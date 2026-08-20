import hashlib
import json
import struct
import unittest
from pathlib import Path

from Core.kira_runtime_body_selection import evaluate_kira_runtime_body_selection
from tools.restore_kira_pre_r6_live_body import verify as verify_rollback


ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    "Avatar/models/temp_ai/kira/avatar.glb":
        "3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e",
    "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6/"
    "r6_20260718_163658/kira_provisional_body_r6.glb":
        "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
    "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6/"
    "r6_20260718_163658/kira_provisional_body_r6_manifest.json":
        "56c4de5cedaee926448b506b2d2117934ba7c6ead200a6d70bee90d3b17f9657",
    "Avatar/models/staged/kira/eyes/kira_brown_eye_rig_v3_2/"
    "kira_brown_eye_rig_v3_2.glb":
        "fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413",
    "Data/world_tests/kira_r6_exact_browser_sandbox_20260718/"
    "20260718T222144Z/evidence.json":
        "29f995522ec773774a61ceb1a36aa9ac0c731b3c7b690e5ac8b9de130957a5ed",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def glb_asset(path: Path) -> dict:
    with path.open("rb") as stream:
        header = stream.read(20)
        if len(header) != 20 or header[:4] != b"glTF":
            raise ValueError("not_glb2")
        version = struct.unpack_from("<I", header, 4)[0]
        json_length = struct.unpack_from("<I", header, 12)[0]
        json_type = header[16:20]
        if version != 2 or json_type != b"JSON":
            raise ValueError("not_glb2_json")
        payload = stream.read(json_length)
    return json.loads(payload.decode("utf-8").rstrip("\x00 \t\r\n"))["asset"]


class KiraR6PortableReviewBundleTests(unittest.TestCase):
    def test_exact_primary_bundle_hashes(self):
        for relative, expected in EXPECTED.items():
            path = ROOT / relative
            with self.subTest(relative=relative):
                self.assertTrue(path.is_file())
                self.assertEqual(sha256(path), expected)

    def test_selection_is_reversible_review_not_permanent_approval(self):
        result = evaluate_kira_runtime_body_selection(ROOT)
        self.assertTrue(result["selection_valid"], result["selection_failures"])
        self.assertEqual(result["decision"], "reversible_r6_owner_review_trial_selected")
        self.assertTrue(result["technical_runtime_compatibility_passed"])
        self.assertFalse(result["full_adult_anatomy_proven"])
        self.assertFalse(result["eye_visual_fit_approved"])
        self.assertFalse(result["permanent_candidate_allowed"])
        self.assertFalse(result["kira_accepted_exact_candidate"])

    def test_rollback_bundle_is_complete_and_exact(self):
        verify_rollback()

    def test_source_attribution_and_adaptation_notice_are_preserved(self):
        asset = glb_asset(ROOT / "Avatar/models/temp_ai/kira/avatar.glb")
        extras = asset.get("extras") or {}
        self.assertEqual(extras.get("author"), "camilooh (https://sketchfab.com/camilooh)")
        self.assertIn("CC-BY-4.0", extras.get("license", ""))
        notice = (ROOT / "Avatar/avatar_builder/candidate_sources/"
                  "kira_provisional_body_r6/PRIVATE_REVIEW_BUNDLE.md")
        text = notice.read_text(encoding="utf-8")
        self.assertIn("CC BY 4.0", text)
        self.assertIn("adapted derivative", text)

    def test_hair_and_clothing_remain_separate(self):
        manifest_path = (ROOT / "Avatar/avatar_builder/candidate_sources/"
                         "kira_provisional_body_r6/r6_20260718_163658/"
                         "kira_provisional_body_r6_manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        absences = manifest["explicit_absences"]
        self.assertIn("not authored", absences["hair"])
        self.assertIn("not authored", absences["clothes"])
        clothing = (ROOT / "System/Docs/"
                    "AVATAR_SEPARATE_SHAREABLE_CLOTHING_v1.md").read_text(
                        encoding="utf-8")
        hair = (ROOT / "System/Docs/"
                "AVATAR_BUILDER_RUNTIME_HAIR_REQUIREMENTS_20260729.md").read_text(
                    encoding="utf-8")
        bald_policy = (ROOT / "System/Docs/"
                       "AVATAR_BALD_LOW_RESOURCE_AND_DETACHABLE_HAIR_POLICY_20260801.md").read_text(
                           encoding="utf-8")
        self.assertIn("independent hash-bound artifacts", clothing)
        self.assertIn("person-to-person transfer", clothing)
        self.assertIn("editable combing", hair)
        self.assertIn("distinct dry and wet states", hair)
        self.assertIn("wind, and wet review states", bald_policy)


if __name__ == "__main__":
    unittest.main()
