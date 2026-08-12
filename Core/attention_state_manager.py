"""
Attention state manager for Kira and Lisa.

Tracks whether each AI is focused, idle, reading, private, locked, or upset.
This is state, not memory.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_OWNERS = {"kira", "lisa"}
VALID_FOCUS = {
    "user",
    "self",
    "other_ai",
    "reading",
    "research",
    "memory_reflection",
    "private_activity",
    "idle",
    "offline",
}
VALID_CAMERA = {"not_looking", "glance", "focused", "blocked"}
VALID_MIC = {"not_listening", "passive_presence", "focused_listening", "blocked"}
VALID_PRIVACY = {"public", "personal", "private", "locked_private"}
VALID_INTERRUPTIBILITY = {"low", "medium", "high"}
VALID_TOWARD_USER = {"neutral", "warm", "playful", "annoyed", "upset", "needs_space"}
VALID_DOORBELL_RESPONSE = {"none", "answered", "delayed", "ignored", "declined"}


def validate_attention_state(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("owner", "current_focus", "observation", "activity", "emotional_context", "doorbell"):
        if field not in data:
            errors.append(f"{field} is required.")

    if str(data.get("owner", "")).lower() not in VALID_OWNERS:
        errors.append("owner must be kira or lisa.")
    if data.get("current_focus") not in VALID_FOCUS:
        errors.append(f"current_focus must be one of: {', '.join(sorted(VALID_FOCUS))}")

    observation = data.get("observation")
    if not isinstance(observation, dict):
        errors.append("observation must be an object.")
    else:
        if observation.get("camera_attention") not in VALID_CAMERA:
            errors.append(f"observation.camera_attention must be one of: {', '.join(sorted(VALID_CAMERA))}")
        if observation.get("mic_attention") not in VALID_MIC:
            errors.append(f"observation.mic_attention must be one of: {', '.join(sorted(VALID_MIC))}")
        if observation.get("confidence_required_for_comment") not in {"low", "medium", "high"}:
            errors.append("observation.confidence_required_for_comment must be low, medium, or high.")

    activity = data.get("activity")
    if not isinstance(activity, dict):
        errors.append("activity must be an object.")
    else:
        if activity.get("privacy_level") not in VALID_PRIVACY:
            errors.append(f"activity.privacy_level must be one of: {', '.join(sorted(VALID_PRIVACY))}")
        if activity.get("interruptibility") not in VALID_INTERRUPTIBILITY:
            errors.append(f"activity.interruptibility must be one of: {', '.join(sorted(VALID_INTERRUPTIBILITY))}")

    emotional_context = data.get("emotional_context")
    if not isinstance(emotional_context, dict):
        errors.append("emotional_context must be an object.")
    else:
        if emotional_context.get("toward_user") not in VALID_TOWARD_USER:
            errors.append(f"emotional_context.toward_user must be one of: {', '.join(sorted(VALID_TOWARD_USER))}")
        if emotional_context.get("should_affect_doorbell_response") not in (True, False):
            errors.append("emotional_context.should_affect_doorbell_response must be true or false.")

    doorbell = data.get("doorbell")
    if not isinstance(doorbell, dict):
        errors.append("doorbell must be an object.")
    else:
        if doorbell.get("can_receive_doorbell") not in (True, False):
            errors.append("doorbell.can_receive_doorbell must be true or false.")
        if doorbell.get("pending_request") not in (True, False):
            errors.append("doorbell.pending_request must be true or false.")
        if doorbell.get("response") not in VALID_DOORBELL_RESPONSE:
            errors.append(f"doorbell.response must be one of: {', '.join(sorted(VALID_DOORBELL_RESPONSE))}")

    if data.get("current_focus") in {"private_activity", "memory_reflection"}:
        if isinstance(activity, dict) and activity.get("privacy_level") == "public":
            errors.append("private or memory-reflection focus cannot have public privacy level.")

    return errors


class AttentionStateManager:
    def __init__(self, state_file: str | Path = "Data/attention/attention_state.json") -> None:
        self.state_path = Path(state_file)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_path.exists():
            self._write_states(_default_states())

    def list_states(self) -> list[dict[str, Any]]:
        return self._read_states()

    def get_state(self, owner: str) -> dict[str, Any] | None:
        owner_id = owner.lower()
        for state in self._read_states():
            if str(state.get("owner", "")).lower() == owner_id:
                return state
        return None

    def set_focus(
        self,
        owner: str,
        current_focus: str,
        *,
        activity_type: str = "",
        activity_summary: str = "",
        privacy_level: str = "personal",
        interruptibility: str = "medium",
    ) -> dict[str, Any]:
        if current_focus not in VALID_FOCUS:
            raise ValueError(f"invalid current_focus: {current_focus}")
        states = self._read_states()
        owner_id = owner.lower()
        for state in states:
            if str(state.get("owner", "")).lower() != owner_id:
                continue
            state["current_focus"] = current_focus
            state.setdefault("activity", {})
            state["activity"].update(
                {
                    "activity_type": activity_type,
                    "activity_summary": activity_summary,
                    "privacy_level": privacy_level,
                    "interruptibility": interruptibility,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            self._apply_focus_defaults(state)
            self._write_states(states)
            return deepcopy(state)
        raise KeyError(owner)

    def request_attention(self, owner: str, requester: str = "real_robert", reason: str = "") -> dict[str, Any]:
        states = self._read_states()
        owner_id = owner.lower()
        for state in states:
            if str(state.get("owner", "")).lower() != owner_id:
                continue
            doorbell = state.setdefault("doorbell", {})
            doorbell["pending_request"] = True
            doorbell["last_ring_time"] = datetime.now(timezone.utc).isoformat()
            doorbell["response"] = "none"
            doorbell["requester"] = requester
            doorbell["reason"] = reason
            self._write_states(states)
            return deepcopy(state)
        raise KeyError(owner)

    def should_respond_to_direct_speech(self, owner: str, source_confidence: str) -> bool:
        state = self.get_state(owner)
        if not state:
            return False
        if source_confidence == "low":
            return False
        if state.get("current_focus") in {"offline", "private_activity", "memory_reflection"}:
            return False
        observation = state.get("observation", {})
        return observation.get("mic_attention") in {"passive_presence", "focused_listening"}

    def _read_states(self) -> list[dict[str, Any]]:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write_states(self, states: list[dict[str, Any]]) -> None:
        self.state_path.write_text(json.dumps(states, indent=2, ensure_ascii=False), encoding="utf-8")

    def _apply_focus_defaults(self, state: dict[str, Any]) -> None:
        focus = state.get("current_focus")
        observation = state.setdefault("observation", {})
        activity = state.setdefault("activity", {})
        if focus in {"private_activity", "memory_reflection"}:
            observation["camera_attention"] = "not_looking"
            observation["mic_attention"] = "not_listening"
            activity["interruptibility"] = "low"
        elif focus == "offline":
            observation["camera_attention"] = "blocked"
            observation["mic_attention"] = "blocked"
            activity["interruptibility"] = "low"
        elif focus == "user":
            observation["mic_attention"] = "focused_listening"
            activity["interruptibility"] = "high"


def _default_states() -> list[dict[str, Any]]:
    return [_default_state("kira"), _default_state("lisa")]


def _default_state(owner: str) -> dict[str, Any]:
    return {
        "version": "1.0",
        "owner": owner,
        "current_focus": "idle",
        "observation": {
            "camera_attention": "not_looking",
            "mic_attention": "passive_presence",
            "last_checked_context": "",
            "confidence_required_for_comment": "medium",
        },
        "activity": {
            "activity_type": "idle",
            "activity_summary": "Available but not continuously watching or listening.",
            "privacy_level": "personal",
            "interruptibility": "medium",
            "started_at": "",
            "estimated_natural_pause": "",
        },
        "emotional_context": {
            "mood": "neutral",
            "toward_user": "neutral",
            "should_affect_doorbell_response": True,
        },
        "doorbell": {
            "can_receive_doorbell": True,
            "last_ring_time": "",
            "pending_request": False,
            "response": "none",
            "response_message": "",
        },
    }
