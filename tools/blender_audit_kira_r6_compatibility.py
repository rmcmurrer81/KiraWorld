#!/usr/bin/env python3
"""Non-visual exact-candidate compatibility audit for private Kira R6."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--eye-manifest", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (
        bpy.data.meshes,
        bpy.data.armatures,
        bpy.data.actions,
        bpy.data.materials,
        bpy.data.images,
    ):
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def import_body(path: Path) -> tuple[bpy.types.Object, bpy.types.Object, dict[str, object]]:
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(path))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    arms = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if not meshes or len(arms) != 1:
        raise ValueError(f"expected at least one mesh and one armature in {path}")
    body = max(meshes, key=lambda obj: len(obj.data.vertices))
    inventory = {
        "mesh_count": len(meshes),
        "mesh_names": [obj.name for obj in meshes],
        "substantive_mesh_count": sum(len(obj.data.vertices) > 1000 for obj in meshes),
        "substantive_mesh_names": [obj.name for obj in meshes if len(obj.data.vertices) > 1000],
        "importer_display_helper_mesh_names": [obj.name for obj in meshes if len(obj.data.vertices) <= 1000],
        "body_name": body.name,
        "mesh_name": body.data.name,
        "armature_name": arms[0].name,
        "vertex_count": len(body.data.vertices),
        "polygon_count": len(body.data.polygons),
        "shape_keys": [
            {"name": key.name, "value": round(float(key.value), 8)}
            for key in body.data.shape_keys.key_blocks
        ]
        if body.data.shape_keys
        else [],
    }
    return body, arms[0], inventory


def morphed_rest_points(body: bpy.types.Object) -> list[Vector]:
    """Evaluate morph weights without armature/action playback.

    A freshly imported evidence action can become Blender's active action and
    pose the armature at frame 1.  Compatibility here concerns the rest cage
    plus its authored body morph, so animation must not contaminate the point
    comparison.
    """

    points = [vertex.co.copy() for vertex in body.data.vertices]
    shape_keys = body.data.shape_keys
    if shape_keys is None or len(shape_keys.key_blocks) <= 1:
        return points
    basis = shape_keys.key_blocks[0]
    for key in shape_keys.key_blocks[1:]:
        value = float(key.value)
        if abs(value) <= 1e-12:
            continue
        for index, point in enumerate(points):
            point += (key.data[index].co - basis.data[index].co) * value
    return points


def face_hash(mesh: bpy.types.Mesh) -> str:
    digest = hashlib.sha256()
    for polygon in mesh.polygons:
        vertices = tuple(int(value) for value in polygon.vertices)
        digest.update(struct.pack("<II", int(polygon.index), len(vertices)))
        digest.update(struct.pack(f"<{len(vertices)}I", *vertices))
    return digest.hexdigest()


def matrix_values(value: Matrix) -> list[float]:
    return [float(value[row][column]) for row in range(4) for column in range(4)]


def max_delta(first: list[float], second: list[float]) -> float:
    if len(first) != len(second):
        return math.inf
    return max((abs(a - b) for a, b in zip(first, second)), default=0.0)


def bone_inventory(armature: bpy.types.Object) -> dict[str, object]:
    bones = list(armature.data.bones)
    return {
        "names": [bone.name for bone in bones],
        "matrices": {bone.name: matrix_values(bone.matrix_local) for bone in bones},
    }


def displacement_stats(
    source_points: list[Vector],
    candidate_points: list[Vector],
    indices: list[int],
    *,
    tolerance: float = 5e-6,
) -> dict[str, object]:
    distances = [(candidate_points[index] - source_points[index]).length for index in indices]
    return {
        "vertex_count": len(indices),
        "moved_vertex_count_over_tolerance": sum(value > tolerance for value in distances),
        "maximum_local_displacement": round(max(distances, default=0.0), 10),
        "mean_local_displacement": round(sum(distances) / max(len(distances), 1), 10),
        "tolerance": tolerance,
        "exact_within_tolerance": max(distances, default=0.0) <= tolerance,
    }


def main() -> int:
    args = parse_args()
    source_path = Path(args.source).resolve(strict=True)
    candidate_path = Path(args.candidate).resolve(strict=True)
    eye_manifest_path = Path(args.eye_manifest).resolve(strict=True)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    eye_manifest = json.loads(eye_manifest_path.read_text(encoding="utf-8"))
    eye_rig_path = Path(eye_manifest["eye_rig"]).resolve(strict=True)

    source_body, source_armature, source_inventory = import_body(source_path)
    source_points = morphed_rest_points(source_body)
    source_face_hash = face_hash(source_body.data)
    source_body_matrix = matrix_values(source_body.matrix_world)
    source_bones = bone_inventory(source_armature)
    source_group_names = [group.name for group in source_body.vertex_groups]

    candidate_body, candidate_armature, candidate_inventory = import_body(candidate_path)
    candidate_points = morphed_rest_points(candidate_body)
    candidate_face_hash = face_hash(candidate_body.data)
    candidate_body_matrix = matrix_values(candidate_body.matrix_world)
    candidate_bones = bone_inventory(candidate_armature)
    candidate_group_names = [group.name for group in candidate_body.vertex_groups]

    same_vertex_index_domain = len(source_points) == len(candidate_points)
    if not same_vertex_index_domain:
        raise ValueError("candidate no longer shares the enrolled source vertex index domain")

    head_indices = [index for index, point in enumerate(source_points) if point.z >= 6.0]
    mouth_indices = [
        index
        for index, point in enumerate(source_points)
        if 6.30 <= point.z <= 6.90 and abs(point.x) <= 0.34 and point.y <= -0.14
    ]
    chest_indices = [
        index
        for index, point in enumerate(source_points)
        if 5.14 <= point.z <= 5.68 and abs(abs(point.x) - 0.31) <= 0.18 and point.y <= -0.30
    ]
    pelvis_indices = [
        index
        for index, point in enumerate(source_points)
        if 3.34 <= point.z <= 4.02 and abs(point.x) <= 0.27 and point.y <= -0.10
    ]
    head_stats = displacement_stats(source_points, candidate_points, head_indices)
    mouth_stats = displacement_stats(source_points, candidate_points, mouth_indices)
    chest_stats = displacement_stats(source_points, candidate_points, chest_indices)
    pelvis_stats = displacement_stats(source_points, candidate_points, pelvis_indices)

    bone_names_preserved = source_bones["names"] == candidate_bones["names"]
    bone_matrix_maximum_delta = math.inf
    if bone_names_preserved:
        bone_matrix_maximum_delta = max(
            max_delta(source_bones["matrices"][name], candidate_bones["matrices"][name])
            for name in source_bones["names"]
        )
    topology_preserved = (
        source_inventory["vertex_count"] == candidate_inventory["vertex_count"]
        and source_inventory["polygon_count"] == candidate_inventory["polygon_count"]
        and source_face_hash == candidate_face_hash
    )
    body_names_preserved = (
        source_inventory["body_name"] == candidate_inventory["body_name"]
        and source_inventory["mesh_name"] == candidate_inventory["mesh_name"]
        and source_inventory["armature_name"] == candidate_inventory["armature_name"]
    )
    exact_source_sha = sha256_file(source_path)
    exact_candidate_sha = sha256_file(candidate_path)
    eye_rig_sha = sha256_file(eye_rig_path)
    eye_manifest_sha = sha256_file(eye_manifest_path)
    head_bone_preserved = False
    head_bone_name = "mixamorig:Head_06"
    if bone_names_preserved and head_bone_name in source_bones["matrices"]:
        head_bone_preserved = (
            max_delta(
                source_bones["matrices"][head_bone_name],
                candidate_bones["matrices"][head_bone_name],
            )
            <= 1e-6
        )

    eye_structural = (
        eye_manifest.get("source_body_sha256") == exact_source_sha
        and eye_manifest.get("eye_rig_sha256") == eye_rig_sha
        and head_stats["exact_within_tolerance"]
        and head_bone_preserved
        and max_delta(source_body_matrix, candidate_body_matrix) <= 1e-7
    )
    mouth_structural = (
        topology_preserved
        and body_names_preserved
        and source_group_names == candidate_group_names
        and mouth_stats["exact_within_tolerance"]
        and candidate_inventory["substantive_mesh_count"] == 1
    )
    adult_form_materially_changed = (
        chest_stats["moved_vertex_count_over_tolerance"] > 0
        and pelvis_stats["moved_vertex_count_over_tolerance"] > 0
        and head_stats["exact_within_tolerance"]
    )

    audit = {
        "schema_version": 1,
        "non_visual_only": True,
        "source": {
            "path": str(source_path),
            "sha256": exact_source_sha,
            "inventory": source_inventory,
        },
        "candidate": {
            "path": str(candidate_path),
            "sha256": exact_candidate_sha,
            "inventory": candidate_inventory,
        },
        "structural_preservation": {
            "same_vertex_index_domain": same_vertex_index_domain,
            "source_face_index_sha256": source_face_hash,
            "candidate_face_index_sha256": candidate_face_hash,
            "topology_preserved_after_fresh_import": topology_preserved,
            "body_mesh_armature_names_preserved": body_names_preserved,
            "vertex_group_names_and_order_preserved": source_group_names == candidate_group_names,
            "bone_names_and_order_preserved": bone_names_preserved,
            "bone_count": len(candidate_bones["names"]),
            "bone_rest_matrix_maximum_delta": round(float(bone_matrix_maximum_delta), 10),
            "bone_rest_matrices_preserved_within_2e_5": bone_matrix_maximum_delta <= 2e-5,
            "body_matrix_maximum_delta": round(max_delta(source_body_matrix, candidate_body_matrix), 10),
        },
        "deformation_regions": {
            "protected_head": head_stats,
            "protected_existing_mouth_surface": mouth_stats,
            "adult_breast_surface": chest_stats,
            "adult_external_pelvic_surface": pelvis_stats,
            "adult_body_form_materially_changed": adult_form_materially_changed,
        },
        "staged_eye_rig_compatibility": {
            "manifest_path": str(eye_manifest_path),
            "manifest_sha256": eye_manifest_sha,
            "eye_rig_path": str(eye_rig_path),
            "eye_rig_sha256": eye_rig_sha,
            "eye_manifest_source_hash_matches_exact_source": eye_manifest.get("source_body_sha256") == exact_source_sha,
            "eye_rig_hash_matches_manifest": eye_manifest.get("eye_rig_sha256") == eye_rig_sha,
            "protected_head_surface_exact": head_stats["exact_within_tolerance"],
            "head_bone_rest_transform_preserved": head_bone_preserved,
            "body_transform_preserved": max_delta(source_body_matrix, candidate_body_matrix) <= 1e-7,
            "structural_reuse_supported": eye_structural,
            "assembled_fit_on_exact_candidate_proven": False,
            "runtime_eye_behavior_proven": False,
        },
        "existing_mouth_lip_sync_compatibility": {
            "single_substantive_exported_body_mesh": candidate_inventory["substantive_mesh_count"] == 1,
            "no_second_substantive_or_named_mouth_mesh": (
                candidate_inventory["substantive_mesh_count"] == 1
                and not any("mouth" in name.lower() for name in candidate_inventory["mesh_names"])
            ),
            "source_topology_and_index_domain_preserved": topology_preserved,
            "source_names_preserved": body_names_preserved,
            "existing_mouth_surface_exact": mouth_stats["exact_within_tolerance"],
            "structural_compatibility_supported": mouth_structural,
            "runtime_lip_sync_playback_on_exact_candidate_proven": False,
            "truth_limit": "Structural preservation only; audio-driven playback must pass in an isolated inactive review before activation.",
        },
        "gates": {
            "adult_external_form_materially_advanced": adult_form_materially_changed,
            "anatomical_completeness_proven": False,
            "stable_working_rig_proven": False,
            "exact_eye_fit_proven": False,
            "exact_runtime_lip_sync_proven": False,
            "owner_approved": False,
            "runtime_activation_allowed": False,
            "autobuild_allowed": False,
        },
    }
    output.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(output),
                "candidate_sha256": exact_candidate_sha,
                "topology_preserved": topology_preserved,
                "adult_form_materially_changed": adult_form_materially_changed,
                "eye_structural_reuse_supported": eye_structural,
                "mouth_structural_compatibility_supported": mouth_structural,
                "runtime_activation_allowed": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
