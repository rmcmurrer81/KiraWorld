#!/usr/bin/env python3
"""Blender worker for the inactive Kira/adult-reference feasibility workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)


def import_glb(path: Path) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [obj for obj in bpy.data.objects if obj not in before]


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def world_bounds(objects: list[bpy.types.Object]) -> dict[str, list[float]]:
    points: list[Vector] = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        points.extend(obj.matrix_world @ vertex.co for vertex in obj.data.vertices)
    if not points:
        return {"low": [], "high": [], "center": [], "size": []}
    low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    center = (low + high) * 0.5
    return {
        "low": [round(float(value), 9) for value in low],
        "high": [round(float(value), 9) for value in high],
        "center": [round(float(value), 9) for value in center],
        "size": [round(float(value), 9) for value in high - low],
    }


def mesh_record(obj: bpy.types.Object) -> dict[str, object]:
    mesh = obj.data
    positive_groups = set()
    maximum_influences = 0
    unweighted = 0
    for vertex in mesh.vertices:
        groups = [item.group for item in vertex.groups if float(item.weight) > 1e-8]
        positive_groups.update(groups)
        maximum_influences = max(maximum_influences, len(groups))
        if not groups:
            unweighted += 1
    return {
        "object": obj.name,
        "mesh": mesh.name,
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "material_slots": len(obj.material_slots),
        "shape_key_count": 0 if mesh.shape_keys is None else len(mesh.shape_keys.key_blocks),
        "vertex_group_count": len(obj.vertex_groups),
        "positive_vertex_group_count": len(positive_groups),
        "unweighted_vertices": unweighted,
        "maximum_positive_influences": maximum_influences,
    }


def armature_record(obj: bpy.types.Object) -> dict[str, object]:
    bones = list(obj.data.bones)
    return {
        "object": obj.name,
        "bone_count": len(bones),
        "bone_names": [bone.name for bone in bones],
    }


def total(records: list[dict[str, object]], key: str) -> int:
    return sum(int(record[key]) for record in records)


def create_readme(config: dict[str, object], decision: dict[str, object]) -> None:
    text = bpy.data.texts.new("READ_ME_INACTIVE_FEASIBILITY_ONLY.txt")
    text.write(
        "KIRA R7 ADULT-SURFACE REFERENCE FEASIBILITY — INACTIVE\n\n"
        "This is not an avatar candidate and is not approved for export, binding, or activation.\n"
        "The exact Kira R6 surface/79-joint cage and the exact CC BY 4.0 BlackProject\n"
        "Base Female Character are in separate locked collections.  The reference is present\n"
        "only for measurements, construction study, and a future human-authored retopology.\n\n"
        "No shrinkwrap, data transfer, remesh, sculpt, vertex movement, reweighting, or material\n"
        "transfer was applied.  Automatic transfer is blocked because the meshes, topology,\n"
        "skeletons, semantic regions, head boundary, and adult surface construction do not\n"
        "correspond.  A deformation or recolor of R6 would preserve the doll-safe topology.\n\n"
        "NEXT BLENDER OPERATION (in the isolated R7 authoring workspace, not here):\n"
        "Visually select and attest one closed neck boundary below Kira's complete protected\n"
        "head and existing single mouth.  Then seed a NEW project-owned body retopology from\n"
        "that reviewed boundary and quad-author downward on Kira's exact 79-joint cage.  Toggle\n"
        "the CC BY reference only for dimensionless proportion/construction comparison.  Do not\n"
        "shrinkwrap or copy its face, identity, materials, textures, rig, or separate anatomy mesh.\n\n"
        f"Reference author: {config['reference_provenance']['author']}\n"
        f"Reference license: {config['reference_provenance']['license']}\n"
        f"Reference source: {config['reference_provenance']['source']}\n"
        f"Decision: {decision['status']}\n"
    )


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    kira_path = Path(config["kira_source"]).resolve(strict=True)
    reference_path = Path(config["reference_source"]).resolve(strict=True)
    if sha256_file(kira_path) != config["kira_sha256"]:
        raise ValueError("Kira source hash mismatch")
    if sha256_file(reference_path) != config["reference_sha256"]:
        raise ValueError("adult reference source hash mismatch")
    if config.get("candidate_export_requested") or config.get("geometry_transfer_requested"):
        raise ValueError("this worker accepts only a non-authoring feasibility request")

    clear_scene()
    kira_collection = bpy.data.collections.new("KIRA_EXACT_79_CAGE_READ_ONLY")
    reference_collection = bpy.data.collections.new("CC_BY_ADULT_REFERENCE_MEASUREMENT_ONLY")
    bpy.context.scene.collection.children.link(kira_collection)
    bpy.context.scene.collection.children.link(reference_collection)

    kira_objects = import_glb(kira_path)
    for obj in kira_objects:
        move_to_collection(obj, kira_collection)
        obj["r7_feasibility_role"] = "exact_kira_source_read_only"
        obj.hide_select = True
        obj.lock_location = (True, True, True)
        obj.lock_rotation = (True, True, True)
        obj.lock_scale = (True, True, True)

    reference_objects = import_glb(reference_path)
    for obj in reference_objects:
        move_to_collection(obj, reference_collection)
        obj["r7_feasibility_role"] = "cc_by_reference_measurement_only"
        obj["license"] = config["reference_provenance"]["license"]
        obj["source"] = config["reference_provenance"]["source"]
        obj.hide_select = True
        obj.hide_render = True
        obj.lock_location = (True, True, True)
        obj.lock_rotation = (True, True, True)
        obj.lock_scale = (True, True, True)
        if obj.type == "MESH":
            obj.display_type = "WIRE"
    reference_collection.hide_render = True

    kira_all_meshes = [obj for obj in kira_objects if obj.type == "MESH"]
    # Both GLBs import a small unweighted Icosphere helper.  It is not one of
    # either source's skinned construction meshes and must not contaminate the
    # body counts or bounds used for this correspondence decision.
    kira_meshes = [obj for obj in kira_all_meshes if len(obj.vertex_groups) > 0]
    kira_armatures = [obj for obj in kira_objects if obj.type == "ARMATURE"]
    reference_all_meshes = [obj for obj in reference_objects if obj.type == "MESH"]
    reference_meshes = [
        obj for obj in reference_all_meshes if len(obj.vertex_groups) > 0
    ]
    reference_armatures = [obj for obj in reference_objects if obj.type == "ARMATURE"]
    if len(kira_armatures) != 1 or len(kira_armatures[0].data.bones) != 79:
        raise ValueError("exact Kira source did not import with one 79-bone cage")
    if len(reference_armatures) != 1:
        raise ValueError("adult reference did not import with exactly one source armature")

    kira_mesh_records = [mesh_record(obj) for obj in kira_meshes]
    reference_mesh_records = [mesh_record(obj) for obj in reference_meshes]
    kira_rig = armature_record(kira_armatures[0])
    reference_rig = armature_record(reference_armatures[0])
    common_bones = sorted(set(kira_rig["bone_names"]) & set(reference_rig["bone_names"]))
    reference_mesh_names = [record["mesh"] for record in reference_mesh_records]
    anatomy_meshes = [
        name for name in reference_mesh_names if "genital" in str(name).lower()
    ]
    face_identity_meshes = [
        name
        for name in reference_mesh_names
        if any(token in str(name).lower() for token in ("face", "lips", "ears", "pupil", "iris"))
    ]

    decision = {
        "status": "automatic_retopology_or_feature_transfer_not_safe",
        "genuinely_different_adult_surface_created": False,
        "reason": (
            "The authorized model is a useful adult proportion and construction reference, "
            "but it has a different 188-bone rig, 28 fragmented meshes, no reviewed Kira-to-reference "
            "surface correspondence, and identity-bearing face parts. Kira's protected head/body "
            "boundary and adult-region masks are still unreviewed. Shrinkwrap, nearest-surface "
            "transfer, remesh, or stronger deformation would either preserve the doll-safe topology, "
            "copy another model's identity/construction, or destroy Kira's 79-joint weights and "
            "existing single mouth."
        ),
    }
    next_operation = {
        "workspace": "Avatar/avatar_builder/candidate_sources/kira_adult_body_r7/workspace_v1/kira_r7_authoring_workspace.blend",
        "operation": "human_reviewed_neck_boundary_then_new_body_retopology_seed",
        "steps": [
            "Confirm and attest the exact 207-vertex existing lip island; keep it immutable as Kira's one mouth.",
            "Visually select one closed neck boundary below the full jaw, ears, scalp, face, eyelids, and sockets; flood-select and hash the protected head.",
            "Create a new project-owned retopology object from a duplicate of only that reviewed boundary ring; do not deform R6 into another relabeled pass.",
            "Quad-author the body downward around Kira's unchanged 79-joint cage, using the CC BY model only for dimensionless proportion and construction comparison.",
            "Author cohesive adult external-form topology rather than copying the reference's separate genitalia or identity-bearing face meshes.",
            "Weight and test the new vertices separately; export remains blocked until topology, anatomy, deformation, face, eye, and owner-review gates pass.",
        ],
    }

    create_readme(config, decision)
    bpy.context.scene["r7_feasibility_only"] = True
    bpy.context.scene["candidate_export_allowed"] = False
    bpy.context.scene["runtime_activation_allowed"] = False
    bpy.context.scene["automatic_geometry_transfer_allowed"] = False
    bpy.context.scene["reference_attribution"] = (
        "Base Female Character by BlackProject, CC BY 4.0, Sketchfab"
    )

    evidence = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "mode": "inactive_locked_reference_comparison_no_authoring",
        "sources": {
            "kira_r6": {"path": str(kira_path), "sha256": config["kira_sha256"]},
            "adult_reference": {
                "path": str(reference_path),
                "sha256": config["reference_sha256"],
                "provenance": config["reference_provenance"],
                "permitted_role": "proportion_and_construction_reference_only",
            },
        },
        "kira": {
            "mesh_count": len(kira_mesh_records),
            "unweighted_import_helper_mesh_count": len(kira_all_meshes) - len(kira_meshes),
            "mesh_totals": {
                "vertices": total(kira_mesh_records, "vertices"),
                "polygons": total(kira_mesh_records, "polygons"),
            },
            "meshes": kira_mesh_records,
            "rig": kira_rig,
            "world_bounds_m": world_bounds(kira_meshes),
            "identity_head_and_existing_mouth_protected_by_policy": True,
            "human_reviewed_head_boundary_available": False,
        },
        "adult_reference": {
            "mesh_count": len(reference_mesh_records),
            "unweighted_import_helper_mesh_count": len(reference_all_meshes) - len(reference_meshes),
            "mesh_totals": {
                "vertices": total(reference_mesh_records, "vertices"),
                "polygons": total(reference_mesh_records, "polygons"),
            },
            "meshes": reference_mesh_records,
            "rig": reference_rig,
            "world_bounds_m": world_bounds(reference_meshes),
            "separate_adult_anatomy_meshes": anatomy_meshes,
            "identity_bearing_face_meshes": face_identity_meshes,
        },
        "correspondence": {
            "kira_bone_count": len(kira_rig["bone_names"]),
            "reference_bone_count": len(reference_rig["bone_names"]),
            "common_bone_names": common_bones,
            "common_bone_count": len(common_bones),
            "exact_skeleton_match": kira_rig["bone_names"] == reference_rig["bone_names"],
            "same_mesh_count": len(kira_mesh_records) == len(reference_mesh_records),
            "same_total_vertex_count": total(kira_mesh_records, "vertices") == total(reference_mesh_records, "vertices"),
            "same_total_polygon_count": total(kira_mesh_records, "polygons") == total(reference_mesh_records, "polygons"),
            "reviewed_vertex_or_surface_map_present": False,
            "reviewed_semantic_region_map_present": False,
            "safe_weight_transfer_map_present": False,
        },
        "method_assessment": {
            "stronger_r6_deformation": "blocked_preserves_existing_topology_and_does_not_create_missing_adult_construction",
            "material_or_color_change": "blocked_never_topology_or_anatomy_proof",
            "shrinkwrap_or_nearest_surface": "blocked_no_semantic_correspondence_and_would_risk_head_identity_and_fragmented_reference_parts",
            "automatic_remesh": "blocked_would_destroy_exact_head_mouth_topology_uvs_and_79_joint_weights",
            "automatic_weight_transfer": "blocked_188_to_79_rig_mismatch_and_no_reviewed_body_surface_map",
            "manual_project_owned_retopology": "feasible_after_reviewed_head_boundary_and_mask_attestation",
        },
        "decision": decision,
        "next_blender_operation": next_operation,
        "workspace": {
            "path": config["workspace"],
            "collections": [kira_collection.name, reference_collection.name],
            "reference_visible_as_wire_measurement_source": True,
            "source_objects_locked_from_selection_and_transform": True,
            "candidate_object_created": False,
        },
        "gates": {
            "automatic_geometry_transfer_allowed": False,
            "manual_geometry_authoring_allowed_now": False,
            "complete_adult_anatomy_proven": False,
            "stable_79_joint_deformation_proven": False,
            "candidate_export_allowed": False,
            "runtime_activation_allowed": False,
            "autobuild_allowed": False,
            "owner_approved": False,
        },
        "safety": {
            "geometry_transfer_applied": False,
            "modifiers_added": False,
            "shape_keys_added": False,
            "weights_changed": False,
            "materials_or_textures_copied": False,
            "candidate_glb_exported": False,
            "live_r6_touched": False,
            "runtime_binding_touched": False,
            "avatar_builder_binding_touched": False,
            "home_world_touched": False,
        },
        "truth_note": (
            "This workspace proves only source structure, incompatibility, provenance, and the "
            "absence of a safe automatic transfer path. It does not prove complete adult anatomy "
            "or create an R7 avatar candidate."
        ),
    }
    evidence_path = Path(config["evidence"])
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=config["workspace"])
    print(json.dumps({"ok": True, "evidence": str(evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
