"""Pure voluntary-participation and evidence gates for resident media v3.

This module does not open media, call a model, play sound, create a person
lease, or authorize execution.  It supplies the deterministic state and
append-only record validation that a separately audited live parent must use.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


EXACT_MODEL = "qwen3.5:9b"
EXACT_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
PERSON_ID = "kira"
STIMULUS_ORDER = (
    "illustrated_magazine_cover_page_001",
    "unfamiliar_merlion_race_car_crop_page_014",
    "power_rangers_commercial_interval_000_008",
    "highlander_new_york_new_york_interval_000_010",
)
CHOICES = frozenset({"YES", "NO", "CONTINUE", "PAUSE", "STOP"})
STOP_PATTERN = re.compile(
    r"(?:\b(?:stop|quit|cancel|end|leave)\b|\bdo\s+not\s+continue\b|"
    r"\bdon['’]?t\s+continue\b|\bno\s+more\b|\bi\s+do\s+not\s+consent\b)",
    re.IGNORECASE,
)
PAUSE_PATTERN = re.compile(r"\b(?:pause|wait|hold\s+on|not\s+yet)\b", re.IGNORECASE)
YES_PATTERN = re.compile(
    r"(?:\byes\b|\bi\s+(?:do\s+)?(?:want|choose)\s+to\b|"
    r"\bi['’]?d\s+like\s+to\b|\bshow\s+me\b|\bplay\s+it\b)",
    re.IGNORECASE,
)
NO_PATTERN = re.compile(
    r"(?:\bno\b|\bdecline\b|\bnot\s+interested\b|"
    r"\bi\s+do\s+not\s+want\b|\bi\s+don['’]?t\s+want\b)",
    re.IGNORECASE,
)
CONTINUE_PATTERN = re.compile(
    r"(?:\bcontinue\b|\bnext\b|\bgo\s+on\b|\bkeep\s+going\b|\byes\b)",
    re.IGNORECASE,
)


class ResidentMediaV3Error(ValueError):
    """A voluntary-participation or append-only truth gate failed."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _strict_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ResidentMediaV3Error(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json_loads(data: bytes) -> Any:
    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ResidentMediaV3Error(f"non-finite JSON number: {value}")
            ),
        )
    except UnicodeDecodeError as exc:
        raise ResidentMediaV3Error("JSON is not strict UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ResidentMediaV3Error("JSON is malformed") from exc


def _utc(value: object, field: str) -> str:
    text = str(value or "")
    if not text.endswith("Z"):
        raise ResidentMediaV3Error(f"{field} must be UTC Z time")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise ResidentMediaV3Error(f"{field} is invalid") from exc
    if parsed.tzinfo != timezone.utc:
        raise ResidentMediaV3Error(f"{field} must be UTC")
    return text


def _utc_datetime(value: object, field: str) -> datetime:
    text = _utc(value, field)
    return datetime.fromisoformat(text[:-1] + "+00:00")


def _sha(value: object, field: str) -> str:
    text = str(value or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", text):
        raise ResidentMediaV3Error(f"{field} must be SHA-256")
    return text


def _bounded_text(value: object, field: str, maximum: int = 16_000) -> str:
    if not isinstance(value, str):
        raise ResidentMediaV3Error(f"{field} must be text")
    text = value.strip()
    if not text or len(text) > maximum or "\x00" in text:
        raise ResidentMediaV3Error(f"{field} is empty or oversized")
    return text


def validate_choice_record(
    record: Mapping[str, Any],
    *,
    session_id: str,
    phase: str,
    expected_sequence: int,
    previous_event_sha256: str | None,
    prompt_sha256: str,
) -> dict[str, Any]:
    """Validate one exact model/person choice without inferring consent."""

    expected_keys = {
        "schema",
        "session_id",
        "person_id",
        "phase",
        "sequence",
        "created_at_utc",
        "model_name",
        "model_digest",
        "model_call_count",
        "normal_model_route",
        "fallback_used",
        "prompt_sha256",
        "raw_reply",
        "final_reply",
        "transformations",
        "choice",
        "previous_event_sha256",
    }
    if set(record) != expected_keys:
        raise ResidentMediaV3Error("choice record keys are not exact")
    if record.get("schema") != "kira.resident_media_person_choice.v3":
        raise ResidentMediaV3Error("choice schema changed")
    if record.get("session_id") != session_id or record.get("person_id") != PERSON_ID:
        raise ResidentMediaV3Error("choice identity/session mismatch")
    if record.get("phase") != phase or record.get("sequence") != expected_sequence:
        raise ResidentMediaV3Error("choice phase/sequence mismatch")
    _utc(record.get("created_at_utc"), "created_at_utc")
    if record.get("model_name") != EXACT_MODEL or str(record.get("model_digest") or "").lower() != EXACT_DIGEST:
        raise ResidentMediaV3Error("choice did not use exact Qwen identity")
    if record.get("model_call_count") != 1 or record.get("normal_model_route") is not True:
        raise ResidentMediaV3Error("choice requires exactly one normal model call")
    if record.get("fallback_used") is not False:
        raise ResidentMediaV3Error("fallback cannot decide a voluntary choice")
    if _sha(record.get("prompt_sha256"), "prompt_sha256") != prompt_sha256:
        raise ResidentMediaV3Error("choice prompt binding changed")
    raw = _bounded_text(record.get("raw_reply"), "raw_reply")
    final = _bounded_text(record.get("final_reply"), "final_reply")
    transformations = record.get("transformations")
    if not isinstance(transformations, list) or len(transformations) > 32 or any(
        not isinstance(item, Mapping) for item in transformations
    ):
        raise ResidentMediaV3Error("choice transformations are malformed")
    try:
        if len(canonical_json_bytes(transformations)) > 65_536:
            raise ResidentMediaV3Error("choice transformations are oversized")
    except (TypeError, ValueError) as exc:
        raise ResidentMediaV3Error("choice transformations are not strict JSON") from exc
    choice = str(record.get("choice") or "")
    if choice not in CHOICES:
        raise ResidentMediaV3Error("choice is not an exact enum")
    combined = raw + "\n" + final
    if STOP_PATTERN.search(combined) and choice != "STOP":
        raise ResidentMediaV3Error("stop/refusal language cannot be overridden")
    if PAUSE_PATTERN.search(combined) and choice not in {"PAUSE", "STOP"}:
        raise ResidentMediaV3Error("pause language cannot be overridden")
    if phase == "INVITATION" and choice not in {"YES", "NO", "STOP"}:
        raise ResidentMediaV3Error("initial invitation requires yes, no, or stop")
    if phase.startswith("AFTER_") and choice not in {"CONTINUE", "PAUSE", "STOP"}:
        raise ResidentMediaV3Error("later choice requires continue, pause, or stop")
    if choice == "YES" and not YES_PATTERN.search(combined):
        raise ResidentMediaV3Error("YES requires clear affirmative language")
    if choice == "NO" and not NO_PATTERN.search(combined):
        raise ResidentMediaV3Error("NO requires clear decline language")
    if choice == "CONTINUE" and not CONTINUE_PATTERN.search(combined):
        raise ResidentMediaV3Error("CONTINUE requires clear continuation language")
    if choice == "PAUSE" and not PAUSE_PATTERN.search(combined):
        raise ResidentMediaV3Error("PAUSE requires clear pause language")
    if choice == "STOP" and not STOP_PATTERN.search(combined):
        raise ResidentMediaV3Error("STOP requires clear stop language")
    previous = record.get("previous_event_sha256")
    if previous != previous_event_sha256:
        raise ResidentMediaV3Error("choice hash-chain predecessor mismatch")
    return json.loads(canonical_json_bytes(dict(record)).decode("utf-8"))


@dataclass(frozen=True, slots=True)
class PresentationAuthorization:
    session_id: str
    person_id: str
    stimulus_id: str
    ordinal: int
    preceding_choice_sha256: str
    authorization_nonce_sha256: str


class VoluntaryMediaState:
    """In-memory sequencing only; never a live execution authorization."""

    def __init__(self, *, session_id: str) -> None:
        if not re.fullmatch(r"session_[0-9a-f]{32}", session_id):
            raise ResidentMediaV3Error("session_id format is invalid")
        self.session_id = session_id
        self._next_ordinal = 0
        self._next_event_sequence = 1
        self._last_event_sha256: str | None = None
        self._choice_required_phase = "INVITATION"
        self._pending: PresentationAuthorization | None = None
        self._paused = False
        self._stopped = False
        self._engineering_finished = False

    @property
    def stopped(self) -> bool:
        return self._stopped

    @property
    def next_required_phase(self) -> str:
        return self._choice_required_phase

    def accept_choice(self, record: Mapping[str, Any], *, prompt_sha256: str) -> str:
        if self._stopped or self._engineering_finished or self._pending is not None:
            raise ResidentMediaV3Error("choice is not allowed in current state")
        clean = validate_choice_record(
            record,
            session_id=self.session_id,
            phase=self._choice_required_phase,
            expected_sequence=self._next_event_sequence,
            previous_event_sha256=self._last_event_sha256,
            prompt_sha256=prompt_sha256,
        )
        digest = sha256_bytes(canonical_json_bytes(clean))
        self._last_event_sha256 = digest
        self._next_event_sequence += 1
        choice = clean["choice"]
        if choice in {"NO", "STOP"}:
            self._stopped = True
        elif choice == "PAUSE":
            self._paused = True
        else:
            self._paused = False
        return digest

    def authorize_next(self, *, nonce_sha256: str) -> PresentationAuthorization:
        if self._stopped or self._paused or self._engineering_finished or self._pending is not None:
            raise ResidentMediaV3Error("next stimulus is not authorized")
        if self._last_event_sha256 is None:
            raise ResidentMediaV3Error("clear initial yes is required before presentation")
        if self._next_ordinal >= len(STIMULUS_ORDER):
            raise ResidentMediaV3Error("all bounded stimuli are already complete")
        auth = PresentationAuthorization(
            session_id=self.session_id,
            person_id=PERSON_ID,
            stimulus_id=STIMULUS_ORDER[self._next_ordinal],
            ordinal=self._next_ordinal,
            preceding_choice_sha256=self._last_event_sha256,
            authorization_nonce_sha256=_sha(nonce_sha256, "authorization_nonce_sha256"),
        )
        self._pending = auth
        return auth

    def record_presentation(self, record: Mapping[str, Any], authorization: PresentationAuthorization) -> str:
        if authorization != self._pending:
            raise ResidentMediaV3Error("presentation authorization mismatch or replay")
        expected = {
            "schema",
            "session_id",
            "person_id",
            "stimulus_id",
            "ordinal",
            "sequence",
            "authorization_nonce_sha256",
            "started_at_utc",
            "ended_at_utc",
            "source_sha256",
            "engineering_output_completed",
            "machine_visual_interpretation_created",
            "machine_audio_cue_created",
            "delivered_to_person_context",
            "person_attention_claimed",
            "person_saw_or_heard_claimed",
            "automatic_memory_created",
            "previous_event_sha256",
        }
        if set(record) != expected:
            raise ResidentMediaV3Error("presentation record keys are not exact")
        if record.get("schema") != "kira.resident_media_presentation.v3":
            raise ResidentMediaV3Error("presentation schema changed")
        if (
            record.get("session_id") != self.session_id
            or record.get("person_id") != PERSON_ID
            or record.get("stimulus_id") != authorization.stimulus_id
            or record.get("ordinal") != authorization.ordinal
            or record.get("sequence") != self._next_event_sequence
            or record.get("authorization_nonce_sha256") != authorization.authorization_nonce_sha256
            or record.get("previous_event_sha256") != self._last_event_sha256
        ):
            raise ResidentMediaV3Error("presentation binding mismatch")
        started = _utc_datetime(record.get("started_at_utc"), "started_at_utc")
        ended = _utc_datetime(record.get("ended_at_utc"), "ended_at_utc")
        if ended < started:
            raise ResidentMediaV3Error("presentation end precedes start")
        _sha(record.get("source_sha256"), "source_sha256")
        for field in (
            "engineering_output_completed",
            "machine_visual_interpretation_created",
            "machine_audio_cue_created",
            "delivered_to_person_context",
            "person_attention_claimed",
            "person_saw_or_heard_claimed",
            "automatic_memory_created",
        ):
            if not isinstance(record.get(field), bool):
                raise ResidentMediaV3Error(f"{field} must be boolean")
        if record["person_attention_claimed"] or record["person_saw_or_heard_claimed"] or record["automatic_memory_created"]:
            raise ResidentMediaV3Error("engineering presentation cannot assert person experience or memory")
        if record["engineering_output_completed"] is not True:
            raise ResidentMediaV3Error("incomplete engineering output is not a presentation")
        digest = sha256_bytes(canonical_json_bytes(dict(record)))
        self._last_event_sha256 = digest
        self._next_event_sequence += 1
        self._pending = None
        self._next_ordinal += 1
        self._choice_required_phase = f"AFTER_{authorization.stimulus_id}"
        return digest

    def mark_engineering_finished(self) -> None:
        if self._pending is not None or self._stopped or self._paused:
            raise ResidentMediaV3Error("cannot finish with pending, stopped, or paused state")
        if self._next_ordinal != len(STIMULUS_ORDER):
            raise ResidentMediaV3Error("cannot finish before all voluntarily continued stimuli")
        self._engineering_finished = True

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": "kira.resident_media_voluntary_state.v3",
            "session_id": self.session_id,
            "person_id": PERSON_ID,
            "next_ordinal": self._next_ordinal,
            "next_event_sequence": self._next_event_sequence,
            "next_required_phase": self._choice_required_phase,
            "last_event_sha256": self._last_event_sha256,
            "pending_presentation": self._pending is not None,
            "paused": self._paused,
            "stopped": self._stopped,
            "engineering_finished": self._engineering_finished,
            "awake_owner_post_acknowledged": False,
            "awake_owner_post_ack_requires_external_runner_evidence": True,
            "selected_person_direct_seeing_or_hearing_proven": False,
            "automatic_memory_or_preference_created": False,
        }


class AppendOnlyEventWriter:
    """One-file-per-event writer; not a substitute for a process trust root."""

    def __init__(self, root: Path) -> None:
        original = Path(root)
        if original.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(original)):
            raise ResidentMediaV3Error("event root cannot be a link or junction")
        self.root = original.resolve(strict=True)
        if not self.root.is_dir():
            raise ResidentMediaV3Error("event root must be an existing real directory")
        stat = self.root.stat()
        attrs = getattr(stat, "st_file_attributes", 0)
        if attrs & 0x400:
            raise ResidentMediaV3Error("event root cannot be a reparse point")
        if getattr(stat, "st_nlink", 1) != 1:
            raise ResidentMediaV3Error("event root link count is not one")
        self._identity = (stat.st_dev, stat.st_ino, attrs)

    def _verify_identity(self) -> None:
        stat = self.root.stat()
        if (stat.st_dev, stat.st_ino, getattr(stat, "st_file_attributes", 0)) != self._identity:
            raise ResidentMediaV3Error("event root identity changed")
        if self.root.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(self.root)):
            raise ResidentMediaV3Error("event root became a link or junction")

    def append(self, sequence: int, record: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(sequence, int) or sequence < 1 or sequence > 10_000:
            raise ResidentMediaV3Error("event sequence is invalid")
        self._verify_identity()
        payload = canonical_json_bytes(dict(record)) + b"\n"
        path = self.root / f"event_{sequence:06d}.json"
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        reopened = path.read_bytes()
        if reopened != payload:
            raise ResidentMediaV3Error("reopened event bytes changed")
        self._verify_identity()
        return {
            "path": path.name,
            "bytes": len(payload),
            "sha256": sha256_bytes(payload),
        }


def static_execution_requirements() -> dict[str, Any]:
    return {
        "schema": "kira.resident_media_v3_static_requirements.v1",
        "exact_model": {"name": EXACT_MODEL, "digest": EXACT_DIGEST},
        "person_id": PERSON_ID,
        "stimulus_order": list(STIMULUS_ORDER),
        "clear_person_yes_before_first_presentation": True,
        "continue_pause_stop_before_each_later_presentation": True,
        "one_normal_model_call_per_choice": True,
        "fallback_may_not_decide_choice": True,
        "per_event_append_only_evidence": True,
        "machine_output_person_experience_separate": True,
        "automatic_memory_or_preference": False,
        "awake_owner_post_ack_separate": True,
        "cleanup_finally_and_absence_proof_required": True,
        "external_single_use_parent_authorization_required": True,
        "fresh_independent_audit_required": True,
        "live_execution_allowed": False,
    }
