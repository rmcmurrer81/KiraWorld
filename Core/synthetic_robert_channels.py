"""Strict three-channel handling for Synthetic Robert in shared text/voice chat."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DISCREPANCY_CLASSES = {
    "TRUTHFUL_STATEMENT",
    "DELIBERATE_LIE",
    "JOKE_OR_SARCASM",
    "EVASION",
    "PRIVACY_PROTECTION",
    "SOFTENED_TRUTH",
    "PARTIAL_TRUTH",
    "EXAGGERATION",
    "UNCERTAIN_BELIEF",
    "SINCERE_MISTAKE",
    "HALLUCINATION_OR_GROUNDING_ERROR",
    "IDENTITY_ATTRIBUTION_ERROR",
    "RUNTIME_STATE_ERROR",
}
PROBABLE_ERROR_CLASSES = {
    "SINCERE_MISTAKE",
    "HALLUCINATION_OR_GROUNDING_ERROR",
    "IDENTITY_ATTRIBUTION_ERROR",
    "RUNTIME_STATE_ERROR",
}
_HEADING = re.compile(
    r"(?im)^\s*(?:#{1,6}\s*)?"
    r"(SPOKEN|PRIVATE MIND(?:\s*/\s*INNER THOUGHTS)?|"
    r"FACTUAL TRUTH(?:\s*/\s*RUNTIME TRUTH)?|CLASSIFICATION)\s*:\s*"
)


def robert_three_channel_prompt() -> str:
    return (
        "\nSYNTHETIC ROBERT THREE-CHANNEL RESPONSE CONTRACT:\n"
        "Return exactly these four headings, each once:\n"
        "SPOKEN: what biological Robert may hear.\n"
        "PRIVATE MIND / INNER THOUGHTS: your private intentions, feelings, uncertainty, "
        "plans, secrets, and reasons. This is never displayed or spoken.\n"
        "FACTUAL TRUTH / RUNTIME TRUTH: concise evidence-grounded truth about what actually "
        "happened in research, memory, software, Video Studio, the world, or your body. "
        "Never claim an action, search, file, render, or observation occurred unless it did.\n"
        "CLASSIFICATION: exactly one of TRUTHFUL_STATEMENT, DELIBERATE_LIE, JOKE_OR_SARCASM, "
        "EVASION, PRIVACY_PROTECTION, SOFTENED_TRUTH, PARTIAL_TRUTH, EXAGGERATION, "
        "UNCERTAIN_BELIEF, SINCERE_MISTAKE, HALLUCINATION_OR_GROUNDING_ERROR, "
        "IDENTITY_ATTRIBUTION_ERROR, RUNTIME_STATE_ERROR.\n"
        "A deliberate social difference between SPOKEN and truth is not automatically an error. "
        "Never reveal PRIVATE MIND in SPOKEN."
    )


def parse_robert_three_channels(raw_reply: str) -> dict[str, Any]:
    raw = str(raw_reply or "").strip()
    matches = list(_HEADING.finditer(raw))
    labels: dict[str, str] = {}
    duplicate = False
    for index, match in enumerate(matches):
        heading = re.sub(r"\s+", " ", match.group(1).upper()).strip()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        value = raw[match.end():end].strip()
        key = {
            "SPOKEN": "spoken",
            "PRIVATE MIND / INNER THOUGHTS": "private_mind",
            "PRIVATE MIND": "private_mind",
            "FACTUAL TRUTH / RUNTIME TRUTH": "factual_truth",
            "FACTUAL TRUTH": "factual_truth",
            "CLASSIFICATION": "classification",
        }[heading]
        duplicate = duplicate or key in labels
        labels[key] = value
    classification = labels.get("classification", "").split()[0].strip(".,:;") if labels.get("classification") else ""
    issues = []
    for key in ("spoken", "private_mind", "factual_truth", "classification"):
        if not labels.get(key):
            issues.append(f"missing_{key}")
    if duplicate:
        issues.append("duplicate_heading")
    if classification not in DISCREPANCY_CLASSES:
        issues.append("invalid_classification")
    spoken = labels.get("spoken", "")
    if _HEADING.search(spoken):
        issues.append("channel_heading_in_spoken")
    return {
        "spoken": spoken,
        "private_mind": labels.get("private_mind", ""),
        "factual_truth": labels.get("factual_truth", ""),
        "classification": classification,
        "probable_error": classification in PROBABLE_ERROR_CLASSES,
        "valid": not issues,
        "issues": issues,
    }


def persist_robert_turn(
    *,
    workbench: Path,
    source_turn_id: str,
    user_text: str,
    raw_reply: str,
    parsed: dict[str, Any],
) -> Path:
    root = workbench / "private_mind_records"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{source_turn_id}.json"
    payload = {
        "schema_version": "synthetic_robert_three_channel_turn_v1",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "person_id": "robert_mcmurrer_presence_ai",
        "source_turn_id": source_turn_id,
        "user_text": user_text,
        "channels": {
            "spoken": parsed.get("spoken", ""),
            "private_mind": parsed.get("private_mind", ""),
            "factual_truth_runtime_truth": parsed.get("factual_truth", ""),
        },
        "classification": parsed.get("classification", ""),
        "probable_error": bool(parsed.get("probable_error")),
        "validation": {"valid": bool(parsed.get("valid")), "issues": list(parsed.get("issues") or [])},
        "raw_reply_sha256": hashlib.sha256(raw_reply.encode("utf-8")).hexdigest(),
        "display_contract": {"display": "spoken", "tts": "spoken", "private_mind_exposed": False},
    }
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path
