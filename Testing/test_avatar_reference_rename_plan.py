import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import plan_avatar_reference_renames as renamer  # noqa: E402


class AvatarReferenceRenamePlanTests(unittest.TestCase):
    def test_builds_clean_body_reference_names(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            original_root = renamer.PROJECT_ROOT
            try:
                renamer.PROJECT_ROOT = root
                folder = root / "Avatar" / "library" / "female" / "body"
                folder.mkdir(parents=True)
                (folder / "download erotic body name.jpg").write_bytes(b"image")
                (folder / "12345.webp").write_bytes(b"image")

                plan = renamer.build_plan(root / "Avatar")
                new_paths = [item["new_path"] for item in plan["renames"]]
                self.assertIn("Avatar/library/female/body/female_body_reference_001.webp", new_paths)
                self.assertIn("Avatar/library/female/body/female_body_reference_002.jpg", new_paths)
                self.assertTrue(plan["rules"]["does_not_clone_a_single_person"])
            finally:
                renamer.PROJECT_ROOT = original_root

    def test_apply_plan_renames_only_allowed_roots(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            original_root = renamer.PROJECT_ROOT
            try:
                renamer.PROJECT_ROOT = root
                folder = root / "Avatar" / "library" / "female" / "face_structure"
                folder.mkdir(parents=True)
                old = folder / "stock_face.jpg"
                old.write_bytes(b"image")

                plan = renamer.build_plan(root / "Avatar")
                renamer.apply_plan(plan)
                self.assertFalse(old.exists())
                self.assertTrue((folder / "female_face_structure_reference_001.jpg").exists())
            finally:
                renamer.PROJECT_ROOT = original_root


if __name__ == "__main__":
    unittest.main()
