"""HTTP client from Controller → Model Host."""

from __future__ import annotations

import base64
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx

from app.node.registry import RegisteredNode
from app.node.schemas import ImagePayload, InferenceRequest, InferenceResponse, NodeErrorCode, PairRequest


class NodeClient:
    def __init__(self, timeout: float = 120.0):
        self.timeout = timeout

    def _headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def health(self, node: RegisteredNode) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.get(f"{node.base_url}/node/health", headers=self._headers(node.auth_token))
                if r.status_code != 200:
                    return {"ok": False, "error_code": NodeErrorCode.NODE_UNHEALTHY.value, "detail": r.text}
                return {"ok": True, **r.json()}
        except httpx.TimeoutException:
            return {"ok": False, "error_code": NodeErrorCode.REMOTE_TIMEOUT.value}
        except Exception as exc:
            return {"ok": False, "error_code": NodeErrorCode.REMOTE_CONNECTION_FAILED.value, "detail": str(exc)}

    def info(self, node: RegisteredNode) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=8.0) as client:
                r = client.get(f"{node.base_url}/node/info", headers=self._headers(node.auth_token))
                r.raise_for_status()
                return r.json()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def pair(self, address: str, port: int, pairing_code: str, controller_node_id: Optional[str] = None) -> dict[str, Any]:
        url = f"http://{address}:{port}/node/pair"
        body = PairRequest(pairing_code=pairing_code, controller_node_id=controller_node_id).model_dump()
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.post(url, json=body)
                data = r.json() if r.content else {}
                if r.status_code != 200 or not data.get("ok"):
                    return {
                        "ok": False,
                        "error_code": NodeErrorCode.NODE_PAIRING_FAILED.value,
                        "detail": data.get("error") or r.text,
                    }
                return data
        except Exception as exc:
            return {
                "ok": False,
                "error_code": NodeErrorCode.REMOTE_CONNECTION_FAILED.value,
                "detail": str(exc),
            }

    def infer(self, node: RegisteredNode, req: InferenceRequest) -> InferenceResponse:
        url = f"{node.base_url}/node/inference"
        try:
            with httpx.Client(timeout=req.timeout or self.timeout) as client:
                r = client.post(url, json=req.model_dump(), headers=self._headers(node.auth_token))
                if r.status_code == 401:
                    return InferenceResponse(
                        request_id=req.request_id,
                        status="error",
                        node_id=node.node_id,
                        error_code=NodeErrorCode.NODE_AUTH_FAILED.value,
                        error="Auth failed",
                    )
                if r.status_code != 200:
                    return InferenceResponse(
                        request_id=req.request_id,
                        status="error",
                        node_id=node.node_id,
                        error_code=NodeErrorCode.REMOTE_INFERENCE_FAILED.value,
                        error=f"HTTP {r.status_code}: {r.text[:300]}",
                    )
                return InferenceResponse.model_validate(r.json())
        except httpx.TimeoutException:
            return InferenceResponse(
                request_id=req.request_id,
                status="error",
                node_id=node.node_id,
                error_code=NodeErrorCode.REMOTE_TIMEOUT.value,
                error="Remote inference timed out",
            )
        except Exception as exc:
            return InferenceResponse(
                request_id=req.request_id,
                status="error",
                node_id=node.node_id,
                error_code=NodeErrorCode.REMOTE_CONNECTION_FAILED.value,
                error=str(exc),
            )


def file_to_image_payload(path: Path, modality: Optional[str] = None) -> ImagePayload:
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    suffix = path.suffix.lower()
    ctype = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")
    return ImagePayload(filename=path.name, content_type=ctype, data_b64=b64, modality=modality)


def make_inference_request(
    task: str,
    query: str,
    images: list[ImagePayload],
    *,
    model: str = "qwen-vl",
    timeout: float = 120.0,
    metadata: Optional[dict] = None,
) -> InferenceRequest:
    return InferenceRequest(
        request_id=str(uuid.uuid4()),
        task=task,
        model=model,
        query=query,
        images=images,
        metadata=metadata or {},
        timeout=timeout,
    )
