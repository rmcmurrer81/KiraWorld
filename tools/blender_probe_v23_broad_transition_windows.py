"""Probe broader V23 pubic-to-root cut windows without saving a candidate.

The rejected R25A-J trials proved that the 0.809--0.824 m superior window is
too shallow: it ends just above the authored shaft attachment and therefore
turns every closure into a shelf/crown.  This diagnostic removes only
owner-surface faces (V23_Surface_Class == 0) in several larger windows while
leaving the authored shaft/scrotal branches in place.  It records the new
boundary components so the later hand-authored transition can stitch the real
body opening to the exposed anatomy-root boundary instead of covering it.

The source file is opened read-only and no .blend is written.
"""

from __future__ import annotations

import json
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
OUTPUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_r26b_broad_transition_probe/"
    "BROAD_TRANSITION_WINDOW_PROBE.json"
)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

WINDOWS = [
    {
        "name": "shaft_root_compact_all_depths",
        "half_x": 0.026,
        "min_y": -0.260,
        "max_y": 0.080,
        "min_z": 0.770,
        "max_z": 0.830,
    },
    {
        "name": "shaft_root_medium_all_depths",
        "half_x": 0.035,
        "min_y": -0.260,
        "max_y": 0.080,
        "min_z": 0.766,
        "max_z": 0.833,
    },
    {
        "name": "shaft_root_compact",
        "half_x": 0.024,
        "min_y": -0.180,
        "max_y": -0.020,
        "min_z": 0.772,
        "max_z": 0.828,
    },
    {
        "name": "shaft_root_medium",
        "half_x": 0.032,
        "min_y": -0.180,
        "max_y": -0.020,
        "min_z": 0.770,
        "max_z": 0.830,
    },
    {
        "name": "shaft_root_wide",
        "half_x": 0.040,
        "min_y": -0.180,
        "max_y": -0.020,
        "min_z": 0.765,
        "max_z": 0.832,
    },
    {
        "name": "shaft_and_scrotal_root_medium",
        "half_x": 0.038,
        "min_y": -0.180,
        "max_y": -0.015,
        "min_z": 0.690,
        "max_z": 0.832,
    },
]


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


def component_record(edges: list[bmesh.types.BMEdge]):
    vertices = {vertex for edge in edges for vertex in edge.verts}
    degrees = {
        vertex: sum(vertex in edge.verts for edge in edges)
        for vertex in vertices
    }
    return {
        "edges": len(edges),
        "vertices": len(vertices),
        "degree_set": sorted(set(degrees.values())),
        "simple_cycle": set(degrees.values()) == {2},
        "bounds": {
            "min_x": min(vertex.co.x for vertex in vertices),
            "max_x": max(vertex.co.x for vertex in vertices),
            "min_y": min(vertex.co.y for vertex in vertices),
            "max_y": max(vertex.co.y for vertex in vertices),
            "min_z": min(vertex.co.z for vertex in vertices),
            "max_z": max(vertex.co.z for vertex in vertices),
        },
        "center": {
            axis: sum(getattr(vertex.co, axis) for vertex in vertices)
            / len(vertices)
            for axis in ("x", "y", "z")
        },
        "surface_class_counts": {},
    }


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = max(
    (obj for obj in bpy.context.scene.objects if obj.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)

base = bmesh.new()
base.from_mesh(body.data)
base.verts.ensure_lookup_table()
base.edges.ensure_lookup_table()
base.faces.ensure_lookup_table()
baseline_boundary = {
    edge_key(edge) for edge in base.edges if len(edge.link_faces) == 1
}

results = []
for window in WINDOWS:
    bm = base.copy()
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    surface_class = bm.verts.layers.int.get("V23_Surface_Class")
    if surface_class is None:
        raise RuntimeError("source lacks V23_Surface_Class")

    cut_faces = []
    for face in bm.faces:
        center = face.calc_center_median()
        if not (
            abs(center.x) <= window["half_x"]
            and window["min_y"] <= center.y <= window["max_y"]
            and window["min_z"] <= center.z <= window["max_z"]
        ):
            continue
        # Preserve all authored shaft/scrotal faces.  A mixed boundary face is
        # also preserved so the real root loop, rather than an arbitrary slice
        # through the branch, becomes the lower stitch authority.
        if any(vertex[surface_class] != 0 for vertex in face.verts):
            continue
        cut_faces.append(face)

    bmesh.ops.delete(bm, geom=cut_faces, context="FACES")
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    new_boundary_edges = [
        edge
        for edge in bm.edges
        if len(edge.link_faces) == 1
        and edge_key(edge) not in baseline_boundary
        and all(
            abs(vertex.co.x) <= window["half_x"] + 0.020
            and window["min_y"] - 0.020
            <= vertex.co.y
            <= window["max_y"] + 0.020
            and window["min_z"] - 0.020
            <= vertex.co.z
            <= window["max_z"] + 0.020
            for vertex in edge.verts
        )
    ]
    component_records = []
    for component in edge_components(new_boundary_edges):
        record = component_record(component)
        vertices = {vertex for edge in component for vertex in edge.verts}
        counts: dict[str, int] = {}
        for vertex in vertices:
            key = str(vertex[surface_class])
            counts[key] = counts.get(key, 0) + 1
        record["surface_class_counts"] = counts
        component_records.append(record)
    component_records.sort(
        key=lambda item: (
            -item["vertices"],
            -item["center"]["z"],
        )
    )
    results.append(
        {
            "window": window,
            "cut_faces": len(cut_faces),
            "new_boundary_edges": len(new_boundary_edges),
            "component_count": len(component_records),
            "components": component_records,
        }
    )
    bm.free()

base.free()

report = {
    "schema": "kira.avatar.v23.broad_transition_window_probe.v1",
    "source": str(SOURCE),
    "diagnostic_only": True,
    "candidate_saved_or_modified": False,
    "purpose": (
        "Find a cut that includes the true shaft/scrotal attachment and all "
        "nested fold sheets after the 0.809--0.824 m approach failed."
    ),
    "results": results,
}
OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(OUTPUT)
print(json.dumps(results, indent=2))
