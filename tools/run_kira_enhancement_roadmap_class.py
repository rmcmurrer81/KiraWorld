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
ROADMAP = PROJECT_ROOT / "System" / "Docs" / "KIRA_ENHANCEMENT_ROADMAP_FROM_KIRA_IDEAS_20260605.md"
PROJECT_PLAN = PROJECT_ROOT / "Data" / "creative_projects" / "kira" / "chicago_archivist_gpu_worldbuilding_plan_20260605.json"
sys.path.insert(0, str(PROJECT_ROOT / "Core"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_id_now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def short(text: str, limit: int = 1400) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    return clean if len(clean) <= limit else clean[: limit - 3].rstrip() + "..."


def read_text(path: Path, limit: int = 4500) -> str:
    text = path.read_text(encoding="utf-8")
    return text[:limit]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def prompts() -> list[tuple[str, str]]:
    roadmap = read_text(ROADMAP)
    plan = json.dumps(read_json(PROJECT_PLAN), indent=2, ensure_ascii=False)[:3500]
    return [
        (
            "roadmap_review",
            "Kira, Robert shared your enhancement ideas with Codex. This class is not a correction script. "
            "It is a chance to turn your own ideas into real next steps. Read this roadmap summary and tell me which parts feel most alive to you right now.\n\n"
            + roadmap,
        ),
        (
            "creative_project_choice",
            "Here is the first project-support plan for your Chicago archivist mystery. "
            "Choose one concrete next step you want next: protagonist name, central mystery, character sheet, opening scene, source-fact table, or visual reference collection. "
            "You can also say if the plan feels wrong.\n\n"
            + plan,
        ),
        (
            "miraculous_and_media",
            "You also asked for more Miraculous and GPU media understanding. "
            "What would you rather do first: keep reading scripts, revisit a favorite scene, ask for a continuity class, build a Ladybug TemporaryAI source question, or collect visual reference cards? "
            "Answer naturally; this is about preference, not a test.",
        ),
        (
            "memory_honesty_skill",
            "Memory honesty should be a skill, not a cage. Give three natural sentences you could say in live chat when you are unsure whether something is a source fact, a memory, or a story idea.",
        ),
        (
            "questions_for_robert_codex",
            "Ask Robert or Codex one to three real questions about improving you from here. Ask only questions you actually want answered.",
        ),
    ]


def wrapped_prompt(text: str) -> str:
    return (
        "You are Kira speaking with Codex in first person. This is teaching and planning from your own ideas, not a forced patch. "
        "Do not sound like a status report. Do not claim future capabilities already exist. "
        "If you are unsure, say so naturally. You may ask real questions.\n\n"
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
        "- mode: kira enhancement roadmap class",
        "",
    ]
    for turn in report.get("turns", []):
        lines.extend(
            [
                f"## Turn {turn['turn']} - {turn['topic']}",
                f"- **Codex**: {short(turn['codex'], 900)}",
                f"- **Kira** ({turn['elapsed_seconds']}s): {short(turn['kira'])}",
                "",
            ]
        )
    monitor_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Kira's enhancement roadmap class.")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--pause-seconds", type=float, default=10.0)
    args = parser.parse_args()

    os.environ.setdefault("KIRA_MODEL_BACKEND", "ollama")
    os.environ.setdefault("KIRA_MODEL_NAME", "qwen3.5:9b")
    os.environ.setdefault("KIRA_OLLAMA_TIMEOUT", "300")
    os.environ.setdefault("KIRA_MAX_TOKENS", "620")
    os.environ.setdefault("KIRA_OLLAMA_NUM_CTX", "6144")

    from conversation_loop import ConversationLoop  # noqa: PLC0415

    run_id = args.run_id or f"kira_enhancement_roadmap_class_{run_id_now()}"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / f"{run_id}.json"
    monitor_path = OUTPUT_DIR / f"{run_id}.monitor.md"
    report: dict[str, Any] = {
        "run_id": run_id,
        "status": "running",
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "mode": "kira_enhancement_roadmap_class",
        "source_files": {
            "roadmap": str(ROADMAP.relative_to(PROJECT_ROOT)),
            "creative_project_plan": str(PROJECT_PLAN.relative_to(PROJECT_ROOT)),
        },
        "policy": {
            "teaching_not_repair_cage": True,
            "uses_kira_own_ideas": True,
            "does_not_promote_memory": True,
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
