#!/usr/bin/env python3
"""Append-only launcher for one future R23 seam/topology diagnostic.

Dry-run is the default. Blender can start only with --execute-diagnostic.
The diagnostic must stop before donor removal, freeze, or save and is accepted
by this controller only when its evidence proves that intentional stop.
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
    "kira_r23_cc0_afes_seam_topology_diagnostic_preparation/"
    "INVOCATION_CONFIG.json"
)


class DiagnosticInvocationError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def project_path(raw: str | Path) -> Path:
    value = Path(str(raw))
    if value.is_absolute() or ".." in value.parts:
        raise DiagnosticInvocationError(f"unsafe project-relative path: {raw}")
    resolved = (ROOT / value).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise DiagnosticInvocationError(f"path escaped project: {raw}") from exc
    return resolved


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
        raise DiagnosticInvocationError(f"missing {label}: {relative(path)}")
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != int(binding["bytes"]) or digest != str(binding["sha256"]):
        raise DiagnosticInvocationError(
            f"sealed {label} drifted: bytes={size}, sha256={digest}"
        )
    return {"path": relative(path), "bytes": size, "sha256": digest}


def verify_directory_files(
    label: str, record: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    directory = project_path(record["directory"])
    if not directory.is_dir():
        raise DiagnosticInvocationError(f"missing preserved {label}: {relative(directory)}")
    expected_names = set(record["files"])
    actual_names = {path.name for path in directory.iterdir() if path.is_file()}
    configured_exact = set(record.get("exact_file_set", sorted(expected_names)))
    if actual_names != configured_exact or expected_names != configured_exact:
        raise DiagnosticInvocationError(
            f"preserved {label} file set drifted: {sorted(actual_names)}"
        )
    return {
        name: verify_file(directory / name, binding, f"{label}/{name}")
        for name, binding in record["files"].items()
    }


def verify_all(spec: Mapping[str, Any]) -> dict[str, Any]:
    verified: dict[str, Any] = {}
    for label, binding in spec["bound_artifacts"].items():
        verified[label] = verify_file(project_path(binding["path"]), binding, label)
    for label, record in spec["preserved_attempts"].items():
        verified[label] = verify_directory_files(label, record)
    return verified


def validate_relative_config_argument(raw: str) -> str:
    value = Path(raw)
    if value.is_absolute() or ".." in value.parts:
        raise DiagnosticInvocationError(
            f"diagnostic --config must remain project-relative: {raw}"
        )
    resolved = project_path(raw)
    if not resolved.is_file():
        raise DiagnosticInvocationError(f"diagnostic --config is missing: {raw}")
    return value.as_posix()


def build_command(spec: Mapping[str, Any]) -> list[str]:
    contract = spec["command_contract"]
    config_argument = validate_relative_config_argument(contract["config_argument"])
    source = project_path(spec["bound_artifacts"]["r19_source_blend"]["path"])
    wrapper = project_path(
        spec["bound_artifacts"]["diagnostic_blender_wrapper"]["path"]
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
    exit_index = command.index("--python-exit-code")
    python_index = command.index("--python")
    if exit_index >= python_index or command[exit_index + 1] != "7":
        raise DiagnosticInvocationError(
            "--python-exit-code 7 must be parsed before --python"
        )
    if Path(command[command.index("--config") + 1]).is_absolute():
        raise DiagnosticInvocationError(
            "constructed --config unexpectedly became absolute"
        )
    return command


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


def validate_diagnostic_evidence(
    spec: Mapping[str, Any], process_exit_code: int
) -> dict[str, Any]:
    contract = spec["runtime_patch_contract"]
    completion = spec["completion_contract"]
    output = project_path(contract["effective_diagnostic_output"])
    diagnostic_path = output / contract["diagnostic_filename"]
    failure_path = output / contract["failure_filename"]
    candidate_path = output / contract["candidate_filename"]
    build_path = output / "BUILD_EVIDENCE.json"
    if completion["raw_blender_exit_expected_nonzero"] and int(process_exit_code) == 0:
        raise DiagnosticInvocationError(
            "diagnostic unexpectedly returned zero instead of the intentional stop"
        )
    if not diagnostic_path.is_file() or not failure_path.is_file():
        raise DiagnosticInvocationError("required diagnostic/failure evidence is absent")
    if candidate_path.exists() or build_path.exists():
        raise DiagnosticInvocationError("diagnostic improperly created candidate/build evidence")
    diagnostic = read_json(diagnostic_path)
    failure = read_json(failure_path)
    required = set(spec["diagnostic_contract"]["required_top_level_sections"])
    if not required.issubset(diagnostic):
        raise DiagnosticInvocationError(
            f"diagnostic sections missing: {sorted(required.difference(diagnostic))}"
        )
    stop_error = contract["intentional_stop_error"]
    if failure.get("error") != stop_error:
        raise DiagnosticInvocationError("failure evidence is not the deliberate stop")
    proof = diagnostic["source_and_stop_proof"]
    if not proof.get("source_unchanged"):
        raise DiagnosticInvocationError("diagnostic does not prove source stayed exact")
    if proof.get("candidate_exists_before_intentional_stop"):
        raise DiagnosticInvocationError("candidate existed before intentional stop")
    forbidden_true = [
        "save_called",
        "render_called",
        "export_called",
        "runtime_changed",
        "freeze_after_author_called",
    ]
    if any(proof.get(key) for key in forbidden_true):
        raise DiagnosticInvocationError("post-topology forbidden operation was reported")
    if not proof.get("donor_present_before_intentional_stop"):
        raise DiagnosticInvocationError("donor was removed before the diagnostic stop")
    incidence = diagnostic["face_edge_incidence"]
    if int(incidence["edge_count"]) != len(incidence["rows"]):
        raise DiagnosticInvocationError("face-edge incidence inventory is incomplete")
    expected_regions = dict(
        spec["diagnostic_contract"]["required_patch_face_region_counts"]
    )
    expected_regions.pop("total")
    if diagnostic["patch"]["face_region_counts"] != expected_regions:
        raise DiagnosticInvocationError("patch region inventory drifted")
    source_binding = spec["bound_artifacts"]["r19_source_blend"]
    source = project_path(source_binding["path"])
    if sha256_file(source) != source_binding["sha256"]:
        raise DiagnosticInvocationError("R19 source changed during diagnostic")
    verify_all(spec)
    return {
        "diagnostic": {
            "path": relative(diagnostic_path),
            "bytes": diagnostic_path.stat().st_size,
            "sha256": sha256_file(diagnostic_path),
        },
        "failure": {
            "path": relative(failure_path),
            "bytes": failure_path.stat().st_size,
            "sha256": sha256_file(failure_path),
        },
        "candidate_exists": False,
        "build_evidence_exists": False,
        "source_unchanged": True,
        "preserved_attempts_unchanged": True,
    }


def execute_once(spec_path: Path, spec: Mapping[str, Any]) -> int:
    verified = verify_all(spec)
    command = build_command(spec)
    if blender_process_count() != 0:
        raise DiagnosticInvocationError("Blender is already active")
    output = project_path(spec["runtime_patch_contract"]["effective_diagnostic_output"])
    run = project_path(spec["future_execution"]["directory"])
    if output.exists():
        raise DiagnosticInvocationError(
            f"append-only diagnostic output already exists: {relative(output)}"
        )
    if run.exists():
        raise DiagnosticInvocationError(
            f"append-only diagnostic execution already exists: {relative(run)}"
        )
    run.mkdir(parents=True, exist_ok=False)
    pre_path = run / spec["future_execution"]["pre_run"]
    stdout_path = run / spec["future_execution"]["stdout"]
    stderr_path = run / spec["future_execution"]["stderr"]
    post_path = run / spec["future_execution"]["post_run"]
    write_json_exclusive(
        pre_path,
        {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_SEAM_TOPOLOGY_DIAGNOSTIC_PRE_RUN",
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
            "diagnostic_output_existed_before": False,
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
    evidence = validate_diagnostic_evidence(spec, int(result.returncode))
    write_json_exclusive(
        post_path,
        {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_SEAM_TOPOLOGY_DIAGNOSTIC_POST_RUN",
            "started_utc": started,
            "ended_utc": ended,
            "raw_process_exit_code": int(result.returncode),
            "effective_controller_exit_code": 0,
            "intentional_stop_validated": True,
            "stdout": {
                "path": relative(stdout_path),
                "bytes": stdout_path.stat().st_size,
                "sha256": sha256_file(stdout_path),
            },
            "stderr": {
                "path": relative(stderr_path),
                "bytes": stderr_path.stat().st_size,
                "sha256": sha256_file(stderr_path),
            },
            "evidence": evidence,
            "blender_process_count_after": blender_process_count(),
        },
    )
    return 0


def arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", default=DEFAULT_SPEC.as_posix())
    parser.add_argument("--execute-diagnostic", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = arguments(argv)
    spec_path = project_path(args.spec)
    spec = read_json(spec_path)
    if spec.get("schema") != "kira.avatar.r23_seam_topology_diagnostic_invocation.v1":
        raise DiagnosticInvocationError("wrong diagnostic invocation schema")
    verified = verify_all(spec)
    command = build_command(spec)
    if not args.execute_diagnostic:
        output = project_path(
            spec["runtime_patch_contract"]["effective_diagnostic_output"]
        )
        run = project_path(spec["future_execution"]["directory"])
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
                    "diagnostic_output_fresh": not output.exists(),
                    "execution_output_fresh": not run.exists(),
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
    except DiagnosticInvocationError as exc:
        print(f"R23 diagnostic invocation refused: {exc}", file=sys.stderr)
        raise SystemExit(2)
