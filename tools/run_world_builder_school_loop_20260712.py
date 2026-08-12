"""Lightweight World Builder School loop.

This is for later world-builder training. It does not launch Home World and it
does not generate a 3D map. It writes lesson assignments that can be reviewed
before the World Builder is asked to rebuild places.

Run:
  py tools/run_world_builder_school_loop_20260712.py --duration-hours 2 --cycle-minutes 20
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHOOL_ROOT = PROJECT_ROOT / "Data" / "world_builder" / "school"
ASSIGNMENT_ROOT = SCHOOL_ROOT / "assignments" / "lesson_runs"
SESSION_ROOT = SCHOOL_ROOT / "session_runs"
PRESENCE_DIR = PROJECT_ROOT / "Data" / "presence"
CURRENT_RUN_PATH = PRESENCE_DIR / "current_world_builder_school_run.json"
STOP_PATH = PRESENCE_DIR / "world_builder_school_stop.json"


LESSONS: list[dict[str, Any]] = [
    {
        "lesson_id": "world_source_evidence",
        "title": "Source Evidence Before Building",
        "assignment": [
            "collect maps, photos, blueprints, reference models, and scale notes before building",
            "separate real-world evidence from guessed filler",
            "record which source supports each major facade, room, door, and landmark",
        ],
        "source_dirs": ["Data/world_reconstruction", "Assets/third_party/intake/3d_models_kira_world/environment"],
    },
    {
        "lesson_id": "notebook_world_separation",
        "title": "Notebook Worlds Stay Separate",
        "assignment": [
            "keep Capture the Flag battlefield out of Home World",
            "keep Paris/Louvre/Place des Vosges as notebook worlds reachable through TARDIS/travel",
            "write travel links without merging all worlds into one RAM-heavy map",
        ],
        "source_dirs": ["Data/world_builds/notebook_worlds", "Data/world_design"],
    },
    {
        "lesson_id": "low_ram_world_budget",
        "title": "Low-RAM World Budgeting",
        "assignment": [
            "list heavy objects before loading them",
            "prefer proxies/LODs/collision boxes while training",
            "separate AI mind/voice testing from 3D world testing when RAM is low",
        ],
        "source_dirs": ["Data/world_design", "Logs"],
    },
    {
        "lesson_id": "building_navigation",
        "title": "Doors, Interiors, Stairs, And AI Navigation",
        "assignment": [
            "every enterable building needs door anchors, walkable floors, and clear path targets",
            "world builder should verify doors from outside and inside",
            "AI navigation targets must be named as semantic places, not only coordinates",
        ],
        "source_dirs": ["Data/world_builds", "Assets/third_party/intake/3d_models_kira_world/home_world"],
    },
    {
        "lesson_id": "legal_day_spa_public_business",
        "title": "Legal Day Spa As A Public Wellness Building",
        "assignment": [
            "build the spa as a legitimate public day spa with reception, waiting, posted lawful services, license wall, clean/dirty linen separation, and accessible public routes",
            "avoid illegal-spa signals such as hidden client entrances, unmarked locked service rooms, or secret back corridors",
            "stage the Avatar Builder as a consent-and-preview studio inside the spa, with a reachable talk button and approval screen",
            "do not place the spa in Home World until Robert approves the standalone exterior, interior, doors, collisions, and AI routes",
        ],
        "source_dirs": [
            "Data/world_builder/projects/legal_day_spa_avatar_builder_spa_20260714",
            "Data/world_builds/notebook_worlds/home_world_notebook_world",
            "Data/avatar_builder",
        ],
    },
    {
        "lesson_id": "door_threshold_follow_through",
        "title": "Door Threshold And Follow-Through Validation",
        "assignment": [
            "for every door, create outside approach, handle, opening arc or slide path, inside follow-through, and exit targets",
            "fail any building where a character hits a door, turns around, clips through a wall, or cannot step across the threshold",
            "test doors from both sides and write a nav/collision report before the building can be approved",
            "keep furniture, counters, invisible colliders, and wall pieces clear of the threshold and door swing",
        ],
        "source_dirs": [
            "Data/world_builder/projects/legal_day_spa_avatar_builder_spa_20260714",
            "Data/world_builds",
            "Data/runtime",
        ],
    },
    {
        "lesson_id": "standalone_preview_before_import",
        "title": "Standalone Preview Before Home World Import",
        "assignment": [
            "create new buildings as staged standalone review scenes before importing them into Home World or any notebook world",
            "produce exterior, interior, overhead floor plan, door close-up, and nav/collision contact sheets",
            "write an approval gate that keeps the staged build out of the live world until Robert approves it",
            "if the staged preview is blocky, misaligned, unwalkable, or visually fake, grade it F and rebuild instead of patching it into the live map",
        ],
        "source_dirs": [
            "Data/world_builder/projects/legal_day_spa_avatar_builder_spa_20260714",
            "Data/world_builds/notebook_worlds",
        ],
    },
    {
        "lesson_id": "future_college_campus_relocation",
        "title": "Move Robotics And Programming Into Future School Campus",
        "assignment": [
            "treat the current strip mall robotics and programming shops as temporary placeholders, not final Home World locations",
            "plan robotics, programming, labs, library learning, and classrooms as part of a future small college campus",
            "keep the Home World strip mall rebuild focused on resident-facing places such as spa, cafe, stores, and public services",
            "record migration notes so existing signs, route names, and AI memories can be updated when the campus exists",
        ],
        "source_dirs": [
            "Data/world_design",
            "Data/world_builder/projects/legal_day_spa_avatar_builder_spa_20260714",
            "Data/world_builds",
        ],
    },
    {
        "lesson_id": "materials_and_scale",
        "title": "Realistic Materials And Scale",
        "assignment": [
            "measure scale from known objects before resizing assets",
            "record material references for brick, stone, glass, roads, floors, and signs",
            "do not use dark blurry placeholder media when a specific place/object must be inspected",
        ],
        "source_dirs": ["Assets/third_party/intake/3d_models_kira_world", "Data/world_reconstruction/sources"],
    },
    {
        "lesson_id": "soft_goods_stores_and_world_inventory",
        "title": "Soft Goods, Stores, And World Inventory",
        "assignment": [
            "treat clothes, blankets, towels, bedding, curtains, and loose fabric as world objects when they are stored, sold, folded, hanging, or placed in rooms",
            "design stores with racks, shelves, folded piles, dressing rooms, checkout counters, product tags, and inventory anchors",
            "separate world prop forms from wearable avatar garment forms; Avatar Builder owns fitting, rigging, cloth physics, and dressing/undressing",
            "record handoff anchors where an AI can buy, pick up, fold, hang, wash, or wear a soft-good item",
            "do not load cloth-heavy simulation in low-RAM Home World unless it is a short focused test",
        ],
        "source_dirs": [
            "Data/world_builder/item_prefab_library",
            "Avatar/avatar_builder/wardrobe_training",
            "Avatar/avatar_builder/policies",
        ],
    },
    {
        "lesson_id": "recognizable_without_labels_gate",
        "title": "Recognizable Without Labels Gate",
        "assignment": [
            "render the building exterior, entrance, reception, main service rooms, restrooms, route paths, and key props twice: once with labels and once with every label hidden",
            "grade the unlabeled version first; if Robert would not know what the object or room is without words, the build is an F",
            "replace box placeholders with recognizable shapes, proportions, material cues, trims, fixtures, furniture details, signs, lighting, and scale references",
            "write an object-recognition checklist for each major room and prop before asking for approval",
            "do not place any unlabeled-failed build into Home World or a notebook world",
        ],
        "source_dirs": [
            "Data/world_builder/projects/legal_day_spa_avatar_builder_spa_20260714",
            "Data/world_builder/school/curriculum",
            "Data/world_reconstruction/sources",
        ],
    },
    {
        "lesson_id": "non_blocky_architecture_and_materials",
        "title": "Non-Blocky Architecture And Materials",
        "assignment": [
            "avoid flat boxes with plain colors; use wall thickness, real door frames, windows, trim, baseboards, ceiling details, roof fascia, floor transitions, and rounded/beveled furniture where appropriate",
            "use material references for spa glass, tile, painted drywall, counters, waiting-room seating, treatment tables, towels, plants, lighting, and signage",
            "create exterior and interior mood/reference boards before modeling, then record which detail each reference supports",
            "include close-up review renders for the front door, reception counter, treatment room, Avatar Builder studio, hallway, restroom, and relaxation lounge",
            "fail any build where rooms and props are only understandable from floating labels",
        ],
        "source_dirs": [
            "Data/world_builder/projects/legal_day_spa_avatar_builder_spa_20260714",
            "Assets/third_party/intake/3d_models_kira_world/environment",
            "Data/world_reconstruction/sources",
        ],
    },
    {
        "lesson_id": "walkable_building_collision_gate",
        "title": "Walkable Building Collision Gate",
        "assignment": [
            "build every door with outside approach, threshold, frame, handle, opening motion, inside follow-through target, and exit target",
            "run an avatar-sized route test through the front door, each interior door, the Avatar Builder talk station, and back out again",
            "fail the build if anything behind a door blocks the route, if a wall gap is too narrow, if a character clips through walls, or if a door opens into furniture",
            "produce a route contact sheet and collision report before the staged building can be approved",
            "keep the staged preview separate from Home World until Robert approves the walkable proof",
        ],
        "source_dirs": [
            "Data/world_builder/projects/legal_day_spa_avatar_builder_spa_20260714",
            "Data/runtime",
            "Avatar/movement_library",
        ],
    },
    {
        "lesson_id": "builder_conversation_blueprint_and_search",
        "title": "Builder Conversation, Blueprint, And Search",
        "assignment": [
            "save Robert's design corrections as durable builder memory before rebuilding",
            "when network/search is allowed, gather current public reference images, floor-plan ideas, and code/permit concepts for legal public spas; cite source URLs in the design notes",
            "show blueprint, exterior preview, interior preview, unlabeled render, and route proof before placement approval",
            "support conversational requests such as make the front less blocky, move the door, add a room, or rebuild from a new reference set",
            "never auto-place a new building into an existing world; create a staged TARDIS/review preview and wait for approval",
        ],
        "source_dirs": [
            "Data/world_builder/projects/legal_day_spa_avatar_builder_spa_20260714",
            "Data/world_builder/known_details",
            "Data/world_design",
        ],
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def source_snapshot(source_dirs: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source_dir in source_dirs:
        path = PROJECT_ROOT / source_dir
        if not path.exists():
            rows.append({"path": source_dir, "exists": False, "file_count": 0})
            continue
        files = [item for item in path.rglob("*") if item.is_file()]
        rows.append({
            "path": source_dir,
            "exists": True,
            "file_count": len(files),
            "sample_files": [rel(item) for item in files[:20]],
        })
    return rows


def write_presence(status: str, payload: dict[str, Any]) -> None:
    write_json(CURRENT_RUN_PATH, {
        "schema_version": 1,
        "status": status,
        "updated_at": now_iso(),
        "pid": os.getpid(),
        **payload,
    })


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a lightweight World Builder School loop.")
    parser.add_argument("--duration-hours", type=float, default=2.0)
    parser.add_argument("--cycle-minutes", type=float, default=20.0)
    args = parser.parse_args()

    run_id = f"world_builder_school_loop_{now_id()}"
    run_dir = SESSION_ROOT / run_id
    log_path = run_dir / f"{run_id}.jsonl"
    index_path = ASSIGNMENT_ROOT / run_id / "assignment_index.json"
    stop_started_at = STOP_PATH.stat().st_mtime if STOP_PATH.exists() else None
    started = time.monotonic()
    end_at = started + max(0.05, args.duration_hours) * 3600.0
    cycle_seconds = max(60.0, args.cycle_minutes * 60.0)
    cycle_index = 0
    index = {"schema_version": 1, "run_id": run_id, "assignments": []}

    write_presence("running", {"run_id": run_id, "log_path": rel(log_path), "assignment_index": rel(index_path)})
    append_jsonl(log_path, {"time": now_iso(), "type": "run_start", "run_id": run_id})

    while time.monotonic() < end_at:
        if STOP_PATH.exists() and (stop_started_at is None or STOP_PATH.stat().st_mtime > stop_started_at):
            append_jsonl(log_path, {"time": now_iso(), "type": "stop_requested", "stop_file": rel(STOP_PATH)})
            break
        lesson = LESSONS[cycle_index % len(LESSONS)]
        assignment_path = ASSIGNMENT_ROOT / run_id / f"{cycle_index:03d}_{lesson['lesson_id']}_assignment.json"
        artifact = {
            "schema_version": 1,
            "run_id": run_id,
            "cycle_index": cycle_index,
            "created_at": now_iso(),
            "lesson_id": lesson["lesson_id"],
            "title": lesson["title"],
            "status": "submitted_for_later_review",
            "assignment": lesson["assignment"],
            "source_snapshot": source_snapshot(lesson["source_dirs"]),
            "rule": "World Builder School trains planning/evidence only; it does not load or build a 3D world.",
        }
        write_json(assignment_path, artifact)
        index["updated_at"] = now_iso()
        index["assignments"].append({
            "cycle_index": cycle_index,
            "lesson_id": lesson["lesson_id"],
            "title": lesson["title"],
            "assignment": rel(assignment_path),
        })
        write_json(index_path, index)
        write_presence("running", {
            "run_id": run_id,
            "cycle_index": cycle_index,
            "current_lesson": lesson["lesson_id"],
            "current_lesson_title": lesson["title"],
            "assignment_index": rel(index_path),
            "latest_assignment": rel(assignment_path),
        })
        append_jsonl(log_path, {"time": now_iso(), "type": "lesson_completed", "assignment": rel(assignment_path)})
        cycle_index += 1
        remaining = end_at - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(cycle_seconds, remaining))

    summary = {
        "schema_version": 1,
        "run_id": run_id,
        "finished_at": now_iso(),
        "cycles_completed": cycle_index,
        "assignment_index": rel(index_path),
        "log_path": rel(log_path),
        "status": "completed" if time.monotonic() >= end_at else "stopped",
    }
    write_json(run_dir / f"{run_id}_summary.json", summary)
    write_presence(summary["status"], summary)
    append_jsonl(log_path, {"time": now_iso(), "type": "run_finish", **summary})
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
