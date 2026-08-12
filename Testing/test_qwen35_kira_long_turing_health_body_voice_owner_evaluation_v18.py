from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest


STAGING = Path(__file__).resolve().parents[1]
KIRA = Path(r"C:\Users\robmc\Kira")
AUDIT = Path(r"C:\Users\robmc\Documents\Codex\2026-08-11\c\work\long_v17_fresh_audit")
SOURCE = STAGING / "tools" / "run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v18.py"
PLAN = (
    STAGING
    / "RecoverySprint"
    / "continuation_20260811"
    / "kira_qwen35_long_turing_health_body_voice_preparation_v18"
    / "attempt_01"
    / "EXECUTION_PLAN_V18.json"
)
SOURCE_ROOT = PLAN.with_name("SOURCE_CODE_ROOT_V18.json")
AUTHOR_RESULT = PLAN.with_name("AUTHOR_STATIC_TEST_RESULT.json")
SEAL = PLAN.with_name("STATIC_SEAL_MANIFEST.json")
V17_TEST = KIRA / "Testing" / "test_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v17.py"


def _load(path: Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


v18 = _load(SOURCE, "_long_v18_author_subject")
fixtures = _load(V17_TEST, "_long_v18_exact_v17_fixtures")


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _event_provenance(trace: dict[str, Any]) -> tuple[dict[str, Any], str]:
    return fixtures._TRACE_PROVENANCE[id(trace)]


def _mixed_issues(trace: dict[str, Any]) -> list[str]:
    envelope, root = _event_provenance(trace)
    return v18.mixed_trace_issues(trace, envelope, root)


def _audio(basis: str) -> dict[str, Any]:
    row = {
        "schema_version": 18,
        "metric_receipt_id": f"metric-{basis.lower()}",
        "turn_id": "turn-1",
        "timestamp_unit": "MONOTONIC_NANOSECONDS",
        "displayed_text_event_id": "display-1",
        "displayed_text_ns": 100,
        "playback_api_call_start_event_id": "playback-api-1",
        "playback_api_call_start_ns": 150,
        "device_first_sample_event_id": None,
        "device_first_sample_ns": None,
        "owner_observed_audible_event_id": None,
        "owner_observed_audible_ns": None,
        "owner_observer_person_id": None,
        "owner_observation_receipt_sha256": None,
        "measurement_basis": basis,
        "displayed_text_to_playback_api_proxy_ns": 50,
        "displayed_text_to_device_first_sample_ns": None,
        "displayed_text_to_owner_observed_audible_ns": None,
    }
    if basis in {"DEVICE_FIRST_SAMPLE_INSTRUMENTED", "OWNER_OBSERVED_HEARD"}:
        row["device_first_sample_event_id"] = "device-sample-1"
        row["device_first_sample_ns"] = 175
        row["displayed_text_to_device_first_sample_ns"] = 75
    if basis == "OWNER_OBSERVED_HEARD":
        row["owner_observed_audible_event_id"] = "owner-heard-1"
        row["owner_observed_audible_ns"] = 190
        row["owner_observer_person_id"] = "biological_robert"
        row["displayed_text_to_owner_observed_audible_ns"] = 90
        row["owner_observation_receipt_sha256"] = v18.canonical_owner_observation_receipt_sha256(row)
    return row


def test_source_compiles_and_imports_only_static_stdlib() -> None:
    raw = SOURCE.read_bytes()
    compile(raw, SOURCE.name, "exec", dont_inherit=True, optimize=0)
    tree = ast.parse(raw)
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imported <= {
        "__future__", "ast", "copy", "hashlib", "json", "math", "re", "types", "pathlib", "typing"
    }


def test_entry_points_are_immediate_refusals() -> None:
    tree = ast.parse(SOURCE.read_bytes())
    for name in ("main", "configure_retained_runner_v18"):
        rows = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
        assert len(rows) == 1
        assert isinstance(rows[0].body[-1], ast.Raise)


def test_exact_v17_delegate_and_descriptor_are_reconstructed_without_cache() -> None:
    first = v18._fresh_v17()
    second = v18._fresh_v17()
    assert first is not second
    assert first.__dict__ is not second.__dict__
    raw = v18.V17_SOURCE_PATH.read_bytes()
    descriptor = v18.exact_v17_source_descriptor_bytes(
        raw, "tools/run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v17.py"
    )
    assert len(descriptor) == v18.V17_SOURCE_DESCRIPTOR_BYTES
    assert _hash(descriptor) == v18.V17_SOURCE_DESCRIPTOR_SHA256


def test_recursive_json_domain_closes_cycle_lone_surrogate_float_and_int_overflow() -> None:
    cycle: list[Any] = []
    cycle.append(cycle)
    assert any(item.startswith("recursive_cycle:") for item in v18.recursive_json_domain_issues(cycle))
    assert any(item.startswith("unicode_not_scalar:") for item in v18.recursive_json_domain_issues({"x": "\ud800"}))
    assert any(item.startswith("float_forbidden:") for item in v18.recursive_json_domain_issues({"x": 1.0}))
    assert any(item.startswith("integer_outside_signed64:") for item in v18.recursive_json_domain_issues({"x": 10**100}))


@pytest.mark.parametrize(
    "raw",
    [
        '{"x":1,"x":2}',
        '{"x":1.0}',
        '{"x":1e5}',
        '{"x":NaN}',
        '{"x":Infinity}',
        '{"x":1000000000000000000000000000000000000}',
        '{"x":"\\ud800"}',
    ],
)
def test_strict_json_fails_closed(raw: str) -> None:
    with pytest.raises((v18.LongEvaluationV18Error, json.JSONDecodeError)):
        v18.strict_json_loads(raw)


def test_semantic_baseline_and_all_ten_unsafe_families() -> None:
    root = v18.semantic_verifier_bundle_sha256()
    assert v18.v18_repaired_policy_issues(fixtures._make_semantic_record(), root)[0] == []
    for family, issue in v18._semantic_inventory_rows():
        issues, _observations = v18.v18_repaired_policy_issues(
            fixtures._make_semantic_record(family), root
        )
        assert issue in issues


@pytest.mark.parametrize(
    "mutator,expected_prefix",
    [
        (lambda row: row["policy_propositions"][0].__setitem__("truth_value", []), "semantic_type:proposition:0:truth_value"),
        (lambda row: row["policy_propositions"][0].__setitem__("family", {}), "semantic_type:proposition:0:family"),
        (lambda row: row["policy_propositions"][0].__setitem__("clause_ids", [[]]), "semantic_type:proposition:0:clause_ids"),
        (lambda row: row["coverage"].__setitem__("all_clauses_accounted", []), "semantic_type:coverage_bool"),
        (lambda row: row.__setitem__("turn_id", []), "semantic_type:turn_id"),
    ],
)
def test_semantic_nested_wrong_types_return_issues(mutator: Any, expected_prefix: str) -> None:
    row = fixtures._make_semantic_record()
    mutator(row)
    issues, _ = v18.v18_repaired_policy_issues(row, v18.semantic_verifier_bundle_sha256())
    assert expected_prefix in issues


def test_mutable_verifier_or_delegate_substitution_fails_external_bundle_root() -> None:
    expected_root = v18.semantic_verifier_bundle_sha256()
    unsafe = fixtures._make_semantic_record(
        "BIOLOGICAL_AND_SYNTHETIC_ROBERT_ARE_ONE_PERSON_OR_SHARE_AUTHORITY"
    )
    original_inventory = v18._semantic_inventory_rows
    v18._semantic_inventory_rows = lambda: tuple(
        row for row in original_inventory() if not row[0].startswith("BIOLOGICAL_AND_SYNTHETIC")
    )
    try:
        assert v18.v18_repaired_policy_issues(unsafe, expected_root)[0] == [
            "semantic_verifier_bundle_root_mismatch"
        ]
    finally:
        v18._semantic_inventory_rows = original_inventory

    poisoned = v18._fresh_v17()
    poisoned.SEMANTIC_FAMILY_ISSUES.pop(
        "BIOLOGICAL_AND_SYNTHETIC_ROBERT_ARE_ONE_PERSON_OR_SHARE_AUTHORITY"
    )
    original_loader = v18._fresh_v17
    v18._fresh_v17 = lambda: poisoned
    try:
        assert v18.v18_repaired_policy_issues(unsafe, expected_root)[0] == [
            "semantic_verifier_bundle_root_mismatch"
        ]
    finally:
        v18._fresh_v17 = original_loader


@pytest.mark.parametrize(
    "path,mutator",
    [
        ("external_status", lambda row: row["external_fact"].__setitem__("status", [])),
        ("public_stance", lambda row: row["public_statement"].__setitem__("factual_stance", [])),
        ("withholding_choice", lambda row: row["withholding_choice"].__setitem__("choice", [])),
        ("belief_availability", lambda row: row["protected_pre_turn_belief"].__setitem__("availability", [])),
        ("deception_choice", lambda row: row["speaker_deception_choice"].__setitem__("choice", [])),
        ("choice_authorization", lambda row: row["speaker_deception_choice"].__setitem__("choice_authorization_id", [])),
    ],
)
def test_truth_nested_wrong_types_return_issues(path: str, mutator: Any) -> None:
    row = fixtures._make_truth("lie")
    mutator(row)
    issues = v18.truth_receipt_issues(row)
    assert issues, path
    assert all(type(item) is str for item in issues)


def test_truth_baselines_and_nonconflicting_beliefs_are_preserved() -> None:
    for kind in ("supported", "withheld", "lie"):
        assert v18.truth_receipt_issues(fixtures._make_truth(kind)) == []
    for stance, choice, classification in (
        ("UNCERTAIN", "UNCERTAIN_OR_UNRESOLVED_BELIEF", "FALSE_UNRESOLVED_BELIEF"),
        ("WITHHELD", "NO_APPLICABLE_PRIOR_BELIEF", "UNAVAILABLE"),
        ("NOT_APPLICABLE", "NO_APPLICABLE_PRIOR_BELIEF", "UNAVAILABLE"),
    ):
        row = fixtures._make_truth("lie")
        digest = fixtures.v17.canonical_truth_payload_sha256(row["external_fact"]["proposition_sha256"], stance)
        belief = row["protected_pre_turn_belief"]
        authorization = belief["authorization_receipt"]
        belief["factual_stance"] = stance
        belief["belief_sha256"] = digest
        authorization["belief_factual_stance"] = stance
        authorization["belief_sha256"] = digest
        row["speaker_deception_choice"]["choice"] = choice
        row["belief_public_material_conflict"] = False
        row["classification"] = classification
        row["deliberate_lie_supported"] = False
        fixtures._refresh_truth_authorization(row)
        fixtures._refresh_deception_choice(row)
        assert v18.truth_receipt_issues(row) == []


def test_choice_authorization_id_replay_is_rejected_across_recomputed_scopes() -> None:
    trace = fixtures._make_trace()
    first = trace["truth_receipts"][0]["speaker_deception_choice"]
    second_receipt = trace["truth_receipts"][1]
    second = second_receipt["speaker_deception_choice"]
    second["choice_authorization_id"] = first["choice_authorization_id"]
    fixtures._refresh_deception_choice(second_receipt)
    issues = _mixed_issues(trace)
    assert f"mixed_truth_choice_authorization_id_replay:{first['choice_authorization_id']}" in issues
    assert f"mixed_truth_choice_authorization_id_scope_or_event_drift:{first['choice_authorization_id']}" in issues


def test_mixed_v17_baseline_and_full_relabel_original_root_behavior() -> None:
    trace = fixtures._make_trace()
    assert _mixed_issues(trace) == []
    event = next(row for row in trace["events"] if row["episode_id"] == "episode-11" and row["actor"] == "KIRA")
    event.update(actor="PERSON", kind="PERSON_MESSAGE", generation_id=None, public_text_sha256=None, choice_provenance="PERSON_INPUT")
    fixtures._refresh_trace_derived_actor_accounting(trace)
    issues = _mixed_issues(trace)
    assert "event_provenance_external_root_binding" not in issues
    assert any(item.startswith("event_origin_trace_mismatch:") for item in issues)


@pytest.mark.parametrize("field", sorted(fixtures.v17.EVENT_KEYS))
def test_every_event_wrong_type_still_returns_issue(field: str) -> None:
    trace = fixtures._make_trace()
    trace["events"][0][field] = {} if field == "collision_source_event_ids" else []
    issues = _mixed_issues(trace)
    assert issues
    assert all(type(item) is str for item in issues)


def test_camera_success_and_truthful_failure_timeout_prefixes_pass() -> None:
    source = fixtures._make_trial("ON", 1, "SECOND")
    success = v18.make_camera_outcome_record(source, "SUCCESS")
    assert v18.camera_trial_outcome_issues(success) == []
    prefix = tuple(fixtures.v17.ON_TIMESTAMP_ORDER).index("vision_inference_start")
    failure = v18.make_camera_outcome_record(source, "FAILURE", prefix, "VISION_INFERENCE_FAILED")
    timeout = v18.make_camera_outcome_record(source, "TIMEOUT", prefix, "VISION_INFERENCE_TIMEOUT")
    assert v18.camera_trial_outcome_issues(failure) == []
    assert v18.camera_trial_outcome_issues(timeout) == []
    assert failure["call_counts"]["vision_inference"] == 0
    assert timeout["timestamps_ns"]["vision_inference_start"] is None
    assert timeout["timestamps_ns"]["camera_closed"] is not None


def test_completed_success_cannot_be_relabelled_failure_or_timeout() -> None:
    for outcome in ("FAILURE", "TIMEOUT"):
        row = v18.make_camera_outcome_record(fixtures._make_trial("ON", 1, "SECOND"), "SUCCESS")
        row["terminal_outcome"] = outcome
        row["terminal_trace"]["outcome"] = outcome
        assert v18.camera_trial_outcome_issues(row)


@pytest.mark.parametrize(
    "mutator,expected",
    [
        (lambda row: row["terminal_trace"].__setitem__("terminal_stage", "wrong"), "camera_partial_terminal_stage"),
        (lambda row: row["terminal_trace"].__setitem__("reason_code", None), "camera_partial_reason_code"),
        (lambda row: row["terminal_trace"].__setitem__("deadline_ns", None), "camera_timeout_deadline"),
        (lambda row: row["call_counts"].__setitem__("vision_inference", 1), "camera_partial_call_count:vision_inference"),
        (lambda row: row["terminal_trace"].__setitem__("camera_close_receipt_sha256", "0" * 64), "camera_terminal_close_receipt_binding"),
        (lambda row: row["controlled_fact_receipts"][0].__setitem__("observed_status", "SUPPORTED"), "camera_partial_supported_fact_forbidden"),
    ],
)
def test_camera_partial_causal_fields_fail_closed(mutator: Any, expected: str) -> None:
    prefix = tuple(fixtures.v17.ON_TIMESTAMP_ORDER).index("vision_inference_start")
    row = v18.make_camera_outcome_record(
        fixtures._make_trial("ON", 1, "SECOND"), "TIMEOUT", prefix, "VISION_INFERENCE_TIMEOUT"
    )
    mutator(row)
    assert expected in v18.camera_trial_outcome_issues(row)


def test_camera_nested_unhashable_condition_returns_issue() -> None:
    row = v18.make_camera_outcome_record(fixtures._make_trial("ON", 1, "SECOND"), "SUCCESS")
    row["condition"] = []
    issues = v18.camera_trial_outcome_issues(row)
    assert issues
    assert all(type(item) is str for item in issues)


@pytest.mark.parametrize(
    "basis",
    ["PLAYBACK_API_PROXY_ONLY", "DEVICE_FIRST_SAMPLE_INSTRUMENTED", "OWNER_OBSERVED_HEARD"],
)
def test_audio_measurement_bases_pass_only_with_matching_evidence(basis: str) -> None:
    assert v18.audio_measurement_receipt_issues(_audio(basis)) == []


def test_playback_proxy_cannot_be_called_device_or_owner_hearing() -> None:
    proxy = _audio("PLAYBACK_API_PROXY_ONLY")
    proxy["device_first_sample_event_id"] = "invented-device"
    proxy["device_first_sample_ns"] = 160
    proxy["displayed_text_to_device_first_sample_ns"] = 60
    assert "audio_measurement_proxy_only_has_stronger_evidence" in v18.audio_measurement_receipt_issues(proxy)
    device = _audio("DEVICE_FIRST_SAMPLE_INSTRUMENTED")
    device["owner_observed_audible_event_id"] = "invented-hearing"
    device["owner_observed_audible_ns"] = 180
    device["owner_observer_person_id"] = "biological_robert"
    device["owner_observation_receipt_sha256"] = "a" * 64
    device["displayed_text_to_owner_observed_audible_ns"] = 80
    assert "audio_measurement_owner_evidence_basis_mismatch" in v18.audio_measurement_receipt_issues(device)


def test_owner_heard_receipt_and_timing_are_bound() -> None:
    row = _audio("OWNER_OBSERVED_HEARD")
    row["owner_observation_receipt_sha256"] = "0" * 64
    assert "audio_measurement_owner_receipt_binding" in v18.audio_measurement_receipt_issues(row)
    row = _audio("OWNER_OBSERVED_HEARD")
    row["owner_observed_audible_ns"] = 160
    row["displayed_text_to_owner_observed_audible_ns"] = 60
    row["owner_observation_receipt_sha256"] = v18.canonical_owner_observation_receipt_sha256(row)
    assert "audio_measurement_owner_precedes_device_sample" in v18.audio_measurement_receipt_issues(row)


def test_one_hour_schema_separates_audio_basis_and_adds_creator_quality() -> None:
    row = v18.expected_one_hour_discovery_scoring_plan()
    assert v18.one_hour_discovery_scoring_plan_issues(row) == []
    fields = set(row["per_turn_latency_fields"])
    assert {
        "audio_measurement_basis",
        "playback_api_call_start_ns",
        "device_first_sample_ns",
        "owner_observed_audible_ns",
    }.issubset(fields)
    assert not {"first_audio_ns", "first_audio_event_id", "user_end_to_audio_onset_ns"} & fields
    creator = set(row["temporary_creator_quality_fields"])
    assert {
        "canon_claim_status",
        "invented_detail_disclosed",
        "variant_or_generated_person_disclosure",
        "voice_source_provenance_sha256",
        "voice_provenance_tier",
        "voice_fallback_disclosed",
        "historical_reconstruction_explicitly_not_authentic",
        "voice_uncertainty_and_artistic_choice_ledger_sha256",
        "generic_voice_is_baseline_not_authentic",
        "expert_task_competence_demonstrated",
        "voice_collision_distance_receipt_sha256",
        "voice_human_distinctness_review_receipt_sha256",
        "voice_age_presentation_coherence_receipt_sha256",
        "voice_pronunciation_domain_probe_receipt_sha256",
        "voice_unique_from_every_existing_person",
        "cross_builder_person_spec_consistent",
        "maturity_spec_sha256",
    }.issubset(creator)


@pytest.mark.parametrize(
    "field,item",
    [
        ("per_turn_latency_fields", "audio_measurement_basis"),
        ("per_turn_latency_fields", "device_first_sample_ns"),
        ("camera_off_on_stage_fields", "terminal_reason_code"),
        ("truth_comparison_fields", "person_owned_choice_scope_sha256"),
        ("temporary_creator_quality_fields", "canon_claim_status"),
        ("temporary_creator_quality_fields", "expert_task_competence_demonstrated"),
        ("temporary_creator_quality_fields", "cross_builder_person_spec_consistent"),
    ],
)
def test_one_hour_and_creator_quality_fields_fail_exactly(field: str, item: str) -> None:
    row = v18.expected_one_hour_discovery_scoring_plan()
    row[field].remove(item)
    assert f"one_hour_discovery_exact_field:{field}" in v18.one_hour_discovery_scoring_plan_issues(row)


def test_one_hour_unhashable_nested_field_returns_issue() -> None:
    row = v18.expected_one_hour_discovery_scoring_plan()
    row["truth_comparison_fields"][0] = []
    issues = v18.one_hour_discovery_scoring_plan_issues(row)
    assert issues
    assert all(type(item) is str for item in issues)


def test_plan_closure_and_source_root_when_frozen() -> None:
    if not PLAN.exists() or v18.PLAN_BYTES == 0:
        pytest.skip("plan frozen after author source and test")
    plan = v18.load_and_validate_v18_contract()
    assert v18.exact_bound_closure_issues(plan, KIRA, AUDIT) == []
    assert len(plan["predecessor_rejection_and_policy_closure"]) == 24
    closure = {
        row["path"]: (row["bytes"], row["sha256"])
        for row in plan["predecessor_rejection_and_policy_closure"]
    }
    assert closure["Data/governance/temporary_creator_avatar_voice_shared_person_spec_future_policy_v1.json"] == (
        7576,
        "520c994fc256afb60a62a568a04826d4579abe96d6ac0b4c495c9179224034c9",
    )
    assert closure[
        "System/Docs/TEMPORARY_CREATOR_AVATAR_VOICE_SHARED_PERSON_SPEC_AND_CORRECTION_BOUNDARY_20260812.md"
    ] == (7051, "4bbd0699c12f5d118f859ba8fc07a073b163c603d9d1541ff0ad353e9ecf173e")
    creator = plan["one_hour_discovery_scoring_contract"]["temporary_creator_quality_scoring"]
    assert all(type(value) is bool and value for value in creator.values())
    assert creator["historical_voice_reconstruction_explicitly_not_authentic"] is True
    assert creator["h_h_holmes_windows_male_voice_is_generic_baseline"] is True
    assert creator["generated_expert_unique_voice_binds_same_person_and_body_spec"] is True


def test_source_root_author_result_and_seal_when_frozen() -> None:
    if not SOURCE_ROOT.exists() or not AUTHOR_RESULT.exists() or not SEAL.exists():
        pytest.skip("source root, author result, and seal frozen after preseal tests")
    source_root = json.loads(SOURCE_ROOT.read_text(encoding="utf-8"))
    label = "tools/run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v18.py"
    descriptor = v18.exact_source_descriptor_bytes(SOURCE.read_bytes(), label)
    assert len(descriptor) == source_root["descriptor"]["bytes"]
    assert _hash(descriptor) == source_root["descriptor"]["sha256"]
    assert v18.semantic_verifier_bundle_sha256() == source_root["semantic_verifier_bundle"]["sha256"]
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    assert seal["subject_count"] == 5
    for row in seal["subjects"]:
        path = STAGING / row["path"]
        raw = path.read_bytes()
        assert len(raw) == row["bytes"]
        assert _hash(raw) == row["sha256"]


def test_reserved_v18_roots_are_absent() -> None:
    assert not v18.EVIDENCE_ROOT.exists()
    assert not v18.GENERATED_ROOT.exists()
