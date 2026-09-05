"""Node schemas and error codes for distributed SatQuery."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class NodeErrorCode(str, Enum):
    NODE_NOT_FOUND = "NODE_NOT_FOUND"
    NODE_OFFLINE = "NODE_OFFLINE"
    NODE_UNHEALTHY = "NODE_UNHEALTHY"
    NODE_PAIRING_FAILED = "NODE_PAIRING_FAILED"
    NODE_AUTH_FAILED = "NODE_AUTH_FAILED"
    MODEL_NOT_AVAILABLE = "MODEL_NOT_AVAILABLE"
    OLLAMA_UNAVAILABLE = "OLLAMA_UNAVAILABLE"
    REMOTE_CONNECTION_FAILED = "REMOTE_CONNECTION_FAILED"
    REMOTE_TIMEOUT = "REMOTE_TIMEOUT"
    REMOTE_INFERENCE_FAILED = "REMOTE_INFERENCE_FAILED"
    REMOTE_RESPONSE_INVALID = "REMOTE_RESPONSE_INVALID"
    IMAGE_TRANSFER_FAILED = "IMAGE_TRANSFER_FAILED"
    UNSUPPORTED_TASK = "UNSUPPORTED_TASK"


class ImagePayload(BaseModel):
    filename: str = "image.png"
    content_type: str = "application/octet-stream"
    # base64-encoded bytes — never filesystem paths
    data_b64: str
    modality: Optional[str] = None


class InferenceRequest(BaseModel):
    request_id: str
    task: str  # vqa | captioning
    model: str = "qwen-vl"
    query: str
    images: list[ImagePayload] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timeout: float = 120.0


class InferenceResponse(BaseModel):
    request_id: str
    status: str  # success | error
    answer: Optional[str] = None
    confidence: Optional[float] = None
    node_id: str
    runtime: str = "ollama"
    model: Optional[str] = None
    execution: str = "REMOTE"
    error_code: Optional[str] = None
    error: Optional[str] = None
    telemetry: Optional[dict[str, Any]] = None


class PairRequest(BaseModel):
    pairing_code: str
    controller_node_id: Optional[str] = None


class PairResponse(BaseModel):
    ok: bool
    node_id: str
    auth_token: Optional[str] = None
    capabilities: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)
    error: Optional[str] = None
