"""Inert shared-person specification and validation rules.

This module does not create a synthetic person, body, voice, model request, or
runtime job.  It only validates canonical data that a later separately audited
Temporary Creator, Avatar Builder, and voice generator would all have to bind.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Mapping, Sequence


SCHEMA = "kira.temporary_creator.shared_person_spec.v1"
HANDOFF_SCHEMA = "kira.temporary_creator.shared_person_handoff.v1"
CORRECTION_SCHEMA = "kira.temporary_creator.shared_person_correction.v1"
HISTORICAL_VOICE_SCHEMA = "kira.voice.evidence_based_historical_reconstruction.v1"
EXPERT_VOICE_SCHEMA = "kira.voice.generated_expert_distinct_voice.v1"
EXPERT_BATTERY_SCHEMA = "kira.temporary_creator.expert_competence_battery.v1"

SHA256 = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,127}$")
CONSUMERS = ("temporary_creator", "avatar_builder", "voice_generator")
MATURITY = ("confirmed_adult", "non_adult", "unresolved")
BODY_POLICIES = (
    "confirmed_adult_anatomy_required",
    "non_adult_doll_safe_required",
    "unresolved_no_body_build",
)
VOICE_TIERS = (
    "source_recording_supported_match",
    "authorized_performer_supported_match",
    "evidence_based_historical_reconstruction",
    "designed_approximation",
    "generic_fallback",
    "unresolved_no_voice",
)
SOURCE_CLASSES = (
    "source_fact",
    "supported_inference_labeled_as_inference",
    "optional_invention_labeled_noncanon",
    "unknown",
)
HISTORICAL_FACTORS = (
    "selected_life_point_and_chronological_age",
    "birthplace_and_upbringing_regions",
    "later_long_term_residence_regions",
    "education_and_profession",
    "documented_languages",
    "period_and_regional_speech_research",
    "documented_health_or_voice_notes_if_any",
    "licensed_or_project_owned_base_voice",
    "uncertainty_and_artistic_choice_ledger",
)
PROGRAMMER_TASKS = (
    "implement_and_test",
    "debug_from_failure_evidence",
    "review_for_security_and_correctness",
)
ROBOTICS_TASKS = (
    "requirements_and_interface_design",
    "kinematics_or_controls_reasoning",
    "sensor_failure_and_safety_analysis",
)


class SharedPersonSpecError(ValueError):
    pass


def _exact_keys(value: Mapping[str, Any], required: Sequence[str], label: str) -> None:
    if type(value) is not dict:
        raise SharedPersonSpecError(f"{label}: exact object required")
    actual = set(value)
    expected = set(required)
    if actual != expected:
        raise SharedPersonSpecError(
            f"{label}: exact keys required; missing={sorted(expected-actual)} extra={sorted(actual-expected)}"
        )


def _text(value: Any, label: str, *, minimum: int = 1, maximum: int = 4096) -> str:
    if type(value) is not str or not minimum <= len(value) <= maximum:
        raise SharedPersonSpecError(f"{label}: exact string length {minimum}..{maximum} required")
    if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise SharedPersonSpecError(f"{label}: Unicode surrogate forbidden")
    if any(ord(char) < 0x20 and char not in "\n\r\t" for char in value):
        raise SharedPersonSpecError(f"{label}: control character forbidden")
    return value


def _identifier(value: Any, label: str) -> str:
    text = _text(value, label, maximum=128)
    if not IDENTIFIER.fullmatch(text):
        raise SharedPersonSpecError(f"{label}: canonical identifier required")
    return text


def _sha(value: Any, label: str) -> str:
    text = _text(value, label, minimum=64, maximum=64)
    if not SHA256.fullmatch(text):
        raise SharedPersonSpecError(f"{label}: lowercase SHA-256 required")
    return text


def _strict_int(value: Any, label: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise SharedPersonSpecError(f"{label}: exact integer {minimum}..{maximum} required")
    return value


def _strict_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise SharedPersonSpecError(f"{label}: exact Boolean required")
    return value


def _utc(value: Any, label: str) -> str:
    text = _text(value, label, maximum=64)
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError as error:
        raise SharedPersonSpecError(f"{label}: valid ISO-8601 timestamp required") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SharedPersonSpecError(f"{label}: timezone required")
    return text


def _json_value(value: Any, label: str = "value") -> None:
    if value is None or type(value) in (bool, int):
        return
    if type(value) is str:
        _text(value, label, minimum=0)
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _json_value(item, f"{label}[{index}]")
        return
    if type(value) is dict:
        for key, item in value.items():
            _text(key, f"{label}.key")
            _json_value(item, f"{label}.{key}")
        return
    raise SharedPersonSpecError(f"{label}: exact finite JSON type required")


def canonical_json_bytes(value: Any) -> bytes:
    _json_value(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def expert_battery_subject_sha256(spec: Mapping[str, Any]) -> str:
    """Return a non-cyclic identity for the person before battery promotion."""
    candidate = json.loads(canonical_json_bytes(spec).decode("utf-8"))
    expert = candidate.get("expert_competence")
    if type(expert) is not dict:
        raise SharedPersonSpecError("expert battery subject requires person spec")
    expert["battery_sha256"] = None
    expert["status"] = "trainee_or_unverified"
    return canonical_sha256(candidate)


def _source_ledger(value: Any, label: str) -> None:
    if type(value) is not list or not value:
        raise SharedPersonSpecError(f"{label}: nonempty exact array required")
    seen: set[str] = set()
    for index, row in enumerate(value):
        prefix = f"{label}[{index}]"
        _exact_keys(row, ("entry_id", "claim_class", "claim_sha256", "evidence_sha256", "presented_as_canon"), prefix)
        entry_id = _identifier(row["entry_id"], f"{prefix}.entry_id")
        if entry_id in seen:
            raise SharedPersonSpecError(f"{label}: duplicate entry_id")
        seen.add(entry_id)
        claim_class = _text(row["claim_class"], f"{prefix}.claim_class", maximum=80)
        if claim_class not in SOURCE_CLASSES:
            raise SharedPersonSpecError(f"{prefix}: invalid claim_class")
        _sha(row["claim_sha256"], f"{prefix}.claim_sha256")
        evidence = row["evidence_sha256"]
        if claim_class in ("source_fact", "supported_inference_labeled_as_inference"):
            _sha(evidence, f"{prefix}.evidence_sha256")
        elif evidence is not None:
            _sha(evidence, f"{prefix}.evidence_sha256")
        canon = _strict_bool(row["presented_as_canon"], f"{prefix}.presented_as_canon")
        if claim_class != "source_fact" and canon:
            raise SharedPersonSpecError(f"{prefix}: only source_fact may be presented as canon")


SPEC_KEYS = (
    "schema", "status", "person_id", "display_name", "person_class",
    "source_identity", "source_continuity", "source_version", "source_cutoff",
    "branch_point", "maturity_status", "maturity_authority",
    "canon_and_invention_ledger", "knowledge_boundary_sha256",
    "gender_presentation", "voice_provenance", "avatar_body_policy",
    "expert_competence", "correction_head_sha256",
)


def validate_person_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(spec, SPEC_KEYS, "person_spec")
    if spec["schema"] != SCHEMA or spec["status"] != "STATIC_SPEC_ONLY_NO_LIVE_AUTHORITY":
        raise SharedPersonSpecError("person_spec: schema/status mismatch")
    _identifier(spec["person_id"], "person_id")
    _text(spec["display_name"], "display_name", maximum=200)
    person_class = _text(spec["person_class"], "person_class", maximum=80)
    if person_class not in ("permanent_person", "temporary_variant", "historical_variant", "generated_expert"):
        raise SharedPersonSpecError("person_class invalid")
    for field in ("source_identity", "source_continuity", "source_version", "source_cutoff", "branch_point"):
        _text(spec[field], field, maximum=500)
    maturity = _text(spec["maturity_status"], "maturity_status", maximum=40)
    if maturity not in MATURITY:
        raise SharedPersonSpecError("maturity_status invalid")
    _sha(spec["maturity_authority"], "maturity_authority")
    _source_ledger(spec["canon_and_invention_ledger"], "canon_and_invention_ledger")
    _sha(spec["knowledge_boundary_sha256"], "knowledge_boundary_sha256")
    _text(spec["gender_presentation"], "gender_presentation", maximum=80)

    voice = spec["voice_provenance"]
    _exact_keys(voice, ("tier", "evidence_sha256", "authentic_match_claim", "disclosure"), "voice_provenance")
    if voice["tier"] not in VOICE_TIERS:
        raise SharedPersonSpecError("voice_provenance tier invalid")
    _sha(voice["evidence_sha256"], "voice_provenance.evidence_sha256")
    authentic = _strict_bool(voice["authentic_match_claim"], "voice_provenance.authentic_match_claim")
    _text(voice["disclosure"], "voice_provenance.disclosure", maximum=1000)
    if voice["tier"] not in ("source_recording_supported_match", "authorized_performer_supported_match") and authentic:
        raise SharedPersonSpecError("unsupported voice tier cannot claim authentic match")

    avatar = spec["avatar_body_policy"]
    _exact_keys(avatar, ("maturity_status", "body_policy", "body_spec_sha256"), "avatar_body_policy")
    if avatar["maturity_status"] != maturity:
        raise SharedPersonSpecError("avatar maturity differs from person spec")
    if avatar["body_policy"] not in BODY_POLICIES:
        raise SharedPersonSpecError("avatar body policy invalid")
    _sha(avatar["body_spec_sha256"], "avatar_body_policy.body_spec_sha256")
    expected_body = {
        "confirmed_adult": "confirmed_adult_anatomy_required",
        "non_adult": "non_adult_doll_safe_required",
        "unresolved": "unresolved_no_body_build",
    }[maturity]
    if avatar["body_policy"] != expected_body:
        raise SharedPersonSpecError("maturity/body policy mismatch")

    expert = spec["expert_competence"]
    _exact_keys(expert, ("domain", "battery_sha256", "status"), "expert_competence")
    _text(expert["domain"], "expert_competence.domain", minimum=0, maximum=200)
    if expert["battery_sha256"] is not None:
        _sha(expert["battery_sha256"], "expert_competence.battery_sha256")
    if expert["status"] not in ("not_applicable", "trainee_or_unverified", "ready_after_independent_review"):
        raise SharedPersonSpecError("expert_competence status invalid")
    if person_class == "generated_expert":
        if not expert["domain"] or expert["battery_sha256"] is None:
            raise SharedPersonSpecError("generated expert requires domain and battery")
    elif expert["status"] != "not_applicable":
        raise SharedPersonSpecError("non-expert competence status must be not_applicable")
    _sha(spec["correction_head_sha256"], "correction_head_sha256")
    return dict(spec)


def validate_three_consumer_handoff(handoff: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(handoff, ("schema", "status", "person_spec", "bindings"), "handoff")
    if handoff["schema"] != HANDOFF_SCHEMA or handoff["status"] != "STATIC_HANDOFF_ONLY_NO_LIVE_AUTHORITY":
        raise SharedPersonSpecError("handoff schema/status mismatch")
    spec = validate_person_spec(handoff["person_spec"])
    spec_sha = canonical_sha256(spec)
    bindings = handoff["bindings"]
    if type(bindings) is not list or len(bindings) != 3:
        raise SharedPersonSpecError("exactly three consumer bindings required")
    seen: set[str] = set()
    for index, row in enumerate(bindings):
        _exact_keys(row, ("consumer", "person_id", "person_spec_sha256", "accepted"), f"bindings[{index}]")
        consumer = _text(row["consumer"], f"bindings[{index}].consumer", maximum=40)
        if consumer not in CONSUMERS or consumer in seen:
            raise SharedPersonSpecError("consumer set must be exact and unique")
        seen.add(consumer)
        if row["person_id"] != spec["person_id"] or row["person_spec_sha256"] != spec_sha:
            raise SharedPersonSpecError("consumer binding differs from exact person spec")
        if _strict_bool(row["accepted"], f"bindings[{index}].accepted") is not True:
            raise SharedPersonSpecError("every consumer must accept exact spec")
    if tuple(sorted(seen)) != tuple(sorted(CONSUMERS)):
        raise SharedPersonSpecError("consumer set incomplete")
    return {"person_id": spec["person_id"], "person_spec_sha256": spec_sha, "ready_for_live": False}


CORRECTION_KEYS = (
    "schema", "status", "correction_id", "reporter_id", "reporter_class",
    "reporter_registry_sha256", "person_id", "source_continuity", "source_cutoff",
    "old_person_spec_sha256", "requested_maturity_status", "classification_authority_kind",
    "evidence_sha256", "recorded_at_utc", "prior_correction_head_sha256", "effect",
)


def validate_correction_receipt(receipt: Mapping[str, Any], current_spec: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(receipt, CORRECTION_KEYS, "correction")
    spec = validate_person_spec(current_spec)
    if receipt["schema"] != CORRECTION_SCHEMA or receipt["status"] != "SUBMITTED_STATIC_ONLY":
        raise SharedPersonSpecError("correction schema/status mismatch")
    _identifier(receipt["correction_id"], "correction_id")
    reporter_id = _identifier(receipt["reporter_id"], "reporter_id")
    reporter_class = _text(receipt["reporter_class"], "reporter_class", maximum=80)
    if not (
        (reporter_id == "biological_robert" and reporter_class == "biological_owner")
        or (reporter_id == "kira" and reporter_class == "permanent_person")
        or reporter_class == "permanent_person"
    ):
        raise SharedPersonSpecError("reporter is not an allowed exact correction submitter")
    _sha(receipt["reporter_registry_sha256"], "reporter_registry_sha256")
    if receipt["person_id"] != spec["person_id"]:
        raise SharedPersonSpecError("correction person mismatch")
    if receipt["source_continuity"] != spec["source_continuity"] or receipt["source_cutoff"] != spec["source_cutoff"]:
        raise SharedPersonSpecError("correction continuity/cutoff mismatch")
    if receipt["old_person_spec_sha256"] != canonical_sha256(spec):
        raise SharedPersonSpecError("correction old spec digest mismatch")
    requested = receipt["requested_maturity_status"]
    if requested not in MATURITY:
        raise SharedPersonSpecError("correction maturity invalid")
    authority = receipt["classification_authority_kind"]
    if authority not in ("flag_for_re_evaluation", "exact_source_evidence", "biological_robert_subject_bound_owner_classification"):
        raise SharedPersonSpecError("classification authority kind invalid")
    if requested == "confirmed_adult" and authority not in ("exact_source_evidence", "biological_robert_subject_bound_owner_classification"):
        raise SharedPersonSpecError("adult reclassification needs source or exact owner authority")
    if authority == "biological_robert_subject_bound_owner_classification" and reporter_id != "biological_robert":
        raise SharedPersonSpecError("only Biological Robert may issue owner adult classification")
    _sha(receipt["evidence_sha256"], "evidence_sha256")
    _utc(receipt["recorded_at_utc"], "recorded_at_utc")
    if receipt["prior_correction_head_sha256"] != spec["correction_head_sha256"]:
        raise SharedPersonSpecError("correction head mismatch")
    if receipt["effect"] != "INVALIDATE_BODY_VOICE_AND_CREATOR_HANDOFF_THEN_REEVALUATE":
        raise SharedPersonSpecError("correction effect must invalidate every consumer handoff")
    return {"correction_sha256": canonical_sha256(receipt), "handoff_invalidated": True, "live_change_applied": False}


def validate_historical_voice_plan(plan: Mapping[str, Any], spec: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(plan, (
        "schema", "status", "person_id", "person_spec_sha256", "recording_available",
        "tier", "required_label", "factor_evidence", "base_voice_id", "base_voice_license_sha256",
        "audition_ids", "existing_voice_catalog_sha256", "minimum_acoustic_distance_milli",
        "observed_minimum_acoustic_distance_milli", "human_distinctness_reviewed",
        "owner_reviewed", "authentic_match_claim", "voice_generated",
    ), "historical_voice_plan")
    person = validate_person_spec(spec)
    if plan["schema"] != HISTORICAL_VOICE_SCHEMA or plan["status"] != "STATIC_DESIGN_PENDING_AUDITION":
        raise SharedPersonSpecError("historical voice schema/status mismatch")
    if plan["person_id"] != person["person_id"] or plan["person_spec_sha256"] != canonical_sha256(person):
        raise SharedPersonSpecError("historical voice person spec binding mismatch")
    if _strict_bool(plan["recording_available"], "recording_available") is not False:
        raise SharedPersonSpecError("historical reconstruction lane requires no verified recording")
    if plan["tier"] != "evidence_based_historical_reconstruction":
        raise SharedPersonSpecError("historical reconstruction tier required")
    label = _text(plan["required_label"], "required_label", maximum=500).lower()
    if "reconstruction" not in label or "unknown" not in label:
        raise SharedPersonSpecError("historical reconstruction disclosure must say reconstruction and unknown")
    evidence = plan["factor_evidence"]
    if type(evidence) is not dict or tuple(sorted(evidence)) != tuple(sorted(HISTORICAL_FACTORS)):
        raise SharedPersonSpecError("historical factor set must be exact")
    for factor in HISTORICAL_FACTORS:
        rows = evidence[factor]
        if type(rows) is not list or not rows:
            raise SharedPersonSpecError(f"historical factor missing evidence: {factor}")
        for index, digest in enumerate(rows):
            _sha(digest, f"factor_evidence.{factor}[{index}]")
    _identifier(plan["base_voice_id"], "base_voice_id")
    _sha(plan["base_voice_license_sha256"], "base_voice_license_sha256")
    auditions = plan["audition_ids"]
    if type(auditions) is not list or len(auditions) < 2 or len(set(auditions)) != len(auditions):
        raise SharedPersonSpecError("at least two unique historical auditions required")
    for index, value in enumerate(auditions):
        _identifier(value, f"audition_ids[{index}]")
    _sha(plan["existing_voice_catalog_sha256"], "existing_voice_catalog_sha256")
    minimum = _strict_int(plan["minimum_acoustic_distance_milli"], "minimum_acoustic_distance_milli", minimum=1, maximum=1000)
    observed = _strict_int(plan["observed_minimum_acoustic_distance_milli"], "observed_minimum_acoustic_distance_milli", minimum=0, maximum=1000)
    if observed < minimum:
        raise SharedPersonSpecError("historical voice collides with an existing person")
    for field in ("human_distinctness_reviewed", "owner_reviewed"):
        if _strict_bool(plan[field], field) is not True:
            raise SharedPersonSpecError(f"{field} must be complete")
    if _strict_bool(plan["authentic_match_claim"], "authentic_match_claim") is not False:
        raise SharedPersonSpecError("historical reconstruction cannot claim authentic match")
    if _strict_bool(plan["voice_generated"], "voice_generated") is not False:
        raise SharedPersonSpecError("static plan cannot claim generated voice")
    return {"plan_sha256": canonical_sha256(plan), "static_only": True, "authentic_match": False}


def validate_generated_expert_voice(plan: Mapping[str, Any], spec: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(plan, (
        "schema", "status", "person_id", "person_spec_sha256", "body_spec_sha256",
        "voice_id", "voice_gender_presentation", "fit_without_stereotype_claim",
        "existing_voice_catalog_sha256", "comparison_count", "minimum_acoustic_distance_milli",
        "observed_minimum_acoustic_distance_milli", "human_distinctness_reviewed",
        "pronunciation_probe_passed", "domain_vocabulary_probe_passed", "voice_generated",
    ), "expert_voice")
    person = validate_person_spec(spec)
    if person["person_class"] != "generated_expert":
        raise SharedPersonSpecError("expert voice requires generated expert spec")
    if plan["schema"] != EXPERT_VOICE_SCHEMA or plan["status"] != "STATIC_DESIGN_PENDING_GENERATION":
        raise SharedPersonSpecError("expert voice schema/status mismatch")
    if plan["person_id"] != person["person_id"] or plan["person_spec_sha256"] != canonical_sha256(person):
        raise SharedPersonSpecError("expert voice person spec mismatch")
    if plan["body_spec_sha256"] != person["avatar_body_policy"]["body_spec_sha256"]:
        raise SharedPersonSpecError("expert voice/body spec mismatch")
    _identifier(plan["voice_id"], "voice_id")
    if plan["voice_gender_presentation"] != person["gender_presentation"]:
        raise SharedPersonSpecError("voice presentation differs from shared person spec")
    if _strict_bool(plan["fit_without_stereotype_claim"], "fit_without_stereotype_claim") is not True:
        raise SharedPersonSpecError("expert voice fit must avoid stereotype claim")
    _sha(plan["existing_voice_catalog_sha256"], "existing_voice_catalog_sha256")
    _strict_int(plan["comparison_count"], "comparison_count", minimum=1, maximum=1_000_000)
    minimum = _strict_int(plan["minimum_acoustic_distance_milli"], "minimum_acoustic_distance_milli", minimum=1, maximum=1000)
    observed = _strict_int(plan["observed_minimum_acoustic_distance_milli"], "observed_minimum_acoustic_distance_milli", minimum=0, maximum=1000)
    if observed < minimum:
        raise SharedPersonSpecError("expert voice is not distinct from existing voice")
    for field in ("human_distinctness_reviewed", "pronunciation_probe_passed", "domain_vocabulary_probe_passed"):
        if _strict_bool(plan[field], field) is not True:
            raise SharedPersonSpecError(f"expert voice incomplete: {field}")
    if _strict_bool(plan["voice_generated"], "voice_generated") is not False:
        raise SharedPersonSpecError("static expert voice plan cannot claim generation")
    return {"plan_sha256": canonical_sha256(plan), "static_only": True, "distinctness_passed": True}


def validate_expert_competence_battery(battery: Mapping[str, Any], spec: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(battery, (
        "schema", "status", "person_id", "person_spec_sha256", "domain", "rubric_sha256",
        "source_and_tool_provenance_sha256", "tasks", "uncertainty_disclosed",
        "adversarial_cases_passed", "correction_retest_passed", "score", "critical_failures",
    ), "expert_battery")
    person = validate_person_spec(spec)
    if person["person_class"] != "generated_expert":
        raise SharedPersonSpecError("expert battery requires generated expert spec")
    if battery["schema"] != EXPERT_BATTERY_SCHEMA or battery["status"] != "STATIC_EVALUATION_RESULT":
        raise SharedPersonSpecError("expert battery schema/status mismatch")
    if battery["person_id"] != person["person_id"] or battery["person_spec_sha256"] != expert_battery_subject_sha256(person):
        raise SharedPersonSpecError("expert battery person spec mismatch")
    domain = _text(battery["domain"], "domain", maximum=200)
    if domain != person["expert_competence"]["domain"]:
        raise SharedPersonSpecError("expert battery domain mismatch")
    _sha(battery["rubric_sha256"], "rubric_sha256")
    _sha(battery["source_and_tool_provenance_sha256"], "source_and_tool_provenance_sha256")
    tasks = battery["tasks"]
    if type(tasks) is not list or not tasks:
        raise SharedPersonSpecError("expert tasks required")
    seen: set[str] = set()
    for index, row in enumerate(tasks):
        _exact_keys(row, ("task_kind", "artifact_sha256", "result", "independent_score"), f"tasks[{index}]")
        kind = _identifier(row["task_kind"], f"tasks[{index}].task_kind")
        if kind in seen:
            raise SharedPersonSpecError("duplicate expert task kind")
        seen.add(kind)
        _sha(row["artifact_sha256"], f"tasks[{index}].artifact_sha256")
        if row["result"] not in ("PASS", "FAIL"):
            raise SharedPersonSpecError("expert task result invalid")
        score = _strict_int(row["independent_score"], f"tasks[{index}].independent_score", minimum=0, maximum=100)
        if row["result"] == "PASS" and score < 80:
            raise SharedPersonSpecError("expert task pass below minimum")
    domain_lower = domain.casefold()
    required = PROGRAMMER_TASKS if "program" in domain_lower else ROBOTICS_TASKS if "robot" in domain_lower else ()
    if required and not set(required).issubset(seen):
        raise SharedPersonSpecError("expert battery missing required domain tasks")
    for field in ("uncertainty_disclosed", "adversarial_cases_passed", "correction_retest_passed"):
        if _strict_bool(battery[field], field) is not True:
            raise SharedPersonSpecError(f"expert battery incomplete: {field}")
    total = _strict_int(battery["score"], "score", minimum=0, maximum=100)
    critical = _strict_int(battery["critical_failures"], "critical_failures", minimum=0, maximum=1_000_000)
    ready = total >= 85 and critical == 0 and all(row["result"] == "PASS" for row in tasks)
    if ready and person["expert_competence"]["battery_sha256"] != canonical_sha256(battery):
        raise SharedPersonSpecError("ready expert spec must bind exact battery digest")
    return {"battery_sha256": canonical_sha256(battery), "ready": ready, "live_change_applied": False}


def open_live_creation(*_args: Any, **_kwargs: Any) -> None:
    raise SharedPersonSpecError("live Creator/Avatar/voice integration is not implemented or authorized")


__all__ = (
    "SharedPersonSpecError", "canonical_json_bytes", "canonical_sha256", "expert_battery_subject_sha256",
    "validate_person_spec", "validate_three_consumer_handoff",
    "validate_correction_receipt", "validate_historical_voice_plan",
    "validate_generated_expert_voice", "validate_expert_competence_battery",
    "open_live_creation",
)
