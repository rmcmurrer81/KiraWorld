#!/usr/bin/env python3
"""Invocation controller for one future R23 Author Attempt 03.

Dry-run is the default. The Blender-side wrapper patches only the missing
edge-face helper and append-only output routing; sealed author files stay exact.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import kira_r23_author_attempt02_invocation as base


ROOT = base.ROOT
DEFAULT_SPEC = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt03_wrapper_preparation/"
    "INVOCATION_CONFIG.json"
)


def verify_all(spec: Mapping[str, Any]) -> dict[str, Any]:
    verified: dict[str, Any] = {}
    for label, binding in spec["bound_artifacts"].items():
        verified[label] = base.verify_file(
            base.project_path(binding["path"]), binding, label
        )
    for section in ("preserved_attempt01_failure", "preserved_attempt02_execution"):
        root = base.project_path(spec[section]["directory"])
        for name, binding in spec[section]["files"].items():
            verified[f"{section}/{name}"] = base.verify_file(
                root / name, binding, f"{section} {name}"
            )
    author_failure = spec["preserved_attempt02_author_failure"]
    root = base.project_path(author_failure["directory"])
    expected_name = author_failure["only_expected_file"]
    names = sorted(path.name for path in root.iterdir()) if root.is_dir() else []
    if names != [expected_name]:
        raise base.Attempt02InvocationError(
            f"preserved Attempt02 author failure directory drifted: {names}"
        )
    verified["preserved_attempt02_author_failure"] = base.verify_file(
        root / expected_name,
        author_failure,
        "Attempt02 author FAILURE_EVIDENCE.json",
    )
    return verified


def output_contract(spec: Mapping[str, Any]) -> dict[str, Any]:
    patch = spec["runtime_patch_contract"]
    configured_raw = str(patch["configured_output_required"])
    effective_raw = str(patch["effective_output"])
    configured = base.project_path(configured_raw)
    effective = base.project_path(effective_raw)
    author_config = base.read_json(
        base.project_path(spec["bound_artifacts"]["sealed_author_config"]["path"])
    )
    actual_configured = str(author_config["output"]["directory"])
    if actual_configured != configured_raw:
        raise base.Attempt02InvocationError(
            f"sealed author configured output drifted: {actual_configured}"
        )
    if configured == effective:
        raise base.Attempt02InvocationError("Attempt03 output is not isolated")
    if not configured.is_dir():
        raise base.Attempt02InvocationError(
            "preserved Attempt02 author failure directory is absent"
        )
    if effective.exists():
        raise base.Attempt02InvocationError(
            f"append-only Attempt03 output already exists: {base.relative(effective)}"
        )
    return {
        "configured": configured,
        "configured_relative": configured_raw,
        "effective": effective,
        "effective_relative": effective_raw,
        "configured_exists": True,
        "effective_exists": False,
    }


def build_command(spec: Mapping[str, Any]) -> list[str]:
    contract = spec["command_contract"]
    config_argument = base.validate_relative_config_argument(
        str(contract["config_argument"])
    )
    source = base.project_path(spec["bound_artifacts"]["r19_source_blend"]["path"])
    wrapper = base.project_path(
        spec["bound_artifacts"]["blender_attempt03_wrapper"]["path"]
    )
    command = [
        str(Path(contract["blender_executable"])),
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
        raise base.Attempt02InvocationError(
            "--python-exit-code must be parsed before --python"
        )
    if command[command.index("--python-exit-code") + 1] != "7":
        raise base.Attempt02InvocationError("Attempt03 Python exit code drifted")
    if Path(command[command.index("--config") + 1]).is_absolute():
        raise base.Attempt02InvocationError("Attempt03 config became absolute")
    return command


def execute_once(spec_path: Path, spec: Mapping[str, Any]) -> int:
    verified = verify_all(spec)
    outputs = output_contract(spec)
    command = build_command(spec)
    if base.blender_process_count() != 0:
        raise base.Attempt02InvocationError("Blender is already active")
    run = base.project_path(spec["future_execution"]["directory"])
    if run.exists():
        raise base.Attempt02InvocationError(
            f"append-only Attempt03 execution exists: {base.relative(run)}"
        )
    run.mkdir(parents=True, exist_ok=False)
    pre_run = run / spec["future_execution"]["pre_run"]
    stdout_path = run / spec["future_execution"]["stdout"]
    stderr_path = run / spec["future_execution"]["stderr"]
    post_run = run / spec["future_execution"]["post_run"]
    configured_failure = (
        outputs["configured"]
        / spec["preserved_attempt02_author_failure"]["only_expected_file"]
    )
    configured_hash_before = base.sha256_file(configured_failure)
    base.write_json_exclusive(
        pre_run,
        {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT03_PRE_RUN",
            "created_utc": base.utc_now(),
            "spec": {
                "path": base.relative(spec_path),
                "sha256": base.sha256_file(spec_path),
            },
            "verified": verified,
            "command": command,
            "config_argument_is_relative": not Path(
                command[command.index("--config") + 1]
            ).is_absolute(),
            "python_exit_code_precedes_python": command.index(
                "--python-exit-code"
            )
            < command.index("--python"),
            "configured_output": {
                "path": outputs["configured_relative"],
                "exists": True,
                "preserved_failure_sha256": configured_hash_before,
            },
            "effective_output": {
                "path": outputs["effective_relative"],
                "exists": False,
                "in_project": True,
            },
            "blender_process_count_before": 0,
        },
    )
    started = base.utc_now()
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        result = subprocess.run(
            command,
            cwd=ROOT,
            stdout=stdout,
            stderr=stderr,
            check=False,
            shell=False,
            creationflags=flags,
        )
    ended = base.utc_now()
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    output = outputs["effective"]
    build = output / spec["success_contract"]["build_evidence"]
    failure = output / spec["success_contract"]["failure_evidence"]
    candidate = output / spec["success_contract"]["candidate"]
    effective_exit = base.classified_exit_code(
        result.returncode,
        stderr_text,
        build.is_file(),
        failure.is_file(),
        candidate.is_file(),
        int(spec["command_contract"]["python_exit_code"]),
    )
    configured_hash_after = base.sha256_file(configured_failure)
    base.write_json_exclusive(
        post_run,
        {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT03_POST_RUN",
            "started_utc": started,
            "ended_utc": ended,
            "process_exit_code": int(result.returncode),
            "effective_exit_code": int(effective_exit),
            "stdout": {
                "path": base.relative(stdout_path),
                "bytes": stdout_path.stat().st_size,
                "sha256": base.sha256_file(stdout_path),
            },
            "stderr": {
                "path": base.relative(stderr_path),
                "bytes": stderr_path.stat().st_size,
                "sha256": base.sha256_file(stderr_path),
                "contains_traceback": "Traceback (most recent call last):"
                in stderr_text,
            },
            "configured_output": {
                "path": outputs["configured_relative"],
                "preserved_failure_sha256_before": configured_hash_before,
                "preserved_failure_sha256_after": configured_hash_after,
                "unchanged": configured_hash_before == configured_hash_after,
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
    parser.add_argument("--spec", default=DEFAULT_SPEC.as_posix())
    parser.add_argument("--execute-attempt03", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = arguments(argv)
    spec_path = base.project_path(args.spec)
    spec = base.read_json(spec_path)
    if spec.get("schema") != "kira.avatar.r23_author_attempt03_wrapper.v1":
        raise base.Attempt02InvocationError("wrong Attempt03 invocation schema")
    verified = verify_all(spec)
    outputs = output_contract(spec)
    command = build_command(spec)
    if not args.execute_attempt03:
        print(
            json.dumps(
                {
                    "status": "DRY_ATTEMPT03_WRAPPER_ONLY_BLENDER_NOT_RUN",
                    "spec": {
                        "path": base.relative(spec_path),
                        "sha256": base.sha256_file(spec_path),
                    },
                    "verified_count": len(verified),
                    "command": command,
                    "config_argument_is_relative": not Path(
                        command[command.index("--config") + 1]
                    ).is_absolute(),
                    "python_exit_code_precedes_python": command.index(
                        "--python-exit-code"
                    )
                    < command.index("--python"),
                    "configured_output": outputs["configured_relative"],
                    "configured_output_exists": outputs["configured_exists"],
                    "effective_output": outputs["effective_relative"],
                    "effective_output_exists": outputs["effective_exists"],
                    "blender_run": False,
                },
                indent=2,
            )
        )
        return 0
    return execute_once(spec_path, spec)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except base.Attempt02InvocationError as exc:
        print(f"Attempt03 invocation refused: {exc}", file=sys.stderr)
        raise SystemExit(2)
