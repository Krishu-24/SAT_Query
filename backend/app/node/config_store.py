"""
Local device role / pairing configuration.

Persisted under `<repo>/.satquery/device.json` (gitignored).
Never commit secrets or machine-specific IPs.
"""

from __future__ import annotations

import json
import secrets
import socket
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


# Logical model id used by the controller/router when requesting VQA/captioning.
QWEN_VL_MODEL_ID = "qwen-vl"
# Ollama registry tag for Model Host VQA/captioning.
# NOTE: "Qwen2.5-VL-7B-Instruct-GGUF:Q4_K_M" is NOT an Ollama library name
# (pull fails with "file does not exist"). The official vision package is:
DEFAULT_HOST_VLM_OLLAMA_TAG = "qwen2.5vl:7b"
# Human-facing label (GGUF Q4_K_M is the quantization class the team targets;
# Ollama's qwen2.5vl:7b is the pullable runtime that serves the same model family).
HOST_VLM_DISPLAY_NAME = "Qwen2.5-VL-7B-Instruct (qwen2.5vl:7b / Q4-class)"
# Alternate tags tried if the default is missing locally (first local match wins).
HOST_VLM_OLLAMA_FALLBACKS = (
    "qwen2.5vl:7b",
    "qwen2.5vl:latest",
    "qwen2.5vl",
    "hf.co/bartowski/Qwen_Qwen2.5-VL-7B-Instruct-GGUF:Q4_K_M",
)


class DeviceRole(str, Enum):
    CONTROLLER = "controller"
    MODEL_HOST = "model_host"
    FULL_SYSTEM = "full_system"


def repo_root() -> Path:
    # backend/app/node/config_store.py -> parents[3] == repo root
    return Path(__file__).resolve().parents[3]


def satquery_dir() -> Path:
    d = repo_root() / ".satquery"
    d.mkdir(parents=True, exist_ok=True)
    return d


def device_config_path() -> Path:
    return satquery_dir() / "device.json"


def _default_node_id() -> str:
    host = socket.gethostname().split(".")[0].upper()[:12] or "NODE"
    suffix = uuid.uuid4().hex[:4].upper()
    return f"SAT-{host}-{suffix}"


@dataclass
class HostedModel:
    id: str
    tasks: list[str]
    ollama_tag: str
    enabled: bool = True


@dataclass
class PairedHost:
    node_id: str
    address: str
    port: int
    auth_token: str
    capabilities: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)


@dataclass
class DeviceConfig:
    role: str
    node_id: str
    port: int = 8000
    node_port: int = 8100
    ollama_url: str = "http://127.0.0.1:11434"
    planner_model: str = "qwen3:4b-instruct"
    hosted_models: list[dict] = field(default_factory=list)
    pairing_code: str = ""
    auth_token: str = ""
    paired_hosts: list[dict] = field(default_factory=list)
    controller_address: str = ""
    remote_timeout_sec: float = 120.0
    version: int = 1

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DeviceConfig":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


def load_device_config() -> Optional[DeviceConfig]:
    path = device_config_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cfg = DeviceConfig.from_dict(data)
        # Soft-migrate invalid / non-registry host VLM tags → pullable Ollama tag
        changed = False
        for m in cfg.hosted_models or []:
            if m.get("id") != QWEN_VL_MODEL_ID:
                continue
            tag = (m.get("ollama_tag") or "").strip()
            if tag in (
                "",
                "Qwen2.5-VL-7B-Instruct-GGUF:Q4_K_M",
                "qwen2.5vl",
            ):
                m["ollama_tag"] = DEFAULT_HOST_VLM_OLLAMA_TAG
                changed = True
        if changed:
            save_device_config(cfg)
        return cfg
    except Exception:
        return None


def save_device_config(cfg: DeviceConfig) -> Path:
    path = device_config_path()
    path.write_text(json.dumps(cfg.to_dict(), indent=2), encoding="utf-8")
    return path


def clear_device_config() -> bool:
    path = device_config_path()
    if path.is_file():
        path.unlink()
        return True
    return False


def new_device_config(role: DeviceRole, *, hosted_qwen_vl: bool = False) -> DeviceConfig:
    token = secrets.token_urlsafe(24)
    code = f"{secrets.randbelow(1_000_000):06d}"
    hosted: list[dict] = []
    if role in (DeviceRole.MODEL_HOST, DeviceRole.FULL_SYSTEM) and hosted_qwen_vl:
        hosted.append(
            asdict(
                HostedModel(
                    id=QWEN_VL_MODEL_ID,
                    tasks=["vqa", "captioning"],
                    ollama_tag=DEFAULT_HOST_VLM_OLLAMA_TAG,
                    enabled=True,
                )
            )
        )
    port = 8000 if role != DeviceRole.MODEL_HOST else 8100
    node_port = 8100
    return DeviceConfig(
        role=role.value,
        node_id=_default_node_id(),
        port=port,
        node_port=node_port,
        pairing_code=code,
        auth_token=token,
        hosted_models=hosted,
    )


def local_ip() -> str:
    """Best-effort LAN IP (not 127.0.0.1)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def config_summary(cfg: DeviceConfig) -> dict[str, Any]:
    return {
        "role": cfg.role,
        "node_id": cfg.node_id,
        "port": cfg.port,
        "node_port": cfg.node_port,
        "paired_hosts": [
            {
                "node_id": h.get("node_id"),
                "address": h.get("address"),
                "port": h.get("port"),
                "capabilities": h.get("capabilities", []),
                "models": h.get("models", []),
            }
            for h in (cfg.paired_hosts or [])
        ],
        "hosted_models": cfg.hosted_models,
    }
