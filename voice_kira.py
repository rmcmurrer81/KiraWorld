"""
Kira typed chat with local voice output.

This runner lets Kira talk aloud after text replies. It does not listen, open
the microphone, or enable speech-to-text.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "Core"))
sys.path.insert(0, str(PROJECT_ROOT))

from Core.conversation_loop import ConversationLoop  # noqa: E402
from Core.voice_output import load_kira_production_voice_config, speak_text  # noqa: E402
from idle_rhythm import IdleRhythm  # noqa: E402
from timed_input import timed_input  # noqa: E402

from chat_kira import _idle_step, _relative, _try_command  # noqa: E402


IDLE_STEP_SECONDS = int(os.getenv("KIRA_IDLE_STEP_SECONDS", "0"))
CHAT_LOG_DIR = PROJECT_ROOT / "Data" / "life_sessions" / "live_chats"
CURRENT_LIFE_RUN_PATH = PROJECT_ROOT / "Data" / "presence" / "current_kira_life_day_run.json"
CONVERSATION_ACTIVE_PATH = PROJECT_ROOT / "Data" / "presence" / "kira_robert_conversation_active.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_current_life_run() -> dict[str, Any]:
    if not CURRENT_LIFE_RUN_PATH.exists():
        return {}
    try:
        return json.loads(CURRENT_LIFE_RUN_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _write_chat_log(json_path: Path, monitor_path: Path, data: dict[str, Any]) -> None:
    CHAT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        f"# {data['chat_id']}",
        "",
        f"- status: {data.get('status')}",
        f"- started_at: {data.get('started_at')}",
        f"- updated_at: {data.get('updated_at')}",
        f"- linked_life_run_id: {data.get('linked_life_run', {}).get('run_id', '')}",
        f"- turns: {len(data.get('turns', []))}",
        "",
        "## Turns",
    ]
    for item in data.get("turns", [])[-40:]:
        if item.get("type") == "idle":
            lines.append(f"- {item['turn']}. [idle] {item.get('reason', '')}")
            continue
        lines.append(f"## Turn {item['turn']}")
        lines.append(f"- **Robert**: {item.get('robert', '')}")
        if item.get("command_handled"):
            lines.append(f"- command_handled: {item.get('command_handled')}")
        if item.get("kira"):
            lines.append(f"- **Kira**: {item.get('kira')}")
        if item.get("possible_truncation"):
            lines.append("- possible_truncation: true")
        if item.get("voice_output"):
            voice = item["voice_output"]
            lines.append(f"- voice: spoken={voice.get('spoken')} reason={voice.get('reason')}")
    monitor_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_conversation_active(chat_id: str, linked_life_run: dict[str, Any]) -> None:
    CONVERSATION_ACTIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "status": "active",
        "started_or_refreshed_at": _utc_now(),
        "updated_at": _utc_now(),
        "chat_id": chat_id,
        "linked_life_run": linked_life_run,
        "note": (
            "Robert/Kira live chat is active. Future 24-hour life loops should pause "
            "autonomous reading, writing, and reflection cycles until this chat closes."
        ),
    }
    CONVERSATION_ACTIVE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _clear_conversation_active(chat_id: str) -> None:
    if not CONVERSATION_ACTIVE_PATH.exists():
        return
    try:
        data = json.loads(CONVERSATION_ACTIVE_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        data = {}
    if not isinstance(data, dict) or data.get("chat_id") in {None, chat_id}:
        try:
            CONVERSATION_ACTIVE_PATH.unlink()
        except FileNotFoundError:
            pass


def _looks_unfinished_reply(text: str) -> bool:
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    if cleaned[-1] in ".?!\"')]}":
        return False
    unfinished_endings = (
        " i think",
        " i feel",
        " because",
        " and",
        " but",
        " so",
        " if",
        " when",
        " about",
        " with",
        " to",
    )
    lowered = cleaned.lower()
    return any(lowered.endswith(ending) for ending in unfinished_endings) or len(cleaned) > 500


def _idle_rhythm_from_args(idle_step_seconds: int = IDLE_STEP_SECONDS) -> IdleRhythm:
    if idle_step_seconds > 0:
        return IdleRhythm(min_seconds=idle_step_seconds, max_seconds=idle_step_seconds)
    return IdleRhythm()


def main() -> None:
    parser = argparse.ArgumentParser(description="Typed Kira chat with local voice output.")
    parser.add_argument("--no-voice", action="store_true", help="Run like chat_kira.py without speaking replies.")
    parser.add_argument("--dry-run-voice", action="store_true", help="Show voice pipeline without playing audio.")
    parser.add_argument("--config", default=str(PROJECT_ROOT / "Voice" / "kira_voice_output_config.json"))
    parser.add_argument("--idle-step-seconds", type=int, default=IDLE_STEP_SECONDS)
    args = parser.parse_args()

    voice_config = load_kira_production_voice_config(args.config)
    if args.no_voice:
        voice_config.enabled = False
    if args.dry_run_voice:
        voice_config.dry_run = True

    loop = ConversationLoop(speaker="Kira")
    idle_rhythm = _idle_rhythm_from_args(args.idle_step_seconds)
    linked_life_run = _load_current_life_run()
    chat_id = f"kira_robert_live_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    chat_json_path = CHAT_LOG_DIR / f"{chat_id}.json"
    chat_monitor_path = CHAT_LOG_DIR / f"{chat_id}.monitor.md"
    chat_log: dict[str, Any] = {
        "chat_id": chat_id,
        "status": "running",
        "started_at": _utc_now(),
        "updated_at": _utc_now(),
        "mode": "robert_kira_voice_chat",
        "linked_life_run": linked_life_run,
        "memory_policy": {
            "not_auto_promoted": True,
            "review_for_errors_before_promotion": True,
            "conversation_record_not_trusted_memory": True,
        },
        "turns": [],
    }
    _write_chat_log(chat_json_path, chat_monitor_path, chat_log)
    _write_conversation_active(chat_id, linked_life_run)
    print("Kira voice-output chat is running. Type /quit to stop.")
    print("Typed input only: microphone/listening is still disabled.")
    print("Type /help for live-session commands.")
    if voice_config.enabled:
        print("Voice output: enabled.")
    else:
        print("Voice output: disabled.")
    print(f"Chat transcript: {_relative(chat_json_path)}")
    print(f"Idle life rhythm: fuzzy {idle_rhythm.min_seconds}-{idle_rhythm.max_seconds} seconds while waiting.")

    try:
        while True:
            _write_conversation_active(chat_id, linked_life_run)
            wait_seconds = idle_rhythm.next_wait_seconds()
            try:
                raw_message, timed_out = timed_input("Robert> ", wait_seconds)
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if timed_out:
                _idle_step(loop, reason=idle_rhythm.last_reason)
                chat_log["turns"].append(
                    {
                        "turn": len(chat_log["turns"]) + 1,
                        "created_at": _utc_now(),
                        "type": "idle",
                        "reason": idle_rhythm.last_reason,
                    }
                )
                chat_log["updated_at"] = _utc_now()
                _write_chat_log(chat_json_path, chat_monitor_path, chat_log)
                continue
            user_message = (raw_message or "").strip()

            if user_message.lower() in {"/quit", "/exit"}:
                break

            if not user_message:
                continue

            turn_record: dict[str, Any] = {
                "turn": len(chat_log["turns"]) + 1,
                "created_at": _utc_now(),
                "type": "message",
                "robert": user_message,
            }

            if _try_command(loop, user_message):
                turn_record["command_handled"] = True
                chat_log["turns"].append(turn_record)
                chat_log["updated_at"] = _utc_now()
                _write_chat_log(chat_json_path, chat_monitor_path, chat_log)
                continue

            response = loop.process(user_message)
            print(f"Kira> {response}")
            voice_result = speak_text(response, config=voice_config)
            turn_record["kira"] = response
            turn_record["voice_output"] = voice_result
            if _looks_unfinished_reply(response):
                turn_record["possible_truncation"] = True
                print("[chat] Kira's answer may have been cut off. Ask her to continue if you want the rest.")
            chat_log["turns"].append(turn_record)
            chat_log["updated_at"] = _utc_now()
            _write_chat_log(chat_json_path, chat_monitor_path, chat_log)
            if not voice_result.get("spoken") and voice_result.get("reason") not in {"voice_output_disabled"}:
                print(f"[voice] {voice_result.get('reason')}")
                if voice_config.dry_run:
                    print(f"[voice dry-run] {_relative(Path(args.config))}: {voice_result.get('text', '')}")
    finally:
        _clear_conversation_active(chat_id)
        chat_log["status"] = "completed"
        chat_log["finished_at"] = _utc_now()
        chat_log["updated_at"] = chat_log["finished_at"]
        _write_chat_log(chat_json_path, chat_monitor_path, chat_log)


if __name__ == "__main__":
    main()
