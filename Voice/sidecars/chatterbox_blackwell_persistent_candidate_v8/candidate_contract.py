#!/usr/bin/env python3
"""Exact-byte and authorization contract for the inactive v8 candidate.

This module is standard-library only.  Importing it performs no network,
model, GPU, audio, playback, or person-state operation.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path(__file__).with_name("candidate_config.json")
CANONICAL_CONFIG_SHA256 = "9b221b9eb4c6ada505c8e912ba5554b8831ee7484a69ac7289cbeb430f338587"
EXACT_CANDIDATE_ID = "kira_chatterbox_blackwell_cpu_park_candidate_v8"
EXACT_QWEN_MODEL = "qwen3.5:9b"
EXACT_QWEN_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
EXACT_PROFILE_SHA256 = "102d17f5420a1a16b3a920204ebde0d532c0a9bfd2979dca28048378ecddc116"
EXACT_REFERENCE_SHA256 = "2039a2abd600a63c294d69c2b2e4d450c64c850dc6d1c9a4fbfa1700ba92069c"
REQUIRED_V8_SEAL_FILES = (
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8/candidate_config.json",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8/README.md",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8/candidate_contract.py",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8/live_adapter.py",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8/persistent_worker.py",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8/playback_worker.py",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8/worker_entry.py",
    "Core/persistent_blackwell_voice_integration_v8.py",
    "Testing/blackwell_v8_static_fixture_backend.py",
    "Testing/test_blackwell_persistent_voice_candidate_v8_hostile_static.py",
)


class V8ContractError(RuntimeError):
    """Fail-closed v8 contract error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _reject_constant(token: str) -> None:
    raise V8ContractError(f"non-finite JSON constant is forbidden: {token}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if not isinstance(key, str) or key in result:
            raise V8ContractError("JSON object keys must be unique strings")
        result[key] = value
    return result


def _closed_finite(value: Any, depth: int = 0) -> None:
    if depth > 64:
        raise V8ContractError("JSON nesting exceeds 64 levels")
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise V8ContractError("JSON contains a non-finite number")
        return
    if isinstance(value, list):
        for item in value:
            _closed_finite(item, depth + 1)
        return
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise V8ContractError("JSON keys must be strings")
        for item in value.values():
            _closed_finite(item, depth + 1)
        return
    raise V8ContractError(f"unsupported JSON type: {type(value).__name__}")


def strict_json_loads(raw: bytes | str) -> Any:
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        value = json.loads(
            text,
            parse_constant=_reject_constant,
            object_pairs_hook=_unique_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise V8ContractError(f"malformed strict JSON: {exc}") from exc
    _closed_finite(value)
    return value


def canonical_json_sha256(value: Any) -> str:
    _closed_finite(value)
    try:
        payload = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise V8ContractError(f"value is not canonical JSON: {exc}") from exc
    return hashlib.sha256(payload).hexdigest()


def _validate_config(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise V8ContractError("v8 config must be an object")
    exact = {
        "schema_version": 5,
        "candidate_id": EXACT_CANDIDATE_ID,
        "production_routing_authorized": False,
        "live_execution_authorized_by_this_candidate": False,
        "live_adapter_available": True,
        "live_adapter_live_validated": False,
        "playback_implemented": True,
        "playback_live_validated": False,
        "playback_authorized_by_this_candidate": False,
        "current_production_route_changed": False,
        "ipc_protocol": "kira_blackwell_v7_jsonl_1",
        "required_windows_start_order": "create_suspended_assign_job_prove_then_resume",
        "required_windows_termination": "job_object_kill_on_close",
        "qwen_model": EXACT_QWEN_MODEL,
        "qwen_digest": EXACT_QWEN_DIGEST,
        "qwen_base_url": "http://127.0.0.1:11434",
        "approved_profile_sha256": EXACT_PROFILE_SHA256,
        "approved_reference_sha256": EXACT_REFERENCE_SHA256,
        "input_channel": "public_spoken_only",
        "cpu_synthesis_allowed": False,
        "generic_voice_allowed": False,
        "sapi_allowed": False,
        "llama_allowed": False,
        "substitute_reference_allowed": False,
        "automatic_fallback_inside_candidate": None,
    }
    for key, expected in exact.items():
        if config.get(key) != expected:
            raise V8ContractError(f"canonical v8 config mismatch: {key}")
    if config.get("qwen_allowed_endpoints") != [
        "/api/ps", "/api/tags", "/api/generate", "/api/chat"
    ]:
        raise V8ContractError("canonical Qwen endpoint set/order mismatch")
    live = config.get("voice_live_component")
    if not isinstance(live, dict) or live.get("class") != "PersistentVoiceRuntime":
        raise V8ContractError("exact persistent-v2 live component is absent")
    if live.get("device") != "cuda" or live.get("required_components") != ["t3", "s3gen", "ve"]:
        raise V8ContractError("live component CUDA/component contract drift")
    if (
        live.get("component_fingerprint")
        != "sha256_full_parameter_and_buffer_bytes_plus_stable_component_identity_v8"
        or live.get("tensor_identity_transfer")
        != "tensor_object_replacement_allowed_only_inside_exact_owned_cpu_cuda_transition_with_unchanged_full_bytes_schema_and_component_objects"
    ):
        raise V8ContractError("v8 stable component-transfer fingerprint contract drift")
    if config.get("state_engine_extension") != (
        "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8/persistent_worker.py"
    ):
        raise V8ContractError("v8 live state-engine extension is not exact")
    transfer = config.get("component_transfer_contract")
    if not isinstance(transfer, dict) or not all(
        transfer.get(key) is True
        for key in (
            "full_parameter_and_buffer_bytes_required",
            "parameter_and_buffer_names_shapes_dtypes_lengths_and_grad_flags_required",
            "tensor_object_identity_may_change_only_during_owned_device_transfer",
            "transfer_ledger_required",
            "model_generation_binds_stable_component_fingerprint",
            "before_and_after_synthesis_full_fingerprint_required",
        )
    ) or transfer.get("component_object_identity_may_change") is not False:
        raise V8ContractError("v8 component transfer contract is incomplete")
    playback = config.get("playback")
    if not isinstance(playback, dict):
        raise V8ContractError("playback contract is absent")
    if playback.get("owner_hearing_observations") != [
        "heard_complete", "heard_partial", "heard_nothing", "uncertain"
    ]:
        raise V8ContractError("owner-hearing observation set drift")
    if playback.get("automatic_owner_hearing_claim_allowed") is not False:
        raise V8ContractError("automatic owner-hearing claims are forbidden")
    if (
        playback.get("implementation")
        != "separate_killable_windows_child_winsound_sync_verified_memory_bytes_only"
        or playback.get("source_truth") != "verified_in_memory_wav_bytes"
        or playback.get("child_environment")
        != "restricted_windows_allowlist_plus_one_time_playback_capability_no_live_model_capabilities"
        or float(playback.get("maximum_owner_ack_delay_seconds", 0)) <= 0
    ):
        raise V8ContractError("playback byte/environment/owner-ack contract drift")
    for group in ("sealed_v2_production_components", "sealed_v7_accepted_boundary"):
        values = config.get(group)
        if not isinstance(values, dict) or not values:
            raise V8ContractError(f"{group} is absent")
        if any(not isinstance(path, str) or not is_sha256(digest) for path, digest in values.items()):
            raise V8ContractError(f"{group} contains an invalid exact-byte record")
    audit = config.get("fresh_audit_contract")
    if not isinstance(audit, dict) or audit.get("author_may_not_create_audit_authorization") is not True:
        raise V8ContractError("different-agent audit contract is absent")
    if audit.get("required_seal_manifest_path") != (
        "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8/STATIC_SEAL_MANIFEST.json"
    ):
        raise V8ContractError("required v8 seal manifest path drift")
    for key, value in config.get("operation_bounds_seconds", {}).items():
        if (
            not isinstance(key, str)
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) <= 0
        ):
            raise V8ContractError(f"operation bound is invalid: {key}")
    return config


def load_canonical_config() -> dict[str, Any]:
    observed = sha256_file(CONFIG_PATH)
    if CANONICAL_CONFIG_SHA256 == "CONFIG_SHA256_PENDING_SEAL":
        raise V8ContractError("v8 config is not sealed")
    if observed != CANONICAL_CONFIG_SHA256:
        raise V8ContractError("canonical v8 config hash drift")
    return _validate_config(strict_json_loads(CONFIG_PATH.read_bytes()))


def verify_preserved_bytes(config: dict[str, Any]) -> dict[str, str]:
    observed: dict[str, str] = {}
    for group in ("sealed_v2_production_components", "sealed_v7_accepted_boundary"):
        for relative, expected in config[group].items():
            path = PROJECT_ROOT / relative
            actual = sha256_file(path)
            observed[relative] = actual
            if actual != expected:
                raise V8ContractError(f"preserved exact byte drift: {relative}")
    return observed


def verify_seal_manifest(config: dict[str, Any], path: Path) -> dict[str, Any]:
    value = strict_json_loads(path.read_bytes())
    required = {
        "schema_version",
        "candidate_id",
        "status",
        "candidate_config_sha256",
        "live_execution_authorized",
        "playback_authorized",
        "files",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise V8ContractError("v8 seal manifest schema is not exact")
    files = value["files"]
    if (
        value["schema_version"] != 1
        or value["candidate_id"] != EXACT_CANDIDATE_ID
        or value["status"] != "static_only_pending_fresh_different_agent_audit"
        or value["candidate_config_sha256"] != CANONICAL_CONFIG_SHA256
        or value["live_execution_authorized"] is not False
        or value["playback_authorized"] is not False
        or not isinstance(files, dict)
        or set(files) != set(REQUIRED_V8_SEAL_FILES)
    ):
        raise V8ContractError("v8 seal manifest content/file set is not exact")
    project = PROJECT_ROOT.resolve(strict=True)
    for relative in REQUIRED_V8_SEAL_FILES:
        record = files[relative]
        if (
            not isinstance(record, dict)
            or set(record) != {"bytes", "sha256"}
            or isinstance(record["bytes"], bool)
            or not isinstance(record["bytes"], int)
            or record["bytes"] <= 0
            or not is_sha256(record["sha256"])
        ):
            raise V8ContractError(f"v8 seal record is invalid: {relative}")
        target = (PROJECT_ROOT / relative).resolve(strict=True)
        target.relative_to(project)
        if target.stat().st_size != record["bytes"] or sha256_file(target) != record["sha256"]:
            raise V8ContractError(f"v8 sealed file drift: {relative}")
    return dict(value)


def verify_fresh_audit_authorization(
    config: dict[str, Any], *, expected_audit_sha256: str
) -> dict[str, Any]:
    """Require a future, different-agent exact-byte audit record.

    The v8 author intentionally does not create this file.  Static acceptance
    and an explicit per-run environment capability are both still required.
    """

    if not is_sha256(expected_audit_sha256):
        raise V8ContractError("fresh audit expected SHA-256 is invalid")
    relative = config["fresh_audit_contract"]["required_relative_path"]
    path = PROJECT_ROOT / relative
    if not path.is_file() or sha256_file(path) != expected_audit_sha256:
        raise V8ContractError("fresh different-agent audit bytes are absent or drifted")
    value = strict_json_loads(path.read_bytes())
    required_keys = {
        "schema_version",
        "candidate_id",
        "candidate_config_sha256",
        "seal_manifest_path",
        "seal_manifest_sha256",
        "fresh_independent_audit",
        "auditor_relationship",
        "verdict",
        "static_only",
    }
    if not isinstance(value, dict) or set(value) != required_keys:
        raise V8ContractError("fresh audit authorization schema is not exact")
    if (
        value["schema_version"] != 1
        or value["candidate_id"] != EXACT_CANDIDATE_ID
        or value["candidate_config_sha256"] != CANONICAL_CONFIG_SHA256
        or value["fresh_independent_audit"] is not True
        or value["auditor_relationship"] != "different_agent_from_v8_author"
        or value["verdict"] != config["fresh_audit_contract"]["required_verdict"]
        or value["static_only"] is not True
        or not is_sha256(value["seal_manifest_sha256"])
    ):
        raise V8ContractError("fresh audit authorization content is not acceptable")
    if value["seal_manifest_path"] != config["fresh_audit_contract"]["required_seal_manifest_path"]:
        raise V8ContractError("fresh audit references the wrong v8 seal path")
    seal = PROJECT_ROOT / value["seal_manifest_path"]
    if not seal.is_file() or sha256_file(seal) != value["seal_manifest_sha256"]:
        raise V8ContractError("fresh audit references a missing/drifted v8 seal")
    verify_seal_manifest(config, seal)
    return dict(value)


def verify_per_run_live_capability(config: dict[str, Any]) -> None:
    name = config["engineering_run_opt_in"]
    expected = config["engineering_run_opt_in_value"]
    if os.environ.get(name) != expected:
        raise V8ContractError("bounded v8 engineering-run capability is absent")


__all__ = [
    "CANONICAL_CONFIG_SHA256",
    "CONFIG_PATH",
    "EXACT_CANDIDATE_ID",
    "EXACT_PROFILE_SHA256",
    "EXACT_QWEN_DIGEST",
    "EXACT_QWEN_MODEL",
    "EXACT_REFERENCE_SHA256",
    "PROJECT_ROOT",
    "V8ContractError",
    "canonical_json_sha256",
    "is_sha256",
    "load_canonical_config",
    "sha256_file",
    "strict_json_loads",
    "verify_fresh_audit_authorization",
    "verify_per_run_live_capability",
    "verify_preserved_bytes",
    "verify_seal_manifest",
]
