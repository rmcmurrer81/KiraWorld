from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEW_ROOT = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_r7_socket_eye_fit"
    / "review_20260722_v2"
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


def record_path(record: dict[str, object]) -> Path:
    path = Path(str(record["path"]))
    return path if path.is_absolute() else PROJECT_ROOT / path


class KiraR7SocketEyeFitV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    def test_candidate_is_inactive_rejected_and_not_promotable(self) -> None:
        self.assertEqual(self.evidence["candidate_id"], "kira_r7_socket_eye_v2")
        self.assertEqual(self.evidence["status"], "rejected_visual_fit")
        self.assertFalse(self.evidence["promotion_allowed"])
        self.assertIn("inactive_eye_only", self.evidence["kind"])
        self.assertTrue((REVIEW_ROOT / "DO_NOT_PROMOTE_REJECTED.md").is_file())

    def test_protected_sources_remain_byte_identical(self) -> None:
        self.assertEqual(self.evidence["hashes_before"], self.evidence["hashes_after"])
        for key, record in self.evidence["sources"].items():
            path = record_path(record)
            self.assertEqual(sha256_file(path), record["sha256"], key)
        self.assertTrue(self.evidence["structural_checks"]["source_and_live_files_unchanged"])

    def test_eye_only_structure_and_candidate_hash(self) -> None:
        checks = self.evidence["structural_checks"]
        for key in (
            "all_required_nodes_present",
            "exactly_two_sclera_nodes",
            "exactly_two_iris_nodes",
            "exactly_two_cornea_nodes",
            "no_fake_insert_lid_nodes",
            "blink_explicitly_unsupported",
            "source_derived_texture_hashes_match",
            "candidate_is_separate_eye_only_glb",
            "r6_body_context_not_exported",
        ):
            self.assertTrue(checks[key], key)
        candidate = self.evidence["candidate"]
        candidate_path = record_path(candidate)
        self.assertEqual(candidate_path, REVIEW_ROOT / "kira_r7_socket_eye_v2.glb")
        self.assertEqual(sha256_file(candidate_path), candidate["sha256"])

    def test_derived_texture_and_render_hashes_are_reproducible(self) -> None:
        manifest = self.evidence["texture_derivation_manifest"]
        self.assertEqual(sha256_file(record_path(manifest)), manifest["sha256"])
        for name, record in self.evidence["derived_textures"].items():
            self.assertEqual(sha256_file(record_path(record)), record["sha256"], name)
        expected_views = {
            "neutral_front",
            "neutral_left_30deg",
            "neutral_right_30deg",
            "neutral_left_profile",
            "neutral_right_profile",
            "gaze_left_front",
            "gaze_right_front",
            "gaze_up_front",
            "gaze_down_front",
            "macro_left_iris_cornea",
            "macro_right_iris_cornea",
        }
        renders = self.evidence["fixed_renders"]
        self.assertEqual(set(renders), expected_views)
        for name, record in renders.items():
            self.assertEqual(sha256_file(record_path(record)), record["sha256"], name)

    def test_visual_gate_fails_closed_with_specific_observed_failures(self) -> None:
        visual = self.evidence["visual_acceptance"]
        self.assertTrue(visual["no_profile_protrusion"])
        for key in (
            "socket_alignment_front_and_three_quarter",
            "four_gaze_views_plausible",
            "brown_iris_reads_as_living_texture_not_flat_disc",
            "sclera_reads_as_living_tissue",
            "cornea_reads_as_natural_wet_lens",
            "macro_views_show_eye_detail",
            "overall_visual_fit_passed",
            "blink_supported",
            "promotion_allowed",
        ):
            self.assertFalse(visual[key], key)
        self.assertIn("macro cameras miss", visual["note"])

    def test_home_world_has_no_v2_candidate_reference(self) -> None:
        main_js = MAIN_JS.read_text(encoding="utf-8")
        self.assertNotIn("kira_r7_socket_eye_v2", main_js)
        self.assertNotIn("review_20260722_v2", main_js)


if __name__ == "__main__":
    unittest.main()
