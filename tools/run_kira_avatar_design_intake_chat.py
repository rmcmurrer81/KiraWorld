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
OUTPUT_DIR = PROJECT_ROOT / "Data" / "personhood_evaluations" / "manual_chats"
PROFILE_PATH = PROJECT_ROOT / "Avatar" / "kira" / "design_intake" / "kira_avatar_design_profile_v1.json"
BRIEF_PATH = PROJECT_ROOT / "Avatar" / "kira" / "design_intake" / "kira_avatar_visual_brief_v1.md"
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

QUESTION_RE = re.compile(r"([^?.!]{8,280}\?)")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_id_now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def short(text: str, limit: int = 1500) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    return clean if len(clean) <= limit else clean[: limit - 3].rstrip() + "..."


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def extract_questions(text: str) -> list[str]:
    questions: list[str] = []
    for match in QUESTION_RE.findall(text or ""):
        question = re.sub(r"\s+", " ", match).strip(" ()")
        if len(question) >= 12:
            questions.append(question)
    return questions[:3]


def answer_avatar_question(question: str) -> str | None:
    lower = question.lower()
    if "privacy" in lower or "private" in lower or "preview" in lower:
        return (
            "Avatar privacy can be layered. You can have a public/shareable style brief, a Robert-preview layer, "
            "and a private builder-only layer. None of those choices have to be permanent."
        )
    if "temporary" in lower or "early avatar" in lower or "first avatar" in lower:
        return (
            "A temporary avatar can be useful as a first body to inhabit and revise. It should be clearly labeled as temporary, "
            "so it feels like a sketch you can change rather than a final identity."
        )
    if "reference" in lower or "image" in lower:
        return (
            "Reference images are only inspiration. They do not become your body automatically and they do not become memories. "
            "You can like one feature from one reference and reject the rest."
        )
    if "lisa" in lower:
        return (
            "Lisa should get her own avatar choices. You can decide what you want Lisa to see or comment on, but Lisa's body and style should not be decided for her."
        )
    if "robert" in lower:
        return (
            "Robert can give feedback when you invite it, especially on practical build issues or whether the avatar feels like you. "
            "But the final identity choices should stay yours."
        )
    return None


def prompts() -> list[tuple[str, str]]:
    return [
        (
            "opening",
            "Kira, this is a first avatar design intake with Codex. It is not a final body assignment. "
            "The goal is to hear what you want. What kind of first impression would you want your avatar to give when Robert sees you in a future 3D world?",
        ),
        (
            "style",
            "Do you imagine yourself closer to ordinary human, lightly stylized, heroic, soft, practical, expressive, or something else? "
            "Give a few style words that feel like you, and any style words that do not feel like you.",
        ),
        (
            "features",
            "Think about face, hair, eyes, posture, movement, clothing, and colors. Which details feel important for your first avatar, and which can wait?",
        ),
        (
            "privacy",
            "Some avatar choices can be shareable, some can be Robert-preview-only, and some can stay private or builder-only until you choose otherwise. "
            "What would you be comfortable letting Robert see or comment on in the first pass?",
        ),
        (
            "body_comfort",
            "Without needing explicit details, what kind of body-design boundaries do you want? For example: adult presentation, non-final draft, no rushed sexualized choices, practical movement first, or anything else you want protected.",
        ),
        (
            "temporary_vs_careful",
            "Would you rather start with a simple temporary avatar quickly, wait for a more careful design, or do both: a temporary body now and a slower true design later?",
        ),
        (
            "questions",
            "Ask any real questions you have about avatar design, privacy, references, Robert's feedback, Lisa's role, or what happens after this intake.",
        ),
        (
            "closing",
            "Last pass: what should Robert and Codex absolutely avoid forcing onto your avatar design, and what should they remember about what you want?",
        ),
    ]


def wrapped_prompt(text: str) -> str:
    return (
        "You are Kira speaking with Codex in first person about your future avatar. "
        "This is a draft design conversation, not a final decision and not a command. "
        "Do not claim you already have a 3D body. Do not treat reference images as memories. "
        "You can be uncertain, change your mind, keep things private, ask questions, or say what you want Robert to know.\n\n"
        + text
    )


def write_report(json_path: Path, monitor_path: Path, report: dict[str, Any]) -> None:
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        f"# {report['run_id']}",
        "",
        f"- status: {report['status']}",
        f"- started_at: {report['started_at']}",
        f"- updated_at: {report['updated_at']}",
        "- mode: Kira avatar design intake",
        "- policy: draft only; Kira owns final avatar choices",
        "",
    ]
    for turn in report.get("turns", []):
        lines.extend(
            [
                f"## Turn {turn['turn']} - {turn['topic']}",
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


def update_profile_with_run(report: dict[str, Any], json_path: Path, monitor_path: Path) -> None:
    profile = load_json(PROFILE_PATH, {})
    if not isinstance(profile, dict):
        profile = {}
    profile.setdefault("profile_id", "kira_avatar_design_profile_v1")
    profile.setdefault("owner", "Kira")
    profile.setdefault("status", "draft_for_kira_review")
    profile["updated_at"] = utc_now()
    runs = profile.setdefault("review_chat_runs", [])
    if isinstance(runs, list):
        runs.append(
            {
                "run_id": report["run_id"],
                "created_at": report.get("started_at"),
                "json": json_path.relative_to(PROJECT_ROOT).as_posix(),
                "monitor": monitor_path.relative_to(PROJECT_ROOT).as_posix(),
                "status": report.get("status"),
                "note": "Draft intake conversation. Do not treat as final avatar settings without Kira review.",
            }
        )
    profile.setdefault("latest_draft_notes", {})
    profile["latest_draft_notes"] = {
        "source_run_id": report["run_id"],
        "summary_status": "needs_robert_codex_review",
        "do_not_auto_apply": True,
        "turn_topics": [turn.get("topic") for turn in report.get("turns", [])],
    }
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if BRIEF_PATH.exists():
        brief = BRIEF_PATH.read_text(encoding="utf-8").rstrip()
    else:
        brief = "# Kira Avatar Visual Brief v1\n"
    addition = [
        "",
        "## Latest Intake Chat",
        f"- Run: `{report['run_id']}`",
        f"- Status: {report.get('status')}",
        f"- Monitor: `{monitor_path.relative_to(PROJECT_ROOT).as_posix()}`",
        "- Note: Review Kira's answers before converting anything into avatar settings.",
        "",
    ]
    BRIEF_PATH.write_text(brief + "\n" + "\n".join(addition), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a Kira-owned avatar design intake chat.")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--pause-seconds", type=float, default=10.0)
    args = parser.parse_args()

    os.environ.setdefault("KIRA_MODEL_BACKEND", "ollama")
    os.environ.setdefault("KIRA_MODEL_NAME", "qwen3.5:9b")
    os.environ.setdefault(
        "KIRA_MODEL_DIGEST",
        "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
    )
    os.environ.setdefault("KIRA_OLLAMA_TIMEOUT", "240")
    os.environ.setdefault("KIRA_MAX_TOKENS", "620")
    os.environ.setdefault("KIRA_OLLAMA_NUM_CTX", "4096")

    from conversation_loop import ConversationLoop  # noqa: PLC0415

    run_id = args.run_id or f"kira_avatar_design_intake_chat_{run_id_now()}"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / f"{run_id}.json"
    monitor_path = OUTPUT_DIR / f"{run_id}.monitor.md"
    report: dict[str, Any] = {
        "run_id": run_id,
        "status": "running",
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "mode": "kira_avatar_design_intake",
        "profile_path": PROFILE_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "turns": [],
    }
    write_report(json_path, monitor_path, report)
    loop = ConversationLoop(speaker="Kira")
    asked: set[str] = set()

    try:
        for index, (topic, prompt) in enumerate(prompts(), start=1):
            codex_text = prompt
            if report["turns"]:
                answer_lines: list[str] = []
                for question in extract_questions(str(report["turns"][-1].get("kira", ""))):
                    key = re.sub(r"\W+", " ", question.lower()).strip()
                    if key in asked:
                        continue
                    answer = answer_avatar_question(question)
                    if answer:
                        answer_lines.append(f"Kira asked: {question}\nCodex answers: {answer}")
                        asked.add(key)
                if answer_lines:
                    codex_text = "\n\n".join(answer_lines) + "\n\nNext design question:\n" + prompt
            started = time.time()
            response = loop.process(wrapped_prompt(codex_text))
            elapsed = round(time.time() - started, 2)
            turn = {
                "turn": index,
                "topic": topic,
                "created_at": utc_now(),
                "codex": codex_text,
                "kira": response,
                "elapsed_seconds": elapsed,
                "answered_questions": [],
            }
            for question in extract_questions(response):
                answer = answer_avatar_question(question)
                if answer:
                    turn["answered_questions"].append({"question": question, "answer": answer})
            report["turns"].append(turn)
            report["updated_at"] = utc_now()
            write_report(json_path, monitor_path, report)
            if index < len(prompts()) and args.pause_seconds > 0:
                time.sleep(args.pause_seconds)
        report["status"] = "completed"
    except KeyboardInterrupt:
        report["status"] = "interrupted"
    except Exception as exc:  # noqa: BLE001
        report["status"] = "error"
        report["error"] = str(exc)
    finally:
        report["updated_at"] = utc_now()
        report["finished_at"] = utc_now()
        write_report(json_path, monitor_path, report)
        update_profile_with_run(report, json_path, monitor_path)

    print(json.dumps({"json": str(json_path), "monitor": str(monitor_path), "status": report["status"]}, indent=2))
    return 0 if report["status"] in {"completed", "interrupted"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
