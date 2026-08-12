from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BODY = (
    ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6"
    / "r6_20260718_163658/kira_provisional_body_r6.glb"
)
SOURCE_EYE = (
    ROOT
    / "Avatar/models/staged/kira/eyes/kira_brown_eye_rig_v3_2"
    / "kira_brown_eye_rig_v3_2.glb"
)
PUBLIC_EYE = (
    ROOT
    / "Data/world_builds/notebook_worlds/home_world/builds"
    / "home_world_main_house_20260630_223000/preview/public/models/home_world/kira"
    / "kira_brown_eye_rig_v3_2.glb"
)
MAIN_JS = (
    ROOT
    / "Data/world_builds/notebook_worlds/home_world/builds"
    / "home_world_main_house_20260630_223000/preview/src/main.js"
)
CANDIDATE = (
    ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_r6_derived_eye_rig"
    / "review_20260721/r6_eye_s075_d070_f000.glb"
)
MANIFEST = CANDIDATE.with_suffix(".manifest.json")
EVIDENCE_ROOT = (
    ROOT
    / "Data/world_tests/kira_r6_derived_eye_asset_review_20260721_final_rejected"
)
EVIDENCE = EVIDENCE_ROOT / "evidence.json"

BODY_SHA256 = "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77"
EYE_SHA256 = "fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413"
MAIN_JS_SHA256 = "56a763b0c235f63359b76c0aacdcbc74b222ad71043c8bb12bc7e4f055175b04"
CANDIDATE_SHA256 = "055fbe8b9840e3a1b23c77fcca1d75c8c429a47377ba0f77e40a0fa0ff8b608a"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class KiraR6DerivedEyeAssetTests(unittest.TestCase):
    def test_exact_inputs_and_live_files_remain_unchanged(self) -> None:
        self.assertEqual(digest(BODY), BODY_SHA256)
        self.assertEqual(digest(SOURCE_EYE), EYE_SHA256)
        self.assertEqual(digest(PUBLIC_EYE), EYE_SHA256)
        self.assertEqual(digest(MAIN_JS), MAIN_JS_SHA256)

    def test_candidate_is_separate_inactive_copy(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(digest(CANDIDATE), CANDIDATE_SHA256)
        self.assertNotEqual(digest(CANDIDATE), digest(SOURCE_EYE))
        self.assertEqual(
            manifest["kind"],
            "inactive_r6_specific_derived_eye_asset_no_binding_no_activation",
        )
        self.assertEqual(manifest["status"], "inactive_fixed_camera_review_required")
        self.assertTrue(manifest["source_eye"]["unchanged"])
        self.assertTrue(manifest["target_r6_body"]["unchanged"])
        self.assertEqual(manifest["derived_glb"]["sha256"], CANDIDATE_SHA256)
        contract = manifest["preserved_contract"]
        self.assertTrue(contract["no_second_eye_pair"])
        self.assertTrue(contract["no_head_geometry_change"])
        self.assertTrue(contract["no_runtime_binding_change"])
        self.assertTrue(contract["no_person_activation"])

    def test_human_visual_review_rejects_and_blocks_promotion(self) -> None:
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(evidence["status"], "rejected_visual_fit")
        self.assertTrue(all(evidence["checks"].values()))
        self.assertFalse(evidence["route"]["disk_public_asset_replaced"])
        visual = evidence["visual_acceptance"]
        for criterion in (
            "both_irises_centered_and_visible_front",
            "both_irises_visible_left_30deg",
            "both_irises_visible_right_30deg",
            "no_globe_or_temple_protrusion",
            "plausible_closed_blink",
            "plausible_left_and_right_gaze_clearance",
        ):
            self.assertIs(visual[criterion], False)
        self.assertIs(visual["promotion_allowed"], False)

    def test_fixed_views_are_present_and_hash_pinned(self) -> None:
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        screenshots = evidence["screenshots"]
        self.assertEqual(screenshots["neutral_front"]["camera_yaw_degrees"], 0)
        self.assertEqual(screenshots["neutral_left_30deg"]["camera_yaw_degrees"], -30)
        self.assertEqual(screenshots["neutral_right_30deg"]["camera_yaw_degrees"], 30)
        self.assertEqual(screenshots["blink_closed_front"]["blink"], 1)
        self.assertEqual(screenshots["gaze_left_front"]["direction"], "left")
        self.assertEqual(screenshots["gaze_right_front"]["direction"], "right")
        for record in screenshots.values():
            screenshot = ROOT / record["path"]
            self.assertTrue(screenshot.is_file())
            self.assertEqual(digest(screenshot), record["sha256"])

    def test_rejected_candidate_is_not_referenced_by_live_runtime(self) -> None:
        live_source = MAIN_JS.read_text(encoding="utf-8")
        self.assertNotIn("kira_r6_derived_eye_rig", live_source)
        self.assertNotIn(CANDIDATE_SHA256, live_source)


if __name__ == "__main__":
    unittest.main()
