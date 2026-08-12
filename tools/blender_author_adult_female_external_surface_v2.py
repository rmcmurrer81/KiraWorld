"""Blender adapter for structured continuous adult-female surface v2.

The accepted v1 adapter is intentionally left byte-for-byte available.  This
version reuses its reviewed topology/weight helpers but supplies the v2
structured fold, rim, and recess field.  It has no CLI, render, export,
selection, publication, or runtime-activation path.
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import bmesh
import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))

from Core.avatar_adult_female_surface_authoring import (
    AuthoringParameters,
    LANDMARK_GROUP_PREFIX,
    METHOD_ID as BASE_METHOD_ID,
    REQUIRED_RELATIONSHIPS,
    SurfaceFrame,
    landmark_group_name,
    surface_displacement as base_surface_displacement,
)
from Core.avatar_adult_female_surface_authoring_v2 import (
    FEATURE_SAMPLE_POINTS,
    METHOD_ID,
    POSTERIOR_FEATURE_SAMPLE_POINTS,
    build_authoring_contract,
    feature_sample_displacements,
    landmark_memberships,
    posterior_landmark_memberships,
    posterior_surface_displacement,
    surface_displacement,
)
from tools.blender_author_adult_female_external_surface import (
    AdultFemaleSurfaceAuthoringError,
    _assert_closed_single_surface,
    _assert_source_object,
    _install_landmark_groups,
    _interpolate_new_weights,
    _local_coordinates,
    _mesh_digest,
    _nonadjacent_intersection_face_pairs,
    _region_faces,
    _skin_group_indices,
    _source_weight_rows,
    _topology_record,
    _weight_record,
)


def _landmark_requirements() -> set[str]:
    required = set(REQUIRED_RELATIONSHIPS)
    required.update(
        {
            "paired_labia_majora__left",
            "paired_labia_majora__right",
            "paired_labia_minora__left",
            "paired_labia_minora__right",
            "perineal_transition_to_anus_and_pelvic_floor__perineal_transition",
            "perineal_transition_to_anus_and_pelvic_floor__posterior_anal_recess",
        }
    )
    return required


def _summary(values: Iterable[float]) -> dict[str, float | int]:
    rows = [float(value) for value in values]
    return {
        "count": len(rows),
        "minimum": min(rows, default=0.0),
        "maximum": max(rows, default=0.0),
        "mean": sum(rows) / len(rows) if rows else 0.0,
    }


def _author_region_v2(
    bm: bmesh.types.BMesh,
    frame: SurfaceFrame,
    parameters: AuthoringParameters,
) -> tuple[
    dict[str, list[int]],
    int,
    set[int],
    dict[str, dict[str, float | int]],
    dict[str, dict[str, float | list[float]]],
]:
    outward = Vector(frame.outward_axis)
    bm.normal_update()
    memberships: defaultdict[str, list[int]] = defaultdict(list)
    displacement_rows: defaultdict[str, list[float]] = defaultdict(list)
    nearest: dict[str, tuple[float, float, float, float]] = {}
    changed = 0
    changed_indices: set[int] = set()
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    for vert in bm.verts:
        u, v, depth = _local_coordinates(vert.co, frame)
        if (
            u * u + v * v >= 1.0
            or abs(depth) > frame.max_surface_offset_m
            or vert.normal.dot(outward) < parameters.minimum_face_normal_alignment
        ):
            continue
        vertex_memberships = landmark_memberships(
            u,
            v,
            threshold=parameters.landmark_influence_threshold,
        )
        for membership in vertex_memberships:
            memberships[membership].append(int(vert.index))
        delta = surface_displacement(
            u,
            v,
            relief_scale_m=parameters.relief_scale_m,
            taper_power=parameters.boundary_taper_power,
        )
        for membership in vertex_memberships:
            displacement_rows[membership].append(delta)
        for name, sample in FEATURE_SAMPLE_POINTS.items():
            distance_squared = (u - sample[0]) ** 2 + (v - sample[1]) ** 2
            previous = nearest.get(name)
            if previous is None or distance_squared < previous[0]:
                nearest[name] = (distance_squared, u, v, delta)
        if abs(delta) > 1.0e-12:
            vert.co += outward * delta
            changed += 1
            changed_indices.add(int(vert.index))
    missing = sorted(
        membership
        for membership in _landmark_requirements()
        if len(memberships.get(membership, []))
        < parameters.minimum_landmark_vertices
    )
    if missing:
        raise AdultFemaleSurfaceAuthoringError(
            "v2_insufficient_local_topology_for_landmarks:" + ",".join(missing)
        )
    if changed < len(REQUIRED_RELATIONSHIPS) * parameters.minimum_landmark_vertices:
        raise AdultFemaleSurfaceAuthoringError(
            f"v2_insufficient_authored_vertex_count:{changed}"
        )
    missing_samples = sorted(set(FEATURE_SAMPLE_POINTS).difference(nearest))
    if missing_samples:
        raise AdultFemaleSurfaceAuthoringError(
            "v2_feature_sample_nearest_vertex_missing:" + ",".join(missing_samples)
        )
    nearest_report = {
        name: {
            "normalized_distance": float(row[0] ** 0.5),
            "nearest_normalized_uv": [float(row[1]), float(row[2])],
            "applied_displacement_m": float(row[3]),
        }
        for name, row in nearest.items()
    }
    return (
        {name: sorted(indices) for name, indices in memberships.items()},
        changed,
        changed_indices,
        {name: _summary(values) for name, values in displacement_rows.items()},
        nearest_report,
    )


def author_continuous_adult_female_surface_v2(
    obj: bpy.types.Object,
    *,
    frame: SurfaceFrame,
    parameters: AuthoringParameters,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Author a private structured v2 patch and return unqualified evidence."""

    _assert_source_object(obj)
    contract = build_authoring_contract(project_root, frame, parameters)
    skin_groups = _skin_group_indices(obj)
    source_rows = _source_weight_rows(obj, skin_groups)
    original_mesh = obj.data
    work_mesh = original_mesh.copy()
    work_mesh.name = f"{original_mesh.name}__{METHOD_ID}"
    bm = bmesh.new()
    committed = False
    try:
        bm.from_mesh(work_mesh)
        bm.verts.ensure_lookup_table()
        original_vertex_count = len(bm.verts)
        source_positions = [vert.co.copy() for vert in bm.verts]
        before = _topology_record(
            bm,
            degeneracy_area_m2=parameters.degeneracy_area_m2,
            include_intersections=True,
        )
        _assert_closed_single_surface(
            before,
            "v2_source",
            require_zero_global_intersections=False,
        )
        source_intersection_pairs = _nonadjacent_intersection_face_pairs(bm)
        source_digest = _mesh_digest(bm)

        selected_faces = _region_faces(bm, frame, parameters)
        selected_face_indices = {int(face.index) for face in selected_faces}
        selected_source_intersections = {
            pair
            for pair in source_intersection_pairs
            if pair[0] in selected_face_indices or pair[1] in selected_face_indices
        }
        if selected_source_intersections:
            raise AdultFemaleSurfaceAuthoringError(
                "v2_source_authoring_region_self_intersections="
                f"{len(selected_source_intersections)}"
            )
        selected_edges = sorted(
            {edge for face in selected_faces for edge in face.edges},
            key=lambda edge: tuple(sorted(vert.index for vert in edge.verts)),
        )
        bmesh.ops.subdivide_edges(
            bm,
            edges=selected_edges,
            cuts=parameters.subdivision_cuts,
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
                "v2_source_vertex_index_stability_lost_during_subdivision"
            )
        interpolated = _interpolate_new_weights(
            bm,
            original_vertex_count,
            source_positions,
            source_rows,
            parameters.maximum_skin_influences,
        )
        (
            memberships,
            changed,
            changed_indices,
            displacement_statistics,
            nearest_feature_samples,
        ) = _author_region_v2(bm, frame, parameters)
        authored_faces_to_triangulate = [
            face
            for face in bm.faces
            if len(face.verts) > 3
            and any(int(vert.index) in changed_indices for vert in face.verts)
        ]
        triangulated_authored_face_count = len(authored_faces_to_triangulate)
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
        result_intersection_pairs = _nonadjacent_intersection_face_pairs(bm)
        after = _topology_record(
            bm,
            degeneracy_area_m2=parameters.degeneracy_area_m2,
            include_intersections=True,
        )
        _assert_closed_single_surface(
            after,
            "v2_result",
            require_zero_global_intersections=False,
        )
        authored_face_indices = {
            int(face.index)
            for face in bm.faces
            if any(int(vert.index) in changed_indices for vert in face.verts)
        }
        authored_region_intersections = {
            pair
            for pair in result_intersection_pairs
            if pair[0] in authored_face_indices or pair[1] in authored_face_indices
        }
        if authored_region_intersections:
            raise AdultFemaleSurfaceAuthoringError(
                "v2_authored_region_self_intersections="
                f"{len(authored_region_intersections)}"
            )
        if len(result_intersection_pairs) > len(source_intersection_pairs):
            first_pair = sorted(result_intersection_pairs.difference(source_intersection_pairs))[0]
            centers = [
                tuple(round(float(value), 7) for value in bm.faces[index].calc_center_median())
                for index in first_pair
            ]
            raise AdultFemaleSurfaceAuthoringError(
                "v2_new_global_self_intersections_detected:"
                f"before={len(source_intersection_pairs)};"
                f"after={len(result_intersection_pairs)};"
                f"first_new_pair={first_pair};centers={centers}"
            )
        weights = _weight_record(
            bm,
            skin_groups,
            parameters.maximum_skin_influences,
        )
        if weights["unweighted_vertex_count"] != 0:
            raise AdultFemaleSurfaceAuthoringError("v2_result_contains_unweighted_vertices")
        if not (
            weights["weight_sum_minimum"] >= 0.999
            and weights["weight_sum_maximum"] <= 1.001
        ):
            raise AdultFemaleSurfaceAuthoringError("v2_result_skin_weights_not_normalized")
        result_digest = _mesh_digest(bm)
        bm.to_mesh(work_mesh)
        work_mesh.update(calc_edges=True)
        obj.data = work_mesh
        committed = True
    finally:
        bm.free()
        if not committed and work_mesh.users == 0:
            bpy.data.meshes.remove(work_mesh)

    group_map = _install_landmark_groups(obj, memberships)
    metadata = {
        "schema_version": 2,
        "method_id": METHOD_ID,
        "status": "AUTHORED_INACTIVE_AWAITING_INDEPENDENT_REVIEW",
        "body_class": "adult_female",
        "scope": "complete_required_external_relationships_no_internal_tract_claim",
        "relationships": list(REQUIRED_RELATIONSHIPS),
        "landmark_groups": group_map,
        "source_mesh_digest_sha256": source_digest,
        "result_mesh_digest_sha256": result_digest,
        "opening_representation": contract["opening_representation"],
        "theoretical_feature_sample_displacements_m": feature_sample_displacements(
            parameters.relief_scale_m,
            parameters.boundary_taper_power,
        ),
        "nearest_authored_feature_samples": nearest_feature_samples,
        "landmark_displacement_statistics_m": displacement_statistics,
        "source_anatomy_geometry_copied": False,
        "wrong_sex_helper_used": False,
        "separate_anatomy_mesh_created": False,
        "boolean_anatomy_union_used": False,
        "painted_only_relationships": False,
        "skin_weights_preserved_and_new_vertices_interpolated": True,
        "authored_nonplanar_faces_triangulated": triangulated_authored_face_count,
        "intersection_audit_method": (
            "dual_tessellation_bvh_broad_phase_exact_triangle_narrow_phase"
        ),
        "independent_topology_review_required": True,
        "independent_relationship_review_required": True,
        "independent_visual_prominence_review_required": True,
        "inherited_global_nonadjacent_self_intersection_pairs": len(
            source_intersection_pairs
        ),
        "result_global_nonadjacent_self_intersection_pairs": len(
            result_intersection_pairs
        ),
        "authored_region_nonadjacent_self_intersection_pairs": len(
            authored_region_intersections
        ),
        "global_topology_ready_for_qualification": len(result_intersection_pairs) == 0,
        "qualified_for_adult_foundation": False,
        "runtime_activation_allowed": False,
    }
    obj["adult_female_surface_method_id"] = METHOD_ID
    obj["adult_female_surface_status"] = metadata["status"]
    obj["adult_female_surface_metadata_json"] = json.dumps(
        metadata,
        sort_keys=True,
        separators=(",", ":"),
    )
    obj["runtime_activation_allowed"] = False
    obj["adult_foundation_qualified"] = False
    return {
        **metadata,
        "contract": contract,
        "source_topology": before,
        "result_topology": after,
        "selected_source_face_count": len(selected_faces),
        "selected_source_edge_count": len(selected_edges),
        "new_vertex_count": interpolated,
        "authored_vertex_count": changed,
        "landmark_vertex_counts": {
            name: len(indices) for name, indices in memberships.items()
        },
        "skin_weights": weights,
        "build_performed": True,
        "render_performed": False,
        "export_performed": False,
        "runtime_mutation_performed": False,
    }


def refine_existing_continuous_adult_female_surface_v2(
    obj: bpy.types.Object,
    *,
    frame: SurfaceFrame,
    base_parameters: AuthoringParameters,
    posterior_frame: SurfaceFrame,
    target_relief_scale_m: float,
    target_taper_power: int = 2,
) -> dict[str, Any]:
    """Convert an authored v1 patch to the structured v2 target in place.

    The v1 method remains the exact qualified neutral starting point.  This
    style-stage refinement changes coordinates only, preserves every vertex,
    face, rig weight, and landmark group, and commits only after an exact
    no-new-intersection audit.  It still requires independent visual review.
    """

    if obj is None or obj.type != "MESH" or obj.mode != "OBJECT":
        raise AdultFemaleSurfaceAuthoringError("v2_refinement_requires_object_mesh")
    if obj.get("adult_female_surface_method_id") != BASE_METHOD_ID:
        raise AdultFemaleSurfaceAuthoringError("v2_refinement_requires_exact_v1_base")
    expected_landmarks = {
        group.name for group in obj.vertex_groups if group.name.startswith(LANDMARK_GROUP_PREFIX)
    }
    if len(expected_landmarks) < len(REQUIRED_RELATIONSHIPS):
        raise AdultFemaleSurfaceAuthoringError("v2_refinement_landmark_set_missing")
    target_relief = float(target_relief_scale_m)
    if not 0.0025 <= target_relief <= 0.008:
        raise AdultFemaleSurfaceAuthoringError("v2_target_relief_scale_out_of_bounds")
    if int(target_taper_power) not in {2, 3}:
        raise AdultFemaleSurfaceAuthoringError("v2_target_taper_power_out_of_bounds")

    original_mesh = obj.data
    work_mesh = original_mesh.copy()
    work_mesh.name = f"{original_mesh.name}__{METHOD_ID}_refined"
    bm = bmesh.new()
    committed = False
    try:
        bm.from_mesh(work_mesh)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        before = _topology_record(
            bm,
            degeneracy_area_m2=base_parameters.degeneracy_area_m2,
            include_intersections=True,
        )
        _assert_closed_single_surface(
            before,
            "v2_refinement_source",
            require_zero_global_intersections=False,
        )
        source_pairs = _nonadjacent_intersection_face_pairs(bm)
        source_digest = _mesh_digest(bm)
        outward = Vector(frame.outward_axis)
        nearest: dict[str, tuple[float, float, float, float]] = {}
        posterior_nearest: dict[str, tuple[float, float, float, float]] = {}
        posterior_memberships: defaultdict[str, list[int]] = defaultdict(list)
        corrections: list[float] = []
        posterior_corrections: list[float] = []
        changed = 0
        bm.normal_update()
        for vert in bm.verts:
            u, v, depth = _local_coordinates(vert.co, frame)
            if (
                u * u + v * v >= 1.0
                or abs(depth) > frame.max_surface_offset_m
                or vert.normal.dot(outward) < base_parameters.minimum_face_normal_alignment
            ):
                continue
            base_delta = base_surface_displacement(
                u,
                v,
                relief_scale_m=base_parameters.relief_scale_m,
                taper_power=base_parameters.boundary_taper_power,
            )
            target_delta = surface_displacement(
                u,
                v,
                relief_scale_m=target_relief,
                taper_power=int(target_taper_power),
            )
            correction = target_delta - base_delta
            for name, sample in FEATURE_SAMPLE_POINTS.items():
                distance_squared = (u - sample[0]) ** 2 + (v - sample[1]) ** 2
                previous = nearest.get(name)
                if previous is None or distance_squared < previous[0]:
                    nearest[name] = (distance_squared, u, v, target_delta)
            if abs(correction) > 1.0e-12:
                vert.co += outward * correction
                corrections.append(correction)
                changed += 1
        bm.normal_update()
        posterior_outward = Vector(posterior_frame.outward_axis)
        for vert in bm.verts:
            u, v, depth = _local_coordinates(vert.co, posterior_frame)
            if (
                u * u + v * v >= 1.0
                or abs(depth) > posterior_frame.max_surface_offset_m
                or vert.normal.dot(posterior_outward)
                < base_parameters.minimum_face_normal_alignment
            ):
                continue
            vertex_memberships = posterior_landmark_memberships(
                u,
                v,
                threshold=base_parameters.landmark_influence_threshold,
            )
            for membership in vertex_memberships:
                posterior_memberships[membership].append(int(vert.index))
            posterior_delta = posterior_surface_displacement(
                u,
                v,
                relief_scale_m=target_relief,
                taper_power=int(target_taper_power),
            )
            for name, sample in POSTERIOR_FEATURE_SAMPLE_POINTS.items():
                distance_squared = (u - sample[0]) ** 2 + (v - sample[1]) ** 2
                previous = posterior_nearest.get(name)
                if previous is None or distance_squared < previous[0]:
                    posterior_nearest[name] = (
                        distance_squared,
                        u,
                        v,
                        posterior_delta,
                    )
            if abs(posterior_delta) > 1.0e-12:
                vert.co += posterior_outward * posterior_delta
                corrections.append(posterior_delta)
                posterior_corrections.append(posterior_delta)
                changed += 1
        required_posterior_memberships = (
            "posterior_commissure_fourchette",
            "perineal_transition_to_anus_and_pelvic_floor",
            "perineal_transition_to_anus_and_pelvic_floor__perineal_transition",
            "perineal_transition_to_anus_and_pelvic_floor__posterior_anal_recess",
        )
        missing_posterior = [
            membership
            for membership in required_posterior_memberships
            if len(posterior_memberships.get(membership, []))
            < base_parameters.minimum_landmark_vertices
        ]
        if missing_posterior:
            raise AdultFemaleSurfaceAuthoringError(
                "v2_posterior_frame_insufficient_landmark_vertices:"
                + ",".join(missing_posterior)
                + f";counts={dict((name, len(rows)) for name, rows in posterior_memberships.items())}"
                + f";nearest={posterior_nearest}"
            )
        missing_posterior_samples = sorted(
            set(POSTERIOR_FEATURE_SAMPLE_POINTS).difference(posterior_nearest)
        )
        if missing_posterior_samples:
            raise AdultFemaleSurfaceAuthoringError(
                "v2_posterior_frame_sample_missing:"
                + ",".join(missing_posterior_samples)
            )
        posterior_gate_values = {
            name: row[3] for name, row in posterior_nearest.items()
        }
        if (
            posterior_nearest["fourchette"][0] ** 0.5 > 0.14
            or posterior_nearest["perineal_transition"][0] ** 0.5 > 0.14
            or posterior_nearest["anal_recess"][0] ** 0.5 > 0.20
            or posterior_gate_values["fourchette"] <= 0.0005
            or posterior_gate_values["perineal_transition"] <= 0.0001
            or posterior_gate_values["anal_recess"] >= -0.00075
        ):
            raise AdultFemaleSurfaceAuthoringError(
                "v2_posterior_frame_sample_prominence_gate_failed:"
                f"nearest={posterior_nearest}"
            )
        if changed < len(REQUIRED_RELATIONSHIPS) * base_parameters.minimum_landmark_vertices:
            raise AdultFemaleSurfaceAuthoringError(
                f"v2_refinement_insufficient_changed_vertex_count:{changed}"
            )
        bm.normal_update()
        result_pairs = _nonadjacent_intersection_face_pairs(bm)
        after = _topology_record(
            bm,
            degeneracy_area_m2=base_parameters.degeneracy_area_m2,
            include_intersections=True,
        )
        _assert_closed_single_surface(
            after,
            "v2_refinement_result",
            require_zero_global_intersections=False,
        )
        new_pairs = result_pairs.difference(source_pairs)
        if new_pairs:
            first_pair = sorted(new_pairs)[0]
            centers = [
                tuple(round(float(value), 7) for value in bm.faces[index].calc_center_median())
                for index in first_pair
            ]
            face_vertices = []
            for face_index in first_pair:
                rows = []
                for vert in bm.faces[face_index].verts:
                    posterior_u, posterior_v, posterior_depth = _local_coordinates(
                        vert.co,
                        posterior_frame,
                    )
                    rows.append(
                        {
                            "index": int(vert.index),
                            "co": tuple(round(float(value), 7) for value in vert.co),
                            "posterior_uv_depth": (
                                round(float(posterior_u), 7),
                                round(float(posterior_v), 7),
                                round(float(posterior_depth), 7),
                            ),
                            "posterior_delta_m": round(
                                float(
                                    posterior_surface_displacement(
                                        posterior_u,
                                        posterior_v,
                                        relief_scale_m=target_relief,
                                        taper_power=int(target_taper_power),
                                    )
                                ),
                                9,
                            ),
                        }
                    )
                face_vertices.append(rows)
            raise AdultFemaleSurfaceAuthoringError(
                "v2_refinement_new_global_self_intersections_detected:"
                f"before={len(source_pairs)};after={len(result_pairs)};"
                f"first_new_pair={first_pair};centers={centers};"
                f"face_vertices={face_vertices}"
            )
        result_digest = _mesh_digest(bm)
        bm.to_mesh(work_mesh)
        work_mesh.update(calc_edges=True)
        obj.data = work_mesh
        committed = True
    finally:
        bm.free()
        if not committed and work_mesh.users == 0:
            bpy.data.meshes.remove(work_mesh)

    nearest_report = {
        name: {
            "normalized_distance": float(row[0] ** 0.5),
            "nearest_normalized_uv": [float(row[1]), float(row[2])],
            "target_displacement_m": float(row[3]),
        }
        for name, row in nearest.items()
    }
    posterior_nearest_report = {
        name: {
            "normalized_distance": float(row[0] ** 0.5),
            "nearest_normalized_uv": [float(row[1]), float(row[2])],
            "target_displacement_m": float(row[3]),
        }
        for name, row in posterior_nearest.items()
    }
    all_vertex_indices = list(range(len(obj.data.vertices)))
    posterior_landmark_group_counts: dict[str, int] = {}
    for membership, indices in posterior_memberships.items():
        group_name = landmark_group_name(membership)
        group = obj.vertex_groups.get(group_name)
        if group is None:
            raise AdultFemaleSurfaceAuthoringError(
                f"v2_posterior_landmark_group_missing:{group_name}"
            )
        group.remove(all_vertex_indices)
        group.add(sorted(set(indices)), 1.0, "REPLACE")
        posterior_landmark_group_counts[group_name] = len(set(indices))
    detail = {
        "schema_version": 1,
        "base_method_id": BASE_METHOD_ID,
        "detail_method_id": METHOD_ID,
        "status": "REFINED_INACTIVE_AWAITING_INDEPENDENT_REQUALIFICATION",
        "scope": "complete_required_external_relationships_no_internal_tract_claim",
        "target_relief_scale_m": target_relief,
        "target_taper_power": int(target_taper_power),
        "theoretical_feature_sample_displacements_m": feature_sample_displacements(
            target_relief,
            int(target_taper_power),
        ),
        "nearest_authored_feature_samples": nearest_report,
        "posterior_frame": {
            "origin": [float(value) for value in posterior_frame.origin],
            "lateral_axis": [float(value) for value in posterior_frame.lateral_axis],
            "longitudinal_axis": [
                float(value) for value in posterior_frame.longitudinal_axis
            ],
            "outward_axis": [float(value) for value in posterior_frame.outward_axis],
            "half_width_m": float(posterior_frame.half_width_m),
            "half_length_m": float(posterior_frame.half_length_m),
            "max_surface_offset_m": float(posterior_frame.max_surface_offset_m),
        },
        "posterior_nearest_authored_feature_samples": posterior_nearest_report,
        "posterior_landmark_group_vertex_counts": posterior_landmark_group_counts,
        "posterior_correction_displacement_m": _summary(posterior_corrections),
        "correction_displacement_m": _summary(corrections),
        "source_mesh_digest_sha256": source_digest,
        "result_mesh_digest_sha256": result_digest,
        "source_topology": before,
        "result_topology": after,
        "inherited_global_nonadjacent_self_intersection_pairs": len(source_pairs),
        "result_global_nonadjacent_self_intersection_pairs": len(result_pairs),
        "new_global_nonadjacent_self_intersection_pairs": len(new_pairs),
        "topology_changed": False,
        "rig_weights_changed": False,
        "landmark_groups_changed": True,
        "landmark_group_names_changed": False,
        "posterior_landmark_memberships_rebound_to_curved_frame": True,
        "separate_anatomy_mesh_created": False,
        "boolean_anatomy_union_used": False,
        "copied_anatomy_geometry_used": False,
        "independent_topology_review_required": True,
        "independent_relationship_review_required": True,
        "independent_visual_prominence_review_required": True,
        "qualified": False,
        "runtime_activation_allowed": False,
    }
    try:
        metadata = json.loads(str(obj.get("adult_female_surface_metadata_json") or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        metadata = {}
    metadata["structured_detail_refinement"] = detail
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
    "author_continuous_adult_female_surface_v2",
    "refine_existing_continuous_adult_female_surface_v2",
]
