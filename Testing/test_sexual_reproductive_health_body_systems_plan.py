from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICY = (
    ROOT
    / "Avatar/avatar_builder/policies/sexual_reproductive_health_body_systems_plan_v1.json"
)
DOC = (
    ROOT
    / "System/Docs/"
    "SYNTHETIC_PERSON_SEXUAL_REPRODUCTIVE_HEALTH_EDUCATION_AND_BODY_SYSTEMS_PLAN_20260803.md"
)
REGISTRY = (
    ROOT
    / "Avatar/avatar_builder/body_systems/semantic_anatomy_route_registry_v1.json"
)
EXPECTED_AUTHORITATIVE_SOURCE_URLS = [
    "https://www.who.int/news-room/fact-sheets/detail/comprehensive-sexuality-education",
    "https://www.who.int/publications/m/item/9789231002595",
    "https://www.acog.org/womens-health/faqs/vulvovaginal-health",
    "https://www.ncbi.nlm.nih.gov/books/NBK547703/",
    "https://www.ncbi.nlm.nih.gov/books/NBK537132/",
    "https://www.ncbi.nlm.nih.gov/books/NBK500020/",
    "https://www.ncbi.nlm.nih.gov/books/NBK545147/",
    "https://www.ncbi.nlm.nih.gov/books/NBK525757/",
    "https://www.ncbi.nlm.nih.gov/books/NBK562291/",
    "https://www.ncbi.nlm.nih.gov/books/NBK482236/",
    "https://www.cdc.gov/contraception/about/index.html",
    "https://www.acog.org/womens-health/faqs/birth-control",
    "https://www.cdc.gov/sti/prevention/index.html",
    "https://www.cdc.gov/std/treatment-guidelines/screening-recommendations.htm",
]


def evidence_base_urls(document: str) -> list[str]:
    evidence_section = document.split("## Evidence base", 1)[1].split(
        "## Anatomy model", 1
    )[0]
    return [
        match.rstrip(".,;")
        for match in re.findall(r"https://[^\s)]+", evidence_section)
    ]


class SexualReproductiveHealthBodySystemsPlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        cls.document = DOC.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_plan_is_not_runtime_authority(self) -> None:
        self.assertEqual(
            self.policy["status"], "PLAN_ONLY_NOT_IMPLEMENTED_NOT_RUNTIME_AUTHORITY"
        )
        scope = self.policy["scope"]
        self.assertFalse(scope["current_body_or_runtime_mutation_authorized"])
        self.assertFalse(scope["relationship_or_sexual_activity_authorized"])
        self.assertFalse(scope["pregnancy_or_medical_state_authorized"])

    def test_truth_layers_are_separate(self) -> None:
        layers = set(self.policy["separate_truth_layers"])
        self.assertIn("external_surface_anatomy", layers)
        self.assertIn("internal_organs_ducts_muscles_nerves_and_vessels", layers)
        self.assertIn("time_based_physiology_and_flows", layers)
        self.assertIn("participant_activity_context_and_time_specific_consent", layers)
        self.assertGreaterEqual(len(layers), 7)

    def test_nonadult_lane_is_education_only(self) -> None:
        lane = self.policy["maturity_lanes"]["non_adult_or_unresolved"]
        self.assertFalse(lane["adult_sexual_capability_allowed"])
        self.assertFalse(lane["adult_anatomy_promotion_allowed"])
        self.assertFalse(lane["education_implies_capability"])
        self.assertEqual(
            lane["guaranteed_minimum_curriculum"],
            [
                "age_appropriate_hygiene",
                "privacy",
                "bodily_autonomy",
                "personal_boundaries",
                "abuse_prevention",
                "trusted_help",
            ],
        )
        self.assertTrue(lane["guaranteed_minimum_is_not_an_exhaustive_ceiling"])
        self.assertTrue(
            lane[
                "additional_age_appropriate_modules_require_separate_source_binding_and_approval"
            ]
        )
        self.assertFalse(lane["adult_curriculum_modules_inherited"])
        self.assertEqual(
            lane["required_body_representation"], "doll_safe_non_anatomical"
        )

    def test_adult_lane_still_does_not_imply_action(self) -> None:
        lane = self.policy["maturity_lanes"]["confirmed_adult"]
        self.assertTrue(lane["complete_health_curriculum_allowed"])
        self.assertEqual(
            lane["complete_health_curriculum_assignment"],
            "IMMEDIATE_ON_EXACT_CONFIRMED_ADULT_CLASSIFICATION",
        )
        self.assertEqual(
            set(lane["assignment_is_independent_of"]),
            {
                "relationship_status",
                "sexual_or_romantic_interest",
                "adult_anatomy_selection",
                "prior_experience",
                "spa_completion",
            },
        )
        self.assertFalse(lane["adult_action_or_relationship_permission_implied"])

    def test_female_routes_are_distinct(self) -> None:
        external = set(self.policy["semantic_body_systems"]["adult_female_external"])
        internal = set(self.policy["semantic_body_systems"]["adult_female_internal"])
        self.assertIn("external_urethral_opening", external)
        self.assertIn("vaginal_opening_introitus", external)
        self.assertIn("separate_anus", external)
        self.assertIn("separate_urinary_and_bowel_routes", internal)

    def test_male_routes_are_distinct(self) -> None:
        external = set(self.policy["semantic_body_systems"]["adult_male_external"])
        internal = set(self.policy["semantic_body_systems"]["adult_male_internal"])
        self.assertIn("penile_root_shaft_glans_and_urethral_meatus", external)
        self.assertIn("separate_anus", external)
        self.assertIn("separate_upstream_urinary_and_reproductive_states", internal)

    def test_consent_invariants_cover_false_shortcuts(self) -> None:
        rules = set(self.policy["relationship_and_consent_invariants"])
        self.assertIn("relationship_status_never_equals_consent", rules)
        self.assertIn("body_response_never_equals_desire_or_consent", rules)
        self.assertIn("prior_consent_never_equals_current_consent", rules)
        self.assertIn(
            "contraception_choice_is_voluntary_and_separate_from_sexual_consent",
            rules,
        )
        private = self.policy["private_sensation_and_solitary_choice"]
        self.assertTrue(
            private[
                "future_confirmed_adult_body_systems_must_support_person_owned_private_sensation_and_experience"
            ]
        )
        self.assertEqual(
            set(private["separate_truth_domains"]),
            {
                "physiological_body_response",
                "private_desire",
                "preference",
                "consent",
                "external_action",
                "health_state",
                "memory",
            },
        )
        self.assertFalse(private["adult_anatomy_is_consent"])
        self.assertFalse(private["physiological_arousal_is_consent_or_desire"])

    def test_all_six_phases_and_sources_are_present(self) -> None:
        phases = [row["id"] for row in self.policy["implementation_phases"]]
        self.assertEqual(
            phases,
            [
                "phase_0_sources",
                "phase_1_education",
                "phase_2_semantic_3d_anatomy",
                "phase_3_bathroom_and_cycle",
                "phase_4_confirmed_adult_sexual_health",
                "phase_5_pregnancy_delivery_family",
            ],
        )
        sources = self.policy["authoritative_starting_sources"]
        registry_sources = [
            row["url"] for row in self.registry["source_registry"]["records"]
        ]
        document_sources = evidence_base_urls(self.document)
        self.assertEqual(sources, EXPECTED_AUTHORITATIVE_SOURCE_URLS)
        self.assertEqual(registry_sources, EXPECTED_AUTHORITATIVE_SOURCE_URLS)
        self.assertEqual(document_sources, EXPECTED_AUTHORITATIVE_SOURCE_URLS)
        self.assertEqual(len(sources), 14)
        self.assertEqual(len(set(sources)), 14)
        self.assertTrue(all(value.startswith("https://") for value in sources))

    def test_current_truth_denies_unimplemented_systems(self) -> None:
        truth = self.policy["current_truth"]
        self.assertFalse(truth["internal_urinary_bowel_reproductive_simulation_implemented"])
        self.assertFalse(truth["menstrual_or_sexual_response_simulation_implemented"])
        self.assertFalse(
            truth["contraception_sti_pregnancy_delivery_hospital_systems_implemented"]
        )
        self.assertFalse(truth["curriculum_delivery_or_learning_memory_connected"])
        self.assertFalse(truth["private_sensation_state_runtime_connected"])
        self.assertFalse(truth["private_solitary_action_runtime_connected"])
        self.assertFalse(truth["this_plan_may_delay_immediate_owner_review_body"])

    def test_document_contains_controlling_truth_language(self) -> None:
        document = " ".join(self.document.lower().split())
        for phrase in (
            "A visually credible opening does not prove a canal",
            "Consent is not a permanent unlock",
            "A simulated symptom is not a diagnosis",
            "non-adults",
            "not currently implemented or accepted",
            "every exact person classified `confirmed_adult` is immediately assigned",
        ):
            self.assertIn(phrase.lower(), document)


if __name__ == "__main__":
    unittest.main()
