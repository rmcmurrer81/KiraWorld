from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation as v1
from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v7 as v7
from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v8 as v8


def _execution() -> dict[str, object]:
    return v8.strict_json_loads(v8.V8_PLAN_PATH.read_text(encoding="utf-8"))


def _reviewed() -> dict[str, object]:
    value = _execution()["reviewed_shell_successor"]
    assert type(value) is dict
    return copy.deepcopy(value)


def test_v8_plan_and_predecessor_closure_are_exact() -> None:
    raw = v8.V8_PLAN_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == v8.V8_PLAN_SHA256
    execution, v7_execution, _v6_execution, _v5_execution, effective = (
        v8.load_and_validate_v8_contract()
    )
    assert execution["schema_version"] == 8
    assert v7_execution["schema_version"] == 7
    assert len(execution["predecessor"]["subjects"]) == 8
    assert len(effective["turns"]) == 35


def test_original_v1_loader_refuses_current_shell_and_v8_accepts_only_reviewed_successor() -> None:
    with pytest.raises(v1.LongEvaluationPlanError, match="project binding drifted:tools/kira_world_shell_server.py"):
        v1.load_and_validate_plan()
    plan = v8._load_v1_plan_with_reviewed_shell_successor(_reviewed())
    assert len(plan["bound_project_files"]) == 10
    row = next(item for item in plan["bound_project_files"] if item["path"] == "tools/kira_world_shell_server.py")
    assert row["sha256"] == v8.LEGACY_SHELL_SHA256
    assert v8._sha256_file(v8.ROOT / row["path"]) == v8.CURRENT_SHELL_SHA256


@pytest.mark.parametrize(
    ("row_name", "field", "replacement"),
    [
        ("current_shell", "bytes", 1),
        ("current_shell", "sha256", "0" * 64),
        ("fast_end_test", "sha256", "0" * 64),
        ("fast_end_checkpoint", "sha256", "0" * 64),
        ("legacy_plan", "sha256", "0" * 64),
    ],
)
def test_every_reviewed_shell_evidence_row_is_exact(
    row_name: str, field: str, replacement: object
) -> None:
    reviewed = _reviewed()
    row = reviewed[row_name]
    assert type(row) is dict
    row[field] = replacement
    with pytest.raises(v8.LongEvaluationV8Error):
        v8._load_v1_plan_with_reviewed_shell_successor(reviewed)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("legacy_shell_binding_sha256", "0" * 64),
        ("original_other_project_binding_count", 8),
        ("exact_one_substitution_only", False),
        ("historical_v1_files_unchanged", False),
    ],
)
def test_reviewed_substitution_policy_is_closed(field: str, replacement: object) -> None:
    reviewed = _reviewed()
    reviewed[field] = replacement
    with pytest.raises(v8.LongEvaluationV8Error):
        v8._load_v1_plan_with_reviewed_shell_successor(reviewed)


def test_any_of_the_other_nine_v1_bindings_still_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = v8.strict_json_loads(v1.PLAN_PATH.read_text(encoding="utf-8"))
    other = next(
        item["path"]
        for item in plan["bound_project_files"]
        if item["path"] != "tools/kira_world_shell_server.py"
    )
    original = v8._sha256_file

    def hostile(path: Path) -> str:
        if path.resolve() == (v8.ROOT / other).resolve():
            return "0" * 64
        return original(path)

    monkeypatch.setattr(v8, "_sha256_file", hostile)
    with pytest.raises(v8.LongEvaluationV8Error, match="unchanged V1 project binding drifted"):
        v8._load_v1_plan_with_reviewed_shell_successor(_reviewed())


def test_nested_loader_patch_is_scoped_and_restores_original() -> None:
    original = v1.load_and_validate_plan
    reviewed = _reviewed()
    loaded = v8._load_v7_with_reviewed_shell(reviewed)
    assert loaded[0]["schema_version"] == 7
    assert v1.load_and_validate_plan is original


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_v8_json_rejects_nonstandard_numeric_constants(constant: str) -> None:
    with pytest.raises(v8.LongEvaluationV8Error, match="non-standard JSON numeric constant"):
        v8.strict_json_loads('{"value":' + constant + "}")


def test_v8_json_rejects_duplicate_keys() -> None:
    with pytest.raises(v8.LongEvaluationV8Error, match="duplicate JSON key"):
        v8.strict_json_loads('{"value":1,"value":2}')


def test_attempt_paths_and_outputs_remain_fail_closed() -> None:
    v8.validate_attempt_binding([])
    with pytest.raises(v8.LongEvaluationV8Error):
        v8.validate_attempt_binding(["--attempt-label", "attempt_02"])
    with pytest.raises(v8.LongEvaluationV8Error):
        v8.validate_attempt_binding(
            [
                "--child-run",
                "--attempt-path",
                str(v8.ROOT / "wrong"),
                "--generated-path",
                str(v8.GENERATED_ROOT / v8.ONLY_ATTEMPT_LABEL),
            ]
        )
    assert not v8.EVIDENCE_ROOT.exists()
    assert not v8.GENERATED_ROOT.exists()


def test_v7_semantic_and_terminal_repairs_remain_the_configured_boundary() -> None:
    source = Path(v8.__file__).read_text(encoding="utf-8")
    assert "v7.configure_retained_runner_v7(" in source
    assert "technical_pass_is_turing_acceptance" in source
    assert "owner_hearing_acknowledged\": False" in source
    assert v7.strict_json_loads('{"finite":1.25}') == {"finite": 1.25}
