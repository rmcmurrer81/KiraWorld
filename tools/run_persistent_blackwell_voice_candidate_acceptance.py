#!/usr/bin/env python3
"""Later, explicitly authorized GPU acceptance for the inactive persistent voice.

This harness never promotes the candidate and never plays the generated WAVs.
Without both command-line confirmations it performs no worker/model operation.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request as urllib_request


ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_persistent_candidate"
if str(SIDECAR) not in sys.path:
    sys.path.insert(0, str(SIDECAR))

from candidate_client import PersistentBlackwellVoiceCandidateClient  # noqa: E402
from candidate_contract import (  # noqa: E402
    CONFIG_PATH,
    load_candidate_config,
    project_file,
    qwen_residency_evidence,
    sha256_file,
    sha256_text,
    verify_candidate_config,
)


ACCEPTANCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
)
APPROVED_PUBLIC_SENTENCE = "I don't see anything and I don't hear anything."
PROTECTED_PATHS = (
    "tools/run_persistent_blackwell_voice_candidate_acceptance.py",
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
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_hashes(paths: tuple[str, ...]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in paths:
        try:
            path = project_file(relative)
            hashes[relative] = sha256_file(path) if path.is_file() else "MISSING"
        except Exception as exc:
            hashes[relative] = f"ERROR:{type(exc).__name__}:{exc}"
    return hashes


def cache_size_bytes(root: Path) -> int:
    if not root.exists():
        return 0
    total = 0
    for path in root.rglob("*"):
        try:
            if path.is_file():
                total += path.stat().st_size
        except OSError:
            continue
    return total


def ollama_residency_evidence(config: dict[str, Any], timeout_seconds: float = 2.0) -> dict[str, Any]:
    """Read local Ollama residency without loading or unloading any model."""

    endpoint = str(config.get("qwen_ps_endpoint") or "")
    try:
        request = urllib_request.Request(endpoint, headers={"Accept": "application/json"})
        with urllib_request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        models = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(models, list):
            raise ValueError("Ollama /api/ps did not return a models list")
        rows = []
        for item in models:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "name": str(item.get("name") or ""),
                    "model": str(item.get("model") or ""),
                    "digest": str(item.get("digest") or "").casefold(),
                    "size_vram": item.get("size_vram"),
                }
            )
        return {
            "query_succeeded": True,
            "all_models_absent_proven": not rows,
            "resident_models": rows,
            "endpoint": endpoint,
            "model_state_changed": False,
        }
    except Exception as exc:
        return {
            "query_succeeded": False,
            "all_models_absent_proven": False,
            "resident_models": [],
            "endpoint": endpoint,
            "reason": "ollama_residency_query_failed_gpu_blocked",
            "error": f"{type(exc).__name__}: {exc}",
            "model_state_changed": False,
        }


def blender_process_evidence() -> dict[str, Any]:
    """Read process state only; never stop Blender."""

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
                "probe": "powershell_get_process_name_blender",
                "returncode": completed.returncode,
                "stderr": completed.stderr.strip()[-1000:],
                "process_state_changed": False,
            }
        try:
            payload = json.loads(completed.stdout.strip())
            if not isinstance(payload, dict):
                raise ValueError("PowerShell Blender query did not return an object")
            raw_matches = payload.get("processes")
            if isinstance(raw_matches, dict):
                raw_matches = [raw_matches]
            if not isinstance(raw_matches, list):
                raise ValueError("PowerShell Blender query did not return a process list")
            matches: list[dict[str, Any]] = []
            for item in raw_matches:
                if not isinstance(item, dict):
                    raise ValueError("PowerShell Blender query returned a malformed process row")
                process_name = str(item.get("process_name") or "").strip()
                pid = item.get("pid")
                if process_name.casefold() != "blender" or isinstance(pid, bool):
                    raise ValueError("PowerShell Blender query returned an unexpected process row")
                pid = int(pid)
                if pid <= 0:
                    raise ValueError("PowerShell Blender query returned an invalid PID")
                matches.append({"pid": pid, "process_name": process_name})
        except Exception as parse_exc:
            return {
                "query_succeeded": False,
                "active": None,
                "matches": [],
                "probe": "powershell_get_process_name_blender",
                "returncode": completed.returncode,
                "stderr": completed.stderr.strip()[-1000:],
                "parse_error": f"{type(parse_exc).__name__}: {parse_exc}",
                "stdout_tail": completed.stdout.strip()[-1000:],
                "process_state_changed": False,
            }
        return {
            "query_succeeded": True,
            "active": bool(matches),
            "matches": matches,
            "probe": "powershell_get_process_name_blender",
            "returncode": completed.returncode,
            "stderr": completed.stderr.strip()[-1000:],
            "process_state_changed": False,
        }
    except Exception as exc:
        return {
            "query_succeeded": False,
            "active": None,
            "matches": [],
            "probe": "powershell_get_process_name_blender",
            "error": f"{type(exc).__name__}: {exc}",
            "process_state_changed": False,
        }


def require_no_active_blender(boundary: str) -> dict[str, Any]:
    evidence = blender_process_evidence()
    evidence["boundary"] = boundary
    if evidence.get("query_succeeded") is not True:
        raise RuntimeError(f"cannot prove Blender state at {boundary}: {evidence}")
    if evidence.get("active") is not False:
        raise RuntimeError(f"active Blender blocks persistent voice GPU acceptance at {boundary}")
    return evidence


def allocate_attempt_directory() -> Path:
    ACCEPTANCE_ROOT.mkdir(parents=True, exist_ok=True)
    for index in range(1, 1000):
        candidate = ACCEPTANCE_ROOT / f"attempt_{index:02d}"
        try:
            candidate.mkdir(exist_ok=False)
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError("no append-only persistent candidate acceptance slot remains")


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def client_diagnostic_snapshot(
    client: PersistentBlackwellVoiceCandidateClient,
) -> dict[str, Any]:
    """Snapshot already-received progress without issuing another worker request."""

    return {
        "diagnostic_paths": client.diagnostic_paths,
        "phase_events": client.events,
        "stderr_tail": client.stderr_tail,
    }


def write_json_exclusive(path: Path, payload: dict[str, Any]) -> str:
    """Create one append-only JSON artifact and return its exact hash."""

    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
    return sha256_file(path)


def truthful_eager_cuda_synthesis_proven(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    proof = payload.get("gpu_proof")
    proof = proof if isinstance(proof, dict) else {}
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
    baseline = proof.get("allocated_before_bytes")
    peak = proof.get("peak_allocated_bytes")
    delta = proof.get("generation_peak_delta_bytes")
    if not (
        isinstance(baseline, int)
        and isinstance(peak, int)
        and isinstance(delta, int)
        and peak > baseline
        and delta == peak - baseline
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
                attempt
                for attempt in attempts
                if isinstance(attempt, dict) and attempt.get("attempt") == accepted_number
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
            and not accepted.get("rejected_warning_matches")
        ):
            return False
    return True


def describe() -> dict[str, Any]:
    return {
        "harness": "persistent_blackwell_voice_candidate_acceptance_v1",
        "candidate_status": "inactive_private_candidate_not_production",
        "required_flags": [
            "--run-gpu",
            "--confirm-no-active-blender",
            "--expected-candidate-config-sha256 <CURRENT_EXACT_SHA256>",
        ],
        "approved_public_sentence": APPROVED_PUBLIC_SENTENCE,
        "operations": [
            "prove Blender absent without stopping it",
            "prove every Ollama model absent without unloading any model",
            "prove Qwen absent without unloading any model",
            "start exact candidate worker unloaded",
            "load exact eager-CUDA Chatterbox once",
            "prepare exact approved Kira reference once",
            "generate two separately bound non-playing WAVs with truthful CPU host returns",
            "explicitly unload and measure returned allocation",
            "close exact owned worker",
            "verify protected production files unchanged",
        ],
        "promotion_performed": False,
        "playback_performed": False,
        "fallback_inside_candidate": None,
        "production_fallback_retained": "sealed_cpu_chatterbox_only",
        "load_request_timeout_seconds": 900,
        "minimum_recommended_outer_timeout_seconds": 1100,
        "append_only_diagnostics": [
            "WORKER_PHASE_EVENTS.jsonl",
            "WORKER_STDERR_FAULTHANDLER.log",
        ],
    }


def run_acceptance(*, expected_candidate_config_sha256: str) -> tuple[Path, dict[str, Any]]:
    expected_config_hash = str(expected_candidate_config_sha256 or "").strip().casefold()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_config_hash):
        raise ValueError("an exact expected candidate-config SHA-256 is required")
    config = load_candidate_config(CONFIG_PATH)
    sealed_artifacts = verify_candidate_config(config)
    actual_config_hash = sha256_file(CONFIG_PATH)
    if not hmac.compare_digest(actual_config_hash, expected_config_hash):
        raise ValueError("candidate config does not match the operator-bound expected SHA-256")
    attempt = allocate_attempt_directory()
    evidence_path = attempt / "PERSISTENT_BLACKWELL_ACCEPTANCE.json"
    cache_root = project_file(config["runtime_cache_root"])
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "persistent_blackwell_voice_candidate_acceptance",
        "started_at": utc_now(),
        "candidate_id": config["candidate_id"],
        "candidate_status": config["candidate_status"],
        "production_routing_authorized": False,
        "promotion_performed": False,
        "playback_performed": False,
        "generic_voice_used": False,
        "sapi_voice_used": False,
        "fallback_used": False,
        "approved_public_sentence": APPROVED_PUBLIC_SENTENCE,
        "approved_public_sentence_sha256": sha256_text(APPROVED_PUBLIC_SENTENCE),
        "candidate_config_sha256": actual_config_hash,
        "operator_expected_candidate_config_sha256": expected_config_hash,
        "acceptance_harness_sha256": sha256_file(Path(__file__).resolve()),
        "sealed_artifact_hashes": sealed_artifacts,
        "protected_before": file_hashes(PROTECTED_PATHS),
        "cache_size_before_bytes": cache_size_bytes(cache_root),
        "boundaries": [],
        "passed": False,
    }
    start_marker_path = attempt / "ATTEMPT_STARTED.json"
    start_marker = {
        "schema_version": 1,
        "artifact_kind": "persistent_blackwell_voice_candidate_attempt_started",
        "started_at": report["started_at"],
        "candidate_id": config["candidate_id"],
        "candidate_status": config["candidate_status"],
        "production_routing_authorized": False,
        "candidate_config_sha256": actual_config_hash,
        "operator_expected_candidate_config_sha256": expected_config_hash,
        "acceptance_harness_sha256": report["acceptance_harness_sha256"],
        "playback_performed": False,
        "fallback_used": False,
    }
    report["attempt_started_marker"] = {
        "path": relative(start_marker_path),
        "sha256": write_json_exclusive(start_marker_path, start_marker),
    }
    client: PersistentBlackwellVoiceCandidateClient | None = None
    try:
        ollama_before = ollama_residency_evidence(config)
        report["ollama_before"] = ollama_before
        if ollama_before.get("all_models_absent_proven") is not True:
            raise RuntimeError("all Ollama models were not proven absent before candidate acceptance")
        report["boundaries"].append(require_no_active_blender("before_qwen_check"))
        qwen_before = qwen_residency_evidence(config)
        report["qwen_before"] = qwen_before
        if qwen_before.get("qwen_absent_proven") is not True:
            raise RuntimeError("Qwen absence was not proven before candidate acceptance")
        report["boundaries"].append(require_no_active_blender("before_worker_start"))
        client = PersistentBlackwellVoiceCandidateClient(
            allow_gpu_model_load=True,
            startup_timeout_seconds=60,
            request_timeout_seconds=900,
            diagnostic_directory=attempt,
        )
        report["diagnostic_contract"] = dict(config["diagnostics"])
        report["diagnostic_paths"] = client.diagnostic_paths
        report["hello"] = client.start()
        report["status_before_load"] = client.status()
        report["boundaries"].append(require_no_active_blender("before_model_load"))
        report["load"] = client.load()
        if report["load"].get("ready") is not True:
            raise RuntimeError(f"persistent candidate load failed: {report['load']}")

        output_one = attempt / "kira_persistent_cold_first_request.wav"
        report["boundaries"].append(require_no_active_blender("before_first_synthesis"))
        first = client.synthesize(
            text=APPROVED_PUBLIC_SENTENCE,
            output_relative=relative(output_one),
        )
        report["first_synthesis"] = first
        if first.get("generated") is not True:
            raise RuntimeError(f"persistent candidate first synthesis failed: {first}")

        output_two = attempt / "kira_persistent_warm_second_request.wav"
        report["boundaries"].append(require_no_active_blender("before_second_synthesis"))
        second = client.synthesize(
            text=APPROVED_PUBLIC_SENTENCE,
            output_relative=relative(output_two),
        )
        report["second_synthesis"] = second
        if second.get("generated") is not True:
            raise RuntimeError(f"persistent candidate second synthesis failed: {second}")
        report["status_before_unload"] = client.status()
        report["unload"] = client.unload()
        report["status_after_unload"] = client.status()
        if report["unload"].get("unloaded") is not True:
            raise RuntimeError("persistent candidate explicit unload failed")
        if (report["status_after_unload"].get("lifecycle") or {}).get("model_loaded") is not False:
            raise RuntimeError("persistent candidate model remained loaded after explicit unload")
        report["diagnostics_before_successful_shutdown"] = client_diagnostic_snapshot(client)
        report["shutdown"] = client.close()
        report["diagnostics_after_successful_shutdown"] = client_diagnostic_snapshot(client)
        client = None
        report["worker_exit_clean"] = (
            report["shutdown"] is not None
            and report["shutdown"].get("owned_process_exit_code") == 0
            and report["shutdown"].get("owned_process_forced_termination") is False
        )
        report["qwen_after"] = qwen_residency_evidence(config)
        if report["qwen_after"].get("qwen_absent_proven") is not True:
            raise RuntimeError("Qwen absence was not proven after candidate acceptance")
        report["ollama_after"] = ollama_residency_evidence(config)
        if report["ollama_after"].get("all_models_absent_proven") is not True:
            raise RuntimeError("an Ollama model became resident during candidate acceptance")

        lifecycle = report["status_before_unload"].get("lifecycle") or {}
        unload_lifecycle = report["unload"].get("lifecycle") or {}
        unload_measurement = unload_lifecycle.get("last_unload") or {}
        exact_text_hash = sha256_text(APPROVED_PUBLIC_SENTENCE)
        exact_identity = {
            "profile_sha256": config["approved_profile_sha256"],
            "reference_sha256": config["approved_reference_sha256"],
        }
        exact_syntheses = all(
            item.get("generated") is True
            and item.get("engine") == "chatterbox_tts"
            and item.get("channel") == "public_spoken_only"
            and item.get("text_sha256") == exact_text_hash
            and item.get("profile_sha256") == exact_identity["profile_sha256"]
            and item.get("reference_sha256") == exact_identity["reference_sha256"]
            and item.get("device") == "cuda"
            and item.get("conditioning_reused") is True
            and item.get("generic_voice_used") is False
            and item.get("sapi_voice_used") is False
            and item.get("fallback_used") is False
            and item.get("playback") is False
            and (item.get("wav_validation") or {}).get("passed") is True
            and bool((item.get("wav_validation") or {}).get("sha256"))
            and truthful_eager_cuda_synthesis_proven(item)
            for item in (first, second)
        )
        load_gpu_proof = report["load"].get("gpu_proof") or {}
        checks = {
            "operator_bound_exact_candidate_config": hmac.compare_digest(
                actual_config_hash, expected_config_hash
            ),
            "candidate_remained_inactive": config["production_routing_authorized"] is False,
            "worker_started_unloaded": report["hello"].get("model_loaded") is False,
            "load_identity_exact": report["load"].get("identity") == exact_identity,
            "load_cuda_contract": all(
                (report["load"].get("runtime_cuda_checks") or {}).get(key) is True
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
            "load_gpu_allocation": (report["load"].get("gpu_proof") or {}).get(
                "actual_gpu_allocation"
            )
            is True,
            "load_model_and_core_components_cuda": load_gpu_proof.get(
                "model_and_core_components_cuda"
            )
            is True,
            "load_cuda_synchronization": (
                load_gpu_proof.get("cuda_synchronize_before_model_load_succeeded") is True
                and load_gpu_proof.get("cuda_synchronize_after_conditioning_succeeded") is True
            ),
            "load_no_rejected_runtime_warning": load_gpu_proof.get(
                "no_rejected_runtime_warnings"
            )
            is True,
            "model_loaded_once": lifecycle.get("model_load_count") == 1,
            "reference_conditioned_once": lifecycle.get("reference_conditioning_count") == 1,
            "two_wavs_generated": lifecycle.get("successful_synthesis_count") == 2,
            "two_attempts_without_false_host_return_retries": (
                lifecycle.get("generation_attempt_count") == 2
            ),
            "first_conditioning_reused": first.get("conditioning_reused") is True,
            "second_conditioning_reused": second.get("conditioning_reused") is True,
            "first_truthful_gpu_execution": truthful_eager_cuda_synthesis_proven(first),
            "second_truthful_gpu_execution": truthful_eager_cuda_synthesis_proven(second),
            "accepted_output_tensors_cuda_never_claimed": all(
                (item.get("gpu_proof") or {}).get("accepted_output_tensors_cuda") is False
                for item in (first, second)
            ),
            "first_wav_valid": (first.get("wav_validation") or {}).get("passed") is True,
            "second_wav_valid": (second.get("wav_validation") or {}).get("passed") is True,
            "exact_profile_reference_and_text_hashes": exact_syntheses,
            "explicit_unload": report["unload"].get("unloaded") is True,
            "torch_allocation_returned": (
                isinstance(unload_measurement.get("allocated_before_bytes"), int)
                and unload_measurement.get("allocated_before_bytes") >= 256 * 1024 * 1024
                and isinstance(unload_measurement.get("allocated_after_bytes"), int)
                and unload_measurement.get("allocated_after_bytes") < 256 * 1024 * 1024
                and isinstance(unload_measurement.get("allocated_returned_bytes"), int)
                and unload_measurement.get("allocated_returned_bytes") >= 256 * 1024 * 1024
            ),
            "model_unloaded": (
                (report["status_after_unload"].get("lifecycle") or {}).get("model_loaded") is False
            ),
            "qwen_absent_before": qwen_before.get("qwen_absent_proven") is True,
            "qwen_absent_after": report["qwen_after"].get("qwen_absent_proven") is True,
            "all_ollama_models_absent_before": ollama_before.get(
                "all_models_absent_proven"
            )
            is True,
            "all_ollama_models_absent_after": report["ollama_after"].get(
                "all_models_absent_proven"
            )
            is True,
            "worker_exit_clean": report["worker_exit_clean"] is True,
            "no_playback": all(
                item.get("playback") is False
                for item in (report["hello"], report["load"], first, second, report["unload"])
            ),
            "no_fallback": all(
                item.get("fallback_used") is False
                for item in (report["hello"], report["load"], first, second, report["unload"])
            ),
        }
        report["checks"] = checks
        report["engineering_pass"] = all(checks.values())
        report["owner_heard_acceptance"] = False
        report["promotion_eligible"] = False
        report["status"] = (
            "engineering_pass_pending_owner_heard_acceptance"
            if report["engineering_pass"]
            else "engineering_failed"
        )
        report["passed"] = bool(report["engineering_pass"])
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
        report["traceback"] = traceback.format_exc()
        report["status"] = "failed_preserved_inactive"
    finally:
        if client is not None:
            report["diagnostics_before_cleanup"] = client_diagnostic_snapshot(client)
            try:
                report["cleanup_shutdown"] = client.close()
            except Exception as cleanup_exc:
                report["cleanup_error"] = f"{type(cleanup_exc).__name__}: {cleanup_exc}"
            report["diagnostics_after_cleanup"] = client_diagnostic_snapshot(client)
        report["cache_size_after_bytes"] = cache_size_bytes(cache_root)
        report["cache_deleted_automatically"] = False
        report["protected_after"] = file_hashes(PROTECTED_PATHS)
        report["protected_files_unchanged"] = report["protected_before"] == report["protected_after"]
        if report["protected_files_unchanged"] is not True:
            report["passed"] = False
            report["status"] = "failed_protected_integrity_changed"
        report["finished_at"] = utc_now()
        report["total_wall_seconds"] = round(
            time.time() - datetime.fromisoformat(report["started_at"]).timestamp(),
            6,
        )
        evidence_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["evidence_path"] = relative(evidence_path)
        report["evidence_sha256"] = sha256_file(evidence_path)
    return evidence_path, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--run-gpu", action="store_true")
    parser.add_argument("--confirm-no-active-blender", action="store_true")
    parser.add_argument("--expected-candidate-config-sha256", default="")
    args = parser.parse_args()
    if args.describe:
        print(json.dumps(describe(), ensure_ascii=False, indent=2))
        return 0
    expected_config_hash = str(args.expected_candidate_config_sha256 or "").strip().casefold()
    if (
        not args.run_gpu
        or not args.confirm_no_active_blender
        or not re.fullmatch(r"[0-9a-f]{64}", expected_config_hash)
    ):
        print(
            json.dumps(
                {
                    **describe(),
                    "ready": False,
                    "reason": "explicit_gpu_no_active_blender_and_exact_config_hash_required",
                    "gpu_started": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    evidence_path, report = run_acceptance(
        expected_candidate_config_sha256=expected_config_hash
    )
    print(
        json.dumps(
            {
                "passed": report.get("passed") is True,
                "status": report.get("status"),
                "evidence_path": relative(evidence_path),
                "evidence_sha256": report.get("evidence_sha256"),
                "promotion_performed": False,
                "playback_performed": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report.get("passed") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
