"""Default-off cancellable Qwen/Blackwell v4 serialization candidate."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from enum import Enum
from typing import Any, Callable, Iterable

from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v4.persistent_worker import (
    EXACT_QWEN_DIGEST,
    EXACT_QWEN_MODEL,
    PersistentVoiceRuntimeV4,
    V4ContractError,
    VoiceState,
)


FEATURE_FLAG = "KIRA_ENABLE_BLACKWELL_CPU_PARK_CANDIDATE_V4"
PRODUCTION_ROUTING_AUTHORIZED = False
PLAYBACK_IMPLEMENTED = False


class QwenOperationState(str, Enum):
    NONE = "NONE"
    LOAD_ONLY_IN_FLIGHT = "LOAD_ONLY_IN_FLIGHT"
    RESIDENT_OWNED = "RESIDENT_OWNED"
    REAL_STREAM_IN_FLIGHT = "REAL_STREAM_IN_FLIGHT"
    CLEANUP_DEBT = "CLEANUP_DEBT"


def _hash_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class QwenVoiceSerializationV4:
    CLEANUP_REASONS = frozenset(
        {
            "user_submit_cancelled",
            "playback_interrupted",
            "person_changed",
            "person_deactivated",
            "chat_closed",
            "idle_timeout",
            "process_error",
            "expired_ttl",
        }
    )

    def __init__(
        self,
        *,
        voice: PersistentVoiceRuntimeV4,
        qwen_backend: Any,
        now: Callable[[], float] | None = None,
    ) -> None:
        self.voice = voice
        self.config = voice.config
        if self.config["qwen_model"] != EXACT_QWEN_MODEL or self.config["qwen_digest"] != EXACT_QWEN_DIGEST:
            raise V4ContractError("coordinator requires canonical exact Qwen identity")
        self.qwen_backend = qwen_backend
        self.operation_lock = voice.operation_lock
        self._control_lock = threading.RLock()
        self._now = now or time.monotonic
        self.state = QwenOperationState.NONE
        self.owned: dict[str, Any] | None = None
        self._seen_token_hashes: set[str] = set()
        self._operation_thread: threading.Thread | None = None
        self._operation_done = threading.Event()
        self._cancel_event = threading.Event()
        self._last_result: dict[str, Any] | None = None
        self.audit_events: list[dict[str, Any]] = []
        self._sequence = 0

    def _event(self, event: str, **fields: Any) -> None:
        self._sequence += 1
        self.audit_events.append(
            {
                "sequence": self._sequence,
                "event": event,
                "qwen_state": self.state.value,
                "voice_state": self.voice.state.value,
                "chat_event_created": False,
                "memory_event_created": False,
                "spoken_event_created": False,
                "private_context_included": False,
                **fields,
            }
        )

    def _binding(self, owner: str, session: str, token: str, *, reject_reuse: bool) -> dict[str, str]:
        for label, value in (("owner", owner), ("session", session), ("token", token)):
            if not isinstance(value, str) or not value.strip():
                raise V4ContractError(f"nonempty {label} binding is required")
        minimum = int(self.config["qwen_load_only"]["minimum_token_characters"])
        if len(token) < minimum:
            raise V4ContractError("cancellation token is below the canonical capability bound")
        hashes = {
            "owner_hash": hashlib.sha256(owner.encode("utf-8")).hexdigest(),
            "session_hash": hashlib.sha256(session.encode("utf-8")).hexdigest(),
            "token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
        }
        if len(set(hashes.values())) != 3:
            raise V4ContractError("owner/session/token bindings must be distinct")
        if reject_reuse and hashes["token_hash"] in self._seen_token_hashes:
            raise V4ContractError("one-time cancellation token was already used")
        return hashes

    def _matches(self, owner: str, session: str, token: str) -> bool:
        try:
            candidate = self._binding(owner, session, token, reject_reuse=False)
        except V4ContractError:
            return False
        current = self.owned.get("binding") if self.owned else None
        return bool(
            isinstance(current, dict)
            and all(hmac.compare_digest(current[key], candidate[key]) for key in candidate)
        )

    def _residency(self) -> dict[str, Any]:
        result = self.qwen_backend.residency()
        if not isinstance(result, dict) or result.get("query_succeeded") is not True:
            raise V4ContractError("Qwen residency query failed")
        records = result.get("records")
        if not isinstance(records, list):
            raise V4ContractError("Qwen residency records are not a list")
        return result

    @staticmethod
    def _absent(result: dict[str, Any]) -> bool:
        return result.get("records") == []

    @staticmethod
    def _exact_resident(result: dict[str, Any]) -> bool:
        return result.get("records") == [{"model": EXACT_QWEN_MODEL, "digest": EXACT_QWEN_DIGEST}]

    def _load_request(self, *, token_hash: str, ttl: int) -> dict[str, Any]:
        maximum = int(self.config["qwen_load_only"]["maximum_residency_ttl_seconds"])
        if ttl <= 0 or ttl > maximum:
            raise V4ContractError("load-only TTL is outside the canonical bound")
        return {
            "purpose": "load_only",
            "model": EXACT_QWEN_MODEL,
            "expected_digest": EXACT_QWEN_DIGEST,
            "prompt": "",
            "messages": [],
            "context": [],
            "stream": False,
            "keep_alive_seconds": ttl,
            "options": {"num_predict": 0},
            "owned_token_hash": token_hash,
        }

    @staticmethod
    def _validate_load_response(response: Any) -> None:
        if not isinstance(response, dict):
            raise V4ContractError("load-only response is not an object")
        message = response.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if response.get("response") not in (None, "") or content not in (None, ""):
            raise V4ContractError("load-only generated hidden text")
        if response.get("eval_count") not in (None, 0):
            raise V4ContractError("load-only evaluated generation tokens")
        if response.get("prompt_eval_count") not in (None, 0):
            raise V4ContractError("load-only evaluated prompt tokens")

    def start_load_only(
        self,
        *,
        owner: str,
        session: str,
        token: str,
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        binding = self._binding(owner, session, token, reject_reuse=True)
        ttl = int(
            ttl_seconds
            if ttl_seconds is not None
            else self.config["qwen_load_only"]["positive_residency_ttl_seconds"]
        )
        request = self._load_request(token_hash=binding["token_hash"], ttl=ttl)
        with self.operation_lock:
            if self.voice.state is not VoiceState.PARKED_CPU:
                return {"started": False, "reason": "qwen_load_requires_parked_voice"}
        with self._control_lock:
            if self.state is not QwenOperationState.NONE or self.owned is not None:
                return {"started": False, "reason": "one_owned_qwen_operation_already_exists"}
            self._seen_token_hashes.add(binding["token_hash"])
            started = self._now()
            self.owned = {
                "binding": binding,
                "request_hash": _hash_json(request),
                "started_monotonic": started,
                "expires_monotonic": started + ttl,
                "ttl_seconds": ttl,
            }
            self.state = QwenOperationState.LOAD_ONLY_IN_FLIGHT
            self._operation_done.clear()
            self._cancel_event.clear()
            self._last_result = None
            thread = threading.Thread(
                target=self._load_worker,
                args=(owner, session, token, request),
                name="blackwell-v4-qwen-load-only",
                daemon=True,
            )
            self._operation_thread = thread
            self._event("qwen_v4_load_only_started", request_hash=_hash_json(request))
            thread.start()
            return {
                "started": True,
                "purpose": "load_only",
                "request_hash": _hash_json(request),
                "binding": binding,
                "expires_monotonic": started + ttl,
            }

    def _load_worker(self, owner: str, session: str, token: str, request: dict[str, Any]) -> None:
        result: dict[str, Any]
        try:
            with self.operation_lock:
                if self.voice.state is not VoiceState.PARKED_CPU:
                    raise V4ContractError("voice left PARKED_CPU before load-only acquired lock")
                response = self.qwen_backend.load_only(
                    dict(request), token=token, cancel_event=self._cancel_event
                )
                if self._cancel_event.is_set():
                    raise V4ContractError("load-only cancelled before acceptance")
                self._validate_load_response(response)
                with self._control_lock:
                    expiry = float(self.owned["expires_monotonic"]) if self.owned else 0.0
                if self._now() >= expiry:
                    raise TimeoutError("load-only completed at or after its TTL")
                residency = self._residency()
                if not self._exact_resident(residency):
                    raise V4ContractError("exact Qwen digest was not solely resident")
                with self._control_lock:
                    if not self._matches(owner, session, token) or self._cancel_event.is_set():
                        raise V4ContractError("load-only ownership changed before commit")
                    self.state = QwenOperationState.RESIDENT_OWNED
                    result = {
                        "loaded": True,
                        "purpose": "load_only",
                        "response": response,
                        "residency": residency,
                        "request_hash": _hash_json(request),
                        "no_conversation_artifacts": True,
                    }
                    self._event("qwen_v4_load_only_resident", response_hash=_hash_json(response))
        except Exception as exc:
            if self._cancel_event.is_set():
                result = {
                    "loaded": False,
                    "reason": "load_only_cancelled_pending_exact_cleanup",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            else:
                reason = "expired_ttl" if isinstance(exc, TimeoutError) else "process_error"
                cleanup = self._cleanup_after_operation_failure(owner, session, token, reason)
                result = {
                    "loaded": False,
                    "reason": "load_only_failed_closed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "cleanup": cleanup,
                }
        finally:
            with self._control_lock:
                self._last_result = result
                self._operation_done.set()

    def wait_load_only(self, timeout_seconds: float = 5.0) -> dict[str, Any]:
        if not self._operation_done.wait(timeout_seconds):
            return {"completed": False, "reason": "load_only_wait_timed_out"}
        with self._control_lock:
            return {"completed": True, "result": dict(self._last_result or {})}

    def run_real_stream(
        self,
        *,
        owner: str,
        session: str,
        token: str,
        messages: list[dict[str, Any]],
        consume_chunk: Callable[[str], None],
    ) -> dict[str, Any]:
        with self._control_lock:
            if not self._matches(owner, session, token):
                raise V4ContractError("real stream owner/session/token mismatch")
            if self.state is not QwenOperationState.RESIDENT_OWNED or self.owned is None:
                raise V4ContractError("real stream requires exact owned resident prewarm")
            if self._now() >= float(self.owned["expires_monotonic"]):
                cleanup = self._cleanup_after_operation_failure(owner, session, token, "expired_ttl")
                return {"completed": False, "reason": "expired_prewarm_refused", "cleanup": cleanup}
            self.state = QwenOperationState.REAL_STREAM_IN_FLIGHT
            self._operation_thread = threading.current_thread()
            self._operation_done.clear()
            self._cancel_event.clear()
        request = {
            "model": EXACT_QWEN_MODEL,
            "expected_digest": EXACT_QWEN_DIGEST,
            "messages": list(messages),
            "stream": True,
            "keep_alive": 0,
        }
        chunks: list[str] = []
        try:
            with self.operation_lock:
                if self.voice.state is not VoiceState.PARKED_CPU:
                    raise V4ContractError("real Qwen stream rejects nonparked voice")
                residency_before = self._residency()
                if not self._exact_resident(residency_before):
                    raise V4ContractError("exact resident Qwen disappeared before real stream")
                stream: Iterable[Any] = self.qwen_backend.stream_real(
                    dict(request), token=token, cancel_event=self._cancel_event
                )
                for value in stream:
                    if self._cancel_event.is_set():
                        raise V4ContractError("real stream cancelled")
                    if not isinstance(value, str):
                        raise V4ContractError("real stream emitted a non-text chunk")
                    chunks.append(value)
                    consume_chunk(value)
                if self._cancel_event.is_set():
                    raise V4ContractError("real stream cancelled at completion boundary")
                residency_after = self._residency()
                if not self._absent(residency_after):
                    raise V4ContractError("real keep_alive=0 did not release exact Qwen")
                with self._control_lock:
                    self.state = QwenOperationState.NONE
                    self.owned = None
                    result = {
                        "completed": True,
                        "request_hash": _hash_json(request),
                        "text": "".join(chunks),
                        "chunk_count": len(chunks),
                        "residency_before": residency_before,
                        "residency_after": residency_after,
                    }
                    self._event("qwen_v4_real_stream_complete", request_hash=_hash_json(request))
                    self._last_result = result
                    return result
        except Exception as exc:
            if self._cancel_event.is_set():
                result = {
                    "completed": False,
                    "reason": "real_stream_cancelled_pending_exact_cleanup",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            else:
                cleanup = self._cleanup_after_operation_failure(
                    owner, session, token, "process_error"
                )
                result = {
                    "completed": False,
                    "reason": "real_stream_failed_closed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "cleanup": cleanup,
                }
            with self._control_lock:
                self._last_result = result
            return result
        finally:
            self._operation_done.set()

    def _exact_qwen_unload(self, token: str, binding: dict[str, str]) -> dict[str, Any]:
        errors: list[str] = []
        try:
            unload = self.qwen_backend.unload_owned(
                token=token, model=EXACT_QWEN_MODEL, digest=EXACT_QWEN_DIGEST
            )
        except Exception as exc:
            unload = None
            errors.append(f"unload_owned:{type(exc).__name__}:{exc}")
        expected = {
            "unloaded": True,
            "model": EXACT_QWEN_MODEL,
            "digest": EXACT_QWEN_DIGEST,
            "token_hash": binding["token_hash"],
        }
        if unload != expected:
            errors.append("unload_owned:exact_result_not_proven")
        try:
            residency = self._residency()
            if not self._absent(residency):
                errors.append("residency:exact_qwen_or_unknown_model_remains")
        except Exception as exc:
            residency = None
            errors.append(f"residency:{type(exc).__name__}:{exc}")
        return {
            "released": not errors,
            "unload_result": unload,
            "residency": residency,
            "errors": errors,
        }

    def _cleanup_after_operation_failure(
        self, owner: str, session: str, token: str, reason: str
    ) -> dict[str, Any]:
        if reason not in self.CLEANUP_REASONS:
            raise V4ContractError(f"unsupported cleanup reason: {reason}")
        with self._control_lock:
            if not self._matches(owner, session, token) or self.owned is None:
                return {"cleaned": False, "reason": "cleanup_binding_mismatch"}
            binding = dict(self.owned["binding"])
        qwen = self._exact_qwen_unload(token, binding)
        voice_cleanup = self.voice.full_unload(reason)
        proven = qwen["released"] is True and voice_cleanup.get("unloaded") is True
        with self._control_lock:
            if proven:
                self.state = QwenOperationState.NONE
                self.owned = None
            else:
                self.state = QwenOperationState.CLEANUP_DEBT
            self._event("qwen_v4_cleanup_proven" if proven else "qwen_v4_cleanup_debt", reason=reason)
        return {
            "cleaned": proven,
            "cleanup_debt": not proven,
            "reason": reason,
            "qwen_cleanup": qwen,
            "voice_cleanup": voice_cleanup,
            "ownership_cleared": self.owned is None,
        }

    def cancel_owned(
        self, *, owner: str, session: str, token: str, reason: str
    ) -> dict[str, Any]:
        if reason not in self.CLEANUP_REASONS:
            raise V4ContractError(f"unsupported cancellation reason: {reason}")
        with self._control_lock:
            if not self._matches(owner, session, token) or self.owned is None:
                return {
                    "cleaned": False,
                    "reason": "stale_or_wrong_binding_no_unowned_resource_touched",
                }
            thread = self._operation_thread
            self._cancel_event.set()
            self._event("qwen_v4_cancel_entered", reason=reason)
        cancel_error = ""
        try:
            self.qwen_backend.cancel_owned(token=token)
        except Exception as exc:
            cancel_error = f"{type(exc).__name__}:{exc}"
        join_bound = float(self.config["operation_bounds_seconds"]["qwen_cancel_join"])
        if thread is not None and thread is not threading.current_thread() and thread.is_alive():
            thread.join(join_bound)
        if thread is not None and thread.is_alive():
            with self._control_lock:
                self.state = QwenOperationState.CLEANUP_DEBT
                self._event("qwen_v4_cancel_join_timed_out", reason=reason)
            return {
                "cleaned": False,
                "cleanup_debt": True,
                "reason": "bounded_cancel_join_timed_out",
                "cancel_error": cancel_error,
                "ownership_cleared": False,
            }
        with self.operation_lock:
            cleanup = self._cleanup_after_operation_failure(owner, session, token, reason)
        cleanup["cancel_error"] = cancel_error
        return cleanup

    def idle_cleanup(
        self, *, owner: str, session: str, token: str, now_monotonic: float
    ) -> dict[str, Any]:
        with self._control_lock:
            if not self._matches(owner, session, token) or self.owned is None:
                return {"cleaned": False, "reason": "idle_cleanup_binding_mismatch"}
            expiry = float(self.owned["expires_monotonic"])
        if now_monotonic < expiry:
            return {"cleaned": False, "reason": "prewarm_ttl_not_expired"}
        return self.cancel_owned(
            owner=owner, session=session, token=token, reason="idle_timeout"
        )


__all__ = [
    "FEATURE_FLAG",
    "PLAYBACK_IMPLEMENTED",
    "PRODUCTION_ROUTING_AUTHORIZED",
    "QwenOperationState",
    "QwenVoiceSerializationV4",
]
