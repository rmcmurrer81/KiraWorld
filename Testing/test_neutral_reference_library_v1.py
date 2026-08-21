from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "Avatar/library/neutral_nonperson_reference_charts_v2"
MANIFEST = PACKAGE / "REFERENCE_ASSET_MANIFEST.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class NeutralReferenceLibraryV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_all_stored_assets_match_exact_size_and_hash(self) -> None:
        assets = self.manifest["assets"]
        self.assertEqual(len(assets), 15)
        for asset in assets:
            with self.subTest(path=asset["path"]):
                path = ROOT / asset["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, asset["bytes"])
                self.assertEqual(sha256(path), asset["sha256"])

    def test_generated_assets_cannot_claim_medical_or_identity_authority(self) -> None:
        for asset in self.manifest["assets"]:
            if asset["content_class"] == "neutral_nonperson_design_chart":
                expected = (
                    "MACHINE_SELECTOR_AND_MATERIAL_DIRECTION_PASS_PENDING_RENDER"
                    if asset["role"] == "skin_tone_and_regional_material"
                    else "UNPROVEN_SELECTOR_ONLY"
                )
                self.assertEqual(asset["utility_status"], expected)

    def test_maturity_and_activation_fail_closed(self) -> None:
        boundary = self.manifest["boundaries"]
        self.assertIs(boundary["contains_real_person_photographs"], False)
        self.assertIs(boundary["automatic_body_authoring_authorized"], False)
        self.assertIs(boundary["photo_deletion_authorized"], False)
        self.assertIs(boundary["machine_utility_proven"], False)

    def test_medical_assets_have_reuse_and_attribution_records(self) -> None:
        for asset in self.manifest["assets"]:
            if asset["content_class"] != "licensed_nonphotographic_medical_illustration":
                continue
            self.assertTrue(asset["source_url"].startswith("https://"))
            self.assertTrue(asset["reuse"])
            self.assertTrue(asset["required_credit"])

    def test_linked_candidate_is_not_misrepresented_as_stored(self) -> None:
        excluded = self.manifest["excluded_from_repository"]
        self.assertEqual(len(excluded), 1)
        self.assertIs(excluded[0]["copied"], False)
        self.assertIn("real_photograph", excluded[0]["reason"])

    def test_male_medical_overviews_are_exact_and_non_identity_evidence(self) -> None:
        assets = {
            Path(asset["path"]).name: asset
            for asset in self.manifest["assets"]
            if asset["content_class"] == "licensed_nonphotographic_medical_illustration"
        }
        expected = {
            "niddk_male_reproductive_tract_side_labeled.jpg",
            "niddk_male_urinary_tract_front_labeled.jpg",
        }
        self.assertTrue(expected.issubset(assets))
        for name in expected:
            asset = assets[name]
            self.assertEqual(asset["source"], "NIDDK, National Institutes of Health")
            self.assertEqual(asset["utility_status"], "GENERAL_STRUCTURE_ONLY")


if __name__ == "__main__":
    unittest.main()
