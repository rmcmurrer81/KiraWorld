"""Build the clean V1-based Biological Robert static engineering substrate.

The V14--V23 lineage is no longer a valid repair substrate because the exact
union baked several closed overlapping pelvis/root sheets into the body.  This
builder returns to the owner-preferred V1 dominant mesh, explicitly excludes
the four separate V1 external-anatomy estimates, applies only the bounded V15
below-neck slimming formulas, and appends the removable dark-blond static
review hair as separate objects.

This file deliberately contains no adult-anatomy attachment yet.  It is a
clean static substrate for a later single-surface local reconstruction, not an
owner-review candidate and not a runtime body.
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
HAIR_SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v19_from_v18/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V19_FROM_V18.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v24_clean_v1_rebase"
)
OUT.mkdir(parents=True, exist_ok=True)
BODY_NAME = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24_CLEAN_V1_REBASE"
BLEND_PATH = OUT / f"{BODY_NAME}.blend"
REPORT_PATH = OUT / "V24_CLEAN_V1_REBASE_REPORT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def topology_counts(obj: bpy.types.Object):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    result = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges": sum(len(edge.link_faces) == 1 for edge in bm.edges),
        "wire_edges": sum(len(edge.link_faces) == 0 for edge in bm.edges),
        "nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2 for edge in bm.edges
        ),
        "local_pelvis_boundary_edges": sum(
            len(edge.link_faces) == 1
            and all(
                abs(vertex.co.x) <= 0.080
                and -0.200 <= vertex.co.y <= 0.130
                and 0.620 <= vertex.co.z <= 0.850
                for vertex in edge.verts
            )
            for edge in bm.edges
        ),
        "local_pelvis_nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2
            and all(
                abs(vertex.co.x) <= 0.080
                and -0.200 <= vertex.co.y <= 0.130
                and 0.620 <= vertex.co.z <= 0.850
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
    raise RuntimeError("owner-preferred V1 body is missing")

removed_objects = []
for obj in list(bpy.data.objects):
    if obj is body:
        continue
    if any(
        token in obj.name
        for token in (
            "External_Anatomy_ESTIMATED",
            "Separate_Brown_Iris",
            "Separate_Pupil",
        )
    ):
        removed_objects.append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)

baseline = topology_counts(body)

# Reapply only the bounded V15 slimming pass.  The V15 local anatomy modifier
# is intentionally omitted because it operated on the defective V14 union.
slimmed_vertices = 0
zone_counts = {
    "below_neck_baseline": 0,
    "abdomen_waist": 0,
    "chest": 0,
    "thighs": 0,
    "upper_arms": 0,
}
for vertex in body.data.vertices:
    co = vertex.co
    if co.z >= 1.58:
        continue
    slimmed_vertices += 1
    zone_counts["below_neck_baseline"] += 1
    co.x *= 0.982
    co.y *= 0.975
    if 0.76 <= co.z <= 1.22:
        co.x *= 0.978
        co.y *= 0.970
        zone_counts["abdomen_waist"] += 1
    elif 1.22 < co.z <= 1.53:
        co.x *= 0.988
        co.y *= 0.985
        zone_counts["chest"] += 1
    if 0.40 <= co.z <= 0.92 and abs(co.x) > 0.08:
        center = 0.18 if co.x > 0 else -0.18
        co.x = center + (co.x - center) * 0.965
        co.y *= 0.978
        zone_counts["thighs"] += 1
    if 1.00 <= co.z <= 1.48 and abs(co.x) > 0.24:
        center = 0.31 if co.x > 0 else -0.31
        co.x = center + (co.x - center) * 0.965
        co.y *= 0.978
        zone_counts["upper_arms"] += 1
body.data.update()

# Append only the removable static-review dark-blond hair meshes.  They remain
# separate from the body and are not represented as a completed runtime groom.
with bpy.data.libraries.load(str(HAIR_SOURCE), link=False) as (
    source_data,
    target_data,
):
    target_data.objects = [
        name for name in ("Object_6", "Object_7") if name in source_data.objects
    ]
hair_objects = []
for index, hair in enumerate(target_data.objects, start=1):
    if hair is None:
        continue
    bpy.context.collection.objects.link(hair)
    hair.name = f"Robert_Removable_Dark_Blond_Static_Hair_V24_{index:02d}"
    hair["component_type"] = "REMOVABLE_STATIC_REVIEW_HAIR"
    hair["runtime_hair_system_complete"] = False
    hair["runtime_approved"] = False
    hair["owner_approved"] = False
    hair_objects.append(hair.name)

body.name = BODY_NAME
body["status"] = (
    "REJECTED ENGINEERING SUBSTRATE — CLEAN V1 BODY; ANATOMY NOT ATTACHED"
)
body["source_authority"] = "OWNER-PREFERRED V1 DOMINANT BODY"
body["excluded_v1_external_anatomy_objects"] = True
body["v14_through_v23_union_lineage_rejected_as_substrate"] = True
body["slimming_pass"] = "BOUNDED V15 BELOW-NECK FORMULAS ONLY"
body["face_and_head_modified"] = False
body["skin_material_replaced"] = False
body["hair_status"] = (
    "REMOVABLE DARK-BLOND STATIC REVIEW COMPONENT — RUNTIME GROOM INCOMPLETE"
)
body["anatomy_status"] = "NOT ATTACHED — CLEAN RECONSTRUCTION REQUIRED"
body["runtime_activation_allowed"] = False
body["movement_started"] = False
body["owner_approved"] = False

for obj in bpy.data.objects:
    if obj.type == "ARMATURE":
        obj.hide_render = True

final = topology_counts(body)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

report = {
    "schema": "kira.avatar.biological_robert.clean_v1_rebase.v1",
    "status": body["status"],
    "source": str(SOURCE),
    "source_sha256": sha256(SOURCE),
    "output": str(BLEND_PATH),
    "output_sha256": sha256(BLEND_PATH),
    "removed_objects": removed_objects,
    "removed_external_anatomy_count": sum(
        "External_Anatomy_ESTIMATED" in name for name in removed_objects
    ),
    "removed_separate_brown_eye_review_objects": sum(
        "Separate_Brown_Iris" in name or "Separate_Pupil" in name
        for name in removed_objects
    ),
    "slimming": {
        "authority": "V15 bounded below-neck formulas",
        "slimmed_vertices": slimmed_vertices,
        "zone_counts": zone_counts,
        "head_face_z_threshold_meters": 1.58,
        "head_face_vertices_changed": 0,
        "defective_v15_local_anatomy_block_reused": False,
    },
    "hair": {
        "source": str(HAIR_SOURCE),
        "objects": hair_objects,
        "separate_from_body": True,
        "runtime_hair_complete": False,
        "owner_approved": False,
    },
    "topology": {
        "baseline": baseline,
        "final": final,
        "identical": baseline == final,
    },
    "truthful_gate": {
        "adult_anatomy_attached": False,
        "static_owner_review_candidate": False,
        "runtime_candidate": False,
        "next_required_work": (
            "single-surface local pelvis/anatomy reconstruction on this "
            "clean substrate"
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
