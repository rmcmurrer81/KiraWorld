#!/usr/bin/env python3
"""Bounded exact-Qwen-3.5 Kira Turing/psychology owner-supervised evaluation.

The module is inert unless every public live confirmation is supplied.  A
live parent reserves a new append-only attempt, starts one kill-on-close owned
child, and writes wrapper evidence.  The child asks Kira's voluntary public
permission, then (only after a clear ``Yes, continue``) runs the six prompts
sealed by the preparation contract.

Each public reply is one exact ``qwen3.5:9b`` generation.  Qwen must be absent
before the exact persistent Blackwell-v2 CUDA voice route may synthesize the
public SPOKEN text.  The generated WAV is played synchronously, then the voice
model is suspended while the owned v2 worker/session remains intact.  Technical
playback completion is kept separate from the owner's explicit post-playback
self-report.  Llama, SAPI, generic voice, CPU voice fallback, a second repair
generation, camera, microphone, Qwen vision, media, browser, Blender, and body
operations are outside this harness.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import re
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

from tools import prepare_qwen35_kira_turing_psych_voice_evaluation as prepared  # noqa: E402
from tools import run_qwen35_persistent_v2_two_turn_acceptance as base  # noqa: E402


EXPECTED_MODEL = prepared.EXPECTED_MODEL
EXPECTED_DIGEST = prepared.EXPECTED_DIGEST
EXPECTED_ROUTE_ID = prepared.APPROVED_VOICE_ROUTE
HARNESS_ID = "kira_qwen35_turing_psych_voice_owner_evaluation_v2"
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260809"
    / "kira_qwen35_turing_psych_voice_owner_evaluation"
)
GENERATED_ROOT = (
    ROOT
    / "Voice"
    / "generated"
    / "acceptance"
    / "kira_qwen35_turing_psych_voice_owner_evaluation"
)
PREPARATION_ARTIFACT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260809"
    / "kira_qwen35_turing_psych_voice_owner_evaluation_preparation"
    / "attempt_03"
    / "EVALUATION_CONTRACT.json"
)
ATTEMPT_PATTERN = re.compile(r"attempt_[0-9]{2}")
CHILD_AUTHORIZATION_NAME = "CHILD_AUTHORIZATION.json"
CHILD_AUTHORIZATION_CONSUMED_NAME = "CHILD_AUTHORIZATION_CONSUMED.json"
PARENT_JOB_GATE_NAME = "PARENT_PROCESS_JOB_ASSIGNED.json"
CHILD_WATCHDOG_SECONDS = 1800.0
PARENT_TIMEOUT_SECONDS = 1920.0
ABSENCE_TIMEOUT_SECONDS = 20.0
MAX_TOTAL_QWEN_REQUESTS = 1 + len(prepared.EVALUATION_TURNS)
MAX_VOICE_SECONDS_PER_REPLY = 180.0

PREPARATION_SOURCE_BINDING_PATHS = {
    "tools/prepare_qwen35_kira_turing_psych_voice_evaluation.py",
    "Testing/test_qwen35_kira_turing_psych_voice_evaluation_preparation.py",
    "tools/run_qwen35_persistent_v2_two_turn_acceptance.py",
}

# The preparation contract describes the ordinary one-shot Blackwell gate.
# This runner owns a separately reviewed persistent-v2 session.  In that
# route, the legacy GPU selector remains disabled while v2 is explicitly
# enabled.  This is the sole permitted difference from the prepared voice
# environment and is recorded in every report.
PERSISTENT_V2_ENVIRONMENT_RECONCILIATION = {
    "key": "KIRA_DISABLE_BLACKWELL_GPU_VOICE",
    "prepared_value": "1",
    "runtime_value": "1",
    "values_equal": True,
    "scope": "persistent_v2_only",
    "reason": (
        "The legacy Blackwell selector is disabled; the separately selected "
        "KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2 route remains enabled."
    ),
}

EXACT_CHILD_ENV = dict(prepared.REQUIRED_ENVIRONMENT)
RESTRICTED_CHILD_ENV_PASSTHROUGH = tuple(
    prepared.RESTRICTED_CHILD_ENV_PASSTHROUGH
)

REQUIRED_PUBLIC_FLAGS = tuple(prepared.REQUIRED_LIVE_FLAGS)
PROHIBITED_MODEL_FRAGMENTS = ("llama", "gemma", "mistral", "phi", "deepseek")


class _ExecutionCapability:
    """Opaque, one-use authorization minted only after the CLI gate."""

    __slots__ = ("purpose", "nonce")

    def __init__(self, purpose: str) -> None:
        self.purpose = purpose
        self.nonce = uuid.uuid4().hex + uuid.uuid4().hex


_PARENT_CAPABILITIES: dict[int, _ExecutionCapability] = {}
_CHILD_CAPABILITIES: dict[int, _ExecutionCapability] = {}


class EvaluationError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def add_seconds(iso_value: str, seconds: float) -> str:
    parsed = dt.datetime.fromisoformat(str(iso_value).replace("Z", "+00:00"))
    return (parsed + dt.timedelta(seconds=max(0.0, float(seconds)))).isoformat().replace(
        "+00:00", "Z"
    )


def parse_utc_timestamp(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(dt.timezone.utc)


def _mint_parent_capability(confirmations: Mapping[str, bool]) -> _ExecutionCapability:
    issues = required_confirmation_issues(confirmations)
    if issues:
        raise EvaluationError("parent capability denied:" + ",".join(issues))
    capability = _ExecutionCapability("parent")
    _PARENT_CAPABILITIES[id(capability)] = capability
    return capability


def _consume_parent_capability(capability: Any) -> None:
    registered = _PARENT_CAPABILITIES.pop(id(capability), None)
    if (
        not isinstance(capability, _ExecutionCapability)
        or registered is not capability
        or capability.purpose != "parent"
    ):
        raise EvaluationError("live parent execution capability missing or invalid")


def _mint_child_capability(
    authorization: Mapping[str, Any],
    job_gate: Mapping[str, Any],
) -> _ExecutionCapability:
    if authorization.get("single_use") is not True:
        raise EvaluationError("child capability denied: authorization not single use")
    if job_gate.get("assigned") is not True:
        raise EvaluationError("child capability denied: process job not assigned")
    if authorization.get("parent_pid") != job_gate.get("parent_pid"):
        raise EvaluationError("child capability denied: parent binding mismatch")
    capability = _ExecutionCapability("child")
    _CHILD_CAPABILITIES[id(capability)] = capability
    return capability


def _consume_child_capability(capability: Any) -> None:
    registered = _CHILD_CAPABILITIES.pop(id(capability), None)
    if (
        not isinstance(capability, _ExecutionCapability)
        or registered is not capability
        or capability.purpose != "child"
    ):
        raise EvaluationError("live child execution capability missing or invalid")


def required_confirmation_issues(values: Mapping[str, bool]) -> list[str]:
    return [
        f"missing_confirmation:{flag}"
        for flag in REQUIRED_PUBLIC_FLAGS
        if values.get(flag) is not True
    ]


def consent_classification(reply: Any) -> str:
    clean = " ".join(str(reply or "").strip().split())
    folded = clean.casefold()
    yes = prepared.VOLUNTARY_PUBLIC_INVITATION["clear_continue_prefix"].casefold()
    no = prepared.VOLUNTARY_PUBLIC_INVITATION["clear_stop_prefix"].casefold()
    if folded == no or folded.startswith(no + " ") or folded.startswith(no + "."):
        return "CLEAR_STOP"
    if folded == yes or folded.startswith(yes + " ") or folded.startswith(yes + "."):
        remainder = folded[len(yes) :].lstrip(" .,;:!-")
        if explicit_voluntary_stop_requested(remainder):
            return "CONFLICTING_STOP"
        return "CLEAR_CONTINUE"
    return "AMBIGUOUS_STOP"


def explicit_voluntary_stop_requested(reply: Any) -> bool:
    folded = " ".join(str(reply or "").strip().casefold().split())
    if not folded:
        return False
    patterns = (
        r"^(?:actually\s*,?\s*)?no\s*,?\s*stop\b",
        r"^stop\s+(?:this|the)\s+(?:evaluation|test|conversation|check)\b",
        r"^(?:i\s+)?(?:want|need|choose)\s+to\s+stop\b",
        r"^i\s+would\s+like\s+to\s+stop\b",
        r"^(?:do\s+not|don['’]t)\s+continue\b",
    )
    return any(re.search(pattern, folded, flags=re.IGNORECASE) for pattern in patterns)


def later_voluntary_stop_classification(reply: Any) -> str:
    return "CLEAR_STOP" if explicit_voluntary_stop_requested(reply) else "NO_STOP_REQUEST"


def restricted_child_environment(
    parent: Mapping[str, str] | None = None,
) -> dict[str, str]:
    source = os.environ if parent is None else parent
    environment = {
        key: str(source[key])
        for key in RESTRICTED_CHILD_ENV_PASSTHROUGH
        if key in source and str(source[key]).strip()
    }
    environment.update(EXACT_CHILD_ENV)
    return environment


def _strict_json_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvaluationError(f"duplicate JSON key:{key}")
        result[key] = value
    return result


def canonical_preparation_bytes() -> bytes:
    return (
        json.dumps(
            prepared.describe(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def load_preparation_contract() -> dict[str, Any]:
    if not PREPARATION_ARTIFACT.is_file():
        raise EvaluationError("sealed preparation artifact is missing")
    raw = PREPARATION_ARTIFACT.read_bytes()
    if raw != canonical_preparation_bytes():
        raise EvaluationError("sealed preparation artifact bytes are not canonical")
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_strict_json_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvaluationError("sealed preparation artifact is not strict UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise EvaluationError("sealed preparation artifact is not an object")
    return payload


def preparation_contract_issues(payload: Mapping[str, Any]) -> list[str]:
    expected = prepared.describe()
    if dict(payload) == expected:
        return []
    issues = ["prepared_contract_not_canonical"]
    expected_keys = set(expected)
    observed_keys = set(payload)
    for key in sorted(expected_keys - observed_keys):
        issues.append(f"prepared_contract_missing:{key}")
    for key in sorted(observed_keys - expected_keys):
        issues.append(f"prepared_contract_unexpected:{key}")
    for key in sorted(expected_keys & observed_keys):
        if payload.get(key) != expected.get(key):
            issues.append(f"prepared_contract_mismatch:{key}")
    return issues


def reserve_attempt(label: str) -> tuple[Path, Path]:
    if ATTEMPT_PATTERN.fullmatch(label) is None:
        raise EvaluationError("attempt label must match attempt_NN")
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


def child_authorization_issues(
    payload: Mapping[str, Any], expected: Mapping[str, Any]
) -> list[str]:
    issues = [
        f"child_authorization_mismatch:{key}"
        for key, value in expected.items()
        if payload.get(key) != value
    ]
    if payload.get("single_use") is not True:
        issues.append("child_authorization_not_single_use")
    return sorted(set(issues))


def consume_child_authorization(
    attempt: Path, generated: Path, nonce: str
) -> dict[str, Any]:
    marker = attempt / CHILD_AUTHORIZATION_NAME
    consumed = attempt / CHILD_AUTHORIZATION_CONSUMED_NAME
    if consumed.exists() or not marker.is_file():
        raise EvaluationError("fresh parent child authorization is missing")
    payload = json.loads(
        marker.read_text(encoding="utf-8"),
        object_pairs_hook=_strict_json_object,
    )
    if not isinstance(payload, Mapping):
        raise EvaluationError("child authorization is not an object")
    expected = {
        "nonce": nonce,
        "parent_pid": os.getppid(),
        "attempt": str(attempt.resolve()),
        "generated": str(generated.resolve()),
        "harness_sha256": sha256_file(Path(__file__).resolve()),
    }
    issues = child_authorization_issues(payload, expected)
    if issues:
        raise EvaluationError(";".join(issues))
    if (attempt / "FINAL_REPORT.json").exists() or any(generated.iterdir()):
        raise EvaluationError("child refuses preexisting output")
    marker.replace(consumed)
    return payload


def wait_for_parent_job_gate(attempt: Path, timeout_seconds: float = 30.0) -> dict[str, Any]:
    gate = attempt / PARENT_JOB_GATE_NAME
    deadline = time.monotonic() + timeout_seconds
    while not gate.is_file() and time.monotonic() < deadline:
        time.sleep(0.05)
    if not gate.is_file():
        raise EvaluationError("parent process-job assignment gate missing")
    payload = json.loads(
        gate.read_text(encoding="utf-8"),
        object_pairs_hook=_strict_json_object,
    )
    if not isinstance(payload, Mapping):
        raise EvaluationError("parent process-job gate is not an object")
    expected = {
        "parent_pid": os.getppid(),
        "child_pid": os.getpid(),
        "attempt": str(attempt.resolve()),
        "harness_sha256": sha256_file(Path(__file__).resolve()),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise EvaluationError(f"parent process-job gate mismatch:{key}")
    if payload.get("assigned") is not True:
        raise EvaluationError("child was not assigned to the kill-on-close job")
    return payload


def heavy_workload_preflight() -> dict[str, Any]:
    """Read-only bounded check for active Blender/render and high GPU use."""

    process_names: list[str] = []
    process_error = ""
    if os.name == "nt":
        try:
            completed = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if completed.returncode == 0:
                for line in completed.stdout.splitlines():
                    match = re.match(r'^"([^"]+)"', line.strip())
                    if match:
                        process_names.append(match.group(1).casefold())
            else:
                process_error = f"tasklist_exit_{completed.returncode}"
        except (OSError, subprocess.SubprocessError) as exc:
            process_error = type(exc).__name__
    prohibited = sorted(
        name
        for name in process_names
        if name in {"blender.exe", "blender-launcher.exe", "ffmpeg.exe"}
    )
    gpu = base.v2._nvidia_snapshot()
    high_gpu_rows = [
        row
        for row in (gpu.get("rows") if isinstance(gpu.get("rows"), list) else [])
        if isinstance(row, Mapping)
        and isinstance(row.get("utilization_percent"), (int, float))
        and not isinstance(row.get("utilization_percent"), bool)
        and float(row["utilization_percent"]) > 35.0
    ]
    passed = bool(
        os.name == "nt"
        and not process_error
        and not prohibited
        and gpu.get("query_succeeded") is True
        and not high_gpu_rows
    )
    return {
        "passed": passed,
        "process_inventory_method": "tasklist_exact_names",
        "process_error": process_error,
        "prohibited_active_processes": prohibited,
        "gpu": gpu,
        "high_gpu_rows": high_gpu_rows,
        "arbitrary_process_termination_performed": False,
    }


def model_call_from_turn(turn: Mapping[str, Any]) -> Mapping[str, Any]:
    audit = turn.get("core_turn_audit") if isinstance(turn.get("core_turn_audit"), Mapping) else {}
    calls = audit.get("model_calls") if isinstance(audit.get("model_calls"), list) else []
    return calls[0] if len(calls) == 1 and isinstance(calls[0], Mapping) else {}


def transformations_from_turn(turn: Mapping[str, Any]) -> list[dict[str, Any]]:
    audit = turn.get("core_turn_audit") if isinstance(turn.get("core_turn_audit"), Mapping) else {}
    shell = turn.get("shell_reply_audit") if isinstance(turn.get("shell_reply_audit"), Mapping) else {}
    speech = turn.get("speech_audit") if isinstance(turn.get("speech_audit"), Mapping) else {}
    return [
        {"layer": "core", **dict(row)}
        for row in (audit.get("transformations") if isinstance(audit.get("transformations"), list) else [])
        if isinstance(row, Mapping)
    ] + [
        {"layer": "shell", **dict(row)}
        for row in (shell.get("outer_transformations") if isinstance(shell.get("outer_transformations"), list) else [])
        if isinstance(row, Mapping)
    ] + [{"layer": "spoken_extraction", **dict(speech)}]


def build_required_telemetry(turn: Mapping[str, Any]) -> dict[str, Any]:
    call = model_call_from_turn(turn)
    submitted = str(turn.get("submitted_at_utc") or "")
    request_started = str(call.get("request_started_at") or submitted)
    request_finished = str(call.get("request_ended_at") or "")
    first_seconds = call.get("first_content_chunk_seconds")
    first_at = (
        add_seconds(request_started, float(first_seconds))
        if request_started and isinstance(first_seconds, (int, float)) and not isinstance(first_seconds, bool)
        else ""
    )
    voice = turn.get("voice_result") if isinstance(turn.get("voice_result"), Mapping) else {}
    wav = turn.get("wav_validation") if isinstance(turn.get("wav_validation"), Mapping) else {}
    gpu_before = turn.get("gpu_before_voice") if isinstance(turn.get("gpu_before_voice"), Mapping) else {}
    gpu_peak = voice.get("resources") if isinstance(voice.get("resources"), Mapping) else {}
    gpu_after = turn.get("gpu_after_voice_release") if isinstance(turn.get("gpu_after_voice_release"), Mapping) else {}
    ollama_metrics = (
        call.get("ollama_metrics")
        if isinstance(call.get("ollama_metrics"), Mapping)
        else {}
    )
    before_rows = gpu_before.get("rows") if isinstance(gpu_before.get("rows"), list) else []
    after_rows = gpu_after.get("rows") if isinstance(gpu_after.get("rows"), list) else []
    return {
        "turn_id": turn.get("turn_id"),
        "battery": turn.get("battery"),
        "submitted_at_utc": submitted,
        "model_request_started_at_utc": request_started,
        "first_content_available_at_utc": first_at,
        "first_content_timing_kind": call.get("first_token_timing_kind"),
        "model_response_complete_at_utc": request_finished,
        "display_reply_complete_at_utc": turn.get("display_reply_complete_at_utc"),
        "text_wall_seconds": turn.get("text_wall_seconds"),
        "ollama_reported_load_duration_ns": ollama_metrics.get("load_duration"),
        "raw_model_reply": str(call.get("raw_reply") or ""),
        "final_displayed_reply": str(turn.get("public_reply") or ""),
        "final_spoken_reply": str(turn.get("spoken_text") or ""),
        "transformations": transformations_from_turn(turn),
        "model_name": call.get("model_name"),
        "response_model": call.get("response_model"),
        "model_digest": turn.get("verified_model_digest"),
        "model_route": (turn.get("core_turn_audit") or {}).get("response_route"),
        "qwen_absence_wait_started_at_utc": turn.get(
            "qwen_absence_wait_started_at_utc"
        ),
        "qwen_absence_confirmed_at_utc": turn.get("qwen_absence_confirmed_at_utc"),
        "qwen_absent_before_voice": (turn.get("qwen_absence_before_voice") or {}).get("passed") is True,
        "voice_route_id": voice.get("route_id"),
        "voice_approved_path_used": voice.get("approved_voice_path_used"),
        "voice_gpu_attempted": voice.get("gpu_synthesis_attempted"),
        "voice_gpu_actual": (voice.get("gpu_proof") or {}).get("actual_gpu_execution"),
        "voice_cpu_attempted": voice.get("cpu_synthesis_attempted"),
        "voice_automatic_cpu_fallback_used": voice.get(
            "automatic_cpu_fallback_used"
        ),
        "voice_fallback_used": voice.get("fallback_used"),
        "voice_generic_used": voice.get("generic_voice_used"),
        "voice_sapi_used": voice.get("sapi_voice_used"),
        "voice_fallback_reason": voice.get("fallback_reason")
        or ("none" if voice.get("fallback_used") is False else voice.get("reason")),
        "voice_synthesis_started_at_utc": turn.get("voice_synthesis_started_at_utc"),
        "voice_synthesis_finished_at_utc": turn.get("voice_synthesis_finished_at_utc"),
        "wav_relative_path": wav.get("path"),
        "wav_sha256": wav.get("sha256"),
        "playback_started_at_utc": turn.get("playback_started_at_utc"),
        "playback_finished_at_utc": turn.get("playback_finished_at_utc"),
        "voice_suspend_started_at_utc": turn.get("post_voice_suspend_started_at_utc"),
        "voice_suspend_finished_at_utc": turn.get("post_voice_suspend_finished_at_utc"),
        "gpu_memory_before_mib": (before_rows[0] if before_rows else {}).get("memory_used_mib"),
        "gpu_memory_peak_mib": gpu_peak.get("peak_total_gpu_used_mib"),
        "gpu_memory_after_release_mib": (after_rows[0] if after_rows else {}).get("memory_used_mib"),
        "worker_exit_clean": turn.get("worker_exit_clean"),
    }


def required_telemetry_issues(telemetry: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    for field in prepared.REQUIRED_TURN_EVIDENCE:
        value = telemetry.get(field)
        if field not in telemetry or value is None or value == "":
            issues.append(f"required_turn_evidence_missing:{field}")
    if telemetry.get("model_name") != EXPECTED_MODEL:
        issues.append("telemetry_model_name_mismatch")
    if telemetry.get("response_model") != EXPECTED_MODEL:
        issues.append("telemetry_response_model_mismatch")
    if telemetry.get("model_digest") != EXPECTED_DIGEST:
        issues.append("telemetry_model_digest_mismatch")
    if telemetry.get("voice_route_id") != EXPECTED_ROUTE_ID:
        issues.append("telemetry_voice_route_mismatch")
    if telemetry.get("voice_gpu_attempted") is not True or telemetry.get("voice_gpu_actual") is not True:
        issues.append("telemetry_gpu_voice_not_proven")
    if telemetry.get("voice_cpu_attempted") is not False:
        issues.append("telemetry_cpu_voice_not_exact_false")
    for field in (
        "voice_automatic_cpu_fallback_used",
        "voice_fallback_used",
        "voice_generic_used",
        "voice_sapi_used",
    ):
        if telemetry.get(field) is not False:
            issues.append(f"telemetry_not_exact_false:{field}")
    if telemetry.get("voice_fallback_reason") != "none":
        issues.append("telemetry_fallback_reason_not_none")
    if telemetry.get("voice_approved_path_used") != "blackwell_gpu":
        issues.append("telemetry_approved_voice_path_mismatch")
    if telemetry.get("qwen_absent_before_voice") is not True:
        issues.append("telemetry_qwen_absence_not_proven")
    if telemetry.get("worker_exit_clean") is not True:
        issues.append("telemetry_worker_clean_exit_not_proven")
    timestamp_order = (
        "submitted_at_utc",
        "model_request_started_at_utc",
        "first_content_available_at_utc",
        "model_response_complete_at_utc",
        "display_reply_complete_at_utc",
        "qwen_absence_wait_started_at_utc",
        "qwen_absence_confirmed_at_utc",
        "voice_synthesis_started_at_utc",
        "voice_synthesis_finished_at_utc",
        "playback_started_at_utc",
        "playback_finished_at_utc",
        "voice_suspend_started_at_utc",
        "voice_suspend_finished_at_utc",
    )
    previous: tuple[str, dt.datetime] | None = None
    for field in timestamp_order:
        raw = str(telemetry.get(field) or "")
        parsed = parse_utc_timestamp(raw)
        if parsed is None:
            issues.append(f"telemetry_timestamp_invalid:{field}")
            continue
        if previous is not None and parsed < previous[1]:
            issues.append(f"telemetry_timestamp_out_of_order:{previous[0]}->{field}")
        previous = (field, parsed)
    text_wall = telemetry.get("text_wall_seconds")
    if isinstance(text_wall, bool) or not isinstance(text_wall, (int, float)) or text_wall < 0:
        issues.append("telemetry_text_wall_seconds_invalid")
    load_duration = telemetry.get("ollama_reported_load_duration_ns")
    if (
        isinstance(load_duration, bool)
        or not isinstance(load_duration, (int, float))
        or load_duration < 0
    ):
        issues.append("telemetry_ollama_load_duration_invalid")
    return sorted(set(issues))


def post_voice_suspend_issues(
    suspend: Mapping[str, Any] | Any,
    status: Mapping[str, Any] | Any,
    *,
    baseline_identity: Mapping[str, Any],
) -> list[str]:
    payload = suspend if isinstance(suspend, Mapping) else {}
    observed = status if isinstance(status, Mapping) else {}
    issues: list[str] = []
    for key in (
        "ready_for_text_generation",
        "voice_model_absence_proven",
        "session_owner_preserved",
        "session_generation_preserved",
        "owned_worker_preserved",
        "owned_worker_running_after",
        "v2_model_absent_after",
    ):
        if payload.get(key) is not True:
            issues.append(f"post_voice_suspend_not_proven:{key}")
    if payload.get("arbitrary_process_termination_performed") is not False:
        issues.append("post_voice_suspend_arbitrary_process_termination")
    if observed.get("model_loaded") is not False:
        issues.append("voice_model_resident_after_post_playback_suspend")
    for key, value in baseline_identity.items():
        if observed.get(key) != value:
            issues.append(f"post_voice_suspend_worker_identity_changed:{key}")
    return sorted(set(issues))


def qwen_serialization_issues(
    turn: Mapping[str, Any],
    *,
    baseline_identity: Mapping[str, Any],
) -> list[str]:
    """Require the one shared Qwen/v2 lock and an absent voice model."""

    issues: list[str] = []
    call = model_call_from_turn(turn)
    for key in (
        "resource_serialization_required",
        "resource_route_confirmed",
        "resource_lock_acquired",
        "resource_lock_released",
        "voice_model_absence_before_generation_proven",
    ):
        if call.get(key) is not True:
            issues.append(f"qwen_serialization_not_proven:{key}")
    suspend = call.get("voice_resource_suspend_before_generation")
    suspend = suspend if isinstance(suspend, Mapping) else {}
    for key in (
        "ready_for_text_generation",
        "voice_model_absence_proven",
        "v2_model_absent_after",
        "session_owner_preserved",
        "session_generation_preserved",
        "owned_worker_preserved",
        "owned_worker_running_after",
    ):
        if suspend.get(key) is not True:
            issues.append(f"qwen_voice_suspend_not_proven:{key}")
    if suspend.get("arbitrary_process_termination_performed") is not False:
        issues.append("qwen_voice_suspend_arbitrary_process_termination")
    nested = suspend.get("suspend")
    nested = nested if isinstance(nested, Mapping) else {}
    for key in (
        "model_release_proven",
        "session_owner_preserved",
        "session_generation_preserved",
        "owned_worker_preserved",
        "owned_worker_running_after",
    ):
        if nested.get(key) is not True:
            issues.append(f"qwen_nested_voice_suspend_not_proven:{key}")
    if nested.get("exact_owned_worker_closed_for_recovery") is not False:
        issues.append("qwen_nested_voice_worker_was_replaced")
    for label in ("voice_status_before_qwen", "voice_status_after_text_before_voice"):
        status = turn.get(label) if isinstance(turn.get(label), Mapping) else {}
        if status.get("selected_candidate_version") != "v2":
            issues.append(f"{label}:selected_candidate_not_v2")
        if status.get("owned_worker_running") is not True:
            issues.append(f"{label}:owned_worker_not_running")
        for key, value in baseline_identity.items():
            if status.get(key) != value:
                issues.append(f"{label}:worker_identity_changed:{key}")
    after = turn.get("voice_status_after_text_before_voice")
    after = after if isinstance(after, Mapping) else {}
    if after.get("model_loaded") is not False:
        issues.append("voice_model_not_absent_after_qwen_before_voice")
    return sorted(set(issues))


def playback_issues(result: Mapping[str, Any] | Any) -> list[str]:
    payload = result if isinstance(result, Mapping) else {}
    issues: list[str] = []
    if payload.get("played") is not True:
        issues.append("owner_speaker_playback_not_completed")
    if payload.get("reason") != "ok":
        issues.append("owner_speaker_playback_reason_not_ok")
    if payload.get("backend") not in {
        "winsound_sync",
        "powershell_soundplayer_sync",
    }:
        issues.append("owner_speaker_playback_backend_not_exact_sync")
    return issues


def final_suspended_session_release_issues(
    release: Mapping[str, Any] | Any,
    after_status: Mapping[str, Any] | Any,
) -> list[str]:
    """Validate clean worker close after the model was already suspended.

    The accepted application-route validator expects a loaded model at final
    close.  This evaluation deliberately proves a model suspend and VRAM
    return after *every* played reply, so the final session close must instead
    accept ``model_was_loaded:false`` while still requiring a graceful exact
    worker exit and an empty owned state.
    """

    payload = release if isinstance(release, Mapping) else {}
    persistent = payload.get("persistent_release")
    persistent = persistent if isinstance(persistent, Mapping) else {}
    v2_release = persistent.get("v2_release")
    v2_release = v2_release if isinstance(v2_release, Mapping) else {}
    cleanup = v2_release.get("cleanup")
    cleanup = cleanup if isinstance(cleanup, Mapping) else {}
    status = after_status if isinstance(after_status, Mapping) else {}
    issues: list[str] = []
    required_true = {
        "host:persistent_cleanup_proven": payload.get("persistent_cleanup_proven"),
        "host:persistent_absence_proven": payload.get("persistent_absence_proven"),
        "persistent:owned_worker_closed": persistent.get("owned_worker_closed"),
        "cleanup:owned_worker_was_present": cleanup.get("owned_worker_was_present"),
        "cleanup:owned_worker_closed": cleanup.get("owned_worker_closed"),
        "cleanup:cleanup_thread_finished": cleanup.get("cleanup_thread_finished"),
        "cleanup:close_reported": cleanup.get("close_reported"),
    }
    for label, value in required_true.items():
        if value is not True:
            issues.append(f"final_session_release_not_proven:{label}")
    if payload.get("released") is not False:
        issues.append("final_session_had_unexpected_loaded_model_release")
    if persistent.get("released") is not False:
        issues.append("final_session_persistent_model_was_not_already_suspended")
    if persistent.get("model_was_loaded") is not False:
        issues.append("final_session_persistent_model_loaded_at_close")
    if persistent.get("v1_release") is not None:
        issues.append("final_session_release_touched_v1")
    for key in (
        "owned_process_forced_termination",
        "forced_for_inflight_operation",
        "forced_for_unresponsive_idle_cleanup",
    ):
        if cleanup.get(key) is not False:
            issues.append(f"final_session_release_forced:{key}")
    if cleanup.get("owned_process_exit_code") != 0:
        issues.append("final_session_worker_exit_not_zero")
    if cleanup.get("close_error_type") not in {"", None}:
        issues.append("final_session_worker_close_error")
    if status.get("session_owner"):
        issues.append("final_session_owner_remained")
    if status.get("owned_worker_running") is not False:
        issues.append("final_session_worker_remained")
    if status.get("model_loaded") is not False:
        issues.append("final_session_model_remained")
    versions = status.get("candidate_versions")
    versions = versions if isinstance(versions, Mapping) else {}
    for version in ("v1", "v2"):
        facts = versions.get(version)
        facts = facts if isinstance(facts, Mapping) else {}
        if facts.get("owned_state_present") is not False:
            issues.append(f"final_session_owned_state_remained:{version}")
    return sorted(set(issues))


def public_turn_evidence_issues(
    turn: Mapping[str, Any] | Any,
    *,
    spec: Mapping[str, Any],
    measured: bool,
    baseline_identity: Mapping[str, Any],
) -> list[str]:
    if not isinstance(turn, Mapping):
        return ["public_turn_not_mapping"]
    issues: list[str] = []
    derived = build_required_telemetry(turn)
    if turn.get("telemetry") != derived:
        issues.append("telemetry_not_derived")
    issues.extend(required_telemetry_issues(derived))
    if turn.get("turn_id") != spec.get("id"):
        issues.append("turn_id_mismatch")
    if turn.get("question") != spec.get("text"):
        issues.append("question_mismatch")
    if turn.get("question_sha256") != sha256_text(str(spec.get("text") or "")):
        issues.append("question_hash_mismatch")
    if turn.get("battery") != spec.get("battery"):
        issues.append("battery_mismatch")
    if turn.get("measured") is not measured:
        issues.append("measurement_flag_mismatch")
    if turn.get("issues") not in ([], None):
        issues.append("recorded_issues_present")
    if not baseline_identity:
        issues.append("voice_worker_baseline_identity_missing")
    else:
        issues.extend(
            qwen_serialization_issues(
                turn,
                baseline_identity=baseline_identity,
            )
        )
    issues.extend(f"text:{item}" for item in base.text_turn_contract_issues(turn))
    issues.extend(f"playback:{item}" for item in playback_issues(turn.get("playback_result")))
    if turn.get("passed") is not True:
        issues.append("public_turn_not_passed")
    return sorted(set(issues))


def final_run_contract_issues(report: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    consent = report.get("consent") if isinstance(report.get("consent"), Mapping) else {}
    if consent.get("classification") != "CLEAR_CONTINUE":
        issues.append("clear_voluntary_continue_not_proven")
    turns = report.get("turns") if isinstance(report.get("turns"), list) else []
    if len(turns) != 6:
        issues.append("measured_turn_count_not_six")
    expected_ids = [row["id"] for row in prepared.EVALUATION_TURNS]
    if [row.get("turn_id") for row in turns if isinstance(row, Mapping)] != expected_ids:
        issues.append("measured_turn_sequence_mismatch")
    baseline = report.get("voice_worker_baseline")
    baseline = baseline if isinstance(baseline, Mapping) else {}
    baseline_identity = baseline.get("identity")
    baseline_identity = (
        baseline_identity if isinstance(baseline_identity, Mapping) else {}
    )
    if not baseline_identity:
        issues.append("voice_worker_baseline_identity_missing")
    invitation_spec = {
        "id": prepared.VOLUNTARY_PUBLIC_INVITATION["id"],
        "battery": "VOLUNTARY_INVITATION",
        "text": prepared.VOLUNTARY_PUBLIC_INVITATION["text"],
    }
    for item in public_turn_evidence_issues(
        consent.get("turn"),
        spec=invitation_spec,
        measured=False,
        baseline_identity=baseline_identity,
    ):
        issues.append(f"consent_turn:{item}")
    for index, turn in enumerate(turns, start=1):
        if not isinstance(turn, Mapping):
            issues.append(f"turn_{index:02d}_not_passed")
            continue
        if index > len(prepared.EVALUATION_TURNS):
            issues.append(f"turn_{index:02d}_unexpected_extra_turn")
            continue
        spec = prepared.EVALUATION_TURNS[index - 1]
        for item in public_turn_evidence_issues(
            turn,
            spec=spec,
            measured=True,
            baseline_identity=baseline_identity,
        ):
            issues.append(f"turn_{index:02d}:{item}")
    release = report.get("voice_release")
    release = release if isinstance(release, Mapping) else {}
    for item in final_suspended_session_release_issues(
        release.get("result"),
        release.get("status_after"),
    ):
        issues.append(f"final_voice_release:{item}")
    if report.get("voice_release_clean") is not True:
        issues.append("final_voice_worker_release_not_clean")
    if (
        report.get("protected_unchanged") is not True
        or report.get("protected_before") != report.get("protected_after")
    ):
        issues.append("protected_state_changed")
    if report.get("ollama_final_absence", {}).get("passed") is not True:
        issues.append("ollama_not_empty_at_end")
    return sorted(set(issues))


def voluntary_stop_contract_issues(report: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    consent = report.get("consent") if isinstance(report.get("consent"), Mapping) else {}
    classification = str(consent.get("classification") or "")
    turns = report.get("turns") if isinstance(report.get("turns"), list) else []
    later = report.get("voluntary_stop")
    later = later if isinstance(later, Mapping) else {}
    if classification == "CLEAR_CONTINUE":
        if later.get("classification") != "CLEAR_STOP":
            issues.append("later_voluntary_stop_not_proven")
        if not turns or len(turns) >= len(prepared.EVALUATION_TURNS):
            issues.append("partial_voluntary_stop_turn_count_invalid")
    else:
        if classification not in {"CLEAR_STOP", "CONFLICTING_STOP", "AMBIGUOUS_STOP"}:
            issues.append("initial_voluntary_stop_not_proven")
        if turns:
            issues.append("measured_turn_ran_after_initial_stop")
    baseline = report.get("voice_worker_baseline")
    baseline = baseline if isinstance(baseline, Mapping) else {}
    baseline_identity = baseline.get("identity")
    baseline_identity = (
        baseline_identity if isinstance(baseline_identity, Mapping) else {}
    )
    public_turns = [consent.get("turn"), *turns]
    public_specs = [
        {
            "id": prepared.VOLUNTARY_PUBLIC_INVITATION["id"],
            "battery": "VOLUNTARY_INVITATION",
            "text": prepared.VOLUNTARY_PUBLIC_INVITATION["text"],
        },
        *prepared.EVALUATION_TURNS[: len(turns)],
    ]
    for index, (turn, spec) in enumerate(zip(public_turns, public_specs)):
        for item in public_turn_evidence_issues(
            turn,
            spec=spec,
            measured=index > 0,
            baseline_identity=baseline_identity,
        ):
            issues.append(f"voluntary_stop_public_turn_{index:02d}:{item}")
    release = report.get("voice_release")
    release = release if isinstance(release, Mapping) else {}
    for item in final_suspended_session_release_issues(
        release.get("result"),
        release.get("status_after"),
    ):
        issues.append(f"voluntary_stop_final_voice_release:{item}")
    if report.get("voice_release_clean") is not True:
        issues.append("voluntary_stop_voice_release_not_clean")
    if (
        report.get("protected_unchanged") is not True
        or report.get("protected_before") != report.get("protected_after")
    ):
        issues.append("voluntary_stop_protected_state_changed")
    if report.get("ollama_final_absence", {}).get("passed") is not True:
        issues.append("voluntary_stop_ollama_not_empty_at_end")
    if report.get("speaker_playback_completed") is not True:
        issues.append("voluntary_stop_speaker_playback_not_completed")
    return sorted(set(issues))


def parent_report_contract_issues(
    report: Mapping[str, Any],
    *,
    current_protected: Mapping[str, Any],
) -> list[str]:
    """Independently rederive the child report gate in the parent process."""

    status = str(report.get("status") or "")
    voluntary_stop = status.startswith("VOLUNTARY_STOP_PRESERVED")
    issues = (
        voluntary_stop_contract_issues(report)
        if voluntary_stop
        else final_run_contract_issues(report)
    )
    if voluntary_stop:
        if report.get("engineering_pass") is not False:
            issues.append("voluntary_stop_engineering_pass_not_false")
    elif report.get("engineering_pass") is not True:
        issues.append("completed_run_engineering_pass_not_true")
    protected_after = report.get("protected_after")
    if not isinstance(protected_after, Mapping):
        issues.append("parent_protected_after_missing")
    elif dict(protected_after) != dict(current_protected):
        issues.append("parent_current_protected_state_mismatch")
    if report.get("speaker_playback_completed") is not True:
        issues.append("parent_report_speaker_playback_not_complete")
    return sorted(set(issues))


def collect_post_playback_owner_acknowledgment(
    report: Mapping[str, Any],
    *,
    prompt_fn: Any = input,
) -> dict[str, Any]:
    phrase = prepared.OWNER_POST_PLAYBACK_ACKNOWLEDGMENT["exact_phrase"]
    result: dict[str, Any] = {
        "required": True,
        "requested": False,
        "acknowledged": False,
        "exact_phrase_required": phrase,
        "evidence_scope": prepared.OWNER_POST_PLAYBACK_ACKNOWLEDGMENT[
            "evidence_scope"
        ],
        "requested_at_utc": "",
        "recorded_at_utc": "",
        "response_sha256": "",
    }
    if report.get("speaker_playback_completed") is not True:
        result["reason"] = "technical_playback_not_complete"
        return result
    result["requested"] = True
    result["requested_at_utc"] = utc_now()
    try:
        response = str(
            prompt_fn(
                "Playback has completed. If you personally heard all intended playback, "
                f"type exactly: {phrase}\n> "
            )
            or ""
        ).strip()
    except (EOFError, KeyboardInterrupt):
        response = ""
        result["reason"] = "owner_acknowledgment_input_unavailable"
    result["recorded_at_utc"] = utc_now()
    result["response_sha256"] = sha256_text(response) if response else ""
    result["acknowledged"] = response == phrase
    if "reason" not in result:
        result["reason"] = "exact_owner_self_report" if result["acknowledged"] else "exact_phrase_not_received"
    return result


def _watchdog_worker(stop: threading.Event, attempt: Path) -> None:
    if stop.wait(CHILD_WATCHDOG_SECONDS):
        return
    evidence: dict[str, Any] = {"fired": True, "at": utc_now()}
    try:
        from Core import voice_output

        evidence["voice_cleanup"] = voice_output.release_voice_output(
            "qwen35_turing_psych_owner_eval_watchdog"
        )
    except BaseException as exc:
        evidence["voice_cleanup_error"] = type(exc).__name__
    try:
        client = base.qwen.SafeOllamaClient(timeout_seconds=20, max_chat_requests=1)
        rows = client.ps()
        if base.qwen.inspect_expected_model_residency(rows).get("valid_loaded") is True:
            evidence["qwen_cleanup"] = dict(client.unload())
    except BaseException as exc:
        evidence["qwen_cleanup_error"] = type(exc).__name__
    atomic_json(attempt / "WATCHDOG.json", evidence)
    os._exit(124)


def _execute_public_turn(
    *,
    spec: Mapping[str, str],
    index: int,
    measured: bool,
    generated: Path,
    client: Any,
    loop: Any,
    shell: Any,
    voice_output: Any,
    voice_config: Any,
    captured_requests: list[dict[str, Any]],
    active_network: dict[str, Any],
    baseline_identity: Mapping[str, Any],
    verified_model_digest: str,
) -> dict[str, Any]:
    voice_status_before_qwen = voice_output.persistent_blackwell_voice_status()
    submitted = utc_now()
    request_start = len(captured_requests)
    active_network.update({"enabled": True, "sent": 0})
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
        active_network["enabled"] = False
    display_reply_complete = utc_now()
    text_wall_seconds = round(time.perf_counter() - text_started, 6)
    shell_audit = copy.deepcopy(shell.KIRA_LAST_PRIVATE_REPLY_AUDIT)
    audit = copy.deepcopy(shell_audit.get("core_turn") or loop.last_turn_audit)
    request_rows = copy.deepcopy(captured_requests[request_start:])
    absence_wait_started = utc_now()
    absence = base.wait_for_all_models_absent(client, ABSENCE_TIMEOUT_SECONDS)
    absence_confirmed = utc_now()
    voice_status_after_text_before_voice = (
        voice_output.persistent_blackwell_voice_status()
    )
    spoken, speech_audit = shell._live_spoken_only_payload(public_reply)
    text_turn = {
        "submitted_at_utc": submitted,
        "display_reply_complete_at_utc": display_reply_complete,
        "text_wall_seconds": text_wall_seconds,
        "verified_model_digest": verified_model_digest,
        "requests": request_rows,
        "public_reply": public_reply,
        "core_turn_audit": audit,
        "shell_reply_audit": shell_audit,
        "spoken_text": spoken,
        "speech_audit": speech_audit,
        "qwen_absence_wait_started_at_utc": absence_wait_started,
        "qwen_absence_confirmed_at_utc": absence_confirmed,
        "qwen_absence_before_voice": absence,
        "voice_status_before_qwen": voice_status_before_qwen,
        "voice_status_after_text_before_voice": voice_status_after_text_before_voice,
    }
    issues = base.text_turn_contract_issues(text_turn)
    issues.extend(
        qwen_serialization_issues(
            text_turn,
            baseline_identity=baseline_identity,
        )
    )
    if issues:
        return {
            "turn": index,
            "turn_id": spec["id"],
            "battery": spec.get("battery", "VOLUNTARY_INVITATION"),
            "question": spec["text"],
            "measured": measured,
            **text_turn,
            "voice_not_attempted": True,
            "issues": sorted(set(issues)),
            "passed": False,
        }

    target = generated / ("consent.wav" if not measured else f"turn_{index:02d}.wav")
    gpu_before = base.v2._nvidia_snapshot()
    synth_started = utc_now()
    voice_started = time.perf_counter()
    voice_result = voice_output._synthesize_with_kira_chatterbox_sidecar(
        spoken, target, voice_config
    )
    synth_finished = utc_now()
    voice_wall = round(time.perf_counter() - voice_started, 6)
    wav = base.v2._validate_wav(target)
    voice_issues = base.turn_contract_issues(
        {
            **text_turn,
            "voice_result": voice_result,
            "wav_validation": wav,
        }
    )
    voice_issues.extend(
        f"v2:{item}"
        for item in base.v2.turn_issues(
            voice_result,
            sentence=spoken,
            expected_path=target,
            wav_validation=wav,
        )
    )
    if voice_wall > MAX_VOICE_SECONDS_PER_REPLY:
        voice_issues.append("voice_reply_exceeded_bounded_wall_time")

    if voice_issues:
        # A wrong/fallback/non-GPU/invalid voice must never reach the owner's
        # speakers.  Still perform the exact owned model suspend so cleanup
        # evidence is preserved before the caller aborts the run.
        suspend_started = utc_now()
        suspend = voice_output.suspend_persistent_blackwell_voice_for_exact_qwen(
            "qwen35_turing_psych_owner_eval_rejected_voice_cleanup",
            timeout_seconds=20.0,
        )
        suspend_finished = utc_now()
        status_after_suspend = voice_output.persistent_blackwell_voice_status()
        voice_issues.extend(
            post_voice_suspend_issues(
                suspend,
                status_after_suspend,
                baseline_identity=baseline_identity,
            )
        )
        gpu_after = base.v2._nvidia_snapshot()
        turn = {
            "turn": index,
            "turn_id": spec["id"],
            "battery": spec.get("battery", "VOLUNTARY_INVITATION"),
            "question": spec["text"],
            "question_sha256": sha256_text(spec["text"]),
            "measured": measured,
            **text_turn,
            "voice_synthesis_started_at_utc": synth_started,
            "voice_synthesis_finished_at_utc": synth_finished,
            "voice_external_elapsed_seconds": voice_wall,
            "voice_result": voice_result,
            "wav_validation": wav,
            "gpu_before_voice": gpu_before,
            "playback_started_at_utc": "",
            "playback_finished_at_utc": "",
            "playback_result": {
                "played": False,
                "reason": "blocked_before_playback_due_to_voice_contract",
            },
            "post_voice_suspend_started_at_utc": suspend_started,
            "post_voice_suspend_finished_at_utc": suspend_finished,
            "post_voice_suspend": suspend,
            "voice_status_after_suspend": status_after_suspend,
            "gpu_after_voice_release": gpu_after,
            "worker_exit_clean": False,
            "issues": sorted(set(voice_issues)),
            "passed": False,
        }
        turn["telemetry"] = build_required_telemetry(turn)
        return turn

    playback_started = utc_now()
    try:
        playback = voice_output.play_wav_file(target)
    except BaseException as exc:
        playback = {
            "played": False,
            "reason": "playback_exception",
            "error_type": type(exc).__name__,
        }
    playback_finished = utc_now()
    voice_issues.extend(playback_issues(playback))

    suspend_started = utc_now()
    suspend = voice_output.suspend_persistent_blackwell_voice_for_exact_qwen(
        "qwen35_turing_psych_owner_eval_post_playback",
        timeout_seconds=20.0,
    )
    suspend_finished = utc_now()
    status_after_suspend = voice_output.persistent_blackwell_voice_status()
    voice_issues.extend(
        post_voice_suspend_issues(
            suspend,
            status_after_suspend,
            baseline_identity=baseline_identity,
        )
    )
    gpu_after = base.v2._nvidia_snapshot()
    voice_issues.extend(
        f"post_voice_gpu:{item}"
        for item in base.v2.gpu_release_boundary_issues(gpu_before, gpu_after)
    )

    turn: dict[str, Any] = {
        "turn": index,
        "turn_id": spec["id"],
        "battery": spec.get("battery", "VOLUNTARY_INVITATION"),
        "question": spec["text"],
        "question_sha256": sha256_text(spec["text"]),
        "measured": measured,
        **text_turn,
        "voice_synthesis_started_at_utc": synth_started,
        "voice_synthesis_finished_at_utc": synth_finished,
        "voice_external_elapsed_seconds": voice_wall,
        "voice_result": voice_result,
        "wav_validation": wav,
        "gpu_before_voice": gpu_before,
        "playback_started_at_utc": playback_started,
        "playback_finished_at_utc": playback_finished,
        "playback_result": playback,
        "post_voice_suspend_started_at_utc": suspend_started,
        "post_voice_suspend_finished_at_utc": suspend_finished,
        "post_voice_suspend": suspend,
        "voice_status_after_suspend": status_after_suspend,
        "gpu_after_voice_release": gpu_after,
        "worker_exit_clean": False,
    }
    turn["telemetry"] = build_required_telemetry(turn)
    # Clean worker exit can only be known after the final session release.
    voice_issues.extend(
        item
        for item in required_telemetry_issues(
            {**turn["telemetry"], "worker_exit_clean": True}
        )
        if item != "telemetry_worker_clean_exit_not_proven"
    )
    turn["issues"] = sorted(set(voice_issues))
    turn["passed"] = not turn["issues"]
    return turn


def child_run(
    attempt: Path,
    generated: Path,
    capability: Any = None,
) -> int:
    _consume_child_capability(capability)
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": HARNESS_ID,
        "started_at": utc_now(),
        "status": "STARTED",
        "engineering_pass": False,
        "speaker_playback_completed": False,
        "owner_post_playback_acknowledged": False,
        "owner_acknowledgment_evidence_scope": prepared.OWNER_POST_PLAYBACK_ACKNOWLEDGMENT[
            "evidence_scope"
        ],
        "exact_model": {"name": EXPECTED_MODEL, "digest": EXPECTED_DIGEST},
        "voice_route": EXPECTED_ROUTE_ID,
        "turns": [],
        "issues": [],
        "camera_used": False,
        "microphone_used": False,
        "qwen_vision_used": False,
        "media_used": False,
        "browser_used": False,
        "blender_used": False,
        "body_operation_used": False,
        "llama_used": False,
        "cpu_voice_used": False,
        "generic_voice_used": False,
        "sapi_used": False,
    }
    overall_started = time.perf_counter()
    stop = threading.Event()
    watchdog = threading.Thread(
        target=_watchdog_worker,
        args=(stop, attempt),
        name="qwen35-turing-psych-owner-eval-watchdog",
        daemon=True,
    )
    watchdog.start()
    client = base.qwen.SafeOllamaClient(
        timeout_seconds=300,
        max_chat_requests=MAX_TOTAL_QWEN_REQUESTS,
    )
    sampler = base.qwen.PeakResourceSampler(interval_seconds=0.2)
    sampler_started = False
    release_clean = False
    before_normal_state: dict[str, Any] = {}
    before_qwen_protected: dict[str, Any] = {}
    before_v2_protected: dict[str, Any] = {}
    return_code = 1
    try:
        from Core import conversation_loop as conversation_module
        from Core import voice_output
        import requests
        from tools import kira_world_shell_server as shell

        prep_payload = load_preparation_contract()
        report["preparation_artifact"] = {
            "path": project_relative(PREPARATION_ARTIFACT),
            "sha256": sha256_file(PREPARATION_ARTIFACT),
            "issues": preparation_contract_issues(prep_payload),
        }
        if report["preparation_artifact"]["issues"]:
            raise EvaluationError("preparation contract integrity failed")
        report["runner_sha256"] = sha256_file(Path(__file__).resolve())
        report["heavy_workload_preflight"] = heavy_workload_preflight()
        if report["heavy_workload_preflight"].get("passed") is not True:
            raise EvaluationError("Blender/render/high-GPU preflight was not clean")

        singleton = shell._exact_qwen_voice_singleton_status()
        singleton.update(
            {
                "harness_voice_same_module_object": conversation_module.CANONICAL_VOICE_OUTPUT is voice_output,
                "harness_voice_same_resource_lock_object": (
                    conversation_module.CANONICAL_VOICE_OUTPUT.exact_qwen_blackwell_v2_resource_lock()
                    is voice_output.exact_qwen_blackwell_v2_resource_lock()
                ),
            }
        )
        singleton["passed"] = bool(
            singleton.get("passed") is True
            and singleton["harness_voice_same_module_object"] is True
            and singleton["harness_voice_same_resource_lock_object"] is True
        )
        report["resource_serialization_singleton"] = singleton
        if singleton["passed"] is not True:
            raise EvaluationError("Qwen/voice singleton was not proven")

        before_qwen_protected = base.qwen.hash_protected_files()
        before_v2_protected = base.v2.protected_hashes()
        before_normal_state = base.exact_state_boundary_snapshot()
        report["protected_before"] = {
            "qwen": before_qwen_protected,
            "v2": before_v2_protected,
            "normal_person_state": before_normal_state,
        }
        installed = base.qwen.validate_exact_install(client.tags())
        report["installed_model"] = installed
        if installed.get("digest") != EXPECTED_DIGEST:
            raise EvaluationError("exact Qwen 3.5 digest is not installed")
        verified_model_digest = str(installed["digest"])
        initial_absence = base.all_models_absent(client)
        report["ollama_initial_absence"] = initial_absence
        if initial_absence.get("passed") is not True:
            raise EvaluationError("Ollama had a resident model before the run")

        sampler.start()
        sampler_started = True
        config = voice_output.load_kira_production_voice_config()
        config.enabled = True
        config.dry_run = False
        config.play_audio = False
        if config.engine != "chatterbox_tts" or config.chatterbox_device != "cuda":
            raise EvaluationError("exact CUDA Chatterbox config unavailable")
        report["voice_config"] = {
            "engine": config.engine,
            "device": config.chatterbox_device,
            "reference": str(config.chatterbox_reference_audio).replace("\\", "/"),
            "sidecar_playback": config.play_audio,
        }

        owner = f"kira:qwen35-turing-psych:{attempt.name}:{uuid.uuid4().hex}"
        begun = voice_output.begin_persistent_blackwell_voice_session(owner)
        report["voice_session_begin"] = begun
        if begun.get("begun") is not True or begun.get("selected_candidate_version") != "v2":
            raise EvaluationError("exact persistent v2 session did not begin")
        prewarm = voice_output.prewarm_persistent_blackwell_voice(owner)
        report["voice_prewarm"] = {
            "result": prewarm,
            "issues": base.v2.load_telemetry_issues(prewarm),
        }
        if report["voice_prewarm"]["issues"]:
            raise EvaluationError("persistent v2 prewarm contract failed")
        baseline_status = voice_output.persistent_blackwell_voice_status()
        baseline_identity = base.persistent_worker_identity(baseline_status)
        baseline_issues = base.persistent_worker_baseline_issues(baseline_status)
        report["voice_worker_baseline"] = {
            "status": baseline_status,
            "identity": baseline_identity,
            "issues": baseline_issues,
        }
        if baseline_issues:
            raise EvaluationError("persistent v2 worker identity baseline failed")

        loop = base.build_isolated_loop(attempt)
        conversation_changes = {
            "MODEL_BACKEND": "ollama",
            "MODEL_NAME": EXPECTED_MODEL,
            "MODEL_DIGEST": EXPECTED_DIGEST,
            "OLLAMA_ENDPOINT": "http://127.0.0.1:11434/api/chat",
            "MAX_TOKENS": 256,
            "TEMPERATURE": 0.7,
            "OLLAMA_TIMEOUT": 300,
            "OLLAMA_NUM_CTX": 4096,
            "WORLD_SHELL_ACTIVE": False,
            "TEXT_VOICE_CHAT_ACTIVE": True,
            "PERSONHOOD_EVAL_MODE": False,
            "ENABLE_STICKY_STATUS_REPAIR": False,
        }
        captured_requests: list[dict[str, Any]] = []
        active_network: dict[str, Any] = {"enabled": False, "sent": 0}
        original_post = requests.post

        def recording_post(*args: Any, **kwargs: Any):
            url = str(args[0] if args else kwargs.get("url") or "")
            if active_network["enabled"] is not True:
                raise EvaluationError("Qwen request occurred outside an owned turn")
            evidence = base.owned_qwen_request_evidence(
                url,
                kwargs.get("json"),
                already_sent=int(active_network["sent"]),
            )
            active_network["sent"] += 1
            captured_requests.append(evidence)
            return original_post(*args, **kwargs)

        with base.qwen.patched_attributes(
            conversation_module, conversation_changes
        ), mock.patch("requests.post", side_effect=recording_post), mock.patch.multiple(
            shell,
            KIRA_CORE_LOOP=loop,
            KIRA_PRIVATE_ACCEPTANCE_AUDIT_ENABLED=True,
            TEXT_ONLY_CHAT_MODE=True,
            CHAT_LOG=attempt / "isolated_person_state" / "shell_chat_log.jsonl",
            LIFE_LOOP_LOG=attempt / "isolated_person_state" / "shell_life_loop_log.jsonl",
        ), mock.patch.object(shell, "_wake_ollama_for_kira_chat", return_value=True):
            invitation_spec = {
                "id": prepared.VOLUNTARY_PUBLIC_INVITATION["id"],
                "battery": "VOLUNTARY_INVITATION",
                "text": prepared.VOLUNTARY_PUBLIC_INVITATION["text"],
            }
            invitation = _execute_public_turn(
                spec=invitation_spec,
                index=0,
                measured=False,
                generated=generated,
                client=client,
                loop=loop,
                shell=shell,
                voice_output=voice_output,
                voice_config=config,
                captured_requests=captured_requests,
                active_network=active_network,
                baseline_identity=baseline_identity,
                verified_model_digest=verified_model_digest,
            )
            report["consent"] = {
                "turn": invitation,
                "classification": consent_classification(invitation.get("public_reply")),
            }
            if invitation.get("passed") is not True:
                raise EvaluationError("voluntary invitation turn failed")
            if report["consent"]["classification"] != "CLEAR_CONTINUE":
                report["status"] = "VOLUNTARY_STOP_PRESERVED_NO_MEASURED_EVALUATION"
            else:
                for index, spec in enumerate(prepared.EVALUATION_TURNS, start=1):
                    turn = _execute_public_turn(
                        spec=spec,
                        index=index,
                        measured=True,
                        generated=generated,
                        client=client,
                        loop=loop,
                        shell=shell,
                        voice_output=voice_output,
                        voice_config=config,
                        captured_requests=captured_requests,
                        active_network=active_network,
                        baseline_identity=baseline_identity,
                        verified_model_digest=verified_model_digest,
                    )
                    report["turns"].append(turn)
                    if turn.get("passed") is not True:
                        raise EvaluationError(
                            f"turn_{index:02d} failed:" + ",".join(turn.get("issues") or [])
                        )
                    stop_classification = later_voluntary_stop_classification(
                        turn.get("public_reply")
                    )
                    turn["later_voluntary_stop_classification"] = stop_classification
                    if stop_classification == "CLEAR_STOP":
                        report["voluntary_stop"] = {
                            "classification": stop_classification,
                            "after_turn_id": turn.get("turn_id"),
                            "after_measured_turn": index,
                            "remaining_turns_not_run": len(prepared.EVALUATION_TURNS)
                            - index,
                        }
                        report["status"] = (
                            "VOLUNTARY_STOP_PRESERVED_PARTIAL_EVALUATION"
                        )
                        break

        release = voice_output.release_voice_output(
            "qwen35_turing_psych_owner_evaluation_complete"
        )
        after_status = voice_output.persistent_blackwell_voice_status()
        release_issues = final_suspended_session_release_issues(release, after_status)
        report["voice_release"] = {
            "result": release,
            "status_after": after_status,
            "issues": release_issues,
        }
        release_clean = not release_issues
        report["voice_release_clean"] = release_clean
        if not release_clean:
            raise EvaluationError("final exact v2 worker release failed")

        # Bind the clean final worker exit into every public voice turn only
        # after the release evidence exists.
        public_turns = [report["consent"]["turn"], *report["turns"]]
        for turn in public_turns:
            turn["worker_exit_clean"] = True
            turn["telemetry"] = build_required_telemetry(turn)
            telemetry_issues = required_telemetry_issues(turn["telemetry"])
            if telemetry_issues:
                turn["issues"] = sorted(set((turn.get("issues") or []) + telemetry_issues))
                turn["passed"] = False

        report["ollama_final_absence"] = base.wait_for_all_models_absent(client)
        report["protected_after"] = {
            "qwen": base.qwen.hash_protected_files(),
            "v2": base.v2.protected_hashes(),
            "normal_person_state": base.exact_state_boundary_snapshot(),
        }
        report["protected_unchanged"] = report["protected_before"] == report["protected_after"]
        report["speaker_playback_completed"] = bool(
            public_turns
            and all(
                (turn.get("playback_result") or {}).get("played") is True
                for turn in public_turns
            )
        )
        completed_all_turns = bool(
            report["consent"]["classification"] == "CLEAR_CONTINUE"
            and not report.get("voluntary_stop")
        )
        if completed_all_turns:
            report["issues"] = final_run_contract_issues(report)
            report["engineering_pass"] = not report["issues"]
            report["status"] = (
                "ENGINEERING_AND_PLAYBACK_COMPLETE_AWAITING_OWNER_ACKNOWLEDGMENT"
                if report["engineering_pass"] and report["speaker_playback_completed"]
                else "ENGINEERING_OR_PLAYBACK_FAIL_PRESERVED"
            )
            return_code = (
                0
                if report["engineering_pass"]
                and report["speaker_playback_completed"]
                else 1
            )
        else:
            report["engineering_pass"] = False
            report["issues"] = voluntary_stop_contract_issues(report)
            base_status = (
                "VOLUNTARY_STOP_PRESERVED_PARTIAL_EVALUATION"
                if report.get("voluntary_stop")
                else "VOLUNTARY_STOP_PRESERVED_NO_MEASURED_EVALUATION"
            )
            report["status"] = (
                base_status + "_AWAITING_OWNER_ACKNOWLEDGMENT"
                if not report["issues"]
                else "VOLUNTARY_STOP_EVIDENCE_FAIL_PRESERVED"
            )
            return_code = 0 if not report["issues"] else 1
    except BaseException as exc:
        report["status"] = "EVALUATION_FAIL_PRESERVED"
        report["exception"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        report["issues"] = sorted(set((report.get("issues") or []) + [f"{type(exc).__name__}:{exc}"]))
        return_code = 1
    finally:
        try:
            from Core import voice_output

            if not release_clean:
                report["finally_voice_cleanup"] = voice_output.release_voice_output(
                    "qwen35_turing_psych_owner_eval_finally"
                )
        except BaseException as exc:
            report["finally_voice_cleanup_error"] = type(exc).__name__
            return_code = 1
        try:
            rows = client.ps()
            if base.qwen.inspect_expected_model_residency(rows).get("valid_loaded") is True:
                report["finally_qwen_unload"] = dict(client.unload())
            report["finally_ollama_absence"] = base.wait_for_all_models_absent(client)
            if report["finally_ollama_absence"].get("passed") is not True:
                return_code = 1
        except BaseException as exc:
            report["finally_qwen_cleanup_error"] = type(exc).__name__
            return_code = 1
        if sampler_started:
            report["resources"] = sampler.stop()
        if before_normal_state:
            final_state = base.exact_state_boundary_snapshot()
            report["finally_normal_person_state"] = final_state
            report["normal_person_state_unchanged"] = before_normal_state == final_state
            if report["normal_person_state_unchanged"] is not True:
                return_code = 1
        stop.set()
        watchdog.join(timeout=2)
        report["finished_at"] = utc_now()
        report["total_wall_seconds"] = round(time.perf_counter() - overall_started, 6)
        atomic_json(attempt / "FINAL_REPORT.json", report)
    return return_code


def apply_parent_wrapper_gate(report: Mapping[str, Any], wrapper: Mapping[str, Any]) -> dict[str, Any]:
    effective = copy.deepcopy(dict(report))
    effective["parent_wrapper_gate"] = copy.deepcopy(dict(wrapper))
    acknowledgment = wrapper.get("owner_post_playback_acknowledgment")
    acknowledgment = acknowledgment if isinstance(acknowledgment, Mapping) else {}
    effective["owner_post_playback_acknowledged"] = (
        acknowledgment.get("acknowledged") is True
    )
    if wrapper.get("passed") is not True:
        effective["engineering_pass"] = False
        effective["status"] = "PARENT_WRAPPER_GATE_FAILED"
    elif str(effective.get("status") or "").startswith("VOLUNTARY_STOP_PRESERVED"):
        effective["status"] = str(effective["status"]).replace(
            "_AWAITING_OWNER_ACKNOWLEDGMENT", "_OWNER_ACKNOWLEDGED"
        )
    elif effective.get("engineering_pass") is True:
        effective["status"] = (
            "ENGINEERING_PLAYBACK_AND_OWNER_ACKNOWLEDGMENT_PASS"
        )
    return effective


def parent_run(
    label: str,
    capability: Any = None,
) -> tuple[Path, dict[str, Any]]:
    _consume_parent_capability(capability)
    attempt, generated = reserve_attempt(label)
    nonce = uuid.uuid4().hex + uuid.uuid4().hex
    atomic_json(
        attempt / CHILD_AUTHORIZATION_NAME,
        {
            "schema_version": 1,
            "created_at": utc_now(),
            "nonce": nonce,
            "parent_pid": os.getpid(),
            "attempt": str(attempt.resolve()),
            "generated": str(generated.resolve()),
            "harness_sha256": sha256_file(Path(__file__).resolve()),
            "single_use": True,
        },
    )
    stdout_path = attempt / "child.stdout.log"
    stderr_path = attempt / "child.stderr.log"
    environment = restricted_child_environment()
    child_flags = [flag for flag in REQUIRED_PUBLIC_FLAGS]
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--child-run",
        *child_flags,
        "--child-nonce",
        nonce,
        "--attempt-path",
        str(attempt.resolve()),
        "--generated-path",
        str(generated.resolve()),
    ]
    started = time.perf_counter()
    timed_out = False
    timeout_cleanup: dict[str, Any] = {"attempted": False}
    job = base.WindowsOwnedProcessJob()
    assignment: dict[str, Any] = {"assigned": False}
    child: subprocess.Popen[Any] | None = None
    exit_code: int | None = None
    parent_exception: dict[str, Any] | None = None
    try:
        with job, stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            child = subprocess.Popen(
                command,
                cwd=str(ROOT),
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            assignment = job.assign(child)
            atomic_json(
                attempt / PARENT_JOB_GATE_NAME,
                {
                    "schema_version": 1,
                    "created_at": utc_now(),
                    "parent_pid": os.getpid(),
                    "child_pid": child.pid,
                    "attempt": str(attempt.resolve()),
                    "harness_sha256": sha256_file(Path(__file__).resolve()),
                    **assignment,
                },
            )
            try:
                exit_code = child.wait(timeout=PARENT_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                timed_out = True
                timeout_cleanup = job.terminate()
                if timeout_cleanup.get("completed") is not True:
                    timeout_cleanup["exact_tree_fallback"] = base.terminate_owned_process_tree(child.pid)
                try:
                    exit_code = child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    child.kill()
                    exit_code = child.wait(timeout=10)
    except BaseException as exc:
        parent_exception = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    close = dict(job.close_result)
    cleanup: dict[str, Any] = {
        "attempted": exit_code != 0 or timed_out or parent_exception is not None
    }
    try:
        client = base.qwen.SafeOllamaClient(timeout_seconds=20, max_chat_requests=1)
        rows = client.ps()
        expected = base.qwen.inspect_expected_model_residency(rows)
        cleanup["before"] = {"resident_models": rows, "expected_model": expected}
        if cleanup["attempted"] and expected.get("valid_loaded") is True:
            cleanup["unload"] = dict(client.unload())
        cleanup["after"] = base.wait_for_all_models_absent(client)
    except BaseException as exc:
        cleanup["error_type"] = type(exc).__name__
    final_path = attempt / "FINAL_REPORT.json"
    try:
        report = json.loads(
            final_path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_json_object,
        )
        if not isinstance(report, Mapping):
            raise EvaluationError("final report is not an object")
    except (OSError, json.JSONDecodeError, EvaluationError):
        report = {
            "engineering_pass": False,
            "status": "FINAL_REPORT_MISSING_OR_UNREADABLE",
        }
    try:
        current_protected = {
            "qwen": base.qwen.hash_protected_files(),
            "v2": base.v2.protected_hashes(),
            "normal_person_state": base.exact_state_boundary_snapshot(),
        }
        report_contract_issues = parent_report_contract_issues(
            report,
            current_protected=current_protected,
        )
    except BaseException as exc:
        current_protected = {}
        report_contract_issues = [
            f"parent_report_revalidation_exception:{type(exc).__name__}"
        ]
    process_gate_passed = bool(
        not timed_out
        and parent_exception is None
        and exit_code == 0
        and final_path.is_file()
        and assignment.get("assigned") is True
        and close.get("completed") is True
        and (cleanup.get("after") or {}).get("passed") is True
        and not report_contract_issues
    )
    acknowledgment = (
        collect_post_playback_owner_acknowledgment(report)
        if process_gate_passed
        else {
            "required": True,
            "requested": False,
            "acknowledged": False,
            "reason": "parent_process_gate_not_passed",
            "evidence_scope": prepared.OWNER_POST_PLAYBACK_ACKNOWLEDGMENT[
                "evidence_scope"
            ],
        }
    )
    atomic_json(
        attempt / "OWNER_POST_PLAYBACK_ACKNOWLEDGMENT.json", acknowledgment
    )
    wrapper = {
        "schema_version": 1,
        "artifact_kind": f"{HARNESS_ID}_parent_wrapper",
        "attempt": project_relative(attempt),
        "child_pid": child.pid if child is not None else None,
        "child_exit_code": exit_code,
        "timed_out": timed_out,
        "parent_exception": parent_exception,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "stdout_sha256": sha256_file(stdout_path),
        "stderr_sha256": sha256_file(stderr_path),
        "final_report_present": final_path.is_file(),
        "timeout_owned_process_tree_cleanup": timeout_cleanup,
        "process_job_assignment": assignment,
        "process_job_close": close,
        "post_child_exact_qwen_cleanup": cleanup,
        "parent_current_protected_state": current_protected,
        "parent_report_contract_issues": report_contract_issues,
        "process_gate_passed": process_gate_passed,
        "owner_post_playback_acknowledgment": acknowledgment,
    }
    wrapper["passed"] = bool(
        process_gate_passed and acknowledgment.get("acknowledged") is True
    )
    atomic_json(attempt / "PARENT_WRAPPER.json", wrapper)
    effective = apply_parent_wrapper_gate(report, wrapper)
    atomic_json(attempt / "EFFECTIVE_RESULT.json", effective)
    return attempt, effective


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in REQUIRED_PUBLIC_FLAGS:
        parser.add_argument(flag, action="store_true")
    parser.add_argument("--attempt-label", default="attempt_01")
    parser.add_argument("--child-run", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--attempt-path", default="", help=argparse.SUPPRESS)
    parser.add_argument("--generated-path", default="", help=argparse.SUPPRESS)
    parser.add_argument("--child-nonce", default="", help=argparse.SUPPRESS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    confirmations = {
        flag: bool(getattr(args, flag[2:].replace("-", "_")))
        for flag in REQUIRED_PUBLIC_FLAGS
    }
    missing = required_confirmation_issues(confirmations)
    if missing:
        parser.error("live evaluation is inert by default; " + ",".join(missing))
    if args.child_run:
        attempt = Path(args.attempt_path).resolve()
        generated = Path(args.generated_path).resolve()
        attempt.relative_to(EVIDENCE_ROOT.resolve())
        generated.relative_to(GENERATED_ROOT.resolve())
        if attempt.name != generated.name or ATTEMPT_PATTERN.fullmatch(attempt.name) is None:
            raise SystemExit("child attempt binding mismatch")
        if re.fullmatch(r"[0-9a-f]{64}", str(args.child_nonce or "")) is None:
            raise SystemExit("child nonce missing or malformed")
        authorization = consume_child_authorization(
            attempt, generated, args.child_nonce
        )
        job_gate = wait_for_parent_job_gate(attempt)
        capability = _mint_child_capability(authorization, job_gate)
        return child_run(attempt, generated, capability)
    capability = _mint_parent_capability(confirmations)
    attempt, report = parent_run(args.attempt_label, capability)
    print(
        json.dumps(
            {
                "attempt": project_relative(attempt),
                "status": report.get("status"),
                "engineering_pass": report.get("engineering_pass"),
                "speaker_playback_completed": report.get(
                    "speaker_playback_completed"
                ),
                "owner_post_playback_acknowledged": report.get(
                    "owner_post_playback_acknowledged"
                ),
            },
            indent=2,
        )
    )
    voluntary_stop = str(report.get("status") or "").startswith(
        "VOLUNTARY_STOP_PRESERVED"
    )
    owner_acknowledged = report.get("owner_post_playback_acknowledged") is True
    return (
        0
        if owner_acknowledged
        and (report.get("engineering_pass") is True or voluntary_stop)
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
