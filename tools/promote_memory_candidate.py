"""
Promote a validated memory promotion candidate into Kira/Lisa memory storage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from memory_manager import MemoryManager  # noqa: E402
from validate_memory_promotion_candidate import validate_candidate  # noqa: E402


def build_memory_from_candidate(candidate: dict) -> dict:
    owner = candidate["owner"]
    if owner == "shared":
        owner = "kira"

    manager = MemoryManager(memory_file=str(PROJECT_ROOT / "Data" / f"memories_{owner}.json"))
    privacy = candidate.get("privacy", {})
    source = candidate.get("source", {})
    importance = candidate.get("importance", {})
    emotional = candidate.get("emotional_context", {})

    memory = manager.build_memory(
        summary=candidate["summary"],
        detail=candidate["detail"],
        owner=owner,
        participants=candidate.get("participants", ["user", owner]),
        memory_type=candidate.get("memory_type", "conversation"),
        core_facts=candidate.get("core_facts", []),
        emotional_context={
            "primary_emotion": emotional.get("primary_emotion", "neutral"),
            "intensity": emotional.get("intensity", 0.0),
            "residue": emotional.get("residue", 0.0),
        },
        importance_weight=importance.get("weight", "medium"),
        importance_score=importance.get("score", 0.5),
        tags=["conversation_promotion", "explicitly_promoted"],
        private=privacy.get("level") in {"private", "private_shared", "locked"},
    )
    memory["known_unknowns"] = candidate.get("known_unknowns", [])
    memory["forbidden_inferences"] = candidate.get("forbidden_inferences", [])
    memory["privacy"] = privacy
    memory["source"] = {
        "type": source.get("type", "conversation_promotion_candidate"),
        "path": source.get("path", ""),
        "confidence": source.get("confidence", 0.8),
        "candidate_id": candidate.get("candidate_id", ""),
    }
    memory["status"] = "approved"
    return memory


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote a memory candidate.")
    parser.add_argument("path", help="Path to candidate JSON.")
    args = parser.parse_args()

    path = Path(args.path)
    candidate = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_candidate(candidate)
    if errors:
        print(f"{path} is not ready for promotion:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    owner = candidate["owner"]
    if owner == "shared":
        owners = ["kira", "lisa"]
    else:
        owners = [owner]

    promoted_ids = []
    for target_owner in owners:
        target = dict(candidate)
        target["owner"] = target_owner
        manager = MemoryManager(
            memory_file=str(PROJECT_ROOT / "Data" / f"memories_{target_owner}.json")
        )
        memory = build_memory_from_candidate(target)
        manager.add_memory(memory)
        promoted_ids.append(memory["memory_id"])

    candidate["status"] = "promoted"
    path.write_text(json.dumps(candidate, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Promoted candidate {candidate['candidate_id']}: {', '.join(promoted_ids)}")


if __name__ == "__main__":
    main()
