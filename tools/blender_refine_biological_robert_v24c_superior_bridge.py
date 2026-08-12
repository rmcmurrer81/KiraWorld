"""Close the remaining superior pubic notch on the clean V24B bridge.

V24B removed the large triangular tunnel with a real connected patch, but its
top-center attachment still sat below the inferior abdominal silhouette.  This
bounded repair advances only that shared bridge vertex upward and slightly
forward.  No anatomy, movement, runtime, clothing, or unrelated likeness work
is introduced.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bmesh
import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v24b_clean_pubic_bridge/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24B_CLEAN_PUBIC_BRIDGE.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v24c_superior_bridge_refinement"
)
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_BODY = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24B_CLEAN_PUBIC_BRIDGE"
BODY_NAME = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_SUPERIOR_BRIDGE_REFINEMENT"
BLEND_PATH = OUT / f"{BODY_NAME}.blend"
REPORT_PATH = OUT / "V24C_SUPERIOR_BRIDGE_REFINEMENT_REPORT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def topology(obj: bpy.types.Object) -> dict[str, int]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    result = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges": sum(len(edge.link_faces) == 1 for edge in bm.edges),
        "nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2 for edge in bm.edges
        ),
        "local_boundary_edges": sum(
            len(edge.link_faces) == 1
            and all(
                abs(vertex.co.x) <= 0.070
                and -0.150 <= vertex.co.y <= 0.130
                and 0.640 <= vertex.co.z <= 0.850
                for vertex in edge.verts
            )
            for edge in bm.edges
        ),
        "local_nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2
            and all(
                abs(vertex.co.x) <= 0.070
                and -0.150 <= vertex.co.y <= 0.130
                and 0.640 <= vertex.co.z <= 0.850
                for vertex in edge.verts
            )
            for edge in bm.edges
        ),
    }
    bm.free()
    return result


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get(SOURCE_BODY)
if body is None:
    raise RuntimeError("V24B clean bridge body is missing")

before_topology = topology(body)
matches = [
    vertex
    for vertex in body.data.vertices
    if abs(vertex.co.x) <= 0.002
    and -0.125 <= vertex.co.y <= -0.090
    and 0.805 <= vertex.co.z <= 0.818
]
if len(matches) != 1:
    raise RuntimeError(
        f"expected one shared superior bridge vertex, found {len(matches)}"
    )
vertex = matches[0]
before_coordinate = tuple(vertex.co)
vertex.co.y = -0.1180
vertex.co.z = 0.8315
after_coordinate = tuple(vertex.co)
body.data.update()

after_topology = topology(body)
body.name = BODY_NAME
body["status"] = (
    "REJECTED ENGINEERING SUBSTRATE — SUPERIOR BRIDGE VISUAL CHECK REQUIRED"
)
body["repair"] = (
    "ONE SHARED TOP-CENTER PUBIC BRIDGE VERTEX ADVANCED UPWARD/FORWARD"
)
body["anatomy_status"] = "NOT ATTACHED"
body["owner_approved"] = False
body["movement_started"] = False
body["runtime_activation_allowed"] = False

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
report = {
    "schema": "kira.avatar.biological_robert.v24c.superior_bridge.v1",
    "status": body["status"],
    "source": str(SOURCE),
    "source_sha256": sha256(SOURCE),
    "output": str(BLEND_PATH),
    "output_sha256": sha256(BLEND_PATH),
    "bounded_vertex_adjustment": {
        "count": 1,
        "before": list(before_coordinate),
        "after": list(after_coordinate),
        "delta": [
            after_coordinate[index] - before_coordinate[index]
            for index in range(3)
        ],
    },
    "topology": {
        "before": before_topology,
        "after": after_topology,
        "unchanged": before_topology == after_topology,
    },
    "truthful_gate": {
        "anatomy_attached": False,
        "static_owner_review_candidate": False,
        "front_side_three_quarter_diagnostics_required": True,
    },
    "scope": {
        "static_only": True,
        "movement": False,
        "activation": False,
        "runtime_attachment": False,
        "synthetic_robert": False,
        "kira": False,
        "clothing": False,
    },
}
REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(BLEND_PATH)
print(REPORT_PATH)
print(json.dumps(report, indent=2))
