"""Attach one compact static anatomy form to the clean V24C pubic bridge.

This private engineering trial evaluates whether the repaired, continuous V1
surface can accept one watertight local form without the Boolean failures seen
on the older overlapping-sheet lineage.  The proportions are deliberately
compact and high-rooted, following the owner's new placement photographs while
using the authorized adult reference only for structural guidance.

The result remains rejected until front, side, three-quarter, silhouette, and
topology checks all pass.  No runtime or movement work is performed.
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
    "biological_static_likeness_v24c_superior_bridge_refinement/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_SUPERIOR_BRIDGE_REFINEMENT.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v24d_compact_anatomy_trial"
)
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_BODY = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_SUPERIOR_BRIDGE_REFINEMENT"
BODY_NAME = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24D_COMPACT_ANATOMY_TRIAL"
BLEND_PATH = OUT / f"{BODY_NAME}.blend"
REPORT_PATH = OUT / "V24D_COMPACT_ANATOMY_TRIAL_REPORT.json"


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
        "wire_edges": sum(len(edge.link_faces) == 0 for edge in bm.edges),
        "nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2 for edge in bm.edges
        ),
        "local_boundary_edges": sum(
            len(edge.link_faces) == 1
            and all(
                abs(vertex.co.x) <= 0.100
                and -0.220 <= vertex.co.y <= 0.130
                and 0.620 <= vertex.co.z <= 0.870
                for vertex in edge.verts
            )
            for edge in bm.edges
        ),
        "local_nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2
            and all(
                abs(vertex.co.x) <= 0.100
                and -0.220 <= vertex.co.y <= 0.130
                and 0.620 <= vertex.co.z <= 0.870
                for vertex in edge.verts
            )
            for edge in bm.edges
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
    bpy.data.meshes.remove(mesh)
    for modifier in obj.modifiers:
        if modifier.name in saved:
            modifier.show_viewport = saved[modifier.name]
    return result


def add_ellipsoid(
    metaball: bpy.types.MetaBall,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    stiffness: float = 2.0,
) -> None:
    element = metaball.elements.new()
    element.type = "ELLIPSOID"
    element.co = center
    element.radius = 1.0
    element.size_x = size[0]
    element.size_y = size[1]
    element.size_z = size[2]
    element.stiffness = stiffness


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get(SOURCE_BODY)
if body is None:
    raise RuntimeError("V24C clean bridge body is missing")
skin = bpy.data.materials.get("MBLab_skin3")
if skin is None:
    raise RuntimeError("V1-derived skin material is missing")

raw_before = mesh_counts(body.data)

metaball = bpy.data.metaballs.new("V24D_Compact_Local_Adult_Form")
metaball.threshold = 0.78
metaball.resolution = 0.0025
metaball.render_resolution = 0.0020
meta_object = bpy.data.objects.new("V24D_Compact_Local_Adult_Form", metaball)
bpy.context.collection.objects.link(meta_object)

elements = [
    # Buried superior root: closes into V24C rather than sitting below it.
    ("superior_root", (0.000, -0.082, 0.813), (0.064, 0.072, 0.048)),
    ("root_transition", (0.000, -0.104, 0.784), (0.048, 0.052, 0.038)),
    ("left_root_fillet", (-0.022, -0.111, 0.774), (0.030, 0.040, 0.033)),
    ("right_root_fillet", (0.022, -0.111, 0.774), (0.030, 0.040, 0.033)),
    # Connected perineal/scrotal envelope behind the shaft.
    ("perineal_transition", (0.000, -0.088, 0.746), (0.038, 0.038, 0.037)),
    ("scrotal_upper", (0.000, -0.111, 0.753), (0.035, 0.036, 0.031)),
    ("scrotal_left", (-0.015, -0.116, 0.721), (0.026, 0.030, 0.038)),
    ("scrotal_right", (0.015, -0.115, 0.718), (0.026, 0.030, 0.039)),
    ("scrotal_lower", (0.000, -0.112, 0.697), (0.027, 0.028, 0.025)),
    # Compact neutral shaft, kept forward of the scrotal envelope.
    ("shaft_root", (0.000, -0.143, 0.779), (0.022, 0.028, 0.025)),
    ("shaft_proximal", (0.000, -0.157, 0.760), (0.020, 0.025, 0.024)),
    ("shaft_mid", (0.000, -0.167, 0.741), (0.018, 0.023, 0.023)),
    ("shaft_distal", (0.000, -0.174, 0.722), (0.017, 0.021, 0.021)),
    ("coronal_flare", (0.000, -0.177, 0.709), (0.021, 0.023, 0.018)),
    ("glans", (0.000, -0.176, 0.697), (0.020, 0.022, 0.020)),
]
for _, center, size in elements:
    add_ellipsoid(metaball, center, size)

bpy.context.view_layer.objects.active = meta_object
meta_object.select_set(True)
bpy.ops.object.convert(target="MESH")
anatomy = bpy.context.object
anatomy.name = "V24D_SINGLE_WATERTIGHT_COMPACT_ADULT_FORM"
anatomy.data.materials.append(skin)
for polygon in anatomy.data.polygons:
    polygon.use_smooth = True
anatomy_counts = mesh_counts(anatomy.data)

# Place the single union before subdivision/displacement so later surface
# modifiers do not manufacture hundreds of intersection edges.
bpy.context.view_layer.objects.active = body
body.select_set(True)
union = body.modifiers.new("V24D_Compact_Adult_Form_Union", "BOOLEAN")
union.operation = "UNION"
union.solver = "EXACT"
union.object = anatomy
while list(body.modifiers).index(union) > 2:
    bpy.ops.object.modifier_move_up(modifier=union.name)
anatomy.hide_render = True
anatomy.hide_set(True)

low_evaluated = evaluated_counts(body, disable_late_surface=True)
full_evaluated = evaluated_counts(body, disable_late_surface=False)

body.name = BODY_NAME
body["status"] = (
    "REJECTED ENGINEERING TRIAL — VISUAL/TOPOLOGY VALIDATION REQUIRED"
)
body["source_authority"] = "V24C CLEAN V1-DERIVED CONTINUOUS PUBIC BRIDGE"
body["anatomy_method"] = (
    "ONE WATERTIGHT COMPACT ORGANIC FORM; ONE LIVE EXACT UNION BEFORE SUBDIVISION"
)
body["private_reference_use"] = (
    "PLACEMENT/PROPORTION GUIDANCE; PRESERVE UNTIL EXPLICIT OWNER APPROVAL"
)
body["owner_approved"] = False
body["movement_started"] = False
body["runtime_activation_allowed"] = False

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
report = {
    "schema": "kira.avatar.biological_robert.v24d.compact_trial.v1",
    "status": body["status"],
    "source": str(SOURCE),
    "source_sha256": sha256(SOURCE),
    "output": str(BLEND_PATH),
    "output_sha256": sha256(BLEND_PATH),
    "reference_handling": {
        "private_owner_references": r"C:\Users\robmc\Desktop\reference",
        "used_for": [
            "high root placement beneath abdomen",
            "bounded external projection",
            "relationship to upper thighs",
        ],
        "deletion": "ONLY AFTER EXPLICIT OWNER APPROVAL",
    },
    "authored_elements": [
        {"name": name, "center_m": list(center), "size_m": list(size)}
        for name, center, size in elements
    ],
    "topology": {
        "body_raw_before": raw_before,
        "single_form": anatomy_counts,
        "low_evaluated_union": low_evaluated,
        "full_evaluated_union": full_evaluated,
        "union_position": list(body.modifiers).index(union),
        "union_count": 1,
    },
    "truthful_gate": {
        "static_owner_review_candidate": False,
        "diagnostics_required": [
            "front",
            "side",
            "three-quarter",
            "silhouette",
            "wireframe",
        ],
        "reject_if": [
            "superior notch remains",
            "schematic/hourglass silhouette",
            "shaft/scrotum merge is visually wrong",
            "side projection is detached or too low",
            "local boundary/nonmanifold topology is not clean",
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
