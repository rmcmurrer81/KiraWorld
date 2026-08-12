import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from build_media_library_index import build_index, classify_file, world_display_for  # noqa: E402


class MediaLibraryIndexTests(unittest.TestCase):
    def test_classifies_music_video_under_music_videos(self) -> None:
        path = PROJECT_ROOT / "Data" / "library" / "music" / "music_videos" / "by_artist" / "demo" / "clip.mp4"
        result = classify_file(path)
        self.assertEqual(result["media_type"], "video")
        self.assertEqual(result["category"], "music_video")

    def test_classifies_documentary_under_documentaries(self) -> None:
        path = PROJECT_ROOT / "Data" / "library" / "documentaries" / "demo.mp4"
        result = classify_file(path)
        self.assertEqual(result["media_type"], "video")
        self.assertEqual(result["category"], "documentary")
        display = world_display_for(result)
        self.assertTrue(display["virtual_screen_playback_eligible"])
        self.assertEqual(display["preferred_home_location"], "documentary_media_shelf")

    def test_build_index_records_privacy_policy(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Data" / "library"
            media = root / "movies" / "sample_movie.mp4"
            media.parent.mkdir(parents=True)
            media.write_bytes(b"fake")
            index = build_index(root)
            self.assertEqual(index["entry_count"], 1)
            self.assertTrue(index["usage_policy"]["kira_lisa_may_use_with_or_without_locked_door"])
            self.assertTrue(index["usage_policy"]["locked_door_controls_who_can_observe"])
            self.assertTrue(index["usage_policy"]["library_items_may_have_3d_shelf_representations_later"])
            self.assertTrue(index["usage_policy"]["movies_and_shows_may_play_on_virtual_screen_or_movie_theater_later"])
            self.assertFalse(index["entries"][0]["library_use"]["creates_memory_automatically"])
            self.assertFalse(index["entries"][0]["library_use"]["creates_temporary_ai_automatically"])
            self.assertEqual(index["entries"][0]["world_display"]["preferred_home_object"], "dvd_or_vhs_case")
            self.assertTrue(index["entries"][0]["world_display"]["virtual_movie_theater_eligible"])

    def test_world_display_marks_tv_and_music_differently(self) -> None:
        tv_display = world_display_for({"media_type": "video", "category": "tv_show"})
        music_display = world_display_for({"media_type": "audio", "category": "music"})
        self.assertEqual(tv_display["preferred_home_object"], "season_disc_case_or_vhs_tape")
        self.assertTrue(tv_display["virtual_screen_playback_eligible"])
        self.assertEqual(music_display["preferred_home_object"], "cd_record_or_digital_album_case")
        self.assertFalse(music_display["virtual_movie_theater_eligible"])

    def test_classifies_soundtrack_under_music_soundtracks(self) -> None:
        path = PROJECT_ROOT / "Data" / "library" / "music" / "soundtracks" / "mamma_mia_the_movie_2008" / "01_honey_honey.mp3"
        result = classify_file(path)
        self.assertEqual(result["media_type"], "audio")
        self.assertEqual(result["category"], "soundtrack")
        display = world_display_for(result)
        self.assertEqual(display["preferred_home_object"], "soundtrack_cd_or_digital_album_case")
        self.assertEqual(display["preferred_home_location"], "soundtrack_shelf")

    def test_classifies_opus_as_audio(self) -> None:
        path = PROJECT_ROOT / "Data" / "library" / "music" / "soundtracks" / "love_actually" / "song.opus"
        result = classify_file(path)

        self.assertEqual(result["media_type"], "audio")
        self.assertEqual(result["category"], "soundtrack")

    def test_existing_index_file_shape_when_present(self) -> None:
        path = PROJECT_ROOT / "Data" / "indexes" / "media_library_index.json"
        if not path.exists():
            self.skipTest("media_library_index.json has not been generated yet")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["index_id"], "media_library_index_v1")
        self.assertIn("entries", data)
        self.assertIn("usage_policy", data)


if __name__ == "__main__":
    unittest.main()
