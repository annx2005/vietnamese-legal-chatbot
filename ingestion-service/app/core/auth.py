import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.core.config import settings
from fastapi import Header, HTTPException


def _decode_base64url(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(signing_input: str) -> str:
    digest = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def _decode_jwt(authorization: str | None) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid bearer token")
    signing_input = f"{parts[0]}.{parts[1]}"
    if not hmac.compare_digest(parts[2], _sign(signing_input)):
        raise HTTPException(status_code=401, detail="Invalid bearer token")
    try:
        payload = json.loads(_decode_base64url(parts[1]))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid bearer token") from exc
    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=401, detail="Expired bearer token")
    return payload


def require_admin(authorization: str | None = Header(default=None)) -> None:
    payload = _decode_jwt(authorization)
    if payload.get("role") != "ROLE_ADMIN":
        raise HTTPException(status_code=403, detail="Admin role is required")
