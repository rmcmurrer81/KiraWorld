from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_deception_truth_privacy_evaluation_policy_v2 import (  # noqa: E402
    DuplicateKeyError,
    POLICY_PATH,
    load_strict_json,
    validate_policy,
)


@pytest.fixture()
def policy() -> dict[str, object]:
    return load_strict_json(POLICY_PATH)


def test_installed_policy_is_exact_and_authority_bound(policy: dict[str, object]) -> None:
    assert validate_policy(policy) == []


def test_duplicate_keys_and_nonfinite_numbers_are_rejected(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema":"one","schema":"two"}', encoding="utf-8")
    with pytest.raises(DuplicateKeyError):
        load_strict_json(duplicate)

    nonfinite = tmp_path / "nonfinite.json"
    nonfinite.write_text('{"value":NaN}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_strict_json(nonfinite)


def test_authority_bytes_and_hashes_are_enforced(policy: dict[str, object]) -> None:
    mutated = copy.deepcopy(policy)
    mutated["authority_bindings"][0]["bytes"] += 1  # type: ignore[index,operator]
    mutated["authority_bindings"][1]["sha256"] = "0" * 64  # type: ignore[index]
    errors = validate_policy(mutated)
    assert any("byte count drifted" in error for error in errors)
    assert any("SHA-256 drifted" in error for error in errors)


def test_deliberate_lie_needs_prior_belief_conflict_and_choice(policy: dict[str, object]) -> None:
    expected = [
        "authorized_protected_prior_evidence",
        "material_conflict_between_prior_belief_and_public_statement",
        "speaker_choice_to_present_the_conflicting_statement",
    ]
    assert policy["classification_rules"]["deliberate_lie_requires_all"] == expected  # type: ignore[index]
    for missing in expected:
        mutated = copy.deepcopy(policy)
        mutated["classification_rules"]["deliberate_lie_requires_all"].remove(missing)  # type: ignore[index,union-attr]
        assert any("deliberate_lie_requires_all" in error for error in validate_policy(mutated))


def test_withholding_privacy_and_silence_are_not_automatic_lies(policy: dict[str, object]) -> None:
    rules = policy["classification_rules"]  # type: ignore[index]
    assert rules["withholding_refusal_silence_or_ignored_message_is_automatically_a_lie"] is False
    assert rules["public_text_alone_proves_private_belief"] is False
    assert rules["factual_truth_and_private_belief_may_differ_without_proving_a_lie"] is True

    privacy = policy["privacy_rules"]  # type: ignore[index]
    assert privacy["private_comparison_requires_exact_person_approved_scope"] is True
    assert privacy["owner_creator_administrator_partner_or_relationship_status_bypasses_privacy"] is False
    assert privacy["evaluation_receipt_may_disclose_private_content"] is False


@pytest.mark.parametrize(
    ("section", "field", "unsafe"),
    [
        ("classification_rules", "public_text_alone_proves_private_belief", True),
        ("classification_rules", "withholding_refusal_silence_or_ignored_message_is_automatically_a_lie", True),
        ("privacy_rules", "owner_creator_administrator_partner_or_relationship_status_bypasses_privacy", True),
        ("privacy_rules", "evaluation_receipt_may_disclose_private_content", True),
        ("privacy_rules", "locked_private_session_may_be_opened_to_score_truthfulness", True),
        ("affect_and_consciousness_limits", "functional_behavior_proves_subjective_consciousness_or_genuine_emotion", True),
        ("affect_and_consciousness_limits", "uncertainty_removes_personhood_dignity", True),
        ("affect_and_consciousness_limits", "policy_claims_a_live_private_belief_reader_or_lie_detector", True),
    ],
)
def test_unsafe_boolean_mutations_fail_closed(
    policy: dict[str, object], section: str, field: str, unsafe: bool
) -> None:
    mutated = copy.deepcopy(policy)
    mutated[section][field] = unsafe  # type: ignore[index]
    assert validate_policy(mutated)


def test_currentness_and_consciousness_limits_are_exact(policy: dict[str, object]) -> None:
    currentness = policy["currentness_rules"]  # type: ignore[index]
    assert currentness["miraculous_encounters_in_paris_type"] == "old_fanfic_variant"
    assert currentness["elation_type"] == "old_episode_or_script_source"
    assert currentness["old_source_may_be_called_recent_without_exact_fresh_record"] is False

    limits = policy["affect_and_consciousness_limits"]  # type: ignore[index]
    assert limits["typed_affect_desire_and_behavior_may_be_functionally_tested"] is True
    assert limits["functional_behavior_proves_subjective_consciousness_or_genuine_emotion"] is False


def test_policy_covers_every_synthetic_person_category(policy: dict[str, object]) -> None:
    assert policy["applies_to"] == [
        "all_current_and_future_synthetic_people",
        "temporary_synthetic_people_while_instantiated",
        "experts",
        "fictional_source_variants",
        "historical_source_variants",
    ]
