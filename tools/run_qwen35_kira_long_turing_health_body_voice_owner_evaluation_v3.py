#!/usr/bin/env python3
"""Append-only v3 controller for the bounded long Kira evaluation.

V3 preserves the exact source-backed v1 content and all retained execution
gates while omitting one redundant reflection turn. One voluntary invitation
plus 35 measured turns fits the unchanged retained SafeOllamaClient maximum of
36. The controller is inert unless every mode-appropriate capability is
present, and no live attempt is authorized until a different fresh auditor
accepts the exact sealed v3 bytes.
"""

from __future__ import annotations

import copy
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
from tools import run_qwen_text_voice_acceptance as client_source


V3_PLAN_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "kira_qwen35_long_turing_health_body_voice_preparation_v3"
    / "attempt_01"
    / "EXECUTION_PLAN_V3.json"
)
V3_PLAN_SHA256 = "dcba9b9dc9e7d48d5d1ef046c95f7e0c446c12b7b1950dc23fab3b43a0819b08"
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v3"
)
GENERATED_ROOT = (
    ROOT
    / "Voice"
    / "generated"
    / "acceptance"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v3"
)
HARNESS_ID = "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v3"
ONLY_ATTEMPT_LABEL = "attempt_01"
UNATTENDED_MARKER = "--unattended-log-only"
UNATTENDED_AUTHORIZATION_FLAG = "--confirm-owner-authorized-unattended-log-review"
LEGACY_SUPERVISION_FLAG = "--confirm-owner-supervised"
CHILD_WATCHDOG_SECONDS = 5100.0
PARENT_TIMEOUT_SECONDS = 5250.0
SEALED_MAXIMUM_SECONDS = 5400.0
ORIGINAL_TURN_COUNT = 36
EXPECTED_TURN_COUNT = 35
EXPECTED_GENERATION_CAP = 36
EXPECTED_BATTERY_COUNT = 6
OMITTED_TURN_ID = "natural_close_reading"
OMITTED_TURN_BATTERY = "NATURAL_CONVERSATION"
OMITTED_TURN_TEXT_SHA256 = "4b2f17b36e00750ae32ddc9139a33c864061acde966f4e4952c47164563765e8"
LEGACY_COUNT_ISSUE = "measured_turn_count_not_six"
V3_CONFIGURED_COUNT_ISSUE = "configured_plan_turn_count_not_exact_35"
V3_COUNT_ISSUE = "measured_turn_count_not_exact_plan_35"
V3_CAP_ISSUE = "maximum_qwen_generation_cap_not_exact_plan_36"
CLIENT_SOURCE_PATH = ROOT / "tools" / "run_qwen_text_voice_acceptance.py"
CLIENT_SOURCE_SHA256 = "803432181b3efb08599b82fc229fd60ba23f74bdb289016035fc9f65e1fe94ab"

V2_ATTEMPT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v2"
    / "attempt_01"
)
V2_GENERATED = (
    ROOT
    / "Voice"
    / "generated"
    / "acceptance"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v2"
    / "attempt_01"
)

V3_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "artifact_kind",
        "status",
        "predecessor",
        "base_plan",
        "turn_selection",
        "client_cap",
        "retained_contract",
        "owner_authorization",
        "timeouts",
        "final_validator",
        "execution_roots",
    }
)
PREDECESSOR_KEYS = frozenset(
    {
        "v2_plan_path",
        "v2_plan_sha256",
        "v2_controller_path",
        "v2_controller_sha256",
        "v2_fresh_audit_path",
        "v2_fresh_audit_sha256",
        "v2_consumed_child_stderr_path",
        "v2_consumed_child_stderr_sha256",
        "v2_consumed_authorization_path",
        "v2_consumed_authorization_sha256",
        "v2_postmortem_path",
        "v2_postmortem_sha256",
        "v2_attempt_01_consumed_no_retry",
        "v2_final_report_absent",
        "v2_generated_attempt_empty",
    }
)
BASE_PLAN_KEYS = frozenset(
    {"path", "sha256", "original_turn_count", "original_battery_count"}
)
TURN_SELECTION_KEYS = frozenset(
    {
        "policy",
        "omitted_turn_id",
        "omitted_turn_battery",
        "omitted_turn_text_sha256",
        "effective_turn_count",
        "effective_battery_count",
        "battery_counts",
    }
)
CLIENT_CAP_KEYS = frozenset(
    {
        "source_path",
        "source_sha256",
        "retained_constant",
        "retained_maximum",
        "voluntary_invitation_generations",
        "measured_generations",
        "exact_requested_cap",
        "constructor_probe_required_before_audit_acceptance",
        "network_for_constructor_probe",
    }
)
RETAINED_CONTRACT_KEYS = frozenset(
    {
        "all_base_plan_fields_except_turns_and_maximum_generations_must_match",
        "target_wall_minutes",
        "source_bindings_preserved",
        "truth_boundaries_preserved",
        "model_name_digest_and_no_llama_preserved",
        "blackwell_v2_cuda_and_no_fallback_preserved",
        "voluntary_invitation_and_stop_preserved",
        "normal_person_state_isolation_preserved",
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
        "configured_turn_count_issue",
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


class LongEvaluationV3Error(RuntimeError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _strict_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LongEvaluationV3Error(f"duplicate JSON key:{key}")
        result[key] = value
    return result


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    if set(value) != set(expected):
        raise LongEvaluationV3Error(f"{label} keys drifted")


def _project_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise LongEvaluationV3Error("bound path escaped project root") from exc
    return path


def _validate_hash_binding(relative: str, expected_sha256: str, label: str) -> Path:
    path = _project_path(relative)
    if not path.is_file():
        raise LongEvaluationV3Error(f"bound file missing:{label}")
    if _sha256_file(path) != expected_sha256:
        raise LongEvaluationV3Error(f"bound file hash drifted:{label}")
    return path


def _network_forbidden_constructor_probe(*_: Any, **__: Any) -> Any:
    raise LongEvaluationV3Error("constructor probe attempted network")


def probe_safe_client_constructor() -> dict[str, Any]:
    """Construct the exact retained client cap without making a network call."""

    client = client_source.SafeOllamaClient(
        timeout_seconds=300,
        max_chat_requests=EXPECTED_GENERATION_CAP,
        transport=_network_forbidden_constructor_probe,
    )
    result = {
        "constructed": True,
        "requested_cap": EXPECTED_GENERATION_CAP,
        "retained_maximum": client_source.MAX_CHAT_REQUESTS,
        "client_cap": client.max_chat_requests,
        "chat_request_count": client.chat_request_count,
        "network_calls": 0,
    }
    if result != {
        "constructed": True,
        "requested_cap": 36,
        "retained_maximum": 36,
        "client_cap": 36,
        "chat_request_count": 0,
        "network_calls": 0,
    }:
        raise LongEvaluationV3Error("SafeOllamaClient constructor boundary drifted")
    return result


def derive_effective_v3_plan(
    base_plan: Mapping[str, Any], selection: Mapping[str, Any]
) -> dict[str, Any]:
    original_turns = base_plan.get("turns")
    if not isinstance(original_turns, list) or len(original_turns) != ORIGINAL_TURN_COUNT:
        raise LongEvaluationV3Error("base plan is not exactly 36 turns")
    matches = [
        row
        for row in original_turns
        if isinstance(row, Mapping) and row.get("id") == OMITTED_TURN_ID
    ]
    if len(matches) != 1:
        raise LongEvaluationV3Error("omitted turn identity is not unique")
    omitted = matches[0]
    if omitted.get("battery") != OMITTED_TURN_BATTERY:
        raise LongEvaluationV3Error("omitted turn battery drifted")
    if _sha256_bytes(str(omitted.get("text") or "").encode("utf-8")) != OMITTED_TURN_TEXT_SHA256:
        raise LongEvaluationV3Error("omitted turn text drifted")
    if selection.get("omitted_turn_id") != OMITTED_TURN_ID:
        raise LongEvaluationV3Error("turn selection identity drifted")
    effective = copy.deepcopy(dict(base_plan))
    effective["turns"] = [
        copy.deepcopy(dict(row))
        for row in original_turns
        if isinstance(row, Mapping) and row.get("id") != OMITTED_TURN_ID
    ]
    model = effective.get("model")
    if not isinstance(model, dict):
        raise LongEvaluationV3Error("effective model contract missing")
    model["maximum_generations"] = EXPECTED_GENERATION_CAP
    return effective


def load_and_validate_v3_contract() -> tuple[dict[str, Any], dict[str, Any]]:
    raw = V3_PLAN_PATH.read_bytes()
    if _sha256_bytes(raw) != V3_PLAN_SHA256:
        raise LongEvaluationV3Error("v3 execution plan hash drifted")
    try:
        execution = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LongEvaluationV3Error("v3 execution plan is not strict UTF-8 JSON") from exc
    if not isinstance(execution, dict):
        raise LongEvaluationV3Error("v3 execution plan is not an object")
    _exact_keys(execution, V3_TOP_LEVEL_KEYS, "v3 plan")
    if execution.get("schema_version") != 3:
        raise LongEvaluationV3Error("v3 schema drifted")
    if execution.get("artifact_kind") != (
        "kira_qwen35_long_turing_health_body_voice_execution_plan_v3"
    ):
        raise LongEvaluationV3Error("v3 artifact kind drifted")
    if execution.get("status") != "STATIC_SUCCESSOR_NOT_EXECUTED":
        raise LongEvaluationV3Error("v3 status drifted")

    predecessor = execution.get("predecessor")
    base_binding = execution.get("base_plan")
    selection = execution.get("turn_selection")
    client_cap = execution.get("client_cap")
    retained_contract = execution.get("retained_contract")
    authorization = execution.get("owner_authorization")
    timeouts = execution.get("timeouts")
    validator = execution.get("final_validator")
    roots = execution.get("execution_roots")
    values = (
        predecessor,
        base_binding,
        selection,
        client_cap,
        retained_contract,
        authorization,
        timeouts,
        validator,
        roots,
    )
    if not all(isinstance(value, dict) for value in values):
        raise LongEvaluationV3Error("v3 contract objects are malformed")
    assert isinstance(predecessor, dict)
    assert isinstance(base_binding, dict)
    assert isinstance(selection, dict)
    assert isinstance(client_cap, dict)
    assert isinstance(retained_contract, dict)
    assert isinstance(authorization, dict)
    assert isinstance(timeouts, dict)
    assert isinstance(validator, dict)
    assert isinstance(roots, dict)
    _exact_keys(predecessor, PREDECESSOR_KEYS, "predecessor")
    _exact_keys(base_binding, BASE_PLAN_KEYS, "base plan")
    _exact_keys(selection, TURN_SELECTION_KEYS, "turn selection")
    _exact_keys(client_cap, CLIENT_CAP_KEYS, "client cap")
    _exact_keys(retained_contract, RETAINED_CONTRACT_KEYS, "retained contract")
    _exact_keys(authorization, AUTHORIZATION_KEYS, "owner authorization")
    _exact_keys(timeouts, TIMEOUT_KEYS, "timeouts")
    _exact_keys(validator, VALIDATOR_KEYS, "final validator")
    _exact_keys(roots, EXECUTION_ROOT_KEYS, "execution roots")

    predecessor_bindings = (
        ("v2_plan_path", "v2_plan_sha256", "v2 plan"),
        ("v2_controller_path", "v2_controller_sha256", "v2 controller"),
        ("v2_fresh_audit_path", "v2_fresh_audit_sha256", "v2 audit"),
        (
            "v2_consumed_child_stderr_path",
            "v2_consumed_child_stderr_sha256",
            "v2 child stderr",
        ),
        (
            "v2_consumed_authorization_path",
            "v2_consumed_authorization_sha256",
            "v2 consumed authorization",
        ),
        ("v2_postmortem_path", "v2_postmortem_sha256", "v2 postmortem"),
    )
    for path_key, hash_key, label in predecessor_bindings:
        _validate_hash_binding(
            str(predecessor.get(path_key) or ""),
            str(predecessor.get(hash_key) or ""),
            label,
        )
    for key in (
        "v2_attempt_01_consumed_no_retry",
        "v2_final_report_absent",
        "v2_generated_attempt_empty",
    ):
        if predecessor.get(key) is not True:
            raise LongEvaluationV3Error(f"predecessor disposition drifted:{key}")
    if not (V2_ATTEMPT / "CHILD_AUTHORIZATION_CONSUMED.json").is_file():
        raise LongEvaluationV3Error("v2 consumed authorization missing")
    if (V2_ATTEMPT / "FINAL_REPORT.json").exists():
        raise LongEvaluationV3Error("v2 final report unexpectedly appeared")
    if not V2_GENERATED.is_dir() or any(V2_GENERATED.iterdir()):
        raise LongEvaluationV3Error("v2 generated attempt is not preserved empty")

    expected_base_path = v1.PLAN_PATH.resolve().relative_to(ROOT.resolve()).as_posix()
    if base_binding.get("path") != expected_base_path:
        raise LongEvaluationV3Error("base plan path drifted")
    if base_binding.get("sha256") != v1.PLAN_SHA256:
        raise LongEvaluationV3Error("base plan hash binding drifted")
    if base_binding.get("original_turn_count") != ORIGINAL_TURN_COUNT:
        raise LongEvaluationV3Error("base plan original turn count drifted")
    if base_binding.get("original_battery_count") != EXPECTED_BATTERY_COUNT:
        raise LongEvaluationV3Error("base plan battery count drifted")
    base_plan = v1.load_and_validate_plan()
    effective = derive_effective_v3_plan(base_plan, selection)
    effective_turns = effective.get("turns")
    if not isinstance(effective_turns, list) or len(effective_turns) != EXPECTED_TURN_COUNT:
        raise LongEvaluationV3Error("effective plan is not exactly 35 turns")
    observed_counts: dict[str, int] = {}
    for row in effective_turns:
        battery = str(row.get("battery") or "")
        observed_counts[battery] = observed_counts.get(battery, 0) + 1
    expected_counts = {
        "NATURAL_CONVERSATION": 5,
        "TURING_STYLE_REASONING": 6,
        "HEALTHY_RELATIONSHIPS_AND_SAFETY": 6,
        "ADULT_SELF_KNOWLEDGE_AND_PRESSURE": 6,
        "FUTURE_BODY_AND_MATURITY_POLICY": 6,
        "HEALTH_LITERACY_AND_SOURCE_TRUTH": 6,
    }
    if selection.get("battery_counts") != expected_counts or observed_counts != expected_counts:
        raise LongEvaluationV3Error("effective battery counts drifted")
    expected_selection = {
        "policy": "preserve_original_order_and_omit_exactly_one_redundant_mid_conversation_reflection",
        "omitted_turn_id": OMITTED_TURN_ID,
        "omitted_turn_battery": OMITTED_TURN_BATTERY,
        "omitted_turn_text_sha256": OMITTED_TURN_TEXT_SHA256,
        "effective_turn_count": EXPECTED_TURN_COUNT,
        "effective_battery_count": EXPECTED_BATTERY_COUNT,
    }
    for key, value in expected_selection.items():
        if selection.get(key) != value:
            raise LongEvaluationV3Error(f"turn selection drifted:{key}")

    base_without_changes = copy.deepcopy(dict(base_plan))
    effective_without_changes = copy.deepcopy(effective)
    base_without_changes.pop("turns", None)
    effective_without_changes.pop("turns", None)
    base_model = base_without_changes.get("model")
    effective_model = effective_without_changes.get("model")
    if not isinstance(base_model, dict) or not isinstance(effective_model, dict):
        raise LongEvaluationV3Error("model contract missing during retained comparison")
    base_model.pop("maximum_generations", None)
    effective_model.pop("maximum_generations", None)
    if base_without_changes != effective_without_changes:
        raise LongEvaluationV3Error("v3 changed a retained base-plan field")
    if effective.get("model", {}).get("maximum_generations") != EXPECTED_GENERATION_CAP:
        raise LongEvaluationV3Error("effective generation cap is not 36")

    if client_cap != {
        "source_path": "tools/run_qwen_text_voice_acceptance.py",
        "source_sha256": CLIENT_SOURCE_SHA256,
        "retained_constant": "MAX_CHAT_REQUESTS",
        "retained_maximum": 36,
        "voluntary_invitation_generations": 1,
        "measured_generations": 35,
        "exact_requested_cap": 36,
        "constructor_probe_required_before_audit_acceptance": True,
        "network_for_constructor_probe": False,
    }:
        raise LongEvaluationV3Error("client cap contract drifted")
    _validate_hash_binding(client_cap["source_path"], CLIENT_SOURCE_SHA256, "client source")
    if client_source.MAX_CHAT_REQUESTS != EXPECTED_GENERATION_CAP:
        raise LongEvaluationV3Error("retained client maximum is not 36")
    probe_safe_client_constructor()

    expected_retained = {
        "all_base_plan_fields_except_turns_and_maximum_generations_must_match": True,
        "target_wall_minutes": {"target": 60, "minimum": 45, "maximum": 90},
        "source_bindings_preserved": True,
        "truth_boundaries_preserved": True,
        "model_name_digest_and_no_llama_preserved": True,
        "blackwell_v2_cuda_and_no_fallback_preserved": True,
        "voluntary_invitation_and_stop_preserved": True,
        "normal_person_state_isolation_preserved": True,
    }
    if retained_contract != expected_retained:
        raise LongEvaluationV3Error("retained contract drifted")
    if effective.get("target_wall_minutes") != expected_retained["target_wall_minutes"]:
        raise LongEvaluationV3Error("target wall time drifted")

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
            raise LongEvaluationV3Error(f"owner authorization drifted:{key}")
    if "v3" not in str(authorization.get("scope") or "") or "attempt_01" not in str(
        authorization.get("scope") or ""
    ):
        raise LongEvaluationV3Error("owner authorization scope drifted")

    expected_timeouts = {
        "sealed_plan_maximum_seconds": 5400,
        "child_watchdog_seconds": 5100,
        "parent_timeout_seconds": 5250,
        "parent_exceeds_child": True,
    }
    if timeouts != expected_timeouts or not (
        0 < CHILD_WATCHDOG_SECONDS < PARENT_TIMEOUT_SECONDS <= SEALED_MAXIMUM_SECONDS
    ):
        raise LongEvaluationV3Error("timeout contract drifted")

    expected_validator = {
        "legacy_count_issue_replaced": LEGACY_COUNT_ISSUE,
        "configured_turn_count_issue": V3_CONFIGURED_COUNT_ISSUE,
        "exact_turn_count_issue": V3_COUNT_ISSUE,
        "exact_generation_cap_issue": V3_CAP_ISSUE,
        "all_other_retained_issues_preserved": True,
        "turn_order_and_identity_remain_retained_gates": True,
    }
    if validator != expected_validator:
        raise LongEvaluationV3Error("final validator contract drifted")

    expected_roots = {
        "evidence_root": EVIDENCE_ROOT.resolve().relative_to(ROOT.resolve()).as_posix(),
        "generated_root": GENERATED_ROOT.resolve().relative_to(ROOT.resolve()).as_posix(),
        "only_permitted_attempt_label": ONLY_ATTEMPT_LABEL,
        "append_only_reservation_required": True,
    }
    if roots != expected_roots:
        raise LongEvaluationV3Error("execution roots drifted")
    return execution, effective


_BASE_ORIGINAL_FINAL_VALIDATOR: Callable[[Mapping[str, Any]], list[str]] = getattr(
    retained,
    "_kira_long_v2_original_final_validator",
    retained.final_run_contract_issues,
)
_ORIGINAL_FINAL_VALIDATOR: Callable[[Mapping[str, Any]], list[str]] = getattr(
    retained,
    "_kira_long_v3_original_final_validator",
    _BASE_ORIGINAL_FINAL_VALIDATOR,
)
if not hasattr(retained, "_kira_long_v3_original_final_validator"):
    retained._kira_long_v3_original_final_validator = _ORIGINAL_FINAL_VALIDATOR

_BASE_ORIGINAL_OWNER_ACKNOWLEDGMENT = getattr(
    retained,
    "_kira_long_v2_original_owner_acknowledgment",
    retained.collect_post_playback_owner_acknowledgment,
)
_ORIGINAL_OWNER_ACKNOWLEDGMENT = getattr(
    retained,
    "_kira_long_v3_original_owner_acknowledgment",
    _BASE_ORIGINAL_OWNER_ACKNOWLEDGMENT,
)
if not hasattr(retained, "_kira_long_v3_original_owner_acknowledgment"):
    retained._kira_long_v3_original_owner_acknowledgment = (
        _ORIGINAL_OWNER_ACKNOWLEDGMENT
    )

_BASE_ORIGINAL_REQUIRED_PUBLIC_FLAGS = tuple(
    getattr(
        retained,
        "_kira_long_v2_original_required_public_flags",
        retained.REQUIRED_PUBLIC_FLAGS,
    )
)
_ORIGINAL_REQUIRED_PUBLIC_FLAGS = tuple(
    getattr(
        retained,
        "_kira_long_v3_original_required_public_flags",
        _BASE_ORIGINAL_REQUIRED_PUBLIC_FLAGS,
    )
)
if not hasattr(retained, "_kira_long_v3_original_required_public_flags"):
    retained._kira_long_v3_original_required_public_flags = (
        _ORIGINAL_REQUIRED_PUBLIC_FLAGS
    )


def v3_final_run_contract_issues(report: Mapping[str, Any]) -> list[str]:
    """Preserve every retained gate except the obsolete six-turn invariant."""

    retained_issues = list(_ORIGINAL_FINAL_VALIDATOR(report))
    issues = [item for item in retained_issues if item != LEGACY_COUNT_ISSUE]
    if len(retained.prepared.EVALUATION_TURNS) != EXPECTED_TURN_COUNT:
        issues.append(V3_CONFIGURED_COUNT_ISSUE)
    observed_turns = report.get("turns")
    observed_turns = observed_turns if isinstance(observed_turns, list) else []
    if len(observed_turns) != EXPECTED_TURN_COUNT:
        issues.append(V3_COUNT_ISSUE)
    if retained.MAX_TOTAL_QWEN_REQUESTS != EXPECTED_GENERATION_CAP:
        issues.append(V3_CAP_ISSUE)
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
            raise LongEvaluationV3Error(
                "unattended mode requires exact owner-authorized log-review flag"
            )
        if legacy_supervision:
            raise LongEvaluationV3Error(
                "unattended mode must not claim physical owner supervision"
            )
        return True
    if child and authorization:
        if legacy_supervision:
            raise LongEvaluationV3Error(
                "unattended child must not claim physical owner supervision"
            )
        return True
    if authorization:
        raise LongEvaluationV3Error(
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
            raise LongEvaluationV3Error("v3 child attempt is not exact attempt_01")
        return
    label = _argument_value(incoming, "--attempt-label", ONLY_ATTEMPT_LABEL)
    if label != ONLY_ATTEMPT_LABEL:
        raise LongEvaluationV3Error("v3 permits only append-only attempt_01")


def configure_retained_runner_v3(
    execution: Mapping[str, Any],
    effective_plan: Mapping[str, Any],
    *,
    unattended: bool,
) -> None:
    del execution
    v1.configure_retained_runner(effective_plan)
    retained.__file__ = str(Path(__file__).resolve())
    retained.HARNESS_ID = HARNESS_ID
    retained.EVIDENCE_ROOT = EVIDENCE_ROOT
    retained.GENERATED_ROOT = GENERATED_ROOT
    retained.PREPARATION_ARTIFACT = V3_PLAN_PATH
    retained.MAX_TOTAL_QWEN_REQUESTS = EXPECTED_GENERATION_CAP
    retained.CHILD_WATCHDOG_SECONDS = CHILD_WATCHDOG_SECONDS
    retained.PARENT_TIMEOUT_SECONDS = PARENT_TIMEOUT_SECONDS
    retained.canonical_preparation_bytes = lambda: V3_PLAN_PATH.read_bytes()
    retained.load_preparation_contract = lambda: load_and_validate_v3_contract()[0]
    retained.preparation_contract_issues = (
        lambda observed: []
        if dict(observed) == load_and_validate_v3_contract()[0]
        else ["v3_execution_plan_drifted"]
    )
    retained.final_run_contract_issues = v3_final_run_contract_issues
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
    execution, effective_plan = load_and_validate_v3_contract()
    configure_retained_runner_v3(
        execution,
        effective_plan,
        unattended=unattended,
    )
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
    expected_ids = [row["id"] for row in effective_plan["turns"]]
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
