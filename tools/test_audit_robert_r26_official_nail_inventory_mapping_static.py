from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT = PROJECT_ROOT / "Tools/audit_robert_r26_official_nail_inventory_mapping.py"


class RobertR26OfficialNailInventoryMappingAuditStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = AUDIT.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_exact_config_and_staged_result_are_bound(self) -> None:
        for token in (
            '"c64fa0f833caa86fb59a53d46ab98852ecd8a926666680a1aad11cce54a07c57"',
            '"c5df50067511dbaffcad5f735416e5b1f5777c06670e5784d2f21d409093b4fc"',
            "EXPECTED_R26_DIAGNOSTIC_SHA256",
            "if sha256_file(config_path) != EXPECTED_CONFIG_SHA256:",
            "if sha256_file(diagnostic_path) != EXPECTED_R26_DIAGNOSTIC_SHA256:",
        ):
            self.assertIn(token, self.source)

    def test_all_twenty_inventory_is_a_required_gate(self) -> None:
        for token in (
            "for definition in expected_nail_inventory():",
            "source_validation = validate_all_twenty_bindings(source_records)",
            '"exact_20_source_inventory_rows": len(source_records) == 20',
            '"all_20_official_source_terminal_neighborhoods_match_inventory"',
            '"all_20_inventory_bones_nearest_their_official_weight_centroid"',
        ):
            self.assertIn(token, self.source)

    def test_ordered_target_skeleton_weight_and_body_sources_are_used(self) -> None:
        for token in (
            "parse_body_obj(base_path)",
            "target_path_from_report(",
            "apply_target(vertices, path, float(row[\"weight\"]))",
            "source_weights(weights_path, len(vertices))",
            "terminal_point(rig, vertices, bone)",
            "weighted_centroid(",
            "NEAREST_SOURCE_BODY_VERTEX_COUNT = 32",
        ):
            self.assertIn(token, self.source)

    def test_preserved_neighbor_digit_mismatch_is_fail_closed(self) -> None:
        for token in (
            "preserved_R26_finger5_L_footprint_rejected",
            "preserved_R26_finger5_L_winning_family_is_finger4_L",
            'observed_binding["winning_digit_family"] == "finger4.L"',
            '"remap_fingernail_5_L_to_finger4_is_supported": False',
            '"no_automatic_bone_remap"',
        ):
            self.assertIn(token, self.source)

    def test_append_only_output_and_no_mutating_capabilities(self) -> None:
        self.assertIn("if output_path.exists():", self.source)
        self.assertIn("output_path.write_text(", self.source)
        forbidden = (
            r"\bbpy\b",
            r"subprocess",
            r"requests",
            r"urllib",
            r"save_as_mainfile",
            r"config_path\.write",
            r"unlink\(",
            r"remove\(",
        )
        for pattern in forbidden:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, self.source))


if __name__ == "__main__":
    unittest.main()
