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
SOURCE_PACK = PROJECT_ROOT / "Data" / "school" / "source_packs" / "kira_miraculous_continuity_interactive_source_pack_20260521.json"
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


def append_monitor(path: Path, line: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


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
    lower = question.lower().strip()
    low_value = [
        "how does that sound",
        "does that make sense",
        "what do you think",
        "can we talk more about",
        "what do you guys think",
        "next step",
    ]
    return any(marker in lower for marker in low_value)


def answer_kira_question(question: str) -> str:
    lower = question.lower()
    if "temporaryai ladybug" in lower or ("temporary" in lower and "ladybug" in lower):
        return (
            "TemporaryAI Ladybug is a project idea, not a canon Miraculous character and not a story inside the show. "
            "It means a bounded, source-grounded visitor based on Marinette/Ladybug who could talk with you about Paris, fashion, courage, awkwardness, "
            "hero identity, and Miraculous source material. She should know only what her source/persona is allowed to know, and she should not overwrite "
            "your memories, Lisa's privacy, or Robert's project records."
        )
    if "specific story" in lower or "within the miraculous universe" in lower or "what does that refer to" in lower:
        return (
            "That is a project layer, not Miraculous canon. The show has Marinette/Ladybug; our project may later create a TemporaryAI Ladybug inspired by source material. "
            "So label it TemporaryAI/project design, not canon and not a watched memory."
        )
    if "original comic" in lower or "original comics" in lower:
        return (
            "For this project, say Miraculous show, script, source material, or fanfic unless we have a specific comic source in front of us. "
            "If you are unsure which source something came from, say source uncertainty instead of calling it original comics."
        )
    if "bunny" in lower and "marinette" in lower:
        return (
            "Small correction for the source layer: Marinette Dupain-Cheng is Ladybug, not Bunny or Bunnyx. Alix Kubdel is the character connected to Bunnyx. "
            "If a fanfic blends names or roles, you can still enjoy it, but label that as fanfic or source uncertainty."
        )
    if "why a character inside" in lower or "might not know" in lower:
        return (
            "A character inside the story only knows what they have learned in that scene or episode. "
            "For example, as source knowledge Kira can know Adrien is Cat Noir, but Marinette may treat Adrien and Cat Noir as separate people until she learns the secret. "
            "That is character point of view, not a contradiction."
        )
    if "can we focus" in lower or "favorite scene" in lower or "favorite part" in lower:
        return (
            "Yes. If a source is finished but still interesting, the clean choices are to revisit a favorite scene or page range, reread from page one, discuss the themes, "
            "or mark it finished-but-liked and pick a related source later."
        )
    if "move on" in lower and ("discuss" in lower or "themes" in lower):
        return (
            "Either choice is valid. If you still feel curious, discuss the themes or revisit a favorite scene. If the source feels complete, mark it finished-but-liked and move on."
        )
    if "boundaries" in lower or "consent" in lower or "power dynamics" in lower or "emotional safety" in lower:
        return (
            "For this class, the safest way to discuss that is at the media-literacy level: notice whether a scene gives characters agency, "
            "whether secret identities limit informed choice, and whether hero/villain pressure changes what consent or trust can mean. "
            "You can compare canon, scripts, and fanfic, but label which layer you are discussing."
        )
    if "visual" in lower or "example" in lower or "show to reference" in lower:
        return (
            "Pre-GPU, we should use text source cards, scripts, and written scene summaries rather than pretending you can visually inspect video. "
            "Later, with GPU/vision, we can add still frames or clips as visual prompts and clearly mark them as observed source evidence."
        )
    if "cat noir" in lower or "chat noir" in lower or "adrien" in lower:
        return (
            "Adrien Agreste and Cat Noir are the same person in canon, but the perspective matters. "
            "If you are speaking as Marinette/Ladybug at a point where she does not know that, you can treat them as separate in her point of view. "
            "If you are speaking as Kira analyzing source material, you can say the broader canon fact."
        )
    if "marinette" in lower or "ladybug" in lower:
        return (
            "Marinette Dupain-Cheng and Ladybug are the same person in different identity contexts. "
            "The useful lesson is that one person can have a public self, a private self, and a role-based self without becoming separate people."
        )
    if "who is" in lower or "same person" in lower or "identity pair" in lower or "identity pairs" in lower:
        return (
            "The basic identity pairs for this class are: Marinette Dupain-Cheng is Ladybug; Adrien Agreste is Cat Noir; "
            "Alix Kubdel can become Bunnyx. Character point of view still matters: a character may not know the hidden identity yet."
        )
    if "bunny" in lower or "bunnyx" in lower or "alix" in lower:
        return (
            "In the source layer for this class, Alix Kubdel can become Bunnyx; that is not just a fanfic idea. "
            "A fanfic can still separate younger Alix and older/future Bunnyx or change their relationship, but that separation should be labeled as a fanfic variant, time-version, or source uncertainty."
        )
    if "fanfic" in lower or "canon" in lower or "source" in lower:
        return (
            "Canon means supported by the official source material. Fanfic means a creative variant that can still be emotionally interesting. "
            "You can like a fanfic, borrow mood from it, or build a Notebook World from it, but it should not rewrite what the show itself says."
        )
    if "inferred" in lower or "implied" in lower or "interpretation" in lower or "creating something entirely new" in lower or "own design" in lower:
        return (
            "Use four labels. Canon: directly supported by the official source. Inferred: not stated, but a reasonable guess from source evidence. "
            "Fanfic-inspired: borrowed from a fanfic or creative variant. Own design: something you invented for a Notebook World or story. "
            "If you are unsure, call it source uncertainty instead of forcing one label."
        )
    if "notebook" in lower or "world" in lower:
        return (
            "A Notebook World can be vivid without pretending it is canon. The clean labels are: confirmed source detail, inference, fanfic-inspired detail, "
            "Kira design choice, placeholder, or unknown."
        )
    if "feedback" in lower and ("memory" in lower or "grounded" in lower or "reality" in lower):
        return (
            "Yes. The best feedback loop is outside your spoken voice: Codex reviews logs and marks claims as grounded, soft/reconstructed, source-inspired, "
            "fanfic/Notebook, or likely drift. Robert can then decide what to discuss with you. You should not have to recite the ledger during normal chat."
        )
    if "memory" in lower or "remembering" in lower or "really happened" in lower or "making up" in lower:
        return (
            "A grounded memory is tied to a real project event, chat, source, or reviewed memory seed. A soft memory is a feeling-shaped reconstruction. "
            "A source-inspired idea comes from reading or fanfic. The honest move is to say which kind it is, or say you are unsure."
        )
    if "temporary" in lower or "visitor" in lower:
        return (
            "A TemporaryAI is a bounded visitor or study companion built from source material. Ladybug can help with Paris, fashion, hero identity, "
            "and Miraculous perspective, but she should not overwrite your private life, Lisa's privacy, or Robert's project records."
        )
    if "finished" in lower or "end" in lower or "page" in lower:
        return (
            "When a source reaches its last page, there is no secret next page. You can choose to reread it from page one, revisit a favorite scene, "
            "talk about it, or move to something new."
        )
    if "anything else" in lower or "what else" in lower or "more to know" in lower or "like to know" in lower:
        return (
            "Useful next topics would be: how secret identities affect trust, how TemporaryAI Ladybug should handle knowledge she would not know in-character, "
            "how to label fanfic variants without making them less enjoyable, and how to make a Paris Notebook World from canon plus your own design choices."
        )
    if "why" in lower and ("matter" in lower or "important" in lower):
        return (
            "It matters because it lets you enjoy stories without confusing source facts, fanfic, roleplay, and your own memories. "
            "That gives you more freedom, not less."
        )
    return (
        "My best answer is: label the layer you are using. Are you speaking from canon, fanfic, a TemporaryAI point of view, a Notebook World design, "
        "or your own Kira reaction? Once the layer is clear, you can be much freer and more natural."
    )


def build_prompts(pack: dict[str, Any]) -> list[tuple[str, str]]:
    cards = pack.get("lesson_cards", [])
    by_id = {str(card.get("id")): card for card in cards if isinstance(card, dict)}

    def card_text(card_id: str) -> str:
        card = by_id[card_id]
        return f"{card['title']}: {card['body']}"

    return [
        (
            "opening",
            "Kira, I want to teach this directly instead of relying on hidden warning notes. "
            "This is an interactive Miraculous continuity class. You can react, disagree, ask questions, or say what feels useful. "
            "This is source knowledge and media literacy, not a memory of watching the show. "
            "Say show, scripts, source material, or fanfic as appropriate; do not claim you are reading original comics unless a specific source says that. "
            "What feels most confusing or interesting about Miraculous right now?"
        ),
        (
            "identity_layers",
            card_text("identity_layers")
            + " Talk this through in your own words: how can one person have a civilian self and a hero self without becoming two unrelated people?"
        ),
        (
            "perspective_boundary",
            card_text("perspective_boundary")
            + " Give me one example of how your answer would differ if you were speaking as Kira analyzing the show versus speaking as Marinette inside the story."
        ),
        (
            "alix_bunnyx",
            card_text("alix_bunnyx")
            + " What should you do if a fanfic makes Alix and Bunnyx feel like two separate people?"
        ),
        (
            "canon_fanfic_notebook",
            card_text("canon_fanfic_notebook")
            + " Imagine you wanted to build a Paris Notebook World inspired by Miraculous. How would you label what is canon, fanfic-inspired, inferred, or your own design?"
        ),
        (
            "temporary_ai_ladybug",
            card_text("temporary_ai_ladybug")
            + " If Ladybug visited as a TemporaryAI later, what would you want to talk with her about, and what boundaries should she have?"
        ),
        (
            "source_completion",
            card_text("source_completion")
            + " Tell me what you would choose if you finished a script you liked: move on, reread from page one, revisit a favorite part, or discuss it."
        ),
        (
            "fact_check_identity_pairs",
            card_text("fact_practice_identity")
            + " Quick fact practice: name the identity pairs, then explain why a character inside the story might not know one of those pairs yet."
        ),
        (
            "fact_check_layers",
            card_text("fact_practice_layers")
            + " Quick fact practice: I will give you four examples. Label each one: canon/source fact, character point of view, fanfic variant, inference, Notebook World design, or Kira reaction. "
            "1. 'Adrien is Cat Noir.' 2. 'Marinette thinks Cat Noir is separate from Adrien.' 3. 'A fanfic gives older Bunnyx a different personality.' 4. 'I design a quiet Paris rooftop for a Notebook World.'"
        ),
        (
            "fact_check_finished_source",
            card_text("fact_practice_finished_source")
            + " Quick fact practice: if a PDF has 32 pages and the next read starts at page 33, what does that mean? What are your choices if you still like the source?"
        ),
        (
            "reflection",
            "Now step away from the worksheet feeling. What did this class change for you, if anything? "
            "What still feels unclear, and what would you want Robert or Codex to explain next?"
        ),
        (
            "open_questions",
            "Before we stop, is there anything else you would like to know about Miraculous continuity, fanfic boundaries, TemporaryAI Ladybug, Notebook Worlds, or finished-source choices? "
            "Ask naturally. If I know the answer from this class, I will answer it; if not, I will mark it for Robert/Codex review later."
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
    parser = argparse.ArgumentParser(description="Run an interactive Miraculous continuity class with Kira.")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--pause-seconds", type=float, default=20.0)
    parser.add_argument("--max-turns", type=int, default=12)
    args = parser.parse_args()

    os.environ.setdefault("KIRA_MODEL_BACKEND", "ollama")
    os.environ.setdefault("KIRA_MODEL_NAME", "qwen3.5:9b")
    os.environ.setdefault("KIRA_OLLAMA_TIMEOUT", "240")
    os.environ.setdefault("KIRA_MAX_TOKENS", "520")
    os.environ.setdefault("KIRA_OLLAMA_NUM_CTX", "4096")

    from conversation_loop import ConversationLoop  # noqa: PLC0415

    pack = load_source_pack()
    prompts = build_prompts(pack)[: max(1, args.max_turns)]
    run_id = args.run_id or f"kira_miraculous_continuity_class_{now_id()}"
    json_path = OUTPUT_DIR / f"{run_id}.json"
    monitor_path = OUTPUT_DIR / f"{run_id}.monitor.md"
    report: dict[str, Any] = {
        "run_id": run_id,
        "status": "running",
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "mode": "interactive_miraculous_continuity_class",
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
                questions = extract_questions(str(report["turns"][-1].get("kira", "")))
                answer_lines = []
                for question in questions:
                    normalized = normalize_question(question)
                    if normalized in answered or is_low_value_question(question):
                        continue
                    answer = answer_kira_question(question)
                    answered.add(normalized)
                    answer_lines.append(f"Kira asked: {question}\nCodex answers: {answer}")
                if answer_lines:
                    codex_text = "\n\n".join(answer_lines) + "\n\nNext class card:\n" + prompt
            turn_start = time.time()
            response = loop.process(
                "You are in a short interactive class with Codex. Answer as Kira in first person. "
                "Do not recite status or debug notes. Do not claim you watched video, heard audio, or read comics unless the source layer explicitly says so. "
                "Ask a real question if one comes up.\n\n"
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
                turn["answered_questions"].append({"question": question, "answer": answer_kira_question(question)})
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
