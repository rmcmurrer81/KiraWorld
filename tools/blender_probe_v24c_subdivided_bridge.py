"""Report the V24C anterior bridge after the production subdivision step."""

from __future__ import annotations

import json
from pathlib import Path

import bmesh
import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v24c_superior_bridge_refinement/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_SUPERIOR_BRIDGE_REFINEMENT.blend"
)
OUTPUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/V24C_SUBDIVIDED_BRIDGE_PROBE.json"
)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects[
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_SUPERIOR_BRIDGE_REFINEMENT"
]
bm = bmesh.new()
bm.from_mesh(body.data)
bm.faces.ensure_lookup_table()
central = [
    face
    for face in bm.faces
    if face.normal.y < -0.75
    and min(vertex.co.x for vertex in face.verts) < -0.030
    and max(vertex.co.x for vertex in face.verts) > 0.030
    and all(
        -0.135 < vertex.co.y < -0.060
        and 0.670 < vertex.co.z < 0.840
        for vertex in face.verts
    )
]
edges = list({edge for face in central for edge in face.edges})
bmesh.ops.subdivide_edges(
    bm,
    edges=edges,
    cuts=5,
    use_grid_fill=True,
)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
bm.normal_update()

faces = []
for face in bm.faces:
    center = face.calc_center_median()
    if (
        face.normal.y < -0.60
        and abs(center.x) <= 0.065
        and 0.700 <= center.z <= 0.830
        and -0.145 <= center.y <= -0.070
    ):
        faces.append(
            {
                "index": face.index,
                "center": [round(float(v), 7) for v in center],
                "vertices": [
                    [round(float(v), 7) for v in vertex.co]
                    for vertex in face.verts
                ],
                "normal": [round(float(v), 7) for v in face.normal],
            }
        )

payload = {
    "source": str(SOURCE),
    "central_face_indices": [face.index for face in central],
    "face_count": len(faces),
    "faces": sorted(
        faces,
        key=lambda item: (-item["center"][2], item["center"][0]),
    ),
}
OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(OUTPUT)
print(json.dumps(payload, indent=2))
bm.free()
