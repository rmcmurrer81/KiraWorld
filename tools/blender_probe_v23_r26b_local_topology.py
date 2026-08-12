"""Report local boundary/nonmanifold edges in the R26B engineering trial."""

from __future__ import annotations

import json
from pathlib import Path

import bmesh
import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_r26b_broad_root_transition_trial/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_"
    "R26B_BROAD_ROOT_TRANSITION_TRIAL.blend"
)
OUTPUT = SOURCE.parent / "R26B_LOCAL_TOPOLOGY_DIAGNOSTIC.json"


def edge_record(edge: bmesh.types.BMEdge):
    return {
        "linked_faces": len(edge.link_faces),
        "vertices": [
            [round(value, 7) for value in vertex.co]
            for vertex in edge.verts
        ],
    }


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = max(
    (obj for obj in bpy.context.scene.objects if obj.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)
bm = bmesh.new()
bm.from_mesh(body.data)
local_edges = [
    edge
    for edge in bm.edges
    if (
        len(edge.link_faces) != 2
        and all(
            abs(vertex.co.x) <= 0.060
            and -0.220 <= vertex.co.y <= 0.100
            and 0.650 <= vertex.co.z <= 0.850
            for vertex in edge.verts
        )
    )
]
report = {
    "source": str(SOURCE),
    "local_non_two_face_edge_count": len(local_edges),
    "by_linked_face_count": {
        str(count): sum(len(edge.link_faces) == count for edge in local_edges)
        for count in sorted({len(edge.link_faces) for edge in local_edges})
    },
    "edges": [edge_record(edge) for edge in local_edges],
}
OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(OUTPUT)
print(json.dumps(report, indent=2))
bm.free()
