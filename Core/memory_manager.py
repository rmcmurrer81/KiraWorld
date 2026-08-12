"""
memory_manager.py
Kira Project — Phase 1 Core File

Handles storage, retrieval, and lightweight scoring of memories.
Phase 1 uses JSON file storage only.
Vector DB / SQLite upgrade is deferred to a later phase.

Source documents:
  - Memory_System_v1_Engineering_Spec.docx
  - MEMORY_OBJECT_SCHEMA_TEMPLATE_v1.pdf
  - MEMORY_DETAIL_GENERATION_RULES_v1.pdf
  - MEMORY AS PERSPECTIVE (FOUNDATIONAL RULE).pdf

Core rules enforced here:
  - Memory must be retrieved BEFORE response generation
  - Memory must be written AFTER response
  - No hallucinated memory allowed
  - Each memory is owned by one entity (kira or lisa)
  - Core facts are locked; interpretation is flexible
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class MemoryManager:
    def __init__(self, memory_file: str = "data/memories.json") -> None:
        self.memory_path = Path(memory_file)
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.memory_path.exists():
            self._write_memories([])

    # ------------------------------------------------------------------
    # Internal read / write
    # ------------------------------------------------------------------

    def _read_memories(self) -> List[Dict[str, Any]]:
        with self.memory_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write_memories(self, memories: List[Dict[str, Any]]) -> None:
        with self.memory_path.open("w", encoding="utf-8") as f:
            json.dump(memories, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Memory creation
    # ------------------------------------------------------------------

    def build_memory(
        self,
        summary: str,
        detail: str = "",
        owner: str = "kira",
        participants: Optional[List[str]] = None,
        memory_type: str = "conversation",
        core_facts: Optional[List[str]] = None,
        emotional_context: Optional[Dict[str, Any]] = None,
        importance_weight: str = "medium",
        importance_score: float = 0.5,
        tags: Optional[List[str]] = None,
        private: bool = False,
    ) -> Dict[str, Any]:
        """
        Constructs a memory object conforming to MEMORY_OBJECT_SCHEMA_TEMPLATE_v1.
        Caller should pass this to add_memory() to persist it.

        memory_type options (Phase 1):
          conversation | event | reflection | insight | relationship | dream | idle_thought
        """
        return {
            "memory_id": f"mem_{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now().isoformat(),
            "memory_type": memory_type,
            "owner": owner,
            "participants": participants or [owner],
            "summary": summary,
            "detail": detail,
            "core_facts": core_facts or [],
            "interpretation": {
                "meaning": "",
                "confidence": 0.0,
            },
            "emotional_context": emotional_context or {
                "primary_emotion": "neutral",
                "intensity": 0.0,
                "residue": 0.0,
            },
            "importance": {
                "weight": importance_weight,
                "score": importance_score,
            },
            "tags": tags or [],
            "source": "conversation",
            "private": private,
        }

    def add_memory(self, memory: Dict[str, Any]) -> None:
        """Appends a memory object to the store."""
        memories = self._read_memories()
        memories.append(memory)
        self._write_memories(memories)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_recent_memories(
        self,
        limit: int = 10,
        owner: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Returns the most recent memories, optionally filtered by owner.
        Used for recency-based context building.
        """
        memories = self._read_memories()
        if owner:
            memories = [m for m in memories if m.get("owner") == owner]
        return memories[-limit:]

    def retrieve_relevant_memories(
        self,
        query: str,
        owner: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Phase 1 retrieval: lightweight keyword overlap + importance weighting.

        Scoring factors (Phase 1):
          - keyword overlap with summary, detail, tags, core_facts
          - importance score bonus

        Replace or augment later with vector/semantic retrieval.

        Per MEMORY AS PERSPECTIVE rule: retrieval is owner-aware.
        Private memories are excluded unless owner matches.
        """
        memories = self._read_memories()

        # Filter by owner and privacy
        if owner:
            memories = [
                m for m in memories
                if m.get("owner") == owner or not m.get("private", False)
            ]

        query_terms = set(query.lower().split())
        scored: List[tuple[float, Dict[str, Any]]] = []

        for memory in memories:
            # Build searchable text from key fields
            searchable = " ".join([
                str(memory.get("summary", "")),
                str(memory.get("detail", "")),
                " ".join(memory.get("tags", [])),
                " ".join(memory.get("core_facts", [])),
            ]).lower()

            keyword_score = sum(1 for term in query_terms if term in searchable)
            if keyword_score == 0:
                continue

            # Bonus for higher importance
            importance_score = memory.get("importance", {}).get("score", 0.5)
            total_score = keyword_score + (importance_score * 0.5)

            scored.append((total_score, memory))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:limit]]

    def get_high_significance_memories(
        self,
        owner: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Returns memories with importance weight of 'high'.
        Used for milestone and relationship-critical retrieval.
        Per Memory System spec: high-significance memories resist compression.
        """
        memories = self._read_memories()
        if owner:
            memories = [m for m in memories if m.get("owner") == owner]
        high = [
            m for m in memories
            if m.get("importance", {}).get("weight") == "high"
        ]
        # Return most recent high-significance memories
        return high[-limit:]

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def count_memories(self, owner: Optional[str] = None) -> int:
        memories = self._read_memories()
        if owner:
            memories = [m for m in memories if m.get("owner") == owner]
        return len(memories)
