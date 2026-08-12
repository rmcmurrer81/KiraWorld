"""
Create a pre-GPU slow-reading chunk and reaction draft.

This is the bridge between "a book exists" and "Kira/Lisa experienced a
small part of it." It extracts only a small unit, advances the slow-reading
session, and writes a reaction draft that can later update taste profiles.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from slow_reading import advance_session
from reading_ledger import append_reading_event
from validate_reading_reaction import validate_reading_reaction
from validate_slow_reading_session import validate_slow_reading_session
from library_source_health import is_text_reading_blocked, mark_unreadable, repaired_output_path, request_ocr


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHUNK_DIR = PROJECT_ROOT / "Data" / "reading" / "chunks"
DEFAULT_REACTION_DIR = PROJECT_ROOT / "Data" / "reading" / "reactions"
MAX_EXCERPT_CHARS = 6000


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:100] or "chunk"


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _project_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _extract_pdf_pages(source_path: Path, start_page: int, page_count: int) -> tuple[str, dict[str, Any]]:
    if is_text_reading_blocked(source_path):
        raise RuntimeError(
            f"Known unreadable/scanned source: {source_path.name}. It needs OCR or a replacement text version before text reading."
        )
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF reading requires pypdf. Install with: py -m pip install pypdf") from exc

    reader = PdfReader(str(source_path))
    total_pages = len(reader.pages)
    if total_pages <= 0:
        raise RuntimeError(f"No pages found in {source_path}")
    start = max(1, start_page)
    end = min(total_pages, start + max(1, page_count) - 1)
    if start > total_pages:
        raise RuntimeError(f"Start page {start} is past the end of {source_path.name} ({total_pages} pages).")

    selected: list[tuple[int, str]] = []
    skipped_blank_pages: list[int] = []
    page = start
    target_nonblank_pages = max(1, page_count)
    while page <= total_pages and len(selected) < target_nonblank_pages:
        text = reader.pages[page - 1].extract_text() or ""
        if text.strip():
            selected.append((page, text))
        else:
            skipped_blank_pages.append(page)
        page += 1

    if selected:
        start = selected[0][0]
        end = selected[-1][0]
    text = "\n\n".join(page_text for _, page_text in selected)
    if not text.strip():
        mark_unreadable(
            source_path,
            reason=f"No extractable text found on or after page {start}; likely scanned/image-only PDF.",
        )
        raise RuntimeError(
            f"No extractable text found on or after page {start}. This may be a scanned/image-only PDF."
        )
    position = {
        "unit_type": "page",
        "unit_label": f"pages_{start:03d}_{end:03d}",
        "start_page": start,
        "end_page": end,
    }
    if skipped_blank_pages:
        position["skipped_blank_pages"] = skipped_blank_pages
    return text, position


def _extract_text_lines(source_path: Path, start_line: int, line_count: int) -> tuple[str, dict[str, Any]]:
    lines = source_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if not lines:
        raise RuntimeError(f"No text lines found in {source_path}")
    start = max(1, start_line)
    end = min(len(lines), start + max(1, line_count) - 1)
    if start > len(lines):
        raise RuntimeError(f"Start line {start} is past the end of {source_path.name} ({len(lines)} lines).")
    text = "\n".join(lines[start - 1 : end])
    return text, {"unit_type": "section", "unit_label": f"lines_{start:04d}_{end:04d}", "start_line": start, "end_line": end}


def infer_next_position(session: dict[str, Any], source_path: Path, pages: int, lines: int) -> tuple[int, int]:
    completed = session.get("progress", {}).get("completed_units", [])
    if not isinstance(completed, list) or not completed:
        return 1, 1
    last = str(completed[-1])
    page_match = re.search(r"pages_(\d{3})_(\d{3})", last)
    if page_match and source_path.suffix.lower() == ".pdf":
        return int(page_match.group(2)) + 1, 1
    line_match = re.search(r"lines_(\d{4})_(\d{4})", last)
    if line_match and source_path.suffix.lower() in {".txt", ".md"}:
        return 1, int(line_match.group(2)) + 1
    return 1, 1


def extract_chunk_text(source_path: Path, session: dict[str, Any], *, start_page: int | None, pages: int, start_line: int | None, lines: int) -> tuple[str, dict[str, Any]]:
    inferred_page, inferred_line = infer_next_position(session, source_path, pages, lines)
    if is_text_reading_blocked(source_path):
        repaired = repaired_output_path(source_path)
        if repaired and repaired.suffix.lower() in {".txt", ".md"}:
            text, position = _extract_text_lines(repaired, start_line or inferred_line, lines)
            position["unit_label"] = f"ocr_{position['unit_label']}"
            position["ocr_derivative_of"] = _relative(source_path)
            position["ocr_derivative_path"] = _relative(repaired)
            position["reader_note"] = "Reading an OCR text derivative because the original PDF has no usable text layer."
            return text, position
        request_ocr(
            source_path,
            requester=str(session.get("reader", "unknown")),
            reason="Reader encountered a known unreadable/scanned source with no repaired OCR derivative available.",
            run_id=str(session.get("session_id", "")),
        )
        raise RuntimeError(
            f"Known unreadable/scanned source: {source_path.name}. OCR has been requested; it needs OCR or a replacement text version before text reading."
        )
    suffix = source_path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_pages(source_path, start_page or inferred_page, pages)
    if suffix in {".txt", ".md"}:
        return _extract_text_lines(source_path, start_line or inferred_line, lines)
    raise RuntimeError(f"Unsupported readable file type for chunk extraction: {source_path.suffix}")


def build_chunk_record(session: dict[str, Any], source_path: Path, text: str, position: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    material = session.get("material", {})
    excerpt = text.strip()[:MAX_EXCERPT_CHARS]
    return {
        "chunk_id": f"reading_chunk_{session['reader']}_{_slug(str(material.get('title', source_path.stem)))}_{position['unit_label']}",
        "created_at": now,
        "reader": session["reader"],
        "session_id": session["session_id"],
        "source": {
            "title": material.get("title", source_path.stem),
            "source_path": material.get("source_path", _relative(source_path)),
            "source_authority": material.get("source_authority", "raw_library_source"),
            "source_material_remains_source": True,
        },
        "position": position,
        "excerpt_char_count": len(excerpt),
        "excerpt_truncated": len(text.strip()) > len(excerpt),
        "excerpt": excerpt,
        "policy": {
            "small_chunk_only": True,
            "does_not_create_lived_memory": True,
            "reaction_required_for_preference_change": True,
            "full_book_not_ingested": True,
        },
        "status": "draft",
    }


def build_reaction_draft(
    session: dict[str, Any],
    chunk: dict[str, Any],
    *,
    reaction_summary: str,
    stance: str,
    affinity: float,
    interest_delta: float,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    source = chunk["source"]
    position = chunk["position"]
    voice_summary = natural_reaction_summary(session["reader"], chunk, reaction_summary)
    return {
        "reaction_id": f"reading_reaction_{session['reader']}_{_slug(str(source['title']))}_{position['unit_label']}",
        "created_at": now,
        "reader": session["reader"],
        "source": source,
        "reading_position": {
            "unit_type": position["unit_type"],
            "unit_label": position["unit_label"],
            "approximate_progress_percent": 0,
        },
        "reaction": {
            "favorite_moments": [],
            "emotions": [],
            "questions": [],
            "discomfort_or_fears": [],
            "curiosity_triggers": [],
            "wants_to_discuss_with": [],
            "wants_to_keep_private": True,
            "shareable_summary": voice_summary,
        },
        "preference_signal": {
            "stance": stance,
            "current_affinity": affinity,
            "interest_delta": interest_delta,
            "reasons": natural_reaction_reasons(chunk),
            "may_change_later": True,
            "older_reactions_can_be_reinterpreted": True,
        },
        "imagination": {
            "imagination_allowed": True,
            "slowly_develops_over_time": True,
            "pictured_places": [],
            "pictured_people": [],
            "pictured_objects": [],
            "atmosphere": [],
            "sensory_details": {
                "sight": [],
                "sound": [],
                "texture": [],
                "smell": [],
                "emotion_tone": [],
            },
            "certainty": "imagined_not_confirmed",
            "may_influence_dreams_or_creative_projects": True,
            "may_become_notebook_world_seed_if_chosen": True,
        },
        "dream_and_fantasy_influence": {
            "stories_may_influence_dreams": True,
            "stories_may_influence_fantasies": True,
            "stories_may_influence_hopes": True,
            "stories_may_influence_fears": True,
            "influence_is_indirect": True,
            "dreams_remain_not_real_events": True,
            "fantasies_remain_private_inner_life_unless_shared": True,
            "fantasies_do_not_prove_consent_or_relationship_status": True,
            "reader_controls_whether_to_share": True,
        },
        "memory_policy": {
            "may_remember_story_moment": True,
            "may_remember_own_reaction": True,
            "does_not_become_lived_memory": True,
            "does_not_create_temporary_ai_automatically": True,
            "does_not_create_notebook_world_automatically": True,
            "source_and_imagination_must_be_labeled": True,
        },
        "privacy": {
            "default_visibility": session.get("privacy", {}).get("default_visibility", "reader_private"),
            "robert_can_see_without_permission": False,
            "other_ai_can_see_without_permission": False,
            "shareable_summary_allowed_if_reader_chooses": True,
        },
        "linked_chunk_id": chunk["chunk_id"],
        "status": "draft",
    }


def natural_reaction_summary(reader: str, chunk: dict[str, Any], fallback: str) -> str:
    excerpt = str(chunk.get("excerpt", "")).strip()
    title = str(chunk.get("source", {}).get("title", "this")).replace("_", " ")
    first_line = next((line.strip() for line in excerpt.splitlines() if line.strip()), "")
    if not first_line:
        return fallback
    if reader == "lisa":
        return f"Lisa read a small piece of {title}; the first thing that stood out was how plainly it opens: {first_line[:120]}"
    return f"Kira read a small piece of {title}; she is not claiming a favorite yet, but the opening hook in her head is: {first_line[:120]}"


def natural_reaction_reasons(chunk: dict[str, Any]) -> list[str]:
    excerpt = str(chunk.get("excerpt", ""))
    reasons: list[str] = []
    if "?" in excerpt:
        reasons.append("the chunk raises a question instead of giving everything away")
    if len(excerpt.strip()) > 500:
        reasons.append("there is enough texture here to form a first impression without pretending to know the whole source")
    if not reasons:
        reasons.append("this is only an opening impression, not a final taste judgment")
    return reasons[:2]


def run_read_chunk(
    session_path: Path,
    *,
    chunk_dir: Path = DEFAULT_CHUNK_DIR,
    reaction_dir: Path = DEFAULT_REACTION_DIR,
    start_page: int | None = None,
    pages: int = 2,
    start_line: int | None = None,
    lines: int = 80,
    reaction_summary: str = "Reading chunk created for later personal reaction.",
    stance: str = "curious",
    affinity: float = 0.25,
    interest_delta: float = 0.0,
    advance: bool = True,
) -> dict[str, Any]:
    session = _load_json(session_path)
    errors = validate_slow_reading_session(session)
    if errors:
        raise ValueError("Invalid slow reading session: " + "; ".join(errors))
    source_path = _project_path(str(session.get("material", {}).get("source_path", "")))
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    text, position = extract_chunk_text(
        source_path,
        session,
        start_page=start_page,
        pages=pages,
        start_line=start_line,
        lines=lines,
    )
    chunk = build_chunk_record(session, source_path, text, position)
    reaction = build_reaction_draft(
        session,
        chunk,
        reaction_summary=reaction_summary,
        stance=stance,
        affinity=affinity,
        interest_delta=interest_delta,
    )
    reaction_errors = validate_reading_reaction(reaction)
    if reaction_errors:
        raise ValueError("Invalid reading reaction: " + "; ".join(reaction_errors))

    chunk_path = chunk_dir / f"{chunk['chunk_id']}.json"
    reaction_path = reaction_dir / f"{reaction['reaction_id']}.draft.json"
    _write_json(chunk_path, chunk)
    _write_json(reaction_path, reaction)
    ledger_entry = append_reading_event(
        reader=str(session["reader"]),
        title=str(chunk["source"].get("title", source_path.stem)),
        source_path=str(chunk["source"].get("source_path", _relative(source_path))),
        position=position,
        chunk_path=_relative(chunk_path),
        reaction_path=_relative(reaction_path),
        session_path=_relative(session_path),
        notes=["created_by_read_next_chunk"],
    )

    if advance:
        session = advance_session(
            session,
            unit_label=position["unit_label"],
            summary=reaction_summary,
            private_reaction="",
        )
        _write_json(session_path, session)

    return {
        "chunk_path": _relative(chunk_path),
        "reaction_path": _relative(reaction_path),
        "session_path": _relative(session_path),
        "position": position,
        "ledger_event_id": ledger_entry["event_id"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Read one small chunk from an active slow-reading session.")
    parser.add_argument("session_path")
    parser.add_argument("--start-page", type=int)
    parser.add_argument("--pages", type=int, default=2)
    parser.add_argument("--start-line", type=int)
    parser.add_argument("--lines", type=int, default=80)
    parser.add_argument("--reaction-summary", default="Reading chunk created for later personal reaction.")
    parser.add_argument("--stance", default="curious")
    parser.add_argument("--affinity", type=float, default=0.25)
    parser.add_argument("--interest-delta", type=float, default=0.0)
    parser.add_argument("--no-advance", action="store_true")
    parser.add_argument("--chunk-dir", default=str(DEFAULT_CHUNK_DIR))
    parser.add_argument("--reaction-dir", default=str(DEFAULT_REACTION_DIR))
    args = parser.parse_args()

    session_path = _project_path(args.session_path)
    chunk_dir = _project_path(args.chunk_dir)
    reaction_dir = _project_path(args.reaction_dir)
    result = run_read_chunk(
        session_path,
        chunk_dir=chunk_dir,
        reaction_dir=reaction_dir,
        start_page=args.start_page,
        pages=args.pages,
        start_line=args.start_line,
        lines=args.lines,
        reaction_summary=args.reaction_summary,
        stance=args.stance,
        affinity=args.affinity,
        interest_delta=args.interest_delta,
        advance=not args.no_advance,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
