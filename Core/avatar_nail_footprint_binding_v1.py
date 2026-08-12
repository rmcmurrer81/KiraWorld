"""Pure fail-closed validation for avatar nail-to-digit footprint bindings.

The nail inventory names a physical digit and an official terminal bone.  A
geometrically plausible plate is not acceptable if the body surface under that
plate is weighted to another digit.  This module validates that relationship
without Blender and never guesses a replacement bone from a nearby surface.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from statistics import median
from typing import Any, Iterable, Mapping


SCHEMA = "kira.avatar.nail_footprint_binding.v1"
EXPECTED_NAIL_COUNT = 20
FINAL_FOOTPRINT_POLICY: dict[str, Any] = {
    "name": "final_nail_footprint",
    "minimum_mean_expected_family_weight": 0.99,
    "minimum_median_expected_family_weight": 0.99,
    "minimum_each_expected_family_weight": 0.99,
    "minimum_median_exact_terminal_bone_weight": 0.90,
    "maximum_foreign_digit_family_weight": 0.01,
    "maximum_wrong_side_digit_weight": 0.01,
    "require_expected_family_dominant_every_sample": True,
}
SOURCE_NEIGHBORHOOD_POLICY: dict[str, Any] = {
    "name": "source_terminal_neighborhood",
    "minimum_mean_expected_family_weight": 0.50,
    "minimum_median_expected_family_weight": 0.50,
    "minimum_each_expected_family_weight": 0.0,
    "minimum_median_exact_terminal_bone_weight": 0.0,
    "maximum_foreign_digit_family_weight": 1.0,
    "maximum_wrong_side_digit_weight": 0.05,
    "require_expected_family_dominant_every_sample": False,
}

_BONE_PATTERN = re.compile(r"^(finger|toe)([1-5])-([1-3])\.([LR])$")


def expected_terminal_bone(kind: str, digit: int, side: str) -> str:
    kind_value = str(kind)
    digit_value = int(digit)
    side_value = str(side)
    if kind_value not in {"fingernail", "toenail"}:
        raise ValueError(f"unsupported nail kind: {kind_value}")
    if not 1 <= digit_value <= 5:
        raise ValueError(f"nail digit outside 1..5: {digit_value}")
    if side_value not in {"L", "R"}:
        raise ValueError(f"unsupported nail side: {side_value}")
    prefix = "finger" if kind_value == "fingernail" else "toe"
    segment = 2 if prefix == "toe" and digit_value == 1 else 3
    return f"{prefix}{digit_value}-{segment}.{side_value}"


def parse_digit_bone(bone_name: str) -> dict[str, Any] | None:
    match = _BONE_PATTERN.fullmatch(str(bone_name))
    if match is None:
        return None
    prefix, raw_digit, raw_segment, side = match.groups()
    return {
        "prefix": prefix,
        "kind": "fingernail" if prefix == "finger" else "toenail",
        "digit": int(raw_digit),
        "segment": int(raw_segment),
        "side": side,
        "family": f"{prefix}{raw_digit}.{side}",
    }


def _coerce_influences(sample: Mapping[str, Any]) -> dict[str, float]:
    raw = sample.get("influences", sample)
    result: dict[str, float] = defaultdict(float)
    if isinstance(raw, Mapping):
        items = raw.items()
    elif isinstance(raw, Iterable) and not isinstance(raw, (str, bytes)):
        pairs = []
        for row in raw:
            if isinstance(row, Mapping):
                pairs.append((row.get("bone"), row.get("weight")))
            else:
                bone, weight = row
                pairs.append((bone, weight))
        items = pairs
    else:
        raise ValueError("footprint sample influences must be a mapping or rows")
    for raw_bone, raw_weight in items:
        bone = str(raw_bone)
        weight = float(raw_weight)
        if not math.isfinite(weight) or weight < 0.0:
            raise ValueError(f"invalid footprint influence: {bone}={weight}")
        if weight > 0.0:
            result[bone] += weight
    if not result:
        raise ValueError("footprint sample has no positive influences")
    total = sum(result.values())
    if not math.isfinite(total) or total <= 0.0:
        raise ValueError(f"invalid footprint influence sum: {total}")
    # MakeHuman's published weight rows are rounded and some source/helper
    # vertices sum slightly above one.  The R26 transfer normalizes them before
    # assignment, so this pure validator performs the same relative
    # normalization instead of treating harmless source precision as a mapping
    # failure.
    return {bone: weight / total for bone, weight in result.items()}


def summarize_footprint_binding(
    *,
    nail_id: str,
    kind: str,
    digit: int,
    side: str,
    expected_bone: str,
    samples: Iterable[Mapping[str, Any]],
    policy: str = "final_nail_footprint",
) -> dict[str, Any]:
    """Summarize whether every sampled footprint belongs to the named digit.

    Segment weights from the same digit chain are combined.  This allows a
    cuticle-edge sample to blend between terminal and penultimate phalanges,
    while still rejecting a surface owned by a neighboring digit or wrong side.
    """

    policies = {
        str(FINAL_FOOTPRINT_POLICY["name"]): FINAL_FOOTPRINT_POLICY,
        str(SOURCE_NEIGHBORHOOD_POLICY["name"]): SOURCE_NEIGHBORHOOD_POLICY,
    }
    if str(policy) not in policies:
        raise ValueError(f"unknown footprint binding policy: {policy}")
    selected_policy = dict(policies[str(policy)])
    exact_expected = expected_terminal_bone(kind, digit, side)
    if str(expected_bone) != exact_expected:
        raise ValueError(
            f"inventory terminal bone mismatch: {nail_id};"
            f"expected={exact_expected};actual={expected_bone}"
        )
    expected_meta = parse_digit_bone(exact_expected)
    if expected_meta is None:
        raise ValueError(f"could not parse expected terminal bone: {exact_expected}")
    rows = [_coerce_influences(dict(sample)) for sample in samples]
    if not rows:
        raise ValueError(f"nail footprint has no samples: {nail_id}")

    expected_family = str(expected_meta["family"])
    expected_weights: list[float] = []
    wrong_side_weights: list[float] = []
    foreign_family_weights: list[float] = []
    expected_family_dominant: list[bool] = []
    family_totals: dict[str, float] = defaultdict(float)
    exact_terminal_weights: list[float] = []
    all_influence_names: set[str] = set()
    per_sample = []
    for index, influences in enumerate(rows):
        all_influence_names.update(influences)
        sample_families: dict[str, float] = defaultdict(float)
        wrong_side = 0.0
        for bone, weight in influences.items():
            meta = parse_digit_bone(bone)
            if meta is None:
                continue
            family = str(meta["family"])
            sample_families[family] += weight
            family_totals[family] += weight
            if (
                meta["prefix"] == expected_meta["prefix"]
                and meta["side"] != expected_meta["side"]
            ):
                wrong_side += weight
        expected_weight = float(sample_families.get(expected_family, 0.0))
        exact_terminal_weight = float(influences.get(exact_expected, 0.0))
        foreign_weight = sum(
            weight
            for family, weight in sample_families.items()
            if family != expected_family
        )
        ranked_sample = sorted(
            sample_families.items(), key=lambda item: (-item[1], item[0])
        )
        sample_winner = ranked_sample[0][0] if ranked_sample else None
        expected_weights.append(expected_weight)
        exact_terminal_weights.append(exact_terminal_weight)
        wrong_side_weights.append(wrong_side)
        foreign_family_weights.append(foreign_weight)
        expected_family_dominant.append(sample_winner == expected_family)
        per_sample.append(
            {
                "sample_index": index,
                "expected_family_weight": expected_weight,
                "exact_terminal_bone_weight": exact_terminal_weight,
                "foreign_digit_family_weight": foreign_weight,
                "wrong_side_digit_weight": wrong_side,
                "winning_digit_family": sample_winner,
                "expected_digit_family_is_dominant": sample_winner
                == expected_family,
                "digit_family_weights": dict(sorted(sample_families.items())),
            }
        )

    mean_family_weights = {
        family: total / len(rows) for family, total in family_totals.items()
    }
    ranked = sorted(
        mean_family_weights.items(), key=lambda item: (-item[1], item[0])
    )
    winning_family = ranked[0][0] if ranked else None
    mean_expected = sum(expected_weights) / len(expected_weights)
    median_expected = float(median(expected_weights))
    median_exact_terminal = float(median(exact_terminal_weights))
    maximum_foreign = max(foreign_family_weights)
    maximum_wrong_side = max(wrong_side_weights)
    gates = {
        "inventory_terminal_bone_exact": str(expected_bone) == exact_expected,
        "expected_digit_family_is_winner": winning_family == expected_family,
        "mean_expected_family_weight_meets_policy": mean_expected
        >= float(selected_policy["minimum_mean_expected_family_weight"]),
        "median_expected_family_weight_meets_policy": median_expected
        >= float(selected_policy["minimum_median_expected_family_weight"]),
        "minimum_expected_family_weight_meets_policy": min(expected_weights)
        >= float(selected_policy["minimum_each_expected_family_weight"]),
        "median_exact_terminal_bone_weight_meets_policy": median_exact_terminal
        >= float(selected_policy["minimum_median_exact_terminal_bone_weight"]),
        "foreign_digit_family_weight_bounded": maximum_foreign
        <= float(selected_policy["maximum_foreign_digit_family_weight"]),
        "wrong_side_digit_weight_bounded": maximum_wrong_side
        <= float(selected_policy["maximum_wrong_side_digit_weight"]),
        "expected_family_dominant_every_sample_if_required": (
            all(expected_family_dominant)
            if bool(selected_policy["require_expected_family_dominant_every_sample"])
            else True
        ),
    }
    return {
        "schema": SCHEMA,
        "nail_id": str(nail_id),
        "kind": str(kind),
        "digit": int(digit),
        "side": str(side),
        "expected_terminal_bone": exact_expected,
        "expected_digit_family": expected_family,
        "policy": selected_policy,
        "sample_count": len(rows),
        "all_influence_names": sorted(all_influence_names),
        "mean_digit_family_weights": dict(sorted(mean_family_weights.items())),
        "winning_digit_family": winning_family,
        "mean_expected_digit_family_weight": mean_expected,
        "median_expected_digit_family_weight": median_expected,
        "minimum_expected_digit_family_weight": min(expected_weights),
        "maximum_expected_digit_family_weight": max(expected_weights),
        "mean_exact_terminal_bone_weight": sum(exact_terminal_weights)
        / len(exact_terminal_weights),
        "median_exact_terminal_bone_weight": median_exact_terminal,
        "maximum_foreign_digit_family_weight": maximum_foreign,
        "maximum_wrong_side_digit_weight": maximum_wrong_side,
        "gates": gates,
        "passed": all(gates.values()),
        "per_sample": per_sample,
        "automatic_bone_remap_performed": False,
    }


def validate_all_twenty_bindings(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in records]
    ids = [str(row.get("nail_id", "")) for row in rows]
    if len(rows) != EXPECTED_NAIL_COUNT or len(set(ids)) != EXPECTED_NAIL_COUNT:
        raise ValueError("footprint binding audit requires 20 unique nail records")
    expected_ids = {
        f"{kind}_{digit}_{side}"
        for kind in ("fingernail", "toenail")
        for side in ("L", "R")
        for digit in range(1, 6)
    }
    if set(ids) != expected_ids:
        raise ValueError("footprint binding nail inventory differs from all twenty")
    failed = sorted(
        str(row["nail_id"]) for row in rows if row.get("passed") is not True
    )
    if failed:
        raise ValueError(f"one or more nail footprint bindings failed: {failed}")
    return {
        "schema": SCHEMA,
        "nail_count": len(rows),
        "fingernail_count": sum(row.get("kind") == "fingernail" for row in rows),
        "toenail_count": sum(row.get("kind") == "toenail" for row in rows),
        "all_twenty_unique": True,
        "all_footprints_match_declared_digit_family": True,
        "automatic_bone_remap_performed": False,
    }


__all__ = [
    "EXPECTED_NAIL_COUNT",
    "FINAL_FOOTPRINT_POLICY",
    "SCHEMA",
    "SOURCE_NEIGHBORHOOD_POLICY",
    "expected_terminal_bone",
    "parse_digit_bone",
    "summarize_footprint_binding",
    "validate_all_twenty_bindings",
]
