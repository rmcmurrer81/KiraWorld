#!/usr/bin/env python3
"""Read-only Blender preflight for Kira's R21 localized correction.

The loaded R19 Blend is never saved.  This probe proves the exact rejected
pelvic mask, compares it with the licensed BlackProject adult-patch interface,
and inventories only the eyebrow, nail, mouth, and soft-tissue authoring hooks
needed by the next private/inactive candidate.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils.kdtree import KDTree


ROOT = Path(r"C:\Users\robmc\Kira")
SOURCE_BLEND = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/"
    "attempt_06/kira_r19_bald_targeted_material_movement_correction.blend"
)
SOURCE_GLB = ROOT / (
    "Avatar/avatar_builder/asset_library/base_body_reference/"
    "base_female_character_blackproject_cc_by_4.glb"
)
OUTPUT_DIR = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r21_localized_repair/preflight_01"
)
OUTPUT = OUTPUT_DIR / "PREFLIGHT.json"
BODY_NAME = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"
RIG_NAME = "Kira_R19_BlackProject_Native_188_Rig"
PATCH_SLOT = 5
ADULT_DATA_NAME = "Ariel_Mesh_Genitalia_0"


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


def matrix_rows(obj: bpy.types.Object) -> list[list[float]]:
    return [[float(value) for value in row] for row in obj.matrix_world]


def mesh_record(obj: bpy.types.Object) -> dict[str, object]:
    geometry = {
        "vertices": [
            [float(vertex.co.x), float(vertex.co.y), float(vertex.co.z)]
            for vertex in obj.data.vertices
        ],
        "polygons": [list(map(int, polygon.vertices)) for polygon in obj.data.polygons],
        "material_indices": [int(polygon.material_index) for polygon in obj.data.polygons],
    }
    return {
        "name": obj.name,
        "data_name": obj.data.name,
        "vertex_count": len(obj.data.vertices),
        "edge_count": len(obj.data.edges),
        "face_count": len(obj.data.polygons),
        "matrix_world": matrix_rows(obj),
        "geometry_material_sha256": sha256_json(geometry),
        "material_slots": [
            material.name if material is not None else None for material in obj.data.materials
        ],
        "vertex_groups": sorted(group.name for group in obj.vertex_groups),
        "modifiers": [
            {
                "name": modifier.name,
                "type": modifier.type,
                "object": getattr(getattr(modifier, "object", None), "name", None),
            }
            for modifier in obj.modifiers
        ],
    }


def selected_patch(body: bpy.types.Object) -> dict[str, object]:
    selected_faces = {
        int(poly.index)
        for poly in body.data.polygons
        if int(poly.material_index) == PATCH_SLOT
    }
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for poly in body.data.polygons:
        vertices = list(map(int, poly.vertices))
        for index, first in enumerate(vertices):
            edge = tuple(sorted((first, vertices[(index + 1) % len(vertices)])))
            edge_faces[edge].append(int(poly.index))
    interface_edges = []
    for edge, faces in edge_faces.items():
        selected_count = sum(face in selected_faces for face in faces)
        if selected_count == 1 and len(faces) == 2:
            interface_edges.append(edge)
    selected_vertices = {
        int(vertex)
        for face in selected_faces
        for vertex in body.data.polygons[face].vertices
    }
    interface_vertices = sorted({vertex for edge in interface_edges for vertex in edge})
    removable = sorted(selected_vertices - set(interface_vertices))
    world = {
        int(index): [float(value) for value in (body.matrix_world @ body.data.vertices[index].co)]
        for index in interface_vertices
    }
    record = {
        "material_slot": PATCH_SLOT,
        "material_name": body.data.materials[PATCH_SLOT].name,
        "face_count": len(selected_faces),
        "incident_vertex_count": len(selected_vertices),
        "interface_edge_count": len(interface_edges),
        "interface_vertex_count": len(interface_vertices),
        "removable_interior_vertex_count": len(removable),
        "face_indices": sorted(selected_faces),
        "interface_edges": sorted([list(edge) for edge in interface_edges]),
        "interface_vertices": interface_vertices,
        "interface_world_m": world,
        "face_index_sha256": sha256_json(sorted(selected_faces)),
        "interface_sha256": sha256_json(
            {"edges": sorted(interface_edges), "world_m": world}
        ),
    }
    return record


def boundary_cycle(obj: bpy.types.Object) -> list[int]:
    counts: dict[tuple[int, int], int] = defaultdict(int)
    for poly in obj.data.polygons:
        vertices = list(map(int, poly.vertices))
        for index, first in enumerate(vertices):
            counts[tuple(sorted((first, vertices[(index + 1) % len(vertices)])))] += 1
    boundary_edges = [edge for edge, count in counts.items() if count == 1]
    adjacency: dict[int, list[int]] = defaultdict(list)
    for first, second in boundary_edges:
        adjacency[first].append(second)
        adjacency[second].append(first)
    if not adjacency or any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise RuntimeError("source adult-patch boundary is not one closed two-valence cycle")
    start = min(adjacency)
    cycle = [start]
    previous = None
    current = start
    while True:
        candidates = sorted(adjacency[current])
        following = candidates[0] if candidates[0] != previous else candidates[1]
        if following == start:
            break
        if following in cycle:
            raise RuntimeError("source adult-patch boundary repeated before closure")
        cycle.append(following)
        previous, current = current, following
    if len(cycle) != len(adjacency):
        raise RuntimeError("source adult-patch has more than one boundary cycle")
    return cycle


def compare_interfaces(
    body: bpy.types.Object,
    patch: dict[str, object],
    adult: bpy.types.Object,
) -> dict[str, object]:
    cycle = boundary_cycle(adult)
    body_indices = list(map(int, patch["interface_vertices"]))
    tree = KDTree(len(body_indices))
    for ordinal, index in enumerate(body_indices):
        tree.insert(body.matrix_world @ body.data.vertices[index].co, ordinal)
    tree.balance()
    matches = []
    seen: set[int] = set()
    for source_index in cycle:
        source_world = adult.matrix_world @ adult.data.vertices[source_index].co
        _point, ordinal, distance = tree.find(source_world)
        target_index = body_indices[int(ordinal)]
        seen.add(target_index)
        matches.append(
            {
                "source_vertex": int(source_index),
                "r19_vertex": int(target_index),
                "distance_m": float(distance),
            }
        )
    return {
        "source_boundary_vertex_count": len(cycle),
        "r19_interface_vertex_count": len(body_indices),
        "unique_r19_matches": len(seen),
        "maximum_distance_m": max(row["distance_m"] for row in matches),
        "mean_distance_m": sum(row["distance_m"] for row in matches) / len(matches),
        "exact_one_to_one_at_1e_8_m": (
            len(cycle) == len(body_indices) == len(seen)
            and max(row["distance_m"] for row in matches) <= 1.0e-8
        ),
        "matches": matches,
    }


def role_inventory() -> dict[str, object]:
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    brows = sorted(
        obj.name for obj in meshes if "brow" in obj.name.lower() or "eyebrow" in obj.name.lower()
    )
    nails = sorted(
        obj.name
        for obj in meshes
        if bool(obj.get("nail_component"))
        or "fingernail" in obj.name.lower()
        or "toenail" in obj.name.lower()
    )
    mouth = sorted(
        obj.name
        for obj in meshes
        if any(token in obj.name.lower() for token in ("lip", "mouth", "tongue", "teeth", "gum"))
    )
    shape_keys = {}
    for obj in meshes:
        if obj.data.shape_keys and obj.data.shape_keys.key_blocks:
            names = [block.name for block in obj.data.shape_keys.key_blocks]
            relevant = [
                name
                for name in names
                if any(token in name.lower() for token in ("mouth", "lip", "jaw", "viseme", "phoneme"))
            ]
            if relevant:
                shape_keys[obj.name] = relevant
    return {
        "eyebrow_mesh_objects": brows,
        "nail_mesh_objects": nails,
        "nail_count": len(nails),
        "mouth_related_mesh_objects": mouth,
        "mouth_lip_jaw_shape_keys": shape_keys,
    }


def main() -> int:
    if OUTPUT.exists() or OUTPUT_DIR.exists():
        raise FileExistsError(f"append-only preflight already exists: {OUTPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    if bpy.data.filepath and Path(bpy.data.filepath).resolve() != SOURCE_BLEND.resolve():
        raise RuntimeError(f"wrong source Blend loaded: {bpy.data.filepath}")
    body = bpy.data.objects.get(BODY_NAME)
    rig = bpy.data.objects.get(RIG_NAME)
    if body is None or body.type != "MESH" or rig is None or rig.type != "ARMATURE":
        raise RuntimeError("exact R19 body or rig is absent")
    body_before = mesh_record(body)
    patch = selected_patch(body)
    roles_before = role_inventory()
    objects_before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE_GLB))
    imported = [obj for obj in bpy.data.objects if obj not in objects_before]
    adult = next(
        (obj for obj in imported if obj.type == "MESH" and obj.data.name == ADULT_DATA_NAME),
        None,
    )
    if adult is None:
        raise RuntimeError("licensed BlackProject adult-patch object is absent")
    comparison = compare_interfaces(body, patch, adult)
    source_record = mesh_record(adult)
    body_after_import = mesh_record(body)
    if body_after_import != body_before:
        raise RuntimeError("R19 body changed during read-only import comparison")
    report = {
        "schema_version": 1,
        "artifact_kind": "KIRA_R21_LOCALIZED_REPAIR_READ_ONLY_PREFLIGHT",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PREFLIGHT_COMPLETE_NO_BODY_SAVE_NO_MUTATION",
        "scope": {
            "approved_face_preserved": True,
            "approved_general_body_preserved": True,
            "authorized_visual_targets": ["pelvic_perineal_surface", "eyebrows", "nails"],
            "later_separate_gates": ["movement", "soft_tissue_and_bra_response", "wav_driven_lip_sync"],
            "hair_loaded_into_runtime": False,
            "private": True,
            "inactive": True,
            "unassigned": True,
        },
        "source_blend": {
            "project_relative_path": str(SOURCE_BLEND.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(SOURCE_BLEND),
            "saved_or_overwritten": False,
        },
        "licensed_reference": {
            "project_relative_path": str(SOURCE_GLB.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(SOURCE_GLB),
            "usage": "same-lineage topology and boundary reference; no source file modification",
            "adult_patch": source_record,
        },
        "r19_body_before": body_before,
        "r19_patch_mask": patch,
        "source_to_r19_interface": comparison,
        "component_inventory": roles_before,
        "truth_boundary": {
            "external_surface_can_be_authored": True,
            "external_surface_does_not_prove_urination_defecation_or_reproduction": True,
            "internal_organs_and_physiology_require_separate_versioned_systems": True,
            "soft_tissue_and_garment_response_require_separate_dynamic_tests": True,
            "lip_sync_requires_exact_final_wav_timeline": True,
        },
        "blender_file_saved": False,
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "output": str(OUTPUT),
        "source_interface_exact": comparison["exact_one_to_one_at_1e_8_m"],
        "patch_faces": patch["face_count"],
        "eyebrow_objects": len(roles_before["eyebrow_mesh_objects"]),
        "nails": roles_before["nail_count"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
