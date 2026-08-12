from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.temporary_ai_control_center import known_canon_fact_sheet  # noqa: E402
import tools.temporary_ai_live_chat as live_chat  # noqa: E402
from tools.temporary_ai_live_chat import build_system_prompt  # noqa: E402


class TemporaryAICanonGroundingTests(unittest.TestCase):
    def test_ladybug_canon_rejects_invented_bakery(self) -> None:
        facts = known_canon_fact_sheet("Fictional Character", "Marinette / Ladybug", "")
        self.assertIn("Tom and Sabine run the Dupain Cheng Bakery in Paris.", facts["facts"])
        self.assertTrue(any("Baguette Borg" in item for item in facts["avoid"]))

    def test_stock_prior_answer_is_not_reinjected(self) -> None:
        candidate = {
            "candidate_id": "ladybug_prompt_smoke",
            "profile": {
                "display_name": "Marinette / Ladybug",
                "role_title": "Fashion student and Ladybug",
                "ai_type": "canon_reconstruction_temp_ai",
                "conversation_style": {
                    "avoid_stock_phrases": ["keeping busy with school and my friends"]
                },
                "canon_fact_sheet": known_canon_fact_sheet(
                    "Fictional Character", "Marinette / Ladybug", ""
                ),
            },
            "creation_request": {},
            "recent_chat_records": [
                {
                    "robert": "How are you?",
                    "candidate": "I've been keeping busy with school and my friends.",
                }
            ],
        }
        prompt = build_system_prompt(candidate, "How are you today?")
        self.assertIn("known stock or drift phrase", prompt)
        self.assertNotIn("I've been keeping busy with school and my friends", prompt)
        self.assertIn("Dupain Cheng Bakery", prompt)

    def test_recent_chat_context_spans_multiple_transcripts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            first = out_dir / "temporary_ai_live_chat_test_candidate_20260620_010000.json"
            second = out_dir / "temporary_ai_live_chat_test_candidate_20260621_010000.json"
            first.write_text(
                json.dumps({"records": [{"robert": "First question", "candidate": "First answer"}]}),
                encoding="utf-8",
            )
            second.write_text(
                json.dumps({"records": [{"robert": "Second question", "candidate": "Second answer"}]}),
                encoding="utf-8",
            )
            os.utime(first, (1000, 1000))
            os.utime(second, (2000, 2000))
            with patch.object(live_chat, "OUT_DIR", out_dir):
                records = live_chat.recent_chat_records("test_candidate", limit=5)

        self.assertEqual([record["robert"] for record in records], ["First question", "Second question"])

    def test_saved_loop_state_is_injected_as_factual_continuity(self) -> None:
        candidate = {
            "candidate_id": "emily_continuity_smoke",
            "profile": {
                "display_name": "Emily Carter",
                "role_title": "Programmer",
                "ai_type": "expert_temp_ai",
            },
            "creation_request": {},
            "recent_chat_records": [],
            "project_continuity": {
                "current_project": "TemporaryAI memory repair",
                "next_step": "Run the continuity tests",
                "last_generated_files": ["workbench/outputs/memory_repair.py"],
            },
        }
        prompt = build_system_prompt(candidate, "Where did you leave off?")
        self.assertIn("TemporaryAI memory repair", prompt)
        self.assertIn("Run the continuity tests", prompt)
        self.assertIn("workbench/outputs/memory_repair.py", prompt)
        self.assertIn("Never claim an artifact exists", prompt)

    def test_kara_adaptation_lock_distinguishes_zor_el_from_brainiac(self) -> None:
        profile_path = (
            PROJECT_ROOT
            / "TemporaryAI"
            / "candidates"
            / "kara_zor_el_my_adventures_with_superman_kara_zor_el_20260606_181026"
            / "temporary_ai_profile.json"
        )
        profile = json.loads(profile_path.read_text(encoding="utf-8-sig"))
        facts = "\n".join(profile["canon_fact_sheet"]["facts"])
        avoids = "\n".join(profile["canon_fact_sheet"]["avoid"])
        self.assertIn("biological father is Zor-El", facts)
        self.assertIn("surrogate parent she calls Father", facts)
        self.assertIn("Do not call Jor-El Kara's father", avoids)


if __name__ == "__main__":
    unittest.main()
