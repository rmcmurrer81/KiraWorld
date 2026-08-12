"""Default-off, static-only Qwen/Blackwell v5 serialization candidate."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import threading
import time
from enum import Enum
from typing import Any, Callable

from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v5.persistent_worker import (
    EXACT_QWEN_DIGEST,
    EXACT_QWEN_MODEL,
    PersistentVoiceRuntimeV5,
    V5BoundaryTimeout,
    V5ContractError,
    VoiceState,
)


FEATURE_FLAG = "KIRA_ENABLE_BLACKWELL_CPU_PARK_CANDIDATE_V5"
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


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdef" for char in value
    )


class QwenVoiceSerializationV5:
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
            "malformed_request",
            "policy_drift",
            "cleanup_debt_retry",
        }
    )

    def __init__(
        self,
        *,
        voice: PersistentVoiceRuntimeV5,
        qwen_backend: Any,
        now: Callable[[], float] | None = None,
    ) -> None:
        self.voice = voice
        config = voice.config
        if config["qwen_model"] != EXACT_QWEN_MODEL or config["qwen_digest"] != EXACT_QWEN_DIGEST:
            raise V5ContractError("coordinator requires canonical exact Qwen identity")
        self._config_bytes = json.dumps(
            config, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        self._policy_digest = voice.policy_digest
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
        self._residency_sequence = 0
        self._residency_ids: set[str] = set()
        self.audit_events: list[dict[str, Any]] = []
        self._sequence = 0

    @property
    def config(self) -> dict[str, Any]:
        return json.loads(self._config_bytes.decode("utf-8"))

    def _require_policy(self) -> None:
        self.voice._require_policy()
        if self.voice.policy_digest != self._policy_digest:
            raise V5ContractError("coordinator/voice immutable policy digest mismatch")
        observed = json.dumps(
            self.voice.config, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        if observed != self._config_bytes:
            raise V5ContractError("coordinator canonical policy bytes drift")

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

    def _binding(self, owner: str, session: str, token: str, reject_reuse: bool) -> dict[str, str]:
        for label, value in (("owner", owner), ("session", session), ("token", token)):
            if not isinstance(value, str) or not value.strip():
                raise V5ContractError(f"nonempty {label} binding is required")
        minimum = int(self.config["qwen_load_only"]["minimum_token_characters"])
        if len(token) < minimum:
            raise V5ContractError("cancellation token is below the canonical bound")
        hashes = {
            "owner_hash": hashlib.sha256(owner.encode("utf-8")).hexdigest(),
            "session_hash": hashlib.sha256(session.encode("utf-8")).hexdigest(),
            "token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
        }
        if len(set(hashes.values())) != 3:
            raise V5ContractError("owner/session/token bindings must be distinct")
        if reject_reuse and hashes["token_hash"] in self._seen_token_hashes:
            raise V5ContractError("one-time cancellation token was already used")
        return hashes

    def _matches(self, owner: str, session: str, token: str) -> bool:
        try:
            candidate = self._binding(owner, session, token, False)
        except V5ContractError:
            return False
        current = self.owned.get("binding") if self.owned else None
        return bool(
            isinstance(current, dict)
            and all(hmac.compare_digest(current[key], candidate[key]) for key in candidate)
        )

    def _residency(self, phase: str) -> dict[str, Any]:
        result = self.voice.call_bounded(
            "qwen_residency", lambda: self.qwen_backend.residency(phase=phase)
        )
        keys = {
            "query_succeeded",
            "records",
            "serialization_lease_id",
            "lease_exclusive",
            "sample_id",
            "sample_sequence",
            "captured_monotonic",
            "phase",
        }
        if not isinstance(result, dict) or set(result) != keys:
            raise V5ContractError("Qwen residency schema is not exact")
        now = float(self._now())
        captured = result["captured_monotonic"]
        maximum_age = float(self.config["resource_bounds"]["maximum_evidence_age_seconds"])
        sequence = result["sample_sequence"]
        sample_id = result["sample_id"]
        if (
            result["query_succeeded"] is not True
            or result["serialization_lease_id"] != self.voice.serialization_lease_id
            or result["lease_exclusive"] is not True
            or result["phase"] != phase
            or not isinstance(result["records"], list)
            or not _is_sha256(sample_id)
            or isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or sequence <= self._residency_sequence
            or sample_id in self._residency_ids
            or isinstance(captured, bool)
            or not isinstance(captured, (int, float))
            or not math.isfinite(float(captured))
            or float(captured) > now
            or now - float(captured) > maximum_age
        ):
            raise V5ContractError("fresh exclusive-lease Qwen residency was not proven")
        self._residency_sequence = sequence
        self._residency_ids.add(sample_id)
        return dict(result)

    @staticmethod
    def _absent(result: dict[str, Any]) -> bool:
        return result.get("records") == []

    @staticmethod
    def _exact_resident(result: dict[str, Any]) -> bool:
        return result.get("records") == [{"model": EXACT_QWEN_MODEL, "digest": EXACT_QWEN_DIGEST}]

    def _load_request(self, token_hash: str, ttl: int) -> dict[str, Any]:
        maximum = int(self.config["qwen_load_only"]["maximum_residency_ttl_seconds"])
        if ttl <= 0 or ttl > maximum:
            raise V5ContractError("load-only TTL is outside the canonical bound")
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
            "serialization_lease_id": self.voice.serialization_lease_id,
        }

    @staticmethod
    def _validate_load_response(response: Any, request_hash: str) -> None:
        keys = {
            "model",
            "digest",
            "request_hash",
            "response",
            "message",
            "eval_count",
            "prompt_eval_count",
            "serialization_lease_id",
        }
        if not isinstance(response, dict) or set(response) != keys:
            raise V5ContractError("load-only response schema is not exact")
        message = response["message"]
        if (
            response["model"] != EXACT_QWEN_MODEL
            or response["digest"] != EXACT_QWEN_DIGEST
            or response["request_hash"] != request_hash
            or response["response"] != ""
            or message != {"content": ""}
            or response["eval_count"] != 0
            or response["prompt_eval_count"] != 0
        ):
            raise V5ContractError("load-only generated content or identity drift")

    def start_load_only(
        self,
        *,
        owner: str,
        session: str,
        token: str,
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        try:
            self._require_policy()
            binding = self._binding(owner, session, token, True)
            ttl = int(
                ttl_seconds
                if ttl_seconds is not None
                else self.config["qwen_load_only"]["positive_residency_ttl_seconds"]
            )
            request = self._load_request(binding["token_hash"], ttl)
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
                    name="blackwell-v5-qwen-load-only",
                    daemon=True,
                )
                self._operation_thread = thread
                self._event("qwen_v5_load_only_started", request_hash=_hash_json(request))
                thread.start()
                return {
                    "started": True,
                    "purpose": "load_only",
                    "request_hash": _hash_json(request),
                    "binding": binding,
                    "expires_monotonic": started + ttl,
                }
        except Exception as exc:
            cleanup = self.voice.full_unload("policy_or_start_failure")
            return {
                "started": False,
                "reason": "qwen_load_start_failed_closed",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "voice_cleanup": cleanup,
            }

    def _load_worker(self, owner: str, session: str, token: str, request: dict[str, Any]) -> None:
        result: dict[str, Any]
        try:
            with self.operation_lock:
                self._require_policy()
                if self.voice.state is not VoiceState.PARKED_CPU:
                    raise V5ContractError("voice left PARKED_CPU before load-only lock")
                absent_before = self._residency("qwen_load_before")
                if not self._absent(absent_before):
                    raise V5ContractError("Qwen was resident before owned load-only")
                request_hash = _hash_json(request)
                response = self.voice.call_bounded(
                    "qwen_load",
                    lambda: self.qwen_backend.load_only(
                        dict(request), token=token, cancel_event=self._cancel_event
                    ),
                )
                if self._cancel_event.is_set():
                    raise V5ContractError("load-only cancelled before acceptance")
                self._validate_load_response(response, request_hash)
                if response["serialization_lease_id"] != self.voice.serialization_lease_id:
                    raise V5ContractError("load-only response lease mismatch")
                with self._control_lock:
                    expiry = float(self.owned["expires_monotonic"]) if self.owned else 0.0
                if self._now() >= expiry:
                    raise TimeoutError("load-only completed at or after its TTL")
                residency = self._residency("qwen_load_commit")
                if not self._exact_resident(residency):
                    raise V5ContractError("exact Qwen digest was not solely resident")
                with self._control_lock:
                    if not self._matches(owner, session, token) or self._cancel_event.is_set():
                        raise V5ContractError("load-only ownership changed before commit")
                    self.state = QwenOperationState.RESIDENT_OWNED
                    result = {
                        "loaded": True,
                        "purpose": "load_only",
                        "response": response,
                        "residency_before": absent_before,
                        "residency": residency,
                        "request_hash": request_hash,
                        "no_conversation_artifacts": True,
                    }
                    self._event("qwen_v5_load_only_resident", response_hash=_hash_json(response))
        except Exception as exc:
            if self._cancel_event.is_set():
                cleanup = self._cleanup_after_operation_failure(
                    owner, session, token, "process_error"
                )
                result = {
                    "loaded": False,
                    "reason": "load_only_cancelled_and_auto_cleanup_attempted",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "cleanup": cleanup,
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

    @staticmethod
    def _validate_messages(messages: Any) -> list[dict[str, str]]:
        if not isinstance(messages, list) or not messages:
            raise V5ContractError("real stream messages must be a nonempty list")
        closed: list[dict[str, str]] = []
        for index, item in enumerate(messages):
            if not isinstance(item, dict) or set(item) != {"role", "content"}:
                raise V5ContractError(f"real stream message {index} violates closed schema")
            if item["role"] not in {"system", "user", "assistant"}:
                raise V5ContractError(f"real stream message {index} has unsupported role")
            if not isinstance(item["content"], str) or not item["content"].strip():
                raise V5ContractError(f"real stream message {index} has empty content")
            closed.append({"role": item["role"], "content": item["content"]})
        return closed

    def run_real_stream(
        self,
        *,
        owner: str,
        session: str,
        token: str,
        messages: list[dict[str, Any]],
        consume_chunk: Callable[[str], None],
    ) -> dict[str, Any]:
        mutated = False
        try:
            self._require_policy()
            closed_messages = self._validate_messages(messages)
            if not callable(consume_chunk):
                raise V5ContractError("real stream chunk consumer must be callable")
            with self._control_lock:
                if not self._matches(owner, session, token):
                    raise V5ContractError("real stream owner/session/token mismatch")
                if self.state is not QwenOperationState.RESIDENT_OWNED or self.owned is None:
                    raise V5ContractError("real stream requires exact owned resident prewarm")
                if self._now() >= float(self.owned["expires_monotonic"]):
                    raise TimeoutError("owned prewarm expired before real stream")
                binding = dict(self.owned["binding"])
            request = {
                "model": EXACT_QWEN_MODEL,
                "expected_digest": EXACT_QWEN_DIGEST,
                "messages": closed_messages,
                "stream": True,
                "keep_alive": 0,
                "owned_token_hash": binding["token_hash"],
                "serialization_lease_id": self.voice.serialization_lease_id,
            }
            request_hash = _hash_json(request)
            with self._control_lock:
                self.state = QwenOperationState.REAL_STREAM_IN_FLIGHT
                self._operation_thread = threading.current_thread()
                self._operation_done.clear()
                self._cancel_event.clear()
                mutated = True
            with self.operation_lock:
                if self.voice.state is not VoiceState.PARKED_CPU:
                    raise V5ContractError("real Qwen stream rejects nonparked voice")
                residency_before = self._residency("qwen_real_stream_before")
                if not self._exact_resident(residency_before):
                    raise V5ContractError("exact resident Qwen disappeared before real stream")
                envelope = self.voice.call_bounded(
                    "qwen_stream",
                    lambda: self.qwen_backend.stream_real(
                        dict(request), token=token, cancel_event=self._cancel_event
                    ),
                )
                keys = {
                    "model",
                    "digest",
                    "request_hash",
                    "chunks",
                    "final_text_sha256",
                    "keep_alive",
                    "serialization_lease_id",
                }
                if not isinstance(envelope, dict) or set(envelope) != keys:
                    raise V5ContractError("real stream backend envelope is not exact")
                chunks = envelope["chunks"]
                if not isinstance(chunks, list) or not chunks or not all(
                    isinstance(value, str) and value for value in chunks
                ):
                    raise V5ContractError("real stream returned empty/non-text chunks")
                text = "".join(chunks)
                if (
                    envelope["model"] != EXACT_QWEN_MODEL
                    or envelope["digest"] != EXACT_QWEN_DIGEST
                    or envelope["request_hash"] != request_hash
                    or envelope["final_text_sha256"] != hashlib.sha256(text.encode("utf-8")).hexdigest()
                    or envelope["keep_alive"] != 0
                    or envelope["serialization_lease_id"] != self.voice.serialization_lease_id
                    or not text.strip()
                ):
                    raise V5ContractError("real stream response identity/text binding mismatch")
                for value in chunks:
                    if self._cancel_event.is_set():
                        raise V5ContractError("real stream cancelled")
                    self.voice.call_bounded("consume_chunk", lambda value=value: consume_chunk(value))
                residency_after = self._residency("qwen_real_stream_after")
                if not self._absent(residency_after):
                    raise V5ContractError("real keep_alive=0 did not release exact Qwen")
                with self._control_lock:
                    self.state = QwenOperationState.NONE
                    self.owned = None
                    result = {
                        "completed": True,
                        "request_hash": request_hash,
                        "text": text,
                        "text_sha256": envelope["final_text_sha256"],
                        "chunk_count": len(chunks),
                        "response_model": envelope["model"],
                        "response_digest": envelope["digest"],
                        "residency_before": residency_before,
                        "residency_after": residency_after,
                    }
                    self._event("qwen_v5_real_stream_complete", request_hash=request_hash)
                    self._last_result = result
                    return result
        except Exception as exc:
            reason = "expired_ttl" if isinstance(exc, TimeoutError) else (
                "malformed_request" if not mutated else "process_error"
            )
            cleanup: dict[str, Any]
            with self._control_lock:
                has_owned = self.owned is not None and self._matches(owner, session, token)
            if has_owned:
                with self.operation_lock:
                    cleanup = self._cleanup_after_operation_failure(owner, session, token, reason)
            else:
                voice_cleanup = self.voice.full_unload(reason)
                cleanup = {
                    "cleaned": voice_cleanup.get("unloaded") is True,
                    "cleanup_debt": voice_cleanup.get("unloaded") is not True,
                    "voice_cleanup": voice_cleanup,
                    "ownership_cleared": self.owned is None,
                }
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
            unload = self.voice.call_bounded(
                "qwen_unload",
                lambda: self.qwen_backend.unload_owned(
                    token=token, model=EXACT_QWEN_MODEL, digest=EXACT_QWEN_DIGEST
                ),
            )
        except Exception as exc:
            unload = None
            errors.append(f"unload_owned:{type(exc).__name__}:{exc}")
        expected = {
            "unloaded": True,
            "model": EXACT_QWEN_MODEL,
            "digest": EXACT_QWEN_DIGEST,
            "token_hash": binding["token_hash"],
            "serialization_lease_id": self.voice.serialization_lease_id,
        }
        if unload != expected:
            errors.append("unload_owned:exact_result_not_proven")
        try:
            residency = self._residency("qwen_cleanup_after_unload")
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
            raise V5ContractError(f"unsupported cleanup reason: {reason}")
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
            self._event("qwen_v5_cleanup_proven" if proven else "qwen_v5_cleanup_debt", reason=reason)
        return {
            "cleaned": proven,
            "cleanup_debt": not proven,
            "reason": reason,
            "qwen_cleanup": qwen,
            "voice_cleanup": voice_cleanup,
            "ownership_cleared": self.owned is None,
        }

    def cancel_owned(self, *, owner: str, session: str, token: str, reason: str) -> dict[str, Any]:
        if reason not in self.CLEANUP_REASONS:
            raise V5ContractError(f"unsupported cancellation reason: {reason}")
        with self._control_lock:
            if not self._matches(owner, session, token) or self.owned is None:
                return {"cleaned": False, "reason": "stale_or_wrong_binding_no_resource_touched"}
            thread = self._operation_thread
            self._cancel_event.set()
            self._event("qwen_v5_cancel_entered", reason=reason)
        try:
            cancel_value = self.voice.call_bounded(
                "qwen_cancel", lambda: self.qwen_backend.cancel_owned(token=token)
            )
            if cancel_value != {
                "cancelled": True,
                "token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
                "serialization_lease_id": self.voice.serialization_lease_id,
            }:
                raise V5ContractError("exact backend cancellation was not proven")
            cancel_error = ""
        except Exception as exc:
            cancel_error = f"{type(exc).__name__}:{exc}"
            with self._control_lock:
                self.state = QwenOperationState.CLEANUP_DEBT
                self._event("qwen_v5_cancel_boundary_failed", reason=reason)
            return {
                "cleaned": False,
                "cleanup_debt": True,
                "reason": "bounded_backend_cancel_failed",
                "cancel_error": cancel_error,
                "ownership_cleared": False,
            }
        join_bound = float(self.config["operation_bounds_seconds"]["qwen_cancel_join"])
        if thread is not None and thread is not threading.current_thread() and thread.is_alive():
            thread.join(join_bound)
        if thread is not None and thread.is_alive():
            with self._control_lock:
                self.state = QwenOperationState.CLEANUP_DEBT
                self._event("qwen_v5_cancel_join_timed_out", reason=reason)
            return {
                "cleaned": False,
                "cleanup_debt": True,
                "reason": "bounded_cancel_join_timed_out",
                "cancel_error": cancel_error,
                "ownership_cleared": False,
            }
        with self._control_lock:
            if self.owned is None and self.state is QwenOperationState.NONE:
                prior = dict(self._last_result or {})
                prior_cleanup = prior.get("cleanup") if isinstance(prior, dict) else None
                if isinstance(prior_cleanup, dict) and prior_cleanup.get("cleaned") is True:
                    return {
                        "cleaned": True,
                        "cleanup_debt": False,
                        "reason": reason,
                        "cancel_error": cancel_error,
                        "automatic_worker_cleanup": prior_cleanup,
                        "ownership_cleared": True,
                    }
        with self.operation_lock:
            cleanup = self._cleanup_after_operation_failure(owner, session, token, reason)
        cleanup["cancel_error"] = cancel_error
        return cleanup

    def recover_cleanup_debt(self, *, owner: str, session: str, token: str) -> dict[str, Any]:
        with self._control_lock:
            if self.state is not QwenOperationState.CLEANUP_DEBT:
                return {"recovered": False, "reason": "no_cleanup_debt"}
            if not self._matches(owner, session, token) or self.owned is None:
                return {"recovered": False, "reason": "cleanup_debt_binding_mismatch"}
        with self.operation_lock:
            cleanup = self._cleanup_after_operation_failure(
                owner, session, token, "cleanup_debt_retry"
            )
        return {"recovered": cleanup["cleaned"], "cleanup": cleanup}

    def idle_cleanup(
        self, *, owner: str, session: str, token: str, now_monotonic: float
    ) -> dict[str, Any]:
        with self._control_lock:
            if not self._matches(owner, session, token) or self.owned is None:
                return {"cleaned": False, "reason": "idle_cleanup_binding_mismatch"}
            expiry = float(self.owned["expires_monotonic"])
        if now_monotonic < expiry:
            return {"cleaned": False, "reason": "prewarm_ttl_not_expired"}
        return self.cancel_owned(owner=owner, session=session, token=token, reason="idle_timeout")


__all__ = [
    "FEATURE_FLAG",
    "PLAYBACK_IMPLEMENTED",
    "PRODUCTION_ROUTING_AUTHORIZED",
    "QwenOperationState",
    "QwenVoiceSerializationV5",
]
