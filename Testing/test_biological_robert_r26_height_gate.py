from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "biological_robert_r26_read_only_preparation"
    / "ROBERT_R26_BUILD_CONFIG.json"
)
WORKER_PATH = ROOT / "Tools" / "blender_build_biological_robert_r26_bald_owner_review.py"


class BiologicalRobertR26HeightGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.worker = WORKER_PATH.read_text(encoding="utf-8")

    def test_exact_separate_height_values_are_bound(self) -> None:
        truth = self.config["foundation_truth"]
        self.assertEqual(truth["prior_v25_r6_reference_height_m"], 1.7441400527954103)
        self.assertEqual(truth["expected_warped_height_m"], 1.746924877166748)
        self.assertEqual(truth["expected_warped_height_tolerance_m"], 0.000001)
        self.assertNotIn("target_height_m", truth)

    def test_exact_extrema_and_lower_body_are_bound(self) -> None:
        truth = self.config["foundation_truth"]
        self.assertEqual(truth["expected_warped_native_floor_z"], -8.181000709533691)
        self.assertEqual(truth["expected_warped_native_top_z"], 9.288248062133789)
        self.assertEqual(truth["expected_warped_floor_vertex_ids"], [6371, 12963])
        self.assertEqual(truth["expected_warped_crown_vertex_id"], 991)
        self.assertEqual(truth["expected_frozen_lower_body_vertex_count"], 9191)
        self.assertEqual(
            truth["expected_frozen_lower_body_signature"],
            "71bea0d9e85c5191931fd5ec654e97d0b9b74eb0f572d1292dcb1f4357b2a29c",
        )

    def test_historical_height_provenance_is_hash_bound(self) -> None:
        row = self.config["inputs"]["prior_v25_r6_height_provenance"]
        path = ROOT / row["path"]
        self.assertTrue(path.is_file())
        self.assertEqual(row["bytes"], path.stat().st_size)
        import hashlib

        self.assertEqual(row["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_worker_uses_explicit_gate_and_has_no_generic_two_mm_gate(self) -> None:
        ast.parse(self.worker)
        self.assertIn("def validate_expected_warped_height_envelope(", self.worker)
        self.assertIn('height_envelope["expected_warped_height_m"]', self.worker)
        self.assertIn('height_envelope["expected_warped_height_tolerance_m"]', self.worker)
        self.assertIn('truth["expected_warped_crown_vertex_id"]', self.worker)
        self.assertIn('truth["expected_warped_floor_vertex_ids"]', self.worker)
        self.assertNotIn('config["foundation_truth"]["target_height_m"]', self.worker)
        self.assertNotIn(" > 0.002", self.worker)

    def test_height_envelope_is_mandatory_and_evidenced(self) -> None:
        self.assertIn(
            "bound_warped_height_envelope", self.config["mandatory_exact_audits"]
        )
        self.assertIn(
            '"bound_warped_height_envelope": height_envelope', self.worker
        )
        self.assertIn(
            '"bound_warped_height_envelope": bool(height_envelope["passed"])',
            self.worker,
        )


if __name__ == "__main__":
    unittest.main()
