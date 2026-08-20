from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from .paths import LocalSandbox
from .records import AppendOnlyJSONL, stable_event_id, utc_now
from .state import AppraisalState, BOUNDARY_NOTICE


LIFE_LOOP_BOUNDARY = (
    "A life loop is a durable software conversation session. The term does not imply biological life, "
    "consciousness, personhood, or a clinical mental state."
)


@dataclass(frozen=True)
class LifeLoop:
    loop_id: str
    profile_id: str
    started_at: str


class LifeLoopManager:
    """Append-only session boundaries and deterministic, privacy-safe consolidation."""

    def __init__(self, sandbox: LocalSandbox, profile_id: str, branch_id: str):
        person = sandbox.person_dir(profile_id)
        self.profile_id = profile_id
        self.branch_id = branch_id
        self.events = AppendOnlyJSONL(person / "life_loops.jsonl")
        self.consolidations = AppendOnlyJSONL(person / "consolidations.jsonl")

    def current(self) -> LifeLoop | None:
        active: dict[str, Any] | None = None
        for event in self.events.records():
            if event.get("action") == "start":
                active = event
            elif event.get("action") == "close" and active and event.get("loop_id") == active.get("loop_id"):
                active = None
        if active is None:
            return None
        return LifeLoop(
            loop_id=str(active["loop_id"]),
            profile_id=self.profile_id,
            started_at=str(active["timestamp"]),
        )

    def start(self, loop_id: str | None = None) -> LifeLoop:
        existing = self.current()
        if existing is not None:
            return existing
        selected = loop_id or uuid.uuid4().hex
        event = {
            "schema_version": 1,
            "event_id": stable_event_id("life-loop", self.profile_id, selected, "start"),
            "timestamp": utc_now(),
            "profile_id": self.profile_id,
            "branch_id": self.branch_id,
            "loop_id": selected,
            "action": "start",
            "boundary": LIFE_LOOP_BOUNDARY,
        }
        self.events.append_once(event)
        return LifeLoop(selected, self.profile_id, str(event["timestamp"]))

    def close(
        self,
        *,
        spoken: AppendOnlyJSONL,
        facts: AppendOnlyJSONL,
        state_events: AppendOnlyJSONL,
        reason: str = "completed",
    ) -> dict[str, Any]:
        active = self.current()
        if active is None:
            raise ValueError("no active life loop")
        loop_spoken = [record for record in spoken.records() if record.get("loop_id") == active.loop_id]
        loop_facts = [record for record in facts.records() if record.get("loop_id") == active.loop_id]
        loop_states = [record for record in state_events.records() if record.get("loop_id") == active.loop_id]
        final_state = AppraisalState.replay(loop_states).as_record()
        consolidation = {
            "schema_version": 1,
            "event_id": stable_event_id("consolidation", self.profile_id, active.loop_id),
            "timestamp": utc_now(),
            "profile_id": self.profile_id,
            "branch_id": self.branch_id,
            "loop_id": active.loop_id,
            "kind": "deterministic_privacy_safe_consolidation",
            "spoken_event_ids": [record["event_id"] for record in loop_spoken[-12:]],
            "fact_event_ids": [record["event_id"] for record in loop_facts[-24:]],
            "final_functional_appraisal_state": final_state,
            "full_raw_user_utterance_persisted": False,
            "explicit_self_introduced_name_label_may_be_retained_separately": True,
            "explicit_reviewed_note_text_may_be_retained_when_confirmed": True,
            "boundary": BOUNDARY_NOTICE,
        }
        self.consolidations.append_once(consolidation)
        close_event = {
            "schema_version": 1,
            "event_id": stable_event_id("life-loop", self.profile_id, active.loop_id, "close"),
            "timestamp": utc_now(),
            "profile_id": self.profile_id,
            "branch_id": self.branch_id,
            "loop_id": active.loop_id,
            "action": "close",
            "reason": reason[:80],
            "consolidation_event_id": consolidation["event_id"],
            "boundary": LIFE_LOOP_BOUNDARY,
        }
        self.events.append_once(close_event)
        return consolidation
