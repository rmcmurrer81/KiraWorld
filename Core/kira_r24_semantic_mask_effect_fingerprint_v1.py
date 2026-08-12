"""R24 semantic-mask fingerprint with bounded runtime-effect comparison.

This revision builds on the sealed revision-02 schema projection without
changing it. Raw ``t`` drift is bounded as a coarse parameter-space guard, then
the exact inherited pure feature/relief formula is evaluated for each unique
aligned vertex. Semantic tags must remain exact and the adjusted pre-fade
offset must remain within a tight meter-space delta.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from Core.kira_r24_semantic_mask_fingerprint import semantic_mask_projection


EFFECT_SCHEMA = "kira.avatar.r24.semantic_mask_runtime_effect_fingerprint.v1"
RAW_T_MAXIMUM_ABSOLUTE_DELTA = 1.0e-05
ADJUSTED_OFFSET_MAXIMUM_ABSOLUTE_DELTA_M = 1.0e-07
MAXIMUM_OFFSET_M = 0.0030
RELIEF_CAP_M = 0.0030
CENTRAL_POSITIVE_MASK = "CENTRAL_POSITIVE_RELIEF"
RUNTIME_PARAMETER_FIELDS = frozenset({"u", "t"})
OPENING_SPECS = {
    "urethral_meatus": {
        "u": 0.0,
        "t": 0.39,
        "su": 0.055,
        "st": 0.045,
        "rim_height_m": 0.00034,
        "cap_depth_m": 0.00042,
    },
    "vaginal_introitus": {
        "u": 0.0,
        "t": 0.55,
        "su": 0.105,
        "st": 0.090,
        "rim_height_m": 0.00058,
        "cap_depth_m": 0.00110,
    },
    "anal_verge": {
        "u": 0.0,
        "t": 0.88,
        "su": 0.090,
        "st": 0.060,
        "rim_height_m": 0.00042,
        "cap_depth_m": 0.00072,
    },
}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _exact_mismatches(
    reference: Any, observed: Any, path: str = ""
) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    if type(reference) is not type(observed):
        return [
            {
                "path": path or "$",
                "reason": "type_mismatch",
                "reference_type": type(reference).__name__,
                "observed_type": type(observed).__name__,
            }
        ]
    if isinstance(reference, dict):
        reference_keys = set(reference)
        observed_keys = set(observed)
        if reference_keys != observed_keys:
            mismatches.append(
                {
                    "path": path or "$",
                    "reason": "key_set_mismatch",
                    "reference_keys": sorted(reference_keys),
                    "observed_keys": sorted(observed_keys),
                }
            )
        for key in sorted(reference_keys & observed_keys):
            child = f"{path}.{key}" if path else key
            mismatches.extend(_exact_mismatches(reference[key], observed[key], child))
        return mismatches
    if isinstance(reference, list):
        if len(reference) != len(observed):
            mismatches.append(
                {
                    "path": path or "$",
                    "reason": "length_mismatch",
                    "reference_length": len(reference),
                    "observed_length": len(observed),
                }
            )
        for index, (reference_item, observed_item) in enumerate(
            zip(reference, observed)
        ):
            mismatches.extend(
                _exact_mismatches(
                    reference_item, observed_item, f"{path}[{index}]"
                )
            )
        return mismatches
    if reference != observed:
        mismatches.append(
            {
                "path": path or "$",
                "reason": "value_mismatch",
                "reference": reference,
                "observed": observed,
            }
        )
    return mismatches


def _finite_float(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{path} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{path} must be finite")
    return result


def _finite_exact_number(value: Any, path: str) -> int | float:
    """Validate a number without erasing the exact JSON numeric type."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{path} must be an int or finite float")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path} must be finite")
    return value


def _exact_int(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{path} must be an int")
    return value


def _gaussian(value: float, center: float, width: float) -> float:
    return math.exp(-0.5 * ((float(value) - center) / max(width, 1.0e-12)) ** 2)


def _gaussian2(
    u: float,
    t: float,
    center_u: float,
    center_t: float,
    width_u: float,
    width_t: float,
) -> float:
    return _gaussian(u, center_u, width_u) * _gaussian(t, center_t, width_t)


def _elliptical_radius(
    u: float,
    t: float,
    center_u: float,
    center_t: float,
    scale_u: float,
    scale_t: float,
) -> float:
    return math.sqrt(
        ((u - center_u) / max(scale_u, 1.0e-12)) ** 2
        + ((t - center_t) / max(scale_t, 1.0e-12)) ** 2
    )


def _ring_value(radius: float, center: float = 1.0, width: float = 0.24) -> float:
    return math.exp(-0.5 * ((float(radius) - center) / width) ** 2)


def inherited_feature_offset_and_tags(u: float, t: float) -> tuple[float, tuple[str, ...]]:
    """Pure copy of the inherited R24 feature formula and tag thresholds."""

    u = _finite_float(u, "u")
    t = _finite_float(t, "t")
    tags: set[str] = set()
    value = 0.00062 * _gaussian2(u, t, 0.0, 0.48, 0.52, 0.34)

    mons = 0.00118 * _gaussian2(u, t, 0.0, 0.16, 0.48, 0.16)
    value += mons
    if mons > 0.00016:
        tags.add("mons")

    left_major = 0.00255 * _gaussian2(u, t, -0.31, 0.46, 0.15, 0.25)
    right_major = 0.00242 * _gaussian2(u, t, 0.32, 0.46, 0.15, 0.25)
    value += left_major + right_major
    if left_major > 0.00022:
        tags.add("labia_majora_left")
    if right_major > 0.00022:
        tags.add("labia_majora_right")

    left_sulcus = -0.00042 * _gaussian2(u, t, -0.205, 0.47, 0.055, 0.23)
    right_sulcus = -0.00042 * _gaussian2(u, t, 0.210, 0.47, 0.055, 0.23)
    value += left_sulcus + right_sulcus

    left_minor = 0.00134 * _gaussian2(u, t, -0.095, 0.47, 0.050, 0.20)
    right_minor = 0.00122 * _gaussian2(u, t, 0.108, 0.47, 0.052, 0.20)
    value += left_minor + right_minor
    if left_minor > 0.00013:
        tags.add("labia_minora_left")
    if right_minor > 0.00013:
        tags.add("labia_minora_right")

    vestibule = -0.00062 * _gaussian2(u, t, 0.0, 0.49, 0.125, 0.18)
    value += vestibule
    if vestibule < -0.00010:
        tags.add("vestibule")

    hood = 0.00110 * _gaussian2(u, t, -0.006, 0.285, 0.120, 0.065)
    glans = 0.00044 * _gaussian2(u, t, -0.010, 0.320, 0.045, 0.032)
    value += hood + glans
    if hood + glans > 0.00012:
        tags.add("clitoral_hood_glans")

    for name, spec in OPENING_SPECS.items():
        radius = _elliptical_radius(
            u,
            t,
            float(spec["u"]),
            float(spec["t"]),
            float(spec["su"]),
            float(spec["st"]),
        )
        rim = float(spec["rim_height_m"]) * _ring_value(radius)
        cap = -float(spec["cap_depth_m"]) * math.exp(
            -0.5 * (radius / 0.48) ** 2
        )
        value += rim + cap
        if 0.68 <= radius <= 1.34:
            tags.add(f"{name}__rim")
        if radius <= 0.56:
            tags.add(f"{name}__cap")

    fourchette = 0.00044 * _gaussian2(u, t, 0.0, 0.68, 0.135, 0.050)
    value += fourchette
    if fourchette > 0.00008:
        tags.add("posterior_fourchette")

    perineum = 0.00018 * _gaussian2(u, t, 0.0, 0.77, 0.25, 0.12)
    value += perineum
    if perineum > 0.000045:
        tags.add("external_perineum")

    bounded = max(-MAXIMUM_OFFSET_M, min(MAXIMUM_OFFSET_M, value))
    return float(bounded), tuple(sorted(tags))


def inherited_adjusted_feature_relief(
    u: float, t: float, central_positive_relief: bool
) -> dict[str, Any]:
    """Evaluate the inherited feature offset plus Attempt-06 positive relief."""

    if type(central_positive_relief) is not bool:
        raise TypeError("central_positive_relief must be a bool")
    original, tags = inherited_feature_offset_and_tags(u, t)
    delta = 0.0
    if central_positive_relief:
        left_major = 0.00255 * _gaussian2(u, t, -0.31, 0.46, 0.15, 0.25)
        right_major = 0.00242 * _gaussian2(u, t, 0.32, 0.46, 0.15, 0.25)
        left_minor = 0.00134 * _gaussian2(u, t, -0.095, 0.47, 0.050, 0.20)
        right_minor = 0.00122 * _gaussian2(u, t, 0.108, 0.47, 0.052, 0.20)
        hood = 0.00110 * _gaussian2(u, t, -0.006, 0.285, 0.120, 0.065)
        glans = 0.00044 * _gaussian2(u, t, -0.010, 0.320, 0.045, 0.032)
        delta = (
            0.12 * (left_major + right_major)
            + 0.10 * (left_minor + right_minor)
            + 0.15 * (hood + glans)
        )
    adjusted = max(-RELIEF_CAP_M, min(RELIEF_CAP_M, float(original) + delta))
    return {
        "semantic_tags": list(tags),
        "original_offset_m": float(original),
        "positive_increment_before_clamp_m": float(delta),
        "adjusted_offset_before_fade_m": float(adjusted),
        "clamped_to_3mm": abs(float(original) + delta) > RELIEF_CAP_M,
    }


def _require_sequence(value: Any, path: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError(f"{path} must be a sequence")
    return value


def _unique_vertex_states(masks: Mapping[str, Any]) -> dict[str, Any]:
    # The sealed revision-02 projection performs closed-schema validation first.
    semantic_mask_projection(masks)
    vertex_masks = masks["vertex_masks"]
    states: dict[tuple[int, int], dict[str, Any]] = {}
    duplicate_membership_identities: list[list[Any]] = []
    inconsistent_records: list[dict[str, Any]] = []
    seen_memberships: set[tuple[str, int, int]] = set()

    for mask_name in sorted(vertex_masks):
        records = _require_sequence(
            vertex_masks[mask_name]["records"],
            f"masks.vertex_masks.{mask_name}.records",
        )
        for index, record in enumerate(records):
            path = f"masks.vertex_masks.{mask_name}.records[{index}]"
            vertex_index = _exact_int(
                record["vertex_index_before_final_reindex"],
                f"{path}.vertex_index_before_final_reindex",
            )
            canonical_id = _exact_int(
                record["canonical_original_id"], f"{path}.canonical_original_id"
            )
            graph_ring = _exact_int(record["graph_ring"], f"{path}.graph_ring")
            u = _finite_exact_number(record["u"], f"{path}.u")
            t = _finite_exact_number(record["t"], f"{path}.t")
            identity = (vertex_index, canonical_id)
            membership_identity = (mask_name, vertex_index, canonical_id)
            if membership_identity in seen_memberships:
                duplicate_membership_identities.append(list(membership_identity))
            seen_memberships.add(membership_identity)

            state = states.get(identity)
            if state is None:
                states[identity] = {
                    "vertex_index_before_final_reindex": vertex_index,
                    "canonical_original_id": canonical_id,
                    "graph_ring": graph_ring,
                    "u": u,
                    "t": t,
                    "memberships": {mask_name},
                }
                continue
            conflicts = {}
            for field, observed in (("graph_ring", graph_ring), ("u", u), ("t", t)):
                if type(state[field]) is not type(observed) or state[field] != observed:
                    conflicts[field] = {"first": state[field], "later": observed}
            if conflicts:
                inconsistent_records.append(
                    {
                        "identity": list(identity),
                        "mask": mask_name,
                        "conflicts": conflicts,
                    }
                )
            state["memberships"].add(mask_name)

    normalized = {}
    for identity, state in states.items():
        normalized[identity] = {
            **state,
            "memberships": tuple(sorted(state["memberships"])),
            "central_positive_relief": CENTRAL_POSITIVE_MASK in state["memberships"],
        }
    return {
        "states": normalized,
        "duplicate_membership_identities": duplicate_membership_identities,
        "inconsistent_records": inconsistent_records,
    }


def _runtime_parameter_states(
    value: Mapping[tuple[int, int], Mapping[str, Any]] | None,
) -> dict[tuple[int, int], dict[str, float]]:
    """Validate optional in-memory coordinates keyed by exact vertex identity."""

    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("observed_runtime_parameters must be a mapping")
    states: dict[tuple[int, int], dict[str, float]] = {}
    for raw_identity, raw_parameters in value.items():
        if type(raw_identity) is not tuple or len(raw_identity) != 2:
            raise TypeError(
                "observed_runtime_parameters keys must be two-int tuples"
            )
        identity = (
            _exact_int(raw_identity[0], "observed_runtime_parameters key[0]"),
            _exact_int(raw_identity[1], "observed_runtime_parameters key[1]"),
        )
        if not isinstance(raw_parameters, Mapping):
            raise TypeError(
                f"observed_runtime_parameters[{identity!r}] must be a mapping"
            )
        observed_fields = set(raw_parameters)
        if observed_fields != RUNTIME_PARAMETER_FIELDS:
            raise ValueError(
                f"observed_runtime_parameters[{identity!r}] fields must be exact; "
                f"missing={sorted(RUNTIME_PARAMETER_FIELDS - observed_fields)}, "
                f"unknown={sorted(observed_fields - RUNTIME_PARAMETER_FIELDS)}"
            )
        states[identity] = {
            "u": _finite_float(
                raw_parameters["u"],
                f"observed_runtime_parameters[{identity!r}].u",
            ),
            "t": _finite_float(
                raw_parameters["t"],
                f"observed_runtime_parameters[{identity!r}].t",
            ),
        }
    return states


def compare_semantic_masks_with_runtime_effect(
    reference_masks: Mapping[str, Any],
    observed_masks: Mapping[str, Any],
    *,
    observed_runtime_parameters: (
        Mapping[tuple[int, int], Mapping[str, Any]] | None
    ) = None,
) -> dict[str, Any]:
    """Gate exact semantics, coarse raw ``t``, tags, and adjusted offset effect.

    Historical reference evidence contains twelve-decimal coordinates. A future
    worker may supply its in-memory observed coordinates. Those coordinates
    must cover the exact observed identities and round back to the serialized
    evidence; their full-precision ``u`` is then held constant across both
    evaluations so the measured effect isolates reference-versus-observed ``t``.
    """

    reference_projection = semantic_mask_projection(reference_masks)
    observed_projection = semantic_mask_projection(observed_masks)
    semantic_mismatches = _exact_mismatches(
        reference_projection, observed_projection
    )
    reference_unique = _unique_vertex_states(reference_masks)
    observed_unique = _unique_vertex_states(observed_masks)
    reference_states = reference_unique["states"]
    observed_states = observed_unique["states"]
    reference_identities = set(reference_states)
    observed_identities = set(observed_states)
    shared_identities = sorted(reference_identities & observed_identities)
    reference_only = sorted(reference_identities - observed_identities)
    observed_only = sorted(observed_identities - reference_identities)
    runtime_parameters = _runtime_parameter_states(observed_runtime_parameters)
    runtime_identities = set(runtime_parameters)
    runtime_parameters_supplied = observed_runtime_parameters is not None
    runtime_only = (
        sorted(runtime_identities - observed_identities)
        if runtime_parameters_supplied
        else []
    )
    runtime_missing = (
        sorted(observed_identities - runtime_identities)
        if runtime_parameters_supplied
        else []
    )

    records = []
    for identity in shared_identities:
        reference = reference_states[identity]
        observed = observed_states[identity]
        runtime = runtime_parameters.get(identity)
        effect_u = runtime["u"] if runtime is not None else observed["u"]
        observed_effect_t = runtime["t"] if runtime is not None else observed["t"]
        runtime_rounds_to_serialized = runtime is None or (
            round(runtime["u"], 12) == observed["u"]
            and round(runtime["t"], 12) == observed["t"]
        )
        reference_effect = inherited_adjusted_feature_relief(
            effect_u, reference["t"], reference["central_positive_relief"]
        )
        observed_effect = inherited_adjusted_feature_relief(
            effect_u, observed_effect_t, observed["central_positive_relief"]
        )
        raw_t_delta = float(observed_effect_t) - float(reference["t"])
        adjusted_delta = float(
            observed_effect["adjusted_offset_before_fade_m"]
            - reference_effect["adjusted_offset_before_fade_m"]
        )
        records.append(
            {
                "vertex_index_before_final_reindex": identity[0],
                "canonical_original_id": identity[1],
                "graph_ring_exact": observed["graph_ring"] == reference["graph_ring"],
                "u_exact": type(observed["u"]) is type(reference["u"])
                and observed["u"] == reference["u"],
                "memberships_exact": observed["memberships"]
                == reference["memberships"],
                "central_positive_relief_exact": observed[
                    "central_positive_relief"
                ]
                == reference["central_positive_relief"],
                "memberships": list(reference["memberships"]),
                "u": reference["u"],
                "effect_u": effect_u,
                "reference_t": reference["t"],
                "observed_t": observed["t"],
                "observed_effect_t": observed_effect_t,
                "runtime_parameters_supplied": runtime is not None,
                "runtime_parameters_round_to_serialized_evidence": (
                    runtime_rounds_to_serialized
                ),
                "raw_t_delta": raw_t_delta,
                "absolute_raw_t_delta": abs(raw_t_delta),
                "reference_effect": reference_effect,
                "observed_effect": observed_effect,
                "semantic_tags_exact": observed_effect["semantic_tags"]
                == reference_effect["semantic_tags"],
                "adjusted_offset_delta_m": adjusted_delta,
                "absolute_adjusted_offset_delta_m": abs(adjusted_delta),
            }
        )

    maximum_raw_t_delta = max(
        (record["absolute_raw_t_delta"] for record in records), default=0.0
    )
    maximum_adjusted_offset_delta = max(
        (record["absolute_adjusted_offset_delta_m"] for record in records),
        default=0.0,
    )
    checks = {
        "semantic_projection_exact": not semantic_mismatches,
        "unique_identity_sets_aligned_exactly": not reference_only
        and not observed_only,
        "reference_membership_identities_have_no_duplicates": not reference_unique[
            "duplicate_membership_identities"
        ],
        "observed_membership_identities_have_no_duplicates": not observed_unique[
            "duplicate_membership_identities"
        ],
        "reference_repeated_identity_records_consistent": not reference_unique[
            "inconsistent_records"
        ],
        "observed_repeated_identity_records_consistent": not observed_unique[
            "inconsistent_records"
        ],
        "graph_rings_u_memberships_and_central_membership_exact": all(
            record["graph_ring_exact"]
            and record["u_exact"]
            and record["memberships_exact"]
            and record["central_positive_relief_exact"]
            for record in records
        ),
        "runtime_parameters_cover_observed_identities_exactly": (
            not runtime_parameters_supplied
            or (not runtime_only and not runtime_missing)
        ),
        "runtime_parameters_round_to_serialized_evidence_exactly": all(
            record["runtime_parameters_round_to_serialized_evidence"]
            for record in records
        ),
        "maximum_absolute_raw_t_delta_within_1e_05": maximum_raw_t_delta
        <= RAW_T_MAXIMUM_ABSOLUTE_DELTA,
        "semantic_tags_exact": all(
            record["semantic_tags_exact"] for record in records
        ),
        "maximum_absolute_adjusted_offset_delta_within_1e_07_m": (
            maximum_adjusted_offset_delta
            <= ADJUSTED_OFFSET_MAXIMUM_ABSOLUTE_DELTA_M
        ),
        "full_mask_canonical_sha256_excluded": True,
    }
    return {
        "schema": EFFECT_SCHEMA,
        "reference_semantic_sha256": _sha256(reference_projection),
        "observed_semantic_sha256": _sha256(observed_projection),
        "raw_t_gate_maximum_absolute_delta": RAW_T_MAXIMUM_ABSOLUTE_DELTA,
        "adjusted_offset_gate_maximum_absolute_delta_m": (
            ADJUSTED_OFFSET_MAXIMUM_ABSOLUTE_DELTA_M
        ),
        "checks": checks,
        "passed": all(checks.values()),
        "semantic_mismatches": semantic_mismatches,
        "reference_only_identities": [list(identity) for identity in reference_only],
        "observed_only_identities": [list(identity) for identity in observed_only],
        "runtime_only_identities": [list(identity) for identity in runtime_only],
        "runtime_missing_identities": [list(identity) for identity in runtime_missing],
        "runtime_parameter_source": (
            "full_precision_observed_memory_with_12_decimal_bound_reference"
            if runtime_parameters_supplied
            else "serialized_mask_evidence"
        ),
        "reference_duplicate_membership_identities": reference_unique[
            "duplicate_membership_identities"
        ],
        "observed_duplicate_membership_identities": observed_unique[
            "duplicate_membership_identities"
        ],
        "reference_inconsistent_records": reference_unique["inconsistent_records"],
        "observed_inconsistent_records": observed_unique["inconsistent_records"],
        "unique_aligned_vertex_count": len(shared_identities),
        "changed_t_count": sum(record["raw_t_delta"] != 0.0 for record in records),
        "maximum_absolute_raw_t_delta": maximum_raw_t_delta,
        "semantic_tag_mismatch_count": sum(
            not record["semantic_tags_exact"] for record in records
        ),
        "maximum_absolute_adjusted_offset_delta_m": maximum_adjusted_offset_delta,
        "records": records,
    }
