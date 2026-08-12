#!/usr/bin/env python3
"""Narrow Attempt05 launcher for the sealed R23 reseal-v3 engine.

This module does not authorize Blender.  It reuses the reviewed v3 controller
engine byte-for-byte, points it at the append-only Attempt05 reseal-v4 package,
and adds a fail-closed check that every configured bound path is the exact
canonical path reported by the controller's locked Windows handle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import types
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
PREPARATION_DIRECTORY = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt05_reseal_v4_preparation"
)
CONFIG_PATH = PREPARATION_DIRECTORY / (
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT05_RESEAL_V4_CONFIG.json"
)
MANIFEST_PATH = PREPARATION_DIRECTORY / "PACKAGE_MANIFEST.json"
ENGINE_PATH = ROOT / "tools/kira_r23_author_attempt04_reseal_v3_invocation.py"
ENGINE_BYTES = 91479
ENGINE_SHA256 = "671a68e926b3b592ef3cad28b02c10f4e204965878ac3202178ccf6c37e76371"


class ResealV4Error(RuntimeError):
    """Fail-closed Attempt05 preparation/launcher error."""


def _load_engine() -> types.ModuleType:
    source = ENGINE_PATH.read_bytes()
    if len(source) != ENGINE_BYTES or hashlib.sha256(source).hexdigest() != ENGINE_SHA256:
        raise ResealV4Error("sealed reseal-v3 controller engine drifted")
    module = types.ModuleType("_kira_r23_reseal_v3_controller_engine")
    module.__file__ = str(ENGINE_PATH)
    module.__package__ = None
    exec(compile(source, str(ENGINE_PATH), "exec", dont_inherit=True), module.__dict__)
    module.PREPARATION_DIRECTORY = PREPARATION_DIRECTORY
    module.CONFIG_PATH = CONFIG_PATH
    module.MANIFEST_PATH = MANIFEST_PATH

    original_acquire = module.acquire_complete_review_inputs

    def strict_acquire(config: Mapping[str, Any]):
        handles, records = original_acquire(config)
        try:
            for label, binding in config["bound_artifacts"].items():
                record = records.get(label)
                if not isinstance(record, dict) or record.get("path") != binding["path"]:
                    raise module.ResealV3Error(
                        f"locked canonical path differs from config before execution: {label}"
                    )
            return handles, records
        except Exception:
            module.close_handles(handles.values())
            raise

    module.acquire_complete_review_inputs = strict_acquire
    return module


ENGINE = _load_engine()


def _canonical_locked_bound_records(config: Mapping[str, Any]) -> dict[str, Any]:
    """Verify bytes and require literal configured/canonical path equality."""

    if os.name != "nt":
        raise ResealV4Error("canonical locked-path verification is Windows-only")
    records: dict[str, Any] = {}
    for label, binding in config["bound_artifacts"].items():
        handle = None
        try:
            handle, record = ENGINE.locked_binding(
                binding, label, inheritable=False
            )
            if record["path"] != binding["path"]:
                raise ResealV4Error(
                    f"configured path is not exact controller canonical path: {label}: "
                    f"{binding['path']} != {record['path']}"
                )
            records[label] = record
        finally:
            if handle is not None:
                handle.close()
    return records


def verify_preparation() -> tuple[dict[str, Any], dict[str, Any]]:
    config = ENGINE.read_json(CONFIG_PATH)
    manifest = ENGINE.read_json(MANIFEST_PATH)
    if config.get("schema") != "kira.avatar.r23_author_attempt04_reseal_v3.v1":
        raise ResealV4Error("v4 package lost its sealed v3 protocol schema")
    if config.get("package_revision") != (
        "R23_ATTEMPT05_RESEAL_V4_CANONICAL_PATH_AND_OUTPUT_REBIND"
    ):
        raise ResealV4Error("wrong Attempt05 reseal-v4 package revision")
    if config.get("status") != (
        "PREPARED_NON_EXECUTING_LIVE_AUTHORIZATION_ABSENT_BLENDER_NOT_RUN"
    ):
        raise ResealV4Error("Attempt05 preparation status drifted")
    if manifest.get("artifact_kind") != (
        "KIRA_R23_AUTHOR_ATTEMPT05_RESEAL_V4_PREPARATION"
    ):
        raise ResealV4Error("wrong Attempt05 reseal-v4 manifest kind")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ResealV4Error("Attempt05 manifest artifact list is absent")
    expected = set(config["manifest_contract"]["required_artifact_paths"])
    actual = [str(row.get("path")) for row in artifacts]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ResealV4Error("Attempt05 preparation manifest closure drifted")

    manifest_verified: dict[str, Any] = {}
    for row in artifacts:
        verified = ENGINE.verify_binding(row, f"manifest/{row['path']}")
        if verified["path"] != row["path"]:
            raise ResealV4Error(
                f"manifest path is not exact canonical project path: {row['path']}"
            )
        manifest_verified[row["path"]] = verified

    bound = _canonical_locked_bound_records(config)
    preserved = [
        ENGINE.verify_exact_directory(section)
        for section in config["preserved_append_only_evidence"]
    ]
    ENGINE.verify_author_handoff(config)
    command = ENGINE.build_command(config)
    record = {
        "config": {
            "path": ENGINE.relative(CONFIG_PATH),
            "bytes": CONFIG_PATH.stat().st_size,
            "sha256": ENGINE.sha256_file(CONFIG_PATH),
        },
        "manifest": {
            "path": ENGINE.relative(MANIFEST_PATH),
            "bytes": MANIFEST_PATH.stat().st_size,
            "sha256": ENGINE.sha256_file(MANIFEST_PATH),
        },
        "manifest_artifacts": manifest_verified,
        "bound_artifacts": bound,
        "preserved": preserved,
        "command": command,
        "command_sha256": ENGINE.canonical_sha256(command),
        "canonical_path_gate": {
            "checked_labels": sorted(bound),
            "all_config_paths_exactly_equal_locked_controller_records": True,
        },
    }
    return config, record


def arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--execute-attempt05-reseal-v4", action="store_true")
    modes.add_argument("--print-authorization-review", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = arguments(argv)
    config, preparation = verify_preparation()
    command = ENGINE.build_command(config)
    presence = ENGINE.authorization_presence(config)
    if args.print_authorization_review:
        if any(presence.values()):
            raise ResealV4Error(
                "authorization-review output requires the authorization directory to be absent"
            )
        print(
            json.dumps(
                ENGINE.read_only_authorization_review(config, command),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if not args.execute_attempt05_reseal_v4:
        if any(presence.values()) and not all(presence.values()):
            raise ResealV4Error("partial Attempt05 authorization package exists")
        print(
            json.dumps(
                {
                    "status": config["status"],
                    "package_revision": config["package_revision"],
                    "execution_enabled": False,
                    "authorization_presence": presence,
                    "command": command,
                    "command_sha256": ENGINE.canonical_sha256(command),
                    "canonical_path_gate": preparation["canonical_path_gate"],
                    "blender_invoked": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if not config["execution_gate"]["live_authorization_required"]:
        raise ResealV4Error("live authorization requirement drifted")
    return ENGINE.execute_once(config, preparation, command)


if __name__ == "__main__":
    raise SystemExit(main())
