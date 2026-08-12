from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from temporary_ai_project_loop import (  # noqa: E402
    candidate_library_context,
    candidate_uses_character_life,
    character_conversation_continuity_context,
    character_life_answer_has_role_drift,
    character_life_prompt,
    generated_file_target,
    role_seed_prompt,
)


class TemporaryAICharacterLifeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidate = {
            "candidate_id": "ladybug_marinette_expanded_smoke",
            "profile": {
                "display_name": "Marinette / Ladybug",
                "role_title": "Fashion student and Ladybug",
                "ai_type": "canon_reconstruction_temp_ai",
                "ui_category": "Fictional Character",
                "personal_interests": ["fashion design", "baking"],
                "life_activity_profile": {
                    "forms": ["Marinette", "Ladybug"],
                    "activities": [
                        {"name": "continue a fashion sketch", "form": "Marinette"},
                        {"name": "write a private diary reflection", "form": "Marinette"},
                    ],
                    "output_folders": {
                        "fashion": "personal_projects/fashion/",
                        "diary": "personal_projects/diary/",
                    },
                },
            },
            "request": {"creation_type": "fictional_character"},
        }

    def test_fictional_candidate_uses_character_life(self) -> None:
        self.assertTrue(candidate_uses_character_life(self.candidate))

    def test_character_prompt_uses_ordinary_life_not_programmer_contract(self) -> None:
        prompt = character_life_prompt(self.candidate, "Continue ordinary life cycle 1")
        self.assertIn("continue a fashion sketch", prompt)
        self.assertIn("Selected activity for this cycle", prompt)
        self.assertIn("personal_projects/fashion/", prompt)
        self.assertIn("not a software-development assignment", prompt)
        self.assertNotIn("TemporaryAI redesign priority", prompt)
        self.assertNotIn("role_shaped_abilities", prompt)

    def test_role_prompt_only_switches_to_programming_when_explicitly_requested(self) -> None:
        ordinary = role_seed_prompt(self.candidate, "Continue ordinary life cycle 2")
        programming = role_seed_prompt(self.candidate, "Write a Python program for Robert")
        self.assertIn("write a private diary reflection", ordinary)
        self.assertNotIn("TemporaryAI redesign priority", ordinary)
        self.assertIn("Builder contract", programming)

    def test_personal_project_artifact_routes_to_stable_workbench_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_loop_dir = Path(temp_dir) / "outputs" / "project_loops"
            generated_root = project_loop_dir / "generated_files" / "run"
            target = generated_file_target(
                project_loop_dir,
                generated_root,
                Path("personal_projects/fashion/sketch_notes.md"),
                "",
            )
            self.assertEqual(
                target,
                Path(temp_dir) / "outputs" / "personal_projects" / "fashion" / "sketch_notes.md",
            )

    def test_library_access_is_read_only_and_interest_matched(self) -> None:
        import temporary_ai_project_loop as loop
        with tempfile.TemporaryDirectory() as temp_dir:
            readable = Path(temp_dir) / "fashion_history_notes.txt"
            readable.write_text("A short history of clothing design and sewing.", encoding="utf-8")
            loop._MEDIA_LIBRARY_CACHE = [
                {"path": str(readable), "name": readable.name, "category": "history", "media_type": "document"},
                {"path": str(Path(temp_dir) / "private.txt"), "name": "private.txt", "category": "private_adult_text", "media_type": "document"},
            ]
            text = candidate_library_context(self.candidate, "cycle 1 fashion history")
            self.assertIn("read-only", text.lower())
            self.assertIn("history of clothing", text)
        self.assertNotIn("private.txt", text)
        loop._MEDIA_LIBRARY_CACHE = None

    def test_character_life_rejects_business_and_skincare_drift(self) -> None:
        answer = "I revised The Ordinary skincare plan and identified stakeholders and job openings."
        self.assertTrue(
            character_life_answer_has_role_drift(
                self.candidate,
                "Continue ordinary life cycle 3",
                answer,
            )
        )
        self.assertFalse(
            character_life_answer_has_role_drift(
                self.candidate,
                "Continue ordinary life cycle 3",
                "I spent some quiet time sketching a jacket and saved two color ideas.",
            )
        )

    def test_character_life_rejects_old_temporary_ai_project_residue(self) -> None:
        answer = (
            "I updated the TemporaryAI candidate knowledge graph, proposed schema, "
            "and design document. Here is how Robert can test this."
        )
        self.assertTrue(
            character_life_answer_has_role_drift(
                self.candidate,
                "Continue ordinary life cycle 4",
                answer,
            )
        )

    def test_character_life_remembers_previous_live_chat_without_scripting_it(self) -> None:
        self.candidate["recent_chat_records"] = [
            {
                "robert": "I had a difficult day and felt lonely.",
                "candidate": "I am glad you told me. I can stay and listen.",
            },
            {
                "robert": "I like old movies and retro games.",
                "candidate": "That sounds like a fun evening.",
            },
        ]
        context = character_conversation_continuity_context(self.candidate)
        prompt = character_life_prompt(self.candidate, "Continue ordinary life cycle 5")
        self.assertIn("felt lonely", context)
        self.assertIn("retro games", prompt)
        self.assertIn("not as a script to repeat", prompt)
        self.assertIn("remember that reply as your mistake", prompt)
        self.assertIn("Do not reopen every old topic", prompt)

    def test_character_life_rejects_speaking_style_self_analysis(self) -> None:
        answer = "I updated my speaking-style notes and continued a canon audit of my personality."
        self.assertTrue(
            character_life_answer_has_role_drift(
                self.candidate,
                "Continue ordinary life cycle 6",
                answer,
            )
        )


if __name__ == "__main__":
    unittest.main()
