"""Blender adapter for a generic continuous adult-female external surface.

The adapter subdivides and displaces a bounded patch on one existing closed,
connected primary body mesh.  It never imports anatomy geometry, creates an
anatomy object, invokes a Boolean, renders, exports, selects a runtime body, or
claims independent qualification.  New vertices receive interpolated,
normalized skin weights; deterministic non-deforming landmark groups and
metadata are added for later independent inspection.

Import this module from a Blender script and call
``author_continuous_adult_female_surface``.  There is intentionally no CLI or
top-level execution path here.
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path
import struct
from typing import Any, Iterable, Mapping

import bmesh
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))

from Core.avatar_adult_female_surface_authoring import (
    AuthoringParameters,
    LANDMARK_GROUP_PREFIX,
    METHOD_ID,
    REQUIRED_RELATIONSHIPS,
    SurfaceFrame,
    build_authoring_contract,
    landmark_group_name,
    landmark_memberships,
    surface_displacement,
)
from tools.blender_exact_mesh_intersections import (
    exact_nonadjacent_intersection_report,
)


FORBIDDEN_WRONG_SEX_TOKENS = (
    "helper-genital",
    "helper_genital",
    "male_helper",
    "penis",
    "scrotum",
    "testicle",
)


class AdultFemaleSurfaceAuthoringError(RuntimeError):
    """Raised before commit when the method cannot preserve its contract."""


def _text_tokens(obj: bpy.types.Object) -> str:
    values = [obj.name, obj.data.name]
    values.extend(group.name for group in obj.vertex_groups)
    return " ".join(values).lower()


def _assert_source_object(obj: bpy.types.Object) -> None:
    if obj is None or obj.type != "MESH":
        raise AdultFemaleSurfaceAuthoringError(
            "source_primary_surface_must_be_one_mesh_object"
        )
    if obj.mode != "OBJECT":
        raise AdultFemaleSurfaceAuthoringError("source_object_must_be_in_object_mode")
    forbidden = [
        token for token in FORBIDDEN_WRONG_SEX_TOKENS if token in _text_tokens(obj)
    ]
    if forbidden or obj.get("wrong_sex_helper_present") is True:
        raise AdultFemaleSurfaceAuthoringError(
            "wrong_sex_helper_present:" + ",".join(sorted(forbidden))
        )
    if any(group.name.startswith(LANDMARK_GROUP_PREFIX) for group in obj.vertex_groups):
        raise AdultFemaleSurfaceAuthoringError(
            "existing_adult_surface_landmark_groups_present"
        )


def _component_sizes(bm: bmesh.types.BMesh) -> list[int]:
    unseen = set(bm.verts)
    sizes: list[int] = []
    while unseen:
        seed = unseen.pop()
        todo = [seed]
        count = 0
        while todo:
            current = todo.pop()
            count += 1
            for edge in current.link_edges:
                neighbor = edge.other_vert(current)
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    todo.append(neighbor)
        sizes.append(count)
    return sorted(sizes, reverse=True)


def _coincident_duplicate_triangles(bm: bmesh.types.BMesh) -> int:
    triangulated = bm.copy()
    try:
        bmesh.ops.triangulate(
            triangulated,
            faces=list(triangulated.faces),
            quad_method="BEAUTY",
            ngon_method="BEAUTY",
        )
        keys: Counter[tuple[tuple[float, float, float], ...]] = Counter()
        for face in triangulated.faces:
            coordinates = tuple(
                sorted(
                    tuple(round(float(component), 10) for component in vert.co)
                    for vert in face.verts
                )
            )
            keys[coordinates] += 1
        return sum(count * (count - 1) // 2 for count in keys.values())
    finally:
        triangulated.free()


def _nonadjacent_intersection_face_pairs(
    bm: bmesh.types.BMesh,
) -> set[tuple[int, int]]:
    report = exact_nonadjacent_intersection_report(bm)
    return {
        tuple(int(value) for value in record["face_indices"])
        for record in report["pairs"]
        if record["genuine_positive_area_or_segment_penetration"] is True
    }


def _topology_record(
    bm: bmesh.types.BMesh,
    *,
    degeneracy_area_m2: float,
    include_intersections: bool,
) -> dict[str, Any]:
    bm.normal_update()
    boundary_edges = sum(len(edge.link_faces) == 1 for edge in bm.edges)
    nonmanifold_edges = sum(len(edge.link_faces) not in {1, 2} for edge in bm.edges)
    components = _component_sizes(bm)
    record: dict[str, Any] = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "primary_surface_components": len(components),
        "component_sizes": components,
        "boundary_edges": boundary_edges,
        "nonmanifold_edges": nonmanifold_edges,
        "degenerate_faces": sum(
            face.calc_area() <= degeneracy_area_m2 for face in bm.faces
        ),
        "coincident_duplicate_triangle_pairs": (
            _coincident_duplicate_triangles(bm)
        ),
    }
    if include_intersections:
        record["nonadjacent_self_intersection_pairs"] = (
            len(_nonadjacent_intersection_face_pairs(bm))
        )
    return record


def _assert_closed_single_surface(
    record: Mapping[str, Any],
    label: str,
    *,
    require_zero_global_intersections: bool,
) -> None:
    requirements = {
        "primary_surface_components": 1,
        "boundary_edges": 0,
        "nonmanifold_edges": 0,
        "degenerate_faces": 0,
        "coincident_duplicate_triangle_pairs": 0,
    }
    failures = [
        f"{name}={record.get(name)!r}"
        for name, expected in requirements.items()
        if record.get(name) != expected
    ]
    if require_zero_global_intersections and record.get(
        "nonadjacent_self_intersection_pairs", 0
    ) != 0:
        failures.append(
            "nonadjacent_self_intersection_pairs="
            f"{record.get('nonadjacent_self_intersection_pairs')!r}"
        )
    if failures:
        raise AdultFemaleSurfaceAuthoringError(
            f"{label}_topology_blocked:" + ";".join(failures)
        )


def _mesh_digest(bm: bmesh.types.BMesh) -> str:
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.faces.index_update()
    digest = hashlib.sha256()
    digest.update(struct.pack("<QQ", len(bm.verts), len(bm.faces)))
    for vert in bm.verts:
        digest.update(
            struct.pack(
                "<3d",
                float(vert.co.x),
                float(vert.co.y),
                float(vert.co.z),
            )
        )
    for face in bm.faces:
        indices = [int(vert.index) for vert in face.verts]
        digest.update(struct.pack("<I", len(indices)))
        digest.update(struct.pack(f"<{len(indices)}I", *indices))
    return digest.hexdigest()


def _local_coordinates(point: Vector, frame: SurfaceFrame) -> tuple[float, float, float]:
    delta = point - Vector(frame.origin)
    lateral = Vector(frame.lateral_axis)
    longitudinal = Vector(frame.longitudinal_axis)
    outward = Vector(frame.outward_axis)
    return (
        delta.dot(lateral) / frame.half_width_m,
        delta.dot(longitudinal) / frame.half_length_m,
        delta.dot(outward),
    )


def _region_faces(
    bm: bmesh.types.BMesh,
    frame: SurfaceFrame,
    parameters: AuthoringParameters,
) -> list[bmesh.types.BMFace]:
    outward = Vector(frame.outward_axis)
    bm.normal_update()
    selected = []
    for face in bm.faces:
        u, v, depth = _local_coordinates(face.calc_center_median(), frame)
        if (
            u * u + v * v < 1.0
            and abs(depth) <= frame.max_surface_offset_m
            and face.normal.dot(outward) >= parameters.minimum_face_normal_alignment
        ):
            selected.append(face)
    if len(selected) < 8:
        raise AdultFemaleSurfaceAuthoringError(
            f"bounded_surface_region_too_sparse:faces={len(selected)}"
        )
    selected_set = set(selected)
    unseen = set(selected)
    component_count = 0
    while unseen:
        component_count += 1
        seed = unseen.pop()
        todo = [seed]
        while todo:
            current = todo.pop()
            for edge in current.edges:
                for neighbor in edge.link_faces:
                    if neighbor in selected_set and neighbor in unseen:
                        unseen.remove(neighbor)
                        todo.append(neighbor)
    if component_count != 1:
        raise AdultFemaleSurfaceAuthoringError(
            f"bounded_surface_region_not_connected:components={component_count}"
        )
    return selected


def _skin_group_indices(obj: bpy.types.Object) -> set[int]:
    armature_names: set[str] = set()
    for modifier in obj.modifiers:
        if modifier.type == "ARMATURE" and modifier.object is not None:
            armature_names.update(
                bone.name for bone in modifier.object.data.bones if bone.use_deform
            )
    groups = {
        group.index
        for group in obj.vertex_groups
        if not group.name.startswith(LANDMARK_GROUP_PREFIX)
        and (not armature_names or group.name in armature_names)
    }
    if not groups:
        raise AdultFemaleSurfaceAuthoringError("source_skin_weight_groups_missing")
    return groups


def _source_weight_rows(
    obj: bpy.types.Object,
    group_indices: set[int],
) -> list[dict[int, float]]:
    rows: list[dict[int, float]] = []
    for vertex in obj.data.vertices:
        row = {
            int(item.group): float(item.weight)
            for item in vertex.groups
            if item.group in group_indices and item.weight > 1.0e-8
        }
        total = sum(row.values())
        if total <= 1.0e-8:
            raise AdultFemaleSurfaceAuthoringError(
                f"source_skin_weight_missing:vertex={vertex.index}"
            )
        rows.append(row)
    return rows


def _normalized_top_weights(
    values: Mapping[int, float],
    maximum: int,
) -> dict[int, float]:
    ordered = sorted(
        ((int(index), float(weight)) for index, weight in values.items() if weight > 1.0e-10),
        key=lambda item: (-item[1], item[0]),
    )[:maximum]
    total = sum(weight for _, weight in ordered)
    return {
        index: weight / total for index, weight in ordered
    } if total > 1.0e-10 else {}


def _interpolate_new_weights(
    bm: bmesh.types.BMesh,
    original_vertex_count: int,
    source_positions: list[Vector],
    source_rows: list[dict[int, float]],
    maximum_influences: int,
) -> int:
    deform = bm.verts.layers.deform.verify()
    tree = KDTree(len(source_positions))
    for index, point in enumerate(source_positions):
        tree.insert(point, index)
    tree.balance()
    interpolated = 0
    sample_count = min(len(source_positions), max(4, maximum_influences * 2))
    for vert in bm.verts:
        if int(vert.index) < original_vertex_count:
            continue
        samples = tree.find_n(vert.co, sample_count)
        accumulated: defaultdict[int, float] = defaultdict(float)
        exact = [sample for sample in samples if float(sample[2]) <= 1.0e-12]
        if exact:
            _, index, _distance = exact[0]
            accumulated.update(source_rows[int(index)])
        else:
            normalization = 0.0
            for _point, index, distance in samples:
                factor = 1.0 / max(float(distance), 1.0e-9) ** 2
                normalization += factor
                for group_index, weight in source_rows[int(index)].items():
                    accumulated[group_index] += factor * weight
            if normalization > 0.0:
                for group_index in list(accumulated):
                    accumulated[group_index] /= normalization
        row = _normalized_top_weights(accumulated, maximum_influences)
        if not row:
            raise AdultFemaleSurfaceAuthoringError(
                "new_vertex_skin_weight_interpolation_failed"
            )
        target = vert[deform]
        target.clear()
        for group_index, weight in row.items():
            target[group_index] = weight
        interpolated += 1
    return interpolated


def _weight_record(
    bm: bmesh.types.BMesh,
    skin_group_indices: set[int],
    maximum_influences: int,
) -> dict[str, Any]:
    deform = bm.verts.layers.deform.verify()
    sums: list[float] = []
    counts: list[int] = []
    for vert in bm.verts:
        row = [
            float(weight)
            for group_index, weight in vert[deform].items()
            if group_index in skin_group_indices and weight > 1.0e-8
        ]
        sums.append(sum(row))
        counts.append(len(row))
    return {
        "vertex_count": len(bm.verts),
        "weighted_vertex_count": sum(value > 1.0e-8 for value in sums),
        "unweighted_vertex_count": sum(value <= 1.0e-8 for value in sums),
        "weight_sum_minimum": min(sums, default=0.0),
        "weight_sum_maximum": max(sums, default=0.0),
        "maximum_positive_skin_influences": max(counts, default=0),
        "new_vertex_maximum_influences_required": maximum_influences,
    }


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


def _author_region(
    bm: bmesh.types.BMesh,
    frame: SurfaceFrame,
    parameters: AuthoringParameters,
) -> tuple[dict[str, list[int]], int, set[int]]:
    outward = Vector(frame.outward_axis)
    bm.normal_update()
    memberships: defaultdict[str, list[int]] = defaultdict(list)
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
        for membership in landmark_memberships(
            u,
            v,
            threshold=parameters.landmark_influence_threshold,
        ):
            memberships[membership].append(int(vert.index))
        delta = surface_displacement(
            u,
            v,
            relief_scale_m=parameters.relief_scale_m,
            taper_power=parameters.boundary_taper_power,
        )
        if abs(delta) > 1.0e-12:
            # The direction is fixed by the supplied anatomical frame so the
            # field stays deterministic even on irregular source tessellation.
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
            "insufficient_local_topology_for_landmarks:" + ",".join(missing)
        )
    if changed < len(REQUIRED_RELATIONSHIPS) * parameters.minimum_landmark_vertices:
        raise AdultFemaleSurfaceAuthoringError(
            f"insufficient_authored_vertex_count:{changed}"
        )
    return (
        {name: sorted(indices) for name, indices in memberships.items()},
        changed,
        changed_indices,
    )


def _install_landmark_groups(
    obj: bpy.types.Object,
    memberships: Mapping[str, Iterable[int]],
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for membership in sorted(memberships):
        name = landmark_group_name(membership)
        group = obj.vertex_groups.new(name=name)
        indices = list(memberships[membership])
        group.add(indices, 1.0, "REPLACE")
        mapping[membership] = name
    return mapping


def author_continuous_adult_female_surface(
    obj: bpy.types.Object,
    *,
    frame: SurfaceFrame,
    parameters: AuthoringParameters,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Author one bounded continuous patch and return an unreviewed report.

    Geometry is prepared on a private mesh datablock and committed only after
    topology, intersection, relationship-density, and skin-weight checks pass.
    The caller remains responsible for saving an inactive workspace and for
    obtaining exact-hash independent evidence.
    """

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
            "source",
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
                "source_authoring_region_self_intersections="
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
                "source_vertex_index_stability_lost_during_subdivision"
            )
        interpolated = _interpolate_new_weights(
            bm,
            original_vertex_count,
            source_positions,
            source_rows,
            parameters.maximum_skin_influences,
        )
        memberships, changed, changed_indices = _author_region(
            bm,
            frame,
            parameters,
        )
        # Make the authored patch's surface interpretation explicit.  Leaving
        # displaced quads non-planar permits different valid diagonals to give
        # contradictory intersection results.  Triangulating only faces that
        # touch authored vertices removes that ambiguity without creating a
        # second mesh, changing any source vertex coordinate, or altering
        # weights.
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
            "result",
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
                "authored_region_self_intersections="
                f"{len(authored_region_intersections)}"
            )
        if len(result_intersection_pairs) > len(source_intersection_pairs):
            raise AdultFemaleSurfaceAuthoringError(
                "new_global_self_intersections_detected:"
                f"before={len(source_intersection_pairs)};"
                f"after={len(result_intersection_pairs)}"
            )
        weights = _weight_record(
            bm,
            skin_groups,
            parameters.maximum_skin_influences,
        )
        if weights["unweighted_vertex_count"] != 0:
            raise AdultFemaleSurfaceAuthoringError(
                "result_contains_unweighted_vertices"
            )
        if not (
            weights["weight_sum_minimum"] >= 0.999
            and weights["weight_sum_maximum"] <= 1.001
        ):
            raise AdultFemaleSurfaceAuthoringError(
                "result_skin_weights_not_normalized"
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

    group_map = _install_landmark_groups(obj, memberships)
    metadata = {
        "schema_version": 1,
        "method_id": METHOD_ID,
        "status": "AUTHORED_INACTIVE_AWAITING_INDEPENDENT_REVIEW",
        "body_class": "adult_female",
        "relationships": list(REQUIRED_RELATIONSHIPS),
        "landmark_groups": group_map,
        "source_mesh_digest_sha256": source_digest,
        "result_mesh_digest_sha256": result_digest,
        "opening_representation": contract["opening_representation"],
        "source_anatomy_geometry_copied": False,
        "wrong_sex_helper_used": False,
        "separate_anatomy_mesh_created": False,
        "boolean_anatomy_union_used": False,
        "painted_only_relationships": False,
        "skin_weights_preserved_and_new_vertices_interpolated": True,
        "authored_nonplanar_faces_triangulated": (
            triangulated_authored_face_count
        ),
        "intersection_audit_method": (
            "dual_tessellation_bvh_broad_phase_exact_triangle_narrow_phase"
        ),
        "independent_topology_review_required": True,
        "independent_relationship_review_required": True,
        "inherited_global_nonadjacent_self_intersection_pairs": len(
            source_intersection_pairs
        ),
        "result_global_nonadjacent_self_intersection_pairs": len(
            result_intersection_pairs
        ),
        "authored_region_nonadjacent_self_intersection_pairs": len(
            authored_region_intersections
        ),
        "global_topology_ready_for_qualification": (
            len(result_intersection_pairs) == 0
        ),
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


__all__ = [
    "AdultFemaleSurfaceAuthoringError",
    "author_continuous_adult_female_surface",
]
