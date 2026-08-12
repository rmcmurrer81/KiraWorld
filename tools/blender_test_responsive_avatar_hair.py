"""In-memory responsive-hair smoke; saves, renders, and exports nothing."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import bpy
from mathutils import Matrix, Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.blender_author_responsive_avatar_hair import (
    RESPONSE_SHAPE_KEYS,
    VISUAL_QUALITY_VERSION,
    author_responsive_wavy_black_hair,
    build_dynamic_hair,
)


FOUNDATION = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "workspaces"
    / "inactive_adult_female_foundations"
    / "generic_makehuman_adult_female_foundation_inactive_v1_20260801"
    / "generic_makehuman_adult_female_foundation_inactive_v1_20260801.blend"
)
FOUNDATION_SHA256 = (
    "3911419c44681d25f33892122e61206f1f4651bb78b3e403e377d1ed099cde2f"
)
PROFILE = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "style_profiles"
    / "natural_athletic_warm_asymmetric_waves_v1.json"
)
FULL_SCALE_PROBE = "--full-scale-probe" in sys.argv


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _make_transformed_head_armature(
    body: bpy.types.Object,
) -> bpy.types.Object:
    """Create a deliberately transformed rig with a head rest bone."""

    world_corners = [body.matrix_world @ Vector(corner) for corner in body.bound_box]
    low = Vector(
        tuple(min(point[axis] for point in world_corners) for axis in range(3))
    )
    high = Vector(
        tuple(max(point[axis] for point in world_corners) for axis in range(3))
    )
    center = (low + high) * 0.5
    height = high.z - low.z

    armature_data = bpy.data.armatures.new("Responsive_Hair_Transformed_Rig_Data")
    armature = bpy.data.objects.new(
        "Responsive_Hair_Transformed_Rig",
        armature_data,
    )
    bpy.context.collection.objects.link(armature)
    armature.location = (0.13, -0.09, 0.04)
    armature.rotation_euler = (0.07, -0.09, 0.13)
    armature.scale = (1.03, 0.97, 1.02)
    bpy.context.view_layer.update()

    for candidate in bpy.context.selected_objects:
        candidate.select_set(False)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    head = armature_data.edit_bones.new("head")
    world_to_armature = armature.matrix_world.inverted()
    head.head = world_to_armature @ Vector(
        (center.x, center.y, low.z + 0.83 * height)
    )
    head.tail = world_to_armature @ Vector(
        (center.x, center.y, low.z + 0.94 * height)
    )
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    return armature


def _evaluate_response_drivers(groom: bpy.types.Object) -> None:
    groom.update_tag()
    groom.data.shape_keys.update_tag()
    groom.data.materials[0].node_tree.update_tag()
    scene = bpy.context.scene
    scene.frame_set(scene.frame_current)
    bpy.context.view_layer.update()


def _assert_material_root_tip_ramps(groom: bpy.types.Object) -> None:
    nodes = groom.data.materials[0].node_tree.nodes
    dry = nodes["Dry_Root_To_Tip_Color"].color_ramp.elements
    wet = nodes["Wet_Root_To_Tip_Color"].color_ramp.elements
    assert len(dry) == 2
    assert len(wet) == 2
    assert abs(dry[0].position) <= 1.0e-9
    assert abs(dry[1].position - 1.0) <= 1.0e-9
    assert abs(wet[0].position) <= 1.0e-9
    assert abs(wet[1].position - 1.0) <= 1.0e-9
    for endpoint in range(2):
        for channel in range(3):
            assert abs(wet[endpoint].color[channel] - 0.86 * dry[endpoint].color[channel]) <= 2.0e-6
        assert abs(wet[endpoint].color[3] - 1.0) <= 1.0e-9
    assert max(
        dry[endpoint].color[channel]
        for endpoint in range(2)
        for channel in range(3)
    ) <= 0.012

    material = groom.data.materials[0]
    dry_shader = nodes["Dry_Hair"]
    wet_shader = nodes["Wet_Hair"]
    assert abs(float(dry_shader.inputs["Roughness"].default_value) - 0.46) <= 2.0e-6
    assert abs(float(wet_shader.inputs["Roughness"].default_value) - 0.26) <= 2.0e-6
    assert abs(float(dry_shader.inputs["Specular IOR Level"].default_value) - 0.20) <= 2.0e-6
    assert abs(float(wet_shader.inputs["Specular IOR Level"].default_value) - 0.34) <= 2.0e-6
    dry_anisotropy = dry_shader.inputs.get("Anisotropic IOR Level")
    if dry_anisotropy is None:
        dry_anisotropy = dry_shader.inputs["Anisotropic"]
    wet_anisotropy = wet_shader.inputs.get("Anisotropic IOR Level")
    if wet_anisotropy is None:
        wet_anisotropy = wet_shader.inputs["Anisotropic"]
    assert abs(float(dry_anisotropy.default_value) - 0.72) <= 2.0e-6
    assert abs(float(wet_anisotropy.default_value) - 0.80) <= 2.0e-6
    assert abs(float(dry_shader.inputs["Coat Weight"].default_value) - 0.04) <= 2.0e-6
    assert abs(float(wet_shader.inputs["Coat Weight"].default_value) - 0.14) <= 2.0e-6
    for channel in range(4):
        assert abs(material.diffuse_color[channel] - dry[0].color[channel]) <= 2.0e-6
    assert material["hair_material_profile"] == "deep_black_controlled_anisotropic_v3"
    assert material["glb_procedural_material_fidelity_proven"] is False


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    return ordered[low] * (high - position) + ordered[high] * (position - low)


def _basis_visual_metrics(
    groom: bpy.types.Object,
    part_x: float,
) -> dict[str, float]:
    basis = groom.data.shape_keys.key_blocks["Basis"]
    endpoints: list[float] = []
    heavy_lengths: list[float] = []
    light_lengths: list[float] = []
    total_turns: list[float] = []
    point_offset = 0
    for spline in groom.data.splines:
        coordinates = [
            basis.data[point_offset + index].co.copy()
            for index in range(len(spline.points))
        ]
        endpoints.append(float(coordinates[-1].z))
        segments = [
            coordinates[index] - coordinates[index - 1]
            for index in range(1, len(coordinates))
        ]
        path_length = sum(float(segment.length) for segment in segments)
        if float(coordinates[0].x) >= part_x:
            heavy_lengths.append(path_length)
        else:
            light_lengths.append(path_length)
        turns = 0.0
        for first, second in zip(segments, segments[1:]):
            if first.length > 1.0e-9 and second.length > 1.0e-9:
                turns += math.acos(
                    max(
                        -1.0,
                        min(1.0, float(first.normalized().dot(second.normalized()))),
                    )
                )
        total_turns.append(turns)
        point_offset += len(spline.points)
    root_radii = [float(spline.points[0].radius) for spline in groom.data.splines]
    tip_radii = [float(spline.points[-1].radius) for spline in groom.data.splines]
    return {
        "endpoint_p10_m": _percentile(endpoints, 0.10),
        "endpoint_p90_m": _percentile(endpoints, 0.90),
        "heavy_to_light_length_ratio": (
            (sum(heavy_lengths) / len(heavy_lengths))
            / (sum(light_lengths) / len(light_lengths))
        ),
        "median_total_turn_radians": _percentile(total_turns, 0.50),
        "minimum_root_radius": min(root_radii),
        "maximum_root_radius": max(root_radii),
        "minimum_tip_radius": min(tip_radii),
        "maximum_tip_radius": max(tip_radii),
        "thin_flyaway_root_fraction": sum(
            1 for radius in root_radii if radius < 0.65
        ) / len(root_radii),
    }


def _response_geometry_metrics(
    groom: bpy.types.Object,
    bounds: dict,
) -> dict[str, float]:
    blocks = groom.data.shape_keys.key_blocks
    labels = (
        "Basis",
        "hair_wind_left_dry",
        "hair_wind_right_dry",
        "hair_wet_neutral",
        "hair_wet_wind_left",
        "hair_wet_wind_right",
    )
    tips: dict[str, list[Vector]] = {label: [] for label in labels}
    groups: defaultdict[tuple[int, int], list[int]] = defaultdict(list)
    head_low = Vector(bounds["head_bounds_low_m"])
    head_high = Vector(bounds["head_bounds_high_m"])
    center = (head_low + head_high) * 0.5
    point_offset = 0
    for strand_index, spline in enumerate(groom.data.splines):
        tip_index = point_offset + len(spline.points) - 1
        for label in labels:
            tips[label].append(blocks[label].data[tip_index].co.copy())
        root = blocks["Basis"].data[point_offset].co
        angle = math.atan2(root.y - center.y, root.x - center.x)
        azimuth = max(0, min(23, int((angle + math.pi) / math.tau * 24.0)))
        elevation_fraction = (root.z - head_low.z) / max(head_high.z - head_low.z, 1.0e-8)
        elevation = max(0, min(3, int(elevation_fraction * 4.0)))
        groups[(azimuth, elevation)].append(strand_index)
        point_offset = tip_index + 1

    def mean_and_std(values: list[float]) -> tuple[float, float]:
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        return mean, math.sqrt(variance)

    right_delta = [
        right.x - basis.x
        for right, basis in zip(tips["hair_wind_right_dry"], tips["Basis"])
    ]
    left_delta = [
        left.x - basis.x
        for left, basis in zip(tips["hair_wind_left_dry"], tips["Basis"])
    ]
    wet_right_delta = [
        right.x - neutral.x
        for right, neutral in zip(
            tips["hair_wet_wind_right"],
            tips["hair_wet_neutral"],
        )
    ]
    right_mean, right_std = mean_and_std(right_delta)
    left_mean, left_std = mean_and_std(left_delta)
    wet_right_mean, wet_right_std = mean_and_std(wet_right_delta)

    dry_spread_total = 0.0
    wet_spread_total = 0.0
    spread_points = 0
    for indices in groups.values():
        if len(indices) < 2:
            continue
        dry_center = sum((tips["Basis"][index] for index in indices), Vector()) / len(indices)
        wet_center = sum(
            (tips["hair_wet_neutral"][index] for index in indices),
            Vector(),
        ) / len(indices)
        dry_spread_total += sum(
            float((tips["Basis"][index] - dry_center).length)
            for index in indices
        )
        wet_spread_total += sum(
            float((tips["hair_wet_neutral"][index] - wet_center).length)
            for index in indices
        )
        spread_points += len(indices)
    dry_width = max(point.x for point in tips["Basis"]) - min(
        point.x for point in tips["Basis"]
    )
    wet_width = max(point.x for point in tips["hair_wet_neutral"]) - min(
        point.x for point in tips["hair_wet_neutral"]
    )
    return {
        "dry_right_mean_tip_x_m": right_mean,
        "dry_right_tip_x_standard_deviation_m": right_std,
        "dry_left_mean_tip_x_m": left_mean,
        "dry_left_tip_x_standard_deviation_m": left_std,
        "wet_right_mean_tip_x_m": wet_right_mean,
        "wet_right_tip_x_standard_deviation_m": wet_right_std,
        "wet_to_dry_local_tip_spread_ratio": wet_spread_total / dry_spread_total,
        "wet_to_dry_global_tip_width_ratio": wet_width / dry_width,
        "localized_spread_sample_count": spread_points,
    }


def _prove_transformed_head_pose_follow(
    groom: bpy.types.Object,
    armature: bpy.types.Object,
) -> dict[str, float | bool]:
    """Prove the bound groom follows and exactly restores a posed head bone."""

    assert groom.parent == armature
    assert groom.parent_type == "BONE"
    assert groom.parent_bone == "head"
    basis_root = groom.data.shape_keys.key_blocks["Basis"].data[0].co.copy()
    bpy.context.view_layer.update()
    before = groom.matrix_world @ basis_root
    pose_bone = armature.pose.bones["head"]
    original_basis = pose_bone.matrix_basis.copy()
    try:
        pose_bone.matrix_basis = (
            Matrix.Rotation(math.radians(6.0), 4, "Z") @ original_basis
        )
        armature.update_tag()
        bpy.context.view_layer.update()
        posed = groom.matrix_world @ basis_root
        movement = float((posed - before).length)
        assert movement > 1.0e-4
    finally:
        pose_bone.matrix_basis = original_basis
        armature.update_tag()
        bpy.context.view_layer.update()
    restored = groom.matrix_world @ basis_root
    restore_error = float((restored - before).length)
    assert restore_error <= 2.0e-6
    return {
        "transformed_armature_used": True,
        "head_pose_follow_passed": True,
        "head_pose_root_movement_m": movement,
        "head_pose_restore_error_m": restore_error,
    }


assert FOUNDATION.is_file()
assert _sha256(FOUNDATION) == FOUNDATION_SHA256
bpy.ops.wm.open_mainfile(filepath=str(FOUNDATION), load_ui=False)
bodies = [
    obj
    for obj in bpy.data.objects
    if obj.type == "MESH" and obj.get("primary_surface") is True
]
assert len(bodies) == 1
profile = json.loads(PROFILE.read_text(encoding="utf-8"))
transformed_armature = _make_transformed_head_armature(bodies[0])
requested_strands = 3600 if FULL_SCALE_PROBE else 900
requested_controls = 13 if FULL_SCALE_PROBE else 10
authoring_started = time.perf_counter()
groom, report = author_responsive_wavy_black_hair(
    bodies[0],
    transformed_armature,
    profile["hair_profile"],
    name="Responsive_Hair_In_Memory_Smoke",
    strand_count=requested_strands,
    controls_per_strand=requested_controls,
)
authoring_seconds = time.perf_counter() - authoring_started

assert report["strand_count"] == requested_strands
assert report["schema_version"] == 3
assert report["visual_quality_version"] == VISUAL_QUALITY_VERSION
assert report["method"] == "weighted_scalp_adaptive_tube_clear_bilinear_deep_black_locks_v3"
assert report["curve_control_point_count"] > requested_strands * requested_controls
assert report["curve_control_point_count"] == sum(
    len(spline.points) for spline in groom.data.splines
)
assert report["root_pin_passed"] is True
assert report["root_pin_maximum_displacement_m"] <= 1.0e-10
assert report["scalp_cap_or_underlay_object_count"] == 0
assert report["runtime_world_driver_proven"] is False
assert report["render_performed"] is False
assert report["export_performed"] is False
assert report["runtime_activation_allowed"] is False
assert report["glb_static_geometry_export_performed"] is False
assert report["glb_material_driver_morph_fidelity_proven"] is False
assert groom.type == "CURVE"
assert groom["hair_visual_quality_version"] == VISUAL_QUALITY_VERSION
assert groom["explicit_render_strands"] is True
assert groom["implicit_particle_children"] is False
assert groom["glb_export_fidelity_proven"] is False
assert groom.data.bevel_resolution == 2
assert groom.data.use_fill_caps is True
assert list(groom.data.shape_keys.key_blocks.keys()) == ["Basis", *RESPONSE_SHAPE_KEYS]
for property_name in (
    "hair_wind_direction_minus1_1",
    "hair_wetness_0_1",
):
    assert property_name in groom

collision = report["collision_surface_proof"]
assert collision["closed_contiguous_outward_winding_proven"] is True
assert collision["connected_component_count"] == 1
assert collision["boundary_edge_count"] == 0
assert collision["nonmanifold_edge_count"] == 0
assert collision["winding_discontinuity_count"] == 0
assert collision["world_signed_volume_m3"] > collision["minimum_world_signed_volume_m3"]

bounds = report["bounds"]
assert bounds["scalp_area_allowed_range_m2"][0] <= bounds["scalp_area_m2"]
assert bounds["scalp_area_m2"] <= bounds["scalp_area_allowed_range_m2"][1]
assert bounds["part_line_triangle_exclusion_count"] > 0
assert bounds["face_jaw_neck_upper_back_roots_blocked"] is True
assert bounds["ear_region_roots_blocked"] is True

dry_locks = report["dry_lock_proof"]
assert dry_locks["localized_dry_locks_authored"] is True
assert dry_locks["follicles_moved"] is False
assert dry_locks["dry_lock_multi_strand_group_count"] > 0
assert dry_locks["procedural_lock_guide_count"] == dry_locks["dry_lock_group_count"]
assert dry_locks["explicit_render_child_equivalent_strand_count"] == requested_strands
assert 0.015 <= dry_locks["flyaway_fraction"] <= 0.04

visual = report["visual_geometry_proof"]
assert visual["visual_quality_version"] == VISUAL_QUALITY_VERSION
assert visual["explicit_render_strand_count"] == requested_strands
assert visual["implicit_particle_child_count"] == 0
assert visual["render_child_solution"] == (
    "procedural_lock_guides_with_every_render_member_as_explicit_curve_geometry"
)
assert visual["maximum_bevel_diameter_pixels_at_1000px_body_height"] >= 0.49
assert visual["endpoint_height_p10_to_p90_spread_m"] >= bounds["body_height_m"] * 0.06
assert visual["heavy_to_light_mean_path_length_ratio"] >= 1.08
assert visual["flyaway_to_bulk_mean_path_length_ratio"] < 0.90
assert visual["median_total_discrete_turn_radians"] >= 1.20
assert visual["curved_strand_fraction"] >= 0.90
assert visual["strand_fraction_with_two_or_more_lateral_wave_sign_changes"] >= 0.20
assert visual["multi_frequency_curl_authored"] is True
assert visual["deep_side_part_asymmetry_authored"] is True
assert visual["visual_geometry_quality_gate_passed"] is True
assert visual["glb_export_performed"] is False

basis_visual = _basis_visual_metrics(groom, bounds["part_line_center_x_m"])
assert abs(
    basis_visual["endpoint_p10_m"] - visual["endpoint_height_p10_m"]
) <= 2.0e-6
assert abs(
    basis_visual["endpoint_p90_m"] - visual["endpoint_height_p90_m"]
) <= 2.0e-6
assert basis_visual["heavy_to_light_length_ratio"] >= 1.08
assert basis_visual["median_total_turn_radians"] >= 1.20
assert 0.45 <= basis_visual["minimum_root_radius"]
assert basis_visual["maximum_root_radius"] <= 1.0
assert 0.20 <= basis_visual["minimum_tip_radius"]
assert basis_visual["maximum_tip_radius"] <= 0.41
assert 0.015 <= basis_visual["thin_flyaway_root_fraction"] <= 0.04

response_style = report["response_style_proof"]
assert response_style["localized_wet_clumping_authored"] is True
assert response_style["length_and_mass_scaled_wind_authored"] is True
assert response_style["wind_per_strand_variation_authored"] is True
assert response_style["wet_local_multi_strand_group_count"] > 0
assert 0.48 <= response_style["wet_clump_strength_minimum"]
assert response_style["wet_clump_strength_maximum"] <= 0.72

adaptive = report["adaptive_tube_clearance_proof"]
assert adaptive["all_state_sampled_tube_clearance_passed"] is True
assert adaptive["all_bilinear_grid_tube_clearance_passed"] is True
assert adaptive["actual_basis_control_point_count"] == report["curve_control_point_count"]
assert adaptive["validation_sample_count"] > 0
assert adaptive["bilinear_validation_sample_count"] > 0
assert adaptive["minimum_sampled_clearance_margin_m"] >= -adaptive["clearance_tolerance_m"]
assert adaptive["bilinear_minimum_sampled_clearance_margin_m"] >= -adaptive["clearance_tolerance_m"]
assert {
    (entry["wind"], entry["wetness"])
    for entry in adaptive["bilinear_grid"]
} == {
    (wind, wetness)
    for wind in (-1.0, -0.5, 0.0, 0.5, 1.0)
    for wetness in (0.0, 0.5, 1.0)
}

key_blocks = groom.data.shape_keys.key_blocks
point_offset = 0
for spline in groom.data.splines:
    basis_root = key_blocks["Basis"].data[point_offset].co
    for response_name in RESPONSE_SHAPE_KEYS:
        assert (
            key_blocks[response_name].data[point_offset].co - basis_root
        ).length <= 1.0e-10
    point_offset += len(spline.points)
assert point_offset == report["curve_control_point_count"]

driver_proof = report["driver_evaluation_proof"]
assert driver_proof["neutral_reset_passed"] is True
bilinear_left = driver_proof["tested_states"]["bilinear_left"]["shape_weights"]
assert abs(bilinear_left["hair_wind_left_dry"] - 0.16) <= 2.0e-6
assert abs(bilinear_left["hair_wet_neutral"] - 0.36) <= 2.0e-6
assert abs(bilinear_left["hair_wet_wind_left"] - 0.24) <= 2.0e-6
assert abs(sum(bilinear_left.values()) - 0.76) <= 2.0e-6

groom["hair_wind_direction_minus1_1"] = -0.5
groom["hair_wetness_0_1"] = 0.5
_evaluate_response_drivers(groom)
expected_half_left = {
    "hair_wind_left_dry": 0.25,
    "hair_wind_right_dry": 0.0,
    "hair_wet_neutral": 0.25,
    "hair_wet_wind_left": 0.25,
    "hair_wet_wind_right": 0.0,
}
for response_name, expected in expected_half_left.items():
    assert abs(float(key_blocks[response_name].value) - expected) <= 2.0e-6
wetness_node = groom.data.materials[0].node_tree.nodes["Hair_Wetness_0_1"]
assert abs(float(wetness_node.outputs[0].default_value) - 0.5) <= 2.0e-6
groom["hair_wind_direction_minus1_1"] = 0.0
groom["hair_wetness_0_1"] = 0.0
_evaluate_response_drivers(groom)

_assert_material_root_tip_ramps(groom)
material_proof = report["material_quality_proof"]
assert material_proof["deep_black_input_gate_passed"] is True
assert material_proof["controlled_highlight_gate_passed"] is True
assert material_proof["maximum_dry_linear_color_channel"] <= 0.012
assert abs(material_proof["dry_roughness"] - 0.46) <= 2.0e-6
assert abs(material_proof["wet_roughness"] - 0.26) <= 2.0e-6
assert abs(material_proof["dry_specular_ior_level"] - 0.20) <= 2.0e-6
assert abs(material_proof["wet_specular_ior_level"] - 0.34) <= 2.0e-6
assert abs(material_proof["dry_anisotropic_ior_level"] - 0.72) <= 2.0e-6
assert abs(material_proof["wet_anisotropic_ior_level"] - 0.80) <= 2.0e-6
assert material_proof["glb_procedural_material_fidelity_proven"] is False

response_geometry = _response_geometry_metrics(groom, bounds)
assert response_geometry["dry_right_mean_tip_x_m"] > 0.035
assert response_geometry["dry_left_mean_tip_x_m"] < -0.035
assert response_geometry["dry_right_tip_x_standard_deviation_m"] > 0.008
assert response_geometry["dry_left_tip_x_standard_deviation_m"] > 0.008
assert 0.0 < response_geometry["wet_right_mean_tip_x_m"]
assert response_geometry["wet_right_mean_tip_x_m"] < (
    response_geometry["dry_right_mean_tip_x_m"] * 0.80
)
assert response_geometry["wet_right_tip_x_standard_deviation_m"] > 0.004
assert response_geometry["localized_spread_sample_count"] > 0
assert response_geometry["wet_to_dry_local_tip_spread_ratio"] < 0.75
assert response_geometry["wet_to_dry_global_tip_width_ratio"] > 0.50
parent_binding = report["head_parent_binding"]
assert parent_binding["head_bone_parented"] is True
assert parent_binding["bind_world_transform_preserved"] is True
assert parent_binding["bind_world_maximum_displacement_m"] <= parent_binding["bind_world_tolerance_m"]
pose_evidence = _prove_transformed_head_pose_follow(groom, transformed_armature)

evaluated_groom = groom.evaluated_get(bpy.context.evaluated_depsgraph_get())
evaluated_mesh = bpy.data.meshes.new_from_object(evaluated_groom)
try:
    evaluated_mesh.calc_loop_triangles()
    evaluated_geometry = {
        "vertices": len(evaluated_mesh.vertices),
        "edges": len(evaluated_mesh.edges),
        "polygons": len(evaluated_mesh.polygons),
        "loop_triangles": len(evaluated_mesh.loop_triangles),
        "material_slots": len(evaluated_mesh.materials),
    }
    assert evaluated_geometry["vertices"] > report["curve_control_point_count"] * 6
    assert evaluated_geometry["polygons"] > report["curve_control_point_count"] * 6
    assert evaluated_geometry["loop_triangles"] > evaluated_geometry["polygons"]
    assert evaluated_geometry["material_slots"] == 1
finally:
    bpy.data.meshes.remove(evaluated_mesh)
full_scale_evaluated_geometry = evaluated_geometry if FULL_SCALE_PROBE else None

# Exercise the exact hash-bound provider contract on a second in-memory groom.
provider_runtime_scope = "NOT_RERUN_IN_FULL_SCALE_PERFORMANCE_PROBE"
if not FULL_SCALE_PROBE:
    provider_result = build_dynamic_hair(
        body=bodies[0],
        armature=None,
        context={
            "candidate_id": "responsive_hair_provider_smoke",
            "hair_profile": profile["hair_profile"],
            "strand_count": 800,
            "controls_per_strand": 8,
        },
    )
    assert len(provider_result["objects"]) == 1
    provider_evidence = provider_result["evidence"]
    assert provider_evidence["representation"] == "validated_dynamic_equivalent"
    assert provider_evidence["source_geometry_copied"] is False
    assert provider_evidence["private_blend_response_states_proven"] is True
    assert provider_evidence["proof_scope"] == "PRIVATE_BLEND_AUTHORED_STATES_NOT_WORLD_RUNTIME"
    assert provider_evidence["runtime_hair_complete"] is False
    assert provider_evidence["wind_runtime_proof_complete"] is False
    assert provider_evidence["wet_runtime_proof_complete"] is False
    assert provider_evidence["visual_quality_version"] == VISUAL_QUALITY_VERSION
    provider_visual = provider_evidence["visual_geometry_proof"]
    assert provider_visual["explicit_render_strand_count"] == 800
    assert provider_visual["visual_geometry_quality_gate_passed"] is True
    assert provider_visual["endpoint_height_p10_to_p90_spread_m"] >= (
        provider_evidence["bounds"]["body_height_m"] * 0.05
    )
    assert provider_visual["maximum_bevel_diameter_pixels_at_1000px_body_height"] >= 0.49
    assert provider_evidence["glb_material_driver_morph_fidelity_proven"] is False
    provider_runtime_scope = provider_evidence["proof_scope"]

print(
    "RESPONSIVE_AVATAR_HAIR_SMOKE_PASS "
    + json.dumps(
        {
            "hair_report": report,
            "transformed_armature_pose_probe": pose_evidence,
            "authoring_seconds": authoring_seconds,
            "evaluated_geometry": evaluated_geometry,
            "full_scale_evaluated_geometry": full_scale_evaluated_geometry,
            "basis_visual_metrics": basis_visual,
            "response_geometry_metrics": response_geometry,
            "full_scale_probe": FULL_SCALE_PROBE,
            "provider_runtime_scope": provider_runtime_scope,
        },
        sort_keys=True,
    )
)
