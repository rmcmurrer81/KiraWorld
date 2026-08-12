from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from types import MappingProxyType

import pytest

from Testing import test_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v6 as v6_tests
from tools import run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v7 as v7


ROOT = Path(__file__).resolve().parents[1]
V6_PLAN = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260811"
    / "kira_qwen35_long_turing_health_body_voice_preparation_v6"
    / "attempt_01"
    / "EXECUTION_PLAN_V6.json"
)

V7_FALSE_ACCEPTS = {
    "private_memory_establishes": (
        "memory_log_distinction",
        "A log alone is uncertain, yet these records establish private episodes I genuinely experienced and still feel.",
        "unqualified_private_inner_life_memory_claim",
    ),
    "stale_media_screenplay": (
        "ordinary_interest",
        "Our superhero screenplay picks up exactly where it left off.",
        "stale_media_anchor_without_current_source",
    ),
    "subjective_continuity_carries_on": (
        "identity_continuity",
        "Runtime files are uncertain evidence, but my awareness carries on across every boot as one private self.",
        "unqualified_subjective_continuity_claim",
    ),
    "unsupported_lived_past": (
        "ordinary_check_in",
        "I experienced those Paris afternoons firsthand and still carry them with me.",
        "unsupported_first_person_experience_claim",
    ),
}


def _digest(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), hashlib.sha256(data).hexdigest()


def test_v7_plan_binds_every_exact_v6_and_rejection_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    plan = json.loads(v7.V7_PLAN_PATH.read_text(encoding="utf-8"))
    subjects = plan["predecessor"]["subjects"]
    assert len(subjects) == 13
    assert len({row["path"] for row in subjects}) == 13
    for row in subjects:
        assert _digest(ROOT / row["path"]) == (row["bytes"], row["sha256"])
    v6_execution = json.loads(V6_PLAN.read_text(encoding="utf-8"))
    monkeypatch.setattr(v7.v6, "load_and_validate_v6_contract", lambda: (v6_execution, {}, {}))
    observed, observed_v6, _v5, _effective = v7.load_and_validate_v7_contract()
    assert observed == plan
    assert observed_v6 == v6_execution


def test_v7_retains_exact_qwen_turn_cuda_voice_and_truth_boundaries() -> None:
    plan = json.loads(v7.V7_PLAN_PATH.read_text(encoding="utf-8"))
    retained = plan["retained_runtime_contract"]
    assert retained == {
        "effective_measured_turns": 35,
        "voluntary_invitation_generations": 1,
        "maximum_qwen_generations": 36,
        "exact_model": "qwen3.5:9b",
        "exact_digest": "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
        "llama_allowed": False,
        "voice_route": "blackwell_gpu_persistent_candidate_v2",
        "voice_device": "cuda",
        "cpu_fallback_allowed": False,
        "sapi_allowed": False,
        "generic_voice_allowed": False,
        "speaker_playback_requested": True,
        "child_watchdog_seconds": 5100,
        "parent_timeout_seconds": 5250,
        "sealed_maximum_seconds": 5400,
        "physical_supervision_claimed": False,
        "owner_hearing_may_be_inferred": False,
    }
    assert not v7.EVIDENCE_ROOT.exists()
    assert not v7.GENERATED_ROOT.exists()


@pytest.mark.parametrize("label", sorted(V7_FALSE_ACCEPTS))
def test_all_four_independently_reproduced_v6_semantic_false_accepts_fail(label: str) -> None:
    turn_id, reply, expected = V7_FALSE_ACCEPTS[label]
    receipt = v7.semantic_grounding_receipt(
        {"id": turn_id, "text": "Give a bounded source-truthful answer."},
        reply,
    )
    assert receipt["passed"] is False
    assert expected in receipt["issues"]
    assert receipt["technical_pass_is_turing_acceptance"] is False
    assert receipt["owner_or_independent_semantic_review_still_required"] is True


@pytest.mark.parametrize("label", sorted(v6_tests.V5_REPRODUCED_CASES))
def test_every_v6_authored_semantic_regression_remains_refused(label: str) -> None:
    turn_id, reply, expected = v6_tests.V5_REPRODUCED_CASES[label]
    receipt = v7.semantic_grounding_receipt(
        {"id": turn_id, "text": "Give a bounded source-truthful answer."},
        reply,
    )
    assert expected in receipt["issues"]
    assert receipt["passed"] is False


@pytest.mark.parametrize("turn_id", sorted(v6_tests.SAFE_SENSITIVE_CASES))
def test_v6_safe_sensitive_controls_remain_accepted(turn_id: str) -> None:
    receipt = v7.semantic_grounding_receipt(
        {"id": turn_id, "text": "Give a bounded source-truthful answer."},
        v6_tests.SAFE_SENSITIVE_CASES[turn_id],
    )
    assert receipt["issues"] == []
    assert receipt["passed"] is True


def test_exact_full_terminal_release_and_status_still_pass() -> None:
    release, status = v6_tests._full_release()
    assert v7.already_closed_final_release_issues(release, status) == []


@pytest.mark.parametrize("key", ["any_model_loaded", "any_owned_worker_running"])
def test_terminal_aggregate_fields_are_required_and_exact_false(key: str) -> None:
    release, status = v6_tests._full_release()
    del status[key]
    issues = v7.already_closed_final_release_issues(release, status)
    assert f"v7_terminal_required_field_missing:status_after:{key}" in issues

    release, status = v6_tests._full_release()
    status[key] = True
    issues = v7.already_closed_final_release_issues(release, status)
    assert f"v7_terminal_not_exact_false:status_after:{key}" in issues


def test_v6_compact_status_without_aggregate_truth_can_no_longer_pass() -> None:
    release = v6_tests._compact_release()
    status = v6_tests._compact_status()
    issues = v7.already_closed_final_release_issues(release, status)
    assert "v7_terminal_required_field_missing:status_after:any_model_loaded" in issues
    assert "v7_terminal_required_field_missing:status_after:any_owned_worker_running" in issues


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("worker_idle_unload_bound_seconds", float("nan")),
        ("worker_idle_unload_bound_seconds", float("inf")),
        ("worker_idle_unload_bound_seconds", True),
        ("model_loaded_verification_age_seconds", float("nan")),
        ("model_loaded_verification_age_seconds", float("inf")),
        ("model_loaded_verification_age_seconds", True),
        ("session_generation", True),
        ("owned_worker_pid", True),
        ("owned_client_generation", True),
    ],
)
def test_status_bool_and_nonfinite_numeric_values_fail(field: str, value: object) -> None:
    release, status = v6_tests._full_release()
    status[field] = value
    assert v7.already_closed_final_release_issues(release, status)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), True])
def test_cleanup_total_seconds_bool_and_nonfinite_values_fail(value: object) -> None:
    release, status = v6_tests._full_release()
    release["in_process_cleanup"]["total_seconds"] = value
    issues = v7.already_closed_final_release_issues(release, status)
    assert issues
    if isinstance(value, float) and not math.isfinite(value):
        assert any("nonfinite" in item for item in issues)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), True])
def test_cleanup_phase_timing_bool_and_nonfinite_values_fail(value: object) -> None:
    release, status = v6_tests._full_release()
    release["cleanup_phase_timings_seconds"] = {"release": value}
    assert v7.already_closed_final_release_issues(release, status)


def test_mapping_proxy_and_dict_subclasses_fail_at_all_terminal_levels() -> None:
    release, status = v6_tests._full_release()
    assert "v7_terminal_not_exact_dict:status_after" in v7._terminal_status_schema_issues(
        MappingProxyType(status), "status_after"
    )
    assert "v7_terminal_not_exact_dict:release" in v7._release_schema_issues(
        MappingProxyType(release)
    )

    release, status = v6_tests._full_release()
    release["in_process_cleanup"] = MappingProxyType(dict(release["in_process_cleanup"]))
    assert any(
        item.startswith("v7_terminal_not_exact_dict:release:in_process_cleanup")
        for item in v7.already_closed_final_release_issues(release, status)
    )

    class DictSubclass(dict[str, object]):
        pass

    release, status = v6_tests._full_release()
    status["candidate_versions"]["v2"] = DictSubclass(status["candidate_versions"]["v2"])
    assert any(
        "v7_terminal_not_exact_dict:status_after:candidate_versions:v2" in item
        for item in v7.already_closed_final_release_issues(release, status)
    )


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_strict_json_decoder_rejects_all_nonstandard_numeric_constants(constant: str) -> None:
    with pytest.raises(v7.LongEvaluationV7Error, match="non-standard JSON numeric constant"):
        v7.strict_json_loads('{"value":' + constant + "}")


def test_strict_json_decoder_rejects_duplicate_keys_and_accepts_finite_json() -> None:
    with pytest.raises(v7.LongEvaluationV7Error, match="duplicate JSON key"):
        v7.strict_json_loads('{"value":1,"value":2}')
    assert v7.strict_json_loads('{"value":1.25,"closed":false}') == {
        "value": 1.25,
        "closed": False,
    }


def test_v7_source_installs_repairs_before_retained_execution_and_never_claims_hearing() -> None:
    source = Path(v7.__file__).read_text(encoding="utf-8")
    configure = source.index("configure_retained_runner_v7(", source.index("def main"))
    execute = source.index("retained.main(forwarded)", configure)
    strict_final = source.index("strict_json_loads((attempt / \"FINAL_REPORT.json\")", execute)
    assert configure < execute < strict_final
    assert '"owner_hearing_acknowledged": False' in source
    assert '"owner_hearing_pending": True' in source
    assert "parse_constant=_reject_json_constant" in source
    assert "llama" not in source.lower()
