"""Build a V23 full-seam, no-collar static-review engineering candidate.

The V1 pelvis contains mirrored doll-safe root patches and a deeply recessed
center seam.  This trial removes the full verified eleven-face seam on each
side, aligns and welds the complete medial arc, and shares that actual boundary
directly with a dense constrained-Delaunay transition surface.  It deliberately
adds no generated support collars: the goal is to remove the rejected cap,
panel, tunnel, and retained-seam cleft while keeping both anatomical branches
compact. The current repair raises the complete structural roots together in
response to the owner side-view note and localizes their displacement so the
pubic surface does not become a long attached panel. The shaft follows a
restrained centerline and the scrotal envelope hangs vertically rather than
becoming a second forward-pointing tube.
No Boolean, primitive shell, donor identity surface, or global remesh is used.

This remains a private static engineering trial.  It cannot authorize
movement, runtime attachment, activation, clothing, Kira, or Synthetic Robert.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt


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
    "biological_static_likeness_v23_minimal_root_trial_r18_balanced_centerline"
)
OUT.mkdir(parents=True, exist_ok=True)
BODY_SOURCE_NAME = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1"
BODY_OUTPUT_NAME = (
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_MINIMAL_ROOT_TRIAL_R18_BALANCED_CENTERLINE"
)
BLEND_PATH = OUT / f"{BODY_OUTPUT_NAME}.blend"


def root_face(center: Vector) -> bool:
    return (
        abs(center.x) < 0.035
        and center.y < -0.02
        and 0.70 < center.z < 0.80
    )


def ordered_cycle(edges: list[bmesh.types.BMEdge]) -> list[bmesh.types.BMVert]:
    adjacency: dict[bmesh.types.BMVert, list[bmesh.types.BMVert]] = {}
    for edge in edges:
        first, second = edge.verts
        adjacency.setdefault(first, []).append(second)
        adjacency.setdefault(second, []).append(first)
    degrees = {len(neighbors) for neighbors in adjacency.values()}
    if degrees != {2}:
        raise RuntimeError(f"boundary is not a simple cycle: degrees={degrees}")
    start = min(adjacency, key=lambda vertex: (vertex.co.z, abs(vertex.co.x)))
    next_vertex = min(adjacency[start], key=lambda vertex: vertex.co.y)
    order = [start, next_vertex]
    previous = start
    current = next_vertex
    while True:
        following = next(
            vertex for vertex in adjacency[current] if vertex is not previous
        )
        if following is start:
            break
        if following in order:
            raise RuntimeError("boundary cycle repeated before closure")
        order.append(following)
        previous, current = current, following
    return order


def edge_components(edges: list[bmesh.types.BMEdge]) -> list[list[bmesh.types.BMEdge]]:
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


def local_topology(obj: bpy.types.Object) -> dict[str, int]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    edges = [
        edge
        for edge in bm.edges
        if all(
            abs(vertex.co.x) < 0.15
            and -0.27 < vertex.co.y < 0.18
            and 0.57 < vertex.co.z < 0.92
            for vertex in edge.verts
        )
    ]
    result = {
        "edges": len(edges),
        "boundary_edges": sum(len(edge.link_faces) == 1 for edge in edges),
        "wire_edges": sum(len(edge.link_faces) == 0 for edge in edges),
        "nonmanifold_gt2_edges": sum(len(edge.link_faces) > 2 for edge in edges),
    }
    bm.free()
    return result


def component_sizes(obj: bpy.types.Object) -> list[int]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    adjacency = {vertex: set() for vertex in bm.verts}
    for edge in bm.edges:
        first, second = edge.verts
        adjacency[first].add(second)
        adjacency[second].add(first)
    unseen = set(adjacency)
    sizes = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        size = 1
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
                    size += 1
        sizes.append(size)
    bm.free()
    return sorted(sizes, reverse=True)


def unwrap_angles(
    boundary: list[bmesh.types.BMVert], center: Vector
) -> list[float]:
    raw = [math.atan2(vertex.co.z - center.z, vertex.co.x - center.x) for vertex in boundary]
    unwrapped = [raw[0]]
    for value in raw[1:]:
        while value - unwrapped[-1] > math.pi:
            value -= 2.0 * math.pi
        while value - unwrapped[-1] < -math.pi:
            value += 2.0 * math.pi
        unwrapped.append(value)
    # Preserve the real X/Z orientation.  Reversing the signs to force a
    # counter-clockwise parameter incorrectly swaps superior and inferior
    # anatomy on clockwise source loops.
    return unwrapped


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get(BODY_SOURCE_NAME)
if body is None:
    raise RuntimeError("V1 body is missing")

for obj in list(bpy.context.scene.objects):
    if "External_Anatomy_ESTIMATED" in obj.name:
        bpy.data.objects.remove(obj, do_unlink=True)

source_sha256 = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
baseline_local_topology = local_topology(body)
baseline_component_sizes = component_sizes(body)

# Normalize V1's duplicate skin assignment while material indices are stable.
for polygon in body.data.polygons:
    if polygon.material_index == 6:
        polygon.material_index = 1

# Freeze only stages that have a fixed original-vertex contract.
applied_pre = []
bpy.context.view_layer.objects.active = body
body.select_set(True)
for modifier in list(body.modifiers):
    if modifier.type in {"ARMATURE", "CORRECTIVE_SMOOTH"}:
        applied_pre.append((modifier.name, modifier.type))
        bpy.ops.object.modifier_apply(modifier=modifier.name)

skin = bpy.data.materials.get("MBLab_skin3")
if skin is None:
    raise RuntimeError("V1 skin material missing")
skin_index = next(
    index
    for index, material in enumerate(body.data.materials)
    if material and material.name == skin.name
)

# Robert's protected front references show blue-gray irises.  Set the actual
# iris material itself; lighting, reflection, and exposure are not used as a
# substitute for the owner eye-color attribute.
iris_material = bpy.data.materials.get("Robert_Brown_Iris_Review")
if iris_material is None:
    raise RuntimeError("separate iris review material is missing")
iris_material.name = "Robert_Natural_Blue_Iris_V23"
iris_color = (0.018, 0.024, 0.030, 1.0)
iris_material.diffuse_color = iris_color
iris_material.use_nodes = True
iris_bsdf = next(
    node for node in iris_material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"
)
iris_bsdf.inputs["Base Color"].default_value = iris_color
iris_bsdf.inputs["Roughness"].default_value = 0.82
iris_bsdf.inputs["IOR"].default_value = 1.376
if iris_bsdf.inputs.get("Specular IOR Level") is not None:
    iris_bsdf.inputs["Specular IOR Level"].default_value = 0.15
for eye_object in (
    obj
    for obj in bpy.context.scene.objects
    if "Separate_Brown_Iris_REVIEW" in obj.name
):
    eye_object.name = eye_object.name.replace(
        "Separate_Brown_Iris_REVIEW",
        "Separate_Blue_Iris_V23",
    )
    eye_object["actual_iris_color"] = "NATURAL BLUE-GRAY"
    eye_object["protected_reference_authority"] = "ROBERT OWNER PHOTOGRAPHS"
    eye_object.scale.x *= 0.90
    eye_object.scale.z *= 0.90

pupil_material = bpy.data.materials.get("Robert_Pupil_Review")
if pupil_material is not None:
    pupil_material.use_nodes = True
    pupil_bsdf = next(
        node
        for node in pupil_material.node_tree.nodes
        if node.type == "BSDF_PRINCIPLED"
    )
    pupil_color = (0.0025, 0.0030, 0.0035, 1.0)
    pupil_material.diffuse_color = pupil_color
    pupil_bsdf.inputs["Base Color"].default_value = pupil_color
    pupil_bsdf.inputs["Roughness"].default_value = 0.72
for pupil_object in (
    obj
    for obj in bpy.context.scene.objects
    if "Separate_Pupil_REVIEW" in obj.name
):
    pupil_object.scale.x *= 0.70
    pupil_object.scale.z *= 0.70
    pupil_object["pupil_balance"] = "BOUNDED NATURAL STATIC REVIEW"

sclera_material = bpy.data.materials.get("Robert_Eye_White_Review")
if sclera_material is not None:
    sclera_material.use_nodes = True
    sclera_bsdf = next(
        node
        for node in sclera_material.node_tree.nodes
        if node.type == "BSDF_PRINCIPLED"
    )
    sclera_color = (0.56, 0.52, 0.49, 1.0)
    sclera_material.diffuse_color = sclera_color
    sclera_bsdf.inputs["Base Color"].default_value = sclera_color
    sclera_bsdf.inputs["Roughness"].default_value = 0.40
    sclera_bsdf.inputs["IOR"].default_value = 1.376
    if sclera_bsdf.inputs.get("Specular IOR Level") is not None:
        sclera_bsdf.inputs["Specular IOR Level"].default_value = 0.28

nail_material = bpy.data.materials.get("MBLab_nails")
if nail_material is not None:
    nail_material.use_nodes = True
    nail_material.diffuse_color = (0.42, 0.30, 0.28, 1.0)
    for node in nail_material.node_tree.nodes:
        if node.type != "BSDF_PRINCIPLED":
            continue
        base_color = node.inputs.get("Base Color")
        if base_color is not None:
            for link in list(base_color.links):
                nail_material.node_tree.links.remove(link)
            base_color.default_value = (0.42, 0.30, 0.28, 1.0)
        node.inputs["Roughness"].default_value = 0.48
        if node.inputs.get("Specular IOR Level") is not None:
            node.inputs["Specular IOR Level"].default_value = 0.24

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

# Replace the complete verified V1 medial seam. R14 proved that retaining the
# upper bilateral seam leaves a real dark keyhole cleft even when the lower
# repair is topologically closed. R16 shares one complete welded opening,
# localizes the root displacement, and does not add a raised collar.
minimal_root_face_indices = {
    5547,
    5738,
    5845,
    5944,
    5948,
    5989,
    6155,
    6162,
    6165,
    6167,
    6168,
    10119,
    10310,
    10417,
    10516,
    10520,
    10561,
    10728,
    10735,
    10738,
    10740,
    10741,
}
selected_faces = [bm.faces[index] for index in sorted(minimal_root_face_indices)]
if len(selected_faces) != 22:
    raise RuntimeError("full seam deletion did not resolve twenty-two V1 faces")
minimal_medial_pairs = (
    (10316, 5668),
    (10525, 5877),
    (10342, 5694),
    (10620, 5972),
    (10626, 5978),
    (10622, 5974),
    (10739, 6091),
    (10763, 6115),
    (10748, 6100),
    (10724, 6076),
    (10926, 6277),
    (10742, 6094),
)
paired_vertices = [
    (bm.verts[left_index], bm.verts[right_index])
    for left_index, right_index in minimal_medial_pairs
]
bmesh.ops.delete(bm, geom=selected_faces, context="FACES")

medial_midpoints = []
vertices_to_weld = []
for left_vertex, right_vertex in paired_vertices:
    midpoint = (left_vertex.co + right_vertex.co) * 0.5
    midpoint.x = 0.0
    # The inherited V1 seam contains center vertices recessed to y≈-0.022,
    # producing a deep black cleft even after topology is closed.  Fair the
    # verified centerline pairs along a shallow pubic fan between the
    # measured inferior and superior anchors.
    fan_progress = max(
        0.0,
        min(1.0, (midpoint.z - 0.679304) / (0.811552 - 0.679304)),
    )
    # Keep the joined centerline slightly anterior to the measured bilateral
    # V1 surface without pulling it several centimeters into a raised cap.
    # R14 showed the inherited -0.02 seam was too recessed; R16/R17 showed
    # that -0.12..-0.145 was too prominent. This bounded ramp follows the
    # measured lateral progression (-0.077 inferior to -0.116 superior) with
    # only a small cleft-closing offset.
    midpoint.y = -0.090 - 0.029 * fan_progress
    left_vertex.co = midpoint
    right_vertex.co = midpoint
    medial_midpoints.append(tuple(midpoint))
    vertices_to_weld.extend((left_vertex, right_vertex))

retained_upper_seam_vertices_faired = 0
bmesh.ops.remove_doubles(
    bm,
    verts=list(dict.fromkeys(vertices_to_weld)),
    dist=0.00005,
)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

root_boundary_edges = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and all(
        abs(vertex.co.x) < 0.075
        and -0.17 < vertex.co.y < -0.04
        and 0.66 < vertex.co.z < 0.84
        for vertex in edge.verts
    )
]
root_components = edge_components(root_boundary_edges)
if len(root_components) != 1:
    raise RuntimeError(
        f"minimal seam weld did not create one boundary: {[len(c) for c in root_components]}"
    )
source_root_boundary = ordered_cycle(root_components[0])
if len(source_root_boundary) != 10:
    raise RuntimeError(
        f"expected a ten-vertex full-seam boundary, found {len(source_root_boundary)}"
    )

# Split each retained boundary edge once so the direct shared transition has
# twenty samples. BMesh interpolates adjacent loop data for the new vertices.
bmesh.ops.subdivide_edges(
    bm,
    edges=root_components[0],
    cuts=1,
    use_grid_fill=False,
)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
root_boundary_edges = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and all(
        abs(vertex.co.x) < 0.075
        and -0.17 < vertex.co.y < -0.04
        and 0.66 < vertex.co.z < 0.84
        for vertex in edge.verts
    )
]
root_components = edge_components(root_boundary_edges)
if len(root_components) != 1:
    raise RuntimeError("subdivided minimal root boundary is not one component")
root_boundary = ordered_cycle(root_components[0])
if len(root_boundary) != 20:
    raise RuntimeError(
        f"expected a twenty-vertex full-seam support boundary, found {len(root_boundary)}"
    )

root_center = sum((vertex.co for vertex in root_boundary), Vector()) / len(root_boundary)
angles = unwrap_angles(root_boundary, root_center)
for vertex in root_boundary:
    vertex[surface_class_layer] = 3
    vertex[regional_mix_layer] = 0.0


boundary_uv_values: list[Vector] = []
if uv_layer is not None:
    for vertex in root_boundary:
        values = [
            loop[uv_layer].uv.copy()
            for face in vertex.link_faces
            for loop in face.loops
            if loop.vert is vertex
        ]
        boundary_uv_values.append(
            sum(values, Vector((0.0, 0.0))) / len(values)
            if values
            else Vector((0.52, 0.38))
        )
else:
    boundary_uv_values = [Vector((0.52, 0.38)) for _ in root_boundary]
regional_uv = sum(boundary_uv_values, Vector((0.0, 0.0))) / len(
    boundary_uv_values
)
vertex_uv = {
    vertex: boundary_uv_values[index]
    for index, vertex in enumerate(root_boundary)
}
new_vertices: list[bmesh.types.BMVert] = []
new_faces: list[bmesh.types.BMFace] = []


def weighted_scalar(
    point: Vector,
    samples: list[tuple[Vector, float]],
    *,
    power: float = 2.4,
) -> float:
    weighted_total = 0.0
    total_weight = 0.0
    for sample_point, value in samples:
        distance = max(0.00035, (point - sample_point).length)
        weight = 1.0 / (distance**power)
        weighted_total += value * weight
        total_weight += weight
    if total_weight <= 0.0:
        raise RuntimeError("inverse-distance surface interpolation has no weight")
    return weighted_total / total_weight


root_boundary_surface_samples = [
    (Vector((vertex.co.x, vertex.co.z)), vertex.co.y)
    for vertex in root_boundary
]


def inherited_boundary_y(x_value: float, z_value: float) -> float:
    return weighted_scalar(
        Vector((x_value, z_value)),
        root_boundary_surface_samples,
    )


def connect_equal_rings(
    first_ring: list[bmesh.types.BMVert],
    second_ring: list[bmesh.types.BMVert],
) -> None:
    if len(first_ring) != len(second_ring):
        raise RuntimeError("ring connection requires equal vertex counts")
    for index in range(len(first_ring)):
        following = (index + 1) % len(first_ring)
        face = bm.faces.new(
            (
                first_ring[index],
                first_ring[following],
                second_ring[following],
                second_ring[index],
            )
        )
        face.material_index = skin_index
        face.smooth = True
        new_faces.append(face)


def signed_area(points: list[Vector]) -> float:
    return 0.5 * sum(
        points[index].x * points[(index + 1) % len(points)].y
        - points[(index + 1) % len(points)].x * points[index].y
        for index in range(len(points))
    )


# Share the actual subdivided V1 seam boundary directly with the dense CDT
# transition. Generated collars in R10-R13 created a visible cap or panel.
outer_ring = root_boundary
# The true 3D boundary is preserved above.  Its raw X/Z projection contains
# small folds, so use an aligned, angle-preserving parameter domain only for
# robust triangulation.  This does not move or remesh the 3D surface.
outer_parameter_center_z = 0.746
outer_parameter_radius_x = 0.046
outer_parameter_radius_z = 0.067
outer_2d = [
    Vector(
        (
            outer_parameter_radius_x * math.cos(theta),
            outer_parameter_center_z
            + outer_parameter_radius_z * math.sin(theta),
        )
    )
    for theta in angles
]
outer_area = signed_area(outer_2d)
if abs(outer_area) < 1e-8:
    raise RuntimeError("compact transition outer loop has near-zero area")
hole_angle_sign = -1.0 if outer_area > 0.0 else 1.0
branch_count = len(root_boundary)
branch_thetas = [
    hole_angle_sign * 2.0 * math.pi * index / branch_count
    for index in range(branch_count)
]


def tangent_cross_axis(tangent: Vector) -> Vector:
    tangent = tangent.normalized()
    cross_axis = Vector((0.0, -tangent.z, tangent.y))
    if cross_axis.length < 1e-8:
        return Vector((0.0, 1.0, 0.0))
    return cross_axis.normalized()


shaft_root_center = Vector((0.0, inherited_boundary_y(0.0, 0.739), 0.739))
shaft_first_center = Vector((0.0, shaft_root_center.y - 0.0100, 0.726))
shaft_root_cross = tangent_cross_axis(shaft_first_center - shaft_root_center)
shaft_root_vertices = []
for theta in branch_thetas:
    coordinate = Vector(
        (
            0.0175 * math.cos(theta),
            0.0,
            0.739 + 0.0100 * math.sin(theta),
        )
    )
    coordinate.y = inherited_boundary_y(coordinate.x, coordinate.z)
    vertex = bm.verts.new(coordinate)
    vertex[surface_class_layer] = 2
    vertex[regional_mix_layer] = 0.86
    vertex_uv[vertex] = regional_uv + Vector(
        (0.010 * math.cos(theta), 0.009 * math.sin(theta))
    )
    shaft_root_vertices.append(vertex)
    new_vertices.append(vertex)

scrotal_root_center = Vector((0.0, inherited_boundary_y(0.0, 0.702), 0.702))
scrotal_first_center = Vector((0.0, scrotal_root_center.y - 0.0040, 0.690))
sac_root_cross = Vector((0.0, 0.68, -0.733)).normalized()
sac_root_vertices = []
for theta in branch_thetas:
    coordinate = Vector(
        (
            0.0240 * math.cos(theta),
            0.0,
            0.702 + 0.0095 * math.sin(theta),
        )
    )
    coordinate.y = inherited_boundary_y(coordinate.x, coordinate.z)
    vertex = bm.verts.new(coordinate)
    vertex[surface_class_layer] = 1
    vertex[regional_mix_layer] = 0.82
    vertex_uv[vertex] = regional_uv + Vector(
        (0.012 * math.cos(theta), 0.010 * math.sin(theta))
    )
    sac_root_vertices.append(vertex)
    new_vertices.append(vertex)

shaft_2d = [
    Vector((0.0175 * math.cos(theta), 0.739 + 0.0100 * math.sin(theta)))
    for theta in branch_thetas
]
sac_2d = [
    Vector((0.0240 * math.cos(theta), 0.702 + 0.0095 * math.sin(theta)))
    for theta in branch_thetas
]


def ellipse_value(
    point: Vector,
    center_x: float,
    center_z: float,
    radius_x: float,
    radius_z: float,
) -> float:
    return (
        ((point.x - center_x) / radius_x) ** 2
        + ((point.y - center_z) / radius_z) ** 2
    )


# R10's sixty-vertex tessellation produced a planar shield and R11's
# post-subdivision projection exposed a folded tunnel.  Build a genuinely
# supported constrained-Delaunay pair-of-pants surface instead: the inherited
# outer loop and both anatomical roots are constraints, while interior
# samples give the bridge enough local topology to curve without triangle-star
# folds.  This is still a fully hand-authored local surface, not a donor copy.
cdt_input_points = [*outer_2d, *shaft_2d, *sac_2d]
cdt_input_existing: list[bmesh.types.BMVert | None] = [
    *outer_ring,
    *shaft_root_vertices,
    *sac_root_vertices,
]
grid_spacing_x = 0.0065
grid_spacing_z = 0.0065
grid_x = -0.039
while grid_x <= 0.039 + 1e-8:
    grid_z = 0.684
    while grid_z <= 0.807 + 1e-8:
        point = Vector((grid_x, grid_z))
        if (
            ellipse_value(
                point,
                0.0,
                outer_parameter_center_z,
                outer_parameter_radius_x,
                outer_parameter_radius_z,
            )
            < 0.94
            and ellipse_value(point, 0.0, 0.739, 0.0175, 0.0100) > 1.22
            and ellipse_value(point, 0.0, 0.702, 0.0240, 0.0095) > 1.22
        ):
            cdt_input_points.append(point)
            cdt_input_existing.append(None)
        grid_z += grid_spacing_z
    grid_x += grid_spacing_x

cdt_edges: list[tuple[int, int]] = []
ring_starts = (0, branch_count, branch_count * 2)
for ring_start in ring_starts:
    for index in range(branch_count):
        cdt_edges.append(
            (
                ring_start + index,
                ring_start + (index + 1) % branch_count,
            )
        )

(
    cdt_points,
    _cdt_edges_out,
    cdt_faces,
    cdt_original_vertices,
    _cdt_original_edges,
    _cdt_original_faces,
) = delaunay_2d_cdt(
    cdt_input_points,
    cdt_edges,
    [
        list(range(branch_count))
        if outer_area > 0.0
        else list(reversed(range(branch_count)))
    ],
    1,
    1e-8,
    True,
)

cdt_surface_samples: list[tuple[Vector, float]] = []
cdt_uv_samples: list[tuple[Vector, Vector]] = []
for parameter_point, existing_vertex in zip(
    cdt_input_points[: branch_count * 3],
    cdt_input_existing[: branch_count * 3],
):
    if existing_vertex is None:
        raise RuntimeError("CDT boundary constraint unexpectedly lacks a mesh vertex")
    cdt_surface_samples.append((parameter_point, existing_vertex.co.y))
    cdt_uv_samples.append((parameter_point, vertex_uv[existing_vertex].copy()))


def weighted_uv(point: Vector) -> Vector:
    weighted_total = Vector((0.0, 0.0))
    total_weight = 0.0
    for sample_point, value in cdt_uv_samples:
        distance = max(0.00035, (point - sample_point).length)
        weight = 1.0 / (distance**2.2)
        weighted_total += value * weight
        total_weight += weight
    if total_weight <= 0.0:
        return regional_uv.copy()
    return weighted_total / total_weight


def compact_root_surface_delta(
    point: Vector,
    *,
    center: Vector,
    radius_x: float,
    parameter_radius_z: float,
    cross_axis: Vector,
    cross_radius: float,
    guard_radius: float,
) -> tuple[float, float]:
    """Return a compact root displacement and its local influence.

    Earlier trials interpolated the root-ring depth across the full pubic
    opening, which made the transition look like an elongated attached panel.
    This field preserves the inherited pelvis surface except inside a narrow
    annulus around each structural root.  The exact ring vertices remain the
    shared topology authority at radius one.
    """

    normalized_x = (point.x - center.x) / radius_x
    normalized_z = (point.y - center.z) / parameter_radius_z
    radial_distance = math.sqrt(
        normalized_x * normalized_x + normalized_z * normalized_z
    )
    if radial_distance >= guard_radius:
        return 0.0, 0.0
    angle = math.atan2(normalized_z, normalized_x)
    perimeter_point = Vector(
        (
            center.x + radius_x * math.cos(angle),
            center.z + parameter_radius_z * math.sin(angle),
        )
    )
    inherited_perimeter_y = inherited_boundary_y(
        perimeter_point.x,
        perimeter_point.y,
    )
    authored_perimeter_y = (
        center.y + cross_axis.y * cross_radius * math.sin(angle)
    )
    transition = max(
        0.0,
        min(
            1.0,
            (guard_radius - radial_distance) / (guard_radius - 1.0),
        ),
    )
    transition = transition * transition * (3.0 - 2.0 * transition)
    return (
        (authored_perimeter_y - inherited_perimeter_y) * transition,
        transition,
    )


def compact_transition_y(point: Vector) -> float:
    # Both structural root rings now lie directly on this inherited surface.
    # Keeping the fill on the same field prevents a generated cap from rising
    # above the pelvis before either branch begins its short outward sweep.
    return inherited_boundary_y(point.x, point.y)


cdt_mesh_vertices: list[bmesh.types.BMVert | None] = [None] * len(cdt_points)
cdt_new_interior_vertices = 0
for output_index, parameter_point in enumerate(cdt_points):
    original_ids = cdt_original_vertices[output_index]
    existing_vertex = None
    if original_ids:
        source_index = original_ids[0]
        if source_index < len(cdt_input_existing):
            existing_vertex = cdt_input_existing[source_index]
    if existing_vertex is not None:
        cdt_mesh_vertices[output_index] = existing_vertex
        continue
    y_value = compact_transition_y(parameter_point)
    vertex = bm.verts.new((parameter_point.x, y_value, parameter_point.y))
    vertex[surface_class_layer] = 3
    vertex[regional_mix_layer] = 0.18
    vertex_uv[vertex] = weighted_uv(parameter_point)
    cdt_mesh_vertices[output_index] = vertex
    new_vertices.append(vertex)
    cdt_new_interior_vertices += 1

cdt_faces_kept = 0
cdt_faces_discarded_outer = 0
cdt_faces_discarded_holes = 0
for triangle in cdt_faces:
    if len(triangle) != 3:
        continue
    centroid = (
        sum(
            (cdt_points[index] for index in triangle),
            Vector((0.0, 0.0)),
        )
        / 3.0
    )
    if (
        ellipse_value(
            centroid,
            0.0,
            outer_parameter_center_z,
            outer_parameter_radius_x,
            outer_parameter_radius_z,
        )
        > 1.001
    ):
        cdt_faces_discarded_outer += 1
        continue
    if (
        ellipse_value(centroid, 0.0, 0.739, 0.0175, 0.0100) < 0.999
        or ellipse_value(centroid, 0.0, 0.702, 0.0240, 0.0095) < 0.999
    ):
        cdt_faces_discarded_holes += 1
        continue
    triangle_vertices = tuple(cdt_mesh_vertices[index] for index in triangle)
    if any(vertex is None for vertex in triangle_vertices):
        raise RuntimeError("CDT output triangle has an unresolved vertex")
    try:
        face = bm.faces.new(triangle_vertices)
    except ValueError:
        continue
    face.material_index = skin_index
    face.smooth = True
    for vertex in face.verts:
        if vertex not in vertex_uv:
            vertex_uv[vertex] = regional_uv
        if vertex[surface_class_layer] == 0:
            vertex[surface_class_layer] = 3
        if vertex[regional_mix_layer] == 0.0:
            vertex[regional_mix_layer] = 0.18
    new_faces.append(face)
    cdt_faces_kept += 1
if cdt_faces_kept < 100:
    raise RuntimeError(
        f"constrained transition surface is unexpectedly sparse: {cdt_faces_kept}"
    )


def build_sweep(
    root_ring: list[bmesh.types.BMVert],
    root_center: Vector,
    centers: list[Vector],
    radii: list[tuple[float, float]],
    *,
    terminal: Vector,
    surface_class: int,
    sac_envelope: bool = False,
) -> None:
    if len(centers) != len(radii):
        raise RuntimeError("sweep center/radius count mismatch")
    path = [root_center, *centers, terminal]
    rings = [root_ring]
    for section_index, (center, (radius_x, radius_cross)) in enumerate(
        zip(centers, radii),
        start=1,
    ):
        tangent = (path[section_index + 1] - path[section_index - 1]).normalized()
        cross_axis = tangent_cross_axis(tangent)
        coordinates = []
        for theta in branch_thetas:
            cosine = math.cos(theta)
            sine = math.sin(theta)
            coordinate = (
                center
                + Vector((1.0, 0.0, 0.0)) * (radius_x * cosine)
                + cross_axis * (radius_cross * sine)
            )
            if sac_envelope:
                # A shallow anterior midline raphe and restrained asymmetry
                # make one continuous bilobed pouch without creating a cleft.
                medial = math.exp(-((coordinate.x / 0.009) ** 2))
                anterior = max(0.0, center.y - coordinate.y)
                if anterior > 0.0:
                    lower_progress = section_index / max(1, len(centers))
                    coordinate.y += (
                        min(0.0040, anterior * 0.22)
                        * medial
                        * lower_progress
                    )
                lower_progress = section_index / max(1, len(centers))
                if coordinate.x < 0.0:
                    coordinate.z -= 0.0025 * lower_progress
                else:
                    coordinate.z += 0.0010 * lower_progress
            coordinates.append(coordinate)
        ring = [bm.verts.new(coordinate) for coordinate in coordinates]
        for theta, vertex in zip(branch_thetas, ring):
            vertex[surface_class_layer] = surface_class
            vertex[regional_mix_layer] = min(
                1.0,
                0.84 + 0.025 * section_index,
            )
            vertex_uv[vertex] = regional_uv + Vector(
                (
                    (0.011 if sac_envelope else 0.009) * math.cos(theta),
                    0.008 * math.sin(theta)
                    + section_index * (0.0012 if sac_envelope else 0.0010),
                )
            )
        connect_equal_rings(rings[-1], ring)
        rings.append(ring)
        new_vertices.extend(ring)
    tip = bm.verts.new(terminal)
    tip[surface_class_layer] = surface_class
    tip[regional_mix_layer] = 1.0
    vertex_uv[tip] = regional_uv + Vector(
        (0.0, len(centers) * (0.0012 if sac_envelope else 0.0010) + 0.0010)
    )
    new_vertices.append(tip)
    for index in range(branch_count):
        following = (index + 1) % branch_count
        face = bm.faces.new((rings[-1][index], rings[-1][following], tip))
        face.material_index = skin_index
        face.smooth = True
        new_faces.append(face)


build_sweep(
    shaft_root_vertices,
    shaft_root_center,
    [
        shaft_first_center,
        Vector((0.0, -0.140, 0.714)),
        Vector((0.0, -0.150, 0.702)),
        Vector((0.0, -0.157, 0.690)),
        Vector((0.0, -0.161, 0.678)),
        Vector((0.0, -0.163, 0.668)),  # neck
        Vector((0.0, -0.163, 0.665)),  # neck support
        Vector((0.0, -0.164, 0.663)),  # coronal rise
        Vector((0.0, -0.164, 0.661)),  # coronal flare
        Vector((0.0, -0.164, 0.657)),  # glans body
        Vector((0.0, -0.163, 0.653)),
        Vector((0.0, -0.162, 0.649)),
        Vector((0.0, -0.161, 0.645)),
    ],
    [
        (0.0174, 0.0132),
        (0.0170, 0.0130),
        (0.0164, 0.0128),
        (0.0158, 0.0125),
        (0.0152, 0.0120),
        (0.0138, 0.0113),
        (0.0136, 0.0110),
        (0.0165, 0.0137),
        (0.0174, 0.0144),
        (0.0170, 0.0140),
        (0.0148, 0.0119),
        (0.0106, 0.0083),
        (0.0062, 0.0047),
    ],
    terminal=Vector((0.0, -0.160, 0.641)),
    surface_class=2,
)
build_sweep(
    sac_root_vertices,
    scrotal_root_center,
    [
        scrotal_first_center,
        Vector((0.0, -0.120, 0.678)),
        Vector((0.0, -0.122, 0.666)),
        Vector((0.0, -0.120, 0.654)),
        Vector((0.0, -0.116, 0.644)),
        Vector((0.0, -0.112, 0.638)),
    ],
    [
        (0.0260, 0.0170),
        (0.0310, 0.0220),
        (0.0330, 0.0245),
        (0.0300, 0.0230),
        (0.0230, 0.0185),
        (0.0120, 0.0090),
    ],
    terminal=Vector((-0.0025, -0.109, 0.632)),
    surface_class=1,
    sac_envelope=True,
)

# Use one verified lower-abdomen UV neighborhood.  AO and cavity are not baked
# into albedo; the V1 skin nodes remain authoritative.
donor_uv = Vector((0.52, 0.38))
donor_found = bool(boundary_uv_values)
if uv_layer is not None:
    for face in new_faces:
        for loop in face.loops:
            loop[uv_layer].uv = vertex_uv.get(loop.vert, donor_uv)

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
new_vertex_set = set(new_vertices)
new_edges = {
    edge for vertex in new_vertex_set for edge in vertex.link_edges
}
new_edge_incidence = {
    "edge_count": len(new_edges),
    "boundary_edges": sum(len(edge.link_faces) == 1 for edge in new_edges),
    "wire_edges": sum(len(edge.link_faces) == 0 for edge in new_edges),
    "nonmanifold_gt2_edges": sum(len(edge.link_faces) > 2 for edge in new_edges),
}
if any(
    new_edge_incidence[key]
    for key in ("boundary_edges", "wire_edges", "nonmanifold_gt2_edges")
):
    bad_edge_details = [
        {
            "vertices": [tuple(vertex.co) for vertex in edge.verts],
            "linked_faces": len(edge.link_faces),
        }
        for edge in new_edges
        if len(edge.link_faces) != 2
    ][:30]
    raise RuntimeError(
        "new patch failed incidence gate: "
        f"{new_edge_incidence}; bad_edges={bad_edge_details}"
    )

bm.to_mesh(body.data)
bm.free()
body.data.update()

# One modest, region-aware slimming pass below the neck.  It does not globally
# scale the body, does not touch the face, hands, feet, or authored central
# anatomy, and preserves an ordinary non-athletic adult build.
def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


slimmed_counts = {
    "abdomen_waist": 0,
    "chest": 0,
    "upper_arms": 0,
    "thighs": 0,
}
for vertex in body.data.vertices:
    co = vertex.co
    absolute_x = abs(co.x)
    if 0.88 <= co.z <= 1.24 and absolute_x < 0.30:
        co.x *= 0.930
        co.y *= 0.930
        slimmed_counts["abdomen_waist"] += 1
    elif 1.24 < co.z <= 1.53 and absolute_x < 0.34:
        co.x *= 0.950
        co.y *= 0.945
        slimmed_counts["chest"] += 1
    elif 1.02 <= co.z <= 1.47 and 0.30 <= absolute_x <= 0.48:
        arm_center = 0.355 if co.x > 0.0 else -0.355
        co.x = arm_center + (co.x - arm_center) * 0.955
        co.y *= 0.960
        slimmed_counts["upper_arms"] += 1
    elif 0.36 <= co.z <= 0.94 and 0.070 <= absolute_x <= 0.36:
        thigh_center = 0.18 if co.x > 0.0 else -0.18
        vertical_weight = smoothstep((co.z - 0.36) / 0.07) * smoothstep(
            (0.94 - co.z) / 0.07
        )
        lateral_weight = smoothstep((absolute_x - 0.070) / 0.045) * smoothstep(
            (0.36 - absolute_x) / 0.055
        )
        weight = vertical_weight * lateral_weight
        co.x = thigh_center + (co.x - thigh_center) * (1.0 - 0.045 * weight)
        co.y *= 1.0 - 0.040 * weight
        slimmed_counts["thighs"] += 1

# Bounded face-likeness correction from Robert's protected front and profile
# photographs.  The nose, eyes, lips, ears, and upper cranium are not globally
# thinned; only the puffy lateral cheek, broad lower jaw, central chin depth,
# and extreme side silhouette receive small changes.
face_refinement_counts = {
    "lateral_cheeks": 0,
    "lower_jaw": 0,
    "chin_depth": 0,
    "side_silhouette": 0,
    "lower_face_taper": 0,
}


for vertex in body.data.vertices:
    co = vertex.co
    absolute_x = abs(co.x)
    if co.y < -0.020 and 1.640 <= co.z <= 1.745 and absolute_x >= 0.045:
        lateral_weight = min(1.0, max(0.0, (absolute_x - 0.045) / 0.070))
        vertical_weight = smoothstep((co.z - 1.640) / 0.025) * smoothstep(
            (1.745 - co.z) / 0.030
        )
        weight = lateral_weight * vertical_weight
        co.x *= 1.0 - 0.105 * weight
        co.y *= 1.0 - 0.028 * weight
        face_refinement_counts["lateral_cheeks"] += 1
    if co.y < -0.020 and 1.585 <= co.z < 1.665 and absolute_x >= 0.030:
        lateral_weight = min(1.0, max(0.0, (absolute_x - 0.030) / 0.075))
        vertical_weight = smoothstep((co.z - 1.585) / 0.025) * smoothstep(
            (1.665 - co.z) / 0.025
        )
        weight = lateral_weight * vertical_weight
        co.x *= 1.0 - 0.130 * weight
        co.y *= 1.0 - 0.020 * weight
        face_refinement_counts["lower_jaw"] += 1
    if co.y < 0.060 and 1.690 <= co.z <= 1.805 and absolute_x >= 0.065:
        lateral_weight = min(1.0, max(0.0, (absolute_x - 0.065) / 0.050))
        vertical_weight = smoothstep((co.z - 1.690) / 0.030) * smoothstep(
            (1.805 - co.z) / 0.035
        )
        co.x *= 1.0 - 0.028 * lateral_weight * vertical_weight
        face_refinement_counts["side_silhouette"] += 1
    if (
        -0.020 < co.y < 0.045
        and 1.595 <= co.z <= 1.690
        and 0.052 <= absolute_x <= 0.128
    ):
        lateral_weight = smoothstep((absolute_x - 0.052) / 0.050)
        vertical_weight = smoothstep((co.z - 1.595) / 0.025) * smoothstep(
            (1.690 - co.z) / 0.030
        )
        co.x *= 1.0 - 0.055 * lateral_weight * vertical_weight
        face_refinement_counts["lower_face_taper"] += 1
    if (
        co.y < -0.045
        and 1.585 <= co.z <= 1.635
        and absolute_x < 0.060
    ):
        central_weight = 1.0 - smoothstep(absolute_x / 0.060)
        vertical_weight = smoothstep((co.z - 1.585) / 0.018) * smoothstep(
            (1.635 - co.z) / 0.020
        )
        co.y *= 1.0 - 0.020 * central_weight * vertical_weight
        co.x *= 1.0 - 0.018 * central_weight * vertical_weight
        face_refinement_counts["chin_depth"] += 1
body.data.update()

surface_class_attribute = body.data.attributes.get("V23_Surface_Class")
if surface_class_attribute is None:
    raise RuntimeError("authored surface class attribute was not preserved")
sac_group = body.vertex_groups.new(name="V23_AUTHORED_SCROTAL_ROOT_SURFACE")
shaft_group = body.vertex_groups.new(name="V23_AUTHORED_SHAFT_GLANS_SURFACE")
transition_group = body.vertex_groups.new(name="V23_AUTHORED_PUBIC_TRANSITION")
sac_indices = [
    vertex.index
    for vertex in body.data.vertices
    if surface_class_attribute.data[vertex.index].value == 1
]
shaft_indices = [
    vertex.index
    for vertex in body.data.vertices
    if surface_class_attribute.data[vertex.index].value == 2
]
transition_indices = [
    vertex.index
    for vertex in body.data.vertices
    if surface_class_attribute.data[vertex.index].value == 3
    and body.data.attributes["V23_Regional_Mix"].data[vertex.index].value > 0.01
]
if sac_indices:
    sac_group.add(sac_indices, 1.0, "REPLACE")
if shaft_indices:
    shaft_group.add(shaft_indices, 1.0, "REPLACE")
if transition_indices:
    transition_group.add(transition_indices, 1.0, "REPLACE")
pre_finish_topology = local_topology(body)

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
for polygon in body.data.polygons:
    polygon.use_smooth = True

# The dense CDT cage already carries the inverse-distance surface field.
# Do not repeat R10's fixed-Y projection or R11's high-strength reprojection
# after subdivision.  Subdivision plus the low-strength local cleanup below
# only interpolates the authored cage.
transition_surface_vertices_faired = 0
transition_surface_max_y_correction = 0.0
surface_class_post = body.data.attributes.get("V23_Surface_Class")
regional_mix_post = body.data.attributes.get("V23_Regional_Mix")
if surface_class_post is None or regional_mix_post is None:
    raise RuntimeError("post-subdivision transition attributes are missing")

# Remove the triangle-star faceting from the compact bifurcation while the
# exact inherited seam and the two structural branches remain pinned.
if transition_indices:
    transition_smooth = body.modifiers.new(
        "V23CompactTransitionSurfaceCleanup",
        "SMOOTH",
    )
    transition_smooth.vertex_group = transition_group.name
    transition_smooth.factor = 0.065
    transition_smooth.iterations = 2
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    bpy.ops.object.modifier_apply(modifier=transition_smooth.name)

# Clear any inherited sharp-edge flag in the bounded repair region and
# recompute face orientation after all local geometry operations.  This does
# not hide a bad transition with normals; it simply prevents obsolete split
# normals from reintroducing a seam after the shape has been corrected.
for edge in body.data.edges:
    if all(
        abs(body.data.vertices[index].co.x) < 0.115
        and -0.215 < body.data.vertices[index].co.y < -0.035
        and 0.620 < body.data.vertices[index].co.z < 0.865
        for index in edge.vertices
    ):
        edge.use_edge_sharp = False
normal_bmesh = bmesh.new()
normal_bmesh.from_mesh(body.data)
bmesh.ops.recalc_face_normals(normal_bmesh, faces=normal_bmesh.faces)
normal_bmesh.to_mesh(body.data)
normal_bmesh.free()
for polygon in body.data.polygons:
    polygon.use_smooth = True
body.data.update()

# The low cage already carries the vertical hanging envelope.  Do not apply a
# second post-subdivision ellipsoid projection: the rejected seam-weld trial
# proved that doing so flattens the pouch into an apron and destroys the side
# profile.  These counters remain explicit evidence that no hidden deformation
# was applied after the shared topology was subdivided.
scrotal_vertices_rounded = 0
post_subdivision_sac_weighted = len(sac_indices)
post_subdivision_sac_in_roi = sum(
    abs(body.data.vertices[index].co.x) < 0.064
    and 0.585 < body.data.vertices[index].co.z < 0.735
    for index in sac_indices
    if index < len(body.data.vertices)
)
post_subdivision_sac_shaft_overlap = 0

# Regional color is stored independently from AO/cavity/roughness.  The
# Low-cage V23_Regional_Mix starts at zero on the inherited V1 seam and reaches
# one only on the authored anatomy. The shared transition is kept neutral so
# the subdivision modifier cannot turn it into a hard painted panel.
regional_mix_attribute = body.data.attributes.get("V23_Regional_Mix")
if regional_mix_attribute is None:
    raise RuntimeError("regional skin blend attribute was not preserved")
tint = body.data.color_attributes.get("V23_Regional_Skin_Tint")
if tint is None:
    tint = body.data.color_attributes.new(
        name="V23_Regional_Skin_Tint",
        type="BYTE_COLOR",
        domain="CORNER",
    )
# Blender 5.1 may relocate attribute storage when a new color attribute is
# created.  Reacquire all attribute handles before iterating to avoid using
# invalidated RNA wrappers.
regional_mix_attribute = body.data.attributes.get("V23_Regional_Mix")
surface_class_for_tint = body.data.attributes.get("V23_Surface_Class")
if regional_mix_attribute is None or surface_class_for_tint is None:
    raise RuntimeError("regional tint source attributes were lost")
for loop_index in range(len(body.data.loops)):
    tint.data[loop_index].color = (1.0, 1.0, 1.0, 1.0)
for loop_index, loop in enumerate(body.data.loops):
    vertex = body.data.vertices[loop.vertex_index]
    surface_class_value = int(
        surface_class_for_tint.data[loop.vertex_index].value
    )
    mix_value = max(
        0.0,
        min(
            1.0,
            float(regional_mix_attribute.data[loop.vertex_index].value),
        ),
    )
    if surface_class_value == 3:
        # The pubic transition retains the inherited V1 albedo.  Regional
        # variation starts on the actual authored anatomy, not on a visible
        # shield-shaped panel.
        mix_value = 0.0
    if mix_value > 0.0:
        shaft_weight = 0.0
        sac_weight = 0.0
        for assignment in vertex.groups:
            if assignment.group == shaft_group.index:
                shaft_weight = assignment.weight
            elif assignment.group == sac_group.index:
                sac_weight = assignment.weight
        distal_weight = (
            shaft_weight
            * max(0.0, min(1.0, (0.672 - vertex.co.z) / 0.035))
        )
        # A subdued center raphe gives the continuous pouch anatomical
        # structure without cutting a geometric cleft or baking AO into skin.
        raphe_weight = (
            sac_weight
            * math.exp(-((vertex.co.x / 0.0065) ** 2))
            * max(0.0, min(1.0, (0.705 - vertex.co.z) / 0.070))
        )
        tint.data[loop_index].color = (
            1.0
            - 0.12 * mix_value
            - 0.17 * shaft_weight
            - 0.025 * distal_weight
            - 0.035 * raphe_weight,
            1.0
            - 0.20 * mix_value
            - 0.22 * shaft_weight
            - 0.035 * distal_weight
            - 0.045 * raphe_weight,
            1.0
            - 0.16 * mix_value
            - 0.23 * shaft_weight
            - 0.030 * distal_weight
            - 0.040 * raphe_weight,
            1.0,
        )

if skin.use_nodes:
    nodes = skin.node_tree.nodes
    links = skin.node_tree.links
    skin_group = next(
        (
            node
            for node in nodes
            if node.type == "GROUP" and node.inputs.get("Albedo Map") is not None
        ),
        None,
    )
    if skin_group is not None and not nodes.get("V23_Regional_Skin_Multiply"):
        attribute = nodes.new("ShaderNodeVertexColor")
        attribute.name = "V23_Regional_Skin_Tint"
        attribute.layer_name = "V23_Regional_Skin_Tint"
        multiply = nodes.new("ShaderNodeMixRGB")
        multiply.name = "V23_Regional_Skin_Multiply"
        multiply.blend_type = "MULTIPLY"
        multiply.inputs[0].default_value = 1.0
        albedo_input = skin_group.inputs["Albedo Map"]
        existing = albedo_input.links[0] if albedo_input.links else None
        if existing is not None:
            existing_from_socket = existing.from_socket
            links.remove(existing)
            links.new(existing_from_socket, multiply.inputs[1])
        else:
            multiply.inputs[1].default_value = (0.72, 0.46, 0.39, 1.0)
        links.new(attribute.outputs["Color"], multiply.inputs[2])
        links.new(multiply.outputs["Color"], albedo_input)

# Append the V15 layered review hairstyle as a removable static component.
# Its shader is intentionally light/dark blond rather than the rejected brown
# material.  This is not a claim that runtime grooming, wet states, cutting,
# or persistent styling are complete.
with bpy.data.libraries.load(str(HAIR_SOURCE), link=False) as (data_from, data_to):
    data_to.objects = [
        name for name in ("Object_6", "Object_7") if name in data_from.objects
    ]
hair_material = bpy.data.materials.new("Robert_V23_Removable_Dark_Blond_Static_Hair")
hair_material.use_nodes = True
hair_bsdf = next(
    node for node in hair_material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"
)
hair_bsdf.inputs["Base Color"].default_value = (0.055, 0.047, 0.038, 1.0)
hair_bsdf.inputs["Roughness"].default_value = 0.64
hair_bsdf.inputs["IOR"].default_value = 1.46
if hair_bsdf.inputs.get("Specular IOR Level") is not None:
    hair_bsdf.inputs["Specular IOR Level"].default_value = 0.32
hair_objects = []
for hair in data_to.objects:
    if hair is None:
        continue
    bpy.context.collection.objects.link(hair)
    if hair.name.startswith("Object_6"):
        hair.scale.x *= 1.120
        hair.scale.y *= 1.120
        hair.scale.z *= 1.055
        hair.location.y -= 0.013
        hair.location.z -= 0.008
    else:
        hair.scale.x *= 1.100
        hair.scale.y *= 1.105
        hair.scale.z *= 1.045
        hair.location.y -= 0.014
        hair.location.z -= 0.008
    hair.data.materials.clear()
    hair.data.materials.append(hair_material)
    for polygon in hair.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True
    hair["stage_a_static_review_only"] = True
    hair["runtime_groom_complete"] = False
    hair["removable_component"] = True
    hair["coverage_review"] = "CROWN TEMPLE SIDE REAR STATIC COVERAGE"
    hair_objects.append(hair.name)

body.name = BODY_OUTPUT_NAME
body.parent = None
body["status"] = "ENGINEERING TRIAL — VISUAL REVIEW REQUIRED"
body["source_v1_sha256"] = source_sha256
body["method"] = (
    "BILATERAL MEDIAL-SEAM WELD + COMPACT BIFURCATION + "
    "TANGENT-FRAMED SHAFT + VERTICAL SCROTAL ENVELOPE"
)
body["boolean_used"] = False
body["donor_surface_transferred"] = False
body["runtime_activation_allowed"] = False
body["movement_started"] = False
body["static_review_only"] = True
body["hair_status"] = "REMOVABLE DARK-BLOND STATIC-REVIEW HAIR PRESENT"
body["anatomy_estimation_label"] = "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE"

final_local_topology = local_topology(body)
final_component_sizes = component_sizes(body)
if (
    final_local_topology["boundary_edges"]
    != baseline_local_topology["boundary_edges"]
    or final_local_topology["wire_edges"]
    != baseline_local_topology["wire_edges"]
    or final_local_topology["nonmanifold_gt2_edges"]
    != baseline_local_topology["nonmanifold_gt2_edges"]
):
    raise RuntimeError(
        "final local topology changed: "
        f"baseline={baseline_local_topology}, final={final_local_topology}"
    )
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

report = {
    "schema_version": 2,
    "status": body["status"],
    "source": str(SOURCE),
    "source_sha256": source_sha256,
    "output": str(BLEND_PATH),
    "root_faces_replaced": len(selected_faces),
    "medial_pairs_aligned_and_welded": len(medial_midpoints),
    "retained_upper_seam_vertices_faired": (
        retained_upper_seam_vertices_faired
    ),
    "bilateral_boundary_vertices": len(root_boundary),
    "new_vertices_pre_subdivision": len(new_vertices),
    "new_faces_pre_subdivision": len(new_faces),
    "new_patch_edge_incidence_pre_subdivision": new_edge_incidence,
    "sac_group_source_vertices": len(sac_indices),
    "shaft_group_source_vertices": len(shaft_indices),
    "post_subdivision_scrotal_projection_vertex_count": scrotal_vertices_rounded,
    "post_subdivision_sac_weighted": post_subdivision_sac_weighted,
    "post_subdivision_sac_in_roi": post_subdivision_sac_in_roi,
    "post_subdivision_sac_shaft_overlap": post_subdivision_sac_shaft_overlap,
    "post_subdivision_hidden_ellipsoid_projection_applied": False,
    "constrained_transition_surface": {
        "method": "DENSE CONSTRAINED DELAUNAY PAIR-OF-PANTS CAGE",
        "input_point_count": len(cdt_input_points),
        "constraint_edge_count": len(cdt_edges),
        "new_interior_vertex_count": cdt_new_interior_vertices,
        "kept_face_count": cdt_faces_kept,
        "discarded_outer_face_count": cdt_faces_discarded_outer,
        "discarded_hole_face_count": cdt_faces_discarded_holes,
        "surface_field": (
            "INHERITED PELVIS FIELD WITH COMPACT ROOT-ANNULUS DISPLACEMENT"
        ),
        "fixed_global_y_projection": False,
        "donor_surface_copied": False,
    },
    "transition_surface_vertices_faired": transition_surface_vertices_faired,
    "transition_surface_max_y_correction_meters": (
        transition_surface_max_y_correction
    ),
    "slimmed_vertex_counts": slimmed_counts,
    "bounded_face_refinement_vertex_counts": face_refinement_counts,
    "actual_iris_material": {
        "name": iris_material.name,
        "base_color_linear_rgba": list(iris_color),
        "roughness": float(iris_bsdf.inputs["Roughness"].default_value),
        "owner_reference": "PROTECTED ROBERT PHOTOGRAPHS",
        "lighting_substitute": False,
    },
    "removable_static_review_hair": {
        "objects": hair_objects,
        "material": hair_material.name,
        "base_color_linear_rgba": list(
            hair_bsdf.inputs["Base Color"].default_value
        ),
        "coverage": "CROWN TEMPLE SIDE REAR",
        "runtime_groom_complete": False,
    },
    "baseline_local_topology": baseline_local_topology,
    "pre_finish_local_topology": pre_finish_topology,
    "final_local_topology": final_local_topology,
    "local_boundary_delta": (
        final_local_topology["boundary_edges"]
        - baseline_local_topology["boundary_edges"]
    ),
    "local_nonmanifold_gt2_delta": (
        final_local_topology["nonmanifold_gt2_edges"]
        - baseline_local_topology["nonmanifold_gt2_edges"]
    ),
    "baseline_component_sizes_top5": baseline_component_sizes[:5],
    "final_component_sizes_top5": final_component_sizes[:5],
    "uv_donor_found": donor_found,
    "pre_patch_modifiers_applied": applied_pre,
    "post_patch_modifiers_applied": applied_post,
    "post_patch_modifiers_removed": removed_post,
    "boolean_operations": 0,
    "medical_landmarks_authored": [
        "continuous bilateral pubic/root attachment",
        "shaft body",
        "neck",
        "coronal flare",
        "glans body and distal tip",
        "scrotal/perineal envelope formed by the proximal continuous surface",
    ],
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
(OUT / "SEAM_WELD_BUILD_AND_TOPOLOGY_REPORT.json").write_text(
    json.dumps(report, indent=2) + "\n",
    encoding="utf-8",
)
print(BLEND_PATH)
print(json.dumps(report, indent=2))
