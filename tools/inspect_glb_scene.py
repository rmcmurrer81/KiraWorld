import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("usage: blender --background --python tools/inspect_glb_scene.py -- path.glb")
    path = Path(sys.argv[-1])
    if not path.exists():
        raise SystemExit(f"missing GLB: {path}")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.ops.import_scene.gltf(filepath=str(path))

    rows = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        low = [min(v[i] for v in corners) for i in range(3)]
        high = [max(v[i] for v in corners) for i in range(3)]
        rows.append(
            {
                "name": obj.name,
                "vertices": len(obj.data.vertices),
                "materials": [mat.name if mat else "" for mat in obj.data.materials],
                "low": [round(value, 4) for value in low],
                "high": [round(value, 4) for value in high],
            }
        )

    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
