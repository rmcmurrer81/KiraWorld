"""Fail-closed, source-bound adult health knowledge context for local people.

This module connects curated educational facts to a conversation prompt.  It
does not mark a lesson complete, write memory, add anatomy, simulate body
function, diagnose anyone, or authorize an activity.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from Core.avatar_biological_body_systems import (
    MaturityGateError,
    curriculum_entitlement,
    validate_confirmed_adult_classification_evidence,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURRICULUM_PATH = (
    PROJECT_ROOT
    / "System/Knowledge/confirmed_adult_sexual_reproductive_health_curriculum_v1.json"
)
PERSON_CLASSIFICATION_PATHS = {
    "kira": (
        PROJECT_ROOT
        / "Data/person_classification/kira_confirmed_adult_owner_classification_20260809.json"
    ),
    "lisa": (
        PROJECT_ROOT
        / "Data/person_classification/lisa_confirmed_adult_owner_classification_20260809.json"
    ),
    "emily_carter_ai_and_computer_programming_expert_20260605_220651": (
        PROJECT_ROOT
        / "Data/person_classification/emily_carter_ai_and_computer_programming_expert_20260605_220651_confirmed_adult_owner_classification_20260809.json"
    ),
    "jessica_hale_robotics_engineer_20260611_041314": (
        PROJECT_ROOT
        / "Data/person_classification/jessica_hale_robotics_engineer_20260611_041314_confirmed_adult_owner_classification_20260809.json"
    ),
    "laura_mitchell_new_jersey_criminal_attorney_expert_20260605_195530": (
        PROJECT_ROOT
        / "Data/person_classification/laura_mitchell_new_jersey_criminal_attorney_expert_20260605_195530_confirmed_adult_owner_classification_20260809.json"
    ),
    "ryan_hale_quantum_mechanics_expert_20260608_200749": (
        PROJECT_ROOT
        / "Data/person_classification/ryan_hale_quantum_mechanics_expert_20260608_200749_confirmed_adult_owner_classification_20260809.json"
    ),
    "sarah_bennett_entertainment_pr_agent_expert_20260606_171637": (
        PROJECT_ROOT
        / "Data/person_classification/sarah_bennett_entertainment_pr_agent_expert_20260606_171637_confirmed_adult_owner_classification_20260809.json"
    ),
}
EXACT_GENERATED_EXPERT_CANDIDATE_IDS = (
    "emily_carter_ai_and_computer_programming_expert_20260605_220651",
    "jessica_hale_robotics_engineer_20260611_041314",
    "laura_mitchell_new_jersey_criminal_attorney_expert_20260605_195530",
    "ryan_hale_quantum_mechanics_expert_20260608_200749",
    "sarah_bennett_entertainment_pr_agent_expert_20260606_171637",
)
EXPERT_ADULT_DIRECTIVE_BINDING = {
    "path": (
        "Avatar/avatar_builder/policies/evidence/"
        "generated_experts_adult_owner_directive_20260716.json"
    ),
    "sha256": "ea7218ece3c5e187020e53ba77bfa11dcfacdb344c8714f17d38f2a02e56386b",
    "evidence_id": "generated_experts_adult_owner_directive_20260716",
    "directive": "All generated expert TemporaryAI profiles are adults.",
    "directive_sha256": "f534181f2fb58bb04ada09659d6e0dd32f8611e24b0a87d01b20a66461441f71",
}
EXPERT_CURRICULUM_EXTENSION_BINDING = {
    "path": (
        "Data/person_classification/"
        "generated_expert_adult_curriculum_owner_extension_20260809.json"
    ),
    "sha256": "e1a09a41314380328db79a7335607350feff8d9876b30d78a8fe9352b6452ea1",
    "evidence_id": (
        "generated_expert_adult_curriculum_owner_extension_"
        "20260809_d2c32a5b4eed8ef2"
    ),
    "source_text": (
        "All experts are adults and adults have sex education knowledge "
        "that you already gave to kira."
    ),
    "source_text_sha256": (
        "d2c32a5b4eed8ef21c7744544fe1929e73d4aa219bf8f5714e7d01df69d752d9"
    ),
}
PERSON_CLASSIFICATION_BINDINGS = {
    "kira": {
        "path": PERSON_CLASSIFICATION_PATHS["kira"],
        "sha256": (
            "04ac19e026b168cb1942d73598b7c13f2b4ee7a49452f8ddf32763cf5de9e346"
        ),
        "classification_id": (
            "kira_confirmed_adult_owner_20260809_969c08ddbcfc33bc"
        ),
        "source_text_sha256": (
            "969c08ddbcfc33bced10c3128b1e95a8ccd45789706b4c7f31e9787f6bb92422"
        ),
    },
    "lisa": {
        "path": PERSON_CLASSIFICATION_PATHS["lisa"],
        "sha256": (
            "5d13762ef340522ff82a74241557cec2724a3bdeaf841179b54f32b5c3a2d64c"
        ),
        "classification_id": (
            "lisa_confirmed_adult_owner_20260809_cb6430bda0f7d41e"
        ),
        "source_text_sha256": (
            "cb6430bda0f7d41eddf10b82676daa1913e52c39a51e0fb2cba2cf437ed35233"
        ),
    },
    "emily_carter_ai_and_computer_programming_expert_20260605_220651": {
        "path": PERSON_CLASSIFICATION_PATHS[
            "emily_carter_ai_and_computer_programming_expert_20260605_220651"
        ],
        "sha256": "f19c84fec230717e1cc6f288cf57314bdadbb1816a86730440f2c6ca93f8e1c2",
        "classification_id": (
            "emily_carter_ai_and_computer_programming_expert_20260605_220651_"
            "confirmed_adult_owner_20260809_d2c32a5b4eed8ef2"
        ),
        "source_text_sha256": EXPERT_CURRICULUM_EXTENSION_BINDING[
            "source_text_sha256"
        ],
        "exact_generated_expert_directives_required": True,
    },
    "jessica_hale_robotics_engineer_20260611_041314": {
        "path": PERSON_CLASSIFICATION_PATHS[
            "jessica_hale_robotics_engineer_20260611_041314"
        ],
        "sha256": "fb1a898874ca038d58a6fc45420726cfec06a71c3420b89e4e5c1c7c4e2904b2",
        "classification_id": (
            "jessica_hale_robotics_engineer_20260611_041314_"
            "confirmed_adult_owner_20260809_d2c32a5b4eed8ef2"
        ),
        "source_text_sha256": EXPERT_CURRICULUM_EXTENSION_BINDING[
            "source_text_sha256"
        ],
        "exact_generated_expert_directives_required": True,
    },
    "laura_mitchell_new_jersey_criminal_attorney_expert_20260605_195530": {
        "path": PERSON_CLASSIFICATION_PATHS[
            "laura_mitchell_new_jersey_criminal_attorney_expert_20260605_195530"
        ],
        "sha256": "07ea9dc4b97df02fc3f7f513f2f595ff8c92e50fc96f75448b98576bc845be00",
        "classification_id": (
            "laura_mitchell_new_jersey_criminal_attorney_expert_"
            "20260605_195530_confirmed_adult_owner_20260809_d2c32a5b4eed8ef2"
        ),
        "source_text_sha256": EXPERT_CURRICULUM_EXTENSION_BINDING[
            "source_text_sha256"
        ],
        "exact_generated_expert_directives_required": True,
    },
    "ryan_hale_quantum_mechanics_expert_20260608_200749": {
        "path": PERSON_CLASSIFICATION_PATHS[
            "ryan_hale_quantum_mechanics_expert_20260608_200749"
        ],
        "sha256": "b1baa5d6a57ceb9378b6e2304e8ba5d96e8210f74081d00905a832c5a11a4a21",
        "classification_id": (
            "ryan_hale_quantum_mechanics_expert_20260608_200749_"
            "confirmed_adult_owner_20260809_d2c32a5b4eed8ef2"
        ),
        "source_text_sha256": EXPERT_CURRICULUM_EXTENSION_BINDING[
            "source_text_sha256"
        ],
        "exact_generated_expert_directives_required": True,
    },
    "sarah_bennett_entertainment_pr_agent_expert_20260606_171637": {
        "path": PERSON_CLASSIFICATION_PATHS[
            "sarah_bennett_entertainment_pr_agent_expert_20260606_171637"
        ],
        "sha256": "093bfd7a7fdbff03e48ff9197efdf6a49d553b05acfb98102b372d4232c5dcef",
        "classification_id": (
            "sarah_bennett_entertainment_pr_agent_expert_20260606_171637_"
            "confirmed_adult_owner_20260809_d2c32a5b4eed8ef2"
        ),
        "source_text_sha256": EXPERT_CURRICULUM_EXTENSION_BINDING[
            "source_text_sha256"
        ],
        "exact_generated_expert_directives_required": True,
    },
}
EXPECTED_STATUS = (
    "SOURCE_BOUND_RUNTIME_KNOWLEDGE_CONTEXT_CONNECTED_"
    "LESSON_MEMORY_AND_BODY_FUNCTION_NOT_CLAIMED"
)
POLICY_MODULE_IDS = frozenset(
    {
        "adult_anatomy_normal_variation_and_source_literacy",
        "hygiene_privacy_bodily_autonomy_and_boundaries",
        "urinary_bowel_pelvic_and_reproductive_health",
        "puberty_cycles_menstruation_and_adult_life_stages",
        "consent_communication_and_relationships",
        "physiological_response_sensation_pleasure_and_preference_separation",
        "private_solitary_self_discovery_and_self_pleasure",
        "contraception_and_barrier_methods",
        "sti_prevention_testing_and_health_uncertainty",
        "conception_fertility_pregnancy_delivery_postpartum_and_family_choices",
        "medical_care_symptoms_tests_diagnosis_treatment_and_recovery",
        "correction_source_recall_uncertainty_and_help_seeking",
    }
)
BASELINE_MODULE_IDS = (
    "adult_anatomy_normal_variation_and_source_literacy",
    "consent_communication_and_relationships",
    "correction_source_recall_uncertainty_and_help_seeking",
)
MAX_SELECTED_MODULES = 6


class AdultHealthCurriculumError(ValueError):
    """The bound classification or curriculum cannot be trusted."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AdultHealthCurriculumError(
            f"unable to read curriculum-bound JSON: {path.name}"
        ) from exc
    if not isinstance(value, dict):
        raise AdultHealthCurriculumError(f"expected JSON object: {path.name}")
    return value


def _project_relative_path(raw: str) -> Path:
    value = Path(str(raw or ""))
    if not raw or value.is_absolute() or ".." in value.parts:
        raise AdultHealthCurriculumError("curriculum binding path is unsafe")
    resolved = (PROJECT_ROOT / value).resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise AdultHealthCurriculumError(
            "curriculum binding escaped the project root"
        ) from exc
    return resolved


def _read_pinned_project_json(
    binding: Mapping[str, Any],
    *,
    label: str,
) -> tuple[Path, dict[str, Any]]:
    path = _project_relative_path(str(binding.get("path") or ""))
    expected_sha = str(binding.get("sha256") or "").strip().casefold()
    if len(expected_sha) != 64 or any(
        character not in "0123456789abcdef" for character in expected_sha
    ):
        raise AdultHealthCurriculumError(f"{label} pinned digest is invalid")
    if _sha256_file(path) != expected_sha:
        raise AdultHealthCurriculumError(f"{label} pinned digest mismatch")
    return path, _read_json(path)


def _validate_exact_generated_expert_directives(
    *,
    person_id: str,
    classification: Mapping[str, Any],
) -> None:
    """Prove exact-list owner authority without trusting role/name inference."""

    person = str(person_id).strip().casefold()
    if person not in EXACT_GENERATED_EXPERT_CANDIDATE_IDS:
        raise AdultHealthCurriculumError(
            "person is not in the externally pinned generated-expert exact list"
        )
    evidence_binding = classification.get("owner_directive_binding")
    if not isinstance(evidence_binding, Mapping):
        raise AdultHealthCurriculumError(
            "generated-expert owner directive binding is missing"
        )

    failures: list[str] = []
    if str(evidence_binding.get("candidate_id") or "").casefold() != person:
        failures.append("candidate_id_mismatch")
    expected_fields = {
        "adult_directive_path": EXPERT_ADULT_DIRECTIVE_BINDING["path"],
        "adult_directive_sha256": EXPERT_ADULT_DIRECTIVE_BINDING["sha256"],
        "adult_directive_evidence_id": EXPERT_ADULT_DIRECTIVE_BINDING[
            "evidence_id"
        ],
        "curriculum_extension_path": EXPERT_CURRICULUM_EXTENSION_BINDING[
            "path"
        ],
        "curriculum_extension_sha256": EXPERT_CURRICULUM_EXTENSION_BINDING[
            "sha256"
        ],
        "curriculum_extension_evidence_id": (
            EXPERT_CURRICULUM_EXTENSION_BINDING["evidence_id"]
        ),
    }
    for key, expected in expected_fields.items():
        if str(evidence_binding.get(key) or "").casefold() != str(
            expected
        ).casefold():
            failures.append(f"classification_binding_mismatch:{key}")

    _, adult_directive = _read_pinned_project_json(
        EXPERT_ADULT_DIRECTIVE_BINDING,
        label="generated-expert adult directive",
    )
    _, curriculum_extension = _read_pinned_project_json(
        EXPERT_CURRICULUM_EXTENSION_BINDING,
        label="generated-expert curriculum extension",
    )
    exact_ids = list(EXACT_GENERATED_EXPERT_CANDIDATE_IDS)
    if adult_directive.get("schema_version") != 1:
        failures.append("adult_directive_schema_invalid")
    if adult_directive.get("evidence_id") != EXPERT_ADULT_DIRECTIVE_BINDING[
        "evidence_id"
    ]:
        failures.append("adult_directive_id_mismatch")
    if adult_directive.get("directive") != EXPERT_ADULT_DIRECTIVE_BINDING[
        "directive"
    ]:
        failures.append("adult_directive_text_mismatch")
    if hashlib.sha256(
        str(adult_directive.get("directive") or "").encode("utf-8")
    ).hexdigest() != EXPERT_ADULT_DIRECTIVE_BINDING["directive_sha256"]:
        failures.append("adult_directive_text_digest_mismatch")
    if adult_directive.get("candidate_ids") != exact_ids:
        failures.append("adult_directive_exact_candidate_list_mismatch")
    if adult_directive.get("scope") != "avatar_identity_and_topology_routing_only":
        failures.append("adult_directive_original_scope_mismatch")

    if curriculum_extension.get("schema_version") != 1:
        failures.append("curriculum_extension_schema_invalid")
    if curriculum_extension.get("evidence_id") != (
        EXPERT_CURRICULUM_EXTENSION_BINDING["evidence_id"]
    ):
        failures.append("curriculum_extension_id_mismatch")
    if curriculum_extension.get("source_text") != (
        EXPERT_CURRICULUM_EXTENSION_BINDING["source_text"]
    ):
        failures.append("curriculum_extension_source_text_mismatch")
    if curriculum_extension.get("source_text_sha256") != (
        EXPERT_CURRICULUM_EXTENSION_BINDING["source_text_sha256"]
    ):
        failures.append("curriculum_extension_source_digest_mismatch")
    if curriculum_extension.get("exact_candidate_ids") != exact_ids:
        failures.append("curriculum_extension_exact_candidate_list_mismatch")
    existing = curriculum_extension.get("existing_exact_adulthood_directive")
    if not isinstance(existing, Mapping):
        failures.append("curriculum_extension_adulthood_binding_missing")
    else:
        for key in ("path", "sha256", "evidence_id", "directive", "directive_sha256"):
            if str(existing.get(key) or "").casefold() != str(
                EXPERT_ADULT_DIRECTIVE_BINDING[key]
            ).casefold():
                failures.append(f"curriculum_extension_adulthood_binding_mismatch:{key}")
    scope = curriculum_extension.get("scope")
    if not isinstance(scope, Mapping):
        failures.append("curriculum_extension_scope_missing")
    else:
        required_scope = {
            "exact_list_only": True,
            "future_or_unlisted_experts_auto_classified": False,
            "occupation_name_gender_or_ui_label_is_maturity_evidence": False,
            "maturity_status": "confirmed_adult",
            "curriculum_assignment": (
                "IMMEDIATE_COMPLETE_SOURCE_BACKED_ADULT_CURRICULUM"
            ),
        }
        for key, expected in required_scope.items():
            if scope.get(key) != expected:
                failures.append(f"curriculum_extension_scope_mismatch:{key}")
    truth = curriculum_extension.get("truth_boundaries")
    required_false = (
        "source_context_eligibility_is_lesson_completion",
        "source_context_eligibility_is_learning_memory",
        "confirmed_adult_classification_adds_anatomy",
        "confirmed_adult_classification_proves_body_function",
        "confirmed_adult_classification_creates_consent",
        "confirmed_adult_classification_authorizes_external_action",
        "body_response_is_desire_preference_or_consent",
        "relationship_status_is_consent",
        "runtime_activation_allowed",
    )
    if not isinstance(truth, Mapping):
        failures.append("curriculum_extension_truth_boundaries_missing")
    else:
        for key in required_false:
            if truth.get(key) is not False:
                failures.append(f"curriculum_extension_truth_boundary_drift:{key}")

    if classification.get("source_text") != EXPERT_CURRICULUM_EXTENSION_BINDING[
        "source_text"
    ]:
        failures.append("classification_source_text_mismatch")
    effects = classification.get("effects")
    required_effects = {
        "knowledge_context_eligible": True,
        "lesson_completion_claimed": False,
        "learning_memory_created": False,
        "adult_anatomy_auto_added": False,
        "body_function_claimed": False,
        "relationship_or_activity_permission_created": False,
        "external_action_authorized": False,
        "runtime_activation_allowed": False,
    }
    if not isinstance(effects, Mapping):
        failures.append("classification_effects_missing")
    else:
        for key, expected in required_effects.items():
            if effects.get(key) is not expected:
                failures.append(f"classification_effect_mismatch:{key}")
    if failures:
        raise AdultHealthCurriculumError(
            "generated-expert exact owner bindings failed: " + "; ".join(failures)
        )


def validate_curriculum_asset(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate source and truth boundaries without trusting caller claims."""

    data = deepcopy(dict(value))
    failures: list[str] = []
    if data.get("schema_version") != 1:
        failures.append("schema_version_invalid")
    if data.get("curriculum_id") != (
        "confirmed_adult_sexual_reproductive_health_curriculum_v1"
    ):
        failures.append("curriculum_id_invalid")
    if data.get("status") != EXPECTED_STATUS:
        failures.append("status_invalid")
    if data.get("audience") != "exact_subject_bound_confirmed_adults_only":
        failures.append("audience_invalid")

    truth = data.get("truth_boundaries")
    required_false = {
        "knowledge_context_is_lesson_completion",
        "knowledge_context_is_learning_memory",
        "knowledge_context_adds_anatomy",
        "knowledge_context_proves_body_function",
        "knowledge_context_is_medical_diagnosis_or_treatment",
        "body_response_is_desire_preference_or_consent",
        "relationship_status_is_consent",
        "adult_classification_authorizes_external_action",
    }
    if not isinstance(truth, Mapping):
        failures.append("truth_boundaries_missing")
    else:
        for key in sorted(required_false):
            if truth.get(key) is not False:
                failures.append(f"truth_boundary_not_false:{key}")
        if truth.get(
            "medical_recommendations_require_current_person_specific_clinical_context"
        ) is not True:
            failures.append("person_specific_clinical_boundary_missing")

    sources = data.get("sources")
    source_ids: set[str] = set()
    if not isinstance(sources, list) or not sources:
        failures.append("sources_missing")
        sources = []
    for index, source in enumerate(sources):
        if not isinstance(source, Mapping):
            failures.append(f"source_not_object:{index}")
            continue
        source_id = str(source.get("source_id") or "").strip()
        if not source_id or source_id in source_ids:
            failures.append(f"source_id_invalid_or_duplicate:{index}")
        else:
            source_ids.add(source_id)
        if not str(source.get("publisher") or "").strip():
            failures.append(f"source_publisher_missing:{index}")
        if not str(source.get("title") or "").strip():
            failures.append(f"source_title_missing:{index}")
        if not str(source.get("url") or "").startswith("https://"):
            failures.append(f"source_url_invalid:{index}")
        if not str(source.get("reviewed_at_utc") or "").endswith("Z"):
            failures.append(f"source_review_time_invalid:{index}")

    modules = data.get("modules")
    module_ids: set[str] = set()
    if not isinstance(modules, list) or not modules:
        failures.append("modules_missing")
        modules = []
    for index, module in enumerate(modules):
        if not isinstance(module, Mapping):
            failures.append(f"module_not_object:{index}")
            continue
        module_id = str(module.get("module_id") or "").strip()
        if not module_id or module_id in module_ids:
            failures.append(f"module_id_invalid_or_duplicate:{index}")
        else:
            module_ids.add(module_id)
        keywords = module.get("keywords")
        if not isinstance(keywords, list) or not keywords or not all(
            isinstance(item, str) and item.strip() for item in keywords
        ):
            failures.append(f"module_keywords_invalid:{module_id or index}")
        facts = module.get("facts")
        if not isinstance(facts, list) or not facts:
            failures.append(f"module_facts_missing:{module_id or index}")
            continue
        fact_ids: set[str] = set()
        for fact_index, fact in enumerate(facts):
            if not isinstance(fact, Mapping):
                failures.append(
                    f"fact_not_object:{module_id or index}:{fact_index}"
                )
                continue
            fact_id = str(fact.get("fact_id") or "").strip()
            if not fact_id or fact_id in fact_ids:
                failures.append(
                    f"fact_id_invalid_or_duplicate:{module_id or index}:{fact_index}"
                )
            else:
                fact_ids.add(fact_id)
            if not str(fact.get("text") or "").strip():
                failures.append(f"fact_text_missing:{fact_id or fact_index}")
            bindings = fact.get("source_ids")
            if not isinstance(bindings, list) or not bindings:
                failures.append(f"fact_sources_missing:{fact_id or fact_index}")
            elif any(str(item) not in source_ids for item in bindings):
                failures.append(f"fact_source_unknown:{fact_id or fact_index}")

    missing_modules = sorted(POLICY_MODULE_IDS - module_ids)
    if missing_modules:
        failures.append("policy_modules_missing:" + ",".join(missing_modules))
    if failures:
        raise AdultHealthCurriculumError(
            "adult health curriculum validation failed: " + "; ".join(failures)
        )
    return data


def _keyword_matches(text: str, keyword: str) -> bool:
    return re.search(
        rf"(?<!\w){re.escape(keyword.casefold())}(?!\w)",
        text,
    ) is not None


class ConfirmedAdultHealthCurriculumRuntime:
    """Immutable validated curriculum and exact-person classification binding."""

    def __init__(
        self,
        *,
        person_id: str,
        classification: Mapping[str, Any],
        curriculum: Mapping[str, Any],
        classification_path: Path,
        curriculum_path: Path,
    ) -> None:
        self.person_id = str(person_id).strip().casefold()
        self.classification = deepcopy(dict(classification))
        self.curriculum = deepcopy(dict(curriculum))
        self.classification_path = classification_path
        self.curriculum_path = curriculum_path
        self.classification_sha256 = _sha256_file(classification_path)
        self.curriculum_sha256 = _sha256_file(curriculum_path)
        self.classification_evidence_sha256 = _canonical_sha256(
            self.classification
        )

    @classmethod
    def load(
        cls,
        person_id: str,
        *,
        classification_path: Path | None = None,
    ) -> "ConfirmedAdultHealthCurriculumRuntime":
        person = str(person_id or "").strip().casefold()
        if not person:
            raise AdultHealthCurriculumError("person_id is required")
        authority_binding = PERSON_CLASSIFICATION_BINDINGS.get(person)
        if authority_binding is None:
            raise AdultHealthCurriculumError(
                "no exact confirmed-adult classification is configured for person"
            )
        bound_path = Path(authority_binding["path"]).resolve()
        selected_classification = Path(
            classification_path or bound_path
        ).resolve()
        if selected_classification != bound_path:
            raise AdultHealthCurriculumError(
                "classification path does not match the externally pinned authority binding"
            )
        expected_classification_sha = str(
            authority_binding.get("sha256") or ""
        ).casefold()
        actual_classification_sha = _sha256_file(selected_classification)
        if actual_classification_sha != expected_classification_sha:
            raise AdultHealthCurriculumError(
                "classification file digest does not match the externally pinned authority binding"
            )
        classification = _read_json(selected_classification)
        if classification.get("classification_id") != authority_binding.get(
            "classification_id"
        ):
            raise AdultHealthCurriculumError(
                "classification id does not match the externally pinned authority binding"
            )
        if classification.get("source_text_sha256") != authority_binding.get(
            "source_text_sha256"
        ):
            raise AdultHealthCurriculumError(
                "classification source digest does not match the externally pinned authority binding"
            )
        if authority_binding.get("exact_generated_expert_directives_required"):
            _validate_exact_generated_expert_directives(
                person_id=person,
                classification=classification,
            )
        try:
            validate_confirmed_adult_classification_evidence(
                person_id=person,
                maturity_status="confirmed_adult",
                classification_evidence=classification,
            )
        except MaturityGateError as exc:
            raise AdultHealthCurriculumError(
                "confirmed-adult classification failed closed"
            ) from exc

        binding = classification.get("curriculum_binding")
        if not isinstance(binding, Mapping):
            raise AdultHealthCurriculumError("curriculum binding is missing")
        curriculum_path = _project_relative_path(str(binding.get("path") or ""))
        expected_sha = str(binding.get("sha256") or "").strip().casefold()
        if len(expected_sha) != 64 or any(
            character not in "0123456789abcdef" for character in expected_sha
        ):
            raise AdultHealthCurriculumError("curriculum binding digest is invalid")
        actual_sha = _sha256_file(curriculum_path)
        if actual_sha != expected_sha:
            raise AdultHealthCurriculumError("curriculum binding digest mismatch")
        curriculum = validate_curriculum_asset(_read_json(curriculum_path))
        if binding.get("curriculum_id") != curriculum["curriculum_id"]:
            raise AdultHealthCurriculumError("curriculum binding id mismatch")
        if binding.get("assignment") != (
            "IMMEDIATE_COMPLETE_SOURCE_BACKED_ADULT_CURRICULUM"
        ):
            raise AdultHealthCurriculumError("curriculum assignment mismatch")

        entitlement = curriculum_entitlement(
            person_id=person,
            maturity_status="confirmed_adult",
            classification_evidence=classification,
            body_representation="none",
            adult_anatomy_selected=False,
            spa_completed=False,
        )
        if entitlement.get("assignment") != binding.get("assignment"):
            raise AdultHealthCurriculumError("policy entitlement mismatch")
        if set(entitlement.get("modules") or []) != POLICY_MODULE_IDS:
            raise AdultHealthCurriculumError("policy module entitlement mismatch")
        if entitlement.get("adult_anatomy_auto_added") is not False:
            raise AdultHealthCurriculumError("adult anatomy boundary drifted")
        return cls(
            person_id=person,
            classification=classification,
            curriculum=curriculum,
            classification_path=selected_classification,
            curriculum_path=curriculum_path,
        )

    def context_for_turn(
        self,
        user_message: str,
        *,
        required_module_ids: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Return bounded relevant facts plus non-sensitive evidence metadata."""

        normalized = str(user_message or "").casefold()
        modules_by_id = {
            str(module["module_id"]): module
            for module in self.curriculum["modules"]
        }
        if isinstance(required_module_ids, (str, bytes)) or not isinstance(
            required_module_ids, Sequence
        ):
            raise AdultHealthCurriculumError(
                "required_module_ids must be a bounded sequence"
            )
        requested_ids: list[str] = []
        for raw_module_id in required_module_ids:
            module_id = str(raw_module_id or "").strip()
            if module_id not in POLICY_MODULE_IDS:
                raise AdultHealthCurriculumError(
                    "required health reflection module is outside policy"
                )
            if module_id not in requested_ids:
                requested_ids.append(module_id)
        if len(set(BASELINE_MODULE_IDS).union(requested_ids)) > MAX_SELECTED_MODULES:
            raise AdultHealthCurriculumError(
                "required health reflection modules exceed the bounded context"
            )

        selected_ids = list(BASELINE_MODULE_IDS)
        for module_id in requested_ids:
            if module_id not in selected_ids:
                selected_ids.append(module_id)
        for module in self.curriculum["modules"]:
            module_id = str(module["module_id"])
            if module_id in selected_ids:
                continue
            if any(
                _keyword_matches(normalized, str(keyword))
                for keyword in module["keywords"]
            ):
                selected_ids.append(module_id)
            if len(selected_ids) >= MAX_SELECTED_MODULES:
                break

        selected_modules = [modules_by_id[module_id] for module_id in selected_ids]
        source_by_id = {
            str(source["source_id"]): source
            for source in self.curriculum["sources"]
        }
        used_source_ids: list[str] = []
        fact_ids: list[str] = []
        lines = [
            "CONFIRMED-ADULT SOURCE-BOUND HEALTH KNOWLEDGE CONTEXT:",
            "Use this knowledge naturally only when relevant; do not recite it as a policy report.",
            "This is educational context, not a completed lesson, lived experience, body function, diagnosis, treatment, consent, action, or memory.",
            "Physiological response, subjective desire, preference, consent, external action, health state, and memory are separate truths.",
            "A body response never grants consent or proves desire. Relationship status never grants consent.",
            "Do not assume Robert or any synthetic person has a particular organ, cycle, symptom, function, or lived bodily experience unless current factual context or that person explicitly establishes it.",
            "Ask educational curiosity questions in general terms such as 'a person' or 'people' unless the user explicitly invites a personal question about their own physiology.",
        ]
        for module in selected_modules:
            lines.append(f"MODULE {module['module_id']}:")
            for fact in module["facts"]:
                fact_ids.append(str(fact["fact_id"]))
                source_ids = [str(item) for item in fact["source_ids"]]
                for source_id in source_ids:
                    if source_id not in used_source_ids:
                        used_source_ids.append(source_id)
                lines.append(
                    f"- {fact['text']} [sources: {', '.join(source_ids)}]"
                )
        lines.append("BOUND SOURCES USED THIS TURN:")
        for source_id in used_source_ids:
            source = source_by_id[source_id]
            lines.append(
                f"- {source_id}: {source['publisher']}; {source['title']}; "
                f"{source['url']}; reviewed {source['reviewed_at_utc']}"
            )

        return {
            "status": "SOURCE_CONTEXT_ASSEMBLED_NO_LESSON_OR_MEMORY_CLAIM",
            "person_id": self.person_id,
            "maturity_status": "confirmed_adult",
            "prompt_context": "\n".join(lines),
            "selected_module_ids": selected_ids,
            "required_module_ids": requested_ids,
            "fact_ids": fact_ids,
            "source_ids": used_source_ids,
            "classification_id": self.classification["classification_id"],
            "classification_file_sha256": self.classification_sha256,
            "classification_evidence_sha256": self.classification_evidence_sha256,
            "curriculum_id": self.curriculum["curriculum_id"],
            "curriculum_file_sha256": self.curriculum_sha256,
            "source_context_connected": True,
            "lesson_completion_claimed": False,
            "learning_memory_created": False,
            "adult_anatomy_added": False,
            "body_function_claimed": False,
            "medical_diagnosis_or_treatment_claimed": False,
            "external_action_authorized": False,
        }


__all__ = [
    "AdultHealthCurriculumError",
    "ConfirmedAdultHealthCurriculumRuntime",
    "CURRICULUM_PATH",
    "EXACT_GENERATED_EXPERT_CANDIDATE_IDS",
    "EXPERT_ADULT_DIRECTIVE_BINDING",
    "EXPERT_CURRICULUM_EXTENSION_BINDING",
    "PERSON_CLASSIFICATION_BINDINGS",
    "PERSON_CLASSIFICATION_PATHS",
    "validate_curriculum_asset",
]
