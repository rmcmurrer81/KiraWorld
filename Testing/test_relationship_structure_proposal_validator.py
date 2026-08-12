import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from validate_relationship_structure_proposal import validate_relationship_structure_proposal  # noqa: E402


class RelationshipStructureProposalValidatorTests(unittest.TestCase):
    def _template(self) -> dict:
        path = (
            PROJECT_ROOT
            / "Data"
            / "relationships"
            / "structures"
            / "proposals"
            / "robert_kira_lisa_open_relationship_discussion.template.json"
        )
        return json.loads(path.read_text(encoding="utf-8"))

    def test_template_validates(self) -> None:
        self.assertEqual(validate_relationship_structure_proposal(self._template()), [])

    def test_jealousy_cannot_create_consent(self) -> None:
        data = self._template()
        data["trigger"]["jealousy_creates_consent"] = True
        errors = validate_relationship_structure_proposal(data)
        self.assertTrue(any("jealousy_creates_consent" in error for error in errors))

    def test_accepted_requires_everyone_yes(self) -> None:
        data = self._template()
        data["status"] = "accepted"
        data["participants"][0]["current_response"] = "yes"
        data["participants"][1]["current_response"] = "yes"
        data["participants"][2]["current_response"] = "undecided"
        errors = validate_relationship_structure_proposal(data)
        self.assertTrue(any("every participant" in error for error in errors))

    def test_structure_changed_requires_accepted_and_yes(self) -> None:
        data = self._template()
        data["outcome"]["structure_changed"] = True
        data["outcome"]["new_structure"] = "open_relationship"
        errors = validate_relationship_structure_proposal(data)
        self.assertTrue(any("status is accepted" in error for error in errors))
        self.assertTrue(any("current_response to be yes" in error for error in errors))

    def test_scope_rules_require_separate_group_consent(self) -> None:
        data = self._template()
        data["interaction_scope_rules"]["relationship_structure_yes_is_not_group_intimacy_yes"] = False
        errors = validate_relationship_structure_proposal(data)
        self.assertTrue(any("relationship_structure_yes_is_not_group_intimacy_yes" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
