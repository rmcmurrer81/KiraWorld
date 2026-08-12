from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROOF_DIR = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests"
    / "kira_r7_visible_lip_viseme_trial_v2_20260722"
)
EVIDENCE_PATH = PROOF_DIR / "topology_and_shape_key_evidence.json"
MANIFEST_PATH = PROOF_DIR / "manifest.json"
REOPENED_PATH = PROOF_DIR / "reopened_candidate_verification.json"
VISUAL_REVIEW_PATH = PROOF_DIR / "visual_review.json"
CANDIDATE_PATH = (
    PROOF_DIR / "inactive_candidate" / "kira_r7_visible_lip_viseme_trial_v2.blend"
)
WORKSPACE_PATH = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_adult_body_r7/workspace_v1"
    / "kira_r7_authoring_workspace.blend"
)
SOURCE_R6_PATH = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6"
    / "r6_20260718_163658/kira_provisional_body_r6.glb"
)
WORKER_PATH = PROJECT_ROOT / "tools/blender_author_kira_r7_visible_lip_visemes_v2.py"
VERIFY_WORKER_PATH = (
    PROJECT_ROOT / "tools/blender_verify_kira_r7_visible_lip_candidate_v2.py"
)

EXPECTED_PINNED_HASHES = {
    "workspace": "9d0f9dad39b2e0650419ccef48a7d524d5cd67e4429f1d23ee3398db396c0394",
    "source_r6": "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
}
EXPECTED_TOPOLOGY = {
    "vertices": 57745,
    "edges": 165776,
    "polygons": 108080,
    "objects": 4,
    "mesh_objects": 3,
}
EXPECTED_KEYS = [
    "KW_VISEME_AH_OPEN_REVIEW",
    "KW_VISEME_EE_REVIEW",
    "KW_VISEME_O_REVIEW",
    "KW_VISEME_MBP_REVIEW",
    "KW_VISEME_FV_REVIEW",
]
EXPECTED_HIDDEN_HASH = (
    "dee38f86b4bfbb732a3cbcc4ae2927f8ff50626d463dcdcfe4bca1f0b84edc3b"
)
EXPECTED_MOVED_HASH = (
    "85e1673c8f778ffc8f5750a8746255a2639ffc91f3a988227f50f716c8a1ca36"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class KiraR7VisibleLipVisemeTrialV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.reopened = json.loads(REOPENED_PATH.read_text(encoding="utf-8"))
        cls.visual = json.loads(VISUAL_REVIEW_PATH.read_text(encoding="utf-8"))

    def test_manifest_records_partial_pass_and_fail_closed_result(self) -> None:
        self.assertEqual(
            self.manifest["status"],
            "inactive_partial_visual_pass_ah_ee_o_mbp_fv_fail_closed_owner_review_pending",
        )
        result = self.manifest["result"]
        self.assertTrue(result["same_existing_welded_mouth_keys_authored"])
        self.assertFalse(result["visual_review_artifact_pending"])
        self.assertEqual(
            result["ah_open_visual_disposition"],
            "pass_distinct_for_owner_review_only",
        )
        self.assertEqual(
            result["ee_visual_disposition"],
            "pass_distinct_for_owner_review_only",
        )
        self.assertEqual(
            result["o_visual_disposition"],
            "pass_distinct_for_owner_review_only",
        )
        self.assertTrue(result["mbp_visual_disposition"].startswith("fail_closed"))
        self.assertTrue(result["fv_visual_disposition"].startswith("fail_closed"))
        self.assertFalse(result["complete_five_viseme_set_proven"])
        self.assertTrue(result["owner_visual_review_pending"])
        self.assertFalse(result["runtime_ready"])
        self.assertTrue(all(value is False for value in self.manifest["gates"].values()))

    def test_visual_review_is_bound_and_keeps_mbp_and_fv_failed_closed(self) -> None:
        artifacts = self.manifest["artifacts"]
        self.assertEqual(
            sha256_file(VISUAL_REVIEW_PATH), artifacts["visual_review_sha256"]
        )
        self.assertEqual(
            self.visual["binding"]["candidate_blend_sha256"],
            artifacts["candidate_blend_sha256"],
        )
        self.assertEqual(
            self.visual["binding"]["fixed_render_sha256"],
            artifacts["fixed_render_sha256"],
        )
        dispositions = {
            name: item["visual_disposition"]
            for name, item in self.visual["visemes"].items()
        }
        for name in EXPECTED_KEYS[:3]:
            self.assertEqual(dispositions[name], "pass_distinct_for_owner_review_only")
        self.assertEqual(
            dispositions[EXPECTED_KEYS[3]],
            "fail_closed_not_convincingly_distinct_from_basis",
        )
        self.assertEqual(
            dispositions[EXPECTED_KEYS[4]],
            "fail_closed_not_convincingly_distinct_and_no_teeth_contact_proof",
        )
        self.assertFalse(self.visual["overall"]["complete_five_viseme_set_proven"])
        self.assertFalse(self.visual["overall"]["runtime_ready"])
        self.assertFalse(self.visual["overall"]["promotion_allowed"])
        self.assertFalse(self.visual["shared_findings"]["second_mouth_visible"])
        self.assertFalse(self.visual["shared_findings"]["obvious_tearing_visible"])
        self.assertFalse(
            self.visual["shared_findings"]["teeth_or_internal_oral_system_authored"]
        )

    def test_topology_and_protected_backing_are_unchanged(self) -> None:
        topology = self.evidence["topology"]
        self.assertEqual(topology["before"], EXPECTED_TOPOLOGY)
        self.assertEqual(topology["after_shape_keys_before_save"], EXPECTED_TOPOLOGY)
        self.assertTrue(topology["unchanged"])
        backing = self.evidence["hidden_backing"]
        self.assertEqual(backing["vertex_count"], 207)
        self.assertEqual(backing["vertex_index_sha256"], EXPECTED_HIDDEN_HASH)
        self.assertFalse(backing["deformed_by_any_shape_key"])

    def test_all_five_keys_move_only_the_same_pinned_visible_region(self) -> None:
        keys = self.evidence["shape_keys"]
        self.assertEqual([entry["name"] for entry in keys], EXPECTED_KEYS)
        for entry in keys:
            self.assertEqual(entry["moved_vertex_count"], 270)
            self.assertEqual(entry["moved_vertex_index_sha256"], EXPECTED_MOVED_HASH)
            self.assertEqual(entry["hidden_backing_maximum_displacement_m"], 0.0)
            self.assertFalse(entry["visual_quality_proven_by_worker"])
        self.assertEqual(
            self.evidence["preexisting_shape_keys_preserved"],
            ["Basis", "Kira_Adult_External_Form_R6"],
        )

    def test_saved_candidate_reopens_inactive_with_zeroed_review_keys(self) -> None:
        self.assertTrue(self.reopened["topology_matches_pinned_r7"])
        self.assertEqual(self.reopened["topology"], EXPECTED_TOPOLOGY)
        self.assertEqual(
            self.reopened["shape_key_names"],
            ["Basis", "Kira_Adult_External_Form_R6", *EXPECTED_KEYS],
        )
        for entry in self.reopened["shape_keys"]:
            self.assertEqual(entry["value_on_reopen"], 0.0)
            self.assertEqual(entry["moved_vertex_count"], 270)
            self.assertEqual(entry["moved_vertex_index_sha256"], EXPECTED_MOVED_HASH)
            self.assertEqual(entry["hidden_backing_maximum_displacement_m"], 0.0)
        policy = self.reopened["saved_candidate_policy"]
        self.assertTrue(policy["inactive_owner_review_only"])
        self.assertEqual(policy["version"], "r7_visible_lip_viseme_v2")
        self.assertFalse(policy["second_mouth_created"])
        self.assertFalse(policy["runtime_export_allowed"])
        self.assertTrue(all(value is False for value in self.reopened["safety"].values()))

    def test_guarded_sources_and_runtime_state_remained_byte_unchanged(self) -> None:
        verification = self.evidence["host_verification"]
        self.assertEqual(verification["pinned_hashes_before"], EXPECTED_PINNED_HASHES)
        self.assertEqual(verification["pinned_hashes_after"], EXPECTED_PINNED_HASHES)
        self.assertEqual(
            verification["runtime_state_sha256_before"],
            verification["runtime_state_sha256_after"],
        )
        self.assertTrue(verification["all_guarded_inputs_byte_unchanged"])
        self.assertTrue(self.manifest["guarded_inputs_byte_unchanged"])
        self.assertEqual(sha256_file(WORKSPACE_PATH), EXPECTED_PINNED_HASHES["workspace"])
        self.assertEqual(sha256_file(SOURCE_R6_PATH), EXPECTED_PINNED_HASHES["source_r6"])
        safety = self.evidence["safety"]
        self.assertTrue(safety["isolated_candidate_saved"])
        for key in (
            "source_workspace_saved_or_overwritten",
            "second_mouth_created",
            "mesh_object_added_to_saved_candidate",
            "vertex_or_face_topology_changed",
            "runtime_model_exported",
            "runtime_binding_touched",
            "person_state_touched",
            "activation_attempted",
        ):
            self.assertFalse(safety[key])

    def test_candidate_evidence_and_fixed_renders_match_manifest(self) -> None:
        artifacts = self.manifest["artifacts"]
        self.assertTrue(CANDIDATE_PATH.is_file())
        self.assertEqual(sha256_file(CANDIDATE_PATH), artifacts["candidate_blend_sha256"])
        self.assertEqual(sha256_file(EVIDENCE_PATH), artifacts["evidence_sha256"])
        self.assertEqual(
            sha256_file(REOPENED_PATH),
            artifacts["reopened_candidate_verification_sha256"],
        )
        render_names = {
            "basis_face": "basis_front_face.png",
            "basis_mouth": "basis_mouth_closeup.png",
            "ah_open_mouth": "ah_open_mouth_closeup.png",
            "ah_open_oblique": "ah_open_oblique.png",
            "ee_mouth": "ee_mouth_closeup.png",
            "ee_oblique": "ee_oblique.png",
            "o_mouth": "o_mouth_closeup.png",
            "o_oblique": "o_oblique.png",
            "mbp_mouth": "mbp_mouth_closeup.png",
            "mbp_oblique": "mbp_oblique.png",
            "fv_mouth": "fv_mouth_closeup.png",
            "fv_oblique": "fv_oblique.png",
        }
        for key, filename in render_names.items():
            render_path = PROOF_DIR / "fixed_renders" / filename
            self.assertTrue(render_path.is_file())
            self.assertGreater(render_path.stat().st_size, 0)
            self.assertEqual(
                sha256_file(render_path), artifacts["fixed_render_sha256"][key]
            )
        for key in ("ah_open_mouth", "ee_mouth", "o_mouth"):
            self.assertNotEqual(
                artifacts["fixed_render_sha256"]["basis_mouth"],
                artifacts["fixed_render_sha256"][key],
            )
        self.assertEqual(list(PROOF_DIR.rglob("*.glb")), [])

    def test_blender_workers_contain_no_export_or_runtime_binding_api(self) -> None:
        for path in (WORKER_PATH, VERIFY_WORKER_PATH):
            source = path.read_text(encoding="utf-8")
            for forbidden in (
                "bpy.ops.export_scene.gltf",
                "runtime_body_selection",
                "kira_world_shell_state",
            ):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
