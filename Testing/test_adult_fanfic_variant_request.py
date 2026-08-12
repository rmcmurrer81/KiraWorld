import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from create_adult_fanfic_variant_request import build_adult_fanfic_variant_request  # noqa: E402
from plan_temp_ai_request import build_temp_ai_request_plan  # noqa: E402
from validate_temp_ai_simple_request import validate_temp_ai_simple_request  # noqa: E402


class AdultFanficVariantRequestTests(unittest.TestCase):
    def test_builds_valid_adult_branch_request_from_case_by_case_fanfic(self) -> None:
        brief = {
            "characters": [
                {
                    "character_id": "ladybug_marinette",
                    "display_name": "Ladybug / Marinette Dupain-Cheng",
                    "sources": [
                        {
                            "file_name": "episode-0509.pdf",
                            "source_path": "Data/library/scripts/Miraculous_Ladybug/episode-0509.pdf",
                            "source_authority": "canon",
                        },
                        {
                            "file_name": "episode-0521.pdf",
                            "source_path": "Data/library/scripts/Miraculous_Ladybug/episode-0521.pdf",
                            "source_authority": "canon",
                        },
                        {
                            "file_name": "miraculous-encounters-in-paris.pdf",
                            "source_path": "Data/library/stories/fanfic/Miraculous_Ladybug/miraculous-encounters-in-paris.pdf",
                            "source_authority": "fanfic_variant",
                            "fanfic_variant_risk_review": {
                                "decision": "case_by_case_keep_non_intimate_or_create_adult_branch",
                                "recommendation_strength": "case_by_case",
                                "adult_branch_required_for_adult_private_use": True,
                                "risk_flags": [
                                    "intoxication_context",
                                    "teen_or_unclear_character_with_romantic_or_intimate_context",
                                ],
                                "review_notes": "Keep teen layer non-intimate or create adult branch.",
                            },
                        }
                    ],
                }
            ]
        }

        request = build_adult_fanfic_variant_request(
            brief,
            character_id="ladybug_marinette",
            source_file="miraculous-encounters-in-paris.pdf",
            adult_age=21,
        )

        self.assertEqual(validate_temp_ai_simple_request(request), [])
        self.assertEqual(request["age_review"]["source_age_coding"], "adult")
        self.assertTrue(request["age_up_branch_plan"]["requested"])
        self.assertIn("teen_source_layer_adult_private_use", request["scope"]["not_allowed_contexts"])
        self.assertEqual(request["fanfic_review"]["risk_override_recommendation_strength"], "case_by_case")
        self.assertTrue(request["branch_source_inheritance"]["adult_branch_uses_canon_as_foundation"])
        self.assertTrue(request["branch_source_inheritance"]["future_canon_may_be_added_as_past_after_review"])
        self.assertEqual(len(request["branch_source_inheritance"]["canon_baseline_source_paths"]), 2)
        self.assertEqual(
            request["branch_source_inheritance"]["foundation_order"],
            [
                "reviewed_canon_baseline",
                "approved_fanfic_variant_layer",
                "adult_branch_transition",
                "branch_private_experience_after_activation",
            ],
        )
        self.assertEqual(
            request["source_plan"]["local_library_paths"][0],
            "Data/library/scripts/Miraculous_Ladybug/episode-0509.pdf",
        )

        plan = build_temp_ai_request_plan(request)
        self.assertEqual(plan["plan_status"], "ready_for_adult_branch_plan")
        self.assertTrue(plan["guardrails"]["age_up_transition_must_be_non_explicit"])

    def test_adult_age_must_be_adult(self) -> None:
        with self.assertRaises(ValueError):
            build_adult_fanfic_variant_request(
                {"characters": []},
                character_id="ladybug_marinette",
                source_file="demo.pdf",
                adult_age=17,
            )


if __name__ == "__main__":
    unittest.main()
