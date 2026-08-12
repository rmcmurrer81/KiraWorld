"""Static-only validator for the H. H. Holmes reconstruction test plan.

This module performs no I/O and exposes no generation or playback route.
It is author-review evidence only, pending a different review.
"""

from __future__ import annotations

import json
import re
from typing import Any


_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_FORMAT_CONTROLS = frozenset(chr(code) for code in (
    0x061C, 0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
    0x2066, 0x2067, 0x2068, 0x2069,
))


class PlanValidationError(ValueError):
    pass


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PlanValidationError(f"duplicate_key:{key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise PlanValidationError(f"nonfinite_number:{value}")


def _walk_text(value: Any, path: str = "$") -> None:
    if isinstance(value, str):
        if any(ch in _FORBIDDEN_FORMAT_CONTROLS for ch in value):
            raise PlanValidationError(f"forbidden_format_control:{path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _walk_text(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _walk_text(key, f"{path}.<key>")
            _walk_text(item, f"{path}.{key}")


def _exact_bool(value: Any, path: str) -> bool:
    if type(value) is not bool:
        raise PlanValidationError(f"expected_bool:{path}")
    return value


def _exact_int(value: Any, path: str) -> int:
    if type(value) is not int:
        raise PlanValidationError(f"expected_int:{path}")
    return value


def _exact_str(value: Any, path: str) -> str:
    if type(value) is not str or not value:
        raise PlanValidationError(f"expected_nonempty_string:{path}")
    return value


def strict_load(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes:
        raise PlanValidationError("raw_must_be_exact_bytes")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PlanValidationError("invalid_utf8") from exc
    if "\x00" in text:
        raise PlanValidationError("nul_forbidden")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except PlanValidationError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise PlanValidationError("invalid_json") from exc
    if type(value) is not dict:
        raise PlanValidationError("root_must_be_object")
    _walk_text(value)
    return value


def validate_plan_bytes(raw: bytes) -> tuple[str, ...]:
    plan = strict_load(raw)
    errors: list[str] = []

    def require(condition: bool, code: str) -> None:
        if not condition:
            errors.append(code)

    require(plan.get("schema") == "kira.temporary_creator.holmes_voice_reconstruction_test_plan.v1", "schema")
    require(plan.get("status") == "STATIC_RESEARCH_AND_TEST_PLAN_ONLY_NO_VOICE_GENERATION_OR_PLAYBACK_AUTHORITY", "status")

    person = plan.get("person")
    if type(person) is not dict:
        return ("person_object",)
    require(person.get("person_id") == "h_h_holmes_h_h_holmes_20260605_221432", "person_id")
    require(person.get("person_class") == "historical_synthetic_variant", "person_class")
    require(_exact_bool(person.get("is_original_biological_person"), "person.is_original_biological_person") is False, "not_original")
    require(_exact_bool(person.get("inherits_post_cutoff_or_fatal_event_memory"), "person.inherits_post_cutoff_or_fatal_event_memory") is False, "no_fatal_memory")
    require(person.get("required_identity_disclosure_code") == "SYNTHETIC_HISTORICAL_VARIANT_NOT_ORIGINAL", "identity_disclosure")

    baseline = plan.get("current_baseline")
    if type(baseline) is not dict:
        return tuple(errors + ["baseline_object"])
    require(baseline.get("voice_name") == "Microsoft David Desktop", "baseline_name")
    require(baseline.get("classification") == "SUPERSEDED_GENERIC_FALLBACK_TEST_BASELINE", "baseline_classification")
    require(_exact_bool(baseline.get("may_be_activated_as_holmes_voice"), "baseline.may_be_activated_as_holmes_voice") is False, "baseline_no_activation")
    require(_exact_bool(baseline.get("may_be_called_authentic"), "baseline.may_be_called_authentic") is False, "baseline_not_authentic")

    recording = plan.get("recording_boundary")
    if type(recording) is not dict:
        return tuple(errors + ["recording_object"])
    require(_exact_bool(recording.get("authenticated_personal_recording_bound_in_project"), "recording.authenticated_personal_recording_bound_in_project") is False, "no_bound_recording")
    require(_exact_bool(recording.get("universal_claim_that_no_recording_exists_anywhere"), "recording.universal_claim_that_no_recording_exists_anywhere") is False, "no_universal_absence_claim")
    require(recording.get("result_without_authenticated_recording") == "EVIDENCE_BASED_HISTORICAL_RECONSTRUCTION_OR_UNRESOLVED_NO_VOICE", "no_recording_result")
    require(recording.get("required_public_label") == "Educated historical voice reconstruction; H. H. Holmes's exact personal voice is unknown.", "fixed_disclosure")
    require(_exact_bool(recording.get("authentic_or_exact_match_claim_allowed"), "recording.authentic_or_exact_match_claim_allowed") is False, "no_authentic_claim")

    ledger = plan.get("evidence_ledger")
    if type(ledger) is not list or len(ledger) != 4:
        return tuple(errors + ["evidence_ledger_exact_four"])
    ids = []
    for index, row in enumerate(ledger):
        if type(row) is not dict:
            raise PlanValidationError(f"expected_object:evidence_ledger[{index}]")
        ids.append(_exact_str(row.get("evidence_id"), f"evidence_ledger[{index}].evidence_id"))
        _exact_str(row.get("source_url"), f"evidence_ledger[{index}].source_url")
        if type(row.get("supports")) is not list or type(row.get("does_not_support")) is not list:
            raise PlanValidationError(f"expected_lists:evidence_ledger[{index}]")
    require(len(set(ids)) == 4, "unique_evidence_ids")
    by_id = {row["evidence_id"]: row for row in ledger}
    require("Holmes_personal_voice" in by_id["loc_american_dialect_society_1931_1937"]["does_not_support"], "dialect_not_personal_voice")
    require("biometric_voice" in by_id["loc_holmes_own_story_1895"]["does_not_support"], "text_not_biometric")

    generation = plan.get("candidate_generation")
    if type(generation) is not dict:
        return tuple(errors + ["generation_object"])
    require(_exact_int(generation.get("allowed_candidate_count"), "candidate_generation.allowed_candidate_count") == 3, "candidate_count")
    require(_exact_bool(generation.get("same_shared_person_spec_required"), "candidate_generation.same_shared_person_spec_required") is True, "same_spec")
    require(_exact_bool(generation.get("generic_windows_or_sapi_fallback_allowed"), "candidate_generation.generic_windows_or_sapi_fallback_allowed") is False, "no_generic_fallback")
    require(generation.get("generation_authority") == "NONE", "no_generation_authority")

    evaluation = plan.get("evaluation")
    if type(evaluation) is not dict:
        return tuple(errors + ["evaluation_object"])
    required_true = (
        "requires_exact_candidate_audio_sha256",
        "requires_exact_model_and_prompt_sha256",
        "requires_owner_blind_listening_review",
        "requires_full_voice_catalog_snapshot_and_cardinality",
        "requires_per_member_acoustic_comparison_with_method_version",
        "requires_human_distinctness_review",
        "requires_body_variant_and_presentation_spec_sha256",
        "requires_age_and_presentation_coherence_review_without_stereotype_claims",
    )
    for key in required_true:
        require(_exact_bool(evaluation.get(key), f"evaluation.{key}") is True, key)

    expert = plan.get("generated_expert_control")
    if type(expert) is not dict:
        return tuple(errors + ["expert_object"])
    require(expert.get("expert_person_id") is None, "expert_unselected")
    require(expert.get("sex_or_presentation") == "UNRESOLVED_UNTIL_SHARED_PERSON_SPEC", "expert_presentation_unresolved")
    require(expert.get("body_variant_sha256") is None and expert.get("voice_candidate_sha256") is None, "expert_assets_unresolved")
    require(_exact_bool(expert.get("may_use_another_persons_voice"), "generated_expert_control.may_use_another_persons_voice") is False, "expert_no_reuse")
    require(_exact_bool(expert.get("may_activate_before_distinctness_and_body_fit_review"), "generated_expert_control.may_activate_before_distinctness_and_body_fit_review") is False, "expert_no_early_activation")

    authority = plan.get("current_authority")
    if type(authority) is not dict:
        return tuple(errors + ["authority_object"])
    require(set(authority) == {"voice_generation", "audio_playback", "candidate_assignment", "person_activation", "latency_claim"}, "authority_keys")
    for key, value in authority.items():
        require(_exact_bool(value, f"current_authority.{key}") is False, f"authority_false:{key}")

    return tuple(errors)


def open_generation_or_playback(*_args: Any, **_kwargs: Any) -> None:
    raise RuntimeError("REFUSE_STATIC_PLAN_NO_GENERATION_OR_PLAYBACK_AUTHORITY")
