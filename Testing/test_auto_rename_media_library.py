import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from auto_rename_media_library import apply_rename_plan, build_rename_plan, normalize_name  # noqa: E402


class AutoRenameMediaLibraryTests(unittest.TestCase):
    def test_normalizes_download_style_file_name(self) -> None:
        self.assertEqual(
            normalize_name("Mighty Morphin Power Rangers The Movie FULL MOVIE 1080p.MP4", is_file=True),
            "mighty_morphin_power_rangers_the_movie.mp4",
        )
        self.assertEqual(
            normalize_name("Demi Lovato - Let It Go (from Frozen) (Official Video).mp4", is_file=True),
            "demi_lovato_let_it_go_from_frozen.mp4",
        )

    def test_normalizes_tv_episode_tokens_for_sorting(self) -> None:
        self.assertEqual(
            normalize_name("WEIRD SCIENCE TV SHOW S1 E7 Party High, U.S.A..mp4", is_file=True),
            "weird_science_s01e07_party_high_u_s_a.mp4",
        )
        self.assertEqual(
            normalize_name("Weird Science TV Show S4E1 Searching for Boris Karloff(1996).mp4", is_file=True),
            "weird_science_s04e01_searching_for_boris_karloff_1996.mp4",
        )

    def test_normalizes_common_library_typos(self) -> None:
        self.assertEqual(normalize_name("Live Preformances", is_file=False), "live_performances")
        self.assertEqual(normalize_name("ghostbusters_soundtrak", is_file=False), "ghostbusters_soundtrack")
        self.assertEqual(normalize_name("kidz_bop_vol_17_with_2_bonus_tacks", is_file=False), "kidz_bop_vol_17_with_2_bonus_tracks")
        self.assertEqual(
            normalize_name("Emilia Jones - BAFTAs 2022 Perfomance.mp4", is_file=True),
            "emilia_jones_baftas_2022_performance.mp4",
        )

    def test_applies_known_canonical_media_names(self) -> None:
        self.assertEqual(
            normalize_name(
                "Twin Peaks Fire Walk with Me 1992 complete full movie in English.mp4",
                is_file=True,
            ),
            "twin_peaks_fire_walk_with_me_1992.mp4",
        )
        self.assertEqual(
            normalize_name(
                "Genesis of the Daleks   FULL EPISODES   Season 12   Doctor Who.mp4",
                is_file=True,
            ),
            "doctor_who_s12e11_e16_genesis_of_the_daleks.mp4",
        )
        self.assertEqual(
            normalize_name("Cartoon All-Stars to the Rescue VHS (1990).mp4", is_file=True),
            "cartoon_all_stars_to_the_rescue_1990_special.mp4",
        )
        self.assertEqual(
            normalize_name("2.Netflix Original Movie Enola Holmes 2 (2022).mp4", is_file=True),
            "enola_holmes_2_2022.mp4",
        )
        self.assertEqual(
            normalize_name(
                "Stranger.Things.S01E02.Chapter.Two.The.Weirdo.On.Maple.Street.720p.5.1Ch.WebRip-iMovieID (video-converter.com).mp4",
                is_file=True,
            ),
            "stranger_things_s01e02_chapter_two_the_weirdo_on_maple_street.mp4",
        )
        self.assertEqual(
            normalize_name("(0) The Christmas Invasion.mp4", is_file=True),
            "doctor_who_2005_s02e00_the_christmas_invasion_2005_special.mp4",
        )
        self.assertEqual(
            normalize_name("Highlander - 1X01 - The Gathering-1.mp4", is_file=True),
            "highlander_s01e01_the_gathering.mp4",
        )
        self.assertEqual(
            normalize_name("Life.On.Mars.S01E01.DVDRip.PAL.Plus.Commentary.x264-MaG.mp4", is_file=True),
            "life_on_mars_uk_s01e01.mp4",
        )
        self.assertEqual(
            normalize_name(
                "Terminator The Sarah Connor Chronicles (2008) - S02E22 - Born to Run (Regrade) VC1.mkv",
                is_file=True,
            ),
            "terminator_the_sarah_connor_chronicles_2008_s02e22_born_to_run.mkv",
        )
        self.assertEqual(
            normalize_name(
                "terminator_the_sarah_connor_chronicles_2008_s01e01_pilot_regrade_vc1.mkv",
                is_file=True,
            ),
            "terminator_the_sarah_connor_chronicles_2008_s01e01_pilot.mkv",
        )

    def test_applies_nested_folder_and_file_renames(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Data" / "library"
            source = root / "movies" / "Perfect Body" / "Perfect Body Full Movie 720p.MP4"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"demo")

            plan = build_rename_plan(root)
            result = apply_rename_plan(plan)

            self.assertEqual(result["applied_count"], 2)
            self.assertTrue((root / "movies" / "perfect_body" / "perfect_body.mp4").exists())
            self.assertFalse(source.exists())

    def test_skips_target_collision(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Data" / "library"
            messy = root / "movies" / "demo" / "Demo Movie.MP4"
            clean = root / "movies" / "demo" / "demo_movie.mp4"
            messy.parent.mkdir(parents=True)
            messy.write_bytes(b"messy")
            clean.write_bytes(b"clean")

            plan = build_rename_plan(root)
            result = apply_rename_plan(plan)

            self.assertEqual(result["applied_count"], 0)
            self.assertEqual(result["skipped_count"], 1)
            self.assertTrue(messy.exists())
            self.assertTrue(clean.exists())


if __name__ == "__main__":
    unittest.main()
