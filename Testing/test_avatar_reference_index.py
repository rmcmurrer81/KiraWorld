import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from build_avatar_reference_index import build_index  # noqa: E402


class AvatarReferenceIndexTests(unittest.TestCase):
    def test_marks_body_references_private(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Avatar"
            body = root / "library" / "female" / "body" / "neutral_body_reference.jpg"
            body.parent.mkdir(parents=True)
            body.write_bytes(b"image")

            index = build_index(root)
            self.assertEqual(index["entry_count"], 1)
            entry = index["entries"][0]
            self.assertEqual(entry["sensitivity"], "private_body_reference")
            self.assertTrue(entry["usage_policy"]["owner_controls_visibility"])
            self.assertFalse(entry["usage_policy"]["may_be_used_for_public_exports"])
            self.assertFalse(entry["usage_policy"]["may_be_used_for_other_avatars"])

    def test_marks_outfits_as_style_references(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Avatar"
            outfit = root / "library" / "female" / "references" / "outfits" / "casual" / "casual_01.png"
            outfit.parent.mkdir(parents=True)
            outfit.write_bytes(b"image")

            index = build_index(root)
            entry = index["entries"][0]
            self.assertEqual(entry["category"], "outfit_reference")
            self.assertEqual(entry["sensitivity"], "style_reference")


if __name__ == "__main__":
    unittest.main()
