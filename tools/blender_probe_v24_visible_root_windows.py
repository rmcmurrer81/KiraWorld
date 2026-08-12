"""Probe clean V24 front-visible attachment windows.

The clean V1-derived V24 substrate has no authored anatomy and no contaminated
union sheets.  This read-only probe identifies small first-hit skin patches
for separate shaft and scrotal roots.  A valid window must expose exactly one
simple, non-self-intersecting boundary cycle per root.
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
    "biological_static_likeness_v24_clean_v1_rebase/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24_CLEAN_V1_REBASE.blend"
)
OUTPUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/V24_VISIBLE_ROOT_WINDOW_PROBE.json"
)
TRIALS = [
    {
        "label": "a",
        "shaft": {"center_z": 0.800, "radius_x": 0.014, "radius_z": 0.014},
        "scrotal": {"center_z": 0.744, "radius_x": 0.020, "radius_z": 0.022},
    },
    {
        "label": "b",
        "shaft": {"center_z": 0.794, "radius_x": 0.015, "radius_z": 0.016},
        "scrotal": {"center_z": 0.735, "radius_x": 0.021, "radius_z": 0.024},
    },
    {
        "label": "c",
        "shaft": {"center_z": 0.788, "radius_x": 0.016, "radius_z": 0.017},
        "scrotal": {"center_z": 0.728, "radius_x": 0.022, "radius_z": 0.026},
    },
    {
        "label": "d_high",
        "shaft": {"center_z": 0.806, "radius_x": 0.016, "radius_z": 0.016},
        "scrotal": {"center_z": 0.752, "radius_x": 0.022, "radius_z": 0.024},
    },
    {
        "label": "e_combined_high",
        "shaft": {"center_z": 0.806, "radius_x": 0.035, "radius_z": 0.028},
        "scrotal": {"center_z": 0.758, "radius_x": 0.034, "radius_z": 0.030},
    },
    {
        "label": "f_combined_mid",
        "shaft": {"center_z": 0.798, "radius_x": 0.040, "radius_z": 0.032},
        "scrotal": {"center_z": 0.744, "radius_x": 0.038, "radius_z": 0.034},
    },
    {
        "label": "g_single_broad",
        "shaft": {"center_z": 0.782, "radius_x": 0.044, "radius_z": 0.060},
        "scrotal": {"center_z": 0.782, "radius_x": 0.044, "radius_z": 0.060},
    },
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
            return None
        ordered.append(following)
        previous, current = current, following
    return ordered


def orientation(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (
        b[1] - a[1]
    ) * (c[0] - a[0])


def proper_intersections(points):
    result = []
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
                result.append([index, other])
    return result


def in_window(point, window):
    return (
        (point.x / window["radius_x"]) ** 2
        + ((point.z - window["center_z"]) / window["radius_z"]) ** 2
        <= 1.0
    )


def run(trial):
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    body = bpy.data.objects[
        "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24_CLEAN_V1_REBASE"
    ]
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    for index, face in enumerate(bm.faces):
        face.index = index
    baseline_boundary = {
        edge_key(edge) for edge in bm.edges if len(edge.link_faces) == 1
    }
    bvh = BVHTree.FromBMesh(bm)
    cut_faces = []
    cut_by_window = {"shaft": 0, "scrotal": 0}
    for face in bm.faces:
        center = face.calc_center_median()
        matching = [
            label
            for label in ("shaft", "scrotal")
            if in_window(center, trial[label])
        ]
        if not matching:
            continue
        hit, _normal, hit_index, _distance = bvh.ray_cast(
            Vector((center.x, -0.35, center.z)),
            Vector((0.0, 1.0, 0.0)),
            0.70,
        )
        if hit is None or hit_index != face.index:
            continue
        cut_faces.append(face)
        for label in matching:
            cut_by_window[label] += 1
    bmesh.ops.delete(bm, geom=cut_faces, context="FACES")
    new_boundary = [
        edge
        for edge in bm.edges
        if len(edge.link_faces) == 1 and edge_key(edge) not in baseline_boundary
    ]
    reports = []
    for component in components(new_boundary):
        vertices = {vertex for edge in component for vertex in edge.verts}
        ordered = ordered_cycle(component)
        intersections = (
            proper_intersections(
                [(float(vertex.co.x), float(vertex.co.z)) for vertex in ordered]
            )
            if ordered
            else []
        )
        reports.append(
            {
                "edge_count": len(component),
                "simple_cycle": ordered is not None,
                "xz_proper_self_intersection_count": len(intersections),
                "first_xz_intersections": intersections[:20],
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
                "mean_retained_normal": [
                    sum(
                        sum((face.normal[axis] for face in vertex.link_faces), 0.0)
                        / max(1, len(vertex.link_faces))
                        for vertex in vertices
                    )
                    / len(vertices)
                    for axis in range(3)
                ],
                "ordered_cycle_coordinates": (
                    [
                        [float(value) for value in vertex.co]
                        for vertex in ordered
                    ]
                    if ordered
                    else []
                ),
            }
        )
    bm.free()
    return {
        "trial": trial,
        "cut_faces": len(cut_faces),
        "cut_faces_by_window": cut_by_window,
        "cycle_count": len(reports),
        "cycles": sorted(reports, key=lambda item: item["center"]["z"], reverse=True),
    }


report = {
    "schema": "kira.avatar.v24.visible_root_window_probe.v1",
    "source": str(SOURCE),
    "trials": [run(trial) for trial in TRIALS],
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
