"""Blender adapter for the final bounded adult-surface v5 repair.

Only coordinates on the existing inactive v4 primary skin are staged.  The
adapter identifies the unique connected front-chart subdivision component,
uses the exact 13,380 neutral MakeHuman coordinates as fixed/tapered anchors,
harmonically reconstructs its 5k-scale subdivided vertices, and adds a subtle
local-normal relationship field.  Topology, object identity, skin weights,
landmark memberships, the rear component and all unrelated body regions are
preserved.  Gate failure leaves the input mesh untouched.
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import bmesh
import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))

from Core.avatar_adult_female_surface_authoring import (
    REQUIRED_RELATIONSHIPS,
    SurfaceFrame,
    landmark_group_name,
)
from Core.avatar_adult_female_surface_delivery_v5 import (
    BASE_DETAIL_METHOD_ID,
    METHOD_ID,
    HarmonicSurfaceParameters,
    alignment_blend,
    anchor_restore_weight,
    build_authoring_contract,
    front_surface_displacement,
)
from tools.blender_author_adult_female_external_surface import (
    AdultFemaleSurfaceAuthoringError,
    _assert_closed_single_surface,
    _local_coordinates,
    _mesh_digest,
    _nonadjacent_intersection_face_pairs,
    _skin_group_indices,
    _topology_record,
    _weight_record,
)
from tools.blender_author_adult_female_external_surface_delivery_v4 import (
    _REQUIRED_MEMBERSHIPS,
    _bounded_local_intersection_rollback,
    _group_assignment_digest,
    _membership_counts,
)


def _summary(values: Iterable[float]) -> dict[str, float | int]:
    rows = [float(value) for value in values]
    return {
        "count": len(rows),
        "minimum": min(rows, default=0.0),
        "maximum": max(rows, default=0.0),
        "mean": sum(rows) / len(rows) if rows else 0.0,
    }


def _coordinate_digest(
    positions: Sequence[Vector],
    indices: Iterable[int],
) -> str:
    digest = hashlib.sha256()
    for index in sorted(int(value) for value in indices):
        point = positions[index]
        digest.update(
            (
                f"{index}|{float(point.x):.12f}|{float(point.y):.12f}|"
                f"{float(point.z):.12f}\n"
            ).encode("ascii")
        )
    return digest.hexdigest()


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


def _new_vertex_components(
    bm: bmesh.types.BMesh,
    original_anchor_count: int,
) -> list[dict[str, Any]]:
    new_indices = {
        int(vert.index)
        for vert in bm.verts
        if int(vert.index) >= int(original_anchor_count)
    }
    pending = set(new_indices)
    components: list[dict[str, Any]] = []
    while pending:
        seed = min(pending)
        stack = [seed]
        indices: set[int] = set()
        while stack:
            index = int(stack.pop())
            if index not in pending:
                continue
            pending.remove(index)
            indices.add(index)
            for edge in bm.verts[index].link_edges:
                for other in edge.verts:
                    other_index = int(other.index)
                    if other_index in pending:
                        stack.append(other_index)
        anchors = {
            int(other.index)
            for index in indices
            for edge in bm.verts[index].link_edges
            for other in edge.verts
            if int(other.index) < int(original_anchor_count)
        }
        coordinates = [bm.verts[index].co for index in indices]
        components.append(
            {
                "indices": indices,
                "anchor_indices": anchors,
                "size": len(indices),
                "minimum_index": min(indices),
                "maximum_index": max(indices),
                "bounds": {
                    "minimum": [
                        min(float(co[axis]) for co in coordinates)
                        for axis in range(3)
                    ],
                    "maximum": [
                        max(float(co[axis]) for co in coordinates)
                        for axis in range(3)
                    ],
                },
            }
        )
    return sorted(components, key=lambda row: int(row["size"]), reverse=True)


def _select_unique_front_component(
    components: Sequence[Mapping[str, Any]],
    *,
    frame: SurfaceFrame,
    parameters: HarmonicSurfaceParameters,
    bm: bmesh.types.BMesh,
) -> dict[str, Any]:
    outward = Vector(frame.outward_axis)
    origin = Vector(frame.origin)
    eligible: list[dict[str, Any]] = []
    for raw in components:
        size = int(raw["size"])
        anchors = set(raw["anchor_indices"])
        if not (
            parameters.minimum_front_component_vertices
            <= size
            <= parameters.maximum_front_component_vertices
            and parameters.minimum_front_anchor_neighbors
            <= len(anchors)
            <= parameters.maximum_front_anchor_neighbors
        ):
            continue
        indices = set(raw["indices"])
        front_context = 0
        for index in indices:
            co = bm.verts[index].co
            u, v, depth = _local_coordinates(co, frame)
            if (
                abs(u) <= 1.55
                and -1.45 <= v <= 1.35
                and abs(depth) <= float(frame.max_surface_offset_m)
                and float((co - origin).dot(outward)) >= -float(frame.max_surface_offset_m)
            ):
                front_context += 1
        overlap_fraction = front_context / max(1, size)
        if overlap_fraction < 0.70:
            continue
        row = dict(raw)
        row["front_context_vertex_count"] = front_context
        row["front_context_fraction"] = overlap_fraction
        eligible.append(row)
    if len(eligible) != 1:
        raise AdultFemaleSurfaceAuthoringError(
            "delivery_v5_unique_front_component_gate_failed:"
            f"eligible={len(eligible)};"
            f"components={[int(row['size']) for row in components]}"
        )
    return eligible[0]


def _harmonic_reconstruct(
    bm: bmesh.types.BMesh,
    *,
    component_indices: set[int],
    parameters: HarmonicSurfaceParameters,
) -> dict[str, Any]:
    adjacency: dict[int, tuple[int, ...]] = {}
    for index in sorted(component_indices):
        neighbors = sorted(
            {
                int(other.index)
                for edge in bm.verts[index].link_edges
                for other in edge.verts
                if int(other.index) != index
            }
        )
        if len(neighbors) < 2:
            raise AdultFemaleSurfaceAuthoringError(
                f"delivery_v5_sparse_harmonic_vertex:{index}:{len(neighbors)}"
            )
        adjacency[index] = tuple(neighbors)

    coordinates = {
        index: bm.verts[index].co.copy() for index in component_indices
    }
    iteration_maxima: list[float] = []
    converged = False
    for iteration in range(1, parameters.harmonic_maximum_iterations + 1):
        pending: dict[int, Vector] = {}
        maximum_step = 0.0
        for index in sorted(component_indices):
            neighbors = adjacency[index]
            average = sum(
                (
                    coordinates[neighbor]
                    if neighbor in component_indices
                    else bm.verts[neighbor].co
                    for neighbor in neighbors
                ),
                Vector((0.0, 0.0, 0.0)),
            ) / float(len(neighbors))
            current = coordinates[index]
            proposal = current.lerp(average, parameters.harmonic_relaxation)
            pending[index] = proposal
            maximum_step = max(maximum_step, float((proposal - current).length))
        coordinates = pending
        iteration_maxima.append(maximum_step)
        if (
            iteration >= parameters.harmonic_minimum_iterations
            and maximum_step <= parameters.harmonic_tolerance_m
        ):
            converged = True
            break
    if not converged:
        raise AdultFemaleSurfaceAuthoringError(
            "delivery_v5_harmonic_solver_did_not_converge:"
            f"iterations={len(iteration_maxima)};"
            f"last_step={iteration_maxima[-1]:.12g}"
        )
    for index, coordinate in coordinates.items():
        bm.verts[index].co = coordinate
    bm.normal_update()

    maximum_residual = 0.0
    mean_residual = 0.0
    for index in sorted(component_indices):
        neighbors = adjacency[index]
        average = sum(
            (bm.verts[neighbor].co for neighbor in neighbors),
            Vector((0.0, 0.0, 0.0)),
        ) / float(len(neighbors))
        residual = float((average - bm.verts[index].co).length)
        maximum_residual = max(maximum_residual, residual)
        mean_residual += residual
    mean_residual /= max(1, len(component_indices))
    return {
        "method": "uniform_graph_harmonic_jacobi_with_fixed_original_anchors",
        "component_vertex_count": len(component_indices),
        "iterations": len(iteration_maxima),
        "converged": True,
        "tolerance_m": parameters.harmonic_tolerance_m,
        "first_iteration_maximum_step_m": iteration_maxima[0],
        "last_iteration_maximum_step_m": iteration_maxima[-1],
        "maximum_final_harmonic_residual_m": maximum_residual,
        "mean_final_harmonic_residual_m": mean_residual,
    }


def repair_existing_continuous_adult_female_surface_delivery_v5(
    obj: bpy.types.Object,
    *,
    neutral_original_positions: Sequence[Vector],
    front_frame: SurfaceFrame,
    parameters: HarmonicSurfaceParameters,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Stage the final front-chart coordinate repair; never save or activate."""

    if obj is None or obj.type != "MESH" or obj.mode != "OBJECT":
        raise AdultFemaleSurfaceAuthoringError("delivery_v5_requires_object_mesh")
    if not bool(obj.get("primary_surface")):
        raise AdultFemaleSurfaceAuthoringError("delivery_v5_requires_primary_surface")
    if obj.get("adult_female_surface_detail_method_id") != BASE_DETAIL_METHOD_ID:
        raise AdultFemaleSurfaceAuthoringError("delivery_v5_requires_exact_v4_base")
    if bool(obj.get("runtime_activation_allowed")):
        raise AdultFemaleSurfaceAuthoringError(
            "delivery_v5_refuses_runtime_activatable_object"
        )
    if len(neutral_original_positions) != parameters.original_anchor_vertex_count:
        raise AdultFemaleSurfaceAuthoringError(
            "delivery_v5_neutral_anchor_count_mismatch:"
            f"expected={parameters.original_anchor_vertex_count};"
            f"actual={len(neutral_original_positions)}"
        )
    if len(obj.data.vertices) <= parameters.original_anchor_vertex_count:
        raise AdultFemaleSurfaceAuthoringError(
            "delivery_v5_requires_existing_subdivided_surface"
        )

    contract = build_authoring_contract(project_root, front_frame, parameters)
    original_mesh = obj.data
    work_mesh = original_mesh.copy()
    work_mesh.name = f"{original_mesh.name}__{METHOD_ID}_coordinate_repair"
    bm = bmesh.new()
    committed = False
    try:
        bm.from_mesh(work_mesh)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.verts.index_update()
        bm.faces.index_update()
        source_positions = [vert.co.copy() for vert in bm.verts]
        source_topology = _topology_record(
            bm,
            degeneracy_area_m2=parameters.degeneracy_area_m2,
            include_intersections=True,
        )
        _assert_closed_single_surface(
            source_topology,
            "delivery_v5_source",
            require_zero_global_intersections=False,
        )
        source_pairs = _nonadjacent_intersection_face_pairs(bm)
        source_mesh_digest = _mesh_digest(bm)

        all_group_names = {
            int(group.index): str(group.name) for group in obj.vertex_groups
        }
        source_assignment_digest = _group_assignment_digest(bm, all_group_names)
        available_groups = {group.name: int(group.index) for group in obj.vertex_groups}
        required_group_indices: dict[str, int] = {}
        for membership in sorted(_REQUIRED_MEMBERSHIPS):
            group_name = landmark_group_name(membership)
            if group_name not in available_groups:
                raise AdultFemaleSurfaceAuthoringError(
                    f"delivery_v5_required_landmark_group_missing:{group_name}"
                )
            required_group_indices[membership] = available_groups[group_name]
        source_membership_counts = _membership_counts(bm, required_group_indices)
        sparse = sorted(
            membership
            for membership, count in source_membership_counts.items()
            if count < parameters.minimum_feature_vertices
        )
        if sparse:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v5_source_landmark_density_failed:" + ",".join(sparse)
            )

        components = _new_vertex_components(
            bm,
            parameters.original_anchor_vertex_count,
        )
        front_component = _select_unique_front_component(
            components,
            frame=front_frame,
            parameters=parameters,
            bm=bm,
        )
        front_indices = set(front_component["indices"])
        anchor_indices = set(front_component["anchor_indices"])
        rear_new_indices = {
            int(index)
            for row in components
            if set(row["indices"]) != front_indices
            for index in row["indices"]
        }
        eligible_indices = front_indices.union(anchor_indices)
        unrelated_indices = set(range(len(source_positions))).difference(
            eligible_indices
        )
        rear_source_coordinate_digest = _coordinate_digest(
            source_positions,
            rear_new_indices,
        )
        unrelated_source_coordinate_digest = _coordinate_digest(
            source_positions,
            unrelated_indices,
        )
        if max(anchor_indices, default=-1) >= len(neutral_original_positions):
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v5_front_component_anchor_index_out_of_range"
            )

        anchor_weights: dict[int, float] = {}
        anchor_corrections: list[float] = []
        for index in sorted(anchor_indices):
            neutral = Vector(neutral_original_positions[index])
            u, v, _depth = _local_coordinates(neutral, front_frame)
            weight = anchor_restore_weight(u, v, parameters)
            anchor_weights[index] = weight
            before = bm.verts[index].co.copy()
            bm.verts[index].co = before.lerp(neutral, weight)
            anchor_corrections.append(float((bm.verts[index].co - before).length))
        if sum(weight >= 0.999999 for weight in anchor_weights.values()) < 60:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v5_too_few_fully_restored_neutral_anchors"
            )

        harmonic = _harmonic_reconstruct(
            bm,
            component_indices=front_indices,
            parameters=parameters,
        )

        bm.normal_update()
        outward = Vector(front_frame.outward_axis).normalized()
        relationship_displacements: list[float] = []
        relationship_vertex_count = 0
        for index in sorted(front_indices.union(anchor_indices)):
            vert = bm.verts[index]
            u, v, depth = _local_coordinates(vert.co, front_frame)
            if abs(depth) > float(front_frame.max_surface_offset_m):
                continue
            alignment = float(vert.normal.dot(outward))
            blend = alignment_blend(
                alignment,
                minimum_alignment=parameters.minimum_front_normal_alignment,
                fade_width=parameters.alignment_fade_width,
            )
            if blend <= 0.0:
                continue
            delta = front_surface_displacement(
                u,
                v,
                prominence_scale_m=parameters.front_prominence_scale_m,
                asymmetry_fraction=parameters.deterministic_asymmetry_fraction,
            ) * blend
            if abs(delta) <= 1.0e-12:
                continue
            local_normal = vert.normal.normalized()
            if float(local_normal.dot(outward)) <= 0.0:
                continue
            vert.co += local_normal * delta
            relationship_displacements.append(float(delta))
            relationship_vertex_count += 1
        if relationship_vertex_count < 1000:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v5_relationship_field_too_sparse:"
                f"{relationship_vertex_count}"
            )
        bm.normal_update()

        proposed_positions = [vert.co.copy() for vert in bm.verts]
        changed_indices = {
            index
            for index, source in enumerate(source_positions)
            if (proposed_positions[index] - source).length > 1.0e-12
        }
        maximum_correction = max(
            (
                (proposed_positions[index] - source_positions[index]).length
                for index in changed_indices
            ),
            default=0.0,
        )
        if maximum_correction > parameters.maximum_total_correction_m:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v5_total_correction_exceeded:"
                f"{maximum_correction:.12g}>"
                f"{parameters.maximum_total_correction_m:.12g}"
            )

        proposed_topology = _topology_record(
            bm,
            degeneracy_area_m2=parameters.degeneracy_area_m2,
            include_intersections=True,
        )
        _assert_closed_single_surface(
            proposed_topology,
            "delivery_v5_proposal",
            require_zero_global_intersections=False,
        )
        proposed_pairs = _nonadjacent_intersection_face_pairs(bm)
        proposed_mesh_digest = _mesh_digest(bm)
        result_pairs, collision_repair = _bounded_local_intersection_rollback(
            bm,
            source_positions=source_positions,
            proposed_positions=proposed_positions,
            source_pairs=source_pairs,
            proposed_pairs=proposed_pairs,
        )
        new_pairs = result_pairs.difference(source_pairs)
        if new_pairs:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v5_new_global_self_intersections_detected:"
                f"before={len(source_pairs)};after={len(result_pairs)};"
                f"first={sorted(new_pairs)[0]};"
                f"repair={json.dumps(collision_repair, sort_keys=True)}"
            )

        result_topology = _topology_record(
            bm,
            degeneracy_area_m2=parameters.degeneracy_area_m2,
            include_intersections=True,
        )
        _assert_closed_single_surface(
            result_topology,
            "delivery_v5_result",
            require_zero_global_intersections=False,
        )
        for name in ("vertices", "edges", "faces"):
            if int(result_topology[name]) != int(source_topology[name]):
                raise AdultFemaleSurfaceAuthoringError(
                    f"delivery_v5_topology_count_changed:{name}"
                )

        result_assignment_digest = _group_assignment_digest(bm, all_group_names)
        if result_assignment_digest != source_assignment_digest:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v5_vertex_group_or_weight_assignments_changed"
            )
        result_membership_counts = _membership_counts(bm, required_group_indices)
        if result_membership_counts != source_membership_counts:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v5_landmark_memberships_changed"
            )
        weights = _weight_record(
            bm,
            _skin_group_indices(obj),
            parameters.maximum_skin_influences,
        )
        if (
            weights["unweighted_vertex_count"] != 0
            or weights["weight_sum_minimum"] < 0.999
            or weights["weight_sum_maximum"] > 1.001
            or weights["maximum_positive_skin_influences"]
            > parameters.maximum_skin_influences
        ):
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v5_result_skin_weights_invalid"
            )

        result_mesh_digest = _mesh_digest(bm)
        final_positions = [vert.co.copy() for vert in bm.verts]
        final_changed_indices = {
            index
            for index, source in enumerate(source_positions)
            if (final_positions[index] - source).length > 1.0e-12
        }
        changed_outside_front_component = final_changed_indices.difference(
            eligible_indices
        )
        if changed_outside_front_component:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v5_changed_vertex_outside_front_component:"
                f"{min(changed_outside_front_component)}"
            )
        rear_result_coordinate_digest = _coordinate_digest(
            final_positions,
            rear_new_indices,
        )
        unrelated_result_coordinate_digest = _coordinate_digest(
            final_positions,
            unrelated_indices,
        )
        if rear_result_coordinate_digest != rear_source_coordinate_digest:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v5_rear_component_coordinate_drift"
            )
        if unrelated_result_coordinate_digest != unrelated_source_coordinate_digest:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v5_unrelated_coordinate_drift"
            )
        changed_bounds = {
            "minimum": [
                min(
                    (float(final_positions[index][axis]) for index in final_changed_indices),
                    default=0.0,
                )
                for axis in range(3)
            ],
            "maximum": [
                max(
                    (float(final_positions[index][axis]) for index in final_changed_indices),
                    default=0.0,
                )
                for axis in range(3)
            ],
        }
        bm.to_mesh(work_mesh)
        work_mesh.update(calc_edges=True)
        obj.data = work_mesh
        committed = True
    finally:
        bm.free()
        if not committed and work_mesh.users == 0:
            bpy.data.meshes.remove(work_mesh)

    component_inventory = [
        {
            "size": int(row["size"]),
            "anchor_neighbor_count": len(set(row["anchor_indices"])),
            "minimum_index": int(row["minimum_index"]),
            "maximum_index": int(row["maximum_index"]),
            "bounds": row["bounds"],
        }
        for row in components
    ]
    detail = {
        "schema_version": 1,
        "base_detail_method_id": BASE_DETAIL_METHOD_ID,
        "detail_method_id": METHOD_ID,
        "status": "FINAL_BOUNDED_SURFACE_REPAIR_INACTIVE_AWAITING_OWNER_VISUAL_DECISION",
        "scope": "front_chart_component_only_rear_v4_component_preserved",
        "front_frame": _frame_record(front_frame),
        "parameters": {
            name: getattr(parameters, name)
            for name in parameters.__dataclass_fields__
        },
        "source_mesh_digest_sha256": source_mesh_digest,
        "proposed_mesh_digest_sha256": proposed_mesh_digest,
        "result_mesh_digest_sha256": result_mesh_digest,
        "source_topology": source_topology,
        "proposed_topology": proposed_topology,
        "result_topology": result_topology,
        "new_vertex_component_inventory": component_inventory,
        "selected_front_component_vertex_count": len(front_indices),
        "selected_front_anchor_neighbor_count": len(anchor_indices),
        "rear_component_vertex_count_preserved": next(
            (
                int(row["size"])
                for row in components
                if set(row["indices"]) != front_indices
            ),
            0,
        ),
        "rear_component_source_coordinate_digest_sha256": rear_source_coordinate_digest,
        "rear_component_result_coordinate_digest_sha256": rear_result_coordinate_digest,
        "unrelated_source_coordinate_digest_sha256": unrelated_source_coordinate_digest,
        "unrelated_result_coordinate_digest_sha256": unrelated_result_coordinate_digest,
        "changed_vertex_count_outside_front_component": 0,
        "neutral_original_position_count": len(neutral_original_positions),
        "neutral_anchor_restore_weights": _summary(anchor_weights.values()),
        "fully_restored_neutral_anchor_count": sum(
            weight >= 0.999999 for weight in anchor_weights.values()
        ),
        "unchanged_boundary_anchor_count": sum(
            weight <= 1.0e-12 for weight in anchor_weights.values()
        ),
        "neutral_anchor_coordinate_corrections_m": _summary(anchor_corrections),
        "harmonic_reconstruction": harmonic,
        "relationship_displacements_m": _summary(relationship_displacements),
        "relationship_vertex_count": relationship_vertex_count,
        "proposed_changed_vertex_count": len(changed_indices),
        "result_changed_vertex_count": len(final_changed_indices),
        "maximum_total_vertex_correction_m": maximum_correction,
        "changed_coordinate_bounds": changed_bounds,
        "inherited_global_nonadjacent_self_intersection_pairs": len(source_pairs),
        "proposed_global_nonadjacent_self_intersection_pairs": len(proposed_pairs),
        "proposed_new_global_nonadjacent_self_intersection_pairs": len(
            proposed_pairs.difference(source_pairs)
        ),
        "result_global_nonadjacent_self_intersection_pairs": len(result_pairs),
        "new_global_nonadjacent_self_intersection_pairs": len(new_pairs),
        "bounded_new_intersection_repair": collision_repair,
        "source_group_assignment_digest_sha256": source_assignment_digest,
        "result_group_assignment_digest_sha256": result_assignment_digest,
        "landmark_vertex_counts_before": source_membership_counts,
        "landmark_vertex_counts_after": result_membership_counts,
        "skin_weights": weights,
        "topology_changed": False,
        "existing_vertex_indices_preserved": True,
        "skin_weights_preserved_exactly": True,
        "landmark_memberships_preserved_exactly": True,
        "same_primary_mesh_object": True,
        "source_anatomy_geometry_copied": False,
        "separate_anatomy_mesh_created": False,
        "boolean_anatomy_union_used": False,
        "internal_tract_claimed": False,
        "rear_v4_component_changed": False,
        "face_geometry_changed": False,
        "rig_changed": False,
        "appearance_changed": False,
        "nails_changed": False,
        "hair_dependency": False,
        "runtime_activation_allowed": False,
        "candidate_created": False,
        "render_performed": False,
        "export_performed": False,
        "owner_visual_review_required": True,
        "visual_attempt_number": 2,
        "v6_allowed_after_this_attempt": False,
        "qualified": False,
        "contract": contract,
    }
    try:
        metadata = json.loads(str(obj.get("adult_female_surface_metadata_json") or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        metadata = {}
    metadata["harmonic_surface_delivery_v5"] = detail
    metadata["result_mesh_digest_sha256"] = result_mesh_digest
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
    "repair_existing_continuous_adult_female_surface_delivery_v5",
]
