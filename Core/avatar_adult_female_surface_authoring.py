"""Generic contract for continuous adult-female external-surface authoring.

This module contains no Blender dependency and no identity data.  It defines
the local coordinate frame, deterministic relief fields, and the exact
relationship/landmark contract consumed by the Blender adapter.  It is an
unpromoted, inactive authoring method: it does not build, render, export,
select, or activate an avatar, and it does not replace independent review.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


METHOD_ID = "generic_continuous_adult_female_external_surface_v1"
POLICY_PATH = Path(
    "Avatar/avatar_builder/policies/adult_foundation_qualification_v1.json"
)
LANDMARK_GROUP_PREFIX = "AFES_LANDMARK__"
OPENING_REPRESENTATION = "recessed_capped_continuous_primary_surface"

# This tuple deliberately mirrors the versioned qualification policy.  The
# contract loader rejects drift in either direction before geometry can change.
REQUIRED_RELATIONSHIPS = (
    "mons_pubis",
    "paired_labia_majora",
    "paired_labia_minora",
    "clitoral_hood",
    "clitoris",
    "vestibule",
    "urethral_opening_anterior_to_vaginal_opening",
    "vaginal_opening",
    "posterior_commissure_fourchette",
    "perineal_transition_to_anus_and_pelvic_floor",
)

LANDMARK_GROUP_CODES: Mapping[str, str] = {
    "mons_pubis": "mons_pubis",
    "paired_labia_majora": "labia_majora",
    "paired_labia_minora": "labia_minora",
    "clitoral_hood": "clitoral_hood",
    "clitoris": "clitoris",
    "vestibule": "vestibule",
    "urethral_opening_anterior_to_vaginal_opening": "urethral_opening",
    "vaginal_opening": "vaginal_opening",
    "posterior_commissure_fourchette": "fourchette",
    "perineal_transition_to_anus_and_pelvic_floor": "perineal_path",
}

LANDMARK_SUBLABEL_CODES: Mapping[str, str] = {
    "left": "left",
    "right": "right",
    "perineal_transition": "transition",
    "posterior_anal_recess": "anal_recess",
}


@dataclass(frozen=True)
class SurfaceFrame:
    """Object-local frame for one existing ventral/perineal skin surface.

    ``longitudinal_axis`` points from the posterior anal/pelvic-floor end
    toward the anterior/superior mons end. ``outward_axis`` points out of the
    body. ``origin`` is centered on the vestibular portion of the skin.
    """

    origin: tuple[float, float, float]
    lateral_axis: tuple[float, float, float]
    longitudinal_axis: tuple[float, float, float]
    outward_axis: tuple[float, float, float]
    half_width_m: float
    half_length_m: float
    max_surface_offset_m: float


@dataclass(frozen=True)
class AuthoringParameters:
    subdivision_cuts: int = 2
    relief_scale_m: float = 0.0032
    boundary_taper_power: int = 3
    minimum_face_normal_alignment: float = 0.20
    minimum_landmark_vertices: int = 3
    landmark_influence_threshold: float = 0.32
    maximum_skin_influences: int = 4
    degeneracy_area_m2: float = 1.0e-12


# Each component is authored as a displacement of the existing primary skin,
# never as imported, Booleaned, or floating anatomy geometry.  Coordinates are
# normalized by the supplied frame. Positive longitudinal coordinate is
# anterior/superior; therefore the urethral recess is deterministically
# anterior to the vaginal recess.
FEATURE_COMPONENTS: Mapping[str, tuple[Mapping[str, float | str], ...]] = {
    "mons_pubis": (
        {"name": "mons", "u": 0.0, "v": 0.72, "su": 0.58, "sv": 0.25, "amplitude": 0.42},
    ),
    "paired_labia_majora": (
        {"name": "left", "u": 0.34, "v": 0.02, "su": 0.17, "sv": 0.53, "amplitude": 0.72},
        {"name": "right", "u": -0.34, "v": 0.02, "su": 0.17, "sv": 0.53, "amplitude": 0.72},
    ),
    "paired_labia_minora": (
        {"name": "left", "u": 0.14, "v": 0.03, "su": 0.075, "sv": 0.34, "amplitude": 0.38},
        {"name": "right", "u": -0.14, "v": 0.03, "su": 0.075, "sv": 0.34, "amplitude": 0.38},
    ),
    "clitoral_hood": (
        {"name": "hood", "u": 0.0, "v": 0.36, "su": 0.23, "sv": 0.11, "amplitude": 0.34},
    ),
    "clitoris": (
        {"name": "clitoris", "u": 0.0, "v": 0.285, "su": 0.075, "sv": 0.065, "amplitude": 0.24},
    ),
    "vestibule": (
        {"name": "vestibule", "u": 0.0, "v": 0.015, "su": 0.19, "sv": 0.29, "amplitude": -0.20},
    ),
    "urethral_opening_anterior_to_vaginal_opening": (
        {"name": "urethral_recess", "u": 0.0, "v": 0.14, "su": 0.050, "sv": 0.050, "amplitude": -0.34},
    ),
    "vaginal_opening": (
        {"name": "vaginal_recess", "u": 0.0, "v": -0.15, "su": 0.13, "sv": 0.18, "amplitude": -0.58},
    ),
    "posterior_commissure_fourchette": (
        {"name": "fourchette", "u": 0.0, "v": -0.40, "su": 0.23, "sv": 0.075, "amplitude": 0.28},
    ),
    "perineal_transition_to_anus_and_pelvic_floor": (
        {"name": "perineal_transition", "u": 0.0, "v": -0.53, "su": 0.42, "sv": 0.18, "amplitude": 0.10},
        {"name": "posterior_anal_recess", "u": 0.0, "v": -0.68, "su": 0.22, "sv": 0.105, "amplitude": -0.55},
    ),
}


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be a finite number")
    return result


def _vector(value: Any, label: str) -> tuple[float, float, float]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or len(value) != 3
    ):
        raise ValueError(f"{label} must contain exactly three numbers")
    return tuple(_number(component, label) for component in value)  # type: ignore[return-value]


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(float(a) * float(b) for a, b in zip(left, right))


def _length(value: Sequence[float]) -> float:
    return math.sqrt(_dot(value, value))


def _normalized(value: Sequence[float], label: str) -> tuple[float, float, float]:
    magnitude = _length(value)
    if magnitude <= 1.0e-9:
        raise ValueError(f"{label} must be non-zero")
    return tuple(float(component) / magnitude for component in value)  # type: ignore[return-value]


def load_required_relationships(project_root: Path) -> tuple[str, ...]:
    root = Path(project_root).resolve(strict=True)
    policy = (root / POLICY_PATH).resolve(strict=True)
    try:
        policy.relative_to(root)
    except ValueError as exc:
        raise ValueError("adult-foundation policy escaped the project root") from exc
    payload = json.loads(policy.read_text(encoding="utf-8-sig"))
    relationships = payload.get("required_adult_female_relationships")
    if not isinstance(relationships, list) or not all(
        isinstance(value, str) and value.strip() for value in relationships
    ):
        raise ValueError("adult-foundation relationship policy is invalid")
    normalized = tuple(value.strip() for value in relationships)
    if normalized != REQUIRED_RELATIONSHIPS:
        raise ValueError("authoring relationship contract drifted from policy")
    if tuple(FEATURE_COMPONENTS) != normalized:
        raise ValueError("feature implementation does not exactly cover policy")
    return normalized


def frame_from_mapping(value: Mapping[str, Any]) -> SurfaceFrame:
    if not isinstance(value, Mapping):
        raise ValueError("surface frame must be an object")
    if str(value.get("coordinate_space") or "").strip() != "object_local":
        raise ValueError("surface frame coordinate_space must be object_local")
    origin = _vector(value.get("origin"), "origin")
    lateral = _normalized(_vector(value.get("lateral_axis"), "lateral_axis"), "lateral_axis")
    longitudinal = _normalized(
        _vector(value.get("longitudinal_axis"), "longitudinal_axis"),
        "longitudinal_axis",
    )
    outward = _normalized(_vector(value.get("outward_axis"), "outward_axis"), "outward_axis")
    for name, first, second in (
        ("lateral/longitudinal", lateral, longitudinal),
        ("lateral/outward", lateral, outward),
        ("longitudinal/outward", longitudinal, outward),
    ):
        if abs(_dot(first, second)) > 1.0e-4:
            raise ValueError(f"surface frame axes are not orthogonal: {name}")
    half_width = _number(value.get("half_width_m"), "half_width_m")
    half_length = _number(value.get("half_length_m"), "half_length_m")
    max_offset = _number(value.get("max_surface_offset_m"), "max_surface_offset_m")
    if not 0.015 <= half_width <= 0.20:
        raise ValueError("half_width_m must remain within [0.015, 0.20]")
    if not 0.04 <= half_length <= 0.35:
        raise ValueError("half_length_m must remain within [0.04, 0.35]")
    if not 0.002 <= max_offset <= 0.12:
        raise ValueError("max_surface_offset_m must remain within [0.002, 0.12]")
    return SurfaceFrame(
        origin=origin,
        lateral_axis=lateral,
        longitudinal_axis=longitudinal,
        outward_axis=outward,
        half_width_m=half_width,
        half_length_m=half_length,
        max_surface_offset_m=max_offset,
    )


def parameters_from_mapping(value: Mapping[str, Any] | None) -> AuthoringParameters:
    raw = dict(value or {})
    allowed = set(AuthoringParameters.__dataclass_fields__)
    unexpected = sorted(set(raw).difference(allowed))
    if unexpected:
        raise ValueError(f"unknown authoring parameter(s): {', '.join(unexpected)}")
    defaults = AuthoringParameters()
    integers = {
        "subdivision_cuts",
        "boundary_taper_power",
        "minimum_landmark_vertices",
        "maximum_skin_influences",
    }
    values: dict[str, int | float] = {}
    for name in allowed:
        supplied = raw.get(name, getattr(defaults, name))
        if name in integers:
            if isinstance(supplied, bool) or not isinstance(supplied, int):
                raise ValueError(f"{name} must be an integer")
            values[name] = supplied
        else:
            values[name] = _number(supplied, name)
    result = AuthoringParameters(**values)  # type: ignore[arg-type]
    if not 1 <= result.subdivision_cuts <= 4:
        raise ValueError("subdivision_cuts must remain within [1, 4]")
    if not 0.0005 <= result.relief_scale_m <= 0.008:
        raise ValueError("relief_scale_m must remain within [0.0005, 0.008]")
    if not 2 <= result.boundary_taper_power <= 6:
        raise ValueError("boundary_taper_power must remain within [2, 6]")
    if not 0.05 <= result.minimum_face_normal_alignment <= 0.95:
        raise ValueError("minimum_face_normal_alignment must remain within [0.05, 0.95]")
    if not 2 <= result.minimum_landmark_vertices <= 32:
        raise ValueError("minimum_landmark_vertices must remain within [2, 32]")
    if not 0.05 <= result.landmark_influence_threshold <= 0.80:
        raise ValueError("landmark_influence_threshold must remain within [0.05, 0.80]")
    if not 1 <= result.maximum_skin_influences <= 8:
        raise ValueError("maximum_skin_influences must remain within [1, 8]")
    if not 1.0e-16 <= result.degeneracy_area_m2 <= 1.0e-8:
        raise ValueError("degeneracy_area_m2 outside bounded range")
    return result


def gaussian(u: float, v: float, component: Mapping[str, float | str]) -> float:
    du = (float(u) - float(component["u"])) / float(component["su"])
    dv = (float(v) - float(component["v"])) / float(component["sv"])
    return math.exp(-0.5 * (du * du + dv * dv))


def boundary_taper(u: float, v: float, power: int) -> float:
    radius_squared = float(u) * float(u) + float(v) * float(v)
    if radius_squared >= 1.0:
        return 0.0
    return max(0.0, 1.0 - radius_squared) ** int(power)


def feature_influences(u: float, v: float) -> dict[str, float]:
    return {
        relationship: max(
            gaussian(u, v, component) for component in components
        )
        for relationship, components in FEATURE_COMPONENTS.items()
    }


def landmark_memberships(
    u: float,
    v: float,
    *,
    threshold: float,
) -> tuple[str, ...]:
    memberships: list[str] = []
    for relationship, components in FEATURE_COMPONENTS.items():
        component_values = [gaussian(u, v, component) for component in components]
        if max(component_values) >= threshold:
            memberships.append(relationship)
        if relationship in {"paired_labia_majora", "paired_labia_minora"}:
            for component, influence in zip(components, component_values):
                if influence >= threshold:
                    memberships.append(f"{relationship}__{component['name']}")
        if relationship == "perineal_transition_to_anus_and_pelvic_floor":
            for component, influence in zip(components, component_values):
                if influence >= threshold:
                    memberships.append(
                        f"{relationship}__{component['name']}"
                    )
    return tuple(memberships)


def landmark_group_name(membership: str) -> str:
    relationship, separator, sublabel = str(membership).partition("__")
    code = LANDMARK_GROUP_CODES.get(relationship)
    if code is None:
        raise ValueError(f"unknown landmark relationship: {relationship}")
    sublabel_code = LANDMARK_SUBLABEL_CODES.get(sublabel) if separator else None
    if separator and sublabel_code is None:
        raise ValueError(f"unknown landmark sublabel: {sublabel}")
    suffix = f"__{sublabel_code}" if sublabel_code else ""
    name = f"{LANDMARK_GROUP_PREFIX}{code}{suffix}"
    if len(name.encode("utf-8")) > 63:
        raise ValueError(f"landmark group name exceeds Blender limit: {name}")
    return name


def surface_displacement(
    u: float,
    v: float,
    *,
    relief_scale_m: float,
    taper_power: int,
) -> float:
    taper = boundary_taper(u, v, taper_power)
    if taper <= 0.0:
        return 0.0
    value = 0.0
    for components in FEATURE_COMPONENTS.values():
        for component in components:
            value += float(component["amplitude"]) * gaussian(u, v, component)
    # Keep the field bounded even when broad features overlap.  This is an
    # authoring displacement, not evidence that the resulting anatomy passed.
    value = max(-1.0, min(1.0, value))
    return float(relief_scale_m) * taper * value


def build_authoring_contract(
    project_root: Path,
    frame: SurfaceFrame,
    parameters: AuthoringParameters,
) -> dict[str, Any]:
    relationships = load_required_relationships(project_root)
    urethral_v = float(
        FEATURE_COMPONENTS[
            "urethral_opening_anterior_to_vaginal_opening"
        ][0]["v"]
    )
    vaginal_v = float(FEATURE_COMPONENTS["vaginal_opening"][0]["v"])
    anal_v = float(
        FEATURE_COMPONENTS[
            "perineal_transition_to_anus_and_pelvic_floor"
        ][1]["v"]
    )
    if not urethral_v > vaginal_v > anal_v:
        raise ValueError("required anterior/posterior relationship is invalid")
    return {
        "schema_version": 1,
        "method_id": METHOD_ID,
        "status": "UNPROMOTED_INACTIVE_AUTHORING_METHOD",
        "body_class": "adult_female",
        "coordinate_convention": (
            "object_local; longitudinal positive toward mons/anterior; "
            "outward positive outside primary skin"
        ),
        "frame": asdict(frame),
        "parameters": asdict(parameters),
        "relationships": list(relationships),
        "relationship_geometry_mode": {
            relationship: "continuous_primary_surface_relief"
            for relationship in relationships
        },
        "opening_representation": OPENING_REPRESENTATION,
        "source_anatomy_geometry_copy_allowed": False,
        "wrong_sex_helper_allowed": False,
        "separate_anatomy_mesh_allowed": False,
        "boolean_anatomy_union_allowed": False,
        "painted_only_relationship_allowed": False,
        "source_primary_surface_required": True,
        "source_component_count_required": 1,
        "source_boundary_edges_required": 0,
        "source_nonmanifold_edges_required": 0,
        "result_component_count_required": 1,
        "result_boundary_edges_required": 0,
        "result_nonmanifold_edges_required": 0,
        "authored_region_nonadjacent_self_intersection_pairs_required": 0,
        "new_global_nonadjacent_self_intersection_pairs_allowed": False,
        "qualification_global_nonadjacent_self_intersection_pairs_required": 0,
        "skin_weights": {
            "preserve_existing_vertices": True,
            "interpolate_new_vertices": True,
            "normalize_new_vertices": True,
            "maximum_influences": parameters.maximum_skin_influences,
        },
        "landmark_group_prefix": LANDMARK_GROUP_PREFIX,
        "landmark_groups": {
            relationship: landmark_group_name(relationship)
            for relationship in relationships
        },
        "independent_topology_review_required": True,
        "independent_relationship_review_required": True,
        "qualified_for_adult_foundation": False,
        "runtime_activation_allowed": False,
        "render_performed": False,
        "export_performed": False,
    }


__all__ = [
    "AuthoringParameters",
    "FEATURE_COMPONENTS",
    "LANDMARK_GROUP_PREFIX",
    "LANDMARK_GROUP_CODES",
    "LANDMARK_SUBLABEL_CODES",
    "METHOD_ID",
    "OPENING_REPRESENTATION",
    "POLICY_PATH",
    "REQUIRED_RELATIONSHIPS",
    "SurfaceFrame",
    "boundary_taper",
    "build_authoring_contract",
    "feature_influences",
    "frame_from_mapping",
    "gaussian",
    "landmark_memberships",
    "landmark_group_name",
    "load_required_relationships",
    "parameters_from_mapping",
    "surface_displacement",
]
