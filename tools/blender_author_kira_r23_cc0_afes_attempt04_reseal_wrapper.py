#!/usr/bin/env python3
"""Inert-until-authorized execution seal for the R23 Attempt04 repair.

This wrapper does not implement a second topology repair. It verifies the new
append-only reseal package, exact Blender identity, and protected directory
shape, then delegates to the hash-bound Attempt04 topology implementation.
The controller must supply independently approved manifest/config/
authorization hashes through task-specific environment values.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
from typing import Any, Mapping

import bpy


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_author_kira_r23_cc0_afes_attempt04_wrapper as topology_impl  # noqa: E402


CONFIG_PATH = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt04_reseal_preparation/"
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT04_RESEAL_CONFIG.json"
)
MANIFEST_PATH = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt04_reseal_preparation/"
    "PACKAGE_MANIFEST.json"
)
MANIFEST_ENV = "KIRA_R23_ATTEMPT04_RESEAL_APPROVED_MANIFEST_SHA256"
CONFIG_ENV = "KIRA_R23_ATTEMPT04_RESEAL_APPROVED_CONFIG_SHA256"
AUTHORIZATION_ENV = "KIRA_R23_ATTEMPT04_RESEAL_AUTHORIZATION_SHA256"


def project_path(raw: str | Path) -> Path:
    value = Path(str(raw))
    if value.is_absolute() or ".." in value.parts:
        raise topology_impl.sealed_worker.R23AuthorError(
            f"unsafe reseal project-relative path: {raw}"
        )
    resolved = (ROOT / value).resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as exc:
        raise topology_impl.sealed_worker.R23AuthorError(
            f"reseal path escaped project root: {raw}"
        ) from exc
    return resolved


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_reparse(path: Path) -> bool:
    details = path.lstat()
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(details, "st_file_attributes", 0) & flag) or path.is_symlink()


def require_regular_file(path: Path, label: str) -> None:
    if not path.exists() or is_reparse(path) or not path.is_file():
        raise topology_impl.sealed_worker.R23AuthorError(
            f"reseal {label} is absent, non-regular, or a reparse point"
        )


def verify_binding(binding: Mapping[str, Any], label: str) -> dict[str, Any]:
    path = project_path(binding["path"])
    require_regular_file(path, label)
    size = path.stat().st_size
    digest = topology_impl.sealed_worker.sha256_file(path)
    if size != int(binding["bytes"]) or digest != str(binding["sha256"]):
        raise topology_impl.sealed_worker.R23AuthorError(
            f"reseal binding drifted for {label}: bytes={size}, sha256={digest}"
        )
    return {
        "path": topology_impl.sealed_worker.relative(path),
        "bytes": size,
        "sha256": digest,
    }


def verify_exact_directory(section: Mapping[str, Any]) -> dict[str, Any]:
    directory = project_path(section["directory"])
    if not directory.is_dir() or is_reparse(directory):
        raise topology_impl.sealed_worker.R23AuthorError(
            f"protected directory is absent or reparse: {section['label']}"
        )
    entries = sorted(directory.iterdir(), key=lambda item: item.name)
    actual_names = [entry.name for entry in entries]
    expected_names = sorted(section["files"])
    if actual_names != expected_names:
        raise topology_impl.sealed_worker.R23AuthorError(
            f"protected directory entries drifted for {section['label']}: {actual_names}"
        )
    verified = {}
    for entry in entries:
        require_regular_file(entry, f"{section['label']}/{entry.name}")
        verified[entry.name] = verify_binding(
            {
                **section["files"][entry.name],
                "path": f"{section['directory']}/{entry.name}",
            },
            f"{section['label']}/{entry.name}",
        )
    return verified


def require_env_sha256(name: str) -> str:
    value = os.environ.get(name, "").strip().lower()
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise topology_impl.sealed_worker.R23AuthorError(
            f"required reseal authorization environment hash missing: {name}"
        )
    return value


def verify_blender_identity(config: Mapping[str, Any]) -> dict[str, Any]:
    expected = config["blender_identity"]
    executable = Path(sys.executable).resolve()
    configured = Path(expected["path"]).resolve()
    if executable != configured:
        raise topology_impl.sealed_worker.R23AuthorError(
            f"Blender executable path drifted: {executable}"
        )
    require_regular_file(executable, "Blender executable")
    size = executable.stat().st_size
    digest = topology_impl.sealed_worker.sha256_file(executable)
    if size != int(expected["bytes"]) or digest != str(expected["sha256"]):
        raise topology_impl.sealed_worker.R23AuthorError(
            f"Blender executable identity drifted: bytes={size}, sha256={digest}"
        )
    actual_version = ".".join(str(value) for value in bpy.app.version[:2])
    if actual_version != str(expected["bpy_version_prefix"]):
        raise topology_impl.sealed_worker.R23AuthorError(
            f"Blender bpy version drifted: {actual_version}"
        )
    return {
        "path": str(executable),
        "bytes": size,
        "sha256": digest,
        "bpy_version_prefix": actual_version,
    }


def verify_reseal_package() -> tuple[dict[str, Any], dict[str, Any]]:
    config_file = project_path(CONFIG_PATH)
    manifest_file = project_path(MANIFEST_PATH)
    require_regular_file(config_file, "reseal config")
    require_regular_file(manifest_file, "reseal manifest")
    expected_manifest_sha = require_env_sha256(MANIFEST_ENV)
    expected_config_sha = require_env_sha256(CONFIG_ENV)
    authorization_sha = require_env_sha256(AUTHORIZATION_ENV)
    actual_manifest_sha = topology_impl.sealed_worker.sha256_file(manifest_file)
    actual_config_sha = topology_impl.sealed_worker.sha256_file(config_file)
    if actual_manifest_sha != expected_manifest_sha:
        raise topology_impl.sealed_worker.R23AuthorError(
            "reseal manifest does not match independently approved hash"
        )
    if actual_config_sha != expected_config_sha:
        raise topology_impl.sealed_worker.R23AuthorError(
            "reseal config does not match independently approved hash"
        )
    config = read_json(config_file)
    manifest = read_json(manifest_file)
    if config.get("schema") != "kira.avatar.r23_author_attempt04_repair.v1":
        raise topology_impl.sealed_worker.R23AuthorError("wrong delegated repair schema")
    if config.get("reseal_schema") != "kira.avatar.r23_author_attempt04_reseal.v1":
        raise topology_impl.sealed_worker.R23AuthorError("wrong reseal config schema")
    if manifest.get("artifact_kind") != "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_PREPARATION":
        raise topology_impl.sealed_worker.R23AuthorError("wrong reseal manifest kind")
    manifest_paths = {str(entry["path"]) for entry in manifest["artifacts"]}
    required_paths = set(config["manifest_contract"]["required_artifact_paths"])
    if manifest_paths != required_paths:
        raise topology_impl.sealed_worker.R23AuthorError(
            "reseal manifest artifact closure differs from config"
        )
    verified_manifest = {
        entry["path"]: verify_binding(entry, f"manifest/{entry['path']}")
        for entry in manifest["artifacts"]
    }
    for section in config["preserved_append_only_evidence"]:
        verify_exact_directory(section)
    preparation = project_path(config["manifest_contract"]["preparation_directory"])
    expected_entries = sorted(config["manifest_contract"]["preparation_directory_entries"])
    actual_entries = sorted(entry.name for entry in preparation.iterdir())
    if actual_entries != expected_entries:
        raise topology_impl.sealed_worker.R23AuthorError(
            f"reseal preparation directory entries drifted: {actual_entries}"
        )
    if any(is_reparse(entry) for entry in preparation.iterdir()):
        raise topology_impl.sealed_worker.R23AuthorError(
            "reseal preparation contains a reparse-point entry"
        )
    blender = verify_blender_identity(config)
    return config, {
        "manifest": {
            "path": topology_impl.sealed_worker.relative(manifest_file),
            "sha256": actual_manifest_sha,
        },
        "config": {
            "path": topology_impl.sealed_worker.relative(config_file),
            "sha256": actual_config_sha,
        },
        "authorization_sha256": authorization_sha,
        "manifest_artifacts": verified_manifest,
        "blender": blender,
    }


def main() -> int:
    config, _verified = verify_reseal_package()
    topology_impl.REPAIR_CONFIG = CONFIG_PATH
    topology_impl.RUNTIME["reseal_package_verified"] = _verified
    return int(topology_impl.main())


if __name__ == "__main__":
    raise SystemExit(main())
