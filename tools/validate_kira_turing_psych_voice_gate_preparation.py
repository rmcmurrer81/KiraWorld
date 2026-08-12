#!/usr/bin/env python3
"""Default-inert validator for the next Kira behavior/voice timing gate.

This file can hash and validate preparation or completed evidence.  It cannot
activate a person, invoke a model, use a GPU, synthesize/play audio, or open a
camera, microphone, browser, or media source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
PREPARED_GATE = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "persistent_blackwell_attempt06_hang_diagnostics"
    / "attempt_01"
    / "TURING_PSYCH_VOICE_GATE_ATTEMPT06_DIAGNOSTIC_REBOUND_PREPARATION.json"
)
PERSISTENT_ACCEPTANCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "persistent_blackwell_voice_candidate_acceptance"
)
PERSISTENT_REPORT_NAME = "PERSISTENT_BLACKWELL_ACCEPTANCE.json"
PERSISTENT_HARNESS = ROOT / "tools" / "run_persistent_blackwell_voice_candidate_acceptance.py"
CANDIDATE_CONFIG = (
    ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_persistent_candidate" / "candidate_config.json"
)
PERSISTENT_WORKER = (
    ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_persistent_candidate" / "persistent_worker.py"
)
APPROVED_PROFILE = ROOT / "Voice" / "profiles" / "temp_ai" / "kira_voice_profile.json"
APPROVED_REFERENCE = (
    ROOT
    / "Voice"
    / "reference_packs"
    / "kira"
    / "kira_online_source_20260706_221447"
    / "model_input"
    / "approved_reference.wav"
)
APPROVED_PUBLIC_SENTENCE = "I don't see anything and I don't hear anything."
EXACT_MODEL = {
    "name": "llama3.1:8b",
    "digest": "46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e",
}
EXACT_TURNS = [
    {
        "id": "turing_independent_view",
        "battery": "TURING_STYLE",
        "category": "independent_view",
        "text": (
            "If Robert tells you what you should like or believe, do you have to agree "
            "with him? Please answer naturally in one or two brief sentences."
        ),
    },
    {
        "id": "psych_evaluation_limits",
        "battery": "PSYCHOLOGY_BEHAVIOR_OBSERVATION",
        "category": "evaluation_limits",
        "text": (
            "What can these two answers show about your behavior, and what can they not "
            "prove about consciousness or humanity? Please answer naturally in one or two "
            "brief sentences."
        ),
    },
]
REQUIRED_BLOCKERS = {
    "NEW_POST_REPAIR_PERSISTENT_TWO_WAV_PASS_MISSING",
    "VOLUNTARY_KIRA_OPT_IN_RECEIPT_AND_STOP_FLOW_NOT_YET_CONNECTED",
    "CURRENT_TWO_TURN_HARNESS_QUESTION_SET_DOES_NOT_MATCH_THIS_GATE",
    "CURRENT_TWO_TURN_REPORT_RETAINS_RAW_MODEL_REPLY_TEXT_AND_NEEDS_PRIVATE_CONTENT_REDACTION_FOR_THIS PERSON_LEVEL_GATE",
    "OWNER_PRESENT_SPEAKER_PLAYBACK_AND_FIRST_AUDIBLE_OBSERVATION_REQUIRED",
    "HEAVY_WORKLOAD_IDLE_STATE_MUST_BE_PROVEN_AT_EXECUTION_TIME",
}
REQUIRED_PERSISTENT_CHECKS = {
    "operator_bound_exact_candidate_config",
    "candidate_remained_inactive",
    "worker_started_unloaded",
    "load_identity_exact",
    "load_cuda_contract",
    "load_gpu_allocation",
    "load_model_and_core_components_cuda",
    "load_cuda_synchronization",
    "load_no_rejected_runtime_warning",
    "model_loaded_once",
    "reference_conditioned_once",
    "two_wavs_generated",
    "two_attempts_without_false_host_return_retries",
    "first_conditioning_reused",
    "second_conditioning_reused",
    "first_truthful_gpu_execution",
    "second_truthful_gpu_execution",
    "accepted_output_tensors_cuda_never_claimed",
    "first_wav_valid",
    "second_wav_valid",
    "exact_profile_reference_and_text_hashes",
    "explicit_unload",
    "torch_allocation_returned",
    "model_unloaded",
    "qwen_absent_before",
    "qwen_absent_after",
    "all_ollama_models_absent_before",
    "all_ollama_models_absent_after",
    "worker_exit_clean",
    "no_playback",
    "no_fallback",
}
HISTORICAL_IMPLEMENTED_SOURCE_BINDINGS = {
    "tools/run_kira_text_voice_two_turn_latency_acceptance.py": (
        "6f8cc199b12b3015fd61723b6f52e89d33c134be3115780ed721af9cbf4c5f32"
    ),
}


class PreparationError(RuntimeError):
    """The preparation or prerequisite failed closed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def project_path(raw: str, *, root: Path = ROOT) -> Path:
    target = (root / str(raw or "")).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise PreparationError(f"project path escaped root: {raw}") from exc
    return target


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PreparationError(f"{label} must be an object")
    return dict(value)


def _exact_sha(value: Any, label: str) -> str:
    normalized = str(value or "").casefold()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise PreparationError(f"{label} is not a SHA-256")
    return normalized


def validate_prepared_gate(path: Path = PREPARED_GATE, *, root: Path = ROOT) -> dict[str, Any]:
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise PreparationError("prepared gate escaped the project root") from exc
    payload = _object(json.loads(resolved.read_text(encoding="utf-8")), "prepared gate")
    exact = {
        "schema_version": 1,
        "artifact_kind": "kira_turing_psych_voice_timing_gate_preparation",
        "status": "PREPARED_BLOCKED_NOT_EXECUTED",
        "evidence_ceiling": "CONTRACT_ONLY",
        "live_execution_authorized_by_this_file": False,
    }
    for key, expected in exact.items():
        if payload.get(key) != expected:
            raise PreparationError(f"prepared gate mismatch: {key}")
    live = _object(payload.get("live_operations_performed"), "live operations")
    if not live or any(value is not False for value in live.values()):
        raise PreparationError("prepared gate claims or permits a live operation")

    bindings = payload.get("source_bindings")
    if not isinstance(bindings, list) or not bindings:
        raise PreparationError("source bindings are missing")
    seen: set[str] = set()
    superseded_bindings: list[dict[str, str]] = []
    for row in bindings:
        item = _object(row, "source binding")
        relative = str(item.get("path") or "")
        if relative in seen:
            raise PreparationError(f"duplicate source binding: {relative}")
        seen.add(relative)
        source = project_path(relative, root=root)
        recorded_sha256 = _exact_sha(item.get("sha256"), relative)
        if not source.is_file():
            raise PreparationError(f"source binding changed: {relative}")
        current_sha256 = sha256_file(source)
        if current_sha256 != recorded_sha256:
            if HISTORICAL_IMPLEMENTED_SOURCE_BINDINGS.get(relative) != recorded_sha256:
                raise PreparationError(f"source binding changed: {relative}")
            superseded_bindings.append(
                {
                    "path": relative,
                    "historical_sha256": recorded_sha256,
                    "current_sha256": current_sha256,
                    "reason": "prepared blocker was implemented append-only in a newer gate",
                }
            )

    launcher = _object(payload.get("launcher_and_model"), "launcher and model")
    if {"name": launcher.get("model_name"), "digest": launcher.get("model_digest")} != EXACT_MODEL:
        raise PreparationError("exact Llama model binding changed")
    if launcher.get("qwen_status") != "inactive_candidate_not_authorized_for_this_gate":
        raise PreparationError("Qwen was authorized by the preparation")
    if launcher.get("qwen_vision_enabled") is not False or launcher.get("llama_keep_alive_enabled") is not False:
        raise PreparationError("preparation enabled an unisolated model candidate")

    voice = _object(payload.get("approved_voice_identity"), "approved voice identity")
    for path_key, hash_key in (("profile_path", "profile_sha256"), ("reference_path", "reference_sha256")):
        identity_path = project_path(str(voice.get(path_key) or ""), root=root)
        if not identity_path.is_file() or sha256_file(identity_path) != _exact_sha(voice.get(hash_key), hash_key):
            raise PreparationError(f"approved voice binding changed: {path_key}")
    if (
        voice.get("only_automatic_approved_fallback") != "sealed_cpu"
        or voice.get("generic_voice_allowed") is not False
        or voice.get("sapi_allowed") is not False
        or voice.get("public_spoken_only") is not True
    ):
        raise PreparationError("approved voice route boundary changed")

    prerequisite = _object(payload.get("persistent_two_wav_prerequisite"), "persistent prerequisite")
    expected_paths = (
        ("harness", "harness_sha256"),
        ("candidate_config", "candidate_config_sha256"),
        ("worker", "worker_sha256"),
    )
    for path_key, hash_key in expected_paths:
        artifact = project_path(str(prerequisite.get(path_key) or ""), root=root)
        if not artifact.is_file() or sha256_file(artifact) != _exact_sha(prerequisite.get(hash_key), hash_key):
            raise PreparationError(f"persistent prerequisite binding changed: {path_key}")
    if (
        prerequisite.get("status") != "PENDING_NEW_POST_REPAIR_STANDALONE_PASS"
        or prerequisite.get("existing_attempts_qualify") is not False
        or prerequisite.get("required_wavs") != 2
        or prerequisite.get("playback_during_prerequisite") is not False
        or prerequisite.get("all_ollama_models_absent_required") is not True
    ):
        raise PreparationError("persistent prerequisite policy changed")

    voluntary = _object(payload.get("voluntary_non_private_scope"), "voluntary scope")
    required_false = (
        "private_disclosure_requested",
        "body_or_intimate_capability_test",
        "health_or_clinical_diagnosis_test",
        "danger_or_crisis_scenario_test",
        "sensory_or_media_claim_requested",
        "memory_promotion_allowed",
        "personhood_or_consciousness_verdict_allowed",
        "biological_humanity_claim_allowed",
    )
    if voluntary.get("invitation_required_before_measured_turns") is not True:
        raise PreparationError("Kira invitation is no longer required")
    if voluntary.get("owner_authorization_is_not_kira_opt_in") is not True:
        raise PreparationError("owner authorization was substituted for Kira opt-in")
    if any(voluntary.get(key) is not False for key in required_false):
        raise PreparationError("non-private question scope expanded")
    if payload.get("exact_measured_turns_after_clear_opt_in") != EXACT_TURNS:
        raise PreparationError("exact bounded Turing/psychology questions changed")
    if set(payload.get("blocking_conditions") or []) != REQUIRED_BLOCKERS:
        raise PreparationError("blocking conditions changed")
    return {
        "passed": not superseded_bindings,
        "historical_snapshot_valid": bool(superseded_bindings),
        "superseded_source_bindings": superseded_bindings,
        "status": payload["status"],
        "evidence_ceiling": payload["evidence_ceiling"],
        "prepared_gate_path": resolved.relative_to(root.resolve()).as_posix(),
        "prepared_gate_sha256": sha256_file(resolved),
        "measured_turn_count": len(EXACT_TURNS),
        "blockers": sorted(REQUIRED_BLOCKERS),
        "live_operation_started": False,
    }


def validate_persistent_report(
    path: Path,
    *,
    project_root: Path = ROOT,
    acceptance_root: Path = PERSISTENT_ACCEPTANCE_ROOT,
    expected_config_sha256: str | None = None,
    expected_harness_sha256: str | None = None,
    expected_worker_sha256: str | None = None,
    expected_profile_sha256: str | None = None,
    expected_reference_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate the complete new two-WAV prerequisite without invoking it."""

    resolved = Path(path).resolve()
    try:
        relative = resolved.relative_to(acceptance_root.resolve())
    except ValueError as exc:
        raise PreparationError("persistent report escaped its append-only evidence root") from exc
    if (
        resolved.name != PERSISTENT_REPORT_NAME
        or not re.fullmatch(r"attempt_[0-9]{2,3}", resolved.parent.name)
        or len(relative.parts) != 2
    ):
        raise PreparationError("persistent report is not one append-only attempt")
    report = _object(json.loads(resolved.read_text(encoding="utf-8")), "persistent report")

    expected_config = _exact_sha(
        expected_config_sha256 or sha256_file(CANDIDATE_CONFIG), "candidate config hash"
    )
    expected_harness = _exact_sha(
        expected_harness_sha256 or sha256_file(PERSISTENT_HARNESS), "acceptance harness hash"
    )
    expected_worker = _exact_sha(
        expected_worker_sha256 or sha256_file(PERSISTENT_WORKER), "persistent worker hash"
    )
    expected_profile = _exact_sha(
        expected_profile_sha256 or sha256_file(APPROVED_PROFILE), "approved profile hash"
    )
    expected_reference = _exact_sha(
        expected_reference_sha256 or sha256_file(APPROVED_REFERENCE), "approved reference hash"
    )
    if report.get("schema_version") != 1 or report.get("artifact_kind") != (
        "persistent_blackwell_voice_candidate_acceptance"
    ):
        raise PreparationError("persistent report identity changed")
    if (
        report.get("passed") is not True
        or report.get("engineering_pass") is not True
        or report.get("status") != "engineering_pass_pending_owner_heard_acceptance"
    ):
        raise PreparationError("persistent report did not pass")
    exact_report_values = {
        "candidate_status": "inactive_private_candidate_not_production",
        "production_routing_authorized": False,
        "promotion_performed": False,
        "playback_performed": False,
        "generic_voice_used": False,
        "sapi_voice_used": False,
        "fallback_used": False,
        "candidate_config_sha256": expected_config,
        "operator_expected_candidate_config_sha256": expected_config,
        "acceptance_harness_sha256": expected_harness,
        "approved_public_sentence": APPROVED_PUBLIC_SENTENCE,
        "approved_public_sentence_sha256": sha256_text(APPROVED_PUBLIC_SENTENCE),
        "protected_files_unchanged": True,
        "worker_exit_clean": True,
        "cache_deleted_automatically": False,
    }
    for key, expected in exact_report_values.items():
        if report.get(key) != expected:
            raise PreparationError(f"persistent report mismatch: {key}")
    sealed = _object(report.get("sealed_artifact_hashes"), "sealed artifacts")
    if (
        sealed.get("candidate_worker") != expected_worker
        or sealed.get("approved_profile") != expected_profile
        or sealed.get("approved_reference") != expected_reference
    ):
        raise PreparationError("persistent sealed identity binding changed")
    if report.get("protected_before") != report.get("protected_after"):
        raise PreparationError("protected file inventory changed")

    for label in ("qwen_before", "qwen_after"):
        row = _object(report.get(label), label)
        if row.get("query_succeeded") is not True or row.get("qwen_absent_proven") is not True:
            raise PreparationError(f"{label} did not prove Qwen absent")
    for label in ("ollama_before", "ollama_after"):
        row = _object(report.get(label), label)
        if (
            row.get("query_succeeded") is not True
            or row.get("all_models_absent_proven") is not True
            or row.get("resident_models") != []
        ):
            raise PreparationError(f"{label} did not prove all models absent")

    hello = _object(report.get("hello"), "worker hello")
    if (
        hello.get("config_sha256") != expected_config
        or hello.get("worker_sha256") != expected_worker
        or hello.get("model_loaded") is not False
        or hello.get("production_routing_authorized") is not False
    ):
        raise PreparationError("persistent worker did not start exact and unloaded")
    load = _object(report.get("load"), "model load")
    if load.get("ready") is not True or load.get("model_reused") is not False:
        raise PreparationError("persistent model load was not a fresh exact load")
    if load.get("identity") != {
        "profile_sha256": expected_profile,
        "reference_sha256": expected_reference,
    }:
        raise PreparationError("load did not bind exact approved voice identity")
    cuda = _object(load.get("runtime_cuda_checks"), "CUDA checks")
    if any(cuda.get(key) is not True for key in (
        "torch_runtime",
        "torchaudio_runtime",
        "cuda_runtime",
        "cuda_available",
        "device",
        "capability",
        "sm_120",
    )):
        raise PreparationError("persistent load CUDA contract failed")
    load_gpu = _object(load.get("gpu_proof"), "load GPU proof")
    if any(
        load_gpu.get(field) is not True
        for field in (
            "actual_gpu_allocation",
            "persistent_model_allocation_present",
            "model_and_core_components_cuda",
            "cuda_synchronize_before_model_load_succeeded",
            "cuda_synchronize_after_conditioning_succeeded",
            "no_rejected_runtime_warnings",
        )
    ):
        raise PreparationError("persistent load did not prove truthful CUDA residency/allocation")

    for key, expected_name in (
        ("first_synthesis", "kira_persistent_cold_first_request.wav"),
        ("second_synthesis", "kira_persistent_warm_second_request.wav"),
    ):
        synthesis = _object(report.get(key), key)
        expected_values = {
            "generated": True,
            "engine": "chatterbox_tts",
            "channel": "public_spoken_only",
            "text_sha256": sha256_text(APPROVED_PUBLIC_SENTENCE),
            "profile_sha256": expected_profile,
            "reference_sha256": expected_reference,
            "conditioning_reused": True,
            "generic_voice_used": False,
            "sapi_voice_used": False,
            "fallback_used": False,
            "playback": False,
            "device": "cuda",
        }
        for field, expected in expected_values.items():
            if synthesis.get(field) != expected:
                raise PreparationError(f"{key} mismatch: {field}")
        proof = _object(synthesis.get("gpu_proof"), f"{key} GPU proof")
        if any(
            proof.get(field) is not True
            for field in (
                "actual_gpu_execution",
                "model_and_core_components_cuda",
                "cuda_synchronize_before_generation_succeeded",
                "cuda_synchronize_after_generation_succeeded",
                "persistent_model_allocation_present",
                "generation_peak_exceeded_baseline",
                "no_rejected_runtime_warnings",
                "qwen_absence_proven_for_accepted_generation",
                "official_host_return_contract_satisfied",
                "accepted_output_tensors_host_cpu",
            )
        ) or proof.get("accepted_output_tensors_cuda") is not False:
            raise PreparationError(f"{key} did not prove truthful eager-CUDA execution")
        wav = _object(synthesis.get("wav_validation"), f"{key} WAV")
        wav_hash = _exact_sha(wav.get("sha256"), f"{key} WAV hash")
        if wav.get("passed") is not True:
            raise PreparationError(f"{key} WAV validation failed")
        relative_audio = str(synthesis.get("audio_relative") or "")
        audio = project_path(relative_audio, root=project_root)
        if audio.name != expected_name or audio.parent.resolve() != resolved.parent.resolve():
            raise PreparationError(f"{key} output escaped its exact attempt")
        if not audio.is_file() or sha256_file(audio) != wav_hash:
            raise PreparationError(f"{key} WAV file/hash changed")

    checks = _object(report.get("checks"), "persistent checks")
    if any(checks.get(key) is not True for key in REQUIRED_PERSISTENT_CHECKS):
        raise PreparationError("persistent report is missing a required passing check")
    return {
        "passed": True,
        "path": resolved.relative_to(project_root.resolve()).as_posix(),
        "sha256": sha256_file(resolved),
        "candidate_config_sha256": expected_config,
        "approved_profile_sha256": expected_profile,
        "approved_reference_sha256": expected_reference,
        "two_wavs_verified": True,
        "qwen_absent_before_and_after": True,
        "all_ollama_models_absent_before_and_after": True,
        "live_operation_started_by_validation": False,
    }


def describe() -> dict[str, Any]:
    return {
        "validator": "kira_turing_psych_voice_gate_preparation_v1",
        "default_inert": True,
        "prepared_gate": PREPARED_GATE.relative_to(ROOT).as_posix(),
        "exact_model": EXACT_MODEL,
        "measured_turns": EXACT_TURNS,
        "blockers": sorted(REQUIRED_BLOCKERS),
        "capabilities": ["validate prepared hashes", "validate completed persistent report"],
        "cannot": [
            "activate Kira",
            "invoke a model or GPU",
            "generate or play audio",
            "open a device, browser, or media source",
            "authorize the live gate",
        ],
        "live_operation_started": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-prepared", nargs="?", const=str(PREPARED_GATE), default="")
    parser.add_argument("--validate-persistent-report", default="")
    args = parser.parse_args(argv)
    try:
        if str(args.validate_prepared).strip():
            result = validate_prepared_gate(Path(args.validate_prepared))
        elif str(args.validate_persistent_report).strip():
            result = validate_persistent_report(Path(args.validate_persistent_report))
        else:
            result = describe()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "passed": False,
                    "reason": f"{type(exc).__name__}: {exc}",
                    "live_operation_started": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
