"""Probe front-visible owner-surface cuts around the R24 superior tunnel.

The broad axis-aligned cut traverses both anterior and hidden sheets.  This
read-only probe instead ray-tests candidate owner faces from the front and
deletes only faces that are the first encoded surface hit.  It reports whether
the resulting boundary cycles are simple in the front X/Z projection.
"""

from __future__ import annotations

import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_preserved_surface_trial_r24_raised_branches/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_"
    "PRESERVED_SURFACE_TRIAL_R24_RAISED_BRANCHES.blend"
)
OUTPUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/R24_FRONT_VISIBLE_CUT_PROBE.json"
)
WINDOWS = [
    {"label": "s1", "half_x": 0.025, "min_z": 0.780, "max_z": 0.832},
    {"label": "s2", "half_x": 0.035, "min_z": 0.770, "max_z": 0.835},
    {"label": "s3", "half_x": 0.045, "min_z": 0.760, "max_z": 0.838},
    {"label": "s4", "half_x": 0.055, "min_z": 0.750, "max_z": 0.840},
]


def coordinate_key(vertex):
    return tuple(round(float(value), 7) for value in vertex.co)


def edge_key(edge):
    return tuple(sorted(coordinate_key(vertex) for vertex in edge.verts))


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
        return None
    start = min(adjacency, key=coordinate_key)
    result = [start]
    previous = None
    current = start
    while True:
        candidates = [vertex for vertex in adjacency[current] if vertex is not previous]
        following = (
            min(candidates, key=coordinate_key) if previous is None else candidates[0]
        )
        if following is start:
            break
        if following in result:
            return None
        result.append(following)
        previous, current = current, following
    return result


def orientation(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (
        b[1] - a[1]
    ) * (c[0] - a[0])


def proper_intersections(points):
    count = 0
    first = []
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
            o1 = orientation(a, b, c)
            o2 = orientation(a, b, d)
            o3 = orientation(c, d, a)
            o4 = orientation(c, d, b)
            if (
                (o1 > 1e-12 and o2 < -1e-12 or o1 < -1e-12 and o2 > 1e-12)
                and (o3 > 1e-12 and o4 < -1e-12 or o3 < -1e-12 and o4 > 1e-12)
            ):
                count += 1
                if len(first) < 30:
                    first.append([index, other])
    return count, first


def cyclic_true_arcs(values):
    """Return contiguous True index arcs on a cyclic boolean sequence."""
    if not any(values):
        return []
    if all(values):
        return [list(range(len(values)))]
    start_false = next(index for index, value in enumerate(values) if not value)
    arcs = []
    current = []
    for offset in range(1, len(values) + 1):
        index = (start_false + offset) % len(values)
        if values[index]:
            current.append(index)
        elif current:
            arcs.append(current)
            current = []
    if current:
        arcs.append(current)
    return arcs


def arc_report(ordered, threshold):
    arcs = cyclic_true_arcs([vertex.co.y <= threshold for vertex in ordered])
    reports = []
    for arc in arcs:
        vertices = [ordered[index] for index in arc]
        reports.append(
            {
                "vertex_count": len(vertices),
                "start_index": arc[0],
                "end_index": arc[-1],
                "bounds": {
                    axis: [
                        min(getattr(vertex.co, axis) for vertex in vertices),
                        max(getattr(vertex.co, axis) for vertex in vertices),
                    ]
                    for axis in ("x", "y", "z")
                },
                "endpoints": [
                    list(coordinate_key(vertices[0])),
                    list(coordinate_key(vertices[-1])),
                ],
            }
        )
    return sorted(reports, key=lambda item: item["vertex_count"], reverse=True)


def vertex_retained_normal(vertex):
    total = Vector((0.0, 0.0, 0.0))
    for face in vertex.link_faces:
        total += face.normal
    return total.normalized() if total.length > 1e-12 else total


def predicate_arc_report(ordered, predicate):
    arcs = cyclic_true_arcs([predicate(vertex) for vertex in ordered])
    reports = []
    for arc in arcs:
        vertices = [ordered[index] for index in arc]
        reports.append(
            {
                "vertex_count": len(vertices),
                "start_index": arc[0],
                "end_index": arc[-1],
                "bounds": {
                    axis: [
                        min(getattr(vertex.co, axis) for vertex in vertices),
                        max(getattr(vertex.co, axis) for vertex in vertices),
                    ]
                    for axis in ("x", "y", "z")
                },
                "mean_retained_normal": [
                    sum(vertex_retained_normal(vertex)[axis] for vertex in vertices)
                    / len(vertices)
                    for axis in range(3)
                ],
            }
        )
    return sorted(reports, key=lambda item: item["vertex_count"], reverse=True)


def run(window):
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
    for index, face in enumerate(bm.faces):
        face.index = index
    surface_class = bm.verts.layers.int.get("V23_Surface_Class")
    baseline_boundary = {
        edge_key(edge) for edge in bm.edges if len(edge.link_faces) == 1
    }
    bvh = BVHTree.FromBMesh(bm)
    cut_faces = []
    visible_candidates = 0
    for face in bm.faces:
        center = face.calc_center_median()
        if not (
            abs(center.x) <= window["half_x"]
            and window["min_z"] <= center.z <= window["max_z"]
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
        if hit is None:
            continue
        if hit_index == face.index:
            visible_candidates += 1
            cut_faces.append(face)
    bmesh.ops.delete(bm, geom=cut_faces, context="FACES")
    new_edges = [
        edge
        for edge in bm.edges
        if len(edge.link_faces) == 1 and edge_key(edge) not in baseline_boundary
    ]
    cycle_reports = []
    for component in components(new_edges):
        vertices = {vertex for edge in component for vertex in edge.verts}
        ordered = ordered_cycle(component)
        projection_count = None
        projection_first = []
        if ordered:
            projection_count, projection_first = proper_intersections(
                [(float(vertex.co.x), float(vertex.co.z)) for vertex in ordered]
            )
        cycle_reports.append(
            {
                "edge_count": len(component),
                "vertex_count": len(vertices),
                "simple_cycle": ordered is not None,
                "xz_proper_self_intersections": projection_count,
                "first_xz_intersections": projection_first,
                "bounds": {
                    axis: [
                        min(getattr(vertex.co, axis) for vertex in vertices),
                        max(getattr(vertex.co, axis) for vertex in vertices),
                    ]
                    for axis in ("x", "y", "z")
                },
                "center": {
                    axis: sum(getattr(vertex.co, axis) for vertex in vertices)
                    / len(vertices)
                    for axis in ("x", "y", "z")
                },
                "front_depth_arcs": (
                    {
                        str(threshold): arc_report(ordered, threshold)
                        for threshold in (-0.12, -0.10, -0.09, -0.08, -0.07, -0.06)
                    }
                    if ordered
                    else {}
                ),
                "normal_arcs": (
                    {
                        str(threshold): predicate_arc_report(
                            ordered,
                            lambda vertex, value=threshold: (
                                vertex_retained_normal(vertex).y <= value
                            ),
                        )
                        for threshold in (-0.8, -0.6, -0.4, -0.2, 0.0)
                    }
                    if ordered
                    else {}
                ),
                "ordered_samples": (
                    [
                        {
                            "index": index,
                            "coordinate": list(coordinate_key(vertex)),
                            "retained_normal": [
                                round(float(value), 6)
                                for value in vertex_retained_normal(vertex)
                            ],
                        }
                        for index, vertex in enumerate(ordered)
                        if index % max(1, len(ordered) // 48) == 0
                    ]
                    if ordered
                    else []
                ),
            }
        )
    bm.free()
    return {
        "window": window,
        "cut_faces": len(cut_faces),
        "front_visible_faces": visible_candidates,
        "new_boundary_edges": len(new_edges),
        "cycles": sorted(cycle_reports, key=lambda item: item["edge_count"]),
    }


report = {
    "schema": "kira.avatar.v23.r24.front_visible_cut_probe.v1",
    "source": str(SOURCE),
    "trials": [run(window) for window in WINDOWS],
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
