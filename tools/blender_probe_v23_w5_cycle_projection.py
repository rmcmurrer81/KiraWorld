"""Read-only projection audit for the R24 W5 pubic reconstruction loops.

The broad W5 cut exposes an outer owner-surface boundary plus the real shaft,
scrotal, and hidden-inner attachment cycles.  A constrained triangulation is
only safe when its 2D parameterization is simple.  This probe measures the
ordered loops in the candidate X/Z and X/Y projection planes and records
segment intersections before any topology is authored.
"""

from __future__ import annotations

import json
import os
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
TRIAL_LABEL = os.environ.get("KIRA_PROJECTION_TRIAL_LABEL", "W5").upper()
OUTPUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    f"anatomy_reference_audit/{TRIAL_LABEL}_CYCLE_PROJECTION_AUDIT.json"
)
WINDOW = {
    "half_x": float(os.environ.get("KIRA_PROJECTION_HALF_X", "0.050")),
    "min_y": float(os.environ.get("KIRA_PROJECTION_MIN_Y", "-0.175")),
    "max_y": float(os.environ.get("KIRA_PROJECTION_MAX_Y", "-0.018")),
    "min_z": float(os.environ.get("KIRA_PROJECTION_MIN_Z", "0.695")),
    "max_z": float(os.environ.get("KIRA_PROJECTION_MAX_Z", "0.830")),
}


def coordinate_key(vertex: bmesh.types.BMVert):
    return tuple(round(float(value), 7) for value in vertex.co)


def edge_key(edge: bmesh.types.BMEdge):
    return tuple(sorted(coordinate_key(vertex) for vertex in edge.verts))


def components(edges: list[bmesh.types.BMEdge]):
    by_vertex: dict[bmesh.types.BMVert, list[bmesh.types.BMEdge]] = {}
    for edge in edges:
        for vertex in edge.verts:
            by_vertex.setdefault(vertex, []).append(edge)
    unseen = set(edges)
    result = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        component = [seed]
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
        raise RuntimeError("cycle is not simple in mesh topology")
    start = min(adjacency, key=lambda vertex: coordinate_key(vertex))
    result = [start]
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
        if next_vertex in result:
            raise RuntimeError("cycle traversal repeated a vertex")
        result.append(next_vertex)
        previous, current = current, next_vertex
    return result


def orientation(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (
        b[1] - a[1]
    ) * (c[0] - a[0])


def proper_segment_intersection(a, b, c, d, epsilon=1e-12):
    o1 = orientation(a, b, c)
    o2 = orientation(a, b, d)
    o3 = orientation(c, d, a)
    o4 = orientation(c, d, b)
    return (
        (o1 > epsilon and o2 < -epsilon or o1 < -epsilon and o2 > epsilon)
        and (o3 > epsilon and o4 < -epsilon or o3 < -epsilon and o4 > epsilon)
    )


def projection_report(ordered, axes):
    points = [
        (
            float(getattr(vertex.co, axes[0])),
            float(getattr(vertex.co, axes[1])),
        )
        for vertex in ordered
    ]
    area = 0.5 * sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )
    intersections = []
    for index in range(len(points)):
        a = points[index]
        b = points[(index + 1) % len(points)]
        for other in range(index + 1, len(points)):
            if other in {
                index,
                (index - 1) % len(points),
                (index + 1) % len(points),
            }:
                continue
            if index == 0 and other == len(points) - 1:
                continue
            c = points[other]
            d = points[(other + 1) % len(points)]
            if proper_segment_intersection(a, b, c, d):
                intersections.append([index, other])
    return {
        "axes": axes,
        "signed_area": area,
        "proper_self_intersection_count": len(intersections),
        "first_proper_self_intersections": intersections[:40],
    }


def vertex_uv(vertex, uv_layer):
    values = [
        loop[uv_layer].uv.copy()
        for face in vertex.link_faces
        for loop in face.loops
        if loop.vert is vertex
    ]
    if not values:
        return Vector((0.0, 0.0))
    total = Vector((0.0, 0.0))
    for value in values:
        total += value
    return total / len(values)


def arbitrary_point_projection_report(points, label):
    area = 0.5 * sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )
    intersections = []
    for index in range(len(points)):
        a = points[index]
        b = points[(index + 1) % len(points)]
        for other in range(index + 1, len(points)):
            if other in {
                index,
                (index - 1) % len(points),
                (index + 1) % len(points),
            }:
                continue
            if index == 0 and other == len(points) - 1:
                continue
            c = points[other]
            d = points[(other + 1) % len(points)]
            if proper_segment_intersection(a, b, c, d):
                intersections.append([index, other])
    return {
        "axes": label,
        "signed_area": area,
        "proper_self_intersection_count": len(intersections),
        "first_proper_self_intersections": intersections[:40],
        "bounds": {
            "u": [min(point[0] for point in points), max(point[0] for point in points)],
            "v": [min(point[1] for point in points), max(point[1] for point in points)],
        },
    }


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = max(
    (obj for obj in bpy.context.scene.objects if obj.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)
bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
surface_class = bm.verts.layers.int.get("V23_Surface_Class")
uv_layer = bm.loops.layers.uv.active
baseline_boundary = {
    edge_key(edge) for edge in bm.edges if len(edge.link_faces) == 1
}
cut_faces = []
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
        continue
    cut_faces.append(face)
bmesh.ops.delete(bm, geom=cut_faces, context="FACES")
new_edges = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1 and edge_key(edge) not in baseline_boundary
]
reports = []
for component in components(new_edges):
    ordered = ordered_cycle_vertices(component)
    center = {
        axis: sum(getattr(vertex.co, axis) for vertex in ordered) / len(ordered)
        for axis in ("x", "y", "z")
    }
    bounds = {
        axis: [
            min(getattr(vertex.co, axis) for vertex in ordered),
            max(getattr(vertex.co, axis) for vertex in ordered),
        ]
        for axis in ("x", "y", "z")
    }
    reports.append(
        {
            "edge_count": len(component),
            "center": center,
            "bounds": bounds,
            "xz": projection_report(ordered, ("x", "z")),
            "xy": projection_report(ordered, ("x", "y")),
            "yz": projection_report(ordered, ("y", "z")),
            "uv": (
                arbitrary_point_projection_report(
                    [
                        tuple(float(value) for value in vertex_uv(vertex, uv_layer))
                        for vertex in ordered
                    ],
                    "active_uv_average",
                )
                if uv_layer is not None
                else None
            ),
            "ordered_samples": [
                {
                    "cycle_index": index,
                    "coordinate": list(coordinate_key(vertex)),
                }
                for index, vertex in enumerate(ordered)
                if index % max(1, len(ordered) // 24) == 0
            ],
        }
    )
bm.free()
report = {
    "schema": "kira.avatar.v23.w5_cycle_projection_audit.v1",
    "trial_label": TRIAL_LABEL,
    "source": str(SOURCE),
    "window": WINDOW,
    "cut_faces": len(cut_faces),
    "cycles": sorted(reports, key=lambda item: item["edge_count"]),
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
