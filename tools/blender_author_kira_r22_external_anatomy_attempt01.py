#!/usr/bin/env python3
"""Append-only Kira R22 external-anatomy module Attempt 01.

This is a private clinical review build.  It preserves the owner-approved face
and the complete body outside the exact pelvic material mask.  The inherited
R21 insert is locally relaxed, then a detachable, rig-bound external-anatomy
module is constructed from ordered medical landmarks.  This attempt does not
claim bladder, bowel, reproductive, pregnancy, or other physiology.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Callable

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree


ROOT = Path(r"C:\Users\robmc\Kira")
TOOLS = ROOT / "Tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import blender_author_kira_r21_pelvis_attempt01 as r21  # noqa: E402


SOURCE = ROOT / (
    "Avatar/private_owner_review/kira_r21_bald_localized_correction_attempt_08_review/"
    "KIRA_R21_BALD_PRIVATE_INACTIVE_PELVIS_ATTEMPT08_REVIEW.blend"
)
EXPECTED_SOURCE_SHA = "bb4d9a4b0d11c17047001278d7dadd105857bcc976ae7c0ec15a93b7945b00e4"
OUTPUT_DIR = ROOT / "Avatar/private_owner_review/kira_r22_external_anatomy_attempt_01"
EVIDENCE_DIR = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r22_external_anatomy/attempt_01"
)
OUTPUT_BLEND = OUTPUT_DIR / "KIRA_R22_BALD_PRIVATE_INACTIVE_EXTERNAL_ANATOMY_ATTEMPT01.blend"
PATCH_SLOT = 5
RIG_NAME = "Kira_R19_BlackProject_Native_188_Rig"
MODULE_PREFIX = "Kira_R22_External_"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def smoothstep(value: float) -> float:
    t = max(0.0, min(1.0, float(value)))
    return t * t * (3.0 - 2.0 * t)


def find_body() -> bpy.types.Object:
    candidates = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and sum(int(poly.material_index) == PATCH_SLOT for poly in obj.data.polygons) >= 1000
        and bool(obj.get("private_review_only"))
    ]
    if len(candidates) != 1:
        raise RuntimeError(f"expected one R21 private body, found {[obj.name for obj in candidates]}")
    return candidates[0]


def patch_topology(body: bpy.types.Object) -> dict[str, Any]:
    patch_faces = {
        int(poly.index)
        for poly in body.data.polygons
        if int(poly.material_index) == PATCH_SLOT
    }
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    neighbors: dict[int, set[int]] = defaultdict(set)
    for poly in body.data.polygons:
        ids = list(map(int, poly.vertices))
        for offset, first in enumerate(ids):
            second = ids[(offset + 1) % len(ids)]
            edge = tuple(sorted((first, second)))
            edge_faces[edge].append(int(poly.index))
            neighbors[first].add(second)
            neighbors[second].add(first)
    interface_edges = {
        edge
        for edge, faces in edge_faces.items()
        if len(faces) == 2 and sum(face in patch_faces for face in faces) == 1
    }
    seam = {index for edge in interface_edges for index in edge}
    patch_vertices = {
        int(index)
        for face in patch_faces
        for index in body.data.polygons[face].vertices
    }
    patch_neighbors = {
        index: {neighbor for neighbor in neighbors[index] if neighbor in patch_vertices}
        for index in patch_vertices
    }
    distance = {index: 0 for index in seam}
    queue = deque(seam)
    while queue:
        current = queue.popleft()
        for neighbor in patch_neighbors[current]:
            if neighbor not in distance:
                distance[neighbor] = distance[current] + 1
                queue.append(neighbor)
    return {
        "faces": patch_faces,
        "vertices": patch_vertices,
        "neighbors": patch_neighbors,
        "seam": seam,
        "distance": distance,
        "interface_edges": interface_edges,
    }


def relax_rejected_center(body: bpy.types.Object, topology: dict[str, Any]) -> dict[str, Any]:
    mesh = body.data
    original = {index: mesh.vertices[index].co.copy() for index in topology["vertices"]}
    moved: set[int] = set()
    iterations = 32
    relaxation = 0.38
    for _ in range(iterations):
        previous = {index: mesh.vertices[index].co.copy() for index in topology["vertices"]}
        pending: dict[int, Vector] = {}
        for index in topology["vertices"]:
            ring = topology["distance"].get(index, 0)
            if ring <= 2:
                continue
            world = body.matrix_world @ previous[index]
            z_gate = smoothstep((world.z - 0.842) / 0.012) * smoothstep((0.912 - world.z) / 0.012)
            x_gate = smoothstep((0.040 - abs(world.x)) / 0.018)
            front_gate = smoothstep((0.025 - world.y) / 0.025)
            weight = z_gate * x_gate * front_gate
            if weight <= 1.0e-6:
                continue
            adjacent = topology["neighbors"][index]
            if not adjacent:
                continue
            target = sum((previous[value] for value in adjacent), Vector()) / len(adjacent)
            pending[index] = previous[index].lerp(target, relaxation * weight)
        for index, value in pending.items():
            mesh.vertices[index].co = value
            moved.add(index)
        mesh.update()
    maximum = max(
        ((mesh.vertices[index].co - original[index]).length for index in moved),
        default=0.0,
    )
    seam_delta = max(
        ((mesh.vertices[index].co - original[index]).length for index in topology["seam"]),
        default=0.0,
    )
    return {
        "method": "bounded_weighted_laplacian_relaxation_of_rejected_central_insert_v1",
        "iterations": iterations,
        "relaxation": relaxation,
        "moved_vertex_count": len(moved),
        "maximum_body_local_movement": float(maximum),
        "seam_maximum_delta": float(seam_delta),
    }


def make_material(
    name: str,
    color: tuple[float, float, float, float],
    roughness: float,
    subsurface: float,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    node = material.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = color
    node.inputs["Roughness"].default_value = roughness
    if node.inputs.get("Subsurface Weight") is not None:
        node.inputs["Subsurface Weight"].default_value = subsurface
    if node.inputs.get("Subsurface Radius") is not None:
        node.inputs["Subsurface Radius"].default_value = (1.0, 0.45, 0.25)
    if node.inputs.get("Specular IOR Level") is not None:
        node.inputs["Specular IOR Level"].default_value = 0.28
    return material


def ray_surface_y(body: bpy.types.Object, x: float, z: float, *, front: bool = True) -> float:
    inverse = body.matrix_world.inverted()
    origin_world = Vector((x, -0.35 if front else 0.35, z))
    direction_world = Vector((0.0, 1.0 if front else -1.0, 0.0))
    origin_local = inverse @ origin_world
    direction_local = (inverse.to_3x3() @ direction_world).normalized()
    hit, location, _normal, _face = body.ray_cast(origin_local, direction_local, distance=0.7)
    if not hit:
        raise RuntimeError(f"body ray missed at x={x:.6f}, z={z:.6f}, front={front}")
    return float((body.matrix_world @ location).y)


def mesh_object(
    name: str,
    world_vertices: list[Vector],
    faces: list[tuple[int, ...]],
    material: bpy.types.Material,
    body: bpy.types.Object,
) -> bpy.types.Object:
    local_vertices = [body.matrix_world.inverted() @ value for value in world_vertices]
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata([tuple(value) for value in local_vertices], [], faces)
    mesh.materials.append(material)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.matrix_world = body.matrix_world.copy()
    return obj


def ribbon(
    *,
    name: str,
    body: bpy.types.Object,
    material: bpy.types.Material,
    z_top: float,
    z_bottom: float,
    center_x: Callable[[float], float],
    half_width: Callable[[float], float],
    height: Callable[[float], float],
    samples: int = 30,
    cross_samples: int = 8,
    front: bool = True,
) -> bpy.types.Object:
    vertices: list[Vector] = []
    for row in range(samples):
        t = row / (samples - 1)
        z = z_top + (z_bottom - z_top) * t
        taper = math.sin(math.pi * t) ** 0.55
        cx = center_x(t)
        width = max(0.00015, half_width(t) * taper)
        for column in range(cross_samples):
            u = -1.0 + 2.0 * column / (cross_samples - 1)
            x = cx + width * u
            base_y = ray_surface_y(body, x, z, front=front)
            profile = max(0.0, 1.0 - u * u) ** 0.72
            outward = height(t) * taper * profile
            y = base_y + (-outward if front else outward)
            vertices.append(Vector((x, y, z)))
    faces = []
    for row in range(samples - 1):
        for column in range(cross_samples - 1):
            first = row * cross_samples + column
            faces.append((first, first + 1, first + 1 + cross_samples, first + cross_samples))
    return mesh_object(name, vertices, faces, material, body)


def elliptical_cap(
    *,
    name: str,
    body: bpy.types.Object,
    material: bpy.types.Material,
    center_x: float,
    center_z: float,
    radius_x: float,
    radius_z: float,
    outward: float,
    front: bool = True,
    segments: int = 40,
) -> bpy.types.Object:
    center_y = ray_surface_y(body, center_x, center_z, front=front)
    sign = -1.0 if front else 1.0
    vertices = [Vector((center_x, center_y + sign * outward, center_z))]
    for index in range(segments):
        angle = 2.0 * math.pi * index / segments
        x = center_x + radius_x * math.cos(angle)
        z = center_z + radius_z * math.sin(angle)
        y = ray_surface_y(body, x, z, front=front) + sign * outward
        vertices.append(Vector((x, y, z)))
    faces = []
    for index in range(segments):
        faces.append((0, 1 + index, 1 + ((index + 1) % segments)))
    return mesh_object(name, vertices, faces, material, body)


def ellipse_rim(
    *,
    name: str,
    body: bpy.types.Object,
    material: bpy.types.Material,
    center_x: float,
    center_z: float,
    radius_x: float,
    radius_z: float,
    thickness: float,
    height: float,
    front: bool = True,
    segments: int = 48,
) -> bpy.types.Object:
    vertices: list[Vector] = []
    sign = -1.0 if front else 1.0
    for index in range(segments):
        angle = 2.0 * math.pi * index / segments
        for radius_scale, lift in ((1.0 - thickness, 0.35), (1.0 + thickness, 0.0)):
            x = center_x + radius_x * radius_scale * math.cos(angle)
            z = center_z + radius_z * radius_scale * math.sin(angle)
            y = ray_surface_y(body, x, z, front=front) + sign * height * lift
            vertices.append(Vector((x, y, z)))
    faces = []
    for index in range(segments):
        following = (index + 1) % segments
        faces.append((2 * index, 2 * following, 2 * following + 1, 2 * index + 1))
    return mesh_object(name, vertices, faces, material, body)


def bind_to_rig(obj: bpy.types.Object, body: bpy.types.Object, rig: bpy.types.Object) -> dict[str, Any]:
    tree = KDTree(len(body.data.vertices))
    for index, vertex in enumerate(body.data.vertices):
        tree.insert(body.matrix_world @ vertex.co, index)
    tree.balance()
    names = {group.index: group.name for group in body.vertex_groups}
    assigned = 0
    groups_used: set[str] = set()
    for vertex in obj.data.vertices:
        world = obj.matrix_world @ vertex.co
        _position, source_index, _distance = tree.find(world)
        weights = [
            (names[element.group], float(element.weight))
            for element in body.data.vertices[int(source_index)].groups
            if float(element.weight) > 1.0e-8
        ]
        if not weights:
            continue
        weights = sorted(weights, key=lambda item: (-item[1], item[0]))[:4]
        total = sum(value for _name, value in weights)
        for group_name, value in weights:
            group = obj.vertex_groups.get(group_name) or obj.vertex_groups.new(name=group_name)
            group.add([vertex.index], value / total, "REPLACE")
            groups_used.add(group_name)
        assigned += 1
    modifier = obj.modifiers.new("KIRA_R22_NATIVE_RIG", "ARMATURE")
    modifier.object = rig
    modifier.use_vertex_groups = True
    modifier.use_deform_preserve_volume = True
    obj.parent = rig
    obj["private_review_only"] = True
    obj["owner_approved"] = False
    obj["runtime_activation_allowed"] = False
    obj["external_anatomy_surface_only"] = True
    return {
        "vertex_count": len(obj.data.vertices),
        "vertices_with_weights": assigned,
        "groups_used": sorted(groups_used),
        "armature": rig.name,
    }


def create_module(body: bpy.types.Object, rig: bpy.types.Object) -> tuple[list[bpy.types.Object], dict[str, Any]]:
    outer = make_material("R22_Outer_Vulvar_Tissue", (0.48, 0.17, 0.13, 1.0), 0.47, 0.06)
    inner = make_material("R22_Inner_Vulvar_Tissue", (0.54, 0.105, 0.115, 1.0), 0.42, 0.08)
    vestibule = make_material("R22_Vestibular_Mucosa", (0.30, 0.045, 0.055, 1.0), 0.34, 0.09)
    opening = make_material("R22_External_Opening_Recess", (0.075, 0.012, 0.016, 1.0), 0.58, 0.02)
    objects: list[bpy.types.Object] = []
    objects.append(ribbon(
        name=MODULE_PREFIX + "Left_Labium_Majus", body=body, material=outer,
        z_top=0.895, z_bottom=0.848,
        center_x=lambda t: -0.0115 - 0.0020 * math.sin(math.pi * t),
        half_width=lambda t: 0.0080 - 0.0015 * t,
        height=lambda t: 0.0042 - 0.0007 * t,
    ))
    objects.append(ribbon(
        name=MODULE_PREFIX + "Right_Labium_Majus", body=body, material=outer,
        z_top=0.895, z_bottom=0.848,
        center_x=lambda t: 0.0110 + 0.0017 * math.sin(math.pi * t),
        half_width=lambda t: 0.0077 - 0.0013 * t,
        height=lambda t: 0.0040 - 0.0006 * t,
    ))
    objects.append(elliptical_cap(
        name=MODULE_PREFIX + "Vestibule", body=body, material=vestibule,
        center_x=0.0, center_z=0.8700, radius_x=0.0072, radius_z=0.0190,
        outward=0.00045,
    ))
    objects.append(ribbon(
        name=MODULE_PREFIX + "Left_Labium_Minus", body=body, material=inner,
        z_top=0.891, z_bottom=0.851,
        center_x=lambda t: -0.0040 - 0.0006 * math.sin(math.pi * t),
        half_width=lambda t: 0.00315 - 0.00065 * t,
        height=lambda t: 0.00275 - 0.0005 * t,
    ))
    objects.append(ribbon(
        name=MODULE_PREFIX + "Right_Labium_Minus", body=body, material=inner,
        z_top=0.889, z_bottom=0.853,
        center_x=lambda t: 0.0037 + 0.00045 * math.sin(math.pi * t),
        half_width=lambda t: 0.00285 - 0.00055 * t,
        height=lambda t: 0.00245 - 0.00045 * t,
    ))
    objects.append(elliptical_cap(
        name=MODULE_PREFIX + "Vaginal_Introitus_Cap", body=body, material=opening,
        center_x=0.0002, center_z=0.8607, radius_x=0.0038, radius_z=0.0070,
        outward=0.0010,
    ))
    objects.append(ellipse_rim(
        name=MODULE_PREFIX + "Vaginal_Introitus_Rim", body=body, material=inner,
        center_x=0.0002, center_z=0.8607, radius_x=0.0043, radius_z=0.0077,
        thickness=0.18, height=0.0022,
    ))
    objects.append(elliptical_cap(
        name=MODULE_PREFIX + "Urethral_Meatus_Cap", body=body, material=opening,
        center_x=-0.0001, center_z=0.8766, radius_x=0.00135, radius_z=0.0010,
        outward=0.00125,
    ))
    objects.append(ellipse_rim(
        name=MODULE_PREFIX + "Urethral_Meatus_Rim", body=body, material=inner,
        center_x=-0.0001, center_z=0.8766, radius_x=0.00165, radius_z=0.00125,
        thickness=0.24, height=0.00135,
    ))
    objects.append(ellipse_rim(
        name=MODULE_PREFIX + "Clitoral_Hood", body=body, material=inner,
        center_x=0.0, center_z=0.8890, radius_x=0.0044, radius_z=0.0033,
        thickness=0.34, height=0.0027,
    ))
    objects.append(elliptical_cap(
        name=MODULE_PREFIX + "Clitoral_Glans", body=body, material=inner,
        center_x=0.0002, center_z=0.8867, radius_x=0.00155, radius_z=0.00175,
        outward=0.0020,
    ))
    objects.append(ribbon(
        name=MODULE_PREFIX + "Posterior_Fourchette", body=body, material=outer,
        z_top=0.8530, z_bottom=0.8470,
        center_x=lambda _t: 0.0,
        half_width=lambda _t: 0.0060,
        height=lambda _t: 0.00155,
        samples=10,
    ))
    objects.append(elliptical_cap(
        name=MODULE_PREFIX + "Anal_Canal_External_Cap", body=body, material=opening,
        center_x=0.0, center_z=0.8425, radius_x=0.0050, radius_z=0.0040,
        outward=0.0009, front=False,
    ))
    objects.append(ellipse_rim(
        name=MODULE_PREFIX + "Anal_Sphincter_External_Rim", body=body, material=outer,
        center_x=0.0, center_z=0.8425, radius_x=0.0058, radius_z=0.0048,
        thickness=0.22, height=0.0017, front=False,
    ))
    bindings = {obj.name: bind_to_rig(obj, body, rig) for obj in objects}
    return objects, {
        "component_order_anterior_to_posterior": [
            "clitoral_hood_and_glans",
            "external_urethral_meatus",
            "vaginal_introitus",
            "posterior_fourchette",
            "continuous_perineum",
            "separate_anal_region",
        ],
        "component_count": len(objects),
        "objects": [obj.name for obj in objects],
        "bindings": bindings,
        "deliberate_normal_variation": "minor left/right fold asymmetry",
    }


def main() -> int:
    if OUTPUT_DIR.exists() or EVIDENCE_DIR.exists():
        raise FileExistsError("append-only R22 external anatomy Attempt 01 already exists")
    if Path(bpy.data.filepath).resolve() != SOURCE.resolve():
        raise RuntimeError("exact R21 Attempt 08 source is not loaded")
    if sha256_file(SOURCE) != EXPECTED_SOURCE_SHA:
        raise RuntimeError("R21 Attempt 08 source hash drifted")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=False)
    body = find_body()
    rig = bpy.data.objects.get(RIG_NAME)
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError("exact inherited rig is absent")
    r21.clear_pose(rig)
    nonpatch_before = r21.nonpatch_snapshot(body)
    inherited = [obj for obj in bpy.data.objects if obj != body]
    protected_before = {obj.name: r21.object_digest(obj) for obj in inherited}
    rig_before = r21.object_digest(rig)
    topology = patch_topology(body)
    relaxation = relax_rejected_center(body, topology)
    if relaxation["seam_maximum_delta"] != 0.0:
        raise RuntimeError("localized relaxation moved the preserved interface")
    nonpatch_after_relaxation = r21.nonpatch_snapshot(body)
    if nonpatch_after_relaxation != nonpatch_before:
        raise RuntimeError("approved body outside the exact pelvic mask changed")
    objects, module = create_module(body, rig)
    protected_after = {obj.name: r21.object_digest(obj) for obj in inherited}
    if protected_after != protected_before or r21.object_digest(rig) != rig_before:
        raise RuntimeError("an inherited nonbody object or rig changed")
    body.name = "Kira_R22_Bald_Private_Inactive_ApprovedBody_ExternalAnatomyA01"
    body["candidate_id"] = "kira_r22_external_anatomy_attempt_01"
    body["private_review_only"] = True
    body["owner_approved"] = False
    body["runtime_assignment_allowed"] = False
    body["runtime_activation_allowed"] = False
    body["approved_face_preserved"] = True
    body["approved_general_body_preserved"] = True
    body["external_anatomy_owner_acceptance"] = False
    body["internal_physiology_implemented"] = False
    body["anatomy_module_objects_json"] = json.dumps(module["objects"], separators=(",", ":"))

    old_states = {obj.name: bool(obj.hide_render) for obj in bpy.data.objects if obj.type in {"LIGHT", "CAMERA"}}
    r21.OUTPUT_DIR = OUTPUT_DIR
    renders = r21.render_review(body)
    for name, state in old_states.items():
        if bpy.data.objects.get(name) is not None:
            bpy.data.objects[name].hide_render = state
    body["render_evidence_json"] = json.dumps(renders, separators=(",", ":"))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND), check_existing=False)
    blend_sha = sha256_file(OUTPUT_BLEND)
    intersection = r21.exact_audit(body)
    evidence = {
        "schema_version": 1,
        "artifact_kind": "KIRA_R22_EXTERNAL_ANATOMY_ATTEMPT01_BUILD_EVIDENCE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PRIVATE_INACTIVE_CLINICAL_EXTERNAL_ANATOMY_REVIEW_CANDIDATE",
        "source": {
            "blend": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
            "sha256": EXPECTED_SOURCE_SHA,
        },
        "owner_visual_decision_applied": {
            "approved_face_preserved": True,
            "approved_general_body_preserved": True,
            "rejected_pelvic_region_targeted": True,
            "eyebrows_pending_separate_worker": True,
            "nails_pending_separate_worker": True,
        },
        "localized_base_relaxation": relaxation,
        "external_anatomy_module": module,
        "preservation": {
            "nonpatch_body_exactly_preserved": nonpatch_after_relaxation == nonpatch_before,
            "inherited_nonbody_objects_exactly_preserved": protected_after == protected_before,
            "rig_exactly_preserved": r21.object_digest(rig) == rig_before,
        },
        "body_exact_intersection_audit": intersection,
        "medical_boundary": {
            "external_surface_only": True,
            "continuous_visible_order_implemented": module["component_order_anterior_to_posterior"],
            "normal_human_variation_retained": True,
            "sources": [
                "https://www.acog.org/womens-health/faqs/vulvovaginal-health",
                "https://www.ncbi.nlm.nih.gov/books/NBK547703/",
                "https://www.ncbi.nlm.nih.gov/books/NBK537132/",
            ],
        },
        "functional_truth": {
            "external_appearance_and_rig_binding_candidate": True,
            "bladder_urethra_bowel_rectum_reproductive_organs_implemented": False,
            "urination_defecation_reproduction_pregnancy_proven": False,
            "movement_and_contact_validation_pending": True,
            "separate_internal_simulation_and_state_system_required": True,
        },
        "outputs": {
            "blend": str(OUTPUT_BLEND.relative_to(ROOT)).replace("\\", "/"),
            "blend_sha256": blend_sha,
            "renders": renders,
        },
        "private": True,
        "inactive": True,
        "unassigned": True,
        "unpublished": True,
        "activation_or_export_performed": False,
    }
    evidence_path = EVIDENCE_DIR / "BUILD_EVIDENCE.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "OWNER_REVIEW_README.md").write_text(
        "# Kira R22 external anatomy Attempt 01\n\n"
        "Private, inactive, clinical review only. The owner-approved face and general body "
        "outside the exact pelvic mask are preserved. The external module is detachable and "
        "rig-bound. It is not proof of urinary, bowel, reproductive, pregnancy, or childbirth "
        "physiology. Eyebrows and nails remain separate correction stages.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": evidence["status"],
        "blend": str(OUTPUT_BLEND),
        "blend_sha256": blend_sha,
        "renders": renders,
        "module_component_count": len(objects),
        "body_exact_pairs": intersection["exact_genuine_penetration_pair_count"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
