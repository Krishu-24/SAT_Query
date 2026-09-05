"""Auth helpers for node pairing."""

from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException


def require_bearer(authorization: Optional[str], expected_token: str) -> None:
    if not expected_token:
        raise HTTPException(status_code=503, detail="Node auth not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="NODE_AUTH_FAILED")
    token = authorization[len("Bearer ") :].strip()
    if token != expected_token:
        raise HTTPException(status_code=401, detail="NODE_AUTH_FAILED")


def bearer_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[len("Bearer ") :].strip()
