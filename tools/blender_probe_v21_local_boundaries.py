"""Report V21 boundary loops near the front pelvis."""
import bmesh
import bpy
from mathutils import Vector
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / "Avatar/private_owner_review/dual_robert_20260729/biological_static_likeness_v21_bounded_local_repair/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V21_BOUNDED_LOCAL_REPAIR.blend"
bpy.ops.wm.open_mainfile(filepath=str(source))
body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V21_BOUNDED_LOCAL_REPAIR")
bm = bmesh.new()
bm.from_mesh(body.data)
local = []
for edge in bm.edges:
    if not edge.is_boundary:
        continue
    center = sum((v.co for v in edge.verts), Vector()) / 2
    if abs(center.x) < .16 and center.y < -.04 and .48 < center.z < .95:
        local.append((center.x, center.y, center.z, edge.index))
print("LOCAL_BOUNDARY_COUNT", len(local))
for row in sorted(local, key=lambda item: (item[2], item[0]))[:500]:
    print("BOUNDARY", *row)
bm.free()
