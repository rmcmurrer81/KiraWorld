"""Synthetic, non-live fixtures for garment contract unit tests."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from Core.garment_contracts import GarmentDefinition, MaturityClass, build_robe_definition


ASSET_HASH = "a" * 64
BODY_HASH = "b" * 64
RIG_HASH = "c" * 64
ITEM_ID = "robe_instance_unit_test_001"
ACTOR_ID = "unit_test_avatar"
WORLD_ID = "unit_test_world"
SUBJECT_ID = "unit_test_subject"
CONSENT_ID = "unit_test_revocable_consent_001"
MATURITY = MaturityClass.ADULT


def robe_definition() -> GarmentDefinition:
    return build_robe_definition(
        garment_type_id="unit_test_robe_v1",
        asset_sha256=ASSET_HASH,
        compatible_body_sha256=BODY_HASH,
        compatible_rig_sha256=RIG_HASH,
        compatible_subject_id=SUBJECT_ID,
        maturity_class=MATURITY,
    )


def anchor(definition: GarmentDefinition, role: str) -> str:
    return definition.anchor_for_role(role).anchor_id


def portal(
    definition: GarmentDefinition,
    side: str,
    *,
    outward: bool = False,
) -> dict[str, Any]:
    before, after = (0.06, -0.06) if outward else (-0.06, 0.06)
    return {
        "portal_anchor_id": anchor(definition, f"{side}_sleeve_portal"),
        "teleported": False,
        "crossing_order": ["elbow", "forearm", "wrist"] if outward else ["wrist", "forearm", "elbow"],
        "segment_paths": {
            segment: {
                "limb_anchor_id": anchor(definition, f"{side}_{segment}_path"),
                "crossed": True,
                "continuous_path": True,
                "signed_distance_before_m": before,
                "signed_distance_after_m": after,
                "path_sample_count": 5,
                "max_path_step_m": 0.08,
            }
            for segment in ("wrist", "forearm", "elbow")
        },
    }


def valid_evidence(
    definition: GarmentDefinition,
    gate: str,
    transaction_id: str,
    *,
    item_instance_id: str = ITEM_ID,
) -> dict[str, Any]:
    raw_trace = {
        "trace_id": f"trace_{transaction_id}_{gate}",
        "transaction_id": transaction_id,
        "item_instance_id": item_instance_id,
        "source": "isolated_unit_test_runtime",
        "frame_count": 24,
    }
    raw_trace_sha256 = hashlib.sha256(
        json.dumps(raw_trace, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    evidence: dict[str, Any] = {
        "capture_basis": "runtime_collision_and_physics_trace",
        "timer_only": False,
        "raw_trace": raw_trace,
        "raw_trace_sha256": raw_trace_sha256,
        "identity": {
            "transaction_id": transaction_id,
            "item_instance_id": item_instance_id,
            "source_instance_id": item_instance_id,
            "target_instance_id": item_instance_id,
            "asset_sha256": definition.asset_sha256,
            "body_sha256": definition.compatible_body_sha256,
            "rig_sha256": definition.compatible_rig_sha256,
            "subject_id": definition.compatible_subject_id,
            "body_owner_subject_id": definition.compatible_subject_id,
            "maturity_class": definition.maturity_class.value,
            "matching_scene_nodes": 1,
        },
        "consent": {
            "consent_record_id": CONSENT_ID,
            "transaction_id": transaction_id,
            "subject_id": definition.compatible_subject_id,
            "decision": "consented",
            "revocable": True,
            "refusal_active": False,
        },
        "privacy": {
            "subject_id": definition.compatible_subject_id,
            "active": True,
            "observers_allowed": False,
            "log_scope": "evidence_only",
            "raw_visual_recording": False,
        },
    }
    if gate == "hook_detach":
        evidence.update(
            {
                "hook_contact": {
                    "touching": True,
                    "hand_anchor_id": anchor(definition, "hand_grip"),
                    "object_anchor_id": anchor(definition, "garment_hook_loop"),
                    "world_anchor_id": anchor(definition, "world_wall_hook"),
                    "distance_m": 0.025,
                    "max_distance_m": 0.032,
                    "consecutive_contact_frames": 4,
                },
                "detachment": {
                    "detached": True,
                    "garment_anchor_id": anchor(definition, "garment_hook_loop"),
                    "source_anchor_id": anchor(definition, "world_wall_hook"),
                    "hand_contact_maintained": True,
                    "source_copy_visible_after": False,
                },
            }
        )
    elif gate in {
        "right_sleeve_crossing",
        "left_sleeve_crossing",
        "right_sleeve_exit",
        "left_sleeve_exit",
    }:
        side = "right" if gate.startswith("right") else "left"
        outward = gate.endswith("exit")
        evidence[f"{side}_sleeve_exit" if outward else f"{side}_sleeve_crossing"] = portal(
            definition, side, outward=outward
        )
    elif gate == "shoulder_settle":
        evidence["shoulder_settle"] = {
            "garment_anchor_id": anchor(definition, "garment_shoulders"),
            "body_anchor_id": anchor(definition, "body_shoulders"),
            "left_supported": True,
            "right_supported": True,
            "attachment_active": True,
            "skinned_to_verified_rig": True,
            "max_separation_m": 0.025,
            "max_collision_penetration_m": 0.008,
            "stable_sample_count": 6,
        }
    elif gate in {"belt_tie", "belt_untie"}:
        evidence["belt_continuity"] = {
            "left_endpoint_anchor_id": anchor(definition, "belt_left_endpoint"),
            "right_endpoint_anchor_id": anchor(definition, "belt_right_endpoint"),
            "left_endpoint_instance_id": item_instance_id,
            "right_endpoint_instance_id": item_instance_id,
            "tracked_continuously": True,
            "endpoint_substitution": False,
            "left_hand_grasp": True,
            "right_hand_grasp": True,
        }
        if gate == "belt_tie":
            evidence["belt_tie"] = {
                "knot_anchor_id": anchor(definition, "belt_knot"),
                "waist_anchor_id": anchor(definition, "body_waist"),
                "knot_formed": True,
                "knot_secured": True,
                "hand_contact_during_tie": True,
                "continuous_hand_paths": True,
                "knot_path_sample_count": 9,
                "wrap_crossing_count": 2,
                "tightening_displacement_m": 0.09,
                "stable_sample_count": 5,
            }
        else:
            evidence["belt_untie"] = {
                "knot_anchor_id": anchor(definition, "belt_knot"),
                "knot_released": True,
                "hand_contact_during_untie": True,
                "continuous_hand_paths": True,
                "path_sample_count": 7,
                "endpoints_separated": True,
            }
    elif gate == "worn_movement":
        evidence["worn_movement"] = {
            "teleported": False,
            "garment_follows_verified_rig": True,
            "garment_detached": False,
            "max_collision_penetration_m": 0.012,
            "walk": {
                "grounded_route": True,
                "path_sample_count": 12,
                "displacement_m": 1.8,
            },
            "turn": {
                "continuous_root_path": True,
                "root_sample_count": 8,
                "rotation_degrees": 90.0,
                "feet_grounded": True,
            },
            "sit": {
                "continuous_posture_transition": True,
                "pelvis_path_sample_count": 8,
                "support_surface_instance_id": "unit_test_chair_001",
                "support_contact": True,
                "supported": True,
                "supported_frame_count": 5,
                "falling": False,
            },
            "stand": {
                "continuous_posture_transition": True,
                "pelvis_path_sample_count": 8,
                "feet_grounded": True,
                "standing_supported": True,
                "seat_support_released": True,
                "falling": False,
            },
            "support_continuity": {
                "sit_surface_instance_id": "unit_test_chair_001",
                "stand_source_surface_instance_id": "unit_test_chair_001",
                "matching_surface_nodes": 1,
            },
        }
    elif gate == "removal":
        evidence["removal"] = {
            "left_sleeve_exit": portal(definition, "left", outward=True),
            "right_sleeve_exit": portal(definition, "right", outward=True),
            "shoulder_attachment_removed": True,
            "garment_held_after_exit": True,
            "hand_anchor_id": anchor(definition, "hand_grip"),
        }
    elif gate == "rehang":
        evidence["rehang"] = {
            "garment_anchor_id": anchor(definition, "garment_hook_loop"),
            "world_anchor_id": anchor(definition, "world_wall_hook"),
            "loop_hook_contact": True,
            "max_loop_hook_distance_m": 0.02,
            "contact_frame_count": 4,
            "hand_contact_until_attached": True,
            "attached": True,
            "supported_by_hook": True,
            "hand_released_after_attachment": True,
            "stable_sample_count": 5,
        }
    elif gate == "bed_placement":
        evidence["bed_placement"] = {
            "surface_anchor_id": anchor(definition, "bed_surface"),
            "hand_contact_before_release": True,
            "surface_contact": True,
            "supported": True,
            "hand_released": True,
            "ballistic_throw": False,
            "stable_sample_count": 5,
        }
    elif gate == "throw_release":
        evidence["throw_release"] = {
            "target_surface_anchor_id": anchor(definition, "bed_surface"),
            "released_from_hand": True,
            "source_hand_empty": True,
            "physics_driven": True,
            "teleported": False,
            "release_speed_mps": 1.2,
            "trajectory_sample_count": 8,
        }
    elif gate == "throw_settle":
        evidence["throw_settle"] = {
            "surface_anchor_id": anchor(definition, "bed_surface"),
            "physics_driven": True,
            "teleported": False,
            "bed_collision_contact": True,
            "supported": True,
            "continuous_from_release": True,
            "max_linear_speed_mps": 0.025,
            "max_angular_speed_rps": 0.04,
            "stable_sample_count": 8,
        }
    elif gate == "bed_pickup":
        evidence["bed_pickup"] = {
            "surface_anchor_id": anchor(definition, "bed_surface"),
            "hand_contact_before_detach": True,
            "surface_support_removed": True,
            "held": True,
            "source_copy_visible_after": False,
        }
    else:
        raise AssertionError(f"test fixture does not implement gate {gate}")
    return evidence
