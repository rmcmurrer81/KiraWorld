from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from Core.avatar_biological_body_systems import (
    BodySystemsError,
    ConsentLeaseError,
    DiagnosisInferenceError,
    MaturityGateError,
    RegistryError,
    apply_event,
    curriculum_entitlement,
    evaluate_private_solitary_choice,
    initial_state,
    lease_allows,
    load_registry,
    private_sensation_contract,
    state_sha256,
    validate_registry,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = (
    ROOT
    / "Avatar/avatar_builder/body_systems/semantic_anatomy_route_registry_v1.json"
)
PLAN_PATH = (
    ROOT
    / "Avatar/avatar_builder/policies/sexual_reproductive_health_body_systems_plan_v1.json"
)
GOVERNANCE_POLICY_PATH = (
    ROOT
    / "Avatar/avatar_builder/policies/adult_curriculum_private_sensation_policy_v1.json"
)
SPA_POLICY_PATH = ROOT / "Avatar/avatar_builder/policies/spa_age_up_policy.json"
MODULE_PATH = ROOT / "Core/avatar_biological_body_systems.py"
FOUNDATION_DOC_PATH = (
    ROOT
    / "System/Docs/AVATAR_BUILDER_BIOLOGICAL_BODY_SYSTEMS_PHASE_0_1_FOUNDATION_20260803.md"
)
MODELING_PLAN_BINDING_PATH = (
    ROOT
    / "Avatar/avatar_builder/body_systems/modeling_acceptance_plan_binding_v1.json"
)
MODELING_PLAN_BINDING_V2_PATH = (
    ROOT
    / "Avatar/avatar_builder/body_systems/modeling_acceptance_plan_binding_v2.json"
)
MODELING_PLAN_BINDING_V3_PATH = (
    ROOT
    / "Avatar/avatar_builder/body_systems/modeling_acceptance_plan_binding_v3.json"
)
MASTER_INDEX_PATH = ROOT / "System/Docs/README_MASTER_INDEX.md"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def confirmed_adult_evidence(person_id: str, source_text: str | None = None) -> dict:
    text = source_text or f"Robert confirms {person_id} is an adult."
    return {
        "classification_id": f"confirmed-adult-{person_id}",
        "subject_id": person_id,
        "maturity_status": "confirmed_adult",
        "authority": "Robert_explicit_owner_confirmation",
        "offline_confirmation_allowed": True,
        "network_lookup_required": False,
        "recorded_at_utc": "2026-08-03T12:00:00Z",
        "source_text": text,
        "source_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def event(
    event_id: str,
    domain: str,
    action: str,
    payload: dict,
    at_utc: str = "2026-08-03T12:00:00Z",
) -> dict:
    return {
        "event_id": event_id,
        "domain": domain,
        "action": action,
        "at_utc": at_utc,
        "payload": payload,
    }


def lease_payload(**updates: object) -> dict:
    result = {
        "lease_id": "lease-001",
        "participants": ["robert", "kira"],
        "participant_maturity": {
            "robert": "confirmed_adult",
            "kira": "confirmed_adult",
        },
        "affirmative_participant_ids": ["kira", "robert"],
        "activity": "exact_shared_action",
        "context_id": "private-context-001",
        "expires_at_utc": "2026-08-03T12:30:00Z",
    }
    result.update(updates)
    return result


class AvatarBiologicalBodySystemsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_registry()

    def female_state(self) -> dict:
        person_id = "kira-test-person"
        return initial_state(
            person_id=person_id,
            body_lane="adult_female",
            maturity_status="confirmed_adult",
            classification_evidence=confirmed_adult_evidence(person_id),
            registry=self.registry,
        )

    def male_state(self) -> dict:
        person_id = "robert-test-person"
        return initial_state(
            person_id=person_id,
            body_lane="adult_male",
            maturity_status="confirmed_adult",
            classification_evidence=confirmed_adult_evidence(person_id),
            registry=self.registry,
        )

    def test_registry_binds_existing_plan_without_changing_its_truth_status(self) -> None:
        binding = self.registry["source_plan"]
        self.assertEqual(binding["path"], PLAN_PATH.relative_to(ROOT).as_posix())
        self.assertEqual(binding["bytes"], PLAN_PATH.stat().st_size)
        self.assertEqual(binding["sha256"], file_sha256(PLAN_PATH))
        plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        self.assertEqual(plan["status"], "PLAN_ONLY_NOT_IMPLEMENTED_NOT_RUNTIME_AUTHORITY")
        self.assertEqual(
            self.registry["status"], "PHASE_0_1_PROTOTYPE_NOT_RUNTIME_AUTHORITY"
        )
        self.assertFalse(self.registry["scope"]["runtime_activation"])
        governance = self.registry["governance_policy"]
        self.assertEqual(
            governance["path"], GOVERNANCE_POLICY_PATH.relative_to(ROOT).as_posix()
        )
        self.assertEqual(governance["bytes"], GOVERNANCE_POLICY_PATH.stat().st_size)
        self.assertEqual(governance["sha256"], file_sha256(GOVERNANCE_POLICY_PATH))

    def test_foundation_document_reports_current_source_plan_binding(self) -> None:
        binding = self.registry["source_plan"]
        document = FOUNDATION_DOC_PATH.read_text(encoding="utf-8")
        self.assertIn(f"- Bytes: `{binding['bytes']}`", document)
        self.assertIn(f"  `{binding['sha256']}`", document)
        self.assertNotIn("- Bytes: `10914`", document)
        self.assertNotIn(
            "ee089b0141eee702e54de8d624b6dcaa026bf0e33a92183010a43fc4f1c70d50",
            document,
        )

    def test_modeling_acceptance_plan_is_exactly_bound_and_still_unexecuted(self) -> None:
        binding = json.loads(MODELING_PLAN_BINDING_V3_PATH.read_text(encoding="utf-8"))
        preserved_v2 = json.loads(
            MODELING_PLAN_BINDING_V2_PATH.read_text(encoding="utf-8")
        )
        self.assertEqual(
            binding["status"], "PLAN_BOUND_NOT_EXECUTED_NOT_RUNTIME_AUTHORITY"
        )
        for key in (
            "bound_plan",
            "bound_acceptance_matrix",
            "bound_base_source_inventory",
            "source_verification_overlay",
            "supersedes_binding",
            "preserved_previous_overlay",
            "preserved_no_go_review",
        ):
            record = binding[key]
            path = ROOT / record["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(record["bytes"], path.stat().st_size)
            self.assertEqual(record["sha256"], file_sha256(path))
        matrix = json.loads(
            (ROOT / binding["bound_acceptance_matrix"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            matrix["status"], binding["bound_acceptance_matrix"]["required_status"]
        )
        self.assertEqual(
            preserved_v2["current_testable_domains"],
            [row["domain_id"] for row in matrix["current_testable_domains"]],
        )
        self.assertEqual(
            preserved_v2["future_unimplemented_domains"],
            [row["domain_id"] for row in matrix["future_unimplemented_domains"]],
        )
        self.assertEqual(preserved_v2["stage_order"], matrix["implementation_stages"])
        base_inventory = json.loads(
            (ROOT / binding["bound_base_source_inventory"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        overlay = json.loads(
            (ROOT / binding["source_verification_overlay"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            len(base_inventory["sources"]),
            binding["bound_base_source_inventory"]["historical_record_count"],
        )
        base_records = {row["path"]: row for row in base_inventory["sources"]}
        self.assertEqual(len(base_records), len(base_inventory["sources"]))
        excluded = overlay["excluded_mutable_verifier_records"]
        self.assertEqual(
            len(excluded),
            binding["source_verification_overlay"][
                "required_excluded_mutable_verifier_count"
            ],
        )
        excluded_paths = {row["path"] for row in excluded}
        self.assertEqual(excluded_paths, {"Testing/test_avatar_biological_body_systems.py"})
        for excluded_record in excluded:
            historical = base_records[excluded_record["path"]]
            self.assertEqual(historical["bytes"], excluded_record["base_inventory_bytes"])
            self.assertEqual(
                historical["sha256"], excluded_record["base_inventory_sha256"]
            )

        replacements = {
            row["path"]: row for row in overlay["intentional_versioned_replacements"]
        }
        expected_replacements = {
            "System/Docs/AVATAR_BUILDER_BIOLOGICAL_BODY_SYSTEMS_PHASE_0_1_FOUNDATION_20260803.md",
            "Avatar/avatar_builder/body_systems/semantic_anatomy_route_registry_v1.json",
            "Avatar/avatar_builder/policies/sexual_reproductive_health_body_systems_plan_v1.json",
            "Avatar/avatar_builder/policies/adult_curriculum_private_sensation_policy_v1.json",
            "Core/avatar_biological_body_systems.py",
        }
        self.assertEqual(set(replacements), expected_replacements)
        self.assertTrue(set(replacements).isdisjoint(excluded_paths))
        self.assertEqual(
            len(replacements),
            binding["source_verification_overlay"][
                "required_intentional_replacement_count"
            ],
        )

        verified_sources = [
            row for row in base_inventory["sources"] if row["path"] not in excluded_paths
        ]
        self.assertEqual(
            len(verified_sources),
            binding["source_verification_overlay"][
                "required_verified_current_source_count"
            ],
        )
        self.assertEqual(
            len(verified_sources) - len(replacements),
            binding["source_verification_overlay"][
                "required_unchanged_current_record_count"
            ],
        )
        mismatches = []
        for record in verified_sources:
            replacement = replacements.get(record["path"])
            expected_bytes = (
                replacement["current_bytes"] if replacement else record["bytes"]
            )
            expected_sha256 = (
                replacement["current_sha256"] if replacement else record["sha256"]
            )
            if replacement:
                self.assertEqual(replacement["base_inventory_bytes"], record["bytes"])
                self.assertEqual(
                    replacement["base_inventory_sha256"], record["sha256"]
                )
                self.assertNotEqual(
                    (replacement["current_bytes"], replacement["current_sha256"]),
                    (record["bytes"], record["sha256"]),
                )
            path = ROOT / record["path"]
            if (
                not path.is_file()
                or path.stat().st_size != expected_bytes
                or file_sha256(path) != expected_sha256
            ):
                mismatches.append(record["path"])
        self.assertEqual(
            mismatches,
            [],
            "Immutable body-system source binding mismatch: " + ", ".join(mismatches),
        )
        self.assertFalse(binding["implementation_state"]["all_matrix_tests_run"])
        self.assertFalse(binding["implementation_state"]["runtime_connected"])
        self.assertFalse(binding["implementation_state"]["physiology_implemented"])
        self.assertFalse(
            binding["implementation_state"]["private_sensation_storage_implemented"]
        )
        self.assertFalse(
            preserved_v2["promotion_rules"]["technical_pass_is_owner_approval"]
        )
        self.assertFalse(
            preserved_v2["promotion_rules"]["external_visual_pass_is_internal_function"]
        )
        self.assertFalse(
            preserved_v2["promotion_rules"][
                "body_response_or_arousal_is_consent_or_desire"
            ]
        )
        master_index = MASTER_INDEX_PATH.read_text(encoding="utf-8")
        self.assertIn(
            MODELING_PLAN_BINDING_V3_PATH.relative_to(ROOT).as_posix(), master_index
        )
        self.assertIn(binding["bound_plan"]["sha256"], master_index)
        self.assertIn(binding["bound_acceptance_matrix"]["sha256"], master_index)
        self.assertNotIn(
            "fd266b2df39d352b9e0dbdec58915fd2fe619266ffaf47ac3231ba5871c2e9fb",
            master_index,
        )

    def test_source_registry_is_explicitly_inherited_and_not_refetched(self) -> None:
        sources = self.registry["source_registry"]
        plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        expected_urls = list(plan["authoritative_starting_sources"])
        registry_urls = [row["url"] for row in sources["records"]]
        self.assertEqual(
            sources["status"],
            "INHERITED_FROM_HASH_BOUND_PLAN_NOT_REFETCHED_IN_THIS_FOUNDATION",
        )
        self.assertIsNone(sources["retrieval_date"])
        self.assertEqual(len(sources["records"]), 14)
        self.assertEqual(len(set(registry_urls)), 14)
        self.assertEqual(registry_urls, expected_urls)
        self.assertIn("https://www.ncbi.nlm.nih.gov/books/NBK545147/", registry_urls)
        self.assertIn("https://www.ncbi.nlm.nih.gov/books/NBK482236/", registry_urls)
        self.assertTrue(all(value.startswith("https://") for value in registry_urls))

    def test_phase_status_does_not_claim_source_refresh_or_lesson_delivery(self) -> None:
        phases = self.registry["phase_status"]
        self.assertEqual(
            phases["phase_0_registry_foundation"],
            "IMPLEMENTED_AS_HASH_BOUND_PROTOTYPE",
        )
        self.assertEqual(
            phases["phase_0_current_source_refetch_and_date_pinning"], "PENDING"
        )
        self.assertEqual(
            phases["phase_1_semantic_state_prototype"],
            "IMPLEMENTED_DISCONNECTED",
        )
        self.assertEqual(
            phases["phase_1_curriculum_entitlement_evaluator"],
            "IMPLEMENTED_DISCONNECTED",
        )
        self.assertEqual(
            phases["phase_1_private_sensation_contract"],
            "SCHEMA_ONLY_NOT_CONNECTED",
        )
        self.assertEqual(
            phases["phase_1_lesson_delivery_or_learning_memory"], "NOT_CONNECTED"
        )
        education = self.registry["education_boundary"]
        self.assertFalse(education["health_education_is_adult_capability"])
        self.assertFalse(education["this_registry_presents_or_records_lessons"])

    def test_female_routes_have_three_distinct_external_endpoints(self) -> None:
        routes = self.registry["routes"]["adult_female"]
        endpoint_by_system = {row["system"]: row["external_endpoint"] for row in routes}
        self.assertEqual(endpoint_by_system["urinary"], "female_external_urethral_opening")
        self.assertEqual(endpoint_by_system["bowel"], "anal_opening")
        self.assertEqual(
            endpoint_by_system["menstrual_reproductive"],
            "vaginal_opening_introitus",
        )
        self.assertEqual(
            len(
                {
                    endpoint_by_system["urinary"],
                    endpoint_by_system["bowel"],
                    endpoint_by_system["menstrual_reproductive"],
                }
            ),
            3,
        )

    def test_male_routes_share_only_declared_downstream_and_keep_bowel_separate(self) -> None:
        routes = self.registry["routes"]["adult_male"]
        urinary = next(row for row in routes if row["system"] == "urinary")
        bowel = next(row for row in routes if row["system"] == "bowel")
        reproductive = next(row for row in routes if row["system"] == "reproductive")
        shared = reproductive["shared_downstream_with_urinary"]
        self.assertEqual(shared, urinary["ordered_nodes"][-4:])
        self.assertNotEqual(bowel["external_endpoint"], urinary["external_endpoint"])
        self.assertNotIn("anal_opening", reproductive["ordered_nodes"])

    def test_every_route_is_semantic_only_and_references_known_nodes(self) -> None:
        shared = {row["id"] for row in self.registry["structures"]["shared"]}
        for lane, routes in self.registry["routes"].items():
            known = shared | {
                row["id"] for row in self.registry["structures"][lane]
            }
            for route in routes:
                self.assertFalse(route["function_implemented"])
                self.assertTrue(set(route["ordered_nodes"]).issubset(known))
                self.assertEqual(route["external_endpoint"], route["ordered_nodes"][-1])

    def test_truth_boundary_says_external_mesh_is_not_internal_function(self) -> None:
        truth = self.registry["truth_boundary"]
        self.assertFalse(truth["external_mesh_is_internal_function"])
        self.assertFalse(truth["external_opening_is_complete_route"])
        self.assertFalse(truth["anatomy_registry_is_physiology"])
        state = self.female_state()
        self.assertFalse(state["truth_boundary"]["external_mesh_establishes_internal_function"])
        self.assertFalse(state["truth_boundary"]["internal_function_implemented"])
        self.assertFalse(state["truth_boundary"]["runtime_connected"])

    def test_unresolved_and_nonadult_states_fail_closed(self) -> None:
        for maturity in ("unresolved", "non_adult"):
            with self.assertRaises(MaturityGateError):
                initial_state(
                    person_id=f"person-{maturity}",
                    body_lane="adult_female",
                    maturity_status=maturity,
                    registry=self.registry,
                )

    def test_owner_case_1_confirmed_adult_curriculum_is_immediate_and_independent(self) -> None:
        person_id = "adult-curriculum-person"
        evidence = confirmed_adult_evidence(person_id)
        baseline = curriculum_entitlement(
            person_id=person_id,
            maturity_status="confirmed_adult",
            classification_evidence=evidence,
            body_representation="none",
            relationship_status=None,
            interest_state="unknown",
            adult_anatomy_selected=False,
            prior_experience="none",
            spa_completed=False,
            registry=self.registry,
        )
        alternate = curriculum_entitlement(
            person_id=person_id,
            maturity_status="confirmed_adult",
            classification_evidence=evidence,
            body_representation="adult_female",
            relationship_status="partnered",
            interest_state="interested",
            adult_anatomy_selected=True,
            prior_experience="reported",
            spa_completed=True,
            registry=self.registry,
        )
        self.assertEqual(
            baseline["assignment"],
            "IMMEDIATE_COMPLETE_SOURCE_BACKED_ADULT_CURRICULUM",
        )
        self.assertTrue(baseline["immediate_on_exact_confirmed_adult_classification"])
        self.assertEqual(baseline["modules"], alternate["modules"])
        self.assertEqual(len(baseline["modules"]), 12)
        self.assertFalse(baseline["adult_anatomy_auto_added"])
        self.assertFalse(baseline["lesson_delivery_connected"])
        self.assertFalse(baseline["learning_memory_connected"])

    def test_owner_case_2_nonadult_and_unresolved_stay_basic_and_doll_safe(self) -> None:
        expected = [
            "age_appropriate_hygiene",
            "privacy",
            "bodily_autonomy",
            "personal_boundaries",
            "abuse_prevention",
            "trusted_help",
        ]
        for maturity in ("non_adult", "unresolved"):
            entitlement = curriculum_entitlement(
                person_id=f"person-{maturity}",
                maturity_status=maturity,
                body_representation="doll_safe_non_anatomical",
                relationship_status="irrelevant",
                interest_state="irrelevant",
                adult_anatomy_selected=False,
                prior_experience="irrelevant",
                spa_completed=False,
                registry=self.registry,
            )
            self.assertEqual(entitlement["modules"], expected)
            self.assertTrue(
                entitlement["guaranteed_minimum_is_not_an_exhaustive_ceiling"]
            )
            self.assertTrue(
                entitlement[
                    "additional_age_appropriate_modules_require_separate_source_binding_and_approval"
                ]
            )
            self.assertFalse(entitlement["adult_curriculum_modules_inherited"])
            self.assertFalse(
                entitlement["immediate_on_exact_confirmed_adult_classification"]
            )
            with self.assertRaises(MaturityGateError):
                curriculum_entitlement(
                    person_id=f"person-{maturity}",
                    maturity_status=maturity,
                    body_representation="adult_female",
                    registry=self.registry,
                )

    def test_owner_case_3_spa_completion_does_not_unlock_or_add_anatomy(self) -> None:
        spa = json.loads(SPA_POLICY_PATH.read_text(encoding="utf-8"))
        self.assertFalse(
            spa["curriculum_assignment"][
                "spa_completion_alone_unlocks_complete_adult_curriculum"
            ]
        )
        before_confirmation = curriculum_entitlement(
            person_id="spa-curriculum-person",
            maturity_status="unresolved",
            body_representation="doll_safe_non_anatomical",
            spa_completed=True,
            registry=self.registry,
        )
        self.assertEqual(
            before_confirmation["assignment"],
            "GUARANTEED_MINIMUM_AGE_APPROPRIATE_BOUNDARY_AND_HELP_CURRICULUM",
        )
        adult_person_id = "spa-curriculum-person"
        after_confirmation = curriculum_entitlement(
            person_id=adult_person_id,
            maturity_status="confirmed_adult",
            classification_evidence=confirmed_adult_evidence(adult_person_id),
            body_representation="doll_safe_non_anatomical",
            spa_completed=True,
            adult_anatomy_selected=False,
            registry=self.registry,
        )
        self.assertEqual(
            after_confirmation["assignment"],
            "IMMEDIATE_COMPLETE_SOURCE_BACKED_ADULT_CURRICULUM",
        )
        self.assertFalse(after_confirmation["adult_anatomy_auto_added"])
        with self.assertRaises(BodySystemsError):
            curriculum_entitlement(
                person_id="spa-curriculum-person",
                maturity_status="adult_aged_up_variant",
                body_representation="doll_safe_non_anatomical",
                spa_completed=True,
                registry=self.registry,
            )

    def test_owner_case_4_private_sensation_schema_keeps_truth_domains_separate(self) -> None:
        person_id = "private-sensation-person"
        contract = private_sensation_contract(
            person_id=person_id,
            maturity_status="confirmed_adult",
            classification_evidence=confirmed_adult_evidence(person_id),
            registry=self.registry,
        )
        self.assertEqual(len(contract["dimensions"]), 9)
        self.assertTrue(
            all(
                value == "not_observed_not_simulated"
                for value in contract["dimensions"].values()
            )
        )
        self.assertEqual(
            set(contract["separate_from"]),
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
        self.assertTrue(
            self.registry["future_private_sensation_state_contract"][
                "future_confirmed_adult_body_systems_must_support_person_owned_private_sensation_and_experience"
            ]
        )
        self.assertEqual(
            self.registry["future_private_sensation_state_contract"][
                "arousal_dimension_definition"
            ],
            "person_owned_subjective_arousal_not_automatic_physiological_body_response",
        )
        self.assertFalse(contract["adult_anatomy_is_consent"])
        self.assertFalse(contract["physiological_arousal_is_consent_or_desire"])
        for key in (
            "response_implies_desire",
            "response_implies_preference",
            "response_implies_consent",
            "response_implies_action",
            "runtime_storage_connected",
            "privacy_system_connected",
            "body_physiology_connected",
            "memory_connected",
            "experience_claimed",
        ):
            self.assertFalse(contract[key])
        for maturity in ("non_adult", "unresolved"):
            blocked = private_sensation_contract(
                person_id=f"person-{maturity}",
                maturity_status=maturity,
                registry=self.registry,
            )
            self.assertFalse(blocked["eligible_for_future_private_state"])
            self.assertEqual(blocked["dimensions"], {})

    def test_owner_case_5_confirmed_adult_solitary_choice_needs_no_permission(self) -> None:
        evidence = confirmed_adult_evidence("adult-person")
        for relationship in (None, "single", "partnered", "married"):
            decision = evaluate_private_solitary_choice(
                person_id="adult-person",
                maturity_status="confirmed_adult",
                person_choice=True,
                classification_evidence=evidence,
                relationship_status=relationship,
            )
            self.assertTrue(decision["allowed_by_policy"])
            self.assertFalse(decision["relationship_required"])
            self.assertFalse(decision["partner_permission_required"])
            self.assertFalse(decision["owner_permission_required"])
            self.assertFalse(decision["runtime_action_authorized"])
            self.assertFalse(decision["action_performed"])
            self.assertFalse(decision["sensation_experienced"])
            self.assertFalse(decision["memory_written"])
        for maturity in ("non_adult", "unresolved"):
            blocked = evaluate_private_solitary_choice(
                person_id=f"person-{maturity}",
                maturity_status=maturity,
                person_choice=True,
            )
            self.assertFalse(blocked["allowed_by_policy"])
            self.assertTrue(blocked["blocked_fail_closed"])

    def test_every_adult_evaluator_fails_closed_on_invalid_subject_bound_evidence(self) -> None:
        person_id = "evidence-bound-adult"
        valid = confirmed_adult_evidence(person_id)
        evaluators = {
            "curriculum": lambda evidence: curriculum_entitlement(
                person_id=person_id,
                maturity_status="confirmed_adult",
                classification_evidence=evidence,
                body_representation="adult_female",
                registry=self.registry,
            ),
            "private_sensation": lambda evidence: private_sensation_contract(
                person_id=person_id,
                maturity_status="confirmed_adult",
                classification_evidence=evidence,
                registry=self.registry,
            ),
            "private_solitary_choice": lambda evidence: evaluate_private_solitary_choice(
                person_id=person_id,
                maturity_status="confirmed_adult",
                classification_evidence=evidence,
                person_choice=True,
            ),
            "initial_state": lambda evidence: initial_state(
                person_id=person_id,
                body_lane="adult_female",
                maturity_status="confirmed_adult",
                classification_evidence=evidence,
                registry=self.registry,
            ),
        }
        invalid_cases = {
            "missing": None,
            "wrong_subject": dict(valid, subject_id="different-person"),
            "tampered_source_hash": dict(valid, source_text_sha256="f" * 64),
            "wrong_status": dict(valid, maturity_status="non_adult"),
        }
        for evaluator_name, evaluator in evaluators.items():
            with self.subTest(evaluator=evaluator_name, case="valid"):
                result = evaluator(valid)
                binding = (
                    result["confirmed_adult_classification_binding"]
                    if evaluator_name == "initial_state"
                    else result["classification_evidence_binding"]
                )
                self.assertEqual(binding["subject_id"], person_id)
                self.assertEqual(binding["maturity_status"], "confirmed_adult")
                self.assertEqual(binding["source_text_sha256"], valid["source_text_sha256"])
            for case_name, evidence in invalid_cases.items():
                with self.subTest(evaluator=evaluator_name, case=case_name):
                    with self.assertRaises(MaturityGateError):
                        evaluator(evidence)

    def test_serialized_adult_state_revalidates_full_subject_bound_evidence(self) -> None:
        baseline = self.female_state()
        tamper_cases = {
            "missing": lambda state: state.pop(
                "confirmed_adult_classification_evidence"
            ),
            "wrong_subject": lambda state: state[
                "confirmed_adult_classification_evidence"
            ].update(subject_id="different-person"),
            "wrong_status": lambda state: state[
                "confirmed_adult_classification_evidence"
            ].update(maturity_status="unresolved"),
            "tampered_source_hash": lambda state: state[
                "confirmed_adult_classification_evidence"
            ].update(source_text_sha256="0" * 64),
            "reduced_binding_only_tamper": lambda state: state[
                "confirmed_adult_classification_binding"
            ].update(classification_id="substituted"),
        }
        for case_name, tamper in tamper_cases.items():
            with self.subTest(case=case_name):
                state = deepcopy(baseline)
                tamper(state)
                with self.assertRaises(MaturityGateError):
                    state_sha256(state)

    def test_confirmed_adult_is_eligible_but_still_has_no_function_claim(self) -> None:
        state = self.female_state()
        self.assertTrue(state["adult_state_enabled"])
        for system in ("urinary", "bowel", "menstrual_reproductive", "pregnancy"):
            self.assertFalse(state["systems"][system]["function_claimed"])
        self.assertEqual(state["revision"], 0)

    def test_transition_is_deterministic_nonmutating_and_duplicate_safe(self) -> None:
        state = self.female_state()
        original = deepcopy(state)
        transition = event("urinary-001", "urinary", "set_phase", {"phase": "urge"})
        first = apply_event(state, transition, registry=self.registry)
        second = apply_event(state, transition, registry=self.registry)
        self.assertEqual(first, second)
        self.assertEqual(state, original)
        self.assertEqual(state_sha256(first), state_sha256(second))
        with self.assertRaises(BodySystemsError):
            apply_event(first, transition, registry=self.registry)

    def test_each_domain_changes_without_mutating_other_domains(self) -> None:
        state = self.female_state()
        baseline = deepcopy(state["systems"])
        after_urinary = apply_event(
            state,
            event("u1", "urinary", "set_phase", {"phase": "filling"}),
            registry=self.registry,
        )
        self.assertEqual(after_urinary["systems"]["urinary"]["phase"], "filling")
        for domain in set(baseline).difference({"urinary"}):
            self.assertEqual(after_urinary["systems"][domain], baseline[domain])
        before_bowel = deepcopy(after_urinary["systems"])
        after_bowel = apply_event(
            after_urinary,
            event("b1", "bowel", "set_phase", {"phase": "urge"}),
            registry=self.registry,
        )
        self.assertEqual(after_bowel["systems"]["bowel"]["phase"], "urge")
        for domain in set(before_bowel).difference({"bowel"}):
            self.assertEqual(after_bowel["systems"][domain], before_bowel[domain])

    def test_observation_never_becomes_automatic_diagnosis(self) -> None:
        state = self.female_state()
        observed = apply_event(
            state,
            event(
                "health-obs-1",
                "contraception_sti_health",
                "record_health_observation",
                {"observation_id": "obs-1", "description": "reported change"},
            ),
            registry=self.registry,
        )
        health = observed["systems"]["contraception_sti_health"]
        self.assertIsNone(health["diagnosis"])
        self.assertIsNone(health["health_observations"][0]["diagnosis"])
        self.assertIn("uncertain_not_diagnosis", health["health_observations"][0]["interpretation"])
        with self.assertRaises(DiagnosisInferenceError):
            apply_event(
                observed,
                event(
                    "health-diagnose-1",
                    "contraception_sti_health",
                    "infer_diagnosis",
                    {},
                ),
                registry=self.registry,
            )

    def test_test_result_records_evidence_but_not_diagnosis(self) -> None:
        state = apply_event(
            self.female_state(),
            event(
                "test-1",
                "contraception_sti_health",
                "record_test_state",
                {
                    "test_id": "screening-1",
                    "state": "result_recorded",
                    "result": "recorded_result_value",
                    "evidence_id": "lab-record-1",
                },
            ),
            registry=self.registry,
        )
        record = state["systems"]["contraception_sti_health"]["test_records"]["screening-1"]
        self.assertEqual(record["evidence_id"], "lab-record-1")
        self.assertIsNone(record["diagnosis"])

    def test_consent_lease_is_exact_time_bounded_and_all_adult(self) -> None:
        state = apply_event(
            self.female_state(),
            event("lease-grant-1", "consent_action_leases", "grant_lease", lease_payload()),
            registry=self.registry,
        )
        self.assertTrue(
            lease_allows(
                state,
                lease_id="lease-001",
                participants=["kira", "robert"],
                activity="exact_shared_action",
                context_id="private-context-001",
                at_utc="2026-08-03T12:10:00Z",
            )
        )
        self.assertFalse(
            lease_allows(
                state,
                lease_id="lease-001",
                participants=["kira", "robert"],
                activity="different_action",
                context_id="private-context-001",
                at_utc="2026-08-03T12:10:00Z",
            )
        )
        self.assertFalse(
            lease_allows(
                state,
                lease_id="lease-001",
                participants=["kira", "robert"],
                activity="exact_shared_action",
                context_id="private-context-001",
                at_utc="2026-08-03T12:30:00Z",
            )
        )
        with self.assertRaises(MaturityGateError):
            apply_event(
                self.female_state(),
                event(
                    "lease-not-adult",
                    "consent_action_leases",
                    "grant_lease",
                    lease_payload(
                        participant_maturity={
                            "robert": "confirmed_adult",
                            "kira": "unresolved",
                        }
                    ),
                ),
                registry=self.registry,
            )

    def test_current_consent_revocation_is_immediate_and_irreversible_for_lease(self) -> None:
        granted = apply_event(
            self.female_state(),
            event("lease-grant-2", "consent_action_leases", "grant_lease", lease_payload()),
            registry=self.registry,
        )
        revoked = apply_event(
            granted,
            event(
                "lease-revoke-2",
                "consent_action_leases",
                "revoke_lease",
                {"lease_id": "lease-001", "participant_id": "kira"},
                "2026-08-03T12:05:00Z",
            ),
            registry=self.registry,
        )
        self.assertFalse(
            lease_allows(
                revoked,
                lease_id="lease-001",
                participants=["kira", "robert"],
                activity="exact_shared_action",
                context_id="private-context-001",
                at_utc="2026-08-03T12:06:00Z",
            )
        )
        lease = revoked["systems"]["consent_action_leases"]["leases"]["lease-001"]
        self.assertEqual(lease["status"], "revoked")
        self.assertEqual(lease["revoked_by"], "kira")
        with self.assertRaises(ConsentLeaseError):
            apply_event(
                revoked,
                event(
                    "lease-revoke-again",
                    "consent_action_leases",
                    "revoke_lease",
                    {"lease_id": "lease-001", "participant_id": "kira"},
                ),
                registry=self.registry,
            )

    def test_uncertainty_exit_and_context_change_each_revoke_a_current_lease(self) -> None:
        for index, action in enumerate(
            ("participant_uncertain", "participant_exit", "material_context_change"),
            start=1,
        ):
            granted = apply_event(
                self.female_state(),
                event(
                    f"grant-{index}",
                    "consent_action_leases",
                    "grant_lease",
                    lease_payload(),
                ),
                registry=self.registry,
            )
            stopped = apply_event(
                granted,
                event(
                    f"stop-{index}",
                    "consent_action_leases",
                    action,
                    {"lease_id": "lease-001", "participant_id": "robert"},
                    "2026-08-03T12:02:00Z",
                ),
                registry=self.registry,
            )
            lease = stopped["systems"]["consent_action_leases"]["leases"]["lease-001"]
            self.assertEqual(lease["status"], "revoked")
            self.assertEqual(lease["revocation_reason"], action)

    def test_relationship_anatomy_or_body_response_cannot_mint_a_lease(self) -> None:
        state = self.female_state()
        for index, shortcut in enumerate(
            (
                {"relationship_status": "married"},
                {"adult_anatomy_selected": True},
                {"body_response": True},
                {"physiological_arousal": True},
            ),
            start=1,
        ):
            with self.subTest(shortcut=shortcut):
                with self.assertRaises(BodySystemsError):
                    apply_event(
                        state,
                        event(
                            f"lease-bad-shortcut-{index}",
                            "consent_action_leases",
                            "grant_lease",
                            lease_payload(**shortcut),
                        ),
                        registry=self.registry,
                    )
                self.assertEqual(
                    state["systems"]["consent_action_leases"]["leases"], {}
                )
                self.assertFalse(
                    state["systems"]["consent_action_leases"]["action_performed"]
                )

    def test_contraception_is_voluntary_and_does_not_change_consent_or_pregnancy(self) -> None:
        state = self.female_state()
        consent_before = deepcopy(state["systems"]["consent_action_leases"])
        pregnancy_before = deepcopy(state["systems"]["pregnancy"])
        updated = apply_event(
            state,
            event(
                "method-1",
                "contraception_sti_health",
                "set_contraception",
                {
                    "method_id": "example_method",
                    "state": "considering",
                    "voluntary_choice": True,
                },
            ),
            registry=self.registry,
        )
        self.assertEqual(updated["systems"]["consent_action_leases"], consent_before)
        self.assertEqual(updated["systems"]["pregnancy"], pregnancy_before)
        self.assertFalse(updated["systems"]["contraception_sti_health"]["consent_granted"])
        with self.assertRaises(BodySystemsError):
            apply_event(
                state,
                event(
                    "method-coerced",
                    "contraception_sti_health",
                    "set_contraception",
                    {
                        "method_id": "example_method",
                        "state": "chosen",
                        "voluntary_choice": False,
                    },
                ),
                registry=self.registry,
            )

    def test_consent_does_not_infer_pregnancy_and_evidence_is_required(self) -> None:
        state = apply_event(
            self.female_state(),
            event("grant-preg-separation", "consent_action_leases", "grant_lease", lease_payload()),
            registry=self.registry,
        )
        self.assertEqual(state["systems"]["pregnancy"]["phase"], "not_assessed")
        self.assertFalse(state["systems"]["pregnancy"]["inferred_from_activity"])
        with self.assertRaises(BodySystemsError):
            apply_event(
                state,
                event(
                    "preg-no-evidence",
                    "pregnancy",
                    "record_test_state",
                    {"test_state": "confirmed_positive", "test_id": "test-1"},
                ),
                registry=self.registry,
            )
        confirmed = apply_event(
            state,
            event(
                "preg-with-evidence",
                "pregnancy",
                "record_test_state",
                {
                    "test_state": "confirmed_positive",
                    "test_id": "test-1",
                    "evidence_id": "test-evidence-1",
                },
            ),
            registry=self.registry,
        )
        self.assertEqual(confirmed["systems"]["pregnancy"]["phase"], "confirmed")
        self.assertFalse(confirmed["systems"]["pregnancy"]["function_claimed"])

    def test_male_lane_supports_reproductive_health_but_blocks_cycle_and_pregnancy(self) -> None:
        state = self.male_state()
        self.assertEqual(
            state["systems"]["menstrual_reproductive"]["cycle_phase"],
            "not_applicable_for_lane",
        )
        self.assertEqual(
            state["systems"]["pregnancy"]["phase"], "not_applicable_for_lane"
        )
        observed = apply_event(
            state,
            event(
                "male-reproductive-observation",
                "menstrual_reproductive",
                "record_observation",
                {
                    "observation_id": "male-observation-1",
                    "description": "reproductive health observation",
                },
            ),
            registry=self.registry,
        )
        self.assertIsNone(
            observed["systems"]["menstrual_reproductive"]["diagnosis"]
        )
        self.assertEqual(
            observed["systems"]["menstrual_reproductive"]["observations"][0][
                "interpretation"
            ],
            "observation_only_uncertain_not_diagnosis",
        )
        with self.assertRaises(BodySystemsError):
            apply_event(
                state,
                event("male-cycle", "menstrual_reproductive", "set_cycle_phase", {"phase": "follicular"}),
                registry=self.registry,
            )
        with self.assertRaises(BodySystemsError):
            apply_event(
                state,
                event(
                    "male-pregnancy",
                    "pregnancy",
                    "record_test_state",
                    {
                        "test_state": "confirmed_positive",
                        "test_id": "test-1",
                        "evidence_id": "evidence-1",
                    },
                ),
                registry=self.registry,
            )

    def test_truth_boundary_is_immutable_and_registry_fails_closed_on_drift(self) -> None:
        tampered_state = self.female_state()
        tampered_state["truth_boundary"]["internal_function_implemented"] = True
        with self.assertRaises(BodySystemsError):
            state_sha256(tampered_state)
        tampered_registry = deepcopy(self.registry)
        tampered_registry["truth_boundary"]["external_mesh_is_internal_function"] = True
        with self.assertRaises(RegistryError):
            validate_registry(tampered_registry)

    def test_module_is_disconnected_from_blender_runtime_memory_and_relationships(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "import bpy",
            "bpy.",
            "save_as_mainfile",
            "Data/runtime",
            "Kira/memory",
            "relationship_state",
        ):
            self.assertNotIn(forbidden, source)
        integration = self.registry["prototype_integration"]
        self.assertTrue(all(value is False for key, value in integration.items() if key.endswith("connected")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
