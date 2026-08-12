import json
import tempfile
import unittest
from pathlib import Path

from tools.run_kira_robert_intro_dialogue_20260714 import (
    build_prompt,
    build_public_report,
    parse_response,
    scan_turn,
    spoken_similarity,
    write_report,
)


class KiraRobertDialoguePrivacyTests(unittest.TestCase):
    def test_parse_private_mind_with_spaces(self):
        parsed = parse_response(
            "SPOKEN:\nHello.\nPRIVATE MIND:\nKira-only note.\nTRUTH_FLAGS:\n- confirmed"
        )
        self.assertEqual("Hello.", parsed["spoken"])
        self.assertEqual("Kira-only note.", parsed["private_mind"])

    def test_prompt_shares_public_text_but_only_own_private_notes(self):
        transcript = [
            {"speaker": "Kira", "spoken": "Public Kira.", "private_mind": "Kira secret.", "truth_flags": "Kira believes this but is uncertain."},
            {"speaker": "Robert", "spoken": "Public Robert.", "private_mind": "Robert secret.", "truth_flags": "Robert privately marked a boast."},
        ]
        kira_prompt = build_prompt(
            "Kira",
            transcript,
            "Robert said: Public Robert.",
            "weekly",
            role_grounding="Kira grounded record.",
            shared_continuity="No approved prior meeting.",
        )
        self.assertIn("Public Kira.", kira_prompt)
        self.assertIn("Public Robert.", kira_prompt)
        self.assertIn("Kira secret.", kira_prompt)
        self.assertIn("Kira believes this but is uncertain.", kira_prompt)
        self.assertNotIn("Robert secret.", kira_prompt)
        self.assertNotIn("Robert privately marked a boast.", kira_prompt)

        robert_prompt = build_prompt(
            "Robert",
            transcript,
            "Kira said: Public Kira.",
            "weekly",
            role_grounding="Robert grounded record.",
            shared_continuity="Prior public continuity.",
        )
        self.assertIn("Robert secret.", robert_prompt)
        self.assertIn("Robert privately marked a boast.", robert_prompt)
        self.assertNotIn("Kira secret.", robert_prompt)
        self.assertNotIn("Kira believes this but is uncertain.", robert_prompt)
        self.assertIn("SPOKEN is public self-expression", robert_prompt)
        self.assertIn("Runtime/world truth is separate evidence", robert_prompt)

    def test_private_marker_in_spoken_is_a_blocker(self):
        warnings = scan_turn(
            "Kira",
            {
                "spoken": "Hello.\nPRIVATE SUMMARY:\nsecret",
                "private_mind": "secret",
                "truth_flags": "confirmed",
            },
            [],
        )
        self.assertIn("private_channel_in_spoken", warnings)

    def test_near_duplicate_detection(self):
        self.assertGreaterEqual(
            spoken_similarity(
                "We should visit the local art museum and cafe together.",
                "We should visit the local art museum and cafe together soon.",
            ),
            0.82,
        )

    def test_cross_speaker_duplicate_and_recurring_intro_reset_are_repaired(self):
        prior = [{
            "speaker": "Kira",
            "spoken": "We could visit the Newark gallery, get coffee, and enjoy the art together.",
        }]
        duplicate = scan_turn(
            "Robert",
            {
                "spoken": "We could visit the Newark gallery, get coffee, and enjoy the art together.",
                "private_mind": "I think I am repeating her.",
                "truth_flags": "confirmed repetition",
            },
            prior,
            meeting_kind="weekly",
        )
        self.assertIn("near_duplicate_spoken", duplicate)

        reset = scan_turn(
            "Kira",
            {
                "spoken": "Hi Robert, nice to meet you. I'm Kira. How are you today?",
                "private_mind": "I forgot the prior meeting.",
                "truth_flags": "uncertain",
            },
            [],
            meeting_kind="weekly",
        )
        self.assertIn("recurring_opening_reset", reset)

    def test_repeated_topic_loop_is_flagged_even_when_worded_differently(self):
        transcript = [
            {"speaker": "Kira" if index % 2 else "Robert", "spoken": text}
            for index, text in enumerate(
                [
                    "The Newark museum might be a pleasant art outing.",
                    "A Newark gallery and coffee stop sounds interesting.",
                    "We could hear music after seeing art in Newark.",
                    "Another Newark museum plan could include a cafe.",
                ],
                1,
            )
        ]
        warnings = scan_turn(
            "Kira",
            {
                "spoken": "Perhaps we should plan yet another Newark gallery and art outing.",
                "private_mind": "This subject is looping.",
                "truth_flags": "confirmed",
            },
            transcript,
            meeting_kind="weekly",
        )
        self.assertIn("topic_loop_stall", warnings)

    def test_inherited_first_person_memory_is_flagged(self):
        warnings = scan_turn(
            "Robert",
            {
                "spoken": "When I was a child, I remember being bullied in school.",
                "private_mind": "This came from human Robert.",
                "truth_flags": "inherited source",
            },
            [],
        )
        self.assertIn("inherited_human_memory_spoken_as_digital_lived_history", warnings)

    def test_unknown_heading_is_a_privacy_blocker(self):
        for heading in (
            "SCRATCHPAD",
            "Confidential Notes",
            "Thoughts",
            "Secret",
            "Chain of Thought",
        ):
            with self.subTest(heading=heading):
                parsed = parse_response(
                    f"SPOKEN:\nHello.\n{heading}:\nsecret\nTRUTH_FLAGS:\nconfirmed"
                )
                warnings = scan_turn("Kira", parsed, [])
                self.assertIn("unknown_section_heading", warnings)
                self.assertIn("speech_privacy_parse_failed", warnings)

    def test_public_report_has_hashes_but_no_private_or_raw_text(self):
        report = {
            "dialogue_id": "privacy_test",
            "status": "running",
            "started_at": "now",
            "model": "test",
            "transcript": [{
                "turn": 1,
                "speaker": "Kira",
                "spoken": "Public hello.",
                "private_mind": "Kira secret.",
                "truth_flags": "confirmed",
                "warnings": [],
                "raw": "SPOKEN: Public hello. PRIVATE_MIND: Kira secret.",
                "at": "now",
            }],
            "observer_notes": [],
        }
        public = build_public_report(
            report,
            {"Kira": {"entry_count": 1, "private_payload_sha256": "d" * 64}},
        )
        encoded = json.dumps(public)
        self.assertIn("Public hello", encoded)
        self.assertNotIn("Kira secret", encoded)
        self.assertNotIn('"raw"', encoded)
        self.assertTrue(public["transcript"][0]["private_recorded"])
        self.assertFalse(public["privacy_storage"]["role_confidentiality_enforced"])
        self.assertNotIn("private/kira", encoded)

    def test_writer_separates_private_sidecar_from_public_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = {
                "dialogue_id": "privacy_test",
                "status": "running",
                "started_at": "now",
                "model": "test",
                "transcript": [{
                    "turn": 1,
                    "speaker": "Robert",
                    "spoken": "Public hello.",
                    "private_mind": "Robert secret.",
                    "truth_flags": "uncertain",
                    "warnings": [],
                    "raw": "raw secret",
                    "at": "now",
                }],
                "observer_notes": [],
            }
            public_json = root / "session.json"
            public_md = root / "session.md"
            monitor = root / "session.monitor.md"
            write_report(report, public_json, public_md, monitor)
            self.assertNotIn("Robert secret", public_json.read_text(encoding="utf-8"))
            self.assertNotIn("Robert secret", public_md.read_text(encoding="utf-8"))
            self.assertNotIn("private/robert", public_json.read_text(encoding="utf-8"))
            private = root / "private" / "robert" / "session.private.json"
            private_record = json.loads(private.read_text(encoding="utf-8"))
            self.assertIn("Robert secret", private.read_text(encoding="utf-8"))
            self.assertFalse(private_record["tts_allowed"])
            self.assertFalse(private_record["role_confidentiality_enforced"])


if __name__ == "__main__":
    unittest.main()
