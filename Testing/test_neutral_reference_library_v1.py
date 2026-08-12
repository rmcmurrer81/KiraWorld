from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "Avatar/library/neutral_generated_reference_charts_v1"
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
        assets = self.manifest["generated_assets"] + self.manifest["medical_assets"]
        self.assertEqual(len(assets), 15)
        for asset in assets:
            with self.subTest(path=asset["path"]):
                path = ROOT / asset["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, asset["bytes"])
                self.assertEqual(sha256(path), asset["sha256"])

    def test_generated_assets_cannot_claim_medical_or_identity_authority(self) -> None:
        for asset in self.manifest["generated_assets"]:
            self.assertIs(asset["medical_authority"], False)
            self.assertIs(asset["identity_binding"], False)

    def test_maturity_and_activation_fail_closed(self) -> None:
        boundary = self.manifest["authoritative_boundaries"]
        self.assertIs(boundary["adult_classification_from_appearance_allowed"], False)
        self.assertIs(boundary["automatic_body_activation_allowed"], False)
        self.assertIs(boundary["existing_reference_deletion_authorized"], False)
        self.assertIs(boundary["owner_visual_review_required"], True)

    def test_medical_assets_have_reuse_and_attribution_records(self) -> None:
        for asset in self.manifest["medical_assets"]:
            self.assertTrue(asset["source_url"].startswith("https://"))
            self.assertTrue(asset["download_url"].startswith("https://"))
            self.assertTrue(asset["license_or_reuse_status"])
            self.assertTrue(asset["required_credit"])

    def test_linked_candidate_is_not_misrepresented_as_stored(self) -> None:
        candidates = self.manifest["linked_not_stored_candidates"]
        self.assertEqual(len(candidates), 1)
        self.assertIs(candidates[0]["stored"], False)

    def test_male_medical_overviews_are_exact_and_non_identity_evidence(self) -> None:
        assets = {
            Path(asset["path"]).name: asset
            for asset in self.manifest["medical_assets"]
        }
        expected = {
            "niddk_male_reproductive_tract_side_labeled.jpg",
            "niddk_male_urinary_tract_front_labeled.jpg",
        }
        self.assertTrue(expected.issubset(assets))
        for name in expected:
            asset = assets[name]
            self.assertIn("NIDDK", asset["license_or_reuse_status"])
            self.assertIn("not_robert_likeness", asset["truth_boundary"])


if __name__ == "__main__":
    unittest.main()
