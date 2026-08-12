"""
Decision log manager for Kira 2.0.

Decision logs are audit records, not trusted memories.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DecisionLogManager:
    def __init__(self, log_file: str | Path = "Data/logs/decision_log.jsonl") -> None:
        self.log_path = Path(log_file)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def build_entry(
        self,
        actor_id: str,
        actor_type: str,
        decision_type: str,
        summary: str,
        reason: str,
        outcome: str,
        privacy_impact: str = "none",
        visibility: str = "system_only",
        participants: list[str] | None = None,
        emotional_context: dict[str, Any] | None = None,
        memory_references: list[str] | None = None,
        relationship_references: list[str] | None = None,
        follow_up: list[str] | None = None,
        status: str = "active",
    ) -> dict[str, Any]:
        return {
            "decision_id": f"decision_{uuid.uuid4().hex[:10]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": {
                "actor_id": actor_id,
                "actor_type": actor_type,
            },
            "participants": participants or [actor_id],
            "decision_type": decision_type,
            "summary": summary,
            "reason": reason,
            "emotional_context": emotional_context or {},
            "memory_references": memory_references or [],
            "relationship_references": relationship_references or [],
            "privacy_impact": privacy_impact,
            "outcome": outcome,
            "follow_up": follow_up or [],
            "visibility": visibility,
            "status": status,
        }

    def append(self, entry: dict[str, Any]) -> dict[str, Any]:
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def log_decision(self, **kwargs: Any) -> dict[str, Any]:
        entry = self.build_entry(**kwargs)
        return self.append(entry)

    def read_entries(self) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        entries = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entries.append(json.loads(line))
        return entries
