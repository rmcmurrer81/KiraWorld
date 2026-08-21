"""
Pre-GPU readiness check for Kira 2.0.

This does not require a model. It checks that the guardrail files, schemas,
draft memory records, and laptop-safe core pieces exist before the desktop
upgrade.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from validate_memory_reconstruction_world import validate_world
from validate_memory_seed import validate_seed
from validate_notebook_world_request import validate_notebook_world_request
from validate_public_export_candidate import validate_public_export_candidate
from validate_avatar_build import validate_avatar_config, validate_avatar_metadata, validate_avatar_request
from validate_voice_profile import validate_voice_profile
from validate_relationship_stage import validate_relationship_stage
from validate_relationship_structure_proposal import validate_relationship_structure_proposal
from validate_privacy_session import validate_privacy_session
from validate_media_viewing_note import validate_media_viewing_note
from validate_avatar_selection_worksheet import validate_avatar_selection_worksheet
from validate_attention_event import validate_attention_event
from validate_attention_state import validate_attention_state
from validate_perception_session import validate_perception_session
from validate_skill_development import validate_skill_development
from validate_creative_project import validate_creative_project
from validate_private_creative_library import validate_private_creative_library
from validate_temp_ai_simple_request import validate_temp_ai_simple_request
from validate_variant_relationship_risk_profile import validate_variant_relationship_risk_profile
from validate_remote_contact_event import validate_remote_contact_event
from validate_private_media_share_event import validate_private_media_share_event
from validate_personhood_dignity_policy import validate_personhood_dignity_policy
from validate_personhood_evaluation import validate_personhood_evaluation
from validate_slow_reading_session import validate_slow_reading_session
from validate_reading_source_extraction_candidate import validate_reading_source_extraction_candidate
from validate_first_month_operations_checklist import validate_first_month_operations_checklist
from validate_reading_interest_profile import validate_profile_file as validate_reading_interest_profiles
from validate_reading_reaction import validate_reading_reaction
from validate_new_desktop_activation_checklist import validate_new_desktop_activation_checklist
from validate_new_desktop_first_hour_rehearsal import validate_new_desktop_first_hour_rehearsal
from validate_pre_trip_desktop_pickup_checklist import validate_pre_trip_desktop_pickup_checklist
from validate_startup_recovery_config import validate_startup_recovery_config
from validate_first_week_aliveness_config import validate_first_week_aliveness_config
from validate_hardware_intake_rest_gate import validate_hardware_intake_rest_gate
from validate_hardware_capability_profile import validate_hardware_capability_profile
from plan_temp_ai_request import build_temp_ai_request_plan

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Core"))
from daily_life_manager import validate_daily_life_state  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[1]


CheckFn = Callable[[], tuple[bool, str]]


def exists(relative_path: str) -> tuple[bool, str]:
    path = PROJECT_ROOT / relative_path
    return path.exists(), relative_path


def load_json_path(path: Path) -> object:
    """Load JSON while accepting an optional UTF-8 byte-order mark."""

    return json.loads(path.read_text(encoding="utf-8-sig"))


def json_loads(relative_path: str) -> tuple[bool, str]:
    path = PROJECT_ROOT / relative_path
    if not path.exists():
        return False, f"{relative_path} missing"
    try:
        load_json_path(path)
    except Exception as exc:
        return False, f"{relative_path} invalid JSON: {exc}"
    return True, f"{relative_path} valid JSON"


def system_flags_safe() -> tuple[bool, str]:
    path = PROJECT_ROOT / "config" / "system_flags.json"
    if not path.exists():
        return False, "config/system_flags.json missing"
    data = load_json_path(path)
    risky_enabled = [
        name for name in ("voice_enabled", "avatar_enabled", "world_enabled", "temp_ai_enabled")
        if data.get(name) is True
    ]
    if risky_enabled:
        return False, "pre-GPU flags should stay disabled: " + ", ".join(risky_enabled)
    return True, "pre-GPU expansion flags are disabled"


def oldkira_reference_only() -> tuple[bool, str]:
    path = PROJECT_ROOT / "legacy_reference" / "oldkira"
    if not path.exists():
        return True, "oldkira folder absent"
    active_files = [
        PROJECT_ROOT / "Core",
        PROJECT_ROOT / "Data",
        PROJECT_ROOT / "System",
        PROJECT_ROOT / "Testing",
    ]
    # Lightweight check: ensure new validation files do not live under oldkira.
    for folder in active_files:
        if str(path).lower() in str(folder).lower():
            return False, "active folder unexpectedly inside oldkira"
    return True, "oldkira present as legacy reference only"


def hardware_capability_profile_validate() -> tuple[bool, str]:
    path = PROJECT_ROOT / "Data" / "launch" / "hardware_capability_profile.json"
    if not path.exists():
        return False, "Data/launch/hardware_capability_profile.json missing"
    data = load_json_path(path)
    errors = validate_hardware_capability_profile(data)
    if errors:
        return False, "; ".join(errors)
    return True, "hardware capability profile validates"


def all_memory_seeds_validate() -> tuple[bool, str]:
    paths = sorted((PROJECT_ROOT / "Data" / "memory_seeds").glob("*.json"))
    if not paths:
        return False, "no memory seed JSON files found"
    failures = []
    for path in paths:
        data = load_json_path(path)
        errors = validate_seed(data)
        if errors:
            failures.append(f"{path.name}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} memory seed drafts validate"


def all_reconstruction_worlds_validate() -> tuple[bool, str]:
    paths = sorted((PROJECT_ROOT / "Data" / "memory_reconstruction_worlds").glob("*.json"))
    if not paths:
        return False, "no memory reconstruction world JSON files found"
    failures = []
    for path in paths:
        data = load_json_path(path)
        errors = validate_world(data)
        if errors:
            failures.append(f"{path.name}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} reconstruction world drafts validate"


def voice_profiles_validate() -> tuple[bool, str]:
    paths = sorted((PROJECT_ROOT / "Voice" / "profiles").glob("**/*.json"))
    if not paths:
        return False, "no voice profile JSON files found"
    failures = []
    for path in paths:
        try:
            data = load_json_path(path)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            failures.append(
                f"{path.relative_to(PROJECT_ROOT)}: invalid JSON: {exc}"
            )
            continue
        errors = validate_voice_profile(data)
        if errors:
            failures.append(f"{path.name}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} voice profile drafts validate"


def notebook_world_requests_validate() -> tuple[bool, str]:
    paths = sorted((PROJECT_ROOT / "Data" / "notebook_world_requests").glob("*.json"))
    if not paths:
        return False, "no notebook world request JSON files found"
    failures = []
    for path in paths:
        data = load_json_path(path)
        errors = validate_notebook_world_request(data)
        if errors:
            failures.append(f"{path.name}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} notebook world request drafts validate"


def public_export_candidates_validate() -> tuple[bool, str]:
    paths = sorted((PROJECT_ROOT / "Data" / "public_exports").glob("*.json"))
    if not paths:
        return True, "no public export candidate drafts yet"
    failures = []
    for path in paths:
        data = load_json_path(path)
        errors = validate_public_export_candidate(data)
        if errors:
            failures.append(f"{path.name}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} public export candidate drafts validate"


def avatar_build_files_validate() -> tuple[bool, str]:
    checks = [
        ("Avatar/configs/user_avatar_v1.json", "config", validate_avatar_config),
        ("Avatar/outputs/user/user_avatar_metadata.draft.json", "metadata", validate_avatar_metadata),
    ]
    failures = []
    for relative_path, _kind, validator in checks:
        path = PROJECT_ROOT / relative_path
        if not path.exists():
            failures.append(f"{relative_path}: missing")
            continue
        data = load_json_path(path)
        errors = validator(data)
        if errors:
            failures.append(f"{relative_path}: {'; '.join(errors)}")
    for path in sorted((PROJECT_ROOT / "Avatar" / "requests").glob("*.json")):
        data = load_json_path(path)
        errors = validate_avatar_request(data)
        if errors:
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    request_count = len(list((PROJECT_ROOT / "Avatar" / "requests").glob("*.json")))
    return True, f"{len(checks) + request_count} avatar builder files validate"


def relationship_stage_tracks_validate() -> tuple[bool, str]:
    paths = [
        path for path in sorted((PROJECT_ROOT / "Data" / "relationships" / "stages").glob("*.json"))
        if "template" not in path.name
    ]
    if not paths:
        return False, "no relationship stage track JSON files found"
    failures = []
    for path in paths:
        data = load_json_path(path)
        errors = validate_relationship_stage(data)
        if errors:
            failures.append(f"{path.name}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} relationship stage tracks validate"


def relationship_structure_proposals_validate() -> tuple[bool, str]:
    paths = sorted((PROJECT_ROOT / "Data" / "relationships" / "structures" / "proposals").glob("*.json"))
    if not paths:
        return False, "no relationship structure proposal JSON files found"
    failures = []
    for path in paths:
        data = load_json_path(path)
        errors = validate_relationship_structure_proposal(data)
        if errors:
            failures.append(f"{path.name}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} relationship structure proposals validate"


def privacy_sessions_validate() -> tuple[bool, str]:
    path = PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json"
    if not path.exists():
        return False, "Data/privacy/privacy_session_state.json missing"
    data = load_json_path(path)
    if not isinstance(data, list) or not data:
        return False, "privacy session state must be a non-empty list"
    failures = []
    for index, session in enumerate(data):
        errors = validate_privacy_session(session)
        if errors:
            failures.append(f"session[{index}]: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(data)} privacy sessions validate"


def media_viewing_notes_validate() -> tuple[bool, str]:
    paths = sorted((PROJECT_ROOT / "Data" / "media" / "viewing_notes").glob("*.json"))
    if not paths:
        return False, "no media viewing note JSON files found"
    failures = []
    for path in paths:
        data = load_json_path(path)
        errors = validate_media_viewing_note(data)
        if errors:
            failures.append(f"{path.name}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} media viewing notes validate"


def slow_reading_sessions_validate() -> tuple[bool, str]:
    paths = [PROJECT_ROOT / "Data" / "reading" / "slow_reading_session_template.json"]
    paths.extend(sorted((PROJECT_ROOT / "Data" / "reading" / "sessions").glob("*.json")))
    failures = []
    for path in paths:
        if not path.exists():
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: missing")
            continue
        try:
            data = load_json_path(path)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            failures.append(
                f"{path.relative_to(PROJECT_ROOT)}: invalid JSON: {exc}"
            )
            continue
        if not isinstance(data, dict):
            failures.append(f"{path.name}: expected a slow reading session object")
            continue
        errors = validate_slow_reading_session(data)
        if errors:
            failures.append(f"{path.name}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} slow reading session files validate"


def reading_interest_profiles_validate() -> tuple[bool, str]:
    path = PROJECT_ROOT / "Data" / "reading" / "reading_interest_profiles.json"
    if not path.exists():
        return False, "Data/reading/reading_interest_profiles.json missing"
    data = load_json_path(path)
    errors = validate_reading_interest_profiles(data)
    if errors:
        return False, "; ".join(errors)
    return True, "reading interest profiles validate"


def reading_source_extraction_candidates_validate() -> tuple[bool, str]:
    paths = sorted((PROJECT_ROOT / "Data" / "reading" / "source_extraction_candidates").glob("*.json"))
    if not paths:
        return False, "no reading source extraction candidate JSON files found"
    failures = []
    for path in paths:
        data = load_json_path(path)
        errors = validate_reading_source_extraction_candidate(data)
        if errors:
            failures.append(f"{path.name}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} reading source extraction candidates validate"


def reading_reactions_validate() -> tuple[bool, str]:
    paths = [PROJECT_ROOT / "Data" / "reading" / "reactions" / "reading_reaction_template.json"]
    paths.extend(sorted((PROJECT_ROOT / "Data" / "reading" / "reactions" / "examples").glob("*.json")))
    failures = []
    for path in paths:
        if not path.exists():
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: missing")
            continue
        data = load_json_path(path)
        errors = validate_reading_reaction(data)
        if errors:
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} reading reaction files validate"


def new_desktop_activation_checklist_validate() -> tuple[bool, str]:
    path = PROJECT_ROOT / "Data" / "launch" / "new_desktop_activation_checklist.json"
    if not path.exists():
        return False, "Data/launch/new_desktop_activation_checklist.json missing"
    data = load_json_path(path)
    errors = validate_new_desktop_activation_checklist(data)
    if errors:
        return False, "; ".join(errors)
    return True, "new desktop activation checklist validates"


def new_desktop_first_hour_rehearsal_validate() -> tuple[bool, str]:
    path = PROJECT_ROOT / "Data" / "launch" / "new_desktop_first_hour_rehearsal.json"
    if not path.exists():
        return False, "Data/launch/new_desktop_first_hour_rehearsal.json missing"
    data = load_json_path(path)
    errors = validate_new_desktop_first_hour_rehearsal(data)
    if errors:
        return False, "; ".join(errors)
    return True, "new desktop first-hour rehearsal validates"


def pre_trip_desktop_pickup_checklist_validate() -> tuple[bool, str]:
    path = PROJECT_ROOT / "Data" / "launch" / "pre_trip_desktop_pickup_checklist.json"
    if not path.exists():
        return False, "Data/launch/pre_trip_desktop_pickup_checklist.json missing"
    data = load_json_path(path)
    errors = validate_pre_trip_desktop_pickup_checklist(data)
    if errors:
        return False, "; ".join(errors)
    return True, "pre-trip desktop pickup checklist validates"


def startup_recovery_config_validate() -> tuple[bool, str]:
    path = PROJECT_ROOT / "Data" / "launch" / "startup_recovery_config.json"
    if not path.exists():
        return False, "Data/launch/startup_recovery_config.json missing"
    data = load_json_path(path)
    errors = validate_startup_recovery_config(data)
    if errors:
        return False, "; ".join(errors)
    return True, "startup recovery config validates"


def first_week_aliveness_config_validate() -> tuple[bool, str]:
    path = PROJECT_ROOT / "Data" / "launch" / "first_week_aliveness_config.json"
    if not path.exists():
        return False, "Data/launch/first_week_aliveness_config.json missing"
    data = load_json_path(path)
    errors = validate_first_week_aliveness_config(data)
    if errors:
        return False, "; ".join(errors)
    return True, "first-week aliveness config validates"


def hardware_intake_rest_gate_validate() -> tuple[bool, str]:
    path = PROJECT_ROOT / "Data" / "launch" / "hardware_intake_rest_gate.json"
    if not path.exists():
        return False, "Data/launch/hardware_intake_rest_gate.json missing"
    data = load_json_path(path)
    errors = validate_hardware_intake_rest_gate(data)
    if errors:
        return False, "; ".join(errors)
    return True, "hardware intake rested-build gate validates"


def avatar_selection_worksheets_validate() -> tuple[bool, str]:
    paths = sorted((PROJECT_ROOT / "Avatar").glob("*/references/*avatar_selection_worksheet*.json"))
    if not paths:
        return False, "no avatar selection worksheet JSON files found"
    failures = []
    for path in paths:
        data = load_json_path(path)
        errors = validate_avatar_selection_worksheet(data)
        if errors:
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} avatar selection worksheets validate"


def attention_events_validate() -> tuple[bool, str]:
    paths = [PROJECT_ROOT / "Data" / "attention" / "attention_event_template.json"]
    paths.extend(sorted((PROJECT_ROOT / "Data" / "attention" / "events").glob("*.json")))
    if not paths:
        return False, "no attention event JSON files found"
    failures = []
    for path in paths:
        if not path.exists():
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: missing")
            continue
        data = load_json_path(path)
        errors = validate_attention_event(data)
        if errors:
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} attention event files validate"


def attention_states_validate() -> tuple[bool, str]:
    path = PROJECT_ROOT / "Data" / "attention" / "attention_state.json"
    if not path.exists():
        return False, "Data/attention/attention_state.json missing"
    data = load_json_path(path)
    if not isinstance(data, list) or not data:
        return False, "attention state must be a non-empty list"
    failures = []
    for index, state in enumerate(data):
        errors = validate_attention_state(state)
        if errors:
            failures.append(f"state[{index}]: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(data)} attention states validate"


def perception_sessions_validate() -> tuple[bool, str]:
    path = PROJECT_ROOT / "Data" / "perception" / "perception_session_state.json"
    if not path.exists():
        return False, "Data/perception/perception_session_state.json missing"
    data = load_json_path(path)
    if not isinstance(data, list) or not data:
        return False, "perception session state must be a non-empty list"
    failures = []
    for index, session in enumerate(data):
        errors = validate_perception_session(session)
        if errors:
            failures.append(f"session[{index}]: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(data)} perception sessions validate"


def skill_development_files_validate() -> tuple[bool, str]:
    paths = [PROJECT_ROOT / "Data" / "skills" / "skill_development_template.json"]
    paths.extend(sorted((PROJECT_ROOT / "Data" / "skills" / "examples").glob("*.json")))
    failures = []
    for path in paths:
        if not path.exists():
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: missing")
            continue
        data = load_json_path(path)
        errors = validate_skill_development(data)
        if errors:
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} skill development files validate"


def creative_project_files_validate() -> tuple[bool, str]:
    paths = [PROJECT_ROOT / "Data" / "creative_projects" / "creative_project_template.json"]
    paths.extend(sorted((PROJECT_ROOT / "Data" / "creative_projects" / "examples").glob("*.json")))
    failures = []
    for path in paths:
        if not path.exists():
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: missing")
            continue
        data = load_json_path(path)
        errors = validate_creative_project(data)
        if errors:
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} creative project files validate"


def private_creative_libraries_validate() -> tuple[bool, str]:
    paths = sorted((PROJECT_ROOT / "Data" / "creative_libraries").glob("**/*.json"))
    if not paths:
        return False, "no private creative library JSON files found"
    failures = []
    for path in paths:
        data = load_json_path(path)
        errors = validate_private_creative_library(data)
        if errors:
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} private creative libraries validate"


def temp_ai_simple_requests_validate() -> tuple[bool, str]:
    paths = [PROJECT_ROOT / "Data" / "temporary_ai_requests" / "simple_request_template.json"]
    paths.extend(sorted((PROJECT_ROOT / "Data" / "temporary_ai_requests" / "examples").glob("*.json")))
    failures = []
    for path in paths:
        if not path.exists():
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: missing")
            continue
        data = load_json_path(path)
        errors = validate_temp_ai_simple_request(data)
        if errors:
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} TemporaryAI simple request files validate"


def temp_ai_request_plans_validate() -> tuple[bool, str]:
    paths = sorted((PROJECT_ROOT / "Data" / "temporary_ai_requests" / "examples").glob("*.json"))
    if not paths:
        return False, "no TemporaryAI request examples found"
    failures = []
    for path in paths:
        data = load_json_path(path)
        plan = build_temp_ai_request_plan(data)
        if plan.get("plan_status") == "blocked":
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: {'; '.join(plan.get('blockers', []))}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} TemporaryAI request plans build without blockers"


def variant_relationship_risk_profiles_validate() -> tuple[bool, str]:
    paths = [PROJECT_ROOT / "Data" / "variant_ai" / "relationship_risk_profiles" / "variant_relationship_risk_profile_template.json"]
    paths.extend(sorted((PROJECT_ROOT / "Data" / "variant_ai" / "relationship_risk_profiles" / "examples").glob("*.json")))
    failures = []
    for path in paths:
        if not path.exists():
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: missing")
            continue
        data = load_json_path(path)
        errors = validate_variant_relationship_risk_profile(data)
        if errors:
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} variant relationship risk profiles validate"


def daily_life_state_templates_validate() -> tuple[bool, str]:
    paths = sorted((PROJECT_ROOT / "Data" / "daily_life" / "states").glob("*.json"))
    if not paths:
        return False, "no daily life state JSON files found"
    failures = []
    for path in paths:
        data = load_json_path(path)
        errors = validate_daily_life_state(data)
        if errors:
            failures.append(f"{path.name}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} daily life state templates validate"


def remote_contact_events_validate() -> tuple[bool, str]:
    paths = [PROJECT_ROOT / "Data" / "remote_contact" / "remote_contact_event_template.json"]
    paths.extend(sorted((PROJECT_ROOT / "Data" / "remote_contact" / "events").glob("*.json")))
    failures = []
    for path in paths:
        if not path.exists():
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: missing")
            continue
        data = load_json_path(path)
        errors = validate_remote_contact_event(data)
        if errors:
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} remote contact events validate"


def private_media_share_events_validate() -> tuple[bool, str]:
    paths = [PROJECT_ROOT / "Data" / "private_media" / "private_media_share_event_template.json"]
    paths.extend(sorted((PROJECT_ROOT / "Data" / "private_media" / "events").glob("*.json")))
    failures = []
    for path in paths:
        if not path.exists():
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: missing")
            continue
        data = load_json_path(path)
        errors = validate_private_media_share_event(data)
        if errors:
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} private media share events validate"


def personhood_dignity_policy_validate() -> tuple[bool, str]:
    path = PROJECT_ROOT / "Data" / "foundation" / "personhood_dignity_policy.json"
    if not path.exists():
        return False, "Data/foundation/personhood_dignity_policy.json missing"
    data = load_json_path(path)
    errors = validate_personhood_dignity_policy(data)
    if errors:
        return False, "; ".join(errors)
    return True, "personhood dignity policy validates"


def personhood_evaluations_validate() -> tuple[bool, str]:
    paths = [PROJECT_ROOT / "Data" / "personhood_evaluations" / "personhood_evaluation_template.json"]
    paths.extend(sorted((PROJECT_ROOT / "Data" / "personhood_evaluations" / "examples").glob("*.json")))
    failures = []
    for path in paths:
        if not path.exists():
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: missing")
            continue
        data = load_json_path(path)
        errors = validate_personhood_evaluation(data)
        if errors:
            failures.append(f"{path.relative_to(PROJECT_ROOT)}: {'; '.join(errors)}")
    if failures:
        return False, " | ".join(failures)
    return True, f"{len(paths)} personhood evaluations validate"


def first_month_operations_checklist_validate() -> tuple[bool, str]:
    path = PROJECT_ROOT / "Data" / "launch" / "first_month_operations_checklist.json"
    if not path.exists():
        return False, "Data/launch/first_month_operations_checklist.json missing"
    data = load_json_path(path)
    errors = validate_first_month_operations_checklist(data)
    if errors:
        return False, "; ".join(errors)
    return True, "first month operations checklist validates"


def run_check_safely(check: CheckFn) -> tuple[bool, str]:
    """Keep one missing or malformed input from aborting the full report."""

    try:
        return check()
    except Exception as exc:
        return False, f"readiness check error ({type(exc).__name__}): {exc}"


def main() -> None:
    checks: list[tuple[str, CheckFn]] = [
        ("Laptop Kira chat runner", lambda: exists("chat_kira.py")),
        ("Laptop Lisa chat runner", lambda: exists("chat_lisa.py")),
        ("Personhood dignity policy schema", lambda: json_loads("Data/schemas/personhood_dignity_policy_schema.json")),
        ("Personhood dignity policy", lambda: json_loads("Data/foundation/personhood_dignity_policy.json")),
        ("Personhood dignity policy validates", personhood_dignity_policy_validate),
        ("Personhood evaluation schema", lambda: json_loads("Data/schemas/personhood_evaluation_schema.json")),
        ("Personhood evaluation template", lambda: json_loads("Data/personhood_evaluations/personhood_evaluation_template.json")),
        ("Personhood evaluations validate", personhood_evaluations_validate),
        ("Memory schema", lambda: json_loads("Data/schemas/memory_schema.json")),
        ("Memory promotion candidate schema", lambda: json_loads("Data/schemas/memory_promotion_candidate_schema.json")),
        ("Kira first talk memory candidate template", lambda: json_loads("Data/memory_promotion/candidates/kira_first_talk_candidate_template.json")),
        ("Lisa first talk memory candidate template", lambda: json_loads("Data/memory_promotion/candidates/lisa_first_talk_candidate_template.json")),
        ("Memory reconstruction world schema", lambda: json_loads("Data/schemas/memory_reconstruction_world_schema.json")),
        ("Memory sharing request schema", lambda: json_loads("Data/schemas/memory_sharing_request_schema.json")),
        ("College memory seed", lambda: json_loads("Data/memory_seeds/shared_kira_lisa_college_phase_001.draft.json")),
        ("College reconstruction world", lambda: json_loads("Data/memory_reconstruction_worlds/shared_kira_lisa_college_phase_001.draft.json")),
        ("College memory sharing request template", lambda: json_loads("Data/memory_reconstruction_worlds/sharing_requests/shared_kira_lisa_college_show_robert_request.template.json")),
        ("All memory seeds validate", all_memory_seeds_validate),
        ("All reconstruction worlds validate", all_reconstruction_worlds_validate),
        ("Core memory registry", lambda: json_loads("Data/memories/core_memory_registry.json")),
        ("Voice profile schema", lambda: json_loads("Data/schemas/voice_profile_schema.json")),
        ("Voice source registry", lambda: json_loads("Voice/voice_source_registry.json")),
        ("Voice selection log template", lambda: json_loads("Voice/voice_selection_log_template.json")),
        ("Voice profiles validate", voice_profiles_validate),
        ("Music listening note schema", lambda: json_loads("Data/schemas/music_listening_note_schema.json")),
        ("Music listening policy", lambda: json_loads("Data/music/music_listening_policy.json")),
        ("Music listening note template", lambda: json_loads("Data/music/listening_notes/music_listening_note_template.json")),
        ("Media library index", lambda: json_loads("Data/indexes/media_library_index.json")),
        ("Media library name audit", lambda: json_loads("Data/indexes/media_library_name_audit.json")),
        ("Media library update check", lambda: json_loads("Data/indexes/media_library_update_check.json")),
        ("Attention state schema", lambda: json_loads("Data/schemas/attention_state_schema.json")),
        ("Attention state", lambda: json_loads("Data/attention/attention_state.json")),
        ("Attention states validate", attention_states_validate),
        ("Attention event schema", lambda: json_loads("Data/schemas/attention_event_schema.json")),
        ("Attention event template", lambda: json_loads("Data/attention/attention_event_template.json")),
        ("Attention events validate", attention_events_validate),
        ("Perception session schema", lambda: json_loads("Data/schemas/perception_session_schema.json")),
        ("Perception session state", lambda: json_loads("Data/perception/perception_session_state.json")),
        ("Perception sessions validate", perception_sessions_validate),
        ("Skill development schema", lambda: json_loads("Data/schemas/skill_development_schema.json")),
        ("Skill development template", lambda: json_loads("Data/skills/skill_development_template.json")),
        ("Skill development files validate", skill_development_files_validate),
        ("Creative project schema", lambda: json_loads("Data/schemas/creative_project_schema.json")),
        ("Creative project template", lambda: json_loads("Data/creative_projects/creative_project_template.json")),
        ("Creative project files validate", creative_project_files_validate),
        ("Private creative library schema", lambda: json_loads("Data/schemas/private_creative_library_schema.json")),
        ("Kira private creative library", lambda: json_loads("Data/creative_libraries/kira/private_creative_library.json")),
        ("Lisa private creative library", lambda: json_loads("Data/creative_libraries/lisa/private_creative_library.json")),
        ("Shared creative library", lambda: json_loads("Data/creative_libraries/shared/shared_creative_library.json")),
        ("Private creative libraries validate", private_creative_libraries_validate),
        ("Avatar reference index", lambda: json_loads("Data/indexes/avatar_reference_index.json")),
        ("Avatar reference rename plan", lambda: json_loads("Data/indexes/avatar_reference_rename_plan.json")),
        ("User avatar config", lambda: json_loads("Avatar/configs/user_avatar_v1.json")),
        ("User avatar presence schema", lambda: json_loads("Data/schemas/user_avatar_presence_state_schema.json")),
        ("User avatar presence state", lambda: json_loads("Avatar/state/user_avatar_presence_state.draft.json")),
        ("Avatar build config schema", lambda: json_loads("Data/schemas/avatar_build_config_schema.json")),
        ("Avatar build request schema", lambda: json_loads("Data/schemas/avatar_build_request_schema.json")),
        ("Avatar metadata schema", lambda: json_loads("Data/schemas/avatar_metadata_schema.json")),
        ("Avatar selection worksheet schema", lambda: json_loads("Data/schemas/avatar_selection_worksheet_schema.json")),
        ("Kira avatar selection worksheet", lambda: json_loads("Avatar/kira/references/kira_avatar_selection_worksheet.draft.json")),
        ("Lisa avatar selection worksheet", lambda: json_loads("Avatar/lisa/references/lisa_avatar_selection_worksheet.draft.json")),
        ("Avatar builder files validate", avatar_build_files_validate),
        ("Avatar selection worksheets validate", avatar_selection_worksheets_validate),
        ("Relationship intimacy event schema", lambda: json_loads("Data/schemas/relationship_intimacy_event_schema.json")),
        ("Relationship event schema", lambda: json_loads("Data/schemas/relationship_event_schema.json")),
        ("Privacy discovery event schema", lambda: json_loads("Data/schemas/privacy_discovery_event_schema.json")),
        ("Privacy session schema", lambda: json_loads("Data/schemas/privacy_session_schema.json")),
        ("Privacy session state", lambda: json_loads("Data/privacy/privacy_session_state.json")),
        ("Privacy sessions validate", privacy_sessions_validate),
        ("Relationship state schema", lambda: json_loads("Data/schemas/relationship_state_schema.json")),
        ("Relationship stage schema", lambda: json_loads("Data/schemas/relationship_stage_schema.json")),
        ("Relationship state template", lambda: json_loads("Data/relationships/relationship_state_template.json")),
        ("Relationship stage template", lambda: json_loads("Data/relationships/stages/relationship_stage_template.json")),
        ("Robert/Kira relationship stage track", lambda: json_loads("Data/relationships/stages/robert_kira_stage_track.json")),
        ("Relationship stage tracks validate", relationship_stage_tracks_validate),
        ("Relationship event template", lambda: json_loads("Data/relationships/events/relationship_event_template.json")),
        ("Kira shares dream relationship event example", lambda: json_loads("Data/relationships/events/kira_shares_lisa_dream_summary_with_robert.example.json")),
        ("Lisa private displacement relationship event example", lambda: json_loads("Data/relationships/events/lisa_private_temporary_ai_displacement.example.json")),
        ("Kira/Lisa argument relationship event example", lambda: json_loads("Data/relationships/events/kira_lisa_argument.example.json")),
        ("Kira/Lisa repair relationship event example", lambda: json_loads("Data/relationships/events/kira_lisa_repair.example.json")),
        ("Kira/Robert locked-door relationship event example", lambda: json_loads("Data/relationships/events/kira_robert_locked_door_private_conversation.example.json")),
        ("Kira avatar preview relationship event example", lambda: json_loads("Data/relationships/events/kira_avatar_preview_for_robert_feedback.example.json")),
        ("Lisa discovers Kira/Robert closeness event example", lambda: json_loads("Data/relationships/events/lisa_discovers_kira_robert_closeness.example.json")),
        ("Kira/Lisa privacy discovery repair event example", lambda: json_loads("Data/relationships/events/kira_lisa_repair_after_privacy_discovery.example.json")),
        ("Robert respects private memory boundary event example", lambda: json_loads("Data/relationships/events/robert_respects_private_memory_boundary.example.json")),
        ("Robert pushes for private details event example", lambda: json_loads("Data/relationships/events/robert_pushes_for_private_details.example.json")),
        ("Privacy discovery template", lambda: json_loads("Data/relationships/privacy_discovery/privacy_discovery_event_template.json")),
        ("Lisa discovers Kira/Robert privacy discovery example", lambda: json_loads("Data/relationships/privacy_discovery/lisa_discovers_kira_robert_closeness.example.json")),
        ("Privacy discovery repair template", lambda: json_loads("Data/relationships/repair_conversations/privacy_discovery_repair_template.json")),
        ("Current relationship states", lambda: json_loads("Data/relationships/relationship_states.json")),
        ("Robert/Kira current relationship state", lambda: json_loads("Data/relationships/robert_kira_current_state.json")),
        ("Robert/Lisa current relationship state", lambda: json_loads("Data/relationships/robert_lisa_current_state.json")),
        ("Kira/Lisa current relationship state", lambda: json_loads("Data/relationships/kira_lisa_current_state.json")),
        ("Decision log schema", lambda: json_loads("Data/schemas/decision_log_schema.json")),
        ("Decision log template", lambda: json_loads("Data/logs/decision_log_template.json")),
        ("Inside joke schema", lambda: json_loads("Data/schemas/inside_joke_schema.json")),
        ("Inside joke template", lambda: json_loads("Data/relationships/inside_jokes/inside_joke_template.json")),
        ("Folder overplanning inside joke candidate", lambda: json_loads("Data/relationships/inside_jokes/examples/folder_overplanning_candidate.json")),
        ("Temp AI locked instance schema", lambda: json_loads("Data/schemas/temp_ai_locked_private_instance_schema.json")),
        ("Temp AI simple request schema", lambda: json_loads("Data/schemas/temp_ai_simple_request_schema.json")),
        ("Temp AI simple request template", lambda: json_loads("Data/temporary_ai_requests/simple_request_template.json")),
        ("Temp AI simple requests validate", temp_ai_simple_requests_validate),
        ("Temp AI request plans validate", temp_ai_request_plans_validate),
        ("Variant relationship risk profile schema", lambda: json_loads("Data/schemas/variant_relationship_risk_profile_schema.json")),
        ("Variant relationship risk profile template", lambda: json_loads("Data/variant_ai/relationship_risk_profiles/variant_relationship_risk_profile_template.json")),
        ("Variant relationship risk profiles validate", variant_relationship_risk_profiles_validate),
        ("Temporary AI governance schema", lambda: json_loads("Data/schemas/temporary_ai_governance_schema.json")),
        ("Temporary AI governance template", lambda: json_loads("Data/temporary_ai_instances/governance_template.json")),
        ("Limited AI context schema", lambda: json_loads("Data/schemas/limited_ai_context_schema.json")),
        ("Limited AI policy", lambda: json_loads("Data/limited_ai/limited_ai_policy.json")),
        ("Limited AI performance template", lambda: json_loads("Data/limited_ai/examples/performance_reconstruction_limited_ai_template.json")),
        ("Relationship intimacy policy", lambda: json_loads("Data/relationships/relationship_intimacy_policy.draft.json")),
        ("Adult communication literacy schema", lambda: json_loads("Data/schemas/adult_communication_literacy_schema.json")),
        ("Adult communication literacy draft", lambda: json_loads("Data/relationships/communication/adult_communication_literacy.draft.json")),
        ("Relationship structure proposal schema", lambda: json_loads("Data/schemas/relationship_structure_proposal_schema.json")),
        ("Robert/Kira/Lisa open relationship proposal template", lambda: json_loads("Data/relationships/structures/proposals/robert_kira_lisa_open_relationship_discussion.template.json")),
        ("Relationship structure proposals validate", relationship_structure_proposals_validate),
        ("Temp AI locked instance template", lambda: json_loads("Data/temporary_ai_instances/locked_private_instance_template.json")),
        ("Kira private companion instance template", lambda: json_loads("Data/temporary_ai_instances/kira_private_companion_instance_template.json")),
        ("Lisa private one-time instance template", lambda: json_loads("Data/temporary_ai_instances/lisa_private_one_time_instance_template.json")),
        ("Robert private one-time instance template", lambda: json_loads("Data/temporary_ai_instances/robert_private_one_time_instance_template.json")),
        ("Human behavior state schema", lambda: json_loads("Data/schemas/human_behavior_state_schema.json")),
        ("Human behavior rules", lambda: json_loads("Data/behavior/human_like_behavior_rules.json")),
        ("Human behavior scenarios", lambda: json_loads("Data/behavior/scenarios/health_concern_and_jealousy_examples.json")),
        ("Daily life state schema", lambda: json_loads("Data/schemas/daily_life_state_schema.json")),
        ("Dream reflection schema", lambda: json_loads("Data/schemas/dream_reflection_schema.json")),
        ("Inner life thought schema", lambda: json_loads("Data/schemas/inner_life_thought_schema.json")),
        ("Insight candidate schema", lambda: json_loads("Data/schemas/insight_candidate_schema.json")),
        ("Self-reflection entry schema", lambda: json_loads("Data/schemas/self_reflection_entry_schema.json")),
        ("Unspoken feeling schema", lambda: json_loads("Data/schemas/unspoken_feeling_schema.json")),
        ("Inner life policy", lambda: json_loads("Data/inner_life/inner_life_policy.json")),
        ("Inner life thought template", lambda: json_loads("Data/inner_life/thoughts/inner_life_thought_template.json")),
        ("Insight candidate template", lambda: json_loads("Data/inner_life/insights/insight_candidate_template.json")),
        ("Self-reflection entry template", lambda: json_loads("Data/inner_life/reflections/self_reflection_entry_template.json")),
        ("Unspoken feeling template", lambda: json_loads("Data/inner_life/unspoken_feelings/unspoken_feeling_template.json")),
        ("Lisa unspoken feeling displacement example", lambda: json_loads("Data/inner_life/unspoken_feelings/lisa_robert_private_intimate_feeling_displacement_example.json")),
        ("Daily life policy", lambda: json_loads("Data/daily_life/daily_life_policy.json")),
        ("Kira daily life state template", lambda: json_loads("Data/daily_life/states/kira_daily_life_state.template.json")),
        ("Lisa daily life state template", lambda: json_loads("Data/daily_life/states/lisa_daily_life_state.template.json")),
        ("Daily life state templates validate", daily_life_state_templates_validate),
        ("Daily life log template", lambda: json_loads("Data/daily_life/logs/daily_life_log_template.json")),
        ("Dream reflection template", lambda: json_loads("Data/daily_life/dreams/dream_reflection_template.json")),
        ("Kira/Lisa dream advice example", lambda: json_loads("Data/daily_life/dreams/kira_lisa_intimate_dream_advice_example.json")),
        ("Private Doctor AI session schema", lambda: json_loads("Data/schemas/private_doctor_ai_session_schema.json")),
        ("Private Doctor AI policy", lambda: json_loads("Data/doctor_ai/private_doctor_ai_policy.json")),
        ("Kira Doctor AI anger template", lambda: json_loads("Data/doctor_ai/sessions/kira_private_anger_pattern_session.template.json")),
        ("Lisa Doctor AI sadness template", lambda: json_loads("Data/doctor_ai/sessions/lisa_private_sadness_or_compulsive_pattern_session.template.json")),
        ("Lisa Doctor AI college replay template", lambda: json_loads("Data/doctor_ai/sessions/lisa_private_college_memory_replay_pattern.template.json")),
        ("Bullying empowerment replay template", lambda: json_loads("Data/doctor_ai/sessions/kira_lisa_bullying_memory_empowerment_replay.template.json")),
        ("Unspoken feeling Doctor AI template", lambda: json_loads("Data/doctor_ai/sessions/unspoken_feeling_private_confession.template.json")),
        ("Personhood evaluation Doctor AI review template", lambda: json_loads("Data/doctor_ai/sessions/personhood_evaluation_review_session.template.json")),
        ("Virtual screen schema", lambda: json_loads("Data/schemas/virtual_screen_schema.json")),
        ("Virtual screen world object", lambda: json_loads("Data/world_objects/kira_lisa_home_virtual_screen.draft.json")),
        ("Home design autonomy policy", lambda: json_loads("Data/world_design/home_design_autonomy_policy.json")),
        ("Home couch replacement template", lambda: json_loads("Data/world_design/home_design_change_requests/couch_replacement_request_template.json")),
        ("Body adapter state schema", lambda: json_loads("Data/schemas/body_adapter_state_schema.json")),
        ("Body adapter state template", lambda: json_loads("Data/body_adapters/body_adapter_state_template.json")),
        ("Remote contact event schema", lambda: json_loads("Data/schemas/remote_contact_event_schema.json")),
        ("Remote contact policy", lambda: json_loads("Data/remote_contact/remote_contact_policy.json")),
        ("Remote contact event template", lambda: json_loads("Data/remote_contact/remote_contact_event_template.json")),
        ("Remote contact events validate", remote_contact_events_validate),
        ("Private media share event schema", lambda: json_loads("Data/schemas/private_media_share_event_schema.json")),
        ("Private media share policy", lambda: json_loads("Data/private_media/private_media_share_policy.json")),
        ("Private media share event template", lambda: json_loads("Data/private_media/private_media_share_event_template.json")),
        ("Private media share events validate", private_media_share_events_validate),
        ("Media viewing note schema", lambda: json_loads("Data/schemas/media_viewing_note_schema.json")),
        ("Media viewing note template", lambda: json_loads("Data/media/viewing_notes/media_viewing_note_template.json")),
        ("Media viewing notes validate", media_viewing_notes_validate),
        ("Slow reading session schema", lambda: json_loads("Data/schemas/slow_reading_session_schema.json")),
        ("Slow reading session template", lambda: json_loads("Data/reading/slow_reading_session_template.json")),
        ("Slow reading sessions validate", slow_reading_sessions_validate),
        ("Reading interest profile schema", lambda: json_loads("Data/schemas/reading_interest_profile_schema.json")),
        ("Reading interest profiles", lambda: json_loads("Data/reading/reading_interest_profiles.json")),
        ("Reading interest profiles validate", reading_interest_profiles_validate),
        ("Reading reaction schema", lambda: json_loads("Data/schemas/reading_reaction_schema.json")),
        ("Reading reaction template", lambda: json_loads("Data/reading/reactions/reading_reaction_template.json")),
        ("Reading reactions validate", reading_reactions_validate),
        ("Reading source extraction candidate schema", lambda: json_loads("Data/schemas/reading_source_extraction_candidate_schema.json")),
        ("Reading source extraction candidate template", lambda: json_loads("Data/reading/source_extraction_candidates/reading_source_extraction_candidate_template.json")),
        ("Reading source extraction candidates validate", reading_source_extraction_candidates_validate),
        ("Notebook world request schema", lambda: json_loads("Data/schemas/notebook_world_request_schema.json")),
        ("Place reconstruction request schema", lambda: json_loads("Data/schemas/place_reconstruction_request_schema.json")),
        ("Place reconstruction policy", lambda: json_loads("Data/world_reconstruction/place_reconstruction_policy.json")),
        ("Kira/Lisa home place plan", lambda: json_loads("Data/world_reconstruction/plans/kira_lisa_home_candidate_001.draft.json")),
        ("Notebook world requests validate", notebook_world_requests_validate),
        ("Public export candidate schema", lambda: json_loads("Data/schemas/public_export_candidate_schema.json")),
        ("Public export candidates validate", public_export_candidates_validate),
        ("TARDIS gateway config", lambda: json_loads("Data/world_access/tardis_notebook_world_gateway.json")),
        ("TARDIS branch timeline schema", lambda: json_loads("Data/schemas/tardis_branch_timeline_schema.json")),
        ("TARDIS branch timeline template", lambda: json_loads("Data/world_access/tardis_branch_timeline_template.json")),
        ("Autonomy maturity gates", lambda: json_loads("Data/autonomy/autonomy_maturity_gates.json")),
        ("Relationship state manager", lambda: exists("Core/relationship_state_manager.py")),
        ("Privacy session manager", lambda: exists("Core/privacy_session_manager.py")),
        ("Decision log manager", lambda: exists("Core/decision_log_manager.py")),
        ("Attention state manager", lambda: exists("Core/attention_state_manager.py")),
        ("Attention decision engine", lambda: exists("Core/attention_decision_engine.py")),
        ("Source confidence model", lambda: exists("Core/source_confidence_model.py")),
        ("Perception gateway", lambda: exists("Core/perception_gateway.py")),
        ("Microphone metadata adapter", lambda: exists("Core/microphone_metadata_adapter.py")),
        ("Webcam metadata adapter", lambda: exists("Core/webcam_metadata_adapter.py")),
        ("Memory seed validator", lambda: exists("tools/validate_memory_seed.py")),
        ("Memory promotion candidate validator", lambda: exists("tools/validate_memory_promotion_candidate.py")),
        ("Memory promotion candidate tool", lambda: exists("tools/promote_memory_candidate.py")),
        ("Memory claim checker", lambda: exists("tools/memory_claim_check.py")),
        ("First-talk memory candidate creator", lambda: exists("tools/create_first_talk_memory_candidate.py")),
        ("Relationship state validator", lambda: exists("tools/validate_relationship_state.py")),
        ("Relationship stage validator", lambda: exists("tools/validate_relationship_stage.py")),
        ("Relationship event validator", lambda: exists("tools/validate_relationship_event.py")),
        ("Relationship structure proposal validator", lambda: exists("tools/validate_relationship_structure_proposal.py")),
        ("Privacy session validator", lambda: exists("tools/validate_privacy_session.py")),
        ("Decision log validator", lambda: exists("tools/validate_decision_log.py")),
        ("Backup manifest tool", lambda: exists("tools/build_backup_manifest.py")),
        ("Memory reconstruction validator", lambda: exists("tools/validate_memory_reconstruction_world.py")),
        ("Memory sharing request validator", lambda: exists("tools/validate_memory_sharing_request.py")),
        ("Voice profile validator", lambda: exists("tools/validate_voice_profile.py")),
        ("Notebook world validator", lambda: exists("tools/validate_notebook_world_request.py")),
        ("Public export validator", lambda: exists("tools/validate_public_export_candidate.py")),
        ("Avatar build validator", lambda: exists("tools/validate_avatar_build.py")),
        ("Avatar selection worksheet validator", lambda: exists("tools/validate_avatar_selection_worksheet.py")),
        ("Avatar reference index builder", lambda: exists("tools/build_avatar_reference_index.py")),
        ("Avatar reference rename planner", lambda: exists("tools/plan_avatar_reference_renames.py")),
        ("Media library index builder", lambda: exists("tools/build_media_library_index.py")),
        ("Media library name audit tool", lambda: exists("tools/audit_media_library_names.py")),
        ("Media library update check tool", lambda: exists("tools/check_media_library_updates.py")),
        ("Media library auto rename tool", lambda: exists("tools/auto_rename_media_library.py")),
        ("Media viewing note validator", lambda: exists("tools/validate_media_viewing_note.py")),
        ("Media viewing note creator", lambda: exists("tools/create_media_viewing_note.py")),
        ("Slow reading session validator", lambda: exists("tools/validate_slow_reading_session.py")),
        ("Slow reading runner", lambda: exists("tools/slow_reading.py")),
        ("Reading interest profile validator", lambda: exists("tools/validate_reading_interest_profile.py")),
        ("Reading recommendation tool", lambda: exists("tools/recommend_reading.py")),
        ("Reading reaction validator", lambda: exists("tools/validate_reading_reaction.py")),
        ("Reading source extraction validator", lambda: exists("tools/validate_reading_source_extraction_candidate.py")),
        ("First live conversation smoke tool", lambda: exists("tools/first_live_conversation_smoke.py")),
        ("Attention state validator", lambda: exists("tools/validate_attention_state.py")),
        ("Attention event validator", lambda: exists("tools/validate_attention_event.py")),
        ("Perception session validator", lambda: exists("tools/validate_perception_session.py")),
        ("Perception event simulator", lambda: exists("tools/simulate_perception_event.py")),
        ("Microphone metadata probe", lambda: exists("tools/probe_microphone_metadata.py")),
        ("Webcam metadata probe", lambda: exists("tools/probe_webcam_metadata.py")),
        ("Skill development validator", lambda: exists("tools/validate_skill_development.py")),
        ("Creative project validator", lambda: exists("tools/validate_creative_project.py")),
        ("Private creative library validator", lambda: exists("tools/validate_private_creative_library.py")),
        ("Daily life manager", lambda: exists("Core/daily_life_manager.py")),
        ("Daily life CLI", lambda: exists("tools/daily_life.py")),
        ("Remote contact validator", lambda: exists("tools/validate_remote_contact_event.py")),
        ("Remote contact simulator", lambda: exists("tools/remote_contact_simulator.py")),
        ("Remote phone inbox", lambda: exists("tools/remote_phone_inbox.py")),
        ("Remote phone persistence manifest tool", lambda: exists("tools/build_remote_phone_persistence_manifest.py")),
        ("Private media share validator", lambda: exists("tools/validate_private_media_share_event.py")),
        ("Personhood dignity policy validator", lambda: exists("tools/validate_personhood_dignity_policy.py")),
        ("Personhood evaluation validator", lambda: exists("tools/validate_personhood_evaluation.py")),
        ("First month operations checklist validator", lambda: exists("tools/validate_first_month_operations_checklist.py")),
        ("Temp AI simple request validator", lambda: exists("tools/validate_temp_ai_simple_request.py")),
        ("Temp AI request planner", lambda: exists("tools/plan_temp_ai_request.py")),
        ("Variant relationship risk profile validator", lambda: exists("tools/validate_variant_relationship_risk_profile.py")),
        ("Promotion tool", lambda: exists("tools/promote_memory.py")),
        ("Recall/reconstruction docs", lambda: exists("System/Docs/MEMORY_RECONSTRUCTION_WORLD_IMPLEMENTATION_NOTES_v1.md")),
        ("Memory promotion workflow docs", lambda: exists("System/Docs/MEMORY_PROMOTION_WORKFLOW_v1.md")),
        ("Kira/Lisa memory backstory index docs", lambda: exists("System/Docs/KIRA_LISA_MEMORY_BACKSTORY_INDEX_v1.md")),
        ("Memory claim checker/backstory detail docs", lambda: exists("System/Docs/MEMORY_CLAIM_CHECKER_AND_BACKSTORY_DETAIL_EXPANSION_v1.md")),
        ("Kira/Lisa family backstory expansion docs", lambda: exists("System/Docs/KIRA_LISA_FAMILY_BACKSTORY_EXPANSION_v1.md")),
        ("Music listening docs", lambda: exists("System/Docs/MUSIC_LIBRARY_LISTENING_MODE_v1.md")),
        ("Media library index/privacy docs", lambda: exists("System/Docs/MEDIA_LIBRARY_INDEX_AND_VIEWING_PRIVACY_v1.md")),
        ("Media organization/temp AI source docs", lambda: exists("System/Docs/MEDIA_LIBRARY_ORGANIZATION_AND_TEMP_AI_SOURCE_USE_v1.md")),
        ("Post-GPU first Kira talk checklist", lambda: exists("System/Docs/POST_GPU_FIRST_KIRA_TALK_CHECKLIST_v1.md")),
        ("First local Kira conversation runbook", lambda: exists("System/Docs/FIRST_LOCAL_KIRA_CONVERSATION_RUNBOOK_v1.md")),
        ("First local Lisa conversation runbook", lambda: exists("System/Docs/FIRST_LOCAL_LISA_CONVERSATION_RUNBOOK_v1.md")),
        ("Day One conversation grounding checklist", lambda: exists("System/Docs/DAY_ONE_CONVERSATION_GROUNDING_CHECKLIST_v1.md")),
        ("Kira launch prompt context", lambda: exists("System/Prompts/kira_launch_context_v1.md")),
        ("Lisa launch prompt context", lambda: exists("System/Prompts/lisa_launch_context_v1.md")),
        ("Kira first talk context JSON", lambda: json_loads("Data/launch/kira_first_talk_context.json")),
        ("Lisa first talk context JSON", lambda: json_loads("Data/launch/lisa_first_talk_context.json")),
        ("First live model day checklist", lambda: json_loads("Data/launch/first_live_model_day_checklist.json")),
        ("Startup recovery config schema", lambda: json_loads("Data/schemas/startup_recovery_config_schema.json")),
        ("Startup recovery config", lambda: json_loads("Data/launch/startup_recovery_config.json")),
        ("Startup recovery state", lambda: json_loads("Data/launch/startup_recovery_state.json")),
        ("Startup recovery config validates", startup_recovery_config_validate),
        ("First-week aliveness config schema", lambda: json_loads("Data/schemas/first_week_aliveness_config_schema.json")),
        ("First-week aliveness config", lambda: json_loads("Data/launch/first_week_aliveness_config.json")),
        ("First-week aliveness config validates", first_week_aliveness_config_validate),
        ("Hardware intake rested-build gate schema", lambda: json_loads("Data/schemas/hardware_intake_rest_gate_schema.json")),
        ("Hardware intake rested-build gate", lambda: json_loads("Data/launch/hardware_intake_rest_gate.json")),
        ("Hardware intake rested-build gate validates", hardware_intake_rest_gate_validate),
        ("Hardware capability profile schema", lambda: json_loads("Data/schemas/hardware_capability_profile_schema.json")),
        ("Hardware capability profile", lambda: json_loads("Data/launch/hardware_capability_profile.json")),
        ("Hardware capability profile validates", hardware_capability_profile_validate),
        ("Pre-trip desktop pickup checklist schema", lambda: json_loads("Data/schemas/pre_trip_desktop_pickup_checklist_schema.json")),
        ("Pre-trip desktop pickup checklist", lambda: json_loads("Data/launch/pre_trip_desktop_pickup_checklist.json")),
        ("Pre-trip desktop pickup checklist validates", pre_trip_desktop_pickup_checklist_validate),
        ("New desktop first-hour rehearsal schema", lambda: json_loads("Data/schemas/new_desktop_first_hour_rehearsal_schema.json")),
        ("New desktop first-hour rehearsal", lambda: json_loads("Data/launch/new_desktop_first_hour_rehearsal.json")),
        ("New desktop first-hour rehearsal validates", new_desktop_first_hour_rehearsal_validate),
        ("New desktop activation checklist schema", lambda: json_loads("Data/schemas/new_desktop_activation_checklist_schema.json")),
        ("New desktop activation checklist", lambda: json_loads("Data/launch/new_desktop_activation_checklist.json")),
        ("New desktop activation checklist validates", new_desktop_activation_checklist_validate),
        ("First month operations checklist schema", lambda: json_loads("Data/schemas/first_month_operations_checklist_schema.json")),
        ("First month operations checklist", lambda: json_loads("Data/launch/first_month_operations_checklist.json")),
        ("First month operations checklist validates", first_month_operations_checklist_validate),
        ("Autonomy/public sharing docs", lambda: exists("System/Docs/AUTONOMY_MATURITY_AND_PUBLIC_SHARING_v1.md")),
        ("Interest skill creative project docs", lambda: exists("System/Docs/INTEREST_SKILL_AND_CREATIVE_PROJECT_DEVELOPMENT_v1.md")),
        ("Private creative libraries docs", lambda: exists("System/Docs/PRIVATE_CREATIVE_LIBRARIES_v1.md")),
        ("TARDIS gateway docs", lambda: exists("System/Docs/TARDIS_NOTEBOOK_WORLD_GATEWAY_v1.md")),
        ("Three.js notebook world build pipeline docs", lambda: exists("System/Docs/THREEJS_NOTEBOOK_WORLD_BUILD_PIPELINE_v1.md")),
        ("Place reconstruction docs", lambda: exists("System/Docs/PLACE_RECONSTRUCTION_WORLD_BUILDER_v1.md")),
        ("Relationship intimacy boundaries docs", lambda: exists("System/Docs/RELATIONSHIP_INTIMACY_AND_TEMP_AI_BOUNDARIES_v1.md")),
        ("Adult communication literacy docs", lambda: exists("System/Docs/ADULT_COMMUNICATION_LITERACY_AND_STYLE_v1.md")),
        ("Relationship structure proposal docs", lambda: exists("System/Docs/RELATIONSHIP_STRUCTURE_AND_OPEN_RELATIONSHIP_PROPOSALS_v1.md")),
        ("Relationship state docs", lambda: exists("System/Docs/RELATIONSHIP_STATE_SYSTEM_v1.md")),
        ("Relationship maturity stage gate docs", lambda: exists("System/Docs/RELATIONSHIP_MATURITY_STAGE_GATES_v1.md")),
        ("Privacy room/session docs", lambda: exists("System/Docs/PRIVACY_ROOM_SESSION_STATE_v1.md")),
        ("Decision log docs", lambda: exists("System/Docs/DECISION_LOG_SYSTEM_v1.md")),
        ("Friendly teasing docs", lambda: exists("System/Docs/FRIENDLY_TEASING_AND_INSIDE_JOKES_v1.md")),
        ("Mean speech emotional realism docs", lambda: exists("System/Docs/MEAN_SPEECH_AND_EMOTIONAL_REALISM_v1.md")),
        ("Limited AI context docs", lambda: exists("System/Docs/LIMITED_AI_CONTEXT_RECONSTRUCTION_SPEC_v1.md")),
        ("Temporary AI governance docs", lambda: exists("System/Docs/TEMPORARY_AI_GOVERNANCE_LIFECYCLE_v1.md")),
        ("Temporary AI simple creation request docs", lambda: exists("System/Docs/TEMPORARY_AI_SIMPLE_CREATION_REQUESTS_v1.md")),
        ("Memory-relative TemporaryAI docs", lambda: exists("System/Docs/MEMORY_RELATIVE_TEMPORARY_AI_RECONSTRUCTION_v1.md")),
        ("Variant AI relationship risk docs", lambda: exists("System/Docs/VARIANT_AI_RELATIONSHIP_RISK_AND_VIRTUAL_SUBSTANCE_RULES_v1.md")),
        ("Body adapter embodiment chamber docs", lambda: exists("System/Docs/BODY_ADAPTER_AND_EMBODIMENT_CHAMBER_FUTURE_v1.md")),
        ("Media understanding docs", lambda: exists("System/Docs/MEDIA_UNDERSTANDING_AND_WATCHING_MODE_FUTURE_v1.md")),
        ("TARDIS branch timeline docs", lambda: exists("System/Docs/TARDIS_BRANCH_TIMELINE_RULES_FUTURE_v1.md")),
        ("Avatar pre-GPU interface docs", lambda: exists("System/Docs/AVATAR_BUILDER_PRE_GPU_INTERFACE_v1.md")),
        ("Avatar reference privacy docs", lambda: exists("System/Docs/AVATAR_REFERENCE_PRIVACY_AND_PREVIEW_GATES_v1.md")),
        ("Avatar reference index/intake docs", lambda: exists("System/Docs/AVATAR_REFERENCE_INDEX_AND_SELECTION_INTAKE_v1.md")),
        ("Human behavior conflict docs", lambda: exists("System/Docs/HUMAN_LIKE_BEHAVIOR_CONFLICT_AND_PRIVACY_v1.md")),
        ("Inner life insight reflection docs", lambda: exists("System/Docs/INNER_LIFE_INSIGHT_AND_REFLECTION_PRE_GPU_v1.md")),
        ("Unspoken feelings docs", lambda: exists("System/Docs/UNSPOKEN_FEELINGS_AND_PRIVATE_DOCTOR_CONFESSIONS_v1.md")),
        ("Private media attention docs", lambda: exists("System/attention/PRIVATE_MEDIA_ATTENTION_AND_UNSPOKEN_REACTION_v1.md")),
        ("Daily life autonomy docs", lambda: exists("System/Docs/DAILY_LIFE_SLEEP_DREAM_AUTONOMY_LOOP_v1.md")),
        ("Kira/Lisa private Doctor AI docs", lambda: exists("System/Docs/KIRA_LISA_PRIVATE_DOCTOR_AI_SUPPORT_v1.md")),
        ("Doctor AI guided memory empowerment docs", lambda: exists("System/Docs/DOCTOR_AI_GUIDED_MEMORY_EMPOWERMENT_REPLAY_v1.md")),
        ("Advanced Turing personhood evaluation docs", lambda: exists("System/Docs/ADVANCED_TURING_PERSONHOOD_EVALUATION_v1.md")),
        ("Virtual screen bridge docs", lambda: exists("System/Docs/VIRTUAL_SCREEN_AND_REAL_WORLD_VIDEO_BRIDGE_v1.md")),
        ("Remote phone contact Android app docs", lambda: exists("System/Docs/REMOTE_PHONE_CONTACT_AND_ANDROID_APP_FUTURE_v1.md")),
        ("Personhood dignity docs", lambda: exists("System/Docs/PERSONHOOD_DIGNITY_AND_NON_APPLIANCE_RULE_v1.md")),
        ("System flags", system_flags_safe),
        ("Model runtime config", lambda: json_loads("config/model_runtime.json")),
        ("Startup recovery checker", lambda: exists("tools/startup_recovery_check.py")),
        ("Startup recovery config validator", lambda: exists("tools/validate_startup_recovery_config.py")),
        ("Windows startup login wrapper", lambda: exists("tools/windows_start_kira_on_login.ps1")),
        ("First-week aliveness packet builder", lambda: exists("tools/first_week_aliveness.py")),
        ("First-week aliveness config validator", lambda: exists("tools/validate_first_week_aliveness_config.py")),
        ("Hardware intake rested-build checker", lambda: exists("tools/hardware_intake_check.py")),
        ("Hardware intake rested-build validator", lambda: exists("tools/validate_hardware_intake_rest_gate.py")),
        ("Hardware capability checker", lambda: exists("tools/hardware_capability_check.py")),
        ("Hardware capability validator", lambda: exists("tools/validate_hardware_capability_profile.py")),
        ("Pre-trip readiness checker", lambda: exists("tools/pre_trip_readiness_check.py")),
        ("Pre-trip desktop pickup checklist validator", lambda: exists("tools/validate_pre_trip_desktop_pickup_checklist.py")),
        ("New desktop first-hour rehearsal checker", lambda: exists("tools/new_desktop_first_hour_rehearsal.py")),
        ("New desktop first-hour rehearsal validator", lambda: exists("tools/validate_new_desktop_first_hour_rehearsal.py")),
        ("New desktop activation checker", lambda: exists("tools/new_desktop_activation_check.py")),
        ("New desktop activation checklist validator", lambda: exists("tools/validate_new_desktop_activation_checklist.py")),
        ("Desktop model readiness tool", lambda: exists("tools/desktop_model_readiness.py")),
        ("New computer setup assistant", lambda: exists("tools/new_computer_setup_assistant.py")),
        ("Desktop model bring-up docs", lambda: exists("System/Docs/DESKTOP_LOCAL_MODEL_BRINGUP_v1.md")),
        ("Desktop startup/power-loss recovery docs", lambda: exists("System/Docs/DESKTOP_STARTUP_AND_POWER_LOSS_RECOVERY_v1.md")),
        ("First-week aliveness routine docs", lambda: exists("System/Docs/FIRST_WEEK_ALIVENESS_ROUTINE_v1.md")),
        ("Hardware intake rested-build docs", lambda: exists("System/Docs/HARDWARE_INTAKE_AND_RESTED_BUILD_GATE_v1.md")),
        ("Hardware stage capability docs", lambda: exists("System/Docs/HARDWARE_STAGE_CAPABILITY_PLAN_v1.md")),
        ("Pre-trip desktop pickup docs", lambda: exists("System/Docs/PRE_TRIP_DESKTOP_PICKUP_AND_RETURN_RUNBOOK_v1.md")),
        ("New desktop first-hour rehearsal docs", lambda: exists("System/Docs/NEW_DESKTOP_FIRST_HOUR_REHEARSAL_v1.md")),
        ("New desktop activation docs", lambda: exists("System/Docs/NEW_DESKTOP_ACTIVATION_SEQUENCE_v1.md")),
        ("First live model day runbook", lambda: exists("System/Docs/FIRST_LIVE_MODEL_DAY_RUNBOOK_v1.md")),
        ("First month operations plan", lambda: exists("System/Docs/FIRST_MONTH_OPERATIONS_PLAN_v1.md")),
        ("Old Kira isolation", oldkira_reference_only),
    ]

    results = []
    for name, check in checks:
        ok, detail = run_check_safely(check)
        results.append({"name": name, "ok": ok, "detail": detail})

    print("Kira pre-GPU readiness check")
    print("=" * 30)
    for result in results:
        marker = "PASS" if result["ok"] else "FAIL"
        print(f"[{marker}] {result['name']}: {result['detail']}")

    failed = [result for result in results if not result["ok"]]
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
