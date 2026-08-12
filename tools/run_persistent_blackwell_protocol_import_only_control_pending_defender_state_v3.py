#!/usr/bin/env python3
"""Strict-Boolean finalization revision for pending-Defender import control."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import importlib.util
import json
import sys
import traceback
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REJECTED_V2_PATH = (
    ROOT
    / "tools"
    / "run_persistent_blackwell_protocol_import_only_control_pending_defender_state_v2.py"
)
REJECTED_V2_SHA256 = "424869e7a3d90d30dd20381a3adbcf00cd91521ec5cd57c40d0e6f0d8e5eb7c0"
ATTEMPT_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
    / "import_only_protocol_control_pending_defender_state_v3"
)
DEFAULT_TIMEOUT_SECONDS = 1100.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if not hmac.compare_digest(sha256_file(REJECTED_V2_PATH), REJECTED_V2_SHA256):
    raise RuntimeError("reviewed rejected v2 finalizer changed before dependency load")
SPEC = importlib.util.spec_from_file_location("rejected_pending_defender_v2", REJECTED_V2_PATH)
assert SPEC is not None and SPEC.loader is not None
rejected_v2 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = rejected_v2
SPEC.loader.exec_module(rejected_v2)


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


REQUIRED_EXACT_FALSE = {
    "report": (
        "defender_queried_by_this_control",
        "defender_changed_by_this_control",
        "candidate_promoted",
        "production_routing_changed",
    ),
    "hello": (
        "production_routing_authorized",
        "generic_voice_used",
        "sapi_voice_used",
        "fallback_used",
        "playback",
        "model_loaded",
    ),
    "load_import_only": (
        "cuda_api_invoked",
        "torchaudio_imported",
        "chatterbox_imported",
        "model_loaded",
        "audio_generated",
        "playback_performed",
        "ollama_invoked",
        "production_routing_authorized",
        "generic_voice_used",
        "sapi_voice_used",
        "fallback_used",
        "playback",
    ),
}

PROHIBITED_KEY_UNION = tuple(
    dict.fromkeys(
        key
        for keys in REQUIRED_EXACT_FALSE.values()
        for key in keys
    )
) + (
    "defender_queried",
    "defender_changed",
)


def classify_prohibited_outcomes_strict(report: dict[str, Any]) -> dict[str, Any]:
    payloads = {
        "report": report,
        "hello": report.get("hello") if isinstance(report.get("hello"), dict) else {},
        "load_import_only": (
            report.get("load_import_only")
            if isinstance(report.get("load_import_only"), dict)
            else {}
        ),
    }
    nonfalse_truthy: list[str] = []
    invalid_or_missing: list[str] = []
    for source_name, keys in REQUIRED_EXACT_FALSE.items():
        payload = payloads[source_name]
        for key in keys:
            if key not in payload:
                invalid_or_missing.append(f"{source_name}.{key}:missing")
                continue
            value = payload[key]
            if value is False:
                continue
            if bool(value):
                nonfalse_truthy.append(f"{source_name}.{key}:{value!r}")
            else:
                invalid_or_missing.append(f"{source_name}.{key}:{value!r}")
    for source_name, payload in payloads.items():
        for key in PROHIBITED_KEY_UNION:
            if key not in payload:
                continue
            value = payload[key]
            if value is False:
                continue
            entry = f"{source_name}.{key}:{value!r}"
            if bool(value):
                if entry not in nonfalse_truthy:
                    nonfalse_truthy.append(entry)
            elif entry not in invalid_or_missing:
                invalid_or_missing.append(entry)
    for list_name in ("phase_events_before_cleanup", "phase_events_after_cleanup"):
        events = report.get(list_name)
        if not isinstance(events, list):
            invalid_or_missing.append(f"{list_name}:missing_or_not_list")
            continue
        for index, event in enumerate(events):
            if not isinstance(event, dict):
                invalid_or_missing.append(f"{list_name}[{index}]:not_object")
                continue
            for key in PROHIBITED_KEY_UNION:
                if key in event and event[key] is not False:
                    if bool(event[key]):
                        nonfalse_truthy.append(f"{list_name}[{index}].{key}:{event[key]!r}")
                    else:
                        invalid_or_missing.append(
                            f"{list_name}[{index}].{key}:{event[key]!r}"
                        )
    if nonfalse_truthy:
        absent: bool | None = False
        status = "PROHIBITED_OR_MALFORMED_TRUTHY_VALUE_OBSERVED"
    elif invalid_or_missing:
        absent = None
        status = "UNKNOWN_MISSING_OR_NONBOOLEAN_FALSE_EVIDENCE"
    else:
        absent = True
        status = "PROHIBITED_OUTCOMES_ABSENCE_PROVEN_EXACT_FALSE"
    return {
        "prohibited_outcomes_observed": bool(nonfalse_truthy),
        "observed_truthy_or_true_fields": nonfalse_truthy,
        "invalid_or_missing_required_fields": invalid_or_missing,
        "prohibited_outcomes_evidence_complete": not nonfalse_truthy
        and not invalid_or_missing,
        "prohibited_outcomes_absent": absent,
        "prohibited_outcomes_status": status,
        "required_exact_false_contract": REQUIRED_EXACT_FALSE,
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
    raise RuntimeError("no append-only v3 import-control attempt is available")


def run_control(
    *,
    expected_candidate_config_sha256: str,
    expected_rejected_v2_sha256: str,
    expected_wrapper_sha256: str,
    expected_apply_result_sha256: str,
    expected_failed_report_sha256: str,
    expected_post_failure_check_sha256: str,
    timeout_seconds: float,
) -> tuple[Path, dict[str, Any]]:
    if not hmac.compare_digest(
        expected_rejected_v2_sha256.strip().casefold(), REJECTED_V2_SHA256
    ):
        raise ValueError("operator-bound rejected-v2 hash mismatch")
    if sha256_file(REJECTED_V2_PATH) != REJECTED_V2_SHA256:
        raise RuntimeError("reviewed rejected v2 finalizer changed")
    wrapper_hash = sha256_file(Path(__file__).resolve())
    if not hmac.compare_digest(expected_wrapper_sha256.strip().casefold(), wrapper_hash):
        raise ValueError("operator-bound v3 wrapper hash mismatch")
    predecessor = rejected_v2.predecessor
    hashes = predecessor.strict_base.exact_candidate_hashes()
    if hashes != predecessor.strict_base.EXPECTED_BASELINE_HASHES:
        raise RuntimeError("restored candidate hashes changed")
    if not hmac.compare_digest(
        expected_candidate_config_sha256.strip().casefold(), hashes["candidate_config"]
    ):
        raise ValueError("operator-bound candidate config hash mismatch")
    apply_result = predecessor.validate_apply_exit_record(expected_apply_result_sha256)
    failed_bindings = rejected_v2.validate_failed_attempt_bindings(
        expected_failed_report_sha256,
        expected_post_failure_check_sha256,
    )
    blender = predecessor.strict_base.no_active_blender_evidence()
    if blender.get("query_succeeded") is not True or blender.get("active") is not False:
        raise RuntimeError(f"no-active-Blender gate failed: {blender}")
    attempt = allocate_attempt_directory()
    marker_path = attempt / "ATTEMPT_STARTED.json"
    report_path = attempt / "PROTOCOL_IMPORT_ONLY_PENDING_DEFENDER_STATE_V3.json"
    marker_hash = predecessor.strict_base.write_json_exclusive(
        marker_path,
        {
            "schema_version": 3,
            "artifact_kind": "protocol_import_only_pending_defender_state_v3_started",
            "candidate_hashes": hashes,
            "rejected_v2_sha256": REJECTED_V2_SHA256,
            "wrapper_sha256": wrapper_hash,
            "apply_result": apply_result,
            "failed_attempt_bindings": failed_bindings,
            "independent_defender_state": predecessor.UNKNOWN_STATE,
        },
    )
    report: dict[str, Any] = {
        "schema_version": 3,
        "artifact_kind": "persistent_blackwell_protocol_import_only_pending_defender_state_v3",
        "status": "started",
        "candidate_hashes": hashes,
        "rejected_v2_binding": {
            "path": relative(REJECTED_V2_PATH),
            "sha256": REJECTED_V2_SHA256,
            "status": "REJECTED_STATIC_EVIDENCE_DO_NOT_RUN",
        },
        "wrapper_sha256": wrapper_hash,
        "apply_result": apply_result,
        "failed_attempt_bindings": failed_bindings,
        "independent_defender_state": predecessor.UNKNOWN_STATE,
        "exclusion_present_claimed": False,
        "monitoring_enabled_claimed_from_independent_evidence": False,
        "latency_improvement_claimed": False,
        "defender_causality_claimed": False,
        "production_voice_acceptance_claimed": False,
        "attempt_started_marker": {"path": relative(marker_path), "sha256": marker_hash},
        "no_active_blender": blender,
        "timeout_seconds": timeout_seconds,
        "defender_queried_by_this_control": False,
        "defender_changed_by_this_control": False,
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
        report["cleanup_observation"] = rejected_v2.close_client_with_observation(client)
        report["phase_events_after_cleanup"] = client.events if client is not None else []
        report["candidate_hashes_after"] = predecessor.strict_base.exact_candidate_hashes()
        report["candidate_unchanged"] = (
            report["candidate_hashes_after"] == predecessor.strict_base.EXPECTED_BASELINE_HASHES
        )
        report.update(classify_prohibited_outcomes_strict(report))
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


def complete_safe_fixture() -> dict[str, Any]:
    return {
        "defender_queried_by_this_control": False,
        "defender_changed_by_this_control": False,
        "candidate_promoted": False,
        "production_routing_changed": False,
        "hello": {
            "production_routing_authorized": False,
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "playback": False,
            "model_loaded": False,
        },
        "load_import_only": {
            "cuda_api_invoked": False,
            "torchaudio_imported": False,
            "chatterbox_imported": False,
            "model_loaded": False,
            "audio_generated": False,
            "playback_performed": False,
            "ollama_invoked": False,
            "production_routing_authorized": False,
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "playback": False,
        },
        "phase_events_before_cleanup": [],
        "phase_events_after_cleanup": [],
    }


def static_self_check() -> dict[str, Any]:
    safe = classify_prohibited_outcomes_strict(complete_safe_fixture())
    missing = classify_prohibited_outcomes_strict({})
    malformed = complete_safe_fixture()
    malformed["load_import_only"]["cuda_api_invoked"] = 0
    malformed_result = classify_prohibited_outcomes_strict(malformed)
    truthy = complete_safe_fixture()
    truthy["hello"]["generic_voice_used"] = "false"
    truthy_result = classify_prohibited_outcomes_strict(truthy)
    misplaced = complete_safe_fixture()
    misplaced["hello"]["cuda_api_invoked"] = True
    misplaced_result = classify_prohibited_outcomes_strict(misplaced)
    malformed_events = complete_safe_fixture()
    malformed_events["phase_events_after_cleanup"] = {}
    malformed_events_result = classify_prohibited_outcomes_strict(malformed_events)
    source = Path(__file__).read_text(encoding="utf-8")
    checks = {
        "rejected_v2_exact": sha256_file(REJECTED_V2_PATH) == REJECTED_V2_SHA256,
        "safe_complete_exact_false_passes": safe["prohibited_outcomes_absent"] is True,
        "missing_is_unknown": missing["prohibited_outcomes_absent"] is None,
        "falsey_nonbool_is_unknown": malformed_result["prohibited_outcomes_absent"] is None,
        "truthy_nonbool_fails_closed": truthy_result["prohibited_outcomes_absent"] is False,
        "misplaced_prohibited_key_fails_closed": misplaced_result[
            "prohibited_outcomes_absent"
        ]
        is False,
        "malformed_event_container_is_unknown": malformed_events_result[
            "prohibited_outcomes_absent"
        ]
        is None,
        "promotion_and_route_required": all(
            key in REQUIRED_EXACT_FALSE["report"]
            for key in ("candidate_promoted", "production_routing_changed")
        ),
        "voice_and_auth_fields_required": all(
            key in REQUIRED_EXACT_FALSE["hello"]
            for key in (
                "production_routing_authorized",
                "generic_voice_used",
                "sapi_voice_used",
                "fallback_used",
            )
        ),
        "no_defender_command": not any(
            marker in source
            for marker in (
                "Get" + "-MpPreference",
                "Add" + "-MpPreference",
                "Remove" + "-MpPreference",
                "Set" + "-MpPreference",
            )
        ),
        "no_torch_cuda_model_audio": not any(
            marker in source
            for marker in (
                "torch." + "cuda",
                "from_" + "pretrained(",
                "winsound." + "PlaySound(",
                "sounddevice." + "play(",
            )
        ),
        "no_promotion_route_functions": not any(
            marker in source
            for marker in (
                "promote_" + "candidate(",
                "activate_" + "candidate(",
                "set_production_" + "route(",
            )
        ),
    }
    return {
        "schema_version": 3,
        "artifact_kind": "pending_defender_import_control_v3_static_self_check",
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


def describe() -> dict[str, Any]:
    return {
        "schema_version": 3,
        "artifact_kind": "pending_defender_import_control_v3_description",
        "status": "STRICT_BOOLEAN_FINALIZATION_PREPARED_NOT_EXECUTED",
        "rejected_v2_path": relative(REJECTED_V2_PATH),
        "rejected_v2_sha256": REJECTED_V2_SHA256,
        "required_exact_false_contract": REQUIRED_EXACT_FALSE,
        "independent_defender_state": rejected_v2.predecessor.UNKNOWN_STATE,
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
    parser.add_argument("--expected-rejected-v2-sha256", default="")
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
    report_path, report = run_control(
        expected_candidate_config_sha256=args.expected_candidate_config_sha256,
        expected_rejected_v2_sha256=args.expected_rejected_v2_sha256,
        expected_wrapper_sha256=args.expected_wrapper_sha256,
        expected_apply_result_sha256=args.expected_apply_result_sha256,
        expected_failed_report_sha256=args.expected_failed_report_sha256,
        expected_post_failure_check_sha256=args.expected_post_failure_check_sha256,
        timeout_seconds=max(300.0, min(1500.0, float(args.timeout_seconds))),
    )
    print(
        json.dumps(
            {
                "report": relative(report_path),
                "report_sha256": sha256_file(report_path),
                "status": report["status"],
                "passed": report["passed"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
