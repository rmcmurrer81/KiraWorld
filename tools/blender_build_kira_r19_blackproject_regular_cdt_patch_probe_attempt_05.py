#!/usr/bin/env python3
"""R19 attempt 05: regular-grid constrained-Delaunay pelvic surface probe.

This append-only bounded worker uses a materially different construction from
attempts 01-04.  It projects the exact live 34-vertex aperture seam to the
frontal X/Z plane, samples a regular interior grid, and triangulates the disk
with Blender's constrained 2-D Delaunay implementation.  Interior depth is a
cubic least-squares continuation of nearby base-torso vertices, with a
harmonic boundary-residual correction for C0 seam continuity and only smooth,
bounded external-landmark relief.  There is no centroid pole, recursive
centroid refinement, or source-patch interior reuse.

The result is private, inactive, unassigned, unpublished, and cannot become a
Kira candidate unless the append-only structural and independent visual gates
both pass.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import hashlib
import json
import math
import sys
import traceback
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
from mathutils.kdtree import KDTree


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_build_kira_r19_blackproject_radial_patch_probe as base_worker  # noqa: E402
import blender_build_kira_r19_blackproject_radial_patch_probe_attempt_02 as bounded_worker  # noqa: E402
import blender_build_kira_r19_blackproject_curvature_patch_probe_attempt_04 as curvature_worker  # noqa: E402


OUTPUT_REL = Path(
    "RecoverySprint/continuation_20260802/"
    "r19_blackproject_regular_cdt_patch/attempt_05"
)
R9B_EVIDENCE_REL = curvature_worker.R9B_EVIDENCE_REL
R9B_EVIDENCE_SHA256 = curvature_worker.R9B_EVIDENCE_SHA256
EXPECTED_SEAM_COUNT = 34
GRID_SPACING_M = 0.0055
GRID_BOUNDARY_CLEARANCE_M = 0.0014
FIT_GEODESIC_DEPTH = 8
HARMONIC_MAX_ITERATIONS = 4000
HARMONIC_TOLERANCE_M = 1.0e-10
ORIGINAL_RENDER_PROBE_SET = curvature_worker.ORIGINAL_RENDER_PROBE_SET


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cubic_basis(
    x: float,
    z: float,
    center_x: float,
    center_z: float,
    x_scale: float,
    z_scale: float,
) -> list[float]:
    u = (x - center_x) / x_scale
    v = (z - center_z) / z_scale
    return [
        1.0,
        u,
        v,
        u * u,
        u * v,
        v * v,
        u * u * u,
        u * u * v,
        u * v * v,
        v * v * v,
    ]


def evaluate_cubic(
    x: float,
    z: float,
    coefficients: list[float],
    fit: dict[str, object],
) -> float:
    return sum(
        coefficient * value
        for coefficient, value in zip(
            coefficients,
            cubic_basis(
                x,
                z,
                float(fit["center_x_m"]),
                float(fit["center_z_m"]),
                float(fit["x_scale_m"]),
                float(fit["z_scale_m"]),
            ),
        )
    )


def map_boundary_to_torso(
    torso: bpy.types.Object,
    boundary_world: list[Vector],
) -> tuple[list[int], list[float], list[Vector]]:
    torso_world = [torso.matrix_world @ vertex.co for vertex in torso.data.vertices]
    tree = KDTree(len(torso_world))
    for index, point in enumerate(torso_world):
        tree.insert(point, index)
    tree.balance()
    mapped = []
    distances = []
    for point in boundary_world:
        _nearest, index, distance = tree.find(point)
        mapped.append(int(index))
        distances.append(float(distance))
    if len(set(mapped)) != EXPECTED_SEAM_COUNT or max(distances) > 1.0e-8:
        raise ValueError("torso does not expose the exact reviewed 34-point aperture")
    return mapped, distances, torso_world


def fit_base_pelvic_cubic(
    torso: bpy.types.Object,
    boundary_world: list[Vector],
    boundary_xz: list[tuple[float, float]],
) -> tuple[list[float], dict[str, object], list[int]]:
    mapped, distances, torso_world = map_boundary_to_torso(torso, boundary_world)
    adjacency: list[set[int]] = [set() for _vertex in torso.data.vertices]
    for edge in torso.data.edges:
        first, second = map(int, edge.vertices)
        adjacency[first].add(second)
        adjacency[second].add(first)
    depths: dict[int, int] = {index: 0 for index in mapped}
    todo = deque(mapped)
    while todo:
        current = todo.popleft()
        if depths[current] >= FIT_GEODESIC_DEPTH:
            continue
        for neighbor in adjacency[current]:
            if neighbor not in depths:
                depths[neighbor] = depths[current] + 1
                todo.append(neighbor)

    center_x = sum(point.x for point in boundary_world) / len(boundary_world)
    center_z = sum(point.z for point in boundary_world) / len(boundary_world)
    x_scale = max(max(abs(point.x - center_x) for point in boundary_world), 0.05)
    z_scale = max(max(abs(point.z - center_z) for point in boundary_world), 0.05)
    samples: list[tuple[float, float, float, float, int, int]] = []
    projected_inside_excluded = 0
    for index, depth in sorted(depths.items()):
        if depth == 0:
            continue
        point = torso_world[index]
        xz = (float(point.x), float(point.z))
        if curvature_worker.point_inside_polygon(xz, boundary_xz):
            projected_inside_excluded += 1
            continue
        distance_to_seam = min(
            curvature_worker.segment_distance_2d(
                xz,
                boundary_xz[edge_index],
                boundary_xz[(edge_index + 1) % EXPECTED_SEAM_COUNT],
            )
            for edge_index in range(EXPECTED_SEAM_COUNT)
        )
        spatial = math.exp(-0.5 * (distance_to_seam / 0.065) ** 2)
        weight = spatial / (float(depth) ** 1.35)
        if weight > 1.0e-8:
            samples.append((point.x, point.z, point.y, weight, depth, index))
    if len(samples) < 80:
        raise ValueError(f"insufficient outside-aperture cubic samples: {len(samples)}")

    term_count = 10
    normal = [[0.0 for _column in range(term_count)] for _row in range(term_count)]
    rhs = [0.0 for _row in range(term_count)]
    for x, z, y, weight, _depth, _index in samples:
        basis = cubic_basis(x, z, center_x, center_z, x_scale, z_scale)
        for row in range(term_count):
            rhs[row] += weight * basis[row] * y
            for column in range(term_count):
                normal[row][column] += weight * basis[row] * basis[column]
    ridge = max(sum(normal[row][row] for row in range(term_count)) * 2.0e-9, 1.0e-11)
    for index in range(term_count):
        normal[index][index] += ridge
    coefficients = curvature_worker.solve_linear_system(normal, rhs)

    residuals = []
    depth_histogram: defaultdict[str, int] = defaultdict(int)
    for x, z, y, _weight, depth, _index in samples:
        residuals.append(
            evaluate_cubic(
                x,
                z,
                coefficients,
                {
                    "center_x_m": center_x,
                    "center_z_m": center_z,
                    "x_scale_m": x_scale,
                    "z_scale_m": z_scale,
                },
            )
            - y
        )
        depth_histogram[str(depth)] += 1
    sample_indices = [record[5] for record in samples]
    return coefficients, {
        "method": "weighted_cubic_least_squares_to_nearby_base_torso_vertices_outside_projected_aperture",
        "basis": ["1", "x", "z", "x2", "xz", "z2", "x3", "x2z", "xz2", "z3"],
        "mapped_boundary_vertex_count": len(mapped),
        "maximum_boundary_to_torso_match_distance_m": max(distances),
        "geodesic_ring_depth": FIT_GEODESIC_DEPTH,
        "sample_count": len(samples),
        "sample_depth_histogram": dict(sorted(depth_histogram.items())),
        "projected_inside_aperture_vertices_excluded": projected_inside_excluded,
        "boundary_vertices_used_as_fit_samples": 0,
        "source_adult_patch_interior_used": False,
        "center_x_m": center_x,
        "center_z_m": center_z,
        "x_scale_m": x_scale,
        "z_scale_m": z_scale,
        "ridge": ridge,
        "coefficients_y_m": coefficients,
        "residual_rms_m": math.sqrt(sum(value * value for value in residuals) / len(residuals)),
        "residual_maximum_absolute_m": max(abs(value) for value in residuals),
    }, sample_indices


def sample_regular_interior_grid(
    boundary_xz: list[tuple[float, float]],
) -> tuple[list[tuple[float, float]], dict[str, object]]:
    min_x = min(point[0] for point in boundary_xz)
    max_x = max(point[0] for point in boundary_xz)
    min_z = min(point[1] for point in boundary_xz)
    max_z = max(point[1] for point in boundary_xz)
    center_x = (min_x + max_x) * 0.5
    center_z = (min_z + max_z) * 0.5
    x_steps = int(math.ceil((max_x - min_x) / GRID_SPACING_M)) + 2
    z_steps = int(math.ceil((max_z - min_z) / GRID_SPACING_M)) + 2
    points = []
    candidates = 0
    excluded_near_boundary = 0
    for ix in range(-x_steps, x_steps + 1):
        x = center_x + ix * GRID_SPACING_M
        if x <= min_x or x >= max_x:
            continue
        for iz in range(-z_steps, z_steps + 1):
            z = center_z + iz * GRID_SPACING_M
            if z <= min_z or z >= max_z:
                continue
            candidates += 1
            point = (x, z)
            if not curvature_worker.point_inside_polygon(point, boundary_xz):
                continue
            distance = min(
                curvature_worker.segment_distance_2d(
                    point,
                    boundary_xz[index],
                    boundary_xz[(index + 1) % EXPECTED_SEAM_COUNT],
                )
                for index in range(EXPECTED_SEAM_COUNT)
            )
            if distance < GRID_BOUNDARY_CLEARANCE_M:
                excluded_near_boundary += 1
                continue
            points.append(point)
    if len(points) < 60:
        raise ValueError(f"regular projected grid is unexpectedly sparse: {len(points)}")
    return points, {
        "kind": "axis_aligned_regular_frontal_xz_grid",
        "spacing_m": GRID_SPACING_M,
        "boundary_clearance_m": GRID_BOUNDARY_CLEARANCE_M,
        "bounding_box_m": {"min_x": min_x, "max_x": max_x, "min_z": min_z, "max_z": max_z},
        "candidate_lattice_point_count": candidates,
        "accepted_strictly_inside_point_count": len(points),
        "excluded_near_boundary_count": excluded_near_boundary,
        "jitter_used": False,
    }


def constrained_delaunay_disk(
    boundary_xz: list[tuple[float, float]],
    grid_xz: list[tuple[float, float]],
) -> tuple[list[tuple[float, float]], list[tuple[int, int, int]], dict[str, object]]:
    input_points = boundary_xz + grid_xz
    constraint_edges = [
        (index, (index + 1) % EXPECTED_SEAM_COUNT)
        for index in range(EXPECTED_SEAM_COUNT)
    ]
    signed_area = 0.5 * sum(
        first[0] * second[1] - second[0] * first[1]
        for first, second in zip(boundary_xz, boundary_xz[1:] + boundary_xz[:1])
    )
    face = list(range(EXPECTED_SEAM_COUNT))
    if signed_area < 0.0:
        face.reverse()
    result = delaunay_2d_cdt(
        [Vector(point) for point in input_points],
        constraint_edges,
        [face],
        1,
        1.0e-10,
        True,
    )
    output_points_raw, output_edges, output_faces, original_vertices, _original_edges, _original_faces = result
    if not output_faces or any(len(face_record) != 3 for face_record in output_faces):
        raise ValueError("CDT inside-constraint output is not an all-triangle disk")

    input_to_output: dict[int, int] = {}
    for output_index, input_ids in enumerate(original_vertices):
        for input_index in input_ids:
            if input_index in input_to_output:
                raise ValueError(f"CDT input vertex {input_index} maps more than once")
            input_to_output[int(input_index)] = output_index
    missing_boundary = [
        index for index in range(EXPECTED_SEAM_COUNT) if index not in input_to_output
    ]
    if missing_boundary:
        raise ValueError(f"CDT omitted exact seam inputs: {missing_boundary}")
    seam_outputs = [input_to_output[index] for index in range(EXPECTED_SEAM_COUNT)]
    if len(set(seam_outputs)) != EXPECTED_SEAM_COUNT:
        raise ValueError("CDT merged exact seam inputs")
    output_order = seam_outputs + [
        index for index in range(len(output_points_raw)) if index not in set(seam_outputs)
    ]
    old_to_new = {old: new for new, old in enumerate(output_order)}
    output_points = []
    for new_index, old_index in enumerate(output_order):
        if new_index < EXPECTED_SEAM_COUNT:
            output_points.append(boundary_xz[new_index])
        else:
            point = output_points_raw[old_index]
            output_points.append((float(point.x), float(point.y)))
    triangles = [
        tuple(old_to_new[int(index)] for index in face_record)
        for face_record in output_faces
    ]

    edge_counts: defaultdict[tuple[int, int], int] = defaultdict(int)
    adjacency: list[set[int]] = [set() for _point in output_points]
    for triangle in triangles:
        for first, second in (
            (triangle[0], triangle[1]),
            (triangle[1], triangle[2]),
            (triangle[2], triangle[0]),
        ):
            key = tuple(sorted((first, second)))
            edge_counts[key] += 1
            adjacency[first].add(second)
            adjacency[second].add(first)
    boundary_edge_set = {
        tuple(sorted((index, (index + 1) % EXPECTED_SEAM_COUNT)))
        for index in range(EXPECTED_SEAM_COUNT)
    }
    observed_boundary = {edge for edge, count in edge_counts.items() if count == 1}
    if observed_boundary != boundary_edge_set:
        raise ValueError(
            "CDT disk boundary differs from exact seam constraints: "
            f"missing={sorted(boundary_edge_set-observed_boundary)} "
            f"extra={sorted(observed_boundary-boundary_edge_set)}"
        )
    boundary_neighbor_counts = [
        len({neighbor for neighbor in adjacency[index] if neighbor < EXPECTED_SEAM_COUNT})
        for index in range(EXPECTED_SEAM_COUNT, len(output_points))
    ]
    star_spoke_vertices = [
        EXPECTED_SEAM_COUNT + offset
        for offset, count in enumerate(boundary_neighbor_counts)
        if count >= 6
    ]
    if star_spoke_vertices:
        raise ValueError(f"CDT created boundary-star spoke vertices: {star_spoke_vertices}")
    return output_points, triangles, {
        "method": "mathutils.geometry.delaunay_2d_cdt",
        "output_type": 1,
        "output_type_meaning": "triangles_inside_constraints",
        "epsilon": 1.0e-10,
        "input_boundary_vertex_count": EXPECTED_SEAM_COUNT,
        "input_regular_grid_vertex_count": len(grid_xz),
        "output_vertex_count": len(output_points),
        "output_edge_count": len(output_edges),
        "output_triangle_count": len(triangles),
        "exact_constraint_boundary_edge_count": len(observed_boundary),
        "maximum_boundary_neighbors_of_any_interior_vertex": max(boundary_neighbor_counts, default=0),
        "boundary_star_spoke_vertex_count": len(star_spoke_vertices),
        "centroid_or_pole_vertex_inserted": False,
        "recursive_centroid_refinement_used": False,
    }


def harmonic_boundary_residuals(
    points: list[tuple[float, float]],
    triangles: list[tuple[int, int, int]],
    boundary_y: list[float],
    baseline_y: list[float],
) -> tuple[list[float], dict[str, object]]:
    adjacency: list[set[int]] = [set() for _point in points]
    for first, second, third in triangles:
        adjacency[first].update((second, third))
        adjacency[second].update((first, third))
        adjacency[third].update((first, second))
    boundary_residuals = [
        boundary_y[index] - baseline_y[index] for index in range(EXPECTED_SEAM_COUNT)
    ]
    values = [0.0] * len(points)
    values[:EXPECTED_SEAM_COUNT] = boundary_residuals
    for index in range(EXPECTED_SEAM_COUNT, len(points)):
        numerator = 0.0
        denominator = 0.0
        x, z = points[index]
        for boundary_index, residual in enumerate(boundary_residuals):
            bx, bz = points[boundary_index]
            influence = 1.0 / max((x - bx) ** 2 + (z - bz) ** 2, 1.0e-10)
            numerator += influence * residual
            denominator += influence
        values[index] = numerator / denominator

    converged_delta = float("inf")
    iteration_count = 0
    for iteration_count in range(1, HARMONIC_MAX_ITERATIONS + 1):
        previous = list(values)
        maximum_delta = 0.0
        for index in range(EXPECTED_SEAM_COUNT, len(points)):
            numerator = 0.0
            denominator = 0.0
            x, z = points[index]
            for neighbor in adjacency[index]:
                nx, nz = points[neighbor]
                edge_length = max(math.hypot(x - nx, z - nz), 1.0e-8)
                influence = 1.0 / edge_length
                numerator += influence * previous[neighbor]
                denominator += influence
            if denominator <= 0.0:
                raise ValueError(f"isolated CDT interior vertex {index}")
            values[index] = numerator / denominator
            maximum_delta = max(maximum_delta, abs(values[index] - previous[index]))
        converged_delta = maximum_delta
        if maximum_delta <= HARMONIC_TOLERANCE_M:
            break
    if converged_delta > HARMONIC_TOLERANCE_M:
        raise ValueError(
            "harmonic seam-residual solve did not converge: "
            f"iterations={iteration_count} delta={converged_delta}"
        )
    return values, {
        "method": "inverse_edge_length_graph_laplacian_on_CDT",
        "boundary_condition": "exact_seam_y_minus_cubic_baseline_y",
        "boundary_residual_range_m": [min(boundary_residuals), max(boundary_residuals)],
        "iteration_count": iteration_count,
        "maximum_final_iteration_delta_m": converged_delta,
        "tolerance_m": HARMONIC_TOLERANCE_M,
        "maximum_iterations": HARMONIC_MAX_ITERATIONS,
        "interior_residual_range_m": [
            min(values[EXPECTED_SEAM_COUNT:]),
            max(values[EXPECTED_SEAM_COUNT:]),
        ],
    }


def gaussian(value: float, center: float, sigma: float) -> float:
    return math.exp(-0.5 * ((value - center) / sigma) ** 2)


def smoothstep01(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def bounded_external_relief(
    x: float,
    z: float,
    boundary_xz: list[tuple[float, float]],
) -> tuple[float, dict[str, float], float]:
    min_x = min(point[0] for point in boundary_xz)
    max_x = max(point[0] for point in boundary_xz)
    min_z = min(point[1] for point in boundary_xz)
    max_z = max(point[1] for point in boundary_xz)
    center_x = (min_x + max_x) * 0.5
    half_x = max((max_x - min_x) * 0.5, 1.0e-6)
    nx = (x - center_x) / half_x
    inferior_progress = (max_z - z) / max(max_z - min_z, 1.0e-6)
    distance_to_boundary = min(
        curvature_worker.segment_distance_2d(
            (x, z),
            boundary_xz[index],
            boundary_xz[(index + 1) % EXPECTED_SEAM_COUNT],
        )
        for index in range(EXPECTED_SEAM_COUNT)
    )
    seam_fade = smoothstep01(distance_to_boundary / 0.011)
    posterior_fade = 1.0 - smoothstep01((inferior_progress - 0.82) / 0.14)
    terms = {
        "bilateral_outer_folds": 0.00120
        * (gaussian(nx, -0.31, 0.14) + gaussian(nx, 0.31, 0.14))
        * gaussian(inferior_progress, 0.48, 0.29),
        "bilateral_inner_folds": 0.00052
        * (gaussian(nx, -0.115, 0.060) + gaussian(nx, 0.115, 0.060))
        * gaussian(inferior_progress, 0.49, 0.23),
        "subtle_vestibule": -0.00024
        * gaussian(nx, 0.0, 0.13)
        * gaussian(inferior_progress, 0.53, 0.20),
        "small_superior_hood": 0.00042
        * gaussian(nx, 0.0, 0.105)
        * gaussian(inferior_progress, 0.25, 0.090),
        "shallow_urethral_recess": -0.00016
        * gaussian(nx, 0.0, 0.058)
        * gaussian(inferior_progress, 0.42, 0.055),
        "shallow_vaginal_recess": -0.00048
        * gaussian(nx, 0.0, 0.088)
        * gaussian(inferior_progress, 0.62, 0.095),
        "posterior_perineal_transition": 0.00016
        * gaussian(nx, 0.0, 0.18)
        * gaussian(inferior_progress, 0.76, 0.11),
    }
    fade = seam_fade * posterior_fade
    return sum(terms.values()) * fade, terms, fade


def nearby_weight_samples(
    torso: bpy.types.Object,
    sample_indices: list[int],
    boundary_xz: list[tuple[float, float]],
    boundary_weights: list[dict[str, float]],
) -> tuple[KDTree, list[dict[str, float]]]:
    records: list[tuple[Vector, dict[str, float]]] = []
    for index in sample_indices:
        point = torso.matrix_world @ torso.data.vertices[index].co
        records.append(
            (
                Vector((point.x, point.z, 0.0)),
                base_worker.source_vertex_weights(torso, index),
            )
        )
    for point, weights in zip(boundary_xz, boundary_weights):
        records.append((Vector((point[0], point[1], 0.0)), dict(weights)))
    tree = KDTree(len(records))
    weights_only = []
    for index, (point, weights) in enumerate(records):
        tree.insert(point, index)
        weights_only.append(weights)
    tree.balance()
    return tree, weights_only


def interpolate_nearby_weights(
    xz: tuple[float, float],
    tree: KDTree,
    records: list[dict[str, float]],
) -> dict[str, float]:
    totals: defaultdict[str, float] = defaultdict(float)
    denominator = 0.0
    for _point, index, distance in tree.find_n(Vector((xz[0], xz[1], 0.0)), 8):
        influence = 1.0 / max(float(distance) ** 2, 1.0e-10)
        denominator += influence
        for name, value in records[int(index)].items():
            totals[name] += influence * value
    if denominator <= 0.0:
        raise ValueError("no nearby base/seam weights found")
    return base_worker.normalized_top_four(
        {name: value / denominator for name, value in totals.items()}
    )


def make_regular_cdt_patch(
    source_patch: bpy.types.Object,
    ordered_cycle: list[int],
    collection: bpy.types.Collection,
) -> tuple[bpy.types.Object, dict[str, object]]:
    cycle = curvature_worker.canonical_boundary_cycle(source_patch, ordered_cycle)
    source_matrix = source_patch.matrix_world.copy()
    source_inverse = source_matrix.inverted()
    boundary_world = [
        source_matrix @ source_patch.data.vertices[index].co for index in cycle
    ]
    boundary_weights = [
        base_worker.source_vertex_weights(source_patch, index) for index in cycle
    ]
    boundary_xz = [(float(point.x), float(point.z)) for point in boundary_world]
    crossings = curvature_worker.polygon_self_crossings(boundary_xz)
    if crossings:
        raise ValueError(f"exact frontal X/Z seam projection self-crosses: {crossings}")
    torso = next(
        (
            obj
            for obj in collection.objects
            if obj.type == "MESH" and obj.data.name == "Ariel_Mesh_Torso_0"
        ),
        None,
    )
    if torso is None:
        raise ValueError("surrounding torso mesh is unavailable")
    coefficients, fit_record, fit_sample_indices = fit_base_pelvic_cubic(
        torso,
        boundary_world,
        boundary_xz,
    )
    grid_xz, grid_record = sample_regular_interior_grid(boundary_xz)
    points_xz, triangles, cdt_record = constrained_delaunay_disk(
        boundary_xz,
        grid_xz,
    )
    baseline_y = [
        evaluate_cubic(x, z, coefficients, fit_record) for x, z in points_xz
    ]
    boundary_y = [float(point.y) for point in boundary_world]
    residuals, residual_record = harmonic_boundary_residuals(
        points_xz,
        triangles,
        boundary_y,
        baseline_y,
    )
    weight_tree, nearby_weights = nearby_weight_samples(
        torso,
        fit_sample_indices,
        boundary_xz,
        boundary_weights,
    )

    vertices_world: list[Vector] = []
    weight_records: list[dict[str, float]] = []
    relief_values = []
    fade_values = []
    relief_term_ranges: defaultdict[str, list[float]] = defaultdict(list)
    for index, (x, z) in enumerate(points_xz):
        if index < EXPECTED_SEAM_COUNT:
            vertices_world.append(boundary_world[index].copy())
            weight_records.append(dict(boundary_weights[index]))
            continue
        outward_relief, terms, fade = bounded_external_relief(x, z, boundary_xz)
        # Frontal outward is negative world Y on this source.
        y = baseline_y[index] + residuals[index] - outward_relief
        vertices_world.append(Vector((x, y, z)))
        weight_records.append(
            interpolate_nearby_weights((x, z), weight_tree, nearby_weights)
        )
        relief_values.append(outward_relief)
        fade_values.append(fade)
        for name, value in terms.items():
            relief_term_ranges[name].append(value * fade)

    oriented_triangles = []
    reversed_face_count = 0
    for first, second, third in triangles:
        normal = (vertices_world[second] - vertices_world[first]).cross(
            vertices_world[third] - vertices_world[first]
        )
        if normal.y > 0.0:
            second, third = third, second
            reversed_face_count += 1
        oriented_triangles.append((first, second, third))

    local_vertices = [source_inverse @ point for point in vertices_world]
    for index, source_index in enumerate(cycle):
        local_vertices[index] = source_patch.data.vertices[source_index].co.copy()
    mesh = bpy.data.meshes.new("Kira_R19_Regular_CDT_Adult_Surface_Mesh")
    mesh.from_pydata([tuple(point) for point in local_vertices], [], oriented_triangles)
    mesh.validate(verbose=True)
    mesh.update()
    patch = bpy.data.objects.new("Kira_R19_Regular_CDT_Adult_Surface", mesh)
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

    group_names = sorted({name for weights in weight_records for name in weights})
    for group_name in group_names:
        patch.vertex_groups.new(name=group_name)
    for vertex_index, weights in enumerate(weight_records):
        normalized = base_worker.normalized_top_four(weights)
        for name, value in normalized.items():
            patch.vertex_groups[name].add([vertex_index], value, "REPLACE")

    boundary_deltas = [
        (
            patch.matrix_world @ patch.data.vertices[index].co - boundary_world[index]
        ).length
        for index in range(EXPECTED_SEAM_COUNT)
    ]
    if max(boundary_deltas) > 1.0e-12:
        raise ValueError(
            "regular CDT patch did not preserve exact seam coordinates: "
            f"{max(boundary_deltas):.12g} m"
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

    patch["private_review_only"] = True
    patch["owner_approved"] = False
    patch["runtime_assignment_allowed"] = False
    patch["source_interior_vertices_reused"] = 0
    patch["source_interior_faces_reused"] = 0
    patch["topology"] = "regular_xz_grid_constrained_delaunay_cubic_harmonic_surface"
    center = sum(boundary_world, Vector((0.0, 0.0, 0.0))) / len(boundary_world)
    return patch, {
        "attempt_05_regular_edge_flow_repair": True,
        "source_boundary_cycle_vertex_count": EXPECTED_SEAM_COUNT,
        "maximum_exact_boundary_coordinate_delta_m": max(boundary_deltas),
        "source_interior_vertices_reused": 0,
        "source_interior_faces_reused": 0,
        "projection_plane": "world_frontal_X_Z",
        "boundary_to_centroid_spokes_used": False,
        "central_single_pole_vertex_count": 0,
        "triangle_fan_or_poke_vertex_used": False,
        "recursive_centroid_refinement_used": False,
        "exact_boundary_projected_self_crossings": crossings,
        "regular_interior_grid": grid_record,
        "constrained_delaunay": cdt_record,
        "base_body_curvature_fit": fit_record,
        "harmonic_boundary_residual_correction": residual_record,
        "neutral_depth_equation": "cubic_base_body_y_fit_plus_harmonic_exact_seam_residual",
        "bounded_external_relief": {
            "direction": "negative_world_Y_is_outward",
            "interior_vertex_count": len(relief_values),
            "combined_outward_range_m": [min(relief_values), max(relief_values)],
            "seam_and_posterior_fade_range": [min(fade_values), max(fade_values)],
            "term_ranges_m_before_combination": {
                name: [min(values), max(values)]
                for name, values in sorted(relief_term_ranges.items())
            },
            "exact_seam_relief_m": 0.0,
        },
        "new_vertex_count": len(patch.data.vertices),
        "new_face_count": len(patch.data.polygons),
        "structured_grid_generated_vertex_count": len(grid_xz),
        "structured_grid_generated_face_count": len(patch.data.polygons),
        "structured_grid_face_vertex_count_histogram": dict(sorted(face_histogram.items())),
        "maximum_vertex_valence": maximum_valence,
        "weight_transfer": {
            "outer_seam": "normalized exact source seam weights",
            "interior": "inverse_squared_projected_distance blend of eight nearby base-torso/seam weight records",
            "maximum_influences": 4,
            "source_interior_weights_used": False,
        },
        "boundary_mean_world_m": base_worker.vec_record(center),
        "longitudinal_axis_world": [0.0, 0.0, -1.0],
        "outward_axis_world": [0.0, -1.0, 0.0],
        "annular_quad_count": 0,
        "face_orientation_reversals_before_recalc": reversed_face_count,
    }


def render_with_wire_overlays(
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
    original_shading = {
        "light": shading.light,
        "color_type": shading.color_type,
        "single_color": tuple(shading.single_color),
        "show_shadows": shading.show_shadows,
        "show_cavity": shading.show_cavity,
        "cavity_type": shading.cavity_type,
    }
    original_wire = bool(body.show_wire)
    original_all_edges = bool(body.show_all_edges)
    close_views = {
        "wire_overlay_front": (
            Vector((patch_center.x, patch_center.y - 1.6, patch_center.z)),
            0.245,
        ),
        "wire_overlay_three_quarter": (
            Vector((patch_center.x + 1.1, patch_center.y - 1.25, patch_center.z)),
            0.265,
        ),
        "wire_overlay_side": (
            Vector((patch_center.x + 1.6, patch_center.y, patch_center.z)),
            0.245,
        ),
    }
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_shadows = False
    shading.show_cavity = True
    shading.cavity_type = "BOTH"
    body.show_wire = True
    body.show_all_edges = True
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
    body.show_wire = original_wire
    body.show_all_edges = original_all_edges
    shading.light = original_shading["light"]
    shading.color_type = original_shading["color_type"]
    shading.single_color = original_shading["single_color"]
    shading.show_shadows = original_shading["show_shadows"]
    shading.show_cavity = original_shading["show_cavity"]
    shading.cavity_type = original_shading["cavity_type"]
    return renders


def boundary_multiset(topology: dict[str, object]) -> list[int]:
    return sorted(
        int(record["vertex_count"])
        for record in topology.get("boundary_parts", [])
    )


def write_manifest(output_dir: Path) -> Path:
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
                "append_only_attempt": "attempt_05",
                "files_excluding_this_manifest": entries,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest_path


def finalize_attempt_05() -> None:
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
    authored = evidence["radial_patch_authoring"]
    renders = evidence["review_renders"]
    gates = {
        "exactly_34_seam_merges": int(join["boundary_vertices_merged"]) == 34,
        "one_connected_primary_component": int(evidence["primary_surface_topology"]["connected_components"]) == 1,
        "zero_new_patch_or_seam_boundary_edges": int(join["post_weld_topology_hard_gate"]["new_patch_boundary_edge_count"]) == 0,
        "zero_patch_related_exact_intersections": int(localized["new_patch_related_genuine_pair_count"]) == 0,
        "inherited_boundary_multiset_exactly_unchanged": (
            observed_multiset == expected_multiset
            and int(evidence["primary_surface_topology"]["boundary_edge_count"]) == 330
            and len(observed_multiset) == 23
        ),
        "new_patch_prejoin_exact_intersections_zero": int(evidence["patch_exact_nonadjacent_intersection_audit"]["exact_genuine_penetration_pair_count"]) == 0,
        "zero_source_interior_geometry_reused": (
            int(authored["source_interior_vertices_reused"]) == 0
            and int(authored["source_interior_faces_reused"]) == 0
        ),
        "exact_frontal_xz_projection": authored["projection_plane"] == "world_frontal_X_Z",
        "regular_interior_grid_used": int(authored["regular_interior_grid"]["accepted_strictly_inside_point_count"]) >= 60,
        "blender_constrained_delaunay_used": authored["constrained_delaunay"]["method"] == "mathutils.geometry.delaunay_2d_cdt",
        "zero_center_fan_or_star_spokes": (
            authored["boundary_to_centroid_spokes_used"] is False
            and int(authored["central_single_pole_vertex_count"]) == 0
            and int(authored["constrained_delaunay"]["boundary_star_spoke_vertex_count"]) == 0
        ),
        "cubic_base_body_fit_used": int(authored["base_body_curvature_fit"]["sample_count"]) >= 80,
        "harmonic_exact_seam_residual_converged": float(authored["harmonic_boundary_residual_correction"]["maximum_final_iteration_delta_m"]) <= HARMONIC_TOLERANCE_M,
        "wire_overlay_closeups_present": all(
            name in renders
            for name in ("wire_overlay_front", "wire_overlay_three_quarter", "wire_overlay_side")
        ),
    }
    if not all(gates.values()):
        failures = sorted(name for name, passed in gates.items() if not passed)
        raise ValueError(f"attempt-05 bounded structural gates failed: {failures}")

    this_path = Path(__file__).resolve()
    dependency_paths = [
        Path(curvature_worker.__file__).resolve(),
        Path(bounded_worker.__file__).resolve(),
        Path(base_worker.__file__).resolve(),
    ]
    evidence["attempt"] = "attempt_05"
    evidence["status"] = "PRIVATE_INACTIVE_REGULAR_CDT_PATCH_STRUCTURAL_GATES_PASSED_REQUIRES_VISUAL_REVIEW"
    evidence["attempt_05_scoped_structural_gate"] = {
        **gates,
        "expected_inherited_boundary_loop_size_multiset": expected_multiset,
        "observed_inherited_boundary_loop_size_multiset": observed_multiset,
        "unresolved_foundation_property": "330 supported BlackProject boundary edges in 23 loops remain unchanged outside this patch",
    }
    evidence["worker"] = {
        "path": str(this_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "sha256": sha256_file(this_path),
        "dependencies": [
            {
                "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "sha256": sha256_file(path),
            }
            for path in dependency_paths
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
                "# R19 BlackProject regular constrained-Delaunay patch — attempt 05",
                "",
                f"Status: `{evidence['status']}`",
                "",
                "- Attempts 01–04 remain unchanged.",
                "- The exact 34-point seam was projected to frontal world X/Z and retained byte-close in 3-D.",
                "- A regular interior grid was triangulated with Blender's constrained 2-D Delaunay implementation.",
                "- Neutral Y depth uses a cubic least-squares fit to nearby base-torso vertices outside the projected aperture, plus a converged harmonic exact-seam residual.",
                "- Smooth bounded landmark fields are zero at the seam; no centroid pole, recursive centroid hierarchy, or source-patch interior was used.",
                "- Exactly 34 seam vertices merged; the new patch contributes zero open edges and zero exact intersections.",
                "- The inherited BlackProject 330-edge/23-loop boundary multiset is unchanged.",
                "- Studio front/three-quarter/side views and solid wire-overlay closeups are included.",
                "- Structural passage does not imply visual or owner approval; reject if any triangular outline, plate, accordion, seam, or star-spoke pattern remains visible.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_manifest(output_dir)


def preserve_failure(exc: BaseException) -> None:
    output_dir = PROJECT_ROOT / OUTPUT_REL
    output_dir.mkdir(parents=True, exist_ok=True)
    failure_path = output_dir / "FAILURE_EVIDENCE.json"
    if failure_path.exists():
        return
    source_path = PROJECT_ROOT / base_worker.SOURCE_REL
    failure_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "attempt": "attempt_05",
                "status": "FAILED_BEFORE_STRUCTURAL_ACCEPTANCE",
                "utc": datetime.now(timezone.utc).isoformat(),
                "exception_type": type(exc).__name__,
                "exception": str(exc),
                "traceback": traceback.format_exc(),
                "source": {
                    "path": str(base_worker.SOURCE_REL).replace("\\", "/"),
                    "sha256": sha256_file(source_path),
                },
                "worker": {
                    "path": str(Path(__file__).resolve().relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "sha256": sha256_file(Path(__file__).resolve()),
                },
                "scope": {
                    "private": True,
                    "inactive": True,
                    "runtime_files_modified": False,
                    "earlier_attempts_modified": False,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_manifest(output_dir)


def main() -> int:
    output_dir = PROJECT_ROOT / OUTPUT_REL
    if output_dir.exists():
        raise FileExistsError("append-only attempt_05 already exists")
    bounded_worker.OUTPUT_REL = OUTPUT_REL
    bounded_worker.make_radial_patch_attempt_02 = make_regular_cdt_patch
    base_worker.render_probe_set = render_with_wire_overlays
    try:
        result = bounded_worker.main()
        finalize_attempt_05()
    except BaseException as exc:
        preserve_failure(exc)
        raise
    print(json.dumps({"ok": True, "attempt": "attempt_05", "output_dir": str(output_dir)}, indent=2))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
