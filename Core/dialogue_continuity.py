"""Review-required continuity candidates for Kira/Robert dialogue sessions."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _topics(turns: list[dict[str, Any]]) -> list[str]:
    text = " ".join(str(item.get("spoken") or "") for item in turns).lower()
    candidates = {
        "consent_and_boundaries": r"\bconsent\b|\bboundar",
        "community_and_belonging": r"\bcommunity\b|\bbelong",
        "newark_places": r"\bnewark\b",
        "art_and_museums": r"\bart\b|\bmuseum",
        "cafes_and_food": r"\bcafe\b|\bcoffee\b|\bfood\b",
        "world_planning": r"kira world|\bworld\b",
    }
    return [name for name, pattern in candidates.items() if re.search(pattern, text)]


def build_continuity_candidate(
    report: dict[str, Any],
    *,
    source_path: Path,
    source_context_contamination_count: int,
) -> dict[str, Any]:
    turns = [item for item in (report.get("transcript") or []) if isinstance(item, dict)]
    warnings = [warning for item in turns for warning in (item.get("warnings") or [])]
    eligible = (
        report.get("status") == "complete"
        and bool(report.get("target_reached"))
        and source_context_contamination_count == 0
        and not warnings
    )
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "review_required_not_promoted",
        "source_dialogue": str(source_path),
        "source_dialogue_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "dialogue_id": report.get("dialogue_id"),
        "turn_count": len(turns),
        "topics_detected_from_public_spoken_text": _topics(turns),
        "public_summary": (
            "Kira and the autonomous Robert variant held a generated text dialogue touching the listed topics. "
            "This is dialogue history, not a physical lived event, and it is not durable memory until reviewed."
        ),
        "private_mind_included": False,
        "source_context_contamination_count": source_context_contamination_count,
        "warnings_count": len(warnings),
        "eligible_for_human_review": eligible,
        "promotion_allowed": False,
        "required_before_promotion": [
            "Robert reviews the public summary",
            "privacy boundary audit passes",
            "identity and false-memory claims are reviewed",
            "an approved copy is written separately with status approved_shared_continuity",
        ],
    }


def write_continuity_candidate(report: dict[str, Any], *, source_path: Path, project_root: Path, contamination_count: int) -> Path:
    folder = project_root / "Data" / "dialogues" / "kira_robert_intro" / "continuity_candidates"
    folder.mkdir(parents=True, exist_ok=True)
    value = build_continuity_candidate(
        report,
        source_path=source_path,
        source_context_contamination_count=contamination_count,
    )
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    path = folder / f"{source_path.stem}.continuity_candidate.sha256-{digest}.json"
    created = False
    try:
        try:
            with path.open("xb") as handle:
                created = True
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            if path.read_bytes() != payload:
                raise RuntimeError(
                    f"Refusing to replace non-identical hash-addressed continuity candidate: {path}"
                )
    except Exception:
        # Never alter a pre-existing candidate.  Clean up only a partial file
        # exclusively created by this invocation.
        if created:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        raise
    return path
