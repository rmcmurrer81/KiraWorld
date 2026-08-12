#!/usr/bin/env python3
"""Append-only finalization revision for the pending-Defender import control.

This revision preserves the predecessor used by the failed attempt.  It keeps
the same real protocol/import-only boundary, but records cleanup and forbidden-
outcome truth as TRUE, FALSE, or UNKNOWN instead of turning missing late
responses into a false claim.  The normal invocation is inert.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import importlib.util
import json
import sys
import traceback
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREDECESSOR_PATH = (
    ROOT
    / "tools"
    / "run_persistent_blackwell_protocol_import_only_control_pending_defender_state.py"
)
PREDECESSOR_SHA256 = "cf72d1d5dcb5060b1f7fdf88deefa3d97d72351c459fca0f80736d60da9c4cd9"
FAILED_ATTEMPT_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "import_only_protocol_control_pending_defender_state"
    / "attempt_01"
)
FAILED_REPORT_PATH = FAILED_ATTEMPT_ROOT / "PROTOCOL_IMPORT_ONLY_PENDING_DEFENDER_STATE.json"
FAILED_REPORT_SHA256 = "9bf47ced167c1d6733277516207426d1f5a4dc699caa900cbfd4228730349884"
POST_FAILURE_CHECK_PATH = FAILED_ATTEMPT_ROOT / "POST_FAILURE_PROCESS_CHECK.json"
POST_FAILURE_CHECK_SHA256 = "c87cc5a66a05c274dec280505c3f474459b1cf64df2672cd0958661f06bada7a"
ATTEMPT_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "import_only_protocol_control_pending_defender_state_v2"
)
DEFAULT_TIMEOUT_SECONDS = 1100.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if not hmac.compare_digest(sha256_file(PREDECESSOR_PATH), PREDECESSOR_SHA256):
    raise RuntimeError("failed-run predecessor wrapper changed before dependency load")
SPEC = importlib.util.spec_from_file_location(
    "pending_defender_import_control_predecessor",
    PREDECESSOR_PATH,
)
assert SPEC is not None and SPEC.loader is not None
predecessor = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = predecessor
SPEC.loader.exec_module(predecessor)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def validate_failed_attempt_bindings(
    expected_failed_report_sha256: str,
    expected_post_failure_check_sha256: str,
) -> dict[str, Any]:
    if not hmac.compare_digest(
        expected_failed_report_sha256.strip().casefold(),
        FAILED_REPORT_SHA256,
    ):
        raise ValueError("operator did not bind the preserved failed report")
    if not hmac.compare_digest(
        expected_post_failure_check_sha256.strip().casefold(),
        POST_FAILURE_CHECK_SHA256,
    ):
        raise ValueError("operator did not bind the post-failure process check")
    if sha256_file(FAILED_REPORT_PATH) != FAILED_REPORT_SHA256:
        raise RuntimeError("preserved failed report changed")
    if sha256_file(POST_FAILURE_CHECK_PATH) != POST_FAILURE_CHECK_SHA256:
        raise RuntimeError("preserved post-failure process check changed")
    report = json.loads(FAILED_REPORT_PATH.read_text(encoding="utf-8"))
    post = json.loads(POST_FAILURE_CHECK_PATH.read_text(encoding="utf-8"))
    if report.get("status") != "failed_preserved" or report.get("passed") is not False:
        raise RuntimeError("preserved failed report truth changed")
    if post.get("report_sha256") != FAILED_REPORT_SHA256:
        raise RuntimeError("post-failure process check binding changed")
    return {
        "failed_report": {
            "path": relative(FAILED_REPORT_PATH),
            "bytes": FAILED_REPORT_PATH.stat().st_size,
            "sha256": FAILED_REPORT_SHA256,
        },
        "post_failure_process_check": {
            "path": relative(POST_FAILURE_CHECK_PATH),
            "bytes": POST_FAILURE_CHECK_PATH.stat().st_size,
            "sha256": POST_FAILURE_CHECK_SHA256,
        },
        "failed_report_preserved_unchanged": True,
    }


def classify_cleanup(
    cleanup_response: dict[str, Any] | None,
    owned_process_exit_code: int | None,
) -> dict[str, Any]:
    acknowledged = bool(
        isinstance(cleanup_response, dict)
        and cleanup_response.get("operation") == "shutdown"
        and cleanup_response.get("shutdown") is True
    )
    forced = (
        cleanup_response.get("owned_process_forced_termination")
        if isinstance(cleanup_response, dict)
        else None
    )
    if acknowledged and owned_process_exit_code == 0 and forced is False:
        clean: bool | None = True
        status = "PROVEN_CLEAN_PROTOCOL_SHUTDOWN"
    elif forced is True or (
        owned_process_exit_code is not None and owned_process_exit_code != 0
    ):
        clean = False
        status = "PROVEN_NOT_CLEAN"
    else:
        clean = None
        status = "UNKNOWN_NO_VALIDATED_SHUTDOWN_RESPONSE"
    return {
        "cleanup_response": cleanup_response,
        "shutdown_response_validated": acknowledged,
        "owned_process_exit_code_observed": owned_process_exit_code,
        "owned_process_forced_termination": forced,
        "cleanup_clean": clean,
        "cleanup_status": status,
    }


def classify_prohibited_outcomes(report: dict[str, Any]) -> dict[str, Any]:
    result = report.get("load_import_only")
    required_child_keys = (
        "cuda_api_invoked",
        "torchaudio_imported",
        "chatterbox_imported",
        "model_loaded",
        "audio_generated",
        "playback_performed",
        "ollama_invoked",
    )
    evidence_complete = isinstance(result, dict) and all(
        key in result for key in required_child_keys
    )
    observed_true: list[str] = []
    for source_name, payload in (
        ("report", report),
        ("hello", report.get("hello") or {}),
        ("load_import_only", result or {}),
    ):
        for key in (
            "cuda_api_invoked",
            "torchaudio_imported",
            "chatterbox_imported",
            "model_loaded",
            "audio_generated",
            "playback_performed",
            "ollama_invoked",
            "candidate_promoted",
            "production_routing_changed",
            "production_routing_authorized",
            "generic_voice_used",
            "sapi_voice_used",
            "fallback_used",
        ):
            if payload.get(key) is True:
                observed_true.append(f"{source_name}.{key}")
    if observed_true:
        absent: bool | None = False
        status = "PROHIBITED_OUTCOME_OBSERVED"
    elif evidence_complete:
        absent = True
        status = "PROHIBITED_OUTCOMES_ABSENCE_PROVEN_BY_COMPLETE_CHILD_RESPONSE"
    else:
        absent = None
        status = "UNKNOWN_INCOMPLETE_CHILD_RESPONSE"
    return {
        "prohibited_outcomes_observed": bool(observed_true),
        "observed_true_fields": observed_true,
        "prohibited_outcomes_evidence_complete": evidence_complete,
        "prohibited_outcomes_absent": absent,
        "prohibited_outcomes_status": status,
    }


def close_client_with_observation(client: Any | None) -> dict[str, Any]:
    if client is None:
        return classify_cleanup(None, None)
    owned_process = client.process
    owned_pid = owned_process.pid if owned_process is not None else None
    cleanup_error: str | None = None
    try:
        cleanup_response = client.close()
    except Exception as exc:
        cleanup_response = None
        cleanup_error = f"{type(exc).__name__}: {exc}"
    exit_code = owned_process.poll() if owned_process is not None else None
    return {
        "owned_process_pid": owned_pid,
        "cleanup_error": cleanup_error,
        **classify_cleanup(cleanup_response, exit_code),
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
    raise RuntimeError("no append-only v2 import-control attempt is available")


def run_control(
    *,
    expected_candidate_config_sha256: str,
    expected_predecessor_sha256: str,
    expected_wrapper_sha256: str,
    expected_apply_result_sha256: str,
    expected_failed_report_sha256: str,
    expected_post_failure_check_sha256: str,
    timeout_seconds: float,
) -> tuple[Path, dict[str, Any]]:
    if not hmac.compare_digest(
        expected_predecessor_sha256.strip().casefold(),
        PREDECESSOR_SHA256,
    ):
        raise ValueError("operator-bound predecessor wrapper hash mismatch")
    if sha256_file(PREDECESSOR_PATH) != PREDECESSOR_SHA256:
        raise RuntimeError("failed-run predecessor wrapper changed")
    wrapper_hash = sha256_file(Path(__file__).resolve())
    if not hmac.compare_digest(
        expected_wrapper_sha256.strip().casefold(),
        wrapper_hash,
    ):
        raise ValueError("operator-bound v2 wrapper hash mismatch")
    hashes = predecessor.strict_base.exact_candidate_hashes()
    if hashes != predecessor.strict_base.EXPECTED_BASELINE_HASHES:
        raise RuntimeError("restored candidate hashes changed")
    if not hmac.compare_digest(
        expected_candidate_config_sha256.strip().casefold(),
        hashes["candidate_config"],
    ):
        raise ValueError("operator-bound candidate config hash mismatch")
    apply_result = predecessor.validate_apply_exit_record(expected_apply_result_sha256)
    failed_bindings = validate_failed_attempt_bindings(
        expected_failed_report_sha256,
        expected_post_failure_check_sha256,
    )
    blender = predecessor.strict_base.no_active_blender_evidence()
    if blender.get("query_succeeded") is not True or blender.get("active") is not False:
        raise RuntimeError(f"no-active-Blender gate failed: {blender}")

    attempt = allocate_attempt_directory()
    marker_path = attempt / "ATTEMPT_STARTED.json"
    report_path = attempt / "PROTOCOL_IMPORT_ONLY_PENDING_DEFENDER_STATE_V2.json"
    started_at = utc_now()
    marker_sha256 = predecessor.strict_base.write_json_exclusive(
        marker_path,
        {
            "schema_version": 1,
            "artifact_kind": "protocol_import_only_pending_defender_state_v2_started",
            "started_at": started_at,
            "candidate_hashes": hashes,
            "predecessor_wrapper_sha256": PREDECESSOR_SHA256,
            "wrapper_sha256": wrapper_hash,
            "apply_result": apply_result,
            "failed_attempt_bindings": failed_bindings,
            "independent_defender_state": predecessor.UNKNOWN_STATE,
            "cuda_api_invoked": False,
            "model_loaded": False,
            "audio_generated": False,
            "candidate_promoted": False,
            "production_routing_changed": False,
        },
    )
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "persistent_blackwell_protocol_import_only_pending_defender_state_v2",
        "started_at": started_at,
        "status": "started",
        "candidate_hashes": hashes,
        "predecessor_wrapper_sha256": PREDECESSOR_SHA256,
        "wrapper_sha256": wrapper_hash,
        "apply_result": apply_result,
        "failed_attempt_bindings": failed_bindings,
        "independent_defender_state": predecessor.UNKNOWN_STATE,
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
        client = predecessor.strict_base.ImportOnlyProtocolClient(
            allow_gpu_model_load=True,
            startup_timeout_seconds=30.0,
            request_timeout_seconds=timeout_seconds,
            diagnostic_directory=attempt,
        )
        report["hello"] = client.start()
        report["status_before_import"] = client.status()
        report["load_import_only"] = client.load_import_only()
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
            }
        )
    finally:
        report["phase_events_before_cleanup"] = client.events if client is not None else []
        report["cleanup_observation"] = close_client_with_observation(client)
        report["phase_events_after_cleanup"] = client.events if client is not None else []
        report["finished_at"] = utc_now()
        report["candidate_hashes_after"] = predecessor.strict_base.exact_candidate_hashes()
        report["candidate_unchanged"] = (
            report["candidate_hashes_after"]
            == predecessor.strict_base.EXPECTED_BASELINE_HASHES
        )
        report.update(classify_prohibited_outcomes(report))
        report["cleanup_clean"] = report["cleanup_observation"]["cleanup_clean"]
        report["passed"] = (
            report.get("functional_gate_passed") is True
            and report["candidate_unchanged"] is True
            and report["cleanup_clean"] is True
            and report["prohibited_outcomes_absent"] is True
        )
        report["status"] = "passed" if report["passed"] else "failed_preserved"
        predecessor.strict_base.write_json_exclusive(report_path, report)
    return report_path, report


def describe() -> dict[str, Any]:
    failed_bindings = validate_failed_attempt_bindings(
        FAILED_REPORT_SHA256,
        POST_FAILURE_CHECK_SHA256,
    )
    return {
        "schema_version": 1,
        "artifact_kind": "protocol_import_only_pending_defender_state_v2_description",
        "status": "PREPARED_NOT_EXECUTED",
        "predecessor_path": relative(PREDECESSOR_PATH),
        "predecessor_sha256": PREDECESSOR_SHA256,
        "predecessor_unchanged": sha256_file(PREDECESSOR_PATH) == PREDECESSOR_SHA256,
        "failed_attempt_bindings": failed_bindings,
        "independent_defender_state": predecessor.UNKNOWN_STATE,
        "missing_cleanup_response_maps_to": "UNKNOWN_NOT_FALSE",
        "incomplete_child_outcome_evidence_maps_to": "UNKNOWN_NOT_FALSE",
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


def static_self_check() -> dict[str, Any]:
    source = Path(__file__).read_text(encoding="utf-8")
    operational = source[: source.index("\ndef static_self_check")]
    unknown_cleanup = classify_cleanup(None, 0)
    unknown_outcomes = classify_prohibited_outcomes({"cuda_api_invoked": False})
    complete_outcomes = classify_prohibited_outcomes(
        {
            "load_import_only": {
                "cuda_api_invoked": False,
                "torchaudio_imported": False,
                "chatterbox_imported": False,
                "model_loaded": False,
                "audio_generated": False,
                "playback_performed": False,
                "ollama_invoked": False,
            }
        }
    )
    checks = {
        "predecessor_unchanged": sha256_file(PREDECESSOR_PATH) == PREDECESSOR_SHA256,
        "failed_report_unchanged": sha256_file(FAILED_REPORT_PATH) == FAILED_REPORT_SHA256,
        "post_failure_check_unchanged": (
            sha256_file(POST_FAILURE_CHECK_PATH) == POST_FAILURE_CHECK_SHA256
        ),
        "strict_base_static_check_passes": predecessor.strict_base.static_self_check().get(
            "passed"
        )
        is True,
        "missing_cleanup_is_unknown": unknown_cleanup["cleanup_clean"] is None,
        "incomplete_outcomes_are_unknown": (
            unknown_outcomes["prohibited_outcomes_absent"] is None
        ),
        "complete_false_outcomes_prove_absence": (
            complete_outcomes["prohibited_outcomes_absent"] is True
        ),
        "no_defender_command": not any(
            marker in operational
            for marker in (
                "Get" + "-MpPreference",
                "Add" + "-MpPreference",
                "Remove" + "-MpPreference",
                "Set" + "-MpPreference",
            )
        ),
        "no_torch_cuda_call": "torch.cuda" not in operational,
        "no_model_factory_call": "from_pretrained(" not in operational,
        "no_audio_or_playback_call": not any(
            marker in operational
            for marker in ("winsound.PlaySound(", "sounddevice.play(", "sd.play(")
        ),
        "no_promotion_or_route_function": not any(
            marker in operational
            for marker in (
                "promote_" + "candidate(",
                "activate_" + "candidate(",
                "set_production_" + "route(",
            )
        ),
    }
    return {
        "schema_version": 1,
        "artifact_kind": "protocol_import_only_pending_defender_state_v2_static_self_check",
        "checks": checks,
        "passed": all(checks.values()),
        "blackwell_runtime_started": False,
        "torch_imported": False,
        "cuda_api_invoked": False,
        "model_loaded": False,
        "audio_generated": False,
        "playback_performed": False,
        "ollama_invoked": False,
        "defender_queried": False,
        "defender_changed": False,
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
    parser.add_argument("--expected-predecessor-sha256", default="")
    parser.add_argument("--expected-wrapper-sha256", default="")
    parser.add_argument("--expected-apply-result-sha256", default="")
    parser.add_argument("--expected-failed-report-sha256", default="")
    parser.add_argument("--expected-post-failure-check-sha256", default="")
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
    timeout_seconds = max(300.0, min(1500.0, float(args.timeout_seconds)))
    report_path, report = run_control(
        expected_candidate_config_sha256=args.expected_candidate_config_sha256,
        expected_predecessor_sha256=args.expected_predecessor_sha256,
        expected_wrapper_sha256=args.expected_wrapper_sha256,
        expected_apply_result_sha256=args.expected_apply_result_sha256,
        expected_failed_report_sha256=args.expected_failed_report_sha256,
        expected_post_failure_check_sha256=args.expected_post_failure_check_sha256,
        timeout_seconds=timeout_seconds,
    )
    print(
        json.dumps(
            {
                "report": relative(report_path),
                "report_sha256": sha256_file(report_path),
                "passed": report.get("passed") is True,
                "status": report.get("status"),
                "cleanup_clean": report.get("cleanup_clean"),
                "prohibited_outcomes_absent": report.get("prohibited_outcomes_absent"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report.get("passed") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
