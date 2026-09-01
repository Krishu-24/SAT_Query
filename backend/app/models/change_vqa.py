"""
Change VQA Model Stub — Placeholder for bi-temporal question answering.

Owner: M4 (ML Pipelines Lead)
Status: STUB — returns 'Model output not available'.

In production: reuses Qwen2.5-VL with 2 images + change context.
"""

from loguru import logger

from app.models.base import BaseModelWrapper


class ChangeVQAModel(BaseModelWrapper):
    """
    Stub: Change VQA — answers specific questions about detected changes.

    In the real implementation, this would feed 2 images + change map
    to Qwen2.5-VL for bi-temporal question answering.

    TODO (M4): Replace with actual Qwen multi-image inference + change context.
    """

    def run(self, action: str, context: dict) -> dict:
        query = context["query"]
        change_info = context.get("intermediate", {}).get("step_1", {})

        logger.info(f"[STUB] Change VQA answering: '{query[:50]}...'")

        return {
            "answer": "Model output not available",
            "confidence": 0.0,
        }
