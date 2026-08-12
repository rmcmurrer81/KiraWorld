"""Build a bounded V23 preserved-pubic-surface engineering trial.

This trial starts from the V1/V15-derived Biological Robert identity body and
does not replace the pubic region with a fabricated elliptical panel.  It:

* welds only the genuine near-medial mirrored seam pairs;
* preserves the lateral V1 pubic surface and its first derivatives;
* locally subdivides the retained owner-body surface;
* opens two compact, independently attached root footprints;
* extrudes each footprint along the retained surface normal before beginning
  the anatomical branch; and
* keeps every edit inside the static anterior-pelvis region.

The result is engineering evidence only.  It is not owner approved and cannot
authorize movement, runtime attachment, activation, clothing, Kira, or
Synthetic Robert.
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
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_preserved_surface_trial_r24_raised_branches"
)
OUT.mkdir(parents=True, exist_ok=True)
BODY_SOURCE_NAME = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1"
BODY_OUTPUT_NAME = (
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_"
    "PRESERVED_SURFACE_TRIAL_R24_RAISED_BRANCHES"
)
BLEND_PATH = OUT / f"{BODY_OUTPUT_NAME}.blend"


TRUE_MEDIAL_PAIRS = (
    (10342, 5694),
    (10620, 5972),
    (10626, 5978),
    (10622, 5974),
    (10739, 6091),
    (10763, 6115),
    (10748, 6100),
    (10724, 6076),
)


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def edge_components(
    edges: list[bmesh.types.BMEdge],
) -> list[list[bmesh.types.BMEdge]]:
    vertex_edges: dict[bmesh.types.BMVert, list[bmesh.types.BMEdge]] = {}
    for edge in edges:
        for vertex in edge.verts:
            vertex_edges.setdefault(vertex, []).append(edge)
    unseen = set(edges)
    components = []
    while unseen:
        seed = unseen.pop()
        component = [seed]
        stack = [seed]
        while stack:
            current = stack.pop()
            for vertex in current.verts:
                for neighbor in vertex_edges[vertex]:
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        component.append(neighbor)
                        stack.append(neighbor)
        components.append(component)
    return components


def ordered_cycle(edges: list[bmesh.types.BMEdge]) -> list[bmesh.types.BMVert]:
    adjacency: dict[bmesh.types.BMVert, list[bmesh.types.BMVert]] = {}
    for edge in edges:
        first, second = edge.verts
        adjacency.setdefault(first, []).append(second)
        adjacency.setdefault(second, []).append(first)
    degrees = {len(neighbors) for neighbors in adjacency.values()}
    if degrees != {2}:
        non_two = [
            {
                "coordinate": tuple(round(value, 6) for value in vertex.co),
                "degree": len(neighbors),
            }
            for vertex, neighbors in adjacency.items()
            if len(neighbors) != 2
        ]
        raise RuntimeError(
            "root boundary is not a simple closed cycle: "
            f"edge_count={len(edges)}, vertex_count={len(adjacency)}, "
            f"degrees={sorted(degrees)}, "
            f"non_two={non_two}"
        )
    start = max(adjacency, key=lambda vertex: (vertex.co.z, -abs(vertex.co.x)))
    first_neighbor = min(
        adjacency[start],
        key=lambda vertex: math.atan2(
            vertex.co.z - start.co.z,
            vertex.co.x - start.co.x,
        ),
    )
    order = [start, first_neighbor]
    previous = start
    current = first_neighbor
    while True:
        following = next(
            vertex for vertex in adjacency[current] if vertex is not previous
        )
        if following is start:
            break
        if following in order:
            raise RuntimeError("root boundary repeats before closure")
        order.append(following)
        previous, current = current, following
    return order


def topology_counts(obj: bpy.types.Object) -> dict[str, int]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    result = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges": sum(len(edge.link_faces) == 1 for edge in bm.edges),
        "wire_edges": sum(len(edge.link_faces) == 0 for edge in bm.edges),
        "nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2 for edge in bm.edges
        ),
    }
    bm.free()
    return result


def average_boundary_uv(
    cycle: list[bmesh.types.BMVert],
    uv_layer: bmesh.types.BMLayerItem | None,
) -> Vector:
    if uv_layer is None:
        return Vector((0.52, 0.38))
    values = [
        loop[uv_layer].uv.copy()
        for vertex in cycle
        for face in vertex.link_faces
        for loop in face.loops
        if loop.vert is vertex
    ]
    if not values:
        return Vector((0.52, 0.38))
    return sum(values, Vector((0.0, 0.0))) / len(values)


def cycle_angles(
    cycle: list[bmesh.types.BMVert],
    center: Vector,
) -> list[float]:
    raw = [
        math.atan2(vertex.co.z - center.z, vertex.co.x - center.x)
        for vertex in cycle
    ]
    result = [raw[0]]
    for value in raw[1:]:
        while value - result[-1] > math.pi:
            value -= math.tau
        while value - result[-1] < -math.pi:
            value += math.tau
        result.append(value)
    return result


def connect_rings(
    bm: bmesh.types.BMesh,
    first: list[bmesh.types.BMVert],
    second: list[bmesh.types.BMVert],
    *,
    material_index: int,
    new_faces: list[bmesh.types.BMFace],
) -> None:
    if len(first) != len(second):
        raise RuntimeError("ring sizes differ")
    for index in range(len(first)):
        following = (index + 1) % len(first)
        face = bm.faces.new(
            (
                first[index],
                first[following],
                second[following],
                second[index],
            )
        )
        face.material_index = material_index
        face.smooth = True
        new_faces.append(face)


def boundary_normal(vertex: bmesh.types.BMVert) -> Vector:
    normal = sum(
        (face.normal for face in vertex.link_faces),
        Vector((0.0, 0.0, 0.0)),
    )
    if normal.length < 1.0e-8:
        normal = Vector((0.0, -1.0, 0.0))
    normal.normalize()
    if normal.y > -0.12:
        normal = Vector((normal.x * 0.25, -1.0, normal.z * 0.25)).normalized()
    return normal


def add_surface_normal_support_ring(
    bm: bmesh.types.BMesh,
    root: list[bmesh.types.BMVert],
    *,
    normal_offset: float,
    down_offset: float,
    surface_class: int,
    surface_class_layer: bmesh.types.BMLayerItem,
    regional_mix_layer: bmesh.types.BMLayerItem,
    vertex_uv: dict[bmesh.types.BMVert, Vector],
    uv_center: Vector,
    new_vertices: list[bmesh.types.BMVert],
) -> list[bmesh.types.BMVert]:
    support = []
    for vertex in root:
        coordinate = (
            vertex.co
            + boundary_normal(vertex) * normal_offset
            + Vector((0.0, 0.0, -down_offset))
        )
        created = bm.verts.new(coordinate)
        created[surface_class_layer] = surface_class
        created[regional_mix_layer] = 0.20
        vertex_uv[created] = uv_center.copy()
        support.append(created)
        new_vertices.append(created)
    return support


def tangent_cross_axis(tangent: Vector) -> Vector:
    tangent = tangent.normalized()
    cross_axis = Vector((0.0, -tangent.z, tangent.y))
    if cross_axis.length < 1.0e-8:
        return Vector((0.0, 1.0, 0.0))
    return cross_axis.normalized()


def add_ideal_ring(
    bm: bmesh.types.BMesh,
    *,
    center: Vector,
    tangent: Vector,
    angles: list[float],
    radius_x: float,
    radius_cross: float,
    surface_class: int,
    mix_value: float,
    surface_class_layer: bmesh.types.BMLayerItem,
    regional_mix_layer: bmesh.types.BMLayerItem,
    vertex_uv: dict[bmesh.types.BMVert, Vector],
    uv_center: Vector,
    new_vertices: list[bmesh.types.BMVert],
    scrotal_envelope: bool = False,
    progress: float = 0.0,
) -> list[bmesh.types.BMVert]:
    cross_axis = tangent_cross_axis(tangent)
    ring = []
    for theta in angles:
        cosine = math.cos(theta)
        sine = math.sin(theta)
        coordinate = (
            center
            + Vector((1.0, 0.0, 0.0)) * (radius_x * cosine)
            + cross_axis * (radius_cross * sine)
        )
        if scrotal_envelope:
            # One connected pouch with a restrained central raphe and slight
            # natural asymmetry.  This is not two floating spheres.
            medial = math.exp(-((coordinate.x / 0.0075) ** 2))
            if coordinate.y < center.y:
                coordinate.y += 0.0020 * medial * progress
            if coordinate.x < 0.0:
                coordinate.z -= 0.0018 * progress
            else:
                coordinate.z += 0.0008 * progress
        vertex = bm.verts.new(coordinate)
        vertex[surface_class_layer] = surface_class
        vertex[regional_mix_layer] = mix_value
        vertex_uv[vertex] = uv_center + Vector(
            (0.010 * cosine, 0.009 * sine)
        )
        ring.append(vertex)
        new_vertices.append(vertex)
    return ring


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get(BODY_SOURCE_NAME)
if body is None:
    raise RuntimeError("V1 Biological Robert body is missing")

for obj in list(bpy.context.scene.objects):
    if "External_Anatomy_ESTIMATED" in obj.name:
        bpy.data.objects.remove(obj, do_unlink=True)

source_sha256 = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
baseline_topology = topology_counts(body)

for polygon in body.data.polygons:
    if polygon.material_index == 6:
        polygon.material_index = 1

bpy.context.view_layer.objects.active = body
body.select_set(True)
applied_pre = []
for modifier in list(body.modifiers):
    if modifier.type in {"ARMATURE", "CORRECTIVE_SMOOTH"}:
        applied_pre.append((modifier.name, modifier.type))
        bpy.ops.object.modifier_apply(modifier=modifier.name)

skin = bpy.data.materials.get("MBLab_skin3")
if skin is None:
    raise RuntimeError("V1 skin material is missing")
skin_index = next(
    index
    for index, material in enumerate(body.data.materials)
    if material and material.name == skin.name
)

bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()
uv_layer = bm.loops.layers.uv.active
surface_class_layer = bm.verts.layers.int.get("V23_Surface_Class")
if surface_class_layer is None:
    surface_class_layer = bm.verts.layers.int.new("V23_Surface_Class")
regional_mix_layer = bm.verts.layers.float.get("V23_Regional_Mix")
if regional_mix_layer is None:
    regional_mix_layer = bm.verts.layers.float.new("V23_Regional_Mix")

# Weld only the genuine near-medial V1 duplicate seam.  The four wider pairs
# used by R14-R18 are retained at their owner-body coordinates; collapsing
# them to x=0 was the direct source of the long leaf-shaped panel.
medial_midpoints = []
medial_vertices = []
for left_index, right_index in TRUE_MEDIAL_PAIRS:
    left = bm.verts[left_index]
    right = bm.verts[right_index]
    if max(abs(left.co.x), abs(right.co.x)) > 0.0155:
        raise RuntimeError("non-medial V1 pair entered the weld allowlist")
    midpoint = (left.co + right.co) * 0.5
    midpoint.x = 0.0
    # Preserve the inherited center depth during topology construction.  A
    # bounded, high-resolution fairing pass after the root geometry exists
    # will relax the visible cleft without changing footprint selection or
    # turning the full region into a planar shield.
    if midpoint.y > -0.050:
        midpoint.y = max(-0.054, midpoint.y - 0.004)
    left.co = midpoint
    right.co = midpoint
    medial_midpoints.append(tuple(midpoint))
    medial_vertices.extend((left, right))

bmesh.ops.remove_doubles(
    bm,
    verts=medial_vertices,
    dist=0.00005,
)
bmesh.ops.dissolve_degenerate(bm, dist=0.00001, edges=bm.edges)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

# Add local resolution to the retained V1 surface.  This preserves the real
# X/Z footprint and one-ring curvature rather than mapping it to an ellipse.
subdivision_faces = [
    face
    for face in bm.faces
    if (
        abs(face.calc_center_median().x) < 0.060
        and -0.145 < face.calc_center_median().y < -0.015
        and 0.675 < face.calc_center_median().z < 0.815
    )
]
subdivision_edges = list(
    {
        edge
        for face in subdivision_faces
        for edge in face.edges
    }
)
if len(subdivision_edges) < 20:
    raise RuntimeError("retained V1 pubic surface selection is unexpectedly sparse")
bmesh.ops.subdivide_edges(
    bm,
    edges=subdivision_edges,
    cuts=3,
    use_grid_fill=True,
)
bmesh.ops.remove_doubles(
    bm,
    verts=[
        vertex
        for vertex in bm.verts
        if (
            abs(vertex.co.x) < 0.00035
            and -0.150 < vertex.co.y < -0.015
            and 0.675 < vertex.co.z < 0.815
        )
    ],
    dist=0.00012,
)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def footprint_value(
    point: Vector,
    *,
    center_z: float,
    radius_x: float,
    radius_z: float,
) -> float:
    return (point.x / radius_x) ** 2 + (
        (point.z - center_z) / radius_z
    ) ** 2


shaft_center_z = 0.789
scrotal_center_z = 0.742
shaft_faces = []
scrotal_faces = []
for face in bm.faces:
    center = face.calc_center_median()
    if not (-0.145 < center.y < -0.018):
        continue
    if footprint_value(
        center,
        center_z=shaft_center_z,
        radius_x=0.0145,
        radius_z=0.0105,
    ) < 0.92:
        shaft_faces.append(face)
    elif footprint_value(
        center,
        center_z=scrotal_center_z,
        radius_x=0.0235,
        radius_z=0.0125,
    ) < 0.92:
        scrotal_faces.append(face)

# Ensure each bilateral footprint crosses a real welded seam segment instead
# of letting the left and right half-holes touch at only one vertex.  A
# one-vertex touch produces a figure-eight boundary (degree four) and cannot
# become a clean root attachment.
for edge in bm.edges:
    if not all(abs(vertex.co.x) < 0.0002 for vertex in edge.verts):
        continue
    midpoint_z = sum(vertex.co.z for vertex in edge.verts) * 0.5
    if 0.774 <= midpoint_z <= 0.804:
        shaft_faces.extend(edge.link_faces)
    elif 0.707 <= midpoint_z <= 0.758:
        scrotal_faces.extend(edge.link_faces)

shaft_faces = list(dict.fromkeys(shaft_faces))
scrotal_faces = [
    face
    for face in dict.fromkeys(scrotal_faces)
    if face not in shaft_faces
]

if not shaft_faces or not scrotal_faces:
    raise RuntimeError(
        f"compact root selection failed: shaft={len(shaft_faces)}, "
        f"scrotal={len(scrotal_faces)}"
    )
preexisting_boundary_edges = {
    edge for edge in bm.edges if len(edge.link_faces) == 1
}
bmesh.ops.delete(
    bm,
    geom=[*shaft_faces, *scrotal_faces],
    context="FACES",
)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

def current_root_components() -> list[list[bmesh.types.BMEdge]]:
    edges = [
        edge
        for edge in bm.edges
        if len(edge.link_faces) == 1
        and edge not in preexisting_boundary_edges
        and all(
            abs(vertex.co.x) < 0.042
            and -0.155 < vertex.co.y < -0.015
            and 0.690 < vertex.co.z < 0.810
            for vertex in edge.verts
        )
    ]
    return [
        component
        for component in edge_components(edges)
        if len(component) >= 8
    ]


# A bilateral face footprint can touch at a single inherited seam vertex even
# after the true seam edges are welded.  Remove only that singular vertex and
# its incident micro-faces, then re-evaluate.  This enlarges the local root by
# one subdivided cell; it does not remove a lateral owner-body strip or create
# a fabricated transition panel.
for _cleanup in range(4):
    root_components = current_root_components()
    bad_vertices = []
    for component in root_components:
        adjacency: dict[bmesh.types.BMVert, set[bmesh.types.BMVert]] = {}
        for edge in component:
            first, second = edge.verts
            adjacency.setdefault(first, set()).add(second)
            adjacency.setdefault(second, set()).add(first)
        bad_vertices.extend(
            vertex
            for vertex, neighbors in adjacency.items()
            if len(neighbors) > 2
        )
    if not bad_vertices:
        break
    bmesh.ops.delete(
        bm,
        geom=list(dict.fromkeys(bad_vertices)),
        context="VERTS",
    )
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

root_components = current_root_components()
small_upper_components = []
for component in root_components:
    component_vertices = {
        vertex for edge in component for vertex in edge.verts
    }
    if (
        len(component) <= 16
        and min(vertex.co.z for vertex in component_vertices) > 0.780
    ):
        small_upper_components.append(component)
for component in small_upper_components:
    fill_result = bmesh.ops.holes_fill(
        bm,
        edges=component,
        sides=0,
    )
    for face in fill_result.get("faces", []):
        face.material_index = skin_index
        face.smooth = True
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
if small_upper_components:
    root_components = current_root_components()
if len(root_components) != 2:
    component_details = []
    for component in root_components:
        vertices = {vertex for edge in component for vertex in edge.verts}
        component_details.append(
            {
                "edge_count": len(component),
                "min_z": min(vertex.co.z for vertex in vertices),
                "max_z": max(vertex.co.z for vertex in vertices),
                "min_x": min(vertex.co.x for vertex in vertices),
                "max_x": max(vertex.co.x for vertex in vertices),
                "centerline_edges": sum(
                    all(abs(vertex.co.x) < 0.0002 for vertex in edge.verts)
                    for edge in component
                ),
            }
        )
    raise RuntimeError(
        "expected two compact root holes, found "
        f"{component_details}"
    )
root_cycles = [ordered_cycle(component) for component in root_components]
root_cycles.sort(
    key=lambda cycle: sum(vertex.co.z for vertex in cycle) / len(cycle),
    reverse=True,
)
shaft_root, scrotal_root = root_cycles

vertex_uv: dict[bmesh.types.BMVert, Vector] = {}
new_vertices: list[bmesh.types.BMVert] = []
new_faces: list[bmesh.types.BMFace] = []
shaft_uv = average_boundary_uv(shaft_root, uv_layer)
scrotal_uv = average_boundary_uv(scrotal_root, uv_layer)
for cycle, uv_center in (
    (shaft_root, shaft_uv),
    (scrotal_root, scrotal_uv),
):
    for vertex in cycle:
        values = [
            loop[uv_layer].uv.copy()
            for face in vertex.link_faces
            for loop in face.loops
            if uv_layer is not None and loop.vert is vertex
        ]
        vertex_uv[vertex] = (
            sum(values, Vector((0.0, 0.0))) / len(values)
            if values
            else uv_center.copy()
        )


def build_branch(
    root: list[bmesh.types.BMVert],
    *,
    centers: list[Vector],
    radii: list[tuple[float, float]],
    surface_class: int,
    uv_center: Vector,
    scrotal_envelope: bool = False,
) -> None:
    if len(centers) != len(radii):
        raise RuntimeError("branch centers and radii differ")
    root_center = sum((vertex.co for vertex in root), Vector()) / len(root)
    angles = cycle_angles(root, root_center)
    support = add_surface_normal_support_ring(
        bm,
        root,
        normal_offset=0.0036,
        down_offset=0.0008 if not scrotal_envelope else 0.0014,
        surface_class=surface_class,
        surface_class_layer=surface_class_layer,
        regional_mix_layer=regional_mix_layer,
        vertex_uv=vertex_uv,
        uv_center=uv_center,
        new_vertices=new_vertices,
    )
    connect_rings(
        bm,
        root,
        support,
        material_index=skin_index,
        new_faces=new_faces,
    )
    rings = [support]
    path = [root_center, *centers]
    for index, (center, (radius_x, radius_cross)) in enumerate(
        zip(centers, radii)
    ):
        previous = root_center if index == 0 else centers[index - 1]
        following = centers[index + 1] if index + 1 < len(centers) else center
        tangent = following - previous
        if tangent.length < 1.0e-8:
            tangent = Vector((0.0, -1.0, -0.1))
        ring = add_ideal_ring(
            bm,
            center=center,
            tangent=tangent,
            angles=angles,
            radius_x=radius_x,
            radius_cross=radius_cross,
            surface_class=surface_class,
            mix_value=min(1.0, 0.30 + 0.70 * (index + 1) / len(centers)),
            surface_class_layer=surface_class_layer,
            regional_mix_layer=regional_mix_layer,
            vertex_uv=vertex_uv,
            uv_center=uv_center,
            new_vertices=new_vertices,
            scrotal_envelope=scrotal_envelope,
            progress=(index + 1) / len(centers),
        )
        connect_rings(
            bm,
            rings[-1],
            ring,
            material_index=skin_index,
            new_faces=new_faces,
        )
        rings.append(ring)
    # A shallow terminal fan closes the rounded end.  The final ring is
    # already very small, so subdivision cannot create a long pointed cap.
    tangent = centers[-1] - centers[-2]
    terminal = centers[-1] + tangent.normalized() * 0.0022
    tip = bm.verts.new(terminal)
    tip[surface_class_layer] = surface_class
    tip[regional_mix_layer] = 1.0
    vertex_uv[tip] = uv_center.copy()
    new_vertices.append(tip)
    for index in range(len(rings[-1])):
        following = (index + 1) % len(rings[-1])
        face = bm.faces.new(
            (rings[-1][index], rings[-1][following], tip)
        )
        face.material_index = skin_index
        face.smooth = True
        new_faces.append(face)


shaft_root_center = sum((vertex.co for vertex in shaft_root), Vector()) / len(
    shaft_root
)
build_branch(
    shaft_root,
    centers=[
        Vector((0.0, shaft_root_center.y - 0.007, shaft_root_center.z - 0.003)),
        Vector((0.0, shaft_root_center.y - 0.018, shaft_root_center.z - 0.012)),
        Vector((0.0, -0.142, 0.758)),
        Vector((0.0, -0.153, 0.740)),
        Vector((0.0, -0.158, 0.722)),
        Vector((0.0, -0.160, 0.706)),
        Vector((0.0, -0.160, 0.695)),
        Vector((0.0, -0.160, 0.691)),
        Vector((0.0, -0.161, 0.688)),
        Vector((0.0, -0.161, 0.684)),
        Vector((0.0, -0.160, 0.679)),
        Vector((0.0, -0.159, 0.674)),
        Vector((0.0, -0.158, 0.670)),
    ],
    radii=[
        (0.0150, 0.0115),
        (0.0160, 0.0125),
        (0.0172, 0.0133),
        (0.0170, 0.0132),
        (0.0165, 0.0129),
        (0.0158, 0.0124),
        (0.0140, 0.0111),
        (0.0136, 0.0108),
        (0.0164, 0.0135),
        (0.0173, 0.0143),
        (0.0167, 0.0137),
        (0.0124, 0.0098),
        (0.0065, 0.0048),
    ],
    surface_class=2,
    uv_center=shaft_uv,
)

scrotal_root_center = sum(
    (vertex.co for vertex in scrotal_root),
    Vector(),
) / len(scrotal_root)
build_branch(
    scrotal_root,
    centers=[
        Vector(
            (
                0.0,
                scrotal_root_center.y - 0.006,
                scrotal_root_center.z - 0.004,
            )
        ),
        Vector((0.0, -0.118, 0.724)),
        Vector((0.0, -0.124, 0.707)),
        Vector((0.0, -0.124, 0.688)),
        Vector((0.0, -0.120, 0.671)),
        Vector((0.0, -0.114, 0.659)),
        Vector((0.0, -0.109, 0.653)),
    ],
    radii=[
        (0.0235, 0.0150),
        (0.0275, 0.0190),
        (0.0325, 0.0235),
        (0.0340, 0.0250),
        (0.0305, 0.0225),
        (0.0220, 0.0160),
        (0.0085, 0.0060),
    ],
    surface_class=1,
    uv_center=scrotal_uv,
    scrotal_envelope=True,
)

sealed_inherited_inner_hole_faces = 0
inner_boundary_edges = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and all(
        abs(vertex.co.x) < 0.060
        and -0.025 < vertex.co.y < 0.100
        and 0.690 < vertex.co.z < 0.820
        for vertex in edge.verts
    )
]
for component in edge_components(inner_boundary_edges):
    component_vertices = {
        vertex for edge in component for vertex in edge.verts
    }
    if (
        len(component) < 4
        or min(vertex.co.y for vertex in component_vertices) <= -0.025
    ):
        continue
    fill_result = bmesh.ops.holes_fill(
        bm,
        edges=component,
        sides=0,
    )
    for face in fill_result.get("faces", []):
        face.material_index = skin_index
        face.smooth = True
        new_faces.append(face)
        sealed_inherited_inner_hole_faces += 1

if uv_layer is not None:
    for face in new_faces:
        for loop in face.loops:
            loop[uv_layer].uv = vertex_uv.get(
                loop.vert,
                shaft_uv if loop.vert.co.z > 0.705 else scrotal_uv,
            )

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(body.data)
bm.free()
body.data.update()

# Modest, feathered body refinement below the neck.  Hands, feet, face, neck,
# and the authored central anatomy remain position locked.
slimmed_counts = {
    "abdomen_waist": 0,
    "chest": 0,
    "upper_arms": 0,
    "thighs": 0,
}
surface_attribute = body.data.attributes.get("V23_Surface_Class")
for vertex in body.data.vertices:
    co = vertex.co
    if (
        surface_attribute is not None
        and surface_attribute.data[vertex.index].value in {1, 2}
    ):
        continue
    absolute_x = abs(co.x)
    if 0.88 <= co.z <= 1.24 and absolute_x < 0.30:
        co.x *= 0.935
        co.y *= 0.935
        slimmed_counts["abdomen_waist"] += 1
    elif 1.24 < co.z <= 1.53 and absolute_x < 0.34:
        co.x *= 0.955
        co.y *= 0.950
        slimmed_counts["chest"] += 1
    elif 1.02 <= co.z <= 1.47 and 0.30 <= absolute_x <= 0.48:
        center_x = 0.355 if co.x > 0.0 else -0.355
        co.x = center_x + (co.x - center_x) * 0.965
        co.y *= 0.970
        slimmed_counts["upper_arms"] += 1
    elif 0.36 <= co.z <= 0.94 and 0.070 <= absolute_x <= 0.36:
        vertical = smoothstep((co.z - 0.36) / 0.08) * smoothstep(
            (0.94 - co.z) / 0.08
        )
        lateral = smoothstep((absolute_x - 0.070) / 0.050) * smoothstep(
            (0.36 - absolute_x) / 0.060
        )
        weight = vertical * lateral
        center_x = 0.18 if co.x > 0.0 else -0.18
        co.x = center_x + (co.x - center_x) * (1.0 - 0.032 * weight)
        co.y *= 1.0 - 0.028 * weight
        slimmed_counts["thighs"] += 1
body.data.update()

applied_post = []
removed_post = []
bpy.context.view_layer.objects.active = body
body.select_set(True)
for modifier in list(body.modifiers):
    if modifier.type == "DISPLACE":
        removed_post.append((modifier.name, modifier.type))
        bpy.ops.object.modifier_remove(modifier=modifier.name)
    else:
        applied_post.append((modifier.name, modifier.type))
        bpy.ops.object.modifier_apply(modifier=modifier.name)

# Fair only the recessed high-resolution center seam and the proximal support
# rings after the two compact roots already exist.  Lateral V1 anatomy and all
# distal authored anatomy are pinned.  This is a bounded surface repair, not a
# global body scale or panel projection.
postfair_vertices_moved = 0
postfair_max_y_delta = 0.0
surface_class_postfair = body.data.attributes.get("V23_Surface_Class")
for vertex in body.data.vertices:
    co = vertex.co
    if not (
        abs(co.x) < 0.060
        and -0.115 < co.y < -0.012
        and 0.695 < co.z < 0.818
    ):
        continue
    class_value = (
        int(surface_class_postfair.data[vertex.index].value)
        if surface_class_postfair is not None
        else 0
    )
    if class_value in {1, 2} and (co.y <= -0.100 or co.z < 0.705):
        continue
    progress = smoothstep((co.z - 0.700) / 0.112)
    target_y = -0.058 - 0.034 * progress
    if co.y <= target_y:
        continue
    lateral_weight = smoothstep((0.060 - abs(co.x)) / 0.050)
    vertical_weight = smoothstep((co.z - 0.695) / 0.018) * smoothstep(
        (0.818 - co.z) / 0.018
    )
    weight = 0.82 * lateral_weight * vertical_weight
    y_delta = max(-0.038, (target_y - co.y) * weight)
    if abs(y_delta) <= 1.0e-7:
        continue
    co.y += y_delta
    postfair_vertices_moved += 1
    postfair_max_y_delta = max(postfair_max_y_delta, abs(y_delta))
body.data.update()

# The V1 source contains one closed internal central boundary behind the
# doll-safe region.  In front view it appears as a black teardrop even after
# the external surface is repaired.  Close only that bounded internal loop so
# the final primary surface no longer exposes the background.
postfill_bm = bmesh.new()
postfill_bm.from_mesh(body.data)
postfill_bm.verts.ensure_lookup_table()
postfill_bm.edges.ensure_lookup_table()
postfill_bm.faces.ensure_lookup_table()
postfill_uv_layer = postfill_bm.loops.layers.uv.active
postfill_edges = [
    edge
    for edge in postfill_bm.edges
    if len(edge.link_faces) == 1
    and all(
        abs(vertex.co.x) < 0.050
        and -0.020 < vertex.co.y < 0.100
        and 0.690 < vertex.co.z < 0.810
        for vertex in edge.verts
    )
]
postfill_faces = []
postfill_components = []
for component in edge_components(postfill_edges):
    vertices = {vertex for edge in component for vertex in edge.verts}
    adjacency: dict[bmesh.types.BMVert, int] = {}
    for edge in component:
        for vertex in edge.verts:
            adjacency[vertex] = adjacency.get(vertex, 0) + 1
    if (
        len(component) < 12
        or set(adjacency.values()) != {2}
        or min(vertex.co.z for vertex in vertices) > 0.730
        or max(vertex.co.z for vertex in vertices) < 0.770
    ):
        continue
    postfill_components.append(component)
    uv_values = []
    if postfill_uv_layer is not None:
        uv_values = [
            loop[postfill_uv_layer].uv.copy()
            for vertex in vertices
            for face in vertex.link_faces
            for loop in face.loops
            if loop.vert is vertex
        ]
    fill_uv = (
        sum(uv_values, Vector((0.0, 0.0))) / len(uv_values)
        if uv_values
        else Vector((0.52, 0.38))
    )
    result = bmesh.ops.triangle_fill(
        postfill_bm,
        edges=component,
        use_beauty=True,
        use_dissolve=False,
    )
    for face in result.get("faces", []):
        face.material_index = skin_index
        face.smooth = True
        if postfill_uv_layer is not None:
            for loop in face.loops:
                loop[postfill_uv_layer].uv = fill_uv
        postfill_faces.append(face)
if postfill_faces:
    bmesh.ops.recalc_face_normals(postfill_bm, faces=postfill_bm.faces)
postfill_bm.to_mesh(body.data)
postfill_bm.free()
body.data.update()

for polygon in body.data.polygons:
    polygon.use_smooth = True
body.data.update()

body.name = BODY_OUTPUT_NAME
body.parent = None
body["status"] = "ENGINEERING TRIAL — VISUAL REVIEW REQUIRED"
body["source_v1_sha256"] = source_sha256
body["method"] = (
    "PRESERVED V1 PUBIC SURFACE + TRUE MEDIAL WELD + "
    "COMPACT NORMAL-EXTRUDED ROOTS"
)
body["boolean_used"] = False
body["global_remesh_used"] = False
body["donor_surface_transferred"] = False
body["static_review_only"] = True
body["runtime_activation_allowed"] = False
body["movement_started"] = False
body["anatomy_estimation_label"] = (
    "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE"
)

final_topology = topology_counts(body)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

report = {
    "schema_version": 1,
    "status": body["status"],
    "source": str(SOURCE),
    "source_sha256": source_sha256,
    "output": str(BLEND_PATH),
    "method": body["method"],
    "true_medial_pairs_welded": len(TRUE_MEDIAL_PAIRS),
    "lateral_pairs_collapsed": 0,
    "medial_midpoints": medial_midpoints,
    "retained_surface_subdivision_face_count": len(subdivision_faces),
    "retained_surface_subdivision_edge_count": len(subdivision_edges),
    "shaft_root_face_count": len(shaft_faces),
    "scrotal_root_face_count": len(scrotal_faces),
    "shaft_root_boundary_vertices": len(shaft_root),
    "scrotal_root_boundary_vertices": len(scrotal_root),
    "sealed_inherited_inner_hole_faces": (
        sealed_inherited_inner_hole_faces
    ),
    "post_subdivision_center_fairing": {
        "vertices_moved": postfair_vertices_moved,
        "max_y_delta_meters": postfair_max_y_delta,
        "lateral_v1_surface_preserved": True,
        "distal_anatomy_pinned": True,
    },
    "post_subdivision_inner_boundary_closure": {
        "components_closed": len(postfill_components),
        "faces_created": len(postfill_faces),
    },
    "new_vertices_pre_subdivision": len(new_vertices),
    "new_faces_pre_subdivision": len(new_faces),
    "baseline_topology": baseline_topology,
    "final_topology": final_topology,
    "slimmed_vertex_counts": slimmed_counts,
    "pre_patch_modifiers_applied": applied_pre,
    "post_patch_modifiers_applied": applied_post,
    "post_patch_modifiers_removed": removed_post,
    "boolean_operations": 0,
    "global_remesh_operations": 0,
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
(OUT / "PRESERVED_SURFACE_BUILD_AND_TOPOLOGY_REPORT.json").write_text(
    json.dumps(report, indent=2) + "\n",
    encoding="utf-8",
)
print(BLEND_PATH)
print(json.dumps(report, indent=2))
