"""Shared three-channel turn and action-result ledger for every person type.

Only ``spoken`` is suitable for display or TTS.  Private mind and runtime truth
are persisted as separate evidence and never folded back into public dialogue.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

from Core.candidate_movement_intents import prepare_and_record_candidate_reply


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TURN_ROOT = PROJECT_ROOT / "Data" / "runtime" / "person_mind_turns"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def finalize_person_turn(
    *,
    person_id: str,
    person_label: str,
    raw_reply: str,
    source_turn_id: str,
    body_active: bool = False,
    activity_controller_active: bool = False,
    turn_root: Path | None = None,
    movement_state_dir: Path | None = None,
    movement_audit_path: Path | None = None,
) -> dict[str, Any]:
    """Separate speech, persist intentions, and record honest execution results."""
    created_at = _now()
    prepared = prepare_and_record_candidate_reply(
        person_id,
        person_label,
        raw_reply,
        source_turn_id=source_turn_id,
        source_at=created_at,
        state_dir=movement_state_dir,
        audit_path=movement_audit_path,
    )
    action_requests = prepared.get("recorded", [])
    action_results: list[dict[str, Any]] = []
    for request in action_requests:
        category = request.get("category")
        can_attempt = activity_controller_active if category == "activity_control" else body_active
        action_results.append(
            {
                "request_id": request.get("record_id"),
                "action": request.get("action"),
                "status": "blocked_no_active_controller" if not can_attempt else "queued_for_runtime_confirmation",
                "attempted": False,
                "completed": False,
                "physical_completion_claimed": False,
            }
        )

    spoken = str(prepared.get("spoken_text") or "").strip()
    payload = {
        "schema_version": "person_mind_turn_v1",
        "turn_id": source_turn_id,
        "created_at": created_at,
        "person": {"person_id": person_id, "display_name": person_label},
        "channels": {
            "spoken": spoken,
            "private_mind": {
                "content": None,
                "visibility": "private_not_generated_by_public_chat",
                "included_in_spoken": False,
            },
            "runtime_truth": {
                "raw_reply_sha256": hashlib.sha256(raw_reply.encode("utf-8")).hexdigest(),
                "spoken_sha256": hashlib.sha256(spoken.encode("utf-8")).hexdigest(),
                "action_requests": action_requests,
                "action_results": action_results,
                "body_active": body_active,
                "activity_controller_active": activity_controller_active,
            },
        },
        "display_contract": {"display_channel": "spoken", "tts_channel": "spoken"},
    }
    root = turn_root or DEFAULT_TURN_ROOT
    path = root / person_id / f"{source_turn_id}.json"
    _atomic_json(path, payload)
    payload["evidence_path"] = str(path)
    return payload
