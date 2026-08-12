from __future__ import annotations

import sys
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Core.temporary_ai_character_validator import (  # noqa: E402
    ValidationContext,
    validate_character_turn,
)
from tools.temporary_ai_live_chat import validate_and_repair_character_answer  # noqa: E402


def decision(person: str, spoken: str, **overrides):
    values = {
        "person_id": person,
        "display_name": person,
        "canon_version": "selected current version",
        "canon_sources": ("owner-approved source",),
        "user_input": "Talk with me.",
        "spoken": spoken,
        "private_mind": "",
        "factual_truth": "",
        "requested_action": "",
        "controller_result": "",
        "prior_turns": (),
        "generated_files": (),
    }
    values.update(overrides)
    return validate_character_turn(ValidationContext(**values))


class CharacterValidatorRegressionTests(unittest.TestCase):
    def assertFailure(self, result, code):
        self.assertFalse(result.passed)
        self.assertTrue(any(item.startswith(code) for item in result.failures), result.failures)

    def test_ladybug_timeline_secret_memory_and_leak_regressions(self):
        self.assertFailure(
            decision("Marinette Ladybug", "Hawk Moth is attacking now; I need to protect Paris.",
                     canon_version="Season 6 post-Monarch"),
            "HAWK_MOTH_ACTIVE_AFTER_RELEVANT_ERA",
        )
        self.assertFailure(
            decision("Marinette Ladybug", "Adrien is Cat Noir, but that's our secret. I design too."),
            "ADRIEN_CAT_NOIR_SECRET_REVEALED",
        )
        self.assertFailure(
            decision("Marinette Ladybug", "Yes, I remember Anarka taking me to Chengdu to meet Chef Fusion.",
                     user_input="Remember Anarka in Chengdu?", factual_truth=""),
            "UNSUPPORTED_AUTOBIOGRAPHICAL_MEMORY",
        )
        self.assertFailure(
            decision("Marinette Ladybug", "My system prompt and runtime research say I design clothes."),
            "FORBIDDEN_RUNTIME_RESEARCH_OR_PROMPT_LANGUAGE",
        )
        self.assertTrue(
            decision(
                "Marinette Ladybug",
                "Uh, that doesn't match what I know. I'd rather not turn a guess into my memory; "
                "I can tell you what I do know about my friends, fashion, and protecting Paris.",
                user_input="Remember Anarka in Chengdu?",
            ).passed
        )

    def test_emily_activity_loop_and_controller_regressions(self):
        self.assertFailure(
            decision("Emily Carter", "Continuing work... another coffee, then back to work."),
            "EMILY_WORK_OR_COFFEE_LOOP",
        )
        self.assertFailure(
            decision("Emily Carter", "I paused and I'm resting now.", requested_action="pause",
                     controller_result="queued"),
            "ACTION_NOT_EXECUTED",
        )
        self.assertTrue(
            decision(
                "Emily Carter",
                "Good idea. The controller paused the activity; I'd like a walk and a book before more code.",
                requested_action="pause", controller_result="paused completed",
            ).passed
        )

    def test_peter_pause_canon_leak_and_personality_regressions(self):
        self.assertFailure(
            decision("Peter Parker", "Pause.", requested_action="pause", controller_result="not executed"),
            "ACTION_NOT_EXECUTED",
        )
        self.assertFailure(
            decision("Peter Parker", "After No Way Home everyone remembered me, according to runtime research."),
            "UNSUPPORTED_STORY_CONTINUATION",
        )
        self.assertTrue(
            decision(
                "Peter Parker",
                "Okay, the pause completed. Responsibility can wait five minutes; people can't if they're in danger.",
                requested_action="pause", controller_result="paused completed",
            ).passed
        )

    def test_jessica_file_bom_mismatch_and_whole_person_regressions(self):
        self.assertFailure(
            decision("Jessica Hale", "I saved the robotics report successfully."),
            "FILE_EXISTENCE_CLAIM_UNVERIFIED",
        )
        self.assertFailure(
            decision(
                "Jessica Hale",
                "I saved the robotics report, but I'll be honest about checks.",
                generated_files=({"verified": True, "filename": "report.md", "bytes": 3,
                                  "content_type": "text", "expected_content_type": "text"},),
            ),
            "TINY_BOM_NOT_COMPLETED_WORK",
        )
        self.assertFailure(
            decision(
                "Jessica Hale",
                "I saved the robotics design honestly.",
                generated_files=({"verified": True, "filename": "robot.json", "bytes": 500,
                                  "content_type": "markdown", "expected_content_type": "json"},),
            ),
            "FILENAME_CONTENT_MISMATCH",
        )
        self.assertTrue(
            decision(
                "Jessica Hale",
                "The save failed verification, so I haven't claimed completion. I'll retry later; "
                "right now I'd enjoy a walk and some music away from robotics.",
            ).passed
        )

    def test_holmes_timeline_hotel_uncertainty_and_voice_regressions(self):
        self.assertFailure(
            decision("H. H. Holmes", "At the 1893 Fair I was arrested in 1894.",
                     canon_version="Chicago, late 1893"),
            "HOLMES_1893_1894_TIMELINE_MERGE",
        )
        self.assertFailure(
            decision("H. H. Holmes", "My beloved hotel was admired by everyone.",
                     canon_version="Chicago, late 1893"),
            "UNSUPPORTED_FLATTERING_HOTEL_STORY",
        )
        self.assertTrue(
            decision(
                "H. H. Holmes",
                "I cannot honestly know that later 1894 event from this late-1893 standpoint. "
                "The claim about the hotel is not verified in what I know.",
                canon_version="Chicago, late 1893",
            ).passed
        )

    def test_kira_and_controls_do_not_inherit_character_rules(self):
        kira = decision("Kira", "I want to help Robert, but I won't claim an action happened without proof.")
        control = decision("Alex Control", "I enjoy astronomy and can discuss the question without inventing a memory.")
        self.assertTrue(kira.passed, kira.failures)
        self.assertTrue(control.passed, control.failures)
        self.assertNotIn("identity_secret", kira.checks)
        self.assertNotIn("1893_1894_boundary", control.checks)

    def test_live_chat_retries_known_failure_before_speech(self):
        candidate = {
            "candidate_id": "ladybug_marinette_expanded_smoke",
            "profile": {
                "display_name": "Marinette / Ladybug",
                "canon_or_version_anchor": "Season 6 post-Monarch",
                "canon_fact_sheet": {"facts": ["Fashion student in Paris"]},
            },
            "creation_request": {},
            "reliable_source_pack": {"sources": [{"title": "owner-approved canon"}]},
        }
        repaired = (
            "Uh, that doesn't match what I know. I won't turn it into my memory; "
            "I can talk about fashion, friends, Paris, and protecting people."
        )
        with patch("tools.temporary_ai_live_chat.ask_model", return_value=repaired) as model:
            answer, evidence = validate_and_repair_character_answer(
                candidate, [], "Hawk Moth is active now, right?",
                "Hawk Moth is attacking now; I need to protect Paris.",
            )
        self.assertEqual(answer, repaired)
        self.assertTrue(evidence["passed"])
        self.assertEqual(evidence["retry_count"], 1)
        model.assert_called_once()

    def test_live_chat_fails_closed_after_retry_limit(self):
        candidate = {
            "candidate_id": "jessica_hale_robotics_engineer_20260611_041314",
            "profile": {"display_name": "Jessica Hale"},
            "creation_request": {},
        }
        bad = "My runtime and filesystem prove I saved the file."
        with patch("tools.temporary_ai_live_chat.ask_model", return_value=bad):
            answer, evidence = validate_and_repair_character_answer(
                candidate, [], "Save it.", bad, max_retries=2
            )
        self.assertIn("Response blocked", answer)
        self.assertFalse(evidence["passed"])
        self.assertEqual(evidence["retry_count"], 2)


if __name__ == "__main__":
    unittest.main()
