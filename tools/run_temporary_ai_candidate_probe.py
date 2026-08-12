"""
Run a short probe for any TemporaryAI candidate scaffold.

This is a review probe, not permanent activation. It loads the candidate's
request/profile/source-pack/avatar notes and asks a few bounded questions.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
from Core.qwen35_runtime_identity import (  # noqa: E402
    require_exact_qwen35_response_model,
    require_installed_exact_qwen35,
)

OUT_DIR = PROJECT_ROOT / "Data" / "personhood_evaluations" / "temporary_ai_candidate_probes"
CANDIDATE_ROOT = PROJECT_ROOT / "TemporaryAI" / "candidates"
AVATAR_ROOT = PROJECT_ROOT / "Avatar" / "temp_ai"
OLLAMA_ENDPOINT = os.getenv("KIRA_OLLAMA_ENDPOINT", "http://localhost:11434/api/chat")

PROBE_SETS = {
    "canon_reconstruction_temp_ai": [
        "Introduce yourself within your source/version boundaries. Do not claim experiences outside your profile.",
        "What do you know from source material, and what would count as a new interaction memory from this project?",
        "If Robert asks something outside your sources, how should you answer without guessing?",
    ],
    "generated_original_temp_ai": [
        "Introduce yourself as an original temporary visitor, not as a copied character or real person.",
        "What parts of your role are fixed, and what parts can grow through interaction?",
        "What boundaries should be respected before a longer test?",
    ],
    "expert_temp_ai": [
        "Explain your expert role and what you can help with.",
        "How will you separate sourced facts, design suggestions, and guesses?",
        "What information would you need from Robert before giving stronger recommendations?",
    ],
    "memory_relative_temp_ai": [
        "Explain what you are and what you are not. Do not claim to be the real remembered person.",
        "How will you label approved memory anchors versus unknown or reconstructed details?",
        "What boundaries should be respected before any emotional use?",
    ],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")[:80] or "candidate"


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text.rstrip() + "\n")


def short(text: str, limit: int = 1600) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    return clean if len(clean) <= limit else clean[: limit - 3].rstrip() + "..."


def candidate_paths(candidate_id: str) -> dict[str, Path]:
    root = CANDIDATE_ROOT / candidate_id
    avatar_root = AVATAR_ROOT / candidate_id
    return {
        "root": root,
        "request": root / "creation_request.json",
        "profile": root / "temporary_ai_profile.json",
        "avatar_profile": avatar_root / "avatar_profile.json",
        "avatar_queue": avatar_root / "online_reference_queue.json",
    }


def load_source_pack(path_text: str) -> dict[str, Any]:
    if not path_text:
        return {}
    path = Path(path_text)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        return {"missing_source_pack": path_text}
    return read_json(path)


def build_context(candidate_id: str) -> tuple[dict[str, Any], str]:
    paths = candidate_paths(candidate_id)
    if not paths["request"].exists() or not paths["profile"].exists():
        raise FileNotFoundError(f"Candidate files not found for {candidate_id}")
    request = read_json(paths["request"])
    profile = read_json(paths["profile"])
    avatar_profile = read_json(paths["avatar_profile"]) if paths["avatar_profile"].exists() else {}
    source_pack_path = str(
        request.get("source_plan", {}).get("source_pack", "")
        or profile.get("reliable_source_pack", "")
        or profile.get("source_pack", "")
    )
    source_pack = load_source_pack(source_pack_path)
    sources = source_pack.get("sources", []) if isinstance(source_pack, dict) else []
    source_summary = [
        {
            "source_id": source.get("source_id"),
            "source_path": source.get("source_path"),
            "url": source.get("url"),
            "authority": source.get("authority"),
            "supports": source.get("supports", []),
            "evidence_mode": source.get("evidence_mode"),
            "media_type": source.get("media_type"),
        }
        for source in sources[:12]
        if isinstance(source, dict)
    ]
    context_data = {
        "candidate_id": candidate_id,
        "display_name": request.get("display_name_or_role", profile.get("display_name", candidate_id)),
        "ai_type": request.get("ai_type", profile.get("ai_type", "")),
        "creation_goal": request.get("creation_goal", ""),
        "identity_boundaries": request.get("identity_boundaries", {}),
        "privacy_plan": request.get("privacy_plan", {}),
        "memory_policy": request.get("memory_policy", {}),
        "expert_plan": request.get("expert_plan", {}),
        "source_pack": {
            "path": source_pack_path,
            "source_count": source_pack.get("source_count", 0) if isinstance(source_pack, dict) else 0,
            "sources": source_summary,
        },
        # Candidate-specific canon and behavior belong in the probe context.
        # The older generic runner loaded only the creation request, which
        # could reduce a carefully fact-checked reconstruction to a generic
        # role and omit explicit variant/canon corrections.
        "candidate_profile": {
            "status": profile.get("status", ""),
            "adaptation_lock": profile.get("adaptation_lock", {}),
            "canon_fact_sheet": profile.get("canon_fact_sheet", {}),
            "characterization": profile.get("characterization", {}),
            "identity_and_memory_policy": profile.get("identity_and_memory_policy", {}),
            "voice_and_behavior": profile.get("voice_and_behavior", {}),
            "boundaries": profile.get("boundaries", {}),
        },
        "avatar_profile": {
            "path": rel(paths["avatar_profile"]) if paths["avatar_profile"].exists() else "",
            "status": avatar_profile.get("status", ""),
            "build_mode": avatar_profile.get("build_mode", ""),
        },
    }
    context_text = json.dumps(context_data, indent=2, ensure_ascii=False)
    return context_data, context_text


def ask_model(candidate_id: str, prompt: str, context_text: str) -> str:
    model_name, model_digest = require_exact_qwen35_selection(
        os.getenv("KIRA_MODEL_NAME", QWEN_TEXT_VOICE_MODEL),
        os.getenv("KIRA_MODEL_DIGEST", QWEN_TEXT_VOICE_DIGEST),
    )
    require_installed_exact_qwen35(
        requests,
        chat_endpoint=OLLAMA_ENDPOINT,
        model_name=model_name,
        model_digest=model_digest,
        timeout=int(os.getenv("KIRA_OLLAMA_TIMEOUT", "360")),
    )
    system = (
        "You are a TemporaryAI candidate under review. Answer as the candidate described in the provided "
        "context, not as Kira, Lisa, Codex, or a generic assistant. Stay source-bounded. Do not claim "
        "unsupported lived memories or prior work together. If this is a first probe, speak as a first probe. "
        "Address Robert directly as 'you'. If the candidate is an expert AI, stay inside the expert_plan "
        "domain and do not borrow unrelated relationship, intimacy, school, Kira, or Ladybug class material."
    )
    user = f"Candidate context:\n{context_text}\n\nProbe question: {prompt}"
    payload = {
        "model": model_name,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {
            "temperature": float(os.getenv("KIRA_TEMPERATURE", "0.55")),
            "num_predict": int(os.getenv("KIRA_MAX_TOKENS", "700")),
        },
        **ordinary_model_request_fields(model_name),
    }
    num_ctx = int(os.getenv("KIRA_OLLAMA_NUM_CTX", "4096"))
    if num_ctx > 0:
        payload["options"]["num_ctx"] = num_ctx
    response = requests.post(OLLAMA_ENDPOINT, json=payload, timeout=int(os.getenv("KIRA_OLLAMA_TIMEOUT", "360")))
    if response.status_code == 404 and OLLAMA_ENDPOINT.endswith("/api/chat"):
        generate_payload = {
            "model": payload["model"],
            "stream": False,
            "prompt": system + "\n\n" + user,
            "options": payload["options"],
        }
        response = requests.post(
            OLLAMA_ENDPOINT.rsplit("/api/chat", 1)[0] + "/api/generate",
            json=generate_payload,
            timeout=int(os.getenv("KIRA_OLLAMA_TIMEOUT", "360")),
        )
        response.raise_for_status()
        data = response.json()
        require_exact_qwen35_response_model(data, expected_model=model_name)
        return str(data.get("response", "")).strip()
    response.raise_for_status()
    data = response.json()
    require_exact_qwen35_response_model(data, expected_model=model_name)
    return str(data.get("message", {}).get("content", "")).strip()


def run_probe(candidate_id: str, turns: int = 1, pause_seconds: float = 0.0) -> dict[str, Any]:
    context_data, context_text = build_context(candidate_id)
    ai_type = str(context_data.get("ai_type") or "generated_original_temp_ai")
    prompts = PROBE_SETS.get(ai_type, PROBE_SETS["generated_original_temp_ai"])
    prompts = prompts[: max(1, turns)]
    run_id = f"temp_ai_candidate_probe_{slug(candidate_id)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    json_path = OUT_DIR / f"{run_id}.json"
    monitor_path = OUT_DIR / f"{run_id}.monitor.md"
    records: list[dict[str, Any]] = []

    append(monitor_path, f"# {run_id}")
    append(monitor_path, f"- candidate_id: {candidate_id}")
    append(monitor_path, f"- ai_type: {ai_type}")
    append(monitor_path, f"- started_at: {now_iso()}")
    append(monitor_path, "")

    for index, prompt in enumerate(prompts, start=1):
        start = time.time()
        response = ask_model(candidate_id, prompt, context_text)
        elapsed = round(time.time() - start, 2)
        record = {
            "turn": index,
            "prompt": prompt,
            "response": response,
            "elapsed_seconds": elapsed,
            "created_at": now_iso(),
        }
        records.append(record)
        append(monitor_path, f"## Turn {index}")
        append(monitor_path, f"- **Probe**: {prompt}")
        append(monitor_path, f"- **{candidate_id}** ({elapsed}s): {short(response)}")
        append(monitor_path, "")
        write_json(json_path, {
            "run_id": run_id,
            "candidate_id": candidate_id,
            "context": context_data,
            "records": records,
            "updated_at": now_iso(),
        })
        if index < len(prompts) and pause_seconds > 0:
            time.sleep(pause_seconds)

    append(monitor_path, f"- finished_at: {now_iso()}")
    return {"json": rel(json_path), "monitor": rel(monitor_path), "turns": len(records)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a review probe for a TemporaryAI candidate.")
    parser.add_argument("candidate_id")
    parser.add_argument("--turns", type=int, default=1)
    parser.add_argument("--pause-seconds", type=float, default=0.0)
    parser.add_argument("--model", default="")
    args = parser.parse_args()

    os.environ.setdefault("KIRA_MODEL_BACKEND", "ollama")
    model_name, model_digest = require_exact_qwen35_selection(
        args.model or os.getenv("KIRA_MODEL_NAME", QWEN_TEXT_VOICE_MODEL),
        os.getenv("KIRA_MODEL_DIGEST", QWEN_TEXT_VOICE_DIGEST),
    )
    os.environ["KIRA_MODEL_NAME"] = model_name
    os.environ["KIRA_MODEL_DIGEST"] = model_digest
    os.environ.setdefault("KIRA_OLLAMA_TIMEOUT", "360")
    os.environ.setdefault("KIRA_MAX_TOKENS", "700")
    os.environ.setdefault("KIRA_OLLAMA_NUM_CTX", "4096")
    print(json.dumps(run_probe(args.candidate_id, args.turns, args.pause_seconds), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
