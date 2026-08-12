from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_r24_internal_midpoint_fair_surface"
)
CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_r24_expanded_carrier_attempt17_preparation"
    / "KIRA_R24_ATTEMPT17_EXPANDED_CARRIER_CONFIG.json"
)
WORKER = ROOT / "tools" / "blender_simulate_kira_r24_attempt17_expanded_carrier_resurface.py"
PROPOSAL = EVIDENCE_ROOT / "PREFLIGHT" / "ATTEMPT_17_EXPANDED_CARRIER_RESURFACE_PROPOSAL.md"
R23_PREFLIGHT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_r23_cc0_afes_expanded_mask"
    / "preflight_attempt_04"
    / "PREFLIGHT.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def preserved_attempt_manifest() -> dict:
    rows = []
    for number in range(1, 16):
        directory = EVIDENCE_ROOT / f"attempt_{number:02d}"
        for path in sorted(item for item in directory.rglob("*") if item.is_file()):
            rows.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    return {
        "file_count": len(rows),
        "total_bytes": sum(row["bytes"] for row in rows),
        "canonical_manifest_sha256": canonical_json_sha256(rows),
    }


class R24Attempt17ExpandedCarrierStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_json(CONFIG)
        cls.evidence = load_json(R23_PREFLIGHT)
        cls.source = WORKER.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source, filename=str(WORKER))

    def test_all_bound_files_and_preserved_attempts_are_exact(self) -> None:
        for name, binding in self.config["bindings"].items():
            path = ROOT / binding["path"]
            with self.subTest(name=name):
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, binding["bytes"])
                self.assertEqual(sha256(path), binding["sha256"])
        self.assertEqual(
            preserved_attempt_manifest(),
            {
                key: self.config["preserved_attempts_01_15"][key]
                for key in (
                    "file_count",
                    "total_bytes",
                    "canonical_manifest_sha256",
                )
            },
        )

    def test_exact_audited_mask_contract_is_reused(self) -> None:
        contract = self.config["expanded_mask_contract"]
        selected = self.evidence["expanded_r19_mask"]
        topology = selected["selected_topology"]
        self.assertEqual(contract["face_count"], 695)
        self.assertEqual(contract["incident_vertex_count"], 394)
        self.assertEqual(contract["edge_count"], 1088)
        self.assertEqual(contract["outer_boundary_vertices"], 91)
        self.assertEqual(contract["face_index_sha256"], selected["selected_face_index_sha256"])
        self.assertEqual(contract["ordered_outer_seam_sha256"], selected["ordered_outer_seam_sha256"])
        self.assertEqual(contract["face_index_sha256"], topology["face_index_sha256"])
        self.assertEqual(contract["incident_vertex_sha256"], topology["vertex_index_sha256"])
        self.assertEqual(contract["edge_sha256"], topology["edge_sha256"])
        self.assertTrue(topology["is_one_disk"])
        self.assertEqual(selected["selected_exterior_rings"], 2)
        self.assertTrue(
            self.evidence["deterministic_selection_checks"]["all_selection_gates_pass"]
        )

    def test_scope_is_append_only_no_save_and_no_donor(self) -> None:
        scope = self.config["scope"]
        self.assertEqual(scope["expected_attempt"], "attempt_17")
        self.assertTrue(scope["append_only"])
        self.assertTrue(scope["simulation_only"])
        for key in (
            "blend_save_allowed",
            "export_allowed",
            "runtime_activation_allowed",
            "donor_geometry_load_allowed",
            "separate_anatomy_object_allowed",
            "scalp_hair_allowed",
        ):
            self.assertFalse(scope[key], key)
        self.assertTrue((EVIDENCE_ROOT / "attempt_15").is_dir())
        attempt16 = EVIDENCE_ROOT / "attempt_16"
        self.assertTrue(attempt16.is_dir())
        started = load_json(attempt16 / "ATTEMPT_STARTED.json")
        failure = load_json(attempt16 / "FAILURE.json")
        self.assertFalse((attempt16 / "SIMULATION_REPORT.json").exists())
        self.assertEqual(
            started["worker_sha256"],
            self.config["bindings"]["reserved_attempt16_worker"]["sha256"],
        )
        self.assertEqual(
            started["config_sha256"],
            self.config["bindings"]["reserved_attempt16_config"]["sha256"],
        )
        self.assertFalse(started["blend_save_permitted"])
        self.assertEqual(
            failure["status"],
            "NO_SAVE_ATTEMPT16_FAILED_PRESERVED_FOR_DIAGNOSIS",
        )
        self.assertFalse(failure["blend_saved"])
        self.assertFalse(failure["runtime_changed"])
        self.assertFalse((EVIDENCE_ROOT / "attempt_17").exists())
        self.assertNotIn("bpy.ops.wm.save", self.source)
        self.assertNotIn("save_as_mainfile", self.source)
        self.assertNotIn("bpy.data.libraries.load", self.source)
        self.assertNotIn("qualified_cc0_foundation_blend", self.source)
        self.assertNotIn("append_donor", self.source)
        fallback = self.config["fallback_policy"]
        self.assertTrue(fallback["attempt16_has_priority"])
        self.assertEqual(
            fallback["attempt16_result"],
            "NO_SAVE_STRUCTURAL_FAILURE_BEFORE_GEOMETRY_MUTATION",
        )
        self.assertTrue(fallback["attempt16_failure_prerequisite_satisfied"])
        self.assertFalse(fallback["run_automatically_after_attempt16"])
        self.assertTrue(fallback["attempt17_requires_separate_reviewed_command"])
        self.assertTrue(fallback["attempt17_slot_reserved_before_attempt18"])
        self.assertTrue(
            fallback["attempt18_must_not_run_before_attempt17_terminal_evidence"]
        )

    def test_config_is_self_bound_and_exact_source_load_is_last(self) -> None:
        expected = sha256(CONFIG)
        self.assertIn(f'"{expected}"', self.source)
        self.assertIn('EXPECTED_ATTEMPT_SLOT = "attempt_17"', self.source)
        verify_bindings = self.source.index("verified_bindings = verify_bindings(config)")
        preserve = self.source.index("preserved_before = verify_preserved_attempts(config)")
        attempt16 = self.source.index("attempt16_runtime_before = verify_attempt16_runtime(config)")
        allocation = self.source.index("ACTIVE_OUTPUT = allocate_output(config)")
        load = self.source.index("bpy.ops.wm.open_mainfile")
        self.assertLess(verify_bindings, preserve)
        self.assertLess(preserve, attempt16)
        self.assertLess(attempt16, allocation)
        self.assertLess(allocation, load)

    def test_attempt16_static_and_future_runtime_evidence_are_bound(self) -> None:
        for name in (
            "reserved_attempt16_config",
            "reserved_attempt16_worker",
            "reserved_attempt16_static_test",
            "reserved_attempt16_proposal",
            "reserved_attempt16_checkpoint",
            "preserved_attempt16_started",
            "preserved_attempt16_append_inventory",
            "preserved_attempt16_failure",
        ):
            self.assertIn(name, self.config["bindings"])
        contract = self.config["attempt16_runtime_evidence_contract"]
        self.assertEqual(contract["directory"].split("/")[-1], "attempt_16")
        self.assertTrue(contract["exactly_one_terminal_file_required"])
        self.assertEqual(
            contract["terminal_files"], ["SIMULATION_REPORT.json", "FAILURE.json"]
        )
        for required in (
            "def verify_attempt16_runtime(",
            "Attempt 16 must have exactly one terminal evidence file",
            '"worker_hash": started.get("worker_sha256") == expected_worker',
            '"config_hash": started.get("config_sha256") == expected_config',
            '"terminal_no_save": terminal_no_save',
            '"attempt16_runtime_manifest_unchanged"',
        ):
            self.assertIn(required, self.source)

    def test_carrier_uses_only_outer_seam_and_exterior_collar(self) -> None:
        carrier = self.config["carrier"]
        self.assertEqual(
            carrier["coordinate_training_source"],
            "outer_seam_plus_two_exterior_face_collars_only",
        )
        self.assertEqual(carrier["old_patch_interior_training_samples_required"], 0)
        self.assertEqual(carrier["exterior_face_collar_rings"], 2)
        for required in (
            "def exterior_face_collar(",
            "training = collar_vertices.difference(mask_vertices).union(boundary)",
            "old_in_training = training.intersection(old_vertices)",
            "old 34-patch interior leaked into carrier training",
            "def solve_dirichlet(",
            "def robust_quadratic_fit(",
            "def solve_screened_biharmonic_depth(",
            '"training_source_only_outer_seam_or_exterior": True',
        ):
            self.assertIn(required, self.source)
        self.assertNotIn("donor_chart_coordinates", self.source)
        self.assertNotIn("mapped_position", self.source)

    def test_relief_is_shallow_and_zero_for_first_three_rings(self) -> None:
        relief = self.config["semantic_relief"]
        self.assertEqual(relief["minimum_topology_distance_from_outer_boundary"], 3)
        self.assertEqual(self.config["gates"]["relief_zero_through_topology_ring"], 2)
        self.assertLessEqual(relief["maximum_positive_relief_m"], 0.0014)
        self.assertLessEqual(relief["maximum_negative_relief_m"], 0.0007)
        self.assertLessEqual(relief["maximum_absolute_combined_relief_m"], 0.0015)
        self.assertFalse(relief["through_holes_allowed"])
        self.assertFalse(relief["separate_rim_or_overlay_geometry_allowed"])
        for field in relief["fields"]:
            self.assertLessEqual(abs(float(field["amplitude_m"])), 0.00105)
        for distance in (0, 1, 2):
            minimum = relief["minimum_topology_distance_from_outer_boundary"]
            value = 0.0 if distance < minimum else math.nan
            self.assertEqual(value, 0.0)
        self.assertIn('"relief_zero_through_ring_2"', self.source)
        self.assertIn('== 0.0', self.source)

    def test_preservation_and_intersection_gates_are_fail_closed(self) -> None:
        gates = self.config["gates"]
        self.assertEqual(gates["outside_expanded_mask_hash_mismatches"], 0)
        self.assertEqual(gates["new_topology_elements"], 0)
        self.assertEqual(gates["changed_mask_genuine_intersection_pairs"], 0)
        self.assertEqual(gates["new_whole_genuine_intersection_pairs"], 0)
        self.assertEqual(gates["whole_genuine_intersection_pairs"], 29)
        for required in (
            '"outside_and_outer_seam_freeze_ledger_exact"',
            '"mask_uv_and_weights_exact"',
            '"topology_counts_exact"',
            '"changed_mask_intersections_zero"',
            '"no_new_whole_intersection_pairs"',
            '"inherited_outside_pair_identity_exact"',
            'if not all(checks.values()):',
            '"FAILED_CLOSED_NO_SAVE"',
            '"STRUCTURAL_DIAGNOSTIC.json"',
            '"false_checks"',
        ):
            self.assertIn(required, self.source)
        fail_gate = self.source.index("if not all(checks.values()):")
        render = self.source.index("renders = render_evidence(")
        self.assertLess(fail_gate, render)

    def test_paired_unoccluded_visual_evidence_is_required(self) -> None:
        render = self.config["render"]
        self.assertEqual(
            render["paired_protected_views"],
            [
                "front",
                "left_three_quarter",
                "right_three_quarter",
                "left_profile",
                "right_profile",
                "inferior",
                "rear",
            ],
        )
        self.assertEqual(render["opposite_light_views"], ["front", "left_three_quarter"])
        self.assertIn("local_unoccluded_surface", self.source)
        self.assertIn("_no_diagnostic_subdivision.png", self.source)
        self.assertIn("_opposite_light.png", self.source)
        self.assertIn("protected_clinical_wire.png", self.source)
        self.assertIn("protected_clinical_feature_mask.png", self.source)
        self.assertIn('"manual_visual_review_required": True', self.source)

    def test_truth_boundary_does_not_overclaim_function_or_approval(self) -> None:
        truth = self.config["truth_boundary"]
        for key in (
            "visual_realism_proven_by_structural_pass",
            "bathroom_function_implemented",
            "internal_organs_implemented",
            "reproduction_or_pregnancy_implemented",
            "sensation_or_subjective_experience_implemented",
            "movement_or_pose_acceptance_run",
        ):
            self.assertFalse(truth[key], key)
        self.assertTrue(truth["owner_visual_approval_required_before_any_save"])
        proposal = PROPOSAL.read_text(encoding="utf-8")
        self.assertIn("visual component", proposal)
        self.assertIn("reject", proposal)
        self.assertIn("No Blend may be saved", proposal)


if __name__ == "__main__":
    unittest.main()
