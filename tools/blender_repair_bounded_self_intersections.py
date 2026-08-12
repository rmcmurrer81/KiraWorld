"""Bounded generic coordinate repair for small genuine self-intersections.

The repair consumes the dual-tessellation exact narrow-phase diagnostic, moves
only vertices of the intersecting faces plus a one-ring falloff, preserves mesh
topology and all vertex-group weights, and commits transactionally only if the
exact global genuine-pair count reaches zero.  It contains no identity,
body-part index, or private measurement constants.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
from pathlib import Path
import struct
from typing import Any, Iterable, Mapping

import bmesh
import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))

from Core.avatar_adult_female_surface_authoring import LANDMARK_GROUP_PREFIX
from tools.blender_exact_mesh_intersections import (
    exact_nonadjacent_intersection_report,
)


class BoundedIntersectionRepairError(RuntimeError):
    """Raised without committing when the bounded repair cannot prove zero."""


def _weight_digest(obj: bpy.types.Object) -> str:
    group_names = {group.index: group.name for group in obj.vertex_groups}
    digest = hashlib.sha256()
    for vertex in obj.data.vertices:
        row = sorted(
            (
                group_names[item.group],
                float(item.weight),
            )
            for item in vertex.groups
            if item.weight > 1.0e-10
        )
        digest.update(struct.pack("<I", int(vertex.index)))
        for name, weight in row:
            encoded = name.encode("utf-8")
            digest.update(struct.pack("<I", len(encoded)))
            digest.update(encoded)
            digest.update(struct.pack("<d", weight))
    return digest.hexdigest()


def _protected_indices(
    obj: bpy.types.Object,
    prefixes: Iterable[str],
) -> set[int]:
    normalized = tuple(str(prefix) for prefix in prefixes)
    protected_group_indices = {
        group.index
        for group in obj.vertex_groups
        if any(group.name.startswith(prefix) for prefix in normalized)
    }
    return {
        int(vertex.index)
        for vertex in obj.data.vertices
        if any(
            item.group in protected_group_indices and item.weight > 1.0e-8
            for item in vertex.groups
        )
    }


def _pair_extent(record: Mapping[str, Any]) -> float:
    bounds = record["combined_bounds"]
    minimum = Vector(bounds["min"])
    maximum = Vector(bounds["max"])
    return float((maximum - minimum).length)


def _pair_severity(record: Mapping[str, Any]) -> float:
    values = []
    for result in record.get("triangle_pair_classifications", []):
        if result.get("genuine_penetration") is not True:
            continue
        if "intersection_segment_length_m" in result:
            values.append(float(result["intersection_segment_length_m"]))
        elif "coplanar_overlap_area_m2" in result:
            values.append(float(result["coplanar_overlap_area_m2"]) ** 0.5)
    return max(values, default=0.0)


def _report_severity(report: Mapping[str, Any]) -> float:
    return sum(
        _pair_severity(record)
        for record in report.get("pairs", [])
        if record.get("genuine_positive_area_or_segment_penetration") is True
    )


def _coordinate_digest(bm: bmesh.types.BMesh) -> str:
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    digest = hashlib.sha256()
    for vert in bm.verts:
        digest.update(
            struct.pack(
                "<I3d",
                int(vert.index),
                float(vert.co.x),
                float(vert.co.y),
                float(vert.co.z),
            )
        )
    return digest.hexdigest()


def _proposed_displacements(
    bm: bmesh.types.BMesh,
    report: Mapping[str, Any],
    *,
    step_multiplier: float,
    diagonal: float,
    protected: set[int],
) -> tuple[dict[int, Vector], set[int]]:
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    bm.faces.index_update()
    bm.verts.index_update()
    accumulated: defaultdict[int, Vector] = defaultdict(Vector)
    contributions: defaultdict[int, int] = defaultdict(int)
    core: set[int] = set()
    minimum_step = diagonal * 1.0e-6
    maximum_pair_step = diagonal * 7.5e-4
    for record in report.get("pairs", []):
        if record.get("genuine_positive_area_or_segment_penetration") is not True:
            continue
        first_index, second_index = map(int, record["face_indices"])
        first_face = bm.faces[first_index]
        second_face = bm.faces[second_index]
        first_center = first_face.calc_center_median()
        second_center = second_face.calc_center_median()
        direction = first_center - second_center
        if direction.length <= diagonal * 1.0e-10:
            direction = first_face.normal - second_face.normal
        if direction.length <= diagonal * 1.0e-10:
            direction = first_face.normal.copy()
        direction.normalize()
        severity = _pair_severity(record)
        pair_step = min(
            maximum_pair_step,
            max(minimum_step, severity * 0.58),
        ) * step_multiplier
        for face, sign in ((first_face, 0.5), (second_face, -0.5)):
            delta = direction * (pair_step * sign)
            for vert in face.verts:
                index = int(vert.index)
                if index in protected:
                    continue
                accumulated[index] += delta
                contributions[index] += 1
                core.add(index)

    # A small one-ring displacement falloff prevents new creases while keeping
    # the repair bounded. Opposing core faces are never overwritten by falloff.
    falloff_accumulated: defaultdict[int, Vector] = defaultdict(Vector)
    falloff_contributions: defaultdict[int, int] = defaultdict(int)
    for index in core:
        if not contributions[index]:
            continue
        core_delta = accumulated[index] / math_sqrt(float(contributions[index]))
        for edge in bm.verts[index].link_edges:
            neighbor = edge.other_vert(bm.verts[index])
            neighbor_index = int(neighbor.index)
            if neighbor_index in core or neighbor_index in protected:
                continue
            falloff_accumulated[neighbor_index] += core_delta * 0.22
            falloff_contributions[neighbor_index] += 1
    for index, delta in falloff_accumulated.items():
        accumulated[index] += delta / max(1, falloff_contributions[index])
        contributions[index] += 1

    proposed: dict[int, Vector] = {}
    maximum_vertex_step = diagonal * 8.0e-4 * step_multiplier
    for index, delta in accumulated.items():
        if contributions[index] > 1:
            delta = delta / math_sqrt(float(contributions[index]))
        if delta.length > maximum_vertex_step:
            delta.normalize()
            delta *= maximum_vertex_step
        proposed[index] = delta
    return proposed, core


def math_sqrt(value: float) -> float:
    # Local wrapper keeps Blender imports minimal and makes the scalar intent
    # explicit at the two displacement-normalization call sites.
    return value ** 0.5


def repair_bounded_self_intersections(
    obj: bpy.types.Object,
    *,
    protected_group_prefixes: tuple[str, ...] = (LANDMARK_GROUP_PREFIX,),
    maximum_iterations: int = 48,
    maximum_pair_extent_fraction: float = 0.02,
    maximum_changed_vertex_fraction: float = 0.025,
    maximum_total_displacement_fraction: float = 0.004,
) -> dict[str, Any]:
    """Resolve small exact intersections or fail without committing."""

    if obj is None or obj.type != "MESH" or obj.mode != "OBJECT":
        raise BoundedIntersectionRepairError(
            "repair_requires_one_mesh_object_in_object_mode"
        )
    if not 1 <= maximum_iterations <= 96:
        raise BoundedIntersectionRepairError("maximum_iterations_out_of_range")
    original_mesh = obj.data
    work_mesh = original_mesh.copy()
    work_mesh.name = f"{original_mesh.name}__bounded_intersection_cleanup"
    before_weight_digest = _weight_digest(obj)
    protected = _protected_indices(obj, protected_group_prefixes)
    bm = bmesh.new()
    committed = False
    try:
        bm.from_mesh(work_mesh)
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        original_coordinates = [vert.co.copy() for vert in bm.verts]
        mesh_bounds_min = Vector(
            tuple(
                min(float(vert.co[axis]) for vert in bm.verts)
                for axis in range(3)
            )
        )
        mesh_bounds_max = Vector(
            tuple(
                max(float(vert.co[axis]) for vert in bm.verts)
                for axis in range(3)
            )
        )
        diagonal = float((mesh_bounds_max - mesh_bounds_min).length)
        before = exact_nonadjacent_intersection_report(bm)
        initial_pairs = int(before["exact_genuine_penetration_pair_count"])
        if initial_pairs == 0:
            return {
                "schema_version": 1,
                "method": "bounded_exact_self_intersection_cleanup_v1",
                "intersection_audit_method": (
                    "blender_geometry_tessellation_plus_deterministic_polygon_fan"
                ),
                "status": "NO_REPAIR_NEEDED",
                "before": before,
                "after": before,
                "changed_vertex_count": 0,
                "maximum_coordinate_displacement_m": 0.0,
                "weight_digest_preserved": True,
                "topology_changed": False,
                "committed": False,
                "render_performed": False,
                "export_performed": False,
                "runtime_mutation_performed": False,
                "qualified_for_adult_foundation": False,
                "runtime_activation_allowed": False,
            }
        oversized = [
            record["face_indices"]
            for record in before["pairs"]
            if record["genuine_positive_area_or_segment_penetration"]
            and _pair_extent(record) > diagonal * maximum_pair_extent_fraction
        ]
        if oversized:
            raise BoundedIntersectionRepairError(
                f"intersection_not_bounded:pairs={oversized}"
            )

        current = before
        current_severity = _report_severity(current)
        step_multiplier = 1.0
        accepted_iterations = 0
        attempted_iterations = 0
        changed_indices: set[int] = set()
        while (
            int(current["exact_genuine_penetration_pair_count"]) > 0
            and attempted_iterations < maximum_iterations
        ):
            attempted_iterations += 1
            snapshot = [vert.co.copy() for vert in bm.verts]
            proposed, core = _proposed_displacements(
                bm,
                current,
                step_multiplier=step_multiplier,
                diagonal=diagonal,
                protected=protected,
            )
            if not proposed:
                raise BoundedIntersectionRepairError(
                    "no_unprotected_bounded_repair_vertices"
                )
            prospective = changed_indices.union(proposed)
            if len(prospective) > len(bm.verts) * maximum_changed_vertex_fraction:
                raise BoundedIntersectionRepairError(
                    "bounded_repair_vertex_fraction_exceeded"
                )
            for index, delta in proposed.items():
                bm.verts[index].co += delta
            bm.normal_update()
            candidate = exact_nonadjacent_intersection_report(bm)
            candidate_count = int(candidate["exact_genuine_penetration_pair_count"])
            candidate_severity = _report_severity(candidate)
            current_count = int(current["exact_genuine_penetration_pair_count"])
            improved = (
                candidate_count < current_count
                or (
                    candidate_count == current_count
                    and candidate_severity < current_severity - diagonal * 1.0e-10
                )
            )
            if improved:
                current = candidate
                current_severity = candidate_severity
                changed_indices.update(proposed)
                accepted_iterations += 1
                step_multiplier = min(1.5, step_multiplier * 1.08)
            else:
                for vert, coordinate in zip(bm.verts, snapshot):
                    vert.co = coordinate
                bm.normal_update()
                step_multiplier *= 0.5
                if step_multiplier < 0.015625:
                    break

        if int(current["exact_genuine_penetration_pair_count"]) != 0:
            raise BoundedIntersectionRepairError(
                "bounded_repair_did_not_reach_zero_exact_pairs:"
                f"remaining={current['exact_genuine_penetration_pair_count']}"
            )
        maximum_displacement = max(
            (
                (bm.verts[index].co - original_coordinates[index]).length
                for index in changed_indices
            ),
            default=0.0,
        )
        if maximum_displacement > diagonal * maximum_total_displacement_fraction:
            raise BoundedIntersectionRepairError(
                "bounded_repair_total_displacement_exceeded:"
                f"maximum_m={maximum_displacement}"
            )
        for index in protected:
            if (bm.verts[index].co - original_coordinates[index]).length > 1.0e-12:
                raise BoundedIntersectionRepairError(
                    f"protected_vertex_changed:{index}"
                )
        before_coordinate_digest = hashlib.sha256(
            b"".join(
                struct.pack("<3d", float(point.x), float(point.y), float(point.z))
                for point in original_coordinates
            )
        ).hexdigest()
        after_coordinate_digest = _coordinate_digest(bm)
        bm.to_mesh(work_mesh)
        work_mesh.update(calc_edges=True)
        obj.data = work_mesh
        committed = True
    finally:
        bm.free()
        if not committed and work_mesh.users == 0:
            bpy.data.meshes.remove(work_mesh)

    after_weight_digest = _weight_digest(obj)
    if after_weight_digest != before_weight_digest:
        raise BoundedIntersectionRepairError(
            "vertex_group_weights_changed_during_coordinate_only_repair"
        )
    return {
        "schema_version": 1,
        "method": "bounded_exact_self_intersection_cleanup_v1",
        "intersection_audit_method": (
            "blender_geometry_tessellation_plus_deterministic_polygon_fan"
        ),
        "status": "REPAIRED_ZERO_EXACT_PAIRS_INACTIVE",
        "before": before,
        "after": current,
        "initial_exact_genuine_pair_count": initial_pairs,
        "final_exact_genuine_pair_count": 0,
        "attempted_iterations": attempted_iterations,
        "accepted_iterations": accepted_iterations,
        "changed_vertex_count": len(changed_indices),
        "changed_vertex_fraction": len(changed_indices) / max(1, len(obj.data.vertices)),
        "maximum_coordinate_displacement_m": float(maximum_displacement),
        "source_coordinate_digest_sha256": before_coordinate_digest,
        "result_coordinate_digest_sha256": after_coordinate_digest,
        "source_weight_digest_sha256": before_weight_digest,
        "result_weight_digest_sha256": after_weight_digest,
        "weight_digest_preserved": True,
        "protected_vertex_count": len(protected),
        "protected_vertices_unchanged": True,
        "topology_changed": False,
        "vertex_count_before": len(original_coordinates),
        "vertex_count_after": len(obj.data.vertices),
        "face_count_before": len(original_mesh.polygons),
        "face_count_after": len(obj.data.polygons),
        "committed": True,
        "qualified_for_adult_foundation": False,
        "render_performed": False,
        "export_performed": False,
        "runtime_mutation_performed": False,
        "runtime_activation_allowed": False,
    }


__all__ = [
    "BoundedIntersectionRepairError",
    "repair_bounded_self_intersections",
]
