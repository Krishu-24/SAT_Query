"""
PipelineExecutor — Runs pipeline steps from a RoutingDecision.

Walks through each step in the pipeline, loads the appropriate model via
ModelRegistry, calls model.run(action, context), and collects results.

Intermediate outputs from earlier steps are passed forward via context["intermediate"].
"""

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from loguru import logger


@dataclass
class StepResult:
    """Result of a single pipeline step."""
    step_num: int
    model_name: str
    action: str
    output: Optional[Any]
    time_ms: float
    success: bool
    error: Optional[str] = None


class PipelineExecutor:
    """
    Executes a multi-step model pipeline.

    Each step:
      1. Load model from registry (auto VRAM management)
      2. Call model.run(action, context)
      3. Store output in context["intermediate"] for next step
      4. Record timing and success/failure

    On failure: logs the error, records it in StepResult, and stops the pipeline.
    """

    def __init__(self, registry):
        """
        Args:
            registry: ModelRegistry instance for loading/unloading models.
        """
        self.registry = registry

    def execute(
        self,
        pipeline: list[dict],
        image_paths: list[str],
        query: str,
        request_id: str = "demo",
    ) -> list[StepResult]:
        """
        Execute the full pipeline.

        Args:
            pipeline: List of step dicts from RoutingDecision.pipeline.
                      Each dict has: step (int), model (str), action (str).
            image_paths: List of uploaded image file paths.
            query: User's natural language query.
            request_id: Unique request identifier for evidence file naming.

        Returns:
            List of StepResult objects.
        """
        results: list[StepResult] = []
        context = {
            "images": image_paths,
            "query": query,
            "request_id": request_id,
            "intermediate": {},
        }

        for step in pipeline:
            step_num = step["step"]
            model_name = step["model"]
            action = step["action"]

            logger.info(
                f"[{request_id}] Step {step_num}: {model_name}.{action}"
            )

            start = time.time()
            try:
                model = self.registry.get(model_name)
                output = model.run(action=action, context=context)
                elapsed_ms = (time.time() - start) * 1000

                # Store output for downstream steps
                context["intermediate"][f"step_{step_num}"] = output

                results.append(StepResult(
                    step_num=step_num,
                    model_name=model_name,
                    action=action,
                    output=output,
                    time_ms=elapsed_ms,
                    success=True,
                ))

                logger.info(
                    f"[{request_id}] Step {step_num} complete ({elapsed_ms:.0f}ms)"
                )

            except Exception as e:
                elapsed_ms = (time.time() - start) * 1000
                error_msg = str(e)

                logger.error(
                    f"[{request_id}] Step {step_num} FAILED: {error_msg}"
                )

                results.append(StepResult(
                    step_num=step_num,
                    model_name=model_name,
                    action=action,
                    output=None,
                    time_ms=elapsed_ms,
                    success=False,
                    error=error_msg,
                ))

                # Stop pipeline on failure
                break

        return results
