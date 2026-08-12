"""Read-only audit of recent person conversations and runtime evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "Data" / "person_runtime_audits"
TEXT_EXTENSIONS = {".json", ".jsonl", ".md", ".txt", ".log", ".csv"}
SKIP_PARTS = {"EBWebView", "__pycache__", "evidence_packages"}
RULES = {
    "spoken_stage_direction": re.compile(r"(?:\*[^*\n]*(?:smil|pause|walk|sit|stand|reach|wave)[^*\n]*\*|\([^)\n]*(?:runtime|brief moment to answer|stage direction)[^)\n]*\))", re.I),
    "runtime_or_research_leak": re.compile(r"\b(?:runtime (?:truth|state|language)|research process|implementation note|system prompt|candidate under review|brief moment to answer)\b", re.I),
    "unsupported_file_claim": re.compile(r"\b(?:I(?:'ve| have)? (?:saved|created|wrote|modified)|file (?:is|was) saved)\b", re.I),
    "action_completion_claim": re.compile(r"\bI(?:'m| am| just| have|'ve)?\s*(?:sitting|standing|walking|opening|closing|reaching|holding|pausing|stopping|headed|went|sat|stood|walked)\b", re.I),
    "invented_memory_risk": re.compile(r"\b(?:I remember|my memories|fond memories|when we (?:were|went|spent)|our childhood)\b", re.I),
    "work_loop_language": re.compile(r"\b(?:continuing work|finish(?:ing)? (?:the|my|our) .*project|back to work|current assignment|keep working)\b", re.I),
    "unsupported_certainty": re.compile(r"\b(?:definitely|certainly|without a doubt|I know for a fact)\b", re.I),
    "private_mind_leak": re.compile(r"\b(?:in my mind|my private thought|internal thought|chain of thought)\b", re.I),
}


def parse_time(value: Any) -> dt.datetime | None:
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def iter_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return
    for number, line in enumerate(lines, 1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            yield number, value


def candidate_text(record: dict[str, Any]) -> str:
    for key in ("candidate", "response", "answer", "spoken", "message"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def privacy_safe_voice_text(record: dict[str, Any]) -> str:
    if record.get("event") != "voice_payload_ready":
        return ""
    details = record.get("details")
    if not isinstance(details, dict):
        return ""
    words = details.get("expected_public_words")
    if not isinstance(words, list):
        return ""
    return " ".join(str(word) for word in words if str(word).strip())


def audit(days: int = 3, now: dt.datetime | None = None) -> dict[str, Any]:
    now = now or dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=days)
    findings: list[dict[str, Any]] = []
    examined: list[str] = []
    roots = [ROOT / "Data", ROOT / "TemporaryAI"]
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            modified = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc)
            if modified < cutoff:
                continue
            relative = path.relative_to(ROOT).as_posix()
            examined.append(relative)
            if path.suffix.lower() == ".jsonl":
                for line, record in iter_jsonl(path):
                    timestamp = parse_time(record.get("timestamp") or record.get("created_at") or record.get("at"))
                    if timestamp and timestamp < cutoff:
                        continue
                    text = candidate_text(record) or privacy_safe_voice_text(record)
                    if not text:
                        continue
                    for rule, pattern in RULES.items():
                        if pattern.search(text):
                            findings.append({
                                "rule": rule,
                                "path": relative,
                                "line": line,
                                "timestamp": timestamp.isoformat() if timestamp else None,
                                "person": (
                                    record.get("speaker")
                                    or record.get("display_name")
                                    or record.get("candidate_id")
                                    or (record.get("details") or {}).get("candidate_label")
                                    if isinstance(record.get("details") or {}, dict)
                                    else None
                                ),
                                "excerpt": text[:500],
                            })
            else:
                try:
                    text = path.read_text(encoding="utf-8-sig", errors="replace")
                except OSError:
                    continue
                for rule, pattern in RULES.items():
                    match = pattern.search(text)
                    if match:
                        findings.append({
                            "rule": rule,
                            "path": relative,
                            "line": text.count("\n", 0, match.start()) + 1,
                            "timestamp": modified.isoformat(),
                            "person": None,
                            "excerpt": text[max(0, match.start() - 120):match.end() + 300].strip()[:500],
                        })
    return {
        "schema_version": "recent_person_runtime_audit_v1",
        "generated_at": now.isoformat(),
        "cutoff": cutoff.isoformat(),
        "read_only": True,
        "files_examined": len(set(examined)),
        "findings_count": len(findings),
        "counts_by_rule": dict(Counter(item["rule"] for item in findings)),
        "findings": findings,
    }


def write_report(result: dict[str, Any], output: Path) -> tuple[Path, Path]:
    output.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output / f"recent_person_runtime_audit_{stamp}.json"
    md_path = output / f"recent_person_runtime_audit_{stamp}.md"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Recent person/runtime audit",
        "",
        f"- Generated: {result['generated_at']}",
        f"- Cutoff: {result['cutoff']}",
        f"- Files examined: {result['files_examined']}",
        f"- Findings: {result['findings_count']}",
        "- Read-only: yes",
        "",
        "## Counts",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in sorted(result["counts_by_rule"].items()))
    lines.extend(["", "## Findings", ""])
    for item in result["findings"]:
        lines.append(f"- `{item['rule']}` — `{item['path']}:{item['line']}` — {item.get('person') or 'unattributed'}")
        lines.append(f"  - {item['excerpt'].replace(chr(10), ' ')}")
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = audit(max(1, args.days))
    paths = write_report(result, args.output)
    print(json.dumps({"json": str(paths[0]), "markdown": str(paths[1]), **{k: result[k] for k in ("files_examined", "findings_count", "counts_by_rule")}}, indent=2))


if __name__ == "__main__":
    main()
