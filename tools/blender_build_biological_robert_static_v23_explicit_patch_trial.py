"""Build an isolated V23 explicit-patch engineering trial.

This trial starts from the intact V1 low-cage identity surface, removes the
proven 212-face bounded pelvis region, restores the unaffected portion of that
region, and replaces its connected central opening with one hand-authored
surface.  The replacement is stitched to existing V1 vertices and contains no
primitive anatomy objects, Boolean operations, copied donor surface, or
floating components.

The result is an engineering comparison only.  It does not authorize
movement, runtime attachment, activation, clothing, or duplication.
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
    "biological_static_likeness_v23_explicit_patch_trial"
)
OUT.mkdir(parents=True, exist_ok=True)

BODY_SOURCE_NAME = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1"
BODY_OUTPUT_NAME = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_EXPLICIT_PATCH_TRIAL"
BLEND_PATH = OUT / f"{BODY_OUTPUT_NAME}.blend"


def face_in_bounded_repair(center: Vector) -> bool:
    return (
        abs(center.x) <= 0.10
        and 0.62 <= center.z <= 0.88
        and -0.22 <= center.y <= 0.13
    )


def face_in_connected_root(center: Vector) -> bool:
    """Choose the two small mirrored front regions used by the local rebuild."""
    return (
        abs(center.x) < 0.035
        and center.y < -0.02
        and 0.70 < center.z < 0.80
    )


def edge_loop_components(
    edge_keys: list[tuple[int, int]],
) -> list[list[tuple[int, int]]]:
    vertex_to_edges: dict[int, list[tuple[int, int]]] = {}
    for edge_key in edge_keys:
        first, second = edge_key
        vertex_to_edges.setdefault(first, []).append(edge_key)
        vertex_to_edges.setdefault(second, []).append(edge_key)
    unseen = set(edge_keys)
    components: list[list[tuple[int, int]]] = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        component = [seed]
        while stack:
            current = stack.pop()
            for vertex_index in current:
                for neighbor_edge in vertex_to_edges[vertex_index]:
                    if neighbor_edge in unseen:
                        unseen.remove(neighbor_edge)
                        component.append(neighbor_edge)
                        stack.append(neighbor_edge)
        components.append(component)
    return components


def ordered_edge_loop(edge_keys: list[tuple[int, int]]) -> list[int]:
    adjacency: dict[int, list[int]] = {}
    for first, second in edge_keys:
        adjacency.setdefault(first, []).append(second)
        adjacency.setdefault(second, []).append(first)
    degree_set = {len(neighbors) for neighbors in adjacency.values()}
    if degree_set != {2}:
        raise RuntimeError(f"root boundary is not a simple loop: degrees={degree_set}")

    # Start at the most lateral right point.  Walk toward the superior point so
    # increasing parameter angle follows a consistent counter-clockwise course
    # in the front-view X/Z plane.
    start = max(adjacency, key=lambda index: source_coordinates[index].x)
    first_neighbors = adjacency[start]
    next_index = max(first_neighbors, key=lambda index: source_coordinates[index].z)
    ordered = [start, next_index]
    previous = start
    current = next_index
    while True:
        candidates = [index for index in adjacency[current] if index != previous]
        if len(candidates) != 1:
            raise RuntimeError("ambiguous root-boundary walk")
        following = candidates[0]
        if following == start:
            break
        if following in ordered:
            raise RuntimeError("root-boundary walk repeated before closure")
        ordered.append(following)
        previous, current = current, following
    if len(ordered) != len(adjacency):
        raise RuntimeError(
            f"root-boundary walk visited {len(ordered)} of {len(adjacency)} vertices"
        )
    return ordered


def gaussian(value: float, center: float, width: float) -> float:
    if width <= 0.0:
        return 0.0
    normalized = (value - center) / width
    return math.exp(-(normalized * normalized))


def local_edge_counts(obj: bpy.types.Object) -> dict[str, int]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    local_edges = [
        edge
        for edge in bm.edges
        if all(
            abs(vertex.co.x) < 0.145
            and -0.255 < vertex.co.y < 0.175
            and 0.585 < vertex.co.z < 0.915
            for vertex in edge.verts
        )
    ]
    result = {
        "edges": len(local_edges),
        "boundary_edges": sum(len(edge.link_faces) == 1 for edge in local_edges),
        "wire_edges": sum(len(edge.link_faces) == 0 for edge in local_edges),
        "nonmanifold_gt2_edges": sum(len(edge.link_faces) > 2 for edge in local_edges),
    }
    bm.free()
    return result


def mesh_component_sizes(obj: bpy.types.Object) -> list[int]:
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
        count = 1
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
                    count += 1
        sizes.append(count)
    bm.free()
    return sorted(sizes, reverse=True)


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get(BODY_SOURCE_NAME)
if body is None:
    raise RuntimeError("V1 body object is missing")

# V1's review-only primitive anatomy must not survive into this trial.
for obj in list(bpy.context.scene.objects):
    if any(
        token in obj.name
        for token in ("External_Anatomy_ESTIMATED", "Separate_Brown_Iris", "Separate_Pupil")
    ):
        bpy.data.objects.remove(obj, do_unlink=True)

source_vertex_count = len(body.data.vertices)
source_coordinates = [vertex.co.copy() for vertex in body.data.vertices]
source_sha256 = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
baseline_local_topology = local_edge_counts(body)
baseline_component_sizes = mesh_component_sizes(body)

# Capture the exact bounded V1 patch, including its material and active UV
# corner data, before any modifier is frozen.  Modifier application retains
# this low-cage vertex/face contract.
active_uv = body.data.uv_layers.active
patch_records: list[dict] = []
patch_face_indices: set[int] = set()
root_face_indices: set[int] = set()
patch_vertex_indices: set[int] = set()
for polygon in body.data.polygons:
    if not face_in_bounded_repair(polygon.center):
        continue
    patch_face_indices.add(polygon.index)
    if face_in_connected_root(polygon.center):
        root_face_indices.add(polygon.index)
    patch_vertex_indices.update(polygon.vertices)
    corner_uv = {}
    if active_uv is not None:
        for loop_index in polygon.loop_indices:
            loop = body.data.loops[loop_index]
            corner_uv[loop.vertex_index] = tuple(active_uv.data[loop_index].uv)
    patch_records.append(
        {
            "index": polygon.index,
            "vertices": tuple(polygon.vertices),
            "material_index": int(polygon.material_index),
            "uv": corner_uv,
        }
    )

if len(patch_face_indices) != 212:
    raise RuntimeError(f"expected the proven 212-face patch, found {len(patch_face_indices)}")
if len(root_face_indices) != 22:
    raise RuntimeError(f"expected 22 bounded front-root faces, found {len(root_face_indices)}")

# The V1 front is mirrored without a welded central front strip, so the
# coordinate selection contains two independent eleven-face regions.  Use the
# right-side region as the one topological opening and restore the other side;
# the authored transition shifts smoothly to X=0.  This avoids the figure-eight
# parameterization/self-intersection produced by trying to collapse both loops
# into one tube.
root_face_adjacency = {index: set() for index in root_face_indices}
root_edge_to_faces: dict[tuple[int, int], list[int]] = {}
for record in patch_records:
    if record["index"] not in root_face_indices:
        continue
    vertices = record["vertices"]
    for offset, first in enumerate(vertices):
        second = vertices[(offset + 1) % len(vertices)]
        key = tuple(sorted((first, second)))
        root_edge_to_faces.setdefault(key, []).append(record["index"])
for face_indices in root_edge_to_faces.values():
    for first in face_indices:
        root_face_adjacency[first].update(index for index in face_indices if index != first)
unseen_root_faces = set(root_face_indices)
root_face_components: list[set[int]] = []
while unseen_root_faces:
    seed = unseen_root_faces.pop()
    stack = [seed]
    component = {seed}
    while stack:
        current = stack.pop()
        for neighbor in root_face_adjacency[current]:
            if neighbor in unseen_root_faces:
                unseen_root_faces.remove(neighbor)
                component.add(neighbor)
                stack.append(neighbor)
    root_face_components.append(component)
if sorted(len(component) for component in root_face_components) != [11, 11]:
    raise RuntimeError(
        f"expected mirrored eleven-face root regions, found {[len(c) for c in root_face_components]}"
    )
record_by_index = {record["index"]: record for record in patch_records}


def component_mean_x(component: set[int]) -> float:
    members = {
        vertex_index
        for face_index in component
        for vertex_index in record_by_index[face_index]["vertices"]
    }
    return sum(source_coordinates[index].x for index in members) / len(members)


root_face_indices = max(root_face_components, key=component_mean_x)
patch_face_keys = {
    frozenset(record["vertices"])
    for record in patch_records
}

# Derive the 86-vertex outer stitch loop and the connected root opening from
# source topology.  No coordinate guessing is used for either seam.
kept_vertex_indices = {
    vertex_index
    for polygon in body.data.polygons
    if polygon.index not in patch_face_indices
    for vertex_index in polygon.vertices
}
outer_boundary_indices = patch_vertex_indices & kept_vertex_indices
if len(outer_boundary_indices) != 86:
    raise RuntimeError(
        f"expected the proven 86-vertex outer boundary, found {len(outer_boundary_indices)}"
    )

root_edge_counts: dict[tuple[int, int], int] = {}
root_vertex_indices: set[int] = set()
for record in patch_records:
    if record["index"] not in root_face_indices:
        continue
    vertices = record["vertices"]
    root_vertex_indices.update(vertices)
    for offset, first in enumerate(vertices):
        second = vertices[(offset + 1) % len(vertices)]
        key = tuple(sorted((first, second)))
        root_edge_counts[key] = root_edge_counts.get(key, 0) + 1
root_boundary_edges = [
    edge_key for edge_key, count in root_edge_counts.items() if count == 1
]
root_loop_components = edge_loop_components(root_boundary_edges)
if [len(component) for component in root_loop_components] != [16]:
    raise RuntimeError(
        "expected one 16-edge root loop, found "
        f"{[len(component) for component in root_loop_components]}"
    )
root_boundary_order = ordered_edge_loop(root_boundary_edges)
if len(root_boundary_order) != 16:
    raise RuntimeError(
        f"expected a 16-vertex root loop, found {len(root_boundary_order)}"
    )
root_boundary_set = set(root_boundary_order)
root_internal_indices = root_vertex_indices - root_boundary_set

# Normalize V1's duplicated skin face assignment without moving material slots.
for polygon in body.data.polygons:
    if polygon.material_index == 6:
        polygon.material_index = 1

# Freeze only vertex-count-dependent stages before changing topology.
applied_pre_patch_modifiers = []
bpy.context.view_layer.objects.active = body
body.select_set(True)
for modifier in list(body.modifiers):
    if modifier.type not in {"ARMATURE", "CORRECTIVE_SMOOTH"}:
        continue
    applied_pre_patch_modifiers.append((modifier.name, modifier.type))
    bpy.ops.object.modifier_apply(modifier=modifier.name)
post_modifier_coordinates = [vertex.co.copy() for vertex in body.data.vertices]

skin = bpy.data.materials.get("MBLab_skin3")
if skin is None:
    raise RuntimeError("V1 MBLab skin material is missing")
skin_index = next(
    index
    for index, material in enumerate(body.data.materials)
    if material and material.name == skin.name
)

# Remove all 212 original faces, then explicitly restore only the unaffected
# 150-face part.  Existing vertices remain available so the outer 86-vertex
# stitch is exact rather than proximity-welded.
bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()
bm_uv = bm.loops.layers.uv.active
source_index_layer = bm.verts.layers.int.get("V23_Source_Vertex_Index")
if source_index_layer is None:
    source_index_layer = bm.verts.layers.int.new("V23_Source_Vertex_Index")
for vertex in bm.verts:
    vertex[source_index_layer] = vertex.index
faces_to_delete = [
    face
    for face in bm.faces
    if frozenset(vertex.index for vertex in face.verts) in patch_face_keys
]
if len(faces_to_delete) != 212:
    raise RuntimeError(
        f"post-modifier patch signature matched {len(faces_to_delete)} faces, expected 212"
    )
bmesh.ops.delete(bm, geom=faces_to_delete, context="FACES")
bm.verts.ensure_lookup_table()
source_vertex_map = {
    vertex[source_index_layer]: vertex
    for vertex in bm.verts
    if vertex[source_index_layer] >= 0
}
missing_source_vertices = patch_vertex_indices - set(source_vertex_map)
for source_index in sorted(missing_source_vertices):
    vertex = bm.verts.new(post_modifier_coordinates[source_index])
    vertex[source_index_layer] = source_index
    source_vertex_map[source_index] = vertex

restored_faces = []
for record in patch_records:
    if record["index"] in root_face_indices:
        continue
    vertices = [source_vertex_map[index] for index in record["vertices"]]
    face = bm.faces.new(vertices)
    face.material_index = 1 if record["material_index"] == 6 else record["material_index"]
    face.smooth = True
    if bm_uv is not None:
        for loop in face.loops:
            uv = record["uv"].get(loop.vert[source_index_layer])
            if uv is not None:
                loop[bm_uv].uv = uv
    restored_faces.append(face)

# Remodel the lower anterior V1 patch as a broad, restrained asymmetric
# scrotal/perineal envelope.  Boundary vertices remain untouched.  The target
# is a continuous surface transition, not a pair of spheres.
sculpted_patch_vertices = 0
for vertex_index in patch_vertex_indices - outer_boundary_indices:
    if vertex_index in root_internal_indices:
        continue
    vertex = source_vertex_map[vertex_index]
    co = vertex.co
    if co.y >= 0.025 or co.z >= 0.765 or abs(co.x) >= 0.078:
        continue
    left_lobe = (
        gaussian(co.x, -0.018, 0.042)
        * gaussian(co.z, 0.668, 0.060)
        * gaussian(co.y, -0.065, 0.105)
    )
    right_lobe = (
        gaussian(co.x, 0.018, 0.041)
        * gaussian(co.z, 0.674, 0.056)
        * gaussian(co.y, -0.065, 0.105)
    )
    upper_bridge = (
        gaussian(co.x, 0.0, 0.055)
        * gaussian(co.z, 0.711, 0.048)
        * gaussian(co.y, -0.055, 0.105)
    )
    perineal_bridge = (
        gaussian(co.x, 0.0, 0.046)
        * gaussian(co.z, 0.655, 0.050)
        * gaussian(co.y, -0.005, 0.085)
    )
    weight = min(1.0, 0.55 * left_lobe + 0.52 * right_lobe + 0.38 * upper_bridge)
    co.y -= 0.058 * weight
    co.y -= 0.018 * perineal_bridge
    # Mild ordinary asymmetry: the left lower envelope hangs only a few
    # millimetres lower.  This is not a copied donor shape.
    co.z -= 0.0035 * left_lobe
    sculpted_patch_vertices += 1

# The V1 central front contains a deep doll-safe cleft that reads as a black
# hole under review lighting even though its edges are topologically closed.
# Bring only this small suprapubic transition forward; no global pelvis shift
# or censor geometry is used.
suprapubic_cleft_vertices = 0
for vertex_index in patch_vertex_indices - outer_boundary_indices:
    if vertex_index in root_internal_indices:
        continue
    vertex = source_vertex_map[vertex_index]
    co = vertex.co
    if abs(co.x) < 0.038 and 0.785 < co.z < 0.846 and co.y > -0.112:
        lateral_fade = 1.0 - min(1.0, abs(co.x) / 0.038)
        vertical_fade = 1.0 - min(1.0, abs(co.z - 0.815) / 0.031)
        weight = max(0.0, lateral_fade * vertical_fade)
        target_y = -0.102
        co.y = co.y * (1.0 - weight) + min(co.y, target_y) * weight
        suprapubic_cleft_vertices += 1

# Root boundary vertices now define the only opening in the restored patch.
root_boundary_vertices = [source_vertex_map[index] for index in root_boundary_order]
root_center = sum((vertex.co for vertex in root_boundary_vertices), Vector()) / len(
    root_boundary_vertices
)

# Parameterize the ordered topological loop.  The rightmost point is theta=0;
# its chosen walk direction goes superiorly, matching the X/Z plane convention.
segment_count = len(root_boundary_vertices)
theta_values = [2.0 * math.pi * index / segment_count for index in range(segment_count)]


def transition_point(
    boundary_point: Vector,
    theta: float,
    amount: float,
    center: Vector,
    radius_x: float,
    radius_z: float,
    upper_y: float,
    lower_y: float,
) -> Vector:
    sine = math.sin(theta)
    lower_weight = (1.0 - sine) * 0.5
    target = Vector(
        (
            center.x + radius_x * math.cos(theta),
            upper_y * (1.0 - lower_weight) + lower_y * lower_weight,
            center.z + radius_z * sine,
        )
    )
    return boundary_point.lerp(target, amount)


# Three broad fascia/envelope rings convert the irregular V1 opening into a
# smooth explicit root.  The lower arc stays behind and fuller to define the
# scrotal/perineal envelope; the upper arc advances into the pubic root.
ring_coordinates: list[list[Vector]] = [
    [vertex.co.copy() for vertex in root_boundary_vertices],
    [
        transition_point(
            vertex.co,
            theta,
            0.40,
            Vector((0.0, -0.076, 0.748)),
            0.038,
            0.048,
            -0.078,
            -0.111,
        )
        for vertex, theta in zip(root_boundary_vertices, theta_values)
    ],
    [
        transition_point(
            vertex.co,
            theta,
            0.80,
            Vector((0.0, -0.096, 0.738)),
            0.030,
            0.035,
            -0.096,
            -0.130,
        )
        for vertex, theta in zip(root_boundary_vertices, theta_values)
    ],
    [
        transition_point(
            vertex.co,
            theta,
            1.0,
            Vector((0.0, -0.116, 0.727)),
            0.025,
            0.027,
            -0.114,
            -0.141,
        )
        for vertex, theta in zip(root_boundary_vertices, theta_values)
    ],
]

# A single continuous phrase-like path of cross-sections defines visible root,
# shaft body, neck, coronal flare, glans, and tip.  These are rings in the same
# surface, never separately generated or concatenated objects.
shaft_sections = [
    # center Y, center Z, horizontal radius, cross radius
    (-0.129, 0.717, 0.0230, 0.0220),
    (-0.143, 0.705, 0.0205, 0.0200),
    (-0.152, 0.691, 0.0185, 0.0185),
    (-0.156, 0.676, 0.0165, 0.0165),  # neck
    (-0.158, 0.670, 0.0230, 0.0220),  # coronal flare
    (-0.159, 0.659, 0.0220, 0.0205),  # glans body
    (-0.158, 0.648, 0.0155, 0.0140),
    (-0.156, 0.642, 0.0065, 0.0060),
]
for y_center, z_center, radius_x, radius_cross in shaft_sections:
    ring_coordinates.append(
        [
            Vector(
                (
                    radius_x * math.cos(theta),
                    y_center,
                    z_center + radius_cross * math.sin(theta),
                )
            )
            for theta in theta_values
        ]
    )

# The first ring reuses the body/root vertices exactly.  Every subsequent ring
# is newly authored.  Consecutive rings are connected with quads and the distal
# surface closes with a single fan.
rings: list[list[bmesh.types.BMVert]] = [root_boundary_vertices]
new_anatomy_vertices: list[bmesh.types.BMVert] = []
new_anatomy_faces: list[bmesh.types.BMFace] = []
for coordinates in ring_coordinates[1:]:
    ring = [bm.verts.new(coordinate) for coordinate in coordinates]
    rings.append(ring)
    new_anatomy_vertices.extend(ring)

for first_ring, second_ring in zip(rings, rings[1:]):
    for index in range(segment_count):
        nxt = (index + 1) % segment_count
        face = bm.faces.new(
            (
                first_ring[index],
                first_ring[nxt],
                second_ring[nxt],
                second_ring[index],
            )
        )
        face.material_index = skin_index
        face.smooth = True
        new_anatomy_faces.append(face)

tip_center = bm.verts.new(Vector((0.0, -0.155, 0.640)))
new_anatomy_vertices.append(tip_center)
last_ring = rings[-1]
for index in range(segment_count):
    nxt = (index + 1) % segment_count
    face = bm.faces.new((last_ring[index], last_ring[nxt], tip_center))
    face.material_index = skin_index
    face.smooth = True
    new_anatomy_faces.append(face)

# Remove only vertices that belonged exclusively to the omitted 62 V1 faces
# and remain unused.  This prevents invisible wire debris while preserving
# every vertex referenced by the restored body patch.
unused_root_vertices = [
    source_vertex_map[index]
    for index in root_internal_indices
    if index in source_vertex_map and not source_vertex_map[index].link_faces
]
if unused_root_vertices:
    bmesh.ops.delete(bm, geom=unused_root_vertices, context="VERTS")

# Assign the same lower-abdomen skin UV neighborhood to newly authored loops.
# This retains V1's material response without baking AO/cavity into albedo.
if bm_uv is not None:
    donor_uv = Vector((0.52, 0.38))
    donor_found = False
    for face in bm.faces:
        center = face.calc_center_median()
        if (
            face.material_index == skin_index
            and abs(center.x) < 0.08
            and center.y < -0.12
            and 0.90 < center.z < 1.05
        ):
            values = [loop[bm_uv].uv.copy() for loop in face.loops]
            if values:
                donor_uv = sum(values, Vector((0.0, 0.0))) / len(values)
                donor_found = True
                break
    for face in new_anatomy_faces:
        for loop in face.loops:
            co = loop.vert.co
            loop[bm_uv].uv = donor_uv + Vector(
                (co.x * 0.065, (co.z - 0.72) * 0.050)
            )
else:
    donor_found = False

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

# Topological truth checks before subdivision.  Every edge touching a newly
# authored vertex must have exactly two incident faces.
new_vertex_set = set(new_anatomy_vertices)
new_edges = {
    edge
    for vertex in new_vertex_set
    for edge in vertex.link_edges
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
    raise RuntimeError(f"explicit patch failed incidence gate: {new_edge_incidence}")

bm.to_mesh(body.data)
bm.free()
body.data.update()
pre_finishing_local_topology = local_edge_counts(body)

# Apply the remaining V1 finishing stack in order.  Subdivision smooths the
# explicit 54-segment surface; no Boolean/remesh operation is introduced.
applied_post_patch_modifiers = []
bpy.context.view_layer.objects.active = body
body.select_set(True)
for modifier in list(body.modifiers):
    applied_post_patch_modifiers.append((modifier.name, modifier.type))
    bpy.ops.object.modifier_apply(modifier=modifier.name)

for polygon in body.data.polygons:
    polygon.use_smooth = True

body.name = BODY_OUTPUT_NAME
body["status"] = "REJECTED VISUAL ENGINEERING EVIDENCE — NOT OWNER APPROVED"
body["source_v1_sha256"] = source_sha256
body["anatomy_method"] = (
    "212-FACE BOUNDED DELETE + 86-VERTEX OUTER RESTORE + "
    "16-VERTEX EXPLICIT CONNECTED PATCH WITH CENTERED TRANSITION; NO BOOLEAN"
)
body["anatomy_estimation_label"] = "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE"
body["medical_reference_scope"] = "STRUCTURAL LANDMARK GUIDANCE ONLY"
body["donor_surface_transferred"] = False
body["boolean_used"] = False
body["runtime_activation_allowed"] = False
body["movement_started"] = False

final_local_topology = local_edge_counts(body)
final_component_sizes = mesh_component_sizes(body)

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

report = {
    "schema_version": 1,
    "status": body["status"],
    "source": str(SOURCE),
    "source_v1_sha256": source_sha256,
    "output": str(BLEND_PATH),
    "source_vertex_count": source_vertex_count,
    "bounded_deleted_faces": len(patch_face_indices),
    "outer_stitch_vertices_reused": len(outer_boundary_indices),
    "restored_unaffected_patch_faces": len(restored_faces),
    "connected_root_faces_replaced": len(root_face_indices),
    "connected_root_boundary_vertices_reused": len(root_boundary_order),
    "explicit_new_vertices_pre_subdivision": len(new_anatomy_vertices),
    "explicit_new_faces_pre_subdivision": len(new_anatomy_faces),
    "sculpted_existing_patch_vertices": sculpted_patch_vertices,
    "suprapubic_cleft_vertices_repositioned": suprapubic_cleft_vertices,
    "unused_root_vertices_removed": len(unused_root_vertices),
    "pre_patch_modifiers_applied": applied_pre_patch_modifiers,
    "post_patch_modifiers_applied": applied_post_patch_modifiers,
    "boolean_operations": 0,
    "primitive_anatomy_objects": 0,
    "donor_surface_transferred": False,
    "new_patch_edge_incidence_pre_subdivision": new_edge_incidence,
    "baseline_local_topology": baseline_local_topology,
    "pre_finishing_local_topology": pre_finishing_local_topology,
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
    "medical_landmarks_authored": [
        "continuous pubic/root attachment",
        "shaft body",
        "neck",
        "coronal flare",
        "glans body and distal tip",
        "broad asymmetric scrotal envelope",
        "perineal transition",
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
    "visual_gate": {
        "status": "FAIL",
        "full_resolution_views_inspected": [
            "close_pelvis_front",
            "close_pelvis_side",
            "close_pelvis_left_three_quarter",
            "close_pelvis_right_three_quarter",
        ],
        "failures": [
            "central suprapubic cleft still reads as a dark opening",
            "unilateral attachment creates a triangular three-quarter transition",
            "scrotal envelope is not clearly or naturally expressed",
            "root/shaft transition remains too simplified",
        ],
        "promotion_allowed": False,
    },
}
(OUT / "EXPLICIT_PATCH_BUILD_AND_TOPOLOGY_REPORT.json").write_text(
    json.dumps(report, indent=2) + "\n",
    encoding="utf-8",
)
print(BLEND_PATH)
print(json.dumps(report, indent=2))
