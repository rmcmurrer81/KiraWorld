"""Build an independent broad R24 pubic-to-root reconstruction trial.

R24's measured superior gap is not a simple planar hole.  A broad owner-surface
cut exposes:

* one outer retained owner-surface cycle;
* the true shaft attachment cycle;
* the true scrotal attachment cycle; and
* one hidden legacy inner-fold cycle.

The outer cycle self-overlaps in X/Z, X/Y, and Y/Z projection, so projecting it
to a camera plane and filling it necessarily creates a panel, shelf, or folded
surface.  This trial instead builds an abstract pair-of-pants parameter domain:
an outer disk with separate shaft and scrotal holes.  A constrained Delaunay
triangulation supplies non-radial topology.  All real boundary coordinates are
pinned and the interior X/Y/Z coordinates are solved by bounded harmonic
relaxation.  The hidden legacy inner-fold cycle is capped separately.

This is private static engineering evidence.  It is never an approval
candidate without encoded flat/wire/normal/silhouette review, a zero effective
gap measurement, and clean local intersection evidence.
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
    "biological_static_likeness_v23_r27a_broad_cdt_transition_trial"
)
OUT.mkdir(parents=True, exist_ok=True)
BLEND_PATH = (
    OUT
    / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_"
    "R27A_BROAD_CDT_TRANSITION_TRIAL.blend"
)
REPORT_PATH = OUT / "R27A_BROAD_CDT_TRANSITION_BUILD_REPORT.json"

WINDOW = {
    "half_x": 0.050,
    "min_y": -0.175,
    "max_y": -0.018,
    "min_z": 0.695,
    "max_z": 0.830,
}
DOMAIN = {
    "outer_radius": 1.0,
    "shaft_center": [0.0, 0.50],
    "shaft_radii": [0.22, 0.19],
    "scrotal_center": [0.0, -0.27],
    "scrotal_radii": [0.31, 0.37],
    "interior_grid_step": 0.045,
}
HARMONIC_ITERATIONS = 1600
HARMONIC_RELAXATION = 0.74


def coordinate_key(vertex: bmesh.types.BMVert):
    return tuple(round(float(value), 7) for value in vertex.co)


def edge_key(edge: bmesh.types.BMEdge):
    return tuple(sorted(coordinate_key(vertex) for vertex in edge.verts))


def topology_counts(bm: bmesh.types.BMesh):
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


def components(edges: list[bmesh.types.BMEdge]):
    by_vertex: dict[bmesh.types.BMVert, list[bmesh.types.BMEdge]] = {}
    for edge in edges:
        for vertex in edge.verts:
            by_vertex.setdefault(vertex, []).append(edge)
    unseen = set(edges)
    result = []
    while unseen:
        seed = unseen.pop()
        component = [seed]
        stack = [seed]
        while stack:
            current = stack.pop()
            for vertex in current.verts:
                for neighbor in by_vertex.get(vertex, []):
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        component.append(neighbor)
                        stack.append(neighbor)
        result.append(component)
    return result


def ordered_cycle_vertices(cycle: list[bmesh.types.BMEdge]):
    adjacency: dict[bmesh.types.BMVert, list[bmesh.types.BMVert]] = {}
    for edge in cycle:
        a, b = edge.verts
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
    if any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise RuntimeError("candidate cut component is not a simple mesh cycle")
    start = min(adjacency, key=lambda vertex: coordinate_key(vertex))
    ordered = [start]
    previous = None
    current = start
    while True:
        candidates = [
            vertex for vertex in adjacency[current] if vertex is not previous
        ]
        if previous is None:
            next_vertex = min(candidates, key=lambda vertex: coordinate_key(vertex))
        else:
            next_vertex = candidates[0]
        if next_vertex is start:
            break
        if next_vertex in ordered:
            raise RuntimeError("cycle traversal repeated a vertex")
        ordered.append(next_vertex)
        previous, current = current, next_vertex
    if len(ordered) != len(adjacency):
        raise RuntimeError("cycle traversal omitted vertices")
    return ordered


def rotate_cycle_to_bottom_center(ordered):
    index = min(
        range(len(ordered)),
        key=lambda candidate: (
            ordered[candidate].co.z,
            abs(ordered[candidate].co.x),
            ordered[candidate].co.y,
        ),
    )
    result = ordered[index:] + ordered[:index]
    # Increasing circle angle from the bottom travels toward +X.  Reverse the
    # cycle when its first meaningful motion travels toward -X.
    direction = None
    for candidate in result[1:]:
        delta = candidate.co.x - result[0].co.x
        if abs(delta) > 1e-7:
            direction = delta
            break
    if direction is not None and direction < 0.0:
        result = [result[0]] + list(reversed(result[1:]))
    return result


def arclength_factors(ordered):
    lengths = [
        (ordered[(index + 1) % len(ordered)].co - ordered[index].co).length
        for index in range(len(ordered))
    ]
    total = sum(lengths)
    if total <= 1e-12:
        raise RuntimeError("zero-length boundary cycle")
    factors = [0.0]
    running = 0.0
    for length in lengths[:-1]:
        running += length
        factors.append(running / total)
    return factors


def map_cycle_to_ellipse(ordered, center, radii):
    ordered = rotate_cycle_to_bottom_center(ordered)
    factors = arclength_factors(ordered)
    points = []
    for factor in factors:
        theta = -math.pi * 0.5 + math.tau * factor
        points.append(
            Vector(
                (
                    center[0] + radii[0] * math.cos(theta),
                    center[1] + radii[1] * math.sin(theta),
                )
            )
        )
    return ordered, points


def point_in_polygon(point: Vector, polygon: list[Vector]):
    inside = False
    previous = polygon[-1]
    for current in polygon:
        if (current.y > point.y) != (previous.y > point.y):
            denominator = previous.y - current.y
            if abs(denominator) < 1e-15:
                previous = current
                continue
            crossing = (
                (previous.x - current.x)
                * (point.y - current.y)
                / denominator
                + current.x
            )
            if point.x < crossing:
                inside = not inside
        previous = current
    return inside


def domain_clear(point, outer, holes):
    return point_in_polygon(point, outer) and not any(
        point_in_polygon(point, hole) for hole in holes
    )


def nearest_boundary_average(point, boundary_indices, points, coordinates):
    nearest = sorted(
        boundary_indices,
        key=lambda index: (points[index] - point).length_squared,
    )[:24]
    total = Vector((0.0, 0.0, 0.0))
    weight_total = 0.0
    for index in nearest:
        distance_squared = max(
            (points[index] - point).length_squared,
            1e-10,
        )
        weight = 1.0 / distance_squared
        total += coordinates[index] * weight
        weight_total += weight
    return total / weight_total


def mesh_bvh(faces):
    vertices = []
    vertex_indices = {}
    polygons = []
    face_vertex_keys = []
    for face in faces:
        polygon = []
        keys = set()
        for vertex in face.verts:
            key = id(vertex)
            if key not in vertex_indices:
                vertex_indices[key] = len(vertices)
                vertices.append(vertex.co.copy())
            polygon.append(vertex_indices[key])
            keys.add(coordinate_key(vertex))
        polygons.append(polygon)
        face_vertex_keys.append(keys)
    if not polygons:
        return None, face_vertex_keys
    return BVHTree.FromPolygons(vertices, polygons, all_triangles=False), face_vertex_keys


def intersection_report(patch_faces, retained_faces):
    patch_bvh, patch_keys = mesh_bvh(patch_faces)
    retained_bvh, retained_keys = mesh_bvh(retained_faces)
    patch_self = set()
    if patch_bvh is not None:
        for first, second in patch_bvh.overlap(patch_bvh):
            if first >= second:
                continue
            if patch_keys[first] & patch_keys[second]:
                continue
            patch_self.add((first, second))
    patch_retained = set()
    if patch_bvh is not None and retained_bvh is not None:
        for patch_index, retained_index in patch_bvh.overlap(retained_bvh):
            if patch_keys[patch_index] & retained_keys[retained_index]:
                continue
            patch_retained.add((patch_index, retained_index))
    return {
        "nonadjacent_patch_self_intersections": len(patch_self),
        "nonadjacent_patch_retained_intersections": len(patch_retained),
        "first_patch_self_pairs": [list(pair) for pair in sorted(patch_self)[:30]],
        "first_patch_retained_pairs": [
            list(pair) for pair in sorted(patch_retained)[:30]
        ],
    }


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = max(
    (obj for obj in bpy.context.scene.objects if obj.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)
body.name = (
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_"
    "R27A_BROAD_CDT_TRANSITION_TRIAL"
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
uv_layer = bm.loops.layers.uv.active
surface_class = bm.verts.layers.int.get("V23_Surface_Class")
anatomy_zone = bm.verts.layers.int.get("Adult_Anatomy_Zone")
transition_class = bm.verts.layers.int.get("R27_Transition_Class")
if transition_class is None:
    transition_class = bm.verts.layers.int.new("R27_Transition_Class")

baseline = topology_counts(bm)
baseline_boundary_keys = {
    edge_key(edge) for edge in bm.edges if len(edge.link_faces) == 1
}
cut_faces = []
authored_faces_excluded = 0
for face in bm.faces:
    center = face.calc_center_median()
    if not (
        abs(center.x) <= WINDOW["half_x"]
        and WINDOW["min_y"] <= center.y <= WINDOW["max_y"]
        and WINDOW["min_z"] <= center.z <= WINDOW["max_z"]
    ):
        continue
    if surface_class is not None and any(
        int(vertex[surface_class]) in {1, 2} for vertex in face.verts
    ):
        authored_faces_excluded += 1
        continue
    cut_faces.append(face)
if len(cut_faces) != 6850:
    raise RuntimeError(f"measured W5 owner-face cut changed: {len(cut_faces)}")
bmesh.ops.delete(bm, geom=cut_faces, context="FACES")
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

new_boundary_edges = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1 and edge_key(edge) not in baseline_boundary_keys
]
cycle_components = components(new_boundary_edges)
if sorted(len(component) for component in cycle_components) != [48, 128, 280, 372]:
    raise RuntimeError(
        "W5 boundary cycle signature changed: "
        f"{sorted(len(component) for component in cycle_components)}"
    )
cycles_by_count = {len(component): component for component in cycle_components}
hidden_cycle = cycles_by_count[48]
shaft_cycle = cycles_by_count[128]
scrotal_cycle = cycles_by_count[280]
outer_cycle = cycles_by_count[372]

outer_order, outer_domain = map_cycle_to_ellipse(
    ordered_cycle_vertices(outer_cycle),
    (0.0, 0.0),
    (DOMAIN["outer_radius"], DOMAIN["outer_radius"]),
)
shaft_order, shaft_domain = map_cycle_to_ellipse(
    ordered_cycle_vertices(shaft_cycle),
    DOMAIN["shaft_center"],
    DOMAIN["shaft_radii"],
)
scrotal_order, scrotal_domain = map_cycle_to_ellipse(
    ordered_cycle_vertices(scrotal_cycle),
    DOMAIN["scrotal_center"],
    DOMAIN["scrotal_radii"],
)

input_points: list[Vector] = []
input_existing: list[bmesh.types.BMVert | None] = []
boundary_ranges = {}
for label, ordered, mapped in (
    ("outer", outer_order, outer_domain),
    ("shaft", shaft_order, shaft_domain),
    ("scrotal", scrotal_order, scrotal_domain),
):
    start = len(input_points)
    input_points.extend(mapped)
    input_existing.extend(ordered)
    boundary_ranges[label] = [start, len(input_points)]

outer_polygon = list(outer_domain)
hole_polygons = [list(shaft_domain), list(scrotal_domain)]
step = DOMAIN["interior_grid_step"]
coordinate = -DOMAIN["outer_radius"] + step
while coordinate < DOMAIN["outer_radius"] - step:
    other = -DOMAIN["outer_radius"] + step
    while other < DOMAIN["outer_radius"] - step:
        point = Vector((coordinate, other))
        if domain_clear(point, outer_polygon, hole_polygons):
            input_points.append(point)
            input_existing.append(None)
        other += step
    coordinate += step

constraint_edges = []
for start, end in boundary_ranges.values():
    for index in range(start, end):
        constraint_edges.append((index, start + ((index - start + 1) % (end - start))))

(
    output_points,
    _output_edges,
    output_faces,
    output_origin_vertices,
    _output_origin_edges,
    _output_origin_faces,
) = delaunay_2d_cdt(
    input_points,
    constraint_edges,
    [],
    0,
    1e-9,
    True,
)

kept_triangles = []
for face in output_faces:
    if len(face) != 3:
        raise RuntimeError(f"CDT output was not triangular: {face}")
    center = sum((output_points[index] for index in face), Vector((0.0, 0.0))) / 3.0
    if domain_clear(center, outer_polygon, hole_polygons):
        kept_triangles.append(tuple(face))

output_existing: dict[int, bmesh.types.BMVert] = {}
input_to_output = {}
for output_index, origins in enumerate(output_origin_vertices):
    for input_index in origins:
        input_to_output[input_index] = output_index
        existing = input_existing[input_index]
        if existing is not None:
            previous = output_existing.get(output_index)
            if previous is not None and previous is not existing:
                raise RuntimeError("CDT merged distinct real boundary vertices")
            output_existing[output_index] = existing

used_output_indices = {
    index for triangle in kept_triangles for index in triangle
}
boundary_input_indices = {
    index
    for start, end in boundary_ranges.values()
    for index in range(start, end)
}
if not boundary_input_indices.issubset(input_to_output):
    raise RuntimeError("CDT omitted one or more real boundary vertices")
fixed_output_indices = {
    input_to_output[index] for index in boundary_input_indices
}
used_edges = {
    tuple(sorted((triangle[index], triangle[(index + 1) % 3])))
    for triangle in kept_triangles
    for index in range(3)
}
missing_constraints = []
for first, second in constraint_edges:
    output_edge = tuple(sorted((input_to_output[first], input_to_output[second])))
    if output_edge not in used_edges:
        missing_constraints.append([first, second])
if missing_constraints:
    raise RuntimeError(
        f"filtered CDT omitted {len(missing_constraints)} boundary constraints"
    )

adjacency = {index: set() for index in used_output_indices}
for triangle in kept_triangles:
    for index in range(3):
        first = triangle[index]
        second = triangle[(index + 1) % 3]
        adjacency[first].add(second)
        adjacency[second].add(first)

fixed_coordinates = {
    output_index: vertex.co.copy()
    for output_index, vertex in output_existing.items()
}
boundary_output_indices = sorted(fixed_coordinates)
coordinates = {}
for index in used_output_indices:
    if index in fixed_coordinates:
        coordinates[index] = fixed_coordinates[index].copy()
    else:
        coordinates[index] = nearest_boundary_average(
            output_points[index],
            boundary_output_indices,
            output_points,
            fixed_coordinates,
        )

maximum_harmonic_delta = 0.0
for _iteration in range(HARMONIC_ITERATIONS):
    iteration_delta = 0.0
    for index in sorted(used_output_indices):
        if index in fixed_coordinates:
            continue
        neighbors = adjacency[index]
        if not neighbors:
            raise RuntimeError("unconnected CDT interior vertex")
        average = sum(
            (coordinates[neighbor] for neighbor in neighbors),
            Vector((0.0, 0.0, 0.0)),
        ) / len(neighbors)
        updated = (
            coordinates[index] * (1.0 - HARMONIC_RELAXATION)
            + average * HARMONIC_RELAXATION
        )
        iteration_delta = max(
            iteration_delta,
            (updated - coordinates[index]).length,
        )
        coordinates[index] = updated
    maximum_harmonic_delta = max(maximum_harmonic_delta, iteration_delta)
    if iteration_delta < 2e-9:
        break

output_vertices = dict(output_existing)
created_vertices = []
for index in sorted(used_output_indices):
    if index in output_vertices:
        continue
    vertex = bm.verts.new(coordinates[index])
    vertex[transition_class] = 1
    if surface_class is not None:
        vertex[surface_class] = 0
    if anatomy_zone is not None:
        vertex[anatomy_zone] = 30
    output_vertices[index] = vertex
    created_vertices.append(vertex)

patch_faces = []
for triangle in kept_triangles:
    vertices = tuple(output_vertices[index] for index in triangle)
    try:
        face = bm.faces.new(vertices)
    except ValueError as error:
        raise RuntimeError(f"could not create CDT triangle {triangle}: {error}")
    face.material_index = skin_index
    face.smooth = True
    patch_faces.append(face)
    if uv_layer is not None:
        center_uv = Vector((0.52, 0.38))
        for loop in face.loops:
            loop[uv_layer].uv = center_uv

before_hidden_faces = set(bm.faces)
bmesh.ops.triangle_fill(
    bm,
    edges=hidden_cycle,
    use_beauty=True,
    use_dissolve=False,
)
hidden_faces = [face for face in bm.faces if face not in before_hidden_faces]
for face in hidden_faces:
    face.material_index = skin_index
    face.smooth = True
    if uv_layer is not None:
        for loop in face.loops:
            loop[uv_layer].uv = Vector((0.52, 0.38))

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.normal_update()
final = topology_counts(bm)

local_retained_faces = []
patch_face_set = set(patch_faces) | set(hidden_faces)
for face in bm.faces:
    if face in patch_face_set:
        continue
    coordinates_face = [vertex.co for vertex in face.verts]
    if (
        max(abs(vertex.x) for vertex in coordinates_face) <= 0.085
        and max(vertex.y for vertex in coordinates_face) >= -0.215
        and min(vertex.y for vertex in coordinates_face) <= 0.040
        and max(vertex.z for vertex in coordinates_face) >= 0.655
        and min(vertex.z for vertex in coordinates_face) <= 0.870
    ):
        local_retained_faces.append(face)
intersections = intersection_report(patch_faces, local_retained_faces)

face_areas = [face.calc_area() for face in patch_faces]
patch_edges = {edge for face in patch_faces for edge in face.edges}
edge_lengths = [
    (edge.verts[1].co - edge.verts[0].co).length for edge in patch_edges
]
patch_bounds = {
    axis: [
        min(getattr(vertex.co, axis) for vertex in created_vertices),
        max(getattr(vertex.co, axis) for vertex in created_vertices),
    ]
    for axis in ("x", "y", "z")
}
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
geometry_gate = (
    min(face_areas) > 1e-12
    and max(edge_lengths) < 0.030
)

bm.to_mesh(body.data)
bm.free()
body.data.update()
mesh_validation_changed = body.data.validate(clean_customdata=False)
for polygon in body.data.polygons:
    polygon.use_smooth = True

body["status"] = (
    "REJECTED ENGINEERING TRIAL - ENCODED VISUAL REVIEW REQUIRED"
)
body["method"] = (
    "W5 OWNER-FACE CUT + ABSTRACT PAIR-OF-PANTS CDT + "
    "PINNED-BOUNDARY HARMONIC XYZ SOLVE + SEPARATE HIDDEN CAP"
)
body["boolean_used"] = False
body["global_remesh_used"] = False
body["radial_fan_used"] = False
body["donor_surface_transferred"] = False
body["runtime_activation_allowed"] = False
body["movement_started"] = False
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

report = {
    "schema": "kira.avatar.v23.r27a.broad_cdt_transition_trial.v1",
    "status": body["status"],
    "source": str(SOURCE),
    "output": str(BLEND_PATH),
    "window": WINDOW,
    "cut_faces": len(cut_faces),
    "authored_faces_excluded": authored_faces_excluded,
    "cycle_edges": {
        "outer_owner_surface": len(outer_cycle),
        "shaft_attachment": len(shaft_cycle),
        "scrotal_attachment": len(scrotal_cycle),
        "hidden_inner_fold": len(hidden_cycle),
    },
    "domain": DOMAIN,
    "input_domain_vertices": len(input_points),
    "output_domain_vertices": len(output_points),
    "kept_cdt_triangles": len(kept_triangles),
    "created_interior_vertices": len(created_vertices),
    "hidden_cap_faces": len(hidden_faces),
    "harmonic_iterations_requested": HARMONIC_ITERATIONS,
    "harmonic_relaxation": HARMONIC_RELAXATION,
    "maximum_iteration_delta_seen_meters": maximum_harmonic_delta,
    "patch_bounds": patch_bounds,
    "minimum_patch_triangle_area_m2": min(face_areas),
    "maximum_patch_edge_length_m": max(edge_lengths),
    "local_retained_faces_audited": len(local_retained_faces),
    "intersection_report": intersections,
    "baseline_topology": baseline,
    "final_topology": final,
    "topology_gate": topology_gate,
    "intersection_gate": intersection_gate,
    "geometry_gate": geometry_gate,
    "mesh_validate_changed_data": bool(mesh_validation_changed),
    "prohibited_methods": {
        "boolean": False,
        "global_remesh": False,
        "radial_or_center_fan": False,
        "donor_surface_transfer": False,
    },
    "visual_promotion": (
        "BLOCKED UNTIL ENCODED FRONT/SIDE/THREE-QUARTER "
        "FLAT, WIREFRAME, NORMAL, AND SILHOUETTE PASSES ARE INSPECTED"
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
