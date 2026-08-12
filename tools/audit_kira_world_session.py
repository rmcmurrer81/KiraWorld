#!/usr/bin/env python3
"""Build a non-invasive audit of one Kira World activation session.

The report keeps three things separate:

* public conversation: what Robert and Kira said;
* runtime/body evidence: what the world actually reported;
* private artifacts: counted and integrity-checked only, never copied into the
  public report.

It does not launch the world, play audio, promote memory, or infer that a
spoken claim happened physically.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "Data" / "runtime"
LIFE_LOG = RUNTIME_DIR / "kira_world_life_loop_log.jsonl"
CHAT_LOG = RUNTIME_DIR / "kira_world_chat_log.jsonl"
STATE_PATH = RUNTIME_DIR / "kira_world_shell_state.json"
OUTPUT_ROOT = ROOT / "Data" / "world_tests" / "kira_world_session_audits"

ARTIFACT_ROOTS = (
    ROOT / "Data" / "life_sessions",
    ROOT / "Data" / "daily_life",
    ROOT / "Data" / "messages" / "kira_to_robert",
    ROOT / "Data" / "tablet" / "kira",
    ROOT / "Data" / "creative_projects" / "kira",
    ROOT / "Data" / "core_ai_workbenches" / "kira",
    ROOT / "Data" / "reading" / "sessions",
)
PRIVATE_ARTIFACT_ROOTS = (
    ROOT / "Data" / "life_sessions",
    ROOT / "Data" / "daily_life",
    ROOT / "Data" / "creative_projects" / "kira",
    ROOT / "Data" / "core_ai_workbenches" / "kira",
)

PRIVATE_PATH_RE = re.compile(
    r"(?:^|[/\\_.-])(private|inner[_ -]?life|doctor|confession|dream)(?:$|[/\\_.-])",
    re.IGNORECASE,
)
SESSION_END_EVENTS = {"deactivate", "safe_stop_active_ai", "shell_safe_close_requested"}
RUNTIME_SNAPSHOT_FRESH_SECONDS = 8.0


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def iso(value: datetime | None) -> str:
    return value.astimezone(timezone.utc).isoformat() if value else ""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    if not path.exists():
        return records, [{"line": 0, "reason": "missing_file"}]
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, raw in enumerate(handle, 1):
            text = raw.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                errors.append({"line": line_number, "reason": f"invalid_json:{exc.msg}"})
                continue
            if not isinstance(value, dict):
                errors.append({"line": line_number, "reason": "record_not_object"})
                continue
            value["_line"] = line_number
            records.append(value)
    return records, errors


def record_time(record: dict[str, Any]) -> datetime | None:
    return parse_time(record.get("at") or record.get("created_at") or record.get("updated_at"))


def _candidate_matches(record: dict[str, Any], candidate: str = "kira") -> bool:
    values = (
        record.get("candidate"),
        record.get("previous"),
        record.get("active_candidate"),
        record.get("speaker_id"),
        record.get("to"),
    )
    return any(str(value or "").strip().lower() == candidate for value in values)


def select_session(
    life_records: list[dict[str, Any]],
    *,
    requested_start: datetime | None = None,
    candidate: str = "kira",
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or utc_now()
    activations = [
        record
        for record in life_records
        if record.get("event") == "activate"
        and str(record.get("candidate") or "").lower() == candidate
        and record_time(record)
    ]
    if requested_start:
        start = requested_start
        activation = next(
            (record for record in reversed(activations) if record_time(record) and record_time(record) <= start),
            None,
        )
    else:
        activation = activations[-1] if activations else None
        start = record_time(activation or {})
    if not start:
        raise ValueError(f"No {candidate} activation was found; pass --start with an ISO timestamp if needed.")

    end_record = None
    for record in life_records:
        when = record_time(record)
        if not when or when < start or record.get("event") not in SESSION_END_EVENTS:
            continue
        if record.get("event") == "shell_safe_close_requested" or _candidate_matches(record, candidate):
            end_record = record
            break
    end = record_time(end_record or {}) or now
    return {
        "candidate": candidate,
        "start": start,
        "end": end,
        "status": "closed" if end_record else "open_at_audit_time",
        "activation_record": activation,
        "end_record": end_record,
    }


def in_window(record: dict[str, Any], start: datetime, end: datetime) -> bool:
    when = record_time(record)
    return bool(when and start <= when <= end)


def public_chat_record(record: dict[str, Any]) -> dict[str, Any] | None:
    speaker = str(record.get("speaker") or "").strip()
    text = str(record.get("text") or "").strip()
    if not speaker or not text or speaker.lower() == "system":
        return None
    return {
        "at": str(record.get("at") or ""),
        "speaker": speaker,
        "to": str(record.get("to") or ""),
        "text": text,
        "location": str(record.get("location") or ""),
        "source_line": record.get("_line"),
    }


def _runtime_place_summary(entry: dict[str, Any]) -> str:
    place = entry.get("place")
    if isinstance(place, dict):
        return str(place.get("summary") or place.get("label") or place.get("areaId") or "").strip()
    return str(place or entry.get("body_place") or "").strip()


def _current_place_without_route_language(value: Any) -> str:
    """Keep a physical place separate from a route/destination description."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    text = re.split(
        r",?\s*(?:moving|walking|waiting)(?:\s+or\s+(?:moving|walking|waiting))?\s+near\s+the\s+route\s+toward\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" ,")
    return text


def _runtime_destination(entry: dict[str, Any]) -> str:
    return str(entry.get("autonomousIntent") or entry.get("autonomous_intent") or "").strip()


def _runtime_evidence_for_claim(
    record: dict[str, Any],
    runtime_samples: list[dict[str, Any]],
    state: dict[str, Any],
) -> dict[str, Any]:
    claim_at = record_time(record)
    candidates: list[tuple[datetime, str, dict[str, Any]]] = []
    if claim_at:
        for sample in runtime_samples:
            when = record_time(sample)
            if when and when <= claim_at:
                candidates.append((when, "avatar_runtime_snapshot", sample))
        state_entry = ((state.get("last_avatar_positions") or {}).get("kira") or {})
        if isinstance(state_entry, dict):
            when = parse_time(state_entry.get("updated_at"))
            if when and when <= claim_at:
                candidates.append((when, "shell_state_avatar_position", state_entry))
    if not candidates or not claim_at:
        return {
            "available": False,
            "fresh": False,
            "age_seconds": None,
            "source": "none",
            "current_place": "",
            "historical_place": "",
            "destination": "",
            "destination_only": False,
        }

    when, source, entry = max(candidates, key=lambda item: item[0])
    age_seconds = max(0.0, (claim_at - when).total_seconds())
    fresh = age_seconds <= RUNTIME_SNAPSHOT_FRESH_SECONDS
    raw_place = _runtime_place_summary(entry)
    current_place = _current_place_without_route_language(raw_place)
    destination = _runtime_destination(entry)
    spoken = str(record.get("spoken_excerpt") or "").lower()
    destination_words = [
        word
        for word in re.findall(r"[a-z0-9]+", destination.lower())
        if len(word) >= 5 and word not in {"public", "entrance", "walk", "route", "toward"}
    ]
    claim_mentions_destination = bool(destination_words and any(word in spoken for word in destination_words))
    place_proves_destination = bool(
        destination_words
        and any(word in current_place.lower() for word in destination_words)
        and "route toward" not in raw_place.lower()
    )
    destination_only = bool(destination and claim_mentions_destination and not place_proves_destination)
    return {
        "available": True,
        "fresh": fresh,
        "age_seconds": round(age_seconds, 3),
        "source": source,
        "snapshot_at": iso(when),
        "current_place": current_place,
        "historical_place": current_place,
        "destination": destination,
        "destination_only": destination_only,
        "entry": entry,
    }


def body_truth_comparison(
    record: dict[str, Any],
    runtime_samples: list[dict[str, Any]] | None = None,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = _runtime_evidence_for_claim(record, runtime_samples or [], state or {})
    fresh = evidence["fresh"] is True
    classification = "speech_recorded_separately_from_runtime_truth"
    classification_reason = "Speech is not physical proof."
    if not fresh:
        classification = "unsupported_by_fresh_runtime_evidence"
        classification_reason = "The latest body telemetry at the time of this claim was missing or stale."
    elif evidence["destination_only"]:
        classification = "unsupported_by_fresh_runtime_evidence"
        classification_reason = "The named place was only a navigation destination; the current-place evidence did not prove arrival."

    stale_text = "unknown (latest body telemetry is stale or unavailable)"
    current_place = evidence["current_place"] if fresh else stale_text
    return {
        "at": str(record.get("at") or ""),
        "spoken_claim_excerpt": str(record.get("spoken_excerpt") or ""),
        "runtime_body_place": current_place or "unknown",
        "historical_runtime_body_place": evidence["historical_place"] if not fresh else "",
        "runtime_affordances": str(record.get("affordances") or "none reported") if fresh else stale_text,
        "runtime_posture": str(record.get("posture") or "none reported") if fresh else stale_text,
        "runtime_held_prop": str(record.get("held_prop") or "none") if fresh else stale_text,
        "runtime_snapshot_at": evidence.get("snapshot_at", ""),
        "runtime_snapshot_age_seconds": evidence["age_seconds"],
        "runtime_snapshot_fresh": fresh,
        "runtime_evidence_source": evidence["source"],
        "runtime_navigation_destination": evidence["destination"],
        "navigation_destination_is_not_arrival": bool(evidence["destination_only"]),
        "classification": classification,
        "classification_reason": classification_reason,
        "physical_action_proven_by_speech": False,
        "source_line": record.get("_line"),
    }


def dedupe_body_truth(
    records: list[dict[str, Any]],
    runtime_samples: list[dict[str, Any]] | None = None,
    state: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Collapse duplicate writes from older runtimes while preserving later claims."""
    result: list[dict[str, Any]] = []
    last_key: tuple[str, str, str, str] | None = None
    last_time: datetime | None = None
    for record in records:
        item = body_truth_comparison(record, runtime_samples, state)
        key = (
            item["spoken_claim_excerpt"],
            item["runtime_body_place"],
            item["runtime_posture"],
            item["runtime_held_prop"],
        )
        when = record_time(record)
        if key == last_key and when and last_time and (when - last_time).total_seconds() <= 2:
            continue
        result.append(item)
        last_key = key
        last_time = when
    return result


def safe_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return "outside_project_root"


def is_private_artifact_path(path: Path) -> bool:
    resolved = path.resolve()
    for root in PRIVATE_ARTIFACT_ROOTS:
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return bool(PRIVATE_PATH_RE.search(safe_relative(path)))


def source_integrity(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {"path": safe_relative(path), "exists": False}
    stat = path.stat()
    return {
        "path": safe_relative(path),
        "exists": True,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "sha256": sha256_file(path),
    }


def changed_artifacts(start: datetime, end: datetime, limit: int = 500) -> dict[str, Any]:
    public: list[dict[str, Any]] = []
    private_count = 0
    private_bytes = 0
    examined = 0
    for root in ARTIFACT_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            examined += 1
            stat = path.stat()
            modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
            if not start <= modified <= end:
                continue
            relative = safe_relative(path)
            if is_private_artifact_path(path):
                private_count += 1
                private_bytes += stat.st_size
                continue
            if len(public) >= limit:
                continue
            public.append(
                {
                    "path": relative,
                    "size_bytes": stat.st_size,
                    "modified_at": modified.isoformat(),
                    "sha256": sha256_file(path),
                    "content_reviewed": False,
                }
            )
    public.sort(key=lambda item: (item["modified_at"], item["path"]))
    return {
        "public_or_personal_metadata": public,
        "private_artifacts": {
            "count": private_count,
            "total_bytes": private_bytes,
            "paths_and_contents_disclosed": False,
        },
        "examined_file_count": examined,
        "public_limit": limit,
        "public_limit_reached": len(public) >= limit,
    }


def _load_state(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def latest_body_snapshot(state: dict[str, Any], start: datetime, end: datetime) -> dict[str, Any]:
    entry = ((state.get("last_avatar_positions") or {}).get("kira") or {})
    if not isinstance(entry, dict):
        return {"available": False}
    when = parse_time(entry.get("updated_at"))
    if not when or not start <= when <= end:
        return {"available": False, "reason": "latest snapshot is outside the selected session"}
    age_seconds = max(0.0, (end - when).total_seconds())
    fresh = age_seconds <= RUNTIME_SNAPSHOT_FRESH_SECONDS
    mind_body = entry.get("mindBodyTruth") if isinstance(entry.get("mindBodyTruth"), dict) else {}
    held = entry.get("activeHeldProp") if isinstance(entry.get("activeHeldProp"), dict) else {}
    posture = entry.get("postureInteraction") or entry.get("postureState")
    historical_place = _current_place_without_route_language(_runtime_place_summary(entry))
    destination = _runtime_destination(entry)
    return {
        "available": True,
        "updated_at": entry.get("updated_at"),
        "snapshot_age_seconds_at_session_end": round(age_seconds, 3),
        "fresh_at_session_end": fresh,
        "current_runtime_truth_available": fresh,
        "location": entry.get("location"),
        "position": entry.get("position"),
        "action": entry.get("action") if fresh else None,
        "historical_action": entry.get("action"),
        "place": historical_place if fresh else None,
        "historical_place": historical_place,
        "navigation_destination": destination,
        "navigation_destination_is_not_arrival": bool(destination),
        "held_prop": {
            "kind": held.get("kind"),
            "grounded": held.get("grounded") is True,
            "source_removed_or_hidden": held.get("sourceRemovedOrHidden") is True,
        }
        if held and fresh
        else None,
        "posture": posture if fresh else None,
        "mind_body_agrees": mind_body.get("agrees") if fresh else None,
        "mind_body_mismatch_reasons": (mind_body.get("mismatchReasons") or []) if fresh else [],
    }


def build_audit(
    life_records: list[dict[str, Any]],
    chat_records: list[dict[str, Any]],
    state: dict[str, Any],
    session: dict[str, Any],
    *,
    life_errors: list[dict[str, Any]] | None = None,
    chat_errors: list[dict[str, Any]] | None = None,
    scan_artifacts: bool = True,
    artifact_limit: int = 500,
) -> dict[str, Any]:
    start: datetime = session["start"]
    end: datetime = session["end"]
    life = [record for record in life_records if in_window(record, start, end)]
    chats = [public_chat_record(record) for record in chat_records if in_window(record, start, end)]
    chats = [record for record in chats if record]
    runtime_samples = [record for record in life if record.get("event") == "avatar_runtime_snapshot"]
    truth = dedupe_body_truth(
        [record for record in life if record.get("event") == "kira_private_body_truth_note"],
        runtime_samples,
        state,
    )
    event_counts = Counter(str(record.get("event") or "unlabeled") for record in life)
    action_counts = Counter(
        str(record.get("action") or "")
        for record in life
        if str(record.get("action") or "").strip()
    )
    location_counts = Counter(
        str(record.get("location") or "")
        for record in life
        if str(record.get("location") or "").strip()
    )
    return {
        "schema_version": 1,
        "generated_at": iso(utc_now()),
        "scope": {
            "candidate": "kira",
            "session_start": iso(start),
            "session_end": iso(end),
            "session_status": session["status"],
            "audio_played": False,
            "world_or_model_launched": False,
            "memory_promoted": False,
        },
        "truth_contract": {
            "spoken_words_may_be_truthful_false_playful_flirtatious_boastful_or_evasive": True,
            "spoken_words_are_not_physical_proof": True,
            "runtime_body_evidence_is_preserved_separately": True,
            "private_inner_mind_content_copied_to_report": False,
        },
        "source_integrity": {
            "life_log": source_integrity(LIFE_LOG),
            "chat_log": source_integrity(CHAT_LOG),
            "shell_state": source_integrity(STATE_PATH),
            "life_jsonl_errors": life_errors or [],
            "chat_jsonl_errors": chat_errors or [],
        },
        "summary": {
            "life_event_count": len(life),
            "public_chat_turn_count": len(chats),
            "speaker_counts": dict(Counter(record["speaker"] for record in chats)),
            "event_counts": dict(event_counts),
            "action_counts": dict(action_counts),
            "location_counts": dict(location_counts),
            "body_truth_comparison_count": len(truth),
            "runtime_sample_count": len(runtime_samples),
        },
        "public_conversation": chats,
        "spoken_claim_runtime_comparisons": truth,
        "runtime_body_samples": runtime_samples,
        "latest_body_snapshot": latest_body_snapshot(state, start, end),
        "changed_artifacts": changed_artifacts(start, end, artifact_limit) if scan_artifacts else {"scan_skipped": True},
    }


def _cell(value: Any, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip().replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def render_markdown(audit: dict[str, Any]) -> str:
    scope = audit["scope"]
    summary = audit["summary"]
    lines = [
        "# Kira World Session Audit",
        "",
        f"- Session: `{scope['session_start']}` to `{scope['session_end']}` ({scope['session_status']})",
        f"- Public chat turns: {summary['public_chat_turn_count']}",
        f"- Runtime/life events: {summary['life_event_count']}",
        f"- Spoken/runtime comparisons: {summary['body_truth_comparison_count']}",
        "- Audio played by audit: no",
        "- Memory promoted by audit: no",
        "",
        "Spoken words are preserved as speech, not treated as proof. Runtime body evidence is reported separately. Private inner-mind content is not copied here.",
        "",
        "## Public conversation",
        "",
    ]
    chats = audit["public_conversation"]
    if chats:
        for record in chats:
            lines.append(f"- `{_cell(record['at'], 40)}` **{_cell(record['speaker'], 40)}:** {_cell(record['text'], 800)}")
    else:
        lines.append("- No public chat turns in this session.")
    lines.extend(["", "## Spoken claims compared with runtime body truth", ""])
    comparisons = audit["spoken_claim_runtime_comparisons"]
    if comparisons:
        lines.extend([
            "| Time | Spoken claim excerpt | Runtime place | Snapshot freshness | Classification |",
            "| --- | --- | --- | --- | --- |",
        ])
        for item in comparisons:
            age = item.get("runtime_snapshot_age_seconds")
            freshness = f"fresh ({age}s old)" if item.get("runtime_snapshot_fresh") else f"stale/unavailable ({age if age is not None else 'unknown'}s old)"
            lines.append(
                f"| {_cell(item['at'], 40)} | {_cell(item['spoken_claim_excerpt'])} | "
                f"{_cell(item['runtime_body_place'], 120)} | {_cell(freshness, 80)} | "
                f"{_cell(item['classification'], 80)} |"
            )
    else:
        lines.append("- No claim/body comparison records were produced in this session.")
    lines.extend(["", "## Counts", ""])
    lines.append(f"- Events: `{json.dumps(summary['event_counts'], sort_keys=True)}`")
    lines.append(f"- Actions: `{json.dumps(summary['action_counts'], sort_keys=True)}`")
    lines.append(f"- Locations: `{json.dumps(summary['location_counts'], sort_keys=True)}`")
    artifacts = audit["changed_artifacts"]
    if not artifacts.get("scan_skipped"):
        lines.extend([
            "",
            "## Files changed during the session",
            "",
            f"- Public/personal metadata records: {len(artifacts['public_or_personal_metadata'])}",
            f"- Private artifacts counted without path/content disclosure: {artifacts['private_artifacts']['count']}",
        ])
        for item in artifacts["public_or_personal_metadata"]:
            lines.append(f"- `{item['path']}` — {item['size_bytes']} bytes — SHA-256 `{item['sha256']}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="", help="ISO UTC/local timestamp; defaults to the latest Kira activation.")
    parser.add_argument("--output-dir", default="", help="Default: Data/world_tests/kira_world_session_audits/<timestamp>.")
    parser.add_argument("--no-artifact-scan", action="store_true")
    parser.add_argument("--artifact-limit", type=int, default=500)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    requested_start = parse_time(args.start) if args.start else None
    if args.start and requested_start is None:
        raise SystemExit("--start must be an ISO timestamp")
    life_records, life_errors = read_jsonl(LIFE_LOG)
    chat_records, chat_errors = read_jsonl(CHAT_LOG)
    session = select_session(life_records, requested_start=requested_start)
    audit = build_audit(
        life_records,
        chat_records,
        _load_state(STATE_PATH),
        session,
        life_errors=life_errors,
        chat_errors=chat_errors,
        scan_artifacts=not args.no_artifact_scan,
        artifact_limit=max(1, args.artifact_limit),
    )
    if args.output_dir:
        output_dir = Path(args.output_dir)
        if not output_dir.is_absolute():
            output_dir = ROOT / output_dir
    else:
        stamp = utc_now().strftime("%Y%m%d_%H%M%S")
        output_dir = OUTPUT_ROOT / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / "report.json"
    md_path = output_dir / "report.md"
    json_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(audit), encoding="utf-8")
    print(json.dumps({"report": safe_relative(json_path), "markdown": safe_relative(md_path), "status": audit["scope"]["session_status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
