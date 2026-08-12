import unittest

from Core.dialogue_privacy import (
    DialoguePrivacyError,
    contains_private_marker,
    parse_structured_response,
    prepare_dialogue_speech_turns,
    prepare_speech_turn,
)


class DialoguePrivacyTests(unittest.TestCase):
    def test_accepts_heading_variants_without_leaking(self):
        variants = ["PRIVATE_MIND", "PRIVATE MIND", "PRIVATE SUMMARY", "Robert PRIVATE SUMMARY"]
        for heading in variants:
            with self.subTest(heading=heading):
                parsed = parse_structured_response(
                    f"SPOKEN:\nHello Robert.\n\n{heading}:\nThis stays private.\n\nTRUTH_FLAGS:\n- confirmed"
                )
                self.assertEqual("Hello Robert.", parsed["spoken"])
                self.assertEqual("This stays private.", parsed["private_mind"])
                self.assertTrue(parsed["privacy_safe_for_speech"])
                self.assertFalse(contains_private_marker(parsed["spoken"]))

    def test_markdown_headings_are_parsed(self):
        parsed = parse_structured_response(
            "**SPOKEN:**\nHi.\n\n**PRIVATE MIND:**\nNo.\n\n**TRUTH FLAGS:**\n- uncertain"
        )
        self.assertEqual("Hi.", parsed["spoken"])
        self.assertEqual("No.", parsed["private_mind"])
        self.assertEqual("- uncertain", parsed["truth_flags"])

    def test_reparses_raw_when_stored_spoken_contains_private_summary(self):
        item = {
            "turn": 41,
            "speaker": "Kira",
            "spoken": "Hello.\n\nPRIVATE SUMMARY:\nsecret\n\nTRUTH_FLAGS:\n- confirmed",
            "raw": "SPOKEN:\nHello.\n\nPRIVATE SUMMARY:\nsecret\n\nTRUTH_FLAGS:\n- confirmed",
        }
        turn = prepare_speech_turn(item)
        self.assertEqual("Hello.", turn["text"])
        self.assertTrue(turn["recovered_from_raw"])

    def test_fails_closed_without_separable_spoken_text(self):
        with self.assertRaises(DialoguePrivacyError):
            prepare_speech_turn(
                {
                    "turn": 2,
                    "speaker": "Robert",
                    "spoken": "PRIVATE MIND:\nsecret",
                    "raw": "PRIVATE MIND:\nsecret\nTRUTH_FLAGS:\n- uncertain",
                }
            )

    def test_internal_thought_and_private_reasoning_never_enter_speech(self):
        for heading in ("INTERNAL THOUGHT", "PRIVATE REASONING", "NOT FOR TTS"):
            with self.subTest(heading=heading):
                item = {
                    "turn": 7,
                    "speaker": "Kira",
                    "spoken": f"Hello.\n{heading}:\nsecret",
                    "raw": f"SPOKEN:\nHello.\n{heading}:\nsecret\nTRUTH_FLAGS:\nconfirmed",
                }
                turn = prepare_speech_turn(item)
                self.assertEqual("Hello.", turn["text"])
                self.assertNotIn("secret", turn["text"])

    def test_title_case_private_headings_never_enter_speech(self):
        headings = (
            "Confidential Notes",
            "Thoughts",
            "Secret",
            "Chain of Thought",
            "Scratchpad",
        )
        for heading in headings:
            with self.subTest(heading=heading):
                item = {
                    "turn": 70,
                    "speaker": "Kira",
                    "spoken": f"Hello.\n{heading}:\nprivate material",
                    "raw": (
                        f"SPOKEN:\nHello.\n{heading}:\nprivate material\n"
                        "TRUTH_FLAGS:\nconfirmed"
                    ),
                }
                try:
                    turn = prepare_speech_turn(item)
                except DialoguePrivacyError:
                    continue
                self.assertEqual("Hello.", turn["text"])
                self.assertNotIn("private material", turn["text"])

    def test_unknown_section_heading_fails_closed(self):
        with self.assertRaises(DialoguePrivacyError):
            prepare_speech_turn(
                {
                    "turn": 8,
                    "speaker": "Robert",
                    "spoken": "Hello.",
                    "raw": "SPOKEN:\nHello.\nSCRATCHPAD:\nsecret\nTRUTH_FLAGS:\nconfirmed",
                }
            )

    def test_unheaded_raw_fails_closed_even_if_stored_spoken_looks_safe(self):
        with self.assertRaises(DialoguePrivacyError):
            prepare_speech_turn(
                {
                    "turn": 9,
                    "speaker": "Robert",
                    "spoken": "Hello.",
                    "raw": "Hello. This response has no explicit speech boundary.",
                }
            )

    def test_dialogue_audit_counts_recovered_turns(self):
        data = {
            "transcript": [
                {
                    "turn": 1,
                    "speaker": "Kira",
                    "spoken": "Hi.",
                    "raw": "SPOKEN:\nHi.\nPRIVATE_MIND:\nprivate\nTRUTH_FLAGS:\n- confirmed",
                },
                {
                    "turn": 2,
                    "speaker": "Robert",
                    "spoken": "Hello.\nPRIVATE MIND:\nprivate\nTRUTH_FLAGS:\n- confirmed",
                    "raw": "SPOKEN:\nHello.\nPRIVATE MIND:\nprivate\nTRUTH_FLAGS:\n- confirmed",
                },
            ]
        }
        turns, audit = prepare_dialogue_speech_turns(data)
        self.assertEqual(2, len(turns))
        self.assertEqual(1, audit["recovered_from_raw_count"])
        self.assertEqual("passed_spoken_only", audit["privacy_status"])

    def test_spoken_only_export_preserves_upstream_context_contamination_label(self):
        data = {
            "privacy_audit": {
                "privacy_status": "passed_spoken_only",
                "source_context_privacy_status": "contaminated_original_recovered_for_speech",
                "source_context_contamination_count": 12,
            },
            "turns": [{"turn": 1, "speaker": "Kira", "spoken": "Safe public text."}],
        }
        turns, first = prepare_dialogue_speech_turns(data)
        data["privacy_audit"]["spoken_payload_sha256"] = first["spoken_payload_sha256"]
        turns, audit = prepare_dialogue_speech_turns(data)
        self.assertEqual(12, audit["source_context_contamination_count"])
        self.assertEqual(0, audit["source_storage_contamination_count"])
        self.assertEqual(
            "contaminated_original_recovered_for_speech",
            audit["source_context_privacy_status"],
        )
        self.assertTrue(audit["upstream_privacy_audit"]["payload_hash_matches"])

    def test_spoken_only_export_can_select_tail_only_after_full_payload_validation(self):
        data = {
            "privacy_audit": {
                "privacy_status": "passed_spoken_only",
                "source_context_privacy_status": "contaminated_original_recovered_for_speech",
                "source_context_contamination_count": 2,
            },
            "turns": [
                {"turn": 1, "speaker": "Kira", "spoken": "First safe turn."},
                {"turn": 2, "speaker": "Robert", "spoken": "Second safe turn."},
                {"turn": 3, "speaker": "Kira", "spoken": "Third safe turn."},
            ],
        }
        _, full = prepare_dialogue_speech_turns(data)
        data["privacy_audit"]["spoken_payload_sha256"] = full["spoken_payload_sha256"]

        turns, excerpt = prepare_dialogue_speech_turns(data, last_turns=2)
        self.assertEqual([2, 3], [turn["source_turn"] for turn in turns])
        self.assertEqual(2, excerpt["turn_count"])
        self.assertEqual(3, excerpt["source_turn_count"])
        self.assertEqual(2, excerpt["selection"]["last_turns"])
        self.assertTrue(excerpt["upstream_privacy_audit"]["payload_hash_matches"])

        data["turns"][0]["spoken"] = "Tampered outside the selected tail."
        with self.assertRaises(DialoguePrivacyError):
            prepare_dialogue_speech_turns(data, last_turns=2)


if __name__ == "__main__":
    unittest.main()
