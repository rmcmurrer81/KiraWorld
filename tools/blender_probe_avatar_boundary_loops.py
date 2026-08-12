"""Print boundary-loop locations for one GLB without exporting or rendering it."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bmesh
import bpy


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(argv) != 1:
        raise SystemExit("usage: blender --background --python <script> -- model.glb")
    source = Path(argv[0]).resolve(strict=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    body = max(meshes, key=lambda item: len(item.data.vertices))
    bm = bmesh.new()
    bm.from_mesh(body.data)
    boundary = {edge for edge in bm.edges if edge.is_boundary}
    loops: list[list] = []
    while boundary:
        seed = boundary.pop()
        component_edges = [seed]
        component_verts = set(seed.verts)
        changed = True
        while changed:
            changed = False
            for edge in list(boundary):
                if any(vertex in component_verts for vertex in edge.verts):
                    boundary.remove(edge)
                    component_edges.append(edge)
                    component_verts.update(edge.verts)
                    changed = True
        points = [body.matrix_world @ vertex.co for vertex in component_verts]
        low = [min(point[index] for point in points) for index in range(3)]
        high = [max(point[index] for point in points) for index in range(3)]
        center = [sum(point[index] for point in points) / len(points) for index in range(3)]
        loops.append(
            {
                "edge_count": len(component_edges),
                "vertex_count": len(component_verts),
                "center": [round(value, 7) for value in center],
                "low": [round(value, 7) for value in low],
                "high": [round(value, 7) for value in high],
                "extent": [round(high[index] - low[index], 7) for index in range(3)],
            }
        )
    bm.free()
    print(json.dumps({"source": source.name, "mesh": body.name, "loops": sorted(loops, key=lambda item: item["center"][2], reverse=True)}, indent=2))


if __name__ == "__main__":
    main()
