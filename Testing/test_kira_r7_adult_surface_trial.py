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
    / "rest_preserving_weight_transfer_r2"
)
EVIDENCE_PATH = PROOF_DIR / "evidence.json"
MANIFEST_PATH = PROOF_DIR / "manifest.json"
REVIEW_BLEND = PROOF_DIR / "inactive_body_surface_trial.blend"
REPORT_PATH = PROJECT_ROOT / "Data/codex_reports/20260722_kira_r7_adult_surface_trial.md"
KIRA_SOURCE = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6"
    / "r6_20260718_163658/kira_provisional_body_r6.glb"
)
REFERENCE_SOURCE = Path(r"C:\Users\robmc\Desktop\5\base_female_character.glb")
NECK_EVIDENCE = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests"
    / "kira_r7_neck_boundary_owner_review_20260721/evidence.json"
)
WORKER = PROJECT_ROOT / "tools/blender_author_kira_r7_adult_surface_trial.py"
EXPECTED_HASHES = {
    "kira_r6": "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
    "adult_reference": "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df",
    "neck_evidence": "f0c4d0eb9e58a42a3ff156d22aa9b66a64210354bc924abe7f2d106d14ceeace",
}
RENDER_NAMES = {
    "neutral_front",
    "neutral_back",
    "neutral_left",
    "neutral_right",
    "identity_overlay_front",
    "identity_overlay_side",
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


class KiraR7AdultSurfaceTrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_result_is_explicitly_rejected_and_cannot_go_live(self) -> None:
        expected = (
            "rejected_identity_seam_and_complete_adult_topology_not_proven_no_candidate"
        )
        self.assertEqual(self.evidence["decision"]["status"], expected)
        self.assertEqual(self.manifest["status"], expected)
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
            "identity_head_joined",
        ):
            self.assertFalse(self.manifest[key], key)
        self.assertEqual(list(PROOF_DIR.rglob("*.glb")), [])

    def test_corrected_landmark_uses_body_floor_not_helper_primitives(self) -> None:
        correction = self.evidence["landmark_correction"]
        self.assertIn("hip_03", correction["rejected_old_landmark"])
        self.assertEqual(correction["correct_anatomical_pelvis"], "pelvis_04")
        self.assertEqual(correction["kira_floor_landmark_mesh"], "Cuerpo__0")
        self.assertEqual(correction["kira_floor_landmark_vertex_count"], 57745)
        self.assertEqual(
            correction["excluded_kira_helper_meshes_from_floor_landmark"],
            ["Icosphere"],
        )
        self.assertAlmostEqual(correction["upper_body_scale"], 0.702299572, places=8)
        self.assertAlmostEqual(correction["lower_body_scale"], 0.670012515, places=8)
        self.assertGreater(correction["lower_body_scale"], 0.60)
        self.assertLess(correction["lower_body_scale"], 0.75)

    def test_authoring_uses_only_attributed_external_form_and_original_tone(self) -> None:
        authored = self.evidence["surface_authoring"]
        self.assertEqual(
            set(authored["source_meshes"]),
            {
                "Ariel_Mesh_Torso_0",
                "Ariel_Mesh_Arms_0",
                "Ariel_Mesh_Legs_0",
                "Ariel_Mesh_Fingernails_0",
                "Ariel_Mesh_Toenails_0",
                "Ariel_Mesh_Genitalia_0",
            },
        )
        self.assertEqual(authored["skin_tone"]["srgb_hex"], "#e6c0a9")
        self.assertEqual(
            authored["skin_tone"]["contract"],
            "pre_r6_live_light_untextured_v1",
        )
        self.assertFalse(authored["source_materials_or_textures_copied"])
        self.assertTrue(authored["reference_head_shell_removed"])
        self.assertTrue(authored["exact_kira_r6_head_overlay_created"])
        self.assertFalse(authored["exact_kira_r6_head_overlay_fused"])
        excluded = " ".join(authored["identity_bearing_source_meshes_excluded"]).lower()
        for token in ("face", "eye", "mouth", "lip"):
            self.assertIn(token, excluded)

    def test_topology_and_weights_are_measured_but_not_adult_identity_proof(self) -> None:
        topology = self.evidence["topology"]
        self.assertEqual(topology["connected_components"], 1)
        self.assertEqual(topology["boundary_connected_parts"], 1)
        self.assertEqual(topology["boundary_closed_cycle_count"], 1)
        self.assertEqual(topology["overused_edge_count"], 0)
        self.assertEqual(topology["degenerate_face_count_under_1e_12_m2"], 0)
        weights = self.evidence["weights"]
        self.assertEqual(weights["unweighted_vertex_count"], 0)
        self.assertLessEqual(weights["maximum_positive_groups_per_vertex"], 4)
        self.assertEqual(weights["invalid_target_groups"], [])
        gates = self.evidence["gates"]
        self.assertTrue(gates["cohesive_body_surface_topology_passed"])
        self.assertTrue(gates["exact_79_joint_weight_transfer_passed"])
        self.assertFalse(gates["stable_fixed_pose_deformation_passed"])
        self.assertFalse(gates["identity_head_preserved_and_joined"])
        self.assertFalse(gates["complete_adult_topology_proven"])
        self.assertFalse(self.evidence["pose_gate_results"]["bilateral_squat"])

    def test_pinned_sources_and_inactive_runtime_were_byte_unchanged(self) -> None:
        verification = self.evidence["host_verification"]
        self.assertEqual(verification["pinned_hashes_before"], EXPECTED_HASHES)
        self.assertEqual(verification["pinned_hashes_after"], EXPECTED_HASHES)
        self.assertTrue(verification["all_guarded_inputs_byte_unchanged"])
        self.assertEqual(
            verification["runtime_state_before"], verification["runtime_state_after"]
        )
        self.assertEqual(verification["runtime_state_before"]["active_candidate"], "")
        self.assertEqual(sha256_file(KIRA_SOURCE), EXPECTED_HASHES["kira_r6"])
        self.assertEqual(sha256_file(REFERENCE_SOURCE), EXPECTED_HASHES["adult_reference"])
        self.assertEqual(sha256_file(NECK_EVIDENCE), EXPECTED_HASHES["neck_evidence"])

    def test_fixed_renders_blend_and_manifest_hashes_are_sealed(self) -> None:
        self.assertTrue(REVIEW_BLEND.is_file())
        artifacts = self.manifest["artifacts"]
        self.assertEqual(
            sha256_file(REVIEW_BLEND), artifacts["inactive_review_blend_sha256"]
        )
        self.assertEqual(sha256_file(EVIDENCE_PATH), artifacts["evidence_sha256"])
        self.assertEqual(set(artifacts["fixed_renders"]), RENDER_NAMES)
        for name, record in artifacts["fixed_renders"].items():
            path = PROJECT_ROOT / record["path"]
            self.assertTrue(path.is_file(), name)
            self.assertGreater(path.stat().st_size, 200_000, name)
            self.assertEqual(sha256_file(path), record["sha256"], name)
        self.assertNotEqual(
            artifacts["fixed_renders"]["neutral_front"]["sha256"],
            artifacts["fixed_renders"]["pose_upper_limb"]["sha256"],
        )

    def test_report_and_worker_preserve_fail_closed_truth(self) -> None:
        report = REPORT_PATH.read_text(encoding="utf-8")
        self.assertIn("Rejected, with no candidate, no live binding, and no promotion", report)
        self.assertIn("no defensible existing closed neck ring", report)
        self.assertIn("rest_preserving_weight_transfer_r2", report)
        source = WORKER.read_text(encoding="utf-8")
        for forbidden in (
            "bpy.ops.export_scene.gltf",
            "runtime_body_selection",
            "kira_world_shell_state",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
