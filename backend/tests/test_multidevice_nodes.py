"""Tests for multi-device role config, host API, pairing, and remote bridge."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.node.config_store import (
    DEFAULT_HOST_VLM_OLLAMA_TAG,
    DeviceRole,
    QWEN_VL_MODEL_ID,
    clear_device_config,
    load_device_config,
    new_device_config,
    save_device_config,
)
from app.node.host_routes import router as host_router
from app.node.registry import RegisteredNode, get_registry
from app.node.schemas import ImagePayload, InferenceRequest, NodeErrorCode
from app.api.node_controller import router as nodes_router


@pytest.fixture(autouse=True)
def _isolate_device_config(tmp_path, monkeypatch):
    """Keep tests from touching the real .satquery/device.json."""
    monkeypatch.setattr(
        "app.node.config_store.satquery_dir",
        lambda: tmp_path / ".satquery",
    )
    (tmp_path / ".satquery").mkdir(parents=True, exist_ok=True)
    # Reset registry singleton
    import app.node.registry as reg_mod

    reg_mod._registry = None
    yield
    reg_mod._registry = None


def test_role_persists_and_can_change(tmp_path):
    cfg = new_device_config(DeviceRole.CONTROLLER)
    save_device_config(cfg)
    loaded = load_device_config()
    assert loaded is not None
    assert loaded.role == "controller"

    cfg2 = new_device_config(DeviceRole.MODEL_HOST, hosted_qwen_vl=True)
    save_device_config(cfg2)
    loaded2 = load_device_config()
    assert loaded2.role == "model_host"
    assert loaded2.hosted_models[0]["ollama_tag"] == DEFAULT_HOST_VLM_OLLAMA_TAG
    assert loaded2.hosted_models[0]["id"] == QWEN_VL_MODEL_ID

    clear_device_config()
    assert load_device_config() is None


def test_invalid_role_rejected_via_api():
    save_device_config(new_device_config(DeviceRole.CONTROLLER))
    app = FastAPI()
    app.include_router(nodes_router, prefix="/api")
    client = TestClient(app)
    r = client.post("/api/nodes/role", json={"role": "spaceship"})
    assert r.status_code == 400


def test_host_health_info_pair_inference_auth():
    cfg = new_device_config(DeviceRole.MODEL_HOST, hosted_qwen_vl=True)
    save_device_config(cfg)

    app = FastAPI()
    app.include_router(host_router)
    client = TestClient(app)

    h = client.get("/node/health")
    assert h.status_code == 200
    assert h.json()["node_id"] == cfg.node_id

    # info requires auth
    bad = client.get("/node/info")
    assert bad.status_code == 401

    good = client.get(
        "/node/info",
        headers={"Authorization": f"Bearer {cfg.auth_token}"},
    )
    assert good.status_code == 200
    body = good.json()
    assert "vqa" in body["capabilities"]
    assert QWEN_VL_MODEL_ID in body["models"]

    fail_pair = client.post("/node/pair", json={"pairing_code": "000000"})
    assert fail_pair.status_code == 200
    assert fail_pair.json()["ok"] is False

    ok_pair = client.post("/node/pair", json={"pairing_code": cfg.pairing_code})
    assert ok_pair.json()["ok"] is True
    assert ok_pair.json()["auth_token"] == cfg.auth_token

    tiny = base64.b64encode(b"fakepng").decode("ascii")
    req = {
        "request_id": "req-abc",
        "task": "captioning",
        "model": QWEN_VL_MODEL_ID,
        "query": "Describe this image.",
        "images": [
            {
                "filename": "x.png",
                "content_type": "image/png",
                "data_b64": tiny,
            }
        ],
        "timeout": 5.0,
    }

    # Auth failure
    unauth = client.post("/node/inference", json=req)
    assert unauth.status_code == 401

    with patch("app.node.host_routes.OllamaNodeRuntime") as RT:
        inst = RT.return_value
        inst.health.return_value = {"ok": True, "models": [DEFAULT_HOST_VLM_OLLAMA_TAG]}
        from app.node.schemas import InferenceResponse

        inst.infer.return_value = InferenceResponse(
            request_id="req-abc",
            status="success",
            answer="A satellite scene with fields.",
            node_id=cfg.node_id,
            runtime="ollama",
            model=DEFAULT_HOST_VLM_OLLAMA_TAG,
            execution="REMOTE",
        )
        resp = client.post(
            "/node/inference",
            json=req,
            headers={"Authorization": f"Bearer {cfg.auth_token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == "req-abc"
    assert data["status"] == "success"
    assert data["model"] == DEFAULT_HOST_VLM_OLLAMA_TAG
    assert "satellite" in data["answer"].lower()


def test_ollama_offline_structured_error():
    cfg = new_device_config(DeviceRole.MODEL_HOST, hosted_qwen_vl=True)
    save_device_config(cfg)
    app = FastAPI()
    app.include_router(host_router)
    client = TestClient(app)

    tiny = base64.b64encode(b"x").decode("ascii")
    req = {
        "request_id": "r1",
        "task": "vqa",
        "model": "qwen-vl",
        "query": "What is this?",
        "images": [{"filename": "a.png", "content_type": "image/png", "data_b64": tiny}],
    }
    with patch("app.node.host_routes.OllamaNodeRuntime") as RT:
        RT.return_value.health.return_value = {"ok": False, "error": "connection refused"}
        resp = client.post(
            "/node/inference",
            json=req,
            headers={"Authorization": f"Bearer {cfg.auth_token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["error_code"] == NodeErrorCode.OLLAMA_UNAVAILABLE.value


def test_controller_pair_and_registry():
    # Host side
    host_cfg = new_device_config(DeviceRole.MODEL_HOST, hosted_qwen_vl=True)
    # Controller side config in same tmp dir — simulate by saving controller after host pair mock
    save_device_config(new_device_config(DeviceRole.CONTROLLER))

    app = FastAPI()
    app.include_router(nodes_router, prefix="/api")
    client = TestClient(app)

    with patch("app.api.node_controller.NodeClient") as NC:
        NC.return_value.pair.return_value = {
            "ok": True,
            "node_id": host_cfg.node_id,
            "auth_token": host_cfg.auth_token,
            "capabilities": ["vqa", "captioning"],
            "models": ["qwen-vl"],
        }
        r = client.post(
            "/api/nodes/pair",
            json={"address": "192.168.1.50", "port": 8100, "pairing_code": host_cfg.pairing_code},
        )
    assert r.status_code == 200
    assert r.json()["ok"] is True

    st = client.get("/api/nodes/status")
    assert st.status_code == 200
    nodes = st.json()["nodes"]
    assert len(nodes) == 1
    assert nodes[0]["node_id"] == host_cfg.node_id


def test_registry_finds_qwen_capable_node_not_by_hostname():
    save_device_config(new_device_config(DeviceRole.CONTROLLER))
    reg = get_registry()
    reg.upsert(
        RegisteredNode(
            node_id="SAT-ANY-0001",
            address="10.0.0.9",
            port=8100,
            auth_token="tok",
            capabilities=["vqa", "captioning"],
            models=["qwen-vl"],
            healthy=True,
        ),
        persist=True,
    )
    found = reg.find_for_task("vqa", "qwen-vl")
    assert found is not None
    assert found.node_id == "SAT-ANY-0001"


def test_hybrid_executor_remote_success(tmp_path):
    from app.agent.hybrid_executor import HybridPipelineExecutor
    from app.node.schemas import InferenceResponse

    save_device_config(new_device_config(DeviceRole.CONTROLLER))
    reg = get_registry()
    reg.upsert(
        RegisteredNode(
            node_id="SAT-HOST-1",
            address="127.0.0.1",
            port=8100,
            auth_token="t",
            capabilities=["captioning", "vqa"],
            models=["qwen-vl"],
            healthy=True,
        ),
        persist=False,
    )

    img = tmp_path / "sat.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

    with patch("app.agent.hybrid_executor.try_remote_vlm") as remote:
        remote.return_value = InferenceResponse(
            request_id="rid-1",
            status="success",
            answer="Urban grid with river.",
            node_id="SAT-HOST-1",
            runtime="ollama",
            model=DEFAULT_HOST_VLM_OLLAMA_TAG,
            execution="REMOTE",
        )
        results = HybridPipelineExecutor(skip_local_inference=True).execute(
            [{"step": 1, "model": "rs_vlm", "action": "generate_caption"}],
            [str(img)],
            "Describe this image.",
            "demo",
        )
    assert len(results) == 1
    assert results[0].success is True
    assert results[0].output["execution"] == "REMOTE"
    assert results[0].telemetry["model"] == DEFAULT_HOST_VLM_OLLAMA_TAG
    assert results[0].output["answer"].startswith("Urban")


def test_default_host_vlm_tag_is_pullable_qwen_vl():
    assert "qwen2.5vl" in DEFAULT_HOST_VLM_OLLAMA_TAG.lower()
    assert "Qwen2.5-VL-7B-Instruct-GGUF:Q4_K_M" != DEFAULT_HOST_VLM_OLLAMA_TAG
