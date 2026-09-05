"""Ollama-backed vision/text runtime for Model Host nodes."""

from __future__ import annotations

import base64
import io
import time
from typing import Any, Optional

import httpx
from PIL import Image

from app.node.schemas import ImagePayload, InferenceRequest, InferenceResponse, NodeErrorCode

# Ollama VLMs reject GeoTIFF / exotic formats; also choke on huge rasters.
_MAX_EDGE_PX = 1536


def _to_ollama_png_b64(raw_b64: str, *, filename: str = "") -> str:
    """Decode any transfer payload → RGB PNG base64 Ollama can load."""
    raw = raw_b64
    if "," in raw and raw.strip().startswith("data:"):
        raw = raw.split(",", 1)[1]
    try:
        data = base64.b64decode(raw, validate=False)
    except Exception as exc:
        raise ValueError(f"IMAGE_TRANSFER_FAILED: bad base64 ({exc})") from exc

    try:
        with Image.open(io.BytesIO(data)) as im:
            # Multi-band / 16-bit GeoTIFF → displayable RGB
            im = im.convert("RGB")
            w, h = im.size
            scale = min(1.0, _MAX_EDGE_PX / float(max(w, h, 1)))
            if scale < 1.0:
                im = im.resize(
                    (max(1, int(w * scale)), max(1, int(h * scale))),
                    Image.Resampling.LANCZOS,
                )
            buf = io.BytesIO()
            im.save(buf, format="PNG", optimize=True)
            return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception as exc:
        raise ValueError(
            f"IMAGE_TRANSFER_FAILED: cannot convert {filename or 'image'} "
            f"to PNG for Ollama ({exc})"
        ) from exc


class OllamaNodeRuntime:
    """Thin client around local Ollama for VQA / captioning on Model Host."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.get(f"{self.base_url}/api/tags")
                if r.status_code != 200:
                    return {"ok": False, "error": f"HTTP {r.status_code}"}
                tags = [m.get("name") for m in r.json().get("models", [])]
                return {"ok": True, "models": tags}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def list_models(self) -> list[str]:
        h = self.health()
        return list(h.get("models") or []) if h.get("ok") else []

    def _images_b64(self, images: list[ImagePayload]) -> list[str]:
        out: list[str] = []
        for img in images:
            out.append(_to_ollama_png_b64(img.data_b64, filename=img.filename or ""))
        return out

    def infer(
        self,
        req: InferenceRequest,
        *,
        node_id: str,
        ollama_tag: str,
    ) -> InferenceResponse:
        started = time.perf_counter()
        try:
            images = self._images_b64(req.images)
        except ValueError as exc:
            return InferenceResponse(
                request_id=req.request_id,
                status="error",
                node_id=node_id,
                model=ollama_tag,
                error_code=NodeErrorCode.IMAGE_TRANSFER_FAILED.value,
                error=str(exc),
            )

        prompt = req.query
        if req.task == "captioning" and not prompt.strip():
            prompt = "Describe this satellite / remote-sensing image in detail."

        payload: dict[str, Any] = {
            "model": ollama_tag,
            "prompt": prompt,
            "stream": False,
            "images": images,
        }

        try:
            with httpx.Client(timeout=req.timeout or self.timeout) as client:
                r = client.post(f"{self.base_url}/api/generate", json=payload)
                if r.status_code != 200:
                    return InferenceResponse(
                        request_id=req.request_id,
                        status="error",
                        node_id=node_id,
                        model=ollama_tag,
                        error_code=NodeErrorCode.REMOTE_INFERENCE_FAILED.value,
                        error=f"Ollama HTTP {r.status_code}: {r.text[:300]}",
                    )
                data = r.json()
                answer = (data.get("response") or "").strip()
                if not answer:
                    return InferenceResponse(
                        request_id=req.request_id,
                        status="error",
                        node_id=node_id,
                        model=ollama_tag,
                        error_code=NodeErrorCode.REMOTE_RESPONSE_INVALID.value,
                        error="Empty Ollama response",
                    )
                elapsed = time.perf_counter() - started
                return InferenceResponse(
                    request_id=req.request_id,
                    status="success",
                    answer=answer,
                    confidence=None,
                    node_id=node_id,
                    runtime="ollama",
                    model=ollama_tag,
                    execution="REMOTE",
                    telemetry={"latency_sec": round(elapsed, 3), "eval_count": data.get("eval_count")},
                )
        except httpx.TimeoutException:
            return InferenceResponse(
                request_id=req.request_id,
                status="error",
                node_id=node_id,
                model=ollama_tag,
                error_code=NodeErrorCode.REMOTE_TIMEOUT.value,
                error="Ollama inference timed out",
            )
        except Exception as exc:
            return InferenceResponse(
                request_id=req.request_id,
                status="error",
                node_id=node_id,
                model=ollama_tag,
                error_code=NodeErrorCode.OLLAMA_UNAVAILABLE.value,
                error=str(exc),
            )
