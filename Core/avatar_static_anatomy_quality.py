"""Stage-A quality rules for private adult avatar static review.

This module deliberately does not certify motion, soft tissue, collision, or
runtime use.  It records the evidence a static candidate must supply before an
owner can review its likeness and anatomy.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping, Sequence


REQUIRED_VIEWS = {
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

ANATOMY_ZONES = {
    "pubic_transition",
    "root_connection",
    "shaft",
    "glans",
    "scrotal_transition",
    "perineal_transition",
}

SHADER_CHANNELS = {
    "base_albedo",
    "roughness_specular",
    "subsurface_scattering",
    "normal_or_bump",
}

AWAITING_STATIC_REVIEW = "AWAITING ROBERT STATIC LIKENESS REVIEW"
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_VISUAL_DECISIONS = {
    "PENDING_OWNER_REVIEW",
    "REJECTED_BY_OWNER",
    "APPROVED_BY_OWNER",
}
_ATTACHMENT_DECISIONS = {
    "PENDING_OWNER_REVIEW",
    "REJECTED",
    "ACCEPTED_BY_OWNER",
}


@dataclass(frozen=True)
class StaticReviewEvidence:
    views: Sequence[str]
    anatomy_zones: Sequence[str]
    shader_channels: Sequence[str]
    hair_color_class: str
    hair_is_removable: bool
    anatomy_is_primary_component: bool
    main_skin_boundary_edges: int
    main_skin_nonmanifold_edges: int
    ao_baked_into_albedo: bool
    runtime_claimed: bool
    motion_claimed: bool
    candidate_sha256: str
    rendered_view_sha256: Mapping[str, str]
    rendered_view_candidate_sha256: Mapping[str, str]
    rendered_visual_review_decision: str
    pelvis_attachment_visual_status: str
    pelvis_open_or_spatial_gap_detected: bool
    visual_rejection_reasons: Sequence[str]


def validate_static_review(evidence: StaticReviewEvidence) -> Mapping[str, object]:
    missing_views = sorted(REQUIRED_VIEWS.difference(evidence.views))
    missing_zones = sorted(ANATOMY_ZONES.difference(evidence.anatomy_zones))
    missing_channels = sorted(SHADER_CHANNELS.difference(evidence.shader_channels))
    failures = []
    if missing_views:
        failures.append("MISSING_REQUIRED_REVIEW_VIEWS")
    if missing_zones:
        failures.append("ANATOMY_ZONE_EVIDENCE_INCOMPLETE")
    if missing_channels:
        failures.append("SHADER_CHANNEL_SEPARATION_INCOMPLETE")
    if evidence.hair_color_class not in {"light_blonde", "blonde", "dark_blonde"}:
        failures.append("OWNER_HAIR_COLOR_MISMATCH")
    if not evidence.hair_is_removable:
        failures.append("STATIC_HAIR_NOT_REMOVABLE")
    if not evidence.anatomy_is_primary_component:
        failures.append("ANATOMY_NOT_CONNECTED_TO_PRIMARY_SKIN")
    if evidence.main_skin_boundary_edges:
        failures.append("PRIMARY_SKIN_HAS_OPEN_BOUNDARIES")
    if evidence.main_skin_nonmanifold_edges:
        failures.append("PRIMARY_SKIN_HAS_NONMANIFOLD_EDGES")
    if evidence.ao_baked_into_albedo:
        failures.append("AO_OR_CAVITY_BAKED_INTO_SKIN_COLOR")
    if evidence.runtime_claimed or evidence.motion_claimed:
        failures.append("STATIC_REVIEW_MAKES_UNPROVEN_RUNTIME_CLAIM")

    candidate_hash = str(evidence.candidate_sha256).strip().lower()
    if not _SHA256_RE.fullmatch(candidate_hash):
        failures.append("CANDIDATE_SHA256_MISSING_OR_INVALID")

    rendered_hashes = {
        str(view): str(value).strip().lower()
        for view, value in evidence.rendered_view_sha256.items()
    }
    rendered_bindings = {
        str(view): str(value).strip().lower()
        for view, value in evidence.rendered_view_candidate_sha256.items()
    }
    missing_render_hashes = sorted(REQUIRED_VIEWS.difference(rendered_hashes))
    missing_render_bindings = sorted(REQUIRED_VIEWS.difference(rendered_bindings))
    invalid_render_hashes = sorted(
        view
        for view in REQUIRED_VIEWS.intersection(rendered_hashes)
        if not _SHA256_RE.fullmatch(rendered_hashes[view])
    )
    mismatched_render_bindings = sorted(
        view
        for view in REQUIRED_VIEWS.intersection(rendered_bindings)
        if (
            not _SHA256_RE.fullmatch(rendered_bindings[view])
            or rendered_bindings[view] != candidate_hash
        )
    )
    if missing_render_hashes:
        failures.append("RENDERED_REVIEW_HASHES_INCOMPLETE")
    if missing_render_bindings:
        failures.append("RENDERED_REVIEW_CANDIDATE_BINDINGS_INCOMPLETE")
    if invalid_render_hashes:
        failures.append("RENDERED_REVIEW_HASH_INVALID")
    if mismatched_render_bindings:
        failures.append("RENDERED_REVIEW_NOT_BOUND_TO_CANDIDATE")
    required_hashes = [
        rendered_hashes[view]
        for view in REQUIRED_VIEWS
        if view in rendered_hashes and _SHA256_RE.fullmatch(rendered_hashes[view])
    ]
    if (
        len(required_hashes) == len(REQUIRED_VIEWS)
        and len(set(required_hashes)) != len(REQUIRED_VIEWS)
    ):
        failures.append("RENDERED_REVIEW_VIEWS_NOT_DISTINCT")

    visual_decision = str(evidence.rendered_visual_review_decision).strip().upper()
    attachment_decision = str(evidence.pelvis_attachment_visual_status).strip().upper()
    if visual_decision not in _VISUAL_DECISIONS:
        failures.append("RENDERED_VISUAL_REVIEW_DECISION_INVALID")
    if attachment_decision not in _ATTACHMENT_DECISIONS:
        failures.append("PELVIS_ATTACHMENT_VISUAL_STATUS_INVALID")
    if evidence.pelvis_open_or_spatial_gap_detected:
        failures.append("PELVIS_OPEN_OR_SPATIAL_GAP_VISIBLE")
    if attachment_decision == "REJECTED":
        failures.append("PELVIS_ATTACHMENT_VISUALLY_REJECTED")
    visual_rejection_reasons = [
        str(reason).strip()
        for reason in evidence.visual_rejection_reasons
        if str(reason).strip()
    ]
    if visual_rejection_reasons:
        failures.append("RENDERED_VISUAL_REJECTION_RECORDED")
    if visual_decision == "REJECTED_BY_OWNER":
        failures.append("RENDERED_VISUAL_REVIEW_REJECTED_BY_OWNER")
    if visual_decision == "APPROVED_BY_OWNER" and attachment_decision != "ACCEPTED_BY_OWNER":
        failures.append("OWNER_APPROVAL_CONTRADICTS_PELVIS_ATTACHMENT_REVIEW")

    owner_approved = (
        not failures
        and visual_decision == "APPROVED_BY_OWNER"
        and attachment_decision == "ACCEPTED_BY_OWNER"
    )
    review_status = "STATIC_OWNER_APPROVED" if owner_approved else AWAITING_STATIC_REVIEW
    return {
        "status": review_status,
        "technical_gate_status": (
            "PASS_STATIC_TECHNICAL_GATE" if not failures else "BLOCKED"
        ),
        "owner_likeness_approval": "RECORDED" if owner_approved else "REQUIRED",
        "missing_views": missing_views,
        "missing_anatomy_zones": missing_zones,
        "missing_shader_channels": missing_channels,
        "missing_render_hashes": missing_render_hashes,
        "missing_render_candidate_bindings": missing_render_bindings,
        "invalid_render_hashes": invalid_render_hashes,
        "mismatched_render_candidate_bindings": mismatched_render_bindings,
        "rendered_visual_review_decision": visual_decision,
        "pelvis_attachment_visual_status": attachment_decision,
        "visual_rejection_reasons": visual_rejection_reasons,
        "failures": failures,
        "runtime_activation_allowed": False,
        "stage_b_motion_realism": "DEFERRED_UNTIL_OWNER_STATIC_APPROVAL",
    }


def validate_bounded_geometry_repair(report: Mapping[str, object]) -> Mapping[str, object]:
    """Reject global/body-wide shortcuts and any protected-region drift."""
    failures = []
    if report.get("global_scaling_used"):
        failures.append("GLOBAL_SCALING_PROHIBITED")
    if report.get("boolean_union_used"):
        failures.append("BOOLEAN_UNION_REPAIR_PROHIBITED")
    if report.get("imported_reference_surface_used"):
        failures.append("REFERENCE_SURFACE_TRANSFER_PROHIBITED")
    if int(report.get("changed_outside_mask_count", 0)):
        failures.append("GEOMETRY_CHANGED_OUTSIDE_APPROVED_MASK")
    for key in (
        "hands_fingers_forearms_delta",
        "lower_legs_feet_delta",
        "head_face_neck_delta",
    ):
        if float(report.get(key, 0.0)) > 1e-9:
            failures.append(f"PROTECTED_REGION_CHANGED:{key}")
    return {
        "status": "PASS_BOUNDED_GEOMETRY_GATE" if not failures else "BLOCKED",
        "failures": failures,
    }


def validate_adult_male_surface_landmarks(
    report: Mapping[str, object],
) -> Mapping[str, object]:
    """Validate a connected adult-male Stage-A surface from measured landmarks.

    This is a reusable Avatar Builder gate, not a likeness generator and not a
    substitute for rendered owner review.  Exact proportions remain controlled
    by the authorized adult subject's references.  The generic rules here only
    reject structurally impossible or visibly disconnected constructions:

    * the external anatomy and surrounding pubic/perineal skin are one primary
      surface component;
    * no superior background tunnel or side attachment gap is visible;
    * the penile root is superior to the scrotal root;
    * the free shaft proceeds away from its root as one continuous body;
    * the scrotum remains inferior and posterior to the shaft in the supplied
      coordinate convention; and
    * the glans/neck measurements describe a continuous distal transition.

    Coordinates are expected in metres with Z up and negative Y toward the
    anterior/front of the body.  All absolute tolerances scale with body height.
    """

    failures: list[str] = []

    def _number(key: str) -> float | None:
        value = report.get(key)
        if isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _point(key: str) -> tuple[float, float, float] | None:
        value = report.get(key)
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            return None
        if len(value) != 3:
            return None
        try:
            return tuple(float(component) for component in value)
        except (TypeError, ValueError):
            return None

    if str(report.get("coordinate_convention") or "").strip().lower() != (
        "z_up_negative_y_front"
    ):
        failures.append("ANATOMY_COORDINATE_CONVENTION_MISSING")

    body_height = _number("body_height_m")
    if body_height is None or body_height <= 0.5:
        failures.append("BODY_HEIGHT_MEASUREMENT_INVALID")
        body_height = None

    if int(report.get("primary_skin_component_count", 0) or 0) != 1:
        failures.append("PRIMARY_SKIN_NOT_ONE_CONNECTED_COMPONENT")
    if report.get("anatomy_primary_skin_same_component") is not True:
        failures.append("ANATOMY_NOT_IN_PRIMARY_SKIN_COMPONENT")
    if int(report.get("main_skin_boundary_edges", 0) or 0):
        failures.append("PRIMARY_SKIN_HAS_OPEN_BOUNDARIES")
    if int(report.get("main_skin_nonmanifold_edges", 0) or 0):
        failures.append("PRIMARY_SKIN_HAS_NONMANIFOLD_EDGES")
    if int(report.get("separate_anatomy_mesh_count", 0) or 0):
        failures.append("SEPARATE_ANATOMY_MESH_PRESENT")

    for key, failure in (
        ("front_superior_gap_rays", "SUPERIOR_PUBIC_BACKGROUND_GAP_VISIBLE"),
        ("side_root_gap_rays", "SIDE_ROOT_BACKGROUND_GAP_VISIBLE"),
        ("three_quarter_root_gap_rays", "THREE_QUARTER_ROOT_GAP_VISIBLE"),
        ("side_silhouette_self_intersections", "SIDE_SILHOUETTE_SELF_INTERSECTS"),
    ):
        value = _number(key)
        if value is None:
            failures.append(f"MEASUREMENT_MISSING:{key}")
        elif value > 0:
            failures.append(failure)

    root_surface_distance = _number("shaft_root_surface_distance_m")
    scrotal_surface_distance = _number("scrotal_root_surface_distance_m")
    if body_height is not None:
        maximum_root_gap = body_height * 0.004
        if root_surface_distance is None:
            failures.append("MEASUREMENT_MISSING:shaft_root_surface_distance_m")
        elif root_surface_distance > maximum_root_gap:
            failures.append("SHAFT_ROOT_NOT_CONTINUOUS_WITH_PUBIC_SURFACE")
        if scrotal_surface_distance is None:
            failures.append("MEASUREMENT_MISSING:scrotal_root_surface_distance_m")
        elif scrotal_surface_distance > maximum_root_gap:
            failures.append("SCROTAL_ROOT_NOT_CONTINUOUS_WITH_PERINEAL_SURFACE")

    shaft_root = _point("shaft_root_center")
    shaft_distal = _point("shaft_distal_center")
    scrotal_root = _point("scrotal_root_center")
    scrotal_lowest = _point("scrotal_lowest_center")
    for key, value in (
        ("shaft_root_center", shaft_root),
        ("shaft_distal_center", shaft_distal),
        ("scrotal_root_center", scrotal_root),
        ("scrotal_lowest_center", scrotal_lowest),
    ):
        if value is None:
            failures.append(f"MEASUREMENT_MISSING:{key}")

    if shaft_root and scrotal_root and shaft_root[2] <= scrotal_root[2]:
        failures.append("SHAFT_ROOT_NOT_SUPERIOR_TO_SCROTAL_ROOT")
    if shaft_root and shaft_distal and shaft_distal[2] >= shaft_root[2]:
        failures.append("FREE_SHAFT_DOES_NOT_PROCEED_INFERIORLY_FROM_ROOT")
    if scrotal_root and scrotal_lowest and scrotal_lowest[2] >= scrotal_root[2]:
        failures.append("SCROTAL_ENVELOPE_HAS_NO_INFERIOR_EXTENT")
    if shaft_distal and scrotal_root and shaft_distal[1] >= scrotal_root[1]:
        failures.append("SHAFT_NOT_ANTERIOR_TO_SCROTAL_ENVELOPE")

    shaft_width = _number("shaft_body_width_m")
    glans_width = _number("glans_max_width_m")
    glans_neck_width = _number("glans_neck_width_m")
    if (
        shaft_width is None
        or glans_width is None
        or glans_neck_width is None
        or min(shaft_width, glans_width, glans_neck_width) <= 0
    ):
        failures.append("GLANS_SHAFT_MEASUREMENTS_INVALID")
    else:
        if glans_width <= glans_neck_width:
            failures.append("GLANS_NECK_TRANSITION_NOT_EXPRESSED")
        ratio = glans_width / shaft_width
        if not 0.75 <= ratio <= 1.40:
            failures.append("GLANS_TO_SHAFT_RATIO_IMPLAUSIBLE")

    if report.get("scrotal_bilateral_envelope_present") is not True:
        failures.append("SCROTAL_BILATERAL_ENVELOPE_NOT_EVIDENCED")
    if report.get("scrotal_raphe_continuity_present") is not True:
        failures.append("SCROTAL_MIDLINE_CONTINUITY_NOT_EVIDENCED")
    if report.get("perineal_transition_continuous") is not True:
        failures.append("PERINEAL_TRANSITION_NOT_CONTINUOUS")

    return {
        "status": (
            "PASS_ADULT_MALE_SURFACE_LANDMARK_GATE"
            if not failures
            else "BLOCKED"
        ),
        "failures": list(dict.fromkeys(failures)),
        "owner_visual_review_still_required": True,
        "runtime_activation_allowed": False,
        "exact_proportion_authority": "AUTHORIZED_OWNER_REFERENCES",
        "general_structure_authority": (
            "AUTHORIZED_ADULT_ANATOMY_REFERENCE_AND_MEDICAL_ANATOMY"
        ),
    }
