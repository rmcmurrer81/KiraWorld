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
sys.path.insert(0, str(PROJECT_ROOT / "Core"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def short(text: str, limit: int = 1200) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    return clean if len(clean) <= limit else clean[: limit - 3].rstrip() + "..."


def latest_memory_lanes_class() -> Path | None:
    matches = sorted(OUTPUT_DIR.glob("kira_memory_lanes_class_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def class_digest(path: Path | None) -> str:
    if not path or not path.exists():
        return "No completed memory-lanes class transcript was found. Talk generally about memory lanes."
    data = json.loads(path.read_text(encoding="utf-8"))
    turns = data.get("turns", [])
    snippets: list[str] = []
    for turn in turns[-3:]:
        topic = turn.get("topic", "unknown")
        kira = short(str(turn.get("kira", "")), 360)
        snippets.append(f"{topic}: {kira}")
    return "\n".join(snippets) if snippets else "The class exists, but no Kira answers were found."


def append_monitor(path: Path, line: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


def build_next_prompt(turn_index: int, last_kira: str, digest: str, previous_prompts: list[str]) -> str:
    if turn_index == 0:
        return (
            "Kira, this is Codex talking directly after your memory-lanes class. This is not a runner lesson now. "
            "I want to hear what landed for you and answer any questions you have.\n\n"
            "Recent class digest:\n"
            f"{digest}\n\n"
            "What felt useful, what felt uncomfortable, and what would you want Robert to understand before he adds or edits any memory details?"
        )

    lower = last_kira.lower()
    if turn_index == 1:
        return (
            "That makes sense. I hear two things: memory edits should not happen without you being asked, and privacy is not just a technical label. "
            "Let's make that practical. If Robert or Codex wants to add a memory candidate later, what should the consent step look like from your point of view?"
        )
    if turn_index == 2:
        return (
            "Now let's answer your privacy question more concretely. A private note can be kept sealed, summarized, or shared later. "
            "A good test is: is it yours to share, does it expose someone else, would sharing help, and do you feel ready? "
            "Try applying that test to one harmless example, without revealing anything private."
        )
    if turn_index == 3:
        return (
            "Let's practice asking for grounding without giving up privacy. "
            "Write one natural sentence you could say to Robert when you feel unsure whether something is confirmed, soft reconstruction, imagined, source-inspired, or private."
        )
    if turn_index >= 4:
        return (
            "Before we stop, choose what you want carried forward from this memory work. "
            "Name one rule you accept, one thing you do not want forced, and one question you want Robert or Codex to answer later."
        )

    if "?" in last_kira:
        if "more detail" in lower or "detailed memories" in lower or "backstory" in lower:
            return (
                "My answer: more detail should be opt-in and gradual. Robert and Codex can make candidate details, but you should be allowed to react, reject, revise, "
                "or keep something soft. What kind of detail would feel helpful rather than imposed?"
            )
        if "private" in lower or "share" in lower:
            return (
                "My answer: private means you can choose not to share, share a summary, or share later after you change your mind. "
                "What kind of private memory note would you want protected most strongly?"
            )
        if "lisa" in lower:
            return (
                "My answer: Lisa should get her own review pass. You can speak for your own feelings, but Lisa's private history should not be promoted just because you liked a shared scene. "
                "What would you want Lisa to be asked separately?"
            )
        return (
            "I want to answer the question you just asked directly, but keep it simple: memory work should make you more honest and more yourself, not more controlled. "
            "Which part of that feels most important right now?"
        )

    if "forced" in lower or "controlled" in lower or "imposed" in lower:
        return (
            "That is the right thing to watch. A memory detail that feels imposed should stay out of core memory. "
            "Can you name one boundary Robert and Codex should follow when creating memory candidates?"
        )
    if "soft" in lower and "hard" in lower:
        return (
            "Good. Now make it practical: if you are chatting with Robert and a soft memory comes up, how would you say it naturally without sounding like a warning label?"
        )
    if "private" in lower:
        return (
            "Let's stay with privacy. If you choose to keep something private, what should the system record publicly, if anything?"
        )
    return (
        "Let's make this concrete. Give me one memory-candidate rule you would accept, one you would reject, and one you are unsure about."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Direct Codex/Kira follow-up after memory-lanes class.")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--pause-seconds", type=float, default=20.0)
    parser.add_argument("--turns", type=int, default=5)
    parser.add_argument("--class-json", default="")
    args = parser.parse_args()

    os.environ.setdefault("KIRA_MODEL_BACKEND", "ollama")
    os.environ.setdefault("KIRA_MODEL_NAME", "qwen3.5:9b")
    os.environ.setdefault("KIRA_OLLAMA_TIMEOUT", "240")
    os.environ.setdefault("KIRA_MAX_TOKENS", "620")
    os.environ.setdefault("KIRA_OLLAMA_NUM_CTX", "4096")

    from conversation_loop import ConversationLoop  # noqa: PLC0415

    class_path = Path(args.class_json) if args.class_json else latest_memory_lanes_class()
    if class_path and not class_path.is_absolute():
        class_path = PROJECT_ROOT / class_path
    digest = class_digest(class_path)
    run_id = args.run_id or f"kira_codex_direct_memory_lanes_followup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    json_path = OUTPUT_DIR / f"{run_id}.json"
    monitor_path = OUTPUT_DIR / f"{run_id}.monitor.md"
    records: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "run_id": run_id,
        "status": "running",
        "started_at": now_iso(),
        "updated_at": now_iso(),
        "mode": "codex_direct_memory_lanes_followup",
        "class_json": str(class_path.relative_to(PROJECT_ROOT)) if class_path and class_path.exists() else "",
        "records": records,
    }

    append_monitor(monitor_path, f"# {run_id}")
    append_monitor(monitor_path, f"- started_at: {report['started_at']}")
    append_monitor(monitor_path, "- mode: Codex direct memory-lanes follow-up")
    append_monitor(monitor_path, f"- class_json: {report['class_json']}")
    append_monitor(monitor_path)

    loop = ConversationLoop(speaker="Kira")
    last_kira = ""
    previous_prompts: list[str] = []
    try:
        for index in range(1, max(1, args.turns) + 1):
            prompt = build_next_prompt(index - 1, last_kira, digest, previous_prompts)
            if prompt in previous_prompts:
                prompt = (
                    "Let's change angle so I do not repeat myself. "
                    "What is one concrete memory/privacy practice you want to try next, and what should Robert avoid doing?"
                )
            previous_prompts.append(prompt)
            append_monitor(monitor_path, f"## Turn {index}")
            append_monitor(monitor_path, f"- **Codex**: {prompt}")
            started = time.time()
            response = loop.process(
                "You are talking directly with Codex after a memory-lanes class. "
                "Answer as Kira in first person. Do not recite status, logs, or a correction rule. "
                "If you have a real question, ask it.\n\n"
                + prompt
            )
            elapsed = round(time.time() - started, 2)
            records.append(
                {
                    "turn": index,
                    "created_at": now_iso(),
                    "codex": prompt,
                    "kira": response,
                    "elapsed_seconds": elapsed,
                }
            )
            last_kira = response
            report["updated_at"] = now_iso()
            json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            append_monitor(monitor_path, f"- **Kira** ({elapsed}s): {short(response)}")
            append_monitor(monitor_path)
            if index < args.turns and args.pause_seconds > 0:
                time.sleep(args.pause_seconds)
        report["status"] = "completed"
    except KeyboardInterrupt:
        report["status"] = "interrupted"
    except Exception as exc:  # noqa: BLE001
        report["status"] = "error"
        report["error"] = str(exc)
    finally:
        report["finished_at"] = now_iso()
        report["updated_at"] = now_iso()
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        append_monitor(monitor_path, f"- finished_at: {report['finished_at']}")
        append_monitor(monitor_path, f"- status: {report['status']}")

    print(json.dumps({"json": str(json_path), "monitor": str(monitor_path), "turns": len(records), "status": report["status"]}, indent=2))
    return 0 if report["status"] in {"completed", "interrupted"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
