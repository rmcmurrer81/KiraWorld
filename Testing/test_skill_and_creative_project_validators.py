import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from validate_creative_project import validate_creative_project  # noqa: E402
from validate_skill_development import validate_skill_development  # noqa: E402


class SkillAndCreativeProjectValidatorTests(unittest.TestCase):
    def test_skill_examples_validate(self) -> None:
        paths = [
            PROJECT_ROOT / "Data" / "skills" / "skill_development_template.json",
            *sorted((PROJECT_ROOT / "Data" / "skills" / "examples").glob("*.json")),
        ]
        for path in paths:
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(validate_skill_development(data), [])

    def test_creative_project_examples_validate(self) -> None:
        paths = [
            PROJECT_ROOT / "Data" / "creative_projects" / "creative_project_template.json",
            *sorted((PROJECT_ROOT / "Data" / "creative_projects" / "examples").glob("*.json")),
        ]
        for path in paths:
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(validate_creative_project(data), [])

    def test_skill_rejects_unapproved_spending(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "skills" / "examples" / "kira_filmmaking_interest_skill.example.json").read_text(encoding="utf-8"))
        data["practice_rules"]["may_spend_money_without_approval"] = True
        errors = validate_skill_development(data)
        self.assertTrue(any("may_spend_money_without_approval" in error for error in errors))

    def test_project_rejects_public_posting_now(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "creative_projects" / "examples" / "kira_private_short_video_project.example.json").read_text(encoding="utf-8"))
        data["public_export_policy"]["public_posting_allowed_now"] = True
        errors = validate_creative_project(data)
        self.assertTrue(any("public_posting_allowed_now" in error for error in errors))

    def test_project_rejects_false_memory_policy(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "creative_projects" / "examples" / "lisa_private_book_project.example.json").read_text(encoding="utf-8"))
        data["memory_policy"]["fictional_events_are_not_personal_history"] = False
        errors = validate_creative_project(data)
        self.assertTrue(any("fictional_events_are_not_personal_history" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
