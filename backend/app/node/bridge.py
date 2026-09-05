"""Remote inference bridge used by the Controller pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from loguru import logger

from app.node.client import NodeClient, file_to_image_payload, make_inference_request
from app.node.config_store import DeviceRole, load_device_config
from app.node.registry import get_registry
from app.node.schemas import InferenceResponse, NodeErrorCode


def role_allows_controller_features() -> bool:
    cfg = load_device_config()
    if not cfg:
        return True
    return cfg.role in (DeviceRole.CONTROLLER.value, DeviceRole.FULL_SYSTEM.value)


def role_is_model_host_only() -> bool:
    cfg = load_device_config()
    return bool(cfg and cfg.role == DeviceRole.MODEL_HOST.value)


def try_remote_vlm(
    *,
    task: str,
    query: str,
    image_paths: list[Path],
    model: str = "qwen-vl",
    modalities: Optional[list[Optional[str]]] = None,
    request_id: str = "demo",
) -> Optional[InferenceResponse]:
    """
    Attempt remote VQA/captioning via a paired Model Host.
    Returns None if no paired host / not applicable (caller falls back to local).
    """
    cfg = load_device_config()
    if cfg and cfg.role == DeviceRole.MODEL_HOST.value:
        return None

    # Always re-read disk — CLI pairing updates device.json while uvicorn is running
    registry = get_registry(reload=True)
    node = registry.find_for_task(task, model)
    if not node:
        logger.warning(
            f"[{request_id}] No paired Model Host for task={task} model={model} "
            f"(paired_count={len(registry.list_nodes())})"
        )
        return None

    names = [Path(p).name for p in image_paths]
    logger.info("=" * 64)
    logger.info(f"[{request_id}] OUTGOING → Model Host {node.node_id} @ {node.base_url}")
    logger.info(f"[{request_id}]   task={task}  model={model}")
    logger.info(f"[{request_id}]   query={query!r}")
    logger.info(f"[{request_id}]   images={names}")
    logger.info("=" * 64)

    client = NodeClient(timeout=(cfg.remote_timeout_sec if cfg else 120.0))
    health = client.health(node)
    node.healthy = bool(health.get("ok"))
    if not health.get("ok"):
        node.last_error = health.get("error_code") or health.get("detail") or "unhealthy"
        registry.upsert(node, persist=False)
        logger.error(
            f"[{request_id}] Model Host unhealthy: {node.last_error} ({health})"
        )
        return InferenceResponse(
            request_id=request_id,
            status="error",
            node_id=node.node_id,
            error_code=health.get("error_code") or NodeErrorCode.NODE_OFFLINE.value,
            error=str(node.last_error),
            execution="REMOTE",
        )

    images = []
    for i, p in enumerate(image_paths):
        mod = modalities[i] if modalities and i < len(modalities) else None
        images.append(file_to_image_payload(Path(p), modality=mod))

    req = make_inference_request(
        task=task,
        query=query,
        images=images,
        model=model,
        timeout=(cfg.remote_timeout_sec if cfg else 120.0),
        metadata={"controller_request_id": request_id},
    )
    req.request_id = request_id

    resp = client.infer(node, req)
    if resp.status != "success":
        node.last_error = resp.error_code or resp.error
        registry.upsert(node, persist=False)
        logger.error(
            f"[{request_id}] INCOMING ← REMOTE FAIL "
            f"code={resp.error_code} error={resp.error}"
        )
    else:
        preview = (resp.answer or "")[:240]
        logger.info("=" * 64)
        logger.info(f"[{request_id}] INCOMING ← Model Host {resp.node_id} SUCCESS")
        logger.info(f"[{request_id}]   model={resp.model} runtime={resp.runtime}")
        logger.info(f"[{request_id}]   answer_preview={preview!r}")
        logger.info("=" * 64)
    return resp


def refresh_all_node_health() -> dict[str, Any]:
    registry = get_registry(reload=True)
    client = NodeClient()
    for n in registry.list_nodes():
        h = client.health(n)
        n.healthy = bool(h.get("ok"))
        n.last_error = None if n.healthy else (h.get("error_code") or str(h.get("detail")))
        if n.healthy:
            info = client.info(n)
            if isinstance(info, dict) and info.get("capabilities"):
                n.capabilities = list(info.get("capabilities") or [])
            if isinstance(info, dict) and info.get("models"):
                n.models = list(info.get("models") or [])
        registry.upsert(n, persist=True)
    return registry.status_payload()
