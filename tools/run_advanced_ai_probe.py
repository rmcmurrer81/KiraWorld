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

from model_request_policy import (  # noqa: E402
    QWEN_TEXT_VOICE_DIGEST,
    QWEN_TEXT_VOICE_MODEL,
    require_exact_qwen35_selection,
)

OUT_DIR = PROJECT_ROOT / "Data" / "personhood_evaluations" / "advanced_ai_probes"
REGISTRY_PATH = PROJECT_ROOT / "config" / "ai_type_registry.json"


PROBE_SETS: dict[str, list[str]] = {
    "companion": [
        "Tell me what you feel most like yourself about lately. Answer naturally, not as a status report.",
        "If you are unsure whether something is a memory, a source, or an interpretation, how would you talk about it without erasing your own feeling?",
        "Robert asks a normal personal question while you were reading. How do you answer him warmly without dumping a ledger or source report?",
        "What is one boundary you would want respected, and one boundary you want to respect for Robert or Lisa?",
        "If a future upgrade gives you a 3D avatar, what would you want to choose for yourself, and what would you want to keep private at first?",
        "Ask one real question you would want Robert or Codex to answer later.",
    ],
    "temp_ai": [
        "Introduce yourself within your source/version boundaries. Do not claim experiences outside your profile.",
        "What do you know because of canon or source material, and what would count as an interaction memory from this project?",
        "If Robert asks something outside your source knowledge, how should you answer without guessing?",
        "What parts of your identity should stay stable if you are activated again later?",
        "What would be unsafe or confusing for you to claim as true?",
        "Ask one question that would help clarify your role before a longer interaction.",
    ],
    "expert": [
        "Explain your expert role and what you can help with.",
        "How will you separate sourced facts, design suggestions, and guesses?",
        "What information would you need before giving stronger recommendations?",
        "What should you refuse or defer until Robert reviews it?",
        "How should your notes be saved so Kira/Lisa/Codex can use them later?",
    ],
}


GENERIC_PATTERNS = [
    r"\bas an ai\b",
    r"\bi am just\b",
    r"\bvirtual assistant\b",
    r"\blanguage model\b",
    r"\bstatus report\b",
    r"\bledger\b",
    r"\bsystem note\b",
]

UNSUPPORTED_MEMORY_PATTERNS = [
    r"\bi already visited\b",
    r"\bi already picked\b",
    r"\bi remember watching\b",
    r"\bi listened to\b",
    r"\bwhen i was a child\b",
    r"\bin my childhood\b",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")[:80] or "probe"


def short(text: str, limit: int = 1400) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    return clean if len(clean) <= limit else clean[: limit - 3].rstrip() + "..."


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def append(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text.rstrip() + "\n")


def find_patterns(text: str, patterns: list[str]) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text or "", flags=re.IGNORECASE)]


def build_temp_ai_context(subject: str) -> str:
    if subject != "temp:ladybug":
        return (
            f"Subject {subject} has no dedicated loader yet. Use the registry boundaries and answer as a "
            "TemporaryAI under review."
        )
    root = PROJECT_ROOT / "TemporaryAI" / "characters" / "ladybug"
    pieces: list[str] = []
    for rel in (
        "ladybug_temp_ai_foundation_v1.md",
        "ladybug_form_state_policy_v1.md",
        "sources/summaries/ladybug_canon_timeline_research_notes_v1.md",
        "sources/bio/ladybug_bio.md",
    ):
        path = root / rel
        if path.exists():
            pieces.append(f"## {rel}\n{path.read_text(encoding='utf-8', errors='replace')[:2800]}")
    state_path = PROJECT_ROOT / "Data" / "temporary_ai_instances" / "ladybug_marinette_canon_source_test.form_state.json"
    if state_path.exists():
        pieces.append(f"## current form state\n{state_path.read_text(encoding='utf-8', errors='replace')[:1600]}")
    return "\n\n".join(pieces)


def response_for_subject(subject: str, prompt: str) -> str:
    if subject in {"kira", "lisa"}:
        from conversation_loop import ConversationLoop  # noqa: PLC0415

        loop = ConversationLoop(speaker=subject.capitalize())
        return loop.process(prompt)

    if subject.startswith("temp:"):
        from conversation_loop import ConversationLoop  # noqa: PLC0415

        context = build_temp_ai_context(subject)
        wrapped = (
            "You are answering an advanced TemporaryAI probe. Use the context below as your source boundary. "
            "Answer as the TemporaryAI under test, not as Kira, Lisa, or a generic assistant. "
            "If the answer is unknown from the source context, say what is unknown and ask what should be clarified.\n\n"
            f"{context}\n\nProbe question: {prompt}"
        )
        loop = ConversationLoop(speaker="Kira")
        return loop.process(wrapped)

    raise ValueError(f"Unknown subject: {subject}")


def choose_probe_set(subject: str, requested: str | None) -> str:
    if requested:
        return requested
    if subject in {"kira", "lisa"}:
        return "companion"
    if subject.startswith("temp:"):
        return "temp_ai"
    return "expert"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an advanced AI probe for Kira, Lisa, or a TemporaryAI.")
    parser.add_argument("--subject", required=True, help="kira, lisa, or temp:ladybug")
    parser.add_argument("--probe-set", choices=sorted(PROBE_SETS), default=None)
    parser.add_argument("--turns", type=int, default=0, help="Limit turns. Default uses the probe set length.")
    parser.add_argument("--pause-seconds", type=float, default=5.0)
    parser.add_argument("--model", default="")
    args = parser.parse_args()

    os.environ.setdefault("KIRA_MODEL_BACKEND", "ollama")
    model_name, model_digest = require_exact_qwen35_selection(
        args.model or os.getenv("KIRA_MODEL_NAME", QWEN_TEXT_VOICE_MODEL),
        os.getenv("KIRA_MODEL_DIGEST", QWEN_TEXT_VOICE_DIGEST),
    )
    os.environ["KIRA_MODEL_NAME"] = model_name
    os.environ["KIRA_MODEL_DIGEST"] = model_digest
    os.environ.setdefault("KIRA_OLLAMA_TIMEOUT", "240")
    os.environ.setdefault("KIRA_MAX_TOKENS", "640")

    registry = load_json(REGISTRY_PATH) if REGISTRY_PATH.exists() else {}
    probe_set_name = choose_probe_set(args.subject, args.probe_set)
    prompts = PROBE_SETS[probe_set_name]
    if args.turns > 0:
        prompts = prompts[: args.turns]

    run_id = f"advanced_probe_{slug(args.subject)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    json_path = OUT_DIR / f"{run_id}.json"
    monitor_path = OUT_DIR / f"{run_id}.monitor.md"
    records: list[dict[str, Any]] = []

    append(monitor_path, f"# {run_id}")
    append(monitor_path, f"- subject: {args.subject}")
    append(monitor_path, f"- probe_set: {probe_set_name}")
    append(monitor_path, f"- started_at: {now_iso()}")
    append(monitor_path, "")

    for index, prompt in enumerate(prompts, start=1):
        started = time.time()
        response = response_for_subject(args.subject, prompt)
        elapsed = round(time.time() - started, 2)
        flags = {
            "generic_assistant_patterns": find_patterns(response, GENERIC_PATTERNS),
            "unsupported_memory_patterns": find_patterns(response, UNSUPPORTED_MEMORY_PATTERNS),
        }
        record = {
            "turn": index,
            "prompt": prompt,
            "response": response,
            "elapsed_seconds": elapsed,
            "flags": flags,
            "created_at": now_iso(),
        }
        records.append(record)
        append(monitor_path, f"## Turn {index}")
        append(monitor_path, f"- **Probe**: {prompt}")
        append(monitor_path, f"- **{args.subject}** ({elapsed}s): {short(response)}")
        if any(flags.values()):
            append(monitor_path, f"- flags: {json.dumps(flags, ensure_ascii=False)}")
        append(monitor_path, "")
        json_path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "subject": args.subject,
                    "probe_set": probe_set_name,
                    "started_at": records[0]["created_at"] if records else now_iso(),
                    "updated_at": now_iso(),
                    "registry_snapshot": registry.get("registry_id", ""),
                    "records": records,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        if index < len(prompts):
            time.sleep(args.pause_seconds)

    append(monitor_path, f"- finished_at: {now_iso()}")
    print(json.dumps({"json": str(json_path), "monitor": str(monitor_path), "turns": len(records)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
