"""Bounded Blender delivery adapter for one continuous adult-female surface.

The checkpointed v3 implementation is imported but never edited.  This
adapter stages a copy of the inactive v2 skin, removes the complete inherited
v2 front and posterior fields, invokes the locally subdivided delivery field,
adds subtle torso landmarks on that same primary mesh, and commits in memory
only after the exact no-new-intersection gate passes.  It has no CLI, save,
export, assignment, publication, activation, clothing, hair, or identity path.
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Mapping

import bmesh
import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))

from Core.avatar_adult_female_surface_authoring import SurfaceFrame
from Core.avatar_adult_female_surface_authoring_v2 import (
    posterior_surface_displacement as legacy_posterior_surface_displacement,
    surface_displacement as legacy_front_surface_displacement,
)
from Core.avatar_adult_female_surface_authoring_delivery_v1 import (
    FRONT_FEATURE_SAMPLE_POINTS,
    METHOD_ID,
    REAR_FEATURE_SAMPLE_POINTS,
    VisibleSurfaceParameters,
    build_authoring_contract,
    feature_sample_displacements,
    front_landmark_memberships,
    front_support_taper,
    front_surface_displacement,
    rear_landmark_memberships,
    rear_support_taper,
    rear_surface_displacement,
)
import tools.blender_author_adult_female_external_surface_v3 as checkpoint_adapter
from tools.blender_author_adult_female_external_surface import (
    AdultFemaleSurfaceAuthoringError,
    _mesh_digest,
    _nonadjacent_intersection_face_pairs,
    _topology_record,
)


TORSO_GROUPS = {
    "navel": "AFES_TORSO__navel",
    "areola_left": "AFES_TORSO__areola_left",
    "areola_right": "AFES_TORSO__areola_right",
}


def _summary(values: list[float]) -> dict[str, float | int]:
    return {
        "count": len(values),
        "minimum": min(values, default=0.0),
        "maximum": max(values, default=0.0),
        "mean": sum(values) / len(values) if values else 0.0,
    }


def _frame_coordinates(co: Vector, frame: SurfaceFrame) -> tuple[float, float, float]:
    relative = co - Vector(frame.origin)
    return (
        float(relative.dot(Vector(frame.lateral_axis))) / float(frame.half_width_m),
        float(relative.dot(Vector(frame.longitudinal_axis))) / float(frame.half_length_m),
        float(relative.dot(Vector(frame.outward_axis))),
    )


def _mesh_snapshot(mesh: bpy.types.Mesh, degeneracy_area_m2: float) -> tuple[dict[str, Any], set[tuple[int, int]], str]:
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.verts.index_update()
        bm.faces.index_update()
        topology = _topology_record(
            bm,
            degeneracy_area_m2=float(degeneracy_area_m2),
            include_intersections=True,
        )
        pairs = _nonadjacent_intersection_face_pairs(bm)
        digest = _mesh_digest(bm)
        return topology, pairs, digest
    finally:
        bm.free()


def _remove_complete_legacy_v2_fields(
    mesh: bpy.types.Mesh,
    *,
    front_frame: SurfaceFrame,
    posterior_frame: SurfaceFrame,
    target_relief_scale_m: float,
    target_taper_power: int,
    minimum_normal_alignment: float,
) -> dict[str, Any]:
    """Reverse the exact v2 target fields over their full original charts.

    The checkpointed v3 removed legacy displacement only on vertices selected
    for the new camera-visible charts.  That left the outer v2 transition ring
    in place.  V2's displacement is along each chart's outward axis, so its
    normalized u/v coordinates are invariant and the fields can be reversed
    deterministically.  The posterior addition is reversed first because it
    was the last v2 coordinate operation.
    """

    bm = bmesh.new()
    posterior_rows: list[float] = []
    front_rows: list[float] = []
    try:
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        posterior_outward = Vector(posterior_frame.outward_axis)
        for vert in bm.verts:
            u, v, depth = _frame_coordinates(vert.co, posterior_frame)
            if (
                u * u + v * v >= 1.0
                or abs(depth) > posterior_frame.max_surface_offset_m
                or float(vert.normal.dot(posterior_outward)) < float(minimum_normal_alignment)
            ):
                continue
            delta = legacy_posterior_surface_displacement(
                u,
                v,
                relief_scale_m=float(target_relief_scale_m),
                taper_power=int(target_taper_power),
            )
            if abs(delta) > 1.0e-12:
                vert.co -= posterior_outward * delta
                posterior_rows.append(float(delta))

        bm.normal_update()
        front_outward = Vector(front_frame.outward_axis)
        for vert in bm.verts:
            u, v, depth = _frame_coordinates(vert.co, front_frame)
            if (
                u * u + v * v >= 1.0
                or abs(depth) > front_frame.max_surface_offset_m
                or float(vert.normal.dot(front_outward)) < float(minimum_normal_alignment)
            ):
                continue
            delta = legacy_front_surface_displacement(
                u,
                v,
                relief_scale_m=float(target_relief_scale_m),
                taper_power=int(target_taper_power),
            )
            if abs(delta) > 1.0e-12:
                vert.co -= front_outward * delta
                front_rows.append(float(delta))
        bm.normal_update()
        bm.to_mesh(mesh)
        mesh.update(calc_edges=True)
    finally:
        bm.free()
    return {
        "reverse_order": ["posterior_v2_target", "front_v2_target"],
        "front_removed_displacement_m": _summary(front_rows),
        "posterior_removed_displacement_m": _summary(posterior_rows),
        "minimum_normal_alignment": float(minimum_normal_alignment),
        "entire_legacy_chart_evaluated": True,
        "checkpoint_v3_partial_legacy_removal_reused": False,
    }


def _apply_same_surface_torso_landmarks(
    obj: bpy.types.Object,
    *,
    body_scale: float,
) -> dict[str, Any]:
    """Add subtle navel/nipple relief and auditable material-region metadata."""

    mesh = obj.data
    bm = bmesh.new()
    memberships: defaultdict[str, list[int]] = defaultdict(list)
    displacements: defaultdict[str, list[float]] = defaultdict(list)
    try:
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.verts.index_update()
        bm.normal_update()
        navel_z = 1.015 * float(body_scale)
        breast_z = 1.285 * float(body_scale)
        breast_x = 0.102 * float(body_scale)
        for vert in bm.verts:
            normal = vert.normal.normalized()
            if float(normal.y) > -0.18:
                continue
            x = float(vert.co.x)
            z = float(vert.co.z)

            navel_radius = ((x / (0.027 * body_scale)) ** 2 + ((z - navel_z) / (0.032 * body_scale)) ** 2) ** 0.5
            if navel_radius <= 1.0:
                memberships["navel"].append(int(vert.index))
                outer = __import__("math").exp(-0.5 * navel_radius * navel_radius)
                inner = __import__("math").exp(
                    -0.5
                    * (
                        (x / (0.008 * body_scale)) ** 2
                        + ((z - navel_z) / (0.011 * body_scale)) ** 2
                    )
                )
                delta = (0.00028 * outer - 0.00135 * inner) * body_scale
                vert.co += normal * delta
                displacements["navel"].append(float(delta))

            for label, center_x in (
                ("areola_left", breast_x),
                ("areola_right", -breast_x),
            ):
                radius = (
                    ((x - center_x) / (0.020 * body_scale)) ** 2
                    + ((z - breast_z) / (0.020 * body_scale)) ** 2
                ) ** 0.5
                if radius > 1.0:
                    continue
                memberships[label].append(int(vert.index))
                areola = __import__("math").exp(-0.5 * (radius / 0.72) ** 2)
                papilla = __import__("math").exp(
                    -0.5
                    * (
                        ((x - center_x) / (0.0065 * body_scale)) ** 2
                        + ((z - breast_z) / (0.0065 * body_scale)) ** 2
                    )
                )
                delta = (0.00020 * areola + 0.00078 * papilla) * body_scale
                vert.co += normal * delta
                displacements[label].append(float(delta))
        bm.normal_update()
        bm.to_mesh(mesh)
        mesh.update(calc_edges=True)
    finally:
        bm.free()

    all_indices = list(range(len(mesh.vertices)))
    group_counts: dict[str, int] = {}
    for label, group_name in TORSO_GROUPS.items():
        group = obj.vertex_groups.get(group_name) or obj.vertex_groups.new(name=group_name)
        group.remove(all_indices)
        indices = sorted(set(memberships.get(label, ())))
        if indices:
            group.add(indices, 1.0, "REPLACE")
        group_counts[group_name] = len(indices)
    return {
        "same_primary_surface": True,
        "separate_geometry_created": False,
        "boolean_used": False,
        "vertex_groups": group_counts,
        "displacement_m": {name: _summary(rows) for name, rows in displacements.items()},
        "material_regions": {
            "areola_left": {
                "mode": "documented_primary_surface_vertex_region",
                "vertex_group": TORSO_GROUPS["areola_left"],
                "suggested_base_color_multiplier": [0.84, 0.68, 0.66],
                "separate_mesh": False,
            },
            "areola_right": {
                "mode": "documented_primary_surface_vertex_region",
                "vertex_group": TORSO_GROUPS["areola_right"],
                "suggested_base_color_multiplier": [0.84, 0.68, 0.66],
                "separate_mesh": False,
            },
            "navel": {
                "mode": "documented_primary_surface_vertex_region",
                "vertex_group": TORSO_GROUPS["navel"],
                "suggested_cavity_roughness_multiplier": 1.08,
                "separate_mesh": False,
            },
        },
        "material_slot_added": False,
        "paint_only_anatomy_claimed": False,
    }


def _smooth_only_local_authored_faces(
    mesh: bpy.types.Mesh,
    *,
    body_scale: float,
) -> dict[str, int]:
    changed = 0
    considered = 0
    for polygon in mesh.polygons:
        coordinates = [mesh.vertices[index].co for index in polygon.vertices]
        in_pelvic_region = any(
            abs(float(co.x)) <= 0.075 * body_scale
            and 0.62 * body_scale <= float(co.z) <= 0.93 * body_scale
            for co in coordinates
        )
        in_torso_region = any(
            abs(float(co.x)) <= 0.15 * body_scale
            and 0.97 * body_scale <= float(co.z) <= 1.33 * body_scale
            for co in coordinates
        )
        if not (in_pelvic_region or in_torso_region):
            continue
        considered += 1
        if not polygon.use_smooth:
            polygon.use_smooth = True
            changed += 1
    mesh.update()
    return {"local_faces_considered": considered, "faces_changed_to_smooth": changed}


def refine_existing_continuous_adult_female_surface_delivery_v1(
    obj: bpy.types.Object,
    *,
    front_frame: SurfaceFrame,
    rear_frame: SurfaceFrame,
    parameters: VisibleSurfaceParameters,
    legacy_v2_frame: SurfaceFrame,
    legacy_v2_posterior_frame: SurfaceFrame,
    legacy_v2_relief_scale_m: float,
    legacy_v2_taper_power: int,
    legacy_v2_minimum_normal_alignment: float,
    front_visible_sheet_minimum_outward_depth_m: float,
    rear_visible_sheet_minimum_outward_depth_m: float,
    body_scale: float,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Stage and refine the inactive v2 primary skin; never save or activate."""

    if obj is None or obj.type != "MESH" or obj.mode != "OBJECT":
        raise AdultFemaleSurfaceAuthoringError("delivery_refinement_requires_object_mesh")
    if not bool(obj.get("primary_surface")):
        raise AdultFemaleSurfaceAuthoringError("delivery_refinement_requires_primary_surface")
    if obj.get("adult_female_surface_detail_method_id") != "generic_continuous_adult_female_external_surface_v2":
        raise AdultFemaleSurfaceAuthoringError("delivery_refinement_requires_exact_v2_base")
    if bool(obj.get("runtime_activation_allowed")):
        raise AdultFemaleSurfaceAuthoringError("delivery_refinement_refuses_runtime_activatable_object")

    original_mesh = obj.data
    source_topology, source_pairs, source_digest = _mesh_snapshot(
        original_mesh,
        parameters.degeneracy_area_m2,
    )
    staging_mesh = original_mesh.copy()
    staging_mesh.name = f"{original_mesh.name}__{METHOD_ID}_staging"
    obj.data = staging_mesh
    committed = False
    patched_names = {
        "METHOD_ID": METHOD_ID,
        "FRONT_FEATURE_SAMPLE_POINTS": FRONT_FEATURE_SAMPLE_POINTS,
        "REAR_FEATURE_SAMPLE_POINTS": REAR_FEATURE_SAMPLE_POINTS,
        "build_authoring_contract": build_authoring_contract,
        "feature_sample_displacements": feature_sample_displacements,
        "front_landmark_memberships": front_landmark_memberships,
        "front_support_taper": front_support_taper,
        "front_surface_displacement": front_surface_displacement,
        "rear_landmark_memberships": rear_landmark_memberships,
        "rear_support_taper": rear_support_taper,
        "rear_surface_displacement": rear_surface_displacement,
        # Full legacy removal is performed once on the entire v2 chart below.
        "v2_surface_displacement": lambda *_args, **_kwargs: 0.0,
        "v2_posterior_surface_displacement": lambda *_args, **_kwargs: 0.0,
    }
    originals = {name: getattr(checkpoint_adapter, name) for name in patched_names}
    try:
        legacy_removal = _remove_complete_legacy_v2_fields(
            staging_mesh,
            front_frame=legacy_v2_frame,
            posterior_frame=legacy_v2_posterior_frame,
            target_relief_scale_m=float(legacy_v2_relief_scale_m),
            target_taper_power=int(legacy_v2_taper_power),
            minimum_normal_alignment=float(legacy_v2_minimum_normal_alignment),
        )
        cleaned_topology, cleaned_pairs, cleaned_digest = _mesh_snapshot(
            staging_mesh,
            parameters.degeneracy_area_m2,
        )
        legacy_new_pairs = cleaned_pairs.difference(source_pairs)
        if legacy_new_pairs:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_legacy_removal_created_new_intersections:"
                + str(sorted(legacy_new_pairs)[0])
            )

        for name, value in patched_names.items():
            setattr(checkpoint_adapter, name, value)
        detail = checkpoint_adapter.refine_existing_continuous_adult_female_surface_v3(
            obj,
            front_frame=front_frame,
            rear_frame=rear_frame,
            parameters=parameters,
            legacy_v2_frame=legacy_v2_frame,
            legacy_v2_posterior_frame=legacy_v2_posterior_frame,
            legacy_v2_relief_scale_m=float(legacy_v2_relief_scale_m),
            legacy_v2_taper_power=int(legacy_v2_taper_power),
            front_visible_sheet_minimum_outward_depth_m=float(
                front_visible_sheet_minimum_outward_depth_m
            ),
            rear_visible_sheet_minimum_outward_depth_m=float(
                rear_visible_sheet_minimum_outward_depth_m
            ),
            project_root=project_root,
        )
        torso = _apply_same_surface_torso_landmarks(obj, body_scale=float(body_scale))
        smoothing = _smooth_only_local_authored_faces(obj.data, body_scale=float(body_scale))
        final_topology, final_pairs, final_digest = _mesh_snapshot(
            obj.data,
            parameters.degeneracy_area_m2,
        )
        new_pairs = final_pairs.difference(source_pairs)
        if new_pairs:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_new_global_self_intersections_detected:"
                f"before={len(source_pairs)};after={len(final_pairs)};"
                f"first_new_pair={sorted(new_pairs)[0]}"
            )
        if (
            final_topology["primary_surface_components"] != 1
            or final_topology["boundary_edges"] != 0
            or final_topology["nonmanifold_edges"] != 0
            or final_topology["degenerate_faces"] != 0
        ):
            raise AdultFemaleSurfaceAuthoringError("delivery_final_topology_gate_failed")

        detail["delivery_method_id"] = METHOD_ID
        detail["status"] = "DELIVERY_COMPONENT_INACTIVE_AWAITING_OWNER_VISUAL_REVIEW"
        detail["checkpoint_source_mesh_digest_sha256"] = source_digest
        detail["legacy_clean_mesh_digest_sha256"] = cleaned_digest
        detail["result_mesh_digest_sha256"] = final_digest
        detail["checkpoint_source_topology"] = source_topology
        detail["legacy_clean_topology"] = cleaned_topology
        detail["result_topology"] = final_topology
        detail["legacy_field_removal"] = legacy_removal
        detail["same_surface_torso_landmarks"] = torso
        detail["localized_smooth_shading"] = smoothing
        detail["checkpoint_source_intersection_pairs"] = len(source_pairs)
        detail["legacy_clean_intersection_pairs"] = len(cleaned_pairs)
        detail["result_global_nonadjacent_self_intersection_pairs"] = len(final_pairs)
        detail["new_global_nonadjacent_self_intersection_pairs"] = len(new_pairs)
        detail["entire_legacy_v2_chart_removed_before_delivery_field"] = True
        detail["rounded_transition_support"] = True
        detail["hair_dependency"] = False
        detail["scalp_geometry_changed"] = False
        detail["separate_anatomy_mesh_created"] = False
        detail["boolean_anatomy_union_used"] = False
        detail["copied_anatomy_geometry_used"] = False
        detail["runtime_activation_allowed"] = False
        detail["render_performed"] = False
        detail["export_performed"] = False

        try:
            metadata = json.loads(str(obj.get("adult_female_surface_metadata_json") or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            metadata = {}
        metadata["delivery_refinement_v1"] = detail
        metadata["result_mesh_digest_sha256"] = final_digest
        metadata["qualified_for_adult_foundation"] = False
        metadata["runtime_activation_allowed"] = False
        obj["adult_female_surface_detail_method_id"] = METHOD_ID
        obj["adult_female_surface_detail_status"] = detail["status"]
        obj["adult_female_surface_metadata_json"] = json.dumps(
            metadata,
            sort_keys=True,
            separators=(",", ":"),
        )
        obj["adult_foundation_qualified"] = False
        obj["runtime_activation_allowed"] = False
        committed = True
        return detail
    finally:
        for name, value in originals.items():
            setattr(checkpoint_adapter, name, value)
        if not committed:
            failed_mesh = obj.data
            obj.data = original_mesh
            if failed_mesh is not original_mesh and failed_mesh.users == 0:
                bpy.data.meshes.remove(failed_mesh)
        elif staging_mesh.users == 0:
            bpy.data.meshes.remove(staging_mesh)


__all__ = [
    "AdultFemaleSurfaceAuthoringError",
    "refine_existing_continuous_adult_female_surface_delivery_v1",
]
