"""Strict, inert contract for the append-only Blackwell v9 static repair."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from Core.blackwell_v9_process_boundary import stable_executable_identity
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8 import (
    candidate_contract as v8_contract,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path(__file__).with_name("candidate_config.json")
EXACT_CANDIDATE_ID = "kira_chatterbox_blackwell_venv_descendant_identity_candidate_v9"
CANONICAL_CONFIG_SHA256 = "a45f05bd46dc86d2dfb35d02709ae2264211f892f4830afd90aa177032b65915"
REQUIRED_SEAL_FILES = (
    "Core/blackwell_v9_process_boundary.py",
    "Core/persistent_blackwell_voice_integration_v9.py",
    "Testing/blackwell_v9_grandchild_redirector.py",
    "Testing/test_blackwell_persistent_voice_candidate_v9_hostile_static.py",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v9/README.md",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v9/candidate_config.json",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v9/candidate_contract.py",
)


class V9ContractError(RuntimeError):
    pass


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def sha256_file(path: Path) -> str:
    return v8_contract.sha256_file(path)


def strict_json_loads(raw: bytes | str) -> Any:
    return v8_contract.strict_json_loads(raw)


def _validate_hash_map(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise V9ContractError(f"{label} must be a nonempty object")
    project = PROJECT_ROOT.resolve(strict=True)
    result: dict[str, str] = {}
    for relative, digest in value.items():
        if not isinstance(relative, str) or not relative or not is_sha256(digest):
            raise V9ContractError(f"{label} entry is invalid")
        target = (PROJECT_ROOT / relative).resolve(strict=True)
        target.relative_to(project)
        result[relative] = digest
    return result


def _validate_identity(value: Any, label: str) -> dict[str, Any]:
    required = {
        "executable_path",
        "executable_sha256",
        "executable_size",
        "executable_volume_serial",
        "executable_file_index",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise V9ContractError(f"{label} identity schema is not exact")
    if not is_sha256(value["executable_sha256"]):
        raise V9ContractError(f"{label} SHA-256 is invalid")
    if not isinstance(value["executable_path"], str) or not Path(value["executable_path"]).is_absolute():
        raise V9ContractError(f"{label} path must be absolute")
    for key in ("executable_size", "executable_volume_serial", "executable_file_index"):
        if isinstance(value[key], bool) or not isinstance(value[key], int) or value[key] <= 0:
            raise V9ContractError(f"{label} {key} is invalid")
    return dict(value)


def _validate_config(value: Any) -> dict[str, Any]:
    required = {
        "schema_version",
        "candidate_id",
        "candidate_status",
        "production_routing_authorized",
        "live_execution_authorized_by_this_candidate",
        "playback_authorized_by_this_candidate",
        "current_production_route_changed",
        "feature_flag",
        "engineering_run_opt_in",
        "engineering_run_opt_in_value",
        "live_attempt_number_allowed_after_fresh_audit",
        "worker_protocol",
        "worker_module",
        "worker_module_path",
        "worker_module_sha256",
        "process_boundary",
        "process_topology",
        "fresh_audit_contract",
        "v8_worker_audit_binding",
        "preserved_v8_boundary",
        "preserved_attempt_and_audit_bytes",
        "static_test_contract",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise V9ContractError("v9 config schema is not exact")
    if (
        value["schema_version"] != 1
        or value["candidate_id"] != EXACT_CANDIDATE_ID
        or value["candidate_status"]
        != "inactive_static_repair_pending_fresh_different_agent_audit"
        or value["production_routing_authorized"] is not False
        or value["live_execution_authorized_by_this_candidate"] is not False
        or value["playback_authorized_by_this_candidate"] is not False
        or value["current_production_route_changed"] is not False
        or value["live_attempt_number_allowed_after_fresh_audit"] != 2
        or value["worker_protocol"] != "kira_blackwell_v7_jsonl_1"
        or value["process_boundary"] != "Core/blackwell_v9_process_boundary.py"
        or not is_sha256(value["worker_module_sha256"])
    ):
        raise V9ContractError("v9 config truth flags are invalid")
    topology = value["process_topology"]
    topology_keys = {
        "platform", "root_role", "worker_role", "direct_child_only",
        "arbitrary_descendant_allowed", "same_retained_job_required",
        "root_and_child_os_creation_tokens_required",
        "root_and_child_handles_retained_until_cleanup", "launcher", "worker",
    }
    if (
        not isinstance(topology, dict)
        or set(topology) != topology_keys
        or topology["platform"] != "windows"
        or topology["direct_child_only"] is not True
        or topology["arbitrary_descendant_allowed"] is not False
        or topology["same_retained_job_required"] is not True
        or topology["root_and_child_os_creation_tokens_required"] is not True
        or topology["root_and_child_handles_retained_until_cleanup"] is not True
    ):
        raise V9ContractError("v9 process topology is invalid")
    _validate_identity(topology["launcher"], "launcher")
    _validate_identity(topology["worker"], "worker")
    audit = value["fresh_audit_contract"]
    audit_keys = {
        "required_before_any_live_attempt_02", "required_relative_path",
        "required_seal_manifest_path", "required_verdict",
        "required_auditor_relationship", "author_may_not_create_audit_authorization",
    }
    if (
        not isinstance(audit, dict)
        or set(audit) != audit_keys
        or audit["required_before_any_live_attempt_02"] is not True
        or audit["required_auditor_relationship"] != "different_agent_from_v9_author"
        or audit["author_may_not_create_audit_authorization"] is not True
    ):
        raise V9ContractError("v9 fresh audit contract is invalid")
    v8_audit = value["v8_worker_audit_binding"]
    if (
        not isinstance(v8_audit, dict)
        or set(v8_audit) != {"path", "sha256"}
        or not is_sha256(v8_audit["sha256"])
    ):
        raise V9ContractError("v8 audit binding is invalid")
    _validate_hash_map(value["preserved_v8_boundary"], "preserved v8 boundary")
    _validate_hash_map(
        value["preserved_attempt_and_audit_bytes"], "preserved attempt/audit bytes"
    )
    static = value["static_test_contract"]
    expected_static = {
        "uses_exact_venvlauncher_and_base_python_topology": True,
        "imports_torch": False,
        "imports_cuda": False,
        "imports_chatterbox": False,
        "starts_ollama_or_qwen": False,
        "synthesizes_audio": False,
        "plays_audio": False,
        "starts_person_or_blender": False,
        "hostile_direct_parent_rejection_required": True,
        "hostile_launcher_identity_rejection_required": True,
        "hostile_worker_identity_rejection_required": True,
        "root_and_child_cleanup_truth_required": True,
    }
    if static != expected_static:
        raise V9ContractError("v9 static-test contract is invalid")
    return dict(value)


def load_canonical_config() -> dict[str, Any]:
    observed = sha256_file(CONFIG_PATH)
    if CANONICAL_CONFIG_SHA256 == "CONFIG_SHA256_PENDING_SEAL":
        raise V9ContractError("v9 config is not sealed")
    if observed != CANONICAL_CONFIG_SHA256:
        raise V9ContractError("canonical v9 config hash drift")
    return _validate_config(strict_json_loads(CONFIG_PATH.read_bytes()))


def verify_topology_executables(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    topology = config["process_topology"]
    observed: dict[str, dict[str, Any]] = {}
    for role in ("launcher", "worker"):
        expected = _validate_identity(topology[role], role)
        actual = stable_executable_identity(Path(expected["executable_path"]))
        left = {**actual, "executable_path": os.path.normcase(actual["executable_path"])}
        right = {**expected, "executable_path": os.path.normcase(str(Path(expected["executable_path"]).resolve(strict=True)))}
        if left != right:
            raise V9ContractError(f"{role} executable identity drift")
        observed[role] = actual
    return observed


def verify_preserved_bytes(config: Mapping[str, Any]) -> dict[str, str]:
    observed: dict[str, str] = {}
    v8_config = v8_contract.load_canonical_config()
    observed.update(v8_contract.verify_preserved_bytes(v8_config))
    for group in ("preserved_v8_boundary", "preserved_attempt_and_audit_bytes"):
        for relative, expected in _validate_hash_map(config[group], group).items():
            actual = sha256_file(PROJECT_ROOT / relative)
            if actual != expected:
                raise V9ContractError(f"preserved exact-byte drift: {relative}")
            observed[relative] = actual
    seal_path = PROJECT_ROOT / v8_config["fresh_audit_contract"]["required_seal_manifest_path"]
    v8_contract.verify_seal_manifest(v8_config, seal_path)
    return observed


def verify_seal_manifest(config: Mapping[str, Any], path: Path) -> dict[str, Any]:
    value = strict_json_loads(path.read_bytes())
    required = {
        "schema_version", "candidate_id", "status", "candidate_config_sha256",
        "live_execution_authorized", "playback_authorized", "files",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise V9ContractError("v9 seal manifest schema is not exact")
    if (
        value["schema_version"] != 1
        or value["candidate_id"] != EXACT_CANDIDATE_ID
        or value["status"] != "static_only_pending_fresh_different_agent_audit"
        or value["candidate_config_sha256"] != CANONICAL_CONFIG_SHA256
        or value["live_execution_authorized"] is not False
        or value["playback_authorized"] is not False
        or not isinstance(value["files"], dict)
        or set(value["files"]) != set(REQUIRED_SEAL_FILES)
    ):
        raise V9ContractError("v9 seal manifest content is invalid")
    for relative in REQUIRED_SEAL_FILES:
        record = value["files"][relative]
        target = PROJECT_ROOT / relative
        if (
            not isinstance(record, dict)
            or set(record) != {"bytes", "sha256"}
            or isinstance(record["bytes"], bool)
            or not isinstance(record["bytes"], int)
            or record["bytes"] <= 0
            or not is_sha256(record["sha256"])
            or target.stat().st_size != record["bytes"]
            or sha256_file(target) != record["sha256"]
        ):
            raise V9ContractError(f"v9 sealed file drift: {relative}")
    return dict(value)


def verify_fresh_audit_authorization(
    config: Mapping[str, Any], *, expected_audit_sha256: str
) -> dict[str, Any]:
    if not is_sha256(expected_audit_sha256):
        raise V9ContractError("fresh v9 audit expected SHA-256 is invalid")
    audit_contract = config["fresh_audit_contract"]
    path = PROJECT_ROOT / audit_contract["required_relative_path"]
    if not path.is_file() or sha256_file(path) != expected_audit_sha256:
        raise V9ContractError("fresh different-agent v9 audit is absent or drifted")
    value = strict_json_loads(path.read_bytes())
    required = {
        "schema_version", "candidate_id", "candidate_config_sha256",
        "seal_manifest_path", "seal_manifest_sha256", "fresh_independent_audit",
        "auditor_relationship", "verdict", "static_only",
        "one_bounded_live_attempt_number",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise V9ContractError("fresh v9 audit schema is not exact")
    if (
        value["schema_version"] != 1
        or value["candidate_id"] != EXACT_CANDIDATE_ID
        or value["candidate_config_sha256"] != CANONICAL_CONFIG_SHA256
        or value["fresh_independent_audit"] is not True
        or value["auditor_relationship"] != "different_agent_from_v9_author"
        or value["verdict"] != audit_contract["required_verdict"]
        or value["static_only"] is not True
        or value["one_bounded_live_attempt_number"] != 2
        or value["seal_manifest_path"] != audit_contract["required_seal_manifest_path"]
        or not is_sha256(value["seal_manifest_sha256"])
    ):
        raise V9ContractError("fresh v9 audit content is not acceptable")
    seal = PROJECT_ROOT / value["seal_manifest_path"]
    if not seal.is_file() or sha256_file(seal) != value["seal_manifest_sha256"]:
        raise V9ContractError("fresh v9 audit references a missing/drifted seal")
    verify_seal_manifest(config, seal)
    return dict(value)


def verify_per_run_live_capability(config: Mapping[str, Any]) -> None:
    if os.environ.get(config["engineering_run_opt_in"]) != config["engineering_run_opt_in_value"]:
        raise V9ContractError("explicit outer per-run v9 capability is absent")


__all__ = [
    "CANONICAL_CONFIG_SHA256",
    "CONFIG_PATH",
    "EXACT_CANDIDATE_ID",
    "PROJECT_ROOT",
    "REQUIRED_SEAL_FILES",
    "V9ContractError",
    "is_sha256",
    "load_canonical_config",
    "sha256_file",
    "strict_json_loads",
    "verify_fresh_audit_authorization",
    "verify_per_run_live_capability",
    "verify_preserved_bytes",
    "verify_seal_manifest",
    "verify_topology_executables",
]
