"""
Grounding Model Wrappers — Grounding DINO (detection) + SAM 2.1 (segmentation).

Owner: M4 (ML Pipelines Lead)

GroundingModel: text-guided open-vocabulary object detection.
SegmentationModel: turns detected boxes into precise pixel masks and builds
the evidence overlay + region list returned to the user.

Both fall back to 'Model output not available' when weights aren't
downloaded or no GPU is present, matching the pattern in app/models/vqa.py.
"""

from pathlib import Path

import numpy as np
from loguru import logger

from app.models.base import BaseModelWrapper
from app.output.evidence import overlay_bboxes, overlay_segmentation_mask
from app.utils.config import settings


class GroundingModel(BaseModelWrapper):
    """
    Grounding DINO text-guided object detection.

    On GPU with downloaded weights: runs real Grounding DINO inference.
    On CPU / no weights: returns empty detections for testing.
    """

    BOX_THRESHOLD = 0.30
    TEXT_THRESHOLD = 0.25

    def __init__(self):
        self.model = None
        self.processor = None
        self.device = "cpu"
        self._mock_mode = False

        self._try_load_model()

    def _try_load_model(self):
        """Attempt to load Grounding DINO. Fall back to mock mode if unavailable."""
        model_path = settings.GDINO_MODEL_PATH

        if not Path(model_path).exists():
            logger.warning(
                "Grounding DINO weights not found. Running in NO OUTPUT MODE — "
                "empty detections will be returned."
            )
            self._mock_mode = True
            return

        try:
            import torch
            from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection

            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading Grounding DINO from {model_path} on {device}...")

            self.processor = AutoProcessor.from_pretrained(model_path)
            self.model = AutoModelForZeroShotObjectDetection.from_pretrained(
                model_path
            ).to(device)
            self.device = device

            logger.info(f"Grounding DINO loaded successfully on {device}")

        except Exception as e:
            logger.warning(f"Failed to load Grounding DINO: {e}. Using NO OUTPUT MODE.")
            self._mock_mode = True

    def run(self, action: str, context: dict) -> dict:
        """
        Detect regions matching the text extracted from the user's query.

        Args:
            action: Must be "detect_regions".
            context: Pipeline context dict (uses "images", "query").

        Returns:
            Dict with "type", "boxes", "scores", "labels", "target".
        """
        if action != "detect_regions":
            raise ValueError(f"Unknown action for GroundingModel: '{action}'")

        query = context["query"]
        target = self._extract_target(query)

        if self._mock_mode:
            logger.info(f"[NO OUTPUT MODE] Grounding DINO skipped for target: '{target}'")
            return {
                "type": "detections",
                "boxes": [],
                "scores": [],
                "labels": [],
                "target": target,
            }

        image_path = context["images"][0]
        logger.info(f"Grounding DINO detecting: '{target}'")

        try:
            boxes, scores, labels = self._detect(image_path, target)
        except Exception as e:
            logger.error(f"Grounding DINO inference failed: {e}")
            boxes, scores, labels = [], [], []

        return {
            "type": "detections",
            "boxes": boxes,
            "scores": scores,
            "labels": labels,
            "target": target,
        }

    def _extract_target(self, query: str) -> str:
        """Extract the grounding target from the query."""
        for prefix in [
            "highlight the ", "show the ", "locate the ",
            "find the ", "where is the ", "identify the ",
            "show me the ", "point out the ", "detect the ",
        ]:
            if query.lower().startswith(prefix):
                return query[len(prefix):].rstrip("?. ")
        return query.rstrip("?. ")

    def _detect(self, image_path: str, target: str) -> tuple[list, list, list]:
        """
        Run Grounding DINO on the image with the target phrase as a text prompt.

        Returns:
            (boxes, scores, labels) — boxes as [x1, y1, x2, y2] pixel coords.
        """
        import torch
        from PIL import Image

        image = Image.open(image_path).convert("RGB")

        # Grounding DINO expects lowercase, period-terminated phrases.
        text_query = target.lower().strip()
        if not text_query.endswith("."):
            text_query += "."

        inputs = self.processor(images=image, text=text_query, return_tensors="pt").to(
            self.device
        )

        with torch.no_grad():
            outputs = self.model(**inputs)

        results = self.processor.post_process_grounded_object_detection(
            outputs,
            inputs.input_ids,
            box_threshold=self.BOX_THRESHOLD,
            text_threshold=self.TEXT_THRESHOLD,
            target_sizes=[image.size[::-1]],
        )[0]

        boxes = results["boxes"].cpu().numpy().tolist()
        scores = [round(s, 3) for s in results["scores"].cpu().numpy().tolist()]
        labels = results.get("text_labels") or results.get("labels") or [target] * len(boxes)

        return boxes, scores, list(labels)


class SegmentationModel(BaseModelWrapper):
    """
    SAM 2.1 Hiera-Tiny segmentation model.

    Turns Grounding DINO's boxes into precise pixel masks, builds the
    evidence overlay image, and assembles the final grounding response.

    On GPU with downloaded weights: runs real SAM 2.1 inference.
    On CPU / no weights: returns 'Model output not available' for testing.
    """

    def __init__(self):
        self.predictor = None
        self.device = "cpu"
        self._mock_mode = False

        self._try_load_model()

    def _try_load_model(self):
        """Attempt to load SAM 2.1. Fall back to mock mode if unavailable."""
        try:
            import torch
            from sam2.sam2_image_predictor import SAM2ImagePredictor

            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading SAM 2.1 ({settings.SAM_MODEL_ID}) on {device}...")

            self.predictor = SAM2ImagePredictor.from_pretrained(
                settings.SAM_MODEL_ID, device=device
            )
            self.device = device

            logger.info(f"SAM 2.1 loaded successfully on {device}")

        except Exception as e:
            logger.warning(f"Failed to load SAM 2.1: {e}. Using NO OUTPUT MODE.")
            self._mock_mode = True

    def run(self, action: str, context: dict) -> dict:
        """
        Segment the regions detected by GroundingModel and build the response.

        Args:
            action: Must be "segment_regions".
            context: Pipeline context dict. Reads detections from
                context["intermediate"]["step_1"] (GroundingModel's output).

        Returns:
            Dict with "answer", "confidence", "evidence_images", "regions".
        """
        if action != "segment_regions":
            raise ValueError(f"Unknown action for SegmentationModel: '{action}'")

        image_path = context["images"][0]
        detections = context["intermediate"]["step_1"]
        request_id = context.get("request_id", "demo")

        target = detections.get("target", "object")
        boxes = detections.get("boxes", [])
        scores = detections.get("scores", [])

        # No detections is a normal outcome (target not present), not an error.
        if not boxes:
            logger.info(f"[{request_id}] No regions detected for '{target}'")
            return {
                "answer": f"No region matching '{target}' was found in the image.",
                "confidence": 0.0,
                "evidence_images": [],
                "regions": [],
            }

        if self._mock_mode:
            logger.info(f"[NO OUTPUT MODE] SAM skipped for {len(boxes)} region(s)")
            return {
                "answer": "Model output not available",
                "confidence": 0.0,
                "evidence_images": [],
                "regions": [],
            }

        logger.info(f"[{request_id}] SAM segmenting {len(boxes)} region(s) for '{target}'")

        try:
            masks = self._segment(image_path, boxes)
        except Exception as e:
            logger.error(f"[{request_id}] SAM inference failed: {e}")
            masks = []

        evidence_images = []
        if masks:
            combined_mask = np.logical_or.reduce(masks).astype(np.uint8)
            overlay_url = overlay_segmentation_mask(image_path, combined_mask, request_id)
        else:
            # Segmentation failed but detection succeeded — fall back to box overlay.
            overlay_url = overlay_bboxes(
                image_path, boxes, [target] * len(boxes), scores, request_id
            )

        if overlay_url:
            evidence_images.append({
                "type": "grounding_overlay",
                "url": overlay_url,
                "caption": f"Highlighted: {target}",
            })

        regions = [
            {"bbox": box, "label": target, "confidence": score}
            for box, score in zip(boxes, scores)
        ]

        return {
            "answer": f"Identified {len(boxes)} region(s) matching '{target}'.",
            "confidence": float(np.mean(scores)) if scores else 0.5,
            "evidence_images": evidence_images,
            "regions": regions,
        }

    def _segment(self, image_path: str, boxes: list[list[float]]) -> list[np.ndarray]:
        """Run SAM 2.1 on the image, once per detected box. Returns boolean masks."""
        from PIL import Image

        image = np.array(Image.open(image_path).convert("RGB"))
        self.predictor.set_image(image)

        masks = []
        for box in boxes:
            box_arr = np.array(box, dtype=np.float32)
            box_masks, _, _ = self.predictor.predict(box=box_arr, multimask_output=False)
            masks.append(box_masks[0].astype(bool))

        return masks
