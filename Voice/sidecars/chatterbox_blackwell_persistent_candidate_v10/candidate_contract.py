"""Strict inert contract for the append-only Blackwell v10 static repair."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path(__file__).with_name("candidate_config.json")
EXACT_CANDIDATE_ID = "kira_chatterbox_blackwell_typed_memory_candidate_v10"
CANONICAL_CONFIG_SHA256 = "60a1ed5f156d1b4cb9868a5779210130a77894ffe69f83db781d091dff3f9748"
REQUIRED_SEAL_FILES = (
    "Core/blackwell_v10_windows_memory.py",
    "Testing/test_blackwell_persistent_voice_candidate_v10_hostile_static.py",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v10/README.md",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v10/candidate_config.json",
    "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v10/candidate_contract.py",
)


class V10ContractError(RuntimeError):
    pass


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
        raise V10ContractError(f"non-finite JSON constant is forbidden: {token}")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise V10ContractError("duplicate JSON key")
            result[key] = value
        return result

    try:
        return json.loads(
            raw.decode("utf-8"),
            parse_constant=reject_constant,
            object_pairs_hook=unique_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise V10ContractError(f"malformed strict JSON: {exc}") from exc


def _hash_map(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise V10ContractError(f"{label} must be nonempty")
    result: dict[str, str] = {}
    project = PROJECT_ROOT.resolve(strict=True)
    for relative, digest in value.items():
        if not isinstance(relative, str) or not is_sha256(digest):
            raise V10ContractError(f"{label} entry is invalid")
        target = (PROJECT_ROOT / relative).resolve(strict=True)
        target.relative_to(project)
        result[relative] = digest
    return result


def _validate_config(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise V10ContractError("v10 config must be an object")
    exact = {
        "schema_version": 1,
        "candidate_id": EXACT_CANDIDATE_ID,
        "candidate_status": "inactive_static_repair_pending_fresh_different_agent_audit",
        "production_routing_authorized": False,
        "live_execution_authorized_by_this_candidate": False,
        "playback_authorized_by_this_candidate": False,
        "current_production_route_changed": False,
        "worker_integration_implemented": False,
        "future_live_attempt_authorized": False,
    }
    for key, expected in exact.items():
        if value.get(key) != expected:
            raise V10ContractError(f"v10 config mismatch: {key}")
    repair = value.get("repair_scope")
    if (
        not isinstance(repair, dict)
        or repair.get("observed_winerror") != 6
        or repair.get("failed_api") != "GetProcessMemoryInfo"
        or repair.get("uses_open_process") is not False
        or repair.get("changes_access_rights") is not False
    ):
        raise V10ContractError("v10 repair scope is not exact")
    win32 = value.get("win32_contract")
    if (
        not isinstance(win32, dict)
        or win32.get("GetCurrentProcess_restype") != "wintypes.HANDLE"
        or win32.get("GetProcessMemoryInfo_restype") != "wintypes.BOOL"
        or win32.get("current_process_pseudohandle_only") is not True
    ):
        raise V10ContractError("v10 pointer-width Win32 contract is absent")
    audit = value.get("fresh_audit_contract")
    if (
        not isinstance(audit, dict)
        or audit.get("author_may_not_create_audit_authorization") is not True
        or audit.get("audit_does_not_authorize_live_execution") is not True
        or audit.get("required_auditor_relationship") != "different_agent_from_v10_author"
    ):
        raise V10ContractError("v10 different-agent audit contract is absent")
    _hash_map(value.get("preserved_attempt_02_evidence"), "attempt evidence")
    _hash_map(value.get("preserved_failure_boundary"), "failure boundary")
    static = value.get("static_test_contract")
    if not isinstance(static, dict) or any(
        static.get(key) is not False
        for key in (
            "may_import_torch",
            "may_touch_cuda",
            "may_contact_ollama_or_qwen",
            "may_load_chatterbox",
            "may_synthesize_audio",
            "may_play_audio",
            "may_start_person_body_or_blender",
        )
    ):
        raise V10ContractError("v10 static-only exclusions are incomplete")
    return value


def load_canonical_config() -> dict[str, Any]:
    if CANONICAL_CONFIG_SHA256 == "CONFIG_SHA256_PENDING_SEAL":
        raise V10ContractError("v10 config is not sealed")
    if sha256_file(CONFIG_PATH) != CANONICAL_CONFIG_SHA256:
        raise V10ContractError("canonical v10 config hash drift")
    return _validate_config(_strict_json(CONFIG_PATH.read_bytes()))


def verify_preserved_bytes(config: Mapping[str, Any]) -> dict[str, str]:
    observed: dict[str, str] = {}
    for group in ("preserved_attempt_02_evidence", "preserved_failure_boundary"):
        for relative, expected in _hash_map(config.get(group), group).items():
            actual = sha256_file(PROJECT_ROOT / relative)
            observed[relative] = actual
            if actual != expected:
                raise V10ContractError(f"preserved v10 dependency drift: {relative}")
    return observed


def verify_seal_manifest(config: Mapping[str, Any], path: Path) -> dict[str, Any]:
    value = _strict_json(path.read_bytes())
    required = {
        "schema_version", "candidate_id", "status", "candidate_config_sha256",
        "live_execution_authorized", "playback_authorized", "files",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise V10ContractError("v10 seal schema is not exact")
    files = value["files"]
    if (
        value["schema_version"] != 1
        or value["candidate_id"] != EXACT_CANDIDATE_ID
        or value["status"] != "static_only_pending_fresh_different_agent_audit"
        or value["candidate_config_sha256"] != CANONICAL_CONFIG_SHA256
        or value["live_execution_authorized"] is not False
        or value["playback_authorized"] is not False
        or not isinstance(files, dict)
        or set(files) != set(REQUIRED_SEAL_FILES)
    ):
        raise V10ContractError("v10 seal content is not exact")
    for relative in REQUIRED_SEAL_FILES:
        record = files[relative]
        target = PROJECT_ROOT / relative
        if (
            not isinstance(record, dict)
            or set(record) != {"bytes", "sha256"}
            or record["bytes"] != target.stat().st_size
            or record["sha256"] != sha256_file(target)
        ):
            raise V10ContractError(f"v10 sealed file drift: {relative}")
    return dict(value)


def verify_fresh_audit_authorization(
    config: Mapping[str, Any], *, expected_audit_sha256: str
) -> dict[str, Any]:
    if not is_sha256(expected_audit_sha256):
        raise V10ContractError("v10 audit hash is invalid")
    audit = config["fresh_audit_contract"]
    path = PROJECT_ROOT / audit["required_relative_path"]
    if not path.is_file() or sha256_file(path) != expected_audit_sha256:
        raise V10ContractError("fresh different-agent v10 audit is absent or drifted")
    value = _strict_json(path.read_bytes())
    required = {
        "schema_version", "candidate_id", "candidate_config_sha256",
        "seal_manifest_path", "seal_manifest_sha256", "fresh_independent_audit",
        "auditor_relationship", "verdict", "static_only", "live_authorized",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise V10ContractError("v10 audit schema is not exact")
    if (
        value["schema_version"] != 1
        or value["candidate_id"] != EXACT_CANDIDATE_ID
        or value["candidate_config_sha256"] != CANONICAL_CONFIG_SHA256
        or value["fresh_independent_audit"] is not True
        or value["auditor_relationship"] != audit["required_auditor_relationship"]
        or value["verdict"] != audit["required_verdict"]
        or value["static_only"] is not True
        or value["live_authorized"] is not False
    ):
        raise V10ContractError("v10 audit content does not authorize static acceptance")
    seal = PROJECT_ROOT / value["seal_manifest_path"]
    if (
        value["seal_manifest_path"] != audit["required_seal_manifest_path"]
        or not seal.is_file()
        or sha256_file(seal) != value["seal_manifest_sha256"]
    ):
        raise V10ContractError("v10 audit seal binding is absent or drifted")
    verify_seal_manifest(config, seal)
    return dict(value)


__all__ = [
    "CANONICAL_CONFIG_SHA256", "CONFIG_PATH", "EXACT_CANDIDATE_ID",
    "PROJECT_ROOT", "REQUIRED_SEAL_FILES", "V10ContractError", "is_sha256",
    "load_canonical_config", "sha256_file", "verify_fresh_audit_authorization",
    "verify_preserved_bytes", "verify_seal_manifest",
]
