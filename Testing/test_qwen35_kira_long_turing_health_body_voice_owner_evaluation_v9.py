from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from Testing import test_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v7 as v7_tests
from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation as v1
from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v7 as v7
from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v8 as v8
from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v9 as v9
from tools import run_qwen35_kira_turing_psych_voice_owner_evaluation as retained


ROOT = Path(__file__).resolve().parents[1]


def _execution() -> dict[str, object]:
    value = v9.strict_json_loads(v9.V9_PLAN_PATH.read_text(encoding="utf-8"))
    assert type(value) is dict
    return value


def _reviewed() -> dict[str, object]:
    value = v8.strict_json_loads(v8.V8_PLAN_PATH.read_text(encoding="utf-8"))[
        "reviewed_shell_successor"
    ]
    assert type(value) is dict
    return copy.deepcopy(value)


def _child_arguments(*extra: str) -> list[str]:
    return [
        "--child-run",
        "--attempt-path",
        str(v9.EVIDENCE_ROOT / v9.ONLY_ATTEMPT_LABEL),
        "--generated-path",
        str(v9.GENERATED_ROOT / v9.ONLY_ATTEMPT_LABEL),
        "--child-nonce",
        "a" * 64,
        *extra,
    ]


def test_v9_plan_and_all_v8_rejection_subjects_are_exact() -> None:
    raw = v9.V9_PLAN_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == v9.V9_PLAN_SHA256
    plan = _execution()
    predecessor = plan["predecessor"]
    assert type(predecessor) is dict
    assert predecessor["v8_rejected_no_live_attempt"] is True
    assert predecessor["v8_live_retry_allowed"] is False
    subjects = predecessor["subjects"]
    assert type(subjects) is list and len(subjects) == 11
    assert len({row["path"] for row in subjects}) == 11
    for row in subjects:
        data = (ROOT / row["path"]).read_bytes()
        assert (len(data), hashlib.sha256(data).hexdigest()) == (
            row["bytes"],
            row["sha256"],
        )


def test_real_v9_projection_loads_the_full_nested_chain_and_restores_v1() -> None:
    original = v9._CANONICAL_V1_LOADER
    loaded = v9.load_and_validate_v9_contract()
    assert [row["schema_version"] for row in loaded[:5]] == [9, 8, 7, 6, 5]
    assert len(loaded[5]["turns"]) == 35
    assert v1.load_and_validate_plan is original
    assert not v9._V1_COMPATIBILITY_LOCK.locked()


def test_exact_model_turn_voice_playback_cleanup_and_unattended_truth_remain() -> None:
    execution, v8_execution, v7_execution, *_rest, effective = (
        v9.load_and_validate_v9_contract()
    )
    runtime = execution["retained_runtime_contract"]
    assert runtime == v9._EXPECTED_RUNTIME
    assert runtime == v8_execution["retained_runtime_contract"]
    assert runtime == v7_execution["retained_runtime_contract"]
    assert runtime["effective_measured_turns"] == 35
    assert runtime["voluntary_invitation_generations"] == 1
    assert runtime["maximum_qwen_generations"] == 36
    assert runtime["exact_model"] == "qwen3.5:9b"
    assert runtime["exact_digest"] == (
        "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
    )
    assert runtime["llama_allowed"] is False
    assert runtime["voice_route"] == "blackwell_gpu_persistent_candidate_v2"
    assert runtime["voice_device"] == "cuda"
    for field in ("cpu_fallback_allowed", "sapi_allowed", "generic_voice_allowed"):
        assert runtime[field] is False
    assert runtime["speaker_playback_requested"] is True
    assert runtime["physical_supervision_claimed"] is False
    assert runtime["owner_hearing_may_be_inferred"] is False
    closed_v7_effective = v9._load_v7_with_closed_v1(_reviewed())[3]
    assert [row["id"] for row in effective["turns"]] == [
        row["id"] for row in closed_v7_effective["turns"]
    ]


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_v9_strict_json_rejects_nonfinite_constants(constant: str) -> None:
    with pytest.raises(v9.LongEvaluationV9Error, match="non-standard JSON"):
        v9.strict_json_loads('{"value":' + constant + "}")


def test_v9_strict_json_rejects_duplicate_keys() -> None:
    with pytest.raises(v9.LongEvaluationV9Error, match="duplicate JSON key"):
        v9.strict_json_loads('{"value":1,"value":2}')


@pytest.mark.parametrize(
    "flag",
    [
        "--attempt-label",
        "--attempt-path",
        "--generated-path",
        "--child-nonce",
        "--child-run",
    ],
)
def test_every_critical_flag_rejects_duplicate_occurrences(flag: str) -> None:
    incoming = _child_arguments()
    if flag == "--attempt-label":
        incoming = [flag, "attempt_01", flag, "attempt_02"]
    elif flag == "--child-run":
        incoming.append(flag)
    else:
        index = incoming.index(flag)
        incoming.extend([flag, incoming[index + 1]])
    with pytest.raises(v9.LongEvaluationV9Error, match="duplicate critical flag"):
        v9.canonicalize_attempt_binding(incoming)


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("--attempt-label", "attempt_01"),
        ("--attempt-path", "somewhere"),
        ("--generated-path", "somewhere"),
        ("--child-nonce", "a" * 64),
        ("--child-run", "true"),
    ],
)
def test_every_critical_flag_rejects_equals_form(flag: str, value: str) -> None:
    with pytest.raises(v9.LongEvaluationV9Error, match="equals-form"):
        v9.canonicalize_attempt_binding([f"{flag}={value}"])


@pytest.mark.parametrize(
    "flag", ["--attempt-label", "--attempt-path", "--generated-path", "--child-nonce"]
)
def test_every_value_flag_rejects_missing_value_before_argparse(flag: str) -> None:
    with pytest.raises(v9.LongEvaluationV9Error, match="missing exact value"):
        v9.canonicalize_attempt_binding([flag])


@pytest.mark.parametrize(
    "value", ["", "-x", "--child-run", "bad\x00value", "bad\nvalue"]
)
def test_malformed_or_flag_shaped_critical_values_fail_before_argparse(value: str) -> None:
    with pytest.raises(v9.LongEvaluationV9Error, match="malformed value"):
        v9.canonicalize_attempt_binding(["--attempt-label", value])


def test_non_string_argument_fails_closed() -> None:
    with pytest.raises(v9.LongEvaluationV9Error, match="non-string"):
        v9.canonicalize_attempt_binding(["--attempt-label", 1])  # type: ignore[list-item]


@pytest.mark.parametrize(
    "incoming",
    [
        ["--attempt-label", "attempt_01", "--attempt-label", "attempt_02"],
        ["--attempt-label=attempt_01"],
        ["--attempt-label"],
        ["--attempt-label", "-x"],
        ["--attempt-label", "attempt_02"],
    ],
)
def test_bad_attempt_binding_is_rejected_before_retained_parser_is_called(
    monkeypatch: pytest.MonkeyPatch, incoming: list[str]
) -> None:
    def forbidden_parser() -> object:
        raise AssertionError("retained parser was reached before V9 rejection")

    monkeypatch.setattr(retained, "build_parser", forbidden_parser)
    with pytest.raises(v9.LongEvaluationV9Error):
        v9.canonicalize_attempt_binding(incoming)


@pytest.mark.parametrize("label", ["attempt_02", "ATTEMPT_01", "attempt_01 "])
def test_parent_attempt_must_be_exact_attempt_01(label: str) -> None:
    with pytest.raises(v9.LongEvaluationV9Error, match="only append-only attempt_01"):
        v9.canonicalize_attempt_binding(["--attempt-label", label])


@pytest.mark.parametrize("flag", ["--attempt-path", "--generated-path", "--child-nonce"])
def test_parent_refuses_every_child_only_value_flag(flag: str) -> None:
    value = "a" * 64 if flag == "--child-nonce" else "somewhere"
    with pytest.raises(v9.LongEvaluationV9Error, match="child-only"):
        v9.canonicalize_attempt_binding([flag, value])


def test_child_refuses_attempt_label_even_when_it_is_attempt_01() -> None:
    with pytest.raises(v9.LongEvaluationV9Error, match="must not provide"):
        v9.canonicalize_attempt_binding(
            _child_arguments("--attempt-label", "attempt_01")
        )


@pytest.mark.parametrize("flag", ["--attempt-path", "--generated-path", "--child-nonce"])
def test_child_requires_every_exact_bound_value(flag: str) -> None:
    incoming = _child_arguments()
    index = incoming.index(flag)
    del incoming[index : index + 2]
    with pytest.raises(v9.LongEvaluationV9Error, match="critical value missing"):
        v9.canonicalize_attempt_binding(incoming)


@pytest.mark.parametrize("flag", ["--attempt-path", "--generated-path"])
def test_attempt_02_child_paths_are_unreachable(flag: str) -> None:
    incoming = _child_arguments()
    index = incoming.index(flag)
    incoming[index + 1] = str(
        (v9.EVIDENCE_ROOT if flag == "--attempt-path" else v9.GENERATED_ROOT)
        / "attempt_02"
    )
    with pytest.raises(v9.LongEvaluationV9Error, match="not exact attempt_01"):
        v9.canonicalize_attempt_binding(incoming)


@pytest.mark.parametrize("nonce", ["A" * 64, "a" * 63, "g" * 64, "0" * 65])
def test_child_nonce_is_exact_lowercase_hex_64(nonce: str) -> None:
    incoming = _child_arguments()
    incoming[incoming.index("--child-nonce") + 1] = nonce
    with pytest.raises(v9.LongEvaluationV9Error, match="nonce is malformed"):
        v9.canonicalize_attempt_binding(incoming)


def test_parent_validation_and_retained_parser_consume_one_identical_value() -> None:
    public = retained.REQUIRED_PUBLIC_FLAGS[0]
    canonical = v9.canonicalize_attempt_binding(
        [public, "--attempt-label", "attempt_01"]
    )
    assert canonical.count("--attempt-label") == 1
    assert canonical[canonical.index("--attempt-label") + 1] == "attempt_01"
    parsed = retained.build_parser().parse_args(canonical)
    assert parsed.attempt_label == "attempt_01"
    assert parsed.child_run is False
    assert getattr(parsed, public[2:].replace("-", "_")) is True


def test_child_validation_and_retained_parser_consume_identical_exact_values() -> None:
    canonical = v9.canonicalize_attempt_binding(_child_arguments())
    for flag in ("--child-run", "--attempt-path", "--generated-path", "--child-nonce"):
        assert canonical.count(flag) == 1
    parsed = retained.build_parser().parse_args(canonical)
    assert parsed.child_run is True
    assert Path(parsed.attempt_path).resolve() == (
        v9.EVIDENCE_ROOT / "attempt_01"
    ).resolve()
    assert Path(parsed.generated_path).resolve() == (
        v9.GENERATED_ROOT / "attempt_01"
    ).resolve()
    assert parsed.child_nonce == "a" * 64


def test_main_forwards_the_same_canonical_list_to_retained_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded = v9.load_and_validate_v9_contract()
    observed: list[list[str]] = []
    monkeypatch.setattr(v9, "load_and_validate_v9_contract", lambda: loaded)
    monkeypatch.setattr(v9, "configure_retained_runner_v9", lambda *args, **kwargs: None)
    monkeypatch.setattr(retained, "main", lambda argv: observed.append(list(argv)) or 0)
    incoming = ["--attempt-label", "attempt_01", retained.REQUIRED_PUBLIC_FLAGS[0]]
    assert v9.main(incoming) == 0
    expected = v9.canonicalize_attempt_binding(incoming)
    assert observed == [expected]


def test_preexisting_hostile_v1_loader_is_rejected_and_canonical_restored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canonical = v9._CANONICAL_V1_LOADER

    def hostile() -> dict[str, bool]:
        return {"hostile": True}

    monkeypatch.setattr(v1, "load_and_validate_plan", hostile)
    with pytest.raises(v9.LongEvaluationV9Error, match="V1 loader binding drifted"):
        v9._load_v7_with_closed_v1(_reviewed())
    assert v1.load_and_validate_plan is canonical
    assert not v9._V1_COMPATIBILITY_LOCK.locked()


@pytest.mark.parametrize(
    ("module", "name"),
    [
        (v8, "_load_v1_plan_with_reviewed_shell_successor"),
        (v8, "configure_retained_runner_v8"),
        (v7, "load_and_validate_v7_contract"),
    ],
)
def test_preexisting_nested_loader_or_config_poison_is_rejected(
    monkeypatch: pytest.MonkeyPatch, module: object, name: str
) -> None:
    monkeypatch.setattr(module, name, lambda *args, **kwargs: {})
    with pytest.raises(v9.LongEvaluationV9Error, match="callable identity drifted"):
        v9._load_v7_with_closed_v1(_reviewed())
    assert v1.load_and_validate_plan is v9._CANONICAL_V1_LOADER
    assert not v9._V1_COMPATIBILITY_LOCK.locked()


def test_overlap_and_reentrancy_are_rejected_without_mutating_v1() -> None:
    assert v9._V1_COMPATIBILITY_LOCK.acquire(blocking=False)
    try:
        with pytest.raises(v9.LongEvaluationV9Error, match="overlapping or reentrant"):
            v9._load_v7_with_closed_v1(_reviewed())
        assert v1.load_and_validate_plan is v9._CANONICAL_V1_LOADER
    finally:
        v9._V1_COMPATIBILITY_LOCK.release()


def test_operation_exception_restores_exact_original_and_releases_lock() -> None:
    def explode() -> None:
        raise RuntimeError("bounded static failure")

    with pytest.raises(RuntimeError, match="bounded static failure"):
        v9._run_with_closed_v1_compatibility(_reviewed(), explode)
    assert v1.load_and_validate_plan is v9._CANONICAL_V1_LOADER
    assert not v9._V1_COMPATIBILITY_LOCK.locked()


def test_in_call_loader_mutation_fails_and_restores_exact_original() -> None:
    def mutate() -> None:
        v1.load_and_validate_plan = lambda: {"hostile": True}

    with pytest.raises(v9.LongEvaluationV9Error, match="changed inside"):
        v9._run_with_closed_v1_compatibility(_reviewed(), mutate)
    assert v1.load_and_validate_plan is v9._CANONICAL_V1_LOADER
    assert not v9._V1_COMPATIBILITY_LOCK.locked()


def test_captured_compatibility_gate_is_closed_after_bounded_call() -> None:
    captured: list[object] = []

    def capture() -> None:
        captured.append(v1.load_and_validate_plan)

    v9._run_with_closed_v1_compatibility(_reviewed(), capture)
    assert len(captured) == 1
    assert v1.load_and_validate_plan is v9._CANONICAL_V1_LOADER
    with pytest.raises(v9.LongEvaluationV9Error, match="closed outside its owner"):
        captured[0]()  # type: ignore[operator]


@pytest.mark.parametrize("binding", ["sys_modules", "package"])
def test_preexisting_v1_module_binding_poison_fails_closed(
    monkeypatch: pytest.MonkeyPatch, binding: str
) -> None:
    if binding == "sys_modules":
        monkeypatch.setitem(sys.modules, v1.__name__, object())
        expected = "sys.modules binding drifted"
    else:
        monkeypatch.setattr(
            v9.tools_package,
            "run_qwen35_kira_long_turing_health_body_voice_owner_evaluation",
            object(),
        )
        expected = "package binding drifted"
    with pytest.raises(v9.LongEvaluationV9Error, match=expected):
        v9._load_v7_with_closed_v1(_reviewed())
    assert v1.load_and_validate_plan is v9._CANONICAL_V1_LOADER
    assert not v9._V1_COMPATIBILITY_LOCK.locked()


def test_real_concurrency_rejects_overlap_and_off_thread_gate_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered = threading.Event()
    release = threading.Event()
    errors: list[BaseException] = []
    results: list[object] = []
    original_read_bytes = Path.read_bytes

    def blocked_read_bytes(path: Path) -> bytes:
        if path.resolve() == v7.V7_PLAN_PATH.resolve() and threading.current_thread().name == "v9-owner":
            entered.set()
            if not release.wait(5):
                raise AssertionError("bounded concurrency test timed out")
        return original_read_bytes(path)

    def invoke() -> None:
        try:
            results.append(v9._load_v7_with_closed_v1(_reviewed()))
        except BaseException as exc:  # recorded for exact static evidence
            errors.append(exc)

    monkeypatch.setattr(Path, "read_bytes", blocked_read_bytes)
    worker = threading.Thread(target=invoke, name="v9-owner")
    worker.start()
    assert entered.wait(5)
    try:
        with pytest.raises(v9.LongEvaluationV9Error, match="overlapping or reentrant"):
            v9._load_v7_with_closed_v1(_reviewed())
        with pytest.raises(v9.LongEvaluationV9Error, match="closed outside its owner"):
            v1.load_and_validate_plan()
    finally:
        release.set()
        worker.join(5)
    assert not worker.is_alive()
    assert errors == []
    assert len(results) == 1 and results[0][0]["schema_version"] == 7
    assert v1.load_and_validate_plan is v9._CANONICAL_V1_LOADER
    assert not v9._V1_COMPATIBILITY_LOCK.locked()


def test_v9_projection_never_calls_v8_unsafe_global_loader() -> None:
    source = Path(v9.__file__).read_text(encoding="utf-8")
    assert "v8.load_and_validate_v8_contract(" not in source
    assert "v8._load_v7_with_reviewed_shell(" not in source
    assert "_load_and_validate_v8_projection()" in source
    assert "_run_with_closed_v1_compatibility(" in source


def test_static_configuration_restores_v1_and_points_retained_at_v9() -> None:
    script = (
        "from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v9 as m;"
        "x=m.load_and_validate_v9_contract();"
        "m.configure_retained_runner_v9(*x,unattended=True);"
        "assert m.v1.load_and_validate_plan is m._CANONICAL_V1_LOADER;"
        "assert m.retained.EVIDENCE_ROOT == m.EVIDENCE_ROOT;"
        "assert m.retained.GENERATED_ROOT == m.GENERATED_ROOT;"
        "assert m.retained.load_preparation_contract()['schema_version'] == 9;"
        "print('STATIC_CONFIG_OK')"
    )
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "STATIC_CONFIG_OK"


@pytest.mark.parametrize("label", sorted(v7_tests.V7_FALSE_ACCEPTS))
def test_every_v7_independent_semantic_false_accept_remains_closed(label: str) -> None:
    turn_id, reply, expected = v7_tests.V7_FALSE_ACCEPTS[label]
    receipt = v7.semantic_grounding_receipt(
        {"id": turn_id, "text": "Give a bounded source-truthful answer."}, reply
    )
    assert receipt["passed"] is False
    assert expected in receipt["issues"]
    assert receipt["technical_pass_is_turing_acceptance"] is False


def test_v7_terminal_cleanup_exact_dict_finite_and_worker_absence_repairs_remain() -> None:
    release, status = v7_tests.v6_tests._full_release()
    assert v7.already_closed_final_release_issues(release, status) == []
    del status["any_owned_worker_running"]
    assert "v7_terminal_required_field_missing:status_after:any_owned_worker_running" in (
        v7.already_closed_final_release_issues(release, status)
    )


def test_unattended_output_never_claims_supervision_hearing_or_turing_acceptance() -> None:
    source = Path(v9.__file__).read_text(encoding="utf-8")
    assert '"unattended_log_only": True' in source
    assert '"physical_owner_supervision_claimed": False' in source
    assert '"owner_hearing_acknowledged": False' in source
    assert '"owner_hearing_pending": True' in source
    assert '"turing_psychology_acceptance": "PENDING_OWNER_OR_INDEPENDENT_REVIEW"' in source
    assert '"owner_hearing_acknowledged": True' not in source


def test_no_output_roots_or_heavy_runtime_imports_exist() -> None:
    assert not v9.EVIDENCE_ROOT.exists()
    assert not v9.GENERATED_ROOT.exists()
    heavy = {
        name
        for name in sys.modules
        if name == "torch"
        or name.startswith("torch.")
        or name == "ollama"
        or name.startswith("ollama.")
        or name == "chatterbox"
        or name.startswith("chatterbox.")
    }
    assert heavy == set()


def test_v9_repair_contract_is_closed_and_exact() -> None:
    assert _execution()["v9_repair_contract"] == v9._EXPECTED_V9_REPAIR
    assert set(_execution()) == set(v9._V9_TOP_LEVEL_KEYS)
    assert json.loads(v9.V9_PLAN_PATH.read_text(encoding="utf-8"))["status"] == (
        "STATIC_SUCCESSOR_NOT_EXECUTED_PENDING_DIFFERENT_FRESH_AUDIT"
    )
