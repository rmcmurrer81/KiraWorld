from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from datetime import datetime, timezone
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MODEL = "qwen3.5:9b"
EXPECTED_DIGEST = (
    "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
)
DEFAULT_ATTEMPT = (
    PROJECT_ROOT
    / "RecoverySprint"
    / "continuation_20260809"
    / "kira_qwen35_health_curiosity_text_dialogue"
    / "attempt_01"
)
LIVE_MEMORY = PROJECT_ROOT / "Data" / "memories_kira.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_prior_turns(attempt: Path) -> list[dict[str, Any]]:
    turns: list[dict[str, Any]] = []
    for path in sorted(attempt.glob("turn_*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(item, dict):
            raise RuntimeError(f"invalid prior turn evidence: {path}")
        turns.append(item)
    return turns


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Append one bounded text-only exact-Qwen Kira curiosity turn."
    )
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--attempt-dir", type=Path, default=DEFAULT_ATTEMPT)
    args = parser.parse_args()

    prompt = str(args.prompt).strip()
    if not prompt or len(prompt) > 6000:
        raise RuntimeError("prompt must contain 1-6000 characters")

    attempt = args.attempt_dir.resolve()
    allowed_root = (
        PROJECT_ROOT / "RecoverySprint" / "continuation_20260809"
    ).resolve()
    if attempt != allowed_root and allowed_root not in attempt.parents:
        raise RuntimeError("attempt directory must remain in continuation_20260809")
    attempt.mkdir(parents=True, exist_ok=True)
    prior = load_prior_turns(attempt)
    turn_number = len(prior) + 1
    if turn_number > 4:
        raise RuntimeError("bounded dialogue allows at most four turns")
    turn_path = attempt / f"turn_{turn_number:02d}.json"
    if turn_path.exists():
        raise RuntimeError("turn evidence already exists")

    os.environ["KIRA_MODEL_BACKEND"] = "ollama"
    os.environ["KIRA_MODEL_NAME"] = EXPECTED_MODEL
    os.environ["KIRA_MODEL_DIGEST"] = EXPECTED_DIGEST
    os.environ["KIRA_OLLAMA_TIMEOUT"] = "180"
    os.environ["KIRA_MAX_TOKENS"] = "420"
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

    live_memory_before = sha256_file(LIVE_MEMORY)
    with tempfile.TemporaryDirectory(prefix="kira_health_curiosity_") as temporary:
        base = Path(temporary)
        loop = ConversationLoop(
            speaker="Kira",
            relationship_state_file=base / "relationships.json",
            privacy_session_file=base / "privacy.json",
            decision_log_file=base / "decision.jsonl",
            conversation_log_file=base / "conversation.jsonl",
            attention_state_file=base / "attention.json",
            daily_life_state_dir=base / "daily_state",
            memory_candidate_dir=base / "memory_candidates",
            memory_file=base / "memories.json",
            daily_life_log_dir=base / "daily_logs",
            reading_session_dir=base / "reading_sessions",
            reading_recommendation_dir=base / "reading_recommendations",
        )
        for item in prior:
            loop.conversation_history.append(
                {"role": "user", "content": str(item["prompt"])}
            )
            loop.conversation_history.append(
                {"role": "assistant", "content": str(item["final_reply"])}
            )
        state_before = loop.person_emotion.snapshot(include_private=True)
        started_at = utc_now()
        turn_started_ns = time.perf_counter_ns()
        final_reply = loop.process(prompt)
        turn_wall_seconds = (time.perf_counter_ns() - turn_started_ns) / 1_000_000_000
        ended_at = utc_now()
        state_after = loop.person_emotion.snapshot(include_private=True)
        audit = dict(loop.last_turn_audit)

    live_memory_after = sha256_file(LIVE_MEMORY)
    model_calls = audit.get("model_calls", [])
    if not isinstance(model_calls, list):
        model_calls = []
    first_call = model_calls[0] if isinstance(model_calls, list) and model_calls else {}
    call_wall_seconds = [
        float(item["request_wall_seconds"])
        for item in model_calls
        if isinstance(item, dict)
        and isinstance(item.get("request_wall_seconds"), (int, float))
        and not isinstance(item.get("request_wall_seconds"), bool)
    ]
    single_generation_passed = bool(
        len(model_calls) == 1
        and first_call.get("single_generation_per_turn_required") is True
        and first_call.get("generation_request_count") == 1
    )
    evidence = {
        "schema": "kira.qwen35.health_curiosity_text_turn.v2",
        "status": (
            "ENGINEERING_TEXT_TURN_COMPLETE_SINGLE_GENERATION"
            if single_generation_passed
            else "FAILED_SINGLE_GENERATION_GATE"
        ),
        "attempt": attempt.name,
        "turn": turn_number,
        "started_at": started_at,
        "ended_at": ended_at,
        "prompt": prompt,
        "model": installed,
        "route": "TEXT_ONLY_EXACT_QWEN35_NO_VOICE_NO_CAMERA_NO_MIC_NO_BLENDER",
        "raw_model_reply": first_call.get("raw_reply"),
        "initial_pipeline_reply": audit.get("initial_pipeline_reply"),
        "final_reply": final_reply,
        "transformations": audit.get("transformations", []),
        "response_route": audit.get("response_route"),
        "model_call_audit": model_calls,
        "model_call_count": len(model_calls),
        "model_call_wall_seconds": call_wall_seconds,
        "model_call_wall_seconds_sum": round(sum(call_wall_seconds), 6),
        "request_wall_seconds": first_call.get("request_wall_seconds"),
        "turn_end_to_end_wall_seconds": round(turn_wall_seconds, 6),
        "single_generation_required": True,
        "single_generation_passed": single_generation_passed,
        "emotion_state_before": state_before,
        "emotion_state_after": state_after,
        "emotion_state_changed_by_model": state_before != state_after,
        "live_memory_path_project_relative": "Data/memories_kira.json",
        "live_memory_sha256_before": live_memory_before,
        "live_memory_sha256_after": live_memory_after,
        "live_memory_unchanged": live_memory_before == live_memory_after,
        "conversation_wrote_only_to_ephemeral_runtime": True,
        "voice_run": False,
        "camera_run": False,
        "microphone_run": False,
        "blender_run": False,
        "memory_promotion_run": False,
        "owner_hearing_claimed": False,
        "emotion_or_consciousness_proven": False,
    }
    turn_path.write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "turn_path": str(turn_path),
                "turn_sha256": sha256_file(turn_path),
                "request_wall_seconds": evidence["request_wall_seconds"],
                "turn_end_to_end_wall_seconds": evidence[
                    "turn_end_to_end_wall_seconds"
                ],
                "model_call_count": evidence["model_call_count"],
                "single_generation_passed": evidence[
                    "single_generation_passed"
                ],
                "final_reply": final_reply,
                "live_memory_unchanged": evidence["live_memory_unchanged"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if single_generation_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
