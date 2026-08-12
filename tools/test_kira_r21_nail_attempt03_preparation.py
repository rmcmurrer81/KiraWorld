from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from Core.avatar_nail_weight_constrained_projection_v1 import (
    MAXIMUM_FINAL_CLEARANCE_M,
    MINIMUM_EXPECTED_FAMILY_WEIGHT,
    MINIMUM_FINAL_CLEARANCE_M,
    MINIMUM_OUTWARD_NORMAL_ALIGNMENT,
)
from Core.avatar_natural_nail_delivery_v3 import (
    CENTER_FRACTION_CANDIDATES,
    FOOTPRINT_SCALE_CANDIDATES,
    MAXIMUM_NORMAL_LIFT_ITERATIONS,
    NAIL_PLATE_THICKNESS_M,
    NORMAL_LIFT_STEP_M,
    PROJECTION_GRID_SIZE,
)
from Core.kira_blackproject_nail_topology_v1 import expected_nail_inventory


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "RecoverySprint/continuation_20260802/kira_r21_nail_correction/author_attempt_03_weight_constrained/preparation/RUN_CONFIG.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class KiraR21NailAttempt03PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_config_is_attempt03_prepared_not_run_and_reuse_is_empty(self) -> None:
        self.assertEqual(
            self.config["schema"], "kira.r21.nail_attempt03.run_config.v1"
        )
        self.assertEqual(self.config["attempt"], 3)
        self.assertEqual(self.config["status"], "PREPARED_NOT_RUN")
        self.assertIsNone(self.config["reuse_components_from"])
        self.assertFalse(
            self.config["scope_boundaries"]["blender_executed_during_preparation"]
        )

    def test_exact_source_and_every_fixed_input_are_hash_pinned(self) -> None:
        source = ROOT / self.config["source"]["path"]
        self.assertTrue(source.is_file())
        self.assertEqual(sha256_file(source), self.config["source"]["sha256"])
        for label, row in self.config["fixed_inputs"].items():
            with self.subTest(label=label):
                path = ROOT / row["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(sha256_file(path), row["sha256"])

    def test_exact_inventory_and_all_corrected_anchors_are_present(self) -> None:
        ids = [row["nail_id"] for row in expected_nail_inventory()]
        self.assertEqual(self.config["exact_nail_inventory"], ids)
        self.assertEqual(set(self.config["corrected_reference_anchors_world_m"]), set(ids))
        for values in self.config["corrected_reference_anchors_world_m"].values():
            self.assertEqual(len(values), 3)

    def test_method_constants_match_the_pinned_pure_contracts(self) -> None:
        actual = self.config["method_constants"]
        self.assertEqual(actual["projection_grid"], [PROJECTION_GRID_SIZE] * 2)
        self.assertEqual(actual["footprint_scale_candidates"], list(FOOTPRINT_SCALE_CANDIDATES))
        self.assertEqual(actual["center_fraction_candidates"], list(CENTER_FRACTION_CANDIDATES))
        self.assertEqual(actual["minimum_expected_family_weight"], MINIMUM_EXPECTED_FAMILY_WEIGHT)
        self.assertEqual(actual["minimum_outward_normal_alignment"], MINIMUM_OUTWARD_NORMAL_ALIGNMENT)
        self.assertEqual(actual["minimum_surface_clearance_m"], MINIMUM_FINAL_CLEARANCE_M)
        self.assertEqual(actual["maximum_surface_clearance_m"], MAXIMUM_FINAL_CLEARANCE_M)
        self.assertEqual(actual["nail_plate_thickness_m"], NAIL_PLATE_THICKNESS_M)
        self.assertEqual(actual["normal_lift_step_m"], NORMAL_LIFT_STEP_M)
        self.assertEqual(actual["maximum_normal_lift_iterations"], MAXIMUM_NORMAL_LIFT_ITERATIONS)

    def test_output_is_fail_closed_and_private(self) -> None:
        gates = self.config["strict_gates"]
        self.assertTrue(all(gates.values()))
        self.assertFalse(self.config["outputs"]["candidate_save_on_partial_pass"])
        boundaries = self.config["scope_boundaries"]
        self.assertFalse(boundaries["activation_assignment_export_publication_or_upload_allowed"])
        self.assertFalse(boundaries["visual_or_owner_acceptance_claimed"])


if __name__ == "__main__":
    unittest.main()
