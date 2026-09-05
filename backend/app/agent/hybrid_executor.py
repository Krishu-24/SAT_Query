"""
Executor that prefers paired Model Hosts for rs_vlm steps, then falls back
to local PipelineExecutor or UnavailableModelExecutor.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from app.agent.executor import PipelineExecutor, StepResult
from app.agent.unavailable_executor import UnavailableModelExecutor
from app.node.bridge import try_remote_vlm
from app.node.registry import get_registry


_REMOTE_ACTIONS = {
    "answer_question": "vqa",
    "generate_caption": "captioning",
    "describe_changes": "vqa",
    "analyze_fused": "vqa",
}


class HybridPipelineExecutor:
    """
    Preserves existing pipeline shape. For rs_vlm actions that map to
    vqa/captioning, attempts remote node inference first when a host is paired.
    """

    def __init__(
        self,
        registry=None,
        *,
        skip_local_inference: bool = True,
    ):
        self.registry = registry
        self.skip_local_inference = skip_local_inference

    def execute(
        self,
        pipeline: list[dict],
        image_paths: list[str],
        query: str,
        request_id: str = "demo",
        intent_decomposition: Optional[list[dict]] = None,
    ) -> list[StepResult]:
        has_remote = bool(get_registry(reload=True).list_nodes())
        if not has_remote:
            logger.warning(
                f"[{request_id}] No paired Model Host in registry — "
                "falling back to local/unavailable path"
            )
            if self.skip_local_inference:
                return UnavailableModelExecutor().execute(
                    pipeline,
                    image_paths,
                    query,
                    request_id,
                    intent_decomposition=intent_decomposition,
                )
            if self.registry is None:
                raise RuntimeError("Model registry required for local inference")
            return PipelineExecutor(self.registry).execute(
                pipeline, image_paths, query, request_id
            )

        logger.info(
            f"[{request_id}] Paired hosts: "
            f"{[n.node_id for n in get_registry().list_nodes()]}"
        )

        results: list[StepResult] = []
        image_names = [Path(p).name for p in image_paths]
        intents = intent_decomposition or []
        pipeline_t0 = time.perf_counter()
        context_intermediate: dict[str, Any] = {}

        for step in pipeline:
            step_num = step["step"]
            model_name = step["model"]
            action = step["action"]
            task_id = step.get("task_id")
            started_at_ms = (time.perf_counter() - pipeline_t0) * 1000

            intent = next(
                (i for i in intents if i.get("task_id") == task_id),
                None,
            )
            query_for_model = (intent.get("query") if intent else None) or query

            remote_task = _REMOTE_ACTIONS.get(action) if model_name == "rs_vlm" else None
            if remote_task:
                t0 = time.perf_counter()
                resp = try_remote_vlm(
                    task=remote_task,
                    query=query_for_model,
                    image_paths=[Path(p) for p in image_paths],
                    model="qwen-vl",
                    request_id=request_id,
                )
                infer_ms = (time.perf_counter() - t0) * 1000

                if resp is not None and resp.status == "success":
                    output = {
                        "answer": resp.answer,
                        "confidence": resp.confidence,
                        "status": "ok",
                        "model": resp.model or "qwen-vl",
                        "action": action,
                        "query": query_for_model,
                        "images": image_names,
                        "execution": "REMOTE",
                        "node_id": resp.node_id,
                        "runtime": resp.runtime,
                        "request_id": resp.request_id,
                        "task_id": task_id,
                    }
                    results.append(
                        StepResult(
                            step_num=step_num,
                            model_name=model_name,
                            action=action,
                            output=output,
                            time_ms=infer_ms,
                            success=True,
                            load_time_ms=0.0,
                            inference_time_ms=infer_ms,
                            model_was_cached=True,
                            started_at_ms=started_at_ms,
                            telemetry={
                                "execution": "REMOTE",
                                "node_id": resp.node_id,
                                "runtime": resp.runtime,
                                "model": resp.model,
                                "request_id": resp.request_id,
                                **(resp.telemetry or {}),
                            },
                        )
                    )
                    context_intermediate[f"step_{step_num}"] = output
                    logger.info(
                        f"[{request_id}] Step {step_num} REMOTE ok via {resp.node_id}"
                    )
                    continue

                if resp is not None and resp.status == "error":
                    # Remote attempted but failed — structured error, do not crash.
                    output = {
                        "answer": "Model not available",
                        "confidence": None,
                        "status": "remote_error",
                        "error_code": resp.error_code,
                        "error": resp.error,
                        "execution": "REMOTE",
                        "node_id": resp.node_id,
                        "model": model_name,
                        "action": action,
                        "query": query_for_model,
                        "images": image_names,
                        "request_id": getattr(resp, "request_id", request_id),
                    }
                    results.append(
                        StepResult(
                            step_num=step_num,
                            model_name=model_name,
                            action=action,
                            output=output,
                            time_ms=infer_ms,
                            success=False,
                            error=resp.error_code or resp.error or "REMOTE_INFERENCE_FAILED",
                            load_time_ms=0.0,
                            inference_time_ms=infer_ms,
                            model_was_cached=False,
                            started_at_ms=started_at_ms,
                            telemetry={
                                "execution": "REMOTE",
                                "node_id": resp.node_id,
                                "error_code": resp.error_code,
                            },
                        )
                    )
                    logger.warning(
                        f"[{request_id}] Step {step_num} REMOTE failed: "
                        f"{resp.error_code} {resp.error}"
                    )
                    break

            # No remote path for this step — local or unavailable
            if self.skip_local_inference:
                stub = UnavailableModelExecutor().execute(
                    [step],
                    image_paths,
                    query,
                    request_id,
                    intent_decomposition=intent_decomposition,
                )
                if stub:
                    stub[0].started_at_ms = started_at_ms
                    results.extend(stub)
                    if not stub[0].success:
                        break
                continue

            if self.registry is None:
                results.append(
                    StepResult(
                        step_num=step_num,
                        model_name=model_name,
                        action=action,
                        output=None,
                        time_ms=0.0,
                        success=False,
                        error="Model not loaded",
                        started_at_ms=started_at_ms,
                    )
                )
                break

            one = PipelineExecutor(self.registry).execute(
                [step], image_paths, query, request_id
            )
            results.extend(one)
            if one and not one[0].success:
                break

        return results
