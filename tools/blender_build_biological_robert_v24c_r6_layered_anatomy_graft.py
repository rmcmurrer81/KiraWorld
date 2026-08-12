"""Attach a compact layered anatomy graft to the clean V24C bridge.

This static-only engineering trial uses V24C as its sole body foundation.  It
subdivides only the already-authored central pubic bridge, opens two small
front-surface roots, and extends those boundary cycles into hand-authored
shaft/glans and perineal/scrotal surfaces.  It does not use Boolean union,
metaballs, voxel remeshing, a donor identity surface, or hidden tunnel sheets.

R5 fixed the frame twist and removed the visible horizontal seams, but placed
the pouch root too far below the shaft, leaving a detached-looking gap.  R6
returns the pouch root beneath the shaft and layers its narrow superior rows
behind the shaft before expanding only below the distal shaft.  This preserves
separation without geometric overlap while restoring the normal connected
front silhouette.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


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
    "biological_static_likeness_v24c_r6_layered_anatomy_graft"
)
OUT.mkdir(parents=True, exist_ok=True)
BODY_NAME = (
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_"
    "R6_LAYERED_ANATOMY_GRAFT"
)
BLEND_PATH = OUT / f"{BODY_NAME}.blend"
REPORT_PATH = OUT / "V24C_R6_LAYERED_ANATOMY_GRAFT_REPORT.json"

PATCH_SUBDIVISION_CUTS = 5
ROOT_ANCHORS = {
    "shaft": {"target_x": 0.0, "target_z": 0.8072844},
    "scrotal": {"target_x": 0.0, "target_z": 0.7588530},
}

ZONE_NAMES = {
    1: "pubic_bridge",
    10: "shaft_root",
    11: "shaft_body",
    12: "shaft_neck",
    13: "glans",
    20: "perineal_scrotal_root",
    21: "scrotal_envelope",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def coordinate_key(vertex):
    return tuple(round(float(value), 7) for value in vertex.co)


def edge_key(edge):
    return tuple(sorted(coordinate_key(vertex) for vertex in edge.verts))


def topology_counts(bm):
    return {
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
                abs(vertex.co.x) <= 0.090
                and -0.190 <= vertex.co.y <= 0.080
                and 0.620 <= vertex.co.z <= 0.860
                for vertex in edge.verts
            )
            for edge in bm.edges
        ),
        "local_nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2
            and all(
                abs(vertex.co.x) <= 0.090
                and -0.190 <= vertex.co.y <= 0.080
                and 0.620 <= vertex.co.z <= 0.860
                for vertex in edge.verts
            )
            for edge in bm.edges
        ),
    }


def edge_components(edges):
    by_vertex = {}
    for edge in edges:
        for vertex in edge.verts:
            by_vertex.setdefault(vertex, []).append(edge)
    unseen = set(edges)
    result = []
    while unseen:
        seed = unseen.pop()
        current = [seed]
        stack = [seed]
        while stack:
            edge = stack.pop()
            for vertex in edge.verts:
                for neighbor in by_vertex[vertex]:
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        current.append(neighbor)
                        stack.append(neighbor)
        result.append(current)
    return result


def ordered_cycle(component):
    adjacency = {}
    for edge in component:
        first, second = edge.verts
        adjacency.setdefault(first, []).append(second)
        adjacency.setdefault(second, []).append(first)
    if not adjacency or set(len(values) for values in adjacency.values()) != {2}:
        raise RuntimeError("root boundary is not one simple degree-two cycle")
    start = max(
        adjacency,
        key=lambda vertex: (vertex.co.z, -abs(vertex.co.x), -vertex.co.y),
    )
    first = min(adjacency[start], key=lambda vertex: vertex.co.x)
    result = [start, first]
    previous = start
    current = first
    while True:
        following = next(
            vertex for vertex in adjacency[current] if vertex is not previous
        )
        if following is start:
            break
        if following in result:
            raise RuntimeError("root boundary repeats before closure")
        result.append(following)
        previous, current = current, following
    return result


def cycle_center(cycle):
    return sum((vertex.co for vertex in cycle), Vector()) / len(cycle)


def average_uv(cycle, uv_layer):
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


def root_angles(cycle):
    """Map the simple root boundary to a monotone elliptic parameter."""

    center = cycle_center(cycle)
    radius_x = max(abs(vertex.co.x - center.x) for vertex in cycle)
    radius_z = max(abs(vertex.co.z - center.z) for vertex in cycle)
    radius_x = max(radius_x, 1.0e-6)
    radius_z = max(radius_z, 1.0e-6)
    raw = [
        math.atan2(
            (vertex.co.z - center.z) / radius_z,
            (vertex.co.x - center.x) / radius_x,
        )
        for vertex in cycle
    ]
    unwrapped = [raw[0]]
    for value in raw[1:]:
        while value - unwrapped[-1] > math.pi:
            value -= math.tau
        while value - unwrapped[-1] < -math.pi:
            value += math.tau
        unwrapped.append(value)
    # A nonmonotone polar walk can fold a transition even when the boundary
    # itself is simple.  Fall back to perimeter angles while preserving the
    # superior starting phase.
    deltas = [
        unwrapped[index + 1] - unwrapped[index]
        for index in range(len(unwrapped) - 1)
    ]
    monotone = all(value >= -1.0e-5 for value in deltas) or all(
        value <= 1.0e-5 for value in deltas
    )
    if monotone:
        return unwrapped, "unwrapped_root_projection"
    lengths = [
        (cycle[(index + 1) % len(cycle)].co - cycle[index].co).length
        for index in range(len(cycle))
    ]
    total = sum(lengths)
    direction = -1.0 if sum(deltas) < 0.0 else 1.0
    values = [raw[0]]
    traversed = 0.0
    for index in range(1, len(cycle)):
        traversed += lengths[index - 1]
        values.append(raw[0] + direction * math.tau * traversed / total)
    return values, "perimeter_fallback"


def cross_axis(tangent):
    """Return the root-correspondent cross axis for a downward path.

    The old sign mapped a superior root vertex to the inferior side of the
    first ideal ring.  The quads therefore crossed even though both cycles
    were individually valid.  Keep positive ring sine on the superior side.
    """

    tangent = tangent.normalized()
    axis = Vector((0.0, tangent.z, -tangent.y))
    if axis.length <= 1.0e-9:
        return Vector((0.0, 0.0, 1.0))
    # Never flip this frame merely to keep one component positive.  Along an
    # outward-then-downward path, tangent cross +X rotates continuously from
    # superior (+Z) toward anterior (-Y).  A component sign change is normal;
    # negating the whole vector would twist the mesh by 180 degrees.
    return axis.normalized()


def create_face(
    bm,
    vertices,
    *,
    material_index,
    uv_layer,
    uv_value,
    new_faces,
):
    face = bm.faces.new(tuple(vertices))
    face.material_index = material_index
    face.smooth = True
    if uv_layer is not None:
        for loop in face.loops:
            loop[uv_layer].uv = uv_value
    new_faces.append(face)
    return face


def connect_rings(
    bm,
    first,
    second,
    *,
    material_index,
    uv_layer,
    uv_value,
    new_faces,
):
    if len(first) != len(second):
        raise RuntimeError("ring counts differ")
    for index in range(len(first)):
        following = (index + 1) % len(first)
        create_face(
            bm,
            (
                first[index],
                first[following],
                second[following],
                second[index],
            ),
            material_index=material_index,
            uv_layer=uv_layer,
            uv_value=uv_value,
            new_faces=new_faces,
        )


def densify_path(keyframes, steps_per_segment=2):
    result = []
    for index in range(len(keyframes) - 1):
        first_center, first_x, first_cross, first_zone = keyframes[index]
        second_center, second_x, second_cross, second_zone = keyframes[index + 1]
        for step in range(steps_per_segment):
            factor = step / steps_per_segment
            eased = factor * factor * (3.0 - 2.0 * factor)
            result.append(
                (
                    first_center.lerp(second_center, eased),
                    first_x + (second_x - first_x) * eased,
                    first_cross + (second_cross - first_cross) * eased,
                    first_zone if factor < 0.5 else second_zone,
                )
            )
    result.append(keyframes[-1])
    return result


def create_ring(
    bm,
    *,
    center,
    tangent,
    angles,
    radius_x,
    radius_cross,
    zone,
    zone_layer,
    authored_layer,
    mix_layer,
    scrotal,
    progress,
):
    axis = cross_axis(tangent)
    ring = []
    for angle in angles:
        cosine = math.cos(angle)
        sine = math.sin(angle)
        coordinate = (
            center
            + Vector((1.0, 0.0, 0.0)) * radius_x * cosine
            + axis * radius_cross * sine
        )
        if scrotal:
            # Recess/raise the midline slightly and lower the lateral envelopes
            # to read as one compact bilateral pouch, not a detached pair.
            normalized_x = coordinate.x / max(radius_x, 1.0e-6)
            medial = math.exp(-((normalized_x / 0.30) ** 2))
            bilateral = 1.0 - medial
            coordinate.y += 0.0028 * medial * progress
            coordinate.z += 0.0026 * medial * progress
            coordinate.z -= 0.0020 * bilateral * progress
            # Owner references support ordinary mild asymmetry, not mirrored
            # toy spheres.
            if coordinate.x > 0.0:
                coordinate.z -= 0.0011 * progress
        vertex = bm.verts.new(coordinate)
        vertex[zone_layer] = zone
        vertex[authored_layer] = 1
        vertex[mix_layer] = min(1.0, 0.18 + 0.82 * progress)
        ring.append(vertex)
    return ring


def build_branch(
    bm,
    *,
    root,
    keyframes,
    scrotal,
    zone_layer,
    authored_layer,
    mix_layer,
    uv_layer,
    material_index,
    new_faces,
):
    angles, angle_method = root_angles(root)
    root_center = cycle_center(root)
    uv_value = average_uv(root, uv_layer)
    path = densify_path(keyframes, steps_per_segment=2)
    first_center, first_x, first_cross, first_zone = path[0]
    first_tangent = path[1][0] - root_center
    first_ring = create_ring(
        bm,
        center=first_center,
        tangent=first_tangent,
        angles=angles,
        radius_x=first_x,
        radius_cross=first_cross,
        zone=first_zone,
        zone_layer=zone_layer,
        authored_layer=authored_layer,
        mix_layer=mix_layer,
        scrotal=scrotal,
        progress=0.05,
    )
    previous = root
    transition_rows = []
    # Preserve the exact cut outline before relaxing it into an ideal ring.
    # The first two rows are nearly parallel skin-normal offsets; this avoids
    # an abrupt collar and prevents a vertically elongated body opening from
    # collapsing into a rotated ellipse.  Later rows use smoothstep toward the
    # first authored cross-section while retaining one-to-one vertex order.
    transition_specs = (
        (0.08, -0.0010, 0.0000),
        (0.18, -0.0020, -0.0001),
        (0.40, -0.0027, -0.0002),
        (0.68, -0.0031, -0.0003),
        (0.88, -0.0032, -0.0003),
    )
    for factor, forward_offset, vertical_offset in transition_specs:
        eased = factor * factor * (3.0 - 2.0 * factor)
        transition = []
        for root_vertex, ideal_vertex in zip(root, first_ring):
            preserved = root_vertex.co + Vector(
                (0.0, forward_offset, vertical_offset)
            )
            vertex = bm.verts.new(preserved.lerp(ideal_vertex.co, eased))
            vertex[zone_layer] = 20 if scrotal else 10
            vertex[authored_layer] = 1
            vertex[mix_layer] = 0.18 + 0.08 * eased
            transition.append(vertex)
        connect_rings(
            bm,
            previous,
            transition,
            material_index=material_index,
            uv_layer=uv_layer,
            uv_value=uv_value,
            new_faces=new_faces,
        )
        previous = transition
        transition_rows.append(
            {
                "factor": factor,
                "forward_offset": forward_offset,
                "vertical_offset": vertical_offset,
                "coordinates": [list(vertex.co) for vertex in transition],
            }
        )
    connect_rings(
        bm,
        previous,
        first_ring,
        material_index=material_index,
        uv_layer=uv_layer,
        uv_value=uv_value,
        new_faces=new_faces,
    )
    previous = first_ring
    centers = [entry[0] for entry in path]
    path_report = []
    for index, (center, radius_x, radius_cross, zone) in enumerate(
        path[1:], start=1
    ):
        before = centers[index - 1]
        after = centers[index + 1] if index + 1 < len(centers) else center
        tangent = after - before
        if tangent.length <= 1.0e-9:
            tangent = Vector((0.0, -1.0, -0.2))
        ring = create_ring(
            bm,
            center=center,
            tangent=tangent,
            angles=angles,
            radius_x=radius_x,
            radius_cross=radius_cross,
            zone=zone,
            zone_layer=zone_layer,
            authored_layer=authored_layer,
            mix_layer=mix_layer,
            scrotal=scrotal,
            progress=(index + 1) / len(path),
        )
        connect_rings(
            bm,
            previous,
            ring,
            material_index=material_index,
            uv_layer=uv_layer,
            uv_value=uv_value,
            new_faces=new_faces,
        )
        previous = ring
        path_report.append(
            {
                "center": list(center),
                "radius_x": radius_x,
                "radius_cross": radius_cross,
                "zone": ZONE_NAMES[zone],
            }
        )
    tangent = centers[-1] - centers[-2]
    terminal = centers[-1] + tangent.normalized() * (
        0.0014 if scrotal else 0.0010
    )
    tip = bm.verts.new(terminal)
    tip[zone_layer] = 21 if scrotal else 13
    tip[authored_layer] = 1
    tip[mix_layer] = 1.0
    for index in range(len(previous)):
        following = (index + 1) % len(previous)
        create_face(
            bm,
            (previous[index], previous[following], tip),
            material_index=material_index,
            uv_layer=uv_layer,
            uv_value=uv_value,
            new_faces=new_faces,
        )
    return {
        "root_center": list(root_center),
        "root_vertices": len(root),
        "angle_method": angle_method,
        "root_coordinates": [list(vertex.co) for vertex in root],
        "root_angles_radians": angles,
        "transition_method": (
            "outline-preserving skin-normal offsets followed by bounded "
            "smoothstep relaxation with superior/inferior correspondence"
        ),
        "transition_rows": transition_rows,
        "path": path_report,
        "terminal": list(terminal),
    }


def mesh_bvh(faces):
    vertices = []
    vertex_map = {}
    polygons = []
    keys = []
    for face in faces:
        polygon = []
        face_keys = set()
        for vertex in face.verts:
            key = coordinate_key(vertex)
            if key not in vertex_map:
                vertex_map[key] = len(vertices)
                vertices.append(vertex.co.copy())
            polygon.append(vertex_map[key])
            face_keys.add(key)
        polygons.append(polygon)
        keys.append(face_keys)
    if not polygons:
        return None, keys
    return BVHTree.FromPolygons(
        vertices,
        polygons,
        all_triangles=False,
    ), keys


def intersection_report(patch_faces, retained_faces):
    patch_bvh, patch_keys = mesh_bvh(patch_faces)
    retained_bvh, retained_keys = mesh_bvh(retained_faces)
    self_pairs = set()
    for first, second in patch_bvh.overlap(patch_bvh):
        if first >= second or patch_keys[first] & patch_keys[second]:
            continue
        self_pairs.add((first, second))
    retained_pairs = set()
    for first, second in patch_bvh.overlap(retained_bvh):
        if patch_keys[first] & retained_keys[second]:
            continue
        retained_pairs.add((first, second))
    return {
        "nonadjacent_patch_self_intersections": len(self_pairs),
        "nonadjacent_patch_retained_intersections": len(retained_pairs),
        "first_patch_self_pairs": [
            list(pair) for pair in sorted(self_pairs)[:40]
        ],
        "first_patch_retained_pairs": [
            list(pair) for pair in sorted(retained_pairs)[:40]
        ],
    }


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects[
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_SUPERIOR_BRIDGE_REFINEMENT"
]
source_sha = sha256(SOURCE)
bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
uv_layer = bm.loops.layers.uv.active
zone_layer = bm.verts.layers.int.get("Adult_Anatomy_Zone")
if zone_layer is None:
    zone_layer = bm.verts.layers.int.new("Adult_Anatomy_Zone")
authored_layer = bm.verts.layers.int.get("V24C_R6_Layered_Graft")
if authored_layer is None:
    authored_layer = bm.verts.layers.int.new("V24C_R6_Layered_Graft")
mix_layer = bm.verts.layers.float.get("V24C_R6_Regional_Mix")
if mix_layer is None:
    mix_layer = bm.verts.layers.float.new("V24C_R6_Regional_Mix")

baseline = topology_counts(bm)
baseline_boundaries = {
    edge_key(edge) for edge in bm.edges if len(edge.link_faces) == 1
}
central_faces = [
    face
    for face in bm.faces
    if face.normal.y < -0.75
    and min(vertex.co.x for vertex in face.verts) < -0.030
    and max(vertex.co.x for vertex in face.verts) > 0.030
    and all(
        -0.135 < vertex.co.y < -0.060
        and 0.670 < vertex.co.z < 0.840
        for vertex in face.verts
    )
]
if len(central_faces) != 4:
    raise RuntimeError(
        "expected four clean V24C anterior bridge faces, found "
        f"{[(face.index, list(face.calc_center_median())) for face in central_faces]}"
    )
central_material = max(
    set(face.material_index for face in central_faces),
    key=[face.material_index for face in central_faces].count,
)
central_edges = list({edge for face in central_faces for edge in face.edges})
bmesh.ops.subdivide_edges(
    bm,
    edges=central_edges,
    cuts=PATCH_SUBDIVISION_CUTS,
    use_grid_fill=True,
)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
bm.normal_update()

anchor_vertices = {}
cut_faces = {}
for label, target in ROOT_ANCHORS.items():
    candidates = [
        vertex
        for vertex in bm.verts
        if abs(vertex.co.x) <= 0.050
        and -0.135 <= vertex.co.y <= -0.085
        and 0.720 <= vertex.co.z <= 0.825
    ]
    anchor = min(
        candidates,
        key=lambda vertex: (
            (vertex.co.x - target["target_x"]) ** 2
            + (vertex.co.z - target["target_z"]) ** 2
        ),
    )
    faces = [
        face
        for face in anchor.link_faces
        if face.normal.y < -0.65
        and all(
            abs(vertex.co.x) <= 0.050
            and -0.140 <= vertex.co.y <= -0.080
            and 0.720 <= vertex.co.z <= 0.830
            for vertex in face.verts
        )
    ]
    if len(faces) != 6:
        raise RuntimeError(
            f"{label} anchor did not have six clean bridge faces: "
            f"anchor={list(anchor.co)} faces={[face.index for face in faces]}"
        )
    anchor_vertices[label] = anchor.co.copy()
    cut_faces[label] = faces
all_cut_faces = list({face for values in cut_faces.values() for face in values})
if any(not values for values in cut_faces.values()):
    raise RuntimeError(
        f"explicit root window missed subdivided faces: "
        f"{ {key: len(value) for key, value in cut_faces.items()} }"
    )
bmesh.ops.delete(bm, geom=all_cut_faces, context="FACES")
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

initial_root_boundaries = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and edge_key(edge) not in baseline_boundaries
    and all(
        abs(vertex.co.x) <= 0.050
        and -0.150 <= vertex.co.y <= -0.070
        and 0.715 <= vertex.co.z <= 0.825
        for vertex in edge.verts
    )
]
# Split each convex six-edge opening once so the authored tube has twelve
# cross-section samples without changing anything beyond adjacent bridge faces.
initial_components = edge_components(initial_root_boundaries)
if len(initial_components) != 2 or any(
    len(component) != 6 for component in initial_components
):
    raise RuntimeError(
        "expected two convex six-edge root stars, found "
        f"{[len(component) for component in initial_components]}"
    )
bmesh.ops.subdivide_edges(
    bm,
    edges=list(
        {
            edge
            for component in initial_components
            for edge in component
        }
    ),
    cuts=1,
    use_grid_fill=False,
)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
bm.normal_update()

new_boundaries = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and edge_key(edge) not in baseline_boundaries
    and all(
        abs(vertex.co.x) <= 0.050
        and -0.150 <= vertex.co.y <= -0.070
        and 0.715 <= vertex.co.z <= 0.825
        for vertex in edge.verts
    )
]
components = edge_components(new_boundaries)
root_cycles = [
    ordered_cycle(component)
    for component in components
    if len(component) >= 4
]
root_cycles.sort(key=lambda cycle: cycle_center(cycle).z, reverse=True)
if len(root_cycles) != 2:
    raise RuntimeError(
        "expected two explicit root cycles, found "
        f"{[(len(cycle), list(cycle_center(cycle))) for cycle in root_cycles]}"
    )
shaft_root, scrotal_root = root_cycles
shaft_center = cycle_center(shaft_root)
scrotal_center = cycle_center(scrotal_root)

new_faces = []
shaft_keyframes = [
    (
        Vector((0.0, -0.1280, shaft_center.z - 0.002)),
        0.0115,
        0.0102,
        10,
    ),
    (Vector((0.0, -0.1290, shaft_center.z - 0.010)), 0.0122, 0.0108, 11),
    (Vector((0.0, -0.1300, shaft_center.z - 0.020)), 0.0125, 0.0110, 11),
    (Vector((0.0, -0.1310, shaft_center.z - 0.030)), 0.0122, 0.0107, 11),
    (Vector((0.0, -0.1315, shaft_center.z - 0.038)), 0.0106, 0.0093, 12),
    (Vector((0.0, -0.1320, shaft_center.z - 0.043)), 0.0135, 0.0113, 13),
    (Vector((0.0, -0.1320, shaft_center.z - 0.047)), 0.0131, 0.0108, 13),
    (Vector((0.0, -0.1315, shaft_center.z - 0.052)), 0.0090, 0.0068, 13),
    (Vector((0.0, -0.1310, shaft_center.z - 0.055)), 0.0036, 0.0026, 13),
]
scrotal_keyframes = [
    (
        Vector((0.0, -0.1145, scrotal_center.z - 0.001)),
        0.0090,
        0.0070,
        20,
    ),
    (Vector((0.0, -0.1140, scrotal_center.z - 0.007)), 0.0100, 0.0075, 21),
    (Vector((0.0, -0.1160, scrotal_center.z - 0.014)), 0.0130, 0.0090, 21),
    (Vector((0.0, -0.1210, scrotal_center.z - 0.022)), 0.0180, 0.0125, 21),
    (Vector((0.0, -0.1250, scrotal_center.z - 0.031)), 0.0220, 0.0155, 21),
    (Vector((0.0, -0.1270, scrotal_center.z - 0.041)), 0.0240, 0.0170, 21),
    (Vector((0.0, -0.1270, scrotal_center.z - 0.051)), 0.0230, 0.0160, 21),
    (Vector((0.0, -0.1260, scrotal_center.z - 0.060)), 0.0190, 0.0130, 21),
    (Vector((0.0, -0.1240, scrotal_center.z - 0.067)), 0.0130, 0.0085, 21),
    (Vector((0.0, -0.1230, scrotal_center.z - 0.071)), 0.0060, 0.0040, 21),
]
shaft_report = build_branch(
    bm,
    root=shaft_root,
    keyframes=shaft_keyframes,
    scrotal=False,
    zone_layer=zone_layer,
    authored_layer=authored_layer,
    mix_layer=mix_layer,
    uv_layer=uv_layer,
    material_index=central_material,
    new_faces=new_faces,
)
scrotal_report = build_branch(
    bm,
    root=scrotal_root,
    keyframes=scrotal_keyframes,
    scrotal=True,
    zone_layer=zone_layer,
    authored_layer=authored_layer,
    mix_layer=mix_layer,
    uv_layer=uv_layer,
    material_index=central_material,
    new_faces=new_faces,
)

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.normal_update()
final = topology_counts(bm)
patch_set = set(new_faces)
retained_local_faces = [
    face
    for face in bm.faces
    if face not in patch_set
    and max(abs(vertex.co.x) for vertex in face.verts) <= 0.095
    and max(vertex.co.y for vertex in face.verts) >= -0.190
    and min(vertex.co.y for vertex in face.verts) <= 0.050
    and max(vertex.co.z for vertex in face.verts) >= 0.630
    and min(vertex.co.z for vertex in face.verts) <= 0.850
]
intersections = intersection_report(new_faces, retained_local_faces)
topology_gate = (
    final["boundary_edges"] == baseline["boundary_edges"]
    and final["wire_edges"] == baseline["wire_edges"]
    and final["nonmanifold_gt2_edges"]
    == baseline["nonmanifold_gt2_edges"]
    and final["local_boundary_edges"] == baseline["local_boundary_edges"]
)
intersection_gate = (
    intersections["nonadjacent_patch_self_intersections"] == 0
    and intersections["nonadjacent_patch_retained_intersections"] == 0
)
zone_counts = {
    name: sum(vertex[zone_layer] == code for vertex in bm.verts)
    for code, name in ZONE_NAMES.items()
}

bm.to_mesh(body.data)
bm.free()
body.data.update()
mesh_validate_changed = body.data.validate(clean_customdata=False)
for polygon in body.data.polygons:
    polygon.use_smooth = True
body.name = BODY_NAME
body["status"] = "ENGINEERING TRIAL - VISUAL REVIEW REQUIRED"
body["source_authority"] = "V24C CLEAN CONTINUOUS PUBIC BRIDGE"
body["method"] = (
    "LAYERED SHAFT/POUCH ROOTS + CONTINUOUS-FRAME COMPACT GRAFTS"
)
body["boolean_used"] = False
body["metaball_used"] = False
body["voxel_remesh_used"] = False
body["donor_identity_surface_used"] = False
body["owner_approved"] = False
body["movement_started"] = False
body["runtime_activation_allowed"] = False
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

report = {
    "schema": "kira.avatar.biological_robert.v24c.r6.layered_graft.v1",
    "status": body["status"],
    "source": str(SOURCE),
    "source_sha256": source_sha,
    "output": str(BLEND_PATH),
    "output_sha256": sha256(BLEND_PATH),
    "reference_handling": {
        "private_owner_reference_directory": r"C:\Users\robmc\Desktop\reference",
        "used_for": [
            "high root placement",
            "short neutral projection",
            "compact relationship to upper thighs",
        ],
        "better_authorized_anatomy_guidance_used_for": [
            "shaft/glans form",
            "bilateral pouch structure",
            "perineal transition",
        ],
        "private_local_only": True,
        "delete_only_after_explicit_owner_approval": True,
    },
    "method_truth": {
        "v24c_clean_bridge_used": True,
        "boolean": False,
        "metaballs": False,
        "voxel_remesh": False,
        "donor_identity_surface": False,
        "global_body_change": False,
        "r1_rejected_reason": (
            "opposite superior/inferior ring correspondence folded transition "
            "panels into leaf shapes and dark gutters"
        ),
        "r2_rejected_reason": (
            "face-center ellipse selection made concave notched root cycles; "
            "outline preservation could not remove the inherited notch"
        ),
        "r3_rejected_reason": (
            "convex roots passed topology but early shaft rows and the whole "
            "scrotal path remained partly behind the retained anterior skin"
        ),
        "r4_rejected_reason": (
            "cross-axis sign forcing twisted rings 180 degrees when a path's "
            "small Y slope changed sign, creating seams and diamond faces"
        ),
        "r5_rejected_reason": (
            "continuous frame removed seams, but low pouch root left a "
            "detached-looking vertical gap below the shaft"
        ),
    },
    "central_bridge": {
        "source_face_count": len(central_faces),
        "subdivision_cuts": PATCH_SUBDIVISION_CUTS,
        "root_anchors": ROOT_ANCHORS,
        "actual_anchor_coordinates": {
            label: list(coordinate)
            for label, coordinate in anchor_vertices.items()
        },
        "initial_root_edges": [
            len(component) for component in initial_components
        ],
        "subdivided_root_edges": [len(cycle) for cycle in root_cycles],
        "cut_face_counts": {
            label: len(faces) for label, faces in cut_faces.items()
        },
    },
    "roots": {
        "shaft_center": list(shaft_center),
        "shaft_vertices": len(shaft_root),
        "scrotal_center": list(scrotal_center),
        "scrotal_vertices": len(scrotal_root),
    },
    "branches": {
        "shaft": shaft_report,
        "scrotal": scrotal_report,
    },
    "zone_vertex_counts": zone_counts,
    "baseline_topology": baseline,
    "final_topology": final,
    "topology_gate": topology_gate,
    "intersection_report": intersections,
    "intersection_gate": intersection_gate,
    "mesh_validate_changed_data": bool(mesh_validate_changed),
    "truthful_gate": {
        "static_owner_review_candidate": False,
        "visual_promotion": (
            "BLOCKED UNTIL NEUTRAL FRONT/SIDE/THREE-QUARTER FLAT, "
            "WIRE, NORMAL, AND SILHOUETTE REVIEW PASSES"
        ),
        "reject_if": [
            "superior hole or lateral gutter remains",
            "root reads as a collar or pasted surface",
            "shaft is too long/thick or bows too far forward",
            "glans is spherical or oversized",
            "pouch is one toy sphere instead of a compact bilateral form",
            "material spills onto the thigh",
        ],
    },
    "reusability_boundary": {
        "candidate_reusable_methods_only_after_owner_approval": [
            "small visible root windows on a clean local bridge",
            "ordered boundary-cycle extraction",
            "outline-preserving skin-normal transition rows",
            "superior/inferior ring correspondence validation",
            "encoded neutral-view and mesh-intersection gates",
        ],
        "robert_private_person_specific_data": [
            "root positions and local proportions inferred from protected photos",
            "Robert likeness body mesh and materials",
            "Robert-specific hair, face, eye, and body parameters",
        ],
        "avatar_builder_promotion": (
            "BLOCKED until Biological Robert static owner approval and "
            "independent proof that the method generalizes"
        ),
        "person_specific_script_disposition": (
            "archive as Robert-private build evidence after approval; "
            "never use Robert as a generic avatar template"
        ),
    },
    "scope": {
        "private_static_engineering_only": True,
        "movement": False,
        "activation": False,
        "runtime_attachment": False,
        "synthetic_robert": False,
        "kira": False,
        "clothing": False,
    },
}
REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(BLEND_PATH)
print(json.dumps(report, indent=2))
