from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping


GENESIS_HASH = "0" * 64


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest_value(value: Any) -> dict[str, Any]:
    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (OverflowError, TypeError, ValueError):
        marker = b"KIRA_HANSON_BRIDGE_UNENCODABLE_REJECTED_VALUE_V1"
        return {
            "sha256": hashlib.sha256(marker).hexdigest(),
            "utf8_bytes": 0,
            "encoding": "UNENCODABLE_REJECTED_VALUE",
        }
    return {"sha256": hashlib.sha256(encoded).hexdigest(), "utf8_bytes": len(encoded)}


def sanitize_payload(
    category: str,
    payload: Mapping[str, Any],
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return bounded evidence metadata without raw private conversation content."""

    settings = dict(config or {})
    sanitized: dict[str, Any] = {
        "intent_id": payload.get("intent_id"),
        "source_identity": payload.get("source_identity"),
        "confidence": payload.get("confidence"),
        "ttl_ms": payload.get("ttl_ms"),
        "age_ms": payload.get("age_ms"),
        "header_frame_id": payload.get("header_frame_id", ""),
    }

    evidence_ref = payload.get("evidence_ref", "")
    if settings.get("include_evidence_ref", False):
        sanitized["evidence_ref"] = evidence_ref
    else:
        sanitized["evidence_ref_digest"] = _digest_value(evidence_ref)

    if category == "speech":
        text = payload.get("text", "")
        if settings.get("include_speech_text", False):
            sanitized["text"] = text
        else:
            sanitized["text_digest"] = _digest_value(text)
        sanitized.update(
            voice=payload.get("voice"),
            max_duration_ms=payload.get("max_duration_ms"),
        )
    elif category == "gaze":
        target = payload.get("target", {})
        if settings.get("include_gaze_coordinates", False):
            sanitized["target"] = target
        else:
            sanitized["target_digest"] = _digest_value(target)
        sanitized.update(
            target_frame=payload.get("target_frame"),
            duration_ms=payload.get("duration_ms"),
        )
    elif category == "expression":
        sanitized.update(
            expression=payload.get("expression"),
            intensity=payload.get("intensity"),
            duration_ms=payload.get("duration_ms"),
        )
    elif category == "gesture":
        sanitized.update(
            gesture=payload.get("gesture"),
            intensity=payload.get("intensity"),
            speed=payload.get("speed"),
            duration_ms=payload.get("duration_ms"),
        )
    return sanitized


class EvidenceChain:
    """Append-only SHA-256-linked JSONL evidence for the simulator proof.

    The chain makes later file edits detectable. It does not prove that a robot
    executed an action, replace platform audit controls, or authenticate the
    publisher.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        valid, count, final_hash = self.verify(self.path)
        if not valid:
            raise ValueError(f"Existing evidence chain is invalid: {self.path}")
        self._next_index = count
        self._previous_hash = final_hash

    def append(self, record: Mapping[str, Any]) -> str:
        envelope = {
            "record_index": self._next_index,
            "previous_record_hash": self._previous_hash,
            "record": dict(record),
        }
        record_hash = hashlib.sha256(_canonical_bytes(envelope)).hexdigest()
        persisted = {**envelope, "record_hash": record_hash}
        line = _canonical_bytes(persisted) + b"\n"

        with self.path.open("ab") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())

        self._next_index += 1
        self._previous_hash = record_hash
        return record_hash

    @staticmethod
    def _records(path: Path) -> Iterable[dict[str, Any]]:
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError("Evidence line must be a JSON object.")
                records.append(value)
        return records

    @classmethod
    def verify(cls, path: str | Path) -> tuple[bool, int, str]:
        evidence_path = Path(path)
        previous_hash = GENESIS_HASH
        count = 0
        try:
            for expected_index, persisted in enumerate(cls._records(evidence_path)):
                if set(persisted) != {
                    "record_index",
                    "previous_record_hash",
                    "record",
                    "record_hash",
                }:
                    return False, count, previous_hash
                if persisted["record_index"] != expected_index:
                    return False, count, previous_hash
                if persisted["previous_record_hash"] != previous_hash:
                    return False, count, previous_hash
                envelope = {
                    "record_index": persisted["record_index"],
                    "previous_record_hash": persisted["previous_record_hash"],
                    "record": persisted["record"],
                }
                expected_hash = hashlib.sha256(_canonical_bytes(envelope)).hexdigest()
                if persisted["record_hash"] != expected_hash:
                    return False, count, previous_hash
                previous_hash = expected_hash
                count += 1
        except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
            return False, count, previous_hash
        return True, count, previous_hash
