"""Build a V23 single-volume anatomy-union engineering trial.

All authored external-anatomy components are fused into one watertight voxel
surface before a single bounded exact union with the intact V1-derived body.
This tests whether the prior multi-Boolean overlaps can be eliminated without
global remeshing or donor identity transfer.
"""

from __future__ import annotations

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
    "biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_voxel_union_trial"
)
OUT.mkdir(parents=True, exist_ok=True)
BODY_SOURCE_NAME = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1"
BODY_OUTPUT_NAME = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_VOXEL_UNION_TRIAL"
BLEND_PATH = OUT / f"{BODY_OUTPUT_NAME}.blend"


def mesh_object(name, vertices, faces):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj


def ellipsoid(name, center, radii, segments=48, rings=28):
    vertices = [tuple(center + Vector((0, 0, -radii.z)))]
    faces = []
    for ring in range(1, rings):
        phi = -math.pi / 2 + math.pi * ring / rings
        cp, sp = math.cos(phi), math.sin(phi)
        for segment in range(segments):
            theta = 2 * math.pi * segment / segments
            vertices.append(
                tuple(
                    center
                    + Vector(
                        (
                            radii.x * cp * math.cos(theta),
                            radii.y * cp * math.sin(theta),
                            radii.z * sp,
                        )
                    )
                )
            )
    top = len(vertices)
    vertices.append(tuple(center + Vector((0, 0, radii.z))))
    for segment in range(segments):
        nxt = (segment + 1) % segments
        faces.append((0, 1 + nxt, 1 + segment))
    for ring in range(rings - 2):
        first = 1 + ring * segments
        second = first + segments
        for segment in range(segments):
            nxt = (segment + 1) % segments
            faces.append((first + segment, first + nxt, second + nxt, second + segment))
    last = 1 + (rings - 2) * segments
    for segment in range(segments):
        nxt = (segment + 1) % segments
        faces.append((last + segment, last + nxt, top))
    return mesh_object(name, vertices, faces)


def shaft_surface():
    centers = [
        Vector((0.0, -0.075, 0.803)),
        Vector((0.0, -0.102, 0.786)),
        Vector((0.0, -0.135, 0.767)),
        Vector((0.0, -0.157, 0.747)),
        Vector((0.0, -0.170, 0.729)),
        Vector((0.0, -0.177, 0.711)),
        Vector((0.0, -0.179, 0.701)),  # neck
        Vector((0.0, -0.180, 0.694)),  # corona
        Vector((0.0, -0.179, 0.685)),  # glans
        Vector((0.0, -0.176, 0.676)),
    ]
    radii_x = [0.043, 0.034, 0.027, 0.023, 0.021, 0.0195, 0.0185, 0.025, 0.023, 0.012]
    radii_cross = [0.034, 0.030, 0.026, 0.023, 0.021, 0.020, 0.019, 0.024, 0.022, 0.010]
    segments = 48
    vertices = []
    faces = []
    for index, center in enumerate(centers):
        if index == 0:
            tangent = (centers[1] - center).normalized()
        elif index == len(centers) - 1:
            tangent = (center - centers[index - 1]).normalized()
        else:
            tangent = (centers[index + 1] - centers[index - 1]).normalized()
        second_axis = Vector((0, -tangent.z, tangent.y)).normalized()
        for segment in range(segments):
            theta = 2 * math.pi * segment / segments
            point = (
                center
                + Vector((1, 0, 0)) * radii_x[index] * math.cos(theta)
                + second_axis * radii_cross[index] * math.sin(theta)
            )
            vertices.append(tuple(point))
    for ring in range(len(centers) - 1):
        first = ring * segments
        second = first + segments
        for segment in range(segments):
            nxt = (segment + 1) % segments
            faces.append((first + segment, first + nxt, second + nxt, second + segment))
    root = len(vertices)
    vertices.append(tuple(centers[0] + Vector((0, 0.006, 0.008))))
    tip = len(vertices)
    vertices.append(tuple(centers[-1] + Vector((0, -0.001, -0.004))))
    for segment in range(segments):
        nxt = (segment + 1) % segments
        faces.append((root, nxt, segment))
        final = (len(centers) - 1) * segments
        faces.append((tip, final + segment, final + nxt))
    return mesh_object("V23_Voxel_Shaft_Root_Glans", vertices, faces)


def topology(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    result = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges_total": sum(len(edge.link_faces) == 1 for edge in bm.edges),
        "nonmanifold_gt2_total": sum(len(edge.link_faces) > 2 for edge in bm.edges),
    }
    local_edges = [
        edge
        for edge in bm.edges
        if all(
            abs(vertex.co.x) < 0.15
            and -0.28 < vertex.co.y < 0.18
            and 0.57 < vertex.co.z < 0.92
            for vertex in edge.verts
        )
    ]
    result.update(
        {
            "local_boundary_edges": sum(len(edge.link_faces) == 1 for edge in local_edges),
            "local_nonmanifold_gt2": sum(len(edge.link_faces) > 2 for edge in local_edges),
        }
    )
    bm.free()
    return result


def ensure_normals(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get(BODY_SOURCE_NAME)
if body is None:
    raise RuntimeError("V1 body missing")
for obj in list(bpy.context.scene.objects):
    if any(
        token in obj.name
        for token in ("External_Anatomy_ESTIMATED", "Separate_Brown_Iris", "Separate_Pupil")
    ):
        bpy.data.objects.remove(obj, do_unlink=True)
for polygon in body.data.polygons:
    if polygon.material_index == 6:
        polygon.material_index = 1

skin = bpy.data.materials.get("MBLab_skin3")
if skin is None:
    raise RuntimeError("skin missing")
baseline = topology(body)

bpy.context.view_layer.objects.active = body
body.select_set(True)
for modifier in list(body.modifiers):
    if modifier.type in {"ARMATURE", "CORRECTIVE_SMOOTH"}:
        bpy.ops.object.modifier_apply(modifier=modifier.name)

parts = [
    # Broad superior transition reaches the former view-through cleft.
    ellipsoid("V23_Voxel_Pubic_Transition", Vector((0, -0.072, 0.786)), Vector((0.056, 0.048, 0.064))),
    # One continuous outer sac after voxel fusion; restrained asymmetry.
    ellipsoid("V23_Voxel_Left_Sac", Vector((-0.014, -0.122, 0.660)), Vector((0.038, 0.041, 0.059))),
    ellipsoid("V23_Voxel_Right_Sac", Vector((0.014, -0.120, 0.667)), Vector((0.037, 0.040, 0.054))),
    ellipsoid("V23_Voxel_Sac_Bridge", Vector((0, -0.116, 0.702)), Vector((0.049, 0.043, 0.047))),
    ellipsoid("V23_Voxel_Perineal_Bridge", Vector((0, -0.052, 0.689)), Vector((0.042, 0.048, 0.050))),
    shaft_surface(),
]
for part in parts:
    part.data.materials.append(skin)
    for polygon in part.data.polygons:
        polygon.material_index = 0

# Join overlapping construction parts, then voxel-remesh them once.  This
# creates one watertight construction surface and removes every internal
# intersection before body integration.
bpy.ops.object.select_all(action="DESELECT")
for part in parts:
    part.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
anatomy = bpy.context.object
anatomy.name = "V23_Single_Voxel_External_Anatomy"
anatomy.data.remesh_voxel_size = 0.0018
anatomy.data.remesh_voxel_adaptivity = 0.0
bpy.ops.object.voxel_remesh()
ensure_normals(anatomy)
for polygon in anatomy.data.polygons:
    polygon.use_smooth = True
voxel_topology = topology(anatomy)

# One and only one exact union with the body.
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
bpy.context.view_layer.objects.active = body
modifier = body.modifiers.new("V23_SINGLE_VOXEL_ANATOMY_UNION", "BOOLEAN")
modifier.operation = "UNION"
modifier.solver = "EXACT"
modifier.object = anatomy
if hasattr(modifier, "material_mode"):
    modifier.material_mode = "TRANSFER"
while list(body.modifiers).index(modifier) > 0:
    bpy.ops.object.modifier_move_up(modifier=modifier.name)
bpy.ops.object.modifier_apply(modifier=modifier.name)
bpy.data.objects.remove(anatomy, do_unlink=True)

# Bounded root smoothing only.
bm = bmesh.new()
bm.from_mesh(body.data)
root_vertices = [
    vertex
    for vertex in bm.verts
    if abs(vertex.co.x) < 0.075
    and -0.15 < vertex.co.y < 0.02
    and 0.715 < vertex.co.z < 0.85
]
for _ in range(5):
    bmesh.ops.smooth_vert(
        bm,
        verts=root_vertices,
        factor=0.12,
        use_axis_x=True,
        use_axis_y=True,
        use_axis_z=True,
    )
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(body.data)
bm.free()

for modifier in list(body.modifiers):
    if modifier.type == "DISPLACE":
        bpy.ops.object.modifier_remove(modifier=modifier.name)
    else:
        bpy.ops.object.modifier_apply(modifier=modifier.name)

for polygon in body.data.polygons:
    polygon.use_smooth = True
    if polygon.material_index == 6:
        polygon.material_index = 1

body.name = BODY_OUTPUT_NAME
body.parent = None
body["status"] = "ENGINEERING TRIAL — VISUAL AND TOPOLOGY REVIEW REQUIRED"
body["static_review_only"] = True
body["runtime_activation_allowed"] = False
body["movement_started"] = False
body["donor_surface_transferred"] = False
body["anatomy_method"] = "SINGLE LOCAL VOXEL SURFACE + ONE EXACT BODY UNION"
final = topology(body)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

report = {
    "status": body["status"],
    "source": str(SOURCE),
    "output": str(BLEND_PATH),
    "baseline_topology": baseline,
    "single_voxel_anatomy_topology": voxel_topology,
    "final_topology": final,
    "boolean_operations_with_body": 1,
    "global_body_remesh": False,
    "donor_surface_transferred": False,
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
(OUT / "VOXEL_UNION_BUILD_AND_TOPOLOGY_REPORT.json").write_text(
    json.dumps(report, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(report, indent=2))
