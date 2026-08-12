"""Audit nonadjacent intersections in a private authored anatomy graft.

Usage:
    blender --background --python \
      tools/blender_validate_authored_graft_intersections.py -- \
      candidate.blend authored_attribute output.json

The named point-domain integer attribute must equal one on graft-authored
vertices. Faces touching those vertices form the graft set. Shared-vertex
neighbors are excluded so ordinary manifold adjacency is not misreported.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils.bvhtree import BVHTree


if "--" not in sys.argv:
    raise SystemExit(
        "Expected -- candidate.blend authored_attribute output.json"
    )
arguments = sys.argv[sys.argv.index("--") + 1 :]
if len(arguments) != 3:
    raise SystemExit("Expected exactly three arguments")
SOURCE = Path(arguments[0]).resolve()
ATTRIBUTE = arguments[1]
OUTPUT = Path(arguments[2]).resolve()
OUTPUT.parent.mkdir(parents=True, exist_ok=True)


def coordinate_key(vertex):
    return tuple(round(float(value), 7) for value in vertex.co)


def mesh_bvh(faces):
    vertices = []
    vertex_map = {}
    polygons = []
    keys = []
    for face in faces:
        polygon = []
        face_keys = set()
        for vertex in face.verts:
            key = coordinate_key(vertex)
            if key not in vertex_map:
                vertex_map[key] = len(vertices)
                vertices.append(vertex.co.copy())
            polygon.append(vertex_map[key])
            face_keys.add(key)
        polygons.append(polygon)
        keys.append(face_keys)
    if not polygons:
        return None, keys
    return BVHTree.FromPolygons(
        vertices,
        polygons,
        all_triangles=False,
    ), keys


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = max(
    (obj for obj in bpy.data.objects if obj.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)
bm = bmesh.new()
bm.from_mesh(body.data)
authored_layer = bm.verts.layers.int.get(ATTRIBUTE)
if authored_layer is None:
    raise RuntimeError(
        f"authored vertex layer {ATTRIBUTE!r} not found; "
        f"available={list(body.data.attributes.keys())}"
    )

patch_faces = [
    face
    for face in bm.faces
    if any(vertex[authored_layer] == 1 for vertex in face.verts)
]
patch_set = set(patch_faces)
retained_faces = [
    face
    for face in bm.faces
    if face not in patch_set
    and max(abs(vertex.co.x) for vertex in face.verts) <= 0.095
    and max(vertex.co.y for vertex in face.verts) >= -0.240
    and min(vertex.co.y for vertex in face.verts) <= 0.060
    and max(vertex.co.z for vertex in face.verts) >= 0.630
    and min(vertex.co.z for vertex in face.verts) <= 0.860
]

patch_bvh, patch_keys = mesh_bvh(patch_faces)
retained_bvh, retained_keys = mesh_bvh(retained_faces)
self_pairs = set()
for first, second in patch_bvh.overlap(patch_bvh):
    if first >= second or patch_keys[first] & patch_keys[second]:
        continue
    self_pairs.add((first, second))
retained_pairs = set()
for first, second in patch_bvh.overlap(retained_bvh):
    if patch_keys[first] & retained_keys[second]:
        continue
    retained_pairs.add((first, second))

report = {
    "schema": "kira.avatar.authored_graft.intersection_audit.v1",
    "source": str(SOURCE),
    "authored_attribute": ATTRIBUTE,
    "patch_face_count": len(patch_faces),
    "retained_local_face_count": len(retained_faces),
    "nonadjacent_patch_self_intersections": len(self_pairs),
    "nonadjacent_patch_retained_intersections": len(retained_pairs),
    "pass": not self_pairs and not retained_pairs,
    "first_patch_self_pairs": [
        list(pair) for pair in sorted(self_pairs)[:40]
    ],
    "first_patch_retained_pairs": [
        list(pair) for pair in sorted(retained_pairs)[:40]
    ],
}
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
bm.free()
print(OUTPUT)
print(json.dumps(report, indent=2))
