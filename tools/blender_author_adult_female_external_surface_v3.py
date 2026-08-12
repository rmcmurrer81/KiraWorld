"""Blender adapter for camera-visible continuous adult surface v3.

This module refines an exact v2-authored primary skin in memory.  It locally
subdivides only measured visible-sheet faces, interpolates existing skin
weights, replaces the v2 height field with separate front/rear v3 fields, and
commits only after exact topology/intersection/landmark gates pass.  It has no
CLI, file output, render, export, assignment, publication, or activation path.
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import bmesh
import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))

from Core.avatar_adult_female_surface_authoring import (
    LANDMARK_GROUP_PREFIX,
    REQUIRED_RELATIONSHIPS,
    SurfaceFrame,
    landmark_group_name,
)
from Core.avatar_adult_female_surface_authoring_v2 import (
    METHOD_ID as BASE_DETAIL_METHOD_ID,
    posterior_surface_displacement as v2_posterior_surface_displacement,
    surface_displacement as v2_surface_displacement,
)
from Core.avatar_adult_female_surface_authoring_v3 import (
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
from tools.blender_author_adult_female_external_surface import (
    AdultFemaleSurfaceAuthoringError,
    _assert_closed_single_surface,
    _interpolate_new_weights,
    _local_coordinates,
    _mesh_digest,
    _nonadjacent_intersection_face_pairs,
    _skin_group_indices,
    _source_weight_rows,
    _topology_record,
    _weight_record,
)


_REQUIRED_MEMBERSHIPS = set(REQUIRED_RELATIONSHIPS).union(
    {
        "paired_labia_majora__left",
        "paired_labia_majora__right",
        "paired_labia_minora__left",
        "paired_labia_minora__right",
        "perineal_transition_to_anus_and_pelvic_floor__perineal_transition",
        "perineal_transition_to_anus_and_pelvic_floor__posterior_anal_recess",
    }
)


def _summary(values: Iterable[float]) -> dict[str, float | int]:
    rows = [float(value) for value in values]
    return {
        "count": len(rows),
        "minimum": min(rows, default=0.0),
        "maximum": max(rows, default=0.0),
        "mean": sum(rows) / len(rows) if rows else 0.0,
    }


def _frame_record(frame: SurfaceFrame) -> dict[str, Any]:
    return {
        "origin": [float(value) for value in frame.origin],
        "lateral_axis": [float(value) for value in frame.lateral_axis],
        "longitudinal_axis": [float(value) for value in frame.longitudinal_axis],
        "outward_axis": [float(value) for value in frame.outward_axis],
        "half_width_m": float(frame.half_width_m),
        "half_length_m": float(frame.half_length_m),
        "max_surface_offset_m": float(frame.max_surface_offset_m),
    }


def _face_components(faces: list[bmesh.types.BMFace]) -> list[list[bmesh.types.BMFace]]:
    selected = set(faces)
    unseen = set(faces)
    components: list[list[bmesh.types.BMFace]] = []
    while unseen:
        seed = unseen.pop()
        component = [seed]
        todo = [seed]
        while todo:
            current = todo.pop()
            for edge in current.edges:
                for neighbor in edge.link_faces:
                    if neighbor in selected and neighbor in unseen:
                        unseen.remove(neighbor)
                        component.append(neighbor)
                        todo.append(neighbor)
        components.append(component)
    return sorted(components, key=lambda rows: (-len(rows), min(face.index for face in rows)))


def _visible_sheet_faces(
    bm: bmesh.types.BMesh,
    *,
    frame: SurfaceFrame,
    support: Callable[[float, float], float],
    minimum_alignment: float,
    minimum_depth_m: float,
    label: str,
) -> tuple[list[bmesh.types.BMFace], list[int]]:
    outward = Vector(frame.outward_axis)
    selected: list[bmesh.types.BMFace] = []
    bm.normal_update()
    for face in bm.faces:
        u, v, depth = _local_coordinates(face.calc_center_median(), frame)
        if (
            support(u, v) > 0.0
            and abs(depth) <= frame.max_surface_offset_m
            and depth >= float(minimum_depth_m)
            and float(face.normal.dot(outward)) >= float(minimum_alignment)
        ):
            selected.append(face)
    if len(selected) < 16:
        raise AdultFemaleSurfaceAuthoringError(
            f"v3_{label}_visible_sheet_too_sparse:faces={len(selected)}"
        )
    components = _face_components(selected)
    component_sizes = [len(rows) for rows in components]
    if len(components) > 1 and len(components[1]) >= max(8, round(len(components[0]) * 0.02)):
        raise AdultFemaleSurfaceAuthoringError(
            f"v3_{label}_visible_sheet_not_single_component:"
            + ",".join(str(value) for value in component_sizes)
        )
    # Tiny normal-threshold islands at the taper edge are excluded rather than
    # bridged across the primary surface.  A competing substantial component
    # fails above, so the chosen sheet remains unambiguous and connected.
    return components[0], component_sizes


def _nearest_sample_report(
    vertices: Iterable[bmesh.types.BMVert],
    frame: SurfaceFrame,
    samples: Mapping[str, tuple[float, float]],
    displacement: Callable[[float, float], float],
    initial_alignment: Mapping[int, float],
) -> dict[str, dict[str, Any]]:
    rows = list(vertices)
    report: dict[str, dict[str, Any]] = {}
    for name, point in samples.items():
        if not rows:
            break
        nearest = min(
            rows,
            key=lambda vert: (
                (_local_coordinates(vert.co, frame)[0] - point[0]) ** 2
                + (_local_coordinates(vert.co, frame)[1] - point[1]) ** 2
            ),
        )
        u, v, depth = _local_coordinates(nearest.co, frame)
        report[name] = {
            "vertex_index": int(nearest.index),
            "nearest_normalized_uv": [float(u), float(v)],
            "normalized_distance": float(((u - point[0]) ** 2 + (v - point[1]) ** 2) ** 0.5),
            "final_outward_depth_m": float(depth),
            "target_displacement_m": float(displacement(u, v)),
            "initial_visible_sheet_normal_alignment": float(initial_alignment[int(nearest.index)]),
        }
    return report


def _replace_landmark_groups(
    obj: bpy.types.Object,
    memberships: Mapping[str, Iterable[int]],
) -> dict[str, str]:
    all_indices = list(range(len(obj.data.vertices)))
    mapping: dict[str, str] = {}
    existing_names = {group.name for group in obj.vertex_groups}
    for membership in sorted(_REQUIRED_MEMBERSHIPS):
        group_name = landmark_group_name(membership)
        if group_name not in existing_names:
            raise AdultFemaleSurfaceAuthoringError(
                f"v3_required_existing_landmark_group_missing:{group_name}"
            )
        indices = sorted(set(int(index) for index in memberships.get(membership, ())))
        if not indices:
            raise AdultFemaleSurfaceAuthoringError(
                f"v3_empty_landmark_membership:{membership}"
            )
        group = obj.vertex_groups[group_name]
        group.remove(all_indices)
        group.add(indices, 1.0, "REPLACE")
        mapping[membership] = group_name
    return mapping


def _opening_density_counts(
    vertices: Iterable[bmesh.types.BMVert],
    frame: SurfaceFrame,
    *,
    center: tuple[float, float],
    inner_radii: tuple[float, float],
    outer_radii: tuple[float, float],
) -> dict[str, int]:
    cap = 0
    rim = 0
    for vert in vertices:
        u, v, _depth = _local_coordinates(vert.co, frame)
        inner = ((u - center[0]) / inner_radii[0]) ** 2 + ((v - center[1]) / inner_radii[1]) ** 2
        outer = ((u - center[0]) / outer_radii[0]) ** 2 + ((v - center[1]) / outer_radii[1]) ** 2
        if inner <= 1.0:
            cap += 1
        elif outer <= 1.0:
            rim += 1
    return {"cap_vertex_count": cap, "annular_rim_vertex_count": rim}


def refine_existing_continuous_adult_female_surface_v3(
    obj: bpy.types.Object,
    *,
    front_frame: SurfaceFrame,
    rear_frame: SurfaceFrame,
    parameters: VisibleSurfaceParameters,
    legacy_v2_frame: SurfaceFrame,
    legacy_v2_posterior_frame: SurfaceFrame,
    legacy_v2_relief_scale_m: float,
    legacy_v2_taper_power: int,
    front_visible_sheet_minimum_outward_depth_m: float,
    rear_visible_sheet_minimum_outward_depth_m: float,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Refine an exact inactive v2 primary surface; never save or activate it."""

    if obj is None or obj.type != "MESH" or obj.mode != "OBJECT":
        raise AdultFemaleSurfaceAuthoringError("v3_refinement_requires_object_mesh")
    if not bool(obj.get("primary_surface")):
        raise AdultFemaleSurfaceAuthoringError("v3_refinement_requires_marked_primary_surface")
    if obj.get("adult_female_surface_detail_method_id") != BASE_DETAIL_METHOD_ID:
        raise AdultFemaleSurfaceAuthoringError("v3_refinement_requires_exact_v2_base")
    if bool(obj.get("runtime_activation_allowed")):
        raise AdultFemaleSurfaceAuthoringError("v3_refinement_refuses_runtime_activatable_object")
    contract = build_authoring_contract(project_root, front_frame, rear_frame, parameters)
    expected_names = {landmark_group_name(membership) for membership in _REQUIRED_MEMBERSHIPS}
    available_names = {group.name for group in obj.vertex_groups}
    missing_names = sorted(expected_names.difference(available_names))
    if missing_names:
        raise AdultFemaleSurfaceAuthoringError(
            "v3_refinement_landmark_set_missing:" + ",".join(missing_names)
        )

    skin_groups = _skin_group_indices(obj)
    source_rows = _source_weight_rows(obj, skin_groups)
    original_mesh = obj.data
    work_mesh = original_mesh.copy()
    work_mesh.name = f"{original_mesh.name}__{METHOD_ID}_refined"
    bm = bmesh.new()
    committed = False
    try:
        bm.from_mesh(work_mesh)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.verts.index_update()
        bm.faces.index_update()
        original_vertex_count = len(bm.verts)
        source_positions = [vert.co.copy() for vert in bm.verts]
        before = _topology_record(
            bm,
            degeneracy_area_m2=parameters.degeneracy_area_m2,
            include_intersections=True,
        )
        _assert_closed_single_surface(
            before,
            "v3_refinement_source",
            require_zero_global_intersections=False,
        )
        source_pairs = _nonadjacent_intersection_face_pairs(bm)
        source_digest = _mesh_digest(bm)

        front_faces, front_face_component_sizes = _visible_sheet_faces(
            bm,
            frame=front_frame,
            support=front_support_taper,
            minimum_alignment=parameters.minimum_front_normal_alignment,
            minimum_depth_m=front_visible_sheet_minimum_outward_depth_m,
            label="front",
        )
        rear_faces, rear_face_component_sizes = _visible_sheet_faces(
            bm,
            frame=rear_frame,
            support=rear_support_taper,
            minimum_alignment=parameters.minimum_rear_normal_alignment,
            minimum_depth_m=rear_visible_sheet_minimum_outward_depth_m,
            label="rear",
        )
        overlap = set(front_faces).intersection(rear_faces)
        if overlap:
            raise AdultFemaleSurfaceAuthoringError(
                f"v3_front_rear_chart_face_overlap:{len(overlap)}"
            )
        selected_edges = sorted(
            {edge for face in front_faces + rear_faces for edge in face.edges},
            key=lambda edge: tuple(sorted(int(vert.index) for vert in edge.verts)),
        )
        bmesh.ops.subdivide_edges(
            bm,
            edges=selected_edges,
            cuts=parameters.local_subdivision_cuts,
            use_grid_fill=True,
            smooth=0.0,
        )
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.verts.index_update()
        bm.faces.index_update()
        if any(
            (bm.verts[index].co - source_positions[index]).length > 1.0e-12
            for index in range(original_vertex_count)
        ):
            raise AdultFemaleSurfaceAuthoringError(
                "v3_source_vertex_index_stability_lost_during_subdivision"
            )
        new_vertex_count = len(bm.verts) - original_vertex_count
        if new_vertex_count <= 0 or new_vertex_count > parameters.maximum_new_vertices:
            raise AdultFemaleSurfaceAuthoringError(
                f"v3_new_vertex_count_out_of_bounds:{new_vertex_count}"
            )
        interpolated = _interpolate_new_weights(
            bm,
            original_vertex_count,
            source_positions,
            source_rows,
            parameters.maximum_skin_influences,
        )
        if interpolated != new_vertex_count:
            raise AdultFemaleSurfaceAuthoringError(
                f"v3_new_vertex_weight_count_mismatch:{interpolated}!={new_vertex_count}"
            )

        bm.normal_update()
        front_outward = Vector(front_frame.outward_axis)
        rear_outward = Vector(rear_frame.outward_axis)
        legacy_outward = Vector(legacy_v2_frame.outward_axis)
        legacy_posterior_outward = Vector(legacy_v2_posterior_frame.outward_axis)
        front_vertices: list[bmesh.types.BMVert] = []
        rear_vertices: list[bmesh.types.BMVert] = []
        front_initial_alignment: dict[int, float] = {}
        rear_initial_alignment: dict[int, float] = {}
        for vert in bm.verts:
            front_u, front_v, front_depth = _local_coordinates(vert.co, front_frame)
            front_alignment = float(vert.normal.dot(front_outward))
            if (
                front_support_taper(front_u, front_v) > 0.0
                and abs(front_depth) <= front_frame.max_surface_offset_m
                and front_depth >= front_visible_sheet_minimum_outward_depth_m
                and front_alignment >= parameters.minimum_front_normal_alignment
            ):
                front_vertices.append(vert)
                front_initial_alignment[int(vert.index)] = front_alignment
            rear_u, rear_v, rear_depth = _local_coordinates(vert.co, rear_frame)
            rear_alignment = float(vert.normal.dot(rear_outward))
            if (
                rear_support_taper(rear_u, rear_v) > 0.0
                and abs(rear_depth) <= rear_frame.max_surface_offset_m
                and rear_depth >= rear_visible_sheet_minimum_outward_depth_m
                and rear_alignment >= parameters.minimum_rear_normal_alignment
            ):
                rear_vertices.append(vert)
                rear_initial_alignment[int(vert.index)] = rear_alignment
        front_indices = {int(vert.index) for vert in front_vertices}
        rear_indices = {int(vert.index) for vert in rear_vertices}
        if front_indices.intersection(rear_indices):
            raise AdultFemaleSurfaceAuthoringError("v3_front_rear_chart_vertex_overlap")

        memberships: defaultdict[str, list[int]] = defaultdict(list)
        front_deltas: list[float] = []
        rear_deltas: list[float] = []
        legacy_removed: list[float] = []
        changed_indices: set[int] = set()

        def remove_legacy_fields(
            vert: bmesh.types.BMVert,
            *,
            blend_factor: float,
        ) -> None:
            blend = max(0.0, min(1.0, float(blend_factor)))
            if blend <= 0.0:
                return
            old_u, old_v, old_depth = _local_coordinates(vert.co, legacy_v2_frame)
            if old_u * old_u + old_v * old_v < 0.82 * 0.82 and abs(old_depth) <= legacy_v2_frame.max_surface_offset_m:
                delta = v2_surface_displacement(
                    old_u,
                    old_v,
                    relief_scale_m=float(legacy_v2_relief_scale_m),
                    taper_power=int(legacy_v2_taper_power),
                )
                if abs(delta) > 1.0e-12:
                    applied = delta * blend
                    vert.co -= legacy_outward * applied
                    legacy_removed.append(applied)
            post_u, post_v, post_depth = _local_coordinates(vert.co, legacy_v2_posterior_frame)
            if post_u * post_u + post_v * post_v < 0.82 * 0.82 and abs(post_depth) <= legacy_v2_posterior_frame.max_surface_offset_m:
                delta = v2_posterior_surface_displacement(
                    post_u,
                    post_v,
                    relief_scale_m=float(legacy_v2_relief_scale_m),
                    taper_power=int(legacy_v2_taper_power),
                )
                if abs(delta) > 1.0e-12:
                    applied = delta * blend
                    vert.co -= legacy_posterior_outward * applied
                    legacy_removed.append(applied)

        for vert in front_vertices:
            initial_u, initial_v, _initial_depth = _local_coordinates(vert.co, front_frame)
            alignment_blend = min(
                1.0,
                max(
                    0.0,
                    (
                        front_initial_alignment[int(vert.index)]
                        - parameters.minimum_front_normal_alignment
                    )
                    / 0.18,
                ),
            )
            alignment_blend = alignment_blend * alignment_blend * (3.0 - 2.0 * alignment_blend)
            remove_legacy_fields(
                vert,
                blend_factor=front_support_taper(initial_u, initial_v) * alignment_blend,
            )
            u, v, _depth = _local_coordinates(vert.co, front_frame)
            delta = front_surface_displacement(
                u,
                v,
                prominence_scale_m=parameters.front_prominence_scale_m,
            ) * alignment_blend
            if abs(delta) > 1.0e-12:
                vert.co += front_outward * delta
                front_deltas.append(delta)
                changed_indices.add(int(vert.index))
            for membership in front_landmark_memberships(u, v):
                memberships[membership].append(int(vert.index))

        for vert in rear_vertices:
            initial_u, initial_v, _initial_depth = _local_coordinates(vert.co, rear_frame)
            alignment_blend = min(
                1.0,
                max(
                    0.0,
                    (
                        rear_initial_alignment[int(vert.index)]
                        - parameters.minimum_rear_normal_alignment
                    )
                    / 0.18,
                ),
            )
            alignment_blend = alignment_blend * alignment_blend * (3.0 - 2.0 * alignment_blend)
            remove_legacy_fields(
                vert,
                blend_factor=rear_support_taper(initial_u, initial_v) * alignment_blend,
            )
            u, v, _depth = _local_coordinates(vert.co, rear_frame)
            delta = rear_surface_displacement(
                u,
                v,
                prominence_scale_m=parameters.rear_prominence_scale_m,
            ) * alignment_blend
            if abs(delta) > 1.0e-12:
                vert.co += rear_outward * delta
                rear_deltas.append(delta)
                changed_indices.add(int(vert.index))
            for membership in rear_landmark_memberships(u, v):
                memberships[membership].append(int(vert.index))

        missing_memberships = sorted(
            membership
            for membership in _REQUIRED_MEMBERSHIPS
            if len(set(memberships.get(membership, ()))) < parameters.minimum_feature_vertices
        )
        if missing_memberships:
            counts = {name: len(set(rows)) for name, rows in memberships.items()}
            raise AdultFemaleSurfaceAuthoringError(
                "v3_insufficient_visible_landmark_density:"
                + ",".join(missing_memberships)
                + f";counts={counts}"
            )

        opening_density = {
            "urethral": _opening_density_counts(
                front_vertices,
                front_frame,
                center=FRONT_FEATURE_SAMPLE_POINTS["urethral_opening"],
                inner_radii=(0.035, 0.033),
                outer_radii=(0.085, 0.070),
            ),
            "vaginal": _opening_density_counts(
                front_vertices,
                front_frame,
                center=FRONT_FEATURE_SAMPLE_POINTS["vaginal_opening"],
                inner_radii=(0.065, 0.065),
                outer_radii=(0.135, 0.115),
            ),
            "anal": _opening_density_counts(
                rear_vertices,
                rear_frame,
                center=REAR_FEATURE_SAMPLE_POINTS["anal_recess"],
                inner_radii=(0.075, 0.075),
                outer_radii=(0.165, 0.145),
            ),
        }
        sparse_openings = [
            name
            for name, row in opening_density.items()
            if row["cap_vertex_count"] < 4 or row["annular_rim_vertex_count"] < 8
        ]
        if sparse_openings:
            raise AdultFemaleSurfaceAuthoringError(
                "v3_opening_cap_or_rim_density_failed:"
                + ",".join(sparse_openings)
                + f";counts={opening_density}"
            )

        authored_faces_to_triangulate = [
            face
            for face in bm.faces
            if len(face.verts) > 3
            and any(int(vert.index) in changed_indices for vert in face.verts)
        ]
        triangulated_face_count = len(authored_faces_to_triangulate)
        if authored_faces_to_triangulate:
            bmesh.ops.triangulate(
                bm,
                faces=authored_faces_to_triangulate,
                quad_method="BEAUTY",
                ngon_method="BEAUTY",
            )
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            bm.verts.index_update()
            bm.faces.index_update()
        bm.normal_update()

        front_nearest = _nearest_sample_report(
            front_vertices,
            front_frame,
            FRONT_FEATURE_SAMPLE_POINTS,
            lambda u, v: front_surface_displacement(
                u,
                v,
                prominence_scale_m=parameters.front_prominence_scale_m,
            ),
            front_initial_alignment,
        )
        rear_nearest = _nearest_sample_report(
            rear_vertices,
            rear_frame,
            REAR_FEATURE_SAMPLE_POINTS,
            lambda u, v: rear_surface_displacement(
                u,
                v,
                prominence_scale_m=parameters.rear_prominence_scale_m,
            ),
            rear_initial_alignment,
        )
        distance_limits = {
            "urethral_opening": 0.060,
            "vaginal_opening": 0.060,
            "fourchette": 0.070,
        }
        failures = [
            name
            for name, maximum in distance_limits.items()
            if front_nearest[name]["normalized_distance"] > maximum
        ]
        if rear_nearest["anal_recess"]["normalized_distance"] > 0.090:
            failures.append("anal_recess")
        if failures:
            raise AdultFemaleSurfaceAuthoringError(
                "v3_wrong_sheet_or_sparse_feature_sample:" + ",".join(failures)
            )

        result_pairs = _nonadjacent_intersection_face_pairs(bm)
        after = _topology_record(
            bm,
            degeneracy_area_m2=parameters.degeneracy_area_m2,
            include_intersections=True,
        )
        _assert_closed_single_surface(
            after,
            "v3_refinement_result",
            require_zero_global_intersections=False,
        )
        new_pairs = result_pairs.difference(source_pairs)
        if new_pairs:
            first_pair = sorted(new_pairs)[0]
            intersection_faces: list[dict[str, Any]] = []
            for face_index in first_pair:
                face = bm.faces[face_index]
                intersection_faces.append(
                    {
                        "face_index": int(face_index),
                        "center": [
                            round(float(value), 7)
                            for value in face.calc_center_median()
                        ],
                        "normal": [round(float(value), 7) for value in face.normal],
                        "vertices": [
                            {
                                "index": int(vert.index),
                                "coordinate": [round(float(value), 7) for value in vert.co],
                                "changed": int(vert.index) in changed_indices,
                                "front_selected": int(vert.index) in front_indices,
                                "rear_selected": int(vert.index) in rear_indices,
                                "front_uv_depth": [
                                    round(float(value), 7)
                                    for value in _local_coordinates(vert.co, front_frame)
                                ],
                            }
                            for vert in face.verts
                        ],
                    }
                )
            raise AdultFemaleSurfaceAuthoringError(
                "v3_new_global_self_intersections_detected:"
                f"before={len(source_pairs)};after={len(result_pairs)};"
                f"first_new_pair={first_pair};"
                f"diagnostic={json.dumps(intersection_faces, sort_keys=True)}"
            )
        weights = _weight_record(bm, skin_groups, parameters.maximum_skin_influences)
        if weights["unweighted_vertex_count"] != 0:
            raise AdultFemaleSurfaceAuthoringError("v3_result_contains_unweighted_vertices")
        if not (
            weights["weight_sum_minimum"] >= 0.999
            and weights["weight_sum_maximum"] <= 1.001
            and weights["maximum_positive_skin_influences"]
            <= parameters.maximum_skin_influences
        ):
            raise AdultFemaleSurfaceAuthoringError("v3_result_skin_weights_invalid")
        result_digest = _mesh_digest(bm)
        bm.to_mesh(work_mesh)
        work_mesh.update(calc_edges=True)
        obj.data = work_mesh
        committed = True
    finally:
        bm.free()
        if not committed and work_mesh.users == 0:
            bpy.data.meshes.remove(work_mesh)

    landmark_groups = _replace_landmark_groups(obj, memberships)
    detail = {
        "schema_version": 1,
        "base_detail_method_id": BASE_DETAIL_METHOD_ID,
        "detail_method_id": METHOD_ID,
        "status": "REFINED_INACTIVE_AWAITING_INDEPENDENT_REQUALIFICATION",
        "scope": "complete_required_external_relationships_no_internal_tract_claim",
        "front_frame": _frame_record(front_frame),
        "rear_frame": _frame_record(rear_frame),
        "parameters": {
            name: getattr(parameters, name)
            for name in parameters.__dataclass_fields__
        },
        "theoretical_feature_sample_displacements_m": feature_sample_displacements(parameters),
        "front_nearest_authored_feature_samples": front_nearest,
        "rear_nearest_authored_feature_samples": rear_nearest,
        "opening_density": opening_density,
        "front_visible_sheet_vertex_count": len(front_vertices),
        "rear_visible_sheet_vertex_count": len(rear_vertices),
        "front_selected_source_face_count": len(front_faces),
        "rear_selected_source_face_count": len(rear_faces),
        "front_visible_sheet_face_component_sizes_before_tiny_island_filter": front_face_component_sizes,
        "rear_visible_sheet_face_component_sizes_before_tiny_island_filter": rear_face_component_sizes,
        "selected_source_edge_count": len(selected_edges),
        "new_vertex_count": new_vertex_count,
        "interpolated_weight_vertex_count": interpolated,
        "front_displacement_m": _summary(front_deltas),
        "rear_displacement_m": _summary(rear_deltas),
        "removed_legacy_v2_displacement_m": _summary(legacy_removed),
        "authored_nonplanar_faces_triangulated": triangulated_face_count,
        "landmark_groups": landmark_groups,
        "landmark_vertex_counts": {
            name: len(set(indices)) for name, indices in memberships.items()
        },
        "source_mesh_digest_sha256": source_digest,
        "result_mesh_digest_sha256": result_digest,
        "source_topology": before,
        "result_topology": after,
        "inherited_global_nonadjacent_self_intersection_pairs": len(source_pairs),
        "result_global_nonadjacent_self_intersection_pairs": len(result_pairs),
        "new_global_nonadjacent_self_intersection_pairs": len(new_pairs),
        "skin_weights": weights,
        "topology_changed_only_by_local_selected_face_subdivision": True,
        "existing_vertex_indices_preserved": True,
        "same_primary_mesh_object": True,
        "source_anatomy_geometry_copied": False,
        "separate_anatomy_mesh_created": False,
        "boolean_anatomy_union_used": False,
        "painted_only_relationships": False,
        "internal_tract_claimed": False,
        "camera_front_and_rear_sheets_separated": True,
        "independent_topology_review_required": True,
        "independent_relationship_review_required": True,
        "independent_visual_prominence_review_required": True,
        "qualified": False,
        "runtime_activation_allowed": False,
        "render_performed": False,
        "export_performed": False,
        "contract": contract,
    }
    try:
        metadata = json.loads(str(obj.get("adult_female_surface_metadata_json") or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        metadata = {}
    metadata["camera_visible_detail_refinement_v3"] = detail
    metadata["result_mesh_digest_sha256"] = result_digest
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
    return detail


__all__ = [
    "AdultFemaleSurfaceAuthoringError",
    "refine_existing_continuous_adult_female_surface_v3",
]
