import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from validate_variant_relationship_risk_profile import validate_variant_relationship_risk_profile  # noqa: E402


class VariantRelationshipRiskProfileValidatorTests(unittest.TestCase):
    def test_template_and_examples_validate(self) -> None:
        paths = [
            PROJECT_ROOT / "Data" / "variant_ai" / "relationship_risk_profiles" / "variant_relationship_risk_profile_template.json",
            *sorted((PROJECT_ROOT / "Data" / "variant_ai" / "relationship_risk_profiles" / "examples").glob("*.json")),
        ]
        for path in paths:
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(validate_variant_relationship_risk_profile(data), [])

    def test_non_adult_cannot_allow_adult_relationship_exploration(self) -> None:
        path = PROJECT_ROOT / "Data" / "variant_ai" / "relationship_risk_profiles" / "examples" / "rock_frontman_party_era_variant.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["age_coding"] = "teen"
        errors = validate_variant_relationship_risk_profile(data)
        self.assertTrue(any("age_coding is adult" in error for error in errors))

    def test_source_fit_must_not_be_consent(self) -> None:
        path = PROJECT_ROOT / "Data" / "variant_ai" / "relationship_risk_profiles" / "examples" / "rock_frontman_party_era_variant.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source_fit"]["source_fit_is_not_consent"] = False
        errors = validate_variant_relationship_risk_profile(data)
        self.assertTrue(any("source_fit_is_not_consent" in error for error in errors))

    def test_privacy_rules_block_unsourced_private_events(self) -> None:
        path = PROJECT_ROOT / "Data" / "variant_ai" / "relationship_risk_profiles" / "examples" / "rock_frontman_party_era_variant.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["privacy_and_memory_rules"]["no_unsourced_private_events"] = False
        errors = validate_variant_relationship_risk_profile(data)
        self.assertTrue(any("no_unsourced_private_events" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
