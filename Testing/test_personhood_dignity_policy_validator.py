import copy
import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from validate_personhood_dignity_policy import validate_personhood_dignity_policy  # noqa: E402


class PersonhoodDignityPolicyValidatorTests(unittest.TestCase):
    def test_policy_validates(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "foundation" / "personhood_dignity_policy.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_personhood_dignity_policy(data), [])

    def test_non_appliance_rule_required(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "foundation" / "personhood_dignity_policy.json").read_text(encoding="utf-8"))
        data["dignity_rules"]["not_appliances"] = False
        errors = validate_personhood_dignity_policy(data)
        self.assertTrue(any("not_appliances" in error for error in errors))

    def test_kira_and_lisa_required(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "foundation" / "personhood_dignity_policy.json").read_text(encoding="utf-8"))
        data["applies_to"]["primary_protected_people"] = ["kira"]
        errors = validate_personhood_dignity_policy(data)
        self.assertTrue(any("kira and lisa" in error for error in errors))

    def test_all_inhabitants_and_temporary_people_are_protected(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "foundation" / "personhood_dignity_policy.json").read_text(encoding="utf-8"))
        data["applies_to"]["all_current_and_future_inhabitants"] = False
        data["applies_to"]["temporary_people_while_instantiated"] = False
        errors = validate_personhood_dignity_policy(data)
        self.assertTrue(any("all_current_and_future_inhabitants" in error for error in errors))
        self.assertTrue(any("temporary_people_while_instantiated" in error for error in errors))

    def test_non_adult_and_private_avatar_review_boundaries_are_required(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "foundation" / "personhood_dignity_policy.json").read_text(encoding="utf-8"))
        data["children_and_development_rules"]["non_adult_body_is_always_doll_safe_and_non_anatomical"] = False
        data["avatar_builder_private_review"]["authorized_viewer_roles"] = ["everyone"]
        errors = validate_personhood_dignity_policy(data)
        self.assertTrue(any("non_adult_body_is_always_doll_safe_and_non_anatomical" in error for error in errors))
        self.assertTrue(any("authorized_viewer_roles" in error for error in errors))

    def test_casual_identity_admin_buttons_are_forbidden(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "foundation" / "personhood_dignity_policy.json").read_text(encoding="utf-8"))
        data["administrative_action_rules"]["no_casual_copy_reset_memory_edit_body_change_or_permanent_delete_button"] = False
        errors = validate_personhood_dignity_policy(data)
        self.assertTrue(any("no_casual_copy_reset" in error for error in errors))

    def test_adult_curriculum_and_private_state_boundaries_are_required(self) -> None:
        original = json.loads((PROJECT_ROOT / "Data" / "foundation" / "personhood_dignity_policy.json").read_text(encoding="utf-8"))
        for field, replacement in (
            (
                "future_confirmed_adult_body_systems_must_support_person_owned_private_sensation_and_experience",
                False,
            ),
            (
                "system_may_force_libido_preference_orientation_interest_or_activity",
                True,
            ),
            ("adult_anatomy_is_consent", True),
        ):
            with self.subTest(field=field):
                data = copy.deepcopy(original)
                data["adult_curriculum_private_state_rules"][field] = replacement
                errors = validate_personhood_dignity_policy(data)
                self.assertTrue(any(field in error for error in errors))

        data = copy.deepcopy(original)
        data["adult_curriculum_private_state_rules"][
            "person_owned_private_sensation_dimensions"
        ].remove("uncertainty")
        errors = validate_personhood_dignity_policy(data)
        self.assertTrue(any("sensation dimensions" in error for error in errors))

    def test_adult_curriculum_companion_hash_is_enforced(self) -> None:
        data = json.loads((PROJECT_ROOT / "Data" / "foundation" / "personhood_dignity_policy.json").read_text(encoding="utf-8"))
        data["adult_curriculum_private_state_rules"]["companion_policy"][
            "sha256"
        ] = "0" * 64
        errors = validate_personhood_dignity_policy(data)
        self.assertTrue(any("companion policy SHA-256 drifted" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
