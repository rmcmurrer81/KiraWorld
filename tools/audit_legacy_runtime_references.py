"""
Audit active Kira runtime files for accidental legacy archive dependencies.

This does not scan the legacy archive itself. It checks current tools,
curriculum, source packs, prompts, and launchers for references to old Kira
material, then classifies each hit as policy text, active-looking, or direct
path dependency.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "Data" / "audits"

SCAN_ROOTS = [
    PROJECT_ROOT / "Core",
    PROJECT_ROOT / "tools",
    PROJECT_ROOT / "Data" / "school" / "curriculum",
    PROJECT_ROOT / "Data" / "school" / "source_packs",
    PROJECT_ROOT / "Data" / "profiles",
    PROJECT_ROOT / "System" / "Prompts",
]
ROOT_FILE_GLOBS = ["*.bat", "*.ps1", "*.py", "*.json"]

TEXT_SUFFIXES = {
    ".bat",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}

PATTERN = re.compile(r"\b(oldkira|old kira|legacy_reference|legacy reference)\b", re.IGNORECASE)
DIRECT_PATH_PATTERN = re.compile(
    r"(legacy_reference[\\/]+oldkira|oldkira[\\/]|old kira[\\/])",
    re.IGNORECASE,
)
POLICY_WORDS = re.compile(
    r"(archive|archived|quarantine|quarantined|reference only|not memory|not current|not canon|not proof|policy)",
    re.IGNORECASE,
)


def iter_candidate_files() -> list[Path]:
    files: set[Path] = set()
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                files.add(path)
    for glob in ROOT_FILE_GLOBS:
        for path in PROJECT_ROOT.glob(glob):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                files.add(path)
    return sorted(files)


def classify(path: Path, line: str) -> str:
    normalized = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    if normalized == "tools/audit_legacy_runtime_references.py":
        return "audit_tool_self_reference"
    if normalized in {
        "tools/memory_claim_check.py",
        "tools/readiness_check.py",
        "tools/run_kira_turing_psych_eval.py",
    }:
        return "guardrail_or_readiness_check"
    if normalized == "tools/run_kira_school_v2.py" and "oldkira" in line.lower():
        return "guardrail_or_readiness_check"
    if normalized in {
        "System/Prompts/kira_launch_context_v1.md",
        "System/Prompts/lisa_launch_context_v1.md",
    }:
        return "policy_or_quarantine_note"
    if DIRECT_PATH_PATTERN.search(line):
        return "direct_path_dependency"
    if POLICY_WORDS.search(line):
        return "policy_or_quarantine_note"
    return "possible_active_reference"


def scan() -> dict:
    findings = []
    for path in iter_candidate_files():
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except Exception as exc:
            findings.append(
                {
                    "path": str(path.relative_to(PROJECT_ROOT)),
                    "line": None,
                    "kind": "read_error",
                    "text": str(exc),
                }
            )
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            if PATTERN.search(line):
                findings.append(
                    {
                        "path": str(path.relative_to(PROJECT_ROOT)),
                        "line": line_no,
                        "kind": classify(path, line),
                        "text": line.strip()[:300],
                    }
                )
    counts: dict[str, int] = {}
    for item in findings:
        counts[item["kind"]] = counts.get(item["kind"], 0) + 1
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scan_roots": [str(path.relative_to(PROJECT_ROOT)) for path in SCAN_ROOTS if path.exists()],
        "root_file_globs": ROOT_FILE_GLOBS,
        "counts": counts,
        "findings": findings,
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = scan()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"legacy_runtime_reference_audit_{stamp}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out_path.relative_to(PROJECT_ROOT)}")
    print(json.dumps(report["counts"], indent=2))
    direct = report["counts"].get("direct_path_dependency", 0)
    active = report["counts"].get("possible_active_reference", 0)
    if direct or active:
        print(f"Review needed: direct_path_dependency={direct}, possible_active_reference={active}")
        return 1
    print("No active-looking legacy dependencies found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
