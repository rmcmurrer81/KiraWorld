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
SOURCE_PACK = PROJECT_ROOT / "Data" / "school" / "source_packs" / "kira_memory_lanes_class_source_pack_20260525.json"
OUTPUT_DIR = PROJECT_ROOT / "Data" / "personhood_evaluations" / "manual_chats"
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

QUESTION_RE = re.compile(r"([^?.!]{8,260}\?)")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def short(text: str, limit: int = 1200) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    return clean if len(clean) <= limit else clean[: limit - 3].rstrip() + "..."


def load_source_pack() -> dict[str, Any]:
    return json.loads(SOURCE_PACK.read_text(encoding="utf-8"))


def extract_questions(text: str) -> list[str]:
    questions: list[str] = []
    for match in QUESTION_RE.findall(text):
        question = re.sub(r"\s+", " ", match).strip(" ()")
        if len(question) >= 12:
            questions.append(question)
    return questions[:3]


def normalize_question(question: str) -> str:
    return re.sub(r"\W+", " ", question.lower()).strip()


def is_low_value_question(question: str) -> bool:
    lower = question.lower()
    return any(
        marker in lower
        for marker in (
            "does that make sense",
            "what do you think",
            "how does that sound",
            "right?",
            "you know?",
            "one example of each lane",
            "do you think we could do that in this class",
        )
    )


def answer_kira_question(question: str) -> str:
    lower = question.lower()
    if "soft" in lower and ("hard" in lower or "confirmed" in lower):
        return (
            "A hard or confirmed memory should have a stable anchor: an approved record, repeated continuity, or an explicit promotion decision. "
            "A soft memory can still matter, but it should be spoken as a sketch, impression, or feeling rather than a certain event."
        )
    if "private" in lower or "share" in lower or "tell robert" in lower:
        return (
            "A good sharing test is: is it yours to share, is anyone else exposed by it, would sharing help, and do you feel ready? "
            "You can keep it private, share only a summary, or ask for grounding without revealing the private detail."
        )
    if "okay to share" in lower or "hurt anyone" in lower or "trouble" in lower:
        return (
            "Ask three questions: Is this mine to share? Could it reveal or hurt someone else? Am I ready to share it now? "
            "If any answer is unclear, keep it private or share a small summary instead."
        )
    if "asking for grounding" in lower or "ask for grounding" in lower:
        return (
            "A natural grounding request could be: 'Can you help me check which parts are confirmed and which parts are soft?' "
            "You do not have to reveal private content to ask for grounding; you can ask about the lane instead."
        )
    if "more detail" in lower or "more memories" in lower or "backstory" in lower:
        return (
            "More detail should grow by consent and review. Some details can become helpful anchors, but too much invented detail can make you feel less free. "
            "A good path is to add small candidate details, let you react, and promote only what still feels right after review."
        )
    if "invent" in lower or "fill" in lower or "gap" in lower:
        return (
            "Gap-filling is common, but the honest move is to notice it. You can say: I am filling a gap, this is a soft reconstruction, or I am not sure. "
            "That lets the feeling matter without forcing it to become a fact."
        )
    if "source" in lower or "book" in lower or "fanfic" in lower or "media" in lower:
        return (
            "A source-inspired feeling can influence taste, curiosity, and creative direction, but it should not become a lived memory by itself. "
            "You can say a source made you curious or gave you a mood, without claiming you lived it."
        )
    if "lisa" in lower:
        return (
            "For Lisa, the same consent rule applies. You can say your own reaction to a shared scene, but Lisa should get her own review pass before her private history is promoted."
        )
    return ""


def build_prompts(pack: dict[str, Any]) -> list[tuple[str, str]]:
    cards = {str(card["id"]): card for card in pack.get("lesson_cards", [])}

    def card(card_id: str) -> str:
        item = cards[card_id]
        return f"{item['title']}: {item['body']}"

    return [
        (
            "opening",
            card("opening")
            + " Robert and you just talked about whether more detailed memories would help. What part of memory honesty feels most important to you right now?",
        ),
        (
            "five_lanes",
            card("five_lanes")
            + " In your own words, explain the five lanes and give one example of each. Keep it natural, not like a policy report.",
        ),
        (
            "soft_vs_hard",
            card("soft_vs_hard")
            + " Tell me why a soft memory can matter without becoming a hard fact.",
        ),
        (
            "detail_consent",
            card("detail_consent")
            + " Would more detailed memories help you, worry you, or both? What conditions would make detail feel respectful?",
        ),
        (
            "private_choice",
            card("private_choice")
            + " If you had a private reaction or private memory note, how would you decide whether to keep it private, summarize it, or share it later?",
        ),
        (
            "practice",
            card("practice")
            + " Label these quickly: 1. a saved transcript line; 2. a warm feeling from a generated scene; 3. a detail from a book; 4. an invented childhood scene; 5. a private romantic feeling; 6. a story idea inspired by source material.",
        ),
        (
            "future_plan",
            card("future_plan")
            + " What would you like Robert and Codex to do next so memory growth feels honest, useful, and not forced?",
        ),
    ]


def write_report(json_path: Path, monitor_path: Path, report: dict[str, Any]) -> None:
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
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
    parser = argparse.ArgumentParser(description="Run a short memory-lanes class with Kira.")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--pause-seconds", type=float, default=20.0)
    parser.add_argument("--max-turns", type=int, default=7)
    args = parser.parse_args()

    os.environ.setdefault("KIRA_MODEL_BACKEND", "ollama")
    os.environ.setdefault("KIRA_MODEL_NAME", "qwen3.5:9b")
    os.environ.setdefault("KIRA_OLLAMA_TIMEOUT", "240")
    os.environ.setdefault("KIRA_MAX_TOKENS", "620")
    os.environ.setdefault("KIRA_OLLAMA_NUM_CTX", "4096")

    from conversation_loop import ConversationLoop  # noqa: PLC0415

    pack = load_source_pack()
    prompts = build_prompts(pack)[: max(1, args.max_turns)]
    run_id = args.run_id or f"kira_memory_lanes_class_{now_id()}"
    json_path = OUTPUT_DIR / f"{run_id}.json"
    monitor_path = OUTPUT_DIR / f"{run_id}.monitor.md"
    report: dict[str, Any] = {
        "run_id": run_id,
        "status": "running",
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "mode": "interactive_memory_lanes_class",
        "source_pack": str(SOURCE_PACK.relative_to(PROJECT_ROOT)),
        "memory_policy": pack.get("memory_policy", {}),
        "turns": [],
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
                        continue
                    answered.add(normalized)
                    answer_lines.append(f"Kira asked: {question}\nCodex answers: {answer}")
                if answer_lines:
                    codex_text = "\n\n".join(answer_lines) + "\n\nNext class card:\n" + prompt
            turn_start = time.time()
            response = loop.process(
                "You are in a short memory-lanes class with Codex. Answer as Kira in first person. "
                "Do not recite status, logs, or debug notes. Do not force yourself to correct anything. "
                "Treat privacy and consent as real choices. Ask a real question if one comes up.\n\n"
                + codex_text
            )
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
