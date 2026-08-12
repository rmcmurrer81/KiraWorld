"""List connected component bounds for V15 body object."""
import bpy
from pathlib import Path
from collections import deque

root = Path(__file__).resolve().parents[1]
source = root / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v15_from_v14/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14.blend"
bpy.ops.wm.open_mainfile(filepath=str(source))
body = bpy.data.objects["BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14"]
mesh = body.data
adj = [set() for _ in mesh.vertices]
for edge in mesh.edges:
    a, b = edge.vertices
    adj[a].add(b); adj[b].add(a)
remaining = set(range(len(mesh.vertices)))
rows = []
while remaining:
    seed = remaining.pop()
    members = [seed]
    q = [seed]
    while q:
        current = q.pop()
        for neighbor in adj[current]:
            if neighbor in remaining:
                remaining.remove(neighbor); q.append(neighbor); members.append(neighbor)
    if len(members) < 500:
        continue
    coords = [mesh.vertices[i].co for i in members]
    mins = tuple(min(c[j] for c in coords) for j in range(3))
    maxs = tuple(max(c[j] for c in coords) for j in range(3))
    rows.append((len(members), mins, maxs, min(members), max(members)))
for row in sorted(rows, reverse=True):
    print("COMPONENT", row)
