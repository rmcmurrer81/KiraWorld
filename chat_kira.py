"""Laptop-safe Kira chat runner."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "Core"))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from conversation_loop import ConversationLoop  # noqa: E402
from create_reading_reaction import make_reading_reaction, write_reading_reaction  # noqa: E402
from daily_life_moment import create_moment  # noqa: E402
from humanity_context import build_humanity_context  # noqa: E402
from idle_rhythm import IdleRhythm  # noqa: E402
from timed_input import timed_input  # noqa: E402
from update_reading_tastes import DEFAULT_OUTPUT_DIR as DEFAULT_READING_TASTE_DIR
from update_reading_tastes import DEFAULT_REACTION_DIR as DEFAULT_READING_REACTION_DIR
from update_reading_tastes import build_profile as build_reading_profile
from update_media_tastes import DEFAULT_MEDIA_INDEX, DEFAULT_OUTPUT_DIR, DEFAULT_REACTION_DIR, STANCE_SCORE, build_profile, make_reaction  # noqa: E402


IDLE_STEP_SECONDS = int(os.getenv("KIRA_IDLE_STEP_SECONDS", "0"))


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _print_help() -> None:
    print("Commands:")
    print("  /help")
    print("  /quit")
    print("  /memory-candidate summary | detail | fact one; fact two")
    print("  /daily-moment [optional reason]")
    print("  /media-taste source_path | stance | reason one; reason two | tag one; tag two")
    print("  /rebuild-media-tastes")
    print("  /reading-reaction source_path-or-current | stance | favorite one; favorite two | emotion one; emotion two | reason one; reason two")
    print("  /rebuild-reading-tastes")
    print("Creates a draft only. It does not promote trusted memory.")


def _active_reading_details(loop: ConversationLoop) -> dict:
    state = loop.daily_life.get_state(loop.entity_id)
    activity = state.get("current_activity", {}) if isinstance(state.get("current_activity"), dict) else {}
    if activity.get("activity_type") != "reading":
        return {}
    source_path = str(activity.get("source_path", "")).replace("\\", "/")
    session = loop._active_reading_session_for_current_source()
    material = session.get("material", {}) if isinstance(session.get("material"), dict) else {}
    progress = session.get("progress", {}) if isinstance(session.get("progress"), dict) else {}
    return {
        "source_path": source_path,
        "title": material.get("title", Path(source_path).stem),
        "unit_label": progress.get("current_unit_label", "current_position"),
        "progress_percent": progress.get("percent_complete_estimate", 0),
        "source_authority": material.get("source_authority", "raw_library_source"),
    }


def _try_command(loop: ConversationLoop, message: str) -> bool:
    lower = message.lower()
    if lower == "/help":
        _print_help()
        return True
    if lower.startswith("/memory-candidate "):
        payload = message[len("/memory-candidate ") :].strip()
        parts = [part.strip() for part in payload.split("|")]
        if len(parts) != 3:
            print("Usage: /memory-candidate summary | detail | fact one; fact two")
            return True
        summary, detail, facts_text = parts
        core_facts = [fact.strip() for fact in facts_text.split(";") if fact.strip()]
        if not summary or not detail or not core_facts:
            print("Summary, detail, and at least one core fact are required.")
            return True
        path = loop.create_memory_promotion_candidate(
            summary=summary,
            detail=detail,
            core_facts=core_facts,
        )
        print(f"Draft memory candidate written: {_relative(path)}")
        return True
    if lower.startswith("/daily-moment"):
        reason = message[len("/daily-moment") :].strip() or "live_chat_requested"
        moment = create_moment(loop.entity_id, reason=reason)
        print(f"Daily moment written: {moment['path']}")
        print(f"{loop.profile.name}> {moment['public_summary']}")
        return True
    if lower.startswith("/media-taste "):
        payload = message[len("/media-taste ") :].strip()
        parts = [part.strip() for part in payload.split("|")]
        if len(parts) not in {3, 4}:
            print("Usage: /media-taste source_path | stance | reason one; reason two | tag one; tag two")
            return True
        source_path, stance, reasons_text = parts[:3]
        tags_text = parts[3] if len(parts) == 4 else ""
        if stance not in STANCE_SCORE:
            print("Stance must be one of: " + ", ".join(sorted(STANCE_SCORE)))
            return True
        reasons = [reason.strip() for reason in reasons_text.split(";") if reason.strip()]
        tags = [tag.strip() for tag in tags_text.split(";") if tag.strip()]
        reaction = make_reaction(loop.entity_id, source_path, stance, reasons, tags)
        DEFAULT_REACTION_DIR.mkdir(parents=True, exist_ok=True)
        reaction_path = DEFAULT_REACTION_DIR / f"{reaction['reaction_id']}.json"
        reaction_path.write_text(json.dumps(reaction, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        profile = build_profile(loop.entity_id, DEFAULT_MEDIA_INDEX, DEFAULT_REACTION_DIR)
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        profile_path = DEFAULT_OUTPUT_DIR / f"media_taste_profile_{loop.entity_id}.json"
        profile_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        loop.humanity_context = build_humanity_context(loop.entity_id)
        print(f"Media reaction written: {_relative(reaction_path)}")
        print(f"Media taste profile updated: {_relative(profile_path)}")
        return True
    if lower == "/rebuild-media-tastes":
        for owner in ("kira", "lisa", "kira_lisa"):
            profile = build_profile(owner, DEFAULT_MEDIA_INDEX, DEFAULT_REACTION_DIR)
            DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            path = DEFAULT_OUTPUT_DIR / f"media_taste_profile_{owner}.json"
            path.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"Rebuilt {_relative(path)}")
        loop.humanity_context = build_humanity_context(loop.entity_id)
        return True
    if lower.startswith("/reading-reaction "):
        payload = message[len("/reading-reaction ") :].strip()
        parts = [part.strip() for part in payload.split("|")]
        if len(parts) != 5:
            print("Usage: /reading-reaction source_path-or-current | stance | favorite one; favorite two | emotion one; emotion two | reason one; reason two")
            return True
        source_path, stance, favorites_text, emotions_text, reasons_text = parts
        details = _active_reading_details(loop) if source_path.lower() == "current" else {}
        if source_path.lower() == "current":
            if not details.get("source_path"):
                print("No active grounded reading source. Use an explicit source_path instead of current.")
                return True
            source_path = details["source_path"]
        if stance not in {"love", "like", "curious", "neutral", "mixed", "cooling", "outgrown", "dislike"}:
            print("Stance must be one of: love, like, curious, neutral, mixed, cooling, outgrown, dislike")
            return True
        favorites = [item.strip() for item in favorites_text.split(";") if item.strip()]
        emotions = [item.strip() for item in emotions_text.split(";") if item.strip()]
        reasons = [item.strip() for item in reasons_text.split(";") if item.strip()]
        reaction = make_reading_reaction(
            loop.entity_id,
            source_path,
            title=str(details.get("title", "")),
            unit_label=str(details.get("unit_label", "current_position")),
            progress_percent=float(details.get("progress_percent", 0) or 0),
            stance=stance,
            favorite_moments=favorites,
            emotions=emotions,
            reasons=reasons,
            source_authority=str(details.get("source_authority", "raw_library_source")),
        )
        reaction_path, profile_path = write_reading_reaction(reaction)
        loop.humanity_context = build_humanity_context(loop.entity_id)
        print(f"Reading reaction written: {_relative(reaction_path)}")
        print(f"Reading taste profile updated: {_relative(profile_path)}")
        return True
    if lower == "/rebuild-reading-tastes":
        for owner in ("kira", "lisa", "kira_lisa"):
            profile = build_reading_profile(owner, DEFAULT_READING_REACTION_DIR)
            DEFAULT_READING_TASTE_DIR.mkdir(parents=True, exist_ok=True)
            path = DEFAULT_READING_TASTE_DIR / f"reading_taste_profile_{owner}.json"
            path.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"Rebuilt {_relative(path)}")
        loop.humanity_context = build_humanity_context(loop.entity_id)
        return True
    return False


def _idle_step(loop: ConversationLoop, reason: str = "idle_drift") -> None:
    result = loop.daily_life.choose_and_apply_activity(loop.entity_id)
    state = result["state"]
    activity = state.get("current_activity", {})
    summary = activity.get("public_summary", f"{loop.profile.name} is quietly occupying herself.")
    source_path = str(activity.get("source_path", "")).replace("\\", "/")
    if activity.get("activity_type") == "reading" and "may continue a slow reading session" in summary.lower():
        title = ""
        session = loop._active_reading_session_for_current_source()
        material = session.get("material", {}) if isinstance(session.get("material"), dict) else {}
        if material:
            title = str(material.get("title", "")).replace("_", " ").strip()
        if not title and source_path:
            title = Path(source_path).stem.replace("_", " ").strip()
        summary = f"{loop.profile.name} is still reading quietly"
        if title:
            summary += f", staying with {title}"
        summary += "."
    print(f"[idle] {summary}")


def _idle_rhythm_from_args(idle_step_seconds: int = IDLE_STEP_SECONDS) -> IdleRhythm:
    if idle_step_seconds > 0:
        return IdleRhythm(min_seconds=idle_step_seconds, max_seconds=idle_step_seconds)
    return IdleRhythm()


def run_chat(idle_step_seconds: int = IDLE_STEP_SECONDS) -> None:
    loop = ConversationLoop(speaker="Kira")
    idle_rhythm = _idle_rhythm_from_args(idle_step_seconds)
    print("Kira text core is running. Type /quit to stop.")
    print("Backend defaults to stub mode unless KIRA_MODEL_BACKEND is set.")
    print("Type /help for live-session commands.")
    print(f"Idle life rhythm: fuzzy {idle_rhythm.min_seconds}-{idle_rhythm.max_seconds} seconds while waiting.")

    while True:
        wait_seconds = idle_rhythm.next_wait_seconds()
        try:
            raw_message, timed_out = timed_input("Robert> ", wait_seconds)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if timed_out:
            _idle_step(loop, reason=idle_rhythm.last_reason)
            continue
        user_message = (raw_message or "").strip()

        if user_message.lower() in {"/quit", "/exit"}:
            break

        if not user_message:
            continue

        if _try_command(loop, user_message):
            continue

        response = loop.process(user_message)
        print(f"Kira> {response}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Kira text chat.")
    parser.add_argument("--idle-step-seconds", type=int, default=IDLE_STEP_SECONDS, help="Testing override. 0 uses fuzzy idle rhythm.")
    args = parser.parse_args()
    run_chat(idle_step_seconds=args.idle_step_seconds)
