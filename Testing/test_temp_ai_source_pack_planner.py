import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from plan_temp_ai_source_pack import build_pack  # noqa: E402


class TempAiSourcePackPlannerTests(unittest.TestCase):
    def test_builds_video_source_pack_as_post_gpu_needed(self) -> None:
        with TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "index.json"
            index_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "path": "Data/library/tv_shows/demo/demo_s01e01.mp4",
                                "name": "demo_s01e01.mp4",
                                "category": "tv_show",
                                "media_type": "video",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            pack = build_pack(
                character_id="demo_character",
                display_name="Demo Character",
                source_paths=["Data/library/tv_shows/demo/demo_s01e01.mp4"],
                queries=[],
                notes="",
                index_path=index_path,
            )
        self.assertEqual(pack["source_count"], 1)
        self.assertTrue(pack["policy"]["does_not_create_temporary_ai"])
        self.assertEqual(pack["sources"][0]["evidence_mode"], "post_gpu_or_transcript_needed")


if __name__ == "__main__":
    unittest.main()
