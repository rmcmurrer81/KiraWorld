from __future__ import annotations

"""Sealed read-only Blender extractor for the append-only R24 R5 gate.

R5 expands R4's projection to include unlinked Mesh/Armature datablocks and
the behavior-relevant child graphs of objects, rigs, Actions, materials,
images, collections, worlds, view layers, and scenes.  It never saves.
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Iterable

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import blender_extract_kira_r24_candidate_read_only_r4 as r4


SCHEMA = "kira.avatar.r24.read_only_blender_extraction.v5"


def _value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else f"<{value}>"
    if hasattr(value, "bl_rna"):
        if hasattr(value, "name"):
            return {
                "rna": str(value.bl_rna.identifier),
                "name": str(value.name),
                "library": str(value.library.filepath) if getattr(value, "library", None) else None,
            }
        # Non-ID pointer structs must never fall through to repr(), whose
        # memory address would make two equivalent fresh processes unequal.
        scalars: dict[str, Any] = {}
        for prop in value.bl_rna.properties:
            if str(prop.identifier) == "rna_type" or str(prop.type) in {"POINTER", "COLLECTION"}:
                continue
            try:
                scalars[str(prop.identifier)] = _value(getattr(value, str(prop.identifier)))
            except (AttributeError, RuntimeError, TypeError, ValueError):
                scalars[str(prop.identifier)] = "<UNREADABLE>"
        return {"rna": str(value.bl_rna.identifier), "scalars": {key: scalars[key] for key in sorted(scalars)}}
    try:
        return [_value(item) for item in value]
    except TypeError:
        return str(value)


def rna_record(value: Any, *, skip: set[str] | None = None) -> dict[str, Any]:
    excluded = {"rna_type"} | (set() if skip is None else set(skip))
    rows: dict[str, Any] = {}
    for prop in value.bl_rna.properties:
        name = str(prop.identifier)
        if name in excluded or str(prop.type) == "COLLECTION":
            continue
        try:
            rows[name] = _value(getattr(value, name))
        except (AttributeError, RuntimeError, TypeError, ValueError):
            rows[name] = "<UNREADABLE>"
    return {name: rows[name] for name in sorted(rows)}


def constraint_rows(values: Iterable[Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": str(item.name),
            "type": str(item.type),
            "rna": rna_record(item, skip={"name", "type"}),
        }
        for item in values
    ]


def driver_or_curve_record(curve: Any) -> dict[str, Any]:
    group = getattr(curve, "group", None)
    driver = getattr(curve, "driver", None)
    return {
        "data_path": str(curve.data_path),
        "array_index": int(curve.array_index),
        "group": str(group.name) if group else None,
        "rna": rna_record(
            curve,
            skip={"data_path", "array_index", "group", "keyframe_points", "sampled_points", "modifiers", "driver"},
        ),
        "keyframes": [rna_record(point) for point in curve.keyframe_points],
        "sampled_points": [rna_record(point) for point in getattr(curve, "sampled_points", ())],
        "modifiers": [
            {
                "type": str(modifier.type),
                "rna": rna_record(modifier, skip={"type"}),
            }
            for modifier in curve.modifiers
        ],
        "driver": (
            {
                "rna": rna_record(driver, skip={"variables"}),
                "variables": [
                    {
                        "name": str(variable.name),
                        "type": str(variable.type),
                        "rna": rna_record(variable, skip={"name", "type", "targets"}),
                        "targets": [rna_record(target) for target in variable.targets],
                    }
                    for variable in driver.variables
                ],
            }
            if driver is not None
            else None
        ),
    }


def animation_data_record(value: Any) -> dict[str, Any] | None:
    animation = getattr(value, "animation_data", None)
    if animation is None:
        return None
    return {
        "rna": rna_record(animation, skip={"drivers", "nla_tracks"}),
        "drivers": [driver_or_curve_record(curve) for curve in animation.drivers],
        "nla_tracks": [
            {
                "name": str(track.name),
                "rna": rna_record(track, skip={"name", "strips"}),
                "strips": [rna_record(strip, skip={"fcurves", "modifiers"}) for strip in track.strips],
            }
            for track in animation.nla_tracks
        ],
    }


def action_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for action in sorted(bpy.data.actions, key=lambda item: str(item.name)):
        row: dict[str, Any] = {
            "name": str(action.name),
            "rna": rna_record(action, skip={"name", "fcurves", "groups", "slots", "layers"}),
            "groups": [rna_record(group, skip={"channels"}) for group in getattr(action, "groups", ())],
        }
        if hasattr(action, "fcurves"):
            row["storage"] = "legacy"
            row["fcurves"] = [
                driver_or_curve_record(curve)
                for curve in sorted(action.fcurves, key=lambda item: (str(item.data_path), int(item.array_index)))
            ]
        else:
            row["storage"] = "layered"
            row["slots"] = [rna_record(slot) for slot in getattr(action, "slots", ())]
            layers = []
            for layer in getattr(action, "layers", ()):
                strips = []
                for strip in getattr(layer, "strips", ()):
                    bags = []
                    for bag in getattr(strip, "channelbags", ()):
                        bags.append(
                            {
                                "slot_handle": int(bag.slot_handle),
                                "rna": rna_record(bag, skip={"fcurves"}),
                                "fcurves": [driver_or_curve_record(curve) for curve in bag.fcurves],
                            }
                        )
                    strips.append({"rna": rna_record(strip, skip={"channelbags"}), "channelbags": bags})
                layers.append({"rna": rna_record(layer, skip={"strips"}), "strips": strips})
            row["layers"] = layers
        rows.append(row)
    return rows


def socket_rows(values: Iterable[Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": str(socket.name),
            "identifier": str(getattr(socket, "identifier", "")),
            "type": str(socket.bl_idname),
            "rna": rna_record(socket, skip={"name", "identifier"}),
        }
        for socket in values
    ]


def node_tree_record(tree: Any) -> dict[str, Any]:
    return {
        "name": str(tree.name),
        "type": str(tree.bl_idname),
        "rna": rna_record(tree, skip={"name", "nodes", "links", "interface"}),
        "nodes": [
            {
                "name": str(node.name),
                "type": str(node.bl_idname),
                "rna": rna_record(node, skip={"name", "inputs", "outputs", "internal_links"}),
                "inputs": socket_rows(node.inputs),
                "outputs": socket_rows(node.outputs),
                "internal_links": sorted(
                    [
                        [
                            str(link.from_socket.identifier),
                            str(link.to_socket.identifier),
                        ]
                        for link in getattr(node, "internal_links", ())
                    ]
                ),
            }
            for node in sorted(tree.nodes, key=lambda item: str(item.name))
        ],
        "links": sorted(
            [
                [
                    str(link.from_node.name),
                    str(link.from_socket.identifier),
                    str(link.to_node.name),
                    str(link.to_socket.identifier),
                    rna_record(link),
                ]
                for link in tree.links
            ],
            key=lambda row: (row[0], row[1], row[2], row[3]),
        ),
        "interface": (
            [rna_record(item) for item in tree.interface.items_tree]
            if getattr(tree, "interface", None) is not None
            else []
        ),
    }


def image_record(image: Any) -> dict[str, Any]:
    packed = getattr(image, "packed_file", None)
    packed_bytes = bytes(packed.data) if packed is not None else b""
    absolute = Path(bpy.path.abspath(str(image.filepath))).resolve() if str(image.filepath) else None
    external = None
    if packed is None and absolute is not None and absolute.is_file():
        external = {
            "path": str(absolute),
            "bytes": int(absolute.stat().st_size),
            "sha256": r4.sha256_file(absolute),
        }
    return {
        "name": str(image.name),
        "rna": rna_record(image, skip={"name", "pixels", "packed_file"}),
        "packed_bytes": len(packed_bytes),
        "packed_sha256": hashlib.sha256(packed_bytes).hexdigest() if packed is not None else None,
        "external_file": external,
    }


def material_record(material: Any) -> dict[str, Any]:
    return {
        "name": str(material.name),
        "users": int(material.users),
        "rna": rna_record(material, skip={"name", "users", "node_tree"}),
        "animation_data": animation_data_record(material),
        "node_tree": node_tree_record(material.node_tree) if material.node_tree else None,
    }


def object_record(obj: Any) -> dict[str, Any]:
    pose_bones = []
    if getattr(obj, "pose", None) is not None:
        pose_bones = [
            {
                "name": str(bone.name),
                "rna": rna_record(bone, skip={"name", "constraints"}),
                "constraints": constraint_rows(bone.constraints),
            }
            for bone in sorted(obj.pose.bones, key=lambda item: str(item.name))
        ]
    return {
        "name": str(obj.name),
        "type": str(obj.type),
        "data_name": str(obj.data.name) if obj.data is not None else None,
        "parent_name": str(obj.parent.name) if obj.parent else None,
        "collection_names": sorted(str(item.name) for item in obj.users_collection),
        "hide_viewport": bool(obj.hide_viewport),
        "hide_render": bool(obj.hide_render),
        "rna": rna_record(
            obj,
            skip={"name", "type", "data", "parent", "users_collection", "constraints", "modifiers", "vertex_groups", "pose"},
        ),
        "constraints": constraint_rows(obj.constraints),
        "modifiers": [
            {
                "name": str(modifier.name),
                "type": str(modifier.type),
                "rna": rna_record(modifier, skip={"name", "type"}),
            }
            for modifier in obj.modifiers
        ],
        "vertex_groups": [
            {
                "name": str(group.name),
                "index": int(group.index),
                "rna": rna_record(group, skip={"name", "index"}),
            }
            for group in obj.vertex_groups
        ],
        "animation_data": animation_data_record(obj),
        "pose_bones": pose_bones,
    }


def armature_data_record(data: Any) -> dict[str, Any]:
    return {
        "name": str(data.name),
        "rna": rna_record(data, skip={"name", "bones", "collections"}),
        "bones": [
            {
                "name": str(bone.name),
                "rna": rna_record(bone, skip={"name", "parent", "children", "collections"}),
                "parent": str(bone.parent.name) if bone.parent else None,
                "collections": sorted(str(item.name) for item in getattr(bone, "collections", ())),
            }
            for bone in sorted(data.bones, key=lambda item: str(item.name))
        ],
        "collections": [
            {
                "name": str(collection.name),
                "rna": rna_record(collection, skip={"name", "bones", "children"}),
                "bones": sorted(str(bone.name) for bone in collection.bones),
                "children": sorted(str(child.name) for child in collection.children),
            }
            for collection in sorted(getattr(data, "collections", ()), key=lambda item: str(item.name))
        ],
        "animation_data": animation_data_record(data),
    }


def armature_object_record(obj: Any) -> dict[str, Any]:
    row = r4.armature_record(obj)
    row["object_semantics"] = object_record(obj)
    row["data_semantics"] = armature_data_record(obj.data)
    return row


def mesh_payload(mesh: Any) -> dict[str, Any]:
    return {
        "rna": rna_record(
            mesh,
            skip={"name", "vertices", "edges", "loops", "polygons", "uv_layers", "attributes", "shape_keys", "materials"},
        ),
        "vertices": [rna_record(item) for item in mesh.vertices],
        "edges": [rna_record(item) for item in mesh.edges],
        "loops": [rna_record(item) for item in mesh.loops],
        "polygons": [rna_record(item) for item in mesh.polygons],
        "uv_layers": [
            {
                "name": str(layer.name),
                "rna": rna_record(layer, skip={"name", "data"}),
                "data": [rna_record(item) for item in layer.data],
            }
            for layer in mesh.uv_layers
        ],
        "attributes": [r4.attribute_record(item) for item in sorted(mesh.attributes, key=lambda x: str(x.name))],
        "materials": [str(item.name) if item else None for item in mesh.materials],
        "shape_keys": (
            {
                "rna": rna_record(mesh.shape_keys, skip={"key_blocks"}),
                "blocks": [
                    {
                        "name": str(block.name),
                        "rna": rna_record(block, skip={"name", "data", "relative_key"}),
                        "relative_key": str(block.relative_key.name) if block.relative_key else None,
                        "data": [rna_record(item) for item in block.data],
                    }
                    for block in mesh.shape_keys.key_blocks
                ],
            }
            if mesh.shape_keys is not None
            else None
        ),
    }


def mesh_datablock_record(mesh: Any) -> dict[str, Any]:
    payload = mesh_payload(mesh)
    return {
        "name": str(mesh.name),
        "users": int(mesh.users),
        "object_users": sorted(str(obj.name) for obj in bpy.data.objects if obj.data == mesh),
        "semantic_sha256": hashlib.sha256(r4.canonical_json(payload)).hexdigest(),
    }


def collection_record(collection: Any) -> dict[str, Any]:
    return {
        "name": str(collection.name),
        "rna": rna_record(collection, skip={"name", "objects", "children"}),
        "objects": sorted(str(item.name) for item in collection.objects),
        "children": sorted(str(item.name) for item in collection.children),
    }


def layer_collection_record(layer: Any) -> dict[str, Any]:
    return {
        "name": str(layer.name),
        "collection": str(layer.collection.name),
        "rna": rna_record(layer, skip={"name", "collection", "children"}),
        "children": [layer_collection_record(child) for child in layer.children],
    }


def scene_record(scene: Any) -> dict[str, Any]:
    nested_names = (
        "render",
        "view_settings",
        "display_settings",
        "sequencer_colorspace_settings",
        "unit_settings",
        "tool_settings",
    )
    nested = {
        name: rna_record(getattr(scene, name))
        for name in nested_names
        if getattr(scene, name, None) is not None
    }
    if getattr(scene.render, "image_settings", None) is not None:
        nested["render_image_settings"] = rna_record(scene.render.image_settings)
    if getattr(scene.render, "ffmpeg", None) is not None:
        nested["render_ffmpeg"] = rna_record(scene.render.ffmpeg)
    return {
        "name": str(scene.name),
        "rna": rna_record(scene, skip={"name", "objects", "view_layers", *nested_names}),
        "object_names": sorted(str(obj.name) for obj in scene.objects),
        "camera": str(scene.camera.name) if scene.camera else None,
        "nested": nested,
        "view_layers": [
            {
                "name": str(layer.name),
                "rna": rna_record(layer, skip={"name", "objects", "layer_collection"}),
                "layer_collection": layer_collection_record(layer.layer_collection),
            }
            for layer in scene.view_layers
        ],
        "animation_data": animation_data_record(scene),
    }


def world_record(world: Any) -> dict[str, Any]:
    return {
        "name": str(world.name),
        "rna": rna_record(world, skip={"name", "node_tree"}),
        "node_tree": node_tree_record(world.node_tree) if world.node_tree else None,
        "animation_data": animation_data_record(world),
    }


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--extractor-sha256", required=True)
    parser.add_argument("--intersection-helper-sha256", required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    candidate = Path(args.candidate).resolve()
    output = Path(args.output).resolve()
    extractor = Path(__file__).resolve()
    helper = TOOLS_ROOT / "blender_exact_mesh_intersections.py"
    if not candidate.is_file() or r4.sha256_file(candidate) != args.candidate_sha256:
        raise RuntimeError("candidate identity changed before extraction")
    if r4.sha256_file(extractor) != args.extractor_sha256 or r4.sha256_file(helper) != args.intersection_helper_sha256:
        raise RuntimeError("sealed extractor dependency changed")
    loaded = Path(bpy.data.filepath).resolve()
    if loaded != candidate:
        raise RuntimeError("Blender did not load the exact requested candidate")
    if output.exists() or output.parent.resolve() == candidate.parent.resolve():
        raise RuntimeError("output must be a fresh evaluator-owned external path")
    state = {
        "objects": [object_record(obj) for obj in sorted(bpy.data.objects, key=lambda item: str(item.name))],
        "mesh_objects": [
            {**r4.mesh_object_record(obj), "object_semantics": object_record(obj)}
            for obj in sorted(bpy.data.objects, key=lambda item: str(item.name))
            if obj.type == "MESH"
        ],
        "armature_objects": [
            armature_object_record(obj)
            for obj in sorted(bpy.data.objects, key=lambda item: str(item.name))
            if obj.type == "ARMATURE"
        ],
        "mesh_datablocks": [mesh_datablock_record(item) for item in sorted(bpy.data.meshes, key=lambda x: str(x.name))],
        "armature_datablocks": [armature_data_record(item) for item in sorted(bpy.data.armatures, key=lambda x: str(x.name))],
        "materials": [material_record(item) for item in sorted(bpy.data.materials, key=lambda x: str(x.name))],
        "actions": action_rows(),
        "images": [image_record(item) for item in sorted(bpy.data.images, key=lambda x: str(x.name))],
        "node_groups": [node_tree_record(item) for item in sorted(bpy.data.node_groups, key=lambda x: str(x.name))],
        "collections": [collection_record(item) for item in sorted(bpy.data.collections, key=lambda x: str(x.name))],
        "worlds": [world_record(item) for item in sorted(bpy.data.worlds, key=lambda x: str(x.name))],
        "scenes": [scene_record(item) for item in sorted(bpy.data.scenes, key=lambda x: str(x.name))],
        "intersection_reports": r4.intersection_records(),
    }
    payload = {
        "schema": SCHEMA,
        "nonce": args.nonce,
        "candidate": {
            "path": str(candidate),
            "bytes": int(candidate.stat().st_size),
            "sha256": args.candidate_sha256,
        },
        "extractor": {"path": str(extractor), "bytes": int(extractor.stat().st_size), "sha256": args.extractor_sha256},
        "intersection_helper": {"path": str(helper), "bytes": int(helper.stat().st_size), "sha256": args.intersection_helper_sha256},
        "blender": {"version": str(bpy.app.version_string), "background": bool(bpy.app.background), "loaded_filepath": str(loaded)},
        "state": state,
        "truth": {
            "read_only_extraction": True,
            "blend_saved": False,
            "candidate_mutated": False,
            "in_memory_pose_evaluation_only": True,
        },
    }
    payload["state_sha256"] = hashlib.sha256(r4.canonical_json(state)).hexdigest()
    encoded = r4.canonical_json(payload)
    descriptor = os.open(str(output), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    if r4.sha256_file(candidate) != args.candidate_sha256:
        raise RuntimeError("candidate identity changed during extraction")
    print("KIRA_R24_R5_READ_ONLY_EXTRACTION_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
