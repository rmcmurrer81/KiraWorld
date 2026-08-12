"""Person-scoped receipt extensions for the existing resident-media stack.

The existing :mod:`Core.media_experience_session` remains the authority for
what source bytes/pages/intervals were presented.  The existing
:mod:`Core.source_bound_audio_perception` remains the authority for whether an
audio cue was derived from exact decoded PCM.  This module adds the missing
person-level separation without opening devices, playing audio, calling Qwen,
loading a sidecar, persisting memory, or promoting a preference.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from copy import deepcopy
from datetime import datetime
from typing import Any, Callable, Mapping, Sequence

from Core.media_experience_session import (
    MediaExperienceLease,
    MediaExperienceSession,
)
from Core.source_bound_audio_perception import validate_audio_cue_bundle


PERSON_MEDIA_RECEIPT_SCHEMA = "kira.person_media_receipt.v1"
MUSIC_LISTENING_RECEIPT_SCHEMA = "kira.supervised_music_listening_receipt.v1"
MEDIA_RECORD_SCHEMA = "kira.person_media_record.v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T.*Z$")
_EPSILON = 1e-9

MEDIA_CHOICES = {
    "listen",
    "continue",
    "pause",
    "replay",
    "skip",
    "discuss",
    "remain_quiet",
    "stop",
}


class PersonMediaReceiptError(ValueError):
    """Raised when a proposed receipt would overstate a person's experience."""


class PersonMediaReceiptLeaseError(PermissionError):
    """Raised when a receipt is submitted under another person's lease."""


def _text(value: object, field_name: str, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersonMediaReceiptError(f"{field_name} must be non-empty text")
    normalized = value.strip()
    if len(normalized) > maximum:
        raise PersonMediaReceiptError(f"{field_name} exceeds {maximum} characters")
    return normalized


def _number(value: object, field_name: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PersonMediaReceiptError(f"{field_name} must be a finite number")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < minimum:
        raise PersonMediaReceiptError(
            f"{field_name} must be a finite number of at least {minimum}"
        )
    return normalized


def _sha256(value: object, field_name: str) -> str:
    normalized = str(value or "").strip().lower()
    if not _SHA256_RE.fullmatch(normalized):
        raise PersonMediaReceiptError(f"{field_name} must be lowercase SHA-256")
    return normalized


def _utc(value: object, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not _UTC_RE.fullmatch(normalized):
        raise PersonMediaReceiptError(f"{field_name} must be an exact UTC timestamp")
    try:
        datetime.fromisoformat(normalized[:-1] + "+00:00")
    except ValueError as exc:
        raise PersonMediaReceiptError(f"{field_name} is malformed") from exc
    return normalized


def _json_copy(value: object, field_name: str, *, maximum_bytes: int = 65_536) -> Any:
    try:
        encoded = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PersonMediaReceiptError(f"{field_name} must contain only JSON values") from exc
    if len(encoded) > maximum_bytes:
        raise PersonMediaReceiptError(f"{field_name} exceeds {maximum_bytes} bytes")
    return json.loads(encoded.decode("utf-8"))


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _covered(start: float, end: float, intervals: Sequence[Mapping[str, Any]]) -> bool:
    cursor = start
    for interval in sorted(
        intervals,
        key=lambda item: (float(item["start_seconds"]), float(item["end_seconds"])),
    ):
        interval_start = float(interval["start_seconds"])
        interval_end = float(interval["end_seconds"])
        if interval_end < cursor - _EPSILON:
            continue
        if interval_start > cursor + _EPSILON:
            return False
        cursor = max(cursor, interval_end)
        if cursor >= end - _EPSILON:
            return True
    return False


class PersonMediaReceiptLedger:
    """In-memory person layer anchored to one ``MediaExperienceSession``.

    Presentation, machine evidence, attention, private appraisal, public
    response, temporary reaction, durable preference, correction, and reviewed
    memory promotion are deliberately stored as separate record families.
    """

    _PRIVATE_FAMILIES = {
        "private_appraisal",
        "temporary_reaction",
        "durable_preference",
        "correction",
        "reviewed_memory_promotion",
    }

    def __init__(
        self,
        *,
        media_session: MediaExperienceSession,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(media_session, MediaExperienceSession):
            raise PersonMediaReceiptError(
                "media_session must be the existing MediaExperienceSession"
            )
        if not callable(clock):
            raise PersonMediaReceiptError("clock must be callable")
        anchor = media_session.snapshot()
        self._media_session = media_session
        self._lease = media_session.lease
        self._clock = clock
        self._last_clock: float | None = None
        self._sequence = 0
        self._stopped = False
        self._anchor = {
            "session_id": anchor["session_id"],
            "person_id": anchor["person_id"],
            "activation_revision": anchor["activation_revision"],
            "kind": anchor["kind"],
            "source": deepcopy(anchor["source"]),
        }
        self._records: dict[str, list[dict[str, Any]]] = {
            "source_presentation": [],
            "machine_evidence": [],
            "attention_choice": [],
            "private_appraisal": [],
            "public_response": [],
            "temporary_reaction": [],
            "durable_preference": [],
            "correction": [],
            "reviewed_memory_promotion": [],
        }

    @property
    def lease(self) -> MediaExperienceLease:
        return self._lease

    @property
    def stopped(self) -> bool:
        return self._stopped

    def _require_lease(self, lease: MediaExperienceLease, *, require_open: bool = True) -> None:
        if not isinstance(lease, MediaExperienceLease) or lease != self._lease:
            raise PersonMediaReceiptLeaseError(
                "media receipt lease does not match this person/session/activation"
            )
        if require_open and self._stopped:
            raise PersonMediaReceiptError("the person chose stop; this session is closed")

    def _timestamp(self) -> float:
        raw = self._clock()
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise PersonMediaReceiptError("clock must return a finite number")
        value = float(raw)
        if not math.isfinite(value):
            raise PersonMediaReceiptError("clock must return a finite number")
        if self._last_clock is not None and value < self._last_clock:
            raise PersonMediaReceiptError("clock must remain monotonic")
        self._last_clock = value
        return value

    def _record(self, family: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        self._sequence += 1
        record_id = f"{family}_{len(self._records[family]) + 1:04d}"
        record = {
            "schema": MEDIA_RECORD_SCHEMA,
            "record_id": record_id,
            "sequence": self._sequence,
            "family": family,
            "person_id": self._anchor["person_id"],
            "session_id": self._anchor["session_id"],
            "source_path": self._anchor["source"]["project_relative_path"],
            "source_sha256": self._anchor["source"]["sha256"],
            "recorded_at_clock_seconds": self._timestamp(),
            **deepcopy(dict(payload)),
        }
        record = _json_copy(record, "record")
        record["record_sha256"] = _canonical_sha256(record)
        self._records[family].append(record)
        return deepcopy(record)

    def _known_record_ids(self, *families: str) -> set[str]:
        selected = families or tuple(self._records)
        return {
            item["record_id"]
            for family in selected
            for item in self._records[family]
        }

    def record_source_presentation(
        self,
        lease: MediaExperienceLease,
        *,
        start_seconds: float,
        end_seconds: float,
        playback_clock_started_at_utc: str,
        playback_clock_ended_at_utc: str,
        actual_output_receipt_sha256: str,
    ) -> dict[str, Any]:
        """Reference an interval already proven presented by the existing session."""

        self._require_lease(lease)
        anchor = self._media_session.snapshot()
        start = _number(start_seconds, "start_seconds")
        end = _number(end_seconds, "end_seconds")
        if end <= start:
            raise PersonMediaReceiptError("presentation interval must be non-empty")
        if not _covered(start, end, anchor["playback"]["presented_intervals"]):
            raise PersonMediaReceiptError(
                "source presentation must be covered by MediaExperienceSession"
            )
        return self._record(
            "source_presentation",
            {
                "start_seconds": start,
                "end_seconds": end,
                "playback_clock_started_at_utc": _utc(
                    playback_clock_started_at_utc,
                    "playback_clock_started_at_utc",
                ),
                "playback_clock_ended_at_utc": _utc(
                    playback_clock_ended_at_utc,
                    "playback_clock_ended_at_utc",
                ),
                "actual_output_receipt_sha256": _sha256(
                    actual_output_receipt_sha256,
                    "actual_output_receipt_sha256",
                ),
                "person_attention_inferred_from_output": False,
            },
        )

    def record_machine_evidence(
        self,
        lease: MediaExperienceLease,
        *,
        evidence: Mapping[str, Any],
        evidence_kind: str,
        start_seconds: float,
        end_seconds: float,
        delivered_to_person_context: bool,
        delivered_at_utc: str | None,
    ) -> dict[str, Any]:
        self._require_lease(lease)
        start = _number(start_seconds, "start_seconds")
        end = _number(end_seconds, "end_seconds")
        if end <= start:
            raise PersonMediaReceiptError("machine evidence interval must be non-empty")
        if not isinstance(delivered_to_person_context, bool):
            raise PersonMediaReceiptError("delivered_to_person_context must be boolean")
        if delivered_to_person_context != (delivered_at_utc is not None):
            raise PersonMediaReceiptError(
                "delivery timestamp must be present exactly when evidence was delivered"
            )
        bounded = _json_copy(evidence, "evidence")
        serialized = json.dumps(bounded, sort_keys=True).lower()
        if any(token in serialized for token in ('"raw_pcm"', '"pcm_bytes"', '"audio_bytes"')):
            raise PersonMediaReceiptError("raw audio bytes must not enter a person receipt")
        binding = bounded.get("source_binding")
        if not isinstance(binding, Mapping) and isinstance(bounded.get("audio_cue"), Mapping):
            binding = bounded["audio_cue"].get("source_binding")
        if not isinstance(binding, Mapping) and isinstance(bounded.get("source"), Mapping):
            binding = bounded["source"]
        if not isinstance(binding, Mapping):
            raise PersonMediaReceiptError("machine evidence requires an exact source binding")
        bound_path = (
            binding.get("project_relative_library_path")
            or binding.get("project_relative_path")
            or binding.get("source_path")
        )
        bound_hash = binding.get("source_sha256") or binding.get("sha256")
        if bound_path != self._anchor["source"]["project_relative_path"]:
            raise PersonMediaReceiptError("machine evidence source path does not match session")
        if bound_hash != self._anchor["source"]["sha256"]:
            raise PersonMediaReceiptError("machine evidence source hash does not match session")
        if "start_seconds" in binding and abs(
            _number(binding["start_seconds"], "evidence binding start") - start
        ) > _EPSILON:
            raise PersonMediaReceiptError("machine evidence start does not match receipt interval")
        if "end_seconds" in binding and abs(
            _number(binding["end_seconds"], "evidence binding end") - end
        ) > _EPSILON:
            raise PersonMediaReceiptError("machine evidence end does not match receipt interval")
        return self._record(
            "machine_evidence",
            {
                "evidence_kind": _text(evidence_kind, "evidence_kind", 128),
                "start_seconds": start,
                "end_seconds": end,
                "evidence": bounded,
                "evidence_sha256": _canonical_sha256(bounded),
                "delivered_to_person_context": delivered_to_person_context,
                "delivered_at_utc": (
                    _utc(delivered_at_utc, "delivered_at_utc")
                    if delivered_at_utc is not None
                    else None
                ),
                "machine_evidence_is_person_attention": False,
                "machine_evidence_is_private_appraisal": False,
            },
        )

    def record_attention_choice(
        self,
        lease: MediaExperienceLease,
        *,
        choice: str,
        based_on_record_ids: Sequence[str],
        person_choice_confirmed: bool,
    ) -> dict[str, Any]:
        self._require_lease(lease)
        normalized_choice = _text(choice, "choice", 64).lower()
        if normalized_choice not in MEDIA_CHOICES:
            raise PersonMediaReceiptError("unsupported media attention choice")
        if not isinstance(person_choice_confirmed, bool):
            raise PersonMediaReceiptError("person_choice_confirmed must be boolean")
        if isinstance(based_on_record_ids, (str, bytes)) or not isinstance(
            based_on_record_ids, Sequence
        ):
            raise PersonMediaReceiptError("based_on_record_ids must be a sequence")
        known = self._known_record_ids("source_presentation", "machine_evidence")
        ids = [_text(item, "based_on_record_id", 256) for item in based_on_record_ids]
        if not ids or any(item not in known for item in ids):
            raise PersonMediaReceiptError("attention choice must reference existing evidence")
        record = self._record(
            "attention_choice",
            {
                "choice": normalized_choice,
                "based_on_record_ids": ids,
                "person_choice_confirmed": person_choice_confirmed,
                "attention_inferred_from_machine_delivery": False,
            },
        )
        if normalized_choice == "stop" and person_choice_confirmed:
            self._stopped = True
        return record

    def record_private_appraisal(
        self,
        lease: MediaExperienceLease,
        *,
        appraisal: str,
        based_on_record_ids: Sequence[str],
    ) -> dict[str, Any]:
        self._require_lease(lease)
        known = self._known_record_ids("source_presentation", "machine_evidence")
        ids = [_text(item, "based_on_record_id", 256) for item in based_on_record_ids]
        if not ids or any(item not in known for item in ids):
            raise PersonMediaReceiptError("private appraisal requires exact existing evidence")
        return self._record(
            "private_appraisal",
            {
                "appraisal": _text(appraisal, "appraisal"),
                "based_on_record_ids": ids,
                "visibility": "person_private",
                "automatically_public": False,
                "automatically_durable": False,
            },
        )

    def record_public_response(
        self,
        lease: MediaExperienceLease,
        *,
        response_text: str,
        voluntarily_disclosed_private_record_ids: Sequence[str] = (),
    ) -> dict[str, Any]:
        self._require_lease(lease)
        text = _text(response_text, "response_text", 4000)
        private_ids = {item["record_id"] for item in self._records["private_appraisal"]}
        disclosed = [
            _text(item, "voluntarily_disclosed_private_record_id", 256)
            for item in voluntarily_disclosed_private_record_ids
        ]
        if any(item not in private_ids for item in disclosed):
            raise PersonMediaReceiptError("public response references unknown private appraisal")
        return self._record(
            "public_response",
            {
                "response_text": text,
                "response_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "voluntarily_disclosed_private_record_ids": disclosed,
                "all_private_appraisal_disclosed_automatically": False,
            },
        )

    def record_temporary_reaction(
        self,
        lease: MediaExperienceLease,
        *,
        label: str,
        intensity: float,
        based_on_record_ids: Sequence[str],
    ) -> dict[str, Any]:
        self._require_lease(lease)
        normalized_intensity = _number(intensity, "intensity")
        if normalized_intensity > 1.0:
            raise PersonMediaReceiptError("reaction intensity must not exceed 1")
        known = self._known_record_ids(
            "source_presentation", "machine_evidence", "private_appraisal"
        )
        ids = [_text(item, "based_on_record_id", 256) for item in based_on_record_ids]
        if not ids or any(item not in known for item in ids):
            raise PersonMediaReceiptError("temporary reaction requires exact existing evidence")
        return self._record(
            "temporary_reaction",
            {
                "label": _text(label, "label", 128),
                "intensity": normalized_intensity,
                "based_on_record_ids": ids,
                "visibility": "person_private",
                "durable_preference_created": False,
                "reviewed_memory_created": False,
            },
        )

    def record_durable_preference_candidate(
        self,
        lease: MediaExperienceLease,
        *,
        preference_statement: str,
        based_on_record_ids: Sequence[str],
    ) -> dict[str, Any]:
        """Record a non-promoting candidate for later cross-session review."""

        self._require_lease(lease, require_open=False)
        known = self._known_record_ids(
            "source_presentation",
            "machine_evidence",
            "private_appraisal",
            "temporary_reaction",
        )
        ids = [_text(item, "based_on_record_id", 256) for item in based_on_record_ids]
        if not ids or any(item not in known for item in ids):
            raise PersonMediaReceiptError(
                "durable preference candidate requires exact current-session evidence"
            )
        return self._record(
            "durable_preference",
            {
                "preference_statement": _text(
                    preference_statement, "preference_statement"
                ),
                "based_on_record_ids": ids,
                "status": "PENDING_LATER_CROSS_SESSION_PERSON_REVIEW",
                "durable_preference_created": False,
                "single_session_promotion": False,
                "automatic_model_preference": False,
            },
        )

    def promote_durable_preference(
        self,
        lease: MediaExperienceLease,
        *,
        preference_statement: str,
        supporting_session_ids: Sequence[str],
        person_confirmed: bool,
        reviewer_id: str,
    ) -> dict[str, Any]:
        """Fail closed until reviewed external receipts have a sealed contract.

        Arbitrary session-ID strings are not evidence.  This deliberately
        preserves the old call shape so a caller cannot silently turn two
        strings into a promoted preference after this repair.
        """

        self._require_lease(lease, require_open=False)
        del preference_statement, supporting_session_ids, person_confirmed, reviewer_id
        raise PersonMediaReceiptError(
            "durable preference promotion requires reviewed external supporting-session receipts; "
            "arbitrary session IDs are insufficient"
        )

    def record_correction(
        self,
        lease: MediaExperienceLease,
        *,
        target_record_id: str,
        exact_correction_text: str,
        resulting_statement: str,
    ) -> dict[str, Any]:
        self._require_lease(lease, require_open=False)
        target = next(
            (
                item
                for records in self._records.values()
                for item in records
                if item["record_id"] == target_record_id
            ),
            None,
        )
        if target is None:
            raise PersonMediaReceiptError("correction target record is unknown")
        return self._record(
            "correction",
            {
                "target_record_id": target["record_id"],
                "target_record_sha256": target["record_sha256"],
                "exact_correction_text": _text(
                    exact_correction_text, "exact_correction_text", 2000
                ),
                "resulting_statement": _text(
                    resulting_statement, "resulting_statement", 2000
                ),
                "prior_record_preserved": True,
            },
        )

    def promote_reviewed_memory(
        self,
        lease: MediaExperienceLease,
        *,
        memory_statement: str,
        supporting_record_ids: Sequence[str],
        person_confirmed: bool,
        reviewer_id: str,
    ) -> dict[str, Any]:
        self._require_lease(lease, require_open=False)
        known = {
            item["record_id"]
            for family, records in self._records.items()
            if family != "reviewed_memory_promotion"
            for item in records
        }
        ids = [_text(item, "supporting_record_id", 256) for item in supporting_record_ids]
        if not ids or any(item not in known for item in ids):
            raise PersonMediaReceiptError("memory promotion requires exact existing records")
        if not person_confirmed:
            raise PersonMediaReceiptError("reviewed memory requires person confirmation")
        return self._record(
            "reviewed_memory_promotion",
            {
                "memory_statement": _text(memory_statement, "memory_statement", 2000),
                "supporting_record_ids": ids,
                "person_confirmed": True,
                "reviewer_id": _text(reviewer_id, "reviewer_id", 256),
                "automatic_memory_promotion": False,
                "full_source_experience_claim": False,
            },
        )

    def snapshot(self, *, include_private: bool = False) -> dict[str, Any]:
        records = {
            family: (
                deepcopy(items)
                if include_private or family not in self._PRIVATE_FAMILIES
                else []
            )
            for family, items in self._records.items()
        }
        result = {
            "schema": PERSON_MEDIA_RECEIPT_SCHEMA,
            **deepcopy(self._anchor),
            "stopped": self._stopped,
            "private_records_included": include_private,
            "record_counts": {family: len(items) for family, items in self._records.items()},
            "records": records,
            "truth_boundaries": {
                "presentation_is_attention": False,
                "machine_evidence_is_attention": False,
                "attention_is_private_appraisal": False,
                "private_appraisal_is_public_response": False,
                "temporary_reaction_is_durable_preference": False,
                "single_session_creates_durable_preference": False,
                "memory_promotion_is_automatic": False,
                "metadata_or_filename_counts_as_hearing": False,
            },
        }
        result["receipt_sha256"] = _canonical_sha256(result)
        return _json_copy(result, "person media receipt", maximum_bytes=512_000)


class SupervisedMusicListeningReceipt:
    """No-playback receipt logic for ordered, exact PCM-derived music windows.

    The class accepts only already validated audio cues.  It does not decode,
    play, capture, call Qwen, or load a sidecar.  Thus its receipt can prove
    source binding and engineering sequencing, never that the person heard or
    enjoyed the track.
    """

    def __init__(
        self,
        *,
        media_session: MediaExperienceSession,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.ledger = PersonMediaReceiptLedger(media_session=media_session, clock=clock)
        anchor = self.ledger.snapshot()
        if anchor["kind"] != "music":
            raise PersonMediaReceiptError("music listening receipt requires a music session")
        self._windows: list[dict[str, Any]] = []
        self._finalized = False
        self._release: dict[str, Any] | None = None

    @property
    def lease(self) -> MediaExperienceLease:
        return self.ledger.lease

    def add_pcm_window(
        self,
        lease: MediaExperienceLease,
        *,
        audio_cue: Mapping[str, Any],
        sidecar_id: str,
        sidecar_version: str,
        sidecar_binary_sha256: str,
        analysis_started_at_utc: str,
        analysis_ended_at_utc: str,
        uncertainty: Mapping[str, Any],
        delivered_to_qwen: bool,
        qwen_model_name: str | None = None,
        qwen_model_digest: str | None = None,
        delivered_at_utc: str | None = None,
        retry_of_window_id: str | None = None,
        gap_reason: str | None = None,
    ) -> dict[str, Any]:
        self.ledger._require_lease(lease)
        if self._finalized:
            raise PersonMediaReceiptError("music receipt is already finalized")
        try:
            validate_audio_cue_bundle(audio_cue)
        except Exception as exc:
            raise PersonMediaReceiptError(f"invalid source-bound audio cue: {exc}") from exc
        cue = _json_copy(audio_cue, "audio_cue")
        binding = cue["source_binding"]
        anchor = self.ledger._anchor
        if binding["project_relative_library_path"] != anchor["source"]["project_relative_path"]:
            raise PersonMediaReceiptError("audio cue source path does not match music session")
        if binding["source_sha256"] != anchor["source"]["sha256"]:
            raise PersonMediaReceiptError("audio cue source hash does not match music session")
        start = _number(binding["start_seconds"], "cue start_seconds")
        end = _number(binding["end_seconds"], "cue end_seconds")
        if end <= start:
            raise PersonMediaReceiptError("audio cue interval must be non-empty")
        if not isinstance(delivered_to_qwen, bool):
            raise PersonMediaReceiptError("delivered_to_qwen must be boolean")
        if delivered_to_qwen:
            if qwen_model_name != "qwen3.5:9b":
                raise PersonMediaReceiptError("delivered music evidence must target exact qwen3.5:9b")
            _sha256(qwen_model_digest, "qwen_model_digest")
            _utc(delivered_at_utc, "delivered_at_utc")
        elif any(item is not None for item in (qwen_model_name, qwen_model_digest, delivered_at_utc)):
            raise PersonMediaReceiptError("undelivered evidence must not claim a Qwen route")

        retry_target: dict[str, Any] | None = None
        if retry_of_window_id is not None:
            retry_target = next(
                (item for item in self._windows if item["window_id"] == retry_of_window_id),
                None,
            )
            if retry_target is None:
                raise PersonMediaReceiptError("retry target window is unknown")
            if (
                abs(retry_target["start_seconds"] - start) > _EPSILON
                or abs(retry_target["end_seconds"] - end) > _EPSILON
            ):
                raise PersonMediaReceiptError("retry must repeat the exact source interval")

        accepted = [item for item in self._windows if item["retry_of_window_id"] is None]
        if accepted and retry_target is None and start < accepted[-1]["start_seconds"] - _EPSILON:
            raise PersonMediaReceiptError("PCM windows must be supplied in source-time order")
        coverage_end = max((item["end_seconds"] for item in accepted), default=start)
        gap_before = max(0.0, start - coverage_end) if accepted else 0.0
        overlap_previous = max(0.0, coverage_end - start) if accepted else 0.0
        normalized_gap_reason = None
        if gap_before > _EPSILON:
            normalized_gap_reason = _text(gap_reason, "gap_reason", 500) if gap_reason else None
        elif gap_reason is not None:
            raise PersonMediaReceiptError("gap_reason is allowed only when a gap exists")

        uncertainty_copy = _json_copy(uncertainty, "uncertainty", maximum_bytes=16_384)
        uncertainty_text = json.dumps(uncertainty_copy, sort_keys=True).lower()
        if any(word in uncertainty_text for word in ("likes", "dislikes", "preference", "memory")):
            raise PersonMediaReceiptError(
                "sidecar uncertainty must not decide liking, preference, or memory"
            )
        evidence = {
            "source_binding": {
                "project_relative_library_path": anchor["source"]["project_relative_path"],
                "source_sha256": anchor["source"]["sha256"],
                "start_seconds": start,
                "end_seconds": end,
            },
            "audio_cue": cue,
            "sidecar": {
                "sidecar_id": _text(sidecar_id, "sidecar_id", 256),
                "sidecar_version": _text(sidecar_version, "sidecar_version", 128),
                "sidecar_binary_sha256": _sha256(
                    sidecar_binary_sha256, "sidecar_binary_sha256"
                ),
                "device": "cpu",
                "replaceable_specialist": True,
                "talker_enabled": False,
                "decides_person_preference": False,
            },
            "analysis_clock": {
                "started_at_utc": _utc(analysis_started_at_utc, "analysis_started_at_utc"),
                "ended_at_utc": _utc(analysis_ended_at_utc, "analysis_ended_at_utc"),
            },
            "uncertainty": uncertainty_copy,
        }
        evidence_record = self.ledger.record_machine_evidence(
            lease,
            evidence=evidence,
            evidence_kind="actual_pcm_music_sidecar_evidence",
            start_seconds=start,
            end_seconds=end,
            delivered_to_person_context=delivered_to_qwen,
            delivered_at_utc=delivered_at_utc,
        )
        window = {
            "window_id": f"pcm_window_{len(self._windows) + 1:04d}",
            "source_path": anchor["source"]["project_relative_path"],
            "source_sha256": anchor["source"]["sha256"],
            "start_seconds": start,
            "end_seconds": end,
            "playback_clock": {
                "source_start_seconds": start,
                "source_end_seconds": end,
                "physical_playback_performed": False,
            },
            "capture_clock": deepcopy(evidence["analysis_clock"]),
            "decoded_pcm_sha256": cue["features"]["decoded_pcm"]["sha256"],
            "cue_sha256": cue["cue_sha256"],
            "machine_evidence_record_id": evidence_record["record_id"],
            "retry_of_window_id": retry_of_window_id,
            "gap_before_seconds": round(gap_before, 9),
            "gap_explained": gap_before <= _EPSILON or normalized_gap_reason is not None,
            "gap_reason": normalized_gap_reason,
            "overlap_with_prior_coverage_seconds": round(overlap_previous, 9),
            "delivered_to_qwen": delivered_to_qwen,
            "qwen_model_name": qwen_model_name,
            "qwen_model_digest": qwen_model_digest,
            "delivered_at_utc": delivered_at_utc,
            "physical_playback_performed": False,
            "person_hearing_claim": False,
        }
        self._windows.append(_json_copy(window, "music window"))
        return deepcopy(window)

    def record_choice(
        self,
        lease: MediaExperienceLease,
        *,
        choice: str,
        based_on_window_ids: Sequence[str],
        person_choice_confirmed: bool,
    ) -> dict[str, Any]:
        known = {item["window_id"]: item for item in self._windows}
        ids = [_text(item, "based_on_window_id", 256) for item in based_on_window_ids]
        if not ids or any(item not in known for item in ids):
            raise PersonMediaReceiptError("music choice must reference exact PCM windows")
        evidence_ids = [known[item]["machine_evidence_record_id"] for item in ids]
        return self.ledger.record_attention_choice(
            lease,
            choice=choice,
            based_on_record_ids=evidence_ids,
            person_choice_confirmed=person_choice_confirmed,
        )

    @staticmethod
    def _coverage(windows: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
        source_windows = [item for item in windows if item["retry_of_window_id"] is None]
        merged: list[dict[str, float]] = []
        gaps: list[dict[str, float]] = []
        for item in sorted(source_windows, key=lambda row: (row["start_seconds"], row["end_seconds"])):
            start = float(item["start_seconds"])
            end = float(item["end_seconds"])
            if not merged or start > merged[-1]["end_seconds"] + _EPSILON:
                if merged:
                    gaps.append(
                        {
                            "start_seconds": merged[-1]["end_seconds"],
                            "end_seconds": start,
                            "duration_seconds": start - merged[-1]["end_seconds"],
                        }
                    )
                merged.append({"start_seconds": start, "end_seconds": end})
            else:
                merged[-1]["end_seconds"] = max(merged[-1]["end_seconds"], end)
        for item in merged:
            item["duration_seconds"] = item["end_seconds"] - item["start_seconds"]
        return merged, gaps

    def finalize(
        self,
        *,
        sidecar_released: bool,
        qwen_released_or_not_started: bool,
    ) -> dict[str, Any]:
        if self._finalized:
            raise PersonMediaReceiptError("music receipt is already finalized")
        if not self._windows:
            raise PersonMediaReceiptError("music receipt requires at least one PCM window")
        if not isinstance(sidecar_released, bool) or not isinstance(
            qwen_released_or_not_started, bool
        ):
            raise PersonMediaReceiptError("release statuses must be boolean")
        merged, gaps = self._coverage(self._windows)
        unexplained = [
            item
            for item in self._windows
            if item["gap_before_seconds"] > _EPSILON and not item["gap_explained"]
        ]
        if unexplained:
            raise PersonMediaReceiptError(
                "music receipt has an unexplained source-time gap"
            )
        self._release = {
            "sidecar_released": sidecar_released,
            "qwen_released_or_not_started": qwen_released_or_not_started,
            "clean_release": sidecar_released and qwen_released_or_not_started,
        }
        self._finalized = True
        person_receipt = self.ledger.snapshot(include_private=False)
        result = {
            "schema": MUSIC_LISTENING_RECEIPT_SCHEMA,
            "person_id": person_receipt["person_id"],
            "session_id": person_receipt["session_id"],
            "source": deepcopy(person_receipt["source"]),
            "mode": "SUPERVISED_CPU_ONLY_NO_PLAYBACK_RECEIPT",
            "ordered_pcm_windows": deepcopy(self._windows),
            "coverage_intervals": merged,
            "gaps": gaps,
            "retry_count": sum(
                item["retry_of_window_id"] is not None for item in self._windows
            ),
            "overlap_window_count": sum(
                item["overlap_with_prior_coverage_seconds"] > _EPSILON
                for item in self._windows
            ),
            "unexplained_gap_count": len(unexplained),
            "release": deepcopy(self._release),
            "person_media_receipt": person_receipt,
            "truth_boundaries": {
                "actual_pcm_analyzed": True,
                "filename_or_metadata_used_as_sound": False,
                "physical_playback_performed": False,
                "person_heard_audio": False,
                "machine_delivery_proves_attention": False,
                "single_session_preference_promoted": False,
                "automatic_memory_created": False,
                "music_listening_or_enjoyment_acceptance": False,
            },
        }
        result["receipt_sha256"] = _canonical_sha256(result)
        return _json_copy(result, "music receipt", maximum_bytes=2_000_000)
