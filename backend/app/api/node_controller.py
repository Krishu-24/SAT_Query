"""Controller-facing node management API (pairing, status, health)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.node.bridge import refresh_all_node_health, role_is_model_host_only
from app.node.client import NodeClient
from app.node.config_store import (
    DeviceRole,
    clear_device_config,
    config_summary,
    load_device_config,
    local_ip,
    new_device_config,
    save_device_config,
)
from app.node.registry import RegisteredNode, get_registry
from app.node.schemas import NodeErrorCode

router = APIRouter(prefix="/nodes", tags=["nodes"])


class PairBody(BaseModel):
    address: str
    port: int = 8100
    pairing_code: str


class RoleBody(BaseModel):
    role: str
    host_qwen_vl: bool = True


@router.get("/status")
def nodes_status() -> dict[str, Any]:
    cfg = load_device_config()
    summary = config_summary(cfg) if cfg else {"role": None, "node_id": None}
    # Reload from disk so CLI pairing is visible without restarting uvicorn
    reg = get_registry(reload=True)
    nodes = reg.status_payload().get("nodes", [])
    # Soft health probe for UI (non-fatal)
    client = NodeClient(timeout=5.0)
    enriched = []
    any_ready = False
    for n in reg.list_nodes():
        h = client.health(n)
        n.healthy = bool(h.get("ok"))
        if n.healthy:
            any_ready = True
            info = client.info(n)
            if isinstance(info, dict):
                if info.get("capabilities"):
                    n.capabilities = list(info.get("capabilities") or n.capabilities)
                if info.get("models"):
                    n.models = list(info.get("models") or n.models)
        else:
            n.last_error = h.get("error_code") or str(h.get("detail") or "offline")
        enriched.append(
            {
                "node_id": n.node_id,
                "address": n.address,
                "port": n.port,
                "capabilities": n.capabilities,
                "models": n.models,
                "healthy": n.healthy,
                "last_error": n.last_error,
                "base_url": n.base_url,
            }
        )
    return {
        "device": summary,
        "lan_ip": local_ip(),
        "nodes": enriched or nodes,
        "model_host_only": role_is_model_host_only(),
        "model_host_connected": any_ready,
        "vlm_ready": any(
            n.get("healthy")
            and (
                "qwen-vl" in (n.get("models") or [])
                or "vqa" in (n.get("capabilities") or [])
                or "captioning" in (n.get("capabilities") or [])
            )
            for n in (enriched or nodes)
        ),
    }


@router.post("/refresh")
def nodes_refresh() -> dict[str, Any]:
    return refresh_all_node_health()


@router.post("/pair")
def nodes_pair(body: PairBody) -> dict[str, Any]:
    cfg = load_device_config()
    if cfg and cfg.role == DeviceRole.MODEL_HOST.value:
        raise HTTPException(status_code=403, detail="Model Host cannot pair outbound")

    client = NodeClient()
    controller_id = cfg.node_id if cfg else None
    result = client.pair(body.address.strip(), int(body.port), body.pairing_code.strip(), controller_id)
    if not result.get("ok"):
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": result.get("error_code") or NodeErrorCode.NODE_PAIRING_FAILED.value,
                "detail": result.get("detail") or result.get("error"),
            },
        )

    node = RegisteredNode(
        node_id=str(result.get("node_id")),
        address=body.address.strip(),
        port=int(body.port),
        auth_token=str(result.get("auth_token") or ""),
        capabilities=list(result.get("capabilities") or []),
        models=list(result.get("models") or []),
        healthy=True,
    )
    get_registry().upsert(node, persist=True)

    # Ensure controller has a device config so pairing persists with a role
    if not cfg:
        cfg = new_device_config(DeviceRole.CONTROLLER)
        save_device_config(cfg)
        get_registry().reload()
        get_registry().upsert(node, persist=True)

    return {"ok": True, "node": {
        "node_id": node.node_id,
        "address": node.address,
        "port": node.port,
        "capabilities": node.capabilities,
        "models": node.models,
    }}


@router.delete("/{node_id}")
def nodes_unpair(node_id: str) -> dict[str, Any]:
    ok = get_registry().remove(node_id, persist=True)
    if not ok:
        raise HTTPException(status_code=404, detail=NodeErrorCode.NODE_NOT_FOUND.value)
    return {"ok": True, "removed": node_id}


@router.post("/role")
def set_role(body: RoleBody) -> dict[str, Any]:
    role_map = {
        "controller": DeviceRole.CONTROLLER,
        "1": DeviceRole.CONTROLLER,
        "model_host": DeviceRole.MODEL_HOST,
        "model-host": DeviceRole.MODEL_HOST,
        "2": DeviceRole.MODEL_HOST,
        "full_system": DeviceRole.FULL_SYSTEM,
        "full-system": DeviceRole.FULL_SYSTEM,
        "3": DeviceRole.FULL_SYSTEM,
    }
    key = body.role.strip().lower().replace(" ", "_")
    if key not in role_map:
        raise HTTPException(status_code=400, detail="Invalid role")
    # Preserve paired hosts when changing away from model_host if possible
    prev = load_device_config()
    paired = list(prev.paired_hosts) if prev else []
    cfg = new_device_config(role_map[key], hosted_qwen_vl=body.host_qwen_vl)
    if role_map[key] != DeviceRole.MODEL_HOST:
        cfg.paired_hosts = paired
    save_device_config(cfg)
    get_registry().reload()
    return config_summary(cfg)


@router.post("/role/reset")
def reset_role() -> dict[str, Any]:
    clear_device_config()
    get_registry().reload()
    return {"ok": True, "cleared": True}
