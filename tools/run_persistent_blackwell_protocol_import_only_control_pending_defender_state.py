#!/usr/bin/env python3
"""Static revision of the protocol import control for pending Defender state.

This wrapper preserves the stricter control unchanged.  It can later run the
same real client/worker Torch-import-only child using the recorded legitimate
UAC helper exit code, while labeling independent current Defender state as
UNKNOWN/PENDING.  It never queries or changes Defender and makes no exclusion,
latency, or causal claim.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import importlib.util
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_TOOL_PATH = ROOT / "tools" / "run_persistent_blackwell_protocol_import_only_control.py"
BASE_TOOL_SHA256 = "7fd8e006ba58aede2f34b4289c4fc857a1bc6ae76d6a6a4fcc36a7f3a0466f21"
APPLY_HELPER_PATH = ROOT / "tools" / "apply_defender_blackwell_voice_exclusion.ps1"
APPLY_HELPER_SHA256 = "87527f0c5973a6e1c3c698b0a21395562ae6db4fb94849b6271cf99591664919"
APPLY_RESULT_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "defender_blackwell_voice_narrow_exclusion"
    / "attempt_02"
    / "APPLY_RESULT_FROM_OBSERVED_UAC_EXIT.json"
)
APPLY_RESULT_SHA256 = "f4e0a73b43a4bb6a6ade9234da3d4a55a69cac4eee1905d59f6ee9201914a057"
PRIOR_CHECKPOINT_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "persistent_blackwell_defender_exclusion_protocol_import_control_preparation"
    / "attempt_01"
    / "CHECKPOINT.md"
)
PRIOR_CHECKPOINT_SHA256 = "8b9771580194a9fec66bf57bf3c6a282883ec637ee89ce90c9378d39b7406d7b"
PRIOR_MANIFEST_PATH = PRIOR_CHECKPOINT_PATH.with_name("MANIFEST.json")
PRIOR_MANIFEST_SHA256 = "8d112384c06144e9405a39233d6564de46db6f508bf01be8db5cc6d49e8c8140"
ATTEMPT_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "import_only_protocol_control_pending_defender_state"
)
DEFAULT_TIMEOUT_SECONDS = 1100.0
UNKNOWN_STATE = "UNKNOWN_PENDING_INDEPENDENT_CAPTURE"
EXPECTED_EXCLUSION_TARGET = (
    r"C:\Users\robmc\Kira\Voice\sidecars\chatterbox_blackwell_gpu\.venv"
)
EXPECTED_EXIT_ZERO_CONTRACT = (
    "the helper's post-" + "Get" + "-MpPreference exact-target-present check passed",
    "the helper's real-time-monitoring-not-disabled check passed",
    "the helper's behavior-monitoring-not-disabled check passed",
)


def _sha256_before_dependency_load(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if not hmac.compare_digest(
    _sha256_before_dependency_load(BASE_TOOL_PATH),
    BASE_TOOL_SHA256,
):
    raise RuntimeError("stricter protocol-import control changed before dependency load")

BASE_SPEC = importlib.util.spec_from_file_location(
    "blackwell_protocol_import_strict_base",
    BASE_TOOL_PATH,
)
assert BASE_SPEC is not None and BASE_SPEC.loader is not None
strict_base = importlib.util.module_from_spec(BASE_SPEC)
sys.modules[BASE_SPEC.name] = strict_base
BASE_SPEC.loader.exec_module(strict_base)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def validate_apply_exit_record(expected_sha256: str) -> dict[str, Any]:
    expected = str(expected_sha256 or "").strip().casefold()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("exact apply-result SHA-256 is required")
    if not hmac.compare_digest(expected, APPLY_RESULT_SHA256):
        raise ValueError("operator did not bind the sealed apply-result record")
    if sha256_file(APPLY_RESULT_PATH) != APPLY_RESULT_SHA256:
        raise ValueError("apply-result record changed")
    if sha256_file(APPLY_HELPER_PATH) != APPLY_HELPER_SHA256:
        raise ValueError("sole apply helper changed")
    if sha256_file(BASE_TOOL_PATH) != BASE_TOOL_SHA256:
        raise ValueError("stricter protocol-import control changed")
    if sha256_file(PRIOR_CHECKPOINT_PATH) != PRIOR_CHECKPOINT_SHA256:
        raise ValueError("prior static checkpoint changed")
    if sha256_file(PRIOR_MANIFEST_PATH) != PRIOR_MANIFEST_SHA256:
        raise ValueError("prior static manifest changed")
    payload = json.loads(APPLY_RESULT_PATH.read_text(encoding="utf-8"))
    observation = payload.get("execution_observation") or {}
    boundary = payload.get("truth_boundary") or {}
    helper = payload.get("sole_apply_helper") or {}
    required = {
        "helper_exit_code_observed": observation.get("helper_exit_code_observed") == 0,
        "independent_state_pending": (
            observation.get("independent_post_state_status") == "UNKNOWN_PENDING"
        ),
        "helper_hash_exact": helper.get("sha256") == APPLY_HELPER_SHA256,
        "helper_path_exact": helper.get("path") == relative(APPLY_HELPER_PATH),
        "helper_target_exact": (
            helper.get("exact_hard_coded_target") == EXPECTED_EXCLUSION_TARGET
        ),
        "helper_exit_contract_exact": tuple(helper.get("exit_zero_code_contract") or ())
        == EXPECTED_EXIT_ZERO_CONTRACT,
        "independent_exclusion_not_claimed": (
            boundary.get("exclusion_present_claimed_from_independent_evidence") is False
        ),
        "independent_monitoring_not_claimed": (
            boundary.get("monitoring_enabled_claimed_from_independent_evidence") is False
        ),
        "latency_not_claimed": boundary.get("latency_improvement_claimed") is False,
        "causality_not_claimed": boundary.get("defender_causality_claimed") is False,
        "production_not_accepted": (
            boundary.get("production_voice_acceptance_claimed") is False
        ),
    }
    if not all(required.values()):
        raise ValueError(f"apply-result truth contract changed: {required}")
    return {
        "path": relative(APPLY_RESULT_PATH),
        "sha256": APPLY_RESULT_SHA256,
        "helper_exit_code_observed": 0,
        "helper_sha256": APPLY_HELPER_SHA256,
        "helper_exact_hard_coded_target": EXPECTED_EXCLUSION_TARGET,
        "helper_exit_zero_contract": list(EXPECTED_EXIT_ZERO_CONTRACT),
        "independent_defender_state": UNKNOWN_STATE,
        "exclusion_present_claimed": False,
        "monitoring_enabled_claimed_from_independent_evidence": False,
        "latency_improvement_claimed": False,
        "defender_causality_claimed": False,
        "paired_pre_post_causality_available": False,
    }


def allocate_attempt_directory() -> Path:
    ATTEMPT_ROOT.mkdir(parents=True, exist_ok=True)
    for number in range(1, 1000):
        path = ATTEMPT_ROOT / f"attempt_{number:02d}"
        try:
            path.mkdir()
        except FileExistsError:
            continue
        return path
    raise RuntimeError("no append-only pending-Defender import-control attempt is available")


def run_control(
    *,
    expected_candidate_config_sha256: str,
    expected_base_tool_sha256: str,
    expected_wrapper_tool_sha256: str,
    expected_apply_result_sha256: str,
    timeout_seconds: float,
) -> tuple[Path, dict[str, Any]]:
    hashes = strict_base.exact_candidate_hashes()
    if hashes != strict_base.EXPECTED_BASELINE_HASHES:
        raise RuntimeError(f"restored Attempt 06 candidate hashes changed: {hashes}")
    if not hmac.compare_digest(
        str(expected_candidate_config_sha256 or "").strip().casefold(),
        hashes["candidate_config"],
    ):
        raise ValueError("operator-bound candidate config SHA-256 mismatch")
    if not hmac.compare_digest(
        str(expected_base_tool_sha256 or "").strip().casefold(),
        BASE_TOOL_SHA256,
    ):
        raise ValueError("operator-bound stricter control SHA-256 mismatch")
    wrapper_hash = sha256_file(Path(__file__).resolve())
    if not hmac.compare_digest(
        str(expected_wrapper_tool_sha256 or "").strip().casefold(),
        wrapper_hash,
    ):
        raise ValueError("operator-bound wrapper SHA-256 mismatch")
    apply_result = validate_apply_exit_record(expected_apply_result_sha256)
    blender = strict_base.no_active_blender_evidence()
    if blender.get("query_succeeded") is not True or blender.get("active") is not False:
        raise RuntimeError(f"no-active-Blender gate failed: {blender}")

    attempt = allocate_attempt_directory()
    report_path = attempt / "PROTOCOL_IMPORT_ONLY_PENDING_DEFENDER_STATE.json"
    marker_path = attempt / "ATTEMPT_STARTED.json"
    started_at = utc_now()
    marker_sha256 = strict_base.write_json_exclusive(
        marker_path,
        {
            "schema_version": 1,
            "artifact_kind": "protocol_import_only_pending_defender_state_started",
            "started_at": started_at,
            "candidate_hashes": hashes,
            "base_tool_sha256": BASE_TOOL_SHA256,
            "wrapper_tool_sha256": wrapper_hash,
            "apply_result": apply_result,
            "independent_defender_state": UNKNOWN_STATE,
            "cuda_api_invoked": False,
            "model_loaded": False,
            "audio_generated": False,
            "candidate_promoted": False,
            "production_routing_changed": False,
        },
    )
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "persistent_blackwell_protocol_import_only_pending_defender_state",
        "started_at": started_at,
        "status": "started",
        "candidate_hashes": hashes,
        "base_tool_sha256": BASE_TOOL_SHA256,
        "wrapper_tool_sha256": wrapper_hash,
        "apply_result": apply_result,
        "independent_defender_state": UNKNOWN_STATE,
        "exclusion_present_claimed": False,
        "monitoring_enabled_claimed_from_independent_evidence": False,
        "latency_improvement_claimed": False,
        "defender_causality_claimed": False,
        "production_voice_acceptance_claimed": False,
        "attempt_started_marker": {
            "path": relative(marker_path),
            "sha256": marker_sha256,
        },
        "no_active_blender": blender,
        "timeout_seconds": timeout_seconds,
        "defender_queried_by_this_control": False,
        "defender_changed_by_this_control": False,
        "cuda_api_invoked": False,
        "model_loaded": False,
        "audio_generated": False,
        "playback_performed": False,
        "ollama_invoked": False,
        "candidate_promoted": False,
        "production_routing_changed": False,
    }
    client: Any | None = None
    try:
        client = strict_base.ImportOnlyProtocolClient(
            allow_gpu_model_load=True,
            startup_timeout_seconds=30.0,
            request_timeout_seconds=timeout_seconds,
            diagnostic_directory=attempt,
        )
        report["hello"] = client.start()
        report["status_before_import"] = client.status()
        report["load_import_only"] = client.load_import_only()
        report["phase_events"] = client.events
        result = report["load_import_only"]
        report["functional_gate_passed"] = (
            result.get("ready") is True
            and result.get("torch_version") == "2.11.0+cu130"
            and result.get("torchaudio_imported") is False
            and result.get("chatterbox_imported") is False
            and result.get("cuda_api_invoked") is False
            and result.get("model_loaded") is False
            and report["hello"].get("production_routing_authorized") is False
        )
    except Exception as exc:
        report.update(
            {
                "functional_gate_passed": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc()[-16000:],
                "phase_events": client.events if client is not None else [],
            }
        )
    finally:
        report["cleanup"] = client.close() if client is not None else None
        report["finished_at"] = utc_now()
        report["candidate_hashes_after"] = strict_base.exact_candidate_hashes()
        report["candidate_unchanged"] = (
            report["candidate_hashes_after"] == strict_base.EXPECTED_BASELINE_HASHES
        )
        cleanup = report.get("cleanup")
        report["cleanup_clean"] = (
            isinstance(cleanup, dict)
            and cleanup.get("owned_process_exit_code") == 0
            and cleanup.get("owned_process_forced_termination") is False
        )
        result = report.get("load_import_only") or {}
        report["prohibited_outcomes_absent"] = (
            report.get("defender_queried_by_this_control") is False
            and report.get("defender_changed_by_this_control") is False
            and report.get("cuda_api_invoked") is False
            and report.get("model_loaded") is False
            and report.get("audio_generated") is False
            and report.get("playback_performed") is False
            and report.get("ollama_invoked") is False
            and report.get("candidate_promoted") is False
            and report.get("production_routing_changed") is False
            and result.get("torchaudio_imported") is False
            and result.get("chatterbox_imported") is False
            and result.get("cuda_api_invoked") is False
            and result.get("model_loaded") is False
            and result.get("audio_generated") is False
            and result.get("playback_performed") is False
            and result.get("ollama_invoked") is False
        )
        report["passed"] = (
            report.get("functional_gate_passed") is True
            and report["candidate_unchanged"] is True
            and report["cleanup_clean"] is True
            and report["prohibited_outcomes_absent"] is True
        )
        report["status"] = "passed" if report["passed"] else "failed_preserved"
        strict_base.write_json_exclusive(report_path, report)
    return report_path, report


def describe() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "artifact_kind": "protocol_import_only_pending_defender_state_description",
        "status": "PREPARED_NOT_EXECUTED",
        "strict_base_tool_path": relative(BASE_TOOL_PATH),
        "strict_base_tool_sha256": BASE_TOOL_SHA256,
        "strict_base_unchanged": sha256_file(BASE_TOOL_PATH) == BASE_TOOL_SHA256,
        "apply_result_path": relative(APPLY_RESULT_PATH),
        "apply_result_sha256": APPLY_RESULT_SHA256,
        "helper_exit_code_observed": 0,
        "independent_defender_state": UNKNOWN_STATE,
        "exclusion_present_claimed": False,
        "monitoring_enabled_claimed_from_independent_evidence": False,
        "latency_improvement_claimed": False,
        "defender_causality_claimed": False,
        "defender_queried": False,
        "defender_changed": False,
        "torch_imported": False,
        "cuda_api_invoked": False,
        "model_loaded": False,
        "audio_generated": False,
        "playback_performed": False,
        "ollama_invoked": False,
        "candidate_promoted": False,
        "production_routing_changed": False,
    }


def static_self_check() -> dict[str, Any]:
    source = Path(__file__).read_text(encoding="utf-8")
    operational_source = source[: source.index("\ndef static_self_check")]
    apply_result = validate_apply_exit_record(APPLY_RESULT_SHA256)
    base_check = strict_base.static_self_check()
    mutation_markers = (
        "Get" + "-MpPreference",
        "Add" + "-MpPreference",
        "Remove" + "-MpPreference",
        "Set" + "-MpPreference",
    )
    checks = {
        "strict_base_unchanged": sha256_file(BASE_TOOL_PATH) == BASE_TOOL_SHA256,
        "sole_apply_helper_unchanged": sha256_file(APPLY_HELPER_PATH) == APPLY_HELPER_SHA256,
        "apply_result_valid": apply_result["helper_exit_code_observed"] == 0,
        "independent_state_unknown": (
            apply_result["independent_defender_state"] == UNKNOWN_STATE
        ),
        "strict_base_static_check_passes": base_check.get("passed") is True,
        "no_defender_command": not any(
            marker in operational_source for marker in mutation_markers
        ),
        "no_torch_import_call_in_wrapper": (
            'import_module("torch")' not in operational_source
        ),
        "no_cuda_call_in_wrapper": "torch.cuda" not in operational_source,
        "no_model_factory_call_in_wrapper": "from_pretrained(" not in operational_source,
        "no_audio_or_playback_call_in_wrapper": not any(
            marker in operational_source
            for marker in ("winsound.PlaySound(", "sounddevice.play(", "sd.play(")
        ),
        "no_promotion_function": not any(
            marker in operational_source
            for marker in ("promote_candidate(", "set_production_route(", "activate_candidate(")
        ),
        "unknown_state_label_present": UNKNOWN_STATE in source,
    }
    return {
        "schema_version": 1,
        "artifact_kind": "protocol_import_only_pending_defender_state_static_self_check",
        "checks": checks,
        "passed": all(checks.values()),
        "independent_defender_state": UNKNOWN_STATE,
        "defender_queried": False,
        "defender_changed": False,
        "blackwell_runtime_started": False,
        "torch_imported": False,
        "cuda_api_invoked": False,
        "model_loaded": False,
        "audio_generated": False,
        "playback_performed": False,
        "ollama_invoked": False,
        "candidate_promoted": False,
        "production_routing_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--describe", action="store_true")
    group.add_argument("--static-self-check", action="store_true")
    group.add_argument("--run-control", action="store_true")
    parser.add_argument("--confirm-no-active-blender", action="store_true")
    parser.add_argument("--expected-candidate-config-sha256", default="")
    parser.add_argument("--expected-base-tool-sha256", default="")
    parser.add_argument("--expected-wrapper-tool-sha256", default="")
    parser.add_argument("--expected-apply-result-sha256", default="")
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args()

    if args.static_self_check:
        result = static_self_check()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 2
    if not args.run_control:
        print(json.dumps(describe(), indent=2, sort_keys=True))
        return 0
    if not args.confirm_no_active_blender:
        raise SystemExit("--confirm-no-active-blender is required")
    timeout = max(300.0, min(1500.0, float(args.timeout_seconds)))
    report_path, report = run_control(
        expected_candidate_config_sha256=args.expected_candidate_config_sha256,
        expected_base_tool_sha256=args.expected_base_tool_sha256,
        expected_wrapper_tool_sha256=args.expected_wrapper_tool_sha256,
        expected_apply_result_sha256=args.expected_apply_result_sha256,
        timeout_seconds=timeout,
    )
    print(
        json.dumps(
            {
                "report": relative(report_path),
                "report_sha256": sha256_file(report_path),
                "passed": report.get("passed") is True,
                "status": report.get("status"),
                "independent_defender_state": UNKNOWN_STATE,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report.get("passed") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
