"""Shared entity, anchor, affordance, and state contracts for garments.

This module deliberately contains no renderer or avatar implementation.  It is
the common vocabulary that lets World Builder and Avatar Builder exchange one
persistent garment instance without cloning it or treating a timed animation as
proof of a physical interaction.

Hashes in these contracts are exact compatibility boundaries.  A garment made
for one body or rig may be previewed elsewhere, but it cannot enter a wearable
state through this contract unless the asset, body, and rig SHA-256 values all
match.  Same-size sharing does not weaken that rule: the unchanged physical
garment needs a separately reviewed target-body/target-rig adapter evaluated by
``Core.wearable_component_contract`` before a new exact runtime definition can
be registered.  The adapter is not a cloned garment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
import re
from typing import Any, Iterable


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ContractError(ValueError):
    """Raised when a garment definition or state request is structurally invalid."""


class GarmentState(str, Enum):
    HANGING_ON_HOOK = "hanging_on_hook"
    GRASPED_FROM_HOOK = "grasped_from_hook"
    RIGHT_SLEEVE_THREADED = "right_sleeve_threaded"
    LEFT_SLEEVE_THREADED = "left_sleeve_threaded"
    BOTH_SLEEVES_THREADED = "both_sleeves_threaded"
    WORN_OPEN = "worn_open"
    WORN_TIED = "worn_tied"
    HELD_AFTER_REMOVAL = "held_after_removal"
    PLACED_ON_BED = "placed_on_bed"
    THROWN_IN_FLIGHT = "thrown_in_flight"
    SETTLED_ON_BED = "settled_on_bed"


class OwnerScope(str, Enum):
    WORLD = "world"
    AVATAR = "avatar"


class MaturityClass(str, Enum):
    ADULT = "adult"
    NON_ADULT_DOLL_SAFE = "non_adult_doll_safe"
    UNASSIGNED_BLOCKED = "unassigned_blocked"


WORLD_STATES = frozenset(
    {
        GarmentState.HANGING_ON_HOOK,
        GarmentState.PLACED_ON_BED,
        GarmentState.THROWN_IN_FLIGHT,
        GarmentState.SETTLED_ON_BED,
    }
)
AVATAR_STATES = frozenset(set(GarmentState) - set(WORLD_STATES))


def owner_scope_for_state(state: GarmentState) -> OwnerScope:
    return OwnerScope.WORLD if state in WORLD_STATES else OwnerScope.AVATAR


@dataclass(frozen=True, slots=True)
class AnchorSpec:
    """A named interaction anchor supplied by a garment, body, or world asset."""

    anchor_id: str
    role: str
    provider: str
    node_name: str
    local_position_m: tuple[float, float, float]
    interaction_radius_m: float

    def __post_init__(self) -> None:
        for label, value in {
            "anchor_id": self.anchor_id,
            "role": self.role,
            "provider": self.provider,
            "node_name": self.node_name,
        }.items():
            if not isinstance(value, str) or not value.strip():
                raise ContractError(f"{label} must be a non-empty string")
        if len(self.local_position_m) != 3 or not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            for value in self.local_position_m
        ):
            raise ContractError(f"anchor {self.anchor_id} needs a finite xyz local position")
        if (
            not isinstance(self.interaction_radius_m, (int, float))
            or not math.isfinite(self.interaction_radius_m)
            or self.interaction_radius_m <= 0
        ):
            raise ContractError(f"anchor {self.anchor_id} needs a positive interaction radius")


@dataclass(frozen=True, slots=True)
class AffordanceSpec:
    """One legal, evidence-gated garment action."""

    affordance_id: str
    verb: str
    from_states: tuple[GarmentState, ...]
    target_state: GarmentState
    evidence_gate: str
    required_anchor_roles: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.affordance_id.strip() or not self.verb.strip() or not self.evidence_gate.strip():
            raise ContractError("affordance id, verb, and evidence gate must be non-empty")
        if not self.from_states:
            raise ContractError(f"affordance {self.affordance_id} has no source state")
        if len(set(self.from_states)) != len(self.from_states):
            raise ContractError(f"affordance {self.affordance_id} repeats a source state")
        if not self.required_anchor_roles or any(not role.strip() for role in self.required_anchor_roles):
            raise ContractError(f"affordance {self.affordance_id} needs anchor roles")


@dataclass(frozen=True, slots=True)
class GarmentDefinition:
    """Immutable compatibility and interaction contract for one garment asset."""

    garment_type_id: str
    asset_sha256: str
    compatible_body_sha256: str
    compatible_rig_sha256: str
    anchors: tuple[AnchorSpec, ...]
    affordances: tuple[AffordanceSpec, ...]
    compatible_subject_id: str = "unassigned_subject"
    maturity_class: MaturityClass = MaturityClass.UNASSIGNED_BLOCKED

    def __post_init__(self) -> None:
        if not self.garment_type_id.strip():
            raise ContractError("garment_type_id must be non-empty")
        if not self.compatible_subject_id.strip():
            raise ContractError("compatible_subject_id must be non-empty")
        if not isinstance(self.maturity_class, MaturityClass):
            raise ContractError("maturity_class must be an explicit MaturityClass")
        for label, value in {
            "asset_sha256": self.asset_sha256,
            "compatible_body_sha256": self.compatible_body_sha256,
            "compatible_rig_sha256": self.compatible_rig_sha256,
        }.items():
            if not SHA256_RE.fullmatch(value):
                raise ContractError(f"{label} must be an exact lowercase SHA-256")

        anchor_ids = [anchor.anchor_id for anchor in self.anchors]
        if len(anchor_ids) != len(set(anchor_ids)):
            raise ContractError("anchor ids must be unique")
        roles = {anchor.role for anchor in self.anchors}
        affordance_ids = [affordance.affordance_id for affordance in self.affordances]
        if len(affordance_ids) != len(set(affordance_ids)):
            raise ContractError("affordance ids must be unique")
        for affordance in self.affordances:
            missing = set(affordance.required_anchor_roles) - roles
            if missing:
                raise ContractError(
                    f"affordance {affordance.affordance_id} lacks anchor roles: {sorted(missing)}"
                )

    def anchor_for_role(self, role: str) -> AnchorSpec:
        matches = [anchor for anchor in self.anchors if anchor.role == role]
        if len(matches) != 1:
            raise ContractError(f"expected exactly one anchor with role {role!r}")
        return matches[0]

    def affordance(self, affordance_id: str) -> AffordanceSpec:
        for affordance in self.affordances:
            if affordance.affordance_id == affordance_id:
                return affordance
        raise ContractError(f"unknown affordance: {affordance_id}")


@dataclass(slots=True)
class GarmentInstance:
    """The single authoritative placement of one persistent physical garment."""

    item_instance_id: str
    garment_type_id: str
    assigned_subject_id: str
    body_owner_subject_id: str
    maturity_class: MaturityClass
    state: GarmentState
    owner_scope: OwnerScope
    owner_id: str
    location_anchor_id: str
    revision: int = 0

    def __post_init__(self) -> None:
        if not self.item_instance_id.strip():
            raise ContractError("item_instance_id must be persistent and non-empty")
        if (
            not self.garment_type_id.strip()
            or not self.assigned_subject_id.strip()
            or not self.body_owner_subject_id.strip()
            or not self.owner_id.strip()
            or not self.location_anchor_id.strip()
        ):
            raise ContractError("garment type, subjects, owner, and location anchor must be non-empty")
        if not isinstance(self.maturity_class, MaturityClass):
            raise ContractError("instance maturity_class must be explicit")
        if self.owner_scope is not owner_scope_for_state(self.state):
            raise ContractError(
                f"state {self.state.value} requires {owner_scope_for_state(self.state).value} ownership"
            )
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 0:
            raise ContractError("revision must be a non-negative integer")

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_instance_id": self.item_instance_id,
            "garment_type_id": self.garment_type_id,
            "assigned_subject_id": self.assigned_subject_id,
            "body_owner_subject_id": self.body_owner_subject_id,
            "maturity_class": self.maturity_class.value,
            "state": self.state.value,
            "owner_scope": self.owner_scope.value,
            "owner_id": self.owner_id,
            "location_anchor_id": self.location_anchor_id,
            "revision": self.revision,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "GarmentInstance":
        return cls(
            item_instance_id=str(value.get("item_instance_id", "")),
            garment_type_id=str(value.get("garment_type_id", "")),
            assigned_subject_id=str(value.get("assigned_subject_id", "")),
            body_owner_subject_id=str(value.get("body_owner_subject_id", "")),
            maturity_class=MaturityClass(value.get("maturity_class")),
            state=GarmentState(value.get("state")),
            owner_scope=OwnerScope(value.get("owner_scope")),
            owner_id=str(value.get("owner_id", "")),
            location_anchor_id=str(value.get("location_anchor_id", "")),
            revision=value.get("revision", -1),
        )


def _anchor(
    anchor_id: str,
    role: str,
    provider: str,
    node_name: str,
    xyz: tuple[float, float, float],
    radius: float = 0.08,
) -> AnchorSpec:
    return AnchorSpec(anchor_id, role, provider, node_name, xyz, radius)


def _affordance(
    affordance_id: str,
    verb: str,
    sources: Iterable[GarmentState],
    target: GarmentState,
    gate: str,
    roles: Iterable[str],
) -> AffordanceSpec:
    return AffordanceSpec(
        affordance_id=affordance_id,
        verb=verb,
        from_states=tuple(sources),
        target_state=target,
        evidence_gate=gate,
        required_anchor_roles=tuple(roles),
    )


def build_robe_definition(
    *,
    garment_type_id: str,
    asset_sha256: str,
    compatible_body_sha256: str,
    compatible_rig_sha256: str,
    compatible_subject_id: str = "unassigned_subject",
    maturity_class: MaturityClass = MaturityClass.UNASSIGNED_BLOCKED,
) -> GarmentDefinition:
    """Build the reusable robe vertical-slice contract.

    Positions are local anchor declarations, not claims about a finished mesh.
    A real asset importer must map these named nodes to the GLB and verify them
    before this definition is approved for runtime use.
    """

    anchors = (
        _anchor("robe_hook_loop", "garment_hook_loop", "garment", "hook_loop", (0.0, 1.02, -0.04)),
        _anchor("world_wall_hook", "world_wall_hook", "world", "bathroom_wall_hook", (0.0, 1.55, 0.0)),
        _anchor("robe_right_sleeve_portal", "right_sleeve_portal", "garment", "right_sleeve_opening", (-0.33, 0.67, 0.0), 0.12),
        _anchor("robe_left_sleeve_portal", "left_sleeve_portal", "garment", "left_sleeve_opening", (0.33, 0.67, 0.0), 0.12),
        _anchor("body_right_wrist", "right_wrist_path", "body", "wrist.R", (-0.47, 0.72, 0.0), 0.07),
        _anchor("body_right_forearm", "right_forearm_path", "body", "forearm.R", (-0.39, 0.79, 0.0), 0.08),
        _anchor("body_right_elbow", "right_elbow_path", "body", "elbow.R", (-0.31, 0.88, 0.0), 0.08),
        _anchor("body_left_wrist", "left_wrist_path", "body", "wrist.L", (0.47, 0.72, 0.0), 0.07),
        _anchor("body_left_forearm", "left_forearm_path", "body", "forearm.L", (0.39, 0.79, 0.0), 0.08),
        _anchor("body_left_elbow", "left_elbow_path", "body", "elbow.L", (0.31, 0.88, 0.0), 0.08),
        _anchor("robe_shoulders", "garment_shoulders", "garment", "shoulder_yoke", (0.0, 0.88, 0.0), 0.11),
        _anchor("body_shoulders", "body_shoulders", "body", "upper_chest", (0.0, 1.35, 0.0), 0.11),
        _anchor("robe_belt_left", "belt_left_endpoint", "garment", "belt_left_end", (0.23, 0.24, 0.08), 0.06),
        _anchor("robe_belt_right", "belt_right_endpoint", "garment", "belt_right_end", (-0.23, 0.24, 0.08), 0.06),
        _anchor("robe_belt_knot", "belt_knot", "garment", "belt_knot", (0.0, 0.28, 0.13), 0.07),
        _anchor("body_waist", "body_waist", "body", "pelvis", (0.0, 0.95, 0.0), 0.12),
        _anchor("world_bed_surface", "bed_surface", "world", "bed_robe_surface", (0.0, 0.58, 0.0), 0.2),
        _anchor("avatar_hand_grip", "hand_grip", "body", "hand.R", (-0.52, 0.75, 0.0), 0.08),
    )

    affordances = (
        _affordance(
            "take_from_hook", "take robe from hook", (GarmentState.HANGING_ON_HOOK,),
            GarmentState.GRASPED_FROM_HOOK, "hook_detach",
            ("garment_hook_loop", "world_wall_hook", "hand_grip"),
        ),
        _affordance(
            "thread_right_first", "put right arm through sleeve", (GarmentState.GRASPED_FROM_HOOK,),
            GarmentState.RIGHT_SLEEVE_THREADED, "right_sleeve_crossing",
            ("right_sleeve_portal", "right_wrist_path", "right_forearm_path", "right_elbow_path"),
        ),
        _affordance(
            "thread_left_first", "put left arm through sleeve", (GarmentState.GRASPED_FROM_HOOK,),
            GarmentState.LEFT_SLEEVE_THREADED, "left_sleeve_crossing",
            ("left_sleeve_portal", "left_wrist_path", "left_forearm_path", "left_elbow_path"),
        ),
        _affordance(
            "thread_left_second", "put left arm through sleeve", (GarmentState.RIGHT_SLEEVE_THREADED,),
            GarmentState.BOTH_SLEEVES_THREADED, "left_sleeve_crossing",
            ("left_sleeve_portal", "left_wrist_path", "left_forearm_path", "left_elbow_path"),
        ),
        _affordance(
            "thread_right_second", "put right arm through sleeve", (GarmentState.LEFT_SLEEVE_THREADED,),
            GarmentState.BOTH_SLEEVES_THREADED, "right_sleeve_crossing",
            ("right_sleeve_portal", "right_wrist_path", "right_forearm_path", "right_elbow_path"),
        ),
        _affordance(
            "unthread_right_only", "withdraw right arm from sleeve", (GarmentState.RIGHT_SLEEVE_THREADED,),
            GarmentState.GRASPED_FROM_HOOK, "right_sleeve_exit",
            ("right_sleeve_portal", "right_wrist_path", "right_forearm_path", "right_elbow_path", "hand_grip"),
        ),
        _affordance(
            "unthread_left_only", "withdraw left arm from sleeve", (GarmentState.LEFT_SLEEVE_THREADED,),
            GarmentState.GRASPED_FROM_HOOK, "left_sleeve_exit",
            ("left_sleeve_portal", "left_wrist_path", "left_forearm_path", "left_elbow_path", "hand_grip"),
        ),
        _affordance(
            "unthread_left_from_both", "withdraw left arm and keep right sleeve", (GarmentState.BOTH_SLEEVES_THREADED,),
            GarmentState.RIGHT_SLEEVE_THREADED, "left_sleeve_exit",
            ("left_sleeve_portal", "left_wrist_path", "left_forearm_path", "left_elbow_path", "hand_grip"),
        ),
        _affordance(
            "unthread_right_from_both", "withdraw right arm and keep left sleeve", (GarmentState.BOTH_SLEEVES_THREADED,),
            GarmentState.LEFT_SLEEVE_THREADED, "right_sleeve_exit",
            ("right_sleeve_portal", "right_wrist_path", "right_forearm_path", "right_elbow_path", "hand_grip"),
        ),
        _affordance(
            "settle_shoulders", "settle robe on shoulders", (GarmentState.BOTH_SLEEVES_THREADED,),
            GarmentState.WORN_OPEN, "shoulder_settle",
            ("garment_shoulders", "body_shoulders"),
        ),
        _affordance(
            "tie_belt", "tie robe belt", (GarmentState.WORN_OPEN,),
            GarmentState.WORN_TIED, "belt_tie",
            ("belt_left_endpoint", "belt_right_endpoint", "belt_knot", "body_waist"),
        ),
        _affordance(
            "untie_belt", "untie robe belt", (GarmentState.WORN_TIED,),
            GarmentState.WORN_OPEN, "belt_untie",
            ("belt_left_endpoint", "belt_right_endpoint", "belt_knot"),
        ),
        _affordance(
            "move_worn_open", "move while wearing open robe", (GarmentState.WORN_OPEN,),
            GarmentState.WORN_OPEN, "worn_movement",
            ("garment_shoulders", "body_shoulders"),
        ),
        _affordance(
            "move_worn_tied", "move while wearing tied robe", (GarmentState.WORN_TIED,),
            GarmentState.WORN_TIED, "worn_movement",
            ("garment_shoulders", "body_shoulders", "belt_left_endpoint", "belt_right_endpoint"),
        ),
        _affordance(
            "remove_robe", "remove robe from arms and shoulders", (GarmentState.WORN_OPEN,),
            GarmentState.HELD_AFTER_REMOVAL, "removal",
            ("left_sleeve_portal", "right_sleeve_portal", "body_shoulders", "hand_grip"),
        ),
        _affordance(
            "rehang", "put robe back on hook", (GarmentState.HELD_AFTER_REMOVAL,),
            GarmentState.HANGING_ON_HOOK, "rehang",
            ("garment_hook_loop", "world_wall_hook", "hand_grip"),
        ),
        _affordance(
            "rehang_after_partial_stop", "return unworn robe to hook", (GarmentState.GRASPED_FROM_HOOK,),
            GarmentState.HANGING_ON_HOOK, "rehang",
            ("garment_hook_loop", "world_wall_hook", "hand_grip"),
        ),
        _affordance(
            "place_on_bed", "place robe on bed", (GarmentState.HELD_AFTER_REMOVAL,),
            GarmentState.PLACED_ON_BED, "bed_placement",
            ("bed_surface", "hand_grip"),
        ),
        _affordance(
            "throw_to_bed", "throw robe toward bed", (GarmentState.HELD_AFTER_REMOVAL,),
            GarmentState.THROWN_IN_FLIGHT, "throw_release",
            ("bed_surface", "hand_grip"),
        ),
        _affordance(
            "settle_after_throw", "settle thrown robe on bed", (GarmentState.THROWN_IN_FLIGHT,),
            GarmentState.SETTLED_ON_BED, "throw_settle",
            ("bed_surface",),
        ),
        _affordance(
            "pick_up_placed_robe", "pick robe up from bed", (GarmentState.PLACED_ON_BED, GarmentState.SETTLED_ON_BED),
            GarmentState.HELD_AFTER_REMOVAL, "bed_pickup",
            ("bed_surface", "hand_grip"),
        ),
    )
    return GarmentDefinition(
        garment_type_id=garment_type_id,
        asset_sha256=asset_sha256,
        compatible_body_sha256=compatible_body_sha256,
        compatible_rig_sha256=compatible_rig_sha256,
        anchors=anchors,
        affordances=affordances,
        compatible_subject_id=compatible_subject_id,
        maturity_class=maturity_class,
    )
