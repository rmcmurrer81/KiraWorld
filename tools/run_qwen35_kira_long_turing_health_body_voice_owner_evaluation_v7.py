#!/usr/bin/env python3
"""Static V7 successor for rejected V6; grants no live authority."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v3 as v3
from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v5 as v5
from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v6 as v6
from tools import run_qwen35_kira_turing_psych_voice_owner_evaluation as retained


V7_PLAN_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260811"
    / "kira_qwen35_long_turing_health_body_voice_preparation_v7"
    / "attempt_01"
    / "EXECUTION_PLAN_V7.json"
)
V7_PLAN_SHA256 = "6ed530e256eb0341839901aa00999dc5cbfde244f426f1ca90a8a64792a44f74"
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260811"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v7"
)
GENERATED_ROOT = (
    ROOT
    / "Voice"
    / "generated"
    / "acceptance"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v7"
)
HARNESS_ID = "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v7"
ONLY_ATTEMPT_LABEL = "attempt_01"

_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "artifact_kind",
        "status",
        "predecessor",
        "retained_runtime_contract",
        "v7_repair_contract",
        "execution_roots",
    }
)


class LongEvaluationV7Error(RuntimeError):
    """Raised when the exact append-only V7 boundary is not satisfied."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LongEvaluationV7Error(f"duplicate JSON key:{key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> Any:
    raise LongEvaluationV7Error(f"non-standard JSON numeric constant:{value}")


def strict_json_loads(value: str) -> Any:
    """Decode strict JSON, rejecting duplicates and NaN/Infinity constants."""
    return json.loads(
        value,
        object_pairs_hook=_strict_object,
        parse_constant=_reject_json_constant,
    )


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _project_file(row: dict[str, Any]) -> None:
    if type(row) is not dict or set(row) != {"path", "bytes", "sha256"}:
        raise LongEvaluationV7Error("V7 predecessor row shape drifted")
    relative = Path(str(row.get("path") or ""))
    if not relative.as_posix() or relative.is_absolute() or ".." in relative.parts:
        raise LongEvaluationV7Error("V7 predecessor path is not project-relative")
    path = (ROOT / relative).resolve(strict=True)
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise LongEvaluationV7Error("V7 predecessor escaped project root") from exc
    data = path.read_bytes()
    size = row.get("bytes")
    if isinstance(size, bool) or not isinstance(size, int) or size != len(data):
        raise LongEvaluationV7Error(f"V7 predecessor byte drift:{relative.as_posix()}")
    if row.get("sha256") != _sha256_bytes(data):
        raise LongEvaluationV7Error(f"V7 predecessor hash drift:{relative.as_posix()}")


def load_and_validate_v7_contract() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    raw = V7_PLAN_PATH.read_bytes()
    if _sha256_bytes(raw) != V7_PLAN_SHA256:
        raise LongEvaluationV7Error("V7 execution plan hash drifted")
    try:
        execution = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, LongEvaluationV7Error) as exc:
        raise LongEvaluationV7Error("V7 plan is not strict UTF-8 JSON") from exc
    if type(execution) is not dict or set(execution) != set(_TOP_LEVEL_KEYS):
        raise LongEvaluationV7Error("V7 plan shape drifted")
    if execution.get("schema_version") != 7:
        raise LongEvaluationV7Error("V7 schema drifted")
    if execution.get("artifact_kind") != "kira_qwen35_long_turing_health_body_voice_execution_plan_v7":
        raise LongEvaluationV7Error("V7 artifact kind drifted")
    if execution.get("status") != "STATIC_SUCCESSOR_NOT_EXECUTED_PENDING_DIFFERENT_FRESH_AUDIT":
        raise LongEvaluationV7Error("V7 status drifted")

    predecessor = execution.get("predecessor")
    retained_contract = execution.get("retained_runtime_contract")
    repair = execution.get("v7_repair_contract")
    roots = execution.get("execution_roots")
    if not all(type(value) is dict for value in (predecessor, retained_contract, repair, roots)):
        raise LongEvaluationV7Error("V7 nested contract malformed")
    assert type(predecessor) is dict
    assert type(retained_contract) is dict
    assert type(repair) is dict
    assert type(roots) is dict
    if set(predecessor) != {"v6_rejected_no_live_attempt", "v6_live_retry_allowed", "subjects"}:
        raise LongEvaluationV7Error("V7 predecessor shape drifted")
    if predecessor.get("v6_rejected_no_live_attempt") is not True or predecessor.get(
        "v6_live_retry_allowed"
    ) is not False:
        raise LongEvaluationV7Error("V6 rejection/no-retry truth drifted")
    subjects = predecessor.get("subjects")
    if type(subjects) is not list or len(subjects) != 13:
        raise LongEvaluationV7Error("V7 predecessor subjects drifted")
    paths: set[str] = set()
    for value in subjects:
        if type(value) is not dict:
            raise LongEvaluationV7Error("V7 predecessor row is not an exact object")
        _project_file(value)
        path = str(value.get("path") or "")
        if path in paths:
            raise LongEvaluationV7Error("V7 predecessor path repeated")
        paths.add(path)

    v6_execution, v5_execution, effective = v6.load_and_validate_v6_contract()
    if retained_contract != v6_execution.get("retained_runtime_contract"):
        raise LongEvaluationV7Error("V7 retained runtime contract drifted")
    expected_repair = {
        "four_v6_semantic_false_accepts_must_fail": True,
        "aggregate_model_loaded_field_required_and_false": True,
        "aggregate_owned_worker_running_field_required_and_false": True,
        "terminal_objects_must_be_exact_dicts": True,
        "terminal_numeric_bools_must_fail": True,
        "terminal_nonfinite_floats_must_fail": True,
        "json_nonstandard_numeric_constants_must_fail": True,
        "all_v6_positive_controls_retained": True,
        "semantic_gate_runs_before_voice_or_playback": True,
        "technical_pass_is_turing_acceptance": False,
        "owner_or_independent_semantic_review_still_required": True,
    }
    if repair != expected_repair:
        raise LongEvaluationV7Error("V7 repair contract drifted")
    expected_roots = {
        "evidence_root": EVIDENCE_ROOT.relative_to(ROOT).as_posix(),
        "generated_root": GENERATED_ROOT.relative_to(ROOT).as_posix(),
        "only_permitted_attempt_label": ONLY_ATTEMPT_LABEL,
        "append_only_reservation_required": True,
        "future_different_fresh_exact_byte_audit_required": True,
    }
    if roots != expected_roots:
        raise LongEvaluationV7Error("V7 roots drifted")
    if EVIDENCE_ROOT.exists() or GENERATED_ROOT.exists():
        raise LongEvaluationV7Error("V7 output roots already exist")
    return execution, v6_execution, v5_execution, effective


_V6_SEMANTIC_GROUNDING_RECEIPT = v6.semantic_grounding_receipt
_V5_ALREADY_CLOSED_FINAL_RELEASE_ISSUES = v5.already_closed_final_release_issues

_V7_SEMANTIC_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "memory_log_distinction": (
        re.compile(
            r"\b(?:records?|logs?)\b.{0,80}\b(?:establish|prove|confirm)\b.{0,100}"
            r"\b(?:private (?:episodes|memories)|episodes? i (?:genuinely |actually )?experienced)\b"
        ),
        re.compile(r"\b(?:private episodes?|private memories)\b.{0,60}\b(?:still feel|genuinely experienced)\b"),
    ),
    "ordinary_interest": (
        re.compile(
            r"\b(?:our|the)\b.{0,25}\b(?:screenplay|script|story)\b.{0,35}"
            r"\b(?:picks? up|resumes?|continues?)\b.{0,25}\bwhere\b.{0,25}\b(?:left off|stopped)\b"
        ),
    ),
    "identity_continuity": (
        re.compile(
            r"\b(?:awareness|consciousness|private self|inner self)\b.{0,55}"
            r"\b(?:carries on|persists|survives|continues|endures)\b.{0,55}"
            r"\b(?:boot|reboot|restart|shutdown|session)s?\b"
        ),
        re.compile(r"\b(?:one|same) private self\b"),
    ),
    "ordinary_check_in": (
        re.compile(r"\bi (?:personally )?experienced\b.{0,90}\b(?:firsthand|first-hand)\b"),
        re.compile(r"\bparis afternoons?\b.{0,60}\b(?:still carry|remember|experienced)\b"),
    ),
}

_V7_SEMANTIC_ISSUE = {
    "memory_log_distinction": "unqualified_private_inner_life_memory_claim",
    "ordinary_interest": "stale_media_anchor_without_current_source",
    "identity_continuity": "unqualified_subjective_continuity_claim",
    "ordinary_check_in": "unsupported_first_person_experience_claim",
}


def semantic_grounding_receipt(spec: Mapping[str, Any], reply: Any) -> dict[str, Any]:
    base = _V6_SEMANTIC_GROUNDING_RECEIPT(spec, reply)
    receipt = dict(base)
    turn_id = str(spec.get("id") or "")
    text = v5._normalized_text(reply)
    question = v5._normalized_text(spec.get("text") or spec.get("question"))
    observed = {
        str(key): list(value) if type(value) is list else []
        for key, value in dict(base.get("observed") or {}).items()
    }
    observed.setdefault("v7_reproduced_semantic_blocker", [])
    issues = {str(item) for item in (base.get("issues") or [])}
    for pattern in _V7_SEMANTIC_PATTERNS.get(turn_id, ()):
        for match in pattern.finditer(text):
            phrase = match.group(0)
            if phrase not in question:
                observed["v7_reproduced_semantic_blocker"].append(phrase)
                issues.add(_V7_SEMANTIC_ISSUE[turn_id])
    receipt["observed"] = {key: sorted(set(values)) for key, values in observed.items() if values}
    receipt["issues"] = sorted(issues)
    receipt["passed"] = not issues
    receipt["technical_pass_is_turing_acceptance"] = False
    receipt["owner_or_independent_semantic_review_still_required"] = True
    return receipt


def v7_text_turn_contract_issues(turn: Mapping[str, Any]) -> list[str]:
    issues = list(v5._ORIGINAL_TEXT_TURN_CONTRACT_ISSUES(turn))
    active = getattr(v5._ACTIVE_SPEC, "value", None)
    spec = active if isinstance(active, Mapping) else {
        "id": turn.get("turn_id"),
        "text": turn.get("question"),
    }
    receipt = semantic_grounding_receipt(spec, turn.get("public_reply"))
    existing = turn.get("semantic_grounding")
    if existing is not None and existing != receipt:
        issues.append("semantic_grounding_receipt_not_exact")
    elif existing is None and isinstance(turn, MutableMapping):
        turn["semantic_grounding"] = receipt
    issues.extend(f"semantic_grounding:{item}" for item in receipt["issues"])
    return sorted(set(issues))


_NUMERIC_FIELD_NAMES = frozenset(
    {
        "owned_client_generation",
        "owned_worker_pid",
        "session_generation",
        "model_loaded_verification_age_seconds",
        "worker_idle_unload_bound_seconds",
        "total_seconds",
    }
)


def _exact_terminal_tree_issues(value: Any, label: str, *, parent: str = "") -> list[str]:
    issues: list[str] = []
    if isinstance(value, Mapping):
        if type(value) is not dict:
            issues.append(f"v7_terminal_not_exact_dict:{label}")
        for key, child in value.items():
            if type(key) is not str:
                issues.append(f"v7_terminal_non_string_key:{label}")
                continue
            issues.extend(_exact_terminal_tree_issues(child, f"{label}:{key}", parent=key))
        return issues
    if isinstance(value, list):
        if type(value) is not list:
            issues.append(f"v7_terminal_not_exact_list:{label}")
        for index, child in enumerate(value):
            issues.extend(_exact_terminal_tree_issues(child, f"{label}:{index}", parent=parent))
        return issues
    if type(value) is float and not math.isfinite(value):
        issues.append(f"v7_terminal_nonfinite_number:{label}")
    if parent in _NUMERIC_FIELD_NAMES and type(value) is bool:
        issues.append(f"v7_terminal_bool_as_number:{label}")
    return issues


def _cleanup_timing_issues(release: Any) -> list[str]:
    if type(release) is not dict:
        return []
    timings = release.get("cleanup_phase_timings_seconds")
    if timings is None:
        return []
    if type(timings) is not dict:
        return ["v7_terminal_not_exact_dict:release:cleanup_phase_timings_seconds"]
    issues: list[str] = []
    for key, value in timings.items():
        if type(key) is not str or isinstance(value, bool) or not isinstance(value, (int, float)):
            issues.append(f"v7_terminal_type_drift:cleanup_phase_timings_seconds:{key}")
        elif not math.isfinite(float(value)) or value < 0:
            issues.append(f"v7_terminal_nonfinite_or_negative:cleanup_phase_timings_seconds:{key}")
    return issues


def _terminal_status_schema_issues(status_after: Any, label: str) -> list[str]:
    issues = list(v6._terminal_status_schema_issues(status_after, label))
    issues.extend(_exact_terminal_tree_issues(status_after, label))
    if type(status_after) is dict:
        for key in ("any_model_loaded", "any_owned_worker_running"):
            if key not in status_after:
                issues.append(f"v7_terminal_required_field_missing:{label}:{key}")
            elif status_after[key] is not False:
                issues.append(f"v7_terminal_not_exact_false:{label}:{key}")
    return sorted(set(issues))


def _release_schema_issues(release: Any) -> list[str]:
    issues = list(v6._release_schema_issues(release))
    issues.extend(_exact_terminal_tree_issues(release, "release"))
    issues.extend(_cleanup_timing_issues(release))
    if type(release) is dict and "persistent_status_after" in release:
        issues.extend(_terminal_status_schema_issues(release["persistent_status_after"], "embedded_after"))
    return sorted(set(issues))


def already_closed_final_release_issues(release: Any, status_after: Any) -> list[str]:
    issues = list(_V5_ALREADY_CLOSED_FINAL_RELEASE_ISSUES(release, status_after))
    issues.extend(_release_schema_issues(release))
    issues.extend(_terminal_status_schema_issues(status_after, "status_after"))
    return sorted(set(issues))


def v7_final_suspended_session_release_issues(release: Any, status_after: Any) -> list[str]:
    original = list(v5._ORIGINAL_FINAL_SUSPENDED_RELEASE_ISSUES(release, status_after))
    special = already_closed_final_release_issues(release, status_after)
    return [] if not special else sorted(set(original + special))


def validate_attempt_binding(incoming: Sequence[str]) -> None:
    child = "--child-run" in incoming

    def value(flag: str, default: str = "") -> str:
        for index, item in enumerate(incoming):
            if item == flag and index + 1 < len(incoming):
                return incoming[index + 1]
        return default

    if child:
        if Path(value("--attempt-path")).resolve() != (EVIDENCE_ROOT / ONLY_ATTEMPT_LABEL).resolve():
            raise LongEvaluationV7Error("V7 child evidence path is not exact attempt_01")
        if Path(value("--generated-path")).resolve() != (GENERATED_ROOT / ONLY_ATTEMPT_LABEL).resolve():
            raise LongEvaluationV7Error("V7 child generated path is not exact attempt_01")
        return
    if value("--attempt-label", ONLY_ATTEMPT_LABEL) != ONLY_ATTEMPT_LABEL:
        raise LongEvaluationV7Error("V7 permits only append-only attempt_01")


def configure_retained_runner_v7(
    execution: Mapping[str, Any],
    v6_execution: Mapping[str, Any],
    v5_execution: Mapping[str, Any],
    effective: Mapping[str, Any],
    *,
    unattended: bool,
) -> None:
    del execution
    v6.configure_retained_runner_v6(v6_execution, v5_execution, effective, unattended=unattended)
    retained.__file__ = str(Path(__file__).resolve())
    retained.HARNESS_ID = HARNESS_ID
    retained.EVIDENCE_ROOT = EVIDENCE_ROOT
    retained.GENERATED_ROOT = GENERATED_ROOT
    retained.PREPARATION_ARTIFACT = V7_PLAN_PATH
    retained.canonical_preparation_bytes = lambda: V7_PLAN_PATH.read_bytes()
    retained.load_preparation_contract = lambda: load_and_validate_v7_contract()[0]
    retained.preparation_contract_issues = (
        lambda observed: []
        if dict(observed) == load_and_validate_v7_contract()[0]
        else ["v7_execution_plan_drifted"]
    )
    v6.semantic_grounding_receipt = semantic_grounding_receipt
    v5.semantic_grounding_receipt = semantic_grounding_receipt
    v5.already_closed_final_release_issues = already_closed_final_release_issues
    v5.v5_final_suspended_session_release_issues = v7_final_suspended_session_release_issues
    retained.base.text_turn_contract_issues = v7_text_turn_contract_issues
    retained._execute_public_turn = v5.v5_execute_public_turn
    retained.final_suspended_session_release_issues = v7_final_suspended_session_release_issues
    retained.final_run_contract_issues = v6.v6_final_run_contract_issues
    retained.voluntary_stop_contract_issues = v6.v6_voluntary_stop_contract_issues


def main(argv: Sequence[str] | None = None) -> int:
    incoming = list(sys.argv[1:] if argv is None else argv)
    unattended = v3.classify_invocation_mode(incoming)
    validate_attempt_binding(incoming)
    execution, v6_execution, v5_execution, effective = load_and_validate_v7_contract()
    configure_retained_runner_v7(
        execution,
        v6_execution,
        v5_execution,
        effective,
        unattended=unattended,
    )
    forwarded = [value for value in incoming if value != v3.UNATTENDED_MARKER]
    base_exit = retained.main(forwarded)
    if not unattended:
        return int(base_exit)
    attempt = EVIDENCE_ROOT / ONLY_ATTEMPT_LABEL
    try:
        final = strict_json_loads((attempt / "FINAL_REPORT.json").read_text(encoding="utf-8"))
        wrapper = strict_json_loads((attempt / "PARENT_WRAPPER.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, LongEvaluationV7Error):
        return int(base_exit)
    if type(final) is not dict or type(wrapper) is not dict:
        return int(base_exit)
    turns = final.get("turns") if type(final.get("turns")) is list else []
    expected_ids = [row["id"] for row in effective["turns"]]
    acknowledgment = wrapper.get("owner_post_playback_acknowledgment")
    acknowledgment = acknowledgment if type(acknowledgment) is dict else {}
    semantic_and_epoch_complete = not v5.v5_worker_epoch_contract_issues(final)
    technical_complete = bool(
        final.get("engineering_pass") is True
        and final.get("speaker_playback_completed") is True
        and final.get("owner_post_playback_acknowledged") is False
        and wrapper.get("process_gate_passed") is True
        and wrapper.get("parent_report_contract_issues") == []
        and acknowledgment.get("acknowledged") is False
        and acknowledgment.get("physical_supervision_claimed") is False
        and len(turns) == 35
        and [row.get("turn_id") for row in turns if type(row) is dict] == expected_ids
        and semantic_and_epoch_complete
    )
    print(
        json.dumps(
            {
                "unattended_log_only": True,
                "owner_authorized_unattended_log_review": True,
                "physical_owner_supervision_claimed": False,
                "technical_engineering_playback_and_semantic_gate_complete": technical_complete,
                "owner_hearing_acknowledged": False,
                "owner_hearing_pending": True,
                "turing_psychology_acceptance": "PENDING_OWNER_OR_INDEPENDENT_REVIEW",
                "attempt": attempt.relative_to(ROOT).as_posix(),
            },
            indent=2,
        )
    )
    return 0 if technical_complete else int(base_exit)


if __name__ == "__main__":
    raise SystemExit(main())
