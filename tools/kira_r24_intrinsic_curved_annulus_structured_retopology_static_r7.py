from __future__ import annotations

"""Append-only R24 R7 static gate; no Blender/body authority is granted."""

import contextlib
import copy
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
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
from types import MappingProxyType
from typing import Iterator, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import kira_r24_blend_sdna_typed_static_r5 as typed
from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static_r4 as r4
from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static_r5 as r5
from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static_r6 as r6


PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7"
)
DEFAULT_CONTRACT = PACKAGE / "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R7_CONTRACT.json"
EXTRACTOR = ROOT / "tools/blender_extract_kira_r24_candidate_read_only_r7.py"
INTERSECTION_HELPER = ROOT / "tools/blender_exact_mesh_intersections.py"
FRESH_EVALUATOR = ROOT / "tools/kira_r24_r7_fresh_evaluator.py"
SEALED_CONTROLLER = ROOT / "tools/kira_r24_r7_sealed_controller.py"
SEALED_CONTRACT_FILE_SHA256 = "0000000000000000000000000000000000000000000000000000000000000000"
SEALED_CONTRACT_SEMANTIC_SHA256 = "0000000000000000000000000000000000000000000000000000000000000000"


class R7PackageError(ValueError):
    pass


class R7SnapshotError(RuntimeError):
    pass


class R7ProcessProtocolError(RuntimeError):
    pass


def canonical_json(value: object) -> bytes:
    return r4.canonical_json(value)


def canonical_sha256(value: object) -> str:
    return r4.canonical_sha256(value)


def sha256_file(path: Path) -> str:
    return r4.sha256_file(path)


def normalized_sealed_python_sha256(path: Path) -> str:
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
                    raise R7PackageError("R7 seal literal shape changed")
                replacement = prefix + b"0" * 64 + suffix
                found.add(prefix)
        result.append(replacement)
    if found != set(prefixes):
        raise R7PackageError("R7 seal field inventory changed")
    return hashlib.sha256(b"".join(result)).hexdigest()


def normalized_worker_sha256(path: Path = Path(__file__)) -> str:
    return normalized_sealed_python_sha256(path)


def _semantic_projection(value: Mapping[str, object]) -> dict[str, object]:
    result = copy.deepcopy(dict(value))
    result["semantic_seal_sha256"] = ""
    return result


def deep_freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): deep_freeze(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(deep_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(deep_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(deep_freeze(item) for item in value)
    return value


def deep_thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): deep_thaw(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [deep_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return {deep_thaw(item) for item in value}
    return value


def _load_contract_overlay() -> tuple[dict[str, object], str]:
    try:
        raw = DEFAULT_CONTRACT.read_bytes()
        overlay = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise R7PackageError(f"R7 contract cannot be loaded: {exc}") from exc
    if hashlib.sha256(raw).hexdigest() != SEALED_CONTRACT_FILE_SHA256:
        raise R7PackageError("R7 contract file identity changed")
    semantic = canonical_sha256(_semantic_projection(overlay))
    if semantic != SEALED_CONTRACT_SEMANTIC_SHA256 or overlay.get("semantic_seal_sha256") != semantic:
        raise R7PackageError("R7 contract semantic identity changed")
    if overlay.get("schema") != "kira.avatar.r24.artifact_derived_gate.v7":
        raise R7PackageError("unexpected R7 schema")
    parents = overlay.get("parent_bindings")
    expected_parents = {
        "r6_contract", "r6_proposal", "r6_checkpoint", "r6_manifest",
        "r6_static_results", "r6_audit",
    }
    if not isinstance(parents, Mapping) or set(parents) != expected_parents:
        raise R7PackageError("R7 parent inventory changed")
    for record in parents.values():
        if not isinstance(record, Mapping):
            raise R7PackageError("R7 parent binding malformed")
        r4.validate_exact_file(ROOT, record)
    implementation = overlay.get("authorized_implementation")
    expected = {
        "worker", "sealed_controller", "runtime_dependencies", "focused_test",
        "python_executable", "candidate_path_prefix", "required_gate_schema",
        "candidate_basename",
    }
    if not isinstance(implementation, Mapping) or set(implementation) != expected:
        raise R7PackageError("R7 implementation inventory changed")
    worker = implementation.get("worker")
    if (
        not isinstance(worker, Mapping)
        or worker.get("path") != Path(__file__).resolve().relative_to(ROOT.resolve()).as_posix()
        or worker.get("normalized_semantic_sha256") != normalized_worker_sha256()
    ):
        raise R7PackageError("R7 worker binding changed")
    controller = implementation.get("sealed_controller")
    if (
        not isinstance(controller, Mapping)
        or controller.get("path") != SEALED_CONTROLLER.relative_to(ROOT).as_posix()
        or controller.get("normalized_semantic_sha256")
        != normalized_sealed_python_sha256(SEALED_CONTROLLER)
    ):
        raise R7PackageError("R7 sealed controller binding changed")
    runtime = implementation.get("runtime_dependencies")
    required_runtime = {
        "base_worker", "r2_worker", "r3_worker", "r4_worker",
        "r5_worker", "r6_worker", "typed_r4", "typed_r5", "r4_extractor",
        "r5_extractor", "r7_projection", "r7_extractor",
        "intersection_helper", "r7_author", "r7_evaluator",
    }
    if not isinstance(runtime, Mapping) or set(runtime) != required_runtime:
        raise R7PackageError("R7 runtime dependency inventory changed")
    for name, record in runtime.items():
        if not isinstance(record, Mapping):
            raise R7PackageError(f"R7 runtime binding {name!r} absent")
        r4.validate_exact_file(ROOT, record)
    focused_test = implementation.get("focused_test")
    if not isinstance(focused_test, Mapping):
        raise R7PackageError("R7 focused test binding absent")
    r4.validate_exact_file(ROOT, focused_test)
    python_record = implementation.get("python_executable")
    if not isinstance(python_record, Mapping):
        raise R7PackageError("R7 Python binding absent")
    r4.validate_absolute_exact_file(python_record)
    amendments = overlay.get("r7_amendments")
    required_amendments = {
        "immutable_windows_snapshot_lease",
        "fresh_exact_sealed_controller_process",
        "deep_frozen_uncached_contract",
        "leased_complete_runtime_dependency_set",
        "sealed_author_command",
        "full_author_process_tree_quiescence",
        "fresh_evaluator_process",
        "anonymous_pipe_evaluator_result",
        "anonymous_pipe_extractor_result",
        "strict_outer_and_nested_schemas",
        "replacement_only_world_quality",
        "inherited_outside_world_non_regression",
        "exact_blender_5_1_0_extraction_and_envelope",
        "both_blender_safety_flags",
        "recursive_nla_meta_child_semantics",
        "material_target_type_name_library_identity",
        "post_audit_package_state",
    }
    if not isinstance(amendments, Mapping) or set(amendments) != required_amendments or not all(amendments.values()):
        raise R7PackageError("R7 amendment inventory changed")
    return overlay, semantic


def _merge_contract_overlay(
    overlay: Mapping[str, object], semantic: str
) -> Mapping[str, object]:
    # Clear the rejected parent's public mutable cache before and after use.
    # The separately launched R7 controller performs this only after every
    # imported project dependency is protected by a deny-write/delete lease.
    thawed = deep_thaw(overlay)
    if not isinstance(thawed, dict):
        raise R7PackageError("R7 thawed contract overlay is not a dictionary")
    overlay = thawed
    r6.load_sealed_contract.cache_clear()
    parent = copy.deepcopy(r6.load_sealed_contract())
    r6.load_sealed_contract.cache_clear()
    merged = copy.deepcopy(parent)
    merged.update(
        {
            "schema": overlay["schema"],
            "status": overlay["status"],
            "lane": overlay["lane"],
            "mode": overlay["mode"],
            "authorized_implementation": copy.deepcopy(implementation),
            "r7_amendments": copy.deepcopy(amendments),
            "inherited_outside_world_quality": copy.deepcopy(
                overlay["inherited_outside_world_quality"]
            ),
            "controller_protocol": copy.deepcopy(overlay["controller_protocol"]),
            "static_execution_authority": bool(overlay.get("static_execution_authority", False)),
            "semantic_seal_sha256": semantic,
        }
    )
    frozen = deep_freeze(merged)
    if not isinstance(frozen, Mapping):
        raise R7PackageError("R7 frozen contract is not a mapping")
    return frozen


def load_sealed_contract() -> Mapping[str, object]:
    """Return a fresh recursively immutable contract on every call."""
    overlay, semantic = _load_contract_overlay()
    return _merge_contract_overlay(overlay, semantic)


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


def _win_error(message: str) -> R7SnapshotError:
    return R7SnapshotError(f"{message}: Windows error {ctypes.get_last_error()}")


def _create_immutable_snapshot(source: Path, expected_sha256: str, label: str) -> ImmutableSnapshot:
    """Copy exact bytes into a new path held with read-only sharing.

    The CreateFile handle is created with write access for the controller but
    shares only reads. It remains open across Blender load and extraction, so
    no other handle can open the snapshot for write or delete in that window.
    """
    if os.name != "nt":
        raise R7SnapshotError("R7 immutable snapshot lease is Windows-only and fails closed")
    directory = Path(tempfile.mkdtemp(prefix=f"kira_r24_r7_{label}_"))
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
            raise R7SnapshotError("copied snapshot bytes do not match evaluator-owned digest")
        if not kernel32.FlushFileBuffers(handle):
            raise _win_error("snapshot flush failed")
        zero = ctypes.c_longlong(0)
        if not kernel32.SetFilePointerEx(handle, zero, None, 0):
            raise _win_error("snapshot rewind failed")
        if sha256_file(path) != expected_sha256 or path.stat().st_size != total:
            raise R7SnapshotError("immutable snapshot post-write identity mismatch")
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
            raise R7SnapshotError("immutable snapshot changed while lease was held")
    finally:
        snapshot.close()


def validate_extraction_envelope(
    payload: object,
    *,
    snapshot: ImmutableSnapshot,
    nonce: str,
    dependency_records: Mapping[str, Mapping[str, object]],
) -> set[str]:
    failures: set[str] = set()
    if not isinstance(payload, Mapping):
        return {"extraction:document"}
    required = {
        "schema", "nonce", "snapshot", "logical_artifact_sha256",
        "dependencies", "blender", "state", "truth", "state_sha256",
    }
    if set(payload) != required:
        failures.add("extraction:exact_envelope")
    if payload.get("schema") != "kira.avatar.r24.read_only_blender_extraction.v7":
        failures.add("extraction:schema")
    if payload.get("nonce") != nonce or payload.get("logical_artifact_sha256") != snapshot.sha256:
        failures.add("extraction:nonce_or_logical_digest")
    row = payload.get("snapshot")
    if not isinstance(row, Mapping) or row != {"path": str(snapshot.path), "bytes": snapshot.bytes, "sha256": snapshot.sha256}:
        failures.add("extraction:immutable_snapshot_binding")
    expected_dependencies = {
        role: {
            "path": str((ROOT / str(record["path"])).resolve()),
            "bytes": int(record["bytes"]),
            "sha256": str(record["sha256"]),
        }
        for role, record in dependency_records.items()
    }
    if payload.get("dependencies") != expected_dependencies:
        failures.add("extraction:dependency_bundle")
    blender = payload.get("blender")
    if (
        not isinstance(blender, Mapping)
        or set(blender) != {
            "version", "background", "loaded_filepath", "loaded_file_sha256"
        }
        or blender.get("version") != "5.1.0"
        or blender.get("background") is not True
        or Path(str(blender.get("loaded_filepath"))).resolve() != snapshot.path
        or blender.get("loaded_file_sha256") != snapshot.sha256
    ):
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


def _extractor_dependency_records(
    contract: Mapping[str, object],
) -> dict[str, Mapping[str, object]]:
    runtime = contract["authorized_implementation"]["runtime_dependencies"]
    roles = (
        "r7_extractor", "r7_projection", "r5_extractor", "r4_extractor",
        "intersection_helper",
    )
    return {role: runtime[role] for role in roles}


def _decode_extractor_stdout(stdout: bytes, nonce: str) -> object:
    if len(stdout) > 768 * 1024 * 1024:
        raise R7SnapshotError("R7 extractor stdout exceeds sealed bound")
    prefix = f"KIRA_R24_R7_EXTRACTION:{nonce}:".encode("ascii")
    matches = [line[len(prefix) :] for line in stdout.splitlines() if line.startswith(prefix)]
    if len(matches) != 1:
        raise R7SnapshotError("R7 extractor anonymous-pipe envelope is absent or ambiguous")
    try:
        return json.loads(matches[0])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise R7SnapshotError(f"R7 extractor pipe envelope invalid: {exc}") from exc


def _invoke_extractor(snapshot: ImmutableSnapshot, blender: Path, timeout_seconds: int = 900) -> dict[str, object]:
    contract = load_sealed_contract()
    blender = r4.validate_blender_runtime(blender, contract)
    dependencies = _extractor_dependency_records(contract)
    for record in dependencies.values():
        r4.validate_exact_file(ROOT, record)
    if sha256_file(snapshot.path) != snapshot.sha256:
        raise R7SnapshotError("immutable snapshot changed before Blender launch")
    nonce = secrets.token_hex(32)
    with tempfile.TemporaryDirectory(prefix="kira_r24_r7_extract_cache_") as raw:
        command = [
            str(blender), "--background", "--factory-startup", "--disable-autoexec",
            str(snapshot.path), "--python-exit-code", "1", "--python", str(EXTRACTOR),
            "--", "--snapshot", str(snapshot.path),
            "--snapshot-sha256", snapshot.sha256,
            "--logical-artifact-sha256", snapshot.sha256,
            "--extractor-sha256", str(dependencies["r7_extractor"]["sha256"]),
            "--projection-sha256", str(dependencies["r7_projection"]["sha256"]),
            "--r5-extractor-sha256", str(dependencies["r5_extractor"]["sha256"]),
            "--r4-extractor-sha256", str(dependencies["r4_extractor"]["sha256"]),
            "--intersection-helper-sha256", str(dependencies["intersection_helper"]["sha256"]),
            "--nonce", nonce,
        ]
        environment = os.environ.copy()
        for name in ("PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "BLENDER_USER_SCRIPTS", "BLENDER_SYSTEM_SCRIPTS"):
            environment.pop(name, None)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONPYCACHEPREFIX"] = str(Path(raw).resolve())
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
        if completed.returncode != 0:
            raise R7SnapshotError(f"R7 extractor failed closed (exit={completed.returncode})")
        if sha256_file(snapshot.path) != snapshot.sha256:
            raise R7SnapshotError("immutable snapshot changed during Blender extraction")
        payload = _decode_extractor_stdout(completed.stdout, nonce)
        failures = validate_extraction_envelope(
            payload,
            snapshot=snapshot,
            nonce=nonce,
            dependency_records=dependencies,
        )
        if failures:
            raise R7SnapshotError("invalid R7 extractor envelope: " + ",".join(sorted(failures)))
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
    failures |= validate_inherited_outside_world_non_regression(
        source, candidate, contract
    )
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


def source_domain_triangle_quality_world(
    source_mesh: Mapping[str, object],
    face_indices: set[int],
    matrix_world: object,
    minimum_area: float,
    minimum_angle: float,
) -> dict[str, object]:
    """Measure inherited source triangles after the exact object transform.

    This is an identity/non-regression record, not permission to relabel the
    inherited licensed topology as newly authored R24 replacement quality.
    """
    positions = source_mesh.get("positions")
    faces = source_mesh.get("faces")
    if not isinstance(positions, list) or not isinstance(faces, list) or not face_indices:
        raise R7PackageError("world-space inherited source domain is absent")
    records: list[tuple[int, float, float]] = []
    for face_index in sorted(face_indices):
        if face_index < 0 or face_index >= len(faces):
            raise R7PackageError("world-space inherited face index is invalid")
        face = faces[face_index]
        if (
            not isinstance(face, list)
            or len(face) != 3
            or any(
                not r4.is_int(value)
                or int(value) < 0
                or int(value) >= len(positions)
                for value in face
            )
        ):
            raise R7PackageError("world-space inherited face is not a triangle")
        points = [
            r4._matrix_transform(matrix_world, positions[int(value)])
            for value in face
        ]
        if any(not r4.finite_vector(point, 3) for point in points):
            raise R7PackageError("world-space inherited transform is malformed")
        area, angle = r4._triangle_measurements(points)  # type: ignore[arg-type]
        records.append((face_index, area, angle))
    minimum_area_record = min(records, key=lambda row: (row[1], row[0]))
    minimum_angle_record = min(records, key=lambda row: (row[2], row[0]))
    below_area = [index for index, area, _ in records if area < minimum_area]
    below_angle = [index for index, _, angle in records if angle < minimum_angle]
    return {
        "space": "WORLD_METERS_AFTER_EXACT_MATRIX_WORLD",
        "matrix_world_sha256": canonical_sha256(matrix_world),
        "face_count": len(records),
        "minimum_area_m2": minimum_area_record[1],
        "minimum_area_face_index": minimum_area_record[0],
        "below_replacement_minimum_area_count": len(below_area),
        "below_replacement_minimum_area_face_indices_sha256": canonical_sha256(below_area),
        "minimum_angle_degrees": minimum_angle_record[2],
        "minimum_angle_face_index": minimum_angle_record[0],
        "below_replacement_minimum_angle_count": len(below_angle),
        "below_replacement_minimum_angle_face_indices_sha256": canonical_sha256(below_angle),
        "classification": "INHERITED_EXACT_WORLD_NON_REGRESSION_NOT_R24_REPLACEMENT_QUALITY",
    }


def validate_inherited_outside_world_non_regression(
    source: Mapping[str, object],
    candidate: Mapping[str, object],
    contract: Mapping[str, object],
) -> set[str]:
    expected = contract.get("inherited_outside_world_quality")
    if not isinstance(expected, Mapping) or set(expected) != {
        "matrix_world", "matrix_provenance", "quality"
    }:
        return {"render:inherited_outside_world_contract"}
    matrix = expected.get("matrix_world")
    source_body = r4._mesh(
        source, contract["artifact_semantic_identity"]["body_object_name"]
    )
    candidate_body = r4._mesh(
        candidate, contract["artifact_semantic_identity"]["body_object_name"]
    )
    if not isinstance(source_body, Mapping) or not isinstance(candidate_body, Mapping):
        return {"render:inherited_outside_world_body_missing"}
    failures: set[str] = set()
    if source_body.get("matrix_world") != matrix:
        failures.add("render:source_body_matrix_world_binding")
    if candidate_body.get("matrix_world") != matrix:
        failures.add("render:candidate_body_matrix_world_non_regression")
    try:
        context = r4.r3.exact_context()
        bounds = contract["metric_bounds"]
        source_quality = source_domain_triangle_quality_world(
            context["source_mesh"],
            set(context["domains"]["outside"]),
            source_body.get("matrix_world"),
            float(bounds["minimum_render_triangle_area_m2"]),
            float(bounds["minimum_render_triangle_angle_degrees"]),
        )
        candidate_quality = source_domain_triangle_quality_world(
            context["source_mesh"],
            set(context["domains"]["outside"]),
            candidate_body.get("matrix_world"),
            float(bounds["minimum_render_triangle_area_m2"]),
            float(bounds["minimum_render_triangle_angle_degrees"]),
        )
    except (KeyError, TypeError, ValueError, R7PackageError):
        return failures | {"render:inherited_outside_world_measurement"}
    if source_quality != expected.get("quality"):
        failures.add("render:source_inherited_outside_world_binding")
    if candidate_quality != source_quality:
        failures.add("render:candidate_inherited_outside_world_non_regression")
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
    except (OSError, TypeError, ValueError, typed.TypedBlendError, R7SnapshotError):
        failures.add("artifact:failed_closed")
    return {
        "schema": "kira.avatar.r24.r7.fresh_artifact_evaluation.v2",
        "artifact_eligible": not failures,
        "eligible": False,
        "failure_names": sorted(failures),
        "truth": {
            "author_exit_or_process_tree_proved_here": False,
            "acceptance_requires_sealed_controller": True,
            "immutable_snapshot_used": True,
            "extraction_stdout_anonymous_pipe": True,
        },
    }


def validate_artifact_evaluation_result(payload: object) -> set[str]:
    failures: set[str] = set()
    if not isinstance(payload, Mapping):
        return {"artifact_result:document"}
    if set(payload) != {
        "schema", "artifact_eligible", "eligible", "failure_names", "truth"
    }:
        failures.add("artifact_result:exact_fields")
    if payload.get("schema") != "kira.avatar.r24.r7.fresh_artifact_evaluation.v2":
        failures.add("artifact_result:schema")
    names = payload.get("failure_names")
    if (
        not isinstance(names, (list, tuple))
        or any(not isinstance(name, str) or not name for name in names)
        or list(names) != sorted(set(names))
    ):
        failures.add("artifact_result:failure_names")
    if not isinstance(payload.get("artifact_eligible"), bool) or payload.get("eligible") is not False:
        failures.add("artifact_result:eligibility_types")
    if payload.get("truth") != {
        "author_exit_or_process_tree_proved_here": False,
        "acceptance_requires_sealed_controller": True,
        "immutable_snapshot_used": True,
        "extraction_stdout_anonymous_pipe": True,
    }:
        failures.add("artifact_result:truth")
    if isinstance(names, (list, tuple)) and bool(payload.get("artifact_eligible")) == bool(names):
        failures.add("artifact_result:eligibility_consistency")
    return failures


@dataclass(frozen=True)
class ProcessTreeEvidence:
    pid: int
    command_sha256: str
    returncode: int
    job_nonce: str
    job_signaled: bool
    active_processes_after_wait: int
    stdout: bytes
    stderr: bytes

    @property
    def job_quiescent(self) -> bool:
        return self.job_signaled and self.active_processes_after_wait == 0


class _WindowsJob:
    def __init__(self) -> None:
        if os.name != "nt":
            raise R7ProcessProtocolError("sealed process-tree protocol requires Windows Job Objects")
        self.kernel32 = ctypes.windll.kernel32
        self.handle = self.kernel32.CreateJobObjectW(None, None)
        if not self.handle:
            raise R7ProcessProtocolError("CreateJobObjectW failed")
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
            raise R7ProcessProtocolError("SetInformationJobObject failed")

    def assign(self, process: subprocess.Popen[bytes]) -> None:
        if not self.kernel32.AssignProcessToJobObject(self.handle, wintypes.HANDLE(int(process._handle))):
            raise R7ProcessProtocolError("AssignProcessToJobObject failed")

    def resume(self, process: subprocess.Popen[bytes]) -> None:
        status = ctypes.windll.ntdll.NtResumeProcess(wintypes.HANDLE(int(process._handle)))
        if status < 0:
            raise R7ProcessProtocolError("NtResumeProcess failed")

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
            raise R7ProcessProtocolError("QueryInformationJobObject failed")
        return signaled, int(info.ActiveProcesses)

    def close(self) -> None:
        if getattr(self, "handle", 0):
            self.kernel32.CloseHandle(self.handle)
            self.handle = 0


def _run_sealed_process_tree(
    command: Sequence[str],
    *,
    expected_command_sha256: str,
    expected_job_nonce: str,
    timeout_seconds: int,
    environment: Mapping[str, str] | None = None,
) -> ProcessTreeEvidence:
    exact_command = [str(value) for value in command]
    actual_command_sha256 = canonical_sha256(exact_command)
    if (
        not re.fullmatch(r"[0-9a-f]{64}", expected_command_sha256)
        or actual_command_sha256 != expected_command_sha256
    ):
        raise R7ProcessProtocolError("sealed process command digest mismatch")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_job_nonce):
        raise R7ProcessProtocolError("sealed process job nonce is malformed")
    job = _WindowsJob()
    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(
            exact_command,
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
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            raise R7ProcessProtocolError("sealed process tree timed out") from exc
        signaled, active = job.wait_quiescent(30)
        returncode = process.poll()
        if returncode is None or not signaled or active != 0:
            raise R7ProcessProtocolError("sealed process tree did not become fully quiescent")
        return ProcessTreeEvidence(
            pid=int(process.pid),
            command_sha256=actual_command_sha256,
            returncode=int(returncode),
            job_nonce=expected_job_nonce,
            job_signaled=signaled,
            active_processes_after_wait=active,
            stdout=stdout,
            stderr=stderr,
        )
    finally:
        # Closing a non-quiescent job kills only this exact assigned tree.
        job.close()


def _sealed_author_command(
    contract: Mapping[str, object],
    attempt: str,
    controller_nonce: str,
    author_job_nonce: str,
    blender: Path,
    source_snapshot: ImmutableSnapshot,
) -> tuple[list[str], Path]:
    if not re.fullmatch(r"attempt_[0-9]{2}", attempt):
        raise R7ProcessProtocolError("attempt name is not exact")
    implementation = contract["authorized_implementation"]
    author = r4.validate_exact_file(
        ROOT, implementation["runtime_dependencies"]["r7_author"]
    )
    if source_snapshot.sha256 != contract["exact_source"]["preserved_target_blend_sha256"]:
        raise R7ProcessProtocolError("sealed author source snapshot changed")
    output = ROOT / implementation["candidate_path_prefix"] / attempt / implementation["candidate_basename"]
    return [
        str(blender), "--background", "--factory-startup", "--disable-autoexec",
        "--python-exit-code", "1", "--python", str(author), "--",
        "--source", str(source_snapshot.path), "--output", str(output),
        "--controller-nonce", controller_nonce,
        "--job-nonce", author_job_nonce,
        "--source-snapshot-sha256", source_snapshot.sha256,
        "--execute-authoring",
    ], output


def _fresh_evaluator_command(
    contract: Mapping[str, object],
    candidate: Path,
    digest: str,
    blender: Path,
    controller_nonce: str,
    author: ProcessTreeEvidence,
    source_snapshot_sha256: str,
    dependency_bundle_sha256: str,
) -> list[str]:
    if (
        not re.fullmatch(r"[0-9a-f]{64}", digest)
        or not re.fullmatch(r"[0-9a-f]{64}", controller_nonce)
        or not re.fullmatch(r"[0-9a-f]{64}", source_snapshot_sha256)
        or not re.fullmatch(r"[0-9a-f]{64}", dependency_bundle_sha256)
        or not author.job_quiescent
        or author.pid <= 0
    ):
        raise R7ProcessProtocolError("fresh evaluator receipt input is malformed")
    evaluator = r4.validate_exact_file(
        ROOT,
        contract["authorized_implementation"]["runtime_dependencies"]["r7_evaluator"],
    )
    python = r4.validate_absolute_exact_file(
        contract["authorized_implementation"]["python_executable"]
    )
    return [
        str(python), "-B", str(evaluator), "--candidate", str(candidate),
        "--candidate-sha256", digest, "--blender", str(blender),
        "--controller-nonce", controller_nonce,
        "--author-job-nonce", author.job_nonce,
        "--author-command-sha256", author.command_sha256,
        "--author-pid", str(author.pid),
        "--author-job-quiescent", "true",
        "--immutable-source-snapshot-sha256", source_snapshot_sha256,
        "--dependency-bundle-sha256", dependency_bundle_sha256,
        "--expected-evaluator-path", str(evaluator),
        "--expected-evaluator-bytes", str(evaluator.stat().st_size),
        "--expected-evaluator-sha256", sha256_file(evaluator),
    ]


def _restricted_child_environment(cache_root: Path | None = None) -> dict[str, str]:
    environment = os.environ.copy()
    for name in (
        "PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "PYTHONINSPECT",
        "BLENDER_USER_SCRIPTS", "BLENDER_SYSTEM_SCRIPTS",
    ):
        environment.pop(name, None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    if cache_root is not None:
        environment["PYTHONPYCACHEPREFIX"] = str(cache_root.resolve())
    return environment


def validate_fresh_evaluator_envelope(
    payload: object,
    *,
    contract: Mapping[str, object],
    candidate: Path,
    candidate_sha256: str,
    controller_nonce: str,
    immutable_snapshot_sha256: str,
    author: ProcessTreeEvidence,
    evaluator_tree: ProcessTreeEvidence,
    dependency_bundle_sha256: str,
) -> set[str]:
    failures: set[str] = set()
    if not isinstance(payload, Mapping):
        return {"evaluator:document"}
    expected_keys = {
        "schema", "controller_nonce", "author_job_nonce", "candidate",
        "immutable_source_snapshot_sha256", "author", "evaluator",
        "dependency_bundle_sha256", "artifact_result", "truth",
    }
    if set(payload) != expected_keys:
        failures.add("evaluator:exact_envelope")
    if payload.get("schema") != "kira.avatar.r24.r7.fresh_evaluator_envelope.v2":
        failures.add("evaluator:schema")
    if payload.get("controller_nonce") != controller_nonce:
        failures.add("evaluator:controller_nonce")
    if payload.get("author_job_nonce") != author.job_nonce:
        failures.add("evaluator:author_job_nonce")
    author_row = payload.get("author")
    if (
        author_row
        != {
            "command_sha256": author.command_sha256,
            "pid": author.pid,
            "job_quiescent": True,
        }
        or not author.job_quiescent
    ):
        failures.add("evaluator:author_process_receipt")
    if payload.get("immutable_source_snapshot_sha256") != immutable_snapshot_sha256:
        failures.add("evaluator:immutable_snapshot_digest")
    if payload.get("candidate") != {
        "path": str(candidate.resolve()),
        "bytes": int(candidate.stat().st_size),
        "sha256": candidate_sha256,
    }:
        failures.add("evaluator:candidate_binding")
    evaluator_record = contract["authorized_implementation"]["runtime_dependencies"]["r7_evaluator"]
    evaluator = ROOT / str(evaluator_record["path"])
    if payload.get("evaluator") != {
        "pid": evaluator_tree.pid,
        "path": str(evaluator.resolve()),
        "bytes": int(evaluator_record["bytes"]),
        "sha256": str(evaluator_record["sha256"]),
    } or not evaluator_tree.job_quiescent:
        failures.add("evaluator:process_tree_receipt")
    if payload.get("dependency_bundle_sha256") != dependency_bundle_sha256:
        failures.add("evaluator:dependency_bundle")
    if payload.get("truth") != {
        "fresh_process": True,
        "stdout_anonymous_pipe_only": True,
        "writable_result_path_used": False,
    }:
        failures.add("evaluator:truth")
    artifact = payload.get("artifact_result")
    failures |= {
        "evaluator:" + name for name in validate_artifact_evaluation_result(artifact)
    }
    return failures


def _process_evidence_record(value: ProcessTreeEvidence) -> dict[str, object]:
    return {
        "pid": value.pid,
        "command_sha256": value.command_sha256,
        "returncode": value.returncode,
        "job_nonce": value.job_nonce,
        "job_signaled": value.job_signaled,
        "active_processes_after_wait": value.active_processes_after_wait,
    }


def _make_gate_result(
    schema: str,
    dependency_bundle_sha256: str,
    controller_pid: int,
    failure_names: Sequence[str],
    *,
    eligible: bool = False,
    derived: Mapping[str, object] | None = None,
    evaluator_stdout_pipe: bool = False,
) -> dict[str, object]:
    base_derived: dict[str, object] = {
        "controller_pid": controller_pid,
        "dependency_bundle_sha256": dependency_bundle_sha256,
        "candidate_sha256": None,
        "author_process_tree": None,
        "fresh_evaluator_process_tree": None,
        "sealed_controller_process_tree": None,
        "controller_nonce": None,
        "immutable_source_snapshot_sha256": None,
        "sealed_author_command_sha256": None,
        "fresh_evaluator_command_sha256": None,
        "fresh_evaluator_envelope_sha256": None,
    }
    if derived:
        if not set(derived).issubset(base_derived):
            raise R7ProcessProtocolError("unknown R7 derived result field")
        base_derived.update(dict(derived))
    names = sorted(set(str(name) for name in failure_names))
    return {
        "schema": schema,
        "eligible": bool(eligible) and not names,
        "failure_names": names,
        "derived": base_derived,
        "truth": {
            "fresh_sealed_controller_process": True,
            "dependency_leases_required": True,
            "evaluator_stdout_anonymous_pipe": evaluator_stdout_pipe,
            "candidate_accepted": bool(eligible) and not names,
        },
    }


def validate_controller_gate_result(
    payload: object,
    *,
    required_schema: str,
    dependency_bundle_sha256: str,
) -> set[str]:
    failures: set[str] = set()
    if not isinstance(payload, Mapping):
        return {"controller_result:document"}
    if set(payload) != {"schema", "eligible", "failure_names", "derived", "truth"}:
        failures.add("controller_result:exact_fields")
    if payload.get("schema") != required_schema:
        failures.add("controller_result:schema")
    names = payload.get("failure_names")
    if (
        not isinstance(names, (list, tuple))
        or any(not isinstance(name, str) or not name for name in names)
        or list(names) != sorted(set(names))
    ):
        failures.add("controller_result:failure_names")
    if not isinstance(payload.get("eligible"), bool):
        failures.add("controller_result:eligible_type")
    if isinstance(names, (list, tuple)) and bool(payload.get("eligible")) == bool(names):
        failures.add("controller_result:eligibility_consistency")
    derived = payload.get("derived")
    expected_derived = {
        "controller_pid", "dependency_bundle_sha256", "candidate_sha256",
        "author_process_tree", "fresh_evaluator_process_tree",
        "sealed_controller_process_tree", "controller_nonce",
        "immutable_source_snapshot_sha256", "sealed_author_command_sha256",
        "fresh_evaluator_command_sha256", "fresh_evaluator_envelope_sha256",
    }
    if not isinstance(derived, Mapping) or set(derived) != expected_derived:
        failures.add("controller_result:derived_fields")
    else:
        if derived.get("dependency_bundle_sha256") != dependency_bundle_sha256:
            failures.add("controller_result:dependency_bundle")
        if not isinstance(derived.get("controller_pid"), int) or int(derived["controller_pid"]) <= 0:
            failures.add("controller_result:controller_pid")
        for name in (
            "candidate_sha256", "controller_nonce",
            "immutable_source_snapshot_sha256", "sealed_author_command_sha256",
            "fresh_evaluator_command_sha256", "fresh_evaluator_envelope_sha256",
        ):
            value = derived.get(name)
            if value is not None and not re.fullmatch(r"[0-9a-f]{64}", str(value)):
                failures.add(f"controller_result:{name}")
        for name in (
            "author_process_tree", "fresh_evaluator_process_tree",
            "sealed_controller_process_tree",
        ):
            value = derived.get(name)
            if value is not None and (
                not isinstance(value, Mapping)
                or set(value) != {
                    "pid", "command_sha256", "returncode", "job_nonce",
                    "job_signaled", "active_processes_after_wait",
                }
            ):
                failures.add(f"controller_result:{name}")
    truth = payload.get("truth")
    if not isinstance(truth, Mapping) or set(truth) != {
        "fresh_sealed_controller_process", "dependency_leases_required",
        "evaluator_stdout_anonymous_pipe", "candidate_accepted",
    }:
        failures.add("controller_result:truth_fields")
    elif (
        truth.get("fresh_sealed_controller_process") is not True
        or truth.get("dependency_leases_required") is not True
        or truth.get("candidate_accepted") is not payload.get("eligible")
        or not isinstance(truth.get("evaluator_stdout_anonymous_pipe"), bool)
    ):
        failures.add("controller_result:truth_values")
    return failures


def _decode_exact_json_stdout(stdout: bytes, label: str) -> object:
    if len(stdout) > 512 * 1024 * 1024:
        raise R7ProcessProtocolError(f"{label} stdout exceeds sealed bound")
    try:
        text = stdout.decode("utf-8")
        decoder = json.JSONDecoder()
        value, end = decoder.raw_decode(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise R7ProcessProtocolError(f"{label} stdout is not exact JSON") from exc
    if text[end:].strip():
        raise R7ProcessProtocolError(f"{label} stdout has trailing data")
    return value


def execute_from_fresh_controller(
    contract: Mapping[str, object],
    attempt: str,
    blender_executable: Path,
    *,
    dependency_bundle_sha256: str,
    controller_pid: int,
    author_timeout_seconds: int = 1800,
    evaluator_timeout_seconds: int = 1800,
) -> dict[str, object]:
    schema = str(contract["authorized_implementation"]["required_gate_schema"])
    if not re.fullmatch(r"[0-9a-f]{64}", dependency_bundle_sha256) or controller_pid <= 0:
        raise R7ProcessProtocolError("fresh controller evidence is malformed")
    if not contract.get("static_execution_authority"):
        return _make_gate_result(
            schema, dependency_bundle_sha256, controller_pid,
            ["r7_static_execution_authority_not_granted"],
        )
    blender = r4.validate_blender_runtime(blender_executable, contract)
    controller_nonce = secrets.token_hex(32)
    author_job_nonce = secrets.token_hex(32)
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
        ) as author_source_snapshot, tempfile.TemporaryDirectory(
            prefix="kira_r24_r7_author_cache_"
        ) as author_cache:
            command, candidate = _sealed_author_command(
                contract, attempt, controller_nonce, author_job_nonce,
                blender, author_source_snapshot,
            )
            if candidate.exists():
                return _make_gate_result(
                    schema, dependency_bundle_sha256, controller_pid,
                    ["author:candidate_not_fresh"],
                )
            candidate.parent.mkdir(parents=True, exist_ok=False)
            author_command_sha256 = canonical_sha256(command)
            author = _run_sealed_process_tree(
                command,
                expected_command_sha256=author_command_sha256,
                expected_job_nonce=author_job_nonce,
                timeout_seconds=author_timeout_seconds,
                environment=_restricted_child_environment(Path(author_cache)),
            )
            if author.returncode != 0 or not candidate.is_file():
                return _make_gate_result(
                    schema, dependency_bundle_sha256, controller_pid,
                    ["author:sealed_tree_or_candidate"],
                )
            if sha256_file(author_source_snapshot.path) != author_source_snapshot.sha256:
                return _make_gate_result(
                    schema, dependency_bundle_sha256, controller_pid,
                    ["author:source_snapshot_changed"],
                )
        digest = sha256_file(candidate)
        evaluator_command = _fresh_evaluator_command(
            contract, candidate, digest, blender, controller_nonce, author,
            str(contract["exact_source"]["preserved_target_blend_sha256"]),
            dependency_bundle_sha256,
        )
        evaluator_job_nonce = secrets.token_hex(32)
        evaluator_command_sha256 = canonical_sha256(evaluator_command)
        with tempfile.TemporaryDirectory(
            prefix="kira_r24_r7_evaluator_cache_"
        ) as evaluator_cache:
            evaluator_tree = _run_sealed_process_tree(
                evaluator_command,
                expected_command_sha256=evaluator_command_sha256,
                expected_job_nonce=evaluator_job_nonce,
                timeout_seconds=evaluator_timeout_seconds,
                environment=_restricted_child_environment(Path(evaluator_cache)),
            )
        if evaluator_tree.returncode != 0:
            return _make_gate_result(
                schema, dependency_bundle_sha256, controller_pid,
                ["evaluator:fresh_tree"],
            )
        envelope = _decode_exact_json_stdout(evaluator_tree.stdout, "fresh evaluator")
        envelope_failures = validate_fresh_evaluator_envelope(
            envelope,
            contract=contract,
            candidate=candidate,
            candidate_sha256=digest,
            controller_nonce=controller_nonce,
            immutable_snapshot_sha256=str(
                contract["exact_source"]["preserved_target_blend_sha256"]
            ),
            author=author,
            evaluator_tree=evaluator_tree,
            dependency_bundle_sha256=dependency_bundle_sha256,
        )
        if envelope_failures:
            return _make_gate_result(
                schema, dependency_bundle_sha256, controller_pid,
                ["evaluator:narrow_channel_or_schema"],
                evaluator_stdout_pipe=True,
            )
        artifact = envelope["artifact_result"]
        names = list(artifact["failure_names"])
        eligible = bool(artifact["artifact_eligible"]) and not names
        return _make_gate_result(
            schema, dependency_bundle_sha256, controller_pid, names,
            eligible=eligible,
            evaluator_stdout_pipe=True,
            derived={
                "candidate_sha256": digest,
                "author_process_tree": _process_evidence_record(author),
                "fresh_evaluator_process_tree": _process_evidence_record(evaluator_tree),
                "controller_nonce": controller_nonce,
                "immutable_source_snapshot_sha256": str(
                    contract["exact_source"]["preserved_target_blend_sha256"]
                ),
                "sealed_author_command_sha256": author_command_sha256,
                "fresh_evaluator_command_sha256": evaluator_command_sha256,
                "fresh_evaluator_envelope_sha256": canonical_sha256(envelope),
            },
        )
    except (
        OSError, TypeError, ValueError, json.JSONDecodeError,
        R7ProcessProtocolError, R7SnapshotError,
    ):
        return _make_gate_result(
            schema, dependency_bundle_sha256, controller_pid,
            ["sealed_author_fresh_evaluator_protocol_failed"],
        )


def _dependency_bundle_rows(contract: Mapping[str, object]) -> list[dict[str, object]]:
    raw = DEFAULT_CONTRACT.read_bytes()
    rows: list[dict[str, object]] = [
        {
            "role": "contract",
            "path": DEFAULT_CONTRACT.relative_to(ROOT).as_posix(),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    ]
    overlay = json.loads(raw)
    for prefix, records in (
        ("parent", overlay["parent_bindings"]),
        ("runtime", overlay["authorized_implementation"]["runtime_dependencies"]),
    ):
        for role, record in sorted(records.items()):
            rows.append({"role": f"{prefix}:{role}", **dict(record)})
    implementation = overlay["authorized_implementation"]
    for role, record in (
        ("worker", implementation["worker"]),
        ("controller", implementation["sealed_controller"]),
    ):
        path = (ROOT / record["path"]).resolve()
        rows.append(
            {
                "role": role,
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": int(path.stat().st_size),
                "sha256": sha256_file(path),
                "normalized_semantic_sha256": record["normalized_semantic_sha256"],
            }
        )
    rows.append({"role": "focused_test", **dict(implementation["focused_test"])})
    rows.append({"role": "python", **dict(implementation["python_executable"])})
    return rows


def _sealed_controller_command(
    contract: Mapping[str, object], attempt: str, blender: Path
) -> list[str]:
    if not re.fullmatch(r"attempt_[0-9]{2}", attempt):
        raise R7ProcessProtocolError("attempt name is not exact")
    implementation = contract["authorized_implementation"]
    controller_record = implementation["sealed_controller"]
    controller = ROOT / str(controller_record["path"])
    if normalized_sealed_python_sha256(controller) != controller_record["normalized_semantic_sha256"]:
        raise R7ProcessProtocolError("sealed controller identity changed")
    python = r4.validate_absolute_exact_file(implementation["python_executable"])
    return [
        str(python), "-B", str(controller), "--contract", str(DEFAULT_CONTRACT),
        "--attempt", attempt, "--blender", str(blender),
    ]


def validate_sealed_controller_envelope(
    payload: object,
    *,
    contract: Mapping[str, object],
    attempt: str,
    controller_tree: ProcessTreeEvidence,
    dependency_bundle_sha256: str,
) -> set[str]:
    failures: set[str] = set()
    if not isinstance(payload, Mapping):
        return {"sealed_controller:document"}
    if set(payload) != {
        "schema", "contract", "controller", "attempt",
        "dependency_bundle_sha256", "result", "truth",
    }:
        failures.add("sealed_controller:exact_fields")
    if payload.get("schema") != "kira.avatar.r24.r7.sealed_controller_envelope.v1":
        failures.add("sealed_controller:schema")
    raw = DEFAULT_CONTRACT.read_bytes()
    if payload.get("contract") != {
        "path": str(DEFAULT_CONTRACT.resolve()),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "semantic_sha256": SEALED_CONTRACT_SEMANTIC_SHA256,
    }:
        failures.add("sealed_controller:contract")
    controller_record = contract["authorized_implementation"]["sealed_controller"]
    controller = (ROOT / str(controller_record["path"])).resolve()
    if payload.get("controller") != {
        "pid": controller_tree.pid,
        "path": str(controller),
        "bytes": int(controller.stat().st_size),
        "sha256": sha256_file(controller),
        "normalized_semantic_sha256": controller_record["normalized_semantic_sha256"],
    } or not controller_tree.job_quiescent:
        failures.add("sealed_controller:process_or_identity")
    if payload.get("attempt") != attempt:
        failures.add("sealed_controller:attempt")
    if payload.get("dependency_bundle_sha256") != dependency_bundle_sha256:
        failures.add("sealed_controller:dependency_bundle")
    failures |= validate_controller_gate_result(
        payload.get("result"),
        required_schema=str(contract["authorized_implementation"]["required_gate_schema"]),
        dependency_bundle_sha256=dependency_bundle_sha256,
    )
    if payload.get("truth") != {
        "fresh_controller_process": True,
        "contract_recursively_immutable": True,
        "dependency_leases_held_through_result": True,
        "caller_selected_implementation": False,
    }:
        failures.add("sealed_controller:truth")
    return failures


def run_sealed_author_then_fresh_evaluator(
    attempt: str,
    blender_executable: Path,
    *,
    author_timeout_seconds: int = 1800,
    evaluator_timeout_seconds: int = 1800,
) -> dict[str, object]:
    del author_timeout_seconds, evaluator_timeout_seconds
    contract = load_sealed_contract()
    schema = str(contract["authorized_implementation"]["required_gate_schema"])
    try:
        dependency_bundle_sha256 = canonical_sha256(_dependency_bundle_rows(contract))
        command = _sealed_controller_command(contract, attempt, blender_executable)
        command_sha256 = canonical_sha256(command)
        job_nonce = secrets.token_hex(32)
        with tempfile.TemporaryDirectory(
            prefix="kira_r24_r7_controller_cache_"
        ) as cache:
            controller_tree = _run_sealed_process_tree(
                command,
                expected_command_sha256=command_sha256,
                expected_job_nonce=job_nonce,
                timeout_seconds=60,
                environment=_restricted_child_environment(Path(cache)),
            )
        if controller_tree.returncode != 0:
            raise R7ProcessProtocolError("sealed controller exited unsuccessfully")
        envelope = _decode_exact_json_stdout(controller_tree.stdout, "sealed controller")
        failures = validate_sealed_controller_envelope(
            envelope,
            contract=contract,
            attempt=attempt,
            controller_tree=controller_tree,
            dependency_bundle_sha256=dependency_bundle_sha256,
        )
        if failures:
            raise R7ProcessProtocolError(
                "sealed controller envelope failed: " + ",".join(sorted(failures))
            )
        result = deep_thaw(envelope["result"])
        result["derived"]["sealed_controller_process_tree"] = _process_evidence_record(
            controller_tree
        )
        return result
    except (OSError, TypeError, ValueError, R7PackageError, R7ProcessProtocolError):
        return {
            "schema": schema,
            "eligible": False,
            "failure_names": ["fresh_sealed_controller_protocol_failed"],
        }


def _obsolete_pre_audit_run_sealed_author_then_fresh_evaluator(
    attempt: str,
    blender_executable: Path,
    *,
    author_timeout_seconds: int = 1800,
    evaluator_timeout_seconds: int = 1800,
) -> dict[str, object]:
    contract = load_sealed_contract()
    schema = contract["authorized_implementation"]["required_gate_schema"]
    if not contract.get("static_execution_authority"):
        return {"schema": schema, "eligible": False, "failure_names": ["r7_static_execution_authority_not_granted"]}
    blender = r4.validate_blender_runtime(blender_executable, contract)
    controller_nonce = secrets.token_hex(32)
    author_job_nonce = secrets.token_hex(32)
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
                contract, attempt, controller_nonce, author_job_nonce,
                blender, author_source_snapshot
            )
            if candidate.exists():
                return {"schema": schema, "eligible": False, "failure_names": ["author:candidate_not_fresh"]}
            candidate.parent.mkdir(parents=True, exist_ok=False)
            author_command_sha256 = canonical_sha256(command)
            author = _run_sealed_process_tree(
                command,
                expected_command_sha256=author_command_sha256,
                expected_job_nonce=author_job_nonce,
                timeout_seconds=author_timeout_seconds,
                environment=_restricted_child_environment(),
            )
            if author.returncode != 0 or not candidate.is_file():
                return {"schema": schema, "eligible": False, "failure_names": ["author:sealed_tree_or_candidate"]}
            if sha256_file(author_source_snapshot.path) != author_source_snapshot.sha256:
                return {"schema": schema, "eligible": False, "failure_names": ["author:source_snapshot_changed"]}
        digest = sha256_file(candidate)
        with tempfile.TemporaryDirectory(prefix="kira_r24_r7_fresh_eval_") as raw:
            output = Path(raw) / "result.json"
            evaluator_command = _fresh_evaluator_command(
                contract, candidate, digest, blender, controller_nonce,
                author, str(contract["exact_source"]["preserved_target_blend_sha256"]),
                output
            )
            evaluator_job_nonce = secrets.token_hex(32)
            evaluator_command_sha256 = canonical_sha256(evaluator_command)
            evaluator_tree = _run_sealed_process_tree(
                evaluator_command,
                expected_command_sha256=evaluator_command_sha256,
                expected_job_nonce=evaluator_job_nonce,
                timeout_seconds=evaluator_timeout_seconds,
                environment=_restricted_child_environment(),
            )
            if evaluator_tree.returncode != 0 or not output.is_file():
                return {"schema": schema, "eligible": False, "failure_names": ["evaluator:fresh_tree"]}
            envelope = json.loads(output.read_text(encoding="utf-8"))
            envelope_failures = validate_fresh_evaluator_envelope(
                envelope,
                contract=contract,
                candidate=candidate,
                candidate_sha256=digest,
                controller_nonce=controller_nonce,
                immutable_snapshot_sha256=str(
                    contract["exact_source"]["preserved_target_blend_sha256"]
                ),
                author=author,
                evaluator_tree=evaluator_tree,
            )
            if envelope_failures:
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
                    "controller_nonce": controller_nonce,
                    "immutable_source_snapshot_sha256": str(
                        contract["exact_source"]["preserved_target_blend_sha256"]
                    ),
                    "sealed_author_command_sha256": author_command_sha256,
                    "fresh_evaluator_command_sha256": evaluator_command_sha256,
                    "fresh_evaluator_file": copy.deepcopy(
                        contract["authorized_implementation"]["fresh_evaluator"]
                    ),
                },
            }
    except (OSError, TypeError, ValueError, json.JSONDecodeError, R7ProcessProtocolError):
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
        "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R7_CONTRACT.json",
        "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R7_PROPOSAL.md",
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
        "schema": "kira.avatar.r24.r7.static_gate_result.v1",
        "status": contract["status"],
        "r5_disposition": "PRESERVED_REJECTED",
        "package_inventory": package_inventory_status(),
        "blender_launched": False,
        "candidate_created": False,
        "execution_authority_granted": False,
        "fresh_independent_r7_audit_required": True,
    }


def main() -> int:
    print(json.dumps(static_evaluation(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
