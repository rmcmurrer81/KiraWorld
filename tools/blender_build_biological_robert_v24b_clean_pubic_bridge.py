"""Repair the inherited V1 central pubic gap on the clean V24 substrate.

The owner-observed dark triangle is not a material problem.  The clean V1
surface has two mirrored root face sets whose medial paths do not form one
continuous superior pubic bridge.  This static engineering step removes only
those 22 known V1 faces, merges their mirrored medial vertices at exact
midpoints, and fills the resulting single compact ten-edge opening.

No anatomy is attached here.  This creates a clean, connected body substrate
for the next bounded anatomy build and keeps the repair independently
inspectable.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v24_clean_v1_rebase/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24_CLEAN_V1_REBASE.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v24b_clean_pubic_bridge"
)
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_BODY = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24_CLEAN_V1_REBASE"
BODY_NAME = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24B_CLEAN_PUBIC_BRIDGE"
BLEND_PATH = OUT / f"{BODY_NAME}.blend"
REPORT_PATH = OUT / "V24B_CLEAN_PUBIC_BRIDGE_REPORT.json"

# Exact mirrored V1 face pairs established by the independent minimal-root
# analysis.  V24 preserves V1's raw vertex/face indexing.
ROOT_FACE_INDICES = [
    5547,
    5738,
    5845,
    5944,
    5948,
    5989,
    6155,
    6162,
    6165,
    6167,
    6168,
    10119,
    10310,
    10417,
    10516,
    10520,
    10561,
    10728,
    10735,
    10738,
    10740,
    10741,
]

MEDIAL_WELD_PAIRS = [
    (10316, 5668),
    (10525, 5877),
    (10342, 5694),
    (10620, 5972),
    (10626, 5978),
    (10622, 5974),
    (10739, 6091),
    (10763, 6115),
    (10748, 6100),
    (10724, 6076),
    (10926, 6277),
    (10742, 6094),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def counts(bm: bmesh.types.BMesh) -> dict[str, int]:
    return {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges": sum(len(edge.link_faces) == 1 for edge in bm.edges),
        "wire_edges": sum(len(edge.link_faces) == 0 for edge in bm.edges),
        "nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2 for edge in bm.edges
        ),
        "local_boundary_edges": sum(
            len(edge.link_faces) == 1
            and all(
                abs(vertex.co.x) <= 0.070
                and -0.150 <= vertex.co.y <= 0.130
                and 0.640 <= vertex.co.z <= 0.830
                for vertex in edge.verts
            )
            for edge in bm.edges
        ),
        "local_nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2
            and all(
                abs(vertex.co.x) <= 0.070
                and -0.150 <= vertex.co.y <= 0.130
                and 0.640 <= vertex.co.z <= 0.830
                for vertex in edge.verts
            )
            for edge in bm.edges
        ),
    }


def ordered_boundary_cycle(
    edges: list[bmesh.types.BMEdge],
) -> list[bmesh.types.BMVert]:
    adjacency: dict[bmesh.types.BMVert, list[bmesh.types.BMVert]] = {}
    for edge in edges:
        a, b = edge.verts
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
    if not adjacency or any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise RuntimeError(
            "local opening is not one simple degree-two boundary cycle"
        )
    start = min(adjacency, key=lambda vertex: (vertex.co.z, vertex.co.x))
    cycle = [start]
    previous = None
    current = start
    while True:
        candidates = [
            vertex for vertex in adjacency[current] if vertex is not previous
        ]
        if not candidates:
            raise RuntimeError("boundary walk terminated early")
        next_vertex = candidates[0]
        if next_vertex is start:
            break
        if next_vertex in cycle:
            raise RuntimeError("boundary walk self-repeated")
        cycle.append(next_vertex)
        previous, current = current, next_vertex
    if len(cycle) != len(adjacency):
        raise RuntimeError("boundary edges contain more than one cycle")
    return cycle


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get(SOURCE_BODY)
if body is None:
    raise RuntimeError("clean V24 body is missing")

bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()
before = counts(bm)

face_objects = [bm.faces[index] for index in ROOT_FACE_INDICES]
original_vertex_objects = {
    index: bm.verts[index]
    for pair in MEDIAL_WELD_PAIRS
    for index in pair
}
bmesh.ops.delete(bm, geom=face_objects, context="FACES")

weld_records = []
for left_index, right_index in MEDIAL_WELD_PAIRS:
    left = original_vertex_objects[left_index]
    right = original_vertex_objects[right_index]
    if not left.is_valid or not right.is_valid:
        raise RuntimeError(
            f"weld vertex invalid after face deletion: {left_index}/{right_index}"
        )
    midpoint = (left.co + right.co) * 0.5
    bmesh.ops.pointmerge(bm, verts=[left, right], merge_co=midpoint)
    weld_records.append(
        {
            "left": left_index,
            "right": right_index,
            "midpoint": [round(value, 7) for value in midpoint],
        }
    )

bm.verts.index_update()
bm.edges.index_update()
bm.faces.index_update()
bm.normal_update()

local_boundary = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and all(
        abs(vertex.co.x) <= 0.070
        and -0.150 <= vertex.co.y <= 0.130
        and 0.640 <= vertex.co.z <= 0.830
        for vertex in edge.verts
    )
]
cycle = ordered_boundary_cycle(local_boundary)
cycle_coordinates = [
    [round(value, 7) for value in vertex.co] for vertex in cycle
]

# Create one compact face and triangulate it without introducing a conical
# center vertex.  Choose the winding whose normal faces the front (-Y).
try:
    patch_face = bm.faces.new(cycle)
except ValueError:
    patch_face = bm.faces.new(list(reversed(cycle)))
bm.normal_update()
if patch_face.normal.y > 0:
    bm.faces.remove(patch_face)
    patch_face = bm.faces.new(list(reversed(cycle)))
    bm.normal_update()

donor_materials = [
    face.material_index
    for edge in local_boundary
    for face in edge.link_faces
    if face is not patch_face
]
patch_face.material_index = (
    max(set(donor_materials), key=donor_materials.count)
    if donor_materials
    else 1
)
patch_material_index = patch_face.material_index
triangulated = bmesh.ops.triangulate(
    bm,
    faces=[patch_face],
    quad_method="BEAUTY",
    ngon_method="BEAUTY",
)
new_faces = [face for face in triangulated["faces"] if face.is_valid]
for face in new_faces:
    face.material_index = patch_material_index
    face.smooth = True

bm.normal_update()
after = counts(bm)
bm.to_mesh(body.data)
body.data.update()
bm.free()

body.name = BODY_NAME
body["status"] = (
    "REJECTED ENGINEERING SUBSTRATE — PUBIC BRIDGE REPAIRED; ANATOMY NOT ATTACHED"
)
body["source_authority"] = "CLEAN V1-DERIVED V24 SUBSTRATE"
body["repair"] = (
    "22-FACE BILATERAL ROOT REMOVAL; 12 MIRRORED MEDIAL WELDS; "
    "ONE COMPACT TRIANGULATED PUBIC PATCH"
)
body["anatomy_status"] = "NOT ATTACHED"
body["owner_approved"] = False
body["movement_started"] = False
body["runtime_activation_allowed"] = False

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
report = {
    "schema": "kira.avatar.biological_robert.v24b.clean_pubic_bridge.v1",
    "status": body["status"],
    "source": str(SOURCE),
    "source_sha256": sha256(SOURCE),
    "output": str(BLEND_PATH),
    "output_sha256": sha256(BLEND_PATH),
    "removed_root_faces": ROOT_FACE_INDICES,
    "welds": weld_records,
    "opening_before_fill": {
        "boundary_edge_count": len(local_boundary),
        "cycle_vertex_count": len(cycle),
        "cycle_coordinates": cycle_coordinates,
    },
    "patch": {
        "triangulated_face_count": len(new_faces),
        "center_fan_vertex_added": False,
        "front_facing": True,
    },
    "topology": {
        "before": before,
        "after": after,
        "local_boundary_restored": after["local_boundary_edges"] == 0,
        "local_nonmanifold_free": after["local_nonmanifold_gt2_edges"] == 0,
    },
    "truthful_gate": {
        "anatomy_attached": False,
        "static_owner_review_candidate": False,
        "next_required_work": (
            "render front/side/three-quarter bridge diagnostics, then build "
            "one connected anatomy surface only if the superior bridge is clean"
        ),
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
