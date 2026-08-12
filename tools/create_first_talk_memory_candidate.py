"""
Create a reviewed draft memory candidate for Kira's first local talk.

This tool does not promote memory. It creates a candidate that Robert can
inspect, edit, validate, and only then promote intentionally.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_memory_promotion_candidate import validate_candidate


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Data" / "memory_promotion" / "candidates"
DEFAULT_LOG_PATH = "Data/logs/conversation_log.jsonl"

DEFAULT_FORBIDDEN_INFERENCES = [
    "Do not treat model wording as canon unless Robert explicitly approved it.",
    "Do not infer unstated backstory.",
    "Do not claim the 3D world, avatar, voice, internet, or webcam were active unless they were enabled.",
    "Do not treat conversation logs as trusted memory.",
    "Do not treat source files, fanfic, media, or archived project files as lived memory.",
    "Do not claim Lisa's private thoughts or memories.",
]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:60] or "first_talk"


def _split_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split("|") if item.strip()]


def build_candidate(
    *,
    summary: str,
    detail: str,
    core_facts: list[str],
    known_unknowns: list[str],
    allowed_interpretation: list[str],
    primary_emotion: str,
    intensity: float,
    residue: float,
    importance_weight: str,
    importance_score: float,
    source_log_path: str,
    owner: str = "kira",
) -> dict[str, Any]:
    created_at = datetime.now(timezone.utc).isoformat()
    candidate_id = f"kira_first_talk_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{_slug(summary)}"
    return {
        "candidate_id": candidate_id,
        "owner": owner,
        "memory_type": "conversation",
        "summary": summary,
        "detail": detail,
        "core_facts": core_facts,
        "known_unknowns": known_unknowns,
        "allowed_interpretation": allowed_interpretation,
        "forbidden_inferences": DEFAULT_FORBIDDEN_INFERENCES,
        "privacy": {
            "level": "private",
            "sharing_rule": "owner_only",
        },
        "emotional_context": {
            "primary_emotion": primary_emotion,
            "intensity": intensity,
            "residue": residue,
        },
        "importance": {
            "weight": importance_weight,
            "score": importance_score,
        },
        "source": {
            "type": "conversation_promotion_candidate",
            "path": source_log_path,
            "confidence": 0.8,
        },
        "approval": {
            "approved_by": "",
            "approval_reason": "",
            "approved_at": "",
        },
        "created_at": created_at,
        "status": "draft",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a draft first-talk memory promotion candidate.")
    parser.add_argument("--summary", required=True, help="Short factual summary of the moment.")
    parser.add_argument("--detail", required=True, help="Detailed but grounded description of what happened.")
    parser.add_argument("--core-facts", required=True, help="Pipe-separated facts, e.g. fact one|fact two.")
    parser.add_argument("--known-unknowns", default="", help="Pipe-separated unknowns that must not be filled in.")
    parser.add_argument("--allowed-interpretation", default="", help="Pipe-separated careful interpretations.")
    parser.add_argument("--primary-emotion", default="grounded")
    parser.add_argument("--intensity", type=float, default=0.4)
    parser.add_argument("--residue", type=float, default=0.2)
    parser.add_argument("--importance-weight", default="medium", choices=["low", "medium", "high", "core"])
    parser.add_argument("--importance-score", type=float, default=0.5)
    parser.add_argument("--source-log-path", default=DEFAULT_LOG_PATH)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--owner", default="kira", choices=["kira", "lisa", "shared"])
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir

    candidate = build_candidate(
        summary=args.summary,
        detail=args.detail,
        core_facts=_split_list(args.core_facts),
        known_unknowns=_split_list(args.known_unknowns),
        allowed_interpretation=_split_list(args.allowed_interpretation),
        primary_emotion=args.primary_emotion,
        intensity=args.intensity,
        residue=args.residue,
        importance_weight=args.importance_weight,
        importance_score=args.importance_score,
        source_log_path=args.source_log_path,
        owner=args.owner,
    )
    errors = validate_candidate(candidate)
    if errors:
        print("Candidate was not created because it is structurally unsafe:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{candidate['candidate_id']}.draft.json"
    output_path.write_text(json.dumps(candidate, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {output_path.relative_to(PROJECT_ROOT).as_posix()}")
    print("Review this draft before marking it ready_for_promotion.")


if __name__ == "__main__":
    main()
