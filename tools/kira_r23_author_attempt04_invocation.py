#!/usr/bin/env python3
"""Dry-default controller for one future bounded R23 Author Attempt 04.

Preparation and dry validation never start Blender. A future operator must use
the exact ``--execute-attempt04`` flag after independent review.
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

from tools import kira_r23_author_attempt02_invocation as base  # noqa: E402


DEFAULT_SPEC = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt04_preparation/"
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT04_REPAIR_CONFIG.json"
)


class Attempt04InvocationError(RuntimeError):
    pass


def verify_file(path: Path, binding: Mapping[str, Any], label: str) -> dict[str, Any]:
    try:
        return base.verify_file(path, binding, label)
    except base.Attempt02InvocationError as exc:
        raise Attempt04InvocationError(str(exc)) from exc


def verify_all(spec: Mapping[str, Any]) -> dict[str, Any]:
    verified: dict[str, Any] = {}
    for label, binding in spec["bound_artifacts"].items():
        verified[label] = verify_file(base.project_path(binding["path"]), binding, label)
    for section in spec["preserved_append_only_evidence"]:
        root = base.project_path(section["directory"])
        if not root.is_dir():
            raise Attempt04InvocationError(
                f"missing preserved directory {section['label']}"
            )
        actual_names = sorted(path.name for path in root.iterdir() if path.is_file())
        expected_names = sorted(section["files"])
        if actual_names != expected_names:
            raise Attempt04InvocationError(
                f"preserved directory drifted for {section['label']}: {actual_names}"
            )
        for name, binding in section["files"].items():
            verified[f"{section['label']}/{name}"] = verify_file(
                root / name, binding, f"{section['label']}/{name}"
            )
    return verified


def output_contract(spec: Mapping[str, Any]) -> dict[str, Any]:
    repair = spec["repair_contract"]
    configured = base.project_path(repair["configured_output_required"])
    effective = base.project_path(repair["effective_output"])
    future_execution = base.project_path(spec["future_execution"]["directory"])
    sealed_config = base.read_json(
        base.project_path(spec["bound_artifacts"]["sealed_author_config"]["path"])
    )
    if sealed_config["output"]["directory"] != repair["configured_output_required"]:
        raise Attempt04InvocationError("sealed configured author output drifted")
    if not configured.is_dir():
        raise Attempt04InvocationError("preserved configured author output is absent")
    if configured == effective:
        raise Attempt04InvocationError("Attempt04 author output is not isolated")
    if effective.exists():
        raise Attempt04InvocationError(
            f"append-only Attempt04 author output exists: {base.relative(effective)}"
        )
    if future_execution.exists():
        raise Attempt04InvocationError(
            "append-only Attempt04 execution directory already exists"
        )
    return {
        "configured": configured,
        "configured_relative": repair["configured_output_required"],
        "effective": effective,
        "effective_relative": repair["effective_output"],
        "future_execution": future_execution,
        "future_execution_relative": spec["future_execution"]["directory"],
    }


def build_command(spec: Mapping[str, Any]) -> list[str]:
    contract = spec["command_contract"]
    try:
        config_argument = base.validate_relative_config_argument(
            contract["sealed_author_config_argument"]
        )
    except base.Attempt02InvocationError as exc:
        raise Attempt04InvocationError(str(exc)) from exc
    source = base.project_path(spec["bound_artifacts"]["r19_source_blend"]["path"])
    wrapper = base.project_path(
        spec["bound_artifacts"]["blender_attempt04_wrapper"]["path"]
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
        raise Attempt04InvocationError(
            "--python-exit-code must be parsed before --python"
        )
    if command[command.index("--python-exit-code") + 1] != "7":
        raise Attempt04InvocationError("Attempt04 Python exit code drifted")
    if Path(command[command.index("--config") + 1]).is_absolute():
        raise Attempt04InvocationError("Attempt04 config argument became absolute")
    return command


def execute_once(spec_path: Path, spec: Mapping[str, Any]) -> int:
    verified = verify_all(spec)
    outputs = output_contract(spec)
    command = build_command(spec)
    if base.blender_process_count() != 0:
        raise Attempt04InvocationError("Blender is already active")
    run = outputs["future_execution"]
    run.mkdir(parents=True, exist_ok=False)
    pre_run = run / spec["future_execution"]["pre_run"]
    stdout_path = run / spec["future_execution"]["stdout"]
    stderr_path = run / spec["future_execution"]["stderr"]
    post_run = run / spec["future_execution"]["post_run"]
    base.write_json_exclusive(
        pre_run,
        {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT04_PRE_RUN",
            "created_utc": base.utc_now(),
            "repair_config": {
                "path": base.relative(spec_path),
                "bytes": spec_path.stat().st_size,
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
            "configured_output_preserved": outputs["configured_relative"],
            "effective_output_absent": outputs["effective_relative"],
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
    success = spec["success_contract"]
    build = output / success["build_evidence"]
    failure = output / success["failure_evidence"]
    candidate = output / success["candidate"]
    effective_exit = base.classified_exit_code(
        result.returncode,
        stderr_text,
        build.is_file(),
        failure.is_file(),
        candidate.is_file(),
        int(spec["command_contract"]["python_exit_code"]),
    )
    base.write_json_exclusive(
        post_run,
        {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT04_POST_RUN",
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
    parser.add_argument("--execute-attempt04", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = arguments(argv)
    spec_path = base.project_path(args.spec)
    spec = base.read_json(spec_path)
    if spec.get("schema") != "kira.avatar.r23_author_attempt04_repair.v1":
        raise Attempt04InvocationError("wrong Attempt04 invocation schema")
    verified = verify_all(spec)
    outputs = output_contract(spec)
    command = build_command(spec)
    blender_count = base.blender_process_count()
    if not args.execute_attempt04:
        print(
            json.dumps(
                {
                    "status": "DRY_ATTEMPT04_REPAIR_ONLY_BLENDER_NOT_RUN",
                    "repair_config": {
                        "path": base.relative(spec_path),
                        "bytes": spec_path.stat().st_size,
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
                    "configured_output_preserved": outputs["configured_relative"],
                    "effective_output": outputs["effective_relative"],
                    "effective_output_exists": False,
                    "future_execution": outputs["future_execution_relative"],
                    "future_execution_exists": False,
                    "blender_process_count_observed": blender_count,
                    "blender_started": False,
                },
                indent=2,
            )
        )
        return 0
    return execute_once(spec_path, spec)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Attempt04InvocationError, base.Attempt02InvocationError) as exc:
        print(f"Attempt04 invocation refused: {exc}", file=sys.stderr)
        raise SystemExit(2)
