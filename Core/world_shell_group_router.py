"""Pure sequential orchestration for World Shell group turns.

This module owns no runtime state and starts no model, voice engine, sensory
lease, or initiative lease.  The shell injects those operations as callbacks.
The router's only job is to validate a participant set and guarantee that one
participant's locked reply and serialized voice work finish before the next
participant begins. Voice runs just outside the state lock so a stop request
can still acquire that person's lock while playback is winding down.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any, ContextManager


ParticipantRecord = Mapping[str, object]
LockFactory = Callable[[str], ContextManager[object]]
ReplyCallback = Callable[[ParticipantRecord, str], object]
VoiceCallback = Callable[[ParticipantRecord, object], object]


class GroupTurnValidationError(ValueError):
    """A fail-closed validation error raised before any callback is invoked."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _validation_error(code: str, message: str) -> GroupTurnValidationError:
    return GroupTurnValidationError(code, message)


def _normalize_participants(
    participants: Iterable[ParticipantRecord],
    *,
    max_participants: int,
) -> list[dict[str, object]]:
    try:
        raw_participants = list(participants)
    except TypeError as exc:
        raise _validation_error(
            "invalid_participants",
            "participants must be an iterable of participant records",
        ) from exc

    if not raw_participants:
        raise _validation_error(
            "empty_participants",
            "a group turn requires at least one participant",
        )
    if len(raw_participants) > max_participants:
        raise _validation_error(
            "participant_capacity_exceeded",
            f"group turn has {len(raw_participants)} participants; capacity is {max_participants}",
        )

    normalized: list[dict[str, object]] = []
    seen_candidate_ids: set[str] = set()
    for index, raw_record in enumerate(raw_participants):
        if not isinstance(raw_record, Mapping):
            raise _validation_error(
                "invalid_participant_record",
                f"participant at index {index} must be a mapping",
            )

        raw_candidate_id = raw_record.get("candidate_id")
        candidate_id = raw_candidate_id.strip() if isinstance(raw_candidate_id, str) else ""
        if not candidate_id:
            raise _validation_error(
                "empty_candidate_id",
                f"participant at index {index} requires a non-empty candidate_id",
            )
        if candidate_id in seen_candidate_ids:
            raise _validation_error(
                "duplicate_candidate_id",
                f"candidate_id {candidate_id!r} appears more than once",
            )
        seen_candidate_ids.add(candidate_id)

        raw_label = raw_record.get("label")
        label = raw_label.strip() if isinstance(raw_label, str) else ""
        record = dict(raw_record)
        record["candidate_id"] = candidate_id
        record["label"] = label or candidate_id
        normalized.append(record)

    return normalized


def run_sequential_group_turn(
    participants: Iterable[ParticipantRecord],
    text: str,
    *,
    max_participants: int,
    lock_for: LockFactory,
    reply_callback: ReplyCallback,
    voice_callback: VoiceCallback,
) -> dict[str, Any]:
    """Run one reply and voice callback per participant in exact input order.

    For each participant, the router enters ``lock_for(candidate_id)`` and
    invokes ``reply_callback(participant, text)``.  It releases the state lock,
    then invokes ``voice_callback(participant, reply_result)`` before advancing
    to the next participant. Callbacks are never run in parallel.

    All participant, text, capacity, and callback validation happens before
    the first lock is entered.  Callback exceptions are intentionally allowed
    to propagate; the context manager still releases the current participant's
    lock and no later participant is started.
    """

    if isinstance(max_participants, bool) or not isinstance(max_participants, int):
        raise _validation_error(
            "invalid_capacity",
            "max_participants must be a positive integer",
        )
    if max_participants < 1:
        raise _validation_error(
            "invalid_capacity",
            "max_participants must be a positive integer",
        )
    if not isinstance(text, str) or not text.strip():
        raise _validation_error("empty_text", "group turn text must not be empty")
    if not callable(lock_for):
        raise _validation_error("invalid_lock_factory", "lock_for must be callable")
    if not callable(reply_callback):
        raise _validation_error("invalid_reply_callback", "reply_callback must be callable")
    if not callable(voice_callback):
        raise _validation_error("invalid_voice_callback", "voice_callback must be callable")

    normalized_text = text.strip()
    normalized_participants = _normalize_participants(
        participants,
        max_participants=max_participants,
    )
    participant_order = [str(record["candidate_id"]) for record in normalized_participants]
    reply_entries: list[dict[str, object]] = []
    voice_entries: list[dict[str, object]] = []

    for sequence, participant in enumerate(normalized_participants, start=1):
        candidate_id = str(participant["candidate_id"])
        label = str(participant["label"])
        with lock_for(candidate_id):
            reply_result = reply_callback(participant, normalized_text)
            reply_entries.append(
                {
                    "sequence": sequence,
                    "candidate_id": candidate_id,
                    "label": label,
                    "result": reply_result,
                }
            )
        voice_result = voice_callback(participant, reply_result)
        voice_entries.append(
            {
                "sequence": sequence,
                "candidate_id": candidate_id,
                "label": label,
                "result": voice_result,
            }
        )

    return {
        "mode": "sequential_group_turn",
        "participant_count": len(normalized_participants),
        "participant_order": participant_order,
        "reply_order": [entry["candidate_id"] for entry in reply_entries],
        "voice_order": [entry["candidate_id"] for entry in voice_entries],
        "replies": reply_entries,
        "voice": {
            "items": voice_entries,
            "callback_serialized": True,
            "parallel_callback_invocation": False,
        },
        "routing": {
            "strategy": "strictly_sequential_per_participant",
            "lock_scope": "per_person_reply_state_only",
            "parallel_reply_generation": False,
            "parallel_voice_callbacks": False,
        },
    }


__all__ = [
    "GroupTurnValidationError",
    "LockFactory",
    "ParticipantRecord",
    "ReplyCallback",
    "VoiceCallback",
    "run_sequential_group_turn",
]
