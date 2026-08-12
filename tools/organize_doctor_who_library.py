"""
Organize Doctor Who library files into era-safe folders.

Classic Doctor Who and revived Doctor Who reuse season numbers, so keeping
everything in one folder makes chronology ambiguous. This tool moves known
Doctor Who files into era folders without overwriting collisions.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY_ROOT = PROJECT_ROOT / "Data" / "library"
DEFAULT_OUTPUT = PROJECT_ROOT / "Data" / "indexes" / "doctor_who_organize_plan.json"

DOCTOR_WHO_ROOT = Path("tv_shows") / "doctor_who"

KNOWN_MOVES = {
    "1. The Daleks in Colour.mp4": "classic_1963/s01_specials/doctor_who_1963_s01_serial_02_the_daleks_in_colour_2023.mp4",
    "S01E01 - An Unearthly Child.mp4": "classic_1963/s01/doctor_who_1963_s01e01_an_unearthly_child.mp4",
    "doctor_who_s07e01_e04_spearhead_from_space.mp4": "classic_1963/s07/doctor_who_1963_s07e01_e04_spearhead_from_space.mp4",
    "doctor_who_s12e11_e16_genesis_of_the_daleks.mp4": "classic_1963/s12/doctor_who_1963_s12e11_e16_genesis_of_the_daleks.mp4",
    "S20E23 - The Five Doctors.mp4": "classic_1963/s20_specials/doctor_who_1963_s20_special_the_five_doctors_1983.mp4",
    "doctor_who_s00e01_the_star_beast_2023_special.mp4": "revived_2005/specials_2023/doctor_who_2005_s00e01_the_star_beast_2023_special.mp4",
    "doctor_who_2005_s02e00_the_christmas_invasion_2005_special.mp4": "revived_2005/s02_specials/doctor_who_2005_s02e00_the_christmas_invasion_2005_special.mp4",
    "doctor_who_2005_s02e01_new_earth.mp4": "revived_2005/s02/doctor_who_2005_s02e01_new_earth.mp4",
    "doctor_who_2005_s02e02_tooth_and_claw.mp4": "revived_2005/s02/doctor_who_2005_s02e02_tooth_and_claw.mp4",
    "doctor_who_2005_s02e03_school_reunion.mp4": "revived_2005/s02/doctor_who_2005_s02e03_school_reunion.mp4",
    "doctor_who_2005_s02e05_rise_of_the_cybermen.mp4": "revived_2005/s02/doctor_who_2005_s02e05_rise_of_the_cybermen.mp4",
    "doctor_who_2005_s02e06_the_age_of_steel.mp4": "revived_2005/s02/doctor_who_2005_s02e06_the_age_of_steel.mp4",
    "doctor_who_2005_s02e07_the_idiots_lantern.mp4": "revived_2005/s02/doctor_who_2005_s02e07_the_idiots_lantern.mp4",
    "doctor_who_2005_s02e08_the_impossible_planet.mp4": "revived_2005/s02/doctor_who_2005_s02e08_the_impossible_planet.mp4",
    "doctor_who_2005_s02e09_the_satan_pit.mp4": "revived_2005/s02/doctor_who_2005_s02e09_the_satan_pit.mp4",
    "doctor_who_2005_s02e12_army_of_ghosts.mp4": "revived_2005/s02/doctor_who_2005_s02e12_army_of_ghosts.mp4",
    "doctor_who_2005_s02e13_doomsday.mp4": "revived_2005/s02/doctor_who_2005_s02e13_doomsday.mp4",
    "doctor_who_2005_s03e00_the_runaway_bride_2006_special.mp4": "revived_2005/s03_specials/doctor_who_2005_s03e00_the_runaway_bride_2006_special.mp4",
    "doctor_who_2005_s05e01_the_eleventh_hour.mp4": "revived_2005/s05/doctor_who_2005_s05e01_the_eleventh_hour.mp4",
    "doctor_who_2005_s05e02_the_beast_below.mp4": "revived_2005/s05/doctor_who_2005_s05e02_the_beast_below.mp4",
    "doctor_who_2005_s05e03_victory_of_the_daleks.mp4": "revived_2005/s05/doctor_who_2005_s05e03_victory_of_the_daleks.mp4",
    "doctor_who_2005_s05e04_the_time_of_the_angels.mp4": "revived_2005/s05/doctor_who_2005_s05e04_the_time_of_the_angels.mp4",
    "doctor_who_2005_s05e05_flesh_and_stone.mp4": "revived_2005/s05/doctor_who_2005_s05e05_flesh_and_stone.mp4",
    "doctor_who_2005_s05e06_the_vampires_of_venice.mp4": "revived_2005/s05/doctor_who_2005_s05e06_the_vampires_of_venice.mp4",
    "doctor_who_2005_s05e07_amys_choice.mp4": "revived_2005/s05/doctor_who_2005_s05e07_amys_choice.mp4",
    "doctor_who_2005_s05e08_the_hungry_earth.mp4": "revived_2005/s05/doctor_who_2005_s05e08_the_hungry_earth.mp4",
    "doctor_who_2005_s05e09_cold_blood.mp4": "revived_2005/s05/doctor_who_2005_s05e09_cold_blood.mp4",
    "doctor_who_2005_s05e11_the_lodger.mp4": "revived_2005/s05/doctor_who_2005_s05e11_the_lodger.mp4",
    "doctor_who_2005_s05e12_the_pandorica_opens.mp4": "revived_2005/s05/doctor_who_2005_s05e12_the_pandorica_opens.mp4",
    "doctor_who_2005_s05e13_the_big_bang.mp4": "revived_2005/s05/doctor_who_2005_s05e13_the_big_bang.mp4",
    "doctor_who_children_in_need_special_time_crash_2007.mp4": "revived_2005/mini_episodes/doctor_who_2005_mini_2007_time_crash_children_in_need.mp4",
    "doctor_who_time_part_one_red_nose_day_2011_bbc_comic_relief_night.mp4": "revived_2005/mini_episodes/doctor_who_2005_mini_2011_time_part_01_red_nose_day.mp4",
    "doctor_who_time_part_two_red_nose_day_2011_bbc_comic_relief_night.mp4": "revived_2005/mini_episodes/doctor_who_2005_mini_2011_time_part_02_red_nose_day.mp4",
}


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def build_plan(library_root: Path = DEFAULT_LIBRARY_ROOT) -> dict[str, Any]:
    doctor_root = library_root / DOCTOR_WHO_ROOT
    operations = []
    skipped = []
    if not doctor_root.exists():
        return {
            "plan_id": "doctor_who_era_organize_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "doctor_who_root": _relative(doctor_root),
            "operation_count": 0,
            "skipped_count": 1,
            "operations": [],
            "skipped": [{"path": _relative(doctor_root), "issues": ["doctor_who_root_missing"]}],
        }

    for source_name, target_relative in KNOWN_MOVES.items():
        source = doctor_root / source_name
        target = doctor_root / target_relative
        if not source.exists():
            existing_target = target.exists()
            skipped.append(
                {
                    "source": _relative(source),
                    "target": _relative(target),
                    "issues": ["source_missing_already_moved" if existing_target else "source_missing"],
                }
            )
            continue
        blocked = target.exists()
        operations.append(
            {
                "source": _relative(source),
                "target": _relative(target),
                "blocked": blocked,
                "issues": ["target_exists"] if blocked else [],
            }
        )

    return {
        "plan_id": "doctor_who_era_organize_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "doctor_who_root": _relative(doctor_root),
        "rules": {
            "classic_and_revived_are_separate": True,
            "does_not_overwrite": True,
            "classic_files_use_doctor_who_1963_prefix": True,
            "revived_files_use_doctor_who_2005_prefix": True,
        },
        "operation_count": len(operations),
        "blocked_count": sum(1 for operation in operations if operation["blocked"]),
        "skipped_count": len(skipped),
        "operations": operations,
        "skipped": skipped,
    }


def apply_plan(plan: dict[str, Any]) -> dict[str, Any]:
    moved = []
    skipped = []
    for operation in plan.get("operations", []):
        if operation.get("blocked"):
            skipped.append(operation)
            continue
        source = PROJECT_ROOT / operation["source"]
        target = PROJECT_ROOT / operation["target"]
        if not source.exists():
            skipped.append({**operation, "issues": [*operation.get("issues", []), "source_missing"]})
            continue
        if target.exists():
            skipped.append({**operation, "issues": [*operation.get("issues", []), "target_exists"]})
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        moved.append({"source": operation["source"], "target": operation["target"]})
    return {"moved_count": len(moved), "skipped_count": len(skipped), "moved": moved, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description="Organize Doctor Who into Classic/Revived era folders.")
    parser.add_argument("--library-root", default=str(DEFAULT_LIBRARY_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    library_root = Path(args.library_root)
    if not library_root.is_absolute():
        library_root = PROJECT_ROOT / library_root
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output

    plan = build_plan(library_root)
    if args.apply:
        plan["last_run"] = {"apply_requested": True, "apply_result": apply_plan(plan)}
        plan = build_plan(library_root) | {"last_run": plan["last_run"]}
    else:
        plan["last_run"] = {"apply_requested": False, "apply_result": None}

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Doctor Who operations: {plan['operation_count']}")
    print(f"Doctor Who blocked: {plan.get('blocked_count', 0)}")
    print(f"Doctor Who skipped: {plan['skipped_count']}")
    if args.apply:
        result = plan["last_run"]["apply_result"]
        print(f"Moved {result['moved_count']}; skipped {result['skipped_count']}.")
    print(f"Wrote {_relative(output)}")


if __name__ == "__main__":
    main()
