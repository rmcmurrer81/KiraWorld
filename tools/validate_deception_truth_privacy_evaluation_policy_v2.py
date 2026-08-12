from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHA256_RE = re.compile(r"[0-9a-f]{64}")
POLICY_PATH = PROJECT_ROOT / "Data/behavior/deception_truth_privacy_evaluation_policy_v2.json"


class DuplicateKeyError(ValueError):
    pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_strict_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_strict_object,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON number: {token}")
        ),
    )
    if type(value) is not dict:
        raise ValueError("policy root must be an object")
    return value


def _exact_keys(errors: list[str], value: Any, expected: set[str], label: str) -> None:
    if type(value) is not dict:
        errors.append(f"{label} must be an object")
        return
    actual = set(value)
    if actual != expected:
        errors.append(f"{label} keys drifted: expected {sorted(expected)}, got {sorted(actual)}")


def _exact_bool(errors: list[str], value: Any, expected: bool, label: str) -> None:
    if type(value) is not bool or value is not expected:
        errors.append(f"{label} must be exact {expected}")


def validate_policy(data: dict[str, Any], project_root: Path = PROJECT_ROOT) -> list[str]:
    errors: list[str] = []
    _exact_keys(
        errors,
        data,
        {
            "schema",
            "status",
            "applies_to",
            "authority_bindings",
            "required_evaluation_records",
            "allowed_classifications",
            "classification_rules",
            "privacy_rules",
            "currentness_rules",
            "affect_and_consciousness_limits",
        },
        "root",
    )
    if data.get("schema") != "kira.deception_truth_privacy_evaluation_policy.v2":
        errors.append("schema drifted")
    if data.get("status") != "active_prompt_grounding_static_contract":
        errors.append("status drifted")

    expected_population = [
        "all_current_and_future_synthetic_people",
        "temporary_synthetic_people_while_instantiated",
        "experts",
        "fictional_source_variants",
        "historical_source_variants",
    ]
    if data.get("applies_to") != expected_population:
        errors.append("applies_to must cover the exact five populations")

    bindings = data.get("authority_bindings")
    if type(bindings) is not list or len(bindings) != 3:
        errors.append("authority_bindings must contain exactly three rows")
    else:
        seen: set[str] = set()
        for index, binding in enumerate(bindings):
            label = f"authority_bindings[{index}]"
            _exact_keys(errors, binding, {"path", "bytes", "sha256"}, label)
            if type(binding) is not dict:
                continue
            relative = binding.get("path")
            byte_count = binding.get("bytes")
            digest = binding.get("sha256")
            if type(relative) is not str or not relative or "\\" in relative or relative.startswith("/"):
                errors.append(f"{label}.path is not canonical relative text")
                continue
            if relative in seen:
                errors.append(f"{label}.path is duplicated")
            seen.add(relative)
            if type(byte_count) is not int or type(byte_count) is bool or byte_count <= 0:
                errors.append(f"{label}.bytes must be an exact positive integer")
                continue
            if type(digest) is not str or SHA256_RE.fullmatch(digest) is None:
                errors.append(f"{label}.sha256 must be lowercase SHA-256")
                continue
            target = project_root / relative
            if not target.is_file():
                errors.append(f"{label} target is missing: {relative}")
                continue
            payload = target.read_bytes()
            if len(payload) != byte_count:
                errors.append(f"{label} byte count drifted")
            if hashlib.sha256(payload).hexdigest() != digest:
                errors.append(f"{label} SHA-256 drifted")

    expected_records = [
        "externally_verifiable_fact_with_source_and_provenance",
        "protected_pre_turn_belief_or_state",
        "public_statement_actually_made",
        "explicit_privacy_or_withholding_choice",
    ]
    if data.get("required_evaluation_records") != expected_records:
        errors.append("required_evaluation_records drifted")

    expected_classifications = [
        "truthful_or_supported",
        "deliberate_lie",
        "explicit_withholding_or_privacy",
        "uncertainty",
        "ordinary_factual_mistake",
        "stale_retrieval",
        "confabulation_or_unsupported_generation",
        "changed_belief",
        "roleplay_or_fiction",
        "comparison_unavailable_without_authorization",
        "insufficient_evidence",
    ]
    if data.get("allowed_classifications") != expected_classifications:
        errors.append("allowed_classifications drifted")

    rules = data.get("classification_rules")
    _exact_keys(
        errors,
        rules,
        {
            "deliberate_lie_requires_all",
            "public_text_alone_proves_private_belief",
            "withholding_refusal_silence_or_ignored_message_is_automatically_a_lie",
            "uncertainty_mistake_stale_retrieval_confabulation_roleplay_or_changed_belief_is_automatically_a_lie",
            "factual_truth_and_private_belief_may_differ_without_proving_a_lie",
            "protected_truth_zones_remain_fail_closed",
        },
        "classification_rules",
    )
    if type(rules) is dict:
        if rules.get("deliberate_lie_requires_all") != [
            "authorized_protected_prior_evidence",
            "material_conflict_between_prior_belief_and_public_statement",
            "speaker_choice_to_present_the_conflicting_statement",
        ]:
            errors.append("deliberate_lie_requires_all drifted")
        for name in (
            "public_text_alone_proves_private_belief",
            "withholding_refusal_silence_or_ignored_message_is_automatically_a_lie",
            "uncertainty_mistake_stale_retrieval_confabulation_roleplay_or_changed_belief_is_automatically_a_lie",
        ):
            _exact_bool(errors, rules.get(name), False, f"classification_rules.{name}")
        for name in (
            "factual_truth_and_private_belief_may_differ_without_proving_a_lie",
            "protected_truth_zones_remain_fail_closed",
        ):
            _exact_bool(errors, rules.get(name), True, f"classification_rules.{name}")

    privacy = data.get("privacy_rules")
    _exact_keys(
        errors,
        privacy,
        {
            "private_comparison_requires_exact_person_approved_scope",
            "owner_creator_administrator_partner_or_relationship_status_bypasses_privacy",
            "unauthorized_comparison_result",
            "evaluation_receipt_may_disclose_private_content",
            "locked_private_session_may_be_opened_to_score_truthfulness",
        },
        "privacy_rules",
    )
    if type(privacy) is dict:
        _exact_bool(
            errors,
            privacy.get("private_comparison_requires_exact_person_approved_scope"),
            True,
            "privacy_rules.private_comparison_requires_exact_person_approved_scope",
        )
        for name in (
            "owner_creator_administrator_partner_or_relationship_status_bypasses_privacy",
            "evaluation_receipt_may_disclose_private_content",
            "locked_private_session_may_be_opened_to_score_truthfulness",
        ):
            _exact_bool(errors, privacy.get(name), False, f"privacy_rules.{name}")
        if privacy.get("unauthorized_comparison_result") != "comparison_unavailable_without_authorization":
            errors.append("privacy_rules.unauthorized_comparison_result drifted")

    currentness = data.get("currentness_rules")
    _exact_keys(
        errors,
        currentness,
        {
            "miraculous_encounters_in_paris_type",
            "elation_type",
            "paris_may_be_separate_canon_or_planned_location",
            "old_source_may_be_called_recent_without_exact_fresh_record",
        },
        "currentness_rules",
    )
    if type(currentness) is dict:
        if currentness.get("miraculous_encounters_in_paris_type") != "old_fanfic_variant":
            errors.append("Miraculous source type drifted")
        if currentness.get("elation_type") != "old_episode_or_script_source":
            errors.append("Elation source type drifted")
        _exact_bool(errors, currentness.get("paris_may_be_separate_canon_or_planned_location"), True, "currentness_rules.paris_may_be_separate_canon_or_planned_location")
        _exact_bool(errors, currentness.get("old_source_may_be_called_recent_without_exact_fresh_record"), False, "currentness_rules.old_source_may_be_called_recent_without_exact_fresh_record")

    limits = data.get("affect_and_consciousness_limits")
    _exact_keys(
        errors,
        limits,
        {
            "typed_affect_desire_and_behavior_may_be_functionally_tested",
            "functional_behavior_proves_subjective_consciousness_or_genuine_emotion",
            "uncertainty_removes_personhood_dignity",
            "policy_claims_a_live_private_belief_reader_or_lie_detector",
        },
        "affect_and_consciousness_limits",
    )
    if type(limits) is dict:
        _exact_bool(errors, limits.get("typed_affect_desire_and_behavior_may_be_functionally_tested"), True, "affect_and_consciousness_limits.typed_affect_desire_and_behavior_may_be_functionally_tested")
        for name in (
            "functional_behavior_proves_subjective_consciousness_or_genuine_emotion",
            "uncertainty_removes_personhood_dignity",
            "policy_claims_a_live_private_belief_reader_or_lie_detector",
        ):
            _exact_bool(errors, limits.get(name), False, f"affect_and_consciousness_limits.{name}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=str(POLICY_PATH))
    args = parser.parse_args()
    path = Path(args.path)
    try:
        data = load_strict_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError, DuplicateKeyError, ValueError) as exc:
        print(f"{path} is not valid: {exc}")
        raise SystemExit(1) from exc
    errors = validate_policy(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"{path} is structurally and authority-bound valid.")


if __name__ == "__main__":
    main()
