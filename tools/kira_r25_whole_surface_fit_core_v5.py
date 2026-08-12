"""Stateless deterministic R25 whole-surface mathematics.

This module deliberately provides no same-process issuance or acceptance
boundary.  Python callers can reflect on and mutate Python state, so every
in-process result is explicitly non-authoritative.  A future exact-byte
isolated worker/controller must establish any execution or evidence authority.

The useful mathematics retained here is a sparse screened-harmonic field over
same-semantic-region mesh edges, followed by an anchor-preserving geometric
line search.  The module is Blender-free and constructs no dense matrix.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import struct
from typing import Iterable, Mapping, Sequence


Vec3 = tuple[float, float, float]

STATIC_MATH_STATUS = (
    "STATIC_MATH_CORE_ONLY_REQUIRES_EXACT_BYTE_ISOLATED_WORKER_CONTROLLER"
)
NONAUTHORITATIVE_CHECK = "NONAUTHORITATIVE_IN_PROCESS_MATH_CHECK"

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
CANDIDATE_VERTEX_CODEC = "kira_r25_candidate_vertices_f64le_v1"
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

DEFAULT_SCREEN_WEIGHT = 0.25
DEFAULT_JACOBI_RELAXATION = 0.85
DEFAULT_CONVERGENCE_TOLERANCE = 1.0e-10
DEFAULT_MAX_ITERATIONS = 2_000
DEFAULT_MAXIMUM_DISPLACEMENT = 0.25
DEFAULT_MINIMUM_TRIANGLE_AREA = 1.0e-12
DEFAULT_MINIMUM_AREA_RATIO = 0.20
DEFAULT_MAXIMUM_AREA_RATIO = 5.0
DEFAULT_MINIMUM_ORIENTATION_COSINE = 0.0
DEFAULT_MAXIMUM_LINE_SEARCH_BACKTRACKS = 12


class WholeSurfaceMathError(ValueError):
    """A fail-closed mathematical precondition or invariant was not met."""


def _integer(value: object, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise WholeSurfaceMathError(f"{label}_invalid")
    return value


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise WholeSurfaceMathError(f"{label}_not_numeric")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise WholeSurfaceMathError(f"{label}_not_f64") from exc
    if not math.isfinite(result):
        raise WholeSurfaceMathError(f"{label}_nonfinite")
    return 0.0 if result == 0.0 else result


def _vec3(value: object, label: str) -> Vec3:
    if type(value) not in (tuple, list) or len(value) != 3:
        raise WholeSurfaceMathError(f"{label}_not_vec3")
    return (
        _finite(value[0], f"{label}_x"),
        _finite(value[1], f"{label}_y"),
        _finite(value[2], f"{label}_z"),
    )


def _exact_string(value: object, label: str) -> str:
    if type(value) is not str:
        raise WholeSurfaceMathError(f"{label}_not_exact_string")
    return value


def _exact_sha256(value: object, label: str) -> str:
    digest = _exact_string(value, label)
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise WholeSurfaceMathError(f"{label}_not_lowercase_sha256")
    return digest


def _plain_sequence(
    value: object, label: str, *, allow_empty: bool = True
) -> tuple[object, ...]:
    if type(value) not in (tuple, list):
        raise WholeSurfaceMathError(f"{label}_not_plain_sequence")
    snapshot = tuple(value)
    if not allow_empty and not snapshot:
        raise WholeSurfaceMathError(f"{label}_empty")
    return snapshot


def _plain_index_collection(value: object, label: str) -> tuple[object, ...]:
    if type(value) not in (tuple, list, set, frozenset):
        raise WholeSurfaceMathError(f"{label}_not_plain_index_collection")
    return tuple(value)


def _normalize_limits(
    *,
    screen_weight: object,
    jacobi_relaxation: object,
    convergence_tolerance: object,
    max_iterations: object,
    maximum_displacement: object,
    minimum_triangle_area: object,
    minimum_area_ratio: object,
    maximum_area_ratio: object,
    minimum_orientation_cosine: object,
    maximum_line_search_backtracks: object,
) -> tuple[float, float, float, int, float, float, float, float, float, int]:
    screen = _finite(screen_weight, "screen_weight")
    relaxation = _finite(jacobi_relaxation, "jacobi_relaxation")
    tolerance = _finite(convergence_tolerance, "convergence_tolerance")
    iterations = _integer(max_iterations, "max_iterations", 1)
    displacement = _finite(maximum_displacement, "maximum_displacement")
    triangle_area = _finite(minimum_triangle_area, "minimum_triangle_area")
    minimum_ratio = _finite(minimum_area_ratio, "minimum_area_ratio")
    maximum_ratio = _finite(maximum_area_ratio, "maximum_area_ratio")
    orientation = _finite(
        minimum_orientation_cosine, "minimum_orientation_cosine"
    )
    backtracks = _integer(
        maximum_line_search_backtracks,
        "maximum_line_search_backtracks",
        0,
    )
    for value, label in (
        (screen, "screen_weight"),
        (relaxation, "jacobi_relaxation"),
        (tolerance, "convergence_tolerance"),
        (displacement, "maximum_displacement"),
        (triangle_area, "minimum_triangle_area"),
        (minimum_ratio, "minimum_area_ratio"),
        (maximum_ratio, "maximum_area_ratio"),
    ):
        if value <= 0.0:
            raise WholeSurfaceMathError(f"{label}_must_be_positive")
    if relaxation > 1.0:
        raise WholeSurfaceMathError("jacobi_relaxation_above_one")
    if orientation < 0.0 or orientation >= 1.0:
        raise WholeSurfaceMathError("minimum_orientation_cosine_out_of_range")
    if minimum_ratio >= maximum_ratio:
        raise WholeSurfaceMathError("area_ratio_order_invalid")
    if iterations > MAX_JACOBI_ITERATIONS:
        raise WholeSurfaceMathError("max_iterations_above_absolute_ceiling")
    if backtracks > MAX_LINE_SEARCH_BACKTRACKS:
        raise WholeSurfaceMathError(
            "maximum_line_search_backtracks_above_absolute_ceiling"
        )
    return (
        screen,
        relaxation,
        tolerance,
        iterations,
        displacement,
        triangle_area,
        minimum_ratio,
        maximum_ratio,
        orientation,
        backtracks,
    )


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
        raise WholeSurfaceMathError(f"canonical_non_integer_string_at:{where}")
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
                raise WholeSurfaceMathError(
                    f"canonical_non_string_key_at:{where}"
                )
            snapshot[key] = _snapshot_canonical_json(item, f"{where}.{key}")
        return snapshot
    raise WholeSurfaceMathError(f"canonical_unsupported_type_at:{where}")


def _pack_vec3(stream: bytearray, value: Sequence[float]) -> None:
    vector = _vec3(value, "vector")
    stream.extend(struct.pack("<ddd", *vector))


def _encode_vec3_rows(
    vectors: Sequence[Sequence[float]], header: bytes
) -> tuple[str, str, int]:
    rows = _plain_sequence(vectors, "vector_rows")
    raw = bytearray(header)
    raw.extend(struct.pack("<I", len(rows)))
    for vector in rows:
        _pack_vec3(raw, vector)
    payload = bytes(raw)
    return (
        base64.b64encode(payload).decode("ascii"),
        hashlib.sha256(payload).hexdigest(),
        len(rows),
    )


def encode_vector_field(
    vectors: Sequence[Sequence[float]],
) -> tuple[str, str]:
    encoded, digest, _count = _encode_vec3_rows(vectors, VECTOR_FIELD_HEADER)
    return encoded, digest


def vector_field_sha256(vectors: Sequence[Sequence[float]]) -> str:
    return encode_vector_field(vectors)[1]


def encode_candidate_vertices(
    vertices: Sequence[Sequence[float]],
) -> tuple[str, str]:
    encoded, digest, _count = _encode_vec3_rows(vertices, CANDIDATE_HEADER)
    return encoded, digest


def candidate_vertices_sha256(vertices: Sequence[Sequence[float]]) -> str:
    return encode_candidate_vertices(vertices)[1]


def baseline_sha256(vertices: Sequence[Sequence[float]]) -> str:
    rows = _plain_sequence(vertices, "baseline_vertices")
    raw = bytearray(BASELINE_HEADER)
    raw.extend(struct.pack("<I", len(rows)))
    for vertex in rows:
        _pack_vec3(raw, vertex)
    return hashlib.sha256(bytes(raw)).hexdigest()


def fit_limits_sha256(
    *,
    screen_weight: object = DEFAULT_SCREEN_WEIGHT,
    jacobi_relaxation: object = DEFAULT_JACOBI_RELAXATION,
    convergence_tolerance: object = DEFAULT_CONVERGENCE_TOLERANCE,
    max_iterations: object = DEFAULT_MAX_ITERATIONS,
    maximum_displacement: object = DEFAULT_MAXIMUM_DISPLACEMENT,
    minimum_triangle_area: object = DEFAULT_MINIMUM_TRIANGLE_AREA,
    minimum_area_ratio: object = DEFAULT_MINIMUM_AREA_RATIO,
    maximum_area_ratio: object = DEFAULT_MAXIMUM_AREA_RATIO,
    minimum_orientation_cosine: object = DEFAULT_MINIMUM_ORIENTATION_COSINE,
    maximum_line_search_backtracks: object = (
        DEFAULT_MAXIMUM_LINE_SEARCH_BACKTRACKS
    ),
) -> str:
    limits = _normalize_limits(
        screen_weight=screen_weight,
        jacobi_relaxation=jacobi_relaxation,
        convergence_tolerance=convergence_tolerance,
        max_iterations=max_iterations,
        maximum_displacement=maximum_displacement,
        minimum_triangle_area=minimum_triangle_area,
        minimum_area_ratio=minimum_area_ratio,
        maximum_area_ratio=maximum_area_ratio,
        minimum_orientation_cosine=minimum_orientation_cosine,
        maximum_line_search_backtracks=maximum_line_search_backtracks,
    )
    raw = bytearray(LIMITS_HEADER)
    raw.extend(
        struct.pack(
            "<ddddddddII",
            limits[0],
            limits[1],
            limits[2],
            limits[4],
            limits[5],
            limits[6],
            limits[7],
            limits[8],
            limits[3],
            limits[9],
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
            raise WholeSurfaceMathError(f"face_invalid:{face_position}")
        face_snapshot = tuple(face)
        raw.extend(struct.pack("<I", len(face_snapshot)))
        seen: set[int] = set()
        checked: list[int] = []
        for value in face_snapshot:
            index = _integer(value, f"face_index:{face_position}")
            if index >= count or index in seen:
                raise WholeSurfaceMathError(
                    f"face_index_duplicate_or_out_of_range:{face_position}"
                )
            seen.add(index)
            checked.append(index)
            raw.extend(struct.pack("<I", index))
        duplicate_key = tuple(sorted(checked))
        if duplicate_key in duplicate_keys:
            raise WholeSurfaceMathError(f"duplicate_face:{face_position}")
        duplicate_keys.add(duplicate_key)
    return hashlib.sha256(bytes(raw)).hexdigest()


def regions_sha256(regions: Sequence[str]) -> str:
    rows = _plain_sequence(regions, "semantic_regions")
    raw = bytearray(REGION_HEADER)
    raw.extend(struct.pack("<I", len(rows)))
    for position, region in enumerate(rows):
        if type(region) is not str or region not in SEMANTIC_REGIONS:
            raise WholeSurfaceMathError(f"unknown_semantic_region:{position}")
        encoded = region.encode("utf-8")
        raw.extend(struct.pack("<I", len(encoded)))
        raw.extend(encoded)
    return hashlib.sha256(bytes(raw)).hexdigest()


def index_set_sha256(indices: Iterable[int], vertex_count: int) -> str:
    count = _integer(vertex_count, "index_set_vertex_count", 1)
    values = _plain_index_collection(indices, "protected_indices")
    checked: list[int] = []
    seen: set[int] = set()
    for value in values:
        index = _integer(value, "protected_index")
        if index >= count or index in seen:
            raise WholeSurfaceMathError(
                "protected_index_duplicate_or_out_of_range"
            )
        seen.add(index)
        checked.append(index)
    raw = bytearray(INDEX_HEADER)
    raw.extend(struct.pack("<I", len(checked)))
    for index in sorted(checked):
        raw.extend(struct.pack("<I", index))
    return hashlib.sha256(bytes(raw)).hexdigest()


def _snapshot_anchor_displacements(
    anchors: Mapping[int, Sequence[float]], vertex_count: int
) -> dict[int, Vec3]:
    if type(anchors) is not dict:
        raise WholeSurfaceMathError("anchor_mapping_invalid")
    snapshot: dict[int, Vec3] = {}
    for key, value in anchors.items():
        index = _integer(key, "anchor_index")
        if index >= vertex_count or index in snapshot:
            raise WholeSurfaceMathError(
                "anchor_index_duplicate_or_out_of_range"
            )
        snapshot[index] = _vec3(value, f"anchor_displacement:{index}")
    return snapshot


def anchor_displacements_sha256(
    anchors: Mapping[int, Sequence[float]], vertex_count: int
) -> str:
    count = _integer(vertex_count, "anchor_vertex_count", 1)
    snapshot = _snapshot_anchor_displacements(anchors, count)
    raw = bytearray(ANCHOR_HEADER)
    raw.extend(struct.pack("<I", len(snapshot)))
    for index, vector in sorted(snapshot.items()):
        raw.extend(struct.pack("<I", index))
        _pack_vec3(raw, vector)
    return hashlib.sha256(bytes(raw)).hexdigest()


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
            raise WholeSurfaceMathError(f"face_invalid:{position}")
        checked = tuple(
            _integer(value, f"face_index:{position}") for value in face
        )
        if len(set(checked)) != len(checked) or any(
            value >= len(vertices) for value in checked
        ):
            raise WholeSurfaceMathError(
                f"face_index_duplicate_or_out_of_range:{position}"
            )
        duplicate_key = tuple(sorted(checked))
        if duplicate_key in duplicate_keys:
            raise WholeSurfaceMathError(f"duplicate_face:{position}")
        duplicate_keys.add(duplicate_key)
        copied_faces.append(checked)
    region_rows = _plain_sequence(vertex_regions, "vertex_regions")
    if len(region_rows) != len(vertices):
        raise WholeSurfaceMathError("vertex_region_count_mismatch")
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


def _component_count(
    adjacency: Sequence[Sequence[int]], vertices: Iterable[int]
) -> int:
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
    anchor_indices = set(anchors)
    for region in present:
        members = {
            index for index, value in enumerate(regions) if value == region
        }
        components = _component_count(adjacency, members)
        if components != 1:
            raise WholeSurfaceMathError(
                f"same_region_graph_disconnected:{region}:{components}"
            )
        remaining = set(members - protected)
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
            free = component - anchor_indices
            if free and not (component & anchor_indices):
                raise WholeSurfaceMathError(
                    "same_region_free_component_without_anchor:"
                    f"{region}:{min(free)}"
                )
    return len(present)


def _triangles(
    faces: Sequence[Sequence[int]],
) -> tuple[tuple[int, int, int], ...]:
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
    return (
        first[0] * second[0]
        + first[1] * second[1]
        + first[2] * second[2]
    )


def _norm(value: Sequence[float]) -> float:
    return math.sqrt(max(0.0, _dot(value, value)))


def _candidate_geometry_issues(
    baseline: Sequence[Vec3],
    candidate: Sequence[Vec3],
    displacements: Sequence[Vec3],
    triangles: Sequence[tuple[int, int, int]],
    limits: tuple[float, float, float, int, float, float, float, float, float, int],
) -> tuple[str, ...]:
    maximum_displacement = limits[4]
    minimum_triangle_area = limits[5]
    minimum_area_ratio = limits[6]
    maximum_area_ratio = limits[7]
    minimum_orientation_cosine = limits[8]
    for index, (point, displacement) in enumerate(
        zip(candidate, displacements, strict=True)
    ):
        if not all(math.isfinite(value) for value in point):
            return (f"candidate_vertex_nonfinite:{index}",)
        if _norm(displacement) > maximum_displacement + 1.0e-15:
            return (f"maximum_displacement_exceeded:{index}",)
    for triangle_index, (a, b, c) in enumerate(triangles):
        base_normal = _cross(
            _sub(baseline[b], baseline[a]),
            _sub(baseline[c], baseline[a]),
        )
        candidate_normal = _cross(
            _sub(candidate[b], candidate[a]),
            _sub(candidate[c], candidate[a]),
        )
        base_twice_area = _norm(base_normal)
        candidate_twice_area = _norm(candidate_normal)
        if (
            not math.isfinite(base_twice_area)
            or base_twice_area * 0.5 <= minimum_triangle_area
        ):
            raise WholeSurfaceMathError(
                f"baseline_triangle_degenerate:{triangle_index}"
            )
        if not math.isfinite(candidate_twice_area):
            return (f"candidate_triangle_nonfinite:{triangle_index}",)
        if candidate_twice_area * 0.5 <= minimum_triangle_area:
            return (f"candidate_triangle_degenerate:{triangle_index}",)
        orientation = _dot(base_normal, candidate_normal) / (
            base_twice_area * candidate_twice_area
        )
        if not math.isfinite(orientation):
            return (f"candidate_orientation_nonfinite:{triangle_index}",)
        if orientation <= minimum_orientation_cosine:
            return (f"candidate_triangle_orientation_flip:{triangle_index}",)
        ratio = candidate_twice_area / base_twice_area
        if ratio < minimum_area_ratio or ratio > maximum_area_ratio:
            return (f"candidate_triangle_area_ratio:{triangle_index}",)
    return ()


def _line_search_anchor_preserving(
    *,
    baseline_vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
    raw_displacements: Sequence[Sequence[float]],
    anchor_indices: Iterable[int],
    protected_indices: Iterable[int],
    limits: tuple[float, float, float, int, float, float, float, float, float, int],
) -> tuple[tuple[Vec3, ...], tuple[Vec3, ...], int, tuple[str, ...]]:
    if type(limits) is not tuple or len(limits) != 10:
        raise WholeSurfaceMathError("line_search_limits_invalid")
    limits = _normalize_limits(
        screen_weight=limits[0],
        jacobi_relaxation=limits[1],
        convergence_tolerance=limits[2],
        max_iterations=limits[3],
        maximum_displacement=limits[4],
        minimum_triangle_area=limits[5],
        minimum_area_ratio=limits[6],
        maximum_area_ratio=limits[7],
        minimum_orientation_cosine=limits[8],
        maximum_line_search_backtracks=limits[9],
    )
    baseline_rows = _plain_sequence(
        baseline_vertices, "line_baseline_vertices", allow_empty=False
    )
    raw_rows = _plain_sequence(
        raw_displacements, "line_raw_displacements", allow_empty=False
    )
    face_rows = _plain_sequence(faces, "line_faces", allow_empty=False)
    baseline = tuple(
        _vec3(value, f"line_baseline:{index}")
        for index, value in enumerate(baseline_rows)
    )
    raw = tuple(
        _vec3(value, f"line_displacement:{index}")
        for index, value in enumerate(raw_rows)
    )
    if len(raw) != len(baseline):
        raise WholeSurfaceMathError("line_search_field_count_mismatch")
    copied_faces: list[tuple[int, ...]] = []
    duplicate_faces: set[tuple[int, ...]] = set()
    for position, face in enumerate(face_rows):
        if type(face) not in (tuple, list) or len(face) < 3:
            raise WholeSurfaceMathError(f"line_face_invalid:{position}")
        checked = tuple(
            _integer(value, f"line_face_index:{position}") for value in face
        )
        if len(set(checked)) != len(checked) or any(
            value >= len(baseline) for value in checked
        ):
            raise WholeSurfaceMathError(
                f"line_face_index_duplicate_or_out_of_range:{position}"
            )
        duplicate_key = tuple(sorted(checked))
        if duplicate_key in duplicate_faces:
            raise WholeSurfaceMathError(f"line_duplicate_face:{position}")
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
            raise WholeSurfaceMathError("line_search_anchor_index_duplicate")
        anchors.add(index)
    for value in protected_values:
        index = _integer(value, "line_search_protected_index")
        if index in protected:
            raise WholeSurfaceMathError(
                "line_search_protected_index_duplicate"
            )
        protected.add(index)
    if not anchors:
        raise WholeSurfaceMathError("line_search_anchor_set_empty")
    if not protected:
        raise WholeSurfaceMathError("line_search_protected_set_empty")
    if anchors & protected:
        raise WholeSurfaceMathError("line_search_anchor_protected_overlap")
    if any(index >= len(baseline) for index in anchors | protected):
        raise WholeSurfaceMathError("line_search_constraint_out_of_range")
    for index in protected:
        if raw[index] != (0.0, 0.0, 0.0):
            raise WholeSurfaceMathError(
                "line_search_protected_not_exact_zero"
            )
    triangle_rows = _triangles(copied_faces_tuple)
    rejections: list[str] = []
    denominator = 1
    for _attempt in range(limits[9] + 1):
        field: list[Vec3] = []
        candidate: list[Vec3] = []
        for index, displacement in enumerate(raw):
            if index in protected:
                selected = (0.0, 0.0, 0.0)
            elif index in anchors:
                selected = displacement
            else:
                selected = (
                    displacement[0] / denominator,
                    displacement[1] / denominator,
                    displacement[2] / denominator,
                )
            field.append(selected)
            candidate.append(
                (
                    baseline[index][0] + selected[0],
                    baseline[index][1] + selected[1],
                    baseline[index][2] + selected[2],
                )
            )
        issues = _candidate_geometry_issues(
            baseline, candidate, field, triangle_rows, limits
        )
        if not issues:
            return (
                tuple(field),
                tuple(candidate),
                denominator,
                tuple(rejections),
            )
        rejections.append(f"scale_1_over_{denominator}:{issues[0]}")
        denominator *= 2
    raise WholeSurfaceMathError(
        "line_search_no_safe_anchor_preserving_scale:"
        + "|".join(rejections)
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
            target = (
                sum(field[neighbor][axis] for neighbor in neighbors)
                / denominator
            )
            residual = max(residual, abs(field[index][axis] - target))
    return residual


def _fixed_1e12(value: float, label: str) -> int:
    if (
        not math.isfinite(value)
        or value < 0.0
        or value > 9_000_000.0
    ):
        raise WholeSurfaceMathError(f"{label}_cannot_encode")
    return int(round(value * 1_000_000_000_000))


def compute_r25_whole_surface_math(
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
    screen_weight: object = DEFAULT_SCREEN_WEIGHT,
    jacobi_relaxation: object = DEFAULT_JACOBI_RELAXATION,
    convergence_tolerance: object = DEFAULT_CONVERGENCE_TOLERANCE,
    max_iterations: object = DEFAULT_MAX_ITERATIONS,
    maximum_displacement: object = DEFAULT_MAXIMUM_DISPLACEMENT,
    minimum_triangle_area: object = DEFAULT_MINIMUM_TRIANGLE_AREA,
    minimum_area_ratio: object = DEFAULT_MINIMUM_AREA_RATIO,
    maximum_area_ratio: object = DEFAULT_MAXIMUM_AREA_RATIO,
    minimum_orientation_cosine: object = DEFAULT_MINIMUM_ORIENTATION_COSINE,
    maximum_line_search_backtracks: object = (
        DEFAULT_MAXIMUM_LINE_SEARCH_BACKTRACKS
    ),
) -> dict[str, object]:
    """Return deterministic primitive math data with no authority claim."""

    qualification = _exact_string(qualification_id, "qualification_id")
    baseline_coordinate_space = _exact_string(
        baseline_space, "baseline_space"
    )
    anchor_coordinate_space = _exact_string(anchor_space, "anchor_space")
    expected_topology = _exact_sha256(
        expected_topology_sha256, "expected_topology_sha256"
    )
    expected_baseline = _exact_sha256(
        expected_baseline_sha256, "expected_baseline_sha256"
    )
    expected_regions = _exact_sha256(
        expected_regions_sha256, "expected_regions_sha256"
    )
    expected_protected = _exact_sha256(
        expected_protected_sha256, "expected_protected_sha256"
    )
    expected_anchor = _exact_sha256(
        expected_anchor_sha256, "expected_anchor_sha256"
    )
    expected_limits = _exact_sha256(
        expected_limits_sha256, "expected_limits_sha256"
    )
    limits = _normalize_limits(
        screen_weight=screen_weight,
        jacobi_relaxation=jacobi_relaxation,
        convergence_tolerance=convergence_tolerance,
        max_iterations=max_iterations,
        maximum_displacement=maximum_displacement,
        minimum_triangle_area=minimum_triangle_area,
        minimum_area_ratio=minimum_area_ratio,
        maximum_area_ratio=maximum_area_ratio,
        minimum_orientation_cosine=minimum_orientation_cosine,
        maximum_line_search_backtracks=maximum_line_search_backtracks,
    )
    limits_digest = fit_limits_sha256(
        screen_weight=limits[0],
        jacobi_relaxation=limits[1],
        convergence_tolerance=limits[2],
        max_iterations=limits[3],
        maximum_displacement=limits[4],
        minimum_triangle_area=limits[5],
        minimum_area_ratio=limits[6],
        maximum_area_ratio=limits[7],
        minimum_orientation_cosine=limits[8],
        maximum_line_search_backtracks=limits[9],
    )
    if limits_digest != expected_limits:
        raise WholeSurfaceMathError("fit_limits_sha256_mismatch")
    if qualification != "kira_r25_qualified_continuous_foundation":
        raise WholeSurfaceMathError("qualification_id_not_exact")
    if baseline_coordinate_space != "globally_aligned_foundation":
        raise WholeSurfaceMathError("baseline_space_not_globally_aligned")
    if (
        anchor_coordinate_space
        != "globally_aligned_foundation_displacement"
    ):
        raise WholeSurfaceMathError("anchor_space_not_exact")

    vertices, copied_faces, regions = _copy_geometry(
        baseline_vertices, faces, vertex_regions
    )
    expected_vertices = _integer(
        expected_vertex_count, "expected_vertex_count", 1
    )
    expected_edges = _integer(
        expected_edge_count, "expected_edge_count", 1
    )
    expected_faces = _integer(
        expected_face_count, "expected_face_count", 1
    )
    expected_components = _integer(
        expected_connected_components,
        "expected_connected_components",
        1,
    )
    if len(vertices) != expected_vertices or len(copied_faces) != expected_faces:
        raise WholeSurfaceMathError("qualified_topology_count_mismatch")

    topology_digest = topology_sha256(len(vertices), copied_faces)
    baseline_digest = baseline_sha256(vertices)
    region_digest = regions_sha256(regions)
    if topology_digest != expected_topology:
        raise WholeSurfaceMathError("qualified_topology_sha256_mismatch")
    if baseline_digest != expected_baseline:
        raise WholeSurfaceMathError(
            "globally_aligned_baseline_sha256_mismatch"
        )
    if region_digest != expected_regions:
        raise WholeSurfaceMathError("semantic_region_sha256_mismatch")

    protected_values = _plain_index_collection(
        protected_vertices, "protected_vertices"
    )
    protected_digest = index_set_sha256(protected_values, len(vertices))
    if protected_digest != expected_protected:
        raise WholeSurfaceMathError(
            "afes_two_ring_protected_sha256_mismatch"
        )
    protected = set(protected_values)
    if not protected:
        raise WholeSurfaceMathError("afes_two_ring_protected_set_empty")

    anchors = _snapshot_anchor_displacements(
        anchor_displacements, len(vertices)
    )
    anchor_digest = anchor_displacements_sha256(anchors, len(vertices))
    if anchor_digest != expected_anchor:
        raise WholeSurfaceMathError("semantic_anchor_sha256_mismatch")
    if not anchors:
        raise WholeSurfaceMathError("semantic_anchor_set_empty")
    if protected & set(anchors):
        raise WholeSurfaceMathError(
            "semantic_anchor_inside_afes_two_ring_protected_set"
        )

    all_adjacency, region_adjacency, edge_count = _build_adjacency(
        len(vertices), copied_faces, regions
    )
    if edge_count != expected_edges:
        raise WholeSurfaceMathError("qualified_edge_count_mismatch")
    connected_components = _component_count(
        all_adjacency, range(len(vertices))
    )
    if connected_components != expected_components or connected_components != 1:
        raise WholeSurfaceMathError("qualified_topology_not_single_component")
    semantic_region_count = _validate_semantic_components(
        regions, region_adjacency, protected, anchors
    )

    fixed = protected | set(anchors)
    free_vertices = tuple(
        index for index in range(len(vertices)) if index not in fixed
    )
    field: list[Vec3] = [(0.0, 0.0, 0.0) for _ in vertices]
    for index, displacement in anchors.items():
        field[index] = displacement
    for index in protected:
        field[index] = (0.0, 0.0, 0.0)

    converged = not free_vertices
    final_update = 0.0
    final_residual = 0.0
    iteration_count = 0
    for iteration in range(1, limits[3] + 1):
        if not free_vertices:
            break
        next_field = list(field)
        final_update = 0.0
        for index in free_vertices:
            neighbors = region_adjacency[index]
            if not neighbors:
                raise WholeSurfaceMathError(
                    f"same_region_vertex_without_edge:{index}"
                )
            denominator = len(neighbors) + limits[0]
            exact = tuple(
                sum(field[neighbor][axis] for neighbor in neighbors)
                / denominator
                for axis in range(3)
            )
            relaxed = tuple(
                field[index][axis]
                + limits[1] * (exact[axis] - field[index][axis])
                for axis in range(3)
            )
            checked = _vec3(relaxed, f"jacobi_result:{index}")
            next_field[index] = checked
            final_update = max(
                final_update,
                *(
                    abs(checked[axis] - field[index][axis])
                    for axis in range(3)
                ),
            )
        for index, displacement in anchors.items():
            next_field[index] = displacement
        for index in protected:
            next_field[index] = (0.0, 0.0, 0.0)
        field = next_field
        iteration_count = iteration
        final_residual = _equation_residual(
            field, region_adjacency, free_vertices, limits[0]
        )
        if final_residual <= limits[2]:
            converged = True
            break
    if not converged:
        raise WholeSurfaceMathError(
            f"screened_harmonic_not_converged:{iteration_count}:"
            f"{final_residual:.17g}"
        )

    raw_field = tuple(field)
    raw_hash = vector_field_sha256(raw_field)
    selected_field, candidate, scale_denominator, rejections = (
        _line_search_anchor_preserving(
            baseline_vertices=vertices,
            faces=copied_faces,
            raw_displacements=raw_field,
            anchor_indices=tuple(sorted(anchors)),
            protected_indices=tuple(sorted(protected)),
            limits=limits,
        )
    )
    for index in protected:
        if selected_field[index] != (0.0, 0.0, 0.0):
            raise WholeSurfaceMathError(
                "post_line_search_protected_displacement_not_exact_zero"
            )
        if candidate[index] != vertices[index]:
            raise WholeSurfaceMathError(
                "protected_candidate_not_exact_aligned_baseline"
            )
    for index, displacement in anchors.items():
        if selected_field[index] != displacement:
            raise WholeSurfaceMathError(
                "post_line_search_anchor_displacement_not_exact"
            )

    topology_after = topology_sha256(len(vertices), copied_faces)
    if topology_after != topology_digest:
        raise WholeSurfaceMathError("topology_index_preservation_failed")
    post_line_search_residual = _equation_residual(
        selected_field, region_adjacency, free_vertices, limits[0]
    )
    if post_line_search_residual > limits[2]:
        raise WholeSurfaceMathError(
            "post_line_search_screened_harmonic_residual_exceeded:"
            f"{post_line_search_residual:.17g}:{limits[2]:.17g}"
        )

    adjacency_slots = sum(len(row) for row in region_adjacency)
    storage_upper_bound = (
        len(vertices) * 12
        + adjacency_slots * 2
        + len(copied_faces) * 4
        + len(anchors) * 8
    )
    field_base64, field_digest = encode_vector_field(selected_field)
    candidate_base64, candidate_digest = encode_candidate_vertices(candidate)
    evidence: dict[str, object] = {
        "qualification_id": qualification,
        "vertex_count": len(vertices),
        "edge_count": edge_count,
        "face_count": len(copied_faces),
        "triangle_count": len(_triangles(copied_faces)),
        "connected_components": connected_components,
        "semantic_region_count": semantic_region_count,
        "protected_vertex_count": len(protected),
        "anchor_count": len(anchors),
        "free_vertex_count": len(free_vertices),
        "sparse_adjacency_slot_count": adjacency_slots,
        "sparse_storage_units_upper_bound": storage_upper_bound,
        "iteration_count": iteration_count,
        "iteration_state": "CONVERGED",
        "final_update_inf_fixed_1e12": _fixed_1e12(
            final_update, "final_update"
        ),
        "raw_equation_residual_inf_fixed_1e12": _fixed_1e12(
            final_residual, "raw_residual"
        ),
        "post_line_search_equation_residual_inf_fixed_1e12": _fixed_1e12(
            post_line_search_residual, "post_line_search_residual"
        ),
        "post_line_search_state": (
            "RESIDUAL_WITHIN_CONFIGURED_TOLERANCE"
        ),
        "line_search_attempt_count": 1 + len(rejections),
        "line_search_scale_numerator": 1,
        "line_search_scale_denominator": scale_denominator,
        "line_search_rejections": list(rejections),
        "baseline_space": baseline_coordinate_space,
        "anchor_space": anchor_coordinate_space,
        "topology_sha256": topology_digest,
        "topology_after_sha256": topology_after,
        "baseline_sha256": baseline_digest,
        "region_sha256": region_digest,
        "protected_sha256": protected_digest,
        "anchor_sha256": anchor_digest,
        "limits_codec": LIMITS_CODEC,
        "limits_sha256": limits_digest,
        "raw_displacement_sha256": raw_hash,
        "post_line_search_displacement_sha256": field_digest,
        "candidate_vertex_sha256": candidate_digest,
    }
    payload: dict[str, object] = {
        "schema": "kira.r25.whole_surface_math.v5",
        "status": (
            "STATIC_MATH_CORE_ONLY_REQUIRES_EXACT_BYTE_ISOLATED_WORKER_CONTROLLER"
        ),
        "check_scope": "NONAUTHORITATIVE_IN_PROCESS_MATH_CHECK",
        "displacement_field": {
            "codec": VECTOR_FIELD_CODEC,
            "vertex_count": len(selected_field),
            "base64": field_base64,
            "sha256": field_digest,
        },
        "candidate_vertices": {
            "codec": CANDIDATE_VERTEX_CODEC,
            "vertex_count": len(candidate),
            "base64": candidate_base64,
            "sha256": candidate_digest,
        },
        "evidence": evidence,
    }
    canonical_json_bytes(payload)
    return payload


def replay_r25_whole_surface_math(
    *, claimed_payload: dict[str, object], **complete_inputs: object
) -> str:
    """Recompute exact math, compare bytes, and return no authority token."""

    if type(claimed_payload) is not dict:
        raise WholeSurfaceMathError("claimed_payload_not_plain_dict")
    claimed_bytes = canonical_json_bytes(claimed_payload)
    recomputed = compute_r25_whole_surface_math(**complete_inputs)
    if claimed_bytes != canonical_json_bytes(recomputed):
        raise WholeSurfaceMathError("non_authoritative_math_replay_mismatch")
    return "NONAUTHORITATIVE_IN_PROCESS_MATH_CHECK"


__all__ = (
    "CANDIDATE_VERTEX_CODEC",
    "LIMITS_CODEC",
    "MAX_JACOBI_ITERATIONS",
    "MAX_LINE_SEARCH_BACKTRACKS",
    "NONAUTHORITATIVE_CHECK",
    "SEMANTIC_REGIONS",
    "STATIC_MATH_STATUS",
    "TOPOLOGY_CODEC",
    "VECTOR_FIELD_CODEC",
    "WholeSurfaceMathError",
    "anchor_displacements_sha256",
    "baseline_sha256",
    "candidate_vertices_sha256",
    "canonical_json_bytes",
    "compute_r25_whole_surface_math",
    "encode_candidate_vertices",
    "encode_vector_field",
    "fit_limits_sha256",
    "index_set_sha256",
    "regions_sha256",
    "replay_r25_whole_surface_math",
    "topology_sha256",
    "vector_field_sha256",
)
