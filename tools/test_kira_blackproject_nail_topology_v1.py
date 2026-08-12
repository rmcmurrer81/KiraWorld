from __future__ import annotations

import unittest

from Core.kira_blackproject_nail_topology_v1 import (
    CACHE_SCHEMA,
    KiraBlackProjectNailContractError,
    PROJECTION_GRID_SIZE,
    component_payload_sha256,
    digit_weight_evidence,
    expected_nail_inventory,
    parse_blackproject_digit_bone,
    summarize_footprint_binding,
    validate_component_cache,
)


class KiraBlackProjectNailTopologyV1Tests(unittest.TestCase):
    def test_inventory_is_exact_bilateral_all_twenty(self) -> None:
        rows = expected_nail_inventory()
        self.assertEqual(len(rows), 20)
        self.assertEqual(len({row["nail_id"] for row in rows}), 20)
        self.assertEqual(sum(row["kind"] == "fingernail" for row in rows), 10)
        self.assertEqual(sum(row["kind"] == "toenail" for row in rows), 10)
        expected = {
            "fingernail_1_L": "lThumb3_049",
            "fingernail_2_R": "rIndex3_078",
            "fingernail_4_R": "rRing3_01",
            "fingernail_5_L": "lPinky3_065",
            "toenail_1_R": "rBigToe_2_036",
            "toenail_2_L": "lSmallToe1_2_018",
            "toenail_5_R": "rSmallToe4_2_028",
        }
        actual = {row["nail_id"]: row["bone"] for row in rows}
        for nail_id, bone in expected.items():
            self.assertEqual(actual[nail_id], bone)

    def test_blackproject_parser_groups_segments_without_crossing_digit_or_side(self) -> None:
        cases = {
            "lThumb1_047": "finger1.L",
            "lThumb3_049": "finger1.L",
            "rRing3_01": "finger4.R",
            "lSmallToe1_1_017": "toe2.L",
            "lSmallToe1_2_018": "toe2.L",
            "rSmallToe4_2_028": "toe5.R",
            "rBigToe_2_036": "toe1.R",
        }
        for bone, family in cases.items():
            with self.subTest(bone=bone):
                self.assertEqual(parse_blackproject_digit_bone(bone)["family"], family)
        self.assertIsNone(parse_blackproject_digit_bone("pelvis_001"))
        self.assertIsNone(parse_blackproject_digit_bone("finger5-3.L"))

    def test_weight_evidence_keeps_non_digit_weight_in_the_denominator(self) -> None:
        evidence = digit_weight_evidence(
            {"lIndex3_053": 0.97, "lHand_045": 0.03}, "finger2.L"
        )
        self.assertAlmostEqual(evidence["expected_family_weight"], 0.97)
        self.assertEqual(evidence["foreign_digit_family_weight"], 0.0)

    def test_complete_81_sample_footprint_requires_terminal_median(self) -> None:
        samples = [
            {"influences": {"lPinky3_065": 1.0}}
            for _ in range(PROJECTION_GRID_SIZE * PROJECTION_GRID_SIZE)
        ]
        result = summarize_footprint_binding(
            nail_id="fingernail_5_L",
            expected_bone="lPinky3_065",
            expected_family="finger5.L",
            samples=samples,
        )
        self.assertTrue(result["passed"])
        samples[0] = {"influences": {"lRing3_061": 1.0}}
        with self.assertRaises(KiraBlackProjectNailContractError):
            summarize_footprint_binding(
                nail_id="fingernail_5_L",
                expected_bone="lPinky3_065",
                expected_family="finger5.L",
                samples=samples,
            )

    def test_component_cache_is_hash_bound_and_tamper_evident(self) -> None:
        count = PROJECTION_GRID_SIZE * PROJECTION_GRID_SIZE
        component = {
            "nail_id": "fingernail_1_L",
            "kind": "fingernail",
            "side": "L",
            "digit": 1,
            "bone": "lThumb3_049",
            "family": "finger1.L",
            "source_blend_sha256": "a" * 64,
            "source_non_nail_manifest_sha256": "b" * 64,
            "rig_rest_sha256": "c" * 64,
            "run_config_sha256": "d" * 64,
            "projection_method": "kira_blackproject_weight_constrained_connected_region_v1",
            "top_surface_vertices_world_m": [[0.0, 0.0, 1.0] for _ in range(count)],
            "top_surface_normals_world": [[0.0, -1.0, 0.0] for _ in range(count)],
            "base_clearances_m": [0.0001 for _ in range(count)],
            "accepted_result_sha256": "e" * 64,
            "all_strict_gates_passed": True,
            "candidate_blend_saved_by_this_component_record": False,
        }
        component["component_payload_sha256"] = component_payload_sha256(component)
        cache = {"schema": CACHE_SCHEMA, "components": [component]}
        result = validate_component_cache(
            cache,
            source_blend_sha256="a" * 64,
            source_non_nail_manifest_sha256="b" * 64,
            rig_rest_sha256="c" * 64,
            run_config_sha256="d" * 64,
        )
        self.assertTrue(result["validated_for_exact_reuse"])
        component["base_clearances_m"][0] = 0.0002
        with self.assertRaises(KiraBlackProjectNailContractError):
            validate_component_cache(
                cache,
                source_blend_sha256="a" * 64,
                source_non_nail_manifest_sha256="b" * 64,
                rig_rest_sha256="c" * 64,
                run_config_sha256="d" * 64,
            )


if __name__ == "__main__":
    unittest.main()
