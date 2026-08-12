from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEW_ROOT = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_r7_socket_eye_fit"
    / "review_20260722_v1"
)
EVIDENCE_PATH = REVIEW_ROOT / "evidence.json"
MAIN_JS = (
    PROJECT_ROOT
    / "Data/world_builds/notebook_worlds/home_world/builds"
    / "home_world_main_house_20260630_223000/preview/src/main.js"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class KiraR7SocketEyeFitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    def test_candidate_is_explicitly_inactive_and_rejected(self) -> None:
        self.assertEqual(self.evidence["candidate_id"], "kira_r7_socket_eye_v1")
        self.assertEqual(self.evidence["status"], "rejected_visual_fit")
        self.assertFalse(self.evidence["promotion_allowed"])
        self.assertIn("inactive_eye_only", self.evidence["kind"])

    def test_immutable_r6_and_live_inputs_are_byte_unchanged(self) -> None:
        self.assertEqual(self.evidence["hashes_before"], self.evidence["hashes_after"])
        for key, record in self.evidence["sources"].items():
            path = PROJECT_ROOT / record["path"]
            self.assertEqual(sha256_file(path), record["sha256"], key)
        self.assertTrue(self.evidence["structural_checks"]["source_and_live_files_unchanged"])

    def test_eye_only_contract_is_structurally_complete(self) -> None:
        checks = self.evidence["structural_checks"]
        self.assertTrue(checks["all_required_nodes_present"])
        self.assertTrue(checks["exactly_two_sclera_nodes"])
        self.assertTrue(checks["four_blink_morphs_present"])
        self.assertTrue(checks["candidate_is_separate_eye_only_glb"])
        candidate = self.evidence["candidate"]
        candidate_path = PROJECT_ROOT / candidate["path"]
        self.assertEqual(
            candidate_path,
            REVIEW_ROOT / "kira_r7_socket_eye_v1.glb",
        )
        self.assertEqual(candidate["sha256"], sha256_file(candidate_path))
        self.assertEqual(
            candidate["sha256"],
            "cba8fe60b434a4bb3658ef40758b2943142eac0319627ec3be85ae30358a26b1",
        )

    def test_fixed_review_set_is_complete_and_hash_valid(self) -> None:
        expected = {
            "neutral_front",
            "neutral_left_30deg",
            "neutral_right_30deg",
            "neutral_left_profile",
            "neutral_right_profile",
            "blink_closed_front",
            "gaze_left_front",
            "gaze_right_front",
            "gaze_up_front",
            "gaze_down_front",
        }
        renders = self.evidence["fixed_renders"]
        self.assertEqual(set(renders), expected)
        for name, record in renders.items():
            path = PROJECT_ROOT / record["path"]
            self.assertTrue(path.is_file(), name)
            self.assertGreater(record["bytes"], 100_000, name)
            self.assertEqual(sha256_file(path), record["sha256"], name)

    def test_visual_verdict_retains_proven_findings_but_fails_closed(self) -> None:
        visual = self.evidence["visual_acceptance"]
        for key in (
            "both_irises_centered_and_visible_front",
            "both_irises_visible_left_30deg",
            "both_irises_visible_right_30deg",
            "no_protrusion_left_profile",
            "no_protrusion_right_profile",
            "plausible_left_right_up_down_gaze",
        ):
            self.assertTrue(visual[key], key)
        self.assertFalse(visual["plausible_closed_blink"])
        self.assertFalse(visual["realistic_brown_iris_material_not_flat_or_mechanical"])
        self.assertFalse(visual["visual_fit_passed"])
        self.assertFalse(visual["promotion_allowed"])

    def test_home_world_has_no_r7_candidate_reference(self) -> None:
        main_js = MAIN_JS.read_text(encoding="utf-8")
        self.assertNotIn("kira_r7_socket_eye_v1", main_js)
        self.assertNotIn("kira_r7_socket_eye_fit", main_js)


if __name__ == "__main__":
    unittest.main()
