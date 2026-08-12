import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from validate_private_creative_library import validate_private_creative_library  # noqa: E402


class PrivateCreativeLibraryValidatorTests(unittest.TestCase):
    def test_private_creative_libraries_validate(self) -> None:
        paths = sorted((PROJECT_ROOT / "Data" / "creative_libraries").glob("**/*.json"))
        self.assertGreaterEqual(len(paths), 3)
        for path in paths:
            with self.subTest(path=path.relative_to(PROJECT_ROOT)):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(validate_private_creative_library(data), [])

    def test_rejects_public_posting_now(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "creative_libraries" / "kira" / "private_creative_library.json").read_text(encoding="utf-8"))
        data["public_export_rules"]["public_posting_allowed_now"] = True
        errors = validate_private_creative_library(data)
        self.assertTrue(any("public_posting_allowed_now" in error for error in errors))

    def test_rejects_not_shared_item_visible_to_robert(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "creative_libraries" / "lisa" / "private_creative_library.json").read_text(encoding="utf-8"))
        data["items"][0]["visibility"] = "shared_with_robert"
        errors = validate_private_creative_library(data)
        self.assertTrue(any("not_shared items must remain owner_only" in error for error in errors))

    def test_rejects_memory_promotion_by_sharing(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "creative_libraries" / "shared" / "shared_creative_library.json").read_text(encoding="utf-8"))
        data["memory_policy"]["sharing_an_item_does_not_promote_memory"] = False
        errors = validate_private_creative_library(data)
        self.assertTrue(any("sharing_an_item_does_not_promote_memory" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
