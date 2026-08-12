from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
from pathlib import Path


HERE = Path(__file__).resolve().parent
KIRA_ROOT = Path(os.environ.get("KIRA_TEST_PROJECT_ROOT", r"C:\Users\robmc\Kira")).resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows() -> list[dict[str, str]]:
    with (HERE / "INPUT_CLOSURE.tsv").open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    assert rows
    assert tuple(rows[0]) == ("role", "path", "bytes", "sha256", "status")
    return rows


def load_json(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def test_input_closure_is_exact_unique_and_complete_41_of_41() -> None:
    rows = load_rows()
    contract = load_json("STATIC_CONTRACT.json")
    closure = contract["input_closure"]
    assert len(rows) == closure["row_count_excluding_header"] == 41
    paths = [row["path"] for row in rows]
    assert len(paths) == len(set(paths))
    assert {row["role"] for row in rows} == set(closure["roles_required"])
    for row in rows:
        relative = Path(row["path"])
        assert "\\" not in row["path"]
        assert not relative.is_absolute()
        assert ".." not in relative.parts
        assert len(row["sha256"]) == 64 and row["sha256"] == row["sha256"].lower()
        int(row["sha256"], 16)
        target = KIRA_ROOT / relative
        assert target.is_file(), row["path"]
        assert target.stat().st_size == int(row["bytes"]), row["path"]
        assert sha256_file(target) == row["sha256"], row["path"]


def test_contract_is_default_off_pending_different_audit_and_claims_no_speed() -> None:
    contract = load_json("STATIC_CONTRACT.json")
    assert contract["status"] == "AUTHOR_SEALED_STATIC_ONLY_PENDING_DIFFERENT_FRESH_AUDIT"
    assert contract["implementation_present"] is contract["author_seal_present"] is True
    assert contract["execution_authority"] == "NONE"
    for field in (
        "production_route_changed",
        "model_or_gpu_execution_authorized",
        "synthesis_or_playback_authorized",
        "camera_or_microphone_authorized",
        "network_authorized",
        "latency_measurements_present",
        "latency_improvement_claimed",
    ):
        assert contract[field] is False
    assert contract["current_boundary"] == "DO_NOT_RUN_COPY_OR_INTEGRATE_V20_PRODUCTION_V2_UNCHANGED"


def test_exact_route_and_controlling_failure_measurements_are_preserved() -> None:
    contract = load_json("STATIC_CONTRACT.json")
    route = contract["exact_route"]
    assert route["text_model"] == "qwen3.5:9b"
    assert route["text_model_digest"] == "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
    assert route["voice_route"] == "blackwell_gpu"
    assert route["generic_voice_allowed"] is route["sapi_allowed"] is route["llama_allowed"] is False
    measurements = contract["controlling_measurements_seconds"]
    assert measurements["persistent_v2_reload_prewarm_min"] == 5.577
    assert measurements["persistent_v2_reload_prewarm_max"] == 5.908
    assert measurements["true_audio_device_first_sample_measured"] is False
    assert measurements["owner_heard_onset_measured"] is False
    assert measurements["verdict"] == "LATENCY_FAIL_PENDING_MATCHED_MEASUREMENT"


def test_direct_worker_is_append_only_mock_only_and_has_no_live_stack_imports() -> None:
    contract = load_json("STATIC_CONTRACT.json")
    worker = contract["direct_worker_implementation"]
    assert worker["runtime_monkeypatch_used"] is False
    assert worker["live_factory_unconditionally_refuses"] is True
    assert worker["author_fixture_exact_execution_authorized_value"] is False
    assert worker["required_components"] == ["t3", "s3gen", "ve"]
    assert worker["one_conditioned_generation_load_count"] == 1
    assert worker["one_reference_conditioning_count"] == 1
    source = (HERE / "voice_v20_worker.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imports.isdisjoint({"torch", "chatterbox", "ollama", "cv2", "pyaudio", "sounddevice"})
    assert "def live_candidate" in source and "raise V20NotAuthorized" in source


def test_state_machine_resource_and_control_binding_are_complete() -> None:
    contract = load_json("STATIC_CONTRACT.json")
    assert contract["required_state_machine"] == [
        "UNLOADED",
        "LOADED_CUDA",
        "PARKED_CPU",
        "QWEN_OWNED",
        "PARKED_CPU",
        "LOADED_CUDA",
        "SYNTHESIZED",
        "PARKED_CPU",
    ]
    bounds = contract["resource_bounds_initial_author_proposal"]
    assert bounds["minimum_available_physical_mib_before_park"] == 6144
    assert bounds["maximum_parked_worker_rss_mib"] == 10240
    assert bounds["maximum_job_memory_mib"] == 16384
    assert bounds["maximum_system_commit_fraction"] == 0.82
    assert bounds["minimum_cuda_free_mib_before_restore"] == 4096
    binding = contract["immutable_control_binding"]
    assert binding["canonical_control_module_object_path_and_source_bytes"] is True
    assert binding["canonical_worker_class_object_and_all_control_method_descriptors"] is True
    assert binding["control_function_object_code_defaults_kwdefaults_closure_and_referenced_globals"] is True
    assert binding["exact_recursive_list_set_dict_tuple_and_frozenset_binding"] is True
    assert binding["backend_object_class_module_and_exact_bound_methods"] is True
    assert binding["runtime_mutation_still_requires_different_hostile_audit"] is True


def test_native_source_and_recorded_strict_build_are_default_off() -> None:
    contract = load_json("STATIC_CONTRACT.json")
    supervisor = contract["native_supervisor_implementation"]
    assert supervisor["source_only_not_execution_package"] is True
    assert supervisor["wmain_default_refusal_exit_code"] == 125
    assert supervisor["assign_kill_on_close_job_before_resume"] is True
    assert supervisor["prove_job_membership_and_limits_before_resume"] is True
    assert supervisor["one_use_ledger_create_new_no_sharing_write_through"] is True
    assert supervisor["terminal_outcome_appended_and_flushed_on_same_handle"] is True
    assert supervisor["silent_retry_allowed"] is supervisor["second_worker_allowed"] is False
    build = load_json("NATIVE_BUILD_STATIC_RESULT.json")
    assert build["status"] == "PASS_SOURCE_COMPILE_AND_STATIC_ANALYSIS_ONLY"
    assert build["execution_performed"] is False
    assert build["w4_wx_compile_exit_code"] == 0
    assert build["analyze_w4_wx_exit_code"] == 0
    assert build["linked_executable_created"] is False


def test_matched_schema_copies_v19_exact_arrays_and_adds_device_timing() -> None:
    schema = load_json("MATCHED_EXPERIMENT_SCHEMA.json")
    v19_path = KIRA_ROOT / "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v19/native_control_contract.json"
    v19 = json.loads(v19_path.read_text(encoding="utf-8"))["future_matched_camera_text_voice_timing"]
    assert schema["conditions"] == v19["conditions"]
    assert schema["required_monotonic_timestamps"] == v19["required_monotonic_timestamps"]
    assert schema["required_metadata"] == v19["required_metadata"]
    assert schema["required_derived_durations"] == v19["required_derived_durations"]
    assert schema["ordering_requirements"] == v19["ordering_requirements"]
    assert [len(schema[key]) for key in (
        "conditions",
        "required_monotonic_timestamps",
        "required_metadata",
        "required_derived_durations",
        "ordering_requirements",
    )] == [4, 51, 42, 30, 15]
    assert "audio_device_first_sample" in schema["v20_required_timestamps_additions"]
    assert "owner_heard_onset_optional" in schema["v20_required_metadata_additions"]
    assert schema["success_rule"]["requires_lower_median"] is True
    assert schema["success_rule"]["requires_lower_worst_case"] is True
    assert schema["success_rule"]["one_faster_sample_is_success"] is False


def test_consumed_failures_rejections_and_production_v2_are_not_superseded() -> None:
    truth = load_json("STATIC_CONTRACT.json")["preserved_predecessor_truth"]
    assert truth["v8_launcher_identity_attempt"] == "CONSUMED_FAILURE_DO_NOT_RERUN"
    assert truth["v9_live_attempt"] == "CONSUMED_FAILURE_UNTYPED_CTYPES_POINTER_WIDTH_DO_NOT_RERUN"
    assert truth["v11"] == "REJECTED_MODULE_OBJECT_SUBSTITUTION_NO_RUN"
    assert truth["v12"] == "REJECTED_CANONICAL_CONTROL_CALLABLE_GLOBAL_SUBSTITUTION_NO_RUN"
    assert truth["v19_result_and_camera_timing_schema"] == "ACCEPTED_STATIC_BOUND_EXACTLY_NO_RUN"
    assert truth["production_v2"] == "UNCHANGED"


def test_downstream_person_spec_and_voice_provenance_never_claim_false_authenticity() -> None:
    contract = load_json("STATIC_CONTRACT.json")
    requirement = contract["downstream_person_spec_and_voice_provenance_requirement"]
    assert requirement["one_exact_person_spec_sha256_across_all_three_builders"] is True
    assert requirement["required_person_spec_fields"] == [
        "identity",
        "source_or_variant",
        "era_or_branch",
        "maturity",
        "body_spec_sha256",
        "voice_provenance",
    ]
    assert requirement["voice_provenance_classes"] == [
        "SOURCE_RECORDING_BACKED_MATCH",
        "AUDITIONED_APPROXIMATION",
        "GENERIC_FALLBACK",
    ]
    assert requirement["auditioned_approximation_may_be_called_authentic"] is False
    assert requirement["generic_fallback_may_be_called_authentic"] is False
    assert requirement["windows_male_voice_may_be_presented_as_historical_authentic_voice"] is False
    assert requirement["later_voice_replacement_supported_without_identity_or_body_spec_drift"] is True
    assert requirement["speaker_playback_owner_permitted_but_v20_authorized_now"] is False
    schema = load_json("MATCHED_EXPERIMENT_SCHEMA.json")
    provenance = schema["voice_provenance_contract"]
    assert provenance["no_recording_exists_requires_explicit_uncertainty"] is True
    assert provenance["windows_voice_may_be_labeled_historical_authentic"] is False
    assert "person_spec_sha256" in schema["v20_required_metadata_additions"]
    assert "auditioned_or_generic_voice_is_never_labeled_source_recording_backed" in schema["v20_pair_identity_requirements"]


def test_remaining_sequence_requires_different_audits_before_any_run() -> None:
    sequence = load_json("STATIC_CONTRACT.json")["remaining_append_only_steps"]
    assert sequence == [
        "DIFFERENT_EXACT_BYTE_STATIC_AUDIT_OF_THIS_SEAL",
        "IF_ACCEPTED_AUTHOR_A_SEPARATE_NON_MODEL_NATIVE_CONTROLLER_HOSTILE_VALIDATION_PACKAGE",
        "DIFFERENT_AUDIT_OF_THAT_CONTROLLER_PACKAGE",
        "IF_ACCEPTED_AUTHOR_A_SEPARATE_ONE_USE_EXECUTION_PACKAGE",
        "DIFFERENT_RUN_AUTHORITY_AUDIT",
        "ONE_MATCHED_OWNER_SCOPED_EXPERIMENT",
        "ACCEPT_REJECT_FROM_EXACT_TEXT_AUDIO_DEVICE_MEMORY_AND_CAMERA_EVIDENCE",
    ]


def test_static_seal_exactly_binds_all_author_subjects() -> None:
    seal = load_json("STATIC_SEAL_MANIFEST.json")
    assert seal["status"] == "AUTHOR_SEALED_STATIC_ONLY_PENDING_DIFFERENT_FRESH_AUDIT"
    assert seal["execution_authority"] == "NONE"
    assert seal["candidate_executed"] is False
    assert seal["latency_improvement_claimed"] is False
    subjects = seal["subjects"]
    expected = {
        "INPUT_CLOSURE.tsv",
        "STATIC_CONTRACT.json",
        "voice_v20_worker.py",
        "voice_v20_native_supervisor.c",
        "MATCHED_EXPERIMENT_SCHEMA.json",
        "README.md",
        "NATIVE_BUILD_STATIC_RESULT.json",
        "test_voice_v20_contract.py",
        "test_voice_v20_worker_hostile.py",
    }
    assert seal["sealed_subject_count"] == len(subjects) == len(expected)
    assert {row["path"] for row in subjects} == expected
    for row in subjects:
        path = HERE / row["path"]
        assert path.is_file()
        assert path.stat().st_size == row["bytes"]
        assert sha256_file(path) == row["sha256"]
