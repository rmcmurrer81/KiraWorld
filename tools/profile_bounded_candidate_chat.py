"""Interactive, explicitly labelled review chat for incomplete profiles.

The normal TemporaryAI live-chat route remains the preferred path when its
source gates pass.  This runner is only for a checked-in candidate whose full
source package is incomplete or unavailable in a clean checkout.  It never
changes the source gate or claims activation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.model_request_policy import (  # noqa: E402
    QWEN_TEXT_VOICE_DIGEST,
    QWEN_TEXT_VOICE_MODEL,
    ordinary_model_request_fields,
    require_exact_qwen35_selection,
)
from Core.profile_bounded_candidate_review import (  # noqa: E402
    build_profile_bounded_system_prompt,
    label_profile_bounded_reply,
    load_profile_bounded_candidate,
)
from Core.qwen35_runtime_identity import (  # noqa: E402
    require_exact_qwen35_response_model,
    require_installed_exact_qwen35,
)


OLLAMA_ENDPOINT = os.getenv("KIRA_OLLAMA_ENDPOINT", "http://localhost:11434/api/chat")
MODEL_NAME = os.getenv("KIRA_MODEL_NAME", QWEN_TEXT_VOICE_MODEL)
MODEL_DIGEST = os.getenv("KIRA_MODEL_DIGEST", QWEN_TEXT_VOICE_DIGEST)
OUT_DIR = PROJECT_ROOT / "Data" / "personhood_evaluations" / "profile_bounded_candidate_chats"
RECENT_TURNS = 10


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _response_text(response: Any, expected_model: str) -> str:
    data = response.json()
    require_exact_qwen35_response_model(data, expected_model=expected_model)
    message = data.get("message") if isinstance(data, dict) else None
    if isinstance(message, dict):
        return str(message.get("content") or "").strip()
    return str(data.get("response") or "").strip() if isinstance(data, dict) else ""


def ask_profile_bounded_model(
    candidate: dict[str, Any],
    history: list[dict[str, str]],
    user_message: str,
    *,
    request_module: Any = requests,
) -> str:
    """Ask the pinned local model without using or weakening full source gates."""

    model_name, model_digest = require_exact_qwen35_selection(MODEL_NAME, MODEL_DIGEST)
    require_installed_exact_qwen35(
        request_module,
        chat_endpoint=OLLAMA_ENDPOINT,
        model_name=model_name,
        model_digest=model_digest,
        timeout=int(os.getenv("KIRA_OLLAMA_TIMEOUT", "360")),
    )
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": build_profile_bounded_system_prompt(candidate),
        }
    ]
    for row in history[-(RECENT_TURNS * 2) :]:
        role = str(row.get("role") or "")
        content = str(row.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": str(user_message).strip()})
    payload = {
        "model": model_name,
        "stream": False,
        "messages": messages,
        "options": {
            "temperature": float(os.getenv("KIRA_TEMPERATURE", "0.45")),
            "num_predict": int(os.getenv("KIRA_MAX_TOKENS", "600")),
            "num_ctx": int(os.getenv("KIRA_OLLAMA_NUM_CTX", "4096")),
        },
        **ordinary_model_request_fields(model_name),
    }
    response = request_module.post(
        OLLAMA_ENDPOINT,
        json=payload,
        timeout=int(os.getenv("KIRA_OLLAMA_TIMEOUT", "360")),
    )
    if response.status_code == 404 and OLLAMA_ENDPOINT.endswith("/api/chat"):
        generate_payload = {
            "model": model_name,
            "stream": False,
            "prompt": (
                build_profile_bounded_system_prompt(candidate)
                + "\n\nRobert: "
                + str(user_message).strip()
            ),
            "options": payload["options"],
        }
        response = request_module.post(
            OLLAMA_ENDPOINT.rsplit("/api/chat", 1)[0] + "/api/generate",
            json=generate_payload,
            timeout=int(os.getenv("KIRA_OLLAMA_TIMEOUT", "360")),
        )
    response.raise_for_status()
    return label_profile_bounded_reply(_response_text(response, model_name))


def run_profile_bounded_chat(
    candidate_id: str,
    *,
    ask: Callable[[dict[str, Any], list[dict[str, str]], str], str] = ask_profile_bounded_model,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> dict[str, str]:
    """Run a typed draft review and save a clearly classified transcript."""

    candidate = load_profile_bounded_candidate(PROJECT_ROOT, candidate_id)
    profile = candidate["profile"]
    display = str(profile.get("display_name") or candidate_id)
    run_id = (
        "profile_bounded_candidate_chat_"
        + candidate_id[:80]
        + "_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    json_path = OUT_DIR / f"{run_id}.json"
    history: list[dict[str, str]] = []
    records: list[dict[str, Any]] = []

    output_fn("")
    output_fn(f"Profile-bounded draft review: {display}")
    output_fn("This is not activation, verified canon, memory proof, body/world presence, or an authentic voice.")
    output_fn("Type /quit when done.")
    output_fn("")
    while True:
        try:
            user_message = input_fn("Robert> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user_message.lower() in {"/quit", "/exit", "quit", "exit"}:
            break
        if not user_message:
            continue
        try:
            answer = ask(candidate, history, user_message)
        except requests.exceptions.ConnectionError:
            answer = "[Draft review - profile-bounded] The local model is offline."
        except Exception as exc:
            answer = (
                "[Draft review - profile-bounded] "
                f"The bounded review could not answer ({type(exc).__name__}: {exc})."
            )
        answer = label_profile_bounded_reply(answer)
        output_fn(f"{display}> {answer}")
        output_fn("")
        record = {
            "turn": len(records) + 1,
            "robert": user_message,
            "candidate": answer,
            "review_mode": "profile_bounded_draft",
            "created_at": now_iso(),
        }
        records.append(record)
        history.extend(
            (
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": answer},
            )
        )
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "candidate_id": candidate_id,
                    "display_name": display,
                    "review_mode": "profile_bounded_draft",
                    "limitations": [
                        "not_permanent_activation",
                        "not_verified_canon_or_memory",
                        "not_authentic_voice",
                        "no_body_or_world_presence",
                    ],
                    "records": records,
                    "updated_at": now_iso(),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return {
        "status": "completed",
        "candidate_id": candidate_id,
        "review_mode": "profile_bounded_draft",
        "transcript": (
            json_path.relative_to(PROJECT_ROOT).as_posix() if json_path.exists() else ""
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run an explicitly labelled profile-bounded candidate review chat."
    )
    parser.add_argument("candidate_id")
    args = parser.parse_args()
    result = run_profile_bounded_chat(args.candidate_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
