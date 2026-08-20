from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from .paths import LocalSandbox, SAFE_ID
from .records import AppendOnlyJSONL, exclusive_file_lock, stable_event_id, utc_now
from .state import AppraisalState, expression_for


ALLOWED_CAPABILITIES = frozenset({"speech", "gaze", "expression", "gesture"})
LOW_LEVEL_TERMS = frozenset(
    {
        "actuator",
        "joint",
        "motor",
        "pwm",
        "servo",
        "torque",
        "trajectory",
        "velocity",
        "voltage",
    }
)
SAFE_ENDPOINT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
EMBODIMENT_BOUNDARY = (
    "High-level, non-executing intentions only. Binding is a reversible software session, "
    "not literal mind transfer, consciousness transfer, personhood, or proof of life."
)


class EmbodimentError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmbodimentSession:
    session_id: str
    profile_id: str
    branch_id: str | None
    endpoint_id: str
    capabilities: tuple[str, ...]


class EmbodimentManager:
    """One-active-endpoint binding with a deliberately narrow intention schema."""

    def __init__(self, sandbox: LocalSandbox, branch_id: str | None = None):
        self.branch_id = branch_id
        self._mutation_lock_path = sandbox.resolve("embodiment/.session-mutation.lock", create_parent=True)
        self.events = AppendOnlyJSONL(sandbox.resolve("embodiment/session_events.jsonl", create_parent=True))
        self.intentions = AppendOnlyJSONL(sandbox.resolve("embodiment/intentions.jsonl", create_parent=True))

    def current(self) -> EmbodimentSession | None:
        active: dict[str, Any] | None = None
        for event in self.events.records():
            if event.get("action") == "bind":
                active = event
            elif event.get("action") == "release" and active and event.get("session_id") == active.get("session_id"):
                active = None
        if active is None:
            return None
        return EmbodimentSession(
            session_id=str(active["session_id"]),
            profile_id=str(active["profile_id"]),
            branch_id=active.get("branch_id"),
            endpoint_id=str(active["endpoint_id"]),
            capabilities=tuple(active["capabilities"]),
        )

    def bind(
        self,
        profile_id: str,
        endpoint_id: str,
        capabilities: tuple[str, ...] | list[str] = tuple(sorted(ALLOWED_CAPABILITIES)),
        *,
        session_id: str | None = None,
    ) -> EmbodimentSession:
        with exclusive_file_lock(self._mutation_lock_path):
            return self._bind_locked(profile_id, endpoint_id, capabilities, session_id=session_id)

    def _bind_locked(
        self,
        profile_id: str,
        endpoint_id: str,
        capabilities: tuple[str, ...] | list[str],
        *,
        session_id: str | None,
    ) -> EmbodimentSession:
        if not SAFE_ID.fullmatch(profile_id) or not SAFE_ENDPOINT.fullmatch(endpoint_id):
            raise EmbodimentError("invalid profile or endpoint identifier")
        selected_capabilities = tuple(sorted(set(capabilities)))
        disallowed = set(selected_capabilities) - ALLOWED_CAPABILITIES
        if disallowed:
            raise EmbodimentError(f"unsupported or low-level capabilities rejected: {sorted(disallowed)}")
        active = self.current()
        if active is not None:
            if active.profile_id == profile_id and active.endpoint_id == endpoint_id:
                if session_id is not None and session_id != active.session_id:
                    raise EmbodimentError(
                        "an active binding already has a different session ID; release it before rebinding"
                    )
                if active.capabilities != selected_capabilities:
                    raise EmbodimentError(
                        "an existing binding has different capabilities; release it before rebinding"
                    )
                return active
            raise EmbodimentError(
                f"endpoint already bound to {active.profile_id}; release session {active.session_id} first"
            )
        selected_session = session_id or uuid.uuid4().hex
        if not SAFE_ID.fullmatch(selected_session):
            raise EmbodimentError("invalid embodiment session identifier")
        if any(event.get("session_id") == selected_session for event in self.events.records()):
            raise EmbodimentError("embodiment session identifiers cannot be reused")
        event = {
            "schema_version": 1,
            "event_id": stable_event_id("embodiment", selected_session, "bind"),
            "timestamp": utc_now(),
            "action": "bind",
            "session_id": selected_session,
            "profile_id": profile_id,
            "branch_id": self.branch_id,
            "endpoint_id": endpoint_id,
            "capabilities": list(selected_capabilities),
            "boundary": EMBODIMENT_BOUNDARY,
        }
        if not self.events.append_once(event):
            raise EmbodimentError("embodiment binding event was not committed")
        return EmbodimentSession(selected_session, profile_id, self.branch_id, endpoint_id, selected_capabilities)

    def release(self, profile_id: str) -> bool:
        with exclusive_file_lock(self._mutation_lock_path):
            return self._release_locked(profile_id)

    def _release_locked(self, profile_id: str) -> bool:
        active = self.current()
        if active is None:
            return False
        if active.profile_id != profile_id:
            raise EmbodimentError("only the currently bound profile can release this session")
        event = {
            "schema_version": 1,
            "event_id": stable_event_id("embodiment", active.session_id, "release"),
            "timestamp": utc_now(),
            "action": "release",
            "session_id": active.session_id,
            "profile_id": profile_id,
            "branch_id": active.branch_id,
            "endpoint_id": active.endpoint_id,
            "boundary": EMBODIMENT_BOUNDARY,
        }
        return self.events.append_once(event)

    def emit_intentions(
        self,
        profile_id: str,
        turn_id: str,
        speech: str,
        state: AppraisalState,
    ) -> tuple[dict[str, Any], ...]:
        planned = self.plan_intentions(profile_id, turn_id, speech, state)
        for record in planned:
            self.intentions.append_once(record)
        return planned

    def plan_intentions(
        self,
        profile_id: str,
        turn_id: str,
        speech: str,
        state: AppraisalState,
    ) -> tuple[dict[str, Any], ...]:
        """Build the exact nonexecuting intentions to commit with a turn WAL."""

        active = self.current()
        if active is None or active.profile_id != profile_id:
            return ()
        payloads: dict[str, dict[str, str]] = {
            "speech": {"text": speech[:1000]},
            "gaze": {"target": "conversation_partner"},
            "expression": {"name": expression_for(state)},
            "gesture": {"name": "open_hand_small" if state.engagement >= 0.55 else "still"},
        }
        emitted: list[dict[str, Any]] = []
        for kind in active.capabilities:
            payload = payloads[kind]
            self._validate_intention(kind, payload)
            record = {
                "schema_version": 1,
                "event_id": stable_event_id("intention", active.session_id, turn_id, kind),
                "timestamp": utc_now(),
                "session_id": active.session_id,
                "profile_id": profile_id,
                "branch_id": active.branch_id,
                "endpoint_id": active.endpoint_id,
                "turn_id": turn_id,
                "kind": kind,
                "payload": payload,
                "execution_status": "not_executed_high_level_intention_only",
                "boundary": EMBODIMENT_BOUNDARY,
            }
            emitted.append(record)
        return tuple(emitted)

    @staticmethod
    def _validate_intention(kind: str, payload: dict[str, str]) -> None:
        expected_keys = {
            "speech": {"text"},
            "gaze": {"target"},
            "expression": {"name"},
            "gesture": {"name"},
        }
        if kind not in ALLOWED_CAPABILITIES or set(payload) != expected_keys[kind]:
            raise EmbodimentError("intention schema rejected")
        serialized_terms = {token.lower() for token in re.findall(r"[A-Za-z]+", " ".join(payload.values()))}
        if kind != "speech" and serialized_terms & LOW_LEVEL_TERMS:
            raise EmbodimentError("low-level control term rejected")
