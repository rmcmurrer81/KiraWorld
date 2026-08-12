#!/usr/bin/env python3
"""Read-only closeout verifier for the quarantined R21 movement Attempt 03.

This worker never saves a Blend and never authors, assigns, renders, or
regenerates an action.  It opens the already-saved candidate, reacquires all
post-reopen objects, records protected-state signatures, then opens the exact
source Blend and compares the inherited state.  The compact JSON result is
printed to stdout for append-only evidence assembly outside Blender.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import bpy


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_author_kira_r21_action_only_movement_attempt01 as base  # noqa: E402
import blender_author_kira_r21_brow_only_attempt01 as brow  # noqa: E402


CONFIG_PATH = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r21_action_only_movement_correction/"
    "MOVEMENT_CONFIG_ATTEMPT_03_EXPANDED.json"
)
ACTION_PREFIX = "KIRA_R21_MOVEMENT_ATTEMPT03_"
CANDIDATE_FILENAME = (
    "KIRA_R21_BALD_PRIVATE_INACTIVE_ACTION_ONLY_MOVEMENT_ATTEMPT01.blend"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def expected_action_names(config: dict[str, Any]) -> list[str]:
    ids = list(config["fixed_pose_actions"].keys())
    ids.extend(str(item["id"]) for item in config["seated_candidates"])
    ids.append("sit_to_stand_transition_foundation")
    return sorted(ACTION_PREFIX + value.upper() for value in ids)


def acquire_state(config: dict[str, Any], include_new_actions: bool) -> dict[str, Any]:
    body = bpy.data.objects.get(str(config["body_object"]))
    rig = bpy.data.objects.get(str(config["rig_object"]))
    if body is None or body.type != "MESH":
        raise RuntimeError("configured body is absent after reopen")
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError("configured rig is absent after reopen")

    base.ACTION_PREFIX = ACTION_PREFIX
    meshes = base.inherited_mesh_snapshot()
    inherited_actions = base.inherited_action_snapshot()
    new_actions = {
        action.name: base.action_signature(action)
        for action in sorted(bpy.data.actions, key=lambda item: item.name)
        if action.name.startswith(ACTION_PREFIX)
    }
    assigned_action = None
    if rig.animation_data is not None and rig.animation_data.action is not None:
        assigned_action = rig.animation_data.action.name

    temp_object_names = sorted(
        obj.name
        for obj in bpy.data.objects
        if obj.name.startswith("KIRA_R21_MOVEMENT_ATTEMPT01_TEMP_")
        or obj.name.startswith("KIRA_R21_MOVEMENT_ATTEMPT03_TEMP_")
    )
    temp_collection_names = sorted(
        collection.name
        for collection in bpy.data.collections
        if collection.name.startswith("KIRA_R21_MOVEMENT_ATTEMPT01_TEMP_")
        or collection.name.startswith("KIRA_R21_MOVEMENT_ATTEMPT03_TEMP_")
    )

    return {
        "body_object": body.name,
        "body_geometry_uv_sha256_r21_brow_serializer": brow.mesh_geometry_digest(body),
        "body_positive_weight_assignment_sha256_r21_brow_serializer": brow.weight_digest(body),
        "neutral_evaluated_coordinate_sha256": base.evaluated_coordinate_sha256(body),
        "rig_object": rig.name,
        "rig_joint_count": len(rig.data.bones),
        "rig_rest_sha256_r21_brow_serializer": brow.armature_digest(rig),
        "rig_assigned_action": assigned_action,
        "inherited_mesh_count": len(meshes),
        "inherited_mesh_snapshot_sha256": base.json_sha256(meshes),
        "inherited_action_count": len(inherited_actions),
        "inherited_action_snapshot_sha256": base.json_sha256(inherited_actions),
        "new_action_count": len(new_actions),
        "new_action_names": sorted(new_actions),
        "new_action_signature_sha256": {
            name: str(signature["sha256"])
            for name, signature in sorted(new_actions.items())
        }
        if include_new_actions
        else {},
        "temporary_object_names": temp_object_names,
        "temporary_collection_names": temp_collection_names,
    }


def main() -> int:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    source = PROJECT_ROOT / str(config["source_blend"])
    source_evidence = PROJECT_ROOT / str(config["source_evidence"])
    candidate = PROJECT_ROOT / str(config["owner_review_output_dir"]) / CANDIDATE_FILENAME

    candidate_hash_before = sha256_file(candidate)
    source_hash_before = sha256_file(source)
    source_evidence_hash = sha256_file(source_evidence)
    if source_hash_before != str(config["source_blend_sha256"]):
        raise RuntimeError("source Blend hash does not match the sealed config")
    if source_evidence_hash != str(config["source_evidence_sha256"]):
        raise RuntimeError("source evidence hash does not match the sealed config")
    if Path(bpy.data.filepath).resolve() != candidate.resolve():
        raise RuntimeError("read-only worker was not started with the exact candidate Blend")

    candidate_state = acquire_state(config, include_new_actions=True)
    expected_names = expected_action_names(config)
    candidate_gates = {
        "geometry_uv_exact": candidate_state[
            "body_geometry_uv_sha256_r21_brow_serializer"
        ]
        == str(config["body_geometry_uv_sha256"]),
        "weights_exact": candidate_state[
            "body_positive_weight_assignment_sha256_r21_brow_serializer"
        ]
        == str(config["body_positive_weight_assignment_sha256"]),
        "rig_rest_exact": candidate_state["rig_rest_sha256_r21_brow_serializer"]
        == str(config["rig_rest_sha256"]),
        "rig_joint_count_exact": candidate_state["rig_joint_count"]
        == int(config["expected_rig_joint_count"]),
        "new_action_inventory_exact": candidate_state["new_action_names"] == expected_names,
        "new_actions_unassigned": candidate_state["rig_assigned_action"] is None,
        "temporary_objects_absent": not candidate_state["temporary_object_names"],
        "temporary_collections_absent": not candidate_state["temporary_collection_names"],
    }
    if not all(candidate_gates.values()):
        raise RuntimeError(f"candidate post-reopen gate failed: {candidate_gates}")

    bpy.ops.wm.open_mainfile(filepath=str(source))
    if Path(bpy.data.filepath).resolve() != source.resolve():
        raise RuntimeError("failed to reopen the exact protected source Blend")
    source_state = acquire_state(config, include_new_actions=False)

    comparison = {
        "all_inherited_mesh_states_exact": candidate_state[
            "inherited_mesh_snapshot_sha256"
        ]
        == source_state["inherited_mesh_snapshot_sha256"],
        "all_inherited_action_states_exact": candidate_state[
            "inherited_action_snapshot_sha256"
        ]
        == source_state["inherited_action_snapshot_sha256"],
        "body_geometry_uv_exact": candidate_state[
            "body_geometry_uv_sha256_r21_brow_serializer"
        ]
        == source_state["body_geometry_uv_sha256_r21_brow_serializer"],
        "body_weights_exact": candidate_state[
            "body_positive_weight_assignment_sha256_r21_brow_serializer"
        ]
        == source_state["body_positive_weight_assignment_sha256_r21_brow_serializer"],
        "native_rest_rig_exact": candidate_state[
            "rig_rest_sha256_r21_brow_serializer"
        ]
        == source_state["rig_rest_sha256_r21_brow_serializer"],
        "neutral_evaluated_coordinates_exact": candidate_state[
            "neutral_evaluated_coordinate_sha256"
        ]
        == source_state["neutral_evaluated_coordinate_sha256"],
    }
    if not all(comparison.values()):
        raise RuntimeError(f"candidate differs from source protected state: {comparison}")

    result = {
        "schema_version": 1,
        "artifact_kind": "KIRA_R21_MOVEMENT_ATTEMPT03_READ_ONLY_CLOSEOUT_VERIFICATION",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": {
            "path": relative(candidate),
            "sha256_before": candidate_hash_before,
            "bytes": candidate.stat().st_size,
            "state": candidate_state,
            "gates": candidate_gates,
        },
        "source": {
            "path": relative(source),
            "sha256_before": source_hash_before,
            "expected_sha256": str(config["source_blend_sha256"]),
            "state": source_state,
            "evidence_path": relative(source_evidence),
            "evidence_sha256": source_evidence_hash,
        },
        "protected_comparison": comparison,
        "expected_new_action_names": expected_names,
        "read_only_contract": {
            "actions_authored": False,
            "actions_assigned": False,
            "renders_generated": False,
            "blend_saved": False,
            "activation_export_publication_performed": False,
        },
    }

    # File hashes are taken again after every Blender read.  The source is the
    # currently opened file, and neither candidate nor source is ever saved.
    result["candidate"]["sha256_after"] = sha256_file(candidate)
    result["source"]["sha256_after"] = sha256_file(source)
    result["candidate"]["unchanged"] = (
        result["candidate"]["sha256_after"] == candidate_hash_before
    )
    result["source"]["unchanged"] = (
        result["source"]["sha256_after"] == source_hash_before
    )
    if not result["candidate"]["unchanged"] or not result["source"]["unchanged"]:
        raise RuntimeError("a Blend file changed during the read-only verification")

    print("READ_ONLY_CLOSEOUT_JSON=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
