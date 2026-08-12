#!/usr/bin/env python3
"""Bounded attempt 02 repair for the R19 BlackProject radial patch probe.

Attempt 01 is immutable evidence.  This worker reuses its orchestration but
replaces the two failed mechanisms: it closes the innermost concentric ring
with an explicit 17-vertex structured median grid, and it expresses the new
surface in the exact source-patch object space before the 34-vertex seam weld.
No source-interior vertex, face, coordinate, or weight is reused.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_build_kira_r19_blackproject_radial_patch_probe as attempt_01_worker  # noqa: E402


OUTPUT_REL = Path(
    "RecoverySprint/continuation_20260802/"
    "r19_blackproject_radial_patch/attempt_02"
)
SEAM_WELD_TOLERANCE_M = 1.0e-6
EXPECTED_SEAM_MERGES = 34
PATCH_FACE_INDICES: set[int] = set()
ORIGINAL_MAKE_RADIAL_PATCH = attempt_01_worker.make_radial_patch
ORIGINAL_EXACT_AUDIT = attempt_01_worker.bmesh_exact_audit


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def vertex_weight_record(obj: bpy.types.Object, vertex_index: int) -> dict[str, float]:
    return attempt_01_worker.normalized_top_four(
        {
            obj.vertex_groups[assignment.group].name: float(assignment.weight)
            for assignment in obj.data.vertices[vertex_index].groups
            if float(assignment.weight) > 1.0e-10
        }
    )


def make_radial_patch_attempt_02(
    source_patch: bpy.types.Object,
    ordered_cycle: list[int],
    collection: bpy.types.Collection,
) -> tuple[bpy.types.Object, dict[str, object]]:
    patch, record = ORIGINAL_MAKE_RADIAL_PATCH(
        source_patch,
        ordered_cycle,
        collection,
    )
    n = len(ordered_cycle)
    if n != EXPECTED_SEAM_MERGES:
        raise ValueError(f"unexpected source seam size: {n}")
    if len(patch.data.vertices) != len(attempt_01_worker.RING_SCALES) * n:
        raise ValueError("attempt-01 open annulus topology drifted")
    if record.get("structured_grid_generated_vertex_count") != 0:
        raise ValueError("attempt-01 grid_fill behavior changed; bounded repair must be reviewed")

    inner_start = (len(attempt_01_worker.RING_SCALES) - 1) * n
    existing_weights = [
        vertex_weight_record(patch, inner_start + index)
        for index in range(n)
    ]
    source_matrix = source_patch.matrix_world.copy()
    source_inverse = source_matrix.inverted()
    # Attempt 01 authored correct world coordinates on an identity object.
    # Convert them to the exact source-patch local frame and then assign the
    # exact source object matrix.  World coordinates remain byte-close while
    # Blender join now sees the same local/object transform as the base body.
    original_world = [patch.matrix_world @ vertex.co for vertex in patch.data.vertices]
    for vertex, world in zip(patch.data.vertices, original_world):
        vertex.co = source_inverse @ world
    patch.matrix_world = source_matrix
    source_boundary_local = [
        source_patch.data.vertices[index].co.copy() for index in ordered_cycle
    ]
    source_boundary_world = [
        source_matrix @ point for point in source_boundary_local
    ]
    # Snap only the 34 seam vertices to their exact reviewed source-local
    # coordinates.  This is boundary preservation, not source-interior reuse.
    matched_source_indices: set[int] = set()
    for vertex_index in range(n):
        world = original_world[vertex_index]
        match = min(
            range(n),
            key=lambda index: (world - source_boundary_world[index]).length,
        )
        if (world - source_boundary_world[match]).length > 1.0e-8:
            raise ValueError("could not map attempt-02 seam vertex exactly")
        matched_source_indices.add(match)
        patch.data.vertices[vertex_index].co = source_boundary_local[match]
    if len(matched_source_indices) != n:
        raise ValueError("attempt-02 seam mapping was not one-to-one")
    patch.data.update()
    maximum_world_reframe_delta = max(
        (
            patch.matrix_world @ vertex.co - original_world[vertex.index]
        ).length
        for vertex in patch.data.vertices
    )
    maximum_outer_to_exact_source_delta = max(
        min(
            (patch.matrix_world @ patch.data.vertices[index].co - source).length
            for source in source_boundary_world
        )
        for index in range(n)
    )
    if maximum_outer_to_exact_source_delta > 1.0e-12:
        raise ValueError(
            "object-space seam does not exactly reproduce source boundary: "
            f"{maximum_outer_to_exact_source_delta:.12g} m"
        )

    bm = bmesh.new()
    bm.from_mesh(patch.data)
    bm.verts.ensure_lookup_table()
    inner = [bm.verts[inner_start + index] for index in range(n)]
    inner_mean = sum((vertex.co for vertex in inner), inner[0].co.copy() * 0.0) / n
    center_start = ((inner[n - 1].co + inner[0].co) * 0.5).lerp(
        inner_mean,
        0.18,
    )
    center_end = ((inner[n // 2 - 1].co + inner[n // 2].co) * 0.5).lerp(
        inner_mean,
        0.18,
    )
    centerline = [
        bm.verts.new(
            center_start.lerp(
                center_end,
                float(index) / float((n // 2) - 1),
            )
        )
        for index in range(n // 2)
    ]
    # There are 17 opposite pairs for a 34-point loop.
    if len(centerline) != 17:
        bm.free()
        raise ValueError("structured centerline did not create 17 vertices")
    generated_faces = []
    generated_faces.append(bm.faces.new((inner[n - 1], inner[0], centerline[0])))
    for index in range(len(centerline) - 1):
        generated_faces.append(
            bm.faces.new(
                (
                    inner[index],
                    inner[index + 1],
                    centerline[index + 1],
                    centerline[index],
                )
            )
        )
        generated_faces.append(
            bm.faces.new(
                (
                    centerline[index],
                    centerline[index + 1],
                    inner[n - 2 - index],
                    inner[n - 1 - index],
                )
            )
        )
    generated_faces.append(
        bm.faces.new((inner[n // 2 - 1], inner[n // 2], centerline[-1]))
    )
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.faces.index_update()
    centerline_indices = [int(vertex.index) for vertex in centerline]
    face_histogram: dict[str, int] = {}
    for face in bm.faces:
        key = str(len(face.verts))
        face_histogram[key] = face_histogram.get(key, 0) + 1
    maximum_valence = max(len(vertex.link_edges) for vertex in bm.verts)
    bm.to_mesh(patch.data)
    bm.free()
    patch.data.validate(verbose=True)
    patch.data.update()

    center_weight_records = []
    for index in range(17):
        opposite = n - 1 - index
        names = set(existing_weights[index]) | set(existing_weights[opposite])
        blended = attempt_01_worker.normalized_top_four(
            {
                name: 0.5 * existing_weights[index].get(name, 0.0)
                + 0.5 * existing_weights[opposite].get(name, 0.0)
                for name in names
            }
        )
        center_weight_records.append(blended)
    for vertex_index, weights in zip(centerline_indices, center_weight_records):
        for name, value in weights.items():
            group = patch.vertex_groups.get(name)
            if group is None:
                group = patch.vertex_groups.new(name=name)
            group.add([vertex_index], value, "REPLACE")

    for polygon in patch.data.polygons:
        polygon.use_smooth = True
    patch["topology"] = (
        "seven_concentric_34_vertex_rings_plus_explicit_17_vertex_"
        "median_grid_32_quads_2_terminal_triangles"
    )
    patch["source_interior_vertices_reused"] = 0
    patch["source_interior_faces_reused"] = 0
    record.update(
        {
            "attempt_02_repair": True,
            "object_space_alignment": "exact_source_patch_matrix_world",
            "maximum_world_coordinate_delta_after_object_space_reframe_m": (
                maximum_world_reframe_delta
            ),
            "maximum_outer_ring_to_exact_source_boundary_delta_m": (
                maximum_outer_to_exact_source_delta
            ),
            "new_vertex_count": len(patch.data.vertices),
            "new_face_count": len(patch.data.polygons),
            "structured_grid_generated_vertex_count": 17,
            "structured_grid_generated_face_count": len(generated_faces),
            "structured_grid_face_vertex_count_histogram": face_histogram,
            "structured_grid_method": (
                "17 boundary-endpoint-derived straight median vertices, "
                "inset 18 percent toward the inner-ring mean; 32 distributed "
                "quads and 2 nondegenerate terminal triangles"
            ),
            "maximum_vertex_valence": maximum_valence,
            "triangle_fan_or_poke_vertex_used": False,
            "central_single_pole_vertex_count": 0,
            "center_weight_method": (
                "normalized top-four mean of the corresponding opposing "
                "innermost-ring vertices; those ring weights derive only "
                "from reviewed source-boundary weights"
            ),
        }
    )
    return patch, record


def join_primary_surface_attempt_02(
    by_mesh_name: dict[str, bpy.types.Object],
    patch: bpy.types.Object,
    armature: bpy.types.Object,
) -> tuple[bpy.types.Object, dict[str, object], set[int]]:
    global PATCH_FACE_INDICES
    base_sources = [
        by_mesh_name[name] for name in attempt_01_worker.PRIMARY_BASE_MESHES
    ]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in base_sources:
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.select_set(True)
    body = base_sources[0]
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()

    bm = bmesh.new()
    bm.from_mesh(body.data)
    base_vertices_before_weld = len(bm.verts)
    bmesh.ops.remove_doubles(
        bm,
        verts=list(bm.verts),
        dist=SEAM_WELD_TOLERANCE_M,
    )
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    base_vertices_after_weld = len(body.data.vertices)
    adult_replacement = attempt_01_worker.legacy_builder.remove_base_faces_under_adult_patch(
        body,
        by_mesh_name[attempt_01_worker.SOURCE_PATCH_MESH],
    )

    source_boundary_world = [
        by_mesh_name[attempt_01_worker.SOURCE_PATCH_MESH].matrix_world
        @ by_mesh_name[attempt_01_worker.SOURCE_PATCH_MESH].data.vertices[index].co
        for index in attempt_01_worker.legacy_builder.ordered_boundary_cycles(
            by_mesh_name[attempt_01_worker.SOURCE_PATCH_MESH]
        )[0]
    ]
    patch_outer_world = [
        patch.matrix_world @ patch.data.vertices[index].co
        for index in range(EXPECTED_SEAM_MERGES)
    ]
    seam_match_distances = [
        min((point - source).length for source in source_boundary_world)
        for point in patch_outer_world
    ]
    if max(seam_match_distances) > 1.0e-8:
        raise ValueError(
            "attempt-02 outer ring is not on the exact source seam: "
            f"{max(seam_match_distances):.12g} m"
        )

    patch_material = patch.data.materials[0]
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    patch.select_set(True)
    bpy.context.view_layer.objects.active = body
    joined_vertex_count = len(body.data.vertices) + len(patch.data.vertices)
    bpy.ops.object.join()
    body.name = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"
    body.data.name = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface_Mesh"
    patch_material_slot = next(
        index
        for index, material in enumerate(body.data.materials)
        if material == patch_material
    )
    patch_face_count_before = sum(
        1
        for polygon in body.data.polygons
        if int(polygon.material_index) == patch_material_slot
    )

    bm = bmesh.new()
    bm.from_mesh(body.data)
    before_seam_weld = len(bm.verts)
    bmesh.ops.remove_doubles(
        bm,
        verts=list(bm.verts),
        dist=SEAM_WELD_TOLERANCE_M,
    )
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    seam_merges = before_seam_weld - len(body.data.vertices)
    if seam_merges != EXPECTED_SEAM_MERGES:
        raise ValueError(
            f"attempt-02 requires exactly 34 seam merges; observed {seam_merges}"
        )
    for polygon in body.data.polygons:
        polygon.use_smooth = True
    top_four = attempt_01_worker.normalize_body_top_four(body)

    PATCH_FACE_INDICES = {
        int(polygon.index)
        for polygon in body.data.polygons
        if int(polygon.material_index) == patch_material_slot
    }
    if len(PATCH_FACE_INDICES) != patch_face_count_before:
        raise ValueError("attempt-02 weld unexpectedly changed radial patch faces")

    topology = attempt_01_worker.audit_helpers.topology_record(body)
    if topology["connected_components"] != 1:
        raise ValueError(
            "attempt-02 joined primary surface is not one component: "
            f"{topology['connected_components']}"
        )
    boundary_bm = bmesh.new()
    boundary_bm.from_mesh(body.data)
    boundary_bm.edges.ensure_lookup_table()
    total_boundary_edges = [
        edge for edge in boundary_bm.edges if len(edge.link_faces) == 1
    ]
    patch_boundary_edges = [
        edge
        for edge in total_boundary_edges
        if edge.link_faces
        and int(edge.link_faces[0].material_index) == patch_material_slot
    ]
    patch_boundary_edge_count = len(patch_boundary_edges)
    boundary_bm.free()
    if patch_boundary_edge_count != 0:
        raise ValueError(
            "attempt-02 radial patch remains open after its 34-vertex seam weld: "
            f"{patch_boundary_edge_count} patch boundary edges"
        )

    modifier = next((item for item in body.modifiers if item.type == "ARMATURE"), None)
    if modifier is None:
        modifier = body.modifiers.new("KIRA_R19_NATIVE_188_RIG", "ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    modifier.use_deform_preserve_volume = True
    body["private_review_only"] = True
    body["owner_approved"] = False
    body["runtime_assignment_allowed"] = False
    body["runtime_activation_allowed"] = False
    body["adult_status"] = "confirmed_adult"
    body["body_class"] = "adult_female"
    body["source_interior_vertices_reused"] = 0
    body["source_interior_faces_reused"] = 0
    return body, {
        "attempt_02_repair": True,
        "base_vertex_count_before_internal_component_weld": base_vertices_before_weld,
        "base_vertex_count_after_internal_component_weld": base_vertices_after_weld,
        "joined_vertex_count_before_boundary_weld": joined_vertex_count,
        "joined_vertex_count_at_bmesh_weld": before_seam_weld,
        "final_vertex_count": len(body.data.vertices),
        "boundary_vertices_merged": seam_merges,
        "required_boundary_vertices_merged": EXPECTED_SEAM_MERGES,
        "maximum_prejoin_outer_ring_to_source_seam_distance_m": max(
            seam_match_distances
        ),
        "weld_tolerance_m": SEAM_WELD_TOLERANCE_M,
        "adult_replacement": adult_replacement,
        "patch_material_slot": patch_material_slot,
        "patch_face_count": len(PATCH_FACE_INDICES),
        "top_four_normalization": top_four,
        "post_weld_topology_hard_gate": {
            "connected_components": topology["connected_components"],
            "total_boundary_edge_count": topology["boundary_edge_count"],
            "new_patch_boundary_edge_count": patch_boundary_edge_count,
            "inherited_blackproject_supported_boundary_edge_count": (
                topology["boundary_edge_count"] - patch_boundary_edge_count
            ),
            "global_zero_boundary_gate": topology["boundary_edge_count"] == 0,
            "bounded_patch_zero_boundary_gate": patch_boundary_edge_count == 0,
        },
    }, set(PATCH_FACE_INDICES)


def exact_audit_with_joined_patch_gate(
    obj: bpy.types.Object,
    include_details: bool,
) -> dict[str, object]:
    report = ORIGINAL_EXACT_AUDIT(obj, include_details)
    if obj.name == "Kira_R19_BlackProject_Radial_Patch_Primary_Surface":
        patch_pairs = [
            record
            for record in report["pairs"]
            if record["genuine_positive_area_or_segment_penetration"]
            and any(index in PATCH_FACE_INDICES for index in record["face_indices"])
        ]
        if patch_pairs:
            raise ValueError(
                "attempt-02 joined radial patch has exact penetrations: "
                f"{json.dumps(patch_pairs)}"
            )
    return report


def finalize_attempt_02_records() -> None:
    output_dir = PROJECT_ROOT / OUTPUT_REL
    evidence_path = output_dir / "BUILD_EVIDENCE.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    base_worker_path = Path(attempt_01_worker.__file__).resolve()
    wrapper_path = Path(__file__).resolve()
    evidence["attempt"] = "attempt_02"
    evidence["status"] = (
        "PRIVATE_INACTIVE_GEOMETRY_PROBE_PASSED_STRUCTURAL_GATES_"
        "REQUIRES_VISUAL_REVIEW"
    )
    evidence["attempt_02_changes"] = {
        "attempt_01_preserved": True,
        "explicit_center_grid": True,
        "object_space_seam_alignment": True,
        "required_seam_merges": EXPECTED_SEAM_MERGES,
        "hard_gate_one_component": True,
        "hard_gate_zero_new_patch_boundary_edges": True,
        "global_zero_boundary_edges": False,
        "inherited_blackproject_boundary_edges": evidence[
            "primary_surface_topology"
        ]["boundary_edge_count"],
        "hard_gate_zero_patch_related_exact_intersections": True,
    }
    evidence["worker"] = {
        "path": str(wrapper_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "sha256": sha256_file(wrapper_path),
        "orchestration_dependency": {
            "path": str(base_worker_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(base_worker_path),
        },
    }
    evidence["gates"]["exactly_34_seam_merges"] = (
        evidence["primary_surface_join"]["boundary_vertices_merged"]
        == EXPECTED_SEAM_MERGES
    )
    evidence["gates"]["one_connected_primary_surface"] = True
    evidence["gates"]["closed_primary_surface"] = (
        evidence["primary_surface_topology"]["boundary_edge_count"] == 0
    )
    evidence["gates"]["zero_new_patch_boundary_edges"] = (
        evidence["primary_surface_join"]["post_weld_topology_hard_gate"][
            "new_patch_boundary_edge_count"
        ]
        == 0
    )
    evidence["gates"]["new_patch_joined_exact_intersection_free"] = True
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    report_path = output_dir / "REPORT.md"
    report_path.write_text(
        "\n".join(
            [
                "# R19 BlackProject radial patch probe — attempt 02",
                "",
                f"Status: `{evidence['status']}`",
                "",
                "- Attempt 01 remains unchanged as the failed open-center/object-space diagnostic.",
                "- The exact 34-vertex source seam was retained and exactly 34 seam vertices merged.",
                "- Reused rejected source interior geometry: `0 vertices / 0 faces`.",
                "- Center topology: 17 distributed median vertices, 32 quads, two terminal triangles, no poke or fan.",
                f"- New patch intersections before join: `{evidence['patch_exact_nonadjacent_intersection_audit']['exact_genuine_penetration_pair_count']}`.",
                f"- New patch-related intersections after join: `{evidence['intersection_localization']['new_patch_related_genuine_pair_count']}`.",
                f"- Inherited exact intersections elsewhere: `{evidence['intersection_localization']['inherited_elsewhere_genuine_pair_count']}`.",
                "- The primary body is one connected component; the new patch adds zero boundary edges.",
                f"- Global closure remains blocked by `{evidence['primary_surface_topology']['boundary_edge_count']}` inherited BlackProject boundary edges outside this patch (the same source condition recorded by R9b).",
                "- Scalp hair is excluded rather than hidden.",
                "- Structural passage is not visual or owner approval; close-up review remains required.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    manifest_path = output_dir / "PACKAGE_MANIFEST.json"
    entries = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name.lower()):
        if path.is_file() and path != manifest_path:
            entries.append(
                {
                    "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "append_only_attempt": "attempt_02",
                "files_excluding_this_manifest": entries,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    if (PROJECT_ROOT / OUTPUT_REL).exists():
        raise FileExistsError("append-only attempt_02 already exists")
    attempt_01_worker.OUTPUT_REL = OUTPUT_REL
    attempt_01_worker.WELD_TOLERANCE_M = SEAM_WELD_TOLERANCE_M
    attempt_01_worker.make_radial_patch = make_radial_patch_attempt_02
    attempt_01_worker.join_primary_surface = join_primary_surface_attempt_02
    attempt_01_worker.bmesh_exact_audit = exact_audit_with_joined_patch_gate
    result = attempt_01_worker.main()
    finalize_attempt_02_records()
    print(
        json.dumps(
            {
                "ok": True,
                "attempt": "attempt_02",
                "output_dir": str(PROJECT_ROOT / OUTPUT_REL),
            },
            indent=2,
        )
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
