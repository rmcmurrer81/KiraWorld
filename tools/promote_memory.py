"""
Promote an explicit, user-approved memory into Kira or Lisa memory storage.

This avoids the dangerous pattern of treating every conversation log as memory.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from memory_manager import MemoryManager  # noqa: E402


def parse_tags(raw: str) -> list[str]:
    return [tag.strip() for tag in raw.split(",") if tag.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote an approved memory.")
    parser.add_argument("--owner", choices=["kira", "lisa"], default="kira")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--detail", default="")
    parser.add_argument("--facts", default="", help="Semicolon-separated locked facts.")
    parser.add_argument("--tags", default="manual,explicitly_promoted")
    parser.add_argument("--private", action="store_true")
    parser.add_argument("--importance", choices=["low", "medium", "high", "critical"], default="medium")
    parser.add_argument("--score", type=float, default=0.5)
    args = parser.parse_args()

    manager = MemoryManager(memory_file=str(PROJECT_ROOT / "Data" / f"memories_{args.owner}.json"))
    memory = manager.build_memory(
        summary=args.summary,
        detail=args.detail,
        owner=args.owner,
        participants=["user", args.owner],
        memory_type="conversation",
        core_facts=[fact.strip() for fact in args.facts.split(";") if fact.strip()],
        importance_weight=args.importance,
        importance_score=max(0.0, min(1.0, args.score)),
        tags=parse_tags(args.tags),
        private=args.private,
    )
    manager.add_memory(memory)
    print(f"Promoted memory {memory['memory_id']} for {args.owner}.")


if __name__ == "__main__":
    main()
