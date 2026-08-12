"""Print renderable object bounds in the current rejected R7 scene."""

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
BLEND = (
    ROOT
    / "Avatar"
    / "private_owner_review"
    / "dual_robert_20260729"
    / "biological_static_likeness_v25_r7_makehuman_cc0_private_fit"
    / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V25_R7.blend"
)


def corners(obj, *, world):
    matrix = obj.matrix_world if world else None
    return [
        matrix @ Vector(corner) if matrix else Vector(corner)
        for corner in obj.bound_box
    ]


def bounds(obj, *, world):
    points = corners(obj, world=world)
    return [
        [min(point[axis] for point in points) for axis in range(3)],
        [max(point[axis] for point in points) for axis in range(3)],
    ]


bpy.ops.wm.open_mainfile(filepath=str(BLEND))
for obj in bpy.data.objects:
    if obj.type != "MESH":
        continue
    print(
        "R7_SCENE_OBJECT",
        {
            "name": obj.name,
            "parent": obj.parent.name if obj.parent else None,
            "hide_render": obj.hide_render,
            "location": list(obj.location),
            "scale": list(obj.scale),
            "local_bounds": bounds(obj, world=False),
            "world_bounds": bounds(obj, world=True),
        },
    )
