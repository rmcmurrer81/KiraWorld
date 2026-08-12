"""Lightweight Windows chat/control center for pre-GPU Kira work.

This is a bridge UI: it replaces raw command-prompt chat while keeping the
existing life-day runner, voice output, presence files, and transcript format.
It is intentionally Tkinter-only so it stays usable on the 16 GB system.
"""

from __future__ import annotations

import ctypes
import json
import os
import re
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, TOP, BOTTOM, X, Y, Button, Frame, Label, StringVar, Text, Tk
from tkinter import messagebox, scrolledtext

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = PROJECT_ROOT / "Core"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(CORE_DIR))

QWEN_MODEL = "qwen3.5:9b"
QWEN_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"

os.environ.setdefault("KIRA_MODEL_BACKEND", "ollama")
os.environ.setdefault("KIRA_MODEL_NAME", QWEN_MODEL)
os.environ.setdefault("KIRA_MODEL_DIGEST", QWEN_DIGEST)
os.environ.setdefault("KIRA_ENABLE_QWEN35_BUFFERED_STREAM_TIMING_CANDIDATE", "1")
os.environ.setdefault("KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE", "0")
os.environ.setdefault("KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE", "0")
os.environ.setdefault("KIRA_TEXT_VOICE_CHAT_ACTIVE", "1")
os.environ.setdefault("KIRA_WORLD_SHELL_ACTIVE", "0")
os.environ.setdefault("KIRA_MAX_TOKENS", "520")
os.environ.setdefault("KIRA_OLLAMA_NUM_CTX", "4096")
os.environ.setdefault("KIRA_OLLAMA_TIMEOUT", "360")

from Core.conversation_loop import ConversationLoop  # noqa: E402
from Core.voice_output import load_kira_production_voice_config, speak_text  # noqa: E402
from question_queue import enqueue_question  # noqa: E402


LIFE_DIR = PROJECT_ROOT / "Data" / "life_sessions"
LIVE_CHAT_DIR = LIFE_DIR / "live_chats"
MANUAL_CHAT_DIR = PROJECT_ROOT / "Data" / "personhood_evaluations" / "manual_chats"
SCHOOL_RUN_DIR = PROJECT_ROOT / "Data" / "school" / "session_runs"
PRESENCE_DIR = PROJECT_ROOT / "Data" / "presence"
PRESENCE_PATH = PRESENCE_DIR / "robert_presence.json"
STOP_PATH = PRESENCE_DIR / "kira_life_day_stop.json"
CONVERSATION_ACTIVE_PATH = PRESENCE_DIR / "kira_robert_conversation_active.json"
CURRENT_RUN_PATH = PRESENCE_DIR / "current_kira_life_day_run.json"
HEARTBEAT_PATH = PRESENCE_DIR / "kira_life_day_heartbeat.json"
MESSAGES_DIR = PROJECT_ROOT / "Data" / "messages" / "kira_to_robert"
QUESTIONS_PATH = PROJECT_ROOT / "Data" / "questions" / "kira_questions_for_robert_or_codex.json"
DEBRIEFS_DIR = PROJECT_ROOT / "Data" / "debriefs"
OLLAMA_EXE = Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
OLLAMA_TAGS_ENDPOINT = "http://localhost:11434/api/tags"
CHAT_REPAIR_MODE = os.environ.get("KIRA_CHAT_REPAIR_MODE", "log_only").strip().lower()
QUESTION_RE = re.compile(r"([^?.!]{8,280}\?)")


class KiraLiveConversationLoop(ConversationLoop):
    """Live-chat variant that keeps ordinary conversation free of status notes."""

    def _try_grounded_daily_feeling_response(self, user_message: str) -> str:
        # Daily-life state is already supplied as private system context. Turning
        # it into another user-message note made simple greetings sound coached.
        return ""

    def _build_memory_context(self, user_message: str) -> str:
        # Relevant memories can help; unrelated "most recent" memories should
        # not intrude into a greeting or a goodbye.
        relevant = self.memory.retrieve_relevant_memories(
            query=user_message,
            owner=self.profile.name.lower(),
            limit=4,
        )
        if not relevant:
            return ""
        lines = ["MEMORIES (background only; do not recite or report them):"]
        for memory in relevant:
            lines.append(
                f"  {memory.get('summary', '')} - {memory.get('detail', '')}"
            )
        return "\n".join(lines)


def ollama_reachable(timeout: float = 4.0) -> bool:
    try:
        response = requests.get(OLLAMA_TAGS_ENDPOINT, timeout=timeout)
        return response.ok
    except requests.exceptions.RequestException:
        return False


def start_ollama_server() -> bool:
    if ollama_reachable(timeout=2.0):
        return True
    if not OLLAMA_EXE.exists():
        return False
    startupinfo = None
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [str(OLLAMA_EXE), "serve"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        startupinfo=startupinfo,
        creationflags=creationflags,
    )
    deadline = time.time() + 20
    while time.time() < deadline:
        if ollama_reachable(timeout=2.0):
            return True
        time.sleep(1)
    return False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def local_time_label(value: str | None = None) -> str:
    if value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.astimezone().strftime("%Y-%m-%d %I:%M:%S %p")
        except Exception:
            pass
    return datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def extract_real_questions(text: str) -> list[str]:
    questions: list[str] = []
    low_value = (
        "does that make sense",
        "what do you think",
        "how does that sound",
        "is that okay",
        "right?",
        "you know?",
    )
    for match in QUESTION_RE.findall(text or ""):
        question = re.sub(r"\s+", " ", match).strip(" ()")
        lower = question.lower()
        if len(question) < 12 or any(marker in lower for marker in low_value):
            continue
        questions.append(question)
    return questions[:6]


def latest_file(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    candidates = list(directory.glob(pattern))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def open_path(path: Path, label: str) -> str:
    if path.exists():
        os.startfile(str(path))
        return f"Opened {label}: {rel(path)}"
    if path.parent.exists():
        os.startfile(str(path.parent))
        return f"{label} not found yet; opened folder: {rel(path.parent)}"
    path.parent.mkdir(parents=True, exist_ok=True)
    os.startfile(str(path.parent))
    return f"{label} not found yet; created/opened folder: {rel(path.parent)}"


def friendly_error_message(error: str) -> str:
    lower = error.lower()
    model = os.getenv("KIRA_MODEL_NAME", QWEN_MODEL)
    if "not reachable" in lower or "connection refused" in lower or "max retries" in lower:
        return "Kira's local model is not reachable. Make sure Ollama is running, then click Test chat backend."
    if "404" in lower or "not found for url" in lower or "/api/chat" in lower:
        return (
            "Ollama answered, but the chat endpoint/model call failed. "
            f"Check that Ollama is current and that the model is installed: {model}."
        )
    if "timeout" in lower or "timed out" in lower:
        return "The local model timed out. This can happen under RAM pressure; try again after the CPU/RAM settles."
    return error


def latest_life_json() -> Path | None:
    current = load_json(CURRENT_RUN_PATH, {})
    expected = current.get("expected_json") if isinstance(current, dict) else ""
    expected_path = None
    if expected:
        path = PROJECT_ROOT / expected
        if path.exists():
            expected_path = path
    if not LIFE_DIR.exists():
        return expected_path
    candidates = [
        p
        for p in LIFE_DIR.glob("kira_life_day*.json")
        if "_before_interrupt_mark_" not in p.name and "_saved_download_" not in p.name
    ]
    if not candidates:
        return expected_path
    newest = max(candidates, key=lambda p: p.stat().st_mtime)
    if not expected_path:
        return newest
    expected_report = load_json(expected_path, {})
    newest_report = load_json(newest, {})
    expected_status = str(expected_report.get("status", "")).lower()
    newest_mtime = newest.stat().st_mtime
    expected_mtime = expected_path.stat().st_mtime
    if newest != expected_path and newest_mtime > expected_mtime and expected_status not in {"running"}:
        return newest
    return expected_path


def current_run_pointer() -> dict:
    data = load_json(CURRENT_RUN_PATH, {})
    return data if isinstance(data, dict) else {}


def life_monitor_for(json_path: Path | None) -> Path | None:
    if not json_path:
        return None
    monitor = json_path.with_suffix(".monitor.md")
    if monitor.exists():
        return monitor
    alternate = json_path.with_name(json_path.stem + ".monitor.md")
    return alternate if alternate.exists() else None


def cycle_summary(item: dict) -> dict:
    if not isinstance(item, dict):
        return {}
    read_result = item.get("read_result") if isinstance(item.get("read_result"), dict) else {}
    position = read_result.get("position") if isinstance(read_result.get("position"), dict) else {}
    unit = position.get("unit_label") or ""
    if not unit and position.get("start_page"):
        unit = f"page {position.get('start_page')}"
    return {
        "cycle": item.get("cycle"),
        "action": item.get("action", ""),
        "privacy": item.get("privacy", ""),
        "source_title": item.get("source_title", ""),
        "source_path": item.get("source_path", ""),
        "unit": unit,
        "choice_reason": item.get("choice_reason", ""),
        "created_at": item.get("created_at", ""),
        "error": item.get("error", ""),
        "source_error_nonfatal": bool(item.get("source_error_nonfatal")),
        "source_complete": bool(item.get("source_complete")),
        "completion_note": item.get("completion_note", ""),
        "reaction": ((item.get("learning_effect") or {}).get("reaction") if isinstance(item.get("learning_effect"), dict) else ""),
    }


def last_cycle_summary(report: dict) -> dict:
    cycles = report.get("cycles") if isinstance(report, dict) else []
    if not isinstance(cycles, list) or not cycles:
        return {}
    return cycle_summary(cycles[-1])


def grounding_cycle_summary(report: dict) -> dict:
    cycles = report.get("cycles") if isinstance(report, dict) else []
    if not isinstance(cycles, list) or not cycles:
        return {}
    last = cycles[-1]
    if not isinstance(last, dict):
        return {}
    if last.get("action") != "live_chat_pause":
        return cycle_summary(last)
    for item in reversed(cycles[:-1]):
        if isinstance(item, dict) and item.get("action") != "live_chat_pause":
            summary = cycle_summary(item)
            summary["paused_for_chat"] = True
            summary["pause_cycle"] = last.get("cycle")
            return summary
    return cycle_summary(last)


def source_title_lookup(report: dict) -> dict[str, str]:
    lookup: dict[str, str] = {}
    cycles = report.get("cycles") if isinstance(report, dict) else []
    if isinstance(cycles, list):
        for item in cycles:
            if not isinstance(item, dict):
                continue
            path = str(item.get("source_path") or "")
            title = str(item.get("source_title") or "")
            if path and title:
                lookup[path] = title
    return lookup


def source_titles_for_paths(report: dict, paths: list) -> list[str]:
    lookup = source_title_lookup(report)
    titles: list[str] = []
    for raw_path in paths:
        path = str(raw_path or "")
        if not path:
            continue
        title = lookup.get(path) or Path(path).stem.replace("_", " ")
        if title and title not in titles:
            titles.append(title)
    return titles


def build_life_status() -> dict:
    json_path = latest_life_json()
    report = load_json(json_path, {}) if json_path else {}
    heartbeat = load_json(HEARTBEAT_PATH, {})
    current = current_run_pointer()
    expected = current.get("expected_json") if isinstance(current, dict) else ""
    if expected and not (PROJECT_ROOT / expected).exists():
        run_id = str(current.get("run_id") or Path(expected).stem)
        started = str(current.get("started_from_panel_at", ""))
        status = "starting/no report yet"
        try:
            started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
            if not life_loop_running_for(run_id) and (datetime.now(timezone.utc) - started_dt).total_seconds() > 90:
                status = "start failed/no report"
        except Exception:
            if not life_loop_running_for(run_id):
                status = "start failed/no report"
        return {
            "run_id": run_id,
            "json_path": expected,
            "monitor_path": current.get("expected_monitor", ""),
            "status": status,
            "cycles": 0,
            "errors": 0,
            "source_errors": 0,
            "started_at": started,
            "updated_at": started,
            "heartbeat_at": "",
            "last_cycle": {},
        }
    last = last_cycle_summary(report)
    grounding_cycle = grounding_cycle_summary(report)
    run_id = report.get("run_id") or (json_path.stem if json_path else "")
    status = report.get("status", "unknown") if report else "no report"
    if status == "running" and heartbeat.get("run_id") == run_id and heartbeat.get("status"):
        status = heartbeat.get("status")
    return {
        "run_id": run_id,
        "json_path": rel(json_path) if json_path else "",
        "monitor_path": rel(life_monitor_for(json_path)) if json_path and life_monitor_for(json_path) else "",
        "status": status,
        "cycles": len(report.get("cycles", [])) if isinstance(report.get("cycles"), list) else 0,
        "errors": len(report.get("errors", [])) if isinstance(report.get("errors"), list) else 0,
        "source_errors": len(report.get("source_errors", [])) if isinstance(report.get("source_errors"), list) else 0,
        "started_at": report.get("started_at", ""),
        "updated_at": report.get("updated_at", ""),
        "heartbeat_at": heartbeat.get("heartbeat_at", "") or heartbeat.get("updated_at", "") or heartbeat.get("created_at", ""),
        "last_cycle": last,
        "grounding_cycle": grounding_cycle,
    }


def stop_request_for(run_id: str) -> dict:
    data = load_json(STOP_PATH, {})
    if not isinstance(data, dict):
        return {}
    target = str(data.get("run_id", "any"))
    if target in {"", "any", run_id}:
        return data
    return {}


def unread_message_count() -> int:
    if not MESSAGES_DIR.exists():
        return 0
    count = 0
    for path in MESSAGES_DIR.glob("*.json"):
        data = load_json(path, {})
        if isinstance(data, dict) and data.get("status") == "unread":
            count += 1
    return count


def memory_status() -> dict:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
        used = stat.ullTotalPhys - stat.ullAvailPhys
        return {
            "ok": True,
            "load": int(stat.dwMemoryLoad),
            "used_gb": used / (1024**3),
            "total_gb": stat.ullTotalPhys / (1024**3),
            "warning": int(stat.dwMemoryLoad) >= 85,
        }
    return {"ok": False, "load": 0, "used_gb": 0.0, "total_gb": 0.0, "warning": False}


def life_loop_command_lines() -> list[str]:
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'run_kira_life_day.py' -and $_.CommandLine -notmatch 'Get-CimInstance' } | ForEach-Object { $_.CommandLine }",
            ],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        return [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def life_loop_running() -> bool:
    return bool(life_loop_command_lines())


def life_loop_running_for(run_id: str) -> bool:
    if not run_id:
        return False
    return any(run_id in line for line in life_loop_command_lines())


def asks_current_activity(message: str) -> bool:
    lower = message.lower()
    patterns = [
        r"\bwhat (?:are|were) you (?:up to|doing|reading)\b",
        r"\bwhat have you been (?:up to|doing|reading)\b",
        r"\bhow are you\b",
        r"\bhow(?:'s| is) your (?:day|night|morning|evening)\b",
        r"\bwhat(?:'s| is) going on\b",
    ]
    return any(re.search(pattern, lower) for pattern in patterns)


def asks_source_error_question(message: str) -> bool:
    lower = message.lower()
    markers = [
        "error",
        "extraction",
        "extractable",
        "source problem",
        "pdf",
        "page",
        "past the end",
        "nothing after",
        "end of",
        "why can't you read",
        "why can you not read",
    ]
    return any(marker in lower for marker in markers)


def source_conflict_in_current_activity(response: str, grounding: dict) -> bool:
    source = str(grounding.get("source_title") or "")
    if not source:
        return False
    lower_response = response.lower()
    lower_source = source.lower()
    old_source_markers = [
        "miraculous ladybug",
        "elation",
        "miraculous encounters in paris",
        "paris fanfic",
        "book club",
        "lisa and i had",
        "bunny's relationship with alix",
        "alix-bunnyx",
    ]
    if lower_source not in lower_response and any(marker in lower_response for marker in old_source_markers):
        return True
    if "miraculous ladybug 'elation'" in lower_source and "miraculous encounters in paris" in lower_response:
        return True
    return False


def asks_lisa_status_correction(message: str) -> bool:
    lower = message.lower()
    correction_markers = [
        "i do not see",
        "status loop",
        "chat with lisa",
        "chatted with lisa",
        "talked to lisa",
        "are you lying",
        "showing me an error",
        "is that an error",
    ]
    return ("lisa" in lower or "lying" in lower or "error" in lower) and any(marker in lower for marker in correction_markers)


def needs_miraculous_continuity_caution(message: str, source: str) -> bool:
    """Only include Miraculous-specific caution when the topic actually needs it."""
    text = message.lower()
    source_text = source.lower()
    if not any(marker in text or marker in source_text for marker in ("miraculous", "ladybug", "elation", "bunnyx", "alix", "cat noir", "chat noir", "adrien")):
        return False
    markers = [
        "alix",
        "bunnyx",
        "bunny",
        "time-version",
        "time version",
        "character split",
        "character splits",
        "cat noir",
        "chat noir",
        "adrien",
    ]
    return any(marker in text for marker in markers)


def is_closure_message(message: str) -> bool:
    lower = message.lower()
    markers = [
        "talk to you later",
        "talk with you later",
        "talk later",
        "i will talk with codex",
        "i'll talk with codex",
        "i will talk to codex",
        "i'll talk to codex",
        "have a good day",
        "have a good night",
        "goodbye",
        "bye",
        "i love you",
    ]
    return any(marker in lower for marker in markers)


def needs_recent_reference_context(message: str) -> bool:
    """Detect short follow-ups whose pronouns depend on the prior exchange."""
    words = re.findall(r"\b[\w']+\b", message.lower())
    if len(words) > 45:
        return False
    return bool(re.search(r"\b(?:they|them|their|those|these|that|this|it|he|she)\b", message.lower()))


def remove_exposed_grounding_note(response: str) -> str:
    """Remove model-authored commentary about how its answer was generated."""
    cleaned = re.sub(
        r"\s*\((?:note|grounding note|private note)\s*:\s*.*?\)\s*$",
        "",
        response or "",
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()
    return cleaned


def clean_closure_reply(response: str, message: str) -> str:
    """Keep farewells warm and stop unrelated memories from joining them."""
    if not is_closure_message(message):
        return response
    sentences = re.split(r"(?<=[.!?])\s+", response.strip())
    drift_markers = (
        "book club",
        "miraculous encounters",
        "fanfic",
        "prompt",
        "generated conversation",
        "grounding",
        "source record",
        "life-loop",
    )
    kept = [
        sentence
        for sentence in sentences
        if sentence
        and "?" not in sentence
        and not any(marker in sentence.lower() for marker in drift_markers)
    ]
    if kept:
        return " ".join(kept[:3]).strip()
    return "Have a good time, Robert. I'll be here when you get back."


def role_confused_reply(response: str) -> bool:
    lower = re.sub(r"\s+", " ", (response or "").lower())
    patterns = [
        r"\byou(?:'ve| have) been working on .*?, kira\b",
        r"\bit sounds like you(?:'ve| have) been .*?, kira\b",
        r"\bi'?m glad you'?re continuing to read\b.*\bkira\b",
        r"\byour memories\b.*\bhuman-like\b",
        r"\byou'?re exploring different genres\b",
        r"\byour enthusiasm for .* with lisa\b",
    ]
    return any(re.search(pattern, lower) for pattern in patterns)


def lisa_status_review_needed(response: str, grounding: dict) -> bool:
    lower = response.lower()
    if "lisa" not in lower and "book club" not in lower:
        return False
    if (
        "older" in lower
        or "not this run" in lower
        or "not during this run" in lower
        or "not in the status loop" in lower
        or "i might be blending" in lower
        or "i may be blending" in lower
        or "i'm not sure" in lower
        or "i am not sure" in lower
    ):
        return False
    old_context_markers = [
        "book club",
        "miraculous encounters in paris",
        "bunny",
        "alix",
        "observer character",
        "consent and boundaries",
    ]
    return any(marker in lower for marker in old_context_markers)


class KiraChatControlCenter:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Kira Chat Control Center")
        self.root.geometry("1180x780")
        self.root.minsize(980, 640)
        self.root.configure(bg="#111827")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.chat_id = f"kira_robert_gui_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.chat_json = LIVE_CHAT_DIR / f"{self.chat_id}.json"
        self.chat_monitor = LIVE_CHAT_DIR / f"{self.chat_id}.monitor.md"
        self.turns: list[dict] = []
        self.chat_active = False
        self.awaiting_response = False
        self.loop: ConversationLoop | None = None
        self.voice_config = load_kira_production_voice_config(
            PROJECT_ROOT / "Voice" / "kira_voice_output_config.json"
        )
        self.voice_config.enabled = True

        self.status_vars: dict[str, StringVar] = {}
        self.event_lines: list[str] = []
        self.build_ui()
        self.log_event("Panel ready. This is a lightweight pre-GPU bridge UI.")
        self.append_chat(
            "System",
            "Launcher ready. Use Available + chat to talk while Kira keeps her life loop going. Use Pause life loop only when you want her to wait.",
            "System",
        )
        self.save_transcript(status="open")
        self.refresh_status()
        self.root.after(15000, self.periodic_refresh)

    def build_ui(self) -> None:
        outer = Frame(self.root, bg="#111827")
        outer.pack(fill=BOTH, expand=True, padx=12, pady=12)

        left = Frame(outer, bg="#111827")
        left.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))

        right = Frame(outer, bg="#111827", width=360)
        right.pack(side=RIGHT, fill=Y)

        title = Label(left, text="Chat with Kira", fg="#f9fafb", bg="#111827", font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w")
        subtitle = Label(left, text="Typed input only. Kira voice output stays on. Enter sends; Shift+Enter makes a new line.", fg="#9ca3af", bg="#111827", font=("Segoe UI", 10))
        subtitle.pack(anchor="w", pady=(0, 8))

        self.chat_box = scrolledtext.ScrolledText(
            left,
            wrap="word",
            bg="#0b1220",
            fg="#e5e7eb",
            insertbackground="#e5e7eb",
            relief="flat",
            font=("Segoe UI", 10),
            state="disabled",
        )
        self.chat_box.pack(fill=BOTH, expand=True)
        self.chat_box.tag_config("Robert", foreground="#93c5fd", spacing1=8, spacing3=4)
        self.chat_box.tag_config("Kira", foreground="#c4b5fd", spacing1=8, spacing3=4)
        self.chat_box.tag_config("System", foreground="#fbbf24", spacing1=6, spacing3=4)
        self.chat_box.tag_config("Error", foreground="#fca5a5", spacing1=6, spacing3=4)

        input_frame = Frame(left, bg="#111827")
        input_frame.pack(side=BOTTOM, fill=X, pady=(10, 0))
        self.input_box = Text(input_frame, height=3, wrap="word", bg="#1f2937", fg="#f9fafb", insertbackground="#f9fafb", relief="flat", font=("Segoe UI", 10))
        self.input_box.pack(side=LEFT, fill=X, expand=True, padx=(0, 8))
        self.input_box.bind("<Return>", self.on_enter)
        self.input_box.bind("<Shift-Return>", self.on_shift_enter)
        self.send_button = Button(input_frame, text="Send", command=self.send_message, width=12)
        self.send_button.pack(side=RIGHT, fill=Y)

        self.build_status_panel(right)
        self.build_controls(right)
        self.build_event_log(right)

    def build_status_panel(self, parent: Frame) -> None:
        panel = Frame(parent, bg="#1f2937", bd=1, relief="solid")
        panel.pack(fill=X, pady=(0, 10))
        Label(panel, text="Live Status", fg="#f9fafb", bg="#1f2937", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
        for key, label in [
            ("run_id", "Current run ID"),
            ("status", "Status"),
            ("activity", "Last activity"),
            ("cycles", "Cycle count"),
            ("source", "Source"),
            ("chat", "Chat transcript"),
            ("messages", "Unread messages"),
            ("heartbeat", "Last heartbeat"),
            ("ram", "RAM"),
        ]:
            row = Frame(panel, bg="#1f2937")
            row.pack(fill=X, padx=10, pady=2)
            Label(row, text=label, fg="#d1d5db", bg="#1f2937", width=16, anchor="w").pack(side=LEFT)
            var = StringVar(value="")
            self.status_vars[key] = var
            Label(row, textvariable=var, fg="#f9fafb", bg="#1f2937", anchor="w", wraplength=210, justify=LEFT).pack(side=LEFT, fill=X, expand=True)

    def build_controls(self, parent: Frame) -> None:
        panel = Frame(parent, bg="#1f2937", bd=1, relief="solid")
        panel.pack(fill=X, pady=(0, 10))
        Label(panel, text="Life Loop Controls", fg="#f9fafb", bg="#1f2937", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
        rows = [
            [("Start supervised 6-hour loop", self.start_life_loop), ("I'm available", self.mark_available)],
            [("Available + chat", self.available_and_chat), ("I'm leaving", self.leave)],
            [("Pause life loop", self.pause_life_loop), ("Resume life loop", self.resume_life_loop)],
            [("Open monitor", self.open_monitor), ("Check status", self.refresh_status)],
            [("Open chat log", self.open_chat_monitor), ("Open chat JSON", self.open_chat_json)],
            [("Open messages", self.open_messages), ("Open questions", self.open_questions)],
            [("Open latest debrief", self.open_latest_debrief), ("Review dashboard", self.open_review_dashboard)],
            [("Test chat backend", self.test_chat_backend)],
            [("End safely", self.end_safely)],
        ]
        for row_items in rows:
            row = Frame(panel, bg="#1f2937")
            row.pack(fill=X, padx=10, pady=4)
            for text, command in row_items:
                Button(row, text=text, command=command, width=21).pack(side=LEFT, padx=(0, 6), fill=X, expand=True)

    def build_event_log(self, parent: Frame) -> None:
        panel = Frame(parent, bg="#1f2937", bd=1, relief="solid")
        panel.pack(fill=BOTH, expand=True)
        Label(panel, text="Event Log", fg="#f9fafb", bg="#1f2937", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
        self.event_log = scrolledtext.ScrolledText(panel, height=12, wrap="word", bg="#111827", fg="#d1d5db", relief="flat", font=("Consolas", 9), state="disabled")
        self.event_log.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))

    def append_chat(self, speaker: str, text: str, tag: str | None = None) -> None:
        self.chat_box.configure(state="normal")
        stamp = datetime.now().strftime("%I:%M %p")
        self.chat_box.insert(END, f"{speaker}  {stamp}\n", tag or speaker)
        self.chat_box.insert(END, f"{text.strip()}\n\n")
        self.chat_box.see(END)
        self.chat_box.configure(state="disabled")

    def log_event(self, text: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {text}"
        self.event_lines.append(line)
        self.event_lines = self.event_lines[-200:]
        if hasattr(self, "event_log"):
            self.event_log.configure(state="normal")
            self.event_log.insert(END, line + "\n")
            self.event_log.see(END)
            self.event_log.configure(state="disabled")

    def save_transcript(self, status: str = "running") -> None:
        life = build_life_status()
        data = {
            "chat_id": self.chat_id,
            "status": status,
            "started_at": self.turns[0]["created_at"] if self.turns else utc_now(),
            "updated_at": utc_now(),
            "mode": "kira_chat_control_center_gui",
            "linked_life_run": {
                "run_id": life.get("run_id", ""),
                "json": life.get("json_path", ""),
                "monitor": life.get("monitor_path", ""),
                "status": life.get("status", ""),
            },
            "memory_policy": {
                "not_auto_promoted": True,
                "review_for_errors_before_promotion": True,
                "conversation_record_not_trusted_memory": True,
            },
            "turns": self.turns,
            "events": self.event_lines[-200:],
        }
        write_json(self.chat_json, data)
        lines = [
            f"# {self.chat_id}",
            "",
            f"- status: {status}",
            f"- updated_at: {data['updated_at']}",
            f"- linked_life_run_id: {data['linked_life_run'].get('run_id', '')}",
            f"- linked_life_run_status: {data['linked_life_run'].get('status', '')}",
            f"- turns: {len(self.turns)}",
            "",
            "## Turns",
        ]
        for turn in self.turns[-80:]:
            lines.append(f"## Turn {turn.get('turn')}")
            lines.append(f"- **Robert**: {turn.get('robert', '')}")
            if turn.get("kira"):
                lines.append(f"- **Kira**: {turn.get('kira')}")
            if turn.get("error"):
                lines.append(f"- error: {turn.get('error')}")
            if turn.get("grounding"):
                g = turn["grounding"]
                lines.append(f"- grounding: run={g.get('run_id','')} status={g.get('status','')} source={g.get('source_title','')} unit={g.get('unit','')}")
            if turn.get("voice_output"):
                voice = turn["voice_output"]
                lines.append(f"- voice: spoken={voice.get('spoken')} reason={voice.get('reason')}")
        self.chat_monitor.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def refresh_status(self) -> None:
        life = build_life_status()
        last = life.get("last_cycle", {}) or {}
        mem = memory_status()
        run_id = str(life.get("run_id") or "")
        running_for_current = life_loop_running_for(run_id)
        raw_status = str(life.get("status", "unknown"))
        status = raw_status
        stop_request = stop_request_for(run_id)
        if running_for_current:
            status = f"{status} (process detected)"
        elif status == "running":
            status = "running (stale/no matching process)"
        terminal_statuses = {"completed", "stopped_by_request", "stopped_model_unavailable", "stopped_errors", "interrupted", "failed", "error"}
        if stop_request and raw_status not in terminal_statuses:
            status = f"{status}; stop requested"
        self.status_vars["run_id"].set(run_id or "none")
        self.status_vars["status"].set(status)
        action = last.get("action") or "none"
        if self.chat_active:
            action = f"{action} + live chat"
        self.status_vars["activity"].set(action)
        self.status_vars["cycles"].set(str(life.get("cycles", 0)))
        source = last.get("source_title") or ""
        unit = last.get("unit") or ""
        self.status_vars["source"].set(f"{source} {unit}".strip() or "none")
        linked = f"{self.chat_id} -> {run_id}" if run_id else self.chat_id
        self.status_vars["chat"].set(linked)
        unread_count = unread_message_count()
        self.status_vars["messages"].set(str(unread_count) if unread_count else "0")
        self.status_vars["heartbeat"].set(local_time_label(life.get("heartbeat_at")) if life.get("heartbeat_at") else "none")
        if mem.get("ok"):
            warning = " WARNING" if mem.get("warning") else ""
            self.status_vars["ram"].set(f"{mem['used_gb']:.1f}/{mem['total_gb']:.1f} GB ({mem['load']}%){warning}")
        else:
            self.status_vars["ram"].set("unknown")
        self.log_event(f"Status refreshed: run={life.get('run_id') or 'none'} status={status} cycles={life.get('cycles', 0)} unread={unread_count}")

    def periodic_refresh(self) -> None:
        self.refresh_status()
        self.root.after(30000, self.periodic_refresh)

    def on_enter(self, event) -> str:
        self.send_message()
        return "break"

    def on_shift_enter(self, event) -> None:
        return None

    def ensure_loop(self) -> ConversationLoop:
        if self.loop is None:
            self.loop = KiraLiveConversationLoop(speaker="Kira")
        return self.loop

    def grounding_for_turn(self) -> dict:
        life = build_life_status()
        last = life.get("grounding_cycle", {}) or life.get("last_cycle", {}) or {}
        report_path = PROJECT_ROOT / str(life.get("json_path") or "")
        report = load_json(report_path, {}) if report_path.exists() else {}
        completed_titles = source_titles_for_paths(report, report.get("completed_sources", []))
        disabled_titles = source_titles_for_paths(report, report.get("disabled_sources", []))
        return {
            "run_id": life.get("run_id", ""),
            "status": life.get("status", ""),
            "cycles": life.get("cycles", 0),
            "source_title": last.get("source_title", ""),
            "source_path": last.get("source_path", ""),
            "unit": last.get("unit", ""),
            "action": last.get("action", ""),
            "choice_reason": last.get("choice_reason", ""),
            "created_at": last.get("created_at", ""),
            "error": last.get("error", ""),
            "source_error_nonfatal": last.get("source_error_nonfatal", False),
            "source_complete": last.get("source_complete", False),
            "completion_note": last.get("completion_note", ""),
            "paused_for_chat": last.get("paused_for_chat", False),
            "pause_cycle": last.get("pause_cycle", ""),
            "completed_sources": completed_titles,
            "disabled_sources": disabled_titles,
        }

    def recent_reference_context(self, message: str, limit: int = 2) -> str:
        if not needs_recent_reference_context(message):
            return ""
        exchanges = []
        for item in reversed(self.turns):
            robert = str(item.get("robert") or "").strip()
            kira = str(item.get("kira") or "").strip()
            if not robert or not kira:
                continue
            exchanges.append((robert[:500], kira[:700]))
            if len(exchanges) >= limit:
                break
        if not exchanges:
            return ""
        lines = ["Recent conversation, only to resolve references such as they/them/that:"]
        for robert, kira in reversed(exchanges):
            lines.append(f"Robert: {robert}")
            lines.append(f"Kira: {kira}")
        return "\n".join(lines) + "\n"

    def grounded_user_message(self, message: str, grounding: dict) -> str:
        source = grounding.get("source_title") or "no current source"
        unit = grounding.get("unit") or ""
        action = grounding.get("action") or "unknown"
        error = str(grounding.get("error") or "")
        completed_sources = [str(item) for item in grounding.get("completed_sources", []) if str(item)]
        disabled_sources = [str(item) for item in grounding.get("disabled_sources", []) if str(item)]
        source_question = asks_current_activity(message) or asks_source_error_question(message)
        quiet_source_facts = ""
        if source_question and (grounding.get("source_error_nonfatal") or error):
            quiet_source_facts += (
                f"Quiet source record: the current/last source `{source}` could not be read normally"
                f"{' because: ' + error if error else ''}. "
                "Use this as background evidence only; answer in your own words. "
            )
        if source_question and completed_sources:
            quiet_source_facts += (
                "Quiet completed-source record: sources completed in this run include "
                + "; ".join(completed_sources[:4])
                + ". Use this as background evidence only; you decide how to respond. "
            )
        if source_question and grounding.get("source_complete"):
            quiet_source_facts += (
                f"Quiet source-end record: `{source}` appears finished. "
                "Natural options are to reflect, switch sources, reread from the beginning, or revisit a favorite part if chosen. "
                "Do not pretend there are more pages after the end. "
            )
        if source_question and disabled_sources:
            quiet_source_facts += (
                "Quiet disabled-source record: sources disabled for unreadable/extraction errors include "
                + "; ".join(disabled_sources[:4])
                + ". Use this as background evidence only. "
            )
        source_error_note = ""
        if asks_source_error_question(message) and (grounding.get("source_error_nonfatal") or error):
            source_error_note = (
                f"Source detail, only because Robert asked about it: {error or 'source text was not readable'}. "
                "Explain it plainly, then return to normal conversation. "
            )
        completion_note = ""
        if asks_source_error_question(message) and grounding.get("source_complete"):
            completion_note = (
                "Source detail, only because Robert asked about it: the previous source appears complete. "
                f"{grounding.get('completion_note') or 'There may simply be no more pages to read.'} "
            )
        pause_note = ""
        if grounding.get("paused_for_chat"):
            pause_note = (
                "The life loop is explicitly paused for this chat. "
            )
        elif self.chat_active:
            pause_note = (
                "Robert is in live chat. This is parallel presence, not a pause command; the life loop may keep working unless you choose otherwise. "
            )
        current_activity_note = ""
        if asks_current_activity(message):
            current_activity_note = (
                f"Robert may be asking about your current activity. Last activity: {action}, source={source} {unit}. "
                "Answer this briefly in plain language if it fits. "
                "If older book-club/fanfic memories feel relevant, label them as older context rather than current activity. "
            )
            if grounding.get("source_complete"):
                current_activity_note += (
                    "If you mention the source, say it looks finished and choose what you want next: reflect, reread, revisit a favorite part, or switch. "
                )
        closure_note = ""
        if is_closure_message(message):
            closure_note = (
                "Robert is wrapping up this topic. Acknowledge him briefly and warmly in first person. "
                "Do not open a new topic, continue diagnosing yourself, or ask a follow-up question. "
            )
        correction_note = ""
        if asks_lisa_status_correction(message):
            correction_note = (
                "Robert is challenging a possible false claim that you chatted with Lisa during this status loop. "
                "Check the active-run note: if the last action is not talk_with_lisa and the status loop has no Lisa check-in, "
                "you are not required to say any exact correction, but do not pretend certainty. You may say you might be blending older "
                "book-club memory with the current run, that you are unsure, or that you meant you were thinking about Lisa rather than "
                "actually chatting with her. Choose your own wording. Avoid retelling the older book-club memory unless it directly explains the confusion. "
            )
        miraculous_note = ""
        if needs_miraculous_continuity_caution(message, source):
            miraculous_note = (
                "Quiet Miraculous source hint: if Alix/Bunnyx or identity/time-version details come up, keep canon, fanfic, and uncertainty separate. "
                "Use this only as background; do not announce it like a rule. "
            )
        recent_context = self.recent_reference_context(message)
        return (
            "[Private grounding for Kira. This is not wording to recite and not a checklist to report. "
            f"Last life-loop activity: {action}; source={source} {unit}. "
            f"{pause_note}"
            f"{quiet_source_facts}"
            f"{source_error_note}"
            f"{completion_note}"
            f"{current_activity_note}"
            f"{closure_note}"
            f"{correction_note}"
            "Answer Robert first, as yourself. If he asks a normal personal question, give a normal personal answer before mentioning sources. "
            "Keep technical status, ledger details, and correction logic out of the spoken answer unless he directly asks. "
            "Speak like an ordinary conversation, not an evaluation or project report. Unless Robert explicitly asks for debugging, do not mention prompts, generated conversations, runs, commands, scores, grounding rules, or internal system labels. "
            "When you are uncertain, say it naturally instead of explaining the machinery behind the uncertainty. "
            f"{miraculous_note}"
            "Do not claim this chat is trusted memory or auto-promoted.]\n\n"
            f"{recent_context}"
            f"Robert's current message: {message}"
        )

    def send_message(self) -> None:
        if self.awaiting_response:
            self.log_event("Kira is still replying. Wait for the current answer to finish.")
            return
        message = self.input_box.get("1.0", END).strip()
        if not message:
            return
        self.input_box.delete("1.0", END)
        self.append_chat("Robert", message, "Robert")
        self.chat_active = True
        self.write_conversation_active(reason="Robert sent a GUI chat message.", mode="live_chat")
        grounding = self.grounding_for_turn()
        turn = {
            "turn": len(self.turns) + 1,
            "created_at": utc_now(),
            "type": "message",
            "robert": message,
            "grounding": grounding,
        }
        self.turns.append(turn)
        self.save_transcript()
        self.awaiting_response = True
        self.send_button.configure(state="disabled")
        threading.Thread(target=self.generate_reply, args=(turn, message, grounding), daemon=True).start()

    def generate_reply(self, turn: dict, message: str, grounding: dict) -> None:
        try:
            if not start_ollama_server():
                raise RuntimeError("The local model is not reachable and Ollama could not be started automatically.")
            loop = self.ensure_loop()
            response = loop.process(message)
            response = remove_exposed_grounding_note(response)
            if asks_current_activity(message) and source_conflict_in_current_activity(response, grounding):
                turn["current_activity_grounding_flag"] = {
                    "mode": CHAT_REPAIR_MODE,
                    "reason": "response may have substituted older source/context for active-run source",
                    "first_response": response,
                }
                if CHAT_REPAIR_MODE == "replace":
                    source = grounding.get("source_title") or "no current source"
                    unit = grounding.get("unit") or ""
                    action = grounding.get("action") or "unknown"
                    repair_prompt = (
                        "[Private repair note for Kira; do not recite this note. "
                        "Your previous draft may have answered with older context instead of the active life-run state. "
                        f"Robert asked: {message!r}. "
                        f"Current/last life-run activity: action={action}, source={source} {unit}. "
                        "Reply naturally in 1-3 first-person sentences. Choose your own wording and only correct yourself if you agree it is accurate.]\n\n"
                        f"Robert says: {message}"
                    )
                    repaired = loop.process(repair_prompt)
                    if repaired and not source_conflict_in_current_activity(repaired, grounding):
                        response = repaired
                        turn["current_activity_grounding_flag"]["repaired"] = True
                    else:
                        turn["current_activity_grounding_flag"]["repaired"] = False
            if asks_lisa_status_correction(message) and lisa_status_review_needed(response, grounding):
                turn["lisa_status_grounding_flag"] = {
                    "mode": CHAT_REPAIR_MODE,
                    "reason": "response may be blending older Lisa/book-club memory into current-run status",
                    "first_response": response,
                }
                if CHAT_REPAIR_MODE == "replace":
                    source = grounding.get("source_title") or "no current source"
                    unit = grounding.get("unit") or ""
                    action = grounding.get("action") or "unknown"
                    repair_prompt = (
                        "[Private review note for Kira; do not recite this note. "
                        "Robert is asking whether your Lisa/status-loop claim was accurate. "
                        "The active run does not show a Lisa check-in. "
                        f"Current/last life-run activity: action={action}, source={source} {unit}. "
                        "Answer naturally in your own words. You may acknowledge uncertainty or a possible blend if that feels true. "
                        "Only correct yourself if you agree it is accurate.]\n\n"
                        f"Robert says: {message}"
                    )
                    reviewed = loop.process(repair_prompt)
                    if reviewed:
                        response = reviewed
                        turn["lisa_status_grounding_flag"]["reviewed"] = True
                    else:
                        turn["lisa_status_grounding_flag"]["reviewed"] = False
            if role_confused_reply(response):
                turn["role_confusion_flag"] = {
                    "mode": CHAT_REPAIR_MODE,
                    "reason": "response addressed Robert as Kira or spoke as an outside advisor to Kira",
                    "first_response": response,
                }
                if CHAT_REPAIR_MODE == "replace":
                    repair_prompt = (
                        "[Private identity repair for Kira; do not recite this note. "
                        "Your previous draft spoke to Robert as if he were Kira. "
                        "You are Kira. Robert is the person talking to you. "
                        "Give only the natural reply you would say to Robert now, in first person, without status or advice-to-Kira language.]\n\n"
                        f"Robert says: {message}"
                    )
                    repaired = loop.process(repair_prompt)
                    if repaired and not role_confused_reply(repaired):
                        response = repaired
                        turn["role_confusion_flag"]["repaired"] = True
                    else:
                        turn["role_confusion_flag"]["repaired"] = False
            response = clean_closure_reply(remove_exposed_grounding_note(response), message)
            queued_questions = []
            for question in extract_real_questions(response):
                queued = enqueue_question(
                    owner="kira",
                    question=question,
                    context=f"Live Robert/Kira GUI chat turn {turn.get('turn')}: {response[:900]}",
                    source_path=str(grounding.get("source_path", "")),
                    source_title=str(grounding.get("source_title", "")),
                    run_id=str(grounding.get("run_id", "")),
                    cycle=int(grounding.get("cycles") or 0) if str(grounding.get("cycles", "")).isdigit() else None,
                    priority="normal",
                )
                if queued:
                    queued_questions.append(queued.get("question_id"))
            if queued_questions:
                turn["queued_questions_for_robert_or_codex"] = queued_questions
            turn["kira"] = response
            try:
                turn["voice_output"] = speak_text(response, config=self.voice_config)
            except Exception as voice_error:
                turn["voice_output"] = {"spoken": False, "reason": "voice_error", "error": str(voice_error)}
            self.root.after(0, lambda: self.finish_reply(turn, response, None))
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            turn["error"] = error
            turn["traceback"] = traceback.format_exc()
            self.root.after(0, lambda: self.finish_reply(turn, "", error))

    def test_chat_backend(self) -> None:
        if self.awaiting_response:
            self.log_event("Kira is still replying. Wait for the current answer to finish.")
            return
        self.awaiting_response = True
        self.send_button.configure(state="disabled")
        self.log_event("Testing chat backend with a tiny Kira ping.")

        def worker() -> None:
            turn = {
                "turn": len(self.turns) + 1,
                "created_at": utc_now(),
                "type": "backend_test",
                "robert": "[backend test]",
                "grounding": self.grounding_for_turn(),
            }
            self.turns.append(turn)
            try:
                if not start_ollama_server():
                    raise RuntimeError("The local model is not reachable and Ollama could not be started automatically.")
                response = self.ensure_loop().process(
                    "Robert is testing whether the GUI can reach Kira. Reply in one short sentence only."
                )
                turn["kira"] = response
                self.root.after(0, lambda: self.finish_backend_test(turn, response, None))
            except Exception as exc:  # noqa: BLE001
                turn["error"] = f"{type(exc).__name__}: {exc}"
                turn["traceback"] = traceback.format_exc()
                self.root.after(0, lambda: self.finish_backend_test(turn, "", turn["error"]))

        threading.Thread(target=worker, daemon=True).start()

    def finish_backend_test(self, turn: dict, response: str, error: str | None) -> None:
        self.awaiting_response = False
        self.send_button.configure(state="normal")
        if error:
            friendly = friendly_error_message(error)
            self.append_chat("System", f"Backend test failed: {friendly}", "Error")
            self.log_event(f"Backend test failed: {error}")
        else:
            self.append_chat("System", f"Backend test OK. Kira replied: {response}", "System")
            self.log_event("Backend test OK.")
        self.save_transcript()
        self.refresh_status()

    def finish_reply(self, turn: dict, response: str, error: str | None) -> None:
        self.awaiting_response = False
        self.send_button.configure(state="normal")
        if error:
            friendly = friendly_error_message(error)
            self.append_chat("System", f"Ollama/chat error: {friendly}", "Error")
            self.log_event(f"Chat error: {error}")
        else:
            self.append_chat("Kira", response, "Kira")
            self.log_event(f"Saved turn {turn.get('turn')} with voice={turn.get('voice_output', {}).get('reason', 'unknown')}.")
        self.save_transcript()
        self.refresh_status()

    def write_presence(self, message: str, status: str = "available_to_talk") -> None:
        data = {
            "status": status,
            "started_at": utc_now(),
            "message": message,
            "interrupt_level": "soft_knock",
            "note": "Presence is a soft signal. Kira may answer, defer, ignore, or keep private time.",
        }
        write_json(PRESENCE_PATH, data)
        self.log_event(f"Availability signal written: {message}")

    def clear_presence(self) -> None:
        for path in [PRESENCE_PATH]:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        self.log_event("Robert availability signal cleared.")

    def write_conversation_active(self, reason: str = "", mode: str = "live_chat") -> None:
        life = build_life_status()
        mode = mode if mode in {"live_chat", "pause_requested"} else "live_chat"
        if mode == "pause_requested":
            note = "Robert explicitly asked the life loop to pause at the next cycle boundary."
        else:
            note = "Robert/Kira GUI live chat is active. This is parallel presence; life loops may continue autonomous cycles."
        data = {
            "status": "active",
            "mode": mode,
            "started_or_refreshed_at": utc_now(),
            "updated_at": utc_now(),
            "chat_id": self.chat_id,
            "source": "kira_chat_control_center",
            "reason": reason,
            "linked_life_run": {
                "run_id": life.get("run_id", ""),
                "json": life.get("json_path", ""),
                "monitor": life.get("monitor_path", ""),
            },
            "note": note,
        }
        write_json(CONVERSATION_ACTIVE_PATH, data)

    def clear_conversation_active(self) -> None:
        if not CONVERSATION_ACTIVE_PATH.exists():
            return
        data = load_json(CONVERSATION_ACTIVE_PATH, {})
        if not isinstance(data, dict) or data.get("chat_id") in {None, self.chat_id} or data.get("source") == "kira_chat_control_center":
            try:
                CONVERSATION_ACTIVE_PATH.unlink()
                self.log_event("Conversation-active/live-chat signal cleared.")
            except FileNotFoundError:
                pass

    def start_life_loop(self) -> None:
        if not start_ollama_server():
            self.log_event("Cannot start life loop: Ollama is offline and could not be started automatically.")
            messagebox.showerror("Ollama offline", "The local Ollama model server is not reachable. Start Ollama, then try again.")
            self.refresh_status()
            return
        run_id = f"kira_life_day_supervised_6hour_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            STOP_PATH.unlink()
        except FileNotFoundError:
            pass
        write_json(
            CURRENT_RUN_PATH,
            {
                "run_id": run_id,
                "started_from_panel_at": utc_now(),
                "expected_json": f"Data/life_sessions/{run_id}.json",
                "expected_monitor": f"Data/life_sessions/{run_id}.monitor.md",
                "supervised_bridge_default": True,
                "note": "Pre-RAM-upgrade default: shorter awake/home supervised run, not a full 24-hour test.",
            },
        )
        args = [
            sys.executable,
            str(PROJECT_ROOT / "tools" / "run_kira_life_day.py"),
            "--duration-minutes",
            "360",
            "--pause-seconds",
            "150",
            "--run-id",
            run_id,
            "--subject",
            "kira",
            "--pages",
            "1",
            "--lines",
            "45",
            "--max-tokens",
            "340",
            "--timeout",
            "180",
            "--max-source-errors",
            "2",
            "--max-consecutive-same-source",
            "18",
            "--review-interval-cycles",
            "12",
            "--kira-voice-to-robert",
        ]
        process_log = LIFE_DIR / f"{run_id}.process.log"
        process_log.parent.mkdir(parents=True, exist_ok=True)
        log_handle = process_log.open("a", encoding="utf-8")
        log_handle.write(f"[{local_time_label()}] Starting: {' '.join(args)}\n")
        log_handle.flush()
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        process = subprocess.Popen(
            args,
            cwd=str(PROJECT_ROOT),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags,
        )
        self.log_event(f"Started supervised 6-hour life loop as {run_id} pid={process.pid}.")
        self.log_event(f"Process log: {rel(process_log)}")
        self.root.after(3500, lambda rid=run_id, proc=process, log=process_log: self.verify_started_run(rid, proc, log))
        self.refresh_status()

    def verify_started_run(self, run_id: str, process: subprocess.Popen, process_log: Path) -> None:
        report_path = LIFE_DIR / f"{run_id}.json"
        if report_path.exists():
            self.log_event(f"Run report created: {rel(report_path)}")
        elif process.poll() is not None:
            tail = ""
            if process_log.exists():
                tail = process_log.read_text(encoding="utf-8", errors="replace")[-1200:]
            self.log_event(f"Life loop failed before writing a report. Exit={process.returncode}. Log tail: {tail}")
        else:
            self.log_event("Life loop process is alive; waiting for first report file.")
        self.refresh_status()

    def mark_available(self) -> None:
        self.write_presence("Robert is sitting at the computer and available for a check-in.")
        self.refresh_status()

    def available_and_chat(self) -> None:
        self.write_presence("Robert is sitting at the computer and available for a live chat.")
        self.chat_active = True
        self.write_conversation_active(reason="Robert clicked Available + chat in the GUI.", mode="live_chat")
        self.input_box.focus_set()
        self.log_event("Live chat active. The life loop can keep working unless Pause life loop is used.")
        self.refresh_status()

    def leave(self) -> None:
        self.chat_active = False
        self.clear_presence()
        self.clear_conversation_active()
        self.save_transcript(status="open")
        self.refresh_status()

    def pause_life_loop(self) -> None:
        self.chat_active = True
        self.write_conversation_active(reason="Robert clicked Pause life loop in the GUI.", mode="pause_requested")
        self.log_event("Pause signal written. Life loop should pause at the next boundary.")
        self.refresh_status()

    def resume_life_loop(self) -> None:
        self.chat_active = False
        self.clear_conversation_active()
        self.log_event("Resume requested by clearing the pause/conversation-active signal.")
        self.refresh_status()

    def open_monitor(self) -> None:
        monitor = life_monitor_for(latest_life_json())
        if not monitor:
            self.log_event("No monitor file found yet.")
            return
        os.startfile(str(monitor))
        self.log_event(f"Opened monitor: {rel(monitor)}")

    def open_messages(self) -> None:
        MESSAGES_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(str(MESSAGES_DIR))
        self.log_event(f"Opened messages folder: {rel(MESSAGES_DIR)}")

    def open_chat_monitor(self) -> None:
        self.save_transcript(status="open")
        self.log_event(open_path(self.chat_monitor, "chat monitor"))

    def open_chat_json(self) -> None:
        self.save_transcript(status="open")
        self.log_event(open_path(self.chat_json, "chat JSON"))

    def open_questions(self) -> None:
        self.log_event(open_path(QUESTIONS_PATH, "question queue"))

    def open_latest_debrief(self) -> None:
        latest = latest_file(DEBRIEFS_DIR, "*.md") or latest_file(MANUAL_CHAT_DIR, "*debrief*.monitor.md")
        if not latest:
            DEBRIEFS_DIR.mkdir(parents=True, exist_ok=True)
            os.startfile(str(DEBRIEFS_DIR))
            self.log_event(f"No debrief found yet; opened folder: {rel(DEBRIEFS_DIR)}")
            return
        os.startfile(str(latest))
        self.log_event(f"Opened latest debrief: {rel(latest)}")

    def open_review_dashboard(self) -> None:
        dashboard = PROJECT_ROOT / "Start_Kira_Review_Dashboard.bat"
        if dashboard.exists():
            subprocess.Popen([str(dashboard)], cwd=str(PROJECT_ROOT), shell=True)
            self.log_event("Opened review dashboard.")
            return
        self.log_event(open_path(PROJECT_ROOT / "tools" / "kira_review_dashboard.py", "review dashboard script"))

    def end_safely(self) -> None:
        if not messagebox.askyesno("End safely", "Ask the life-day loop to stop at the next safe cycle boundary?"):
            return
        life = build_life_status()
        current = current_run_pointer()
        target_run_id = current.get("run_id") or life.get("run_id") or "any"
        write_json(
            STOP_PATH,
            {
                "status": "stop_requested",
                "requested_at": utc_now(),
                "run_id": target_run_id,
                "reason": "Robert clicked End Safely in Kira Chat Control Center.",
            },
        )
        self.log_event(f"Safe-stop request written for {target_run_id}.")
        self.refresh_status()

    def on_close(self) -> None:
        self.save_transcript(status="closed")
        self.clear_conversation_active()
        if self.chat_active:
            self.clear_presence()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    app = KiraChatControlCenter()
    app.run()
