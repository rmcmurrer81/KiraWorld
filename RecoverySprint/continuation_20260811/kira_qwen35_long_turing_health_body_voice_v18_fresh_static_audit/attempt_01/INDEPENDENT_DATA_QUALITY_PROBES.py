#!/usr/bin/env python3
"""Read-only, inert data-quality probes for the installed Long V18 package.

This script imports only the sealed static validator and its fixture module. It
does not call either entry point and does not use any model, device, private
state, person, body, media, network, or one-hour route.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import types
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

KIRA = Path(r"C:\Users\robmc\Kira")
ATTEMPT = (
    KIRA
    / "RecoverySprint"
    / "continuation_20260811"
    / "kira_qwen35_long_turing_health_body_voice_preparation_v18"
    / "attempt_01"
)
SOURCE = KIRA / "tools" / "run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v18.py"
TEST = KIRA / "Testing" / "test_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v18.py"
PLAN = ATTEMPT / "EXECUTION_PLAN_V18.json"
SOURCE_ROOT = ATTEMPT / "SOURCE_CODE_ROOT_V18.json"
AUTHOR_RESULT = ATTEMPT / "AUTHOR_STATIC_TEST_RESULT.json"
SEAL = ATTEMPT / "STATIC_SEAL_MANIFEST.json"
CHECKPOINT = ATTEMPT / "CHECKPOINT.md"
V17_TEST = KIRA / "Testing" / "test_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v17.py"


def _load(path: Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load static module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_record(path: Path) -> dict[str, Any]:
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": _sha256(path)}


def _audio_proxy_row() -> dict[str, Any]:
    return {
        "schema_version": 18,
        "metric_receipt_id": "metric-proxy",
        "turn_id": "turn-1",
        "timestamp_unit": "MONOTONIC_NANOSECONDS",
        "displayed_text_event_id": "display-1",
        "displayed_text_ns": 100,
        "playback_api_call_start_event_id": "playback-1",
        "playback_api_call_start_ns": 150,
        "device_first_sample_event_id": None,
        "device_first_sample_ns": None,
        "owner_observed_audible_event_id": None,
        "owner_observed_audible_ns": None,
        "owner_observer_person_id": None,
        "owner_observation_receipt_sha256": None,
        "measurement_basis": "PLAYBACK_API_PROXY_ONLY",
        "displayed_text_to_playback_api_proxy_ns": 50,
        "displayed_text_to_device_first_sample_ns": None,
        "displayed_text_to_owner_observed_audible_ns": None,
    }


def main() -> int:
    v18 = _load(SOURCE, "_long_v18_independent_data_review_subject")
    fixtures = _load(V17_TEST, "_long_v18_independent_data_review_fixtures")

    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    source_root = json.loads(SOURCE_ROOT.read_text(encoding="utf-8"))
    sealed_rows: list[dict[str, Any]] = []
    for subject in seal["subjects"]:
        path = KIRA / subject["path"]
        actual = _file_record(path)
        sealed_rows.append(
            {
                "path": subject["path"],
                "expected_bytes": subject["bytes"],
                "actual_bytes": actual["bytes"],
                "expected_sha256": subject["sha256"],
                "actual_sha256": actual["sha256"],
                "exact": actual["bytes"] == subject["bytes"] and actual["sha256"] == subject["sha256"],
            }
        )

    plan = v18.load_and_validate_v18_contract()
    closure_issues = v18.exact_bound_closure_issues(
        plan,
        KIRA,
        Path(r"C:\Users\robmc\Documents\Codex\2026-08-11\c\work\long_v17_fresh_audit"),
    )

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    suite = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(TEST)],
        cwd=str(Path(r"C:\Users\robmc\Documents\Codex\2026-08-11\c\work")),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    mutable_row = _audio_proxy_row()
    mutable_row["unreviewed_extension"] = "accepted only after ordinary module reassignment"
    mutable_before = v18.audio_measurement_receipt_issues(mutable_row)
    original_audio_keys = v18.AUDIO_MEASUREMENT_KEYS
    try:
        v18.AUDIO_MEASUREMENT_KEYS = frozenset(set(original_audio_keys) | {"unreviewed_extension"})
        mutable_after = v18.audio_measurement_receipt_issues(mutable_row)
    finally:
        v18.AUDIO_MEASUREMENT_KEYS = original_audio_keys

    bool_row = _audio_proxy_row()
    bool_row["playback_api_call_start_ns"] = 101
    bool_row["displayed_text_to_playback_api_proxy_ns"] = True
    bool_issues = v18.audio_measurement_receipt_issues(bool_row)

    camera_results: dict[str, Any] = {}
    source = fixtures._make_trial("ON", 1, "SECOND")
    prefix = tuple(fixtures.v17.ON_TIMESTAMP_ORDER).index("vision_inference_start")
    for outcome in ("FAILURE", "TIMEOUT"):
        reason = "VISION_INFERENCE_FAILED" if outcome == "FAILURE" else "VISION_INFERENCE_TIMEOUT"
        baseline = v18.make_camera_outcome_record(source, outcome, prefix, reason)
        variants: dict[str, Any] = {}
        for variant in ("authorized_after_terminal", "expired_before_enable", "expires_before_authorized"):
            row = copy.deepcopy(baseline)
            consent = row["consent_receipt"]
            if variant == "authorized_after_terminal":
                consent["authorized_at_ns"] = row["terminal_trace"]["terminal_event_ns"] + 1000
                consent["expires_at_ns"] = consent["authorized_at_ns"] + 1
            elif variant == "expired_before_enable":
                consent["authorized_at_ns"] = 1
                consent["expires_at_ns"] = 2
            else:
                consent["authorized_at_ns"] = 1000
                consent["expires_at_ns"] = 999
            consent["authorization_receipt_sha256"] = fixtures.v17.canonical_camera_authorization_receipt_sha256(consent)
            variants[variant] = {
                "supplied_authorized_at_ns": consent["authorized_at_ns"],
                "supplied_expires_at_ns": consent["expires_at_ns"],
                "terminal_event_ns": row["terminal_trace"]["terminal_event_ns"],
                "issues": v18.camera_trial_outcome_issues(row),
            }
        camera_results[outcome] = {
            "baseline_issues": v18.camera_trial_outcome_issues(baseline),
            "variants": variants,
        }

    scoring_fields = v18.expected_one_hour_discovery_scoring_plan()["temporary_creator_quality_fields"]
    source_text = SOURCE.read_text(encoding="utf-8")
    source_label = "tools/run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v18.py"
    descriptor = v18.exact_source_descriptor_bytes(SOURCE.read_bytes(), source_label)
    semantic_bundle = v18.semantic_verifier_bundle_descriptor_bytes()
    result = {
        "schema_version": 1,
        "artifact_kind": "long_v18_independent_data_quality_probe_result",
        "mode": "READ_ONLY_STATIC_AND_IN_MEMORY_ONLY",
        "installed_subjects": [
            _file_record(SOURCE),
            _file_record(TEST),
            _file_record(PLAN),
            _file_record(SOURCE_ROOT),
            _file_record(AUTHOR_RESULT),
            _file_record(SEAL),
            _file_record(CHECKPOINT),
        ],
        "seal": {
            "declared_subject_count": seal["subject_count"],
            "checked_subject_count": len(sealed_rows),
            "all_exact": all(row["exact"] for row in sealed_rows),
            "subjects": sealed_rows,
        },
        "input_closure": {
            "declared_count": len(plan["predecessor_rejection_and_policy_closure"]),
            "issues": closure_issues,
            "all_exact": closure_issues == [],
        },
        "external_roots": {
            "source_descriptor": {
                "expected_bytes": source_root["descriptor"]["bytes"],
                "actual_bytes": len(descriptor),
                "expected_sha256": source_root["descriptor"]["sha256"],
                "actual_sha256": hashlib.sha256(descriptor).hexdigest(),
                "exact": (
                    len(descriptor) == source_root["descriptor"]["bytes"]
                    and hashlib.sha256(descriptor).hexdigest() == source_root["descriptor"]["sha256"]
                ),
            },
            "semantic_verifier_bundle": {
                "expected_bytes": source_root["semantic_verifier_bundle"]["bytes"],
                "actual_bytes": len(semantic_bundle),
                "expected_sha256": source_root["semantic_verifier_bundle"]["sha256"],
                "actual_sha256": hashlib.sha256(semantic_bundle).hexdigest(),
                "exact": (
                    len(semantic_bundle) == source_root["semantic_verifier_bundle"]["bytes"]
                    and hashlib.sha256(semantic_bundle).hexdigest()
                    == source_root["semantic_verifier_bundle"]["sha256"]
                ),
            },
        },
        "author_suite": {
            "command": [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(TEST)],
            "returncode": suite.returncode,
            "stdout": suite.stdout.strip(),
            "cache_free": True,
        },
        "defects": {
            "ordinary_mutable_module_value_changes_rule_behavior": {
                "module_value": "AUDIO_MEASUREMENT_KEYS",
                "issues_before_reassignment": mutable_before,
                "issues_after_reassignment": mutable_after,
                "confirmed": bool(mutable_before) and mutable_after == [],
            },
            "boolean_accepted_as_exact_integer_audio_duration": {
                "field": "displayed_text_to_playback_api_proxy_ns",
                "supplied_value": True,
                "supplied_python_type": type(bool_row["displayed_text_to_playback_api_proxy_ns"]).__name__,
                "mathematical_expected_duration": 1,
                "issues": bool_issues,
                "confirmed": bool_issues == [],
            },
            "partial_camera_normalization_replaces_consent_before_validation": {
                "source_lines": [1063, 1064, 1065, 1066, 1067],
                "outcomes": camera_results,
                "confirmed": all(
                    item["issues"] == []
                    for outcome_row in camera_results.values()
                    for item in outcome_row["variants"].values()
                ),
            },
        },
        "creator_scoring": {
            "field_count": len(scoring_fields),
            "fields": scoring_fields,
            "policy_files_bound_exactly": True,
            "dedicated_creator_result_row_validator_present": "temporary_creator_quality_row_issues" in source_text,
            "only_field_list_schema_validator_present": "one_hour_discovery_scoring_plan_issues" in source_text,
        },
        "scope": {
            "entry_points_invoked": False,
            "model_camera_microphone_audio_private_body_media_network_or_one_hour_route_invoked": False,
            "kira_written": False,
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if suite.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
