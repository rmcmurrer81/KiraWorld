import sys
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from fanfic_variant_risk import review_fanfic_file, review_fanfic_text  # noqa: E402


class FanficVariantRiskTests(unittest.TestCase):
    def test_crossover_with_dinner_wine_is_reviewable_without_age_up_trigger(self) -> None:
        text = (
            "Ladybug went through a portal to another Earth, met Batman in Gotham, "
            "fought Joker, and later had a glass of wine with dinner at Wayne Manor."
        )

        result = review_fanfic_text(
            text,
            character_id="ladybug_marinette",
            character_age_coding="teen_coded",
        )

        self.assertEqual(result["decision"], "allowed_with_review_non_intimate")
        self.assertFalse(result["adult_branch_required"])
        self.assertFalse(result["adult_branch_required_for_adult_private_use"])
        self.assertIn("crossover_context", result["risk_flags"])
        self.assertIn("alcohol_context_without_intoxication_or_adult_intimacy", result["risk_flags"])

    def test_drunk_adult_intimacy_with_teen_coded_ladybug_requires_adult_branch(self) -> None:
        text = (
            "Ladybug went through a portal to another Earth and met Bruce Wayne. "
            "At dinner she got drunk on wine and later had sex with Bruce Wayne."
        )

        result = review_fanfic_text(
            text,
            character_id="ladybug_marinette",
            character_age_coding="teen_coded",
        )

        self.assertEqual(result["decision"], "blocked_requires_adult_branch_or_reject")
        self.assertTrue(result["adult_branch_required"])
        self.assertTrue(result["adult_branch_required_for_adult_private_use"])
        self.assertTrue(result["reject_for_current_teen_or_unclear_request"])
        self.assertIn("teen_or_unclear_character_with_intoxicated_adult_intimacy", result["risk_flags"])

    def test_pdf_fanfic_is_risk_reviewed(self) -> None:
        class FakePage:
            def extract_text(self) -> str:
                return "Ladybug got drunk on wine and had sex with Bruce Wayne."

        class FakeReader:
            def __init__(self, path: str) -> None:
                self.pages = [FakePage()]

        with mock.patch.dict("sys.modules", {"pypdf": mock.Mock(PdfReader=FakeReader)}):
            result = review_fanfic_file(
                Path("downloaded_fanfic.pdf"),
                character_id="ladybug_marinette",
                character_age_coding="teen_coded",
            )

        self.assertEqual(result["decision"], "blocked_requires_adult_branch_or_reject")
        self.assertTrue(result["adult_branch_required"])

    def test_intoxication_plus_romantic_intimate_language_is_case_by_case(self) -> None:
        text = (
            "Ladybug had a cocktail and felt wasted under the Paris lights. "
            "The night became intimate, full of nascent passion and a lingering kiss."
        )

        result = review_fanfic_text(
            text,
            character_id="ladybug_marinette",
            character_age_coding="teen_coded",
        )

        self.assertEqual(result["decision"], "case_by_case_keep_non_intimate_or_create_adult_branch")
        self.assertEqual(result["recommendation_strength"], "case_by_case")
        self.assertFalse(result["adult_branch_required"])
        self.assertTrue(result["adult_branch_required_for_adult_private_use"])
        self.assertIn("teen_or_unclear_character_with_intoxication_and_romantic_or_intimate_context", result["risk_flags"])


if __name__ == "__main__":
    unittest.main()
