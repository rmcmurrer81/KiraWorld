#!/usr/bin/env python3
"""Repaired connected-digit Kira nail projection adapter.

This is an append-only successor to v1.  It fixes the reserved-component-zero
and unbound-center defects without weakening the established complete-shell,
clearance, weight, winding, or exact-intersection gates.  It has no file-open,
save, render, runtime, or activation path.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from Core.avatar_nail_weight_constrained_projection_v1 import (
    NailWeightConstrainedProjectionError,
)
from Core.avatar_natural_nail_delivery_v3 import (
    FOOTPRINT_SCALE_CANDIDATES,
    MAXIMUM_NORMAL_LIFT_ITERATIONS,
    NORMAL_LIFT_STEP_M,
    PROJECTION_GRID_SIZE,
    oval_half_width_scale,
)
from Core.kira_blackproject_nail_topology_v1 import (
    digit_weight_evidence,
    parse_blackproject_digit_bone,
    summarize_footprint_binding,
)
from Core.kira_r24_brow_nail_component_contract_v1 import (
    MAXIMUM_FREE_EDGE_M,
    MAXIMUM_REFERENCE_CENTER_ERROR_M,
    METHOD_ID,
    select_connected_weight_constrained_grid_v2,
    validate_reference_bound_candidate,
)
from tools import blender_avatar_blackproject_weight_constrained_nail_projection_v1 as v1
from tools import blender_avatar_natural_nail_delivery_v3 as nails
from tools import blender_probe_robert_r26_all20_evaluated_nail_footprints as all20


# Every trial stays within the independently recorded 1.5 mm source-center
# boundary.  The exact source center is always attempted first.
CENTER_OFFSET_CANDIDATES_M = (
    (0.0, 0.0),
    (-0.0005, 0.0),
    (0.0005, 0.0),
    (0.0, -0.0005),
    (0.0, 0.0005),
    (-0.0010, 0.0),
    (0.0010, 0.0),
    (0.0, -0.0010),
    (0.0, 0.0010),
)


class BlackProjectWeightConstrainedNailV2Error(RuntimeError):
    pass


def _jsonable_rna_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "name") and hasattr(value, "bl_rna"):
        return {"id_type": value.__class__.__name__, "name": str(value.name)}
    if isinstance(value, (list, tuple)) or (
        hasattr(value, "__len__") and hasattr(value, "__getitem__")
    ):
        try:
            return [_jsonable_rna_value(value[index]) for index in range(len(value))]
        except (TypeError, AttributeError, ReferenceError):
            pass
    return {"type": value.__class__.__name__}


def modifier_stack_record(obj: Any) -> list[dict[str, Any]]:
    """Capture all readable RNA properties, order, and linked IDs."""

    rows = []
    for ordinal, modifier in enumerate(obj.modifiers):
        properties = {}
        for prop in modifier.bl_rna.properties:
            identifier = str(prop.identifier)
            if identifier == "rna_type":
                continue
            try:
                properties[identifier] = _jsonable_rna_value(
                    getattr(modifier, identifier)
                )
            except (AttributeError, RuntimeError, TypeError, ValueError):
                properties[identifier] = {"unreadable": True}
        rows.append(
            {
                "ordinal": ordinal,
                "name": str(modifier.name),
                "type": str(modifier.type),
                "properties": properties,
            }
        )
    return rows


def modifier_stack_sha256(obj: Any) -> str:
    encoded = json.dumps(
        modifier_stack_record(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _candidate_grid_v2(
    *,
    definition: Mapping[str, Any],
    footprint_scale: float,
    longitudinal_offset_m: float,
    lateral_offset_m: float,
    evaluated_tree: BVHTree,
    body: Any,
    raw_tree: BVHTree,
    raw_points: Sequence[Vector],
    raw_triangles: Sequence[tuple[int, int, int]],
    group_names: Mapping[int, str],
    component_by_triangle: Mapping[int, int],
) -> dict[str, Any]:
    grid = PROJECTION_GRID_SIZE
    if grid != 9:
        raise BlackProjectWeightConstrainedNailV2Error(
            "R24 nail footprint must remain a complete 9x9 grid"
        )
    length_m = float(definition["target_length_m"])
    width_m = float(definition["target_width_m"])
    reference_center = definition["reference_center_world"]
    longitudinal = definition["reference_longitudinal_world"]
    lateral = definition["reference_lateral_world"]
    outward = definition["reference_outward_world"]
    candidate_center = (
        reference_center
        + longitudinal * float(longitudinal_offset_m)
        + lateral * float(lateral_offset_m)
    )
    if float((candidate_center - reference_center).length) > MAXIMUM_REFERENCE_CENTER_ERROR_M:
        raise BlackProjectWeightConstrainedNailV2Error(
            "candidate center exceeds the exact source landmark bound"
        )

    stacks = []
    expected_points = []
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
            expected = candidate_center + longitudinal * along + lateral * across
            expected_points.append(expected)
            stacks.append(
                v1._bounded_ray_hit_stack(  # noqa: SLF001
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

    selection = select_connected_weight_constrained_grid_v2(
        stacks, center_sample_index=(grid * grid) // 2
    )
    selected = selection["selected_hits"]
    hits = [row["location"].copy() for row in selected]
    normals = [row["normal"].copy() for row in selected]
    reference_binding = validate_reference_bound_candidate(
        reference_center=tuple(map(float, reference_center)),
        candidate_center=tuple(map(float, candidate_center)),
        projected_points=[tuple(map(float, point)) for point in hits],
        expected_points=[tuple(map(float, point)) for point in expected_points],
    )
    binding = summarize_footprint_binding(
        nail_id=str(definition["nail_id"]),
        expected_bone=str(definition["bone"]),
        expected_family=str(definition["family"]),
        samples=[{"influences": row["influences"]} for row in selected],
    )
    locality = nails._grid_locality_record(  # noqa: SLF001
        points=hits,
        nominal_center=candidate_center,
        longitudinal=longitudinal,
        lateral=lateral,
        length_m=length_m,
        width_m=width_m,
        footprint_scale=footprint_scale,
        grid=grid,
    )
    if locality["locality_gate_passed"] is not True:
        raise BlackProjectWeightConstrainedNailV2Error(
            "selected connected-digit grid failed local continuity"
        )
    if int(selection["selected_raw_component_id"]) <= 0:
        raise BlackProjectWeightConstrainedNailV2Error(
            "reserved connected-component ID zero reached R24 geometry"
        )
    return {
        "grid": grid,
        "length_m": length_m,
        "width_m": width_m,
        "hits": hits,
        "normals": normals,
        "selection": {
            **{key: value for key, value in selection.items() if key != "selected_hits"},
            "selected_hits": [v1._compact_hit(row) for row in selected],  # noqa: SLF001
        },
        "footprint_binding": {
            key: value for key, value in binding.items() if key != "per_sample"
        },
        "grid_locality": locality,
        "reference_binding": reference_binding,
        "candidate_center_world_m": list(map(float, candidate_center)),
        "longitudinal_offset_m": float(longitudinal_offset_m),
        "lateral_offset_m": float(lateral_offset_m),
        # Every distal-row sample is projected onto the declared digit; this
        # preparation creates no extension beyond the surface.
        "free_edge_extension_m": 0.0,
        "maximum_free_edge_m": MAXIMUM_FREE_EDGE_M,
        "raw_ray_hit_count": sum(len(stack) for stack in stacks),
        "maximum_hits_on_one_ray": max(len(stack) for stack in stacks),
    }


def _validate_complete_shell_v2(
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
    full_modifier_sha256_before: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    exact, gate = v1._validate_complete_shell(  # noqa: SLF001
        nail=nail,
        body=body,
        armature=armature,
        evaluated_points=evaluated_points,
        evaluated_triangles=evaluated_triangles,
        source_count=source_count,
        solidify=solidify,
        body_signature_before=body_signature_before,
        rig_signature_before=rig_signature_before,
        body_modifier_count_before=len(body.modifiers),
    )
    after = modifier_stack_sha256(body)
    if after != full_modifier_sha256_before:
        raise BlackProjectWeightConstrainedNailV2Error(
            "complete body modifier stack changed during nail construction"
        )
    gate = {
        **gate,
        "full_modifier_stack_sha256_before": full_modifier_sha256_before,
        "full_modifier_stack_sha256_after": after,
        "full_modifier_stack_unchanged": True,
    }
    return exact, gate


def build_weight_constrained_nail_v2(
    *,
    body: Any,
    armature: Any,
    definition: Mapping[str, Any],
    name: str,
    bed_material: Any,
    free_edge_material: Any,
) -> tuple[Any, dict[str, Any]]:
    """Build one in-memory R24 nail and pass every repaired live gate."""

    expected_meta = parse_blackproject_digit_bone(str(definition["bone"]))
    if expected_meta is None or expected_meta["family"] != definition["family"]:
        raise BlackProjectWeightConstrainedNailV2Error(
            "declared terminal bone/family is not exact"
        )
    body_signature_before = nails._mesh_signature(body)  # noqa: SLF001
    rig_signature_before = nails._rig_signature(armature)  # noqa: SLF001
    full_modifier_sha256_before = modifier_stack_sha256(body)
    raw_points, raw_triangles = all20.world_geometry(body, evaluated=False)
    evaluated_points, evaluated_triangles = all20.world_geometry(body, evaluated=True)
    raw_tree = BVHTree.FromPolygons(raw_points, raw_triangles, all_triangles=True)
    evaluated_tree = BVHTree.FromPolygons(
        evaluated_points, evaluated_triangles, all_triangles=True
    )
    component_by_triangle, component_evidence = v1.declared_digit_triangle_components(
        body=body,
        raw_triangles=raw_triangles,
        expected_family=str(definition["family"]),
    )
    if not component_by_triangle or min(component_by_triangle.values()) <= 0:
        raise BlackProjectWeightConstrainedNailV2Error(
            "declared digit component labels are not strictly positive"
        )
    group_names = all20.body_group_names(body)
    attempts = []
    for footprint_scale in FOOTPRINT_SCALE_CANDIDATES:
        for longitudinal_offset_m, lateral_offset_m in CENTER_OFFSET_CANDIDATES_M:
            attempt: dict[str, Any] = {
                "footprint_scale": float(footprint_scale),
                "longitudinal_offset_m": float(longitudinal_offset_m),
                "lateral_offset_m": float(lateral_offset_m),
                "automatic_bone_remap_performed": False,
            }
            nail = None
            try:
                candidate = _candidate_grid_v2(
                    definition=definition,
                    footprint_scale=float(footprint_scale),
                    longitudinal_offset_m=float(longitudinal_offset_m),
                    lateral_offset_m=float(lateral_offset_m),
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
                nail = v1._create_top_plate(  # noqa: SLF001
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
                    raise BlackProjectWeightConstrainedNailV2Error(
                        "R24 nail top surface is folded or inward"
                    )
                solidify, attachment = v1._finalize_attachment(  # noqa: SLF001
                    nail, armature, str(definition["bone"])
                )
                source_count = len(nail.data.vertices)
                lift_attempts = []
                for lift_iteration in range(MAXIMUM_NORMAL_LIFT_ITERATIONS + 1):
                    additional = lift_iteration * NORMAL_LIFT_STEP_M
                    for vertex, surface, normal, base in zip(
                        nail.data.vertices,
                        candidate["hits"],
                        candidate["normals"],
                        clearances,
                    ):
                        vertex.co = surface + normal * (base + additional)
                    nail.data.update()
                    bpy.context.view_layer.update()
                    try:
                        exact, shell_gate = _validate_complete_shell_v2(
                            nail=nail,
                            body=body,
                            armature=armature,
                            evaluated_points=evaluated_points,
                            evaluated_triangles=evaluated_triangles,
                            source_count=source_count,
                            solidify=solidify,
                            body_signature_before=body_signature_before,
                            rig_signature_before=rig_signature_before,
                            full_modifier_sha256_before=full_modifier_sha256_before,
                        )
                    except (
                        NailWeightConstrainedProjectionError,
                        BlackProjectWeightConstrainedNailV2Error,
                    ) as exc:
                        lift_attempts.append(
                            {
                                "lift_iteration": lift_iteration,
                                "additional_normal_lift_m": additional,
                                "shell_gate_passed": False,
                                "failure": str(exc),
                            }
                        )
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
                    return nail, {
                        "method": METHOD_ID,
                        "nail_id": str(definition["nail_id"]),
                        "kind": str(definition["kind"]),
                        "side": str(definition["side"]),
                        "digit": int(definition["digit"]),
                        "declared_terminal_bone": str(definition["bone"]),
                        "declared_digit_family": str(definition["family"]),
                        "footprint_scale": float(footprint_scale),
                        "longitudinal_offset_m": float(longitudinal_offset_m),
                        "lateral_offset_m": float(lateral_offset_m),
                        "connected_region_evidence": component_evidence,
                        "component_id_zero_rejected": True,
                        "selection": candidate["selection"],
                        "footprint_binding": candidate["footprint_binding"],
                        "grid_locality": candidate["grid_locality"],
                        "reference_binding": candidate["reference_binding"],
                        "free_edge_extension_m": candidate["free_edge_extension_m"],
                        "maximum_free_edge_m": candidate["maximum_free_edge_m"],
                        "top_surface_winding": winding,
                        "attachment": attachment,
                        "accepted_lift_iteration": lift_iteration,
                        "final_evaluated_complete_shell_gate": shell_gate,
                        "top_surface_vertices_world_m": [
                            list(map(float, nail.matrix_world @ vertex.co))
                            for vertex in nail.data.vertices
                        ],
                        "top_surface_normals_world": [
                            list(map(float, normal)) for normal in candidate["normals"]
                        ],
                        "base_clearances_m": final_clearances,
                        "body_mesh_sha256_before": body_signature_before,
                        "body_mesh_sha256_after": nails._mesh_signature(body),  # noqa: SLF001
                        "official_rig_sha256_before": rig_signature_before,
                        "official_rig_sha256_after": nails._rig_signature(armature),  # noqa: SLF001
                        "full_modifier_stack_sha256_before": full_modifier_sha256_before,
                        "full_modifier_stack_sha256_after": modifier_stack_sha256(body),
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
    raise BlackProjectWeightConstrainedNailV2Error(
        "bounded R24 connected-digit projection failed: "
        + json.dumps(attempts, sort_keys=True)
    )


corrected_reference_definition = v1.corrected_reference_definition
declared_digit_triangle_components = v1.declared_digit_triangle_components


__all__ = [
    "BlackProjectWeightConstrainedNailV2Error",
    "CENTER_OFFSET_CANDIDATES_M",
    "METHOD_ID",
    "build_weight_constrained_nail_v2",
    "corrected_reference_definition",
    "declared_digit_triangle_components",
    "modifier_stack_record",
    "modifier_stack_sha256",
]
