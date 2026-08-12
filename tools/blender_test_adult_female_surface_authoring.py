"""In-memory Blender smoke test for the generic continuous-surface adapter.

The fixture is an identity-neutral closed ellipsoid with one normalized root
weight.  Nothing is saved, rendered, exported, assigned, or activated.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import bmesh
import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_adult_female_surface_authoring import (
    frame_from_mapping,
    parameters_from_mapping,
)
from tools.blender_author_adult_female_external_surface import (
    author_continuous_adult_female_surface,
)


for existing in list(bpy.data.objects):
    bpy.data.objects.remove(existing, do_unlink=True)

mesh = bpy.data.meshes.new("GenericClosedWeightedPrimarySurface")
bm = bmesh.new()
bmesh.ops.create_uvsphere(
    bm,
    u_segments=48,
    v_segments=32,
    radius=1.0,
)
for vert in bm.verts:
    vert.co.x *= 0.16
    vert.co.y *= 0.12
    vert.co.z *= 0.22
bm.to_mesh(mesh)
bm.free()
mesh.update(calc_edges=True)

body = bpy.data.objects.new("GenericClosedWeightedPrimarySurface", mesh)
bpy.context.collection.objects.link(body)
pelvis_a = body.vertex_groups.new(name="pelvis_a")
pelvis_b = body.vertex_groups.new(name="pelvis_b")
source_skin_weights = []
for vertex in mesh.vertices:
    first = 0.25 + 0.50 * ((float(vertex.co.z) / 0.22 + 1.0) * 0.5)
    second = 1.0 - first
    pelvis_a.add([vertex.index], first, "REPLACE")
    pelvis_b.add([vertex.index], second, "REPLACE")
    source_skin_weights.append((first, second))
source_vertex_count = len(mesh.vertices)

frame = frame_from_mapping(
    {
        "coordinate_space": "object_local",
        "origin": [0.0, -0.12, 0.0],
        "lateral_axis": [1.0, 0.0, 0.0],
        "longitudinal_axis": [0.0, 0.0, 1.0],
        "outward_axis": [0.0, -1.0, 0.0],
        "half_width_m": 0.07,
        "half_length_m": 0.13,
        "max_surface_offset_m": 0.035,
    }
)
parameters = parameters_from_mapping(
    {
        "subdivision_cuts": 1,
        "relief_scale_m": 0.0015,
        "minimum_landmark_vertices": 2,
        "landmark_influence_threshold": 0.20,
    }
)
report = author_continuous_adult_female_surface(
    body,
    frame=frame,
    parameters=parameters,
    project_root=PROJECT_ROOT,
)

assert report["status"] == "AUTHORED_INACTIVE_AWAITING_INDEPENDENT_REVIEW"
assert report["result_topology"]["primary_surface_components"] == 1
assert report["result_topology"]["boundary_edges"] == 0
assert report["result_topology"]["nonmanifold_edges"] == 0
assert report["result_topology"]["nonadjacent_self_intersection_pairs"] == 0
assert report["skin_weights"]["unweighted_vertex_count"] == 0
group_names = {group.index: group.name for group in body.vertex_groups}
for index in range(source_vertex_count):
    actual = {
        group_names[item.group]: float(item.weight)
        for item in body.data.vertices[index].groups
        if group_names[item.group] in {"pelvis_a", "pelvis_b"}
    }
    expected_a, expected_b = source_skin_weights[index]
    assert abs(actual["pelvis_a"] - expected_a) <= 1.0e-7
    assert abs(actual["pelvis_b"] - expected_b) <= 1.0e-7
assert report["runtime_activation_allowed"] is False
assert report["render_performed"] is False
assert report["export_performed"] is False
assert len(bpy.data.objects) == 1

print(
    "ADULT_FEMALE_SURFACE_SMOKE_PASS "
    + json.dumps(
        {
            "source_topology": report["source_topology"],
            "result_topology": report["result_topology"],
            "new_vertex_count": report["new_vertex_count"],
            "authored_vertex_count": report["authored_vertex_count"],
            "landmark_vertex_counts": report["landmark_vertex_counts"],
            "object_count": len(bpy.data.objects),
            "render_performed": report["render_performed"],
            "export_performed": report["export_performed"],
            "runtime_activation_allowed": report["runtime_activation_allowed"],
        },
        sort_keys=True,
    )
)
