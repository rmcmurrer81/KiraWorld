from __future__ import annotations

"""Sealed read-only Blender extractor for the R24 R4 acceptance boundary.

This file is intended to be invoked by the R4 evaluator in a fresh background
Blender process after that evaluator has selected the exact candidate and a
private nonce/output path.  It never saves the Blend and exposes no authoring
operation.  The evaluator, not a caller-authored evidence document, consumes
the exhaustive state emitted here.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Iterable

import bpy
import bmesh


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from blender_exact_mesh_intersections import exact_nonadjacent_intersection_report


SCHEMA = "kira.avatar.r24.read_only_blender_extraction.v4"
BODY_OBJECT_NAME = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"
PATCH_MATERIAL_NAME = "R19_WarmTexture_Genitalia_Attempt06_BoundedSurfaceResponse"
PATCH_OBJECT_NAME = "Kira_R24_Intrinsic_EStar_Repaired_Patch"
INTERSECTION_ACTION_NAME = "KIRA_R19_ATTEMPT05_HANDS_PRESENT_Y_OUT_A"


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def floats(values: Iterable[Any]) -> list[float]:
    return [float(value) for value in values]


def matrix_rows(value: Any) -> list[list[float]]:
    return [floats(row) for row in value]


def json_value(value: Any) -> Any:
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    try:
        return [json_value(item) for item in value]
    except TypeError:
        return str(value)


def rna_scalar_properties(value: Any, *, skip: set[str] | None = None) -> dict[str, Any]:
    """Serialize non-collection RNA properties without executing operators.

    The acceptance extractor must not reduce a modifier or other stateful RNA
    record to its display name and type.  Only scalar/array properties are
    admitted here; pointer and collection properties are represented by an
    explicit ID name elsewhere or skipped instead of being stringified into an
    unstable memory address.
    """
    excluded = {"rna_type"} | (set() if skip is None else set(skip))
    rows: dict[str, Any] = {}
    for prop in value.bl_rna.properties:
        identifier = str(prop.identifier)
        if identifier in excluded or str(prop.type) in {"POINTER", "COLLECTION"}:
            continue
        try:
            raw = getattr(value, identifier)
            rows[identifier] = json_value(raw)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            rows[identifier] = "<UNREADABLE>"
    return {name: rows[name] for name in sorted(rows)}


def attribute_record(attribute: Any) -> dict[str, Any]:
    data: list[Any] = []
    for item in attribute.data:
        found = False
        for field in (
            "value",
            "vector",
            "color",
            "byte_color",
            "uv",
            "quaternion",
            "matrix",
        ):
            if hasattr(item, field):
                data.append(json_value(getattr(item, field)))
                found = True
                break
        if not found:
            data.append(rna_scalar_properties(item))
    return {
        "name": str(attribute.name),
        "domain": str(attribute.domain),
        "data_type": str(attribute.data_type),
        "data": data,
    }


def curve_rows(curves: Iterable[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for curve in sorted(curves, key=lambda item: (str(item.data_path), int(item.array_index))):
        rows.append(
            {
                "data_path": str(curve.data_path),
                "array_index": int(curve.array_index),
                "extrapolation": str(getattr(curve, "extrapolation", "")),
                "keyframes": [
                    {
                        "co": [float(point.co.x), float(point.co.y)],
                        "handle_left": [float(point.handle_left.x), float(point.handle_left.y)],
                        "handle_right": [float(point.handle_right.x), float(point.handle_right.y)],
                        "handle_left_type": str(getattr(point, "handle_left_type", "")),
                        "handle_right_type": str(getattr(point, "handle_right_type", "")),
                        "interpolation": str(point.interpolation),
                        "easing": str(getattr(point, "easing", "")),
                    }
                    for point in curve.keyframe_points
                ],
            }
        )
    return rows


def action_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for action in sorted(bpy.data.actions, key=lambda value: str(value.name)):
        row: dict[str, Any] = {
            "name": str(action.name),
            "frame_range": floats(action.frame_range),
            "use_fake_user": bool(getattr(action, "use_fake_user", False)),
        }
        if hasattr(action, "fcurves"):
            row["storage"] = "legacy"
            row["fcurves"] = curve_rows(action.fcurves)
        else:
            row["storage"] = "layered"
            row["slots"] = [
                {
                    "handle": int(slot.handle),
                    "identifier": str(slot.identifier),
                    "target_id_type": str(slot.target_id_type),
                }
                for slot in sorted(getattr(action, "slots", ()), key=lambda value: int(value.handle))
            ]
            row["layers"] = []
            for layer in getattr(action, "layers", ()):
                layer_row = {"name": str(layer.name), "strips": []}
                for strip in getattr(layer, "strips", ()):
                    strip_row = {
                        "type": str(getattr(strip, "type", type(strip).__name__)),
                        "channelbags": [],
                    }
                    for bag in sorted(
                        getattr(strip, "channelbags", ()),
                        key=lambda value: int(value.slot_handle),
                    ):
                        strip_row["channelbags"].append(
                            {
                                "slot_handle": int(bag.slot_handle),
                                "fcurves": curve_rows(getattr(bag, "fcurves", ())),
                            }
                        )
                    layer_row["strips"].append(strip_row)
                row["layers"].append(layer_row)
        rows.append(row)
    return rows


def material_record(material: Any) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    links: list[list[str]] = []
    if bool(material.use_nodes) and material.node_tree is not None:
        for node in sorted(material.node_tree.nodes, key=lambda item: str(item.name)):
            inputs = []
            for socket in node.inputs:
                if hasattr(socket, "default_value"):
                    inputs.append([str(socket.name), json_value(socket.default_value)])
            node_row: dict[str, Any] = {
                "name": str(node.name),
                "type": str(node.bl_idname),
                "label": str(node.label),
                "inputs": inputs,
            }
            image = getattr(node, "image", None)
            if image is not None:
                packed = getattr(image, "packed_file", None)
                node_row["image"] = {
                    "name": str(image.name),
                    "filepath": str(image.filepath),
                    "packed_bytes": int(len(packed.data)) if packed is not None else 0,
                }
            nodes.append(node_row)
        links = sorted(
            [
                [
                    str(link.from_node.name),
                    str(link.from_socket.name),
                    str(link.to_node.name),
                    str(link.to_socket.name),
                ]
                for link in material.node_tree.links
            ]
        )
    return {
        "name": str(material.name),
        "use_nodes": bool(material.use_nodes),
        "surface_render_method": str(getattr(material, "surface_render_method", "")),
        "nodes": nodes,
        "links": links,
    }


def mesh_object_record(obj: Any) -> dict[str, Any]:
    mesh = obj.data
    group_names = {int(group.index): str(group.name) for group in obj.vertex_groups}
    vertices = [
        {
            "index": int(vertex.index),
            "coordinate_local_m": floats(vertex.co),
            "normal_local": floats(vertex.normal),
            "groups": sorted(
                [
                    {"name": group_names[int(item.group)], "weight": float(item.weight)}
                    for item in vertex.groups
                    if int(item.group) in group_names and float(item.weight) > 0.0
                ],
                key=lambda item: item["name"],
            ),
        }
        for vertex in mesh.vertices
    ]
    edges = [
        {
            "index": int(edge.index),
            "vertices": [int(value) for value in edge.vertices],
            "use_seam": bool(getattr(edge, "use_seam", False)),
            "use_edge_sharp": bool(getattr(edge, "use_edge_sharp", False)),
        }
        for edge in mesh.edges
    ]
    polygons = [
        {
            "index": int(poly.index),
            "vertices": [int(value) for value in poly.vertices],
            "loop_indices": [int(value) for value in poly.loop_indices],
            "material_index": int(poly.material_index),
            "use_smooth": bool(poly.use_smooth),
        }
        for poly in mesh.polygons
    ]
    loops = [
        {"index": int(loop.index), "vertex_index": int(loop.vertex_index)}
        for loop in mesh.loops
    ]
    uv_layers = []
    for layer in mesh.uv_layers:
        uv_layers.append(
            {
                "name": str(layer.name),
                "active": bool(layer == mesh.uv_layers.active),
                "active_render": bool(layer.active_render),
                "data": [
                    {"loop_index": index, "uv": floats(item.uv)}
                    for index, item in enumerate(layer.data)
                ],
            }
        )
    shape_keys = []
    if mesh.shape_keys is not None:
        shape_keys = [
            {
                "name": str(block.name),
                "relative_key": str(block.relative_key.name) if block.relative_key else None,
                "coordinates_local_m": [floats(item.co) for item in block.data],
            }
            for block in mesh.shape_keys.key_blocks
        ]
    mesh.calc_loop_triangles()
    loop_triangles = [
        {
            "index": int(triangle.index),
            "polygon_index": int(triangle.polygon_index),
            "vertices": [int(value) for value in triangle.vertices],
            "loops": [int(value) for value in triangle.loops],
            "material_index": int(mesh.polygons[triangle.polygon_index].material_index),
        }
        for triangle in mesh.loop_triangles
    ]
    modifiers = [
        {
            "name": str(modifier.name),
            "type": str(modifier.type),
            "object": str(modifier.object.name) if getattr(modifier, "object", None) else None,
            "properties": rna_scalar_properties(
                modifier,
                skip={"name", "type", "object"},
            ),
        }
        for modifier in obj.modifiers
    ]
    return {
        "object_name": str(obj.name),
        "mesh_name": str(mesh.name),
        "parent_name": str(obj.parent.name) if obj.parent else None,
        "matrix_world": matrix_rows(obj.matrix_world),
        "modifiers": modifiers,
        "materials": [str(item.name) if item is not None else None for item in mesh.materials],
        "vertices": vertices,
        "edges": edges,
        "polygons": polygons,
        "loops": loops,
        "uv_layers": uv_layers,
        "attributes": [
            attribute_record(attribute)
            for attribute in sorted(mesh.attributes, key=lambda item: str(item.name))
        ],
        "shape_keys": shape_keys,
        "loop_triangles": loop_triangles,
    }


def patch_material_index(obj: Any) -> int:
    matches = [
        index
        for index, material in enumerate(obj.data.materials)
        if material is not None and str(material.name) == PATCH_MATERIAL_NAME
    ]
    if len(matches) != 1:
        raise RuntimeError("body does not contain one exact protected patch-material slot")
    return int(matches[0])


def intersection_report_for_mesh(obj: Any, mesh: Any, *, patch_only: bool) -> dict[str, Any]:
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.faces.ensure_lookup_table()
        if patch_only:
            required_slot = patch_material_index(obj)
            remove = [face for face in bm.faces if int(face.material_index) != required_slot]
            if remove:
                bmesh.ops.delete(bm, geom=remove, context="FACES")
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            for index, face in enumerate(bm.faces):
                face.index = index
        bm.transform(obj.matrix_world)
        return exact_nonadjacent_intersection_report(bm, include_pair_details=True)
    finally:
        bm.free()


def annotate_patch_pairs(report: dict[str, Any], mesh: Any, patch_slot: int) -> dict[str, Any]:
    patch_pairs: list[dict[str, Any]] = []
    nonpatch_pairs: list[dict[str, Any]] = []
    for row in report.get("pairs", []):
        if not bool(row.get("genuine_positive_area_or_segment_penetration")):
            continue
        face_indices = row.get("face_indices", [])
        if (
            not isinstance(face_indices, list)
            or len(face_indices) != 2
            or any(
                not isinstance(index, int)
                or isinstance(index, bool)
                or index < 0
                or index >= len(mesh.polygons)
                for index in face_indices
            )
        ):
            raise RuntimeError("intersection report contains an invalid face reference")
        target = (
            patch_pairs
            if any(int(mesh.polygons[index].material_index) == patch_slot for index in face_indices)
            else nonpatch_pairs
        )
        target.append(row)
    return {
        "report": report,
        "patch_related_genuine_pairs": patch_pairs,
        "nonpatch_genuine_pairs": nonpatch_pairs,
    }


def intersection_records() -> dict[str, Any]:
    body = bpy.data.objects.get(BODY_OBJECT_NAME)
    rig = bpy.data.objects.get("Kira_R19_BlackProject_Native_188_Rig")
    action = bpy.data.actions.get(INTERSECTION_ACTION_NAME)
    if body is None or body.type != "MESH" or rig is None or rig.type != "ARMATURE" or action is None:
        raise RuntimeError("required body, rig, or intersection action is absent")
    patch_slot = patch_material_index(body)
    neutral_full = intersection_report_for_mesh(body, body.data, patch_only=False)
    private_patch = bpy.data.objects.get(PATCH_OBJECT_NAME)
    if private_patch is not None and private_patch.type != "MESH":
        raise RuntimeError("sealed private patch object has the wrong type")
    standalone_object = private_patch if private_patch is not None else body
    standalone_patch = intersection_report_for_mesh(
        standalone_object,
        standalone_object.data,
        patch_only=private_patch is None,
    )
    standalone_patch["extracted_object_name"] = str(standalone_object.name)
    standalone_patch["scope"] = (
        "complete_private_patch_object"
        if private_patch is not None
        else "source_body_patch_material_region"
    )

    scene = bpy.context.scene
    prior_frame = int(scene.frame_current)
    animation = rig.animation_data_create()
    prior_action = getattr(animation, "action", None)
    frame = int(round(float(action.frame_range[0])))
    try:
        animation.action = action
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = body.evaluated_get(depsgraph)
        evaluated_mesh = evaluated.to_mesh(
            preserve_all_data_layers=True,
            depsgraph=depsgraph,
        )
        try:
            posed_full = intersection_report_for_mesh(body, evaluated_mesh, patch_only=False)
            posed = annotate_patch_pairs(posed_full, evaluated_mesh, patch_slot)
        finally:
            evaluated.to_mesh_clear()
    finally:
        animation.action = prior_action
        scene.frame_set(prior_frame)
        bpy.context.view_layer.update()
    return {
        "algorithm": "sealed_blender_exact_mesh_intersections",
        "neutral_full": neutral_full,
        "standalone_patch": standalone_patch,
        "required_pose": {
            "action": INTERSECTION_ACTION_NAME,
            "frame": frame,
            **posed,
        },
    }


def armature_record(obj: Any) -> dict[str, Any]:
    return {
        "object_name": str(obj.name),
        "armature_name": str(obj.data.name),
        "parent_name": str(obj.parent.name) if obj.parent else None,
        "matrix_world": matrix_rows(obj.matrix_world),
        "bones": [
            {
                "name": str(bone.name),
                "parent": str(bone.parent.name) if bone.parent else None,
                "head_local": floats(bone.head_local),
                "tail_local": floats(bone.tail_local),
                "matrix_local": matrix_rows(bone.matrix_local),
                "use_deform": bool(bone.use_deform),
            }
            for bone in sorted(obj.data.bones, key=lambda item: str(item.name))
        ],
    }


def object_links() -> list[dict[str, Any]]:
    return [
        {
            "name": str(obj.name),
            "type": str(obj.type),
            "data_name": str(obj.data.name) if obj.data is not None else None,
            "parent_name": str(obj.parent.name) if obj.parent else None,
            "collection_names": sorted(str(item.name) for item in obj.users_collection),
            "hide_viewport": bool(obj.hide_viewport),
            "hide_render": bool(obj.hide_render),
        }
        for obj in sorted(bpy.data.objects, key=lambda item: str(item.name))
    ]


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
    intersection_helper = TOOLS_ROOT / "blender_exact_mesh_intersections.py"
    if not candidate.is_file() or sha256_file(candidate) != args.candidate_sha256:
        raise RuntimeError("candidate identity changed before extraction")
    if sha256_file(extractor) != args.extractor_sha256:
        raise RuntimeError("extractor identity changed")
    if sha256_file(intersection_helper) != args.intersection_helper_sha256:
        raise RuntimeError("intersection helper identity changed")
    loaded = Path(bpy.data.filepath).resolve()
    if loaded != candidate:
        raise RuntimeError("Blender did not load the exact requested candidate")
    if output.exists() or output.parent.resolve() == candidate.parent.resolve():
        raise RuntimeError("output must be a fresh evaluator-owned external path")
    payload = {
        "schema": SCHEMA,
        "nonce": args.nonce,
        "candidate": {
            "path": str(candidate),
            "bytes": int(candidate.stat().st_size),
            "sha256": args.candidate_sha256,
        },
        "extractor": {
            "path": str(extractor),
            "bytes": int(extractor.stat().st_size),
            "sha256": args.extractor_sha256,
        },
        "intersection_helper": {
            "path": str(intersection_helper),
            "bytes": int(intersection_helper.stat().st_size),
            "sha256": args.intersection_helper_sha256,
        },
        "blender": {
            "version": str(bpy.app.version_string),
            "background": bool(bpy.app.background),
            "loaded_filepath": str(loaded),
        },
        "state": {
            "objects": object_links(),
            "mesh_objects": [
                mesh_object_record(obj)
                for obj in sorted(bpy.data.objects, key=lambda item: str(item.name))
                if obj.type == "MESH"
            ],
            "armature_objects": [
                armature_record(obj)
                for obj in sorted(bpy.data.objects, key=lambda item: str(item.name))
                if obj.type == "ARMATURE"
            ],
            "materials": [material_record(item) for item in sorted(bpy.data.materials, key=lambda x: str(x.name))],
            "actions": action_rows(),
            "intersection_reports": intersection_records(),
            "scenes": [
                {
                    "name": str(scene.name),
                    "object_names": sorted(str(obj.name) for obj in scene.objects),
                    "camera": str(scene.camera.name) if scene.camera else None,
                }
                for scene in sorted(bpy.data.scenes, key=lambda item: str(item.name))
            ],
        },
        "truth": {
            "read_only_extraction": True,
            "blend_saved": False,
            "candidate_mutated": False,
            "in_memory_pose_evaluation_only": True,
        },
    }
    payload["state_sha256"] = hashlib.sha256(canonical_json(payload["state"])).hexdigest()
    encoded = canonical_json(payload)
    descriptor = os.open(str(output), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    if sha256_file(candidate) != args.candidate_sha256:
        raise RuntimeError("candidate identity changed during extraction")
    print("KIRA_R24_R4_READ_ONLY_EXTRACTION_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
