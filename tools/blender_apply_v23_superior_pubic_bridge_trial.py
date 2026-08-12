"""Replace the rejected V23 superior tunnel with a stitched bridge trial.

The visible dark teardrop in R22/R24 is a 12 mm high exterior discontinuity
between the lower-abdomen underside and the retained pubic surface.  It is not
the old internal boundary loop.  This bounded engineering pass removes only
the folded micro-surface inside the measured cut window, closes the hidden
inner cycle, and fills the exterior cycle with an explicitly shaped,
hand-authored radial superior pubic bridge.

No Boolean, voxel remesh, donor surface, runtime, movement, clothing, Kira, or
Synthetic Robert work is performed.  The result remains rejected engineering
evidence until its rendered views pass.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import bmesh
import bpy


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
    "biological_static_likeness_v23_r25j_analytic_coons_bridge_trial"
)
OUT.mkdir(parents=True, exist_ok=True)
BLEND_PATH = OUT / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_R25J_ANALYTIC_COONS_BRIDGE_TRIAL.blend"

WINDOW = {
    "half_x": 0.018,
    "min_y": -0.165,
    "max_y": -0.045,
    "min_z": 0.809,
    "max_z": 0.824,
}


def coordinate_key(vertex: bmesh.types.BMVert) -> tuple[float, float, float]:
    return tuple(round(value, 7) for value in vertex.co)


def edge_key(
    edge: bmesh.types.BMEdge,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    return tuple(sorted(coordinate_key(vertex) for vertex in edge.verts))


def components(
    edges: list[bmesh.types.BMEdge],
) -> list[list[bmesh.types.BMEdge]]:
    by_vertex: dict[bmesh.types.BMVert, list[bmesh.types.BMEdge]] = {}
    for edge in edges:
        for vertex in edge.verts:
            by_vertex.setdefault(vertex, []).append(edge)
    unseen = set(edges)
    result = []
    while unseen:
        seed = unseen.pop()
        current_component = [seed]
        stack = [seed]
        while stack:
            current = stack.pop()
            for vertex in current.verts:
                for neighbor in by_vertex[vertex]:
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        current_component.append(neighbor)
                        stack.append(neighbor)
        result.append(current_component)
    return result


def ordered_cycle_vertices(
    cycle: list[bmesh.types.BMEdge],
) -> list[bmesh.types.BMVert]:
    adjacency: dict[bmesh.types.BMVert, list[bmesh.types.BMVert]] = {}
    for edge in cycle:
        a, b = edge.verts
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
    if any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise RuntimeError("cannot order non-simple bridge cycle")
    start = min(
        adjacency,
        key=lambda vertex: (
            vertex.co.x,
            vertex.co.z,
            vertex.co.y,
        ),
    )
    result = [start]
    previous = None
    current = start
    while True:
        candidates = [
            vertex
            for vertex in adjacency[current]
            if vertex is not previous
        ]
        if not candidates:
            raise RuntimeError("bridge cycle traversal stopped early")
        if previous is None:
            # The left-upper start has one neighbor across the abdomen anchors
            # and one descending the left pubic side.  Always descend first so
            # the bilateral grid indices remain deterministic.
            next_vertex = max(candidates, key=lambda vertex: vertex.co.y)
        else:
            next_vertex = candidates[0]
        if next_vertex is start:
            break
        if next_vertex in result:
            raise RuntimeError("bridge cycle traversal repeated a vertex")
        result.append(next_vertex)
        previous, current = current, next_vertex
    if len(result) != len(adjacency):
        raise RuntimeError("bridge cycle traversal missed vertices")
    return result


def topology_counts(bm: bmesh.types.BMesh) -> dict[str, int]:
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


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = max(
    (obj for obj in bpy.context.scene.objects if obj.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)
body.name = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_R25J_ANALYTIC_COONS_BRIDGE_TRIAL"
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
baseline = topology_counts(bm)
baseline_boundary_keys = {
    edge_key(edge) for edge in bm.edges if len(edge.link_faces) == 1
}

cut_faces = [
    face
    for face in bm.faces
    if (
        abs(face.calc_center_median().x) <= WINDOW["half_x"]
        and WINDOW["min_y"]
        <= face.calc_center_median().y
        <= WINDOW["max_y"]
        and WINDOW["min_z"]
        <= face.calc_center_median().z
        <= WINDOW["max_z"]
    )
]
if len(cut_faces) != 408:
    raise RuntimeError(f"measured R24 cut changed: {len(cut_faces)} != 408")
bmesh.ops.delete(bm, geom=cut_faces, context="FACES")
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

new_boundary_edges = [
    edge
    for edge in bm.edges
    if (
        len(edge.link_faces) == 1
        and edge_key(edge) not in baseline_boundary_keys
        and all(
            abs(vertex.co.x) <= WINDOW["half_x"] + 0.012
            and WINDOW["min_y"] - 0.025
            <= vertex.co.y
            <= WINDOW["max_y"] + 0.025
            and WINDOW["min_z"] - 0.012
            <= vertex.co.z
            <= WINDOW["max_z"] + 0.012
            for vertex in edge.verts
        )
    )
]
cycles = components(new_boundary_edges)
if len(cycles) != 2:
    raise RuntimeError(f"expected two bridge cycles, found {len(cycles)}")
for cycle in cycles:
    degree: dict[bmesh.types.BMVert, int] = {}
    for edge in cycle:
        for vertex in edge.verts:
            degree[vertex] = degree.get(vertex, 0) + 1
    if set(degree.values()) != {2}:
        raise RuntimeError("bridge cut did not produce simple closed cycles")

cycles.sort(
    key=lambda cycle: min(
        vertex.co.y for edge in cycle for vertex in edge.verts
    )
)
outer_cycle, inner_cycle = cycles
outer_cycle_order = ordered_cycle_vertices(outer_cycle)
outer_cycle_order_coordinates = [
    [round(value, 7) for value in vertex.co]
    for vertex in outer_cycle_order
]

# The rendered R25B and R25C patches proved that closing/forward-projecting the
# cycle still leaves the original vertical separation visible.  R25D therefore
# applies the owner's actual correction: raise the lower root perimeter toward
# the lower-abdomen attachment while keeping the upper anchors fixed.  The
# vertical compression is bounded to this measured exterior cycle.
max_boundary_forward_shift = 0.0
max_boundary_upward_shift = 0.0
for vertex in outer_cycle_order:
    original_z = vertex.co.z
    t = max(0.0, min(1.0, (original_z - 0.808) / 0.016))
    lateral = min(1.0, abs(vertex.co.x) / 0.0223)
    target_y = -0.150 - 0.008 * t + 0.008 * lateral
    if vertex.co.y > target_y:
        old_y = vertex.co.y
        vertex.co.y = target_y
        max_boundary_forward_shift = max(
            max_boundary_forward_shift,
            old_y - vertex.co.y,
        )
    target_z = 0.8195 + 0.0043 * t
    if vertex.co.z < target_z:
        vertex.co.z = target_z
        max_boundary_upward_shift = max(
            max_boundary_upward_shift,
            vertex.co.z - original_z,
        )

# R25D eliminated most of the vertical gap but exposed the alternating
# high-frequency perimeter left by the source subdivision as a row of visible
# "teeth".  Smooth only the measured cycle, preserving the seven true
# lower-abdomen anchors at the top.  The surrounding faces follow the same
# vertices, so this is a continuous local fairing rather than a detached cap.
boundary_smoothing_iterations = 10
pinned_boundary_indices = {
    index
    for index, coordinate in enumerate(outer_cycle_order_coordinates)
    if coordinate[1] <= -0.145 and coordinate[2] >= 0.822
}
for _iteration in range(boundary_smoothing_iterations):
    coordinates = [vertex.co.copy() for vertex in outer_cycle_order]
    for index, vertex in enumerate(outer_cycle_order):
        if index in pinned_boundary_indices:
            continue
        previous = coordinates[(index - 1) % len(coordinates)]
        current = coordinates[index]
        following = coordinates[(index + 1) % len(coordinates)]
        average = (previous + current * 2.0 + following) * 0.25
        vertex.co.x = current.x * 0.80 + average.x * 0.20
        vertex.co.y = current.y * 0.55 + average.y * 0.45
        vertex.co.z = current.z * 0.55 + average.z * 0.45

# Replace the remaining saw-tooth parameterization with two explicit smooth
# authority curves.  The lower chain is a symmetric U-shaped attachment; the
# seven upper anchors form a smooth lower-abdomen arch.  Endpoints are
# identical, so the later Coons strip is closed without a cap or center fan.
before_analytic_coordinates = [
    vertex.co.copy() for vertex in outer_cycle_order
]
half_width = 0.0222858
for index, vertex in enumerate(outer_cycle_order[:111]):
    s = index / 110.0
    center_weight = math.sin(math.pi * s) ** 2
    vertex.co.x = -half_width * math.cos(math.pi * s)
    vertex.co.y = -0.1460 - 0.0060 * center_weight
    vertex.co.z = (
        0.81970
        + 0.00390 * abs(math.cos(math.pi * s)) ** 1.5
    )
top_indices_left_to_right = (0, 115, 114, 113, 112, 111, 110)
for index, cycle_index in enumerate(top_indices_left_to_right):
    s = index / 6.0
    center_weight = math.sin(math.pi * s) ** 2
    vertex = outer_cycle_order[cycle_index]
    vertex.co.x = -half_width + 2.0 * half_width * s
    vertex.co.y = -0.1460 - 0.0165 * center_weight
    vertex.co.z = 0.82360 + 0.00110 * center_weight
max_analytic_boundary_shift = max(
    (vertex.co - before).length
    for vertex, before in zip(
        outer_cycle_order,
        before_analytic_coordinates,
    )
)
reshaped_outer_cycle_coordinates = [
    [round(value, 7) for value in vertex.co]
    for vertex in outer_cycle_order
]

before_inner_faces = set(bm.faces)
inner_result = bmesh.ops.triangle_fill(
    bm,
    edges=inner_cycle,
    use_beauty=True,
    use_dissolve=False,
)
inner_faces = [
    face
    for face in bm.faces
    if face not in before_inner_faces
]
for face in inner_faces:
    face.material_index = skin_index
    face.smooth = True

outer_boundary_vertices = {
    vertex for edge in outer_cycle for vertex in edge.verts
}

# R25A-F proved that any disk/fan or cross-width convergence creates visible
# spokes.  Treat the perimeter as the two curves it actually contains: a short
# superior abdomen chain and a long inferior pubic/root chain.  Subdivide the
# six real superior boundary edges to exactly the inferior chain's 111
# vertices, then form a five-interval Hermite/Coons-like strip of quads.  No
# interior point is shared by an entire row and no center fan exists.
lower_chain_coordinates = [
    vertex.co.copy() for vertex in outer_cycle_order[:111]
]
top_seed_coordinates = [
    outer_cycle_order[index].co.copy()
    for index in (0, 115, 114, 113, 112, 111, 110)
]
top_segment_cuts = (18, 18, 17, 17, 17, 17)
top_chain_coordinates = [top_seed_coordinates[0].copy()]
top_subdivision_coordinates = []
for start_coordinate, end_coordinate, cuts in zip(
    top_seed_coordinates[:-1],
    top_seed_coordinates[1:],
    top_segment_cuts,
):
    bm.verts.ensure_lookup_table()
    local_vertices = [
        vertex
        for vertex in bm.verts
        if (
            abs(vertex.co.x) <= 0.024
            and -0.166 <= vertex.co.y <= -0.108
            and 0.818 <= vertex.co.z <= 0.826
        )
    ]
    start = min(
        local_vertices,
        key=lambda vertex: (vertex.co - start_coordinate).length_squared,
    )
    end = min(
        local_vertices,
        key=lambda vertex: (vertex.co - end_coordinate).length_squared,
    )
    if (start.co - start_coordinate).length_squared > 1e-12:
        raise RuntimeError("superior bridge start anchor moved unexpectedly")
    if (end.co - end_coordinate).length_squared > 1e-12:
        raise RuntimeError("superior bridge end anchor moved unexpectedly")
    edge = bm.edges.get((start, end))
    if edge is None:
        raise RuntimeError("measured superior bridge edge was not found")
    result = bmesh.ops.subdivide_edges(
        bm,
        edges=[edge],
        cuts=cuts,
        use_grid_fill=False,
        smooth=0.0,
    )
    direction = end_coordinate - start_coordinate
    length_squared = direction.length_squared
    new_vertices = {
        item
        for value in result.values()
        if hasattr(value, "__iter__")
        for item in value
        if (
            isinstance(item, bmesh.types.BMVert)
            and item is not start
            and item is not end
        )
    }
    ordered_new_vertices = sorted(
        new_vertices,
        key=lambda vertex: (
            (vertex.co - start_coordinate).dot(direction) / length_squared
        ),
    )
    if len(ordered_new_vertices) != cuts:
        raise RuntimeError(
            "superior boundary subdivision returned "
            f"{len(ordered_new_vertices)} vertices, expected {cuts}"
        )
    ordered_new_coordinates = [
        vertex.co.copy() for vertex in ordered_new_vertices
    ]
    top_chain_coordinates.extend(ordered_new_coordinates)
    top_chain_coordinates.append(end_coordinate.copy())
    top_subdivision_coordinates.extend(ordered_new_coordinates)

bm.verts.ensure_lookup_table()
local_lookup = {
    tuple(round(value, 7) for value in vertex.co): vertex
    for vertex in bm.verts
    if (
        abs(vertex.co.x) <= 0.024
        and -0.166 <= vertex.co.y <= -0.108
        and 0.818 <= vertex.co.z <= 0.826
    )
}
lower_chain = [
    local_lookup[tuple(round(value, 7) for value in coordinate)]
    for coordinate in lower_chain_coordinates
]
top_chain = [
    local_lookup[tuple(round(value, 7) for value in coordinate)]
    for coordinate in top_chain_coordinates
]
top_subdivision_vertices = [
    local_lookup[tuple(round(value, 7) for value in coordinate)]
    for coordinate in top_subdivision_coordinates
]

if len(top_chain) != len(lower_chain):
    raise RuntimeError(
        f"equal-chain invariant failed: {len(top_chain)} != "
        f"{len(lower_chain)}"
    )

strip_intermediate_rows = 4
strip_rows: list[list[bmesh.types.BMVert]] = [top_chain]
outer_vertices: list[bmesh.types.BMVert] = [
    *top_subdivision_vertices,
]
for row_index in range(1, strip_intermediate_rows + 1):
    u = row_index / (strip_intermediate_rows + 1)
    hermite_u = u * u * (3.0 - 2.0 * u)
    row = []
    for column, (top_vertex, lower_vertex) in enumerate(
        zip(top_chain, lower_chain)
    ):
        if column in {0, len(top_chain) - 1}:
            row.append(top_vertex)
            continue
        coordinate = (
            top_vertex.co * (1.0 - hermite_u)
            + lower_vertex.co * hermite_u
        )
        end_weight = min(
            1.0,
            min(column, len(top_chain) - 1 - column) / 12.0,
        )
        coordinate.y -= 0.0015 * 4.0 * u * (1.0 - u) * end_weight
        vertex = bm.verts.new(coordinate)
        row.append(vertex)
        outer_vertices.append(vertex)
    strip_rows.append(row)
strip_rows.append(lower_chain)

outer_faces: list[bmesh.types.BMFace] = []
last_column = len(top_chain) - 1
for upper_row, lower_row in zip(strip_rows[:-1], strip_rows[1:]):
    outer_faces.append(
        bm.faces.new(
            (
                upper_row[0],
                upper_row[1],
                lower_row[1],
            )
        )
    )
    for column in range(1, last_column - 1):
        outer_faces.append(
            bm.faces.new(
                (
                    upper_row[column],
                    upper_row[column + 1],
                    lower_row[column + 1],
                    lower_row[column],
                )
            )
        )
    outer_faces.append(
        bm.faces.new(
            (
                upper_row[last_column - 1],
                upper_row[last_column],
                lower_row[last_column - 1],
            )
        )
    )

local_open_edges = [
    edge
    for edge in bm.edges
    if (
        len(edge.link_faces) == 1
        and all(
            abs(vertex.co.x) <= 0.024
            and -0.166 <= vertex.co.y <= -0.108
            and 0.818 <= vertex.co.z <= 0.826
            for vertex in edge.verts
        )
    )
]
local_hole_fill_faces: list[bmesh.types.BMFace] = []
for face in outer_faces:
    face.material_index = skin_index
    face.smooth = True
    for edge in face.edges:
        edge.smooth = True
for face in inner_faces:
    for edge in face.edges:
        edge.smooth = True
max_bridge_y_delta = max(
    abs(vertex.co.y + 0.138)
    for vertex in outer_vertices
) if outer_vertices else 0.0

if uv_layer is not None:
    donor_uv = None
    for face in body.data.polygons:
        if face.material_index == skin_index:
            donor_uv = (0.52, 0.38)
            break
    donor_uv = donor_uv or (0.52, 0.38)
    for face in [*inner_faces, *outer_faces]:
        for loop in face.loops:
            loop[uv_layer].uv = donor_uv

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
outer_normal_average = [
    sum(face.normal[axis] for face in outer_faces) / len(outer_faces)
    for axis in range(3)
]
outer_normal_y_sign_counts = {
    "negative_front_facing": sum(face.normal.y < -0.05 for face in outer_faces),
    "near_tangent": sum(abs(face.normal.y) <= 0.05 for face in outer_faces),
    "positive_back_facing": sum(face.normal.y > 0.05 for face in outer_faces),
}
final = topology_counts(bm)
bm.to_mesh(body.data)
bm.free()
body.data.update()
for polygon in body.data.polygons:
    polygon.use_smooth = True

body["status"] = "REJECTED ENGINEERING TRIAL - RENDERED VISUAL REVIEW REQUIRED"
body["method"] = (
    "MEASURED 408-FACE SUPERIOR TUNNEL CUT + HIDDEN INNER CAP + "
    "BOUNDED RAISED ROOT + EQUAL-CHAIN HERMITE/COONS QUAD STRIP"
)
body["boolean_used"] = False
body["global_remesh_used"] = False
body["donor_surface_transferred"] = False
body["runtime_activation_allowed"] = False
body["movement_started"] = False

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
report = {
    "schema": "kira.avatar.v23.superior_pubic_bridge_trial.v2",
    "status": body["status"],
    "source": str(SOURCE),
    "output": str(BLEND_PATH),
    "window": WINDOW,
    "cut_faces": len(cut_faces),
    "outer_cycle_edges": len(outer_cycle),
    "outer_cycle_order_before_reshape": outer_cycle_order_coordinates,
    "outer_cycle_order_after_reshape": reshaped_outer_cycle_coordinates,
    "max_boundary_forward_shift_meters": max_boundary_forward_shift,
    "max_boundary_upward_shift_meters": max_boundary_upward_shift,
    "boundary_smoothing_iterations": boundary_smoothing_iterations,
    "pinned_boundary_indices": sorted(pinned_boundary_indices),
    "max_analytic_boundary_shift_meters": max_analytic_boundary_shift,
    "analytic_lower_chain": {
        "vertices": 111,
        "half_width_meters": half_width,
        "center_y_meters": -0.152,
        "center_z_meters": 0.81970,
    },
    "analytic_top_chain": {
        "seed_vertices": 7,
        "center_y_meters": -0.1625,
        "center_z_meters": 0.82470,
    },
    "inner_cycle_edges": len(inner_cycle),
    "inner_faces_created": len(inner_faces),
    "outer_faces_created": len(outer_faces),
    "outer_support_vertices_created": len(outer_vertices),
    "top_chain_vertices": len(top_chain),
    "lower_chain_vertices": len(lower_chain),
    "top_segment_cuts": list(top_segment_cuts),
    "strip_intermediate_rows": strip_intermediate_rows,
    "strip_total_rows": len(strip_rows),
    "local_open_edges_before_final_fill": len(local_open_edges),
    "local_hole_fill_faces": len(local_hole_fill_faces),
    "max_support_to_nominal_center_y_distance_meters": max_bridge_y_delta,
    "outer_normal_average_xyz": outer_normal_average,
    "outer_normal_y_sign_counts": outer_normal_y_sign_counts,
    "baseline_topology": baseline,
    "final_topology": final,
    "boundary_edge_delta": (
        final["boundary_edges"] - baseline["boundary_edges"]
    ),
    "wire_edge_delta": final["wire_edges"] - baseline["wire_edges"],
    "nonmanifold_gt2_delta": (
        final["nonmanifold_gt2_edges"] - baseline["nonmanifold_gt2_edges"]
    ),
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
(OUT / "SUPERIOR_PUBIC_BRIDGE_BUILD_REPORT.json").write_text(
    json.dumps(report, indent=2) + "\n",
    encoding="utf-8",
)
print(BLEND_PATH)
print(json.dumps(report, indent=2))
