from __future__ import annotations

"""Read-only Blender state extractor for the append-only R24 R6 gate."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import blender_extract_kira_r24_candidate_read_only_r5 as r5
import kira_r24_r6_semantic_projection as projection


SCHEMA = "kira.avatar.r24.read_only_blender_extraction.v6"


def constraint_rows(values: Any) -> list[dict[str, Any]]:
    return [
        {
            "name": str(item.name),
            "type": str(item.type),
            "rna": r5.rna_record(item, skip={"name", "type"}),
            "custom_properties": projection.custom_properties(item),
        }
        for item in values
    ]


def curve_record(curve: Any) -> dict[str, Any]:
    row = r5.driver_or_curve_record(curve)
    row["custom_properties"] = projection.custom_properties(curve)
    row["group_custom_properties"] = (
        projection.custom_properties(curve.group) if getattr(curve, "group", None) else {}
    )
    row["keyframes"] = [
        {**r5.rna_record(point), "custom_properties": projection.custom_properties(point)}
        for point in curve.keyframe_points
    ]
    row["sampled_points"] = [
        {**r5.rna_record(point), "custom_properties": projection.custom_properties(point)}
        for point in getattr(curve, "sampled_points", ())
    ]
    row["modifiers"] = [
        {
            "type": str(modifier.type),
            "rna": r5.rna_record(modifier, skip={"type"}),
            "custom_properties": projection.custom_properties(modifier),
        }
        for modifier in curve.modifiers
    ]
    driver = getattr(curve, "driver", None)
    if driver is not None:
        row["driver"]["custom_properties"] = projection.custom_properties(driver)
        for variable_row, variable in zip(row["driver"]["variables"], driver.variables, strict=True):
            variable_row["custom_properties"] = projection.custom_properties(variable)
            for target_row, target in zip(variable_row["targets"], variable.targets, strict=True):
                target_row["custom_properties"] = projection.custom_properties(target)
    return row


def animation_data_record(value: Any) -> dict[str, Any] | None:
    animation = getattr(value, "animation_data", None)
    if animation is None:
        return None
    return {
        "rna": r5.rna_record(animation, skip={"drivers", "nla_tracks"}),
        "custom_properties": projection.custom_properties(animation),
        "drivers": [curve_record(curve) for curve in animation.drivers],
        "nla_tracks": [
            {
                "name": str(track.name),
                "rna": r5.rna_record(track, skip={"name", "strips"}),
                "custom_properties": projection.custom_properties(track),
                "strips": [
                    projection.nla_strip_record(
                        strip,
                        rna_serializer=r5.rna_record,
                        curve_serializer=curve_record,
                    )
                    for strip in track.strips
                ],
            }
            for track in animation.nla_tracks
        ],
    }


def action_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for action in sorted(bpy.data.actions, key=lambda item: str(item.name)):
        row: dict[str, Any] = {
            "name": str(action.name),
            "rna": r5.rna_record(action, skip={"name", "fcurves", "groups", "slots", "layers"}),
            "custom_properties": projection.custom_properties(action),
            "groups": [
                {
                    "rna": r5.rna_record(group, skip={"channels"}),
                    "custom_properties": projection.custom_properties(group),
                }
                for group in getattr(action, "groups", ())
            ],
        }
        if hasattr(action, "fcurves"):
            row["storage"] = "legacy"
            row["fcurves"] = [
                curve_record(curve)
                for curve in sorted(action.fcurves, key=lambda item: (str(item.data_path), int(item.array_index)))
            ]
        else:
            row["storage"] = "layered"
            row["slots"] = [
                {"rna": r5.rna_record(slot), "custom_properties": projection.custom_properties(slot)}
                for slot in getattr(action, "slots", ())
            ]
            layers = []
            for layer in getattr(action, "layers", ()):
                strips = []
                for strip in getattr(layer, "strips", ()):
                    bags = []
                    for bag in getattr(strip, "channelbags", ()):
                        bags.append(
                            {
                                "slot_handle": int(bag.slot_handle),
                                "rna": r5.rna_record(bag, skip={"fcurves"}),
                                "custom_properties": projection.custom_properties(bag),
                                "fcurves": [curve_record(curve) for curve in bag.fcurves],
                            }
                        )
                    strips.append(
                        {
                            "rna": r5.rna_record(strip, skip={"channelbags"}),
                            "custom_properties": projection.custom_properties(strip),
                            "channelbags": bags,
                        }
                    )
                layers.append(
                    {
                        "rna": r5.rna_record(layer, skip={"strips"}),
                        "custom_properties": projection.custom_properties(layer),
                        "strips": strips,
                    }
                )
            row["layers"] = layers
        rows.append(row)
    return rows


def node_tree_record(tree: Any) -> dict[str, Any]:
    row = r5.node_tree_record(tree)
    row["custom_properties"] = projection.custom_properties(tree)
    by_name = {str(node.name): node for node in tree.nodes}
    for node_row in row["nodes"]:
        node = by_name[node_row["name"]]
        node_row["custom_properties"] = projection.custom_properties(node)
        node_row["nested_collections"] = projection.node_nested_collections(node)
        for socket_row, socket in zip(node_row["inputs"], node.inputs, strict=True):
            socket_row["custom_properties"] = projection.custom_properties(socket)
        for socket_row, socket in zip(node_row["outputs"], node.outputs, strict=True):
            socket_row["custom_properties"] = projection.custom_properties(socket)
    return row


def material_record(material: Any) -> dict[str, Any]:
    row = r5.material_record(material)
    row["custom_properties"] = projection.custom_properties(material)
    row["animation_data"] = animation_data_record(material)
    row["node_tree"] = node_tree_record(material.node_tree) if material.node_tree else None
    return row


def object_record(obj: Any) -> dict[str, Any]:
    row = r5.object_record(obj)
    row["custom_properties"] = projection.custom_properties(obj)
    row["material_slots"] = projection.material_slot_records(obj.material_slots)
    row["constraints"] = constraint_rows(obj.constraints)
    row["modifiers"] = [
        {
            "name": str(modifier.name),
            "type": str(modifier.type),
            "rna": r5.rna_record(modifier, skip={"name", "type"}),
            "custom_properties": projection.custom_properties(modifier),
        }
        for modifier in obj.modifiers
    ]
    row["animation_data"] = animation_data_record(obj)
    if getattr(obj, "pose", None) is not None:
        row["pose_bones"] = [
            {
                "name": str(bone.name),
                "rna": r5.rna_record(bone, skip={"name", "constraints"}),
                "custom_properties": projection.custom_properties(bone),
                "constraints": constraint_rows(bone.constraints),
            }
            for bone in sorted(obj.pose.bones, key=lambda item: str(item.name))
        ]
    return row


def armature_data_record(data: Any) -> dict[str, Any]:
    row = r5.armature_data_record(data)
    row["custom_properties"] = projection.custom_properties(data)
    actual_bones = {str(bone.name): bone for bone in data.bones}
    for bone_row in row["bones"]:
        bone_row["custom_properties"] = projection.custom_properties(actual_bones[bone_row["name"]])
    actual_collections = {str(item.name): item for item in getattr(data, "collections", ())}
    for collection_row in row["collections"]:
        collection_row["custom_properties"] = projection.custom_properties(actual_collections[collection_row["name"]])
    row["animation_data"] = animation_data_record(data)
    return row


def armature_object_record(obj: Any) -> dict[str, Any]:
    row = r5.r4.armature_record(obj)
    row["object_semantics"] = object_record(obj)
    row["data_semantics"] = armature_data_record(obj.data)
    return row


def mesh_datablock_record(mesh: Any) -> dict[str, Any]:
    payload = {
        "r5_payload": r5.mesh_payload(mesh),
        "custom_properties": projection.custom_properties(mesh),
        "shape_key_custom_properties": (
            projection.custom_properties(mesh.shape_keys) if mesh.shape_keys is not None else {}
        ),
    }
    return {
        "name": str(mesh.name),
        "users": int(mesh.users),
        "object_users": sorted(str(obj.name) for obj in bpy.data.objects if obj.data == mesh),
        "semantic_sha256": hashlib.sha256(r5.r4.canonical_json(payload)).hexdigest(),
    }


def image_record(image: Any) -> dict[str, Any]:
    row = r5.image_record(image)
    row["custom_properties"] = projection.custom_properties(image)
    return row


def collection_record(collection: Any) -> dict[str, Any]:
    row = r5.collection_record(collection)
    row["custom_properties"] = projection.custom_properties(collection)
    return row


def scene_record(scene: Any) -> dict[str, Any]:
    row = r5.scene_record(scene)
    row["custom_properties"] = projection.custom_properties(scene)
    row["animation_data"] = animation_data_record(scene)
    return row


def world_record(world: Any) -> dict[str, Any]:
    row = r5.world_record(world)
    row["custom_properties"] = projection.custom_properties(world)
    row["node_tree"] = node_tree_record(world.node_tree) if world.node_tree else None
    row["animation_data"] = animation_data_record(world)
    return row


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--snapshot-sha256", required=True)
    parser.add_argument("--logical-artifact-sha256", required=True)
    parser.add_argument("--extractor-sha256", required=True)
    parser.add_argument("--intersection-helper-sha256", required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    snapshot = Path(args.snapshot).resolve()
    output = Path(args.output).resolve()
    extractor = Path(__file__).resolve()
    helper = TOOLS_ROOT / "blender_exact_mesh_intersections.py"
    if not snapshot.is_file() or r5.r4.sha256_file(snapshot) != args.snapshot_sha256:
        raise RuntimeError("immutable snapshot identity changed before extraction")
    if args.logical_artifact_sha256 != args.snapshot_sha256:
        raise RuntimeError("logical artifact and immutable snapshot digest disagree")
    if r5.r4.sha256_file(extractor) != args.extractor_sha256 or r5.r4.sha256_file(helper) != args.intersection_helper_sha256:
        raise RuntimeError("sealed extractor dependency changed")
    loaded = Path(bpy.data.filepath).resolve()
    if loaded != snapshot:
        raise RuntimeError("Blender did not load the exact immutable snapshot")
    if output.exists() or output.parent.resolve() == snapshot.parent.resolve():
        raise RuntimeError("output must be a fresh evaluator-owned external path")
    state = {
        "objects": [object_record(obj) for obj in sorted(bpy.data.objects, key=lambda item: str(item.name))],
        "mesh_objects": [
            {**r5.r4.mesh_object_record(obj), "object_semantics": object_record(obj)}
            for obj in sorted(bpy.data.objects, key=lambda item: str(item.name))
            if obj.type == "MESH"
        ],
        "armature_objects": [armature_object_record(obj) for obj in sorted(bpy.data.objects, key=lambda item: str(item.name)) if obj.type == "ARMATURE"],
        "mesh_datablocks": [mesh_datablock_record(item) for item in sorted(bpy.data.meshes, key=lambda x: str(x.name))],
        "armature_datablocks": [armature_data_record(item) for item in sorted(bpy.data.armatures, key=lambda x: str(x.name))],
        "materials": [material_record(item) for item in sorted(bpy.data.materials, key=lambda x: str(x.name))],
        "actions": action_rows(),
        "images": [image_record(item) for item in sorted(bpy.data.images, key=lambda x: str(x.name))],
        "node_groups": [node_tree_record(item) for item in sorted(bpy.data.node_groups, key=lambda x: str(x.name))],
        "collections": [collection_record(item) for item in sorted(bpy.data.collections, key=lambda x: str(x.name))],
        "worlds": [world_record(item) for item in sorted(bpy.data.worlds, key=lambda x: str(x.name))],
        "scenes": [scene_record(item) for item in sorted(bpy.data.scenes, key=lambda x: str(x.name))],
        "intersection_reports": r5.r4.intersection_records(),
    }
    payload = {
        "schema": SCHEMA,
        "nonce": args.nonce,
        "snapshot": {"path": str(snapshot), "bytes": int(snapshot.stat().st_size), "sha256": args.snapshot_sha256},
        "logical_artifact_sha256": args.logical_artifact_sha256,
        "extractor": {"path": str(extractor), "bytes": int(extractor.stat().st_size), "sha256": args.extractor_sha256},
        "intersection_helper": {"path": str(helper), "bytes": int(helper.stat().st_size), "sha256": args.intersection_helper_sha256},
        "blender": {"version": str(bpy.app.version_string), "background": bool(bpy.app.background), "loaded_filepath": str(loaded)},
        "state": state,
        "truth": {
            "read_only_extraction": True,
            "blend_saved": False,
            "snapshot_mutated": False,
            "in_memory_pose_evaluation_only": True,
        },
    }
    payload["state_sha256"] = hashlib.sha256(r5.r4.canonical_json(state)).hexdigest()
    encoded = r5.r4.canonical_json(payload)
    descriptor = os.open(str(output), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    if r5.r4.sha256_file(snapshot) != args.snapshot_sha256:
        raise RuntimeError("immutable snapshot identity changed during extraction")
    print("KIRA_R24_R6_READ_ONLY_EXTRACTION_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

