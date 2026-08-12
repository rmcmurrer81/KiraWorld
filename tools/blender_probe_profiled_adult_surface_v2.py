"""Real-source in-memory probe for the profiled v1 -> structured v2 surface.

This performs the same exact source/style/rig/surface steps as the candidate
builder, then exits without eyes, nails, hair, render, save, export, output
directory creation, assignment, or activation.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_adult_female_surface_authoring import (
    frame_from_mapping,
    parameters_from_mapping,
)
from Core.avatar_profiled_adult_candidate_contract import (
    evaluate_profiled_candidate_preflight,
    load_validated_profiled_candidate_builder_config,
    scaled_adult_surface_settings,
)
from tools.blender_author_adult_female_external_surface import (
    author_continuous_adult_female_surface,
)
from tools.blender_author_adult_female_external_surface_v2 import (
    refine_existing_continuous_adult_female_surface_v2,
)
from tools.blender_profiled_adult_candidate_components import (
    build_body_object,
    build_official_rig_and_normalized_weights,
    build_warm_skin_material,
    prepare_profiled_body_source,
)
from tools.blender_repair_bounded_self_intersections import (
    repair_bounded_self_intersections,
)


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    assert isinstance(payload, dict)
    return payload


probe_output = Path(
    "Avatar/private_owner_review/"
    "kira_profiled_adult_candidate_surface_probe_never_written_20260801"
)
assert not (PROJECT_ROOT / probe_output).exists()
preflight = evaluate_profiled_candidate_preflight(PROJECT_ROOT, probe_output)
assert preflight["ready"] is True, preflight["blockers"]
config, _config_report = load_validated_profiled_candidate_builder_config(PROJECT_ROOT)
profile = _read_json(PROJECT_ROOT / config["style_profile"]["path"])
target_height_m = float(profile["dimensions"]["target_height_m"])

for existing in list(bpy.data.objects):
    bpy.data.objects.remove(existing, do_unlink=True)

base_path = PROJECT_ROOT / config["makehuman_source_set"]["base_body"]["path"]
source = prepare_profiled_body_source(
    base_path=base_path,
    female_macros=config["makehuman_source_set"]["female_macros"],
    resolved_style_targets=preflight["style_profile"]["resolved_targets"],
    project_root=PROJECT_ROOT,
    target_height_m=target_height_m,
)
skin_material, _skin_report = build_warm_skin_material(profile)
body = build_body_object(source, "kira_profiled_surface_v2_probe", skin_material)
armature, _rig_report = build_official_rig_and_normalized_weights(
    body=body,
    source=source,
    skeleton_path=PROJECT_ROOT / config["official_rig"]["skeleton"]["path"],
    weights_path=PROJECT_ROOT / config["official_rig"]["weights"]["path"],
    candidate_id="kira_profiled_surface_v2_probe",
    maximum_influences=4,
)
cleanup = repair_bounded_self_intersections(body)
assert cleanup["after"]["exact_genuine_penetration_pair_count"] == 0
scaled_frame, scaled_parameters = scaled_adult_surface_settings(
    config["adult_surface_authoring"], target_height_m
)
frame = frame_from_mapping(scaled_frame)
parameters = parameters_from_mapping(scaled_parameters)
base_report = author_continuous_adult_female_surface(
    body,
    frame=frame,
    parameters=parameters,
    project_root=PROJECT_ROOT,
)
detail_config = config["adult_surface_authoring"]["structured_detail_refinement"]
target_relief_scale_m = float(detail_config["baseline_relief_scale_m"]) * (
    target_height_m / float(config["adult_surface_authoring"]["baseline_height_m"])
)
detail_ratio = target_height_m / float(
    config["adult_surface_authoring"]["baseline_height_m"]
)
posterior_frame_payload = dict(detail_config["posterior_frame"])
posterior_frame_payload["origin"] = [
    float(value) * detail_ratio for value in posterior_frame_payload["origin"]
]
for metric_name in ("half_width_m", "half_length_m", "max_surface_offset_m"):
    posterior_frame_payload[metric_name] = (
        float(posterior_frame_payload[metric_name]) * detail_ratio
    )
posterior_frame = frame_from_mapping(posterior_frame_payload)
detail_report = refine_existing_continuous_adult_female_surface_v2(
    body,
    frame=frame,
    base_parameters=parameters,
    posterior_frame=posterior_frame,
    target_relief_scale_m=target_relief_scale_m,
    target_taper_power=int(detail_config["boundary_taper_power"]),
)

frame_origin = Vector(frame.origin)
frame_lateral = Vector(frame.lateral_axis)
frame_longitudinal = Vector(frame.longitudinal_axis)
frame_outward = Vector(frame.outward_axis)
all_surface_nearest = {}
from Core.avatar_adult_female_surface_authoring_v2 import FEATURE_SAMPLE_POINTS
for sample_name, sample_uv in FEATURE_SAMPLE_POINTS.items():
    best = None
    for vertex in body.data.vertices:
        delta = vertex.co - frame_origin
        u = delta.dot(frame_lateral) / frame.half_width_m
        v = delta.dot(frame_longitudinal) / frame.half_length_m
        depth = delta.dot(frame_outward)
        distance_squared = (u - sample_uv[0]) ** 2 + (v - sample_uv[1]) ** 2
        if best is None or distance_squared < best[0]:
            best = (
                distance_squared,
                int(vertex.index),
                float(u),
                float(v),
                float(depth),
                float(vertex.normal.dot(frame_outward)),
                [float(value) for value in vertex.co],
            )
    assert best is not None
    all_surface_nearest[sample_name] = {
        "normalized_distance": best[0] ** 0.5,
        "vertex_index": best[1],
        "normalized_uv": [best[2], best[3]],
        "depth_m": best[4],
        "normal_alignment": best[5],
        "object_local_position": best[6],
    }
central_pelvis_bins = {}
for lower_z in (0.62, 0.64, 0.66, 0.68, 0.70, 0.72, 0.74, 0.76, 0.78, 0.80):
    rows = [
        vertex
        for vertex in body.data.vertices
        if abs(float(vertex.co.x)) <= 0.025
        and lower_z <= float(vertex.co.z) < lower_z + 0.02
    ]
    if not rows:
        continue
    front = min(rows, key=lambda vertex: float(vertex.co.y))
    rear = max(rows, key=lambda vertex: float(vertex.co.y))
    central_pelvis_bins[f"{lower_z:.2f}_{lower_z + 0.02:.2f}"] = {
        "vertex_count": len(rows),
        "front": {
            "vertex_index": int(front.index),
            "position": [float(value) for value in front.co],
            "normal": [float(value) for value in front.normal],
        },
        "rear": {
            "vertex_index": int(rear.index),
            "position": [float(value) for value in rear.co],
            "normal": [float(value) for value in rear.normal],
        },
    }

assert base_report["global_topology_ready_for_qualification"] is True
assert detail_report["new_global_nonadjacent_self_intersection_pairs"] == 0
assert detail_report["topology_changed"] is False
assert detail_report["rig_weights_changed"] is False
assert detail_report["runtime_activation_allowed"] is False
assert bpy.data.filepath == ""
assert not (PROJECT_ROOT / probe_output).exists()

print(
    "PROFILED_ADULT_SURFACE_V2_REAL_SOURCE_PROBE_PASS "
    + json.dumps(
        {
            "base_method_id": base_report["method_id"],
            "detail_method_id": detail_report["detail_method_id"],
            "target_relief_scale_m": detail_report["target_relief_scale_m"],
            "theoretical_feature_sample_displacements_m": detail_report[
                "theoretical_feature_sample_displacements_m"
            ],
            "nearest_authored_feature_samples": detail_report[
                "nearest_authored_feature_samples"
            ],
            "posterior_nearest_authored_feature_samples": detail_report[
                "posterior_nearest_authored_feature_samples"
            ],
            "all_surface_nearest_feature_samples": all_surface_nearest,
            "central_pelvis_bins": central_pelvis_bins,
            "source_topology": detail_report["source_topology"],
            "result_topology": detail_report["result_topology"],
            "new_global_nonadjacent_self_intersection_pairs": detail_report[
                "new_global_nonadjacent_self_intersection_pairs"
            ],
            "blend_saved": False,
            "render_performed": False,
            "export_performed": False,
            "output_directory_created": False,
            "runtime_activation_allowed": False,
        },
        sort_keys=True,
    )
)
