#!/usr/bin/env python3
"""Invocation-only correction for one future R23 author Attempt 02.

Dry-run is the default. Blender can start only with --execute-attempt02.
The sealed author config, worker, and core are inputs and are never edited.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt02_invocation_preparation/"
    "INVOCATION_CONFIG.json"
)


class Attempt02InvocationError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def project_path(raw: str | Path) -> Path:
    value = Path(str(raw))
    if value.is_absolute() or ".." in value.parts:
        raise Attempt02InvocationError(f"unsafe project-relative path: {raw}")
    path = (ROOT / value).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise Attempt02InvocationError(f"path escaped project: {raw}") from exc
    return path


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def verify_file(path: Path, binding: Mapping[str, Any], label: str) -> dict[str, Any]:
    if not path.is_file():
        raise Attempt02InvocationError(f"missing {label}: {path}")
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != int(binding["bytes"]) or digest != str(binding["sha256"]):
        raise Attempt02InvocationError(
            f"sealed {label} drifted: bytes={size}, sha256={digest}"
        )
    return {"path": relative(path), "bytes": size, "sha256": digest}


def verify_all(spec: Mapping[str, Any]) -> dict[str, Any]:
    verified: dict[str, Any] = {}
    for label, binding in spec["bound_artifacts"].items():
        verified[label] = verify_file(project_path(binding["path"]), binding, label)
    failure_root = project_path(spec["preserved_attempt01_failure"]["directory"])
    for name, binding in spec["preserved_attempt01_failure"]["files"].items():
        verified[f"attempt01_failure/{name}"] = verify_file(
            failure_root / name, binding, f"Attempt01 failure {name}"
        )
    return verified


def validate_relative_config_argument(raw: str) -> str:
    value = Path(raw)
    if value.is_absolute() or ".." in value.parts:
        raise Attempt02InvocationError(
            f"Attempt02 --config must remain project-relative: {raw}"
        )
    resolved = project_path(raw)
    if not resolved.is_file():
        raise Attempt02InvocationError(f"Attempt02 --config is missing: {raw}")
    return value.as_posix()


def build_command(spec: Mapping[str, Any]) -> list[str]:
    contract = spec["command_contract"]
    config_argument = validate_relative_config_argument(contract["config_argument"])
    source = project_path(spec["bound_artifacts"]["r19_source_blend"]["path"])
    worker = project_path(spec["bound_artifacts"]["sealed_author_worker"]["path"])
    command = [
        str(Path(contract["blender_executable"])),
        "--background",
        "--factory-startup",
        "--disable-autoexec",
        str(source),
        "--python-exit-code",
        str(int(contract["python_exit_code"])),
        "--python",
        str(worker),
        "--",
        "--config",
        config_argument,
        str(contract["worker_flag"]),
    ]
    exit_index = command.index("--python-exit-code")
    python_index = command.index("--python")
    if exit_index >= python_index or command[exit_index + 1] != "7":
        raise Attempt02InvocationError(
            "--python-exit-code 7 must be parsed before --python"
        )
    if Path(command[command.index("--config") + 1]).is_absolute():
        raise Attempt02InvocationError("constructed --config unexpectedly became absolute")
    return command


def classified_exit_code(
    process_exit_code: int,
    stderr_text: str,
    build_evidence_exists: bool,
    failure_evidence_exists: bool,
    candidate_exists: bool,
    fallback_error_code: int = 7,
) -> int:
    """Never treat a zero launcher code as success without author evidence."""

    if int(process_exit_code) != 0:
        return int(process_exit_code)
    if "Traceback (most recent call last):" in stderr_text:
        return int(fallback_error_code)
    if failure_evidence_exists:
        return int(fallback_error_code)
    if not build_evidence_exists or not candidate_exists:
        return int(fallback_error_code)
    return 0


def blender_process_count() -> int:
    if os.name != "nt":
        return 0
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq blender.exe", "/FO", "CSV", "/NH"],
        check=False,
        capture_output=True,
        text=True,
        shell=False,
    )
    return sum(
        1
        for line in result.stdout.splitlines()
        if line.strip().lower().startswith('"blender.exe"')
    )


def execute_once(spec_path: Path, spec: Mapping[str, Any]) -> int:
    verified = verify_all(spec)
    command = build_command(spec)
    if blender_process_count() != 0:
        raise Attempt02InvocationError("Blender is already active")
    output = project_path(spec["configured_author_output_unchanged"]["directory"])
    if output.exists():
        raise Attempt02InvocationError(
            f"append-only configured author output already exists: {relative(output)}"
        )
    run = project_path(spec["future_execution"]["directory"])
    if run.exists():
        raise Attempt02InvocationError(
            f"append-only Attempt02 execution directory already exists: {relative(run)}"
        )
    run.mkdir(parents=True, exist_ok=False)
    pre_run = run / spec["future_execution"]["pre_run"]
    stdout_path = run / spec["future_execution"]["stdout"]
    stderr_path = run / spec["future_execution"]["stderr"]
    post_run = run / spec["future_execution"]["post_run"]
    write_json_exclusive(
        pre_run,
        {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT02_PRE_RUN",
            "created_utc": utc_now(),
            "spec": {
                "path": relative(spec_path),
                "sha256": sha256_file(spec_path),
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
            "blender_process_count_before": 0,
            "author_output_existed_before": False,
        },
    )
    started = utc_now()
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
    ended = utc_now()
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    build = output / spec["success_contract"]["build_evidence"]
    failure = output / spec["success_contract"]["failure_evidence"]
    candidate = output / spec["success_contract"]["candidate"]
    effective_exit = classified_exit_code(
        result.returncode,
        stderr_text,
        build.is_file(),
        failure.is_file(),
        candidate.is_file(),
        int(spec["command_contract"]["python_exit_code"]),
    )
    write_json_exclusive(
        post_run,
        {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_AUTHOR_ATTEMPT02_POST_RUN",
            "started_utc": started,
            "ended_utc": ended,
            "process_exit_code": int(result.returncode),
            "effective_exit_code": int(effective_exit),
            "stdout": {
                "path": relative(stdout_path),
                "bytes": stdout_path.stat().st_size,
                "sha256": sha256_file(stdout_path),
            },
            "stderr": {
                "path": relative(stderr_path),
                "bytes": stderr_path.stat().st_size,
                "sha256": sha256_file(stderr_path),
                "contains_traceback": "Traceback (most recent call last):"
                in stderr_text,
            },
            "author_output": {
                "directory_exists": output.is_dir(),
                "build_evidence_exists": build.is_file(),
                "failure_evidence_exists": failure.is_file(),
                "candidate_exists": candidate.is_file(),
            },
            "blender_process_count_after": blender_process_count(),
        },
    )
    return int(effective_exit)


def arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", default=DEFAULT_SPEC.as_posix())
    parser.add_argument("--execute-attempt02", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = arguments(argv)
    spec_path = project_path(args.spec)
    spec = read_json(spec_path)
    if spec.get("schema") != "kira.avatar.r23_author_attempt02_invocation.v1":
        raise Attempt02InvocationError("wrong Attempt02 invocation schema")
    verified = verify_all(spec)
    command = build_command(spec)
    if not args.execute_attempt02:
        print(
            json.dumps(
                {
                    "status": "DRY_COMMAND_CONSTRUCTION_ONLY_BLENDER_NOT_RUN",
                    "spec": {
                        "path": relative(spec_path),
                        "sha256": sha256_file(spec_path),
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
    except Attempt02InvocationError as exc:
        print(f"Attempt02 invocation refused: {exc}", file=sys.stderr)
        raise SystemExit(2)
