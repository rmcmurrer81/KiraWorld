"""Blender adapter for twenty short, rounded, conformal natural nails.

This is a component adapter only.  It never renders, saves, exports, registers,
or activates a candidate.  A later append-only private candidate builder may call
``add_natural_nails_v3`` after the primary MakeHuman body and official rig exist.
The unchanged primary path raycasts the already-rounded footprint rather than
reshaping a fitted rectangle.  Only after that bounded path fails, a 17x17
nearest coherent local-surface fallback may run with locality, winding,
clearance, and exact-intersection gates.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any, Mapping, Sequence

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import tools.blender_profiled_adult_candidate_components as v1
import tools.blender_exact_mesh_intersections as exact_auditor
from Core.avatar_natural_nail_delivery_v3 import (
    CENTER_FRACTION_CANDIDATES,
    FOOTPRINT_SCALE_CANDIDATES,
    FREE_EDGE_MATERIAL,
    MAXIMUM_NORMAL_LIFT_ITERATIONS,
    MAXIMUM_SURFACE_CLEARANCE_M,
    METHOD_ID,
    MINIMUM_OUTWARD_NORMAL_ALIGNMENT,
    MINIMUM_RETAINED_FOOTPRINT_SCALE,
    NAIL_BED_MATERIAL,
    NAIL_PLATE_THICKNESS_M,
    NORMAL_LIFT_STEP_M,
    PROJECTION_GRID_SIZE,
    expected_nail_inventory,
    is_free_edge_face_row,
    material_contract,
    oval_half_width_scale,
    validate_attachment_measurement,
    validate_clearance_measurement,
    validate_delivery_records,
    validate_finite_points,
)


class NaturalNailDeliveryV3Error(RuntimeError):
    pass


LOCAL_SURFACE_FALLBACK_GRID_SIZE = 17
LOCAL_SURFACE_MAXIMUM_QUERY_DISTANCE_M = 0.004
LOCAL_SURFACE_CENTER_RAY_OFFSET_M = 0.025
LOCAL_SURFACE_CENTER_RAY_LENGTH_M = 0.050


def _principled_input(node: Any, *names: str) -> Any | None:
    for name in names:
        value = node.inputs.get(name)
        if value is not None:
            return value
    return None


def _natural_nail_material(name: str, contract: Mapping[str, Any]) -> Any:
    color = v1.srgb_hex_to_linear_rgba(str(contract["srgb_hex"]))
    rgba = color[:3] + (float(contract["alpha"]),)
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = rgba
    material["avatar_natural_nail_delivery_v3"] = True
    material["natural_nail_role"] = str(contract["description"])
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled is None:
        raise NaturalNailDeliveryV3Error("Principled BSDF unavailable for nail material")
    base = _principled_input(principled, "Base Color")
    roughness = _principled_input(principled, "Roughness")
    alpha = _principled_input(principled, "Alpha")
    transmission = _principled_input(principled, "Transmission Weight", "Transmission")
    subsurface = _principled_input(principled, "Subsurface Weight", "Subsurface")
    coat = _principled_input(principled, "Coat Weight", "Clearcoat")
    ior = _principled_input(principled, "IOR")
    if base is None or roughness is None or alpha is None:
        raise NaturalNailDeliveryV3Error("required nail shader inputs unavailable")
    base.default_value = rgba
    roughness.default_value = float(contract["roughness"])
    alpha.default_value = float(contract["alpha"])
    if transmission is not None:
        transmission.default_value = float(contract["transmission_weight"])
    if subsurface is not None:
        subsurface.default_value = float(contract["subsurface_weight"])
    if coat is not None:
        coat.default_value = float(contract["coat_weight"])
    if ior is not None:
        ior.default_value = 1.376
    if hasattr(material, "surface_render_method"):
        material.surface_render_method = "DITHERED"
    elif hasattr(material, "blend_method"):
        material.blend_method = "BLEND"
    if hasattr(material, "use_transparency_overlap"):
        material.use_transparency_overlap = False
    return material


def _remove_object_and_mesh(obj: Any) -> None:
    mesh = obj.data if obj is not None and obj.type == "MESH" else None
    if obj is not None:
        bpy.data.objects.remove(obj, do_unlink=True)
    if mesh is not None and mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def _mesh_signature(obj: Any) -> str:
    if obj is None or obj.type != "MESH":
        raise NaturalNailDeliveryV3Error("mesh signature requires a mesh object")
    digest = hashlib.sha256()
    digest.update(obj.data.name.encode("utf-8"))
    for vertex in obj.data.vertices:
        digest.update(struct.pack("<3d", *(float(value) for value in vertex.co)))
    for polygon in obj.data.polygons:
        digest.update(struct.pack("<I", len(polygon.vertices)))
        for index in polygon.vertices:
            digest.update(struct.pack("<I", int(index)))
    return digest.hexdigest()


def _rig_signature(armature: Any) -> str:
    if armature is None or armature.type != "ARMATURE":
        raise NaturalNailDeliveryV3Error("rig signature requires an armature")
    digest = hashlib.sha256()
    for bone in sorted(armature.data.bones, key=lambda item: item.name):
        digest.update(bone.name.encode("utf-8"))
        digest.update((bone.parent.name if bone.parent else "").encode("utf-8"))
        digest.update(struct.pack("<3d", *(float(value) for value in bone.head_local)))
        digest.update(struct.pack("<3d", *(float(value) for value in bone.tail_local)))
        digest.update(struct.pack("<?", bool(bone.use_deform)))
    return digest.hexdigest()


def _terminal_frame(
    armature: Any,
    bone_name: str,
    outward_hint: Sequence[float],
) -> tuple[Vector, Vector, Vector, Vector]:
    bone = armature.data.bones.get(str(bone_name))
    if bone is None:
        raise NaturalNailDeliveryV3Error(f"terminal nail bone missing: {bone_name}")
    direction = (
        armature.matrix_world.to_3x3() @ (bone.tail_local - bone.head_local)
    ).normalized()
    outward = Vector(tuple(float(value) for value in outward_hint)).normalized()
    longitudinal = direction - outward * direction.dot(outward)
    if longitudinal.length <= 1.0e-8:
        raise NaturalNailDeliveryV3Error(f"nail tangent degenerate: {bone_name}")
    longitudinal.normalize()
    lateral = outward.cross(longitudinal)
    if lateral.length <= 1.0e-8:
        raise NaturalNailDeliveryV3Error(f"nail lateral frame degenerate: {bone_name}")
    lateral.normalize()
    terminal = armature.matrix_world @ bone.tail_local
    return terminal, longitudinal, lateral, outward


def _outward_grid_faces(grid: int) -> list[tuple[int, int, int, int]]:
    # longitudinal x lateral points along the outward surface hint.  This winding
    # is intentional so the small Solidify thickness expands away from skin.
    return [
        (
            row * grid + column,
            (row + 1) * grid + column,
            (row + 1) * grid + column + 1,
            row * grid + column + 1,
        )
        for row in range(grid - 1)
        for column in range(grid - 1)
    ]


def _world_surface_geometry(
    obj: Any,
) -> tuple[list[Vector], list[tuple[int, int, int]]]:
    mesh = obj.data
    mesh.calc_loop_triangles()
    points = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
    triangles = [
        tuple(int(value) for value in triangle.vertices)
        for triangle in mesh.loop_triangles
    ]
    if not points or not triangles:
        raise NaturalNailDeliveryV3Error("body surface geometry is empty")
    return points, triangles


def _exact_cross_intersection_record(
    *,
    body_points: Sequence[Vector],
    body_triangles: Sequence[tuple[int, int, int]],
    body_tree: BVHTree,
    nail: Any,
) -> dict[str, Any]:
    nail.data.calc_loop_triangles()
    nail_points = [nail.matrix_world @ vertex.co for vertex in nail.data.vertices]
    nail_triangles = [
        tuple(int(value) for value in triangle.vertices)
        for triangle in nail.data.loop_triangles
    ]
    nail_tree = BVHTree.FromPolygons(
        nail_points,
        nail_triangles,
        all_triangles=True,
    )
    low = Vector(
        tuple(min(float(point[axis]) for point in body_points) for axis in range(3))
    )
    high = Vector(
        tuple(max(float(point[axis]) for point in body_points) for axis in range(3))
    )
    tolerance = max(1.0e-10, float((high - low).length) * 1.0e-8)
    raw_pairs = sorted(body_tree.overlap(nail_tree))
    classification_counts: dict[str, int] = {}
    genuine_pairs: list[list[int]] = []
    for body_index, nail_index in raw_pairs:
        result = exact_auditor.classify_triangle_pair(
            tuple(body_points[index] for index in body_triangles[body_index]),
            tuple(nail_points[index] for index in nail_triangles[nail_index]),
            linear_tolerance=tolerance,
        )
        classification = str(result["classification"])
        classification_counts[classification] = (
            classification_counts.get(classification, 0) + 1
        )
        if result.get("genuine_penetration") is True:
            genuine_pairs.append([int(body_index), int(nail_index)])
    return {
        "method": "actual_loop_triangles_BVH_plus_exact_triangle_narrow_phase",
        "raw_bvhtree_pair_count": len(raw_pairs),
        "classification_counts": classification_counts,
        "exact_genuine_penetration_pair_count": len(genuine_pairs),
        "exact_genuine_penetration_pairs": genuine_pairs,
        "linear_tolerance_m": tolerance,
        "raw_bvhtree_pairs_are_not_the_pass_gate": True,
    }


def _grid_locality_record(
    *,
    points: Sequence[Vector],
    nominal_center: Vector,
    longitudinal: Vector,
    lateral: Vector,
    length_m: float,
    width_m: float,
    footprint_scale: float,
    grid: int,
) -> dict[str, Any]:
    if len(points) != grid * grid:
        return {
            "grid_sample_count": len(points),
            "expected_grid_sample_count": grid * grid,
            "one_connected_grid_shell_by_construction": False,
            "locality_gate_passed": False,
            "failure_reason": "incomplete_grid",
        }
    longitudinal_edges: list[float] = []
    lateral_edges: list[float] = []
    for row in range(grid):
        for column in range(grid):
            index = row * grid + column
            if row + 1 < grid:
                longitudinal_edges.append(
                    float((points[index] - points[index + grid]).length)
                )
            if column + 1 < grid:
                lateral_edges.append(
                    float((points[index] - points[index + 1]).length)
                )
    all_edges = longitudinal_edges + lateral_edges
    ordered = sorted(all_edges)
    expected_longitudinal_step = length_m * footprint_scale / (grid - 1)
    expected_lateral_step = width_m * footprint_scale / (grid - 1)
    maximum_allowed_neighbor_edge = max(
        0.00075,
        expected_longitudinal_step * 2.8,
        expected_lateral_step * 3.5,
    )
    centroid = sum(points, Vector()) / len(points)
    relative = [point - nominal_center for point in points]
    longitudinal_values = [float(value.dot(longitudinal)) for value in relative]
    lateral_values = [float(value.dot(lateral)) for value in relative]
    maximum_neighbor_edge = max(all_edges)
    return {
        "grid_sample_count": len(points),
        "expected_grid_sample_count": grid * grid,
        "one_connected_grid_shell_by_construction": True,
        "maximum_longitudinal_neighbor_edge_m": max(longitudinal_edges),
        "maximum_lateral_neighbor_edge_m": max(lateral_edges),
        "maximum_neighbor_edge_m": maximum_neighbor_edge,
        "median_neighbor_edge_m": ordered[len(ordered) // 2],
        "maximum_allowed_neighbor_edge_m": maximum_allowed_neighbor_edge,
        "centroid_to_nominal_center_m": float((centroid - nominal_center).length),
        "longitudinal_span_m": max(longitudinal_values)
        - min(longitudinal_values),
        "lateral_span_m": max(lateral_values) - min(lateral_values),
        "locality_gate_passed": maximum_neighbor_edge
        <= maximum_allowed_neighbor_edge,
        "failure_reason": (
            ""
            if maximum_neighbor_edge <= maximum_allowed_neighbor_edge
            else "discontinuous_or_wrong_surface_grid_neighbor"
        ),
    }


def _top_surface_winding_record(nail: Any, outward: Vector) -> dict[str, Any]:
    nail.data.update(calc_edges=True)
    alignments = [
        float((nail.matrix_world.to_3x3() @ polygon.normal).normalized().dot(outward))
        for polygon in nail.data.polygons
    ]
    non_outward = sum(value <= 0.0 for value in alignments)
    return {
        "minimum_outward_face_normal_alignment": min(alignments),
        "maximum_outward_face_normal_alignment": max(alignments),
        "non_outward_face_count": int(non_outward),
        "all_top_surface_faces_outward": non_outward == 0,
    }


def _nearest_coherent_local_surface_fallback(
    *,
    name: str,
    body_points: Sequence[Vector],
    body_triangles: Sequence[tuple[int, int, int]],
    body_tree: BVHTree,
    terminal: Vector,
    longitudinal_hint: Vector,
    outward_hint: Vector,
    length_m: float,
    width_m: float,
    bed_material: Any,
    free_edge_material: Any,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], int, int]:
    grid = LOCAL_SURFACE_FALLBACK_GRID_SIZE
    faces = _outward_grid_faces(grid)
    attempts: list[dict[str, Any]] = []
    center_raycast_count = 0
    nearest_query_count = 0
    for center_fraction in CENTER_FRACTION_CANDIDATES:
        nominal_center = terminal - longitudinal_hint * (
            length_m * float(center_fraction)
        )
        center_origin = nominal_center + outward_hint * (
            LOCAL_SURFACE_CENTER_RAY_OFFSET_M
        )
        center_raycast_count += 1
        center_hit, center_normal, center_face, center_distance = body_tree.ray_cast(
            center_origin,
            -outward_hint,
            LOCAL_SURFACE_CENTER_RAY_LENGTH_M,
        )
        if center_hit is None or center_normal is None:
            attempts.append(
                {
                    "projection_method": "nearest_coherent_local_surface_fallback",
                    "center_fraction_from_terminal": float(center_fraction),
                    "projection_complete": False,
                    "fit_passed": False,
                    "failure_reason": "local_surface_center_ray_miss",
                }
            )
            continue
        if center_normal.dot(outward_hint) < 0.0:
            center_normal = -center_normal
        center_normal.normalize()
        local_longitudinal = longitudinal_hint - center_normal * (
            longitudinal_hint.dot(center_normal)
        )
        if local_longitudinal.length <= 1.0e-8:
            attempts.append(
                {
                    "projection_method": "nearest_coherent_local_surface_fallback",
                    "center_fraction_from_terminal": float(center_fraction),
                    "projection_complete": False,
                    "fit_passed": False,
                    "failure_reason": "local_longitudinal_tangent_degenerate",
                }
            )
            continue
        local_longitudinal.normalize()
        if local_longitudinal.dot(longitudinal_hint) < 0.0:
            local_longitudinal = -local_longitudinal
        local_lateral = center_normal.cross(local_longitudinal)
        if local_lateral.length <= 1.0e-8:
            attempts.append(
                {
                    "projection_method": "nearest_coherent_local_surface_fallback",
                    "center_fraction_from_terminal": float(center_fraction),
                    "projection_complete": False,
                    "fit_passed": False,
                    "failure_reason": "local_lateral_tangent_degenerate",
                }
            )
            continue
        local_lateral.normalize()

        for footprint_scale in FOOTPRINT_SCALE_CANDIDATES:
            hits: list[Vector] = []
            normals: list[Vector] = []
            base_clearances: list[float] = []
            complete = True
            failure_reason = ""
            minimum_alignment = 1.0
            maximum_query_distance = 0.0
            for row in range(grid):
                along = (
                    ((row / (grid - 1)) - 0.5)
                    * length_m
                    * float(footprint_scale)
                )
                row_width_scale = oval_half_width_scale(row, grid)
                for column in range(grid):
                    across_fraction = (column / (grid - 1)) - 0.5
                    across = (
                        across_fraction
                        * width_m
                        * float(footprint_scale)
                        * row_width_scale
                    )
                    expected = (
                        center_hit
                        + local_longitudinal * along
                        + local_lateral * across
                    )
                    nearest_query_count += 1
                    hit, normal, _face, distance = body_tree.find_nearest(
                        expected,
                        LOCAL_SURFACE_MAXIMUM_QUERY_DISTANCE_M,
                    )
                    if hit is None or normal is None:
                        complete = False
                        failure_reason = f"nearest_local_surface_miss_{row}_{column}"
                        break
                    maximum_query_distance = max(
                        maximum_query_distance,
                        float(distance),
                    )
                    if normal.dot(center_normal) < 0.0:
                        normal = -normal
                    normal.normalize()
                    alignment = float(normal.dot(center_normal))
                    minimum_alignment = min(minimum_alignment, alignment)
                    if alignment < MINIMUM_OUTWARD_NORMAL_ALIGNMENT:
                        complete = False
                        failure_reason = f"local_surface_discontinuity_{row}_{column}"
                        break
                    transverse_arch = 1.0 - min(
                        1.0, abs(across_fraction) * 2.0
                    ) ** 2
                    hits.append(hit.copy())
                    normals.append(normal.copy())
                    base_clearances.append(
                        0.000055 + 0.000055 * transverse_arch
                    )
                if not complete:
                    break
            attempt: dict[str, Any] = {
                "projection_method": "nearest_coherent_local_surface_fallback",
                "footprint_scale": float(footprint_scale),
                "center_fraction_from_terminal": float(center_fraction),
                "projection_complete": complete,
                "projected_sample_count": len(hits),
                "minimum_local_normal_alignment": minimum_alignment,
                "maximum_nearest_query_distance_m": maximum_query_distance,
                "maximum_allowed_nearest_query_distance_m": (
                    LOCAL_SURFACE_MAXIMUM_QUERY_DISTANCE_M
                ),
                "center_surface_face_index": int(center_face),
                "center_ray_distance_m": float(center_distance),
                "failure_reason": failure_reason,
            }
            if not complete:
                attempt["fit_passed"] = False
                attempts.append(attempt)
                continue

            locality = _grid_locality_record(
                points=hits,
                nominal_center=center_hit,
                longitudinal=local_longitudinal,
                lateral=local_lateral,
                length_m=length_m,
                width_m=width_m,
                footprint_scale=float(footprint_scale),
                grid=grid,
            )
            attempt["grid_locality"] = locality
            if locality["locality_gate_passed"] is not True:
                attempt["fit_passed"] = False
                attempt["failure_reason"] = "generated_grid_locality_failed"
                attempts.append(attempt)
                continue

            mesh = bpy.data.meshes.new(name)
            mesh.from_pydata(
                [
                    tuple(hit + normal * clearance)
                    for hit, normal, clearance in zip(
                        hits, normals, base_clearances
                    )
                ],
                [],
                faces,
            )
            mesh.update(calc_edges=True)
            nail = bpy.data.objects.new(name, mesh)
            bpy.context.collection.objects.link(nail)
            mesh.materials.append(bed_material)
            mesh.materials.append(free_edge_material)
            free_edge_face_count = 0
            for polygon in mesh.polygons:
                polygon.use_smooth = True
                face_row = int(polygon.index) // (grid - 1)
                polygon.material_index = (
                    1 if is_free_edge_face_row(face_row, grid) else 0
                )
                free_edge_face_count += int(polygon.material_index == 1)

            try:
                winding = _top_surface_winding_record(nail, center_normal)
            except Exception:
                _remove_object_and_mesh(nail)
                raise
            attempt["top_surface_winding"] = winding
            if winding["all_top_surface_faces_outward"] is not True:
                attempt["fit_passed"] = False
                attempt["failure_reason"] = "non_outward_or_folded_top_surface"
                attempts.append(attempt)
                _remove_object_and_mesh(nail)
                continue

            accepted_lift = -1
            clearance: dict[str, Any] | None = None
            exact: dict[str, Any] | None = None
            initial_clearance: dict[str, Any] | None = None
            initial_exact: dict[str, Any] | None = None
            for lift_iteration in range(MAXIMUM_NORMAL_LIFT_ITERATIONS + 1):
                additional_lift = lift_iteration * NORMAL_LIFT_STEP_M
                for vertex, hit, normal, base_clearance in zip(
                    nail.data.vertices,
                    hits,
                    normals,
                    base_clearances,
                ):
                    vertex.co = hit + normal * (
                        base_clearance + additional_lift
                    )
                nail.data.update()
                try:
                    clearance = v1._body_clearance_record(  # noqa: SLF001
                        body_tree,
                        [nail],
                    )
                    exact = _exact_cross_intersection_record(
                        body_points=body_points,
                        body_triangles=body_triangles,
                        body_tree=body_tree,
                        nail=nail,
                    )
                except Exception:
                    _remove_object_and_mesh(nail)
                    raise
                if lift_iteration == 0:
                    initial_clearance = dict(clearance)
                    initial_exact = dict(exact)
                try:
                    validate_clearance_measurement(
                        minimum_m=float(
                            clearance[
                                "minimum_unsigned_body_surface_clearance_m"
                            ]
                        ),
                        maximum_m=float(
                            clearance[
                                "maximum_unsigned_body_surface_clearance_m"
                            ]
                        ),
                        overlap_count=int(
                            exact["exact_genuine_penetration_pair_count"]
                        ),
                    )
                except ValueError:
                    if (
                        float(
                            clearance[
                                "maximum_unsigned_body_surface_clearance_m"
                            ]
                        )
                        > MAXIMUM_SURFACE_CLEARANCE_M
                    ):
                        break
                    continue
                if float(footprint_scale) < MINIMUM_RETAINED_FOOTPRINT_SCALE:
                    break
                accepted_lift = lift_iteration
                break

            attempt.update(
                {
                    "initial_clearance": initial_clearance,
                    "initial_exact_intersections": initial_exact,
                    "final_clearance": clearance,
                    "final_exact_intersections": exact,
                    "adaptive_normal_lift_iteration_count": max(
                        0, accepted_lift
                    ),
                    "fit_passed": accepted_lift >= 0,
                }
            )
            attempts.append(attempt)
            if (
                accepted_lift >= 0
                and clearance is not None
                and exact is not None
            ):
                return (
                    {
                        "nail": nail,
                        "grid": grid,
                        "clearance": clearance,
                        "overlap_count": int(
                            exact["exact_genuine_penetration_pair_count"]
                        ),
                        "broad_overlap_count": int(
                            exact["raw_bvhtree_pair_count"]
                        ),
                        "exact_intersections": exact,
                        "footprint_scale": float(footprint_scale),
                        "center_fraction": float(center_fraction),
                        "minimum_alignment": minimum_alignment,
                        "lift_iteration": accepted_lift,
                        "free_edge_face_count": free_edge_face_count,
                        "initial_clearance": initial_clearance,
                        "initial_overlap_count": int(
                            (initial_exact or {}).get(
                                "exact_genuine_penetration_pair_count",
                                -1,
                            )
                        ),
                        "measurement_longitudinal": local_longitudinal,
                        "measurement_lateral": local_lateral,
                        "measurement_outward": center_normal,
                        "projection_query_mode": (
                            "nearest_coherent_local_surface_fallback"
                        ),
                        "grid_locality": locality,
                        "top_surface_winding": winding,
                        "maximum_nearest_query_distance_m": (
                            maximum_query_distance
                        ),
                        "center_surface_face_index": int(center_face),
                    },
                    attempts,
                    center_raycast_count,
                    nearest_query_count,
                )
            _remove_object_and_mesh(nail)
    return None, attempts, center_raycast_count, nearest_query_count


def _attachment_report(nail: Any, armature: Any, bone_name: str) -> dict[str, Any]:
    group = nail.vertex_groups.get(bone_name)
    group_index = group.index if group is not None else -1
    unit_weighted = group is not None and all(
        len(vertex.groups) == 1
        and int(vertex.groups[0].group) == group_index
        and abs(float(vertex.groups[0].weight) - 1.0) <= 1.0e-7
        for vertex in nail.data.vertices
    )
    armature_modifiers = [
        modifier for modifier in nail.modifiers if modifier.type == "ARMATURE"
    ]
    modifier_targets_rig = (
        len(armature_modifiers) == 1 and armature_modifiers[0].object == armature
    )
    report = validate_attachment_measurement(
        expected_bone=bone_name,
        actual_bone=bone_name if group is not None else "",
        parent_is_exact_armature=nail.parent == armature,
        armature_modifier_targets_exact_rig=modifier_targets_rig,
        every_vertex_has_unit_terminal_bone_weight=unit_weighted,
    )
    report.update(
        {
            "armature_modifier": (
                armature_modifiers[0].name if modifier_targets_rig else ""
            ),
            "single_vertex_group_count": len(nail.vertex_groups),
            "follow_clearance_rule": (
                "Re-audit evaluated body/nail clearance in every accepted candidate "
                "pose; this component proves exact rigid terminal-bone following."
            ),
        }
    )
    return report


def _projected_oval_nail_plate(
    *,
    name: str,
    nail_id: str,
    body_points: Sequence[Vector],
    body_triangles: Sequence[tuple[int, int, int]],
    body_tree: BVHTree,
    armature: Any,
    bone_name: str,
    outward_hint: Sequence[float],
    length_m: float,
    width_m: float,
    target_height_m: float,
    bed_material: Any,
    free_edge_material: Any,
) -> tuple[Any, dict[str, Any]]:
    terminal, longitudinal, lateral, outward = _terminal_frame(
        armature, bone_name, outward_hint
    )
    grid = PROJECTION_GRID_SIZE
    faces = _outward_grid_faces(grid)
    attempts: list[dict[str, Any]] = []
    total_raycast_count = 0
    total_nearest_query_count = 0
    primary_attempt_count = 0
    fallback_attempt_count = 0
    accepted: dict[str, Any] | None = None

    for footprint_scale in FOOTPRINT_SCALE_CANDIDATES:
        if accepted is not None:
            break
        for center_fraction in CENTER_FRACTION_CANDIDATES:
            nominal_center = terminal - longitudinal * (length_m * center_fraction)
            hits: list[Vector] = []
            normals: list[Vector] = []
            base_clearances: list[float] = []
            complete = True
            failure_reason = ""
            minimum_alignment = 1.0
            for row in range(grid):
                along = (
                    ((row / (grid - 1)) - 0.5) * length_m * footprint_scale
                )
                row_width_scale = oval_half_width_scale(row, grid)
                for column in range(grid):
                    across_fraction = (column / (grid - 1)) - 0.5
                    across = (
                        across_fraction
                        * width_m
                        * footprint_scale
                        * row_width_scale
                    )
                    expected = nominal_center + longitudinal * along + lateral * across
                    origin = expected + outward * 0.025
                    total_raycast_count += 1
                    hit, normal, _face, _distance = body_tree.ray_cast(
                        origin, -outward, 0.050
                    )
                    if hit is None or normal is None:
                        complete = False
                        failure_reason = f"surface_projection_miss_{row}_{column}"
                        break
                    if normal.dot(outward) < 0.0:
                        normal = -normal
                    normal.normalize()
                    alignment = float(normal.dot(outward))
                    minimum_alignment = min(minimum_alignment, alignment)
                    if alignment < MINIMUM_OUTWARD_NORMAL_ALIGNMENT:
                        complete = False
                        failure_reason = f"outward_normal_alignment_{row}_{column}"
                        break
                    transverse_arch = 1.0 - min(1.0, abs(across_fraction) * 2.0) ** 2
                    hits.append(hit.copy())
                    normals.append(normal.copy())
                    base_clearances.append(0.000055 + 0.000055 * transverse_arch)
                if not complete:
                    break
            attempt: dict[str, Any] = {
                "footprint_scale": float(footprint_scale),
                "center_fraction_from_terminal": float(center_fraction),
                "projection_complete": complete,
                "projected_sample_count": len(hits),
                "minimum_outward_normal_alignment": minimum_alignment,
                "failure_reason": failure_reason,
            }
            primary_attempt_count += 1
            if not complete:
                attempts.append(attempt)
                continue

            mesh = bpy.data.meshes.new(name)
            mesh.from_pydata(
                [
                    tuple(hit + normal * clearance)
                    for hit, normal, clearance in zip(hits, normals, base_clearances)
                ],
                [],
                faces,
            )
            mesh.update(calc_edges=True)
            nail = bpy.data.objects.new(name, mesh)
            bpy.context.collection.objects.link(nail)
            mesh.materials.append(bed_material)
            mesh.materials.append(free_edge_material)
            free_edge_face_count = 0
            for polygon in mesh.polygons:
                polygon.use_smooth = True
                face_row = int(polygon.index) // (grid - 1)
                polygon.material_index = 1 if is_free_edge_face_row(face_row, grid) else 0
                free_edge_face_count += int(polygon.material_index == 1)

            initial_clearance: dict[str, Any] | None = None
            clearance: dict[str, Any] | None = None
            initial_overlap_count = -1
            overlap_count = -1
            accepted_lift = -1
            for lift_iteration in range(MAXIMUM_NORMAL_LIFT_ITERATIONS + 1):
                additional_lift = lift_iteration * NORMAL_LIFT_STEP_M
                for vertex, hit, normal, base_clearance in zip(
                    nail.data.vertices, hits, normals, base_clearances
                ):
                    vertex.co = hit + normal * (base_clearance + additional_lift)
                nail.data.update()
                clearance = v1._body_clearance_record(body_tree, [nail])  # noqa: SLF001
                overlap_count = len(
                    body_tree.overlap(v1._world_surface_bvh(nail))  # noqa: SLF001
                )
                if lift_iteration == 0:
                    initial_clearance = dict(clearance)
                    initial_overlap_count = overlap_count
                try:
                    validate_clearance_measurement(
                        minimum_m=float(
                            clearance["minimum_unsigned_body_surface_clearance_m"]
                        ),
                        maximum_m=float(
                            clearance["maximum_unsigned_body_surface_clearance_m"]
                        ),
                        overlap_count=overlap_count,
                    )
                except ValueError:
                    if (
                        float(
                            clearance["maximum_unsigned_body_surface_clearance_m"]
                        )
                        > MAXIMUM_SURFACE_CLEARANCE_M
                    ):
                        break
                    continue
                if footprint_scale < MINIMUM_RETAINED_FOOTPRINT_SCALE:
                    break
                accepted_lift = lift_iteration
                break
            attempt.update(
                {
                    "initial_clearance": initial_clearance,
                    "initial_body_surface_triangle_overlap_count": initial_overlap_count,
                    "final_clearance": clearance,
                    "final_body_surface_triangle_overlap_count": overlap_count,
                    "adaptive_normal_lift_iteration_count": max(0, accepted_lift),
                    "fit_passed": accepted_lift >= 0,
                }
            )
            attempts.append(attempt)
            if accepted_lift >= 0:
                accepted = {
                    "nail": nail,
                    "grid": grid,
                    "clearance": clearance,
                    "overlap_count": overlap_count,
                    "broad_overlap_count": overlap_count,
                    "exact_intersections": None,
                    "footprint_scale": float(footprint_scale),
                    "center_fraction": float(center_fraction),
                    "minimum_alignment": minimum_alignment,
                    "lift_iteration": accepted_lift,
                    "free_edge_face_count": free_edge_face_count,
                    "initial_clearance": initial_clearance,
                    "initial_overlap_count": initial_overlap_count,
                    "measurement_longitudinal": longitudinal,
                    "measurement_lateral": lateral,
                    "measurement_outward": outward,
                    "projection_query_mode": "first_hit_outward_raycast_primary",
                    "grid_locality": None,
                    "top_surface_winding": None,
                    "maximum_nearest_query_distance_m": None,
                    "center_surface_face_index": None,
                }
                break
            _remove_object_and_mesh(nail)

    if accepted is None:
        (
            accepted,
            fallback_attempts,
            fallback_center_raycast_count,
            fallback_nearest_query_count,
        ) = _nearest_coherent_local_surface_fallback(
            name=name,
            body_points=body_points,
            body_triangles=body_triangles,
            body_tree=body_tree,
            terminal=terminal,
            longitudinal_hint=longitudinal,
            outward_hint=outward,
            length_m=length_m,
            width_m=width_m,
            bed_material=bed_material,
            free_edge_material=free_edge_material,
        )
        attempts.extend(fallback_attempts)
        fallback_attempt_count = len(fallback_attempts)
        total_raycast_count += fallback_center_raycast_count
        total_nearest_query_count += fallback_nearest_query_count

    if accepted is None:
        raise NaturalNailDeliveryV3Error(
            f"bounded oval conformal nail projection failed: {bone_name};"
            f"attempts={json.dumps(attempts, sort_keys=True)}"
        )

    nail = accepted["nail"]
    accepted_grid = int(accepted["grid"])
    measurement_longitudinal = accepted["measurement_longitudinal"]
    measurement_lateral = accepted["measurement_lateral"]
    measurement_outward = accepted["measurement_outward"]
    points = [nail.matrix_world @ vertex.co for vertex in nail.data.vertices]
    finite = validate_finite_points(tuple(tuple(point) for point in points))
    longitudinal_values = [
        float(point.dot(measurement_longitudinal)) for point in points
    ]
    lateral_values = [float(point.dot(measurement_lateral)) for point in points]
    plate_length = max(longitudinal_values) - min(longitudinal_values)
    plate_width = max(lateral_values) - min(lateral_values)
    face_normal_alignments = [
        float(
            (nail.matrix_world.to_3x3() @ polygon.normal)
            .normalized()
            .dot(measurement_outward)
        )
        for polygon in nail.data.polygons
    ]
    minimum_face_normal_alignment = min(face_normal_alignments)
    if minimum_face_normal_alignment <= 0.0:
        _remove_object_and_mesh(nail)
        raise NaturalNailDeliveryV3Error(
            f"nail top-surface winding is not outward: {bone_name}"
        )

    v1.assign_rigid_bone(nail, armature, bone_name)
    solidify = nail.modifiers.new("Natural_Nail_Plate_Thickness_V3", "SOLIDIFY")
    solidify.thickness = NAIL_PLATE_THICKNESS_M
    solidify.offset = 1.0
    if hasattr(solidify, "use_even_offset"):
        solidify.use_even_offset = True
    if hasattr(solidify, "use_rim"):
        solidify.use_rim = True
    attachment = _attachment_report(nail, armature, bone_name)
    clearance = accepted["clearance"]
    if clearance is None:
        _remove_object_and_mesh(nail)
        raise NaturalNailDeliveryV3Error("accepted nail lost clearance evidence")
    record = {
        "nail_id": nail_id,
        "object": nail.name,
        "bone": bone_name,
        "target_height_m": float(target_height_m),
        "projection_grid_dimensions": [accepted_grid, accepted_grid],
        "vertex_count": len(nail.data.vertices),
        "polygon_count": len(nail.data.polygons),
        "projection_raycast_count": total_raycast_count,
        "projection_nearest_query_count": total_nearest_query_count,
        "projection_attempt_count": len(attempts),
        "primary_projection_attempt_count": primary_attempt_count,
        "fallback_projection_attempt_count": fallback_attempt_count,
        "projection_attempts": attempts,
        "projection_query_mode": accepted["projection_query_mode"],
        "retained_footprint_scale": accepted["footprint_scale"],
        "projection_center_fraction_from_terminal": accepted["center_fraction"],
        "minimum_outward_projection_normal_alignment": accepted[
            "minimum_alignment"
        ],
        "minimum_outward_face_normal_alignment": minimum_face_normal_alignment,
        "adaptive_normal_lift_iteration_count": accepted["lift_iteration"],
        "additional_normal_lift_m": accepted["lift_iteration"]
        * NORMAL_LIFT_STEP_M,
        "minimum_clearance_m": float(
            clearance["minimum_unsigned_body_surface_clearance_m"]
        ),
        "maximum_clearance_m": float(
            clearance["maximum_unsigned_body_surface_clearance_m"]
        ),
        "body_surface_triangle_overlap_count": int(accepted["overlap_count"]),
        "broad_body_surface_triangle_overlap_count": int(
            accepted["broad_overlap_count"]
        ),
        "exact_intersections": accepted["exact_intersections"],
        "grid_locality": accepted["grid_locality"],
        "top_surface_winding": accepted["top_surface_winding"],
        "maximum_nearest_query_distance_m": accepted[
            "maximum_nearest_query_distance_m"
        ],
        "center_surface_face_index": accepted["center_surface_face_index"],
        "initial_clearance": accepted["initial_clearance"],
        "initial_body_surface_triangle_overlap_count": accepted[
            "initial_overlap_count"
        ],
        "plate_length_m": plate_length,
        "plate_width_m": plate_width,
        "plate_aspect_ratio": plate_length / plate_width,
        "rounded_oval_silhouette": True,
        "proximal_half_width_scale": oval_half_width_scale(0, accepted_grid),
        "widest_half_width_scale": max(
            oval_half_width_scale(index, accepted_grid)
            for index in range(accepted_grid)
        ),
        "distal_half_width_scale": oval_half_width_scale(
            accepted_grid - 1, accepted_grid
        ),
        "free_edge_face_count": int(accepted["free_edge_face_count"]),
        "nail_bed_face_count": len(nail.data.polygons)
        - int(accepted["free_edge_face_count"]),
        "outward_only_plate_thickness_m": NAIL_PLATE_THICKNESS_M,
        **finite,
        **attachment,
    }
    return nail, record


def add_natural_nails_v3(
    *,
    body: Any,
    armature: Any,
    target_height_m: float,
    candidate_id: str,
) -> tuple[list[Any], dict[str, Any]]:
    """Add only the detachable nail presentation components to an existing body."""

    if body is None or body.type != "MESH":
        raise NaturalNailDeliveryV3Error("natural nails require the exact body mesh")
    if armature is None or armature.type != "ARMATURE":
        raise NaturalNailDeliveryV3Error("natural nails require the exact official rig")
    if not math.isfinite(float(target_height_m)) or float(target_height_m) <= 0.0:
        raise NaturalNailDeliveryV3Error("target height must be finite and positive")
    if not str(candidate_id).strip():
        raise NaturalNailDeliveryV3Error("candidate id is required")

    body_signature_before = _mesh_signature(body)
    rig_signature_before = _rig_signature(armature)
    body_modifier_count_before = len(body.modifiers)
    body_tree = v1._world_surface_bvh(body)  # noqa: SLF001
    body_points, body_triangles = _world_surface_geometry(body)
    bed_material = _natural_nail_material(
        f"{candidate_id}_Natural_Nail_Bed_V3", NAIL_BED_MATERIAL
    )
    free_edge_material = _natural_nail_material(
        f"{candidate_id}_Natural_Nail_Free_Edge_V3", FREE_EDGE_MATERIAL
    )
    objects: list[Any] = []
    records: list[dict[str, Any]] = []
    try:
        for definition in expected_nail_inventory():
            nail, record = _projected_oval_nail_plate(
                name=f"{candidate_id}_{definition['nail_id']}_natural_v3",
                nail_id=str(definition["nail_id"]),
                body_points=body_points,
                body_triangles=body_triangles,
                body_tree=body_tree,
                armature=armature,
                bone_name=str(definition["bone"]),
                outward_hint=definition["outward_hint"],
                length_m=float(target_height_m)
                * float(definition["length_height_fraction"]),
                width_m=float(target_height_m)
                * float(definition["width_height_fraction"]),
                target_height_m=float(target_height_m),
                bed_material=bed_material,
                free_edge_material=free_edge_material,
            )
            nail["candidate_id"] = str(candidate_id)
            nail["private_owner_review_only"] = True
            nail["inactive_candidate"] = True
            nail["runtime_activation_allowed"] = False
            nail["nail_component"] = True
            nail["avatar_natural_nail_delivery_v3"] = True
            nail["rounded_oval_silhouette"] = True
            nail["translucent_natural_pink_bed"] = True
            nail["softly_paler_free_edge"] = True
            nail["visual_pose_clearance_review_required"] = True
            objects.append(nail)
            records.append(
                {
                    **record,
                    "kind": str(definition["kind"]),
                    "side": str(definition["side"]),
                    "digit": int(definition["digit"]),
                }
            )
        contract_report = validate_delivery_records(records)
        body_signature_after = _mesh_signature(body)
        rig_signature_after = _rig_signature(armature)
        if body_signature_after != body_signature_before:
            raise NaturalNailDeliveryV3Error("primary body mesh changed during nail authoring")
        if rig_signature_after != rig_signature_before:
            raise NaturalNailDeliveryV3Error("official rig changed during nail authoring")
        if len(body.modifiers) != body_modifier_count_before:
            raise NaturalNailDeliveryV3Error("primary body modifier stack changed")
    except Exception:
        for obj in reversed(objects):
            if obj.name in bpy.data.objects:
                _remove_object_and_mesh(obj)
        for material in (bed_material, free_edge_material):
            if material.users == 0:
                bpy.data.materials.remove(material)
        raise

    report = {
        "method": METHOD_ID,
        **contract_report,
        "objects": [obj.name for obj in objects],
        "records": records,
        "material_contract": material_contract(),
        "material_names": {
            "nail_bed": bed_material.name,
            "free_edge": free_edge_material.name,
        },
        "translucent_natural_pink_bed": True,
        "softly_paler_free_edges": True,
        "opaque_white_polish_used": False,
        "outward_only_plate_thickness_m": NAIL_PLATE_THICKNESS_M,
        "primary_body_mesh_sha256_before": body_signature_before,
        "primary_body_mesh_sha256_after": body_signature_after,
        "primary_body_mesh_unchanged": body_signature_after == body_signature_before,
        "official_rig_sha256_before": rig_signature_before,
        "official_rig_sha256_after": rig_signature_after,
        "official_rig_unchanged": rig_signature_after == rig_signature_before,
        "body_modifier_stack_unchanged": len(body.modifiers)
        == body_modifier_count_before,
        "component_objects_are_separate_from_primary_body": True,
        "inactive_private_owner_review_only": True,
        "candidate_built_saved_rendered_exported_or_activated_by_this_adapter": False,
        "required_next_candidate_audit": [
            "evaluated nail/body overlap after every accepted hand, foot, seated, lying, and eating-ready pose",
            "left and right hand close visual review",
            "left and right foot close visual review",
        ],
    }
    return objects, report


__all__ = [
    "METHOD_ID",
    "NaturalNailDeliveryV3Error",
    "add_natural_nails_v3",
]
