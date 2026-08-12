#!/usr/bin/env python3
"""Read-only console diagnostic for R19 body/reference transform spaces."""

from pathlib import Path
import bpy
from mathutils import Vector

root = Path(__file__).resolve().parent.parent
face = root / "RecoverySprint/continuation_20260802/r19_blackproject_face_material_diagnostic/attempt_03/r19_face_material_probe.blend"
body = bpy.data.objects["Kira_R19_BlackProject_Radial_Patch_Primary_Surface"]

def record(obj):
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    low = [min(float(point[i]) for point in points) for i in range(3)]
    high = [max(float(point[i]) for point in points) for i in range(3)]
    return {
        "name": obj.name,
        "data": obj.data.name,
        "parent": obj.parent.name if obj.parent else None,
        "matrix_world": [list(row) for row in obj.matrix_world],
        "matrix_local": [list(row) for row in obj.matrix_local],
        "bounds": [low, high],
    }

print("BODY", record(body))
with bpy.data.libraries.load(str(face), link=False) as (data_from, data_to):
    print("SOURCE_OBJECT_NAMES", list(data_from.objects))
    data_to.objects = list(data_from.objects)
loaded = [obj for obj in data_to.objects if obj is not None]
collection = bpy.data.collections.new("INSPECT_FACE_REFERENCE_HIERARCHY")
bpy.context.scene.collection.children.link(collection)
for obj in loaded:
    collection.objects.link(obj)
bpy.context.view_layer.update()
for obj in loaded:
    if obj.type == "MESH" and obj.data.name.startswith("Ariel_Mesh_Torso"):
        print("TORSO", record(obj))
for obj in loaded:
    if obj.type == "ARMATURE":
        print("ARMATURE", {"name": obj.name, "matrix_world": [list(row) for row in obj.matrix_world]})
