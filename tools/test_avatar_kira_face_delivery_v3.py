from pathlib import Path
import unittest

from Core.avatar_kira_face_delivery_v3 import (
    HEAD_REGION_MINIMUM_HEIGHT_FRACTION,
    MAXIMUM_VERTEX_DELTA_M,
    TARGETS,
    validate_contract,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class KiraFaceDeliveryV3Tests(unittest.TestCase):
    def test_contract_and_hashes(self) -> None:
        report = validate_contract(PROJECT_ROOT)
        self.assertEqual(report["target_count"], 11)
        self.assertFalse(report["identity_match_claim_allowed"])
        self.assertFalse(report["topology_change_allowed"])

    def test_bounded_head_only_contract(self) -> None:
        self.assertGreaterEqual(HEAD_REGION_MINIMUM_HEIGHT_FRACTION, 0.75)
        self.assertLessEqual(MAXIMUM_VERTEX_DELTA_M, 0.012)
        self.assertTrue(all(0.0 < float(row["weight"]) <= 0.25 for row in TARGETS))

    def test_paired_cheek_targets(self) -> None:
        pairs = {
            (str(row.get("pair_id")), str(row.get("side")))
            for row in TARGETS
            if row.get("pair_id")
        }
        self.assertEqual(
            pairs,
            {("cheekbone_definition", "left"), ("cheekbone_definition", "right")},
        )


if __name__ == "__main__":
    unittest.main()
