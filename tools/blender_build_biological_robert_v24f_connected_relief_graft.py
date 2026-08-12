"""Create a bounded, one-surface anatomy graft on the clean V24C bridge.

This private Stage-A engineering trial replaces the flat ten-sided bridge fill
with a locally subdivided continuation of the *same* body mesh.  The surface is
then shaped as a compact adult-male relief with a high pubic root, continuous
pelvic transition, short neutral shaft/glans relationship, and compact
bilateral scrotal/perineal transition.

It intentionally avoids donor-body transfer, floating components, metaballs,
and Boolean overlap.  The candidate remains rejected until neutral front,
side, three-quarter, silhouette, and topology evidence all pass.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


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
    "biological_static_likeness_v24f_connected_relief_graft_trial"
)
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_BODY = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_SUPERIOR_BRIDGE_REFINEMENT"
BODY_NAME = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24F_CONNECTED_RELIEF_GRAFT_TRIAL"
BLEND_PATH = OUT / f"{BODY_NAME}.blend"
REPORT_PATH = OUT / "V24F_CONNECTED_RELIEF_GRAFT_REPORT.json"

# These are the eight V24B fill triangles, unchanged by the one-vertex V24C
# refinement.  No surrounding thigh, abdomen, face, hand, or hair face is
# included.
PATCH_FACE_INDICES = [10502, 10506, 10547, 10714, 10721, 10724, 10726, 10727]

# The original ten-edge shield boundary in x/z projection, updated with the
# V24C superior point.  This is used only to keep the sculpt strictly inside
# the repaired bridge.
PATCH_BOUNDARY_XZ = [
    (0.0, 0.6793043),
    (-0.0396497, 0.6873205),
    (-0.0355907, 0.7234631),
    (-0.0355455, 0.7588530),
    (-0.0372957, 0.7867661),
    (0.0, 0.8315000),
    (0.0372957, 0.7867661),
    (0.0355455, 0.7588530),
    (0.0355907, 0.7234631),
    (0.0396497, 0.6873205),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def topology(mesh: bpy.types.Mesh) -> dict[str, int]:
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
                abs(vertex.co.x) <= 0.080
                and -0.260 <= vertex.co.y <= 0.050
                and 0.630 <= vertex.co.z <= 0.860
                for vertex in edge.verts
            )
            for edge in bm.edges
        ),
        "local_nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2
            and all(
                abs(vertex.co.x) <= 0.080
                and -0.260 <= vertex.co.y <= 0.050
                and 0.630 <= vertex.co.z <= 0.860
                for vertex in edge.verts
            )
            for edge in bm.edges
        ),
    }
    bm.free()
    return result


def point_in_polygon(x: float, z: float) -> bool:
    inside = False
    count = len(PATCH_BOUNDARY_XZ)
    for index in range(count):
        x1, z1 = PATCH_BOUNDARY_XZ[index]
        x2, z2 = PATCH_BOUNDARY_XZ[(index + 1) % count]
        crosses = (z1 > z) != (z2 > z)
        if not crosses:
            continue
        crossing_x = x1 + (x2 - x1) * (z - z1) / (z2 - z1)
        if x < crossing_x:
            inside = not inside
    return inside


def segment_distance(
    x: float,
    z: float,
    a: tuple[float, float],
    b: tuple[float, float],
) -> float:
    ax, az = a
    bx, bz = b
    vx, vz = bx - ax, bz - az
    wx, wz = x - ax, z - az
    length_squared = vx * vx + vz * vz
    if length_squared <= 1e-12:
        return math.hypot(wx, wz)
    t = max(0.0, min(1.0, (wx * vx + wz * vz) / length_squared))
    return math.hypot(x - (ax + t * vx), z - (az + t * vz))


def boundary_blend(x: float, z: float) -> float:
    distance = min(
        segment_distance(
            x,
            z,
            PATCH_BOUNDARY_XZ[index],
            PATCH_BOUNDARY_XZ[(index + 1) % len(PATCH_BOUNDARY_XZ)],
        )
        for index in range(len(PATCH_BOUNDARY_XZ))
    )
    # Preserve the exact V24C boundary while reaching full form within 14 mm.
    t = max(0.0, min(1.0, distance / 0.014))
    return t * t * (3.0 - 2.0 * t)


def gaussian(
    x: float,
    z: float,
    center_x: float,
    center_z: float,
    sigma_x: float,
    sigma_z: float,
) -> float:
    return math.exp(
        -0.5
        * (
            ((x - center_x) / sigma_x) ** 2
            + ((z - center_z) / sigma_z) ** 2
        )
    )


def relief_depth(x: float, z: float) -> float:
    """Return forward (-Y) displacement in metres.

    The functions overlap smoothly, so the root, shaft, glans, scrotal
    envelope, and perineal transition remain one connected surface rather than
    separate pasted-on objects.
    """

    # Broad high-root blend directly beneath the abdomen/pubic transition.
    root = 0.036 * gaussian(x, z, 0.0, 0.798, 0.026, 0.030)

    # Short neutral shaft with a mild forward emphasis through its middle.
    shaft_upper = 0.055 * gaussian(x, z, 0.0, 0.773, 0.0135, 0.029)
    shaft_lower = 0.070 * gaussian(x, z, 0.0, 0.735, 0.0130, 0.028)

    # Modest coronal/glans expansion.  It is deliberately oval, not spherical.
    coronal = 0.074 * gaussian(x, z, 0.0, 0.710, 0.0175, 0.015)
    glans_tip = 0.060 * gaussian(x, z, 0.0, 0.697, 0.0155, 0.014)

    # Compact bilateral scrotal envelope behind and lateral to the shaft.
    scrotal_left = 0.045 * gaussian(x, z, -0.015, 0.704, 0.015, 0.024)
    scrotal_right = 0.045 * gaussian(x, z, 0.015, 0.704, 0.015, 0.024)
    scrotal_upper = 0.028 * gaussian(x, z, 0.0, 0.731, 0.026, 0.024)
    perineal = 0.020 * gaussian(x, z, 0.0, 0.686, 0.021, 0.013)

    # A shallow central raphe/cleft reduces the fused single-blob reading while
    # retaining a continuous skin surface.
    center_relief = 0.007 * gaussian(x, z, 0.0, 0.704, 0.0045, 0.026)

    # Use smooth maximum-like accumulation: overlapping structures reinforce
    # one form without the extreme hourglass/tentacle depths of rejected trials.
    shaft_form = max(root, shaft_upper, shaft_lower, coronal, glans_tip)
    scrotal_form = max(scrotal_left, scrotal_right, scrotal_upper, perineal)
    combined = shaft_form + 0.72 * scrotal_form - center_relief
    return max(0.0, combined)


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get(SOURCE_BODY)
if body is None:
    raise RuntimeError("V24C clean bridge body is missing")

before = topology(body.data)
bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

patch_faces = [bm.faces[index] for index in PATCH_FACE_INDICES]
if len(patch_faces) != 8:
    raise RuntimeError("expected all eight V24C bridge faces")

patch_edges = {edge for face in patch_faces for edge in face.edges}
bmesh.ops.subdivide_edges(
    bm,
    edges=list(patch_edges),
    cuts=8,
    use_grid_fill=True,
    smooth=0.0,
)
bm.normal_update()

# Some Blender subdivision paths do not propagate arbitrary face layers.
# Therefore membership is computed from the actual x/z polygon and front-side
# location.  Exact original boundary vertices are never displaced.
candidate_vertices = [
    vertex
    for vertex in bm.verts
    if vertex.co.y < 0.0
    and point_in_polygon(float(vertex.co.x), float(vertex.co.z))
]

displacements: list[float] = []
for vertex in candidate_vertices:
    x = float(vertex.co.x)
    z = float(vertex.co.z)
    blend = boundary_blend(x, z)
    displacement = relief_depth(x, z) * blend
    if displacement <= 0.0:
        continue
    vertex.co.y -= displacement
    displacements.append(displacement)

bm.normal_update()
after_bmesh = {
    "vertices": len(bm.verts),
    "edges": len(bm.edges),
    "faces": len(bm.faces),
    "local_boundary_edges": sum(
        len(edge.link_faces) == 1
        and all(
            abs(vertex.co.x) <= 0.080
            and -0.260 <= vertex.co.y <= 0.050
            and 0.630 <= vertex.co.z <= 0.860
            for vertex in edge.verts
        )
        for edge in bm.edges
    ),
    "local_nonmanifold_gt2_edges": sum(
        len(edge.link_faces) > 2
        and all(
            abs(vertex.co.x) <= 0.080
            and -0.260 <= vertex.co.y <= 0.050
            and 0.630 <= vertex.co.z <= 0.860
            for vertex in edge.verts
        )
        for edge in bm.edges
    ),
}
bm.to_mesh(body.data)
body.data.update()
bm.free()

after = topology(body.data)
body.name = BODY_NAME
body["status"] = (
    "REJECTED ENGINEERING TRIAL — CONNECTED RELIEF REQUIRES VISUAL REVIEW"
)
body["source_authority"] = "V24C CLEAN V1-DERIVED CONTINUOUS PUBIC BRIDGE"
body["anatomy_method"] = (
    "SAME-MESH LOCAL SUBDIVISION AND BOUNDED RELIEF; NO DONOR TRANSFER; "
    "NO BOOLEAN; NO FLOATING COMPONENT"
)
body["private_reference_use"] = (
    "ROBERT-SPECIFIC PLACEMENT/PROPORTION ONLY; PRESERVE UNTIL OWNER APPROVAL"
)
body["owner_approved"] = False
body["movement_started"] = False
body["runtime_activation_allowed"] = False

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
report = {
    "schema": "kira.avatar.biological_robert.v24f.connected_relief.v1",
    "status": body["status"],
    "source": str(SOURCE),
    "source_sha256": sha256(SOURCE),
    "output": str(BLEND_PATH),
    "output_sha256": sha256(BLEND_PATH),
    "construction": {
        "patch_face_indices": PATCH_FACE_INDICES,
        "subdivision_cuts": 8,
        "candidate_vertices": len(candidate_vertices),
        "displaced_vertices": len(displacements),
        "maximum_forward_displacement_m": (
            max(displacements) if displacements else 0.0
        ),
        "mean_forward_displacement_m": (
            sum(displacements) / len(displacements) if displacements else 0.0
        ),
        "separate_anatomy_objects": 0,
        "booleans": 0,
        "metaballs": 0,
    },
    "topology": {
        "before": before,
        "after_bmesh": after_bmesh,
        "after": after,
        "local_boundary_clean": after["local_boundary_edges"] == 0,
        "local_nonmanifold_clean": (
            after["local_nonmanifold_gt2_edges"] == 0
        ),
    },
    "reference_handling": {
        "private_owner_references": r"C:\Users\robmc\Desktop\reference",
        "used_for": [
            "high root placement",
            "compact neutral scale",
            "relationship to upper thighs and abdomen",
        ],
        "retention": "PRESERVE UNTIL EXPLICIT OWNER APPROVAL",
        "generic_avatar_template_use": False,
    },
    "truthful_gate": {
        "static_owner_review_candidate": False,
        "required_diagnostics": [
            "neutral front",
            "neutral side",
            "neutral three-quarter",
            "silhouette",
            "wireframe",
        ],
        "reject_if": [
            "superior or lateral gap",
            "buried or flattened anatomy",
            "hourglass/tentacle/schematic silhouette",
            "unnatural low placement",
            "local boundary or >2-face topology regression",
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
