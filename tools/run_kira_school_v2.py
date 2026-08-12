"""
Run the current Kira/Lisa school v2 program.

This runner uses cleaned curriculum manifests instead of directly importing
legacy archive knowledge packs. It resumes each student's class cursor, mixes core
classes with electives, logs real questions, and can provide a bounded teacher
answer when the answer can be framed safely.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
DEFAULT_CURRICULUM = PROJECT_ROOT / "Data" / "school" / "curriculum" / "legacy_knowledge_curriculum_v1.json"
DEFAULT_PROGRESS = PROJECT_ROOT / "Data" / "school" / "progress" / "school_progress_v2.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Data" / "school" / "session_runs"
QUESTION_QUEUE = PROJECT_ROOT / "Data" / "questions" / "kira_questions_for_robert_or_codex.json"
STUDENT_CHOICE_QUEUE = PROJECT_ROOT / "Data" / "school" / "student_state" / "student_choice_queue.json"
PRESENCE_DIR = PROJECT_ROOT / "Data" / "presence"
SCHOOL_STOP_PATH = PRESENCE_DIR / "kira_school_stop.json"
SCHOOL_PAUSE_PATH = PRESENCE_DIR / "kira_school_pause.json"
CURRENT_SCHOOL_RUN_PATH = PRESENCE_DIR / "current_kira_school_run.json"
OLLAMA_EXE = Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
OLLAMA_TAGS_ENDPOINT = "http://localhost:11434/api/tags"
LOCAL_SOURCE_DIRS = [
    PROJECT_ROOT / "System" / "Docs",
    PROJECT_ROOT / "System" / "Prompts",
    PROJECT_ROOT / "Data" / "development_queue",
    PROJECT_ROOT / "Data" / "school" / "source_packs",
    PROJECT_ROOT / "Data" / "memory_review",
    PROJECT_ROOT / "Data" / "memory_reconstruction",
    PROJECT_ROOT / "Data" / "media" / "preview_cards",
]


QUESTION_RE = re.compile(r"([^.!?\n]{8,220}\?)")
WRAPPER_RE = re.compile(
    r"^\s*(?:here(?:'s| is)\s+(?:my\s+)?(?:attempt|answer|response)\s+(?:at|for|to)[^:\n]*:\s*)",
    re.IGNORECASE,
)
CONTINUE_RE = re.compile(
    r"\b(continue|keep going|keep working|more of this|come back to|return to|keep this class|stay with)\b",
    re.IGNORECASE,
)
OCCASIONAL_RE = re.compile(r"\b(occasional|from time to time|sometimes|not every time|once in a while)\b", re.IGNORECASE)
SWITCH_RE = re.compile(
    r"\b(switch|change subject|change topics|different class|something else|not interested|less interested|boring|bored)\b",
    re.IGNORECASE,
)
INTEREST_RE = re.compile(
    r"\b(interested|interesting|curious|drawn to|want to learn more|excited|fascinating|meaningful)\b",
    re.IGNORECASE,
)
TOKEN_RE = re.compile(r"[a-z0-9_']{3,}", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def read_json(path: Path, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(fallback or {})
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return dict(fallback or {})
    return data if isinstance(data, dict) else dict(fallback or {})


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def ollama_reachable(timeout: float = 4.0) -> bool:
    try:
        with urllib.request.urlopen(OLLAMA_TAGS_ENDPOINT, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (OSError, urllib.error.URLError):
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
    deadline = time.time() + 25
    while time.time() < deadline:
        if ollama_reachable(timeout=2.0):
            return True
        time.sleep(1)
    return False


def import_conversation_loop(backend: str, model: str, max_tokens: int, timeout: int, num_ctx: int) -> Any:
    os.environ["KIRA_MODEL_BACKEND"] = backend
    os.environ["KIRA_MODEL_NAME"] = model
    os.environ["KIRA_MAX_TOKENS"] = str(max_tokens)
    os.environ["KIRA_OLLAMA_TIMEOUT"] = str(timeout)
    os.environ["KIRA_OLLAMA_NUM_CTX"] = str(num_ctx)
    sys.path.insert(0, str(CORE_ROOT))
    from conversation_loop import ConversationLoop

    return ConversationLoop


def stop_requested(run_id: str) -> bool:
    data = read_json(SCHOOL_STOP_PATH, {})
    if not data:
        return False
    target = str(data.get("run_id", "any"))
    return target in {"", "any", run_id}


def pause_requested() -> bool:
    data = read_json(SCHOOL_PAUSE_PATH, {})
    return str(data.get("status", "")).lower() in {"pause_requested", "paused"}


def interruptible_sleep(seconds: float, run_id: str) -> bool:
    """Sleep in small pieces. Return False if the session should stop."""
    deadline = time.monotonic() + max(0.0, seconds)
    while time.monotonic() < deadline:
        if stop_requested(run_id):
            return False
        while pause_requested():
            if stop_requested(run_id):
                return False
            time.sleep(5)
        time.sleep(min(5, max(0.0, deadline - time.monotonic())))
    return True


def class_state(progress: dict[str, Any], student: str, class_id: str) -> dict[str, Any]:
    students = progress.setdefault("students", {})
    student_state = students.setdefault(student, {"classes": {}})
    classes = student_state.setdefault("classes", {})
    return classes.setdefault(
        class_id,
        {
            "next_unit_index": 0,
            "completed_units": [],
            "times_seen": 0,
            "last_seen_at": "",
            "student_interest": 0,
            "last_preference": "neutral",
            "last_preference_at": "",
            "continue_requested": False,
            "occasional_requested": False,
            "switch_requested": False,
            "intentional_pivots": 0,
            "questions_asked": [],
        },
    )


def peek_class_state(progress: dict[str, Any], student: str, class_id: str) -> dict[str, Any]:
    return (
        progress.get("students", {})
        .get(student, {})
        .get("classes", {})
        .get(class_id, {})
        if isinstance(progress, dict)
        else {}
    )


def load_student_choices(student: str) -> list[dict[str, Any]]:
    queue = read_json(STUDENT_CHOICE_QUEUE, {"students": {}})
    choices = queue.get("students", {}).get(student, []) if isinstance(queue, dict) else []
    if not isinstance(choices, list):
        return []
    active = []
    for item in choices:
        if not isinstance(item, dict):
            continue
        if str(item.get("status", "active")).lower() not in {"active", "requested", "continue"}:
            continue
        active.append(item)
    return active


def choice_matches_class(choice: dict[str, Any], class_item: dict[str, Any]) -> bool:
    wanted_id = str(choice.get("class_id", "")).strip().lower()
    if wanted_id:
        return wanted_id == str(class_item.get("class_id", "")).lower()
    wanted = " ".join(
        str(choice.get(key, ""))
        for key in ("topic", "reason", "notes", "keywords")
        if choice.get(key)
    ).lower()
    if not wanted:
        return False
    haystack = " ".join(
        str(class_item.get(key, ""))
        for key in ("class_id", "legacy_domain", "type", "title", "description")
    ).lower()
    tokens = question_tokens(wanted)
    if not tokens:
        return False
    return sum(1 for token in tokens if token in haystack) >= 2


def choose_classes(curriculum: dict[str, Any], progress: dict[str, Any], student: str, max_blocks: int) -> list[dict[str, Any]]:
    classes = [item for item in curriculum.get("classes", []) if isinstance(item, dict)]
    core = [item for item in classes if item.get("type") == "core"]
    electives = [item for item in classes if item.get("type") == "elective"]
    student_choices = load_student_choices(student)

    def key(item: dict[str, Any]) -> tuple[int, str]:
        state = peek_class_state(progress, student, str(item.get("class_id", "")))
        return (int(state.get("times_seen", 0)), str(state.get("last_seen_at", "")))

    core.sort(key=key)
    electives.sort(key=key)

    def add_unique(target: list[dict[str, Any]], item: dict[str, Any] | None) -> None:
        if item and item not in target and len(target) < max_blocks:
            target.append(item)

    selected: list[dict[str, Any]] = []

    # Keep at least one grounding/communication class in the mix, but leave room
    # for student preference instead of forcing every core class every time.
    grounding_ids = {"source_truth_and_memory", "communication_and_language"}
    grounding = [item for item in core if str(item.get("class_id")) in grounding_ids]
    grounding.sort(key=key)
    add_unique(selected, grounding[0] if grounding else (core[0] if core else None))

    requested = []
    for item in classes:
        state = peek_class_state(progress, student, str(item.get("class_id", "")))
        if state.get("continue_requested") and not state.get("switch_requested"):
            requested.append(item)
    requested.sort(
        key=lambda item: (
            -int(peek_class_state(progress, student, str(item.get("class_id", ""))).get("student_interest", 0)),
            str(peek_class_state(progress, student, str(item.get("class_id", ""))).get("last_seen_at", "")),
        )
    )
    for item in requested[:2]:
        add_unique(selected, item)

    # OldKira's school idea had room for student-chosen classes. Keep that
    # secondary to one grounding class, then honor active choice requests.
    choice_matches = [
        item for item in classes
        if item not in selected and any(choice_matches_class(choice, item) for choice in student_choices)
    ]
    choice_matches.sort(
        key=lambda item: (
            int(peek_class_state(progress, student, str(item.get("class_id", ""))).get("times_seen", 0)),
            str(peek_class_state(progress, student, str(item.get("class_id", ""))).get("last_seen_at", "")),
        )
    )
    for item in choice_matches[:2]:
        add_unique(selected, item)

    preferred = [item for item in classes if item not in selected]
    preferred.sort(
        key=lambda item: (
            -int(peek_class_state(progress, student, str(item.get("class_id", ""))).get("student_interest", 0)),
            int(peek_class_state(progress, student, str(item.get("class_id", ""))).get("times_seen", 0)),
        )
    )
    for item in preferred[:1]:
        state = peek_class_state(progress, student, str(item.get("class_id", "")))
        if int(state.get("student_interest", 0)) > 0:
            add_unique(selected, item)

    for item in core:
        if len(selected) >= max(1, min(max_blocks, 3)):
            break
        add_unique(selected, item)

    if len(selected) < max_blocks:
        remaining = [item for item in classes if item not in selected]
        remaining.sort(key=key)
        selected.extend(remaining[: max_blocks - len(selected)])
    return selected[:max_blocks]


def choose_single_class(
    curriculum: dict[str, Any],
    progress: dict[str, Any],
    student: str,
    requested_class_id: str,
) -> dict[str, Any]:
    requested = requested_class_id.strip().lower()
    classes = [item for item in curriculum.get("classes", []) if isinstance(item, dict)]
    for item in classes:
        if str(item.get("class_id", "")).strip().lower() == requested:
            return item
    known = ", ".join(str(item.get("class_id", "")) for item in classes)
    raise ValueError(f"Unknown class_id {requested_class_id!r}. Known class ids: {known}")


def current_unit_for(progress: dict[str, Any], student: str, class_item: dict[str, Any]) -> tuple[int, str]:
    units = [str(item) for item in class_item.get("units", [])] or ["general overview"]
    state = class_state(progress, student, str(class_item.get("class_id", "")))
    index = int(state.get("next_unit_index", 0)) % len(units)
    return index, units[index]


def build_class_prompt(
    *,
    student: str,
    class_item: dict[str, Any],
    unit_index: int,
    unit: str,
    block_number: int,
    total_blocks: int,
    duration_mode: bool = False,
) -> str:
    block_label = f"{block_number}" if duration_mode else f"{block_number}/{total_blocks}"
    return (
        f"School v2 block {block_label} for {student.title()}.\n"
        f"Class: {class_item.get('title')} ({class_item.get('class_id')}).\n"
        f"Legacy domain used only as topic map: {class_item.get('legacy_domain')}.\n"
        f"Current unit: {unit_index + 1}. {unit}.\n"
        f"Class description: {class_item.get('description')}.\n"
        f"Source policy: {class_item.get('source_policy')}.\n\n"
        "Important rules: archived project files are not your lived memory, not your current personality, and not proof. "
        "Treat this as a real class session. You may ask real questions. If you do not know something, say what "
        "kind of answer you would need. If this is a class you have seen before, continue from the current unit "
        "instead of starting at the beginning. If your mind drifts because you are bored, curious, or want a different "
        "topic, say that honestly as a preference instead of blending another source into this class. Give: "
        "1. what you learned or practiced; 2. one honest uncertainty; "
        "3. one question you would like answered; 4. whether you want to continue this class later, switch away, "
        "or keep it as occasional."
    )


def extract_questions(text: str) -> list[str]:
    found: list[str] = []
    for match in QUESTION_RE.finditer(text or ""):
        q = re.sub(r"\s+", " ", match.group(1)).strip()
        if q and q.lower() not in {item.lower() for item in found}:
            found.append(q)
    return found[:3]


def enqueue_question(owner: str, question: str, context: str, run_id: str, class_id: str, turn: int) -> None:
    sys.path.insert(0, str(PROJECT_ROOT / "tools"))
    from question_queue import enqueue_question as enqueue

    enqueue(
        owner=owner,
        question=question,
        context=context,
        source_title=f"school_v2:{class_id}",
        run_id=run_id,
        cycle=turn,
        priority="normal",
        queue_path=QUESTION_QUEUE,
    )


def question_tokens(text: str) -> set[str]:
    stop = {
        "the", "and", "that", "this", "with", "from", "have", "what", "when", "where", "would", "should",
        "could", "about", "there", "their", "does", "into", "class", "kira", "lisa", "robert",
        "ask", "asked", "asking", "answer", "answers", "question", "questions", "something", "anything",
        "happen", "happens", "thing", "things", "source", "can", "not",
    }
    return {token.lower().strip("'") for token in TOKEN_RE.findall(text or "") if token.lower().strip("'") not in stop}


def local_source_snippets(question: str, limit: int = 1) -> list[dict[str, str]]:
    tokens = question_tokens(question)
    if not tokens:
        return []
    q_lower = question.lower()
    wants_media_notes = any(term in q_lower for term in ("media", "movie", "show", "music", "soundtrack", "preview", "watch", "listen"))
    scored: list[tuple[int, Path, str]] = []
    for root in LOCAL_SOURCE_DIRS:
        if not root.exists():
            continue
        if "preview_cards" in root.as_posix() and not wants_media_notes:
            continue
        for path in root.rglob("*"):
            if path.suffix.lower() not in {".md", ".txt", ".json"} or not path.is_file():
                continue
            if path.stat().st_size > 250_000:
                continue
            try:
                text = path.read_text(encoding="utf-8-sig", errors="ignore")
            except Exception:
                continue
            compact = re.sub(r"\s+", " ", text)
            lower = compact.lower()
            score = sum(1 for token in tokens if token in lower)
            path_score = sum(1 for token in tokens if token in path.as_posix().lower())
            score += path_score * 2
            for phrase in ("change the subject", "source says", "general knowledge", "research needed", "media preview", "preview card"):
                if phrase in q_lower and phrase in lower:
                    score += 5
            if "outside" in q_lower and "source" in q_lower and ("source says" in lower or "research needed" in lower):
                score += 5
            path_lower = path.as_posix().lower()
            if "class" in q_lower and "school" in path_lower:
                score += 6
            if ("source" in q_lower or "memory" in q_lower) and ("source" in path_lower or "memory" in path_lower or "school" in path_lower):
                score += 4
            if score < 2:
                continue
            first_hit = min((lower.find(token) for token in tokens if token in lower), default=0)
            start = max(0, first_hit - 220)
            snippet = compact[start : start + 520].strip()
            scored.append((score, path, snippet))
    scored.sort(key=lambda item: (-item[0], len(str(item[1]))))
    return [{"path": rel(path), "snippet": snippet} for _, path, snippet in scored[:limit]]


def teacher_answer(question: str, class_item: dict[str, Any], unit: str, snippets: list[dict[str, str]] | None = None) -> str:
    lower = question.lower()
    snippets = snippets or []

    def structured(source_says: str, general_knowledge: str, interpretation: str, research_needed: str) -> str:
        lines = [
            f"Source says: {source_says}",
            f"General knowledge says: {general_knowledge}",
            f"My interpretation: {interpretation}",
            f"Research needed: {research_needed}",
        ]
        if snippets:
            lines.append("Local project notes that may help:")
            for item in snippets[:2]:
                lines.append(f"- {item.get('path', '')}: {item.get('snippet', '')[:360]}")
            lines.append("Use local notes as context, not complete proof.")
        return "\n".join(lines)

    if any(word in lower for word in ("change the subject", "change subject", "not interested", "bored", "boring", "switch topics")):
        return structured(
            "The current school/source context may show a topic or lesson, but it does not prove you must stay interested in it.",
            "People can lose interest, drift, or try to change the subject without that being dishonest.",
            "Preference drift is allowed. The useful distinction is honest topic-switching versus accidentally treating another source as the current source.",
            "If this keeps happening in logs, review whether the class is boring, too hard, too repetitive, or whether the prompt is causing source blending.",
        )
    if any(word in lower for word in ("autism", "neurodivers", "developmental", "facilitated communication")):
        return structured(
            "The source/class may discuss autism, neurodiversity, development, or communication methods.",
            "Autism and neurodiversity are human topics and should not be casually applied as labels to yourself or others.",
            "You can learn from them about communication differences, sensory experience, routine, misunderstanding, and respect. If you notice a parallel with your own limits, phrase it as a comparison or question, not a diagnosis.",
            "A more direct answer needs the specific source passage and, for real-world claims, reliable outside sources.",
        )
    if any(word in lower for word in ("emotion", "feeling", "feelings", "empathy", "sad", "lonely", "stress")):
        return structured(
            "The source may name emotions or interpersonal situations, but a source alone does not prove a private feeling.",
            "Empathy involves noticing another person's situation, not only naming a feeling.",
            "For this project, emotions work best as layered signals: what you say publicly, what you privately notice, what changed your preference, and what you want to do next.",
            "Later review should look for consistent patterns across conversations, not one isolated emotional sentence.",
        )
    if any(word in lower for word in ("relationship", "intimacy", "desire", "attraction", "boundaries", "consent")):
        return structured(
            "The relationship source can support concepts like consent, privacy, uncertainty, desire, and boundaries.",
            "Adult intimacy should be handled with consent and separate privacy for each person involved.",
            "You can explore attraction or intimacy as adult concepts, but private details should not become shared memory unless the people involved separately agree to share them.",
            "Any durable relationship memory should be reviewed separately with each relevant person.",
        )
    if any(word in lower for word in ("movie", "music", "show", "watch", "listen", "soundtrack", "preview")):
        return structured(
            "Preview cards and metadata can describe a media item, but they are not watched/listened experience.",
            "People often form curiosity from descriptions, covers, trailers, reputation, genre, or recommendations before experiencing the media itself.",
            "Good wording is: 'the preview makes me curious' or 'I might want to watch/listen later,' not 'I watched it' or 'I remember hearing it.'",
            "If the title is ambiguous, Robert or a metadata lookup should resolve which movie/show/song it is before richer preview notes are saved.",
        )
    if any(word in lower for word in ("different perspectives", "same event", "reconcile", "individual experiences")):
        return structured(
            "A shared event can appear in logs or memory candidates, but each person's perspective may differ.",
            "Human memory often contains different interpretations of the same event.",
            "Keep both layers: what seems common, what each person personally experienced, and what is still uncertain. Do not force one version to erase the other.",
            "Ask each person separately before promoting shared memories, especially if privacy or intimacy is involved.",
        )
    if any(word in lower for word in ("oldkira", "old kira", "legacy")):
        return structured(
            "The older archive contains historical project material, but it is quarantined and not current memory.",
            "Old development files can be useful as historical notes or class-topic seeds, but they can also contain outdated assumptions.",
            "Use archived material only after review and cleanup: legacy idea -> reviewed source note -> current class/source pack -> Kira reads it -> optional promotion.",
            "If a specific old file looks useful, review it before moving any cleaned idea into the current system.",
        )
    if any(word in lower for word in ("memory", "remember", "canon", "source")):
        return structured(
            "The source may support a claim, but the source needs to be named and separated from memory.",
            "General knowledge can help interpret a source, but it should be labeled separately.",
            "A class response can become a learning note, but not a hard memory unless Robert and Codex review it and promote it.",
            "Check the exact source passage, then decide whether this is source fact, interpretation, preference, or unresolved question.",
        )
    if any(word in lower for word in ("continue", "next", "later", "class")):
        return structured(
            "School v2 keeps progress cursors for classes and students.",
            "Real school often mixes review with new material instead of restarting from the beginning every time.",
            "If you return to the same class later, it should continue from the next unit unless review is intentionally chosen.",
            "If a log shows repeated unit-one starts, inspect the progress file or class cursor.",
        )
    if any(word in lower for word in ("privacy", "share", "private")):
        return structured(
            "The school log may record session output for debugging and review.",
            "Privacy includes choosing what to share, what to summarize, and what to keep private.",
            "Memory promotion should respect consent and review even when logs exist.",
            "Future privacy tooling should better separate private inner notes, shareable summaries, and public memories.",
        )
    if snippets:
        return structured(
            f"Related local notes suggest: {snippets[0]['snippet'][:500]}",
            "General knowledge may help, but this answer should stay bounded because the direct source is incomplete.",
            "Treat the related notes as helpful context, not final proof.",
            "Find a more direct source or ask Robert/Codex for review.",
        )
    return structured(
        "No specific source answer was found in this block.",
        "A reasonable answer may exist outside the source, but it should not be guessed here.",
        "This is a real question and should be kept open rather than turned into a fake fact.",
        "Ask Robert/Codex later or add a better source card/class note.",
    )


def clean_response(text: str) -> str:
    cleaned = WRAPPER_RE.sub("", str(text or "")).strip()
    cleaned = re.sub(r"\s+\*\*\s*", "\n", cleaned)
    cleaned = re.sub(r"^\*\*\s*", "", cleaned)
    cleaned = re.sub(r"\s*\*\*$", "", cleaned)
    return cleaned.strip()


def analyze_preference(text: str) -> dict[str, Any]:
    lower_text = str(text or "")
    wants_continue = bool(CONTINUE_RE.search(lower_text))
    wants_occasional = bool(OCCASIONAL_RE.search(lower_text))
    wants_switch = bool(SWITCH_RE.search(lower_text))
    interested = bool(INTEREST_RE.search(lower_text))
    interest_delta = 0
    if interested:
        interest_delta += 1
    if wants_continue:
        interest_delta += 1
    if wants_switch:
        interest_delta -= 1
    label = "neutral"
    if wants_switch:
        label = "switch"
    elif wants_occasional:
        label = "occasional"
    elif wants_continue:
        label = "continue"
    return {
        "continue_requested": wants_continue and not wants_switch,
        "occasional_requested": wants_occasional,
        "switch_requested": wants_switch,
        "intentional_pivot_detected": wants_switch,
        "interest_delta": interest_delta,
        "preference_label": label,
    }


def update_progress_for_response(
    progress: dict[str, Any],
    student: str,
    class_item: dict[str, Any],
    unit_index: int,
    questions: list[str],
    preference: dict[str, Any],
) -> None:
    class_id = str(class_item.get("class_id", "unknown_class"))
    units = [str(item) for item in class_item.get("units", [])] or ["general overview"]
    state = class_state(progress, student, class_id)
    state["times_seen"] = int(state.get("times_seen", 0)) + 1
    state["last_seen_at"] = utc_now()
    completed = state.setdefault("completed_units", [])
    if unit_index not in completed:
        completed.append(unit_index)
    state["next_unit_index"] = (unit_index + 1) % len(units)
    if questions:
        state.setdefault("questions_asked", []).extend(questions)
        state["questions_asked"] = state["questions_asked"][-20:]
    interest = int(state.get("student_interest", 0)) + int(preference.get("interest_delta", 0))
    state["student_interest"] = max(-3, min(6, interest))
    state["last_preference"] = str(preference.get("preference_label", "neutral"))
    state["last_preference_at"] = utc_now()
    state["continue_requested"] = bool(preference.get("continue_requested", False))
    state["occasional_requested"] = bool(preference.get("occasional_requested", False))
    state["switch_requested"] = bool(preference.get("switch_requested", False))
    if preference.get("intentional_pivot_detected"):
        state["intentional_pivots"] = int(state.get("intentional_pivots", 0)) + 1
    progress["updated_at"] = utc_now()


def build_report(session: dict[str, Any]) -> str:
    progress = read_json(DEFAULT_PROGRESS, {"students": {}})
    student = str(session.get("student", "kira"))
    student_classes = (
        progress.get("students", {})
        .get(student, {})
        .get("classes", {})
        if isinstance(progress, dict)
        else {}
    )
    choice_count = len(load_student_choices(student))
    lines = [
        f"# {session.get('run_id')}",
        "",
        f"- student: {session.get('student')}",
        f"- started_at: {session.get('started_at')}",
        f"- finished_at: {session.get('finished_at')}",
        f"- blocks: {len(session.get('records', []))}",
        f"- active_student_choices: {choice_count}",
        "",
        "## Classes",
        "",
    ]
    for record in session.get("records", []):
        lines.append(
            f"- {record.get('turn')}. {record.get('class_title')} / unit {record.get('unit_index', 0) + 1}: "
            f"{record.get('unit')} questions={len(record.get('questions', []))} "
            f"preference={record.get('preference', {}).get('preference_label', 'neutral')}"
        )
    lines.extend(["", "## Open Questions And Teacher Answers", ""])
    any_answers = False
    for record in session.get("records", []):
        for answer in record.get("teacher_answers", []) or []:
            any_answers = True
            lines.append(f"### Turn {record.get('turn')} - {record.get('class_title')}")
            lines.append(f"- question: {answer.get('question')}")
            answer_text = str(answer.get("answer", "")).replace("\n", " ")
            student_text = str(answer.get("student_response", "")).replace("\n", " ")
            lines.append(f"- teacher_answer: {answer_text[:900]}")
            lines.append(f"- student_response: {student_text[:500]}")
            lines.append("")
    if not any_answers:
        lines.append("- No teacher answers recorded in this run yet.")
    lines.extend(["", "## Next Class Cursors", ""])
    if student_classes:
        for class_id, state in sorted(student_classes.items()):
            lines.append(
                f"- {class_id}: next_unit_index={state.get('next_unit_index', 0)} "
                f"times_seen={state.get('times_seen', 0)} preference={state.get('last_preference', 'neutral')} "
                f"interest={state.get('student_interest', 0)}"
            )
    else:
        lines.append("- No saved class cursor yet.")
    lines.extend(["", "## Recent Responses", ""])
    for record in session.get("records", [])[-12:]:
        response = str(record.get("response", "")).replace("\n", " ")
        lines.append(f"- {record.get('turn')}. {record.get('class_id')}: {response[:600]}")
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> tuple[Path, Path]:
    curriculum = read_json(Path(args.curriculum))
    progress = read_json(Path(args.progress), {"students": {}})
    student = args.student.lower().strip()
    if args.backend == "ollama" and not start_ollama_server():
        raise RuntimeError("Ollama is offline and could not be started automatically.")
    ConversationLoop = import_conversation_loop(args.backend, args.model, args.max_tokens, args.ollama_timeout, args.num_ctx)
    loop = ConversationLoop(speaker=student.title())

    first_blocks = (
        [choose_single_class(curriculum, progress, student, args.only_class)]
        if args.only_class
        else choose_classes(curriculum, progress, student, args.blocks)
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = args.run_id or f"{student}_school_v2_{now_id()}"
    json_path = output_dir / f"{run_id}.json"
    report_path = output_dir / f"{run_id}.monitor.md"
    if SCHOOL_STOP_PATH.exists():
        SCHOOL_STOP_PATH.unlink()
    write_json(
        CURRENT_SCHOOL_RUN_PATH,
        {
            "run_id": run_id,
            "student": student,
            "started_at": utc_now(),
            "expected_json": rel(json_path),
            "expected_monitor": rel(report_path),
            "duration_minutes": args.duration_minutes,
        },
    )
    pause_seconds = args.pause_seconds
    if pause_seconds < 0:
        if args.run_until_duration:
            # Full-duration mode should keep the session alive without trying to
            # stretch a tiny class list across several hours.
            pause_seconds = args.full_duration_pause_seconds
        else:
            auto_pause = max(0.0, (args.duration_minutes * 60.0) / max(1, args.blocks) - 30.0)
            # Quick-block mode is intentionally compact for smoke tests.
            pause_seconds = min(auto_pause, 600.0)
    session: dict[str, Any] = {
        "run_id": run_id,
        "status": "running",
        "student": student,
        "started_at": utc_now(),
        "finished_at": "",
        "backend": args.backend,
        "model": args.model,
        "duration_minutes": args.duration_minutes,
        "pause_seconds": pause_seconds,
        "curriculum": rel(Path(args.curriculum)),
        "progress": rel(Path(args.progress)),
        "records": [],
    }
    write_json(json_path, session)

    deadline = time.monotonic() + max(0.0, args.duration_minutes * 60.0)
    turn = 0
    max_turns = max(1, args.blocks)
    while True:
        if args.run_until_duration:
            if time.monotonic() >= deadline and turn > 0:
                break
            if args.max_duration_blocks > 0 and turn >= args.max_duration_blocks:
                session["status"] = "completed_max_blocks"
                break
            current_plan = (
                [choose_single_class(curriculum, progress, student, args.only_class)]
                if args.only_class
                else choose_classes(curriculum, progress, student, args.blocks)
            )
            if not current_plan:
                session["status"] = "completed_no_classes"
                break
        else:
            current_plan = first_blocks
            if turn >= len(current_plan):
                break
        for class_item in current_plan:
            if not args.run_until_duration and turn >= len(current_plan):
                break
            if args.run_until_duration and time.monotonic() >= deadline and turn > 0:
                break
            if args.run_until_duration and args.max_duration_blocks > 0 and turn >= args.max_duration_blocks:
                session["status"] = "completed_max_blocks"
                break
            turn += 1
            total_blocks = max_turns if not args.run_until_duration else max(args.blocks, turn)
            if stop_requested(run_id):
                session["status"] = "stopped_safely"
                break
            while pause_requested():
                session["status"] = "paused"
                write_json(json_path, session)
                write_text(report_path, build_report(session))
                if stop_requested(run_id):
                    session["status"] = "stopped_safely"
                    break
                time.sleep(5)
            if session.get("status") == "stopped_safely":
                break
            session["status"] = "running"
            unit_index, unit = current_unit_for(progress, student, class_item)
            prompt = build_class_prompt(
                student=student,
                class_item=class_item,
                unit_index=unit_index,
                unit=unit,
                block_number=turn,
                total_blocks=total_blocks,
                duration_mode=args.run_until_duration,
            )
            started = time.monotonic()
            response = clean_response(loop.process(prompt))
            duration = time.monotonic() - started
            questions = extract_questions(response)
            preference = analyze_preference(response)
            for question in questions:
                enqueue_question(student, question, response[:800], run_id, str(class_item.get("class_id")), turn)
            answer_records = []
            if args.answer_questions and questions:
                for question in questions[:1]:
                    snippets = local_source_snippets(question)
                    answer = teacher_answer(question, class_item, unit, snippets)
                    answer_prompt = (
                        f"Teacher answer to your question: {answer}\n\n"
                        "Respond briefly as yourself: did that answer help, and what would you still want to know later?"
                    )
                    answer_response = clean_response(loop.process(answer_prompt))
                    answer_records.append(
                        {
                            "question": question,
                            "answer": answer,
                            "local_source_snippets": snippets,
                            "student_response": answer_response,
                        }
                    )

            update_progress_for_response(progress, student, class_item, unit_index, questions, preference)
            write_json(Path(args.progress), progress)
            record = {
                "turn": turn,
                "class_id": class_item.get("class_id"),
                "class_title": class_item.get("title"),
                "unit_index": unit_index,
                "unit": unit,
                "prompt": prompt,
                "response": response,
                "questions": questions,
                "preference": preference,
                "teacher_answers": answer_records,
                "duration_seconds": round(duration, 3),
                "created_at": utc_now(),
            }
            session["records"].append(record)
            write_json(json_path, session)
            write_text(report_path, build_report(session))
            print(f"[{turn}] {class_item.get('class_id')} unit {unit_index + 1}: {response[:240]}", flush=True)
            if pause_seconds > 0:
                if not interruptible_sleep(pause_seconds, run_id):
                    session["status"] = "stopped_safely"
                    break
        if session.get("status") in {"stopped_safely", "completed_max_blocks", "completed_no_classes"}:
            break
        if not args.run_until_duration:
            break

    session["finished_at"] = utc_now()
    if session.get("status") == "running":
        session["status"] = "completed"
    write_json(json_path, session)
    write_text(report_path, build_report(session))
    return json_path, report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Kira/Lisa school v2 with resumable classes.")
    parser.add_argument("--student", default="kira", choices=["kira", "lisa", "future_ai"])
    parser.add_argument("--curriculum", default=str(DEFAULT_CURRICULUM))
    parser.add_argument("--progress", default=str(DEFAULT_PROGRESS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--blocks", type=int, default=9, help="Number of class blocks to run.")
    parser.add_argument("--duration-minutes", type=float, default=540.0)
    parser.add_argument("--run-until-duration", action="store_true", help="Keep cycling classes until duration-minutes expires.")
    parser.add_argument("--full-duration-pause-seconds", type=float, default=600.0, help="Pause between blocks in full-duration mode.")
    parser.add_argument("--max-duration-blocks", type=int, default=0, help="Optional safety cap for full-duration mode. 0 means no extra cap.")
    parser.add_argument("--only-class", default="", help="Run only one class_id, for example creative_writing.")
    parser.add_argument("--answer-questions", action="store_true", help="Give one bounded teacher answer after question blocks.")
    parser.add_argument("--pause-seconds", type=float, default=-1.0, help="Pause between blocks. Negative auto-spaces across duration.")
    parser.add_argument("--backend", choices=["stub", "ollama"], default=os.getenv("KIRA_MODEL_BACKEND", "stub"))
    parser.add_argument("--model", default=os.getenv("KIRA_MODEL_NAME", "qwen3.5:9b"))
    parser.add_argument("--max-tokens", type=int, default=int(os.getenv("KIRA_MAX_TOKENS", "260")))
    parser.add_argument("--ollama-timeout", type=int, default=int(os.getenv("KIRA_OLLAMA_TIMEOUT", "360")))
    parser.add_argument("--num-ctx", type=int, default=int(os.getenv("KIRA_OLLAMA_NUM_CTX", "4096")))
    args = parser.parse_args()
    json_path, report_path = run(args)
    print(f"TRANSCRIPT_PATH={rel(json_path)}")
    print(f"REPORT_PATH={rel(report_path)}")


if __name__ == "__main__":
    main()
