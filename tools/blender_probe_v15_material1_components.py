"""List connected face components within V15 material slot 1."""
import bpy
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v15_from_v14/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14.blend"
bpy.ops.wm.open_mainfile(filepath=str(source))
obj = bpy.data.objects["BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14"]
faces = [p for p in obj.data.polygons if p.material_index == 6]
vertex_faces = {}
for face in faces:
    for vi in face.vertices:
        vertex_faces.setdefault(vi, set()).add(face.index)
face_by_id = {p.index:p for p in faces}
remaining = set(face_by_id)
rows=[]
while remaining:
    seed=remaining.pop(); stack=[seed]; members={seed}
    while stack:
        fid=stack.pop()
        for vi in face_by_id[fid].vertices:
            for other in vertex_faces.get(vi,()):
                if other in remaining:
                    remaining.remove(other); members.add(other); stack.append(other)
    verts={vi for fid in members for vi in face_by_id[fid].vertices}
    coords=[obj.data.vertices[i].co for i in verts]
    rows.append((len(members),len(verts),tuple(min(c[j] for c in coords) for j in range(3)),tuple(max(c[j] for c in coords) for j in range(3))))
for row in sorted(rows,reverse=True):
    print("MAT6_COMPONENT",row)
