"""Print local/world bounds and hierarchy for the approved static hair asset."""

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
ASSET = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "asset_library"
    / "hair_reference"
    / "short_hair_cut_in_layers_with_bones_90fd798a2e.glb"
)


def bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return [
        [min(point[axis] for point in points) for axis in range(3)],
        [max(point[axis] for point in points) for axis in range(3)],
    ]


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ASSET))
for obj in bpy.data.objects:
    print(
        "HAIR_ASSET_OBJECT",
        {
            "name": obj.name,
            "type": obj.type,
            "parent": obj.parent.name if obj.parent else None,
            "location": list(obj.location),
            "rotation_euler": list(obj.rotation_euler),
            "scale": list(obj.scale),
            "world_bounds": bounds(obj),
        },
    )
