import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from sort_unsorted_audio import apply_plan, build_plan, infer_artist_title  # noqa: E402


class SortUnsortedAudioTests(unittest.TestCase):
    def test_infers_artist_dash_title(self) -> None:
        artist, title = infer_artist_title(Path("Rachel Platten - Fight Song.mp3"))

        self.assertEqual(artist, "rachel_platten")
        self.assertEqual(title, "fight_song")

    def test_infers_dear_evan_hansen_cast_recording(self) -> None:
        artist, title = infer_artist_title(
            Path("Waving Through a Window from the DEAR EVAN HANSEN Original Broadway Cast Recording.mp3")
        )

        self.assertEqual(artist, "dear_evan_hansen_original_broadway_cast")
        self.assertEqual(title, "waving_through_a_window")

    def test_infers_loose_the_fray_track_without_dash(self) -> None:
        artist, title = infer_artist_title(Path("The Fray Fair Fight.mp3"))

        self.assertEqual(artist, "the_fray")
        self.assertEqual(title, "fair_fight")

    def test_build_and_apply_plan_for_loose_audio_only(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "Data" / "library" / "music" / "unsorted"
            target = root / "Data" / "library" / "music" / "artists"
            song = source / "Rachel Platten - Fight Song.mp3"
            album_song = source / "Album" / "01 Track.mp3"
            video = source / "Rachel Platten - Fight Song.mp4"
            song.parent.mkdir(parents=True)
            song.write_bytes(b"song")
            album_song.parent.mkdir()
            album_song.write_bytes(b"album")
            video.write_bytes(b"video")

            plan = build_plan(source, target)
            result = apply_plan(plan)

            self.assertEqual(plan["operation_count"], 1)
            self.assertEqual(result["applied_count"], 1)
            self.assertTrue((target / "rachel_platten" / "rachel_platten_fight_song.mp3").exists())
            self.assertTrue(album_song.exists())
            self.assertTrue(video.exists())


if __name__ == "__main__":
    unittest.main()
