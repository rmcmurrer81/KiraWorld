"""Strict inert contract for Blackwell canonical integration V12."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path(__file__).with_name("candidate_config.json")
EXACT_CANDIDATE_ID = (
    "kira_chatterbox_blackwell_canonical_typed_memory_integration_candidate_v12"
)
CANONICAL_CONFIG_SHA256 = (
    "9a6e96f6bae827437b301e4f4e9a1cb468fa44491b080e80956d33e3f3a52c59"
)
REQUIRED_SEAL_FILES = (
    "Core/persistent_blackwell_voice_integration_v12.py",
    "Testing/test_blackwell_persistent_voice_candidate_v12_hostile_static.py",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v12/README.md",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v12/candidate_config.json",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v12/candidate_contract.py",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v12/canonical_typed_memory_binding.py",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v12/worker_entry.py",
)


class V12ContractError(RuntimeError):
    """Fail-closed V12 configuration or authority error."""


def is_sha256(value: Any) -> bool:
    return (
        type(value) is str
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
        raise V12ContractError(f"non-finite JSON constant forbidden: {token}")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise V12ContractError("duplicate JSON key")
            result[key] = value
        return result

    try:
        return json.loads(
            raw.decode("utf-8"),
            parse_constant=reject_constant,
            object_pairs_hook=unique_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise V12ContractError(f"malformed strict JSON: {exc}") from exc


def _closed(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise V12ContractError(f"{label} schema is not exact")
    if any(type(key) is not str for key in value):
        raise V12ContractError(f"{label} keys must be exact strings")
    return value


def _typed_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return set(actual) == set(expected) and all(
            _typed_equal(actual[key], expected[key]) for key in expected
        )
    if type(expected) is list:
        return len(actual) == len(expected) and all(
            _typed_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def _hash_map(value: Any, label: str) -> dict[str, str]:
    if type(value) is not dict or not value:
        raise V12ContractError(f"{label} must be a nonempty exact object")
    root = PROJECT_ROOT.resolve(strict=True)
    result: dict[str, str] = {}
    for relative, digest in value.items():
        if type(relative) is not str or not relative or not is_sha256(digest):
            raise V12ContractError(f"{label} entry is invalid")
        target = (PROJECT_ROOT / relative).resolve(strict=True)
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise V12ContractError(f"{label} path escaped project root") from exc
        result[relative] = digest
    return result


_EXPECTED_INTEGRATION = {
    "base_semantic_worker": "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.worker_entry",
    "process_topology": "Core/blackwell_v9_process_boundary.py",
    "parent_coordinator": "Core/persistent_blackwell_voice_integration_v12.py",
    "exact_adapter_source": "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8/live_adapter.py",
    "exact_memory_source": "Core/blackwell_v10_windows_memory.py",
    "normal_import_state_used_for_adapter_or_memory": False,
    "preexisting_sys_modules_or_package_binding_rejected": True,
    "private_module_objects_never_registered": True,
    "exact_executed_module_object_bound": True,
    "module_name_spec_origin_loader_bound": True,
    "original_callable_identity_bound": True,
    "callable_code_defaults_globals_builtins_closure_bound": True,
    "source_file_handle_identity_and_sha_bound": True,
    "revalidate_before_and_after_every_authority_use": True,
    "install_failure_exact_rollback_or_quarantine": True,
    "live_backend_constructed_by_candidate": False,
    "new_ready_schema_fields_added": False,
    "new_worker_response_schema_fields_added": False,
    "qwen_model_changed": False,
    "voice_model_changed": False,
    "production_route_changed": False,
}

_EXPECTED_STATIC = {
    "may_start_static_fixture_worker": True,
    "may_execute_inert_adapter_definitions_from_exact_bytes": True,
    "may_call_typed_current_process_memory_probe": True,
    "may_contact_ollama_or_qwen": False,
    "may_import_or_run_torch": False,
    "may_touch_cuda": False,
    "may_load_chatterbox": False,
    "may_synthesize_audio": False,
    "may_play_audio": False,
    "may_start_person_body_media_or_blender": False,
    "must_restore_all_hostile_mutations": True,
    "must_close_static_process_tree_and_handles": True,
    "must_keep_production_route_exact": True,
}


def _validate_config(value: Any) -> dict[str, Any]:
    config = _closed(
        value,
        {
            "schema_version", "candidate_id", "candidate_status",
            "production_routing_authorized", "live_execution_authorized_by_this_candidate",
            "playback_authorized_by_this_candidate", "current_production_route_changed",
            "worker_integration_implemented", "worker_integration_live_validated",
            "future_live_attempt_authorized", "feature_flag", "engineering_run_opt_in",
            "engineering_run_opt_in_value", "worker_module", "worker_module_path",
            "canonical_binding_module", "canonical_binding_path", "integration_contract",
            "v10_static_audit_binding", "v11_rejection_binding",
            "future_fresh_audit_contract", "preserved_boundaries", "static_test_contract",
        },
        "v12 config",
    )
    exact = {
        "schema_version": 1,
        "candidate_id": EXACT_CANDIDATE_ID,
        "candidate_status": "inactive_static_repair_pending_fresh_different_agent_audit",
        "production_routing_authorized": False,
        "live_execution_authorized_by_this_candidate": False,
        "playback_authorized_by_this_candidate": False,
        "current_production_route_changed": False,
        "worker_integration_implemented": True,
        "worker_integration_live_validated": False,
        "future_live_attempt_authorized": False,
        "feature_flag": "KIRA_ENABLE_BLACKWELL_CANONICAL_TYPED_MEMORY_CANDIDATE_V12",
        "engineering_run_opt_in": "KIRA_AUTHORIZE_BLACKWELL_V12_FUTURE_HARNESS_PREPARATION",
        "engineering_run_opt_in_value": "exact_v12_after_fresh_audit_and_new_one_shot_successor_capability_only",
        "worker_module": "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12.worker_entry",
        "worker_module_path": "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v12/worker_entry.py",
        "canonical_binding_module": "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12.canonical_typed_memory_binding",
        "canonical_binding_path": "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v12/canonical_typed_memory_binding.py",
    }
    for key, expected in exact.items():
        if not _typed_equal(config[key], expected):
            raise V12ContractError(f"v12 config mismatch: {key}")
    if not _typed_equal(config["integration_contract"], _EXPECTED_INTEGRATION):
        raise V12ContractError("v12 integration contract drifted")
    if not _typed_equal(config["static_test_contract"], _EXPECTED_STATIC):
        raise V12ContractError("v12 static contract drifted")

    v10 = _closed(
        config["v10_static_audit_binding"],
        {"path", "sha256", "verdict", "live_authorized"},
        "v10 static audit binding",
    )
    if not _typed_equal(
        v10,
        {
            "path": "RecoverySprint/continuation_20260810/blackwell_v10_windows_memory_fresh_static_audit/attempt_01/AUDIT_AUTHORIZATION.json",
            "sha256": "7bbd3ea93fe5949f9f1c6bcaf55ac12205d6fbc9aa74d98e4a0cab406c90e535",
            "verdict": "ACCEPT_V10_STATIC_MEMORY_REPAIR_FOR_FUTURE_HARNESS_AUTHORING_ONLY",
            "live_authorized": False,
        },
    ):
        raise V12ContractError("v10 static audit binding drifted")

    v11 = _closed(
        config["v11_rejection_binding"],
        {"path", "sha256", "verdict", "live_authorized", "blocking_finding_id"},
        "v11 rejection binding",
    )
    if not _typed_equal(
        v11,
        {
            "path": "RecoverySprint/continuation_20260811/blackwell_v11_typed_memory_integration_fresh_static_audit/attempt_01/AUDIT_DECISION.json",
            "sha256": "9ab9a2ec9132e125ef5dead739f8108d8544f449f903e59658610c766ad0c90f",
            "verdict": "REJECT_V11_STATIC_INTEGRATION_CANDIDATE",
            "live_authorized": False,
            "blocking_finding_id": "BLOCK_V11_EXACT_ADAPTER_MODULE_OBJECT_NOT_BOUND",
        },
    ):
        raise V12ContractError("v11 rejection binding drifted")

    future = _closed(
        config["future_fresh_audit_contract"],
        {
            "required_before_any_future_harness_authoring", "required_relative_path",
            "required_seal_manifest_path", "required_verdict",
            "required_auditor_relationship", "author_may_not_create_audit_authorization",
            "audit_does_not_authorize_live_execution",
        },
        "v12 future audit contract",
    )
    if not _typed_equal(
        future,
        {
            "required_before_any_future_harness_authoring": True,
            "required_relative_path": "RecoverySprint/continuation_20260811/blackwell_v12_canonical_typed_memory_integration_fresh_static_audit/attempt_01/AUDIT_AUTHORIZATION.json",
            "required_seal_manifest_path": "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v12/STATIC_SEAL_MANIFEST.json",
            "required_verdict": "ACCEPT_V12_STATIC_CANONICAL_INTEGRATION_FOR_FUTURE_HARNESS_AUTHORING_ONLY",
            "required_auditor_relationship": "different_agent_from_v12_author",
            "author_may_not_create_audit_authorization": True,
            "audit_does_not_authorize_live_execution": True,
        },
    ):
        raise V12ContractError("v12 future audit contract drifted")

    boundaries = _hash_map(config["preserved_boundaries"], "preserved boundaries")
    if len(boundaries) != 28:
        raise V12ContractError("v12 preserved boundary count drifted")
    return config


def load_canonical_config() -> dict[str, Any]:
    if sha256_file(CONFIG_PATH) != CANONICAL_CONFIG_SHA256:
        raise V12ContractError("canonical v12 config hash drift")
    return _validate_config(_strict_json(CONFIG_PATH.read_bytes()))


def verify_preserved_bytes(config: Mapping[str, Any]) -> dict[str, str]:
    observed: dict[str, str] = {}
    for relative, expected in _hash_map(
        config.get("preserved_boundaries"), "preserved boundaries"
    ).items():
        actual = sha256_file(PROJECT_ROOT / relative)
        observed[relative] = actual
        if actual != expected:
            raise V12ContractError(f"preserved V12 dependency drift: {relative}")
    return observed


def verify_v10_static_audit(config: Mapping[str, Any]) -> dict[str, Any]:
    binding = config["v10_static_audit_binding"]
    path = PROJECT_ROOT / binding["path"]
    if not path.is_file() or sha256_file(path) != binding["sha256"]:
        raise V12ContractError("accepted v10 audit is absent or drifted")
    from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v10 import (
        candidate_contract as v10_contract,
    )

    v10_config = v10_contract.load_canonical_config()
    v10_contract.verify_preserved_bytes(v10_config)
    value = v10_contract.verify_fresh_audit_authorization(
        v10_config, expected_audit_sha256=binding["sha256"]
    )
    if (
        value.get("verdict") != binding["verdict"]
        or value.get("static_only") is not True
        or value.get("live_authorized") is not False
    ):
        raise V12ContractError("v10 audit grants wrong authority")
    return dict(value)


def verify_v11_rejection(config: Mapping[str, Any]) -> dict[str, Any]:
    binding = config["v11_rejection_binding"]
    path = PROJECT_ROOT / binding["path"]
    if not path.is_file() or sha256_file(path) != binding["sha256"]:
        raise V12ContractError("v11 rejection evidence is absent or drifted")
    value = _strict_json(path.read_bytes())
    decision = _closed(
        value,
        {
            "schema_version", "candidate_id", "attempt_id", "completed_at_utc",
            "decision", "verdict", "static_only", "live_authorized",
            "future_harness_authoring_authorized", "promotion_authorized",
            "audit_authorization_created",
            "different_fresh_reaudit_required_after_append_only_repair",
            "sealed_subjects_exact_byte_match", "preserved_dependencies_exact_byte_match",
            "authored_v11_tests_passed", "authored_v10_tests_passed",
            "independent_hostile_tests_run", "independent_hostile_tests_passed",
            "independent_hostile_tests_failed", "blocking_finding_count",
            "blocking_finding_ids", "audit_result", "hostile_probe_result", "reason",
            "required_next_step", "scope_truth",
        },
        "v11 rejection decision",
    )
    if (
        decision["decision"] != "REJECT"
        or decision["verdict"] != binding["verdict"]
        or decision["static_only"] is not True
        or decision["live_authorized"] is not False
        or decision["future_harness_authoring_authorized"] is not False
        or decision["promotion_authorized"] is not False
        or decision["audit_authorization_created"] is not False
        or decision["blocking_finding_ids"] != [binding["blocking_finding_id"]]
    ):
        raise V12ContractError("v11 rejection truth is invalid")
    return dict(decision)


def verify_seal_manifest(config: Mapping[str, Any], path: Path) -> dict[str, Any]:
    seal = _closed(
        _strict_json(path.read_bytes()),
        {
            "schema_version", "candidate_id", "status", "candidate_config_sha256",
            "live_execution_authorized", "playback_authorized", "files",
        },
        "v12 seal",
    )
    if (
        seal["schema_version"] != 1
        or seal["candidate_id"] != EXACT_CANDIDATE_ID
        or seal["status"] != "static_only_pending_fresh_different_agent_audit"
        or seal["candidate_config_sha256"] != CANONICAL_CONFIG_SHA256
        or seal["live_execution_authorized"] is not False
        or seal["playback_authorized"] is not False
        or type(seal["files"]) is not dict
        or set(seal["files"]) != set(REQUIRED_SEAL_FILES)
    ):
        raise V12ContractError("v12 seal content is not exact")
    for relative in REQUIRED_SEAL_FILES:
        record = _closed(seal["files"][relative], {"bytes", "sha256"}, relative)
        target = PROJECT_ROOT / relative
        if (
            type(record["bytes"]) is not int
            or record["bytes"] != target.stat().st_size
            or not is_sha256(record["sha256"])
            or record["sha256"] != sha256_file(target)
        ):
            raise V12ContractError(f"v12 sealed file drift: {relative}")
    return dict(seal)


def verify_future_fresh_audit_authorization(
    config: Mapping[str, Any], *, expected_audit_sha256: str
) -> dict[str, Any]:
    if not is_sha256(expected_audit_sha256):
        raise V12ContractError("v12 future audit hash is invalid")
    audit = config["future_fresh_audit_contract"]
    path = PROJECT_ROOT / audit["required_relative_path"]
    if not path.is_file() or sha256_file(path) != expected_audit_sha256:
        raise V12ContractError("fresh different-agent v12 audit is absent or drifted")
    authorization = _closed(
        _strict_json(path.read_bytes()),
        {
            "schema_version", "candidate_id", "candidate_config_sha256",
            "seal_manifest_path", "seal_manifest_sha256", "fresh_independent_audit",
            "auditor_relationship", "verdict", "static_only", "live_authorized",
        },
        "v12 audit authorization",
    )
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
        raise V12ContractError("v12 audit content is invalid")
    seal_path = PROJECT_ROOT / authorization["seal_manifest_path"]
    if (
        authorization["seal_manifest_path"] != audit["required_seal_manifest_path"]
        or not seal_path.is_file()
        or sha256_file(seal_path) != authorization["seal_manifest_sha256"]
    ):
        raise V12ContractError("v12 audit seal binding is absent or drifted")
    verify_seal_manifest(config, seal_path)
    return dict(authorization)


def verify_outer_preparation_opt_in(config: Mapping[str, Any]) -> None:
    if os.environ.get(config["engineering_run_opt_in"]) != config[
        "engineering_run_opt_in_value"
    ]:
        raise V12ContractError("outer v12 preparation opt-in is absent")


__all__ = [
    "CANONICAL_CONFIG_SHA256", "CONFIG_PATH", "EXACT_CANDIDATE_ID", "PROJECT_ROOT",
    "REQUIRED_SEAL_FILES", "V12ContractError", "is_sha256", "load_canonical_config",
    "sha256_file", "verify_future_fresh_audit_authorization",
    "verify_outer_preparation_opt_in", "verify_preserved_bytes", "verify_seal_manifest",
    "verify_v10_static_audit", "verify_v11_rejection",
]
