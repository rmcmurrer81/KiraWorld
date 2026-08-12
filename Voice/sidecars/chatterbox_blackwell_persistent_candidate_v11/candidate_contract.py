"""Strict inert contract for Blackwell typed-memory integration v11."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path(__file__).with_name("candidate_config.json")
EXACT_CANDIDATE_ID = "kira_chatterbox_blackwell_typed_memory_integration_candidate_v11"
CANONICAL_CONFIG_SHA256 = "925ebd235fa0f6ee6fb0fb53cbdafef9b9c19f8f2122e90c26b56613efcbf411"
REQUIRED_SEAL_FILES = (
    "Core/persistent_blackwell_voice_integration_v11.py",
    "Testing/test_blackwell_persistent_voice_candidate_v11_hostile_static.py",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v11/README.md",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v11/candidate_config.json",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v11/candidate_contract.py",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v11/worker_entry.py",
)


class V11ContractError(RuntimeError):
    """Fail-closed v11 configuration or authority error."""


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _strict_json(raw: bytes) -> Any:
    def reject_constant(token: str) -> None:
        raise V11ContractError(f"non-finite JSON constant is forbidden: {token}")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise V11ContractError("duplicate JSON key")
            result[key] = value
        return result

    try:
        return json.loads(
            raw.decode("utf-8"),
            parse_constant=reject_constant,
            object_pairs_hook=unique_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise V11ContractError(f"malformed strict JSON: {exc}") from exc


def _closed_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise V11ContractError(f"{label} schema is not exact")
    return value


def _hash_map(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise V11ContractError(f"{label} must be a nonempty object")
    root = PROJECT_ROOT.resolve(strict=True)
    result: dict[str, str] = {}
    for relative, digest in value.items():
        if not isinstance(relative, str) or not relative or not is_sha256(digest):
            raise V11ContractError(f"{label} entry is invalid")
        target = (PROJECT_ROOT / relative).resolve(strict=True)
        target.relative_to(root)
        result[relative] = digest
    return result


def _validate_config(value: Any) -> dict[str, Any]:
    keys = {
        "schema_version", "candidate_id", "candidate_status",
        "production_routing_authorized", "live_execution_authorized_by_this_candidate",
        "playback_authorized_by_this_candidate", "current_production_route_changed",
        "worker_integration_implemented", "worker_integration_live_validated",
        "future_live_attempt_authorized", "feature_flag", "engineering_run_opt_in",
        "engineering_run_opt_in_value", "worker_module", "worker_module_path",
        "integration_contract", "v10_static_audit_binding",
        "future_fresh_audit_contract", "preserved_boundaries", "static_test_contract",
    }
    config = _closed_object(value, keys, "v11 config")
    exact = {
        "schema_version": 1,
        "candidate_id": EXACT_CANDIDATE_ID,
        "candidate_status": "inactive_static_integration_pending_fresh_different_agent_audit",
        "production_routing_authorized": False,
        "live_execution_authorized_by_this_candidate": False,
        "playback_authorized_by_this_candidate": False,
        "current_production_route_changed": False,
        "worker_integration_implemented": True,
        "worker_integration_live_validated": False,
        "future_live_attempt_authorized": False,
        "feature_flag": "KIRA_ENABLE_BLACKWELL_TYPED_MEMORY_INTEGRATION_CANDIDATE_V11",
        "engineering_run_opt_in": "KIRA_AUTHORIZE_BLACKWELL_V11_BOUNDED_ENGINEERING_RUN",
        "engineering_run_opt_in_value": "exact_v11_typed_memory_integration_after_fresh_audit_and_future_harness_only",
        "worker_module": "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v11.worker_entry",
        "worker_module_path": "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v11/worker_entry.py",
    }
    for key, expected in exact.items():
        if type(config.get(key)) is not type(expected) or config.get(key) != expected:
            raise V11ContractError(f"v11 config mismatch: {key}")

    integration = _closed_object(
        config["integration_contract"],
        {
            "base_semantic_worker", "base_live_adapter", "process_topology",
            "parent_coordinator", "memory_repair",
            "static_fixture_delegates_without_live_adapter_import",
            "live_branch_verifies_v10_audit_before_adapter_import",
            "live_branch_installs_typed_probe_before_v8_worker_main",
            "exact_v8_adapter_bytes_required", "new_ready_schema_fields_added",
            "new_worker_response_schema_fields_added", "qwen_model_changed",
            "voice_model_changed", "production_route_changed",
        },
        "v11 integration contract",
    )
    required_true = (
        "static_fixture_delegates_without_live_adapter_import",
        "live_branch_verifies_v10_audit_before_adapter_import",
        "live_branch_installs_typed_probe_before_v8_worker_main",
        "exact_v8_adapter_bytes_required",
    )
    required_false = (
        "new_ready_schema_fields_added", "new_worker_response_schema_fields_added",
        "qwen_model_changed", "voice_model_changed", "production_route_changed",
    )
    if any(integration[key] is not True for key in required_true) or any(
        integration[key] is not False for key in required_false
    ):
        raise V11ContractError("v11 integration truth is not exact")

    v10 = _closed_object(
        config["v10_static_audit_binding"],
        {"path", "sha256", "verdict", "live_authorized"},
        "v10 audit binding",
    )
    if (
        not is_sha256(v10["sha256"])
        or v10["verdict"]
        != "ACCEPT_V10_STATIC_MEMORY_REPAIR_FOR_FUTURE_HARNESS_AUTHORING_ONLY"
        or v10["live_authorized"] is not False
    ):
        raise V11ContractError("v10 accepted static audit binding is invalid")

    future = _closed_object(
        config["future_fresh_audit_contract"],
        {
            "required_before_any_harness_authoring_or_live_attempt",
            "required_relative_path", "required_seal_manifest_path",
            "required_verdict", "required_auditor_relationship",
            "author_may_not_create_audit_authorization",
            "audit_does_not_authorize_live_execution",
        },
        "v11 future audit contract",
    )
    if (
        future["required_before_any_harness_authoring_or_live_attempt"] is not True
        or future["required_auditor_relationship"] != "different_agent_from_v11_author"
        or future["author_may_not_create_audit_authorization"] is not True
        or future["audit_does_not_authorize_live_execution"] is not True
    ):
        raise V11ContractError("v11 different-agent audit boundary is invalid")

    boundaries = _hash_map(config["preserved_boundaries"], "preserved boundaries")
    if len(boundaries) != 14:
        raise V11ContractError("v11 preserved boundary count drifted")
    static = _closed_object(
        config["static_test_contract"],
        {
            "may_start_static_fixture_worker",
            "may_import_v8_live_adapter_without_constructing_backend",
            "may_call_typed_current_process_memory_probe",
            "may_contact_ollama_or_qwen", "may_import_or_run_torch",
            "may_touch_cuda", "may_load_chatterbox", "may_synthesize_audio",
            "may_play_audio", "may_start_person_body_or_blender",
            "must_restore_any_test_only_module_patch", "must_keep_production_route_exact",
        },
        "v11 static test contract",
    )
    for key in (
        "may_contact_ollama_or_qwen", "may_import_or_run_torch", "may_touch_cuda",
        "may_load_chatterbox", "may_synthesize_audio", "may_play_audio",
        "may_start_person_body_or_blender",
    ):
        if static[key] is not False:
            raise V11ContractError(f"v11 static exclusion drifted: {key}")
    return config


def load_canonical_config() -> dict[str, Any]:
    if sha256_file(CONFIG_PATH) != CANONICAL_CONFIG_SHA256:
        raise V11ContractError("canonical v11 config hash drift")
    return _validate_config(_strict_json(CONFIG_PATH.read_bytes()))


def verify_preserved_bytes(config: Mapping[str, Any]) -> dict[str, str]:
    observed: dict[str, str] = {}
    for relative, expected in _hash_map(
        config.get("preserved_boundaries"), "preserved boundaries"
    ).items():
        actual = sha256_file(PROJECT_ROOT / relative)
        observed[relative] = actual
        if actual != expected:
            raise V11ContractError(f"preserved v11 dependency drift: {relative}")
    return observed


def verify_v10_static_audit(
    config: Mapping[str, Any], *, expected_audit_sha256: str | None = None
) -> dict[str, Any]:
    binding = config["v10_static_audit_binding"]
    expected = binding["sha256"] if expected_audit_sha256 is None else expected_audit_sha256
    if expected != binding["sha256"] or not is_sha256(expected):
        raise V11ContractError("v10 audit hash does not match the sealed binding")
    path = PROJECT_ROOT / binding["path"]
    if not path.is_file() or sha256_file(path) != expected:
        raise V11ContractError("accepted v10 static audit is absent or drifted")
    from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v10 import (
        candidate_contract as v10_contract,
    )

    v10_config = v10_contract.load_canonical_config()
    v10_contract.verify_preserved_bytes(v10_config)
    value = v10_contract.verify_fresh_audit_authorization(
        v10_config, expected_audit_sha256=expected
    )
    if value.get("verdict") != binding["verdict"] or value.get("live_authorized") is not False:
        raise V11ContractError("v10 audit grants the wrong authority")
    return dict(value)


def verify_seal_manifest(config: Mapping[str, Any], path: Path) -> dict[str, Any]:
    value = _strict_json(path.read_bytes())
    required = {
        "schema_version", "candidate_id", "status", "candidate_config_sha256",
        "live_execution_authorized", "playback_authorized", "files",
    }
    seal = _closed_object(value, required, "v11 seal")
    if (
        seal["schema_version"] != 1
        or seal["candidate_id"] != EXACT_CANDIDATE_ID
        or seal["status"] != "static_only_pending_fresh_different_agent_audit"
        or seal["candidate_config_sha256"] != CANONICAL_CONFIG_SHA256
        or seal["live_execution_authorized"] is not False
        or seal["playback_authorized"] is not False
        or not isinstance(seal["files"], dict)
        or set(seal["files"]) != set(REQUIRED_SEAL_FILES)
    ):
        raise V11ContractError("v11 seal content is not exact")
    for relative in REQUIRED_SEAL_FILES:
        record = _closed_object(seal["files"][relative], {"bytes", "sha256"}, relative)
        target = PROJECT_ROOT / relative
        if (
            type(record["bytes"]) is not int
            or record["bytes"] != target.stat().st_size
            or record["sha256"] != sha256_file(target)
        ):
            raise V11ContractError(f"v11 sealed file drift: {relative}")
    return dict(seal)


def verify_future_fresh_audit_authorization(
    config: Mapping[str, Any], *, expected_audit_sha256: str
) -> dict[str, Any]:
    if not is_sha256(expected_audit_sha256):
        raise V11ContractError("v11 future audit hash is invalid")
    audit = config["future_fresh_audit_contract"]
    path = PROJECT_ROOT / audit["required_relative_path"]
    if not path.is_file() or sha256_file(path) != expected_audit_sha256:
        raise V11ContractError("fresh different-agent v11 audit is absent or drifted")
    value = _strict_json(path.read_bytes())
    required = {
        "schema_version", "candidate_id", "candidate_config_sha256",
        "seal_manifest_path", "seal_manifest_sha256", "fresh_independent_audit",
        "auditor_relationship", "verdict", "static_only", "live_authorized",
    }
    authorization = _closed_object(value, required, "v11 audit")
    if (
        authorization["schema_version"] != 1
        or authorization["candidate_id"] != EXACT_CANDIDATE_ID
        or authorization["candidate_config_sha256"] != CANONICAL_CONFIG_SHA256
        or authorization["fresh_independent_audit"] is not True
        or authorization["auditor_relationship"] != audit["required_auditor_relationship"]
        or authorization["verdict"] != audit["required_verdict"]
        or authorization["static_only"] is not True
        or authorization["live_authorized"] is not False
    ):
        raise V11ContractError("v11 audit content is invalid")
    seal_path = PROJECT_ROOT / authorization["seal_manifest_path"]
    if (
        authorization["seal_manifest_path"] != audit["required_seal_manifest_path"]
        or not seal_path.is_file()
        or sha256_file(seal_path) != authorization["seal_manifest_sha256"]
    ):
        raise V11ContractError("v11 audit seal binding is absent or drifted")
    verify_seal_manifest(config, seal_path)
    return dict(authorization)


def verify_per_run_live_capability(config: Mapping[str, Any]) -> None:
    key = config["engineering_run_opt_in"]
    expected = config["engineering_run_opt_in_value"]
    if os.environ.get(key) != expected:
        raise V11ContractError("explicit outer per-run v11 capability is absent")


__all__ = [
    "CANONICAL_CONFIG_SHA256", "CONFIG_PATH", "EXACT_CANDIDATE_ID", "PROJECT_ROOT",
    "REQUIRED_SEAL_FILES", "V11ContractError", "is_sha256", "load_canonical_config",
    "sha256_file", "verify_future_fresh_audit_authorization",
    "verify_per_run_live_capability", "verify_preserved_bytes", "verify_seal_manifest",
    "verify_v10_static_audit",
]
