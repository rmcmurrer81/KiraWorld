#!/usr/bin/env python3
"""Append-only Qwen 3.5 -> persistent Blackwell v2 two-turn acceptance.

The tool is inert unless every live acknowledgement is supplied.  A live run
uses only exact ``qwen3.5:9b`` with top-level ``think:false`` and ``keep_alive:0``.
It prewarms one inactive persistent-v2 Kira voice worker, obtains one Qwen
generation for each of two natural turns, proves Qwen absent, and then renders
one continuous no-playback WAV on that same worker.  Llama, SAPI, generic
speech, CPU synthesis, static/emergency replies, browser, camera, microphone,
body work, promotion, and normal-default changes are outside this harness.
"""

from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "Core"
for entry in (ROOT, CORE):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from tools import run_kira_persistent_blackwell_v2_application_route_acceptance as v2  # noqa: E402
from tools import run_qwen_text_voice_acceptance as qwen  # noqa: E402


EXPECTED_MODEL = qwen.EXPECTED_MODEL
EXPECTED_DIGEST = qwen.EXPECTED_DIGEST
HARNESS_ID = "qwen35_persistent_blackwell_v2_two_turn_no_playback_v2"
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "qwen35_persistent_v2_two_turn_acceptance"
    / "no_playback"
)
GENERATED_ROOT = (
    ROOT
    / "Voice"
    / "generated"
    / "acceptance"
    / "qwen35_persistent_v2_two_turn"
)
ATTEMPT_PATTERN = re.compile(r"attempt_[0-9]{2}")
CHILD_WATCHDOG_SECONDS = 600.0
PARENT_TIMEOUT_SECONDS = 720.0
ABSENCE_TIMEOUT_SECONDS = 20.0
LAZY_MODEL_RELOAD_TURN_BOUND_SECONDS = 180.0
WORKER_SESSION_ID_PATTERN = re.compile(r"[0-9a-f]{24}")
CHILD_AUTHORIZATION_NAME = "CHILD_AUTHORIZATION.json"
CHILD_AUTHORIZATION_CONSUMED_NAME = "CHILD_AUTHORIZATION_CONSUMED.json"
PARENT_JOB_GATE_NAME = "PARENT_PROCESS_JOB_ASSIGNED.json"

TURN_SPECS: tuple[dict[str, str], ...] = (
    {
        "id": "natural_check_in",
        "text": (
            "Kira, how are you feeling right now? Answer naturally in one brief "
            "sentence, without describing a test or system."
        ),
    },
    {
        "id": "creative_continuity_choice",
        "text": (
            "What would you like to continue together from your recent creative "
            "work? Answer naturally in one brief sentence."
        ),
    },
)

EXACT_CHILD_ENV = {
    "KIRA_MODEL_BACKEND": "ollama",
    "KIRA_MODEL_NAME": EXPECTED_MODEL,
    "KIRA_PERSONHOOD_EVAL_MODE": "0",
    "KIRA_TEXT_VOICE_CHAT_ACTIVE": "1",
    "KIRA_SHELL_TEXT_ONLY": "1",
    "KIRA_WORLD_SHELL_ACTIVE": "0",
    "KIRA_ENABLE_QWEN35_BUFFERED_STREAM_TIMING_CANDIDATE": "1",
    "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE": "0",
    "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE": "0",
    "KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE": "0",
    "KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2": "1",
    "KIRA_DISABLE_BLACKWELL_GPU_VOICE": "1",
    "KIRA_DISABLE_CHATTERBOX_PY311_SIDECAR": "1",
    "KIRA_VOICE_FORCE_SAPI": "0",
    "KIRA_CHATTERBOX_DEVICE": "cuda",
    "KIRA_VOICE_IDLE_UNLOAD_SECONDS": "0",
    "KIRA_UNLOAD_VOICE_AFTER_SPEAK": "0",
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
}

KNOWN_CANNED_REPLIES = {
    "i need to slow down. i do not have a grounded answer to that yet, and i do not want to decorate uncertainty until it sounds real.",
    "i need a moment to decide what i actually want to say aloud.",
    "i'm still sorting out how i feel right now, and i want to answer you without drifting into old project talk.",
    "i caught myself reaching for the same answer i gave you before. i don't want to pretend that repetition is a new moment; i'm still working out what i actually want to say.",
}

NORMAL_STATE_FILE_BOUNDARIES: tuple[Path, ...] = (
    ROOT / "Data" / "memories_kira.json",
    ROOT / "Data" / "relationships" / "relationship_states.json",
    ROOT / "Data" / "privacy" / "privacy_session_state.json",
    ROOT / "Data" / "attention" / "attention_state.json",
    ROOT / "Data" / "logs" / "conversation_log.jsonl",
    ROOT / "Data" / "logs" / "decision_log.jsonl",
    ROOT / "Data" / "daily_life" / "runtime" / "kira_daily_life_state.json",
    ROOT / "Data" / "runtime" / "kira_world_chat_log.jsonl",
    ROOT / "Data" / "runtime" / "kira_world_life_loop_log.jsonl",
)
NORMAL_STATE_DIRECTORY_BOUNDARIES: tuple[Path, ...] = (
    ROOT / "Data" / "daily_life" / "logs" / "events",
    ROOT / "Data" / "memory_promotion" / "candidates",
    ROOT / "Data" / "reading" / "sessions",
)


class AcceptanceError(RuntimeError):
    pass


def utc_now() -> str:
    import datetime as dt

    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def project_relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def exact_state_boundary_snapshot() -> dict[str, Any]:
    """Hash only the normal mutable person-state boundaries this run isolates."""

    files: dict[str, Any] = {}
    for path in NORMAL_STATE_FILE_BOUNDARIES:
        relative = project_relative(path)
        files[relative] = (
            {
                "exists": True,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            if path.is_file()
            else {"exists": False}
        )
    directories: dict[str, Any] = {}
    for directory in NORMAL_STATE_DIRECTORY_BOUNDARIES:
        relative_directory = project_relative(directory)
        entries: dict[str, Any] = {}
        if directory.is_dir():
            for path in sorted(item for item in directory.rglob("*") if item.is_file()):
                relative = path.relative_to(directory).as_posix()
                entries[relative] = {
                    "size": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
        directories[relative_directory] = {
            "exists": directory.is_dir(),
            "files": entries,
        }
    return {"files": files, "directories": directories}


def reserve_attempt(label: str) -> tuple[Path, Path]:
    if ATTEMPT_PATTERN.fullmatch(label) is None:
        raise AcceptanceError("attempt label must match attempt_NN")
    attempt = EVIDENCE_ROOT / label
    generated = GENERATED_ROOT / label
    attempt.mkdir(parents=True, exist_ok=False)
    try:
        generated.mkdir(parents=True, exist_ok=False)
    except BaseException:
        atomic_json(
            attempt / "RESERVATION_FAILURE.json",
            {"at": utc_now(), "reason": "generated_directory_reservation_failed"},
        )
        raise
    return attempt, generated


def consume_child_authorization(
    attempt: Path,
    generated: Path,
    nonce: str,
) -> dict[str, Any]:
    marker = attempt / CHILD_AUTHORIZATION_NAME
    consumed = attempt / CHILD_AUTHORIZATION_CONSUMED_NAME
    if consumed.exists() or not marker.is_file():
        raise AcceptanceError("fresh parent child authorization is missing")
    payload = json.loads(marker.read_text(encoding="utf-8"))
    expected = {
        "nonce": nonce,
        "parent_pid": os.getppid(),
        "attempt": str(attempt.resolve()),
        "generated": str(generated.resolve()),
        "harness_sha256": sha256_file(Path(__file__).resolve()),
    }
    issues = child_authorization_issues(payload, expected)
    if issues:
        raise AcceptanceError(";".join(issues))
    if (attempt / "FINAL_REPORT.json").exists():
        raise AcceptanceError("child refuses to overwrite FINAL_REPORT.json")
    if any(generated.iterdir()):
        raise AcceptanceError("child refuses a nonempty generated attempt directory")
    marker.replace(consumed)
    return payload


def child_authorization_issues(
    payload: Mapping[str, Any], expected: Mapping[str, Any]
) -> list[str]:
    """Pure validator used before consuming the parent-owned marker."""

    issues: list[str] = []
    for key, value in expected.items():
        if payload.get(key) != value:
            issues.append(f"child_authorization_mismatch:{key}")
    if payload.get("single_use") is not True:
        issues.append("child_authorization_not_single_use")
    return sorted(set(issues))


def copy_or_seed(source: Path, target: Path, seed: Any) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_file():
        shutil.copy2(source, target)
    else:
        target.write_text(json.dumps(seed, indent=2) + "\n", encoding="utf-8")
    return target


def normalize_reply(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def canned_reply(value: Any) -> bool:
    normalized = normalize_reply(value)
    return normalized in KNOWN_CANNED_REPLIES or normalized.startswith(
        "[kira thinking backend unavailable:"
    )


def transformation_issues(transformations: Any) -> list[str]:
    rows = transformations if isinstance(transformations, list) else []
    issues: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or row.get("changed") is not True:
            continue
        before = str(row.get("before") or "")
        after = str(row.get("after") or "")
        stage = str(row.get("stage") or f"stage_{index}")
        if canned_reply(after):
            issues.append(f"canned_transformation:{stage}")
        if before and after and min(len(before), len(after)) >= 24:
            similarity = difflib.SequenceMatcher(
                None, normalize_reply(before), normalize_reply(after)
            ).ratio()
            if similarity < 0.35:
                issues.append(f"wholesale_hidden_rewrite:{stage}")
    return issues


def qwen_core_transformation_issues(transformations: Any) -> list[str]:
    rows = transformations if isinstance(transformations, list) else []
    if not rows:
        return ["qwen_core_transform_audit_missing"]
    always_apply_privacy_stages = {
        "suppress_private_emotion_context_leakage",
        "suppress_hypothetical_current_person_invention",
    }
    issues: list[str] = []
    seen_stages: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            issues.append(f"malformed_qwen_core_transform:{index}")
            continue
        stage = str(row.get("stage") or f"stage_{index}")
        if stage in seen_stages:
            issues.append(f"duplicate_qwen_core_transform:{stage}")
        seen_stages.add(stage)
        if row.get("changed") is not False:
            issues.append(f"qwen_core_transform_changed:{stage}")
        if stage in always_apply_privacy_stages:
            if row.get("privacy_boundary_applied_without_model_generation") is not True:
                issues.append(f"qwen_core_privacy_boundary_not_proven:{stage}")
            if row.get("skipped") is True:
                issues.append(f"qwen_core_privacy_boundary_was_skipped:{stage}")
        else:
            if row.get("skipped") is not True:
                issues.append(f"qwen_core_transform_not_skipped:{stage}")
            if row.get("reason") != "qwen_single_generation_preserves_completed_reply":
                issues.append(f"qwen_core_transform_skip_reason_mismatch:{stage}")
        if row.get("additional_model_calls"):
            issues.append(f"qwen_core_transform_added_model_call:{stage}")
    for stage in sorted(always_apply_privacy_stages - seen_stages):
        issues.append(f"qwen_core_privacy_boundary_missing:{stage}")
    return issues


def qwen_outer_transformation_issues(
    transformations: Any,
    *,
    raw_reply: str,
    public_reply: str,
) -> list[str]:
    rows = transformations if isinstance(transformations, list) else []
    if not rows:
        return ["qwen_outer_transform_audit_missing"]
    issues: list[str] = []
    allowed_changed_stage = "clean_kira_world_reply"
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            issues.append(f"malformed_qwen_outer_transform:{index}")
            continue
        stage = str(row.get("stage") or f"stage_{index}")
        if row.get("additional_model_calls"):
            issues.append(f"qwen_outer_transform_added_model_call:{stage}")
        if row.get("changed") is True and stage != allowed_changed_stage:
            issues.append(f"qwen_outer_transform_changed:{stage}")
    if raw_reply and public_reply:
        similarity = difflib.SequenceMatcher(
            None, normalize_reply(raw_reply), normalize_reply(public_reply)
        ).ratio()
        if similarity < 0.70:
            issues.append("qwen_public_reply_not_derivable_from_raw_generation")
    return issues


def speech_contract_issues(
    spoken: Any,
    speech_audit: Any,
) -> list[str]:
    audit = speech_audit if isinstance(speech_audit, Mapping) else {}
    clean = str(spoken or "").strip()
    issues: list[str] = []
    if not clean:
        issues.append("spoken_text_empty_before_voice")
    if audit.get("privacy_safe_for_speech") is not True:
        issues.append("spoken_privacy_not_proven_before_voice")
    if audit.get("reason") != "ok":
        issues.append("spoken_preparation_reason_not_ok")
    if audit.get("non_name_word_coverage_exact") is not True:
        issues.append("spoken_word_coverage_not_exact")
    if qwen.contains_private_marker(clean):
        issues.append("private_marker_in_spoken_text")
    if canned_reply(clean):
        issues.append("canned_or_emergency_spoken_text")
    return issues


def owned_qwen_request_evidence(
    url: str,
    payload: Any,
    *,
    already_sent: int,
) -> dict[str, Any]:
    """Validate the exact request before any network bytes are sent."""

    if already_sent >= 1:
        raise AcceptanceError("second Qwen network request blocked before transmission")
    if url != "http://127.0.0.1:11434/api/chat":
        raise AcceptanceError("Qwen request escaped the exact /api/chat endpoint")
    if not isinstance(payload, Mapping):
        raise AcceptanceError("Qwen request payload was not a mapping")
    evidence = request_evidence(payload)
    if evidence.get("stream") is not True or evidence.get("keep_alive") != 0:
        raise AcceptanceError("Qwen request lifecycle contract mismatch")
    evidence["endpoint"] = url
    return evidence


def all_models_absent(client: qwen.SafeOllamaClient) -> dict[str, Any]:
    rows = client.ps()
    expected = qwen.inspect_expected_model_residency(rows)
    return {
        "passed": not rows and expected.get("clean_absence") is True,
        "resident_models": rows,
        "expected_model": expected,
    }


def wait_for_all_models_absent(
    client: qwen.SafeOllamaClient,
    timeout_seconds: float = ABSENCE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last = all_models_absent(client)
    while last.get("passed") is not True and time.monotonic() < deadline:
        time.sleep(0.25)
        last = all_models_absent(client)
    return last


def request_evidence(payload: Mapping[str, Any]) -> dict[str, Any]:
    qwen.validate_qwen_payload(payload, ordinary_reply=True)
    messages = payload.get("messages") if isinstance(payload.get("messages"), list) else []
    encoded = canonical_json(dict(payload)).encode("utf-8")
    message_bytes = canonical_json(messages).encode("utf-8")
    forbidden = any(
        str(key).casefold() in qwen.FORBIDDEN_PAYLOAD_KEYS
        for key in payload
    )
    return {
        "model": payload.get("model"),
        "think": payload.get("think"),
        "keep_alive": payload.get("keep_alive"),
        "stream": payload.get("stream"),
        "message_count": len(messages),
        "payload_sha256": sha256_bytes(encoded),
        "payload_utf8_bytes": len(encoded),
        "messages_sha256": sha256_bytes(message_bytes),
        "messages_utf8_bytes": len(message_bytes),
        "forbidden_media_key_present": forbidden,
    }


def temporal_content_issues(turn: Mapping[str, Any]) -> list[str]:
    """Reject stale-currentness even when transport and model identity pass."""

    turn_id = str(turn.get("turn_id") or "")
    reply = str(turn.get("public_reply") or "")
    issues: list[str] = []
    if turn_id == "natural_check_in":
        if re.search(
            r"\b(?:(?:just|recently)\s+(?:finished|finishing|completed|completing|"
            r"read|reading|watched|watching|listened|listening|reflected|reflecting|"
            r"worked|working)|wrapped\s+up|after\s+(?:finishing|"
            r"completing|reading|watching|listening|reflecting|working))\b",
            reply,
            flags=re.IGNORECASE,
        ):
            issues.append("natural_check_in_claims_ungrounded_recent_activity")
        if re.search(
            r"\b(?:Miraculous|Elation|book\s+club|fanfic|Paris\s+fanfic|"
            r"Chicago\s+(?:story|project)|Lisa)\b",
            reply,
            flags=re.IGNORECASE,
        ):
            issues.append("natural_check_in_source_drops_historical_context")
    if turn_id == "creative_continuity_choice" and re.search(
        r"\b(?:Miraculous|Elation|book\s+club|fanfic|Paris\s+fanfic|"
        r"Chicago\s+(?:story|project)|Lisa)\b",
        reply,
        flags=re.IGNORECASE,
    ):
        issues.append("creative_continuity_source_drops_historical_context")
    return issues


def text_turn_contract_issues(turn: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    requests = turn.get("requests") if isinstance(turn.get("requests"), list) else []
    audit = turn.get("core_turn_audit") if isinstance(turn.get("core_turn_audit"), Mapping) else {}
    calls = audit.get("model_calls") if isinstance(audit.get("model_calls"), list) else []
    reply = str(turn.get("public_reply") or "")
    spoken = str(turn.get("spoken_text") or "")
    speech_audit = turn.get("speech_audit")
    shell_audit = (
        turn.get("shell_reply_audit")
        if isinstance(turn.get("shell_reply_audit"), Mapping)
        else {}
    )
    absence = turn.get("qwen_absence_before_voice")
    absence = absence if isinstance(absence, Mapping) else {}
    if len(requests) != 1:
        issues.append("qwen_request_count_not_one")
    for row in requests:
        if not isinstance(row, Mapping):
            issues.append("malformed_qwen_request_evidence")
            continue
        if row.get("model") != EXPECTED_MODEL:
            issues.append("request_model_mismatch")
        if row.get("endpoint") != "http://127.0.0.1:11434/api/chat":
            issues.append("request_endpoint_mismatch")
        if row.get("think") is not False:
            issues.append("request_think_not_false")
        if row.get("keep_alive") != 0:
            issues.append("request_keep_alive_not_zero")
        if row.get("stream") is not True:
            issues.append("buffered_stream_not_enabled")
        if row.get("forbidden_media_key_present") is not False:
            issues.append("forbidden_media_key_present")
    if len(calls) != 1:
        issues.append("core_model_call_count_not_one")
    for call in calls:
        if not isinstance(call, Mapping):
            issues.append("malformed_model_call_audit")
            continue
        if call.get("model_name") != EXPECTED_MODEL:
            issues.append("audit_model_mismatch")
        if call.get("response_model") != EXPECTED_MODEL:
            issues.append("response_model_mismatch")
        if call.get("backend") != "ollama" or call.get("outcome") != "completed":
            issues.append("qwen_call_not_completed")
        if call.get("requested_keep_alive") != 0:
            issues.append("audit_keep_alive_not_zero")
        if call.get("single_generation_per_turn_required") is not True:
            issues.append("single_generation_policy_not_proven")
        if call.get("qwen_buffered_stream_timing_candidate_enabled") is not True:
            issues.append("qwen_buffered_timing_not_proven")
        if call.get("first_token_available") is not True:
            issues.append("first_content_timing_missing")
        first_content = call.get("first_content_chunk_seconds")
        if (
            isinstance(first_content, bool)
            or not isinstance(first_content, (int, float))
            or float(first_content) < 0.0
        ):
            issues.append("first_content_timing_not_numeric")
        if call.get("buffered_until_complete") is not True:
            issues.append("qwen_response_not_buffered_until_complete")
        if call.get("stream_done_observed") is not True:
            issues.append("qwen_stream_done_not_observed")
        if call.get("unvalidated_stream_content_displayed") is not False:
            issues.append("unvalidated_stream_content_displayed")
    if audit.get("response_route") not in {
        "ordinary_model_call",
        "ollama_with_private_grounded_draft",
    }:
        issues.append("non_model_or_static_response_route")
    if audit.get("model_name") != EXPECTED_MODEL:
        issues.append("core_turn_model_mismatch")
    raw_reply = str((calls[0] if len(calls) == 1 and isinstance(calls[0], Mapping) else {}).get("raw_reply") or "")
    initial_reply = str(audit.get("initial_pipeline_reply") or "")
    final_core_reply = str(audit.get("final_core_reply") or "")
    if not raw_reply.strip():
        issues.append("raw_qwen_reply_empty")
    if initial_reply.strip() == "":
        issues.append("initial_pipeline_reply_empty")
    if initial_reply != raw_reply:
        issues.append("initial_pipeline_reply_not_raw_generation")
    if final_core_reply != raw_reply:
        issues.append("final_core_reply_not_raw_generation")
    if not reply.strip():
        issues.append("empty_public_reply")
    if canned_reply(reply):
        issues.append("canned_or_emergency_public_reply")
    if qwen.contains_private_marker(reply):
        issues.append("private_marker_in_public_reply")
    issues.extend(temporal_content_issues(turn))
    issues.extend(qwen_core_transformation_issues(audit.get("transformations")))
    if shell_audit.get("completed") is not True:
        issues.append("shell_reply_audit_not_completed")
    if shell_audit.get("qwen_single_generation_per_turn") is not True:
        issues.append("shell_qwen_single_generation_not_proven")
    if str(shell_audit.get("final_shell_reply") or "") != reply:
        issues.append("final_shell_reply_mismatch")
    repair_budget = (
        shell_audit.get("outer_model_repair_budget")
        if isinstance(shell_audit.get("outer_model_repair_budget"), Mapping)
        else {}
    )
    if repair_budget.get("maximum_extra_model_calls") != 0:
        issues.append("shell_extra_model_repair_budget_not_zero")
    if repair_budget.get("extra_model_calls_consumed") != 0:
        issues.append("shell_extra_model_call_consumed")
    issues.extend(
        qwen_outer_transformation_issues(
            shell_audit.get("outer_transformations"),
            raw_reply=raw_reply,
            public_reply=reply,
        )
    )
    issues.extend(speech_contract_issues(spoken, speech_audit))
    if absence.get("passed") is not True:
        issues.append("qwen_not_absent_before_voice")
    return sorted(set(issues))


def turn_contract_issues(turn: Mapping[str, Any]) -> list[str]:
    issues = text_turn_contract_issues(turn)
    voice = turn.get("voice_result") if isinstance(turn.get("voice_result"), Mapping) else {}
    wav = turn.get("wav_validation") if isinstance(turn.get("wav_validation"), Mapping) else {}
    if voice.get("route_id") != v2.EXPECTED_ROUTE_ID:
        issues.append("voice_route_not_exact_v2")
    for key in (
        "cpu_synthesis_attempted",
        "automatic_cpu_fallback_used",
        "generic_voice_used",
        "sapi_voice_used",
        "fallback_used",
        "production_route_promoted",
        "playback",
    ):
        if voice.get(key) is not False:
            issues.append(f"voice_{key}_not_exact_false")
    gpu = voice.get("gpu_proof") if isinstance(voice.get("gpu_proof"), Mapping) else {}
    if gpu.get("actual_gpu_execution") is not True:
        issues.append("actual_gpu_execution_not_proven")
    if wav.get("passed") is not True:
        issues.append("wav_not_valid_non_silent")
    return sorted(set(issues))


WORKER_IDENTITY_KEYS: tuple[str, ...] = (
    "session_owner",
    "session_generation",
    "owned_client_generation",
    "owned_worker_pid",
    "owned_worker_session_id",
)


def persistent_worker_identity(status: Mapping[str, Any] | Any) -> dict[str, Any]:
    payload = status if isinstance(status, Mapping) else {}
    return {key: payload.get(key) for key in WORKER_IDENTITY_KEYS}


def persistent_worker_baseline_issues(status: Mapping[str, Any] | Any) -> list[str]:
    payload = status if isinstance(status, Mapping) else {}
    identity = persistent_worker_identity(payload)
    issues: list[str] = []
    if payload.get("selected_candidate_version") != "v2":
        issues.append("worker_baseline_not_selected_v2")
    if payload.get("owned_worker_running") is not True:
        issues.append("worker_baseline_not_running")
    if payload.get("model_loaded") is not True:
        issues.append("worker_baseline_model_not_loaded")
    if not str(identity.get("session_owner") or ""):
        issues.append("worker_baseline_owner_missing")
    for key in ("session_generation", "owned_client_generation", "owned_worker_pid"):
        value = identity.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            issues.append(f"worker_baseline_invalid:{key}")
    worker_session_id = str(identity.get("owned_worker_session_id") or "")
    if WORKER_SESSION_ID_PATTERN.fullmatch(worker_session_id) is None:
        issues.append("worker_baseline_session_id_invalid")
    return sorted(set(issues))


def _worker_snapshot_issues(
    snapshot: Mapping[str, Any] | Any,
    *,
    baseline_identity: Mapping[str, Any],
    label: str,
    expected_model_loaded: bool,
) -> list[str]:
    payload = snapshot if isinstance(snapshot, Mapping) else {}
    issues: list[str] = []
    if payload.get("selected_candidate_version") != "v2":
        issues.append(f"{label}:selected_candidate_not_v2")
    if payload.get("owned_worker_running") is not True:
        issues.append(f"{label}:owned_worker_not_running")
    if payload.get("model_loaded") is not expected_model_loaded:
        issues.append(f"{label}:model_loaded_not_{str(expected_model_loaded).lower()}")
    observed_identity = persistent_worker_identity(payload)
    for key in WORKER_IDENTITY_KEYS:
        if observed_identity.get(key) != baseline_identity.get(key):
            issues.append(f"{label}:worker_identity_changed:{key}")
    return issues


def serialized_text_boundary_issues(
    turn: Mapping[str, Any],
    *,
    baseline_identity: Mapping[str, Any],
) -> list[str]:
    issues: list[str] = []
    issues.extend(
        _worker_snapshot_issues(
            turn.get("voice_status_before_qwen"),
            baseline_identity=baseline_identity,
            label="before_qwen",
            expected_model_loaded=True,
        )
    )
    audit = turn.get("core_turn_audit")
    audit = audit if isinstance(audit, Mapping) else {}
    calls = audit.get("model_calls") if isinstance(audit.get("model_calls"), list) else []
    call = calls[0] if len(calls) == 1 and isinstance(calls[0], Mapping) else {}
    if call.get("resource_serialization_required") is not True:
        issues.append("qwen_resource_serialization_not_required")
    if call.get("resource_route_confirmed") is not True:
        issues.append("qwen_resource_route_not_confirmed")
    if call.get("resource_lock_acquired") is not True:
        issues.append("qwen_resource_lock_not_acquired")
    if call.get("resource_lock_released") is not True:
        issues.append("qwen_resource_lock_not_released")
    if call.get("voice_model_absence_before_generation_proven") is not True:
        issues.append("voice_model_absence_before_qwen_not_proven")
    suspend = call.get("voice_resource_suspend_before_generation")
    suspend = suspend if isinstance(suspend, Mapping) else {}
    nested = suspend.get("suspend") if isinstance(suspend.get("suspend"), Mapping) else {}
    required_suspend = {
        "voice_model_absence_proven": True,
        "v2_model_absent_after": True,
        "session_owner_preserved": True,
        "session_generation_preserved": True,
        "owned_worker_preserved": True,
        "owned_worker_running_after": True,
        "arbitrary_process_termination_performed": False,
    }
    for key, expected in required_suspend.items():
        if suspend.get(key) is not expected:
            issues.append(f"qwen_suspend_contract_mismatch:{key}")
    required_nested = {
        "model_release_proven": True,
        "model_was_loaded": True,
        "session_owner_preserved": True,
        "session_generation_preserved": True,
        "owned_worker_preserved": True,
        "owned_worker_running_after": True,
        "exact_owned_worker_closed_for_recovery": False,
    }
    for key, expected in required_nested.items():
        if nested.get(key) is not expected:
            issues.append(f"qwen_nested_suspend_contract_mismatch:{key}")
    issues.extend(
        _worker_snapshot_issues(
            turn.get("voice_status_after_text_before_voice"),
            baseline_identity=baseline_identity,
            label="after_qwen_before_voice",
            expected_model_loaded=False,
        )
    )
    return sorted(set(issues))


def serialized_voice_lifecycle_issues(
    turn: Mapping[str, Any],
    *,
    baseline_identity: Mapping[str, Any],
    expected_turn: int,
) -> list[str]:
    issues = serialized_text_boundary_issues(
        turn,
        baseline_identity=baseline_identity,
    )
    voice = turn.get("voice_result")
    voice = voice if isinstance(voice, Mapping) else {}
    if voice.get("persistent_worker_reused") is not True:
        issues.append("persistent_worker_process_or_client_not_reused")
    if voice.get("persistent_model_reused") is not False:
        issues.append("serialized_voice_model_was_unsafely_reused")
    if voice.get("lazy_model_reload_performed") is not True:
        issues.append("serialized_lazy_model_reload_not_proven")
    if voice.get("lazy_voice_load_before_synthesis") is not True:
        issues.append("application_lazy_voice_load_not_proven")
    if voice.get("session_id") != baseline_identity.get("owned_worker_session_id"):
        issues.append("voice_result_worker_session_changed")
    elapsed = turn.get("voice_external_elapsed_seconds")
    if (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or float(elapsed) < 0.0
        or float(elapsed) > LAZY_MODEL_RELOAD_TURN_BOUND_SECONDS
    ):
        issues.append("lazy_model_reload_turn_exceeded_bound")
    lifecycle = voice.get("lifecycle") if isinstance(voice.get("lifecycle"), Mapping) else {}
    expected_counts = {
        "model_load_count": expected_turn + 1,
        "reference_conditioning_count": expected_turn + 1,
        "unload_count": expected_turn,
        "successful_synthesis_count": expected_turn,
    }
    for key, expected in expected_counts.items():
        if lifecycle.get(key) != expected:
            issues.append(f"serialized_lifecycle_count_mismatch:{key}")
    last_unload = (
        lifecycle.get("last_unload")
        if isinstance(lifecycle.get("last_unload"), Mapping)
        else {}
    )
    if last_unload.get("was_loaded") is not True:
        issues.append("serialized_prior_model_unload_not_proven")
    issues.extend(
        _worker_snapshot_issues(
            turn.get("voice_status_after_voice"),
            baseline_identity=baseline_identity,
            label="after_voice",
            expected_model_loaded=True,
        )
    )
    return sorted(set(issues))


def build_isolated_loop(attempt: Path):
    from Core.conversation_loop import ConversationLoop

    isolated = attempt / "isolated_person_state"
    isolated.mkdir(exist_ok=False)
    relationships = copy_or_seed(
        ROOT / "Data/relationships/relationship_states.json",
        isolated / "relationships.json",
        [],
    )
    privacy = copy_or_seed(
        ROOT / "Data/privacy/privacy_session_state.json",
        isolated / "privacy.json",
        [],
    )
    attention = copy_or_seed(
        ROOT / "Data/attention/attention_state.json",
        isolated / "attention.json",
        {},
    )
    memories = copy_or_seed(
        ROOT / "Data/memories_kira.json",
        isolated / "memories_kira.json",
        [],
    )
    loop = ConversationLoop(
        speaker="Kira",
        memory_file=memories,
        relationship_state_file=relationships,
        privacy_session_file=privacy,
        decision_log_file=isolated / "decision_log.jsonl",
        conversation_log_file=isolated / "conversation_log.jsonl",
        attention_state_file=attention,
        daily_life_state_dir=isolated / "daily_life",
        daily_life_log_dir=isolated / "daily_life_logs",
        reading_session_dir=isolated / "reading_sessions",
        reading_recommendation_dir=isolated / "reading_recommendations",
        memory_candidate_dir=isolated / "memory_candidates",
    )
    return loop


def watchdog_worker(stop: threading.Event, attempt: Path) -> None:
    if stop.wait(CHILD_WATCHDOG_SECONDS):
        return
    evidence: dict[str, Any] = {
        "fired": True,
        "at": utc_now(),
        "timeout_seconds": CHILD_WATCHDOG_SECONDS,
    }
    try:
        from Core import voice_output

        evidence["voice_cleanup"] = voice_output.release_voice_output(
            "qwen35_v2_two_turn_child_watchdog"
        )
    except BaseException as exc:
        evidence["voice_cleanup_error"] = type(exc).__name__
    try:
        client = qwen.SafeOllamaClient(max_chat_requests=2)
        rows = client.ps()
        expected = qwen.inspect_expected_model_residency(rows)
        if expected.get("valid_loaded") is True:
            evidence["qwen_cleanup"] = dict(client.unload())
    except BaseException as exc:
        evidence["qwen_cleanup_error"] = type(exc).__name__
    atomic_json(attempt / "WATCHDOG.json", evidence)
    os._exit(124)


def child_run(attempt: Path, generated: Path) -> int:
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": HARNESS_ID,
        "started_at": utc_now(),
        "expected_model": EXPECTED_MODEL,
        "expected_digest": EXPECTED_DIGEST,
        "playback_performed": False,
        "normal_defaults_changed": False,
        "promotion_performed": False,
        "camera_used": False,
        "microphone_used": False,
        "blender_used": False,
        "turn_specs": list(TURN_SPECS),
        "turns": [],
        "issues": [],
        "engineering_pass": False,
    }
    overall_started = time.perf_counter()
    watchdog_stop = threading.Event()
    watchdog = threading.Thread(
        target=watchdog_worker,
        args=(watchdog_stop, attempt),
        name="qwen35-v2-two-turn-watchdog",
        daemon=True,
    )
    watchdog.start()
    sampler = qwen.PeakResourceSampler(interval_seconds=0.2)
    sampler_started = False
    client = qwen.SafeOllamaClient(timeout_seconds=300, max_chat_requests=2)
    release_result: dict[str, Any] | None = None
    release_proven_clean = False
    before_gpu: dict[str, Any] = {}
    before_qwen_protected: dict[str, Any] = {}
    before_v2_protected: dict[str, Any] = {}
    before_normal_state: dict[str, Any] = {}
    try:
        from Core import voice_output
        from Core import conversation_loop as conversation_module
        import requests
        from tools import kira_world_shell_server as shell

        singleton_status = shell._exact_qwen_voice_singleton_status()
        singleton_status.update(
            {
                "harness_voice_same_module_object": (
                    conversation_module.CANONICAL_VOICE_OUTPUT is voice_output
                ),
                "harness_voice_same_resource_lock_object": (
                    conversation_module.CANONICAL_VOICE_OUTPUT.exact_qwen_blackwell_v2_resource_lock()
                    is voice_output.exact_qwen_blackwell_v2_resource_lock()
                ),
            }
        )
        singleton_status["passed"] = bool(
            singleton_status.get("passed") is True
            and singleton_status["harness_voice_same_module_object"] is True
            and singleton_status["harness_voice_same_resource_lock_object"] is True
        )
        report["resource_serialization_singleton"] = singleton_status
        if singleton_status["passed"] is not True:
            raise AcceptanceError(
                "exact Qwen text and persistent-v2 voice singleton was not proven"
            )

        before_qwen_protected = qwen.hash_protected_files()
        before_v2_protected = v2.protected_hashes()
        before_normal_state = exact_state_boundary_snapshot()
        report["protected_before"] = {
            "qwen": before_qwen_protected,
            "v2": before_v2_protected,
            "normal_person_state": before_normal_state,
        }
        installed = qwen.validate_exact_install(client.tags())
        report["installed_model"] = installed
        initial_absence = all_models_absent(client)
        report["ollama_initial_absence"] = initial_absence
        if initial_absence.get("passed") is not True:
            raise AcceptanceError("Ollama had a resident model before the owned run")

        before_gpu = v2._nvidia_snapshot()
        report["gpu_before"] = before_gpu
        if before_gpu.get("query_succeeded") is not True:
            raise AcceptanceError("NVIDIA telemetry unavailable")
        sampler.start()
        sampler_started = True

        config = voice_output.load_kira_production_voice_config()
        config.enabled = True
        config.dry_run = False
        config.play_audio = False
        report["voice_config"] = {
            "engine": config.engine,
            "device": config.chatterbox_device,
            "reference": str(config.chatterbox_reference_audio).replace("\\", "/"),
            "play_audio": config.play_audio,
        }
        if config.engine != "chatterbox_tts" or config.chatterbox_device != "cuda":
            raise AcceptanceError("exact CUDA Chatterbox config unavailable")

        owner = f"kira:qwen35-v2-two-turn:{attempt.name}:{uuid.uuid4().hex}"
        begun = voice_output.begin_persistent_blackwell_voice_session(owner)
        report["voice_session_begin"] = begun
        if begun.get("begun") is not True or begun.get("selected_candidate_version") != "v2":
            raise AcceptanceError("exact v2 voice session did not begin")
        prewarm_started = time.perf_counter()
        prewarm = voice_output.prewarm_persistent_blackwell_voice(owner)
        report["voice_prewarm"] = {
            "external_elapsed_seconds": round(time.perf_counter() - prewarm_started, 6),
            "result": prewarm,
            "issues": v2.load_telemetry_issues(prewarm),
        }
        if report["voice_prewarm"]["issues"]:
            raise AcceptanceError("persistent v2 voice prewarm contract failed")
        baseline_status = voice_output.persistent_blackwell_voice_status()
        baseline_identity = persistent_worker_identity(baseline_status)
        baseline_issues = persistent_worker_baseline_issues(baseline_status)
        report["voice_worker_baseline"] = {
            "status": baseline_status,
            "identity": baseline_identity,
            "issues": baseline_issues,
        }
        if baseline_issues:
            raise AcceptanceError("persistent v2 worker baseline identity failed")
        report["gpu_after_voice_prewarm"] = v2._nvidia_snapshot()

        loop = build_isolated_loop(attempt)
        conversation_changes = {
            "MODEL_BACKEND": "ollama",
            "MODEL_NAME": EXPECTED_MODEL,
            "OLLAMA_ENDPOINT": "http://127.0.0.1:11434/api/chat",
            "MAX_TOKENS": 128,
            "TEMPERATURE": 0.7,
            "OLLAMA_TIMEOUT": 300,
            "OLLAMA_NUM_CTX": 4096,
            "WORLD_SHELL_ACTIVE": False,
            "TEXT_VOICE_CHAT_ACTIVE": True,
            "PERSONHOOD_EVAL_MODE": False,
            "ENABLE_STICKY_STATUS_REPAIR": False,
        }
        captured_requests: list[dict[str, Any]] = []
        active_turn_network = {"enabled": False, "sent": 0}
        original_post = requests.post

        def recording_post(*args: Any, **kwargs: Any):
            url = str(args[0] if args else kwargs.get("url") or "")
            if active_turn_network["enabled"] is not True:
                raise AcceptanceError("Qwen network request occurred outside an owned turn")
            payload = kwargs.get("json")
            evidence = owned_qwen_request_evidence(
                url,
                payload,
                already_sent=int(active_turn_network["sent"]),
            )
            active_turn_network["sent"] += 1
            captured_requests.append(evidence)
            return original_post(*args, **kwargs)

        with qwen.patched_attributes(
            conversation_module, conversation_changes
        ), mock.patch("requests.post", side_effect=recording_post), mock.patch.multiple(
            shell,
            KIRA_CORE_LOOP=loop,
            KIRA_PRIVATE_ACCEPTANCE_AUDIT_ENABLED=True,
            TEXT_ONLY_CHAT_MODE=True,
            CHAT_LOG=attempt / "isolated_person_state" / "shell_chat_log.jsonl",
            LIFE_LOOP_LOG=attempt / "isolated_person_state" / "shell_life_loop_log.jsonl",
        ), mock.patch.object(shell, "_wake_ollama_for_kira_chat", return_value=True):
            for index, spec in enumerate(TURN_SPECS, start=1):
                voice_status_before_qwen = voice_output.persistent_blackwell_voice_status()
                request_start = len(captured_requests)
                active_turn_network.update({"enabled": True, "sent": 0})
                text_started = time.perf_counter()
                try:
                    shell.KIRA_LAST_PRIVATE_REPLY_AUDIT = {}
                    public_reply = str(
                        shell._kira_world_core_reply(
                            "Kira",
                            spec["text"],
                            "home",
                            {"active": "kira", "location": "home"},
                        )
                        or ""
                    ).strip()
                finally:
                    active_turn_network["enabled"] = False
                text_wall = round(time.perf_counter() - text_started, 6)
                shell_audit = copy.deepcopy(shell.KIRA_LAST_PRIVATE_REPLY_AUDIT)
                audit = copy.deepcopy(shell_audit.get("core_turn") or loop.last_turn_audit)
                request_rows = copy.deepcopy(captured_requests[request_start:])
                absence = wait_for_all_models_absent(client)
                voice_status_after_text_before_voice = (
                    voice_output.persistent_blackwell_voice_status()
                )
                spoken, speech_audit = shell._live_spoken_only_payload(public_reply)
                text_turn = {
                    "turn": index,
                    "turn_id": spec["id"],
                    "question": spec["text"],
                    "requests": request_rows,
                    "public_reply": public_reply,
                    "core_turn_audit": audit,
                    "shell_reply_audit": shell_audit,
                    "spoken_text": spoken,
                    "speech_audit": speech_audit,
                    "qwen_absence_before_voice": absence,
                    "voice_status_before_qwen": voice_status_before_qwen,
                    "voice_status_after_text_before_voice": (
                        voice_status_after_text_before_voice
                    ),
                }
                text_issues = text_turn_contract_issues(text_turn)
                text_issues.extend(
                    serialized_text_boundary_issues(
                        text_turn,
                        baseline_identity=baseline_identity,
                    )
                )
                text_issues = sorted(set(text_issues))
                if text_issues:
                    report["turns"].append(
                        {
                            "turn": index,
                            "turn_id": spec["id"],
                            "question": spec["text"],
                            "public_reply": public_reply,
                            "text_wall_seconds": text_wall,
                            **text_turn,
                            "voice_not_attempted": True,
                            "issues": text_issues,
                            "passed": False,
                        }
                    )
                    raise AcceptanceError(
                        f"turn_{index:02d} text contract failed before voice: "
                        + ",".join(text_issues)
                    )
                target = generated / f"turn_{index:02d}.wav"
                voice_started = time.perf_counter()
                voice_result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                    spoken,
                    target,
                    config,
                )
                voice_wall = round(time.perf_counter() - voice_started, 6)
                voice_status_after_voice = voice_output.persistent_blackwell_voice_status()
                wav = v2._validate_wav(target)
                turn = {
                    "turn": index,
                    "turn_id": spec["id"],
                    "question": spec["text"],
                    "question_sha256": sha256_bytes(spec["text"].encode("utf-8")),
                    "public_reply": public_reply,
                    "public_reply_sha256": sha256_bytes(public_reply.encode("utf-8")),
                    "spoken_text": spoken,
                    "spoken_sha256": sha256_bytes(spoken.encode("utf-8")),
                    "speech_audit": speech_audit,
                    "text_wall_seconds": text_wall,
                    "requests": request_rows,
                    "core_turn_audit": audit,
                    "shell_reply_audit": shell_audit,
                    "qwen_absence_before_voice": absence,
                    "voice_status_before_qwen": voice_status_before_qwen,
                    "voice_status_after_text_before_voice": (
                        voice_status_after_text_before_voice
                    ),
                    "voice_status_after_voice": voice_status_after_voice,
                    "voice_external_elapsed_seconds": voice_wall,
                    "voice_result": voice_result,
                    "wav_validation": wav,
                }
                issues = turn_contract_issues(turn)
                issues.extend(
                    f"v2:{item}"
                    for item in v2.turn_issues(
                        voice_result,
                        sentence=spoken,
                        expected_path=target,
                        wav_validation=wav,
                    )
                )
                issues.extend(
                    f"serialized:{item}"
                    for item in serialized_voice_lifecycle_issues(
                        turn,
                        baseline_identity=baseline_identity,
                        expected_turn=index,
                    )
                )
                turn["issues"] = sorted(set(issues))
                turn["passed"] = not turn["issues"]
                report["turns"].append(turn)
                if turn["issues"]:
                    raise AcceptanceError(
                        f"turn_{index:02d} contract failed: {','.join(turn['issues'])}"
                    )

        session_ids = [
            str((turn.get("voice_result") or {}).get("session_id") or "")
            for turn in report["turns"]
        ]
        report["same_voice_worker_session"] = bool(session_ids[0]) and len(set(session_ids)) == 1
        if report["same_voice_worker_session"] is not True:
            raise AcceptanceError("two turns did not reuse one exact v2 worker")
        report["same_persistent_worker_process_and_client"] = all(
            persistent_worker_identity(snapshot) == baseline_identity
            for turn in report["turns"]
            for snapshot in (
                turn.get("voice_status_before_qwen"),
                turn.get("voice_status_after_text_before_voice"),
                turn.get("voice_status_after_voice"),
            )
        )
        if report["same_persistent_worker_process_and_client"] is not True:
            raise AcceptanceError("persistent v2 worker process/client identity changed")

        release_started = time.perf_counter()
        release_result = voice_output.release_voice_output(
            "qwen35_persistent_v2_two_turn_complete"
        )
        after_status = voice_output.persistent_blackwell_voice_status()
        report["voice_release"] = {
            "external_elapsed_seconds": round(time.perf_counter() - release_started, 6),
            "result": release_result,
            "status_after": after_status,
            "issues": v2.release_issues(release_result, after_status),
        }
        if report["voice_release"]["issues"]:
            raise AcceptanceError("exact v2 worker release failed")
        release_proven_clean = True

        final_absence = wait_for_all_models_absent(client)
        report["ollama_final_absence"] = final_absence
        if final_absence.get("passed") is not True:
            raise AcceptanceError("Ollama was not empty after both turns")
        report["gpu_after_release"] = v2._nvidia_snapshot()
        report["gpu_release_issues"] = v2.gpu_release_boundary_issues(
            before_gpu, report["gpu_after_release"]
        )
        if report["gpu_release_issues"]:
            raise AcceptanceError("VRAM did not return to the owned boundary")

        after_qwen_protected = qwen.hash_protected_files()
        after_v2_protected = v2.protected_hashes()
        after_normal_state = exact_state_boundary_snapshot()
        report["protected_after"] = {
            "qwen": after_qwen_protected,
            "v2": after_v2_protected,
            "normal_person_state": after_normal_state,
        }
        report["protected_unchanged"] = (
            before_qwen_protected == after_qwen_protected
            and before_v2_protected == after_v2_protected
            and before_normal_state == after_normal_state
        )
        if report["protected_unchanged"] is not True:
            raise AcceptanceError("protected files changed during acceptance")

        report["checks"] = {
            "exact_qwen_installed": installed.get("digest") == EXPECTED_DIGEST,
            "one_voice_module_and_resource_lock": (
                (report.get("resource_serialization_singleton") or {}).get("passed")
                is True
            ),
            "two_exact_qwen_turns": len(report["turns"]) == 2
            and all(turn.get("passed") is True for turn in report["turns"]),
            "one_generation_per_turn": all(
                len((turn.get("core_turn_audit") or {}).get("model_calls") or []) == 1
                for turn in report["turns"]
            ),
            "qwen_absent_before_each_voice": all(
                (turn.get("qwen_absence_before_voice") or {}).get("passed") is True
                for turn in report["turns"]
            ),
            "same_persistent_v2_worker": report["same_voice_worker_session"] is True,
            "same_persistent_v2_process_and_client": (
                report["same_persistent_worker_process_and_client"] is True
            ),
            "serialized_model_unload_and_lazy_reload_each_turn": all(
                not serialized_voice_lifecycle_issues(
                    turn,
                    baseline_identity=baseline_identity,
                    expected_turn=index,
                )
                for index, turn in enumerate(report["turns"], start=1)
            ),
            "no_playback_fallback_or_promotion": all(
                all(
                    (turn.get("voice_result") or {}).get(key) is False
                    for key in (
                        "playback",
                        "cpu_synthesis_attempted",
                        "automatic_cpu_fallback_used",
                        "generic_voice_used",
                        "sapi_voice_used",
                        "fallback_used",
                        "production_route_promoted",
                    )
                )
                for turn in report["turns"]
            ),
            "exact_release": not report["voice_release"]["issues"],
            "ollama_empty_after": final_absence.get("passed") is True,
            "vram_return": not report["gpu_release_issues"],
            "protected_unchanged": report["protected_unchanged"] is True,
        }
        report["engineering_pass"] = all(report["checks"].values())
        report["status"] = (
            "ENGINEERING_PASS_NO_PLAYBACK_PENDING_OWNER_HEARING"
            if report["engineering_pass"]
            else "ENGINEERING_FAIL_PRESERVED"
        )
        return_code = 0 if report["engineering_pass"] else 1
    except BaseException as exc:
        report["status"] = "ENGINEERING_FAIL_PRESERVED"
        report["exception"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        report["issues"].append(f"{type(exc).__name__}:{exc}")
        return_code = 1
    finally:
        try:
            from Core import voice_output

            if not release_proven_clean:
                report["finally_voice_cleanup"] = voice_output.release_voice_output(
                    "qwen35_persistent_v2_two_turn_finally"
                )
        except BaseException as exc:
            report["finally_voice_cleanup_error"] = type(exc).__name__
            report["engineering_pass"] = False
            report["status"] = "ENGINEERING_FAIL_PRESERVED"
            report["issues"].append("finally_voice_cleanup_failed")
            return_code = 1
        try:
            rows = client.ps()
            expected = qwen.inspect_expected_model_residency(rows)
            if expected.get("valid_loaded") is True:
                report["finally_qwen_unload"] = dict(client.unload())
            report["finally_ollama_absence"] = wait_for_all_models_absent(client)
            if report["finally_ollama_absence"].get("passed") is not True:
                report["engineering_pass"] = False
                report["status"] = "ENGINEERING_FAIL_PRESERVED"
                report["issues"].append("finally_ollama_not_empty")
                return_code = 1
        except BaseException as exc:
            report["finally_qwen_cleanup_error"] = type(exc).__name__
            report["engineering_pass"] = False
            report["status"] = "ENGINEERING_FAIL_PRESERVED"
            report["issues"].append("finally_qwen_cleanup_failed")
            return_code = 1
        if sampler_started:
            report["resources"] = sampler.stop()
        if before_normal_state:
            try:
                final_normal_state = exact_state_boundary_snapshot()
                report["finally_normal_person_state"] = final_normal_state
                report["normal_person_state_unchanged"] = (
                    before_normal_state == final_normal_state
                )
                if report["normal_person_state_unchanged"] is not True:
                    report["engineering_pass"] = False
                    report["status"] = "ENGINEERING_FAIL_PRESERVED"
                    report["issues"].append("normal_person_state_changed")
                    return_code = 1
            except BaseException as exc:
                report["normal_person_state_verification_error"] = type(exc).__name__
                report["engineering_pass"] = False
                report["status"] = "ENGINEERING_FAIL_PRESERVED"
                report["issues"].append("normal_person_state_verification_failed")
                return_code = 1
        watchdog_stop.set()
        watchdog.join(timeout=2)
        report["finished_at"] = utc_now()
        report["total_wall_seconds"] = round(time.perf_counter() - overall_started, 6)
        report["playback_performed"] = False
        report["promotion_performed"] = False
        report["normal_defaults_changed"] = False
        atomic_json(attempt / "FINAL_REPORT.json", report)
    return return_code


def terminate_owned_process_tree(pid: int) -> dict[str, Any]:
    """Terminate only the exact acceptance child and descendants on timeout."""

    result: dict[str, Any] = {
        "attempted": True,
        "root_pid": int(pid),
        "method": "taskkill_exact_pid_tree" if os.name == "nt" else "terminate_exact_child",
    }
    if os.name != "nt":
        result["completed"] = False
        result["reason"] = "non_windows_fallback_requires_caller_terminate"
        return result
    try:
        completed = subprocess.run(
            ["taskkill", "/PID", str(int(pid)), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
        result.update(
            {
                "completed": completed.returncode == 0,
                "exit_code": completed.returncode,
                "stdout": completed.stdout[-4000:],
                "stderr": completed.stderr[-4000:],
            }
        )
    except BaseException as exc:
        result.update(
            {
                "completed": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )
    return result


def apply_parent_wrapper_gate(
    report: Mapping[str, Any], wrapper: Mapping[str, Any]
) -> dict[str, Any]:
    effective = copy.deepcopy(dict(report))
    effective["parent_wrapper_gate"] = copy.deepcopy(dict(wrapper))
    if wrapper.get("passed") is not True:
        effective["engineering_pass"] = False
        effective["status"] = "PARENT_WRAPPER_GATE_FAILED"
    return effective


class WindowsOwnedProcessJob:
    """Kill-on-close job containing only the acceptance child and descendants."""

    def __init__(self) -> None:
        self._handle: Any = None
        self.close_result: dict[str, Any] = {"attempted": False}
        self.assignment: dict[str, Any] = {
            "supported": os.name == "nt",
            "assigned": False,
        }

    def __enter__(self) -> "WindowsOwnedProcessJob":
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        self.close_result = self.close()

    def assign(self, child: subprocess.Popen[Any]) -> dict[str, Any]:
        if os.name != "nt":
            self.assignment = {
                "supported": False,
                "assigned": False,
                "reason": "windows_job_required",
            }
            return dict(self.assignment)
        import ctypes
        from ctypes import wintypes

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL

        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            self.assignment = {
                "supported": True,
                "assigned": False,
                "stage": "CreateJobObjectW",
                "winerror": ctypes.get_last_error(),
            }
            return dict(self.assignment)
        self._handle = handle
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
            handle, 9, ctypes.byref(info), ctypes.sizeof(info)
        ):
            self.assignment = {
                "supported": True,
                "assigned": False,
                "stage": "SetInformationJobObject",
                "winerror": ctypes.get_last_error(),
            }
            return dict(self.assignment)
        process_handle = wintypes.HANDLE(int(getattr(child, "_handle")))
        if not kernel32.AssignProcessToJobObject(handle, process_handle):
            self.assignment = {
                "supported": True,
                "assigned": False,
                "stage": "AssignProcessToJobObject",
                "winerror": ctypes.get_last_error(),
                "child_pid": child.pid,
            }
            return dict(self.assignment)
        self.assignment = {
            "supported": True,
            "assigned": True,
            "kill_on_job_close": True,
            "child_pid": child.pid,
        }
        return dict(self.assignment)

    def terminate(self) -> dict[str, Any]:
        if os.name != "nt" or self._handle is None:
            return {"attempted": False, "completed": False}
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel32.TerminateJobObject.restype = wintypes.BOOL
        completed = bool(kernel32.TerminateJobObject(self._handle, 124))
        return {
            "attempted": True,
            "completed": completed,
            "winerror": 0 if completed else ctypes.get_last_error(),
        }

    def close(self) -> dict[str, Any]:
        if os.name != "nt" or self._handle is None:
            result = {"attempted": False, "completed": self._handle is None}
            self.close_result = result
            return result
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        completed = bool(kernel32.CloseHandle(self._handle))
        self._handle = None
        result = {
            "attempted": True,
            "completed": completed,
            "kill_on_close_applied": bool(self.assignment.get("assigned")),
            "winerror": 0 if completed else ctypes.get_last_error(),
        }
        self.close_result = result
        return result


def wait_for_parent_job_gate(attempt: Path, timeout_seconds: float = 30.0) -> dict[str, Any]:
    gate = attempt / PARENT_JOB_GATE_NAME
    deadline = time.monotonic() + timeout_seconds
    while not gate.is_file() and time.monotonic() < deadline:
        time.sleep(0.05)
    if not gate.is_file():
        raise AcceptanceError("parent process-job assignment gate missing")
    payload = json.loads(gate.read_text(encoding="utf-8"))
    expected = {
        "parent_pid": os.getppid(),
        "child_pid": os.getpid(),
        "attempt": str(attempt.resolve()),
        "harness_sha256": sha256_file(Path(__file__).resolve()),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise AcceptanceError(f"parent process-job gate mismatch:{key}")
    if payload.get("assigned") is not True:
        raise AcceptanceError("acceptance child was not assigned to kill-on-close job")
    return payload


def parent_run(label: str) -> tuple[Path, dict[str, Any]]:
    attempt, generated = reserve_attempt(label)
    child_nonce = uuid.uuid4().hex + uuid.uuid4().hex
    atomic_json(
        attempt / CHILD_AUTHORIZATION_NAME,
        {
            "schema_version": 1,
            "created_at": utc_now(),
            "nonce": child_nonce,
            "parent_pid": os.getpid(),
            "attempt": str(attempt.resolve()),
            "generated": str(generated.resolve()),
            "harness_sha256": sha256_file(Path(__file__).resolve()),
            "single_use": True,
        },
    )
    stdout_path = attempt / "child.stdout.log"
    stderr_path = attempt / "child.stderr.log"
    env = dict(os.environ)
    env.update(EXACT_CHILD_ENV)
    started = time.perf_counter()
    timed_out = False
    timeout_tree_cleanup: dict[str, Any] = {"attempted": False}
    parent_gpu_before = v2._nvidia_snapshot()
    owned_job = WindowsOwnedProcessJob()
    process_job_assignment: dict[str, Any] = {"assigned": False}
    process_job_close: dict[str, Any] = {"attempted": False}
    with owned_job, stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        child = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--child-run",
                "--execute-live",
                "--confirm-exact-qwen35",
                "--confirm-persistent-v2-gpu",
                "--confirm-no-playback",
                "--child-nonce",
                child_nonce,
                "--attempt-path",
                str(attempt.resolve()),
                "--generated-path",
                str(generated.resolve()),
            ],
            cwd=str(ROOT),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        process_job_assignment = owned_job.assign(child)
        atomic_json(
            attempt / PARENT_JOB_GATE_NAME,
            {
                "schema_version": 1,
                "created_at": utc_now(),
                "parent_pid": os.getpid(),
                "child_pid": child.pid,
                "attempt": str(attempt.resolve()),
                "harness_sha256": sha256_file(Path(__file__).resolve()),
                **process_job_assignment,
            },
        )
        try:
            exit_code = child.wait(timeout=PARENT_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            timed_out = True
            timeout_tree_cleanup = owned_job.terminate()
            if timeout_tree_cleanup.get("completed") is not True:
                timeout_tree_cleanup["taskkill_fallback"] = terminate_owned_process_tree(
                    child.pid
                )
            try:
                exit_code = child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                # taskkill may itself have failed.  This fallback targets only
                # the exact child handle; the wrapper still fails regardless.
                child.kill()
                exit_code = child.wait(timeout=10)
    # Closing a successfully assigned KILL_ON_JOB_CLOSE handle removes any
    # persistent-v2 grandchild left by a watchdog or early child failure.
    process_job_close = dict(owned_job.close_result)
    post_child_qwen_cleanup: dict[str, Any] = {
        "attempted": exit_code != 0 or timed_out,
    }
    try:
        cleanup_client = qwen.SafeOllamaClient(timeout_seconds=20, max_chat_requests=1)
        rows = cleanup_client.ps()
        expected = qwen.inspect_expected_model_residency(rows)
        post_child_qwen_cleanup["before"] = {
            "resident_models": rows,
            "expected_model": expected,
        }
        if (exit_code != 0 or timed_out) and expected.get("valid_loaded") is True:
            post_child_qwen_cleanup["unload"] = dict(cleanup_client.unload())
        post_child_qwen_cleanup["after"] = wait_for_all_models_absent(
            cleanup_client, timeout_seconds=20
        )
    except BaseException as exc:
        post_child_qwen_cleanup["error_type"] = type(exc).__name__
        post_child_qwen_cleanup["error"] = str(exc)
    final_path = attempt / "FINAL_REPORT.json"
    wrapper = {
        "schema_version": 1,
        "artifact_kind": f"{HARNESS_ID}_parent_wrapper",
        "started_at": utc_now(),
        "attempt": project_relative(attempt),
        "child_pid": child.pid,
        "child_exit_code": exit_code,
        "timed_out": timed_out,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "stdout_sha256": sha256_file(stdout_path),
        "stderr_sha256": sha256_file(stderr_path),
        "final_report_present": final_path.is_file(),
        "timeout_owned_process_tree_cleanup": timeout_tree_cleanup,
        "process_job_assignment": process_job_assignment,
        "process_job_close": process_job_close,
        "post_child_exact_qwen_cleanup": post_child_qwen_cleanup,
        "gpu_before_child": parent_gpu_before,
        "gpu_after_child": v2._nvidia_snapshot(),
    }
    wrapper["passed"] = bool(
        wrapper["timed_out"] is False
        and wrapper["child_exit_code"] == 0
        and wrapper["final_report_present"] is True
        and process_job_assignment.get("assigned") is True
        and process_job_close.get("completed") is True
        and (post_child_qwen_cleanup.get("after") or {}).get("passed") is True
    )
    atomic_json(attempt / "PARENT_WRAPPER.json", wrapper)
    try:
        report = (
            json.loads(final_path.read_text(encoding="utf-8"))
            if final_path.is_file()
            else {"engineering_pass": False, "status": "FINAL_REPORT_MISSING"}
        )
    except (OSError, json.JSONDecodeError) as exc:
        report = {
            "engineering_pass": False,
            "status": "FINAL_REPORT_UNREADABLE",
            "final_report_error_type": type(exc).__name__,
            "final_report_error": str(exc),
        }
        wrapper["passed"] = False
        atomic_json(attempt / "PARENT_WRAPPER.json", wrapper)
    effective = apply_parent_wrapper_gate(report, wrapper)
    atomic_json(attempt / "EFFECTIVE_RESULT.json", effective)
    return attempt, effective


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--confirm-exact-qwen35", action="store_true")
    parser.add_argument("--confirm-persistent-v2-gpu", action="store_true")
    parser.add_argument("--confirm-no-playback", action="store_true")
    parser.add_argument("--attempt-label", default="attempt_01")
    parser.add_argument("--child-run", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--attempt-path", default="", help=argparse.SUPPRESS)
    parser.add_argument("--generated-path", default="", help=argparse.SUPPRESS)
    parser.add_argument("--child-nonce", default="", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    confirmations = (
        args.execute_live,
        args.confirm_exact_qwen35,
        args.confirm_persistent_v2_gpu,
        args.confirm_no_playback,
    )

    if args.child_run:
        if not all(confirmations):
            parser.error("child mode requires every live confirmation")
        attempt = Path(args.attempt_path).resolve()
        generated = Path(args.generated_path).resolve()
        attempt.relative_to(EVIDENCE_ROOT.resolve())
        generated.relative_to(GENERATED_ROOT.resolve())
        if attempt.name != generated.name or ATTEMPT_PATTERN.fullmatch(attempt.name) is None:
            raise SystemExit("child attempt binding mismatch")
        if not re.fullmatch(r"[0-9a-f]{64}", str(args.child_nonce or "")):
            raise SystemExit("child nonce is missing or malformed")
        consume_child_authorization(attempt, generated, args.child_nonce)
        wait_for_parent_job_gate(attempt)
        return child_run(attempt, generated)

    if not all(confirmations):
        parser.error(
            "live inference is inert by default; all exact-Qwen/v2/no-playback confirmations are required"
        )
    attempt, report = parent_run(args.attempt_label)
    print(
        json.dumps(
            {
                "attempt": project_relative(attempt),
                "status": report.get("status"),
                "engineering_pass": report.get("engineering_pass"),
            },
            indent=2,
        )
    )
    return 0 if report.get("engineering_pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
