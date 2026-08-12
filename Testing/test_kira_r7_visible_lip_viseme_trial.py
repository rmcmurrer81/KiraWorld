from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROOF_DIR = (
    PROJECT_ROOT
    / "Data/avatar_builder_workspace_tests"
    / "kira_r7_visible_lip_viseme_trial_20260722"
)
EVIDENCE_PATH = PROOF_DIR / "topology_and_shape_key_evidence.json"
MANIFEST_PATH = PROOF_DIR / "manifest.json"
REOPENED_PATH = PROOF_DIR / "reopened_candidate_verification.json"
CANDIDATE_PATH = (
    PROOF_DIR / "inactive_candidate" / "kira_r7_visible_lip_viseme_trial.blend"
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
WORKER_PATH = PROJECT_ROOT / "tools/blender_author_kira_r7_visible_lip_visemes.py"
VERIFY_WORKER_PATH = PROJECT_ROOT / "tools/blender_verify_kira_r7_visible_lip_candidate.py"

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
EXPECTED_PATH_EDGE_HASHES = {
    "upper_right": "f877fece76f77301b4a85b99b2b23065b80efa8ce851c38ede1cec6670d2074f",
    "upper_left": "35708fd61a3c61b0247f399eeca77ed299c1c924a1847c14f10e33d6004cee25",
    "lower_right": "b5fe710470e1fb8383315b5b1eb0f6540de517dc5eab9c621603dbbbbf92a006",
    "lower_left": "1028c64110ab47da89e1a427e4b362396f79c8f032105c8a269cefb4c0354e83",
}
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


class KiraR7VisibleLipVisemeTrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.reopened = json.loads(REOPENED_PATH.read_text(encoding="utf-8"))

    def test_manifest_is_inactive_owner_review_only(self) -> None:
        self.assertEqual(
            self.manifest["status"],
            "inactive_same_mesh_visible_motion_engineering_pass_owner_review_pending",
        )
        result = self.manifest["result"]
        self.assertTrue(result["same_existing_face_mesh_shape_keys_authored"])
        self.assertTrue(result["visible_open_shape_proven"])
        self.assertFalse(result["o_viseme_final_quality_proven"])
        self.assertEqual(
            result["o_viseme_disposition"],
            "provisional_shape_not_visually_distinct_enough_for_final_o",
        )
        self.assertFalse(result["second_mouth_created"])
        self.assertFalse(result["hidden_backing_deformed"])
        self.assertFalse(result["topology_changed"])
        self.assertFalse(result["runtime_or_live_body_changed"])
        self.assertTrue(result["owner_visual_review_pending"])
        self.assertTrue(all(value is False for value in self.manifest["gates"].values()))

    def test_topology_and_existing_backing_are_unchanged(self) -> None:
        topology = self.evidence["topology"]
        self.assertEqual(topology["before"], EXPECTED_TOPOLOGY)
        self.assertEqual(topology["after_shape_keys_before_save"], EXPECTED_TOPOLOGY)
        self.assertTrue(topology["unchanged"])
        backing = self.evidence["hidden_backing"]
        self.assertEqual(backing["vertex_count"], 207)
        self.assertEqual(backing["vertex_index_sha256"], EXPECTED_HIDDEN_HASH)
        self.assertFalse(backing["deformed_by_any_shape_key"])

    def test_visible_lip_rim_selection_is_pinned_and_separate(self) -> None:
        proof = self.evidence["visible_lip_rim_proof"]
        self.assertEqual(proof["path_edge_sha256"], EXPECTED_PATH_EDGE_HASHES)
        self.assertEqual(proof["visible_rim_vertex_count"], 58)
        self.assertEqual(
            proof["visible_rim_vertex_index_sha256"],
            "37deb01f27e3ad2cdf839bafabf0e9faf4a662b4e55586abb41b2bf574088240",
        )
        self.assertFalse(proof["overlaps_hidden_backing"])
        self.assertTrue(
            proof["all_consecutive_path_edges_are_single_use_mesh_boundaries"]
        )
        self.assertGreaterEqual(proof["upper_min_negative_normal_z"], 0.73)
        self.assertGreaterEqual(proof["lower_min_positive_normal_z"], 0.94)

    def test_same_mesh_trial_keys_are_measured_and_o_remains_provisional(self) -> None:
        keys = {entry["name"]: entry for entry in self.evidence["shape_keys"]}
        self.assertEqual(
            set(keys), {"KW_VISIBLE_LIP_OPEN_REVIEW", "KW_VISEME_O_REVIEW"}
        )
        for entry in keys.values():
            self.assertEqual(entry["moved_vertex_count"], 270)
            self.assertEqual(entry["moved_vertex_index_sha256"], EXPECTED_MOVED_HASH)
            self.assertEqual(entry["hidden_backing_maximum_displacement_m"], 0.0)
        self.assertEqual(
            keys["KW_VISIBLE_LIP_OPEN_REVIEW"]["review_disposition"],
            "visible_same_mesh_open_shape_engineering_proof_owner_review_pending",
        )
        self.assertEqual(
            keys["KW_VISEME_O_REVIEW"]["review_disposition"],
            "provisional_shape_not_visually_distinct_enough_for_final_o",
        )
        self.assertEqual(
            self.evidence["preexisting_shape_keys_preserved"],
            ["Basis", "Kira_Adult_External_Form_R6"],
        )
        separation = self.evidence["center_separation"]
        open_delta = (
            separation["KW_VISIBLE_LIP_OPEN_REVIEW"]["vertical_separation_m"]
            - separation["Basis"]["vertical_separation_m"]
        )
        self.assertGreaterEqual(open_delta, 0.045)

    def test_saved_candidate_reopens_with_zeroed_review_keys(self) -> None:
        self.assertTrue(self.reopened["topology_matches_pinned_r7"])
        self.assertEqual(self.reopened["topology"], EXPECTED_TOPOLOGY)
        self.assertEqual(
            self.reopened["shape_key_names"],
            [
                "Basis",
                "Kira_Adult_External_Form_R6",
                "KW_VISIBLE_LIP_OPEN_REVIEW",
                "KW_VISEME_O_REVIEW",
            ],
        )
        for entry in self.reopened["shape_keys"]:
            self.assertEqual(entry["value_on_reopen"], 0.0)
            self.assertEqual(entry["moved_vertex_count"], 270)
            self.assertEqual(entry["moved_vertex_index_sha256"], EXPECTED_MOVED_HASH)
            self.assertEqual(entry["hidden_backing_maximum_displacement_m"], 0.0)
        self.assertEqual(self.reopened["hidden_backing"]["vertex_count"], 207)
        self.assertEqual(
            self.reopened["hidden_backing"]["vertex_index_sha256"],
            EXPECTED_HIDDEN_HASH,
        )
        self.assertTrue(
            self.reopened["hidden_backing"]["unchanged_in_every_trial_key"]
        )
        self.assertEqual(
            self.reopened["saved_candidate_policy"],
            {
                "inactive_owner_review_only": True,
                "second_mouth_created": False,
                "runtime_export_allowed": False,
            },
        )
        self.assertTrue(
            all(value is False for value in self.reopened["safety"].values())
        )

    def test_guarded_sources_and_runtime_state_remained_unchanged(self) -> None:
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
        self.assertFalse(safety["source_workspace_saved_or_overwritten"])
        self.assertTrue(safety["isolated_candidate_saved"])
        for key in (
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
            "open_face": "open_front_face.png",
            "basis_mouth": "basis_mouth_closeup.png",
            "open_mouth": "open_mouth_closeup.png",
            "round_mouth": "viseme_o_mouth_closeup.png",
            "open_oblique": "open_oblique.png",
        }
        for key, filename in render_names.items():
            render_path = PROOF_DIR / "fixed_renders" / filename
            self.assertTrue(render_path.is_file())
            self.assertGreater(render_path.stat().st_size, 0)
            self.assertEqual(
                sha256_file(render_path), artifacts["fixed_render_sha256"][key]
            )
        self.assertNotEqual(
            artifacts["fixed_render_sha256"]["basis_mouth"],
            artifacts["fixed_render_sha256"]["open_mouth"],
        )
        self.assertEqual(list(PROOF_DIR.rglob("*.glb")), [])

    def test_workers_have_no_model_export_or_runtime_binding_api(self) -> None:
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
