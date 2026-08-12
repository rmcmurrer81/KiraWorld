"""Build a deformation-only superior pubic bridge trial from R24.

The visible superior opening in R24 is produced by a deeply recessed/folded
closed surface between the inferior abdominal underside and the authored shaft
root. Earlier face-cut/fill trials produced radial teeth, cups, shelves, or
corrugated strips. This trial does not cut or add topology. It moves only the
existing anterior-facing owner-surface vertices into a bounded smooth Hermite
curve between measured lower and upper anchors.

No anatomy branch vertices are moved. No Boolean, remesh, donor surface,
radial fan, inserted panel, or bridge strip is used.

The result is static engineering evidence only. It cannot authorize movement,
runtime attachment, activation, Synthetic Robert, Kira, clothing, or Kira
World work.
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
    "biological_static_likeness_v23_preserved_surface_trial_r24_raised_branches/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_"
    "PRESERVED_SURFACE_TRIAL_R24_RAISED_BRANCHES.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_r26a_surface_fair_bridge_trial"
)
OUT.mkdir(parents=True, exist_ok=True)
BODY_OUTPUT_NAME = (
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_"
    "R26A_SURFACE_FAIR_BRIDGE_TRIAL"
)
BLEND_PATH = OUT / f"{BODY_OUTPUT_NAME}.blend"
REPORT_PATH = OUT / "R26A_SURFACE_FAIR_BRIDGE_REPORT.json"


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def topology_counts_bmesh(bm: bmesh.types.BMesh) -> dict[str, int]:
    return {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges": sum(len(edge.link_faces) == 1 for edge in bm.edges),
        "wire_edges": sum(len(edge.link_faces) == 0 for edge in bm.edges),
        "nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2 for edge in bm.edges
        ),
    }


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = next(
    obj
    for obj in bpy.context.scene.objects
    if obj.type == "MESH" and "BIOLOGICAL_ROBERT_STATIC_LIKENESS" in obj.name
)
source_sha256 = hashlib.sha256(SOURCE.read_bytes()).hexdigest()

bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.normal_update()
baseline_topology = topology_counts_bmesh(bm)
surface_class = bm.verts.layers.int.get("V23_Surface_Class")

# Measured anchors from R24:
# - lower pubic/root surface around Z 0.8065, Y about -0.086;
# - inferior abdominal underside around Z 0.8240, Y about -0.147.
# The zero-slope smoothstep endpoints create a continuous, non-corrugated
# transition without inventing a flat bridge panel.
lower_z = 0.8065
upper_z = 0.8240
lower_y = -0.0860
upper_y = -0.1470
maximum_abs_x = 0.046
full_weight_abs_x = 0.014

moved = []
candidate_vertices = []
anatomy_vertices_moved = 0
maximum_delta_y = 0.0
for vertex in bm.verts:
    co = vertex.co
    if (
        abs(co.x) > maximum_abs_x
        or co.z < lower_z - 0.0015
        or co.z > upper_z + 0.0015
        or co.y < -0.165
        or co.y > -0.025
    ):
        continue
    class_value = int(vertex[surface_class]) if surface_class is not None else 0
    if class_value in {1, 2}:
        continue
    # Select only the intended exterior/front or inferior-underbelly surface,
    # not the recessed inner/back layer of the fold.
    normal = vertex.normal
    exterior = normal.y < -0.18
    underbelly = normal.z < -0.55 and co.y < -0.095
    if not (exterior or underbelly):
        continue
    candidate_vertices.append(vertex)
    vertical = smoothstep((co.z - lower_z) / (upper_z - lower_z))
    curve_y = lower_y + (upper_y - lower_y) * vertical
    lateral = 1.0 - smoothstep(
        (abs(co.x) - full_weight_abs_x)
        / (maximum_abs_x - full_weight_abs_x)
    )
    target_y = co.y * (1.0 - lateral) + curve_y * lateral
    # Never pull an already anterior point backward.
    if co.y <= target_y:
        continue
    original_y = float(co.y)
    co.y = target_y
    delta = abs(original_y - float(co.y))
    moved.append(
        {
            "index": vertex.index,
            "coordinate_before_y": original_y,
            "coordinate_after_y": float(co.y),
            "x": float(co.x),
            "z": float(co.z),
            "normal_y": float(normal.y),
            "normal_z": float(normal.z),
        }
    )
    maximum_delta_y = max(maximum_delta_y, delta)
    if class_value in {1, 2}:
        anatomy_vertices_moved += 1

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.normal_update()
final_topology = topology_counts_bmesh(bm)
bm.to_mesh(body.data)
bm.free()
body.data.update()

body.name = BODY_OUTPUT_NAME
body["status"] = "ENGINEERING TRIAL — VISUAL REVIEW REQUIRED"
body["source_r24_sha256"] = source_sha256
body["method"] = (
    "DEFORMATION-ONLY EXISTING SURFACE FAIRING BETWEEN MEASURED "
    "PUBIC/UNDERBELLY ANCHORS"
)
body["boolean_used"] = False
body["global_remesh_used"] = False
body["faces_added_or_deleted"] = False
body["donor_surface_transferred"] = False
body["static_review_only"] = True
body["runtime_activation_allowed"] = False
body["movement_started"] = False

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

report = {
    "schema_version": 1,
    "status": body["status"],
    "source": str(SOURCE),
    "source_sha256": source_sha256,
    "output": str(BLEND_PATH),
    "method": body["method"],
    "measured_anchor_parameters": {
        "lower_z": lower_z,
        "lower_y": lower_y,
        "upper_z": upper_z,
        "upper_y": upper_y,
        "maximum_abs_x": maximum_abs_x,
        "full_weight_abs_x": full_weight_abs_x,
    },
    "candidate_vertex_count": len(candidate_vertices),
    "moved_vertex_count": len(moved),
    "maximum_delta_y_m": maximum_delta_y,
    "anatomy_branch_vertices_moved": anatomy_vertices_moved,
    "moved_vertex_sample": moved[:50],
    "baseline_topology": baseline_topology,
    "final_topology": final_topology,
    "topology_identical": baseline_topology == final_topology,
    "faces_added": 0,
    "faces_deleted": 0,
    "boolean_operations": 0,
    "global_remesh_operations": 0,
    "donor_surface_transferred": False,
    "radial_fan_used": False,
    "inserted_panel_used": False,
    "scope": {
        "static_review_only": True,
        "movement": False,
        "activation": False,
        "runtime_attachment": False,
        "synthetic_robert": False,
        "kira": False,
        "clothing": False,
    },
}
REPORT_PATH.write_text(
    json.dumps(report, indent=2) + "\n",
    encoding="utf-8",
)
print(BLEND_PATH)
print(json.dumps(report, indent=2))
