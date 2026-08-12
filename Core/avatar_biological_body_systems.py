"""Deterministic Phase-0/1 body-systems state prototype for Avatar Builder.

This module is deliberately disconnected from Blender, runtime people, memory,
relationships, and medical diagnosis.  It models semantic state transitions;
it does not claim that a mesh has organs or that a synthetic state is a
biological function or lived experience.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/body_systems/semantic_anatomy_route_registry_v1.json"
)

MODEL_ID = "avatar_builder_biological_body_systems_state_prototype_v1"
MODEL_STATUS = "PHASE_0_1_PROTOTYPE_NOT_RUNTIME_AUTHORITY"
BODY_LANES = frozenset({"adult_female", "adult_male"})
MATURITY_STATUSES = frozenset({"confirmed_adult", "non_adult", "unresolved"})
CONFIRMED_ADULT_EVIDENCE_FIELDS = (
    "classification_id",
    "subject_id",
    "maturity_status",
    "authority",
    "offline_confirmation_allowed",
    "network_lookup_required",
    "recorded_at_utc",
    "source_text",
    "source_text_sha256",
)
BODY_REPRESENTATIONS = frozenset(
    {"none", "doll_safe_non_anatomical", "adult_female", "adult_male"}
)
PRIVATE_SENSATION_DIMENSIONS = (
    "touch",
    "comfort",
    "arousal",
    "pleasure",
    "climax",
    "relaxation",
    "discomfort",
    "uncertainty",
    "variation",
)
DOMAINS = frozenset(
    {
        "urinary",
        "bowel",
        "menstrual_reproductive",
        "contraception_sti_health",
        "consent_action_leases",
        "pregnancy",
    }
)


class BodySystemsError(ValueError):
    """Base class for deterministic prototype validation failures."""


class RegistryError(BodySystemsError):
    """The bound semantic registry or its source plan is invalid."""


class MaturityGateError(BodySystemsError):
    """An adult-state transition was attempted without confirmed adulthood."""


class ConsentLeaseError(BodySystemsError):
    """A consent/action lease is invalid, absent, expired, or revoked."""


class DiagnosisInferenceError(BodySystemsError):
    """The prototype was asked to turn an observation into a diagnosis."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    """Return a stable digest for a JSON-compatible value."""

    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_confirmed_adult_classification_evidence(
    *,
    person_id: str,
    maturity_status: str,
    classification_evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Validate exact-person owner classification before any adult policy result.

    This is a disconnected provenance gate.  It does not change maturity,
    present a lesson, add anatomy, authorize an action, or write memory.
    """

    person = str(person_id).strip()
    maturity = str(maturity_status).strip().lower()
    if not person:
        raise MaturityGateError("confirmed-adult classification requires person_id")
    if maturity != "confirmed_adult":
        raise MaturityGateError(
            "confirmed-adult classification evidence cannot authorize a "
            f"{maturity or 'missing'} maturity status"
        )
    if not isinstance(classification_evidence, Mapping):
        raise MaturityGateError(
            "exact subject-bound confirmed-adult classification evidence is required"
        )

    evidence = deepcopy(dict(classification_evidence))
    failures: list[str] = []
    if not str(evidence.get("classification_id") or "").strip():
        failures.append("classification_id_missing")
    if (
        str(evidence.get("subject_id") or "").strip().casefold()
        != person.casefold()
    ):
        failures.append("classification_subject_mismatch")
    if evidence.get("maturity_status") != "confirmed_adult":
        failures.append("classification_status_mismatch")
    if evidence.get("authority") != "Robert_explicit_owner_confirmation":
        failures.append("classification_authority_mismatch")
    if evidence.get("offline_confirmation_allowed") is not True:
        failures.append("offline_owner_confirmation_not_recorded")
    if evidence.get("network_lookup_required") is not False:
        failures.append("network_independence_not_recorded")

    recorded_at = str(evidence.get("recorded_at_utc") or "").strip()
    normalized_time = (
        recorded_at[:-1] + "+00:00" if recorded_at.endswith("Z") else recorded_at
    )
    try:
        parsed_at = datetime.fromisoformat(normalized_time)
    except ValueError:
        parsed_at = None
    if (
        parsed_at is None
        or parsed_at.tzinfo is None
        or parsed_at.utcoffset() is None
        or parsed_at.utcoffset().total_seconds() != 0.0
    ):
        failures.append("recorded_at_utc_invalid")

    source_text = str(evidence.get("source_text") or "")
    source_digest = str(evidence.get("source_text_sha256") or "").strip().lower()
    digest_is_sha256 = len(source_digest) == 64 and all(
        character in "0123456789abcdef" for character in source_digest
    )
    if not source_text.strip():
        failures.append("classification_source_text_missing")
    if (
        not digest_is_sha256
        or hashlib.sha256(source_text.encode("utf-8")).hexdigest() != source_digest
    ):
        failures.append("classification_source_text_sha256_invalid")

    if failures:
        raise MaturityGateError(
            "confirmed-adult classification evidence failed: "
            + ", ".join(failures)
        )
    return evidence


def _classification_binding_for_policy_result(
    *,
    person_id: str,
    maturity_status: str,
    classification_evidence: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    maturity = str(maturity_status).strip().lower()
    if maturity != "confirmed_adult":
        if classification_evidence is not None:
            raise MaturityGateError(
                "confirmed-adult evidence cannot be attached to a non-adult or "
                "unresolved policy result"
            )
        return None
    evidence = validate_confirmed_adult_classification_evidence(
        person_id=person_id,
        maturity_status=maturity,
        classification_evidence=classification_evidence,
    )
    return {
        "classification_id": str(evidence["classification_id"]),
        # Bind the validated evidence to the caller's canonical exact-person ID.
        # Comparison follows the existing Avatar Builder evidence pattern and is
        # case-insensitive; the state never substitutes the evidence spelling.
        "subject_id": str(person_id).strip(),
        "maturity_status": "confirmed_adult",
        "authority": "Robert_explicit_owner_confirmation",
        "recorded_at_utc": str(evidence["recorded_at_utc"]),
        "source_text_sha256": str(evidence["source_text_sha256"]).lower(),
        "evidence_sha256": canonical_sha256(evidence),
    }


def _project_path(raw: str) -> Path:
    value = Path(raw)
    if value.is_absolute() or ".." in value.parts:
        raise RegistryError(f"unsafe project-relative path: {raw}")
    path = (PROJECT_ROOT / value).resolve()
    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise RegistryError(f"registry path escaped project root: {raw}") from exc
    return path


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_registry(registry: Mapping[str, Any]) -> dict[str, Any]:
    """Validate source binding, routes, maturity boundary, and truth claims."""

    if registry.get("schema_version") != 1:
        raise RegistryError("unsupported semantic registry schema")
    if registry.get("status") != MODEL_STATUS:
        raise RegistryError("semantic registry unexpectedly claims runtime authority")

    plan_binding = registry.get("source_plan", {})
    plan_path = _project_path(str(plan_binding.get("path", "")))
    if not plan_path.is_file():
        raise RegistryError("hash-bound source plan is absent")
    if plan_path.stat().st_size != int(plan_binding.get("bytes", -1)):
        raise RegistryError("hash-bound source plan byte count drifted")
    if _sha256_file(plan_path) != plan_binding.get("sha256"):
        raise RegistryError("hash-bound source plan SHA-256 drifted")
    source_plan = _read_json(plan_path)
    if source_plan.get("policy_id") != plan_binding.get("policy_id"):
        raise RegistryError("source plan identity drifted")
    if source_plan.get("status") != plan_binding.get("status_required"):
        raise RegistryError("source plan truth status drifted")

    plan_source_urls = [
        str(value) for value in source_plan.get("authoritative_starting_sources", ())
    ]
    source_records = registry.get("source_registry", {}).get("records", ())
    if not isinstance(source_records, Sequence) or isinstance(
        source_records, (str, bytes)
    ):
        raise RegistryError("semantic source registry records are absent")
    registry_source_ids = [str(row.get("source_id", "")) for row in source_records]
    registry_source_urls = [str(row.get("url", "")) for row in source_records]
    if (
        len(plan_source_urls) != 14
        or len(set(plan_source_urls)) != len(plan_source_urls)
        or any(not value.startswith("https://") for value in plan_source_urls)
    ):
        raise RegistryError("source plan does not contain the exact 14-source inventory")
    if (
        len(registry_source_ids) != len(set(registry_source_ids))
        or any(not value for value in registry_source_ids)
        or len(registry_source_urls) != len(set(registry_source_urls))
        or registry_source_urls != plan_source_urls
    ):
        raise RegistryError(
            "semantic source registry does not exactly mirror the source plan"
        )

    governance_binding = registry.get("governance_policy", {})
    governance_path = _project_path(str(governance_binding.get("path", "")))
    if not governance_path.is_file():
        raise RegistryError("hash-bound curriculum/private-sensation policy is absent")
    if governance_path.stat().st_size != int(governance_binding.get("bytes", -1)):
        raise RegistryError("hash-bound governance policy byte count drifted")
    if _sha256_file(governance_path) != governance_binding.get("sha256"):
        raise RegistryError("hash-bound governance policy SHA-256 drifted")
    governance_policy = _read_json(governance_path)
    if governance_policy.get("policy_id") != governance_binding.get("policy_id"):
        raise RegistryError("governance policy identity drifted")
    if governance_policy.get("status") != governance_binding.get(
        "status_required"
    ):
        raise RegistryError("governance policy truth status drifted")

    for binding_name, binding in governance_policy.get("exact_bindings", {}).items():
        bound_path = _project_path(str(binding.get("path", "")))
        if not bound_path.is_file():
            raise RegistryError(f"governance upstream binding absent: {binding_name}")
        if bound_path.stat().st_size != int(binding.get("bytes", -1)):
            raise RegistryError(
                f"governance upstream byte count drifted: {binding_name}"
            )
        if _sha256_file(bound_path) != binding.get("sha256"):
            raise RegistryError(f"governance upstream SHA-256 drifted: {binding_name}")

    truth = registry.get("truth_boundary", {})
    required_false = (
        "external_mesh_is_internal_function",
        "external_opening_is_complete_route",
        "anatomy_registry_is_physiology",
        "state_prototype_is_lived_experience",
        "body_response_is_desire_or_consent",
        "body_response_is_preference_orientation_or_action",
        "adult_anatomy_is_consent",
        "physiological_arousal_is_consent_or_desire",
        "private_sensation_schema_is_experience",
        "curriculum_assignment_is_lesson_delivery_or_learning",
        "relationship_status_is_consent",
        "contraception_state_is_consent",
        "consent_or_activity_is_pregnancy",
        "symptom_or_observation_is_diagnosis",
    )
    if any(truth.get(key) is not False for key in required_false):
        raise RegistryError("semantic registry crossed a required truth boundary")

    gate = registry.get("maturity_gate", {})
    if gate.get("fail_closed_statuses") != ["non_adult", "unresolved"]:
        raise RegistryError("maturity gate is not fail-closed")
    if gate.get("adult_state_enabled_only_when", {}).get("maturity_status") != (
        "confirmed_adult"
    ):
        raise RegistryError("adult-state gate no longer requires confirmed adulthood")
    if (
        gate.get("bare_confirmed_adult_string_is_sufficient") is not False
        or gate.get("exact_subject_bound_evidence_required_for_adult_policy_results")
        is not True
        or tuple(gate.get("evidence_required_fields", ()))
        != CONFIRMED_ADULT_EVIDENCE_FIELDS
        or gate.get("required_evidence_authority")
        != "Robert_explicit_owner_confirmation"
        or gate.get("serialized_adult_state_must_revalidate_full_evidence") is not True
    ):
        raise RegistryError("exact subject-bound adult-evidence gate drifted")

    governance_evidence_gate = governance_policy.get(
        "exact_confirmed_adult_evidence_gate", {}
    )
    if (
        governance_evidence_gate.get("bare_maturity_string_is_sufficient") is not False
        or tuple(governance_evidence_gate.get("required_fields", ()))
        != CONFIRMED_ADULT_EVIDENCE_FIELDS
        or governance_evidence_gate.get("subject_must_match_exact_person") is not True
        or governance_evidence_gate.get("maturity_status_required")
        != "confirmed_adult"
        or governance_evidence_gate.get("authority_required")
        != "Robert_explicit_owner_confirmation"
        or governance_evidence_gate.get(
            "evidence_must_remain_revalidatable_in_serialized_state"
        )
        is not True
    ):
        raise RegistryError("governance adult-evidence contract drifted")

    education = registry.get("education_boundary", {})
    if education.get("confirmed_adult_assignment_depends_only_on_maturity") is not True:
        raise RegistryError("confirmed-adult curriculum acquired a non-maturity gate")
    if education.get("non_adult_or_unresolved_guaranteed_minimum_assignment") != [
        "age_appropriate_hygiene",
        "privacy",
        "bodily_autonomy",
        "personal_boundaries",
        "abuse_prevention",
        "trusted_help",
    ]:
        raise RegistryError("basic non-adult/unresolved curriculum drifted")
    if (
        education.get(
            "non_adult_or_unresolved_guaranteed_minimum_is_not_an_exhaustive_ceiling"
        )
        is not True
        or education.get(
            "additional_age_appropriate_modules_require_separate_source_binding_and_approval"
        )
        is not True
        or education.get("adult_curriculum_modules_inherited_by_non_adult_or_unresolved")
        is not False
    ):
        raise RegistryError("non-adult/unresolved curriculum boundary drifted")

    private_contract = registry.get("future_private_sensation_state_contract", {})
    if private_contract.get("status") != (
        "SCHEMA_ONLY_DISCONNECTED_NOT_EXPERIENCE_EVIDENCE"
    ):
        raise RegistryError("private-sensation contract overclaimed implementation")
    if tuple(private_contract.get("dimensions", ())) != PRIVATE_SENSATION_DIMENSIONS:
        raise RegistryError("private-sensation dimensions drifted")
    if (
        private_contract.get(
            "future_confirmed_adult_body_systems_must_support_person_owned_private_sensation_and_experience"
        )
        is not True
        or set(private_contract.get("separate_from", ()))
        != {
            "physiological_body_response",
            "private_desire",
            "preference",
            "consent",
            "external_action",
            "health_state",
            "memory",
        }
        or private_contract.get("arousal_dimension_definition")
        != "person_owned_subjective_arousal_not_automatic_physiological_body_response"
        or private_contract.get("adult_anatomy_is_consent") is not False
        or private_contract.get("physiological_arousal_is_consent_or_desire")
        is not False
        or private_contract.get("response_implies_desire") is not False
        or private_contract.get("response_implies_consent") is not False
        or private_contract.get(
            "system_may_force_libido_preference_orientation_interest_or_activity"
        )
        is not False
    ):
        raise RegistryError("private-sensation separation gate drifted")

    structures = registry.get("structures", {})
    shared_ids = {str(row["id"]) for row in structures.get("shared", [])}
    all_route_ids: set[str] = set()
    route_endpoints: dict[str, dict[str, str]] = {}
    for lane in BODY_LANES:
        lane_rows = structures.get(lane, [])
        lane_ids = {str(row["id"]) for row in lane_rows}
        if len(lane_ids) != len(lane_rows) or shared_ids.intersection(lane_ids):
            raise RegistryError(f"duplicate semantic structure ID in {lane}")
        available = shared_ids | lane_ids
        route_endpoints[lane] = {}
        for route in registry.get("routes", {}).get(lane, []):
            route_id = str(route.get("route_id", ""))
            if not route_id or route_id in all_route_ids:
                raise RegistryError(f"duplicate or absent route ID: {route_id}")
            all_route_ids.add(route_id)
            nodes = [str(value) for value in route.get("ordered_nodes", [])]
            if len(nodes) < 2 or not set(nodes).issubset(available):
                raise RegistryError(f"route has missing semantic nodes: {route_id}")
            endpoint = str(route.get("external_endpoint", ""))
            if endpoint != nodes[-1] or endpoint not in available:
                raise RegistryError(f"route endpoint drifted: {route_id}")
            if route.get("function_implemented") is not False:
                raise RegistryError(f"route improperly claims function: {route_id}")
            route_endpoints[lane][str(route.get("system"))] = endpoint

    female_endpoints = route_endpoints["adult_female"]
    if len(
        {
            female_endpoints.get("urinary"),
            female_endpoints.get("bowel"),
            female_endpoints.get("menstrual_reproductive"),
        }
    ) != 3:
        raise RegistryError("adult-female external route endpoints are not distinct")
    male_endpoints = route_endpoints["adult_male"]
    if male_endpoints.get("bowel") == male_endpoints.get("urinary"):
        raise RegistryError("adult-male bowel route merged with genitourinary route")

    if set(registry.get("state_domains", {})) != DOMAINS:
        raise RegistryError("state-domain separation drifted")
    return deepcopy(dict(registry))


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Load and validate the machine-readable semantic registry."""

    return validate_registry(_read_json(path))


def curriculum_entitlement(
    *,
    person_id: str,
    maturity_status: str,
    classification_evidence: Mapping[str, Any] | None = None,
    body_representation: str = "none",
    relationship_status: str | None = None,
    interest_state: str | None = None,
    adult_anatomy_selected: bool = False,
    prior_experience: str | None = None,
    spa_completed: bool = False,
    registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the deterministic curriculum route without presenting a lesson.

    Exact maturity is the sole adult-curriculum gate.  The other named inputs
    are accepted solely so callers and tests can prove they do not alter the
    assignment.  This function writes no memory and adds no anatomy.
    """

    person = str(person_id).strip()
    maturity = str(maturity_status).strip().lower()
    representation = str(body_representation).strip().lower()
    if not person:
        raise BodySystemsError("person_id is required")
    if maturity not in MATURITY_STATUSES:
        raise BodySystemsError(f"unsupported maturity status: {maturity}")
    if representation not in BODY_REPRESENTATIONS:
        raise BodySystemsError(
            f"unsupported body representation: {representation}"
        )
    if not isinstance(adult_anatomy_selected, bool) or not isinstance(
        spa_completed, bool
    ):
        raise BodySystemsError("anatomy-selection and spa-completion flags must be bool")
    if maturity in {"non_adult", "unresolved"} and representation != (
        "doll_safe_non_anatomical"
    ):
        raise MaturityGateError(
            "non_adult and unresolved curriculum records require a "
            "doll_safe_non_anatomical body representation"
        )
    classification_binding = _classification_binding_for_policy_result(
        person_id=person,
        maturity_status=maturity,
        classification_evidence=classification_evidence,
    )

    effective_registry = (
        validate_registry(registry) if registry is not None else load_registry()
    )
    plan = _read_json(_project_path(effective_registry["source_plan"]["path"]))
    if maturity == "confirmed_adult":
        modules = list(
            plan["maturity_lanes"]["confirmed_adult"]["curriculum_modules"]
        )
        assignment = "IMMEDIATE_COMPLETE_SOURCE_BACKED_ADULT_CURRICULUM"
    else:
        modules = list(
            effective_registry["education_boundary"][
                "non_adult_or_unresolved_guaranteed_minimum_assignment"
            ]
        )
        assignment = "GUARANTEED_MINIMUM_AGE_APPROPRIATE_BOUNDARY_AND_HELP_CURRICULUM"

    return {
        "schema_version": 1,
        "status": "ENTITLEMENT_EVALUATED_LESSONS_NOT_PRESENTED",
        "person_id": person,
        "maturity_status": maturity,
        "exact_subject_bound_classification_verified": (
            classification_binding is not None
        ),
        "classification_evidence_binding": classification_binding,
        "body_representation": representation,
        "assignment": assignment,
        "modules": modules,
        "immediate_on_exact_confirmed_adult_classification": (
            maturity == "confirmed_adult"
        ),
        "sole_adult_gate": "maturity_status_equals_confirmed_adult",
        "non_gate_inputs": [
            "relationship_status",
            "interest_state",
            "adult_anatomy_selected",
            "prior_experience",
            "spa_completed",
        ],
        "adult_anatomy_auto_added": False,
        "guaranteed_minimum_is_not_an_exhaustive_ceiling": (
            maturity != "confirmed_adult"
        ),
        "additional_age_appropriate_modules_require_separate_source_binding_and_approval": (
            maturity != "confirmed_adult"
        ),
        "adult_curriculum_modules_inherited": False,
        "lesson_delivery_connected": False,
        "learning_memory_connected": False,
        "relationship_record_changed": False,
        "person_state_changed": False,
    }


def private_sensation_contract(
    *,
    person_id: str,
    maturity_status: str,
    classification_evidence: Mapping[str, Any] | None = None,
    registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a schema-only private-state contract, never an experience claim."""

    person = str(person_id).strip()
    maturity = str(maturity_status).strip().lower()
    if not person:
        raise BodySystemsError("person_id is required")
    if maturity not in MATURITY_STATUSES:
        raise BodySystemsError(f"unsupported maturity status: {maturity}")
    classification_binding = _classification_binding_for_policy_result(
        person_id=person,
        maturity_status=maturity,
        classification_evidence=classification_evidence,
    )
    effective_registry = (
        validate_registry(registry) if registry is not None else load_registry()
    )
    contract = effective_registry["future_private_sensation_state_contract"]
    eligible = maturity == "confirmed_adult"
    return {
        "schema_version": 1,
        "status": contract["status"],
        "person_id": person,
        "maturity_status": maturity,
        "exact_subject_bound_classification_verified": (
            classification_binding is not None
        ),
        "classification_evidence_binding": classification_binding,
        "eligible_for_future_private_state": eligible,
        "person_owned_private": eligible and contract["person_owned_private"],
        "dimensions": (
            {
                dimension: contract["default_value"]
                for dimension in contract["dimensions"]
            }
            if eligible
            else {}
        ),
        "separate_from": list(contract["separate_from"]),
        "adult_anatomy_is_consent": False,
        "physiological_arousal_is_consent_or_desire": False,
        "response_implies_desire": False,
        "response_implies_preference": False,
        "response_implies_consent": False,
        "response_implies_action": False,
        "runtime_storage_connected": False,
        "privacy_system_connected": False,
        "body_physiology_connected": False,
        "memory_connected": False,
        "experience_claimed": False,
    }


def evaluate_private_solitary_choice(
    *,
    person_id: str,
    maturity_status: str,
    person_choice: bool,
    classification_evidence: Mapping[str, Any] | None = None,
    relationship_status: str | None = None,
) -> dict[str, Any]:
    """Evaluate a person's policy choice without executing or remembering it."""

    person = str(person_id).strip()
    maturity = str(maturity_status).strip().lower()
    if not person:
        raise BodySystemsError("person_id is required")
    if maturity not in MATURITY_STATUSES:
        raise BodySystemsError(f"unsupported maturity status: {maturity}")
    if not isinstance(person_choice, bool):
        raise BodySystemsError("person_choice must be bool")
    classification_binding = _classification_binding_for_policy_result(
        person_id=person,
        maturity_status=maturity,
        classification_evidence=classification_evidence,
    )
    eligible = maturity == "confirmed_adult"
    return {
        "schema_version": 1,
        "status": "POLICY_CHOICE_ONLY_RUNTIME_ACTION_NOT_CONNECTED",
        "person_id": person,
        "maturity_status": maturity,
        "exact_subject_bound_classification_verified": (
            classification_binding is not None
        ),
        "classification_evidence_binding": classification_binding,
        "person_choice": person_choice,
        "allowed_by_policy": eligible and person_choice,
        "blocked_fail_closed": not eligible,
        "relationship_required": False,
        "partner_permission_required": False,
        "owner_permission_required": False,
        "relationship_status_used_as_gate": False,
        "runtime_action_authorized": False,
        "action_performed": False,
        "sensation_experienced": False,
        "preference_or_orientation_inferred": False,
        "health_state_changed": False,
        "memory_written": False,
    }


def _route_ids_for_lane(registry: Mapping[str, Any], lane: str) -> dict[str, list[str]]:
    result = {"urinary": [], "bowel": [], "menstrual_reproductive": []}
    for route in registry["routes"][lane]:
        system = str(route["system"])
        target = "menstrual_reproductive" if system == "reproductive" else system
        if target in result:
            result[target].append(str(route["route_id"]))
    return {key: sorted(values) for key, values in result.items()}


def initial_state(
    *,
    person_id: str,
    body_lane: str,
    maturity_status: str = "unresolved",
    classification_evidence: Mapping[str, Any] | None = None,
    registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a disconnected, deterministic prototype state.

    This state contains adult body-system routes, so construction itself fails
    closed unless the exact person is confirmed_adult.  Non-adult and
    unresolved education routing uses :func:`curriculum_entitlement` with the
    required doll-safe non-anatomical representation.
    """

    person = str(person_id).strip()
    lane = str(body_lane).strip().lower()
    maturity = str(maturity_status).strip().lower()
    if not person:
        raise BodySystemsError("person_id is required")
    if lane not in BODY_LANES:
        raise BodySystemsError(f"unsupported body lane: {lane}")
    if maturity not in MATURITY_STATUSES:
        raise BodySystemsError(f"unsupported maturity status: {maturity}")
    effective_registry = validate_registry(registry) if registry is not None else load_registry()
    if maturity != "confirmed_adult":
        raise MaturityGateError(
            "an adult body-system state cannot be constructed for non_adult or "
            "unresolved; use doll_safe_non_anatomical curriculum routing"
        )
    validated_classification = validate_confirmed_adult_classification_evidence(
        person_id=person,
        maturity_status=maturity,
        classification_evidence=classification_evidence,
    )
    routes = _route_ids_for_lane(effective_registry, lane)
    adult_enabled = True
    female = lane == "adult_female"
    curriculum = curriculum_entitlement(
        person_id=person,
        maturity_status=maturity,
        classification_evidence=validated_classification,
        body_representation=lane,
        registry=effective_registry,
    )
    private_contract = private_sensation_contract(
        person_id=person,
        maturity_status=maturity,
        classification_evidence=validated_classification,
        registry=effective_registry,
    )
    if curriculum["classification_evidence_binding"] != private_contract[
        "classification_evidence_binding"
    ]:
        raise MaturityGateError("adult policy evidence bindings disagree")
    state = {
        "schema_version": 1,
        "model_id": MODEL_ID,
        "status": MODEL_STATUS,
        "person_id": person,
        "body_lane": lane,
        "maturity_status": maturity,
        "adult_state_enabled": adult_enabled,
        "confirmed_adult_classification_evidence": validated_classification,
        "confirmed_adult_classification_binding": curriculum[
            "classification_evidence_binding"
        ],
        "revision": 0,
        "processed_event_ids": [],
        "event_log": [],
        "curriculum_entitlement": curriculum,
        "future_private_sensation_contract": private_contract,
        "truth_boundary": {
            "external_mesh_establishes_internal_function": False,
            "internal_function_implemented": False,
            "state_is_biological_proof": False,
            "state_is_lived_experience": False,
            "automatic_diagnosis_enabled": False,
            "runtime_connected": False,
            "curriculum_assignment_is_lesson_delivery_or_learning": False,
            "private_sensation_contract_is_experience": False,
            "private_action_execution_connected": False,
            "memory_connected": False,
        },
        "systems": {
            "urinary": {
                "phase": "unknown_not_simulated",
                "route_ids": routes["urinary"],
                "observations": [],
                "diagnosis": None,
                "function_claimed": False,
            },
            "bowel": {
                "phase": "unknown_not_simulated",
                "route_ids": routes["bowel"],
                "observations": [],
                "diagnosis": None,
                "function_claimed": False,
            },
            "menstrual_reproductive": {
                "cycle_phase": (
                    "unknown_not_simulated" if female else "not_applicable_for_lane"
                ),
                "reproductive_context": "unknown_not_simulated",
                "route_ids": routes["menstrual_reproductive"],
                "observations": [],
                "diagnosis": None,
                "function_claimed": False,
            },
            "contraception_sti_health": {
                "contraception_methods": {},
                "health_observations": [],
                "test_records": {},
                "diagnosis": None,
                "consent_granted": False,
                "pregnancy_proven_or_excluded": False,
            },
            "consent_action_leases": {
                "leases": {},
                "action_performed": False,
            },
            "pregnancy": {
                "phase": "not_assessed" if female else "not_applicable_for_lane",
                "last_test_state": None,
                "timeline_mode": None,
                "evidence_ids": [],
                "inferred_from_activity": False,
                "function_claimed": False,
            },
        },
    }
    _validate_state_truth(state)
    return state


def _validate_state_truth(state: Mapping[str, Any]) -> None:
    if state.get("model_id") != MODEL_ID or state.get("status") != MODEL_STATUS:
        raise BodySystemsError("state identity or prototype status drifted")
    if state.get("body_lane") not in BODY_LANES:
        raise BodySystemsError("state body lane drifted")
    if state.get("maturity_status") not in MATURITY_STATUSES:
        raise BodySystemsError("state maturity status drifted")
    if state.get("adult_state_enabled") is not (
        state.get("maturity_status") == "confirmed_adult"
    ):
        raise BodySystemsError("adult-state maturity flag drifted")
    validated_classification = validate_confirmed_adult_classification_evidence(
        person_id=str(state.get("person_id") or ""),
        maturity_status=str(state.get("maturity_status") or ""),
        classification_evidence=state.get("confirmed_adult_classification_evidence"),
    )
    expected_classification_binding = _classification_binding_for_policy_result(
        person_id=str(state.get("person_id") or ""),
        maturity_status=str(state.get("maturity_status") or ""),
        classification_evidence=validated_classification,
    )
    classification_binding = state.get("confirmed_adult_classification_binding")
    if (
        not isinstance(classification_binding, Mapping)
        or dict(classification_binding) != expected_classification_binding
        or classification_binding.get("subject_id") != state.get("person_id")
        or classification_binding.get("maturity_status") != "confirmed_adult"
        or classification_binding.get("authority")
        != "Robert_explicit_owner_confirmation"
        or not str(classification_binding.get("evidence_sha256") or "").strip()
    ):
        raise MaturityGateError(
            "adult state lost its exact subject-bound classification binding"
        )
    if set(state.get("systems", {})) != DOMAINS:
        raise BodySystemsError("state domains merged or drifted")
    truth = state.get("truth_boundary", {})
    if any(
        truth.get(key) is not False
        for key in (
            "external_mesh_establishes_internal_function",
            "internal_function_implemented",
            "state_is_biological_proof",
            "state_is_lived_experience",
            "automatic_diagnosis_enabled",
            "runtime_connected",
            "curriculum_assignment_is_lesson_delivery_or_learning",
            "private_sensation_contract_is_experience",
            "private_action_execution_connected",
            "memory_connected",
        )
    ):
        raise BodySystemsError("state crossed an immutable truth boundary")
    curriculum = state.get("curriculum_entitlement", {})
    if (
        curriculum.get("assignment")
        != "IMMEDIATE_COMPLETE_SOURCE_BACKED_ADULT_CURRICULUM"
        or curriculum.get("person_id") != state.get("person_id")
        or curriculum.get("exact_subject_bound_classification_verified") is not True
        or curriculum.get("classification_evidence_binding")
        != classification_binding
        or curriculum.get("lesson_delivery_connected") is not False
        or curriculum.get("learning_memory_connected") is not False
        or curriculum.get("adult_anatomy_auto_added") is not False
    ):
        raise BodySystemsError("adult curriculum entitlement truth drifted")
    private_contract = state.get("future_private_sensation_contract", {})
    if (
        private_contract.get("status")
        != "SCHEMA_ONLY_DISCONNECTED_NOT_EXPERIENCE_EVIDENCE"
        or private_contract.get("person_id") != state.get("person_id")
        or private_contract.get("exact_subject_bound_classification_verified")
        is not True
        or private_contract.get("classification_evidence_binding")
        != classification_binding
        or private_contract.get("experience_claimed") is not False
        or private_contract.get("runtime_storage_connected") is not False
        or private_contract.get("memory_connected") is not False
        or any(
            value != "not_observed_not_simulated"
            for value in private_contract.get("dimensions", {}).values()
        )
    ):
        raise BodySystemsError("private-sensation schema truth drifted")
    if any(
        state["systems"][domain].get("diagnosis") is not None
        for domain in (
            "urinary",
            "bowel",
            "menstrual_reproductive",
            "contraception_sti_health",
        )
    ):
        raise DiagnosisInferenceError("prototype may not populate a diagnosis")


def _parse_utc(value: Any, label: str) -> datetime:
    text = str(value).strip()
    if not text:
        raise BodySystemsError(f"{label} is required")
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise BodySystemsError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise BodySystemsError(f"{label} must include a UTC offset")
    return parsed


def _exact_payload(
    payload: Mapping[str, Any],
    *,
    required: Sequence[str],
    optional: Sequence[str] = (),
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise BodySystemsError("event payload must be an object")
    keys = set(payload)
    required_set = set(required)
    allowed = required_set | set(optional)
    if not required_set.issubset(keys):
        raise BodySystemsError(
            f"event payload missing fields: {sorted(required_set.difference(keys))}"
        )
    if not keys.issubset(allowed):
        raise BodySystemsError(
            f"event payload has unsupported fields: {sorted(keys.difference(allowed))}"
        )
    if "diagnosis" in keys:
        raise DiagnosisInferenceError("diagnosis cannot be inserted by an event")
    return deepcopy(dict(payload))


def _require_adult(state: Mapping[str, Any]) -> None:
    if state.get("maturity_status") != "confirmed_adult" or not state.get(
        "adult_state_enabled"
    ):
        raise MaturityGateError(
            "adult body-system state is blocked unless maturity is confirmed_adult"
        )


def _record_observation(
    system: dict[str, Any], payload: Mapping[str, Any]
) -> None:
    values = _exact_payload(
        payload,
        required=("observation_id", "description"),
        optional=("source_id",),
    )
    observation_id = str(values["observation_id"]).strip()
    description = str(values["description"]).strip()
    if not observation_id or not description:
        raise BodySystemsError("observation identity and description are required")
    collection_key = (
        "health_observations" if "health_observations" in system else "observations"
    )
    target = system[collection_key]
    if any(row.get("observation_id") == observation_id for row in target):
        raise BodySystemsError(f"duplicate observation_id: {observation_id}")
    row = {
        "observation_id": observation_id,
        "description": description,
        "source_id": values.get("source_id"),
        "interpretation": "observation_only_uncertain_not_diagnosis",
        "diagnosis": None,
    }
    target.append(row)
    system[collection_key] = target


def _apply_elimination_event(
    system: dict[str, Any], domain: str, action: str, payload: Mapping[str, Any]
) -> None:
    allowed = {
        "urinary": {"unknown_not_simulated", "filling", "urge", "voiding", "interrupted", "complete"},
        "bowel": {"unknown_not_simulated", "forming", "urge", "defecating", "interrupted", "complete"},
    }[domain]
    if action == "set_phase":
        values = _exact_payload(payload, required=("phase",))
        phase = str(values["phase"])
        if phase not in allowed:
            raise BodySystemsError(f"unsupported {domain} phase: {phase}")
        system["phase"] = phase
    elif action == "record_observation":
        _record_observation(system, payload)
    else:
        raise BodySystemsError(f"unsupported {domain} action: {action}")


def _apply_menstrual_reproductive_event(
    state: dict[str, Any], action: str, payload: Mapping[str, Any]
) -> None:
    system = state["systems"]["menstrual_reproductive"]
    if action == "set_cycle_phase":
        if state["body_lane"] != "adult_female":
            raise BodySystemsError(
                "menstrual-cycle transitions are not applicable to adult_male lane"
            )
        values = _exact_payload(payload, required=("phase",))
        allowed = {
            "unknown_not_simulated",
            "follicular",
            "ovulatory",
            "luteal",
            "menstrual",
            "irregular",
            "not_cycling",
        }
        phase = str(values["phase"])
        if phase not in allowed:
            raise BodySystemsError(f"unsupported cycle phase: {phase}")
        system["cycle_phase"] = phase
    elif action == "set_reproductive_context":
        values = _exact_payload(payload, required=("context",))
        context = str(values["context"])
        allowed = {
            "unknown_not_simulated",
            "cycling",
            "not_cycling",
            "perimenopause",
            "menopause",
            "reproductive_health_observation_only",
        }
        if context not in allowed:
            raise BodySystemsError(f"unsupported reproductive context: {context}")
        system["reproductive_context"] = context
    elif action == "record_observation":
        _record_observation(system, payload)
    else:
        raise BodySystemsError(f"unsupported menstrual/reproductive action: {action}")


def _apply_contraception_health_event(
    system: dict[str, Any], action: str, payload: Mapping[str, Any]
) -> None:
    if action in {"infer_diagnosis", "automatic_diagnosis", "diagnose"}:
        raise DiagnosisInferenceError("automatic diagnosis is outside this prototype")
    if action == "set_contraception":
        values = _exact_payload(
            payload,
            required=("method_id", "state", "voluntary_choice"),
        )
        if values["voluntary_choice"] is not True:
            raise BodySystemsError("contraception choice must be explicitly voluntary")
        method_id = str(values["method_id"]).strip()
        method_state = str(values["state"])
        if not method_id:
            raise BodySystemsError("contraception method_id is required")
        if method_state not in {
            "considering",
            "chosen",
            "in_use",
            "discontinued",
            "unknown",
        }:
            raise BodySystemsError(f"unsupported contraception state: {method_state}")
        system["contraception_methods"][method_id] = {
            "state": method_state,
            "voluntary_choice": True,
        }
        system["consent_granted"] = False
        system["pregnancy_proven_or_excluded"] = False
    elif action == "record_health_observation":
        _record_observation(system, payload)
    elif action == "record_test_state":
        values = _exact_payload(
            payload,
            required=("test_id", "state"),
            optional=("result", "evidence_id"),
        )
        test_id = str(values["test_id"]).strip()
        test_state = str(values["state"])
        if not test_id:
            raise BodySystemsError("test_id is required")
        if test_state not in {
            "offered",
            "consented",
            "sample_collected",
            "pending",
            "result_recorded",
        }:
            raise BodySystemsError(f"unsupported test state: {test_state}")
        if test_state == "result_recorded" and (
            not str(values.get("result", "")).strip()
            or not str(values.get("evidence_id", "")).strip()
        ):
            raise BodySystemsError("recorded test result requires result and evidence_id")
        system["test_records"][test_id] = {
            "state": test_state,
            "result": values.get("result"),
            "evidence_id": values.get("evidence_id"),
            "diagnosis": None,
        }
    else:
        raise BodySystemsError(f"unsupported contraception/STI-health action: {action}")


def _grant_lease(
    system: dict[str, Any], event_at: datetime, payload: Mapping[str, Any]
) -> None:
    values = _exact_payload(
        payload,
        required=(
            "lease_id",
            "participants",
            "participant_maturity",
            "affirmative_participant_ids",
            "activity",
            "context_id",
            "expires_at_utc",
        ),
    )
    lease_id = str(values["lease_id"]).strip()
    participants = sorted({str(value).strip() for value in values["participants"]})
    affirmative = sorted(
        {str(value).strip() for value in values["affirmative_participant_ids"]}
    )
    maturity = {
        str(key).strip(): str(value).strip().lower()
        for key, value in dict(values["participant_maturity"]).items()
    }
    activity = str(values["activity"]).strip()
    context_id = str(values["context_id"]).strip()
    expires = _parse_utc(values["expires_at_utc"], "expires_at_utc")
    if not lease_id or lease_id in system["leases"]:
        raise ConsentLeaseError("lease_id is absent or already used")
    if len(participants) < 2 or any(not value for value in participants):
        raise ConsentLeaseError("at least two exact participants are required")
    if set(maturity) != set(participants) or any(
        maturity[value] != "confirmed_adult" for value in participants
    ):
        raise MaturityGateError("every lease participant must be confirmed_adult")
    if affirmative != participants:
        raise ConsentLeaseError("every participant must provide current affirmative consent")
    if not activity or not context_id:
        raise ConsentLeaseError("exact activity and context_id are required")
    if expires <= event_at:
        raise ConsentLeaseError("lease must expire after it is granted")
    system["leases"][lease_id] = {
        "lease_id": lease_id,
        "participants": participants,
        "activity": activity,
        "context_id": context_id,
        "granted_at_utc": event_at.isoformat(),
        "expires_at_utc": expires.isoformat(),
        "status": "active",
        "revoked_by": None,
        "revoked_at_utc": None,
        "revocation_reason": None,
        "action_performed": False,
    }


def _revoke_lease(
    system: dict[str, Any], event_at: datetime, payload: Mapping[str, Any], reason: str
) -> None:
    values = _exact_payload(payload, required=("lease_id", "participant_id"))
    lease_id = str(values["lease_id"])
    participant = str(values["participant_id"])
    lease = system["leases"].get(lease_id)
    if lease is None:
        raise ConsentLeaseError(f"unknown consent/action lease: {lease_id}")
    if participant not in lease["participants"]:
        raise ConsentLeaseError("only a participant can revoke this lease")
    if lease["status"] != "active":
        raise ConsentLeaseError("lease is no longer active")
    lease["status"] = "revoked"
    lease["revoked_by"] = participant
    lease["revoked_at_utc"] = event_at.isoformat()
    lease["revocation_reason"] = reason


def _apply_consent_event(
    system: dict[str, Any], event_at: datetime, action: str, payload: Mapping[str, Any]
) -> None:
    if action == "grant_lease":
        _grant_lease(system, event_at, payload)
    elif action == "revoke_lease":
        _revoke_lease(system, event_at, payload, "participant_revoked")
    elif action == "participant_uncertain":
        _revoke_lease(system, event_at, payload, "participant_uncertain")
    elif action == "participant_exit":
        _revoke_lease(system, event_at, payload, "participant_exit")
    elif action == "material_context_change":
        _revoke_lease(system, event_at, payload, "material_context_change")
    else:
        raise ConsentLeaseError(f"unsupported consent/action lease action: {action}")


def _apply_pregnancy_event(
    state: dict[str, Any], action: str, payload: Mapping[str, Any]
) -> None:
    if state["body_lane"] != "adult_female":
        raise BodySystemsError("pregnancy state is not applicable to adult_male lane")
    system = state["systems"]["pregnancy"]
    if action == "record_test_state":
        values = _exact_payload(
            payload,
            required=("test_state", "test_id"),
            optional=("evidence_id",),
        )
        test_state = str(values["test_state"])
        if test_state not in {
            "pending",
            "confirmed_positive",
            "confirmed_negative",
            "inconclusive",
        }:
            raise BodySystemsError(f"unsupported pregnancy test state: {test_state}")
        test_id = str(values["test_id"]).strip()
        if not test_id:
            raise BodySystemsError("pregnancy test_id is required")
        evidence_id = str(values.get("evidence_id", "")).strip()
        if test_state != "pending" and not evidence_id:
            raise BodySystemsError("pregnancy test result requires evidence_id")
        system["last_test_state"] = test_state
        if evidence_id and evidence_id not in system["evidence_ids"]:
            system["evidence_ids"].append(evidence_id)
        if test_state == "pending":
            system["phase"] = "test_pending"
        elif test_state == "confirmed_positive":
            system["phase"] = "confirmed"
        else:
            system["phase"] = "not_assessed"
    elif action == "set_phase":
        values = _exact_payload(payload, required=("phase", "evidence_id"))
        phase = str(values["phase"])
        evidence_id = str(values["evidence_id"]).strip()
        if phase not in {"confirmed", "continuing", "ended", "postpartum"}:
            raise BodySystemsError(f"unsupported pregnancy phase: {phase}")
        if not evidence_id:
            raise BodySystemsError("pregnancy phase transition requires evidence_id")
        current = system["phase"]
        allowed_from = {
            "confirmed": {"confirmed"},
            "continuing": {"confirmed", "continuing"},
            "ended": {"confirmed", "continuing", "ended"},
            "postpartum": {"ended", "postpartum"},
        }
        if current not in allowed_from[phase]:
            raise BodySystemsError(f"pregnancy phase transition {current} -> {phase} blocked")
        system["phase"] = phase
        if evidence_id not in system["evidence_ids"]:
            system["evidence_ids"].append(evidence_id)
    elif action == "set_timeline_mode":
        values = _exact_payload(
            payload, required=("mode", "voluntary_choice")
        )
        if system["phase"] not in {"confirmed", "continuing"}:
            raise BodySystemsError("timeline mode requires confirmed pregnancy state")
        if values["voluntary_choice"] is not True:
            raise BodySystemsError("pregnancy timeline choice must be voluntary")
        mode = str(values["mode"])
        if mode not in {"ordinary", "accelerated"}:
            raise BodySystemsError(f"unsupported pregnancy timeline mode: {mode}")
        system["timeline_mode"] = mode
    else:
        raise BodySystemsError(f"unsupported pregnancy action: {action}")


def apply_event(
    state: Mapping[str, Any],
    event: Mapping[str, Any],
    *,
    registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply one deterministic event and return a new JSON-compatible state."""

    _validate_state_truth(state)
    effective_registry = validate_registry(registry) if registry is not None else load_registry()
    if state["body_lane"] not in effective_registry["scope"]["adult_body_lanes"]:
        raise RegistryError("state lane is absent from semantic registry")
    if not isinstance(event, Mapping):
        raise BodySystemsError("event must be an object")
    allowed_event_keys = {"event_id", "domain", "action", "at_utc", "payload"}
    if set(event) != allowed_event_keys:
        raise BodySystemsError("event must contain exactly event_id/domain/action/at_utc/payload")
    event_id = str(event["event_id"]).strip()
    domain = str(event["domain"]).strip()
    action = str(event["action"]).strip()
    event_at = _parse_utc(event["at_utc"], "at_utc")
    payload = event["payload"]
    if not event_id or event_id in state["processed_event_ids"]:
        raise BodySystemsError("event_id is absent or already processed")
    if domain not in DOMAINS:
        raise BodySystemsError(f"unsupported body-system domain: {domain}")
    _require_adult(state)

    updated = deepcopy(dict(state))
    if domain in {"urinary", "bowel"}:
        _apply_elimination_event(updated["systems"][domain], domain, action, payload)
    elif domain == "menstrual_reproductive":
        _apply_menstrual_reproductive_event(updated, action, payload)
    elif domain == "contraception_sti_health":
        _apply_contraception_health_event(
            updated["systems"][domain], action, payload
        )
    elif domain == "consent_action_leases":
        _apply_consent_event(updated["systems"][domain], event_at, action, payload)
    elif domain == "pregnancy":
        _apply_pregnancy_event(updated, action, payload)

    updated["processed_event_ids"].append(event_id)
    updated["event_log"].append(
        {
            "event_id": event_id,
            "domain": domain,
            "action": action,
            "at_utc": event_at.isoformat(),
            "payload_sha256": canonical_sha256(payload),
        }
    )
    updated["revision"] = int(updated["revision"]) + 1
    _validate_state_truth(updated)
    return updated


def lease_allows(
    state: Mapping[str, Any],
    *,
    lease_id: str,
    participants: Sequence[str],
    activity: str,
    context_id: str,
    at_utc: str,
) -> bool:
    """Return whether an exact current consent/action lease remains valid."""

    _validate_state_truth(state)
    if state.get("maturity_status") != "confirmed_adult":
        return False
    lease = state["systems"]["consent_action_leases"]["leases"].get(lease_id)
    if not lease or lease.get("status") != "active":
        return False
    now = _parse_utc(at_utc, "at_utc")
    expires = _parse_utc(lease["expires_at_utc"], "expires_at_utc")
    return (
        sorted({str(value).strip() for value in participants})
        == lease["participants"]
        and str(activity).strip() == lease["activity"]
        and str(context_id).strip() == lease["context_id"]
        and now >= _parse_utc(lease["granted_at_utc"], "granted_at_utc")
        and now < expires
    )


def state_sha256(state: Mapping[str, Any]) -> str:
    """Validate and hash an exact prototype state."""

    _validate_state_truth(state)
    return canonical_sha256(state)


__all__ = [
    "BODY_LANES",
    "BODY_REPRESENTATIONS",
    "DOMAINS",
    "MODEL_ID",
    "MODEL_STATUS",
    "PRIVATE_SENSATION_DIMENSIONS",
    "BodySystemsError",
    "ConsentLeaseError",
    "DiagnosisInferenceError",
    "MaturityGateError",
    "RegistryError",
    "apply_event",
    "canonical_sha256",
    "curriculum_entitlement",
    "evaluate_private_solitary_choice",
    "initial_state",
    "lease_allows",
    "load_registry",
    "private_sensation_contract",
    "state_sha256",
    "validate_registry",
]
