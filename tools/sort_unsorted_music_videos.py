"""
Move music videos from Data/library/music/unsorted into by-artist folders.

The sorter is conservative: it only moves video files, keeps duplicates instead
of deleting them, and writes a JSON plan/result for review.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auto_rename_media_library import normalize_name


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "Data" / "library" / "music" / "unsorted"
DEFAULT_TARGET_ROOT = PROJECT_ROOT / "Data" / "library" / "music" / "music_videos" / "by_artist"
DEFAULT_OUTPUT = PROJECT_ROOT / "Data" / "indexes" / "music_video_sort_plan.json"
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".m4v"}

EXACT_OVERRIDES = {
    "if i believed in me song miraculous the movie now available on netflix": (
        "miraculous_movie_cast",
        "if_i_believed_in_me_from_miraculous_the_movie",
    ),
    "you are ladybug song miraculous the movie now available on netflix": (
        "miraculous_movie_cast",
        "you_are_ladybug_from_miraculous_the_movie",
    ),
    "annie 2014 i think i m gonna like it here sing along sony pictures kids zone": (
        "annie_2014_cast",
        "i_think_i_m_gonna_like_it_here",
    ),
    "annie 2014 it s the hard knock life sing along sony pictures kids zone": (
        "annie_2014_cast",
        "its_the_hard_knock_life",
    ),
    "barenaked ladies - big bang theory": ("barenaked_ladies", "big_bang_theory_theme"),
    "can t stop singing music video teen beach movie disney channel official": (
        "teen_beach_movie_cast",
        "can_t_stop_singing_from_teen_beach_movie",
    ),
    "chanson gotta be me teen beach 2 disney channel be": (
        "teen_beach_2_cast",
        "gotta_be_me_from_teen_beach_2",
    ),
    "courage in me sing along miraculous ladybug cat noir the movie netflix after school": (
        "miraculous_movie_cast",
        "courage_in_me_from_miraculous_the_movie",
    ),
    "crisis on infinite earths recap raps": ("recap_raps", "crisis_on_infinite_earths"),
    "exclusive watch zachary levi and krysta rodriguez record first impressions from first date": (
        "first_date_cast",
        "first_impressions_from_first_date",
    ),
    "frozen do you want to build a snowman hd": ("frozen_cast", "do_you_want_to_build_a_snowman"),
    "frozen for the first time in forever hd": ("frozen_cast", "for_the_first_time_in_forever"),
    "go freaky friday disney channel": ("freaky_friday_2018_cast", "go_from_freaky_friday_2018"),
    "hannah montana ordinary girl music video official disney channel uk": ("hannah_montana", "ordinary_girl"),
    "hannah montana supergirl music video official disney channel uk": ("hannah_montana", "supergirl"),
    "john schneider good ole boys music video": ("john_schneider", "good_ole_boys"),
    "like me from teen beach movie": ("teen_beach_movie_cast", "like_me_from_teen_beach_movie"),
    "man to woman emilia perez": ("emilia_perez_cast", "man_to_woman"),
    "meant to be from teen beach movie": ("teen_beach_movie_cast", "meant_to_be_from_teen_beach_movie"),
    "miraculous ladybug laura marano s theme song music video nick": (
        "laura_marano",
        "miraculous_ladybug_theme_song",
    ),
    "miraculous ladybug theme song music video ft lou lenni kim disney channel uk": (
        "lou_and_lenni_kim",
        "miraculous_ladybug_theme_song",
    ),
    "oh biology from the disney channel original movie freaky friday": (
        "freaky_friday_2018_cast",
        "oh_biology_from_freaky_friday_2018",
    ),
    "paddington shine co written by gwen stefani pharrell the weinstein company": (
        "gwen_stefani_and_pharrell",
        "shine_from_paddington",
    ),
    "sail awolnation youtube": ("awolnation", "sail"),
    "sadie stanley call me beep me from kim possible": ("sadie_stanley", "call_me_beep_me_from_kim_possible"),
    "safer first date": ("first_date_cast", "safer_from_first_date"),
    "the lion king can you feel the love tonight": (
        "the_lion_king_cast",
        "can_you_feel_the_love_tonight",
    ),
    "the little mermaid lyric video part of your world sing along": (
        "the_little_mermaid_cast",
        "part_of_your_world",
    ),
    "wildside": (
        "sabrina_carpenter_and_sofia_carson",
        "wildside_from_adventures_in_babysitting",
    ),
    "wildside from adventures in babysitting": (
        "sabrina_carpenter_and_sofia_carson",
        "wildside_from_adventures_in_babysitting",
    ),
    "wildside from adventures in babysitting official lyric video": (
        "sabrina_carpenter_and_sofia_carson",
        "wildside_from_adventures_in_babysitting",
    ),
    "wizards of waverly place a year without rain music video selena gomez official disney channel uk": (
        "selena_gomez",
        "a_year_without_rain_from_wizards_of_waverly_place",
    ),
    "wreck it ralph owl city music video when can i see you again 2012 john c reilly movie hd": (
        "owl_city",
        "when_can_i_see_you_again_from_wreck_it_ralph",
    ),
    "ariana debose this wish live from disneyland paris": (
        "ariana_debose",
        "this_wish_live_from_disneyland_paris",
    ),
    "defying gravity wicked 20th anniversary edition wicked the musical": (
        "wicked_20th_anniversary_cast",
        "defying_gravity_wicked_the_musical",
    ),
    "defying gravity x go the distance pentatonix live stream christmas 2023 tiktok with crowd choir": (
        "pentatonix",
        "defying_gravity_x_go_the_distance_live_stream_christmas_2023",
    ),
    "emilia jones both sides now baftas 2022 performance from coda": (
        "emilia_jones",
        "both_sides_now_baftas_2022_performance_from_coda",
    ),
    "kristen bell performs do you want to build a snowman at frozen fandemonium d23 expo 2015": (
        "kristen_bell",
        "do_you_want_to_build_a_snowman_frozen_fandemonium_d23_expo_2015",
    ),
    "leakycon portland la vie boheme fandom parody": (
        "leakycon_portland_cast",
        "la_vie_boheme_fandom_parody",
    ),
    "p nk just like fire 2016 billboard music awards performance": (
        "p_nk",
        "just_like_fire_2016_billboard_music_awards_performance",
    ),
    "savannah singing little wonders new song live city walk dec 13 2009": (
        "savannah",
        "little_wonders_live_city_walk_2009",
    ),
    "seasons of love performed by the cast of rent": (
        "rent_cast",
        "seasons_of_love",
    ),
    "the boxer rebellion new york": ("the_boxer_rebellion", "new_york"),
    "ray parker jr ghostbusters 1984": ("ray_parker_jr", "ghostbusters_1984"),
}


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _simplify(stem: str) -> str:
    cleaned = stem.replace("%20", " ")
    cleaned = cleaned.replace("%28", " ").replace("%29", " ")
    cleaned = cleaned.replace("&", " and ")
    cleaned = re.sub(r"\[[^\]]*\]", " ", cleaned)
    cleaned = re.sub(r"\([^\)]*(official|video|youtube|hd|remaster|audio|clean version)[^\)]*\)", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", cleaned).strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _slug(value: str) -> str:
    return normalize_name(value, is_file=False)


def _clean_title(value: str) -> str:
    value = re.sub(r"\bOfficial Music Video\b", " ", value, flags=re.I)
    value = re.sub(r"\bOfficial Video\b", " ", value, flags=re.I)
    value = re.sub(r"\bOfficial Lyric Video\b", " ", value, flags=re.I)
    value = re.sub(r"\bYouTube\b", " ", value, flags=re.I)
    value = re.sub(r"\bVIDEO\b", " ", value, flags=re.I)
    value = re.sub(r"\bHD Remaster\b", " ", value, flags=re.I)
    value = re.sub(r"\bFull HD\b", " ", value, flags=re.I)
    value = re.sub(r"\bDigitally Remastered and Upscaled\b", " ", value, flags=re.I)
    value = re.sub(r"\s+", " ", value).strip(" -_.,")
    return value or "untitled"


def infer_artist_title(path: Path) -> tuple[str, str]:
    stem = path.stem.replace("%20", " ").replace("%28", " ").replace("%29", " ")
    simple = _simplify(stem)
    if simple in EXACT_OVERRIDES:
        return EXACT_OVERRIDES[simple]

    match = re.match(r"(.+?)\s+-\s+(.+)", stem)
    if match:
        artist = _slug(match.group(1))
        title = _slug(_clean_title(match.group(2)))
        return artist, title

    parts = re.split(r"\s{2,}", stem, maxsplit=1)
    if len(parts) == 2:
        return _slug(parts[0]), _slug(_clean_title(parts[1]))

    return "unknown_artist", _slug(_clean_title(stem))


def unique_target(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}_duplicate_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def build_plan(source_dir: Path = DEFAULT_SOURCE_DIR, target_root: Path = DEFAULT_TARGET_ROOT) -> dict[str, Any]:
    operations: list[dict[str, Any]] = []
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        artist, title = infer_artist_title(path)
        target = unique_target(target_root / artist / f"{artist}_{title}{path.suffix.lower()}")
        operations.append(
            {
                "source": _relative(path),
                "target": _relative(target),
                "artist": artist,
                "title": title,
                "blocked": False,
                "issues": [],
            }
        )
    return {
        "plan_id": "music_video_sort_plan_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": _relative(source_dir),
        "target_root": _relative(target_root),
        "operation_count": len(operations),
        "blocked_count": sum(1 for item in operations if item["blocked"]),
        "operations": operations,
    }


def _project_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def apply_plan(plan: dict[str, Any]) -> dict[str, Any]:
    applied: list[dict[str, str]] = []
    skipped: list[dict[str, Any]] = []
    for operation in plan.get("operations", []):
        if operation.get("blocked"):
            skipped.append(operation)
            continue
        source = _project_path(str(operation["source"]))
        target = _project_path(str(operation["target"]))
        if not source.exists():
            skipped.append({**operation, "issues": [*operation.get("issues", []), "source_missing"]})
            continue
        target = unique_target(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        applied.append({"source": operation["source"], "target": _relative(target)})
    return {"applied_count": len(applied), "skipped_count": len(skipped), "applied": applied, "skipped": skipped}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sort unsorted music videos into by-artist folders.")
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR))
    parser.add_argument("--target-root", default=str(DEFAULT_TARGET_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    if not source_dir.is_absolute():
        source_dir = PROJECT_ROOT / source_dir
    target_root = Path(args.target_root)
    if not target_root.is_absolute():
        target_root = PROJECT_ROOT / target_root
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output

    plan = build_plan(source_dir, target_root)
    if args.apply:
        plan["last_run"] = {"apply_requested": True, "apply_result": apply_plan(plan)}
        plan = build_plan(source_dir, target_root) | {"last_run": plan["last_run"]}
    else:
        plan["last_run"] = {"apply_requested": False, "apply_result": None}
    write_json(output, plan)
    print(f"Planned {plan['operation_count']} music video moves.")
    print(f"Blocked {plan['blocked_count']} operations.")
    if args.apply:
        result = plan["last_run"]["apply_result"]
        print(f"Applied {result['applied_count']} operations; skipped {result['skipped_count']}.")
    print(f"Wrote {_relative(output)}")


if __name__ == "__main__":
    main()
