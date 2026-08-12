"""Fail-closed physical evidence gates for garment transitions.

The evaluator accepts structured runtime observations, never an animation name,
elapsed duration, or visual-state flag by itself.  Every decision is bound to
one transaction, persistent item instance, exact garment asset, and (when a
body participates) exact body and rig hashes.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any

from Core.garment_contracts import AffordanceSpec, GarmentDefinition, SHA256_RE


TIMER_ONLY_BASES = {
    "timer",
    "timer_only",
    "animation_elapsed",
    "scripted_claim",
    "state_name_only",
}

ALLOWED_CAPTURE_BASES = frozenset(
    {
        "runtime_collision_and_physics_trace",
        "runtime_sensor_trace",
        "verified_physics_trace",
    }
)

BODY_GATES = frozenset(
    {
        "hook_detach",
        "right_sleeve_crossing",
        "left_sleeve_crossing",
        "right_sleeve_exit",
        "left_sleeve_exit",
        "shoulder_settle",
        "belt_tie",
        "belt_untie",
        "worn_movement",
        "removal",
        "rehang",
        "bed_placement",
        "throw_release",
        "bed_pickup",
    }
)


@dataclass(frozen=True, slots=True)
class EvidenceDecision:
    transaction_id: str
    item_instance_id: str
    evidence_gate: str
    raw_trace_sha256: str
    evidence_context_sha256: str
    decision_sha256: str
    passed: bool
    reasons: tuple[str, ...]

    @property
    def status(self) -> str:
        return "passed" if self.passed else "blocked"

    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "item_instance_id": self.item_instance_id,
            "evidence_gate": self.evidence_gate,
            "raw_trace_sha256": self.raw_trace_sha256,
            "evidence_context_sha256": self.evidence_context_sha256,
            "decision_sha256": self.decision_sha256,
            "status": self.status,
            "passed": self.passed,
            "reasons": list(self.reasons),
        }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def _need(reasons: list[str], condition: bool, reason: str) -> None:
    if not condition:
        reasons.append(reason)


def _at_most(value: Any, maximum: float) -> bool:
    number = _number(value)
    return number is not None and 0.0 <= number <= maximum


def _at_least(value: Any, minimum: float) -> bool:
    number = _number(value)
    return number is not None and number >= max(0.0, minimum)


def _anchor_id(definition: GarmentDefinition, role: str) -> str:
    return definition.anchor_for_role(role).anchor_id


def _computed_raw_trace_sha256(evidence: dict[str, Any]) -> str:
    return _canonical_sha256(_dict(evidence.get("raw_trace")))


def _canonical_sha256(value: Any) -> str:
    """Hash canonical JSON without retaining the source payload."""

    try:
        payload = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return ""
    return hashlib.sha256(payload).hexdigest()


def compute_decision_sha256(
    *,
    transaction_id: str,
    item_instance_id: str,
    evidence_gate: str,
    raw_trace_sha256: str,
    evidence_context_sha256: str,
    passed: bool,
    reasons: list[str] | tuple[str, ...],
) -> str:
    """Bind the evaluated evidence identity to its exact derived result."""

    return _canonical_sha256(
        {
            "schema_version": 1,
            "transaction_id": transaction_id,
            "item_instance_id": item_instance_id,
            "evidence_gate": evidence_gate,
            "raw_trace_sha256": raw_trace_sha256,
            "evidence_context_sha256": evidence_context_sha256,
            "passed": passed,
            "reasons": list(reasons),
        }
    )


def _identity_reasons(
    definition: GarmentDefinition,
    affordance: AffordanceSpec,
    evidence: dict[str, Any],
    *,
    transaction_id: str,
    item_instance_id: str,
    consent_record_id: str,
) -> list[str]:
    identity = _dict(evidence.get("identity"))
    reasons: list[str] = []
    _need(reasons, _text(identity.get("transaction_id")) == transaction_id, "evidence is not bound to this transaction")
    _need(reasons, _text(identity.get("item_instance_id")) == item_instance_id, "evidence has the wrong item instance")
    _need(reasons, _text(identity.get("source_instance_id")) == item_instance_id, "source garment identity is not continuous")
    _need(reasons, _text(identity.get("target_instance_id")) == item_instance_id, "target garment identity is not continuous")
    _need(reasons, _text(identity.get("asset_sha256")) == definition.asset_sha256, "evidence has the wrong garment asset hash")
    _need(reasons, _text(identity.get("subject_id")) == definition.compatible_subject_id, "evidence has the wrong garment subject")
    _need(reasons, _text(identity.get("body_owner_subject_id")) == definition.compatible_subject_id, "evidence body ownership does not match the garment subject")
    _need(reasons, _text(identity.get("maturity_class")) == definition.maturity_class.value, "evidence has the wrong maturity policy")
    matching_nodes = identity.get("matching_scene_nodes")
    _need(
        reasons,
        isinstance(matching_nodes, int)
        and not isinstance(matching_nodes, bool)
        and matching_nodes == 1,
        "scene evidence does not show exactly one node for this item",
    )

    basis = _text(evidence.get("capture_basis")).lower()
    _need(reasons, bool(basis), "evidence capture basis is missing")
    _need(reasons, basis in ALLOWED_CAPTURE_BASES, "evidence capture basis is not an approved runtime trace source")
    _need(reasons, basis not in TIMER_ONLY_BASES, "timer/state-name-only evidence cannot prove a garment interaction")
    _need(reasons, evidence.get("timer_only") is not True, "timer-only success is forbidden")

    raw_trace = _dict(evidence.get("raw_trace"))
    claimed_trace_hash = _text(evidence.get("raw_trace_sha256")).lower()
    _need(reasons, _text(raw_trace.get("transaction_id")) == transaction_id, "raw trace is not bound to this transaction")
    _need(reasons, _text(raw_trace.get("item_instance_id")) == item_instance_id, "raw trace is not bound to this garment instance")
    frame_count = raw_trace.get("frame_count")
    _need(reasons, isinstance(frame_count, int) and not isinstance(frame_count, bool) and frame_count >= 3, "raw trace needs at least three sensor/physics frames")
    computed_trace_hash = _computed_raw_trace_sha256(evidence)
    _need(reasons, bool(SHA256_RE.fullmatch(claimed_trace_hash)), "raw trace hash is not an exact SHA-256")
    _need(reasons, bool(computed_trace_hash) and claimed_trace_hash == computed_trace_hash, "raw trace hash does not match the supplied trace")

    if affordance.evidence_gate in BODY_GATES:
        _need(reasons, _text(identity.get("body_sha256")) == definition.compatible_body_sha256, "evidence has the wrong body hash")
        _need(reasons, _text(identity.get("rig_sha256")) == definition.compatible_rig_sha256, "evidence has the wrong rig hash")
        consent = _dict(evidence.get("consent"))
        _need(reasons, bool(consent_record_id) and _text(consent.get("consent_record_id")) == consent_record_id, "evidence is not bound to the active consent record")
        _need(reasons, _text(consent.get("transaction_id")) == transaction_id, "consent is not bound to this transaction")
        _need(reasons, _text(consent.get("subject_id")) == definition.compatible_subject_id, "consent belongs to the wrong subject")
        _need(reasons, _text(consent.get("decision")).lower() == "consented", "the subject did not consent to this garment step")
        _need(reasons, consent.get("revocable") is True, "garment consent is not explicitly revocable")
        _need(reasons, consent.get("refusal_active") is False, "an active refusal blocks the garment step")

        privacy = _dict(evidence.get("privacy"))
        _need(reasons, _text(privacy.get("subject_id")) == definition.compatible_subject_id, "privacy state belongs to the wrong subject")
        _need(reasons, privacy.get("active") is True, "private wardrobe mode is not active")
        _need(reasons, privacy.get("observers_allowed") is False, "wardrobe evidence still permits observers")
        _need(reasons, _text(privacy.get("log_scope")).lower() in {"metadata_only", "evidence_only"}, "wardrobe privacy log scope is too broad")
        _need(reasons, privacy.get("raw_visual_recording") is False, "raw wardrobe imagery must not be retained")
    return reasons


def _contact_reasons(
    section: dict[str, Any],
    *,
    hand_anchor_id: str,
    object_anchor_id: str,
    maximum_distance_m: float = 0.04,
) -> list[str]:
    reasons: list[str] = []
    _need(reasons, section.get("touching") is True, "hand contact is not physically reported")
    _need(reasons, _text(section.get("hand_anchor_id")) == hand_anchor_id, "hand contact uses the wrong hand anchor")
    _need(reasons, _text(section.get("object_anchor_id")) == object_anchor_id, "hand contact uses the wrong garment anchor")
    _need(reasons, _at_most(section.get("distance_m"), maximum_distance_m), "hand is outside the contact distance")
    _need(reasons, _at_most(section.get("max_distance_m"), maximum_distance_m), "contact exceeded 0.04 m during the proof window")
    contact_frames = section.get("consecutive_contact_frames")
    _need(reasons, isinstance(contact_frames, int) and not isinstance(contact_frames, bool) and contact_frames >= 3, "contact needs at least three consecutive frames")
    return reasons


def _portal_crossing_reasons(
    section: dict[str, Any],
    *,
    portal_anchor_id: str,
    limb_anchor_ids: dict[str, str],
    outward: bool = False,
) -> list[str]:
    reasons: list[str] = []
    _need(reasons, _text(section.get("portal_anchor_id")) == portal_anchor_id, "sleeve crossing uses the wrong portal")
    _need(reasons, section.get("teleported") is False, "teleport/direct placement cannot prove sleeve crossing")
    expected_order = ["elbow", "forearm", "wrist"] if outward else ["wrist", "forearm", "elbow"]
    _need(reasons, section.get("crossing_order") == expected_order, "wrist, forearm, and elbow did not cross in a physically valid order")
    paths = _dict(section.get("segment_paths"))
    for segment in ("wrist", "forearm", "elbow"):
        path = _dict(paths.get(segment))
        before = _number(path.get("signed_distance_before_m"))
        after = _number(path.get("signed_distance_after_m"))
        _need(reasons, _text(path.get("limb_anchor_id")) == limb_anchor_ids[segment], f"sleeve crossing uses the wrong {segment} anchor")
        _need(reasons, path.get("crossed") is True, f"{segment} did not cross the sleeve portal")
        _need(reasons, path.get("continuous_path") is True, f"{segment} crossing has no continuous path")
        sample_count = path.get("path_sample_count")
        _need(reasons, isinstance(sample_count, int) and not isinstance(sample_count, bool) and sample_count >= 3, f"{segment} crossing needs at least three path samples")
        _need(reasons, _at_most(path.get("max_path_step_m"), 0.15), f"{segment} path contains an implausible discontinuity")
        if outward:
            _need(reasons, before is not None and before >= 0.02, f"{segment} removal path did not begin inside the sleeve portal")
            _need(reasons, after is not None and after <= -0.02, f"{segment} removal path did not end outside the sleeve portal")
        else:
            _need(reasons, before is not None and before <= -0.02, f"{segment} dressing path did not begin outside the sleeve portal")
            _need(reasons, after is not None and after >= 0.02, f"{segment} dressing path did not end inside the sleeve portal")
    return reasons


def _belt_continuity_reasons(
    definition: GarmentDefinition,
    section: dict[str, Any],
    item_instance_id: str,
) -> list[str]:
    reasons: list[str] = []
    _need(reasons, _text(section.get("left_endpoint_anchor_id")) == _anchor_id(definition, "belt_left_endpoint"), "left belt endpoint anchor is wrong")
    _need(reasons, _text(section.get("right_endpoint_anchor_id")) == _anchor_id(definition, "belt_right_endpoint"), "right belt endpoint anchor is wrong")
    _need(reasons, _text(section.get("left_endpoint_instance_id")) == item_instance_id, "left belt endpoint lost robe identity")
    _need(reasons, _text(section.get("right_endpoint_instance_id")) == item_instance_id, "right belt endpoint lost robe identity")
    _need(reasons, section.get("tracked_continuously") is True, "belt endpoints were not tracked continuously")
    _need(reasons, section.get("endpoint_substitution") is False, "belt endpoint substitution/duplication is reported")
    return reasons


def _gate_reasons(
    definition: GarmentDefinition,
    affordance: AffordanceSpec,
    evidence: dict[str, Any],
    item_instance_id: str,
) -> list[str]:
    gate = affordance.evidence_gate
    reasons: list[str] = []

    if gate == "hook_detach":
        contact = _dict(evidence.get("hook_contact"))
        reasons.extend(
            _contact_reasons(
                contact,
                hand_anchor_id=_anchor_id(definition, "hand_grip"),
                object_anchor_id=_anchor_id(definition, "garment_hook_loop"),
            )
        )
        _need(reasons, _text(contact.get("world_anchor_id")) == _anchor_id(definition, "world_wall_hook"), "contact is not associated with the declared wall hook")
        detach = _dict(evidence.get("detachment"))
        _need(reasons, detach.get("detached") is True, "robe has not detached from the hook")
        _need(reasons, _text(detach.get("garment_anchor_id")) == _anchor_id(definition, "garment_hook_loop"), "detachment uses the wrong garment loop")
        _need(reasons, _text(detach.get("source_anchor_id")) == _anchor_id(definition, "world_wall_hook"), "detachment uses the wrong source hook")
        _need(reasons, detach.get("hand_contact_maintained") is True, "hand contact was not maintained through detachment")
        _need(reasons, detach.get("source_copy_visible_after") is False, "source robe copy remains visible after detachment")

    elif gate in {
        "right_sleeve_crossing",
        "left_sleeve_crossing",
        "right_sleeve_exit",
        "left_sleeve_exit",
    }:
        side = "right" if gate.startswith("right") else "left"
        outward = gate.endswith("exit")
        section_name = f"{side}_sleeve_exit" if outward else f"{side}_sleeve_crossing"
        reasons.extend(
            _portal_crossing_reasons(
                _dict(evidence.get(section_name)),
                portal_anchor_id=_anchor_id(definition, f"{side}_sleeve_portal"),
                limb_anchor_ids={
                    "wrist": _anchor_id(definition, f"{side}_wrist_path"),
                    "forearm": _anchor_id(definition, f"{side}_forearm_path"),
                    "elbow": _anchor_id(definition, f"{side}_elbow_path"),
                },
                outward=outward,
            )
        )

    elif gate == "shoulder_settle":
        settle = _dict(evidence.get("shoulder_settle"))
        _need(reasons, _text(settle.get("garment_anchor_id")) == _anchor_id(definition, "garment_shoulders"), "shoulder evidence uses the wrong garment anchor")
        _need(reasons, _text(settle.get("body_anchor_id")) == _anchor_id(definition, "body_shoulders"), "shoulder evidence uses the wrong body anchor")
        _need(reasons, settle.get("left_supported") is True and settle.get("right_supported") is True, "robe is not supported on both shoulders")
        _need(reasons, settle.get("attachment_active") is True, "robe-to-body attachment is not active")
        _need(reasons, settle.get("skinned_to_verified_rig") is True, "robe is not skinned to the verified rig")
        _need(reasons, _at_most(settle.get("max_separation_m"), 0.04), "robe has not settled within 0.04 m of the shoulders")
        _need(reasons, _at_most(settle.get("max_collision_penetration_m"), 0.03), "shoulder settle has excessive clipping")
        _need(reasons, isinstance(settle.get("stable_sample_count"), int) and settle["stable_sample_count"] >= 3, "shoulder settle needs physical stability samples")

    elif gate == "belt_tie":
        continuity = _dict(evidence.get("belt_continuity"))
        reasons.extend(_belt_continuity_reasons(definition, continuity, item_instance_id))
        _need(reasons, continuity.get("left_hand_grasp") is True and continuity.get("right_hand_grasp") is True, "both belt ends were not grasped")
        tie = _dict(evidence.get("belt_tie"))
        _need(reasons, _text(tie.get("knot_anchor_id")) == _anchor_id(definition, "belt_knot"), "tie evidence uses the wrong knot anchor")
        _need(reasons, _text(tie.get("waist_anchor_id")) == _anchor_id(definition, "body_waist"), "tie evidence uses the wrong waist anchor")
        _need(reasons, tie.get("knot_formed") is True and tie.get("knot_secured") is True, "robe belt knot was not physically formed and secured")
        _need(reasons, tie.get("hand_contact_during_tie") is True, "belt tie has no hand-contact evidence")
        _need(reasons, tie.get("continuous_hand_paths") is True, "belt tie has no continuous two-hand path")
        _need(reasons, isinstance(tie.get("knot_path_sample_count"), int) and not isinstance(tie.get("knot_path_sample_count"), bool) and tie["knot_path_sample_count"] >= 5, "belt tie needs a sampled knot-forming path")
        _need(reasons, isinstance(tie.get("wrap_crossing_count"), int) and not isinstance(tie.get("wrap_crossing_count"), bool) and tie["wrap_crossing_count"] >= 1, "belt ends never crossed during the tie")
        _need(reasons, _at_least(tie.get("tightening_displacement_m"), 0.03), "belt tie has no measurable tightening motion")
        _need(reasons, isinstance(tie.get("stable_sample_count"), int) and tie["stable_sample_count"] >= 3, "belt knot has no stable physical samples")

    elif gate == "belt_untie":
        continuity = _dict(evidence.get("belt_continuity"))
        reasons.extend(_belt_continuity_reasons(definition, continuity, item_instance_id))
        untie = _dict(evidence.get("belt_untie"))
        _need(reasons, _text(untie.get("knot_anchor_id")) == _anchor_id(definition, "belt_knot"), "untie evidence uses the wrong knot anchor")
        _need(reasons, untie.get("knot_released") is True, "belt knot remains tied")
        _need(reasons, untie.get("hand_contact_during_untie") is True, "belt untie has no hand-contact evidence")
        _need(reasons, untie.get("continuous_hand_paths") is True, "belt untie has no continuous two-hand path")
        _need(reasons, isinstance(untie.get("path_sample_count"), int) and not isinstance(untie.get("path_sample_count"), bool) and untie["path_sample_count"] >= 4, "belt untie needs a sampled release path")
        _need(reasons, untie.get("endpoints_separated") is True, "belt endpoints are not visibly separated after untying")

    elif gate == "worn_movement":
        movement = _dict(evidence.get("worn_movement"))
        _need(reasons, movement.get("teleported") is False, "teleport/direct placement cannot prove worn movement")
        _need(reasons, movement.get("garment_follows_verified_rig") is True, "garment did not follow the verified rig")
        _need(reasons, movement.get("garment_detached") is False, "garment detached during movement")
        _need(reasons, _at_most(movement.get("max_collision_penetration_m"), 0.04), "worn movement has excessive clipping")

        walk = _dict(movement.get("walk"))
        _need(reasons, walk.get("grounded_route") is True, "worn walking route is not grounded")
        walk_samples = walk.get("path_sample_count")
        _need(reasons, isinstance(walk_samples, int) and not isinstance(walk_samples, bool) and walk_samples >= 6, "worn walking needs at least six path samples")
        _need(reasons, _at_least(walk.get("displacement_m"), 0.50), "worn walking displacement is too small")

        turn = _dict(movement.get("turn"))
        _need(reasons, turn.get("continuous_root_path") is True, "worn turn has no continuous root path")
        turn_samples = turn.get("root_sample_count")
        _need(reasons, isinstance(turn_samples, int) and not isinstance(turn_samples, bool) and turn_samples >= 4, "worn turn needs at least four root samples")
        _need(reasons, _at_least(turn.get("rotation_degrees"), 45.0), "worn turn rotation is too small")
        _need(reasons, turn.get("feet_grounded") is True, "feet are not grounded during the worn turn")

        sit = _dict(movement.get("sit"))
        _need(reasons, sit.get("continuous_posture_transition") is True, "sit transition is not continuous")
        sit_samples = sit.get("pelvis_path_sample_count")
        _need(reasons, isinstance(sit_samples, int) and not isinstance(sit_samples, bool) and sit_samples >= 4, "sit transition needs a sampled pelvis path")
        _need(reasons, bool(_text(sit.get("support_surface_instance_id"))), "sit transition has no support-surface identity")
        _need(reasons, sit.get("support_contact") is True and sit.get("supported") is True, "body is not physically supported while seated")
        supported_frames = sit.get("supported_frame_count")
        _need(reasons, isinstance(supported_frames, int) and not isinstance(supported_frames, bool) and supported_frames >= 3, "sit support needs at least three frames")
        _need(reasons, sit.get("falling") is False, "body is falling during the sit proof")

        stand = _dict(movement.get("stand"))
        _need(reasons, stand.get("continuous_posture_transition") is True, "stand transition is not continuous")
        stand_samples = stand.get("pelvis_path_sample_count")
        _need(reasons, isinstance(stand_samples, int) and not isinstance(stand_samples, bool) and stand_samples >= 4, "stand transition needs a sampled pelvis path")
        _need(reasons, stand.get("feet_grounded") is True and stand.get("standing_supported") is True, "body is not grounded after standing")
        _need(reasons, stand.get("seat_support_released") is True, "seat support was not released during standing")
        _need(reasons, stand.get("falling") is False, "body is falling during the stand proof")

        support = _dict(movement.get("support_continuity"))
        surface_id = _text(sit.get("support_surface_instance_id"))
        _need(reasons, _text(support.get("sit_surface_instance_id")) == surface_id, "sit support identity is not continuous")
        _need(reasons, _text(support.get("stand_source_surface_instance_id")) == surface_id, "stand did not depart from the same support surface")
        matching_surfaces = support.get("matching_surface_nodes")
        _need(reasons, isinstance(matching_surfaces, int) and not isinstance(matching_surfaces, bool) and matching_surfaces == 1, "support evidence does not identify exactly one surface instance")

    elif gate == "removal":
        removal = _dict(evidence.get("removal"))
        reasons.extend(
            _portal_crossing_reasons(
                _dict(removal.get("left_sleeve_exit")),
                portal_anchor_id=_anchor_id(definition, "left_sleeve_portal"),
                limb_anchor_ids={
                    "wrist": _anchor_id(definition, "left_wrist_path"),
                    "forearm": _anchor_id(definition, "left_forearm_path"),
                    "elbow": _anchor_id(definition, "left_elbow_path"),
                },
                outward=True,
            )
        )
        reasons.extend(
            _portal_crossing_reasons(
                _dict(removal.get("right_sleeve_exit")),
                portal_anchor_id=_anchor_id(definition, "right_sleeve_portal"),
                limb_anchor_ids={
                    "wrist": _anchor_id(definition, "right_wrist_path"),
                    "forearm": _anchor_id(definition, "right_forearm_path"),
                    "elbow": _anchor_id(definition, "right_elbow_path"),
                },
                outward=True,
            )
        )
        _need(reasons, removal.get("shoulder_attachment_removed") is True, "robe remains attached to the shoulders")
        _need(reasons, removal.get("garment_held_after_exit") is True, "robe is not held after removal")
        _need(reasons, _text(removal.get("hand_anchor_id")) == _anchor_id(definition, "hand_grip"), "removed robe is not held at the declared grip")

    elif gate == "rehang":
        rehang = _dict(evidence.get("rehang"))
        _need(reasons, _text(rehang.get("garment_anchor_id")) == _anchor_id(definition, "garment_hook_loop"), "rehang uses the wrong robe loop")
        _need(reasons, _text(rehang.get("world_anchor_id")) == _anchor_id(definition, "world_wall_hook"), "rehang uses the wrong wall hook")
        _need(reasons, rehang.get("loop_hook_contact") is True, "robe loop did not contact the hook")
        _need(reasons, _at_most(rehang.get("max_loop_hook_distance_m"), 0.04), "robe loop exceeded 0.04 m from the hook during contact")
        rehang_frames = rehang.get("contact_frame_count")
        _need(reasons, isinstance(rehang_frames, int) and not isinstance(rehang_frames, bool) and rehang_frames >= 3, "rehang contact needs at least three frames")
        _need(reasons, rehang.get("hand_contact_until_attached") is True, "hand released before the robe attached")
        _need(reasons, rehang.get("attached") is True and rehang.get("supported_by_hook") is True, "robe is not supported by the hook")
        _need(reasons, rehang.get("hand_released_after_attachment") is True, "hand did not release after attachment")
        _need(reasons, isinstance(rehang.get("stable_sample_count"), int) and rehang["stable_sample_count"] >= 3, "rehang has no stable support samples")

    elif gate == "bed_placement":
        placement = _dict(evidence.get("bed_placement"))
        _need(reasons, _text(placement.get("surface_anchor_id")) == _anchor_id(definition, "bed_surface"), "placement uses the wrong bed surface")
        _need(reasons, placement.get("hand_contact_before_release") is True, "placement has no hand contact before release")
        _need(reasons, placement.get("surface_contact") is True and placement.get("supported") is True, "robe is not physically supported by the bed")
        _need(reasons, placement.get("hand_released") is True, "hand has not released the placed robe")
        _need(reasons, placement.get("ballistic_throw") is False, "a throw cannot pass as deliberate bed placement")
        _need(reasons, isinstance(placement.get("stable_sample_count"), int) and placement["stable_sample_count"] >= 3, "bed placement has no stable support samples")

    elif gate == "throw_release":
        release = _dict(evidence.get("throw_release"))
        _need(reasons, _text(release.get("target_surface_anchor_id")) == _anchor_id(definition, "bed_surface"), "throw has the wrong target surface")
        _need(reasons, release.get("released_from_hand") is True and release.get("source_hand_empty") is True, "robe was not physically released from the hand")
        _need(reasons, release.get("physics_driven") is True, "throw trajectory is not physics-driven")
        _need(reasons, release.get("teleported") is False, "teleport/direct placement cannot prove a throw")
        _need(reasons, _at_least(release.get("release_speed_mps"), 0.10), "throw has no measurable release velocity")
        _need(reasons, isinstance(release.get("trajectory_sample_count"), int) and release["trajectory_sample_count"] >= 3, "throw needs a sampled trajectory")

    elif gate == "throw_settle":
        settle = _dict(evidence.get("throw_settle"))
        _need(reasons, _text(settle.get("surface_anchor_id")) == _anchor_id(definition, "bed_surface"), "throw settled on the wrong surface")
        _need(reasons, settle.get("physics_driven") is True, "throw settling is not physics-driven")
        _need(reasons, settle.get("teleported") is False, "teleport/direct placement cannot prove throw settling")
        _need(reasons, settle.get("bed_collision_contact") is True and settle.get("supported") is True, "thrown robe is not supported by the bed")
        _need(reasons, settle.get("continuous_from_release") is True, "throw-to-settle item continuity is missing")
        _need(reasons, _at_most(settle.get("max_linear_speed_mps"), 0.08), "robe is still moving too quickly to be settled")
        _need(reasons, _at_most(settle.get("max_angular_speed_rps"), 0.15), "robe is still rotating too quickly to be settled")
        _need(reasons, isinstance(settle.get("stable_sample_count"), int) and settle["stable_sample_count"] >= 4, "throw settle needs stable physics samples")

    elif gate == "bed_pickup":
        pickup = _dict(evidence.get("bed_pickup"))
        _need(reasons, _text(pickup.get("surface_anchor_id")) == _anchor_id(definition, "bed_surface"), "pickup uses the wrong bed surface")
        _need(reasons, pickup.get("hand_contact_before_detach") is True, "bed pickup has no hand contact before detachment")
        _need(reasons, pickup.get("surface_support_removed") is True, "bed still supports the robe after pickup")
        _need(reasons, pickup.get("held") is True, "robe is not held after bed pickup")
        _need(reasons, pickup.get("source_copy_visible_after") is False, "a separate bed copy remains after pickup")

    else:
        reasons.append(f"unsupported evidence gate: {gate}")

    return reasons


def evaluate_garment_transition(
    definition: GarmentDefinition,
    affordance: AffordanceSpec,
    evidence: dict[str, Any],
    *,
    transaction_id: str,
    item_instance_id: str,
    consent_record_id: str = "",
) -> EvidenceDecision:
    """Evaluate physical observations for one exact pending transition."""

    evidence = _dict(evidence)
    evidence_context_sha256 = _canonical_sha256(
        {
            "schema_version": 1,
            "transaction_id": transaction_id,
            "item_instance_id": item_instance_id,
            "affordance_id": affordance.affordance_id,
            "evidence_gate": affordance.evidence_gate,
            "consent_record_id": consent_record_id,
            "garment_type_id": definition.garment_type_id,
            "asset_sha256": definition.asset_sha256,
            "compatible_body_sha256": definition.compatible_body_sha256,
            "compatible_rig_sha256": definition.compatible_rig_sha256,
            "compatible_subject_id": definition.compatible_subject_id,
            "maturity_class": definition.maturity_class.value,
            "evidence": evidence,
        }
    )
    reasons = _identity_reasons(
        definition,
        affordance,
        evidence,
        transaction_id=transaction_id,
        item_instance_id=item_instance_id,
        consent_record_id=consent_record_id,
    )
    reasons.extend(_gate_reasons(definition, affordance, evidence, item_instance_id))
    if not evidence_context_sha256:
        reasons.append("complete evidence context is not canonical JSON and cannot be hashed")
    unique = tuple(dict.fromkeys(reason for reason in reasons if reason))
    raw_trace_sha256 = _computed_raw_trace_sha256(evidence)
    passed = not unique
    decision_sha256 = compute_decision_sha256(
        transaction_id=transaction_id,
        item_instance_id=item_instance_id,
        evidence_gate=affordance.evidence_gate,
        raw_trace_sha256=raw_trace_sha256,
        evidence_context_sha256=evidence_context_sha256,
        passed=passed,
        reasons=unique,
    )
    return EvidenceDecision(
        transaction_id=transaction_id,
        item_instance_id=item_instance_id,
        evidence_gate=affordance.evidence_gate,
        raw_trace_sha256=raw_trace_sha256,
        evidence_context_sha256=evidence_context_sha256,
        decision_sha256=decision_sha256,
        passed=passed,
        reasons=unique,
    )
