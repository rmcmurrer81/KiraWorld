from __future__ import annotations

"""R24 R4 artifact-derived acceptance gate.

R4 has no API that can accept a caller-authored evidence JSON document.  A
future bounded run supplies only an artifact path and a Blender executable;
this evaluator type-checks the Blend, creates private extraction nonces, runs
the exact sealed read-only extractor against the sealed source and candidate,
and computes acceptance from those extracted states.
"""

import copy
import collections
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
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import kira_r24_blend_sdna_typed_static_r4 as typed
from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static_r3 as r3


PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_intrinsic_curved_annulus_structured_retopology_static_r4"
)
DEFAULT_CONTRACT = PACKAGE / "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R4_CONTRACT.json"
EXTRACTOR = ROOT / "tools/blender_extract_kira_r24_candidate_read_only_r4.py"
INTERSECTION_HELPER = ROOT / "tools/blender_exact_mesh_intersections.py"
SEALED_CONTRACT_FILE_SHA256 = "f22ecd500092b83825b61fb22111d5dca4820889566c45012d883bfedb77f5d4"
SEALED_CONTRACT_SEMANTIC_SHA256 = "f6f930b206a70c91869a41994bac5a859810277236d6826ba319bbb2ee729d35"
SHA256_CHARS = frozenset("0123456789abcdef")
PROVENANCE_ATTRIBUTE_NAMES = {
    "r24_source_face",
    "r24_barycentric",
    "r24_displacement_local_m",
}


class R4PackageError(ValueError):
    """The append-only R4 package or an exact binding changed."""


class R4ExtractionError(RuntimeError):
    """The evaluator-owned read-only extraction did not complete exactly."""


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_worker_sha256(path: Path = Path(__file__)) -> str:
    data = path.read_bytes()
    lines = data.splitlines(keepends=True)
    found: set[bytes] = set()
    normalized: list[bytes] = []
    prefixes = (
        b'SEALED_CONTRACT_FILE_SHA256 = "',
        b'SEALED_CONTRACT_SEMANTIC_SHA256 = "',
    )
    for line in lines:
        replaced = line
        for prefix in prefixes:
            if line.startswith(prefix):
                suffix = line[len(prefix) + 64 :]
                if not suffix.startswith(b'"'):
                    raise R4PackageError("R4 evaluator seal literal shape changed")
                replaced = prefix + b"0" * 64 + suffix
                found.add(prefix)
        normalized.append(replaced)
    if found != set(prefixes):
        raise R4PackageError("R4 evaluator seal field inventory changed")
    return hashlib.sha256(b"".join(normalized)).hexdigest()


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= SHA256_CHARS


def is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def finite_vector(value: object, length: int) -> bool:
    return isinstance(value, list) and len(value) == length and all(finite(item) for item in value)


def vector_close(first: Sequence[object], second: Sequence[object], tolerance: float = 1e-8) -> bool:
    return len(first) == len(second) and all(
        finite(a) and finite(b) and math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=tolerance)
        for a, b in zip(first, second, strict=True)
    )


def resolve_project_path(root: Path, raw: object) -> Path:
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute():
        raise ValueError("path must be nonempty and project-relative")
    path = (root / raw).resolve()
    path.relative_to(root.resolve())
    return path


def validate_exact_file(root: Path, record: Mapping[str, object]) -> Path:
    path = resolve_project_path(root, record.get("path"))
    if not path.is_file():
        raise ValueError("bound file is absent")
    if not is_int(record.get("bytes")) or int(record["bytes"]) != path.stat().st_size:
        raise ValueError("bound byte count changed")
    if not is_sha256(record.get("sha256")) or record["sha256"] != sha256_file(path):
        raise ValueError("bound SHA-256 changed")
    return path


def validate_absolute_exact_file(record: Mapping[str, object]) -> Path:
    raw = record.get("path")
    if not isinstance(raw, str) or not Path(raw).is_absolute():
        raise ValueError("absolute bound path is invalid")
    path = Path(raw).resolve()
    if not path.is_file():
        raise ValueError("absolute bound file is absent")
    if not is_int(record.get("bytes")) or int(record["bytes"]) != path.stat().st_size:
        raise ValueError("absolute bound byte count changed")
    if not is_sha256(record.get("sha256")) or record["sha256"] != sha256_file(path):
        raise ValueError("absolute bound SHA-256 changed")
    return path


def validate_blender_runtime(blender: Path, contract: Mapping[str, object]) -> Path:
    runtime = contract.get("authorized_runtime")
    if not isinstance(runtime, Mapping) or set(runtime) != {"blender_executable", "required_version"}:
        raise R4PackageError("authorized runtime binding is not exact")
    record = runtime.get("blender_executable")
    if not isinstance(record, Mapping):
        raise R4PackageError("Blender executable binding is absent")
    expected = validate_absolute_exact_file(record)
    if blender.resolve() != expected:
        raise R4ExtractionError("caller-selected Blender is not the sealed executable")
    return expected


def _semantic_projection(contract: Mapping[str, object]) -> dict[str, object]:
    result = copy.deepcopy(dict(contract))
    result["semantic_seal_sha256"] = ""
    return result


@lru_cache(maxsize=1)
def load_sealed_contract() -> dict[str, object]:
    try:
        raw = DEFAULT_CONTRACT.read_bytes()
        contract = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise R4PackageError(f"R4 contract cannot be loaded: {exc}") from exc
    if hashlib.sha256(raw).hexdigest() != SEALED_CONTRACT_FILE_SHA256:
        raise R4PackageError("R4 contract file identity changed")
    semantic = canonical_sha256(_semantic_projection(contract))
    if semantic != SEALED_CONTRACT_SEMANTIC_SHA256 or contract.get("semantic_seal_sha256") != semantic:
        raise R4PackageError("R4 contract semantic identity changed")
    if contract.get("schema") != "kira.avatar.r24.artifact_derived_gate.v4":
        raise R4PackageError("unexpected R4 contract schema")
    parent_bindings = contract.get("parent_bindings")
    required_parents = {
        "r3_contract",
        "r3_proposal",
        "r3_checkpoint",
        "r3_manifest",
        "r3_evaluator",
        "r3_test",
        "r3_rejection_audit",
        "r3_rejection_checkpoint",
        "r3_reproducer",
        "r3_reproduction",
    }
    if not isinstance(parent_bindings, Mapping) or set(parent_bindings) != required_parents:
        raise R4PackageError("R4 parent binding inventory is not exact")
    for name, record in parent_bindings.items():
        if not isinstance(record, Mapping):
            raise R4PackageError(f"parent binding {name!r} is malformed")
        try:
            validate_exact_file(ROOT, record)
        except (OSError, TypeError, ValueError) as exc:
            raise R4PackageError(f"parent binding {name!r} changed: {exc}") from exc
    implementation = contract.get("authorized_implementation")
    if not isinstance(implementation, Mapping) or set(implementation) != {
        "worker",
        "typed_preflight",
        "read_only_extractor",
        "intersection_helper",
        "focused_test",
        "candidate_path_prefix",
        "required_gate_schema",
    }:
        raise R4PackageError("authorized implementation is absent")
    worker = implementation.get("worker")
    if (
        not isinstance(worker, Mapping)
        or worker.get("path") != Path(__file__).resolve().relative_to(ROOT.resolve()).as_posix()
        or worker.get("normalized_semantic_sha256") != normalized_worker_sha256()
    ):
        raise R4PackageError("implementation binding 'worker' changed")
    for key in ("typed_preflight", "read_only_extractor", "intersection_helper", "focused_test"):
        record = implementation.get(key)
        if not isinstance(record, Mapping):
            raise R4PackageError(f"implementation binding {key!r} is absent")
        try:
            validate_exact_file(ROOT, record)
        except (OSError, TypeError, ValueError) as exc:
            raise R4PackageError(f"implementation binding {key!r} changed: {exc}") from exc
    bounds = contract.get("metric_bounds")
    if not isinstance(bounds, Mapping):
        raise R4PackageError("metric bounds absent")
    if (
        not finite(bounds.get("minimum_render_triangle_angle_degrees"))
        or float(bounds["minimum_render_triangle_angle_degrees"]) != 12.0
        or not finite(bounds.get("minimum_render_triangle_area_m2"))
        or float(bounds["minimum_render_triangle_area_m2"]) != 1e-10
        or not is_int(bounds.get("maximum_new_interior_vertices"))
        or bounds["maximum_new_interior_vertices"] != 160
        or not finite(bounds.get("maximum_world_displacement_m"))
        or float(bounds["maximum_world_displacement_m"]) != 0.012
    ):
        raise R4PackageError("R4 metric bounds changed")
    provenance = contract.get("candidate_owned_vertex_provenance")
    if provenance != {
        "source_face": {
            "name": "r24_source_face",
            "domain": "POINT",
            "data_type": "INT",
        },
        "barycentric": {
            "name": "r24_barycentric",
            "domain": "POINT",
            "data_type": "FLOAT_VECTOR",
        },
        "displacement": {
            "name": "r24_displacement_local_m",
            "domain": "POINT",
            "data_type": "FLOAT_VECTOR",
        },
        "barycentric_tolerance": 1e-8,
        "coordinate_binding_tolerance_m": 1e-7,
        "boundary_zero_displacement_tolerance_m": 1e-10,
    }:
        raise R4PackageError("candidate-owned vertex provenance contract changed")
    try:
        validate_blender_runtime(
            Path(str(contract["authorized_runtime"]["blender_executable"]["path"])),
            contract,
        )
    except (OSError, TypeError, ValueError, R4ExtractionError) as exc:
        raise R4PackageError(f"sealed Blender runtime changed: {exc}") from exc
    return contract


def _records_by_name(rows: object, name_key: str) -> dict[str, Mapping[str, object]]:
    if not isinstance(rows, list):
        return {}
    result: dict[str, Mapping[str, object]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get(name_key), str) or row[name_key] in result:
            return {}
        result[str(row[name_key])] = row
    return result


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
        "schema",
        "nonce",
        "candidate",
        "extractor",
        "intersection_helper",
        "blender",
        "state",
        "truth",
        "state_sha256",
    }
    if set(snapshot) != required:
        failures.add("extraction:exact_envelope")
    if snapshot.get("schema") != "kira.avatar.r24.read_only_blender_extraction.v4":
        failures.add("extraction:schema")
    if snapshot.get("nonce") != nonce:
        failures.add("extraction:nonce")
    candidate_row = snapshot.get("candidate")
    if not isinstance(candidate_row, Mapping) or set(candidate_row) != {"path", "bytes", "sha256"}:
        failures.add("extraction:candidate_binding")
    elif (
        Path(str(candidate_row.get("path"))).resolve() != candidate.resolve()
        or candidate_row.get("bytes") != candidate.stat().st_size
        or candidate_row.get("sha256") != candidate_sha256
    ):
        failures.add("extraction:candidate_binding")
    extractor_row = snapshot.get("extractor")
    if not isinstance(extractor_row, Mapping) or set(extractor_row) != {"path", "bytes", "sha256"}:
        failures.add("extraction:extractor_binding")
    elif (
        Path(str(extractor_row.get("path"))).resolve() != EXTRACTOR.resolve()
        or extractor_row.get("bytes") != EXTRACTOR.stat().st_size
        or extractor_row.get("sha256") != extractor_sha256
    ):
        failures.add("extraction:extractor_binding")
    helper_row = snapshot.get("intersection_helper")
    if not isinstance(helper_row, Mapping) or set(helper_row) != {"path", "bytes", "sha256"}:
        failures.add("extraction:intersection_helper_binding")
    elif (
        Path(str(helper_row.get("path"))).resolve() != INTERSECTION_HELPER.resolve()
        or helper_row.get("bytes") != INTERSECTION_HELPER.stat().st_size
        or helper_row.get("sha256") != intersection_helper_sha256
    ):
        failures.add("extraction:intersection_helper_binding")
    blender = snapshot.get("blender")
    if (
        not isinstance(blender, Mapping)
        or not blender.get("background")
        or Path(str(blender.get("loaded_filepath"))).resolve() != candidate.resolve()
        or not isinstance(blender.get("version"), str)
    ):
        failures.add("extraction:blender_context")
    truth = snapshot.get("truth")
    if truth != {
        "read_only_extraction": True,
        "blend_saved": False,
        "candidate_mutated": False,
        "in_memory_pose_evaluation_only": True,
    }:
        failures.add("extraction:read_only_truth")
    state = snapshot.get("state")
    required_state = {
        "objects",
        "mesh_objects",
        "armature_objects",
        "materials",
        "actions",
        "intersection_reports",
        "scenes",
    }
    if not isinstance(state, Mapping) or set(state) != required_state:
        failures.add("extraction:complete_state")
    else:
        for key in required_state - {"intersection_reports"}:
            if not isinstance(state.get(key), list):
                failures.add("extraction:complete_state")
        if not isinstance(state.get("intersection_reports"), Mapping):
            failures.add("extraction:complete_state")
    try:
        state_hash = canonical_sha256(snapshot.get("state"))
    except (TypeError, ValueError):
        state_hash = ""
    if snapshot.get("state_sha256") != state_hash:
        failures.add("extraction:state_digest")
    return failures


def _invoke_extractor(candidate: Path, blender: Path, timeout_seconds: int = 900) -> dict[str, object]:
    contract = load_sealed_contract()
    blender = validate_blender_runtime(blender, contract)
    extractor_record = contract["authorized_implementation"]["read_only_extractor"]
    helper_record = contract["authorized_implementation"]["intersection_helper"]
    validate_exact_file(ROOT, extractor_record)
    validate_exact_file(ROOT, helper_record)
    candidate_before = sha256_file(candidate)
    nonce = secrets.token_hex(32)
    with tempfile.TemporaryDirectory(prefix="kira_r24_r4_extract_") as raw:
        output = Path(raw) / "extraction.json"
        command = [
            str(blender),
            "--background",
            "--factory-startup",
            str(candidate),
            "--python",
            str(EXTRACTOR),
            "--",
            "--candidate",
            str(candidate),
            "--candidate-sha256",
            candidate_before,
            "--extractor-sha256",
            str(extractor_record["sha256"]),
            "--intersection-helper-sha256",
            str(helper_record["sha256"]),
            "--nonce",
            nonce,
            "--output",
            str(output),
        ]
        child_environment = os.environ.copy()
        for name in (
            "PYTHONHOME",
            "PYTHONPATH",
            "PYTHONSTARTUP",
            "BLENDER_USER_SCRIPTS",
            "BLENDER_SYSTEM_SCRIPTS",
        ):
            child_environment.pop(name, None)
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
            shell=False,
            env=child_environment,
        )
        if completed.returncode != 0 or not output.is_file() or output.stat().st_size > 512 * 1024 * 1024:
            raise R4ExtractionError(
                f"read-only extractor failed closed (exit={completed.returncode}, output={output.is_file()})"
            )
        if sha256_file(candidate) != candidate_before:
            raise R4ExtractionError("candidate changed during read-only extraction")
        try:
            snapshot = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise R4ExtractionError(f"extractor output is not exact JSON: {exc}") from exc
        failures = validate_extraction_envelope(
            snapshot,
            nonce=nonce,
            candidate=candidate,
            candidate_sha256=candidate_before,
            extractor_sha256=str(extractor_record["sha256"]),
            intersection_helper_sha256=str(helper_record["sha256"]),
        )
        if failures:
            raise R4ExtractionError("invalid extractor envelope: " + ",".join(sorted(failures)))
        return snapshot


def _mesh(snapshot: Mapping[str, object], object_name: str) -> Mapping[str, object] | None:
    state = snapshot.get("state")
    if not isinstance(state, Mapping):
        return None
    return _records_by_name(state.get("mesh_objects"), "object_name").get(object_name)


def _armature(snapshot: Mapping[str, object], object_name: str) -> Mapping[str, object] | None:
    state = snapshot.get("state")
    if not isinstance(state, Mapping):
        return None
    return _records_by_name(state.get("armature_objects"), "object_name").get(object_name)


def _mesh_maps(mesh: Mapping[str, object] | None) -> tuple[dict[int, Mapping[str, object]], dict[int, Mapping[str, object]]]:
    if not isinstance(mesh, Mapping):
        return {}, {}
    vertices = {
        int(row["index"]): row
        for row in mesh.get("vertices", [])
        if isinstance(row, Mapping) and is_int(row.get("index"))
    }
    polygons = {
        int(row["index"]): row
        for row in mesh.get("polygons", [])
        if isinstance(row, Mapping) and is_int(row.get("index"))
    }
    return vertices, polygons


def validate_object_links(snapshot: Mapping[str, object], contract: Mapping[str, object]) -> set[str]:
    failures: set[str] = set()
    state = snapshot.get("state")
    if not isinstance(state, Mapping):
        return {"artifact_state:missing"}
    objects = _records_by_name(state.get("objects"), "name")
    identity = contract["artifact_semantic_identity"]
    for name, expected in identity["required_objects"].items():
        row = objects.get(name)
        if not isinstance(row, Mapping) or row.get("type") != expected["type"] or row.get("data_name") != expected["data_name"]:
            failures.add(f"object_link:{name}")
    rig_name = contract["rig_and_action_requirements"]["required_armature_name"]
    for object_name in identity["armature_modified_mesh_objects"]:
        mesh = _mesh(snapshot, object_name)
        modifiers = mesh.get("modifiers") if isinstance(mesh, Mapping) else None
        if not isinstance(modifiers, list) or not any(
            isinstance(row, Mapping) and row.get("type") == "ARMATURE" and row.get("object") == rig_name
            for row in modifiers
        ):
            failures.add(f"object_link:{object_name}:armature_modifier")
    return failures


def validate_protected_object_inventory(
    source: Mapping[str, object], candidate: Mapping[str, object], contract: Mapping[str, object]
) -> set[str]:
    failures: set[str] = set()
    source_state = source.get("state")
    candidate_state = candidate.get("state")
    if not isinstance(source_state, Mapping) or not isinstance(candidate_state, Mapping):
        return {"object_inventory:state_missing"}
    source_objects = _records_by_name(source_state.get("objects"), "name")
    candidate_objects = _records_by_name(candidate_state.get("objects"), "name")
    patch_name = contract["artifact_semantic_identity"]["patch_object_name"]
    if not source_objects or set(candidate_objects) != set(source_objects) | {patch_name}:
        failures.add("object_inventory:exact_name_set")
    mutable = {
        contract["artifact_semantic_identity"]["body_object_name"],
        patch_name,
    }
    for name, row in source_objects.items():
        if name not in mutable and candidate_objects.get(name) != row:
            failures.add(f"object_inventory:{name}:source_exact")
    if candidate_state.get("scenes") != source_state.get("scenes"):
        failures.add("object_inventory:scene_links_source_exact_patch_unlinked")
    return failures


def validate_preserved_rig_actions_material(
    source: Mapping[str, object], candidate: Mapping[str, object], contract: Mapping[str, object]
) -> set[str]:
    failures: set[str] = set()
    rig_name = contract["rig_and_action_requirements"]["required_armature_name"]
    source_rig = _armature(source, rig_name)
    candidate_rig = _armature(candidate, rig_name)
    if source_rig is None or candidate_rig != source_rig:
        failures.add("rig:source_exact_armature_state")
    source_state = source.get("state")
    candidate_state = candidate.get("state")
    if not isinstance(source_state, Mapping) or not isinstance(candidate_state, Mapping):
        return failures | {"state:missing"}
    source_armatures = _records_by_name(source_state.get("armature_objects"), "object_name")
    candidate_armatures = _records_by_name(candidate_state.get("armature_objects"), "object_name")
    if not source_armatures or candidate_armatures != source_armatures:
        failures.add("rig:complete_source_exact_armature_inventory")
    source_actions = _records_by_name(source_state.get("actions"), "name")
    candidate_actions = _records_by_name(candidate_state.get("actions"), "name")
    if not source_actions or candidate_actions != source_actions:
        failures.add("actions:complete_source_exact_inventory")
    for name in contract["rig_and_action_requirements"]["required_action_names"]:
        if name not in source_actions or candidate_actions.get(name) != source_actions[name]:
            failures.add(f"actions:{name}:source_exact")
    material_name = contract["artifact_semantic_identity"]["required_material_name"]
    source_materials = _records_by_name(source_state.get("materials"), "name")
    candidate_materials = _records_by_name(candidate_state.get("materials"), "name")
    if not source_materials or candidate_materials != source_materials:
        failures.add("material:complete_source_exact_inventory")
    if material_name not in source_materials or candidate_materials.get(material_name) != source_materials[material_name]:
        failures.add("material:source_exact_graph")
    return failures


def _matrix_transform(matrix: object, coordinate: object) -> list[float] | None:
    if (
        not isinstance(matrix, list)
        or len(matrix) != 4
        or any(not finite_vector(row, 4) for row in matrix)
        or not finite_vector(coordinate, 3)
    ):
        return None
    vector = [float(value) for value in coordinate] + [1.0]
    return [sum(float(matrix[row][column]) * vector[column] for column in range(4)) for row in range(3)]


def _uv_layers_by_name(mesh: Mapping[str, object]) -> dict[str, dict[int, object]]:
    result: dict[str, dict[int, object]] = {}
    for layer in mesh.get("uv_layers", []):
        if not isinstance(layer, Mapping) or not isinstance(layer.get("name"), str) or layer["name"] in result:
            return {}
        rows: dict[int, object] = {}
        for item in layer.get("data", []):
            if not isinstance(item, Mapping) or not is_int(item.get("loop_index")) or item["loop_index"] in rows:
                return {}
            rows[int(item["loop_index"])] = item.get("uv")
        result[str(layer["name"])] = rows
    return result


def _face_record(
    mesh: Mapping[str, object],
    polygon: Mapping[str, object],
    *,
    world: bool,
    include_normals: bool,
) -> dict[str, object] | None:
    vertices, _ = _mesh_maps(mesh)
    loops = {
        int(row["index"]): row
        for row in mesh.get("loops", [])
        if isinstance(row, Mapping) and is_int(row.get("index"))
    }
    raw_vertices = polygon.get("vertices")
    raw_loops = polygon.get("loop_indices")
    if (
        not isinstance(raw_vertices, list)
        or not isinstance(raw_loops, list)
        or len(raw_vertices) < 3
        or len(raw_vertices) != len(raw_loops)
        or any(not is_int(value) or value not in vertices for value in raw_vertices)
        or any(not is_int(value) or value not in loops for value in raw_loops)
    ):
        return None
    for vertex_index, loop_index in zip(raw_vertices, raw_loops, strict=True):
        if loops[int(loop_index)].get("vertex_index") != vertex_index:
            return None
    matrix = mesh.get("matrix_world")
    attribute_rows = [row for row in mesh.get("attributes", []) if isinstance(row, Mapping)]

    def domain_attributes(domain: str, index: int) -> list[dict[str, object]] | None:
        rows: list[dict[str, object]] = []
        for attribute in attribute_rows:
            if attribute.get("domain") != domain:
                continue
            data = attribute.get("data")
            if not isinstance(attribute.get("name"), str) or not isinstance(data, list) or index >= len(data):
                return None
            rows.append(
                {
                    "name": attribute["name"],
                    "data_type": attribute.get("data_type"),
                    "value": data[index],
                }
            )
        return sorted(rows, key=lambda row: str(row["name"]))

    point_rows: list[dict[str, object]] = []
    shape_keys = [row for row in mesh.get("shape_keys", []) if isinstance(row, Mapping)]
    for vertex_index in raw_vertices:
        vertex = vertices[int(vertex_index)]
        coordinate = vertex.get("coordinate_local_m")
        output_coordinate = _matrix_transform(matrix, coordinate) if world else coordinate
        if not finite_vector(output_coordinate, 3):
            return None
        shape_rows = []
        for shape in shape_keys:
            coordinates = shape.get("coordinates_local_m")
            if not isinstance(coordinates, list) or int(vertex_index) >= len(coordinates):
                return None
            shaped = _matrix_transform(matrix, coordinates[int(vertex_index)]) if world else coordinates[int(vertex_index)]
            if not finite_vector(shaped, 3):
                return None
            shape_rows.append({"name": shape.get("name"), "coordinate_m": shaped})
        point_row = {
            "coordinate_m": output_coordinate,
            "groups": vertex.get("groups"),
            "shape_keys": shape_rows,
            "attributes": domain_attributes("POINT", int(vertex_index)),
        }
        if point_row["attributes"] is None:
            return None
        if include_normals:
            point_row["normal_local"] = vertex.get("normal_local")
        point_rows.append(point_row)
    layers = _uv_layers_by_name(mesh)
    uv_rows: list[dict[str, object]] = []
    for loop_index in raw_loops:
        corner_attributes = domain_attributes("CORNER", int(loop_index))
        if corner_attributes is None:
            return None
        uv_rows.append(
            {
                "loop_layers": [
                    {"name": name, "uv": layers[name].get(int(loop_index))}
                    for name in sorted(layers)
                ],
                "attributes": corner_attributes,
            }
        )
    material_index = polygon.get("material_index")
    materials = mesh.get("materials")
    material_name = None
    if isinstance(materials, list) and is_int(material_index) and 0 <= int(material_index) < len(materials):
        material_name = materials[int(material_index)]
    polygon_index = polygon.get("index")
    face_attributes = domain_attributes("FACE", int(polygon_index)) if is_int(polygon_index) else None
    if face_attributes is None:
        return None
    edge_by_vertices = {
        _canonical_edge(int(row["vertices"][0]), int(row["vertices"][1])): int(row["index"])
        for row in mesh.get("edges", [])
        if isinstance(row, Mapping)
        and is_int(row.get("index"))
        and isinstance(row.get("vertices"), list)
        and len(row["vertices"]) == 2
        and all(is_int(value) for value in row["vertices"])
    }
    edge_rows: list[dict[str, object]] = []
    if mesh.get("edges") is not None:
        for offset, first in enumerate(raw_vertices):
            second = raw_vertices[(offset + 1) % len(raw_vertices)]
            edge_index = edge_by_vertices.get(_canonical_edge(int(first), int(second)))
            if edge_index is None:
                return None
            attributes = domain_attributes("EDGE", edge_index)
            if attributes is None:
                return None
            edge_rows.append({"attributes": attributes})
    return {
        "points_in_winding": point_rows,
        "edges_in_winding": edge_rows,
        "corners_in_winding": uv_rows,
        "face_attributes": face_attributes,
        "material_name": material_name,
        "use_smooth": polygon.get("use_smooth"),
    }


def _face_record_counter(
    mesh: Mapping[str, object] | None,
    face_indices: set[int] | None = None,
    *,
    world: bool,
    include_normals: bool = True,
) -> tuple[collections.Counter[str], set[str]]:
    failures: set[str] = set()
    _, polygons = _mesh_maps(mesh)
    if not isinstance(mesh, Mapping):
        return collections.Counter(), {"protected_body:mesh_missing"}
    requested = set(polygons) if face_indices is None else set(face_indices)
    if not requested.issubset(polygons):
        failures.add("protected_body:source_face_index_binding")
    counter: collections.Counter[str] = collections.Counter()
    for index in sorted(requested & set(polygons)):
        record = _face_record(
            mesh,
            polygons[index],
            world=world,
            include_normals=include_normals,
        )
        if record is None:
            failures.add("protected_body:malformed_extracted_face")
            continue
        counter[canonical_json(record).decode("ascii")] += 1
    return counter, failures


def _without_r24_provenance_attributes(mesh: Mapping[str, object] | None) -> Mapping[str, object] | None:
    if not isinstance(mesh, Mapping):
        return None
    result = dict(mesh)
    result["attributes"] = [
        row
        for row in mesh.get("attributes", [])
        if isinstance(row, Mapping) and row.get("name") not in PROVENANCE_ATTRIBUTE_NAMES
    ]
    return result


def _source_corner_signature(
    source_mesh: Mapping[str, object], bone_names: Sequence[str], vertex_index: int
) -> dict[str, object]:
    joints = source_mesh.get("joints")
    weights = source_mesh.get("weights")
    positions = source_mesh.get("positions")
    normals = source_mesh.get("normals")
    texcoords = source_mesh.get("texcoords")
    if not all(isinstance(value, list) for value in (joints, weights, positions, normals, texcoords)):
        raise R4PackageError("licensed source vertex arrays are incomplete")
    try:
        groups = [
            {"name": str(bone_names[int(joint)]), "weight": float(weight)}
            for joint, weight in zip(joints[vertex_index], weights[vertex_index], strict=True)
            if float(weight) > 0.0
        ]
        return {
            "coordinate_local_m": list(positions[vertex_index]),
            "normal_local": list(normals[vertex_index]),
            "uv": list(texcoords[vertex_index]),
            "groups": sorted(groups, key=lambda row: str(row["name"])),
        }
    except (IndexError, TypeError, ValueError) as exc:
        raise R4PackageError("licensed source vertex record is malformed") from exc


def _canonical_winding_records(records: Sequence[Mapping[str, object]]) -> str:
    if not records:
        return ""
    encoded = [canonical_json(dict(record)).decode("ascii") for record in records]
    rotations = [encoded[index:] + encoded[:index] for index in range(len(encoded))]
    return canonical_json(min(rotations)).decode("ascii")


def _source_face_signature(
    source_mesh: Mapping[str, object], bone_names: Sequence[str], face_index: int
) -> str:
    faces = source_mesh.get("faces")
    if not isinstance(faces, list) or face_index < 0 or face_index >= len(faces):
        raise R4PackageError("licensed source face index is invalid")
    face = faces[face_index]
    if not isinstance(face, list) or len(face) != 3 or any(not is_int(value) for value in face):
        raise R4PackageError("licensed source face is not one exact triangle")
    return _canonical_winding_records(
        [_source_corner_signature(source_mesh, bone_names, int(index)) for index in face]
    )


def _candidate_face_signature(
    mesh: Mapping[str, object], polygon: Mapping[str, object]
) -> str | None:
    vertices, _ = _mesh_maps(mesh)
    loops = {
        int(row["index"]): row
        for row in mesh.get("loops", [])
        if isinstance(row, Mapping) and is_int(row.get("index"))
    }
    layers = [row for row in mesh.get("uv_layers", []) if isinstance(row, Mapping) and row.get("active_render")]
    if len(layers) != 1:
        return None
    uv_data = {
        int(row["loop_index"]): row.get("uv")
        for row in layers[0].get("data", [])
        if isinstance(row, Mapping) and is_int(row.get("loop_index"))
    }
    raw_vertices = polygon.get("vertices")
    raw_loops = polygon.get("loop_indices")
    if (
        not isinstance(raw_vertices, list)
        or len(raw_vertices) != 3
        or not isinstance(raw_loops, list)
        or len(raw_loops) != 3
    ):
        return None
    records: list[dict[str, object]] = []
    for vertex_index, loop_index in zip(raw_vertices, raw_loops, strict=True):
        if not is_int(vertex_index) or not is_int(loop_index):
            return None
        vertex = vertices.get(int(vertex_index))
        loop = loops.get(int(loop_index))
        uv = uv_data.get(int(loop_index))
        if (
            not isinstance(vertex, Mapping)
            or not isinstance(loop, Mapping)
            or loop.get("vertex_index") != vertex_index
            or not finite_vector(vertex.get("coordinate_local_m"), 3)
            or not finite_vector(vertex.get("normal_local"), 3)
            or not finite_vector(uv, 2)
        ):
            return None
        groups = vertex.get("groups")
        if not isinstance(groups, list) or any(
            not isinstance(row, Mapping)
            or not isinstance(row.get("name"), str)
            or not finite(row.get("weight"))
            for row in groups
        ):
            return None
        records.append(
            {
                "coordinate_local_m": list(vertex["coordinate_local_m"]),
                "normal_local": list(vertex["normal_local"]),
                "uv": list(uv),
                "groups": sorted(
                    [
                        {"name": str(row["name"]), "weight": float(row["weight"])}
                        for row in groups
                        if float(row["weight"]) > 0.0
                    ],
                    key=lambda row: str(row["name"]),
                ),
            }
        )
    return _canonical_winding_records(records)


def _subset_mesh(mesh: Mapping[str, object], selected_faces: set[int]) -> dict[str, object] | None:
    """Return an evaluator-owned, reindexed view of selected extracted faces."""
    vertices, polygons = _mesh_maps(mesh)
    if not selected_faces or not selected_faces.issubset(polygons):
        return None
    selected_polygons = [polygons[index] for index in sorted(selected_faces)]
    used_vertices = sorted(
        {
            int(value)
            for polygon in selected_polygons
            for value in polygon.get("vertices", [])
            if is_int(value)
        }
    )
    if any(
        not isinstance(polygon.get("vertices"), list)
        or len(polygon.get("vertices", [])) < 3
        or any(int(value) not in vertices for value in polygon.get("vertices", []))
        for polygon in selected_polygons
    ):
        return None
    vertex_map = {old: new for new, old in enumerate(used_vertices)}
    loop_rows = {
        int(row["index"]): row
        for row in mesh.get("loops", [])
        if isinstance(row, Mapping) and is_int(row.get("index"))
    }
    selected_loops: list[int] = []
    for polygon in selected_polygons:
        raw = polygon.get("loop_indices")
        if not isinstance(raw, list) or len(raw) != len(polygon["vertices"]):
            return None
        selected_loops.extend(int(value) for value in raw if is_int(value))
    if len(selected_loops) != sum(len(polygon["vertices"]) for polygon in selected_polygons):
        return None
    if len(set(selected_loops)) != len(selected_loops) or any(index not in loop_rows for index in selected_loops):
        return None
    loop_map = {old: new for new, old in enumerate(selected_loops)}
    edge_rows = {
        _canonical_edge(int(row["vertices"][0]), int(row["vertices"][1])): row
        for row in mesh.get("edges", [])
        if isinstance(row, Mapping)
        and isinstance(row.get("vertices"), list)
        and len(row["vertices"]) == 2
        and all(is_int(value) for value in row["vertices"])
    }
    required_edges: list[tuple[int, int]] = []
    for polygon in selected_polygons:
        raw = [int(value) for value in polygon["vertices"]]
        for offset, first in enumerate(raw):
            edge = _canonical_edge(first, raw[(offset + 1) % len(raw)])
            if edge not in required_edges:
                required_edges.append(edge)
    if any(edge not in edge_rows for edge in required_edges):
        return None
    edge_map = {edge: index for index, edge in enumerate(required_edges)}
    polygon_map = {old: new for new, old in enumerate(sorted(selected_faces))}

    def subset_attribute(row: Mapping[str, object]) -> dict[str, object] | None:
        domain = row.get("domain")
        indices = {
            "POINT": used_vertices,
            "EDGE": [int(edge_rows[edge]["index"]) for edge in required_edges],
            "FACE": sorted(selected_faces),
            "CORNER": selected_loops,
        }.get(str(domain))
        data = row.get("data")
        if indices is None or not isinstance(data, list) or any(index < 0 or index >= len(data) for index in indices):
            return None
        return {**dict(row), "data": [copy.deepcopy(data[index]) for index in indices]}

    attributes: list[dict[str, object]] = []
    for row in mesh.get("attributes", []):
        if not isinstance(row, Mapping):
            return None
        subset = subset_attribute(row)
        if subset is None:
            return None
        attributes.append(subset)
    layers: list[dict[str, object]] = []
    for layer in mesh.get("uv_layers", []):
        if not isinstance(layer, Mapping):
            return None
        by_loop = {
            int(row["loop_index"]): row
            for row in layer.get("data", [])
            if isinstance(row, Mapping) and is_int(row.get("loop_index"))
        }
        if any(index not in by_loop for index in selected_loops):
            return None
        layers.append(
            {
                **{key: copy.deepcopy(value) for key, value in layer.items() if key != "data"},
                "data": [
                    {**dict(by_loop[old]), "loop_index": loop_map[old]}
                    for old in selected_loops
                ],
            }
        )
    shape_keys = []
    for row in mesh.get("shape_keys", []):
        if not isinstance(row, Mapping) or not isinstance(row.get("coordinates_local_m"), list):
            return None
        coordinates = row["coordinates_local_m"]
        if any(index >= len(coordinates) for index in used_vertices):
            return None
        shape_keys.append(
            {
                **{key: copy.deepcopy(value) for key, value in row.items() if key != "coordinates_local_m"},
                "coordinates_local_m": [copy.deepcopy(coordinates[index]) for index in used_vertices],
            }
        )
    triangles = []
    for row in mesh.get("loop_triangles", []):
        if not isinstance(row, Mapping) or row.get("polygon_index") not in selected_faces:
            continue
        raw_vertices = row.get("vertices")
        raw_loops = row.get("loops")
        if (
            not isinstance(raw_vertices, list)
            or not isinstance(raw_loops, list)
            or len(raw_vertices) != 3
            or len(raw_loops) != 3
            or any(int(value) not in vertex_map for value in raw_vertices)
            or any(int(value) not in loop_map for value in raw_loops)
        ):
            return None
        triangles.append(
            {
                **dict(row),
                "index": len(triangles),
                "polygon_index": polygon_map[int(row["polygon_index"])],
                "vertices": [vertex_map[int(value)] for value in raw_vertices],
                "loops": [loop_map[int(value)] for value in raw_loops],
            }
        )
    result = {
        key: copy.deepcopy(value)
        for key, value in mesh.items()
        if key not in {"vertices", "edges", "polygons", "loops", "uv_layers", "attributes", "shape_keys", "loop_triangles"}
    }
    result.update(
        {
            "vertices": [
                {**dict(vertices[old]), "index": vertex_map[old]}
                for old in used_vertices
            ],
            "edges": [
                {
                    **dict(edge_rows[edge]),
                    "index": edge_map[edge],
                    "vertices": [vertex_map[edge[0]], vertex_map[edge[1]]],
                }
                for edge in required_edges
            ],
            "polygons": [
                {
                    **dict(polygons[old]),
                    "index": polygon_map[old],
                    "vertices": [vertex_map[int(value)] for value in polygons[old]["vertices"]],
                    "loop_indices": [loop_map[int(value)] for value in polygons[old]["loop_indices"]],
                }
                for old in sorted(selected_faces)
            ],
            "loops": [
                {
                    **dict(loop_rows[old]),
                    "index": loop_map[old],
                    "vertex_index": vertex_map[int(loop_rows[old]["vertex_index"])],
                }
                for old in selected_loops
            ],
            "uv_layers": layers,
            "attributes": attributes,
            "shape_keys": shape_keys,
            "loop_triangles": triangles,
        }
    )
    return result


def derive_repaired_estar_patch(
    complete_patch: Mapping[str, object] | None,
    context: Mapping[str, object],
    contract: Mapping[str, object],
) -> tuple[set[str], Mapping[str, object] | None]:
    """Prove the licensed outside-E* surface and return only the new E* disk."""
    failures: set[str] = set()
    if not isinstance(complete_patch, Mapping):
        return {"scope:complete_patch_missing"}, None
    vertices, polygons = _mesh_maps(complete_patch)
    loops = {
        int(row["index"]): row
        for row in complete_patch.get("loops", [])
        if isinstance(row, Mapping) and is_int(row.get("index"))
    }
    used_vertices = {
        int(value)
        for polygon in polygons.values()
        for value in polygon.get("vertices", [])
        if is_int(value)
    }
    used_loops = {
        int(value)
        for polygon in polygons.values()
        for value in polygon.get("loop_indices", [])
        if is_int(value)
    }
    edge_keys = {
        _canonical_edge(int(value), int(raw[(offset + 1) % len(raw)]))
        for polygon in polygons.values()
        for raw in [polygon.get("vertices", [])]
        if isinstance(raw, list) and len(raw) >= 3
        for offset, value in enumerate(raw)
        if is_int(value) and is_int(raw[(offset + 1) % len(raw)])
    }
    extracted_edge_keys = {
        _canonical_edge(int(row["vertices"][0]), int(row["vertices"][1]))
        for row in complete_patch.get("edges", [])
        if isinstance(row, Mapping)
        and isinstance(row.get("vertices"), list)
        and len(row["vertices"]) == 2
        and all(is_int(value) for value in row["vertices"])
    }
    if set(vertices) != used_vertices or set(loops) != used_loops or edge_keys != extracted_edge_keys:
        failures.add("scope:complete_patch_has_hidden_or_partial_geometry")
    layers = [row for row in complete_patch.get("uv_layers", []) if isinstance(row, Mapping) and row.get("active_render")]
    if len(layers) != 1 or {
        int(row["loop_index"])
        for row in layers[0].get("data", [])
        if isinstance(row, Mapping) and is_int(row.get("loop_index"))
    } != set(loops):
        failures.add("scope:complete_patch_uv_coverage")
    materials = complete_patch.get("materials")
    required_material = contract["artifact_semantic_identity"]["required_material_name"]
    if not isinstance(materials, list) or materials.count(required_material) != 1:
        failures.add("scope:complete_patch_material")
    else:
        slot = materials.index(required_material)
        if any(row.get("material_index") != slot for row in polygons.values()):
            failures.add("scope:complete_patch_material")

    source_mesh = context["source_mesh"]
    bone_names = context["bone_names"]
    outside = set(context["domains"]["outside"])
    expected_count = int(contract["exact_topology"]["outside_face_count"])
    if len(outside) != expected_count:
        raise R4PackageError("sealed outside-E* domain count changed")
    expected_by_index = {
        int(index): _source_face_signature(source_mesh, bone_names, int(index))
        for index in sorted(outside)
    }
    malformed = False
    for index, signature in expected_by_index.items():
        polygon = polygons.get(index)
        actual = _candidate_face_signature(complete_patch, polygon) if isinstance(polygon, Mapping) else None
        if actual is None:
            malformed = True
        if actual != signature:
            failures.add("scope:all_1275_licensed_faces_outside_estar_exact")
    if malformed:
        failures.add("scope:malformed_extracted_face")
    repaired_faces = set(polygons) - outside
    if not outside.issubset(polygons):
        failures.add("scope:all_1275_licensed_faces_outside_estar_exact")
    if len(set(polygons) & outside) != expected_count:
        failures.add("scope:outside_estar_exact_face_count")
    if not repaired_faces:
        failures.add("scope:replacement_estar_nonempty")
        return failures, None
    source_estar = collections.Counter(
        _source_face_signature(source_mesh, bone_names, int(index))
        for index in sorted(context["domains"]["estar"])
    )
    repaired_signatures = collections.Counter(
        signature
        for index in repaired_faces
        for signature in [_candidate_face_signature(complete_patch, polygons[index])]
        if signature is not None
    )
    if source_estar & repaired_signatures:
        failures.add("scope:consumed_estar_faces_not_reused")
    outside_signatures = set(expected_by_index.values())
    if any(signature in outside_signatures for signature in repaired_signatures):
        failures.add("scope:licensed_outside_faces_not_duplicated")
    subset = _subset_mesh(complete_patch, repaired_faces)
    if subset is None:
        failures.add("scope:repaired_estar_extraction")
    return failures, subset


def _canonical_cycle(values: Sequence[int]) -> tuple[int, ...]:
    if not values:
        return ()
    rotations = [tuple(values[index:]) + tuple(values[:index]) for index in range(len(values))]
    return min(rotations)


def _material_face_indices(mesh: Mapping[str, object] | None, material_name: str) -> set[int]:
    if not isinstance(mesh, Mapping) or not isinstance(mesh.get("materials"), list):
        return set()
    slots = [index for index, value in enumerate(mesh["materials"]) if value == material_name]
    if len(slots) != 1:
        return set()
    _, polygons = _mesh_maps(mesh)
    return {
        index
        for index, row in polygons.items()
        if row.get("material_index") == slots[0]
    }


def _global_material_interface_records(
    mesh: Mapping[str, object] | None, material_name: str
) -> list[dict[str, object]] | None:
    if not isinstance(mesh, Mapping):
        return None
    patch_faces = _material_face_indices(mesh, material_name)
    vertices, polygons = _mesh_maps(mesh)
    if not patch_faces or not vertices or not polygons:
        return None
    edge_owners: dict[tuple[int, int], list[bool]] = {}
    for index, polygon in polygons.items():
        raw = polygon.get("vertices")
        if not isinstance(raw, list) or len(raw) < 3:
            return None
        values = [int(value) for value in raw]
        for offset, first in enumerate(values):
            edge_owners.setdefault(_canonical_edge(first, values[(offset + 1) % len(values)]), []).append(
                index in patch_faces
            )
    boundary_vertices = sorted(
        {
            value
            for edge, owners in edge_owners.items()
            if any(owners) and not all(owners)
            for value in edge
        }
    )
    records: list[dict[str, object]] = []
    for index in boundary_vertices:
        row = vertices.get(index)
        if not isinstance(row, Mapping):
            return None
        records.append(
            {
                "coordinate_local_m": row.get("coordinate_local_m"),
                "normal_local": row.get("normal_local"),
                "groups": row.get("groups"),
            }
        )
    return sorted(records, key=lambda row: canonical_json(row))


def validate_complete_protected_scene(
    source: Mapping[str, object], candidate: Mapping[str, object], contract: Mapping[str, object]
) -> set[str]:
    failures: set[str] = set()
    source_state = source.get("state")
    candidate_state = candidate.get("state")
    if not isinstance(source_state, Mapping) or not isinstance(candidate_state, Mapping):
        return {"protected_scene:missing"}
    body_name = contract["artifact_semantic_identity"]["body_object_name"]
    patch_name = contract["artifact_semantic_identity"]["patch_object_name"]
    source_meshes = _records_by_name(source_state.get("mesh_objects"), "object_name")
    candidate_meshes = _records_by_name(candidate_state.get("mesh_objects"), "object_name")
    if set(candidate_meshes) != set(source_meshes) | {patch_name}:
        failures.add("protected_scene:mesh_object_inventory")
    for name, row in source_meshes.items():
        if name != body_name and candidate_meshes.get(name) != row:
            failures.add(f"protected_scene:mesh:{name}:source_exact")
    source_objects = _records_by_name(source_state.get("objects"), "name")
    candidate_objects = _records_by_name(candidate_state.get("objects"), "name")
    if set(candidate_objects) != set(source_objects) | {patch_name}:
        failures.add("protected_scene:object_inventory")
    for name, row in source_objects.items():
        if name != body_name and candidate_objects.get(name) != row:
            failures.add(f"protected_scene:object:{name}:source_exact")
    if source_state.get("scenes") != candidate_state.get("scenes"):
        failures.add("protected_scene:scene_membership")
    return failures


def validate_interface_and_protected_body(
    source: Mapping[str, object],
    candidate: Mapping[str, object],
    contract: Mapping[str, object],
    outside_face_indices: set[int],
) -> set[str]:
    del outside_face_indices
    failures: set[str] = set()
    body_name = contract["artifact_semantic_identity"]["body_object_name"]
    material_name = contract["artifact_semantic_identity"]["required_material_name"]
    source_mesh = _mesh(source, body_name)
    candidate_mesh = _mesh(candidate, body_name)
    if not isinstance(source_mesh, Mapping) or not isinstance(candidate_mesh, Mapping):
        return {"protected_body:mesh_missing"}
    for key in (
        "object_name",
        "mesh_name",
        "parent_name",
        "matrix_world",
        "modifiers",
        "materials",
        "shape_keys",
    ):
        if candidate_mesh.get(key) != source_mesh.get(key):
            failures.add(f"protected_body:{key}:source_exact")
    _, source_polygons = _mesh_maps(source_mesh)
    _, candidate_polygons = _mesh_maps(candidate_mesh)
    source_patch_faces = _material_face_indices(source_mesh, material_name)
    candidate_patch_faces = _material_face_indices(candidate_mesh, material_name)
    if not source_patch_faces or not candidate_patch_faces:
        failures.add("protected_body:one_patch_material_region")
    source_records, source_failures = _face_record_counter(
        source_mesh, set(source_polygons) - source_patch_faces, world=False
    )
    candidate_records, candidate_failures = _face_record_counter(
        candidate_mesh, set(candidate_polygons) - candidate_patch_faces, world=False
    )
    failures |= source_failures | candidate_failures
    if candidate_records != source_records:
        failures.add("protected_body:outside_face_topology_material")
    source_interface = _global_material_interface_records(source_mesh, material_name)
    candidate_interface = _global_material_interface_records(candidate_mesh, material_name)
    required_count = int(contract["intersection_and_interface_requirements"]["global_interface_vertex_count"])
    if (
        source_interface is None
        or candidate_interface is None
        or len(source_interface) != required_count
        or candidate_interface != source_interface
    ):
        failures.add("interface:exact_extracted_vertex_state")
    return failures


def validate_actual_graft(
    source_snapshot: Mapping[str, object],
    candidate_snapshot: Mapping[str, object],
    contract: Mapping[str, object],
    consumed_face_indices: set[int] | None = None,
) -> set[str]:
    """Prove that the extracted standalone patch is the extracted body graft.

    The comparison is a multiset of world-space face records, not a supplied
    ledger and not a polygon-index assumption.  Every source body face outside
    E* must remain, every residual candidate face must be represented by the
    separately extracted patch, and no original E* face may remain as an
    unaccounted residual.
    """
    failures: set[str] = set()
    identity = contract["artifact_semantic_identity"]
    source_body = _mesh(source_snapshot, identity["body_object_name"])
    candidate_body = _mesh(candidate_snapshot, identity["body_object_name"])
    patch = _mesh(candidate_snapshot, identity["patch_object_name"])
    del consumed_face_indices
    if (
        isinstance(candidate_body, Mapping)
        and isinstance(patch, Mapping)
        and patch.get("matrix_world") != candidate_body.get("matrix_world")
    ):
        failures.add("graft:patch_body_world_transform_exact")
    _, source_polygons = _mesh_maps(source_body)
    material_name = identity["required_material_name"]
    source_replaced = _material_face_indices(source_body, material_name)
    if not source_replaced:
        return {"graft:source_replacement_material_region"}
    protected_indices = set(source_polygons) - source_replaced
    protected, protected_failures = _face_record_counter(
        _without_r24_provenance_attributes(source_body),
        protected_indices,
        world=True,
        include_normals=False,
    )
    candidate_all, candidate_failures = _face_record_counter(
        _without_r24_provenance_attributes(candidate_body),
        None,
        world=True,
        include_normals=False,
    )
    patch_all, patch_failures = _face_record_counter(
        _without_r24_provenance_attributes(patch),
        None,
        world=True,
        include_normals=False,
    )
    failures |= protected_failures | candidate_failures | patch_failures
    residual = candidate_all.copy()
    for record, count in protected.items():
        if residual[record] < count:
            failures.add("graft:all_source_faces_outside_estar_preserved")
            residual[record] = 0
        else:
            residual[record] -= count
    residual += collections.Counter()
    if residual != patch_all:
        failures.add("graft:standalone_patch_equals_body_residual")
    if not patch_all:
        failures.add("graft:nonempty_replacement")
    if isinstance(source_body, Mapping) and isinstance(candidate_body, Mapping):
        immutable_keys = {
            "object_name",
            "mesh_name",
            "parent_name",
            "matrix_world",
            "modifiers",
            "materials",
            "shape_keys",
        }
        if any(candidate_body.get(key) != source_body.get(key) for key in immutable_keys):
            failures.add("graft:body_object_rig_material_shape_state")
    return failures


def _canonical_edge(first: int, second: int) -> tuple[int, int]:
    return (first, second) if first < second else (second, first)


def _components(polygons: list[list[int]]) -> int:
    owners: dict[int, set[int]] = {}
    for index, vertices in enumerate(polygons):
        for vertex in vertices:
            owners.setdefault(vertex, set()).add(index)
    unseen = set(range(len(polygons)))
    count = 0
    while unseen:
        count += 1
        stack = [unseen.pop()]
        while stack:
            current = stack.pop()
            neighbors = set().union(*(owners[value] for value in polygons[current]))
            discovered = neighbors & unseen
            unseen -= discovered
            stack.extend(discovered)
    return count


def validate_patch_topology(
    patch: Mapping[str, object] | None,
    boundary_coordinates: Mapping[int, Sequence[float]],
    boundary_cycle: Sequence[int],
    maximum_new_vertices: int,
    required_material_name: str,
) -> tuple[set[str], dict[int, int]]:
    failures: set[str] = set()
    vertices, polygons_map = _mesh_maps(patch)
    if not vertices or not polygons_map:
        return {"topology:missing_extracted_patch"}, {}
    if set(vertices) != set(range(len(vertices))) or set(polygons_map) != set(range(len(polygons_map))):
        failures.add("topology:contiguous_extracted_indices")
    polygons: list[list[int]] = []
    edge_owners: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for polygon_index in sorted(polygons_map):
        row = polygons_map[polygon_index]
        raw_vertices = row.get("vertices")
        if not isinstance(raw_vertices, list) or len(raw_vertices) < 3 or any(index not in vertices for index in raw_vertices):
            failures.add("topology:polygon_indices")
            continue
        values = [int(value) for value in raw_vertices]
        if len(values) != len(set(values)):
            failures.add("topology:polygon_indices")
            continue
        polygons.append(values)
        for offset, first in enumerate(values):
            second = values[(offset + 1) % len(values)]
            direction = 1 if first < second else -1
            edge_owners.setdefault(_canonical_edge(first, second), []).append((polygon_index, direction))
    if not polygons or any(len(rows) > 2 for rows in edge_owners.values()):
        failures.add("topology:manifold")
    if any(len(rows) == 2 and rows[0][1] == rows[1][1] for rows in edge_owners.values()):
        failures.add("topology:orientable_winding")
    boundary_edges = {edge for edge, owners in edge_owners.items() if len(owners) == 1}
    boundary_locals = {value for edge in boundary_edges for value in edge}
    local_to_source: dict[int, int] = {}
    for local in boundary_locals:
        row = vertices.get(local)
        coordinate = row.get("coordinate_local_m") if isinstance(row, Mapping) else None
        matches = [
            source_index
            for source_index, expected in boundary_coordinates.items()
            if isinstance(coordinate, list) and vector_close(coordinate, expected)
        ]
        if len(matches) == 1:
            local_to_source[local] = matches[0]
    expected_edges = {
        _canonical_edge(int(boundary_cycle[index]), int(boundary_cycle[(index + 1) % len(boundary_cycle)]))
        for index in range(len(boundary_cycle))
    }
    mapped_edges = {
        _canonical_edge(local_to_source[first], local_to_source[second])
        for first, second in boundary_edges
        if first in local_to_source and second in local_to_source
    }
    if mapped_edges != expected_edges or len(local_to_source) != len(boundary_cycle):
        failures.add("topology:exact_unsplit_source_boundary")
    new_count = len(vertices) - len(local_to_source)
    if new_count < 0 or new_count > maximum_new_vertices:
        failures.add("topology:maximum_new_vertices")
    edge_count = len(edge_owners)
    if len(vertices) - edge_count + len(polygons) != 1 or _components(polygons) != 1:
        failures.add("topology:single_disk")
    materials = patch.get("materials") if isinstance(patch, Mapping) else None
    if not isinstance(materials, list):
        failures.add("topology:material_binding")
    else:
        for row in polygons_map.values():
            slot = row.get("material_index")
            if not is_int(slot) or slot < 0 or slot >= len(materials) or materials[slot] != required_material_name:
                failures.add("topology:material_binding")
                break
    return failures, local_to_source


def _weight_map(row: Mapping[str, object] | None) -> dict[str, float]:
    if not isinstance(row, Mapping) or not isinstance(row.get("groups"), list):
        return {}
    result: dict[str, float] = {}
    for item in row["groups"]:
        if not isinstance(item, Mapping) or not isinstance(item.get("name"), str) or not finite(item.get("weight")):
            return {}
        result[str(item["name"])] = float(item["weight"])
    return result


def _required_point_attribute(
    mesh: Mapping[str, object],
    vertex_count: int,
    name: str,
    data_type: str,
) -> list[object] | None:
    """Read one exact Blender-extracted POINT attribute.

    The attribute is candidate-owned Blend state read by the sealed extractor;
    it is not an evidence row supplied to the evaluator.  Requiring complete
    point-domain coverage makes missing, partial, duplicate, renamed, or
    type-shifted provenance fail closed.
    """
    rows = [
        row
        for row in mesh.get("attributes", [])
        if isinstance(row, Mapping) and row.get("name") == name
    ]
    if len(rows) != 1:
        return None
    row = rows[0]
    data = row.get("data")
    if (
        row.get("domain") != "POINT"
        or row.get("data_type") != data_type
        or not isinstance(data, list)
        or len(data) != vertex_count
    ):
        return None
    return data


def _linear_world_displacement(
    matrix_world: object, displacement_local: Sequence[float]
) -> list[float] | None:
    if (
        not isinstance(matrix_world, list)
        or len(matrix_world) != 4
        or any(not finite_vector(row, 4) for row in matrix_world)
        or not finite_vector(displacement_local, 3)
        or not vector_close(matrix_world[3], [0.0, 0.0, 0.0, 1.0], 1e-10)
    ):
        return None
    linear = [[float(matrix_world[row][column]) for column in range(3)] for row in range(3)]
    determinant = (
        linear[0][0] * (linear[1][1] * linear[2][2] - linear[1][2] * linear[2][1])
        - linear[0][1] * (linear[1][0] * linear[2][2] - linear[1][2] * linear[2][0])
        + linear[0][2] * (linear[1][0] * linear[2][1] - linear[1][1] * linear[2][0])
    )
    if not math.isfinite(determinant) or abs(determinant) <= 1e-18:
        return None
    return [
        sum(linear[row][column] * float(displacement_local[column]) for column in range(3))
        for row in range(3)
    ]


def validate_patch_uv_and_weights(
    patch: Mapping[str, object] | None,
    source_positions: Sequence[Sequence[float]],
    source_faces: Sequence[Sequence[int]],
    source_uvs: Sequence[Sequence[float]],
    source_weights: Sequence[Sequence[Mapping[str, object]]],
    eligible_face_indices: set[int],
    local_to_source: Mapping[int, int],
    maximum_world_displacement_m: float = 0.012,
) -> set[str]:
    failures: set[str] = set()
    vertices, polygons = _mesh_maps(patch)
    if not isinstance(patch, Mapping):
        return {"attributes:patch_missing"}
    loops = {
        int(row["index"]): row
        for row in patch.get("loops", [])
        if isinstance(row, Mapping) and is_int(row.get("index"))
    }
    layers = [row for row in patch.get("uv_layers", []) if isinstance(row, Mapping) and row.get("active_render")]
    if len(layers) != 1:
        return {"uv:one_active_render_layer"}
    uv_data = {
        int(row["loop_index"]): row.get("uv")
        for row in layers[0].get("data", [])
        if isinstance(row, Mapping) and is_int(row.get("loop_index"))
    }
    if not finite(maximum_world_displacement_m) or float(maximum_world_displacement_m) <= 0.0:
        return {"attributes:maximum_world_displacement_contract"}
    matrix_world = patch.get("matrix_world")
    if _linear_world_displacement(matrix_world, [0.0, 0.0, 0.0]) is None:
        return {"attributes:patch_world_transform"}
    source_face_attribute = _required_point_attribute(
        patch, len(vertices), "r24_source_face", "INT"
    )
    barycentric_attribute = _required_point_attribute(
        patch, len(vertices), "r24_barycentric", "FLOAT_VECTOR"
    )
    displacement_attribute = _required_point_attribute(
        patch, len(vertices), "r24_displacement_local_m", "FLOAT_VECTOR"
    )
    if source_face_attribute is None:
        failures.add("attributes:source_face_provenance")
    if barycentric_attribute is None:
        failures.add("attributes:barycentric_provenance")
    if displacement_attribute is None:
        failures.add("attributes:displacement_provenance")
    if failures & {
        "attributes:source_face_provenance",
        "attributes:barycentric_provenance",
        "attributes:displacement_provenance",
    }:
        return failures

    projection: dict[int, tuple[list[float], dict[str, float]]] = {}
    for local, row in vertices.items():
        normal = row.get("normal_local") if isinstance(row, Mapping) else None
        if (
            not finite_vector(normal, 3)
            or not math.isclose(
                math.sqrt(sum(float(value) ** 2 for value in normal)),
                1.0,
                rel_tol=0.0,
                abs_tol=1e-5,
            )
        ):
            failures.add("attributes:finite_unit_vertex_normals")
        raw_face_index = source_face_attribute[local]
        raw_bary = barycentric_attribute[local]
        raw_displacement = displacement_attribute[local]
        if (
            not is_int(raw_face_index)
            or int(raw_face_index) not in eligible_face_indices
            or int(raw_face_index) < 0
            or int(raw_face_index) >= len(source_faces)
        ):
            failures.add("attributes:eligible_source_face")
            continue
        face_index = int(raw_face_index)
        face = source_faces[face_index]
        if (
            not isinstance(face, Sequence)
            or isinstance(face, (str, bytes))
            or len(face) != 3
            or any(not is_int(value) or int(value) < 0 or int(value) >= len(source_positions) for value in face)
        ):
            failures.add("attributes:source_face_triangle")
            continue
        if (
            not finite_vector(raw_bary, 3)
            or not math.isclose(sum(float(value) for value in raw_bary), 1.0, rel_tol=0.0, abs_tol=1e-8)
            or min(float(value) for value in raw_bary) < -1e-8
            or max(float(value) for value in raw_bary) > 1.0 + 1e-8
        ):
            failures.add("attributes:normalized_barycentric_origin")
            continue
        bary = [float(value) for value in raw_bary]
        if not finite_vector(raw_displacement, 3):
            failures.add("attributes:finite_local_displacement")
            continue
        displacement = [float(value) for value in raw_displacement]
        world_displacement = _linear_world_displacement(matrix_world, displacement)
        if world_displacement is None:
            failures.add("attributes:patch_world_transform")
        elif math.sqrt(sum(value * value for value in world_displacement)) > float(maximum_world_displacement_m) + 1e-12:
            failures.add("attributes:maximum_world_displacement")
        try:
            triangle = [source_positions[int(index)] for index in face]
            if any(not finite_vector(value, 3) for value in triangle):
                raise ValueError
            origin = [
                sum(bary[corner] * float(triangle[corner][axis]) for corner in range(3))
                for axis in range(3)
            ]
        except (IndexError, TypeError, ValueError):
            failures.add("attributes:source_origin")
            continue
        point = row.get("coordinate_local_m")
        expected_point = [origin[axis] + displacement[axis] for axis in range(3)]
        if not finite_vector(point, 3) or not vector_close(point, expected_point, 1e-7):
            failures.add("attributes:displacement_coordinate_binding")
        if local in local_to_source:
            source_index = local_to_source[local]
            corners = [corner for corner, value in enumerate(face) if int(value) == source_index]
            if len(corners) != 1:
                failures.add("attributes:boundary_source_vertex_binding")
            else:
                one_hot = [1.0 if corner == corners[0] else 0.0 for corner in range(3)]
                if not vector_close(bary, one_hot, 1e-8):
                    failures.add("attributes:boundary_source_vertex_binding")
            if not vector_close(displacement, [0.0, 0.0, 0.0], 1e-10):
                failures.add("attributes:boundary_zero_displacement")
        uv = [sum(bary[i] * float(source_uvs[face[i]][axis]) for i in range(3)) for axis in range(2)]
        weights_by_bone: dict[str, float] = {}
        for corner, source_index in enumerate(face):
            for item in source_weights[source_index]:
                name = str(item["bone_name"])
                weights_by_bone[name] = weights_by_bone.get(name, 0.0) + bary[corner] * float(item["weight"])
        projection[local] = (uv, {name: value for name, value in weights_by_bone.items() if value > 1e-8})
    for polygon in polygons.values():
        vertices_raw = polygon.get("vertices")
        loops_raw = polygon.get("loop_indices")
        if not isinstance(vertices_raw, list) or not isinstance(loops_raw, list) or len(vertices_raw) != len(loops_raw):
            failures.add("uv:loop_topology")
            continue
        for local, loop_index in zip(vertices_raw, loops_raw, strict=True):
            if loop_index not in loops or loops[loop_index].get("vertex_index") != local or local not in projection:
                failures.add("uv:loop_topology")
                continue
            actual_uv = uv_data.get(loop_index)
            if not isinstance(actual_uv, list) or not vector_close(actual_uv, projection[local][0], 1e-7):
                failures.add("uv:source_derived_corner_values")
    if set(uv_data) != set(loops):
        failures.add("uv:complete_corner_coverage")
    for local, (_, expected) in projection.items():
        actual = _weight_map(vertices.get(local))
        if (
            set(actual) != set(expected)
            or not math.isclose(sum(actual.values()), 1.0, rel_tol=0.0, abs_tol=1e-6)
            or any(
            not math.isclose(actual[name], expected[name], rel_tol=0.0, abs_tol=1e-6) for name in expected
            )
        ):
            failures.add("weights:source_derived_native_groups")
            break
    return failures


def _triangle_measurements(points: Sequence[Sequence[float]]) -> tuple[float, float]:
    first, second, third = points
    ab = [float(second[i]) - float(first[i]) for i in range(3)]
    ac = [float(third[i]) - float(first[i]) for i in range(3)]
    cross = [
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    ]
    area = 0.5 * math.sqrt(sum(value * value for value in cross))
    lengths = [math.dist(first, second), math.dist(second, third), math.dist(third, first)]
    angles: list[float] = []
    for index in range(3):
        side_a = lengths[index]
        side_b = lengths[(index + 2) % 3]
        opposite = lengths[(index + 1) % 3]
        if side_a <= 0 or side_b <= 0:
            angles.append(0.0)
        else:
            cosine = (side_a * side_a + side_b * side_b - opposite * opposite) / (2.0 * side_a * side_b)
            angles.append(math.degrees(math.acos(max(-1.0, min(1.0, cosine)))))
    return area, min(angles)


def validate_extracted_triangulation_identity(mesh: Mapping[str, object] | None) -> set[str]:
    """Require complete Blender loop-triangle identity without quality grading.

    This structural pass is deliberately separate from replacement quality.
    The complete licensed patch contains inherited outside-E* slivers that may
    not be mutated.  They must retain exact source face identity and one honest
    extracted triangulation, but they are not falsely reclassified as new R24
    quality failures.
    """
    failures: set[str] = set()
    _, polygons = _mesh_maps(mesh)
    if not isinstance(mesh, Mapping):
        return {"render:mesh_missing"}
    loops = {
        int(row["index"]): row
        for row in mesh.get("loops", [])
        if isinstance(row, Mapping) and is_int(row.get("index"))
    }
    triangles = mesh.get("loop_triangles")
    if not isinstance(triangles, list):
        return {"render:triangulation_missing"}
    by_polygon: dict[int, list[Mapping[str, object]]] = {}
    seen: set[tuple[int, tuple[int, ...], tuple[int, ...]]] = set()
    seen_indices: set[int] = set()
    for row in triangles:
        if (
            not isinstance(row, Mapping)
            or not is_int(row.get("index"))
            or int(row["index"]) in seen_indices
            or not is_int(row.get("polygon_index"))
            or not isinstance(row.get("vertices"), list)
            or not isinstance(row.get("loops"), list)
        ):
            failures.add("render:triangulation_structure")
            continue
        seen_indices.add(int(row["index"]))
        polygon_index = int(row["polygon_index"])
        polygon = polygons.get(polygon_index)
        values = row["vertices"]
        loop_values = row["loops"]
        polygon_vertices = polygon.get("vertices") if isinstance(polygon, Mapping) else None
        polygon_loops = polygon.get("loop_indices") if isinstance(polygon, Mapping) else None
        if (
            not isinstance(polygon, Mapping)
            or not isinstance(polygon_vertices, list)
            or not isinstance(polygon_loops, list)
            or len(values) != 3
            or len(loop_values) != 3
            or any(not is_int(value) for value in values + loop_values)
            or row.get("material_index") != polygon.get("material_index")
        ):
            failures.add("render:triangulation_structure")
            continue
        corner_pairs = set(zip(polygon_vertices, polygon_loops, strict=True))
        triangle_pairs = list(zip(values, loop_values, strict=True))
        if (
            len(corner_pairs) != len(polygon_vertices)
            or not set(triangle_pairs).issubset(corner_pairs)
            or any(
                int(loop_index) not in loops
                or loops[int(loop_index)].get("vertex_index") != vertex_index
                for vertex_index, loop_index in triangle_pairs
            )
        ):
            failures.add("render:triangulation_structure")
            continue
        if len(polygon_vertices) == 3:
            expected = [(polygon_vertices[offset], polygon_loops[offset]) for offset in range(3)]
            rotations = [expected[offset:] + expected[:offset] for offset in range(3)]
            if triangle_pairs not in rotations:
                failures.add("render:triangulation_structure")
                continue
        identity = (
            polygon_index,
            tuple(sorted(int(value) for value in values)),
            tuple(sorted(int(value) for value in loop_values)),
        )
        if identity in seen:
            failures.add("render:triangulation_structure")
        seen.add(identity)
        by_polygon.setdefault(polygon_index, []).append(row)
    if set(by_polygon) != set(polygons) or any(
        len(by_polygon[index]) != len(polygons[index].get("vertices", [])) - 2 for index in polygons
    ):
        failures.add("render:complete_blender_loop_triangulation")
    if seen_indices != set(range(len(triangles))):
        failures.add("render:triangulation_structure")
    return failures


def validate_render_triangulation(
    mesh: Mapping[str, object] | None, minimum_area: float, minimum_angle: float
) -> set[str]:
    failures = validate_extracted_triangulation_identity(mesh)
    vertices, polygons = _mesh_maps(mesh)
    if not isinstance(mesh, Mapping):
        return failures
    triangles = mesh.get("loop_triangles")
    if not isinstance(triangles, list):
        return failures
    for row in triangles:
        if not isinstance(row, Mapping) or not isinstance(row.get("vertices"), list):
            continue
        values = row["vertices"]
        if len(values) != 3 or any(not is_int(value) or int(value) not in vertices for value in values):
            continue
        try:
            points = [vertices[int(index)]["coordinate_local_m"] for index in values]
            area, angle = _triangle_measurements(points)
        except (KeyError, TypeError, ValueError):
            failures.add("render:triangle_geometry")
            continue
        if not math.isfinite(area) or area < minimum_area:
            failures.add("render:minimum_triangle_area")
        if not math.isfinite(angle) or angle < minimum_angle:
            failures.add("render:minimum_triangle_angle")
    return failures


def source_domain_triangle_quality(
    source_mesh: Mapping[str, object],
    face_indices: set[int],
    minimum_area: float,
    minimum_angle: float,
) -> dict[str, object]:
    """Describe inherited source quality without converting it into a pass."""
    positions = source_mesh.get("positions")
    faces = source_mesh.get("faces")
    if not isinstance(positions, list) or not isinstance(faces, list) or not face_indices:
        raise R4PackageError("source quality domain is absent")
    records: list[tuple[int, float, float]] = []
    for face_index in sorted(face_indices):
        if face_index < 0 or face_index >= len(faces):
            raise R4PackageError("source quality face index is invalid")
        face = faces[face_index]
        if (
            not isinstance(face, list)
            or len(face) != 3
            or any(not is_int(value) or int(value) < 0 or int(value) >= len(positions) for value in face)
        ):
            raise R4PackageError("source quality face is not a triangle")
        try:
            points = [positions[int(value)] for value in face]
            if any(not finite_vector(point, 3) for point in points):
                raise ValueError
            area, angle = _triangle_measurements(points)
        except (IndexError, TypeError, ValueError) as exc:
            raise R4PackageError("source quality geometry is malformed") from exc
        records.append((face_index, area, angle))
    minimum_area_record = min(records, key=lambda row: (row[1], row[0]))
    minimum_angle_record = min(records, key=lambda row: (row[2], row[0]))
    below_area = [index for index, area, _ in records if area < minimum_area]
    below_angle = [index for index, _, angle in records if angle < minimum_angle]
    return {
        "face_count": len(records),
        "minimum_area_m2": minimum_area_record[1],
        "minimum_area_face_index": minimum_area_record[0],
        "below_replacement_minimum_area_count": len(below_area),
        "below_replacement_minimum_area_face_indices_sha256": canonical_sha256(below_area),
        "minimum_angle_degrees": minimum_angle_record[2],
        "minimum_angle_face_index": minimum_angle_record[0],
        "below_replacement_minimum_angle_count": len(below_angle),
        "below_replacement_minimum_angle_face_indices_sha256": canonical_sha256(below_angle),
        "classification": "INHERITED_EXACT_NON_REGRESSION_NOT_R24_REPLACEMENT_QUALITY",
    }


def validate_inherited_outside_quality_record(
    context: Mapping[str, object], contract: Mapping[str, object]
) -> set[str]:
    bounds = contract["metric_bounds"]
    actual = source_domain_triangle_quality(
        context["source_mesh"],
        set(context["domains"]["outside"]),
        float(bounds["minimum_render_triangle_area_m2"]),
        float(bounds["minimum_render_triangle_angle_degrees"]),
    )
    return set() if actual == contract.get("inherited_outside_quality") else {
        "render:inherited_outside_quality_binding"
    }


def _segment_triangle(first: Sequence[float], second: Sequence[float], triangle: Sequence[Sequence[float]]) -> bool:
    epsilon = 1e-9
    direction = [float(second[i]) - float(first[i]) for i in range(3)]
    edge1 = [float(triangle[1][i]) - float(triangle[0][i]) for i in range(3)]
    edge2 = [float(triangle[2][i]) - float(triangle[0][i]) for i in range(3)]
    pvec = [
        direction[1] * edge2[2] - direction[2] * edge2[1],
        direction[2] * edge2[0] - direction[0] * edge2[2],
        direction[0] * edge2[1] - direction[1] * edge2[0],
    ]
    determinant = sum(edge1[i] * pvec[i] for i in range(3))
    if abs(determinant) <= epsilon:
        return False
    inverse = 1.0 / determinant
    tvec = [float(first[i]) - float(triangle[0][i]) for i in range(3)]
    u = sum(tvec[i] * pvec[i] for i in range(3)) * inverse
    if u <= epsilon or u >= 1.0 - epsilon:
        return False
    qvec = [
        tvec[1] * edge1[2] - tvec[2] * edge1[1],
        tvec[2] * edge1[0] - tvec[0] * edge1[2],
        tvec[0] * edge1[1] - tvec[1] * edge1[0],
    ]
    v = sum(direction[i] * qvec[i] for i in range(3)) * inverse
    if v <= epsilon or u + v >= 1.0 - epsilon:
        return False
    distance = sum(edge2[i] * qvec[i] for i in range(3)) * inverse
    return epsilon < distance < 1.0 - epsilon


def _cross3(first: Sequence[float], second: Sequence[float]) -> list[float]:
    return [
        float(first[1]) * float(second[2]) - float(first[2]) * float(second[1]),
        float(first[2]) * float(second[0]) - float(first[0]) * float(second[2]),
        float(first[0]) * float(second[1]) - float(first[1]) * float(second[0]),
    ]


def _coplanar_triangles_overlap(
    first: Sequence[Sequence[float]], second: Sequence[Sequence[float]], normal: Sequence[float]
) -> bool:
    drop = max(range(3), key=lambda axis: abs(float(normal[axis])))
    axes = [axis for axis in range(3) if axis != drop]
    a = [[float(point[axis]) for axis in axes] for point in first]
    b = [[float(point[axis]) for axis in axes] for point in second]

    def orient(p: Sequence[float], q: Sequence[float], r: Sequence[float]) -> float:
        return (float(q[0]) - float(p[0])) * (float(r[1]) - float(p[1])) - (
            float(q[1]) - float(p[1])
        ) * (float(r[0]) - float(p[0]))

    epsilon = 1e-12
    for i in range(3):
        for j in range(3):
            o1 = orient(a[i], a[(i + 1) % 3], b[j])
            o2 = orient(a[i], a[(i + 1) % 3], b[(j + 1) % 3])
            o3 = orient(b[j], b[(j + 1) % 3], a[i])
            o4 = orient(b[j], b[(j + 1) % 3], a[(i + 1) % 3])
            if o1 * o2 < -epsilon and o3 * o4 < -epsilon:
                return True

    def strict_inside(point: Sequence[float], triangle: Sequence[Sequence[float]]) -> bool:
        values = [orient(triangle[i], triangle[(i + 1) % 3], point) for i in range(3)]
        return min(values) > epsilon or max(values) < -epsilon

    center_a = [sum(point[axis] for point in a) / 3.0 for axis in range(2)]
    center_b = [sum(point[axis] for point in b) / 3.0 for axis in range(2)]
    return strict_inside(center_a, b) or strict_inside(center_b, a)


def triangles_properly_intersect(first: Sequence[Sequence[float]], second: Sequence[Sequence[float]]) -> bool:
    for triangle in (first, second):
        if any(not finite_vector(point, 3) for point in triangle):
            return True
    for axis in range(3):
        if max(float(point[axis]) for point in first) < min(float(point[axis]) for point in second) - 1e-9:
            return False
        if max(float(point[axis]) for point in second) < min(float(point[axis]) for point in first) - 1e-9:
            return False
    for offset in range(3):
        if _segment_triangle(first[offset], first[(offset + 1) % 3], second):
            return True
        if _segment_triangle(second[offset], second[(offset + 1) % 3], first):
            return True
    first_edges = [
        [float(first[1][axis]) - float(first[0][axis]) for axis in range(3)],
        [float(first[2][axis]) - float(first[0][axis]) for axis in range(3)],
    ]
    second_edges = [
        [float(second[1][axis]) - float(second[0][axis]) for axis in range(3)],
        [float(second[2][axis]) - float(second[0][axis]) for axis in range(3)],
    ]
    normal_first = _cross3(first_edges[0], first_edges[1])
    normal_second = _cross3(second_edges[0], second_edges[1])
    normals_cross = _cross3(normal_first, normal_second)
    normal_length = math.sqrt(sum(value * value for value in normal_first))
    if (
        normal_length > 1e-18
        and math.sqrt(sum(value * value for value in normals_cross)) <= 1e-10 * normal_length
        and abs(
            sum(
                normal_first[axis] * (float(second[0][axis]) - float(first[0][axis]))
                for axis in range(3)
            )
        )
        <= 1e-9 * normal_length
    ):
        return _coplanar_triangles_overlap(first, second, normal_first)
    return False


def derived_self_intersections(mesh: Mapping[str, object] | None) -> list[list[int]]:
    if not isinstance(mesh, Mapping):
        return []
    vertices, _ = _mesh_maps(mesh)
    triangles = []
    for fallback_index, row in enumerate(mesh.get("loop_triangles", [])):
        if not isinstance(row, Mapping) or not isinstance(row.get("vertices"), list) or len(row["vertices"]) != 3:
            continue
        vertex_indices = [int(value) for value in row["vertices"]]
        try:
            points = [vertices[index]["coordinate_local_m"] for index in vertex_indices]
        except (KeyError, TypeError):
            continue
        triangles.append(
            {
                "index": int(row["index"]) if is_int(row.get("index")) else fallback_index,
                "vertices": vertex_indices,
                "points": points,
                "minimum": [min(float(point[axis]) for point in points) for axis in range(3)],
                "maximum": [max(float(point[axis]) for point in points) for axis in range(3)],
            }
        )
    triangles.sort(key=lambda row: (row["minimum"][0], row["maximum"][0], row["index"]))
    result: list[list[int]] = []
    for position, first in enumerate(triangles):
        for second in triangles[position + 1 :]:
            if second["minimum"][0] > first["maximum"][0] + 1e-9:
                break
            if any(
                first["maximum"][axis] < second["minimum"][axis] - 1e-9
                or second["maximum"][axis] < first["minimum"][axis] - 1e-9
                for axis in (1, 2)
            ):
                continue
            if set(first["vertices"]) & set(second["vertices"]):
                continue
            if triangles_properly_intersect(first["points"], second["points"]):
                result.append(sorted([int(first["index"]), int(second["index"])]))
    result.sort()
    return result


def derived_intersection_geometry_records(mesh: Mapping[str, object] | None) -> list[str]:
    if not isinstance(mesh, Mapping):
        return []
    vertices, _ = _mesh_maps(mesh)
    triangles = {
        int(row["index"]) if is_int(row.get("index")) else fallback: row
        for fallback, row in enumerate(mesh.get("loop_triangles", []))
        if isinstance(row, Mapping) and isinstance(row.get("vertices"), list) and len(row["vertices"]) == 3
    }
    records: list[str] = []
    for first_index, second_index in derived_self_intersections(mesh):
        pair = []
        for index in (first_index, second_index):
            row = triangles[index]
            points = [vertices[int(vertex)]["coordinate_local_m"] for vertex in row["vertices"]]
            pair.append(canonical_sha256(sorted(points)))
        records.append(canonical_sha256(sorted(pair)))
    return sorted(records)


def _intersection_measurement_records(rows: object) -> list[dict[str, object]] | None:
    if not isinstance(rows, list):
        return None
    result: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("face_indices"), list):
            return None
        result.append(
            {
                "face_indices": row.get("face_indices"),
                "measurement_sha256": canonical_sha256(row),
            }
        )
    return result


def _stable_patch_pair_record(
    row: Mapping[str, object], face_index_map: Mapping[int, int] | None = None
) -> dict[str, object] | None:
    """Remove only index/topology fields that can change under E* retopology.

    Face identity is rebound to the exact licensed source index.  Geometric
    centers, bounds, distances, classifications, and segment measurements stay
    exact; helper-local triangle indices and topology-hop counts do not.
    """
    face_indices = row.get("face_indices")
    face_centers = row.get("face_centers")
    classifications = row.get("triangle_pair_classifications")
    if (
        not isinstance(face_indices, list)
        or len(face_indices) != 2
        or any(not is_int(value) for value in face_indices)
        or not isinstance(face_centers, list)
        or len(face_centers) != 2
        or any(not finite_vector(value, 3) for value in face_centers)
        or not isinstance(classifications, list)
    ):
        return None
    mapped: list[tuple[int, list[float]]] = []
    for index, center in zip(face_indices, face_centers, strict=True):
        value = int(index)
        if face_index_map is not None:
            if value not in face_index_map:
                return None
            value = int(face_index_map[value])
        mapped.append((value, [float(item) for item in center]))
    mapped.sort(key=lambda item: item[0])
    measurement_rows: list[dict[str, object]] = []
    for item in classifications:
        if (
            not isinstance(item, Mapping)
            or not isinstance(item.get("classification"), str)
            or not isinstance(item.get("genuine_penetration"), bool)
        ):
            return None
        value: dict[str, object] = {
            "classification": str(item["classification"]),
            "genuine_penetration": bool(item["genuine_penetration"]),
        }
        if "intersection_segment_length_m" in item:
            if not finite(item.get("intersection_segment_length_m")):
                return None
            value["intersection_segment_length_m"] = float(item["intersection_segment_length_m"])
        measurement_rows.append(value)
    measurement_rows.sort(key=lambda value: canonical_json(value))
    stable = {
        "face_indices": [item[0] for item in mapped],
        "face_centers": [item[1] for item in mapped],
        "shared_vertex_count": row.get("shared_vertex_count"),
        "shared_edge_count": row.get("shared_edge_count"),
        "center_distance_m": row.get("center_distance_m"),
        "combined_bounds": row.get("combined_bounds"),
        "body_region": row.get("body_region"),
        "overlap_character": row.get("overlap_character"),
        "genuine_positive_area_or_segment_penetration": row.get(
            "genuine_positive_area_or_segment_penetration"
        ),
        "triangle_pair_measurements": measurement_rows,
    }
    if (
        not is_int(stable["shared_vertex_count"])
        or not is_int(stable["shared_edge_count"])
        or not finite(stable["center_distance_m"])
        or not isinstance(stable["combined_bounds"], Mapping)
        or not finite_vector(stable["combined_bounds"].get("min"), 3)
        or not finite_vector(stable["combined_bounds"].get("max"), 3)
        or not isinstance(stable["body_region"], str)
        or not isinstance(stable["overlap_character"], str)
        or stable["genuine_positive_area_or_segment_penetration"] is not True
    ):
        return None
    return stable


def _stable_patch_pair_records(
    rows: object, face_index_map: Mapping[int, int] | None = None
) -> list[dict[str, object]] | None:
    if not isinstance(rows, list):
        return None
    result: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            return None
        record = _stable_patch_pair_record(row, face_index_map)
        if record is None:
            return None
        result.append(record)
    return sorted(result, key=lambda value: canonical_json(value))


def _source_patch_diagnostic_records(
    contract: Mapping[str, object], outside_faces: set[int]
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    binding = contract["intersection_and_interface_requirements"].get("source_patch_diagnostic")
    if not isinstance(binding, Mapping):
        raise R4PackageError("source patch intersection diagnostic binding is absent")
    path = validate_exact_file(ROOT, binding)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        report = payload["adult_patch"]["exact_nonadjacent_intersections"]
        rows = report["pairs"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise R4PackageError("source patch intersection diagnostic is malformed") from exc
    all_records = _stable_patch_pair_records(rows)
    if all_records is None:
        raise R4PackageError("source patch intersection records are malformed")
    outside_rows = [
        row
        for row in rows
        if isinstance(row, Mapping)
        and isinstance(row.get("face_indices"), list)
        and len(row["face_indices"]) == 2
        and all(is_int(value) and int(value) in outside_faces for value in row["face_indices"])
    ]
    outside_records = _stable_patch_pair_records(outside_rows)
    if outside_records is None:
        raise R4PackageError("outside source patch intersection records are malformed")
    requirements = contract["intersection_and_interface_requirements"]
    if (
        len(all_records) != int(requirements["source_patch_total_pair_count"])
        or canonical_sha256(all_records) != requirements["source_patch_total_pair_records_sha256"]
        or len(outside_records) != int(requirements["inherited_outside_pair_count"])
        or canonical_sha256(outside_records) != requirements["inherited_outside_pair_records_sha256"]
    ):
        raise R4PackageError("source patch intersection diagnostic classification changed")
    return all_records, outside_records


def validate_neutral_patch_pair_partition(
    source_report: Mapping[str, object],
    candidate_report: Mapping[str, object],
    outside_faces: set[int],
    expected_all_source: list[dict[str, object]],
    expected_inherited_outside: list[dict[str, object]],
    *,
    source_object_name: str,
    candidate_object_name: str,
) -> set[str]:
    failures: set[str] = set()
    source_rows = source_report.get("pairs")
    candidate_rows = candidate_report.get("pairs")
    source_records = _stable_patch_pair_records(source_rows)
    candidate_records = _stable_patch_pair_records(candidate_rows)
    if (
        source_report.get("scope") != "source_body_patch_material_region"
        or source_report.get("extracted_object_name") != source_object_name
        or source_records != expected_all_source
        or source_report.get("exact_genuine_penetration_pair_count") != len(expected_all_source)
    ):
        failures.add("intersections:source_neutral_patch_exact_259")
    if (
        candidate_report.get("scope") != "complete_private_patch_object"
        or candidate_report.get("extracted_object_name") != candidate_object_name
    ):
        failures.add("intersections:candidate_private_patch_scope")
    if not isinstance(candidate_rows, list):
        failures.add("intersections:candidate_neutral_patch_rows")
        return failures
    for row in candidate_rows:
        face_indices = row.get("face_indices") if isinstance(row, Mapping) else None
        if (
            not isinstance(face_indices, list)
            or len(face_indices) != 2
            or any(not is_int(value) or int(value) not in outside_faces for value in face_indices)
        ):
            failures.add("intersections:replacement_or_cross_boundary_neutral_pair")
    if (
        candidate_records != expected_inherited_outside
        or candidate_report.get("exact_genuine_penetration_pair_count") != len(expected_inherited_outside)
    ):
        failures.add("intersections:exact_214_inherited_outside_pairs")
    return failures


def _source_face_index_map_for_patch_region(
    mesh: Mapping[str, object] | None,
    context: Mapping[str, object],
    material_name: str,
) -> dict[int, int]:
    if not isinstance(mesh, Mapping):
        return {}
    source_mesh = context["source_mesh"]
    bone_names = context["bone_names"]
    signature_to_source = {
        _source_face_signature(source_mesh, bone_names, index): index
        for index in range(len(source_mesh["faces"]))
    }
    if len(signature_to_source) != len(source_mesh["faces"]):
        raise R4PackageError("licensed source face signatures are not unique")
    _, polygons = _mesh_maps(mesh)
    result: dict[int, int] = {}
    for index in _material_face_indices(mesh, material_name):
        signature = _candidate_face_signature(mesh, polygons[index])
        if signature in signature_to_source:
            result[index] = int(signature_to_source[signature])
    return result


def _partition_posed_pairs(
    pose: Mapping[str, object],
    body: Mapping[str, object] | None,
    context: Mapping[str, object],
    material_name: str,
) -> tuple[
    list[dict[str, object]] | None,
    list[dict[str, object]] | None,
    list[Mapping[str, object]] | None,
]:
    report = pose.get("report")
    rows = report.get("pairs") if isinstance(report, Mapping) else None
    if not isinstance(rows, list) or not isinstance(body, Mapping):
        return None, None, None
    patch_faces = _material_face_indices(body, material_name)
    source_map = _source_face_index_map_for_patch_region(body, context, material_name)
    outside = set(context["domains"]["outside"])
    nonpatch: list[Mapping[str, object]] = []
    outside_rows: list[Mapping[str, object]] = []
    forbidden: list[Mapping[str, object]] = []
    outside_face_map: dict[int, int] = {}
    for row in rows:
        face_indices = row.get("face_indices") if isinstance(row, Mapping) else None
        if (
            not isinstance(row, Mapping)
            or not isinstance(face_indices, list)
            or len(face_indices) != 2
            or any(not is_int(value) for value in face_indices)
        ):
            return None, None, None
        values = [int(value) for value in face_indices]
        if all(value not in patch_faces for value in values):
            nonpatch.append(row)
        elif all(value in patch_faces for value in values) and all(
            value in source_map and source_map[value] in outside for value in values
        ):
            outside_rows.append(row)
            outside_face_map.update({value: source_map[value] for value in values})
        else:
            forbidden.append(row)
    return (
        _intersection_measurement_records(nonpatch),
        _stable_patch_pair_records(outside_rows, outside_face_map),
        forbidden,
    )


def validate_extracted_intersection_reports(
    source: Mapping[str, object],
    candidate: Mapping[str, object],
    contract: Mapping[str, object],
    context: Mapping[str, object],
    expected_inherited: list[dict[str, object]],
) -> set[str]:
    failures: set[str] = set()

    def reports(snapshot: Mapping[str, object]) -> Mapping[str, object] | None:
        state = snapshot.get("state")
        value = state.get("intersection_reports") if isinstance(state, Mapping) else None
        return value if isinstance(value, Mapping) else None

    source_reports = reports(source)
    candidate_reports = reports(candidate)
    if source_reports is None or candidate_reports is None:
        return {"intersections:artifact_derived_reports_missing"}
    if (
        source_reports.get("algorithm") != "sealed_blender_exact_mesh_intersections"
        or candidate_reports.get("algorithm") != "sealed_blender_exact_mesh_intersections"
    ):
        failures.add("intersections:sealed_algorithm")
    identity = contract["artifact_semantic_identity"]
    outside = set(context["domains"]["outside"])
    expected_all_source, expected_outside = _source_patch_diagnostic_records(contract, outside)
    source_standalone = source_reports.get("standalone_patch")
    candidate_standalone = candidate_reports.get("standalone_patch")
    if not isinstance(source_standalone, Mapping) or not isinstance(candidate_standalone, Mapping):
        failures.add("intersections:artifact_derived_standalone_reports_missing")
    else:
        failures |= validate_neutral_patch_pair_partition(
            source_standalone,
            candidate_standalone,
            outside,
            expected_all_source,
            expected_outside,
            source_object_name=identity["body_object_name"],
            candidate_object_name=identity["patch_object_name"],
        )
    action_name = contract["intersection_and_interface_requirements"]["measurement_action_name"]
    source_pose = source_reports.get("required_pose")
    candidate_pose = candidate_reports.get("required_pose")
    if (
        not isinstance(source_pose, Mapping)
        or source_pose.get("action") != action_name
        or not isinstance(candidate_pose, Mapping)
        or candidate_pose.get("action") != action_name
    ):
        return failures | {"intersections:required_pose"}
    source_body = _mesh(source, identity["body_object_name"])
    candidate_body = _mesh(candidate, identity["body_object_name"])
    material_name = identity["required_material_name"]
    source_nonpatch, source_outside, _source_removable = _partition_posed_pairs(
        source_pose, source_body, context, material_name
    )
    candidate_nonpatch, candidate_outside, candidate_forbidden = _partition_posed_pairs(
        candidate_pose, candidate_body, context, material_name
    )
    if source_nonpatch != expected_inherited:
        failures.add("intersections:source_exact_29_inherited_body_pairs")
    if candidate_nonpatch != expected_inherited:
        failures.add("intersections:candidate_exact_29_inherited_body_pairs")
    if source_outside is None or candidate_outside != source_outside:
        failures.add("intersections:posed_inherited_outside_pairs_exact")
    if candidate_forbidden is None or candidate_forbidden:
        failures.add("intersections:posed_replacement_cross_or_new_pair")
    candidate_full = candidate_pose.get("report")
    if (
        not isinstance(candidate_full, Mapping)
        or candidate_full.get("exact_genuine_penetration_pair_count")
        != len(expected_inherited) + len(candidate_outside or [])
    ):
        failures.add("intersections:posed_no_unclassified_pairs")
    return failures


def validate_extracted_pair(
    source: Mapping[str, object], candidate: Mapping[str, object], contract: Mapping[str, object]
) -> set[str]:
    failures = validate_object_links(candidate, contract)
    failures |= validate_protected_object_inventory(source, candidate, contract)
    failures |= validate_complete_protected_scene(source, candidate, contract)
    failures |= validate_preserved_rig_actions_material(source, candidate, contract)
    context = r3.exact_context()
    source_mesh = context["source_mesh"]
    failures |= validate_inherited_outside_quality_record(context, contract)
    failures |= validate_interface_and_protected_body(
        source,
        candidate,
        contract,
        set(),
    )
    identity = contract["artifact_semantic_identity"]
    complete_patch = _mesh(candidate, identity["patch_object_name"])
    failures |= validate_extracted_triangulation_identity(complete_patch)
    scope_failures, patch = derive_repaired_estar_patch(
        complete_patch,
        context,
        contract,
    )
    failures |= scope_failures
    cycle = contract["exact_topology"]["outer_boundary_cycle"]
    boundary = {int(index): source_mesh["positions"][int(index)] for index in cycle}
    topology_failures, local_to_source = validate_patch_topology(
        patch,
        boundary,
        cycle,
        int(contract["metric_bounds"]["maximum_new_interior_vertices"]),
        identity["required_material_name"],
    )
    failures |= topology_failures
    source_weight_rows = [
        [
            {
                "bone_name": context["bone_names"][int(joint)],
                "weight": float(weight),
            }
            for joint, weight in zip(source_mesh["joints"][index], source_mesh["weights"][index], strict=True)
            if float(weight) > 0.0
        ]
        for index in range(len(source_mesh["positions"]))
    ]
    failures |= validate_patch_uv_and_weights(
        patch,
        source_mesh["positions"],
        source_mesh["faces"],
        source_mesh["texcoords"],
        source_weight_rows,
        set(context["domains"]["estar"]),
        local_to_source,
        float(contract["metric_bounds"]["maximum_world_displacement_m"]),
    )
    if not isinstance(patch, Mapping) or len(patch.get("shape_keys", [])) != int(source_mesh["morph_target_count"]):
        failures.add("attributes:exact_source_shape_key_disposition")
    failures |= validate_actual_graft(source, candidate, contract)
    bounds = contract["metric_bounds"]
    failures |= validate_render_triangulation(
        patch,
        float(bounds["minimum_render_triangle_area_m2"]),
        float(bounds["minimum_render_triangle_angle_degrees"]),
    )
    failures |= validate_extracted_intersection_reports(
        source,
        candidate,
        contract,
        context,
        context["inherited_pair_records"],
    )
    return failures


def _typed_identity_failures(summary: Mapping[str, object], contract: Mapping[str, object]) -> set[str]:
    failures: set[str] = set()
    identity = contract["artifact_semantic_identity"]
    for code, names in identity["required_typed_id_names"].items():
        if not set(names).issubset(typed.semantic_names(dict(summary), code)):
            failures.add(f"typed_sdna:required_{code}_identity")
    semantic = summary.get("semantic_ids")
    if not isinstance(semantic, Mapping):
        return failures | {"typed_sdna:semantic_inventory"}
    for code, required in identity["required_direct_block_hashes"].items():
        rows = semantic.get(code)
        actual = (
            {
                str(row.get("name")): row.get("direct_block_sha256")
                for row in rows
                if isinstance(row, Mapping) and isinstance(row.get("name"), str)
            }
            if isinstance(rows, list)
            else {}
        )
        if not actual or any(actual.get(name) != digest for name, digest in required.items()):
            failures.add(f"typed_sdna:required_{code}_direct_hash")
    normalized_required = identity.get("required_id_user_count_normalized_block_hashes")
    if not isinstance(normalized_required, Mapping) or set(normalized_required) != {"MA"}:
        failures.add("typed_sdna:normalized_material_hash_contract")
    else:
        rows = semantic.get("MA")
        actual = (
            {
                str(row.get("name")): row.get("id_user_count_normalized_block_sha256")
                for row in rows
                if isinstance(row, Mapping) and isinstance(row.get("name"), str)
            }
            if isinstance(rows, list)
            else {}
        )
        if not actual or any(
            actual.get(name) != digest
            for name, digest in normalized_required["MA"].items()
        ):
            failures.add("typed_sdna:required_MA_id_us_normalized_hash")
    return failures


def evaluate_candidate_artifact(
    candidate_path: Path,
    blender_executable: Path,
) -> dict[str, object]:
    """Future production entry: candidate path only; no evidence JSON input."""
    contract = load_sealed_contract()
    failures: set[str] = set()
    candidate = candidate_path.resolve()
    candidate_sha256 = ""
    try:
        candidate.relative_to(ROOT.resolve())
        required_prefix = (ROOT / contract["authorized_implementation"]["candidate_path_prefix"]).resolve()
        candidate.relative_to(required_prefix)
        if not candidate.is_file():
            raise ValueError("candidate absent")
    except (OSError, ValueError):
        return {
            "schema": contract["authorized_implementation"]["required_gate_schema"],
            "eligible": False,
            "failure_names": ["artifact:path_or_presence"],
        }
    candidate_sha256 = sha256_file(candidate)
    if candidate_sha256 == contract["exact_source"]["preserved_target_blend_sha256"]:
        failures.add("artifact:not_preserved_source")
    try:
        typed_summary = typed.parse_typed_blend(candidate)
        failures |= _typed_identity_failures(typed_summary, contract)
        if sha256_file(candidate) != candidate_sha256:
            failures.add("artifact:changed_during_typed_preflight")
    except (OSError, ValueError, typed.TypedBlendError):
        failures.add("typed_sdna:genuine_structure")
    if failures:
        return {
            "schema": contract["authorized_implementation"]["required_gate_schema"],
            "eligible": False,
            "failure_names": sorted(failures),
        }
    source = validate_exact_file(
        ROOT,
        {
            "path": contract["exact_source"]["preserved_target_blend_path"],
            "bytes": contract["exact_source"]["preserved_target_blend_bytes"],
            "sha256": contract["exact_source"]["preserved_target_blend_sha256"],
        },
    )
    try:
        source_snapshot = _invoke_extractor(source, blender_executable)
        candidate_snapshot = _invoke_extractor(candidate, blender_executable)
        failures |= validate_extracted_pair(source_snapshot, candidate_snapshot, contract)
    except (OSError, TypeError, ValueError, R4ExtractionError) as exc:
        failures.add("extraction:failed_closed")
    return {
        "schema": contract["authorized_implementation"]["required_gate_schema"],
        "eligible": not failures,
        "failure_names": sorted(failures),
        "derived": {
            "candidate": {
                "path": candidate.relative_to(ROOT.resolve()).as_posix(),
                "bytes": candidate.stat().st_size,
                "sha256": candidate_sha256,
            },
            "caller_evidence_used": False,
            "typed_sdna_preflight_used": True,
            "sealed_read_only_source_and_candidate_extraction_used": True,
        },
    }


def evaluate_measured_candidate_evidence(evidence: object = None, *args: object, **kwargs: object) -> dict[str, object]:
    """Compatibility trap: JSON/evidence mappings can never authorize R4."""
    del evidence, args, kwargs
    contract = load_sealed_contract()
    return {
        "schema": contract["authorized_implementation"]["required_gate_schema"],
        "eligible": False,
        "failure_names": ["caller_evidence_not_an_acceptance_input"],
    }


def package_inventory_status(package: Path = PACKAGE) -> dict[str, object]:
    pre = {
        "CHECKPOINT.md",
        "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R4_CONTRACT.json",
        "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R4_PROPOSAL.md",
        "PACKAGE_MANIFEST.json",
        "STATIC_TEST_RESULTS.json",
    }
    post = pre | {"INDEPENDENT_STATIC_AUDIT.md"}
    actual = {path.name for path in package.iterdir() if path.is_file()} if package.is_dir() else set()
    state = "PRE_AUDIT_EXACT" if actual == pre else "POST_AUDIT_EXACT" if actual == post else "INVALID"
    return {"state": state, "actual": sorted(actual), "pre_audit": sorted(pre), "post_audit": sorted(post)}


def static_evaluation() -> dict[str, object]:
    contract = load_sealed_contract()
    fixture = validate_exact_file(ROOT, contract["rejection_fixture_binding"])
    try:
        typed.parse_typed_blend(fixture)
        fixture_result = "INCORRECTLY_ACCEPTED"
    except (OSError, ValueError, typed.TypedBlendError):
        fixture_result = "REJECTED_TYPED_SDNA"
    context = r3.exact_context()
    bounds = contract["metric_bounds"]
    inherited_outside_quality = source_domain_triangle_quality(
        context["source_mesh"],
        set(context["domains"]["outside"]),
        float(bounds["minimum_render_triangle_area_m2"]),
        float(bounds["minimum_render_triangle_angle_degrees"]),
    )
    return {
        "schema": "kira.avatar.r24.artifact_derived_gate_static_evaluation.v4",
        "status": "STATIC_R4_IMPLEMENTED_FRESH_INDEPENDENT_AUDIT_REQUIRED_NOT_EXECUTION_AUTHORIZED",
        "caller_json_gate": evaluate_measured_candidate_evidence({"eligible": True}),
        "preserved_synthetic_fixture": fixture_result,
        "inherited_outside_quality": inherited_outside_quality,
        "future_candidate": {
            "eligible": False,
            "failure_names": ["candidate_and_read_only_extraction_absent"],
        },
        "package_inventory": package_inventory_status(),
        "blender_used": False,
        "mesh_mutated": False,
        "candidate_created": False,
        "execution_authority_granted": False,
        "fresh_independent_static_audit_required": True,
    }


def main() -> int:
    print(json.dumps(static_evaluation(), sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
