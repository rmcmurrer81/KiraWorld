"""Fail-closed structural audit for Biological Robert static-review candidates.

Run with Blender, not the system Python::

    blender --background --python \
      tools/blender_audit_biological_robert_v23_static_quality.py -- \
      --baseline path/to/V1.blend \
      --source path/to/V23.blend \
      --rendered-evidence path/to/RENDERED_VISUAL_EVIDENCE.json \
      --output path/to/V23_STATIC_QUALITY_AUDIT.json

This audit compares a candidate with the preserved V1 baseline.  It checks
mesh/component continuity, localizes newly introduced non-manifold topology,
rejects a separately attached anatomy object, verifies material and nail
assignments, reads the actual iris shader color, follows the regional skin
tint into the MBLab albedo input, checks preservation of the hand/finger deform
groups, measures unchanged body regions for global-scale evidence, looks for
coarse upper-thigh profile outliers, verifies the removable Stage-A blond hair
contract, and confirms that the candidate remains static and runtime-disabled.

The report is deliberately fail-closed. Structural measurements cannot override
a visible gap, a rejected attachment, or another owner visual rejection.
Rendered evidence must be hash-bound to the exact candidate. The audit records
owner review but does not make a likeness or anatomical-realism judgment itself.
"""

from __future__ import annotations

import argparse
import colorsys
import hashlib
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import bpy


SCHEMA_VERSION = 3
BODY_PREFIX = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_"
HAND_GROUP_PREFIXES = ("hand", "thumb", "index", "middle", "ring", "pinky")
THIGH_Z_FRACTION = (0.20, 0.44)
PELVIS_Z_FRACTION = (0.30, 0.52)
REQUIRED_RENDERED_VIEWS = {
    "front",
    "rear",
    "left_profile",
    "right_profile",
    "left_three_quarter",
    "right_three_quarter",
    "face_close",
    "side_anatomy_placement",
    "front_anatomy_close",
    "three_quarter_anatomy_close",
}


def _parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, help="Preserved V1 .blend")
    parser.add_argument("--source", required=True, help="Candidate .blend")
    parser.add_argument(
        "--rendered-evidence",
        help=(
            "Hash-bound rendered review evidence JSON. If omitted, the audit "
            "looks for RENDERED_VISUAL_EVIDENCE.json beside the candidate."
        ),
    )
    parser.add_argument("--output", required=True, help="JSON report path")
    parser.add_argument(
        "--allow-fail",
        action="store_true",
        help="Return zero after writing a FAIL report (the report still fails).",
    )
    return parser.parse_args(argv)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rendered_evidence_report(
    manifest_path: Path,
    candidate_sha256: str,
) -> dict[str, Any]:
    """Validate the exact render files a visual decision was made against."""

    failures: list[str] = []
    if not manifest_path.is_file():
        return {
            "status": "FAIL",
            "manifest_path": str(manifest_path),
            "manifest_sha256": "",
            "candidate_sha256": candidate_sha256,
            "review_decision": "NOT_RECORDED",
            "pelvis_attachment_status": "NOT_RECORDED",
            "failures": ["RENDERED_VISUAL_EVIDENCE_MANIFEST_MISSING"],
            "hash_bound_rendered_evidence_pass": False,
            "owner_visual_approval_recorded": False,
        }
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "status": "FAIL",
            "manifest_path": str(manifest_path),
            "manifest_sha256": _sha256(manifest_path),
            "candidate_sha256": candidate_sha256,
            "review_decision": "NOT_RECORDED",
            "pelvis_attachment_status": "NOT_RECORDED",
            "failures": ["RENDERED_VISUAL_EVIDENCE_MANIFEST_UNREADABLE"],
            "hash_bound_rendered_evidence_pass": False,
            "owner_visual_approval_recorded": False,
        }
    if not isinstance(manifest, dict):
        manifest = {}
        failures.append("RENDERED_VISUAL_EVIDENCE_MANIFEST_NOT_OBJECT")

    recorded_candidate = str(
        manifest.get("candidate_sha256")
        or manifest.get("candidate_body_sha256")
        or ""
    ).strip().lower()
    if recorded_candidate != candidate_sha256.lower():
        failures.append("RENDERED_EVIDENCE_CANDIDATE_HASH_MISMATCH")

    decision = str(manifest.get("review_decision") or "").strip().upper()
    attachment_status = str(
        manifest.get("pelvis_attachment_status") or ""
    ).strip().upper()
    rejection_reasons = manifest.get("rejection_reasons")
    if not isinstance(rejection_reasons, list):
        rejection_reasons = []
        failures.append("VISUAL_REJECTION_RECORD_INVALID")
    else:
        rejection_reasons = [
            str(reason).strip() for reason in rejection_reasons if str(reason).strip()
        ]
    if rejection_reasons:
        failures.append("VISUAL_REJECTION_RECORDED")
    if decision == "REJECTED_BY_OWNER":
        failures.append("RENDERED_VISUAL_REVIEW_REJECTED_BY_OWNER")
    elif decision not in {"PENDING_OWNER_REVIEW", "APPROVED_BY_OWNER"}:
        failures.append("RENDERED_VISUAL_REVIEW_DECISION_INVALID")
    if manifest.get("pelvis_open_or_spatial_gap_detected") is True:
        failures.append("PELVIS_OPEN_OR_SPATIAL_GAP_VISIBLE")
    elif manifest.get("pelvis_open_or_spatial_gap_detected") is not False:
        failures.append("PELVIS_GAP_VISUAL_DECISION_MISSING")
    if attachment_status == "REJECTED":
        failures.append("PELVIS_ATTACHMENT_VISUALLY_REJECTED")
    elif attachment_status not in {
        "PENDING_OWNER_REVIEW",
        "ACCEPTED_BY_OWNER",
    }:
        failures.append("PELVIS_ATTACHMENT_VISUAL_STATUS_INVALID")
    if decision == "APPROVED_BY_OWNER" and attachment_status != "ACCEPTED_BY_OWNER":
        failures.append("OWNER_APPROVAL_CONTRADICTS_ATTACHMENT_STATUS")

    views = manifest.get("views")
    if not isinstance(views, dict):
        views = {}
        failures.append("RENDERED_VISUAL_VIEW_RECORDS_MISSING")
    missing_views = sorted(REQUIRED_RENDERED_VIEWS.difference(views))
    if missing_views:
        failures.append("RENDERED_VISUAL_REQUIRED_VIEWS_MISSING")

    evidence_root = manifest_path.parent.resolve()
    verified: dict[str, Any] = {}
    verified_hashes: list[str] = []
    for view in sorted(REQUIRED_RENDERED_VIEWS.intersection(views)):
        record = views.get(view)
        if not isinstance(record, dict):
            failures.append(f"RENDERED_VISUAL_VIEW_RECORD_INVALID:{view}")
            continue
        view_candidate_hash = str(
            record.get("candidate_sha256")
            or record.get("candidate_body_sha256")
            or ""
        ).strip().lower()
        if view_candidate_hash != candidate_sha256.lower():
            failures.append(f"RENDERED_VISUAL_VIEW_CANDIDATE_HASH_MISMATCH:{view}")
        path_value = str(record.get("path") or "").strip()
        if not path_value:
            failures.append(f"RENDERED_VISUAL_VIEW_PATH_INVALID:{view}")
            continue
        path = Path(path_value)
        if not path.is_absolute():
            path = evidence_root / path
        try:
            path = path.resolve(strict=True)
            path.relative_to(evidence_root)
        except (FileNotFoundError, ValueError):
            failures.append(f"RENDERED_VISUAL_VIEW_PATH_INVALID:{view}")
            continue
        if not path.is_file():
            failures.append(f"RENDERED_VISUAL_VIEW_PATH_INVALID:{view}")
            continue
        expected_hash = str(record.get("sha256") or "").strip().lower()
        actual_hash = _sha256(path).lower()
        if not expected_hash or expected_hash != actual_hash:
            failures.append(f"RENDERED_VISUAL_VIEW_HASH_MISMATCH:{view}")
            continue
        verified_hashes.append(actual_hash)
        verified[view] = {
            "path": str(path),
            "sha256": actual_hash,
            "candidate_sha256": view_candidate_hash,
        }
    if (
        len(verified_hashes) == len(REQUIRED_RENDERED_VIEWS)
        and len(set(verified_hashes)) != len(REQUIRED_RENDERED_VIEWS)
    ):
        failures.append("RENDERED_VISUAL_VIEWS_NOT_DISTINCT")

    if failures:
        status = "FAIL"
    elif decision == "PENDING_OWNER_REVIEW":
        status = "AWAITING_OWNER_REVIEW"
    else:
        status = "PASS"
    return {
        "status": status,
        "manifest_path": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "candidate_sha256": candidate_sha256,
        "recorded_candidate_sha256": recorded_candidate,
        "review_decision": decision,
        "pelvis_attachment_status": attachment_status,
        "pelvis_open_or_spatial_gap_detected": manifest.get(
            "pelvis_open_or_spatial_gap_detected"
        ),
        "rejection_reasons": rejection_reasons,
        "required_views": sorted(REQUIRED_RENDERED_VIEWS),
        "missing_views": missing_views,
        "verified_views": verified,
        "failures": failures,
        "hash_bound_rendered_evidence_pass": not failures,
        "owner_visual_approval_recorded": (
            not failures
            and decision == "APPROVED_BY_OWNER"
            and attachment_status == "ACCEPTED_BY_OWNER"
        ),
        "rule": (
            "A clean topology report cannot override a visible open/spatial "
            "pelvis gap, rejected attachment, or other rejection in the exact "
            "hash-bound rendered views."
        ),
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        return list(value)
    except Exception:
        return str(value)


def _quantile(values: Iterable[float], fraction: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * max(0.0, min(1.0, fraction))
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _linear_to_srgb(channel: float) -> float:
    value = max(0.0, min(1.0, float(channel)))
    if value <= 0.0031308:
        return 12.92 * value
    return 1.055 * (value ** (1.0 / 2.4)) - 0.055


class _DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = bytearray(size)

    def find(self, value: int) -> int:
        parent = self.parent
        root = value
        while parent[root] != root:
            root = parent[root]
        while parent[value] != value:
            next_value = parent[value]
            parent[value] = root
            value = next_value
        return root

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1


def _find_body() -> tuple[Any, list[str]]:
    named = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.name.startswith(BODY_PREFIX)
    ]
    if named:
        named.sort(key=lambda obj: len(obj.data.vertices), reverse=True)
        return named[0], [obj.name for obj in named]
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("No mesh object exists in the blend file.")
    meshes.sort(key=lambda obj: len(obj.data.vertices), reverse=True)
    return meshes[0], [obj.name for obj in meshes]


def _material_names(body: Any) -> list[str | None]:
    return [material.name if material else None for material in body.data.materials]


def _group_metrics(body: Any) -> dict[str, dict[str, float | int]]:
    metrics: dict[str, dict[str, float | int]] = {}
    for group in body.vertex_groups:
        lowered = group.name.casefold()
        if not lowered.startswith(HAND_GROUP_PREFIXES) and not lowered.startswith("thigh"):
            continue
        members = 0
        weight_sum = 0.0
        for vertex in body.data.vertices:
            for assignment in vertex.groups:
                if assignment.group != group.index:
                    continue
                weight_sum += float(assignment.weight)
                if assignment.weight > 0.001:
                    members += 1
                break
        metrics[group.name] = {
            "members_above_0_001": members,
            "weight_sum": round(weight_sum, 6),
            "member_fraction": round(members / max(1, len(body.data.vertices)), 9),
            "weight_fraction": round(weight_sum / max(1, len(body.data.vertices)), 9),
        }
    return metrics


def _base_color(material: Any) -> dict[str, Any] | None:
    if not material or not material.use_nodes or not material.node_tree:
        return None
    principled = next(
        (node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"),
        None,
    )
    if principled is None:
        return None
    socket = principled.inputs.get("Base Color")
    if socket is None:
        return None
    linear = tuple(float(value) for value in socket.default_value[:3])
    srgb = tuple(_linear_to_srgb(value) for value in linear)
    hue, saturation, value = colorsys.rgb_to_hsv(*srgb)
    return {
        "linear_rgb": [round(value, 6) for value in linear],
        "srgb": [round(value, 6) for value in srgb],
        "hue_degrees": round(hue * 360.0, 3),
        "saturation": round(saturation, 6),
        "value": round(value, 6),
        "base_color_is_linked": bool(socket.is_linked),
    }


def _object_transform_snapshot(obj: Any) -> dict[str, Any]:
    """Record the actual object transform without relying on author metadata."""

    return {
        "location": [round(float(value), 8) for value in obj.location],
        "rotation_euler": [round(float(value), 8) for value in obj.rotation_euler],
        "scale": [round(float(value), 8) for value in obj.scale],
        "dimensions": [round(float(value), 8) for value in obj.dimensions],
        "matrix_world_determinant": round(float(obj.matrix_world.determinant()), 9),
    }


def _mesh_component_snapshot(body: Any) -> dict[str, Any]:
    """List scene mesh components and flag any separately attached anatomy.

    Object names and material names are enough for this structural audit.  No
    protected image paths, reference filenames, or raw reference data are
    included in the report.
    """

    components = []
    separate_anatomy = []
    anatomy_tokens = (
        "external_anatomy",
        "separate_anatomy",
        "genital",
        "penis",
        "scrot",
    )
    for obj in sorted(
        (item for item in bpy.context.scene.objects if item.type == "MESH"),
        key=lambda item: item.name.casefold(),
    ):
        material_names = [
            material.name if material else None for material in obj.data.materials
        ]
        lowered = " ".join(
            [obj.name.casefold()]
            + [(name or "").casefold() for name in material_names]
        )
        if obj == body:
            classification = "integrated_body"
        elif "hair" in lowered or obj.get("stage_a_static_review_only"):
            classification = "removable_static_hair"
        elif "iris" in lowered:
            classification = "separate_eye_iris"
        elif "pupil" in lowered:
            classification = "separate_eye_pupil"
        elif any(token in lowered for token in anatomy_tokens):
            classification = "forbidden_separate_anatomy"
            separate_anatomy.append(obj.name)
        else:
            classification = "other_mesh_component"
        components.append(
            {
                "name": obj.name,
                "classification": classification,
                "vertices": len(obj.data.vertices),
                "polygons": len(obj.data.polygons),
                "materials": material_names,
                "parent": obj.parent.name if obj.parent else None,
                "parent_type": obj.parent.type if obj.parent else None,
                "hidden_render": bool(obj.hide_render),
                "transform": _object_transform_snapshot(obj),
            }
        )
    return {
        "mesh_object_count": len(components),
        "objects": components,
        "forbidden_separate_anatomy_objects": separate_anatomy,
    }


def _iris_snapshot(body: Any) -> dict[str, Any]:
    """Inspect the actual iris mesh materials, not lighting or metadata alone."""

    iris_objects = []
    for obj in bpy.context.scene.objects:
        if obj == body or obj.type != "MESH":
            continue
        material_names = [
            material.name if material else None for material in obj.data.materials
        ]
        if "iris" not in obj.name.casefold() and not any(
            "iris" in (name or "").casefold() for name in material_names
        ):
            continue
        used_indices = {int(polygon.material_index) for polygon in obj.data.polygons}
        material_details = []
        for index, material in enumerate(obj.data.materials):
            if index not in used_indices:
                continue
            material_details.append(
                {
                    "slot": index,
                    "name": material.name if material else None,
                    "base_color": _base_color(material),
                }
            )
        iris_objects.append(
            {
                "name": obj.name,
                "vertices": len(obj.data.vertices),
                "used_materials": material_details,
                "actual_iris_color_property": _json_value(
                    obj.get("actual_iris_color")
                ),
            }
        )
    return {"objects": iris_objects}


def _regional_skin_snapshot(body: Any) -> dict[str, Any]:
    """Prove the regional tint is connected to the real skin albedo path."""

    mix_attribute = body.data.attributes.get("V23_Regional_Mix")
    tint_attribute = body.data.color_attributes.get("V23_Regional_Skin_Tint")
    mix_values: list[float] = []
    if mix_attribute is not None and hasattr(mix_attribute, "data"):
        for item in mix_attribute.data:
            if hasattr(item, "value"):
                mix_values.append(float(item.value))
    tint_values: list[tuple[float, float, float, float]] = []
    if tint_attribute is not None:
        for item in tint_attribute.data:
            tint_values.append(tuple(float(value) for value in item.color))

    skin_material = next(
        (
            material
            for material in body.data.materials
            if material
            and "skin" in material.name.casefold()
            and material.use_nodes
            and material.node_tree
        ),
        None,
    )
    graph = {
        "skin_material": skin_material.name if skin_material else None,
        "tint_node_exists": False,
        "tint_node_layer": None,
        "multiply_node_exists": False,
        "multiply_blend_type": None,
        "tint_to_multiply": False,
        "multiply_to_mblab_albedo": False,
        "preexisting_albedo_to_multiply": False,
        "target_group": None,
        "target_socket": None,
    }
    if skin_material is not None:
        nodes = skin_material.node_tree.nodes
        links = skin_material.node_tree.links
        tint_node = nodes.get("V23_Regional_Skin_Tint")
        multiply_node = nodes.get("V23_Regional_Skin_Multiply")
        group_node = next(
            (
                node
                for node in nodes
                if node.type == "GROUP" and node.inputs.get("Albedo Map") is not None
            ),
            None,
        )
        graph.update(
            {
                "tint_node_exists": tint_node is not None,
                "tint_node_layer": (
                    getattr(tint_node, "layer_name", None) if tint_node else None
                ),
                "multiply_node_exists": multiply_node is not None,
                "multiply_blend_type": (
                    getattr(multiply_node, "blend_type", None)
                    if multiply_node
                    else None
                ),
                "target_group": group_node.name if group_node else None,
                "target_socket": "Albedo Map" if group_node else None,
            }
        )
        if tint_node is not None and multiply_node is not None:
            graph["tint_to_multiply"] = any(
                link.from_node == tint_node and link.to_node == multiply_node
                for link in links
            )
            graph["preexisting_albedo_to_multiply"] = any(
                link.to_node == multiply_node and link.from_node != tint_node
                for link in links
            )
        if multiply_node is not None and group_node is not None:
            graph["multiply_to_mblab_albedo"] = any(
                link.from_node == multiply_node
                and link.to_node == group_node
                and link.to_socket.name == "Albedo Map"
                for link in links
            )

    nonzero_mix = sum(value > 1e-6 for value in mix_values)
    non_neutral_tint = sum(
        max(abs(value[index] - 1.0) for index in range(3)) > 1e-4
        for value in tint_values
    )
    return {
        "regional_mix_attribute": {
            "exists": mix_attribute is not None,
            "domain": mix_attribute.domain if mix_attribute else None,
            "data_type": mix_attribute.data_type if mix_attribute else None,
            "element_count": len(mix_values),
            "nonzero_elements": nonzero_mix,
            "minimum": round(min(mix_values), 8) if mix_values else None,
            "maximum": round(max(mix_values), 8) if mix_values else None,
        },
        "regional_tint_attribute": {
            "exists": tint_attribute is not None,
            "domain": tint_attribute.domain if tint_attribute else None,
            "data_type": tint_attribute.data_type if tint_attribute else None,
            "element_count": len(tint_values),
            "non_neutral_elements": non_neutral_tint,
        },
        "shader_graph": graph,
    }


def _hair_snapshot(body: Any) -> dict[str, Any]:
    hair_objects = []
    for obj in bpy.context.scene.objects:
        if obj == body or obj.type != "MESH":
            continue
        material_names = [material.name if material else None for material in obj.data.materials]
        is_hair = bool(
            obj.get("stage_a_static_review_only")
            or "hair" in obj.name.casefold()
            or any("hair" in (name or "").casefold() for name in material_names)
        )
        if not is_hair:
            continue
        material_details = []
        for material in obj.data.materials:
            material_details.append(
                {
                    "name": material.name if material else None,
                    "base_color": _base_color(material),
                }
            )
        parent_armature = bool(obj.parent and obj.parent.type == "ARMATURE")
        armature_modifiers = [
            modifier.name for modifier in obj.modifiers if modifier.type == "ARMATURE"
        ]
        hair_objects.append(
            {
                "name": obj.name,
                "vertices": len(obj.data.vertices),
                "materials": material_details,
                "stage_a_static_review_only": obj.get("stage_a_static_review_only"),
                "runtime_groom_complete": obj.get("runtime_groom_complete"),
                "separate_removable_object": obj != body,
                "parent_armature": parent_armature,
                "armature_modifiers": armature_modifiers,
            }
        )
    return {
        "objects": hair_objects,
        "body_hair_status_property": _json_value(body.get("hair_status")),
    }


def _active_animation_snapshot(body: Any) -> dict[str, Any]:
    animated_objects = []
    for obj in bpy.context.scene.objects:
        animation_data = obj.animation_data
        if not animation_data:
            continue
        action = animation_data.action
        nla_track_count = len(animation_data.nla_tracks)
        drivers = len(animation_data.drivers)
        if action or nla_track_count or drivers:
            animated_objects.append(
                {
                    "name": obj.name,
                    "type": obj.type,
                    "action": action.name if action else None,
                    "nla_tracks": nla_track_count,
                    "drivers": drivers,
                }
            )
    armature_objects = [
        {
            "name": obj.name,
            "parented_body": body.parent == obj,
            "action": (
                obj.animation_data.action.name
                if obj.animation_data and obj.animation_data.action
                else None
            ),
        }
        for obj in bpy.context.scene.objects
        if obj.type == "ARMATURE"
    ]
    return {
        "body_armature_modifiers": [
            modifier.name for modifier in body.modifiers if modifier.type == "ARMATURE"
        ],
        "body_parent_armature": bool(body.parent and body.parent.type == "ARMATURE"),
        "armature_objects": armature_objects,
        "animated_objects": animated_objects,
        "runtime_activation_allowed": _json_value(body.get("runtime_activation_allowed")),
        "movement_started": _json_value(body.get("movement_started")),
        "movement_claimed": _json_value(body.get("movement_claimed")),
        "static_review_only": _json_value(body.get("static_review_only")),
    }


def _classify_region(
    x: float,
    y: float,
    z: float,
    bounds: dict[str, float],
) -> str:
    width = bounds["x_max"] - bounds["x_min"]
    height = bounds["z_max"] - bounds["z_min"]
    z_fraction = (z - bounds["z_min"]) / max(height, 1e-9)
    x_center = (bounds["x_min"] + bounds["x_max"]) * 0.5
    y_center = (bounds["y_min"] + bounds["y_max"]) * 0.5
    if (
        PELVIS_Z_FRACTION[0] <= z_fraction <= PELVIS_Z_FRACTION[1]
        and abs(x - x_center) <= width * 0.21
        and y <= y_center + (bounds["y_max"] - bounds["y_min"]) * 0.13
    ):
        return "pelvis_local_repair_roi"
    if z_fraction >= 0.76:
        return "head_and_neck"
    if z_fraction <= 0.18:
        return "lower_legs_and_feet"
    if abs(x - x_center) > width * 0.30:
        return "arms_and_hands"
    return "torso_and_nonrepair_body"


def _topology_snapshot(body: Any) -> dict[str, Any]:
    bpy.context.scene.frame_set(1)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    try:
        vertex_count = len(mesh.vertices)
        edge_count = len(mesh.edges)
        polygon_count = len(mesh.polygons)
        coordinates = [vertex.co.copy() for vertex in mesh.vertices]
        bounds = {
            "x_min": min(value.x for value in coordinates),
            "x_max": max(value.x for value in coordinates),
            "y_min": min(value.y for value in coordinates),
            "y_max": max(value.y for value in coordinates),
            "z_min": min(value.z for value in coordinates),
            "z_max": max(value.z for value in coordinates),
        }

        disjoint = _DisjointSet(vertex_count)
        for edge in mesh.edges:
            left, right = edge.vertices
            disjoint.union(int(left), int(right))
        component_counts = Counter(disjoint.find(index) for index in range(vertex_count))
        largest_root, largest_size = component_counts.most_common(1)[0]

        edge_face_counts = [0] * edge_count
        for loop in mesh.loops:
            edge_face_counts[loop.edge_index] += 1

        anomaly_regions: dict[str, Counter[str]] = {
            "boundary": Counter(),
            "multi_face": Counter(),
            "all_nonmanifold": Counter(),
        }
        main_anomaly_regions: dict[str, Counter[str]] = {
            "boundary": Counter(),
            "multi_face": Counter(),
            "all_nonmanifold": Counter(),
        }
        for edge, face_count in zip(mesh.edges, edge_face_counts):
            if face_count == 2:
                continue
            left, right = (int(value) for value in edge.vertices)
            midpoint = (coordinates[left] + coordinates[right]) * 0.5
            region = _classify_region(midpoint.x, midpoint.y, midpoint.z, bounds)
            kind = "boundary" if face_count <= 1 else "multi_face"
            anomaly_regions[kind][region] += 1
            anomaly_regions["all_nonmanifold"][region] += 1
            if disjoint.find(left) == largest_root and disjoint.find(right) == largest_root:
                main_anomaly_regions[kind][region] += 1
                main_anomaly_regions["all_nonmanifold"][region] += 1

        material_names = _material_names(body)
        invalid_material_polygons = []
        used_materials: Counter[int] = Counter()
        nail_indices = {
            index
            for index, name in enumerate(material_names)
            if name and "nail" in name.casefold()
        }
        nail_vertices: set[int] = set()
        nail_disjoint = _DisjointSet(vertex_count)
        nail_polygon_count = 0
        for polygon in mesh.polygons:
            material_index = int(polygon.material_index)
            if material_index < 0 or material_index >= len(material_names):
                if len(invalid_material_polygons) < 50:
                    invalid_material_polygons.append(int(polygon.index))
                continue
            used_materials[material_index] += 1
            if material_index in nail_indices:
                nail_polygon_count += 1
                polygon_vertices = [int(index) for index in polygon.vertices]
                nail_vertices.update(polygon_vertices)
                for left, right in zip(
                    polygon_vertices,
                    polygon_vertices[1:] + polygon_vertices[:1],
                ):
                    nail_disjoint.union(left, right)
        # Count material islands using only nail polygons.  The full body
        # component graph would collapse every attached fingernail/toenail into
        # the skin root and incorrectly report one component.
        nail_component_roots = {
            nail_disjoint.find(index) for index in nail_vertices
        }

        x_center = (bounds["x_min"] + bounds["x_max"]) * 0.5
        y_center = (bounds["y_min"] + bounds["y_max"]) * 0.5
        width = bounds["x_max"] - bounds["x_min"]
        height = bounds["z_max"] - bounds["z_min"]
        pelvis_vertices = [
            index
            for index, coordinate in enumerate(coordinates)
            if (
                PELVIS_Z_FRACTION[0]
                <= (coordinate.z - bounds["z_min"]) / max(height, 1e-9)
                <= PELVIS_Z_FRACTION[1]
                and abs(coordinate.x - x_center) <= width * 0.21
                and coordinate.y
                <= y_center + (bounds["y_max"] - bounds["y_min"]) * 0.13
            )
        ]
        pelvis_main_count = sum(
            1 for index in pelvis_vertices if disjoint.find(index) == largest_root
        )

        thigh_profile = _thigh_profile(coordinates, bounds, largest_root, disjoint)
        return {
            "evaluated_vertices": vertex_count,
            "evaluated_edges": edge_count,
            "evaluated_polygons": polygon_count,
            "bounds": {key: round(value, 8) for key, value in bounds.items()},
            "connected_components": len(component_counts),
            "largest_component_vertices": largest_size,
            "largest_component_fraction": round(largest_size / max(1, vertex_count), 9),
            "component_vertex_counts_top_25": [
                count for _, count in component_counts.most_common(25)
            ],
            "anomaly_regions": {
                kind: dict(sorted(counts.items()))
                for kind, counts in anomaly_regions.items()
            },
            "main_component_anomaly_regions": {
                kind: dict(sorted(counts.items()))
                for kind, counts in main_anomaly_regions.items()
            },
            "pelvis_roi_vertices": len(pelvis_vertices),
            "pelvis_roi_vertices_in_main_component": pelvis_main_count,
            "pelvis_roi_main_component_fraction": round(
                pelvis_main_count / max(1, len(pelvis_vertices)), 9
            ),
            "materials": {
                "slots": material_names,
                "invalid_material_polygon_count": len(invalid_material_polygons),
                "invalid_material_polygon_examples": invalid_material_polygons,
                "used_polygon_counts": {
                    str(index): count for index, count in sorted(used_materials.items())
                },
                "none_material_slots_used": [
                    index
                    for index in used_materials
                    if index >= len(material_names) or material_names[index] is None
                ],
            },
            "nails": {
                "material_slot_indices": sorted(nail_indices),
                "material_names": [
                    material_names[index] for index in sorted(nail_indices)
                ],
                "polygon_count": nail_polygon_count,
                "vertex_count": len(nail_vertices),
                "connected_components": len(nail_component_roots),
            },
            "thigh_profile": thigh_profile,
        }
    finally:
        evaluated.to_mesh_clear()


def _preserved_region_snapshot(body: Any) -> dict[str, Any]:
    """Measure regions outside the local repair to detect baked global scaling."""

    bpy.context.scene.frame_set(1)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    try:
        coordinates = [vertex.co.copy() for vertex in mesh.vertices]
        x_values = [value.x for value in coordinates]
        y_values = [value.y for value in coordinates]
        z_values = [value.z for value in coordinates]
        bounds = {
            "x_min": min(x_values),
            "x_max": max(x_values),
            "y_min": min(y_values),
            "y_max": max(y_values),
            "z_min": min(z_values),
            "z_max": max(z_values),
        }
        width = bounds["x_max"] - bounds["x_min"]
        height = bounds["z_max"] - bounds["z_min"]
        x_center = (bounds["x_min"] + bounds["x_max"]) * 0.5
        regions = {
            "lower_legs_and_feet": [
                value
                for value in coordinates
                if (value.z - bounds["z_min"]) / max(height, 1e-9) <= 0.18
            ],
            "distal_hands": [
                value
                for value in coordinates
                if (
                    abs(value.x - x_center) >= width * 0.40
                    and 0.32
                    <= (value.z - bounds["z_min"]) / max(height, 1e-9)
                    <= 0.74
                )
            ],
        }
        result: dict[str, Any] = {
            "whole_body": {
                "robust_x_span_q998": round(
                    _quantile(x_values, 0.999) - _quantile(x_values, 0.001), 8
                ),
                "robust_y_span_q998": round(
                    _quantile(y_values, 0.999) - _quantile(y_values, 0.001), 8
                ),
                "robust_z_span_q998": round(
                    _quantile(z_values, 0.999) - _quantile(z_values, 0.001), 8
                ),
                "exact_z_span": round(height, 8),
            }
        }
        for name, values in regions.items():
            axes = {
                "x": [value.x for value in values],
                "y": [value.y for value in values],
                "z": [value.z for value in values],
            }
            result[name] = {
                "vertices": len(values),
                "median": {
                    axis: round(statistics.median(numbers), 8)
                    if numbers
                    else None
                    for axis, numbers in axes.items()
                },
                "robust_span_q98": {
                    axis: round(
                        _quantile(numbers, 0.99) - _quantile(numbers, 0.01), 8
                    )
                    if numbers
                    else None
                    for axis, numbers in axes.items()
                },
            }
        return result
    finally:
        evaluated.to_mesh_clear()


def _thigh_profile(
    coordinates: list[Any],
    bounds: dict[str, float],
    main_root: int,
    disjoint: _DisjointSet,
    bins: int = 18,
) -> dict[str, Any]:
    height = bounds["z_max"] - bounds["z_min"]
    width = bounds["x_max"] - bounds["x_min"]
    x_center = (bounds["x_min"] + bounds["x_max"]) * 0.5
    z_lower = bounds["z_min"] + height * THIGH_Z_FRACTION[0]
    z_upper = bounds["z_min"] + height * THIGH_Z_FRACTION[1]
    # Keep the protected central repair surface out of the thigh-tail metric.
    # The upper-leg audit starts laterally enough to measure the actual thighs,
    # not the newly authored midline anatomy.
    center_exclusion = width * 0.075
    outer_limit = width * 0.34
    profiles: dict[str, list[dict[str, float | int]]] = {"left": [], "right": []}

    for bin_index in range(bins):
        low = z_lower + (z_upper - z_lower) * bin_index / bins
        high = z_lower + (z_upper - z_lower) * (bin_index + 1) / bins
        for side, sign in (("left", 1.0), ("right", -1.0)):
            points = []
            for index, coordinate in enumerate(coordinates):
                if disjoint.find(index) != main_root or not (low <= coordinate.z < high):
                    continue
                offset = (coordinate.x - x_center) * sign
                if center_exclusion < offset < outer_limit:
                    points.append((coordinate.x, coordinate.y))
            if len(points) < 20:
                profiles[side].append(
                    {
                        "bin": bin_index,
                        "samples": len(points),
                        "width_q96": 0.0,
                        "depth_q96": 0.0,
                        "outer_tail": 0.0,
                    }
                )
                continue
            x_values = [point[0] for point in points]
            y_values = [point[1] for point in points]
            x_low = _quantile(x_values, 0.02)
            x_high = _quantile(x_values, 0.98)
            y_low = _quantile(y_values, 0.02)
            y_high = _quantile(y_values, 0.98)
            robust_width = x_high - x_low
            robust_depth = y_high - y_low
            x_span = max(x_values) - min(x_values)
            y_span = max(y_values) - min(y_values)
            tail = max(
                x_span / max(robust_width, 1e-9),
                y_span / max(robust_depth, 1e-9),
            )
            profiles[side].append(
                {
                    "bin": bin_index,
                    "samples": len(points),
                    "width_q96": round(robust_width, 8),
                    "depth_q96": round(robust_depth, 8),
                    "outer_tail": round(tail, 6),
                }
            )
    return {
        "z_fraction_range": list(THIGH_Z_FRACTION),
        "bins": bins,
        "profiles": profiles,
    }


def _snapshot(path: Path) -> dict[str, Any]:
    bpy.ops.wm.open_mainfile(filepath=str(path))
    body, body_candidates = _find_body()
    raw_properties = {
        key: _json_value(body.get(key))
        for key in (
            "status",
            "runtime_activation_allowed",
            "movement_started",
            "movement_claimed",
            "static_review_only",
            "hair_status",
            "regional_skin_variation",
            "global_scaling_used",
            "boolean_used",
            "donor_surface_transferred",
            "method",
        )
    }
    return {
        "file_name": path.name,
        "sha256": _sha256(path),
        "body_object": body.name,
        "body_detection_candidates": body_candidates,
        "raw_vertices": len(body.data.vertices),
        "raw_polygons": len(body.data.polygons),
        "raw_modifiers": [
            {"name": modifier.name, "type": modifier.type}
            for modifier in body.modifiers
        ],
        "raw_properties": raw_properties,
        "body_transform": _object_transform_snapshot(body),
        "mesh_components": _mesh_component_snapshot(body),
        "iris": _iris_snapshot(body),
        "regional_skin": _regional_skin_snapshot(body),
        "preserved_regions": _preserved_region_snapshot(body),
        "group_metrics": _group_metrics(body),
        "hair": _hair_snapshot(body),
        "static_runtime": _active_animation_snapshot(body),
        "topology": _topology_snapshot(body),
    }


def _sum_regions(regions: dict[str, int], exclude_pelvis: bool) -> int:
    return sum(
        int(count)
        for region, count in regions.items()
        if not exclude_pelvis or region != "pelvis_local_repair_roi"
    )


def _compare_topology(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    base_topology = baseline["topology"]
    candidate_topology = candidate["topology"]
    base_regions = base_topology["main_component_anomaly_regions"]
    candidate_regions = candidate_topology["main_component_anomaly_regions"]
    details: dict[str, Any] = {}
    strict_no_new_anomalies = True
    localization_pass = True

    for kind in ("boundary", "multi_face", "all_nonmanifold"):
        base_all = _sum_regions(base_regions[kind], exclude_pelvis=False)
        candidate_all = _sum_regions(candidate_regions[kind], exclude_pelvis=False)
        base_nonpelvis = _sum_regions(base_regions[kind], exclude_pelvis=True)
        candidate_nonpelvis = _sum_regions(
            candidate_regions[kind], exclude_pelvis=True
        )
        base_pelvis = int(base_regions[kind].get("pelvis_local_repair_roi", 0))
        candidate_pelvis = int(
            candidate_regions[kind].get("pelvis_local_repair_roi", 0)
        )
        total_delta = candidate_all - base_all
        pelvis_delta = candidate_pelvis - base_pelvis
        nonpelvis_delta = candidate_nonpelvis - base_nonpelvis
        permitted_nonpelvis_delta = max(4, int(math.ceil(base_nonpelvis * 0.01)))
        kind_localization_pass = nonpelvis_delta <= permitted_nonpelvis_delta
        if total_delta > 0:
            positive_pelvis_share = max(0, pelvis_delta) / max(1, total_delta)
            kind_localization_pass = (
                kind_localization_pass and positive_pelvis_share >= 0.95
            )
        else:
            positive_pelvis_share = 1.0
        kind_strict_pass = total_delta <= 0
        localization_pass = localization_pass and kind_localization_pass
        strict_no_new_anomalies = strict_no_new_anomalies and kind_strict_pass
        details[kind] = {
            "baseline_main_component": base_all,
            "candidate_main_component": candidate_all,
            "baseline_regions": dict(sorted(base_regions[kind].items())),
            "candidate_regions": dict(sorted(candidate_regions[kind].items())),
            "total_delta": total_delta,
            "baseline_pelvis_roi": base_pelvis,
            "candidate_pelvis_roi": candidate_pelvis,
            "pelvis_delta": pelvis_delta,
            "baseline_nonpelvis": base_nonpelvis,
            "candidate_nonpelvis": candidate_nonpelvis,
            "nonpelvis_delta": nonpelvis_delta,
            "permitted_nonpelvis_delta": permitted_nonpelvis_delta,
            "positive_delta_localized_to_pelvis_fraction": round(
                positive_pelvis_share, 6
            ),
            "localized_to_pelvis_pass": kind_localization_pass,
            "no_new_anomaly_pass": kind_strict_pass,
        }

    candidate_membership = (
        candidate_topology["pelvis_roi_vertices"] > 0
        and candidate_topology["pelvis_roi_main_component_fraction"] >= 0.999
    )
    return {
        "status": (
            "PASS"
            if candidate_membership and localization_pass and strict_no_new_anomalies
            else "FAIL"
        ),
        "main_body_component_membership_pass": candidate_membership,
        "pelvis_roi_main_component_fraction": candidate_topology[
            "pelvis_roi_main_component_fraction"
        ],
        "new_anomaly_delta_localized_to_pelvis_pass": localization_pass,
        "strict_no_new_nonmanifold_or_boundary_edges_pass": strict_no_new_anomalies,
        "delta": details,
        "interpretation": (
            "A localized delta identifies where a defect was introduced; it does "
            "not make new non-manifold topology acceptable."
        ),
    }


def _compare_materials_and_nails(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    base_materials = baseline["topology"]["materials"]
    candidate_materials = candidate["topology"]["materials"]
    base_nails = baseline["topology"]["nails"]
    candidate_nails = candidate["topology"]["nails"]
    required_materials = {
        name
        for name in base_materials["slots"]
        if name is not None
    }
    candidate_material_names = {
        name
        for name in candidate_materials["slots"]
        if name is not None
    }
    missing_materials = sorted(required_materials - candidate_material_names)
    material_pass = (
        candidate_materials["invalid_material_polygon_count"] == 0
        and not candidate_materials["none_material_slots_used"]
        and not missing_materials
    )
    nail_polygon_delta = (
        candidate_nails["polygon_count"] - base_nails["polygon_count"]
    )
    nail_polygon_tolerance = max(
        8, int(math.ceil(base_nails["polygon_count"] * 0.02))
    )
    nail_component_pass = (
        base_nails["connected_components"] == 20
        and candidate_nails["connected_components"] == 20
    )
    nail_pass = (
        nail_component_pass
        and candidate_nails["polygon_count"] > 0
        and abs(nail_polygon_delta) <= nail_polygon_tolerance
        and any(
            name and "nail" in name.casefold()
            for name in candidate_nails["material_names"]
        )
    )
    return {
        "status": "PASS" if material_pass and nail_pass else "FAIL",
        "material_index_validity_pass": material_pass,
        "missing_baseline_materials": missing_materials,
        "baseline": base_materials,
        "candidate": candidate_materials,
        "nails_20_components_and_material_pass": nail_pass,
        "nails_20_material_islands_pass": nail_component_pass,
        "nail_polygon_delta": nail_polygon_delta,
        "nail_polygon_delta_tolerance": nail_polygon_tolerance,
        "baseline_nails": base_nails,
        "candidate_nails": candidate_nails,
    }


def _evaluate_components(candidate: dict[str, Any]) -> dict[str, Any]:
    snapshot = candidate["mesh_components"]
    classifications = Counter(
        item["classification"] for item in snapshot["objects"]
    )
    failures = []
    if classifications["integrated_body"] != 1:
        failures.append("INTEGRATED_BODY_OBJECT_COUNT_NOT_ONE")
    if snapshot["forbidden_separate_anatomy_objects"]:
        failures.append("SEPARATE_ANATOMY_OBJECT_PRESENT")
    return {
        "status": "PASS" if not failures else "FAIL",
        **snapshot,
        "classification_counts": dict(sorted(classifications.items())),
        "interpretation": (
            "Hair and eye parts may be removable/separate components. The locally "
            "rebuilt adult anatomy must belong to the one integrated body mesh; "
            "a separately floating or attached anatomy object fails."
        ),
        "failures": failures,
        "one_integrated_body_no_separate_anatomy_gate_pass": not failures,
    }


def _evaluate_iris(candidate: dict[str, Any]) -> dict[str, Any]:
    objects = candidate["iris"]["objects"]
    failures = []
    evaluated_colors = []
    if len(objects) < 2:
        failures.append("FEWER_THAN_TWO_IRIS_OBJECTS")
    for obj in objects:
        if not obj["used_materials"]:
            failures.append(f"{obj['name']}:NO_USED_IRIS_MATERIAL")
            continue
        object_has_actual_blue = False
        for material in obj["used_materials"]:
            color = material["base_color"]
            name = material["name"] or ""
            if not color:
                failures.append(f"{obj['name']}:{name}:NO_PRINCIPLED_BASE_COLOR")
                continue
            evaluated_colors.append(
                {"object": obj["name"], "material": name, **color}
            )
            hue = float(color["hue_degrees"])
            saturation = float(color["saturation"])
            value = float(color["value"])
            plausible_natural_blue = (
                180.0 <= hue <= 250.0
                and 0.20 <= saturation <= 0.90
                and 0.12 <= value <= 0.85
            )
            actual_unlinked_color = not bool(color["base_color_is_linked"])
            if plausible_natural_blue and actual_unlinked_color:
                object_has_actual_blue = True
            else:
                if not plausible_natural_blue:
                    failures.append(
                        f"{obj['name']}:{name}:BASE_COLOR_NOT_NATURAL_BLUE_RANGE"
                    )
                if not actual_unlinked_color:
                    failures.append(
                        f"{obj['name']}:{name}:BASE_COLOR_LINKED_NOT_DIRECTLY_VERIFIED"
                    )
        if not object_has_actual_blue:
            failures.append(f"{obj['name']}:NO_ACTUAL_BLUE_IRIS_SHADER")
    return {
        "status": "PASS" if not failures else "FAIL",
        "objects": objects,
        "evaluated_shader_colors": evaluated_colors,
        "method": (
            "Reads the used Principled Base Color on each iris mesh. A blue-looking "
            "reflection, lamp, world color, exposure change, or metadata string "
            "cannot satisfy this material gate."
        ),
        "neutral_render_pixel_review": "SEPARATE VISUAL REVIEW REQUIRED",
        "failures": sorted(set(failures)),
        "actual_blue_iris_material_gate_pass": not failures,
    }


def _evaluate_regional_skin(candidate: dict[str, Any]) -> dict[str, Any]:
    snapshot = candidate["regional_skin"]
    mix = snapshot["regional_mix_attribute"]
    tint = snapshot["regional_tint_attribute"]
    graph = snapshot["shader_graph"]
    failures = []
    if not mix["exists"] or mix["element_count"] <= 0:
        failures.append("REGIONAL_MIX_ATTRIBUTE_MISSING")
    elif mix["nonzero_elements"] <= 0 or (mix["maximum"] or 0.0) <= 0.0:
        failures.append("REGIONAL_MIX_ATTRIBUTE_EMPTY")
    if not tint["exists"] or tint["element_count"] <= 0:
        failures.append("REGIONAL_TINT_COLOR_ATTRIBUTE_MISSING")
    elif tint["non_neutral_elements"] <= 0:
        failures.append("REGIONAL_TINT_CONTAINS_NO_COLOR_VARIATION")
    if not graph["skin_material"]:
        failures.append("SKIN_NODE_MATERIAL_NOT_FOUND")
    if not graph["tint_node_exists"]:
        failures.append("REGIONAL_TINT_SHADER_NODE_MISSING")
    if graph["tint_node_layer"] != "V23_Regional_Skin_Tint":
        failures.append("REGIONAL_TINT_NODE_USES_WRONG_LAYER")
    if not graph["multiply_node_exists"] or graph["multiply_blend_type"] != "MULTIPLY":
        failures.append("REGIONAL_MULTIPLY_NODE_MISSING_OR_WRONG_BLEND")
    if not graph["tint_to_multiply"]:
        failures.append("REGIONAL_TINT_NOT_LINKED_TO_MULTIPLY")
    if not graph["preexisting_albedo_to_multiply"]:
        failures.append("ORIGINAL_SKIN_ALBEDO_NOT_PRESERVED_AS_MULTIPLY_INPUT")
    if not graph["multiply_to_mblab_albedo"]:
        failures.append("REGIONAL_MULTIPLY_NOT_LINKED_TO_MBLAB_ALBEDO")
    return {
        "status": "PASS" if not failures else "FAIL",
        **snapshot,
        "method": (
            "Verifies non-neutral mesh color data and follows the named tint "
            "multiply node into the MBLab skin group's Albedo Map input. AO, "
            "cavity, roughness, or a disconnected node cannot satisfy this gate."
        ),
        "appearance_review": (
            "Automated linkage does not certify subtle or natural-looking skin; "
            "neutral-light protected renders still require owner review."
        ),
        "failures": failures,
        "regional_skin_real_albedo_path_gate_pass": not failures,
    }


def _evaluate_local_only_deformation(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    baseline_transform = baseline["body_transform"]
    candidate_transform = candidate["body_transform"]
    base_regions = baseline["preserved_regions"]
    candidate_regions = candidate["preserved_regions"]
    failures = []

    transform_delta = {
        key: [
            round(float(candidate_transform[key][index]) - float(value), 9)
            for index, value in enumerate(baseline_transform[key])
        ]
        for key in ("location", "rotation_euler", "scale")
    }
    if any(abs(value) > 1e-6 for value in transform_delta["scale"]):
        failures.append("BODY_OBJECT_SCALE_CHANGED")
    if any(abs(value) > 1e-6 for value in transform_delta["location"]):
        failures.append("BODY_OBJECT_LOCATION_CHANGED")
    if any(abs(value) > 1e-6 for value in transform_delta["rotation_euler"]):
        failures.append("BODY_OBJECT_ROTATION_CHANGED")

    whole_z_ratio = (
        float(candidate_regions["whole_body"]["exact_z_span"])
        / max(1e-9, float(base_regions["whole_body"]["exact_z_span"]))
    )
    if not 0.995 <= whole_z_ratio <= 1.005:
        failures.append("WHOLE_BODY_HEIGHT_CHANGED_LIKE_GLOBAL_SCALE")

    preserved_region_ratios: dict[str, Any] = {}
    for region_name, tolerance in (
        ("lower_legs_and_feet", 0.015),
        ("distal_hands", 0.025),
    ):
        base_region = base_regions[region_name]
        candidate_region = candidate_regions[region_name]
        ratios = {}
        median_deltas = {}
        for axis in ("x", "y", "z"):
            base_span = base_region["robust_span_q98"][axis]
            candidate_span = candidate_region["robust_span_q98"][axis]
            ratios[axis] = (
                round(float(candidate_span) / max(1e-9, float(base_span)), 8)
                if base_span is not None and candidate_span is not None
                else None
            )
            base_median = base_region["median"][axis]
            candidate_median = candidate_region["median"][axis]
            median_deltas[axis] = (
                round(float(candidate_median) - float(base_median), 8)
                if base_median is not None and candidate_median is not None
                else None
            )
        preserved_region_ratios[region_name] = {
            "baseline_vertices": base_region["vertices"],
            "candidate_vertices": candidate_region["vertices"],
            "robust_span_ratios": ratios,
            "median_deltas": median_deltas,
            "allowed_span_delta_fraction": tolerance,
        }
        if any(
            ratio is None or not (1.0 - tolerance <= ratio <= 1.0 + tolerance)
            for ratio in ratios.values()
        ):
            failures.append(f"{region_name.upper()}:PRESERVED_SPAN_CHANGED")
        height = max(
            1e-9, float(base_regions["whole_body"]["exact_z_span"])
        )
        if any(
            delta is None or abs(float(delta)) / height > 0.003
            for delta in median_deltas.values()
        ):
            failures.append(f"{region_name.upper()}:PRESERVED_CENTER_CHANGED")

    if candidate["raw_properties"].get("global_scaling_used") is True:
        failures.append("GLOBAL_SCALING_USED_PROPERTY_TRUE")
    return {
        "status": "PASS" if not failures else "FAIL",
        "baseline_transform": baseline_transform,
        "candidate_transform": candidate_transform,
        "transform_delta": transform_delta,
        "whole_body_height_ratio": round(whole_z_ratio, 9),
        "preserved_region_comparison": preserved_region_ratios,
        "global_scaling_used_property": candidate["raw_properties"].get(
            "global_scaling_used"
        ),
        "method": (
            "Compares body transforms, full height, and robust spans/centers in "
            "feet/lower-leg and distal-hand regions outside the local pelvis "
            "repair. This detects object-level or baked whole-body scaling. It "
            "does not claim that every changed vertex is visually correct."
        ),
        "failures": failures,
        "measured_no_global_scale_signal_gate_pass": not failures,
    }


def _compare_hand_groups(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    baseline_groups = {
        name: metrics
        for name, metrics in baseline["group_metrics"].items()
        if name.casefold().startswith(HAND_GROUP_PREFIXES)
    }
    candidate_groups = {
        name: metrics
        for name, metrics in candidate["group_metrics"].items()
        if name.casefold().startswith(HAND_GROUP_PREFIXES)
    }
    missing = sorted(set(baseline_groups) - set(candidate_groups))
    empty = sorted(
        name
        for name in baseline_groups
        if name in candidate_groups
        and candidate_groups[name]["members_above_0_001"] <= 0
    )

    density_ratios = {}
    for name, baseline_metrics in baseline_groups.items():
        if name not in candidate_groups:
            continue
        baseline_fraction = float(baseline_metrics["weight_fraction"])
        candidate_fraction = float(candidate_groups[name]["weight_fraction"])
        density_ratios[name] = (
            candidate_fraction / baseline_fraction
            if baseline_fraction > 1e-12
            else 0.0
        )
    ratio_values = [value for value in density_ratios.values() if value > 0.0]
    median_ratio = statistics.median(ratio_values) if ratio_values else 0.0
    density_outliers = sorted(
        name
        for name, ratio in density_ratios.items()
        if (
            median_ratio <= 0.0
            or ratio < median_ratio * 0.65
            or ratio > median_ratio * 1.45
        )
    )

    side_pair_drift = {}
    side_pair_failures = []
    for name in sorted(baseline_groups):
        if not name.endswith("_L"):
            continue
        right_name = name[:-2] + "_R"
        if right_name not in baseline_groups:
            continue
        if name not in candidate_groups or right_name not in candidate_groups:
            continue
        baseline_left = float(baseline_groups[name]["weight_sum"])
        baseline_right = float(baseline_groups[right_name]["weight_sum"])
        candidate_left = float(candidate_groups[name]["weight_sum"])
        candidate_right = float(candidate_groups[right_name]["weight_sum"])
        baseline_ratio = baseline_left / max(baseline_right, 1e-12)
        candidate_ratio = candidate_left / max(candidate_right, 1e-12)
        relative_drift = candidate_ratio / max(baseline_ratio, 1e-12)
        pair = name[:-2]
        side_pair_drift[pair] = {
            "baseline_left_right_weight_ratio": round(baseline_ratio, 6),
            "candidate_left_right_weight_ratio": round(candidate_ratio, 6),
            "relative_drift": round(relative_drift, 6),
        }
        if relative_drift < 0.75 or relative_drift > 1.25:
            side_pair_failures.append(pair)

    expected_group_count = len(baseline_groups)
    pass_gate = (
        expected_group_count >= 40
        and not missing
        and not empty
        and not density_outliers
        and not side_pair_failures
    )
    return {
        "status": "PASS" if pass_gate else "FAIL",
        "expected_baseline_group_count": expected_group_count,
        "candidate_matching_group_count": len(set(baseline_groups) & set(candidate_groups)),
        "missing_groups": missing,
        "empty_groups": empty,
        "normalized_weight_density_ratio_median": round(median_ratio, 6),
        "normalized_weight_density_outliers": density_outliers,
        "left_right_pair_drift": side_pair_drift,
        "left_right_pair_failures": side_pair_failures,
        "preservation_pass": pass_gate,
    }


def _compare_thigh_profiles(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    base_profiles = baseline["topology"]["thigh_profile"]["profiles"]
    candidate_profiles = candidate["topology"]["thigh_profile"]["profiles"]
    side_reports = {}
    all_failures = []
    for side in ("left", "right"):
        ratios = []
        tail_excesses = []
        insufficient_bins = []
        for base_bin, candidate_bin in zip(base_profiles[side], candidate_profiles[side]):
            if (
                base_bin["samples"] < 20
                or candidate_bin["samples"] < 20
                or base_bin["width_q96"] <= 0.0
                or base_bin["depth_q96"] <= 0.0
            ):
                insufficient_bins.append(int(candidate_bin["bin"]))
                continue
            width_ratio = (
                float(candidate_bin["width_q96"]) / float(base_bin["width_q96"])
            )
            depth_ratio = (
                float(candidate_bin["depth_q96"]) / float(base_bin["depth_q96"])
            )
            ratios.append(
                {
                    "bin": int(candidate_bin["bin"]),
                    "width_ratio": round(width_ratio, 6),
                    "depth_ratio": round(depth_ratio, 6),
                }
            )
            tail_excesses.append(
                float(candidate_bin["outer_tail"]) - float(base_bin["outer_tail"])
            )
        width_ratios = [entry["width_ratio"] for entry in ratios]
        depth_ratios = [entry["depth_ratio"] for entry in ratios]
        adjacent_jumps = []
        for current, following in zip(ratios, ratios[1:]):
            adjacent_jumps.append(
                max(
                    abs(float(current["width_ratio"]) - float(following["width_ratio"])),
                    abs(float(current["depth_ratio"]) - float(following["depth_ratio"])),
                )
            )
        failures = []
        if len(ratios) < 12:
            failures.append("INSUFFICIENT_CROSS_SECTIONS")
        if width_ratios and (
            min(width_ratios) < 0.70 or max(width_ratios) > 1.15
        ):
            failures.append("WIDTH_PROFILE_OUTSIDE_MODEST_REPAIR_RANGE")
        if depth_ratios and (
            min(depth_ratios) < 0.70 or max(depth_ratios) > 1.15
        ):
            failures.append("DEPTH_PROFILE_OUTSIDE_MODEST_REPAIR_RANGE")
        if adjacent_jumps and max(adjacent_jumps) > 0.15:
            failures.append("ABRUPT_ADJACENT_CROSS_SECTION_CHANGE")
        if tail_excesses and max(tail_excesses) > 0.12:
            failures.append("NEW_SURFACE_TAIL_OUTLIER")
        all_failures.extend(f"{side.upper()}:{failure}" for failure in failures)
        side_reports[side] = {
            "compared_bins": len(ratios),
            "insufficient_bins": insufficient_bins,
            "width_ratio_min": round(min(width_ratios), 6) if width_ratios else None,
            "width_ratio_max": round(max(width_ratios), 6) if width_ratios else None,
            "depth_ratio_min": round(min(depth_ratios), 6) if depth_ratios else None,
            "depth_ratio_max": round(max(depth_ratios), 6) if depth_ratios else None,
            "max_adjacent_ratio_jump": (
                round(max(adjacent_jumps), 6) if adjacent_jumps else None
            ),
            "max_new_outer_tail_excess": (
                round(max(tail_excesses), 6) if tail_excesses else None
            ),
            "failures": failures,
            "per_bin_ratios": ratios,
        }

    symmetry_failures = []
    left = candidate_profiles["left"]
    right = candidate_profiles["right"]
    symmetry_deltas = []
    for left_bin, right_bin in zip(left, right):
        if (
            left_bin["width_q96"] <= 0.0
            or right_bin["width_q96"] <= 0.0
            or left_bin["depth_q96"] <= 0.0
            or right_bin["depth_q96"] <= 0.0
        ):
            continue
        width_delta = abs(
            float(left_bin["width_q96"]) - float(right_bin["width_q96"])
        ) / max(
            1e-9,
            (
                float(left_bin["width_q96"])
                + float(right_bin["width_q96"])
            )
            * 0.5,
        )
        depth_delta = abs(
            float(left_bin["depth_q96"]) - float(right_bin["depth_q96"])
        ) / max(
            1e-9,
            (
                float(left_bin["depth_q96"])
                + float(right_bin["depth_q96"])
            )
            * 0.5,
        )
        symmetry_deltas.append(max(width_delta, depth_delta))
    if symmetry_deltas and max(symmetry_deltas) > 0.18:
        symmetry_failures.append("CANDIDATE_LEFT_RIGHT_PROFILE_ASYMMETRY")
    all_failures.extend(symmetry_failures)
    return {
        "status": "PASS" if not all_failures else "FAIL",
        "method": (
            "Robust 2nd-to-98th percentile width/depth cross sections over the "
            "upper-leg z range, compared with V1; this detects coarse lumps or "
            "spikes but does not replace visual surface review."
        ),
        "sides": side_reports,
        "candidate_max_left_right_profile_delta": (
            round(max(symmetry_deltas), 6) if symmetry_deltas else None
        ),
        "symmetry_failures": symmetry_failures,
        "failures": all_failures,
        "surface_outlier_gate_pass": not all_failures,
    }


def _evaluate_hair(candidate: dict[str, Any]) -> dict[str, Any]:
    hair = candidate["hair"]
    objects = hair["objects"]
    failures = []
    colors = []
    if not objects:
        failures.append("NO_HAIR_OBJECT")
    for obj in objects:
        if not obj["separate_removable_object"]:
            failures.append(f"{obj['name']}:NOT_REMOVABLE")
        if obj["stage_a_static_review_only"] is not True:
            failures.append(f"{obj['name']}:STATIC_ONLY_FLAG_MISSING")
        if obj["runtime_groom_complete"] is not False:
            failures.append(f"{obj['name']}:RUNTIME_GROOM_FLAG_NOT_FALSE")
        if obj["parent_armature"] or obj["armature_modifiers"]:
            failures.append(f"{obj['name']}:ARMATURE_BOUND")
        if not obj["materials"]:
            failures.append(f"{obj['name']}:NO_MATERIAL")
        for material in obj["materials"]:
            name = material["name"] or ""
            color = material["base_color"]
            if "blond" not in name.casefold():
                failures.append(f"{obj['name']}:{name}:MATERIAL_NOT_SEMANTICALLY_BLOND")
            if not color:
                failures.append(f"{obj['name']}:{name}:NO_PRINCIPLED_BASE_COLOR")
                continue
            colors.append({"object": obj["name"], "material": name, **color})
            hue = float(color["hue_degrees"])
            saturation = float(color["saturation"])
            value = float(color["value"])
            plausible_dark_blond = (
                24.0 <= hue <= 60.0
                and 0.18 <= saturation <= 0.80
                and 0.25 <= value <= 0.85
            )
            if not plausible_dark_blond:
                failures.append(f"{obj['name']}:{name}:SHADER_COLOR_NOT_PLAUSIBLE_BLOND")

    body_hair_status = hair["body_hair_status_property"]
    status_consistent = not (
        objects
        and isinstance(body_hair_status, str)
        and any(token in body_hair_status.casefold() for token in ("absent", "none"))
    )
    if not status_consistent:
        failures.append("BODY_HAIR_STATUS_CONTRADICTS_PRESENT_HAIR_OBJECTS")
    return {
        "status": "PASS" if not failures else "FAIL",
        "object_count": len(objects),
        "objects": objects,
        "evaluated_shader_colors": colors,
        "body_hair_status_property": body_hair_status,
        "body_hair_status_consistent": status_consistent,
        "failures": sorted(set(failures)),
        "removable_static_blond_hair_gate_pass": not failures,
        "runtime_hair_completion_claimed": False,
    }


def _evaluate_static_runtime(candidate: dict[str, Any]) -> dict[str, Any]:
    snapshot = candidate["static_runtime"]
    failures = []
    if snapshot["body_armature_modifiers"]:
        failures.append("BODY_HAS_ARMATURE_MODIFIER")
    if snapshot["body_parent_armature"]:
        failures.append("BODY_PARENTED_TO_ARMATURE")
    if snapshot["animated_objects"]:
        failures.append("ACTIVE_ACTION_NLA_OR_DRIVER_PRESENT")
    if snapshot["runtime_activation_allowed"] is not False:
        failures.append("RUNTIME_ACTIVATION_NOT_EXPLICITLY_FALSE")
    if snapshot["static_review_only"] is not True:
        failures.append("STATIC_REVIEW_ONLY_NOT_EXPLICITLY_TRUE")
    movement_values = [
        snapshot["movement_started"],
        snapshot["movement_claimed"],
    ]
    if any(value is True for value in movement_values):
        failures.append("MOVEMENT_FLAG_TRUE")
    armature_links = [
        item for item in snapshot["armature_objects"] if item["parented_body"] or item["action"]
    ]
    if armature_links:
        failures.append("ARMATURE_OBJECT_ACTIVE_OR_LINKED")
    return {
        "status": "PASS" if not failures else "FAIL",
        **snapshot,
        "inert_armature_object_note": (
            "An unbound rest-rig object may remain as construction evidence; "
            "the gate requires no body binding, parenting, action, NLA, driver, "
            "movement claim, or runtime activation."
        ),
        "failures": failures,
        "static_only_no_armature_activation_gate_pass": not failures,
    }


def _build_report(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    rendered_evidence: dict[str, Any],
) -> dict[str, Any]:
    topology = _compare_topology(baseline, candidate)
    materials_and_nails = _compare_materials_and_nails(baseline, candidate)
    components = _evaluate_components(candidate)
    iris = _evaluate_iris(candidate)
    regional_skin = _evaluate_regional_skin(candidate)
    local_only_deformation = _evaluate_local_only_deformation(
        baseline, candidate
    )
    hand_groups = _compare_hand_groups(baseline, candidate)
    thighs = _compare_thigh_profiles(baseline, candidate)
    hair = _evaluate_hair(candidate)
    static_runtime = _evaluate_static_runtime(candidate)
    checks = {
        "topology_and_main_body_membership": topology,
        "materials_and_nails": materials_and_nails,
        "mesh_components_and_integrated_body": components,
        "actual_blue_iris_material": iris,
        "regional_skin_real_albedo_path": regional_skin,
        "local_only_deformation_no_global_scale_signal": local_only_deformation,
        "hand_and_finger_group_preservation": hand_groups,
        "upper_thigh_surface_outliers": thighs,
        "hair_static_review_contract": hair,
        "static_only_runtime_contract": static_runtime,
        "hash_bound_rendered_visual_evidence": rendered_evidence,
    }
    structural_checks = {
        name: result
        for name, result in checks.items()
        if name != "hash_bound_rendered_visual_evidence"
    }
    failed_structural_checks = [
        name
        for name, result in structural_checks.items()
        if result["status"] != "PASS"
    ]
    structural_pass = not failed_structural_checks
    failed_checks = list(failed_structural_checks)
    if rendered_evidence["status"] == "FAIL":
        failed_checks.append("hash_bound_rendered_visual_evidence")
    owner_visual_approved = rendered_evidence.get(
        "owner_visual_approval_recorded"
    ) is True
    if failed_checks:
        overall_status = "FAIL"
    elif owner_visual_approved:
        overall_status = "STATIC_OWNER_APPROVED"
    else:
        overall_status = "AWAITING ROBERT STATIC LIKENESS REVIEW"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": overall_status,
        "scope": (
            "Automated structural/material/static-state comparison plus "
            "integrity verification of the exact rendered files used for "
            "visual review. The audit does not make a likeness or adult "
            "anatomical-realism judgment. Visual rejection overrides topology."
        ),
        "visual_approval": (
            "APPROVED_BY_OWNER"
            if owner_visual_approved
            else rendered_evidence.get("review_decision", "NOT_RECORDED")
        ),
        "candidate": {
            key: candidate[key]
            for key in (
                "file_name",
                "sha256",
                "body_object",
                "body_detection_candidates",
                "raw_vertices",
                "raw_polygons",
                "raw_modifiers",
                "raw_properties",
                "body_transform",
            )
        },
        "baseline": {
            key: baseline[key]
            for key in (
                "file_name",
                "sha256",
                "body_object",
                "raw_vertices",
                "raw_polygons",
                "raw_modifiers",
            )
        },
        "checks": checks,
        "failed_checks": failed_checks,
        "failed_structural_checks": failed_structural_checks,
        "structural_gate_pass": structural_pass,
        "hash_bound_rendered_evidence_gate_pass": (
            rendered_evidence.get("hash_bound_rendered_evidence_pass") is True
        ),
        "visual_rejection_overrides_topology": True,
        "owner_review_required": not owner_visual_approved,
        "runtime_activation_allowed": False,
        "protected_reference_data_included": False,
    }


def main() -> int:
    args = _parse_args()
    baseline_path = Path(args.baseline).resolve()
    source_path = Path(args.source).resolve()
    output_path = Path(args.output).resolve()
    rendered_evidence_path = (
        Path(args.rendered_evidence).resolve()
        if args.rendered_evidence
        else source_path.parent / "RENDERED_VISUAL_EVIDENCE.json"
    )
    if not baseline_path.is_file():
        raise SystemExit(f"Baseline blend not found: {baseline_path}")
    if not source_path.is_file():
        raise SystemExit(f"Candidate blend not found: {source_path}")

    baseline = _snapshot(baseline_path)
    candidate = _snapshot(source_path)
    rendered_evidence = _rendered_evidence_report(
        rendered_evidence_path,
        str(candidate["sha256"]),
    )
    report = _build_report(baseline, candidate, rendered_evidence)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report))
    if report["status"] == "FAIL" and not args.allow_fail:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
