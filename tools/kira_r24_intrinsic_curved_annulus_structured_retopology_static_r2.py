from __future__ import annotations

import collections
import copy
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys
from typing import Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static as parent


DEFAULT_CONTRACT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_intrinsic_curved_annulus_structured_retopology_static_r2/"
    "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R2_CONTRACT.json"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class R2EvidenceError(ValueError):
    """Raised only for a sealed static-package or source-data defect."""


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


def is_lower_sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def is_strict_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def is_nonnegative_int(value: object) -> bool:
    return is_strict_int(value) and value >= 0


def is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def finite_vector(value: object, size: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) == size
        and all(is_finite_number(component) for component in value)
    )


def vector_close(first: Sequence[object], second: Sequence[object], tolerance: float = 1e-9) -> bool:
    return len(first) == len(second) and all(
        math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=tolerance)
        for a, b in zip(first, second, strict=True)
    )


def load_contract(path: Path = DEFAULT_CONTRACT) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != "kira.avatar.r24.intrinsic_curved_annulus_structured_retopology_gate.v2":
        raise R2EvidenceError("unexpected R2 contract schema")
    return value


def resolve_project_path(root: Path, raw: object) -> Path:
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute():
        raise ValueError("path is not a nonempty project-relative path")
    resolved = (root / raw).resolve()
    resolved.relative_to(root.resolve())
    return resolved


def validate_exact_file(root: Path, record: Mapping[str, object]) -> Path:
    path = resolve_project_path(root, record.get("path"))
    if not path.is_file():
        raise ValueError("bound path is not a file")
    if not is_nonnegative_int(record.get("bytes")) or path.stat().st_size != record["bytes"]:
        raise ValueError("bound byte count is not exact")
    if not is_lower_sha256(record.get("sha256")) or sha256_file(path) != record["sha256"]:
        raise ValueError("bound SHA-256 is not exact")
    return path


def validate_parent_bindings(contract: Mapping[str, object], root: Path = ROOT) -> dict[str, Path]:
    bindings = contract.get("parent_bindings")
    if not isinstance(bindings, Mapping) or set(bindings) != {
        "contract",
        "proposal",
        "checkpoint",
        "independent_audit",
        "evaluator",
        "test",
    }:
        raise R2EvidenceError("R2 parent binding inventory is not exact")
    resolved: dict[str, Path] = {}
    for name, raw in bindings.items():
        if not isinstance(raw, Mapping):
            raise R2EvidenceError(f"R2 parent binding {name!r} is malformed")
        try:
            resolved[str(name)] = validate_exact_file(root, raw)
        except (OSError, TypeError, ValueError) as exc:
            raise R2EvidenceError(f"R2 parent binding {name!r} changed: {exc}") from exc
    return resolved


def _parse_glb(path: Path) -> tuple[dict[str, object], bytes]:
    data = path.read_bytes()
    if len(data) < 20:
        raise R2EvidenceError("truncated source GLB")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise R2EvidenceError("invalid source GLB header")
    document: dict[str, object] | None = None
    binary: bytes | None = None
    offset = 12
    while offset < len(data):
        length, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset : offset + length]
        offset += length
        if len(chunk) != length:
            raise R2EvidenceError("truncated source GLB chunk")
        if kind == 0x4E4F534A:
            document = json.loads(chunk)
        elif kind == 0x004E4942:
            binary = chunk
    if offset != len(data) or document is None or binary is None:
        raise R2EvidenceError("source GLB lacks JSON or binary data")
    return document, binary


def _read_accessor(
    document: Mapping[str, object], binary: bytes, accessor_index: int
) -> list[object]:
    accessor = document["accessors"][accessor_index]
    view = document["bufferViews"][accessor["bufferView"]]
    component_formats = {
        5120: "b",
        5121: "B",
        5122: "h",
        5123: "H",
        5125: "I",
        5126: "f",
    }
    component_counts = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
    component_type = accessor["componentType"]
    component_count = component_counts.get(accessor["type"])
    if component_type not in component_formats or component_count is None:
        raise R2EvidenceError("unsupported source GLB accessor")
    fmt = "<" + component_formats[component_type] * component_count
    item_size = struct.calcsize(fmt)
    stride = int(view.get("byteStride", item_size))
    if stride < item_size:
        raise R2EvidenceError("invalid source GLB accessor stride")
    start = int(view.get("byteOffset", 0)) + int(accessor.get("byteOffset", 0))
    values: list[object] = []
    for index in range(accessor["count"]):
        unpacked = struct.unpack_from(fmt, binary, start + index * stride)
        if accessor.get("normalized") and component_type != 5126:
            bits = struct.calcsize(component_formats[component_type]) * 8
            signed = component_type in {5120, 5122}
            denominator = (2 ** (bits - 1) - 1) if signed else (2**bits - 1)
            unpacked = tuple(
                max(-1.0, float(value) / denominator) if signed else float(value) / denominator
                for value in unpacked
            )
        values.append(unpacked[0] if component_count == 1 else list(unpacked))
    return values


def _load_source_mesh(contract: Mapping[str, object], root: Path) -> dict[str, object]:
    source = contract["exact_source"]
    glb_record = {
        "path": source["licensed_source_glb_path"],
        "bytes": source["licensed_source_glb_bytes"],
        "sha256": source["licensed_source_glb_sha256"],
    }
    glb_path = validate_exact_file(root, glb_record)
    document, binary = _parse_glb(glb_path)
    meshes = [
        mesh
        for mesh in document["meshes"]
        if mesh.get("name") == source["source_mesh"]
    ]
    if len(meshes) != 1 or len(meshes[0]["primitives"]) != 1:
        raise R2EvidenceError("source mesh identity is not unique")
    primitive = meshes[0]["primitives"][0]
    indices = [int(value) for value in _read_accessor(document, binary, primitive["indices"])]
    if len(indices) % 3:
        raise R2EvidenceError("source triangle index count is invalid")
    faces = [indices[index : index + 3] for index in range(0, len(indices), 3)]
    attributes = primitive["attributes"]
    positions = _read_accessor(document, binary, attributes["POSITION"])
    normals = _read_accessor(document, binary, attributes["NORMAL"])
    texcoords = _read_accessor(document, binary, attributes["TEXCOORD_0"])
    joints = _read_accessor(document, binary, attributes["JOINTS_0"])
    weights = _read_accessor(document, binary, attributes["WEIGHTS_0"])
    if not (
        len(positions) == len(normals) == len(texcoords) == len(joints) == len(weights)
    ):
        raise R2EvidenceError("source vertex attribute counts differ")
    return {
        "faces": faces,
        "positions": positions,
        "normals": normals,
        "texcoords": texcoords,
        "joints": joints,
        "weights": weights,
        "morph_target_count": len(primitive.get("targets", [])),
    }


@lru_cache(maxsize=1)
def static_context() -> dict[str, object]:
    contract = load_contract()
    validate_parent_bindings(contract)
    parent_contract = parent.load_contract(
        ROOT / Path(contract["parent_bindings"]["contract"]["path"])
    )
    bindings = parent.validate_immutable_bindings(parent_contract)
    domains = parent.reconstruct_exact_domains(parent_contract, bindings)
    source_mesh = _load_source_mesh(contract, ROOT)
    if source_mesh["faces"] != [list(face) for face in domains["faces"]]:
        raise R2EvidenceError("R2 source GLB topology differs from the sealed parent")
    return {
        "contract": contract,
        "parent_contract": parent_contract,
        "parent_bindings": bindings,
        "domains": domains,
        "source_mesh": source_mesh,
    }


def _record_point(source_mesh: Mapping[str, object], vertex_index: int) -> dict[str, object]:
    return {
        "vertex_index": vertex_index,
        "coordinate_m": list(source_mesh["positions"][vertex_index]),
        "normal": list(source_mesh["normals"][vertex_index]),
    }


def expected_outside_records(context: Mapping[str, object] | None = None) -> dict[str, list[object]]:
    context = static_context() if context is None else context
    source_mesh = context["source_mesh"]
    faces = source_mesh["faces"]
    outside = sorted(context["domains"]["outside"])
    material = context["contract"]["exact_source"]["preserved_material_index"]
    point_indices = sorted({vertex for face_index in outside for vertex in faces[face_index]})
    edges = sorted(
        {
            tuple(sorted((triangle[index], triangle[(index + 1) % 3])))
            for face_index in outside
            for triangle in [faces[face_index]]
            for index in range(3)
        }
    )
    face_records = [
        {
            "face_index": face_index,
            "vertices": list(faces[face_index]),
            "material_index": material,
        }
        for face_index in outside
    ]
    corner_records = [
        {
            "face_index": face_index,
            "corner_index": corner_index,
            "vertex_index": vertex_index,
            "uv": list(source_mesh["texcoords"][vertex_index]),
            "normal": list(source_mesh["normals"][vertex_index]),
            "material_index": material,
        }
        for face_index in outside
        for corner_index, vertex_index in enumerate(faces[face_index])
    ]
    return {
        "POINT": [_record_point(source_mesh, index) for index in point_indices],
        "EDGE": [{"vertices": list(edge)} for edge in edges],
        "FACE": face_records,
        "CORNER": corner_records,
    }


def expected_outer_boundary_records(
    context: Mapping[str, object] | None = None,
) -> dict[str, list[object]]:
    context = static_context() if context is None else context
    source_mesh = context["source_mesh"]
    faces = source_mesh["faces"]
    cycle = context["contract"]["exact_topology"]["outer_boundary_cycle"]
    exterior = sorted(context["domains"]["exterior_adjacent"])
    material = context["contract"]["exact_source"]["preserved_material_index"]
    return {
        "POINT": [_record_point(source_mesh, index) for index in cycle],
        "EDGE": [
            {"order": order, "vertices": [cycle[order], cycle[(order + 1) % len(cycle)]]}
            for order in range(len(cycle))
        ],
        "FACE": [
            {
                "face_index": face_index,
                "vertices": list(faces[face_index]),
                "material_index": material,
            }
            for face_index in exterior
        ],
        "CORNER": [
            {
                "face_index": face_index,
                "corner_index": corner_index,
                "vertex_index": vertex_index,
                "uv": list(source_mesh["texcoords"][vertex_index]),
                "normal": list(source_mesh["normals"][vertex_index]),
                "material_index": material,
            }
            for face_index in exterior
            for corner_index, vertex_index in enumerate(faces[face_index])
        ],
    }


def ledger(records: list[object]) -> dict[str, object]:
    return {
        "record_count": len(records),
        "records": records,
        "sha256": canonical_sha256(records),
    }


def paired_ledger(records: list[object]) -> dict[str, object]:
    return {"source": ledger(copy.deepcopy(records)), "candidate": ledger(copy.deepcopy(records))}


def evidence_payload_sha256(evidence: Mapping[str, object]) -> str:
    value = copy.deepcopy(dict(evidence))
    value["record_sha256"] = ""
    artifact = value.get("artifact")
    if isinstance(artifact, dict):
        artifact["evidence_payload_sha256"] = ""
    run = value.get("construction_run")
    if isinstance(run, dict):
        run["evidence_payload_sha256"] = ""
    return canonical_sha256(value)


def finalize_evidence_digest(evidence: dict[str, object]) -> dict[str, object]:
    evidence["record_sha256"] = ""
    if isinstance(evidence.get("artifact"), dict):
        evidence["artifact"]["evidence_payload_sha256"] = ""
    if isinstance(evidence.get("construction_run"), dict):
        evidence["construction_run"]["evidence_payload_sha256"] = ""
    digest = evidence_payload_sha256(evidence)
    evidence["record_sha256"] = digest
    if isinstance(evidence.get("artifact"), dict):
        evidence["artifact"]["evidence_payload_sha256"] = digest
    if isinstance(evidence.get("construction_run"), dict):
        evidence["construction_run"]["evidence_payload_sha256"] = digest
    return evidence


def _add(failures: set[str], name: str, condition: bool) -> None:
    if not condition:
        failures.add(name)


def _parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _scan_numeric_truth(value: object, failures: set[str], key: str = "") -> None:
    if isinstance(value, bool):
        failures.add("asserted_boolean_not_measurement")
        return
    if value is None or isinstance(value, str):
        return
    if isinstance(value, Mapping):
        for child_key, child in value.items():
            _scan_numeric_truth(child, failures, str(child_key))
        return
    if isinstance(value, list):
        for child in value:
            _scan_numeric_truth(child, failures, key)
        return
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            failures.add("nonfinite_numeric_value")
            return
        lowered = key.lower()
        if lowered.endswith(("_count", "_bytes", "_index", "_order")):
            if not is_nonnegative_int(value):
                failures.add("invalid_nonnegative_integer")
        nonnegative_tokens = (
            "area",
            "angle",
            "length",
            "weight",
            "residual",
            "duration",
        )
        if any(token in lowered for token in nonnegative_tokens) and float(value) < 0:
            failures.add("negative_metric_value")
        return
    failures.add("unsupported_evidence_value_type")


def _validate_ledger(
    name: str,
    raw: object,
    failures: set[str],
    *,
    expected: list[object] | None = None,
    exact_count: int | None = None,
) -> list[object]:
    if not isinstance(raw, Mapping):
        failures.add(f"{name}:missing_ledger")
        return []
    records = raw.get("records")
    if not isinstance(records, list):
        failures.add(f"{name}:records_missing")
        return []
    _add(
        failures,
        f"{name}:record_count",
        is_nonnegative_int(raw.get("record_count"))
        and raw.get("record_count") == len(records),
    )
    if exact_count is not None:
        _add(failures, f"{name}:exact_count", len(records) == exact_count)
    try:
        computed = canonical_sha256(records)
    except (TypeError, ValueError):
        computed = None
    _add(
        failures,
        f"{name}:digest",
        is_lower_sha256(raw.get("sha256")) and raw.get("sha256") == computed,
    )
    if expected is not None:
        _add(failures, f"{name}:exact_records", records == expected)
    return records


def _validate_paired_ledger(
    name: str,
    raw: object,
    failures: set[str],
    *,
    expected: list[object] | None = None,
    exact_count: int | None = None,
) -> tuple[list[object], list[object]]:
    if not isinstance(raw, Mapping):
        failures.add(f"{name}:missing_pair")
        return [], []
    source = _validate_ledger(
        f"{name}:source",
        raw.get("source"),
        failures,
        expected=expected,
        exact_count=exact_count,
    )
    candidate = _validate_ledger(
        f"{name}:candidate",
        raw.get("candidate"),
        failures,
        exact_count=exact_count,
    )
    _add(failures, f"{name}:candidate_equals_source", candidate == source)
    return source, candidate


def _validate_artifact_and_run(
    evidence: Mapping[str, object],
    contract: Mapping[str, object],
    failures: set[str],
    *,
    binding_root: Path,
    artifact_root: Path,
) -> None:
    run = evidence.get("construction_run")
    artifact = evidence.get("artifact")
    if not isinstance(run, Mapping):
        failures.add("construction_run:missing")
        return
    if not isinstance(artifact, Mapping):
        failures.add("artifact:missing")
        return
    run_id = run.get("run_id")
    _add(
        failures,
        "construction_run:run_id",
        isinstance(run_id, str)
        and re.fullmatch(r"[a-z0-9][a-z0-9_-]{7,63}", run_id) is not None,
    )
    started = _parse_utc(run.get("started_utc"))
    ended = _parse_utc(run.get("ended_utc"))
    _add(
        failures,
        "construction_run:time_range",
        started is not None and ended is not None and ended >= started,
    )
    exact_source = contract["exact_source"]
    authorized = contract["authorized_implementation"]
    expected_bindings = {
        "source": {
            "path": exact_source["preserved_target_blend_path"],
            "bytes": exact_source["preserved_target_blend_bytes"],
            "sha256": exact_source["preserved_target_blend_sha256"],
        },
        "worker": {"path": authorized["worker_path"]},
        "config": {"path": authorized["config_path"]},
    }
    actual_binding_hashes: dict[str, str] = {}
    for name, expected in expected_bindings.items():
        raw = run.get(name)
        if not isinstance(raw, Mapping):
            failures.add(f"construction_run:{name}_binding")
            continue
        _add(failures, f"construction_run:{name}_path", raw.get("path") == expected["path"])
        try:
            path = resolve_project_path(binding_root, raw.get("path"))
            actual_bytes = path.stat().st_size if path.is_file() else -1
            actual_hash = sha256_file(path) if path.is_file() else ""
        except (OSError, TypeError, ValueError):
            actual_bytes = -1
            actual_hash = ""
        _add(
            failures,
            f"construction_run:{name}_bytes",
            is_nonnegative_int(raw.get("bytes")) and raw.get("bytes") == actual_bytes,
        )
        _add(
            failures,
            f"construction_run:{name}_sha256",
            is_lower_sha256(raw.get("sha256")) and raw.get("sha256") == actual_hash,
        )
        if "bytes" in expected:
            _add(failures, f"construction_run:{name}_expected_bytes", raw.get("bytes") == expected["bytes"])
            _add(failures, f"construction_run:{name}_expected_sha256", raw.get("sha256") == expected["sha256"])
        actual_binding_hashes[name] = actual_hash

    raw_path = artifact.get("path")
    required_prefix = authorized["candidate_path_prefix"]
    expected_path = (
        f"{required_prefix}{run_id}/candidate.blend" if isinstance(run_id, str) else ""
    )
    _add(failures, "artifact:path", raw_path == expected_path)
    _add(
        failures,
        "artifact:kind",
        artifact.get("kind") == authorized["required_artifact_kind"],
    )
    artifact_path: Path | None = None
    try:
        artifact_path = resolve_project_path(artifact_root, raw_path)
        actual_bytes = artifact_path.stat().st_size if artifact_path.is_file() else -1
        actual_hash = sha256_file(artifact_path) if artifact_path.is_file() else ""
    except (OSError, TypeError, ValueError):
        actual_bytes = -1
        actual_hash = ""
    _add(
        failures,
        "artifact:bytes",
        is_nonnegative_int(artifact.get("bytes"))
        and artifact.get("bytes", 0) > 0
        and artifact.get("bytes") == actual_bytes,
    )
    _add(
        failures,
        "artifact:sha256",
        is_lower_sha256(artifact.get("sha256")) and artifact.get("sha256") == actual_hash,
    )
    _add(
        failures,
        "artifact:not_preexisting_source",
        raw_path != exact_source["preserved_target_blend_path"]
        and actual_hash != exact_source["preserved_target_blend_sha256"],
    )
    _add(failures, "artifact:run_id_binding", artifact.get("construction_run_id") == run_id)
    _add(
        failures,
        "artifact:source_binding",
        artifact.get("source_sha256") == actual_binding_hashes.get("source"),
    )
    _add(
        failures,
        "artifact:worker_binding",
        artifact.get("worker_sha256") == actual_binding_hashes.get("worker"),
    )
    _add(
        failures,
        "artifact:config_binding",
        artifact.get("config_sha256") == actual_binding_hashes.get("config"),
    )
    created = _parse_utc(artifact.get("created_utc"))
    _add(
        failures,
        "artifact:created_in_run",
        created is not None
        and started is not None
        and ended is not None
        and started <= created <= ended,
    )
    if artifact_path is not None and artifact_path.is_file() and started and ended:
        modified = datetime.fromtimestamp(artifact_path.stat().st_mtime, timezone.utc)
        _add(
            failures,
            "artifact:file_time_in_run",
            started.timestamp() - 5.0 <= modified.timestamp() <= ended.timestamp() + 5.0,
        )

    try:
        digest = evidence_payload_sha256(evidence)
    except (TypeError, ValueError):
        digest = ""
        failures.add("evidence:noncanonical_payload")
    _add(
        failures,
        "evidence:record_sha256",
        is_lower_sha256(evidence.get("record_sha256"))
        and evidence.get("record_sha256") == digest,
    )
    _add(
        failures,
        "artifact:evidence_payload_binding",
        artifact.get("evidence_payload_sha256") == digest
        and run.get("evidence_payload_sha256") == digest,
    )


def _canonical_edge(first: int, second: int) -> tuple[int, int]:
    return (first, second) if first < second else (second, first)


def _face_components(faces: list[dict[str, object]]) -> int:
    edge_faces: dict[tuple[int, int], list[int]] = collections.defaultdict(list)
    for index, face in enumerate(faces):
        vertices = face["vertices"]
        for offset, first in enumerate(vertices):
            edge_faces[_canonical_edge(first, vertices[(offset + 1) % len(vertices)])].append(index)
    adjacency = {index: set() for index in range(len(faces))}
    for owners in edge_faces.values():
        if len(owners) == 2:
            first, second = owners
            adjacency[first].add(second)
            adjacency[second].add(first)
    components = 0
    seen: set[int] = set()
    for start in adjacency:
        if start in seen:
            continue
        components += 1
        queue = collections.deque([start])
        seen.add(start)
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
    return components


def _validate_topology(
    evidence: Mapping[str, object],
    contract: Mapping[str, object],
    failures: set[str],
) -> tuple[list[dict[str, object]], dict[int, list[float]], set[int]]:
    topology = evidence.get("topology")
    if not isinstance(topology, Mapping):
        failures.add("topology:missing")
        return [], {}, set()
    face_records = _validate_ledger("topology:faces", topology.get("face_ledger"), failures)
    coordinate_records = _validate_ledger(
        "topology:vertex_coordinates", topology.get("vertex_coordinate_ledger"), failures
    )
    schedule = _validate_ledger(
        "topology:ordered_stitch_schedule", topology.get("ordered_stitch_schedule"), failures
    )
    valid_faces: list[dict[str, object]] = []
    face_ids: set[int] = set()
    for record in face_records:
        if not isinstance(record, Mapping):
            failures.add("topology:malformed_face_record")
            continue
        face_id = record.get("face_id")
        vertices = record.get("vertices")
        if not is_nonnegative_int(face_id) or face_id in face_ids:
            failures.add("topology:face_id")
            continue
        if (
            not isinstance(vertices, list)
            or len(vertices) < 3
            or any(not is_nonnegative_int(value) for value in vertices)
            or len(set(vertices)) != len(vertices)
        ):
            failures.add("topology:face_vertices")
            continue
        _add(
            failures,
            "topology:face_material",
            record.get("material_index") == contract["exact_source"]["preserved_material_index"],
        )
        face_ids.add(face_id)
        valid_faces.append(dict(record))
    _add(failures, "topology:face_records_complete", len(valid_faces) == len(face_records) and bool(valid_faces))

    coordinates: dict[int, list[float]] = {}
    for record in coordinate_records:
        if not isinstance(record, Mapping):
            failures.add("topology:malformed_coordinate_record")
            continue
        vertex_index = record.get("vertex_index")
        coordinate = record.get("coordinate_m")
        if (
            not is_nonnegative_int(vertex_index)
            or vertex_index in coordinates
            or not finite_vector(coordinate, 3)
        ):
            failures.add("topology:vertex_coordinate")
            continue
        coordinates[vertex_index] = list(coordinate)
    used_vertices = {
        vertex for face in valid_faces for vertex in face["vertices"]
    }
    _add(failures, "topology:coordinate_coverage", set(coordinates) == used_vertices)

    cycle = contract["exact_topology"]["outer_boundary_cycle"]
    _add(failures, "topology:outer_cycle_exact", topology.get("outer_boundary_cycle") == cycle)
    edge_owners: dict[tuple[int, int], list[tuple[int, int]]] = collections.defaultdict(list)
    for face_index, face in enumerate(valid_faces):
        vertices = face["vertices"]
        for offset, first in enumerate(vertices):
            second = vertices[(offset + 1) % len(vertices)]
            edge_owners[_canonical_edge(first, second)].append((face_index, 1 if first < second else -1))
    _add(failures, "topology:manifold", bool(edge_owners) and all(len(owners) <= 2 for owners in edge_owners.values()))
    boundary = {edge for edge, owners in edge_owners.items() if len(owners) == 1}
    expected_boundary = {
        _canonical_edge(cycle[index], cycle[(index + 1) % len(cycle)])
        for index in range(len(cycle))
    }
    _add(failures, "topology:fixed_outer_boundary", boundary == expected_boundary)
    _add(failures, "topology:zero_outer_boundary_splits", len(boundary) == 41)
    _add(
        failures,
        "topology:orientable_winding",
        all(len(owners) != 2 or owners[0][1] != owners[1][1] for owners in edge_owners.values()),
    )
    _add(failures, "topology:one_component", bool(valid_faces) and _face_components(valid_faces) == 1)
    euler = len(used_vertices) - len(edge_owners) + len(valid_faces)
    _add(failures, "topology:one_disk_euler", euler == 1)
    odd_sided_count = sum(len(face["vertices"]) % 2 == 1 for face in valid_faces)
    _add(
        failures,
        "topology:mixed_parity",
        odd_sided_count > 0 and odd_sided_count % 2 == 1,
    )

    schedule_by_order: list[dict[str, object]] = []
    for record in schedule:
        if not isinstance(record, Mapping):
            failures.add("topology:malformed_schedule_record")
            continue
        schedule_by_order.append(dict(record))
    expected_schedule = [
        {
            "order": order,
            "operation": "emit_face",
            "face_id": face["face_id"],
            "vertices": face["vertices"],
        }
        for order, face in enumerate(valid_faces)
    ]
    _add(
        failures,
        "topology:schedule_bound_to_faces",
        schedule_by_order == expected_schedule,
    )
    return valid_faces, coordinates, used_vertices - set(cycle)


def _validate_scope(
    evidence: Mapping[str, object],
    context: Mapping[str, object],
    failures: set[str],
) -> None:
    scope = evidence.get("scope")
    if not isinstance(scope, Mapping):
        failures.add("scope:missing")
        return
    faces = context["source_mesh"]["faces"]
    estar = sorted(context["domains"]["estar"])
    collar = sorted(context["domains"]["collar"])
    expected_consumed = [
        {"source_face_index": index, "vertices": list(faces[index])}
        for index in estar
    ]
    expected_collar = [
        {
            "source_face_index": index,
            "vertices": list(faces[index]),
            "disposition": "consumed_by_complete_estar_structured_retopology",
        }
        for index in collar
    ]
    _validate_ledger(
        "scope:consumed_estar_faces",
        scope.get("consumed_estar_face_ledger"),
        failures,
        expected=expected_consumed,
        exact_count=context["contract"]["exact_topology"]["estar_face_count"],
    )
    _validate_ledger(
        "scope:collar_disposition",
        scope.get("collar_disposition_ledger"),
        failures,
        expected=expected_collar,
        exact_count=context["contract"]["exact_topology"]["collar_face_count"],
    )


def _source_weight_map(
    context: Mapping[str, object],
    triangle: Sequence[int],
    barycentric: Sequence[float],
) -> list[dict[str, object]]:
    source = context["source_mesh"]
    combined: dict[int, float] = collections.defaultdict(float)
    for vertex_index, barycentric_weight in zip(triangle, barycentric, strict=True):
        for joint, weight in zip(
            source["joints"][vertex_index], source["weights"][vertex_index], strict=True
        ):
            if float(weight) > 0:
                combined[int(joint)] += float(barycentric_weight) * float(weight)
    total = sum(combined.values())
    if not math.isfinite(total) or total <= 0:
        return []
    return [
        {"joint_index": joint, "weight": weight / total}
        for joint, weight in sorted(combined.items())
        if weight > 1e-12
    ]


def _validate_provenance(
    evidence: Mapping[str, object],
    context: Mapping[str, object],
    failures: set[str],
    coordinates: Mapping[int, list[float]],
    new_vertices: set[int],
    shape_key_names: list[str],
    uv_layer_names: list[str],
) -> None:
    provenance = evidence.get("provenance")
    if not isinstance(provenance, Mapping):
        failures.add("provenance:missing")
        return
    records = _validate_ledger(
        "provenance:new_vertices",
        provenance.get("new_vertex_ledger"),
        failures,
        exact_count=len(new_vertices),
    )
    source = context["source_mesh"]
    seen: set[int] = set()
    maximum = context["contract"]["metric_bounds"]["maximum_new_interior_vertices"]
    _add(
        failures,
        "provenance:new_vertex_budget",
        is_nonnegative_int(len(new_vertices)) and len(new_vertices) <= maximum,
    )
    for record in records:
        if not isinstance(record, Mapping):
            failures.add("provenance:malformed_record")
            continue
        vertex_index = record.get("vertex_index")
        if not is_nonnegative_int(vertex_index) or vertex_index in seen:
            failures.add("provenance:vertex_index")
            continue
        seen.add(vertex_index)
        face_index = record.get("source_face_index")
        triangle = record.get("source_triangle")
        barycentric = record.get("barycentric")
        if (
            not is_nonnegative_int(face_index)
            or face_index >= len(source["faces"])
            or triangle != source["faces"][face_index]
            or not finite_vector(barycentric, 3)
            or any(float(weight) < 0 for weight in barycentric)
            or not math.isclose(sum(float(weight) for weight in barycentric), 1.0, rel_tol=0.0, abs_tol=1e-8)
        ):
            failures.add("provenance:source_triangle_barycentric")
            continue
        computed_source = [
            sum(
                float(barycentric[corner]) * float(source["positions"][triangle[corner]][axis])
                for corner in range(3)
            )
            for axis in range(3)
        ]
        source_position = record.get("source_position_m")
        displacement = record.get("displacement_m")
        final_position = record.get("final_position_m")
        length = record.get("displacement_length_m")
        _add(
            failures,
            "provenance:source_position",
            finite_vector(source_position, 3) and vector_close(source_position, computed_source),
        )
        _add(failures, "provenance:finite_displacement", finite_vector(displacement, 3))
        if finite_vector(source_position, 3) and finite_vector(displacement, 3):
            computed_final = [float(source_position[i]) + float(displacement[i]) for i in range(3)]
            computed_length = math.sqrt(sum(float(value) ** 2 for value in displacement))
        else:
            computed_final = []
            computed_length = math.nan
        _add(
            failures,
            "provenance:final_position",
            finite_vector(final_position, 3)
            and bool(computed_final)
            and vector_close(final_position, computed_final)
            and vertex_index in coordinates
            and vector_close(final_position, coordinates[vertex_index]),
        )
        _add(
            failures,
            "provenance:displacement_length",
            is_finite_number(length)
            and float(length) >= 0
            and math.isclose(float(length), computed_length, rel_tol=0.0, abs_tol=1e-9),
        )
        uv_records = record.get("uv_records")
        _add(
            failures,
            "provenance:uv_records",
            isinstance(uv_records, list)
            and [row.get("layer") for row in uv_records if isinstance(row, Mapping)] == uv_layer_names
            and all(
                isinstance(row, Mapping) and finite_vector(row.get("uv"), 2)
                for row in uv_records
            ),
        )
        normal = record.get("normal")
        _add(
            failures,
            "provenance:normal",
            finite_vector(normal, 3)
            and math.isclose(
                math.sqrt(sum(float(value) ** 2 for value in normal)),
                1.0,
                rel_tol=0.0,
                abs_tol=1e-6,
            ),
        )
        actual_weights = record.get("native_weights")
        expected_weights = _source_weight_map(context, triangle, barycentric)
        weight_ok = isinstance(actual_weights, list) and len(actual_weights) == len(expected_weights)
        if weight_ok:
            for actual, expected in zip(actual_weights, expected_weights, strict=True):
                if (
                    not isinstance(actual, Mapping)
                    or actual.get("joint_index") != expected["joint_index"]
                    or not is_finite_number(actual.get("weight"))
                    or float(actual.get("weight")) < 0
                    or not math.isclose(
                        float(actual.get("weight")), expected["weight"], rel_tol=0.0, abs_tol=1e-7
                    )
                ):
                    weight_ok = False
                    break
        _add(failures, "provenance:native_weights", weight_ok and bool(expected_weights))
        _add(
            failures,
            "provenance:material",
            record.get("material_index") == context["contract"]["exact_source"]["preserved_material_index"],
        )
        shape_records = record.get("shape_key_records")
        _add(
            failures,
            "provenance:shape_keys",
            isinstance(shape_records, list)
            and [row.get("name") for row in shape_records if isinstance(row, Mapping)] == shape_key_names
            and all(
                isinstance(row, Mapping) and finite_vector(row.get("delta_m"), 3)
                for row in shape_records
            ),
        )
    _add(failures, "provenance:complete_vertex_set", seen == new_vertices)


def _validate_attributes(
    evidence: Mapping[str, object],
    context: Mapping[str, object],
    failures: set[str],
) -> tuple[list[str], list[str]]:
    attributes = evidence.get("attributes")
    if not isinstance(attributes, Mapping):
        failures.add("attributes:missing")
        return [], []
    materials, _ = _validate_paired_ledger(
        "attributes:materials", attributes.get("material_inventory"), failures
    )
    material_indices = [
        row.get("material_index") for row in materials if isinstance(row, Mapping)
    ]
    _add(
        failures,
        "attributes:preserved_material_present",
        context["contract"]["exact_source"]["preserved_material_index"] in material_indices,
    )
    uv_layers, _ = _validate_paired_ledger(
        "attributes:uv_layers", attributes.get("uv_layer_inventory"), failures
    )
    uv_names = [row.get("name") for row in uv_layers if isinstance(row, Mapping)]
    _add(
        failures,
        "attributes:uv_layer_names",
        bool(uv_names)
        and len(uv_names) == len(set(uv_names))
        and all(isinstance(name, str) and name for name in uv_names),
    )
    shape_keys, _ = _validate_paired_ledger(
        "attributes:shape_keys", attributes.get("shape_key_inventory"), failures
    )
    shape_names = [row.get("name") for row in shape_keys if isinstance(row, Mapping)]
    shape_ok = (
        len(shape_names) == context["source_mesh"]["morph_target_count"]
        and len(shape_names) == len(set(shape_names))
        and all(isinstance(name, str) and name for name in shape_names)
    )
    for row in shape_keys:
        shape_ok = shape_ok and isinstance(row, Mapping) and is_lower_sha256(row.get("data_sha256"))
    _add(failures, "attributes:shape_key_inventory", shape_ok)
    _add(
        failures,
        "attributes:exact_source_uv_inventory",
        uv_layers == [{"name": "TEXCOORD_0", "domain": "CORNER", "components": 2}],
    )
    expected_mode = (
        "reconstructed_from_exact_source_inventory"
        if shape_names
        else "source_has_no_shape_keys"
    )
    _add(
        failures,
        "attributes:shape_key_disposition",
        attributes.get("shape_key_disposition") == expected_mode,
    )
    return [str(name) for name in shape_names], [str(name) for name in uv_names]


def _validate_rig(
    evidence: Mapping[str, object],
    context: Mapping[str, object],
    failures: set[str],
) -> None:
    rig = evidence.get("rig")
    if not isinstance(rig, Mapping):
        failures.add("rig:missing")
        return
    requirements = context["contract"]["rig_and_action_requirements"]
    armatures, _ = _validate_paired_ledger(
        "rig:armature_inventory", rig.get("armature_inventory"), failures, exact_count=1
    )
    armature_ok = len(armatures) == 1 and isinstance(armatures[0], Mapping)
    if armature_ok:
        record = armatures[0]
        bones = record.get("bone_names")
        armature_ok = (
            record.get("name") == requirements["required_armature_name"]
            and record.get("rest_structure_sha256")
            == requirements["required_armature_rest_structure_sha256"]
            and is_nonnegative_int(record.get("bone_count"))
            and record.get("bone_count") == requirements["required_armature_bone_count"]
            and isinstance(bones, list)
            and len(bones) == requirements["required_armature_bone_count"]
            and len(bones) == len(set(bones))
            and all(isinstance(name, str) and name for name in bones)
            and is_lower_sha256(record.get("bone_names_sha256"))
            and record.get("bone_names_sha256") == canonical_sha256(bones)
        )
    _add(failures, "rig:exact_native_armature", armature_ok)
    actions, _ = _validate_paired_ledger(
        "rig:action_inventory", rig.get("action_inventory"), failures
    )
    action_names = [row.get("name") for row in actions if isinstance(row, Mapping)]
    action_ok = (
        action_names == requirements["required_action_names"]
        and all(
            isinstance(row, Mapping) and is_lower_sha256(row.get("fcurve_data_sha256"))
            for row in actions
        )
    )
    _add(failures, "rig:exact_action_inventory", action_ok)


def _validate_protected_records(
    evidence: Mapping[str, object],
    context: Mapping[str, object],
    failures: set[str],
) -> None:
    protected = evidence.get("protected_records")
    if not isinstance(protected, Mapping):
        failures.add("protected_records:missing")
        return
    expected_sets = {
        "outside_estar": expected_outside_records(context),
        "outer_boundary": expected_outer_boundary_records(context),
    }
    for scope_name, expected_domains in expected_sets.items():
        raw_scope = protected.get(scope_name)
        if not isinstance(raw_scope, Mapping):
            failures.add(f"protected_records:{scope_name}:missing")
            continue
        _add(
            failures,
            f"protected_records:{scope_name}:exact_domains",
            set(raw_scope) == {"POINT", "EDGE", "FACE", "CORNER"},
        )
        for domain in ("POINT", "EDGE", "FACE", "CORNER"):
            _validate_paired_ledger(
                f"protected_records:{scope_name}:{domain}",
                raw_scope.get(domain),
                failures,
                expected=expected_domains[domain],
                exact_count=len(expected_domains[domain]),
            )


def _triangle_measurements(points: Sequence[Sequence[float]]) -> tuple[float, list[float]]:
    first, second, third = points
    ab = [float(second[i]) - float(first[i]) for i in range(3)]
    ac = [float(third[i]) - float(first[i]) for i in range(3)]
    cross = [
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    ]
    area = 0.5 * math.sqrt(sum(value * value for value in cross))
    lengths = [
        math.dist(first, second),
        math.dist(second, third),
        math.dist(third, first),
    ]
    angles: list[float] = []
    for index in range(3):
        side_a = lengths[index]
        side_b = lengths[(index + 2) % 3]
        opposite = lengths[(index + 1) % 3]
        if side_a <= 0 or side_b <= 0:
            angles.append(0.0)
            continue
        cosine = (side_a * side_a + side_b * side_b - opposite * opposite) / (
            2.0 * side_a * side_b
        )
        angles.append(math.degrees(math.acos(max(-1.0, min(1.0, cosine)))))
    return area, angles


def render_triangle_records(
    faces: Sequence[Mapping[str, object]], coordinates: Mapping[int, Sequence[float]]
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    triangle_index = 0
    for face in faces:
        vertices = face["vertices"]
        for corner in range(1, len(vertices) - 1):
            corner_indices = [0, corner, corner + 1]
            triangle_vertices = [vertices[index] for index in corner_indices]
            area, angles = _triangle_measurements(
                [coordinates[index] for index in triangle_vertices]
            )
            records.append(
                {
                    "triangle_index": triangle_index,
                    "face_id": face["face_id"],
                    "polygon_corner_indices": corner_indices,
                    "vertices": triangle_vertices,
                    "area_m2": area,
                    "angles_degrees": angles,
                }
            )
            triangle_index += 1
    return records


def _validate_render(
    evidence: Mapping[str, object],
    contract: Mapping[str, object],
    failures: set[str],
    faces: list[dict[str, object]],
    coordinates: Mapping[int, list[float]],
) -> None:
    render = evidence.get("render")
    if not isinstance(render, Mapping):
        failures.add("render:missing")
        return
    actual = _validate_ledger(
        "render:triangle_ledger", render.get("triangle_ledger"), failures
    )
    try:
        expected = render_triangle_records(faces, coordinates)
    except (KeyError, TypeError, ValueError):
        expected = []
        failures.add("render:coordinate_derivation")
    measurements_match = len(actual) == len(expected)
    if measurements_match:
        for candidate, derived in zip(actual, expected, strict=True):
            if not isinstance(candidate, Mapping):
                measurements_match = False
                break
            exact_fields = ("triangle_index", "face_id", "polygon_corner_indices", "vertices")
            if any(candidate.get(field) != derived[field] for field in exact_fields):
                measurements_match = False
                break
            if (
                not is_finite_number(candidate.get("area_m2"))
                or not math.isclose(
                    float(candidate["area_m2"]), derived["area_m2"], rel_tol=0.0, abs_tol=1e-12
                )
                or not finite_vector(candidate.get("angles_degrees"), 3)
                or not vector_close(candidate["angles_degrees"], derived["angles_degrees"], 1e-8)
            ):
                measurements_match = False
                break
    _add(failures, "render:triangle_ledger_derived", measurements_match and bool(expected))
    if expected:
        minimum_area = min(row["area_m2"] for row in expected)
        minimum_angle = min(min(row["angles_degrees"]) for row in expected)
        _add(
            failures,
            "render:minimum_triangle_area",
            math.isfinite(minimum_area)
            and minimum_area >= contract["metric_bounds"]["minimum_render_triangle_area_m2"],
        )
        _add(
            failures,
            "render:minimum_triangle_angle",
            math.isfinite(minimum_angle)
            and minimum_angle >= contract["metric_bounds"]["minimum_render_triangle_angle_degrees"],
        )


def _valid_pair_records(records: list[object]) -> bool:
    identities: set[tuple[str, int, str, int]] = set()
    for raw in records:
        if not isinstance(raw, Mapping):
            return False
        object_a = raw.get("object_a")
        object_b = raw.get("object_b")
        triangle_a = raw.get("triangle_a")
        triangle_b = raw.get("triangle_b")
        if (
            not isinstance(object_a, str)
            or not object_a
            or not isinstance(object_b, str)
            or not object_b
            or not is_nonnegative_int(triangle_a)
            or not is_nonnegative_int(triangle_b)
            or not is_lower_sha256(raw.get("measurement_sha256"))
        ):
            return False
        first = (object_a, triangle_a)
        second = (object_b, triangle_b)
        identity = (*first, *second) if first <= second else (*second, *first)
        if identity in identities:
            return False
        identities.add(identity)
    return True


def _validate_intersections(
    evidence: Mapping[str, object],
    contract: Mapping[str, object],
    failures: set[str],
) -> None:
    intersections = evidence.get("intersections")
    if not isinstance(intersections, Mapping):
        failures.add("intersections:missing")
        return
    requirements = contract["intersection_and_interface_requirements"]
    for name, count_key in (
        ("standalone_patch_pairs", "standalone_patch_pair_count"),
        ("post_graft_patch_pairs", "post_graft_patch_pair_count"),
        ("new_noninherited_pairs", "new_noninherited_pair_count"),
    ):
        records = _validate_ledger(
            f"intersections:{name}",
            intersections.get(name),
            failures,
            exact_count=requirements[count_key],
        )
        _add(failures, f"intersections:{name}:records", _valid_pair_records(records))
    inherited_source, inherited_candidate = _validate_paired_ledger(
        "intersections:inherited_nonpatch_pairs",
        intersections.get("inherited_nonpatch_pairs"),
        failures,
        exact_count=requirements["inherited_nonpatch_pair_count"],
    )
    _add(
        failures,
        "intersections:inherited_nonpatch_pair_records",
        _valid_pair_records(inherited_source) and _valid_pair_records(inherited_candidate),
    )


def _validate_interface(
    evidence: Mapping[str, object],
    contract: Mapping[str, object],
    failures: set[str],
) -> None:
    interface = evidence.get("global_interface")
    if not isinstance(interface, Mapping):
        failures.add("global_interface:missing")
        return
    requirements = contract["intersection_and_interface_requirements"]
    source, candidate = _validate_paired_ledger(
        "global_interface:coordinates",
        interface.get("coordinate_ledger"),
        failures,
        exact_count=requirements["global_interface_vertex_count"],
    )
    expected_indices = requirements["global_interface_vertex_indices"]
    coordinate_ok = [
        row.get("vertex_index") for row in source if isinstance(row, Mapping)
    ] == expected_indices and all(
        isinstance(row, Mapping) and finite_vector(row.get("coordinate_m"), 3)
        for row in source
    )
    _add(failures, "global_interface:exact_coordinate_records", coordinate_ok and source == candidate)
    _add(
        failures,
        "global_interface:legacy_source_digest",
        interface.get("legacy_source_world_coordinate_sha256")
        == requirements["legacy_source_world_coordinate_sha256"],
    )
    welds = _validate_ledger(
        "global_interface:welds",
        interface.get("weld_ledger"),
        failures,
        exact_count=requirements["required_unique_weld_count"],
    )
    weld_ok = [
        row.get("vertex_index") for row in welds if isinstance(row, Mapping)
    ] == expected_indices and all(
        isinstance(row, Mapping)
        and is_finite_number(row.get("residual_m"))
        and float(row.get("residual_m")) == 0.0
        for row in welds
    )
    _add(failures, "global_interface:exact_unique_weld_records", weld_ok)


def _validate_truth(evidence: Mapping[str, object], failures: set[str]) -> None:
    truth = evidence.get("truth")
    if not isinstance(truth, Mapping):
        failures.add("truth:missing")
        return
    expected = [
        {"property": "privacy", "value": "private"},
        {"property": "activation", "value": "inactive"},
        {"property": "assignment", "value": "unassigned"},
        {"property": "publication", "value": "unpublished"},
        {"property": "owner_approval", "value": "not_claimed"},
    ]
    _validate_ledger("truth:state", truth.get("state_ledger"), failures, expected=expected, exact_count=5)


def evaluate_measured_candidate_evidence(
    evidence: Mapping[str, object] | None,
    contract: Mapping[str, object] | None = None,
    *,
    binding_root: Path = ROOT,
    artifact_root: Path = ROOT,
) -> dict[str, object]:
    contract = load_contract() if contract is None else contract
    schema = contract["authorized_implementation"]["required_gate_schema"]
    if not isinstance(evidence, Mapping):
        return {
            "schema": schema,
            "eligible": False,
            "failure_names": ["measured_candidate_evidence_absent"],
        }
    failures: set[str] = set()
    _add(
        failures,
        "evidence:schema",
        evidence.get("schema")
        == contract["authorized_implementation"]["required_evidence_schema"],
    )
    _scan_numeric_truth(evidence, failures)
    context = dict(static_context())
    context["contract"] = contract

    _validate_artifact_and_run(
        evidence,
        contract,
        failures,
        binding_root=binding_root,
        artifact_root=artifact_root,
    )
    faces, coordinates, new_vertices = _validate_topology(evidence, contract, failures)
    _validate_scope(evidence, context, failures)
    shape_key_names, uv_layer_names = _validate_attributes(evidence, context, failures)
    _validate_rig(evidence, context, failures)
    _validate_protected_records(evidence, context, failures)
    _validate_provenance(
        evidence,
        context,
        failures,
        coordinates,
        new_vertices,
        shape_key_names,
        uv_layer_names,
    )
    _validate_render(evidence, contract, failures, faces, coordinates)
    _validate_intersections(evidence, contract, failures)
    _validate_interface(evidence, contract, failures)
    _validate_truth(evidence, failures)
    return {
        "schema": schema,
        "eligible": not failures,
        "failure_names": sorted(failures),
        "derived": {
            "topology_face_record_count": len(faces),
            "topology_vertex_record_count": len(coordinates),
            "new_interior_vertex_record_count": len(new_vertices),
            "asserted_boolean_accepted": False,
            "scalar_only_measurement_accepted": False,
        },
    }


def static_evaluation() -> dict[str, object]:
    contract = load_contract()
    parent_bindings = validate_parent_bindings(contract)
    context = static_context()
    future = evaluate_measured_candidate_evidence(None, contract)
    return {
        "schema": "kira.avatar.r24.intrinsic_curved_annulus_structured_retopology_r2_static_evaluation.v1",
        "status": "STATIC_R2_GATE_IMPLEMENTED_FUTURE_EVIDENCE_ABSENT_INDEPENDENT_AUDIT_REQUIRED",
        "parent_binding_count": len(parent_bindings),
        "source_domain": {
            "estar_face_count": len(context["domains"]["estar"]),
            "collar_face_count": len(context["domains"]["collar"]),
            "outside_face_count": len(context["domains"]["outside"]),
            "outer_boundary_vertex_count": len(context["domains"]["outer_cycle"]),
        },
        "future_measured_candidate": future,
        "blender_used": False,
        "mesh_mutated": False,
        "candidate_created": False,
        "body_repair_claimed": False,
        "execution_authority_granted": False,
    }


def main() -> int:
    print(json.dumps(static_evaluation(), sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
