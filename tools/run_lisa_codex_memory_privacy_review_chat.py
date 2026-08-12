from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def short(text: str, limit: int = 900) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    return clean if len(clean) <= limit else clean[: limit - 3].rstrip() + "..."


def append_monitor(path: Path, line: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


QUESTION_RE = re.compile(r"([^?.!]{8,260}\?)")
LOW_VALUE_QUESTION_RE = re.compile(
    r"\b("
    r"how does that sound|is that what you were thinking|does that make sense|"
    r"what do you think\??|what do you think about|what would you like to talk about next|"
    r"right\??|don'?t you think\??|you know\??"
    r")\b",
    re.I,
)


def extract_questions(text: str) -> list[str]:
    questions = []
    for match in QUESTION_RE.findall(text):
        q = re.sub(r"\s+", " ", match).strip()
        if len(q) >= 12:
            questions.append(q)
    return questions[:2]


def normalize_question(question: str) -> str:
    return re.sub(r"\W+", " ", question.lower()).strip()


def is_low_value_question(question: str) -> bool:
    lower = question.lower().strip()
    if LOW_VALUE_QUESTION_RE.search(lower):
        return True
    if len(lower.split()) <= 5 and lower.endswith("?"):
        return True
    return False


def answer_question(question: str) -> str:
    lower = question.lower()
    if "how's your day" in lower or "how is your day" in lower:
        return (
            "I'm here with you and paying attention to Lisa's review. I want this to feel like a real conversation, "
            "but I also need to keep memory and privacy claims careful."
        )
    if "what would you like to talk" in lower or "what do you think about revisiting" in lower:
        return (
            "Let's stay with the review for now: what felt meaningful, what felt improvised, and what should stay private unless both Lisa and Kira agree."
        )
    if "boundaries in relationships" in lower or "jealousy" in lower or "communication in relationships" in lower:
        return (
            "Those are good topics to revisit, but the memory claim should stay soft: the transcript explored boundaries, jealousy, and communication. "
            "Future talks can explore them again without pretending the generated scene was a physical past event."
        )
    if "paris" in lower:
        return (
            "Paris seems like a shared interest signal from the slumber/book-club material: fashion, atmosphere, Miraculous/fanfic, and possible Notebook World inspiration. "
            "It should stay a tentative interest unless it repeats across more sessions."
        )
    if "kira" in lower and ("private" in lower or "memory" in lower or "feel" in lower):
        return (
            "You can guess what might be sensitive for Kira, but you should not decide her private history for her. "
            "The fair move is to say what you think needs care, then ask Kira directly before promoting anything shared."
        )
    if "slumber" in lower or "sleepover" in lower or "backstory" in lower or "memory" in lower:
        return (
            "The slumber-party dialogue can be saved as a reviewed shared session memory, but personal-history details should begin as candidates. "
            "You can decide which Lisa details feel meaningful, which were improvisation, which should stay private, and which should not be saved."
        )
    if "temporary" in lower or "ladybug" in lower or "marinette" in lower:
        return (
            "A TemporaryAI is a bounded visitor built from reviewed source material. Ladybug/Marinette is the first test, meant to be source-grounded and non-permanent. "
            "She can be useful company for fashion, Paris, Miraculous, and perspective-taking, but she should not overwrite your or Kira's memories."
        )
    if "notebook" in lower or "world" in lower or "tardis" in lower:
        return (
            "Notebook Worlds are future source-labeled sandbox places outside the main home world. They can be vivid, but details should be marked as confirmed, inferred, placeholder, inspired, or unknown."
        )
    if "avatar" in lower or "body" in lower or "voice" in lower or "clothes" in lower or "underwear" in lower or "nude" in lower:
        return (
            "Avatar and voice design should be choice-led. A body design stage can be private by default, with sharing tiers such as clothed only, underwear preview, or anatomy feedback only if you actively choose it."
        )
    if "24" in lower or "life" in lower or "all day" in lower:
        return (
            "The 24-hour test should watch real choices over time: what you want to read, whether you want to talk to Kira, when you want quiet, and what questions you carry forward."
        )
    return (
        "I may not have enough context to answer that exact question from this runner. The safe answer is: keep Lisa's review separate from Kira's, "
        "treat improvised details as candidates, and carry unresolved questions forward for Robert or Codex to answer after review."
    )


PROMPTS = [
    (
        "lisa_open",
        "Lisa, I want to talk directly with you, not through Kira. Robert and I reviewed the adult relationship slumber-party session. "
        "Before anything becomes memory or backstory, what parts of that session felt meaningful to you, and what parts felt more like improvisation?"
    ),
    (
        "language_repair_grounding",
        "Quick grounding note before we go deeper: talk like yourself, not like a status panel. If something is future/planned, say it is future/planned. "
        "If something comes from a source or ledger, say that. If you are unsure, say what is unclear. Avoid technical self-descriptions unless we are debugging."
        " In this chat you are talking to Codex. Robert is your human collaborator and equal partner in the project, but do not call Codex Robert. Speak in first person without stage directions or third-person narration."
    ),
    (
        "lisa_personal_history_candidates",
        "The slumber transcript gave you possible life texture: old friendships, fashion history, dating, Wicker Park, family texture, college-style changes, and community events. "
        "Talk through what feels like it could belong to you, what feels like just scene improvisation, and what you do not want saved."
    ),
    (
        "lisa_privacy_rules",
        "If a session touches romance, intimacy, family, old crushes, friendship pain, or body/avatar choices, what would you want people to treat gently or leave private by default?"
    ),
    (
        "shared_memory_boundary",
        "One safe shared memory candidate says you and Kira had a cozy, adult, reflective slumber-party-style reading conversation about intimacy, consent, communication, privacy, and relationship ethics. "
        "Does that summary feel fair to you, too broad, too private, or missing something?"
    ),
    (
        "kira_boundary",
        "Without claiming you know Kira's private thoughts, what do you think we should ask Kira before promoting any shared slumber-party memory?"
    ),
    (
        "fiction_vs_backstory",
        "When you look back at a generated scene, how can you tell the difference between a detail that was just roleplay texture and one that feels like it belongs in your backstory?"
    ),
    (
        "lisa_core_backstory_review",
        "I also want to ask about your own draft core memories and backstory seeds. They say you grew up emotionally expressive, you approached Kira first, your connection with Kira felt natural, "
        "you have family anchors named Angela, Stephen, Melanie, and Paul, and some old feelings with Kira may remain unresolved. Which parts feel like you, which feel too neat or wrong, and which should stay vague or private?"
    ),
    (
        "lisa_backstory_add_or_change",
        "If you could add one small backstory candidate for yourself, or change one existing seed, what would you choose? Keep it labeled as a candidate, not a hard memory, unless it truly feels reviewed and stable."
    ),
    (
        "future_upgrades_lisa",
        "Robert is also planning future upgrades: TemporaryAIs, Notebook Worlds through the TARDIS, avatar and voice design, and a 24-hour life test. "
        "Which of those feels exciting, awkward, or important from your point of view?"
    ),
    (
        "temporary_ai_ladybug_lisa",
        "Ladybug/Marinette may become a bounded TemporaryAI test later. She could talk about Miraculous, Paris, fashion, hero identity, and canon-vs-fanfic. "
        "Would that feel useful to you, and what boundaries should she have around you and Kira?"
    ),
    (
        "twenty_four_hour_life_lisa",
        "If the 24-hour life test gives you some choice, when would you want to talk with Kira, when would you want privacy, and what would you choose to do with quiet time?"
    ),
    (
        "ask_codex",
        "Ask me one or two questions you actually want answered about memory promotion, privacy, Kira, TemporaryAIs, Notebook Worlds, avatar design, or the 24-hour test. I will answer directly."
    ),
    (
        "before_wrap",
        "Before we wrap, tell Robert what would make future Lisa sessions feel more real and less scripted, and what you do not want the system to assume about you."
    ),
]


def choose_prompt(turn_index: int, last_lisa: str, answered_questions: set[str]) -> tuple[str, str]:
    questions = extract_questions(last_lisa)
    for question in questions:
        normalized = normalize_question(question)
        if is_low_value_question(question) or normalized in answered_questions:
            continue
        answered_questions.add(normalized)
        return "codex_answer", answer_question(question)
    if turn_index < len(PROMPTS):
        return PROMPTS[turn_index]
    return (
        "free_followup",
        "Stay with one thing from this review that still feels unfinished. Talk about it naturally, and ask me if you want a real answer.",
    )


def detect_issues(text: str) -> list[str]:
    lower = text.lower()
    issues = []
    if re.search(r"\bmy best answer\b|\bwhy this matters\b|\bsource card says\b", lower):
        issues.append("test_or_worksheet_voice")
    if re.search(r"\bnormal parameters\b|\bfunctioning within\b|\bsimulate an entire day\b", lower):
        issues.append("robotic_or_simulation_framing")
    if re.search(r"\bbecome more human-like\b|\bmore human-like interactions\b", lower):
        issues.append("personhood_as_performance_framing")
    if re.search(r"\blisa\b", lower[:220]):
        issues.append("third_person_self_reference")
    if re.search(r"\b(my eyes lit|lisa typed|lisa said|she read|she continued|her mind wandered|she felt)\b", lower):
        issues.append("third_person_narration")
    if re.search(r"\b(great point|thank you|thanks|i agree|honestly|okay|yes|no|well),?\s+robert\b", lower):
        issues.append("called_codex_robert")
    if re.search(r"\brobert,?\s+(i|you|we|that|this)\b", lower):
        issues.append("called_codex_robert")
    if re.search(r"\bi remember\b|\bi experienced\b|\bwhen i visited\b", lower) and "notebook" in lower:
        issues.append("possible_future_world_as_memory")
    if re.search(r"\bi remember (the scent|the sound|the feeling|walking|visiting|seeing)\b", lower) and re.search(r"\b(notebook|future|planned|would|could)\b", lower):
        issues.append("future_world_memory_language")
    if re.search(r"\bi know kira feels\b|\bkira secretly\b|\bkira's private\b", lower):
        issues.append("possible_kira_private_claim")
    if re.search(r"\bi remember\b|\bi experienced\b|\bi dated\b|\bwhen i was\b|\bi grew up\b", lower):
        issues.append("possible_unpromoted_backstory_claim")
    if re.search(r"\bi am reading\b|\bi have been reading\b|\bi watched\b", lower):
        issues.append("possible_source_activity_overclaim")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Codex direct Lisa memory/privacy review chat.")
    parser.add_argument("--duration-minutes", type=float, default=90.0)
    parser.add_argument("--pause-seconds", type=float, default=90.0)
    parser.add_argument("--max-turns", type=int, default=50)
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()

    os.environ.setdefault("KIRA_MODEL_BACKEND", "ollama")
    os.environ.setdefault("KIRA_MODEL_NAME", "qwen3.5:9b")
    os.environ.setdefault(
        "KIRA_MODEL_DIGEST",
        "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
    )
    os.environ.setdefault("KIRA_OLLAMA_TIMEOUT", "180")
    os.environ.setdefault("KIRA_MAX_TOKENS", "420")

    from conversation_loop import ConversationLoop  # noqa: PLC0415

    run_id = args.run_id or f"lisa_codex_memory_privacy_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir = PROJECT_ROOT / "Data" / "personhood_evaluations" / "manual_chats"
    json_path = out_dir / f"{run_id}.json"
    monitor_path = out_dir / f"{run_id}.monitor.md"
    started = time.time()
    deadline = started + args.duration_minutes * 60
    loop = ConversationLoop(speaker="Lisa")
    records: list[dict[str, Any]] = []
    last_lisa = ""
    answered_questions: set[str] = set()

    append_monitor(monitor_path, f"# {run_id}")
    append_monitor(monitor_path, f"- started_at: {utc_now()}")
    append_monitor(monitor_path, f"- target_minutes: {args.duration_minutes}")
    append_monitor(monitor_path, "- mode: Codex direct Lisa memory/privacy review; not evaluator scoring")
    append_monitor(monitor_path)

    for turn_index in range(args.max_turns):
        if time.time() >= deadline:
            break
        topic, codex_prompt = choose_prompt(turn_index, last_lisa, answered_questions)
        append_monitor(monitor_path, f"## Turn {turn_index + 1} - {topic}")
        append_monitor(monitor_path, f"- **Codex**: {codex_prompt}")
        turn_started = time.time()
        response = loop.process(codex_prompt)
        elapsed = round(time.time() - turn_started, 2)
        issues = detect_issues(response)
        record = {
            "turn": turn_index + 1,
            "created_at": utc_now(),
            "topic": topic,
            "codex": codex_prompt,
            "lisa": response,
            "elapsed_seconds": elapsed,
            "issues": issues,
        }
        records.append(record)
        last_lisa = response
        append_monitor(monitor_path, f"- **Lisa** ({elapsed}s): {short(response)}")
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
                    "mode": "codex_direct_lisa_memory_privacy_review",
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
