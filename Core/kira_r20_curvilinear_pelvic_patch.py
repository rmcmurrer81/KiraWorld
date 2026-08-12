"""Pure geometry contract for Kira's bounded R20 external-surface repair.

This module contains no Blender import and performs no file, render, runtime,
or GPU work.  It builds only the 34-seam/740-new-vertex/756-quad topology and
its bounded external-surface fields.  The shallow capped depressions are
surface geometry; they are not internal tracts or functional organs.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Iterable, Mapping, Sequence


METHOD_ID = "R20_BLACKPROJECT_CLAMPED_CURVILINEAR_QUAD_PATCH_V1"
SOURCE_BLEND_SHA256 = (
    "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f"
)
SOURCE_PACKAGE_MANIFEST_SHA256 = (
    "9c7038b60e2c712e49e810c0b7f7932bf36a18042dd00a6951834be59bb40f0c"
)
PLAN_SHA256 = "d9907f9ac7db74999ce2853b8865f614ccacabfabacef82b3111374dd89d0035"
FREEZE_LEDGER_SHA256 = (
    "b63bdff693d8efe239f982d72591e4523c860abe89107a79d7b4607e43243873"
)
SOURCE_LEDGER_SHA256 = (
    "3076b54d86a705d599a142816ace5688bf34b89ce230d0ba11bfddcd55964ee4"
)

SEAM_COUNT = 34
COLLAR_RING_COUNT = 2
CORE_COLUMNS = 21
CORE_ROWS = 32
CORE_VERTEX_COUNT = CORE_COLUMNS * CORE_ROWS
CORE_PERIMETER_COUNT = 2 * (CORE_COLUMNS + CORE_ROWS) - 4
COLLAR_1_OFFSET = SEAM_COUNT
COLLAR_2_OFFSET = SEAM_COUNT * 2
CORE_OFFSET = SEAM_COUNT * 3
TOTAL_PATCH_INCIDENT_VERTICES = CORE_OFFSET + CORE_VERTEX_COUNT
NEW_VERTEX_COUNT = TOTAL_PATCH_INCIDENT_VERTICES - SEAM_COUNT
REPLACEMENT_FACE_COUNT = 756
REPLACEMENT_EDGE_COUNT = 1529
MAXIMUM_FEATURE_OFFSET_M = 0.005

# A three-to-one all-quad transition has a fixed outer edge and three inner
# perimeter edges.  Each radial/circumferential edge therefore needs a small
# margin above one third of the corresponding fixed edge in order to satisfy
# the sealed maximum 3.0 edge-ratio gate after floating-point evaluation and
# on locally uneven interface spacing.  These are geometry-construction
# floors, not relaxed acceptance thresholds.
MINIMUM_LOCAL_COLLAR_EXTENT_EDGE_FRACTION = 1.08
MINIMUM_LOCAL_CORE_INSET_EDGE_FRACTION = 0.38
TRANSITION_SUBEDGE_TARGET_FRACTION = 0.334
CORE_QUALITY_STABILIZATION_ITERATIONS = 400
CORE_QUALITY_STABILIZATION_RELAXATION = 0.10

U_STATIONS = (
    -1.0,
    -0.86,
    -0.73,
    -0.61,
    -0.50,
    -0.40,
    -0.31,
    -0.23,
    -0.15,
    -0.075,
    0.0,
    0.075,
    0.15,
    0.23,
    0.31,
    0.40,
    0.50,
    0.61,
    0.73,
    0.86,
    1.0,
)

V_STATIONS = (
    0.0,
    0.045,
    0.09,
    0.135,
    0.18,
    0.225,
    0.27,
    0.31,
    0.345,
    0.375,
    0.405,
    0.435,
    0.465,
    0.495,
    0.525,
    0.555,
    0.585,
    0.615,
    0.645,
    0.675,
    0.705,
    0.735,
    0.765,
    0.795,
    0.825,
    0.855,
    0.885,
    0.915,
    0.94,
    0.962,
    0.982,
    1.0,
)

EXTERNAL_LANDMARK_ORDER = (
    "clitoral_hood_and_restrained_glans",
    "external_urethral_meatus",
    "vaginal_opening_introitus",
    "posterior_fourchette",
    "continuous_perineum",
    "separate_anal_region",
)

Vec2 = tuple[float, float]
Vec3 = tuple[float, float, float]
Mat3 = tuple[tuple[float, float, float], ...]
Mat4 = tuple[tuple[float, float, float, float], ...]
Quad = tuple[int, int, int, int]


@dataclass(frozen=True)
class CandidateParameters:
    candidate_id: str
    label: str
    collar_extent_edge_fraction: float
    core_inset_edge_fraction: float
    feature_scale: float
    asymmetry: float
    biharmonic_iterations: int
    biharmonic_relaxation: float


CANDIDATES = (
    CandidateParameters(
        candidate_id="r20_candidate_a_balanced_organic",
        label="balanced organic relief",
        collar_extent_edge_fraction=0.92,
        core_inset_edge_fraction=0.34,
        feature_scale=1.0,
        asymmetry=0.035,
        biharmonic_iterations=180,
        biharmonic_relaxation=0.08,
    ),
    CandidateParameters(
        candidate_id="r20_candidate_b_soft_natural",
        label="softer natural relief",
        collar_extent_edge_fraction=0.86,
        core_inset_edge_fraction=0.30,
        feature_scale=0.82,
        asymmetry=-0.025,
        biharmonic_iterations=220,
        biharmonic_relaxation=0.07,
    ),
)


@dataclass(frozen=True)
class WeightSolution:
    records: tuple[dict[str, float], ...]
    iterations: int
    final_maximum_delta: float
    group_count_before_projection: int
    maximum_positive_influences_after_projection: int


def _finite(value: float, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _v3(value: Sequence[float], label: str) -> Vec3:
    if len(value) != 3:
        raise ValueError(f"{label} must have three coordinates")
    return tuple(_finite(component, label) for component in value)  # type: ignore[return-value]


def _add(first: Vec3, second: Vec3) -> Vec3:
    return tuple(first[index] + second[index] for index in range(3))  # type: ignore[return-value]


def _sub(first: Vec3, second: Vec3) -> Vec3:
    return tuple(first[index] - second[index] for index in range(3))  # type: ignore[return-value]


def _scale(value: Vec3, scalar: float) -> Vec3:
    return tuple(component * scalar for component in value)  # type: ignore[return-value]


def _dot(first: Vec3, second: Vec3) -> float:
    return sum(first[index] * second[index] for index in range(3))


def _cross(first: Vec3, second: Vec3) -> Vec3:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _length(value: Vec3) -> float:
    return math.sqrt(_dot(value, value))


def _normalize(value: Vec3, label: str) -> Vec3:
    length = _length(value)
    if length <= 1.0e-12:
        raise ValueError(f"{label} collapsed")
    return _scale(value, 1.0 / length)


def _lerp(first: Vec3, second: Vec3, alpha: float) -> Vec3:
    return _add(_scale(first, 1.0 - alpha), _scale(second, alpha))


def _mean(values: Iterable[Vec3]) -> Vec3:
    records = list(values)
    if not records:
        raise ValueError("cannot average an empty vector sequence")
    return _scale(
        tuple(sum(value[axis] for value in records) for axis in range(3)),  # type: ignore[arg-type]
        1.0 / len(records),
    )


def _median(values: Iterable[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("cannot take an empty median")
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return 0.5 * (ordered[middle - 1] + ordered[middle])


def _square_matrix(
    value: Sequence[Sequence[float]], size: int, label: str
) -> tuple[tuple[float, ...], ...]:
    if len(value) != size or any(len(row) != size for row in value):
        raise ValueError(f"{label} must be {size}x{size}")
    return tuple(
        tuple(_finite(component, label) for component in row) for row in value
    )


def positive_affine_transform_matrices(
    matrix_world: Sequence[Sequence[float]],
) -> tuple[Mat4, Mat3, dict[str, object]]:
    """Return a positive affine inverse and inverse-transpose normal matrix.

    The full linear part is retained, so nonuniform scale and shear are safe.
    Singular, reflected, projective, or nonfinite transforms fail closed.
    """

    rows = _square_matrix(matrix_world, 4, "affine matrix")
    if any(abs(rows[3][column]) > 1.0e-12 for column in range(3)) or not math.isclose(
        rows[3][3], 1.0, rel_tol=0.0, abs_tol=1.0e-12
    ):
        raise ValueError("matrix must be finite affine, not projective")
    linear = tuple(tuple(rows[row][column] for column in range(3)) for row in range(3))
    determinant = (
        linear[0][0] * (linear[1][1] * linear[2][2] - linear[1][2] * linear[2][1])
        - linear[0][1] * (linear[1][0] * linear[2][2] - linear[1][2] * linear[2][0])
        + linear[0][2] * (linear[1][0] * linear[2][1] - linear[1][1] * linear[2][0])
    )
    if determinant <= 1.0e-15:
        raise ValueError(
            "matrix linear part must be nonsingular and orientation preserving"
        )

    augmented = [
        list(linear[row]) + [1.0 if row == column else 0.0 for column in range(3)]
        for row in range(3)
    ]
    for column in range(3):
        pivot_row = max(range(column, 3), key=lambda row: abs(augmented[row][column]))
        pivot = augmented[pivot_row][column]
        if abs(pivot) <= 1.0e-15:
            raise ValueError("matrix linear part is numerically singular")
        augmented[column], augmented[pivot_row] = augmented[pivot_row], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(3):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                augmented[row][index] - factor * augmented[column][index]
                for index in range(6)
            ]
    inverse_linear: Mat3 = tuple(
        tuple(float(augmented[row][column]) for column in range(3, 6))
        for row in range(3)
    )  # type: ignore[assignment]
    translation = tuple(rows[row][3] for row in range(3))
    inverse_translation = tuple(
        -sum(inverse_linear[row][column] * translation[column] for column in range(3))
        for row in range(3)
    )
    inverse: Mat4 = tuple(
        tuple(inverse_linear[row]) + (inverse_translation[row],) for row in range(3)
    ) + ((0.0, 0.0, 0.0, 1.0),)  # type: ignore[assignment]
    normal_matrix: Mat3 = tuple(
        tuple(inverse_linear[column][row] for column in range(3)) for row in range(3)
    )  # type: ignore[assignment]

    basis = tuple(
        tuple(linear[row][column] for row in range(3)) for column in range(3)
    )
    basis_scales = tuple(_length(vector) for vector in basis)
    if min(basis_scales) <= 1.0e-12:
        raise ValueError("matrix contains a collapsed basis vector")
    shear_cosines = tuple(
        abs(_dot(basis[first], basis[second]) / (basis_scales[first] * basis_scales[second]))
        for first, second in ((0, 1), (0, 2), (1, 2))
    )
    evidence: dict[str, object] = {
        "determinant": determinant,
        "orientation_preserving": True,
        "affine_last_row": list(rows[3]),
        "basis_scales_project_m_per_local_unit": list(basis_scales),
        "maximum_to_minimum_basis_scale_ratio": max(basis_scales) / min(basis_scales),
        "maximum_absolute_basis_shear_cosine": max(shear_cosines),
        "full_affine_point_transform_used": True,
        "inverse_transpose_normal_transform_used": True,
        "nonuniform_scale_and_shear_supported": True,
        "reflection_projective_singular_transform_rejected": True,
    }
    return inverse, normal_matrix, evidence


def transform_affine_points(
    matrix: Sequence[Sequence[float]], points: Sequence[Sequence[float]]
) -> tuple[Vec3, ...]:
    rows = _square_matrix(matrix, 4, "affine point-transform matrix")
    result = []
    for raw in points:
        point = _v3(raw, "affine point")
        result.append(
            tuple(
                sum(rows[row][column] * point[column] for column in range(3))
                + rows[row][3]
                for row in range(3)
            )
        )
    return tuple(result)  # type: ignore[return-value]


def transform_normals(
    normal_matrix: Sequence[Sequence[float]], normals: Sequence[Sequence[float]]
) -> tuple[Vec3, ...]:
    rows = _square_matrix(normal_matrix, 3, "normal matrix")
    return tuple(
        _normalize(
            tuple(
                sum(rows[row][column] * normal[column] for column in range(3))
                for row in range(3)
            ),  # type: ignore[arg-type]
            "transformed normal",
        )
        for normal in (_v3(value, "source normal") for value in normals)
    )


def closed_cycle_median_edge_scale(points: Sequence[Sequence[float]]) -> float:
    values = tuple(_v3(point, "cycle point") for point in points)
    if len(values) < 3:
        raise ValueError("closed cycle must contain at least three points")
    return _median(
        _length(_sub(values[(index + 1) % len(values)], values[index]))
        for index in range(len(values))
    )


def affine_roundtrip_maximum_delta(
    points: Sequence[Sequence[float]],
    matrix_world: Sequence[Sequence[float]],
    matrix_world_inverse: Sequence[Sequence[float]],
) -> float:
    source = tuple(_v3(point, "roundtrip source point") for point in points)
    returned = transform_affine_points(
        matrix_world_inverse, transform_affine_points(matrix_world, source)
    )
    return max(_length(_sub(first, second)) for first, second in zip(source, returned))


def _smoothstep(value: float) -> float:
    t = max(0.0, min(1.0, float(value)))
    return t * t * (3.0 - 2.0 * t)


def core_index(row: int, column: int) -> int:
    if not 0 <= row < CORE_ROWS or not 0 <= column < CORE_COLUMNS:
        raise IndexError((row, column))
    return CORE_OFFSET + row * CORE_COLUMNS + column


def core_perimeter_indices() -> tuple[int, ...]:
    result = [core_index(0, column) for column in range(CORE_COLUMNS)]
    result.extend(core_index(row, CORE_COLUMNS - 1) for row in range(1, CORE_ROWS))
    result.extend(core_index(CORE_ROWS - 1, column) for column in range(CORE_COLUMNS - 2, -1, -1))
    result.extend(core_index(row, 0) for row in range(CORE_ROWS - 2, 0, -1))
    if len(result) != CORE_PERIMETER_COUNT or len(set(result)) != CORE_PERIMETER_COUNT:
        raise AssertionError("core perimeter construction drifted")
    return tuple(result)


def build_quad_topology(*, reverse_winding: bool = False) -> tuple[Quad, ...]:
    faces: list[Quad] = []
    for index in range(SEAM_COUNT):
        following = (index + 1) % SEAM_COUNT
        faces.append(
            (
                index,
                following,
                COLLAR_1_OFFSET + following,
                COLLAR_1_OFFSET + index,
            )
        )
        faces.append(
            (
                COLLAR_1_OFFSET + index,
                COLLAR_1_OFFSET + following,
                COLLAR_2_OFFSET + following,
                COLLAR_2_OFFSET + index,
            )
        )

    perimeter = core_perimeter_indices()
    for index in range(SEAM_COUNT):
        start = 3 * index
        following = (index + 1) % SEAM_COUNT
        faces.append(
            (
                COLLAR_2_OFFSET + index,
                perimeter[start],
                perimeter[start + 1],
                perimeter[start + 2],
            )
        )
        faces.append(
            (
                COLLAR_2_OFFSET + index,
                perimeter[start + 2],
                perimeter[(start + 3) % CORE_PERIMETER_COUNT],
                COLLAR_2_OFFSET + following,
            )
        )

    for row in range(CORE_ROWS - 1):
        for column in range(CORE_COLUMNS - 1):
            faces.append(
                (
                    core_index(row, column),
                    core_index(row, column + 1),
                    core_index(row + 1, column + 1),
                    core_index(row + 1, column),
                )
            )
    if reverse_winding:
        faces = [tuple(reversed(face)) for face in faces]  # type: ignore[assignment]
    return tuple(faces)


def topology_adjacency(faces: Sequence[Quad]) -> tuple[frozenset[int], ...]:
    adjacency = [set() for _ in range(TOTAL_PATCH_INCIDENT_VERTICES)]
    for face in faces:
        for first, second in zip(face, face[1:] + face[:1]):
            adjacency[first].add(second)
            adjacency[second].add(first)
    return tuple(frozenset(values) for values in adjacency)


def topology_contract(faces: Sequence[Quad] | None = None) -> dict[str, object]:
    values = tuple(faces or build_quad_topology())
    if any(len(face) != 4 or len(set(face)) != 4 for face in values):
        raise ValueError("R20 topology contains a non-quad or repeated face vertex")
    if any(index < 0 or index >= TOTAL_PATCH_INCIDENT_VERTICES for face in values for index in face):
        raise ValueError("R20 topology references an out-of-range vertex")
    canonical_faces = {tuple(sorted(face)) for face in values}
    if len(canonical_faces) != len(values):
        raise ValueError("R20 topology contains duplicate faces")

    incidence: defaultdict[tuple[int, int], int] = defaultdict(int)
    for face in values:
        for first, second in zip(face, face[1:] + face[:1]):
            incidence[tuple(sorted((first, second)))] += 1
    boundary = sorted(edge for edge, count in incidence.items() if count == 1)
    nonmanifold = sorted(edge for edge, count in incidence.items() if count > 2)
    adjacency = topology_adjacency(values)
    seen = {0}
    queue = deque([0])
    while queue:
        current = queue.popleft()
        for neighbor in adjacency[current]:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    maximum_valence = max(map(len, adjacency))
    digest = hashlib.sha256(
        json.dumps(values, separators=(",", ":")).encode("ascii")
    ).hexdigest()
    return {
        "method_id": METHOD_ID,
        "vertices_including_reused_seam": TOTAL_PATCH_INCIDENT_VERTICES,
        "new_vertices": NEW_VERTEX_COUNT,
        "faces": len(values),
        "quads": len(values),
        "triangles": 0,
        "ngons": 0,
        "edges": len(incidence),
        "boundary_edges": len(boundary),
        "boundary_vertices": len({vertex for edge in boundary for vertex in edge}),
        "boundary_is_exact_seam": set(boundary)
        == {tuple(sorted((index, (index + 1) % SEAM_COUNT))) for index in range(SEAM_COUNT)},
        "nonmanifold_edges": len(nonmanifold),
        "connected_components": 1 if len(seen) == TOTAL_PATCH_INCIDENT_VERTICES else 2,
        "visited_vertices": len(seen),
        "maximum_vertex_valence": maximum_valence,
        "euler_disk_value": TOTAL_PATCH_INCIDENT_VERTICES - len(incidence) + len(values),
        "connectivity_sha256": digest,
    }


def mask_topology_contract(
    faces: Sequence[Sequence[int]],
    selected_face_indices: Iterable[int],
) -> dict[str, object]:
    """Validate a connected selected-face insert without any Blender import.

    This is the fake/static-test counterpart to the Blender mask preflight.
    It deliberately makes no selection from filenames or coordinates; callers
    must first bind the exact material/asset authority and then supply the
    selected face IDs.
    """

    values = tuple(tuple(int(vertex) for vertex in face) for face in faces)
    selected = {int(index) for index in selected_face_indices}
    if not selected or any(index < 0 or index >= len(values) for index in selected):
        raise ValueError("selected face IDs are empty or out of range")
    if any(len(face) < 3 or len(set(face)) != len(face) for face in values):
        raise ValueError("mask source contains a degenerate face")
    edge_faces: defaultdict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(values):
        for first, second in zip(face, face[1:] + face[:1]):
            edge_faces[tuple(sorted((first, second)))].append(face_index)
    selected_adjacency: defaultdict[int, set[int]] = defaultdict(set)
    interface_edges = []
    for edge, incident_faces in edge_faces.items():
        selected_incident = [index for index in incident_faces if index in selected]
        if len(selected_incident) > 1:
            for first in selected_incident:
                selected_adjacency[first].update(
                    second for second in selected_incident if second != first
                )
        if selected_incident and len(selected_incident) != len(incident_faces):
            if len(incident_faces) != 2 or len(selected_incident) != 1:
                raise ValueError("interface edge does not have exactly one face per side")
            interface_edges.append(edge)
    unseen = set(selected)
    components = 0
    while unseen:
        components += 1
        queue = deque([unseen.pop()])
        while queue:
            current = queue.popleft()
            for neighbor in selected_adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
    interface_graph: defaultdict[int, set[int]] = defaultdict(set)
    for first, second in interface_edges:
        interface_graph[first].add(second)
        interface_graph[second].add(first)
    interface_is_cycles = bool(interface_graph) and all(
        len(neighbors) == 2 for neighbors in interface_graph.values()
    )
    interface_components = 0
    unseen_interface = set(interface_graph)
    while unseen_interface:
        interface_components += 1
        queue = deque([unseen_interface.pop()])
        while queue:
            current = queue.popleft()
            for neighbor in interface_graph[current]:
                if neighbor in unseen_interface:
                    unseen_interface.remove(neighbor)
                    queue.append(neighbor)
    incident_vertices = {
        vertex for face_index in selected for vertex in values[face_index]
    }
    interface_vertices = set(interface_graph)
    removable_vertices = incident_vertices - interface_vertices
    unselected_vertices = {
        vertex
        for face_index, face in enumerate(values)
        if face_index not in selected
        for vertex in face
    }
    if removable_vertices.intersection(unselected_vertices):
        raise ValueError("a removable vertex is referenced by an unselected face")
    return {
        "selected_face_count": len(selected),
        "selected_face_connected_components": components,
        "incident_vertex_count": len(incident_vertices),
        "interface_edge_count": len(interface_edges),
        "interface_vertex_count": len(interface_vertices),
        "interface_degree_two": interface_is_cycles,
        "interface_connected_components": interface_components,
        "removable_interior_vertex_count": len(removable_vertices),
        "selected_face_indices_sha256": hashlib.sha256(
            json.dumps(sorted(selected), separators=(",", ":")).encode("ascii")
        ).hexdigest(),
    }


def canonicalize_cycle(
    points: Sequence[Sequence[float]],
) -> tuple[tuple[Vec3, ...], tuple[int, ...]]:
    """Apply the sealed minimum-Y start and greater-Z direction rule."""

    if len(points) != SEAM_COUNT:
        raise ValueError(f"expected {SEAM_COUNT} seam points, found {len(points)}")
    values = tuple(_v3(point, "seam point") for point in points)
    if len(set(values)) != SEAM_COUNT:
        raise ValueError("seam cycle contains duplicate coordinates")
    start = min(
        range(SEAM_COUNT),
        key=lambda index: (
            values[index][1],
            abs(values[index][0]),
            -values[index][2],
            -values[index][0],
        ),
    )
    previous = (start - 1) % SEAM_COUNT
    following = (start + 1) % SEAM_COUNT
    direction_key = lambda index: (values[index][2], values[index][0])
    if direction_key(previous) == direction_key(following):
        raise ValueError("seam direction rule is ambiguous")
    step = 1 if direction_key(following) > direction_key(previous) else -1
    order = tuple((start + step * offset) % SEAM_COUNT for offset in range(SEAM_COUNT))
    return tuple(values[index] for index in order), order


def _catmull_rom(points: Sequence[Vec3], segment: int, alpha: float) -> Vec3:
    count = len(points)
    p0 = points[(segment - 1) % count]
    p1 = points[segment % count]
    p2 = points[(segment + 1) % count]
    p3 = points[(segment + 2) % count]
    t = float(alpha)
    t2 = t * t
    t3 = t2 * t
    return tuple(
        0.5
        * (
            2.0 * p1[axis]
            + (-p0[axis] + p2[axis]) * t
            + (2.0 * p0[axis] - 5.0 * p1[axis] + 4.0 * p2[axis] - p3[axis]) * t2
            + (-p0[axis] + 3.0 * p1[axis] - 3.0 * p2[axis] + p3[axis]) * t3
        )
        for axis in range(3)
    )  # type: ignore[return-value]


def _hermite(first: Vec3, second: Vec3, first_tangent: Vec3, second_tangent: Vec3, t: float) -> Vec3:
    t2 = t * t
    t3 = t2 * t
    h00 = 2.0 * t3 - 3.0 * t2 + 1.0
    h10 = t3 - 2.0 * t2 + t
    h01 = -2.0 * t3 + 3.0 * t2
    h11 = t3 - t2
    return tuple(
        h00 * first[axis]
        + h10 * first_tangent[axis]
        + h01 * second[axis]
        + h11 * second_tangent[axis]
        for axis in range(3)
    )  # type: ignore[return-value]


def _coons(
    top: Vec3,
    right: Vec3,
    bottom: Vec3,
    left: Vec3,
    corners: tuple[Vec3, Vec3, Vec3, Vec3],
    s: float,
    t: float,
) -> Vec3:
    q00, q10, q11, q01 = corners
    boundary_blend = _add(
        _add(_scale(top, 1.0 - t), _scale(bottom, t)),
        _add(_scale(left, 1.0 - s), _scale(right, s)),
    )
    bilinear = _add(
        _add(_scale(q00, (1.0 - s) * (1.0 - t)), _scale(q10, s * (1.0 - t))),
        _add(_scale(q01, (1.0 - s) * t), _scale(q11, s * t)),
    )
    return _sub(boundary_blend, bilinear)


def _fair_core(
    grid: list[list[Vec3]],
    iterations: int,
    relaxation: float,
) -> None:
    for _iteration in range(iterations):
        previous = [list(row) for row in grid]
        for row in range(1, CORE_ROWS - 1):
            for column in range(1, CORE_COLUMNS - 1):
                current = previous[row][column]
                if 2 <= row < CORE_ROWS - 2 and 2 <= column < CORE_COLUMNS - 2:
                    axial = _mean(
                        (
                            previous[row - 1][column],
                            previous[row + 1][column],
                            previous[row][column - 1],
                            previous[row][column + 1],
                        )
                    )
                    diagonal = _mean(
                        (
                            previous[row - 1][column - 1],
                            previous[row - 1][column + 1],
                            previous[row + 1][column - 1],
                            previous[row + 1][column + 1],
                        )
                    )
                    second = _mean(
                        (
                            previous[row - 2][column],
                            previous[row + 2][column],
                            previous[row][column - 2],
                            previous[row][column + 2],
                        )
                    )
                    target = _add(
                        _scale(axial, 1.6),
                        _add(_scale(diagonal, -0.4), _scale(second, -0.2)),
                    )
                else:
                    target = _mean(
                        (
                            previous[row - 1][column],
                            previous[row + 1][column],
                            previous[row][column - 1],
                            previous[row][column + 1],
                        )
                    )
                grid[row][column] = _lerp(current, target, relaxation)


def _stabilize_core_quality(grid: list[list[Vec3]]) -> None:
    """Damp only the high-frequency ringing left by the thin-plate solve.

    The sealed baseline remains the clamped Coons/biharmonic construction.
    This bounded harmonic tail does not move its perimeter; it prevents the
    alternating 34->102 transition correction from collapsing the first
    interior core row on locally uneven seams.
    """

    for _iteration in range(CORE_QUALITY_STABILIZATION_ITERATIONS):
        previous = [list(row) for row in grid]
        for row in range(1, CORE_ROWS - 1):
            for column in range(1, CORE_COLUMNS - 1):
                target = _mean(
                    (
                        previous[row - 1][column],
                        previous[row + 1][column],
                        previous[row][column - 1],
                        previous[row][column + 1],
                    )
                )
                grid[row][column] = _lerp(
                    previous[row][column],
                    target,
                    CORE_QUALITY_STABILIZATION_RELAXATION,
                )


def _gaussian(u: float, v: float, cu: float, cv: float, su: float, sv: float) -> float:
    return math.exp(-0.5 * (((u - cu) / su) ** 2 + ((v - cv) / sv) ** 2))


def _ridge(u: float, v: float, center: float, width: float, cv: float, sv: float) -> float:
    return _gaussian(u, v, center, cv, width, sv)


def _annulus(u: float, v: float, cu: float, cv: float, su: float, sv: float) -> float:
    radius = math.sqrt(((u - cu) / su) ** 2 + ((v - cv) / sv) ** 2)
    return math.exp(-0.5 * ((radius - 1.0) / 0.24) ** 2)


def external_feature_components(
    u: float,
    v: float,
    *,
    asymmetry: float,
) -> dict[str, float]:
    left_scale = 1.0 + asymmetry
    right_scale = 1.0 - asymmetry
    return {
        "mons": 0.00078 * _gaussian(u, v, 0.0, 0.145, 0.58, 0.15),
        "labia_majora_left": 0.00158 * left_scale * _ridge(u, v, -0.39, 0.16, 0.50, 0.27),
        "labia_majora_right": 0.00158 * right_scale * _ridge(u, v, 0.39, 0.16, 0.50, 0.27),
        "labial_sulci": -0.00030
        * (_ridge(u, v, -0.25, 0.085, 0.51, 0.24) + _ridge(u, v, 0.25, 0.085, 0.51, 0.24)),
        "labia_minora_left": 0.00092 * left_scale * _ridge(u, v, -0.12, 0.065, 0.51, 0.22),
        "labia_minora_right": 0.00092 * right_scale * _ridge(u, v, 0.12, 0.065, 0.51, 0.22),
        "clitoral_hood_and_restrained_glans": 0.00058 * _gaussian(u, v, 0.0, 0.285, 0.14, 0.060),
        "vestibule": -0.00023 * _gaussian(u, v, 0.0, 0.52, 0.17, 0.19),
        "urethral_meatus_rim": 0.00029 * _annulus(u, v, 0.0, 0.405, 0.105, 0.043),
        "urethral_meatus_blind_cap": -0.00048 * _gaussian(u, v, 0.0, 0.405, 0.060, 0.025),
        "vaginal_opening_rim": 0.00052 * _annulus(u, v, 0.0, 0.605, 0.20, 0.080),
        "vaginal_opening_blind_cap": -0.00094 * _gaussian(u, v, 0.0, 0.605, 0.13, 0.055),
        "posterior_fourchette": 0.00034 * _gaussian(u, v, 0.0, 0.755, 0.18, 0.045),
        "continuous_perineum": 0.00014 * _gaussian(u, v, 0.0, 0.83, 0.27, 0.10),
        "anal_rim": 0.00039 * _annulus(u, v, 0.0, 0.925, 0.16, 0.040),
        "anal_blind_cap": -0.00072 * _gaussian(u, v, 0.0, 0.925, 0.095, 0.025),
    }


def feature_displacement(u: float, v: float, candidate: CandidateParameters) -> tuple[float, dict[str, float]]:
    terms = external_feature_components(u, v, asymmetry=candidate.asymmetry)
    value = candidate.feature_scale * sum(terms.values())
    if abs(value) > MAXIMUM_FEATURE_OFFSET_M:
        raise ValueError(f"external feature field exceeded {MAXIMUM_FEATURE_OFFSET_M} m")
    return value, {name: candidate.feature_scale * raw for name, raw in terms.items()}


def _feature_taper(row: int, column: int) -> float:
    distance = min(row, CORE_ROWS - 1 - row, column, CORE_COLUMNS - 1 - column)
    return _smoothstep(distance / 3.0)


def build_positions(
    seam_points: Sequence[Sequence[float]],
    exterior_ring_1: Sequence[Sequence[float]],
    exterior_ring_2: Sequence[Sequence[float]],
    seam_normals: Sequence[Sequence[float]],
    candidate: CandidateParameters,
) -> tuple[tuple[Vec3, ...], dict[str, object]]:
    if any(len(values) != SEAM_COUNT for values in (seam_points, exterior_ring_1, exterior_ring_2, seam_normals)):
        raise ValueError("seam, exterior rings, and seam normals must each have 34 entries")
    seam = tuple(_v3(value, "seam") for value in seam_points)
    exterior_1 = tuple(_v3(value, "exterior ring 1") for value in exterior_ring_1)
    exterior_2 = tuple(_v3(value, "exterior ring 2") for value in exterior_ring_2)
    normals = tuple(_normalize(_v3(value, "seam normal"), "seam normal") for value in seam_normals)
    edge_scale = _median(
        _length(_sub(seam[(index + 1) % SEAM_COUNT], seam[index]))
        for index in range(SEAM_COUNT)
    )
    if not 1.0e-5 <= edge_scale <= 0.10:
        raise ValueError(f"seam median edge scale is implausible: {edge_scale}")

    seam_edge_lengths = tuple(
        _length(_sub(seam[(index + 1) % SEAM_COUNT], seam[index]))
        for index in range(SEAM_COUNT)
    )
    collar_1: list[Vec3] = []
    collar_2: list[Vec3] = []
    inward_hints: list[Vec3] = []
    requested_extent = edge_scale * candidate.collar_extent_edge_fraction
    collar_extents: list[float] = []
    for index, point in enumerate(seam):
        local_edge_scale = max(
            seam_edge_lengths[(index - 1) % SEAM_COUNT],
            seam_edge_lengths[index],
        )
        extent = max(
            requested_extent,
            local_edge_scale * MINIMUM_LOCAL_COLLAR_EXTENT_EDGE_FRACTION,
        )
        collar_extents.append(extent)
        first_difference = _sub(point, exterior_1[index])
        inward = _normalize(first_difference, f"seam inward derivative {index}")
        curvature = _sub(_sub(point, _scale(exterior_1[index], 2.0)), _scale(exterior_2[index], -1.0))
        curvature = _scale(curvature, min(0.18, extent / max(_length(curvature), extent) * 0.18))
        endpoint = _add(_add(point, _scale(inward, extent)), curvature)
        first_tangent = _scale(inward, extent * 0.92)
        second_tangent = _scale(inward, extent * 0.62)
        collar_1.append(_hermite(point, endpoint, first_tangent, second_tangent, 1.0 / 3.0))
        collar_2.append(_hermite(point, endpoint, first_tangent, second_tangent, 2.0 / 3.0))
        inward_hints.append(inward)

    collar_2_edge_lengths = tuple(
        _length(_sub(collar_2[(index + 1) % SEAM_COUNT], collar_2[index]))
        for index in range(SEAM_COUNT)
    )
    requested_inset = edge_scale * candidate.core_inset_edge_fraction
    core_anchors: list[Vec3] = []
    core_anchor_inwards: list[Vec3] = []
    core_insets: list[float] = []
    for index, point in enumerate(collar_2):
        tangent = _normalize(
            _sub(collar_2[(index + 1) % SEAM_COUNT], collar_2[(index - 1) % SEAM_COUNT]),
            "collar-2 perimeter tangent",
        )
        inward = _cross(normals[index], tangent)
        if _dot(inward, inward_hints[index]) < 0.0:
            inward = _scale(inward, -1.0)
        inward = _normalize(inward, "local core-boundary inward")
        local_edge_scale = max(
            collar_2_edge_lengths[(index - 1) % SEAM_COUNT],
            collar_2_edge_lengths[index],
        )
        inset = max(
            requested_inset,
            local_edge_scale * MINIMUM_LOCAL_CORE_INSET_EDGE_FRACTION,
        )
        core_anchors.append(_add(point, _scale(inward, inset)))
        core_anchor_inwards.append(inward)
        core_insets.append(inset)

    # The inner perimeter of a nested loop is necessarily shorter than its
    # collar.  A naive one-third resample therefore exceeds the exact 3.0
    # ratio gate in the 34->102 transition.  For each collar edge, construct
    # the two intermediate points as the minimum symmetric deviation from the
    # anchor chord that gives all three perimeter subedges a deterministic
    # just-over-one-third outer-edge floor.  The deviation stays in the local tangent
    # surface (not the feature/normal direction), so it does not introduce an
    # anatomy relief term or modify the immutable seam.
    core_boundary: list[Vec3] = []
    core_boundary_normals: list[Vec3] = []
    transition_deviations: list[float] = []
    for segment in range(SEAM_COUNT):
        following = (segment + 1) % SEAM_COUNT
        first = core_anchors[segment]
        fourth = core_anchors[following]
        chord = _sub(fourth, first)
        chord_length = _length(chord)
        if chord_length <= 1.0e-12:
            raise ValueError(f"core-boundary anchor chord {segment} collapsed")
        chord_direction = _scale(chord, 1.0 / chord_length)
        quality_direction = _normalize(
            _lerp(core_anchor_inwards[segment], core_anchor_inwards[following], 0.5),
            f"transition quality direction {segment}",
        )
        quality_direction = _sub(
            quality_direction,
            _scale(chord_direction, _dot(quality_direction, chord_direction)),
        )
        if _length(quality_direction) <= 1.0e-12:
            averaged_normal = _normalize(
                _lerp(normals[segment], normals[following], 0.5),
                f"transition fallback normal {segment}",
            )
            quality_direction = _sub(
                averaged_normal,
                _scale(chord_direction, _dot(averaged_normal, chord_direction)),
            )
        quality_direction = _normalize(
            quality_direction,
            f"orthogonal transition quality direction {segment}",
        )
        target = collar_2_edge_lengths[segment] * TRANSITION_SUBEDGE_TARGET_FRACTION
        straight_subedge = chord_length / 3.0
        deviation = math.sqrt(max(0.0, target * target - straight_subedge * straight_subedge))
        second = _add(
            _lerp(first, fourth, 1.0 / 3.0),
            _scale(quality_direction, -deviation),
        )
        third = _add(
            _lerp(first, fourth, 2.0 / 3.0),
            _scale(quality_direction, deviation),
        )
        core_boundary.extend((first, second, third))
        core_boundary_normals.extend(
            (
                normals[segment],
                _normalize(_lerp(normals[segment], normals[following], 1.0 / 3.0), "transition normal"),
                _normalize(_lerp(normals[segment], normals[following], 2.0 / 3.0), "transition normal"),
            )
        )
        transition_deviations.append(deviation)
    if len(core_boundary) != CORE_PERIMETER_COUNT:
        raise AssertionError("three-to-one perimeter construction drifted")

    grid: list[list[Vec3 | None]] = [
        [None for _column in range(CORE_COLUMNS)] for _row in range(CORE_ROWS)
    ]
    normal_grid: list[list[Vec3 | None]] = [
        [None for _column in range(CORE_COLUMNS)] for _row in range(CORE_ROWS)
    ]
    for index, vertex_index in enumerate(core_perimeter_indices()):
        local = vertex_index - CORE_OFFSET
        row, column = divmod(local, CORE_COLUMNS)
        grid[row][column] = core_boundary[index]
        normal_grid[row][column] = core_boundary_normals[index]
    q00 = grid[0][0]
    q10 = grid[0][-1]
    q11 = grid[-1][-1]
    q01 = grid[-1][0]
    if None in (q00, q10, q11, q01):
        raise AssertionError("core corners were not assigned")
    corners = (q00, q10, q11, q01)  # type: ignore[arg-type]
    normal_corners = (
        normal_grid[0][0],
        normal_grid[0][-1],
        normal_grid[-1][-1],
        normal_grid[-1][0],
    )
    for row in range(1, CORE_ROWS - 1):
        t = V_STATIONS[row]
        for column in range(1, CORE_COLUMNS - 1):
            s = 0.5 * (U_STATIONS[column] + 1.0)
            grid[row][column] = _coons(
                grid[0][column],  # type: ignore[arg-type]
                grid[row][-1],  # type: ignore[arg-type]
                grid[-1][column],  # type: ignore[arg-type]
                grid[row][0],  # type: ignore[arg-type]
                corners,
                s,
                t,
            )
            normal_grid[row][column] = _normalize(
                _coons(
                    normal_grid[0][column],  # type: ignore[arg-type]
                    normal_grid[row][-1],  # type: ignore[arg-type]
                    normal_grid[-1][column],  # type: ignore[arg-type]
                    normal_grid[row][0],  # type: ignore[arg-type]
                    normal_corners,  # type: ignore[arg-type]
                    s,
                    t,
                ),
                "coons reference normal",
            )
    concrete_grid = [[value for value in row] for row in grid]
    if any(value is None for row in concrete_grid for value in row):
        raise AssertionError("core Coons initialization is incomplete")
    typed_grid: list[list[Vec3]] = concrete_grid  # type: ignore[assignment]
    _fair_core(
        typed_grid,
        candidate.biharmonic_iterations,
        candidate.biharmonic_relaxation,
    )
    _stabilize_core_quality(typed_grid)

    maximum_offset = 0.0
    feature_extrema: defaultdict[str, list[float]] = defaultdict(list)
    for row in range(CORE_ROWS):
        for column in range(CORE_COLUMNS):
            if row in (0, CORE_ROWS - 1) or column in (0, CORE_COLUMNS - 1):
                continue
            before = typed_grid[row][column]
            tangent_u = _sub(
                typed_grid[row][min(column + 1, CORE_COLUMNS - 1)],
                typed_grid[row][max(column - 1, 0)],
            )
            tangent_v = _sub(
                typed_grid[min(row + 1, CORE_ROWS - 1)][column],
                typed_grid[max(row - 1, 0)][column],
            )
            local_normal = _normalize(_cross(tangent_u, tangent_v), "core normal")
            reference_normal = normal_grid[row][column]
            if reference_normal is None:
                raise AssertionError("core reference normal is missing")
            if _dot(local_normal, reference_normal) < 0.0:
                local_normal = _scale(local_normal, -1.0)
            raw, terms = feature_displacement(
                U_STATIONS[column],
                V_STATIONS[row],
                candidate,
            )
            taper = _feature_taper(row, column)
            displacement = raw * taper
            typed_grid[row][column] = _add(before, _scale(local_normal, displacement))
            maximum_offset = max(maximum_offset, abs(displacement))
            for name, value in terms.items():
                feature_extrema[name].append(value * taper)

    positions: list[Vec3] = list(seam) + collar_1 + collar_2
    positions.extend(
        typed_grid[row][column]
        for row in range(CORE_ROWS)
        for column in range(CORE_COLUMNS)
    )
    if len(positions) != TOTAL_PATCH_INCIDENT_VERTICES:
        raise AssertionError("R20 position count drifted")
    return tuple(positions), {
        "method_id": METHOD_ID,
        "candidate": asdict(candidate),
        "median_seam_edge_m": edge_scale,
        "requested_collar_extent_m": requested_extent,
        "collar_extent_m": {
            "minimum": min(collar_extents),
            "maximum": max(collar_extents),
        },
        "requested_core_perimeter_inset_m": requested_inset,
        "core_perimeter_inset_m": {
            "minimum": min(core_insets),
            "maximum": max(core_insets),
        },
        "transition_subedge_target_fraction": TRANSITION_SUBEDGE_TARGET_FRACTION,
        "transition_quality_deviation_m": {
            "minimum": min(transition_deviations),
            "maximum": max(transition_deviations),
        },
        "core_quality_stabilization": {
            "method": "fixed-boundary harmonic high-frequency damping after biharmonic solve",
            "iterations": CORE_QUALITY_STABILIZATION_ITERATIONS,
            "relaxation": CORE_QUALITY_STABILIZATION_RELAXATION,
        },
        "maximum_absolute_feature_offset_m": maximum_offset,
        "feature_extrema_m": {
            name: {"minimum": min(values), "maximum": max(values)}
            for name, values in sorted(feature_extrema.items())
        },
        "baseline": "3D clamped Hermite collars plus XYZ Coons/biharmonic core with bounded fixed-boundary quality stabilization",
        "copied_donor_interior_vertices": 0,
        "copied_donor_interior_faces": 0,
        "separate_anatomy_objects": 0,
        "internal_tracts": 0,
    }


def _rect_perimeter(rows: range, columns: range) -> tuple[int, ...]:
    row_values = tuple(rows)
    column_values = tuple(columns)
    top = [core_index(row_values[0], column) for column in column_values]
    right = [core_index(row, column_values[-1]) for row in row_values[1:]]
    bottom = [core_index(row_values[-1], column) for column in reversed(column_values[:-1])]
    left = [core_index(row, column_values[0]) for row in reversed(row_values[1:-1])]
    return tuple(top + right + bottom + left)


def _rect_interior(rows: range, columns: range) -> tuple[int, ...]:
    row_values = tuple(rows)
    column_values = tuple(columns)
    return tuple(
        core_index(row, column)
        for row in row_values[1:-1]
        for column in column_values[1:-1]
    )


def landmark_vertex_sets() -> dict[str, tuple[int, ...]]:
    groups = {
        "mons": tuple(core_index(row, column) for row in range(0, 9) for column in range(4, 17)),
        "labia_majora_left": tuple(core_index(row, column) for row in range(7, 25) for column in range(4, 8)),
        "labia_majora_right": tuple(core_index(row, column) for row in range(7, 25) for column in range(13, 17)),
        "labia_minora_left": tuple(core_index(row, column) for row in range(8, 24) for column in range(8, 10)),
        "labia_minora_right": tuple(core_index(row, column) for row in range(8, 24) for column in range(11, 13)),
        "clitoral_hood_and_restrained_glans": tuple(
            core_index(row, column) for row in range(7, 11) for column in range(9, 12)
        ),
        "vestibule": tuple(core_index(row, column) for row in range(10, 24) for column in range(9, 12)),
        "external_urethral_meatus_rim": _rect_perimeter(range(11, 16), range(8, 13)),
        "external_urethral_meatus_blind_cap": _rect_interior(range(11, 16), range(8, 13)),
        "vaginal_opening_introitus_rim": _rect_perimeter(range(16, 24), range(7, 14)),
        "vaginal_opening_introitus_blind_cap": _rect_interior(range(16, 24), range(7, 14)),
        "posterior_fourchette": tuple(core_index(row, column) for row in range(23, 25) for column in range(9, 12)),
        "continuous_perineum": tuple(core_index(row, column) for row in range(24, 28) for column in range(8, 13)),
        "separate_anal_region_rim": _rect_perimeter(range(27, 32), range(8, 13)),
        "separate_anal_region_blind_cap": _rect_interior(range(27, 32), range(8, 13)),
    }
    if len(groups["external_urethral_meatus_rim"]) != 16:
        raise AssertionError("urethral rim count drifted")
    if len(groups["vaginal_opening_introitus_rim"]) != 26:
        raise AssertionError("vaginal rim count drifted")
    if len(groups["separate_anal_region_rim"]) != 16:
        raise AssertionError("anal rim count drifted")
    return groups


def landmark_records(positions: Sequence[Sequence[float]]) -> dict[str, dict[str, object]]:
    if len(positions) != TOTAL_PATCH_INCIDENT_VERTICES:
        raise ValueError("landmark records require the complete local patch position set")
    values = tuple(_v3(value, "landmark position") for value in positions)
    result: dict[str, dict[str, object]] = {}
    for name, indices in landmark_vertex_sets().items():
        center = _mean(values[index] for index in indices)
        result[name] = {
            "local_patch_vertex_indices": list(indices),
            "vertex_count": len(indices),
            "project_space_centroid_m": [float(component) for component in center],
            "same_connected_primary_surface": True,
            "semantic_hook_only": True,
        }
    result["required_longitudinal_order"] = {
        "names": list(EXTERNAL_LANDMARK_ORDER),
        "external_surface_only": True,
        "internal_function_claimed": False,
    }
    return result


def _segment_cross(first: Vec2, second: Vec2, third: Vec2) -> float:
    return (second[0] - first[0]) * (third[1] - first[1]) - (second[1] - first[1]) * (third[0] - first[0])


def _segments_intersect(a: Vec2, b: Vec2, c: Vec2, d: Vec2, tolerance: float = 1.0e-12) -> bool:
    ab_c = _segment_cross(a, b, c)
    ab_d = _segment_cross(a, b, d)
    cd_a = _segment_cross(c, d, a)
    cd_b = _segment_cross(c, d, b)
    return ab_c * ab_d < -tolerance and cd_a * cd_b < -tolerance


def uv_cycle_crossings(values: Sequence[Sequence[float]]) -> tuple[tuple[int, int], ...]:
    if len(values) != SEAM_COUNT:
        raise ValueError("UV seam must contain 34 values")
    points: tuple[Vec2, ...] = tuple(
        (_finite(value[0], "u"), _finite(value[1], "v"))
        for value in values
        if len(value) == 2
    )
    if len(points) != SEAM_COUNT:
        raise ValueError("each UV seam value must contain two components")
    result = []
    for first in range(SEAM_COUNT):
        first_next = (first + 1) % SEAM_COUNT
        for second in range(first + 1, SEAM_COUNT):
            second_next = (second + 1) % SEAM_COUNT
            if len({first, first_next, second, second_next}) < 4:
                continue
            if _segments_intersect(points[first], points[first_next], points[second], points[second_next]):
                result.append((first, second))
    return tuple(result)


def _harmonic_vectors(
    boundary: Sequence[Sequence[float]],
    dimension: int,
    *,
    tolerance: float,
    maximum_iterations: int,
) -> tuple[list[list[float]], int, float]:
    if len(boundary) != SEAM_COUNT:
        raise ValueError("harmonic boundary must contain 34 values")
    adjacency = topology_adjacency(build_quad_topology())
    if any(not neighbors for neighbors in adjacency):
        raise ValueError("harmonic graph contains an isolated vertex")
    boundary_values = [
        [_finite(component, "harmonic boundary") for component in value]
        for value in boundary
    ]
    if any(len(value) != dimension for value in boundary_values):
        raise ValueError("harmonic boundary dimension mismatch")
    mean = [sum(value[axis] for value in boundary_values) / SEAM_COUNT for axis in range(dimension)]
    values = [list(value) for value in boundary_values] + [list(mean) for _ in range(NEW_VERTEX_COUNT)]
    final_delta = math.inf
    for iteration in range(1, maximum_iterations + 1):
        maximum_delta = 0.0
        for index in range(SEAM_COUNT, TOTAL_PATCH_INCIDENT_VERTICES):
            target = [
                sum(values[neighbor][axis] for neighbor in adjacency[index]) / len(adjacency[index])
                for axis in range(dimension)
            ]
            maximum_delta = max(
                maximum_delta,
                max(abs(target[axis] - values[index][axis]) for axis in range(dimension)),
            )
            values[index] = target
        final_delta = maximum_delta
        if maximum_delta <= tolerance:
            return values, iteration, final_delta
    raise ValueError(
        f"harmonic solve did not converge in {maximum_iterations} iterations; delta={final_delta}"
    )


def harmonic_uv(
    seam_uv: Sequence[Sequence[float]],
    *,
    tolerance: float = 1.0e-10,
    maximum_iterations: int = 10000,
) -> tuple[tuple[Vec2, ...], dict[str, object]]:
    crossings = uv_cycle_crossings(seam_uv)
    if crossings:
        raise ValueError(f"seam UV cycle self-crosses: {crossings}")
    values, iterations, delta = _harmonic_vectors(
        seam_uv,
        2,
        tolerance=tolerance,
        maximum_iterations=maximum_iterations,
    )
    return tuple((value[0], value[1]) for value in values), {
        "method": "discrete_harmonic_mean_value_on_fixed_quad_graph",
        "iterations": iterations,
        "final_maximum_delta": delta,
        "exact_seam_values_retained": True,
    }


def _top_four(record: Mapping[str, float]) -> dict[str, float]:
    selected = sorted(
        ((str(name), float(value)) for name, value in record.items() if float(value) > 1.0e-12),
        key=lambda item: (-item[1], item[0]),
    )[:4]
    total = sum(value for _name, value in selected)
    if total <= 1.0e-12:
        raise ValueError("new R20 vertex has no positive seam-derived weight")
    return {name: value / total for name, value in selected}


def harmonic_weights(
    seam_weights: Sequence[Mapping[str, float]],
    *,
    tolerance: float = 1.0e-10,
    maximum_iterations: int = 10000,
) -> WeightSolution:
    if len(seam_weights) != SEAM_COUNT:
        raise ValueError("exactly 34 seam weight records are required")
    groups = tuple(sorted({str(name) for record in seam_weights for name in record}))
    if not groups:
        raise ValueError("seam has no deform groups")
    exact_boundary: list[dict[str, float]] = []
    vectors = []
    for index, record in enumerate(seam_weights):
        cleaned = {str(name): _finite(value, f"seam weight {index}") for name, value in record.items() if float(value) > 0.0}
        if not cleaned or any(value < 0.0 for value in cleaned.values()):
            raise ValueError(f"invalid seam weights at {index}")
        exact_boundary.append(cleaned)
        vectors.append([cleaned.get(group, 0.0) for group in groups])
    solved, iterations, delta = _harmonic_vectors(
        vectors,
        len(groups),
        tolerance=tolerance,
        maximum_iterations=maximum_iterations,
    )
    result: list[dict[str, float]] = list(exact_boundary)
    for vector in solved[SEAM_COUNT:]:
        result.append(_top_four(dict(zip(groups, vector))))
    return WeightSolution(
        records=tuple(result),
        iterations=iterations,
        final_maximum_delta=delta,
        group_count_before_projection=len(groups),
        maximum_positive_influences_after_projection=max(
            len(record) for record in result[SEAM_COUNT:]
        ),
    )


def geometry_quality(
    positions: Sequence[Sequence[float]],
    faces: Sequence[Quad] | None = None,
) -> dict[str, float | int]:
    values = tuple(_v3(value, "position") for value in positions)
    if len(values) != TOTAL_PATCH_INCIDENT_VERTICES:
        raise ValueError("geometry quality requires all 774 incident positions")
    face_values = tuple(faces or build_quad_topology())
    areas = []
    edge_ratios = []
    for face in face_values:
        first, second, third, fourth = (values[index] for index in face)
        area = 0.5 * _length(_cross(_sub(second, first), _sub(third, first)))
        area += 0.5 * _length(_cross(_sub(third, first), _sub(fourth, first)))
        areas.append(area)
        lengths = [
            _length(_sub(values[second_index], values[first_index]))
            for first_index, second_index in zip(face, face[1:] + face[:1])
        ]
        minimum = min(lengths)
        edge_ratios.append(max(lengths) / minimum if minimum > 0.0 else math.inf)
    return {
        "face_count": len(face_values),
        "minimum_face_area_m2": min(areas),
        "degenerate_face_count_at_1e_10_m2": sum(area <= 1.0e-10 for area in areas),
        "maximum_quad_edge_ratio": max(edge_ratios),
    }


def contract_record() -> dict[str, object]:
    return {
        "method_id": METHOD_ID,
        "source_blend_sha256": SOURCE_BLEND_SHA256,
        "source_package_manifest_sha256": SOURCE_PACKAGE_MANIFEST_SHA256,
        "plan_sha256": PLAN_SHA256,
        "freeze_ledger_sha256": FREEZE_LEDGER_SHA256,
        "source_ledger_sha256": SOURCE_LEDGER_SHA256,
        "topology": topology_contract(),
        "candidate_parameters": [asdict(candidate) for candidate in CANDIDATES],
        "external_landmark_order": list(EXTERNAL_LANDMARK_ORDER),
        "maximum_feature_offset_m": MAXIMUM_FEATURE_OFFSET_M,
        "quality_construction": {
            "minimum_local_collar_extent_edge_fraction": MINIMUM_LOCAL_COLLAR_EXTENT_EDGE_FRACTION,
            "minimum_local_core_inset_edge_fraction": MINIMUM_LOCAL_CORE_INSET_EDGE_FRACTION,
            "transition_subedge_target_fraction": TRANSITION_SUBEDGE_TARGET_FRACTION,
            "fixed_boundary_harmonic_stabilization_iterations": CORE_QUALITY_STABILIZATION_ITERATIONS,
            "fixed_boundary_harmonic_stabilization_relaxation": CORE_QUALITY_STABILIZATION_RELAXATION,
            "acceptance_maximum_quad_edge_ratio": 3.0,
        },
        "copied_donor_interior_vertices": 0,
        "copied_donor_interior_faces": 0,
        "separate_anatomy_objects": 0,
        "boolean_used": False,
        "painted_substitute_used": False,
        "internal_organs_or_tracts": False,
        "runtime_activation_allowed": False,
        "owner_approval_claimed": False,
    }
