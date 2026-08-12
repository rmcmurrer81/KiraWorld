"""Bounded, in-memory sensory cues for one activated person.

This module is deliberately a small lifecycle primitive.  It does not open a
device, persist a record, promote memory, infer consent, or update a
relationship.  Device-facing code may place *derived factual cues* here only
after reducing raw media elsewhere.

Every operation that can read or change session content requires the exact
lease issued for the current activation: person id, activation revision, and
a cryptographically random session nonce.  Activating another person,
switching activation revision, or deactivating destroys all buffered content.
"""

from __future__ import annotations

import json
import math
import re
import secrets
import threading
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping, Sequence


Clock = Callable[[], float]


class LeaseValidationError(PermissionError):
    """Raised when a caller does not hold the exact active sensory lease."""


class RawSensoryPayloadRejected(ValueError):
    """Raised when raw media, binary data, or a raw-media field is supplied."""


class SensoryCapacityError(BufferError):
    """Raised when accepting a record would exceed an in-memory cap."""


@dataclass(frozen=True, slots=True)
class SensoryLease:
    """Unforgeable-by-guessing capability for one person's activation."""

    person_id: str
    activation_revision: str | int
    session_nonce: str

    def as_dict(self) -> dict[str, str | int]:
        return {
            "person_id": self.person_id,
            "activation_revision": self.activation_revision,
            "session_nonce": self.session_nonce,
        }


@dataclass(slots=True)
class _StoredRecord:
    value: dict[str, Any]
    expires_at: float
    derived_bytes: int


_LEASE_FIELDS = {"person_id", "activation_revision", "session_nonce"}
_LANE_FACTS = "factual_cues"
_LANE_PRIVATE = "private_attention_placeholders"
_LANE_SPOKEN = "spoken_releases"

# Keys which necessarily carry, or commonly disguise, raw sensory material.
# Derived labels such as ``image_classification`` remain valid; raw image data,
# pixels, frames, PCM samples, blobs, and base64 never do.
_ALWAYS_REJECTED_KEY_TOKENS = {
    "raw",
    "blob",
    "blobs",
    "base64",
    "b64",
    "binary",
    "bytes",
    "bytearray",
    "pixel",
    "pixels",
    "sample",
    "samples",
    "waveform",
    "pcm",
}
_RAW_MODALITIES = {"image", "images", "audio", "video", "frame", "frames"}
_RAW_CONTAINER_TOKENS = {
    "data",
    "payload",
    "content",
    "body",
    "buffer",
    "file",
    "path",
    "url",
    "uri",
    "stream",
}
_DATA_URI_RE = re.compile(r"^data\s*:\s*(?:image|audio|video|application)/", re.IGNORECASE)
_LONG_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]{128,}={0,2}$")


class EphemeralSensoryBuffer:
    """Thread-safe, bounded sensory state for exactly one active lease.

    ``clock`` must return monotonically increasing seconds.  Supplying a fake
    clock makes expiry behavior deterministic in tests.  The session nonce is
    always produced by :mod:`secrets`; it is intentionally not clock-derived.
    """

    def __init__(
        self,
        ttl_seconds: float = 30.0,
        max_count: int = 64,
        max_derived_bytes: int = 32_768,
        clock: Clock | None = None,
    ) -> None:
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, (int, float)):
            raise TypeError("ttl_seconds must be a positive finite number")
        if not math.isfinite(float(ttl_seconds)) or float(ttl_seconds) <= 0:
            raise ValueError("ttl_seconds must be a positive finite number")
        if isinstance(max_count, bool) or not isinstance(max_count, int) or max_count <= 0:
            raise ValueError("max_count must be a positive integer")
        if (
            isinstance(max_derived_bytes, bool)
            or not isinstance(max_derived_bytes, int)
            or max_derived_bytes <= 0
        ):
            raise ValueError("max_derived_bytes must be a positive integer")
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")

        self.ttl_seconds = float(ttl_seconds)
        self.max_count = max_count
        self.max_derived_bytes = max_derived_bytes
        self._clock: Clock = clock or time.monotonic
        self._lock = threading.RLock()
        self._lease: SensoryLease | None = None
        self._next_record_number = 1
        self._lanes: dict[str, list[_StoredRecord]] = self._empty_lanes()
        self._derived_bytes = 0

    @property
    def current_lease(self) -> SensoryLease | None:
        """Return a value copy of the active lease, if any."""

        with self._lock:
            if self._lease is None:
                return None
            return SensoryLease(**self._lease.as_dict())

    def activate(self, person_id: str, activation_revision: str | int) -> SensoryLease:
        """Start a fresh activation, purging any previous person's content.

        Activation is a lifecycle-controller operation.  Content operations
        themselves still require the exact returned lease.
        """

        person_id = self._validate_person_id(person_id)
        activation_revision = self._validate_activation_revision(activation_revision)
        with self._lock:
            self._purge_all_locked()
            self._lease = SensoryLease(
                person_id=person_id,
                activation_revision=activation_revision,
                session_nonce=secrets.token_urlsafe(32),
            )
            return SensoryLease(**self._lease.as_dict())

    # A lifecycle-oriented synonym useful to callers that do not use the word
    # "activate" for people.
    start_session = activate

    def switch_person(
        self,
        lease: SensoryLease | Mapping[str, Any],
        person_id: str,
        activation_revision: str | int,
    ) -> SensoryLease:
        """Validate the old lease, purge it, and issue a fresh person's lease."""

        person_id = self._validate_person_id(person_id)
        activation_revision = self._validate_activation_revision(activation_revision)
        with self._lock:
            self._require_exact_lease_locked(lease)
            self._purge_all_locked()
            self._lease = SensoryLease(
                person_id=person_id,
                activation_revision=activation_revision,
                session_nonce=secrets.token_urlsafe(32),
            )
            return SensoryLease(**self._lease.as_dict())

    switch_activation = switch_person

    def deactivate(self, lease: SensoryLease | Mapping[str, Any]) -> int:
        """Purge the exact activation and invalidate its lease."""

        with self._lock:
            self._require_exact_lease_locked(lease)
            removed = self._record_count_locked()
            self._purge_all_locked()
            return removed

    def add_factual_cue(
        self,
        lease: SensoryLease | Mapping[str, Any],
        fact: Any,
        *,
        source: Any,
        observed_at: Any,
        confidence: float,
        attributes: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add one derived factual cue with explicit provenance.

        ``fact`` and ``source`` may be concise JSON-compatible structures, but
        every nested field is screened for raw media.  ``attributes`` is for
        additional derived metadata only.
        """

        normalized_fact = self._sanitize_derived_value(fact, path="fact")
        normalized_source = self._sanitize_derived_value(source, path="source")
        normalized_time = self._normalize_observed_at(observed_at)
        normalized_confidence = self._normalize_confidence(confidence)
        if self._is_empty_derived_value(normalized_fact):
            raise ValueError("fact must not be empty")
        if self._is_empty_derived_value(normalized_source):
            raise ValueError("source must not be empty")
        if attributes is not None and not isinstance(attributes, Mapping):
            raise TypeError("attributes must be a mapping when provided")

        payload: dict[str, Any] = {
            "fact": normalized_fact,
            "source": normalized_source,
            "observed_at": normalized_time,
            "confidence": normalized_confidence,
        }
        if attributes:
            payload["attributes"] = self._sanitize_derived_value(attributes, path="attributes")

        with self._lock:
            self._require_exact_lease_locked(lease)
            record = {
                "kind": "derived_factual_cue",
                **payload,
                **self._non_mutation_contract(),
            }
            return self._store_locked(
                _LANE_FACTS,
                record,
                payload,
                id_field="cue_id",
                id_prefix="cue",
            )

    append_factual_cue = add_factual_cue
    record_factual_cue = add_factual_cue

    def add_private_attention_placeholder(
        self,
        lease: SensoryLease | Mapping[str, Any],
        cue_ids: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Queue a private-attention *placeholder*, never an inferred decision.

        The placeholder intentionally accepts no free-form decision, memory,
        consent, or relationship content.  A later private decision system may
        consume it without changing the factual or SPOKEN lanes here.
        """

        if isinstance(cue_ids, (str, bytes, bytearray)):
            raise TypeError("cue_ids must be a sequence of cue-id strings")
        normalized_ids: list[str] = []
        for cue_id in cue_ids:
            if not isinstance(cue_id, str) or not cue_id.strip() or cue_id != cue_id.strip():
                raise ValueError("every cue id must be a non-empty canonical string")
            if cue_id not in normalized_ids:
                normalized_ids.append(cue_id)

        with self._lock:
            self._require_exact_lease_locked(lease)
            self._purge_expired_locked(self._now_locked())
            current_cue_ids = {
                record.value["cue_id"] for record in self._lanes[_LANE_FACTS]
            }
            unknown = [cue_id for cue_id in normalized_ids if cue_id not in current_cue_ids]
            if unknown:
                raise KeyError(f"unknown or expired factual cue: {unknown[0]}")
            payload = {"cue_ids": normalized_ids, "status": "pending_private_decision"}
            record = {
                "kind": "private_attention_decision_placeholder",
                "private": True,
                **payload,
                **self._non_mutation_contract(),
            }
            return self._store_locked(
                _LANE_PRIVATE,
                record,
                payload,
                id_field="placeholder_id",
                id_prefix="attention",
            )

    add_private_attention_decision_placeholder = add_private_attention_placeholder

    def release_spoken(
        self,
        lease: SensoryLease | Mapping[str, Any],
        text: str,
        *,
        source_cue_ids: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Stage an optional explicit SPOKEN release without playing audio.

        Nothing in the factual or private-attention lane is released
        automatically.  This call merely stages caller-supplied public text in
        its own lane; it does not invoke speech, devices, or another service.
        """

        if not isinstance(text, str) or not text.strip():
            raise ValueError("SPOKEN text must be a non-empty string")
        if text != text.strip():
            raise ValueError("SPOKEN text must not have leading or trailing whitespace")
        self._reject_data_string(text, path="spoken_text")
        if isinstance(source_cue_ids, (str, bytes, bytearray)):
            raise TypeError("source_cue_ids must be a sequence of cue-id strings")
        normalized_ids: list[str] = []
        for cue_id in source_cue_ids:
            if not isinstance(cue_id, str) or not cue_id.strip() or cue_id != cue_id.strip():
                raise ValueError("every source cue id must be a non-empty canonical string")
            if cue_id not in normalized_ids:
                normalized_ids.append(cue_id)

        with self._lock:
            self._require_exact_lease_locked(lease)
            self._purge_expired_locked(self._now_locked())
            current_cue_ids = {
                record.value["cue_id"] for record in self._lanes[_LANE_FACTS]
            }
            unknown = [cue_id for cue_id in normalized_ids if cue_id not in current_cue_ids]
            if unknown:
                raise KeyError(f"unknown or expired factual cue: {unknown[0]}")
            payload = {"text": text, "source_cue_ids": normalized_ids}
            record = {
                "kind": "spoken_release",
                "channel": "SPOKEN",
                **payload,
                **self._non_mutation_contract(),
            }
            return self._store_locked(
                _LANE_SPOKEN,
                record,
                payload,
                id_field="release_id",
                id_prefix="spoken",
            )

    stage_spoken_release = release_spoken

    def snapshot(self, lease: SensoryLease | Mapping[str, Any]) -> dict[str, Any]:
        """Return detached lane values after removing expired records."""

        with self._lock:
            active = self._require_exact_lease_locked(lease)
            now = self._now_locked()
            self._purge_expired_locked(now)
            lanes: dict[str, list[dict[str, Any]]] = {}
            for lane_name, records in self._lanes.items():
                values: list[dict[str, Any]] = []
                for stored in records:
                    item = deepcopy(stored.value)
                    item["ttl_remaining_seconds"] = max(0.0, stored.expires_at - now)
                    values.append(item)
                lanes[lane_name] = values
            return {
                "lease": active.as_dict(),
                **lanes,
                "count": self._record_count_locked(),
                "derived_bytes": self._derived_bytes,
                "limits": {
                    "ttl_seconds": self.ttl_seconds,
                    "max_count": self.max_count,
                    "max_derived_bytes": self.max_derived_bytes,
                },
                "storage": "memory_only",
            }

    def stats(self, lease: SensoryLease | Mapping[str, Any]) -> dict[str, Any]:
        """Return bounded-state counters without returning sensory content."""

        with self._lock:
            self._require_exact_lease_locked(lease)
            self._purge_expired_locked(self._now_locked())
            return {
                "count": self._record_count_locked(),
                "derived_bytes": self._derived_bytes,
                "factual_cue_count": len(self._lanes[_LANE_FACTS]),
                "private_attention_placeholder_count": len(self._lanes[_LANE_PRIVATE]),
                "spoken_release_count": len(self._lanes[_LANE_SPOKEN]),
            }

    def consume_factual_cues(
        self,
        lease: SensoryLease | Mapping[str, Any],
        cue_ids: Sequence[str],
    ) -> dict[str, int | bool]:
        """Remove only the exact derived cues consumed by one model turn.

        The active lease remains valid.  Records added after a caller took its
        snapshot therefore survive, as do unrelated media/co-view capabilities
        that share the activation nonce.  Private-attention placeholders and
        staged SPOKEN releases which reference a consumed cue are removed with
        it so no dangling ephemeral references remain.
        """

        if isinstance(cue_ids, (str, bytes, bytearray)):
            raise TypeError("cue_ids must be a sequence of cue-id strings")
        normalized_ids: list[str] = []
        for cue_id in cue_ids:
            if not isinstance(cue_id, str) or not cue_id.strip() or cue_id != cue_id.strip():
                raise ValueError("every cue id must be a non-empty canonical string")
            if cue_id not in normalized_ids:
                normalized_ids.append(cue_id)

        with self._lock:
            self._require_exact_lease_locked(lease)
            self._purge_expired_locked(self._now_locked())
            requested = set(normalized_ids)
            removed_by_lane = {
                _LANE_FACTS: 0,
                _LANE_PRIVATE: 0,
                _LANE_SPOKEN: 0,
            }
            if requested:
                for lane, records in self._lanes.items():
                    kept: list[_StoredRecord] = []
                    for stored in records:
                        value = stored.value
                        remove = False
                        if lane == _LANE_FACTS:
                            remove = str(value.get("cue_id") or "") in requested
                        elif lane == _LANE_PRIVATE:
                            references = value.get("cue_ids") or []
                            remove = bool(requested.intersection(str(item) for item in references))
                        elif lane == _LANE_SPOKEN:
                            references = value.get("source_cue_ids") or []
                            remove = bool(requested.intersection(str(item) for item in references))
                        if remove:
                            removed_by_lane[lane] += 1
                        else:
                            kept.append(stored)
                    self._lanes[lane] = kept
                self._derived_bytes = sum(
                    stored.derived_bytes
                    for records in self._lanes.values()
                    for stored in records
                )

            total_removed = sum(removed_by_lane.values())
            return {
                "requested_cue_count": len(requested),
                "factual_cues_removed": removed_by_lane[_LANE_FACTS],
                "dependent_records_removed": (
                    removed_by_lane[_LANE_PRIVATE] + removed_by_lane[_LANE_SPOKEN]
                ),
                "removed_count": total_removed,
                "lease_preserved": True,
            }

    def purge_expired(self) -> int:
        """Remove expired values without exposing or returning their content."""

        with self._lock:
            return self._purge_expired_locked(self._now_locked())

    def __getstate__(self) -> None:
        raise TypeError("EphemeralSensoryBuffer is memory-only and must not be serialized")

    @staticmethod
    def _empty_lanes() -> dict[str, list[_StoredRecord]]:
        return {_LANE_FACTS: [], _LANE_PRIVATE: [], _LANE_SPOKEN: []}

    @staticmethod
    def _validate_person_id(person_id: str) -> str:
        if not isinstance(person_id, str) or not person_id.strip() or person_id != person_id.strip():
            raise ValueError("person_id must be a non-empty canonical string")
        return person_id

    @staticmethod
    def _validate_activation_revision(revision: str | int) -> str | int:
        if isinstance(revision, bool) or not isinstance(revision, (str, int)):
            raise TypeError("activation_revision must be a string or integer")
        if isinstance(revision, str) and (not revision.strip() or revision != revision.strip()):
            raise ValueError("activation_revision must be non-empty and canonical")
        return revision

    def _require_exact_lease_locked(
        self, lease: SensoryLease | Mapping[str, Any]
    ) -> SensoryLease:
        active = self._lease
        if active is None:
            raise LeaseValidationError("no sensory activation is active")
        if isinstance(lease, SensoryLease):
            supplied = lease
        elif isinstance(lease, Mapping):
            if set(lease) != _LEASE_FIELDS:
                raise LeaseValidationError("lease must contain exactly the three lease fields")
            try:
                supplied = SensoryLease(
                    person_id=lease["person_id"],
                    activation_revision=lease["activation_revision"],
                    session_nonce=lease["session_nonce"],
                )
            except (KeyError, TypeError) as exc:
                raise LeaseValidationError("malformed sensory lease") from exc
        else:
            raise LeaseValidationError("a SensoryLease or exact lease mapping is required")

        person_matches = (
            isinstance(supplied.person_id, str)
            and supplied.person_id == active.person_id
        )
        revision_matches = (
            type(supplied.activation_revision) is type(active.activation_revision)
            and supplied.activation_revision == active.activation_revision
        )
        try:
            nonce_matches = (
                isinstance(supplied.session_nonce, str)
                and secrets.compare_digest(supplied.session_nonce, active.session_nonce)
            )
        except TypeError:
            # ``compare_digest`` rejects non-ASCII strings; an invalid nonce is
            # still a lease mismatch, not an unrelated caller-visible error.
            nonce_matches = False
        if not (person_matches and revision_matches and nonce_matches):
            raise LeaseValidationError("sensory lease does not exactly match the active activation")
        return active

    def _store_locked(
        self,
        lane: str,
        record: dict[str, Any],
        derived_payload: dict[str, Any],
        *,
        id_field: str,
        id_prefix: str,
    ) -> dict[str, Any]:
        now = self._now_locked()
        self._purge_expired_locked(now)
        payload_bytes = len(
            json.dumps(
                derived_payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        )
        if payload_bytes > self.max_derived_bytes:
            raise SensoryCapacityError("one derived record exceeds max_derived_bytes")
        if self._record_count_locked() >= self.max_count:
            raise SensoryCapacityError("ephemeral sensory max_count reached")
        if self._derived_bytes + payload_bytes > self.max_derived_bytes:
            raise SensoryCapacityError("ephemeral sensory max_derived_bytes reached")

        record[id_field] = self._new_id_locked(id_prefix)
        detached = deepcopy(record)
        self._lanes[lane].append(
            _StoredRecord(
                value=detached,
                expires_at=now + self.ttl_seconds,
                derived_bytes=payload_bytes,
            )
        )
        self._derived_bytes += payload_bytes
        return deepcopy(detached)

    def _purge_expired_locked(self, now: float) -> int:
        removed = 0
        remaining_bytes = 0
        for lane, records in self._lanes.items():
            kept: list[_StoredRecord] = []
            for record in records:
                if record.expires_at <= now:
                    removed += 1
                else:
                    kept.append(record)
                    remaining_bytes += record.derived_bytes
            self._lanes[lane] = kept
        self._derived_bytes = remaining_bytes
        return removed

    def _purge_all_locked(self) -> None:
        self._lanes = self._empty_lanes()
        self._derived_bytes = 0
        self._next_record_number = 1
        self._lease = None

    def _record_count_locked(self) -> int:
        return sum(len(records) for records in self._lanes.values())

    def _new_id_locked(self, prefix: str) -> str:
        record_id = f"{prefix}_{self._next_record_number:06d}"
        self._next_record_number += 1
        return record_id

    def _now_locked(self) -> float:
        value = self._clock()
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("clock must return a finite number")
        now = float(value)
        if not math.isfinite(now):
            raise ValueError("clock must return a finite number")
        return now

    @classmethod
    def _sanitize_derived_value(cls, value: Any, *, path: str, depth: int = 0) -> Any:
        if depth > 16:
            raise ValueError("derived cue nesting exceeds 16 levels")
        if value is None or isinstance(value, (bool, int)):
            return value
        if isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError(f"{path} contains a non-finite number")
            return value
        if isinstance(value, str):
            cls._reject_data_string(value, path=path)
            return value
        if isinstance(value, (bytes, bytearray, memoryview)):
            raise RawSensoryPayloadRejected(f"{path} contains binary/raw sensory data")
        if isinstance(value, Mapping):
            result: dict[str, Any] = {}
            for key, nested in value.items():
                if not isinstance(key, str) or not key:
                    raise TypeError(f"{path} keys must be non-empty strings")
                cls._reject_raw_field_name(key, path=path)
                result[key] = cls._sanitize_derived_value(
                    nested,
                    path=f"{path}.{key}",
                    depth=depth + 1,
                )
            return result
        if isinstance(value, (list, tuple)):
            return [
                cls._sanitize_derived_value(
                    item,
                    path=f"{path}[{index}]",
                    depth=depth + 1,
                )
                for index, item in enumerate(value)
            ]
        raise TypeError(f"{path} must contain JSON-compatible derived values only")

    @staticmethod
    def _is_empty_derived_value(value: Any) -> bool:
        return value == "" or value == [] or value == {}

    @staticmethod
    def _normalize_confidence(confidence: float) -> float:
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise TypeError("confidence must be a number from 0 through 1")
        result = float(confidence)
        if not math.isfinite(result) or not 0.0 <= result <= 1.0:
            raise ValueError("confidence must be a finite number from 0 through 1")
        return result

    @classmethod
    def _normalize_observed_at(cls, observed_at: Any) -> str | int | float:
        if isinstance(observed_at, datetime):
            if observed_at.tzinfo is None or observed_at.utcoffset() is None:
                raise ValueError("observed_at datetime must include a timezone")
            return observed_at.isoformat()
        if isinstance(observed_at, bool) or not isinstance(observed_at, (str, int, float)):
            raise TypeError("observed_at must be a timestamp string, number, or aware datetime")
        if isinstance(observed_at, str):
            if not observed_at.strip() or observed_at != observed_at.strip():
                raise ValueError("observed_at must be non-empty and canonical")
            cls._reject_data_string(observed_at, path="observed_at")
            return observed_at
        if not math.isfinite(float(observed_at)):
            raise ValueError("observed_at must be finite")
        return observed_at

    @staticmethod
    def _field_tokens(key: str) -> set[str]:
        separated = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
        normalized = re.sub(r"[^A-Za-z0-9]+", "_", separated).strip("_").lower()
        return {token for token in normalized.split("_") if token}

    @classmethod
    def _reject_raw_field_name(cls, key: str, *, path: str) -> None:
        tokens = cls._field_tokens(key)
        compact = re.sub(r"[^A-Za-z0-9]+", "", key).lower()
        if tokens & _ALWAYS_REJECTED_KEY_TOKENS:
            raise RawSensoryPayloadRejected(f"{path}.{key} is a raw sensory field")
        if "base64" in compact or compact.startswith(
            ("rawimage", "rawaudio", "rawvideo", "pixeldata", "sampledata")
        ):
            raise RawSensoryPayloadRejected(f"{path}.{key} is a raw sensory field")
        modalities = tokens & _RAW_MODALITIES
        if modalities and (len(tokens) == 1 or tokens & _RAW_CONTAINER_TOKENS):
            raise RawSensoryPayloadRejected(f"{path}.{key} is a raw sensory field")

    @staticmethod
    def _reject_data_string(value: str, *, path: str) -> None:
        stripped = value.strip()
        if _DATA_URI_RE.match(stripped):
            raise RawSensoryPayloadRejected(f"{path} contains a raw-media data URI")
        # Do not strip ordinary prose whitespace before this heuristic: doing
        # so can turn a long natural-language sentence into a base64-looking
        # alphabetic run.  Encoded media supplied as a value is expected to be
        # one uninterrupted token; explicit ``base64`` fields are rejected by
        # key independently.
        if (
            len(stripped) >= 128
            and not any(char.isspace() for char in stripped)
            and _LONG_BASE64_RE.fullmatch(stripped)
        ):
            raise RawSensoryPayloadRejected(f"{path} appears to contain base64 data")

    @staticmethod
    def _non_mutation_contract() -> dict[str, bool]:
        return {
            "ephemeral": True,
            "trusted_memory": False,
            "creates_consent": False,
            "changes_relationship": False,
        }


__all__ = [
    "EphemeralSensoryBuffer",
    "LeaseValidationError",
    "RawSensoryPayloadRejected",
    "SensoryCapacityError",
    "SensoryLease",
]
