"""
Kira Source Evidence Extractor - v1

Purpose:
- Read the source index created by Kira/Core/source_indexer.py.
- Extract starter evidence from scripts, transcripts, stories, and fanfic.
- Save evidence files per character.
- Keep raw sources separate from processed evidence.

Important:
- This is a starter extractor, not a final AI reader.
- It uses simple rule-based extraction so it can run pre-GPU.
- Augment Code can later improve it with stronger NLP/model-assisted extraction.
- Extracted evidence is NOT personal memory for Kira or Lisa.
- Fanfic evidence is variant evidence and must not overwrite canon.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_INDEX_PATH = "Kira/Data/indexes/character_source_index.json"
DEFAULT_OUTPUT_ROOT = "Kira/Data/processed/source_evidence"


LOCATION_KEYWORDS = [
    "Paris",
    "Eiffel Tower",
    "Louvre",
    "Louvre Museum",
    "Seine",
    "Notre-Dame",
    "school",
    "bakery",
    "rooftop",
    "rooftops",
    "museum",
    "park",
    "street",
    "train",
    "metro",
    "home",
    "bedroom",
    "classroom",
]

ACTION_KEYWORDS = [
    "runs",
    "ran",
    "jumps",
    "jumped",
    "fights",
    "fought",
    "looks",
    "looked",
    "smiles",
    "smiled",
    "cries",
    "cried",
    "laughs",
    "laughed",
    "transforms",
    "transformed",
    "throws",
    "threw",
    "saves",
    "saved",
    "protects",
    "protected",
    "hides",
    "hid",
    "whispers",
    "whispered",
    "shouts",
    "shouted",
]

TRAIT_KEYWORDS = {
    "brave": ["brave", "courage", "courageous", "fearless"],
    "protective": ["protect", "protects", "protected", "saving", "saves", "saved"],
    "curious": ["curious", "wonder", "wondered", "question", "questions"],
    "angry": ["angry", "furious", "mad", "rage"],
    "nervous": ["nervous", "anxious", "worried", "scared"],
    "clever": ["clever", "smart", "plan", "strategy", "figures out"],
    "kind": ["kind", "gentle", "comfort", "helped", "helps"],
}

RELATIONSHIP_KEYWORDS = [
    "friend",
    "friends",
    "partner",
    "partners",
    "trust",
    "trusted",
    "love",
    "loves",
    "liked",
    "likes",
    "protect",
    "protects",
    "help",
    "helps",
    "saved",
    "betray",
    "betrayed",
    "secret",
]


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required JSON file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def resolve_path(project_root: Path, path_string: str) -> Path:
    path = Path(path_string)
    if path.is_absolute():
        return path
    return project_root / path


def extract_text_from_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF extraction requires pypdf. Install with: pip install pypdf") from exc

    reader = PdfReader(str(path))
    pages: List[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    return ""


def normalize_lines(text: str) -> List[str]:
    lines = []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if line:
            lines.append(line)
    return lines


def contains_any(text: str, words: Iterable[str]) -> bool:
    lower = text.lower()
    return any(word.lower() in lower for word in words)


def nearby_window(lines: List[str], index: int, radius: int = 1) -> str:
    start = max(0, index - radius)
    end = min(len(lines), index + radius + 1)
    return " / ".join(lines[start:end])


def make_evidence_id(character_id: str, source_stem: str, evidence_type: str, number: int) -> str:
    safe_source = re.sub(r"[^a-zA-Z0-9]+", "_", source_stem).strip("_").lower()[:40]
    return f"ev_{character_id}_{safe_source}_{evidence_type}_{number:04d}"


def detect_dialogue_for_alias(lines: List[str], aliases: List[str]) -> List[Dict[str, Any]]:
    """
    Starter script-style dialogue detection.

    Handles common formats:
    - LADYBUG: line
    - Ladybug: line
    - Marinette: line

    This is intentionally conservative. Later versions can handle more formats.
    """
    evidence: List[Dict[str, Any]] = []
    alias_patterns = [re.escape(alias) for alias in aliases]
    if not alias_patterns:
        return evidence

    pattern = re.compile(rf"^({'|'.join(alias_patterns)})\s*[:\-]\s*(.+)$", re.IGNORECASE)

    for i, line in enumerate(lines):
        match = pattern.match(line)
        if not match:
            continue

        speaker = match.group(1)
        dialogue = match.group(2).strip()

        if len(dialogue) < 2:
            continue

        evidence.append({
            "line_number": i + 1,
            "speaker_alias": speaker,
            "raw_excerpt": dialogue[:500],
            "context": nearby_window(lines, i, radius=1),
        })

    return evidence


def detect_mentions_with_context(lines: List[str], aliases: List[str], keywords: List[str], evidence_type: str) -> List[Dict[str, Any]]:
    """
    Find lines where a character alias and one of the evidence keywords appear nearby.
    """
    found: List[Dict[str, Any]] = []

    for i, line in enumerate(lines):
        if not contains_any(line, aliases):
            continue
        if not contains_any(line, keywords):
            continue

        found.append({
            "line_number": i + 1,
            "raw_excerpt": line[:500],
            "context": nearby_window(lines, i, radius=1),
            "matched_keywords": [word for word in keywords if word.lower() in line.lower()],
            "evidence_type": evidence_type,
        })

    return found


def detect_locations(lines: List[str]) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []

    for i, line in enumerate(lines):
        matches = [loc for loc in LOCATION_KEYWORDS if loc.lower() in line.lower()]
        if matches:
            found.append({
                "line_number": i + 1,
                "locations": sorted(set(matches)),
                "raw_excerpt": line[:500],
                "context": nearby_window(lines, i, radius=1),
            })

    return found


def detect_trait_clues(lines: List[str], aliases: List[str]) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []

    for i, line in enumerate(lines):
        if not contains_any(line, aliases):
            continue

        lower = line.lower()
        matched_traits: List[str] = []
        matched_words: List[str] = []

        for trait, keywords in TRAIT_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in lower:
                    matched_traits.append(trait)
                    matched_words.append(keyword)

        if matched_traits:
            found.append({
                "line_number": i + 1,
                "possible_traits": sorted(set(matched_traits)),
                "matched_words": sorted(set(matched_words)),
                "raw_excerpt": line[:500],
                "context": nearby_window(lines, i, radius=1),
            })

    return found


def build_evidence_item(
    character_id: str,
    source_info: Dict[str, Any],
    evidence_type: str,
    raw_excerpt: str,
    summary: str,
    number: int,
    confidence: float,
    related_characters: Optional[List[str]] = None,
    locations: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    requires_review: bool = True,
) -> Dict[str, Any]:
    source_path = source_info.get("source_path", "")
    source_stem = Path(source_path).stem or "source"

    return {
        "evidence_id": make_evidence_id(character_id, source_stem, evidence_type, number),
        "character_id": character_id,
        "source_path": source_path,
        "source_set": source_info.get("source_set"),
        "source_authority": source_info.get("source_authority", "unknown"),
        "content_format": source_info.get("content_format", "unknown"),
        "evidence_type": evidence_type,
        "raw_excerpt": raw_excerpt[:500],
        "summary": summary,
        "related_characters": related_characters or [],
        "locations": locations or [],
        "tags": tags or [],
        "confidence": confidence,
        "requires_review": requires_review,
        "accepted_into_profile": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "notes": "",
    }


def extract_for_character_source(
    project_root: Path,
    character_id: str,
    character_source: Dict[str, Any]
) -> List[Dict[str, Any]]:
    source_path = resolve_path(project_root, character_source["source_path"])
    text = extract_text(source_path)
    lines = normalize_lines(text)

    aliases = character_source.get("matched_aliases", [])
    if not aliases:
        return []

    source_authority = character_source.get("source_authority", "unknown")
    requires_review = source_authority != "canon"

    evidence: List[Dict[str, Any]] = []
    counter = 1

    # Dialogue evidence
    dialogue_hits = detect_dialogue_for_alias(lines, aliases)
    for hit in dialogue_hits[:50]:
        evidence.append(build_evidence_item(
            character_id=character_id,
            source_info=character_source,
            evidence_type="dialogue",
            raw_excerpt=hit["raw_excerpt"],
            summary=f"Possible dialogue spoken by {character_id} using alias {hit['speaker_alias']}.",
            number=counter,
            confidence=0.75 if source_authority == "canon" else 0.55,
            tags=["dialogue", "auto_extracted"],
            requires_review=requires_review,
        ))
        counter += 1

    # Action evidence
    action_hits = detect_mentions_with_context(lines, aliases, ACTION_KEYWORDS, "action")
    for hit in action_hits[:40]:
        evidence.append(build_evidence_item(
            character_id=character_id,
            source_info=character_source,
            evidence_type="action",
            raw_excerpt=hit["raw_excerpt"],
            summary=f"Possible action clue involving {character_id}.",
            number=counter,
            confidence=0.55 if source_authority == "canon" else 0.4,
            tags=["action", "auto_extracted"],
            requires_review=True,
        ))
        counter += 1

    # Relationship evidence
    relationship_hits = detect_mentions_with_context(lines, aliases, RELATIONSHIP_KEYWORDS, "relationship")
    for hit in relationship_hits[:40]:
        evidence.append(build_evidence_item(
            character_id=character_id,
            source_info=character_source,
            evidence_type="relationship",
            raw_excerpt=hit["raw_excerpt"],
            summary=f"Possible relationship clue involving {character_id}.",
            number=counter,
            confidence=0.5 if source_authority == "canon" else 0.35,
            tags=["relationship", "auto_extracted"],
            requires_review=True,
        ))
        counter += 1

    # Trait clues
    trait_hits = detect_trait_clues(lines, aliases)
    for hit in trait_hits[:40]:
        evidence.append(build_evidence_item(
            character_id=character_id,
            source_info=character_source,
            evidence_type="trait",
            raw_excerpt=hit["raw_excerpt"],
            summary=f"Possible trait clue for {character_id}: {', '.join(hit['possible_traits'])}.",
            number=counter,
            confidence=0.45 if source_authority == "canon" else 0.3,
            tags=["trait", "auto_extracted"] + [f"trait:{trait}" for trait in hit["possible_traits"]],
            requires_review=True,
        ))
        counter += 1

    # Location evidence is source-level, but save it for every detected character source so profiles can learn context.
    location_hits = detect_locations(lines)
    for hit in location_hits[:25]:
        evidence.append(build_evidence_item(
            character_id=character_id,
            source_info=character_source,
            evidence_type="location",
            raw_excerpt=hit["raw_excerpt"],
            summary=f"Location/context clue found near source material: {', '.join(hit['locations'])}.",
            number=counter,
            confidence=0.6 if source_authority == "canon" else 0.45,
            locations=hit["locations"],
            tags=["location", "auto_extracted"],
            requires_review=requires_review,
        ))
        counter += 1

    return evidence


def extract_all(project_root: Path, index_path: Path, output_root: Path) -> Dict[str, Any]:
    index = load_json(index_path)
    by_character = index.get("by_character", {})

    summary = {
        "generated_by": "source_evidence_extractor.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "characters_processed": 0,
        "evidence_items_created": 0,
        "errors": [],
        "output_root": str(output_root),
    }

    master_index: Dict[str, Any] = {
        "version": "1.0",
        "generated_at": summary["generated_at"],
        "characters": {},
    }

    for character_id, character_sources in by_character.items():
        all_evidence: List[Dict[str, Any]] = []

        for source in character_sources:
            try:
                all_evidence.extend(extract_for_character_source(project_root, character_id, source))
            except Exception as exc:
                summary["errors"].append({
                    "character_id": character_id,
                    "source_path": source.get("source_path"),
                    "error": str(exc),
                })

        character_output = output_root / character_id / "evidence.json"
        write_json(character_output, {
            "character_id": character_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "evidence_count": len(all_evidence),
            "evidence": all_evidence,
        })

        master_index["characters"][character_id] = {
            "evidence_count": len(all_evidence),
            "evidence_file": str(character_output),
        }

        summary["characters_processed"] += 1
        summary["evidence_items_created"] += len(all_evidence)

    write_json(output_root / "source_evidence_master_index.json", master_index)
    write_json(output_root / "source_evidence_extraction_log.json", summary)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract starter character evidence from Kira source indexes.")
    parser.add_argument("--project-root", default=".", help="Path to the parent folder that contains Kira.")
    parser.add_argument("--index", default=DEFAULT_INDEX_PATH, help="Path to character_source_index.json.")
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT, help="Output root for extracted evidence.")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    index_path = resolve_path(project_root, args.index)
    output_root = resolve_path(project_root, args.output_root)

    summary = extract_all(project_root, index_path, output_root)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
