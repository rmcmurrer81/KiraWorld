"""Fail-closed evidence coverage for real-place notebook-world areas.

The World Builder may draft only the parts of a real place that are supported
by reviewed references.  This module does not download sources, author
geometry, approve a build, or open a door.  It decides whether an area has
enough independent evidence to enter *draft authoring* and verifies that every
unsupported destination remains behind a closed, locked, solid portal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


CONTRACT_KIND = "world_area_reference_evidence_contract"
SOURCE_KINDS = {
    "photo",
    "video",
    "floor_plan",
    "site_plan",
    "section",
    "elevation",
    "measurement",
    "official_map",
    "owner_note",
}
RIGHTS_MODES = {
    "owner_supplied_private_reference",
    "official_fact_reference",
    "reference_only_no_asset_reuse",
    "reusable_asset_with_terms",
    "restricted_service_visualization_only",
    "unknown_locked",
}
TRUTH_USES = {
    "visual_feature_observation",
    "layout_topology",
    "scale_measurement",
    "runtime_asset",
    "context_only",
}
LOCKED_PORTAL_STATE = "closed_locked_solid"


class WorldReferenceEvidenceError(ValueError):
    """Raised when a contract could turn unsupported evidence into geometry."""


@dataclass(frozen=True)
class AreaEvidenceDecision:
    area_id: str
    evidence_sufficient_for_draft: bool
    photo_viewpoints: int
    video_viewpoints: int
    has_layout_source: bool
    has_scale_source: bool
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "area_id": self.area_id,
            "evidence_sufficient_for_draft": self.evidence_sufficient_for_draft,
            "photo_viewpoints": self.photo_viewpoints,
            "video_viewpoints": self.video_viewpoints,
            "has_layout_source": self.has_layout_source,
            "has_scale_source": self.has_scale_source,
            "reasons": list(self.reasons),
        }


def _nonempty_string(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorldReferenceEvidenceError(f"{label} must be a non-empty string")
    return value.strip()


def _bounded_int(value: Any, *, label: str, minimum: int, maximum: int = 100) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise WorldReferenceEvidenceError(
            f"{label} must be an integer from {minimum} to {maximum}"
        )
    return value


def _source_can_support_geometry(source: Mapping[str, Any]) -> bool:
    """Return whether policy allows this source to support manual geometry facts."""

    rights_mode = source["rights_mode"]
    truth_use = source["truth_use"]
    if rights_mode in {"unknown_locked", "restricted_service_visualization_only"}:
        return False
    return truth_use in {
        "visual_feature_observation",
        "layout_topology",
        "scale_measurement",
    }


def _validate_source(source: Mapping[str, Any], *, label: str) -> None:
    _nonempty_string(source.get("source_id"), label=f"{label}.source_id")
    kind = source.get("kind")
    if kind not in SOURCE_KINDS:
        raise WorldReferenceEvidenceError(f"{label}.kind is unsupported")
    rights_mode = source.get("rights_mode")
    if rights_mode not in RIGHTS_MODES:
        raise WorldReferenceEvidenceError(f"{label}.rights_mode is unsupported")
    truth_use = source.get("truth_use")
    if truth_use not in TRUTH_USES:
        raise WorldReferenceEvidenceError(f"{label}.truth_use is unsupported")
    _nonempty_string(source.get("provenance"), label=f"{label}.provenance")

    if kind in {"photo", "video"}:
        _nonempty_string(source.get("viewpoint_id"), label=f"{label}.viewpoint_id")
    elif source.get("viewpoint_id") not in {None, ""}:
        raise WorldReferenceEvidenceError(f"{label}.viewpoint_id belongs only on photo/video evidence")

    if rights_mode == "restricted_service_visualization_only" and truth_use != "context_only":
        raise WorldReferenceEvidenceError(
            f"{label} is restricted visualization content and may only be context_only"
        )
    if rights_mode == "unknown_locked" and truth_use != "context_only":
        raise WorldReferenceEvidenceError(f"{label} has unknown rights and may only be context_only")
    if truth_use == "runtime_asset" and rights_mode != "reusable_asset_with_terms":
        raise WorldReferenceEvidenceError(
            f"{label} may be a runtime asset only with explicit reusable-asset terms"
        )
    if rights_mode == "reference_only_no_asset_reuse" and truth_use == "runtime_asset":
        raise WorldReferenceEvidenceError(f"{label} is reference-only and cannot become a runtime asset")


def _area_decision(area: Mapping[str, Any], policy: Mapping[str, Any]) -> AreaEvidenceDecision:
    area_id = _nonempty_string(area.get("area_id"), label="area.area_id")
    sources = area.get("sources")
    if not isinstance(sources, list):
        raise WorldReferenceEvidenceError(f"Area {area_id!r} sources must be a list")

    source_ids: set[str] = set()
    photo_views: set[str] = set()
    video_views: set[str] = set()
    has_layout = False
    has_scale = False
    for index, source in enumerate(sources):
        if not isinstance(source, Mapping):
            raise WorldReferenceEvidenceError(f"Area {area_id!r} source {index} must be an object")
        _validate_source(source, label=f"areas[{area_id}].sources[{index}]")
        source_id = str(source["source_id"])
        if source_id in source_ids:
            raise WorldReferenceEvidenceError(f"Area {area_id!r} repeats source_id {source_id!r}")
        source_ids.add(source_id)
        if not _source_can_support_geometry(source):
            continue
        if source["kind"] == "photo":
            photo_views.add(str(source["viewpoint_id"]))
        elif source["kind"] == "video":
            video_views.add(str(source["viewpoint_id"]))
        if source["kind"] in {"floor_plan", "site_plan", "section", "official_map"}:
            has_layout = has_layout or source["truth_use"] == "layout_topology"
        if source["kind"] in {"measurement", "section", "elevation"}:
            has_scale = has_scale or source["truth_use"] == "scale_measurement"

    min_photos = int(policy["minimum_distinct_photo_viewpoints"])
    min_videos = int(policy["minimum_distinct_video_viewpoints"])
    reasons: list[str] = []
    if len(photo_views) < min_photos:
        reasons.append(f"needs {min_photos - len(photo_views)} more distinct photo viewpoint(s)")
    if len(video_views) < min_videos:
        reasons.append(f"needs {min_videos - len(video_views)} more distinct video viewpoint(s)")
    if policy["layout_source_required"] is True and not has_layout:
        reasons.append("needs a reviewed plan/map source for layout topology")
    if policy["scale_source_required"] is True and not has_scale:
        reasons.append("needs a reviewed measurement/section/elevation source for scale")

    sufficient = not reasons
    declared = area.get("evidence_sufficient_for_draft")
    if declared is not sufficient:
        raise WorldReferenceEvidenceError(
            f"Area {area_id!r} evidence_sufficient_for_draft must be {str(sufficient).lower()}"
        )
    if area.get("runtime_approved") is not False:
        raise WorldReferenceEvidenceError(f"Area {area_id!r} runtime_approved must remain false")

    return AreaEvidenceDecision(
        area_id=area_id,
        evidence_sufficient_for_draft=sufficient,
        photo_viewpoints=len(photo_views),
        video_viewpoints=len(video_views),
        has_layout_source=has_layout,
        has_scale_source=has_scale,
        reasons=tuple(reasons),
    )


def validate_reference_evidence_contract(
    contract: Mapping[str, Any],
) -> tuple[AreaEvidenceDecision, ...]:
    """Validate a reference contract and return deterministic area decisions."""

    if contract.get("contract_kind") != CONTRACT_KIND:
        raise WorldReferenceEvidenceError("Unexpected world reference contract kind")
    if contract.get("schema_version") != 1:
        raise WorldReferenceEvidenceError("schema_version must be 1")
    _nonempty_string(contract.get("world_id"), label="world_id")
    if contract.get("status") != "reference_review_draft_not_runtime_approval":
        raise WorldReferenceEvidenceError("Contract must remain a reference-review draft")

    policy = contract.get("coverage_policy")
    if not isinstance(policy, Mapping):
        raise WorldReferenceEvidenceError("coverage_policy must be an object")
    _bounded_int(
        policy.get("minimum_distinct_photo_viewpoints"),
        label="coverage_policy.minimum_distinct_photo_viewpoints",
        minimum=3,
    )
    _bounded_int(
        policy.get("minimum_distinct_video_viewpoints"),
        label="coverage_policy.minimum_distinct_video_viewpoints",
        minimum=1,
    )
    for key in (
        "layout_source_required",
        "scale_source_required",
        "unsupported_destination_portals_locked",
        "texture_import_requires_explicit_reuse_terms",
        "restricted_map_content_derivation_prohibited",
    ):
        if policy.get(key) is not True:
            raise WorldReferenceEvidenceError(f"coverage_policy.{key} must be true")

    areas = contract.get("areas")
    if not isinstance(areas, list) or not areas:
        raise WorldReferenceEvidenceError("areas must be a non-empty list")
    decisions: list[AreaEvidenceDecision] = []
    area_by_id: dict[str, Mapping[str, Any]] = {}
    for area in areas:
        if not isinstance(area, Mapping):
            raise WorldReferenceEvidenceError("Every area must be an object")
        decision = _area_decision(area, policy)
        if decision.area_id in area_by_id:
            raise WorldReferenceEvidenceError(f"Duplicate area_id {decision.area_id!r}")
        area_by_id[decision.area_id] = area
        decisions.append(decision)

    portals = contract.get("portals")
    if not isinstance(portals, list):
        raise WorldReferenceEvidenceError("portals must be a list")
    decision_by_id = {decision.area_id: decision for decision in decisions}
    portal_ids: set[str] = set()
    for index, portal in enumerate(portals):
        if not isinstance(portal, Mapping):
            raise WorldReferenceEvidenceError(f"portals[{index}] must be an object")
        portal_id = _nonempty_string(portal.get("portal_id"), label=f"portals[{index}].portal_id")
        if portal_id in portal_ids:
            raise WorldReferenceEvidenceError(f"Duplicate portal_id {portal_id!r}")
        portal_ids.add(portal_id)
        destination = _nonempty_string(
            portal.get("destination_area_id"), label=f"portals[{index}].destination_area_id"
        )
        if destination not in area_by_id:
            raise WorldReferenceEvidenceError(f"Portal {portal_id!r} has an unknown destination")
        decision = decision_by_id[destination]
        if portal.get("collision_solid") is not True or portal.get("opens") is not False:
            raise WorldReferenceEvidenceError(
                f"Portal {portal_id!r} cannot open from a reference-review contract"
            )
        if not decision.evidence_sufficient_for_draft:
            if portal.get("runtime_state") != LOCKED_PORTAL_STATE:
                raise WorldReferenceEvidenceError(
                    f"Portal {portal_id!r} must remain {LOCKED_PORTAL_STATE} until {destination!r} has evidence"
                )

    return tuple(decisions)
