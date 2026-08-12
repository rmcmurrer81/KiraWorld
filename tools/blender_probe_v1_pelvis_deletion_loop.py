"""Probe a bounded V1 pelvis deletion mask without saving changes."""
from pathlib import Path
import bmesh
import bpy

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
bpy.ops.wm.open_mainfile(filepath=str(SRC))
obj = bpy.data.objects["BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1"]
bm = bmesh.new()
bm.from_mesh(obj.data)
delete = [
    face
    for face in bm.faces
    if (
        abs(face.calc_center_median().x) <= 0.10
        and 0.62 <= face.calc_center_median().z <= 0.88
        and -0.22 <= face.calc_center_median().y <= 0.13
    )
]
bmesh.ops.delete(bm, geom=delete, context="FACES")
boundary = [edge for edge in bm.edges if len(edge.link_faces) == 1]
adjacency = {}
for edge in boundary:
    a, b = edge.verts
    adjacency.setdefault(a, set()).add(b)
    adjacency.setdefault(b, set()).add(a)
unseen = set(adjacency)
loops = []
while unseen:
    seed = unseen.pop()
    stack = [seed]
    members = {seed}
    while stack:
        current = stack.pop()
        for neighbor in adjacency[current]:
            if neighbor in unseen:
                unseen.remove(neighbor)
                members.add(neighbor)
                stack.append(neighbor)
    loops.append(members)
print("deleted_faces", len(delete))
print("boundary_edges", len(boundary))
for number, members in enumerate(sorted(loops, key=len, reverse=True)):
    xs = [v.co.x for v in members]
    ys = [v.co.y for v in members]
    zs = [v.co.z for v in members]
    print(
        "loop",
        number,
        "verts",
        len(members),
        "degree_set",
        sorted({len(adjacency[v]) for v in members}),
        "bounds",
        (min(xs), min(ys), min(zs)),
        (max(xs), max(ys), max(zs)),
    )
bm.free()
