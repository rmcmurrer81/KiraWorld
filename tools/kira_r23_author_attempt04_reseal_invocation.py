#!/usr/bin/env python3
"""Dry-default, authorization-bound controller for R23 Attempt04 reseal.

There is deliberately no ``--spec`` option. Execution can use only the exact
hard-coded config and manifest. The preparation is inert until a separate
append-only authorization file binds their independently reviewed hashes.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import kira_r23_author_attempt02_invocation as base  # noqa: E402


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


class Attempt04ResealError(RuntimeError):
    pass


def project_path(raw: str | Path) -> Path:
    try:
        return base.project_path(raw)
    except base.Attempt02InvocationError as exc:
        raise Attempt04ResealError(str(exc)) from exc


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return base.sha256_file(path)


def is_reparse(path: Path) -> bool:
    details = path.lstat()
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(details, "st_file_attributes", 0) & flag) or path.is_symlink()


def require_regular_file(path: Path, label: str) -> None:
    if not path.exists() or is_reparse(path) or not path.is_file():
        raise Attempt04ResealError(
            f"{label} is absent, non-regular, or a reparse point: {path}"
        )


def verify_binding(binding: Mapping[str, Any], label: str) -> dict[str, Any]:
    path = project_path(binding["path"])
    require_regular_file(path, label)
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != int(binding["bytes"]) or digest != str(binding["sha256"]):
        raise Attempt04ResealError(
            f"sealed {label} drifted: bytes={size}, sha256={digest}"
        )
    return {"path": base.relative(path), "bytes": size, "sha256": digest}


def verify_exact_directory(section: Mapping[str, Any]) -> dict[str, Any]:
    directory = project_path(section["directory"])
    if not directory.is_dir() or is_reparse(directory):
        raise Attempt04ResealError(
            f"protected directory absent or reparse: {section['label']}"
        )
    entries = sorted(directory.iterdir(), key=lambda entry: entry.name)
    actual_names = [entry.name for entry in entries]
    expected_names = sorted(section["files"])
    if actual_names != expected_names:
        raise Attempt04ResealError(
            f"protected directory entries drifted for {section['label']}: {actual_names}"
        )
    verified: dict[str, Any] = {}
    for entry in entries:
        require_regular_file(entry, f"{section['label']}/{entry.name}")
        binding = {
            **section["files"][entry.name],
            "path": f"{section['directory']}/{entry.name}",
        }
        verified[entry.name] = verify_binding(
            binding, f"{section['label']}/{entry.name}"
        )
    return verified


def verify_all(config: Mapping[str, Any]) -> dict[str, Any]:
    verified: dict[str, Any] = {}
    for label, binding in config["bound_artifacts"].items():
        verified[label] = verify_binding(binding, label)
    for section in config["preserved_append_only_evidence"]:
        rows = verify_exact_directory(section)
        for name, record in rows.items():
            verified[f"{section['label']}/{name}"] = record
    return verified


def snapshot_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    import hashlib

    return hashlib.sha256(encoded).hexdigest()


def verify_blender_identity(config: Mapping[str, Any]) -> dict[str, Any]:
    expected = config["blender_identity"]
    path = Path(expected["path"])
    if not path.is_absolute():
        raise Attempt04ResealError("Blender executable path is not absolute")
    require_regular_file(path, "Blender executable")
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != int(expected["bytes"]) or digest != str(expected["sha256"]):
        raise Attempt04ResealError(
            f"Blender executable drifted: bytes={size}, sha256={digest}"
        )
    return {
        "path": str(path.resolve()),
        "bytes": size,
        "sha256": digest,
        "file_version": expected["file_version"],
        "product_version": expected["product_version"],
    }


def verify_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    manifest_path = project_path(MANIFEST_PATH)
    require_regular_file(manifest_path, "reseal package manifest")
    manifest = read_json(manifest_path)
    if manifest.get("artifact_kind") != "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_PREPARATION":
        raise Attempt04ResealError("wrong reseal manifest artifact kind")
    actual_paths = {str(entry["path"]) for entry in manifest["artifacts"]}
    expected_paths = set(config["manifest_contract"]["required_artifact_paths"])
    if actual_paths != expected_paths:
        raise Attempt04ResealError("reseal manifest artifact path closure drifted")
    verified = {
        entry["path"]: verify_binding(entry, f"manifest/{entry['path']}")
        for entry in manifest["artifacts"]
    }
    preparation = project_path(config["manifest_contract"]["preparation_directory"])
    if not preparation.is_dir() or is_reparse(preparation):
        raise Attempt04ResealError("reseal preparation directory absent or reparse")
    entries = sorted(preparation.iterdir(), key=lambda entry: entry.name)
    actual_entries = [entry.name for entry in entries]
    expected_entries = sorted(config["manifest_contract"]["preparation_directory_entries"])
    if actual_entries != expected_entries:
        raise Attempt04ResealError(
            f"reseal preparation directory entries drifted: {actual_entries}"
        )
    for entry in entries:
        require_regular_file(entry, f"reseal preparation/{entry.name}")
    return {
        "path": base.relative(manifest_path),
        "bytes": manifest_path.stat().st_size,
        "sha256": sha256_file(manifest_path),
        "artifacts": verified,
    }


def assert_no_reparse_ancestors(path: Path) -> None:
    resolved_root = ROOT.resolve()
    target = path.resolve(strict=False)
    try:
        relative = target.relative_to(resolved_root)
    except ValueError as exc:
        raise Attempt04ResealError(f"output escaped project root: {path}") from exc
    current = resolved_root
    for part in relative.parts[:-1]:
        current = current / part
        if current.exists() and is_reparse(current):
            raise Attempt04ResealError(f"output ancestor is a reparse point: {current}")


def output_contract(config: Mapping[str, Any]) -> dict[str, Any]:
    repair = config["repair_contract"]
    configured = project_path(repair["configured_output_required"])
    effective = project_path(repair["effective_output"])
    execution = project_path(config["future_execution"]["directory"])
    if configured == effective or not configured.is_dir() or is_reparse(configured):
        raise Attempt04ResealError("configured/effective output isolation failed")
    assert_no_reparse_ancestors(effective)
    assert_no_reparse_ancestors(execution)
    if effective.exists():
        raise Attempt04ResealError("append-only Attempt04 author output already exists")
    if execution.exists():
        raise Attempt04ResealError("append-only Attempt04 reseal execution already exists")
    return {
        "configured": configured,
        "configured_relative": repair["configured_output_required"],
        "effective": effective,
        "effective_relative": repair["effective_output"],
        "execution": execution,
        "execution_relative": config["future_execution"]["directory"],
    }


def build_command(config: Mapping[str, Any]) -> list[str]:
    contract = config["command_contract"]
    try:
        config_argument = base.validate_relative_config_argument(
            contract["sealed_author_config_argument"]
        )
    except base.Attempt02InvocationError as exc:
        raise Attempt04ResealError(str(exc)) from exc
    source = project_path(config["bound_artifacts"]["r19_source_blend"]["path"])
    wrapper = project_path(config["bound_artifacts"]["reseal_blender_wrapper"]["path"])
    command = [
        str(Path(config["blender_identity"]["path"])),
        "--background",
        "--factory-startup",
        "--disable-autoexec",
        str(source),
        "--python-exit-code",
        str(int(contract["python_exit_code"])),
        "--python",
        str(wrapper),
        "--",
        "--config",
        config_argument,
        str(contract["worker_flag"]),
    ]
    if command.index("--python-exit-code") >= command.index("--python"):
        raise Attempt04ResealError("--python-exit-code must precede --python")
    if command[command.index("--python-exit-code") + 1] != "7":
        raise Attempt04ResealError("Python exit code is not 7")
    if Path(command[command.index("--config") + 1]).is_absolute():
        raise Attempt04ResealError("sealed author config argument became absolute")
    return command


def verify_authorization(
    config: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, Any]:
    contract = config["execution_gate"]
    authorization_path = project_path(contract["authorization_path"])
    require_regular_file(authorization_path, "Attempt04 reseal authorization")
    authorization = read_json(authorization_path)
    if authorization.get("schema") != "kira.avatar.r23_attempt04_reseal_authorization.v1":
        raise Attempt04ResealError("wrong Attempt04 reseal authorization schema")
    if authorization.get("execution_enabled") is not True:
        raise Attempt04ResealError("Attempt04 reseal authorization is not enabled")
    actual = {
        "reviewed_manifest_sha256": manifest["sha256"],
        "reviewed_config_sha256": sha256_file(project_path(CONFIG_PATH)),
        "reviewed_controller_sha256": sha256_file(Path(__file__).resolve()),
        "reviewed_wrapper_sha256": sha256_file(
            project_path(config["bound_artifacts"]["reseal_blender_wrapper"]["path"])
        ),
        "effective_output": config["repair_contract"]["effective_output"],
        "execution_output": config["future_execution"]["directory"],
    }
    for key, value in actual.items():
        if authorization.get(key) != value:
            raise Attempt04ResealError(f"authorization binding drifted: {key}")
    return {
        "path": base.relative(authorization_path),
        "bytes": authorization_path.stat().st_size,
        "sha256": sha256_file(authorization_path),
        **actual,
    }


def postrun_protection(
    config: Mapping[str, Any],
    pre_verified: Mapping[str, Any],
    pre_manifest: Mapping[str, Any],
    pre_blender: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        post_verified = verify_all(config)
        post_manifest = verify_manifest(config)
        post_blender = verify_blender_identity(config)
        checks = {
            "protected_snapshot_exact": post_verified == pre_verified,
            "manifest_snapshot_exact": post_manifest == pre_manifest,
            "blender_identity_exact": post_blender == pre_blender,
        }
        return {
            "passed": all(checks.values()),
            "checks": checks,
            "pre_snapshot_sha256": snapshot_sha256(pre_verified),
            "post_snapshot_sha256": snapshot_sha256(post_verified),
            "error": None,
        }
    except Exception as exc:
        return {
            "passed": False,
            "checks": {},
            "pre_snapshot_sha256": snapshot_sha256(pre_verified),
            "post_snapshot_sha256": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def execute_once(
    config: Mapping[str, Any],
    manifest: Mapping[str, Any],
    blender_identity: Mapping[str, Any],
    authorization: Mapping[str, Any],
) -> int:
    pre_verified = verify_all(config)
    outputs = output_contract(config)
    command = build_command(config)
    if base.blender_process_count() != 0:
        raise Attempt04ResealError("Blender is already active")
    run = outputs["execution"]
    run.mkdir(parents=True, exist_ok=False)
    pre_run = run / config["future_execution"]["pre_run"]
    stdout_path = run / config["future_execution"]["stdout"]
    stderr_path = run / config["future_execution"]["stderr"]
    post_run = run / config["future_execution"]["post_run"]
    base.write_json_exclusive(
        pre_run,
        {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_PRE_RUN",
            "created_utc": base.utc_now(),
            "manifest": {key: manifest[key] for key in ("path", "bytes", "sha256")},
            "config": {
                "path": base.relative(project_path(CONFIG_PATH)),
                "sha256": sha256_file(project_path(CONFIG_PATH)),
            },
            "authorization": authorization,
            "blender_identity": blender_identity,
            "verified": pre_verified,
            "verified_snapshot_sha256": snapshot_sha256(pre_verified),
            "command": command,
            "blender_process_count_before": 0,
        },
    )
    environment = os.environ.copy()
    environment[MANIFEST_ENV] = manifest["sha256"]
    environment[CONFIG_ENV] = sha256_file(project_path(CONFIG_PATH))
    environment[AUTHORIZATION_ENV] = authorization["sha256"]
    started = base.utc_now()
    process_exit = 7
    launch_error = None
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            result = subprocess.run(
                command,
                cwd=ROOT,
                stdout=stdout,
                stderr=stderr,
                check=False,
                shell=False,
                creationflags=flags,
                env=environment,
            )
        process_exit = int(result.returncode)
    except Exception as exc:
        launch_error = f"{type(exc).__name__}: {exc}"
        stdout_path.touch(exist_ok=True)
        stderr_path.touch(exist_ok=True)
    ended = base.utc_now()
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    success = config["success_contract"]
    output = outputs["effective"]
    build = output / success["build_evidence"]
    failure = output / success["failure_evidence"]
    candidate = output / success["candidate"]
    effective_exit = base.classified_exit_code(
        process_exit,
        stderr_text,
        build.is_file(),
        failure.is_file(),
        candidate.is_file(),
        int(config["command_contract"]["python_exit_code"]),
    )
    protection = postrun_protection(
        config, pre_verified, manifest, blender_identity
    )
    if not protection["passed"] or launch_error is not None:
        effective_exit = int(config["command_contract"]["python_exit_code"])
    base.write_json_exclusive(
        post_run,
        {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_POST_RUN",
            "started_utc": started,
            "ended_utc": ended,
            "process_exit_code": process_exit,
            "effective_exit_code": effective_exit,
            "launch_error": launch_error,
            "postrun_protection": protection,
            "stdout": {
                "path": base.relative(stdout_path),
                "bytes": stdout_path.stat().st_size,
                "sha256": sha256_file(stdout_path),
            },
            "stderr": {
                "path": base.relative(stderr_path),
                "bytes": stderr_path.stat().st_size,
                "sha256": sha256_file(stderr_path),
                "contains_traceback": "Traceback (most recent call last):" in stderr_text,
            },
            "effective_output": {
                "path": outputs["effective_relative"],
                "directory_exists": output.is_dir(),
                "build_evidence_exists": build.is_file(),
                "failure_evidence_exists": failure.is_file(),
                "candidate_exists": candidate.is_file(),
            },
            "blender_process_count_after": base.blender_process_count(),
        },
    )
    return int(effective_exit)


def arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-attempt04-reseal", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = arguments(argv)
    config_path = project_path(CONFIG_PATH)
    config = read_json(config_path)
    if config.get("schema") != "kira.avatar.r23_author_attempt04_repair.v1":
        raise Attempt04ResealError("wrong delegated Attempt04 repair schema")
    if config.get("reseal_schema") != "kira.avatar.r23_author_attempt04_reseal.v1":
        raise Attempt04ResealError("wrong Attempt04 reseal config schema")
    verified = verify_all(config)
    manifest = verify_manifest(config)
    blender = verify_blender_identity(config)
    outputs = output_contract(config)
    command = build_command(config)
    blender_count = base.blender_process_count()
    authorization_path = project_path(config["execution_gate"]["authorization_path"])
    if not args.execute_attempt04_reseal:
        print(
            json.dumps(
                {
                    "status": "DRY_ATTEMPT04_RESEAL_PREPARED_NOT_AUTHORIZED_BLENDER_NOT_RUN",
                    "execution_enabled": False,
                    "config": {
                        "path": base.relative(config_path),
                        "bytes": config_path.stat().st_size,
                        "sha256": sha256_file(config_path),
                    },
                    "manifest": {key: manifest[key] for key in ("path", "bytes", "sha256")},
                    "verified_count": len(verified),
                    "verified_snapshot_sha256": snapshot_sha256(verified),
                    "blender_identity": blender,
                    "command": command,
                    "authorization_path": base.relative(authorization_path),
                    "authorization_exists": authorization_path.exists(),
                    "effective_output": outputs["effective_relative"],
                    "effective_output_exists": False,
                    "execution_output": outputs["execution_relative"],
                    "execution_output_exists": False,
                    "blender_process_count_observed": blender_count,
                    "blender_started": False,
                },
                indent=2,
            )
        )
        return 0
    authorization = verify_authorization(config, manifest)
    return execute_once(config, manifest, blender, authorization)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Attempt04ResealError, base.Attempt02InvocationError) as exc:
        print(f"Attempt04 reseal invocation refused: {exc}", file=sys.stderr)
        raise SystemExit(2)
