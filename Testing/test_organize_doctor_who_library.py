import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from organize_doctor_who_library import apply_plan, build_plan  # noqa: E402


class OrganizeDoctorWhoLibraryTests(unittest.TestCase):
    def test_moves_classic_and_revived_files_into_era_folders(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Data" / "library"
            doctor_root = root / "tv_shows" / "doctor_who"
            doctor_root.mkdir(parents=True)
            classic = doctor_root / "S01E01 - An Unearthly Child.mp4"
            revived = doctor_root / "doctor_who_2005_s05e01_the_eleventh_hour.mp4"
            classic.write_bytes(b"classic")
            revived.write_bytes(b"revived")

            plan = build_plan(root)
            result = apply_plan(plan)

            self.assertEqual(result["moved_count"], 2)
            self.assertTrue(
                (doctor_root / "classic_1963" / "s01" / "doctor_who_1963_s01e01_an_unearthly_child.mp4").exists()
            )
            self.assertTrue(
                (doctor_root / "revived_2005" / "s05" / "doctor_who_2005_s05e01_the_eleventh_hour.mp4").exists()
            )

    def test_moves_revived_season_two_and_specials(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Data" / "library"
            doctor_root = root / "tv_shows" / "doctor_who"
            doctor_root.mkdir(parents=True)
            special = doctor_root / "doctor_who_2005_s02e00_the_christmas_invasion_2005_special.mp4"
            episode = doctor_root / "doctor_who_2005_s02e01_new_earth.mp4"
            special.write_bytes(b"special")
            episode.write_bytes(b"episode")

            plan = build_plan(root)
            result = apply_plan(plan)

            self.assertEqual(result["moved_count"], 2)
            self.assertTrue(
                (
                    doctor_root
                    / "revived_2005"
                    / "s02_specials"
                    / "doctor_who_2005_s02e00_the_christmas_invasion_2005_special.mp4"
                ).exists()
            )
            self.assertTrue(
                (doctor_root / "revived_2005" / "s02" / "doctor_who_2005_s02e01_new_earth.mp4").exists()
            )

    def test_blocks_target_collision(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Data" / "library"
            doctor_root = root / "tv_shows" / "doctor_who"
            source = doctor_root / "S01E01 - An Unearthly Child.mp4"
            target = doctor_root / "classic_1963" / "s01" / "doctor_who_1963_s01e01_an_unearthly_child.mp4"
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
