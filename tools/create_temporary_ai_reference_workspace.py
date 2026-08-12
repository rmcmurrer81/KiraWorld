"""Create a read-only-style Kira reference snapshot for a TemporaryAI.

The snapshot copies text/code/doc files into the candidate workbench so the
candidate can study and edit copies without touching the real Kira system.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMP_AI_ROOT = PROJECT_ROOT / "TemporaryAI" / "candidates"

TEXT_EXTENSIONS = {
    ".bat",
    ".cmd",
    ".css",
    ".csv",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}

SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
}

DEFAULT_ROOTS = [
    "HANDOFF_FOR_NEXT_CODEX_SESSION.md",
    "DESKTOP_UPGRADE_HANDOFF.md",
    "System/Docs",
    "tools",
    "Core",
    "Config",
    "Data/development_queue",
]


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def is_text_candidate(path: Path, max_bytes: int) -> bool:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return False
    try:
        return path.stat().st_size <= max_bytes
    except OSError:
        return False


def iter_files(root: Path, max_bytes: int):
    if root.is_file():
        if is_text_candidate(root, max_bytes):
            yield root
        return
    if not root.exists():
        return
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and is_text_candidate(path, max_bytes):
            yield path


def create_snapshot(candidate_id: str, roots: list[str], max_files: int, max_bytes: int) -> dict:
    candidate_dir = TEMP_AI_ROOT / candidate_id
    if not candidate_dir.exists():
        raise SystemExit(f"Candidate not found: {candidate_id}")

    snapshot_id = f"kira_reference_snapshot_{now_stamp()}"
    snapshot_root = candidate_dir / "workbench" / "inputs" / "kira_system_reference" / snapshot_id
    files_root = snapshot_root / "files"
    files_root.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "snapshot_id": snapshot_id,
        "created_at": now_iso(),
        "candidate_id": candidate_id,
        "policy": {
            "purpose": "TemporaryAI studies and edits copies only.",
            "original_files_modified": False,
            "candidate_may_edit": "files under this snapshot and its own workbench outputs",
            "candidate_must_not_edit": "original Kira project files",
            "human_review_required_before_applying": True,
        },
        "limits": {
            "max_files": max_files,
            "max_bytes_per_file": max_bytes,
            "extensions": sorted(TEXT_EXTENSIONS),
        },
        "requested_roots": roots,
        "copied_files": [],
        "skipped_roots": [],
    }

    copied = 0
    for raw_root in roots:
        root = PROJECT_ROOT / raw_root
        if not root.exists():
            manifest["skipped_roots"].append({"root": raw_root, "reason": "not_found"})
            continue
        for source in iter_files(root, max_bytes):
            if copied >= max_files:
                break
            dest = files_root / rel(source)
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(source, dest)
            except OSError as exc:
                manifest.setdefault("skipped_files", []).append(
                    {
                        "source": rel(source),
                        "reason": f"copy_failed: {exc}",
                    }
                )
                continue
            manifest["copied_files"].append(
                {
                    "source": rel(source),
                    "copy": rel(dest),
                    "bytes": source.stat().st_size,
                }
            )
            copied += 1
        if copied >= max_files:
            break

    manifest_path = snapshot_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    readme = snapshot_root / "README.md"
    readme.write_text(
        "\n".join(
            [
                f"# {snapshot_id}",
                "",
                "This is a copied Kira reference snapshot for TemporaryAI review.",
                "",
                "- Original Kira files were not modified.",
                "- Edit copies or create proposal files in the candidate workbench only.",
                "- Human/Codex review is required before anything is applied to the real project.",
                "",
                f"Copied files: {len(manifest['copied_files'])}",
                "",
                "Recommended output folders:",
                "",
                "- `workbench/outputs/review_notes`",
                "- `workbench/outputs/program_drafts`",
                "- `workbench/outputs/patch_proposals`",
                "- `workbench/outputs/copied_file_edits`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "snapshot_id": snapshot_id,
        "snapshot_root": rel(snapshot_root),
        "manifest": rel(manifest_path),
        "copied_files": len(manifest["copied_files"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", default="emily_carter_ai_and_computer_programming_expert_20260605_220651")
    parser.add_argument("--root", action="append", default=[], help="Project-relative file or folder to copy. Repeatable.")
    parser.add_argument("--max-files", type=int, default=500)
    parser.add_argument("--max-bytes", type=int, default=750_000)
    args = parser.parse_args()
    roots = args.root or DEFAULT_ROOTS
    result = create_snapshot(args.candidate_id, roots, args.max_files, args.max_bytes)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
