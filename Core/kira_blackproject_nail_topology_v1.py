"""Pure Kira/BlackProject nail identity and append-only reuse contracts.

The BlackProject skeleton does not use the MakeHuman ``fingerN-3.L`` names
used by the generic Avatar Builder nail author.  This module supplies the
exact twenty Kira nail identities, maps every recognized BlackProject digit
bone to one anatomical digit family, and validates cached top-surface
components without importing Blender.

No function in this module mutates a body, rig, candidate, or cache file.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "kira.blackproject_nail_topology.v1"
CACHE_SCHEMA = "kira.r21.passing_nail_components.v1"
METHOD_ID = "kira_blackproject_weight_constrained_connected_region_v1"
PROJECTION_GRID_SIZE = 9
EXPECTED_NAIL_COUNT = 20
MINIMUM_EXPECTED_FAMILY_WEIGHT = 0.99
MAXIMUM_FOREIGN_DIGIT_FAMILY_WEIGHT = 0.01
MAXIMUM_WRONG_SIDE_DIGIT_WEIGHT = 0.01
MINIMUM_MEDIAN_EXACT_TERMINAL_BONE_WEIGHT = 0.90


class KiraBlackProjectNailContractError(ValueError):
    pass


_FINGERS = (
    (1, "Thumb", "lThumb3_049", "rThumb3_074"),
    (2, "Index", "lIndex3_053", "rIndex3_078"),
    (3, "Mid", "lMid3_057", "rMid3_082"),
    (4, "Ring", "lRing3_061", "rRing3_01"),
    (5, "Pinky", "lPinky3_065", "rPinky3_088"),
)
_TOES = (
    (1, "BigToe", "lBigToe_2_020", "rBigToe_2_036"),
    (2, "SmallToe1", "lSmallToe1_2_018", "rSmallToe1_2_034"),
    (3, "SmallToe2", "lSmallToe2_2_016", "rSmallToe2_2_032"),
    (4, "SmallToe3", "lSmallToe3_2_014", "rSmallToe3_2_030"),
    (5, "SmallToe4", "lSmallToe4_2_012", "rSmallToe4_2_028"),
)


def expected_nail_inventory() -> tuple[dict[str, Any], ...]:
    """Return the exact bilateral Kira inventory in deterministic order."""

    rows: list[dict[str, Any]] = []
    for side, index in (("L", 2), ("R", 3)):
        for digit, _label, left_bone, right_bone in _FINGERS:
            bone = (left_bone, right_bone)[index - 2]
            rows.append(
                {
                    "nail_id": f"fingernail_{digit}_{side}",
                    "source_object": (
                        f"R19_BlackProject_fingernail_{digit}_{side}_source_native"
                    ),
                    "kind": "fingernail",
                    "side": side,
                    "digit": digit,
                    "bone": bone,
                    "family": f"finger{digit}.{side}",
                    "reference_length_scale": 0.68 if digit == 1 else 0.70,
                    "reference_width_scale": 0.88,
                }
            )
        for digit, _label, left_bone, right_bone in _TOES:
            bone = (left_bone, right_bone)[index - 2]
            rows.append(
                {
                    "nail_id": f"toenail_{digit}_{side}",
                    "source_object": (
                        f"R19_BlackProject_toenail_{digit}_{side}_source_native"
                    ),
                    "kind": "toenail",
                    "side": side,
                    "digit": digit,
                    "bone": bone,
                    "family": f"toe{digit}.{side}",
                    "reference_length_scale": 0.70 if digit == 1 else 0.76,
                    "reference_width_scale": 0.90,
                }
            )
    return tuple(deepcopy(rows))


_FINGER_NAME_TO_DIGIT = {
    "Thumb": 1,
    "Index": 2,
    "Mid": 3,
    "Ring": 4,
    "Pinky": 5,
}
_FINGER_RE = re.compile(r"^(?P<side>[lr])(?P<name>Thumb|Index|Mid|Ring|Pinky)(?P<segment>[123])_(?P<serial>\d+)$")
_BIG_TOE_RE = re.compile(r"^(?P<side>[lr])BigToe(?:_(?P<segment>[12]))?_(?P<serial>\d+)$")
_SMALL_TOE_RE = re.compile(r"^(?P<side>[lr])SmallToe(?P<ordinal>[1-4])(?:_(?P<segment>[12]))?_(?P<serial>\d+)$")


def parse_blackproject_digit_bone(name: str) -> dict[str, Any] | None:
    """Map one recognized BlackProject bone name to its digit family."""

    value = str(name)
    match = _FINGER_RE.fullmatch(value)
    if match:
        side = match.group("side").upper()
        digit = _FINGER_NAME_TO_DIGIT[match.group("name")]
        return {
            "bone": value,
            "kind": "fingernail",
            "prefix": "finger",
            "side": side,
            "digit": digit,
            "segment": int(match.group("segment")),
            "family": f"finger{digit}.{side}",
        }
    match = _BIG_TOE_RE.fullmatch(value)
    if match:
        side = match.group("side").upper()
        return {
            "bone": value,
            "kind": "toenail",
            "prefix": "toe",
            "side": side,
            "digit": 1,
            "segment": int(match.group("segment") or 0),
            "family": f"toe1.{side}",
        }
    match = _SMALL_TOE_RE.fullmatch(value)
    if match:
        side = match.group("side").upper()
        digit = int(match.group("ordinal")) + 1
        return {
            "bone": value,
            "kind": "toenail",
            "prefix": "toe",
            "side": side,
            "digit": digit,
            "segment": int(match.group("segment") or 0),
            "family": f"toe{digit}.{side}",
        }
    return None


def digit_weight_evidence(
    influences: Mapping[str, float], expected_family: str
) -> dict[str, Any]:
    """Summarize normalized raw-cage weights for one declared digit."""

    family_prefix, family_side = str(expected_family).split(".", 1)
    expected_prefix = "finger" if family_prefix.startswith("finger") else "toe"
    family_weights: dict[str, float] = {}
    wrong_side = 0.0
    total = 0.0
    normalized: dict[str, float] = {}
    for bone_name, raw_weight in influences.items():
        weight = float(raw_weight)
        if not math.isfinite(weight) or weight < 0.0:
            raise KiraBlackProjectNailContractError(
                f"non-finite or negative bone weight: {bone_name}"
            )
        if weight == 0.0:
            continue
        total += weight
        normalized[str(bone_name)] = weight
    if total <= 0.0:
        raise KiraBlackProjectNailContractError("sample has no positive weight")
    normalized = {name: value / total for name, value in normalized.items()}
    for bone_name, weight in normalized.items():
        metadata = parse_blackproject_digit_bone(bone_name)
        if metadata is None:
            continue
        family = str(metadata["family"])
        family_weights[family] = family_weights.get(family, 0.0) + weight
        if metadata["prefix"] == expected_prefix and metadata["side"] != family_side:
            wrong_side += weight
    ranked = sorted(family_weights.items(), key=lambda row: (-row[1], row[0]))
    winner = ranked[0][0] if ranked else None
    expected = float(family_weights.get(str(expected_family), 0.0))
    foreign = sum(
        float(weight)
        for family, weight in family_weights.items()
        if family != expected_family
    )
    return {
        "expected_family_weight": expected,
        "foreign_digit_family_weight": foreign,
        "wrong_side_digit_weight": wrong_side,
        "winning_digit_family": winner,
        "expected_family_is_dominant": winner == expected_family,
        "digit_family_weights": dict(sorted(family_weights.items())),
        "normalized_influences": normalized,
    }


def summarize_footprint_binding(
    *,
    nail_id: str,
    expected_bone: str,
    expected_family: str,
    samples: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Fail closed unless every grid sample belongs to the declared digit."""

    rows = []
    terminal_weights = []
    for index, sample in enumerate(samples):
        influences = {
            str(name): float(weight)
            for name, weight in dict(sample.get("influences", {})).items()
        }
        evidence = digit_weight_evidence(influences, expected_family)
        terminal = float(evidence["normalized_influences"].get(expected_bone, 0.0))
        terminal_weights.append(terminal)
        rows.append({"sample_index": index, **evidence, "exact_terminal_bone_weight": terminal})
    if len(rows) != PROJECTION_GRID_SIZE * PROJECTION_GRID_SIZE:
        raise KiraBlackProjectNailContractError(
            f"{nail_id} footprint requires exactly 81 samples"
        )
    sorted_terminal = sorted(terminal_weights)
    median_terminal = sorted_terminal[len(sorted_terminal) // 2]
    gates = {
        "every_sample_expected_family_at_least_0_99": all(
            row["expected_family_weight"] >= MINIMUM_EXPECTED_FAMILY_WEIGHT
            for row in rows
        ),
        "every_sample_foreign_digit_at_most_0_01": all(
            row["foreign_digit_family_weight"]
            <= MAXIMUM_FOREIGN_DIGIT_FAMILY_WEIGHT
            for row in rows
        ),
        "every_sample_wrong_side_at_most_0_01": all(
            row["wrong_side_digit_weight"] <= MAXIMUM_WRONG_SIDE_DIGIT_WEIGHT
            for row in rows
        ),
        "every_sample_expected_family_dominant": all(
            row["expected_family_is_dominant"] is True for row in rows
        ),
        "median_exact_terminal_bone_at_least_0_90": (
            median_terminal >= MINIMUM_MEDIAN_EXACT_TERMINAL_BONE_WEIGHT
        ),
    }
    if not all(gates.values()):
        failed = sorted(name for name, passed in gates.items() if not passed)
        raise KiraBlackProjectNailContractError(
            f"{nail_id} strict footprint binding failed: {failed}"
        )
    return {
        "schema": SCHEMA,
        "nail_id": str(nail_id),
        "expected_bone": str(expected_bone),
        "expected_family": str(expected_family),
        "sample_count": len(rows),
        "minimum_expected_family_weight": min(
            row["expected_family_weight"] for row in rows
        ),
        "maximum_foreign_digit_family_weight": max(
            row["foreign_digit_family_weight"] for row in rows
        ),
        "maximum_wrong_side_digit_weight": max(
            row["wrong_side_digit_weight"] for row in rows
        ),
        "median_exact_terminal_bone_weight": median_terminal,
        "gates": gates,
        "passed": True,
        "per_sample": rows,
    }


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def component_payload_sha256(component: Mapping[str, Any]) -> str:
    payload = dict(component)
    payload.pop("component_payload_sha256", None)
    return canonical_json_sha256(payload)


def validate_cached_component(
    component: Mapping[str, Any],
    *,
    source_blend_sha256: str,
    source_non_nail_manifest_sha256: str,
    rig_rest_sha256: str,
    run_config_sha256: str,
) -> dict[str, Any]:
    """Validate one reusable passing top plate without trusting its filename."""

    row = deepcopy(dict(component))
    inventory = {item["nail_id"]: item for item in expected_nail_inventory()}
    nail_id = str(row.get("nail_id", ""))
    if nail_id not in inventory:
        raise KiraBlackProjectNailContractError("cache has unknown nail ID")
    definition = inventory[nail_id]
    bindings = {
        "source_blend_sha256": source_blend_sha256,
        "source_non_nail_manifest_sha256": source_non_nail_manifest_sha256,
        "rig_rest_sha256": rig_rest_sha256,
        "run_config_sha256": run_config_sha256,
    }
    for field, expected in bindings.items():
        if str(row.get(field, "")) != str(expected):
            raise KiraBlackProjectNailContractError(
                f"cached {nail_id} binding changed: {field}"
            )
    for field in ("bone", "family", "kind", "side", "digit"):
        if row.get(field) != definition[field]:
            raise KiraBlackProjectNailContractError(
                f"cached {nail_id} identity changed: {field}"
            )
    points = row.get("top_surface_vertices_world_m")
    normals = row.get("top_surface_normals_world")
    clearances = row.get("base_clearances_m")
    sample_count = PROJECTION_GRID_SIZE * PROJECTION_GRID_SIZE
    if not all(
        isinstance(values, list) and len(values) == sample_count
        for values in (points, normals, clearances)
    ):
        raise KiraBlackProjectNailContractError(
            f"cached {nail_id} does not contain the complete 9x9 top surface"
        )
    numeric_rows: Sequence[Any] = list(points) + list(normals)
    if any(
        not isinstance(values, list)
        or len(values) != 3
        or any(not math.isfinite(float(value)) for value in values)
        for values in numeric_rows
    ):
        raise KiraBlackProjectNailContractError(
            f"cached {nail_id} contains non-finite XYZ geometry"
        )
    if any(not math.isfinite(float(value)) or float(value) <= 0.0 for value in clearances):
        raise KiraBlackProjectNailContractError(
            f"cached {nail_id} contains invalid base clearances"
        )
    if row.get("all_strict_gates_passed") is not True:
        raise KiraBlackProjectNailContractError(
            f"cached {nail_id} was not a passing component"
        )
    expected_hash = component_payload_sha256(row)
    if str(row.get("component_payload_sha256", "")) != expected_hash:
        raise KiraBlackProjectNailContractError(
            f"cached {nail_id} payload hash mismatch"
        )
    return row


def validate_component_cache(
    cache: Mapping[str, Any],
    *,
    source_blend_sha256: str,
    source_non_nail_manifest_sha256: str,
    rig_rest_sha256: str,
    run_config_sha256: str,
) -> dict[str, Any]:
    """Validate an append-only partial-success cache for a later attempt."""

    record = deepcopy(dict(cache))
    if record.get("schema") != CACHE_SCHEMA:
        raise KiraBlackProjectNailContractError("unsupported component-cache schema")
    components = list(record.get("components", []))
    ids = [str(row.get("nail_id", "")) for row in components]
    if len(ids) != len(set(ids)):
        raise KiraBlackProjectNailContractError("component cache repeats a nail ID")
    validated = [
        validate_cached_component(
            row,
            source_blend_sha256=source_blend_sha256,
            source_non_nail_manifest_sha256=source_non_nail_manifest_sha256,
            rig_rest_sha256=rig_rest_sha256,
            run_config_sha256=run_config_sha256,
        )
        for row in components
    ]
    return {
        **record,
        "components": validated,
        "component_count": len(validated),
        "validated_for_exact_reuse": True,
    }


__all__ = [
    "CACHE_SCHEMA",
    "EXPECTED_NAIL_COUNT",
    "KiraBlackProjectNailContractError",
    "MAXIMUM_FOREIGN_DIGIT_FAMILY_WEIGHT",
    "MAXIMUM_WRONG_SIDE_DIGIT_WEIGHT",
    "METHOD_ID",
    "MINIMUM_EXPECTED_FAMILY_WEIGHT",
    "MINIMUM_MEDIAN_EXACT_TERMINAL_BONE_WEIGHT",
    "PROJECTION_GRID_SIZE",
    "SCHEMA",
    "canonical_json_sha256",
    "component_payload_sha256",
    "digit_weight_evidence",
    "expected_nail_inventory",
    "parse_blackproject_digit_bone",
    "summarize_footprint_binding",
    "validate_cached_component",
    "validate_component_cache",
]
