#!/usr/bin/env python3
"""Kira/BlackProject Blender adapter for connected-region nail projection.

This adapter is deliberately limited to constructing and validating one nail
at a time.  It has no file-open, save, render, export, or process path.  The
caller supplies the exact body, rig, source-native nail landmark, materials,
and declared inventory row.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from typing import Any, Mapping, Sequence

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from Core.avatar_nail_weight_constrained_projection_v1 import (
    MAXIMUM_FINAL_CLEARANCE_M,
    MINIMUM_EXPECTED_FAMILY_WEIGHT,
    NailWeightConstrainedProjectionError,
    select_connected_weight_constrained_grid,
    validate_final_evaluated_shell_gate,
)
from Core.avatar_natural_nail_delivery_v3 import (
    CENTER_FRACTION_CANDIDATES,
    FOOTPRINT_SCALE_CANDIDATES,
    MAXIMUM_NORMAL_LIFT_ITERATIONS,
    NAIL_PLATE_THICKNESS_M,
    NORMAL_LIFT_STEP_M,
    PROJECTION_GRID_SIZE,
    is_free_edge_face_row,
    oval_half_width_scale,
)
from Core.kira_blackproject_nail_topology_v1 import (
    METHOD_ID,
    digit_weight_evidence,
    parse_blackproject_digit_bone,
    summarize_footprint_binding,
)
from tools import blender_avatar_natural_nail_delivery_v3 as nails
from tools import blender_diagnose_robert_r26_finger5_nail_modifier_stages as stages
from tools import blender_probe_robert_r26_all20_evaluated_nail_footprints as all20


MAXIMUM_RAY_HITS = 8
RAY_START_OFFSET_M = 0.025
RAY_LENGTH_M = 0.050
RAY_ADVANCE_EPSILON_M = 0.000002
MAXIMUM_RAW_CAGE_MAPPING_DISTANCE_M = 0.004
NOT_DECLARED_DIGIT_COMPONENT = 0
REFERENCE_ANCHOR_MAXIMUM_ERROR_M = 0.0015


class BlackProjectWeightConstrainedNailError(RuntimeError):
    pass


def _raw_vertex_influences(body: Any, index: int) -> dict[str, float]:
    names = {int(group.index): str(group.name) for group in body.vertex_groups}
    influences = {
        names[int(row.group)]: float(row.weight)
        for row in body.data.vertices[int(index)].groups
        if int(row.group) in names and float(row.weight) > 0.0
    }
    total = sum(influences.values())
    if total <= 0.0 or not math.isfinite(total):
        raise BlackProjectWeightConstrainedNailError(
            f"raw body vertex has no finite positive weights: {index}"
        )
    return {name: value / total for name, value in influences.items()}


def _vertex_is_strict_declared_digit(
    body: Any, vertex_index: int, expected_family: str
) -> bool:
    evidence = digit_weight_evidence(
        _raw_vertex_influences(body, vertex_index), expected_family
    )
    return (
        float(evidence["expected_family_weight"])
        >= MINIMUM_EXPECTED_FAMILY_WEIGHT
        and float(evidence["foreign_digit_family_weight"]) <= 0.01
        and float(evidence["wrong_side_digit_weight"]) <= 0.01
        and evidence["expected_family_is_dominant"] is True
    )


def declared_digit_triangle_components(
    *,
    body: Any,
    raw_triangles: Sequence[tuple[int, int, int]],
    expected_family: str,
) -> tuple[dict[int, int], dict[str, Any]]:
    """Label strict declared-digit raw triangles by shared-edge connectivity."""

    relevant_vertices = {
        int(vertex) for triangle in raw_triangles for vertex in triangle
    }
    strict = {
        vertex: _vertex_is_strict_declared_digit(body, vertex, expected_family)
        for vertex in relevant_vertices
    }
    eligible = {
        index
        for index, triangle in enumerate(raw_triangles)
        if all(strict[int(vertex)] for vertex in triangle)
    }
    if not eligible:
        raise BlackProjectWeightConstrainedNailError(
            f"declared Kira digit has no strict raw triangles: {expected_family}"
        )
    edge_to_triangles: dict[tuple[int, int], list[int]] = defaultdict(list)
    for triangle_index in eligible:
        a, b, c = raw_triangles[triangle_index]
        for left, right in ((a, b), (b, c), (c, a)):
            edge_to_triangles[tuple(sorted((int(left), int(right))))].append(
                triangle_index
            )
    neighbors: dict[int, set[int]] = {index: set() for index in eligible}
    for touching in edge_to_triangles.values():
        for left in touching:
            neighbors[left].update(right for right in touching if right != left)
    component_by_triangle: dict[int, int] = {}
    components = []
    for seed in sorted(eligible):
        if seed in component_by_triangle:
            continue
        component_id = len(components) + 1
        stack = [seed]
        members = []
        component_by_triangle[seed] = component_id
        while stack:
            current = stack.pop()
            members.append(current)
            for neighbor in sorted(neighbors[current]):
                if neighbor not in component_by_triangle:
                    component_by_triangle[neighbor] = component_id
                    stack.append(neighbor)
        components.append(
            {
                "raw_component_id": component_id,
                "raw_triangle_count": len(members),
                "minimum_raw_triangle_index": min(members),
                "maximum_raw_triangle_index": max(members),
            }
        )
    return component_by_triangle, {
        "expected_digit_family": expected_family,
        "strict_eligible_raw_triangle_count": len(eligible),
        "connected_component_count": len(components),
        "components": components,
        "triangle_eligibility_requires_all_three_vertices": True,
        "minimum_each_vertex_expected_family_weight": (
            MINIMUM_EXPECTED_FAMILY_WEIGHT
        ),
        "automatic_bone_remap_performed": False,
    }


def corrected_reference_definition(
    *,
    source_nail: Any,
    body: Any,
    armature: Any,
    definition: Mapping[str, Any],
    expected_anchor_world_m: Sequence[float],
) -> dict[str, Any]:
    """Derive a world-space landmark without using the bad nail parent inverse.

    The inherited nail mesh coordinates are in the BlackProject body-local
    frame.  Applying ``source_nail.matrix_world`` reproduces the known ~105x
    placement error.  The exact correction is ``body.matrix_world @ vertex.co``.
    """

    if source_nail is None or source_nail.type != "MESH":
        raise BlackProjectWeightConstrainedNailError("source-native nail missing")
    if str(source_nail.name) != str(definition["source_object"]):
        raise BlackProjectWeightConstrainedNailError("source-native nail identity drifted")
    if armature.data.bones.get(str(definition["bone"])) is None:
        raise BlackProjectWeightConstrainedNailError("declared terminal bone missing")
    positive_groups = []
    for group in source_nail.vertex_groups:
        positive = 0
        for vertex in source_nail.data.vertices:
            try:
                positive += int(float(group.weight(vertex.index)) > 0.0)
            except RuntimeError:
                pass
        if positive:
            positive_groups.append((str(group.name), positive))
    if positive_groups != [(str(definition["bone"]), len(source_nail.data.vertices))]:
        raise BlackProjectWeightConstrainedNailError(
            "source-native landmark is not exactly bound to its declared bone"
        )
    points = [body.matrix_world @ vertex.co for vertex in source_nail.data.vertices]
    if not points:
        raise BlackProjectWeightConstrainedNailError("source-native nail has no vertices")
    points_np = np.asarray([tuple(map(float, point)) for point in points], dtype=np.float64)
    center_np = points_np.mean(axis=0)
    center = Vector(tuple(float(value) for value in center_np))
    expected_anchor = Vector(tuple(float(value) for value in expected_anchor_world_m))
    anchor_error = float((center - expected_anchor).length)
    if anchor_error > REFERENCE_ANCHOR_MAXIMUM_ERROR_M:
        raise BlackProjectWeightConstrainedNailError(
            f"corrected source anchor drifted by {anchor_error:.9f} m"
        )
    covariance = np.cov((points_np - center_np).T)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    normal = Vector(tuple(float(value) for value in eigenvectors[:, 0])).normalized()
    tangent_a = Vector(tuple(float(value) for value in eigenvectors[:, 1])).normalized()
    tangent_b = Vector(tuple(float(value) for value in eigenvectors[:, 2])).normalized()
    bone = armature.data.bones[str(definition["bone"])]
    bone_direction = (
        armature.matrix_world.to_3x3() @ (bone.tail_local - bone.head_local)
    ).normalized()
    longitudinal = (
        tangent_a
        if abs(float(tangent_a.dot(bone_direction)))
        >= abs(float(tangent_b.dot(bone_direction)))
        else tangent_b
    )
    if longitudinal.dot(bone_direction) < 0.0:
        longitudinal = -longitudinal
    longitudinal = (longitudinal - normal * longitudinal.dot(normal)).normalized()
    lateral = normal.cross(longitudinal).normalized()
    longitudinal = lateral.cross(normal).normalized()
    raw_points, raw_triangles = all20.world_geometry(body, evaluated=False)
    raw_tree = BVHTree.FromPolygons(raw_points, raw_triangles, all_triangles=True)
    nearest, nearest_normal, _triangle, _distance = raw_tree.find_nearest(
        center, 0.010
    )
    if nearest is None or nearest_normal is None:
        raise BlackProjectWeightConstrainedNailError(
            "corrected landmark cannot find the local body surface"
        )
    if normal.dot(nearest_normal) < 0.0:
        normal = -normal
        lateral = -lateral
    centered = points_np - center_np
    length_values = centered @ np.asarray(tuple(longitudinal), dtype=np.float64)
    width_values = centered @ np.asarray(tuple(lateral), dtype=np.float64)
    source_length = float(length_values.max() - length_values.min())
    source_width = float(width_values.max() - width_values.min())
    terminal = armature.matrix_world @ bone.tail_local
    return {
        **dict(definition),
        "reference_center_world": center,
        "reference_terminal_world": terminal,
        "reference_longitudinal_world": longitudinal,
        "reference_lateral_world": lateral,
        "reference_outward_world": normal,
        "reference_length_m": source_length,
        "reference_width_m": source_width,
        "target_length_m": source_length * float(definition["reference_length_scale"]),
        "target_width_m": source_width * float(definition["reference_width_scale"]),
        "corrected_anchor_expected_world_m": list(map(float, expected_anchor)),
        "corrected_anchor_actual_world_m": list(map(float, center)),
        "corrected_anchor_error_m": anchor_error,
        "corrected_anchor_maximum_error_m": REFERENCE_ANCHOR_MAXIMUM_ERROR_M,
        "source_transform_rule": "body.matrix_world_at_source_open @ source_nail.data.vertex.co",
        "source_nail_matrix_world_used_for_placement": False,
        "source_pca_eigenvalues": [float(value) for value in eigenvalues],
    }


def _bounded_ray_hit_stack(
    *,
    expected_point: Vector,
    outward: Vector,
    evaluated_tree: BVHTree,
    body: Any,
    raw_tree: BVHTree,
    raw_points: Sequence[Vector],
    raw_triangles: Sequence[tuple[int, int, int]],
    group_names: Mapping[int, str],
    component_by_triangle: Mapping[int, int],
    expected_family: str,
) -> list[dict[str, Any]]:
    direction = -outward
    origin = expected_point + outward * RAY_START_OFFSET_M
    traveled = 0.0
    remaining = RAY_LENGTH_M
    records = []
    for ordinal in range(MAXIMUM_RAY_HITS):
        hit, normal, evaluated_triangle, distance = evaluated_tree.ray_cast(
            origin, direction, remaining
        )
        if hit is None or normal is None or evaluated_triangle is None:
            break
        depth = traveled + float(distance)
        normal = normal.normalized()
        influences, mapping = all20.interpolate_raw_cage_influences(
            point=hit,
            body=body,
            raw_tree=raw_tree,
            raw_points=raw_points,
            raw_triangles=raw_triangles,
            group_names=group_names,
        )
        raw_triangle = int(mapping["raw_loop_triangle_index"])
        evidence = digit_weight_evidence(influences, expected_family)
        records.append(
            {
                "ray_hit_ordinal": ordinal,
                "ray_depth_m": depth,
                "distance_to_expected_point_m": float((hit - expected_point).length),
                "evaluated_triangle_index": int(evaluated_triangle),
                "raw_triangle_index": raw_triangle,
                "raw_component_id": int(
                    component_by_triangle.get(raw_triangle, NOT_DECLARED_DIGIT_COMPONENT)
                ),
                "expected_family_weight": evidence["expected_family_weight"],
                "foreign_digit_family_weight": evidence["foreign_digit_family_weight"],
                "wrong_side_digit_weight": evidence["wrong_side_digit_weight"],
                "expected_family_is_dominant": evidence["expected_family_is_dominant"],
                "winning_digit_family": evidence["winning_digit_family"],
                "digit_family_weights": evidence["digit_family_weights"],
                "outward_normal_alignment": float(normal.dot(outward)),
                "raw_cage_distance_m": float(mapping["raw_cage_distance_m"]),
                "raw_barycentric": mapping["raw_barycentric"],
                "influences": influences,
                "location": hit.copy(),
                "normal": normal.copy(),
            }
        )
        advance = float(distance) + RAY_ADVANCE_EPSILON_M
        traveled += advance
        remaining = RAY_LENGTH_M - traveled
        if remaining <= 0.0:
            break
        origin = hit + direction * RAY_ADVANCE_EPSILON_M
    return records


def _compact_hit(hit: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in hit.items()
        if key not in {"location", "normal", "influences"}
    }


def _candidate_grid(
    *,
    definition: Mapping[str, Any],
    footprint_scale: float,
    center_fraction: float,
    evaluated_tree: BVHTree,
    body: Any,
    raw_tree: BVHTree,
    raw_points: Sequence[Vector],
    raw_triangles: Sequence[tuple[int, int, int]],
    group_names: Mapping[int, str],
    component_by_triangle: Mapping[int, int],
) -> dict[str, Any]:
    grid = PROJECTION_GRID_SIZE
    length_m = float(definition["target_length_m"])
    width_m = float(definition["target_width_m"])
    terminal = definition["reference_terminal_world"]
    longitudinal = definition["reference_longitudinal_world"]
    lateral = definition["reference_lateral_world"]
    outward = definition["reference_outward_world"]
    nominal_center = terminal - longitudinal * (length_m * center_fraction)
    stacks = []
    for row in range(grid):
        along = ((row / (grid - 1)) - 0.5) * length_m * footprint_scale
        half_width = oval_half_width_scale(row, grid)
        for column in range(grid):
            across = (
                ((column / (grid - 1)) - 0.5)
                * width_m
                * footprint_scale
                * half_width
            )
            expected = nominal_center + longitudinal * along + lateral * across
            stacks.append(
                _bounded_ray_hit_stack(
                    expected_point=expected,
                    outward=outward,
                    evaluated_tree=evaluated_tree,
                    body=body,
                    raw_tree=raw_tree,
                    raw_points=raw_points,
                    raw_triangles=raw_triangles,
                    group_names=group_names,
                    component_by_triangle=component_by_triangle,
                    expected_family=str(definition["family"]),
                )
            )
    selection = select_connected_weight_constrained_grid(
        stacks, center_sample_index=(grid * grid) // 2
    )
    selected = selection["selected_hits"]
    hits = [row["location"].copy() for row in selected]
    normals = [row["normal"].copy() for row in selected]
    binding = summarize_footprint_binding(
        nail_id=str(definition["nail_id"]),
        expected_bone=str(definition["bone"]),
        expected_family=str(definition["family"]),
        samples=[{"influences": row["influences"]} for row in selected],
    )
    locality = nails._grid_locality_record(  # noqa: SLF001
        points=hits,
        nominal_center=nominal_center,
        longitudinal=longitudinal,
        lateral=lateral,
        length_m=length_m,
        width_m=width_m,
        footprint_scale=footprint_scale,
        grid=grid,
    )
    if locality["locality_gate_passed"] is not True:
        raise BlackProjectWeightConstrainedNailError(
            "selected Kira digit grid failed local continuity"
        )
    return {
        "grid": grid,
        "length_m": length_m,
        "width_m": width_m,
        "hits": hits,
        "normals": normals,
        "selection": {
            **{key: value for key, value in selection.items() if key != "selected_hits"},
            "selected_hits": [_compact_hit(row) for row in selected],
        },
        "footprint_binding": {
            key: value for key, value in binding.items() if key != "per_sample"
        },
        "grid_locality": locality,
        "raw_ray_hit_count": sum(len(stack) for stack in stacks),
        "maximum_hits_on_one_ray": max(len(stack) for stack in stacks),
    }


def _create_top_plate(
    *,
    name: str,
    hits: Sequence[Vector],
    normals: Sequence[Vector],
    clearances: Sequence[float],
    bed_material: Any,
    free_edge_material: Any,
) -> Any:
    grid = PROJECTION_GRID_SIZE
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(
        [
            tuple(hit + normal * clearance)
            for hit, normal, clearance in zip(hits, normals, clearances)
        ],
        [],
        nails._outward_grid_faces(grid),  # noqa: SLF001
    )
    mesh.update(calc_edges=True)
    nail = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(nail)
    mesh.materials.append(bed_material)
    mesh.materials.append(free_edge_material)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
        row = int(polygon.index) // (grid - 1)
        polygon.material_index = 1 if is_free_edge_face_row(row, grid) else 0
    return nail


def _validate_complete_shell(
    *,
    nail: Any,
    body: Any,
    armature: Any,
    evaluated_points: Sequence[Vector],
    evaluated_triangles: Sequence[tuple[int, int, int]],
    source_count: int,
    solidify: Any,
    body_signature_before: str,
    rig_signature_before: str,
    body_modifier_count_before: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    nail_points, nail_triangles = stages.world_geometry(nail, evaluated=True)
    exact = stages.exact_pair_record(
        evaluated_points,
        evaluated_triangles,
        nail_points,
        nail_triangles,
        source_nail_vertex_count=source_count,
    )
    shell_raw = {
        "body_surface_space": "evaluated_rest",
        "nail_surface_space": "evaluated_armature_then_solidify",
        "exact_narrow_phase_used": True,
        "complete_shell_included": True,
        "solidify_rim_included": bool(getattr(solidify, "use_rim", True)),
        "source_top_vertex_count": source_count,
        "evaluated_shell_vertex_count": len(nail_points),
        "exact_genuine_triangle_pair_count": int(
            exact["exact_genuine_triangle_pair_count"]
        ),
        "minimum_unsigned_surface_clearance_m": float(
            exact["minimum_unsigned_surface_clearance_m"]
        ),
        "maximum_unsigned_surface_clearance_m": float(
            exact["maximum_unsigned_surface_clearance_m"]
        ),
        "body_mesh_unchanged": (
            nails._mesh_signature(body) == body_signature_before  # noqa: SLF001
        ),
        "official_rig_unchanged": (
            nails._rig_signature(armature) == rig_signature_before  # noqa: SLF001
        ),
        "body_modifier_stack_unchanged": (
            len(body.modifiers) == body_modifier_count_before
        ),
        "automatic_bone_remap_performed": False,
    }
    return exact, validate_final_evaluated_shell_gate(shell_raw)


def _finalize_attachment(
    nail: Any, armature: Any, bone_name: str
) -> tuple[Any, dict[str, Any]]:
    nails.v1.assign_rigid_bone(nail, armature, bone_name)
    solidify = nail.modifiers.new(
        "Natural_Nail_Plate_Thickness_Kira_Attempt03", "SOLIDIFY"
    )
    solidify.thickness = NAIL_PLATE_THICKNESS_M
    solidify.offset = 1.0
    if hasattr(solidify, "use_even_offset"):
        solidify.use_even_offset = True
    if hasattr(solidify, "use_rim"):
        solidify.use_rim = True
    attachment = nails._attachment_report(nail, armature, bone_name)  # noqa: SLF001
    return solidify, attachment


def build_weight_constrained_nail_v1(
    *,
    body: Any,
    armature: Any,
    definition: Mapping[str, Any],
    name: str,
    bed_material: Any,
    free_edge_material: Any,
) -> tuple[Any, dict[str, Any]]:
    """Build one Kira nail and pass the complete evaluated-shell gate."""

    expected_meta = parse_blackproject_digit_bone(str(definition["bone"]))
    if expected_meta is None or expected_meta["family"] != definition["family"]:
        raise BlackProjectWeightConstrainedNailError(
            "declared Kira terminal bone/family is not exact"
        )
    body_signature_before = nails._mesh_signature(body)  # noqa: SLF001
    rig_signature_before = nails._rig_signature(armature)  # noqa: SLF001
    body_modifier_count_before = len(body.modifiers)
    raw_points, raw_triangles = all20.world_geometry(body, evaluated=False)
    evaluated_points, evaluated_triangles = all20.world_geometry(body, evaluated=True)
    raw_tree = BVHTree.FromPolygons(raw_points, raw_triangles, all_triangles=True)
    evaluated_tree = BVHTree.FromPolygons(
        evaluated_points, evaluated_triangles, all_triangles=True
    )
    if float(all20.MAXIMUM_RAW_CAGE_MAPPING_DISTANCE_M) != MAXIMUM_RAW_CAGE_MAPPING_DISTANCE_M:
        raise BlackProjectWeightConstrainedNailError(
            "raw-cage mapping distance contract differs from the proven probe"
        )
    component_by_triangle, component_evidence = declared_digit_triangle_components(
        body=body,
        raw_triangles=raw_triangles,
        expected_family=str(definition["family"]),
    )
    group_names = all20.body_group_names(body)
    attempts = []
    for footprint_scale in FOOTPRINT_SCALE_CANDIDATES:
        for center_fraction in CENTER_FRACTION_CANDIDATES:
            attempt: dict[str, Any] = {
                "footprint_scale": float(footprint_scale),
                "center_fraction": float(center_fraction),
                "automatic_bone_remap_performed": False,
            }
            nail = None
            try:
                candidate = _candidate_grid(
                    definition=definition,
                    footprint_scale=float(footprint_scale),
                    center_fraction=float(center_fraction),
                    evaluated_tree=evaluated_tree,
                    body=body,
                    raw_tree=raw_tree,
                    raw_points=raw_points,
                    raw_triangles=raw_triangles,
                    group_names=group_names,
                    component_by_triangle=component_by_triangle,
                )
                clearances = []
                grid = int(candidate["grid"])
                for _row in range(grid):
                    for column in range(grid):
                        arch = 1.0 - min(
                            1.0, abs((column / (grid - 1)) - 0.5) * 2.0
                        ) ** 2
                        clearances.append(0.000055 + 0.000055 * arch)
                nail = _create_top_plate(
                    name=name,
                    hits=candidate["hits"],
                    normals=candidate["normals"],
                    clearances=clearances,
                    bed_material=bed_material,
                    free_edge_material=free_edge_material,
                )
                winding = nails._top_surface_winding_record(  # noqa: SLF001
                    nail, definition["reference_outward_world"]
                )
                if winding["all_top_surface_faces_outward"] is not True:
                    raise BlackProjectWeightConstrainedNailError(
                        "Kira nail top surface is folded or inward"
                    )
                solidify, attachment = _finalize_attachment(
                    nail, armature, str(definition["bone"])
                )
                source_count = len(nail.data.vertices)
                lift_attempts = []
                for lift_iteration in range(MAXIMUM_NORMAL_LIFT_ITERATIONS + 1):
                    additional = lift_iteration * NORMAL_LIFT_STEP_M
                    for vertex, hit, normal, base in zip(
                        nail.data.vertices,
                        candidate["hits"],
                        candidate["normals"],
                        clearances,
                    ):
                        vertex.co = hit + normal * (base + additional)
                    nail.data.update()
                    bpy.context.view_layer.update()
                    try:
                        exact, shell_gate = _validate_complete_shell(
                            nail=nail,
                            body=body,
                            armature=armature,
                            evaluated_points=evaluated_points,
                            evaluated_triangles=evaluated_triangles,
                            source_count=source_count,
                            solidify=solidify,
                            body_signature_before=body_signature_before,
                            rig_signature_before=rig_signature_before,
                            body_modifier_count_before=body_modifier_count_before,
                        )
                    except NailWeightConstrainedProjectionError as exc:
                        row = {
                            "lift_iteration": lift_iteration,
                            "additional_normal_lift_m": additional,
                            "shell_gate_passed": False,
                            "failure": str(exc),
                        }
                        lift_attempts.append(row)
                        continue
                    lift_attempts.append(
                        {
                            "lift_iteration": lift_iteration,
                            "additional_normal_lift_m": additional,
                            "exact_full_shell": exact,
                            "shell_gate": shell_gate,
                            "shell_gate_passed": True,
                        }
                    )
                    final_clearances = [base + additional for base in clearances]
                    world_vertices = [
                        list(map(float, nail.matrix_world @ vertex.co))
                        for vertex in nail.data.vertices
                    ]
                    return nail, {
                        "method": METHOD_ID,
                        "nail_id": str(definition["nail_id"]),
                        "kind": str(definition["kind"]),
                        "side": str(definition["side"]),
                        "digit": int(definition["digit"]),
                        "declared_terminal_bone": str(definition["bone"]),
                        "declared_digit_family": str(definition["family"]),
                        "footprint_scale": float(footprint_scale),
                        "center_fraction": float(center_fraction),
                        "connected_region_evidence": component_evidence,
                        "selection": candidate["selection"],
                        "footprint_binding": candidate["footprint_binding"],
                        "grid_locality": candidate["grid_locality"],
                        "top_surface_winding": winding,
                        "attachment": attachment,
                        "accepted_lift_iteration": lift_iteration,
                        "final_evaluated_complete_shell_gate": shell_gate,
                        "top_surface_vertices_world_m": world_vertices,
                        "top_surface_normals_world": [
                            list(map(float, normal)) for normal in candidate["normals"]
                        ],
                        "base_clearances_m": final_clearances,
                        "body_mesh_sha256_before": body_signature_before,
                        "body_mesh_sha256_after": nails._mesh_signature(body),  # noqa: SLF001
                        "official_rig_sha256_before": rig_signature_before,
                        "official_rig_sha256_after": nails._rig_signature(armature),  # noqa: SLF001
                        "body_modifier_count_before": body_modifier_count_before,
                        "body_modifier_count_after": len(body.modifiers),
                        "automatic_bone_remap_performed": False,
                        "all_strict_gates_passed": True,
                        "attempts": attempts + [attempt],
                    }
                attempt["lift_attempts"] = lift_attempts
                attempt["final_shell_passed"] = False
            except Exception as exc:
                attempt.update(
                    {
                        "failure_type": type(exc).__name__,
                        "failure": str(exc),
                        "projection_complete": False,
                    }
                )
            attempts.append(attempt)
            if nail is not None and nail.name in bpy.data.objects:
                nails._remove_object_and_mesh(nail)  # noqa: SLF001
    raise BlackProjectWeightConstrainedNailError(
        "bounded Kira weight-constrained projection failed: "
        + json.dumps(attempts, sort_keys=True)
    )


def reconstruct_cached_nail_v1(
    *,
    body: Any,
    armature: Any,
    definition: Mapping[str, Any],
    cached_component: Mapping[str, Any],
    name: str,
    bed_material: Any,
    free_edge_material: Any,
) -> tuple[Any, dict[str, Any]]:
    """Reconstruct a prior passing top plate and re-run every live shell gate."""

    body_signature_before = nails._mesh_signature(body)  # noqa: SLF001
    rig_signature_before = nails._rig_signature(armature)  # noqa: SLF001
    body_modifier_count_before = len(body.modifiers)
    points = [Vector(tuple(map(float, row))) for row in cached_component["top_surface_vertices_world_m"]]
    normals = [Vector(tuple(map(float, row))).normalized() for row in cached_component["top_surface_normals_world"]]
    zeros = [0.0] * len(points)
    nail = _create_top_plate(
        name=name,
        hits=points,
        normals=normals,
        clearances=zeros,
        bed_material=bed_material,
        free_edge_material=free_edge_material,
    )
    try:
        winding = nails._top_surface_winding_record(  # noqa: SLF001
            nail, definition["reference_outward_world"]
        )
        if winding["all_top_surface_faces_outward"] is not True:
            raise BlackProjectWeightConstrainedNailError(
                "cached Kira top surface winding changed"
            )
        solidify, attachment = _finalize_attachment(
            nail, armature, str(definition["bone"])
        )
        evaluated_points, evaluated_triangles = all20.world_geometry(body, evaluated=True)
        bpy.context.view_layer.update()
        exact, shell_gate = _validate_complete_shell(
            nail=nail,
            body=body,
            armature=armature,
            evaluated_points=evaluated_points,
            evaluated_triangles=evaluated_triangles,
            source_count=len(nail.data.vertices),
            solidify=solidify,
            body_signature_before=body_signature_before,
            rig_signature_before=rig_signature_before,
            body_modifier_count_before=body_modifier_count_before,
        )
        return nail, {
            "method": METHOD_ID,
            "nail_id": str(definition["nail_id"]),
            "reused_cached_top_surface_without_reprojection": True,
            "live_exact_full_shell": exact,
            "final_evaluated_complete_shell_gate": shell_gate,
            "attachment": attachment,
            "top_surface_winding": winding,
            "all_strict_gates_passed": True,
            "automatic_bone_remap_performed": False,
        }
    except Exception:
        nails._remove_object_and_mesh(nail)  # noqa: SLF001
        raise


__all__ = [
    "BlackProjectWeightConstrainedNailError",
    "MAXIMUM_RAY_HITS",
    "METHOD_ID",
    "REFERENCE_ANCHOR_MAXIMUM_ERROR_M",
    "build_weight_constrained_nail_v1",
    "corrected_reference_definition",
    "declared_digit_triangle_components",
    "reconstruct_cached_nail_v1",
]
