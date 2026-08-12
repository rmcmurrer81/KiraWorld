"""Read-only inventory of the authorized male anatomy GLB variants."""

import sys
from pathlib import Path

import bpy
from mathutils import Vector


source = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
for obj in sorted(
    (item for item in bpy.context.scene.objects if item.type == "MESH"),
    key=lambda item: len(item.data.vertices),
    reverse=True,
):
    bounds = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    print(
        obj.name,
        "v",
        len(obj.data.vertices),
        "f",
        len(obj.data.polygons),
        "min",
        tuple(round(min(point[axis] for point in bounds), 4) for axis in range(3)),
        "max",
        tuple(round(max(point[axis] for point in bounds), 4) for axis in range(3)),
    )
