"""Read-only/in-memory localization of MakeHuman female overlap candidates.

The script prints a source/result JSON comparison to stdout.  It does not save,
render, export, activate, assign, clothe, publish, or write an evidence file.
"""

from __future__ import annotations

from collections import Counter
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
from tools.blender_audit_rapid_body_candidate import self_intersection_audit
from tools.blender_build_makehuman_adult_female_foundation_inactive import (
    _apply_target,
    _attach_normalized_default_weights,
    _compact_and_scale,
    _foundation_source_bindings,
    _new_body,
    _parse_body_group,
)
from tools.blender_exact_mesh_intersections import (
    exact_nonadjacent_intersection_report,
)
from tools.blender_repair_bounded_self_intersections import (
    repair_bounded_self_intersections,
)


def exact_report(obj: bpy.types.Object) -> dict[str, object]:
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        return exact_nonadjacent_intersection_report(bm)
    finally:
        bm.free()


def summary(report: dict[str, object]) -> dict[str, object]:
    pairs = report["pairs"]
    return {
        "bvh_nonadjacent_candidate_pair_count": report[
            "bvh_nonadjacent_candidate_pair_count"
        ],
        "exact_genuine_penetration_pair_count": report[
            "exact_genuine_penetration_pair_count"
        ],
        "touch_or_coplanar_false_positive_pair_count": report[
            "touch_or_coplanar_false_positive_pair_count"
        ],
        "bvh_aabb_false_positive_pair_count": report[
            "bvh_aabb_false_positive_pair_count"
        ],
        "body_regions": dict(
            sorted(Counter(pair["body_region"] for pair in pairs).items())
        ),
        "overlap_characters": dict(
            sorted(
                Counter(pair["overlap_character"] for pair in pairs).items()
            )
        ),
    }


def independent_summary(obj: bpy.types.Object) -> dict[str, object]:
    report = self_intersection_audit(obj)
    return {
        "raw_triangle_pair_count": report[
            "nonadjacent_intersecting_triangle_pair_count"
        ],
        "raw_source_face_pair_count": report[
            "nonadjacent_intersecting_source_face_pair_count"
        ],
        "exact_genuine_triangle_pair_count": report[
            "exact_genuine_nonadjacent_triangle_pair_count"
        ],
        "exact_genuine_source_face_pair_count": report[
            "exact_genuine_nonadjacent_source_face_pair_count"
        ],
        "exact_touch_or_numerical_triangle_pair_count": report[
            "exact_touch_or_numerical_triangle_pair_count"
        ],
        "exact_bvh_aabb_false_positive_triangle_pair_count": report[
            "exact_bvh_aabb_false_positive_triangle_pair_count"
        ],
        "exact_classification_counts": report["exact_classification_counts"],
        "exact_genuine_records": [
            record
            for record in report["exact_first_triangle_pair_records"]
            if record["genuine_penetration"] is True
        ],
    }


for existing in list(bpy.data.objects):
    bpy.data.objects.remove(existing, do_unlink=True)

profile = json.loads(
    (
        PROJECT_ROOT
        / "Avatar/avatar_builder/tooling/"
        "makehuman_adult_female_foundation_inactive_authoring_v1.json"
    ).read_text(encoding="utf-8")
)
base_path, target_bindings, _entry = _foundation_source_bindings()
vertices, faces = _parse_body_group(base_path)
for target_path, target_weight in target_bindings:
    _apply_target(vertices, target_path, target_weight)
compact, compact_faces, old_to_new, transform = _compact_and_scale(
    vertices,
    faces,
    float(profile["target_height_m"]),
)
body = _new_body(profile["candidate_id"], compact, compact_faces)
_attach_normalized_default_weights(body, old_to_new)

source = exact_report(body)
source_independent = independent_summary(body)
cleanup = repair_bounded_self_intersections(body)
cleaned_source = exact_report(body)
cleaned_source_independent = independent_summary(body)
authoring = author_continuous_adult_female_surface(
    body,
    frame=frame_from_mapping(profile["frame"]),
    parameters=parameters_from_mapping(profile["parameters"]),
    project_root=PROJECT_ROOT,
)
result = exact_report(body)
result_independent = independent_summary(body)

diagnostic = {
    "schema_version": 1,
    "diagnostic": "makehuman_adult_female_source_and_authored_exact_intersections_v1",
    "status": "IN_MEMORY_DIAGNOSTIC_ONLY",
    "foundation_id": profile["foundation_id"],
    "transform": transform,
    "source": source,
    "source_summary": summary(source),
    "source_independent": source_independent,
    "cleanup": cleanup,
    "cleaned_source": cleaned_source,
    "cleaned_source_summary": summary(cleaned_source),
    "cleaned_source_independent": cleaned_source_independent,
    "authored_result": result,
    "authored_result_summary": summary(result),
    "authored_result_independent": result_independent,
    "authoring_guard": {
        "inherited_global_nonadjacent_self_intersection_pairs": authoring[
            "inherited_global_nonadjacent_self_intersection_pairs"
        ],
        "result_global_nonadjacent_self_intersection_pairs": authoring[
            "result_global_nonadjacent_self_intersection_pairs"
        ],
        "authored_region_nonadjacent_self_intersection_pairs": authoring[
            "authored_region_nonadjacent_self_intersection_pairs"
        ],
    },
    "object_count": len(bpy.data.objects),
    "blend_saved": False,
    "render_performed": False,
    "export_performed": False,
    "runtime_mutation_performed": False,
    "runtime_activation_allowed": False,
}
assert len(bpy.data.objects) == 1
assert diagnostic["blend_saved"] is False
assert diagnostic["render_performed"] is False
assert diagnostic["export_performed"] is False
assert diagnostic["runtime_activation_allowed"] is False
print("MAKEHUMAN_EXACT_INTERSECTION_DIAGNOSTIC " + json.dumps(diagnostic, sort_keys=True))
assert cleaned_source["exact_genuine_penetration_pair_count"] == 0
assert result["exact_genuine_penetration_pair_count"] == 0
assert cleaned_source_independent["exact_genuine_source_face_pair_count"] == 0
assert result_independent["exact_genuine_source_face_pair_count"] == 0
assert cleaned_source_independent["raw_source_face_pair_count"] == 0
assert result_independent["raw_source_face_pair_count"] == 0
assert cleanup["weight_digest_preserved"] is True
assert cleanup["topology_changed"] is False
