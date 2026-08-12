"""Correct V24D's buried side projection without lowering its root.

V24D proved a clean one-union topology on the repaired V24C body, but the
visible form remained buried inside the upper-thigh silhouette.  This bounded
static trial keeps the superior attachment fixed and progressively advances
the lower local form toward the front (-Y).  It does not change body identity,
face, hair, movement, or runtime state.
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
    "biological_static_likeness_v24d_compact_anatomy_trial/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24D_COMPACT_ANATOMY_TRIAL.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v24e_external_projection_trial"
)
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_BODY = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24D_COMPACT_ANATOMY_TRIAL"
BODY_NAME = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24E_EXTERNAL_PROJECTION_TRIAL"
ANATOMY_NAME = "V24D_SINGLE_WATERTIGHT_COMPACT_ADULT_FORM"
BLEND_PATH = OUT / f"{BODY_NAME}.blend"
REPORT_PATH = OUT / "V24E_EXTERNAL_PROJECTION_TRIAL_REPORT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def mesh_counts(mesh: bpy.types.Mesh) -> dict[str, int]:
    bm = bmesh.new()
    bm.from_mesh(mesh)
    result = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges": sum(len(edge.link_faces) == 1 for edge in bm.edges),
        "nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2 for edge in bm.edges
        ),
    }
    bm.free()
    return result


def evaluated_counts(
    obj: bpy.types.Object, *, disable_late_surface: bool
) -> dict[str, int]:
    saved = {}
    if disable_late_surface:
        for modifier in obj.modifiers:
            if modifier.type in {"SUBSURF", "DISPLACE"}:
                saved[modifier.name] = modifier.show_viewport
                modifier.show_viewport = False
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(
        evaluated, preserve_all_data_layers=True, depsgraph=depsgraph
    )
    result = mesh_counts(mesh)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    result["local_boundary_edges"] = sum(
        len(edge.link_faces) == 1
        and all(
            abs(vertex.co.x) <= 0.100
            and -0.300 <= vertex.co.y <= 0.130
            and 0.620 <= vertex.co.z <= 0.870
            for vertex in edge.verts
        )
        for edge in bm.edges
    )
    result["local_nonmanifold_gt2_edges"] = sum(
        len(edge.link_faces) > 2
        and all(
            abs(vertex.co.x) <= 0.100
            and -0.300 <= vertex.co.y <= 0.130
            and 0.620 <= vertex.co.z <= 0.870
            for vertex in edge.verts
        )
        for edge in bm.edges
    )
    bm.free()
    bpy.data.meshes.remove(mesh)
    for modifier in obj.modifiers:
        if modifier.name in saved:
            modifier.show_viewport = saved[modifier.name]
    return result


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get(SOURCE_BODY)
anatomy = bpy.data.objects.get(ANATOMY_NAME)
if body is None or anatomy is None:
    raise RuntimeError("V24D body or its single local form is missing")

before_bounds = [
    [min(vertex.co[index] for vertex in anatomy.data.vertices) for index in range(3)],
    [max(vertex.co[index] for vertex in anatomy.data.vertices) for index in range(3)],
]
changed = 0
max_shift = 0.0
for vertex in anatomy.data.vertices:
    z = vertex.co.z
    # Keep the buried superior attachment effectively fixed.  Advance the
    # lower envelope gradually, reaching the full 75 mm correction below the
    # compact shaft/scrotal midline.
    if z >= 0.830:
        weight = 0.0
    elif z >= 0.790:
        weight = (0.830 - z) / 0.040 * 0.42
    elif z >= 0.740:
        weight = 0.42 + (0.790 - z) / 0.050 * 0.58
    else:
        weight = 1.0
    shift = 0.075 * max(0.0, min(1.0, weight))
    if shift > 0:
        vertex.co.y -= shift
        changed += 1
        max_shift = max(max_shift, shift)
anatomy.data.update()

after_bounds = [
    [min(vertex.co[index] for vertex in anatomy.data.vertices) for index in range(3)],
    [max(vertex.co[index] for vertex in anatomy.data.vertices) for index in range(3)],
]
local_form_topology = mesh_counts(anatomy.data)
low_union = evaluated_counts(body, disable_late_surface=True)
full_union = evaluated_counts(body, disable_late_surface=False)

body.name = BODY_NAME
body["status"] = (
    "REJECTED ENGINEERING TRIAL — EXTERNAL PROJECTION VISUAL CHECK REQUIRED"
)
body["repair"] = (
    "SUPERIOR ROOT FIXED; LOWER SINGLE FORM ADVANCED PROGRESSIVELY TOWARD FRONT"
)
body["owner_approved"] = False
body["movement_started"] = False
body["runtime_activation_allowed"] = False

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
report = {
    "schema": "kira.avatar.biological_robert.v24e.external_projection.v1",
    "status": body["status"],
    "source": str(SOURCE),
    "source_sha256": sha256(SOURCE),
    "output": str(BLEND_PATH),
    "output_sha256": sha256(BLEND_PATH),
    "bounded_projection": {
        "changed_vertices": changed,
        "maximum_forward_shift_m": max_shift,
        "superior_fixed_above_z_m": 0.830,
        "full_shift_below_z_m": 0.740,
        "before_bounds": before_bounds,
        "after_bounds": after_bounds,
    },
    "topology": {
        "single_form": local_form_topology,
        "low_evaluated_union": low_union,
        "full_evaluated_union": full_union,
    },
    "truthful_gate": {
        "static_owner_review_candidate": False,
        "reject_if": [
            "detached root",
            "flat plate silhouette",
            "schematic/hourglass form",
            "incorrect shaft/glans/scrotal relationship",
            "local topology regression",
        ],
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
