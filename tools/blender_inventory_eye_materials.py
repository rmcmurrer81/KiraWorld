"""Inventory eye-like objects, materials, and embedded images in one model.

Read-only Blender diagnostic.  The model is imported into a factory-startup
scene and a JSON inventory is printed to stdout.  No blend/model/image is
saved, exported, or changed on disk.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy  # type: ignore


def main() -> None:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(values) != 1:
        raise SystemExit("usage: blender ... --python script.py -- MODEL")
    source = Path(values[0]).resolve()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(source))

    objects = []
    for obj in bpy.data.objects:
        material_names = [slot.material.name for slot in obj.material_slots if slot.material]
        if any(token in (obj.name + " " + " ".join(material_names)).lower()
               for token in ("eye", "iris", "sclera", "cornea", "pupil")):
            objects.append({
                "name": obj.name,
                "type": obj.type,
                "dimensions": [round(float(value), 7) for value in obj.dimensions],
                "materials": material_names,
                "vertex_count": len(obj.data.vertices) if obj.type == "MESH" else None,
            })

    materials = []
    for material in bpy.data.materials:
        image_nodes = []
        if material.use_nodes and material.node_tree:
            for node in material.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image:
                    image_nodes.append(node.image.name)
        if image_nodes or any(token in material.name.lower()
                              for token in ("eye", "iris", "sclera", "cornea", "pupil")):
            materials.append({
                "name": material.name,
                "image_nodes": sorted(set(image_nodes)),
            })

    images = []
    for image in bpy.data.images:
        images.append({
            "name": image.name,
            "size": [int(image.size[0]), int(image.size[1])],
            "file_format": image.file_format,
            "filepath": image.filepath,
            "packed": bool(image.packed_file),
        })

    print("EYE_INVENTORY_JSON_BEGIN")
    print(json.dumps({
        "source": str(source),
        "eye_like_objects": objects,
        "eye_related_materials": materials,
        "all_images": images,
    }, indent=2))
    print("EYE_INVENTORY_JSON_END")


if __name__ == "__main__":
    main()
