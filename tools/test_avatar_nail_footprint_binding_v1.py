from __future__ import annotations

import copy
import math
import unittest

from Core.avatar_nail_footprint_binding_v1 import (
    expected_terminal_bone,
    parse_digit_bone,
    summarize_footprint_binding,
    validate_all_twenty_bindings,
)


def passing_record(kind: str, digit: int, side: str) -> dict[str, object]:
    bone = expected_terminal_bone(kind, digit, side)
    prefix = "finger" if kind == "fingernail" else "toe"
    prior_segment = 1 if kind == "toenail" and digit == 1 else 2
    return summarize_footprint_binding(
        nail_id=f"{kind}_{digit}_{side}",
        kind=kind,
        digit=digit,
        side=side,
        expected_bone=bone,
        samples=(
            {"influences": {bone: 1.0}},
            {
                "influences": {
                    bone: 0.72,
                    f"{prefix}{digit}-{prior_segment}.{side}": 0.18,
                }
            },
        ),
    )


class AvatarNailFootprintBindingV1Tests(unittest.TestCase):
    def test_exact_all_twenty_terminal_mapping(self) -> None:
        rows = {
            (kind, digit, side): expected_terminal_bone(kind, digit, side)
            for kind in ("fingernail", "toenail")
            for side in ("L", "R")
            for digit in range(1, 6)
        }
        self.assertEqual(len(rows), 20)
        self.assertEqual(rows[("fingernail", 1, "L")], "finger1-3.L")
        self.assertEqual(rows[("fingernail", 5, "R")], "finger5-3.R")
        self.assertEqual(rows[("toenail", 1, "L")], "toe1-2.L")
        self.assertEqual(rows[("toenail", 5, "R")], "toe5-3.R")

    def test_digit_bone_parser_distinguishes_family_segment_and_side(self) -> None:
        self.assertEqual(
            parse_digit_bone("finger4-2.L"),
            {
                "prefix": "finger",
                "kind": "fingernail",
                "digit": 4,
                "segment": 2,
                "side": "L",
                "family": "finger4.L",
            },
        )
        self.assertIsNone(parse_digit_bone("wrist.L"))

    def test_same_digit_segment_blend_passes(self) -> None:
        result = passing_record("fingernail", 5, "L")
        self.assertIs(result["passed"], True)
        self.assertEqual(result["winning_digit_family"], "finger5.L")
        self.assertIs(result["automatic_bone_remap_performed"], False)

    def test_rounded_source_weight_sum_is_normalized(self) -> None:
        result = summarize_footprint_binding(
            nail_id="fingernail_5_L",
            kind="fingernail",
            digit=5,
            side="L",
            expected_bone="finger5-3.L",
            samples=(
                {
                    "influences": {
                        "finger5-2.L": 0.099,
                        "finger5-3.L": 0.902,
                    }
                },
            ),
        )
        self.assertIs(result["passed"], True)
        self.assertAlmostEqual(result["mean_expected_digit_family_weight"], 1.0)

    def test_preserved_r26_neighbor_digit_case_fails(self) -> None:
        result = summarize_footprint_binding(
            nail_id="fingernail_5_L",
            kind="fingernail",
            digit=5,
            side="L",
            expected_bone="finger5-3.L",
            samples=(
                {"influences": {"finger4-2.L": 0.098, "finger4-3.L": 0.902}},
                {"influences": {"finger4-3.L": 1.0}},
                {"influences": {"finger4-2.L": 0.415, "finger4-3.L": 0.585}},
            ),
        )
        self.assertIs(result["passed"], False)
        self.assertEqual(result["winning_digit_family"], "finger4.L")
        self.assertEqual(result["mean_expected_digit_family_weight"], 0.0)
        self.assertIs(result["gates"]["expected_digit_family_is_winner"], False)

    def test_wrong_side_weight_fails(self) -> None:
        result = summarize_footprint_binding(
            nail_id="toenail_3_L",
            kind="toenail",
            digit=3,
            side="L",
            expected_bone="toe3-3.L",
            samples=(
                {"influences": {"toe3-3.L": 0.70, "toe3-3.R": 0.30}},
            ),
        )
        self.assertIs(result["passed"], False)
        self.assertIs(result["gates"]["wrong_side_digit_weight_bounded"], False)

    def test_inventory_bone_mismatch_and_invalid_weights_raise(self) -> None:
        with self.assertRaisesRegex(ValueError, "inventory terminal bone mismatch"):
            summarize_footprint_binding(
                nail_id="fingernail_5_L",
                kind="fingernail",
                digit=5,
                side="L",
                expected_bone="finger4-3.L",
                samples=({"finger4-3.L": 1.0},),
            )
        with self.assertRaisesRegex(ValueError, "invalid footprint influence"):
            summarize_footprint_binding(
                nail_id="fingernail_5_L",
                kind="fingernail",
                digit=5,
                side="L",
                expected_bone="finger5-3.L",
                samples=({"finger5-3.L": math.nan},),
            )

    def test_all_twenty_validation_passes_and_is_fail_closed(self) -> None:
        records = [
            passing_record(kind, digit, side)
            for kind in ("fingernail", "toenail")
            for side in ("L", "R")
            for digit in range(1, 6)
        ]
        report = validate_all_twenty_bindings(records)
        self.assertEqual(report["nail_count"], 20)
        self.assertIs(report["all_footprints_match_declared_digit_family"], True)
        broken = copy.deepcopy(records)
        broken[-1]["passed"] = False
        with self.assertRaisesRegex(ValueError, "footprint bindings failed"):
            validate_all_twenty_bindings(broken)


if __name__ == "__main__":
    unittest.main()
