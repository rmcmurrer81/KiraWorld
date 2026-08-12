#!/usr/bin/env python3
"""R19 attempt 04: pelvis-curvature-following adult-surface probe.

This bounded worker abandons boundary-to-centroid geometry.  It groups the
reviewed 34-point BlackProject aperture into four anatomical perimeter arcs,
regularizes them through a narrow local-normal curvature-fitted transition band,
and fills the resulting simple inner contour with a distributed recursively
refined harmonic/Coons-like field.  Base depth comes from a quadratic fit to
the surrounding torso's geodesic neighbor rings; bounded local external
landmark relief is applied only inside the normalized contour.

All earlier attempts remain immutable.  No source-interior adult-patch vertex,
face, coordinate, or weight is used.  The result is private, inactive,
unassigned, unpublished, and never runtime eligible without later review.
"""

from __future__ import annotations

from collections import defaultdict, deque
import hashlib
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from mathutils.kdtree import KDTree


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_build_kira_r19_blackproject_radial_patch_probe as base_worker  # noqa: E402
import blender_build_kira_r19_blackproject_radial_patch_probe_attempt_02 as bounded_worker  # noqa: E402


OUTPUT_REL = Path(
    "RecoverySprint/continuation_20260802/"
    "r19_blackproject_curvature_patch/attempt_04"
)
R9B_EVIDENCE_REL = Path(
    "Avatar/private_owner_review/kira_temporary_functional_body_20260730/"
    "kira_tfb_blackproject_r9b_20260730_072700/BUILD_EVIDENCE.json"
)
R9B_EVIDENCE_SHA256 = "79741bb5dfec080c523ae57c875fa95ca8ff91c77342406ffb11ce8506137d42"
EXPECTED_SEAM_COUNT = 34
CAP_REFINEMENT_LEVELS = 2
ORIGINAL_RENDER_PROBE_SET = base_worker.render_probe_set


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_boundary_cycle(
    source_patch: bpy.types.Object,
    cycle: list[int],
) -> list[int]:
    """Return the stable reviewed physical perimeter orientation.

    The earlier JSON inspection file listed boundary vertices by source index,
    not by edge traversal.  The live mesh cycle is a simple anatomical
    perimeter: max-X at 1, anterior midline near 5, min-X at 9, posterior-left
    at 20, and posterior-right at 24.
    """

    candidates: list[tuple[float, list[int], list[Vector]]] = []
    for orientation in (list(cycle), list(reversed(cycle))):
        points = [
            source_patch.matrix_world @ source_patch.data.vertices[index].co
            for index in orientation
        ]
        max_x_index = max(range(len(points)), key=lambda index: points[index].x)
        start = (max_x_index - 1) % len(points)
        ordered = orientation[start:] + orientation[:start]
        ordered_points = [
            source_patch.matrix_world @ source_patch.data.vertices[index].co
            for index in ordered
        ]
        minimum_x = min(point.x for point in ordered_points)
        minimum_y = min(point.y for point in ordered_points)
        score = (
            abs(ordered_points[1].x - max(point.x for point in ordered_points))
            + abs(ordered_points[5].x)
            + abs(ordered_points[5].y - minimum_y)
            + abs(ordered_points[9].x - minimum_x)
        )
        candidates.append((score, ordered, ordered_points))
    valid = [
        item
        for item in candidates
        if item[2][1].x > 0.05
        and abs(item[2][5].x) < 0.003
        and item[2][9].x < -0.05
    ]
    if valid:
        return min(valid, key=lambda item: item[0])[1]
    diagnostic = [
        {
            "score": item[0],
            "p1": base_worker.vec_record(item[2][1]),
            "p5": base_worker.vec_record(item[2][5]),
            "p9": base_worker.vec_record(item[2][9]),
        }
        for item in candidates
    ]
    raise ValueError(
        "could not recover the reviewed 34-point anatomical seam grouping: "
        f"{diagnostic}"
    )


def solve_linear_system(matrix: list[list[float]], values: list[float]) -> list[float]:
    n = len(values)
    augmented = [list(matrix[row]) + [float(values[row])] for row in range(n)]
    for column in range(n):
        pivot = max(range(column, n), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1.0e-12:
            raise ValueError("surrounding-body curvature fit is singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(n):
            if row == column:
                continue
            factor = augmented[row][column]
            if abs(factor) <= 1.0e-18:
                continue
            augmented[row] = [
                current - factor * pivot_value
                for current, pivot_value in zip(augmented[row], augmented[column])
            ]
    return [augmented[row][-1] for row in range(n)]


def quadratic_basis(u: float, v: float, u_scale: float, v_scale: float) -> list[float]:
    normalized_u = u / u_scale
    normalized_v = v / v_scale
    return [
        1.0,
        normalized_u,
        normalized_v,
        normalized_u * normalized_u,
        normalized_u * normalized_v,
        normalized_v * normalized_v,
    ]


def fit_surrounding_curvature(
    torso: bpy.types.Object,
    boundary_world: list[Vector],
    center: Vector,
    lateral: Vector,
    longitudinal: Vector,
    outward: Vector,
) -> tuple[list[float], dict[str, object]]:
    torso_world = [torso.matrix_world @ vertex.co for vertex in torso.data.vertices]
    tree = KDTree(len(torso_world))
    for index, point in enumerate(torso_world):
        tree.insert(point, index)
    tree.balance()
    mapped: list[int] = []
    distances: list[float] = []
    for point in boundary_world:
        _nearest, index, distance = tree.find(point)
        mapped.append(int(index))
        distances.append(float(distance))
    if len(set(mapped)) != EXPECTED_SEAM_COUNT or max(distances) > 1.0e-8:
        raise ValueError("torso does not expose the exact reviewed adult aperture")

    adjacency: list[set[int]] = [set() for _vertex in torso.data.vertices]
    for edge in torso.data.edges:
        first, second = map(int, edge.vertices)
        adjacency[first].add(second)
        adjacency[second].add(first)
    depth: dict[int, int] = {index: 0 for index in mapped}
    todo = deque(mapped)
    while todo:
        current = todo.popleft()
        if depth[current] >= 4:
            continue
        for neighbor in adjacency[current]:
            if neighbor not in depth:
                depth[neighbor] = depth[current] + 1
                todo.append(neighbor)
    samples: list[tuple[float, float, float, float, int]] = []
    for index, geodesic_depth in depth.items():
        point = torso_world[index]
        offset = point - center
        u = float(offset.dot(lateral))
        v = float(offset.dot(longitudinal))
        w = float(offset.dot(outward))
        # Neighbor rings, rather than the sawtooth aperture itself, dominate
        # the fitted continuation. Boundary points remain a light constraint.
        weight = 0.35 if geodesic_depth == 0 else 1.0 / float(geodesic_depth)
        samples.append((u, v, w, weight, geodesic_depth))
    u_scale = max(max(abs(sample[0]) for sample in samples), 0.05)
    v_scale = max(max(abs(sample[1]) for sample in samples), 0.08)
    normal = [[0.0 for _column in range(6)] for _row in range(6)]
    rhs = [0.0 for _row in range(6)]
    for u, v, w, weight, _depth in samples:
        basis = quadratic_basis(u, v, u_scale, v_scale)
        for row in range(6):
            rhs[row] += weight * basis[row] * w
            for column in range(6):
                normal[row][column] += weight * basis[row] * basis[column]
    ridge = max(sum(normal[row][row] for row in range(6)) * 1.0e-10, 1.0e-12)
    for index in range(6):
        normal[index][index] += ridge
    coefficients = solve_linear_system(normal, rhs)

    residuals = []
    depth_histogram: defaultdict[str, int] = defaultdict(int)
    for u, v, w, _weight, geodesic_depth in samples:
        predicted = sum(
            coefficient * value
            for coefficient, value in zip(
                coefficients,
                quadratic_basis(u, v, u_scale, v_scale),
            )
        )
        residuals.append(predicted - w)
        depth_histogram[str(geodesic_depth)] += 1
    return coefficients, {
        "method": "weighted_quadratic_fit_to_torso_geodesic_neighbor_rings",
        "mapped_boundary_vertex_count": len(mapped),
        "maximum_boundary_to_torso_match_distance_m": max(distances),
        "geodesic_ring_depth": 4,
        "sample_count": len(samples),
        "sample_depth_histogram": dict(sorted(depth_histogram.items())),
        "boundary_sample_weight": 0.35,
        "neighbor_weight": "1/geodesic_depth",
        "u_scale_m": u_scale,
        "v_scale_m": v_scale,
        "coefficients_w_m": coefficients,
        "residual_rms_m": math.sqrt(
            sum(value * value for value in residuals) / len(residuals)
        ),
        "residual_maximum_absolute_m": max(abs(value) for value in residuals),
    }


def evaluate_curvature(
    u: float,
    v: float,
    coefficients: list[float],
    fit: dict[str, object],
) -> float:
    return sum(
        coefficient * value
        for coefficient, value in zip(
            coefficients,
            quadratic_basis(
                u,
                v,
                float(fit["u_scale_m"]),
                float(fit["v_scale_m"]),
            ),
        )
    )


def segment_distance_2d(
    point: tuple[float, float],
    first: tuple[float, float],
    second: tuple[float, float],
) -> float:
    dx = second[0] - first[0]
    dy = second[1] - first[1]
    denominator = dx * dx + dy * dy
    if denominator <= 1.0e-18:
        return math.hypot(point[0] - first[0], point[1] - first[1])
    amount = max(
        0.0,
        min(
            1.0,
            ((point[0] - first[0]) * dx + (point[1] - first[1]) * dy)
            / denominator,
        ),
    )
    closest = (first[0] + amount * dx, first[1] + amount * dy)
    return math.hypot(point[0] - closest[0], point[1] - closest[1])


def polygon_self_crossings(points: list[tuple[float, float]]) -> list[list[int]]:
    def orientation(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def crosses(a, b, c, d):
        return (
            orientation(a, b, c) * orientation(a, b, d) < 0.0
            and orientation(c, d, a) * orientation(c, d, b) < 0.0
        )

    result = []
    count = len(points)
    for first in range(count):
        for second in range(first + 1, count):
            if second in {first, (first + 1) % count, (first - 1) % count}:
                continue
            if first == 0 and second == count - 1:
                continue
            if crosses(
                points[first],
                points[(first + 1) % count],
                points[second],
                points[(second + 1) % count],
            ):
                result.append([first, second])
    return result


def point_inside_polygon(
    point: tuple[float, float],
    polygon: list[tuple[float, float]],
) -> bool:
    inside = False
    previous = polygon[-1]
    for current in polygon:
        if (current[1] > point[1]) != (previous[1] > point[1]):
            crossing_x = (
                (previous[0] - current[0])
                * (point[1] - current[1])
                / (previous[1] - current[1])
                + current[0]
            )
            if point[0] < crossing_x:
                inside = not inside
        previous = current
    return inside


def locally_inset_contour(
    boundary: list[tuple[float, float]],
) -> tuple[list[tuple[float, float]], dict[str, object]]:
    """Offset each seam point along its local 2-D inward bisector.

    This is deliberately not scaling toward a centroid.  Distances are
    bounded by anatomical arc: superior, left/right lateral, and the narrow
    posterior/inferior return.
    """

    area = 0.5 * sum(
        first[0] * second[1] - second[0] * first[1]
        for first, second in zip(boundary, boundary[1:] + boundary[:1])
    )
    orientation = 1.0 if area > 0.0 else -1.0
    result = []
    distances = []
    for index, current in enumerate(boundary):
        previous = boundary[(index - 1) % len(boundary)]
        following = boundary[(index + 1) % len(boundary)]
        incoming = Vector((
            current[0] - previous[0],
            current[1] - previous[1],
        )).normalized()
        outgoing = Vector((
            following[0] - current[0],
            following[1] - current[1],
        )).normalized()
        first_normal = Vector((-incoming.y, incoming.x)) * orientation
        second_normal = Vector((-outgoing.y, outgoing.x)) * orientation
        bisector = first_normal + second_normal
        if bisector.length <= 1.0e-8:
            bisector = first_normal
        bisector.normalize()
        if 1 <= index <= 9:
            requested = 0.0040
            arc = "superior"
        elif 20 <= index <= 24:
            requested = 0.0016
            arc = "inferior_posterior"
        else:
            requested = 0.0030
            arc = "lateral"
        local_edge_limit = 0.30 * min(
            math.hypot(current[0] - previous[0], current[1] - previous[1]),
            math.hypot(following[0] - current[0], following[1] - current[1]),
        )
        distance = min(requested, local_edge_limit)
        candidate = (
            current[0] + bisector.x * distance,
            current[1] + bisector.y * distance,
        )
        # Acute corners can overshoot. Reduce only that local displacement
        # until the new vertex is demonstrably inside the exact seam polygon.
        reductions = 0
        while not point_inside_polygon(candidate, boundary) and reductions < 8:
            distance *= 0.5
            candidate = (
                current[0] + bisector.x * distance,
                current[1] + bisector.y * distance,
            )
            reductions += 1
        if not point_inside_polygon(candidate, boundary):
            raise ValueError(f"could not inset seam vertex {index} inside its local arc")
        result.append(candidate)
        distances.append(
            {
                "index": index,
                "arc": arc,
                "requested_m": requested,
                "applied_m": distance,
                "reductions": reductions,
            }
        )
    crossings = polygon_self_crossings(result)
    if crossings:
        raise ValueError(f"local inward-offset contour self-crosses: {crossings}")
    return result, {
        "method": "per_vertex_local_inward_bisector_offset",
        "signed_projected_area_m2": area,
        "orientation": "counterclockwise" if area > 0.0 else "clockwise",
        "distances": distances,
        "projected_self_crossings": crossings,
        "all_vertices_inside_exact_seam_polygon": all(
            point_inside_polygon(point, boundary) for point in result
        ),
        "centroid_scaling_used": False,
    }


def inverse_distance_boundary_weights(
    uv: tuple[float, float],
    boundary_uv: list[tuple[float, float]],
    boundary_weights: list[dict[str, float]],
) -> dict[str, float]:
    totals: defaultdict[str, float] = defaultdict(float)
    denominator = 0.0
    for point, weights in zip(boundary_uv, boundary_weights):
        distance_squared = max(
            (uv[0] - point[0]) ** 2 + (uv[1] - point[1]) ** 2,
            1.0e-10,
        )
        influence = 1.0 / distance_squared
        denominator += influence
        for name, value in weights.items():
            totals[name] += influence * value
    return base_worker.normalized_top_four(
        {name: value / denominator for name, value in totals.items()}
    )


def make_curvature_patch(
    source_patch: bpy.types.Object,
    ordered_cycle: list[int],
    collection: bpy.types.Collection,
) -> tuple[bpy.types.Object, dict[str, object]]:
    cycle = canonical_boundary_cycle(source_patch, ordered_cycle)
    source_matrix = source_patch.matrix_world.copy()
    source_inverse = source_matrix.inverted()
    boundary_world = [
        source_matrix @ source_patch.data.vertices[index].co for index in cycle
    ]
    boundary_weights = [
        base_worker.source_vertex_weights(source_patch, index) for index in cycle
    ]
    center = sum(boundary_world, Vector((0.0, 0.0, 0.0))) / len(boundary_world)
    lateral = Vector((1.0, 0.0, 0.0))
    longitudinal = base_worker.boundary_long_axis(boundary_world)
    outward = -(lateral.cross(longitudinal)).normalized()
    if outward.y > 0.0:
        outward.negate()

    torso = next(
        (
            obj
            for obj in collection.objects
            if obj.type == "MESH" and obj.data.name == "Ariel_Mesh_Torso_0"
        ),
        None,
    )
    if torso is None:
        raise ValueError("surrounding torso mesh is unavailable for curvature fit")
    coefficients, curvature_fit = fit_surrounding_curvature(
        torso,
        boundary_world,
        center,
        lateral,
        longitudinal,
        outward,
    )

    boundary_uv = [
        (
            float((point - center).dot(lateral)),
            float((point - center).dot(longitudinal)),
        )
        for point in boundary_world
    ]
    vertices_world = [point.copy() for point in boundary_world]
    vertex_uv = list(boundary_uv)
    weight_records = [dict(record) for record in boundary_weights]
    exact_boundary_crossings = polygon_self_crossings(boundary_uv)
    if exact_boundary_crossings:
        raise ValueError(
            "live edge-ordered source aperture is not a simple projected contour: "
            f"{exact_boundary_crossings}"
        )
    inner_uv, inset_record = locally_inset_contour(boundary_uv)
    inner_loop = []
    boundary_mean_weights = base_worker.weighted_mean(boundary_weights)
    for index, (u, v) in enumerate(inner_uv):
        w = evaluate_curvature(u, v, coefficients, curvature_fit)
        world = center + lateral * u + longitudinal * v + outward * w
        inner_index = len(vertices_world)
        vertices_world.append(world)
        vertex_uv.append((u, v))
        # The narrow transition stays mostly associated with its matching seam
        # vertex while softly approaching the boundary-wide pelvic mean.
        weight_records.append(
            base_worker.blended_weights(
                boundary_weights[index],
                boundary_mean_weights,
                0.82,
            )
        )
        inner_loop.append(inner_index)

    arc_records: dict[str, object] = {
        "superior_anterior": {
            "cycle_indices_inclusive": list(range(1, 10)),
            "corner_indices": [1, 9],
        },
        "left_lateral_inferior": {
            "cycle_indices_inclusive": list(range(9, 21)),
            "corner_indices": [9, 20],
        },
        "inferior_posterior": {
            "cycle_indices_inclusive": list(range(20, 25)),
            "corner_indices": [20, 24],
        },
        "right_lateral_superior": {
            "cycle_indices_inclusive": list(range(24, 34)) + [0, 1],
            "corner_indices": [24, 1],
        },
    }
    faces: list[tuple[int, ...]] = [
        (
            index,
            (index + 1) % EXPECTED_SEAM_COUNT,
            inner_loop[(index + 1) % EXPECTED_SEAM_COUNT],
            inner_loop[index],
        )
        for index in range(EXPECTED_SEAM_COUNT)
    ]

    cap_vectors = [Vector((u, v, 0.0)) for u, v in inner_uv]
    coarse_cap = tessellate_polygon([cap_vectors])
    if len(coarse_cap) != len(inner_loop) - 2:
        raise ValueError(
            "inner contour tessellation did not produce a simple disk: "
            f"triangles={len(coarse_cap)} expected={len(inner_loop) - 2}"
        )
    coarse_triangles: list[tuple[int, int, int]] = []
    for triangle in coarse_cap:
        indices = []
        for vector in triangle:
            if isinstance(vector, int):
                match = int(vector)
            else:
                match = min(
                    range(len(inner_uv)),
                    key=lambda index: math.hypot(
                        float(vector.x) - inner_uv[index][0],
                        float(vector.y) - inner_uv[index][1],
                    ),
                )
                if math.hypot(
                    float(vector.x) - inner_uv[match][0],
                    float(vector.y) - inner_uv[match][1],
                ) > 1.0e-8:
                    raise ValueError(
                        "could not bind cap tessellation to the inner contour"
                    )
            indices.append(inner_loop[match])
        coarse_triangles.append(tuple(indices))

    u_values = [uv[0] for uv in inner_uv]
    v_values = [uv[1] for uv in inner_uv]
    u_center = (min(u_values) + max(u_values)) * 0.5
    v_center = (min(v_values) + max(v_values)) * 0.5
    u_half = max((max(u_values) - min(u_values)) * 0.5, 1.0e-6)
    v_half = max((max(v_values) - min(v_values)) * 0.5, 1.0e-6)
    relief_values = []

    triangles = coarse_triangles
    refinement_vertices_by_level = []
    for _level in range(CAP_REFINEMENT_LEVELS):
        refined: list[tuple[int, int, int]] = []
        level_vertices = []
        for first, second, third in triangles:
            u = (
                vertex_uv[first][0] + vertex_uv[second][0] + vertex_uv[third][0]
            ) / 3.0
            v = (
                vertex_uv[first][1] + vertex_uv[second][1] + vertex_uv[third][1]
            ) / 3.0
            distance_to_boundary = min(
                segment_distance_2d(
                    (u, v),
                    inner_uv[index],
                    inner_uv[(index + 1) % len(inner_uv)],
                )
                for index in range(len(inner_uv))
            )
            fade_raw = max(0.0, min(1.0, distance_to_boundary / 0.012))
            fade = fade_raw * fade_raw * (3.0 - 2.0 * fade_raw)
            normalized_u = (u - u_center) / u_half
            normalized_v = (v - v_center) / v_half
            relief, _terms = base_worker.landmark_relief(
                normalized_u,
                normalized_v,
            )
            relief *= fade
            w = evaluate_curvature(u, v, coefficients, curvature_fit) + relief
            world = center + lateral * u + longitudinal * v + outward * w
            middle = len(vertices_world)
            vertices_world.append(world)
            vertex_uv.append((u, v))
            weight_records.append(
                inverse_distance_boundary_weights(
                    (u, v),
                    boundary_uv,
                    boundary_weights,
                )
            )
            relief_values.append(relief)
            level_vertices.append(middle)
            refined.extend(
                (
                    (first, second, middle),
                    (second, third, middle),
                    (third, first, middle),
                )
            )
        refinement_vertices_by_level.append(level_vertices)
        triangles = refined
    faces.extend(triangles)

    local_vertices = [source_inverse @ world for world in vertices_world]
    # Restore every seam coordinate from the exact source-local value after
    # the float-space curvature calculations.
    for index, source_index in enumerate(cycle):
        local_vertices[index] = source_patch.data.vertices[source_index].co.copy()
    mesh = bpy.data.meshes.new("Kira_R19_Curvature_Following_Adult_Surface_Mesh")
    mesh.from_pydata([tuple(point) for point in local_vertices], [], faces)
    mesh.validate(verbose=True)
    mesh.update()
    patch = bpy.data.objects.new("Kira_R19_Curvature_Following_Adult_Surface", mesh)
    collection.objects.link(patch)
    patch.matrix_world = source_matrix
    bm = bmesh.new()
    bm.from_mesh(patch.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(patch.data)
    bm.free()
    patch.data.update()
    for polygon in patch.data.polygons:
        polygon.use_smooth = True

    for group_name in sorted({name for weights in weight_records for name in weights}):
        patch.vertex_groups.new(name=group_name)
    for vertex_index, weights in enumerate(weight_records):
        for name, value in weights.items():
            patch.vertex_groups[name].add([vertex_index], value, "REPLACE")

    boundary_deltas = [
        (
            patch.matrix_world @ patch.data.vertices[index].co
            - boundary_world[index]
        ).length
        for index in range(EXPECTED_SEAM_COUNT)
    ]
    if max(boundary_deltas) > 1.0e-12:
        raise ValueError(
            "curvature patch did not preserve exact seam coordinates: "
            f"{max(boundary_deltas):.12g} m"
        )
    patch["private_review_only"] = True
    patch["owner_approved"] = False
    patch["runtime_assignment_allowed"] = False
    patch["source_interior_vertices_reused"] = 0
    patch["source_interior_faces_reused"] = 0
    patch["topology"] = (
        "local_inward_bisector_transition_plus_curvature_fitted_inner_contour_"
        "and_two_level_distributed_centroid_refinement"
    )
    face_histogram: defaultdict[str, int] = defaultdict(int)
    maximum_valence = 0
    audit_bm = bmesh.new()
    audit_bm.from_mesh(patch.data)
    for face in audit_bm.faces:
        face_histogram[str(len(face.verts))] += 1
    for vertex in audit_bm.verts:
        maximum_valence = max(maximum_valence, len(vertex.link_edges))
    audit_bm.free()
    return patch, {
        "attempt_04_curvature_following_repair": True,
        "source_boundary_cycle_vertex_count": EXPECTED_SEAM_COUNT,
        "maximum_exact_boundary_coordinate_delta_m": max(boundary_deltas),
        "source_interior_vertices_reused": 0,
        "source_interior_faces_reused": 0,
        "boundary_to_centroid_spokes_used": False,
        "central_single_pole_vertex_count": 0,
        "triangle_fan_or_poke_vertex_used": False,
        "anatomically_grouped_seam_arcs": arc_records,
        "exact_boundary_projected_self_crossings": exact_boundary_crossings,
        "local_inset": inset_record,
        "inner_contour_vertex_count": len(inner_loop),
        "inner_contour_projected_self_crossings": inset_record[
            "projected_self_crossings"
        ],
        "coarse_cap_triangle_count": len(coarse_triangles),
        "distributed_refinement_levels": CAP_REFINEMENT_LEVELS,
        "distributed_refinement_vertex_counts": [
            len(indices) for indices in refinement_vertices_by_level
        ],
        "new_vertex_count": len(patch.data.vertices),
        "new_face_count": len(patch.data.polygons),
        "structured_grid_generated_vertex_count": sum(
            len(indices) for indices in refinement_vertices_by_level
        ),
        "structured_grid_generated_face_count": len(triangles),
        "structured_grid_face_vertex_count_histogram": dict(
            sorted(face_histogram.items())
        ),
        "maximum_vertex_valence": maximum_valence,
        "curvature_fit": curvature_fit,
        "local_relief_range_m": [
            min(relief_values) if relief_values else 0.0,
            max(relief_values) if relief_values else 0.0,
        ],
        "weight_transfer": {
            "outer_seam": "normalized exact boundary weights",
            "transition_contour": "normalized paired boundary means",
            "refined_interior": "normalized inverse-UV-distance boundary interpolation",
            "maximum_influences": 4,
            "source_interior_weights_used": False,
        },
        "boundary_mean_world_m": base_worker.vec_record(center),
        "longitudinal_axis_world": base_worker.vec_record(longitudinal),
        "outward_axis_world": base_worker.vec_record(outward),
        "annular_quad_count": 0,
    }


def render_flat_and_wire_closeups(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    output_dir: Path,
    body: bpy.types.Object,
    patch_center: Vector,
) -> dict[str, str]:
    renders = ORIGINAL_RENDER_PROBE_SET(
        scene,
        camera,
        output_dir,
        body,
        patch_center,
    )
    shading = scene.display.shading
    original = {
        "type": shading.type,
        "light": shading.light,
        "color_type": shading.color_type,
        "single_color": tuple(shading.single_color),
        "show_shadows": shading.show_shadows,
        "show_cavity": shading.show_cavity,
    }
    close_views = {
        "flat_patch_front": (
            Vector((patch_center.x, patch_center.y - 1.6, patch_center.z)),
            0.27,
        ),
        "flat_patch_three_quarter": (
            Vector((patch_center.x + 1.1, patch_center.y - 1.25, patch_center.z)),
            0.29,
        ),
        "flat_patch_side": (
            Vector((patch_center.x + 1.6, patch_center.y, patch_center.z)),
            0.27,
        ),
    }
    shading.type = "SOLID"
    shading.light = "FLAT"
    shading.color_type = "MATERIAL"
    shading.show_shadows = False
    shading.show_cavity = False
    for name, (location, scale) in close_views.items():
        path = output_dir / f"{name}.png"
        base_worker.render_view(
            scene,
            camera,
            path,
            location,
            patch_center,
            scale,
        )
        renders[name] = path.name

    shading.type = "WIREFRAME"
    shading.light = "FLAT"
    shading.color_type = "SINGLE"
    shading.single_color = (0.02, 0.62, 0.82)
    wire_views = {
        "wire_patch_front": close_views["flat_patch_front"],
        "wire_patch_three_quarter": close_views["flat_patch_three_quarter"],
        "wire_patch_side": close_views["flat_patch_side"],
    }
    for name, (location, scale) in wire_views.items():
        path = output_dir / f"{name}.png"
        base_worker.render_view(
            scene,
            camera,
            path,
            location,
            patch_center,
            scale,
        )
        renders[name] = path.name

    shading.type = original["type"]
    shading.light = original["light"]
    shading.color_type = original["color_type"]
    shading.single_color = original["single_color"]
    shading.show_shadows = original["show_shadows"]
    shading.show_cavity = original["show_cavity"]
    return renders


def boundary_multiset(topology: dict[str, object]) -> list[int]:
    return sorted(
        int(record["vertex_count"])
        for record in topology.get("boundary_parts", [])
    )


def finalize_attempt_04() -> None:
    output_dir = PROJECT_ROOT / OUTPUT_REL
    evidence_path = output_dir / "BUILD_EVIDENCE.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    r9b_path = PROJECT_ROOT / R9B_EVIDENCE_REL
    if sha256_file(r9b_path) != R9B_EVIDENCE_SHA256:
        raise ValueError("sealed R9b topology baseline hash mismatch")
    r9b = json.loads(r9b_path.read_text(encoding="utf-8"))
    expected_multiset = boundary_multiset(r9b["topology_author_audit"])
    observed_multiset = boundary_multiset(evidence["primary_surface_topology"])
    join = evidence["primary_surface_join"]
    localized = evidence["intersection_localization"]
    gates = {
        "exactly_34_seam_merges": int(join["boundary_vertices_merged"]) == 34,
        "one_connected_primary_component": int(
            evidence["primary_surface_topology"]["connected_components"]
        )
        == 1,
        "zero_new_patch_or_seam_boundary_edges": int(
            join["post_weld_topology_hard_gate"]["new_patch_boundary_edge_count"]
        )
        == 0,
        "zero_patch_related_exact_intersections": int(
            localized["new_patch_related_genuine_pair_count"]
        )
        == 0,
        "inherited_boundary_multiset_exactly_unchanged": (
            observed_multiset == expected_multiset
            and int(evidence["primary_surface_topology"]["boundary_edge_count"])
            == 330
            and len(observed_multiset) == 23
        ),
        "new_patch_prejoin_exact_intersections_zero": int(
            evidence["patch_exact_nonadjacent_intersection_audit"][
                "exact_genuine_penetration_pair_count"
            ]
        )
        == 0,
        "zero_source_interior_geometry_reused": (
            int(evidence["radial_patch_authoring"]["source_interior_vertices_reused"])
            == 0
            and int(evidence["radial_patch_authoring"]["source_interior_faces_reused"])
            == 0
        ),
        "boundary_to_centroid_spokes_absent": evidence["radial_patch_authoring"][
            "boundary_to_centroid_spokes_used"
        ]
        is False,
        "flat_closeups_present": all(
            name in evidence["review_renders"]
            for name in (
                "flat_patch_front",
                "flat_patch_three_quarter",
                "flat_patch_side",
            )
        ),
        "wire_closeups_present": all(
            name in evidence["review_renders"]
            for name in (
                "wire_patch_front",
                "wire_patch_three_quarter",
                "wire_patch_side",
            )
        ),
    }
    if not all(gates.values()):
        failures = sorted(name for name, passed in gates.items() if not passed)
        raise ValueError(f"attempt-04 bounded structural gates failed: {failures}")

    this_path = Path(__file__).resolve()
    attempt_02_path = Path(bounded_worker.__file__).resolve()
    base_path = Path(base_worker.__file__).resolve()
    evidence["attempt"] = "attempt_04"
    evidence["status"] = (
        "PRIVATE_INACTIVE_CURVATURE_PATCH_STRUCTURAL_GATES_PASSED_"
        "REQUIRES_FLAT_WIRE_VISUAL_REVIEW"
    )
    evidence["attempt_04_corrected_bounded_gate"] = {
        **gates,
        "expected_inherited_boundary_loop_size_multiset": expected_multiset,
        "observed_inherited_boundary_loop_size_multiset": observed_multiset,
        "unresolved_foundation_property": (
            "330 supported BlackProject boundary edges in 23 loops remain "
            "unchanged outside this patch"
        ),
    }
    evidence["worker"] = {
        "path": str(this_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "sha256": sha256_file(this_path),
        "dependencies": [
            {
                "path": str(attempt_02_path.relative_to(PROJECT_ROOT)).replace(
                    "\\", "/"
                ),
                "sha256": sha256_file(attempt_02_path),
            },
            {
                "path": str(base_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "sha256": sha256_file(base_path),
            },
        ],
    }
    evidence["gates"].update(gates)
    evidence["gates"]["closed_primary_surface"] = False
    evidence["gates"]["visual_review"] = "PENDING"
    evidence["gates"]["owner_approval"] = "PENDING"
    evidence["gates"]["runtime_eligibility"] = False
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    report_path = output_dir / "REPORT.md"
    report_path.write_text(
        "\n".join(
            [
                "# R19 BlackProject pelvis-curvature patch — attempt 04",
                "",
                f"Status: `{evidence['status']}`",
                "",
                "- Attempts 01–03 remain unchanged.",
                "- Boundary-to-centroid spokes were abandoned.",
                "- The base field is fit from four surrounding torso geodesic rings.",
                "- The live edge-ordered seam is grouped into superior, left-lateral, posterior/inferior, and right-lateral arcs.",
                "- A narrow local inward-bisector band reaches a simple 34-point curvature-fitted inner contour without centroid scaling.",
                "- The inner contour uses distributed two-level refinement with no global pole or fan.",
                "- Exactly 34 seam vertices merged; the new patch contributes zero open edges and zero exact intersections.",
                "- The inherited BlackProject 330-edge/23-loop boundary multiset is unchanged.",
                "- Flat-material and wireframe front, three-quarter, and side closeups are included.",
                "- Structural passage does not imply visual or owner approval; the package must self-reject if an apron, plate, or seam remains visible.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    manifest_path = output_dir / "PACKAGE_MANIFEST.json"
    entries = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name.lower()):
        if path.is_file() and path != manifest_path:
            entries.append(
                {
                    "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "append_only_attempt": "attempt_04",
                "files_excluding_this_manifest": entries,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    output_dir = PROJECT_ROOT / OUTPUT_REL
    if output_dir.exists():
        raise FileExistsError("append-only attempt_04 already exists")
    bounded_worker.OUTPUT_REL = OUTPUT_REL
    bounded_worker.make_radial_patch_attempt_02 = make_curvature_patch
    base_worker.render_probe_set = render_flat_and_wire_closeups
    result = bounded_worker.main()
    finalize_attempt_04()
    print(
        json.dumps(
            {
                "ok": True,
                "attempt": "attempt_04",
                "output_dir": str(output_dir),
            },
            indent=2,
        )
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
