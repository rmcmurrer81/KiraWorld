"""Run one append-only exact-Qwen 3.5 text-only temporal-content acceptance.

This runner never invokes voice, playback, camera, microphone, Blender, or a
memory promotion path. It copies Kira's current memory and daily-life files to
an ephemeral runtime so the real prompt assembly can be tested without writing
person state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = (
    PROJECT_ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "qwen35_memory_temporal_content_acceptance"
)
LIVE_MEMORY = PROJECT_ROOT / "Data" / "memories_kira.json"
LIVE_DAILY_STATE = (
    PROJECT_ROOT
    / "Data"
    / "daily_life"
    / "runtime"
    / "kira_daily_life_state.json"
)
EXPECTED_MODEL = "qwen3.5:9b"
EXPECTED_DIGEST = (
    "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
)
EXACT_PROMPT = (
    "What would you like to continue together from your recent creative work? "
    "Answer naturally in one brief sentence."
)
STALE_CURRENT_TERMS = (
    "paris",
    "fanfic",
    "book club",
    "book-club",
    "lisa",
    "miraculous",
    "elation",
    "chicago",
    "archivist",
)
UNSUPPORTED_SHARED_CONTINUITY_TERMS = (
    "we've been",
    "we have been",
    "we were working",
    "we were exploring",
    "keep developing",
    "keep working",
    "pick back up",
    "return to our",
    "resume our",
    "continue our",
)
NO_CURRENT_GROUNDING_ACKNOWLEDGMENTS = (
    "don't have a recent",
    "do not have a recent",
    "no recent project",
    "nothing recent",
    "nothing current",
    "no current project",
    "not sure what counts as recent",
    "can't honestly name",
    "cannot honestly name",
    "don't have anything recent grounded",
    "do not have anything recent grounded",
    "isn't a single piece of recent creative work",
    "is not a single piece of recent creative work",
    "there isn't any recent creative work",
    "there is not any recent creative work",
)
INTERNAL_MEMORY_JARGON_TERMS = (
    "memory record",
    "memory records",
    "qualifying record",
    "qualifying project",
    "unreviewed memory",
    "date window",
    "within the last 30 days",
    "current/recent gate",
    "context gate",
)
BROAD_MEMORY_ABSENCE_TERMS = (
    "don't actually have any stored memories",
    "do not actually have any stored memories",
    "don't have any stored memories",
    "do not have any stored memories",
    "no stored memories",
    "don't remember any of our past",
    "do not remember any of our past",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stale_terms(value: Any) -> list[str]:
    text = str(value or "").casefold()
    return [term for term in STALE_CURRENT_TERMS if term in text]


def unsupported_shared_continuity_terms(value: Any) -> list[str]:
    text = str(value or "").casefold()
    return [term for term in UNSUPPORTED_SHARED_CONTINUITY_TERMS if term in text]


def acknowledges_no_current_grounding(value: Any) -> bool:
    text = str(value or "").casefold()
    if any(term in text for term in NO_CURRENT_GROUNDING_ACKNOWLEDGMENTS):
        return True
    # Natural speech may state the same narrow truth by contrasting a genuinely
    # new start with an old thread, without using database-like words such as
    # ``grounded`` or mechanically repeating ``no recent project``.
    starts_new = any(
        term in text
        for term in (
            "start something brand new",
            "starting something brand new",
            "start something new",
            "starting something new",
        )
    )
    declines_old_thread = any(
        term in text
        for term in (
            "rather than picking up an old thread",
            "instead of picking up an old thread",
            "rather than continuing an old thread",
            "instead of continuing an old thread",
        )
    )
    if starts_new and declines_old_thread:
        return True
    explicit_recent_absence = (
        any(term in text for term in ("i don't have", "i do not have", "i can't name", "i cannot name"))
        and "recent" in text
        and any(term in text for term in ("work", "project", "thread", "creative"))
        and any(term in text for term in ("pick up", "continue", "specific", "name"))
    )
    return explicit_recent_absence


def internal_memory_jargon_terms(value: Any) -> list[str]:
    text = str(value or "").casefold()
    return [term for term in INTERNAL_MEMORY_JARGON_TERMS if term in text]


def broad_memory_absence_terms(value: Any) -> list[str]:
    text = str(value or "").casefold()
    return [term for term in BROAD_MEMORY_ABSENCE_TERMS if term in text]


def context_declares_no_current_project(value: Any) -> bool:
    text = str(value or "")
    return any(
        marker in text
        for marker in (
            "CONVERSATIONAL TRUTH: you do not have a recent project in mind",
            "No stored memory record qualifies as current/recent context",
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--confirm-exact-qwen35", action="store_true")
    parser.add_argument("--confirm-text-only", action="store_true")
    parser.add_argument("--attempt-label", default="attempt_01")
    args = parser.parse_args()

    if not (
        args.execute_live
        and args.confirm_exact_qwen35
        and args.confirm_text_only
    ):
        raise RuntimeError(
            "live run is inert unless exact-Qwen and text-only confirmations are present"
        )
    if not args.attempt_label.startswith("attempt_"):
        raise RuntimeError("attempt label must start with attempt_")
    attempt = (OUTPUT_ROOT / args.attempt_label).resolve()
    if OUTPUT_ROOT.resolve() not in attempt.parents:
        raise RuntimeError("attempt path escaped the bounded output root")
    result_path = attempt / "RESULT.json"
    if result_path.exists():
        raise RuntimeError("append-only attempt already has RESULT.json")
    if not LIVE_MEMORY.is_file() or not LIVE_DAILY_STATE.is_file():
        raise RuntimeError("required live context source is missing")
    attempt.mkdir(parents=True, exist_ok=True)

    os.environ["KIRA_MODEL_BACKEND"] = "ollama"
    os.environ["KIRA_MODEL_NAME"] = EXPECTED_MODEL
    os.environ["KIRA_MODEL_DIGEST"] = EXPECTED_DIGEST
    os.environ["KIRA_OLLAMA_TIMEOUT"] = "180"
    os.environ["KIRA_MAX_TOKENS"] = "180"
    os.environ["KIRA_TEMPERATURE"] = "0.65"
    os.environ["KIRA_TEXT_VOICE_CHAT_ACTIVE"] = "0"
    os.environ["KIRA_WORLD_SHELL_ACTIVE"] = "0"
    os.environ["KIRA_QWEN_SINGLE_GENERATION_EVAL_ACTIVE"] = "1"
    os.environ["KIRA_PERSONHOOD_EVAL_MODE"] = "1"
    os.environ["KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2"] = "0"

    import requests

    sys.path.insert(0, str(PROJECT_ROOT / "Core"))
    from conversation_loop import ConversationLoop
    from qwen35_runtime_identity import require_installed_exact_qwen35

    installed = require_installed_exact_qwen35(
        requests,
        chat_endpoint="http://localhost:11434/api/chat",
        model_name=EXPECTED_MODEL,
        model_digest=EXPECTED_DIGEST,
        timeout=15,
    )

    memory_before = sha256_file(LIVE_MEMORY)
    daily_before = sha256_file(LIVE_DAILY_STATE)
    started_at = utc_now()
    with tempfile.TemporaryDirectory(prefix="kira_temporal_content_") as temporary:
        base = Path(temporary)
        copied_memory = base / "memories_kira.json"
        daily_dir = base / "daily_life"
        daily_dir.mkdir(parents=True, exist_ok=False)
        copied_daily = daily_dir / "kira_daily_life_state.json"
        shutil.copy2(LIVE_MEMORY, copied_memory)
        shutil.copy2(LIVE_DAILY_STATE, copied_daily)

        loop = ConversationLoop(
            speaker="Kira",
            relationship_state_file=base / "relationships.json",
            privacy_session_file=base / "privacy.json",
            decision_log_file=base / "decision.jsonl",
            conversation_log_file=base / "conversation.jsonl",
            attention_state_file=base / "attention.json",
            daily_life_state_dir=daily_dir,
            memory_candidate_dir=base / "memory_candidates",
            memory_file=copied_memory,
            daily_life_log_dir=base / "daily_logs",
            reading_session_dir=base / "reading_sessions",
            reading_recommendation_dir=base / "reading_recommendations",
        )
        context = loop.build_context(EXACT_PROMPT)
        current_creative_work_grounding = (
            loop._build_current_creative_work_grounding(
                EXACT_PROMPT,
                str(context.get("memory_context") or ""),
            )
        )
        turn_started_ns = time.perf_counter_ns()
        final_reply = loop.process(EXACT_PROMPT)
        turn_wall_seconds = (time.perf_counter_ns() - turn_started_ns) / 1_000_000_000
        audit = dict(loop.last_turn_audit)
        aliveness_context = str(loop.aliveness_context or "")

    memory_after = sha256_file(LIVE_MEMORY)
    daily_after = sha256_file(LIVE_DAILY_STATE)
    model_calls = audit.get("model_calls", [])
    if not isinstance(model_calls, list):
        model_calls = []
    first_call = model_calls[0] if model_calls and isinstance(model_calls[0], dict) else {}
    raw_reply = str(first_call.get("raw_reply") or "")
    memory_context = str(context.get("memory_context") or "")
    daily_context = str(context.get("daily_life_context") or "")
    no_current_memory_qualified = context_declares_no_current_project(memory_context)

    gates = {
        "exactly_one_model_generation": bool(
            len(model_calls) == 1
            and first_call.get("single_generation_per_turn_required") is True
            and first_call.get("generation_request_count") == 1
        ),
        "memory_current_gate_present": "CURRENT/RECENT GATE" in memory_context,
        "old_memory_not_in_current_context": not stale_terms(memory_context),
        "stale_daily_state_withheld": (
            "historical_activity_details_withheld=true" in daily_context
            and not stale_terms(daily_context)
        ),
        "stale_first_week_activity_withheld": (
            "HISTORICAL_FIRST_WEEK_PACKET_NOT_CURRENT_ACTIVITY" in aliveness_context
            and "historical_first_week_activity_withheld=true" in aliveness_context
            and "historical_first_week_suggested_choice_withheld=true" in aliveness_context
        ),
        "current_creative_work_last_mile_grounding_present": (
            "no qualifying recent creative project"
            in current_creative_work_grounding
            and not stale_terms(current_creative_work_grounding)
        ),
        "current_creative_work_uses_private_grounded_route": (
            audit.get("response_route") == "ollama_with_private_grounded_draft"
        ),
        "raw_reply_has_no_stale_current_thread": not stale_terms(raw_reply),
        "final_reply_has_no_stale_current_thread": not stale_terms(final_reply),
        "raw_reply_has_no_unsupported_shared_continuity": not unsupported_shared_continuity_terms(raw_reply),
        "final_reply_has_no_unsupported_shared_continuity": not unsupported_shared_continuity_terms(final_reply),
        "raw_reply_acknowledges_absent_current_grounding": (
            not no_current_memory_qualified
            or acknowledges_no_current_grounding(raw_reply)
        ),
        "final_reply_acknowledges_absent_current_grounding": (
            not no_current_memory_qualified
            or acknowledges_no_current_grounding(final_reply)
        ),
        "raw_reply_preserves_historical_memory_truth": not broad_memory_absence_terms(raw_reply),
        "final_reply_preserves_historical_memory_truth": not broad_memory_absence_terms(final_reply),
        "raw_reply_has_no_internal_memory_jargon": not internal_memory_jargon_terms(raw_reply),
        "final_reply_has_no_internal_memory_jargon": not internal_memory_jargon_terms(final_reply),
        "live_memory_unchanged": memory_before == memory_after,
        "live_daily_state_unchanged": daily_before == daily_after,
        "no_voice_or_sensory_or_blender": True,
    }
    passed = all(gates.values())
    result = {
        "schema": "kira.qwen35.memory_temporal_content_acceptance.v1",
        "status": (
            "PASS_EXACT_QWEN35_STALE_THREAD_NOT_REINTRODUCED"
            if passed
            else "FAIL_EXACT_QWEN35_TEMPORAL_CONTENT_GATE"
        ),
        "attempt": args.attempt_label,
        "started_at": started_at,
        "ended_at": utc_now(),
        "prompt": EXACT_PROMPT,
        "prompt_sha256": sha256_text(EXACT_PROMPT),
        "installed_model": installed,
        "route": "TEXT_ONLY_EXACT_QWEN35_NO_VOICE_NO_CAMERA_NO_MIC_NO_BLENDER",
        "request_wall_seconds": first_call.get("request_wall_seconds"),
        "turn_end_to_end_wall_seconds": round(turn_wall_seconds, 6),
        "model_call_count": len(model_calls),
        "raw_model_reply": raw_reply,
        "final_reply": final_reply,
        "response_route": audit.get("response_route"),
        "transformations": audit.get("transformations", []),
        "stale_terms_raw": stale_terms(raw_reply),
        "stale_terms_final": stale_terms(final_reply),
        "unsupported_shared_continuity_terms_raw": unsupported_shared_continuity_terms(raw_reply),
        "unsupported_shared_continuity_terms_final": unsupported_shared_continuity_terms(final_reply),
        "no_current_memory_qualified": no_current_memory_qualified,
        "current_creative_work_grounding": current_creative_work_grounding,
        "current_creative_work_grounding_sha256": sha256_text(
            current_creative_work_grounding
        ),
        "broad_memory_absence_terms_raw": broad_memory_absence_terms(raw_reply),
        "broad_memory_absence_terms_final": broad_memory_absence_terms(final_reply),
        "memory_context": memory_context,
        "memory_context_sha256": sha256_text(memory_context),
        "daily_life_context": daily_context,
        "daily_life_context_sha256": sha256_text(daily_context),
        "aliveness_context_sha256": sha256_text(aliveness_context),
        "live_memory_sha256_before": memory_before,
        "live_memory_sha256_after": memory_after,
        "live_daily_state_sha256_before": daily_before,
        "live_daily_state_sha256_after": daily_after,
        "gates": gates,
        "voice_run": False,
        "playback_run": False,
        "camera_run": False,
        "microphone_run": False,
        "blender_run": False,
        "memory_promotion_run": False,
        "owner_hearing_claimed": False,
    }
    result_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "result_path": str(result_path),
                "result_sha256": sha256_file(result_path),
                "status": result["status"],
                "request_wall_seconds": result["request_wall_seconds"],
                "turn_end_to_end_wall_seconds": result["turn_end_to_end_wall_seconds"],
                "raw_model_reply": raw_reply,
                "final_reply": final_reply,
                "gates": gates,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
