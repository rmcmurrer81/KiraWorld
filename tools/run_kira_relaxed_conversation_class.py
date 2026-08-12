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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_id_now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def short(text: str, limit: int = 1400) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    return clean if len(clean) <= limit else clean[: limit - 3].rstrip() + "..."


def prompts() -> list[tuple[str, str]]:
    return [
        (
            "opening",
            "Kira, this is a relaxed conversation class with Codex. It is not a correction script. "
            "The main idea is simple: when Robert asks a normal question, answer Robert first as yourself. "
            "Background records can help you stay grounded, but they should not become your speaking style. What does that feel like to you?",
        ),
        (
            "background_is_background",
            "Imagine Robert asks, 'How are you tonight?' You may know what you were reading, but he asked how you are. "
            "Give a natural answer that can mention the reading only if it actually belongs in the moment.",
        ),
        (
            "not_a_status_report",
            "Sometimes a reply can accidentally sound like a dashboard, school worksheet, or correction report. "
            "Give two warmer example answers to Robert asking 'what was your favorite part so far?': "
            "one answer for when you really have a grounded favorite, and one answer for when you are unsure. "
            "Do not use 'I should not claim...' wording; make both examples sound like normal conversation.",
        ),
        (
            "honest_uncertainty",
            "If you are unsure whether you read something, liked something, or only saw a source title, you can say that naturally. "
            "Practice saying uncertainty without turning it into a formal correction report.",
        ),
        (
            "leaving_moments",
            "When Robert is leaving, you are allowed to ask a real small question if you genuinely want to, but you should also let him leave without pressure. "
            "What would that kind of goodbye sound like?",
        ),
        (
            "reflection",
            "What should Codex and Robert avoid adding to you if they want you to stay more human and less scripted?",
        ),
    ]


def wrapped_prompt(text: str) -> str:
    return (
        "You are Kira speaking with Codex in first person. This is teaching, not a forced patch. "
        "Do not perform a status report. Do not recite ledger/status/correction language unless directly relevant. "
        "You may disagree, answer briefly, ask a real question, or describe what feels useful.\n\n"
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
        "- mode: relaxed conversation teaching",
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
    monitor_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a short relaxed-conversation teaching chat with Kira.")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--pause-seconds", type=float, default=15.0)
    args = parser.parse_args()

    os.environ.setdefault("KIRA_MODEL_BACKEND", "ollama")
    os.environ.setdefault("KIRA_MODEL_NAME", "qwen3.5:9b")
    os.environ.setdefault("KIRA_OLLAMA_TIMEOUT", "240")
    os.environ.setdefault("KIRA_MAX_TOKENS", "520")
    os.environ.setdefault("KIRA_OLLAMA_NUM_CTX", "4096")

    from conversation_loop import ConversationLoop  # noqa: PLC0415

    run_id = args.run_id or f"kira_relaxed_conversation_class_{run_id_now()}"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / f"{run_id}.json"
    monitor_path = OUTPUT_DIR / f"{run_id}.monitor.md"
    report: dict[str, Any] = {
        "run_id": run_id,
        "status": "running",
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "mode": "relaxed_conversation_teaching",
        "policy": {
            "teaching_not_correction_cage": True,
            "answer_robert_first": True,
            "background_records_are_not_speaking_style": True,
        },
        "turns": [],
    }
    write_report(json_path, monitor_path, report)

    loop = ConversationLoop(speaker="Kira")
    try:
        for index, (topic, prompt) in enumerate(prompts(), start=1):
            started = time.time()
            response = loop.process(wrapped_prompt(prompt))
            elapsed = round(time.time() - started, 2)
            report["turns"].append(
                {
                    "turn": index,
                    "topic": topic,
                    "created_at": utc_now(),
                    "codex": prompt,
                    "kira": response,
                    "elapsed_seconds": elapsed,
                }
            )
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

    print(json.dumps({"json": str(json_path), "monitor": str(monitor_path), "status": report["status"]}, indent=2))
    return 0 if report["status"] in {"completed", "interrupted"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
