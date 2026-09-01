# 07 — Model Pipelines Plan (POC)

> Model-agnostic pipeline wrappers. Model slots are placeholders — final model choices TBD.

---

## Owner: M4 (ML Pipelines Lead)

---

## Pipeline Architecture

Every model wrapper follows the same interface:

```python
# app/models/base.py
from abc import ABC, abstractmethod

class BaseModelWrapper(ABC):
    @abstractmethod
    def run(self, action: str, context: dict) -> dict:
        """Run inference.

        Args:
            action: What to do (e.g., 'answer_question', 'detect_regions')
            context: {
                'images': list[str],     # image file paths
                'query': str,            # user's question
                'intermediate': dict,    # outputs from previous pipeline steps
            }

        Returns:
            dict with keys like 'answer', 'confidence', 'evidence_images', 'regions', etc.
        """
        pass
```

---

## Pipeline 1: VQA (Single Image)

**Slot:** `rs_vlm`
**Model:** TBD (VLM — see Model Recommendations doc)
**VRAM:** ~5-6 GB (4-bit quantized)

```python
# app/models/vqa.py
class VQAModel(BaseModelWrapper):
    def __init__(self):
        # Load VLM here (model TBD)
        self.model = None
        self.processor = None

    def run(self, action, context):
        image_path = context["images"][0]
        query = context["query"]

        if action == "answer_question":
            answer = self._infer(image_path, query)
            return {"answer": answer, "confidence": self._confidence(answer)}

        elif action == "generate_caption":
            prompt = ("Provide a detailed description of this satellite image. "
                      "Include land cover types, structures, and spatial layout.")
            answer = self._infer(image_path, prompt)
            return {"answer": answer, "confidence": self._confidence(answer)}

        elif action == "describe_changes":
            # For bi-temporal: gets 2 images
            img1, img2 = context["images"][0], context["images"][1]
            change_info = context.get("intermediate", {}).get("step_1", {})
            answer = self._infer_bitemporal(img1, img2, query, change_info)
            return {"answer": answer, "confidence": self._confidence(answer)}

        elif action == "analyze_fused":
            fused = context.get("intermediate", {}).get("step_1", {})
            answer = self._infer_fused(context["images"], query, fused)
            return {"answer": answer, "confidence": self._confidence(answer)}

    def _infer(self, image_path, prompt):
        # MODEL-SPECIFIC: Replace with actual inference
        pass

    def _infer_bitemporal(self, img1, img2, query, change_info):
        # MODEL-SPECIFIC: Multi-image inference
        pass

    def _infer_fused(self, images, query, fused_info):
        # MODEL-SPECIFIC: Post-fusion analysis
        pass

    def _confidence(self, answer):
        words = len(answer.split())
        if words > 30: return 0.85
        elif words > 15: return 0.75
        elif words > 5: return 0.65
        return 0.50
```

---

## Pipeline 2: Grounding (Single Image)

**Slot:** `grounding_dino` + `sam`
**Models:** TBD (object detector + segmenter — see Model Recommendations)
**VRAM:** ~1-2 GB combined

```python
# app/models/grounding.py
import cv2
import numpy as np
from pathlib import Path

class GroundingModel(BaseModelWrapper):
    def __init__(self):
        # Load object detection model (GDINO or similar)
        self.model = None

    def run(self, action, context):
        image_path = context["images"][0]
        query = context["query"]
        target = self._extract_target(query)

        # Detect bounding boxes for the target text
        boxes, scores, labels = self._detect(image_path, target)

        return {
            "type": "detections",
            "boxes": boxes,
            "scores": scores,
            "labels": labels,
            "target": target,
        }

    def _extract_target(self, query):
        for prefix in ["highlight the ", "show the ", "locate the ",
                       "find the ", "where is the ", "identify the "]:
            if query.lower().startswith(prefix):
                return query[len(prefix):].rstrip("?. ")
        return query

    def _detect(self, image_path, text):
        # MODEL-SPECIFIC: Replace with actual detection
        pass

class SegmentationModel(BaseModelWrapper):
    def __init__(self):
        # Load segmentation model (SAM or similar)
        self.model = None

    def run(self, action, context):
        image_path = context["images"][0]
        detections = context["intermediate"]["step_1"]
        request_id = context.get("request_id", "demo")

        # Segment within detected boxes
        masks = self._segment(image_path, detections["boxes"])

        # Generate overlay evidence image
        overlay_path = self._create_overlay(image_path, masks, detections, request_id)

        return {
            "answer": f"Identified {len(masks)} region(s) matching '{detections['target']}'.",
            "confidence": float(np.mean(detections["scores"])) if detections["scores"] else 0.5,
            "evidence_images": [{"type": "grounding_overlay", "url": overlay_path,
                                 "caption": f"Highlighted: {detections['target']}"}],
            "regions": [{"bbox": b, "label": detections["target"],
                         "confidence": s} for b, s in zip(detections["boxes"], detections["scores"])],
        }

    def _segment(self, image_path, boxes):
        # MODEL-SPECIFIC
        pass

    def _create_overlay(self, image_path, masks, detections, request_id):
        img = cv2.imread(image_path)
        for mask in masks:
            overlay = img.copy()
            overlay[mask > 0] = [0, 120, 255]  # Blue highlight
            img = cv2.addWeighted(img, 0.6, overlay, 0.4, 0)
        out_path = f"results/{request_id}_grounding.png"
        cv2.imwrite(out_path, img)
        return f"/results/{request_id}_grounding.png"
```

---

## Pipeline 3: Change Detection (Bi-Temporal)

**Slot:** `change_detection`
**Model:** TBD (change detection CNN — see Model Recommendations)
**VRAM:** ~0.15-0.5 GB

```python
# app/models/change_detection.py
import cv2
import numpy as np

class ChangeDetectionModel(BaseModelWrapper):
    def __init__(self):
        # Load CD model (TinyCD, BIT, etc.)
        self.model = None

    def run(self, action, context):
        img1_path, img2_path = context["images"][0], context["images"][1]
        request_id = context.get("request_id", "demo")

        # Generate binary change mask
        change_mask = self._detect_changes(img1_path, img2_path)

        # Stats
        total_px = change_mask.size
        changed_px = int(change_mask.sum())
        change_ratio = changed_px / total_px

        # Save change map as evidence
        map_path = self._save_change_map(change_mask, request_id)

        return {
            "type": "change_map",
            "change_mask": change_mask,
            "change_ratio": round(change_ratio, 4),
            "changed_pixels": changed_px,
            "total_pixels": total_px,
            "evidence_images": [{"type": "change_map", "url": map_path,
                                 "caption": f"Changes detected: {change_ratio*100:.1f}% of area"}],
        }

    def _detect_changes(self, path1, path2):
        # MODEL-SPECIFIC: Replace with actual CD inference
        pass

    def _save_change_map(self, mask, request_id):
        colored = np.zeros((*mask.shape, 3), dtype=np.uint8)
        colored[mask > 0] = [0, 0, 255]  # Red for changes
        colored[mask == 0] = [200, 200, 200]  # Gray for no change
        out = f"results/{request_id}_change_map.png"
        cv2.imwrite(out, colored)
        return f"/results/{request_id}_change_map.png"
```

---

## Pipeline 4: Change VQA (Bi-Temporal + Question)

**Slot:** `change_vqa`
**Model:** TBD (reuses VLM with bi-temporal input — see Model Recommendations)
**VRAM:** ~5-6 GB

```python
# app/models/change_vqa.py
class ChangeVQAModel(BaseModelWrapper):
    def __init__(self):
        # Can share backbone with VQA model or use separate
        self.model = None

    def run(self, action, context):
        img1, img2 = context["images"][0], context["images"][1]
        query = context["query"]
        change_info = context.get("intermediate", {}).get("step_1", {})

        answer = self._answer_change_question(img1, img2, query, change_info)

        return {
            "answer": answer,
            "confidence": self._confidence(answer, change_info),
        }

    def _answer_change_question(self, img1, img2, query, change_info):
        # MODEL-SPECIFIC: Feed 2 images + change context to VLM
        pass

    def _confidence(self, answer, change_info):
        base = 0.75
        if change_info.get("change_ratio", 0) > 0.05:
            base += 0.1  # More confident when changes are clear
        return min(base, 0.95)
```

---

## Pipeline 5: Optical-SAR Fusion (Cross-Modal)

**Slot:** `optical_sar_fusion`
**Model:** TBD (fusion network — see Model Recommendations)
**VRAM:** ~0.5 GB

```python
# app/models/optical_sar.py
import numpy as np
import cv2

class OpticalSARFusionModel(BaseModelWrapper):
    def __init__(self):
        # Load fusion network
        self.model = None
        self.class_names = ["Built-up", "Water", "Vegetation", "Bare soil", "Agriculture"]
        self.class_colors = [(255,0,0), (0,0,255), (0,180,0), (139,90,43), (255,255,0)]

    def run(self, action, context):
        optical_path = context["images"][0]
        sar_path = context["images"][1]
        request_id = context.get("request_id", "demo")

        # Run fusion + classification
        class_map, class_probs = self._fuse_and_classify(optical_path, sar_path)

        # Generate land cover map evidence
        map_path = self._save_land_cover_map(class_map, request_id)

        # Compute class percentages
        classes = {}
        total = class_map.size
        for i, name in enumerate(self.class_names):
            count = int((class_map == i).sum())
            if count > 0:
                classes[name] = round(count / total * 100, 1)

        return {
            "type": "fusion_result",
            "classes": classes,
            "evidence_images": [{"type": "land_cover_map", "url": map_path,
                                 "caption": "Land cover classification from optical+SAR fusion"}],
        }

    def _fuse_and_classify(self, optical_path, sar_path):
        # MODEL-SPECIFIC
        pass

    def _save_land_cover_map(self, class_map, request_id):
        h, w = class_map.shape
        colored = np.zeros((h, w, 3), dtype=np.uint8)
        for i, color in enumerate(self.class_colors):
            colored[class_map == i] = color
        out = f"results/{request_id}_landcover.png"
        cv2.imwrite(out, colored)
        return f"/results/{request_id}_landcover.png"
```

---

## Registration (in main.py lifespan)

```python
# In app/main.py lifespan
from app.models.registry import ModelRegistry
from app.models.vqa import VQAModel
from app.models.grounding import GroundingModel, SegmentationModel
from app.models.change_detection import ChangeDetectionModel
from app.models.change_vqa import ChangeVQAModel
from app.models.optical_sar import OpticalSARFusionModel

registry = ModelRegistry()
registry.register("rs_vlm", lambda: VQAModel(), vram_gb=6)
registry.register("grounding_dino", lambda: GroundingModel(), vram_gb=1)
registry.register("sam", lambda: SegmentationModel(), vram_gb=1)
registry.register("change_detection", lambda: ChangeDetectionModel(), vram_gb=0.5)
registry.register("change_vqa", lambda: ChangeVQAModel(), vram_gb=6)
registry.register("optical_sar_fusion", lambda: OpticalSARFusionModel(), vram_gb=0.5)
app.state.model_registry = registry
```

---

## What M4 Needs From Others

| Need | From | When |
|------|------|------|
| Model weights downloaded | M5 | Day 1 afternoon |
| `BaseModelWrapper` interface agreed | M1 | Day 1 morning |
| `context` dict structure agreed | M3 | Day 1 morning |
| Evidence image save path convention | M1 | Day 1 morning |
| Specific model choices | Team decision | Before Day 1 coding |
