"""
Recommend slow reading choices from Data/library.

The recommender is intentionally advisory. It notices new library arrivals,
matches broad themes/interests, avoids active sessions by default, and never
starts a reading session on its own.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_media_library_index import build_index
from check_media_library_updates import check_updates
from slow_reading import DEFAULT_INDEX_PATH, DEFAULT_OUTPUT_DIR, readable_entries
from validate_reading_interest_profile import validate_profile_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY_ROOT = PROJECT_ROOT / "Data" / "library"
DEFAULT_PROFILE_PATH = PROJECT_ROOT / "Data" / "reading" / "reading_interest_profiles.json"
DEFAULT_UPDATE_CHECK_PATH = PROJECT_ROOT / "Data" / "indexes" / "media_library_update_check.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "Data" / "reading" / "reading_recommendations.json"
DEFAULT_TASTE_DIR = PROJECT_ROOT / "Data" / "reading" / "tastes"


KEYWORDS_BY_THEME = {
    "identity": {"frankenstein", "dorian", "gatsby", "jane", "wonderland"},
    "creation": {"frankenstein", "ancient", "egypt"},
    "fear": {"dracula", "frankenstein", "dorian", "titanic"},
    "responsibility": {"presidents", "prohibition", "united_states", "history", "titanic"},
    "relationship": {"pride", "prejudice", "jane", "romeo", "juliet", "domestic_girlfriend"},
    "social_pressure": {"pride", "prejudice", "victorians", "tudors", "gatsby"},
    "jealousy": {"pride", "prejudice", "domestic_girlfriend", "gatsby"},
    "power": {"presidents", "tudors", "victorians", "prohibition", "united_states"},
    "history": {"history", "ancient", "egypt", "titanic", "tudors", "victorians", "presidents", "prohibition"},
    "worldbuilding": {"ancient", "egypt", "titanic", "tudors", "victorians", "odyssey", "wonderland"},
    "mystery": {"sherlock", "holmes"},
    "survival": {"titanic", "odyssey", "old_man", "sea", "monte_cristo"},
    "privacy": {"dracula", "dorian", "prohibition", "victorians"},
}

ERA_CONTEXT_KEYWORDS = {
    ("gatsby",): {"prohibition", "united_states", "presidents"},
    ("dracula", "dorian", "sherlock", "holmes", "jane_eyre", "great_expectations"): {"victorians"},
    ("romeo", "juliet", "shakespeare"): {"tudors"},
    ("odyssey", "homer"): {"ancient"},
    ("monte_cristo", "tale_of_two_cities"): {"history_year_by_year"},
    ("frankenstein",): {"victorians", "history_year_by_year"},
    ("moby_dick", "old_man", "sea"): {"titanic", "history_year_by_year"},
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def output_path_for_owner(output: Path, owner: str) -> Path:
    if output.name == DEFAULT_OUTPUT.name:
        return output.with_name(f"reading_recommendations_{owner}.json")
    return output


def _entry_text(entry: dict[str, Any]) -> str:
    return " ".join(
        str(entry.get(key, ""))
        for key in ("path", "name", "category", "media_type")
    ).lower()


def _active_paths(session_dir: Path = DEFAULT_OUTPUT_DIR) -> set[str]:
    paths = set()
    for path in sorted(session_dir.glob("*.json")):
        try:
            session = _load_json(path)
        except Exception:
            continue
        if session.get("status") in {"active", "paused"}:
            source_path = session.get("material", {}).get("source_path")
            if isinstance(source_path, str):
                paths.add(source_path)
    return paths


def _new_paths(update_check: dict[str, Any]) -> set[str]:
    return {
        str(entry.get("path"))
        for entry in update_check.get("added", [])
        if isinstance(entry, dict) and entry.get("path")
    }


def _same_source(left: str, right: str) -> bool:
    left_norm = left.replace("\\", "/").lower()
    right_norm = right.replace("\\", "/").lower()
    return left_norm == right_norm or left_norm.endswith(right_norm) or right_norm.endswith(left_norm)


def _contains_source(path: str, candidates: set[str]) -> bool:
    return any(_same_source(path, candidate) for candidate in candidates)


def _load_taste_profile(owner: str, taste_dir: Path = DEFAULT_TASTE_DIR) -> dict[str, Any]:
    path = taste_dir / f"reading_taste_profile_{owner}.json"
    if not path.exists():
        return {}
    data = _load_json(path)
    return data if isinstance(data, dict) else {}


def _profile_source_text(profile: dict[str, Any]) -> str:
    interests = profile.get("current_interests", {})
    if not isinstance(interests, dict):
        return ""
    paths = []
    for key in ("active_source_paths", "favorite_source_paths", "historical_context_source_paths"):
        value = interests.get(key, [])
        if isinstance(value, list):
            paths.extend(str(item) for item in value)
    return " ".join(paths).replace("\\", "/").lower()


def _era_context_matches(entry_text: str, profile: dict[str, Any]) -> list[str]:
    source_text = _profile_source_text(profile)
    matches = []
    for source_keywords, history_keywords in ERA_CONTEXT_KEYWORDS.items():
        if any(keyword in source_text for keyword in source_keywords) and any(keyword in entry_text for keyword in history_keywords):
            matches.append("_".join(source_keywords[:2]))
    return matches


def _score_entry(
    entry: dict[str, Any],
    profile: dict[str, Any],
    new_arrivals: set[str],
    active_paths: set[str],
    taste_profile: dict[str, Any] | None = None,
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    path = str(entry.get("path", ""))
    text = _entry_text(entry)
    category = str(entry.get("category", ""))

    if path in new_arrivals:
        score += 6
        reasons.append("new_library_arrival")
    if category in set(str(item) for item in profile.get("preferred_categories", [])):
        score += 3
        reasons.append(f"preferred_category:{category}")

    weights = profile.get("theme_weights", {})
    if isinstance(weights, dict):
        for theme, weight in weights.items():
            keywords = KEYWORDS_BY_THEME.get(str(theme), set())
            if any(keyword in text for keyword in keywords):
                score += int(weight)
                reasons.append(f"theme_match:{theme}")

    active_profile_paths = set(profile.get("current_interests", {}).get("active_source_paths", []))
    favorite_profile_paths = set(profile.get("current_interests", {}).get("favorite_source_paths", []))
    taste_profile = taste_profile or {}
    favorite_taste_paths = set(taste_profile.get("favorite_source_paths", []))
    cooling_taste_paths = set(taste_profile.get("cooling_or_outgrown_source_paths", []))
    if _contains_source(path, favorite_profile_paths):
        score += 4
        reasons.append("favorite_reread_candidate")
    if _contains_source(path, favorite_taste_paths):
        score += 4
        reasons.append("current_taste_favorite")
    if _contains_source(path, cooling_taste_paths):
        score -= 30
        reasons.append("recent_taste_cooling_or_outgrown")
    if _contains_source(path, active_paths) or _contains_source(path, active_profile_paths):
        score -= 8
        reasons.append("already_active_or_in_rotation")

    if category == "history":
        score += 1
        reasons.append("history_context_builder")
        for match in _era_context_matches(text, profile):
            score += 5
            reasons.append(f"story_era_context:{match}")
    if category in {"comic_books", "manga"}:
        score += 1
        reasons.append("post_gpu_visual_story_candidate")

    return score, reasons


def build_recommendations(
    *,
    owner: str,
    index_path: Path = DEFAULT_INDEX_PATH,
    profile_path: Path = DEFAULT_PROFILE_PATH,
    library_root: Path = DEFAULT_LIBRARY_ROOT,
    update_check_path: Path = DEFAULT_UPDATE_CHECK_PATH,
    taste_dir: Path = DEFAULT_TASTE_DIR,
    limit: int = 5,
    include_active: bool = False,
) -> dict[str, Any]:
    profiles = _load_json(profile_path)
    errors = validate_profile_file(profiles)
    if errors:
        raise ValueError("; ".join(errors))
    profile = next((item for item in profiles if item.get("owner") == owner), None)
    if profile is None:
        raise ValueError(f"No reading interest profile for owner: {owner}")

    if index_path.exists():
        index = _load_json(index_path)
    else:
        index = build_index(library_root)

    update_check = check_updates(library_root, index_path)
    update_check_path.parent.mkdir(parents=True, exist_ok=True)
    update_check_path.write_text(json.dumps(update_check, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    active_paths = _active_paths()
    new_arrivals = _new_paths(update_check)
    taste_profile = _load_taste_profile(owner, taste_dir)
    candidates = []
    for entry in readable_entries(index):
        path = str(entry.get("path", ""))
        active_profile_paths = set(profile.get("current_interests", {}).get("active_source_paths", []))
        if not include_active and (_contains_source(path, active_paths) or _contains_source(path, active_profile_paths)):
            continue
        score, reasons = _score_entry(entry, profile, new_arrivals, active_paths, taste_profile)
        if score <= 0:
            continue
        candidates.append(
            {
                "source_path": entry.get("path", ""),
                "title": Path(str(entry.get("name", ""))).stem,
                "category": entry.get("category", ""),
                "media_type": entry.get("media_type", ""),
                "score": score,
                "reasons": reasons,
                "recommendation_policy": {
                    "starts_reading_automatically": False,
                    "reader_may_decline": True,
                    "reader_may_keep_interest_private": True,
                    "use_slow_reading_session_if_chosen": True,
                    "favorite_reread_allowed_if_reader_chooses": True,
                    "history_context_followup_allowed_if_reader_chooses": True,
                },
            }
        )
    candidates.sort(key=lambda item: (-int(item["score"]), str(item["source_path"])))
    return {
        "recommendation_id": f"reading_recommendations_{owner}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "owner": owner,
        "new_arrivals_detected": sorted(new_arrivals),
        "active_paths_considered": sorted(active_paths),
        "recommendations": candidates[:limit],
        "policy": {
            "advisory_only": True,
            "does_not_start_reading": True,
            "does_not_create_memory": True,
            "does_not_create_temporary_ai": True,
            "new_arrivals_should_be_mentioned_to_owner": bool(new_arrivals),
            "favorite_books_may_be_reread_by_choice": True,
            "taste_profiles_can_change_recommendations": True,
            "story_era_history_followups_allowed_by_choice": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Recommend slow reading choices for Kira/Lisa.")
    parser.add_argument("--owner", required=True, choices=["kira", "lisa", "kira_lisa"])
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--index", default=str(DEFAULT_INDEX_PATH))
    parser.add_argument("--profiles", default=str(DEFAULT_PROFILE_PATH))
    parser.add_argument("--library-root", default=str(DEFAULT_LIBRARY_ROOT))
    parser.add_argument("--taste-dir", default=str(DEFAULT_TASTE_DIR))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--include-active", action="store_true", help="Allow already-active reading sessions to appear as continue-reading suggestions.")
    args = parser.parse_args()

    index_path = Path(args.index)
    if not index_path.is_absolute():
        index_path = PROJECT_ROOT / index_path
    profile_path = Path(args.profiles)
    if not profile_path.is_absolute():
        profile_path = PROJECT_ROOT / profile_path
    library_root = Path(args.library_root)
    if not library_root.is_absolute():
        library_root = PROJECT_ROOT / library_root
    taste_dir = Path(args.taste_dir)
    if not taste_dir.is_absolute():
        taste_dir = PROJECT_ROOT / taste_dir
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output = output_path_for_owner(output, args.owner)

    recommendations = build_recommendations(
        owner=args.owner,
        index_path=index_path,
        profile_path=profile_path,
        library_root=library_root,
        taste_dir=taste_dir,
        limit=args.limit,
        include_active=args.include_active,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(recommendations, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(recommendations, indent=2, ensure_ascii=False))
    print(f"Wrote {_relative(output)}")


if __name__ == "__main__":
    main()
