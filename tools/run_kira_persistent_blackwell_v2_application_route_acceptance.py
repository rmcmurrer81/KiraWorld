"""Append-only, no-playback application-route acceptance for Blackwell v2.

This harness is intentionally *prepared but not automatically executed* by
its unit tests.  A real run exercises ``Core.voice_output`` with only the
explicit v2 persistent-candidate flag enabled.  It never asks a text model for
a reply and never invokes an audio player.  The exact approved Kira profile,
reference, inactive v2 candidate, production routing manifest, and byte-sealed
v1 rollback candidate are all hash-bound.

Normal invocation (only when the live acceptance is separately authorized)::

    py Tools/run_kira_persistent_blackwell_v2_application_route_acceptance.py \
        --attempt-label attempt_01

The parent process owns a bounded child.  The child also owns a shorter
watchdog which asks ``Core.voice_output`` to release only its exact session-
owned worker before exiting.  No process discovery or PID-wide termination is
used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import traceback
import wave
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    # Direct ``py Tools\...`` execution otherwise exposes only the Tools
    # directory on sys.path.  The bounded child must resolve the exact local
    # ``Core`` package before it can start its watchdog or write FINAL_REPORT.
    sys.path.insert(0, str(ROOT))
HARNESS_ID = "kira_persistent_blackwell_v2_application_route_acceptance_v1"
HARNESS_RELATIVE = "Tools/run_kira_persistent_blackwell_v2_application_route_acceptance.py"
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "application_route_v2"
)
GENERATED_ROOT = (
    ROOT
    / "Voice"
    / "generated"
    / "acceptance"
    / "persistent_blackwell_v2_application_route"
)
ATTEMPT_LABEL_PATTERN = re.compile(r"attempt_[0-9]{2}")

# The child watchdog runs first so it has time to request exact-owned cleanup.
# Leave enough time after the child watchdog for its bounded 20-second idle
# cleanup, exact-process terminate/kill waits, thread joins, and atomic
# evidence write to finish before the parent acts.
CHILD_WATCHDOG_SECONDS = 360.0
PARENT_CHILD_TIMEOUT_SECONDS = 480.0
PARENT_TERMINATE_WAIT_SECONDS = 10.0
PARENT_KILL_WAIT_SECONDS = 5.0

V2_FEATURE_FLAG = "KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2"
V1_FEATURE_FLAG = "KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE"
EXACT_CHILD_ENVIRONMENT = {
    V2_FEATURE_FLAG: "1",
    V1_FEATURE_FLAG: "0",
    # These disable every non-v2 synthesis route if the inactive candidate
    # fails.  They do not enter the candidate's separately restricted worker
    # environment.
    "KIRA_DISABLE_BLACKWELL_GPU_VOICE": "1",
    "KIRA_DISABLE_CHATTERBOX_PY311_SIDECAR": "1",
    "KIRA_VOICE_FORCE_SAPI": "0",
    "KIRA_CHATTERBOX_DEVICE": "cuda",
    "KIRA_VOICE_IDLE_UNLOAD_SECONDS": "0",
    "PYTHONDONTWRITEBYTECODE": "1",
}

PUBLIC_SPOKEN_SENTENCES = (
    "I don't see anything and I don't hear anything.",
    "I'm here with you, and this second sentence tests the warm Kira voice path.",
)
PUBLIC_SPOKEN_SHA256 = tuple(
    hashlib.sha256(sentence.encode("utf-8")).hexdigest()
    for sentence in PUBLIC_SPOKEN_SENTENCES
)

APPROVED_PROFILE_RELATIVE = "Voice/profiles/temp_ai/kira_voice_profile.json"
APPROVED_PROFILE_SHA256 = (
    "102d17f5420a1a16b3a920204ebde0d532c0a9bfd2979dca28048378ecddc116"
)
APPROVED_REFERENCE_RELATIVE = (
    "Voice/reference_packs/kira/kira_online_source_20260706_221447/"
    "model_input/approved_reference.wav"
)
APPROVED_REFERENCE_SHA256 = (
    "2039a2abd600a63c294d69c2b2e4d450c64c850dc6d1c9a4fbfa1700ba92069c"
)
FULL_GPU_PASS_RELATIVE = (
    "RecoverySprint/continuation_20260802/"
    "persistent_blackwell_voice_candidate_acceptance/full_gpu_v2/"
    "attempt_02/FINAL_REPORT.json"
)
FULL_GPU_PASS_SHA256 = (
    "40771bb8961a09a9e627e2c8b3a0d80da18dbb3199aea900912c56ceefc7d339"
)
V2_CONFIG_SHA256 = "805c1d2836c618970a81f5f44d31f81f67e204173bd919857452daa8dbedc8bb"
V2_WORKER_SHA256 = "b6f2dcc816537552db02d00c5a1932057f2d99b5d206a578344d4a92523b3cad"
EXPECTED_ROUTE_ID = "blackwell_gpu_persistent_candidate_v2"
EXPECTED_RUNTIME_VERSIONS = {
    "torch": "2.11.0+cu130",
    "torchaudio": "2.11.0+cu130",
    "chatterbox-tts": "0.1.7",
}
EXPECTED_RUNTIME_CUDA_CHECKS = (
    "capability",
    "cuda_available",
    "cuda_runtime",
    "device",
    "sm_120",
    "torch_runtime",
    "torchaudio_runtime",
)
EXPECTED_LOAD_RESOURCE_FIELDS = (
    "peak_process_rss_mib",
    "peak_system_ram_used_mib",
    "baseline_total_gpu_used_mib",
    "peak_total_gpu_used_mib",
    "peak_total_gpu_delta_mib",
    "host_sample_count",
    "external_gpu_sample_count",
)
EXPECTED_LOAD_PHASES = (
    "load.restricted_environment",
    "load.runtime_dependency_metadata",
    "load.approved_identity_hashes",
    "load.qwen_absence",
    "imports.torch",
    "imports.torchaudio",
    "imports.transformers_compatibility",
    "imports.numpy",
    "imports.soundfile",
    "imports.chatterbox",
    "imports.dialogue_contracts",
    "load.cuda_contract",
    "load.cuda_prepare",
    "load.model_from_pretrained",
    "load.reference_prepare_conditionals",
    "load.cuda_synchronize_after_conditioning",
)

# These exact v1 hashes are both rollback evidence and a guard against a live
# acceptance silently changing the older candidate.
PINNED_PROTECTED_HASHES = {
    "Voice/sidecars/kira_approved_voice_routing.json": (
        "a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81"
    ),
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate/candidate_config.json": (
        "8fffb5b641486963341ba2a4c10ff13f067eaf1d085c26488f9996ac4cd1af57"
    ),
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate/candidate_contract.py": (
        "e74ce6ad83b181d5f8ca786764d5e61e2cc5e053aaebf29065063151aed38cbc"
    ),
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate/candidate_client.py": (
        "b57e1a57625f8d3c55881795611b440aaf91aeb7466ee2f1231ee7bedbc3e9f1"
    ),
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate/persistent_worker.py": (
        "bbf33447e7b742a3f2c79da6f7a3527b37a069e32bb888ed3d1e833345388085"
    ),
    "Core/persistent_blackwell_voice_integration.py": (
        "bd7809c3ae2f997fad241ff7fe4cbbabeff3a5643dfe2c11d3ebffebe85203df"
    ),
}

# These implementation files may receive reviewed changes before the first
# live run, so the attempt records their exact before/after equality without
# pinning a stale authoring-time hash.
TRACKED_IMPLEMENTATION_FILES = (
    "Core/persistent_blackwell_voice_integration_v2.py",
    "Core/voice_output.py",
    HARNESS_RELATIVE,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    import datetime as _dt

    return _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _project_file(relative: str) -> Path:
    candidate = (ROOT / relative).resolve()
    candidate.relative_to(ROOT.resolve())
    return candidate


def protected_hashes() -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for relative in (*PINNED_PROTECTED_HASHES, *TRACKED_IMPLEMENTATION_FILES):
        path = _project_file(relative)
        result[relative] = sha256_file(path) if path.is_file() else None
    return result


def pinned_hash_issues(observed: dict[str, str | None]) -> list[str]:
    return [
        f"pinned_hash_mismatch:{relative}"
        for relative, expected in PINNED_PROTECTED_HASHES.items()
        if observed.get(relative) != expected
    ]


def _build_child_environment(parent: dict[str, str] | None = None) -> dict[str, str]:
    environment = dict(os.environ if parent is None else parent)
    environment.update(EXACT_CHILD_ENVIRONMENT)
    return environment


def _environment_evidence() -> dict[str, Any]:
    selected = {key: os.environ.get(key) for key in EXACT_CHILD_ENVIRONMENT}
    return {
        "values": selected,
        "exact_v2_only": selected == EXACT_CHILD_ENVIRONMENT,
        "v2_feature_enabled": selected.get(V2_FEATURE_FLAG) == "1",
        "v1_feature_disabled": selected.get(V1_FEATURE_FLAG) == "0",
        "one_shot_gpu_disabled": selected.get("KIRA_DISABLE_BLACKWELL_GPU_VOICE") == "1",
        "sealed_cpu_disabled": selected.get("KIRA_DISABLE_CHATTERBOX_PY311_SIDECAR") == "1",
        "sapi_force_disabled": selected.get("KIRA_VOICE_FORCE_SAPI") == "0",
    }


def _qwen_absent(evidence: Any) -> bool:
    return bool(
        isinstance(evidence, dict)
        and evidence.get("query_succeeded") is True
        and evidence.get("qwen_absent_proven") is True
        and evidence.get("qwen_records") == []
        and evidence.get("model_state_changed") is False
    )


def _safe_load_qwen_absent(evidence: Any) -> bool:
    return bool(
        isinstance(evidence, dict)
        and evidence.get("query_succeeded") is True
        and evidence.get("qwen_absent_proven") is True
        and evidence.get("qwen_record_count") == 0
        and evidence.get("model_state_changed") is False
    )


def _nvidia_snapshot() -> dict[str, Any]:
    command = [
        "nvidia-smi",
        "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu",
        "--format=csv,noheader,nounits",
    ]
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "query_succeeded": False,
            "error_type": type(exc).__name__,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
        }
    rows: list[dict[str, Any]] = []
    if completed.returncode == 0:
        for line in completed.stdout.splitlines():
            fields = [field.strip() for field in line.split(",")]
            if len(fields) != 6:
                continue
            try:
                rows.append(
                    {
                        "index": int(fields[0]),
                        "name": fields[1],
                        "memory_total_mib": float(fields[2]),
                        "memory_used_mib": float(fields[3]),
                        "memory_free_mib": float(fields[4]),
                        "utilization_percent": float(fields[5]),
                    }
                )
            except ValueError:
                continue
    return {
        "query_succeeded": completed.returncode == 0 and bool(rows),
        "returncode": completed.returncode,
        "rows": rows,
        "stderr_tail": str(completed.stderr or "")[-1000:],
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "scope": "boundary_snapshot_not_continuous_peak",
    }


def _validate_wav(path: Path) -> dict[str, Any]:
    try:
        display_path = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        display_path = str(path)
    result: dict[str, Any] = {
        "path": display_path,
        "exists": path.is_file(),
        "passed": False,
    }
    if not path.is_file():
        return result
    try:
        with wave.open(str(path), "rb") as reader:
            channels = int(reader.getnchannels())
            sample_width = int(reader.getsampwidth())
            sample_rate = int(reader.getframerate())
            frame_count = int(reader.getnframes())
            frames = reader.readframes(frame_count)
    except (OSError, EOFError, wave.Error) as exc:
        result["error_type"] = type(exc).__name__
        return result
    peak = 0
    energy = 0.0
    sample_count = 0
    if sample_width == 2:
        for offset in range(0, len(frames) - 1, 2):
            sample = int.from_bytes(frames[offset : offset + 2], "little", signed=True)
            absolute = abs(sample)
            peak = max(peak, absolute)
            energy += float(sample) ** 2
            sample_count += 1
    rms = (energy / sample_count) ** 0.5 if sample_count else 0.0
    duration = frame_count / sample_rate if sample_rate else 0.0
    result.update(
        {
            "channels": channels,
            "sample_width_bytes": sample_width,
            "sample_rate_hz": sample_rate,
            "frame_count": frame_count,
            "duration_seconds": round(duration, 6),
            "peak_normalized": round(peak / 32767.0, 8),
            "rms_normalized": round(rms / 32767.0, 8),
            "non_silent": peak >= 33 and rms >= 3.3,
            "sha256": sha256_file(path),
        }
    )
    result["passed"] = bool(
        channels == 1
        and sample_width == 2
        and sample_rate >= 8000
        and duration >= 0.1
        and result["non_silent"] is True
    )
    return result


def load_telemetry_issues(prewarm: Any) -> list[str]:
    payload = prewarm if isinstance(prewarm, dict) else {}
    telemetry = payload.get("load_telemetry")
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    gpu = telemetry.get("gpu_proof")
    gpu = gpu if isinstance(gpu, dict) else {}
    lifecycle = telemetry.get("lifecycle")
    lifecycle = lifecycle if isinstance(lifecycle, dict) else {}
    worker_start = telemetry.get("worker_start")
    worker_start = worker_start if isinstance(worker_start, dict) else {}
    versions = telemetry.get("runtime_versions")
    versions = versions if isinstance(versions, dict) else {}
    runtime_checks = telemetry.get("runtime_cuda_checks")
    runtime_checks = runtime_checks if isinstance(runtime_checks, dict) else {}
    identity = telemetry.get("identity")
    identity = identity if isinstance(identity, dict) else {}
    resources = telemetry.get("resources")
    resources = resources if isinstance(resources, dict) else {}
    qwen = telemetry.get("qwen_residency_before_load")
    qwen = qwen if isinstance(qwen, dict) else {}
    phases = telemetry.get("phase_timings")
    phases = phases if isinstance(phases, list) else []
    issues: list[str] = []
    if payload.get("warmed") is not True or payload.get("device") != "cuda":
        issues.append("prewarm_not_ready_on_cuda")
    if payload.get("selected_candidate_version") != "v2":
        issues.append("prewarm_not_selected_v2")
    if payload.get("test_only_injected_client") is not False:
        issues.append("prewarm_not_real_sealed_client")
    if telemetry.get("ready") is not True:
        issues.append("load_telemetry_not_ready")
    if telemetry.get("telemetry_scope") != "initial_worker_start_and_model_load":
        issues.append("load_telemetry_scope_mismatch")
    if telemetry.get("model_reused") is not False:
        issues.append("initial_load_not_proven_cold")
    if not _safe_load_qwen_absent(qwen):
        issues.append("qwen_absence_not_proven_before_load")
    if "qwen_records" in qwen:
        issues.append("raw_qwen_records_exposed_in_safe_load_telemetry")
    if worker_start.get("ready") is not True:
        issues.append("worker_start_not_ready")
    if worker_start.get("model_loaded_before_explicit_load") is not False:
        issues.append("worker_loaded_before_explicit_load")
    if worker_start.get("worker_sha256") != V2_WORKER_SHA256:
        issues.append("worker_start_hash_mismatch")
    if worker_start.get("config_sha256") != V2_CONFIG_SHA256:
        issues.append("worker_config_hash_mismatch")
    if (
        isinstance(worker_start.get("elapsed_seconds"), bool)
        or not isinstance(worker_start.get("elapsed_seconds"), (int, float))
        or worker_start.get("elapsed_seconds") < 0
    ):
        issues.append("worker_start_timing_missing")
    for key in (
        "actual_gpu_allocation",
        "persistent_model_allocation_present",
        "cuda_synchronize_before_model_load_succeeded",
        "cuda_synchronize_after_conditioning_succeeded",
        "model_and_core_components_cuda",
        "no_rejected_runtime_warnings",
    ):
        if gpu.get(key) is not True:
            issues.append(f"load_gpu_proof_missing:{key}")
    for key in (
        "allocated_before_bytes",
        "allocated_after_bytes",
        "reserved_before_bytes",
        "reserved_after_bytes",
        "peak_allocated_bytes",
        "peak_reserved_bytes",
    ):
        value = gpu.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            issues.append(f"load_gpu_measurement_missing:{key}")
    allocated_before = gpu.get("allocated_before_bytes")
    allocated_after = gpu.get("allocated_after_bytes")
    reserved_before = gpu.get("reserved_before_bytes")
    reserved_after = gpu.get("reserved_after_bytes")
    if all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in (allocated_before, allocated_after)
    ) and allocated_after <= allocated_before:
        issues.append("load_gpu_allocation_did_not_increase")
    if all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in (reserved_before, reserved_after)
    ) and reserved_after <= reserved_before:
        issues.append("load_gpu_reservation_did_not_increase")
    if lifecycle.get("model_loaded") is not True:
        issues.append("load_lifecycle_not_loaded")
    if lifecycle.get("model_load_count") != 1:
        issues.append("load_lifecycle_model_load_count_mismatch")
    if lifecycle.get("reference_conditioning_count") != 1:
        issues.append("load_lifecycle_reference_conditioning_count_mismatch")
    if lifecycle.get("conditioned_reference_sha256") != APPROVED_REFERENCE_SHA256:
        issues.append("load_reference_conditioning_hash_mismatch")
    if identity.get("profile_sha256") != APPROVED_PROFILE_SHA256:
        issues.append("load_profile_hash_mismatch")
    if identity.get("reference_sha256") != APPROVED_REFERENCE_SHA256:
        issues.append("load_reference_hash_mismatch")
    for key, expected in EXPECTED_RUNTIME_VERSIONS.items():
        if versions.get(key) != expected:
            issues.append(f"load_runtime_version_mismatch:{key}")
    for key in EXPECTED_RUNTIME_CUDA_CHECKS:
        if runtime_checks.get(key) is not True:
            issues.append(f"load_runtime_cuda_check_missing:{key}")
    for key in EXPECTED_LOAD_RESOURCE_FIELDS:
        value = resources.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            issues.append(f"load_resource_measurement_missing:{key}")
    phase_names: list[str] = []
    for item in phases:
        if not isinstance(item, dict):
            issues.append("load_phase_timing_not_object")
            continue
        phase = str(item.get("phase") or "")
        phase_names.append(phase)
        elapsed = item.get("elapsed_seconds")
        if (
            isinstance(elapsed, bool)
            or not isinstance(elapsed, (int, float))
            or elapsed < 0
        ):
            issues.append(f"load_phase_timing_missing:{phase}")
        if item.get("status") != "passed":
            issues.append(f"load_phase_not_passed:{phase}")
    if phase_names != list(EXPECTED_LOAD_PHASES):
        issues.append("load_phase_sequence_mismatch")
    if not isinstance(telemetry.get("operation_seconds"), (int, float)):
        issues.append("load_operation_timing_missing")
    transport = telemetry.get("parent_transport_timing")
    if not isinstance(transport, dict) or not isinstance(
        transport.get("elapsed_seconds"), (int, float)
    ):
        issues.append("load_transport_timing_missing")
    return issues


def turn_issues(
    result: Any,
    *,
    sentence: str,
    expected_path: Path,
    wav_validation: dict[str, Any],
) -> list[str]:
    payload = result if isinstance(result, dict) else {}
    issues: list[str] = []
    expected_values = {
        "generated": True,
        "route_id": EXPECTED_ROUTE_ID,
        "selected_candidate_version": "v2",
        "application_route_connected": True,
        "production_route_promoted": False,
        "approved_voice_path_used": "blackwell_gpu",
        "gpu_synthesis_attempted": True,
        "cpu_synthesis_attempted": False,
        "automatic_cpu_fallback_used": False,
        "generic_voice_used": False,
        "sapi_voice_used": False,
        "fallback_used": False,
        "playback": False,
        "channel": "public_spoken_only",
        "requested_text_bound": True,
        "device": "cuda",
        "profile_sha256": APPROVED_PROFILE_SHA256,
        "reference_sha256": APPROVED_REFERENCE_SHA256,
        "text_sha256": hashlib.sha256(sentence.encode("utf-8")).hexdigest(),
        "test_only_injected_client": False,
        "full_gpu_acceptance_sha256": FULL_GPU_PASS_SHA256,
        "conditioning_reused": True,
        "persistent_worker_reused": True,
        "sidecar_lifecycle": "session_owned_persistent_candidate_v2",
    }
    for key, expected in expected_values.items():
        if payload.get(key) != expected:
            issues.append(f"turn_contract_mismatch:{key}")
    try:
        returned_path = Path(str(payload.get("audio_path") or "")).resolve()
    except (OSError, ValueError):
        returned_path = Path()
    if returned_path != expected_path.resolve():
        issues.append("turn_audio_path_mismatch")
    if wav_validation.get("passed") is not True:
        issues.append("turn_wav_invalid_or_silent")
    worker_wav = payload.get("wav_validation")
    worker_wav = worker_wav if isinstance(worker_wav, dict) else {}
    if worker_wav.get("sha256") != wav_validation.get("sha256"):
        issues.append("turn_wav_hash_not_bound")
    if not _qwen_absent(payload.get("parent_qwen_residency_before_synthesis")):
        issues.append("qwen_absence_not_proven_before_synthesis")
    gpu = payload.get("gpu_proof")
    gpu = gpu if isinstance(gpu, dict) else {}
    for key in (
        "actual_gpu_execution",
        "persistent_model_allocation_present",
        "model_and_core_components_cuda",
        "cuda_synchronize_before_generation_succeeded",
        "cuda_synchronize_after_generation_succeeded",
        "generation_peak_exceeded_baseline",
        "no_rejected_runtime_warnings",
        "qwen_absence_proven_for_accepted_generation",
        "official_host_return_contract_satisfied",
        "accepted_output_tensors_host_cpu",
    ):
        if gpu.get(key) is not True:
            issues.append(f"turn_gpu_proof_missing:{key}")
    if gpu.get("accepted_output_tensors_cuda") is not False:
        issues.append("turn_host_return_contract_mismatch")
    route = payload.get("approved_voice_routing")
    route = route if isinstance(route, dict) else {}
    exact_route_values = {
        "actual_approved_path_used": "blackwell_gpu",
        "preferred_path": EXPECTED_ROUTE_ID,
        "preferred_path_used": True,
        "automatic_cpu_fallback_used": False,
        "generic_voice_fallback_used": False,
        "sapi_fallback_used": False,
        "unsealed_in_process_fallback_used": False,
        "one_shot_gpu_rollback_invoked": False,
        "arbitrary_model_unload_performed": False,
    }
    for key, expected in exact_route_values.items():
        if route.get(key) != expected:
            issues.append(f"application_route_truth_mismatch:{key}")
    if not isinstance(payload.get("integration_elapsed_seconds"), (int, float)):
        issues.append("turn_integration_timing_missing")
    transport = payload.get("parent_transport_timing")
    if not isinstance(transport, dict) or not isinstance(
        transport.get("elapsed_seconds"), (int, float)
    ):
        issues.append("turn_transport_timing_missing")
    if not isinstance(payload.get("operation_seconds"), (int, float)):
        issues.append("turn_operation_timing_missing")
    return issues


def release_issues(release: Any, after_status: Any) -> list[str]:
    payload = release if isinstance(release, dict) else {}
    persistent = payload.get("persistent_release")
    persistent = persistent if isinstance(persistent, dict) else {}
    v2 = persistent.get("v2_release")
    v2 = v2 if isinstance(v2, dict) else {}
    cleanup = v2.get("cleanup")
    cleanup = cleanup if isinstance(cleanup, dict) else {}
    unload = cleanup.get("unload_telemetry")
    unload = unload if isinstance(unload, dict) else {}
    last_unload = unload.get("last_unload")
    last_unload = last_unload if isinstance(last_unload, dict) else {}
    status = after_status if isinstance(after_status, dict) else {}
    issues: list[str] = []
    if payload.get("released") is not True:
        issues.append("host_release_not_reported")
    if payload.get("persistent_cleanup_proven") is not True:
        issues.append("host_persistent_cleanup_not_proven")
    if persistent.get("released") is not True:
        issues.append("persistent_release_not_reported")
    if persistent.get("owned_worker_closed") is not True:
        issues.append("persistent_owned_worker_close_not_proven")
    if persistent.get("model_was_loaded") is not True:
        issues.append("persistent_loaded_model_release_not_proven")
    if persistent.get("v1_release") is not None:
        issues.append("v1_release_unexpected")
    if cleanup.get("owned_worker_was_present") is not True:
        issues.append("owned_v2_worker_not_present_at_release")
    if cleanup.get("owned_worker_closed") is not True:
        issues.append("owned_v2_worker_clean_exit_not_proven")
    if cleanup.get("owned_process_forced_termination") is not False:
        issues.append("owned_v2_worker_forced_termination")
    if cleanup.get("forced_for_inflight_operation") is not False:
        issues.append("release_occurred_during_inflight_operation")
    if cleanup.get("forced_for_unresponsive_idle_cleanup") is not False:
        issues.append("release_forced_unresponsive_idle_cleanup")
    if cleanup.get("cleanup_thread_finished") is not True:
        issues.append("release_cleanup_thread_not_finished")
    if cleanup.get("graceful_cleanup_bound_seconds") != 20.0:
        issues.append("release_graceful_cleanup_bound_mismatch")
    if cleanup.get("owned_process_exit_code") != 0:
        issues.append("owned_v2_worker_exit_code_not_zero")
    if cleanup.get("unload_reported") is not True:
        issues.append("owned_v2_worker_unload_response_missing")
    if cleanup.get("close_reported") is not True:
        issues.append("owned_v2_worker_close_response_missing")
    if cleanup.get("unload_error_type") not in {"", None}:
        issues.append("owned_v2_worker_unload_error")
    if cleanup.get("close_error_type") not in {"", None}:
        issues.append("owned_v2_worker_close_error")
    if unload.get("reported") is not True or unload.get("unloaded") is not True:
        issues.append("owned_v2_worker_unload_not_reported")
    if unload.get("model_was_loaded") is not True:
        issues.append("owned_v2_model_was_not_loaded_at_unload")
    if unload.get("lifecycle_model_loaded_after") is not False:
        issues.append("owned_v2_model_remained_loaded_after_unload")
    if not isinstance(unload.get("operation_seconds"), (int, float)):
        issues.append("owned_v2_unload_operation_timing_missing")
    unload_transport = unload.get("parent_transport_timing")
    if not isinstance(unload_transport, dict) or not isinstance(
        unload_transport.get("elapsed_seconds"), (int, float)
    ):
        issues.append("owned_v2_unload_transport_timing_missing")
    if last_unload.get("was_loaded") is not True:
        issues.append("owned_v2_last_unload_did_not_release_loaded_model")
    for prefix in ("allocated", "reserved"):
        before = last_unload.get(f"{prefix}_before_bytes")
        after = last_unload.get(f"{prefix}_after_bytes")
        returned = last_unload.get(f"{prefix}_returned_bytes")
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in (before, after, returned)
        ):
            issues.append(f"owned_v2_unload_measurements_missing:{prefix}")
            continue
        if returned <= 0:
            issues.append(f"owned_v2_unload_return_not_proven:{prefix}_returned_bytes")
        if after > 64 * 1024 * 1024:
            issues.append(f"owned_v2_unload_residual_too_large:{prefix}")
        expected_return = max(0, before - after)
        tolerance = max(1024 * 1024, int(before * 0.01))
        if abs(returned - expected_return) > tolerance:
            issues.append(f"owned_v2_unload_return_inconsistent:{prefix}")
        if before > 0 and returned / before < 0.90:
            issues.append(f"owned_v2_unload_return_ratio_below_90_percent:{prefix}")
    if status.get("session_owner"):
        issues.append("session_owner_remained_after_release")
    if status.get("owned_worker_running") is not False:
        issues.append("owned_worker_running_after_release")
    if status.get("model_loaded") is not False:
        issues.append("model_loaded_after_release")
    versions = status.get("candidate_versions")
    versions = versions if isinstance(versions, dict) else {}
    for version in ("v1", "v2"):
        facts = versions.get(version)
        facts = facts if isinstance(facts, dict) else {}
        if facts.get("owned_state_present") is not False:
            issues.append(f"owned_state_remained_after_release:{version}")
    return issues


def gpu_release_boundary_issues(before: Any, after: Any) -> list[str]:
    """Require the external GPU boundary to return near its pre-load state."""

    before_payload = before if isinstance(before, dict) else {}
    after_payload = after if isinstance(after, dict) else {}
    issues: list[str] = []
    if before_payload.get("query_succeeded") is not True:
        issues.append("gpu_before_snapshot_unavailable")
    if after_payload.get("query_succeeded") is not True:
        issues.append("gpu_after_release_snapshot_unavailable")
    before_rows = before_payload.get("rows")
    after_rows = after_payload.get("rows")
    before_rows = before_rows if isinstance(before_rows, list) else []
    after_rows = after_rows if isinstance(after_rows, list) else []
    before_map = {
        (row.get("index"), row.get("name")): row
        for row in before_rows
        if isinstance(row, dict)
    }
    after_map = {
        (row.get("index"), row.get("name")): row
        for row in after_rows
        if isinstance(row, dict)
    }
    if not before_map or before_map.keys() != after_map.keys():
        issues.append("gpu_release_snapshot_device_set_mismatch")
        return issues
    for key, before_row in before_map.items():
        after_row = after_map[key]
        before_used = before_row.get("memory_used_mib")
        after_used = after_row.get("memory_used_mib")
        if any(
            not isinstance(value, (int, float)) or isinstance(value, bool)
            for value in (before_used, after_used)
        ):
            issues.append(f"gpu_release_usage_missing:{key[0]}")
            continue
        if after_used > before_used + 256.0:
            issues.append(f"gpu_release_external_residual_over_256_mib:{key[0]}")
    return issues


def parent_wrapper_issues(started: Any, wrapper: Any) -> list[str]:
    start_payload = started if isinstance(started, dict) else {}
    payload = wrapper if isinstance(wrapper, dict) else {}
    issues: list[str] = []
    if payload.get("parent_exception") is not None:
        issues.append("parent_exception")
    if payload.get("timed_out") is not False:
        issues.append("parent_child_timed_out")
    if payload.get("child_exit_code") != 0:
        issues.append("child_exit_not_zero")
    if payload.get("final_report_present") is not True:
        issues.append("final_report_missing")
    if payload.get("protected_unchanged_from_attempt_start") is not True:
        issues.append("parent_protected_files_changed")
    after = payload.get("protected_after_parent")
    after = after if isinstance(after, dict) else {}
    issues.extend(pinned_hash_issues(after))
    if after != start_payload.get("protected_before_parent"):
        if "parent_protected_files_changed" not in issues:
            issues.append("parent_protected_files_changed")
    return sorted(set(issues))


def _watchdog_worker(stop: threading.Event, attempt_dir: Path) -> None:
    if stop.wait(CHILD_WATCHDOG_SECONDS):
        return
    evidence: dict[str, Any] = {
        "watchdog_fired": True,
        "fired_at": _utc_now(),
        "timeout_seconds": CHILD_WATCHDOG_SECONDS,
        "cleanup_requested": False,
    }
    try:
        from Core import voice_output

        cleanup_started = time.perf_counter()
        cleanup = voice_output.release_voice_output("application_route_v2_child_watchdog")
        evidence.update(
            {
                "cleanup_requested": True,
                "cleanup_elapsed_seconds": round(time.perf_counter() - cleanup_started, 6),
                "cleanup": cleanup,
                "status_after_cleanup": voice_output.persistent_blackwell_voice_status(),
            }
        )
    except BaseException as exc:  # Watchdog must preserve the error before exit.
        evidence["cleanup_error_type"] = type(exc).__name__
    try:
        _atomic_json(attempt_dir / "WATCHDOG_CLEANUP.json", evidence)
    finally:
        os._exit(124)


def _child_run(attempt_dir: Path, generated_dir: Path) -> int:
    from Core import voice_output

    started_at = _utc_now()
    overall_started = time.perf_counter()
    watchdog_stop = threading.Event()
    watchdog = threading.Thread(
        target=_watchdog_worker,
        args=(watchdog_stop, attempt_dir),
        name="kira-v2-application-route-watchdog",
        daemon=True,
    )
    watchdog.start()
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "kira_persistent_blackwell_v2_application_route_acceptance",
        "harness_id": HARNESS_ID,
        "started_at": started_at,
        "status": "started",
        "engineering_pass": False,
        "owner_heard_acceptance": False,
        "playback_performed": False,
        "promotion_performed": False,
        "model_text_call_performed": False,
        "blender_operation_performed": False,
        "public_spoken_sentences": list(PUBLIC_SPOKEN_SENTENCES),
        "public_spoken_sha256": list(PUBLIC_SPOKEN_SHA256),
        "attempt_relative": attempt_dir.relative_to(ROOT).as_posix(),
        "generated_relative": generated_dir.relative_to(ROOT).as_posix(),
    }
    cleanup_result: dict[str, Any] | None = None
    try:
        before = protected_hashes()
        report["protected_before"] = before
        issues = pinned_hash_issues(before)
        identity_hashes = {
            APPROVED_PROFILE_RELATIVE: sha256_file(_project_file(APPROVED_PROFILE_RELATIVE)),
            APPROVED_REFERENCE_RELATIVE: sha256_file(
                _project_file(APPROVED_REFERENCE_RELATIVE)
            ),
            FULL_GPU_PASS_RELATIVE: sha256_file(_project_file(FULL_GPU_PASS_RELATIVE)),
        }
        report["identity_and_acceptance_hashes"] = identity_hashes
        if identity_hashes[APPROVED_PROFILE_RELATIVE] != APPROVED_PROFILE_SHA256:
            issues.append("approved_profile_hash_mismatch")
        if identity_hashes[APPROVED_REFERENCE_RELATIVE] != APPROVED_REFERENCE_SHA256:
            issues.append("approved_reference_hash_mismatch")
        if identity_hashes[FULL_GPU_PASS_RELATIVE] != FULL_GPU_PASS_SHA256:
            issues.append("full_gpu_acceptance_hash_mismatch")
        environment = _environment_evidence()
        report["child_environment"] = environment
        if environment.get("exact_v2_only") is not True:
            issues.append("child_environment_not_exact_v2_only")

        config = voice_output.load_kira_production_voice_config()
        config.play_audio = False
        config.dry_run = False
        config.enabled = True
        report["voice_config"] = {
            "engine": config.engine,
            "reference": str(config.chatterbox_reference_audio).replace("\\", "/"),
            "device": config.chatterbox_device,
            "play_audio": config.play_audio,
            "dry_run": config.dry_run,
            "enabled": config.enabled,
            "output_dir": config.output_dir,
        }
        if config.engine != "chatterbox_tts":
            issues.append("voice_config_engine_not_chatterbox")
        if str(config.chatterbox_reference_audio).replace("\\", "/") != APPROVED_REFERENCE_RELATIVE:
            issues.append("voice_config_reference_not_exact")
        if config.chatterbox_device != "cuda":
            issues.append("voice_config_device_not_cuda")
        if config.play_audio is not False:
            issues.append("voice_config_playback_not_disabled")

        report["qwen_before"] = voice_output._qwen_residency_evidence()
        report["gpu_before"] = _nvidia_snapshot()
        if not _qwen_absent(report["qwen_before"]):
            issues.append("qwen_not_proven_absent_before_application_route")

        owner = f"kira:application-route-v2:{attempt_dir.name}"
        begin_started = time.perf_counter()
        begun = voice_output.begin_persistent_blackwell_voice_session(owner)
        report["session_begin"] = {
            "elapsed_seconds": round(time.perf_counter() - begin_started, 6),
            "result": begun,
        }
        if begun.get("begun") is not True or begun.get("selected_candidate_version") != "v2":
            issues.append("exact_v2_owned_session_not_begun")

        prewarm_started = time.perf_counter()
        prewarm = voice_output.prewarm_persistent_blackwell_voice(owner)
        report["prewarm"] = {
            "external_elapsed_seconds": round(time.perf_counter() - prewarm_started, 6),
            "result": prewarm,
        }
        issues.extend(load_telemetry_issues(prewarm))
        report["gpu_after_prewarm"] = _nvidia_snapshot()

        turns: list[dict[str, Any]] = []
        for index, sentence in enumerate(PUBLIC_SPOKEN_SENTENCES, start=1):
            target = generated_dir / f"turn_{index:02d}.wav"
            turn_started = time.perf_counter()
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                sentence,
                target,
                config,
            )
            external_elapsed = round(time.perf_counter() - turn_started, 6)
            wav_validation = _validate_wav(target)
            current_issues = turn_issues(
                result,
                sentence=sentence,
                expected_path=target,
                wav_validation=wav_validation,
            )
            issues.extend(f"turn_{index:02d}:{issue}" for issue in current_issues)
            turns.append(
                {
                    "turn": index,
                    "sentence": sentence,
                    "sentence_sha256": PUBLIC_SPOKEN_SHA256[index - 1],
                    "external_elapsed_seconds": external_elapsed,
                    "result": result,
                    "wav_validation": wav_validation,
                    "issues": current_issues,
                    "gpu_boundary_after": _nvidia_snapshot(),
                }
            )
        report["turns"] = turns
        worker_session_ids = [
            str((turn.get("result") or {}).get("session_id") or "") for turn in turns
        ]
        if not worker_session_ids[0] or len(set(worker_session_ids)) != 1:
            issues.append("two_turns_did_not_use_one_exact_owned_worker_session")

        release_started = time.perf_counter()
        cleanup_result = voice_output.release_voice_output(
            "application_route_v2_acceptance_complete"
        )
        release_elapsed = round(time.perf_counter() - release_started, 6)
        after_status = voice_output.persistent_blackwell_voice_status()
        report["release"] = {
            "external_elapsed_seconds": release_elapsed,
            "result": cleanup_result,
            "status_after": after_status,
        }
        issues.extend(release_issues(cleanup_result, after_status))
        cleanup = (
            (((cleanup_result or {}).get("persistent_release") or {}).get("v2_release") or {}).get(
                "cleanup"
            )
            or {}
        )
        unload_telemetry = cleanup.get("unload_telemetry") or {}
        report["performance_summary"] = {
            "load": {
                "external_elapsed_seconds": report["prewarm"]["external_elapsed_seconds"],
                "worker_operation_seconds": (prewarm.get("load_telemetry") or {}).get(
                    "operation_seconds"
                ),
                "transport_elapsed_seconds": (
                    (prewarm.get("load_telemetry") or {}).get("parent_transport_timing")
                    or {}
                ).get("elapsed_seconds"),
            },
            "first_turn": {
                "external_elapsed_seconds": turns[0]["external_elapsed_seconds"],
                "integration_elapsed_seconds": (turns[0]["result"] or {}).get(
                    "integration_elapsed_seconds"
                ),
                "worker_operation_seconds": (turns[0]["result"] or {}).get(
                    "operation_seconds"
                ),
                "worker_generation_seconds": (turns[0]["result"] or {}).get(
                    "generation_seconds"
                ),
            },
            "warm_second_turn": {
                "external_elapsed_seconds": turns[1]["external_elapsed_seconds"],
                "integration_elapsed_seconds": (turns[1]["result"] or {}).get(
                    "integration_elapsed_seconds"
                ),
                "worker_operation_seconds": (turns[1]["result"] or {}).get(
                    "operation_seconds"
                ),
                "worker_generation_seconds": (turns[1]["result"] or {}).get(
                    "generation_seconds"
                ),
            },
            "release": {
                "external_elapsed_seconds": release_elapsed,
                "worker_operation_seconds": unload_telemetry.get("operation_seconds"),
                "transport_elapsed_seconds": (
                    unload_telemetry.get("parent_transport_timing") or {}
                ).get("elapsed_seconds"),
            },
        }
        report["qwen_after"] = voice_output._qwen_residency_evidence()
        report["gpu_after_release"] = _nvidia_snapshot()
        gpu_boundary_issues = gpu_release_boundary_issues(
            report["gpu_before"], report["gpu_after_release"]
        )
        report["gpu_release_boundary_issues"] = gpu_boundary_issues
        issues.extend(gpu_boundary_issues)
        if not _qwen_absent(report["qwen_after"]):
            issues.append("qwen_not_proven_absent_after_application_route")

        after = protected_hashes()
        report["protected_after"] = after
        report["protected_files_unchanged"] = before == after
        if before != after:
            issues.append("protected_or_tracked_file_changed")
        issues.extend(pinned_hash_issues(after))

        report["checks"] = {
            "exact_v2_flag_only": environment.get("exact_v2_only") is True,
            "approved_profile_exact": identity_hashes.get(APPROVED_PROFILE_RELATIVE)
            == APPROVED_PROFILE_SHA256,
            "approved_reference_exact": identity_hashes.get(APPROVED_REFERENCE_RELATIVE)
            == APPROVED_REFERENCE_SHA256,
            "full_gpu_engineering_pass_exact": identity_hashes.get(FULL_GPU_PASS_RELATIVE)
            == FULL_GPU_PASS_SHA256,
            "two_public_spoken_turns": len(turns) == 2,
            "all_wavs_valid_non_silent": all(
                turn["wav_validation"].get("passed") is True for turn in turns
            ),
            "all_routes_exact_v2": all(
                (turn["result"] or {}).get("route_id") == EXPECTED_ROUTE_ID
                for turn in turns
            ),
            "one_exact_owned_worker_session": bool(worker_session_ids[0])
            and len(set(worker_session_ids)) == 1
            and all(
                (turn["result"] or {}).get("persistent_worker_reused") is True
                and (turn["result"] or {}).get("conditioning_reused") is True
                for turn in turns
            ),
            "gpu_execution_proven_each_turn": all(
                ((turn["result"] or {}).get("gpu_proof") or {}).get(
                    "actual_gpu_execution"
                )
                is True
                for turn in turns
            ),
            "qwen_absent_before_during_after": (
                _qwen_absent(report["qwen_before"])
                and all(
                    _qwen_absent(
                        (turn["result"] or {}).get(
                            "parent_qwen_residency_before_synthesis"
                        )
                    )
                    for turn in turns
                )
                and _qwen_absent(report["qwen_after"])
            ),
            "cpu_generic_sapi_fallback_false": all(
                (turn["result"] or {}).get("cpu_synthesis_attempted") is False
                and (turn["result"] or {}).get("automatic_cpu_fallback_used") is False
                and (turn["result"] or {}).get("generic_voice_used") is False
                and (turn["result"] or {}).get("sapi_voice_used") is False
                and (turn["result"] or {}).get("fallback_used") is False
                for turn in turns
            ),
            "no_playback": all(
                (turn["result"] or {}).get("playback") is False for turn in turns
            ),
            "no_promotion": all(
                (turn["result"] or {}).get("production_route_promoted") is False
                for turn in turns
            ),
            "exact_owned_clean_release": not release_issues(cleanup_result, after_status),
            "external_vram_return_proven": not gpu_boundary_issues,
            "protected_files_unchanged": before == after,
            "no_model_text_call": True,
        }
        report["issues"] = sorted(set(issues))
        report["engineering_pass"] = not report["issues"] and all(
            report["checks"].values()
        )
        report["status"] = (
            "engineering_pass_pending_owner_heard_acceptance"
            if report["engineering_pass"]
            else "engineering_fail_preserved_no_playback"
        )
        return_code = 0 if report["engineering_pass"] else 1
    except BaseException as exc:
        report["status"] = "harness_exception_preserved_no_playback"
        report["exception"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        return_code = 1
    finally:
        if cleanup_result is None:
            try:
                cleanup_started = time.perf_counter()
                cleanup_result = voice_output.release_voice_output(
                    "application_route_v2_acceptance_finally"
                )
                report["finally_cleanup"] = {
                    "elapsed_seconds": round(time.perf_counter() - cleanup_started, 6),
                    "result": cleanup_result,
                    "status_after": voice_output.persistent_blackwell_voice_status(),
                }
            except BaseException as exc:
                report["finally_cleanup"] = {"error_type": type(exc).__name__}
        watchdog_stop.set()
        watchdog.join(timeout=2)
        report["finished_at"] = _utc_now()
        report["total_wall_seconds"] = round(time.perf_counter() - overall_started, 6)
        report["playback_performed"] = False
        report["promotion_performed"] = False
        report["model_text_call_performed"] = False
        _atomic_json(attempt_dir / "FINAL_REPORT.json", report)
    return return_code


def _reserve_attempt(label: str) -> tuple[Path, Path]:
    if ATTEMPT_LABEL_PATTERN.fullmatch(label) is None:
        raise ValueError("attempt label must match attempt_NN")
    attempt_dir = EVIDENCE_ROOT / label
    generated_dir = GENERATED_ROOT / label
    attempt_dir.mkdir(parents=True, exist_ok=False)
    try:
        generated_dir.mkdir(parents=True, exist_ok=False)
    except BaseException:
        # Keep the append-only evidence directory and record why generation
        # could not begin; never delete an already reserved attempt.
        _atomic_json(
            attempt_dir / "ATTEMPT_RESERVATION_FAILURE.json",
            {
                "attempt": label,
                "generated_target": generated_dir.relative_to(ROOT).as_posix(),
                "reason": "generated_attempt_directory_already_exists_or_unavailable",
                "at": _utc_now(),
            },
        )
        raise
    return attempt_dir, generated_dir


def _parent_run(attempt_label: str) -> int:
    attempt_dir, generated_dir = _reserve_attempt(attempt_label)
    started = {
        "schema_version": 1,
        "artifact_kind": "kira_persistent_blackwell_v2_application_route_attempt_started",
        "harness_id": HARNESS_ID,
        "attempt": attempt_label,
        "started_at": _utc_now(),
        "prepared_boundaries": {
            "no_playback": True,
            "no_promotion": True,
            "no_model_text_call": True,
            "no_blender": True,
            "exact_v2_flag_only": True,
            "sealed_cpu_fallback_disabled_for_acceptance": True,
            "one_shot_gpu_rollback_disabled_for_acceptance": True,
        },
        "parent_timeout_seconds": PARENT_CHILD_TIMEOUT_SECONDS,
        "child_watchdog_seconds": CHILD_WATCHDOG_SECONDS,
        "protected_before_parent": protected_hashes(),
    }
    _atomic_json(attempt_dir / "ATTEMPT_STARTED.json", started)
    child_environment = _build_child_environment()
    command = [
        sys.executable,
        str(_project_file(HARNESS_RELATIVE)),
        "--child-run",
        "--attempt-relative",
        attempt_dir.relative_to(ROOT).as_posix(),
        "--generated-relative",
        generated_dir.relative_to(ROOT).as_posix(),
    ]
    process: subprocess.Popen[str] | None = None
    stdout = ""
    stderr = ""
    timed_out = False
    terminated = False
    killed = False
    exact_child_cleanup_attempted = False
    exact_child_cleanup_proven = False
    parent_exception: dict[str, str] | None = None
    parent_started = time.perf_counter()
    try:
        try:
            process = subprocess.Popen(
                command,
                cwd=str(ROOT),
                env=child_environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            stdout, stderr = process.communicate(timeout=PARENT_CHILD_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            timed_out = True
            exact_child_cleanup_attempted = True
            if process is not None and process.poll() is None:
                process.terminate()
                terminated = True
            try:
                if process is not None:
                    stdout, stderr = process.communicate(
                        timeout=PARENT_TERMINATE_WAIT_SECONDS
                    )
            except subprocess.TimeoutExpired:
                if process is not None and process.poll() is None:
                    process.kill()
                    killed = True
                if process is not None:
                    stdout, stderr = process.communicate(
                        timeout=PARENT_KILL_WAIT_SECONDS
                    )
    except BaseException as exc:
        parent_exception = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        if process is not None and process.poll() is None:
            exact_child_cleanup_attempted = True
            try:
                process.terminate()
                terminated = True
                stdout, stderr = process.communicate(
                    timeout=PARENT_TERMINATE_WAIT_SECONDS
                )
            except BaseException:
                try:
                    if process.poll() is None:
                        process.kill()
                        killed = True
                    stdout, stderr = process.communicate(
                        timeout=PARENT_KILL_WAIT_SECONDS
                    )
                except BaseException as cleanup_exc:
                    if parent_exception is None:
                        parent_exception = {
                            "type": type(cleanup_exc).__name__,
                            "message": str(cleanup_exc),
                            "traceback": traceback.format_exc(),
                        }
        exact_child_cleanup_proven = bool(
            process is None or process.poll() is not None
        )
    wrapper = {
        "schema_version": 1,
        "artifact_kind": "kira_persistent_blackwell_v2_application_route_parent_wrapper",
        "harness_id": HARNESS_ID,
        "attempt": attempt_label,
        "command": command,
        "child_environment": {key: child_environment.get(key) for key in EXACT_CHILD_ENVIRONMENT},
        "child_spawned": process is not None,
        "child_exit_code": process.returncode if process is not None else None,
        "timed_out": timed_out,
        "owned_child_terminated": terminated,
        "owned_child_killed": killed,
        "exact_child_cleanup_attempted": exact_child_cleanup_attempted,
        "exact_child_cleanup_proven": exact_child_cleanup_proven,
        "parent_exception": parent_exception,
        "elapsed_seconds": round(time.perf_counter() - parent_started, 6),
        "stdout": stdout,
        "stderr": stderr,
        "final_report_present": (attempt_dir / "FINAL_REPORT.json").is_file(),
        "watchdog_cleanup_present": (attempt_dir / "WATCHDOG_CLEANUP.json").is_file(),
        "protected_after_parent": protected_hashes(),
        "finished_at": _utc_now(),
    }
    wrapper["protected_unchanged_from_attempt_start"] = (
        wrapper["protected_after_parent"] == started["protected_before_parent"]
    )
    wrapper["issues"] = parent_wrapper_issues(started, wrapper)
    _atomic_json(attempt_dir / "PARENT_WRAPPER.json", wrapper)
    if wrapper["issues"]:
        return 1
    try:
        final = json.loads((attempt_dir / "FINAL_REPORT.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return 1
    return 0 if final.get("engineering_pass") is True else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt-label", default="attempt_01")
    parser.add_argument("--child-run", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--attempt-relative", help=argparse.SUPPRESS)
    parser.add_argument("--generated-relative", help=argparse.SUPPRESS)
    return parser.parse_args()


def _validated_child_path(relative: str | None, expected_parent: Path) -> Path:
    if not relative:
        raise ValueError("child path is required")
    resolved = _project_file(relative)
    resolved.relative_to(expected_parent.resolve())
    if not resolved.is_dir():
        raise ValueError("child path must be a pre-reserved directory")
    return resolved


def main() -> int:
    args = _parse_args()
    if args.child_run:
        attempt = _validated_child_path(args.attempt_relative, EVIDENCE_ROOT)
        generated = _validated_child_path(args.generated_relative, GENERATED_ROOT)
        if attempt.name != generated.name:
            raise ValueError("evidence and generated attempt labels must match")
        return _child_run(attempt, generated)
    return _parent_run(args.attempt_label)


if __name__ == "__main__":
    raise SystemExit(main())
