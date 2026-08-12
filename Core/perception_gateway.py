"""
Permissioned pre-GPU perception gateway.

This module does not open the microphone or webcam. It accepts simulated or
future-device cue packets, checks permission/privacy gates, then routes them
through source confidence and attention decision logic.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from attention_decision_engine import build_attention_event
from attention_state_manager import AttentionStateManager
from source_confidence_model import classify_source


VALID_STATUS = {"disabled", "available", "active", "paused", "archived"}
VALID_MODES = {
    "off",
    "simulated",
    "mic_metadata_only",
    "webcam_metadata_only",
    "mic_and_webcam_metadata_only",
    "full_future",
}
VALID_OWNERS = {"kira", "lisa", "kira_lisa", "system"}
REQUIRED_FIELDS = {
    "session_id",
    "status",
    "mode",
    "owner",
    "devices",
    "permissions",
    "privacy",
    "limits",
    "routing",
    "last_event",
}


def validate_perception_session(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")
    if not str(data.get("session_id", "")).strip():
        errors.append("session_id is required.")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")
    if data.get("mode") not in VALID_MODES:
        errors.append(f"mode must be one of: {', '.join(sorted(VALID_MODES))}")
    if data.get("owner") not in VALID_OWNERS:
        errors.append(f"owner must be one of: {', '.join(sorted(VALID_OWNERS))}")

    for object_field in ("devices", "permissions", "privacy", "limits", "routing", "last_event"):
        if object_field in data and not isinstance(data.get(object_field), dict):
            errors.append(f"{object_field} must be an object.")

    devices = data.get("devices", {})
    if isinstance(devices, dict):
        for key in ("microphone_available", "microphone_enabled", "webcam_available", "webcam_enabled"):
            if devices.get(key) not in (True, False):
                errors.append(f"devices.{key} must be true or false.")

    permissions = data.get("permissions", {})
    if isinstance(permissions, dict):
        for key in ("explicit_robert_permission_required", "current_permission_granted", "always_on_monitoring_allowed", "wake_phrase_required"):
            if permissions.get(key) not in (True, False):
                errors.append(f"permissions.{key} must be true or false.")
        if permissions.get("always_on_monitoring_allowed") is True:
            errors.append("always_on_monitoring_allowed must remain false.")

    privacy = data.get("privacy", {})
    if isinstance(privacy, dict):
        required_false = ("store_raw_audio", "store_raw_video", "store_private_content")
        for key in required_false:
            if privacy.get(key) is not False:
                errors.append(f"privacy.{key} must be false.")
        required_true = ("metadata_only", "adult_or_private_media_defaults_to_privacy", "visitor_present_blocks_private_teasing")
        for key in required_true:
            if privacy.get(key) is not True:
                errors.append(f"privacy.{key} must be true.")

    if data.get("status") == "active":
        if isinstance(permissions, dict) and permissions.get("current_permission_granted") is not True:
            errors.append("active perception requires permissions.current_permission_granted true.")
        if data.get("mode") == "off":
            errors.append("active perception cannot use mode off.")

    return errors


class PerceptionGateway:
    def __init__(
        self,
        session_file: str | Path = "Data/perception/perception_session_state.json",
        attention_state_file: str | Path = "Data/attention/attention_state.json",
    ) -> None:
        self.session_path = Path(session_file)
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.session_path.exists():
            self._write_sessions([])
        self.attention_states = AttentionStateManager(attention_state_file)

    def list_sessions(self) -> list[dict[str, Any]]:
        return self._read_sessions()

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        for session in self._read_sessions():
            if session.get("session_id") == session_id:
                return session
        return None

    def process_cues(
        self,
        session_id: str,
        cues: dict[str, Any],
        *,
        relationship_stage: str = "friendship",
        unspoken_feeling_possible: bool = False,
        mutual_intimate_context_established: bool = False,
    ) -> dict[str, Any]:
        sessions = self._read_sessions()
        for session in sessions:
            if session.get("session_id") != session_id:
                continue
            gate = self._permission_gate(session)
            if gate:
                event = self._blocked_event(session, gate)
                session["last_event"] = event
                self._write_sessions(sessions)
                return deepcopy(event)

            source = classify_source(cues)
            owner = str(session.get("owner", "system")).lower()
            attention_state = self._attention_event_state_name(owner)
            event = build_attention_event(
                owner=owner if owner in {"kira", "lisa"} else "system",
                attention_state=attention_state,
                relationship_id=(f"rel_robert_{owner}_current" if owner in {"kira", "lisa"} else ""),
                relationship_stage=relationship_stage,
                unspoken_feeling_possible=unspoken_feeling_possible,
                mutual_intimate_context_established=mutual_intimate_context_established,
                **{key: source[key] for key in ("source_label", "source_confidence", "category_guess", "other_person_present")},
            )
            session["last_event"] = {
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "attention_event": event,
            }
            self._write_sessions(sessions)
            return deepcopy(event)
        raise KeyError(session_id)

    def _permission_gate(self, session: dict[str, Any]) -> str:
        if session.get("status") != "active":
            return "perception_session_not_active"
        if session.get("mode") == "off":
            return "perception_mode_off"
        permissions = session.get("permissions", {})
        if permissions.get("current_permission_granted") is not True:
            return "permission_not_granted"
        return ""

    def _blocked_event(self, session: dict[str, Any], reason: str) -> dict[str, Any]:
        owner = str(session.get("owner", "system")).lower()
        return {
            "event_id": f"perception_blocked_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "owner": owner,
            "blocked": True,
            "reason": reason,
            "recommended_action": "do_not_observe",
            "memory_policy": {
                "attention_event_is_not_trusted_memory": True,
                "does_not_create_consent": True,
                "does_not_upgrade_relationship_stage": True,
                "store_exact_private_content": False,
                "owner_controls_private_reflection": True,
            },
        }

    def _attention_event_state_name(self, owner: str) -> str:
        state = self.attention_states.get_state(owner) or {}
        focus = state.get("current_focus", "idle")
        mapping = {
            "user": "focused_on_user",
            "idle": "idle_nearby",
            "reading": "reading_or_researching",
            "research": "reading_or_researching",
            "memory_reflection": "private_reflection",
            "private_activity": "locked_private_space",
            "other_ai": "private_conversation",
            "offline": "upset_unavailable",
        }
        return mapping.get(str(focus), "idle_nearby")

    def _read_sessions(self) -> list[dict[str, Any]]:
        return json.loads(self.session_path.read_text(encoding="utf-8"))

    def _write_sessions(self, sessions: list[dict[str, Any]]) -> None:
        self.session_path.write_text(json.dumps(sessions, indent=2, ensure_ascii=False), encoding="utf-8")
