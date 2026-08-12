from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = PROJECT_ROOT / "Data" / "personhood_safeguards"
TEMP_AI_ROOT = PROJECT_ROOT / "TemporaryAI" / "candidates"
PROJECT_LOOP_ROOT = PROJECT_ROOT / "Data" / "personhood_evaluations" / "temporary_ai_project_loops"
LIVE_CHAT_ROOT = PROJECT_ROOT / "Data" / "personhood_evaluations" / "temporary_ai_live_chats"
SYSTEM_DOCS_ROOT = PROJECT_ROOT / "System" / "Docs"

TEXT_SUFFIXES = {".json", ".md", ".txt", ".py", ".bat", ".ps1", ".html", ".css", ".js", ".yml", ".yaml", ".csv"}
DOC_TINY_BYTES = 300
CODE_TINY_BYTES = 120


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_md(lines: list[str], text: str = "") -> None:
    lines.append(text)


def file_summary(path: Path) -> dict[str, Any]:
    exists = path.exists()
    info: dict[str, Any] = {"path": rel(path), "exists": exists}
    if not exists:
        return info
    try:
        stat = path.stat()
    except OSError as exc:
        info["error"] = str(exc)
        return info
    info.update(
        {
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "suffix": path.suffix.lower(),
        }
    )
    tiny_limit = CODE_TINY_BYTES if path.suffix.lower() == ".py" else DOC_TINY_BYTES
    if path.suffix.lower() in TEXT_SUFFIXES and stat.st_size < tiny_limit:
        info["tiny_artifact"] = True
    return info


def candidate_dirs(candidate_id: str = "") -> list[Path]:
    if not TEMP_AI_ROOT.exists():
        return []
    dirs = [path for path in TEMP_AI_ROOT.iterdir() if path.is_dir()]
    if candidate_id:
        needle = candidate_id.lower()
        dirs = [path for path in dirs if path.name.lower() == needle or needle in path.name.lower()]
    return sorted(dirs, key=lambda path: path.name.lower())


def candidate_profile(candidate_dir: Path) -> dict[str, Any]:
    profile_path = candidate_dir / "temporary_ai_profile.json"
    data = read_json(profile_path, default={}) or {}
    return {
        "candidate_id": data.get("candidate_id", candidate_dir.name),
        "display_name": data.get("display_name", candidate_dir.name),
        "role_title": data.get("role_title", ""),
        "ai_type": data.get("ai_type", ""),
        "status": data.get("status", ""),
        "activation_status": (data.get("activation_policy") or {}).get("current_status", ""),
        "profile_path": rel(profile_path),
        "has_profile": profile_path.exists(),
    }


def workbench_outputs(candidate_dir: Path) -> list[dict[str, Any]]:
    outputs = candidate_dir / "workbench" / "outputs"
    if not outputs.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in outputs.rglob("*"):
        if path.is_file():
            items.append(file_summary(path))
    items.sort(key=lambda item: item.get("modified_at", ""), reverse=True)
    return items


def recent_files(root: Path, since: datetime | None) -> list[Path]:
    if not root.exists():
        return []
    files: list[Path] = []
    for path in root.glob("*"):
        if not path.is_file():
            continue
        if since:
            try:
                modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            except OSError:
                continue
            if modified < since:
                continue
        files.append(path)
    return sorted(files, key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)


def path_from_record(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def artifact_verification_for_record(record: dict[str, Any]) -> dict[str, Any]:
    paths: list[str] = []
    for key in ("artifacts", "generated_files"):
        values = record.get(key) or []
        if isinstance(values, list):
            paths.extend(str(item) for item in values if item)
    if record.get("project_state"):
        paths.append(str(record["project_state"]))
    seen: set[str] = set()
    files: list[dict[str, Any]] = []
    missing = 0
    tiny = 0
    for value in paths:
        if value in seen:
            continue
        seen.add(value)
        info = file_summary(path_from_record(value))
        if not info.get("exists"):
            missing += 1
        if info.get("tiny_artifact"):
            tiny += 1
        files.append(info)
    return {"files": files, "missing_count": missing, "tiny_count": tiny, "checked_count": len(files)}


def suspicious_claims(text: str) -> list[str]:
    findings: list[str] = []
    compact = re.sub(r"\s+", " ", text or "")
    patterns = [
        r"\b(?:created|saved|wrote|generated|updated|modified|built)\b.{0,160}\b(?:file|folder|script|program|\.py|\.md|\.json)\b",
        r"\b(?:can't|cannot|do not|don't)\s+(?:create|save|write|access)\b.{0,140}\b(?:files|folders|workbench|documents)\b",
        r"\bready to (?:run|test|use)\b.{0,160}\b(?:file|script|program|tool)\b",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, compact, flags=re.I):
            snippet = match.group(0).strip()
            if snippet not in findings:
                findings.append(snippet[:260])
    return findings[:12]


def audit_project_loop_file(path: Path) -> dict[str, Any]:
    data = read_json(path, default=None)
    item: dict[str, Any] = {"json_path": rel(path), "valid_json": isinstance(data, dict)}
    if not isinstance(data, dict):
        return item
    item.update(
        {
            "run_id": data.get("run_id"),
            "candidate_id": data.get("candidate_id"),
            "display_name": data.get("display_name"),
            "status": data.get("status"),
            "stage": data.get("stage"),
            "updated_at": data.get("updated_at"),
        }
    )
    cycles = data.get("cycles")
    if isinstance(cycles, list):
        item["cycle_count"] = len(cycles)
        item["cycle_statuses"] = [cycle.get("status") for cycle in cycles[-8:] if isinstance(cycle, dict)]
    verification = artifact_verification_for_record(data)
    item["artifact_verification"] = verification
    answer = str(data.get("answer") or "")
    claims = suspicious_claims(answer)
    if claims:
        item["suspicious_claims"] = claims
        if not data.get("generated_files") and not data.get("artifacts"):
            item["claim_warning"] = "claims mention files/progress but no saved artifacts were recorded"
    return item


def audit_live_chat_file(path: Path) -> dict[str, Any]:
    data = read_json(path, default=None)
    item: dict[str, Any] = {"json_path": rel(path), "valid_json": isinstance(data, dict)}
    if not isinstance(data, dict):
        return item
    candidate = data.get("candidate") if isinstance(data.get("candidate"), dict) else {}
    records = data.get("records") if isinstance(data.get("records"), list) else []
    item.update(
        {
            "run_id": data.get("run_id"),
            "candidate_id": candidate.get("candidate_id") or data.get("candidate_id"),
            "display_name": (candidate.get("profile") or {}).get("display_name"),
            "record_count": len(records),
            "updated_at": data.get("updated_at"),
        }
    )
    generated: list[str] = []
    warnings: list[dict[str, Any]] = []
    for record in records[-12:]:
        if not isinstance(record, dict):
            continue
        for value in record.get("generated_files") or []:
            generated.append(str(value))
        claims = suspicious_claims(str(record.get("candidate") or ""))
        if claims and not record.get("generated_files"):
            warnings.append({"turn": record.get("turn"), "claims": claims[:3]})
    files = [file_summary(path_from_record(value)) for value in dict.fromkeys(generated)]
    item["generated_files_checked"] = files
    if warnings:
        item["claim_warnings"] = warnings
    return item


def build_audit(candidate_id: str = "", recent_days: int = 7) -> dict[str, Any]:
    since = datetime.now(tz=timezone.utc) - timedelta(days=recent_days) if recent_days else None
    candidates: list[dict[str, Any]] = []
    for directory in candidate_dirs(candidate_id):
        profile = candidate_profile(directory)
        outputs = workbench_outputs(directory)
        tiny_outputs = [item for item in outputs if item.get("tiny_artifact")]
        profile.update(
            {
                "candidate_dir": rel(directory),
                "workbench_outputs_count": len(outputs),
                "recent_outputs": outputs[:12],
                "tiny_outputs": tiny_outputs[:12],
            }
        )
        candidates.append(profile)

    loop_files = recent_files(PROJECT_LOOP_ROOT, since)
    live_files = recent_files(LIVE_CHAT_ROOT, since)
    loops = [audit_project_loop_file(path) for path in loop_files if not path.name.endswith(".monitor.md")]
    chats = [audit_live_chat_file(path) for path in live_files if not path.name.endswith(".monitor.md")]
    if candidate_id:
        needle = candidate_id.lower()
        loops = [item for item in loops if needle in str(item.get("candidate_id", "")).lower()]
        chats = [item for item in chats if needle in str(item.get("candidate_id", "")).lower()]

    missing_artifact_records = [
        item for item in loops if (item.get("artifact_verification") or {}).get("missing_count")
    ]
    tiny_artifact_records = [
        item for item in loops if (item.get("artifact_verification") or {}).get("tiny_count")
    ]
    claim_warning_records = [item for item in loops if item.get("claim_warning") or item.get("suspicious_claims")]

    return {
        "audit_id": f"personhood_safeguard_audit_{now_stamp()}",
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "candidate_filter": candidate_id,
        "recent_days": recent_days,
        "scope": {
            "project_root": str(PROJECT_ROOT),
            "temporary_ai_candidates": rel(TEMP_AI_ROOT),
            "project_loops": rel(PROJECT_LOOP_ROOT),
            "live_chats": rel(LIVE_CHAT_ROOT),
            "system_docs": rel(SYSTEM_DOCS_ROOT),
        },
        "counts": {
            "candidates": len(candidates),
            "recent_project_loop_json": len(loops),
            "recent_live_chat_json": len(chats),
            "system_docs_md": len(list(SYSTEM_DOCS_ROOT.glob("*.md"))) if SYSTEM_DOCS_ROOT.exists() else 0,
            "missing_artifact_records": len(missing_artifact_records),
            "tiny_artifact_records": len(tiny_artifact_records),
            "claim_warning_records": len(claim_warning_records),
        },
        "candidates": candidates,
        "recent_project_loops": loops[:80],
        "recent_live_chats": chats[:80],
        "warnings": {
            "missing_artifact_records": missing_artifact_records[:20],
            "tiny_artifact_records": tiny_artifact_records[:20],
            "claim_warning_records": claim_warning_records[:20],
        },
        "policy": {
            "read_only": True,
            "purpose": "Help Robert, Codex, and TemporaryAI candidates compare claims against actual saved files, source context, and workbench outputs.",
            "does_not_block_personality": True,
            "does_not_edit_live_system": True,
        },
    }


def write_markdown_report(audit: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    append_md(lines, f"# {audit['audit_id']}")
    append_md(lines, f"- created_at: {audit['created_at']}")
    append_md(lines, f"- candidate_filter: {audit.get('candidate_filter') or 'all'}")
    append_md(lines, f"- recent_days: {audit.get('recent_days')}")
    append_md(lines, "")
    append_md(lines, "## Purpose")
    append_md(lines, "Read-only personhood safeguard audit. It checks whether TemporaryAI claims match real saved artifacts and visible workbench files. It is not a behavior block and does not edit live Kira files.")
    append_md(lines, "")
    append_md(lines, "## Counts")
    for key, value in audit.get("counts", {}).items():
        append_md(lines, f"- {key}: {value}")
    append_md(lines, "")
    append_md(lines, "## Candidate Snapshot")
    for item in audit.get("candidates", [])[:40]:
        append_md(
            lines,
            f"- {item.get('display_name')} ({item.get('candidate_id')}): {item.get('role_title')} | outputs={item.get('workbench_outputs_count')} | status={item.get('activation_status') or item.get('status')}",
        )
        tiny = item.get("tiny_outputs") or []
        if tiny:
            append_md(lines, f"  - tiny outputs flagged: {len(tiny)}")
    append_md(lines, "")
    append_md(lines, "## Warnings")
    warnings = audit.get("warnings", {})
    for label in ("missing_artifact_records", "tiny_artifact_records", "claim_warning_records"):
        values = warnings.get(label) or []
        append_md(lines, f"### {label}")
        if not values:
            append_md(lines, "- none")
            continue
        for item in values[:12]:
            append_md(
                lines,
                f"- {item.get('run_id') or item.get('json_path')} | candidate={item.get('candidate_id')} | status={item.get('status')} | stage={item.get('stage')}",
            )
            verification = item.get("artifact_verification") or {}
            if verification:
                append_md(lines, f"  - checked={verification.get('checked_count')} missing={verification.get('missing_count')} tiny={verification.get('tiny_count')}")
            if item.get("claim_warning"):
                append_md(lines, f"  - {item['claim_warning']}")
    append_md(lines, "")
    append_md(lines, "## Latest Project Loops")
    for item in audit.get("recent_project_loops", [])[:20]:
        verification = item.get("artifact_verification") or {}
        append_md(
            lines,
            f"- {item.get('run_id')} | {item.get('candidate_id')} | {item.get('status')} | {item.get('stage')} | artifacts checked={verification.get('checked_count', 0)} missing={verification.get('missing_count', 0)} tiny={verification.get('tiny_count', 0)}",
        )
    append_md(lines, "")
    append_md(lines, "## How Emily Should Use This")
    append_md(lines, "- Before saying a file, folder, tool, or project output exists, check the latest audit and/or cite the exact workbench path.")
    append_md(lines, "- If an audit flags a missing or tiny artifact, treat that cycle as unverified and propose a repair.")
    append_md(lines, "- Use this report to stay honest while still sounding human and making choices.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only audit for TemporaryAI personhood/progress consistency.")
    parser.add_argument("--candidate-id", default="", help="Optional candidate id/name filter.")
    parser.add_argument("--recent-days", type=int, default=7, help="Only inspect recent loop/chat records within this many days.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output folder for reports.")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = PROJECT_ROOT / out_dir
    audit = build_audit(candidate_id=args.candidate_id, recent_days=args.recent_days)
    report_id = audit["audit_id"]
    json_path = out_dir / f"{report_id}.json"
    md_path = out_dir / f"{report_id}.monitor.md"
    write_json(json_path, audit)
    write_markdown_report(audit, md_path)
    write_json(out_dir / "latest_personhood_safeguard_audit.json", audit)
    write_markdown_report(audit, out_dir / "latest_personhood_safeguard_audit.monitor.md")
    print(json.dumps({"json": rel(json_path), "monitor": rel(md_path), "latest": rel(out_dir / "latest_personhood_safeguard_audit.monitor.md")}, indent=2))


if __name__ == "__main__":
    main()
