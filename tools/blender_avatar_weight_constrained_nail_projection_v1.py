#!/usr/bin/env python3
"""Reusable Blender adapter for weight-constrained evaluated nail projection.

This is an additive, unbound correction candidate.  It enumerates bounded
evaluated-body ray hits rather than accepting the global first hit, retains
only hits belonging to one connected raw-cage region owned by the declared
digit, and accepts only a complete evaluated Armature-plus-Solidify shell with
zero exact body penetrations.  It never remaps a nail to another bone.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from typing import Any, Mapping, Sequence

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from Core.avatar_nail_footprint_binding_v1 import (
    parse_digit_bone,
    summarize_footprint_binding,
)
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
from tools import blender_avatar_natural_nail_delivery_v3 as nails
from tools import blender_diagnose_robert_r26_finger5_nail_modifier_stages as stages
from tools import blender_probe_robert_r26_all20_evaluated_nail_footprints as all20


METHOD_ID = "avatar_weight_constrained_evaluated_nail_projection_v1"
MAXIMUM_RAY_HITS = 8
RAY_START_OFFSET_M = 0.025
RAY_LENGTH_M = 0.050
RAY_ADVANCE_EPSILON_M = 0.000002
MAXIMUM_RAW_CAGE_MAPPING_DISTANCE_M = 0.004
NOT_DECLARED_DIGIT_COMPONENT = 0


class WeightConstrainedNailProjectionError(RuntimeError):
    pass


def _raw_vertex_influences(body: Any, index: int) -> dict[str, float]:
    names = {int(group.index): str(group.name) for group in body.vertex_groups}
    result = {
        names[int(row.group)]: float(row.weight)
        for row in body.data.vertices[int(index)].groups
        if int(row.group) in names and float(row.weight) > 0.0
    }
    total = sum(result.values())
    if total <= 0.0 or not math.isfinite(total):
        raise WeightConstrainedNailProjectionError(
            f"raw body vertex has no finite positive weights: {index}"
        )
    return {name: value / total for name, value in result.items()}


def _digit_evidence(
    influences: Mapping[str, float], expected_family: str
) -> dict[str, Any]:
    families: dict[str, float] = defaultdict(float)
    # A family such as ``finger5.L`` is not itself a bone.  Parse its prefix
    # and side directly while every actual influence is parsed by the shared
    # official-bone parser.
    family_prefix, family_side = str(expected_family).split(".")
    expected_prefix = "finger" if family_prefix.startswith("finger") else "toe"
    wrong_side = 0.0
    for bone_name, raw_weight in influences.items():
        meta = parse_digit_bone(str(bone_name))
        if meta is None:
            continue
        weight = float(raw_weight)
        family = str(meta["family"])
        families[family] += weight
        if meta["prefix"] == expected_prefix and meta["side"] != family_side:
            wrong_side += weight
    ranked = sorted(families.items(), key=lambda row: (-row[1], row[0]))
    winner = ranked[0][0] if ranked else None
    expected = float(families.get(expected_family, 0.0))
    foreign = sum(
        float(value) for family, value in families.items() if family != expected_family
    )
    return {
        "expected_family_weight": expected,
        "foreign_digit_family_weight": foreign,
        "wrong_side_digit_weight": wrong_side,
        "winning_digit_family": winner,
        "expected_family_is_dominant": winner == expected_family,
        "digit_family_weights": dict(sorted(families.items())),
    }


def _vertex_is_strict_declared_digit(
    body: Any, vertex_index: int, expected_family: str
) -> bool:
    evidence = _digit_evidence(
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
    """Label strict declared-digit raw triangles by edge connectivity."""

    relevant_vertices = {
        int(vertex) for triangle in raw_triangles for vertex in triangle
    }
    strict_vertices = {
        vertex: _vertex_is_strict_declared_digit(
            body, vertex, expected_family
        )
        for vertex in relevant_vertices
    }
    eligible = {
        index
        for index, triangle in enumerate(raw_triangles)
        if all(strict_vertices[int(vertex)] for vertex in triangle)
    }
    if not eligible:
        raise WeightConstrainedNailProjectionError(
            f"declared digit has no strict raw triangles: {expected_family}"
        )
    edge_to_triangles: dict[tuple[int, int], list[int]] = defaultdict(list)
    for triangle_index in eligible:
        triangle = raw_triangles[triangle_index]
        for left, right in (
            (triangle[0], triangle[1]),
            (triangle[1], triangle[2]),
            (triangle[2], triangle[0]),
        ):
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
        alignment = float(normal.dot(outward))
        influences, mapping = all20.interpolate_raw_cage_influences(
            point=hit,
            body=body,
            raw_tree=raw_tree,
            raw_points=raw_points,
            raw_triangles=raw_triangles,
            group_names=group_names,
        )
        raw_triangle = int(mapping["raw_loop_triangle_index"])
        evidence = _digit_evidence(influences, expected_family)
        records.append(
            {
                "ray_hit_ordinal": ordinal,
                "ray_depth_m": depth,
                "distance_to_expected_point_m": float((hit - expected_point).length),
                "evaluated_triangle_index": int(evaluated_triangle),
                "raw_triangle_index": raw_triangle,
                "raw_component_id": int(
                    component_by_triangle.get(
                        raw_triangle, NOT_DECLARED_DIGIT_COMPONENT
                    )
                ),
                "expected_family_weight": evidence["expected_family_weight"],
                "foreign_digit_family_weight": evidence[
                    "foreign_digit_family_weight"
                ],
                "wrong_side_digit_weight": evidence["wrong_side_digit_weight"],
                "expected_family_is_dominant": evidence[
                    "expected_family_is_dominant"
                ],
                "winning_digit_family": evidence["winning_digit_family"],
                "digit_family_weights": evidence["digit_family_weights"],
                "outward_normal_alignment": alignment,
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
    target_height_m: float,
    footprint_scale: float,
    center_fraction: float,
    terminal: Vector,
    longitudinal: Vector,
    lateral: Vector,
    outward: Vector,
    evaluated_tree: BVHTree,
    body: Any,
    raw_tree: BVHTree,
    raw_points: Sequence[Vector],
    raw_triangles: Sequence[tuple[int, int, int]],
    group_names: Mapping[int, str],
    component_by_triangle: Mapping[int, int],
    expected_family: str,
) -> dict[str, Any]:
    grid = PROJECTION_GRID_SIZE
    length_m = target_height_m * float(definition["length_height_fraction"])
    width_m = target_height_m * float(definition["width_height_fraction"])
    nominal_center = terminal - longitudinal * (length_m * center_fraction)
    stacks = []
    expected_points = []
    for row in range(grid):
        along = (
            ((row / (grid - 1)) - 0.5) * length_m * footprint_scale
        )
        half_width = oval_half_width_scale(row, grid)
        for column in range(grid):
            across = (
                ((column / (grid - 1)) - 0.5)
                * width_m
                * footprint_scale
                * half_width
            )
            expected = nominal_center + longitudinal * along + lateral * across
            expected_points.append(expected)
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
                    expected_family=expected_family,
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
        kind=str(definition["kind"]),
        digit=int(definition["digit"]),
        side=str(definition["side"]),
        expected_bone=str(definition["bone"]),
        samples=[{"influences": row["influences"]} for row in selected],
        policy="final_nail_footprint",
    )
    if binding["passed"] is not True:
        raise WeightConstrainedNailProjectionError(
            "selected connected grid failed strict complete-footprint binding"
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
        raise WeightConstrainedNailProjectionError(
            "selected declared-digit grid failed local continuity"
        )
    return {
        "grid": grid,
        "length_m": length_m,
        "width_m": width_m,
        "nominal_center": nominal_center,
        "expected_points": expected_points,
        "hits": hits,
        "normals": normals,
        "selection": {
            **{
                key: value
                for key, value in selection.items()
                if key != "selected_hits"
            },
            "selected_hits": [_compact_hit(row) for row in selected],
        },
        "footprint_binding": {
            key: value for key, value in binding.items() if key != "per_sample"
        },
        "grid_locality": locality,
        "raw_ray_hit_count": sum(len(stack) for stack in stacks),
        "maximum_hits_on_one_ray": max(len(stack) for stack in stacks),
        "first_hit_winner_counts": dict(
            sorted(
                {
                    winner: sum(
                        bool(stack)
                        and stack[0].get("winning_digit_family") == winner
                        for stack in stacks
                    )
                    for winner in {
                        stack[0].get("winning_digit_family")
                        for stack in stacks
                        if stack
                    }
                }.items()
            )
        ),
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


def build_weight_constrained_nail_v1(
    *,
    body: Any,
    armature: Any,
    definition: Mapping[str, Any],
    target_height_m: float,
    name: str,
    bed_material: Any,
    free_edge_material: Any,
) -> tuple[Any, dict[str, Any]]:
    """Build one bounded correction candidate without changing body or rig."""

    if body is None or body.type != "MESH":
        raise WeightConstrainedNailProjectionError("exact body mesh is required")
    if armature is None or armature.type != "ARMATURE":
        raise WeightConstrainedNailProjectionError("exact armature is required")
    if not math.isfinite(float(target_height_m)) or target_height_m <= 0.0:
        raise WeightConstrainedNailProjectionError(
            "target height must be finite and positive"
        )
    expected_meta = parse_digit_bone(str(definition["bone"]))
    if expected_meta is None:
        raise WeightConstrainedNailProjectionError(
            "declared terminal bone is not an official digit bone"
        )
    expected_family = str(expected_meta["family"])
    body_signature_before = nails._mesh_signature(body)  # noqa: SLF001
    rig_signature_before = nails._rig_signature(armature)  # noqa: SLF001
    body_modifier_count_before = len(body.modifiers)
    raw_points, raw_triangles = all20.world_geometry(body, evaluated=False)
    evaluated_points, evaluated_triangles = all20.world_geometry(
        body, evaluated=True
    )
    raw_tree = BVHTree.FromPolygons(raw_points, raw_triangles, all_triangles=True)
    evaluated_tree = BVHTree.FromPolygons(
        evaluated_points, evaluated_triangles, all_triangles=True
    )
    group_names = all20.body_group_names(body)
    if (
        float(all20.MAXIMUM_RAW_CAGE_MAPPING_DISTANCE_M)
        != MAXIMUM_RAW_CAGE_MAPPING_DISTANCE_M
    ):
        raise WeightConstrainedNailProjectionError(
            "raw-cage mapping distance contract differs from all-20 evidence"
        )
    component_by_triangle, component_evidence = (
        declared_digit_triangle_components(
            body=body,
            raw_triangles=raw_triangles,
            expected_family=expected_family,
        )
    )
    terminal, longitudinal, lateral, outward = nails._terminal_frame(  # noqa: SLF001
        armature, str(definition["bone"]), definition["outward_hint"]
    )

    attempts = []
    accepted_nail = None
    accepted_record = None
    for footprint_scale in FOOTPRINT_SCALE_CANDIDATES:
        if accepted_nail is not None:
            break
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
                    target_height_m=float(target_height_m),
                    footprint_scale=float(footprint_scale),
                    center_fraction=float(center_fraction),
                    terminal=terminal,
                    longitudinal=longitudinal,
                    lateral=lateral,
                    outward=outward,
                    evaluated_tree=evaluated_tree,
                    body=body,
                    raw_tree=raw_tree,
                    raw_points=raw_points,
                    raw_triangles=raw_triangles,
                    group_names=group_names,
                    component_by_triangle=component_by_triangle,
                    expected_family=expected_family,
                )
                attempt.update(
                    {
                        "projection_complete": True,
                        "selection": candidate["selection"],
                        "footprint_binding": candidate["footprint_binding"],
                        "grid_locality": candidate["grid_locality"],
                        "raw_ray_hit_count": candidate["raw_ray_hit_count"],
                        "maximum_hits_on_one_ray": candidate[
                            "maximum_hits_on_one_ray"
                        ],
                        "first_hit_winner_counts": candidate[
                            "first_hit_winner_counts"
                        ],
                    }
                )
                grid = int(candidate["grid"])
                clearances = []
                for row in range(grid):
                    for column in range(grid):
                        arch = 1.0 - min(
                            1.0,
                            abs((column / (grid - 1)) - 0.5) * 2.0,
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
                    nail, outward
                )
                if winding["all_top_surface_faces_outward"] is not True:
                    raise WeightConstrainedNailProjectionError(
                        "weight-constrained top surface winding is not outward"
                    )
                nails.v1.assign_rigid_bone(nail, armature, str(definition["bone"]))
                solidify = nail.modifiers.new(
                    "Natural_Nail_Plate_Thickness_V4_Prepared", "SOLIDIFY"
                )
                solidify.thickness = NAIL_PLATE_THICKNESS_M
                solidify.offset = 1.0
                if hasattr(solidify, "use_even_offset"):
                    solidify.use_even_offset = True
                if hasattr(solidify, "use_rim"):
                    solidify.use_rim = True
                attachment = nails._attachment_report(  # noqa: SLF001
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
                    nail_points, nail_triangles = stages.world_geometry(
                        nail, evaluated=True
                    )
                    exact = stages.exact_pair_record(
                        evaluated_points,
                        evaluated_triangles,
                        nail_points,
                        nail_triangles,
                        source_nail_vertex_count=source_count,
                    )
                    body_unchanged = (
                        nails._mesh_signature(body) == body_signature_before  # noqa: SLF001
                    )
                    rig_unchanged = (
                        nails._rig_signature(armature) == rig_signature_before  # noqa: SLF001
                    )
                    shell_raw = {
                        "body_surface_space": "evaluated_rest",
                        "nail_surface_space": (
                            "evaluated_armature_then_solidify"
                        ),
                        "exact_narrow_phase_used": True,
                        "complete_shell_included": True,
                    "solidify_rim_included": bool(
                        getattr(solidify, "use_rim", True)
                    ),
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
                        "body_mesh_unchanged": body_unchanged,
                        "official_rig_unchanged": rig_unchanged,
                        "body_modifier_stack_unchanged": len(body.modifiers)
                        == body_modifier_count_before,
                        "automatic_bone_remap_performed": False,
                    }
                    lift_row = {
                        "lift_iteration": lift_iteration,
                        "additional_normal_lift_m": additional,
                        "exact_full_shell": exact,
                        "shell_gate_passed": False,
                    }
                    try:
                        shell_gate = validate_final_evaluated_shell_gate(shell_raw)
                    except NailWeightConstrainedProjectionError as exc:
                        lift_row["shell_gate_failure"] = str(exc)
                        lift_attempts.append(lift_row)
                        if (
                            float(exact["maximum_unsigned_surface_clearance_m"])
                            > MAXIMUM_FINAL_CLEARANCE_M
                        ):
                            break
                        continue
                    lift_row["shell_gate_passed"] = True
                    lift_row["shell_gate"] = shell_gate
                    lift_attempts.append(lift_row)
                    accepted_nail = nail
                    accepted_record = {
                        "method": METHOD_ID,
                        "nail_id": str(definition["nail_id"]),
                        "declared_terminal_bone": str(definition["bone"]),
                        "declared_digit_family": expected_family,
                        "footprint_scale": float(footprint_scale),
                        "center_fraction": float(center_fraction),
                        "connected_region_evidence": component_evidence,
                        "selection": candidate["selection"],
                        "footprint_binding": candidate["footprint_binding"],
                        "grid_locality": candidate["grid_locality"],
                        "top_surface_winding": winding,
                        "attachment": attachment,
                        "lift_attempts": lift_attempts,
                        "accepted_lift_iteration": lift_iteration,
                        "final_evaluated_complete_shell_gate": shell_gate,
                        "automatic_bone_remap_performed": False,
                    }
                    break
                attempt["lift_attempts"] = lift_attempts
                attempt["final_shell_passed"] = accepted_nail is nail
                attempts.append(attempt)
                if accepted_nail is nail:
                    break
                nails._remove_object_and_mesh(nail)  # noqa: SLF001
                nail = None
            except Exception as exc:
                attempt.update(
                    {
                        "projection_complete": False,
                        "failure_type": type(exc).__name__,
                        "failure": str(exc),
                    }
                )
                attempts.append(attempt)
                if nail is not None and nail.name in bpy.data.objects:
                    nails._remove_object_and_mesh(nail)  # noqa: SLF001
    if accepted_nail is None or accepted_record is None:
        raise WeightConstrainedNailProjectionError(
            "bounded weight-constrained evaluated nail projection failed: "
            + json.dumps(attempts, sort_keys=True)
        )
    accepted_record["attempts"] = attempts
    accepted_record["body_mesh_sha256_before"] = body_signature_before
    accepted_record["body_mesh_sha256_after"] = nails._mesh_signature(body)  # noqa: SLF001
    accepted_record["official_rig_sha256_before"] = rig_signature_before
    accepted_record["official_rig_sha256_after"] = nails._rig_signature(armature)  # noqa: SLF001
    accepted_record["body_modifier_count_before"] = body_modifier_count_before
    accepted_record["body_modifier_count_after"] = len(body.modifiers)
    return accepted_nail, accepted_record


__all__ = [
    "MAXIMUM_RAY_HITS",
    "METHOD_ID",
    "WeightConstrainedNailProjectionError",
    "build_weight_constrained_nail_v1",
    "declared_digit_triangle_components",
]
