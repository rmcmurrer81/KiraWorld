#!/usr/bin/env python3
"""Read-only Blender inspection for Kira R7 face-authoring boundaries.

This worker opens the already-isolated R7 workspace, measures topology and
semantic evidence, and writes JSON.  It never edits or saves the Blend file,
exports a model, or changes a runtime binding.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector


MASK_NAMES = (
    "r7_mask_protected_head_existing_mouth",
    "r7_mask_authorable_body_below_protected_boundary",
    "r7_mask_mammary_areola_left",
    "r7_mask_mammary_areola_right",
    "r7_mask_external_genital_surface",
)

EXPECTED_EYE_OBJECTS = (
    "KiraBrownEyeRig_v3_2",
    "KiraLeftEyePivot",
    "KiraLeftEyeSocket",
    "KiraRightEyePivot",
    "KiraRightEyeSocket",
)

SUPPORT_GROUPS = (
    "mixamorig:Head_06",
    "mixamorig:Neck_05",
    "mixamorig:Spine2_04",
)


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--eye-rig", required=True)
    parser.add_argument("--workspace-sha256", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--eye-rig-sha256", required=True)
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def index_sha256(indices: list[int]) -> str:
    digest = hashlib.sha256()
    for index in sorted(indices):
        digest.update(struct.pack("<I", index))
    return digest.hexdigest()


def bounds(points: list[Vector]) -> dict[str, list[float]]:
    low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    center = (low + high) * 0.5
    return {
        "low": [round(float(value), 9) for value in low],
        "high": [round(float(value), 9) for value in high],
        "center": [round(float(value), 9) for value in center],
        "size": [round(float(value), 9) for value in high - low],
    }


def connected_components(mesh: bpy.types.Mesh) -> list[list[int]]:
    parent = list(range(len(mesh.vertices)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first: int, second: int) -> None:
        left = find(first)
        right = find(second)
        if left != right:
            parent[right] = left

    for edge in mesh.edges:
        union(int(edge.vertices[0]), int(edge.vertices[1]))

    result: dict[int, list[int]] = {}
    for vertex in mesh.vertices:
        result.setdefault(find(int(vertex.index)), []).append(int(vertex.index))
    return sorted(result.values(), key=lambda item: (-len(item), min(item)))


def component_record(
    body: bpy.types.Object,
    component_id: str,
    indices: list[int],
) -> dict[str, object]:
    local_points = [body.data.vertices[index].co.copy() for index in indices]
    world_points = [body.matrix_world @ point for point in local_points]
    return {
        "component_id": component_id,
        "vertex_count": len(indices),
        "minimum_vertex_index": min(indices),
        "maximum_vertex_index": max(indices),
        "vertex_index_sha256": index_sha256(indices),
        "local_bounds": bounds(local_points),
        "world_bounds_m": bounds(world_points),
    }


def support_record(
    body: bpy.types.Object,
    component_by_vertex: dict[int, str],
    group_name: str,
) -> dict[str, object]:
    group = body.vertex_groups.get(group_name)
    if group is None:
        return {"present": False, "vertex_count": 0, "components": {}}
    positive: list[tuple[int, float]] = []
    for vertex in body.data.vertices:
        weight = max(
            (
                float(item.weight)
                for item in vertex.groups
                if int(item.group) == int(group.index)
            ),
            default=0.0,
        )
        if weight > 1e-8:
            positive.append((int(vertex.index), weight))
    component_counts = Counter(component_by_vertex[index] for index, _ in positive)
    local_z = [float(body.data.vertices[index].co.z) for index, _ in positive]
    return {
        "present": True,
        "vertex_count": len(positive),
        "vertex_index_sha256": index_sha256([index for index, _ in positive]),
        "local_z_range": [round(min(local_z), 9), round(max(local_z), 9)],
        "weight_range": [
            round(min(weight for _, weight in positive), 9),
            round(max(weight for _, weight in positive), 9),
        ],
        "components": dict(sorted(component_counts.items())),
    }


def mask_record(mesh: bpy.types.Mesh, name: str) -> dict[str, object]:
    attribute = mesh.attributes.get(name)
    if attribute is None:
        return {"present": False, "nonzero_vertex_count": 0}
    selected = [
        index
        for index, value in enumerate(attribute.data)
        if float(value.value) > 0.5
    ]
    return {
        "present": True,
        "domain": attribute.domain,
        "data_type": attribute.data_type,
        "value_count": len(attribute.data),
        "nonzero_vertex_count": len(selected),
        "vertex_index_sha256": index_sha256(selected),
    }


def main() -> int:
    args = parse_args()
    workspace = Path(bpy.data.filepath).resolve(strict=True)
    source = Path(args.source).resolve(strict=True)
    eye_rig = Path(args.eye_rig).resolve(strict=True)
    output = Path(args.output).resolve()

    actual_hashes = {
        "workspace": sha256_file(workspace),
        "source_r6": sha256_file(source),
        "staged_eye_rig": sha256_file(eye_rig),
    }
    expected_hashes = {
        "workspace": args.workspace_sha256,
        "source_r6": args.source_sha256,
        "staged_eye_rig": args.eye_rig_sha256,
    }
    if actual_hashes != expected_hashes:
        raise ValueError(
            f"pinned source mismatch: expected={expected_hashes} actual={actual_hashes}"
        )

    working = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.get("r7_role") == "working_body_unauthored"
    ]
    if len(working) != 1:
        raise ValueError(f"expected one R7 working body, found {len(working)}")
    body = working[0]
    mesh = body.data

    components = connected_components(mesh)
    component_by_vertex: dict[int, str] = {}
    records: list[dict[str, object]] = []
    for ordinal, indices in enumerate(components):
        component_id = f"component_{ordinal:03d}"
        for index in indices:
            component_by_vertex[index] = component_id
        records.append(component_record(body, component_id, indices))

    mouth_matches = [record for record in records if record["vertex_count"] == 207]
    mouth_candidate = mouth_matches[0] if len(mouth_matches) == 1 else None

    supports = {
        name: support_record(body, component_by_vertex, name)
        for name in SUPPORT_GROUPS
    }
    shared_support_components = sorted(
        set(supports[SUPPORT_GROUPS[0]]["components"])
        & set(supports[SUPPORT_GROUPS[1]]["components"])
        & set(supports[SUPPORT_GROUPS[2]]["components"])
    )

    shape_key_names = (
        [key.name for key in mesh.shape_keys.key_blocks]
        if mesh.shape_keys is not None
        else []
    )
    face_tokens = ("viseme", "phoneme", "mouth", "jaw", "blink", "eye_")
    facial_shape_keys = [
        name for name in shape_key_names if any(token in name.lower() for token in face_tokens)
    ]
    armatures = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "ARMATURE"
        and obj.get("r7_role") == "protected_exact_79_bone_rig"
    ]
    if len(armatures) != 1:
        raise ValueError(f"expected one protected R7 rig, found {len(armatures)}")
    bone_names = [bone.name for bone in armatures[0].data.bones]
    facial_bone_tokens = ("jaw", "lip", "mouth", "eye", "lid", "face")
    facial_bones = [
        name for name in bone_names if any(token in name.lower() for token in facial_bone_tokens)
    ]

    masks = {name: mask_record(mesh, name) for name in MASK_NAMES}
    scene_object_names = sorted(obj.name for obj in bpy.context.scene.objects)
    eye_objects_present = [name for name in EXPECTED_EYE_OBJECTS if name in scene_object_names]

    evidence = {
        "schema_version": 1,
        "inspection_id": "kira_r7_face_authoring_boundary_20260721",
        "mode": "read_only_inactive_blender_workspace_inspection",
        "sources": {
            "workspace": {"path": str(workspace), "sha256": actual_hashes["workspace"]},
            "source_r6": {"path": str(source), "sha256": actual_hashes["source_r6"]},
            "staged_eye_rig": {
                "path": str(eye_rig),
                "sha256": actual_hashes["staged_eye_rig"],
            },
        },
        "working_body": {
            "object": body.name,
            "mesh": mesh.name,
            "vertex_count": len(mesh.vertices),
            "edge_count": len(mesh.edges),
            "polygon_count": len(mesh.polygons),
            "connected_component_count": len(records),
            "largest_components": records[:20],
        },
        "existing_single_mouth_surface": {
            "runtime_cross_reference_vertex_count": 207,
            "matching_connected_component_count": len(mouth_matches),
            "unique_topology_island_candidate": mouth_candidate,
            "deterministic_on_exact_pinned_r6": mouth_candidate is not None,
            "semantic_status": (
                "Exact disconnected 207-vertex component matching the tested R6 runtime lip-island count; "
                "a human must still confirm it before any authoring mask is assigned."
            ),
            "second_mouth_created": False,
        },
        "head_neck_boundary": {
            "support_groups": supports,
            "components_with_head_neck_and_upper_torso_support": shared_support_components,
            "head_neck_torso_welded_in_same_component": bool(shared_support_components),
            "closed_neck_boundary_loop_semantically_labeled": False,
            "automatic_boundary_selection_proven": False,
            "why_manual": (
                "Connectivity isolates the lip island but not the protected head/neck transition. "
                "Head, neck, and upper-torso skin support share a continuous component, and bone "
                "weights/coordinates do not encode the human-reviewed cutoff."
            ),
        },
        "face_animation_capability": {
            "shape_key_names": shape_key_names,
            "facial_shape_keys": facial_shape_keys,
            "facial_bones": facial_bones,
            "reviewed_viseme_or_jaw_control_present": bool(facial_shape_keys or facial_bones),
            "real_lip_sync_ready": False,
            "reason": (
                "The exact existing lip surface is present, but the R7 workspace has no reviewed "
                "viseme/phoneme shape keys, jaw/lip controls, or mouth-interior authoring proof."
            ),
        },
        "eye_fit_capability": {
            "staged_eye_rig_exists_as_separate_pinned_asset": True,
            "expected_eye_objects_in_workspace": eye_objects_present,
            "eye_rig_appended_to_workspace": len(eye_objects_present) == len(EXPECTED_EYE_OBJECTS),
            "eyelid_socket_vertex_masks_present": False,
            "exact_eye_fit_proven": False,
            "why_manual": (
                "The staged rig is separate, while the R7 head has no reviewed eyelid/socket rim "
                "selection. A modeler must mark those loops and fit the globes behind the existing lids."
            ),
        },
        "current_semantic_masks": {
            "masks": masks,
            "all_empty": all(record.get("nonzero_vertex_count") == 0 for record in masks.values()),
            "face_authoring_lane_gap": (
                "The current protected-head/existing-mouth mask combines immutable identity surface "
                "with the surface that must receive controlled in-place mouth authoring. Add reviewed, "
                "separate mouth and eyelid/socket authoring masks before face work."
            ),
        },
        "next_manual_operation": {
            "operation_id": "review_r7_face_boundary_and_authoring_sublanes",
            "automatic_selection_allowed": False,
            "steps": [
                "Open the inactive R7 Blend workspace; do not move or save geometry yet.",
                "Confirm the reported 207-vertex disconnected island is Kira's one existing lip surface.",
                "On the continuous main body surface, choose one closed neck boundary edge loop below the complete jaw, ears, scalp, face, eyelids, and sockets.",
                "Flood-select the complete head above that reviewed loop and attest its exact vertex-index hash; assign the exact complement below it.",
                "Create separate reviewed authoring submasks for the existing lip island and the left/right eyelid/socket rims; do not create a second mouth or separate face shell.",
                "Only then author mouth interior and viseme/jaw deformation on the existing mouth, and fit the separate staged eyes behind the existing lids.",
            ],
        },
        "gates": {
            "face_geometry_authoring_allowed": False,
            "eye_fit_authoring_allowed": False,
            "real_lip_sync_proven": False,
            "exact_eye_fit_proven": False,
            "candidate_export_allowed": False,
            "runtime_activation_allowed": False,
            "owner_approved": False,
        },
        "safety": {
            "blend_saved": False,
            "candidate_exported": False,
            "live_r6_touched": False,
            "runtime_binding_touched": False,
            "avatar_builder_binding_touched": False,
            "home_world_touched": False,
        },
        "truth_note": (
            "This inspection proves topology/connectivity facts for the pinned inactive workspace only. "
            "It does not prove complete adult anatomy, owner approval, eye fit, or real lip sync."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
