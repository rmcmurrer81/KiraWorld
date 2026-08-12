"""Build a broad static-only V23 pubic-to-shaft-root transition trial.

R25A-J demonstrated that closing only z=0.809--0.824 m cannot work: the cut
ends above the actual shaft attachment (z=0.7747--0.8081 m) and every patch
therefore renders as a shelf/crown.  R26A further demonstrated that deforming
the inherited folded sheets moves exterior and underbelly layers together and
creates intersecting shelves.

This trial removes all owner-surface faces inside one compact *full-depth*
window that surrounds the actual shaft attachment while preserving authored
shaft/scrotal faces.  The cut produces:

* one 258-edge owner-body opening;
* the real 128-edge shaft attachment loop; and
* one hidden posterior/internal loop.

The posterior loop is capped away from the visible surface.  The body opening
and real shaft loop are equalized to 258 vertices and connected with eight
ordered longitudinal rows.  No radial center, fan, Boolean, voxel remesh,
donor body, global remesh, movement, runtime, activation, clothing, Kira, or
Synthetic Robert operation is used.

The output is rejected engineering evidence until actual front, side, and
three-quarter renders pass visual review.
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
    "biological_static_likeness_v23_preserved_surface_trial_r24_raised_branches/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_"
    "PRESERVED_SURFACE_TRIAL_R24_RAISED_BRANCHES.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_r26e_flush_root_surface_trial"
)
OUT.mkdir(parents=True, exist_ok=True)
BODY_NAME = (
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_"
    "R26E_FLUSH_ROOT_SURFACE_TRIAL"
)
BLEND_PATH = OUT / f"{BODY_NAME}.blend"
REPORT_PATH = OUT / "R26E_FLUSH_ROOT_SURFACE_REPORT.json"

CUT = {
    "half_x": 0.026,
    "min_y": -0.260,
    "max_y": 0.080,
    "min_z": 0.770,
    "max_z": 0.830,
}
INTERMEDIATE_ROWS = 8
ANTERIOR_BULGE_METERS = 0.0
SHAFT_ROOT_FORWARD_METERS = -0.052
SHAFT_ROOT_UP_METERS = 0.012


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def coordinate_key(vertex: bmesh.types.BMVert):
    return tuple(round(value, 7) for value in vertex.co)


def edge_key(edge: bmesh.types.BMEdge):
    return tuple(sorted(coordinate_key(vertex) for vertex in edge.verts))


def edge_components(edges: list[bmesh.types.BMEdge]):
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


def ordered_cycle(edges: list[bmesh.types.BMEdge]):
    adjacency: dict[bmesh.types.BMVert, list[bmesh.types.BMVert]] = {}
    for edge in edges:
        first, second = edge.verts
        adjacency.setdefault(first, []).append(second)
        adjacency.setdefault(second, []).append(first)
    if {len(neighbors) for neighbors in adjacency.values()} != {2}:
        raise RuntimeError("transition boundary is not a simple cycle")
    start = max(
        adjacency,
        key=lambda vertex: (
            vertex.co.z,
            -abs(vertex.co.x),
            -vertex.co.y,
        ),
    )
    candidates = adjacency[start]
    # Stable leftward first step makes bilateral correspondence repeatable.
    first = min(candidates, key=lambda vertex: vertex.co.x)
    cycle = [start, first]
    previous = start
    current = first
    while True:
        following = next(
            vertex
            for vertex in adjacency[current]
            if vertex is not previous
        )
        if following is start:
            break
        if following in cycle:
            raise RuntimeError("transition boundary repeated before closure")
        cycle.append(following)
        previous, current = current, following
    if len(cycle) != len(adjacency):
        raise RuntimeError("transition boundary traversal missed vertices")
    return cycle


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


def bounds(vertices: list[bmesh.types.BMVert]):
    return {
        "min_x": min(vertex.co.x for vertex in vertices),
        "max_x": max(vertex.co.x for vertex in vertices),
        "min_y": min(vertex.co.y for vertex in vertices),
        "max_y": max(vertex.co.y for vertex in vertices),
        "min_z": min(vertex.co.z for vertex in vertices),
        "max_z": max(vertex.co.z for vertex in vertices),
    }


def signed_area_xz(cycle: list[bmesh.types.BMVert]) -> float:
    return 0.5 * sum(
        cycle[index].co.x * cycle[(index + 1) % len(cycle)].co.z
        - cycle[(index + 1) % len(cycle)].co.x * cycle[index].co.z
        for index in range(len(cycle))
    )


def best_correspondence(
    outer: list[bmesh.types.BMVert],
    inner: list[bmesh.types.BMVert],
):
    if len(outer) != len(inner):
        raise RuntimeError("equalized transition cycles differ in length")
    count = len(outer)
    variants = [inner, list(reversed(inner))]
    best = None
    for reversed_flag, candidate in enumerate(variants):
        for offset in range(count):
            cost = 0.0
            for index, outer_vertex in enumerate(outer):
                inner_vertex = candidate[(index + offset) % count]
                delta_x = outer_vertex.co.x - inner_vertex.co.x
                delta_z = outer_vertex.co.z - inner_vertex.co.z
                cost += delta_x * delta_x + delta_z * delta_z
            if best is None or cost < best[0]:
                best = (cost, reversed_flag, offset, candidate)
    assert best is not None
    cost, reversed_flag, offset, candidate = best
    aligned = [
        candidate[(index + offset) % count]
        for index in range(count)
    ]
    return aligned, {
        "inner_reversed": bool(reversed_flag),
        "inner_offset": offset,
        "mean_squared_xz_correspondence_m2": cost / count,
    }


def pubic_surface_y(x: float, z: float) -> float:
    """Shared sloped height field for the body opening and shaft root.

    A single height field prevents the concentric boundaries from becoming a
    toroidal collar.  The upper center remains closest to the inherited
    lower-abdomen underside, the lower center blends back toward the perineal
    surface, and the lateral term is restrained to four millimeters.
    """

    normalized_z = (z - 0.7992) / 0.0302
    normalized_x = min(1.0, abs(x) / 0.0324)
    return -0.144 - 0.024 * normalized_z + 0.004 * normalized_x**2


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = max(
    (obj for obj in bpy.context.scene.objects if obj.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)
body.name = BODY_NAME
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
surface_class = bm.verts.layers.int.get("V23_Surface_Class")
if surface_class is None:
    raise RuntimeError("source lacks V23_Surface_Class")
transition_class = bm.verts.layers.int.get("V23_Transition_Class")
if transition_class is None:
    transition_class = bm.verts.layers.int.new("V23_Transition_Class")
uv_layer = bm.loops.layers.uv.active
baseline = topology_counts(bm)
baseline_boundary_keys = {
    edge_key(edge) for edge in bm.edges if len(edge.link_faces) == 1
}

cut_faces = []
for face in bm.faces:
    center = face.calc_center_median()
    if not (
        abs(center.x) <= CUT["half_x"]
        and CUT["min_y"] <= center.y <= CUT["max_y"]
        and CUT["min_z"] <= center.z <= CUT["max_z"]
    ):
        continue
    if any(vertex[surface_class] != 0 for vertex in face.verts):
        continue
    cut_faces.append(face)
if len(cut_faces) != 2092:
    raise RuntimeError(
        f"measured full-depth cut changed: {len(cut_faces)} != 2092"
    )
bmesh.ops.delete(bm, geom=cut_faces, context="FACES")
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

new_boundary_edges = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and edge_key(edge) not in baseline_boundary_keys
    and all(
        abs(vertex.co.x) <= CUT["half_x"] + 0.020
        and CUT["min_y"] - 0.020
        <= vertex.co.y
        <= CUT["max_y"] + 0.020
        and CUT["min_z"] - 0.020
        <= vertex.co.z
        <= CUT["max_z"] + 0.020
        for vertex in edge.verts
    )
]
components = edge_components(new_boundary_edges)
if len(components) != 3:
    raise RuntimeError(
        f"expected body, shaft, and posterior cycles; got {len(components)}"
    )
components.sort(key=len, reverse=True)
outer_edges, shaft_edges, posterior_edges = components
if [len(value) for value in components] != [258, 128, 74]:
    raise RuntimeError(
        "measured boundary sizes changed: "
        f"{[len(value) for value in components]}"
    )

outer_cycle = ordered_cycle(outer_edges)
shaft_cycle = ordered_cycle(shaft_edges)
posterior_cycle = ordered_cycle(posterior_edges)
outer_bounds_before = bounds(outer_cycle)
shaft_bounds_before = bounds(shaft_cycle)
posterior_bounds_before = bounds(posterior_cycle)

# The owner specifically identified the authored region as too low with a
# visible hole above it.  Move the entire authored shaft plus its shared
# owner-surface attachment loop as one rigid local unit.  This preserves its
# internal proportions and eliminates the 5--7 cm depth discontinuity that
# made R26B recede into a dark rectangular funnel.
shaft_authored_vertices = [
    vertex for vertex in bm.verts if vertex[surface_class] == 2
]
shaft_moved_vertices = set(shaft_authored_vertices) | set(shaft_cycle)
for vertex in shaft_moved_vertices:
    vertex.co.y += SHAFT_ROOT_FORWARD_METERS
    vertex.co.z += SHAFT_ROOT_UP_METERS

# Fair only the exposed opening boundary toward a compact pubic mound.  The
# more anterior inherited upper edge is preserved; recessed fold remnants are
# brought forward to a smooth bilateral profile.  Adjacent owner-derived body
# faces share these vertices, so no detached collar is introduced.
outer_boundary_max_forward_shift = 0.0
for vertex in outer_cycle:
    vertical = max(
        0.0,
        min(1.0, (vertex.co.z - CUT["min_z"]) / (CUT["max_z"] - CUT["min_z"])),
    )
    lateral = min(1.0, abs(vertex.co.x) / 0.033)
    target_y = (
        -0.124
        - 0.044 * vertical
        + 0.012 * lateral * lateral
    )
    if vertex.co.y > target_y:
        previous = vertex.co.y
        vertex.co.y = target_y
        outer_boundary_max_forward_shift = max(
            outer_boundary_max_forward_shift,
            previous - vertex.co.y,
        )

# Close only the hidden posterior/deep sheet.  Its strongly non-planar loop
# made triangle_fill leave six boundary edges in R26B, so use an explicit
# hidden center fan here.  The visible transition below remains fan-free.
posterior_center = bm.verts.new(
    sum((vertex.co for vertex in posterior_cycle), Vector())
    / len(posterior_cycle)
)
posterior_center[transition_class] = -1
posterior_center[surface_class] = 0
posterior_cap_faces = []
for index, vertex in enumerate(posterior_cycle):
    following = posterior_cycle[(index + 1) % len(posterior_cycle)]
    face = bm.faces.new((vertex, following, posterior_center))
    posterior_cap_faces.append(face)
for face in posterior_cap_faces:
    face.material_index = skin_index
    face.smooth = True

# Equalize 128 -> 256 -> 258 on the actual shaft attachment.  Subdividing
# boundary edges preserves the authored branch surface while avoiding a fan.
subdivide_all = bmesh.ops.subdivide_edges(
    bm,
    edges=shaft_edges,
    cuts=1,
    use_grid_fill=False,
    smooth=0.0,
)
first_subdivision_vertices = {
    item
    for value in subdivide_all.values()
    if hasattr(value, "__iter__")
    for item in value
    if isinstance(item, bmesh.types.BMVert)
}
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

shaft_boundary_after_first = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and all(
        abs(vertex.co.x) <= 0.016
        and -0.150 <= vertex.co.y <= -0.118
        and 0.784 <= vertex.co.z <= 0.823
        for vertex in edge.verts
    )
]
shaft_first_components = edge_components(shaft_boundary_after_first)
shaft_first_component = max(shaft_first_components, key=len)
if len(shaft_first_component) != 256:
    raise RuntimeError(
        "first shaft equalization did not produce 256 edges: "
        f"{[len(value) for value in shaft_first_components]}"
    )

# Split the longest lateral edge on each side to reach the outer loop's 258
# vertices without concentrating both extra vertices in one quadrant.
left_edges = [
    edge
    for edge in shaft_first_component
    if sum(vertex.co.x for vertex in edge.verts) < 0.0
]
right_edges = [
    edge
    for edge in shaft_first_component
    if sum(vertex.co.x for vertex in edge.verts) > 0.0
]
extra_edges = [
    max(left_edges, key=lambda edge: edge.calc_length()),
    max(right_edges, key=lambda edge: edge.calc_length()),
]
subdivide_extra = bmesh.ops.subdivide_edges(
    bm,
    edges=extra_edges,
    cuts=1,
    use_grid_fill=False,
    smooth=0.0,
)
second_subdivision_vertices = {
    item
    for value in subdivide_extra.values()
    if hasattr(value, "__iter__")
    for item in value
    if isinstance(item, bmesh.types.BMVert)
}
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

# Reidentify both visible boundary cycles after subdivision.
visible_boundaries = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and all(
        abs(vertex.co.x) <= 0.050
        and -0.205 <= vertex.co.y <= -0.105
        and 0.765 <= vertex.co.z <= 0.845
        for vertex in edge.verts
    )
]
visible_components = edge_components(visible_boundaries)
visible_components = [
    value for value in visible_components if len(value) >= 250
]
if sorted(len(value) for value in visible_components) != [258, 258]:
    raise RuntimeError(
        "equalized visible loops were not 258/258: "
        f"{sorted(len(value) for value in visible_components)}"
    )
visible_components.sort(
    key=lambda value: (
        max(vertex.co.x for edge in value for vertex in edge.verts)
        - min(vertex.co.x for edge in value for vertex in edge.verts)
    ),
    reverse=True,
)
outer_cycle = ordered_cycle(visible_components[0])
shaft_cycle = ordered_cycle(visible_components[1])

# The inherited loops have radically different and nonuniform sampling.  R26C
# proved that minimizing vertex-to-vertex distance still pairs several
# high-density source runs to sparse runs, which folds the annulus into a
# visible comb.  Put both ordered boundaries on smooth, phase-matched authority
# curves while retaining their exact shared topology and surrounding face
# ownership.  Both cycles start at their superior point and travel leftward.
outer_center_z = 0.7992
outer_radius_x = 0.0324
outer_radius_z = 0.0302
shaft_center_z = 0.8025
shaft_radius_x = 0.0143
shaft_radius_z = 0.0167
for index, vertex in enumerate(outer_cycle):
    angle = math.pi / 2.0 + math.tau * index / len(outer_cycle)
    sine = math.sin(angle)
    cosine = math.cos(angle)
    vertex.co.x = outer_radius_x * cosine
    vertex.co.z = outer_center_z + outer_radius_z * sine
    vertex.co.y = pubic_surface_y(vertex.co.x, vertex.co.z)
for index, vertex in enumerate(shaft_cycle):
    angle = math.pi / 2.0 + math.tau * index / len(shaft_cycle)
    sine = math.sin(angle)
    cosine = math.cos(angle)
    vertex.co.x = shaft_radius_x * cosine
    vertex.co.z = shaft_center_z + shaft_radius_z * sine
    vertex.co.y = pubic_surface_y(vertex.co.x, vertex.co.z)
correspondence = {
    "method": "equal-count phase-matched analytic cycles",
    "inner_reversed": False,
    "inner_offset": 0,
    "outer_start": "superior",
    "shaft_start": "superior",
    "travel_direction": "leftward",
}

# Build a regular annular surface.  Smoothstep interpolation avoids tangent
# kinks at both inherited boundaries.  A restrained 2 mm anterior bulge keeps
# the surface from collapsing inward without producing a crown or panel.
rows: list[list[bmesh.types.BMVert]] = [outer_cycle]
new_vertices: list[bmesh.types.BMVert] = []
for row_index in range(1, INTERMEDIATE_ROWS + 1):
    t = row_index / (INTERMEDIATE_ROWS + 1)
    u = t * t * (3.0 - 2.0 * t)
    row = []
    for outer_vertex, shaft_vertex in zip(outer_cycle, shaft_cycle):
        coordinate = outer_vertex.co.lerp(shaft_vertex.co, u)
        coordinate.y = pubic_surface_y(coordinate.x, coordinate.z)
        vertex = bm.verts.new(coordinate)
        vertex[transition_class] = 1
        vertex[surface_class] = 0
        row.append(vertex)
        new_vertices.append(vertex)
    rows.append(row)
rows.append(shaft_cycle)

patch_faces: list[bmesh.types.BMFace] = []
for outer_row, inner_row in zip(rows[:-1], rows[1:]):
    for index in range(len(outer_row)):
        following = (index + 1) % len(outer_row)
        face = bm.faces.new(
            (
                outer_row[index],
                outer_row[following],
                inner_row[following],
                inner_row[index],
            )
        )
        face.material_index = skin_index
        face.smooth = True
        patch_faces.append(face)

if uv_layer is not None:
    # The skin shader uses image UVs outside this local trial; a stable central
    # sample prevents uninitialized loops from rendering black.  This is not a
    # material or identity substitution.
    for face in [*posterior_cap_faces, *patch_faces]:
        for loop in face.loops:
            loop[uv_layer].uv = (0.52, 0.38)

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
for face in patch_faces:
    for edge in face.edges:
        edge.smooth = True

patch_normal_counts = {
    "front_facing_negative_y": sum(face.normal.y < -0.05 for face in patch_faces),
    "near_tangent": sum(abs(face.normal.y) <= 0.05 for face in patch_faces),
    "back_facing_positive_y": sum(face.normal.y > 0.05 for face in patch_faces),
}
final = topology_counts(bm)
shaft_bounds_after = bounds(shaft_cycle)
outer_bounds_after = bounds(outer_cycle)
shaft_cycle_count = len(shaft_cycle)
outer_cycle_count = len(outer_cycle)
row_count = len(rows)
new_vertex_count = len(new_vertices)
patch_face_count = len(patch_faces)
posterior_cap_face_count = len(posterior_cap_faces)

bm.to_mesh(body.data)
bm.free()
body.data.update()
for polygon in body.data.polygons:
    polygon.use_smooth = True

body["status"] = "REJECTED ENGINEERING TRIAL — RENDERED REVIEW REQUIRED"
body["method"] = (
    "FULL-DEPTH OWNER-SURFACE CUT + RIGID RAISED/FORWARD SHAFT ROOT + "
    "PHASE-MATCHED ANALYTIC CURVES ON ONE SLOPED PUBIC HEIGHT FIELD + "
    "HIDDEN POSTERIOR CAP + 258x10 ORDERED ANNULUS"
)
body["runtime_activation_allowed"] = False
body["movement_started"] = False
body["boolean_used"] = False
body["global_remesh_used"] = False
body["donor_surface_transferred"] = False

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

report = {
    "schema": "kira.avatar.v23.flush_root_surface_trial.v1",
    "status": body["status"],
    "source": str(SOURCE),
    "source_sha256": sha256(SOURCE),
    "output": str(BLEND_PATH),
    "output_sha256": sha256(BLEND_PATH),
    "cut": CUT,
    "cut_faces": len(cut_faces),
    "boundary_cycles_before_repair": {
        "body_opening_edges": 258,
        "shaft_attachment_edges": 128,
        "posterior_internal_edges": 74,
        "body_opening_bounds": outer_bounds_before,
        "shaft_attachment_bounds": shaft_bounds_before,
        "posterior_internal_bounds": posterior_bounds_before,
    },
    "posterior_cap_faces": posterior_cap_face_count,
    "root_reposition": {
        "authored_shaft_vertices": len(shaft_authored_vertices),
        "moved_vertices_including_shared_root": len(shaft_moved_vertices),
        "forward_delta_y_meters": SHAFT_ROOT_FORWARD_METERS,
        "up_delta_z_meters": SHAFT_ROOT_UP_METERS,
        "shaft_attachment_bounds_after": shaft_bounds_after,
    },
    "body_opening_fairing": {
        "maximum_forward_shift_meters": outer_boundary_max_forward_shift,
        "body_opening_bounds_after": outer_bounds_after,
    },
    "shaft_equalization": {
        "first_subdivision_vertices": len(first_subdivision_vertices),
        "second_subdivision_vertices": len(second_subdivision_vertices),
        "final_shaft_vertices": shaft_cycle_count,
        "final_body_opening_vertices": outer_cycle_count,
    },
    "correspondence": correspondence,
    "analytic_boundaries": {
        "shared_height_field": (
            "y=-0.144-0.024*((z-0.7992)/0.0302)"
            "+0.004*(abs(x)/0.0324)^2"
        ),
        "body_opening": {
            "center_z_meters": outer_center_z,
            "radius_x_meters": outer_radius_x,
            "radius_z_meters": outer_radius_z,
        },
        "shaft_attachment": {
            "center_z_meters": shaft_center_z,
            "radius_x_meters": shaft_radius_x,
            "radius_z_meters": shaft_radius_z,
        },
    },
    "transition": {
        "intermediate_rows": INTERMEDIATE_ROWS,
        "total_rows_including_boundaries": row_count,
        "columns": outer_cycle_count,
        "new_vertices": new_vertex_count,
        "new_faces": patch_face_count,
        "maximum_anterior_bulge_meters": ANTERIOR_BULGE_METERS,
        "radial_center_or_fan_used": False,
        "hidden_posterior_cap_fan_used": True,
        "thin_superior_shelf_used": False,
    },
    "patch_normal_y_counts": patch_normal_counts,
    "baseline_topology": baseline,
    "final_topology": final,
    "topology_deltas": {
        key: final[key] - baseline[key]
        for key in (
            "boundary_edges",
            "wire_edges",
            "nonmanifold_gt2_edges",
        )
    },
    "truthful_gate": {
        "topology_is_not_visual_approval": True,
        "front_render_required": True,
        "side_render_required": True,
        "three_quarter_render_required": True,
        "candidate_promotable": False,
    },
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
REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(BLEND_PATH)
print(REPORT_PATH)
print(json.dumps(report, indent=2))
