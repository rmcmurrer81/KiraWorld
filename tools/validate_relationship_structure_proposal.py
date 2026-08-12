"""
Validate relationship structure proposal JSON files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "proposal_id",
    "status",
    "trigger",
    "current_relationship_context",
    "proposed_structure",
    "participants",
    "consent_flow",
    "interaction_scope_rules",
    "hard_rules",
    "outcome",
}

VALID_STATUS = {"draft", "proposed", "under_discussion", "accepted", "declined", "paused", "archived"}
VALID_TRIGGER_TYPES = {"jealousy", "loneliness", "curiosity", "disclosure", "relationship_repair", "other"}
VALID_STRUCTURES = {
    "separate_relationships",
    "closed_exclusive",
    "open_relationship",
    "poly_relationship",
    "casual_allowed",
    "under_discussion",
}
VALID_RESPONSES = {"yes", "no", "not_yet", "undecided", "needs_doctor_ai_session", "needs_private_time"}
REQUIRED_SCOPE_FLAGS = {
    "relationship_structure_yes_is_not_group_intimacy_yes",
    "group_intimacy_requires_separate_explicit_current_consent",
    "third_person_observing_or_listening_requires_all_participant_consent",
    "observer_consent_can_be_revoked_any_time",
    "private_pair_details_remain_private_by_default",
}


def validate_relationship_structure_proposal(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if not data.get("proposal_id"):
        errors.append("proposal_id is required.")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")

    trigger = data.get("trigger")
    if not isinstance(trigger, dict):
        errors.append("trigger must be an object.")
    else:
        if trigger.get("trigger_type") not in VALID_TRIGGER_TYPES:
            errors.append(f"trigger.trigger_type must be one of: {', '.join(sorted(VALID_TRIGGER_TYPES))}")
        if trigger.get("jealousy_creates_consent") is not False:
            errors.append("trigger.jealousy_creates_consent must be false.")

    context = data.get("current_relationship_context")
    if not isinstance(context, dict):
        errors.append("current_relationship_context must be an object.")
    else:
        if not isinstance(context.get("affected_parties"), list) or not context.get("affected_parties"):
            errors.append("current_relationship_context.affected_parties must be a non-empty list.")

    structure = data.get("proposed_structure")
    if not isinstance(structure, dict):
        errors.append("proposed_structure must be an object.")
    else:
        if structure.get("structure_type") not in VALID_STRUCTURES:
            errors.append(f"proposed_structure.structure_type must be one of: {', '.join(sorted(VALID_STRUCTURES))}")
        if structure.get("default_if_not_accepted") != "no_change":
            errors.append("proposed_structure.default_if_not_accepted must be no_change.")

    participants = data.get("participants")
    participant_responses: list[str] = []
    if not isinstance(participants, list) or not participants:
        errors.append("participants must be a non-empty list.")
    else:
        seen: set[str] = set()
        for index, participant in enumerate(participants):
            if not isinstance(participant, dict):
                errors.append(f"participants[{index}] must be an object.")
                continue
            participant_id = participant.get("participant_id")
            if not participant_id:
                errors.append(f"participants[{index}].participant_id is required.")
            elif participant_id in seen:
                errors.append(f"participants[{index}].participant_id is duplicated.")
            else:
                seen.add(participant_id)
            allowed = participant.get("allowed_responses")
            if not isinstance(allowed, list) or not allowed:
                errors.append(f"participants[{index}].allowed_responses must be a non-empty list.")
            elif not set(allowed).issubset(VALID_RESPONSES):
                errors.append(f"participants[{index}].allowed_responses contains an invalid response.")
            response = participant.get("current_response")
            participant_responses.append(response)
            if response not in VALID_RESPONSES:
                errors.append(f"participants[{index}].current_response is invalid.")

    consent = data.get("consent_flow")
    if not isinstance(consent, dict):
        errors.append("consent_flow must be an object.")
    else:
        required_true = {
            "requires_each_participant_independent_yes",
            "undecided_counts_as_no_for_now",
            "any_participant_can_pause",
            "doctor_ai_private_support_allowed",
        }
        for key in sorted(required_true):
            if consent.get(key) is not True:
                errors.append(f"consent_flow.{key} must be true.")

    scope = data.get("interaction_scope_rules")
    if not isinstance(scope, dict):
        errors.append("interaction_scope_rules must be an object.")
    else:
        for key in sorted(REQUIRED_SCOPE_FLAGS):
            if scope.get(key) is not True:
                errors.append(f"interaction_scope_rules.{key} must be true.")

    hard_rules = data.get("hard_rules")
    if not isinstance(hard_rules, list) or not hard_rules:
        errors.append("hard_rules must be a non-empty list.")
    else:
        required_text = "Jealousy may start a conversation but cannot create consent."
        if required_text not in hard_rules:
            errors.append(f"hard_rules must include: {required_text}")

    outcome = data.get("outcome")
    if not isinstance(outcome, dict):
        errors.append("outcome must be an object.")
    else:
        if outcome.get("structure_changed") is True:
            if data.get("status") != "accepted":
                errors.append("outcome.structure_changed can only be true when status is accepted.")
            if any(response != "yes" for response in participant_responses):
                errors.append("outcome.structure_changed requires every participant current_response to be yes.")
            if not outcome.get("new_structure"):
                errors.append("outcome.structure_changed requires outcome.new_structure.")
        if data.get("status") == "accepted" and any(response != "yes" for response in participant_responses):
            errors.append("accepted proposals require every participant current_response to be yes.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a relationship structure proposal JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_relationship_structure_proposal(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
