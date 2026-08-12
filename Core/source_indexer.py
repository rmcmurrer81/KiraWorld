"""
Kira TemporaryAI Source Indexer - v2

Purpose:
- Scan Kira/Data/library as the central raw source library.
- Detect which configured characters appear in each script/story/document.
- Deduplicate files by SHA-256 hash.
- Separate canon evidence from fanfic/variant evidence.
- Write character_source_index.json for later TemporaryAI creation.

Important design rules:
- External scripts, novels, fanfics, and documents are knowledge sources, NOT Kira/Lisa personal memories.
- Reading a file does not automatically create a memory.
- Fanfic is optional variant evidence and never overwrites canon.
- Raw source files should remain read-only.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set


SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md"}
SUPPORTED_PDF_EXTENSIONS = {".pdf"}


@dataclass
class DetectedCharacter:
    character_id: str
    display_name: str
    matched_aliases: List[str]
    mention_count: int
    confidence: float


@dataclass
class IndexedSource:
    source_set: str
    source_path: str
    file_name: str
    file_type: str
    sha256: str
    source_authority: str
    content_format: str
    detected_characters: List[DetectedCharacter]
    tags: List[str]


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def iter_source_files(folder: Path, patterns: List[str], recursive: bool) -> Iterable[Path]:
    if not folder.exists():
        return []

    candidates = folder.rglob("*") if recursive else folder.glob("*")
    files: List[Path] = []

    for path in candidates:
        if not path.is_file():
            continue
        if any(fnmatch.fnmatch(path.name, pattern) for pattern in patterns):
            files.append(path)

    return files


def extract_text_from_pdf(path: Path) -> str:
    """
    Basic PDF text extraction.

    Dependency:
      pip install pypdf

    Augment Code may later replace this with a stronger parser if needed.
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF support requires pypdf. Install with: pip install pypdf"
        ) from exc

    reader = PdfReader(str(path))
    chunks: List[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in SUPPORTED_TEXT_EXTENSIONS:
        return path.read_text(encoding="utf-8", errors="ignore")

    if suffix in SUPPORTED_PDF_EXTENSIONS:
        return extract_text_from_pdf(path)

    return ""


def count_alias_mentions(text: str, aliases: List[str]) -> Dict[str, int]:
    """
    Counts case-insensitive whole-word-ish alias mentions.
    Handles multi-word aliases like 'Marinette Dupain-Cheng'.
    """
    counts: Dict[str, int] = {}

    for alias in aliases:
        escaped = re.escape(alias)
        pattern = rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])"
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if matches:
            counts[alias] = len(matches)

    return counts


def confidence_from_mentions(total_mentions: int, matched_aliases: int) -> float:
    """
    Starter heuristic:
    - 1 mention = low confidence
    - 2-4 mentions = medium confidence
    - 5+ mentions = high confidence
    - multiple aliases increase confidence slightly
    """
    if total_mentions <= 0:
        return 0.0

    base = min(0.95, 0.35 + (total_mentions * 0.10))
    alias_bonus = min(0.10, max(0, matched_aliases - 1) * 0.05)
    return round(min(0.99, base + alias_bonus), 2)


def characters_allowed_for_source_set(
    character_config: Dict[str, Any],
    source_set_name: str
) -> Dict[str, Any]:
    """
    Only scan characters assigned to the active source set.
    This prevents unrelated character lists from being tested against every source folder.
    """
    allowed: Dict[str, Any] = {}

    for character_id, character in character_config.items():
        source_sets = set(character.get("source_sets", []))
        if source_set_name in source_sets:
            allowed[character_id] = character

    return allowed


def detect_characters(text: str, character_config: Dict[str, Any]) -> List[DetectedCharacter]:
    detected: List[DetectedCharacter] = []

    for character_id, character in character_config.items():
        aliases = character.get("aliases", [])
        alias_counts = count_alias_mentions(text, aliases)
        total_mentions = sum(alias_counts.values())

        if total_mentions <= 0:
            continue

        matched_aliases = list(alias_counts.keys())
        detected.append(
            DetectedCharacter(
                character_id=character_id,
                display_name=character.get("display_name", character_id),
                matched_aliases=matched_aliases,
                mention_count=total_mentions,
                confidence=confidence_from_mentions(total_mentions, len(matched_aliases)),
            )
        )

    detected.sort(key=lambda item: item.mention_count, reverse=True)
    return detected


def resolve_project_path(project_root: Path, path_string: str) -> Path:
    path = Path(path_string)
    if path.is_absolute():
        return path
    return project_root / path


def scan_sources(project_root: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    source_sets = config.get("source_sets", {})
    characters = config.get("characters", {})

    seen_hashes: Dict[str, str] = {}
    indexed_sources: List[IndexedSource] = []
    skipped_duplicates: List[Dict[str, str]] = []
    missing_folders: List[Dict[str, str]] = []
    errors: List[Dict[str, str]] = []

    for source_set_name, source_set in source_sets.items():
        folders = source_set.get("source_folders", [])
        patterns = source_set.get("file_patterns", ["*.pdf", "*.txt", "*.md"])
        recursive = bool(source_set.get("recursive", True))
        tags = list(source_set.get("tags", [])) + [f"source_set:{source_set_name}"]
        source_authority = source_set.get("source_authority", "unknown")
        content_format = source_set.get("content_format", "unknown")

        active_characters = characters_allowed_for_source_set(characters, source_set_name)

        locked_sources = source_set.get("locked_sources", [])
        use_locked_sources = bool(locked_sources)

        files: List[Path] = []

        if use_locked_sources:
            files = [resolve_project_path(project_root, p) for p in locked_sources]
        else:
            for folder_str in folders:
                folder = resolve_project_path(project_root, folder_str)
                if not folder.exists():
                    missing_folders.append({
                        "source_set": source_set_name,
                        "folder": str(folder),
                        "note": "Folder does not exist yet. This is okay for future/empty categories, but check spelling if sources should be present."
                    })
                    continue
                files.extend(iter_source_files(folder, patterns, recursive))

        for path in sorted(set(files)):
            try:
                if not path.exists() or not path.is_file():
                    errors.append({"path": str(path), "error": "File missing or not a file"})
                    continue

                file_hash = sha256_file(path)
                if file_hash in seen_hashes:
                    skipped_duplicates.append({
                        "duplicate_path": str(path),
                        "original_path": seen_hashes[file_hash],
                        "sha256": file_hash,
                        "note": "Duplicate raw source detected by hash. Keep only one true source copy if possible."
                    })
                    continue

                seen_hashes[file_hash] = str(path)

                text = extract_text(path)
                detected = detect_characters(text, active_characters)

                indexed_sources.append(
                    IndexedSource(
                        source_set=source_set_name,
                        source_path=str(path),
                        file_name=path.name,
                        file_type=path.suffix.lower().lstrip("."),
                        sha256=file_hash,
                        source_authority=source_authority,
                        content_format=content_format,
                        detected_characters=detected,
                        tags=tags,
                    )
                )

            except Exception as exc:
                errors.append({"path": str(path), "error": str(exc)})

    by_character: Dict[str, List[Dict[str, Any]]] = {}

    for source in indexed_sources:
        for detected in source.detected_characters:
            by_character.setdefault(detected.character_id, []).append({
                "source_set": source.source_set,
                "source_path": source.source_path,
                "file_name": source.file_name,
                "sha256": source.sha256,
                "source_authority": source.source_authority,
                "content_format": source.content_format,
                "matched_aliases": detected.matched_aliases,
                "mention_count": detected.mention_count,
                "confidence": detected.confidence,
                "tags": source.tags,
            })

    for character_sources in by_character.values():
        character_sources.sort(
            key=lambda item: (
                item["source_authority"] != "canon",
                -item["confidence"],
                item["file_name"]
            )
        )

    return {
        "version": config.get("version", "1.1"),
        "generated_by": "source_indexer.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rules": config.get("rules", {}),
        "summary": {
            "source_files_indexed": len(indexed_sources),
            "characters_with_sources": len(by_character),
            "duplicates_skipped": len(skipped_duplicates),
            "missing_folders": len(missing_folders),
            "errors": len(errors),
        },
        "sources": [
            {
                **asdict(source),
                "detected_characters": [asdict(character) for character in source.detected_characters],
            }
            for source in indexed_sources
        ],
        "by_character": by_character,
        "skipped_duplicates": skipped_duplicates,
        "missing_folders": missing_folders,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan Kira source folders and build character source index.")
    parser.add_argument("--project-root", default=".", help="Path to the parent folder that contains Kira.")
    parser.add_argument(
        "--config",
        default="Kira/TemporaryAI/config/sources.json",
        help="Path to sources.json, relative to project root unless absolute.",
    )
    parser.add_argument("--output", default=None, help="Optional output path for character_source_index.json.")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    config_path = resolve_project_path(project_root, args.config)
    config = load_json(config_path)

    result = scan_sources(project_root, config)

    output_from_config = config.get("index_output", {}).get("character_source_index")
    output_path = Path(args.output) if args.output else Path(output_from_config or "Kira/Data/indexes/character_source_index.json")

    if not output_path.is_absolute():
        output_path = project_root / output_path

    write_json(output_path, result)

    scan_log_path = config.get("index_output", {}).get("scan_log")
    if scan_log_path:
        log_path = resolve_project_path(project_root, scan_log_path)
        write_json(log_path, {
            "generated_at": result["generated_at"],
            "summary": result["summary"],
            "missing_folders": result["missing_folders"],
            "skipped_duplicates": result["skipped_duplicates"],
            "errors": result["errors"],
        })

    print(f"Wrote source index: {output_path}")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
