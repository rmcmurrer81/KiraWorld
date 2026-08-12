#!/usr/bin/env python3
"""Append-only v2 controller for the 36-turn unattended Kira evaluation.

This successor keeps the sealed v1 content plan and retained execution gates,
replaces only the retained historical six-turn final-count invariant, adds an
exact 37-generation-cap invariant, and gives unattended execution a truthful
owner-authorization flag. It is inert unless every mode-appropriate flag is
present and a different fresh auditor has authorized the exact bytes.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation as v1
from tools import run_qwen35_kira_turing_psych_voice_owner_evaluation as retained


V2_PLAN_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "kira_qwen35_long_turing_health_body_voice_preparation_v2"
    / "attempt_01"
    / "EXECUTION_PLAN_V2.json"
)
V2_PLAN_SHA256 = "696f7c16e6911d48e213677878bb404b0b5ceba9a0978f76c6dd438267f1e928"
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v2"
)
GENERATED_ROOT = (
    ROOT
    / "Voice"
    / "generated"
    / "acceptance"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v2"
)
HARNESS_ID = "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v2"
ONLY_ATTEMPT_LABEL = "attempt_01"
UNATTENDED_MARKER = "--unattended-log-only"
UNATTENDED_AUTHORIZATION_FLAG = "--confirm-owner-authorized-unattended-log-review"
LEGACY_SUPERVISION_FLAG = "--confirm-owner-supervised"
CHILD_WATCHDOG_SECONDS = 5100.0
PARENT_TIMEOUT_SECONDS = 5250.0
SEALED_MAXIMUM_SECONDS = 5400.0
EXPECTED_TURN_COUNT = 36
EXPECTED_GENERATION_CAP = 37
LEGACY_COUNT_ISSUE = "measured_turn_count_not_six"
V2_COUNT_ISSUE = "measured_turn_count_not_exact_plan_36"
V2_CAP_ISSUE = "maximum_qwen_generation_cap_not_exact_plan_37"

V2_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "artifact_kind",
        "status",
        "base_plan",
        "owner_authorization",
        "timeouts",
        "final_validator",
        "execution_roots",
    }
)
BASE_PLAN_KEYS = frozenset(
    {
        "path",
        "sha256",
        "expected_turn_count",
        "expected_battery_count",
        "expected_generation_cap",
    }
)
AUTHORIZATION_KEYS = frozenset(
    {
        "mode",
        "required_public_flag",
        "unattended_marker",
        "legacy_supervision_flag",
        "legacy_supervision_flag_allowed_in_unattended_mode",
        "interactive_mode_preserves_legacy_supervision_flag",
        "owner_present_for_unattended_run",
        "owner_hearing_may_be_claimed",
        "exact_owner_instruction",
        "owner_instruction_date",
        "scope",
    }
)
TIMEOUT_KEYS = frozenset(
    {
        "sealed_plan_maximum_seconds",
        "child_watchdog_seconds",
        "parent_timeout_seconds",
        "parent_exceeds_child",
    }
)
VALIDATOR_KEYS = frozenset(
    {
        "legacy_count_issue_replaced",
        "exact_turn_count_issue",
        "exact_generation_cap_issue",
        "all_other_retained_issues_preserved",
        "turn_order_and_identity_remain_retained_gates",
    }
)
EXECUTION_ROOT_KEYS = frozenset(
    {
        "evidence_root",
        "generated_root",
        "only_permitted_attempt_label",
        "append_only_reservation_required",
    }
)


class LongEvaluationV2Error(RuntimeError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _strict_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LongEvaluationV2Error(f"duplicate JSON key:{key}")
        result[key] = value
    return result


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    if set(value) != set(expected):
        raise LongEvaluationV2Error(f"{label} keys drifted")


def load_and_validate_v2_contract() -> tuple[dict[str, Any], dict[str, Any]]:
    raw = V2_PLAN_PATH.read_bytes()
    if _sha256_bytes(raw) != V2_PLAN_SHA256:
        raise LongEvaluationV2Error("v2 execution plan hash drifted")
    try:
        execution = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LongEvaluationV2Error("v2 execution plan is not strict UTF-8 JSON") from exc
    if not isinstance(execution, dict):
        raise LongEvaluationV2Error("v2 execution plan is not an object")
    _exact_keys(execution, V2_TOP_LEVEL_KEYS, "v2 plan")
    if execution.get("schema_version") != 2:
        raise LongEvaluationV2Error("v2 schema drifted")
    if execution.get("artifact_kind") != (
        "kira_qwen35_long_turing_health_body_voice_execution_plan_v2"
    ):
        raise LongEvaluationV2Error("v2 artifact kind drifted")
    if execution.get("status") != "STATIC_SUCCESSOR_NOT_EXECUTED":
        raise LongEvaluationV2Error("v2 status drifted")

    base_binding = execution.get("base_plan")
    authorization = execution.get("owner_authorization")
    timeouts = execution.get("timeouts")
    validator = execution.get("final_validator")
    roots = execution.get("execution_roots")
    if not all(
        isinstance(value, dict)
        for value in (base_binding, authorization, timeouts, validator, roots)
    ):
        raise LongEvaluationV2Error("v2 contract objects are malformed")
    assert isinstance(base_binding, dict)
    assert isinstance(authorization, dict)
    assert isinstance(timeouts, dict)
    assert isinstance(validator, dict)
    assert isinstance(roots, dict)
    _exact_keys(base_binding, BASE_PLAN_KEYS, "base plan")
    _exact_keys(authorization, AUTHORIZATION_KEYS, "owner authorization")
    _exact_keys(timeouts, TIMEOUT_KEYS, "timeouts")
    _exact_keys(validator, VALIDATOR_KEYS, "final validator")
    _exact_keys(roots, EXECUTION_ROOT_KEYS, "execution roots")

    expected_base = v1.PLAN_PATH.resolve().relative_to(ROOT.resolve()).as_posix()
    if base_binding.get("path") != expected_base:
        raise LongEvaluationV2Error("base plan path drifted")
    if base_binding.get("sha256") != v1.PLAN_SHA256:
        raise LongEvaluationV2Error("base plan hash binding drifted")
    base_plan = v1.load_and_validate_plan()
    turns = base_plan.get("turns")
    if not isinstance(turns, list) or len(turns) != EXPECTED_TURN_COUNT:
        raise LongEvaluationV2Error("effective plan is not exactly 36 turns")
    batteries = {str(row.get("battery") or "") for row in turns if isinstance(row, dict)}
    if len(batteries) != 6:
        raise LongEvaluationV2Error("effective plan is not exactly six batteries")
    if base_plan.get("model", {}).get("maximum_generations") != EXPECTED_GENERATION_CAP:
        raise LongEvaluationV2Error("effective generation cap is not 37")
    expected_base_values = {
        "expected_turn_count": EXPECTED_TURN_COUNT,
        "expected_battery_count": 6,
        "expected_generation_cap": EXPECTED_GENERATION_CAP,
    }
    for key, value in expected_base_values.items():
        if base_binding.get(key) != value:
            raise LongEvaluationV2Error(f"base plan invariant drifted:{key}")

    expected_authorization = {
        "mode": "owner_authorized_unattended_log_review",
        "required_public_flag": UNATTENDED_AUTHORIZATION_FLAG,
        "unattended_marker": UNATTENDED_MARKER,
        "legacy_supervision_flag": LEGACY_SUPERVISION_FLAG,
        "legacy_supervision_flag_allowed_in_unattended_mode": False,
        "interactive_mode_preserves_legacy_supervision_flag": True,
        "owner_present_for_unattended_run": False,
        "owner_hearing_may_be_claimed": False,
        "exact_owner_instruction": (
            "Do the test without me I trust you and I can read the log later."
        ),
        "owner_instruction_date": "2026-08-10",
    }
    for key, value in expected_authorization.items():
        if authorization.get(key) != value:
            raise LongEvaluationV2Error(f"owner authorization drifted:{key}")
    if "attempt_01" not in str(authorization.get("scope") or ""):
        raise LongEvaluationV2Error("owner authorization scope is not attempt_01")

    expected_timeouts = {
        "sealed_plan_maximum_seconds": int(SEALED_MAXIMUM_SECONDS),
        "child_watchdog_seconds": int(CHILD_WATCHDOG_SECONDS),
        "parent_timeout_seconds": int(PARENT_TIMEOUT_SECONDS),
        "parent_exceeds_child": True,
    }
    for key, value in expected_timeouts.items():
        if timeouts.get(key) != value:
            raise LongEvaluationV2Error(f"timeout binding drifted:{key}")
    if not (
        0 < CHILD_WATCHDOG_SECONDS < PARENT_TIMEOUT_SECONDS <= SEALED_MAXIMUM_SECONDS
    ):
        raise LongEvaluationV2Error("timeouts exceed the sealed maximum")

    expected_validator = {
        "legacy_count_issue_replaced": LEGACY_COUNT_ISSUE,
        "exact_turn_count_issue": V2_COUNT_ISSUE,
        "exact_generation_cap_issue": V2_CAP_ISSUE,
        "all_other_retained_issues_preserved": True,
        "turn_order_and_identity_remain_retained_gates": True,
    }
    for key, value in expected_validator.items():
        if validator.get(key) != value:
            raise LongEvaluationV2Error(f"final validator binding drifted:{key}")

    expected_roots = {
        "evidence_root": EVIDENCE_ROOT.resolve().relative_to(ROOT.resolve()).as_posix(),
        "generated_root": GENERATED_ROOT.resolve().relative_to(ROOT.resolve()).as_posix(),
        "only_permitted_attempt_label": ONLY_ATTEMPT_LABEL,
        "append_only_reservation_required": True,
    }
    for key, value in expected_roots.items():
        if roots.get(key) != value:
            raise LongEvaluationV2Error(f"execution root binding drifted:{key}")
    return execution, base_plan


_ORIGINAL_FINAL_VALIDATOR: Callable[[Mapping[str, Any]], list[str]] = getattr(
    retained,
    "_kira_long_v2_original_final_validator",
    retained.final_run_contract_issues,
)
if not hasattr(retained, "_kira_long_v2_original_final_validator"):
    retained._kira_long_v2_original_final_validator = _ORIGINAL_FINAL_VALIDATOR

_ORIGINAL_OWNER_ACKNOWLEDGMENT = getattr(
    retained,
    "_kira_long_v2_original_owner_acknowledgment",
    retained.collect_post_playback_owner_acknowledgment,
)
if not hasattr(retained, "_kira_long_v2_original_owner_acknowledgment"):
    retained._kira_long_v2_original_owner_acknowledgment = (
        _ORIGINAL_OWNER_ACKNOWLEDGMENT
    )

_ORIGINAL_REQUIRED_PUBLIC_FLAGS = tuple(
    getattr(
        retained,
        "_kira_long_v2_original_required_public_flags",
        retained.REQUIRED_PUBLIC_FLAGS,
    )
)
if not hasattr(retained, "_kira_long_v2_original_required_public_flags"):
    retained._kira_long_v2_original_required_public_flags = (
        _ORIGINAL_REQUIRED_PUBLIC_FLAGS
    )


def v2_final_run_contract_issues(report: Mapping[str, Any]) -> list[str]:
    """Preserve all retained gates while replacing only its six-turn invariant."""

    retained_issues = list(_ORIGINAL_FINAL_VALIDATOR(report))
    issues = [item for item in retained_issues if item != LEGACY_COUNT_ISSUE]
    configured_turns = retained.prepared.EVALUATION_TURNS
    if len(configured_turns) != EXPECTED_TURN_COUNT:
        issues.append("configured_plan_turn_count_not_exact_36")
    observed_turns = report.get("turns")
    observed_turns = observed_turns if isinstance(observed_turns, list) else []
    if len(observed_turns) != EXPECTED_TURN_COUNT:
        issues.append(V2_COUNT_ISSUE)
    if retained.MAX_TOTAL_QWEN_REQUESTS != EXPECTED_GENERATION_CAP:
        issues.append(V2_CAP_ISSUE)
    return sorted(set(issues))


def _unattended_owner_acknowledgment(_: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "required": True,
        "requested": False,
        "acknowledged": False,
        "reason": "owner_not_present_owner_authorized_unattended_log_review",
        "authorization_flag": UNATTENDED_AUTHORIZATION_FLAG,
        "physical_supervision_claimed": False,
        "evidence_scope": retained.prepared.OWNER_POST_PLAYBACK_ACKNOWLEDGMENT[
            "evidence_scope"
        ],
    }


def _unattended_required_flags() -> tuple[str, ...]:
    flags = tuple(
        flag for flag in _ORIGINAL_REQUIRED_PUBLIC_FLAGS if flag != LEGACY_SUPERVISION_FLAG
    )
    if UNATTENDED_AUTHORIZATION_FLAG not in flags:
        flags = (*flags, UNATTENDED_AUTHORIZATION_FLAG)
    return flags


def classify_invocation_mode(incoming: Sequence[str]) -> bool:
    marker = UNATTENDED_MARKER in incoming
    authorization = UNATTENDED_AUTHORIZATION_FLAG in incoming
    legacy_supervision = LEGACY_SUPERVISION_FLAG in incoming
    child = "--child-run" in incoming
    if marker:
        if not authorization:
            raise LongEvaluationV2Error(
                "unattended mode requires exact owner-authorized log-review flag"
            )
        if legacy_supervision:
            raise LongEvaluationV2Error(
                "unattended mode must not claim physical owner supervision"
            )
        return True
    if child and authorization:
        if legacy_supervision:
            raise LongEvaluationV2Error(
                "unattended child must not claim physical owner supervision"
            )
        return True
    if authorization:
        raise LongEvaluationV2Error(
            "unattended authorization flag requires --unattended-log-only"
        )
    return False


def _argument_value(argv: Sequence[str], flag: str, default: str = "") -> str:
    for index, value in enumerate(argv):
        if value == flag and index + 1 < len(argv):
            return argv[index + 1]
    return default


def validate_attempt_binding(incoming: Sequence[str]) -> None:
    child = "--child-run" in incoming
    if child:
        attempt_path = Path(_argument_value(incoming, "--attempt-path")).resolve()
        generated_path = Path(_argument_value(incoming, "--generated-path")).resolve()
        if attempt_path.name != ONLY_ATTEMPT_LABEL or generated_path.name != ONLY_ATTEMPT_LABEL:
            raise LongEvaluationV2Error("v2 child attempt is not exact attempt_01")
        return
    label = _argument_value(incoming, "--attempt-label", ONLY_ATTEMPT_LABEL)
    if label != ONLY_ATTEMPT_LABEL:
        raise LongEvaluationV2Error("v2 permits only append-only attempt_01")


def configure_retained_runner_v2(
    execution: Mapping[str, Any],
    base_plan: Mapping[str, Any],
    *,
    unattended: bool,
) -> None:
    del execution
    v1.configure_retained_runner(base_plan)
    retained.__file__ = str(Path(__file__).resolve())
    retained.HARNESS_ID = HARNESS_ID
    retained.EVIDENCE_ROOT = EVIDENCE_ROOT
    retained.GENERATED_ROOT = GENERATED_ROOT
    retained.PREPARATION_ARTIFACT = V2_PLAN_PATH
    retained.MAX_TOTAL_QWEN_REQUESTS = EXPECTED_GENERATION_CAP
    retained.CHILD_WATCHDOG_SECONDS = CHILD_WATCHDOG_SECONDS
    retained.PARENT_TIMEOUT_SECONDS = PARENT_TIMEOUT_SECONDS
    retained.canonical_preparation_bytes = lambda: V2_PLAN_PATH.read_bytes()
    retained.load_preparation_contract = lambda: load_and_validate_v2_contract()[0]
    retained.preparation_contract_issues = (
        lambda observed: []
        if dict(observed) == load_and_validate_v2_contract()[0]
        else ["v2_execution_plan_drifted"]
    )
    retained.final_run_contract_issues = v2_final_run_contract_issues
    if unattended:
        retained.REQUIRED_PUBLIC_FLAGS = _unattended_required_flags()
        retained.collect_post_playback_owner_acknowledgment = (
            _unattended_owner_acknowledgment
        )
    else:
        retained.REQUIRED_PUBLIC_FLAGS = _ORIGINAL_REQUIRED_PUBLIC_FLAGS
        retained.collect_post_playback_owner_acknowledgment = (
            _ORIGINAL_OWNER_ACKNOWLEDGMENT
        )


def main(argv: Sequence[str] | None = None) -> int:
    incoming = list(sys.argv[1:] if argv is None else argv)
    unattended = classify_invocation_mode(incoming)
    validate_attempt_binding(incoming)
    execution, base_plan = load_and_validate_v2_contract()
    configure_retained_runner_v2(execution, base_plan, unattended=unattended)
    forwarded = [value for value in incoming if value != UNATTENDED_MARKER]
    base_exit = retained.main(forwarded)
    if not unattended:
        return int(base_exit)

    attempt = EVIDENCE_ROOT / ONLY_ATTEMPT_LABEL
    final = attempt / "FINAL_REPORT.json"
    parent_wrapper_path = attempt / "PARENT_WRAPPER.json"
    try:
        child_report = json.loads(
            final.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
        )
        parent_wrapper = json.loads(
            parent_wrapper_path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
        )
    except (OSError, json.JSONDecodeError):
        return int(base_exit)
    if not isinstance(child_report, dict) or not isinstance(parent_wrapper, dict):
        return int(base_exit)
    expected_ids = [row["id"] for row in base_plan["turns"]]
    observed_turns = child_report.get("turns")
    observed_turns = observed_turns if isinstance(observed_turns, list) else []
    acknowledgment = parent_wrapper.get("owner_post_playback_acknowledgment")
    acknowledgment = acknowledgment if isinstance(acknowledgment, dict) else {}
    technical_complete = bool(
        child_report.get("engineering_pass") is True
        and child_report.get("speaker_playback_completed") is True
        and child_report.get("owner_post_playback_acknowledged") is False
        and parent_wrapper.get("process_gate_passed") is True
        and parent_wrapper.get("parent_report_contract_issues") == []
        and acknowledgment.get("acknowledged") is False
        and acknowledgment.get("physical_supervision_claimed") is False
        and len(observed_turns) == EXPECTED_TURN_COUNT
        and [row.get("turn_id") for row in observed_turns if isinstance(row, dict)]
        == expected_ids
    )
    print(
        json.dumps(
            {
                "unattended_log_only": True,
                "owner_authorized_unattended_log_review": True,
                "physical_owner_supervision_claimed": False,
                "parent_process_gate_passed": parent_wrapper.get(
                    "process_gate_passed"
                )
                is True,
                "technical_engineering_and_playback_complete": technical_complete,
                "owner_hearing_acknowledged": False,
                "owner_hearing_pending": True,
                "attempt": attempt.resolve().relative_to(ROOT.resolve()).as_posix(),
            },
            indent=2,
        )
    )
    return 0 if technical_complete else int(base_exit)


if __name__ == "__main__":
    raise SystemExit(main())
