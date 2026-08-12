"""Fail-closed, read-only R19 Attempt-06 package verification for Kira R25.

This verifier is deliberately independent of the rejected R24 author/controller
chain.  It does not import Blender, execute a child process, or write anywhere
inside the preserved R19 package.  The fixed command-line entry point writes a
new append-only verification record outside that package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_RELATIVE = PurePosixPath(
    "RecoverySprint/continuation_20260802/"
    "kira_r19_bald_targeted_correction/attempt_06"
)
MANIFEST_NAME = "PACKAGE_MANIFEST.json"
EXPECTED_MANIFEST_SIZE = 13_209
EXPECTED_MANIFEST_SHA256 = (
    "9c7038b60e2c712e49e810c0b7f7932bf36a18042dd00a6951834be59bb40f0c"
)
EXPECTED_MEMBER_COUNT = 49
EXPECTED_BLEND_RELATIVE = (
    f"{PACKAGE_RELATIVE.as_posix()}/"
    "kira_r19_bald_targeted_material_movement_correction.blend"
)
EXPECTED_BUILD_EVIDENCE_RELATIVE = (
    f"{PACKAGE_RELATIVE.as_posix()}/BUILD_EVIDENCE.json"
)
EXPECTED_IDENTITIES = {
    EXPECTED_BLEND_RELATIVE: {
        "size_bytes": 90_861_425,
        "sha256": (
            "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f"
        ),
    },
    EXPECTED_BUILD_EVIDENCE_RELATIVE: {
        "size_bytes": 167_951,
        "sha256": (
            "f1c20f0570418506150f60df25a6b6ac548597b3108878b1920116f3d0fd714c"
        ),
    },
}
EVIDENCE_BASE_RELATIVE = PurePosixPath(
    "RecoverySprint/continuation_20260809/"
    "kira_r25_r19_attempt06_package_integrity_gate"
)
EVIDENCE_RELATIVE = EVIDENCE_BASE_RELATIVE / "attempt_02"


class PackageIntegrityError(RuntimeError):
    """Raised whenever the sealed package cannot be proven exact."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_reparse_or_link(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError as exc:
        raise PackageIntegrityError(f"cannot lstat required path: {path}: {exc}") from exc
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(info.st_mode) or bool(attributes & reparse_flag)


def _assert_existing_components_nonreparse(root: Path, parts: Iterable[str]) -> Path:
    cursor = root
    if _is_reparse_or_link(cursor):
        raise PackageIntegrityError(f"project root is linked or reparsed: {cursor}")
    for part in parts:
        cursor = cursor / part
        if not os.path.lexists(cursor):
            raise PackageIntegrityError(f"required path component is absent: {cursor}")
        if _is_reparse_or_link(cursor):
            raise PackageIntegrityError(f"linked or reparsed path component rejected: {cursor}")
    return cursor


def _stable_file_identity(path: Path) -> dict[str, Any]:
    if not path.is_file() or _is_reparse_or_link(path):
        raise PackageIntegrityError(f"required regular non-reparse file is absent: {path}")
    before = path.stat()
    digest = hashlib.sha256()
    bytes_read = 0
    try:
        with path.open("rb") as stream:
            while True:
                block = stream.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
                bytes_read += len(block)
    except OSError as exc:
        raise PackageIntegrityError(f"cannot read required file: {path}: {exc}") from exc
    after = path.stat()
    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if any(getattr(before, name) != getattr(after, name) for name in stable_fields):
        raise PackageIntegrityError(f"file changed while it was being verified: {path}")
    if bytes_read != after.st_size:
        raise PackageIntegrityError(f"short or inconsistent read for required file: {path}")
    return {
        "size_bytes": bytes_read,
        "sha256": digest.hexdigest(),
        "stable_read": True,
    }


def _stable_file_bytes(path: Path) -> tuple[dict[str, Any], bytes]:
    """Read and identify the exact bytes once through one held descriptor."""

    if not path.is_file() or _is_reparse_or_link(path):
        raise PackageIntegrityError(f"required regular non-reparse file is absent: {path}")
    try:
        with path.open("rb") as stream:
            descriptor_before = os.fstat(stream.fileno())
            raw = stream.read()
            descriptor_after = os.fstat(stream.fileno())
    except OSError as exc:
        raise PackageIntegrityError(f"cannot read required file: {path}: {exc}") from exc
    path_after = path.stat()
    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if any(
        getattr(descriptor_before, name) != getattr(descriptor_after, name)
        for name in stable_fields
    ) or any(
        getattr(descriptor_after, name) != getattr(path_after, name)
        for name in stable_fields
    ):
        raise PackageIntegrityError(f"file changed while exact bytes were being read: {path}")
    if len(raw) != descriptor_after.st_size:
        raise PackageIntegrityError(f"short or inconsistent exact-byte read: {path}")
    return (
        {
            "size_bytes": len(raw),
            "sha256": _sha256_bytes(raw),
            "stable_read": True,
            "single_held_descriptor_read": True,
        },
        raw,
    )


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PackageIntegrityError(f"duplicate JSON object key rejected: {key}")
        result[key] = value
    return result


def _load_manifest_exact(raw: bytes) -> Mapping[str, Any]:
    """Parse only the same exact raw bytes whose identity was verified."""

    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_json_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageIntegrityError(f"manifest is not unique-key UTF-8 JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise PackageIntegrityError("manifest root must be a JSON object")
    return document


def validate_evidence_relative(raw: str) -> PurePosixPath:
    """Constrain append-only output to one direct child of the exact gate root."""

    if not isinstance(raw, str) or not raw:
        raise PackageIntegrityError("evidence path must be a nonempty project-relative string")
    if "\\" in raw or "\x00" in raw:
        raise PackageIntegrityError("evidence path must use normalized forward slashes only")
    parsed = PurePosixPath(raw)
    if parsed.is_absolute() or raw != parsed.as_posix():
        raise PackageIntegrityError("evidence path must be normalized and project-relative")
    if any(part in ("", ".", "..") or ":" in part for part in parsed.parts):
        raise PackageIntegrityError("evidence path contains traversal, dot, or drive syntax")
    base_parts = EVIDENCE_BASE_RELATIVE.parts
    if parsed.parts[: len(base_parts)] != base_parts or len(parsed.parts) != len(base_parts) + 1:
        raise PackageIntegrityError(
            "evidence path must be one new attempt directly under the exact R25 gate root"
        )
    return parsed


def _confined_new_evidence_output(project_root: Path, relative: PurePosixPath) -> Path:
    base = _assert_existing_components_nonreparse(project_root, EVIDENCE_BASE_RELATIVE.parts)
    if not base.is_dir():
        raise PackageIntegrityError("exact evidence gate root is absent or not a directory")
    output = project_root.joinpath(*relative.parts)
    if output.parent != base:
        raise PackageIntegrityError("evidence output escaped its exact gate root")
    if os.path.lexists(output):
        raise PackageIntegrityError("append-only evidence attempt already exists")
    return output


def _normalize_member_path(raw: Any, package_relative: PurePosixPath) -> str:
    if not isinstance(raw, str) or not raw:
        raise PackageIntegrityError("manifest member path must be a nonempty string")
    if "\\" in raw or "\x00" in raw:
        raise PackageIntegrityError(f"non-canonical member path rejected: {raw!r}")
    parsed = PurePosixPath(raw)
    normalized = parsed.as_posix()
    if parsed.is_absolute() or raw != normalized:
        raise PackageIntegrityError(f"non-normalized project-relative path rejected: {raw!r}")
    if any(part in ("", ".", "..") or ":" in part for part in parsed.parts):
        raise PackageIntegrityError(f"traversal or drive-like member path rejected: {raw!r}")
    package_parts = package_relative.parts
    if parsed.parts[: len(package_parts)] != package_parts:
        raise PackageIntegrityError(f"member is outside the preserved Attempt-06 package: {raw}")
    if len(parsed.parts) <= len(package_parts):
        raise PackageIntegrityError(f"member path does not name a package file: {raw}")
    if parsed.name == MANIFEST_NAME:
        raise PackageIntegrityError("manifest must exclude itself")
    return normalized


def _inventory_package_files(
    project_root: Path, package_relative: PurePosixPath
) -> set[str]:
    package_root = _assert_existing_components_nonreparse(project_root, package_relative.parts)
    if not package_root.is_dir():
        raise PackageIntegrityError(f"package root is not a directory: {package_root}")
    found: set[str] = set()
    pending = [package_root]
    while pending:
        directory = pending.pop()
        try:
            entries = list(os.scandir(directory))
        except OSError as exc:
            raise PackageIntegrityError(f"cannot enumerate package directory: {directory}: {exc}") from exc
        for entry in entries:
            path = Path(entry.path)
            if _is_reparse_or_link(path):
                raise PackageIntegrityError(f"linked or reparsed package entry rejected: {path}")
            try:
                if entry.is_dir(follow_symlinks=False):
                    pending.append(path)
                elif entry.is_file(follow_symlinks=False):
                    relative = path.relative_to(project_root).as_posix()
                    found.add(relative)
                else:
                    raise PackageIntegrityError(f"non-regular package entry rejected: {path}")
            except OSError as exc:
                raise PackageIntegrityError(f"cannot classify package entry: {path}: {exc}") from exc
    return found


def verify_package(
    *,
    project_root: Path,
    package_relative: PurePosixPath,
    expected_manifest_size: int,
    expected_manifest_sha256: str,
    expected_member_count: int,
    expected_identities: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Verify one sealed manifest package without modifying it."""

    project_root = project_root.absolute()
    package_root = _assert_existing_components_nonreparse(project_root, package_relative.parts)
    manifest_path = _assert_existing_components_nonreparse(
        project_root, (*package_relative.parts, MANIFEST_NAME)
    )
    manifest_identity, manifest_raw = _stable_file_bytes(manifest_path)
    if manifest_identity["size_bytes"] != expected_manifest_size:
        raise PackageIntegrityError(
            "manifest byte-size mismatch: "
            f"expected {expected_manifest_size}, got {manifest_identity['size_bytes']}"
        )
    if manifest_identity["sha256"] != expected_manifest_sha256:
        raise PackageIntegrityError(
            "manifest SHA-256 mismatch: "
            f"expected {expected_manifest_sha256}, got {manifest_identity['sha256']}"
        )

    manifest = _load_manifest_exact(manifest_raw)
    expected_root_keys = {
        "append_only_attempt",
        "created_utc",
        "files_excluding_this_manifest",
        "schema_version",
    }
    if set(manifest) != expected_root_keys:
        raise PackageIntegrityError("manifest root keys do not match the sealed schema")
    if manifest.get("schema_version") != 1:
        raise PackageIntegrityError("manifest schema_version must be exactly 1")
    if manifest.get("append_only_attempt") != "attempt_06":
        raise PackageIntegrityError("manifest append_only_attempt must be exactly attempt_06")
    if not isinstance(manifest.get("created_utc"), str) or not manifest["created_utc"]:
        raise PackageIntegrityError("manifest created_utc must be a nonempty string")
    members = manifest.get("files_excluding_this_manifest")
    if not isinstance(members, list) or len(members) != expected_member_count:
        raise PackageIntegrityError(
            f"manifest must contain exactly {expected_member_count} member entries"
        )

    normalized_seen: set[str] = set()
    windows_seen: set[str] = set()
    verified_members: list[dict[str, Any]] = []
    manifest_identities: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(members):
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "size_bytes"}:
            raise PackageIntegrityError(f"member {index} does not match the sealed entry schema")
        normalized = _normalize_member_path(entry["path"], package_relative)
        folded = normalized.casefold()
        if normalized in normalized_seen or folded in windows_seen:
            raise PackageIntegrityError(f"duplicate normalized member path rejected: {normalized}")
        normalized_seen.add(normalized)
        windows_seen.add(folded)
        claimed_hash = entry["sha256"]
        claimed_size = entry["size_bytes"]
        if (
            not isinstance(claimed_hash, str)
            or len(claimed_hash) != 64
            or any(ch not in "0123456789abcdef" for ch in claimed_hash)
        ):
            raise PackageIntegrityError(f"member {normalized} has a non-canonical SHA-256")
        if not isinstance(claimed_size, int) or isinstance(claimed_size, bool) or claimed_size < 0:
            raise PackageIntegrityError(f"member {normalized} has an invalid byte size")
        member_path = _assert_existing_components_nonreparse(
            project_root, PurePosixPath(normalized).parts
        )
        try:
            member_path.resolve(strict=True).relative_to(package_root.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise PackageIntegrityError(f"resolved member escaped package root: {normalized}") from exc
        actual = _stable_file_identity(member_path)
        if actual["size_bytes"] != claimed_size:
            raise PackageIntegrityError(
                f"member size mismatch for {normalized}: expected {claimed_size}, "
                f"got {actual['size_bytes']}"
            )
        if actual["sha256"] != claimed_hash:
            raise PackageIntegrityError(
                f"member SHA-256 mismatch for {normalized}: expected {claimed_hash}, "
                f"got {actual['sha256']}"
            )
        manifest_identities[normalized] = {
            "size_bytes": claimed_size,
            "sha256": claimed_hash,
        }
        verified_members.append(
            {
                "path": normalized,
                "size_bytes": claimed_size,
                "sha256": claimed_hash,
                "stable_read": True,
                "nonreparse": True,
                "contained": True,
            }
        )

    for expected_path, expected_identity in expected_identities.items():
        if manifest_identities.get(expected_path) != dict(expected_identity):
            raise PackageIntegrityError(
                f"required sealed identity is absent or changed: {expected_path}"
            )

    actual_inventory = _inventory_package_files(project_root, package_relative)
    expected_inventory = set(normalized_seen)
    manifest_relative = f"{package_relative.as_posix()}/{MANIFEST_NAME}"
    if actual_inventory != expected_inventory | {manifest_relative}:
        missing = sorted((expected_inventory | {manifest_relative}) - actual_inventory)
        extra = sorted(actual_inventory - (expected_inventory | {manifest_relative}))
        raise PackageIntegrityError(
            f"package file-set mismatch; missing={missing!r}; extra={extra!r}"
        )

    return {
        "schema_version": 1,
        "artifact_kind": "KIRA_R25_R19_ATTEMPT06_PACKAGE_INTEGRITY_GATE",
        "status": "READ_ONLY_PACKAGE_INTEGRITY_PASS",
        "read_only": True,
        "blender_invoked": False,
        "atomic_snapshot": False,
        "atomic_authoring_binding": False,
        "package_relative": package_relative.as_posix(),
        "manifest": {
            "path": manifest_relative,
            **manifest_identity,
            "exact_expected_bytes_and_hash": True,
        },
        "member_count": len(verified_members),
        "unique_normalized_project_relative_paths": True,
        "windows_casefold_unique_paths": True,
        "complete_file_set_exact": True,
        "no_link_or_reparse_components_observed": True,
        "all_members_contained_in_package": True,
        "required_identities": {key: dict(value) for key, value in expected_identities.items()},
        "members": verified_members,
    }


def verify_quiet_tree_twice(
    *,
    project_root: Path,
    package_relative: PurePosixPath,
    expected_manifest_size: int,
    expected_manifest_sha256: str,
    expected_member_count: int,
    expected_identities: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Run two identical full reads; this is still not an atomic snapshot."""

    arguments = {
        "project_root": project_root,
        "package_relative": package_relative,
        "expected_manifest_size": expected_manifest_size,
        "expected_manifest_sha256": expected_manifest_sha256,
        "expected_member_count": expected_member_count,
        "expected_identities": expected_identities,
    }
    first = verify_package(**arguments)
    second = verify_package(**arguments)
    if first != second:
        raise PackageIntegrityError("the two complete quiet-tree verification passes differed")
    result = dict(second)
    result.update(
        {
            "status": "QUIET_TREE_POINT_IN_TIME_PASS",
            "verification_pass_count": 2,
            "both_full_passes_identical": True,
            "second_pass_immediately_preceded_evidence_write": True,
            "atomic_snapshot": False,
            "atomic_authoring_binding": False,
            "limitation": (
                "Two matching read-only passes are a quiet-tree point-in-time check, "
                "not an atomic filesystem snapshot and not a binding to any future authoring run."
            ),
        }
    )
    return result


def _write_append_only_evidence(output_dir: Path, result: Mapping[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=False)
    result_path = output_dir / "PACKAGE_INTEGRITY_EVIDENCE.json"
    markdown_path = output_dir / "README.md"
    verifier_relative = Path(__file__).resolve().relative_to(PROJECT_ROOT).as_posix()
    verifier_identity = _stable_file_identity(Path(__file__).resolve())
    record = {
        **dict(result),
        "verified_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "verifier": {
            "path": verifier_relative,
            "size_bytes": verifier_identity["size_bytes"],
            "sha256": verifier_identity["sha256"],
        },
        "evidence_policy": "append_only_new_attempt_directory",
    }
    encoded = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with result_path.open("xb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    evidence_hash = _sha256_bytes(encoded)
    markdown = (
        "# Kira R25 fresh R19 Attempt-06 package-integrity gate\n\n"
        "Status: **QUIET_TREE_POINT_IN_TIME_PASS**\n\n"
        "This was a read-only verification. Blender was not launched and no file "
        "inside the preserved R19 package was written.\n\n"
        f"- Sealed manifest: `{record['manifest']['path']}`\n"
        f"- Manifest SHA-256: `{record['manifest']['sha256']}`\n"
        f"- Manifest bytes: `{record['manifest']['size_bytes']}`\n"
        f"- Verified member count: `{record['member_count']}`\n"
        f"- Evidence JSON SHA-256: `{evidence_hash}`\n"
        f"- Exact R19 Blend SHA-256: `{EXPECTED_IDENTITIES[EXPECTED_BLEND_RELATIVE]['sha256']}`\n"
        f"- Exact BUILD_EVIDENCE SHA-256: "
        f"`{EXPECTED_IDENTITIES[EXPECTED_BUILD_EVIDENCE_RELATIVE]['sha256']}`\n\n"
        "The gate additionally proved normalized project-relative member paths, "
        "Windows case-fold uniqueness, exact package containment, no observed "
        "symlink/reparse component, stable reads, and an exact package file set. "
        "Two complete passes matched immediately before evidence writing.\n\n"
        "Limit: this is a quiet-tree point-in-time result. It is not an atomic "
        "filesystem snapshot and it creates no atomic authoring binding. Both "
        "`atomic_snapshot` and `atomic_authoring_binding` are explicitly false.\n"
    )
    with markdown_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(markdown)
        stream.flush()
        os.fsync(stream.fileno())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence-relative",
        default=EVIDENCE_RELATIVE.as_posix(),
        help="new project-relative append-only evidence directory",
    )
    args = parser.parse_args(argv)
    evidence_relative = validate_evidence_relative(args.evidence_relative)
    evidence_output = _confined_new_evidence_output(PROJECT_ROOT, evidence_relative)
    result = verify_quiet_tree_twice(
        project_root=PROJECT_ROOT,
        package_relative=PACKAGE_RELATIVE,
        expected_manifest_size=EXPECTED_MANIFEST_SIZE,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        expected_member_count=EXPECTED_MEMBER_COUNT,
        expected_identities=EXPECTED_IDENTITIES,
    )
    _write_append_only_evidence(evidence_output, result)
    print(
        json.dumps(
            {
                "status": "QUIET_TREE_POINT_IN_TIME_PASS",
                "evidence": evidence_relative.as_posix(),
                "atomic_authoring_binding": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PackageIntegrityError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1)
