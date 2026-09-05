"""Controller-side registry of paired Model Hosts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.node.config_store import DeviceConfig, load_device_config, save_device_config
from app.node.schemas import NodeErrorCode


@dataclass
class RegisteredNode:
    node_id: str
    address: str
    port: int
    auth_token: str
    capabilities: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    healthy: Optional[bool] = None
    last_error: Optional[str] = None

    @property
    def base_url(self) -> str:
        return f"http://{self.address}:{self.port}"


class NodeRegistry:
    """In-memory view backed by DeviceConfig.paired_hosts."""

    def __init__(self) -> None:
        self._nodes: dict[str, RegisteredNode] = {}
        self.reload()

    def reload(self) -> None:
        self._nodes.clear()
        cfg = load_device_config()
        if not cfg:
            return
        for h in cfg.paired_hosts or []:
            nid = h.get("node_id") or f"{h.get('address')}:{h.get('port')}"
            self._nodes[nid] = RegisteredNode(
                node_id=nid,
                address=str(h.get("address")),
                port=int(h.get("port", 8100)),
                auth_token=str(h.get("auth_token", "")),
                capabilities=list(h.get("capabilities") or []),
                models=list(h.get("models") or []),
            )

    def list_nodes(self) -> list[RegisteredNode]:
        return list(self._nodes.values())

    def get(self, node_id: str) -> Optional[RegisteredNode]:
        return self._nodes.get(node_id)

    def find_for_task(self, task: str, model: str = "qwen-vl") -> Optional[RegisteredNode]:
        """Pick first healthy-or-unknown host advertising the task/model."""
        for n in self._nodes.values():
            caps = n.capabilities or []
            models = n.models or []
            if task in caps or model in models or "vqa" in caps or not caps:
                if n.healthy is False:
                    continue
                return n
        # Fall back to first registered even if unhealthy unknown
        for n in self._nodes.values():
            return n
        return None

    def upsert(self, node: RegisteredNode, persist: bool = True) -> None:
        self._nodes[node.node_id] = node
        if persist:
            self._persist()

    def remove(self, node_id: str, persist: bool = True) -> bool:
        if node_id not in self._nodes:
            return False
        del self._nodes[node_id]
        if persist:
            self._persist()
        return True

    def _persist(self) -> None:
        cfg = load_device_config()
        if not cfg:
            return
        cfg.paired_hosts = [
            {
                "node_id": n.node_id,
                "address": n.address,
                "port": n.port,
                "auth_token": n.auth_token,
                "capabilities": n.capabilities,
                "models": n.models,
            }
            for n in self._nodes.values()
        ]
        save_device_config(cfg)

    def status_payload(self) -> dict[str, Any]:
        return {
            "nodes": [
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
                for n in self._nodes.values()
            ]
        }


_registry: Optional[NodeRegistry] = None


def get_registry(*, reload: bool = False) -> NodeRegistry:
    global _registry
    if _registry is None:
        _registry = NodeRegistry()
    elif reload:
        _registry.reload()
    return _registry
