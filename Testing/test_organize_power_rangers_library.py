import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from organize_power_rangers_library import apply_plan, build_plan  # noqa: E402


class OrganizePowerRangersLibraryTests(unittest.TestCase):
    def test_moves_once_and_always_between_s29_and_s30(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Data" / "library"
            ranger_root = root / "tv_shows" / "power_rangers"
            ranger_root.mkdir(parents=True)
            source = ranger_root / "Power Rangers III - Once & Always.mp4"
            source.write_bytes(b"special")

            plan = build_plan(root)
            result = apply_plan(plan)

            self.assertEqual(result["moved_count"], 1)
            self.assertTrue(
                (
                    ranger_root
                    / "s29_s30_specials"
                    / "power_rangers_s29_s30_special_once_and_always_2023.mp4"
                ).exists()
            )

    def test_moves_cosmic_fury_to_s30_folder_with_clean_name(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Data" / "library"
            ranger_root = root / "tv_shows" / "power_rangers"
            source = (
                ranger_root
                / "cosmic_fury"
                / "Power Rangers - S30E01 - Lightning Strikes (1080p x265 EDGE2023).mp4"
            )
            source.parent.mkdir(parents=True)
            source.write_bytes(b"cosmic")

            plan = build_plan(root)
            result = apply_plan(plan)

            self.assertEqual(result["moved_count"], 1)
            self.assertTrue(
                (
                    ranger_root
                    / "s30_cosmic_fury"
                    / "power_rangers_cosmic_fury_s30e01_lightning_strikes.mp4"
                ).exists()
            )

    def test_blocks_target_collision(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Data" / "library"
            ranger_root = root / "tv_shows" / "power_rangers"
            source = ranger_root / "Power Rangers III - Once & Always.mp4"
            target = ranger_root / "s29_s30_specials" / "power_rangers_s29_s30_special_once_and_always_2023.mp4"
            source.parent.mkdir(parents=True)
            target.parent.mkdir(parents=True)
            source.write_bytes(b"source")
            target.write_bytes(b"target")

            plan = build_plan(root)
            result = apply_plan(plan)

            self.assertEqual(result["moved_count"], 0)
            self.assertEqual(result["skipped_count"], 1)
            self.assertTrue(source.exists())
            self.assertTrue(target.exists())


if __name__ == "__main__":
    unittest.main()
