"""Build the bounded V23 Biological Robert static-review candidate.

This pass deliberately abandons the failed V14/V15 four-sphere anatomy and the
failed first V23 face-extrusion attempt.  It starts from the intact V1 identity
surface, applies only named local proportion masks, authors a curved external
male anatomy surface from explicit landmark rings, and performs a bounded
exact union.  No runtime, rig, clothing, or activation work is performed.
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
    "biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
)
HAIR_SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v15_from_v14/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_medical_local_rebuild"
)
OUT.mkdir(parents=True, exist_ok=True)


def smoothstep(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    t = max(0.0, min(1.0, (value - low) / (high - low)))
    return t * t * (3.0 - 2.0 * t)


def make_mesh_object(name: str, vertices, faces) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata([tuple(point) for point in vertices], [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    ensure_outward(obj)
    return obj


def ensure_outward(obj: bpy.types.Object) -> float:
    """Make a closed construction surface consistently outward-facing."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    volume = bm.calc_volume(signed=True)
    if volume < 0.0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        volume = -volume
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return float(volume)


def make_ellipsoid(
    name: str,
    center: Vector,
    radii: Vector,
    segments: int = 48,
    rings: int = 24,
    medial_valley: float = 0.0,
) -> bpy.types.Object:
    vertices = []
    faces = []
    # A custom latitude surface is used so the scrotal sac can carry a subtle
    # bilateral front contour instead of being a rigid sphere.
    vertices.append(center + Vector((0.0, 0.0, -radii.z)))
    for ring in range(1, rings):
        phi = -math.pi / 2.0 + math.pi * ring / rings
        cp = math.cos(phi)
        sp = math.sin(phi)
        for segment in range(segments):
            theta = 2.0 * math.pi * segment / segments
            ct = math.cos(theta)
            st = math.sin(theta)
            x = radii.x * cp * ct
            y = radii.y * cp * st
            z = radii.z * sp
            # Only the forward half receives the slight paired-lobe contour.
            # Robert's front is -Y.
            if medial_valley and y < 0.0:
                lateral = min(1.0, abs(x) / max(radii.x, 1e-6))
                y -= medial_valley * lateral * lateral * cp * cp
                z += medial_valley * 0.18 * (x / max(radii.x, 1e-6))
            vertices.append(center + Vector((x, y, z)))
    top_index = len(vertices)
    vertices.append(center + Vector((0.0, 0.0, radii.z)))

    first_ring = 1
    for segment in range(segments):
        faces.append(
            (
                0,
                first_ring + (segment + 1) % segments,
                first_ring + segment,
            )
        )
    for ring in range(rings - 2):
        first = 1 + ring * segments
        second = first + segments
        for segment in range(segments):
            nxt = (segment + 1) % segments
            faces.append((first + segment, first + nxt, second + nxt, second + segment))
    last_ring = 1 + (rings - 2) * segments
    for segment in range(segments):
        faces.append(
            (
                last_ring + segment,
                last_ring + (segment + 1) % segments,
                top_index,
            )
        )
    return make_mesh_object(name, vertices, faces)


def make_shaft() -> bpy.types.Object:
    # Centers and radii are static-neutral review landmarks, not runtime
    # deformation claims.  The first two rings sit inside the pubic surface;
    # the visible body emerges gradually, then the distal flare defines the
    # corona/glans relationship without a pasted-on second object.
    centers = [
        # Broad crus/root ring.  Its placement corrects the over-high
        # V22/early-V23 attachment while keeping the visible shaft lower.
        Vector((0.0, -0.068, 0.792)),
        Vector((0.0, -0.087, 0.777)),
        Vector((0.0, -0.112, 0.762)),
        Vector((0.0, -0.133, 0.744)),
        Vector((0.0, -0.146, 0.724)),
        Vector((0.0, -0.152, 0.704)),
        # Distinct neck/corona/glans sequence.  These remain one continuous
        # mesh and are never synthesized as stacked primitive spheres.
        Vector((0.0, -0.154, 0.691)),
        Vector((0.0, -0.155, 0.683)),
        Vector((0.0, -0.155, 0.673)),
        Vector((0.0, -0.154, 0.663)),
        Vector((0.0, -0.153, 0.657)),
    ]
    radii_x = [
        0.0410,
        0.0310,
        0.0250,
        0.0215,
        0.0195,
        0.0185,
        0.0175,
        0.0250,
        0.0240,
        0.0165,
        0.0080,
    ]
    radii_cross = [
        0.0300,
        0.0270,
        0.0240,
        0.0215,
        0.0200,
        0.0190,
        0.0180,
        0.0240,
        0.0230,
        0.0170,
        0.0080,
    ]
    segments = 48
    vertices = []
    faces = []

    for index, center in enumerate(centers):
        if index == 0:
            tangent = (centers[1] - centers[0]).normalized()
        elif index == len(centers) - 1:
            tangent = (centers[-1] - centers[-2]).normalized()
        else:
            tangent = (centers[index + 1] - centers[index - 1]).normalized()
        # Cross-section axes: X and the perpendicular within the YZ plane.
        second_axis = Vector((0.0, -tangent.z, tangent.y)).normalized()
        for segment in range(segments):
            angle = 2.0 * math.pi * segment / segments
            point = (
                center
                + Vector((1.0, 0.0, 0.0)) * (radii_x[index] * math.cos(angle))
                + second_axis * (radii_cross[index] * math.sin(angle))
            )
            vertices.append(point)
    for ring in range(len(centers) - 1):
        first = ring * segments
        second = first + segments
        for segment in range(segments):
            nxt = (segment + 1) % segments
            faces.append((first + segment, first + nxt, second + nxt, second + segment))

    # Close both hidden root and distal tip.  The root cap is fully inside the
    # body and disappears during the union; the distal cap is softly rounded.
    root_center = len(vertices)
    vertices.append(centers[0] - (centers[1] - centers[0]).normalized() * 0.006)
    tip_center = len(vertices)
    vertices.append(centers[-1] + (centers[-1] - centers[-2]).normalized() * 0.0020)
    for segment in range(segments):
        nxt = (segment + 1) % segments
        faces.append((root_center, nxt, segment))
        final = (len(centers) - 1) * segments
        faces.append((tip_center, final + segment, final + nxt))
    return make_mesh_object("V23_Shaft_Glans_Corona_Surface", vertices, faces)


def exact_union(target: bpy.types.Object, source: bpy.types.Object, name: str) -> None:
    ensure_outward(target)
    ensure_outward(source)
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    source.select_set(False)
    modifier = target.modifiers.new(name, "BOOLEAN")
    modifier.operation = "UNION"
    modifier.solver = "EXACT"
    modifier.object = source
    if hasattr(modifier, "material_mode"):
        modifier.material_mode = "TRANSFER"
    while list(target.modifiers).index(modifier) > 0:
        bpy.ops.object.modifier_move_up(modifier=modifier.name)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(source, do_unlink=True)


def print_bounds(label: str, obj: bpy.types.Object) -> None:
    coordinates = [vertex.co for vertex in obj.data.vertices]
    print(
        label,
        "vertices=",
        len(coordinates),
        "x=",
        (min(point.x for point in coordinates), max(point.x for point in coordinates)),
        "y=",
        (min(point.y for point in coordinates), max(point.y for point in coordinates)),
        "z=",
        (min(point.z for point in coordinates), max(point.z for point in coordinates)),
    )


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1")
if body is None:
    raise RuntimeError("intact V1 identity surface is missing")

for obj in list(bpy.context.scene.objects):
    if any(
        token in obj.name
        for token in ("External_Anatomy_ESTIMATED", "Separate_Brown_Iris", "Separate_Pupil")
    ):
        bpy.data.objects.remove(obj, do_unlink=True)

source_vertex_count = len(body.data.vertices)
source_positions = [vertex.co.copy() for vertex in body.data.vertices]

# V1 contains the same MBLab skin datablock in material slots 1 and 6.  Blender
# can mis-handle that duplicate during evaluated conversion, which is the true
# cause of the gray rectangular thigh/pelvis patches in several rejected
# passes. Normalize the face assignments before any modifier is applied. The
# duplicate slot itself stays in place until all topology operations finish so
# tongue, teeth, and nail indices cannot shift underneath existing faces.
for polygon in body.data.polygons:
    if polygon.material_index == 6:
        polygon.material_index = 1

# Modest, locally blended slimming below the neck.  Each region scales around
# its own anatomical center so hands, feet, head, joint positions, and the
# inter-thigh gap are not globally distorted.
torso_group = body.vertex_groups.new(name="V23_LOCAL_TORSO_PROPORTION_MASK")
arm_group = body.vertex_groups.new(name="V23_LOCAL_UPPER_ARM_PROPORTION_MASK")
thigh_group = body.vertex_groups.new(name="V23_LOCAL_THIGH_PROPORTION_MASK")
hand_group = body.vertex_groups.new(name="V23_LOCAL_HAND_PROPORTION_MASK")
torso_members = []
arm_members = []
thigh_members = []
hand_members = []

for vertex in body.data.vertices:
    co = vertex.co
    original = co.copy()
    # Torso/abdomen: strongest at the waist and abdomen, fading before the neck.
    if 0.84 < co.z < 1.48 and abs(co.x) < 0.285:
        low = smoothstep(co.z, 0.84, 0.96)
        high = 1.0 - smoothstep(co.z, 1.36, 1.48)
        weight = low * high
        co.x *= 1.0 - 0.082 * weight
        co.y *= 1.0 - 0.118 * weight
        if weight > 0.001:
            torso_members.append(vertex.index)
    # Upper arms: modest circumference reduction around each local arm axis.
    if 1.02 < co.z < 1.42 and 0.245 < abs(co.x) < 0.385:
        side = 1.0 if co.x > 0 else -1.0
        center_x = side * 0.302
        weight = smoothstep(co.z, 1.02, 1.10) * (1.0 - smoothstep(co.z, 1.34, 1.42))
        co.x = center_x + (co.x - center_x) * (1.0 - 0.050 * weight)
        co.y *= 1.0 - 0.045 * weight
        if weight > 0.001:
            arm_members.append(vertex.index)
    # Upper legs: reduce excess circumference around independent thigh axes.
    if 0.52 < co.z < 0.91 and 0.045 < abs(co.x) < 0.285:
        side = 1.0 if co.x > 0 else -1.0
        center_x = side * 0.122
        weight = smoothstep(co.z, 0.52, 0.61) * (1.0 - smoothstep(co.z, 0.82, 0.91))
        co.x = center_x + (co.x - center_x) * (1.0 - 0.055 * weight)
        co.y *= 1.0 - 0.050 * weight
        if weight > 0.001:
            thigh_members.append(vertex.index)
    if (co - original).length > 1e-9:
        pass

# Hands and all five fingers are selected from the existing anatomical weight
# groups rather than a guessed world-space box.  This retains the V1 hand/nail
# mesh, modestly corrects blade-like width, and shortens distal proportions
# without touching the forearms.
hand_weight_groups = {
    group.index
    for group in body.vertex_groups
    if any(
        token in group.name.lower()
        for token in ("hand_", "thumb", "index", "middle", "ring", "pinky")
    )
}
hand_by_side = {-1: [], 1: []}
for vertex in body.data.vertices:
    if any(
        assignment.group in hand_weight_groups and assignment.weight > 0.05
        for assignment in vertex.groups
    ):
        hand_by_side[1 if vertex.co.x > 0 else -1].append(vertex)
for side, vertices in hand_by_side.items():
    if not vertices:
        continue
    center_x = sum(vertex.co.x for vertex in vertices) / len(vertices)
    center_y = sum(vertex.co.y for vertex in vertices) / len(vertices)
    wrist_z = max(vertex.co.z for vertex in vertices)
    for vertex in vertices:
        vertex.co.x = center_x + (vertex.co.x - center_x) * 1.070
        vertex.co.y = center_y + (vertex.co.y - center_y) * 1.040
        vertex.co.z = wrist_z + (vertex.co.z - wrist_z) * 0.960
        hand_members.append(vertex.index)

for group, members in (
    (torso_group, torso_members),
    (arm_group, arm_members),
    (thigh_group, thigh_members),
    (hand_group, hand_members),
):
    if members:
        group.add(members, 1.0, "REPLACE")

skin = bpy.data.materials.get("MBLab_skin3")
if skin is None:
    raise RuntimeError("V1 authored MBLab skin material is missing")

# Freeze the armature and corrective stages while the original V1 vertex count
# is still intact.  Corrective Smooth stores an original-vertex contract and
# must never be run after topology is added (that caused the rejected
# paper/spike explosion).  Subdivision and displacement remain live so the
# joined local surface still receives the same finishing treatment.
applied_modifiers = []
bpy.context.view_layer.objects.active = body
body.select_set(True)
for modifier in list(body.modifiers):
    if modifier.type not in {"ARMATURE", "CORRECTIVE_SMOOTH"}:
        continue
    applied_modifiers.append((modifier.name, modifier.type))
    bpy.ops.object.modifier_apply(modifier=modifier.name)

# Hand-authored adult external anatomy components.  The sac, pubic transition,
# perineal bridge, and shaft all overlap well inside one another and the body.
# They are merged before body integration; no finished reference body surface
# or reference identity/proportion is transferred.
shaft = make_shaft()

# The scrotal envelope is constructed from two strongly overlapping,
# asymmetrical lobes plus a broad upper bridge.  After exact union this is one
# continuous sac, not two floating testes and not the ring/donut silhouette
# produced by the rejected single sphere.  The left side hangs slightly lower,
# consistent with ordinary adult variation; the asymmetry is deliberately
# restrained.
scrotum_left = make_ellipsoid(
    "V23_Scrotal_Left_Lobe",
    Vector((-0.0125, -0.098, 0.668)),
    Vector((0.0330, 0.0305, 0.0500)),
    segments=48,
    rings=28,
)
scrotum_right = make_ellipsoid(
    "V23_Scrotal_Right_Lobe",
    Vector((0.0125, -0.097, 0.674)),
    Vector((0.0325, 0.0300, 0.0460)),
    segments=48,
    rings=28,
)
scrotal_upper_bridge = make_ellipsoid(
    "V23_Scrotal_Upper_Bridge",
    Vector((0.0, -0.091, 0.704)),
    Vector((0.0435, 0.0340, 0.0380)),
    segments=48,
    rings=28,
)
pubic_transition = make_ellipsoid(
    "V23_Pubic_Root_Transition",
    Vector((0.0, -0.080, 0.750)),
    Vector((0.047, 0.040, 0.045)),
    segments=56,
    rings=30,
)
perineal_transition = make_ellipsoid(
    "V23_Perineal_Transition",
    Vector((0.0, -0.035, 0.690)),
    Vector((0.038, 0.043, 0.044)),
    segments=48,
    rings=26,
)
for obj in (
    shaft,
    scrotum_left,
    scrotum_right,
    scrotal_upper_bridge,
    pubic_transition,
    perineal_transition,
):
    obj.data.materials.append(skin)

exact_union(scrotum_left, scrotum_right, "V23_Bilateral_Scrotal_Union")
print_bounds("after bilateral union", scrotum_left)
exact_union(scrotum_left, scrotal_upper_bridge, "V23_Scrotal_Upper_Bridge_Union")
print_bounds("after upper bridge union", scrotum_left)
exact_union(scrotum_left, pubic_transition, "V23_Pubic_Transition_Union")
print_bounds("after pubic transition union", scrotum_left)
exact_union(scrotum_left, perineal_transition, "V23_Perineal_Transition_Union")
print_bounds("after perineal transition union", scrotum_left)
exact_union(scrotum_left, shaft, "V23_Shaft_Scrotum_Union")
print_bounds("after shaft union", scrotum_left)
scrotum_left.name = "V23_Integrated_External_Anatomy"
anatomy_signed_volume = ensure_outward(scrotum_left)
for polygon in scrotum_left.data.polygons:
    polygon.use_smooth = True

# Join the locally authored surface to Robert.  The construction penetrates the
# existing pubic surface so the union removes hidden caps and leaves one skin
# surface instead of a floating or merely touching component.
pre_union_vertex_count = len(body.data.vertices)
exact_union(body, scrotum_left, "V23_Bounded_External_Anatomy_Union")

# Relax only the root-transition band.  This reduces Boolean edge creases
# without changing the distal form, face, hands, thighs, or any other region.
bm = bmesh.new()
bm.from_mesh(body.data)
root_vertices = [
    vertex
    for vertex in bm.verts
    if abs(vertex.co.x) < 0.072
    and -0.135 < vertex.co.y < 0.030
    and 0.725 < vertex.co.z < 0.815
]
for _ in range(4):
    bmesh.ops.smooth_vert(
        bm,
        verts=root_vertices,
        factor=0.14,
        use_axis_x=True,
        use_axis_y=True,
        use_axis_z=True,
    )
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(body.data)
bm.free()
body.data.update()
for polygon in body.data.polygons:
    polygon.use_smooth = True

# Now freeze the remaining shared Stage-A surface modifiers in their real V1
# order.  Only subdivision/displacement should remain.
bpy.context.view_layer.objects.active = body
body.select_set(True)
for modifier in list(body.modifiers):
    applied_modifiers.append((modifier.name, modifier.type))
    bpy.ops.object.modifier_apply(modifier=modifier.name)

# The exact union can leave one bounded, degree-two interface loop around the
# proximal anatomy even when the outer forms visually overlap.  That loop is
# the source of the black "hole" seen in rejected protected views.  Close only
# this medically bounded pelvis loop with a real triangulated bridge; inherited
# mouth/eye openings are deliberately excluded.
bm = bmesh.new()
bm.from_mesh(body.data)
pelvis_boundary_edges = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and all(
        abs(vertex.co.x) < 0.065
        and -0.110 < vertex.co.y < -0.025
        and 0.715 < vertex.co.z < 0.825
        for vertex in edge.verts
    )
]
pelvis_boundary_vertex_degrees = {}
for edge in pelvis_boundary_edges:
    for vertex in edge.verts:
        pelvis_boundary_vertex_degrees[vertex] = (
            pelvis_boundary_vertex_degrees.get(vertex, 0) + 1
        )
if not pelvis_boundary_edges or set(pelvis_boundary_vertex_degrees.values()) != {2}:
    bm.free()
    raise RuntimeError(
        "bounded pelvis interface is not one or more clean degree-two loops"
    )
fill_result = bmesh.ops.triangle_fill(
    bm,
    edges=pelvis_boundary_edges,
    use_beauty=True,
    use_dissolve=False,
)
pelvis_bridge_faces = [
    item for item in fill_result["geom"] if isinstance(item, bmesh.types.BMFace)
]
if not pelvis_bridge_faces:
    bm.free()
    raise RuntimeError("bounded pelvis bridge produced no faces")
for face in pelvis_bridge_faces:
    face.material_index = 1

# The bridge is topologically closed at this point, but its inherited loop can
# still form a deep superior concavity that reads as a black opening.  Shape a
# small pubic/root transition forward using a smooth center/height falloff.
# This is a local surface edit, not a coordinate shift of the external anatomy.
pubic_root_shape_vertices = []
for vertex in bm.verts:
    if (
        abs(vertex.co.x) < 0.043
        and -0.110 < vertex.co.y < -0.020
        and 0.780 < vertex.co.z < 0.833
    ):
        center_weight = 1.0 - smoothstep(abs(vertex.co.x), 0.014, 0.043)
        low_weight = smoothstep(vertex.co.z, 0.780, 0.792)
        high_weight = 1.0 - smoothstep(vertex.co.z, 0.818, 0.833)
        weight = center_weight * low_weight * high_weight
        target_y = -0.094 + 0.34 * (vertex.co.z - 0.790)
        if weight > 0.0 and vertex.co.y > target_y:
            vertex.co.y = vertex.co.y * (1.0 - weight) + target_y * weight
            pubic_root_shape_vertices.append(vertex)

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(body.data)
bm.free()
body.data.update()

# Applying the Boolean removes the now-unused duplicate V1 skin slot. Blender
# removes the slot itself but leaves the later face indices numerically
# unchanged. Restore the semantic mapping explicitly before review rendering:
# old 7/8/9 are tongue/teeth/nails and become clean slots 6/7/8.
for polygon in body.data.polygons:
    if polygon.material_index in {7, 8, 9}:
        polygon.material_index -= 1

# Preserve the authored V1 skin maps.  New local faces use the same skin
# datablock and receive a bounded UV projection rather than a flat color.
if skin.name not in [material.name for material in body.data.materials if material]:
    body.data.materials.append(skin)
skin_index = next(
    index
    for index, material in enumerate(body.data.materials)
    if material and material.name == skin.name
)
for polygon in body.data.polygons:
    center = polygon.center
    if (
        abs(center.x) < 0.12
        and -0.26 < center.y < 0.10
        and 0.59 < center.z < 0.86
    ):
        polygon.material_index = skin_index

# Boolean-created loops do not carry meaningful V1 UVs.  Sample a verified
# lower-abdomen skin point and give only the bounded central repair area a
# stable nearby UV neighborhood.  This keeps the authored MBLab skin response
# instead of the rejected white/flat construction color.
uv_layer = body.data.uv_layers.active
if uv_layer is not None:
    donor_candidates = [
        polygon
        for polygon in body.data.polygons
        if polygon.material_index == skin_index
        and abs(polygon.center.x) < 0.08
        and polygon.center.y < -0.12
        and 0.90 < polygon.center.z < 1.05
    ]
    if donor_candidates:
        donor = min(
            donor_candidates,
            key=lambda polygon: (
                polygon.center - Vector((0.0, -0.18, 0.97))
            ).length,
        )
        donor_uvs = [uv_layer.data[index].uv.copy() for index in donor.loop_indices]
        donor_uv = sum(donor_uvs, Vector((0.0, 0.0))) / len(donor_uvs)
        for polygon in body.data.polygons:
            center = polygon.center
            if (
                abs(center.x) < 0.078
                and -0.23 < center.y < 0.02
                and 0.615 < center.z < 0.825
            ):
                for loop_index in polygon.loop_indices:
                    vertex = body.data.vertices[body.data.loops[loop_index].vertex_index]
                    uv_layer.data[loop_index].uv = donor_uv + Vector(
                        (vertex.co.x * 0.07, (vertex.co.z - 0.71) * 0.045)
                    )

# A corner-domain tint separates subtle regional pigmentation from lighting,
# AO, or cavity shading while retaining one shared skin material.  The earlier
# polygon-level rectangle produced false triangular thigh discoloration.
# V23 therefore calculates a smooth per-vertex weight limited to the authored
# anterior anatomy surface; adjacent thighs and the abdominal underside remain
# on the unmodified V1 albedo.
tint = body.data.color_attributes.get("V23_Regional_Skin_Tint")
if tint is None:
    tint = body.data.color_attributes.new(
        name="V23_Regional_Skin_Tint",
        type="BYTE_COLOR",
        domain="CORNER",
    )
for polygon in body.data.polygons:
    coordinates = [
        body.data.vertices[body.data.loops[index].vertex_index].co
        for index in polygon.loop_indices
    ]
    entirely_on_authored_surface = bool(coordinates) and all(
        abs(co.x) < 0.058
        and co.y < -0.082
        and 0.605 < co.z < 0.805
        for co in coordinates
    )
    for loop_index in polygon.loop_indices:
        vertex = body.data.vertices[body.data.loops[loop_index].vertex_index]
        co = vertex.co
        x_weight = 1.0 - smoothstep(abs(co.x), 0.045, 0.058)
        front_weight = smoothstep(-co.y, 0.082, 0.125)
        low_weight = smoothstep(co.z, 0.605, 0.645)
        high_weight = 1.0 - smoothstep(co.z, 0.780, 0.805)
        weight = (
            x_weight
            * front_weight
            * low_weight
            * high_weight
            if entirely_on_authored_surface
            else 0.0
        )
        # Subtle warm regional tone.  This is albedo variation only; AO,
        # cavity, roughness and subsurface response remain separate.
        color = (
            1.0 - 0.032 * weight,
            1.0 - 0.052 * weight,
            1.0 - 0.058 * weight,
            1.0,
        )
        tint.data[loop_index].color = color

if skin.use_nodes:
    nodes = skin.node_tree.nodes
    links = skin.node_tree.links
    bsdf = next((node for node in nodes if node.type == "BSDF_PRINCIPLED"), None)
    if bsdf is not None and not nodes.get("V23_Regional_Skin_Multiply"):
        attribute = nodes.new("ShaderNodeVertexColor")
        attribute.name = "V23_Regional_Skin_Tint"
        attribute.layer_name = "V23_Regional_Skin_Tint"
        multiply = nodes.new("ShaderNodeMixRGB")
        multiply.name = "V23_Regional_Skin_Multiply"
        multiply.blend_type = "MULTIPLY"
        multiply.inputs[0].default_value = 1.0
        existing = bsdf.inputs["Base Color"].links[0] if bsdf.inputs["Base Color"].links else None
        if existing is not None:
            links.remove(existing)
            links.new(existing.from_socket, multiply.inputs[1])
        else:
            multiply.inputs[1].default_value = bsdf.inputs["Base Color"].default_value
        links.new(attribute.outputs["Color"], multiply.inputs[2])
        links.new(multiply.outputs["Color"], bsdf.inputs["Base Color"])

# Removable Stage-A hairstyle only.  A dedicated neutral dark-blond shader
# prevents imported image nodes from turning the hair white or brown.
with bpy.data.libraries.load(str(HAIR_SOURCE), link=False) as (data_from, data_to):
    data_to.objects = [name for name in ("Object_6", "Object_7") if name in data_from.objects]
hair_material = bpy.data.materials.new("Robert_V23_Removable_Dark_Blond_Static_Hair")
hair_material.use_nodes = True
hair_bsdf = next(
    node for node in hair_material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"
)
hair_bsdf.inputs["Base Color"].default_value = (0.115, 0.055, 0.018, 1.0)
hair_bsdf.inputs["Roughness"].default_value = 0.40
hair_bsdf.inputs["IOR"].default_value = 1.46
for hair in data_to.objects:
    if hair is None:
        continue
    bpy.context.collection.objects.link(hair)
    if hair.name.startswith("Object_6"):
        hair.scale.x *= 1.105
        hair.scale.y *= 1.120
        hair.scale.z *= 1.055
        hair.location.y -= 0.012
        hair.location.z -= 0.006
    else:
        hair.scale.x *= 1.125
        hair.scale.y *= 1.135
        hair.scale.z *= 1.065
        hair.location.y -= 0.010
        hair.location.z -= 0.006
    hair.data.materials.clear()
    hair.data.materials.append(hair_material)
    for polygon in hair.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True
    hair["stage_a_static_review_only"] = True
    hair["runtime_groom_complete"] = False

body.name = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_MEDICAL_LOCAL_REBUILD"
body["status"] = "V23 ENGINEERING CANDIDATE — VISUAL AND TOPOLOGY GATES REQUIRED"
body["source_v1_sha256"] = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
body["anatomy_method"] = (
    "HAND-AUTHORED LANDMARK RINGS + BOUNDED EXACT UNION + LOCAL ROOT RELAXATION"
)
body["reference_use"] = "STRUCTURAL/MEDICAL GUIDANCE ONLY"
body["anatomy_estimation_label"] = "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE"
body["global_scaling_used"] = False
body["finished_reference_surface_transferred"] = False
body["runtime_activation_allowed"] = False
body["movement_started"] = False
body["regional_skin_variation"] = (
    "PRESERVED_FROM_V1 + SMOOTH LOCAL ANATOMY ALBEDO; "
    "NO AO/CAVITY BAKED INTO SKIN COLOR"
)

blend_path = OUT / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_MEDICAL_LOCAL_REBUILD.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

outside_change = []
for index, (before, vertex) in enumerate(zip(source_positions, body.data.vertices)):
    if index >= source_vertex_count:
        break
    if (vertex.co - before).length > 1e-9:
        outside_change.append(index)

report = {
    "schema_version": 1,
    "status": body["status"],
    "preferred_identity_foundation": "V1 / V15-V18-derived accepted face-and-skin direction",
    "failed_inputs_not_reused": [
        "V14/V15 four-sphere anatomy",
        "V20/V21 global distortions",
        "V22 coordinate shift",
        "V23 first flat face-extrusion attempt",
    ],
    "source_v1_sha256": body["source_v1_sha256"],
    "source_vertex_count": source_vertex_count,
    "pre_union_vertex_count": pre_union_vertex_count,
    "final_vertex_count": len(body.data.vertices),
    "static_surface_modifiers_applied_in_order": applied_modifiers,
    "named_local_masks": {
        "torso": len(torso_members),
        "upper_arms": len(arm_members),
        "upper_legs": len(thigh_members),
        "hands": len(hand_members),
    },
    "anatomy_method": body["anatomy_method"],
    "authored_anatomy_positive_volume_m3": anatomy_signed_volume,
    "bounded_pelvis_interface_edges_bridged": len(pelvis_boundary_edges),
    "bounded_pelvis_bridge_faces": len(pelvis_bridge_faces),
    "pubic_root_shape_vertices": len(pubic_root_shape_vertices),
    "medical_landmarks_authored": [
        "pubic/root transition",
        "shaft body",
        "coronal flare",
        "glans/tip transition",
        "single scrotal sac with subtle bilateral contour",
        "perineal transition",
    ],
    "global_scaling_used": False,
    "finished_reference_surface_transferred": False,
    "skin_source": "V1 MBLab authored skin maps retained",
    "hair": "removable dark-blond Stage-A review hairstyle; runtime groom not complete",
    "movement": "not started",
    "runtime_attachment": "prohibited",
}
(OUT / "BUILD_REPORT.json").write_text(
    json.dumps(report, indent=2) + "\n", encoding="utf-8"
)
print(blend_path)
