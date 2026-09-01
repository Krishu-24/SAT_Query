"""
BaseModelWrapper — Abstract interface for all model pipelines.

Every model wrapper (VQA, grounding, change detection, etc.) must implement this interface.
This ensures the PipelineExecutor can call any model uniformly.
"""

from abc import ABC, abstractmethod


class BaseModelWrapper(ABC):
    """
    Abstract base class for all model wrappers in SatQuery AI.

    Every model must implement the `run` method with a standard signature.
    The PipelineExecutor calls `model.run(action, context)` for each pipeline step.
    """

    @abstractmethod
    def run(self, action: str, context: dict) -> dict:
        """
        Run inference for the given action.

        Args:
            action: What to do. Examples:
                - "answer_question" (VQA)
                - "generate_caption" (captioning)
                - "detect_regions" (grounding detection)
                - "segment_regions" (grounding segmentation)
                - "generate_change_map" (change detection)
                - "answer_change_question" (change VQA)
                - "fuse_modalities" (optical-SAR fusion)
                - "describe_changes" (VLM-based change description)
                - "analyze_fused" (VLM analysis of fused result)

            context: Dict with keys:
                - images (list[str]): Image file paths
                - query (str): User's question
                - request_id (str): Unique request identifier
                - intermediate (dict): Outputs from previous pipeline steps
                    e.g. context["intermediate"]["step_1"] = output from step 1

        Returns:
            Dict with relevant output keys. Common keys:
                - answer (str): Natural language answer
                - confidence (float): Model confidence
                - evidence_images (list[dict]): Evidence image info
                - regions (list[dict]): Detected bounding regions
                - type (str): Output type identifier
        """
        pass
