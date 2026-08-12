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
from dataclasses import dataclass
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
            "topology_index_preserved": "YES",
            "protected_displacements_exact_zero": "YES",
            "anchor_displacements_exact": "YES",
            "same_region_propagation_only": "YES",
            "dense_matrix_constructed": "NO",
            "geometry_field_only": "YES",
        }


@dataclass(frozen=True)
class FitResult:
    displacement_field: tuple[Vec3, ...]
    candidate_vertices: tuple[Vec3, ...]
    evidence: FitEvidence

    def canonical_payload(self) -> dict[str, object]:
        encoded, digest = encode_vector_field(self.displacement_field)
        if digest != self.evidence.accepted_displacement_sha256:
            raise WholeSurfaceFitError("result_displacement_hash_drifted")
        return {
            "schema": "kira.r25.whole_surface_geometry_field.v2",
            "status": "STATIC_GEOMETRY_FIELD_VALIDATED_NOT_A_BODY",
            "displacement_field": {
                "codec": VECTOR_FIELD_CODEC,
                "vertex_count": len(self.displacement_field),
                "base64": encoded,
                "sha256": digest,
            },
            "evidence": self.evidence.payload(),
        }

    def canonical_sha256(self) -> str:
        return hashlib.sha256(canonical_json_bytes(self.canonical_payload())).hexdigest()


def _integer(value: object, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise WholeSurfaceFitError(f"{label}_invalid")
    return value


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WholeSurfaceFitError(f"{label}_not_numeric")
    result = float(value)
    if not math.isfinite(result):
        raise WholeSurfaceFitError(f"{label}_nonfinite")
    return 0.0 if result == 0.0 else result


def _vec3(value: object, label: str) -> Vec3:
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise WholeSurfaceFitError(f"{label}_not_vec3")
    return (
        _finite(value[0], f"{label}_x"),
        _finite(value[1], f"{label}_y"),
        _finite(value[2], f"{label}_z"),
    )


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
    _integer(
        limits.maximum_line_search_backtracks,
        "maximum_line_search_backtracks",
        0,
    )


def _normalized_limits(limits: FitLimits) -> FitLimits:
    """Return one exact immutable snapshot; subclasses are not consumed."""

    _validate_limits(limits)
    return FitLimits(
        screen_weight=_finite(limits.screen_weight, "screen_weight"),
        jacobi_relaxation=_finite(limits.jacobi_relaxation, "jacobi_relaxation"),
        convergence_tolerance=_finite(
            limits.convergence_tolerance, "convergence_tolerance"
        ),
        max_iterations=_integer(limits.max_iterations, "max_iterations", 1),
        maximum_displacement=_finite(
            limits.maximum_displacement, "maximum_displacement"
        ),
        minimum_triangle_area=_finite(
            limits.minimum_triangle_area, "minimum_triangle_area"
        ),
        minimum_area_ratio=_finite(limits.minimum_area_ratio, "minimum_area_ratio"),
        maximum_area_ratio=_finite(limits.maximum_area_ratio, "maximum_area_ratio"),
        minimum_orientation_cosine=_finite(
            limits.minimum_orientation_cosine, "minimum_orientation_cosine"
        ),
        maximum_line_search_backtracks=_integer(
            limits.maximum_line_search_backtracks,
            "maximum_line_search_backtracks",
            0,
        ),
    )


def canonical_json_bytes(value: object) -> bytes:
    _validate_canonical_json(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _validate_canonical_json(value: object, where: str = "$") -> None:
    if isinstance(value, bool) or value is None or isinstance(value, float):
        raise WholeSurfaceFitError(f"canonical_non_integer_string_at:{where}")
    if isinstance(value, (str, int)):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_canonical_json(item, f"{where}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise WholeSurfaceFitError(f"canonical_non_string_key_at:{where}")
            _validate_canonical_json(item, f"{where}.{key}")
        return
    raise WholeSurfaceFitError(f"canonical_unsupported_type_at:{where}")


def _pack_vec3(stream: bytearray, value: Sequence[float]) -> None:
    vector = _vec3(value, "vector")
    stream.extend(struct.pack("<ddd", *vector))


def encode_vector_field(vectors: Sequence[Sequence[float]]) -> tuple[str, str]:
    raw = bytearray(VECTOR_FIELD_HEADER)
    raw.extend(struct.pack("<I", len(vectors)))
    for vector in vectors:
        _pack_vec3(raw, vector)
    payload = bytes(raw)
    return base64.b64encode(payload).decode("ascii"), hashlib.sha256(payload).hexdigest()


def vector_field_sha256(vectors: Sequence[Sequence[float]]) -> str:
    return encode_vector_field(vectors)[1]


def baseline_sha256(vertices: Sequence[Sequence[float]]) -> str:
    raw = bytearray(BASELINE_HEADER)
    raw.extend(struct.pack("<I", len(vertices)))
    for vertex in vertices:
        _pack_vec3(raw, vertex)
    return hashlib.sha256(bytes(raw)).hexdigest()


def candidate_vertices_sha256(vertices: Sequence[Sequence[float]]) -> str:
    raw = bytearray(CANDIDATE_HEADER)
    raw.extend(struct.pack("<I", len(vertices)))
    for vertex in vertices:
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
    raw = bytearray(TOPOLOGY_CODEC.encode("ascii") + b"\0")
    raw.extend(struct.pack("<II", count, len(faces)))
    for face_position, face in enumerate(faces):
        if not isinstance(face, (tuple, list)) or len(face) < 3:
            raise WholeSurfaceFitError(f"face_invalid:{face_position}")
        raw.extend(struct.pack("<I", len(face)))
        seen: set[int] = set()
        for value in face:
            index = _integer(value, f"face_index:{face_position}")
            if index >= count or index in seen:
                raise WholeSurfaceFitError(f"face_index_duplicate_or_out_of_range:{face_position}")
            seen.add(index)
            raw.extend(struct.pack("<I", index))
    return hashlib.sha256(bytes(raw)).hexdigest()


def regions_sha256(regions: Sequence[str]) -> str:
    raw = bytearray(REGION_HEADER)
    raw.extend(struct.pack("<I", len(regions)))
    for position, region in enumerate(regions):
        if not isinstance(region, str) or region not in SEMANTIC_REGIONS:
            raise WholeSurfaceFitError(f"unknown_semantic_region:{position}")
        encoded = region.encode("utf-8")
        raw.extend(struct.pack("<I", len(encoded)))
        raw.extend(encoded)
    return hashlib.sha256(bytes(raw)).hexdigest()


def index_set_sha256(indices: Iterable[int], vertex_count: int) -> str:
    values = list(indices)
    checked = []
    seen: set[int] = set()
    for value in values:
        index = _integer(value, "protected_index")
        if index >= vertex_count or index in seen:
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
    if not isinstance(anchors, Mapping):
        raise WholeSurfaceFitError("anchor_mapping_invalid")
    raw = bytearray(ANCHOR_HEADER)
    raw.extend(struct.pack("<I", len(anchors)))
    seen: set[int] = set()
    rows: list[tuple[int, Vec3]] = []
    for key, value in anchors.items():
        index = _integer(key, "anchor_index")
        if index >= vertex_count or index in seen:
            raise WholeSurfaceFitError("anchor_index_duplicate_or_out_of_range")
        seen.add(index)
        rows.append((index, _vec3(value, f"anchor_displacement:{index}")))
    for index, vector in sorted(rows):
        raw.extend(struct.pack("<I", index))
        _pack_vec3(raw, vector)
    return hashlib.sha256(bytes(raw)).hexdigest()


def _snapshot_anchor_displacements(
    anchors: Mapping[int, Sequence[float]], vertex_count: int
) -> dict[int, Vec3]:
    if not isinstance(anchors, Mapping):
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
    if not isinstance(baseline_vertices, (tuple, list)) or not baseline_vertices:
        raise WholeSurfaceFitError("baseline_vertices_invalid")
    vertices = tuple(
        _vec3(value, f"baseline_vertex:{index}")
        for index, value in enumerate(baseline_vertices)
    )
    if not isinstance(faces, (tuple, list)) or not faces:
        raise WholeSurfaceFitError("faces_invalid")
    copied_faces: list[tuple[int, ...]] = []
    duplicate_keys: set[tuple[int, ...]] = set()
    for position, face in enumerate(faces):
        if not isinstance(face, (tuple, list)) or len(face) < 3:
            raise WholeSurfaceFitError(f"face_invalid:{position}")
        checked = tuple(_integer(value, f"face_index:{position}") for value in face)
        if len(set(checked)) != len(checked) or any(value >= len(vertices) for value in checked):
            raise WholeSurfaceFitError(f"face_index_duplicate_or_out_of_range:{position}")
        duplicate_key = tuple(sorted(checked))
        if duplicate_key in duplicate_keys:
            raise WholeSurfaceFitError(f"duplicate_face:{position}")
        duplicate_keys.add(duplicate_key)
        copied_faces.append(checked)
    if not isinstance(vertex_regions, (tuple, list)) or len(vertex_regions) != len(vertices):
        raise WholeSurfaceFitError("vertex_region_count_mismatch")
    copied_regions = tuple(vertex_regions)
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


def line_search_anchor_preserving(
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
    baseline = tuple(_vec3(value, f"line_baseline:{i}") for i, value in enumerate(baseline_vertices))
    raw = tuple(_vec3(value, f"line_displacement:{i}") for i, value in enumerate(raw_displacements))
    if len(raw) != len(baseline):
        raise WholeSurfaceFitError("line_search_field_count_mismatch")
    copied_faces = tuple(tuple(_integer(v, "line_face_index") for v in face) for face in faces)
    topology_sha256(len(baseline), copied_faces)
    anchor_values = list(anchor_indices)
    protected_values = list(protected_indices)
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
    if anchors & protected:
        raise WholeSurfaceFitError("line_search_anchor_protected_overlap")
    if any(index < 0 or index >= len(baseline) for index in anchors | protected):
        raise WholeSurfaceFitError("line_search_constraint_out_of_range")
    for index in protected:
        if raw[index] != (0.0, 0.0, 0.0):
            raise WholeSurfaceFitError("line_search_protected_not_exact_zero")
    triangle_rows = _triangles(copied_faces)
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

    protected_values = list(protected_vertices)
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
    accepted, candidate, scale_denominator, rejections = line_search_anchor_preserving(
        baseline_vertices=vertices,
        faces=copied_faces,
        raw_displacements=raw_field,
        anchor_indices=anchors,
        protected_indices=protected,
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
    result = FitResult(accepted, candidate, evidence)
    result.canonical_sha256()
    return result


__all__ = (
    "FitEvidence",
    "FitLimits",
    "FitResult",
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
    "line_search_anchor_preserving",
    "regions_sha256",
    "solve_r25_whole_surface_fit",
    "topology_sha256",
    "vector_field_sha256",
)
