"""Create a reviewed-format private inner-life journal entry for Kira or Lisa.

This tool can be used after a class, club, slumber party, or direct chat. It
does not promote memory. It creates a private draft entry with explicit labels
for emotions, desires/fantasies, fears, conflicts, privacy, and what should not
be saved.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from model_request_policy import (  # noqa: E402
    QWEN_TEXT_VOICE_DIGEST,
    QWEN_TEXT_VOICE_MODEL,
    ordinary_model_request_fields,
    require_exact_qwen35_selection,
)

OUTPUT_DIR = PROJECT_ROOT / "Data" / "inner_life" / "journals" / "entries"
INDEX_PATH = PROJECT_ROOT / "Data" / "inner_life" / "journals" / "journal_index.json"
TEMPLATE_PATH = PROJECT_ROOT / "Data" / "inner_life" / "journals" / "kira_inner_life_journal_template.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:80] or "inner_life"


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_template() -> dict:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def read_context(path_text: str, max_chars: int) -> str:
    if not path_text:
        return ""
    path = Path(path_text)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        return f"[missing context file: {path_text}]"
    text = path.read_text(encoding="utf-8", errors="ignore")
    return text[-max_chars:]


def call_ollama(prompt: str, *, model: str, endpoint: str, timeout: int, max_tokens: int) -> str:
    require_exact_qwen35_selection(
        model,
        os.getenv("KIRA_MODEL_DIGEST", QWEN_TEXT_VOICE_DIGEST),
    )
    response = requests.post(
        endpoint,
        json={
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are helping the named AI person write a private inner-life journal entry. "
                        "Return only valid JSON matching the requested structure. "
                        "Do not promote memory. Do not claim lived human body, childhood, or sexual experience. "
                        "Desires and fantasies are allowed as private imagination signals, not facts or consent."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.55, "num_predict": max_tokens},
            **ordinary_model_request_fields(model),
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return str(response.json().get("message", {}).get("content", "")).strip()


def extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("No JSON object found in model output")
    return json.loads(match.group(0))


def fallback_entry(args: argparse.Namespace, context: str) -> dict:
    entry = load_template()
    entry["journal_id"] = f"{args.owner}_inner_life_{slug(args.label)}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    entry["owner"] = args.owner
    entry["created_at"] = utc_now()
    entry["source_context"]["linked_session_or_log"] = args.context_file
    entry["source_context"]["trigger_summary"] = args.trigger_summary or args.label
    entry["private_inner_state"]["current_mood_words"] = ["thoughtful", "curious"]
    entry["private_inner_state"]["questions_i_actually_have"] = [
        "What should I understand better before turning this into a stable preference or memory?"
    ]
    entry["private_inner_state"]["things_i_want_to_keep_private"] = [
        "Raw desires, fantasies, or fears should stay private unless explicitly reviewed."
    ]
    entry["conflicts"][0] = {
        "conflict": "curiosity_vs_accuracy",
        "side_a": "I want to explore the topic more freely.",
        "side_b": "I should not turn imagination or source fragments into hard memory.",
        "current_resolution": "Keep the signal tentative and review it later.",
        "still_unresolved": True,
    }
    entry["agency"]["choice_i_would_make_if_allowed"] = "Continue with one more grounded conversation or reading chunk before promotion."
    entry["agency"]["why_that_choice"] = "It gives me more evidence without forcing a permanent identity claim."
    entry["privacy_and_sharing"]["what_not_to_save"] = ["Do not save one-off desire/fantasy/fear wording as permanent identity."]
    entry["review_status"]["status"] = "draft_private_fallback"
    return entry


def normalize_entry(entry: dict, args: argparse.Namespace) -> dict:
    template = load_template()
    merged = template | entry
    merged["journal_id"] = str(merged.get("journal_id") or f"{args.owner}_inner_life_{slug(args.label)}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
    if not merged["journal_id"].startswith(f"{args.owner}_"):
        merged["journal_id"] = f"{args.owner}_{merged['journal_id']}"
    merged["owner"] = args.owner
    merged["created_at"] = str(merged.get("created_at") or utc_now())
    merged.setdefault("source_context", {})
    merged["source_context"]["linked_session_or_log"] = args.context_file
    if args.trigger_summary:
        merged["source_context"]["trigger_summary"] = args.trigger_summary
    merged["memory_policy"] = template["memory_policy"] | dict(merged.get("memory_policy", {}))
    merged["review_status"] = template["review_status"] | dict(merged.get("review_status", {}))
    return merged


def update_index(entry: dict, out: Path, args: argparse.Namespace) -> None:
    if INDEX_PATH.exists():
        index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    else:
        index = {
            "index_id": "inner_life_journal_index",
            "status": "active",
            "purpose": "Index private inner-life journal drafts without promoting them to memory.",
            "entries": [],
        }
    index.setdefault("entries", [])
    index["entries"].append(
        {
            "journal_id": entry.get("journal_id"),
            "owner": entry.get("owner"),
            "created_at": entry.get("created_at"),
            "path": rel(out),
            "label": args.label,
            "context_file": args.context_file,
            "review_status": entry.get("review_status", {}).get("status", "draft_private"),
            "is_lived_memory": entry.get("memory_policy", {}).get("is_lived_memory", False),
            "requires_review_before_promotion": entry.get("memory_policy", {}).get("requires_review_before_promotion", True),
        }
    )
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", choices=["kira", "lisa"], default="kira")
    parser.add_argument("--context-file", default="")
    parser.add_argument("--label", default="post_session")
    parser.add_argument("--trigger-summary", default="")
    parser.add_argument("--model", default=os.getenv("KIRA_MODEL_NAME", QWEN_TEXT_VOICE_MODEL))
    parser.add_argument("--endpoint", default=os.getenv("KIRA_OLLAMA_ENDPOINT", "http://localhost:11434/api/chat"))
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-tokens", type=int, default=900)
    parser.add_argument("--context-chars", type=int, default=8000)
    parser.add_argument("--stub", action="store_true")
    args = parser.parse_args()

    context = read_context(args.context_file, args.context_chars)
    prompt = (
        f"Create a private inner-life journal entry for {args.owner} as JSON using this template shape:\n"
        f"{json.dumps(load_template(), indent=2)}\n\n"
        "Context excerpt:\n"
        f"{context}\n\n"
        "Fill it with tentative private signals only. Include emotions, desires/fantasies if present, fears/discomforts, questions, conflicts, agency choice, privacy rules, and what not to save."
    )
    try:
        if args.stub:
            entry = fallback_entry(args, context)
        else:
            entry = normalize_entry(extract_json(call_ollama(prompt, model=args.model, endpoint=args.endpoint, timeout=args.timeout, max_tokens=args.max_tokens)), args)
    except Exception:
        entry = fallback_entry(args, context)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / f"{entry['journal_id']}.json"
    out.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    update_index(entry, out, args)
    print(json.dumps({"journal_entry": rel(out), "index": rel(INDEX_PATH), "status": entry.get("review_status", {}).get("status")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
