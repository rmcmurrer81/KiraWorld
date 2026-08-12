"""Print compact armature/head transforms for a GLB without changing it.

Usage:
    blender --background --python tools/blender_probe_avatar_head.py -- model.glb [head-name]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy  # type: ignore


def matrix_rows(value) -> list[list[float]]:
    return [[round(float(item), 7) for item in row] for row in value]


def main() -> None:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if not values:
        raise SystemExit("usage: ... -- model.glb [head-name]")
    path = Path(values[0]).resolve(strict=True)
    head_name = values[1] if len(values) > 1 else "mixamorig:Head_06"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"expected one armature; found {len(armatures)}")
    armature = armatures[0]
    bone = armature.data.bones.get(head_name)
    pose_bone = armature.pose.bones.get(head_name)
    if bone is None or pose_bone is None:
        raise RuntimeError(f"head bone is missing: {head_name}")
    print(
        json.dumps(
            {
                "path": str(path),
                "armature": armature.name,
                "armature_location": [round(float(item), 7) for item in armature.location],
                "armature_scale": [round(float(item), 7) for item in armature.scale],
                "armature_matrix_world": matrix_rows(armature.matrix_world),
                "head": bone.name,
                "head_local": [round(float(item), 7) for item in bone.head_local],
                "tail_local": [round(float(item), 7) for item in bone.tail_local],
                "bone_matrix_local": matrix_rows(bone.matrix_local),
                "pose_matrix": matrix_rows(pose_bone.matrix),
                "head_world_matrix": matrix_rows(armature.matrix_world @ pose_bone.matrix),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
