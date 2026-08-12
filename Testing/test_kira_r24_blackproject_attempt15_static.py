from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / (
    "RecoverySprint/continuation_20260807/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT15_CONFIG.json"
)
WORKER_PATH = ROOT / (
    "tools/blender_simulate_kira_r24_blackproject_local_reconstruction_attempt15.py"
)
TOPOLOGY_PATH = ROOT / (
    "RecoverySprint/continuation_20260807/"
    "r24_blackproject_patch_reconstruction_diagnostic/attempt_01/"
    "BLACKPROJECT_ATTEMPT02_INTERSECTION_TOPOLOGY.json"
)
DOMAIN_PATH = ROOT / (
    "RecoverySprint/continuation_20260807/"
    "r24_blackproject_patch_reconstruction_diagnostic/attempt_02/"
    "BLACKPROJECT_ATTEMPT02_REPAIR_DOMAIN.json"
)
FILL_PATH = ROOT / (
    "RecoverySprint/continuation_20260807/"
    "r24_blackproject_patch_reconstruction_diagnostic/attempt_03/"
    "BLACKPROJECT_ATTEMPT02_LOCAL_FILL_PROBE.json"
)
HARMONIC_PATH = ROOT / (
    "RecoverySprint/continuation_20260807/"
    "r24_blackproject_patch_reconstruction_diagnostic/attempt_04/"
    "BLACKPROJECT_ATTEMPT02_LOCAL_HARMONIC_SCAN.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Attempt15StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.worker = WORKER_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.worker)
        cls.topology = json.loads(TOPOLOGY_PATH.read_text(encoding="utf-8"))
        cls.domain = json.loads(DOMAIN_PATH.read_text(encoding="utf-8"))
        cls.fill = json.loads(FILL_PATH.read_text(encoding="utf-8"))
        cls.harmonic = json.loads(HARMONIC_PATH.read_text(encoding="utf-8"))

    def test_01_all_bound_inputs_are_present_and_hash_exact(self) -> None:
        for name, record in self.config["inputs"].items():
            path = ROOT / record["path"]
            self.assertTrue(path.is_file(), name)
            self.assertEqual(sha256_file(path), record["sha256"], name)

    def test_02_license_and_scope_are_exact(self) -> None:
        license_record = self.config["license"]
        self.assertEqual(license_record["author"], "BlackProject")
        self.assertEqual(license_record["license"], "CC BY 4.0")
        self.assertTrue(license_record["derivative_attribution_required"])
        self.assertEqual(
            self.config["mode"], "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
        )
        self.assertFalse(self.config["output"]["blend_save_permitted"])

    def test_03_measured_locality_is_bound_to_evidence(self) -> None:
        measured = self.config["measured_repair_domain"]
        self.assertEqual(measured["initial_exact_pair_count"], 28)
        self.assertEqual(
            self.topology["attempt02"]["exact_report"][
                "exact_genuine_penetration_pair_count"
            ],
            28,
        )
        self.assertEqual(self.topology["attempt02"]["involved_vertex_count"], 31)
        self.assertEqual(
            self.topology["attempt02"][
                "minimum_involved_vertex_ring_distance_from_34_seam"
            ],
            6,
        )
        self.assertEqual(
            self.topology["attempt02"][
                "maximum_involved_vertex_ring_distance_from_34_seam"
            ],
            14,
        )
        self.assertEqual(
            self.topology["attempt02_to_r24_interface"][
                "maximum_nearest_distance_m"
            ],
            0.0,
        )
        self.assertTrue(
            self.topology["attempt02_to_r24_interface"]["bijection"]
        )

    def test_04_repair_domain_is_exact_two_ring_disk(self) -> None:
        selected = self.domain["smallest_qualified_replacement_domain"]
        measured = self.config["measured_repair_domain"]
        self.assertEqual(selected["face_ring_expansion"], 2)
        self.assertEqual(selected["face_count"], measured["face_count"])
        self.assertEqual(selected["vertex_count"], measured["vertex_count"])
        self.assertEqual(selected["edge_count"], measured["edge_count"])
        self.assertTrue(selected["is_one_topological_disk"])
        self.assertFalse(selected["touches_global_34_vertex_seam"])
        self.assertEqual(selected["boundary_edge_count"], 32)
        self.assertEqual(selected["boundary_cycle_lengths"], [32])
        self.assertEqual(selected["minimum_vertex_ring_distance_from_global_seam"], 5)

    def test_05_zero_pair_fill_is_feasibility_only_and_quality_rejected(self) -> None:
        exact = self.fill["exact_intersections"]
        fill = self.fill["fill"]
        replacement = self.config["replacement"]
        self.assertEqual(exact["before_genuine_pair_count"], 28)
        self.assertEqual(exact["after_genuine_pair_count"], 0)
        self.assertEqual(fill["maximum_global_34_seam_coordinate_delta_local_units"], 0.0)
        self.assertAlmostEqual(
            fill["minimum_new_triangle_angle_degrees"],
            replacement["reject_feasibility_fill_minimum_angle_degrees"],
        )
        self.assertLess(
            fill["minimum_new_triangle_angle_degrees"],
            replacement["minimum_new_triangle_angle_degrees"],
        )
        self.assertFalse(self.fill["truth"]["qualified_for_body_use"])

    def test_06_topology_preserving_harmonic_family_is_rejected(self) -> None:
        variants = self.harmonic["variants"]
        self.assertTrue(variants)
        self.assertTrue(all(row["exact_genuine_pair_count"] > 0 for row in variants))
        self.assertIsNone(
            self.harmonic["minimum_movement_zero_intersection_variant"]
        )

    def test_07_worker_has_required_reconstruction_and_hard_gates(self) -> None:
        required = (
            "delaunay_2d_cdt",
            "quality_refined_cdt",
            "solve_dirichlet",
            "minimum_new_triangle_angle_degrees",
            "minimum_new_triangle_world_area_m2",
            "standalone_patch_exact_genuine_intersections_zero",
            "post_graft_patch_related_exact_genuine_intersections_zero",
            "global_34_seam_coordinate_delta_m_exact_zero",
            "nonpatch_body_and_face_snapshot_exact",
            "native_rig_exact",
            "inherited_pair_signature",
            "render_uniform_clay_pairs_without_subdivision",
        )
        for value in required:
            self.assertIn(value, self.worker)

    def test_08_worker_contains_no_blend_save_or_activation_path(self) -> None:
        forbidden = (
            "save_as_mainfile",
            "save_mainfile",
            "write_homefile",
            "runtime_assignment_allowed = True",
            "runtime_activation_allowed = True",
            "owner_approved = True",
        )
        for value in forbidden:
            self.assertNotIn(value, self.worker)
        self.assertIn('"blend_saved": False', self.worker)
        self.assertIn('"save_allowed": False', self.worker)

    def test_09_zero_intersection_gate_does_not_hide_inherited_body_pairs(self) -> None:
        gates = self.config["hard_gates"]
        self.assertEqual(gates["standalone_patch_exact_genuine_intersections"], 0)
        self.assertEqual(
            gates["post_graft_patch_related_exact_genuine_intersections"], 0
        )
        self.assertEqual(
            gates["post_graft_new_noninherited_exact_genuine_intersections"], 0
        )
        self.assertEqual(
            gates["preserved_inherited_nonpatch_exact_genuine_intersections"],
            29,
        )
        self.assertIn('"whole_body_intersections_zero": False', self.worker)

    def test_10_paired_visual_contract_matches_attempt14(self) -> None:
        visual = self.config["paired_visual_evidence"]
        required = visual["required_candidate_views"]
        self.assertEqual(required, visual["required_same_camera_pairs"])
        self.assertGreaterEqual(len(required), 13)
        for filename in required:
            baseline = ROOT / visual["baseline_root"] / filename
            self.assertTrue(baseline.is_file(), filename)
        self.assertIn("render_evidence", self.worker)
        self.assertIn("same_camera_light_clay_contract", self.worker)

    def test_11_attempt15_slot_is_append_only_and_unallocated(self) -> None:
        self.assertEqual(self.config["attempt_id"], "attempt_15")
        self.assertFalse((ROOT / self.config["output"]["root"]).exists())


if __name__ == "__main__":
    unittest.main()
