"""
Refresh media/source indexes and summarize TemporaryAI character candidates.

This connects the library update checker, media index, source indexer, and
source evidence extractor. It is intended for pre-GPU use when new files are
added under Data/library.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_media_library_index import DEFAULT_LIBRARY_ROOT, DEFAULT_OUTPUT as DEFAULT_MEDIA_INDEX_PATH
from build_media_library_index import build_index
from check_media_library_updates import DEFAULT_OUTPUT as DEFAULT_UPDATE_CHECK_PATH
from check_media_library_updates import check_updates


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARENT_ROOT = PROJECT_ROOT.parent
DEFAULT_SOURCE_CONFIG = PROJECT_ROOT / "TemporaryAI" / "config" / "sources.json"
DEFAULT_SOURCE_INDEX = PROJECT_ROOT / "Data" / "indexes" / "character_source_index.json"
DEFAULT_SOURCE_SCAN_LOG = PROJECT_ROOT / "Data" / "indexes" / "source_scan_log.json"
DEFAULT_EVIDENCE_ROOT = PROJECT_ROOT / "Data" / "processed" / "source_evidence"
DEFAULT_DISCOVERY_BRIEF = PROJECT_ROOT / "Data" / "processed" / "source_evidence" / "character_discovery_brief.json"

PARSEABLE_SOURCE_EXTENSIONS = {".pdf", ".txt", ".md"}
SOURCE_RELEVANT_CATEGORIES = {"script", "story", "novel", "tv_show", "movie"}


sys.path.insert(0, str(PROJECT_ROOT / "Core"))
from source_evidence_extractor import extract_all  # noqa: E402
from fanfic_variant_risk import review_fanfic_file  # noqa: E402
from source_indexer import load_json as load_source_config  # noqa: E402
from source_indexer import scan_sources, write_json  # noqa: E402


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_source_relevant(entry: dict[str, Any]) -> bool:
    return entry.get("category") in SOURCE_RELEVANT_CATEGORIES


def _classify_source_candidate(entry: dict[str, Any]) -> dict[str, Any]:
    extension = str(entry.get("extension", "")).lower()
    media_type = entry.get("media_type")
    category = entry.get("category")
    parseable_now = extension in PARSEABLE_SOURCE_EXTENSIONS and category in {"script", "story", "novel"}
    media_needs_future_analysis = media_type in {"video", "audio", "image"}

    if parseable_now:
        recommendation = "run_source_indexer_and_evidence_extractor"
    elif media_needs_future_analysis:
        recommendation = "index_as_media_now; add transcript/script or future audio_video_analysis before character evidence extraction"
    else:
        recommendation = "review_manually_before_source_extraction"

    return {
        "path": entry.get("path"),
        "name": entry.get("name"),
        "category": category,
        "media_type": media_type,
        "extension": extension,
        "parseable_by_pre_gpu_source_tools": parseable_now,
        "media_needs_future_analysis": media_needs_future_analysis,
        "recommendation": recommendation,
    }


def _source_candidates_from_updates(update_check: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for bucket in ("added", "changed"):
        for entry in update_check.get(bucket, []):
            if isinstance(entry, dict) and _is_source_relevant(entry):
                candidate = _classify_source_candidate(entry)
                candidate["change_type"] = bucket
                candidates.append(candidate)
    return candidates


def _build_character_discovery_brief(
    character_index: dict[str, Any],
    evidence_master_index: dict[str, Any],
    update_check: dict[str, Any],
    source_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    characters: list[dict[str, Any]] = []
    evidence_counts = evidence_master_index.get("characters", {})
    display_names: dict[str, str] = {}
    fanfic_risk_reviews: dict[tuple[str, str], dict[str, Any]] = {}

    for source in character_index.get("sources", []):
        if not isinstance(source, dict):
            continue
        for detected in source.get("detected_characters", []):
            if not isinstance(detected, dict):
                continue
            character_id = detected.get("character_id")
            display_name = detected.get("display_name")
            if isinstance(character_id, str) and isinstance(display_name, str):
                display_names[character_id] = display_name
            if source.get("source_authority") == "fanfic_variant" and isinstance(character_id, str):
                source_path = source.get("source_path")
                if isinstance(source_path, str):
                    path = Path(source_path)
                    if path.exists() and path.suffix.lower() in {".md", ".txt", ".pdf"}:
                        fanfic_risk_reviews[(character_id, source_path)] = review_fanfic_file(
                            path,
                            character_id=character_id,
                            character_age_coding="teen_coded" if character_id == "ladybug_marinette" else "unknown",
                        )

    for character_id, sources in sorted(character_index.get("by_character", {}).items()):
        if not isinstance(sources, list):
            continue

        canon_sources = [source for source in sources if source.get("source_authority") == "canon"]
        fanfic_sources = [source for source in sources if source.get("source_authority") == "fanfic_variant"]
        evidence_count = int(evidence_counts.get(character_id, {}).get("evidence_count", 0))
        display_name = display_names.get(character_id, character_id)
        if sources:
            display_name = sources[0].get("display_name") or display_name

        source_notes: list[str] = []
        if canon_sources:
            source_notes.append(f"{len(canon_sources)} canon source(s) detected.")
        if fanfic_sources:
            source_notes.append(f"{len(fanfic_sources)} fanfic/variant source(s) detected; keep variant-labeled.")
        if evidence_count:
            source_notes.append(f"{evidence_count} starter evidence item(s) extracted.")
        if not source_notes:
            source_notes.append("Detected as a possible character, but no extracted evidence is available yet.")

        characters.append({
            "character_id": character_id,
            "display_name": display_name,
            "source_count": len(sources),
            "canon_source_count": len(canon_sources),
            "fanfic_variant_source_count": len(fanfic_sources),
            "evidence_count": evidence_count,
            "candidate_for_future_temporary_ai": evidence_count > 0,
            "source_notes": source_notes,
            "sources": [
                {
                    "file_name": source.get("file_name"),
                    "source_authority": source.get("source_authority"),
                    "content_format": source.get("content_format"),
                    "matched_aliases": source.get("matched_aliases", []),
                    "mention_count": source.get("mention_count", 0),
                    "confidence": source.get("confidence", 0),
                    "fanfic_variant_risk_review": fanfic_risk_reviews.get(
                        (character_id, source.get("source_path", "")),
                    ),
                }
                for source in sources
            ],
        })

    return {
        "brief_id": "temporary_ai_character_discovery_brief_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Summarize which characters were detected in Data/library source material so Kira or Lisa can later request a TemporaryAI candidate such as Alix/Bunnyx.",
        "rules": {
            "source_material_remains_source": True,
            "detected_character_does_not_create_temporary_ai": True,
            "fanfic_must_remain_variant_labeled": True,
            "video_audio_media_need_transcript_or_future_analysis_before_evidence_extraction": True,
        },
        "media_update_summary": {
            "needs_index_refresh": update_check.get("needs_index_refresh"),
            "added_count": update_check.get("added_count"),
            "changed_count": update_check.get("changed_count"),
            "removed_count": update_check.get("removed_count"),
        },
        "source_candidates_from_new_or_changed_media": source_candidates,
        "characters": characters,
    }


def scan_library_sources(
    library_root: Path = DEFAULT_LIBRARY_ROOT,
    media_index_path: Path = DEFAULT_MEDIA_INDEX_PATH,
    update_check_path: Path = DEFAULT_UPDATE_CHECK_PATH,
    source_config_path: Path = DEFAULT_SOURCE_CONFIG,
    source_index_path: Path = DEFAULT_SOURCE_INDEX,
    evidence_root: Path = DEFAULT_EVIDENCE_ROOT,
    discovery_brief_path: Path = DEFAULT_DISCOVERY_BRIEF,
    force_source_refresh: bool = False,
) -> dict[str, Any]:
    update_check = check_updates(library_root, media_index_path)
    _write_json(update_check_path, update_check)

    media_index_refreshed = False
    if update_check["needs_index_refresh"]:
        _write_json(media_index_path, build_index(library_root))
        media_index_refreshed = True

    source_candidates = _source_candidates_from_updates(update_check)
    should_refresh_sources = force_source_refresh or bool(source_candidates) or not source_index_path.exists()

    source_summary: dict[str, Any] | None = None
    evidence_summary: dict[str, Any] | None = None
    discovery_brief: dict[str, Any] | None = None

    if should_refresh_sources:
        config = load_source_config(source_config_path)
        source_index = scan_sources(PARENT_ROOT, config)
        write_json(source_index_path, source_index)
        scan_log_path = config.get("index_output", {}).get("scan_log")
        if scan_log_path:
            write_json(PARENT_ROOT / scan_log_path, {
                "generated_at": source_index["generated_at"],
                "summary": source_index["summary"],
                "missing_folders": source_index["missing_folders"],
                "skipped_duplicates": source_index["skipped_duplicates"],
                "errors": source_index["errors"],
            })

        evidence_summary = extract_all(PARENT_ROOT, source_index_path, evidence_root)
        evidence_master_index = _read_json(evidence_root / "source_evidence_master_index.json")
        discovery_brief = _build_character_discovery_brief(
            source_index,
            evidence_master_index,
            update_check,
            source_candidates,
        )
        _write_json(discovery_brief_path, discovery_brief)
        source_summary = source_index["summary"]
    elif source_index_path.exists() and (evidence_root / "source_evidence_master_index.json").exists():
        source_index = _read_json(source_index_path)
        evidence_master_index = _read_json(evidence_root / "source_evidence_master_index.json")
        discovery_brief = _build_character_discovery_brief(
            source_index,
            evidence_master_index,
            update_check,
            source_candidates,
        )
        _write_json(discovery_brief_path, discovery_brief)
        source_summary = source_index.get("summary", {})

    return {
        "scan_id": "library_source_scan_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "media_index_refreshed": media_index_refreshed,
        "source_refresh_ran": should_refresh_sources,
        "update_check_path": _relative(update_check_path),
        "media_index_path": _relative(media_index_path),
        "source_index_path": _relative(source_index_path),
        "evidence_root": _relative(evidence_root),
        "discovery_brief_path": _relative(discovery_brief_path),
        "update_summary": {
            "needs_index_refresh": update_check.get("needs_index_refresh"),
            "added_count": update_check.get("added_count"),
            "changed_count": update_check.get("changed_count"),
            "removed_count": update_check.get("removed_count"),
        },
        "source_candidates_detected": len(source_candidates),
        "source_index_summary": source_summary,
        "evidence_summary": evidence_summary,
        "characters_in_discovery_brief": len(discovery_brief.get("characters", [])) if discovery_brief else 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect new library material and refresh TemporaryAI source evidence.")
    parser.add_argument("--force-source-refresh", action="store_true", help="Run source index/evidence extraction even if no new source candidates were detected.")
    args = parser.parse_args()

    result = scan_library_sources(force_source_refresh=args.force_source_refresh)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
