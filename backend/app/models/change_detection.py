"""
Change Detection Model Stub — Placeholder for TinyCD.

Owner: M4 (ML Pipelines Lead)
Status: STUB — returns 'Model output not available'.

Replace with real TinyCD inference.
"""

import numpy as np
from PIL import Image
from loguru import logger

from app.models.base import BaseModelWrapper
from app.output.evidence import colorize_change_map


class ChangeDetectionModel(BaseModelWrapper):
    """
    Stub: TinyCD change detection model.

    Generates a random but plausible change mask from two images.
    TODO (M4): Replace with actual TinyCD inference on LEVIR-CD weights.
    """

    def run(self, action: str, context: dict) -> dict:
        img1_path = context["images"][0]
        img2_path = context["images"][1]
        request_id = context.get("request_id", "demo")

        logger.info("[STUB] Change detection running on image pair")

        # No model available
        return {
            "type": "change_map",
            "change_ratio": 0.0,
            "changed_pixels": 0,
            "total_pixels": 0,
            "evidence_images": [],
        }
