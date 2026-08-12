"""In-memory MakeHuman wrapper smoke test; saves and renders nothing."""

from __future__ import annotations

import json
from pathlib import Path
import sys

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
from tools.blender_audit_rapid_body_candidate import self_intersection_audit
from tools.blender_build_makehuman_adult_female_foundation_inactive import (
    _apply_target,
    _attach_normalized_default_weights,
    _compact_and_scale,
    _foundation_source_bindings,
    _new_body,
    _parse_body_group,
)
from tools.blender_repair_bounded_self_intersections import (
    repair_bounded_self_intersections,
)


for existing in list(bpy.data.objects):
    bpy.data.objects.remove(existing, do_unlink=True)

base_path, target_bindings, _entry = _foundation_source_bindings()
vertices, faces = _parse_body_group(base_path)
for target_path, target_weight in target_bindings:
    _apply_target(vertices, target_path, target_weight)
compact, compact_faces, old_to_new, _transform = _compact_and_scale(
    vertices,
    faces,
    1.70,
)
body = _new_body(
    "generic_makehuman_adult_female_surface_smoke",
    compact,
    compact_faces,
)
_attach_normalized_default_weights(body, old_to_new)
cleanup = repair_bounded_self_intersections(body)

report = author_continuous_adult_female_surface(
    body,
    frame=frame_from_mapping(
        {
            "coordinate_space": "object_local",
            "origin": [0.0, -0.070, 0.79],
            "lateral_axis": [1.0, 0.0, 0.0],
            "longitudinal_axis": [0.0, -0.30, 0.9539392014],
            "outward_axis": [0.0, -0.9539392014, -0.30],
            "half_width_m": 0.060,
            "half_length_m": 0.135,
            "max_surface_offset_m": 0.090,
        }
    ),
    parameters=parameters_from_mapping(
        {
            "subdivision_cuts": 3,
            "relief_scale_m": 0.0024,
            "minimum_face_normal_alignment": 0.05,
            "minimum_landmark_vertices": 8,
            "landmark_influence_threshold": 0.10,
        }
    ),
    project_root=PROJECT_ROOT,
)
independent_bvh = self_intersection_audit(body)

assert report["result_topology"]["primary_surface_components"] == 1
assert report["result_topology"]["boundary_edges"] == 0
assert report["result_topology"]["nonmanifold_edges"] == 0
assert cleanup["initial_exact_genuine_pair_count"] == 20
assert cleanup["final_exact_genuine_pair_count"] == 0
assert cleanup["weight_digest_preserved"] is True
assert cleanup["topology_changed"] is False
assert report["authored_region_nonadjacent_self_intersection_pairs"] == 0
assert report["result_global_nonadjacent_self_intersection_pairs"] <= report[
    "inherited_global_nonadjacent_self_intersection_pairs"
]
assert report["skin_weights"]["unweighted_vertex_count"] == 0
assert report["authored_nonplanar_faces_triangulated"] > 0
assert independent_bvh["nonadjacent_intersecting_triangle_pair_count"] == 0
assert independent_bvh["nonadjacent_intersecting_source_face_pair_count"] == 0
assert independent_bvh["exact_genuine_nonadjacent_triangle_pair_count"] == 0
assert independent_bvh["exact_genuine_nonadjacent_source_face_pair_count"] == 0
assert independent_bvh["exact_narrow_phase_gate_passed"] is True
assert len(bpy.data.objects) == 1
assert report["render_performed"] is False
assert report["export_performed"] is False
assert report["runtime_activation_allowed"] is False

print(
    "MAKEHUMAN_ADULT_FEMALE_SURFACE_SMOKE_PASS "
    + json.dumps(
        {
            "source_topology": report["source_topology"],
            "result_topology": report["result_topology"],
            "cleanup": {
                "initial_exact_genuine_pair_count": cleanup[
                    "initial_exact_genuine_pair_count"
                ],
                "final_exact_genuine_pair_count": cleanup[
                    "final_exact_genuine_pair_count"
                ],
                "changed_vertex_count": cleanup["changed_vertex_count"],
                "maximum_coordinate_displacement_m": cleanup[
                    "maximum_coordinate_displacement_m"
                ],
                "weight_digest_preserved": cleanup[
                    "weight_digest_preserved"
                ],
            },
            "new_vertex_count": report["new_vertex_count"],
            "authored_vertex_count": report["authored_vertex_count"],
            "landmark_vertex_counts": report["landmark_vertex_counts"],
            "independent_bvh": {
                "nonadjacent_intersecting_triangle_pair_count": independent_bvh[
                    "nonadjacent_intersecting_triangle_pair_count"
                ],
                "nonadjacent_intersecting_source_face_pair_count": independent_bvh[
                    "nonadjacent_intersecting_source_face_pair_count"
                ],
                "exact_genuine_nonadjacent_triangle_pair_count": independent_bvh[
                    "exact_genuine_nonadjacent_triangle_pair_count"
                ],
                "exact_genuine_nonadjacent_source_face_pair_count": independent_bvh[
                    "exact_genuine_nonadjacent_source_face_pair_count"
                ],
            },
            "authored_nonplanar_faces_triangulated": report[
                "authored_nonplanar_faces_triangulated"
            ],
            "object_count": len(bpy.data.objects),
            "render_performed": report["render_performed"],
            "export_performed": report["export_performed"],
            "runtime_activation_allowed": report["runtime_activation_allowed"],
        },
        sort_keys=True,
    )
)
