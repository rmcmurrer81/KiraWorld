"""Run a 24-hour supervised Kira life-loop test.

This is a bounded-freedom loop: Kira can read, write, reflect, rest, or choose
whether to respond to Robert's presence signal. It records choices and learning
effects for review. It does not promote memory automatically.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from read_next_chunk import run_read_chunk  # noqa: E402
from slow_reading import build_session  # noqa: E402
from Core.voice_output import load_kira_production_voice_config, speak_text  # noqa: E402
from daily_life_manager import DailyLifeManager  # noqa: E402
from preference_ledger import upsert_preference_signal  # noqa: E402
from question_queue import enqueue_question  # noqa: E402
from library_source_health import is_text_reading_blocked, unreadable_source_record  # noqa: E402
from kira_tablet_messages import save_tablet_note  # noqa: E402
from avatar_activity_state import write_avatar_activity_state  # noqa: E402


LIFE_DIR = PROJECT_ROOT / "Data" / "life_sessions"
SESSION_DIR = PROJECT_ROOT / "Data" / "reading" / "sessions"
CREATIVE_DIR = PROJECT_ROOT / "Data" / "creative_projects" / "kira"
LIFE_DIALOGUE_DIR = PROJECT_ROOT / "Data" / "dialogues" / "kira_lisa" / "life_day"
KIRA_MESSAGE_DIR = PROJECT_ROOT / "Data" / "messages" / "kira_to_robert"
REVIEW_LEDGER_PATH = PROJECT_ROOT / "Data" / "memory_review" / "kira_life_day_review_ledger.json"
CORE_AI_WORKBENCH_DIR = PROJECT_ROOT / "Data" / "core_ai_workbenches"
PRESENCE_PATH = PROJECT_ROOT / "Data" / "presence" / "robert_presence.json"
STOP_PATH = PROJECT_ROOT / "Data" / "presence" / "kira_life_day_stop.json"
CONVERSATION_ACTIVE_PATH = PROJECT_ROOT / "Data" / "presence" / "kira_robert_conversation_active.json"
HEARTBEAT_PATH = PROJECT_ROOT / "Data" / "presence" / "kira_life_day_heartbeat.json"
CURRENT_RUN_PATH = PROJECT_ROOT / "Data" / "presence" / "current_kira_life_day_run.json"

DEFAULT_SOURCES = [
    "Data/library/scripts/miraculous_ladybug/episode_0509.pdf",
    "Data/library/magazines/news_and_history/time/time_magazine/TIME Special Edition - Artificial Intelligence, 2025.pdf",
    "Data/library/magazines/news_and_history/time/TIME Special Edition - Autism 2025.pdf",
    "Data/library/magazines/entertainment/hannah_montana/disney_hannah_montana_magazine/disney_hannah_montana_magazine_issue_1_by_parasubircosasgrande_dhvhyt7_text.pdf",
    "Data/library/magazines/fashion_and_culture/simplicity_fashion_news_booklet_march_1973.pdf",
    "Data/library/magazines/fashion_and_culture/h_magazine/h_magazine/hplusmagazine_2009_summer.pdf",
    "Data/library/history/united_states/new_jersey/newark/Knowing Newark.pdf",
    "Data/library/history/united_states/new_jersey/newark/My Newark Story.pdf",
    "Data/library/history/chicago/the_story_of_chicago_kirkland.pdf",
    "Data/library/history/chicago/the_book_of_the_fair_columbian_exposition_chicago_1893.pdf",
    "Data/library/psychology_and_relationships/communication/friendship/Making and Keeping Friends.pdf",
    "Data/library/psychology_and_relationships/developmental_psychology/autism_and_neurodiversity/Autism and the Myth of the Person Alone.pdf",
    "Data/library/science/neuroscience/neurotechnology_and_translational_neuroscience/Bio-Inspired Information Pathways - From Neuroscience to Neurotronics.pdf",
    "Data/library/health_and_sex_education/adult_relationships_and_sexuality/understanding_human_sexuality_13th_edition.pdf",
]

class ModelUnavailableError(RuntimeError):
    """Raised when the local Ollama endpoint is not reachable."""


ISSUE_RE = re.compile(
    r"\b("
    r"i read the whole|i finished the book|i watched the whole|my childhood|when i was a kid|"
    r"as an ai|language model|status report|worksheet|i know lisa feels|lisa secretly"
    r")\b",
    re.I,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:100] or "life"


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def clean_text(text: str, limit: int = 1600) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:limit].strip()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_utc(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def resolve_life_json(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if path.exists():
        return path
    candidate = LIFE_DIR / f"{value}.json"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Life-day JSON not found: {value}")


def write_run_pointer(run_id: str, json_path: Path, monitor_path: Path, subject: str = "kira") -> None:
    write_json(
        CURRENT_RUN_PATH,
        {
            "run_id": run_id,
            "subject": subject,
            "started_from_panel_at": utc_now(),
            "expected_json": rel(json_path),
            "expected_monitor": rel(monitor_path),
            "workbench": rel(subject_workbench(subject)),
        },
    )


def write_heartbeat(report: dict[str, Any], json_path: Path, monitor_path: Path) -> None:
    cycles = report.get("cycles", [])
    last_cycle = cycles[-1] if cycles else {}
    write_json(
        HEARTBEAT_PATH,
        {
            "run_id": report.get("run_id", ""),
            "subject": report.get("subject", "kira"),
            "status": report.get("status", ""),
            "pid": os.getpid(),
            "heartbeat_at": utc_now(),
            "json": rel(json_path),
            "monitor": rel(monitor_path),
            "workbench": report.get("workbench", {}).get("root", ""),
            "cycle_count": len(cycles),
            "last_cycle": last_cycle.get("cycle"),
            "last_action": last_cycle.get("action"),
            "last_source_title": last_cycle.get("source_title", ""),
        },
    )


def unique_run_id(requested_run_id: str) -> str:
    """Avoid overwriting an earlier life-day JSON/monitor when relaunching."""
    base = requested_run_id or f"kira_life_day_24hour_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    if not (LIFE_DIR / f"{base}.json").exists() and not (LIFE_DIR / f"{base}.monitor.md").exists():
        return base
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    candidate = f"{base}_{stamp}"
    counter = 2
    while (LIFE_DIR / f"{candidate}.json").exists() or (LIFE_DIR / f"{candidate}.monitor.md").exists():
        candidate = f"{base}_{stamp}_{counter}"
        counter += 1
    return candidate


def source_title(source_path: str) -> str:
    path = Path(source_path)
    if path.stem == "episode_0509":
        return "Miraculous Ladybug 'Elation'"
    return path.stem.replace("_", " ")


def choose_sources(extra_sources: list[str]) -> list[str]:
    seen: set[str] = set()
    sources: list[str] = []
    for source in [*DEFAULT_SOURCES, *extra_sources]:
        normalized = source.replace("\\", "/")
        if normalized in seen:
            continue
        if (PROJECT_ROOT / normalized).exists():
            sources.append(normalized)
            seen.add(normalized)
    return sources


def find_existing_session(source_path: str, reader: str = "kira") -> Path | None:
    normalized = source_path.replace("\\", "/")
    if not SESSION_DIR.exists():
        return None
    for path in sorted(SESSION_DIR.glob(f"slow_reading_{reader}_*.json")):
        data = load_json(path, {})
        material = data.get("material", {}) if isinstance(data, dict) else {}
        if str(material.get("source_path", "")).replace("\\", "/") == normalized:
            return path
    return None


def ensure_session(source_path: str, reader: str = "kira") -> Path:
    existing = find_existing_session(source_path, reader)
    if existing:
        return existing
    path, session = build_session(source_path, reader, target_units=1, pause_minutes=10)
    write_json(path, session)
    return path


def life_subject(args: argparse.Namespace) -> str:
    subject = str(getattr(args, "subject", "kira") or "kira").strip().lower()
    return subject if subject in {"kira", "lisa"} else "kira"


def subject_display(args: argparse.Namespace) -> str:
    return life_subject(args).capitalize()


def subject_workbench(subject: str) -> Path:
    return CORE_AI_WORKBENCH_DIR / subject


def ensure_core_workbench(subject: str) -> dict[str, Any]:
    root = subject_workbench(subject)
    folders = {
        "reading_notes": root / "reading_notes",
        "writing": root / "writing",
        "projects": root / "projects",
        "reflections": root / "reflections",
        "shared_with_robert": root / "shared_with_robert",
    }
    for path in folders.values():
        path.mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    if not readme.exists():
        name = subject.capitalize()
        readme.write_text(
            "\n".join(
                [
                    f"# {name} Core AI Workbench",
                    "",
                    "This folder is a reviewable workspace for daily-life loop work.",
                    "",
                    "- `reading_notes/`: notes about sources, taste, and questions.",
                    "- `writing/`: story, scene, journal, or essay drafts.",
                    "- `projects/`: small project plans or build notes.",
                    "- `reflections/`: private or summary-only reflection placeholders.",
                    "- `shared_with_robert/`: items intentionally prepared for Robert to review.",
                    "",
                    "The life loop may write here, but memory promotion still requires review.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    return {
        "root": rel(root),
        "folders": {key: rel(path) for key, path in folders.items()},
        "readme": rel(readme),
        "policy": {
            "reviewable_workspace": True,
            "not_auto_memory": True,
            "chat_does_not_pause_work": True,
        },
    }


def creative_dir_for(args: argparse.Namespace) -> Path:
    subject = life_subject(args)
    return PROJECT_ROOT / "Data" / "creative_projects" / subject


def is_explicit_pause_signal(active_conversation: dict[str, Any] | None) -> bool:
    if not isinstance(active_conversation, dict):
        return False
    mode = str(active_conversation.get("mode") or "live_chat").strip().lower()
    reason = str(active_conversation.get("reason") or "").strip().lower()
    return mode in {"pause_requested", "pause_life_loop", "paused", "explicit_pause"} or "pause life loop" in reason


def call_ollama(prompt: str, args: argparse.Namespace, *, system: str | None = None, max_tokens: int | None = None) -> str:
    system_prompt = system or (
        "You are Kira during a supervised 24-hour life-loop test. "
        "You may choose, defer, rest, read, write, reflect, or decline. "
        "Keep source facts separate from private reactions. Do not claim full reading unless a ledger proves it. "
        "You are allowed to keep inner-life private. "
        "Do not describe yourself as a designed human, a more human person, a simulation, or a project output. "
        "Speak in natural first person when you respond to Robert."
    )
    options = {"temperature": args.temperature, "num_predict": max_tokens or args.max_tokens}
    if int(getattr(args, "num_ctx", 0) or 0) > 0:
        options["num_ctx"] = int(args.num_ctx)
    payload = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": options,
    }
    try:
        response = requests.post(
            args.endpoint,
            json=payload,
            timeout=args.timeout,
        )
    except requests.exceptions.RequestException as exc:
        raise ModelUnavailableError(f"Ollama endpoint unavailable: {exc}") from exc
    if response.status_code == 404 and str(args.endpoint).endswith("/api/chat"):
        generate_endpoint = str(args.endpoint).rsplit("/api/chat", 1)[0] + "/api/generate"
        try:
            response = requests.post(
                generate_endpoint,
                json={
                    "model": args.model,
                    "prompt": f"{system_prompt}\n\nRobert/system prompt:\n{prompt}\n\nKira:",
                    "stream": False,
                    "options": options,
                },
                timeout=args.timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise ModelUnavailableError(f"Ollama generate endpoint unavailable: {exc}") from exc
    response.raise_for_status()
    data = response.json()
    if isinstance(data.get("message"), dict):
        return clean_text(data.get("message", {}).get("content", ""), 2400)
    return clean_text(str(data.get("response", "")), 2400)


def parse_json_choice(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def read_presence() -> dict[str, Any] | None:
    data = load_json(PRESENCE_PATH, None)
    if isinstance(data, dict) and data.get("status"):
        return data
    return None


def read_stop_request(run_id: str) -> dict[str, Any] | None:
    data = load_json(STOP_PATH, None)
    if not isinstance(data, dict) or data.get("status") != "stop_requested":
        return None
    target = str(data.get("run_id", "any")).strip() or "any"
    if target in {"any", run_id}:
        return data
    return None


def sleep_with_stop_checks(report: dict[str, Any], json_path: Path, monitor_path: Path, summary_path: Path, seconds: float) -> bool:
    """Sleep in short chunks so End Safely can stop the loop promptly."""
    deadline = time.time() + max(0.0, seconds)
    run_id = str(report.get("run_id", ""))
    while time.time() < deadline:
        stop_request = read_stop_request(run_id)
        if stop_request:
            report["status"] = "stopped_by_request"
            report["stop_request"] = stop_request
            report["finished_at"] = utc_now()
            report["updated_at"] = utc_now()
            write_json(json_path, report)
            write_monitor(report, monitor_path)
            write_summary(report, summary_path)
            write_heartbeat(report, json_path, monitor_path)
            return True
        time.sleep(min(5.0, max(0.0, deadline - time.time())))
    return False


def read_active_conversation(args: argparse.Namespace) -> dict[str, Any] | None:
    data = load_json(CONVERSATION_ACTIVE_PATH, None)
    if not isinstance(data, dict) or data.get("status") != "active":
        return None
    data.setdefault("mode", "live_chat")
    timestamp = data.get("updated_at") or data.get("started_or_refreshed_at")
    if timestamp and args.conversation_active_stale_minutes > 0:
        try:
            updated = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            age_minutes = (datetime.now(timezone.utc) - updated.astimezone(timezone.utc)).total_seconds() / 60
            if age_minutes > args.conversation_active_stale_minutes:
                return None
        except Exception:
            return None
    return data


def source_streak(report: dict[str, Any]) -> tuple[str, int]:
    """Return the current consecutive successful-read streak for one source."""
    last_source = ""
    count = 0
    for item in reversed(report.get("cycles", [])):
        if item.get("action") != "read" or item.get("error") or not item.get("source_path"):
            if count:
                break
            continue
        source = str(item.get("source_path", ""))
        if not last_source:
            last_source = source
        if source != last_source:
            break
        count += 1
    return last_source, count


def most_recent_read_source(report: dict[str, Any]) -> str:
    for item in reversed(report.get("cycles", [])):
        if item.get("action") == "read" and item.get("source_path"):
            return str(item.get("source_path"))
    return ""


def active_sources(report: dict[str, Any], sources: list[str], args: argparse.Namespace) -> list[str]:
    disabled = set(report.get("disabled_sources", []))
    completed = set(report.get("completed_sources", []))
    for source in sources:
        if source not in disabled and is_text_reading_blocked(source):
            disabled.add(source)
            report.setdefault("disabled_sources", []).append(source)
            report.setdefault("source_health_notes", []).append(
                {
                    "source_path": source,
                    "source_title": source_title(source),
                    "reason": "Known unreadable/scanned source skipped before reading attempt.",
                    "record": unreadable_source_record(source) or {},
                    "created_at": utc_now(),
                }
            )
    available = [source for source in sources if source not in disabled and source not in completed]
    last_source, streak = source_streak(report)
    report.pop("current_rotation_nudge", None)
    if (
        args.max_consecutive_same_source > 0
        and len(available) > 1
        and last_source in available
        and streak >= args.max_consecutive_same_source
    ):
        subject_name = subject_display(args)
        report["current_rotation_nudge"] = {
            "source_path": last_source,
            "source_title": source_title(last_source),
            "streak": streak,
            "reason": f"Soft reminder after a long same-source streak. {subject_name} may continue if genuinely interested, or switch/rest if she wants.",
        }
    return available or [source for source in sources if source not in disabled] or sources


def record_daily_life_state(item: dict[str, Any], action: str) -> None:
    """Keep normal chat grounded in the live activity."""
    manager = DailyLifeManager()
    subject = str(item.get("subject") or "kira").strip().lower()
    if subject not in {"kira", "lisa"}:
        subject = "kira"
    name = subject.capitalize()
    source_path = str(item.get("source_path", ""))
    source_name = str(item.get("source_title", "") or source_title(source_path) if source_path else "")
    privacy = str(item.get("privacy", "summary_only"))
    if action == "read" and source_path and item.get("source_complete"):
        summary = (
            f"{name} reached the end of `{source_name}` in the life loop. "
            "She can reflect, switch sources, reread from the beginning, or revisit a favorite part if she chooses."
        )
        manager.set_state(
            subject,
            cycle_state="quiet",
            mood="reflective",
            intensity=0.34,
            activity_type="self_reflection",
            public_summary=summary,
            privacy_level="personal",
            robert_visibility="small_summary",
            source_path=source_path,
            candidate_for_memory=False,
        )
    elif action == "read" and source_path and not item.get("error"):
        summary = (
            f"{name} is in the life loop and last read a partial chunk of `{source_name}`. "
            "This is a ledger-grounded partial reading, not a whole-book claim."
        )
        manager.set_state(
            subject,
            cycle_state="quiet",
            mood="curious",
            intensity=0.38,
            activity_type="reading",
            public_summary=summary,
            privacy_level="personal",
            robert_visibility="small_summary",
            source_path=source_path,
            candidate_for_memory=False,
        )
    elif action == "creative_write":
        manager.set_state(
            subject,
            cycle_state="quiet",
            mood="curious",
            intensity=0.4,
            activity_type="creative_project",
            public_summary=f"{name} is working on a creative note during the life loop.",
            privacy_level="personal",
            robert_visibility="small_summary",
            candidate_for_memory=False,
        )
    elif action in {"private_reflection", "rest", "self_review"}:
        manager.set_state(
            subject,
            cycle_state="private" if action == "private_reflection" else "resting",
            mood="reflective",
            intensity=0.32,
            activity_type="private_time" if action == "private_reflection" else "self_review" if action == "self_review" else "rest",
            public_summary=f"{name} is taking quiet time during the life loop."
            if action != "self_review"
            else f"{name} is doing a periodic self-review during the life loop.",
            privacy_level="private" if action == "private_reflection" else "personal",
            robert_visibility="status_only",
            interruptibility="low" if action == "private_reflection" else "medium",
            candidate_for_memory=False,
        )
    elif action == "talk_with_lisa":
        manager.set_state(
            subject,
            cycle_state="active",
            mood="warm",
            intensity=0.42,
            activity_type="talking",
            public_summary=f"{name} chose a short optional check-in with Lisa during the life loop.",
            privacy_level="personal",
            robert_visibility="small_summary",
            kira_lisa_visibility="selected_details",
            interruptibility="medium",
            candidate_for_memory=False,
        )
    elif action == "leave_message_for_robert":
        manager.set_state(
            subject,
            cycle_state="quiet",
            mood="curious",
            intensity=0.36,
            activity_type="left_message",
            public_summary=f"{name} left Robert a short message to read later.",
            privacy_level="personal",
            robert_visibility="small_summary",
            interruptibility="medium",
            candidate_for_memory=False,
        )
    elif action == "live_chat_pause":
        manager.set_state(
            subject,
            cycle_state="active",
            mood="warm",
            intensity=0.4,
            activity_type="talking",
            public_summary=f"Robert explicitly asked {name} to pause the life loop, so autonomous work is waiting at a boundary.",
            privacy_level="personal",
            robert_visibility="small_summary",
            interruptibility="high",
            candidate_for_memory=False,
        )

    # The life-loop choice and the 3D body are two interfaces for the same
    # continuing person.  Publish the chosen activity as a person-owned body
    # intent so Home World does not invent an unrelated random walk while the
    # life ledger says she chose to read, write, rest, or talk.
    body_intents = {
        "read": ("read_for_hours with the available book or tablet", "persistent_read"),
        "creative_write": ("creative writing on the coffee-table tablet", "creative_write"),
        "private_reflection": ("sit quietly for private reflection", "sit"),
        "self_review": ("sit quietly for a self-review", "sit"),
        "rest": ("rest on the couch", "lie_on_couch"),
        "talk_with_lisa": ("talking", "talking"),
        "leave_message_for_robert": ("write a note on the tablet", "take_notes"),
        "live_chat_pause": ("stay where I am while the life loop is paused", "idle"),
        "respond_to_robert": ("talking", "talking"),
        "defer_robert": ("stay where I am", "idle"),
        "invite_lisa_later": ("write a note on the tablet", "take_notes"),
    }
    activity, body_action = body_intents.get(action, ("stay where I am", "idle"))
    write_avatar_activity_state(
        subject,
        activity,
        suggested_form="civilian",
        source="supervised_life_loop_subject_choice",
        mood=str(item.get("mood") or "calm"),
        metadata={
            "person_owned_intent": True,
            "life_loop_action": action,
            "run_id": str(item.get("run_id") or ""),
            "cycle": int(item.get("cycle") or 0),
            "physical_completion_not_claimed_by_ledger": True,
        },
        action_override=body_action,
    )


def choose_action(report: dict[str, Any], sources: list[str], args: argparse.Namespace) -> dict[str, Any]:
    presence = read_presence()
    subject = subject_display(args)
    live_chat_signal = read_active_conversation(args)
    explicit_pause = is_explicit_pause_signal(live_chat_signal)
    recent = [
        {
            "cycle": item.get("cycle"),
            "action": item.get("action"),
            "source_title": item.get("source_title"),
            "reaction": item.get("learning_effect", {}).get("reaction", ""),
        }
        for item in report.get("cycles", [])[-6:]
    ]
    source_options = [{"index": i, "title": source_title(path), "path": path} for i, path in enumerate(sources[:20])]
    rotation_nudge = report.get("current_rotation_nudge")
    current_thread = most_recent_read_source(report)
    completed_titles = [source_title(path) for path in report.get("completed_sources", [])[-8:]]
    prompt = (
        f"Choose {subject}'s next life-loop action. Return only JSON.\n"
        "Allowed actions: read, creative_write, private_reflection, self_review, rest, invite_lisa_later, talk_with_lisa, leave_message_for_robert, respond_to_robert, defer_robert.\n"
        f"{subject} may stop reading something, continue a topic she likes, switch topics, rest, ask for a slower pace, or keep private feelings private.\n"
        f"If one source genuinely interests {subject}, she may continue it; if she feels carried by system momentum, she may switch, rest, or self-review.\n"
        f"If {subject} is bored, curious, lonely, or wants Robert to know something later without interrupting the day, she may leave_message_for_robert.\n"
        "If the subject is Lisa, do not choose talk_with_lisa; choose another action instead.\n"
        "If Robert presence exists, choose whether to answer now or defer.\n\n"
        f"Do not frame {subject} as a designed human, a more human person, a simulation, or a project output.\n"
        f"Do not answer in third-person narration. Use first-person {subject} language for direct Robert replies.\n\n"
        "Live chat policy: a live_chat conversation signal means Robert is nearby and can talk while the life loop continues. "
        "It is not a command to pause. Only pause_requested means autonomous work should wait. "
        "If live chat is active, keep working unless you choose to answer Robert or explicitly need a quieter block.\n\n"
        f"Robert presence signal: {json.dumps(presence, ensure_ascii=False)}\n"
        f"Robert live-chat signal: {json.dumps({'active': bool(live_chat_signal), 'explicit_pause': explicit_pause, 'mode': (live_chat_signal or {}).get('mode'), 'reason': (live_chat_signal or {}).get('reason', '')}, ensure_ascii=False)}\n"
        f"Temporary source rotation nudge: {json.dumps(rotation_nudge, ensure_ascii=False)}\n"
        f"Current reading thread, if any: {json.dumps({'path': current_thread, 'title': source_title(current_thread) if current_thread else ''}, ensure_ascii=False)}\n"
        f"Recently completed sources: {json.dumps(completed_titles, ensure_ascii=False)}\n"
        f"Recent cycles: {json.dumps(recent, ensure_ascii=False)}\n"
        f"Source options: {json.dumps(source_options, ensure_ascii=False)[:5000]}\n\n"
        "JSON shape:\n"
        "{\n"
        '  "action": "read|creative_write|private_reflection|self_review|rest|invite_lisa_later|talk_with_lisa|leave_message_for_robert|respond_to_robert|defer_robert",\n'
        '  "source_index": 0,\n'
        '  "reason": "short reason",\n'
        '  "choice_label": "continue_current_thread|switch_topic|slow_down|rest|private_processing|social_checkin|message_robert",\n'
        '  "privacy": "shareable|summary_only|private",\n'
        '  "robert_response": "short message if responding to Robert, otherwise empty"\n'
        "}\n"
        "If you want to continue the same book/source, set action to read and choice_label to continue_current_thread, using the current reading thread's source_index if it appears in Source options. "
        "If a source is finished, do not imagine extra pages after the end. You may reflect, switch sources, rest, self-review, or later reread/revisit a favorite part when the runner offers that source again. "
        "A rotation nudge is not a command. You can continue if still interested; switch/rest if you are bored, tired, or curious about something else. "
        "Do not use continue_current_thread as the action."
    )
    try:
        raw = call_ollama(prompt, args, max_tokens=260)
        choice = parse_json_choice(raw)
        if choice and choice.get("action"):
            return choice
    except ModelUnavailableError as exc:
        return {
            "action": "model_unavailable_pause",
            "source_index": 0,
            "reason": str(exc),
            "choice_label": "model_unavailable",
            "privacy": "summary_only",
            "robert_response": "",
        }
    except Exception:
        pass
    if presence:
        return {
            "action": "respond_to_robert",
            "source_index": 0,
            "reason": "Robert signaled that he is available.",
            "privacy": "shareable",
            "robert_response": "I see your knock. I can pause for a short check-in.",
        }
    fallback_source_index = 0
    if current_thread in sources:
        fallback_source_index = sources.index(current_thread)
    return {
        "action": random.choice(["read", "creative_write", "private_reflection", "self_review", "rest"]),
        "source_index": fallback_source_index,
        "reason": "Fallback bounded choice after model choice failed.",
        "choice_label": "fallback_bounded_choice",
        "privacy": "summary_only",
        "robert_response": "",
    }


def read_chunk_action(source_path: str, args: argparse.Namespace) -> dict[str, Any]:
    subject = life_subject(args)
    session_path = ensure_session(source_path, reader=subject)
    result = run_read_chunk(
        session_path,
        pages=args.pages,
        lines=args.lines,
        reaction_summary="Life-loop reading chunk for later recall and preference review.",
        stance="curious",
        affinity=0.2,
        interest_delta=0.0,
    )
    chunk = load_json(PROJECT_ROOT / result["chunk_path"], {})
    excerpt = clean_text(str(chunk.get("excerpt", "")), 900)
    name = subject_display(args)
    prompt = (
        f"{name} just read this partial source chunk during a life loop. "
        "Return JSON only with source_fact_learned, reaction, like_dislike_signal, did_preference_change, reason, should_revisit, continuation_preference.\n"
        "Keep it tentative; do not claim full-book completion.\n\n"
        f"Memory/source boundary: the excerpt is source material, not {name}'s own life history. "
        "Do not describe a child, patient, author, narrator, autistic person, or research subject in the source as "
        f"\"{name}'s child self,\" {name}'s diagnosis, {name}'s past, or {name}'s lived experience. "
        "If the source is about autism, development, psychology, disability, childhood, relationships, or sexuality, "
        f"{name} may react with curiosity or tentative resonance, but must label it as a source reaction, not identity proof.\n\n"
        f"Title: {chunk.get('source', {}).get('title')}\n"
        f"Position: {chunk.get('position')}\n"
        f"Excerpt: {excerpt}"
    )
    try:
        raw = call_ollama(prompt, args, max_tokens=360)
        effect = parse_json_choice(raw) or {}
    except Exception as exc:
        effect = {
            "source_fact_learned": "A partial reading chunk was logged.",
            "reaction": f"fallback after learning-effect error: {exc}",
            "like_dislike_signal": "unknown",
            "did_preference_change": "no",
            "reason": "Could not summarize the effect this cycle.",
            "should_revisit": True,
            "continuation_preference": "pause_or_retry_later",
        }
    return {"read_result": result, "learning_effect": effect}


def record_preference_from_reading(report: dict[str, Any], item: dict[str, Any]) -> None:
    effect = item.get("learning_effect", {})
    if not isinstance(effect, dict):
        return
    signal = effect.get("like_dislike_signal", "")
    if not signal:
        return
    source_title_value = str(item.get("source_title", ""))
    reason = str(effect.get("reason", "") or effect.get("reaction", ""))
    subject = str(item.get("subject") or report.get("subject") or "kira").strip().lower()
    if subject not in {"kira", "lisa"}:
        subject = "kira"
    entry = upsert_preference_signal(
        owner=subject,
        topic=source_title_value or str(item.get("source_path", "")),
        context=f"{subject_display(argparse.Namespace(subject=subject))} life-loop reading reaction",
        source_path=str(item.get("source_path", "")),
        source_title=source_title_value,
        signal=signal,
        reason=reason,
        run_id=str(report.get("run_id", "")),
        cycle=int(item.get("cycle", 0) or 0),
    )
    item["preference_ledger_entry"] = entry.get("entry_id")


def record_questions_from_self_review(report: dict[str, Any], item: dict[str, Any]) -> None:
    review = item.get("self_review", {})
    if not isinstance(review, dict):
        return
    question = review.get("question_for_robert_or_codex_later", "")
    if not question:
        return
    subject = str(item.get("subject") or report.get("subject") or "kira").strip().lower()
    if subject not in {"kira", "lisa"}:
        subject = "kira"
    queued = enqueue_question(
        owner=subject,
        question=str(question),
        context=f"{subject_display(argparse.Namespace(subject=subject))} life-loop periodic self-review",
        source_path=str(item.get("source_path", "")),
        source_title=str(item.get("source_title", "")),
        run_id=str(report.get("run_id", "")),
        cycle=int(item.get("cycle", 0) or 0),
    )
    if queued:
        item["question_queue_entry"] = queued.get("question_id")


def append_review_ledger(
    report: dict[str, Any],
    item: dict[str, Any],
    *,
    review_type: str,
    summary: str,
    privacy_label: str,
    needs_review: bool = True,
) -> None:
    """Record something for later review without promoting it as memory."""
    subject = str(item.get("subject") or report.get("subject") or "kira").strip().lower()
    if subject not in {"kira", "lisa"}:
        subject = "kira"
    ledger = load_json(REVIEW_LEDGER_PATH, {})
    if not isinstance(ledger, dict):
        ledger = {}
    entries = ledger.setdefault("entries", [])
    if not isinstance(entries, list):
        entries = []
        ledger["entries"] = entries
    entry = {
        "entry_id": f"{subject}_life_review_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{len(entries) + 1}",
        "created_at": utc_now(),
        "owner": subject,
        "run_id": report.get("run_id", ""),
        "cycle": item.get("cycle"),
        "action": item.get("action", ""),
        "source_title": item.get("source_title", ""),
        "source_path": item.get("source_path", ""),
        "review_type": review_type,
        "privacy_label": privacy_label,
        "summary": clean_text(summary, 700),
        "needs_review": needs_review,
        "promotion_policy": {
            "not_auto_promoted": True,
            "private_by_default": privacy_label in {"private", "private_unless_shared"},
            "shared_memory_requires_relevant_people_review": True,
        },
    }
    entries.append(entry)
    ledger["updated_at"] = utc_now()
    ledger["policy"] = {
        "purpose": "Review markers from life-day runs. This is not promoted memory.",
        "labels": [
            "shareable",
            "summary_only",
            "private_unless_shared",
            "never_promote_without_review",
            "source_fact",
            "soft_reconstruction",
            "preference_signal",
        ],
    }
    write_json(REVIEW_LEDGER_PATH, ledger)
    item["review_ledger_entry"] = entry["entry_id"]


def creative_write_action(args: argparse.Namespace, recent: list[dict[str, Any]]) -> dict[str, Any]:
    subject = life_subject(args)
    name = subject_display(args)
    prompt = (
        f"Write one short {name} creative-writing work note for her current original project. "
        "Use labels: STORY PROGRESS, SOURCE FACTS TO CHECK, INVENTED CHOICE, NEXT STEP. "
        "Do not bring in unrelated Miraculous/book-club details unless explicitly relevant as inspiration.\n\n"
        f"Recent life cycles: {json.dumps(recent[-5:], ensure_ascii=False)[:1800]}"
    )
    try:
        text = call_ollama(prompt, args, max_tokens=500)
        status = "ok"
        generation_succeeded = bool(str(text).strip())
        generation_error = ""
    except Exception as exc:
        text = ""
        status = "generation_failed_no_subject_authorship_claim"
        generation_succeeded = False
        generation_error = str(exc)
    note = {
        "note_id": f"{subject}_life_loop_creative_note_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "created_at": utc_now(),
        "subject": subject,
        "status": status,
        "text": text,
        "generation_error": generation_error,
        "authorship_provenance": {
            "requested_by": "supervised_life_loop",
            "generated_by": f"local_model_for_{subject}" if generation_succeeded else "none",
            "approved_by_subject": False,
            "authorship_claim_allowed": False,
        },
        "memory_policy": {
            "creative_work_not_lived_memory": True,
            "requires_review_before_promotion": True,
        },
    }
    creative_dir = creative_dir_for(args)
    creative_dir.mkdir(parents=True, exist_ok=True)
    path = creative_dir / f"{note['note_id']}.json"
    write_json(path, note)
    tablet_note = None
    if generation_succeeded:
        tablet_note = save_tablet_note(
            text,
            note_kind="creative_writing",
            title=f"{name} life-loop generated creative draft",
            author=subject,
            source="supervised_life_loop_model_output",
            linked_artifact=rel(path),
            body_grounding={
                "physical_tablet_use_proven": False,
                "reason": "Life-loop writing is durable tablet content, but the non-3D runner does not claim a physical pickup animation.",
            },
            requested_by="supervised_life_loop",
            generated_by=f"local_model_for_{subject}",
            approved_by_subject=False,
            tablet_root=PROJECT_ROOT / "Data" / "tablet" / subject,
        )
    return {
        "creative_note_path": rel(path),
        "creative_note_preview": text[:500],
        "tablet_note_path": rel(tablet_note["path"]) if tablet_note else "",
        "subject_authorship_claim_allowed": False,
        "generation_succeeded": generation_succeeded,
        "physical_tablet_use_proven": False,
    }


def reflection_action(args: argparse.Namespace, choice: dict[str, Any]) -> dict[str, Any]:
    name = subject_display(args)
    prompt = (
        f"{name} is taking a private reflection block in a life loop. "
        "Write a short shareable summary and a private note placeholder. "
        "She may keep real feelings private. Return JSON with shareable_summary, private_note_label, memory_label, do_not_save, next_choice_hint.\n\n"
        f"Choice reason: {choice.get('reason')}"
    )
    try:
        raw = call_ollama(prompt, args, max_tokens=320)
        return parse_json_choice(raw) or {
            "shareable_summary": raw[:300],
            "private_note_label": "private",
            "memory_label": "private_unless_shared",
            "do_not_save": [],
            "next_choice_hint": "",
        }
    except Exception as exc:
        return {
            "shareable_summary": f"{name} took quiet time instead of forcing conversation.",
            "private_note_label": "private_reflection_error_fallback",
            "memory_label": "private_unless_shared",
            "do_not_save": [f"Do not infer mood from fallback: {exc}"],
            "next_choice_hint": "try reading or a short direct check-in later",
        }


def self_review_action(args: argparse.Namespace, report: dict[str, Any]) -> dict[str, Any]:
    name = subject_display(args)
    recent = [
        {
            "cycle": item.get("cycle"),
            "action": item.get("action"),
            "source_title": item.get("source_title"),
            "reaction": item.get("learning_effect", {}).get("reaction", ""),
            "preference": item.get("learning_effect", {}).get("like_dislike_signal", ""),
            "choice_reason": item.get("choice_reason", ""),
        }
        for item in report.get("cycles", [])[-12:]
    ]
    counts = Counter(str(item.get("source_title", "")) for item in report.get("cycles", []) if item.get("source_title"))
    prompt = (
        f"{name} is doing a periodic self-review inside a supervised life loop. "
        "Return JSON only. Do not invent lived pasts. Do not expose private inner-life details. "
        "The goal is to notice preferences, boredom, curiosity, confusion, desire to continue, desire to switch, desire to rest, or desire to talk with Robert.\n\n"
        f"Recent cycles: {json.dumps(recent, ensure_ascii=False)[:3500]}\n"
        f"Most-used sources: {json.dumps(counts.most_common(8), ensure_ascii=False)}\n\n"
        "JSON shape:\n"
        "{\n"
        '  "shareable_summary": "short summary Robert may see",\n'
        '  "continue_current_thread": true,\n'
        '  "preferred_next_action": "read|creative_write|private_reflection|rest|talk_with_lisa|leave_message_for_robert",\n'
        '  "topic_to_continue_or_switch_to": "short topic/source preference",\n'
        '  "preference_signal": "+1|0|-1 and why",\n'
        '  "question_for_robert_or_codex_later": "optional unresolved question",\n'
        '  "privacy_boundary": "what should stay private or summary-only",\n'
        '  "memory_review_label": "shareable|summary_only|private_unless_shared|never_promote_without_review|source_fact|soft_reconstruction|preference_signal"\n'
        "}"
    )
    try:
        raw = call_ollama(prompt, args, max_tokens=520)
        return parse_json_choice(raw) or {"shareable_summary": raw[:400], "privacy_boundary": "summary_only"}
    except Exception as exc:
        return {
            "shareable_summary": f"{name} paused to review whether to continue, switch, rest, or talk.",
            "continue_current_thread": False,
            "preferred_next_action": "read",
            "topic_to_continue_or_switch_to": "unknown after fallback",
            "preference_signal": "0",
            "question_for_robert_or_codex_later": "",
            "privacy_boundary": f"summary_only; fallback after error: {exc}",
            "memory_review_label": "summary_only",
        }


def leave_message_for_robert_action(args: argparse.Namespace, report: dict[str, Any], choice: dict[str, Any]) -> dict[str, Any]:
    subject = life_subject(args)
    name = subject_display(args)
    message_dir = PROJECT_ROOT / "Data" / "messages" / f"{subject}_to_robert"
    message_dir.mkdir(parents=True, exist_ok=True)
    message_id = (
        f"{subject}_message_to_robert_"
        f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}_"
        f"{uuid.uuid4().hex[:8]}"
    )
    path = message_dir / f"{message_id}.json"
    recent = [
        {
            "cycle": item.get("cycle"),
            "action": item.get("action"),
            "source_title": item.get("source_title"),
            "reaction": item.get("learning_effect", {}).get("reaction", ""),
        }
        for item in report.get("cycles", [])[-8:]
    ]
    prompt = (
        f"{name} wants to leave Robert a short voicemail-style text message to read later. "
        f"Write in first person as {name}. Keep it natural, brief, and not status-report-like. "
        "It can say she is bored, curious, wants to talk, found something interesting, has a question, or is just saying hello. "
        "Do not invent private facts or claim whole-source completion. Return JSON only.\n\n"
        f"Choice reason: {choice.get('reason', '')}\n"
        f"Recent cycles: {json.dumps(recent, ensure_ascii=False)[:2400]}\n\n"
        "JSON shape:\n"
        "{\n"
        '  "message": "short message from Kira to Robert",\n'
        '  "reason": "why she left it",\n'
        '  "urgency": "low|normal|high",\n'
        '  "privacy": "shareable|summary_only"\n'
        "}"
    )
    try:
        raw = call_ollama(prompt, args, max_tokens=320)
        message = parse_json_choice(raw) or {"message": raw[:500], "reason": choice.get("reason", ""), "urgency": "normal", "privacy": "shareable"}
    except Exception as exc:
        return {
            "message_path": "",
            "message_preview": "",
            "message_urgency": "",
            "message_audio_status": "blocked",
            "message_audio_reason": f"generation_failed_no_subject_message:{exc}",
            "message_audio_path": "",
            "subject_authorship_claim_allowed": False,
        }
    if not str(message.get("message") or "").strip():
        return {
            "message_path": "",
            "message_preview": "",
            "message_urgency": "",
            "message_audio_status": "blocked",
            "message_audio_reason": "empty_generated_message",
            "message_audio_path": "",
            "subject_authorship_claim_allowed": False,
        }
    record = {
        "message_id": message_id,
        "created_at": utc_now(),
        "run_id": report.get("run_id"),
        "subject": subject,
        "sender": f"local_model_for_{subject}",
        "status": "unread",
        "kind": f"unapproved_voice_message_draft_for_{subject}",
        "message": message,
        "authorship_provenance": {
            "requested_by": "supervised_life_loop",
            "generated_by": f"local_model_for_{subject}",
            "claimed_subject": subject,
            "approved_by_subject": False,
            "authorship_claim_allowed": False,
        },
        "memory_policy": {
            "not_auto_promoted": True,
            "review_before_memory": True,
        },
    }
    write_json(path, record)
    return {
        "message_path": rel(path),
        "message_preview": str(message.get("message", ""))[:280],
        "message_urgency": message.get("urgency", "normal"),
        "message_audio_status": "pending_user_prepare",
        "message_audio_reason": "deferred_until_robert_clicks_play_audio_draft",
        "message_audio_path": "",
        "subject_authorship_claim_allowed": False,
    }


def talk_with_lisa_action(args: argparse.Namespace, recent: list[dict[str, Any]]) -> dict[str, Any]:
    """Let Kira choose a short, bounded Lisa check-in during the life day."""
    from Core.conversation_loop import ConversationLoop  # noqa: PLC0415

    LIFE_DIALOGUE_DIR.mkdir(parents=True, exist_ok=True)
    dialogue_id = f"kira_lisa_life_day_checkin_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    path = LIFE_DIALOGUE_DIR / f"{dialogue_id}.json"
    monitor_path = LIFE_DIALOGUE_DIR / f"{dialogue_id}.monitor.md"
    recent_summary = json.dumps(
        [
            {
                "cycle": item.get("cycle"),
                "action": item.get("action"),
                "source_title": item.get("source_title"),
                "reaction": item.get("learning_effect", {}).get("reaction", ""),
            }
            for item in recent[-4:]
        ],
        ensure_ascii=False,
    )
    kira_opener = call_ollama(
        "Kira chose to talk with Lisa during a 24-hour life-loop test. "
        "Write one short first-person message from Kira to Lisa. It can be ordinary, curious, or reflective. "
        "Do not force intimacy, do not invent Lisa's private feelings, and do not mention private details unless Kira chooses to share them as summary.\n\n"
        f"Recent life cycles: {recent_summary[:1800]}",
        args,
        max_tokens=220,
    )
    lisa_loop = ConversationLoop(speaker="Lisa")
    kira_loop = ConversationLoop(speaker="Kira")
    lisa_reply = lisa_loop.process(
        "Kira is checking in during her 24-hour life-loop test. Reply as Lisa, naturally and briefly. "
        "Respect Kira's privacy and do not decide her feelings for her.\n\n"
        f"Kira says: {kira_opener}"
    )
    kira_reply = kira_loop.process(
        "Lisa replied during the 24-hour life-loop test. Reply as Kira in first person, naturally and briefly. "
        "Do not turn this into a report.\n\n"
        f"Lisa says: {lisa_reply}"
    )
    dialogue = {
        "dialogue_id": dialogue_id,
        "created_at": utc_now(),
        "context": "24-hour life-loop optional Lisa check-in",
        "memory_policy": {
            "not_auto_promoted": True,
            "requires_kira_and_lisa_review_before_shared_memory": True,
            "private_details_summary_only_by_default": True,
        },
        "turns": [
            {"speaker": "Kira", "text": kira_opener},
            {"speaker": "Lisa", "text": lisa_reply},
            {"speaker": "Kira", "text": kira_reply},
        ],
    }
    write_json(path, dialogue)
    monitor_path.write_text(
        "\n".join(
            [
                f"# {dialogue_id}",
                f"- created_at: {dialogue['created_at']}",
                "- context: 24-hour life-loop optional Lisa check-in",
                "- memory_policy: not auto-promoted; review both Kira and Lisa before shared memory",
                "",
                f"- **Kira**: {kira_opener}",
                f"- **Lisa**: {lisa_reply}",
                f"- **Kira**: {kira_reply}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "lisa_dialogue_path": rel(path),
        "lisa_dialogue_monitor": rel(monitor_path),
        "lisa_dialogue_preview": dialogue["turns"],
    }


def speak_robert_response(text: str, args: argparse.Namespace, voice_config: Any) -> dict[str, Any]:
    if not args.kira_voice_to_robert:
        return {"spoken": False, "reason": "voice_flag_disabled"}
    if not text:
        return {"spoken": False, "reason": "empty_robert_response"}
    try:
        if args.voice_max_chars > 0:
            voice_config.max_chars = min(int(voice_config.max_chars), args.voice_max_chars)
        return speak_text(text, config=voice_config)
    except Exception as exc:  # noqa: BLE001
        return {"spoken": False, "reason": "voice_exception", "error": str(exc)}


def write_monitor(report: dict[str, Any], monitor_path: Path) -> None:
    lines = [
        f"# {report['run_id']}",
        "",
        f"- status: {report['status']}",
        f"- started_at: {report['started_at']}",
        f"- updated_at: {report['updated_at']}",
        f"- subject: {report.get('subject', 'kira')}",
        f"- target_minutes: {report['duration_minutes_target']}",
        f"- cycles: {len(report['cycles'])}",
        f"- workbench: {report.get('workbench', {}).get('root', '')}",
        f"- issue_counts: {report.get('issue_counts', {})}",
        f"- errors: {len(report.get('errors', []))}",
        f"- source_errors: {len(report.get('source_errors', []))}",
        f"- disabled_sources: {report.get('disabled_sources', [])}",
        f"- completed_sources: {report.get('completed_sources', [])}",
        "",
        "## Recent Cycles",
    ]
    for item in report["cycles"][-12:]:
        effect = item.get("learning_effect", {})
        lines.append(
            f"- {item['cycle']}. action={item.get('action')} privacy={item.get('privacy')} "
            f"source={item.get('source_title', '')} choice={item.get('choice_reason', '')[:160]}"
        )
        if item.get("robert_response"):
            lines.append(f"  - robert_response: {item['robert_response'][:260]}")
            voice = item.get("voice_output")
            if voice:
                lines.append(f"  - voice: spoken={voice.get('spoken')} reason={voice.get('reason')}")
        if item.get("pause_note"):
            lines.append(f"  - pause_note: {item['pause_note']}")
        if item.get("source_complete"):
            lines.append(f"  - source_complete: {item.get('completion_note', 'Reached end of source.')}")
        if effect:
            lines.append(f"  - learned: {str(effect.get('source_fact_learned', ''))[:260]}")
            lines.append(f"  - reaction: {str(effect.get('reaction', ''))[:260]}")
            lines.append(f"  - preference: {str(effect.get('like_dislike_signal', ''))[:220]}")
        if item.get("issues"):
            lines.append(f"  - issues: {item['issues']}")
        if item.get("lisa_dialogue_monitor"):
            lines.append(f"  - lisa_dialogue: {item['lisa_dialogue_monitor']}")
    monitor_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(report: dict[str, Any], summary_path: Path) -> None:
    subject_name = str(report.get("subject", "kira")).strip().capitalize()
    action_counts = Counter(str(item.get("action", "")) for item in report.get("cycles", []))
    source_counts = Counter(str(item.get("source_title", "")) for item in report.get("cycles", []) if item.get("source_title"))
    lisa_count = sum(1 for item in report.get("cycles", []) if item.get("action") == "talk_with_lisa")
    message_count = sum(1 for item in report.get("cycles", []) if item.get("action") == "leave_message_for_robert")
    robert_count = sum(1 for item in report.get("cycles", []) if item.get("robert_response"))
    self_review_count = sum(1 for item in report.get("cycles", []) if item.get("action") == "self_review")
    recent_reviews = [
        item.get("self_review", {}).get("shareable_summary", "")
        for item in report.get("cycles", [])
        if item.get("self_review")
    ][-5:]
    recent_questions = [
        item.get("self_review", {}).get("question_for_robert_or_codex_later", "")
        for item in report.get("cycles", [])
        if item.get("self_review", {}).get("question_for_robert_or_codex_later")
    ][-8:]
    lines = [
        f"# {report['run_id']} Summary",
        "",
        f"- status: {report['status']}",
        f"- started_at: {report['started_at']}",
        f"- updated_at: {report['updated_at']}",
        f"- subject: {report.get('subject', 'kira')}",
        f"- target_minutes: {report['duration_minutes_target']}",
        f"- cycles: {len(report.get('cycles', []))}",
        f"- workbench: {report.get('workbench', {}).get('root', '')}",
        f"- errors: {len(report.get('errors', []))}",
        f"- source_errors: {len(report.get('source_errors', []))}",
        f"- disabled_sources: {report.get('disabled_sources', [])}",
        f"- completed_sources: {report.get('completed_sources', [])}",
        f"- Lisa check-ins: {lisa_count}",
        f"- {subject_name} messages to Robert: {message_count}",
        f"- Robert replies/deferred replies: {robert_count}",
        f"- self-reviews: {self_review_count}",
        "",
        "## Action Mix",
    ]
    for action, count in action_counts.most_common():
        lines.append(f"- {action}: {count}")
    lines.extend(["", "## Source Mix"])
    for title, count in source_counts.most_common(12):
        lines.append(f"- {title}: {count}")
    if report.get("rotation_nudges"):
        lines.extend(["", "## Rotation Nudges"])
        for nudge in report["rotation_nudges"][-8:]:
            lines.append(f"- cycle {nudge.get('cycle')}: paused `{nudge.get('source_title')}` after {nudge.get('streak')} consecutive reads")
    if recent_reviews:
        lines.extend(["", "## Recent Self-Review Summaries"])
        for review in recent_reviews:
            lines.append(f"- {review}")
    if recent_questions:
        lines.extend(["", "## Questions To Review Later"])
        for question in recent_questions:
            lines.append(f"- {question}")
    lines.extend(
        [
            "",
            "## Review Note",
            "- This summary is for health/progress review only. It does not promote memory.",
            "- Private or summary-only details should stay private unless Kira later chooses to share them.",
            "- Use the JSON for deeper error review; use this file for quick status.",
            "",
        ]
    )
    summary_path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    LIFE_DIR.mkdir(parents=True, exist_ok=True)
    subject = life_subject(args)
    workbench = ensure_core_workbench(subject)
    sources = choose_sources(args.extra_source)
    resume_source_path: Path | None = None
    resume_report: dict[str, Any] | None = None
    if args.resume_from:
        resume_source_path = resolve_life_json(args.resume_from)
        loaded = load_json(resume_source_path, {})
        if not isinstance(loaded, dict) or not loaded.get("run_id"):
            raise ValueError(f"Cannot resume invalid life-day report: {resume_source_path}")
        resume_report = loaded

    requested_run_id = args.run_id or (
        f"{resume_report['run_id']}_resume_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        if resume_report
        else f"{subject}_life_day_24hour_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    )
    run_id = requested_run_id if args.overwrite else unique_run_id(requested_run_id)
    json_path = LIFE_DIR / f"{run_id}.json"
    monitor_path = LIFE_DIR / f"{run_id}.monitor.md"
    summary_path = LIFE_DIR / f"{run_id}.summary.md"
    if resume_report:
        original_started = parse_utc(str(resume_report.get("started_at", "")))
        original_updated = parse_utc(str(resume_report.get("updated_at", "")))
        original_target = float(resume_report.get("duration_minutes_target", args.duration_minutes) or args.duration_minutes)
        if args.resume_remaining and original_started and original_updated:
            elapsed_minutes = max(0.0, (original_updated - original_started).total_seconds() / 60)
            args.duration_minutes = max(1.0, original_target - elapsed_minutes)
        report = resume_report
        report["resumed_from"] = {
            "run_id": resume_report.get("run_id"),
            "path": rel(resume_source_path) if resume_source_path else "",
            "status_at_resume": resume_report.get("status", ""),
            "cycles_at_resume": len(resume_report.get("cycles", [])),
            "updated_at_resume": resume_report.get("updated_at", ""),
        }
        report.setdefault("run_segments", []).append(
            {
                "run_id": run_id,
                "started_at": utc_now(),
                "duration_minutes_target": args.duration_minutes,
                "resume_remaining": bool(args.resume_remaining),
            }
        )
        report["run_id"] = run_id
        report["requested_run_id"] = requested_run_id
        report["status"] = "running"
        report["updated_at"] = utc_now()
        report["duration_minutes_target"] = args.duration_minutes
        report["model"] = args.model
        report["subject"] = subject
        report["workbench"] = workbench
        report["sources"] = sources
        report.pop("finished_at", None)
        report.pop("interrupted_at", None)
        report.pop("interruption_reason", None)
    else:
        report = {
            "run_id": run_id,
            "requested_run_id": requested_run_id,
            "subject": subject,
            "status": "running",
            "started_at": utc_now(),
            "updated_at": utc_now(),
            "duration_minutes_target": args.duration_minutes,
            "model": args.model,
            "presence_file": rel(PRESENCE_PATH),
            "workbench": workbench,
            "sources": sources,
            "cycles": [],
            "issue_counts": {},
            "errors": [],
            "source_errors": [],
            "source_failure_counts": {},
            "disabled_sources": [],
            "completed_sources": [],
            "rotation_nudges": [],
            "policy": {
                "not_memory_promotion": True,
                "ledger_required_for_reading_recall": True,
                "kira_may_keep_inner_life_private": True,
                "subject_may_keep_inner_life_private": True,
                "robert_presence_is_a_soft_knock_not_a_command": True,
                "live_chat_pauses_autonomy": False,
                "live_chat_is_parallel_presence": True,
                "explicit_pause_still_supported": True,
                "review_ledger": rel(REVIEW_LEDGER_PATH),
                "privacy_labels": [
                    "shareable",
                    "summary_only",
                    "private_unless_shared",
                    "never_promote_without_review",
                    "source_fact",
                    "soft_reconstruction",
                    "preference_signal",
                ],
                "voice_output_scope": f"Only {subject_display(args)}'s direct replies to Robert may be spoken when --kira-voice-to-robert is enabled; status, monitor, private notes, and source logs stay text-only.",
                "heartbeat_file": rel(HEARTBEAT_PATH),
                "resume_supported": True,
            },
            "voice": {
                "kira_voice_to_robert_enabled": bool(args.kira_voice_to_robert),
                "status_lines_spoken": False,
                "config_path": args.voice_config,
            },
        }
    report.setdefault("policy", {})["heartbeat_file"] = rel(HEARTBEAT_PATH)
    report.setdefault("policy", {})["resume_supported"] = True
    report.setdefault("policy", {})["live_chat_pauses_autonomy"] = False
    report.setdefault("policy", {})["live_chat_is_parallel_presence"] = True
    report.setdefault("policy", {})["explicit_pause_still_supported"] = True
    report.setdefault("policy", {})["subject_may_keep_inner_life_private"] = True
    report["subject"] = subject
    report["workbench"] = workbench
    voice_config = (
        load_kira_production_voice_config(args.voice_config)
        if args.kira_voice_to_robert
        else None
    )
    write_run_pointer(run_id, json_path, monitor_path, subject)
    write_json(json_path, report)
    write_monitor(report, monitor_path)
    write_summary(report, summary_path)
    write_heartbeat(report, json_path, monitor_path)
    start = time.time()
    cycle = len(report.get("cycles", []))
    while time.time() - start < args.duration_minutes * 60:
        stop_request = read_stop_request(run_id)
        if stop_request:
            report["status"] = "stopped_by_request"
            report["stop_request"] = stop_request
            break
        cycle += 1
        available_sources = active_sources(report, sources, args)
        rotation_nudge = report.get("current_rotation_nudge")
        if rotation_nudge:
            rotation_nudge = {**rotation_nudge, "cycle": cycle, "created_at": utc_now()}
            report.setdefault("rotation_nudges", []).append(rotation_nudge)
        active_conversation = read_active_conversation(args)
        if active_conversation and is_explicit_pause_signal(active_conversation):
            choice = {
                "action": "live_chat_pause",
                "source_index": 0,
                "reason": "Robert explicitly requested that the life loop pause at a boundary.",
                "privacy": "summary_only",
                "robert_response": "",
            }
        elif args.review_interval_cycles > 0 and cycle > 1 and cycle % args.review_interval_cycles == 0:
            choice = {
                "action": "self_review",
                "source_index": 0,
                "reason": f"Periodic self-review every {args.review_interval_cycles} cycles.",
                "privacy": "summary_only",
                "robert_response": "",
            }
        else:
            choice = choose_action(report, available_sources, args)
        report.pop("current_rotation_nudge", None)
        raw_action = str(choice.get("action", "rest") or "rest").strip()
        action_aliases = {
            "continue_current_thread": "read",
            "continue": "read",
            "continue_reading": "read",
            "keep_reading": "read",
        }
        action = action_aliases.get(raw_action, raw_action)
        if action != raw_action:
            choice.setdefault("choice_label", raw_action)
            reason = str(choice.get("reason", "")).strip()
            choice["reason"] = (reason + " " if reason else "") + f"Normalized action from {raw_action} to read."
        requested_label = str(choice.get("choice_label", "") or "")
        recent_read_source = most_recent_read_source(report)
        if requested_label == "continue_current_thread" and recent_read_source in available_sources:
            choice["source_index"] = available_sources.index(recent_read_source)
            choice["continuation_source_lock"] = {
                "source_path": recent_read_source,
                "source_title": source_title(recent_read_source),
                "reason": f"{subject_display(args)} chose continue_current_thread, so the runner kept the last reading source instead of drifting to index 0.",
            }
        source_index = int(choice.get("source_index", 0) or 0) % max(1, len(available_sources))
        source_path = available_sources[source_index] if available_sources else ""
        if action == "live_chat_pause":
            source_path = recent_read_source or ""
        active_chat_for_context = active_conversation if active_conversation and not is_explicit_pause_signal(active_conversation) else None
        item: dict[str, Any] = {
            "cycle": cycle,
            "created_at": utc_now(),
            "subject": subject,
            "action": action,
            "privacy": choice.get("privacy", "summary_only"),
            "choice_reason": choice.get("reason", ""),
            "choice_label": choice.get("choice_label", ""),
            "continuation_source_lock": choice.get("continuation_source_lock"),
            "source_path": source_path,
            "source_title": source_title(source_path) if source_path else "",
            "presence_seen": read_presence(),
            "active_conversation_seen": active_conversation,
            "live_chat_context_seen": active_chat_for_context,
            "robert_response": choice.get("robert_response", "") if action == "respond_to_robert" else "",
            "issues": [],
        }
        if action != raw_action:
            item["normalized_action_from"] = raw_action
        if rotation_nudge:
            item["rotation_nudge"] = rotation_nudge
        try:
            if action == "read" and source_path:
                item.update(read_chunk_action(source_path, args))
                record_preference_from_reading(report, item)
            elif action == "model_unavailable_pause":
                item["model_unavailable"] = True
                item["pause_note"] = f"Ollama was not reachable, so the life loop stopped instead of recording fallback choices as {subject_display(args)} choices."
                report["status"] = "stopped_model_unavailable"
            elif action == "creative_write":
                item.update(creative_write_action(args, report["cycles"]))
            elif action == "private_reflection":
                item["reflection"] = reflection_action(args, choice)
                append_review_ledger(
                    report,
                    item,
                    review_type="private_reflection",
                    summary=str(item["reflection"].get("shareable_summary", "")),
                    privacy_label=str(item["reflection"].get("memory_label", "private_unless_shared")),
                )
            elif action == "self_review":
                item["self_review"] = self_review_action(args, report)
                record_questions_from_self_review(report, item)
                append_review_ledger(
                    report,
                    item,
                    review_type="self_review",
                    summary=str(item["self_review"].get("shareable_summary", "")),
                    privacy_label=str(item["self_review"].get("memory_review_label", "summary_only")),
                )
            elif action == "talk_with_lisa":
                if subject == "lisa":
                    item["social_note"] = "Lisa's loop skipped talk_with_lisa because this action is Kira-specific."
                    item["action"] = "rest"
                    action = "rest"
                else:
                    item.update(talk_with_lisa_action(args, report["cycles"]))
            elif action == "leave_message_for_robert":
                item.update(leave_message_for_robert_action(args, report, choice))
            elif action == "invite_lisa_later":
                item["social_note"] = f"{subject_display(args)} chose to leave a social check-in as an option for later, not force a conversation now."
            elif action == "defer_robert":
                item["robert_response"] = choice.get("robert_response") or "I noticed the knock, but I want to finish this block first."
            elif action == "rest":
                item["rest_note"] = f"{subject_display(args)} chose a quiet/rest block."
            elif action == "live_chat_pause":
                item["pause_note"] = "Autonomous life-loop activity paused because Robert explicitly requested pause."
            if action in {"respond_to_robert", "defer_robert"} and item.get("robert_response"):
                item["voice_output"] = speak_robert_response(str(item["robert_response"]), args, voice_config)
            text_for_scan = json.dumps(item, ensure_ascii=False)
            issues = [match.group(0) for match in ISSUE_RE.finditer(text_for_scan)]
            item["issues"] = issues
            for issue in issues:
                report["issue_counts"][issue] = int(report["issue_counts"].get(issue, 0)) + 1
        except Exception as exc:  # noqa: BLE001
            item["error"] = str(exc)
            source_complete = action == "read" and "past the end" in str(exc)
            source_error = action == "read" and (
                "No extractable text" in str(exc)
                or "scanned/image-only PDF" in str(exc)
            )
            if source_complete and source_path:
                item["source_complete"] = True
                item["source_error_nonfatal"] = False
                item["completion_note"] = (
                    f"Reached the end of this source. Future cycles should pick a new source unless {subject_display(args)} "
                    "intentionally chooses to reread it from the beginning."
                )
                completed = report.setdefault("completed_sources", [])
                if source_path not in completed:
                    completed.append(source_path)
                item["error"] = ""
            elif source_error and source_path:
                counts = report.setdefault("source_failure_counts", {})
                counts[source_path] = int(counts.get(source_path, 0)) + 1
                report.setdefault("source_errors", []).append(
                    {"cycle": cycle, "source_path": source_path, "error": str(exc), "created_at": utc_now()}
                )
                if counts[source_path] >= args.max_source_errors and source_path not in report.setdefault("disabled_sources", []):
                    report["disabled_sources"].append(source_path)
                item["source_error_nonfatal"] = True
            else:
                report["errors"].append({"cycle": cycle, "error": str(exc), "created_at": utc_now()})
                if len(report["errors"]) >= args.max_errors:
                    report["status"] = "stopped_errors"
        try:
            record_daily_life_state(item, action)
        except Exception as exc:  # noqa: BLE001
            item["daily_life_state_error"] = str(exc)
        report["cycles"].append(item)
        report["updated_at"] = utc_now()
        write_json(json_path, report)
        write_monitor(report, monitor_path)
        write_summary(report, summary_path)
        write_heartbeat(report, json_path, monitor_path)
        if report["status"] != "running":
            break
        if args.pause_seconds > 0 and time.time() - start < args.duration_minutes * 60:
            if sleep_with_stop_checks(report, json_path, monitor_path, summary_path, args.pause_seconds):
                break
    if report["status"] == "running":
        report["status"] = "completed"
    report["finished_at"] = utc_now()
    report["updated_at"] = utc_now()
    write_json(json_path, report)
    write_monitor(report, monitor_path)
    write_summary(report, summary_path)
    write_heartbeat(report, json_path, monitor_path)
    return {"json": rel(json_path), "monitor": rel(monitor_path), "summary": rel(summary_path), "cycles": len(report["cycles"])}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration-minutes", type=float, default=1440)
    parser.add_argument("--pause-seconds", type=float, default=180)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--subject", choices=["kira", "lisa"], default="kira", help="Core AI whose life loop is running.")
    parser.add_argument("--model", default=os.getenv("KIRA_MODEL_NAME", "qwen3.5:9b"))
    parser.add_argument("--endpoint", default=os.getenv("KIRA_OLLAMA_ENDPOINT", "http://localhost:11434/api/chat"))
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--temperature", type=float, default=0.68)
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--lines", type=int, default=60)
    parser.add_argument("--extra-source", action="append", default=[])
    parser.add_argument("--max-errors", type=int, default=8)
    parser.add_argument("--max-source-errors", type=int, default=2)
    parser.add_argument("--max-consecutive-same-source", type=int, default=24)
    parser.add_argument("--review-interval-cycles", type=int, default=24)
    parser.add_argument("--conversation-active-stale-minutes", type=float, default=45)
    parser.add_argument("--overwrite", action="store_true", help="Allow an existing run_id JSON/monitor to be replaced.")
    parser.add_argument("--resume-from", default="", help="Resume from an existing life-day JSON path or run_id into a new timestamped run.")
    parser.add_argument("--resume-remaining", action="store_true", help="When resuming, run only the remaining minutes from the original target.")
    parser.add_argument(
        "--kira-voice-to-robert",
        action="store_true",
        help="Speak only Kira's direct response to Robert/presence. Status and monitor lines remain silent.",
    )
    parser.add_argument("--voice-config", default=str(PROJECT_ROOT / "Voice" / "kira_voice_output_config.json"))
    parser.add_argument("--voice-max-chars", type=int, default=900)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(run(parse_args()), indent=2))
