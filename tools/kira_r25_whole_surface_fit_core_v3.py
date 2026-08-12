"""Deterministic sparse geometry-field kernel for Kira R25.

This module is deliberately Blender-free.  It consumes an already globally
aligned foundation mesh plus externally bound semantic anchors and a protected
AFES-plus-two-ring vertex set.  It returns only a displacement field and
validation evidence.  It does not author a body, infer anatomy, alter a rig,
or grant execution/activation authority.

The solve is a screened harmonic system evaluated with synchronous weighted
Jacobi iterations over same-semantic-region mesh edges.  Storage is O(V + E):
no dense vertex-by-vertex matrix is constructed.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import struct
import weakref
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence


Vec3 = tuple[float, float, float]

SEMANTIC_REGIONS = (
    "face",
    "head",
    "neck",
    "torso",
    "upper_arm.L",
    "lower_arm.L",
    "hand.L",
    "upper_arm.R",
    "lower_arm.R",
    "hand.R",
    "thigh.L",
    "shin.L",
    "foot.L",
    "thigh.R",
    "shin.R",
    "foot.R",
)

TOPOLOGY_CODEC = "kira_r25_topology_le_v1"
VECTOR_FIELD_CODEC = "kira_r25_displacement_field_f64le_v1"
VECTOR_FIELD_HEADER = b"KIRA_R25_DISPLACEMENT_FIELD_F64LE_V1\0"
BASELINE_HEADER = b"KIRA_R25_GLOBALLY_ALIGNED_BASELINE_F64LE_V1\0"
REGION_HEADER = b"KIRA_R25_SEMANTIC_REGIONS_UTF8_V1\0"
INDEX_HEADER = b"KIRA_R25_SORTED_VERTEX_INDEX_SET_U32LE_V1\0"
ANCHOR_HEADER = b"KIRA_R25_ANCHOR_DISPLACEMENTS_F64LE_V1\0"
LIMITS_CODEC = "kira_r25_fit_limits_f64le_v1"
LIMITS_HEADER = b"KIRA_R25_FIT_LIMITS_F64LE_V1\0"
CANDIDATE_HEADER = b"KIRA_R25_CANDIDATE_VERTICES_F64LE_V1\0"

MAX_JACOBI_ITERATIONS = 10_000
MAX_LINE_SEARCH_BACKTRACKS = 64


class WholeSurfaceFitError(ValueError):
    """A fail-closed R25 geometry-field boundary was not satisfied."""


@dataclass(frozen=True)
class FitLimits:
    """Numerical and geometric limits for one deterministic fit."""

    screen_weight: float = 0.25
    jacobi_relaxation: float = 0.85
    convergence_tolerance: float = 1.0e-10
    max_iterations: int = 2_000
    maximum_displacement: float = 0.25
    minimum_triangle_area: float = 1.0e-12
    minimum_area_ratio: float = 0.20
    maximum_area_ratio: float = 5.0
    minimum_orientation_cosine: float = 0.0
    maximum_line_search_backtracks: int = 12


@dataclass(frozen=True)
class FitEvidence:
    qualification_id: str
    vertex_count: int
    edge_count: int
    face_count: int
    triangle_count: int
    connected_components: int
    semantic_region_count: int
    protected_vertex_count: int
    anchor_count: int
    free_vertex_count: int
    sparse_adjacency_slot_count: int
    sparse_storage_units_upper_bound: int
    iteration_count: int
    converged: str
    final_update_inf_fixed_1e12: int
    raw_equation_residual_inf_fixed_1e12: int
    accepted_equation_residual_inf_fixed_1e12: int
    accepted_field_converged: str
    line_search_attempt_count: int
    line_search_scale_numerator: int
    line_search_scale_denominator: int
    line_search_rejections: tuple[str, ...]
    baseline_space: str
    anchor_space: str
    topology_sha256: str
    topology_after_sha256: str
    baseline_sha256: str
    region_sha256: str
    protected_sha256: str
    anchor_sha256: str
    limits_sha256: str
    raw_displacement_sha256: str
    accepted_displacement_sha256: str
    candidate_vertex_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "qualification_id": self.qualification_id,
            "vertex_count": self.vertex_count,
            "edge_count": self.edge_count,
            "face_count": self.face_count,
            "triangle_count": self.triangle_count,
            "connected_components": self.connected_components,
            "semantic_region_count": self.semantic_region_count,
            "protected_vertex_count": self.protected_vertex_count,
            "anchor_count": self.anchor_count,
            "free_vertex_count": self.free_vertex_count,
            "sparse_adjacency_slot_count": self.sparse_adjacency_slot_count,
            "sparse_storage_units_upper_bound": self.sparse_storage_units_upper_bound,
            "iteration_count": self.iteration_count,
            "converged": self.converged,
            "final_update_inf_fixed_1e12": self.final_update_inf_fixed_1e12,
            "raw_equation_residual_inf_fixed_1e12": self.raw_equation_residual_inf_fixed_1e12,
            "accepted_equation_residual_inf_fixed_1e12": self.accepted_equation_residual_inf_fixed_1e12,
            "accepted_field_converged": self.accepted_field_converged,
            "line_search_attempt_count": self.line_search_attempt_count,
            "line_search_scale_numerator": self.line_search_scale_numerator,
            "line_search_scale_denominator": self.line_search_scale_denominator,
            "line_search_rejections": list(self.line_search_rejections),
            "baseline_space": self.baseline_space,
            "anchor_space": self.anchor_space,
            "topology_sha256": self.topology_sha256,
            "topology_after_sha256": self.topology_after_sha256,
            "baseline_sha256": self.baseline_sha256,
            "region_sha256": self.region_sha256,
            "protected_sha256": self.protected_sha256,
            "anchor_sha256": self.anchor_sha256,
            "limits_codec": LIMITS_CODEC,
            "limits_sha256": self.limits_sha256,
            "raw_displacement_sha256": self.raw_displacement_sha256,
            "accepted_displacement_sha256": self.accepted_displacement_sha256,
            "candidate_vertex_sha256": self.candidate_vertex_sha256,
        }


@dataclass(frozen=True)
class _ResultBindings:
    baseline_vertices: tuple[Vec3, ...]
    faces: tuple[tuple[int, ...], ...]
    regions: tuple[str, ...]
    protected_vertices: tuple[int, ...]
    anchor_displacements: tuple[tuple[int, Vec3], ...]
    limits: FitLimits
    raw_displacement_field: tuple[Vec3, ...]


def _create_fit_result_api():
    """Keep canonical authority tied to a result produced in this process.

    Direct dataclass construction and ``dataclasses.replace`` produce an
    unregistered object whose canonical methods fail closed.  The retained
    binding snapshot is independently revalidated before serialization.
    """

    construction_token = object()
    registry: dict[
        int,
        tuple[
            weakref.ReferenceType[object],
            _ResultBindings,
            str,
        ],
    ] = {}

    @dataclass(frozen=True)
    class _FitResult:
        displacement_field: tuple[Vec3, ...]
        candidate_vertices: tuple[Vec3, ...]
        evidence: FitEvidence
        _construction_token: object = field(repr=False, compare=False)

        def __post_init__(self) -> None:
            if self._construction_token is not construction_token:
                raise WholeSurfaceFitError("fit_result_not_solver_constructed")

        def canonical_payload(self) -> dict[str, object]:
            record = registry.get(id(self))
            if record is None or record[0]() is not self:
                raise WholeSurfaceFitError("fit_result_not_registered")
            return _validated_result_payload(self, record[1], record[2])

        def canonical_sha256(self) -> str:
            return hashlib.sha256(
                canonical_json_bytes(self.canonical_payload())
            ).hexdigest()

    _FitResult.__name__ = "FitResult"
    _FitResult.__qualname__ = "FitResult"

    def construct(
        displacement_field: tuple[Vec3, ...],
        candidate_vertices: tuple[Vec3, ...],
        evidence: FitEvidence,
        bindings: _ResultBindings,
    ):
        if type(bindings) is not _ResultBindings:
            raise WholeSurfaceFitError("result_bindings_type_invalid")
        result = _FitResult(
            displacement_field,
            candidate_vertices,
            evidence,
            construction_token,
        )
        evidence_digest = hashlib.sha256(
            canonical_json_bytes(evidence.payload())
        ).hexdigest()
        identifier = id(result)

        def discard(_reference, identifier: int = identifier) -> None:
            registry.pop(identifier, None)

        registry[identifier] = (
            weakref.ref(result, discard),
            bindings,
            evidence_digest,
        )
        return result

    return _FitResult, construct


FitResult, _construct_fit_result = _create_fit_result_api()


def _integer(value: object, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise WholeSurfaceFitError(f"{label}_invalid")
    return value


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise WholeSurfaceFitError(f"{label}_not_numeric")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise WholeSurfaceFitError(f"{label}_not_f64") from exc
    if not math.isfinite(result):
        raise WholeSurfaceFitError(f"{label}_nonfinite")
    return 0.0 if result == 0.0 else result


def _vec3(value: object, label: str) -> Vec3:
    if type(value) not in (tuple, list) or len(value) != 3:
        raise WholeSurfaceFitError(f"{label}_not_vec3")
    return (
        _finite(value[0], f"{label}_x"),
        _finite(value[1], f"{label}_y"),
        _finite(value[2], f"{label}_z"),
    )


def _exact_string(value: object, label: str) -> str:
    if type(value) is not str:
        raise WholeSurfaceFitError(f"{label}_not_exact_string")
    return value


def _exact_sha256(value: object, label: str) -> str:
    digest = _exact_string(value, label)
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise WholeSurfaceFitError(f"{label}_not_lowercase_sha256")
    return digest


def _plain_sequence(value: object, label: str, *, allow_empty: bool = True) -> tuple:
    if type(value) not in (tuple, list):
        raise WholeSurfaceFitError(f"{label}_not_plain_sequence")
    snapshot = tuple(value)
    if not allow_empty and not snapshot:
        raise WholeSurfaceFitError(f"{label}_empty")
    return snapshot


def _plain_index_collection(value: object, label: str) -> tuple[object, ...]:
    if type(value) not in (tuple, list, set, frozenset):
        raise WholeSurfaceFitError(f"{label}_not_plain_index_collection")
    return tuple(value)


def _validate_limits(limits: FitLimits) -> None:
    if type(limits) is not FitLimits:
        raise WholeSurfaceFitError("limits_type_invalid")
    positive = (
        (limits.screen_weight, "screen_weight"),
        (limits.jacobi_relaxation, "jacobi_relaxation"),
        (limits.convergence_tolerance, "convergence_tolerance"),
        (limits.maximum_displacement, "maximum_displacement"),
        (limits.minimum_triangle_area, "minimum_triangle_area"),
        (limits.minimum_area_ratio, "minimum_area_ratio"),
        (limits.maximum_area_ratio, "maximum_area_ratio"),
    )
    for value, label in positive:
        if _finite(value, label) <= 0.0:
            raise WholeSurfaceFitError(f"{label}_must_be_positive")
    if limits.jacobi_relaxation > 1.0:
        raise WholeSurfaceFitError("jacobi_relaxation_above_one")
    orientation = _finite(
        limits.minimum_orientation_cosine, "minimum_orientation_cosine"
    )
    if orientation < 0.0 or orientation >= 1.0:
        raise WholeSurfaceFitError("minimum_orientation_cosine_out_of_range")
    if limits.minimum_area_ratio >= limits.maximum_area_ratio:
        raise WholeSurfaceFitError("area_ratio_order_invalid")
    _integer(limits.max_iterations, "max_iterations", 1)
    if limits.max_iterations > MAX_JACOBI_ITERATIONS:
        raise WholeSurfaceFitError("max_iterations_above_absolute_ceiling")
    _integer(
        limits.maximum_line_search_backtracks,
        "maximum_line_search_backtracks",
        0,
    )
    if limits.maximum_line_search_backtracks > MAX_LINE_SEARCH_BACKTRACKS:
        raise WholeSurfaceFitError(
            "maximum_line_search_backtracks_above_absolute_ceiling"
        )


def _normalized_limits(limits: FitLimits) -> FitLimits:
    """Return one exact immutable snapshot; subclasses are not consumed."""

    if type(limits) is not FitLimits:
        raise WholeSurfaceFitError("limits_type_invalid")
    # Read each plain dataclass field once, reject effectful subclasses before
    # conversion, then validate only the new private snapshot.
    values = (
        limits.screen_weight,
        limits.jacobi_relaxation,
        limits.convergence_tolerance,
        limits.max_iterations,
        limits.maximum_displacement,
        limits.minimum_triangle_area,
        limits.minimum_area_ratio,
        limits.maximum_area_ratio,
        limits.minimum_orientation_cosine,
        limits.maximum_line_search_backtracks,
    )
    snapshot = FitLimits(
        screen_weight=_finite(values[0], "screen_weight"),
        jacobi_relaxation=_finite(values[1], "jacobi_relaxation"),
        convergence_tolerance=_finite(values[2], "convergence_tolerance"),
        max_iterations=_integer(values[3], "max_iterations", 1),
        maximum_displacement=_finite(values[4], "maximum_displacement"),
        minimum_triangle_area=_finite(values[5], "minimum_triangle_area"),
        minimum_area_ratio=_finite(values[6], "minimum_area_ratio"),
        maximum_area_ratio=_finite(values[7], "maximum_area_ratio"),
        minimum_orientation_cosine=_finite(
            values[8], "minimum_orientation_cosine"
        ),
        maximum_line_search_backtracks=_integer(
            values[9], "maximum_line_search_backtracks", 0
        ),
    )
    _validate_limits(snapshot)
    return snapshot


def canonical_json_bytes(value: object) -> bytes:
    snapshot = _snapshot_canonical_json(value)
    return json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _snapshot_canonical_json(value: object, where: str = "$") -> object:
    if type(value) is bool or value is None or type(value) is float:
        raise WholeSurfaceFitError(f"canonical_non_integer_string_at:{where}")
    if type(value) in (str, int):
        return value
    if type(value) is list:
        return [
            _snapshot_canonical_json(item, f"{where}[{index}]")
            for index, item in enumerate(value)
        ]
    if type(value) is dict:
        snapshot: dict[str, object] = {}
        for key, item in tuple(value.items()):
            if type(key) is not str:
                raise WholeSurfaceFitError(f"canonical_non_string_key_at:{where}")
            snapshot[key] = _snapshot_canonical_json(item, f"{where}.{key}")
        return snapshot
    raise WholeSurfaceFitError(f"canonical_unsupported_type_at:{where}")


def _pack_vec3(stream: bytearray, value: Sequence[float]) -> None:
    vector = _vec3(value, "vector")
    stream.extend(struct.pack("<ddd", *vector))


def encode_vector_field(vectors: Sequence[Sequence[float]]) -> tuple[str, str]:
    rows = _plain_sequence(vectors, "vector_field")
    raw = bytearray(VECTOR_FIELD_HEADER)
    raw.extend(struct.pack("<I", len(rows)))
    for vector in rows:
        _pack_vec3(raw, vector)
    payload = bytes(raw)
    return base64.b64encode(payload).decode("ascii"), hashlib.sha256(payload).hexdigest()


def vector_field_sha256(vectors: Sequence[Sequence[float]]) -> str:
    return encode_vector_field(vectors)[1]


def baseline_sha256(vertices: Sequence[Sequence[float]]) -> str:
    rows = _plain_sequence(vertices, "baseline_vertices")
    raw = bytearray(BASELINE_HEADER)
    raw.extend(struct.pack("<I", len(rows)))
    for vertex in rows:
        _pack_vec3(raw, vertex)
    return hashlib.sha256(bytes(raw)).hexdigest()


def candidate_vertices_sha256(vertices: Sequence[Sequence[float]]) -> str:
    rows = _plain_sequence(vertices, "candidate_vertices")
    raw = bytearray(CANDIDATE_HEADER)
    raw.extend(struct.pack("<I", len(rows)))
    for vertex in rows:
        _pack_vec3(raw, vertex)
    return hashlib.sha256(bytes(raw)).hexdigest()


def fit_limits_sha256(limits: FitLimits) -> str:
    limits = _normalized_limits(limits)
    raw = bytearray(LIMITS_HEADER)
    raw.extend(
        struct.pack(
            "<ddddddddII",
            _finite(limits.screen_weight, "screen_weight"),
            _finite(limits.jacobi_relaxation, "jacobi_relaxation"),
            _finite(limits.convergence_tolerance, "convergence_tolerance"),
            _finite(limits.maximum_displacement, "maximum_displacement"),
            _finite(limits.minimum_triangle_area, "minimum_triangle_area"),
            _finite(limits.minimum_area_ratio, "minimum_area_ratio"),
            _finite(limits.maximum_area_ratio, "maximum_area_ratio"),
            _finite(limits.minimum_orientation_cosine, "minimum_orientation_cosine"),
            limits.max_iterations,
            limits.maximum_line_search_backtracks,
        )
    )
    return hashlib.sha256(bytes(raw)).hexdigest()


def topology_sha256(vertex_count: int, faces: Sequence[Sequence[int]]) -> str:
    count = _integer(vertex_count, "topology_vertex_count", 1)
    face_rows = _plain_sequence(faces, "topology_faces")
    raw = bytearray(TOPOLOGY_CODEC.encode("ascii") + b"\0")
    raw.extend(struct.pack("<II", count, len(face_rows)))
    duplicate_keys: set[tuple[int, ...]] = set()
    for face_position, face in enumerate(face_rows):
        if type(face) not in (tuple, list) or len(face) < 3:
            raise WholeSurfaceFitError(f"face_invalid:{face_position}")
        face_snapshot = tuple(face)
        raw.extend(struct.pack("<I", len(face_snapshot)))
        seen: set[int] = set()
        checked: list[int] = []
        for value in face_snapshot:
            index = _integer(value, f"face_index:{face_position}")
            if index >= count or index in seen:
                raise WholeSurfaceFitError(f"face_index_duplicate_or_out_of_range:{face_position}")
            seen.add(index)
            checked.append(index)
            raw.extend(struct.pack("<I", index))
        duplicate_key = tuple(sorted(checked))
        if duplicate_key in duplicate_keys:
            raise WholeSurfaceFitError(f"duplicate_face:{face_position}")
        duplicate_keys.add(duplicate_key)
    return hashlib.sha256(bytes(raw)).hexdigest()


def regions_sha256(regions: Sequence[str]) -> str:
    rows = _plain_sequence(regions, "semantic_regions")
    raw = bytearray(REGION_HEADER)
    raw.extend(struct.pack("<I", len(rows)))
    for position, region in enumerate(rows):
        if type(region) is not str or region not in SEMANTIC_REGIONS:
            raise WholeSurfaceFitError(f"unknown_semantic_region:{position}")
        encoded = region.encode("utf-8")
        raw.extend(struct.pack("<I", len(encoded)))
        raw.extend(encoded)
    return hashlib.sha256(bytes(raw)).hexdigest()


def index_set_sha256(indices: Iterable[int], vertex_count: int) -> str:
    count = _integer(vertex_count, "index_set_vertex_count", 1)
    values = _plain_index_collection(indices, "protected_indices")
    checked = []
    seen: set[int] = set()
    for value in values:
        index = _integer(value, "protected_index")
        if index >= count or index in seen:
            raise WholeSurfaceFitError("protected_index_duplicate_or_out_of_range")
        seen.add(index)
        checked.append(index)
    raw = bytearray(INDEX_HEADER)
    raw.extend(struct.pack("<I", len(checked)))
    for index in sorted(checked):
        raw.extend(struct.pack("<I", index))
    return hashlib.sha256(bytes(raw)).hexdigest()


def anchor_displacements_sha256(
    anchors: Mapping[int, Sequence[float]], vertex_count: int
) -> str:
    count = _integer(vertex_count, "anchor_vertex_count", 1)
    if type(anchors) is not dict:
        raise WholeSurfaceFitError("anchor_mapping_invalid")
    snapshot = _snapshot_anchor_displacements(anchors, count)
    raw = bytearray(ANCHOR_HEADER)
    raw.extend(struct.pack("<I", len(snapshot)))
    for index, vector in sorted(snapshot.items()):
        raw.extend(struct.pack("<I", index))
        _pack_vec3(raw, vector)
    return hashlib.sha256(bytes(raw)).hexdigest()


def _snapshot_anchor_displacements(
    anchors: Mapping[int, Sequence[float]], vertex_count: int
) -> dict[int, Vec3]:
    if type(anchors) is not dict:
        raise WholeSurfaceFitError("anchor_mapping_invalid")
    snapshot: dict[int, Vec3] = {}
    # Exactly one traversal of caller-owned mapping state.  Hashing and solving
    # operate only on this new ordinary dict, closing a hash/use split.
    for key, value in anchors.items():
        index = _integer(key, "anchor_index")
        if index >= vertex_count or index in snapshot:
            raise WholeSurfaceFitError("anchor_index_duplicate_or_out_of_range")
        snapshot[index] = _vec3(value, f"anchor_displacement:{index}")
    return snapshot


def _copy_geometry(
    baseline_vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
    vertex_regions: Sequence[str],
) -> tuple[tuple[Vec3, ...], tuple[tuple[int, ...], ...], tuple[str, ...]]:
    baseline_rows = _plain_sequence(
        baseline_vertices, "baseline_vertices", allow_empty=False
    )
    vertices = tuple(
        _vec3(value, f"baseline_vertex:{index}")
        for index, value in enumerate(baseline_rows)
    )
    face_rows = _plain_sequence(faces, "faces", allow_empty=False)
    copied_faces: list[tuple[int, ...]] = []
    duplicate_keys: set[tuple[int, ...]] = set()
    for position, face in enumerate(face_rows):
        if type(face) not in (tuple, list) or len(face) < 3:
            raise WholeSurfaceFitError(f"face_invalid:{position}")
        checked = tuple(_integer(value, f"face_index:{position}") for value in face)
        if len(set(checked)) != len(checked) or any(value >= len(vertices) for value in checked):
            raise WholeSurfaceFitError(f"face_index_duplicate_or_out_of_range:{position}")
        duplicate_key = tuple(sorted(checked))
        if duplicate_key in duplicate_keys:
            raise WholeSurfaceFitError(f"duplicate_face:{position}")
        duplicate_keys.add(duplicate_key)
        copied_faces.append(checked)
    region_rows = _plain_sequence(vertex_regions, "vertex_regions")
    if len(region_rows) != len(vertices):
        raise WholeSurfaceFitError("vertex_region_count_mismatch")
    copied_regions = tuple(region_rows)
    regions_sha256(copied_regions)
    return vertices, tuple(copied_faces), copied_regions


def _build_adjacency(
    vertex_count: int,
    faces: Sequence[Sequence[int]],
    regions: Sequence[str],
) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...], int]:
    all_sets = [set() for _ in range(vertex_count)]
    region_sets = [set() for _ in range(vertex_count)]
    edges: set[tuple[int, int]] = set()
    for face in faces:
        for position, first in enumerate(face):
            second = face[(position + 1) % len(face)]
            edge = (first, second) if first < second else (second, first)
            edges.add(edge)
            all_sets[first].add(second)
            all_sets[second].add(first)
            if regions[first] == regions[second]:
                region_sets[first].add(second)
                region_sets[second].add(first)
    return (
        tuple(tuple(sorted(row)) for row in all_sets),
        tuple(tuple(sorted(row)) for row in region_sets),
        len(edges),
    )


def _component_count(adjacency: Sequence[Sequence[int]], vertices: Iterable[int]) -> int:
    remaining = set(vertices)
    count = 0
    while remaining:
        count += 1
        seed = min(remaining)
        remaining.remove(seed)
        stack = [seed]
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
    return count


def _validate_semantic_components(
    regions: Sequence[str],
    adjacency: Sequence[Sequence[int]],
    protected: set[int],
    anchors: Mapping[int, Vec3],
) -> int:
    present = tuple(region for region in SEMANTIC_REGIONS if region in regions)
    for region in present:
        members = {index for index, value in enumerate(regions) if value == region}
        components = _component_count(adjacency, members)
        if components != 1:
            raise WholeSurfaceFitError(f"same_region_graph_disconnected:{region}:{components}")
        movable = members - protected
        remaining = set(movable)
        while remaining:
            seed = min(remaining)
            remaining.remove(seed)
            component = {seed}
            stack = [seed]
            while stack:
                current = stack.pop()
                for neighbor in adjacency[current]:
                    if neighbor in protected or neighbor not in remaining:
                        continue
                    remaining.remove(neighbor)
                    component.add(neighbor)
                    stack.append(neighbor)
            free = component - set(anchors)
            if free and not (component & set(anchors)):
                raise WholeSurfaceFitError(
                    f"same_region_free_component_without_anchor:{region}:{min(free)}"
                )
    return len(present)


def _triangles(faces: Sequence[Sequence[int]]) -> tuple[tuple[int, int, int], ...]:
    triangles: list[tuple[int, int, int]] = []
    for face in faces:
        for offset in range(1, len(face) - 1):
            triangles.append((face[0], face[offset], face[offset + 1]))
    return tuple(triangles)


def _sub(first: Sequence[float], second: Sequence[float]) -> Vec3:
    return (
        first[0] - second[0],
        first[1] - second[1],
        first[2] - second[2],
    )


def _cross(first: Sequence[float], second: Sequence[float]) -> Vec3:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _dot(first: Sequence[float], second: Sequence[float]) -> float:
    return first[0] * second[0] + first[1] * second[1] + first[2] * second[2]


def _norm(value: Sequence[float]) -> float:
    return math.sqrt(max(0.0, _dot(value, value)))


def _candidate_geometry_issues(
    baseline: Sequence[Vec3],
    candidate: Sequence[Vec3],
    displacements: Sequence[Vec3],
    triangles: Sequence[tuple[int, int, int]],
    limits: FitLimits,
) -> tuple[str, ...]:
    for index, (point, displacement) in enumerate(zip(candidate, displacements)):
        if not all(math.isfinite(value) for value in point):
            return (f"candidate_vertex_nonfinite:{index}",)
        if _norm(displacement) > limits.maximum_displacement + 1.0e-15:
            return (f"maximum_displacement_exceeded:{index}",)
    for triangle_index, (a, b, c) in enumerate(triangles):
        base_normal = _cross(_sub(baseline[b], baseline[a]), _sub(baseline[c], baseline[a]))
        candidate_normal = _cross(
            _sub(candidate[b], candidate[a]), _sub(candidate[c], candidate[a])
        )
        base_twice_area = _norm(base_normal)
        candidate_twice_area = _norm(candidate_normal)
        if not math.isfinite(base_twice_area) or base_twice_area * 0.5 <= limits.minimum_triangle_area:
            raise WholeSurfaceFitError(f"baseline_triangle_degenerate:{triangle_index}")
        if not math.isfinite(candidate_twice_area):
            return (f"candidate_triangle_nonfinite:{triangle_index}",)
        if candidate_twice_area * 0.5 <= limits.minimum_triangle_area:
            return (f"candidate_triangle_degenerate:{triangle_index}",)
        orientation = _dot(base_normal, candidate_normal) / (
            base_twice_area * candidate_twice_area
        )
        if not math.isfinite(orientation):
            return (f"candidate_orientation_nonfinite:{triangle_index}",)
        if orientation <= limits.minimum_orientation_cosine:
            return (f"candidate_triangle_orientation_flip:{triangle_index}",)
        ratio = candidate_twice_area / base_twice_area
        if ratio < limits.minimum_area_ratio or ratio > limits.maximum_area_ratio:
            return (f"candidate_triangle_area_ratio:{triangle_index}",)
    return ()


def _line_search_anchor_preserving(
    *,
    baseline_vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
    raw_displacements: Sequence[Sequence[float]],
    anchor_indices: Iterable[int],
    protected_indices: Iterable[int],
    limits: FitLimits,
) -> tuple[tuple[Vec3, ...], tuple[Vec3, ...], int, tuple[str, ...]]:
    """Backtrack only propagated vertices while keeping constraints exact.

    Semantic anchor values are never scaled.  Protected values are exactly
    ``(0.0, 0.0, 0.0)``.  The scale therefore applies only to the propagated
    free field; if the fixed constraints themselves are unsafe, every trial is
    rejected and this function fails closed.
    """

    limits = _normalized_limits(limits)
    baseline_rows = _plain_sequence(
        baseline_vertices, "line_baseline_vertices", allow_empty=False
    )
    raw_rows = _plain_sequence(
        raw_displacements, "line_raw_displacements", allow_empty=False
    )
    face_rows = _plain_sequence(faces, "line_faces", allow_empty=False)
    baseline = tuple(
        _vec3(value, f"line_baseline:{i}")
        for i, value in enumerate(baseline_rows)
    )
    raw = tuple(
        _vec3(value, f"line_displacement:{i}")
        for i, value in enumerate(raw_rows)
    )
    if len(raw) != len(baseline):
        raise WholeSurfaceFitError("line_search_field_count_mismatch")
    copied_faces: list[tuple[int, ...]] = []
    duplicate_faces: set[tuple[int, ...]] = set()
    for position, face in enumerate(face_rows):
        if type(face) not in (tuple, list) or len(face) < 3:
            raise WholeSurfaceFitError(f"line_face_invalid:{position}")
        checked = tuple(
            _integer(value, f"line_face_index:{position}") for value in face
        )
        if len(set(checked)) != len(checked) or any(
            value >= len(baseline) for value in checked
        ):
            raise WholeSurfaceFitError(
                f"line_face_index_duplicate_or_out_of_range:{position}"
            )
        duplicate_key = tuple(sorted(checked))
        if duplicate_key in duplicate_faces:
            raise WholeSurfaceFitError(f"line_duplicate_face:{position}")
        duplicate_faces.add(duplicate_key)
        copied_faces.append(checked)
    copied_faces_tuple = tuple(copied_faces)
    topology_sha256(len(baseline), copied_faces_tuple)
    anchor_values = _plain_index_collection(
        anchor_indices, "line_search_anchor_indices"
    )
    protected_values = _plain_index_collection(
        protected_indices, "line_search_protected_indices"
    )
    anchors: set[int] = set()
    protected: set[int] = set()
    for value in anchor_values:
        index = _integer(value, "line_search_anchor_index")
        if index in anchors:
            raise WholeSurfaceFitError("line_search_anchor_index_duplicate")
        anchors.add(index)
    for value in protected_values:
        index = _integer(value, "line_search_protected_index")
        if index in protected:
            raise WholeSurfaceFitError("line_search_protected_index_duplicate")
        protected.add(index)
    if not anchors:
        raise WholeSurfaceFitError("line_search_anchor_set_empty")
    if not protected:
        raise WholeSurfaceFitError("line_search_protected_set_empty")
    if anchors & protected:
        raise WholeSurfaceFitError("line_search_anchor_protected_overlap")
    if any(index < 0 or index >= len(baseline) for index in anchors | protected):
        raise WholeSurfaceFitError("line_search_constraint_out_of_range")
    for index in protected:
        if raw[index] != (0.0, 0.0, 0.0):
            raise WholeSurfaceFitError("line_search_protected_not_exact_zero")
    triangle_rows = _triangles(copied_faces_tuple)
    rejections: list[str] = []
    denominator = 1
    for _attempt in range(limits.maximum_line_search_backtracks + 1):
        field: list[Vec3] = []
        candidate: list[Vec3] = []
        for index, displacement in enumerate(raw):
            if index in protected:
                accepted = (0.0, 0.0, 0.0)
            elif index in anchors:
                accepted = displacement
            else:
                accepted = (
                    displacement[0] / denominator,
                    displacement[1] / denominator,
                    displacement[2] / denominator,
                )
            field.append(accepted)
            candidate.append(
                (
                    baseline[index][0] + accepted[0],
                    baseline[index][1] + accepted[1],
                    baseline[index][2] + accepted[2],
                )
            )
        issues = _candidate_geometry_issues(
            baseline, candidate, field, triangle_rows, limits
        )
        if not issues:
            return tuple(field), tuple(candidate), denominator, tuple(rejections)
        rejections.append(f"scale_1_over_{denominator}:{issues[0]}")
        denominator *= 2
    raise WholeSurfaceFitError(
        "line_search_no_safe_anchor_preserving_scale:" + "|".join(rejections)
    )


def _equation_residual(
    field: Sequence[Vec3],
    adjacency: Sequence[Sequence[int]],
    free_vertices: Sequence[int],
    screen_weight: float,
) -> float:
    residual = 0.0
    for index in free_vertices:
        neighbors = adjacency[index]
        denominator = len(neighbors) + screen_weight
        for axis in range(3):
            target = sum(field[neighbor][axis] for neighbor in neighbors) / denominator
            residual = max(residual, abs(field[index][axis] - target))
    return residual


def _fixed_1e12(value: float, label: str) -> int:
    if not math.isfinite(value) or value < 0.0 or value > 9_000_000.0:
        raise WholeSurfaceFitError(f"{label}_cannot_encode")
    return int(round(value * 1_000_000_000_000))


_EVIDENCE_INTEGER_FIELDS = (
    "vertex_count",
    "edge_count",
    "face_count",
    "triangle_count",
    "connected_components",
    "semantic_region_count",
    "protected_vertex_count",
    "anchor_count",
    "free_vertex_count",
    "sparse_adjacency_slot_count",
    "sparse_storage_units_upper_bound",
    "iteration_count",
    "final_update_inf_fixed_1e12",
    "raw_equation_residual_inf_fixed_1e12",
    "accepted_equation_residual_inf_fixed_1e12",
    "line_search_attempt_count",
    "line_search_scale_numerator",
    "line_search_scale_denominator",
)

_EVIDENCE_STRING_FIELDS = (
    "qualification_id",
    "converged",
    "accepted_field_converged",
    "baseline_space",
    "anchor_space",
)

_EVIDENCE_HASH_FIELDS = (
    "topology_sha256",
    "topology_after_sha256",
    "baseline_sha256",
    "region_sha256",
    "protected_sha256",
    "anchor_sha256",
    "limits_sha256",
    "raw_displacement_sha256",
    "accepted_displacement_sha256",
    "candidate_vertex_sha256",
)


def _validate_evidence_scalar_types(evidence: FitEvidence) -> None:
    if type(evidence) is not FitEvidence:
        raise WholeSurfaceFitError("result_evidence_type_invalid")
    for name in _EVIDENCE_INTEGER_FIELDS:
        _integer(getattr(evidence, name), f"evidence_{name}")
    for name in _EVIDENCE_STRING_FIELDS:
        _exact_string(getattr(evidence, name), f"evidence_{name}")
    for name in _EVIDENCE_HASH_FIELDS:
        _exact_sha256(getattr(evidence, name), f"evidence_{name}")
    if type(evidence.line_search_rejections) is not tuple:
        raise WholeSurfaceFitError("evidence_line_search_rejections_not_tuple")
    for position, reason in enumerate(evidence.line_search_rejections):
        _exact_string(reason, f"evidence_line_search_rejection:{position}")


def _validated_result_payload(
    result,
    bindings: _ResultBindings,
    expected_evidence_digest: str,
) -> dict[str, object]:
    """Recompute every retained geometry/result binding before claiming YES."""

    if type(bindings) is not _ResultBindings:
        raise WholeSurfaceFitError("result_bindings_type_invalid")
    evidence = result.evidence
    _validate_evidence_scalar_types(evidence)
    expected_digest = _exact_sha256(
        expected_evidence_digest, "registered_evidence_sha256"
    )
    evidence_payload = evidence.payload()
    actual_digest = hashlib.sha256(canonical_json_bytes(evidence_payload)).hexdigest()
    if actual_digest != expected_digest:
        raise WholeSurfaceFitError("registered_evidence_drifted")

    baseline, faces, regions = _copy_geometry(
        bindings.baseline_vertices,
        bindings.faces,
        bindings.regions,
    )
    limits = _normalized_limits(bindings.limits)
    protected_rows = _plain_index_collection(
        bindings.protected_vertices, "result_protected_vertices"
    )
    protected_digest = index_set_sha256(protected_rows, len(baseline))
    protected = set(protected_rows)
    if not protected:
        raise WholeSurfaceFitError("result_protected_set_empty")

    anchor_rows = _plain_sequence(
        bindings.anchor_displacements,
        "result_anchor_displacements",
        allow_empty=False,
    )
    anchors: dict[int, Vec3] = {}
    for position, row in enumerate(anchor_rows):
        if type(row) is not tuple or len(row) != 2:
            raise WholeSurfaceFitError(f"result_anchor_row_invalid:{position}")
        index = _integer(row[0], f"result_anchor_index:{position}")
        if index >= len(baseline) or index in anchors:
            raise WholeSurfaceFitError(
                f"result_anchor_duplicate_or_out_of_range:{position}"
            )
        anchors[index] = _vec3(row[1], f"result_anchor_value:{position}")
    if protected & set(anchors):
        raise WholeSurfaceFitError("result_anchor_protected_overlap")

    field_rows = _plain_sequence(
        result.displacement_field,
        "result_displacement_field",
        allow_empty=False,
    )
    candidate_rows = _plain_sequence(
        result.candidate_vertices,
        "result_candidate_vertices",
        allow_empty=False,
    )
    raw_rows = _plain_sequence(
        bindings.raw_displacement_field,
        "result_raw_displacement_field",
        allow_empty=False,
    )
    field = tuple(
        _vec3(row, f"result_displacement:{position}")
        for position, row in enumerate(field_rows)
    )
    candidate = tuple(
        _vec3(row, f"result_candidate:{position}")
        for position, row in enumerate(candidate_rows)
    )
    raw_field = tuple(
        _vec3(row, f"result_raw_displacement:{position}")
        for position, row in enumerate(raw_rows)
    )
    if not (len(field) == len(candidate) == len(raw_field) == len(baseline)):
        raise WholeSurfaceFitError("result_geometry_count_mismatch")
    for index, displacement in enumerate(field):
        expected_candidate = (
            baseline[index][0] + displacement[0],
            baseline[index][1] + displacement[1],
            baseline[index][2] + displacement[2],
        )
        if candidate[index] != expected_candidate:
            raise WholeSurfaceFitError(f"result_candidate_not_baseline_plus_field:{index}")
    for index in protected:
        if field[index] != (0.0, 0.0, 0.0) or candidate[index] != baseline[index]:
            raise WholeSurfaceFitError(f"result_protected_constraint_drifted:{index}")
    for index, displacement in anchors.items():
        if field[index] != displacement:
            raise WholeSurfaceFitError(f"result_anchor_constraint_drifted:{index}")

    topology_digest = topology_sha256(len(baseline), faces)
    baseline_digest = baseline_sha256(baseline)
    region_digest = regions_sha256(regions)
    anchor_digest = anchor_displacements_sha256(anchors, len(baseline))
    limits_digest = fit_limits_sha256(limits)
    raw_digest = vector_field_sha256(raw_field)
    field_digest = vector_field_sha256(field)
    candidate_digest = candidate_vertices_sha256(candidate)
    all_adjacency, region_adjacency, edge_count = _build_adjacency(
        len(baseline), faces, regions
    )
    connected_components = _component_count(
        all_adjacency, range(len(baseline))
    )
    semantic_region_count = _validate_semantic_components(
        regions, region_adjacency, protected, anchors
    )
    if connected_components != 1:
        raise WholeSurfaceFitError("result_topology_not_single_component")
    fixed = protected | set(anchors)
    free_vertices = tuple(
        index for index in range(len(baseline)) if index not in fixed
    )
    raw_residual = _equation_residual(
        raw_field, region_adjacency, free_vertices, limits.screen_weight
    )
    accepted_residual = _equation_residual(
        field, region_adjacency, free_vertices, limits.screen_weight
    )
    if raw_residual > limits.convergence_tolerance:
        raise WholeSurfaceFitError("result_raw_field_not_converged")
    if accepted_residual > limits.convergence_tolerance:
        raise WholeSurfaceFitError("result_accepted_field_not_converged")
    geometry_issues = _candidate_geometry_issues(
        baseline, candidate, field, _triangles(faces), limits
    )
    if geometry_issues:
        raise WholeSurfaceFitError("result_candidate_geometry_invalid:" + geometry_issues[0])

    adjacency_slots = sum(len(row) for row in region_adjacency)
    storage_upper_bound = (
        len(baseline) * 12
        + adjacency_slots * 2
        + len(faces) * 4
        + len(anchors) * 8
    )
    exact_expectations = {
        "vertex_count": len(baseline),
        "edge_count": edge_count,
        "face_count": len(faces),
        "triangle_count": len(_triangles(faces)),
        "connected_components": connected_components,
        "semantic_region_count": semantic_region_count,
        "protected_vertex_count": len(protected),
        "anchor_count": len(anchors),
        "free_vertex_count": len(free_vertices),
        "sparse_adjacency_slot_count": adjacency_slots,
        "sparse_storage_units_upper_bound": storage_upper_bound,
        "raw_equation_residual_inf_fixed_1e12": _fixed_1e12(
            raw_residual, "result_raw_residual"
        ),
        "accepted_equation_residual_inf_fixed_1e12": _fixed_1e12(
            accepted_residual, "result_accepted_residual"
        ),
    }
    for name, expected in exact_expectations.items():
        if getattr(evidence, name) != expected:
            raise WholeSurfaceFitError(f"result_evidence_mismatch:{name}")
    hash_expectations = {
        "topology_sha256": topology_digest,
        "topology_after_sha256": topology_digest,
        "baseline_sha256": baseline_digest,
        "region_sha256": region_digest,
        "protected_sha256": protected_digest,
        "anchor_sha256": anchor_digest,
        "limits_sha256": limits_digest,
        "raw_displacement_sha256": raw_digest,
        "accepted_displacement_sha256": field_digest,
        "candidate_vertex_sha256": candidate_digest,
    }
    for name, expected in hash_expectations.items():
        if getattr(evidence, name) != expected:
            raise WholeSurfaceFitError(f"result_evidence_mismatch:{name}")
    if evidence.qualification_id != "kira_r25_qualified_continuous_foundation":
        raise WholeSurfaceFitError("result_qualification_not_exact")
    if evidence.baseline_space != "globally_aligned_foundation":
        raise WholeSurfaceFitError("result_baseline_space_not_exact")
    if evidence.anchor_space != "globally_aligned_foundation_displacement":
        raise WholeSurfaceFitError("result_anchor_space_not_exact")
    if evidence.converged != "YES" or evidence.accepted_field_converged != "YES":
        raise WholeSurfaceFitError("result_convergence_claim_not_exact")
    if evidence.iteration_count > limits.max_iterations:
        raise WholeSurfaceFitError("result_iteration_count_above_limit")
    if free_vertices and evidence.iteration_count < 1:
        raise WholeSurfaceFitError("result_iteration_count_missing")
    if not free_vertices and evidence.iteration_count != 0:
        raise WholeSurfaceFitError("result_iteration_count_unexpected")
    if evidence.line_search_scale_numerator != 1:
        raise WholeSurfaceFitError("result_line_search_numerator_not_one")
    if evidence.line_search_scale_denominator != 1 << len(
        evidence.line_search_rejections
    ):
        raise WholeSurfaceFitError("result_line_search_denominator_mismatch")
    if evidence.line_search_attempt_count != 1 + len(
        evidence.line_search_rejections
    ):
        raise WholeSurfaceFitError("result_line_search_attempt_count_mismatch")
    if len(evidence.line_search_rejections) > limits.maximum_line_search_backtracks:
        raise WholeSurfaceFitError("result_line_search_backtracks_above_limit")

    encoded, digest = encode_vector_field(field)
    if digest != field_digest:
        raise WholeSurfaceFitError("result_displacement_hash_drifted")
    evidence_payload["validated_claims"] = {
        "topology_index_preserved": "YES",
        "protected_displacements_exact_zero": "YES",
        "anchor_displacements_exact": "YES",
        "same_region_propagation_only": "YES",
        "dense_matrix_constructed": "NO",
        "geometry_field_only": "YES",
    }
    return {
        "schema": "kira.r25.whole_surface_geometry_field.v3",
        "status": "STATIC_GEOMETRY_FIELD_VALIDATED_NOT_A_BODY",
        "displacement_field": {
            "codec": VECTOR_FIELD_CODEC,
            "vertex_count": len(field),
            "base64": encoded,
            "sha256": digest,
        },
        "evidence": evidence_payload,
    }


def solve_r25_whole_surface_fit(
    *,
    qualification_id: str,
    baseline_space: str,
    anchor_space: str,
    baseline_vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
    vertex_regions: Sequence[str],
    protected_vertices: Iterable[int],
    anchor_displacements: Mapping[int, Sequence[float]],
    expected_vertex_count: int,
    expected_edge_count: int,
    expected_face_count: int,
    expected_connected_components: int,
    expected_topology_sha256: str,
    expected_baseline_sha256: str,
    expected_regions_sha256: str,
    expected_protected_sha256: str,
    expected_anchor_sha256: str,
    expected_limits_sha256: str,
    limits: FitLimits = FitLimits(),
) -> FitResult:
    """Solve and validate one externally bound whole-surface field."""

    qualification_id = _exact_string(qualification_id, "qualification_id")
    baseline_space = _exact_string(baseline_space, "baseline_space")
    anchor_space = _exact_string(anchor_space, "anchor_space")
    expected_topology_sha256 = _exact_sha256(
        expected_topology_sha256, "expected_topology_sha256"
    )
    expected_baseline_sha256 = _exact_sha256(
        expected_baseline_sha256, "expected_baseline_sha256"
    )
    expected_regions_sha256 = _exact_sha256(
        expected_regions_sha256, "expected_regions_sha256"
    )
    expected_protected_sha256 = _exact_sha256(
        expected_protected_sha256, "expected_protected_sha256"
    )
    expected_anchor_sha256 = _exact_sha256(
        expected_anchor_sha256, "expected_anchor_sha256"
    )
    expected_limits_sha256 = _exact_sha256(
        expected_limits_sha256, "expected_limits_sha256"
    )
    limits = _normalized_limits(limits)
    limits_digest = fit_limits_sha256(limits)
    if limits_digest != expected_limits_sha256:
        raise WholeSurfaceFitError("fit_limits_sha256_mismatch")
    if qualification_id != "kira_r25_qualified_continuous_foundation":
        raise WholeSurfaceFitError("qualification_id_not_exact")
    if baseline_space != "globally_aligned_foundation":
        raise WholeSurfaceFitError("baseline_space_not_globally_aligned")
    if anchor_space != "globally_aligned_foundation_displacement":
        raise WholeSurfaceFitError("anchor_space_not_exact")
    vertices, copied_faces, regions = _copy_geometry(
        baseline_vertices, faces, vertex_regions
    )
    expected_vertices = _integer(expected_vertex_count, "expected_vertex_count", 1)
    expected_edges = _integer(expected_edge_count, "expected_edge_count", 1)
    expected_faces = _integer(expected_face_count, "expected_face_count", 1)
    expected_components = _integer(
        expected_connected_components, "expected_connected_components", 1
    )
    if len(vertices) != expected_vertices or len(copied_faces) != expected_faces:
        raise WholeSurfaceFitError("qualified_topology_count_mismatch")

    topology_digest = topology_sha256(len(vertices), copied_faces)
    baseline_digest = baseline_sha256(vertices)
    region_digest = regions_sha256(regions)
    if topology_digest != expected_topology_sha256:
        raise WholeSurfaceFitError("qualified_topology_sha256_mismatch")
    if baseline_digest != expected_baseline_sha256:
        raise WholeSurfaceFitError("globally_aligned_baseline_sha256_mismatch")
    if region_digest != expected_regions_sha256:
        raise WholeSurfaceFitError("semantic_region_sha256_mismatch")

    protected_values = _plain_index_collection(
        protected_vertices, "protected_vertices"
    )
    protected_digest = index_set_sha256(protected_values, len(vertices))
    if protected_digest != expected_protected_sha256:
        raise WholeSurfaceFitError("afes_two_ring_protected_sha256_mismatch")
    protected = set(protected_values)
    if not protected:
        raise WholeSurfaceFitError("afes_two_ring_protected_set_empty")

    anchors = _snapshot_anchor_displacements(anchor_displacements, len(vertices))
    anchor_digest = anchor_displacements_sha256(anchors, len(vertices))
    if anchor_digest != expected_anchor_sha256:
        raise WholeSurfaceFitError("semantic_anchor_sha256_mismatch")
    if not anchors:
        raise WholeSurfaceFitError("semantic_anchor_set_empty")
    if protected & set(anchors):
        raise WholeSurfaceFitError("semantic_anchor_inside_afes_two_ring_protected_set")

    all_adjacency, region_adjacency, edge_count = _build_adjacency(
        len(vertices), copied_faces, regions
    )
    if edge_count != expected_edges:
        raise WholeSurfaceFitError("qualified_edge_count_mismatch")
    connected_components = _component_count(all_adjacency, range(len(vertices)))
    if connected_components != expected_components or connected_components != 1:
        raise WholeSurfaceFitError("qualified_topology_not_single_component")
    semantic_region_count = _validate_semantic_components(
        regions, region_adjacency, protected, anchors
    )

    fixed = protected | set(anchors)
    free_vertices = tuple(index for index in range(len(vertices)) if index not in fixed)
    field: list[Vec3] = [(0.0, 0.0, 0.0) for _ in vertices]
    for index, displacement in anchors.items():
        field[index] = displacement
    for index in protected:
        field[index] = (0.0, 0.0, 0.0)

    converged = not free_vertices
    final_update = 0.0
    final_residual = 0.0
    iteration_count = 0
    for iteration in range(1, limits.max_iterations + 1):
        if not free_vertices:
            break
        next_field = list(field)
        final_update = 0.0
        for index in free_vertices:
            neighbors = region_adjacency[index]
            if not neighbors:
                raise WholeSurfaceFitError(f"same_region_vertex_without_edge:{index}")
            denominator = len(neighbors) + limits.screen_weight
            exact = tuple(
                sum(field[neighbor][axis] for neighbor in neighbors) / denominator
                for axis in range(3)
            )
            relaxed = tuple(
                field[index][axis]
                + limits.jacobi_relaxation * (exact[axis] - field[index][axis])
                for axis in range(3)
            )
            checked = _vec3(relaxed, f"jacobi_result:{index}")
            next_field[index] = checked
            final_update = max(
                final_update,
                *(abs(checked[axis] - field[index][axis]) for axis in range(3)),
            )
        for index, displacement in anchors.items():
            next_field[index] = displacement
        for index in protected:
            next_field[index] = (0.0, 0.0, 0.0)
        field = next_field
        iteration_count = iteration
        final_residual = _equation_residual(
            field, region_adjacency, free_vertices, limits.screen_weight
        )
        if final_residual <= limits.convergence_tolerance:
            converged = True
            break
    if not converged:
        raise WholeSurfaceFitError(
            f"screened_harmonic_not_converged:{iteration_count}:"
            f"{final_residual:.17g}"
        )

    raw_field = tuple(field)
    raw_hash = vector_field_sha256(raw_field)
    accepted, candidate, scale_denominator, rejections = _line_search_anchor_preserving(
        baseline_vertices=vertices,
        faces=copied_faces,
        raw_displacements=raw_field,
        anchor_indices=tuple(sorted(anchors)),
        protected_indices=tuple(sorted(protected)),
        limits=limits,
    )
    for index in protected:
        if accepted[index] != (0.0, 0.0, 0.0):
            raise WholeSurfaceFitError("accepted_protected_displacement_not_exact_zero")
        if candidate[index] != vertices[index]:
            raise WholeSurfaceFitError("protected_candidate_not_exact_aligned_baseline")
    for index, displacement in anchors.items():
        if accepted[index] != displacement:
            raise WholeSurfaceFitError("accepted_anchor_displacement_not_exact")

    topology_after = topology_sha256(len(vertices), copied_faces)
    if topology_after != topology_digest:
        raise WholeSurfaceFitError("topology_index_preservation_failed")
    accepted_residual = _equation_residual(
        accepted, region_adjacency, free_vertices, limits.screen_weight
    )
    if accepted_residual > limits.convergence_tolerance:
        raise WholeSurfaceFitError(
            "accepted_field_screened_harmonic_residual_exceeded:"
            f"{accepted_residual:.17g}:"
            f"{limits.convergence_tolerance:.17g}"
        )
    adjacency_slots = sum(len(row) for row in region_adjacency)
    # Deterministic conservative accounting units, not a live process-memory claim.
    storage_upper_bound = (
        len(vertices) * 12
        + adjacency_slots * 2
        + len(copied_faces) * 4
        + len(anchors) * 8
    )
    evidence = FitEvidence(
        qualification_id=qualification_id,
        vertex_count=len(vertices),
        edge_count=edge_count,
        face_count=len(copied_faces),
        triangle_count=len(_triangles(copied_faces)),
        connected_components=connected_components,
        semantic_region_count=semantic_region_count,
        protected_vertex_count=len(protected),
        anchor_count=len(anchors),
        free_vertex_count=len(free_vertices),
        sparse_adjacency_slot_count=adjacency_slots,
        sparse_storage_units_upper_bound=storage_upper_bound,
        iteration_count=iteration_count,
        converged="YES",
        final_update_inf_fixed_1e12=_fixed_1e12(final_update, "final_update"),
        raw_equation_residual_inf_fixed_1e12=_fixed_1e12(
            final_residual, "raw_residual"
        ),
        accepted_equation_residual_inf_fixed_1e12=_fixed_1e12(
            accepted_residual, "accepted_residual"
        ),
        accepted_field_converged="YES",
        line_search_attempt_count=1 + len(rejections),
        line_search_scale_numerator=1,
        line_search_scale_denominator=scale_denominator,
        line_search_rejections=rejections,
        baseline_space=baseline_space,
        anchor_space=anchor_space,
        topology_sha256=topology_digest,
        topology_after_sha256=topology_after,
        baseline_sha256=baseline_digest,
        region_sha256=region_digest,
        protected_sha256=protected_digest,
        anchor_sha256=anchor_digest,
        limits_sha256=limits_digest,
        raw_displacement_sha256=raw_hash,
        accepted_displacement_sha256=vector_field_sha256(accepted),
        candidate_vertex_sha256=candidate_vertices_sha256(candidate),
    )
    bindings = _ResultBindings(
        baseline_vertices=vertices,
        faces=copied_faces,
        regions=regions,
        protected_vertices=tuple(sorted(protected)),
        anchor_displacements=tuple(sorted(anchors.items())),
        limits=limits,
        raw_displacement_field=raw_field,
    )
    result = _construct_fit_result(accepted, candidate, evidence, bindings)
    result.canonical_sha256()
    return result


__all__ = (
    "FitEvidence",
    "FitLimits",
    "FitResult",
    "MAX_JACOBI_ITERATIONS",
    "MAX_LINE_SEARCH_BACKTRACKS",
    "SEMANTIC_REGIONS",
    "TOPOLOGY_CODEC",
    "VECTOR_FIELD_CODEC",
    "WholeSurfaceFitError",
    "anchor_displacements_sha256",
    "baseline_sha256",
    "candidate_vertices_sha256",
    "canonical_json_bytes",
    "encode_vector_field",
    "fit_limits_sha256",
    "index_set_sha256",
    "regions_sha256",
    "solve_r25_whole_surface_fit",
    "topology_sha256",
    "vector_field_sha256",
)
