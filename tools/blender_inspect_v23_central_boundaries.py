"""Inspect open-edge components in the bounded anterior-pelvis region."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bmesh
import bpy


if "--" not in sys.argv:
    raise SystemExit("expected -- source.blend")
arguments = sys.argv[sys.argv.index("--") + 1 :]
if len(arguments) != 1:
    raise SystemExit("expected exactly one source.blend")
source = Path(arguments[0]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(source))
body = max(
    (obj for obj in bpy.data.objects if obj.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)
bm = bmesh.new()
bm.from_mesh(body.data)
edges = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and all(
        abs(vertex.co.x) < 0.120
        and -0.220 < vertex.co.y < 0.160
        and 0.620 < vertex.co.z < 0.870
        for vertex in edge.verts
    )
]
vertex_edges = {}
for edge in edges:
    for vertex in edge.verts:
        vertex_edges.setdefault(vertex, []).append(edge)
unseen = set(edges)
components = []
while unseen:
    seed = unseen.pop()
    component = [seed]
    stack = [seed]
    while stack:
        current = stack.pop()
        for vertex in current.verts:
            for neighbor in vertex_edges[vertex]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    component.append(neighbor)
                    stack.append(neighbor)
    vertices = {vertex for edge in component for vertex in edge.verts}
    components.append(
        {
            "edge_count": len(component),
            "vertex_count": len(vertices),
            "min_x": min(vertex.co.x for vertex in vertices),
            "max_x": max(vertex.co.x for vertex in vertices),
            "min_y": min(vertex.co.y for vertex in vertices),
            "max_y": max(vertex.co.y for vertex in vertices),
            "min_z": min(vertex.co.z for vertex in vertices),
            "max_z": max(vertex.co.z for vertex in vertices),
            "coordinates": [
                [round(value, 6) for value in vertex.co]
                for vertex in sorted(
                    vertices,
                    key=lambda item: (item.co.z, item.co.x, item.co.y),
                )[:40]
            ],
        }
    )
print(json.dumps({"source": str(source), "components": components}, indent=2))
bm.free()
