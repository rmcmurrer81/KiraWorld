"""Build a bounded organic pelvis/anatomy-root trial on the clean V24 rebase.

This is a private static engineering trial.  It deliberately starts from the
clean V1-derived V24 substrate and does not reuse any V14--V23 exact-union
pelvis geometry.  One watertight implicit local form is authored, converted to
a mesh, and unioned once with the preserved body.  The local form is guided by
the owner's newly supplied placement photographs and the authorized adult
anatomy reference, but it does not transfer another model's body, face, skin,
or identity.

The result remains rejected evidence until front, side, and three-quarter
diagnostics prove that it has no tunnel, shelf, seam, floating piece, or
schematic silhouette.
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
    "biological_static_likeness_v24_clean_v1_rebase/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24_CLEAN_V1_REBASE.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v24a_organic_root_trial"
)
OUT.mkdir(parents=True, exist_ok=True)
BODY_SOURCE_NAME = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24_CLEAN_V1_REBASE"
BODY_NAME = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24A_ORGANIC_ROOT_TRIAL"
BLEND_PATH = OUT / f"{BODY_NAME}.blend"
REPORT_PATH = OUT / "V24A_ORGANIC_ROOT_TRIAL_REPORT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def raw_topology(obj: bpy.types.Object) -> dict[str, int]:
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
    }
    bm.free()
    return result


def evaluated_topology(obj: bpy.types.Object) -> dict[str, int]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(
        evaluated, preserve_all_data_layers=True, depsgraph=depsgraph
    )
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
        "local_pelvis_boundary_edges": sum(
            len(edge.link_faces) == 1
            and all(
                abs(vertex.co.x) <= 0.100
                and -0.220 <= vertex.co.y <= 0.130
                and 0.600 <= vertex.co.z <= 0.850
                for vertex in edge.verts
            )
            for edge in bm.edges
        ),
        "local_pelvis_nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2
            and all(
                abs(vertex.co.x) <= 0.100
                and -0.220 <= vertex.co.y <= 0.130
                and 0.600 <= vertex.co.z <= 0.850
                for vertex in edge.verts
            )
            for edge in bm.edges
        ),
    }
    bm.free()
    bpy.data.meshes.remove(mesh)
    return result


def add_ellipsoid(
    metaball: bpy.types.MetaBall,
    *,
    name: str,
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
    # Element names are not supported, so keep the authored inventory below.


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get(BODY_SOURCE_NAME)
if body is None:
    raise RuntimeError("clean V24 V1-derived body is missing")

skin = bpy.data.materials.get("MBLab_skin3")
if skin is None:
    raise RuntimeError("preserved V1 skin material is missing")

raw_before = raw_topology(body)

# Build one coherent implicit form.  The broad, shallow superior elements
# overlap the existing pubic surface and close the inherited triangular
# silhouette without creating a collar.  The scrotal envelope remains behind
# the compact neutral shaft; the glans is only modestly wider than the distal
# shaft.  Every element overlaps the next so conversion produces one closed
# component before the body union.
metaball = bpy.data.metaballs.new("V24A_Organic_Local_Adult_Form")
metaball.threshold = 0.72
metaball.resolution = 0.0028
metaball.render_resolution = 0.0022
meta_object = bpy.data.objects.new(
    "V24A_Organic_Local_Adult_Form", metaball
)
bpy.context.collection.objects.link(meta_object)

elements = [
    # Superior pubic/root transition: broad but shallow, buried into V1.
    ("superior_pubic_mound", (0.000, -0.060, 0.773), (0.060, 0.058, 0.047), 2.0),
    ("inferior_pubic_bridge", (0.000, -0.083, 0.736), (0.046, 0.052, 0.043), 2.0),
    ("left_root_fillet", (-0.024, -0.092, 0.731), (0.031, 0.042, 0.037), 2.0),
    ("right_root_fillet", (0.024, -0.092, 0.731), (0.031, 0.042, 0.037), 2.0),
    # Perineal and scrotal transition, kept behind the shaft.
    ("perineal_bridge", (0.000, -0.073, 0.695), (0.044, 0.042, 0.042), 2.0),
    ("scrotal_upper_bridge", (0.000, -0.101, 0.708), (0.038, 0.039, 0.035), 2.0),
    ("scrotal_left", (-0.017, -0.111, 0.675), (0.029, 0.033, 0.046), 2.0),
    ("scrotal_right", (0.017, -0.110, 0.672), (0.029, 0.033, 0.047), 2.0),
    ("scrotal_lower_bridge", (0.000, -0.106, 0.654), (0.029, 0.030, 0.029), 2.0),
    # Compact neutral shaft, flowing continuously downward and forward.
    ("shaft_root", (0.000, -0.119, 0.733), (0.024, 0.030, 0.029), 2.0),
    ("shaft_proximal", (0.000, -0.132, 0.715), (0.021, 0.026, 0.027), 2.0),
    ("shaft_mid", (0.000, -0.145, 0.695), (0.019, 0.024, 0.026), 2.0),
    ("shaft_distal", (0.000, -0.154, 0.674), (0.018, 0.022, 0.024), 2.0),
    ("coronal_flare", (0.000, -0.158, 0.657), (0.022, 0.024, 0.020), 2.0),
    ("glans", (0.000, -0.157, 0.643), (0.021, 0.023, 0.021), 2.0),
]
for element_name, center, size, stiffness in elements:
    add_ellipsoid(
        metaball,
        name=element_name,
        center=center,
        size=size,
        stiffness=stiffness,
    )

# Convert the implicit union to a single watertight mesh before it touches the
# body.  This prevents stacked primitive shells from entering the result.
bpy.context.view_layer.objects.active = meta_object
meta_object.select_set(True)
bpy.ops.object.convert(target="MESH")
anatomy = bpy.context.object
anatomy.name = "V24A_SINGLE_WATERTIGHT_LOCAL_ADULT_FORM"
anatomy.data.materials.append(skin)
for polygon in anatomy.data.polygons:
    polygon.use_smooth = True
anatomy["source_guidance"] = (
    "OWNER PRIVATE PLACEMENT REFERENCES + AUTHORIZED ADULT ANATOMY REFERENCE"
)
anatomy["another_identity_surface_transferred"] = False
anatomy["runtime_approved"] = False
anatomy["owner_approved"] = False
anatomy_topology = raw_topology(anatomy)

# One body union only.  Keep the modifier live for the engineering trial so
# the accepted V1 body data, UVs, and materials remain recoverable.  The local
# source form is hidden from render, ensuring the diagnostic images show the
# evaluated union rather than stacked surfaces.
bpy.context.view_layer.objects.active = body
body.select_set(True)
union = body.modifiers.new("V24A_Single_Local_Adult_Form_Union", "BOOLEAN")
union.operation = "UNION"
union.solver = "EXACT"
union.object = anatomy
anatomy.hide_render = True
anatomy.hide_set(True)

body.name = BODY_NAME
body["status"] = (
    "REJECTED ENGINEERING TRIAL — VISUAL DIAGNOSTICS REQUIRED"
)
body["source_authority"] = "CLEAN V1-DERIVED V24 SUBSTRATE"
body["anatomy_method"] = (
    "ONE WATERTIGHT ORGANIC LOCAL FORM; ONE LIVE EXACT BODY UNION"
)
body["private_reference_use"] = (
    "PLACEMENT/PROPORTION GUIDANCE ONLY; DELETE ONLY AFTER OWNER APPROVAL"
)
body["v14_through_v23_union_lineage_reused"] = False
body["movement_started"] = False
body["runtime_activation_allowed"] = False
body["owner_approved"] = False

evaluated_after = evaluated_topology(body)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

report = {
    "schema": "kira.avatar.biological_robert.v24a.organic_root_trial.v1",
    "status": body["status"],
    "source": str(SOURCE),
    "source_sha256": sha256(SOURCE),
    "output": str(BLEND_PATH),
    "output_sha256": sha256(BLEND_PATH),
    "reference_handling": {
        "owner_private_folder": r"C:\Users\robmc\Desktop\reference",
        "used_for": [
            "superior root placement",
            "relationship to belly and upper thighs",
            "bounded overall proportions",
        ],
        "another_model_identity_or_body_transferred": False,
        "deletion": "DEFERRED UNTIL EXPLICIT OWNER APPROVAL",
    },
    "authored_elements": [
        {
            "name": name,
            "center_m": list(center),
            "size_m": list(size),
            "stiffness": stiffness,
        }
        for name, center, size, stiffness in elements
    ],
    "topology": {
        "body_raw_before": raw_before,
        "single_local_form_before_union": anatomy_topology,
        "evaluated_body_after_live_union": evaluated_after,
        "union_count": 1,
        "local_source_closed_before_union": (
            anatomy_topology["boundary_edges"] == 0
            and anatomy_topology["nonmanifold_gt2_edges"] == 0
        ),
    },
    "truthful_gate": {
        "static_owner_review_candidate": False,
        "visual_diagnostics_required": [
            "front",
            "side",
            "three-quarter",
            "wireframe",
            "silhouette tunnel check",
        ],
        "automatic_rejection_conditions": [
            "tunnel",
            "shelf",
            "seam",
            "floating piece",
            "schematic silhouette",
            "incorrect side projection",
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
