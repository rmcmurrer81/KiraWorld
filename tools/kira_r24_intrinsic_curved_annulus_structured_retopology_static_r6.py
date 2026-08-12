from __future__ import annotations

"""Append-only R24 R6 static gate; no Blender/body authority is granted."""

import contextlib
import copy
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from typing import Iterator, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import kira_r24_blend_sdna_typed_static_r5 as typed
from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static_r4 as r4
from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static_r5 as r5


PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_intrinsic_curved_annulus_structured_retopology_static_r6"
)
DEFAULT_CONTRACT = PACKAGE / "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R6_CONTRACT.json"
EXTRACTOR = ROOT / "tools/blender_extract_kira_r24_candidate_read_only_r6.py"
INTERSECTION_HELPER = ROOT / "tools/blender_exact_mesh_intersections.py"
FRESH_EVALUATOR = ROOT / "tools/kira_r24_r6_fresh_evaluator.py"
SEALED_CONTRACT_FILE_SHA256 = "8b29509644011b1afc88ac69cb6c6a8260d26c88eb632f18b5595cbecd28320f"
SEALED_CONTRACT_SEMANTIC_SHA256 = "273305a151b6f6720b0ee1d9fc35d0388e858633f5f2561511cd15188d03b4c6"


class R6PackageError(ValueError):
    pass


class R6SnapshotError(RuntimeError):
    pass


class R6ProcessProtocolError(RuntimeError):
    pass


def canonical_json(value: object) -> bytes:
    return r4.canonical_json(value)


def canonical_sha256(value: object) -> str:
    return r4.canonical_sha256(value)


def sha256_file(path: Path) -> str:
    return r4.sha256_file(path)


def normalized_worker_sha256(path: Path = Path(__file__)) -> str:
    lines = path.read_bytes().splitlines(keepends=True)
    prefixes = (
        b'SEALED_CONTRACT_FILE_SHA256 = "',
        b'SEALED_CONTRACT_SEMANTIC_SHA256 = "',
    )
    found: set[bytes] = set()
    result: list[bytes] = []
    for line in lines:
        replacement = line
        for prefix in prefixes:
            if line.startswith(prefix):
                suffix = line[len(prefix) + 64 :]
                if not suffix.startswith(b'"'):
                    raise R6PackageError("R6 seal literal shape changed")
                replacement = prefix + b"0" * 64 + suffix
                found.add(prefix)
        result.append(replacement)
    if found != set(prefixes):
        raise R6PackageError("R6 seal field inventory changed")
    return hashlib.sha256(b"".join(result)).hexdigest()


def _semantic_projection(value: Mapping[str, object]) -> dict[str, object]:
    result = copy.deepcopy(dict(value))
    result["semantic_seal_sha256"] = ""
    return result


@lru_cache(maxsize=1)
def load_sealed_contract() -> dict[str, object]:
    try:
        raw = DEFAULT_CONTRACT.read_bytes()
        overlay = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise R6PackageError(f"R6 contract cannot be loaded: {exc}") from exc
    if hashlib.sha256(raw).hexdigest() != SEALED_CONTRACT_FILE_SHA256:
        raise R6PackageError("R6 contract file identity changed")
    semantic = canonical_sha256(_semantic_projection(overlay))
    if semantic != SEALED_CONTRACT_SEMANTIC_SHA256 or overlay.get("semantic_seal_sha256") != semantic:
        raise R6PackageError("R6 contract semantic identity changed")
    if overlay.get("schema") != "kira.avatar.r24.artifact_derived_gate.v6":
        raise R6PackageError("unexpected R6 schema")
    parents = overlay.get("parent_bindings")
    if not isinstance(parents, Mapping) or set(parents) != {"r5_contract", "r5_manifest", "r5_audit"}:
        raise R6PackageError("R6 parent inventory changed")
    for record in parents.values():
        if not isinstance(record, Mapping):
            raise R6PackageError("R6 parent binding malformed")
        r4.validate_exact_file(ROOT, record)
    parent = r5.load_sealed_contract()
    implementation = overlay.get("authorized_implementation")
    expected = {
        "worker", "typed_preflight", "semantic_projection", "read_only_extractor",
        "intersection_helper", "sealed_author_worker", "fresh_evaluator",
        "focused_test", "python_executable", "candidate_path_prefix",
        "required_gate_schema", "candidate_basename",
    }
    if not isinstance(implementation, Mapping) or set(implementation) != expected:
        raise R6PackageError("R6 implementation inventory changed")
    worker = implementation.get("worker")
    if (
        not isinstance(worker, Mapping)
        or worker.get("path") != Path(__file__).resolve().relative_to(ROOT.resolve()).as_posix()
        or worker.get("normalized_semantic_sha256") != normalized_worker_sha256()
    ):
        raise R6PackageError("R6 worker binding changed")
    for name in (
        "typed_preflight", "semantic_projection", "read_only_extractor",
        "intersection_helper", "sealed_author_worker", "fresh_evaluator", "focused_test",
    ):
        record = implementation.get(name)
        if not isinstance(record, Mapping):
            raise R6PackageError(f"R6 binding {name!r} absent")
        r4.validate_exact_file(ROOT, record)
    python_record = implementation.get("python_executable")
    if not isinstance(python_record, Mapping):
        raise R6PackageError("R6 Python binding absent")
    r4.validate_absolute_exact_file(python_record)
    amendments = overlay.get("r6_amendments")
    required_amendments = {
        "immutable_windows_snapshot_lease",
        "sealed_author_command",
        "full_author_process_tree_quiescence",
        "fresh_evaluator_process",
        "replacement_only_world_quality",
        "nla_custom_node_and_slot_semantics",
        "post_audit_package_state",
    }
    if not isinstance(amendments, Mapping) or set(amendments) != required_amendments or not all(amendments.values()):
        raise R6PackageError("R6 amendment inventory changed")
    merged = copy.deepcopy(parent)
    merged.update(
        {
            "schema": overlay["schema"],
            "status": overlay["status"],
            "lane": overlay["lane"],
            "mode": overlay["mode"],
            "authorized_implementation": copy.deepcopy(implementation),
            "r6_amendments": copy.deepcopy(amendments),
            "static_execution_authority": bool(overlay.get("static_execution_authority", False)),
            "semantic_seal_sha256": semantic,
        }
    )
    return merged


@dataclass
class ImmutableSnapshot:
    path: Path
    sha256: str
    bytes: int
    handle: int
    directory: Path

    def close(self) -> None:
        if self.handle:
            ctypes.windll.kernel32.CloseHandle(wintypes.HANDLE(self.handle))
            self.handle = 0
        try:
            self.path.unlink(missing_ok=True)
            self.directory.rmdir()
        except OSError:
            pass


def _win_error(message: str) -> R6SnapshotError:
    return R6SnapshotError(f"{message}: Windows error {ctypes.get_last_error()}")


def _create_immutable_snapshot(source: Path, expected_sha256: str, label: str) -> ImmutableSnapshot:
    """Copy exact bytes into a new path held with read-only sharing.

    The CreateFile handle is created with write access for the controller but
    shares only reads. It remains open across Blender load and extraction, so
    no other handle can open the snapshot for write or delete in that window.
    """
    if os.name != "nt":
        raise R6SnapshotError("R6 immutable snapshot lease is Windows-only and fails closed")
    directory = Path(tempfile.mkdtemp(prefix=f"kira_r24_r6_{label}_"))
    path = directory / f"{label}.blend"
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    kernel32.CreateFileW.restype = wintypes.HANDLE
    handle = kernel32.CreateFileW(
        str(path),
        0x80000000 | 0x40000000,  # GENERIC_READ | GENERIC_WRITE
        0x00000001,  # FILE_SHARE_READ only: no write or delete sharing
        None,
        1,  # CREATE_NEW
        0x00000100 | 0x08000000,  # TEMPORARY | SEQUENTIAL_SCAN
        None,
    )
    invalid = ctypes.c_void_p(-1).value
    if not handle or int(handle) == invalid:
        shutil.rmtree(directory, ignore_errors=True)
        raise _win_error("cannot create evaluator-owned snapshot")
    digest = hashlib.sha256()
    total = 0
    try:
        with source.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
                buffer = ctypes.create_string_buffer(block)
                written = wintypes.DWORD()
                if not kernel32.WriteFile(handle, buffer, len(block), ctypes.byref(written), None) or written.value != len(block):
                    raise _win_error("snapshot write failed")
                total += len(block)
        if digest.hexdigest() != expected_sha256:
            raise R6SnapshotError("copied snapshot bytes do not match evaluator-owned digest")
        if not kernel32.FlushFileBuffers(handle):
            raise _win_error("snapshot flush failed")
        zero = ctypes.c_longlong(0)
        if not kernel32.SetFilePointerEx(handle, zero, None, 0):
            raise _win_error("snapshot rewind failed")
        if sha256_file(path) != expected_sha256 or path.stat().st_size != total:
            raise R6SnapshotError("immutable snapshot post-write identity mismatch")
        return ImmutableSnapshot(path, expected_sha256, total, int(handle), directory)
    except BaseException:
        kernel32.CloseHandle(handle)
        shutil.rmtree(directory, ignore_errors=True)
        raise


@contextlib.contextmanager
def immutable_snapshot(source: Path, expected_sha256: str, label: str) -> Iterator[ImmutableSnapshot]:
    snapshot = _create_immutable_snapshot(source.resolve(), expected_sha256, label)
    try:
        yield snapshot
        if sha256_file(snapshot.path) != snapshot.sha256:
            raise R6SnapshotError("immutable snapshot changed while lease was held")
    finally:
        snapshot.close()


def validate_extraction_envelope(
    payload: object,
    *,
    snapshot: ImmutableSnapshot,
    nonce: str,
    extractor_sha256: str,
    helper_sha256: str,
) -> set[str]:
    failures: set[str] = set()
    if not isinstance(payload, Mapping):
        return {"extraction:document"}
    required = {
        "schema", "nonce", "snapshot", "logical_artifact_sha256", "extractor",
        "intersection_helper", "blender", "state", "truth", "state_sha256",
    }
    if set(payload) != required:
        failures.add("extraction:exact_envelope")
    if payload.get("schema") != "kira.avatar.r24.read_only_blender_extraction.v6":
        failures.add("extraction:schema")
    if payload.get("nonce") != nonce or payload.get("logical_artifact_sha256") != snapshot.sha256:
        failures.add("extraction:nonce_or_logical_digest")
    row = payload.get("snapshot")
    if not isinstance(row, Mapping) or row != {"path": str(snapshot.path), "bytes": snapshot.bytes, "sha256": snapshot.sha256}:
        failures.add("extraction:immutable_snapshot_binding")
    for name, path, digest in (("extractor", EXTRACTOR, extractor_sha256), ("intersection_helper", INTERSECTION_HELPER, helper_sha256)):
        binding = payload.get(name)
        if not isinstance(binding, Mapping) or binding != {"path": str(path), "bytes": path.stat().st_size, "sha256": digest}:
            failures.add(f"extraction:{name}_binding")
    blender = payload.get("blender")
    if not isinstance(blender, Mapping) or not blender.get("background") or Path(str(blender.get("loaded_filepath"))).resolve() != snapshot.path:
        failures.add("extraction:blender_context")
    if payload.get("truth") != {
        "read_only_extraction": True,
        "blend_saved": False,
        "snapshot_mutated": False,
        "in_memory_pose_evaluation_only": True,
    }:
        failures.add("extraction:read_only_truth")
    state = payload.get("state")
    expected_fields = {
        "objects", "mesh_objects", "armature_objects", "mesh_datablocks",
        "armature_datablocks", "materials", "actions", "images", "node_groups",
        "collections", "worlds", "scenes", "intersection_reports",
    }
    if not isinstance(state, Mapping) or set(state) != expected_fields:
        failures.add("extraction:complete_state")
    if payload.get("state_sha256") != canonical_sha256(state):
        failures.add("extraction:state_digest")
    return failures


def _invoke_extractor(snapshot: ImmutableSnapshot, blender: Path, timeout_seconds: int = 900) -> dict[str, object]:
    contract = load_sealed_contract()
    blender = r4.validate_blender_runtime(blender, contract)
    extractor_record = contract["authorized_implementation"]["read_only_extractor"]
    helper_record = contract["authorized_implementation"]["intersection_helper"]
    r4.validate_exact_file(ROOT, extractor_record)
    r4.validate_exact_file(ROOT, helper_record)
    if sha256_file(snapshot.path) != snapshot.sha256:
        raise R6SnapshotError("immutable snapshot changed before Blender launch")
    nonce = secrets.token_hex(32)
    with tempfile.TemporaryDirectory(prefix="kira_r24_r6_extract_") as raw:
        output = Path(raw) / "extraction.json"
        command = [
            str(blender), "--background", "--factory-startup", "--disable-autoexec",
            str(snapshot.path), "--python-exit-code", "1", "--python", str(EXTRACTOR),
            "--", "--snapshot", str(snapshot.path),
            "--snapshot-sha256", snapshot.sha256,
            "--logical-artifact-sha256", snapshot.sha256,
            "--extractor-sha256", str(extractor_record["sha256"]),
            "--intersection-helper-sha256", str(helper_record["sha256"]),
            "--nonce", nonce, "--output", str(output),
        ]
        environment = os.environ.copy()
        for name in ("PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "BLENDER_USER_SCRIPTS", "BLENDER_SYSTEM_SCRIPTS"):
            environment.pop(name, None)
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
            shell=False,
            env=environment,
        )
        if completed.returncode != 0 or not output.is_file() or output.stat().st_size > 512 * 1024 * 1024:
            raise R6SnapshotError(f"R6 extractor failed closed (exit={completed.returncode})")
        if sha256_file(snapshot.path) != snapshot.sha256:
            raise R6SnapshotError("immutable snapshot changed during Blender extraction")
        try:
            payload = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise R6SnapshotError(f"R6 extractor output invalid: {exc}") from exc
        failures = validate_extraction_envelope(
            payload,
            snapshot=snapshot,
            nonce=nonce,
            extractor_sha256=str(extractor_record["sha256"]),
            helper_sha256=str(helper_record["sha256"]),
        )
        if failures:
            raise R6SnapshotError("invalid R6 extractor envelope: " + ",".join(sorted(failures)))
        return payload


def validate_extracted_pair(
    source: Mapping[str, object],
    candidate: Mapping[str, object],
    contract: Mapping[str, object],
) -> set[str]:
    failures = r4.validate_extracted_pair(source, candidate, contract)
    failures.discard("render:minimum_triangle_area")
    failures.discard("render:minimum_triangle_angle")
    failures.discard("material:complete_source_exact_inventory")
    failures.discard("material:source_exact_graph")
    failures |= r5.validate_complete_protected_state(source, candidate, contract)
    failures |= r5.validate_complete_child_graphs(source, candidate, contract)
    context = r4.r3.exact_context()
    complete_patch = r4._mesh(candidate, contract["artifact_semantic_identity"]["patch_object_name"])
    scope_failures, replacement = r4.derive_repaired_estar_patch(complete_patch, context, contract)
    failures |= scope_failures
    bounds = contract["metric_bounds"]
    failures |= r5.validate_render_triangulation(
        replacement,
        float(bounds["minimum_render_triangle_area_m2"]),
        float(bounds["minimum_render_triangle_angle_degrees"]),
    )
    return failures


def artifact_evaluation_only(
    candidate_path: Path,
    expected_candidate_sha256: str,
    blender_executable: Path,
) -> dict[str, object]:
    """Fresh-process artifact gate; never claims author/process acceptance."""
    contract = load_sealed_contract()
    source = r4.validate_exact_file(
        ROOT,
        {
            "path": contract["exact_source"]["preserved_target_blend_path"],
            "bytes": contract["exact_source"]["preserved_target_blend_bytes"],
            "sha256": contract["exact_source"]["preserved_target_blend_sha256"],
        },
    )
    candidate = candidate_path.resolve()
    failures: set[str] = set()
    try:
        prefix = (ROOT / contract["authorized_implementation"]["candidate_path_prefix"]).resolve()
        relative = candidate.relative_to(prefix)
        if (
            len(relative.parts) != 2
            or not re.fullmatch(r"attempt_[0-9]{2}", relative.parts[0])
            or relative.parts[1] != contract["authorized_implementation"]["candidate_basename"]
        ):
            raise ValueError("candidate route is not exact")
        if not candidate.is_file():
            raise ValueError("candidate absent")
        if not re.fullmatch(r"[0-9a-f]{64}", expected_candidate_sha256):
            raise ValueError("candidate digest is malformed")
        if expected_candidate_sha256 == contract["exact_source"]["preserved_target_blend_sha256"]:
            failures.add("artifact:not_preserved_source")
        with immutable_snapshot(source, str(contract["exact_source"]["preserved_target_blend_sha256"]), "source") as source_snapshot, immutable_snapshot(candidate, expected_candidate_sha256, "candidate") as candidate_snapshot:
            source_typed = typed.parse_typed_blend(source_snapshot.path)
            candidate_typed = typed.parse_typed_blend(candidate_snapshot.path)
            failures |= r5.typed_inventory_failures(source_typed, candidate_typed, contract)
            if not failures:
                source_state = _invoke_extractor(source_snapshot, blender_executable)
                candidate_state = _invoke_extractor(candidate_snapshot, blender_executable)
                failures |= validate_extracted_pair(source_state, candidate_state, contract)
                # Preserve R5's repeated typed-preflight boundary, now against
                # the exact same lease-protected immutable bytes Blender read.
                if typed.parse_typed_blend(source_snapshot.path) != source_typed:
                    failures.add("typed_sdna:source_post_extraction_changed")
                if typed.parse_typed_blend(candidate_snapshot.path) != candidate_typed:
                    failures.add("typed_sdna:candidate_post_extraction_changed")
            if sha256_file(source_snapshot.path) != source_snapshot.sha256 or sha256_file(candidate_snapshot.path) != candidate_snapshot.sha256:
                failures.add("snapshot:final_identity")
    except (OSError, TypeError, ValueError, typed.TypedBlendError, R6SnapshotError):
        failures.add("artifact:failed_closed")
    return {
        "schema": "kira.avatar.r24.r6.fresh_artifact_evaluation.v1",
        "artifact_eligible": not failures,
        "eligible": False,
        "failure_names": sorted(failures),
        "truth": {
            "author_exit_or_process_tree_proved_here": False,
            "acceptance_requires_sealed_controller": True,
            "immutable_snapshot_used": True,
        },
    }


@dataclass(frozen=True)
class ProcessTreeEvidence:
    pid: int
    command_sha256: str
    returncode: int
    job_nonce: str
    job_signaled: bool
    active_processes_after_wait: int


class _WindowsJob:
    def __init__(self) -> None:
        if os.name != "nt":
            raise R6ProcessProtocolError("sealed process-tree protocol requires Windows Job Objects")
        self.kernel32 = ctypes.windll.kernel32
        self.handle = self.kernel32.CreateJobObjectW(None, None)
        if not self.handle:
            raise R6ProcessProtocolError("CreateJobObjectW failed")
        class BasicLimit(ctypes.Structure):
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
        class IoCounters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
            )]
        class ExtendedLimit(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BasicLimit),
                ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]
        info = ExtendedLimit()
        info.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
        if not self.kernel32.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            self.close()
            raise R6ProcessProtocolError("SetInformationJobObject failed")

    def assign(self, process: subprocess.Popen[bytes]) -> None:
        if not self.kernel32.AssignProcessToJobObject(self.handle, wintypes.HANDLE(int(process._handle))):
            raise R6ProcessProtocolError("AssignProcessToJobObject failed")

    def resume(self, process: subprocess.Popen[bytes]) -> None:
        status = ctypes.windll.ntdll.NtResumeProcess(wintypes.HANDLE(int(process._handle)))
        if status < 0:
            raise R6ProcessProtocolError("NtResumeProcess failed")

    def wait_quiescent(self, timeout_seconds: int) -> tuple[bool, int]:
        result = self.kernel32.WaitForSingleObject(self.handle, int(timeout_seconds * 1000))
        signaled = result == 0
        class Accounting(ctypes.Structure):
            _fields_ = [
                ("TotalUserTime", ctypes.c_longlong), ("TotalKernelTime", ctypes.c_longlong),
                ("ThisPeriodTotalUserTime", ctypes.c_longlong), ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
                ("TotalPageFaultCount", wintypes.DWORD), ("TotalProcesses", wintypes.DWORD),
                ("ActiveProcesses", wintypes.DWORD), ("TotalTerminatedProcesses", wintypes.DWORD),
            ]
        info = Accounting()
        returned = wintypes.DWORD()
        if not self.kernel32.QueryInformationJobObject(self.handle, 1, ctypes.byref(info), ctypes.sizeof(info), ctypes.byref(returned)):
            raise R6ProcessProtocolError("QueryInformationJobObject failed")
        return signaled, int(info.ActiveProcesses)

    def close(self) -> None:
        if getattr(self, "handle", 0):
            self.kernel32.CloseHandle(self.handle)
            self.handle = 0


def _run_sealed_process_tree(
    command: Sequence[str],
    *,
    timeout_seconds: int,
    environment: Mapping[str, str] | None = None,
) -> ProcessTreeEvidence:
    job = _WindowsJob()
    job_nonce = secrets.token_hex(32)
    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(
            [str(value) for value in command],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            env=dict(environment) if environment is not None else None,
            creationflags=0x00000004 | 0x00000200,  # CREATE_SUSPENDED | NEW_PROCESS_GROUP
        )
        job.assign(process)
        job.resume(process)
        try:
            process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            raise R6ProcessProtocolError("sealed process tree timed out") from exc
        signaled, active = job.wait_quiescent(30)
        returncode = process.poll()
        if returncode is None or not signaled or active != 0:
            raise R6ProcessProtocolError("sealed process tree did not become fully quiescent")
        return ProcessTreeEvidence(
            pid=int(process.pid),
            command_sha256=canonical_sha256([str(value) for value in command]),
            returncode=int(returncode),
            job_nonce=job_nonce,
            job_signaled=signaled,
            active_processes_after_wait=active,
        )
    finally:
        # Closing a non-quiescent job kills only this exact assigned tree.
        job.close()


def _sealed_author_command(
    contract: Mapping[str, object],
    attempt: str,
    nonce: str,
    blender: Path,
    source_snapshot: ImmutableSnapshot,
) -> tuple[list[str], Path]:
    if not re.fullmatch(r"attempt_[0-9]{2}", attempt):
        raise R6ProcessProtocolError("attempt name is not exact")
    implementation = contract["authorized_implementation"]
    author = r4.validate_exact_file(ROOT, implementation["sealed_author_worker"])
    if source_snapshot.sha256 != contract["exact_source"]["preserved_target_blend_sha256"]:
        raise R6ProcessProtocolError("sealed author source snapshot changed")
    output = ROOT / implementation["candidate_path_prefix"] / attempt / implementation["candidate_basename"]
    return [
        str(blender), "--background", "--factory-startup", "--disable-autoexec",
        "--python-exit-code", "1", "--python", str(author), "--",
        "--source", str(source_snapshot.path), "--output", str(output), "--controller-nonce", nonce,
        "--execute-authoring",
    ], output


def _fresh_evaluator_command(
    contract: Mapping[str, object],
    candidate: Path,
    digest: str,
    blender: Path,
    nonce: str,
    output: Path,
) -> list[str]:
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or not re.fullmatch(r"[0-9a-f]{64}", nonce):
        raise R6ProcessProtocolError("fresh evaluator digest or nonce is malformed")
    evaluator = r4.validate_exact_file(
        ROOT, contract["authorized_implementation"]["fresh_evaluator"]
    )
    python = r4.validate_absolute_exact_file(
        contract["authorized_implementation"]["python_executable"]
    )
    return [
        str(python), "-B", str(evaluator), "--candidate", str(candidate),
        "--candidate-sha256", digest, "--blender", str(blender),
        "--nonce", nonce, "--output", str(output),
    ]


def _restricted_child_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in (
        "PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "PYTHONINSPECT",
        "BLENDER_USER_SCRIPTS", "BLENDER_SYSTEM_SCRIPTS",
    ):
        environment.pop(name, None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def run_sealed_author_then_fresh_evaluator(
    attempt: str,
    blender_executable: Path,
    *,
    author_timeout_seconds: int = 1800,
    evaluator_timeout_seconds: int = 1800,
) -> dict[str, object]:
    contract = load_sealed_contract()
    schema = contract["authorized_implementation"]["required_gate_schema"]
    if not contract.get("static_execution_authority"):
        return {"schema": schema, "eligible": False, "failure_names": ["r6_static_execution_authority_not_granted"]}
    blender = r4.validate_blender_runtime(blender_executable, contract)
    nonce = secrets.token_hex(32)
    source = r4.validate_exact_file(
        ROOT,
        {
            "path": contract["exact_source"]["preserved_target_blend_path"],
            "bytes": contract["exact_source"]["preserved_target_blend_bytes"],
            "sha256": contract["exact_source"]["preserved_target_blend_sha256"],
        },
    )
    try:
        with immutable_snapshot(
            source,
            str(contract["exact_source"]["preserved_target_blend_sha256"]),
            "author_source",
        ) as author_source_snapshot:
            command, candidate = _sealed_author_command(
                contract, attempt, nonce, blender, author_source_snapshot
            )
            if candidate.exists():
                return {"schema": schema, "eligible": False, "failure_names": ["author:candidate_not_fresh"]}
            candidate.parent.mkdir(parents=True, exist_ok=False)
            author = _run_sealed_process_tree(
                command,
                timeout_seconds=author_timeout_seconds,
                environment=_restricted_child_environment(),
            )
            if author.returncode != 0 or not candidate.is_file():
                return {"schema": schema, "eligible": False, "failure_names": ["author:sealed_tree_or_candidate"]}
            if sha256_file(author_source_snapshot.path) != author_source_snapshot.sha256:
                return {"schema": schema, "eligible": False, "failure_names": ["author:source_snapshot_changed"]}
        digest = sha256_file(candidate)
        with tempfile.TemporaryDirectory(prefix="kira_r24_r6_fresh_eval_") as raw:
            output = Path(raw) / "result.json"
            evaluator_command = _fresh_evaluator_command(
                contract, candidate, digest, blender, nonce, output
            )
            evaluator_tree = _run_sealed_process_tree(
                evaluator_command,
                timeout_seconds=evaluator_timeout_seconds,
                environment=_restricted_child_environment(),
            )
            if evaluator_tree.returncode != 0 or not output.is_file():
                return {"schema": schema, "eligible": False, "failure_names": ["evaluator:fresh_tree"]}
            envelope = json.loads(output.read_text(encoding="utf-8"))
            if (
                not isinstance(envelope, Mapping)
                or envelope.get("nonce") != nonce
                or envelope.get("candidate_sha256") != digest
                or not isinstance(envelope.get("artifact_result"), Mapping)
            ):
                return {"schema": schema, "eligible": False, "failure_names": ["evaluator:narrow_channel"]}
            artifact = envelope["artifact_result"]
            failures = list(artifact.get("failure_names", [])) if isinstance(artifact.get("failure_names"), list) else ["evaluator:result"]
            eligible = bool(artifact.get("artifact_eligible")) and not failures
            return {
                "schema": schema,
                "eligible": eligible,
                "failure_names": sorted(str(value) for value in failures),
                "derived": {
                    "candidate_sha256": digest,
                    "author_process_tree": author.__dict__,
                    "fresh_evaluator_process_tree": evaluator_tree.__dict__,
                    "sealed_author_command_sha256": canonical_sha256(command),
                },
            }
    except (OSError, TypeError, ValueError, json.JSONDecodeError, R6ProcessProtocolError):
        return {"schema": schema, "eligible": False, "failure_names": ["sealed_author_fresh_evaluator_protocol_failed"]}


def evaluate_candidate_artifact(candidate_path: Path, blender_executable: Path) -> dict[str, object]:
    del candidate_path, blender_executable
    contract = load_sealed_contract()
    return {
        "schema": contract["authorized_implementation"]["required_gate_schema"],
        "eligible": False,
        "failure_names": ["path_only_evaluation_forbidden_use_sealed_controller"],
    }


def package_inventory_status(package: Path = PACKAGE) -> dict[str, object]:
    pre = {
        "CHECKPOINT.md",
        "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R6_CONTRACT.json",
        "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R6_PROPOSAL.md",
        "PACKAGE_MANIFEST.json",
        "STATIC_TEST_RESULTS.json",
    }
    post = pre | {"INDEPENDENT_STATIC_AUDIT.md"}
    actual = {path.name for path in package.iterdir() if path.is_file()} if package.is_dir() else set()
    state = "PRE_AUDIT_EXACT" if actual == pre else "POST_AUDIT_EXACT" if actual == post else "INVALID"
    return {"state": state, "actual": sorted(actual), "pre_audit": sorted(pre), "post_audit": sorted(post)}


def static_evaluation() -> dict[str, object]:
    contract = load_sealed_contract()
    return {
        "schema": "kira.avatar.r24.r6.static_gate_result.v1",
        "status": contract["status"],
        "r5_disposition": "PRESERVED_REJECTED",
        "package_inventory": package_inventory_status(),
        "blender_launched": False,
        "candidate_created": False,
        "execution_authority_granted": False,
        "fresh_independent_r6_audit_required": True,
    }


def main() -> int:
    print(json.dumps(static_evaluation(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
