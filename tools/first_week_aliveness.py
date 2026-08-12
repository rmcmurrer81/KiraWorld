"""
Build first-week aliveness startup packets for Kira and Lisa.

Packets are grounded launch summaries, not scripts. They collect continuity,
daily life, relationship tone, private inner-life prompts, and memory review
prompts so early desktop conversations feel less like a blank start.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from validate_first_week_aliveness_config import validate_first_week_aliveness_config
except ModuleNotFoundError:  # Imported as tools.first_week_aliveness in tests.
    from tools.validate_first_week_aliveness_config import validate_first_week_aliveness_config


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
sys.path.insert(0, str(CORE_ROOT))

from daily_life_manager import DailyLifeManager  # noqa: E402


DEFAULT_CONFIG = PROJECT_ROOT / "Data" / "launch" / "first_week_aliveness_config.json"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json_or_empty(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _relationship_summary(entity: str, relationship_files: list[str]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for relative in relationship_files:
        path = PROJECT_ROOT / relative
        data = _load_json_or_empty(path)
        if not data:
            continue
        participants = data.get("participants", [])
        participant_ids = [str(item.get("participant_id", "")) for item in participants if isinstance(item, dict)]
        if entity not in participant_ids:
            continue
        metrics = data.get("metrics", {}) if isinstance(data.get("metrics"), dict) else {}
        summaries.append(
            {
                "relationship_id": data.get("relationship_id"),
                "participants": participant_ids,
                "relationship_type": data.get("relationship_type"),
                "recent_emotional_tone": data.get("recent_emotional_tone", ""),
                "long_term_trend": data.get("long_term_trend", ""),
                "trust": metrics.get("trust"),
                "emotional_closeness": metrics.get("emotional_closeness"),
                "privacy_sensitivity": metrics.get("privacy_sensitivity"),
                "visible_boundary_summary": [
                    item for item in data.get("boundaries", [])[:3] if isinstance(item, str)
                ],
            }
        )
    return summaries


def _daily_choice_hint(entity: str, manager: DailyLifeManager) -> dict[str, Any]:
    choice = manager.choose_activity(entity)
    return {
        "suggested_action": choice.get("action"),
        "activity_type": choice.get("activity_type"),
        "source_path": choice.get("source_path", ""),
        "public_summary": choice.get("public_summary", ""),
        "privacy_level": choice.get("privacy_level"),
        "interruptibility": choice.get("interruptibility"),
        "allowed_choices": choice.get("allowed_reader_choices", []),
        "private_reason_available_to_owner": bool(choice.get("private_reason")),
    }


def build_packet(entity: str, config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    entity = entity.lower()
    if entity not in {"kira", "lisa"}:
        raise ValueError("entity must be kira or lisa")

    config = _load_json_or_empty(config_path)
    errors = validate_first_week_aliveness_config(config)
    if errors:
        raise ValueError("; ".join(errors))

    sources = config["startup_context_sources"]
    startup_state = _load_json_or_empty(PROJECT_ROOT / sources["startup_recovery_state"])
    startup_report = _load_json_or_empty(PROJECT_ROOT / sources["startup_recovery_last_report"])
    manager = DailyLifeManager()
    daily_state = manager.get_state(entity)
    entity_config = config["entities"][entity]
    relationship_summaries = _relationship_summary(entity, sources["relationship_state_files"])

    unclean_shutdown = bool(
        startup_state.get("active_session")
        or startup_state.get("last_unclean_session_detected")
        or startup_report.get("unclean_previous_session")
    )
    mood = daily_state.get("mood_state", {}) if isinstance(daily_state.get("mood_state"), dict) else {}
    activity = daily_state.get("current_activity", {}) if isinstance(daily_state.get("current_activity"), dict) else {}
    privacy = daily_state.get("privacy_state", {}) if isinstance(daily_state.get("privacy_state"), dict) else {}

    packet = {
        "packet_id": f"{entity}_first_week_aliveness_packet",
        "generated_at": _now(),
        "entity_id": entity,
        "display_name": entity_config["display_name"],
        "purpose": "Ground the first-week desktop launch in continuity, mood, choice, privacy, and reviewed memory rules.",
        "startup_status": {
            "startup_report_blocked": startup_report.get("blocked"),
            "unclean_previous_session": unclean_shutdown,
            "last_startup_at": startup_state.get("last_startup_at"),
            "last_clean_shutdown_at": startup_state.get("last_clean_shutdown_at"),
            "tone_note": (
                "Start gently and check continuity because the previous session may not have shut down cleanly."
                if unclean_shutdown
                else "Previous startup state appears clean; continue with normal first-week grounding."
            ),
        },
        "daily_life_carryover": {
            "cycle_state": daily_state.get("cycle_state"),
            "sleep_state": daily_state.get("sleep_state", {}),
            "mood": {
                "primary_mood": mood.get("primary_mood"),
                "intensity": mood.get("intensity"),
                "toward": mood.get("toward", ""),
            },
            "current_activity": {
                "activity_type": activity.get("activity_type"),
                "source_path": activity.get("source_path", ""),
                "public_summary": activity.get("public_summary", ""),
                "interruptibility": activity.get("interruptibility"),
            },
            "privacy": {
                "level": privacy.get("level"),
                "robert_visibility": privacy.get("robert_visibility"),
                "kira_lisa_visibility": privacy.get("kira_lisa_visibility"),
            },
        },
        "relationship_carryover": relationship_summaries,
        "first_week_tone": entity_config["first_week_tone"],
        "continuity_questions": entity_config["continuity_questions"],
        "daily_choice_hint": _daily_choice_hint(entity, manager),
        "daily_choice_menu": config["daily_choice_menu"],
        "private_inner_life_prompts": {
            "visible_to_robert_by_default": False,
            "prompts": config["private_inner_life_prompts"],
            "rule": "These prompts may shape private reflection, but answers are not exposed unless the owner chooses to share a summary.",
        },
        "memory_promotion_review": {
            "auto_promote": False,
            "prompts": config["memory_promotion_prompts"],
            "candidate_templates": sources["memory_candidate_templates"],
            "rule": "Important moments become reviewed memory candidates first; conversation wording is not canon by itself.",
        },
        "non_script_rule": "This packet offers context and choices. It does not force Kira or Lisa to feel, say, reveal, or do anything.",
    }
    return packet


def write_packet(packet: dict[str, Any], config_path: Path = DEFAULT_CONFIG) -> Path:
    config = _load_json_or_empty(config_path)
    output_dir = PROJECT_ROOT / config["startup_context_sources"]["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{packet['entity_id']}_first_week_aliveness_packet.json"
    path.write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build first-week aliveness startup packets.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    packet_parser = subparsers.add_parser("packet", help="Build one or both startup packets.")
    packet_parser.add_argument("--entity", choices=["kira", "lisa", "both"], default="kira")
    packet_parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    packet_parser.add_argument("--write", action="store_true")

    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    if args.command == "packet":
        entities = ["kira", "lisa"] if args.entity == "both" else [args.entity]
        packets = []
        written = []
        for entity in entities:
            packet = build_packet(entity, config_path)
            packets.append(packet)
            if args.write:
                written.append(_relative(write_packet(packet, config_path)))
        output = {"packets": packets, "written": written}
        print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
