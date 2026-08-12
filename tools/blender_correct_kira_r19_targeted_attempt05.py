#!/usr/bin/env python3
"""Bounded material/action correction derived from sealed Kira R19 attempt 04.

This worker does not edit topology, body/face shape, rig structure or weights,
or any nail data.  It replaces only the failed active iris colorizer, layers a
bounded surface-response adjustment onto the six accepted packed skin graphs,
and evaluates exactly two predeclared action candidates for each of four
movement defects.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import traceback
from typing import Any, Sequence

import bpy
from mathutils import Vector


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_assemble_kira_r19_bald_owner_review as assembly  # noqa: E402
import blender_probe_blackproject_r19_seated_contact as seated_worker  # noqa: E402


BODY_NAME = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"
RIG_NAME = "Kira_R19_BlackProject_Native_188_Rig"
DEFAULT_CONFIG = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "KIRA_R19_TARGETED_CORRECTION_CONFIG_ATTEMPT_05.json"
)
POSE_FRAME = 30
FINGERTIP_BONES = {
    "left": ["lThumb3_049", "lIndex3_053", "lMid3_057", "lRing3_061", "lPinky3_065"],
    "right": ["rThumb3_074", "rIndex3_078", "rMid3_082", "rRing3_01", "rPinky3_088"],
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--preflight-only", action="store_true")
    return parser.parse_args(argv)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def canonical(name: str) -> str:
    stem, dot, suffix = name.rpartition(".")
    return stem if dot and suffix.isdigit() else name


def float_rows(matrix) -> list[list[float]]:
    return [[float(value) for value in row] for row in matrix]


def weight_signature(obj: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    group_names = {group.index: group.name for group in obj.vertex_groups}
    for vertex in obj.data.vertices:
        digest.update(f"v:{int(vertex.index)};".encode("ascii"))
        assignments = sorted(
            (group_names[int(item.group)], float(item.weight))
            for item in vertex.groups
            if float(item.weight) > 0.0
        )
        for name, weight in assignments:
            digest.update(f"{name}:{weight:.12g};".encode("utf-8"))
    return digest.hexdigest()


def modifier_signature(obj: bpy.types.Object) -> list[dict[str, Any]]:
    return [
        {
            "name": modifier.name,
            "type": modifier.type,
            "object": modifier.object.name
            if modifier.type == "ARMATURE" and modifier.object is not None
            else None,
            "use_vertex_groups": bool(modifier.use_vertex_groups)
            if modifier.type == "ARMATURE"
            else None,
        }
        for modifier in obj.modifiers
    ]


def mesh_immutable_state(obj: bpy.types.Object) -> dict[str, Any]:
    return {
        "object": obj.name,
        "mesh": canonical(obj.data.name),
        "geometry_uv_sha256": assembly.mesh_geometry_uv_signature(obj),
        "positive_weight_assignment_sha256": weight_signature(obj),
        "matrix_world": float_rows(obj.matrix_world),
        "modifiers": modifier_signature(obj),
        "vertex_count": len(obj.data.vertices),
        "polygon_count": len(obj.data.polygons),
    }


def rig_immutable_signature(rig: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    for bone in sorted(rig.data.bones, key=lambda item: item.name):
        digest.update(
            (
                f"{bone.name}|{bone.parent.name if bone.parent else ''}|"
                f"{float(bone.head_local.x):.12g},{float(bone.head_local.y):.12g},{float(bone.head_local.z):.12g}|"
                f"{float(bone.tail_local.x):.12g},{float(bone.tail_local.y):.12g},{float(bone.tail_local.z):.12g}|"
                f"{float(bone.roll):.12g}|{int(bool(bone.use_deform))};"
            ).encode("utf-8")
        )
    return digest.hexdigest()


def validate_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = []
    for entry in manifest["files_excluding_this_manifest"]:
        path = PROJECT_ROOT / str(entry["path"])
        if not path.is_file():
            failures.append({"path": str(entry["path"]), "cause": "missing"})
            continue
        actual = sha256_file(path)
        if actual != str(entry["sha256"]).lower():
            failures.append(
                {"path": str(entry["path"]), "expected": entry["sha256"], "actual": actual}
            )
    if failures:
        raise RuntimeError(f"sealed attempt-04 manifest mismatch: {failures}")
    return {
        "entry_count": len(manifest["files_excluding_this_manifest"]),
        "all_entries_rehashed": True,
        "all_entries_match": True,
    }


def load_config(config_path: Path) -> tuple[dict[str, Any], dict[str, Path], dict[str, Any]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    paths = {
        "source_blend": PROJECT_ROOT / str(config["source_blend"]),
        "source_evidence": PROJECT_ROOT / str(config["source_evidence"]),
        "source_manifest": PROJECT_ROOT / str(config["source_manifest"]),
        "source_visual_review": PROJECT_ROOT / str(config["source_visual_review"]),
    }
    expected = {
        "source_blend": str(config["source_blend_sha256"]),
        "source_evidence": str(config["source_evidence_sha256"]),
        "source_manifest": str(config["source_manifest_sha256"]),
        "source_visual_review": str(config["source_visual_review_sha256"]),
    }
    hashes = {}
    for key, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        hashes[key] = sha256_file(path)
        if hashes[key] != expected[key].lower():
            raise RuntimeError(f"protected input hash mismatch for {key}")
    candidate_groups = config.get("pose_candidates", {})
    expected_groups = {
        "supported_seated",
        "supine_lying",
        "eating_or_table_reach",
        "hands_fingers",
    }
    if set(candidate_groups) != expected_groups:
        raise RuntimeError(f"unexpected movement candidate groups: {sorted(candidate_groups)}")
    ids = []
    for group in sorted(expected_groups):
        candidates = candidate_groups[group]
        if len(candidates) != 2:
            raise RuntimeError(f"{group} must contain exactly two predeclared candidates")
        ids.extend(str(candidate["id"]) for candidate in candidates)
    if len(ids) != len(set(ids)):
        raise RuntimeError("predeclared movement candidate IDs must be unique")
    manifest_gate = validate_manifest(paths["source_manifest"])
    return config, paths, {
        "config": project_relative(config_path),
        "config_sha256": sha256_file(config_path),
        "protected_input_hashes": hashes,
        "sealed_source_manifest": manifest_gate,
        "candidate_group_count": 4,
        "candidate_count": 8,
        "exactly_two_candidates_per_defect": True,
        "open_search_or_framework_used": False,
    }


def candidate_meshes() -> list[bpy.types.Object]:
    return sorted(
        [
            obj
            for obj in bpy.data.objects
            if obj.type == "MESH" and not bool(obj.get("review_context_prop_only"))
        ],
        key=lambda obj: obj.name,
    )


def find_components() -> tuple[bpy.types.Object, bpy.types.Object, list[bpy.types.Object], bpy.types.Object]:
    body = bpy.data.objects.get(BODY_NAME)
    rig = bpy.data.objects.get(RIG_NAME)
    if body is None or body.type != "MESH":
        raise RuntimeError("sealed attempt-04 body missing")
    if rig is None or rig.type != "ARMATURE" or len(rig.data.bones) != 188:
        raise RuntimeError("sealed attempt-04 native 188-joint rig missing")
    nails = sorted(
        [obj for obj in bpy.data.objects if obj.type == "MESH" and bool(obj.get("nail_component"))],
        key=lambda obj: obj.name,
    )
    if len(nails) != 20:
        raise RuntimeError(f"expected exactly 20 retained nails, found {len(nails)}")
    irises = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH" and canonical(obj.data.name) == "Ariel_Mesh_Irises_0"
    ]
    if len(irises) != 1:
        raise RuntimeError(f"expected exactly one iris object, found {len(irises)}")
    return body, rig, nails, irises[0]


def active_principled(material: bpy.types.Material) -> bpy.types.Node:
    nodes = [
        node
        for node in material.node_tree.nodes
        if node.bl_idname == "ShaderNodeBsdfPrincipled"
    ]
    if len(nodes) != 1:
        raise RuntimeError(f"{material.name} must retain one Principled node")
    return nodes[0]


def strengthen_iris_material(iris: bpy.types.Object, spec: dict[str, Any]) -> dict[str, Any]:
    geometry_before = assembly.mesh_geometry_uv_signature(iris)
    weights_before = weight_signature(iris)
    modifiers_before = modifier_signature(iris)
    source_material = iris.material_slots[0].material
    if source_material is None or source_material.name != str(spec["source_active_material"]):
        raise RuntimeError(f"unexpected active iris material: {getattr(source_material, 'name', None)}")
    derived = source_material.copy()
    derived.name = str(spec["derived_material"])
    nodes = derived.node_tree.nodes
    links = derived.node_tree.links
    principal = active_principled(derived)
    base = principal.inputs.get("Base Color")
    failed = nodes.get(str(spec["failed_colorizer_node"]))
    if base is None or failed is None:
        raise RuntimeError("failed attempt-04 iris colorizer chain is incomplete")
    source_links = list(failed.inputs[1].links)
    base_links = list(base.links)
    if len(source_links) != 1 or len(base_links) != 1 or base_links[0].from_node != failed:
        raise RuntimeError("failed iris colorizer source/base links are ambiguous")
    source_socket = source_links[0].from_socket
    source_node = source_links[0].from_node
    source_image = getattr(source_node, "image", None)
    for link in list(base.links):
        links.remove(link)
    colorizer = nodes.new("ShaderNodeMixRGB")
    colorizer.name = str(spec["new_colorizer_node"])
    colorizer.label = "R19 bounded warm-brown melanin-like texture filter; source variation retained"
    colorizer.blend_type = str(spec["blend_type"])
    colorizer.inputs[0].default_value = float(spec["factor"])
    colorizer.inputs[2].default_value = tuple(float(value) for value in spec["warm_brown_linear_rgba"])
    links.new(source_socket, colorizer.inputs[1])
    links.new(colorizer.outputs[0], base)
    nodes.remove(failed)
    iris.material_slots[0].material = derived
    if nodes.get(str(spec["new_colorizer_node"])) is None:
        raise RuntimeError("new active iris pigment filter missing")
    if nodes.get(str(spec["failed_colorizer_node"])) is not None:
        raise RuntimeError("failed COLOR iris node remained in the active derived material")
    if assembly.mesh_geometry_uv_signature(iris) != geometry_before:
        raise RuntimeError("iris geometry/UV changed during material-only correction")
    if weight_signature(iris) != weights_before or modifier_signature(iris) != modifiers_before:
        raise RuntimeError("iris weights/modifier binding changed during material-only correction")
    return {
        "object": iris.name,
        "mesh": canonical(iris.data.name),
        "source_material": source_material.name,
        "derived_active_material": derived.name,
        "failed_colorizer_removed_from_active_material": True,
        "new_colorizer_node": colorizer.name,
        "blend_type": colorizer.blend_type,
        "factor": float(colorizer.inputs[0].default_value),
        "warm_brown_linear_rgba": [float(value) for value in colorizer.inputs[2].default_value],
        "source_texture_node": source_node.name,
        "source_image": source_image.name if source_image else None,
        "source_image_size": list(source_image.size) if source_image else None,
        "source_texture_feed_retained": any(
            link.from_node == source_node and link.to_node == colorizer
            for link in derived.node_tree.links
        ),
        "geometry_uv_sha256_before": geometry_before,
        "geometry_uv_sha256_after": assembly.mesh_geometry_uv_signature(iris),
        "positive_weight_assignment_sha256_unchanged": weight_signature(iris) == weights_before,
        "modifier_bindings_unchanged": modifier_signature(iris) == modifiers_before,
        "reason_for_attempt04_visual_failure": (
            "The prior COLOR blend retained the grey source luminance and its factor-0.82 hue replacement "
            "did not survive the rendered cornea/lighting strongly enough to read warm brown."
        ),
        "physical_interpretation": (
            "The stronger MULTIPLY layer acts as a bounded wavelength-selective pigment filter over the exact "
            "source albedo, retaining source texture variation rather than replacing it with a flat color."
        ),
        "visual_acceptance_claimed": False,
    }


def adjust_skin_surface_response(body: bpy.types.Object, spec: dict[str, Any]) -> dict[str, Any]:
    expected_names = list(spec["source_materials"])
    active = [material for material in body.data.materials if material is not None]
    if [material.name for material in active] != expected_names:
        raise RuntimeError(
            f"sealed body regional material order drifted: {[material.name for material in active]}"
        )
    records = []
    for index, source in enumerate(active):
        derived = source.copy()
        derived.name = source.name + str(spec["derived_suffix"])
        nodes = derived.node_tree.nodes
        links = derived.node_tree.links
        principal = active_principled(derived)
        roughness = principal.inputs.get("Roughness")
        specular = principal.inputs.get("Specular IOR Level")
        if roughness is None or specular is None or len(roughness.links) != 1 or len(specular.links) != 0:
            raise RuntimeError(f"unexpected packed surface-response graph in {source.name}")
        packed_socket = roughness.links[0].from_socket
        packed_node = roughness.links[0].from_node
        base_link_before = [
            (link.from_node.name, link.from_socket.name)
            for link in principal.inputs["Base Color"].links
        ]
        normal_link_before = [
            (link.from_node.name, link.from_socket.name)
            for link in principal.inputs["Normal"].links
        ]
        links.remove(roughness.links[0])
        roughness_adjust = nodes.new("ShaderNodeMath")
        roughness_adjust.name = str(spec["roughness_node"])
        roughness_adjust.label = "Bounded packed roughness: source*0.42+0.48"
        roughness_adjust.operation = str(spec["roughness_operation"])
        roughness_adjust.use_clamp = bool(spec["roughness_clamp"])
        roughness_adjust.inputs[1].default_value = float(spec["roughness_multiplier"])
        roughness_adjust.inputs[2].default_value = float(spec["roughness_addend"])
        links.new(packed_socket, roughness_adjust.inputs[0])
        links.new(roughness_adjust.outputs[0], roughness)
        specular_adjust = nodes.new("ShaderNodeValue")
        specular_adjust.name = str(spec["specular_node"])
        specular_adjust.label = "Bounded skin Specular IOR Level"
        specular_adjust.outputs[0].default_value = float(spec["specular_ior_level"])
        links.new(specular_adjust.outputs[0], specular)
        body.data.materials[index] = derived
        base_link_after = [
            (link.from_node.name, link.from_socket.name)
            for link in principal.inputs["Base Color"].links
        ]
        normal_link_after = [
            (link.from_node.name, link.from_socket.name)
            for link in principal.inputs["Normal"].links
        ]
        if base_link_after != base_link_before or normal_link_after != normal_link_before:
            raise RuntimeError(f"base-color or normal graph changed for {source.name}")
        records.append(
            {
                "source_material": source.name,
                "derived_active_material": derived.name,
                "packed_roughness_source_node": packed_node.name,
                "packed_roughness_source_socket": packed_socket.name,
                "roughness_node": roughness_adjust.name,
                "roughness_operation": roughness_adjust.operation,
                "roughness_multiplier": float(roughness_adjust.inputs[1].default_value),
                "roughness_addend": float(roughness_adjust.inputs[2].default_value),
                "roughness_clamped": bool(roughness_adjust.use_clamp),
                "specular_node": specular_adjust.name,
                "specular_ior_level": float(specular_adjust.outputs[0].default_value),
                "base_color_graph_unchanged": True,
                "normal_graph_unchanged": True,
                "flat_material_replacement_used": False,
            }
        )
    return {
        "regional_material_count": len(records),
        "records": records,
        "accepted_packed_base_color_normal_roughness_sources_retained": True,
        "bounded_surface_response_layer_only": True,
        "plastic_gloss_visual_acceptance_claimed": False,
    }


def degrees_to_radians(raw: dict[str, Sequence[float]]) -> dict[str, tuple[float, float, float]]:
    return {
        name: tuple(math.radians(float(value)) for value in values)
        for name, values in raw.items()
    }


def region_maps(body: bpy.types.Object) -> dict[str, list[int]]:
    regions = {
        "pelvis": assembly.region_indices(body, ("pelvis_", "lThighBend_", "rThighBend_"), 0.16),
        "left_thigh": assembly.region_indices(body, ("lThighBend_",), 0.16),
        "right_thigh": assembly.region_indices(body, ("rThighBend_",), 0.16),
        "left_foot": assembly.region_indices(body, ("lFoot_", "lToe_", "lMetatarsals_"), 0.10),
        "right_foot": assembly.region_indices(body, ("rFoot_", "rToe_", "rMetatarsals_"), 0.10),
        "left_hand": assembly.region_indices(
            body, ("lHand_", "lThumb", "lIndex", "lMid", "lRing", "lPinky"), 0.10
        ),
        "right_hand": assembly.region_indices(
            body, ("rHand_", "rThumb", "rIndex", "rMid", "rRing", "rPinky"), 0.10
        ),
    }
    if any(not indices for indices in regions.values()):
        raise RuntimeError(f"one or more movement regions is empty: { {k: len(v) for k, v in regions.items()} }")
    return regions


def fingertip_metrics(rig: bpy.types.Object) -> dict[str, Any]:
    result = {}
    for side, names in FINGERTIP_BONES.items():
        points = []
        for name in names:
            bone = rig.pose.bones.get(name)
            if bone is None:
                raise RuntimeError(f"terminal finger bone missing: {name}")
            points.append(rig.matrix_world @ bone.tail)
        adjacent = [(points[index] - points[index + 1]).length for index in range(4)]
        result[side] = {
            "bones": names,
            "tips_world_m": [[float(value) for value in point] for point in points],
            "adjacent_tip_distances_m": [round(float(value), 9) for value in adjacent],
            "minimum_adjacent_tip_distance_m": round(min(adjacent), 9),
            "tip_span_m": round(max((a - b).length for a in points for b in points), 9),
        }
    result["bilateral_minimum_adjacent_tip_distance_m"] = min(
        result["left"]["minimum_adjacent_tip_distance_m"],
        result["right"]["minimum_adjacent_tip_distance_m"],
    )
    return result


def supine_metrics(
    posed: list[Vector],
    neutral: list[Vector],
    epsilon: float,
    tolerance: float,
) -> dict[str, Any]:
    neutral_y = [float(point.y) for point in neutral]
    posterior_threshold = statistics.median(neutral_y)
    posterior_indices = [index for index, point in enumerate(neutral) if float(point.y) >= posterior_threshold]
    low_z = min(float(point.z) for point in posed)
    plane_z = low_z - epsilon
    support_limit = plane_z + 0.035
    supported = [posed[index] for index in posterior_indices if float(posed[index].z) <= support_limit]
    all_near = [point for point in posed if float(point.z) <= support_limit]
    posed_y = [float(point.y) for point in posed]
    total_span = max(posed_y) - min(posed_y)
    contact_span = (
        max(float(point.y) for point in supported) - min(float(point.y) for point in supported)
        if len(supported) >= 2
        else 0.0
    )
    neutral_high = max(float(point.z) for point in neutral)
    head_indices = [
        index
        for index, point in enumerate(neutral)
        if float(point.z) >= neutral_high - 0.30 and abs(float(point.x)) <= 0.16
    ]
    if not head_indices:
        raise RuntimeError("supine face-up metric has no head vertices")
    head_y = [float(neutral[index].y) for index in head_indices]
    head_mid = statistics.median(head_y)
    front = [posed[index] for index in head_indices if float(neutral[index].y) <= head_mid]
    rear = [posed[index] for index in head_indices if float(neutral[index].y) > head_mid]
    face_up_delta = (
        statistics.mean(float(point.z) for point in front)
        - statistics.mean(float(point.z) for point in rear)
    )
    return {
        "support_plane_z_m": round(plane_z, 9),
        "posterior_candidate_vertex_count": len(posterior_indices),
        "posterior_vertices_within_35mm": len(supported),
        "all_vertices_within_35mm": len(all_near),
        "posterior_longitudinal_contact_span_m": round(contact_span, 9),
        "body_longitudinal_span_m": round(total_span, 9),
        "posterior_contact_span_fraction": round(contact_span / total_span if total_span else 0.0, 9),
        "front_of_face_above_rear_delta_m": round(face_up_delta, 9),
        "face_up_orientation": face_up_delta > 0.02,
        "support_contact": assembly.plane_contact_metrics(all_near, plane_z, tolerance),
        "truth_note": "Geometric support/orientation metrics do not by themselves establish a natural lying pose.",
    }


def mouth_indices(neutral: list[Vector]) -> list[int]:
    high_z = max(float(point.z) for point in neutral)
    candidates = [
        index
        for index, point in enumerate(neutral)
        if high_z - 0.29 <= float(point.z) <= high_z - 0.13
        and abs(float(point.x)) <= 0.10
    ]
    if not candidates:
        raise RuntimeError("mouth-region approximation has no vertices")
    front_y = min(float(neutral[index].y) for index in candidates)
    selected = [index for index in candidates if float(neutral[index].y) <= front_y + 0.035]
    if not selected:
        raise RuntimeError("mouth-region front selection has no vertices")
    return selected


def reach_metrics(
    posed: list[Vector],
    neutral: list[Vector],
    regions: dict[str, list[int]],
    epsilon: float,
    tolerance: float,
) -> dict[str, Any]:
    hand = [posed[index] for index in regions["left_hand"]]
    hand_low = min(float(point.z) for point in hand)
    table_z = hand_low - epsilon
    near = [point for point in hand if float(point.z) <= hand_low + 0.035]
    hand_center = sum(hand, Vector()) / len(hand)
    mouth = [posed[index] for index in mouth_indices(neutral)]
    mouth_center = sum(mouth, Vector()) / len(mouth)
    mouth_distance = (hand_center - mouth_center).length
    return {
        "table_top_z_m": round(table_z, 9),
        "table_contact": assembly.plane_contact_metrics(near, table_z, tolerance),
        "hand_center_world_m": [float(value) for value in hand_center],
        "mouth_region_center_world_m": [float(value) for value in mouth_center],
        "hand_center_to_mouth_region_m": round(float(mouth_distance), 9),
        "classification": "hand_to_mouth_foundation" if mouth_distance <= 0.16 else "table_reach_only",
        "eating_or_swallowing_claimed": False,
    }


def candidate_specific_metrics(
    group: str,
    body: bpy.types.Object,
    rig: bpy.types.Object,
    posed: list[Vector],
    neutral: list[Vector],
    regions: dict[str, list[int]],
    config: dict[str, Any],
) -> dict[str, Any]:
    epsilon = float(config["support_epsilon_m"])
    tolerance = float(config["contact_tolerance_m"])
    if group == "supported_seated":
        seat_regions = {key: regions[key] for key in ("pelvis", "left_foot", "right_foot")}
        return {
            "contact": seated_worker.contact_solution(body, posed, seat_regions),
            "geometry": seated_worker.geometric_pose_metrics(body, posed, seat_regions),
        }
    if group == "supine_lying":
        return supine_metrics(posed, neutral, epsilon, tolerance)
    if group == "eating_or_table_reach":
        return reach_metrics(posed, neutral, regions, epsilon, tolerance)
    if group == "hands_fingers":
        return fingertip_metrics(rig)
    raise ValueError(group)


def candidate_score(
    group: str,
    exact_count: int,
    nail_count: int,
    stretch: dict[str, Any],
    metrics: dict[str, Any],
    baseline: int,
) -> tuple[float, dict[str, float]]:
    parts = {
        "exact_self_intersection_excess": float(max(0, exact_count - baseline) * 1000),
        "exact_body_nail_crossing": float(nail_count * 100000),
        "maximum_edge_ratio": float(max(0.0, stretch["all_body_edges"]["maximum_ratio"] - 1.0) * 10.0),
    }
    if group == "supported_seated":
        contact = metrics["contact"]
        geometry = metrics["geometry"]
        parts["missing_three_supports"] = 0.0 if contact["all_three_supports_within_tolerance"] else 50000.0
        parts["foot_height_asymmetry"] = float(geometry["bilateral_foot_low_height_difference_m"] * 10000.0)
        parts["sole_pitch"] = float(
            (
                geometry["left_toe_heel_bottom_height_difference_m"]
                + geometry["right_toe_heel_bottom_height_difference_m"]
            )
            * 3000.0
        )
        parts["posterior_contact_reward"] = -float(contact["seat"]["contact_point_count_within_tolerance"] * 0.1)
    elif group == "supine_lying":
        parts["face_down_penalty"] = 0.0 if metrics["face_up_orientation"] else 50000.0
        parts["limited_support_span"] = float(max(0.0, 0.55 - metrics["posterior_contact_span_fraction"]) * 10000.0)
        parts["posterior_contact_reward"] = -float(metrics["posterior_vertices_within_35mm"] * 0.02)
    elif group == "eating_or_table_reach":
        parts["missing_table_contact"] = 0.0 if metrics["table_contact"]["within_contact_tolerance"] else 50000.0
        parts["reach_contact_reward"] = -float(metrics["table_contact"]["contact_point_count_within_tolerance"] * 0.02)
    elif group == "hands_fingers":
        separation = float(metrics["bilateral_minimum_adjacent_tip_distance_m"])
        parts["compressed_tip_penalty"] = float(max(0.0, 0.012 - separation) * 100000.0)
        parts["tip_separation_reward"] = -separation * 100.0
    return sum(parts.values()), parts


def set_visible(objects: Sequence[bpy.types.Object], visible: bool) -> None:
    for obj in objects:
        obj.hide_render = not visible
        obj.hide_viewport = not visible
        obj.hide_set(not visible)


def support_props(
    group: str,
    candidate_id: str,
    posed: list[Vector],
    regions: dict[str, list[int]],
    metrics: dict[str, Any],
    collection: bpy.types.Collection,
    epsilon: float,
) -> list[bpy.types.Object]:
    navy = assembly.make_material(
        f"Kira_R19_Attempt05_Support_Navy_{candidate_id}", (0.025, 0.09, 0.15, 1.0), 0.82
    )
    floor_mat = assembly.make_material(
        f"Kira_R19_Attempt05_Floor_{candidate_id}", (0.055, 0.065, 0.075, 1.0), 0.88
    )
    box = assembly.bounds(posed)
    low, high = Vector(box["low"]), Vector(box["high"])
    props = []
    if group == "supported_seated":
        seat = metrics["contact"]["seat"]
        floor = metrics["contact"]["floor"]
        props.append(
            assembly.make_cube(
                collection,
                f"Kira_R19_Attempt05_{candidate_id}_Seat",
                (
                    (seat["x_min_m"] + seat["x_max_m"]) * 0.5,
                    (seat["y_min_m"] + seat["y_max_m"]) * 0.5,
                    seat["top_z_m"] - 0.025,
                ),
                (
                    seat["x_max_m"] - seat["x_min_m"],
                    seat["y_max_m"] - seat["y_min_m"],
                    0.05,
                ),
                navy,
            )
        )
        props.append(
            assembly.make_cube(
                collection,
                f"Kira_R19_Attempt05_{candidate_id}_Floor",
                ((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, floor["top_z_m"] - 0.0125),
                ((high.x - low.x) + 0.5, (high.y - low.y) + 0.5, 0.025),
                floor_mat,
            )
        )
    elif group == "supine_lying":
        plane = float(metrics["support_plane_z_m"])
        props.append(
            assembly.make_cube(
                collection,
                f"Kira_R19_Attempt05_{candidate_id}_SupineSupport",
                ((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, plane - 0.04),
                ((high.x - low.x) + 0.3, (high.y - low.y) + 0.3, 0.08),
                navy,
            )
        )
    elif group == "eating_or_table_reach":
        hand = [posed[index] for index in regions["left_hand"]]
        hand_box = assembly.bounds(hand)
        hand_low, hand_high = Vector(hand_box["low"]), Vector(hand_box["high"])
        table = float(metrics["table_top_z_m"])
        props.append(
            assembly.make_cube(
                collection,
                f"Kira_R19_Attempt05_{candidate_id}_ReachTable",
                ((hand_low.x + hand_high.x) * 0.5, (hand_low.y + hand_high.y) * 0.5, table - 0.025),
                (0.48, 0.42, 0.05),
                navy,
            )
        )
        props.append(
            assembly.make_cube(
                collection,
                f"Kira_R19_Attempt05_{candidate_id}_ContextCup",
                (float(hand_high.x) + 0.035, (hand_low.y + hand_high.y) * 0.5, table + 0.055),
                (0.055, 0.055, 0.11),
                assembly.make_material(
                    f"Kira_R19_Attempt05_Cup_{candidate_id}", (0.14, 0.42, 0.56, 1.0), 0.50
                ),
            )
        )
    for obj in props:
        obj["attempt05_candidate"] = candidate_id
        obj["review_context_prop_only"] = True
        obj["must_not_export"] = True
    set_visible(props, False)
    return props


def candidate_preview(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    output_dir: Path,
    group: str,
    candidate_id: str,
    posed: list[Vector],
    regions: dict[str, list[int]],
    props: Sequence[bpy.types.Object],
) -> str:
    set_visible(props, True)
    box = assembly.bounds(posed)
    low, high = Vector(box["low"]), Vector(box["high"])
    center = (low + high) * 0.5
    height, width, depth = high.z - low.z, high.x - low.x, high.y - low.y
    distance = max(height, width, depth) * 2.3 + 1.0
    name = f"candidate_{candidate_id}"
    if group == "supported_seated":
        location = Vector((center.x + distance * 0.58, center.y - distance, center.z))
        target, scale = center, height * 1.16
    elif group == "supine_lying":
        location = Vector((center.x + distance * 0.55, center.y - distance * 0.72, center.z + distance * 0.30))
        target, scale = center, max(width, depth) * 1.15
    elif group == "eating_or_table_reach":
        location = Vector((center.x + distance * 0.58, center.y - distance, center.z))
        target, scale = center, height * 1.12
    else:
        hand_points = [posed[index] for key in ("left_hand", "right_hand") for index in regions[key]]
        hand_box = assembly.bounds(hand_points)
        hand_low, hand_high = Vector(hand_box["low"]), Vector(hand_box["high"])
        target = (hand_low + hand_high) * 0.5
        scale = max(hand_high.x - hand_low.x, hand_high.z - hand_low.z, 0.42) * 1.15
        location = Vector((target.x, target.y - 2.0, target.z + 0.05))
    filename = assembly.render_view(scene, camera, output_dir, name, location, target, scale)
    set_visible(props, False)
    return filename


def evaluate_candidates(
    config: dict[str, Any],
    body: bpy.types.Object,
    rig: bpy.types.Object,
    nails: list[bpy.types.Object],
    neutral_body: list[Vector],
    neutral_nails: dict[str, list[Vector]],
    regions: dict[str, list[int]],
    output_dir: Path,
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    prop_collection: bpy.types.Collection,
    source_nail_records: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]], dict[str, list[bpy.types.Object]]]:
    exact_dir = output_dir / "exact_intersections"
    nail_dir = output_dir / "body_nail_intersections"
    exact_dir.mkdir()
    nail_dir.mkdir()
    records_by_group: dict[str, list[dict[str, Any]]] = {}
    props_by_candidate: dict[str, list[bpy.types.Object]] = {}
    baseline = int(config["neutral_exact_self_intersection_baseline"])
    region_for_group = {
        "supported_seated": sorted(set(regions["pelvis"] + regions["left_thigh"] + regions["right_thigh"])),
        "supine_lying": list(range(len(body.data.vertices))),
        "eating_or_table_reach": regions["left_hand"],
        "hands_fingers": sorted(set(regions["left_hand"] + regions["right_hand"])),
    }

    for group, candidates in config["pose_candidates"].items():
        group_records = []
        for candidate in candidates:
            candidate_id = str(candidate["id"])
            rotations = degrees_to_radians(candidate["rotations_degrees_xyz"])
            assembly.apply_rotations(rig, rotations)
            posed = assembly.evaluated_vertices(body)
            exact = assembly.exact_body_intersection_report(body)
            exact_path = exact_dir / f"{candidate_id}.json"
            write_json(exact_path, exact)
            nail_cross = assembly.exact_cross_intersections(body, nails)
            nail_path = nail_dir / f"{candidate_id}.json"
            write_json(nail_path, nail_cross)
            stretch = assembly.edge_stretch_report(
                body,
                neutral_body,
                posed,
                set(region_for_group[group]),
            )
            metrics = candidate_specific_metrics(
                group,
                body,
                rig,
                posed,
                neutral_body,
                regions,
                config,
            )
            nail_follow = assembly.nail_follow_report(
                rig,
                nails,
                source_nail_records,
                neutral_nails,
            )
            exact_count = int(exact["exact_genuine_penetration_pair_count"])
            nail_count = int(nail_cross["total_exact_genuine_body_nail_triangle_pair_count"])
            score, score_parts = candidate_score(
                group,
                exact_count,
                nail_count,
                stretch,
                metrics,
                baseline,
            )
            props = support_props(
                group,
                candidate_id,
                posed,
                regions,
                metrics,
                prop_collection,
                float(config["support_epsilon_m"]),
            )
            props_by_candidate[candidate_id] = props
            preview = candidate_preview(
                scene,
                camera,
                output_dir,
                group,
                candidate_id,
                posed,
                regions,
                props,
            )
            action_name = f"KIRA_R19_ATTEMPT05_{candidate_id.upper()}"
            action = assembly.author_action(
                rig,
                action_name,
                rotations,
                str(config["candidate_id"]),
            )
            action["bounded_candidate_group"] = group
            action["bounded_candidate_id"] = candidate_id
            action["owner_approved"] = False
            group_records.append(
                {
                    "id": candidate_id,
                    "action": action.name,
                    "rotations_degrees_xyz": candidate["rotations_degrees_xyz"],
                    "exact_self_intersections": {
                        "report": project_relative(exact_path),
                        "report_sha256": sha256_file(exact_path),
                        "exact_genuine_penetration_pair_count": exact_count,
                    },
                    "exact_body_nail_intersections": {
                        "report": project_relative(nail_path),
                        "report_sha256": sha256_file(nail_path),
                        "total_exact_genuine_body_nail_triangle_pair_count": nail_count,
                    },
                    "deformation_stretch": stretch,
                    "nail_follow": nail_follow,
                    "specific_metrics": metrics,
                    "selection_score": round(float(score), 9),
                    "selection_score_parts": score_parts,
                    "preview_render": preview,
                    "visual_acceptance_claimed": False,
                }
            )
        records_by_group[group] = group_records

    selected = {}
    for group, records in records_by_group.items():
        best = min(records, key=lambda record: (float(record["selection_score"]), str(record["id"])))
        selected[group] = {
            "id": best["id"],
            "action": best["action"],
            "selection_score": best["selection_score"],
            "selection_basis": (
                "Deterministic ranking of the two predeclared candidates: exact body/nail crossings first, "
                "then bounded deformation and defect-specific contact/orientation/separation metrics."
            ),
            "owner_visual_acceptance_claimed": False,
        }
        bpy.data.actions[best["action"]]["selected_bounded_candidate"] = True
        for record in records:
            if record["id"] != best["id"]:
                bpy.data.actions[record["action"]]["selected_bounded_candidate"] = False
    return records_by_group, selected, props_by_candidate


def render_neutral_material_evidence(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    output_dir: Path,
    body: bpy.types.Object,
    iris: bpy.types.Object,
    regions: dict[str, list[int]],
) -> dict[str, str]:
    points = assembly.evaluated_vertices(body)
    box = assembly.bounds(points)
    low, high = Vector(box["low"]), Vector(box["high"])
    center = (low + high) * 0.5
    height = high.z - low.z
    distance = height * 2.5 + 1.0
    renders = {}
    renders["attempt05_neutral_front_surface_response"] = assembly.render_view(
        scene,
        camera,
        output_dir,
        "attempt05_neutral_front_surface_response",
        Vector((center.x, center.y - distance, center.z)),
        center,
        height * 1.08,
    )
    face_target = Vector((center.x, center.y, high.z - 0.22))
    renders["attempt05_close_face_eyes_brows_surface_response"] = assembly.render_view(
        scene,
        camera,
        output_dir,
        "attempt05_close_face_eyes_brows_surface_response",
        Vector((face_target.x, face_target.y - distance, face_target.z)),
        face_target,
        0.56,
    )
    iris_points = assembly.evaluated_vertices(iris)
    split_x = statistics.median(float(point.x) for point in iris_points)
    for label, subset in {
        "attempt05_close_negative_x_eye_warm_brown": [point for point in iris_points if float(point.x) <= split_x],
        "attempt05_close_positive_x_eye_warm_brown": [point for point in iris_points if float(point.x) > split_x],
    }.items():
        target = sum(subset, Vector()) / len(subset)
        subset_box = assembly.bounds(subset)
        eye_size = max(Vector(subset_box["size"]).x, Vector(subset_box["size"]).z)
        renders[label] = assembly.render_view(
            scene,
            camera,
            output_dir,
            label,
            Vector((target.x, target.y - 1.2, target.z)),
            target,
            max(0.13, eye_size * 4.2),
        )
    pelvis = assembly.region_center(points, regions["pelvis"])
    renders["attempt05_protected_adult_front_panel_unchanged"] = assembly.render_view(
        scene,
        camera,
        output_dir,
        "attempt05_protected_adult_front_panel_unchanged",
        Vector((pelvis.x, pelvis.y - 1.5, pelvis.z)),
        pelvis,
        0.48,
    )
    shoulder_target = Vector((0.23, center.y - 0.02, 1.38))
    renders["attempt05_skin_surface_response_close"] = assembly.render_view(
        scene,
        camera,
        output_dir,
        "attempt05_skin_surface_response_close",
        Vector((shoulder_target.x + 0.9, shoulder_target.y - 1.1, shoulder_target.z + 0.15)),
        shoulder_target,
        0.48,
    )
    return renders


def selected_record(records_by_group: dict[str, list[dict[str, Any]]], selected: dict[str, Any], group: str) -> dict[str, Any]:
    selected_id = selected[group]["id"]
    return next(record for record in records_by_group[group] if record["id"] == selected_id)


def render_selected_movements(
    config: dict[str, Any],
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    output_dir: Path,
    body: bpy.types.Object,
    rig: bpy.types.Object,
    regions: dict[str, list[int]],
    records_by_group: dict[str, list[dict[str, Any]]],
    selected: dict[str, dict[str, Any]],
    props_by_candidate: dict[str, list[bpy.types.Object]],
) -> dict[str, str]:
    renders: dict[str, str] = {}
    for group in ("supported_seated", "supine_lying", "eating_or_table_reach", "hands_fingers"):
        record = selected_record(records_by_group, selected, group)
        rotations = degrees_to_radians(record["rotations_degrees_xyz"])
        assembly.apply_rotations(rig, rotations)
        points = assembly.evaluated_vertices(body)
        box = assembly.bounds(points)
        low, high = Vector(box["low"]), Vector(box["high"])
        center = (low + high) * 0.5
        height, width, depth = high.z - low.z, high.x - low.x, high.y - low.y
        distance = max(height, width, depth) * 2.3 + 1.0
        props = props_by_candidate[str(record["id"])]
        set_visible(props, True)
        if group == "supported_seated":
            views = {
                "selected_seated_front_three_quarter": Vector((center.x + distance * 0.58, center.y - distance, center.z)),
                "selected_seated_left_profile": Vector((center.x - distance, center.y, center.z)),
                "selected_seated_rear_three_quarter": Vector((center.x - distance * 0.58, center.y + distance, center.z)),
            }
            for name, location in views.items():
                renders[name] = assembly.render_view(scene, camera, output_dir, name, location, center, height * 1.16)
            feet = (
                assembly.region_center(points, regions["left_foot"])
                + assembly.region_center(points, regions["right_foot"])
            ) * 0.5
            renders["selected_seated_feet_contact"] = assembly.render_view(
                scene,
                camera,
                output_dir,
                "selected_seated_feet_contact",
                Vector((feet.x + 1.5, feet.y - 1.2, feet.z + 0.08)),
                feet,
                0.62,
            )
        elif group == "supine_lying":
            for suffix, location in {
                "side": Vector((center.x + distance, center.y, center.z)),
                "three_quarter": Vector((center.x + distance * 0.55, center.y - distance * 0.72, center.z + distance * 0.30)),
                "top": Vector((center.x, center.y, center.z + distance)),
            }.items():
                name = f"selected_supine_{suffix}"
                renders[name] = assembly.render_view(
                    scene, camera, output_dir, name, location, center, max(width, depth) * 1.15
                )
        elif group == "eating_or_table_reach":
            for suffix, location in {
                "front_three_quarter": Vector((center.x + distance * 0.58, center.y - distance, center.z)),
                "left_profile": Vector((center.x - distance, center.y, center.z)),
            }.items():
                name = f"selected_reach_{suffix}"
                renders[name] = assembly.render_view(scene, camera, output_dir, name, location, center, height * 1.12)
            hand = assembly.region_center(points, regions["left_hand"])
            renders["selected_reach_hand_table_close"] = assembly.render_view(
                scene,
                camera,
                output_dir,
                "selected_reach_hand_table_close",
                Vector((hand.x + 1.2, hand.y - 1.0, hand.z + 0.15)),
                hand,
                0.52,
            )
        else:
            for side in ("left", "right"):
                hand = assembly.region_center(points, regions[f"{side}_hand"])
                front_name = f"selected_hands_{side}_front_close"
                top_name = f"selected_hands_{side}_top_close"
                renders[front_name] = assembly.render_view(
                    scene,
                    camera,
                    output_dir,
                    front_name,
                    Vector((hand.x, hand.y - 1.35, hand.z + 0.05)),
                    hand,
                    0.36,
                )
                renders[top_name] = assembly.render_view(
                    scene,
                    camera,
                    output_dir,
                    top_name,
                    Vector((hand.x, hand.y, hand.z + 1.35)),
                    hand,
                    0.36,
                )
        set_visible(props, False)
    assembly.reset_pose(rig)
    return renders


def run_attempt(
    config_path: Path,
    config: dict[str, Any],
    paths: dict[str, Path],
    preflight: dict[str, Any],
) -> int:
    if Path(bpy.data.filepath).resolve() != paths["source_blend"].resolve():
        raise RuntimeError("worker must open the exact sealed attempt-04 Blend")
    source_evidence = json.loads(paths["source_evidence"].read_text(encoding="utf-8"))
    if source_evidence["candidate_id"] != "KIRA_BALD_LOW_RESOURCE_BODY_R19_ATTEMPT_04":
        raise RuntimeError("source evidence is not the sealed attempt-04 candidate")
    if int(source_evidence["pose_exact_body_intersection_counts"]["neutral"]) != int(
        config["neutral_exact_self_intersection_baseline"]
    ):
        raise RuntimeError("configured neutral exact-intersection baseline drifted")

    output_dir = (PROJECT_ROOT / str(config["output_dir"])).resolve()
    if output_dir.exists():
        raise FileExistsError(f"append-only output already exists: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)

    body, rig, nails, iris = find_components()
    source_meshes = candidate_meshes()
    source_mesh_names = [obj.name for obj in source_meshes]
    mesh_before = {obj.name: mesh_immutable_state(obj) for obj in source_meshes}
    rig_before = rig_immutable_signature(rig)
    nail_materials_before = {
        nail.name: assembly.material_binding_signature(nail) for nail in nails
    }
    protected_eye_names = {
        "Ariel_Mesh_Pupils_0",
        "Ariel_Mesh_Cornea_0",
        "Ariel_Mesh_Sclera_0",
    }
    protected_eye_before = {
        canonical(obj.data.name): {
            "immutable": mesh_immutable_state(obj),
            "materials": assembly.material_binding_signature(obj),
        }
        for obj in source_meshes
        if canonical(obj.data.name) in protected_eye_names
    }
    if set(protected_eye_before) != protected_eye_names:
        raise RuntimeError("protected pupil/cornea/sclera inventory incomplete")

    material_spec = config["material_corrections"]
    iris_record = strengthen_iris_material(iris, material_spec["iris"])
    skin_record = adjust_skin_surface_response(body, material_spec["skin"])

    # Retain every earlier context object only as hidden evidence.  New props
    # are separately named and never exported.
    for obj in bpy.data.objects:
        if bool(obj.get("review_context_prop_only")):
            obj.hide_render = True
            obj.hide_viewport = True
            obj.hide_set(True)

    scene, camera = assembly.configure_render(config)
    prop_collection = bpy.data.collections.new("KIRA_R19_ATTEMPT05_REVIEW_PROPS_DO_NOT_EXPORT")
    bpy.context.scene.collection.children.link(prop_collection)
    regions = region_maps(body)
    assembly.reset_pose(rig)
    neutral_body = assembly.evaluated_vertices(body)
    neutral_nails = {nail.name: assembly.evaluated_vertices(nail) for nail in nails}

    records_by_group, selected, props_by_candidate = evaluate_candidates(
        config,
        body,
        rig,
        nails,
        neutral_body,
        neutral_nails,
        regions,
        output_dir,
        scene,
        camera,
        prop_collection,
        source_evidence["nails"]["records"],
    )
    assembly.reset_pose(rig)
    neutral_renders = render_neutral_material_evidence(
        scene,
        camera,
        output_dir,
        body,
        iris,
        regions,
    )
    movement_renders = render_selected_movements(
        config,
        scene,
        camera,
        output_dir,
        body,
        rig,
        regions,
        records_by_group,
        selected,
        props_by_candidate,
    )
    candidate_renders = {
        f"candidate_{record['id']}": record["preview_render"]
        for records in records_by_group.values()
        for record in records
    }
    render_names = {**candidate_renders, **neutral_renders, **movement_renders}

    restoration = assembly.restoration_report(rig, body, neutral_body)
    if not restoration["exact_neutral_restoration_passed"]:
        raise RuntimeError(f"exact neutral restoration failed: {restoration}")

    mesh_after = {
        name: mesh_immutable_state(bpy.data.objects[name])
        for name in source_mesh_names
    }
    geometry_drift = {
        name: {"before": mesh_before[name], "after": mesh_after[name]}
        for name in source_mesh_names
        if mesh_before[name] != mesh_after[name]
    }
    if geometry_drift:
        raise RuntimeError(f"immutable mesh/UV/weight/transform/modifier state changed: {list(geometry_drift)}")
    rig_after = rig_immutable_signature(rig)
    if rig_after != rig_before:
        raise RuntimeError("native rig rest structure changed")
    nail_materials_after = {
        nail.name: assembly.material_binding_signature(nail) for nail in nails
    }
    if nail_materials_after != nail_materials_before:
        raise RuntimeError("nail material bindings changed")
    protected_eye_after = {
        canonical(obj.data.name): {
            "immutable": mesh_immutable_state(obj),
            "materials": assembly.material_binding_signature(obj),
        }
        for obj in source_meshes
        if canonical(obj.data.name) in protected_eye_names
    }
    if protected_eye_after != protected_eye_before:
        raise RuntimeError("pupil/cornea/sclera changed")

    source_hashes_after = {key: sha256_file(path) for key, path in paths.items()}
    if source_hashes_after != preflight["protected_input_hashes"]:
        raise RuntimeError("one or more protected attempt-04 inputs changed")

    scene["candidate_id"] = str(config["candidate_id"])
    scene["private_owner_review_only"] = True
    scene["inactive_candidate"] = True
    scene["owner_approved"] = False
    scene["runtime_assignment_allowed"] = False
    scene["runtime_activation_allowed"] = False
    scene["public_export_allowed"] = False
    scene["no_scalp_hair_dependency"] = True
    scene["pelvic_component_visual_acceptance"] = False
    scene["known_pelvic_component_defect"] = "unchanged hard triangular superior panel / recessed seam"
    scene["material_and_action_correction_only"] = True
    scene["bounded_candidates_per_movement_defect"] = 2

    blend_path = output_dir / "kira_r19_bald_targeted_material_movement_correction.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    render_evidence = assembly.render_bindings(output_dir, render_names)

    selected_summary = {}
    for group, selection in selected.items():
        record = selected_record(records_by_group, selected, group)
        selected_summary[group] = {
            **selection,
            "exact_genuine_body_self_intersection_pair_count": record[
                "exact_self_intersections"
            ]["exact_genuine_penetration_pair_count"],
            "exact_body_nail_crossing_pair_count": record[
                "exact_body_nail_intersections"
            ]["total_exact_genuine_body_nail_triangle_pair_count"],
            "maximum_body_edge_ratio": record["deformation_stretch"]["all_body_edges"][
                "maximum_ratio"
            ],
            "specific_metrics": record["specific_metrics"],
        }

    evidence = {
        "schema_version": 1,
        "candidate_id": str(config["candidate_id"]),
        "created_utc": utc_now(),
        "status": (
            "COMPLETE_BOUNDED_TARGETED_MATERIAL_AND_ACTION_CORRECTION_PACKAGE_"
            "PENDING_OWNER_VISUAL_REVIEW_WITH_UNCHANGED_PELVIC_FAILURE"
        ),
        "scope": {
            "private": True,
            "inactive": True,
            "unassigned": True,
            "unpublished": True,
            "owner_approved": False,
            "runtime_activation_allowed": False,
            "live_export_created": False,
            "glb_export_created": False,
            "clothing_included": False,
            "scalp_hair_included": False,
            "source_attempt_04_preserved": True,
        },
        "preflight": preflight,
        "material_diagnosis_and_corrections": {
            "iris": iris_record,
            "skin_surface_response": skin_record,
            "visual_acceptance_requires_post_render_review": True,
        },
        "immutable_component_verification": {
            "source_mesh_object_count": len(source_meshes),
            "all_source_mesh_geometry_uv_weights_transforms_modifiers_unchanged": True,
            "body_and_face_shape_unchanged": True,
            "pelvic_topology_and_shape_unchanged": True,
            "native_rig_rest_structure_sha256_before": rig_before,
            "native_rig_rest_structure_sha256_after": rig_after,
            "native_rig_rest_structure_unchanged": True,
            "nail_geometry_uv_weights_transforms_modifiers_unchanged": True,
            "nail_material_bindings_unchanged": True,
            "pupils_cornea_sclera_unchanged": True,
            "immutable_mesh_states": mesh_after,
        },
        "bounded_movement_candidate_contract": {
            "candidate_groups": list(config["pose_candidates"]),
            "candidates_per_group": 2,
            "total_candidates": 8,
            "open_search_or_framework_used": False,
            "selection_is_provisional_not_owner_approval": True,
        },
        "movement_candidates": records_by_group,
        "selected_movement_candidates": selected_summary,
        "neutral_exact_self_intersection_baseline": int(
            config["neutral_exact_self_intersection_baseline"]
        ),
        "exact_neutral_restoration": restoration,
        "bald_runtime_contract": assembly.scalp_hair_dependency_audit(),
        "protected_source_hashes_after": source_hashes_after,
        "known_unchanged_failures": {
            "pelvic_panel": (
                "The attempt-04/attempt-05 body retains the same hard triangular superior pelvic panel, "
                "straight seam, and recessed transition. This task did not change or disguise it."
            ),
            "nails": (
                "All twenty attempt-04 source-native nail objects are preserved exactly, including the "
                "previously disclosed long square/French-tip fingernails and faceted/dark toenail appearance."
            ),
            "whole_body_owner_approval": False,
        },
        "gates": {
            "iris_geometry_uv_weights_rig_unchanged": True,
            "active_iris_source_texture_retained": bool(iris_record["source_texture_feed_retained"]),
            "active_failed_color_blend_removed": True,
            "six_packed_regional_skin_graphs_retained": skin_record["regional_material_count"] == 6,
            "bounded_roughness_and_specular_layer_present": True,
            "exactly_two_predeclared_candidates_per_movement_defect": True,
            "body_face_pelvic_nail_geometry_unchanged": True,
            "native_rig_and_weights_unchanged": True,
            "exact_neutral_restoration": True,
            "pelvic_component_visual_acceptance": False,
            "whole_body_owner_acceptance": False,
            "runtime_eligibility": False,
        },
        "artifacts": {
            "blend": {
                "path": project_relative(blend_path),
                "sha256": sha256_file(blend_path),
                "size_bytes": blend_path.stat().st_size,
            },
            "renders": render_evidence,
        },
    }
    evidence_path = output_dir / "BUILD_EVIDENCE.json"
    write_json(evidence_path, evidence)
    (output_dir / "ROLLBACK.md").write_text(
        "# Rollback\n\n"
        "This package is append-only and inactive. Roll back by keeping the sealed attempt-04 package as the "
        "controlling source and disregarding this attempt-05 directory. Do not delete or overwrite attempt 04.\n",
        encoding="utf-8",
    )
    (output_dir / "OWNER_REVIEW_README.md").write_text(
        "# Kira R19 targeted correction attempt 05\n\n"
        "Status: **COMPLETE BOUNDED CORRECTION PACKAGE; NOT OWNER-ACCEPTED OR ACTIVE**\n\n"
        "This package changes only the active iris material, the six packed skin materials' bounded roughness/"
        "specular response, and new private movement actions selected from exactly two predeclared candidates "
        "per defect. It does not change body, face, pelvic, nail, or rig geometry/weights.\n\n"
        "The pelvic panel and nail appearance remain deliberately unchanged and rejected. Candidate previews, "
        "selected-action renders, and exact audits are included. Graph or metric passes are not visual approval.\n",
        encoding="utf-8",
    )
    checkpoint_path = output_dir / "CHECKPOINT.md"
    checkpoint_path.write_text(
        "# Kira R19 attempt-05 targeted correction checkpoint\n\n"
        f"Created UTC: `{evidence['created_utc']}`\n\n"
        f"Candidate: `{config['candidate_id']}`\n\n"
        f"Blend SHA-256: `{sha256_file(blend_path)}`\n\n"
        f"Build evidence SHA-256 before manifest: `{sha256_file(evidence_path)}`\n\n"
        "Private, inactive, unassigned, unpublished, not runtime eligible, and pending independent visual review.\n",
        encoding="utf-8",
    )
    manifest_path = assembly.write_manifest(output_dir)
    print(
        json.dumps(
            {
                "ok": True,
                "status": evidence["status"],
                "output_dir": project_relative(output_dir),
                "blend_sha256": sha256_file(blend_path),
                "evidence_sha256": sha256_file(evidence_path),
                "checkpoint_sha256": sha256_file(checkpoint_path),
                "manifest_sha256": sha256_file(manifest_path),
                "render_count": len(render_evidence),
                "selected": selected_summary,
                "owner_approval": False,
                "runtime_eligibility": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def preserve_failure(config: dict[str, Any], config_path: Path, exc: BaseException) -> None:
    output_dir = (PROJECT_ROOT / str(config["output_dir"])).resolve()
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=False)
    failure_path = output_dir / "FAILURE_EVIDENCE.json"
    if failure_path.exists():
        return
    write_json(
        failure_path,
        {
            "schema_version": 1,
            "status": "ATTEMPT_05_FAILED_BEFORE_TARGETED_PACKAGE_COMPLETION",
            "created_utc": utc_now(),
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
            "config": project_relative(config_path),
            "config_sha256": sha256_file(config_path),
            "worker": project_relative(Path(__file__).resolve()),
            "worker_sha256": sha256_file(Path(__file__).resolve()),
            "source_attempt_04_modified": False,
            "attempt_04_preserved": True,
            "runtime_or_assignment_changed": False,
            "owner_approval_claimed": False,
        },
    )
    assembly.write_manifest(output_dir)


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    try:
        config, paths, preflight = load_config(config_path)
        if args.preflight_only:
            if Path(bpy.data.filepath).resolve() != paths["source_blend"].resolve():
                raise RuntimeError("preflight must open the exact sealed attempt-04 Blend")
            body, rig, nails, iris = find_components()
            requested_bones = {
                bone_name
                for candidates in config["pose_candidates"].values()
                for candidate in candidates
                for bone_name in candidate["rotations_degrees_xyz"]
            }
            missing_bones = sorted(requested_bones - {bone.name for bone in rig.data.bones})
            if missing_bones:
                raise RuntimeError(f"predeclared action bones missing: {missing_bones}")
            active_skin = [material.name for material in body.data.materials if material is not None]
            if active_skin != config["material_corrections"]["skin"]["source_materials"]:
                raise RuntimeError(f"sealed skin material bindings drifted: {active_skin}")
            iris_material = iris.material_slots[0].material
            if iris_material is None or iris_material.name != config["material_corrections"]["iris"]["source_active_material"]:
                raise RuntimeError("sealed active iris material drifted")
            print(
                json.dumps(
                    {
                        "ok": True,
                        "preflight_only": True,
                        **preflight,
                        "native_joint_count": len(rig.data.bones),
                        "nail_count": len(nails),
                        "predeclared_bone_count": len(requested_bones),
                        "all_predeclared_bones_present": True,
                        "attempt_05_output_created": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        return run_attempt(config_path, config, paths, preflight)
    except BaseException as exc:
        if not args.preflight_only:
            preserve_failure(config, config_path, exc)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
