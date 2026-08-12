from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROOF_DIR = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests"
    / "kira_r7_adult_surface_trial_20260722"
    / "measured_neck_bridge_r3"
)
EVIDENCE_PATH = PROOF_DIR / "evidence.json"
MANIFEST_PATH = PROOF_DIR / "manifest.json"
REVIEW_BLEND = PROOF_DIR / "inactive_measured_neck_bridge_r3.blend"
REPORT_PATH = PROJECT_ROOT / "Data/codex_reports/20260722_kira_r7_adult_surface_r3.md"
EXPECTED_STATUS = (
    "rejected_complete_adult_topology_and_owner_visual_approval_not_proven_no_candidate"
)
EXPECTED_RENDERS = {
    "neutral_front",
    "neutral_back",
    "neutral_left",
    "neutral_right",
    "neck_closeup_front",
    "neck_closeup_left",
    "neck_closeup_right",
    "identity_front",
    "identity_left_profile",
    "identity_mouth_closeup",
    "pose_upper_limb",
    "pose_hip_knee",
    "pose_spine",
    "pose_bilateral_squat",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class KiraR7AdultSurfaceR3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_result_is_rejected_and_cannot_reach_runtime(self) -> None:
        self.assertEqual(self.evidence["decision"]["status"], EXPECTED_STATUS)
        self.assertEqual(self.manifest["status"], EXPECTED_STATUS)
        for key in (
            "candidate_glb_created",
            "candidate_export_allowed",
            "avatar_builder_binding_changed",
            "avatar_builder_promotion_allowed",
            "live_body_changed",
            "runtime_state_changed",
            "runtime_activation_allowed",
            "owner_approved",
            "complete_adult_topology_proven",
        ):
            self.assertFalse(self.manifest[key], key)
        self.assertEqual(list(PROOF_DIR.rglob("*.glb")), [])

    def test_measured_bridge_and_identity_values_are_sealed(self) -> None:
        rings = self.evidence["measured_rings"]
        self.assertEqual(rings["body"]["vertex_count"], 76)
        self.assertEqual(rings["head"]["vertex_count"], 154)
        bridge = self.evidence["bridge"]
        self.assertEqual(bridge["bridge_triangles"], 230)
        self.assertEqual(
            bridge["bridge_triangles"], bridge["expected_bridge_triangles"]
        )
        identity = self.evidence["identity_preservation"]
        self.assertEqual(identity["retained_exact_r6_head_maximum_coordinate_delta_m"], 0.0)
        self.assertEqual(
            identity["head_coordinate_digest_before"],
            identity["head_coordinate_digest_after"],
        )
        self.assertFalse(identity["face_and_mouth_vertices_smoothed_or_moved"])

    def test_engineering_checks_do_not_override_failed_visual_gate(self) -> None:
        topology = self.evidence["topology"]
        self.assertEqual(topology["connected_components"], 1)
        self.assertEqual(topology["boundary_closed_cycle_count"], 3)
        self.assertEqual(topology["overused_edge_count"], 0)
        self.assertEqual(topology["degenerate_face_count_under_1e_12_m2"], 0)
        weights = self.evidence["weights"]
        self.assertEqual(weights["defined_vertex_group_count"], 79)
        self.assertEqual(weights["unweighted_vertex_count"], 0)
        self.assertLessEqual(weights["maximum_positive_groups_per_vertex"], 4)
        self.assertTrue(all(self.evidence["pose_gate_results"].values()))
        gates = self.evidence["gates"]
        self.assertTrue(gates["engineering_measured_neck_bridge_passed"])
        self.assertFalse(gates["neutral_neck_identity_squat_visual_review_passed"])
        self.assertFalse(gates["complete_adult_topology_proven"])
        self.assertFalse(gates["owner_visual_review_approved"])

    def test_visual_rejection_names_the_observed_neck_defects(self) -> None:
        visual = self.evidence["owner_visual_review"]
        self.assertFalse(visual["passed"])
        findings = " ".join(visual["blocking_findings"]).lower()
        for required in ("horizontal seam", "cylindrical collar", "abrupt"):
            self.assertIn(required, findings)
        manifest_findings = " ".join(
            self.manifest["visual_review"]["blocking_findings"]
        ).lower()
        self.assertIn("collar/tube", manifest_findings)

    def test_artifacts_and_fixed_renders_match_manifest_hashes(self) -> None:
        artifacts = self.manifest["artifacts"]
        self.assertTrue(REVIEW_BLEND.is_file())
        self.assertEqual(
            sha256_file(REVIEW_BLEND), artifacts["inactive_review_blend_sha256"]
        )
        self.assertEqual(sha256_file(EVIDENCE_PATH), artifacts["evidence_sha256"])
        self.assertEqual(set(artifacts["fixed_renders"]), EXPECTED_RENDERS)
        for name, record in artifacts["fixed_renders"].items():
            path = PROJECT_ROOT / record["path"]
            self.assertTrue(path.is_file(), name)
            self.assertGreater(path.stat().st_size, 200_000, name)
            self.assertEqual(sha256_file(path), record["sha256"], name)

    def test_runtime_and_parent_artifacts_remained_unchanged(self) -> None:
        host = self.evidence["host_verification"]
        self.assertEqual(host["parent_hashes_before"], host["parent_hashes_after"])
        self.assertEqual(host["runtime_state_before"], host["runtime_state_after"])
        self.assertEqual(host["runtime_state_after"]["active_candidate"], "")
        self.assertEqual(host["runtime_state_after"]["active_conversation_mode"], "")
        self.assertTrue(host["all_guarded_inputs_and_runtime_byte_unchanged"])

    def test_report_preserves_the_visual_failure_and_truth_limits(self) -> None:
        report = REPORT_PATH.read_text(encoding="utf-8")
        for required in (
            "Original-resolution visual review **failed**",
            "cylindrical collar or tube",
            "must not be exported, bound, activated, promoted, or used for autobuild",
            "Complete adult topology proven: `False`",
            "No GLB was created",
        ):
            self.assertIn(required, report)


if __name__ == "__main__":
    unittest.main()
