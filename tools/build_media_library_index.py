"""
Build a lightweight index of local media under Data/library.

This does not read or play media contents. It only records file paths,
extensions, rough media categories, and privacy-safe usage notes.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY_ROOT = PROJECT_ROOT / "Data" / "library"
DEFAULT_OUTPUT = PROJECT_ROOT / "Data" / "indexes" / "media_library_index.json"

AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".m4v"}
DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
IGNORED_FILENAMES = {"thumbs.db", "desktop.ini"}


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def classify_file(path: Path, library_root: Path = DEFAULT_LIBRARY_ROOT) -> dict[str, str]:
    suffix = path.suffix.lower()
    relative_parts = [part.lower() for part in path.relative_to(library_root).parts]
    top_level = relative_parts[0] if relative_parts else "unknown"

    if suffix in AUDIO_EXTENSIONS:
        media_type = "audio"
    elif suffix in VIDEO_EXTENSIONS:
        media_type = "video"
    elif suffix in DOCUMENT_EXTENSIONS:
        media_type = "document"
    elif suffix in IMAGE_EXTENSIONS:
        media_type = "image"
    else:
        media_type = "other"

    if top_level == "unsorted":
        category = "unsorted_intake"
    elif top_level == "music":
        category = "music"
        if "music_videos" in relative_parts:
            category = "music_video"
        elif "soundtracks" in relative_parts:
            category = "soundtrack"
    elif top_level == "movies":
        category = "movie"
        if "clips" in relative_parts:
            category = "movie_clip"
    elif top_level == "personal_videos":
        category = "personal_video"
    elif top_level == "video_commentary":
        category = "video_commentary"
    elif top_level == "video_tutorials":
        category = "tutorial_video"
    elif top_level == "video_commercials":
        category = "commercial_video"
    elif top_level == "video_skits_and_parodies":
        category = "skit_or_parody_video"
    elif top_level == "private_adult_videos":
        category = "private_adult_media"
    elif top_level == "radio_shows":
        category = "radio_show"
    elif top_level == "documentaries":
        category = "documentary"
    elif top_level == "tv_shows":
        category = "tv_show"
        if "clips" in relative_parts:
            category = "tv_clip"
    elif top_level == "scripts":
        category = "script"
    elif top_level == "stories":
        category = "story"
    elif top_level == "novels":
        category = "novel"
    else:
        category = top_level

    return {"media_type": media_type, "category": category}


def unsorted_intake_for(path: Path, library_root: Path = DEFAULT_LIBRARY_ROOT) -> dict[str, Any] | None:
    relative_parts = list(path.relative_to(library_root).parts)
    if not relative_parts or relative_parts[0].lower() != "unsorted":
        return None
    folder_parts = relative_parts[1:-1]
    top_folder = folder_parts[0] if folder_parts else ""
    name = path.name.lower()
    folder_text = " ".join(part.lower() for part in folder_parts)
    combined = f"{folder_text} {name}"

    subtype = "unknown_unsorted_item"
    confidence = "low"
    if "multifandom" in combined:
        subtype = "multifandom_fan_music_video"
        confidence = "high"
    elif "cover videos" in folder_text or "cover" in combined or "pentatonix" in combined or "one voice" in combined:
        subtype = "cover_or_performance_video"
        confidence = "medium"
    elif "commercial" in combined or " tvc" in combined or "toy" in combined or "action figure" in combined:
        subtype = "commercial_or_toy_promo"
        confidence = "high"
    elif "trailer" in combined or "promo" in combined or "first look" in combined or "comic-con" in combined:
        subtype = "trailer_or_promo_clip"
        confidence = "high"
    elif "deleted scene" in combined or "alternate ending" in combined or "scene" in combined or "clip" in combined:
        subtype = "movie_or_show_clip"
        confidence = "high"
    elif "song" in combined or "lyric video" in combined or "music video" in combined or "full performance" in combined:
        subtype = "song_or_performance_clip"
        confidence = "medium"
    elif "watchmojo" in folder_text or "screencrush" in folder_text or "breakdown" in combined or "honest trailers" in combined:
        subtype = "commentary_or_list_video"
        confidence = "high"
    elif "how to" in folder_text or "tutorial" in combined:
        subtype = "how_to_or_tutorial_video"
        confidence = "high"
    elif "robert mcmurrer" in folder_text:
        subtype = "personal_or_robert_created_video"
        confidence = "medium"
    elif top_folder:
        subtype = "franchise_or_title_reference_clip"
        confidence = "medium"

    return {
        "intake_root": "Data/library/unsorted",
        "folder_hint": "/".join(folder_parts),
        "subtype": subtype,
        "confidence": confidence,
        "status": "leave_in_unsorted_until_reviewed",
        "usage_note": (
            "Treat as intake/reference material. Do not treat as a full movie, full episode, "
            "canon source, or watched/listened experience unless Robert later sorts it or a "
            "separate viewing/listening note is created."
        ),
    }


def world_display_for(classification: dict[str, str]) -> dict[str, Any]:
    media_type = classification["media_type"]
    category = classification["category"]

    display = {
        "can_appear_as_3d_object": True,
        "home_shelf_eligible": True,
        "virtual_screen_playback_eligible": False,
        "virtual_movie_theater_eligible": False,
        "preferred_home_object": "library_item",
        "preferred_home_location": "shared_media_library",
        "notes": "World display metadata only; does not play or understand media by itself.",
    }
    if category == "movie":
        display.update(
            {
                "virtual_screen_playback_eligible": True,
                "virtual_movie_theater_eligible": True,
                "preferred_home_object": "dvd_or_vhs_case",
                "preferred_home_location": "living_room_media_shelf",
            }
        )
    elif category == "movie_clip":
        display.update(
            {
                "virtual_screen_playback_eligible": True,
                "preferred_home_object": "movie_clip_video_file",
                "preferred_home_location": "movie_clip_shelf",
                "notes": "Movie clip metadata only; do not treat as a full movie or complete canon context.",
            }
        )
    elif category == "documentary":
        display.update(
            {
                "virtual_screen_playback_eligible": True,
                "virtual_movie_theater_eligible": True,
                "preferred_home_object": "documentary_disc_or_tape",
                "preferred_home_location": "documentary_media_shelf",
            }
        )
    elif category == "tv_show":
        display.update(
            {
                "virtual_screen_playback_eligible": True,
                "virtual_movie_theater_eligible": True,
                "preferred_home_object": "season_disc_case_or_vhs_tape",
                "preferred_home_location": "series_shelf",
            }
        )
    elif category == "tv_clip":
        display.update(
            {
                "virtual_screen_playback_eligible": True,
                "preferred_home_object": "episode_clip_video_file",
                "preferred_home_location": "series_clip_shelf",
                "notes": "TV show clip metadata only; do not treat as a full episode or complete canon context.",
            }
        )
    elif category == "music_video":
        display.update(
            {
                "virtual_screen_playback_eligible": True,
                "virtual_movie_theater_eligible": True,
                "preferred_home_object": "music_video_disc_or_tape",
                "preferred_home_location": "music_video_shelf",
            }
        )
    elif category == "personal_video":
        display.update(
            {
                "virtual_screen_playback_eligible": True,
                "preferred_home_object": "personal_video_file_or_tape",
                "preferred_home_location": "private_personal_video_shelf",
                "notes": "Personal/local recording metadata only; do not treat as watched, public, or interpreted without a viewing note.",
            }
        )
    elif category == "video_commentary":
        display.update(
            {
                "virtual_screen_playback_eligible": True,
                "preferred_home_object": "commentary_video_file_or_playlist",
                "preferred_home_location": "commentary_and_facts_video_shelf",
                "notes": "Information/list/facts video metadata only; does not verify claims until watched or separately sourced.",
            }
        )
    elif category == "tutorial_video":
        display.update(
            {
                "virtual_screen_playback_eligible": True,
                "preferred_home_object": "tutorial_video_file_or_playlist",
                "preferred_home_location": "tutorial_video_shelf",
                "notes": "How-to/tutorial metadata only; do not treat as learned skill until watched and a learning note is saved.",
            }
        )
    elif category == "commercial_video":
        display.update(
            {
                "virtual_screen_playback_eligible": True,
                "preferred_home_object": "commercial_or_promo_video_file",
                "preferred_home_location": "commercial_and_promo_video_shelf",
                "notes": "Commercial/promo metadata only; not a full episode, movie, or canon source.",
            }
        )
    elif category == "skit_or_parody_video":
        display.update(
            {
                "virtual_screen_playback_eligible": True,
                "preferred_home_object": "skit_or_parody_video_file",
                "preferred_home_location": "skits_and_parodies_shelf",
                "notes": "Comedy/skit/parody metadata only; do not treat as canon source material.",
            }
        )
    elif category == "private_adult_media":
        display.update(
            {
                "can_appear_as_3d_object": False,
                "home_shelf_eligible": False,
                "virtual_screen_playback_eligible": True,
                "virtual_movie_theater_eligible": True,
                "preferred_home_object": "restricted_private_adult_media_file",
                "preferred_home_location": "restricted_private_adult_library",
                "notes": "Private adult-media metadata. Adult books may be read pre-GPU if chosen; adult videos may be watched post-GPU if Kira/Lisa or another adult AI explicitly chooses them under the right privacy state. Not casual/default browsing.",
            }
        )
    elif category == "soundtrack":
        display.update(
            {
                "preferred_home_object": "soundtrack_cd_or_digital_album_case",
                "preferred_home_location": "soundtrack_shelf",
            }
        )
    elif category == "radio_show":
        display.update(
            {
                "preferred_home_object": "radio_show_audio_file_or_reel",
                "preferred_home_location": "old_time_radio_shelf",
                "notes": "Radio show metadata only; may be listened to pre-GPU and can create listening/taste notes if chosen.",
            }
        )
    elif category == "music" or media_type == "audio":
        display.update(
            {
                "preferred_home_object": "cd_record_or_digital_album_case",
                "preferred_home_location": "music_shelf",
            }
        )
    elif category in {"script", "story", "novel"} or media_type == "document":
        display.update(
            {
                "preferred_home_object": "book_script_binder_or_document",
                "preferred_home_location": "reading_shelf",
            }
        )
    elif media_type == "image":
        display.update(
            {
                "preferred_home_object": "photo_or_reference_card",
                "preferred_home_location": "reference_board_or_shelf",
            }
        )
    return display


def build_index(library_root: Path = DEFAULT_LIBRARY_ROOT) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    counts_by_type: dict[str, int] = {}
    counts_by_category: dict[str, int] = {}

    for path in sorted(library_root.rglob("*")):
        if not path.is_file():
            continue
        if path.name.lower() in IGNORED_FILENAMES:
            continue
        classification = classify_file(path, library_root)
        unsorted_intake = unsorted_intake_for(path, library_root)
        media_type = classification["media_type"]
        category = classification["category"]
        counts_by_type[media_type] = counts_by_type.get(media_type, 0) + 1
        counts_by_category[category] = counts_by_category.get(category, 0) + 1
        library_use = {
            "can_be_used_with_door_unlocked": True,
            "can_be_used_with_door_locked": True,
            "can_be_chosen_by_kira_or_lisa_when_bored_or_relaxing": True,
            "can_create_curiosity_or_learning_notes": True,
            "can_create_slow_reading_session": category in {"script", "story", "novel", "comic_books", "manga"} or media_type == "document",
            "can_create_reading_source_extraction_candidate": category in {"script", "story", "novel", "comic_books", "manga"} or media_type == "document",
            "character_profile_requires_separate_temporary_ai_request": True,
            "place_reconstruction_requires_separate_notebook_world_request": True,
            "can_inspire_temporary_ai_request_later": True,
            "creates_memory_automatically": False,
            "creates_temporary_ai_automatically": False,
            "creates_notebook_world_automatically": False,
            "source_material_remains_source": True,
        }
        privacy_default = "owner_or_session_controlled"
        if category == "private_adult_media":
            is_adult_document = media_type == "document"
            is_adult_video = media_type == "video"
            privacy_default = "restricted_private_adult"
            library_use.update(
                {
                    "can_be_used_with_door_unlocked": False,
                    "can_be_used_with_door_locked": True,
                    "can_be_chosen_by_kira_or_lisa_when_bored_or_relaxing": False,
                    "can_create_curiosity_or_learning_notes": True,
                    "can_create_slow_reading_session": is_adult_document,
                    "can_create_reading_source_extraction_candidate": is_adult_document,
                    "character_profile_requires_separate_temporary_ai_request": False,
                    "place_reconstruction_requires_separate_notebook_world_request": False,
                    "can_inspire_temporary_ai_request_later": True,
                    "pre_gpu_reading_eligible_if_chosen": is_adult_document,
                    "post_gpu_viewing_eligible_if_chosen": is_adult_video,
                    "adult_ai_access_eligible_if_chosen": True,
                    "requires_explicit_kira_lisa_interest": True,
                    "requires_private_adult_context": True,
                    "not_for_default_recommendations": True,
                }
            )

        entry = {
                "path": _relative(path),
                "name": path.name,
                "extension": path.suffix.lower(),
                "media_type": media_type,
                "category": category,
                "size_bytes": path.stat().st_size,
                "privacy_default": privacy_default,
                "library_use": library_use,
                "world_display": world_display_for(classification),
            }
        if unsorted_intake:
            entry["unsorted_intake"] = unsorted_intake
        entries.append(entry)

    return {
        "index_id": "media_library_index_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "library_root": _relative(library_root),
        "entry_count": len(entries),
        "counts_by_type": dict(sorted(counts_by_type.items())),
        "counts_by_category": dict(sorted(counts_by_category.items())),
        "usage_policy": {
            "kira_lisa_may_use_with_or_without_locked_door": True,
            "kira_lisa_may_choose_library_items_for_boredom_relaxation_or_curiosity": True,
            "locked_door_controls_who_can_observe": True,
            "reading_watching_or_listening_may_create_curiosity_or_learning_notes": True,
            "reading_should_use_slow_reading_sessions": True,
            "reading_may_create_source_extraction_candidates": True,
            "source_extraction_candidates_may_support_temporary_ai_or_notebook_world_requests": True,
            "watching_or_listening_may_create_notes": True,
            "watching_or_listening_does_not_create_lived_memory": True,
            "library_items_may_inspire_temporary_ai_request_later": True,
            "media_does_not_create_temporary_ai_without_separate_approval": True,
            "library_items_may_have_3d_shelf_representations_later": True,
            "movies_and_shows_may_play_on_virtual_screen_or_movie_theater_later": True,
        },
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the local media library index.")
    parser.add_argument("--library-root", default=str(DEFAULT_LIBRARY_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    library_root = Path(args.library_root)
    if not library_root.is_absolute():
        library_root = PROJECT_ROOT / library_root
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output

    index = build_index(library_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {index['entry_count']} media/library entries to {_relative(output)}")


if __name__ == "__main__":
    main()
