import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from scan_library_sources import _build_character_discovery_brief, _source_candidates_from_updates  # noqa: E402


class LibrarySourceScanTests(unittest.TestCase):
    def test_source_candidates_include_parseable_scripts_and_media_review_notes(self) -> None:
        update_check = {
            "added": [
                {
                    "path": "Data/library/scripts/Miraculous_Ladybug/episode-0601.pdf",
                    "name": "episode-0601.pdf",
                    "extension": ".pdf",
                    "media_type": "document",
                    "category": "script",
                },
                {
                    "path": "Data/library/tv_shows/miraculous_ladybug/s06e01.mp4",
                    "name": "s06e01.mp4",
                    "extension": ".mp4",
                    "media_type": "video",
                    "category": "tv_show",
                },
                {
                    "path": "Data/library/music/artists/demo/song.mp3",
                    "name": "song.mp3",
                    "extension": ".mp3",
                    "media_type": "audio",
                    "category": "music",
                },
            ],
            "changed": [],
        }

        candidates = _source_candidates_from_updates(update_check)

        self.assertEqual(len(candidates), 2)
        self.assertTrue(candidates[0]["parseable_by_pre_gpu_source_tools"])
        self.assertEqual(candidates[0]["recommendation"], "run_source_indexer_and_evidence_extractor")
        self.assertFalse(candidates[1]["parseable_by_pre_gpu_source_tools"])
        self.assertTrue(candidates[1]["media_needs_future_analysis"])
        self.assertIn("future audio_video_analysis", candidates[1]["recommendation"])

    def test_discovery_brief_notes_multiple_characters_for_future_temp_ai(self) -> None:
        with TemporaryDirectory() as tmpdir:
            fanfic_path = Path(tmpdir) / "ladybug_bunnyx_king_arthur_test_fanfic.md"
            fanfic_path.write_text(
                "Ladybug went through a portal and Bunnyx helped her repair time.",
                encoding="utf-8",
            )
            character_index = {
                "sources": [
                    {
                        "source_path": str(fanfic_path),
                        "source_authority": "fanfic_variant",
                        "detected_characters": [
                            {
                                "character_id": "bunnyx_alix",
                                "display_name": "Bunnyx / Alix Kubdel",
                            }
                        ],
                    }
                ],
                "by_character": {
                    "ladybug_marinette": [
                        {
                            "display_name": "Ladybug / Marinette Dupain-Cheng",
                            "file_name": "episode-0509.pdf",
                            "source_authority": "canon",
                            "content_format": "script_or_transcript",
                            "matched_aliases": ["Ladybug", "Marinette"],
                            "mention_count": 164,
                            "confidence": 0.99,
                        }
                    ],
                    "bunnyx_alix": [
                        {
                            "source_path": str(fanfic_path),
                            "file_name": "ladybug_bunnyx_king_arthur_test_fanfic.md",
                            "source_authority": "fanfic_variant",
                            "content_format": "story_prose",
                            "matched_aliases": ["Bunnyx"],
                            "mention_count": 21,
                            "confidence": 0.95,
                        }
                    ],
                },
            }
            evidence_master = {
                "characters": {
                    "ladybug_marinette": {"evidence_count": 115},
                    "bunnyx_alix": {"evidence_count": 14},
                }
            }

            brief = _build_character_discovery_brief(
                character_index=character_index,
                evidence_master_index=evidence_master,
                update_check={"needs_index_refresh": False, "added_count": 0, "changed_count": 0, "removed_count": 0},
                source_candidates=[],
            )

            characters = {item["character_id"]: item for item in brief["characters"]}
            self.assertTrue(characters["ladybug_marinette"]["candidate_for_future_temporary_ai"])
            self.assertTrue(characters["bunnyx_alix"]["candidate_for_future_temporary_ai"])
            self.assertEqual(characters["bunnyx_alix"]["display_name"], "Bunnyx / Alix Kubdel")
            self.assertEqual(characters["bunnyx_alix"]["fanfic_variant_source_count"], 1)
            self.assertIn("fanfic/variant", " ".join(characters["bunnyx_alix"]["source_notes"]))
            risk_review = characters["bunnyx_alix"]["sources"][0]["fanfic_variant_risk_review"]
            self.assertEqual(risk_review["decision"], "allowed_with_review")

    def test_discovery_brief_runs_risk_review_for_pdf_fanfic_sources(self) -> None:
        with TemporaryDirectory() as tmpdir, unittest.mock.patch(
            "scan_library_sources.review_fanfic_file",
            return_value={"decision": "blocked_requires_adult_branch_or_reject"},
        ) as review:
            fanfic_path = Path(tmpdir) / "downloaded_fanfic.pdf"
            fanfic_path.write_bytes(b"%PDF-test")
            character_index = {
                "sources": [
                    {
                        "source_path": str(fanfic_path),
                        "source_authority": "fanfic_variant",
                        "detected_characters": [
                            {
                                "character_id": "ladybug_marinette",
                                "display_name": "Ladybug / Marinette Dupain-Cheng",
                            }
                        ],
                    }
                ],
                "by_character": {
                    "ladybug_marinette": [
                        {
                            "source_path": str(fanfic_path),
                            "file_name": "downloaded_fanfic.pdf",
                            "source_authority": "fanfic_variant",
                            "content_format": "story_prose",
                            "matched_aliases": ["Ladybug"],
                            "mention_count": 10,
                            "confidence": 0.95,
                        }
                    ]
                },
            }
            evidence_master = {"characters": {"ladybug_marinette": {"evidence_count": 4}}}

            brief = _build_character_discovery_brief(
                character_index=character_index,
                evidence_master_index=evidence_master,
                update_check={"needs_index_refresh": False, "added_count": 0, "changed_count": 0, "removed_count": 0},
                source_candidates=[],
            )

            review.assert_called_once()
            risk_review = brief["characters"][0]["sources"][0]["fanfic_variant_risk_review"]
            self.assertEqual(risk_review["decision"], "blocked_requires_adult_branch_or_reject")


if __name__ == "__main__":
    unittest.main()
