"""Print degenerate mesh faces and their local adjacency from a saved blend."""

from __future__ import annotations

import sys
from pathlib import Path

import bmesh
import bpy


arguments = sys.argv[sys.argv.index("--") + 1 :]
source = Path(arguments[0]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(source))

for obj in (item for item in bpy.context.scene.objects if item.type == "MESH"):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bad = [face for face in bm.faces if face.calc_area() < 1.0e-11]
    if bad:
        print(f"OBJECT {obj.name} DEGENERATE {len(bad)}")
        for face in bad:
            print(
                {
                    "face_index": face.index,
                    "area": face.calc_area(),
                    "center": tuple(round(value, 9) for value in face.calc_center_median()),
                    "vertices": [
                        {
                            "index": vertex.index,
                            "co": tuple(round(value, 9) for value in vertex.co),
                            "linked_faces": len(vertex.link_faces),
                        }
                        for vertex in face.verts
                    ],
                    "edge_link_faces": [len(edge.link_faces) for edge in face.edges],
                }
            )
    bm.free()
