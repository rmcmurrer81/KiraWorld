#!/usr/bin/env python3
"""Read-only material diagnosis for the sealed Kira R19 attempt-04 Blend."""

from __future__ import annotations

import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parent.parent
EXPECTED = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r19_bald_owner_review/"
    "attempt_04/kira_r19_bald_low_resource_private_owner_review.blend"
)
BODY_NAME = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"


def canonical(name: str) -> str:
    stem, dot, suffix = name.rpartition(".")
    return stem if dot and suffix.isdigit() else name


def socket_record(socket):
    return {
        "name": socket.name,
        "default_value": list(socket.default_value)
        if hasattr(socket.default_value, "__len__") and not isinstance(socket.default_value, str)
        else socket.default_value,
        "links": [
            {
                "from_node": link.from_node.name,
                "from_socket": link.from_socket.name,
            }
            for link in socket.links
        ],
    }


def material_record(material):
    nodes = material.node_tree.nodes
    principal = next(node for node in nodes if node.bl_idname == "ShaderNodeBsdfPrincipled")
    wanted = ("Base Color", "Roughness", "Specular IOR Level", "IOR", "Coat Weight")
    return {
        "name": material.name,
        "principled": {
            name: socket_record(principal.inputs[name])
            for name in wanted
            if principal.inputs.get(name) is not None
        },
        "named_adjustment_nodes": [
            {
                "name": node.name,
                "type": node.bl_idname,
                "blend_type": getattr(node, "blend_type", None),
            }
            for node in nodes
            if "R19" in node.name or "KIRA" in node.name
        ],
        "image_nodes": [
            {
                "node": node.name,
                "image": node.image.name if node.image else None,
                "size": list(node.image.size) if node.image else None,
                "colorspace": node.image.colorspace_settings.name if node.image else None,
            }
            for node in nodes
            if node.bl_idname == "ShaderNodeTexImage"
        ],
    }


if Path(bpy.data.filepath).resolve() != EXPECTED.resolve():
    raise RuntimeError("diagnostic must open the exact sealed attempt-04 Blend")

body = bpy.data.objects[BODY_NAME]
skin_materials = [material for material in body.data.materials if material is not None]
iris = next(
    obj
    for obj in bpy.data.objects
    if obj.type == "MESH" and canonical(obj.data.name) == "Ariel_Mesh_Irises_0"
)
iris_material = iris.material_slots[0].material
iris_record = material_record(iris_material)

colorizer = iris_material.node_tree.nodes.get("KIRA_R19_WARM_BROWN_IRIS_TEXTURE_COLORIZE")
if colorizer is None:
    raise RuntimeError("attempt-04 iris colorizer missing")
source_links = list(colorizer.inputs[1].links)
if len(source_links) != 1:
    raise RuntimeError("attempt-04 iris colorizer has no unique source feed")
source_node = source_links[0].from_node
source_image = getattr(source_node, "image", None)
source_image_record = None
if source_image is not None:
    # Do not force a full packed-image pixel decode during this read-only
    # graph diagnosis.  The rendered macro is the controlling color evidence.
    source_image_record = {
        "image": source_image.name,
        "size": [int(value) for value in source_image.size],
        "colorspace": source_image.colorspace_settings.name,
        "packed": source_image.packed_file is not None,
    }

print(
    "KIRA_R19_ATTEMPT04_MATERIAL_DIAGNOSIS="
    + json.dumps(
        {
            "iris": iris_record,
            "iris_colorizer": {
                "blend_type": colorizer.blend_type,
                "factor": float(colorizer.inputs[0].default_value),
                "color1_source": source_node.name,
                "color2_linear_rgba": [float(value) for value in colorizer.inputs[2].default_value],
                "source_image": source_image_record,
            },
            "skin": [material_record(material) for material in skin_materials],
        },
        sort_keys=True,
    )
)
