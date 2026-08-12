"""Default-off Qwen/Blackwell v3 serialization candidate.

This is an append-only static candidate.  It is not imported by the normal
voice route, performs no playback, and never selects a fallback.  A host may
schedule ``load_only`` on its existing bounded executor; this controller owns
and audits exactly one such request and shares the voice operation lock so
Qwen and CUDA Chatterbox cannot overlap.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from enum import Enum
from typing import Any, Callable

from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v3.persistent_worker import (
    PersistentVoiceRuntimeV3,
    V3ContractError,
    VoiceState,
)


FEATURE_FLAG = "KIRA_ENABLE_BLACKWELL_CPU_PARK_CANDIDATE_V3"
PRODUCTION_ROUTING_AUTHORIZED = False
PLAYBACK_IMPLEMENTED = False


class PrewarmState(str, Enum):
    NONE = "NONE"
    LOAD_ONLY_IN_FLIGHT = "LOAD_ONLY_IN_FLIGHT"
    RESIDENT_OWNED = "RESIDENT_OWNED"
    RELEASE_REQUIRED = "RELEASE_REQUIRED"


def _hash_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class QwenVoiceSerializationV3:
    """One-lock exact-Qwen load-only and CUDA-voice boundary."""

    CLEANUP_REASONS = frozenset(
        {
            "user_submit_cancelled",
            "playback_interrupted",
            "person_changed",
            "person_deactivated",
            "chat_closed",
            "idle_timeout",
            "process_error",
        }
    )

    def __init__(
        self,
        *,
        voice: PersistentVoiceRuntimeV3,
        qwen_backend: Any,
        now: Callable[[], float] | None = None,
    ) -> None:
        self.voice = voice
        self.config = voice.config
        self.qwen_backend = qwen_backend
        self.operation_lock: threading.RLock = voice.operation_lock
        self._now = now or time.monotonic
        self.prewarm_state = PrewarmState.NONE
        self.owned: dict[str, Any] | None = None
        self.audit_events: list[dict[str, Any]] = []
        self._sequence = 0

    def _event(self, event: str, **fields: Any) -> None:
        self._sequence += 1
        self.audit_events.append(
            {
                "sequence": self._sequence,
                "event": event,
                "prewarm_state": self.prewarm_state.value,
                "voice_state": self.voice.state.value,
                "chat_event_created": False,
                "memory_event_created": False,
                "spoken_event_created": False,
                "private_context_included": False,
                **fields,
            }
        )

    def _owner_binding(self, owner: str, session: str, token: str) -> dict[str, str]:
        return {
            "owner_hash": hashlib.sha256(owner.encode("utf-8")).hexdigest(),
            "session_hash": hashlib.sha256(session.encode("utf-8")).hexdigest(),
            "token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
        }

    def _matches(self, owner: str, session: str, token: str) -> bool:
        return bool(self.owned and self.owned["binding"] == self._owner_binding(owner, session, token))

    def _residency(self) -> dict[str, Any]:
        result = self.qwen_backend.residency()
        if not isinstance(result, dict) or result.get("query_succeeded") is not True:
            raise V3ContractError("Qwen residency query did not succeed")
        return result

    def _exact_resident(self, result: dict[str, Any]) -> bool:
        records = result.get("records")
        return bool(
            isinstance(records, list)
            and len(records) == 1
            and records[0].get("model") == self.config["qwen_model"]
            and records[0].get("digest") == self.config["qwen_digest"]
        )

    @staticmethod
    def _absent(result: dict[str, Any]) -> bool:
        return result.get("records") == []

    def _load_only_request(self, *, ttl_seconds: int, token: str) -> dict[str, Any]:
        maximum = int(self.config["qwen_load_only"]["maximum_residency_ttl_seconds"])
        if ttl_seconds <= 0 or ttl_seconds > maximum:
            raise V3ContractError("Qwen load-only TTL is outside the bounded positive range")
        request = {
            "purpose": "load_only",
            "model": self.config["qwen_model"],
            "expected_digest": self.config["qwen_digest"],
            "prompt": "",
            "messages": [],
            "context": [],
            "stream": False,
            "keep_alive_seconds": ttl_seconds,
            "options": {"num_predict": 0},
            "owned_token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
        }
        if request["prompt"] or request["messages"] or request["context"]:
            raise V3ContractError("load-only request contains conversational context")
        return request

    @staticmethod
    def _validate_load_only_response(response: Any) -> None:
        if not isinstance(response, dict):
            raise V3ContractError("load-only response is not an object")
        message = response.get("message")
        message_content = message.get("content") if isinstance(message, dict) else None
        if response.get("response") not in (None, ""):
            raise V3ContractError("load-only produced response text")
        if message_content not in (None, ""):
            raise V3ContractError("load-only produced message content")
        if response.get("eval_count") not in (None, 0):
            raise V3ContractError("load-only evaluated generation tokens")
        if response.get("prompt_eval_count") not in (None, 0):
            raise V3ContractError("load-only evaluated prompt tokens")

    def load_only(
        self,
        *,
        owner: str,
        session: str,
        token: str,
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Own one exact load-only operation; caller may invoke this on an executor."""

        with self.operation_lock:
            if self.voice.state is not VoiceState.PARKED_CPU:
                return {"loaded": False, "reason": "qwen_load_rejects_nonparked_voice"}
            if self.prewarm_state is not PrewarmState.NONE or self.owned is not None:
                return {"loaded": False, "reason": "one_owned_prewarm_already_exists"}
            binding = self._owner_binding(owner, session, token)
            ttl = int(
                ttl_seconds
                if ttl_seconds is not None
                else self.config["qwen_load_only"]["positive_residency_ttl_seconds"]
            )
            request = self._load_only_request(ttl_seconds=ttl, token=token)
            self.prewarm_state = PrewarmState.LOAD_ONLY_IN_FLIGHT
            self.owned = {
                "binding": binding,
                "request_hash": _hash_json(request),
                "started_monotonic": self._now(),
                "expires_monotonic": self._now() + ttl,
                "ttl_seconds": ttl,
            }
            self._event("qwen_v3_load_only_started", purpose="load_only", request_hash=_hash_json(request))
            try:
                response = self.qwen_backend.load_only(dict(request), token=token)
                self._validate_load_only_response(response)
                residency = self._residency()
                if not self._exact_resident(residency):
                    raise V3ContractError("load-only did not prove the exact Qwen digest resident alone")
                self.prewarm_state = PrewarmState.RESIDENT_OWNED
                self._event(
                    "qwen_v3_load_only_resident",
                    purpose="load_only",
                    request_hash=_hash_json(request),
                    response_hash=_hash_json(response),
                    eval_count=response.get("eval_count"),
                )
                return {
                    "loaded": True,
                    "purpose": "load_only",
                    "request": request,
                    "request_hash": _hash_json(request),
                    "response": response,
                    "residency": residency,
                    "owner_binding": binding,
                    "no_conversation_artifacts": True,
                }
            except Exception as exc:
                cleanup = self._cleanup_locked(owner, session, token, "process_error", unload_voice=True)
                return {
                    "loaded": False,
                    "reason": "qwen_load_only_failed_closed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "cleanup": cleanup,
                }

    def prepare_real_reply(
        self,
        *,
        owner: str,
        session: str,
        token: str,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        with self.operation_lock:
            if self.voice.state is not VoiceState.PARKED_CPU:
                raise V3ContractError("real Qwen request rejects CUDA-loaded voice")
            if not self._matches(owner, session, token):
                raise V3ContractError("real Qwen request owner/session/token mismatch")
            if self.prewarm_state is not PrewarmState.RESIDENT_OWNED:
                raise V3ContractError("exact owned Qwen prewarm is not resident")
            residency = self._residency()
            if not self._exact_resident(residency):
                raise V3ContractError("real request cannot bind exact resident Qwen digest")
            request = {
                "model": self.config["qwen_model"],
                "expected_digest": self.config["qwen_digest"],
                "messages": list(messages),
                "stream": True,
                "keep_alive": int(self.config["qwen_load_only"]["real_reply_keep_alive"]),
            }
            self.prewarm_state = PrewarmState.RELEASE_REQUIRED
            self._event("qwen_v3_real_reply_boundary", request_hash=_hash_json(request))
            return request

    def confirm_real_reply_unloaded(self, *, owner: str, session: str, token: str) -> dict[str, Any]:
        with self.operation_lock:
            if not self._matches(owner, session, token):
                raise V3ContractError("real-reply completion owner/session/token mismatch")
            residency = self._residency()
            if not self._absent(residency):
                cleanup = self._cleanup_locked(owner, session, token, "process_error", unload_voice=True)
                return {"confirmed": False, "reason": "qwen_remained_resident_after_keep_alive_zero", "cleanup": cleanup}
            self.prewarm_state = PrewarmState.NONE
            self.owned = None
            self._event("qwen_v3_real_reply_unloaded")
            return {"confirmed": True, "residency": residency}

    def release_for_voice(
        self,
        *,
        owner: str,
        session: str,
        token: str,
        resume_reason: str,
    ) -> dict[str, Any]:
        with self.operation_lock:
            if not self._matches(owner, session, token):
                return {"released": False, "reason": "owned_prewarm_binding_mismatch"}
            unload = self.qwen_backend.unload_owned(
                token=token,
                model=self.config["qwen_model"],
                digest=self.config["qwen_digest"],
            )
            residency = self._residency()
            if not isinstance(unload, dict) or unload.get("unloaded") is not True or not self._absent(residency):
                cleanup = self._cleanup_locked(owner, session, token, "process_error", unload_voice=True)
                return {"released": False, "reason": "exact_qwen_release_not_proven", "cleanup": cleanup}
            self.prewarm_state = PrewarmState.NONE
            self.owned = None
            self._event("qwen_v3_released_before_voice")
            resume = self.voice.resume_cuda(resume_reason)
            return {"released": resume.get("resumed") is True, "qwen_unload": unload, "residency": residency, "voice_resume": resume}

    def _cleanup_locked(
        self,
        owner: str,
        session: str,
        token: str,
        reason: str,
        *,
        unload_voice: bool,
    ) -> dict[str, Any]:
        if reason not in self.CLEANUP_REASONS:
            raise V3ContractError(f"unsupported cleanup reason: {reason}")
        if not self._matches(owner, session, token):
            self._event("qwen_v3_stale_cleanup_token_rejected", reason=reason)
            return {
                "cleaned": False,
                "reason": "stale_or_wrong_owner_token_no_unowned_resource_touched",
                "prewarm_preserved": self.owned is not None,
            }
        errors: list[str] = []
        try:
            cancel = getattr(self.qwen_backend, "cancel_owned", None)
            if callable(cancel):
                cancel(token=token)
            self.qwen_backend.unload_owned(
                token=token,
                model=self.config["qwen_model"],
                digest=self.config["qwen_digest"],
            )
        except Exception as exc:
            errors.append(f"qwen_cleanup:{type(exc).__name__}:{exc}")
        self.prewarm_state = PrewarmState.NONE
        self.owned = None
        voice_cleanup = self.voice.full_unload(reason) if unload_voice else None
        self._event("qwen_v3_owned_cleanup", reason=reason, errors=errors)
        return {
            "cleaned": not errors,
            "reason": reason,
            "qwen_cleanup_errors": errors,
            "voice_cleanup": voice_cleanup,
            "exact_owned_binding_cleared": self.owned is None,
        }

    def cancel_owned(self, *, owner: str, session: str, token: str, reason: str) -> dict[str, Any]:
        with self.operation_lock:
            return self._cleanup_locked(owner, session, token, reason, unload_voice=True)

    def idle_cleanup(self, *, owner: str, session: str, token: str, now_monotonic: float) -> dict[str, Any]:
        with self.operation_lock:
            if not self._matches(owner, session, token):
                return {"cleaned": False, "reason": "idle_cleanup_binding_mismatch"}
            if self.owned is None or now_monotonic < float(self.owned["expires_monotonic"]):
                return {"cleaned": False, "reason": "prewarm_ttl_not_expired"}
            return self._cleanup_locked(owner, session, token, "idle_timeout", unload_voice=True)


__all__ = [
    "FEATURE_FLAG",
    "PLAYBACK_IMPLEMENTED",
    "PRODUCTION_ROUTING_AUTHORIZED",
    "PrewarmState",
    "QwenVoiceSerializationV3",
]
