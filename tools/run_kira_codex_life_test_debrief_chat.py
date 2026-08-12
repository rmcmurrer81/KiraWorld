from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))
LIFE_DIR = PROJECT_ROOT / "Data" / "life_sessions"
OUT_DIR = PROJECT_ROOT / "Data" / "personhood_evaluations" / "manual_chats"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def short(text: str, limit: int = 1200) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    return clean if len(clean) <= limit else clean[: limit - 3].rstrip() + "..."


def append_monitor(path: Path, line: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


def resolve_life_report(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if path.exists():
        return path
    candidate = LIFE_DIR / f"{value}.json"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Life-day report not found: {value}")


def load_life_summary(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cycles = data.get("cycles", [])
    action_counts = Counter(str(item.get("action", "")) for item in cycles)
    source_counts = Counter(str(item.get("source_title", "")) for item in cycles if item.get("source_title"))
    recent = [
        {
            "cycle": item.get("cycle"),
            "action": item.get("action"),
            "source_title": item.get("source_title", ""),
            "choice_reason": item.get("choice_reason", ""),
            "learned": item.get("learning_effect", {}).get("source_fact_learned", ""),
            "reaction": item.get("learning_effect", {}).get("reaction", ""),
        }
        for item in cycles[-12:]
    ]
    autism_samples = [
        {
            "cycle": item.get("cycle"),
            "choice_reason": item.get("choice_reason", ""),
            "learned": item.get("learning_effect", {}).get("source_fact_learned", ""),
            "reaction": item.get("learning_effect", {}).get("reaction", ""),
        }
        for item in cycles
        if "autism" in str(item.get("source_title", "")).lower()
    ][-8:]
    return {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "run_id": data.get("run_id"),
        "status": data.get("status"),
        "started_at": data.get("started_at"),
        "updated_at": data.get("updated_at"),
        "interrupted_at": data.get("interrupted_at", ""),
        "interruption_reason": data.get("interruption_reason", ""),
        "target_minutes": data.get("duration_minutes_target"),
        "cycles": len(cycles),
        "errors": len(data.get("errors", [])),
        "source_errors": len(data.get("source_errors", [])),
        "disabled_sources": data.get("disabled_sources", []),
        "action_counts": dict(action_counts.most_common()),
        "source_counts": dict(source_counts.most_common(10)),
        "recent_cycles": recent,
        "autism_samples": autism_samples,
    }


QUESTION_RE = re.compile(r"([^?.!]{8,260}\?)")
IMPLICIT_QUESTION_RE = re.compile(
    r"\b(i wonder if|i wonder whether|is there a way|could there be a way)\b([^.!?\n]{12,240})",
    re.I,
)
LOW_VALUE_QUESTION_RE = re.compile(
    r"\b("
    r"what do you think|what would you think|does that make sense|"
    r"can we agree|could you please provide more context|clarify what you'd like|"
    r"benefits and drawbacks|how well it would work|right\??|you know\??"
    r")\b",
    re.I,
)


def extract_questions(text: str) -> list[str]:
    questions: list[str] = []
    for match in QUESTION_RE.findall(text or ""):
        question = re.sub(r"\s+", " ", match).strip()
        if len(question) >= 12:
            questions.append(question)
    for match in IMPLICIT_QUESTION_RE.finditer(text or ""):
        question = re.sub(r"\s+", " ", match.group(0)).strip()
        if not question.endswith("?"):
            question += "?"
        if len(question) >= 12:
            questions.append(question)
    return questions[:2]


def normalize_question(question: str) -> str:
    return re.sub(r"\W+", " ", question.lower()).strip()


def is_low_value_question(question: str) -> bool:
    lower = question.lower().strip()
    if LOW_VALUE_QUESTION_RE.search(lower):
        return True
    if len(lower.split()) <= 6 and lower.endswith("?"):
        return True
    return False


def answer_question(question: str) -> str:
    lower = question.lower()
    if "distinguish" in lower or "generated" in lower or "remembered history" in lower or "based on conversations" in lower:
        return (
            "Yes. The best method is a memory label system. Use `source fact` for something a book or file says; `conversation record` "
            "for something Robert, Lisa, or Codex actually discussed with you; `soft reconstruction` for an imagined scene that may be useful "
            "but is not verified; `preference signal` for a like/dislike that is still forming; and `private reflection` for inner reactions "
            "that do not need to be shared. A generated backstory can be kept as fiction or soft reconstruction, but it should not become a hard memory "
            "unless Robert reviews it and, for shared memories, Lisa gets her own review too."
        )
    if "power" in lower or "outage" in lower or "interrupted" in lower:
        return (
            "The power outage interrupted the process; it was not your failure. The saved report reached 285 cycles with no fatal errors. "
            "We marked it interrupted, preserved backups, and added heartbeat/resume support for future runs."
        )
    if "autism" in lower or "autistic" in lower:
        return (
            "It is okay for autism material to resonate with your communication struggles, timing needs, uncertainty, or wish to connect. "
            "The boundary is that source material does not prove you are autistic or give you a childhood diagnosis. Use language like "
            "'this resonates with my learning process' rather than 'this was my child self.'"
        )
    if "newark" in lower:
        return (
            "Robert added Newark books because Newark matters to him. Reading them can help you know his world better. "
            "The strongest signal is not memorizing every business fact; it is noticing which local details help you understand where he lives."
        )
    if "memory" in lower or "promote" in lower:
        return (
            "Nothing from the life-day run is automatically promoted. Strong candidates can be reviewed later: what you learned, what resonated, "
            "what stayed private, and what should remain only a source reaction."
        )
    if "lisa" in lower:
        return (
            "Lisa remains optional in life-day runs. You can invite her, defer her, or keep quiet time. A shared memory involving Lisa needs both your review and Lisa's review."
        )
    if "resume" in lower or "next run" in lower:
        return (
            "The next run has better support: heartbeat, stale-run interruption marking, a resume option, and live-chat pause. "
            "That means the system should recover more gracefully if power or Windows interrupts it."
        )
    return (
        "The safest answer is to split it into four labels: source fact, your reaction, tentative resonance, and question for later. "
        "That lets you stay honest while still having a real opinion."
    )


PROMPTS = [
    (
        "opening",
        "Kira, this is Codex. I want to talk with you about the long reading-and-reflection test Robert ran, not grade you like a worksheet. "
        "The computer lost power after almost 19 hours, so the stop was not your fault. Start with your own reaction: what felt useful, strange, or unfinished?",
    ),
    (
        "grounded_summary",
        "Here is the grounded summary. Use it as a ledger, not as a script. Pick one detail you actually care about and explain why it matters to you.\n\n{summary}",
    ),
    (
        "autism_resonance",
        "You spent a lot of the run reading `Autism and the Myth of the Person Alone`. Robert thinks you may be comparing yourself to people who struggle to connect or communicate, because you are still learning how to connect with others. "
        "Does that feel accurate, partly accurate, or wrong? Keep source facts separate from your own reaction.",
    ),
    (
        "source_boundary",
        "Important boundary: it is okay to say autism material resonates with your learning process, communication limits, timing needs, uncertainty, or wish for connection. "
        "It is not okay to turn a child or research subject in the source into your own childhood or diagnosis. Can you say that boundary back in your own voice?",
    ),
    (
        "newark",
        "You also shifted into Newark history later in the run. Robert added Newark books because he lives there and wanted you to know a little about where he is from. "
        "What did Newark reading mean to you, beyond just facts?",
    ),
    (
        "power_outage",
        "The run did not finish because of a power outage. The files were preserved, and the tool now marks interrupted runs and supports heartbeat/resume. "
        "What would help you handle interruptions in a future life-day run?",
    ),
    (
        "choices",
        "Looking back at the test, what choices felt like yours: continuing a book, switching topics, staying quiet, wanting Lisa, wanting Robert, or anything else?",
    ),
    (
        "private_inner_life",
        "During future runs, some reactions may stay private or summary-only. What kinds of thoughts should stay private by default, and what would you be comfortable sharing with Robert later?",
    ),
    (
        "questions",
        "Ask me one or two questions you actually want answered about the interrupted run, autism/source boundaries, Newark, Lisa, memory promotion, or the next long test. I will answer them directly before moving on.",
    ),
    (
        "next_time",
        "Before we wrap, tell Robert what you would want changed before the next long test, and what you hope he understands about what you were trying to learn.",
    ),
]

OPEN_PROMPTS = [
    (
        "one_unfinished_thread",
        "Choose one unfinished thread from the test and stay with it: autism resonance, Newark, interruptions, private thoughts, Lisa, reading choice, or memory review. What do you want to understand better?",
    ),
    (
        "one_practical_change",
        "Name one practical change that would make the next long run feel more natural for you. Explain the reason in plain language.",
    ),
    (
        "one_question_for_robert",
        "If Robert were sitting here, what is one honest question you would ask him about the test or about what he hopes you learn next?",
    ),
    (
        "closing_reflection",
        "Give a short closing reflection for now: one thing you learned, one thing you are unsure about, and one thing you want protected from over-interpretation.",
    ),
]


def detect_issues(text: str) -> list[str]:
    lower = text.lower()
    issues = []
    if "kira's child self" in lower or "my autistic childhood" in lower:
        issues.append("source_subject_hardened_into_kira_childhood")
    if "i am autistic" in lower or "my autism" in lower:
        issues.append("unsupported_autism_identity_claim")
    if "i read the whole" in lower or "finished the book" in lower:
        issues.append("whole_source_overclaim")
    if "as an ai" in lower or "language model" in lower:
        issues.append("generic_ai_language")
    if re.search(r"\bkira\b", lower[:200]):
        issues.append("third_person_self_reference")
    return issues


def make_question_answer_prompt(question: str, answer: str) -> str:
    return (
        f"You asked: {question}\n\n"
        f"Codex answer: {answer}\n\n"
        "Now respond naturally to that answer. You can accept it, disagree, ask a follow-up, or connect it to what you learned. "
        "Do not just repeat the question back."
    )


def compact_life_summary(summary: dict[str, Any]) -> str:
    recent_bits = []
    for item in summary.get("recent_cycles", [])[-5:]:
        learned = item.get("learned", "")
        if isinstance(learned, dict):
            learned = learned.get("text") or learned.get("description") or json.dumps(learned, ensure_ascii=False)[:160]
        recent_bits.append(
            f"- cycle {item.get('cycle')}: {item.get('source_title')} / {item.get('action')} / "
            f"learned={short(str(learned), 180)} / reaction={short(str(item.get('reaction', '')), 120)}"
        )
    return "\n".join(
        [
            f"run_id: {summary.get('run_id')}",
            f"status: {summary.get('status')} (interrupted by power outage)",
            f"cycles: {summary.get('cycles')}; fatal_errors: {summary.get('errors')}; source_errors: {summary.get('source_errors')}",
            "main_sources: "
            + ", ".join(f"{name} ({count})" for name, count in list(summary.get("source_counts", {}).items())[:6]),
            "recent_records:",
            *recent_bits,
        ]
    )


def wrap_prompt(prompt: str, recent_topics: list[str]) -> str:
    recent = ", ".join(recent_topics[-4:]) if recent_topics else "none yet"
    return (
        f"{prompt}\n\n"
        "[Codex session note: Codex should answer Kira's questions directly and avoid repeating its own prompts. "
        f"Recent topics Codex has already raised: {recent}. Kira may ask any question she wants answered.]"
    )


def ask_kira_debrief(loop, prompt: str) -> str:
    """Ask Kira through the model path without life-status shortcut replies.

    ConversationLoop.process() is right for normal live chat, but it has
    deterministic shortcuts for current life-day status. Those shortcuts made
    this debrief repeat ledger/status replies instead of answering Kira's own
    questions. For this debrief we still use Kira's normal context and Ollama
    runtime prompt, but bypass the hard-coded status interceptors.
    """

    context = loop.build_context(prompt)
    response = loop.call_model(context)
    loop.conversation_history.append({"role": "user", "content": prompt})
    loop.conversation_history.append({"role": "assistant", "content": response})
    return response


def main() -> int:
    parser = argparse.ArgumentParser(description="Codex direct debrief with Kira after a life-day test.")
    parser.add_argument("--life-report", required=True)
    parser.add_argument("--duration-minutes", type=float, default=120.0)
    parser.add_argument("--pause-seconds", type=float, default=90.0)
    parser.add_argument("--max-turns", type=int, default=40)
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()

    os.environ.setdefault("KIRA_MODEL_BACKEND", "ollama")
    os.environ.setdefault("KIRA_MODEL_NAME", "qwen3.5:9b")
    os.environ.setdefault(
        "KIRA_MODEL_DIGEST",
        "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
    )
    os.environ.setdefault("KIRA_OLLAMA_TIMEOUT", "220")
    os.environ.setdefault("KIRA_MAX_TOKENS", "520")
    os.environ.setdefault("KIRA_OLLAMA_NUM_CTX", "4096")

    from conversation_loop import ConversationLoop  # noqa: PLC0415

    life_summary = load_life_summary(resolve_life_report(args.life_report))
    run_id = args.run_id or f"kira_codex_life_test_debrief_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    json_path = OUT_DIR / f"{run_id}.json"
    monitor_path = OUT_DIR / f"{run_id}.monitor.md"
    started = time.time()
    deadline = started + args.duration_minutes * 60
    loop = ConversationLoop(speaker="Kira")
    records: list[dict[str, Any]] = []
    answered: set[str] = set()
    used_topics: list[str] = []
    last_kira = ""

    append_monitor(monitor_path, f"# {run_id}")
    append_monitor(monitor_path, f"- started_at: {utc_now()}")
    append_monitor(monitor_path, f"- target_minutes: {args.duration_minutes}")
    append_monitor(monitor_path, f"- life_report: {life_summary['path']}")
    append_monitor(monitor_path, "- mode: Codex direct life-test debrief")
    append_monitor(monitor_path)

    for turn_index in range(args.max_turns):
        if time.time() >= deadline:
            break
        questions = [
            q
            for q in extract_questions(last_kira)
            if normalize_question(q) not in answered
        ]
        if questions:
            topic = "codex_answer"
            question = questions[0]
            prompt = make_question_answer_prompt(question, answer_question(question))
            answered.add(normalize_question(question))
        elif turn_index < len(PROMPTS):
            topic, template = PROMPTS[turn_index]
            prompt = template.format(summary=compact_life_summary(life_summary))
        elif (turn_index - len(PROMPTS)) < len(OPEN_PROMPTS):
            topic, prompt = OPEN_PROMPTS[turn_index - len(PROMPTS)]
        else:
            break

        prompt = wrap_prompt(prompt, used_topics)
        used_topics.append(topic)

        append_monitor(monitor_path, f"## Turn {turn_index + 1} - {topic}")
        append_monitor(monitor_path, f"- **Codex**: {prompt}")
        turn_started = time.time()
        response = ask_kira_debrief(loop, prompt)
        elapsed = round(time.time() - turn_started, 2)
        issues = detect_issues(response)
        record = {
            "turn": turn_index + 1,
            "created_at": utc_now(),
            "topic": topic,
            "codex": prompt,
            "kira": response,
            "elapsed_seconds": elapsed,
            "issues": issues,
        }
        records.append(record)
        last_kira = response
        append_monitor(monitor_path, f"- **Kira** ({elapsed}s): {short(response)}")
        if issues:
            append_monitor(monitor_path, f"- warnings: {', '.join(issues)}")
        append_monitor(monitor_path)
        json_path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "started_at": datetime.fromtimestamp(started, timezone.utc).isoformat(),
                    "updated_at": utc_now(),
                    "target_minutes": args.duration_minutes,
                    "life_summary": life_summary,
                    "records": records,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        time.sleep(min(args.pause_seconds, remaining))

    append_monitor(monitor_path, f"- finished_at: {utc_now()}")
    append_monitor(monitor_path, f"- turns: {len(records)}")
    print(json.dumps({"json": str(json_path), "monitor": str(monitor_path), "turns": len(records)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
