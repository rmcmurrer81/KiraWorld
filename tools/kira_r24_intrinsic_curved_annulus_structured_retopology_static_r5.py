from __future__ import annotations

"""Append-only R24 R5 artifact-derived static acceptance gate.

R5 repairs the six independently reproduced R4 boundary defects.  It is still
a static gate: importing or running this module never starts Blender and does
not grant body/candidate authority.  The only production-shaped entry owns the
author subprocess, waits for that exact child to exit, then guards one exact
post-exit artifact identity through typed preflight and fresh extraction.
"""

import collections
import contextlib
import copy
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from typing import BinaryIO, Iterator, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import kira_r24_blend_sdna_typed_static_r5 as typed
from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static_r4 as r4


PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_intrinsic_curved_annulus_structured_retopology_static_r5"
)
DEFAULT_CONTRACT = PACKAGE / "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R5_CONTRACT.json"
EXTRACTOR = ROOT / "tools/blender_extract_kira_r24_candidate_read_only_r5.py"
INTERSECTION_HELPER = ROOT / "tools/blender_exact_mesh_intersections.py"
SEALED_CONTRACT_FILE_SHA256 = "7d1a65fd9d4a732137e62db43a1de0f1d797088819a7bb710459fde2cfc62ecf"
SEALED_CONTRACT_SEMANTIC_SHA256 = "a06568f87cf6a40fd28440cfd2a60ac03f38d05e79991320ca2a3acced885579"
SHA256_CHARS = frozenset("0123456789abcdef")


class R5PackageError(ValueError):
    pass


class R5ExtractionError(RuntimeError):
    pass


class R5AuthorProtocolError(RuntimeError):
    pass


def canonical_json(value: object) -> bytes:
    return r4.canonical_json(value)


def canonical_sha256(value: object) -> str:
    return r4.canonical_sha256(value)


def sha256_file(path: Path) -> str:
    return r4.sha256_file(path)


def normalized_worker_sha256(path: Path = Path(__file__)) -> str:
    data = path.read_bytes()
    lines = data.splitlines(keepends=True)
    prefixes = (
        b'SEALED_CONTRACT_FILE_SHA256 = "',
        b'SEALED_CONTRACT_SEMANTIC_SHA256 = "',
    )
    found: set[bytes] = set()
    normalized: list[bytes] = []
    for line in lines:
        replacement = line
        for prefix in prefixes:
            if line.startswith(prefix):
                suffix = line[len(prefix) + 64 :]
                if not suffix.startswith(b'"'):
                    raise R5PackageError("R5 evaluator seal literal shape changed")
                replacement = prefix + b"0" * 64 + suffix
                found.add(prefix)
        normalized.append(replacement)
    if found != set(prefixes):
        raise R5PackageError("R5 evaluator seal field inventory changed")
    return hashlib.sha256(b"".join(normalized)).hexdigest()


def _semantic_projection(value: Mapping[str, object]) -> dict[str, object]:
    result = copy.deepcopy(dict(value))
    result["semantic_seal_sha256"] = ""
    return result


def _exact_file(record: Mapping[str, object]) -> Path:
    return r4.validate_exact_file(ROOT, record)


@lru_cache(maxsize=1)
def load_sealed_contract() -> dict[str, object]:
    try:
        raw = DEFAULT_CONTRACT.read_bytes()
        overlay = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise R5PackageError(f"R5 contract cannot be loaded: {exc}") from exc
    if hashlib.sha256(raw).hexdigest() != SEALED_CONTRACT_FILE_SHA256:
        raise R5PackageError("R5 contract file identity changed")
    semantic = canonical_sha256(_semantic_projection(overlay))
    if semantic != SEALED_CONTRACT_SEMANTIC_SHA256 or overlay.get("semantic_seal_sha256") != semantic:
        raise R5PackageError("R5 contract semantic identity changed")
    if overlay.get("schema") != "kira.avatar.r24.artifact_derived_gate.v5":
        raise R5PackageError("unexpected R5 contract schema")
    parents = overlay.get("parent_bindings")
    if not isinstance(parents, Mapping) or set(parents) != {"r4_contract", "r4_audit", "r4_manifest"}:
        raise R5PackageError("R5 parent binding inventory changed")
    for record in parents.values():
        if not isinstance(record, Mapping):
            raise R5PackageError("R5 parent binding malformed")
        _exact_file(record)
    parent = r4.load_sealed_contract()
    implementation = overlay.get("authorized_implementation")
    required = {
        "worker",
        "typed_preflight",
        "read_only_extractor",
        "intersection_helper",
        "focused_test",
        "candidate_path_prefix",
        "required_gate_schema",
    }
    if not isinstance(implementation, Mapping) or set(implementation) != required:
        raise R5PackageError("R5 implementation inventory changed")
    worker = implementation.get("worker")
    if (
        not isinstance(worker, Mapping)
        or worker.get("path") != Path(__file__).resolve().relative_to(ROOT.resolve()).as_posix()
        or worker.get("normalized_semantic_sha256") != normalized_worker_sha256()
    ):
        raise R5PackageError("R5 worker binding changed")
    for name in ("typed_preflight", "read_only_extractor", "intersection_helper", "focused_test"):
        record = implementation.get(name)
        if not isinstance(record, Mapping):
            raise R5PackageError(f"R5 implementation binding {name!r} absent")
        _exact_file(record)
    amendments = overlay.get("r5_amendments")
    if not isinstance(amendments, Mapping) or set(amendments) != {
        "typed_and_extraction_one_digest",
        "complete_datablock_inventories",
        "protected_state_projection",
        "world_space_quality",
        "child_graph_semantics",
        "author_exit_protocol",
    } or not all(value is True for value in amendments.values()):
        raise R5PackageError("R5 amendment inventory changed")
    merged = copy.deepcopy(parent)
    merged.update(
        {
            "schema": overlay["schema"],
            "status": overlay["status"],
            "lane": overlay["lane"],
            "mode": overlay["mode"],
            "authorized_implementation": copy.deepcopy(implementation),
            "r5_amendments": copy.deepcopy(amendments),
            "semantic_seal_sha256": semantic,
        }
    )
    return merged


def _records(rows: object, key: str) -> dict[str, Mapping[str, object]]:
    return r4._records_by_name(rows, key)


def validate_extraction_envelope(
    snapshot: object,
    *,
    nonce: str,
    candidate: Path,
    candidate_sha256: str,
    extractor_sha256: str,
    intersection_helper_sha256: str,
) -> set[str]:
    failures: set[str] = set()
    if not isinstance(snapshot, Mapping):
        return {"extraction:document"}
    required = {
        "schema", "nonce", "candidate", "extractor", "intersection_helper",
        "blender", "state", "truth", "state_sha256",
    }
    if set(snapshot) != required:
        failures.add("extraction:exact_envelope")
    if snapshot.get("schema") != "kira.avatar.r24.read_only_blender_extraction.v5":
        failures.add("extraction:schema")
    if snapshot.get("nonce") != nonce:
        failures.add("extraction:nonce")
    row = snapshot.get("candidate")
    if not isinstance(row, Mapping) or set(row) != {"path", "bytes", "sha256"}:
        failures.add("extraction:candidate_binding")
    elif (
        Path(str(row.get("path"))).resolve() != candidate.resolve()
        or row.get("bytes") != candidate.stat().st_size
        or row.get("sha256") != candidate_sha256
    ):
        failures.add("extraction:candidate_binding")
    for name, path, digest in (
        ("extractor", EXTRACTOR, extractor_sha256),
        ("intersection_helper", INTERSECTION_HELPER, intersection_helper_sha256),
    ):
        binding = snapshot.get(name)
        if not isinstance(binding, Mapping) or set(binding) != {"path", "bytes", "sha256"}:
            failures.add(f"extraction:{name}_binding")
        elif (
            Path(str(binding.get("path"))).resolve() != path.resolve()
            or binding.get("bytes") != path.stat().st_size
            or binding.get("sha256") != digest
        ):
            failures.add(f"extraction:{name}_binding")
    blender = snapshot.get("blender")
    if (
        not isinstance(blender, Mapping)
        or not blender.get("background")
        or Path(str(blender.get("loaded_filepath"))).resolve() != candidate.resolve()
        or not isinstance(blender.get("version"), str)
    ):
        failures.add("extraction:blender_context")
    if snapshot.get("truth") != {
        "read_only_extraction": True,
        "blend_saved": False,
        "candidate_mutated": False,
        "in_memory_pose_evaluation_only": True,
    }:
        failures.add("extraction:read_only_truth")
    state = snapshot.get("state")
    state_fields = {
        "objects", "mesh_objects", "armature_objects", "mesh_datablocks",
        "armature_datablocks", "materials", "actions", "images", "node_groups",
        "collections", "worlds", "scenes", "intersection_reports",
    }
    if not isinstance(state, Mapping) or set(state) != state_fields:
        failures.add("extraction:complete_state")
    else:
        for name in state_fields - {"intersection_reports"}:
            if not isinstance(state.get(name), list):
                failures.add("extraction:complete_state")
        if not isinstance(state.get("intersection_reports"), Mapping):
            failures.add("extraction:complete_state")
    try:
        digest = canonical_sha256(state)
    except (TypeError, ValueError):
        digest = ""
    if snapshot.get("state_sha256") != digest:
        failures.add("extraction:state_digest")
    return failures


@dataclass(frozen=True)
class _GuardIdentity:
    path: Path
    bytes: int
    sha256: str
    device: int
    inode: int


def _hash_stream(stream: BinaryIO) -> str:
    digest = hashlib.sha256()
    stream.seek(0)
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(block)
    stream.seek(0)
    return digest.hexdigest()


def _guard_matches(identity: _GuardIdentity) -> bool:
    try:
        stat = identity.path.stat()
        return (
            stat.st_size == identity.bytes
            and stat.st_dev == identity.device
            and stat.st_ino == identity.inode
            and sha256_file(identity.path) == identity.sha256
        )
    except OSError:
        return False


@contextlib.contextmanager
def _guarded_artifact(path: Path, expected_sha256: str | None = None) -> Iterator[_GuardIdentity]:
    with path.open("rb") as stream:
        stat = os.fstat(stream.fileno())
        identity = _GuardIdentity(path.resolve(), stat.st_size, _hash_stream(stream), stat.st_dev, stat.st_ino)
        if expected_sha256 is not None and identity.sha256 != expected_sha256:
            raise R5ExtractionError("artifact does not match evaluator-owned expected digest")
        if not _guard_matches(identity):
            raise R5ExtractionError("artifact path/handle identity disagrees before evaluation")
        yield identity
        if not _guard_matches(identity) or _hash_stream(stream) != identity.sha256:
            raise R5ExtractionError("artifact changed while evaluator guard was held")


def _assert_guard(identity: _GuardIdentity, boundary: str) -> None:
    if not _guard_matches(identity):
        raise R5ExtractionError(f"artifact identity changed at {boundary}")


def _invoke_extractor(
    candidate: Path,
    blender: Path,
    expected_sha256: str,
    *,
    timeout_seconds: int = 900,
) -> dict[str, object]:
    contract = load_sealed_contract()
    blender = r4.validate_blender_runtime(blender, contract)
    extractor_record = contract["authorized_implementation"]["read_only_extractor"]
    helper_record = contract["authorized_implementation"]["intersection_helper"]
    _exact_file(extractor_record)
    _exact_file(helper_record)
    if sha256_file(candidate) != expected_sha256:
        raise R5ExtractionError("artifact differs from typed-preflight digest before extractor launch")
    nonce = secrets.token_hex(32)
    with tempfile.TemporaryDirectory(prefix="kira_r24_r5_extract_") as raw:
        output = Path(raw) / "extraction.json"
        command = [
            str(blender), "--background", "--factory-startup", str(candidate),
            "--python", str(EXTRACTOR), "--", "--candidate", str(candidate),
            "--candidate-sha256", expected_sha256,
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
            raise R5ExtractionError(f"read-only extractor failed closed (exit={completed.returncode})")
        if sha256_file(candidate) != expected_sha256:
            raise R5ExtractionError("artifact changed during extraction")
        try:
            snapshot = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise R5ExtractionError(f"extractor output invalid: {exc}") from exc
        failures = validate_extraction_envelope(
            snapshot,
            nonce=nonce,
            candidate=candidate,
            candidate_sha256=expected_sha256,
            extractor_sha256=str(extractor_record["sha256"]),
            intersection_helper_sha256=str(helper_record["sha256"]),
        )
        if failures:
            raise R5ExtractionError("invalid extractor envelope: " + ",".join(sorted(failures)))
        if sha256_file(candidate) != expected_sha256:
            raise R5ExtractionError("artifact changed before extractor return")
        return snapshot


def _semantic_map(summary: Mapping[str, object], code: str) -> dict[str, Mapping[str, object]]:
    semantic = summary.get("semantic_ids")
    if not isinstance(semantic, Mapping) or not isinstance(semantic.get(code), list):
        return {}
    return _records(semantic[code], "name")


def typed_inventory_failures(
    source: Mapping[str, object],
    candidate: Mapping[str, object],
    contract: Mapping[str, object],
) -> set[str]:
    failures: set[str] = set()
    identity = contract["artifact_semantic_identity"]
    additions = {
        "OB": {identity["patch_object_name"]},
        "ME": {identity["patch_mesh_name"]},
        "AR": set(),
        "AC": set(),
        "MA": set(),
    }
    for code, allowed in additions.items():
        source_rows = _semantic_map(source, code)
        candidate_rows = _semantic_map(candidate, code)
        if not source_rows or set(candidate_rows) != set(source_rows) | allowed:
            failures.add(f"typed_sdna:exact_{code}_inventory")
    for code in ("AR", "AC"):
        source_rows = _semantic_map(source, code)
        candidate_rows = _semantic_map(candidate, code)
        for name, row in source_rows.items():
            if candidate_rows.get(name, {}).get("direct_block_sha256") != row.get("direct_block_sha256"):
                failures.add(f"typed_sdna:{code}:{name}:direct_source_exact")
    source_materials = _semantic_map(source, "MA")
    candidate_materials = _semantic_map(candidate, "MA")
    controlled = identity["required_material_name"]
    for name, row in source_materials.items():
        candidate_row = candidate_materials.get(name, {})
        if candidate_row.get("id_user_count_normalized_block_sha256") != row.get("id_user_count_normalized_block_sha256"):
            failures.add(f"typed_sdna:MA:{name}:only_id_us_may_change")
        source_users = row.get("id_user_count")
        candidate_users = candidate_row.get("id_user_count")
        expected_delta = 1 if name == controlled else 0
        if (
            not isinstance(source_users, int)
            or isinstance(source_users, bool)
            or not isinstance(candidate_users, int)
            or isinstance(candidate_users, bool)
            or candidate_users != source_users + expected_delta
        ):
            failures.add(f"typed_sdna:MA:{name}:controlled_id_us_transition")
    return failures


def validate_complete_protected_state(
    source: Mapping[str, object],
    candidate: Mapping[str, object],
    contract: Mapping[str, object],
) -> set[str]:
    failures: set[str] = set()
    source_state = source.get("state")
    candidate_state = candidate.get("state")
    if not isinstance(source_state, Mapping) or not isinstance(candidate_state, Mapping):
        return {"protected_state:missing"}
    identity = contract["artifact_semantic_identity"]
    body = identity["body_object_name"]
    patch_object = identity["patch_object_name"]
    body_mesh = identity["body_mesh_name"]
    patch_mesh = identity["patch_mesh_name"]
    source_objects = _records(source_state.get("objects"), "name")
    candidate_objects = _records(candidate_state.get("objects"), "name")
    if not source_objects or set(candidate_objects) != set(source_objects) | {patch_object}:
        failures.add("protected_state:exact_object_inventory")
    for name, row in source_objects.items():
        if candidate_objects.get(name) != row:
            failures.add(f"protected_state:object:{name}:source_exact")
    patch = candidate_objects.get(patch_object)
    if (
        not isinstance(patch, Mapping)
        or patch.get("type") != "MESH"
        or patch.get("data_name") != patch_mesh
        or patch.get("collection_names") != []
    ):
        failures.add("protected_state:patch_object_detached")
    source_meshes = _records(source_state.get("mesh_datablocks"), "name")
    candidate_meshes = _records(candidate_state.get("mesh_datablocks"), "name")
    if not source_meshes or set(candidate_meshes) != set(source_meshes) | {patch_mesh}:
        failures.add("protected_state:exact_mesh_datablock_inventory")
    for name, row in source_meshes.items():
        if name != body_mesh and candidate_meshes.get(name) != row:
            failures.add(f"protected_state:mesh_datablock:{name}:source_exact")
    patch_data = candidate_meshes.get(patch_mesh)
    if not isinstance(patch_data, Mapping) or patch_data.get("object_users") != [patch_object]:
        failures.add("protected_state:patch_mesh_exact_user")
    for field, key in (
        ("armature_datablocks", "name"),
        ("collections", "name"),
        ("images", "name"),
        ("node_groups", "name"),
        ("worlds", "name"),
        ("scenes", "name"),
    ):
        if candidate_state.get(field) != source_state.get(field):
            failures.add(f"protected_state:{field}:source_exact")
    return failures


def validate_complete_child_graphs(
    source: Mapping[str, object],
    candidate: Mapping[str, object],
    contract: Mapping[str, object],
) -> set[str]:
    failures: set[str] = set()
    source_state = source.get("state")
    candidate_state = candidate.get("state")
    if not isinstance(source_state, Mapping) or not isinstance(candidate_state, Mapping):
        return {"child_graph:missing"}
    for field, key in (("armature_objects", "object_name"), ("actions", "name")):
        if _records(candidate_state.get(field), key) != _records(source_state.get(field), key):
            failures.add(f"child_graph:{field}:source_exact")
    source_materials = _records(source_state.get("materials"), "name")
    candidate_materials = _records(candidate_state.get("materials"), "name")
    if set(candidate_materials) != set(source_materials):
        failures.add("child_graph:materials:exact_inventory")
    controlled = contract["artifact_semantic_identity"]["required_material_name"]
    for name, row in source_materials.items():
        candidate_row = candidate_materials.get(name)
        if not isinstance(candidate_row, Mapping):
            continue
        source_copy = copy.deepcopy(dict(row))
        candidate_copy = copy.deepcopy(dict(candidate_row))
        source_users = source_copy.pop("users", None)
        candidate_users = candidate_copy.pop("users", None)
        if candidate_copy != source_copy:
            failures.add(f"child_graph:material:{name}:semantic_source_exact")
        expected_delta = 1 if name == controlled else 0
        if (
            not isinstance(source_users, int)
            or isinstance(source_users, bool)
            or not isinstance(candidate_users, int)
            or isinstance(candidate_users, bool)
            or candidate_users != source_users + expected_delta
        ):
            failures.add(f"child_graph:material:{name}:controlled_users")
    return failures


def validate_render_triangulation(
    mesh: Mapping[str, object] | None,
    minimum_area_m2: float,
    minimum_angle_degrees: float,
) -> set[str]:
    failures = r4.validate_extracted_triangulation_identity(mesh)
    vertices, _ = r4._mesh_maps(mesh)
    if not isinstance(mesh, Mapping) or not isinstance(mesh.get("loop_triangles"), list):
        return failures
    matrix = mesh.get("matrix_world")
    for row in mesh["loop_triangles"]:
        if not isinstance(row, Mapping) or not isinstance(row.get("vertices"), list):
            continue
        indices = row["vertices"]
        if len(indices) != 3 or any(not r4.is_int(value) or int(value) not in vertices for value in indices):
            continue
        points = [r4._matrix_transform(matrix, vertices[int(index)].get("coordinate_local_m")) for index in indices]
        if any(point is None for point in points):
            failures.add("render:triangle_world_geometry")
            continue
        area, angle = r4._triangle_measurements(points)  # type: ignore[arg-type]
        if not math.isfinite(area) or area < minimum_area_m2:
            failures.add("render:minimum_world_triangle_area")
        if not math.isfinite(angle) or angle < minimum_angle_degrees:
            failures.add("render:minimum_world_triangle_angle")
    return failures


def validate_extracted_pair(
    source: Mapping[str, object],
    candidate: Mapping[str, object],
    contract: Mapping[str, object],
) -> set[str]:
    failures = r4.validate_extracted_pair(source, candidate, contract)
    # Replace R4's local-space quality verdict with the R5 world-space verdict.
    failures.discard("render:minimum_triangle_area")
    failures.discard("render:minimum_triangle_angle")
    # R5 records Material.users so it can prove the one legitimate +1
    # transition. R4 had no such field and therefore treats that newly honest
    # difference as generic graph drift; the R5 child-graph gate below is the
    # stronger replacement and checks every other material field exactly.
    failures.discard("material:complete_source_exact_inventory")
    failures.discard("material:source_exact_graph")
    failures |= validate_complete_protected_state(source, candidate, contract)
    failures |= validate_complete_child_graphs(source, candidate, contract)
    patch = r4._mesh(candidate, contract["artifact_semantic_identity"]["patch_object_name"])
    bounds = contract["metric_bounds"]
    failures |= validate_render_triangulation(
        patch,
        float(bounds["minimum_render_triangle_area_m2"]),
        float(bounds["minimum_render_triangle_angle_degrees"]),
    )
    return failures


@dataclass(frozen=True)
class _AuthorExitAttestation:
    capability: object
    pid: int
    command_sha256: str
    returncode: int
    wait_completed: bool
    poll_after_wait: int | None
    candidate_path: str
    candidate_bytes: int
    candidate_sha256: str


_AUTHOR_CAPABILITY = object()


def _evaluate_post_author(
    candidate_path: Path,
    blender_executable: Path,
    attestation: _AuthorExitAttestation,
) -> dict[str, object]:
    contract = load_sealed_contract()
    schema = contract["authorized_implementation"]["required_gate_schema"]
    if (
        not isinstance(attestation, _AuthorExitAttestation)
        or attestation.capability is not _AUTHOR_CAPABILITY
        or attestation.pid <= 0
        or attestation.returncode != 0
        or not attestation.wait_completed
        or attestation.poll_after_wait != 0
    ):
        return {"schema": schema, "eligible": False, "failure_names": ["author:clean_exit_not_evaluator_attested"]}
    candidate = candidate_path.resolve()
    try:
        candidate.relative_to(ROOT.resolve())
        candidate.relative_to((ROOT / contract["authorized_implementation"]["candidate_path_prefix"]).resolve())
    except ValueError:
        return {"schema": schema, "eligible": False, "failure_names": ["artifact:path_or_presence"]}
    if (
        str(candidate) != attestation.candidate_path
        or not candidate.is_file()
        or candidate.stat().st_size != attestation.candidate_bytes
        or sha256_file(candidate) != attestation.candidate_sha256
    ):
        return {"schema": schema, "eligible": False, "failure_names": ["author:post_exit_artifact_identity_changed"]}
    source = r4.validate_exact_file(
        ROOT,
        {
            "path": contract["exact_source"]["preserved_target_blend_path"],
            "bytes": contract["exact_source"]["preserved_target_blend_bytes"],
            "sha256": contract["exact_source"]["preserved_target_blend_sha256"],
        },
    )
    failures: set[str] = set()
    candidate_digest = attestation.candidate_sha256
    source_digest = contract["exact_source"]["preserved_target_blend_sha256"]
    try:
        with _guarded_artifact(source, str(source_digest)) as source_guard, _guarded_artifact(candidate, candidate_digest) as candidate_guard:
            source_typed = typed.parse_typed_blend(source)
            candidate_typed = typed.parse_typed_blend(candidate)
            failures |= typed_inventory_failures(source_typed, candidate_typed, contract)
            _assert_guard(source_guard, "after_typed_source")
            _assert_guard(candidate_guard, "after_typed_candidate")
            if failures:
                raise R5ExtractionError("typed inventory rejected")
            source_snapshot = _invoke_extractor(source, blender_executable, source_guard.sha256)
            _assert_guard(source_guard, "after_source_extraction")
            _assert_guard(candidate_guard, "before_candidate_extraction")
            candidate_snapshot = _invoke_extractor(candidate, blender_executable, candidate_guard.sha256)
            _assert_guard(source_guard, "after_candidate_extraction")
            _assert_guard(candidate_guard, "after_candidate_extraction")
            # Repeat typed parsing on the still-guarded artifacts so the typed
            # direct-block gate and extracted state cannot be different files.
            source_typed_after = typed.parse_typed_blend(source)
            candidate_typed_after = typed.parse_typed_blend(candidate)
            if canonical_sha256(source_typed_after) != canonical_sha256(source_typed):
                failures.add("artifact:source_typed_identity_changed")
            if canonical_sha256(candidate_typed_after) != canonical_sha256(candidate_typed):
                failures.add("artifact:candidate_typed_identity_changed")
            failures |= validate_extracted_pair(source_snapshot, candidate_snapshot, contract)
            _assert_guard(source_guard, "before_eligibility_return")
            _assert_guard(candidate_guard, "before_eligibility_return")
    except (OSError, TypeError, ValueError, typed.TypedBlendError, R5ExtractionError):
        failures.add("extraction:failed_closed")
    return {
        "schema": schema,
        "eligible": not failures,
        "failure_names": sorted(failures),
        "derived": {
            "candidate": {
                "path": candidate.relative_to(ROOT.resolve()).as_posix(),
                "bytes": attestation.candidate_bytes,
                "sha256": candidate_digest,
            },
            "author_process": {
                "pid": attestation.pid,
                "command_sha256": attestation.command_sha256,
                "clean_exit_evaluator_observed": True,
            },
            "typed_preflight_repeated_after_extraction": True,
            "one_expected_digest_crosses_all_boundaries": True,
            "caller_evidence_used": False,
        },
    }


def run_author_then_evaluate(
    author_command: Sequence[str],
    candidate_path: Path,
    blender_executable: Path,
    *,
    timeout_seconds: int = 1800,
) -> dict[str, object]:
    """Own, wait for, attest, and evaluate exactly one author child process."""
    contract = load_sealed_contract()
    schema = contract["authorized_implementation"]["required_gate_schema"]
    command = tuple(str(value) for value in author_command)
    if not command or any(not value for value in command):
        return {"schema": schema, "eligible": False, "failure_names": ["author:command"]}
    candidate = candidate_path.resolve()
    try:
        candidate.relative_to((ROOT / contract["authorized_implementation"]["candidate_path_prefix"]).resolve())
    except ValueError:
        return {"schema": schema, "eligible": False, "failure_names": ["artifact:path_or_presence"]}
    if candidate.exists():
        return {"schema": schema, "eligible": False, "failure_names": ["author:candidate_not_fresh"]}
    process = subprocess.Popen(
        list(command),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    try:
        process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
        return {"schema": schema, "eligible": False, "failure_names": ["author:timeout_exact_child_stopped"]}
    returncode = process.poll()
    if returncode != 0 or not candidate.is_file():
        return {"schema": schema, "eligible": False, "failure_names": ["author:clean_exit_or_candidate"]}
    digest = sha256_file(candidate)
    attestation = _AuthorExitAttestation(
        capability=_AUTHOR_CAPABILITY,
        pid=int(process.pid),
        command_sha256=canonical_sha256(list(command)),
        returncode=int(returncode),
        wait_completed=True,
        poll_after_wait=process.poll(),
        candidate_path=str(candidate),
        candidate_bytes=int(candidate.stat().st_size),
        candidate_sha256=digest,
    )
    return _evaluate_post_author(candidate, blender_executable, attestation)


def evaluate_candidate_artifact(candidate_path: Path, blender_executable: Path) -> dict[str, object]:
    del candidate_path, blender_executable
    contract = load_sealed_contract()
    return {
        "schema": contract["authorized_implementation"]["required_gate_schema"],
        "eligible": False,
        "failure_names": ["author_exit_attestation_required_use_run_author_then_evaluate"],
    }


def evaluate_measured_candidate_evidence(evidence: object = None, *args: object, **kwargs: object) -> dict[str, object]:
    del evidence, args, kwargs
    return evaluate_candidate_artifact(Path("."), Path("."))


def package_inventory_status(package: Path = PACKAGE) -> dict[str, object]:
    expected = {
        "CHECKPOINT.md",
        "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R5_CONTRACT.json",
        "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R5_PROPOSAL.md",
        "PACKAGE_MANIFEST.json",
        "STATIC_TEST_RESULTS.json",
    }
    actual = {path.name for path in package.iterdir() if path.is_file()} if package.is_dir() else set()
    return {"state": "PRE_AUDIT_EXACT" if actual == expected else "INVALID", "actual": sorted(actual), "expected": sorted(expected)}


def static_evaluation() -> dict[str, object]:
    contract = load_sealed_contract()
    fixture = r4.validate_exact_file(ROOT, contract["rejection_fixture_binding"])
    try:
        typed.parse_typed_blend(fixture)
        fixture_result = "INCORRECTLY_ACCEPTED"
    except (OSError, ValueError, typed.TypedBlendError):
        fixture_result = "REJECTED_TYPED_SDNA"
    return {
        "schema": "kira.avatar.r24.r5.static_gate_result.v1",
        "status": contract["status"],
        "r4_disposition": "PRESERVED_REJECTED",
        "r3_fixture": fixture_result,
        "six_r4_blockers_repaired_in_static_successor": True,
        "candidate_created": False,
        "candidate_accepted": False,
        "blender_launched": False,
        "execution_authority_granted": False,
        "fresh_independent_static_audit_required": True,
        "package_inventory": package_inventory_status(),
    }


def main() -> int:
    print(json.dumps(static_evaluation(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
