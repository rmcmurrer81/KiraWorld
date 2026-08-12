"""Build the V23 R25 compact pubic-bridge engineering trial.

The trial starts with the intact V1 low-cage identity surface, removes the
proven bounded pelvis patch, restores every unaffected V1 face, and replaces a
compact *bilateral* pubic/perineal region with one hand-authored connected
surface.  Both mirrored sides and their existing upper connector are replaced
together.  The bridge is internally subdivided and tangent-faired before two
compact anatomical roots are extruded from it.  No unilateral strip, primitive
anatomy objects, Boolean, remesh, floating shell, or donor identity surface is
used.

This is private static-review engineering evidence only.  It cannot authorize
movement, runtime attachment, activation, clothing, Kira work, or Synthetic
Robert duplication.
"""

from __future__ import annotations

import hashlib
import heapq
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon


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
    "biological_static_likeness_v23_r25_compact_pubic_bridge_trial"
)
OUT.mkdir(parents=True, exist_ok=True)

BODY_SOURCE_NAME = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1"
BODY_OUTPUT_NAME = (
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_R25_COMPACT_PUBIC_BRIDGE_TRIAL"
)
BLEND_PATH = OUT / f"{BODY_OUTPUT_NAME}.blend"


def face_in_bounded_repair(center: Vector) -> bool:
    return (
        abs(center.x) <= 0.10
        and 0.62 <= center.z <= 0.88
        and -0.22 <= center.y <= 0.13
    )


def seed_face(center: Vector) -> bool:
    """Two compact mirrored regions spanning pubic, scrotal, and perineal form."""
    return (
        abs(center.x) < 0.040
        and center.y < -0.020
        and 0.665 < center.z < 0.805
    )


def face_components(face_indices: set[int], adjacency: dict[int, set[int]]) -> list[set[int]]:
    unseen = set(face_indices)
    result: list[set[int]] = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        member = {seed}
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    member.add(neighbor)
                    stack.append(neighbor)
        result.append(member)
    return result


def cheapest_bilateral_connector(
    left: set[int],
    right: set[int],
    records: dict[int, dict],
    adjacency: dict[int, set[int]],
) -> list[int]:
    """Find the compact shared upper-center corridor between mirrored halves."""
    allowed = {
        index
        for index, record in records.items()
        if (
            abs(record["center"].x) < 0.075
            and record["center"].y < 0.035
            and 0.65 < record["center"].z < 0.855
        )
    }
    queue: list[tuple[float, int]] = []
    cost: dict[int, float] = {}
    predecessor: dict[int, int] = {}
    for index in left:
        cost[index] = 0.0
        heapq.heappush(queue, (0.0, index))
    target = None
    while queue:
        current_cost, current = heapq.heappop(queue)
        if current_cost != cost[current]:
            continue
        if current in right:
            target = current
            break
        for neighbor in adjacency[current]:
            if neighbor not in allowed:
                continue
            center = records[neighbor]["center"]
            step = (
                1.0
                + abs(center.x) * 4.0
                + max(0.0, center.y + 0.02) * 12.0
                + abs(center.z - 0.81) * 1.5
            )
            candidate = current_cost + step
            if candidate < cost.get(neighbor, float("inf")):
                cost[neighbor] = candidate
                predecessor[neighbor] = current
                heapq.heappush(queue, (candidate, neighbor))
    if target is None:
        raise RuntimeError("could not find a compact bilateral connector path")
    path = [target]
    while path[-1] not in left:
        path.append(predecessor[path[-1]])
    path.reverse()
    return path


def ordered_edge_loop(
    edge_keys: list[tuple[int, int]],
    coordinates: list[Vector],
) -> list[int]:
    adjacency: dict[int, list[int]] = {}
    for first, second in edge_keys:
        adjacency.setdefault(first, []).append(second)
        adjacency.setdefault(second, []).append(first)
    if {len(neighbors) for neighbors in adjacency.values()} != {2}:
        raise RuntimeError("bilateral replacement boundary is not one simple loop")
    start = max(adjacency, key=lambda index: coordinates[index].x)
    first_neighbor = max(adjacency[start], key=lambda index: coordinates[index].z)
    order = [start, first_neighbor]
    previous = start
    current = first_neighbor
    while True:
        candidate = next(index for index in adjacency[current] if index != previous)
        if candidate == start:
            break
        if candidate in order:
            raise RuntimeError("bilateral boundary repeated before closure")
        order.append(candidate)
        previous, current = current, candidate
    if len(order) != len(adjacency):
        raise RuntimeError(
            f"bilateral boundary visited {len(order)} of {len(adjacency)} vertices"
        )
    return order


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


def cumulative_loop_parameters(points: list[Vector]) -> list[float]:
    lengths = []
    total = 0.0
    for index, point in enumerate(points):
        following = points[(index + 1) % len(points)]
        length = (following - point).length
        lengths.append(length)
        total += length
    if total <= 1e-9:
        raise RuntimeError("bilateral boundary has zero arc length")
    parameters = [0.0]
    accumulated = 0.0
    for length in lengths[:-1]:
        accumulated += length
        parameters.append(2.0 * math.pi * accumulated / total)
    return parameters


def envelope_target(
    theta: float,
    center_z: float,
    radius_x: float,
    radius_z: float,
    upper_y: float,
    lower_y: float,
    lobe_depth: float,
    medial_relief: float,
    asymmetry: float,
) -> Vector:
    sine = math.sin(theta)
    cosine = math.cos(theta)
    lower_weight = max(0.0, -sine)
    side_weight = abs(cosine)
    upper_blend = 0.5 * (sine + 1.0)
    y = lower_y * (1.0 - upper_blend) + upper_y * upper_blend
    # Two continuous lower lobes are deeper laterally than at the medial raphe.
    y -= lobe_depth * lower_weight * side_weight
    y += medial_relief * lower_weight * (1.0 - side_weight)
    z = center_z + radius_z * sine
    # Restrained ordinary asymmetry: left lower lobe hangs a few millimetres lower.
    if lower_weight:
        z -= asymmetry * lower_weight * max(0.0, -cosine)
        z += asymmetry * 0.45 * lower_weight * max(0.0, cosine)
    return Vector((radius_x * cosine, y, z))


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get(BODY_SOURCE_NAME)
if body is None:
    raise RuntimeError("V1 body object is missing")

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

active_uv = body.data.uv_layers.active
patch_records: list[dict] = []
patch_face_indices: set[int] = set()
patch_vertex_indices: set[int] = set()
for polygon in body.data.polygons:
    if not face_in_bounded_repair(polygon.center):
        continue
    corner_uv = {}
    if active_uv is not None:
        for loop_index in polygon.loop_indices:
            loop = body.data.loops[loop_index]
            corner_uv[loop.vertex_index] = tuple(active_uv.data[loop_index].uv)
    record = {
        "index": polygon.index,
        "vertices": tuple(polygon.vertices),
        "material_index": int(polygon.material_index),
        "uv": corner_uv,
        "center": polygon.center.copy(),
        "edge_keys": tuple(tuple(sorted(edge)) for edge in polygon.edge_keys),
    }
    patch_records.append(record)
    patch_face_indices.add(polygon.index)
    patch_vertex_indices.update(polygon.vertices)
if len(patch_face_indices) != 212:
    raise RuntimeError(f"expected proven 212-face patch, found {len(patch_face_indices)}")

record_by_index = {record["index"]: record for record in patch_records}
edge_to_patch_faces: dict[tuple[int, int], list[int]] = {}
for record in patch_records:
    for edge_key in record["edge_keys"]:
        edge_to_patch_faces.setdefault(edge_key, []).append(record["index"])
patch_adjacency = {index: set() for index in patch_face_indices}
for face_indices in edge_to_patch_faces.values():
    for first in face_indices:
        patch_adjacency[first].update(
            index for index in face_indices if index != first
        )

bilateral_seed = {
    index
    for index, record in record_by_index.items()
    if seed_face(record["center"])
}
seed_components = sorted(
    face_components(bilateral_seed, patch_adjacency), key=len, reverse=True
)
if [len(component) for component in seed_components] != [14, 14]:
    raise RuntimeError(
        f"expected mirrored 14-face seeds, found {[len(c) for c in seed_components]}"
    )
left_seed, right_seed = sorted(
    seed_components,
    key=lambda component: sum(record_by_index[index]["center"].x for index in component),
)
connector_path = cheapest_bilateral_connector(
    left_seed,
    right_seed,
    record_by_index,
    patch_adjacency,
)
replacement_face_indices = bilateral_seed | set(connector_path)
replacement_components = face_components(replacement_face_indices, patch_adjacency)
if [len(component) for component in replacement_components] != [38]:
    raise RuntimeError(
        "bilateral replacement did not become one 38-face component: "
        f"{[len(c) for c in replacement_components]}"
    )

replacement_edge_counts: dict[tuple[int, int], int] = {}
replacement_vertex_indices: set[int] = set()
for face_index in replacement_face_indices:
    record = record_by_index[face_index]
    replacement_vertex_indices.update(record["vertices"])
    for edge_key in record["edge_keys"]:
        replacement_edge_counts[edge_key] = replacement_edge_counts.get(edge_key, 0) + 1
replacement_boundary_edges = [
    edge_key for edge_key, count in replacement_edge_counts.items() if count == 1
]
replacement_boundary_order = ordered_edge_loop(
    replacement_boundary_edges,
    source_coordinates,
)
if len(replacement_boundary_order) != 54:
    raise RuntimeError(
        f"expected compact 54-vertex bilateral boundary, found {len(replacement_boundary_order)}"
    )
replacement_boundary_set = set(replacement_boundary_order)
replacement_internal_indices = replacement_vertex_indices - replacement_boundary_set

# The two central connector faces are already one bilateral shared bridge in
# V1 topology. Their combined six-edge boundary becomes the authored shaft
# root. The wider 38-face region remains the explicit sculpt/retopology scope,
# but it is not collapsed into a ring (the earlier collapse caused fins).
root_face_indices = {10979, 10980}
if not root_face_indices.issubset(replacement_face_indices):
    raise RuntimeError("shared bilateral root faces are outside the replacement scope")
root_edge_counts: dict[tuple[int, int], int] = {}
root_vertex_indices: set[int] = set()
for face_index in root_face_indices:
    record = record_by_index[face_index]
    root_vertex_indices.update(record["vertices"])
    for edge_key in record["edge_keys"]:
        root_edge_counts[edge_key] = root_edge_counts.get(edge_key, 0) + 1
root_boundary_edges = [
    edge_key for edge_key, count in root_edge_counts.items() if count == 1
]
root_boundary_order = ordered_edge_loop(root_boundary_edges, source_coordinates)
if len(root_boundary_order) != 6:
    raise RuntimeError(
        f"expected six-vertex shared bilateral root boundary, found {len(root_boundary_order)}"
    )
root_boundary_set = set(root_boundary_order)
root_internal_indices = root_vertex_indices - root_boundary_set

kept_vertex_indices = {
    vertex_index
    for polygon in body.data.polygons
    if polygon.index not in patch_face_indices
    for vertex_index in polygon.vertices
}
outer_boundary_indices = patch_vertex_indices & kept_vertex_indices
if len(outer_boundary_indices) != 86:
    raise RuntimeError(
        f"expected proven 86-vertex outer patch boundary, found {len(outer_boundary_indices)}"
    )

patch_face_keys = {
    frozenset(record["vertices"])
    for record in patch_records
}

# Preserve all V1 skin, hands, nails, and thigh surfaces.  Only the duplicate
# V1 skin assignment is normalized; material slot ordering remains untouched.
for polygon in body.data.polygons:
    if polygon.material_index == 6:
        polygon.material_index = 1

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

bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()
bm_uv = bm.loops.layers.uv.active
source_index_layer = bm.verts.layers.int.new("V23_Bilateral_Source_Vertex_Index")
source_face_layer = bm.faces.layers.int.new("V23_Bilateral_Source_Face_Index")
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

source_vertex_map = {
    vertex[source_index_layer]: vertex
    for vertex in bm.verts
    if vertex[source_index_layer] >= 0
}
for source_index in sorted(patch_vertex_indices - set(source_vertex_map)):
    vertex = bm.verts.new(post_modifier_coordinates[source_index])
    vertex[source_index_layer] = source_index
    source_vertex_map[source_index] = vertex

restored_faces = []
restored_face_by_source = {}
for record in patch_records:
    if record["index"] in replacement_face_indices:
        continue
    vertices = [source_vertex_map[index] for index in record["vertices"]]
    face = bm.faces.new(vertices)
    face.material_index = 1 if record["material_index"] == 6 else record["material_index"]
    face.smooth = True
    face[source_face_layer] = record["index"]
    if bm_uv is not None:
        for loop in face.loops:
            uv = record["uv"].get(loop.vert[source_index_layer])
            if uv is not None:
                loop[bm_uv].uv = uv
    restored_faces.append(face)
    restored_face_by_source[record["index"]] = face

# Build a single explicit "pair-of-pants" bridge inside the exact compact
# 54-edge bilateral body opening.  The bridge has two authored child openings:
# an upper shaft root and a lower scrotal/perineal root.  Blender's polygon
# tessellator is used only to connect these declared loops; it is not a remesh
# and creates no inferred or donor surface.
outer_vertices = [
    source_vertex_map[index]
    for index in replacement_boundary_order
]
outer_count = len(outer_vertices)
shaft_count = 24
sac_count = 28
# The real boundary is non-planar and its direct X/Z projection folds across
# itself.  Parameterize it by measured 3D arc length onto an aligned ellipse:
# this preserves the actual non-uniform vertex spacing and anatomical phase
# without the self-intersection of the raw projection or the equal-index twist
# of the rejected unit-circle map.
outer_center = sum((vertex.co for vertex in outer_vertices), Vector()) / outer_count
segment_lengths = [
    (outer_vertices[(index + 1) % outer_count].co - outer_vertices[index].co).length
    for index in range(outer_count)
]
total_boundary_length = sum(segment_lengths)
if total_boundary_length <= 0.0:
    raise RuntimeError("bilateral replacement boundary has zero measured length")
start_angle = math.atan2(
    outer_vertices[0].co.z - outer_center.z,
    outer_vertices[0].co.x - outer_center.x,
)
cumulative_length = 0.0
outer_2d = []
for index in range(outer_count):
    theta = start_angle + 2.0 * math.pi * cumulative_length / total_boundary_length
    outer_2d.append(
        Vector(
            (
                0.060 * math.cos(theta),
                0.740 + 0.100 * math.sin(theta),
            )
        )
    )
    cumulative_length += segment_lengths[index]


def signed_area(points: list[Vector]) -> float:
    return 0.5 * sum(
        points[index].x * points[(index + 1) % len(points)].y
        - points[(index + 1) % len(points)].x * points[index].y
        for index in range(len(points))
    )


# Hole loops must wind opposite the measured, non-uniform V1 boundary.  The
# prior artificial unit-circle map discarded the real boundary parameterization
# and produced a diagonal/twisted bridge in 3D.
outer_area = signed_area(outer_2d)
if abs(outer_area) < 1e-8:
    raise RuntimeError("actual V1 replacement boundary has near-zero projected area")
hole_angle_sign = -1.0 if outer_area > 0.0 else 1.0
shaft_2d = [
    Vector(
        (
            0.0260 * math.cos(hole_angle_sign * 2.0 * math.pi * index / shaft_count),
            0.754
            + 0.0220
            * math.sin(hole_angle_sign * 2.0 * math.pi * index / shaft_count),
        )
    )
    for index in range(shaft_count)
]
sac_2d = [
    Vector(
        (
            0.0360 * math.cos(hole_angle_sign * 2.0 * math.pi * index / sac_count),
            0.684
            + 0.0290
            * math.sin(hole_angle_sign * 2.0 * math.pi * index / sac_count),
        )
    )
    for index in range(sac_count)
]

shaft_root_coordinates = [
    Vector(
        (
            0.0260 * math.cos(hole_angle_sign * 2.0 * math.pi * index / shaft_count),
            -0.118,
            0.754
            + 0.0220
            * math.sin(hole_angle_sign * 2.0 * math.pi * index / shaft_count),
        )
    )
    for index in range(shaft_count)
]
sac_root_coordinates = [
    Vector(
        (
            0.0360 * math.cos(hole_angle_sign * 2.0 * math.pi * index / sac_count),
            -0.112,
            0.684
            + 0.0290
            * math.sin(hole_angle_sign * 2.0 * math.pi * index / sac_count),
        )
    )
    for index in range(sac_count)
]
shaft_root_vertices = [bm.verts.new(coordinate) for coordinate in shaft_root_coordinates]
sac_root_vertices = [bm.verts.new(coordinate) for coordinate in sac_root_coordinates]

tessellation = tessellate_polygon([outer_2d, shaft_2d, sac_2d])
print(
    "ACTUAL_PROJECTION_DEBUG",
    {
        "outer_area": outer_area,
        "outer_bounds": {
            "x": (min(point.x for point in outer_2d), max(point.x for point in outer_2d)),
            "z": (min(point.y for point in outer_2d), max(point.y for point in outer_2d)),
        },
        "shaft_bounds": {
            "x": (min(point.x for point in shaft_2d), max(point.x for point in shaft_2d)),
            "z": (min(point.y for point in shaft_2d), max(point.y for point in shaft_2d)),
        },
        "sac_bounds": {
            "x": (min(point.x for point in sac_2d), max(point.x for point in sac_2d)),
            "z": (min(point.y for point in sac_2d), max(point.y for point in sac_2d)),
        },
        "triangles": len(tessellation),
        "outer_points": [
            (round(point.x, 6), round(point.y, 6)) for point in outer_2d
        ],
    },
)
bridge_vertices = outer_vertices + shaft_root_vertices + sac_root_vertices
new_vertices: list[bmesh.types.BMVert] = (
    list(shaft_root_vertices) + list(sac_root_vertices)
)
new_faces: list[bmesh.types.BMFace] = []
for triangle in tessellation:
    face = bm.faces.new(tuple(bridge_vertices[index] for index in triangle))
    face.material_index = skin_index
    face.smooth = True
    new_faces.append(face)


def build_tube(
    root_ring: list[bmesh.types.BMVert],
    centers: list[Vector],
    radii: list[tuple[float, float]],
    *,
    terminal: Vector,
    bilateral_sac: bool = False,
) -> None:
    count = len(root_ring)
    # Hole loops are authored clockwise. Maintain that parameterization through
    # every ring so the tessellated bridge and branch share an exact edge loop.
    theta_values = [
        hole_angle_sign * 2.0 * math.pi * index / count
        for index in range(count)
    ]
    rings = [root_ring]
    for section_index, (center, section_radii) in enumerate(zip(centers, radii)):
        coordinates = []
        for theta in theta_values:
            cosine = math.cos(theta)
            sine = math.sin(theta)
            x = section_radii[0] * cosine
            z = center.z + section_radii[1] * sine
            y = center.y
            if bilateral_sac:
                lateral = abs(cosine)
                lower = max(0.0, -sine)
                # Lateral lobes sit slightly forward while the continuous
                # medial raphe remains shallow. The left lobe hangs modestly
                # lower than the right.
                y -= 0.008 * lateral
                y += 0.0045 * (1.0 - lateral) * lower
                x *= 1.0 + 0.08 * lower * lateral
                # Raise the central inferior point slightly so the lower
                # contour reads as two continuous lobes with a shallow raphe,
                # not one featureless egg.
                z += 0.0075 * (1.0 - lateral) * lower
                if cosine < 0.0:
                    z -= 0.0040 * lower
                else:
                    z += 0.0018 * lower
            coordinates.append(Vector((x, y, z)))
        ring = [bm.verts.new(coordinate) for coordinate in coordinates]
        rings.append(ring)
        new_vertices.extend(ring)
    for first_ring, second_ring in zip(rings, rings[1:]):
        for index in range(count):
            following = (index + 1) % count
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
    tip = bm.verts.new(terminal)
    new_vertices.append(tip)
    for index in range(count):
        following = (index + 1) % count
        face = bm.faces.new((rings[-1][index], rings[-1][following], tip))
        face.material_index = skin_index
        face.smooth = True
        new_faces.append(face)


build_tube(
    shaft_root_vertices,
    [
        Vector((0.0, -0.145, 0.744)),
        Vector((0.0, -0.180, 0.729)),
        Vector((0.0, -0.205, 0.712)),
        Vector((0.0, -0.212, 0.699)),  # neck
        Vector((0.0, -0.214, 0.692)),  # coronal flare
        Vector((0.0, -0.214, 0.683)),  # glans body
        Vector((0.0, -0.212, 0.674)),
        Vector((0.0, -0.209, 0.668)),
    ],
    [
        (0.0240, 0.0225),
        (0.0210, 0.0200),
        (0.0185, 0.0183),
        (0.0165, 0.0163),
        (0.0218, 0.0190),
        (0.0208, 0.0170),
        (0.0145, 0.0115),
        (0.0100, 0.0075),
    ],
    terminal=Vector((0.0, -0.205, 0.661)),
)
build_tube(
    sac_root_vertices,
    [
        Vector((0.0, -0.136, 0.670)),
        Vector((0.0, -0.156, 0.658)),
        Vector((0.0, -0.172, 0.654)),
        Vector((0.0, -0.181, 0.655)),
    ],
    [
        (0.0370, 0.0350),
        (0.0410, 0.0500),
        (0.0340, 0.0410),
        (0.0200, 0.0240),
    ],
    terminal=Vector((0.0, -0.184, 0.655)),
    bilateral_sac=True,
)

sculpted_bilateral_vertices = len(new_vertices)
shared_center_vertices = sum(abs(vertex.co.x) < 0.0025 for vertex in new_vertices)
subdivision_created_geometry = 0
unused_replacement_vertices = [
    source_vertex_map[index]
    for index in replacement_internal_indices
    if source_vertex_map[index].is_valid and not source_vertex_map[index].link_faces
]
if unused_replacement_vertices:
    bmesh.ops.delete(bm, geom=unused_replacement_vertices, context="VERTS")

donor_uv = Vector((0.52, 0.38))
donor_found = False
if bm_uv is not None:
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
    for face in new_faces:
        for loop in face.loops:
            coordinate = loop.vert.co
            loop[bm_uv].uv = donor_uv + Vector(
                (coordinate.x * 0.065, (coordinate.z - 0.72) * 0.050)
            )

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
new_vertex_set = set(new_vertices)
new_edges = {edge for vertex in new_vertex_set for edge in vertex.link_edges}
new_patch_edge_incidence = {
    "edge_count": len(new_edges),
    "boundary_edges": sum(len(edge.link_faces) == 1 for edge in new_edges),
    "wire_edges": sum(len(edge.link_faces) == 0 for edge in new_edges),
    "nonmanifold_gt2_edges": sum(len(edge.link_faces) > 2 for edge in new_edges),
}
if any(
    new_patch_edge_incidence[key]
    for key in ("boundary_edges", "wire_edges", "nonmanifold_gt2_edges")
):
    raise RuntimeError(
        f"bilateral explicit surface failed edge-incidence gate: {new_patch_edge_incidence}"
    )

bm.to_mesh(body.data)
bm.free()
body.data.update()
pre_finishing_local_topology = local_edge_counts(body)
if (
    pre_finishing_local_topology["boundary_edges"]
    != baseline_local_topology["boundary_edges"]
    or pre_finishing_local_topology["nonmanifold_gt2_edges"]
    != baseline_local_topology["nonmanifold_gt2_edges"]
):
    raise RuntimeError(
        "bilateral repair changed inherited local topology before finishing: "
        f"baseline={baseline_local_topology} new={pre_finishing_local_topology}"
    )

applied_post_patch_modifiers = []
bpy.context.view_layer.objects.active = body
body.select_set(True)
for modifier in list(body.modifiers):
    applied_post_patch_modifiers.append((modifier.name, modifier.type))
    if modifier.type == "DISPLACE":
        bpy.ops.object.modifier_remove(modifier=modifier.name)
    else:
        bpy.ops.object.modifier_apply(modifier=modifier.name)
for polygon in body.data.polygons:
    polygon.use_smooth = True

# Append the accepted V15 layered review hairstyle as removable static-review
# hair.  The dedicated light/dark-blond material avoids the rejected brown or
# bald side silhouette.  This does not claim a runtime groom system.
with bpy.data.libraries.load(str(HAIR_SOURCE), link=False) as (data_from, data_to):
    data_to.objects = [
        name for name in ("Object_6", "Object_7") if name in data_from.objects
    ]
hair_material = bpy.data.materials.new(
    "Robert_V23_Bilateral_Removable_Dark_Blond_Static_Hair"
)
hair_material.use_nodes = True
hair_bsdf = next(
    node for node in hair_material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"
)
hair_bsdf.inputs["Base Color"].default_value = (0.19, 0.085, 0.022, 1.0)
hair_bsdf.inputs["Roughness"].default_value = 0.40
hair_bsdf.inputs["IOR"].default_value = 1.46
hair_objects = []
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
    hair_objects.append(hair.name)

body.name = BODY_OUTPUT_NAME
body["status"] = (
    "REJECTED VISUAL ENGINEERING EVIDENCE - NOT OWNER APPROVED"
)
body["source_v1_sha256"] = source_sha256
body["anatomy_method"] = (
    "212-FACE BOUNDED DELETE + 86-VERTEX OUTER RESTORE + "
    "38-FACE BILATERAL EXPLICIT PAIR-OF-PANTS BRIDGE + "
    "24-VERTEX SHAFT ROOT + 28-VERTEX SAC ROOT"
)
body["anatomy_estimation_label"] = "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE"
body["medical_reference_scope"] = "STRUCTURAL LANDMARK GUIDANCE ONLY"
body["boolean_used"] = False
body["remesh_used"] = False
body["donor_surface_transferred"] = False
body["runtime_activation_allowed"] = False
body["movement_started"] = False

final_local_topology = local_edge_counts(body)
final_component_sizes = mesh_component_sizes(body)
if (
    final_local_topology["boundary_edges"] != baseline_local_topology["boundary_edges"]
    or final_local_topology["nonmanifold_gt2_edges"]
    != baseline_local_topology["nonmanifold_gt2_edges"]
):
    raise RuntimeError(
        "bilateral repair changed inherited local topology after finishing: "
        f"baseline={baseline_local_topology} new={final_local_topology}"
    )

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
    "bilateral_seed_faces": len(bilateral_seed),
    "bilateral_connector_path_faces": connector_path,
    "bilateral_replacement_faces": len(replacement_face_indices),
    "bilateral_boundary_vertices_reused": len(replacement_boundary_order),
    "shaft_root_vertices": len(shaft_root_vertices),
    "sac_root_vertices": len(sac_root_vertices),
    "pair_of_pants_bridge_triangles": len(tessellation),
    "central_bridge_method": (
        "explicit tessellated polygon with two declared holes"
    ),
    "explicit_branch_vertices": sculpted_bilateral_vertices,
    "shared_center_vertices_in_scope": shared_center_vertices,
    "explicit_new_vertices_pre_subdivision": len(new_vertices),
    "explicit_new_faces_pre_subdivision": len(new_faces),
    "unused_replacement_vertices_removed": len(unused_replacement_vertices),
    "pre_patch_modifiers_applied": applied_pre_patch_modifiers,
    "post_patch_modifiers_applied": applied_post_patch_modifiers,
    "boolean_operations": 0,
    "remesh_operations": 0,
    "primitive_anatomy_objects": 0,
    "donor_surface_transferred": False,
    "unilateral_strip_used": False,
    "new_patch_edge_incidence_pre_subdivision": new_patch_edge_incidence,
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
    "v1_surface_preservation": {
        "skin_material": skin.name,
        "hands": "untouched V1 geometry",
        "nails": "untouched V1 geometry and material slots",
        "thighs": "untouched V1 geometry outside the bounded central seam",
        "global_scaling": False,
    },
    "hair": {
        "source": str(HAIR_SOURCE),
        "objects": hair_objects,
        "classification": "removable V15-derived static-review hair only",
        "color": "light/dark blond",
        "runtime_groom_complete": False,
    },
    "uv_donor_found": donor_found,
    "medical_landmarks_authored": [
        "bilateral pubic/root transition",
        "shared central bridge and medial raphe",
        "shaft body",
        "neck",
        "coronal flare",
        "glans body and distal tip",
        "one continuous bilobed scrotal envelope",
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
        "reason_codes": [
            "TWISTED_OR_DIAGONAL_PUBIC_BRIDGE_FOLD",
            "SHAFT_READS_AS_CURVED_PASTED_ON_TUBE",
            "SAC_READS_AS_OVERSIZED_ROUND_EGG_LIKE_ENVELOPE",
            "ROOT_ATTACHMENT_NOT_ANATOMICALLY_NATURAL",
            "SIDE_PROFILE_NOT_ANATOMICALLY_COHERENT",
        ],
        "inspected_full_resolution_views": [
            "close_pelvis_front.png",
            "close_pelvis_side.png",
            "close_pelvis_left_three_quarter.png",
            "close_pelvis_right_three_quarter.png",
            "close_upper_legs.png",
            "front.png",
        ],
        "topology_pass_does_not_override_visual_failure": True,
        "promotion_allowed": False,
    },
}
(OUT / "BILATERAL_EXPLICIT_BUILD_AND_TOPOLOGY_REPORT.json").write_text(
    json.dumps(report, indent=2) + "\n",
    encoding="utf-8",
)
print(BLEND_PATH)
print(json.dumps(report, indent=2))
