#!/usr/bin/env python3
"""Read-only diagnosis of appended face hierarchy evaluation under hiding."""

from pathlib import Path
import bpy


root = Path(__file__).resolve().parent.parent
face = root / (
    "RecoverySprint/continuation_20260802/"
    "r19_blackproject_face_material_diagnostic/attempt_03/"
    "r19_face_material_probe.blend"
)


def matrix_rows(matrix):
    return [[float(value) for value in row] for row in matrix]


def world_bounds(obj):
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    return [
        [min(float(point[axis]) for point in points) for axis in range(3)],
        [max(float(point[axis]) for point in points) for axis in range(3)],
    ]


def report(label, obj):
    print(
        label,
        {
            "object": obj.name,
            "mesh": obj.data.name,
            "parent": obj.parent.name if obj.parent else None,
            "hide_viewport": bool(obj.hide_viewport),
            "matrix_world": matrix_rows(obj.matrix_world),
            "world_bounds": world_bounds(obj),
        },
    )


with bpy.data.libraries.load(str(face), link=False) as (data_from, data_to):
    data_to.objects = list(data_from.objects)
loaded = [obj for obj in data_to.objects if obj is not None]
collection = bpy.data.collections.new("INSPECT_FACE_REFERENCE_VISIBILITY_HIERARCHY")
bpy.context.scene.collection.children.link(collection)
for obj in loaded:
    collection.objects.link(obj)
    obj.hide_render = True
    obj.hide_viewport = True

torso = next(
    obj
    for obj in loaded
    if obj.type == "MESH" and obj.data.name.startswith("Ariel_Mesh_Torso_0")
)
bpy.context.view_layer.update()
report("HIDDEN_BEFORE_FIRST_UPDATE", torso)

for obj in loaded:
    obj.hide_viewport = False
bpy.context.view_layer.update()
report("VISIBLE_AFTER_UPDATE", torso)

for obj in loaded:
    obj.hide_viewport = True
bpy.context.view_layer.update()
report("HIDDEN_AFTER_VALID_UPDATE", torso)

