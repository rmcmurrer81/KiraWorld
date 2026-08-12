#!/usr/bin/env python3
"""Revision 01 bounded full-GPU acceptance for the inactive voice v2 candidate.

This file is an append-only successor to the v1 acceptance harness.  Its
default, ``--describe``, and ``--static-self-check`` paths never start Torch,
CUDA, Chatterbox, Ollama, audio, or Blender.  A live run requires all explicit
operator bindings and still cannot promote the candidate or play audio.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Package-qualified imports are intentional.  The v1 and v2 candidates have
# modules with the same leaf names; unqualified imports can silently reuse a
# wrong module already present in sys.modules.
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v2.candidate_client import (  # noqa: E402
    PersistentBlackwellVoiceCandidateClient,
    restricted_candidate_environment,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v2.candidate_contract import (  # noqa: E402
    CONFIG_PATH,
    load_candidate_config,
    project_file,
    qwen_residency_evidence,
    sha256_file,
    sha256_text,
    verify_candidate_config,
)


HARNESS_ID = "persistent_blackwell_voice_candidate_v2_full_gpu_acceptance_revision01"
APPROVED_PUBLIC_SENTENCE = "I don't see anything and I don't hear anything."
APPROVED_PUBLIC_SENTENCE_SHA256 = (
    "0956e983e4287fb61142377cfe09fe3277c6c33747da9bec9da312b316dcfaf7"
)
V2_CONFIG_SHA256 = "805c1d2836c618970a81f5f44d31f81f67e204173bd919857452daa8dbedc8bb"
V2_CONTRACT_SHA256 = "863c6ece050b12af157565c60df6fd82b207dae5476e693cc08e34b392c8f910"
V2_CLIENT_SHA256 = "9f33ef0d9fd969da05ce48eb148163efc77306bfd3bc215efcb482e68e7261a8"
V2_WORKER_SHA256 = "b6f2dcc816537552db02d00c5a1932057f2d99b5d206a578344d4a92523b3cad"
PRODUCTION_ROUTING_SHA256 = (
    "a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81"
)
READINESS_TOOL_RELATIVE = "Tools/run_blackwell_torch_readiness.py"
READINESS_TOOL_SHA256 = "0c3b17a821553ffbe2c8d70d01803a634a9cdd3c670b5f787007bfdac640d3b5"
IMPORT_ONLY_REPORT_RELATIVE = (
    "RecoverySprint/continuation_20260802/"
    "persistent_blackwell_voice_candidate_acceptance/"
    "import_only_v2_request_gate/attempt_01/FINAL_REPORT.json"
)
IMPORT_ONLY_REPORT_SHA256 = (
    "38a566bf29cf72b5532514a0b7876eb2003e648745a6a36d1581bbf42ef04726"
)
IMPORT_ONLY_HARNESS_SHA256 = (
    "40eaa812edd2ae88c82854909684a4ea1f821ac199627aaf11e3738159aaab10"
)
ACCEPTANCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "full_gpu_v2"
)

STARTUP_TIMEOUT_SECONDS = 60.0
REQUEST_TIMEOUT_SECONDS = 900.0
EAGER_PREFLIGHT_TIMEOUT_SECONDS = 120.0
CLEANUP_DRAIN_TIMEOUT_SECONDS = 10.0
MAX_LIVE_PHASES = 9
MAX_CAPTURE_BYTES = 1024 * 1024

EXPECTED_V2_HASHES = {
    "config": V2_CONFIG_SHA256,
    "contract": V2_CONTRACT_SHA256,
    "client": V2_CLIENT_SHA256,
    "worker": V2_WORKER_SHA256,
}

PROTECTED_PATHS = (
    READINESS_TOOL_RELATIVE,
    "Tools/run_persistent_blackwell_voice_candidate_acceptance.py",
    "Tools/run_persistent_blackwell_voice_candidate_v2_acceptance.py",
    "Tools/run_persistent_blackwell_voice_candidate_v2_acceptance_revision01.py",
    IMPORT_ONLY_REPORT_RELATIVE,
    "Voice/sidecars/kira_approved_voice_routing.json",
    "Voice/sidecars/chatterbox_blackwell_gpu/sidecar_config.json",
    "Voice/sidecars/chatterbox_blackwell_gpu/sidecar_worker.py",
    "Voice/sidecars/chatterbox_py311/sidecar_config.json",
    "Voice/sidecars/chatterbox_py311/sidecar_worker.py",
    "Voice/profiles/temp_ai/kira_voice_profile.json",
    "Voice/reference_packs/kira/kira_online_source_20260706_221447/model_input/approved_reference.wav",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate/candidate_contract.py",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate/candidate_client.py",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate/persistent_worker.py",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate/candidate_config.json",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v2/candidate_contract.py",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v2/candidate_client.py",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v2/persistent_worker.py",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v2/candidate_config.json",
)

FORBIDDEN_RESPONSE_FLAGS = (
    "production_routing_authorized",
    "playback",
    "generic_voice_used",
    "sapi_voice_used",
    "fallback_used",
)

REJECTED_CUDA_TEXT = (
    "no kernel image is available",
    "no kernel image",
    "not compatible with the current pytorch installation",
    "unsupported gpu architecture",
    "unsupported architecture",
    "sm_120 is not compatible",
)

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _plain_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and float(value) >= 0.0
    )


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _hash_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _attempt_names() -> list[str]:
    if not ACCEPTANCE_ROOT.is_dir():
        return []
    return sorted(item.name for item in ACCEPTANCE_ROOT.iterdir())


def allocate_attempt_directory() -> Path:
    ACCEPTANCE_ROOT.mkdir(parents=True, exist_ok=True)
    for index in range(1, 1000):
        candidate = ACCEPTANCE_ROOT / f"attempt_{index:02d}"
        try:
            candidate.mkdir(exist_ok=False)
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError("no append-only v2 full-GPU acceptance slot remains")


def _atomic_bytes_exclusive(path: Path, payload: bytes) -> str:
    """Atomically publish one new artifact without overwriting an old one."""

    if path.exists():
        raise FileExistsError(f"append-only artifact already exists: {path}")
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.part")
    try:
        with temporary.open("xb", buffering=0) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            raise FileExistsError(f"append-only artifact appeared before publish: {path}")
        os.rename(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)
    return _hash_bytes(payload)


def atomic_json_exclusive(path: Path, payload: dict[str, Any]) -> str:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return _atomic_bytes_exclusive(path, encoded)


def file_hashes(paths: Iterable[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for value in paths:
        path = (ROOT / value).resolve()
        try:
            path.relative_to(ROOT.resolve())
            hashes[value] = sha256_file(path) if path.is_file() else "MISSING"
        except Exception as exc:
            hashes[value] = f"ERROR:{type(exc).__name__}:{exc}"
    return hashes


def _artifact_evidence(path: Path) -> dict[str, Any]:
    try:
        if not path.is_file():
            return {"present": False, "bytes": None, "sha256": None}
        return {
            "present": True,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "path": relative(path),
        }
    except Exception as exc:
        return {
            "present": None,
            "bytes": None,
            "sha256": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def qwen_absence_proven(payload: Any) -> bool:
    return bool(
        isinstance(payload, dict)
        and payload.get("query_succeeded") is True
        and payload.get("qwen_absent_proven") is True
        and payload.get("qwen_records") == []
        and payload.get("model_state_changed") is False
    )


def _exact_false_flags(payload: Any, keys: Iterable[str] = FORBIDDEN_RESPONSE_FLAGS) -> bool:
    return isinstance(payload, dict) and all(payload.get(key) is False for key in keys)


def validate_import_only_report_payload(payload: Any) -> list[str]:
    """Return precise issues for the one exact import-only prerequisite."""

    issues: list[str] = []
    if not isinstance(payload, dict):
        return ["report_not_object"]
    exact_top = {
        "schema_version": 1,
        "artifact_kind": "v2_inherited_pipe_torch_import_only_final_report",
        "status": "passed",
        "trusted_child_result": True,
        "parent_bound_exceeded": False,
        "controller_error": None,
        "drains_finalized_before_diagnostic_hashes": True,
        "promotion_performed": False,
        "routing_change_performed": False,
    }
    for key, expected in exact_top.items():
        if payload.get(key) != expected or type(payload.get(key)) is not type(expected):
            issues.append(f"top_{key}_mismatch")
    if payload.get("validation_issues") != []:
        issues.append("validation_issues_not_empty")
    outcomes = payload.get("outcomes")
    if not isinstance(outcomes, dict):
        issues.append("outcomes_missing")
    else:
        for key in (
            "audio_generated",
            "chatterbox_imported",
            "cuda_api_called",
            "fallback_used",
            "generic_voice_used",
            "model_loaded",
            "ollama_called",
            "playback",
            "production_routing_changed",
            "promotion_performed",
            "sapi_voice_used",
            "torchaudio_imported",
        ):
            if outcomes.get(key) is not False:
                issues.append(f"outcome_{key}_not_exact_false")
    cleanup = payload.get("cleanup")
    if not isinstance(cleanup, dict):
        issues.append("cleanup_missing")
    else:
        expected_cleanup = {
            "drains_finalized": True,
            "terminate_sent": False,
            "kill_sent": False,
            "owned_process_exit_code": 0,
            "owned_process_present": True,
        }
        for key, expected in expected_cleanup.items():
            if cleanup.get(key) != expected or type(cleanup.get(key)) is not type(expected):
                issues.append(f"cleanup_{key}_mismatch")
    child_evidence = payload.get("child_result_evidence")
    child = child_evidence.get("payload") if isinstance(child_evidence, dict) else None
    if not (
        isinstance(child_evidence, dict)
        and child_evidence.get("present") is True
        and child_evidence.get("parsed") is True
        and isinstance(child, dict)
    ):
        issues.append("trusted_child_payload_missing")
        child = {}
    expected_child = {
        "schema_version": 1,
        "artifact_kind": "v2_inherited_pipe_torch_import_only_child_result",
        "trusted_child_result": True,
        "torch_imported": True,
        "torch_version": "2.11.0+cu130",
        "reader_parked_at_request_gate": True,
        "reader_readline_absent": True,
        "transport_eof_received": True,
        "transport_serve_returned": True,
        "serve_return_code": 0,
        "harness_sha256": IMPORT_ONLY_HARNESS_SHA256,
        "v2_config_sha256": V2_CONFIG_SHA256,
        "v2_contract_sha256": V2_CONTRACT_SHA256,
        "v2_client_sha256": V2_CLIENT_SHA256,
        "v2_worker_sha256": V2_WORKER_SHA256,
    }
    for key, expected in expected_child.items():
        if child.get(key) != expected or type(child.get(key)) is not type(expected):
            issues.append(f"child_{key}_mismatch")
    for key in (
        "audio_generated",
        "chatterbox_imported",
        "cuda_api_called",
        "fallback_used",
        "generic_voice_used",
        "model_loaded",
        "ollama_called",
        "playback",
        "production_routing_changed",
        "promotion_performed",
        "sapi_voice_used",
        "torchaudio_imported",
    ):
        if child.get(key) is not False:
            issues.append(f"child_{key}_not_exact_false")
    hello = payload.get("hello")
    if not (
        isinstance(hello, dict)
        and hello.get("ready") is True
        and hello.get("model_loaded") is False
        and hello.get("production_routing_authorized") is False
        and hello.get("worker_sha256") == V2_WORKER_SHA256
        and _exact_false_flags(hello)
    ):
        issues.append("hello_contract_mismatch")
    load_response = payload.get("load_response")
    if not (
        isinstance(load_response, dict)
        and load_response.get("ready") is True
        and load_response.get("import_only") is True
        and load_response.get("model_loaded") is False
        and _exact_false_flags(load_response)
    ):
        issues.append("load_response_contract_mismatch")
    return sorted(set(issues))


def verify_import_only_prerequisite() -> dict[str, Any]:
    path = (ROOT / IMPORT_ONLY_REPORT_RELATIVE).resolve()
    path.relative_to(ROOT.resolve())
    actual_hash = sha256_file(path)
    if not hmac.compare_digest(actual_hash, IMPORT_ONLY_REPORT_SHA256):
        raise ValueError("exact v2 import-only PASS report hash mismatch")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"v2 import-only PASS report is unreadable: {exc}") from exc
    issues = validate_import_only_report_payload(payload)
    if issues:
        raise ValueError(f"v2 import-only PASS report failed semantic validation: {issues}")
    return {
        "path": IMPORT_ONLY_REPORT_RELATIVE,
        "sha256": actual_hash,
        "status": payload["status"],
        "trusted_child_result": payload["trusted_child_result"],
        "validation_issues": [],
        "bound_v2_hashes": dict(EXPECTED_V2_HASHES),
    }


def active_blender_evidence() -> dict[str, Any]:
    """Read exact Blender process state; never terminate or mutate it."""

    command = [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        (
            "$items = @(Get-Process -Name blender -ErrorAction SilentlyContinue | "
            "ForEach-Object { [pscustomobject]@{ pid = [int]$_.Id; "
            "process_name = [string]$_.ProcessName } }); "
            "[Console]::Out.Write(([pscustomobject]@{ processes = @($items) } | "
            "ConvertTo-Json -Compress -Depth 3))"
        ),
    ]
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode != 0:
            return {
                "query_succeeded": False,
                "active": None,
                "matches": [],
                "returncode": completed.returncode,
                "stderr_tail": completed.stderr[-1000:],
                "process_state_changed": False,
            }
        payload = json.loads(completed.stdout)
        rows = payload.get("processes") if isinstance(payload, dict) else None
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            raise ValueError("Blender process query did not return a list")
        matches: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("malformed Blender process row")
            pid = row.get("pid")
            name = str(row.get("process_name") or "")
            if not _plain_int(pid) or pid <= 0 or name.casefold() != "blender":
                raise ValueError("unexpected Blender process row")
            matches.append({"pid": pid, "process_name": name})
        return {
            "query_succeeded": True,
            "active": bool(matches),
            "matches": matches,
            "returncode": completed.returncode,
            "stderr_tail": completed.stderr[-1000:],
            "process_state_changed": False,
        }
    except Exception as exc:
        return {
            "query_succeeded": False,
            "active": None,
            "matches": [],
            "error": f"{type(exc).__name__}: {exc}",
            "process_state_changed": False,
        }


def require_no_active_blender(boundary: str) -> dict[str, Any]:
    evidence = active_blender_evidence()
    evidence["boundary"] = boundary
    if evidence.get("query_succeeded") is not True:
        raise RuntimeError(f"cannot prove Blender state at {boundary}: {evidence}")
    if evidence.get("active") is not False:
        raise RuntimeError(f"active Blender blocks v2 full-GPU acceptance at {boundary}")
    return evidence


def nvidia_memory_accounting(payload: Any) -> dict[str, Any]:
    """Validate one WDDM row while recording, not guessing about, its gap."""

    evidence: dict[str, Any] = {
        "valid": False,
        "unreported_or_reserved_gap_mib": None,
        "maximum_allowed_gap_mib": None,
        "gap_rule": "max_1024_mib_or_10_percent_of_reported_total",
        "gap_interpretation": (
            "reported_total_minus_reported_free_minus_reported_used; "
            "not attributed to a process and not mislabeled as measured VRAM use"
        ),
    }
    if not (
        isinstance(payload, dict)
        and payload.get("returncode") == 0
        and payload.get("stderr") == ""
        and isinstance(payload.get("rows"), list)
        and len(payload["rows"]) == 1
        and isinstance(payload["rows"][0], dict)
    ):
        evidence["reason"] = "query_or_row_shape_invalid"
        return evidence
    row = payload["rows"][0]
    values = (row.get("total_mib"), row.get("free_mib"), row.get("used_mib"))
    identity_valid = bool(
        row.get("name") == "NVIDIA GeForce RTX 5060 Ti"
        and isinstance(row.get("driver_version"), str)
        and bool(re.fullmatch(r"[0-9]+(?:\.[0-9]+)+", row["driver_version"]))
    )
    integers_valid = all(_plain_int(value) and value >= 0 for value in values)
    evidence.update(
        {
            "device_name": row.get("name"),
            "driver_version": row.get("driver_version"),
            "total_mib": row.get("total_mib"),
            "free_mib": row.get("free_mib"),
            "used_mib": row.get("used_mib"),
            "identity_and_driver_valid": identity_valid,
            "nonnegative_integer_fields": integers_valid,
        }
    )
    if not identity_valid or not integers_valid or row["total_mib"] <= 0:
        evidence["reason"] = "identity_driver_or_numeric_field_invalid"
        return evidence
    total = row["total_mib"]
    free = row["free_mib"]
    used = row["used_mib"]
    gap = total - free - used
    maximum = max(1024.0, total * 0.10)
    bounds_valid = bool(
        0 <= free <= total
        and 0 <= used <= total
        and free + used <= total
        and 0 <= gap <= maximum
    )
    evidence.update(
        {
            "unreported_or_reserved_gap_mib": gap,
            "maximum_allowed_gap_mib": round(maximum, 3),
            "free_and_used_within_total": bounds_valid,
            "valid": bounds_valid,
            "reason": "bounded_wddm_accounting_gap" if bounds_valid else "memory_accounting_bounds_failed",
        }
    )
    return evidence


def _single_nvidia_row_valid(payload: Any) -> bool:
    return nvidia_memory_accounting(payload).get("valid") is True


def validate_eager_cuda_payload(
    payload: Any,
    *,
    config: dict[str, Any],
    stderr_text: str = "",
) -> list[str]:
    """Validate the fresh output of the sealed ordinary-eager readiness tool."""

    issues: list[str] = []
    if not isinstance(payload, dict):
        return ["eager_payload_not_object"]
    expected_python = str(project_file(config["python"]).resolve()).casefold()
    python_value = payload.get("python") or {}
    if not (
        isinstance(python_value, dict)
        and python_value.get("version") == "3.11.9"
        and str(python_value.get("executable") or "").casefold() == expected_python
    ):
        issues.append("eager_python_identity_mismatch")
    versions = payload.get("versions") or {}
    if not (
        isinstance(versions, dict)
        and versions.get("torch") == config["torch_version"]
        and versions.get("torchaudio") == config["torchaudio_version"]
        and versions.get("torch_cuda_runtime") == config["cuda_runtime"]
    ):
        issues.append("eager_runtime_versions_mismatch")
    cuda = payload.get("cuda") or {}
    if not (
        isinstance(cuda, dict)
        and cuda.get("available") is True
        and cuda.get("device_name") == config["required_device_name"]
        and cuda.get("device_capability") == config["required_device_capability"]
        and cuda.get("sm_120_compiled") is True
        and isinstance(cuda.get("compiled_architectures"), list)
        and config["required_compiled_architecture"] in cuda["compiled_architectures"]
    ):
        issues.append("eager_cuda_identity_mismatch")
    operation = payload.get("cuda_operation") or {}
    if not (
        isinstance(operation, dict)
        and operation.get("kind") == "float32_cuda_matmul"
        and operation.get("left_shape") == [4096, 4096]
        and operation.get("right_shape") == [4096, 64]
        and operation.get("result_shape") == [4096, 64]
        and operation.get("sample") == [[8192.0, 8192.0], [8192.0, 8192.0]]
        and operation.get("expected_value") == 8192.0
        and operation.get("expected_result") is True
        and operation.get("allocation_measurable") is True
        and operation.get("release_measurable") is True
    ):
        issues.append("eager_matrix_contract_mismatch")
    allocation_names = (
        "allocated_before_bytes",
        "allocated_during_bytes",
        "allocated_after_release_bytes",
        "reserved_before_bytes",
        "reserved_during_bytes",
        "reserved_after_release_bytes",
        "peak_allocated_bytes",
        "peak_reserved_bytes",
        "free_before_bytes",
        "free_during_bytes",
        "free_after_release_bytes",
        "total_before_bytes",
        "total_during_bytes",
        "total_after_bytes",
    )
    if not all(_plain_int(operation.get(key)) and operation[key] >= 0 for key in allocation_names):
        issues.append("eager_allocator_metrics_invalid")
    elif not (
        operation["allocated_during_bytes"] > operation["allocated_before_bytes"]
        and operation["allocated_after_release_bytes"] < operation["allocated_during_bytes"]
        and operation["peak_allocated_bytes"] >= operation["allocated_during_bytes"]
        and operation["reserved_during_bytes"] >= operation["allocated_during_bytes"]
        and operation["peak_reserved_bytes"] >= operation["reserved_during_bytes"]
        and operation["reserved_after_release_bytes"] <= operation["reserved_during_bytes"]
        and operation["total_before_bytes"] == operation["total_during_bytes"]
        == operation["total_after_bytes"]
        and operation["total_before_bytes"] > 0
        and all(
            0 <= operation[key] <= operation["total_before_bytes"]
            for key in ("free_before_bytes", "free_during_bytes", "free_after_release_bytes")
        )
    ):
        issues.append("eager_allocator_inequalities_failed")
    checks = payload.get("checks")
    if not isinstance(checks, dict) or not checks or not all(value is True for value in checks.values()):
        issues.append("eager_checks_not_all_exact_true")
    if payload.get("schema_version") != 1:
        issues.append("eager_schema_mismatch")
    if payload.get("status") != "PASS" or payload.get("issues") != [] or payload.get("errors") != []:
        issues.append("eager_status_or_issue_mismatch")
    if payload.get("rejected_warning_matches") != []:
        issues.append("eager_rejected_warning_matches_present")
    captured = payload.get("captured_warnings")
    if not isinstance(captured, list):
        issues.append("eager_captured_warnings_not_list")
        captured = []
    folded = (stderr_text + "\n" + "\n".join(str(item) for item in captured)).casefold()
    if any(value in folded for value in REJECTED_CUDA_TEXT):
        issues.append("eager_rejected_runtime_text_present")
    before_accounting = nvidia_memory_accounting(payload.get("nvidia_before"))
    after_accounting = nvidia_memory_accounting(payload.get("nvidia_after"))
    if before_accounting.get("valid") is not True:
        issues.append("eager_nvidia_before_invalid")
    if after_accounting.get("valid") is not True:
        issues.append("eager_nvidia_after_invalid")
    if (
        before_accounting.get("device_name") != after_accounting.get("device_name")
        or before_accounting.get("driver_version")
        != after_accounting.get("driver_version")
    ):
        issues.append("eager_nvidia_identity_or_driver_changed")
    if not _number(payload.get("elapsed_seconds")):
        issues.append("eager_elapsed_timing_invalid")
    return sorted(set(issues))


def run_eager_cuda_preflight(config: dict[str, Any], attempt: Path) -> dict[str, Any]:
    """Run the sealed eager-matrix tool as one exact-owned bounded child."""

    tool = (ROOT / READINESS_TOOL_RELATIVE).resolve()
    if not hmac.compare_digest(sha256_file(tool), READINESS_TOOL_SHA256):
        raise RuntimeError("sealed eager CUDA readiness tool hash mismatch")
    output = attempt / "EAGER_CUDA_READINESS.json"
    checksum = output.with_suffix(".sha256")
    environment = restricted_candidate_environment(
        config,
        session_nonce=f"full-gpu-v2-eager-{uuid.uuid4().hex}",
        allow_gpu_model_load=False,
    )
    environment["KIRA_FULL_GPU_V2_EAGER_PREFLIGHT"] = "1"
    command = [
        str(project_file(config["python"])),
        "-B",
        str(tool),
        "--output",
        str(output),
    ]
    started = time.perf_counter()
    process: subprocess.Popen[str] | None = None
    stdout = ""
    stderr = ""
    timed_out = False
    terminate_sent = False
    kill_sent = False
    try:
        process = subprocess.Popen(
            command,
            cwd=str(ROOT),
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            stdout, stderr = process.communicate(timeout=EAGER_PREFLIGHT_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = str(exc.stdout or "")
            stderr = str(exc.stderr or "")
            process.terminate()
            terminate_sent = True
            try:
                tail_out, tail_err = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                kill_sent = True
                tail_out, tail_err = process.communicate(timeout=10)
            stdout += tail_out or ""
            stderr += tail_err or ""
    except Exception:
        if process is not None and process.poll() is None:
            process.terminate()
            terminate_sent = True
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                kill_sent = True
                process.wait(timeout=10)
        raise
    if len(stdout.encode("utf-8", errors="replace")) > MAX_CAPTURE_BYTES:
        raise RuntimeError("eager CUDA stdout exceeded bound")
    if len(stderr.encode("utf-8", errors="replace")) > MAX_CAPTURE_BYTES:
        raise RuntimeError("eager CUDA stderr exceeded bound")
    stdout_path = attempt / "EAGER_CUDA_LAUNCH_STDOUT.log"
    stderr_path = attempt / "EAGER_CUDA_LAUNCH_STDERR.log"
    stdout_hash = _atomic_bytes_exclusive(stdout_path, stdout.encode("utf-8"))
    stderr_hash = _atomic_bytes_exclusive(stderr_path, stderr.encode("utf-8"))
    payload: dict[str, Any] | None = None
    try:
        decoded = json.loads(output.read_text(encoding="utf-8"))
        payload = decoded if isinstance(decoded, dict) else None
    except (OSError, UnicodeError, json.JSONDecodeError):
        payload = None
    issues = validate_eager_cuda_payload(payload, config=config, stderr_text=stderr)
    nvidia_accounting = {
        "before": nvidia_memory_accounting(
            payload.get("nvidia_before") if isinstance(payload, dict) else None
        ),
        "after": nvidia_memory_accounting(
            payload.get("nvidia_after") if isinstance(payload, dict) else None
        ),
    }
    actual_output_hash = sha256_file(output) if output.is_file() else None
    checksum_text = checksum.read_text(encoding="utf-8").strip() if checksum.is_file() else ""
    expected_checksum_text = (
        f"{actual_output_hash}  {output.name}" if actual_output_hash is not None else None
    )
    if checksum_text != expected_checksum_text:
        issues.append("eager_checksum_sidecar_mismatch")
    try:
        launch_summary = json.loads(stdout)
    except json.JSONDecodeError:
        launch_summary = None
    if not (
        isinstance(launch_summary, dict)
        and launch_summary.get("status") == "PASS"
        and Path(str(launch_summary.get("evidence") or "")).resolve() == output.resolve()
        and launch_summary.get("sha256") == actual_output_hash
    ):
        issues.append("eager_launch_summary_mismatch")
    if timed_out:
        issues.append("eager_child_timed_out")
    if process is None or process.returncode != 0:
        issues.append("eager_child_exit_not_zero")
    if terminate_sent or kill_sent:
        issues.append("eager_child_required_forced_cleanup")
    issues = sorted(set(issues))
    return {
        "tool": {"path": READINESS_TOOL_RELATIVE, "sha256": READINESS_TOOL_SHA256},
        "command": command,
        "owned_pid": process.pid if process is not None else None,
        "owned_process_exit_code": process.returncode if process is not None else None,
        "timed_out": timed_out,
        "terminate_sent": terminate_sent,
        "kill_sent": kill_sent,
        "wall_seconds": round(time.perf_counter() - started, 9),
        "stdout": {"path": relative(stdout_path), "sha256": stdout_hash, "bytes": stdout_path.stat().st_size},
        "stderr": {"path": relative(stderr_path), "sha256": stderr_hash, "bytes": stderr_path.stat().st_size},
        "output": _artifact_evidence(output),
        "checksum": _artifact_evidence(checksum),
        "nvidia_memory_accounting": nvidia_accounting,
        "trusted_payload": not issues,
        "payload": payload if not issues else None,
        "untrusted_payload_for_diagnosis": payload if issues else None,
        "validation_issues": issues,
        "passed": not issues,
        "exact_owned_cleanup_only": True,
    }


def client_diagnostic_snapshot(client: PersistentBlackwellVoiceCandidateClient) -> dict[str, Any]:
    return {
        "diagnostic_paths": client.diagnostic_paths,
        "phase_events": client.events,
        "stderr_tail": client.stderr_tail,
    }


def close_exact_client(client: PersistentBlackwellVoiceCandidateClient) -> dict[str, Any]:
    """Close only this client's Popen child and finish its two drain threads."""

    owned_process = client.process
    owned_pid = owned_process.pid if owned_process is not None else None
    response: dict[str, Any] | None = None
    close_error: str | None = None
    try:
        response = client.close()
    except Exception as exc:
        close_error = f"{type(exc).__name__}: {exc}"
    drains: dict[str, Any] = {}
    for label, attribute in (("stdout", "_stdout_thread"), ("stderr", "_stderr_thread")):
        thread = getattr(client, attribute, None)
        if thread is not None:
            thread.join(timeout=CLEANUP_DRAIN_TIMEOUT_SECONDS)
            drains[label] = {"present": True, "alive_after_join": thread.is_alive()}
        else:
            drains[label] = {"present": False, "alive_after_join": None}
    exit_code = owned_process.returncode if owned_process is not None else None
    forced = response.get("owned_process_forced_termination") if isinstance(response, dict) else None
    clean = bool(
        close_error is None
        and isinstance(response, dict)
        and response.get("owned_process_exit_code") == 0
        and response.get("owned_process_forced_termination") is False
        and exit_code == 0
        and all(item.get("alive_after_join") is False for item in drains.values() if item["present"])
        and client.process is None
    )
    return {
        "owned_pid": owned_pid,
        "owned_process_exit_code": exit_code,
        "close_response": response,
        "close_error": close_error,
        "forced_termination": forced,
        "drains": drains,
        "drains_finalized": all(
            item.get("alive_after_join") is False for item in drains.values() if item["present"]
        ),
        "client_process_reference_released": client.process is None,
        "exact_owned_cleanup_only": True,
        "clean_exit": clean,
    }


def truthful_eager_cuda_synthesis_proven(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    proof = payload.get("gpu_proof")
    if not isinstance(proof, dict):
        return False
    required_true = (
        "actual_gpu_execution",
        "model_and_core_components_cuda",
        "cuda_synchronize_before_generation_succeeded",
        "cuda_synchronize_after_generation_succeeded",
        "persistent_model_allocation_present",
        "generation_peak_exceeded_baseline",
        "no_rejected_runtime_warnings",
        "qwen_absence_proven_for_accepted_generation",
        "official_host_return_contract_satisfied",
        "accepted_output_tensors_host_cpu",
    )
    if not all(proof.get(key) is True for key in required_true):
        return False
    if proof.get("accepted_output_tensors_cuda") is not False:
        return False
    before = proof.get("allocated_before_bytes")
    peak = proof.get("peak_allocated_bytes")
    delta = proof.get("generation_peak_delta_bytes")
    if not (
        _plain_int(before)
        and _plain_int(peak)
        and _plain_int(delta)
        and peak > before
        and delta == peak - before
    ):
        return False
    chunks = payload.get("chunk_checks")
    if not isinstance(chunks, list) or not chunks:
        return False
    for chunk in chunks:
        if not isinstance(chunk, dict):
            return False
        accepted_number = chunk.get("accepted_attempt")
        attempts = chunk.get("attempts")
        if not isinstance(attempts, list) or not attempts:
            return False
        accepted = next(
            (
                item
                for item in attempts
                if isinstance(item, dict) and item.get("attempt") == accepted_number
            ),
            None,
        )
        if not (
            isinstance(accepted, dict)
            and accepted.get("passed") is True
            and accepted.get("output_tensor_device_type") == "cpu"
            and accepted.get("output_tensor_returned_to_host") is True
            and accepted.get("official_host_return_contract_satisfied") is True
            and accepted.get("output_tensor_was_cuda") is False
            and accepted.get("rejected_warning_matches") == []
            and qwen_absence_proven(accepted.get("qwen_residency"))
        ):
            return False
    return True


def _resource_evidence_valid(payload: Any) -> bool:
    return bool(
        isinstance(payload, dict)
        and _plain_int(payload.get("sample_count"))
        and payload["sample_count"] > 0
        and _number(payload.get("peak_process_rss_mib"))
        and payload.get("peak_process_rss_mib") > 0
        and _number(payload.get("peak_system_ram_used_mib"))
        and payload.get("peak_system_ram_used_mib") > 0
        and _number(payload.get("peak_total_gpu_used_mib"))
        and payload.get("peak_total_gpu_used_mib") > 0
        and payload.get("gpu_sampling_mode") == "boundary_only_external_nvidia_smi"
        and payload.get("background_external_gpu_polling") is False
        and payload.get("gpu_peak_measurement_scope")
        == "operation_boundary_snapshots_not_continuous_peak"
        and payload.get("sampling_errors") == []
    )


def _wav_and_identity_valid(payload: Any, config: dict[str, Any]) -> bool:
    wav = payload.get("wav_validation") if isinstance(payload, dict) else None
    return bool(
        isinstance(payload, dict)
        and payload.get("generated") is True
        and payload.get("engine") == "chatterbox_tts"
        and payload.get("channel") == "public_spoken_only"
        and payload.get("text_sha256") == APPROVED_PUBLIC_SENTENCE_SHA256
        and payload.get("profile_sha256") == config["approved_profile_sha256"]
        and payload.get("reference_sha256") == config["approved_reference_sha256"]
        and payload.get("device") == "cuda"
        and payload.get("conditioning_reused") is True
        and _exact_false_flags(payload)
        and isinstance(wav, dict)
        and wav.get("passed") is True
        and wav.get("non_silent") is True
        and _number(wav.get("duration_seconds"))
        and wav.get("duration_seconds") > 0
        and isinstance(wav.get("sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", wav["sha256"])
        and truthful_eager_cuda_synthesis_proven(payload)
        and _resource_evidence_valid(payload.get("resources"))
        and _number(payload.get("generation_seconds"))
        and _number(payload.get("operation_seconds"))
        and isinstance(payload.get("phase_timings"), list)
        and bool(payload.get("phase_timings"))
    )


def _diagnostic_evidence(attempt: Path, client_snapshot: dict[str, Any] | None) -> dict[str, Any]:
    configured = (client_snapshot or {}).get("diagnostic_paths") or {}
    result: dict[str, Any] = {}
    for label, filename in (
        ("phase_events", "WORKER_PHASE_EVENTS.jsonl"),
        ("stderr", "WORKER_STDERR_FAULTHANDLER.log"),
    ):
        path = attempt / filename
        evidence = _artifact_evidence(path)
        evidence["configured_path"] = configured.get(label)
        result[label] = evidence
    return result


def performance_summary(report: dict[str, Any]) -> dict[str, Any]:
    """Keep authoritative allocator peaks separate from boundary snapshots."""

    rows: dict[str, Any] = {}
    process_ram: list[float] = []
    system_ram: list[float] = []
    torch_allocated: list[int] = []
    torch_reserved: list[int] = []
    boundary_total_gpu: list[float] = []
    for label, report_key in (
        ("model_load", "load"),
        ("first_wav", "first_synthesis"),
        ("second_warm_wav", "second_synthesis"),
    ):
        payload = report.get(report_key) or {}
        resources = payload.get("resources") or {}
        gpu = payload.get("gpu_proof") or {}
        row = {
            "operation_seconds": payload.get("operation_seconds"),
            "generation_seconds": payload.get("generation_seconds"),
            "parent_transport_seconds": (payload.get("parent_transport_timing") or {}).get(
                "elapsed_seconds"
            ),
            "phase_timings": payload.get("phase_timings"),
            "peak_process_rss_mib": resources.get("peak_process_rss_mib"),
            "peak_system_ram_used_mib": resources.get("peak_system_ram_used_mib"),
            "torch_peak_allocated_bytes": gpu.get("peak_allocated_bytes"),
            "torch_peak_reserved_bytes": gpu.get("peak_reserved_bytes"),
            "boundary_total_gpu_used_mib": resources.get("peak_total_gpu_used_mib"),
            "boundary_total_gpu_measurement_scope": resources.get(
                "gpu_peak_measurement_scope"
            ),
        }
        rows[label] = row
        if _number(row["peak_process_rss_mib"]):
            process_ram.append(float(row["peak_process_rss_mib"]))
        if _number(row["peak_system_ram_used_mib"]):
            system_ram.append(float(row["peak_system_ram_used_mib"]))
        if _plain_int(row["torch_peak_allocated_bytes"]):
            torch_allocated.append(row["torch_peak_allocated_bytes"])
        if _plain_int(row["torch_peak_reserved_bytes"]):
            torch_reserved.append(row["torch_peak_reserved_bytes"])
        if _number(row["boundary_total_gpu_used_mib"]):
            boundary_total_gpu.append(float(row["boundary_total_gpu_used_mib"]))
    return {
        "matrix_preflight_seconds": (report.get("eager_cuda_preflight") or {}).get(
            "wall_seconds"
        ),
        "worker_start_seconds": (
            (report.get("hello") or {}).get("parent_process_start_timing") or {}
        ).get("elapsed_seconds"),
        "operations": rows,
        "max_peak_process_rss_mib": max(process_ram) if process_ram else None,
        "max_peak_system_ram_used_mib": max(system_ram) if system_ram else None,
        "max_authoritative_torch_peak_allocated_bytes": (
            max(torch_allocated) if torch_allocated else None
        ),
        "max_authoritative_torch_peak_reserved_bytes": (
            max(torch_reserved) if torch_reserved else None
        ),
        "max_boundary_total_gpu_used_mib": (
            max(boundary_total_gpu) if boundary_total_gpu else None
        ),
        "boundary_total_gpu_is_continuous_peak": False,
        "authoritative_vram_peak_source": "torch_allocator_per_operation",
        "worker_timing_scope": (
            "fresh_worker_process_and_cold_model_after_eager_matrix_driver_warmup"
        ),
        "total_including_matrix_preflight_seconds": report.get("total_wall_seconds"),
    }


def build_acceptance_checks(report: dict[str, Any], config: dict[str, Any]) -> dict[str, bool]:
    hello = report.get("hello") or {}
    status_before_load = report.get("status_before_load") or {}
    load = report.get("load") or {}
    first = report.get("first_synthesis") or {}
    second = report.get("second_synthesis") or {}
    status_before_unload = report.get("status_before_unload") or {}
    unload = report.get("unload") or {}
    status_after_unload = report.get("status_after_unload") or {}
    shutdown = report.get("worker_shutdown") or {}
    lifecycle = status_before_unload.get("lifecycle") or {}
    unload_measurement = (unload.get("lifecycle") or {}).get("last_unload") or {}
    unload_phases = unload_measurement.get("phase_timings") or []
    load_checks = load.get("runtime_cuda_checks") or {}
    load_gpu = load.get("gpu_proof") or {}
    exact_identity = {
        "profile_sha256": config["approved_profile_sha256"],
        "reference_sha256": config["approved_reference_sha256"],
    }
    qwen_boundaries = report.get("qwen_boundaries") or {}
    response_sequence = (
        hello,
        status_before_load,
        load,
        first,
        second,
        status_before_unload,
        unload,
        status_after_unload,
        (shutdown.get("close_response") or {}),
    )
    protected_before = report.get("protected_before")
    protected_after = report.get("protected_after")
    diagnostics = report.get("diagnostic_evidence") or {}
    performance = report.get("performance_summary") or {}
    checks = {
        "import_only_prerequisite_exact_pass": (
            (report.get("import_only_prerequisite") or {}).get("sha256")
            == IMPORT_ONLY_REPORT_SHA256
        ),
        "operator_bound_exact_harness": report.get("operator_bound_exact_harness") is True,
        "operator_bound_exact_candidate_config": report.get("operator_bound_exact_candidate_config") is True,
        "candidate_inactive_and_unpromoted": (
            config.get("candidate_status") == "inactive_private_candidate_not_production"
            and config.get("production_routing_authorized") is False
            and report.get("promotion_performed") is False
            and report.get("routing_change_performed") is False
        ),
        "approved_sentence_hash_exact": (
            sha256_text(APPROVED_PUBLIC_SENTENCE) == APPROVED_PUBLIC_SENTENCE_SHA256
        ),
        "eager_cuda_preflight": (report.get("eager_cuda_preflight") or {}).get("passed") is True,
        "worker_started_cold_unloaded": (
            hello.get("ready") is True
            and hello.get("model_loaded") is False
            and (status_before_load.get("lifecycle") or {}).get("model_loaded") is False
            and (status_before_load.get("lifecycle") or {}).get("model_load_count") == 0
        ),
        "cold_load_identity_exact": load.get("identity") == exact_identity,
        "cold_load_not_reused": load.get("model_reused") is False,
        "load_cuda_contract": all(
            load_checks.get(key) is True
            for key in (
                "torch_runtime",
                "torchaudio_runtime",
                "cuda_runtime",
                "cuda_available",
                "device",
                "capability",
                "sm_120",
            )
        ),
        "load_gpu_allocation_and_residency": (
            load_gpu.get("actual_gpu_allocation") is True
            and load_gpu.get("persistent_model_allocation_present") is True
            and load_gpu.get("model_and_core_components_cuda") is True
            and load_gpu.get("cuda_synchronize_before_model_load_succeeded") is True
            and load_gpu.get("cuda_synchronize_after_conditioning_succeeded") is True
            and load_gpu.get("no_rejected_runtime_warnings") is True
            and load_gpu.get("rejected_warning_matches") == []
        ),
        "load_resources_and_timings": (
            _resource_evidence_valid(load.get("resources"))
            and _number(load.get("operation_seconds"))
            and isinstance(load.get("phase_timings"), list)
            and bool(load.get("phase_timings"))
        ),
        "first_wav_exact_readable_non_silent_cuda": _wav_and_identity_valid(first, config),
        "second_warm_wav_exact_readable_non_silent_cuda": _wav_and_identity_valid(second, config),
        "loaded_and_conditioned_once_for_two_wavs": (
            lifecycle.get("model_load_count") == 1
            and lifecycle.get("reference_conditioning_count") == 1
            and lifecycle.get("successful_synthesis_count") == 2
            and lifecycle.get("generation_attempt_count") == 2
        ),
        "qwen_absent_at_every_harness_boundary": (
            set(qwen_boundaries) == {"before_eager", "before_load", "before_first", "before_second", "after_unload"}
            and all(qwen_absence_proven(value) for value in qwen_boundaries.values())
        ),
        "qwen_absent_in_parent_and_worker_load": (
            qwen_absence_proven(load.get("parent_qwen_residency_before_load"))
            and qwen_absence_proven(load.get("qwen_residency"))
        ),
        "qwen_absent_in_parent_and_worker_syntheses": (
            qwen_absence_proven(first.get("parent_qwen_residency_before_synthesis"))
            and qwen_absence_proven(second.get("parent_qwen_residency_before_synthesis"))
            and truthful_eager_cuda_synthesis_proven(first)
            and truthful_eager_cuda_synthesis_proven(second)
        ),
        "explicit_unload_and_vram_return": (
            unload.get("unloaded") is True
            and _plain_int(unload_measurement.get("allocated_before_bytes"))
            and unload_measurement.get("allocated_before_bytes") >= 256 * 1024 * 1024
            and _plain_int(unload_measurement.get("allocated_after_bytes"))
            and unload_measurement.get("allocated_after_bytes") < 256 * 1024 * 1024
            and _plain_int(unload_measurement.get("allocated_returned_bytes"))
            and unload_measurement.get("allocated_returned_bytes") >= 256 * 1024 * 1024
            and _plain_int(unload_measurement.get("reserved_before_bytes"))
            and unload_measurement.get("reserved_before_bytes") >= 256 * 1024 * 1024
            and _plain_int(unload_measurement.get("reserved_after_bytes"))
            and unload_measurement.get("reserved_after_bytes") < 256 * 1024 * 1024
            and _plain_int(unload_measurement.get("reserved_returned_bytes"))
            and unload_measurement.get("reserved_returned_bytes") >= 256 * 1024 * 1024
            and any(
                isinstance(item, dict)
                and item.get("phase") == "unload.cuda_empty_cache_and_synchronize"
                and item.get("status") == "passed"
                for item in unload_phases
            )
            and (status_after_unload.get("lifecycle") or {}).get("model_loaded") is False
        ),
        "clean_exact_worker_exit_and_finalized_drains": (
            shutdown.get("clean_exit") is True
            and shutdown.get("exact_owned_cleanup_only") is True
            and shutdown.get("drains_finalized") is True
            and shutdown.get("owned_process_exit_code") == 0
            and shutdown.get("forced_termination") is False
        ),
        "no_playback_generic_sapi_or_fallback": all(
            _exact_false_flags(item) for item in response_sequence
        ),
        "protected_files_unchanged": (
            isinstance(protected_before, dict)
            and protected_before == protected_after
            and protected_before.get("Voice/sidecars/kira_approved_voice_routing.json")
            == PRODUCTION_ROUTING_SHA256
        ),
        "diagnostics_finalized_and_hashed": (
            shutdown.get("drains_finalized") is True
            and all(
                isinstance(item, dict)
                and item.get("present") is True
                and isinstance(item.get("sha256"), str)
                and bool(re.fullmatch(r"[0-9a-f]{64}", item["sha256"]))
                for item in diagnostics.values()
            )
        ),
        "peak_ram_vram_and_phase_timings_recorded": (
            _number(performance.get("max_peak_process_rss_mib"))
            and performance.get("max_peak_process_rss_mib") > 0
            and _number(performance.get("max_peak_system_ram_used_mib"))
            and performance.get("max_peak_system_ram_used_mib") > 0
            and _plain_int(performance.get("max_authoritative_torch_peak_allocated_bytes"))
            and performance.get("max_authoritative_torch_peak_allocated_bytes") > 0
            and _plain_int(performance.get("max_authoritative_torch_peak_reserved_bytes"))
            and performance.get("max_authoritative_torch_peak_reserved_bytes") > 0
            and performance.get("boundary_total_gpu_is_continuous_peak") is False
            and performance.get("authoritative_vram_peak_source")
            == "torch_allocator_per_operation"
            and isinstance(performance.get("operations"), dict)
            and len(performance["operations"]) == 3
        ),
    }
    return checks


def _observed_outcomes(report: dict[str, Any]) -> dict[str, Any]:
    """Use null for anything that failure evidence does not actually prove."""

    responses = [
        report.get(name)
        for name in (
            "hello",
            "status_before_load",
            "load",
            "first_synthesis",
            "second_synthesis",
            "status_before_unload",
            "unload",
            "status_after_unload",
        )
        if isinstance(report.get(name), dict)
    ]
    both_syntheses_observed = all(
        isinstance(report.get(name), dict) for name in ("first_synthesis", "second_synthesis")
    )
    complete_trusted_sequence = bool(
        all(
            isinstance(report.get(name), dict)
            for name in (
                "hello",
                "status_before_load",
                "load",
                "first_synthesis",
                "second_synthesis",
                "status_before_unload",
                "unload",
                "status_after_unload",
            )
        )
        and (report.get("worker_shutdown") or {}).get("clean_exit") is True
    )
    return {
        "audio_generated": (
            True
            if any(item.get("generated") is True for item in responses)
            else False if both_syntheses_observed else None
        ),
        "cuda_execution_proven": (
            True
            if (report.get("eager_cuda_preflight") or {}).get("passed") is True
            or any(truthful_eager_cuda_synthesis_proven(item) for item in responses)
            else None
        ),
        "promotion_performed": False,
        "routing_change_performed": False,
        "playback": False if complete_trusted_sequence and all(item.get("playback") is False for item in responses) else None,
        "generic_voice_used": False if complete_trusted_sequence and all(item.get("generic_voice_used") is False for item in responses) else None,
        "sapi_voice_used": False if complete_trusted_sequence and all(item.get("sapi_voice_used") is False for item in responses) else None,
        "fallback_used": False if complete_trusted_sequence and all(item.get("fallback_used") is False for item in responses) else None,
        "worker_clean_exit": (report.get("worker_shutdown") or {}).get("clean_exit"),
        "protected_files_unchanged": report.get("protected_files_unchanged"),
    }


def describe() -> dict[str, Any]:
    return {
        "harness": HARNESS_ID,
        "candidate_status": "inactive_private_candidate_not_production",
        "live_execution_performed": False,
        "required_flags": [
            "--run-full-gpu-v2",
            "--confirm-no-active-blender",
            "--confirm-inactive-no-promotion",
            "--expected-harness-sha256 <CURRENT_EXACT_SHA256>",
            f"--expected-candidate-config-sha256 {V2_CONFIG_SHA256}",
            f"--expected-import-only-report-sha256 {IMPORT_ONLY_REPORT_SHA256}",
        ],
        "import_only_prerequisite": {
            "path": IMPORT_ONLY_REPORT_RELATIVE,
            "sha256": IMPORT_ONLY_REPORT_SHA256,
        },
        "v2_bindings": dict(EXPECTED_V2_HASHES),
        "approved_public_sentence": APPROVED_PUBLIC_SENTENCE,
        "approved_public_sentence_sha256": APPROVED_PUBLIC_SENTENCE_SHA256,
        "operations_if_explicitly_authorized": [
            "prove Blender absent without stopping it",
            "prove Qwen absent before eager preflight, load, and each synthesis",
            "run one exact-venv eager CUDA matrix preflight without compilation or Triton",
            "start actual package-qualified v2 client and exact owned worker unloaded",
            "cold-load exact eager-CUDA Chatterbox and exact approved Kira reference",
            "generate first and second warm non-playing WAVs from the exact approved sentence",
            "explicitly unload, prove VRAM return, and close only the exact owned worker",
            "finalize diagnostic drains before hashing and verify protected files unchanged",
        ],
        "timing_interpretation": (
            "the matrix preflight warms the CUDA driver; worker/model timings are fresh-process "
            "cold-model and warm-request timings, not machine-cold boot timings"
        ),
        "bounds": {
            "startup_timeout_seconds": STARTUP_TIMEOUT_SECONDS,
            "per_request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
            "eager_preflight_timeout_seconds": EAGER_PREFLIGHT_TIMEOUT_SECONDS,
            "cleanup_drain_timeout_seconds_per_thread": CLEANUP_DRAIN_TIMEOUT_SECONDS,
            "maximum_live_phases": MAX_LIVE_PHASES,
            "synthesis_request_count": 2,
            "automatic_retry_count": 0,
        },
        "torch_compile_authorized": False,
        "triton_authorized": False,
        "ollama_load_or_unload_authorized": False,
        "playback_authorized": False,
        "fallback_authorized": False,
        "promotion_authorized": False,
        "routing_change_authorized": False,
        "candidate_remains_inactive": True,
        "owner_heard_acceptance": False,
        "promotion_eligible": False,
        "revision": "revision01_wddm_gap_validator_only",
        "nvidia_memory_gap_rule": (
            "free and used must each be within total; free+used must not exceed total; "
            "unreported_or_reserved_gap_mib must be no greater than max(1024 MiB, 10% total)"
        ),
    }


def static_self_check() -> dict[str, Any]:
    before_attempts = _attempt_names()
    torch_before = "torch" in sys.modules
    source = Path(__file__).read_text(encoding="utf-8")
    ast.parse(source)
    config = load_candidate_config(CONFIG_PATH)
    sealed = verify_candidate_config(config)
    prerequisite = verify_import_only_prerequisite()
    readiness_tool = ROOT / READINESS_TOOL_RELATIVE
    readiness_source = readiness_tool.read_text(encoding="utf-8")
    actual = {
        "config": sha256_file(CONFIG_PATH),
        "contract": sha256_file(project_file(config["contract"])),
        "client": sha256_file(project_file(config["client"])),
        "worker": sha256_file(project_file(config["worker"])),
    }
    checks = {
        "v2_hashes_exact": actual == EXPECTED_V2_HASHES,
        "sealed_hashes_exact": (
            sealed.get("candidate_contract") == V2_CONTRACT_SHA256
            and sealed.get("candidate_client") == V2_CLIENT_SHA256
            and sealed.get("candidate_worker") == V2_WORKER_SHA256
            and sealed.get("production_routing_manifest") == PRODUCTION_ROUTING_SHA256
        ),
        "import_only_prerequisite_exact": prerequisite["sha256"] == IMPORT_ONLY_REPORT_SHA256,
        "approved_sentence_exact": sha256_text(APPROVED_PUBLIC_SENTENCE) == APPROVED_PUBLIC_SENTENCE_SHA256,
        "candidate_inactive": (
            config.get("candidate_status") == "inactive_private_candidate_not_production"
            and config.get("production_routing_authorized") is False
        ),
        "package_qualified_v2_client": (
            PersistentBlackwellVoiceCandidateClient.__module__
            == "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v2.candidate_client"
        ),
        "no_compile_or_triton_path": (
            "torch" + ".compile" not in readiness_source
            and "import " + "triton" not in readiness_source
        ),
        "readiness_tool_hash_exact": sha256_file(readiness_tool) == READINESS_TOOL_SHA256,
        "no_live_attempt_created": before_attempts == _attempt_names(),
        "torch_host_import_state_unchanged": ("torch" in sys.modules) == torch_before,
    }
    return {
        "harness": HARNESS_ID,
        "passed": all(checks.values()),
        "checks": checks,
        "live_execution_performed": False,
        "torch_imported_before": torch_before,
        "torch_imported_after": "torch" in sys.modules,
        "v2_bindings": actual,
        "import_only_prerequisite": prerequisite,
        "attempt_directories_before": before_attempts,
        "attempt_directories_after": _attempt_names(),
    }


def _validate_live_bindings(
    *,
    expected_harness_sha256: str,
    expected_candidate_config_sha256: str,
    expected_import_only_report_sha256: str,
) -> dict[str, Any]:
    values = {
        "harness": str(expected_harness_sha256 or "").strip().casefold(),
        "config": str(expected_candidate_config_sha256 or "").strip().casefold(),
        "import_only": str(expected_import_only_report_sha256 or "").strip().casefold(),
    }
    if not all(re.fullmatch(r"[0-9a-f]{64}", value) for value in values.values()):
        raise ValueError("all three exact SHA-256 operator bindings are required")
    actual_harness = sha256_file(Path(__file__).resolve())
    actual_config = sha256_file(CONFIG_PATH)
    actual_import = sha256_file(ROOT / IMPORT_ONLY_REPORT_RELATIVE)
    expected_constants = {
        "config": V2_CONFIG_SHA256,
        "import_only": IMPORT_ONLY_REPORT_SHA256,
    }
    if not hmac.compare_digest(values["harness"], actual_harness):
        raise ValueError("operator-bound harness SHA-256 does not match this file")
    if not hmac.compare_digest(values["config"], actual_config):
        raise ValueError("operator-bound candidate config SHA-256 does not match the file")
    if not hmac.compare_digest(values["config"], expected_constants["config"]):
        raise ValueError("candidate config is not the reviewed v2 config")
    if not hmac.compare_digest(values["import_only"], actual_import):
        raise ValueError("operator-bound import-only report SHA-256 does not match the file")
    if not hmac.compare_digest(values["import_only"], expected_constants["import_only"]):
        raise ValueError("import-only report is not the reviewed PASS report")
    return {
        "harness_sha256": actual_harness,
        "candidate_config_sha256": actual_config,
        "import_only_report_sha256": actual_import,
    }


def run_acceptance(
    *,
    expected_harness_sha256: str,
    expected_candidate_config_sha256: str,
    expected_import_only_report_sha256: str,
) -> tuple[Path, dict[str, Any]]:
    bindings = _validate_live_bindings(
        expected_harness_sha256=expected_harness_sha256,
        expected_candidate_config_sha256=expected_candidate_config_sha256,
        expected_import_only_report_sha256=expected_import_only_report_sha256,
    )
    prerequisite = verify_import_only_prerequisite()
    config = load_candidate_config(CONFIG_PATH)
    sealed = verify_candidate_config(config)
    initial_blender = require_no_active_blender("before_attempt_allocation")
    attempt = allocate_attempt_directory()
    final_path = attempt / "FINAL_REPORT.json"
    started_perf = time.perf_counter()
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "persistent_blackwell_voice_candidate_v2_full_gpu_acceptance",
        "harness": HARNESS_ID,
        "started_at": utc_now(),
        "candidate_id": config["candidate_id"],
        "candidate_status": config["candidate_status"],
        "import_only_prerequisite": prerequisite,
        "operator_bindings": bindings,
        "operator_bound_exact_harness": True,
        "operator_bound_exact_candidate_config": True,
        "sealed_artifact_hashes": sealed,
        "approved_public_sentence": APPROVED_PUBLIC_SENTENCE,
        "approved_public_sentence_sha256": APPROVED_PUBLIC_SENTENCE_SHA256,
        "promotion_performed": False,
        "routing_change_performed": False,
        "playback_performed": False,
        "candidate_remains_inactive": True,
        "blender_boundaries": [initial_blender],
        "qwen_boundaries": {},
        "protected_before": file_hashes(PROTECTED_PATHS),
        "protected_after": None,
        "protected_files_unchanged": None,
        "engineering_pass": False,
        "status": "running",
        "checks": None,
        "observed_outcomes": {
            "audio_generated": None,
            "cuda_execution_proven": None,
            "promotion_performed": False,
            "routing_change_performed": False,
            "playback": None,
            "generic_voice_used": None,
            "sapi_voice_used": None,
            "fallback_used": None,
            "worker_clean_exit": None,
            "protected_files_unchanged": None,
        },
        "bounds": describe()["bounds"],
        "final_report_path": relative(final_path),
    }
    start_marker = {
        "schema_version": 1,
        "artifact_kind": "persistent_blackwell_voice_candidate_v2_full_gpu_attempt_started",
        "started_at": report["started_at"],
        "candidate_id": config["candidate_id"],
        "candidate_status": config["candidate_status"],
        "harness_sha256": bindings["harness_sha256"],
        "candidate_config_sha256": bindings["candidate_config_sha256"],
        "import_only_report_sha256": bindings["import_only_report_sha256"],
        "promotion_authorized": False,
        "routing_change_authorized": False,
        "playback_authorized": False,
    }
    start_path = attempt / "ATTEMPT_STARTED.json"
    report["attempt_started"] = {
        "path": relative(start_path),
        "sha256": atomic_json_exclusive(start_path, start_marker),
    }
    client: PersistentBlackwellVoiceCandidateClient | None = None
    last_client_snapshot: dict[str, Any] | None = None
    try:
        report["qwen_boundaries"]["before_eager"] = qwen_residency_evidence(config)
        if not qwen_absence_proven(report["qwen_boundaries"]["before_eager"]):
            raise RuntimeError("Qwen absence was not proven before eager CUDA preflight")
        report["blender_boundaries"].append(require_no_active_blender("before_eager_cuda"))
        report["eager_cuda_preflight"] = run_eager_cuda_preflight(config, attempt)
        if report["eager_cuda_preflight"].get("passed") is not True:
            raise RuntimeError(
                f"eager CUDA preflight failed: {report['eager_cuda_preflight'].get('validation_issues')}"
            )

        report["blender_boundaries"].append(require_no_active_blender("before_worker_start"))
        client = PersistentBlackwellVoiceCandidateClient(
            allow_gpu_model_load=True,
            startup_timeout_seconds=STARTUP_TIMEOUT_SECONDS,
            request_timeout_seconds=REQUEST_TIMEOUT_SECONDS,
            diagnostic_directory=attempt,
        )
        report["diagnostic_contract"] = dict(config["diagnostics"])
        report["diagnostic_paths"] = client.diagnostic_paths
        report["hello"] = client.start()
        report["status_before_load"] = client.status()

        report["qwen_boundaries"]["before_load"] = qwen_residency_evidence(config)
        if not qwen_absence_proven(report["qwen_boundaries"]["before_load"]):
            raise RuntimeError("Qwen absence was not proven immediately before cold model load")
        report["blender_boundaries"].append(require_no_active_blender("before_cold_model_load"))
        report["load"] = client.load()
        if report["load"].get("ready") is not True:
            raise RuntimeError(f"persistent v2 cold load failed: {report['load']}")

        output_one = attempt / "kira_v2_cold_first_request.wav"
        report["qwen_boundaries"]["before_first"] = qwen_residency_evidence(config)
        if not qwen_absence_proven(report["qwen_boundaries"]["before_first"]):
            raise RuntimeError("Qwen absence was not proven immediately before first synthesis")
        report["blender_boundaries"].append(require_no_active_blender("before_first_synthesis"))
        report["first_synthesis"] = client.synthesize(
            text=APPROVED_PUBLIC_SENTENCE,
            output_relative=relative(output_one),
        )
        if report["first_synthesis"].get("generated") is not True:
            raise RuntimeError(f"persistent v2 first synthesis failed: {report['first_synthesis']}")

        output_two = attempt / "kira_v2_warm_second_request.wav"
        report["qwen_boundaries"]["before_second"] = qwen_residency_evidence(config)
        if not qwen_absence_proven(report["qwen_boundaries"]["before_second"]):
            raise RuntimeError("Qwen absence was not proven immediately before second synthesis")
        report["blender_boundaries"].append(require_no_active_blender("before_second_synthesis"))
        report["second_synthesis"] = client.synthesize(
            text=APPROVED_PUBLIC_SENTENCE,
            output_relative=relative(output_two),
        )
        if report["second_synthesis"].get("generated") is not True:
            raise RuntimeError(f"persistent v2 second synthesis failed: {report['second_synthesis']}")

        report["status_before_unload"] = client.status()
        report["unload"] = client.unload()
        report["status_after_unload"] = client.status()
        if report["unload"].get("unloaded") is not True:
            raise RuntimeError("persistent v2 explicit unload failed")
        if (report["status_after_unload"].get("lifecycle") or {}).get("model_loaded") is not False:
            raise RuntimeError("persistent v2 model remained loaded after explicit unload")

        last_client_snapshot = client_diagnostic_snapshot(client)
        report["diagnostics_before_shutdown"] = last_client_snapshot
        report["worker_shutdown"] = close_exact_client(client)
        last_client_snapshot = client_diagnostic_snapshot(client)
        report["diagnostics_after_shutdown"] = last_client_snapshot
        client = None
        if report["worker_shutdown"].get("clean_exit") is not True:
            raise RuntimeError("persistent v2 worker did not exit cleanly")

        report["qwen_boundaries"]["after_unload"] = qwen_residency_evidence(config)
        if not qwen_absence_proven(report["qwen_boundaries"]["after_unload"]):
            raise RuntimeError("Qwen absence was not proven after voice unload")
        report["blender_boundaries"].append(require_no_active_blender("after_worker_exit"))
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
        report["traceback"] = traceback.format_exc()[-20000:]
        report["status"] = "failed_preserved_inactive"
    finally:
        if client is not None:
            try:
                last_client_snapshot = client_diagnostic_snapshot(client)
                report["diagnostics_before_failure_cleanup"] = last_client_snapshot
                report["worker_shutdown"] = close_exact_client(client)
                last_client_snapshot = client_diagnostic_snapshot(client)
                report["diagnostics_after_failure_cleanup"] = last_client_snapshot
            except Exception as cleanup_exc:
                report["cleanup_error"] = f"{type(cleanup_exc).__name__}: {cleanup_exc}"
        report["diagnostic_evidence"] = _diagnostic_evidence(attempt, last_client_snapshot)
        report["protected_after"] = file_hashes(PROTECTED_PATHS)
        report["protected_files_unchanged"] = (
            report["protected_before"] == report["protected_after"]
        )
        report["finished_at"] = utc_now()
        report["total_wall_seconds"] = round(time.perf_counter() - started_perf, 9)
        report["performance_summary"] = performance_summary(report)
        if report.get("error") is None:
            try:
                report["checks"] = build_acceptance_checks(report, config)
                report["engineering_pass"] = all(report["checks"].values())
                report["status"] = (
                    "engineering_pass_pending_owner_heard_acceptance"
                    if report["engineering_pass"]
                    else "engineering_failed_preserved_inactive"
                )
            except Exception as validation_exc:
                report["checks"] = None
                report["engineering_pass"] = False
                report["validation_error"] = (
                    f"{type(validation_exc).__name__}: {validation_exc}"
                )
                report["validation_traceback"] = traceback.format_exc()[-12000:]
                report["status"] = "engineering_validation_failed_preserved_inactive"
        if report["protected_files_unchanged"] is not True:
            report["engineering_pass"] = False
            report["status"] = "failed_protected_integrity_changed"
        report["observed_outcomes"] = _observed_outcomes(report)
        report["playback_performed"] = False
        report["promotion_performed"] = False
        report["routing_change_performed"] = False
        report["owner_heard_acceptance"] = False
        report["promotion_eligible"] = False
        atomic_json_exclusive(final_path, report)
    return final_path, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--static-self-check", action="store_true")
    parser.add_argument("--run-full-gpu-v2", action="store_true")
    parser.add_argument("--confirm-no-active-blender", action="store_true")
    parser.add_argument("--confirm-inactive-no-promotion", action="store_true")
    parser.add_argument("--expected-harness-sha256", default="")
    parser.add_argument("--expected-candidate-config-sha256", default="")
    parser.add_argument("--expected-import-only-report-sha256", default="")
    args = parser.parse_args()
    if args.describe:
        print(json.dumps(describe(), ensure_ascii=False, indent=2))
        return 0
    if args.static_self_check:
        result = static_self_check()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 2
    required_hashes = (
        args.expected_harness_sha256,
        args.expected_candidate_config_sha256,
        args.expected_import_only_report_sha256,
    )
    if not (
        args.run_full_gpu_v2
        and args.confirm_no_active_blender
        and args.confirm_inactive_no_promotion
        and all(re.fullmatch(r"[0-9a-fA-F]{64}", str(value or "")) for value in required_hashes)
    ):
        print(
            json.dumps(
                {
                    **describe(),
                    "ready": False,
                    "reason": "all_explicit_live_flags_and_three_exact_hash_bindings_required",
                    "attempt_created": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    try:
        evidence_path, report = run_acceptance(
            expected_harness_sha256=args.expected_harness_sha256,
            expected_candidate_config_sha256=args.expected_candidate_config_sha256,
            expected_import_only_report_sha256=args.expected_import_only_report_sha256,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "passed": False,
                    "status": "rejected_before_attempt_or_unpreserved_controller_failure",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "promotion_performed": False,
                    "routing_change_performed": False,
                    "playback_performed": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    digest = sha256_file(evidence_path)
    print(
        json.dumps(
            {
                "passed": report.get("engineering_pass") is True,
                "status": report.get("status"),
                "evidence_path": relative(evidence_path),
                "evidence_sha256": digest,
                "promotion_performed": False,
                "routing_change_performed": False,
                "playback_performed": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report.get("engineering_pass") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
