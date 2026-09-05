"""Model Host FastAPI router: /node/health|info|capabilities|pair|inference."""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger
from fastapi import APIRouter, Header, HTTPException

from app.node.auth import require_bearer
from app.node.config_store import (
    DEFAULT_HOST_VLM_OLLAMA_TAG,
    DeviceConfig,
    DeviceRole,
    QWEN_VL_MODEL_ID,
    load_device_config,
    local_ip,
)
from app.node.hardware import probe_hardware
from app.node.ollama_runtime import OllamaNodeRuntime
from app.node.schemas import InferenceRequest, InferenceResponse, NodeErrorCode, PairRequest, PairResponse

router = APIRouter(prefix="/node", tags=["node"])


def _cfg() -> DeviceConfig:
    cfg = load_device_config()
    if not cfg:
        raise HTTPException(status_code=503, detail="Device role not configured")
    return cfg


def _assert_host_role(cfg: DeviceConfig) -> None:
    if cfg.role not in (DeviceRole.MODEL_HOST.value, DeviceRole.FULL_SYSTEM.value):
        raise HTTPException(
            status_code=403,
            detail="This process is not a Model Host / Full System node",
        )


def _resolve_ollama_tag(cfg: DeviceConfig, model_id: str) -> Optional[str]:
    for m in cfg.hosted_models or []:
        if m.get("id") == model_id and m.get("enabled", True):
            return m.get("ollama_tag") or model_id
    # Soft fallback when hosted_models empty (misconfigured host)
    if not cfg.hosted_models:
        return model_id if model_id != QWEN_VL_MODEL_ID else DEFAULT_HOST_VLM_OLLAMA_TAG
    return None


def _capabilities(cfg: DeviceConfig) -> list[str]:
    caps: set[str] = set()
    for m in cfg.hosted_models or []:
        for t in m.get("tasks") or []:
            caps.add(t)
    if not caps and cfg.role in (DeviceRole.MODEL_HOST.value, DeviceRole.FULL_SYSTEM.value):
        caps.update({"vqa", "captioning"})
    return sorted(caps)


@router.get("/health")
def node_health(authorization: Optional[str] = Header(None)) -> dict[str, Any]:
    cfg = _cfg()
    _assert_host_role(cfg)
    # Health may be unauthenticated for discovery; auth preferred
    runtime = OllamaNodeRuntime(cfg.ollama_url)
    oh = runtime.health()
    return {
        "ok": True,
        "node_id": cfg.node_id,
        "role": cfg.role,
        "ollama_ok": bool(oh.get("ok")),
        "ollama": oh,
        "lan_ip": local_ip(),
        "node_port": cfg.node_port,
    }


@router.get("/info")
def node_info(authorization: Optional[str] = Header(None)) -> dict[str, Any]:
    cfg = _cfg()
    _assert_host_role(cfg)
    require_bearer(authorization, cfg.auth_token)
    hw = probe_hardware()
    return {
        "node_id": cfg.node_id,
        "role": cfg.role,
        "lan_ip": local_ip(),
        "node_port": cfg.node_port,
        "capabilities": _capabilities(cfg),
        "models": [m.get("id") for m in (cfg.hosted_models or []) if m.get("enabled", True)],
        "hosted_models": cfg.hosted_models,
        "hardware": hw,
        "ollama_url": cfg.ollama_url,
    }


@router.get("/capabilities")
def node_capabilities(authorization: Optional[str] = Header(None)) -> dict[str, Any]:
    cfg = _cfg()
    _assert_host_role(cfg)
    require_bearer(authorization, cfg.auth_token)
    return {
        "node_id": cfg.node_id,
        "capabilities": _capabilities(cfg),
        "models": cfg.hosted_models,
    }


@router.post("/pair", response_model=PairResponse)
def node_pair(body: PairRequest) -> PairResponse:
    cfg = _cfg()
    _assert_host_role(cfg)
    if not body.pairing_code or body.pairing_code.strip() != (cfg.pairing_code or "").strip():
        return PairResponse(
            ok=False,
            node_id=cfg.node_id,
            error=NodeErrorCode.NODE_PAIRING_FAILED.value,
        )
    return PairResponse(
        ok=True,
        node_id=cfg.node_id,
        auth_token=cfg.auth_token,
        capabilities=_capabilities(cfg),
        models=[m.get("id") for m in (cfg.hosted_models or []) if m.get("enabled", True)],
    )


@router.post("/inference", response_model=InferenceResponse)
def node_inference(
    body: InferenceRequest,
    authorization: Optional[str] = Header(None),
) -> InferenceResponse:
    cfg = _cfg()
    _assert_host_role(cfg)
    require_bearer(authorization, cfg.auth_token)

    image_names = [im.filename for im in (body.images or [])]
    logger.info("=" * 64)
    logger.info(f"[{body.request_id}] INCOMING ← Controller inference request")
    logger.info(f"[{body.request_id}]   task={body.task}  model={body.model}")
    logger.info(f"[{body.request_id}]   query={body.query!r}")
    logger.info(f"[{body.request_id}]   images={image_names}")
    logger.info("=" * 64)

    if body.task not in ("vqa", "captioning"):
        return InferenceResponse(
            request_id=body.request_id,
            status="error",
            node_id=cfg.node_id,
            error_code=NodeErrorCode.UNSUPPORTED_TASK.value,
            error=f"Unsupported task: {body.task}",
        )

    tag = _resolve_ollama_tag(cfg, body.model)
    if not tag:
        logger.error(f"[{body.request_id}] MODEL_NOT_AVAILABLE for {body.model}")
        return InferenceResponse(
            request_id=body.request_id,
            status="error",
            node_id=cfg.node_id,
            error_code=NodeErrorCode.MODEL_NOT_AVAILABLE.value,
            error=f"Model not available: {body.model}",
        )

    runtime = OllamaNodeRuntime(cfg.ollama_url, timeout=cfg.remote_timeout_sec)
    oh = runtime.health()
    if not oh.get("ok"):
        logger.error(f"[{body.request_id}] OLLAMA_UNAVAILABLE: {oh}")
        return InferenceResponse(
            request_id=body.request_id,
            status="error",
            node_id=cfg.node_id,
            model=tag,
            error_code=NodeErrorCode.OLLAMA_UNAVAILABLE.value,
            error=str(oh.get("error") or "Ollama unavailable"),
        )

    # Warn if the configured tag is not present locally
    local_models = [str(m).lower() for m in (oh.get("models") or [])]
    if tag.lower() not in local_models and not any(tag.lower() in m for m in local_models):
        logger.warning(
            f"[{body.request_id}] Ollama tag {tag!r} not in local list {oh.get('models')}; "
            "inference may fail — run: ollama pull qwen2.5vl:7b"
        )

    logger.info(f"[{body.request_id}] Running Ollama tag={tag} ...")
    result = runtime.infer(body, node_id=cfg.node_id, ollama_tag=tag)
    if result.status == "success":
        preview = (result.answer or "")[:240]
        logger.info(f"[{body.request_id}] OUTGOING → Controller SUCCESS answer_preview={preview!r}")
    else:
        logger.error(
            f"[{body.request_id}] OUTGOING → Controller FAIL "
            f"{result.error_code}: {result.error}"
        )
    return result
