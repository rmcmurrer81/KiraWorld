"""Build a clean V24 visible-skin adult-anatomy attachment trial.

This static-only engineering trial deliberately abandons the contaminated
V14--V23 exact-union lineage.  It starts from the clean, owner-preferred
V1-derived V24 body, removes only first-hit anterior skin faces inside a small
high pubic window, and reconstructs the missing center with:

* a symmetric pubic saddle welded directly to the two clean skin boundaries;
* separate, high shaft and scrotal root openings in that authored saddle;
* one continuous shaft branch with a restrained neck/corona/glans sequence;
* one continuous scrotal/perineal branch with modest bilateral shaping; and
* no Boolean union, voxel remesh, donor identity surface, or hidden tunnel
  sheet.

The result remains rejected engineering evidence until encoded front, side,
and three-quarter diagnostics demonstrate a continuous natural attachment.
It does not authorize movement, runtime attachment, activation, Synthetic
Robert, Kira, clothing, or Kira World work.
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
    "biological_static_likeness_v24_clean_v1_rebase/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24_CLEAN_V1_REBASE.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v24_r1_visible_skin_anatomy_trial"
)
OUT.mkdir(parents=True, exist_ok=True)
BODY_NAME = (
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24_"
    "R1_VISIBLE_SKIN_ANATOMY_TRIAL"
)
BLEND_PATH = OUT / f"{BODY_NAME}.blend"
REPORT_PATH = OUT / "V24_R1_VISIBLE_SKIN_ANATOMY_TRIAL_REPORT.json"

WINDOWS = (
    {"center_z": 0.806, "radius_x": 0.035, "radius_z": 0.028},
    {"center_z": 0.758, "radius_x": 0.034, "radius_z": 0.030},
)
BRIDGE_U_STEPS = 14
BOUNDARY_SUBDIVISIONS = 2

ZONE_NAMES = {
    1: "pubic_transition",
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


def coordinate_key(vertex: bmesh.types.BMVert):
    return tuple(round(float(value), 7) for value in vertex.co)


def edge_key(edge: bmesh.types.BMEdge):
    return tuple(sorted(coordinate_key(vertex) for vertex in edge.verts))


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
    if set(len(neighbors) for neighbors in adjacency.values()) != {2}:
        raise RuntimeError("boundary component is not a simple cycle")
    start = min(adjacency, key=coordinate_key)
    first = min(adjacency[start], key=coordinate_key)
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
            raise RuntimeError("boundary cycle repeats before closure")
        result.append(following)
        previous, current = current, following
    return result


def cycle_center(cycle):
    return sum((vertex.co for vertex in cycle), Vector()) / len(cycle)


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
        "local_pelvis_boundary_edges": sum(
            len(edge.link_faces) == 1
            and all(
                abs(vertex.co.x) <= 0.090
                and -0.220 <= vertex.co.y <= 0.080
                and 0.620 <= vertex.co.z <= 0.860
                for vertex in edge.verts
            )
            for edge in bm.edges
        ),
        "local_pelvis_nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2
            and all(
                abs(vertex.co.x) <= 0.090
                and -0.220 <= vertex.co.y <= 0.080
                and 0.620 <= vertex.co.z <= 0.860
                for vertex in edge.verts
            )
            for edge in bm.edges
        ),
    }


def in_window(point, window):
    return (
        (point.x / window["radius_x"]) ** 2
        + ((point.z - window["center_z"]) / window["radius_z"]) ** 2
        <= 1.0
    )


def align_mirrored(left, right):
    """Align right-cycle vertices to the mirrored left-cycle coordinates."""

    if len(left) != len(right):
        raise RuntimeError("left and right boundary counts differ")
    best = None
    for reverse in (False, True):
        sequence = list(reversed(right)) if reverse else list(right)
        for offset in range(len(sequence)):
            candidate = sequence[offset:] + sequence[:offset]
            error = 0.0
            for first, second in zip(left, candidate):
                target = Vector((-first.co.x, first.co.y, first.co.z))
                error += (target - second.co).length_squared
            if best is None or error < best[0]:
                best = (error, candidate, reverse, offset)
    return best


def average_cycle_uv(cycle, uv_layer):
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


def create_face(bm, vertices, material_index, new_faces, uv_layer, uv_value):
    face = bm.faces.new(tuple(vertices))
    face.material_index = material_index
    face.smooth = True
    new_faces.append(face)
    if uv_layer is not None:
        for loop in face.loops:
            loop[uv_layer].uv = uv_value
    return face


def root_angles(cycle):
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
    values = [raw[0]]
    for value in raw[1:]:
        while value - values[-1] > math.pi:
            value -= math.tau
        while value - values[-1] < -math.pi:
            value += math.tau
        values.append(value)
    return values


def cross_axis(tangent):
    tangent = tangent.normalized()
    axis = Vector((0.0, -tangent.z, tangent.y))
    if axis.length <= 1.0e-9:
        return Vector((0.0, 1.0, 0.0))
    return axis.normalized()


def create_ideal_ring(
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
    material_mix_layer,
    uv_center,
    scrotal,
    progress,
):
    axis = cross_axis(tangent)
    result = []
    for angle in angles:
        cosine = math.cos(angle)
        sine = math.sin(angle)
        coordinate = (
            center
            + Vector((1.0, 0.0, 0.0)) * radius_x * cosine
            + axis * radius_cross * sine
        )
        if scrotal:
            normalized_x = coordinate.x / max(radius_x, 1.0e-6)
            medial = math.exp(-((normalized_x / 0.28) ** 2))
            bilateral = 1.0 - medial
            coordinate.z += 0.0022 * medial * progress
            coordinate.z -= 0.0030 * bilateral * progress
            coordinate.y += 0.0008 * medial * progress
        vertex = bm.verts.new(coordinate)
        vertex[zone_layer] = zone
        vertex[authored_layer] = 1
        vertex[material_mix_layer] = min(1.0, 0.18 + progress * 0.82)
        result.append(vertex)
    return result


def connect_rings(
    bm,
    first,
    second,
    *,
    material_index,
    new_faces,
    uv_layer,
    uv_center,
):
    if len(first) != len(second):
        raise RuntimeError("ring vertex counts differ")
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
            material_index,
            new_faces,
            uv_layer,
            uv_center,
        )


def densify_path(keyframes, steps_per_segment=2):
    dense = []
    for index in range(len(keyframes) - 1):
        first_center, first_x, first_cross, first_zone = keyframes[index]
        second_center, second_x, second_cross, second_zone = keyframes[index + 1]
        for step in range(steps_per_segment):
            factor = step / steps_per_segment
            eased = factor * factor * (3.0 - 2.0 * factor)
            dense.append(
                (
                    first_center.lerp(second_center, eased),
                    first_x + (second_x - first_x) * eased,
                    first_cross + (second_cross - first_cross) * eased,
                    first_zone if factor < 0.5 else second_zone,
                )
            )
    dense.append(keyframes[-1])
    return dense


def build_branch(
    bm,
    *,
    root,
    keyframes,
    scrotal,
    zone_layer,
    authored_layer,
    material_mix_layer,
    material_index,
    uv_layer,
    new_faces,
):
    center = cycle_center(root)
    uv_center = average_cycle_uv(root, uv_layer)
    angles = root_angles(root)
    for vertex in root:
        vertex[zone_layer] = 20 if scrotal else 10
    path = densify_path(keyframes, steps_per_segment=2)
    first_center, first_radius_x, first_radius_cross, first_zone = path[0]
    first_tangent = path[1][0] - center
    first_ring = create_ideal_ring(
        bm,
        center=first_center,
        tangent=first_tangent,
        angles=angles,
        radius_x=first_radius_x,
        radius_cross=first_radius_cross,
        zone=first_zone,
        zone_layer=zone_layer,
        authored_layer=authored_layer,
        material_mix_layer=material_mix_layer,
        uv_center=uv_center,
        scrotal=scrotal,
        progress=0.05,
    )
    previous = root
    # Two eased transition rows preserve the clean visible-skin root instead
    # of collapsing the irregular owner-body boundary into a radial fan.
    for factor in (0.34, 0.68):
        eased = factor * factor * (3.0 - 2.0 * factor)
        transition = []
        for root_vertex, ideal_vertex in zip(root, first_ring):
            vertex = bm.verts.new(root_vertex.co.lerp(ideal_vertex.co, eased))
            vertex[zone_layer] = 20 if scrotal else 10
            vertex[authored_layer] = 1
            vertex[material_mix_layer] = 0.18 + 0.08 * eased
            transition.append(vertex)
        connect_rings(
            bm,
            previous,
            transition,
            material_index=material_index,
            new_faces=new_faces,
            uv_layer=uv_layer,
            uv_center=uv_center,
        )
        previous = transition
    connect_rings(
        bm,
        previous,
        first_ring,
        material_index=material_index,
        new_faces=new_faces,
        uv_layer=uv_layer,
        uv_center=uv_center,
    )
    previous = first_ring
    ring_reports = []
    centers = [entry[0] for entry in path]
    for index, (path_center, radius_x, radius_cross, zone) in enumerate(
        path[1:], start=1
    ):
        previous_center = centers[index - 1]
        following_center = (
            centers[index + 1] if index + 1 < len(centers) else path_center
        )
        tangent = following_center - previous_center
        if tangent.length <= 1.0e-9:
            tangent = Vector((0.0, -1.0, -0.2))
        ring = create_ideal_ring(
            bm,
            center=path_center,
            tangent=tangent,
            angles=angles,
            radius_x=radius_x,
            radius_cross=radius_cross,
            zone=zone,
            zone_layer=zone_layer,
            authored_layer=authored_layer,
            material_mix_layer=material_mix_layer,
            uv_center=uv_center,
            scrotal=scrotal,
            progress=(index + 1) / len(path),
        )
        connect_rings(
            bm,
            previous,
            ring,
            material_index=material_index,
            new_faces=new_faces,
            uv_layer=uv_layer,
            uv_center=uv_center,
        )
        previous = ring
        ring_reports.append(
            {
                "center": list(path_center),
                "radius_x": radius_x,
                "radius_cross": radius_cross,
                "zone": ZONE_NAMES[zone],
            }
        )
    terminal_tangent = centers[-1] - centers[-2]
    terminal = centers[-1] + terminal_tangent.normalized() * (
        0.0018 if scrotal else 0.0012
    )
    tip = bm.verts.new(terminal)
    tip[zone_layer] = 21 if scrotal else 13
    tip[authored_layer] = 1
    tip[material_mix_layer] = 1.0
    for index in range(len(previous)):
        following = (index + 1) % len(previous)
        create_face(
            bm,
            (previous[index], previous[following], tip),
            material_index,
            new_faces,
            uv_layer,
            uv_center,
        )
    return {
        "root_center": list(center),
        "root_vertices": len(root),
        "path": ring_reports,
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
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24_CLEAN_V1_REBASE"
]
source_sha = sha256(SOURCE)
skin_index = next(
    (
        index
        for index, material in enumerate(body.data.materials)
        if material and material.name == "MBLab_skin3"
    ),
    0,
)

bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
for index, face in enumerate(bm.faces):
    face.index = index
uv_layer = bm.loops.layers.uv.active
zone_layer = bm.verts.layers.int.get("Adult_Anatomy_Zone")
if zone_layer is None:
    zone_layer = bm.verts.layers.int.new("Adult_Anatomy_Zone")
authored_layer = bm.verts.layers.int.get("V24_R1_Authored_Local_Surface")
if authored_layer is None:
    authored_layer = bm.verts.layers.int.new(
        "V24_R1_Authored_Local_Surface"
    )
material_mix_layer = bm.verts.layers.float.get("V24_R1_Regional_Mix")
if material_mix_layer is None:
    material_mix_layer = bm.verts.layers.float.new("V24_R1_Regional_Mix")

baseline = topology_counts(bm)
baseline_boundary_keys = {
    edge_key(edge) for edge in bm.edges if len(edge.link_faces) == 1
}
bvh = BVHTree.FromBMesh(bm)
cut_faces = []
for face in bm.faces:
    center = face.calc_center_median()
    if not any(in_window(center, window) for window in WINDOWS):
        continue
    hit, _normal, hit_index, _distance = bvh.ray_cast(
        Vector((center.x, -0.35, center.z)),
        Vector((0.0, 1.0, 0.0)),
        0.70,
    )
    if hit is not None and hit_index == face.index:
        cut_faces.append(face)
bmesh.ops.delete(bm, geom=cut_faces, context="FACES")

new_boundary = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and edge_key(edge) not in baseline_boundary_keys
]
if len(edge_components(new_boundary)) != 2:
    raise RuntimeError("visible V24 cut did not expose two clean boundaries")
bmesh.ops.subdivide_edges(
    bm,
    edges=new_boundary,
    cuts=BOUNDARY_SUBDIVISIONS,
    use_grid_fill=False,
)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

local_cut_boundary = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and all(
        abs(vertex.co.x) < 0.060
        and -0.130 < vertex.co.y < -0.010
        and 0.720 < vertex.co.z < 0.850
        for vertex in edge.verts
    )
]
components = edge_components(local_cut_boundary)
if len(components) != 2:
    raise RuntimeError(
        "subdivided V24 visible cut did not retain two cycles: "
        f"{[len(component) for component in components]}"
    )
cycles = [ordered_cycle(component) for component in components]
cycles.sort(key=lambda cycle: cycle_center(cycle).x)
left, right = cycles
alignment_error, right_aligned, alignment_reversed, alignment_offset = (
    align_mirrored(left, right)
)
if alignment_error > 5.0e-4:
    raise RuntimeError(
        f"V24 bilateral cut is not sufficiently mirrored: {alignment_error}"
    )

bridge_faces = []
all_new_faces = []
uv_center = (
    average_cycle_uv(left, uv_layer)
    + average_cycle_uv(right_aligned, uv_layer)
) * 0.5
rows = [left]
for u_index in range(1, BRIDGE_U_STEPS):
    factor = u_index / BRIDGE_U_STEPS
    center_weight = math.sin(math.pi * factor) ** 2
    row = []
    for left_vertex, right_vertex in zip(left, right_aligned):
        coordinate = left_vertex.co.lerp(right_vertex.co, factor)
        front_weight = max(
            0.0,
            min(1.0, (-coordinate.y - 0.050) / 0.060),
        )
        coordinate.y -= 0.0060 * center_weight * front_weight
        vertex = bm.verts.new(coordinate)
        vertex[zone_layer] = 1
        vertex[authored_layer] = 1
        vertex[material_mix_layer] = 0.12
        row.append(vertex)
    rows.append(row)
rows.append(right_aligned)

skipped = {"shaft": 0, "scrotal": 0}
for u_index in range(BRIDGE_U_STEPS):
    for v_index in range(len(left)):
        following = (v_index + 1) % len(left)
        vertices = (
            rows[u_index][v_index],
            rows[u_index][following],
            rows[u_index + 1][following],
            rows[u_index + 1][v_index],
        )
        center = sum((vertex.co for vertex in vertices), Vector()) / 4.0
        front_visible = center.y < -0.086
        shaft_hole = (
            front_visible
            and abs(center.x) < 0.0135
            and 0.790 < center.z < 0.817
        )
        scrotal_hole = (
            front_visible
            and abs(center.x) < 0.0235
            and 0.751 < center.z < 0.779
        )
        if shaft_hole or scrotal_hole:
            skipped["shaft" if shaft_hole else "scrotal"] += 1
            continue
        face = create_face(
            bm,
            vertices,
            skin_index,
            all_new_faces,
            uv_layer,
            uv_center,
        )
        bridge_faces.append(face)

root_boundary_edges = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and all(
        abs(vertex.co.x) < 0.035
        and vertex.co.y < -0.080
        and 0.740 < vertex.co.z < 0.825
        for vertex in edge.verts
    )
]
root_components = edge_components(root_boundary_edges)
root_cycles = [
    ordered_cycle(component)
    for component in root_components
    if len(component) >= 6
]
root_cycles.sort(key=lambda cycle: cycle_center(cycle).z, reverse=True)
if len(root_cycles) != 2:
    raise RuntimeError(
        "expected separate shaft/scrotal root cycles, found "
        f"{[(len(cycle), list(cycle_center(cycle))) for cycle in root_cycles]}"
    )
shaft_root, scrotal_root = root_cycles
shaft_center = cycle_center(shaft_root)
scrotal_center = cycle_center(scrotal_root)

shaft_keyframes = [
    (
        Vector((0.0, shaft_center.y - 0.004, shaft_center.z - 0.001)),
        0.0134,
        0.0124,
        10,
    ),
    (Vector((0.0, -0.124, shaft_center.z - 0.013)), 0.0144, 0.0134, 11),
    (Vector((0.0, -0.134, shaft_center.z - 0.030)), 0.0147, 0.0131, 11),
    (Vector((0.0, -0.140, shaft_center.z - 0.048)), 0.0144, 0.0127, 11),
    (Vector((0.0, -0.143, shaft_center.z - 0.061)), 0.0124, 0.0108, 12),
    (Vector((0.0, -0.144, shaft_center.z - 0.067)), 0.0170, 0.0141, 13),
    (Vector((0.0, -0.145, shaft_center.z - 0.075)), 0.0164, 0.0135, 13),
    (Vector((0.0, -0.144, shaft_center.z - 0.082)), 0.0102, 0.0078, 13),
    (Vector((0.0, -0.143, shaft_center.z - 0.086)), 0.0048, 0.0036, 13),
]
scrotal_keyframes = [
    (
        Vector(
            (
                0.0,
                scrotal_center.y + 0.002,
                scrotal_center.z - 0.001,
            )
        ),
        0.0215,
        0.0180,
        20,
    ),
    (Vector((0.0, -0.086, scrotal_center.z - 0.014)), 0.0270, 0.0240, 21),
    (Vector((0.0, -0.083, scrotal_center.z - 0.031)), 0.0315, 0.0280, 21),
    (Vector((0.0, -0.081, scrotal_center.z - 0.047)), 0.0310, 0.0260, 21),
    (Vector((0.0, -0.079, scrotal_center.z - 0.060)), 0.0260, 0.0205, 21),
    (Vector((0.0, -0.078, scrotal_center.z - 0.069)), 0.0175, 0.0130, 21),
    (Vector((0.0, -0.077, scrotal_center.z - 0.074)), 0.0070, 0.0050, 21),
]
shaft_report = build_branch(
    bm,
    root=shaft_root,
    keyframes=shaft_keyframes,
    scrotal=False,
    zone_layer=zone_layer,
    authored_layer=authored_layer,
    material_mix_layer=material_mix_layer,
    material_index=skin_index,
    uv_layer=uv_layer,
    new_faces=all_new_faces,
)
scrotal_report = build_branch(
    bm,
    root=scrotal_root,
    keyframes=scrotal_keyframes,
    scrotal=True,
    zone_layer=zone_layer,
    authored_layer=authored_layer,
    material_mix_layer=material_mix_layer,
    material_index=skin_index,
    uv_layer=uv_layer,
    new_faces=all_new_faces,
)

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.normal_update()
final = topology_counts(bm)
patch_set = set(all_new_faces)
local_retained_faces = [
    face
    for face in bm.faces
    if face not in patch_set
    and max(abs(vertex.co.x) for vertex in face.verts) <= 0.095
    and max(vertex.co.y for vertex in face.verts) >= -0.230
    and min(vertex.co.y for vertex in face.verts) <= 0.050
    and max(vertex.co.z for vertex in face.verts) >= 0.620
    and min(vertex.co.z for vertex in face.verts) <= 0.860
]
intersections = intersection_report(all_new_faces, local_retained_faces)

zone_counts = {
    name: sum(vertex[zone_layer] == code for vertex in bm.verts)
    for code, name in ZONE_NAMES.items()
}
face_areas = [face.calc_area() for face in all_new_faces]
topology_gate = (
    final["boundary_edges"] == baseline["boundary_edges"]
    and final["wire_edges"] == baseline["wire_edges"]
    and final["nonmanifold_gt2_edges"]
    == baseline["nonmanifold_gt2_edges"]
    and final["local_pelvis_boundary_edges"]
    == baseline["local_pelvis_boundary_edges"]
)
intersection_gate = (
    intersections["nonadjacent_patch_self_intersections"] == 0
    and intersections["nonadjacent_patch_retained_intersections"] == 0
)

bm.to_mesh(body.data)
bm.free()
body.data.update()
mesh_validate_changed = body.data.validate(clean_customdata=False)
for polygon in body.data.polygons:
    polygon.use_smooth = True

body.name = BODY_NAME
body["status"] = "REJECTED ENGINEERING TRIAL - VISUAL REVIEW REQUIRED"
body["source_authority"] = "CLEAN V1-DERIVED V24 SUBSTRATE"
body["method"] = (
    "FIRST-HIT VISIBLE-SKIN CUT + BILATERAL PUBIC SADDLE + "
    "TWO CONTINUOUS ANATOMY BRANCHES"
)
body["contaminated_v14_v23_union_lineage_reused"] = False
body["boolean_used"] = False
body["global_remesh_used"] = False
body["donor_identity_surface_transferred"] = False
body["hidden_tunnel_sheets_used"] = False
body["movement_started"] = False
body["runtime_activation_allowed"] = False
body["owner_approved"] = False
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

report = {
    "schema": "kira.avatar.biological_robert.v24.r1.visible_skin_trial.v1",
    "status": body["status"],
    "source": str(SOURCE),
    "source_sha256": source_sha,
    "output": str(BLEND_PATH),
    "output_sha256": sha256(BLEND_PATH),
    "method": body["method"],
    "visible_cut": {
        "windows": list(WINDOWS),
        "cut_faces": len(cut_faces),
        "boundary_subdivisions": BOUNDARY_SUBDIVISIONS,
        "left_cycle_vertices": len(left),
        "right_cycle_vertices": len(right_aligned),
        "mirror_alignment_squared_error": alignment_error,
        "right_cycle_reversed": alignment_reversed,
        "right_cycle_offset": alignment_offset,
    },
    "pubic_saddle": {
        "u_steps": BRIDGE_U_STEPS,
        "faces": len(bridge_faces),
        "skipped_root_faces": skipped,
        "front_visible_only": True,
        "hidden_tunnel_sheets_used": False,
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
    "minimum_authored_face_area_m2": min(face_areas),
    "mesh_validate_changed_data": bool(mesh_validate_changed),
    "truthful_gate": {
        "static_owner_review_candidate": False,
        "visual_promotion": (
            "BLOCKED UNTIL ENCODED FRONT/SIDE/THREE-QUARTER FLAT, "
            "WIRE, NORMAL, AND SILHOUETTE REVIEW PASSES"
        ),
        "automatic_rejection_if_hole_or_pasted_root_visible": True,
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
