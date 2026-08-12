"""Prepare a private static clean-V1 substrate diagnostic.

The final V1 likeness mesh is retained exactly.  The four historical separate
anatomy primitives and duplicate review-eye overlays are excluded so the
pelvis surface can be judged before a new adult local topology is authored.
This does not create a candidate and does not alter the V1 source.
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
    "biological_static_likeness_v1/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_r26_clean_v1_substrate_diagnostic"
)
OUT.mkdir(parents=True, exist_ok=True)
BLEND = OUT / "BIOLOGICAL_ROBERT_V1_CLEAN_PELVIS_SUBSTRATE_DIAGNOSTIC.blend"
REPORT = OUT / "CLEAN_V1_SUBSTRATE_REPORT.json"


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
        "local_pelvis_boundary_edges": sum(
            len(edge.link_faces) == 1
            and all(
                abs(vertex.co.x) <= 0.10
                and -0.20 <= vertex.co.y <= 0.12
                and 0.60 <= vertex.co.z <= 0.88
                for vertex in edge.verts
            )
            for edge in bm.edges
        ),
        "local_pelvis_nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2
            and all(
                abs(vertex.co.x) <= 0.10
                and -0.20 <= vertex.co.y <= 0.12
                and 0.60 <= vertex.co.z <= 0.88
                for vertex in edge.verts
            )
            for edge in bm.edges
        ),
    }
    bm.free()
    return result


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1")
if body is None:
    raise RuntimeError("final V1 likeness body is missing")

removed = []
for obj in list(bpy.context.scene.objects):
    if obj is body:
        continue
    if (
        "External_Anatomy_ESTIMATED" in obj.name
        or "Separate_Brown_Iris" in obj.name
        or "Separate_Pupil" in obj.name
        or "Separate_Eyeball" in obj.name
    ):
        removed.append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)

body.name = "BIOLOGICAL_ROBERT_V1_CLEAN_PELVIS_SUBSTRATE_DIAGNOSTIC"
body["status"] = "DIAGNOSTIC ONLY - NOT A BODY CANDIDATE"
body["runtime_activation_allowed"] = False
body["movement_started"] = False
body["adult_anatomy_complete"] = False
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

report = {
    "schema": "kira.avatar.clean_v1_pelvis_substrate.v1",
    "status": body["status"],
    "source": str(SOURCE),
    "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "output": str(BLEND),
    "excluded_objects": removed,
    "body_topology": topology(body),
    "purpose": (
        "Preserve the owner-preferred V1 face/skin while removing historical "
        "separate overlapping anatomy primitives before the next bounded "
        "pubic-to-root reconstruction."
    ),
    "scope": {
        "diagnostic_only": True,
        "static_only": True,
        "movement": False,
        "activation": False,
        "runtime_attachment": False,
        "synthetic_robert": False,
        "kira": False,
        "clothing": False,
    },
}
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(BLEND)
print(json.dumps(report, indent=2))
