"""
RuleBasedRouter — Keyword + input analysis based task classifier.

Owner: M3 (Agent/Router Lead)

Uses TWO signals to classify the task:
  1. Input analysis — How many images? What modality?
  2. Query keywords — What words suggest which task?

Task Classification Matrix:
  | Images | Modalities    | Keywords                              | → Task            |
  |--------|---------------|---------------------------------------|--------------------|
  | 1      | Any           | "highlight", "show me", "locate", ... | GROUNDING          |
  | 1      | Any           | "describe", "caption", "summarize"    | CAPTION            |
  | 1      | Any           | Any other question                    | VQA                |
  | 2      | Same          | Specific question ("has X increased?")| CHANGE_VQA         |
  | 2      | Same          | General ("what changed?")             | CHANGE_DETECTION   |
  | 2      | optical+sar   | Any                                   | OPTICAL_SAR        |
"""

from __future__ import annotations

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


# Bumped whenever the routing rules themselves change, so a stored trace can
# be interpreted against the ruleset that actually produced it.
ROUTER_VERSION = "rule_based_keyword/2"


class TaskType(Enum):
    """All supported task types for the agentic pipeline."""
    VQA = "vqa"
    CAPTION = "caption"
    GROUNDING = "grounding"
    CHANGE_DETECTION = "change_detection"
    CHANGE_VQA = "change_vqa"
    OPTICAL_SAR = "optical_sar"


@dataclass
class RoutingDecision:
    """Output of the router — what task, which models, pipeline steps.

    No `confidence` field: this is a deterministic keyword/rule-based
    classifier, not a learned model — it has no real notion of "how sure"
    it is about a match, so it doesn't fabricate one. `reasoning` carries
    the actual justification for the decision instead. The telemetry fields
    below exist to explain a decision, not to score it — do not "complete
    the set" by adding a confidence back.

    Optional planner_* / router_type fields are unused by RuleBasedRouter
    (defaults preserve existing behavior). The Shiven adapter fills them so
    TraceBuilder can surface LLM planning metadata without a second return type.
    """
    task_type: TaskType
    models: list[str]
    pipeline: list[dict]
    reasoning: str
    # Stable identifier for the branch that fired, so telemetry can group
    # and compare decisions without parsing the prose in `reasoning`.
    rule_id: str = ""
    # The actual keyword substrings that matched this query. Empty for
    # branches that match on input structure (image count/modality) rather
    # than on query text.
    matched_keywords: list[str] = field(default_factory=list)

    # ── Optional: filled by Shiven adapter; RuleBasedRouter leaves defaults ──
    router_type: str = "rule_based_keyword"
    router_version: str = ROUTER_VERSION
    # None → TraceBuilder keeps legacy rule_id == "default_vqa" behavior.
    fallback_used: Optional[bool] = None
    planner_type: Optional[str] = None
    planning_time_ms: Optional[float] = None
    intent_decomposition: Optional[list[dict]] = None
    planner_raw_output: Optional[str] = None


class RuleBasedRouter:
    """
    Rule-based router for SatQuery AI.

    Deterministic task classifier using keyword matching + input structure.
    Zero VRAM — runs on CPU. Perfect for POC demo.
    """

    # Overlay / localization imperatives — must be whole words / phrases.
    # Avoid bare "locate" matching inside "located".
    GROUNDING_KW = [
        "highlight",
        "show me",
        "locate",
        "find",
        "where is the",
        "where are the",
        "mark",
        "segment",
        "outline",
        "bounding box",
        "point out",
        "detect",
        "circle",
        "indicate",
    ]

    # Strong overlay verbs — if present, never demote grounding to VQA.
    GROUNDING_OVERLAY_KW = [
        "highlight",
        "segment",
        "outline",
        "bounding box",
        "mark the",
        "circle",
        "point out",
        "show me",
    ]

    CAPTION_KW = [
        "describe",
        "caption",
        "summarize",
        "overview",
        "tell me about",
        "what does this show",
        "explain this",
        "what is in this",
        "give me a description",
        "summary",
    ]

    CHANGE_KW = [
        "change", "differ", "before", "after", "increase",
        "decrease", "grew", "expand", "transform", "evolve",
        "develop", "built", "construct", "demolish", "deforest",
        "urban", "sprawl", "flood", "recede",
    ]

    SPECIFIC_QUESTION_PREFIXES = [
        "has ", "is ", "did ", "does ", "how many", "how much",
        "was ", "were ", "are ", "have ", "can you tell",
    ]

    def route(self, query: str, input_info: dict) -> RoutingDecision:
        """
        Classify a user query + input into a task type.

        Args:
            query: Natural language question from the user.
            input_info: Dict with keys:
                - num_images (int)
                - modalities (list[str]): e.g. ["optical"], ["optical", "sar"]
                - is_temporal (bool, optional)
                - is_cross_modal (bool, optional)

        Returns:
            RoutingDecision with task_type, models, pipeline, reasoning.
        """
        q = query.lower().strip()
        n = input_info["num_images"]
        mods = input_info.get("modalities", ["optical"])
        is_cross = input_info.get("is_cross_modal", False)

        # ── Text-only (no images) → conversational response, no image pipeline ──
        if n == 0:
            return RoutingDecision(
                task_type=TaskType.VQA,
                models=["rs_vlm"],
                pipeline=[
                    {"step": 1, "model": "rs_vlm", "action": "answer_question"},
                ],
                reasoning="No images attached → conversational response, no image pipeline run.",
                rule_id="text_only",
            )

        # ── Cross-modal → always Optical-SAR ──
        if is_cross or (n == 2 and set(mods) == {"optical", "sar"}):
            return RoutingDecision(
                task_type=TaskType.OPTICAL_SAR,
                models=["optical_sar_fusion", "rs_vlm"],
                pipeline=[
                    {"step": 1, "model": "optical_sar_fusion", "action": "fuse_modalities"},
                    {"step": 2, "model": "rs_vlm", "action": "analyze_fused"},
                ],
                reasoning="Cross-modal input detected (optical + SAR) → Optical-SAR fusion pipeline",
                rule_id="cross_modal",
            )

        # ── Bi-temporal (2 images, same modality) ──
        if n == 2:
            is_specific = any(q.startswith(w) for w in self.SPECIFIC_QUESTION_PREFIXES)
            if (is_specific or "?" in q) and q.strip("?") != "what changed" and self._has_kw(q, self.CHANGE_KW):
                return RoutingDecision(
                    task_type=TaskType.CHANGE_VQA,
                    models=["change_detection", "change_vqa"],
                    pipeline=[
                        {"step": 1, "model": "change_detection", "action": "generate_change_map"},
                        {"step": 2, "model": "change_vqa", "action": "answer_change_question"},
                    ],
                    reasoning="Bi-temporal input + specific change question → Change VQA pipeline",
                    rule_id="bitemporal_specific",
                    matched_keywords=self._matched_kw(q, self.CHANGE_KW),
                )
            return RoutingDecision(
                task_type=TaskType.CHANGE_DETECTION,
                models=["change_detection", "rs_vlm"],
                pipeline=[
                    {"step": 1, "model": "change_detection", "action": "generate_change_map"},
                    {"step": 2, "model": "rs_vlm", "action": "describe_changes"},
                ],
                reasoning="Bi-temporal input + general query → Change Detection pipeline",
                rule_id="bitemporal_general",
                matched_keywords=self._matched_kw(q, self.CHANGE_KW),
            )

        # ── Single image: multi-part analytical questions → one VQA ──
        # e.g. "What are the features, where are they relative to center, and what evidence..."
        if self._is_compound_analytical_vqa(q):
            return RoutingDecision(
                task_type=TaskType.VQA,
                models=["rs_vlm"],
                pipeline=[
                    {"step": 1, "model": "rs_vlm", "action": "answer_question"},
                ],
                reasoning=(
                    "Multi-part analytical question seeking a textual answer → "
                    "single VQA via VLM (not grounding/caption split)"
                ),
                rule_id="compound_analytical_vqa",
            )

        # ── Single image: Grounding (overlay / localization imperatives) ──
        if self._has_kw(q, self.GROUNDING_KW):
            return RoutingDecision(
                task_type=TaskType.GROUNDING,
                models=["grounding_dino", "sam"],
                pipeline=[
                    {"step": 1, "model": "grounding_dino", "action": "detect_regions"},
                    {"step": 2, "model": "sam", "action": "segment_regions"},
                ],
                reasoning="Grounding keywords detected in query → Grounding pipeline (DINO + SAM)",
                rule_id="grounding_keywords",
                matched_keywords=self._matched_kw(q, self.GROUNDING_KW),
            )

        # ── Single image: Caption ──
        # Prefer VQA when the query is clearly interrogative ("what/how/which...?")
        if self._has_kw(q, self.CAPTION_KW) and not self._is_interrogative_vqa(q):
            return RoutingDecision(
                task_type=TaskType.CAPTION,
                models=["rs_vlm"],
                pipeline=[
                    {"step": 1, "model": "rs_vlm", "action": "generate_caption"},
                ],
                reasoning="Caption/description keywords detected → Caption mode via VLM",
                rule_id="caption_keywords",
                matched_keywords=self._matched_kw(q, self.CAPTION_KW),
            )

        # ── Default: VQA ──
        return RoutingDecision(
            task_type=TaskType.VQA,
            models=["rs_vlm"],
            pipeline=[
                {"step": 1, "model": "rs_vlm", "action": "answer_question"},
            ],
            reasoning="General question → Visual Question Answering via VLM",
            rule_id="default_vqa",
        )

    def _is_compound_analytical_vqa(self, query: str) -> bool:
        """True when the user wants one textual analysis, not boxes/masks.

        Catches prompts like: features + relative location + supporting evidence.
        """
        if self._has_kw(query, self.GROUNDING_OVERLAY_KW):
            return False
        if any(
            p in query
            for p in (
                "relative to",
                "what evidence",
                "supports your",
                "most prominent",
                "visual features",
            )
        ):
            return True
        interrogatives = len(re.findall(r"\b(what|where|which|how|why)\b", query))
        return interrogatives >= 2

    def _is_interrogative_vqa(self, query: str) -> bool:
        if "?" in query:
            return True
        return bool(
            re.search(
                r"^\s*(what|where|which|how|why|who|is|are|does|do|can|could)\b",
                query,
            )
        )

    def _matched_kw(self, query: str, keywords: list[str]) -> list[str]:
        """Keyword phrases that matched as whole words/phrases (not substrings)."""
        matched: list[str] = []
        for kw in keywords:
            if " " in kw:
                if kw in query:
                    matched.append(kw)
            else:
                if re.search(rf"\b{re.escape(kw)}\b", query):
                    matched.append(kw)
        return matched

    def _has_kw(self, query: str, keywords: list[str]) -> bool:
        """Check if any keyword appears as a whole word/phrase in the query."""
        return bool(self._matched_kw(query, keywords))
