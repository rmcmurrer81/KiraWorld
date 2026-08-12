import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from validate_reading_reaction import validate_reading_reaction  # noqa: E402


class ReadingReactionValidatorTests(unittest.TestCase):
    def test_template_validates(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "reading" / "reactions" / "reading_reaction_template.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_reading_reaction(data), [])

    def test_example_validates(self) -> None:
        data = json.loads(
            (
                PROJECT_ROOT
                / "Data"
                / "reading"
                / "reactions"
                / "examples"
                / "kira_frankenstein_first_imagination.example.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(validate_reading_reaction(data), [])

    def test_lived_memory_conversion_is_rejected(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "reading" / "reactions" / "reading_reaction_template.json").read_text(encoding="utf-8"))
        data["memory_policy"]["does_not_become_lived_memory"] = False
        errors = validate_reading_reaction(data)
        self.assertIn("memory_policy.does_not_become_lived_memory must be true.", errors)

    def test_private_imagination_requires_label(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "reading" / "reactions" / "reading_reaction_template.json").read_text(encoding="utf-8"))
        data["imagination"]["certainty"] = "actually_happened_to_me"
        errors = validate_reading_reaction(data)
        self.assertTrue(any("imagination.certainty" in error for error in errors))

    def test_story_fantasy_influence_cannot_be_treated_as_consent(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "reading" / "reactions" / "reading_reaction_template.json").read_text(encoding="utf-8"))
        data["dream_and_fantasy_influence"]["fantasies_do_not_prove_consent_or_relationship_status"] = False
        errors = validate_reading_reaction(data)
        self.assertIn(
            "dream_and_fantasy_influence.fantasies_do_not_prove_consent_or_relationship_status must be true.",
            errors,
        )

    def test_preference_signal_requires_changeable_taste(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "reading" / "reactions" / "reading_reaction_template.json").read_text(encoding="utf-8"))
        data["preference_signal"]["may_change_later"] = False
        errors = validate_reading_reaction(data)
        self.assertIn("preference_signal.may_change_later must be true.", errors)


if __name__ == "__main__":
    unittest.main()
