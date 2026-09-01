# 06 — Agent and Router Plan (POC)

> Task detection, input validation, and trace generation for a single-endpoint remote-sensing analysis system.

## Owner: M3 (Agent / Router Lead)

## Core Files

| File | Purpose | Timing |
|---|---|---|
| `app/agent/router.py` | route selection based on input and query text | Day 1 morning |
| `app/agent/validator.py` | format, count, and modality validation | Day 1 afternoon |
| `app/output/trace.py` | execution trace structuring | Day 1 evening |
| `app/output/integrator.py` | combine model outputs into final payload | Day 1 evening |
| `app/output/evidence.py` | produce overlays and change-map outputs | Day 2 afternoon |

## Router Design

The router relies on two signals:

1. input structure — number of images, modality, and temporal relationship
2. query semantics — keywords that indicate the intent of the request

### Task Classification Matrix

| Images | Modality | Keywords | Task |
|---|---|---|---|
| 1 | any | "highlight", "show", "locate", "find" | `GROUNDING` |
| 1 | any | "describe", "caption", "summarize" | `CAPTION` |
| 1 | any | general question | `VQA` |
| 2 | same | specific question about change | `CHANGE_VQA` |
| 2 | same | general "what changed" query | `CHANGE_DETECTION` |
| 2 | optical + SAR | any | `OPTICAL_SAR` |

## Implementation

```python
# app/agent/router.py
from enum import Enum
from dataclasses import dataclass

class TaskType(Enum):
    VQA = "vqa"
    CAPTION = "caption"
    GROUNDING = "grounding"
    CHANGE_DETECTION = "change_detection"
    CHANGE_VQA = "change_vqa"
    OPTICAL_SAR = "optical_sar"

@dataclass
class RoutingDecision:
    task_type: TaskType
    models: list[str]
    pipeline: list[dict]
    confidence: float
    reasoning: str

class RuleBasedRouter:
    GROUNDING_KW = [
        "highlight", "show", "locate", "find", "where is",
        "mark", "segment", "outline", "box", "identify region"
    ]
    CAPTION_KW = [
        "describe", "caption", "summarize", "overview",
        "tell me about", "what does this show"
    ]
    CHANGE_KW = [
        "change", "differ", "before", "after", "increase",
        "decrease", "grew", "expand", "transform"
    ]

    def route(self, query: str, input_info: dict) -> RoutingDecision:
        q = query.lower()
        n = input_info["num_images"]
        mods = input_info["modalities"]
        is_cross = input_info.get("is_cross_modal", False)

        if is_cross or (n == 2 and set(mods) == {"optical", "sar"}):
            return RoutingDecision(
                TaskType.OPTICAL_SAR,
                ["optical_sar_fusion", "rs_vlm"],
                [
                    {"step": 1, "model": "optical_sar_fusion", "action": "fuse_modalities"},
                    {"step": 2, "model": "rs_vlm", "action": "analyze_fused"},
                ],
                0.92,
                "Cross-modal input selected optical-sar fusion",
            )

        if n == 2:
            is_specific = any(q.startswith(w) for w in ["has ", "is ", "did ", "does ", "how many", "how much"]) or "?" in q
            if is_specific and self._has_kw(q, self.CHANGE_KW):
                return RoutingDecision(
                    TaskType.CHANGE_VQA,
                    ["change_detection", "change_vqa"],
                    [
                        {"step": 1, "model": "change_detection", "action": "generate_change_map"},
                        {"step": 2, "model": "change_vqa", "action": "answer_change_question"},
                    ],
                    0.90,
                    "Bi-temporal input paired with a specific change question",
                )

            return RoutingDecision(
                TaskType.CHANGE_DETECTION,
                ["change_detection", "rs_vlm"],
                [
                    {"step": 1, "model": "change_detection", "action": "generate_change_map"},
                    {"step": 2, "model": "rs_vlm", "action": "describe_changes"},
                ],
                0.90,
                "Bi-temporal input selected change detection",
            )

        if self._has_kw(q, self.GROUNDING_KW):
            return RoutingDecision(
                TaskType.GROUNDING,
                ["grounding_dino", "sam"],
                [
                    {"step": 1, "model": "grounding_dino", "action": "detect_regions"},
                    {"step": 2, "model": "sam", "action": "segment_regions"},
                ],
                0.95,
                "Grounding keywords detected in the prompt",
            )

        if self._has_kw(q, self.CAPTION_KW):
            return RoutingDecision(
                TaskType.CAPTION,
                ["rs_vlm"],
                [{"step": 1, "model": "rs_vlm", "action": "generate_caption"}],
                0.90,
                "Caption-style prompt detected",
            )

        return RoutingDecision(
            TaskType.VQA,
            ["rs_vlm"],
            [{"step": 1, "model": "rs_vlm", "action": "answer_question"}],
            0.85,
            "General question selected the VQA pathway",
        )

    def _has_kw(self, q, kws):
        return any(kw in q for kw in kws)
```

## Input Validation

```python
# app/agent/validator.py
from pathlib import Path
from dataclasses import dataclass, field

@dataclass
class ValidationResult:
    is_valid: bool
    num_images: int
    modalities: list[str]
    is_temporal: bool
    is_cross_modal: bool
    format_info: list[dict]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

class InputValidator:
    VALID_EXT = {".tif", ".tiff", ".geotiff", ".png", ".jpg", ".jpeg"}

    def validate(self, paths: list[str], metadata: dict = None) -> ValidationResult:
        errors, warnings = [], []
        modalities = metadata.get("modalities", ["optical"]) if metadata else ["optical"]

        if len(paths) == 0:
            errors.append("No images provided.")
        if len(paths) > 2:
            errors.append(f"Max 2 images, got {len(paths)}.")

        fmt_info = []
        for i, p in enumerate(paths):
            ext = Path(p).suffix.lower()
            if ext not in self.VALID_EXT:
                errors.append(f"Image {i + 1}: unsupported format '{ext}'.")
            from PIL import Image
            try:
                img = Image.open(p)
                fmt_info.append({"size": img.size, "bands": len(img.getbands()), "format": ext})
            except Exception as e:
                errors.append(f"Image {i + 1}: cannot read — {e}")

        while len(modalities) < len(paths):
            modalities.append("optical")

        is_cross = len(paths) == 2 and set(modalities[:2]) == {"optical", "sar"}
        is_temporal = len(paths) == 2 and not is_cross

        return ValidationResult(
            is_valid=len(errors) == 0,
            num_images=len(paths),
            modalities=modalities[:len(paths)],
            is_temporal=is_temporal,
            is_cross_modal=is_cross,
            format_info=fmt_info,
            errors=errors,
            warnings=warnings,
        )
```

## Trace Builder

```python
# app/output/trace.py
class TraceBuilder:
    def build(self, validation, decision, step_results):
        return {
            "input_validation": {
                "image_count": validation.num_images,
                "format": [f.get("format", "unknown") for f in validation.format_info],
                "modality": validation.modalities,
                "temporal": validation.is_temporal,
                "cross_modal": validation.is_cross_modal,
                "compatible": validation.is_valid,
                "warnings": validation.warnings,
            },
            "detected_task": decision.task_type.value,
            "task_confidence": decision.confidence,
            "reasoning": decision.reasoning,
            "selected_models": [{"name": m, "version": "1.0"} for m in decision.models],
            "pipeline_steps": [
                {
                    "step": r.step_num,
                    "model": r.model_name,
                    "action": r.action,
                    "status": "success" if r.success else "error",
                    "time_ms": round(r.time_ms, 1),
                    "error": r.error,
                }
                for r in step_results
            ],
            "total_time_ms": round(sum(r.time_ms for r in step_results), 1),
        }
```

## Testing the Router

```python
router = RuleBasedRouter()

tests = [
    ("What objects are present?", {"num_images": 1, "modalities": ["optical"]}, "vqa"),
    ("Describe the scene", {"num_images": 1, "modalities": ["optical"]}, "caption"),
    ("Highlight the water body", {"num_images": 1, "modalities": ["optical"]}, "grounding"),
    ("What changed?", {"num_images": 2, "modalities": ["optical", "optical"], "is_temporal": True}, "change_detection"),
    ("Has the built-up area increased?", {"num_images": 2, "modalities": ["optical", "optical"], "is_temporal": True}, "change_vqa"),
    ("Identify regions using both", {"num_images": 2, "modalities": ["optical", "sar"], "is_cross_modal": True}, "optical_sar"),
]

for query, info, expected in tests:
    result = router.route(query, info)
    status = "PASS" if result.task_type.value == expected else "FAIL"
    print(f"{status} '{query[:30]}...' → {result.task_type.value} (expected {expected})")
```

## OutputIntegrator

```python
# app/output/integrator.py
class OutputIntegrator:
    def integrate(self, step_results, task_type, query, request_id=""):
        answer = "No answer generated."
        confidence = 0.5
        evidence = {"images": [], "regions": []}

        for r in step_results:
            if not r.success or not r.output:
                continue
            out = r.output
            if "answer" in out:
                answer = out["answer"]
            if "confidence" in out:
                confidence = out["confidence"]
            if "evidence_images" in out:
                evidence["images"].extend(out["evidence_images"])
            if "regions" in out:
                evidence["regions"].extend(out["regions"])

        return {"answer": answer, "confidence": confidence, "evidence": evidence}
```

---

## Testing the Router

Test these queries to verify routing:

```python
# Quick test
router = RuleBasedRouter()

tests = [
    ("What objects are present?", {"num_images": 1, "modalities": ["optical"]}, "vqa"),
    ("Describe the scene", {"num_images": 1, "modalities": ["optical"]}, "caption"),
    ("Highlight the water body", {"num_images": 1, "modalities": ["optical"]}, "grounding"),
    ("What changed?", {"num_images": 2, "modalities": ["optical", "optical"], "is_temporal": True}, "change_detection"),
    ("Has the built-up area increased?", {"num_images": 2, "modalities": ["optical", "optical"], "is_temporal": True}, "change_vqa"),
    ("Identify regions using both", {"num_images": 2, "modalities": ["optical", "sar"], "is_cross_modal": True}, "optical_sar"),
]

for query, info, expected in tests:
    result = router.route(query, info)
    status = "PASS" if result.task_type.value == expected else "FAIL"
    print(f"{status} '{query[:30]}...' → {result.task_type.value} (expected {expected})")
```
