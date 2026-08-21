from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "Avatar/library/neutral_nonperson_reference_charts_v2"
MANIFEST = PACKAGE / "REFERENCE_ASSET_MANIFEST.json"


def strict_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate key: {key}")
        value[key] = item
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class NeutralNonpersonReferenceChartsV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(
            MANIFEST.read_text(encoding="utf-8"),
            object_pairs_hook=strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )

    def test_exact_asset_set_hashes_and_plain_files(self):
        expected = {asset["path"] for asset in self.manifest["assets"]}
        actual = {
            path.relative_to(ROOT).as_posix()
            for path in PACKAGE.rglob("*")
            if path.is_file() and path.name not in {"README.md", "REFERENCE_ASSET_MANIFEST.json"}
        }
        self.assertEqual(actual, expected)
        marker = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        for asset in self.manifest["assets"]:
            path = ROOT / asset["path"]
            metadata = os.lstat(path)
            self.assertEqual(getattr(metadata, "st_nlink", 1), 1)
            self.assertFalse(marker and getattr(metadata, "st_file_attributes", 0) & marker)
            self.assertEqual(path.stat().st_size, asset["bytes"])
            self.assertEqual(sha256(path), asset["sha256"])

    def test_no_real_person_photo_class_or_embedded_photo_asset(self):
        boundaries = self.manifest["boundaries"]
        self.assertIs(boundaries["contains_real_person_photographs"], False)
        self.assertIs(boundaries["contains_real_person_photo_pixels"], False)
        allowed = {
            "neutral_nonperson_design_chart",
            "licensed_nonphotographic_medical_illustration",
            "machine_selector_map",
        }
        self.assertEqual({asset["content_class"] for asset in self.manifest["assets"]}, allowed)
        self.assertFalse(any(asset["path"].lower().endswith(".svg") for asset in self.manifest["assets"]))
        excluded = self.manifest["excluded_from_repository"]
        self.assertEqual(len(excluded), 1)
        self.assertIn("real_photograph", excluded[0]["reason"])
        self.assertIs(excluded[0]["copied"], False)

    def test_machine_utility_and_photo_deletion_remain_blocked(self):
        boundaries = self.manifest["boundaries"]
        self.assertIs(boundaries["machine_utility_proven"], False)
        self.assertIs(
            boundaries["skin_material_selector_and_direction_repeatable"], True
        )
        self.assertIs(boundaries["skin_material_render_review_passed"], False)
        self.assertIs(boundaries["photo_deletion_authorized"], False)
        skin_assets = {
            asset["role"]: asset for asset in self.manifest["assets"][:2]
        }
        self.assertEqual(
            {asset["utility_status"] for asset in skin_assets.values()},
            {"MACHINE_SELECTOR_AND_MATERIAL_DIRECTION_PASS_PENDING_RENDER"},
        )
        for asset in self.manifest["assets"][2:11]:
            self.assertEqual(asset["utility_status"], "UNPROVEN_SELECTOR_ONLY")
        self.assertEqual(
            self.manifest["next_gate"]["required"],
            "skin_material_render_and_structural_review_then_remaining_chart_selectors",
        )

    def test_medical_drawings_retain_source_and_credit(self):
        medical = [
            asset
            for asset in self.manifest["assets"]
            if asset["content_class"] == "licensed_nonphotographic_medical_illustration"
        ]
        self.assertEqual(len(medical), 4)
        for asset in medical:
            self.assertEqual(asset["source"], "NIDDK, National Institutes of Health")
            self.assertTrue(asset["source_url"].startswith("https://www.niddk.nih.gov/"))
            self.assertIn("National Institutes of Health", asset["required_credit"])

    def test_package_has_no_local_task_surface(self):
        combined = MANIFEST.read_text(encoding="utf-8") + (PACKAGE / "README.md").read_text(encoding="utf-8")
        lowered = combined.lower()
        self.assertNotIn("codex", lowered)
        self.assertNotIn("handoff", lowered)
        self.assertNotIn("c:\\users\\", lowered)
        self.assertNotIn("file://", lowered)


if __name__ == "__main__":
    unittest.main()
