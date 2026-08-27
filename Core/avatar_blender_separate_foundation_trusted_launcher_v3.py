"""Independent static evaluator for the V3 trusted Blender launcher.

The evaluator reads and hashes the frozen closure. It never invokes PowerShell,
Blender, the worker, authoring, authority, claims, staging, or publication.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Iterable, Mapping


PROJECT_ROOT = Path(r"C:\Users\robmc\Kira")
POLICY_RELATIVE_PATH = "Avatar/avatar_builder/tooling/blender_5_1_separate_foundation_trusted_launcher_v3.json"
WORKER_POLICY_COMPAT_RELATIVE_PATH = "Avatar/avatar_builder/tooling/blender_5_1_separate_foundation_trusted_launcher_v2.json"
LAUNCHER_RELATIVE_PATH = "tools/run_avatar_builder_blender_5_1_separate_foundation_trusted_launcher_v3.ps1"
RUNTIME_IDENTITY_RELATIVE_PATH = "Avatar/avatar_builder/tooling/blender_5_1_runtime_identity_v1.json"
WORKER_RELATIVE_PATH = "tools/blender_author_separate_foundation_bodies_successor_v1.py"
WORKER_CONFIG_RELATIVE_PATH = "Avatar/avatar_builder/tooling/blender_5_1_separate_foundation_authoring_successor_v1.json"
INDEPENDENT_AUDIT_RELATIVE_PATH = "System/Docs/AVATAR_BUILDER_BLENDER_SEPARATE_FOUNDATION_TRUSTED_LAUNCHER_V3_INDEPENDENT_AUDIT.json"
WORKER_AUDIT_COMPAT_RELATIVE_PATH = "System/Docs/AVATAR_BUILDER_BLENDER_SEPARATE_FOUNDATION_TRUSTED_LAUNCHER_V2_INDEPENDENT_AUDIT.json"
STATIC_RECEIPT_RELATIVE_PATH = "System/Docs/AVATAR_BUILDER_BLENDER_SEPARATE_FOUNDATION_AUTHORING_SUCCESSOR_RECEIPT_20260826.json"
RECORDED_RECEIPT_RELATIVE_PATH = "System/Docs/AVATAR_BUILDER_BLENDER_SEPARATE_FOUNDATION_TRUSTED_LAUNCHER_V3_STATIC_RECEIPT_20260827.json"
AUTHORITY_RELATIVE_PATH = "Avatar/avatar_builder/runtime/separate_foundation_authoring_v1/RUN_AUTHORIZATION_V2.json"
CONSUMPTION_RELATIVE_PATH = "Avatar/avatar_builder/runtime/separate_foundation_authoring_v1/RUN_AUTHORIZATION_V2.consumed.json"
CLAIM_RELATIVE_PATH = "Avatar/avatar_builder/runtime/separate_foundation_authoring_v1/RUN_AUTHORIZATION_V2.worker_claimed.json"
RUNTIME_NAMESPACE_RELATIVE_PATH = "Avatar/avatar_builder/runtime/separate_foundation_authoring_v1"

EXPECTED_RESULT_STATUS = "static_sealed_separate_foundation_launcher_v3_ready_independent_audit_passed_authority_absent"
BLOCKED_RESULT_STATUS = "blocked_separate_foundation_launcher_v3_invalid"
EXPECTED_POLICY_RECORD_TYPE = "avatar_builder_blender_separate_foundation_trusted_launcher_contract"
EXPECTED_POLICY_STATUS = "FROZEN_SUCCESSOR_INDEPENDENT_AUDIT_PASSED_AUTHORITY_SEPARATE"
EXPECTED_RUNTIME_IDENTITY_SHA256 = "44fcf953db0422bab2c9ffe0c885550031f918b0b63538024da47124535749a5"
EXPECTED_WORKER_SHA256 = "9685e7c2babd966cb4605ec82a585c19546e9ba1665125d769b95924f70b5890"
EXPECTED_WORKER_CONFIG_SHA256 = "70a72c6f628fab4a85ac4c5e6dc6d3da45ef2e4ef98be4a2162a562d42bebc20"
EXPECTED_OUTPUT_CONTRACT_SHA256 = "11a564fa1bc9f5a4b21a59dfb4eecce622c11418be8a9c14babb4a2f78274c71"
EXPECTED_AUTHORING_RECEIPT_BYTES = 1924
EXPECTED_AUTHORING_RECEIPT_SHA256 = "070f71a3296e0e3591a6ed22071db0ee99a5aa2782397513c713ddd83d7fee08"
EXPECTED_FINAL_FILES = [
    "kira_foundation_candidate.blend",
    "output.manifest.json",
    "success.receipt.json",
    "synthetic_robert_foundation_candidate.blend",
]
EXPECTED_SOURCES = [
    {
        "subject_id": "kira",
        "path": "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6/r6_20260718_163658/kira_provisional_body_r6.glb",
        "bytes": 5_105_808,
        "sha256": "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
    },
    {
        "subject_id": "synthetic_robert",
        "path": "Avatar/outputs/user/dual_robert_candidates_20260729/synthetic_robert_twin_body/synthetic_robert_twin_body.glb",
        "bytes": 8_645_492,
        "sha256": "bfcdf8ec2a1d8444cfef5f7d1382884cb5f6aff685f04c6e4d000b4de0332370",
    },
]
POLICY_KEYS = {
    "schema_version", "record_type", "status", "sealed_launcher_closure_sha256",
    "runtime_identity_sha256", "worker_sha256", "worker_config_sha256", "output_contract_sha256",
}
AUDIT_KEYS = {
    "schema_version", "record_type", "status", "launcher_policy_sha256",
    "sealed_launcher_closure_sha256", "runtime_identity_sha256", "worker_sha256",
    "worker_config_sha256", "output_contract_sha256",
}

POLICY_PATH = PROJECT_ROOT.joinpath(*POLICY_RELATIVE_PATH.split("/"))
LAUNCHER_PATH = PROJECT_ROOT.joinpath(*LAUNCHER_RELATIVE_PATH.split("/"))
RECORDED_RECEIPT_PATH = PROJECT_ROOT.joinpath(*RECORDED_RECEIPT_RELATIVE_PATH.split("/"))


class SeparateFoundationTrustedLauncherV3Rejected(ValueError):
    """Raised when any static V3 trust-boundary invariant differs."""


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _path(root: Path, relative: str) -> Path:
    parts = relative.split("/")
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise SeparateFoundationTrustedLauncherV3Rejected(f"unsafe relative path: {relative}")
    candidate = root.joinpath(*parts)
    resolved_parent = candidate.parent.resolve(strict=True)
    expected_parent = root.joinpath(*parts[:-1]).resolve(strict=True)
    if resolved_parent != expected_parent:
        raise SeparateFoundationTrustedLauncherV3Rejected(f"path parent escaped or traversed a link: {relative}")
    return candidate


def _assert_regular_nonreparse_file(path: Path, label: str) -> os.stat_result:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise SeparateFoundationTrustedLauncherV3Rejected(f"{label} is absent or unreadable") from exc
    if path.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise SeparateFoundationTrustedLauncherV3Rejected(f"{label} is not a regular non-link file")
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if getattr(before, "st_file_attributes", 0) & reparse_flag:
        raise SeparateFoundationTrustedLauncherV3Rejected(f"{label} is a reparse point")
    return before


def _read_stable_bytes(path: Path, label: str) -> bytes:
    before = _assert_regular_nonreparse_file(path, label)
    raw = path.read_bytes()
    after = _assert_regular_nonreparse_file(path, label)
    if (len(raw) != before.st_size or before.st_size != after.st_size or
            before.st_mtime_ns != after.st_mtime_ns or
            getattr(before, "st_ino", None) != getattr(after, "st_ino", None)):
        raise SeparateFoundationTrustedLauncherV3Rejected(f"{label} changed while read")
    return raw


def _reject_constant(value: str) -> None:
    raise SeparateFoundationTrustedLauncherV3Rejected(f"non-finite JSON constant is forbidden: {value}")


def _closed_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    folded: set[str] = set()
    for key, item in pairs:
        if key in value or key.casefold() in folded:
            raise SeparateFoundationTrustedLauncherV3Rejected("duplicate or case-colliding JSON key")
        value[key] = item
        folded.add(key.casefold())
    return value


def _decode_json_object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_closed_object, parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SeparateFoundationTrustedLauncherV3Rejected(f"{label} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise SeparateFoundationTrustedLauncherV3Rejected(f"{label} must be one JSON object")
    return value


def _load_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    raw = _read_stable_bytes(path, label)
    return _decode_json_object(raw, label), raw


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise SeparateFoundationTrustedLauncherV3Rejected(f"{label} exact key closure differs")


def _require_exact_type(value: Any, expected: type, label: str) -> None:
    if type(value) is not expected:
        raise SeparateFoundationTrustedLauncherV3Rejected(f"{label} scalar type differs")


def _slice(source: str, start: str, end: str, label: str) -> str:
    try:
        left = source.index(start)
        right = source.index(end, left + len(start))
    except ValueError as exc:
        raise SeparateFoundationTrustedLauncherV3Rejected(f"{label} function boundary differs") from exc
    return source[left:right]


def _require_order(source: str, markers: Iterable[str], label: str) -> None:
    cursor = -1
    for marker in markers:
        found = source.find(marker, cursor + 1)
        if found < 0:
            raise SeparateFoundationTrustedLauncherV3Rejected(f"{label} marker absent or out of order: {marker}")
        cursor = found


def validate_launcher_source(source: str) -> dict[str, bool]:
    """Adversarial static source validator used by the independent tests."""

    for forbidden in (
        "$StaticExecutionAuthorityGranted", "Start-Process", "Invoke-WebRequest",
        "Invoke-RestMethod", "System.Net.Http", "MOVEFILE_REPLACE_EXISTING",
        "QueryFullProcessImageNameW",
    ):
        if forbidden in source:
            raise SeparateFoundationTrustedLauncherV3Rejected(f"launcher contains forbidden capability: {forbidden}")

    open_directory = _slice(source, "public static SafeFileHandle OpenDirectoryIdentity(string path)",
                            "public static SafeFileHandle OpenDirectoryIdentityForRename", "directory identity open")
    share_match = re.search(r"var share\s*=\s*([^;]+);", open_directory)
    if share_match is None or "FILE_SHARE_DELETE" in share_match.group(1):
        raise SeparateFoundationTrustedLauncherV3Rejected("directory identity handle permits delete sharing")
    for marker in ("FILE_SHARE_READ | FILE_SHARE_WRITE", "FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT"):
        if marker not in open_directory:
            raise SeparateFoundationTrustedLauncherV3Rejected(f"directory identity open lacks: {marker}")

    directory_closure = _slice(source, "function Open-DirectoryIdentityClosure",
                               "function Open-And-RevalidateLockedRows", "directory identity closure")
    _require_order(directory_closure, (
        "Assert-NoReparseAncestry", "OpenDirectoryIdentity($Directory)", "IsReparsePoint($Handle)",
        "StableVolumeFileIdentity($Handle)", "StableIdentity = $StableIdentity",
        "Assert-DirectoryIdentityClosure $Entries", "function Assert-DirectoryIdentityClosure",
        "StableVolumeFileIdentity($Entry.Handle)", "Assert-NoReparseAncestry ([string]$Entry.Path)",
        "OpenDirectoryIdentity([string]$Entry.Path)", "StableVolumeFileIdentity($AtPath)",
        "path no longer names the locked directory identity",
    ), "directory identity closure")

    mapped_api = _slice(source, "public static string ProcessMappedImageDevicePath",
                        "public static string DosPathToDevicePath", "process mapped-image API")
    _require_order(mapped_api, ("NtQueryInformationProcess", "ReadProcessMemory", "GetMappedFileNameW"),
                   "process mapped-image API")

    process = _slice(source, "function Start-SuspendedJobBoundBlender",
                     "function Open-And-ValidateOutputClosure", "suspended process boundary")
    _require_order(process, (
        "Assert-DirectoryIdentityClosure $Locked.DirectoryClosure 'runtime namespace immediately before suspended CreateProcess'",
        "$LockedBlenderIdentity = Get-HandleIdentity", "CreateJobObjectW", "SetInformationJobObject",
        "CreateProcessW", "AssignProcessToJobObject", "ProcessMappedImageDevicePath($ProcessInfo.hProcess)",
        "DosPathToDevicePath($Blender)", "MappedImageDevicePath.Equals",
        "Assert-DirectoryIdentityClosure $Locked.DirectoryClosure 'runtime namespace after suspended CreateProcess'",
        "OpenFileDenyWriteDelete($Blender)",
        "$ProcessImageIdentity.stable_identity -cne $LockedBlenderIdentity.stable_identity",
        "Assert-LockedRows $Locked", "ResumeThread",
    ), "suspended mapped-image identity proof")

    cleanup = _slice(source, "function Get-PreservedInvocationResidueState",
                     "function Invoke-SeparateFoundationTrustedLauncher", "failure residue verifier")
    if "Remove-Item" in cleanup or "Directory]::Delete" in cleanup:
        raise SeparateFoundationTrustedLauncherV3Rejected("failure residue path can be deleted by cleanup")
    _require_order(cleanup, (
        "Invocation residue text boundary differs", "Assert-DirectoryIdentityClosure $OriginalNamespaceClosure",
        "Assert-NoReparseAncestry $Absolute", "IsReparsePoint($IdentityHandle)",
        "StableVolumeFileIdentity($IdentityHandle) -cne $ExpectedStableIdentity",
        "OpenDirectoryIdentity($Absolute)", "IsReparsePoint($AtPath)",
        "StableVolumeFileIdentity($AtPath) -cne $ExpectedStableIdentity", "preserved = $true",
    ), "failure residue identity verifier")

    invoke = source[source.index("function Invoke-SeparateFoundationTrustedLauncher"):]
    _require_order(invoke, (
        "if (-not $Execute)", "Initialize-NativeBoundary", "$PolicyBinding = Read-JsonBinding",
        "$WorkerPolicyCompatBinding = Read-JsonBinding", "$AuditBinding = Read-JsonBinding",
        "$WorkerAuditCompatBinding = Read-JsonBinding", "$AuthorityBinding = Read-JsonBinding",
        "$NamespaceClosure = Open-DirectoryIdentityClosure", "$PreclaimLocked = Open-And-RevalidateLockedRows",
        "Commit-BytesExclusive ($ConsumptionPath", "Commit-BytesExclusive ($WorkerClaimPath",
        "$FullLocked = Open-And-RevalidateLockedRows", "CreateDirectoryExclusive($Stage)",
        "OpenDirectoryIdentityForRename($Stage)",
        "$StageStableIdentity = [AvatarFoundationNativeV2]::StableVolumeFileIdentity($StageHandle)",
        "Start-SuspendedJobBoundBlender", "Open-And-ValidateOutputClosure",
        "Assert-DirectoryIdentityClosure $NamespaceClosure 'runtime namespace before final commit'",
        "RenameDirectoryHandleNoReplace($StageHandle, $Final)",
        "StableVolumeFileIdentity($FinalPathHandle) -cne $StageStableIdentity",
        "Assert-CommittedOutputClosure", "$PrimaryFailure = $_", "Get-PreservedInvocationResidueState",
        "cleanup_performed = $false", "residue_preserved = $true",
    ), "launcher transaction and failure preservation")
    if "Commit-BytesExclusive ($AuditPath" in source:
        raise SeparateFoundationTrustedLauncherV3Rejected("launcher can create its own independent audit")
    if "Commit-BytesExclusive ($AuthorityPath" in source:
        raise SeparateFoundationTrustedLauncherV3Rejected("launcher can issue its own authority")

    read_json = _slice(source, "function Read-JsonBinding", "function Assert-Binding", "strict pre-interpreter JSON")
    _require_order(read_json, ("$Raw = [IO.File]::ReadAllBytes($Path)", "AssertUniqueJsonObjectKeys($Raw)",
                               "$Document = $Text | ConvertFrom-Json"), "strict pre-interpreter JSON")
    for marker in (
        "Assert-JsonBoolean", "Assert-JsonInteger", "Assert-JsonString", "Assert-JsonArray",
        "$MaxJsonBytes = 1048576", "NoDefaultCurrentDirectoryInExePath", "PYTHONDONTWRITEBYTECODE",
        "PYTHONNOUSERSITE", "PYTHONSAFEPATH", "foreach ($Variable in Get-ChildItem Env:)",
        "CUDA path is forbidden", "$Names.Count -ne 4", "$OutputFileIds.Count -ne 4",
        "$Artifacts.Count -ne 2", "source_files_modified -ne $false", "runtime_activation_allowed",
        "publication_performed",
    ):
        if marker not in source:
            raise SeparateFoundationTrustedLauncherV3Rejected(f"launcher trust-boundary marker absent: {marker}")
    return {
        "execute_gate_precedes_native_initialization": True,
        "directory_delete_sharing_disabled": True,
        "ancestor_volume_file_identity_closure_revalidated": True,
        "suspended_process_mapped_image_identity_proven": True,
        "locked_executable_volume_file_identity_reverified": True,
        "handle_bound_no_replace_final_commit": True,
        "failure_residue_preserved_and_identity_verified": True,
        "duplicate_and_case_colliding_json_keys_rejected": True,
        "scalar_type_closure_enforced": True,
        "sealed_environment_scrubbed": True,
        "exact_four_file_output_closure": True,
        "source_modification_forbidden": True,
        "launcher_cannot_create_audit_or_authority": True,
    }


def _truth() -> dict[str, bool]:
    return {
        "independent_audit_present": True, "independent_audit_passed": True,
        "external_issuer_authentication_proven": False, "positive_authority_present": False,
        "authority_consumed": False, "worker_claim_present": False, "execution_authorized": False,
        "execution_trust_boundary_closed": False, "continuous_source_static_locks_proven_for_a_run": False,
        "exclusive_stage_namespace_proven_for_a_run": False, "blender_started": False,
        "body_authoring_performed": False, "source_files_modified": False, "kira_body_accepted": False,
        "synthetic_robert_body_accepted": False, "internal_anatomy_accepted": False,
        "skin_soft_tissue_accepted": False, "movement_accepted": False, "hair_physics_accepted": False,
        "runtime_activation_allowed": False, "publication_allowed": False,
    }


def evaluate_separate_foundation_trusted_launcher_v3(project_root: Path = PROJECT_ROOT,
                                                       *, policy_path: Path | None = None) -> dict[str, Any]:
    failures: list[str] = []
    truth = _truth()
    try:
        root = Path(project_root).resolve(strict=True)
        selected_policy = policy_path or _path(root, POLICY_RELATIVE_PATH)
        policy, policy_raw = _load_json(selected_policy, "V3 launcher policy")
        mirror_policy, mirror_policy_raw = _load_json(_path(root, WORKER_POLICY_COMPAT_RELATIVE_PATH),
                                                       "worker policy compatibility mirror")
        if policy_raw != mirror_policy_raw or policy != mirror_policy:
            raise SeparateFoundationTrustedLauncherV3Rejected("V3 policy and worker compatibility mirror differ")
        _exact_keys(policy, POLICY_KEYS, "launcher policy")
        _require_exact_type(policy["schema_version"], int, "policy schema_version")
        for key in POLICY_KEYS - {"schema_version"}:
            _require_exact_type(policy[key], str, f"policy {key}")

        launcher_raw = _read_stable_bytes(_path(root, LAUNCHER_RELATIVE_PATH), "V3 launcher source")
        launcher_sha = _sha256_bytes(launcher_raw)
        if policy != {
            "schema_version": 2, "record_type": EXPECTED_POLICY_RECORD_TYPE, "status": EXPECTED_POLICY_STATUS,
            "sealed_launcher_closure_sha256": launcher_sha,
            "runtime_identity_sha256": EXPECTED_RUNTIME_IDENTITY_SHA256,
            "worker_sha256": EXPECTED_WORKER_SHA256, "worker_config_sha256": EXPECTED_WORKER_CONFIG_SHA256,
            "output_contract_sha256": EXPECTED_OUTPUT_CONTRACT_SHA256,
        }:
            raise SeparateFoundationTrustedLauncherV3Rejected("schema-v2 policy hash/type binding differs")
        evidence = validate_launcher_source(launcher_raw.decode("utf-8"))

        runtime_raw = _read_stable_bytes(_path(root, RUNTIME_IDENTITY_RELATIVE_PATH), "runtime identity")
        worker_raw = _read_stable_bytes(_path(root, WORKER_RELATIVE_PATH), "frozen worker")
        config, config_raw = _load_json(_path(root, WORKER_CONFIG_RELATIVE_PATH), "frozen worker config")
        if (_sha256_bytes(runtime_raw) != EXPECTED_RUNTIME_IDENTITY_SHA256 or
                _sha256_bytes(worker_raw) != EXPECTED_WORKER_SHA256 or
                _sha256_bytes(config_raw) != EXPECTED_WORKER_CONFIG_SHA256):
            raise SeparateFoundationTrustedLauncherV3Rejected("runtime/worker/config frozen identity differs")
        output = config["output_transaction"]
        if (type(output["exact_final_file_count"]) is not int or output["exact_final_file_count"] != 4 or
                output["exact_final_files"] != EXPECTED_FINAL_FILES or
                output["future_launcher_final_commit_required"] is not True or
                output["overwrite_allowed"] is not False or output["source_modification_allowed"] is not False):
            raise SeparateFoundationTrustedLauncherV3Rejected("four-file no-overwrite output contract differs")
        if config["worker_claim_contract"]["maximum_authority_ttl_seconds"] != 900:
            raise SeparateFoundationTrustedLauncherV3Rejected("one-use authority TTL differs")

        sources: list[dict[str, Any]] = []
        for expected in EXPECTED_SOURCES:
            source_path = _path(root, expected["path"])
            before = _assert_regular_nonreparse_file(source_path, "source GLB")
            raw = _read_stable_bytes(source_path, "source GLB")
            after = _assert_regular_nonreparse_file(source_path, "source GLB")
            actual = {"subject_id": expected["subject_id"], "path": expected["path"], "bytes": len(raw),
                      "sha256": _sha256_bytes(raw), "mtime_ns": after.st_mtime_ns}
            if (actual["bytes"] != expected["bytes"] or actual["sha256"] != expected["sha256"] or
                    before.st_mtime_ns != after.st_mtime_ns):
                raise SeparateFoundationTrustedLauncherV3Rejected("exact source GLB identity or non-mutation evidence differs")
            sources.append(actual)

        authoring_raw = _read_stable_bytes(_path(root, STATIC_RECEIPT_RELATIVE_PATH),
                                           "authoring successor static receipt")
        if (len(authoring_raw) != EXPECTED_AUTHORING_RECEIPT_BYTES or
                _sha256_bytes(authoring_raw) != EXPECTED_AUTHORING_RECEIPT_SHA256):
            raise SeparateFoundationTrustedLauncherV3Rejected("authoring successor static receipt differs")

        audit, audit_raw = _load_json(_path(root, INDEPENDENT_AUDIT_RELATIVE_PATH), "V3 independent audit")
        audit_mirror, audit_mirror_raw = _load_json(_path(root, WORKER_AUDIT_COMPAT_RELATIVE_PATH),
                                                    "worker audit compatibility mirror")
        if audit_raw != audit_mirror_raw or audit != audit_mirror:
            raise SeparateFoundationTrustedLauncherV3Rejected("V3 audit and worker compatibility mirror differ")
        _exact_keys(audit, AUDIT_KEYS, "independent audit")
        _require_exact_type(audit["schema_version"], int, "audit schema_version")
        for key in AUDIT_KEYS - {"schema_version"}:
            _require_exact_type(audit[key], str, f"audit {key}")
        if audit != {
            "schema_version": 1,
            "record_type": "avatar_builder_blender_separate_foundation_launcher_independent_audit",
            "status": "PASS_FROZEN_SUCCESSOR_EXECUTION_AUTHORITY_SEPARATE",
            "launcher_policy_sha256": _sha256_bytes(policy_raw),
            "sealed_launcher_closure_sha256": launcher_sha,
            "runtime_identity_sha256": EXPECTED_RUNTIME_IDENTITY_SHA256,
            "worker_sha256": EXPECTED_WORKER_SHA256,
            "worker_config_sha256": EXPECTED_WORKER_CONFIG_SHA256,
            "output_contract_sha256": EXPECTED_OUTPUT_CONTRACT_SHA256,
        }:
            raise SeparateFoundationTrustedLauncherV3Rejected("independent audit exact binding differs")

        forbidden_runtime_paths = (AUTHORITY_RELATIVE_PATH, CONSUMPTION_RELATIVE_PATH,
                                   CLAIM_RELATIVE_PATH, RUNTIME_NAMESPACE_RELATIVE_PATH)
        if any(os.path.lexists(root.joinpath(*item.split("/"))) for item in forbidden_runtime_paths):
            raise SeparateFoundationTrustedLauncherV3Rejected("authority, claim, stage, or output runtime namespace exists")
        return {
            "status": EXPECTED_RESULT_STATUS, "static_launcher_v3_valid": True,
            "launcher_path": LAUNCHER_RELATIVE_PATH, "launcher_bytes": len(launcher_raw),
            "launcher_sha256": launcher_sha, "policy_path": POLICY_RELATIVE_PATH,
            "policy_bytes": len(policy_raw), "policy_sha256": _sha256_bytes(policy_raw),
            "policy_compatibility_mirror_identical": True, "audit_path": INDEPENDENT_AUDIT_RELATIVE_PATH,
            "audit_bytes": len(audit_raw), "audit_sha256": _sha256_bytes(audit_raw),
            "audit_compatibility_mirror_identical": True,
            "runtime_identity_sha256": EXPECTED_RUNTIME_IDENTITY_SHA256,
            "worker_sha256": EXPECTED_WORKER_SHA256, "worker_config_sha256": EXPECTED_WORKER_CONFIG_SHA256,
            "output_contract_sha256": EXPECTED_OUTPUT_CONTRACT_SHA256, "maximum_authority_ttl_seconds": 900,
            "exact_final_files": EXPECTED_FINAL_FILES, "sources": sources, "launcher_evidence": evidence,
            **truth, "failures": [],
        }
    except (KeyError, OSError, TypeError, UnicodeError, ValueError) as exc:
        failures.append(str(exc))
        return {"status": BLOCKED_RESULT_STATUS, "static_launcher_v3_valid": False,
                **{key: False for key in truth}, "source_files_modified": False, "failures": failures}


def main() -> int:
    result = evaluate_separate_foundation_trusted_launcher_v3()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["static_launcher_v3_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AUDIT_KEYS", "BLOCKED_RESULT_STATUS", "EXPECTED_RESULT_STATUS", "LAUNCHER_PATH",
    "LAUNCHER_RELATIVE_PATH", "POLICY_KEYS", "POLICY_PATH", "POLICY_RELATIVE_PATH",
    "RECORDED_RECEIPT_PATH", "SeparateFoundationTrustedLauncherV3Rejected", "_decode_json_object",
    "evaluate_separate_foundation_trusted_launcher_v3", "validate_launcher_source",
]
