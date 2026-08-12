"""Create AI workspaces from local folders.

An AI workspace is a reviewed local work area that Kira, Lisa, or a TemporaryAI
can read from during a session and write draft outputs into. It extracts text
where practical and saves a manifest instead of handing raw folders directly to
the model.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT / "Data" / "ai_workspaces"
CANDIDATE_ROOT = PROJECT_ROOT / "TemporaryAI" / "candidates"

TEXT_EXTS = {".txt", ".md", ".json", ".csv", ".log", ".py", ".bat", ".ps1", ".html", ".htm"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
PDF_EXTS = {".pdf"}
ZIP_EXTS = {".zip"}
SKIP_DIRS = {"__pycache__", ".git", ".idea", "node_modules", ".venv", "venv"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:80] or "workspace"


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_text_file(path: Path, limit: int) -> tuple[str, str]:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        return text[:limit], "extracted"
    except Exception as exc:
        return "", f"text_error: {exc}"


def extract_pdf(path: Path, limit: int) -> tuple[str, str]:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        return "", f"pdf_reader_missing: {exc}"
    try:
        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages[:80]:
            parts.append(page.extract_text() or "")
            if sum(len(part) for part in parts) >= limit:
                break
        text = "\n\n".join(part.strip() for part in parts if part.strip())
        if not text.strip():
            return "", "pdf_no_selectable_text_needs_ocr"
        return text[:limit], "extracted"
    except Exception as exc:
        return "", f"pdf_error: {exc}"


def extract_image_ocr(path: Path, limit: int) -> tuple[str, str]:
    try:
        from PIL import Image
        import pytesseract
    except Exception as exc:
        return "", f"ocr_missing: {exc}"
    try:
        text = pytesseract.image_to_string(Image.open(path))
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return "", "ocr_empty"
        return text[:limit], "ocr_extracted"
    except Exception as exc:
        return "", f"ocr_error: {exc}"


def inventory_zip(path: Path, limit: int) -> tuple[str, str, list[dict[str, Any]]]:
    entries: list[dict[str, Any]] = []
    lines = [f"ZIP archive inventory for {path.name}"]
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist()[:300]:
                entries.append({
                    "filename": info.filename,
                    "file_size": info.file_size,
                    "compress_size": info.compress_size,
                })
                lines.append(f"- {info.filename} ({info.file_size} bytes)")
                suffix = Path(info.filename).suffix.lower()
                if suffix in {".txt", ".md", ".json", ".csv"} and info.file_size <= 500_000:
                    try:
                        data = archive.read(info.filename)[:200_000].decode("utf-8", errors="replace")
                        data = re.sub(r"\s+", " ", data).strip()
                        if data:
                            lines.append(f"  excerpt: {data[:600]}")
                    except Exception:
                        pass
                if len("\n".join(lines)) > limit:
                    break
        return "\n".join(lines)[:limit], "zip_inventory", entries
    except Exception as exc:
        return "", f"zip_error: {exc}", entries


def iter_files(source_folder: Path, max_files: int) -> list[Path]:
    files: list[Path] = []
    for path in source_folder.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        files.append(path)
        if len(files) >= max_files:
            break
    return files


def extract_file(path: Path, extracted_dir: Path, source_folder: Path, per_file_limit: int) -> dict[str, Any]:
    suffix = path.suffix.lower()
    text = ""
    status = "unsupported"
    zip_entries: list[dict[str, Any]] = []
    if suffix in TEXT_EXTS:
        text, status = read_text_file(path, per_file_limit)
    elif suffix in PDF_EXTS:
        text, status = extract_pdf(path, per_file_limit)
    elif suffix in IMAGE_EXTS:
        text, status = extract_image_ocr(path, per_file_limit)
    elif suffix in ZIP_EXTS:
        text, status, zip_entries = inventory_zip(path, per_file_limit)

    relative_source = path.relative_to(source_folder).as_posix()
    extracted_path = ""
    if text:
        out_name = slug(relative_source) + ".txt"
        out_path = extracted_dir / out_name
        write_text(out_path, text)
        extracted_path = rel(out_path)
    return {
        "source_path": path.as_posix(),
        "relative_source_path": relative_source,
        "extension": suffix,
        "size_bytes": path.stat().st_size,
        "status": status,
        "extracted_text_path": extracted_path,
        "excerpt": text[:900],
        "zip_entries": zip_entries[:80],
    }


def attach_workspace_to_candidate(candidate_id: str, workspace_manifest: Path) -> None:
    candidate_dir = CANDIDATE_ROOT / candidate_id
    profile_path = candidate_dir / "temporary_ai_profile.json"
    request_path = candidate_dir / "creation_request.json"
    if not profile_path.exists():
        raise FileNotFoundError(f"Candidate profile not found: {profile_path}")
    for path in [profile_path, request_path]:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        workspaces = data.setdefault("attached_workspaces", [])
        manifest_rel = rel(workspace_manifest)
        if manifest_rel not in workspaces:
            workspaces.append(manifest_rel)
        data["updated_at"] = now_iso()
        write_json(path, data)


def create_workspace(args: argparse.Namespace) -> dict[str, Any]:
    source_folder = Path(args.source_folder).expanduser().resolve()
    if not source_folder.exists() or not source_folder.is_dir():
        raise FileNotFoundError(f"Source folder not found: {source_folder}")
    owner = slug(args.owner)
    workspace_id = f"{owner}_{slug(args.workspace_name or source_folder.name)}_{stamp()}"
    workspace_dir = WORKSPACE_ROOT / owner / workspace_id
    extracted_dir = workspace_dir / "extracted_text"
    outputs_dir = workspace_dir / "outputs"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    files = []
    for path in iter_files(source_folder, args.max_files):
        if path.stat().st_size > args.max_file_mb * 1024 * 1024:
            files.append({
                "source_path": path.as_posix(),
                "relative_source_path": path.relative_to(source_folder).as_posix(),
                "extension": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
                "status": "skipped_too_large",
                "extracted_text_path": "",
                "excerpt": "",
                "zip_entries": [],
            })
            continue
        files.append(extract_file(path, extracted_dir, source_folder, args.per_file_chars))

    extracted_count = sum(1 for item in files if item.get("extracted_text_path"))
    manifest = {
        "workspace_id": workspace_id,
        "created_at": now_iso(),
        "owner": owner,
        "candidate_id": args.candidate_id,
        "workspace_name": args.workspace_name or source_folder.name,
        "source_folder": source_folder.as_posix(),
        "workspace_folder": rel(workspace_dir),
        "outputs_folder": rel(outputs_dir),
        "status": "ready",
        "permissions": {
            "read_extracted_text": True,
            "write_drafts_to_outputs": True,
            "raw_source_folder_is_reference_only": True,
            "do_not_modify_original_files": True,
        },
        "safety_notes": [
            "Workspace excerpts are source evidence, not memory.",
            "AI outputs are drafts for Robert review.",
            "Legal, medical, financial, admissions, and other high-stakes drafts require qualified human review.",
        ],
        "file_count": len(files),
        "extracted_count": extracted_count,
        "files": files,
    }
    manifest_path = workspace_dir / "workspace_manifest.json"
    write_json(manifest_path, manifest)
    write_text(workspace_dir / "README.md", f"""# AI Workspace: {manifest['workspace_name']}

Workspace ID: `{workspace_id}`

Original folder:

```text
{source_folder}
```

Outputs should be saved under:

```text
{rel(outputs_dir)}
```

This workspace is source evidence for AI assistance. Original files should not
be modified by AI tools.
""")
    if args.candidate_id:
        attach_workspace_to_candidate(args.candidate_id, manifest_path)
    return {
        "workspace_id": workspace_id,
        "manifest": rel(manifest_path),
        "workspace_folder": rel(workspace_dir),
        "outputs_folder": rel(outputs_dir),
        "file_count": len(files),
        "extracted_count": extracted_count,
        "attached_candidate": args.candidate_id,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an AI workspace from a local folder.")
    parser.add_argument("source_folder", help="Folder of documents/images/archives to make available as reviewed source evidence.")
    parser.add_argument("--workspace-name", default="")
    parser.add_argument("--owner", default="temporary_ai")
    parser.add_argument("--candidate-id", default="", help="Optional TemporaryAI candidate id to attach this workspace to.")
    parser.add_argument("--max-files", type=int, default=120)
    parser.add_argument("--max-file-mb", type=int, default=25)
    parser.add_argument("--per-file-chars", type=int, default=12000)
    args = parser.parse_args()
    print(json.dumps(create_workspace(args), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
