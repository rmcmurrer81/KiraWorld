import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ATTEMPT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_r24_internal_midpoint_fair_surface"
    / "attempt_36"
)
TRACE = ATTEMPT / "CDT_QUALITY_TRACE.json"
FAILURE = ATTEMPT / "FAILURE.json"
INTEGRITY = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260808"
    / "attempt36_external_pre_post_integrity.json"
)
PROPOSAL = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_r24_internal_midpoint_fair_surface"
    / "PREFLIGHT"
    / "ATTEMPT_37_NONDEGRADING_CDT_CANDIDATE_PROPOSAL.md"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Attempt36RuntimeAnalysisStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.trace = json.loads(TRACE.read_text(encoding="utf-8"))
        cls.failure = json.loads(FAILURE.read_text(encoding="utf-8"))
        cls.integrity = json.loads(INTEGRITY.read_text(encoding="utf-8"))
        cls.proposal = PROPOSAL.read_text(encoding="utf-8")

    def test_runtime_evidence_is_exactly_bound(self) -> None:
        self.assertEqual(
            sha256(TRACE),
            "8f4c93d88dbc6b385f65aefc7f900d2297b31955cc61c7bb3d1be5337e5f86fb",
        )
        self.assertEqual(
            sha256(FAILURE),
            "e5d29049c19a4d733e4bcae7ace3e7017f6ede44f2dc35741792327c6eb398f4",
        )
        self.assertEqual(
            sha256(INTEGRITY),
            "7daccc6dc4c39a0ae4c68e317b1db841abc6ea66cdb1c5bb7945728a62de7308",
        )

    def test_instrumentation_was_identity_observation(self) -> None:
        instrument = self.trace["instrumentation"]
        self.assertEqual(instrument["wrapped_callable"], "attempt15.run_cdt")
        self.assertEqual(instrument["original_call_count_per_wrapper_call"], 1)
        self.assertTrue(instrument["returns_exact_original_result"])
        self.assertFalse(instrument["mutates_inputs_or_result"])
        self.assertFalse(instrument["changes_refinement_decisions"])

    def test_terminal_failure_is_the_unchanged_quality_failure(self) -> None:
        expected = (
            "quality_refined_cdt_failed_minimum_angle:"
            "achieved=0.0:required=12.0:seeds=160"
        )
        self.assertEqual(self.trace["error"], expected)
        self.assertEqual(self.failure["error"], expected)
        self.assertEqual(self.trace["call_count"], 124)
        self.assertEqual(len(self.trace["calls"]), 124)

    def test_first_zero_angle_appears_at_call_nine(self) -> None:
        zero_calls = [
            item
            for item in self.trace["calls"]
            if item["minimum_triangle_angle_degrees"] == 0.0
            or item["zero_angle_face_count"] > 0
        ]
        self.assertEqual(zero_calls[0]["call_index"], 9)
        self.assertEqual(zero_calls[0]["seed_count"], 46)
        self.assertEqual(zero_calls[0]["zero_angle_face_count"], 1)

    def test_early_incenter_sequence_strictly_degrades(self) -> None:
        calls = self.trace["calls"]
        angles = [calls[index]["minimum_triangle_angle_degrees"] for index in range(1, 10)]
        edges = [calls[index]["minimum_edge_length_m"] for index in range(1, 10)]
        self.assertTrue(all(first > second for first, second in zip(angles, angles[1:])))
        self.assertTrue(all(first > second for first, second in zip(edges, edges[1:])))
        for index in range(2, 10):
            self.assertEqual(
                calls[index]["new_seeds"][0]["classification"],
                "WORST_FACE_INCENTER",
            )
        self.assertAlmostEqual(angles[0], 2.6350737482994022)
        self.assertEqual(angles[-1], 0.0)

    def test_no_exact_duplicate_or_boundary_motion_explains_failure(self) -> None:
        for item in self.trace["calls"]:
            self.assertEqual(item["seed_duplicate_groups"], [])
            self.assertEqual(item["output_duplicate_coordinate_groups"], [])
            self.assertEqual(
                item["output_coordinate_count"],
                item["output_unique_rounded_14_coordinate_count"],
            )
            self.assertEqual(item["maximum_boundary_delta_2d_m"], 0.0)

    def test_final_trace_records_numerical_collapse(self) -> None:
        final = self.trace["final_call"]
        self.assertEqual(final["call_index"], 123)
        self.assertEqual(final["seed_count"], 160)
        self.assertEqual(final["minimum_triangle_angle_degrees"], 0.0)
        self.assertEqual(final["zero_angle_face_count"], 12)
        self.assertLess(final["minimum_edge_length_m"], 3.0e-11)
        self.assertLess(final["minimum_absolute_double_area_m2"], 4.0e-21)

    def test_external_integrity_and_no_save_boundaries_hold(self) -> None:
        self.assertEqual(self.integrity["blender_exit_code"], 1)
        self.assertIsNone(self.integrity["native_invocation_error"])
        self.assertTrue(self.integrity["pre_post_exact"])
        self.assertEqual(len(self.integrity["before"]), 216)
        self.assertEqual(len(self.integrity["after"]), 216)
        self.assertFalse(self.failure["blend_saved"])
        self.assertFalse(self.failure["render_reached"])
        self.assertFalse(self.failure["runtime_changed"])

    def test_next_proposal_is_static_and_preserves_hard_gates(self) -> None:
        required = (
            "static proposal only",
            "does not authorize or launch Blender",
            "Remove `triangle_incenter(points)`",
            "12-degree minimum-angle gate",
            "160-interior-vertex cap",
            "no-render, no-save",
            "No runtime attempt is authorized by this proposal.",
        )
        for value in required:
            self.assertIn(value, self.proposal)
        protected_actions = (
            "lower a\n   gate",
            "raise the seed cap",
            "silently return a sub-gate mesh",
        )
        for value in protected_actions:
            self.assertIn(value, self.proposal)


if __name__ == "__main__":
    unittest.main()
