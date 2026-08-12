#!/usr/bin/env python3
"""Execution-disabled CPU controller for one Kira R24 author transaction.

The controller is intentionally inert.  The independent R4 audit found that
R4 is not an execution authority, so all author/evaluator dependency digests
remain symbolic and ``EXECUTION_AUTHORITY_STATE`` is not granted.  A future
post-R4 gate may be sealed into these bindings after independent review.

The eventual transaction is deliberately one-shot:

* verify the complete exact 49-entry R19 Attempt 06 manifest and its closed
  on-disk directory;
* verify every exact executable dependency and prove no Blender process is
  already running;
* reserve one append-only attempt root and an external extraction root;
* start one author Blender in a kill-on-close Windows Job, attest its PID/job
  assignment to the waiting worker, require a clean exit, close the job, and
  only then hash the saved candidate;
* start one distinct read-only fresh-reopen Blender with identical safety
  flags, also Job-owned, and do not retry either process;
* derive the controller result from artifacts after both children have exited.

Importing or running this file without a later reseal cannot start Blender.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import time
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
R19_ATTEMPT_RELATIVE = PurePosixPath(
    "RecoverySprint/continuation_20260802/"
    "kira_r19_bald_targeted_correction/attempt_06"
)
R19_MANIFEST_RELATIVE = R19_ATTEMPT_RELATIVE / "PACKAGE_MANIFEST.json"
R19_MANIFEST_BYTES = 13_209
R19_MANIFEST_SHA256 = "9c7038b60e2c712e49e810c0b7f7932bf36a18042dd00a6951834be59bb40f0c"
R19_SOURCE_RELATIVE = R19_ATTEMPT_RELATIVE / "kira_r19_bald_targeted_material_movement_correction.blend"
R19_SOURCE_BYTES = 90_861_425
R19_SOURCE_SHA256 = "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f"
RUNTIME_ROOT_RELATIVE = PurePosixPath(
    "RecoverySprint/continuation_20260808/"
    "kira_r24_one_shot_runtime_attempts"
)
ATTEMPT_NAME = "attempt_01"
CANDIDATE_BASENAME = "kira_r24_one_shot_private_candidate.blend"
FRESH_REOPEN_DIRECTORY = "fresh_reopen"
FRESH_REOPEN_BASENAME = "candidate_extraction.json"
RESULT_BASENAME = "ONE_SHOT_TRANSACTION_RESULT.json"
FAILURE_BASENAME = "ONE_SHOT_TRANSACTION_FAILURE.json"
JOB_GATE_BASENAME = "AUTHOR_PARENT_JOB_GATE.json"

BLENDER_BINDING: dict[str, object] = {
    "path": "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe",
    "bytes": 108_687_824,
    "sha256": "1e6624af112b3c936f4b038b025ebd2bf00ae72c4b62881a6787166d71c58fa5",
}

# R4 is independently rejected as execution authority.  These symbolic paths
# describe the dependency roles but cannot pass verify_dependencies until a
# later accepted gate and author operation are separately sealed.
DEPENDENCY_BINDINGS: dict[str, dict[str, object]] = {
    "author_worker": {
        "path": "tools/blender_author_kira_r24_one_shot_candidate.py",
        "bytes": None,
        "sha256": None,
    },
    "external_surface_author_operation": {
        "path": "tools/blender_author_kira_r24_r5_external_surface_operation.py",
        "bytes": None,
        "sha256": None,
    },
    "accepted_artifact_gate": {
        "path": "tools/kira_r24_artifact_derived_gate_r5.py",
        "bytes": None,
        "sha256": None,
    },
    "read_only_extractor": {
        "path": "tools/blender_extract_kira_r24_candidate_read_only_r5.py",
        "bytes": None,
        "sha256": None,
    },
    "intersection_helper": {
        "path": "tools/blender_exact_mesh_intersections.py",
        "bytes": None,
        "sha256": None,
    },
    "accepted_gate_contract": {
        "path": (
            "RecoverySprint/continuation_20260808/"
            "kira_r24_artifact_derived_gate_r5/"
            "KIRA_R24_ARTIFACT_DERIVED_GATE_R5_CONTRACT.json"
        ),
        "bytes": None,
        "sha256": None,
    },
}
EXECUTION_AUTHORITY_STATE = (
    "NOT_GRANTED_R4_REJECTED_POST_R4_GATE_AND_AUTHOR_OPERATION_RESEAL_REQUIRED"
)
REQUIRED_EXECUTION_AUTHORITY_STATE = "GRANTED_FOR_EXACT_ONE_SHOT_TRANSACTION"
SAFETY_FLAGS = [
    "--background",
    "--factory-startup",
    "--disable-autoexec",
    "--python-exit-code",
    "1",
]


class R24OneShotControllerError(RuntimeError):
    """Fail-closed transaction-controller error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _exclusive_json(path: Path, value: object) -> None:
    encoded = canonical_bytes(value)
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())


def _exclusive_bytes(path: Path, value: bytes) -> None:
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())


def _project_path(raw: object, *, require_file: bool = False) -> Path:
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute():
        raise R24OneShotControllerError("project path must be nonempty and relative")
    pure = PurePosixPath(raw.replace("\\", "/"))
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise R24OneShotControllerError("project path has an unsafe component")
    path = ROOT.joinpath(*pure.parts)
    try:
        path.resolve(strict=require_file).relative_to(ROOT.resolve())
    except (OSError, ValueError) as exc:
        raise R24OneShotControllerError("project path escaped the repository") from exc
    if require_file and (not path.is_file() or path.is_symlink()):
        raise R24OneShotControllerError(f"bound regular file is absent: {raw}")
    return path


def _sealed_record(binding: Mapping[str, object], label: str, *, absolute: bool = False) -> dict[str, object]:
    if set(binding) != {"path", "bytes", "sha256"}:
        raise R24OneShotControllerError(f"{label} binding field inventory changed")
    size = binding.get("bytes")
    digest = binding.get("sha256")
    if not isinstance(size, int) or isinstance(size, bool) or size < 1:
        raise R24OneShotControllerError(f"{label} byte binding is not sealed")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise R24OneShotControllerError(f"{label} digest binding is not sealed")
    raw = binding.get("path")
    if absolute:
        if not isinstance(raw, str) or not Path(raw).is_absolute():
            raise R24OneShotControllerError(f"{label} absolute path is invalid")
        path = Path(raw).resolve()
        if not path.is_file() or path.is_symlink():
            raise R24OneShotControllerError(f"{label} exact file is absent")
    else:
        path = _project_path(raw, require_file=True)
    if path.stat().st_size != size or sha256_file(path) != digest:
        raise R24OneShotControllerError(f"{label} exact identity changed")
    return {"path": str(path), "bytes": size, "sha256": digest}


def verify_r19_package() -> dict[str, object]:
    manifest_path = _project_path(R19_MANIFEST_RELATIVE.as_posix(), require_file=True)
    if manifest_path.stat().st_size != R19_MANIFEST_BYTES or sha256_file(manifest_path) != R19_MANIFEST_SHA256:
        raise R24OneShotControllerError("R19 Attempt 06 manifest identity changed")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise R24OneShotControllerError("R19 Attempt 06 manifest is invalid") from exc
    if not isinstance(manifest, dict) or set(manifest) != {
        "append_only_attempt", "created_utc", "files_excluding_this_manifest", "schema_version"
    }:
        raise R24OneShotControllerError("R19 manifest top-level fields changed")
    rows = manifest.get("files_excluding_this_manifest")
    if manifest.get("schema_version") != 1 or manifest.get("append_only_attempt") != "attempt_06":
        raise R24OneShotControllerError("R19 manifest schema or attempt changed")
    if not isinstance(rows, list) or len(rows) != 49:
        raise R24OneShotControllerError("R19 manifest does not contain exact 49-file closure")
    attempt_root = _project_path(R19_ATTEMPT_RELATIVE.as_posix())
    expected: set[Path] = {manifest_path.resolve()}
    verified: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "size_bytes"}:
            raise R24OneShotControllerError(f"R19 manifest row {index} fields changed")
        record = _sealed_record(
            {"path": row["path"], "bytes": row["size_bytes"], "sha256": row["sha256"]},
            f"R19 manifest row {index}",
        )
        path = Path(str(record["path"])).resolve()
        try:
            path.relative_to(attempt_root.resolve())
        except ValueError as exc:
            raise R24OneShotControllerError("R19 manifest row escaped Attempt 06") from exc
        if path in expected:
            raise R24OneShotControllerError("R19 manifest contains a duplicate path")
        expected.add(path)
        verified.append(record)
    actual = {path.resolve() for path in attempt_root.rglob("*") if path.is_file()}
    if actual != expected:
        raise R24OneShotControllerError("R19 Attempt 06 on-disk file closure changed")
    source = _project_path(R19_SOURCE_RELATIVE.as_posix(), require_file=True)
    if source.stat().st_size != R19_SOURCE_BYTES or sha256_file(source) != R19_SOURCE_SHA256:
        raise R24OneShotControllerError("R19 exact source Blend identity changed")
    return {
        "manifest": {"path": str(manifest_path), "bytes": R19_MANIFEST_BYTES, "sha256": R19_MANIFEST_SHA256},
        "verified_file_count_excluding_manifest": len(verified),
        "closed_directory_file_count_including_manifest": len(actual),
        "source": {"path": str(source), "bytes": R19_SOURCE_BYTES, "sha256": R19_SOURCE_SHA256},
    }


def verify_dependencies() -> dict[str, dict[str, object]]:
    verified = {"blender": _sealed_record(BLENDER_BINDING, "Blender", absolute=True)}
    for label, binding in DEPENDENCY_BINDINGS.items():
        verified[label] = _sealed_record(binding, label)
    return verified


def _require_execution_authority() -> None:
    if EXECUTION_AUTHORITY_STATE != REQUIRED_EXECUTION_AUTHORITY_STATE:
        raise R24OneShotControllerError(
            "one-shot R24 transaction is inert; post-R4 execution authority is absent"
        )


def ensure_no_blender_process(
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> dict[str, object]:
    if os.name != "nt":
        raise R24OneShotControllerError("the sealed Blender transaction is Windows-only")
    completed = runner(
        ["tasklist.exe", "/FO", "CSV", "/NH"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        shell=False,
        timeout=20,
    )
    if completed.returncode != 0:
        raise R24OneShotControllerError("one bounded tasklist inventory failed")
    try:
        rows = list(csv.reader(io.StringIO(completed.stdout.decode("utf-8", errors="strict"))))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise R24OneShotControllerError("tasklist output is not parseable") from exc
    blender_rows = [row for row in rows if row and row[0].lower() in {"blender.exe", "blender-launcher.exe"}]
    if blender_rows:
        raise R24OneShotControllerError("a Blender process is already active")
    return {"inventory_command": "tasklist.exe /FO CSV /NH", "blender_process_count": 0}


def _safe_create_directory(path: Path) -> None:
    try:
        relative = path.resolve(strict=False).relative_to(ROOT.resolve())
    except ValueError as exc:
        raise R24OneShotControllerError("output directory escaped repository") from exc
    cursor = ROOT
    for part in relative.parts:
        cursor = cursor / part
        if os.path.lexists(cursor):
            if cursor.is_symlink() or not cursor.is_dir():
                raise R24OneShotControllerError(f"unsafe output directory component: {cursor}")
        else:
            cursor.mkdir(exist_ok=False)


def reserve_attempt() -> dict[str, Path]:
    runtime_root = _project_path(RUNTIME_ROOT_RELATIVE.as_posix())
    _safe_create_directory(runtime_root)
    attempt = runtime_root / ATTEMPT_NAME
    if os.path.lexists(attempt):
        raise R24OneShotControllerError("append-only attempt_01 is already reserved")
    attempt.mkdir(exist_ok=False)
    extraction = attempt / FRESH_REOPEN_DIRECTORY
    extraction.mkdir(exist_ok=False)
    return {
        "attempt": attempt,
        "candidate": attempt / CANDIDATE_BASENAME,
        "extraction_directory": extraction,
        "extraction": extraction / FRESH_REOPEN_BASENAME,
        "job_gate": attempt / JOB_GATE_BASENAME,
        "result": attempt / RESULT_BASENAME,
        "failure": attempt / FAILURE_BASENAME,
    }


def child_environment(nonce: str) -> dict[str, str]:
    allowed = (
        "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERNAME", "USERPROFILE",
        "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA", "APPDATA", "PATH",
    )
    environment = {name: os.environ[name] for name in allowed if os.environ.get(name)}
    environment.update(
        {
            "PYTHONNOUSERSITE": "1",
            "KIRA_R24_ONE_SHOT_CONTROLLER_NONCE": nonce,
        }
    )
    return environment


class WindowsOwnedProcessJob:
    """One kill-on-close Windows Job for an exact Blender child tree."""

    def __init__(self) -> None:
        self._handle: Any = None
        self.assignment: dict[str, object] = {"assigned": False}

    def assign(self, child: subprocess.Popen[bytes]) -> dict[str, object]:
        if os.name != "nt":
            raise R24OneShotControllerError("Windows Job ownership is mandatory")
        import ctypes
        from ctypes import wintypes

        class BASIC(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
            )]

        class EXTENDED(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BASIC), ("IoInfo", IO),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            raise R24OneShotControllerError("CreateJobObjectW failed")
        self._handle = handle
        info = EXTENDED()
        info.BasicLimitInformation.LimitFlags = 0x00002000
        if not kernel32.SetInformationJobObject(handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            self.close()
            raise R24OneShotControllerError("SetInformationJobObject failed")
        if not kernel32.AssignProcessToJobObject(handle, wintypes.HANDLE(int(getattr(child, "_handle")))):
            self.close()
            raise R24OneShotControllerError("AssignProcessToJobObject failed")
        self.assignment = {
            "assigned": True,
            "kill_on_job_close": True,
            "child_pid": int(child.pid),
        }
        return dict(self.assignment)

    def terminate(self, code: int = 124) -> None:
        if self._handle is None:
            return
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.TerminateJobObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        kernel32.TerminateJobObject.restype = ctypes.c_int
        kernel32.TerminateJobObject(self._handle, code)

    def close(self) -> dict[str, object]:
        if self._handle is None:
            return {"closed": True, "already_closed": True}
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_int
        completed = bool(kernel32.CloseHandle(self._handle))
        self._handle = None
        if not completed:
            raise R24OneShotControllerError("CloseHandle for owned Job failed")
        return {"closed": True, "kill_on_job_close_applied": bool(self.assignment.get("assigned"))}


def run_owned_child(
    command: Sequence[str],
    environment: Mapping[str, str],
    *,
    timeout_seconds: int,
    author_job_gate: Path | None = None,
    nonce: str | None = None,
) -> dict[str, object]:
    child = subprocess.Popen(
        list(command),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        env=dict(environment),
    )
    job = WindowsOwnedProcessJob()
    try:
        assignment = job.assign(child)
        if author_job_gate is not None:
            if nonce is None:
                raise R24OneShotControllerError("author gate nonce is absent")
            _exclusive_json(
                author_job_gate,
                {
                    "schema": "kira.avatar.r24.author_parent_job_gate.v1",
                    "nonce": nonce,
                    "parent_pid": os.getpid(),
                    "child_pid": child.pid,
                    "assigned": True,
                    "kill_on_job_close": True,
                },
            )
        try:
            stdout, stderr = child.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            job.terminate()
            child.communicate(timeout=30)
            raise R24OneShotControllerError("bounded Blender child timed out") from exc
        direct_exit_observed = child.poll() is not None
        returncode = int(child.returncode) if child.returncode is not None else None
        close = job.close()
        if not direct_exit_observed:
            raise R24OneShotControllerError("direct Blender child exit was not observed")
        return {
            "pid": int(child.pid),
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
            "direct_exit_observed": True,
            "job_assignment": assignment,
            "job_close": close,
        }
    except BaseException:
        job.terminate()
        job.close()
        raise


def author_command(paths: Mapping[str, Path], dependencies: Mapping[str, Mapping[str, object]], nonce: str) -> list[str]:
    command = [str(dependencies["blender"]["path"]), *SAFETY_FLAGS, "--python", str(dependencies["author_worker"]["path"]), "--"]
    command.extend(
        [
            "--source", str(_project_path(R19_SOURCE_RELATIVE.as_posix(), require_file=True)),
            "--output", str(paths["candidate"]),
            "--controller-nonce", nonce,
            "--job-gate", str(paths["job_gate"]),
            "--execute-authoring",
        ]
    )
    return command


def extractor_command(
    paths: Mapping[str, Path],
    dependencies: Mapping[str, Mapping[str, object]],
    candidate_sha256: str,
    nonce: str,
) -> list[str]:
    return [
        str(dependencies["blender"]["path"]),
        *SAFETY_FLAGS,
        str(paths["candidate"]),
        "--python", str(dependencies["read_only_extractor"]["path"]),
        "--",
        "--candidate", str(paths["candidate"]),
        "--candidate-sha256", candidate_sha256,
        "--extractor-sha256", str(dependencies["read_only_extractor"]["sha256"]),
        "--intersection-helper-sha256", str(dependencies["intersection_helper"]["sha256"]),
        "--nonce", nonce,
        "--output", str(paths["extraction"]),
    ]


def _load_exact_gate(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("_kira_r24_accepted_artifact_gate", path)
    if spec is None or spec.loader is None:
        raise R24OneShotControllerError("accepted artifact gate cannot be imported")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "validate_extraction_envelope", None)):
        raise R24OneShotControllerError("accepted artifact gate envelope validator is absent")
    return module


def execute_transaction(
    *,
    dependency_verifier: Callable[[], dict[str, dict[str, object]]] = verify_dependencies,
    package_verifier: Callable[[], dict[str, object]] = verify_r19_package,
    process_guard: Callable[[], dict[str, object]] = ensure_no_blender_process,
    reserver: Callable[[], dict[str, Path]] = reserve_attempt,
    child_runner: Callable[..., dict[str, object]] = run_owned_child,
) -> dict[str, object]:
    _require_execution_authority()
    package = package_verifier()
    dependencies = dependency_verifier()
    process_inventory = process_guard()
    paths = reserver()
    nonce = hashlib.sha256(os.urandom(64)).hexdigest()
    environment = child_environment(nonce)
    source = _project_path(R19_SOURCE_RELATIVE.as_posix(), require_file=True)
    source_before = sha256_file(source)
    author = child_runner(
        author_command(paths, dependencies, nonce),
        environment,
        timeout_seconds=1800,
        author_job_gate=paths["job_gate"],
        nonce=nonce,
    )
    _exclusive_bytes(paths["attempt"] / "author.stdout.log", bytes(author["stdout"]))
    _exclusive_bytes(paths["attempt"] / "author.stderr.log", bytes(author["stderr"]))
    if author.get("returncode") != 0 or author.get("direct_exit_observed") is not True:
        raise R24OneShotControllerError("the exact author child failed or did not exit cleanly")
    if sha256_file(source) != source_before:
        raise R24OneShotControllerError("preserved R19 source changed during author child")
    candidate = paths["candidate"]
    if not candidate.is_file() or candidate.is_symlink():
        raise R24OneShotControllerError("author child did not produce one regular candidate")
    # This digest is deliberately taken only after direct author exit and Job
    # closure.  The future artifact gate must bind this post-exit identity.
    candidate_after_author_exit = sha256_file(candidate)
    candidate_bytes = candidate.stat().st_size
    extractor = child_runner(
        extractor_command(paths, dependencies, candidate_after_author_exit, nonce),
        environment,
        timeout_seconds=1800,
    )
    _exclusive_bytes(paths["extraction_directory"] / "extractor.stdout.log", bytes(extractor["stdout"]))
    _exclusive_bytes(paths["extraction_directory"] / "extractor.stderr.log", bytes(extractor["stderr"]))
    if extractor.get("returncode") != 0 or extractor.get("direct_exit_observed") is not True:
        raise R24OneShotControllerError("the exact fresh-reopen child failed or did not exit cleanly")
    if sha256_file(candidate) != candidate_after_author_exit:
        raise R24OneShotControllerError("candidate changed during fresh reopen")
    if sha256_file(source) != source_before:
        raise R24OneShotControllerError("preserved R19 source changed during fresh reopen")
    if not paths["extraction"].is_file() or paths["extraction"].stat().st_size > 512 * 1024 * 1024:
        raise R24OneShotControllerError("fresh-reopen extraction is absent or oversized")
    snapshot = json.loads(paths["extraction"].read_text(encoding="utf-8"))
    gate = _load_exact_gate(Path(str(dependencies["accepted_artifact_gate"]["path"])))
    failures = gate.validate_extraction_envelope(
        snapshot,
        nonce=nonce,
        candidate=candidate,
        candidate_sha256=candidate_after_author_exit,
        extractor_sha256=str(dependencies["read_only_extractor"]["sha256"]),
        intersection_helper_sha256=str(dependencies["intersection_helper"]["sha256"]),
    )
    if failures:
        raise R24OneShotControllerError("fresh-reopen envelope rejected: " + ",".join(sorted(failures)))
    result = {
        "schema": "kira.avatar.r24.one_shot_author_transaction.v1",
        "status": "FRESH_REOPEN_CAPTURED_ARTIFACT_GATE_EVALUATION_STILL_REQUIRED_NOT_ACCEPTED",
        "r19_package": package,
        "process_inventory": process_inventory,
        "attempt": str(paths["attempt"]),
        "author": {
            "pid": author["pid"],
            "returncode": author["returncode"],
            "direct_exit_observed": author["direct_exit_observed"],
            "job_assignment": author["job_assignment"],
            "job_close": author["job_close"],
        },
        "candidate_post_author_exit": {
            "path": str(candidate),
            "bytes": candidate_bytes,
            "sha256": candidate_after_author_exit,
        },
        "fresh_reopen": {
            "pid": extractor["pid"],
            "returncode": extractor["returncode"],
            "direct_exit_observed": extractor["direct_exit_observed"],
            "job_assignment": extractor["job_assignment"],
            "job_close": extractor["job_close"],
            "extraction_path": str(paths["extraction"]),
            "extraction_sha256": sha256_file(paths["extraction"]),
        },
        "author_blender_invocation_count": 1,
        "fresh_reopen_blender_invocation_count": 1,
        "retry_count": 0,
        "candidate_accepted": False,
        "candidate_private_inactive_unassigned_unpublished": True,
        "candidate_runtime_eligible": False,
    }
    _exclusive_json(paths["result"], result)
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-once", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.execute_once:
        raise R24OneShotControllerError("--execute-once is required but not sufficient")
    result = execute_transaction()
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
