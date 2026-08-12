"""
Validate relationship stage track JSON files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "stage_track_id",
    "relationship_id",
    "current_stage",
    "stage_history",
    "available_transitions",
    "hard_gates",
    "privacy_notes",
    "gate_status",
    "third_party_considerations",
    "avatar_preview_gate",
    "shared_memory_gate",
    "status",
}

VALID_STAGES = {
    "friendship",
    "close_friendship",
    "emotionally_intimate_friendship",
    "shared_intimate_history_friendship",
    "unspoken_romantic_tension",
    "reopened_romantic_tension",
    "mutual_romantic_acknowledgment",
    "private_romantic_relationship",
    "known_romantic_relationship",
    "adult_intimate_relationship",
    "paused",
    "cooling",
}
VALID_STATUS = {"draft", "active", "paused", "archived"}
VALID_PREVIEW_LEVELS = {
    "none",
    "feature_only",
    "shoulders_up",
    "clothed_body",
    "full_body_feedback",
}
VALID_MEMORY_SCOPES = {
    "none",
    "summary",
    "emotional_meaning",
    "verbal_details_only",
    "non_intimate_lead_in",
    "selected_zones",
    "one_time_full_replay",
    "full_replay",
}


def validate_relationship_stage(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if not data.get("stage_track_id"):
        errors.append("stage_track_id is required.")
    if not data.get("relationship_id"):
        errors.append("relationship_id is required.")
    if data.get("current_stage") not in VALID_STAGES:
        errors.append(f"current_stage must be one of: {', '.join(sorted(VALID_STAGES))}")
    if data.get("status") not in VALID_STATUS:
        errors.append(f"status must be one of: {', '.join(sorted(VALID_STATUS))}")

    if not isinstance(data.get("stage_history"), list):
        errors.append("stage_history must be a list.")
    transitions = data.get("available_transitions")
    if not isinstance(transitions, list) or not transitions:
        errors.append("available_transitions must be a non-empty list.")
    else:
        for index, transition in enumerate(transitions):
            if not isinstance(transition, dict):
                errors.append(f"available_transitions[{index}] must be an object.")
                continue
            if transition.get("to_stage") not in VALID_STAGES:
                errors.append(f"available_transitions[{index}].to_stage is invalid.")
            if not isinstance(transition.get("requirements"), list) or not transition.get("requirements"):
                errors.append(f"available_transitions[{index}].requirements must be a non-empty list.")

    hard_gates = data.get("hard_gates")
    if not isinstance(hard_gates, list) or not hard_gates:
        errors.append("hard_gates must be a non-empty list.")
    else:
        required_gate_text = "No adult/intimate relationship without explicit current consent."
        if required_gate_text not in hard_gates:
            errors.append(f"hard_gates must include: {required_gate_text}")

    raw_gate_status = data.get("gate_status")
    gate_status = raw_gate_status if isinstance(raw_gate_status, dict) else {}

    if data.get("current_stage") == "adult_intimate_relationship":
        required_true = {
            "adult_only_confirmed",
            "explicit_current_consent",
            "locked_door_privacy_required",
            "locked_door_privacy_available",
            "relationship_state_supports",
            "no_unresolved_blockers",
        }
        for key in sorted(required_true):
            if gate_status.get(key) is not True:
                errors.append(f"adult_intimate_relationship requires gate_status.{key} true.")

    if not isinstance(raw_gate_status, dict):
        errors.append("gate_status must be an object.")
    else:
        for key, value in raw_gate_status.items():
            if not isinstance(value, bool):
                errors.append(f"gate_status.{key} must be true or false.")

    if data.get("current_stage") == "private_romantic_relationship":
        if gate_status.get("mutual_romantic_acknowledgment") is not True:
            errors.append("private_romantic_relationship requires mutual romantic acknowledgment.")
        if gate_status.get("private_relationship_agreement") is not True:
            errors.append("private_romantic_relationship requires a private relationship agreement.")
        if gate_status.get("locked_door_privacy_available") is not True:
            errors.append("private_romantic_relationship requires locked-door privacy available.")

    third_party = data.get("third_party_considerations")
    if not isinstance(third_party, dict):
        errors.append("third_party_considerations must be an object.")
    elif data.get("current_stage") == "known_romantic_relationship":
        if third_party.get("disclosure_plan_required") is not True:
            errors.append("known_romantic_relationship requires a disclosure plan requirement.")
        if not third_party.get("disclosure_plan"):
            errors.append("known_romantic_relationship requires a disclosure plan.")

    avatar_gate = data.get("avatar_preview_gate")
    if not isinstance(avatar_gate, dict):
        errors.append("avatar_preview_gate must be an object.")
    else:
        preview_level = avatar_gate.get("preview_level")
        if preview_level not in VALID_PREVIEW_LEVELS:
            errors.append(f"avatar_preview_gate.preview_level must be one of: {', '.join(sorted(VALID_PREVIEW_LEVELS))}")
        if avatar_gate.get("avatar_preview_allowed") is True:
            if avatar_gate.get("owner_choice_required") is not True:
                errors.append("avatar preview cannot be allowed without owner_choice_required true.")
            if avatar_gate.get("owner_has_chosen_to_share") is not True:
                errors.append("avatar preview cannot be allowed until owner_has_chosen_to_share is true.")
            if preview_level == "none":
                errors.append("avatar preview cannot be allowed with preview_level none.")
            if avatar_gate.get("saving_or_copying_allowed") is True:
                errors.append("avatar preview gate must not allow saving or copying by default.")

    memory_gate = data.get("shared_memory_gate")
    if not isinstance(memory_gate, dict):
        errors.append("shared_memory_gate must be an object.")
    else:
        allowed_scope = memory_gate.get("allowed_scope")
        if allowed_scope not in VALID_MEMORY_SCOPES:
            errors.append(f"shared_memory_gate.allowed_scope must be one of: {', '.join(sorted(VALID_MEMORY_SCOPES))}")
        if memory_gate.get("shared_intimate_memory_access_allowed") is True:
            if memory_gate.get("all_involved_permanent_participants_consented") is not True:
                errors.append("shared intimate memory access cannot be allowed without all involved permanent participant consent.")
            if allowed_scope == "none":
                errors.append("shared intimate memory access cannot be allowed with allowed_scope none.")
        if memory_gate.get("visual_body_exposure_allowed") is True:
            if memory_gate.get("all_involved_permanent_participants_consented") is not True:
                errors.append("visual body exposure cannot be allowed without all involved permanent participant consent.")
            if memory_gate.get("shared_intimate_memory_access_allowed") is not True:
                errors.append("visual body exposure requires shared intimate memory access allowed.")
        if memory_gate.get("permanent_replay_access_allowed") is True:
            if memory_gate.get("all_involved_permanent_participants_consented") is not True:
                errors.append("permanent replay access cannot be allowed without all involved permanent participant consent.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a relationship stage track JSON file.")
    parser.add_argument("path")
    args = parser.parse_args()

    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_relationship_stage(data)
    if errors:
        print(f"{path} is not valid:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"{path} is structurally valid.")


if __name__ == "__main__":
    main()
