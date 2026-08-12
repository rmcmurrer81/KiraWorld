from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


INSTALLED = Path(
    r"C:\Users\robmc\Kira\RecoverySprint\continuation_20260811"
    r"\blackwell_voice_v20_measured_latency_successor_static_preparation\attempt_01"
)
sys.path.insert(0, str(INSTALLED))

import test_voice_v20_worker_hostile as author_fixture  # noqa: E402


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def probe_backend_bound_object_map_substitution() -> dict[str, object]:
    worker, _backend, clock = author_fixture.make_worker()
    original = worker._binding.backend_bound_objects["sample_resources"]
    calls: list[str] = []

    def substituted(**kwargs: object) -> object:
        calls.append(str(kwargs["label"]))
        return original(**kwargs)

    worker._binding.backend_bound_objects["sample_resources"] = substituted
    result = worker.load_once(deadline_ns=author_fixture.deadline(clock))
    verified_state = worker.status()["state"]
    return {
        "substitution_was_invoked": calls == ["load_before", "load_after"],
        "substituted_call_labels": calls,
        "operation_succeeded": result["success"] is True,
        "state_after_verify": verified_state,
    }


def probe_mutable_authority() -> dict[str, object]:
    worker, _backend, _clock = author_fixture.make_worker(maximum_turns=1)
    before = worker.status()
    worker.authority["maximum_turns"] = 4
    worker.authority["expires_monotonic_ns"] = 10**30
    worker.authority["owner_hash"] = "f" * 64
    after = worker.status()
    return {
        "before_maximum_turns": before["maximum_turns"],
        "after_maximum_turns": after["maximum_turns"],
        "mutated_expiry_retained": worker.authority["expires_monotonic_ns"] == 10**30,
        "mutated_owner_retained": worker.authority["owner_hash"] == "f" * 64,
        "graph_verification_still_passed": after["state"] == "UNLOADED",
    }


def probe_self_authenticated_stale_qwen_receipt() -> dict[str, object]:
    worker, _backend, clock = author_fixture.prepare_parked_worker(maximum_turns=1)
    turn_id = digest("fresh-audit-turn")
    token_hash = digest("fresh-audit-token")
    request_hash = digest("fresh-audit-request")
    grant = worker.enter_qwen_window(
        turn_id=turn_id,
        token_hash=token_hash,
        request_sha256=request_hash,
        deadline_ns=author_fixture.deadline(clock),
    )
    receipt = author_fixture.qwen_receipt(worker, turn_id, token_hash, request_hash)
    grant_entered = grant["transition"]["entered_monotonic_ns"]
    accepted = worker.complete_qwen_window(
        receipt=receipt,
        deadline_ns=author_fixture.deadline(clock),
    )
    return {
        "receipt_unload_completed_ns": receipt["unload_completed_ns"],
        "qwen_window_grant_entered_ns": grant_entered,
        "receipt_entirely_predates_grant": receipt["unload_completed_ns"] < grant_entered,
        "receipt_has_external_signature_or_mac": False,
        "stale_self_hashed_receipt_accepted": accepted["success"] is True,
        "state_after_accept": accepted["state"],
    }


def probe_experiment_schema() -> dict[str, object]:
    schema = json.loads((INSTALLED / "MATCHED_EXPERIMENT_SCHEMA.json").read_text("utf-8"))
    derived = set(schema["required_derived_durations"])
    additions = set(schema["v20_required_timestamps_additions"])
    success = schema["success_rule"]
    return {
        "audio_device_timestamp_present": "audio_device_first_sample" in additions,
        "device_first_sample_derived_metrics": sorted(
            name for name in derived if "device" in name or "heard" in name
        ),
        "success_rule_names_controlling_metric": any(
            key in success for key in ("metric", "metric_id", "primary_metric", "metrics")
        ),
        "owner_heard_is_timestamp": "owner_heard_onset" in additions,
        "measurement_method_has_closed_enum": isinstance(
            schema.get("device_first_sample_measurement_methods"), list
        ),
    }


def probe_native_path_binding() -> dict[str, object]:
    source = (INSTALLED / "voice_v20_native_supervisor.c").read_text("utf-8")
    ledger_call = "CreateFileW(ledger_path, GENERIC_READ | GENERIC_WRITE" in source
    return {
        "ledger_created_by_absolute_or_string_path": ledger_call,
        "handle_relative_root_directory_creation_present": "RootDirectory" in source,
        "nt_create_file_present": "NtCreateFile" in source or "NtCreateFile" in source,
        "created_ledger_identity_requeried": "GetFileInformationByHandle(ledger->handle" in source,
        "created_ledger_security_digest_requeried": "v20_security_digest(ledger->handle" in source,
    }


def main() -> None:
    result = {
        "schema": "kira.blackwell.voice_v20.different_fresh_hostile_probe.v1",
        "installed_root": str(INSTALLED),
        "candidate_or_live_stack_executed": False,
        "model_gpu_audio_playback_camera_microphone_network_calls": 0,
        "backend_bound_object_map_substitution": probe_backend_bound_object_map_substitution(),
        "mutable_authority": probe_mutable_authority(),
        "stale_self_hashed_qwen_receipt": probe_self_authenticated_stale_qwen_receipt(),
        "experiment_schema": probe_experiment_schema(),
        "native_path_binding": probe_native_path_binding(),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
