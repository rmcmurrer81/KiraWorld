"""Topology-preserving Blender adapter for organic adult-surface delivery v4.

The adapter accepts only the inactive, exact v3 primary skin.  It stages a
mesh-data copy, reverses the known v3 normal displacement, applies two bounded
normal-axis fairing passes, and adds the lower-amplitude organic v4 field.
Every vertex, edge, face, skin assignment and landmark membership is retained.

There is intentionally no CLI, file write, render, export, assignment,
publication, activation, hair, clothing, Boolean, or separate anatomy-object
path in this module.
"""

from __future__ import annotations

import hashlib
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
    REQUIRED_RELATIONSHIPS,
    SurfaceFrame,
    landmark_group_name,
)
from Core.avatar_adult_female_surface_authoring_v3 import (
    front_support_taper as legacy_v3_front_support_taper,
    front_surface_displacement as legacy_v3_front_surface_displacement,
    rear_support_taper as legacy_v3_rear_support_taper,
    rear_surface_displacement as legacy_v3_rear_surface_displacement,
)
from Core.avatar_adult_female_surface_delivery_v4 import (
    BASE_DETAIL_METHOD_ID,
    COLLISION_REPAIR_MAX_FRACTION_OF_CHANGED_VERTICES,
    COLLISION_REPAIR_MAX_PASSES,
    COLLISION_REPAIR_MAX_VERTICES,
    COLLISION_REPAIR_RETENTION_BY_RING,
    METHOD_ID,
    OrganicSurfaceParameters,
    alignment_blend,
    build_authoring_contract,
    front_support_taper,
    front_surface_displacement,
    rear_support_taper,
    rear_surface_displacement,
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


def _legacy_alignment_blend(alignment: float, minimum_alignment: float) -> float:
    """Mirror v3's cubic alignment blend for deterministic field reversal."""

    t = min(
        1.0,
        max(0.0, (float(alignment) - float(minimum_alignment)) / 0.18),
    )
    return t * t * (3.0 - 2.0 * t)


def _group_assignment_digest(
    bm: bmesh.types.BMesh,
    group_names: Mapping[int, str],
) -> str:
    """Hash every deform assignment without changing any group or weight."""

    layer = bm.verts.layers.deform.active
    if layer is None:
        raise AdultFemaleSurfaceAuthoringError("delivery_v4_deform_layer_missing")
    digest = hashlib.sha256()
    for index, name in sorted(group_names.items()):
        digest.update(f"G|{int(index)}|{name}\n".encode("utf-8"))
    for vert in sorted(bm.verts, key=lambda item: int(item.index)):
        values = [
            (int(group_index), float(weight))
            for group_index, weight in vert[layer].items()
            if int(group_index) in group_names and float(weight) > 0.0
        ]
        for group_index, weight in sorted(values):
            digest.update(
                f"V|{int(vert.index)}|{group_index}|{weight:.12f}\n".encode("ascii")
            )
    return digest.hexdigest()


def _membership_counts(
    bm: bmesh.types.BMesh,
    group_indices: Mapping[str, int],
) -> dict[str, int]:
    layer = bm.verts.layers.deform.active
    if layer is None:
        raise AdultFemaleSurfaceAuthoringError("delivery_v4_deform_layer_missing")
    return {
        membership: sum(
            1
            for vert in bm.verts
            if float(vert[layer].get(int(group_index), 0.0)) > 0.0
        )
        for membership, group_index in group_indices.items()
    }


def _selected_vertices(
    bm: bmesh.types.BMesh,
    *,
    frame: SurfaceFrame,
    organic_support: Callable[[float, float], float],
    legacy_support: Callable[[float, float], float],
    minimum_alignment: float,
    minimum_depth_m: float,
) -> tuple[list[bmesh.types.BMVert], dict[int, float], dict[int, float]]:
    outward = Vector(frame.outward_axis)
    selected: list[bmesh.types.BMVert] = []
    alignments: dict[int, float] = {}
    envelopes: dict[int, float] = {}
    bm.normal_update()
    for vert in bm.verts:
        u, v, depth = _local_coordinates(vert.co, frame)
        envelope = max(organic_support(u, v), legacy_support(u, v))
        alignment = float(vert.normal.dot(outward))
        if (
            envelope > 0.0
            and abs(depth) <= float(frame.max_surface_offset_m)
            and depth >= float(minimum_depth_m)
            and alignment >= float(minimum_alignment)
        ):
            selected.append(vert)
            alignments[int(vert.index)] = alignment
            envelopes[int(vert.index)] = envelope
    return selected, alignments, envelopes


def _fair_along_outward_axis(
    bm: bmesh.types.BMesh,
    vertices: list[bmesh.types.BMVert],
    *,
    frame: SurfaceFrame,
    support: Callable[[float, float], float],
    blend_by_index: Mapping[int, float],
    iterations: int,
    strength: float,
    maximum_step_m: float,
) -> list[float]:
    """Reduce residual plate edges without tangential shrink or topology edits."""

    if iterations <= 0 or strength <= 0.0:
        return []
    outward = Vector(frame.outward_axis)
    selected = {int(vert.index): vert for vert in vertices}
    applied_steps: list[float] = []
    for _iteration in range(int(iterations)):
        snapshot = {int(vert.index): vert.co.copy() for vert in bm.verts}
        pending: dict[int, float] = {}
        for index, vert in selected.items():
            neighbor_indices = {
                int(other.index)
                for edge in vert.link_edges
                for other in edge.verts
                if int(other.index) != index
            }
            if len(neighbor_indices) < 2:
                continue
            average = sum(
                (snapshot[neighbor] for neighbor in neighbor_indices),
                Vector((0.0, 0.0, 0.0)),
            ) / float(len(neighbor_indices))
            u, v, _depth = _local_coordinates(snapshot[index], frame)
            envelope = support(u, v) * float(blend_by_index.get(index, 0.0))
            raw_step = float((average - snapshot[index]).dot(outward))
            step = raw_step * float(strength) * envelope
            step = max(-float(maximum_step_m), min(float(maximum_step_m), step))
            if abs(step) > 1.0e-12:
                pending[index] = step
        for index, step in pending.items():
            selected[index].co += outward * step
            applied_steps.append(step)
        bm.normal_update()
    return applied_steps


def _bounded_local_intersection_rollback(
    bm: bmesh.types.BMesh,
    *,
    source_positions: list[Vector],
    proposed_positions: list[Vector],
    source_pairs: set[tuple[int, int]],
    proposed_pairs: set[tuple[int, int]],
) -> tuple[set[tuple[int, int]], dict[str, Any]]:
    """Locally retain source coordinates until proposal-only pairs disappear.

    Only vertices actually moved by this v4 proposal are eligible.  Vertices
    of an offending face return fully to their source coordinate; the first
    and second connected rings retain 45% and 75% of the proposed correction.
    The process is bounded by pass, vertex-count and changed-region-fraction
    gates.  It never edits topology, weights, groups, or inherited source
    intersection pairs.
    """

    proposed_changed = {
        index
        for index, source in enumerate(source_positions)
        if (proposed_positions[index] - source).length > 1.0e-12
    }
    current_pairs = set(proposed_pairs)
    new_pairs = current_pairs.difference(source_pairs)
    record: dict[str, Any] = {
        "mode": "local_source_coordinate_retention_backtracking",
        "status": "NOT_REQUIRED" if not new_pairs else "IN_PROGRESS",
        "proposed_changed_vertex_count": len(proposed_changed),
        "proposed_intersection_pair_count": len(proposed_pairs),
        "proposed_new_pair_count": len(new_pairs),
        "maximum_passes": COLLISION_REPAIR_MAX_PASSES,
        "maximum_vertices": COLLISION_REPAIR_MAX_VERTICES,
        "maximum_fraction_of_changed_vertices": (
            COLLISION_REPAIR_MAX_FRACTION_OF_CHANGED_VERTICES
        ),
        "retention_by_offending_face_ring": list(
            COLLISION_REPAIR_RETENTION_BY_RING
        ),
        "passes": [],
        "repaired_vertex_count": 0,
        "final_intersection_pair_count": len(current_pairs),
        "final_new_pair_count": len(new_pairs),
    }
    if not new_pairs:
        return current_pairs, record

    retention_by_index: dict[int, float] = {}
    for pass_index in range(1, COLLISION_REPAIR_MAX_PASSES + 1):
        seed_indices = {
            int(vert.index)
            for pair in new_pairs
            for face_index in pair
            for vert in bm.faces[int(face_index)].verts
            if int(vert.index) in proposed_changed
        }
        if not seed_indices:
            record["status"] = "FAILED_NO_MOVED_VERTEX_IN_NEW_PAIR"
            break

        rings: list[set[int]] = [set(seed_indices)]
        visited = set(seed_indices)
        for _ring_index in range(1, len(COLLISION_REPAIR_RETENTION_BY_RING)):
            next_ring = {
                int(other.index)
                for index in rings[-1]
                for edge in bm.verts[index].link_edges
                for other in edge.verts
                if int(other.index) not in visited
                and int(other.index) in proposed_changed
            }
            rings.append(next_ring)
            visited.update(next_ring)

        candidate_retention = dict(retention_by_index)
        for ring, maximum_retention in zip(
            rings,
            COLLISION_REPAIR_RETENTION_BY_RING,
        ):
            for index in ring:
                candidate_retention[index] = min(
                    candidate_retention.get(index, 1.0),
                    float(maximum_retention),
                )
        candidate_count = len(candidate_retention)
        candidate_fraction = candidate_count / max(1, len(proposed_changed))
        if candidate_count > COLLISION_REPAIR_MAX_VERTICES:
            record["status"] = "FAILED_VERTEX_BOUND_EXCEEDED"
            record["rejected_candidate_vertex_count"] = candidate_count
            break
        if candidate_fraction > COLLISION_REPAIR_MAX_FRACTION_OF_CHANGED_VERTICES:
            record["status"] = "FAILED_CHANGED_REGION_FRACTION_EXCEEDED"
            record["rejected_candidate_fraction"] = candidate_fraction
            break

        retention_by_index = candidate_retention
        for index, retention in retention_by_index.items():
            bm.verts[index].co = source_positions[index] + (
                proposed_positions[index] - source_positions[index]
            ) * float(retention)
        bm.normal_update()
        current_pairs = _nonadjacent_intersection_face_pairs(bm)
        new_pairs = current_pairs.difference(source_pairs)
        record["passes"].append(
            {
                "pass": pass_index,
                "offending_seed_vertex_count": len(seed_indices),
                "ring_vertex_counts": [len(ring) for ring in rings],
                "cumulative_repaired_vertex_count": len(retention_by_index),
                "minimum_retention": min(retention_by_index.values()),
                "result_intersection_pair_count": len(current_pairs),
                "result_new_pair_count": len(new_pairs),
            }
        )
        if not new_pairs:
            record["status"] = "APPLIED_BOUNDED_LOCAL_ROLLBACK"
            break

    record["repaired_vertex_count"] = len(retention_by_index)
    record["fully_restored_source_vertex_count"] = sum(
        value <= 1.0e-12 for value in retention_by_index.values()
    )
    record["minimum_retention"] = min(retention_by_index.values(), default=1.0)
    record["final_intersection_pair_count"] = len(current_pairs)
    record["final_new_pair_count"] = len(new_pairs)
    if new_pairs and record["status"] == "IN_PROGRESS":
        record["status"] = "FAILED_MAXIMUM_PASSES_EXHAUSTED"
    return current_pairs, record


def refine_existing_continuous_adult_female_surface_delivery_v4(
    obj: bpy.types.Object,
    *,
    front_frame: SurfaceFrame,
    rear_frame: SurfaceFrame,
    parameters: OrganicSurfaceParameters,
    legacy_v3_front_prominence_scale_m: float,
    legacy_v3_rear_prominence_scale_m: float,
    legacy_v3_minimum_front_normal_alignment: float,
    legacy_v3_minimum_rear_normal_alignment: float,
    front_visible_sheet_minimum_outward_depth_m: float,
    rear_visible_sheet_minimum_outward_depth_m: float,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Replace an exact inactive v3 field in memory; never save or activate."""

    if obj is None or obj.type != "MESH" or obj.mode != "OBJECT":
        raise AdultFemaleSurfaceAuthoringError("delivery_v4_requires_object_mesh")
    if not bool(obj.get("primary_surface")):
        raise AdultFemaleSurfaceAuthoringError("delivery_v4_requires_primary_surface")
    if obj.get("adult_female_surface_detail_method_id") != BASE_DETAIL_METHOD_ID:
        raise AdultFemaleSurfaceAuthoringError("delivery_v4_requires_exact_v3_base")
    if bool(obj.get("runtime_activation_allowed")):
        raise AdultFemaleSurfaceAuthoringError(
            "delivery_v4_refuses_runtime_activatable_object"
        )
    if not 0.0035 <= float(legacy_v3_front_prominence_scale_m) <= 0.009:
        raise AdultFemaleSurfaceAuthoringError(
            "delivery_v4_legacy_front_scale_out_of_bounds"
        )
    if not 0.003 <= float(legacy_v3_rear_prominence_scale_m) <= 0.008:
        raise AdultFemaleSurfaceAuthoringError(
            "delivery_v4_legacy_rear_scale_out_of_bounds"
        )
    if not 0.05 <= float(legacy_v3_minimum_front_normal_alignment) <= 0.50:
        raise AdultFemaleSurfaceAuthoringError(
            "delivery_v4_legacy_front_alignment_out_of_bounds"
        )
    if not 0.05 <= float(legacy_v3_minimum_rear_normal_alignment) <= 0.50:
        raise AdultFemaleSurfaceAuthoringError(
            "delivery_v4_legacy_rear_alignment_out_of_bounds"
        )

    contract = build_authoring_contract(
        project_root,
        front_frame,
        rear_frame,
        parameters,
    )
    available_groups = {group.name: int(group.index) for group in obj.vertex_groups}
    required_group_indices: dict[str, int] = {}
    for membership in sorted(_REQUIRED_MEMBERSHIPS):
        group_name = landmark_group_name(membership)
        if group_name not in available_groups:
            raise AdultFemaleSurfaceAuthoringError(
                f"delivery_v4_required_landmark_group_missing:{group_name}"
            )
        required_group_indices[membership] = available_groups[group_name]

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
        before = _topology_record(
            bm,
            degeneracy_area_m2=parameters.degeneracy_area_m2,
            include_intersections=True,
        )
        _assert_closed_single_surface(
            before,
            "delivery_v4_source",
            require_zero_global_intersections=False,
        )
        source_pairs = _nonadjacent_intersection_face_pairs(bm)
        source_mesh_digest = _mesh_digest(bm)
        all_group_names = {
            int(group.index): str(group.name) for group in obj.vertex_groups
        }
        source_assignment_digest = _group_assignment_digest(bm, all_group_names)
        source_membership_counts = _membership_counts(bm, required_group_indices)
        sparse_source_memberships = sorted(
            membership
            for membership, count in source_membership_counts.items()
            if count < parameters.minimum_feature_vertices
        )
        if sparse_source_memberships:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v4_source_landmark_density_failed:"
                + ",".join(sparse_source_memberships)
            )

        front_vertices, front_alignments, front_envelopes = _selected_vertices(
            bm,
            frame=front_frame,
            organic_support=front_support_taper,
            legacy_support=legacy_v3_front_support_taper,
            minimum_alignment=min(
                parameters.minimum_front_normal_alignment,
                float(legacy_v3_minimum_front_normal_alignment),
            ),
            minimum_depth_m=float(front_visible_sheet_minimum_outward_depth_m),
        )
        rear_vertices, rear_alignments, rear_envelopes = _selected_vertices(
            bm,
            frame=rear_frame,
            organic_support=rear_support_taper,
            legacy_support=legacy_v3_rear_support_taper,
            minimum_alignment=min(
                parameters.minimum_rear_normal_alignment,
                float(legacy_v3_minimum_rear_normal_alignment),
            ),
            minimum_depth_m=float(rear_visible_sheet_minimum_outward_depth_m),
        )
        front_indices = {int(vert.index) for vert in front_vertices}
        rear_indices = {int(vert.index) for vert in rear_vertices}
        overlap = front_indices.intersection(rear_indices)
        if overlap:
            raise AdultFemaleSurfaceAuthoringError(
                f"delivery_v4_front_rear_chart_vertex_overlap:{len(overlap)}"
            )
        if len(front_vertices) < 64 or len(rear_vertices) < 24:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v4_visible_sheet_too_sparse:"
                f"front={len(front_vertices)};rear={len(rear_vertices)}"
            )

        front_outward = Vector(front_frame.outward_axis)
        rear_outward = Vector(rear_frame.outward_axis)
        front_legacy_removed: list[float] = []
        rear_legacy_removed: list[float] = []
        front_new_added: list[float] = []
        rear_new_added: list[float] = []
        front_new_blends: dict[int, float] = {}
        rear_new_blends: dict[int, float] = {}

        # Phase 1: reverse only the v3 field.  Chart u/v are unchanged by an
        # outward-axis displacement, so the analytic reversal is deterministic.
        for vert in front_vertices:
            index = int(vert.index)
            u, v, _depth = _local_coordinates(vert.co, front_frame)
            legacy_blend = _legacy_alignment_blend(
                front_alignments[index],
                float(legacy_v3_minimum_front_normal_alignment),
            )
            old_delta = legacy_v3_front_surface_displacement(
                u,
                v,
                prominence_scale_m=float(legacy_v3_front_prominence_scale_m),
            ) * legacy_blend
            if abs(old_delta) > 1.0e-12:
                vert.co -= front_outward * old_delta
                front_legacy_removed.append(old_delta)
            front_new_blends[index] = alignment_blend(
                front_alignments[index],
                minimum_alignment=parameters.minimum_front_normal_alignment,
                fade_width=parameters.alignment_fade_width,
            )

        for vert in rear_vertices:
            index = int(vert.index)
            u, v, _depth = _local_coordinates(vert.co, rear_frame)
            legacy_blend = _legacy_alignment_blend(
                rear_alignments[index],
                float(legacy_v3_minimum_rear_normal_alignment),
            )
            old_delta = legacy_v3_rear_surface_displacement(
                u,
                v,
                prominence_scale_m=float(legacy_v3_rear_prominence_scale_m),
            ) * legacy_blend
            if abs(old_delta) > 1.0e-12:
                vert.co -= rear_outward * old_delta
                rear_legacy_removed.append(old_delta)
            rear_new_blends[index] = alignment_blend(
                rear_alignments[index],
                minimum_alignment=parameters.minimum_rear_normal_alignment,
                fade_width=parameters.alignment_fade_width,
            )

        # Normal-only fairing softens any inherited boundary/ridge residue.  It
        # cannot shrink the chart laterally or longitudinally.
        front_fairing = _fair_along_outward_axis(
            bm,
            front_vertices,
            frame=front_frame,
            support=lambda u, v: max(
                front_support_taper(u, v), legacy_v3_front_support_taper(u, v)
            ),
            blend_by_index=front_new_blends,
            iterations=parameters.fairing_iterations,
            strength=parameters.fairing_strength,
            maximum_step_m=parameters.fairing_max_step_m,
        )
        rear_fairing = _fair_along_outward_axis(
            bm,
            rear_vertices,
            frame=rear_frame,
            support=lambda u, v: max(
                rear_support_taper(u, v), legacy_v3_rear_support_taper(u, v)
            ),
            blend_by_index=rear_new_blends,
            iterations=parameters.fairing_iterations,
            strength=parameters.fairing_strength,
            maximum_step_m=parameters.fairing_max_step_m,
        )

        # Phase 2: add the broad, low-amplitude organic field.
        for vert in front_vertices:
            index = int(vert.index)
            u, v, _depth = _local_coordinates(vert.co, front_frame)
            new_delta = front_surface_displacement(
                u,
                v,
                prominence_scale_m=parameters.front_prominence_scale_m,
                asymmetry_fraction=parameters.deterministic_asymmetry_fraction,
            ) * front_new_blends[index]
            if abs(new_delta) > 1.0e-12:
                vert.co += front_outward * new_delta
                front_new_added.append(new_delta)

        for vert in rear_vertices:
            index = int(vert.index)
            u, v, _depth = _local_coordinates(vert.co, rear_frame)
            new_delta = rear_surface_displacement(
                u,
                v,
                prominence_scale_m=parameters.rear_prominence_scale_m,
            ) * rear_new_blends[index]
            if abs(new_delta) > 1.0e-12:
                vert.co += rear_outward * new_delta
                rear_new_added.append(new_delta)

        bm.normal_update()
        proposed_positions = [vert.co.copy() for vert in bm.verts]
        proposed_changed_indices = {
            index
            for index, source in enumerate(source_positions)
            if (proposed_positions[index] - source).length > 1.0e-12
        }
        proposed_maximum_total_correction = max(
            (
                (proposed_positions[index] - source_positions[index]).length
                for index in proposed_changed_indices
            ),
            default=0.0,
        )
        if proposed_maximum_total_correction > parameters.maximum_total_correction_m:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v4_total_correction_exceeded:"
                f"{proposed_maximum_total_correction:.9f}>"
                f"{parameters.maximum_total_correction_m:.9f}"
            )

        proposed_topology = _topology_record(
            bm,
            degeneracy_area_m2=parameters.degeneracy_area_m2,
            include_intersections=True,
        )
        _assert_closed_single_surface(
            proposed_topology,
            "delivery_v4_proposed_result",
            require_zero_global_intersections=False,
        )
        for key in (
            "vertices",
            "edges",
            "faces",
            "primary_surface_components",
            "boundary_edges",
            "nonmanifold_edges",
        ):
            if proposed_topology[key] != before[key]:
                raise AdultFemaleSurfaceAuthoringError(
                    "delivery_v4_proposed_topology_changed:"
                    f"{key}:{before[key]}->{proposed_topology[key]}"
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
        bm.normal_update()
        after = _topology_record(
            bm,
            degeneracy_area_m2=parameters.degeneracy_area_m2,
            include_intersections=True,
        )
        _assert_closed_single_surface(
            after,
            "delivery_v4_result",
            require_zero_global_intersections=False,
        )
        for key in (
            "vertices",
            "edges",
            "faces",
            "primary_surface_components",
            "boundary_edges",
            "nonmanifold_edges",
        ):
            if after[key] != before[key]:
                raise AdultFemaleSurfaceAuthoringError(
                    f"delivery_v4_topology_changed:{key}:{before[key]}->{after[key]}"
                )
        new_pairs = result_pairs.difference(source_pairs)
        changed_indices = {
            index
            for index, source in enumerate(source_positions)
            if (bm.verts[index].co - source).length > 1.0e-12
        }
        maximum_total_correction = max(
            (
                (bm.verts[index].co - source_positions[index]).length
                for index in changed_indices
            ),
            default=0.0,
        )
        if new_pairs:
            first_pair = sorted(new_pairs)[0]
            diagnostic: list[dict[str, Any]] = []
            for face_index in first_pair:
                face = bm.faces[int(face_index)]
                diagnostic.append(
                    {
                        "face_index": int(face_index),
                        "center": [
                            round(float(value), 8)
                            for value in face.calc_center_median()
                        ],
                        "normal": [round(float(value), 8) for value in face.normal],
                        "vertices": [
                            {
                                "index": int(vert.index),
                                "coordinate": [
                                    round(float(value), 8) for value in vert.co
                                ],
                                "source_coordinate": [
                                    round(float(value), 8)
                                    for value in source_positions[int(vert.index)]
                                ],
                                "displacement_m": round(
                                    float(
                                        (
                                            vert.co
                                            - source_positions[int(vert.index)]
                                        ).length
                                    ),
                                    9,
                                ),
                                "front_selected": int(vert.index) in front_indices,
                                "rear_selected": int(vert.index) in rear_indices,
                                "front_uv_depth": [
                                    round(float(value), 8)
                                    for value in _local_coordinates(
                                        vert.co,
                                        front_frame,
                                    )
                                ],
                                "rear_uv_depth": [
                                    round(float(value), 8)
                                    for value in _local_coordinates(
                                        vert.co,
                                        rear_frame,
                                    )
                                ],
                            }
                            for vert in face.verts
                        ],
                    }
                )
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v4_new_global_self_intersections_detected:"
                f"before={len(source_pairs)};after={len(result_pairs)};"
                f"first_new_pair={first_pair};"
                f"bounded_repair={json.dumps(collision_repair, sort_keys=True)};"
                f"diagnostic={json.dumps(diagnostic, sort_keys=True)}"
            )

        result_assignment_digest = _group_assignment_digest(bm, all_group_names)
        if result_assignment_digest != source_assignment_digest:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v4_vertex_group_or_weight_assignments_changed"
            )
        result_membership_counts = _membership_counts(bm, required_group_indices)
        if result_membership_counts != source_membership_counts:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v4_landmark_memberships_changed"
            )
        skin_groups = _skin_group_indices(obj)
        weights = _weight_record(bm, skin_groups, parameters.maximum_skin_influences)
        if weights["unweighted_vertex_count"] != 0:
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v4_result_contains_unweighted_vertices"
            )
        if not (
            weights["weight_sum_minimum"] >= 0.999
            and weights["weight_sum_maximum"] <= 1.001
            and weights["maximum_positive_skin_influences"]
            <= parameters.maximum_skin_influences
        ):
            raise AdultFemaleSurfaceAuthoringError(
                "delivery_v4_result_skin_weights_invalid"
            )

        result_mesh_digest = _mesh_digest(bm)
        changed_coordinates = [bm.verts[index].co for index in changed_indices]
        changed_coordinate_bounds = {
            "minimum": [
                min((float(co[axis]) for co in changed_coordinates), default=0.0)
                for axis in range(3)
            ],
            "maximum": [
                max((float(co[axis]) for co in changed_coordinates), default=0.0)
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

    detail = {
        "schema_version": 1,
        "base_detail_method_id": BASE_DETAIL_METHOD_ID,
        "detail_method_id": METHOD_ID,
        "status": "TARGETED_ORGANIC_REPAIR_INACTIVE_AWAITING_OWNER_VISUAL_REVIEW",
        "scope": "complete_required_external_relationships_no_internal_tract_claim",
        "front_frame": _frame_record(front_frame),
        "rear_frame": _frame_record(rear_frame),
        "parameters": {
            name: getattr(parameters, name)
            for name in parameters.__dataclass_fields__
        },
        "legacy_v3_parameters": {
            "front_prominence_scale_m": float(legacy_v3_front_prominence_scale_m),
            "rear_prominence_scale_m": float(legacy_v3_rear_prominence_scale_m),
            "minimum_front_normal_alignment": float(
                legacy_v3_minimum_front_normal_alignment
            ),
            "minimum_rear_normal_alignment": float(
                legacy_v3_minimum_rear_normal_alignment
            ),
        },
        "source_mesh_digest_sha256": source_mesh_digest,
        "proposed_mesh_digest_sha256": proposed_mesh_digest,
        "result_mesh_digest_sha256": result_mesh_digest,
        "source_topology": before,
        "proposed_topology_before_bounded_collision_repair": proposed_topology,
        "result_topology": after,
        "source_group_assignment_digest_sha256": source_assignment_digest,
        "result_group_assignment_digest_sha256": result_assignment_digest,
        "landmark_vertex_counts_before": source_membership_counts,
        "landmark_vertex_counts_after": result_membership_counts,
        "front_selected_vertex_count": len(front_vertices),
        "rear_selected_vertex_count": len(rear_vertices),
        "front_selection_envelope": _summary(front_envelopes.values()),
        "rear_selection_envelope": _summary(rear_envelopes.values()),
        "front_removed_v3_displacement_m": _summary(front_legacy_removed),
        "rear_removed_v3_displacement_m": _summary(rear_legacy_removed),
        "front_normal_axis_fairing_m": _summary(front_fairing),
        "rear_normal_axis_fairing_m": _summary(rear_fairing),
        "front_added_v4_displacement_m": _summary(front_new_added),
        "rear_added_v4_displacement_m": _summary(rear_new_added),
        "proposed_changed_vertex_count": len(proposed_changed_indices),
        "changed_vertex_count": len(changed_indices),
        "proposed_maximum_total_vertex_correction_m": (
            proposed_maximum_total_correction
        ),
        "maximum_total_vertex_correction_m": maximum_total_correction,
        "bounded_new_intersection_repair": collision_repair,
        "changed_coordinate_bounds": changed_coordinate_bounds,
        "inherited_global_nonadjacent_self_intersection_pairs": len(source_pairs),
        "proposed_global_nonadjacent_self_intersection_pairs": len(proposed_pairs),
        "proposed_new_global_nonadjacent_self_intersection_pairs": len(
            proposed_pairs.difference(source_pairs)
        ),
        "result_global_nonadjacent_self_intersection_pairs": len(result_pairs),
        "new_global_nonadjacent_self_intersection_pairs": len(new_pairs),
        "skin_weights": weights,
        "topology_changed": False,
        "existing_vertex_indices_preserved": True,
        "skin_weights_preserved_exactly": True,
        "landmark_memberships_preserved_exactly": True,
        "same_primary_mesh_object": True,
        "source_anatomy_geometry_copied": False,
        "separate_anatomy_mesh_created": False,
        "boolean_anatomy_union_used": False,
        "painted_only_relationships": False,
        "internal_tract_claimed": False,
        "hair_dependency": False,
        "scalp_geometry_changed": False,
        "qualified": False,
        "runtime_activation_allowed": False,
        "render_performed": False,
        "export_performed": False,
        "owner_visual_review_required": True,
        "contract": contract,
    }
    try:
        metadata = json.loads(str(obj.get("adult_female_surface_metadata_json") or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        metadata = {}
    metadata["organic_surface_delivery_v4"] = detail
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
    "refine_existing_continuous_adult_female_surface_delivery_v4",
]
