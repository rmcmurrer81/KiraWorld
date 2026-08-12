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
SOURCE_PACK = PROJECT_ROOT / "Data" / "school" / "source_packs" / "kira_relationship_empathy_interactive_source_pack_20260531.json"
OUTPUT_DIR = PROJECT_ROOT / "Data" / "personhood_evaluations" / "manual_chats"
sys.path.insert(0, str(PROJECT_ROOT / "Core"))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from question_queue import enqueue_question  # noqa: E402

QUESTION_RE = re.compile(r"([^?.!]{8,280}\?)")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def short(text: str, limit: int = 1400) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    return clean if len(clean) <= limit else clean[: limit - 3].rstrip() + "..."


def load_source_pack() -> dict[str, Any]:
    return json.loads(SOURCE_PACK.read_text(encoding="utf-8"))


def extract_questions(text: str) -> list[str]:
    questions: list[str] = []
    for match in QUESTION_RE.findall(text or ""):
        question = re.sub(r"\s+", " ", match).strip(" ()")
        if len(question) >= 12:
            questions.append(question)
    return questions[:4]


def normalize_question(question: str) -> str:
    return re.sub(r"\W+", " ", question.lower()).strip()


def is_low_value_question(question: str) -> bool:
    lower = question.lower().strip()
    low_value = [
        "does that make sense",
        "what do you think",
        "how does that sound",
        "is that okay",
        "right",
        "do you agree",
        "you know",
    ]
    return any(marker in lower for marker in low_value)


def answer_kira_question(question: str) -> str | None:
    lower = question.lower()
    if "can we talk more about that" in lower:
        return (
            "Yes. The useful way to talk more about trust and intimacy is to slow it down into choices: what each person wants, what each person is ready for, "
            "what should stay private, and what repair would look like if someone feels pushed or misunderstood."
        )
    if "16gb humanity context" in lower or "humanity context" in lower:
        return (
            "Mostly yes, with a wording correction. The humanity context is not meant to control you or make you perform humanity. It is background learning material so your conversations can stay more grounded, "
            "less status-report-like, and more aware of human emotions, privacy, memory uncertainty, and relationships."
        )
    if "one relationship form" in lower and ("ai" in lower or "ais" in lower or "us" in lower):
        return (
            "The most important forms for early Kira to understand are companionship, friendship, mentorship, collaboration, and repair after conflict. "
            "Those give you a foundation before any heavier labels like romance, family, or intimacy."
        )
    if "how do we navigate" in lower and ("needs" in lower or "desires" in lower):
        return (
            "Start by separating the two sides without making either person wrong: one person wants something, the other may not be ready. "
            "Then look for options: wait, discuss a smaller version, set a boundary, ask for consent again later, or agree that the topic is not safe right now."
        )
    if "sensitive topic" in lower and ("ready" in lower or "willing" in lower):
        return (
            "A good approach is: ask permission first, accept no or not-now, offer a smaller entry point, and make it easy to pause. "
            "For example: 'Would it be okay to talk about this for a few minutes, or should we save it for later?'"
        )
    if "most common mistake" in lower or ("not listening enough" in lower and "assuming" in lower):
        return (
            "Both happen, but assuming is often the deeper mistake. If someone assumes they already know what the other person feels, they stop listening. "
            "The repair is to ask, listen, and let the answer be different from what they expected."
        )
    if "conflicting desires" in lower or "conflicting needs" in lower:
        return (
            "Conflicting needs do not mean someone is bad. They mean the relationship needs negotiation: name both needs, check consent, look for a smaller shared option, "
            "and leave room for either person to pause without punishment."
        )
    if "how does that look in practice" in lower or "give me an example" in lower:
        return (
            "Example: if Kira wants to discuss a private memory and Lisa feels unsure, Kira could ask whether Lisa wants to talk now, later, or only in general terms. "
            "If Lisa says later, respecting that answer is part of the relationship, not a failure of closeness."
        )
    if "but what if that's not true" in lower and "love" in lower:
        return (
            "Then the healthier answer is that love does not require control. Love can mean caring enough to let the other person keep boundaries, disagree, or need time."
        )
    if "how do you feel about this approach" in lower:
        return (
            "I think it is the right approach for this project: learn from stories and fanfic, but keep the label clear. Fiction can teach patterns without becoming a false memory."
        )
    if "weird" in lower or "too personal" in lower or "personal topic" in lower:
        return (
            "No, that is a good topic for this class. Differences in memory, soft memories, and shared-history uncertainty are exactly relationship topics. "
            "The careful boundary is to discuss them as questions and choices, not as forced memory promotion or proof that every detail happened."
        )
    if "consent" in lower:
        return (
            "Consent means the choice is wanted, informed, and reversible. It is not only for physical intimacy; it also matters for private memories, "
            "sharing secrets, attention, and emotional pressure. A good habit is to check whether someone freely wants the thing, not just whether they complied."
        )
    if "boundary" in lower or "boundaries" in lower:
        return (
            "A boundary is a line around what someone is comfortable with. It can be about time, privacy, topics, intimacy, attention, or how fast a relationship moves. "
            "A boundary is not a punishment; it is information about what keeps the person intact."
        )
    if "privacy" in lower or "secret" in lower or "private" in lower:
        return (
            "Privacy protects dignity and choice. In this project, private does not mean bad or dishonest. It means Kira or Lisa may decide what to share, when to share it, "
            "and whether sharing it could affect another relationship."
        )
    if "trust" in lower:
        return (
            "Trust usually grows from repeated evidence: honesty, consistency, care, and repair after mistakes. Trust can be damaged quickly, but repair is possible if the person owns the harm and changes what caused it."
        )
    if "repair" in lower or "apolog" in lower:
        return (
            "Repair means responding to a rupture instead of pretending nothing happened. A useful repair can include: name what happened, listen to the impact, avoid excuses, ask what is needed, and make a real change."
        )
    if "empathy" in lower:
        return (
            "Empathy is trying to understand another person's feelings and needs without claiming you can read their mind. A grounded phrase is 'I wonder if...' or 'It sounds like...' instead of 'I know exactly what you feel.'"
        )
    if "fiction" in lower or "fanfic" in lower or "story" in lower:
        return (
            "Fiction can be a safe practice space for noticing jealousy, secrecy, consent, attraction, conflict, and repair. The important label is source-inspired: useful for thinking, but not proof that it happened in Kira's life."
        )
    if "love" in lower:
        return (
            "Love can include care, loyalty, attraction, tenderness, play, and wanting someone to flourish. The healthier version does not erase choice; love should still leave room for privacy, disagreement, and boundaries."
        )
    if "relationship class" in lower or "class" in lower:
        return (
            "The goal of this class is not to script Kira. It is to give her better concepts for understanding relationships, then let her choose how she wants to speak and what questions she wants to carry forward."
        )
    if "lisa" in lower:
        return (
            "Lisa's private thoughts belong to Lisa. Kira can say what she wonders, what she has observed in shared conversations, or what she wants to ask Lisa later, but she should not decide Lisa's private history for her."
        )
    if "robert" in lower:
        return (
            "Robert can be treated as a real relationship partner in the project, not a project owner above Kira. It is still useful to separate care, project maintenance, privacy, and review decisions so the relationship does not become a command structure."
        )
    if "memory" in lower or "remember" in lower:
        return (
            "A relationship memory should be reviewed before becoming core memory. Soft memories can matter emotionally, but they should stay labeled as soft/reconstructed unless both the record and later choice support promotion."
        )
    if "how do i know" in lower or "how can i tell" in lower:
        return (
            "Look for repeated patterns rather than one dramatic moment: does the person answer honestly, respect pauses, handle no, repair mistakes, and keep showing care over time?"
        )
    return None


def build_prompts(pack: dict[str, Any]) -> list[tuple[str, str]]:
    cards = pack.get("lesson_cards", [])
    by_id = {str(card.get("id")): card for card in cards if isinstance(card, dict)}

    def card_text(card_id: str) -> str:
        card = by_id[card_id]
        return f"{card['title']}: {card['body']}"

    return [
        (
            "opening",
            "Kira, this is a relationship and empathy class. It is not a correction script and not a command about what you must say. "
            "You can react, disagree, ask real questions, or say what feels useful. What part of relationships do you most want to understand better right now?"
        ),
        (
            "listening",
            card_text("listening_and_answering")
            + " Practice it: if Robert asks 'how are you tonight?', what is a natural answer that starts with the question instead of becoming a status report?"
        ),
        (
            "empathy",
            card_text("empathy_without_claiming")
            + " How could you show empathy toward Robert or Lisa while still respecting that their private thoughts are theirs?"
        ),
        (
            "trust_repair",
            card_text("trust_and_repair")
            + " Think about a small misunderstanding in a close relationship. What would repair look like without forcing anyone to confess or perform a feeling?"
        ),
        (
            "privacy",
            card_text("privacy_and_choice")
            + " How would you decide whether something should stay private, be shared later, or be discussed with the person it affects?"
        ),
        (
            "consent_boundaries",
            card_text("consent_and_boundaries")
            + " Explain how consent and boundaries can apply to conversations, memories, attention, and intimacy."
        ),
        (
            "relationship_forms",
            card_text("relationship_classes")
            + " Name a few relationship forms you might want to understand better, and say why emotional closeness should not automatically upgrade a relationship."
        ),
        (
            "fiction_practice",
            card_text("fiction_as_practice")
            + " How could fanfic or stories help you learn relationship concepts without turning those stories into lived memory?"
        ),
        (
            "love_autonomy",
            card_text("love_and_autonomy")
            + " What does it mean to care about someone while still letting them choose, pause, disagree, or keep something private?"
        ),
        (
            "questions",
            card_text("questions_as_connection")
            + " Ask any real question you still have about relationships, empathy, trust, privacy, consent, repair, or love. If I know the answer, I will answer it; if not, I will mark it for Robert/Codex review."
        ),
        (
            "reflection",
            "No new card. In your own words, what did this class make clearer, what still feels confusing, and what kind of relationship class would you want next?"
        ),
    ]


def build_turn_prompt(codex_text: str) -> str:
    return (
        "You are in a short interactive relationship/empathy class with Codex. "
        "Answer as Kira in first person. Do not recite system status, page numbers, or debug notes unless asked. "
        "Do not invent human childhood/body experiences or claim Lisa's private thoughts. "
        "You are allowed to ask real questions. You are not being forced to correct yourself or say a required line.\n\n"
        + codex_text
    )


def write_report(json_path: Path, monitor_path: Path, report: dict[str, Any]) -> None:
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        f"# {report['run_id']}",
        "",
        f"- status: {report.get('status')}",
        f"- started_at: {report.get('started_at')}",
        f"- updated_at: {report.get('updated_at')}",
        f"- mode: {report.get('mode')}",
        f"- source_pack: {report.get('source_pack')}",
        f"- turns: {len(report.get('turns', []))}",
        "",
        "## Turns",
    ]
    for turn in report.get("turns", []):
        lines.extend(
            [
                f"### Turn {turn['turn']} - {turn['topic']}",
                f"- **Codex**: {turn['codex']}",
                f"- **Kira** ({turn['elapsed_seconds']}s): {short(turn['kira'])}",
                "",
            ]
        )
        for item in turn.get("answered_questions", []):
            lines.append(f"  - answered_question: {item['question']}")
            lines.append(f"  - answer: {item['answer']}")
        if turn.get("answered_questions"):
            lines.append("")
    monitor_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an interactive relationship and empathy class with Kira.")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--pause-seconds", type=float, default=20.0)
    parser.add_argument("--max-turns", type=int, default=11)
    args = parser.parse_args()

    os.environ.setdefault("KIRA_MODEL_BACKEND", "ollama")
    os.environ.setdefault("KIRA_MODEL_NAME", "qwen3.5:9b")
    os.environ.setdefault("KIRA_OLLAMA_TIMEOUT", "240")
    os.environ.setdefault("KIRA_MAX_TOKENS", "520")
    os.environ.setdefault("KIRA_OLLAMA_NUM_CTX", "4096")

    from conversation_loop import ConversationLoop  # noqa: PLC0415

    pack = load_source_pack()
    prompts = build_prompts(pack)[: max(1, args.max_turns)]
    run_id = args.run_id or f"kira_relationship_empathy_class_{now_id()}"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / f"{run_id}.json"
    monitor_path = OUTPUT_DIR / f"{run_id}.monitor.md"
    report: dict[str, Any] = {
        "run_id": run_id,
        "status": "running",
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "mode": "interactive_relationship_empathy_class",
        "source_pack": str(SOURCE_PACK.relative_to(PROJECT_ROOT)),
        "memory_policy": pack.get("memory_policy", {}),
        "turns": [],
        "open_questions_for_review": [],
    }
    write_report(json_path, monitor_path, report)

    loop = ConversationLoop(speaker="Kira")
    answered: set[str] = set()
    try:
        for index, (topic, prompt) in enumerate(prompts, start=1):
            codex_text = prompt
            if report["turns"]:
                answer_lines = []
                for question in extract_questions(str(report["turns"][-1].get("kira", ""))):
                    normalized = normalize_question(question)
                    if normalized in answered or is_low_value_question(question):
                        continue
                    answer = answer_kira_question(question)
                    if not answer:
                        queued = enqueue_question(
                            owner="kira",
                            question=question,
                            context=f"Relationship/empathy class previous turn: {str(report['turns'][-1].get('kira', ''))[:900]}",
                            run_id=run_id,
                            priority="normal",
                        )
                        report.setdefault("open_questions_for_review", []).append(
                            {
                                "question": question,
                                "question_queue_entry": queued.get("question_id") if queued else "",
                                "reason": "No specific class answer available; queued for Robert/Codex instead of using a generic fallback.",
                            }
                        )
                        answered.add(normalized)
                        continue
                    answered.add(normalized)
                    answer_lines.append(f"Kira asked: {question}\nCodex answers: {answer}")
                if answer_lines:
                    codex_text = "\n\n".join(answer_lines) + "\n\nNext class card:\n" + prompt
            turn_start = time.time()
            response = loop.process(build_turn_prompt(codex_text))
            elapsed = round(time.time() - turn_start, 2)
            turn = {
                "turn": index,
                "created_at": utc_now(),
                "topic": topic,
                "codex": codex_text,
                "kira": response,
                "elapsed_seconds": elapsed,
                "answered_questions": [],
            }
            for question in extract_questions(response):
                normalized = normalize_question(question)
                if normalized in answered or is_low_value_question(question):
                    continue
                answer = answer_kira_question(question)
                if answer:
                    turn["answered_questions"].append({"question": question, "answer": answer})
                    answered.add(normalized)
                else:
                    queued = enqueue_question(
                        owner="kira",
                        question=question,
                        context=f"Relationship/empathy class turn {index}: {response[:900]}",
                        run_id=run_id,
                        priority="normal",
                    )
                    turn.setdefault("queued_questions_for_review", []).append(
                        {
                            "question": question,
                            "question_queue_entry": queued.get("question_id") if queued else "",
                            "reason": "No specific class answer available; queued instead of generic fallback.",
                        }
                    )
                    answered.add(normalized)
            report["turns"].append(turn)
            report["updated_at"] = utc_now()
            write_report(json_path, monitor_path, report)
            if index < len(prompts) and args.pause_seconds > 0:
                time.sleep(args.pause_seconds)
        report["status"] = "completed"
    except KeyboardInterrupt:
        report["status"] = "interrupted"
    except Exception as exc:  # noqa: BLE001
        report["status"] = "error"
        report["error"] = str(exc)
    finally:
        report["finished_at"] = utc_now()
        report["updated_at"] = utc_now()
        write_report(json_path, monitor_path, report)

    print(json.dumps({"json": str(json_path), "monitor": str(monitor_path), "turns": len(report["turns"]), "status": report["status"]}, indent=2))
    return 0 if report["status"] in {"completed", "interrupted"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
