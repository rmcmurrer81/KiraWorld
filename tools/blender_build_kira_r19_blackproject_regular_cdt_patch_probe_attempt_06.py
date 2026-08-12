#!/usr/bin/env python3
"""R19 attempt 06: one localized C1/tangent-ring correction to attempt 05.

The regular X/Z grid and constrained-Delaunay topology are retained.  Only the
depth field is corrected: exact retained-torso vertex normals define a fixed
first interior tangent ring, then a graph-Laplacian fairing solves the remaining
interior relative to a two-ring cubic base-body fit.  Landmark relief is kept
away from the fixed tangent ring and made shallower laterally.  Explicit
temporary beveled curves provide genuine wire-overlay evidence.
"""

from __future__ import annotations

from collections import defaultdict
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


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_build_kira_r19_blackproject_radial_patch_probe as base_worker  # noqa: E402
import blender_build_kira_r19_blackproject_radial_patch_probe_attempt_02 as bounded_worker  # noqa: E402
import blender_build_kira_r19_blackproject_curvature_patch_probe_attempt_04 as curvature_worker  # noqa: E402
import blender_build_kira_r19_blackproject_regular_cdt_patch_probe_attempt_05 as attempt_05_worker  # noqa: E402


OUTPUT_REL = Path(
    "RecoverySprint/continuation_20260802/"
    "r19_blackproject_regular_cdt_patch/attempt_06"
)
R9B_EVIDENCE_REL = curvature_worker.R9B_EVIDENCE_REL
R9B_EVIDENCE_SHA256 = curvature_worker.R9B_EVIDENCE_SHA256
EXPECTED_SEAM_COUNT = 34
FIT_GEODESIC_DEPTH = 2
FAIRING_MAX_ITERATIONS = 5000
FAIRING_TOLERANCE_M = 1.0e-10
ORIGINAL_RENDER_PROBE_SET = curvature_worker.ORIGINAL_RENDER_PROBE_SET
LAST_AUTHORING_RECORD: dict[str, object] | None = None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def graph_adjacency(
    vertex_count: int,
    triangles: list[tuple[int, int, int]],
) -> list[set[int]]:
    adjacency = [set() for _index in range(vertex_count)]
    for first, second, third in triangles:
        adjacency[first].update((second, third))
        adjacency[second].update((first, third))
        adjacency[third].update((first, second))
    return adjacency


def retained_torso_boundary_normals(
    torso: bpy.types.Object,
    boundary_world: list[Vector],
) -> tuple[list[Vector], dict[str, object]]:
    mapped, distances, _torso_world = attempt_05_worker.map_boundary_to_torso(
        torso,
        boundary_world,
    )
    normal_matrix = torso.matrix_world.to_3x3().inverted().transposed()
    normals = []
    clamped_y_count = 0
    for index in mapped:
        normal = (normal_matrix @ torso.data.vertices[index].normal).normalized()
        # Only numerical near-tangencies are clamped. Direction is retained.
        if abs(normal.y) < 0.12:
            normal.y = math.copysign(0.12, normal.y if normal.y != 0.0 else -1.0)
            normal.normalize()
            clamped_y_count += 1
        normals.append(normal)
    return normals, {
        "source": "normals of retained Ariel_Mesh_Torso_0 faces at exact mapped seam vertices",
        "mapped_vertex_count": len(mapped),
        "maximum_mapping_distance_m": max(distances),
        "normal_transform": "inverse_transpose_object_matrix",
        "near_tangent_y_clamp_absolute_minimum": 0.12,
        "near_tangent_y_clamp_count": clamped_y_count,
    }


def fixed_first_tangent_ring(
    points_xz: list[tuple[float, float]],
    triangles: list[tuple[int, int, int]],
    boundary_world: list[Vector],
    boundary_normals: list[Vector],
) -> tuple[dict[int, float], dict[str, object]]:
    adjacency = graph_adjacency(len(points_xz), triangles)
    first_ring = sorted(
        {
            neighbor
            for boundary_index in range(EXPECTED_SEAM_COUNT)
            for neighbor in adjacency[boundary_index]
            if neighbor >= EXPECTED_SEAM_COUNT
        }
    )
    if not first_ring:
        raise ValueError("constrained Delaunay mesh has no first interior tangent ring")
    targets: dict[int, float] = {}
    contributor_counts = []
    unclamped_deltas = []
    clamped_deltas = []
    for index in first_ring:
        x, z = points_xz[index]
        boundary_neighbors = sorted(
            neighbor
            for neighbor in adjacency[index]
            if neighbor < EXPECTED_SEAM_COUNT
        )
        if not boundary_neighbors:
            raise ValueError(f"first-ring vertex {index} lacks a seam neighbor")
        numerator = 0.0
        denominator = 0.0
        for boundary_index in boundary_neighbors:
            boundary = boundary_world[boundary_index]
            normal = boundary_normals[boundary_index]
            dx = x - boundary.x
            dz = z - boundary.z
            tangent_delta = -(
                normal.x * dx + normal.z * dz
            ) / normal.y
            projected_distance = max(math.hypot(dx, dz), 1.0e-8)
            unclamped_deltas.append(tangent_delta)
            maximum_delta = max(0.006, 3.0 * projected_distance)
            tangent_delta = max(-maximum_delta, min(maximum_delta, tangent_delta))
            clamped_deltas.append(tangent_delta)
            influence = 1.0 / (projected_distance * projected_distance)
            numerator += influence * (boundary.y + tangent_delta)
            denominator += influence
        targets[index] = numerator / denominator
        contributor_counts.append(len(boundary_neighbors))
    return targets, {
        "method": "fixed_first_interior_ring_from_adjacent_retained_torso_vertex_normals",
        "first_ring_vertex_indices": first_ring,
        "first_ring_vertex_count": len(first_ring),
        "boundary_contributor_count_range": [min(contributor_counts), max(contributor_counts)],
        "unclamped_tangent_delta_range_m": [min(unclamped_deltas), max(unclamped_deltas)],
        "clamped_tangent_delta_range_m": [min(clamped_deltas), max(clamped_deltas)],
        "maximum_delta_rule": "max(0.006 m, 3 * projected seam distance)",
        "fixed_during_remaining_interior_fairing": True,
    }


def fair_remaining_interior(
    points_xz: list[tuple[float, float]],
    triangles: list[tuple[int, int, int]],
    baseline_y: list[float],
    boundary_world: list[Vector],
    tangent_targets: dict[int, float],
) -> tuple[list[float], dict[str, object]]:
    adjacency = graph_adjacency(len(points_xz), triangles)
    fixed: dict[int, float] = {
        index: boundary_world[index].y - baseline_y[index]
        for index in range(EXPECTED_SEAM_COUNT)
    }
    fixed.update(
        {
            index: target_y - baseline_y[index]
            for index, target_y in tangent_targets.items()
        }
    )
    values = [0.0] * len(points_xz)
    for index, value in fixed.items():
        values[index] = value
    fixed_indices = sorted(fixed)
    for index in range(len(points_xz)):
        if index in fixed:
            continue
        x, z = points_xz[index]
        numerator = 0.0
        denominator = 0.0
        for anchor in fixed_indices:
            ax, az = points_xz[anchor]
            influence = 1.0 / max((x - ax) ** 2 + (z - az) ** 2, 1.0e-10)
            numerator += influence * fixed[anchor]
            denominator += influence
        values[index] = numerator / denominator

    solved_indices = [index for index in range(len(points_xz)) if index not in fixed]
    final_delta = float("inf")
    iteration_count = 0
    for iteration_count in range(1, FAIRING_MAX_ITERATIONS + 1):
        previous = list(values)
        final_delta = 0.0
        for index in solved_indices:
            x, z = points_xz[index]
            numerator = 0.0
            denominator = 0.0
            for neighbor in adjacency[index]:
                nx, nz = points_xz[neighbor]
                influence = 1.0 / max(math.hypot(x - nx, z - nz), 1.0e-8)
                numerator += influence * previous[neighbor]
                denominator += influence
            values[index] = numerator / denominator
            final_delta = max(final_delta, abs(values[index] - previous[index]))
        if final_delta <= FAIRING_TOLERANCE_M:
            break
    if final_delta > FAIRING_TOLERANCE_M:
        raise ValueError(
            "fixed-seam/fixed-tangent-ring fairing did not converge: "
            f"iterations={iteration_count} delta={final_delta}"
        )
    return values, {
        "method": "inverse_edge_length_graph_laplacian_relative_to_two_ring_cubic_baseline",
        "fixed_exact_seam_vertex_count": EXPECTED_SEAM_COUNT,
        "fixed_first_tangent_ring_vertex_count": len(tangent_targets),
        "solved_remaining_interior_vertex_count": len(solved_indices),
        "iteration_count": iteration_count,
        "maximum_final_iteration_delta_m": final_delta,
        "tolerance_m": FAIRING_TOLERANCE_M,
        "residual_range_m": [min(values), max(values)],
    }


def smoothstep01(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def localized_relief(
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
    progress = (max_z - z) / max(max_z - min_z, 1.0e-6)
    distance = min(
        curvature_worker.segment_distance_2d(
            (x, z),
            boundary_xz[index],
            boundary_xz[(index + 1) % EXPECTED_SEAM_COUNT],
        )
        for index in range(EXPECTED_SEAM_COUNT)
    )
    # No field edge at the seam or fixed first ring; broad smooth fade-in.
    seam_fade = smoothstep01((distance - 0.0045) / 0.016)
    posterior_fade = 1.0 - smoothstep01((progress - 0.80) / 0.16)
    g = attempt_05_worker.gaussian
    terms = {
        "bilateral_outer_folds": 0.00058
        * (g(nx, -0.30, 0.18) + g(nx, 0.30, 0.18))
        * g(progress, 0.48, 0.30),
        "bilateral_inner_folds": 0.00036
        * (g(nx, -0.11, 0.075) + g(nx, 0.11, 0.075))
        * g(progress, 0.50, 0.24),
        "subtle_vestibule": -0.00018 * g(nx, 0.0, 0.14) * g(progress, 0.53, 0.20),
        "small_superior_hood": 0.00028 * g(nx, 0.0, 0.12) * g(progress, 0.27, 0.10),
        "shallow_urethral_recess": -0.00012 * g(nx, 0.0, 0.070) * g(progress, 0.43, 0.065),
        "shallow_vaginal_recess": -0.00033 * g(nx, 0.0, 0.10) * g(progress, 0.62, 0.11),
        "posterior_perineal_transition": 0.00011 * g(nx, 0.0, 0.20) * g(progress, 0.75, 0.13),
    }
    fade = seam_fade * posterior_fade
    return sum(terms.values()) * fade, terms, fade


def make_tangent_ring_cdt_patch(
    source_patch: bpy.types.Object,
    ordered_cycle: list[int],
    collection: bpy.types.Collection,
) -> tuple[bpy.types.Object, dict[str, object]]:
    global LAST_AUTHORING_RECORD
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
    attempt_05_worker.FIT_GEODESIC_DEPTH = FIT_GEODESIC_DEPTH
    coefficients, fit_record, fit_sample_indices = attempt_05_worker.fit_base_pelvic_cubic(
        torso,
        boundary_world,
        boundary_xz,
    )
    grid_xz, grid_record = attempt_05_worker.sample_regular_interior_grid(boundary_xz)
    points_xz, triangles, cdt_record = attempt_05_worker.constrained_delaunay_disk(
        boundary_xz,
        grid_xz,
    )
    baseline_y = [
        attempt_05_worker.evaluate_cubic(x, z, coefficients, fit_record)
        for x, z in points_xz
    ]
    boundary_normals, normal_record = retained_torso_boundary_normals(
        torso,
        boundary_world,
    )
    tangent_targets, tangent_record = fixed_first_tangent_ring(
        points_xz,
        triangles,
        boundary_world,
        boundary_normals,
    )
    fair_residuals, fair_record = fair_remaining_interior(
        points_xz,
        triangles,
        baseline_y,
        boundary_world,
        tangent_targets,
    )
    weight_tree, nearby_weights = attempt_05_worker.nearby_weight_samples(
        torso,
        fit_sample_indices,
        boundary_xz,
        boundary_weights,
    )

    vertices_world: list[Vector] = []
    weight_records: list[dict[str, float]] = []
    relief_values = []
    relief_fades = []
    relief_term_ranges: defaultdict[str, list[float]] = defaultdict(list)
    first_ring_indices = set(tangent_targets)
    for index, (x, z) in enumerate(points_xz):
        if index < EXPECTED_SEAM_COUNT:
            vertices_world.append(boundary_world[index].copy())
            weight_records.append(dict(boundary_weights[index]))
            continue
        if index in first_ring_indices:
            outward_relief = 0.0
            terms: dict[str, float] = {}
            fade = 0.0
            y = tangent_targets[index]
        else:
            outward_relief, terms, fade = localized_relief(x, z, boundary_xz)
            y = baseline_y[index] + fair_residuals[index] - outward_relief
        vertices_world.append(Vector((x, y, z)))
        weight_records.append(
            attempt_05_worker.interpolate_nearby_weights(
                (x, z),
                weight_tree,
                nearby_weights,
            )
        )
        relief_values.append(outward_relief)
        relief_fades.append(fade)
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
    mesh = bpy.data.meshes.new("Kira_R19_Tangent_Ring_CDT_Adult_Surface_Mesh")
    mesh.from_pydata([tuple(point) for point in local_vertices], [], oriented_triangles)
    mesh.validate(verbose=True)
    mesh.update()
    patch = bpy.data.objects.new("Kira_R19_Tangent_Ring_CDT_Adult_Surface", mesh)
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
    for name in sorted({name for weights in weight_records for name in weights}):
        patch.vertex_groups.new(name=name)
    for vertex_index, weights in enumerate(weight_records):
        for name, value in base_worker.normalized_top_four(weights).items():
            patch.vertex_groups[name].add([vertex_index], value, "REPLACE")

    boundary_deltas = [
        (patch.matrix_world @ patch.data.vertices[index].co - boundary_world[index]).length
        for index in range(EXPECTED_SEAM_COUNT)
    ]
    if max(boundary_deltas) > 1.0e-12:
        raise ValueError(
            "attempt-06 patch did not preserve exact seam coordinates: "
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
    patch["topology"] = "regular_xz_CDT_fixed_C1_tangent_ring_faired_interior"
    center = sum(boundary_world, Vector((0.0, 0.0, 0.0))) / len(boundary_world)
    record: dict[str, object] = {
        "attempt_06_localized_C1_tangent_ring_correction": True,
        "attempt_05_regular_topology_retained": True,
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
        "retained_torso_boundary_normals": normal_record,
        "first_interior_tangent_ring": tangent_record,
        "harmonic_boundary_residual_correction": fair_record,
        "neutral_depth_equation": "two-ring cubic base-body y plus fixed-seam/fixed-tangent-ring Laplacian residual",
        "bounded_external_relief": {
            "direction": "negative_world_Y_is_outward",
            "first_tangent_ring_relief_m": 0.0,
            "combined_outward_range_m": [min(relief_values), max(relief_values)],
            "fade_range": [min(relief_fades), max(relief_fades)],
            "term_ranges_m": {
                name: [min(values), max(values)]
                for name, values in sorted(relief_term_ranges.items())
            },
            "lateral_amplitudes_reduced_from_attempt_05": True,
        },
        "new_vertex_count": len(patch.data.vertices),
        "new_face_count": len(patch.data.polygons),
        "structured_grid_generated_vertex_count": len(grid_xz),
        "structured_grid_generated_face_count": len(patch.data.polygons),
        "structured_grid_face_vertex_count_histogram": dict(sorted(face_histogram.items())),
        "maximum_vertex_valence": maximum_valence,
        "weight_transfer": {
            "outer_seam": "normalized exact source seam weights",
            "interior": "inverse_squared projected distance blend of eight nearby two-ring base-torso/seam records",
            "maximum_influences": 4,
            "source_interior_weights_used": False,
        },
        "boundary_mean_world_m": base_worker.vec_record(center),
        "longitudinal_axis_world": [0.0, 0.0, -1.0],
        "outward_axis_world": [0.0, -1.0, 0.0],
        "annular_quad_count": 0,
        "face_orientation_reversals_before_recalc": reversed_face_count,
    }
    LAST_AUTHORING_RECORD = record
    return patch, record


def explicit_patch_wire_curve(
    scene: bpy.types.Scene,
    body: bpy.types.Object,
) -> tuple[bpy.types.Object, dict[str, object]]:
    patch_slots = [
        index
        for index, material in enumerate(body.data.materials)
        if material is not None and "Radial_Patch_Skin_Audit_Tag" in material.name
    ]
    if len(patch_slots) != 1:
        raise ValueError(f"could not uniquely identify joined patch material: {patch_slots}")
    patch_slot = patch_slots[0]
    edge_set: set[tuple[int, int]] = set()
    patch_faces = [
        polygon
        for polygon in body.data.polygons
        if int(polygon.material_index) == patch_slot
    ]
    for polygon in patch_faces:
        vertices = list(map(int, polygon.vertices))
        for first, second in zip(vertices, vertices[1:] + vertices[:1]):
            edge_set.add(tuple(sorted((first, second))))
    if len(edge_set) < 100:
        raise ValueError(f"patch wire overlay edge inventory is too small: {len(edge_set)}")

    curve_data = bpy.data.curves.new("Kira_R19_Attempt06_Patch_Wire_Data", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 1
    curve_data.bevel_depth = 0.00022
    curve_data.bevel_resolution = 0
    curve_data.resolution_u = 1
    normal_matrix = body.matrix_world.to_3x3().inverted().transposed()
    world_points = []
    for vertex in body.data.vertices:
        point = body.matrix_world @ vertex.co
        normal = (normal_matrix @ vertex.normal).normalized()
        world_points.append(point + normal * 0.00038)
    for first, second in sorted(edge_set):
        spline = curve_data.splines.new("POLY")
        spline.points.add(1)
        spline.points[0].co = (*world_points[first], 1.0)
        spline.points[1].co = (*world_points[second], 1.0)
    wire_object = bpy.data.objects.new("Kira_R19_Attempt06_Explicit_Patch_Wire", curve_data)
    scene.collection.objects.link(wire_object)
    wire_material = base_worker.make_material(
        "Kira_R19_Attempt06_Wire_Cyan",
        (0.015, 0.52, 0.78, 1.0),
        0.30,
    )
    curve_data.materials.append(wire_material)
    return wire_object, {
        "method": "temporary_beveled_curve_for_each_unique_joined_patch_edge",
        "patch_material_slot": patch_slot,
        "patch_face_count": len(patch_faces),
        "unique_patch_edge_count": len(edge_set),
        "curve_spline_count": len(curve_data.splines),
        "bevel_depth_m": curve_data.bevel_depth,
        "normal_offset_m": 0.00038,
        "temporary_curve_removed_before_blend_save": True,
    }


def render_with_explicit_wire_overlays(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    output_dir: Path,
    body: bpy.types.Object,
    patch_center: Vector,
) -> dict[str, str]:
    global LAST_AUTHORING_RECORD
    renders = ORIGINAL_RENDER_PROBE_SET(scene, camera, output_dir, body, patch_center)
    wire_object, wire_record = explicit_patch_wire_curve(scene, body)
    shading = scene.display.shading
    original = {
        "light": shading.light,
        "color_type": shading.color_type,
        "show_shadows": shading.show_shadows,
        "show_cavity": shading.show_cavity,
        "cavity_type": shading.cavity_type,
    }
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_shadows = False
    shading.show_cavity = True
    shading.cavity_type = "BOTH"
    views = {
        "wire_overlay_front": (Vector((patch_center.x, patch_center.y - 1.6, patch_center.z)), 0.245),
        "wire_overlay_three_quarter": (Vector((patch_center.x + 1.1, patch_center.y - 1.25, patch_center.z)), 0.265),
        "wire_overlay_side": (Vector((patch_center.x + 1.6, patch_center.y, patch_center.z)), 0.245),
    }
    for name, (location, scale) in views.items():
        path = output_dir / f"{name}.png"
        base_worker.render_view(scene, camera, path, location, patch_center, scale)
        renders[name] = path.name
    shading.light = original["light"]
    shading.color_type = original["color_type"]
    shading.show_shadows = original["show_shadows"]
    shading.show_cavity = original["show_cavity"]
    shading.cavity_type = original["cavity_type"]
    curve_data = wire_object.data
    bpy.data.objects.remove(wire_object, do_unlink=True)
    bpy.data.curves.remove(curve_data)
    if LAST_AUTHORING_RECORD is not None:
        LAST_AUTHORING_RECORD["wire_overlay_capture"] = wire_record
    return renders


def boundary_multiset(topology: dict[str, object]) -> list[int]:
    return sorted(int(record["vertex_count"]) for record in topology.get("boundary_parts", []))


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
            {"schema_version": 1, "append_only_attempt": "attempt_06", "files_excluding_this_manifest": entries},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest_path


def finalize_attempt_06() -> None:
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
    wire = authored["wire_overlay_capture"]
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
        "regular_CDT_without_center_fan_retained": (
            authored["attempt_05_regular_topology_retained"] is True
            and int(authored["constrained_delaunay"]["boundary_star_spoke_vertex_count"]) == 0
            and int(authored["central_single_pole_vertex_count"]) == 0
        ),
        "two_ring_outside_aperture_cubic_fit": (
            int(authored["base_body_curvature_fit"]["geodesic_ring_depth"]) == FIT_GEODESIC_DEPTH
            and int(authored["base_body_curvature_fit"]["sample_count"]) >= 80
        ),
        "fixed_first_tangent_ring_present": (
            int(authored["first_interior_tangent_ring"]["first_ring_vertex_count"]) > 0
            and authored["first_interior_tangent_ring"]["fixed_during_remaining_interior_fairing"] is True
        ),
        "remaining_interior_fairing_converged": float(authored["harmonic_boundary_residual_correction"]["maximum_final_iteration_delta_m"]) <= FAIRING_TOLERANCE_M,
        "explicit_wire_overlay_geometry_present": (
            int(wire["unique_patch_edge_count"]) >= 100
            and int(wire["curve_spline_count"]) == int(wire["unique_patch_edge_count"])
        ),
        "wire_overlay_closeups_present": all(
            name in renders
            for name in ("wire_overlay_front", "wire_overlay_three_quarter", "wire_overlay_side")
        ),
    }
    if not all(gates.values()):
        failures = sorted(name for name, passed in gates.items() if not passed)
        raise ValueError(f"attempt-06 bounded structural gates failed: {failures}")
    this_path = Path(__file__).resolve()
    dependencies = [
        Path(attempt_05_worker.__file__).resolve(),
        Path(curvature_worker.__file__).resolve(),
        Path(bounded_worker.__file__).resolve(),
        Path(base_worker.__file__).resolve(),
    ]
    evidence["attempt"] = "attempt_06"
    evidence["status"] = "PRIVATE_INACTIVE_FIXED_TANGENT_RING_CDT_STRUCTURAL_GATES_PASSED_REQUIRES_VISUAL_REVIEW"
    evidence["attempt_06_scoped_structural_gate"] = {
        **gates,
        "expected_inherited_boundary_loop_size_multiset": expected_multiset,
        "observed_inherited_boundary_loop_size_multiset": observed_multiset,
        "unresolved_foundation_property": "330 supported BlackProject boundary edges in 23 loops remain unchanged outside this patch",
    }
    evidence["worker"] = {
        "path": str(this_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "sha256": sha256_file(this_path),
        "dependencies": [
            {"path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"), "sha256": sha256_file(path)}
            for path in dependencies
        ],
    }
    evidence["gates"].update(gates)
    evidence["gates"]["closed_primary_surface"] = False
    evidence["gates"]["visual_review"] = "PENDING"
    evidence["gates"]["owner_approval"] = "PENDING"
    evidence["gates"]["runtime_eligibility"] = False
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    (output_dir / "REPORT.md").write_text(
        "\n".join(
            [
                "# R19 BlackProject fixed tangent-ring constrained-Delaunay patch — attempt 06",
                "",
                f"Status: `{evidence['status']}`",
                "",
                "- Attempts 01–05 remain unchanged.",
                "- Attempt 05's regular X/Z lattice and constrained-Delaunay topology are retained; no center pole, fan, or recursive centroid hierarchy was introduced.",
                "- The cubic baseline is limited to the nearest two retained-torso geodesic rings outside the projected aperture.",
                "- Retained-torso seam normals fix the first interior tangent ring; the remaining interior is faired with both seam and tangent ring fixed.",
                "- Relief is zero on the tangent ring, smoothly localized inward, and shallower laterally.",
                "- Exactly 34 seam vertices merged; the new patch adds zero open edges and zero exact intersections.",
                "- Explicit temporary beveled curves render the actual joined patch edges, then are removed before the Blend is saved.",
                "- Structural passage does not imply visual or owner approval; reject if a triangular/rectangular outline, plate, accordion, pinched recess, seam, or star-spoke pattern remains visible.",
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
    if not failure_path.exists():
        source_path = PROJECT_ROOT / base_worker.SOURCE_REL
        failure_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "attempt": "attempt_06",
                    "status": "FAILED_BEFORE_STRUCTURAL_ACCEPTANCE",
                    "utc": datetime.now(timezone.utc).isoformat(),
                    "exception_type": type(exc).__name__,
                    "exception": str(exc),
                    "traceback": traceback.format_exc(),
                    "source_sha256": sha256_file(source_path),
                    "worker_sha256": sha256_file(Path(__file__).resolve()),
                    "earlier_attempts_modified": False,
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
        raise FileExistsError("append-only attempt_06 already exists")
    bounded_worker.OUTPUT_REL = OUTPUT_REL
    bounded_worker.make_radial_patch_attempt_02 = make_tangent_ring_cdt_patch
    base_worker.render_probe_set = render_with_explicit_wire_overlays
    try:
        result = bounded_worker.main()
        finalize_attempt_06()
    except BaseException as exc:
        preserve_failure(exc)
        raise
    print(json.dumps({"ok": True, "attempt": "attempt_06", "output_dir": str(output_dir)}, indent=2))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
