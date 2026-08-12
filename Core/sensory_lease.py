"""Short-lived signed leases for person-bound ephemeral sensory work."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Callable


LEASE_VERSION = 1
MAX_LEASE_SECONDS = 300


class SensoryLeaseError(ValueError):
    """Raised when a sensory lease is missing, invalid, expired, or misbound."""


def _secret_bytes(secret: str | bytes) -> bytes:
    raw = secret if isinstance(secret, bytes) else str(secret or "").encode("utf-8")
    if len(raw) < 32:
        raise SensoryLeaseError("sensory lease secret must contain at least 32 bytes")
    return raw


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    text = str(value or "").strip()
    if not text or len(text) > 4096:
        raise SensoryLeaseError("sensory lease encoding is invalid")
    try:
        return base64.urlsafe_b64decode(text + ("=" * (-len(text) % 4)))
    except Exception as exc:
        raise SensoryLeaseError("sensory lease encoding is invalid") from exc


def issue_sensory_lease(
    secret: str | bytes,
    *,
    person_id: str,
    activation_revision: str,
    ttl_seconds: int = 90,
    clock: Callable[[], float] = time.time,
    nonce: str | None = None,
) -> str:
    """Return a signed, short-lived lease without persisting person data."""

    person = str(person_id or "").strip()
    revision = str(activation_revision or "").strip()
    if not person or not revision:
        raise SensoryLeaseError("person_id and activation_revision are required")
    ttl = int(ttl_seconds)
    if ttl < 1 or ttl > MAX_LEASE_SECONDS:
        raise SensoryLeaseError(f"ttl_seconds must be between 1 and {MAX_LEASE_SECONDS}")
    issued_at = int(clock())
    payload = {
        "v": LEASE_VERSION,
        "person_id": person,
        "activation_revision": revision,
        "issued_at": issued_at,
        "expires_at": issued_at + ttl,
        "nonce": str(nonce or secrets.token_urlsafe(18)),
    }
    encoded_payload = _b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    signature = hmac.new(_secret_bytes(secret), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded_payload}.{_b64encode(signature)}"


def validate_sensory_lease(
    token: str,
    secret: str | bytes,
    *,
    expected_person_id: str,
    expected_activation_revision: str,
    clock: Callable[[], float] = time.time,
) -> dict[str, Any]:
    """Validate signature, expiry, and exact person/activation binding."""

    parts = str(token or "").strip().split(".")
    if len(parts) != 2:
        raise SensoryLeaseError("sensory lease format is invalid")
    encoded_payload, encoded_signature = parts
    supplied_signature = _b64decode(encoded_signature)
    expected_signature = hmac.new(
        _secret_bytes(secret), encoded_payload.encode("ascii"), hashlib.sha256
    ).digest()
    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise SensoryLeaseError("sensory lease signature is invalid")
    try:
        payload = json.loads(_b64decode(encoded_payload).decode("utf-8"))
    except Exception as exc:
        raise SensoryLeaseError("sensory lease payload is invalid") from exc
    if not isinstance(payload, dict) or payload.get("v") != LEASE_VERSION:
        raise SensoryLeaseError("sensory lease version is invalid")
    person = str(expected_person_id or "").strip()
    revision = str(expected_activation_revision or "").strip()
    if not person or not revision:
        raise SensoryLeaseError("expected person and activation revision are required")
    if not hmac.compare_digest(str(payload.get("person_id") or ""), person):
        raise SensoryLeaseError("sensory lease belongs to a different person")
    if not hmac.compare_digest(str(payload.get("activation_revision") or ""), revision):
        raise SensoryLeaseError("sensory lease belongs to a different activation")
    try:
        issued_at = int(payload.get("issued_at"))
        expires_at = int(payload.get("expires_at"))
    except (TypeError, ValueError) as exc:
        raise SensoryLeaseError("sensory lease time fields are invalid") from exc
    now = int(clock())
    if issued_at > now + 5:
        raise SensoryLeaseError("sensory lease was issued in the future")
    if expires_at <= now:
        raise SensoryLeaseError("sensory lease expired")
    if expires_at - issued_at < 1 or expires_at - issued_at > MAX_LEASE_SECONDS:
        raise SensoryLeaseError("sensory lease lifetime is invalid")
    if not str(payload.get("nonce") or "").strip():
        raise SensoryLeaseError("sensory lease nonce is missing")
    return dict(payload)

