"""Fail-closed separation of spoken dialogue from private truth channels.

Long local-model conversations sometimes vary headings (for example
``PRIVATE_MIND`` versus ``PRIVATE MIND`` or ``PRIVATE SUMMARY``).  Speech
renderers must recover the spoken section from the raw response and must never
send a stored field containing a private section marker to TTS.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DialoguePrivacyError(ValueError):
    """Raised when a turn cannot be proven safe for speech rendering."""


_HEADING_RE = re.compile(
    r"^\s*(?:[#>*-]+\s*)?(?:\*{1,2})?"
    r"(?:(?:Kira|Robert)\s+)?"
    r"(?P<label>"
    r"SPOKEN|"
    r"PRIVATE(?:[\s_-]+)(?:MIND|SUMMARY|REFLECTION|THOUGHTS|CHANNEL|REASONING|ANALYSIS|DELIBERATION|MEMORY|NOTES?)|"
    r"INTERNAL(?:[\s_-]+)(?:MIND|SUMMARY|REFLECTION|THOUGHTS?|CHANNEL|REASONING|ANALYSIS|DELIBERATION|MEMORY|NOTES?)|"
    r"HIDDEN(?:[\s_-]+)(?:MIND|SUMMARY|THOUGHTS?|REASONING|ANALYSIS|NOTES?)|"
    r"UNSPOKEN(?:[\s_-]+)(?:MIND|SUMMARY|THOUGHTS?|REASONING|NOTES?)|"
    r"NOT(?:[\s_-]+)FOR(?:[\s_-]+)(?:SPEECH|TTS)|"
    r"TRUTH(?:[\s_-]+)(?:FLAG|FLAGS|CHECK|CHANNEL)"
    r")\s*:\s*(?:\*{1,2})?\s*(?P<rest>.*)$",
    flags=re.IGNORECASE,
)

_ANY_HEADING_RE = re.compile(
    r"^\s*(?:[#>*-]+\s*)?(?:\*{1,2})?"
    r"(?P<label>[A-Za-z][A-Za-z0-9 /_-]{1,63})\s*:\s*(?:\*{1,2})?\s*(?P<rest>.*)$"
)

_PRIVATE_MARKER_RE = re.compile(
    r"(?im)^\s*(?:[#>*-]+\s*)?(?:\*{1,2})?"
    r"(?:(?:Kira|Robert)\s+)?"
    r"(?:PRIVATE(?:[\s_-]+)(?:MIND|SUMMARY|REFLECTION|THOUGHTS|CHANNEL|REASONING|ANALYSIS|DELIBERATION|MEMORY|NOTES?)|"
    r"INTERNAL(?:[\s_-]+)(?:MIND|SUMMARY|REFLECTION|THOUGHTS?|CHANNEL|REASONING|ANALYSIS|DELIBERATION|MEMORY|NOTES?)|"
    r"HIDDEN(?:[\s_-]+)(?:MIND|SUMMARY|THOUGHTS?|REASONING|ANALYSIS|NOTES?)|"
    r"UNSPOKEN(?:[\s_-]+)(?:MIND|SUMMARY|THOUGHTS?|REASONING|NOTES?)|"
    r"NOT(?:[\s_-]+)FOR(?:[\s_-]+)(?:SPEECH|TTS)|"
    r"CONFIDENTIAL(?:[\s_-]+)(?:MIND|SUMMARY|THOUGHTS?|REASONING|ANALYSIS|NOTES?)|"
    r"SECRET(?:(?:[\s_-]+)(?:MIND|SUMMARY|THOUGHTS?|REASONING|ANALYSIS|NOTES?))?|"
    r"CHAIN(?:[\s_-]+)OF(?:[\s_-]+)THOUGHT|"
    r"SCRATCHPAD|THOUGHTS?|REASONING|ANALYSIS|DELIBERATION|MEMORY|NOTES?|"
    r"TRUTH(?:[\s_-]+)(?:FLAG|FLAGS|CHECK|CHANNEL))\s*:",
)

_SUSPICIOUS_HEADING_RE = re.compile(
    r"\b(?:private|internal|hidden|unspoken|confidential|secret|scratchpad|"
    r"thoughts?|reasoning|analysis|deliberation|memory|notes?|truth)\b",
    flags=re.IGNORECASE,
)


def _canonical_section(label: str) -> str:
    normalized = re.sub(r"[\s_-]+", "_", label.strip().upper())
    if normalized == "SPOKEN":
        return "spoken"
    if normalized.startswith(
        (
            "PRIVATE_",
            "INTERNAL_",
            "HIDDEN_",
            "UNSPOKEN_",
            "CONFIDENTIAL_",
            "SECRET_",
            "CHAIN_OF_THOUGHT",
        )
    ):
        return "private_mind"
    if normalized.startswith("NOT_FOR_"):
        return "private_mind"
    if normalized in {
        "SECRET",
        "SCRATCHPAD",
        "THOUGHT",
        "THOUGHTS",
        "REASONING",
        "ANALYSIS",
        "DELIBERATION",
        "MEMORY",
        "NOTE",
        "NOTES",
    }:
        return "private_mind"
    if normalized.startswith("TRUTH_"):
        return "truth_flags"
    raise DialoguePrivacyError(f"Unknown dialogue section heading: {label!r}")


def _section_text(lines: list[str]) -> str:
    value = "\n".join(lines).strip()
    return re.sub(r"^\*\*|\*\*$", "", value).strip()


def contains_private_marker(text: str) -> bool:
    return bool(_PRIVATE_MARKER_RE.search(text or ""))


def parse_structured_response(raw: str) -> dict[str, Any]:
    """Parse flexible headings while keeping speech and private text separate."""

    sections: dict[str, list[str]] = {
        "spoken": [],
        "private_mind": [],
        "truth_flags": [],
    }
    current: str | None = None
    found_heading = False
    found_sections: set[str] = set()
    unknown_headings: list[str] = []

    for line in str(raw or "").replace("\r\n", "\n").split("\n"):
        match = _HEADING_RE.match(line)
        if match:
            current = _canonical_section(match.group("label"))
            found_heading = True
            found_sections.add(current)
            rest = match.group("rest").strip()
            if rest:
                sections[current].append(rest)
            continue
        unknown = _ANY_HEADING_RE.match(line) if current in (None, "spoken") else None
        if unknown and (
            unknown.group("label") == unknown.group("label").upper()
            or "_" in unknown.group("label")
            or _SUSPICIOUS_HEADING_RE.search(unknown.group("label"))
        ):
            found_heading = True
            current = "_unknown"
            unknown_headings.append(unknown.group("label").strip())
            continue
        if current is None:
            continue
        if current in sections:
            sections[current].append(line)

    result: dict[str, Any] = {
        key: _section_text(value) for key, value in sections.items()
    }
    issues: list[str] = []
    if not result["spoken"]:
        issues.append("missing_spoken")
    if not result["private_mind"]:
        issues.append("missing_private_mind")
    if not result["truth_flags"]:
        issues.append("missing_truth_flags")
    if contains_private_marker(result["spoken"]):
        issues.append("private_marker_in_spoken")
    if unknown_headings:
        issues.append("unknown_section_heading")
    if "spoken" not in found_sections:
        issues.append("missing_explicit_spoken_heading")
    result["issues"] = list(dict.fromkeys(issues))
    result["privacy_safe_for_speech"] = (
        bool(result["spoken"])
        and "spoken" in found_sections
        and not unknown_headings
        and not contains_private_marker(result["spoken"])
    )
    result["found_heading"] = found_heading
    result["found_spoken_heading"] = "spoken" in found_sections
    result["unknown_section_headings"] = unknown_headings
    return result


def normalize_speaker(value: Any) -> str:
    speaker = str(value or "").strip()
    if speaker.lower().startswith("kira"):
        return "Kira"
    if speaker.lower().startswith("robert"):
        return "Robert"
    raise DialoguePrivacyError(f"Unsupported dialogue speaker: {speaker!r}")


def prepare_speech_turn(item: dict[str, Any]) -> dict[str, Any]:
    """Return one privacy-safe spoken turn, preferring reparsed raw output."""

    speaker = normalize_speaker(item.get("speaker"))
    stored_spoken = str(item.get("spoken") or "").strip()
    raw = str(item.get("raw") or "")
    recovered_from_raw = False

    if raw:
        parsed = parse_structured_response(raw)
        spoken = str(parsed["spoken"]).strip()
        if not parsed["privacy_safe_for_speech"]:
            raise DialoguePrivacyError(
                f"Turn {item.get('turn', '?')} cannot be separated safely: "
                + ", ".join(parsed["issues"])
            )
        recovered_from_raw = spoken != stored_spoken or contains_private_marker(stored_spoken)
    else:
        spoken = stored_spoken

    if not spoken or contains_private_marker(spoken):
        raise DialoguePrivacyError(f"Turn {item.get('turn', '?')} contains unsafe or empty spoken text")

    return {
        "speaker": speaker,
        "text": spoken,
        "source_turn": item.get("turn"),
        "recovered_from_raw": recovered_from_raw,
        "spoken_sha256": hashlib.sha256(spoken.encode("utf-8")).hexdigest(),
    }


def prepare_dialogue_speech_turns(
    data: dict[str, Any],
    *,
    last_turns: int = 0,
    max_chars: int = 0,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if isinstance(last_turns, bool) or not isinstance(last_turns, int) or last_turns < 0:
        raise DialoguePrivacyError("last_turns must be a non-negative integer")
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 0:
        raise DialoguePrivacyError("max_chars must be a non-negative integer")

    all_raw_turns = data.get("transcript") or data.get("turns") or []
    all_raw_turns = [item for item in all_raw_turns if isinstance(item, dict)]

    # Validate the complete stored payload before applying a listening selection.
    # This prevents a clean tail excerpt from hiding tampering elsewhere in an
    # already privacy-audited spoken-only export.
    all_prepared_turns = [prepare_speech_turn(item) for item in all_raw_turns]
    if not all_prepared_turns:
        raise DialoguePrivacyError("No privacy-safe Kira/Robert spoken turns found")
    full_combined = "\n".join(
        f"{turn['speaker']}\t{turn['text']}" for turn in all_prepared_turns
    )
    full_payload_sha256 = hashlib.sha256(full_combined.encode("utf-8")).hexdigest()

    selected_raw_turns = all_raw_turns[-last_turns:] if last_turns > 0 else all_raw_turns
    selected_prepared_turns = (
        all_prepared_turns[-last_turns:] if last_turns > 0 else all_prepared_turns
    )
    turns: list[dict[str, Any]] = []
    for prepared in selected_prepared_turns:
        turn = copy.deepcopy(prepared)
        if max_chars > 0 and len(turn["text"]) > max_chars:
            turn["text"] = turn["text"][: max_chars - 1].rstrip() + "."
            turn["spoken_sha256"] = hashlib.sha256(turn["text"].encode("utf-8")).hexdigest()
            turn["truncated_for_speech"] = True
        if contains_private_marker(turn["text"]):
            raise DialoguePrivacyError(f"Turn {turn['source_turn']} failed the final privacy scan")
        turns.append(turn)

    combined = "\n".join(f"{turn['speaker']}\t{turn['text']}" for turn in turns)
    local_contamination_count = sum(
        contains_private_marker(str(item.get("spoken") or "")) for item in all_raw_turns
    )
    upstream = data.get("privacy_audit") if isinstance(data.get("privacy_audit"), dict) else {}
    try:
        upstream_contamination_count = max(0, int(upstream.get("source_context_contamination_count") or 0))
    except (TypeError, ValueError):
        upstream_contamination_count = 0
    audit = {
        "privacy_status": "passed_spoken_only",
        "turn_count": len(turns),
        "source_turn_count": len(all_prepared_turns),
        "selection": {
            "last_turns": last_turns,
            "max_chars_per_turn": max_chars,
            "selected_source_turn_count": len(selected_raw_turns),
        },
        "recovered_from_raw_count": sum(bool(turn["recovered_from_raw"]) for turn in turns),
        "source_storage_contamination_count": local_contamination_count,
        "source_context_contamination_count": max(
            local_contamination_count,
            upstream_contamination_count,
        ),
        "truncated_count": sum(bool(turn.get("truncated_for_speech")) for turn in turns),
        "spoken_payload_sha256": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
        "full_source_spoken_payload_sha256": full_payload_sha256,
    }
    audit["source_context_privacy_status"] = (
        "contaminated_original_recovered_for_speech"
        if audit["source_context_contamination_count"]
        else "clean"
    )
    if upstream:
        audit["upstream_privacy_audit"] = {
            "privacy_status": upstream.get("privacy_status"),
            "source_context_privacy_status": upstream.get("source_context_privacy_status"),
            "source_context_contamination_count": upstream_contamination_count,
            "spoken_payload_sha256": upstream.get("spoken_payload_sha256"),
            "payload_hash_matches": upstream.get("spoken_payload_sha256") in {
                None,
                "",
                full_payload_sha256,
            },
        }
        if not audit["upstream_privacy_audit"]["payload_hash_matches"]:
            raise DialoguePrivacyError("Spoken-only export payload no longer matches its upstream privacy audit")
    return turns, audit


def build_spoken_only_export(data: dict[str, Any], *, source_path: Path) -> dict[str, Any]:
    turns, audit = prepare_dialogue_speech_turns(data)
    source_bytes = source_path.read_bytes()
    return {
        "schema_version": 1,
        "status": "prepared_privacy_safe_spoken_only",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_dialogue": str(source_path),
        "source_dialogue_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "dialogue_id": data.get("dialogue_id"),
        "privacy_audit": audit,
        "turns": [
            {
                "turn": turn["source_turn"],
                "speaker": turn["speaker"],
                "spoken": turn["text"],
                "spoken_sha256": turn["spoken_sha256"],
                "recovered_from_raw": turn["recovered_from_raw"],
            }
            for turn in turns
        ],
        "private_channels_included": False,
    }


def clone_with_reparsed_sections(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    """Repair parser fields in a copy; the source report remains immutable."""

    repaired = copy.deepcopy(data)
    counts = {"turns": 0, "changed": 0, "privacy_safe_spoken": 0}
    for item in repaired.get("transcript") or []:
        if not isinstance(item, dict):
            continue
        counts["turns"] += 1
        parsed = parse_structured_response(str(item.get("raw") or ""))
        before = (item.get("spoken"), item.get("private_mind"), item.get("truth_flags"))
        after = (parsed["spoken"], parsed["private_mind"], parsed["truth_flags"])
        if before != after:
            counts["changed"] += 1
        item["spoken"], item["private_mind"], item["truth_flags"] = after
        item["parser_privacy_safe_for_speech"] = parsed["privacy_safe_for_speech"]
        if parsed["privacy_safe_for_speech"]:
            counts["privacy_safe_spoken"] += 1
    repaired["parser_repair"] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "reparsed_copy_original_unchanged",
        **counts,
    }
    return repaired, counts


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
