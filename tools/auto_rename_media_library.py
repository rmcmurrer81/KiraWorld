"""
Plan or apply safe automatic Data/library filename cleanup.

The tool normalizes obvious download-style names into stable ASCII snake_case.
It is intentionally conservative: it renames files/folders in place, avoids
collisions, and writes a plan before applying changes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from audit_media_library_names import build_audit
from build_media_library_index import DEFAULT_LIBRARY_ROOT, DEFAULT_OUTPUT as DEFAULT_INDEX_PATH
from build_media_library_index import build_index
from check_media_library_updates import DEFAULT_OUTPUT as DEFAULT_UPDATE_CHECK_PATH
from check_media_library_updates import check_updates


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN_OUTPUT = PROJECT_ROOT / "Data" / "indexes" / "media_library_rename_plan.json"
DEFAULT_AUDIT_OUTPUT = PROJECT_ROOT / "Data" / "indexes" / "media_library_name_audit.json"

DOWNLOAD_LABELS = (
    "official video",
    "official music video",
    "full movie",
    "full episode",
    "watch party",
    "youtube",
    "1080p",
    "720p",
    "480p",
)

TYPO_REPLACEMENTS = {
    "epidode": "episode",
    "preformances": "performances",
    "preformance": "performance",
    "perfomance": "performance",
    "soundtrak": "soundtrack",
    "tacks": "tracks",
    "heroez": "heroez",
}

CANONICAL_FILE_NAMES = {
    "doctor_who_s14e01_23_nov_2023_the_star_beast_540p_mp4.mp4": (
        "doctor_who_s00e01_the_star_beast_2023_special.mp4"
    ),
    "genesis_of_the_daleks_s_season_12_doctor_who.mp4": (
        "doctor_who_s12e11_e16_genesis_of_the_daleks.mp4"
    ),
    "spearhead_from_space_s_season_7_doctor_who.mp4": (
        "doctor_who_s07e01_e04_spearhead_from_space.mp4"
    ),
    "twin_peaks_fire_walk_with_me_1992_complete_in_english.mp4": (
        "twin_peaks_fire_walk_with_me_1992.mp4"
    ),
    "wizards_beyond_waverly_place_first_everything_is_not_what_it_seems_disneychannel.mp4": (
        "wizards_beyond_waverly_place_s01e01_everything_is_not_what_it_seems.mp4"
    ),
    "wizards_beyond_waverly_place_s2_finale_disneychannel.mp4": (
        "wizards_beyond_waverly_place_s02e00_finale.mp4"
    ),
    "the_computer_wore_tennis_shoes.mp4": (
        "the_computer_wore_tennis_shoes_1995.mp4"
    ),
    "from_the_confidential_casefiles_of_agent_22_s01e17_ducktales_disneyxd.mp4": (
        "ducktales_s01e17_from_the_confidential_casefiles_of_agent_22.mp4"
    ),
    "jaw_s01e16_ducktales_disneyxd.mp4": "ducktales_s01e16_jaw.mp4",
    "let_s_get_dangerous_ducktales_disney_xd.mp4": "ducktales_s03e12_lets_get_dangerous.mp4",
    "mcmystery_at_mcduck_mcmanor_s01e10_ducktales_disneyxd.mp4": (
        "ducktales_s01e10_mcmystery_at_mcduck_mcmanor.mp4"
    ),
    "terror_of_the_terra_firmians_s01e09_ducktales_disneyxd.mp4": (
        "ducktales_s01e09_terror_of_the_terra_firmians.mp4"
    ),
    "the_last_crash_of_the_sunchaser_s01e22_ducktales_disneyxd.mp4": (
        "ducktales_s01e22_the_last_crash_of_the_sunchaser.mp4"
    ),
    "the_other_bin_of_scrooge_mcduck_s01e21_ducktales_disneyxd.mp4": (
        "ducktales_s01e21_the_other_bin_of_scrooge_mcduck.mp4"
    ),
    "the_shadow_war_s01e23_ducktales_disneyxd.mp4": (
        "ducktales_s01e23_the_shadow_war.mp4"
    ),
    "the_spear_of_selene_s01e12_ducktales_disneyxd.mp4": (
        "ducktales_s01e12_the_spear_of_selene.mp4"
    ),
    "who_is_gizmoduck_s01e20_ducktales_disneyxd.mp4": (
        "ducktales_s01e20_who_is_gizmoduck.mp4"
    ),
    "popcornarchive_startrekinsurrection1998.mp4": "star_trek_insurrection_1998.mp4",
    "8738805647941.mp4": "buffy_the_vampire_slayer_1992.mp4",
    "buffy_the_vampire_slayer_1992.pdf": "buffy_the_vampire_slayer_1992_script_1990_04_01.pdf",
    "cartoon_all_stars_to_the_rescue_vhs_1990.mp4": "cartoon_all_stars_to_the_rescue_1990_special.mp4",
    "0_the_christmas_invasion.mp4": "doctor_who_2005_s02e00_the_christmas_invasion_2005_special.mp4",
    "1_new_earth.mp4": "doctor_who_2005_s02e01_new_earth.mp4",
    "2_tooth_and_claw.mp4": "doctor_who_2005_s02e02_tooth_and_claw.mp4",
    "3_school_reunion.mp4": "doctor_who_2005_s02e03_school_reunion.mp4",
    "5_rise_of_the_cybermen.mp4": "doctor_who_2005_s02e05_rise_of_the_cybermen.mp4",
    "6_the_age_of_steel.mp4": "doctor_who_2005_s02e06_the_age_of_steel.mp4",
    "7_the_idiot_s_lantern.mp4": "doctor_who_2005_s02e07_the_idiots_lantern.mp4",
    "8_the_impossible_planet.mp4": "doctor_who_2005_s02e08_the_impossible_planet.mp4",
    "9_the_satans_pit.mp4": "doctor_who_2005_s02e09_the_satan_pit.mp4",
    "12_army_of_ghosts.mp4": "doctor_who_2005_s02e12_army_of_ghosts.mp4",
    "13_doomsday.mp4": "doctor_who_2005_s02e13_doomsday.mp4",
    "14_the_runaway_bride.mp4": "doctor_who_2005_s03e00_the_runaway_bride_2006_special.mp4",
    "highlander_1x01_the_gathering_1.mp4": "highlander_s01e01_the_gathering.mp4",
    "highlander_2x01_the_watchers_1.mp4": "highlander_s02e01_the_watchers.mp4",
    "highlander_2x04_the_darkness_4.mp4": "highlander_s02e04_the_darkness.mp4",
    "highlander_3x16_methos_16.mp4": "highlander_s03e16_methos.mp4",
    "journeyman_2007_s01e01_a_love_of_a_lifetime_ia.mp4": "journeyman_s01e01_a_love_of_a_lifetime.mp4",
    "life_on_mars_s01e01_dvdrip_pal_plus_commentary_x264_mag.mp4": "life_on_mars_uk_s01e01.mp4",
    "life_on_mars_s01e02_dvdrip_pal_plus_commentary_x264_mag.mp4": "life_on_mars_uk_s01e02.mp4",
    "life_on_mars_s01e03_dvdrip_pal_plus_commentary_x264_mag.mp4": "life_on_mars_uk_s01e03.mp4",
    "life_on_mars_s01e04_dvdrip_pal_plus_commentary_x264_mag.mp4": "life_on_mars_uk_s01e04.mp4",
    "life_on_mars_s01e05_dvdrip_pal_plus_commentary_x264_mag.mp4": "life_on_mars_uk_s01e05.mp4",
    "life_on_mars_s01e06_dvdrip_pal_plus_commentary_x264_mag.mp4": "life_on_mars_uk_s01e06.mp4",
    "life_on_mars_s01e07_dvdrip_pal_plus_commentary_x264_mag.mp4": "life_on_mars_uk_s01e07.mp4",
    "life_on_mars_s01e08_dvdrip_pal_plus_commentary_x264_mag.mp4": "life_on_mars_uk_s01e08.mp4",
    "life_on_mars_s02e01_dvdrip_dd2_0_dd5_1_x264_mag.mp4": "life_on_mars_uk_s02e01.mp4",
    "life_on_mars_s02e02_dvdrip_dd2_0_dd5_1_x264_mag.mp4": "life_on_mars_uk_s02e02.mp4",
    "life_on_mars_s02e03_dvdrip_dd2_0_dd5_1_x264_mag.mp4": "life_on_mars_uk_s02e03.mp4",
    "life_on_mars_s02e04_dvdrip_dd2_0_dd5_1_x264_mag.mp4": "life_on_mars_uk_s02e04.mp4",
    "life_on_mars_s02e05_dvdrip_dd2_0_dd5_1_x264_mag.mp4": "life_on_mars_uk_s02e05.mp4",
    "life_on_mars_s02e06_dvdrip_dd2_0_dd5_1_x264_mag.mp4": "life_on_mars_uk_s02e06.mp4",
    "life_on_mars_s02e07_dvdrip_dd2_0_dd5_1_x264_mag.mp4": "life_on_mars_uk_s02e07.mp4",
    "life_on_mars_s02e08_dvdrip_dd2_0_dd5_1_x264_mag.mp4": "life_on_mars_uk_s02e08.mp4",
    "terminator_the_sarah_connor_chronicles_2008_s02e22_born_to_run_regrade_vc1.mkv": (
        "terminator_the_sarah_connor_chronicles_2008_s02e22_born_to_run.mkv"
    ),
    "terminator_the_sarah_connor_chronicles_2008_s01e01_pilot_regrade_vc1.mkv": (
        "terminator_the_sarah_connor_chronicles_2008_s01e01_pilot.mkv"
    ),
    "terminator_the_sarah_connor_chronicles_2008_s01e02_gnothi_seauton_regrade_vc1.mkv": (
        "terminator_the_sarah_connor_chronicles_2008_s01e02_gnothi_seauton.mkv"
    ),
    "2_netflix_original_movie_enola_holmes_2_2022.mp4": "enola_holmes_2_2022.mp4",
    "weird_science_1985_bluray_x264_yify.mp4": "weird_science_1985.mp4",
    "stranger_things_s01e01_hd.mp4": "stranger_things_s01e01_chapter_one_the_vanishing_of_will_byers.mp4",
    "stranger_things_s01e02_chapter_two_the_weirdo_on_maple_street_5_1ch_webrip_imovieid_video_converter_com.mp4": (
        "stranger_things_s01e02_chapter_two_the_weirdo_on_maple_street.mp4"
    ),
    "stranger_things_s01e05_chapter_five_the_flea_and_the_acrobat_5_1ch_webrip_imovieid_video_converter_com.mp4": (
        "stranger_things_s01e05_chapter_five_the_flea_and_the_acrobat.mp4"
    ),
    "1_the_eleventh_hour.mp4": "doctor_who_2005_s05e01_the_eleventh_hour.mp4",
    "2_the_beast_below.mp4": "doctor_who_2005_s05e02_the_beast_below.mp4",
    "3_victory_of_the_daleks.mp4": "doctor_who_2005_s05e03_victory_of_the_daleks.mp4",
    "4_the_time_of_the_angels.mp4": "doctor_who_2005_s05e04_the_time_of_the_angels.mp4",
    "5_flesh_and_stone.mp4": "doctor_who_2005_s05e05_flesh_and_stone.mp4",
    "6_the_vampires_of_venice.mp4": "doctor_who_2005_s05e06_the_vampires_of_venice.mp4",
    "7_amy_s_choice.mp4": "doctor_who_2005_s05e07_amys_choice.mp4",
    "8_the_hungry_earth.mp4": "doctor_who_2005_s05e08_the_hungry_earth.mp4",
    "9_cold_blood.mp4": "doctor_who_2005_s05e09_cold_blood.mp4",
    "11_the_lodger.mp4": "doctor_who_2005_s05e11_the_lodger.mp4",
    "12_the_pandorica_opens.mp4": "doctor_who_2005_s05e12_the_pandorica_opens.mp4",
    "13_the_big_bang.mp4": "doctor_who_2005_s05e13_the_big_bang.mp4",
}


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _ascii(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def normalize_name(name: str, is_file: bool) -> str:
    suffix = ""
    stem = name
    if is_file:
        path = Path(name)
        suffix = path.suffix.lower()
        stem = path.stem

    cleaned = _ascii(stem).lower()
    cleaned = cleaned.replace("&", " and ")
    cleaned = re.sub(r"\[[^\]]*\]", " ", cleaned)
    for label in DOWNLOAD_LABELS:
        cleaned = cleaned.replace(label, " ")
    for typo, replacement in TYPO_REPLACEMENTS.items():
        cleaned = cleaned.replace(typo, replacement)
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = "untitled"
    cleaned = normalize_media_tokens(cleaned)
    target_name = cleaned + suffix
    return CANONICAL_FILE_NAMES.get(target_name, target_name)


def normalize_media_tokens(stem: str) -> str:
    cleaned = stem.replace("_tv_show_", "_")

    def spaced_episode(match: re.Match[str]) -> str:
        season = int(match.group(1))
        episode = int(match.group(2))
        return f"s{season:02d}e{episode:02d}"

    cleaned = re.sub(r"(?<![a-z0-9])s(\d{1,2})_e(\d{1,2})(?![a-z0-9])", spaced_episode, cleaned)
    cleaned = re.sub(r"(?<![a-z0-9])s(\d{1,2})e(\d{1,2})(?![a-z0-9])", spaced_episode, cleaned)
    return cleaned


def _operation_for(path: Path, library_root: Path) -> dict[str, Any] | None:
    is_file = path.is_file()
    target_name = normalize_name(path.name, is_file=is_file)
    if target_name == path.name:
        return None

    target = path.with_name(target_name)
    issues: list[str] = []
    blocked = False
    same_case_insensitive_path = os.path.normcase(str(path.resolve())) == os.path.normcase(str(target.resolve()))
    if target.exists() and not same_case_insensitive_path:
        blocked = True
        issues.append("target_already_exists")
    if not path.exists():
        blocked = True
        issues.append("source_missing")
    try:
        path.relative_to(library_root)
        target.relative_to(library_root)
    except ValueError:
        blocked = True
        issues.append("outside_library_root")

    return {
        "source": _relative(path),
        "target": _relative(target),
        "item_type": "file" if is_file else "directory",
        "case_only_or_same_path": same_case_insensitive_path,
        "blocked": blocked,
        "issues": issues,
    }


def build_rename_plan(library_root: Path = DEFAULT_LIBRARY_ROOT) -> dict[str, Any]:
    paths = sorted(library_root.rglob("*"), key=lambda item: (len(item.parts), item.as_posix()))
    operations = []
    for path in paths:
        operation = _operation_for(path, library_root)
        if operation is not None:
            operations.append(operation)
    return {
        "plan_id": "media_library_rename_plan_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "library_root": _relative(library_root),
        "operation_count": len(operations),
        "blocked_count": sum(1 for operation in operations if operation["blocked"]),
        "rules": {
            "ascii_snake_case": True,
            "lowercase_extensions": True,
            "removes_obvious_download_labels": True,
            "renames_in_place_only": True,
            "skips_existing_targets": True,
            "refreshes_index_after_apply": True,
        },
        "operations": operations,
    }


def _project_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _remap_path(path: Path, directory_moves: list[tuple[Path, Path]]) -> Path:
    for source_dir, target_dir in directory_moves:
        try:
            suffix = path.relative_to(source_dir)
        except ValueError:
            continue
        path = target_dir / suffix
    return path


def apply_rename_plan(plan: dict[str, Any]) -> dict[str, Any]:
    applied: list[dict[str, str]] = []
    skipped: list[dict[str, Any]] = []
    operations = plan.get("operations", [])
    directory_moves: list[tuple[Path, Path]] = []

    directories = [operation for operation in operations if operation.get("item_type") == "directory"]
    files = [operation for operation in operations if operation.get("item_type") == "file"]

    for operation in [*directories, *files]:
        if operation.get("blocked") is True:
            skipped.append(operation)
            continue
        source = _remap_path(_project_path(str(operation["source"])), directory_moves)
        target = _remap_path(_project_path(str(operation["target"])), directory_moves)
        if not source.exists():
            skipped.append({**operation, "issues": [*operation.get("issues", []), "source_missing_at_apply"]})
            continue
        same_case_insensitive_path = os.path.normcase(str(source.resolve())) == os.path.normcase(str(target.resolve()))
        if target.exists() and not same_case_insensitive_path:
            skipped.append({**operation, "issues": [*operation.get("issues", []), "target_exists_at_apply"]})
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            if same_case_insensitive_path and source.name != target.name:
                temp = source.with_name(f".rename_tmp_{source.name}")
                counter = 1
                while temp.exists():
                    temp = source.with_name(f".rename_tmp_{counter}_{source.name}")
                    counter += 1
                source.rename(temp)
                temp.rename(target)
            else:
                source.rename(target)
        except OSError as exc:
            skipped.append({**operation, "issues": [*operation.get("issues", []), f"rename_failed: {exc}"]})
            continue
        applied.append({"source": operation["source"], "target": operation["target"]})
        if operation.get("item_type") == "directory":
            directory_moves.append((source, target))

    return {
        "applied_count": len(applied),
        "skipped_count": len(skipped),
        "applied": applied,
        "skipped": skipped,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def refresh_indexes(library_root: Path) -> None:
    write_json(DEFAULT_INDEX_PATH, build_index(library_root))
    write_json(DEFAULT_AUDIT_OUTPUT, build_audit(library_root))
    write_json(DEFAULT_UPDATE_CHECK_PATH, check_updates(library_root, DEFAULT_INDEX_PATH))


def run_once(library_root: Path, output: Path, apply: bool, refresh: bool) -> dict[str, Any]:
    plan = build_rename_plan(library_root)
    result: dict[str, Any] = {"apply_requested": apply, "apply_result": None}
    if apply:
        result["apply_result"] = apply_rename_plan(plan)
        if refresh:
            refresh_indexes(library_root)
        plan = build_rename_plan(library_root)
    plan["last_run"] = result
    write_json(output, plan)
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan/apply safe Data/library filename normalization.")
    parser.add_argument("--library-root", default=str(DEFAULT_LIBRARY_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_PLAN_OUTPUT))
    parser.add_argument("--apply", action="store_true", help="Apply planned safe renames.")
    parser.add_argument("--no-refresh", action="store_true", help="Do not rebuild media indexes after apply.")
    parser.add_argument("--watch", action="store_true", help="Poll and rerun when library contents change.")
    parser.add_argument("--interval-seconds", type=int, default=30)
    args = parser.parse_args()

    library_root = Path(args.library_root)
    if not library_root.is_absolute():
        library_root = PROJECT_ROOT / library_root
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output

    if not args.watch:
        plan = run_once(library_root, output, args.apply, not args.no_refresh)
        print(f"Planned {plan['operation_count']} media/library rename operations.")
        print(f"Blocked {plan['blocked_count']} operations.")
        if args.apply and plan.get("last_run", {}).get("apply_result"):
            apply_result = plan["last_run"]["apply_result"]
            print(f"Applied {apply_result['applied_count']} operations; skipped {apply_result['skipped_count']}.")
        print(f"Wrote {_relative(output)}")
        return

    print("Watching media library for rename cleanup. Press Ctrl+C to stop.")
    previous_signature = ""
    while True:
        current_signature = "|".join(
            f"{path.as_posix()}:{path.stat().st_mtime_ns}:{path.stat().st_size if path.is_file() else 0}"
            for path in sorted(library_root.rglob("*"))
        )
        if current_signature != previous_signature:
            plan = run_once(library_root, output, args.apply, not args.no_refresh)
            print(
                f"[{datetime.now().isoformat(timespec='seconds')}] "
                f"planned {plan['operation_count']} operations"
            )
            previous_signature = current_signature
        time.sleep(max(5, args.interval_seconds))


if __name__ == "__main__":
    main()
