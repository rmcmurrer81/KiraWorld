"""Measure the visible face surface around Kira's eyes in body-native space.

Run with Blender in background mode.  The report is diagnostic only and does
not modify the active avatar.
"""

from __future__ import annotations

import json
from pathlib import Path

import bpy  # type: ignore
from mathutils import Vector  # type: ignore
from mathutils.bvhtree import BVHTree  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Avatar/models/temp_ai/kira/avatar.glb"
OUTPUT = ROOT / "Data/world_tests/kira_eye_upgrade_20260718/socket_surface_measurements.json"


def main() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    mesh = max(
        (obj for obj in bpy.context.scene.objects if obj.type == "MESH"),
        key=lambda obj: len(obj.data.vertices),
    )
    depsgraph = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(mesh, depsgraph)
    world_from_local = mesh.matrix_world.copy()
    local_from_world = world_from_local.inverted()
    measurements = []
    for x in (-0.036, -0.032, -0.0288, -0.025, -0.021, 0.021, 0.025, 0.0288, 0.032, 0.036):
        for z in (1.099, 1.102, 1.1056, 1.109, 1.112):
            # Ray enters the face from in front (negative native Y).
            world_origin = Vector((x, -0.25, z))
            world_direction = Vector((0.0, 1.0, 0.0))
            local_origin = local_from_world @ world_origin
            local_direction = (local_from_world.to_3x3() @ world_direction).normalized()
            hit, normal, face_index, distance = bvh.ray_cast(local_origin, local_direction, 5.0)
            world_hit = world_from_local @ hit if hit else None
            world_normal = (world_from_local.to_3x3().inverted().transposed() @ normal).normalized() if normal else None
            measurements.append(
                {
                    "x": x,
                    "z": z,
                    "hit": list(world_hit) if world_hit else None,
                    "normal": list(world_normal) if world_normal else None,
                    "face_index": face_index,
                    "distance": distance,
                }
            )
    aperture_summary = {}
    for side, x_min, x_max in (("left", -0.045, -0.010), ("right", 0.010, 0.045)):
        hole_points = []
        scanlines = {}
        x_steps = 71
        z_steps = 47
        for zi in range(z_steps):
            z = 1.095 + (1.118 - 1.095) * zi / (z_steps - 1)
            xs = []
            for xi in range(x_steps):
                x = x_min + (x_max - x_min) * xi / (x_steps - 1)
                local_origin = local_from_world @ Vector((x, -0.25, z))
                local_direction = (local_from_world.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
                hit, _normal, _face_index, _distance = bvh.ray_cast(local_origin, local_direction, 5.0)
                world_hit = world_from_local @ hit if hit else None
                # A positive-Y first hit is the rear of the hollow head, so the
                # ray passed through the actual eye opening without touching
                # the front face.
                if world_hit is not None and world_hit.y > 0.0:
                    hole_points.append((x, z))
                    xs.append(x)
            if xs:
                scanlines[f"{z:.6f}"] = [min(xs), max(xs)]
        if hole_points:
            aperture_summary[side] = {
                "centroid_x": sum(point[0] for point in hole_points) / len(hole_points),
                "centroid_z": sum(point[1] for point in hole_points) / len(hole_points),
                "min_x": min(point[0] for point in hole_points),
                "max_x": max(point[0] for point in hole_points),
                "min_z": min(point[1] for point in hole_points),
                "max_z": max(point[1] for point in hole_points),
                "point_count": len(hole_points),
                "scanlines": scanlines,
            }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": str(SOURCE),
        "mesh": mesh.name,
        "coordinate_note": "negative Y is face-forward; first hit is the visible exterior surface",
        "measurements": measurements,
        "aperture_summary": aperture_summary,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
