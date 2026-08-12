#!/usr/bin/env python3
"""Build Kira R21 pelvis Attempt 01 from the approved R19 body.

Only the rejected 376-face R19 insert is replaced.  The replacement is the
same-lineage, medically bounded BlackProject patch after the best preserved
harmonic reconstruction (R19 reconstruction Attempt 03).  The face, overall
body, rig, eyes, eyebrows, nails, and all other objects remain untouched.

The result is private, inactive, unassigned, and append-only.  It is a visual
and deformation candidate, not proof of urinary, bowel, reproductive, or
pregnancy physiology.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import bmesh
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree


ROOT = Path(r"C:\Users\robmc\Kira")
TOOLS = ROOT / "Tools"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import blender_author_kira_r20_pelvis_only as r20  # noqa: E402
from blender_exact_mesh_intersections import (  # noqa: E402
    exact_nonadjacent_intersection_report,
)


SOURCE_BLEND = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/"
    "attempt_06/kira_r19_bald_targeted_material_movement_correction.blend"
)
PATCH_BLEND = ROOT / (
    "RecoverySprint/continuation_20260802/r19_blackproject_patch_reconstruction/"
    "attempt_03/r19_patch_reconstruction_probe.blend"
)
PATCH_REPORT = PATCH_BLEND.with_name("PATCH_RECONSTRUCTION_PROBE.json")
OUTPUT_DIR = ROOT / (
    "Avatar/private_owner_review/kira_r21_bald_localized_correction_attempt_01"
)
EVIDENCE_DIR = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r21_localized_repair/author_attempt_01"
)
OUTPUT_BLEND = OUTPUT_DIR / "KIRA_R21_BALD_PRIVATE_INACTIVE_PELVIS_ATTEMPT01.blend"
BODY_NAME = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"
RIG_NAME = "Kira_R19_BlackProject_Native_188_Rig"
PATCH_OBJECT_NAME = "Object_23"
PATCH_SLOT = 5
EXPECTED_SOURCE_SHA = "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f"
EXPECTED_PATCH_BLEND_SHA = "8f0feb0b0732feba1c46a128e318be7f66ed37ff2ed5657d7270c31efd8a9a0f"
WELD_TOLERANCE_LOCAL = 1.0e-7


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def coordinate_key(value: Vector) -> str:
    return "|".join(f"{float(component):.9f}" for component in value)


def weights_for_vertex(obj: bpy.types.Object, index: int) -> list[list[Any]]:
    names = {group.index: group.name for group in obj.vertex_groups}
    return sorted(
        [names[item.group], round(float(item.weight), 10)]
        for item in obj.data.vertices[index].groups
        if float(item.weight) > 1.0e-10
    )


def canonical_cycle(values: list[str]) -> list[str]:
    rotations = [values[index:] + values[:index] for index in range(len(values))]
    reversed_values = list(reversed(values))
    rotations.extend(
        reversed_values[index:] + reversed_values[:index]
        for index in range(len(reversed_values))
    )
    return min(rotations)


def nonpatch_snapshot(body: bpy.types.Object) -> dict[str, Any]:
    polygons = [
        polygon
        for polygon in body.data.polygons
        if int(polygon.material_index) != PATCH_SLOT
    ]
    vertices = sorted({int(index) for polygon in polygons for index in polygon.vertices})
    vertex_records = sorted(
        [coordinate_key(body.data.vertices[index].co), weights_for_vertex(body, index)]
        for index in vertices
    )
    face_records = []
    uv_layer = body.data.uv_layers.active
    for polygon in polygons:
        coordinates = [
            coordinate_key(body.data.vertices[int(index)].co)
            for index in polygon.vertices
        ]
        uv = []
        if uv_layer is not None:
            uv = sorted(
                [round(float(uv_layer.data[loop].uv.x), 9), round(float(uv_layer.data[loop].uv.y), 9)]
                for loop in range(polygon.loop_start, polygon.loop_start + polygon.loop_total)
            )
        face_records.append(
            [canonical_cycle(coordinates), int(polygon.material_index), uv]
        )
    face_records.sort()
    return {
        "face_count": len(polygons),
        "vertex_count": len(vertices),
        "vertex_coordinate_weight_sha256": sha256_json(vertex_records),
        "face_coordinate_material_uv_sha256": sha256_json(face_records),
    }


def object_digest(obj: bpy.types.Object) -> str:
    value: dict[str, Any] = {
        "name": obj.name,
        "type": obj.type,
        "matrix": [[float(x) for x in row] for row in obj.matrix_world],
    }
    if obj.type == "MESH":
        value["vertices"] = [
            [float(vertex.co.x), float(vertex.co.y), float(vertex.co.z)]
            for vertex in obj.data.vertices
        ]
        value["polygons"] = [list(map(int, polygon.vertices)) for polygon in obj.data.polygons]
        value["materials"] = [material.name if material else None for material in obj.data.materials]
    elif obj.type == "ARMATURE":
        value["bones"] = [
            {
                "name": bone.name,
                "head": [float(x) for x in bone.head_local],
                "tail": [float(x) for x in bone.tail_local],
                "parent": bone.parent.name if bone.parent else None,
            }
            for bone in obj.data.bones
        ]
    return sha256_json(value)


def patch_mask(body: bpy.types.Object) -> dict[str, Any]:
    selected = {
        int(poly.index)
        for poly in body.data.polygons
        if int(poly.material_index) == PATCH_SLOT
    }
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for polygon in body.data.polygons:
        vertices = list(map(int, polygon.vertices))
        for index, first in enumerate(vertices):
            edge_faces[tuple(sorted((first, vertices[(index + 1) % len(vertices)])))].append(
                int(polygon.index)
            )
    interface_edges = [
        edge
        for edge, faces in edge_faces.items()
        if len(faces) == 2 and sum(face in selected for face in faces) == 1
    ]
    interface = sorted({vertex for edge in interface_edges for vertex in edge})
    incident = {int(vertex) for face in selected for vertex in body.data.polygons[face].vertices}
    removable = sorted(incident - set(interface))
    if (len(selected), len(incident), len(interface_edges), len(interface), len(removable)) != (
        376,
        206,
        34,
        34,
        172,
    ):
        raise RuntimeError("exact R19 rejected-patch mask drifted")
    return {
        "faces": sorted(selected),
        "interface_edges": sorted(interface_edges),
        "interface_vertices": interface,
        "removable_vertices": removable,
    }


def append_patch() -> bpy.types.Object:
    before = set(bpy.data.objects)
    with bpy.data.libraries.load(str(PATCH_BLEND), link=False) as (source, target):
        if PATCH_OBJECT_NAME not in source.objects:
            raise RuntimeError("reconstructed source patch object is absent")
        target.objects = [PATCH_OBJECT_NAME]
    appended = [obj for obj in bpy.data.objects if obj not in before]
    if len(appended) != 1 or appended[0].type != "MESH":
        raise RuntimeError(f"unexpected appended patch inventory: {[obj.name for obj in appended]}")
    bpy.context.scene.collection.objects.link(appended[0])
    return appended[0]


def boundary_vertices(obj: bpy.types.Object) -> list[int]:
    counts: dict[tuple[int, int], int] = defaultdict(int)
    for polygon in obj.data.polygons:
        vertices = list(map(int, polygon.vertices))
        for index, first in enumerate(vertices):
            counts[tuple(sorted((first, vertices[(index + 1) % len(vertices)])))] += 1
    vertices = sorted({vertex for edge, count in counts.items() if count == 1 for vertex in edge})
    if len(vertices) != 34:
        raise RuntimeError(f"reconstructed patch boundary drifted: {len(vertices)}")
    return vertices


def interface_comparison(body: bpy.types.Object, mask: dict[str, Any], adult: bpy.types.Object) -> dict[str, Any]:
    target = list(map(int, mask["interface_vertices"]))
    tree = KDTree(len(target))
    for ordinal, index in enumerate(target):
        tree.insert(body.matrix_world @ body.data.vertices[index].co, ordinal)
    tree.balance()
    distances = []
    matches = set()
    for index in boundary_vertices(adult):
        _point, ordinal, distance = tree.find(adult.matrix_world @ adult.data.vertices[index].co)
        distances.append(float(distance))
        matches.add(target[int(ordinal)])
    result = {
        "maximum_distance_m": max(distances),
        "mean_distance_m": statistics.mean(distances),
        "unique_matches": len(matches),
        "exact_one_to_one_at_1e_8_m": len(matches) == 34 and max(distances) <= 1.0e-8,
    }
    if not result["exact_one_to_one_at_1e_8_m"]:
        raise RuntimeError(f"reconstructed patch no longer matches R19: {result}")
    return result


def remove_old_patch(body: bpy.types.Object, mask: dict[str, Any]) -> None:
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(
        bm,
        geom=[bm.faces[index] for index in mask["faces"]],
        context="FACES_ONLY",
    )
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(
        bm,
        geom=[bm.verts[index] for index in mask["removable_vertices"]],
        context="VERTS",
    )
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()


def join_and_weld(body: bpy.types.Object, adult: bpy.types.Object, rig: bpy.types.Object) -> dict[str, Any]:
    approved_material = body.data.materials[PATCH_SLOT]
    adult.data.materials.clear()
    adult.data.materials.append(approved_material)
    for polygon in adult.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True
    before_join = len(body.data.vertices) + len(adult.data.vertices)
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    adult.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    before_weld = len(body.data.vertices)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.ensure_lookup_table()
    result = bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=WELD_TOLERANCE_LOCAL)
    merged_target_count = len(result.get("targetmap", {}))
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    for polygon in body.data.polygons:
        if int(polygon.material_index) == PATCH_SLOT:
            polygon.use_smooth = True
    modifier = next((item for item in body.modifiers if item.type == "ARMATURE"), None)
    if modifier is None:
        modifier = body.modifiers.new("KIRA_R21_NATIVE_188_RIG", "ARMATURE")
    modifier.object = rig
    modifier.use_vertex_groups = True
    modifier.use_deform_preserve_volume = True
    return {
        "joined_vertex_count_before_weld": before_join,
        "bmesh_vertex_count_before_weld": before_weld,
        "final_vertex_count": len(body.data.vertices),
        "merged_target_map_entries": merged_target_count,
        "expected_boundary_merge_count": 34,
        "actual_vertex_reduction": before_weld - len(body.data.vertices),
        "weld_tolerance_body_local": WELD_TOLERANCE_LOCAL,
    }


def exact_audit(body: bpy.types.Object) -> dict[str, Any]:
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.transform(body.matrix_world)
    report = exact_nonadjacent_intersection_report(bm, include_pair_details=True)
    bm.free()
    patch_faces = {
        int(polygon.index)
        for polygon in body.data.polygons
        if int(polygon.material_index) == PATCH_SLOT
    }
    related = 0
    inherited = 0
    for record in report.get("pairs", []):
        if record.get("genuine_positive_area_or_segment_penetration") is not True:
            continue
        first, second = map(int, record["face_indices"])
        if first in patch_faces or second in patch_faces:
            related += 1
        else:
            inherited += 1
    report["classification"] = {
        "patch_related_exact_genuine_pairs": related,
        "nonpatch_exact_genuine_pairs": inherited,
        "patch_face_count": len(patch_faces),
    }
    return report


def clear_pose(rig: bpy.types.Object) -> None:
    if rig.animation_data:
        rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.location = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


def add_light(name: str, location: tuple[float, float, float], energy: float, size: float) -> None:
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector((0.0, 0.0, 0.9)) - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_view(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    path: Path,
    location: Vector,
    target: Vector,
    scale: float,
) -> None:
    camera.location = location
    camera.data.ortho_scale = float(scale)
    camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def render_review(body: bpy.types.Object) -> list[str]:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.006, 0.011, 0.018)
    for obj in bpy.data.objects:
        if obj.type in {"LIGHT", "CAMERA"}:
            obj.hide_render = True
    add_light("R21_KEY", (2.2, -3.0, 2.8), 900.0, 4.0)
    add_light("R21_FILL", (-2.2, -2.0, 1.6), 520.0, 3.0)
    add_light("R21_RIM", (0.8, 2.3, 2.5), 720.0, 3.0)
    camera_data = bpy.data.cameras.new("R21_REVIEW_CAMERA_DATA")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("R21_REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    minimum = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    center = (minimum + maximum) * 0.5
    height = maximum.z - minimum.z
    patch_vertices = {
        int(index)
        for polygon in body.data.polygons
        if int(polygon.material_index) == PATCH_SLOT
        for index in polygon.vertices
    }
    patch_points = [body.matrix_world @ body.data.vertices[index].co for index in patch_vertices]
    patch_center = sum(patch_points, Vector()) / len(patch_points)
    full_scale = max(height * 1.08, (maximum.x - minimum.x) * 1.18)
    views = {
        "neutral_front": (Vector((center.x, center.y - 3.0, center.z)), center, full_scale),
        "neutral_left_three_quarter": (Vector((center.x - 2.3, center.y - 2.3, center.z)), center, full_scale),
        "neutral_right_three_quarter": (Vector((center.x + 2.3, center.y - 2.3, center.z)), center, full_scale),
        "protected_external_front": (Vector((patch_center.x, patch_center.y - 1.5, patch_center.z)), patch_center, 0.25),
        "protected_external_left_three_quarter": (Vector((patch_center.x - 0.75, patch_center.y - 1.15, patch_center.z)), patch_center, 0.27),
        "protected_external_right_three_quarter": (Vector((patch_center.x + 0.75, patch_center.y - 1.15, patch_center.z)), patch_center, 0.27),
        "protected_external_left_profile": (Vector((patch_center.x - 1.45, patch_center.y, patch_center.z)), patch_center, 0.27),
        "protected_external_rear": (Vector((patch_center.x, patch_center.y + 1.5, patch_center.z)), patch_center, 0.26),
        "protected_external_inferior_front": (Vector((patch_center.x, patch_center.y - 0.62, patch_center.z - 0.62)), patch_center, 0.25),
        "protected_external_inferior_rear": (Vector((patch_center.x, patch_center.y + 0.62, patch_center.z - 0.62)), patch_center, 0.25),
    }
    names = []
    for name, (location, target, scale) in views.items():
        path = OUTPUT_DIR / f"{name}.png"
        render_view(scene, camera, path, location, target, scale)
        names.append(path.name)
    return names


def main() -> int:
    if OUTPUT_DIR.exists() or EVIDENCE_DIR.exists():
        raise FileExistsError("append-only R21 Attempt 01 output already exists")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=False)
    if sha256_file(SOURCE_BLEND) != EXPECTED_SOURCE_SHA:
        raise RuntimeError("R19 source Blend hash mismatch")
    actual_patch_sha = sha256_file(PATCH_BLEND)
    if actual_patch_sha != EXPECTED_PATCH_BLEND_SHA:
        raise RuntimeError(
            f"reconstructed patch Blend hash mismatch: {actual_patch_sha}"
        )
    if Path(bpy.data.filepath).resolve() != SOURCE_BLEND.resolve():
        raise RuntimeError("exact R19 source Blend is not loaded")
    body = bpy.data.objects.get(BODY_NAME)
    rig = bpy.data.objects.get(RIG_NAME)
    if body is None or body.type != "MESH" or rig is None or rig.type != "ARMATURE":
        raise RuntimeError("exact R19 body or rig is absent")
    clear_pose(rig)
    mask = patch_mask(body)
    nonpatch_before = nonpatch_snapshot(body)
    preserved_normals = r20._capture_preserved_loop_normals(body)
    original_objects = [obj for obj in bpy.data.objects if obj != body]
    protected_before = {obj.name: object_digest(obj) for obj in original_objects}
    rig_before = object_digest(rig)
    material_names_before = [material.name if material else None for material in body.data.materials]
    adult = append_patch()
    comparison = interface_comparison(body, mask, adult)
    remove_old_patch(body, mask)
    join_record = join_and_weld(body, adult, rig)
    if join_record["actual_vertex_reduction"] != 34:
        raise RuntimeError(f"exact seam did not weld 34 vertices: {join_record}")
    normal_restore = r20._restore_exact_preserved_loop_normals(body, preserved_normals)
    nonpatch_after = nonpatch_snapshot(body)
    if nonpatch_after != nonpatch_before:
        raise RuntimeError(
            "approved nonpatch body geometry, weights, material binding, or UVs changed"
        )
    material_names_after = [material.name if material else None for material in body.data.materials]
    if material_names_after != material_names_before:
        raise RuntimeError(
            f"body material slots drifted: {material_names_before} -> {material_names_after}"
        )
    protected_after = {obj.name: object_digest(obj) for obj in original_objects}
    if protected_after != protected_before or object_digest(rig) != rig_before:
        raise RuntimeError("a protected nonbody object or rig changed")
    body.name = "Kira_R21_Bald_Private_Inactive_Pelvis_Attempt01"
    body.data.name = "Kira_R21_Bald_Private_Inactive_Pelvis_Attempt01_Mesh"
    body["candidate_id"] = "kira_r21_bald_localized_correction_attempt_01"
    body["private_review_only"] = True
    body["owner_approved"] = False
    body["runtime_assignment_allowed"] = False
    body["runtime_activation_allowed"] = False
    body["approved_face_preserved"] = True
    body["approved_general_body_preserved"] = True
    body["pelvic_surface_owner_acceptance"] = False
    body["internal_physiology_implemented"] = False
    intersection = exact_audit(body)
    renders = render_review(body)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND), check_existing=False)
    blend_sha = sha256_file(OUTPUT_BLEND)
    patch_source_report = json.loads(PATCH_REPORT.read_text(encoding="utf-8"))
    evidence = {
        "schema_version": 1,
        "artifact_kind": "KIRA_R21_PELVIS_ATTEMPT01_BUILD_EVIDENCE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PRIVATE_INACTIVE_COMPLETE_REVIEW_CANDIDATE_WITH_DISCLOSED_INTERSECTION_GATE",
        "candidate_id": "kira_r21_bald_localized_correction_attempt_01",
        "source": {
            "r19_blend": str(SOURCE_BLEND.relative_to(ROOT)).replace("\\", "/"),
            "r19_sha256": EXPECTED_SOURCE_SHA,
            "reconstructed_patch_blend": str(PATCH_BLEND.relative_to(ROOT)).replace("\\", "/"),
            "reconstructed_patch_sha256": actual_patch_sha,
            "patch_source_exact_pairs_before_join": patch_source_report[
                "exact_nonadjacent_intersections"
            ]["exact_genuine_penetration_pair_count"],
        },
        "scope": {
            "changed": ["exact_rejected_376_face_pelvic_insert"],
            "unchanged": [
                "approved_face",
                "approved_general_body_outside_exact_mask",
                "eyes",
                "existing_rejected_eyebrow_object_pending_next_stage",
                "existing_rejected_nails_pending_next_stage",
                "rig_rest_structure",
                "actions",
                "scalp",
                "skin_material_graphs",
            ],
            "private": True,
            "inactive": True,
            "unassigned": True,
            "unpublished": True,
            "hair_loaded": False,
        },
        "mask": {
            "old_face_count": len(mask["faces"]),
            "old_interface_vertex_count": len(mask["interface_vertices"]),
            "old_removed_interior_vertex_count": len(mask["removable_vertices"]),
        },
        "interface": comparison,
        "join": join_record,
        "nonpatch_before": nonpatch_before,
        "nonpatch_after": nonpatch_after,
        "nonpatch_exactly_preserved": nonpatch_after == nonpatch_before,
        "protected_nonbody_objects_exactly_preserved": protected_after == protected_before,
        "rig_exactly_preserved": object_digest(rig) == rig_before,
        "normal_and_corner_attribute_restoration": normal_restore,
        "exact_intersection_audit": intersection,
        "outputs": {
            "blend": str(OUTPUT_BLEND.relative_to(ROOT)).replace("\\", "/"),
            "blend_sha256": blend_sha,
            "renders": renders,
        },
        "visual_truth": {
            "owner_review_required": True,
            "source_like_natural_external_topology_restored": True,
            "eyebrows_repaired_in_this_attempt": False,
            "nails_repaired_in_this_attempt": False,
            "movement_accepted_in_this_attempt": False,
        },
        "functional_truth": {
            "external_surface_candidate": True,
            "internal_bladder_bowel_reproductive_organs_implemented": False,
            "urination_defecation_reproduction_pregnancy_proven": False,
            "separate_internal_simulation_required": True,
        },
        "activation_or_export_performed": False,
    }
    evidence_path = EVIDENCE_DIR / "BUILD_EVIDENCE.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    readme = (
        "# Kira R21 pelvis Attempt 01 owner review\n\n"
        "This is a private, inactive, bald review candidate. The approved R19 face and general "
        "body outside the exact rejected pelvic mask are unchanged. This attempt replaces only "
        "the rejected plate-like insert with the same-lineage reconstructed natural surface.\n\n"
        "The images are intentionally close and clinical. This attempt does not yet repair the "
        "already rejected eyebrows or nails. It also does not claim internal urinary, bowel, "
        "reproductive, pregnancy, or childbirth physiology.\n\n"
        f"Exact body intersection audit: {intersection['exact_genuine_penetration_pair_count']} "
        "genuine nonadjacent triangle pairs; see BUILD_EVIDENCE.json for patch/nonpatch classification.\n"
    )
    (OUTPUT_DIR / "OWNER_REVIEW_README.md").write_text(readme, encoding="utf-8")
    print(json.dumps({
        "status": evidence["status"],
        "blend": str(OUTPUT_BLEND),
        "blend_sha256": blend_sha,
        "renders": renders,
        "exact_pairs": intersection["exact_genuine_penetration_pair_count"],
        "classification": intersection["classification"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
