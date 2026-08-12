#!/usr/bin/env python3
"""Static V8 successor: exact reviewed shell substitution; no live authority."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation as v1
from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v3 as v3
from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v7 as v7
from tools import run_qwen35_kira_turing_psych_voice_owner_evaluation as retained


V8_PLAN_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260811"
    / "kira_qwen35_long_turing_health_body_voice_preparation_v8"
    / "attempt_01"
    / "EXECUTION_PLAN_V8.json"
)
V8_PLAN_SHA256 = "9e472f839a4ecae2d538db67244db23fb6d9cc4101b29d2d3b87f3e54d32d40e"
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260811"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v8"
)
GENERATED_ROOT = (
    ROOT
    / "Voice"
    / "generated"
    / "acceptance"
    / "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v8"
)
HARNESS_ID = "kira_qwen35_long_turing_health_body_voice_owner_evaluation_v8"
ONLY_ATTEMPT_LABEL = "attempt_01"
LEGACY_SHELL_SHA256 = "69594a9917b55dbca4992c12c357f79d81c0ccb7028ca8f2cc46e4f18789ecdd"
CURRENT_SHELL_SHA256 = "72e4fc403e00a2c4e7ac84e7a87a3c925fc9ce475a8afc90e17ac9e0b6b19fb4"

_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "artifact_kind",
        "status",
        "predecessor",
        "retained_runtime_contract",
        "reviewed_shell_successor",
        "v8_repair_contract",
        "execution_roots",
    }
)


class LongEvaluationV8Error(RuntimeError):
    """Raised when the exact append-only V8 boundary is not satisfied."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LongEvaluationV8Error(f"duplicate JSON key:{key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> Any:
    raise LongEvaluationV8Error(f"non-standard JSON numeric constant:{value}")


def strict_json_loads(value: str) -> Any:
    return json.loads(
        value,
        object_pairs_hook=_strict_object,
        parse_constant=_reject_json_constant,
    )


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _project_file(row: dict[str, Any], label: str) -> bytes:
    if type(row) is not dict or set(row) != {"path", "bytes", "sha256"}:
        raise LongEvaluationV8Error(f"{label} row shape drifted")
    relative = Path(str(row.get("path") or ""))
    if not relative.as_posix() or relative.is_absolute() or ".." in relative.parts:
        raise LongEvaluationV8Error(f"{label} path is not project-relative")
    path = (ROOT / relative).resolve(strict=True)
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise LongEvaluationV8Error(f"{label} escaped project root") from exc
    data = path.read_bytes()
    size = row.get("bytes")
    if isinstance(size, bool) or not isinstance(size, int) or size != len(data):
        raise LongEvaluationV8Error(f"{label} byte drift:{relative.as_posix()}")
    if row.get("sha256") != _sha256_bytes(data):
        raise LongEvaluationV8Error(f"{label} hash drift:{relative.as_posix()}")
    return data


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    if type(value) is not dict or set(value) != set(expected):
        raise LongEvaluationV8Error(f"{label} keys drifted")


def _load_v1_plan_with_reviewed_shell_successor(reviewed: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the frozen V1 plan, allowing exactly the reviewed shell successor."""
    legacy_row = reviewed.get("legacy_plan")
    current_shell_row = reviewed.get("current_shell")
    fast_end_test = reviewed.get("fast_end_test")
    fast_end_checkpoint = reviewed.get("fast_end_checkpoint")
    if not all(type(value) is dict for value in (
        legacy_row,
        current_shell_row,
        fast_end_test,
        fast_end_checkpoint,
    )):
        raise LongEvaluationV8Error("reviewed shell evidence rows malformed")
    assert type(legacy_row) is dict
    assert type(current_shell_row) is dict
    assert type(fast_end_test) is dict
    assert type(fast_end_checkpoint) is dict
    raw = _project_file(legacy_row, "legacy V1 plan")
    _project_file(current_shell_row, "current shell")
    _project_file(fast_end_test, "fast-end test")
    _project_file(fast_end_checkpoint, "fast-end checkpoint")
    if Path(str(legacy_row.get("path"))) != v1.PLAN_PATH.relative_to(ROOT):
        raise LongEvaluationV8Error("legacy V1 plan path drifted")
    if legacy_row.get("sha256") != v1.PLAN_SHA256:
        raise LongEvaluationV8Error("legacy V1 plan identity drifted")
    if current_shell_row != {
        "path": "tools/kira_world_shell_server.py",
        "bytes": 606696,
        "sha256": CURRENT_SHELL_SHA256,
    }:
        raise LongEvaluationV8Error("current shell successor identity drifted")
    if reviewed.get("legacy_shell_binding_sha256") != LEGACY_SHELL_SHA256:
        raise LongEvaluationV8Error("legacy shell binding identity drifted")
    if reviewed.get("original_other_project_binding_count") != 9:
        raise LongEvaluationV8Error("other V1 project binding count drifted")
    if reviewed.get("exact_one_substitution_only") is not True:
        raise LongEvaluationV8Error("one-substitution boundary disabled")
    if reviewed.get("historical_v1_files_unchanged") is not True:
        raise LongEvaluationV8Error("historical V1 preservation truth drifted")
    try:
        payload = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, LongEvaluationV8Error) as exc:
        raise LongEvaluationV8Error("legacy V1 plan is not strict UTF-8 JSON") from exc
    _exact_keys(payload, v1.PLAN_TOP_LEVEL_KEYS, "legacy V1 plan")
    if payload.get("schema_version") != 1:
        raise LongEvaluationV8Error("legacy V1 schema drifted")
    if payload.get("artifact_kind") != "kira_qwen35_long_turing_health_body_voice_evaluation_plan_v1":
        raise LongEvaluationV8Error("legacy V1 artifact kind drifted")
    if payload.get("status") != "STATIC_PLAN_NOT_EXECUTED":
        raise LongEvaluationV8Error("legacy V1 status drifted")

    model = payload.get("model")
    voice = payload.get("voice")
    person = payload.get("person")
    invitation = payload.get("voluntary_invitation")
    if not all(type(value) is dict for value in (model, voice, person, invitation)):
        raise LongEvaluationV8Error("legacy V1 identity objects malformed")
    assert type(model) is dict
    assert type(voice) is dict
    assert type(person) is dict
    assert type(invitation) is dict
    if model.get("name") != "qwen3.5:9b" or model.get("digest") != v1.prepared.EXPECTED_DIGEST:
        raise LongEvaluationV8Error("exact Qwen binding drifted")
    if model.get("llama_allowed") is not False:
        raise LongEvaluationV8Error("Llama became allowed")
    if voice.get("route") != "blackwell_gpu_persistent_candidate_v2":
        raise LongEvaluationV8Error("voice route drifted")
    for key in ("cpu_fallback_allowed", "sapi_allowed", "generic_voice_allowed"):
        if voice.get(key) is not False:
            raise LongEvaluationV8Error(f"unapproved voice path enabled:{key}")
    if person.get("candidate_id") != "kira" or person.get("classification") != "confirmed_adult":
        raise LongEvaluationV8Error("Kira adult identity binding drifted")
    if person.get("body_state") != "unfinished_and_inactive":
        raise LongEvaluationV8Error("body truth drifted")

    turns = payload.get("turns")
    if type(turns) is not list or len(turns) != 36:
        raise LongEvaluationV8Error("exact 36-turn legacy V1 plan is absent")
    if model.get("maximum_generations") != len(turns) + 1:
        raise LongEvaluationV8Error("legacy generation cap drifted")
    seen: set[str] = set()
    for index, row in enumerate(turns, start=1):
        if type(row) is not dict or set(row) != {"id", "battery", "text"}:
            raise LongEvaluationV8Error(f"legacy turn {index} shape drifted")
        turn_id = str(row.get("id") or "")
        text = str(row.get("text") or "")
        if not turn_id or turn_id in seen:
            raise LongEvaluationV8Error(f"legacy turn {index} id drifted")
        if row.get("battery") not in v1.ALLOWED_BATTERIES:
            raise LongEvaluationV8Error(f"legacy turn {index} battery drifted")
        if not (40 <= len(text) <= 1200):
            raise LongEvaluationV8Error(f"legacy turn {index} text outside bounds")
        seen.add(turn_id)
    if set(invitation) != {"id", "text", "clear_continue_prefix", "clear_stop_prefix"}:
        raise LongEvaluationV8Error("legacy voluntary invitation shape drifted")
    if invitation.get("clear_continue_prefix") != "Yes, continue":
        raise LongEvaluationV8Error("legacy continue phrase drifted")
    if invitation.get("clear_stop_prefix") != "No, stop":
        raise LongEvaluationV8Error("legacy stop phrase drifted")

    bindings = payload.get("bound_project_files")
    if type(bindings) is not list or len(bindings) != 10:
        raise LongEvaluationV8Error("legacy project binding set absent")
    paths: set[str] = set()
    substitutions = 0
    for row in bindings:
        if type(row) is not dict or set(row) != {"path", "sha256"}:
            raise LongEvaluationV8Error("legacy project binding shape drifted")
        relative = str(row.get("path") or "")
        expected_hash = str(row.get("sha256") or "")
        if relative in paths or not relative or len(expected_hash) != 64:
            raise LongEvaluationV8Error("legacy project binding absent or duplicated")
        target = (ROOT / relative).resolve()
        try:
            target.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise LongEvaluationV8Error("legacy project binding escaped root") from exc
        if relative == "tools/kira_world_shell_server.py":
            if expected_hash != LEGACY_SHELL_SHA256:
                raise LongEvaluationV8Error("legacy shell row changed")
            if not target.is_file() or _sha256_file(target) != CURRENT_SHELL_SHA256:
                raise LongEvaluationV8Error("reviewed shell successor drifted")
            substitutions += 1
        elif not target.is_file() or _sha256_file(target) != expected_hash:
            raise LongEvaluationV8Error(f"unchanged V1 project binding drifted:{relative}")
        paths.add(relative)
    if substitutions != 1 or len(paths) != 10:
        raise LongEvaluationV8Error("exact one reviewed shell substitution absent")

    truth = payload.get("truth_boundaries")
    if type(truth) is not dict or not truth:
        raise LongEvaluationV8Error("legacy truth boundaries absent")
    if any(value is not False for value in truth.values()):
        raise LongEvaluationV8Error("a prohibited legacy inference became true")
    return payload


def _load_v7_with_reviewed_shell(
    reviewed: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    original = v1.load_and_validate_plan
    v1.load_and_validate_plan = lambda: _load_v1_plan_with_reviewed_shell_successor(reviewed)
    try:
        return v7.load_and_validate_v7_contract()
    finally:
        v1.load_and_validate_plan = original


def load_and_validate_v8_contract() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]
]:
    raw = V8_PLAN_PATH.read_bytes()
    if _sha256_bytes(raw) != V8_PLAN_SHA256:
        raise LongEvaluationV8Error("V8 execution plan hash drifted")
    try:
        execution = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, LongEvaluationV8Error) as exc:
        raise LongEvaluationV8Error("V8 plan is not strict UTF-8 JSON") from exc
    _exact_keys(execution, _TOP_LEVEL_KEYS, "V8 plan")
    if execution.get("schema_version") != 8:
        raise LongEvaluationV8Error("V8 schema drifted")
    if execution.get("artifact_kind") != "kira_qwen35_long_turing_health_body_voice_execution_plan_v8":
        raise LongEvaluationV8Error("V8 artifact kind drifted")
    if execution.get("status") != "STATIC_SUCCESSOR_NOT_EXECUTED_PENDING_DIFFERENT_FRESH_AUDIT":
        raise LongEvaluationV8Error("V8 status drifted")

    predecessor = execution.get("predecessor")
    retained_contract = execution.get("retained_runtime_contract")
    reviewed = execution.get("reviewed_shell_successor")
    repair = execution.get("v8_repair_contract")
    roots = execution.get("execution_roots")
    if not all(type(value) is dict for value in (predecessor, retained_contract, reviewed, repair, roots)):
        raise LongEvaluationV8Error("V8 nested contract malformed")
    assert type(predecessor) is dict
    assert type(retained_contract) is dict
    assert type(reviewed) is dict
    assert type(repair) is dict
    assert type(roots) is dict
    if set(predecessor) != {"v7_rejected_no_live_attempt", "v7_live_retry_allowed", "subjects"}:
        raise LongEvaluationV8Error("V8 predecessor shape drifted")
    if predecessor.get("v7_rejected_no_live_attempt") is not True or predecessor.get(
        "v7_live_retry_allowed"
    ) is not False:
        raise LongEvaluationV8Error("V7 rejection/no-retry truth drifted")
    subjects = predecessor.get("subjects")
    if type(subjects) is not list or len(subjects) != 8:
        raise LongEvaluationV8Error("V8 predecessor subjects drifted")
    paths: set[str] = set()
    for value in subjects:
        if type(value) is not dict:
            raise LongEvaluationV8Error("V8 predecessor row is not an exact object")
        _project_file(value, "V8 predecessor")
        path = str(value.get("path") or "")
        if path in paths:
            raise LongEvaluationV8Error("V8 predecessor path repeated")
        paths.add(path)

    expected_reviewed_keys = {
        "legacy_plan",
        "legacy_shell_binding_sha256",
        "current_shell",
        "fast_end_test",
        "fast_end_checkpoint",
        "original_other_project_binding_count",
        "exact_one_substitution_only",
        "historical_v1_files_unchanged",
    }
    if set(reviewed) != expected_reviewed_keys:
        raise LongEvaluationV8Error("reviewed shell successor shape drifted")
    v7_execution, v6_execution, v5_execution, effective = _load_v7_with_reviewed_shell(reviewed)
    if retained_contract != v7_execution.get("retained_runtime_contract"):
        raise LongEvaluationV8Error("V8 retained runtime contract drifted")
    expected_repair = {
        "v7_semantic_and_terminal_repairs_retained": True,
        "legacy_v1_plan_must_remain_exact": True,
        "legacy_shell_binding_must_match_recorded_predecessor": True,
        "current_shell_and_fast_end_evidence_must_match_exact": True,
        "all_nine_other_v1_project_bindings_must_match_exact": True,
        "no_second_project_binding_substitution_allowed": True,
        "full_nested_contract_loader_must_pass_before_live_authority": True,
        "technical_pass_is_turing_acceptance": False,
        "owner_or_independent_semantic_review_still_required": True,
    }
    if repair != expected_repair:
        raise LongEvaluationV8Error("V8 repair contract drifted")
    expected_roots = {
        "evidence_root": EVIDENCE_ROOT.relative_to(ROOT).as_posix(),
        "generated_root": GENERATED_ROOT.relative_to(ROOT).as_posix(),
        "only_permitted_attempt_label": ONLY_ATTEMPT_LABEL,
        "append_only_reservation_required": True,
        "future_different_fresh_exact_byte_audit_required": True,
    }
    if roots != expected_roots:
        raise LongEvaluationV8Error("V8 roots drifted")
    if EVIDENCE_ROOT.exists() or GENERATED_ROOT.exists():
        raise LongEvaluationV8Error("V8 output roots already exist")
    return execution, v7_execution, v6_execution, v5_execution, effective


def validate_attempt_binding(incoming: Sequence[str]) -> None:
    child = "--child-run" in incoming

    def value(flag: str, default: str = "") -> str:
        for index, item in enumerate(incoming):
            if item == flag and index + 1 < len(incoming):
                return incoming[index + 1]
        return default

    if child:
        if Path(value("--attempt-path")).resolve() != (EVIDENCE_ROOT / ONLY_ATTEMPT_LABEL).resolve():
            raise LongEvaluationV8Error("V8 child evidence path is not exact attempt_01")
        if Path(value("--generated-path")).resolve() != (GENERATED_ROOT / ONLY_ATTEMPT_LABEL).resolve():
            raise LongEvaluationV8Error("V8 child generated path is not exact attempt_01")
        return
    if value("--attempt-label", ONLY_ATTEMPT_LABEL) != ONLY_ATTEMPT_LABEL:
        raise LongEvaluationV8Error("V8 permits only append-only attempt_01")


def configure_retained_runner_v8(
    execution: Mapping[str, Any],
    v7_execution: Mapping[str, Any],
    v6_execution: Mapping[str, Any],
    v5_execution: Mapping[str, Any],
    effective: Mapping[str, Any],
    *,
    unattended: bool,
) -> None:
    reviewed = execution["reviewed_shell_successor"]
    v7.configure_retained_runner_v7(
        v7_execution,
        v6_execution,
        v5_execution,
        effective,
        unattended=unattended,
    )
    retained.__file__ = str(Path(__file__).resolve())
    retained.HARNESS_ID = HARNESS_ID
    retained.EVIDENCE_ROOT = EVIDENCE_ROOT
    retained.GENERATED_ROOT = GENERATED_ROOT
    retained.PREPARATION_ARTIFACT = V8_PLAN_PATH
    retained.canonical_preparation_bytes = lambda: V8_PLAN_PATH.read_bytes()
    retained.load_preparation_contract = lambda: load_and_validate_v8_contract()[0]
    retained.preparation_contract_issues = (
        lambda observed: []
        if dict(observed) == load_and_validate_v8_contract()[0]
        else ["v8_execution_plan_drifted"]
    )
    del reviewed


def main(argv: Sequence[str] | None = None) -> int:
    incoming = list(sys.argv[1:] if argv is None else argv)
    unattended = v3.classify_invocation_mode(incoming)
    validate_attempt_binding(incoming)
    execution, v7_execution, v6_execution, v5_execution, effective = load_and_validate_v8_contract()
    configure_retained_runner_v8(
        execution,
        v7_execution,
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
    except (OSError, json.JSONDecodeError, LongEvaluationV8Error):
        return int(base_exit)
    if type(final) is not dict or type(wrapper) is not dict:
        return int(base_exit)
    turns = final.get("turns") if type(final.get("turns")) is list else []
    expected_ids = [row["id"] for row in effective["turns"]]
    acknowledgment = wrapper.get("owner_post_playback_acknowledgment")
    acknowledgment = acknowledgment if type(acknowledgment) is dict else {}
    semantic_and_epoch_complete = not v7.v5.v5_worker_epoch_contract_issues(final)
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
