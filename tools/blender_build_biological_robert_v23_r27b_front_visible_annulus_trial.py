"""Bridge the R24 superior tunnel using its two real visible-cut boundaries.

Unlike the rejected broad R27A reconstruction, this trial removes only owner
faces that are the first front-ray hit in a small superior-root window.  The
cut exposes two cycles: a retained lower-abdomen boundary and a continuous
inner/root boundary.  They are joined as one triangulated annulus.  Neither
cycle is independently capped, so this does not create the stacked sheets seen
in prior Coons/cap trials.

All real boundary vertices remain pinned.  Interior coordinates are solved by
harmonic relaxation over an abstract annulus, avoiding any radial fan or
camera-plane projection of the self-overlapping inner cycle.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_preserved_surface_trial_r24_raised_branches/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_"
    "PRESERVED_SURFACE_TRIAL_R24_RAISED_BRANCHES.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_r27b_front_visible_annulus_trial"
)
OUT.mkdir(parents=True, exist_ok=True)
BLEND_PATH = (
    OUT
    / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_"
    "R27B_FRONT_VISIBLE_ANNULUS_TRIAL.blend"
)
REPORT_PATH = OUT / "R27B_FRONT_VISIBLE_ANNULUS_BUILD_REPORT.json"
WINDOW = {"half_x": 0.025, "min_z": 0.780, "max_z": 0.832}
INNER_DOMAIN_RADIUS = 0.34
GRID_STEP = 0.040
RELAXATION = 0.72
ITERATIONS = 1800


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
    }


def components(edges):
    by_vertex = {}
    for edge in edges:
        for vertex in edge.verts:
            by_vertex.setdefault(vertex, []).append(edge)
    unseen = set(edges)
    result = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        current = [seed]
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
        a, b = edge.verts
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
    if set(len(values) for values in adjacency.values()) != {2}:
        raise RuntimeError("cut boundary is not a simple mesh cycle")
    start = min(adjacency, key=coordinate_key)
    ordered = [start]
    previous = None
    current = start
    while True:
        candidates = [vertex for vertex in adjacency[current] if vertex is not previous]
        following = (
            min(candidates, key=coordinate_key) if previous is None else candidates[0]
        )
        if following is start:
            break
        if following in ordered:
            raise RuntimeError("boundary cycle repeated a vertex")
        ordered.append(following)
        previous, current = current, following
    return ordered


def rotate_to_leftmost(ordered):
    start = min(
        range(len(ordered)),
        key=lambda index: (
            ordered[index].co.x,
            -ordered[index].co.z,
            ordered[index].co.y,
        ),
    )
    return ordered[start:] + ordered[:start]


def map_cycle(ordered, radius):
    ordered = rotate_to_leftmost(ordered)
    lengths = [
        (ordered[(index + 1) % len(ordered)].co - ordered[index].co).length
        for index in range(len(ordered))
    ]
    total = sum(lengths)
    factors = [0.0]
    running = 0.0
    for length in lengths[:-1]:
        running += length
        factors.append(running / total)
    # Begin at the leftmost point.  Choose direction so the next real vertex's
    # Z motion agrees with the circle's first motion.
    direction = 1.0
    for candidate in ordered[1:]:
        delta = candidate.co.z - ordered[0].co.z
        if abs(delta) > 1e-7:
            direction = 1.0 if delta < 0.0 else -1.0
            break
    points = []
    for factor in factors:
        theta = math.pi + direction * math.tau * factor
        points.append(Vector((radius * math.cos(theta), radius * math.sin(theta))))
    return ordered, points


def point_in_polygon(point, polygon):
    inside = False
    previous = polygon[-1]
    for current in polygon:
        if (current.y > point.y) != (previous.y > point.y):
            crossing = (
                (previous.x - current.x)
                * (point.y - current.y)
                / (previous.y - current.y)
                + current.x
            )
            if point.x < crossing:
                inside = not inside
        previous = current
    return inside


def initial_coordinate(point, fixed_indices, domain_points, fixed_coordinates):
    nearest = sorted(
        fixed_indices,
        key=lambda index: (domain_points[index] - point).length_squared,
    )[:20]
    total = Vector((0.0, 0.0, 0.0))
    weight_total = 0.0
    for index in nearest:
        distance_squared = max(
            (domain_points[index] - point).length_squared,
            1e-10,
        )
        weight = 1.0 / distance_squared
        total += fixed_coordinates[index] * weight
        weight_total += weight
    return total / weight_total


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
    return BVHTree.FromPolygons(vertices, polygons, all_triangles=False), keys


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
        "first_patch_self_pairs": [list(pair) for pair in sorted(self_pairs)[:30]],
        "first_patch_retained_pairs": [
            list(pair) for pair in sorted(retained_pairs)[:30]
        ],
    }


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = max(
    (obj for obj in bpy.context.scene.objects if obj.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)
body.name = (
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_"
    "R27B_FRONT_VISIBLE_ANNULUS_TRIAL"
)
skin_index = next(
    (
        index
        for index, material in enumerate(body.data.materials)
        if material and material.name == "MBLab_skin3"
    ),
    1,
)
bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
for index, face in enumerate(bm.faces):
    face.index = index
uv_layer = bm.loops.layers.uv.active
surface_class = bm.verts.layers.int.get("V23_Surface_Class")
anatomy_zone = bm.verts.layers.int.get("Adult_Anatomy_Zone")
transition_class = bm.verts.layers.int.get("R27_Transition_Class")
if transition_class is None:
    transition_class = bm.verts.layers.int.new("R27_Transition_Class")
baseline = topology_counts(bm)
baseline_boundaries = {
    edge_key(edge) for edge in bm.edges if len(edge.link_faces) == 1
}
bvh = BVHTree.FromBMesh(bm)
cut_faces = []
for face in bm.faces:
    center = face.calc_center_median()
    if not (
        abs(center.x) <= WINDOW["half_x"]
        and WINDOW["min_z"] <= center.z <= WINDOW["max_z"]
        and -0.23 <= center.y <= 0.04
    ):
        continue
    if surface_class is not None and any(
        int(vertex[surface_class]) in {1, 2} for vertex in face.verts
    ):
        continue
    hit, _normal, hit_index, _distance = bvh.ray_cast(
        Vector((center.x, -0.35, center.z)),
        Vector((0.0, 1.0, 0.0)),
        0.70,
    )
    if hit is not None and hit_index == face.index:
        cut_faces.append(face)
if len(cut_faces) != 764:
    raise RuntimeError(f"front-visible S1 cut changed: {len(cut_faces)}")
bmesh.ops.delete(bm, geom=cut_faces, context="FACES")
new_boundary_edges = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1 and edge_key(edge) not in baseline_boundaries
]
cycle_components = components(new_boundary_edges)
if sorted(len(component) for component in cycle_components) != [22, 284]:
    raise RuntimeError(
        "front-visible cycle signature changed: "
        f"{sorted(len(component) for component in cycle_components)}"
    )
outer_order, outer_domain = map_cycle(
    ordered_cycle(min(cycle_components, key=len)),
    1.0,
)
inner_order, inner_domain = map_cycle(
    ordered_cycle(max(cycle_components, key=len)),
    INNER_DOMAIN_RADIUS,
)

input_points = list(outer_domain) + list(inner_domain)
input_existing = list(outer_order) + list(inner_order)
outer_range = (0, len(outer_domain))
inner_range = (outer_range[1], len(input_points))
coordinate = -1.0 + GRID_STEP
while coordinate < 1.0 - GRID_STEP:
    other = -1.0 + GRID_STEP
    while other < 1.0 - GRID_STEP:
        point = Vector((coordinate, other))
        if point.length < 0.985 and point.length > INNER_DOMAIN_RADIUS + 0.018:
            input_points.append(point)
            input_existing.append(None)
        other += GRID_STEP
    coordinate += GRID_STEP
constraints = []
for start, end in (outer_range, inner_range):
    for index in range(start, end):
        constraints.append((index, start + ((index - start + 1) % (end - start))))

(
    output_points,
    _output_edges,
    output_faces,
    output_origins,
    _origin_edges,
    _origin_faces,
) = delaunay_2d_cdt(input_points, constraints, [], 0, 1e-9, True)
kept_faces = []
for face in output_faces:
    if len(face) != 3:
        raise RuntimeError("CDT unexpectedly returned a non-triangle")
    center = sum(
        (output_points[index] for index in face),
        Vector((0.0, 0.0)),
    ) / 3.0
    if point_in_polygon(center, outer_domain) and not point_in_polygon(
        center, inner_domain
    ):
        kept_faces.append(tuple(face))

input_to_output = {}
output_existing = {}
for output_index, origins in enumerate(output_origins):
    for input_index in origins:
        input_to_output[input_index] = output_index
        existing = input_existing[input_index]
        if existing is not None:
            prior = output_existing.get(output_index)
            if prior is not None and prior is not existing:
                raise RuntimeError("CDT merged real boundary vertices")
            output_existing[output_index] = existing
used_indices = {index for face in kept_faces for index in face}
used_edges = {
    tuple(sorted((face[index], face[(index + 1) % 3])))
    for face in kept_faces
    for index in range(3)
}
missing_constraints = [
    edge
    for edge in constraints
    if tuple(sorted((input_to_output[edge[0]], input_to_output[edge[1]])))
    not in used_edges
]
if missing_constraints:
    raise RuntimeError(f"annulus lost {len(missing_constraints)} real boundary edges")
adjacency = {index: set() for index in used_indices}
for face in kept_faces:
    for index in range(3):
        a = face[index]
        b = face[(index + 1) % 3]
        adjacency[a].add(b)
        adjacency[b].add(a)
fixed_coordinates = {
    index: vertex.co.copy() for index, vertex in output_existing.items()
}
fixed_indices = sorted(fixed_coordinates)
coordinates = {}
for index in used_indices:
    coordinates[index] = (
        fixed_coordinates[index].copy()
        if index in fixed_coordinates
        else initial_coordinate(
            output_points[index],
            fixed_indices,
            output_points,
            fixed_coordinates,
        )
    )
last_delta = None
iterations_used = 0
for iteration in range(ITERATIONS):
    last_delta = 0.0
    for index in sorted(used_indices):
        if index in fixed_coordinates:
            continue
        average = sum(
            (coordinates[neighbor] for neighbor in adjacency[index]),
            Vector((0.0, 0.0, 0.0)),
        ) / len(adjacency[index])
        updated = (
            coordinates[index] * (1.0 - RELAXATION)
            + average * RELAXATION
        )
        last_delta = max(last_delta, (updated - coordinates[index]).length)
        coordinates[index] = updated
    iterations_used = iteration + 1
    if last_delta < 2e-9:
        break

output_vertices = dict(output_existing)
created_vertices = []
for index in sorted(used_indices):
    if index in output_vertices:
        continue
    vertex = bm.verts.new(coordinates[index])
    vertex[transition_class] = 2
    if surface_class is not None:
        vertex[surface_class] = 0
    if anatomy_zone is not None:
        vertex[anatomy_zone] = 31
    output_vertices[index] = vertex
    created_vertices.append(vertex)
patch_faces = []
for triangle in kept_faces:
    face = bm.faces.new(tuple(output_vertices[index] for index in triangle))
    face.material_index = skin_index
    face.smooth = True
    patch_faces.append(face)
    if uv_layer is not None:
        for loop in face.loops:
            loop[uv_layer].uv = Vector((0.52, 0.38))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.normal_update()
final = topology_counts(bm)
patch_set = set(patch_faces)
local_retained = []
for face in bm.faces:
    if face in patch_set:
        continue
    vertices = [vertex.co for vertex in face.verts]
    if (
        max(abs(vertex.x) for vertex in vertices) <= 0.065
        and max(vertex.y for vertex in vertices) >= -0.23
        and min(vertex.y for vertex in vertices) <= 0.04
        and max(vertex.z for vertex in vertices) >= 0.755
        and min(vertex.z for vertex in vertices) <= 0.850
    ):
        local_retained.append(face)
intersections = intersection_report(patch_faces, local_retained)
face_areas = [face.calc_area() for face in patch_faces]
edge_lengths = [
    (edge.verts[1].co - edge.verts[0].co).length
    for edge in {edge for face in patch_faces for edge in face.edges}
]
topology_gate = (
    final["boundary_edges"] == baseline["boundary_edges"]
    and final["wire_edges"] == baseline["wire_edges"]
    and final["nonmanifold_gt2_edges"]
    == baseline["nonmanifold_gt2_edges"]
)
intersection_gate = (
    intersections["nonadjacent_patch_self_intersections"] == 0
    and intersections["nonadjacent_patch_retained_intersections"] == 0
)
bm.to_mesh(body.data)
bm.free()
body.data.update()
mesh_validation_changed = body.data.validate(clean_customdata=False)
for polygon in body.data.polygons:
    polygon.use_smooth = True
body["status"] = "REJECTED ENGINEERING TRIAL - VISUAL REVIEW REQUIRED"
body["method"] = (
    "FRONT-RAY VISIBLE S1 CUT + ONE ABSTRACT CDT ANNULUS + "
    "PINNED-BOUNDARY HARMONIC XYZ"
)
body["boolean_used"] = False
body["global_remesh_used"] = False
body["radial_fan_used"] = False
body["runtime_activation_allowed"] = False
body["movement_started"] = False
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
report = {
    "schema": "kira.avatar.v23.r27b.front_visible_annulus_trial.v1",
    "status": body["status"],
    "source": str(SOURCE),
    "output": str(BLEND_PATH),
    "window": WINDOW,
    "cut_faces": len(cut_faces),
    "boundary_cycles": {
        "outer_lower_abdomen": len(outer_order),
        "inner_root_transition": len(inner_order),
    },
    "method": body["method"],
    "input_domain_vertices": len(input_points),
    "output_domain_vertices": len(output_points),
    "created_interior_vertices": len(created_vertices),
    "patch_triangles": len(patch_faces),
    "iterations_used": iterations_used,
    "last_harmonic_delta_meters": last_delta,
    "minimum_patch_area_m2": min(face_areas),
    "maximum_patch_edge_meters": max(edge_lengths),
    "local_retained_faces_audited": len(local_retained),
    "intersection_report": intersections,
    "baseline_topology": baseline,
    "final_topology": final,
    "topology_gate": topology_gate,
    "intersection_gate": intersection_gate,
    "mesh_validate_changed_data": bool(mesh_validation_changed),
    "visual_promotion": (
        "BLOCKED UNTIL ENCODED FRONT/SIDE/THREE-QUARTER "
        "FLAT, WIRE, NORMAL, AND SILHOUETTE REVIEW PASSES"
    ),
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
