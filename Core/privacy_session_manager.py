"""
Privacy session manager for Kira 2.0.

Tracks locked rooms, doorbell requests, participants, and safe sharing scopes.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from datetime import datetime, timezone


VALID_SESSION_TYPES = {
    "ordinary_chat",
    "locked_door_private",
    "doctor_ai_private",
    "memory_reconstruction",
    "avatar_preview",
    "temporary_ai_owner_locked",
    "mediation",
}
VALID_STATUS = {"draft", "active", "paused", "ended", "archived"}
VALID_DOOR_STATES = {"open", "closed", "locked", "doorbell_pending", "do_not_disturb"}
VALID_SHARING_SCOPES = {
    "none",
    "metadata_only",
    "owner_selected_summary",
    "emotional_meaning",
    "partial_transcript",
    "full_transcript",
}
REQUIRED_FIELDS = {
    "session_id",
    "session_type",
    "status",
    "owner",
    "participants",
    "door_state",
    "allowed_participants",
    "denied_participants",
    "observers_allowed",
    "entry_requests",
    "door_messages",
    "sharing_scope",
    "content_logging",
    "related_records",
}


def validate_privacy_session(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if not data.get("session_id"):
        errors.append("session_id is required.")
    if data.get("session_type") not in VALID_SESSION_TYPES:
        errors.append(f"session_type must be one of: {', '.join(sorted(VALID_SESSION_TYPES))}")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")
    if not data.get("owner"):
        errors.append("owner is required.")
    if data.get("door_state") not in VALID_DOOR_STATES:
        errors.append(f"door_state must be one of: {', '.join(sorted(VALID_DOOR_STATES))}")
    if data.get("sharing_scope") not in VALID_SHARING_SCOPES:
        errors.append(f"sharing_scope must be one of: {', '.join(sorted(VALID_SHARING_SCOPES))}")

    for key in ("participants", "allowed_participants", "denied_participants", "entry_requests", "door_messages", "related_records"):
        if key in data and not isinstance(data.get(key), list):
            errors.append(f"{key} must be a list.")

    if data.get("observers_allowed") not in (True, False):
        errors.append("observers_allowed must be true or false.")

    participants = set(data.get("participants", [])) if isinstance(data.get("participants"), list) else set()
    allowed = set(data.get("allowed_participants", [])) if isinstance(data.get("allowed_participants"), list) else set()
    denied = set(data.get("denied_participants", [])) if isinstance(data.get("denied_participants"), list) else set()

    if participants and allowed and not participants <= allowed:
        errors.append("participants must be included in allowed_participants.")
    overlap = allowed & denied
    if overlap:
        errors.append(f"participants cannot be both allowed and denied: {', '.join(sorted(overlap))}")

    content_logging = data.get("content_logging")
    if not isinstance(content_logging, dict):
        errors.append("content_logging must be an object.")
    else:
        for key in ("metadata_allowed", "content_allowed", "safe_summary_allowed"):
            if content_logging.get(key) not in (True, False):
                errors.append(f"content_logging.{key} must be true or false.")

    if data.get("session_type") in {"locked_door_private", "doctor_ai_private", "temporary_ai_owner_locked"}:
        if data.get("door_state") not in {"locked", "doorbell_pending", "do_not_disturb"}:
            errors.append(f"{data.get('session_type')} requires locked, doorbell_pending, or do_not_disturb door_state.")
        if data.get("observers_allowed") is True:
            errors.append(f"{data.get('session_type')} cannot allow observers by default.")
        if isinstance(content_logging, dict) and content_logging.get("content_allowed") is True:
            errors.append(f"{data.get('session_type')} must not log private content by default.")

    if data.get("session_type") == "memory_reconstruction":
        if data.get("sharing_scope") == "full_transcript" and "all_participants_consented" not in data:
            errors.append("full memory reconstruction sharing requires all_participants_consented field.")
        if data.get("all_participants_consented") is False and data.get("sharing_scope") in {"partial_transcript", "full_transcript"}:
            errors.append("memory reconstruction cannot share transcript content without all participant consent.")

    return errors


class PrivacySessionManager:
    def __init__(self, session_file: str | Path = "Data/privacy/privacy_session_state.json") -> None:
        self.session_path = Path(session_file)
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.session_path.exists():
            self._write_sessions([])

    def _read_sessions(self) -> list[dict[str, Any]]:
        return json.loads(self.session_path.read_text(encoding="utf-8"))

    def _write_sessions(self, sessions: list[dict[str, Any]]) -> None:
        self.session_path.write_text(json.dumps(sessions, indent=2, ensure_ascii=False), encoding="utf-8")

    def list_sessions(self) -> list[dict[str, Any]]:
        return self._read_sessions()

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        for session in self._read_sessions():
            if session.get("session_id") == session_id:
                return session
        return None

    def can_access(self, session_id: str, participant_id: str) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        if participant_id in session.get("denied_participants", []):
            return False
        if participant_id in session.get("allowed_participants", []):
            return True
        return bool(session.get("observers_allowed") is True and session.get("door_state") == "open")

    def add_entry_request(self, session_id: str, participant_id: str, reason: str = "") -> dict[str, Any]:
        return self.request_entry(session_id, participant_id, reason)

    def request_entry(self, session_id: str, participant_id: str, reason: str = "") -> dict[str, Any]:
        sessions = self._read_sessions()
        for session in sessions:
            if session.get("session_id") != session_id:
                continue
            request = {
                "requester": participant_id,
                "reason": reason,
                "status": "pending",
                "requested_at": datetime.now(timezone.utc).isoformat(),
            }
            session.setdefault("entry_requests", []).append(request)
            if session.get("door_state") in {"locked", "closed"}:
                session["door_state"] = "doorbell_pending"
            self._write_sessions(sessions)
            return deepcopy(session)
        raise KeyError(session_id)

    def approve_entry(self, session_id: str, participant_id: str, approved_by: str) -> dict[str, Any]:
        sessions = self._read_sessions()
        for session in sessions:
            if session.get("session_id") != session_id:
                continue
            if not self._can_control_session(session, approved_by):
                raise PermissionError(f"{approved_by} cannot approve entry for {session_id}")
            denied = session.setdefault("denied_participants", [])
            if participant_id in denied:
                denied.remove(participant_id)
            allowed = session.setdefault("allowed_participants", [])
            if participant_id not in allowed:
                allowed.append(participant_id)
            participants = session.setdefault("participants", [])
            if participant_id not in participants:
                participants.append(participant_id)
            self._mark_entry_request(session, participant_id, "approved", approved_by)
            if session.get("door_state") == "doorbell_pending":
                session["door_state"] = "closed"
            session["last_privacy_action"] = self._action("approve_entry", approved_by, participant_id)
            self._write_sessions(sessions)
            return deepcopy(session)
        raise KeyError(session_id)

    def deny_entry(self, session_id: str, participant_id: str, denied_by: str, reason: str = "") -> dict[str, Any]:
        sessions = self._read_sessions()
        for session in sessions:
            if session.get("session_id") != session_id:
                continue
            if not self._can_control_session(session, denied_by):
                raise PermissionError(f"{denied_by} cannot deny entry for {session_id}")
            participants = session.setdefault("participants", [])
            if participant_id in participants:
                participants.remove(participant_id)
            allowed = session.setdefault("allowed_participants", [])
            if participant_id in allowed:
                allowed.remove(participant_id)
            denied = session.setdefault("denied_participants", [])
            if participant_id not in denied:
                denied.append(participant_id)
            self._mark_entry_request(session, participant_id, "denied", denied_by, reason)
            if session.get("door_state") == "doorbell_pending":
                session["door_state"] = "locked"
            session["last_privacy_action"] = self._action("deny_entry", denied_by, participant_id, reason)
            self._write_sessions(sessions)
            return deepcopy(session)
        raise KeyError(session_id)

    def lock_session(self, session_id: str, actor_id: str) -> dict[str, Any]:
        return self._set_door_state(session_id, "locked", actor_id)

    def unlock_session(self, session_id: str, actor_id: str) -> dict[str, Any]:
        return self._set_door_state(session_id, "open", actor_id)

    def close_session_door(self, session_id: str, actor_id: str) -> dict[str, Any]:
        return self._set_door_state(session_id, "closed", actor_id)

    def end_session(self, session_id: str, actor_id: str, safe_summary: str = "") -> dict[str, Any]:
        sessions = self._read_sessions()
        for session in sessions:
            if session.get("session_id") != session_id:
                continue
            if not self._can_control_session(session, actor_id):
                raise PermissionError(f"{actor_id} cannot end {session_id}")
            session["status"] = "ended"
            session["door_state"] = "closed"
            session["ended_at"] = datetime.now(timezone.utc).isoformat()
            session["last_privacy_action"] = self._action("end_session", actor_id)
            logging = session.setdefault("content_logging", {})
            logging["content_allowed"] = False
            if safe_summary:
                if logging.get("safe_summary_allowed") is True:
                    session["safe_summary"] = safe_summary
                else:
                    session["safe_summary"] = "withheld"
            self._write_sessions(sessions)
            return deepcopy(session)
        raise KeyError(session_id)

    def safe_summary_allowed(self, session_id: str, participant_id: str) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        if self.can_access(session_id, participant_id):
            return True
        logging = session.get("content_logging", {})
        return bool(logging.get("safe_summary_allowed") is True and session.get("sharing_scope") != "none")

    def leave_door_message(
        self,
        session_id: str,
        sender_id: str,
        message: str,
    ) -> dict[str, Any]:
        cleaned = " ".join(message.strip().split())
        if not cleaned:
            raise ValueError("door message cannot be empty")
        sessions = self._read_sessions()
        for session in sessions:
            if session.get("session_id") != session_id:
                continue
            entry = {
                "message_id": f"door_message_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
                "sender_id": sender_id,
                "message": cleaned[:500],
                "status": "unread",
                "left_at": datetime.now(timezone.utc).isoformat(),
                "trusted_memory": False,
                "grants_access": False,
            }
            session.setdefault("door_messages", []).append(entry)
            session["last_privacy_action"] = self._action("leave_door_message", sender_id)
            self._write_sessions(sessions)
            return deepcopy(session)
        raise KeyError(session_id)

    def read_door_messages(self, session_id: str, reader_id: str) -> list[dict[str, Any]]:
        sessions = self._read_sessions()
        for session in sessions:
            if session.get("session_id") != session_id:
                continue
            if not self._can_control_session(session, reader_id):
                raise PermissionError(f"{reader_id} cannot read door messages for {session_id}")
            messages = session.setdefault("door_messages", [])
            read_at = datetime.now(timezone.utc).isoformat()
            for message in messages:
                if message.get("status") == "unread":
                    message["status"] = "read"
                    message["read_by"] = reader_id
                    message["read_at"] = read_at
            session["last_privacy_action"] = self._action("read_door_messages", reader_id)
            self._write_sessions(sessions)
            return deepcopy(messages)
        raise KeyError(session_id)

    def respond_to_door_message(
        self,
        session_id: str,
        responder_id: str,
        message_id: str,
        response: str,
    ) -> dict[str, Any]:
        cleaned = " ".join(response.strip().split())
        if not cleaned:
            raise ValueError("door message response cannot be empty")
        sessions = self._read_sessions()
        for session in sessions:
            if session.get("session_id") != session_id:
                continue
            if not self._can_control_session(session, responder_id):
                raise PermissionError(f"{responder_id} cannot respond to door messages for {session_id}")
            for message in session.setdefault("door_messages", []):
                if message.get("message_id") == message_id:
                    message["status"] = "responded"
                    message["response"] = cleaned[:500]
                    message["responded_by"] = responder_id
                    message["responded_at"] = datetime.now(timezone.utc).isoformat()
                    session["last_privacy_action"] = self._action("respond_to_door_message", responder_id)
                    self._write_sessions(sessions)
                    return deepcopy(session)
            raise KeyError(message_id)
        raise KeyError(session_id)

    def _set_door_state(self, session_id: str, door_state: str, actor_id: str) -> dict[str, Any]:
        if door_state not in VALID_DOOR_STATES:
            raise ValueError(f"invalid door_state: {door_state}")
        sessions = self._read_sessions()
        for session in sessions:
            if session.get("session_id") != session_id:
                continue
            if not self._can_control_session(session, actor_id):
                raise PermissionError(f"{actor_id} cannot change door state for {session_id}")
            session["door_state"] = door_state
            session["last_privacy_action"] = self._action(f"set_door_{door_state}", actor_id)
            self._write_sessions(sessions)
            return deepcopy(session)
        raise KeyError(session_id)

    def _can_control_session(self, session: dict[str, Any], actor_id: str) -> bool:
        owner = str(session.get("owner", ""))
        if actor_id == owner or actor_id in owner.split("_"):
            return True
        return actor_id in session.get("participants", [])

    def _mark_entry_request(
        self,
        session: dict[str, Any],
        participant_id: str,
        status: str,
        actor_id: str,
        reason: str = "",
    ) -> None:
        for request in reversed(session.setdefault("entry_requests", [])):
            if request.get("requester") == participant_id and request.get("status") == "pending":
                request["status"] = status
                request["resolved_by"] = actor_id
                request["resolved_at"] = datetime.now(timezone.utc).isoformat()
                if reason:
                    request["resolution_reason"] = reason
                return
        session.setdefault("entry_requests", []).append(
            {
                "requester": participant_id,
                "status": status,
                "resolved_by": actor_id,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
                "resolution_reason": reason,
            }
        )

    def _action(
        self,
        action: str,
        actor_id: str,
        target_id: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        data = {
            "action": action,
            "actor_id": actor_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if target_id:
            data["target_id"] = target_id
        if reason:
            data["reason"] = reason
        return data
