from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.temporary_ai_control_center import (  # noqa: E402
    build_ambiguity_questions,
    build_knowledge_plan,
)


class TemporaryAIContinuityDefaultTests(unittest.TestCase):
    def test_adaptation_without_season_uses_whole_released_continuity(self) -> None:
        plan = build_knowledge_plan(
            "Fictional Character",
            "Kara Zor-El",
            "My Adventures With Superman",
            "Female",
        )
        self.assertEqual(
            plan["continuity_scope"]["mode"],
            "whole_released_selected_source_continuity",
        )
        self.assertFalse(
            plan["continuity_scope"]["adaptation_identity_must_still_be_resolved"]
        )
        self.assertIn("latest verified released material", plan["continuity_scope"]["default_rule"])

    def test_explicit_season_remains_an_explicit_endpoint(self) -> None:
        plan = build_knowledge_plan(
            "Fictional Character",
            "Kara Zor-El",
            "My Adventures With Superman season 3",
            "Female",
        )
        self.assertEqual(plan["continuity_scope"]["mode"], "explicit_endpoint")

    def test_blank_version_uses_ranked_primary_continuity_without_routine_question(self) -> None:
        questions = build_ambiguity_questions("Fictional Character", "Spider-Man", "")
        plan = build_knowledge_plan(
            "Fictional Character",
            "Spider-Man",
            "",
            "Male",
        )
        self.assertEqual(questions, [])
        self.assertEqual(
            plan["continuity_scope"]["adaptation_identity_resolution_mode"],
            "automatic_ranked_primary_continuity_resolution",
        )
        self.assertFalse(plan["continuity_scope"]["routine_owner_question_required"])


if __name__ == "__main__":
    unittest.main()
