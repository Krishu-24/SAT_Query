from __future__ import annotations

import re

from app.schemas.intent import QueryIntent, QueryPlan
from app.schemas.task import TaskType


class QueryClassifier:
    """Rule-based intent classifier used as LLM-planner fallback."""

    # Spatial overlay / localization — NOT relative-location prose in a VQA.
    GROUNDING_OVERLAY = [
        "highlight",
        "segment",
        "outline",
        "bounding box",
        "mark the",
        "mark ",
        "circle the",
        "point out",
        "show me",
    ]

    GROUNDING_LOCATE = [
        "locate the",
        "locate ",
        "find the",
        "find ",
        "where is the",
        "where are the",
        "detect the",
        "detect ",
    ]

    CAPTION_KEYWORDS = [
        "describe",
        "caption",
        "give me a description",
        "generate a description",
        "summarize",
        "overview",
    ]

    CHANGE_KEYWORDS = [
        "what changed",
        "changes between",
        "change between",
        "difference between",
        "detect changes",
    ]

    def classify(self, query: str) -> QueryIntent:
        query_lower = query.lower().strip().rstrip(".")

        # Multi-part analytical questions → one VQA (do not ground/caption-split)
        if self._is_compound_analytical_vqa(query_lower):
            return QueryIntent(
                task_id="task_1",
                task=TaskType.VQA,
                target=query,
                requires_spatial_evidence=False,
                requires_segmentation=False,
                confidence=0.92,
            )

        # --------------------------------------------------
        # Grounding — overlay verbs OR short locate/where-is-the requests
        # --------------------------------------------------
        if self._is_grounding_request(query_lower):
            target = self._extract_target(query_lower)
            return QueryIntent(
                task_id="task_1",
                task=TaskType.GROUNDING,
                target=target,
                requires_spatial_evidence=True,
                requires_segmentation=(
                    "highlight" in query_lower or "segment" in query_lower
                ),
                confidence=0.95,
            )

        # --------------------------------------------------
        # Change Detection
        # --------------------------------------------------
        if any(keyword in query_lower for keyword in self.CHANGE_KEYWORDS):
            return QueryIntent(
                task_id="task_1",
                task=TaskType.CHANGE_DETECTION,
                target="changes",
                requires_spatial_evidence=True,
                requires_comparison=True,
                confidence=0.95,
            )

        # --------------------------------------------------
        # Captioning (not when clearly a question → VQA)
        # --------------------------------------------------
        if any(keyword in query_lower for keyword in self.CAPTION_KEYWORDS):
            if self._looks_like_question(query_lower):
                return QueryIntent(
                    task_id="task_1",
                    task=TaskType.VQA,
                    target=query,
                    confidence=0.85,
                )
            return QueryIntent(
                task_id="task_1",
                task=TaskType.CAPTIONING,
                target="image",
                confidence=0.95,
            )

        # --------------------------------------------------
        # VQA
        # --------------------------------------------------
        question_keywords = [
            "what",
            "which",
            "how many",
            "is there",
            "are there",
            "does",
            "do",
            "where",
            "why",
            "examine",
        ]

        if any(
            query_lower.startswith(keyword) or f" {keyword} " in f" {query_lower} "
            for keyword in question_keywords
        ) or "?" in query_lower:
            return QueryIntent(
                task_id="task_1",
                task=TaskType.VQA,
                target=query,
                confidence=0.80,
            )

        # --------------------------------------------------
        # Unknown
        # --------------------------------------------------
        return QueryIntent(
            task_id="task_1",
            task=TaskType.UNKNOWN,
            target=query,
            confidence=0.30,
        )

    def _is_compound_analytical_vqa(self, query: str) -> bool:
        if any(k in query for k in self.GROUNDING_OVERLAY):
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

    def _is_grounding_request(self, query: str) -> bool:
        if any(k in query for k in self.GROUNDING_OVERLAY):
            return True
        # "locate" must be a whole word — not "located"
        if re.search(r"\blocate\b", query) or re.search(r"\bfind\b", query):
            return True
        if any(k in query for k in ("where is the", "where are the", "detect the")):
            return True
        return False

    def _looks_like_question(self, query: str) -> bool:
        if "?" in query:
            return True
        return bool(
            re.search(
                r"\b(what|where|which|how|why|who|is|are|does|do|can|could)\b",
                query,
            )
        )

    def _extract_target(self, query: str) -> str:
        """
        Extract the object/region being referred to.

        This is intentionally simple for the first prototype.
        We will replace it with a more robust query parser later.
        """
        prefixes = [
            "highlight the ",
            "highlight ",
            "locate the ",
            "locate ",
            "find the ",
            "find ",
            "show me the ",
            "show me ",
            "show the ",
            "show ",
            "mark the ",
            "mark ",
            "outline the ",
            "outline ",
            "where is the ",
            "where are the ",
            "detect the ",
            "detect ",
        ]

        target = query
        for prefix in prefixes:
            if query.startswith(prefix):
                target = query[len(prefix):]
                break

        trailing_phrases = [
            " in this image",
            " in the image",
            " on this image",
            " on the image",
            " from this image",
            " from the image",
        ]
        for phrase in trailing_phrases:
            if target.endswith(phrase):
                target = target[: -len(phrase)]
                break

        return target.rstrip(" .")

    def create_plan(self, query: str) -> QueryPlan:
        """
        Convert a natural-language query into one or more tasks.

        Only split compound *actions* (find X and describe). Keep multi-part
        analytical questions as a single VQA task.
        """
        query_lower = query.lower().strip()

        if self._is_compound_analytical_vqa(query_lower):
            return QueryPlan(tasks=[self.classify(query)])

        separators = [
            " then ",
            " also ",
            " as well as ",
            " along with ",
            " and ",
        ]

        parts = [query]
        for separator in separators:
            if separator not in query_lower:
                continue
            split_index = query_lower.find(separator)
            left = query[:split_index].strip()
            right = query[split_index + len(separator) :].strip()
            if not left or not right:
                continue
            # Only split "and" when left is a grounding imperative
            if separator == " and " and not self._left_is_grounding_imperative(left.lower()):
                continue
            parts = [left, right]
            break

        tasks = []
        for part in parts:
            intent = self.classify(part)
            if intent.task != TaskType.UNKNOWN:
                tasks.append(intent)

        if not tasks:
            tasks.append(self.classify(query))

        return QueryPlan(tasks=tasks)

    def _left_is_grounding_imperative(self, left: str) -> bool:
        starts = (
            "find ",
            "locate ",
            "highlight ",
            "show me ",
            "mark ",
            "outline ",
            "detect ",
            "segment ",
            "circle ",
            "point out ",
        )
        return left.startswith(starts) or any(k in left for k in self.GROUNDING_OVERLAY)
