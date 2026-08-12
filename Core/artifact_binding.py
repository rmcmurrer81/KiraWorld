"""Deterministic SHA-256 bindings for generated review artifacts.

The binding is deliberately small: every input artifact is hashed separately,
then the named hashes and stable metadata are hashed again as canonical JSON.
This makes it possible to prove which transcript, speech payload, voice
references, and output WAV belonged to one render without trusting filenames.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(encoded)


def bind_artifact_hashes(
    artifacts: Mapping[str, str],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind already-computed hashes, rejecting ambiguous or malformed input."""

    if not artifacts:
        raise ValueError("At least one artifact hash is required")
    normalized: dict[str, str] = {}
    for raw_name, raw_digest in artifacts.items():
        name = str(raw_name).strip()
        digest = str(raw_digest).strip().lower()
        if not name or name in normalized:
            raise ValueError("Artifact names must be non-empty and unique")
        if not _SHA256_RE.fullmatch(digest):
            raise ValueError(f"Invalid SHA-256 for artifact {name!r}")
        normalized[name] = digest

    body: dict[str, Any] = {
        "schema_version": 1,
        "algorithm": "sha256",
        "artifacts": dict(sorted(normalized.items())),
        "metadata": dict(metadata or {}),
    }
    return {**body, "binding_sha256": canonical_json_sha256(body)}
