"""Build a staged legal day-spa preview for World Builder review.

This creates a standalone 3D review scene and reports. It does not import the
spa into Home World.
"""

from __future__ import annotations

import json
import heapq
import hashlib
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "legal_day_spa_avatar_builder_spa_20260714"
PROJECT_DIR = ROOT / "Data" / "world_builder" / "projects" / PROJECT_ID
PREVIEW_ROOT = PROJECT_DIR / "preview_builds"
THREE_MODULE_URL = (
    "/Data/world_builds/notebook_worlds/home_world/builds/"
    "home_world_main_house_20260630_223000/preview/node_modules/three/build/three.module.js"
)
THREE_ADDONS_URL = (
    "/Data/world_builds/notebook_worlds/home_world/builds/"
    "home_world_main_house_20260630_223000/preview/node_modules/three/examples/jsm/"
)

ITEM_PREFAB_LIBRARY_PATH = ROOT / "Data" / "world_builder" / "item_prefab_library" / "item_prefab_library.json"
COMPONENT_LIBRARY_PATH = ROOT / "Data" / "world_builder" / "item_prefab_library" / "component_library.json"

INDEXED_REAL_PREFAB_REQUESTS: tuple[dict[str, Any], ...] = (
    {
        "role": "waiting_sofa",
        "requested_tags": ["couch"],
        "prefab_id": "f00b1adbfa11_source_bundle",
        "expected_source": "staged_assets_for_world_builder/desktop_3d_models/some more 3d/modern_sofa (1).glb",
        "expected_sha256": "6e83a399496811d0da3e07afe4ef67881e25e153fcc5a7b60729f3ae2a9a73e0",
        "author": "NatureAssets3D",
        "source_page": "https://sketchfab.com/3d-models/modern-sofa-ae722994457b42b4a34aa7cddbb39f70",
        "author_page": "https://sketchfab.com/super-valentin",
        "reason": "A real indexed sofa is appropriate for the public waiting area.",
    },
    {
        "role": "consultation_chair",
        "requested_tags": ["chair"],
        "prefab_id": "6ec16398846f_source_bundle",
        "expected_source": "staged_assets_for_world_builder/desktop_beds_models/leather_office_chair_-_low_polygon__game_ready.glb",
        "expected_sha256": "e8693801cb6b3ee33b3a547003c845876a73c1b85fb6f53a7c953fb6c3f77447",
        "author": "murattd3v",
        "source_page": "https://sketchfab.com/3d-models/leather-office-chair-low-polygon-game-ready-aee7ef0361b848d6b66bd3588fc2190c",
        "author_page": "https://sketchfab.com/murattd3v",
        "reason": "The office chair is suitable for consultation seating, never as a salon chair.",
    },
    {
        "role": "restroom_toilet",
        "requested_tags": ["toilet", "bathroom_fixture"],
        "prefab_id": "fca3ad56d799_source_bundle",
        "expected_source": "staged_assets_for_world_builder/desktop_3d_models/3D Models Kira World/Rigged Toilet/toilet_002_rigged.glb",
        "expected_sha256": "402dd56ee1cc0d976ba8af5e648c0a6da20cf47cf423a71afffbce38dde97989",
        "author": "photon (that one larry)",
        "source_page": "https://sketchfab.com/3d-models/toilet-002-rigged-14b3f0f8c85c4bcd9e65a96c0afea77f",
        "author_page": "https://sketchfab.com/Professor_E12",
        "reason": "A real indexed toilet is appropriate for the accessible-restroom draft.",
    },
)

CONTROLLED_PROJECT_PREFAB_DESCRIPTORS: tuple[dict[str, Any], ...] = (
    {
        "role": "restroom_sink_cabinet",
        "requested_tags": ["sink", "cabinet", "bathroom_fixture"],
        "prefab_id": "project_local:bathroom_sink_cabinet_light:b86e54e60e39",
        "source": "Data/world_builder/staged_assets_for_world_builder/desktop_a_bunch_more/bathroom_sink_cabinet (1).glb",
        "expected_sha256": "b86e54e60e392ff7b268f891829080d7e791be7c382e3f5746a9f5c289affed3",
        "author": "jimbogies",
        "source_page": "https://sketchfab.com/3d-models/bathroom-sink-cabinet-e5cf10304ffb4c11bc7841b584ccd706",
        "author_page": "https://sketchfab.com/jimbogies",
        "reason": "Recent licensed sink/vanity candidate is semantically correct for the restroom.",
    },
    {
        "role": "waiting_coffee_table",
        "requested_tags": ["coffee_table", "table"],
        "prefab_id": "project_local:low_height_coffee_table_light:b35b7d91f37d",
        "source": "Data/world_builder/staged_assets_for_world_builder/desktop_a_bunch_more/low_height_coffee_table (1).glb",
        "expected_sha256": "b35b7d91f37d43f7e9edabb7556dd066a01915e12314f0598e6e0c7cc119d611",
        "author": "Sapizon",
        "source_page": "https://sketchfab.com/3d-models/low-height-coffee-table-a8f02de4e002418b94fc1371882b67f3",
        "author_page": "https://sketchfab.com/sapizon",
        "reason": "A real low coffee table is suitable only for the waiting area.",
    },
)

UNRESOLVED_REAL_ASSET_ROLES: tuple[dict[str, str], ...] = (
    {"role": "front_storefront_door", "reason": "The indexed single wood door does not satisfy the approved double-glass storefront requirement."},
    {"role": "reception_counter", "reason": "No acceptable real reception counter prefab was found."},
    {"role": "consultation_desk_tablet", "reason": "A coffee table is not a consultation desk and no suitable real desk/tablet set was found."},
    {"role": "treatment_table_a", "reason": "No massage/treatment-table prefab was found; a bed must not be relabelled."},
    {"role": "treatment_table_b", "reason": "No massage/treatment-table prefab was found; a bed must not be relabelled."},
    {"role": "treatment_room_stools", "reason": "No appropriate treatment stool prefab was found."},
    {"role": "treatment_side_counters_and_sinks", "reason": "No reviewed treatment-room counter/sink set was found."},
    {"role": "styling_salon_chair", "reason": "An office chair is not a salon chair and no salon-chair prefab was found."},
    {"role": "styling_shampoo_basin", "reason": "No reviewed shampoo-basin prefab was found."},
    {"role": "styling_mirror", "reason": "No reviewed styling-station mirror prefab was found."},
    {"role": "relaxation_lounges", "reason": "A sofa is not a relaxation chaise and no appropriate lounge prefab was found."},
    {"role": "clean_towel_storage", "reason": "A bookshelf must not be relabelled as clean-towel storage."},
    {"role": "dirty_linen_hamper", "reason": "No appropriate hamper prefab was found."},
    {"role": "laundry_machines", "reason": "No reviewed washer/dryer prefab was found."},
    {"role": "staff_utility_sink", "reason": "The public restroom vanity must not be duplicated as a utility sink."},
    {"role": "accessible_grab_rails", "reason": "No reviewed accessible grab-rail prefab was found."},
    {"role": "spa_ceiling_light_fixtures", "reason": "Current light candidates are not appropriate spa ceiling fixtures."},
)

LICENSE_ID = "CC-BY-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"

AVATAR_RADIUS_METERS = 0.34
PATH_GRID_METERS = 0.10
DOOR_APPROACH_DISTANCE_METERS = 0.90
DOOR_LEAF_THICKNESS_METERS = 0.08
STATIC_PATH_BOUNDS = (-13.0, 13.0, -11.5, 10.0)


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _root_relative_url(source: str) -> str:
    return "/" + source.replace("\\", "/").lstrip("/")


def _library_source_path(source: str) -> Path:
    return ROOT / "Data" / "world_builder" / Path(source)


def _component_candidates(component_library: dict[str, Any], requested_tags: list[str]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    groups = component_library.get("groups") or {}
    for tag in requested_tags:
        group = groups.get(tag) or {}
        for row in group.get("recommended") or []:
            if isinstance(row, dict) and row.get("id") not in {item.get("id") for item in candidates}:
                candidates.append(row)
    return candidates


def build_asset_selection_report() -> dict[str, Any]:
    """Query the current libraries first, then make explicit real-or-missing selections."""

    component_library = _read_json_dict(COMPONENT_LIBRARY_PATH)
    item_library = _read_json_dict(ITEM_PREFAB_LIBRARY_PATH)
    all_prefabs = [row for row in item_library.get("prefabs") or [] if isinstance(row, dict)]
    queries: list[dict[str, Any]] = []
    selections: list[dict[str, Any]] = []

    for request in INDEXED_REAL_PREFAB_REQUESTS:
        component_candidates = _component_candidates(component_library, request["requested_tags"])
        item_candidates = [
            row for row in all_prefabs
            if request["prefab_id"] == row.get("id")
            or request["expected_source"] == row.get("source")
        ]
        selected = next((row for row in item_candidates if row.get("id") == request["prefab_id"]), None)
        queries.append({
            "role": request["role"],
            "requested_tags": request["requested_tags"],
            "query_order": ["component_library", "item_prefab_library"],
            "component_candidate_ids": [row.get("id") for row in component_candidates[:20]],
            "component_candidate_count": len(component_candidates),
            "item_candidate_ids": [row.get("id") for row in item_candidates[:20]],
            "item_candidate_count": len(item_candidates),
            "requested_prefab_id": request["prefab_id"],
        })

        source = selected.get("source") if selected else request["expected_source"]
        source_path = _library_source_path(source)
        actual_sha = _sha256(source_path) if source_path.is_file() else None
        failures: list[str] = []
        if selected is None:
            failures.append("prefab_id_not_found_in_current_item_library")
        if selected and source != request["expected_source"]:
            failures.append("selected_prefab_source_changed")
        if not source_path.is_file():
            failures.append("selected_source_file_missing")
        if actual_sha and actual_sha != request["expected_sha256"]:
            failures.append("selected_source_sha256_changed")
        selections.append({
            "role": request["role"],
            "status": "selected_real_prefab" if not failures else "failed_missing_real_prefab",
            "render_mode": "real_prefab",
            "selection_stage": "item_prefab_library_after_component_query",
            "requested_tags": request["requested_tags"],
            "prefab_id": request["prefab_id"] if selected else None,
            "prefab_kind": selected.get("kind") if selected else None,
            "node_name": selected.get("nodeName") if selected else None,
            "source": f"Data/world_builder/{source}",
            "source_url": _root_relative_url(f"Data/world_builder/{source}"),
            "source_sha256": actual_sha,
            "expected_sha256": request["expected_sha256"],
            "license": LICENSE_ID,
            "license_url": LICENSE_URL,
            "author": request["author"],
            "author_page": request["author_page"],
            "source_page": request["source_page"],
            "selection_reason": request["reason"],
            "no_block_fallback": True,
            "load_failure_status": "failed_missing_real_prefab",
            "failures": failures,
        })

    for descriptor in CONTROLLED_PROJECT_PREFAB_DESCRIPTORS:
        component_candidates = _component_candidates(component_library, descriptor["requested_tags"])
        item_candidates = [
            row for row in all_prefabs
            if descriptor["source"].endswith(str(row.get("source", "")))
            or Path(str(row.get("sourceFile", ""))).name == Path(descriptor["source"]).name
        ]
        queries.append({
            "role": descriptor["role"],
            "requested_tags": descriptor["requested_tags"],
            "query_order": ["component_library", "item_prefab_library", "controlled_project_descriptor"],
            "component_candidate_ids": [row.get("id") for row in component_candidates[:20]],
            "component_candidate_count": len(component_candidates),
            "item_candidate_ids": [row.get("id") for row in item_candidates[:20]],
            "item_candidate_count": len(item_candidates),
            "requested_prefab_id": descriptor["prefab_id"],
            "current_library_result": "recent_candidate_not_indexed" if not item_candidates else "matching_filename_found",
        })
        source_path = ROOT / descriptor["source"]
        actual_sha = _sha256(source_path) if source_path.is_file() else None
        failures: list[str] = []
        if not source_path.is_file():
            failures.append("controlled_source_file_missing")
        if actual_sha and actual_sha != descriptor["expected_sha256"]:
            failures.append("controlled_source_sha256_changed")
        selections.append({
            "role": descriptor["role"],
            "status": "selected_real_prefab" if not failures else "failed_missing_real_prefab",
            "render_mode": "real_prefab",
            "selection_stage": "controlled_project_descriptor_after_current_library_query",
            "requested_tags": descriptor["requested_tags"],
            "prefab_id": descriptor["prefab_id"] if not failures else None,
            "prefab_kind": "controlled_project_source_bundle",
            "node_name": None,
            "source": descriptor["source"],
            "source_url": _root_relative_url(descriptor["source"]),
            "source_sha256": actual_sha,
            "expected_sha256": descriptor["expected_sha256"],
            "license": LICENSE_ID,
            "license_url": LICENSE_URL,
            "author": descriptor["author"],
            "author_page": descriptor["author_page"],
            "source_page": descriptor["source_page"],
            "selection_reason": descriptor["reason"],
            "global_library_refresh_avoided_because": (
                "The current structural repair is under test; the global builder deletes and recreates all per-prefab "
                "descriptors. This exact SHA-pinned project descriptor avoids an unrelated bulk rewrite."
            ),
            "no_block_fallback": True,
            "load_failure_status": "failed_missing_real_prefab",
            "failures": failures,
        })

    missing = [
        {
            "role": row["role"],
            "status": "failed_missing_real_prefab",
            "visual_created": False,
            "source": None,
            "prefab_id": None,
            "reason": row["reason"],
            "block_fallback_allowed": False,
        }
        for row in UNRESOLVED_REAL_ASSET_ROLES
    ]
    selected_count = sum(row["status"] == "selected_real_prefab" for row in selections)
    return {
        "schema_version": 1,
        "project_id": PROJECT_ID,
        "created_at": now_iso(),
        "status": "real_prefabs_selected_with_unresolved_required_assets",
        "library_query": {
            "query_order": ["component_library", "item_prefab_library", "controlled_project_descriptor_if_unindexed"],
            "component_library": {
                "path": rel(COMPONENT_LIBRARY_PATH),
                "generated_at": component_library.get("generatedAt"),
                "source_count": component_library.get("sourceCount"),
                "prefab_count": component_library.get("prefabCount"),
            },
            "item_prefab_library": {
                "path": rel(ITEM_PREFAB_LIBRARY_PATH),
                "generated_at": item_library.get("generatedAt"),
                "source_count": item_library.get("sourceCount"),
                "prefab_count": item_library.get("prefabCount"),
                "error_count": item_library.get("errorCount"),
            },
            "queries": queries,
        },
        "selections": selections,
        "selected_count": selected_count,
        "failed_selection_count": len(selections) - selected_count,
        "missing_asset_roles": missing,
        "missing_asset_count": len(missing),
        "forbidden_substitutions": [
            "office chair as salon chair",
            "coffee table as consultation desk or reception counter",
            "bed as treatment table",
            "sofa as relaxation chaise",
            "bookshelf as towel storage",
        ],
        "home_world_modified": False,
    }


def asset_credits(selection_report: dict[str, Any]) -> dict[str, Any]:
    by_sha: dict[str, dict[str, Any]] = {}
    for row in selection_report["selections"]:
        if row["status"] != "selected_real_prefab" or not row.get("source_sha256"):
            continue
        sha = row["source_sha256"]
        entry = by_sha.setdefault(sha, {
            "source_sha256": sha,
            "local_source": row["source"],
            "source_url": row["source_page"],
            "author": row["author"],
            "author_url": row["author_page"],
            "license": row["license"],
            "license_url": row["license_url"],
            "requirements": "Credit the author and source wherever this preview or a derivative is shared.",
            "roles": [],
            "prefab_ids": [],
        })
        if row["role"] not in entry["roles"]:
            entry["roles"].append(row["role"])
        if row.get("prefab_id") and row["prefab_id"] not in entry["prefab_ids"]:
            entry["prefab_ids"].append(row["prefab_id"])
    return {
        "schema_version": 1,
        "project_id": PROJECT_ID,
        "created_at": now_iso(),
        "license_policy": "Preserve attribution for all CC-BY-4.0 assets in private builds and any shared derivative.",
        "credits": list(by_sha.values()),
        "home_world_modified": False,
    }


def missing_asset_report(selection_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "project_id": PROJECT_ID,
        "created_at": now_iso(),
        "status": "failed_missing_real_prefabs_visual_gate_unresolved",
        "missing_assets": selection_report["missing_asset_roles"],
        "forbidden_substitutions": selection_report["forbidden_substitutions"],
        "visual_gate_passed": False,
        "approval_ready": False,
        "important_truth": "Missing required objects remain empty in the render. Reserved static planning proxies are not visible objects and do not claim an asset exists.",
    }


def room(
    room_id: str,
    label: str,
    x: float,
    z: float,
    w: float,
    d: float,
    color: str,
    *,
    public: bool = True,
) -> dict[str, Any]:
    return {
        "id": room_id,
        "label": label,
        "x": x,
        "z": z,
        "w": w,
        "d": d,
        "color": color,
        "public": public,
    }


def box(
    name: str,
    kind: str,
    x: float,
    y: float,
    z: float,
    w: float,
    h: float,
    d: float,
    color: str,
    *,
    solid: bool = True,
    wall_run_id: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "kind": kind,
        "x": x,
        "y": y,
        "z": z,
        "w": w,
        "h": h,
        "d": d,
        "color": color,
        "solid": solid,
        "wall_run_id": wall_run_id,
    }


def collision_proxy(
    proxy_id: str,
    asset_role: str,
    x: float,
    z: float,
    width: float,
    depth: float,
    *,
    status: str,
    height: float = 1.0,
) -> dict[str, Any]:
    row = box(proxy_id, "collision_proxy", x, height / 2, z, width, height, depth, "#000000")
    row.update({
        "asset_role": asset_role,
        "asset_status": status,
        "visual": False,
        "render_mode": "never_render_static_validation_only",
    })
    return row


def target(
    target_id: str,
    label: str,
    x: float,
    z: float,
    room_id: str,
    *,
    kind: str = "interaction_approach",
    show_label: bool = True,
    linked_asset_role: str | None = None,
    linked_asset_status: str = "available",
) -> dict[str, Any]:
    return {
        "id": target_id,
        "label": label,
        "x": x,
        "y": 0.08,
        "z": z,
        "room": room_id,
        "kind": kind,
        "requires_clearance": True,
        "show_label": show_label,
        "linked_asset_role": linked_asset_role,
        "linked_asset_status": linked_asset_status,
    }


def door(
    door_id: str,
    label: str,
    x: float,
    z: float,
    width: float,
    orientation: str,
    wall_run_id: str,
    from_room: str,
    to_room: str,
    *,
    from_normal_sign: int,
    open_angle_degrees: float = 90.0,
) -> dict[str, Any]:
    if orientation not in {"along_x", "along_z"}:
        raise ValueError(f"unsupported door orientation: {orientation}")
    if from_normal_sign not in {-1, 1}:
        raise ValueError("from_normal_sign must be -1 or 1")
    return {
        "id": door_id,
        "label": label,
        "x": x,
        "z": z,
        "width": width,
        "orientation": orientation,
        "wall_run_id": wall_run_id,
        "from_room": from_room,
        "to_room": to_room,
        "from_normal_sign": from_normal_sign,
        "from_target": f"{door_id}_from_approach",
        "to_target": f"{door_id}_to_followthrough",
        "open_angle_degrees": open_angle_degrees,
        "status": "requires_computed_threshold_validation",
    }


def wall_run(
    wall_run_id: str,
    orientation: str,
    fixed: float,
    start: float,
    end: float,
    *,
    openings: list[str] | None = None,
    height: float = 2.9,
    thickness: float = 0.18,
    color: str = "#e8e8df",
) -> dict[str, Any]:
    if orientation not in {"along_x", "along_z"}:
        raise ValueError(f"unsupported wall orientation: {orientation}")
    if end <= start:
        raise ValueError(f"wall run {wall_run_id} end must be after start")
    return {
        "id": wall_run_id,
        "orientation": orientation,
        "fixed": fixed,
        "start": start,
        "end": end,
        "openings": list(openings or []),
        "height": height,
        "thickness": thickness,
        "color": color,
    }


def derive_wall_geometry(wall_runs: list[dict[str, Any]], doors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Split canonical wall runs around their declared door apertures."""

    door_by_id = {item["id"]: item for item in doors}
    walls: list[dict[str, Any]] = []
    for run in wall_runs:
        intervals: list[tuple[float, float, str]] = []
        for door_id in run["openings"]:
            if door_id not in door_by_id:
                raise ValueError(f"wall run {run['id']} references missing door {door_id}")
            item = door_by_id[door_id]
            if item["wall_run_id"] != run["id"]:
                raise ValueError(f"door {door_id} points at {item['wall_run_id']} instead of {run['id']}")
            if item["orientation"] != run["orientation"]:
                raise ValueError(f"door {door_id} orientation does not match wall run {run['id']}")
            fixed_value = item["z"] if run["orientation"] == "along_x" else item["x"]
            if not math.isclose(fixed_value, run["fixed"], abs_tol=1e-6):
                raise ValueError(f"door {door_id} is not aligned to wall run {run['id']}")
            center = item["x"] if run["orientation"] == "along_x" else item["z"]
            aperture_start = center - item["width"] / 2
            aperture_end = center + item["width"] / 2
            if aperture_start < run["start"] - 1e-6 or aperture_end > run["end"] + 1e-6:
                raise ValueError(f"door {door_id} falls outside wall run {run['id']}")
            intervals.append((aperture_start, aperture_end, door_id))

        intervals.sort()
        cursor = run["start"]
        segment_index = 0
        for aperture_start, aperture_end, door_id in intervals:
            if aperture_start < cursor - 1e-6:
                raise ValueError(f"overlapping door apertures in wall run {run['id']} near {door_id}")
            if aperture_start - cursor > 1e-6:
                walls.append(_wall_segment_box(run, cursor, aperture_start, segment_index))
                segment_index += 1
            cursor = aperture_end
        if run["end"] - cursor > 1e-6:
            walls.append(_wall_segment_box(run, cursor, run["end"], segment_index))
    return walls


def _wall_segment_box(run: dict[str, Any], start: float, end: float, segment_index: int) -> dict[str, Any]:
    length = end - start
    center = (start + end) / 2
    if run["orientation"] == "along_x":
        x, z, width, depth = center, run["fixed"], length, run["thickness"]
    else:
        x, z, width, depth = run["fixed"], center, run["thickness"], length
    return box(
        f"{run['id']}_segment_{segment_index}",
        "wall",
        x,
        run["height"] / 2,
        z,
        width,
        run["height"],
        depth,
        run["color"],
        wall_run_id=run["id"],
    )


def door_anchor_targets(doors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in doors:
        if item["orientation"] == "along_x":
            nx, nz = 0.0, 1.0
        else:
            nx, nz = 1.0, 0.0
        sign = item["from_normal_sign"]
        from_x = item["x"] + nx * sign * DOOR_APPROACH_DISTANCE_METERS
        from_z = item["z"] + nz * sign * DOOR_APPROACH_DISTANCE_METERS
        to_x = item["x"] - nx * sign * DOOR_APPROACH_DISTANCE_METERS
        to_z = item["z"] - nz * sign * DOOR_APPROACH_DISTANCE_METERS
        rows.append(target(
            item["from_target"],
            f"{item['label']} outside approach",
            from_x,
            from_z,
            item["from_room"],
            kind="door_approach",
            show_label=False,
        ))
        rows.append(target(
            item["to_target"],
            f"{item['label']} inside follow-through",
            to_x,
            to_z,
            item["to_room"],
            kind="door_followthrough",
            show_label=False,
        ))
    return rows


def build_asset_instances(selection_report: dict[str, Any]) -> list[dict[str, Any]]:
    selected = {
        row["role"]: row
        for row in selection_report["selections"]
        if row["status"] == "selected_real_prefab"
    }
    placements = [
        {
            "id": "waiting_sofa_real",
            "role": "waiting_sofa",
            "x": -3.5,
            "y": 0.08,
            "z": -6.8,
            "yaw_degrees": 0,
            "fit": {"max_width": 2.7, "max_height": 0.95, "max_depth": 0.95},
            "collision_proxy_id": "waiting_sofa_collision",
        },
        {
            "id": "consultation_chair_left_real",
            "role": "consultation_chair",
            "x": 3.35,
            "y": 0.08,
            "z": -5.85,
            "yaw_degrees": 90,
            "fit": {"max_width": 0.78, "max_height": 1.1, "max_depth": 0.78},
            "collision_proxy_id": "consultation_chair_left_collision",
        },
        {
            "id": "consultation_chair_right_real",
            "role": "consultation_chair",
            "x": 5.05,
            "y": 0.08,
            "z": -5.85,
            "yaw_degrees": -90,
            "fit": {"max_width": 0.78, "max_height": 1.1, "max_depth": 0.78},
            "collision_proxy_id": "consultation_chair_right_collision",
        },
        {
            "id": "restroom_toilet_real",
            "role": "restroom_toilet",
            "x": 10.35,
            "y": 0.08,
            "z": -6.65,
            "yaw_degrees": 180,
            "fit": {"max_width": 0.78, "max_height": 0.95, "max_depth": 1.0},
            "collision_proxy_id": "restroom_toilet_collision",
        },
        {
            "id": "restroom_sink_cabinet_real",
            "role": "restroom_sink_cabinet",
            "x": 8.35,
            "y": 0.08,
            "z": -7.10,
            "yaw_degrees": 0,
            "fit": {"max_width": 1.15, "max_height": 0.95, "max_depth": 0.58},
            "collision_proxy_id": "restroom_sink_cabinet_collision",
        },
        {
            "id": "waiting_coffee_table_real",
            "role": "waiting_coffee_table",
            "x": -5.15,
            "y": 0.08,
            "z": -5.15,
            "yaw_degrees": 0,
            "fit": {"max_width": 1.2, "max_height": 0.45, "max_depth": 0.72},
            "collision_proxy_id": "waiting_coffee_table_collision",
        },
    ]
    instances: list[dict[str, Any]] = []
    for placement in placements:
        source = selected.get(placement["role"])
        if not source:
            continue
        instance = dict(placement)
        instance.update({
            "status": "selected_real_prefab",
            "render_mode": "real_prefab",
            "solid": False,
            "source": source["source"],
            "source_url": source["source_url"],
            "source_sha256": source["source_sha256"],
            "prefab_id": source["prefab_id"],
            "selector": {"kind": "scene_root"},
            "uniform_box3_fit": True,
            "bottom_align": True,
            "no_block_fallback": True,
            "load_failure_status": "failed_missing_real_prefab",
        })
        instances.append(instance)
    return instances


def build_collision_proxies() -> list[dict[str, Any]]:
    selected = "selected_real_prefab"
    missing = "failed_missing_real_prefab_reserved_footprint"
    return [
        collision_proxy("waiting_sofa_collision", "waiting_sofa", -3.5, -6.8, 2.7, 0.9, status=selected, height=0.9),
        collision_proxy("consultation_chair_left_collision", "consultation_chair", 3.35, -5.85, 0.72, 0.72, status=selected, height=1.1),
        collision_proxy("consultation_chair_right_collision", "consultation_chair", 5.05, -5.85, 0.72, 0.72, status=selected, height=1.1),
        collision_proxy("restroom_toilet_collision", "restroom_toilet", 10.35, -6.65, 0.72, 0.92, status=selected, height=0.95),
        collision_proxy("restroom_sink_cabinet_collision", "restroom_sink_cabinet", 8.35, -7.10, 1.10, 0.52, status=selected, height=0.95),
        collision_proxy("waiting_coffee_table_collision", "waiting_coffee_table", -5.15, -5.15, 1.15, 0.68, status=selected, height=0.45),
        collision_proxy("reception_counter_reserved_collision", "reception_counter", -7.2, -6.6, 3.4, 0.8, status=missing, height=1.1),
        collision_proxy("consultation_desk_reserved_collision", "consultation_desk_tablet", 4.2, -6.0, 1.5, 1.1, status=missing, height=0.9),
        collision_proxy("avatar_scanner_collision", "avatar_scanner", -8.3, 0.8, 2.4, 0.18, status="purpose_built_code_native", height=2.7),
        collision_proxy("avatar_talk_button_collision", "avatar_talk_button", -10.4, -0.4, 0.45, 0.45, status="purpose_built_code_native", height=0.8),
        collision_proxy("treatment_table_a_reserved_collision", "treatment_table_a", 3.1, 0.2, 2.2, 0.9, status=missing, height=0.55),
        collision_proxy("treatment_table_b_reserved_collision", "treatment_table_b", 7.9, 0.2, 2.2, 0.9, status=missing, height=0.55),
        collision_proxy("styling_chair_reserved_collision", "styling_salon_chair", -8.9, 6.1, 0.8, 0.8, status=missing, height=0.9),
        collision_proxy("relax_lounge_1_reserved_collision", "relaxation_lounges", -4.0, 6.3, 1.7, 0.8, status=missing, height=0.45),
        collision_proxy("relax_lounge_2_reserved_collision", "relaxation_lounges", -1.4, 6.3, 1.7, 0.8, status=missing, height=0.45),
        collision_proxy("clean_towel_storage_reserved_collision", "clean_towel_storage", 2.1, 8.55, 2.3, 0.3, status=missing, height=2.0),
        collision_proxy("dirty_linen_hamper_reserved_collision", "dirty_linen_hamper", 5.6, 8.0, 0.75, 0.75, status=missing, height=0.9),
    ]


def build_code_native_fixtures() -> list[dict[str, Any]]:
    return [
        {
            "id": "license_services_wall",
            "role": "legal_service_signage",
            "geometry": "framed_canvas_sign",
            "x": -9.8,
            "y": 1.45,
            "z": -8.94,
            "yaw_degrees": 0,
            "title": "LICENSED PUBLIC WELLNESS SERVICES",
            "lines": ["Massage therapy", "Facial + skin care", "Hair styling", "Avatar consultation"],
            "status": "purpose_built_code_native",
        },
        {
            "id": "avatar_scanner_ring",
            "role": "avatar_scanner",
            "geometry": "torus_scanner_ring",
            "x": -8.3,
            "y": 1.35,
            "z": 0.8,
            "radius": 1.15,
            "tube": 0.08,
            "status": "purpose_built_code_native",
        },
        {
            "id": "avatar_approval_screen",
            "role": "avatar_approval_screen",
            "geometry": "framed_emissive_screen",
            "x": -10.82,
            "y": 1.35,
            "z": 0.9,
            "width": 2.2,
            "height": 1.5,
            "yaw_degrees": 90,
            "status": "purpose_built_code_native",
        },
        {
            "id": "avatar_talk_button",
            "role": "avatar_talk_button",
            "geometry": "pedestal_talk_button",
            "x": -10.4,
            "y": 0.0,
            "z": -0.4,
            "status": "purpose_built_code_native",
        },
    ]


def build_scene(selection_report: dict[str, Any] | None = None) -> dict[str, Any]:
    rooms = [
        room("vestibule", "Front Vestibule", 0, -7.5, 3.2, 3.0, "#8fb5c8"),
        room("reception", "Reception / Waiting", -6.7, -5.6, 9.2, 6.4, "#d7cbb5"),
        room("consultation", "Consultation", 4.2, -5.6, 4.6, 4.4, "#c7d6c5"),
        room("restroom", "Accessible Restroom", 9.3, -5.8, 3.6, 3.4, "#c8d0db"),
        room("avatar_studio", "Avatar Builder Studio", -8.3, 0.9, 6.2, 6.0, "#bccde0"),
        room("corridor", "Public Corridor", -1.7, 0.7, 5.0, 12.2, "#e2d8c5"),
        room("treatment_a", "Treatment Room A", 3.1, 0.2, 4.2, 4.6, "#d9c9c9"),
        room("treatment_b", "Treatment Room B", 7.9, 0.2, 4.2, 4.6, "#d9c9c9"),
        room("styling", "Styling Room", -8.9, 6.0, 5.2, 4.8, "#d7d2c0"),
        room("relaxation", "Relaxation Room", -2.8, 6.1, 6.0, 4.9, "#cfd9c8"),
        room("staff_laundry", "Staff / Laundry / Storage", 4.0, 6.0, 5.1, 4.8, "#c9c4bd", public=False),
        room("mechanical", "Mechanical", 9.4, 6.3, 3.2, 3.2, "#b9bec4", public=False),
    ]

    doors = [
        door("front_door", "Public front door", 0.0, -9.1, 2.4, "along_x", "front_exterior", "exterior", "vestibule", from_normal_sign=-1),
        door("vestibule_to_reception", "Reception entry", -2.0, -6.0, 1.5, "along_z", "reception_vestibule_partition", "vestibule", "reception", from_normal_sign=1),
        door("reception_to_avatar", "Avatar Studio door", -6.9, -2.3, 1.5, "along_x", "reception_avatar_partition", "reception", "avatar_studio", from_normal_sign=-1),
        door("reception_to_consult", "Consultation door", 4.2, -4.0, 1.2, "along_x", "consultation_partition", "corridor", "consultation", from_normal_sign=1),
        door("corridor_to_restroom", "Restroom door", 9.3, -4.0, 1.2, "along_x", "restroom_partition", "corridor", "restroom", from_normal_sign=1),
        door("corridor_to_treatment_a", "Treatment A door", 3.1, -2.3, 1.2, "along_x", "treatment_front_partition", "corridor", "treatment_a", from_normal_sign=-1),
        door("corridor_to_treatment_b", "Treatment B door", 7.9, -2.3, 1.2, "along_x", "treatment_front_partition", "corridor", "treatment_b", from_normal_sign=-1),
        door("corridor_to_styling", "Styling door", -8.9, 3.5, 1.2, "along_x", "back_room_front_partition", "corridor", "styling", from_normal_sign=-1),
        door("corridor_to_relaxation", "Relaxation door", -2.8, 3.5, 1.2, "along_x", "back_room_front_partition", "corridor", "relaxation", from_normal_sign=-1),
        door("corridor_to_staff", "Staff door", 4.0, 3.5, 1.2, "along_x", "back_room_front_partition", "corridor", "staff_laundry", from_normal_sign=-1),
        door("corridor_to_mechanical", "Mechanical door", 9.4, 3.5, 1.1, "along_x", "back_room_front_partition", "corridor", "mechanical", from_normal_sign=-1),
    ]

    wall_runs = [
        wall_run("front_exterior", "along_x", -9.1, -12.1, 12.1, openings=["front_door"], height=3.1, thickness=0.24, color="#f0f3ee"),
        wall_run("rear_exterior", "along_x", 9.1, -12.1, 12.1, height=3.1, thickness=0.24, color="#f0f3ee"),
        wall_run("left_exterior", "along_z", -12.1, -9.1, 9.1, height=3.1, thickness=0.24, color="#f0f3ee"),
        wall_run("right_exterior", "along_z", 12.1, -9.1, 9.1, height=3.1, thickness=0.24, color="#f0f3ee"),
        wall_run("reception_vestibule_partition", "along_z", -2.0, -8.95, -3.2, openings=["vestibule_to_reception"]),
        wall_run("reception_avatar_partition", "along_x", -2.3, -12.0, -2.1, openings=["reception_to_avatar"]),
        wall_run("consultation_partition", "along_x", -4.0, 1.8, 6.6, openings=["reception_to_consult"]),
        wall_run("restroom_partition", "along_x", -4.0, 7.45, 11.15, openings=["corridor_to_restroom"]),
        wall_run("treatment_front_partition", "along_x", -2.3, 1.0, 10.0, openings=["corridor_to_treatment_a", "corridor_to_treatment_b"]),
        wall_run("avatar_right_partition", "along_z", -5.1, -2.3, 3.5),
        wall_run("treatment_divider", "along_z", 5.5, -2.3, 2.5),
        wall_run(
            "back_room_front_partition",
            "along_x",
            3.5,
            -11.5,
            11.0,
            openings=["corridor_to_styling", "corridor_to_relaxation", "corridor_to_staff", "corridor_to_mechanical"],
        ),
        wall_run("staff_mechanical_partition", "along_z", 7.2, 3.5, 9.0),
    ]
    walls = derive_wall_geometry(wall_runs, doors)

    selection_report = selection_report or build_asset_selection_report()
    asset_instances = build_asset_instances(selection_report)
    collision_proxies = build_collision_proxies()
    code_native_fixtures = build_code_native_fixtures()
    furniture: list[dict[str, Any]] = []

    targets = [
        target("spa_front_door_outside", "Outside front door", 0.0, -10.7, "exterior"),
        target("spa_front_door_inside", "Inside vestibule", 0.0, -8.0, "vestibule"),
        target("spa_corridor_center", "Public corridor clear area", 0.0, -1.0, "corridor"),
        target("spa_reception_counter", "Reserved reception-counter approach (asset missing)", -7.2, -5.65, "reception", linked_asset_role="reception_counter", linked_asset_status="failed_missing_real_prefab"),
        target("spa_waiting_chair", "Waiting sofa approach", -3.5, -5.75, "reception", linked_asset_role="waiting_sofa"),
        target("spa_consultation_chair", "Consultation chair approach", 4.2, -4.85, "consultation", linked_asset_role="consultation_chair"),
        target("spa_avatar_builder_talk_button", "Avatar Builder talk-button approach", -9.5, -0.40, "avatar_studio", linked_asset_role="avatar_talk_button", linked_asset_status="purpose_built_code_native"),
        target("spa_avatar_preview_marker", "Avatar scanner approach", -8.3, 1.45, "avatar_studio", linked_asset_role="avatar_scanner", linked_asset_status="purpose_built_code_native"),
        target("spa_treatment_table_a", "Reserved Treatment A approach (asset missing)", 3.1, 1.20, "treatment_a", linked_asset_role="treatment_table_a", linked_asset_status="failed_missing_real_prefab"),
        target("spa_treatment_table_b", "Reserved Treatment B approach (asset missing)", 7.9, 1.20, "treatment_b", linked_asset_role="treatment_table_b", linked_asset_status="failed_missing_real_prefab"),
        target("spa_styling_chair", "Reserved styling approach (asset missing)", -8.9, 5.15, "styling", linked_asset_role="styling_salon_chair", linked_asset_status="failed_missing_real_prefab"),
        target("spa_relaxation_lounge", "Reserved relaxation approach (asset missing)", -2.8, 5.25, "relaxation", linked_asset_role="relaxation_lounges", linked_asset_status="failed_missing_real_prefab"),
        target("spa_restroom_inside", "Accessible restroom clear area", 9.3, -5.25, "restroom"),
        target("spa_exit", "Exit", 0.0, -10.7, "exterior"),
    ]
    targets.extend(door_anchor_targets(doors))

    public_route_tests = [
        {"route_id": "outside_to_vestibule", "target": "spa_front_door_inside", "via_doors": ["front_door"]},
        {"route_id": "outside_to_corridor", "target": "spa_corridor_center", "via_doors": ["front_door"]},
        {"route_id": "outside_to_reception", "target": "spa_reception_counter", "via_doors": ["front_door", "vestibule_to_reception"]},
        {"route_id": "outside_to_waiting", "target": "spa_waiting_chair", "via_doors": ["front_door", "vestibule_to_reception"]},
        {"route_id": "outside_to_consultation", "target": "spa_consultation_chair", "via_doors": ["front_door", "reception_to_consult"]},
        {"route_id": "outside_to_avatar_builder", "target": "spa_avatar_builder_talk_button", "via_doors": ["front_door", "vestibule_to_reception", "reception_to_avatar"]},
        {"route_id": "outside_to_avatar_scanner", "target": "spa_avatar_preview_marker", "via_doors": ["front_door", "vestibule_to_reception", "reception_to_avatar"]},
        {"route_id": "outside_to_treatment_a", "target": "spa_treatment_table_a", "via_doors": ["front_door", "corridor_to_treatment_a"]},
        {"route_id": "outside_to_treatment_b", "target": "spa_treatment_table_b", "via_doors": ["front_door", "corridor_to_treatment_b"]},
        {"route_id": "outside_to_styling", "target": "spa_styling_chair", "via_doors": ["front_door", "corridor_to_styling"]},
        {"route_id": "outside_to_relaxation", "target": "spa_relaxation_lounge", "via_doors": ["front_door", "corridor_to_relaxation"]},
        {"route_id": "outside_to_restroom", "target": "spa_restroom_inside", "via_doors": ["front_door", "corridor_to_restroom"]},
    ]

    return {
        "schema_version": 1,
        "project_id": PROJECT_ID,
        "created_at": now_iso(),
        "status": "staged_preview_not_approved",
        "units": "meters",
        "footprint": {"width": 24, "depth": 18},
        "truth_note": "Draft procedural preview based on Robert-approved blueprint rules, not final Home World placement.",
        "rooms": rooms,
        "wall_runs": wall_runs,
        "walls": walls,
        "furniture": furniture,
        "asset_instances": asset_instances,
        "collision_proxies": collision_proxies,
        "code_native_fixtures": code_native_fixtures,
        "missing_asset_roles": selection_report["missing_asset_roles"],
        "asset_selection_status": selection_report["status"],
        "route_targets": targets,
        "doors": doors,
        "public_route_tests": public_route_tests,
        "approval_policy": {
            "auto_place_in_home_world": False,
            "requires_robert_approval": True,
            "runtime_kira_test_completed": False,
        },
    }


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Legal Day Spa Preview</title>
  <style>
    html, body { margin: 0; height: 100%; background: #071018; color: #d9edf7; font-family: Arial, sans-serif; overflow: hidden; }
    #app { position: fixed; inset: 0; }
    #hud { position: fixed; top: 12px; left: 12px; width: 360px; max-width: calc(100vw - 24px); background: rgba(4, 16, 28, 0.88); border: 1px solid #2a6282; padding: 12px; box-sizing: border-box; }
    h1 { font-size: 18px; margin: 0 0 6px; }
    p { font-size: 12px; line-height: 1.35; margin: 5px 0; color: #b8d2df; }
    .buttons { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; margin-top: 10px; }
    button { background: #0d3b5d; color: #e2f7ff; border: 1px solid #3e8db7; padding: 7px 8px; cursor: pointer; }
    button:hover { background: #14547f; }
    #status { position: fixed; right: 12px; bottom: 12px; max-width: 520px; background: rgba(4, 16, 28, 0.88); border: 1px solid #2a6282; padding: 10px; font-size: 12px; color: #c9e5f2; }
    #assetFailures { position: fixed; right: 12px; top: 12px; width: 410px; max-width: calc(100vw - 24px); background: rgba(4, 16, 28, 0.92); border: 1px solid #2a6282; padding: 10px; box-sizing: border-box; font-size: 12px; color: #bde7d1; white-space: pre-wrap; }
    #assetFailures.failed { border-color: #e05b66; color: #ffd5d8; }
  </style>
</head>
<body>
  <div id="app"></div>
  <div id="hud">
    <h1>Legal Day Spa Preview</h1>
    <p>Staged only. Not placed in Home World. This review scene checks layout, interactive doors, route targets, and Avatar Builder room placement before approval.</p>
    <p>Drag to orbit. Wheel to zoom. Click a door to open or close it. Labels can be hidden once the layout is understandable.</p>
    <div class="buttons">
      <button data-view="overview">Completed View</button>
      <button data-view="exterior">Exterior</button>
      <button data-view="front">Front Door</button>
      <button data-view="overhead">Blueprint</button>
      <button data-view="reception">Reception</button>
      <button data-view="avatar">Avatar Room</button>
      <button data-view="route">Route Path</button>
      <button data-action="toggle-labels">Hide Labels</button>
      <button data-action="open-doors">Open Doors</button>
      <button data-action="close-doors">Close Doors</button>
    </div>
  </div>
  <div id="status">Grade: draft. Needs Robert review and a Kira route test before Home World placement.</div>
  <div id="assetFailures">Real prefabs: preparing loader...</div>
  <script type="importmap">
    {"imports":{"three":"__THREE_MODULE_URL__","three/addons/":"__THREE_ADDONS_URL__"}}
  </script>
  <script type="module">
    import * as THREE from "three";
    import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
    const sceneData = __SCENE_JSON__;
    const root = document.querySelector("#app");
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x071018);
    const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 200);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    root.appendChild(renderer.domElement);

    const ambient = new THREE.HemisphereLight(0xdff5ff, 0x29363f, 1.6);
    scene.add(ambient);
    const key = new THREE.DirectionalLight(0xffffff, 1.8);
    key.position.set(-10, 18, -12);
    key.castShadow = true;
    scene.add(key);
    const fill = new THREE.PointLight(0x5bbdff, 1.2, 45);
    fill.position.set(0, 5, -5);
    scene.add(fill);

    const mats = new Map();
    const labelSprites = [];
    const doorGroups = new Map();
    const doorHitMeshes = [];
    const roofMeshes = [];
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const gltfLoader = new GLTFLoader();
    const sourceCache = new Map();
    const assetFailurePanel = document.querySelector("#assetFailures");
    const assetLoadState = {
      status: "loading",
      expectedInstances: sceneData.asset_instances.length,
      expectedUniqueSources: new Set(sceneData.asset_instances.map(item => item.source_url)).size,
      loaded: [],
      failures: [],
      uniqueSourcesRequested: 0,
    };
    window.spaReview = { version: 1, ready: false, assetLoadState };

    function updateAssetFailurePanel() {
      const loaded = assetLoadState.loaded.length;
      const expected = assetLoadState.expectedInstances;
      if (assetLoadState.failures.length) {
        assetFailurePanel.classList.add("failed");
        const details = assetLoadState.failures.map(row => `${row.id}: ${row.error}`).join(String.fromCharCode(10));
        assetFailurePanel.textContent = `REAL PREFAB LOAD FAILURE (${loaded}/${expected} loaded)\n${details}\nNo colored-block fallback was created.`;
        return;
      }
      assetFailurePanel.classList.remove("failed");
      assetFailurePanel.textContent = assetLoadState.status === "loaded"
        ? `Real prefabs: ${loaded}/${expected} loaded from ${sourceCache.size} unique GLB sources.`
        : `Real prefabs: loading ${loaded}/${expected}...`;
    }

    function cachedSourceRoot(sourceUrl) {
      if (!sourceCache.has(sourceUrl)) {
        sourceCache.set(sourceUrl, gltfLoader.loadAsync(sourceUrl).then(gltf => {
          const rootObject = gltf.scene || gltf.scenes?.[0];
          if (!rootObject) throw new Error("GLB did not contain a scene root");
          return rootObject;
        }));
        assetLoadState.uniqueSourcesRequested = sourceCache.size;
      }
      return sourceCache.get(sourceUrl);
    }

    function addFittedRealPrefab(sourceRoot, instance) {
      if (instance.selector?.kind !== "scene_root") {
        throw new Error(`unsupported selector ${JSON.stringify(instance.selector)}`);
      }
      const model = sourceRoot.clone(true);
      const holder = new THREE.Group();
      holder.name = instance.id;
      holder.add(model);

      let bounds = new THREE.Box3().setFromObject(model);
      const size = bounds.getSize(new THREE.Vector3());
      if (![size.x, size.y, size.z].every(value => Number.isFinite(value) && value > 1e-5)) {
        throw new Error(`invalid Box3 source bounds ${size.x},${size.y},${size.z}`);
      }
      const fit = instance.fit;
      const uniformScale = Math.min(fit.max_width / size.x, fit.max_height / size.y, fit.max_depth / size.z);
      if (!Number.isFinite(uniformScale) || uniformScale <= 0) {
        throw new Error("uniform Box3 fit produced an invalid scale");
      }
      model.scale.multiplyScalar(uniformScale);
      model.updateMatrixWorld(true);
      bounds = new THREE.Box3().setFromObject(model);
      const center = bounds.getCenter(new THREE.Vector3());
      model.position.x -= center.x;
      model.position.z -= center.z;
      if (instance.bottom_align !== false) model.position.y -= bounds.min.y;
      holder.rotation.y = THREE.MathUtils.degToRad(instance.yaw_degrees || 0);
      holder.position.set(instance.x, instance.y, instance.z);
      model.traverse(object => {
        if (object.isMesh) {
          object.castShadow = true;
          object.receiveShadow = true;
        }
      });
      holder.userData = {
        assetRole: instance.role,
        prefabId: instance.prefab_id,
        sourceUrl: instance.source_url,
        sourceSha256: instance.source_sha256,
        renderMode: "real_prefab",
      };
      scene.add(holder);
      return holder;
    }

    async function loadRealPrefab(instance) {
      try {
        const sourceRoot = await cachedSourceRoot(instance.source_url);
        addFittedRealPrefab(sourceRoot, instance);
        assetLoadState.loaded.push({ id: instance.id, role: instance.role, sourceUrl: instance.source_url });
      } catch (error) {
        assetLoadState.failures.push({
          id: instance.id,
          role: instance.role,
          sourceUrl: instance.source_url,
          status: instance.load_failure_status || "failed_missing_real_prefab",
          error: error instanceof Error ? error.message : String(error),
        });
        // Deliberately no primitive, colored-block, or semantic fallback.
      }
      updateAssetFailurePanel();
    }
    function mat(color, rough = true, kind = "solid") {
      const key = [color, rough, kind].join(":");
      if (!mats.has(key)) {
        const opts = { color, roughness: rough ? 0.82 : 0.35, metalness: rough ? 0.05 : 0.2 };
        if (kind === "glass") {
          opts.transparent = true;
          opts.opacity = 0.42;
          opts.roughness = 0.08;
          opts.metalness = 0.0;
        }
        if (kind === "glow") {
          opts.emissive = new THREE.Color(color);
          opts.emissiveIntensity = 0.55;
        }
        mats.set(key, new THREE.MeshStandardMaterial(opts));
      }
      return mats.get(key);
    }
    function addBox(item) {
      const geom = new THREE.BoxGeometry(item.w, item.h, item.d);
      const mesh = new THREE.Mesh(geom, mat(item.color, true, item.kind === "glass" ? "glass" : (item.kind === "control" || item.kind === "glow") ? "glow" : "solid"));
      mesh.position.set(item.x, item.y, item.z);
      mesh.castShadow = item.kind !== "floor";
      mesh.receiveShadow = true;
      mesh.name = item.name || item.id || item.label;
      scene.add(mesh);
      if (item.kind === "roof") roofMeshes.push(mesh);
      return mesh;
    }
    function addCylinder(name, x, y, z, radius, depth, color, rotation = [0, 0, 0], segments = 32) {
      const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, depth, segments), mat(color, true));
      mesh.position.set(x, y, z);
      mesh.rotation.set(rotation[0], rotation[1], rotation[2]);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      mesh.name = name;
      scene.add(mesh);
      return mesh;
    }
    function framedCanvasSign(fixture) {
      const canvas = document.createElement("canvas");
      canvas.width = 1024;
      canvas.height = 512;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#f1eee3";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.strokeStyle = "#2d748c";
      ctx.lineWidth = 18;
      ctx.strokeRect(18, 18, canvas.width - 36, canvas.height - 36);
      ctx.fillStyle = "#123b4a";
      ctx.textAlign = "center";
      ctx.font = "bold 48px Arial";
      ctx.fillText(fixture.title, canvas.width / 2, 92);
      ctx.font = "36px Arial";
      fixture.lines.forEach((line, index) => ctx.fillText(line, canvas.width / 2, 175 + index * 68));
      const texture = new THREE.CanvasTexture(canvas);
      texture.colorSpace = THREE.SRGBColorSpace;
      const group = new THREE.Group();
      group.name = fixture.id;
      group.position.set(fixture.x, fixture.y, fixture.z);
      group.rotation.y = THREE.MathUtils.degToRad(fixture.yaw_degrees || 0);
      const board = new THREE.Mesh(
        new THREE.PlaneGeometry(3.0, 1.5),
        new THREE.MeshStandardMaterial({ map: texture, roughness: 0.72, side: THREE.DoubleSide })
      );
      board.castShadow = true;
      group.add(board);
      const frameMat = mat("#1d3d49", false);
      const horizontal = new THREE.BoxGeometry(3.12, 0.08, 0.08);
      const vertical = new THREE.BoxGeometry(0.08, 1.58, 0.08);
      for (const y of [-0.79, 0.79]) {
        const bar = new THREE.Mesh(horizontal, frameMat);
        bar.position.y = y;
        group.add(bar);
      }
      for (const x of [-1.56, 1.56]) {
        const bar = new THREE.Mesh(vertical, frameMat);
        bar.position.x = x;
        group.add(bar);
      }
      scene.add(group);
    }

    function avatarScanner(fixture) {
      const group = new THREE.Group();
      group.name = fixture.id;
      group.position.set(fixture.x, fixture.y, fixture.z);
      const scannerMat = new THREE.MeshStandardMaterial({ color: 0x50ddff, emissive: 0x137c98, emissiveIntensity: 1.5, metalness: 0.55, roughness: 0.22 });
      const ring = new THREE.Mesh(new THREE.TorusGeometry(fixture.radius, fixture.tube, 20, 128), scannerMat);
      ring.castShadow = true;
      group.add(ring);
      const guide = new THREE.Mesh(
        new THREE.TorusGeometry(fixture.radius * 0.78, fixture.tube * 0.22, 12, 96),
        new THREE.MeshBasicMaterial({ color: 0xa3efff, transparent: true, opacity: 0.45 })
      );
      group.add(guide);
      const statusLight = new THREE.PointLight(0x48dfff, 1.4, 5.5);
      statusLight.position.set(0, 0, 0.35);
      group.add(statusLight);
      scene.add(group);
    }

    function avatarApprovalScreen(fixture) {
      const group = new THREE.Group();
      group.name = fixture.id;
      group.position.set(fixture.x, fixture.y, fixture.z);
      group.rotation.y = THREE.MathUtils.degToRad(fixture.yaw_degrees || 0);
      const screen = new THREE.Mesh(
        new THREE.PlaneGeometry(fixture.width, fixture.height),
        new THREE.MeshStandardMaterial({ color: 0x65dfff, emissive: 0x126987, emissiveIntensity: 1.25, roughness: 0.16, side: THREE.DoubleSide })
      );
      group.add(screen);
      const frameMat = mat("#172d38", false);
      const horizontal = new THREE.BoxGeometry(fixture.width + 0.16, 0.09, 0.10);
      const vertical = new THREE.BoxGeometry(0.09, fixture.height + 0.16, 0.10);
      for (const y of [-fixture.height / 2 - 0.045, fixture.height / 2 + 0.045]) {
        const bar = new THREE.Mesh(horizontal, frameMat);
        bar.position.y = y;
        group.add(bar);
      }
      for (const x of [-fixture.width / 2 - 0.045, fixture.width / 2 + 0.045]) {
        const bar = new THREE.Mesh(vertical, frameMat);
        bar.position.x = x;
        group.add(bar);
      }
      scene.add(group);
    }

    function avatarTalkButton(fixture) {
      const group = new THREE.Group();
      group.name = fixture.id;
      group.position.set(fixture.x, fixture.y, fixture.z);
      const pedestal = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.25, 0.72, 32), mat("#203c49", false));
      pedestal.position.y = 0.36;
      pedestal.castShadow = true;
      group.add(pedestal);
      const button = new THREE.Mesh(
        new THREE.SphereGeometry(0.16, 32, 18),
        new THREE.MeshStandardMaterial({ color: 0xffdc73, emissive: 0xa55a00, emissiveIntensity: 1.1, metalness: 0.25, roughness: 0.28 })
      );
      button.scale.y = 0.42;
      button.position.y = 0.77;
      button.name = fixture.id + "_press_surface";
      group.add(button);
      scene.add(group);
    }

    function addCodeNativeFixture(fixture) {
      if (fixture.geometry === "framed_canvas_sign") framedCanvasSign(fixture);
      if (fixture.geometry === "torus_scanner_ring") avatarScanner(fixture);
      if (fixture.geometry === "framed_emissive_screen") avatarApprovalScreen(fixture);
      if (fixture.geometry === "pedestal_talk_button") avatarTalkButton(fixture);
    }
    function label(text, x, y, z, color = "#dff6ff") {
      const canvas = document.createElement("canvas");
      canvas.width = 512;
      canvas.height = 128;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "rgba(4,16,28,0.82)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.strokeStyle = "#2a8bb9";
      ctx.strokeRect(4, 4, canvas.width - 8, canvas.height - 8);
      ctx.fillStyle = color;
      ctx.font = "bold 34px Arial";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(text, canvas.width / 2, canvas.height / 2);
      const texture = new THREE.CanvasTexture(canvas);
      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true }));
      sprite.position.set(x, y, z);
      sprite.scale.set(3.2, 0.8, 1);
      scene.add(sprite);
      labelSprites.push(sprite);
      return sprite;
    }

    addBox({ name: "site_ground", kind: "floor", x: 0, y: -0.05, z: 0, w: 34, h: 0.08, d: 28, color: "#496c4c" });
    addBox({ name: "spa_foundation", kind: "floor", x: 0, y: 0, z: 0, w: 24.2, h: 0.08, d: 18.2, color: "#c6c0b4" });
    addBox({ name: "front_sidewalk", kind: "floor", x: 0, y: 0.02, z: -11.6, w: 30, h: 0.05, d: 2.2, color: "#d8d8d2" });
    addBox({ name: "front_walkway", kind: "floor", x: 0, y: 0.03, z: -10.1, w: 3.6, h: 0.05, d: 3.4, color: "#e7e2d8" });
    addBox({ name: "soft_roof_slab", kind: "roof", x: 0, y: 3.26, z: 0.15, w: 25.0, h: 0.16, d: 18.9, color: "#44535a" });
    addBox({ name: "front_parapet", kind: "roof", x: 0, y: 3.62, z: -9.35, w: 25.3, h: 0.62, d: 0.35, color: "#52656a" });
    addBox({ name: "warm_entry_canopy", kind: "roof", x: 0, y: 2.9, z: -9.82, w: 4.4, h: 0.18, d: 1.45, color: "#6f8078" });
    addBox({ name: "entry_sign_panel", kind: "glow", x: 0, y: 3.55, z: -9.58, w: 6.4, h: 0.7, d: 0.08, color: "#103a4d" });

    for (const room of sceneData.rooms) {
      addBox({ name: room.id + "_floor", kind: "floor", x: room.x, y: 0.04, z: room.z, w: room.w, h: 0.05, d: room.d, color: room.color });
      label(room.label, room.x, 0.35, room.z, "#eefaff");
    }
    for (const wall of sceneData.walls) addBox(wall);
    for (const fixture of sceneData.code_native_fixtures) addCodeNativeFixture(fixture);
    // collision_proxies are consumed only by the Python static validator and are never rendered.
    const assetLoadPromise = Promise.all(sceneData.asset_instances.map(loadRealPrefab)).then(() => {
      assetLoadState.status = assetLoadState.failures.length ? "failed" : "loaded";
      window.spaReview.ready = true;
      updateAssetFailurePanel();
      return assetLoadState;
    });

    const trim = "#dfe8e3";
    addBox({ name: "front_base_trim", kind: "trim", x: 0, y: 0.18, z: -9.23, w: 24.6, h: 0.18, d: 0.1, color: trim });
    addBox({ name: "rear_base_trim", kind: "trim", x: 0, y: 0.18, z: 9.23, w: 24.6, h: 0.18, d: 0.1, color: trim });
    addBox({ name: "left_base_trim", kind: "trim", x: -12.23, y: 0.18, z: 0, w: 0.1, h: 0.18, d: 18.5, color: trim });
    addBox({ name: "right_base_trim", kind: "trim", x: 12.23, y: 0.18, z: 0, w: 0.1, h: 0.18, d: 18.5, color: trim });
    addBox({ name: "front_window_left_frame_top", kind: "trim", x: -3.0, y: 2.76, z: -9.04, w: 5.1, h: 0.12, d: 0.14, color: "#22343d" });
    addBox({ name: "front_window_left_frame_bottom", kind: "trim", x: -3.0, y: 0.18, z: -9.04, w: 5.1, h: 0.12, d: 0.14, color: "#22343d" });
    addBox({ name: "front_window_right_frame_top", kind: "trim", x: 3.0, y: 2.76, z: -9.04, w: 5.1, h: 0.12, d: 0.14, color: "#22343d" });
    addBox({ name: "front_window_right_frame_bottom", kind: "trim", x: 3.0, y: 0.18, z: -9.04, w: 5.1, h: 0.12, d: 0.14, color: "#22343d" });
    addBox({ name: "front_door_frame_header", kind: "trim", x: 0, y: 2.72, z: -9.23, w: 2.7, h: 0.16, d: 0.18, color: "#1d3038" });
    addBox({ name: "front_door_frame_left", kind: "trim", x: -1.32, y: 1.35, z: -9.23, w: 0.16, h: 2.75, d: 0.18, color: "#1d3038" });
    addBox({ name: "front_door_frame_right", kind: "trim", x: 1.32, y: 1.35, z: -9.23, w: 0.16, h: 2.75, d: 0.18, color: "#1d3038" });
    addBox({ name: "glass_storefront_left", kind: "glass", x: -3.0, y: 1.45, z: -9.0, w: 4.8, h: 2.5, d: 0.05, color: "#79b7ce" });
    addBox({ name: "glass_storefront_right", kind: "glass", x: 3.0, y: 1.45, z: -9.0, w: 4.8, h: 2.5, d: 0.05, color: "#79b7ce" });
    label("LEGAL DAY SPA + AVATAR BUILDER", 0, 3.35, -9.2, "#9feaff");

    const targetMat = new THREE.MeshStandardMaterial({ color: 0x2fe0ff, emissive: 0x0d6c86, emissiveIntensity: 0.8 });
    for (const t of sceneData.route_targets) {
      const marker = new THREE.Mesh(new THREE.SphereGeometry(0.18, 24, 16), targetMat);
      marker.position.set(t.x, t.y + 0.18, t.z);
      scene.add(marker);
      if (t.show_label !== false) label(t.label, t.x, 0.9, t.z, "#ffffff");
    }

    const doorMat = new THREE.MeshStandardMaterial({ color: 0x6fd5ff, emissive: 0x113f54, emissiveIntensity: 0.25, transparent: true, opacity: 0.76 });
    const handleMat = new THREE.MeshStandardMaterial({ color: 0xf4d58d, roughness: 0.28, metalness: 0.45 });
    const hingeMat = new THREE.MeshStandardMaterial({ color: 0x243540, roughness: 0.35, metalness: 0.45 });
    function setDoorState(id, open) {
      const entry = doorGroups.get(id);
      if (!entry) return;
      entry.open = open;
      entry.group.rotation.y = open ? entry.openAngle : 0;
      document.querySelector("#status").textContent = `${entry.label}: ${open ? "open" : "closed"}. Grade still draft until Robert approves and Kira can walk it.`;
    }
    function toggleDoor(id) {
      const entry = doorGroups.get(id);
      if (entry) setDoorState(id, !entry.open);
    }
    for (const d of sceneData.doors) {
      const isMissingStorefrontDoor = d.id === "front_door";
      const alongX = d.orientation === "along_x";
      const hingeX = alongX ? d.x - d.width / 2 : d.x;
      const hingeZ = alongX ? d.z : d.z - d.width / 2;
      const openAngle = THREE.MathUtils.degToRad(d.open_angle_degrees || 90);
      const group = new THREE.Group();
      group.position.set(hingeX, 0, hingeZ);
      group.name = d.id + "_hinge_group";
      const panelGeometry = alongX
        ? new THREE.BoxGeometry(d.width, 2.2, 0.08)
        : new THREE.BoxGeometry(0.08, 2.2, d.width);
      const panelMaterial = isMissingStorefrontDoor
        ? new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false, colorWrite: false })
        : doorMat;
      const panel = new THREE.Mesh(panelGeometry, panelMaterial);
      panel.position.set(alongX ? d.width / 2 : 0, 1.1, alongX ? 0 : d.width / 2);
      panel.name = d.id + "_clickable_panel";
      panel.userData.doorId = d.id;
      panel.castShadow = !isMissingStorefrontDoor;
      panel.receiveShadow = !isMissingStorefrontDoor;
      group.add(panel);
      if (!isMissingStorefrontDoor) {
        const handle = new THREE.Mesh(new THREE.SphereGeometry(0.075, 18, 12), handleMat);
        handle.position.set(alongX ? d.width * 0.82 : -0.08, 1.04, alongX ? -0.08 : d.width * 0.82);
        handle.name = d.id + "_handle";
        group.add(handle);
        const hinge = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.045, 2.25, 16), hingeMat);
        hinge.position.set(0, 1.12, 0);
        hinge.name = d.id + "_hinge";
        group.add(hinge);
      }
      scene.add(group);
      doorGroups.set(d.id, { group, label: d.label, open: true, openAngle });
      doorHitMeshes.push(panel);
      setDoorState(d.id, true);
      label(isMissingStorefrontDoor ? "MISSING: DOUBLE-GLASS STOREFRONT DOOR" : d.label, d.x, 2.55, d.z, isMissingStorefrontDoor ? "#ffd5d8" : "#aeeeff");
    }

    const routePoints = (sceneData.validated_review_route_points || []).map(point => new THREE.Vector3(point.x, 0.18, point.z));
    if (routePoints.length > 1) {
      const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(routePoints), new THREE.LineBasicMaterial({ color: 0xffd166, linewidth: 4 }));
      scene.add(line);
    }

    let theta = -0.75;
    let phi = 0.92;
    let radius = 31;
    let target = new THREE.Vector3(0, 0, 0);
    function setCamera() {
      camera.position.set(
        target.x + radius * Math.sin(phi) * Math.sin(theta),
        target.y + radius * Math.cos(phi),
        target.z + radius * Math.sin(phi) * Math.cos(theta)
      );
      camera.lookAt(target);
    }
    function preset(name) {
      const roofVisible = name === "exterior" || name === "front";
      roofMeshes.forEach(mesh => { mesh.visible = roofVisible; });
      if (name === "overview") { theta = -0.75; phi = 0.92; radius = 31; target.set(0, 0, 0); }
      if (name === "exterior") { theta = -2.75; phi = 1.22; radius = 18; target.set(0, 1.05, -9.2); }
      if (name === "front") { theta = Math.PI; phi = 1.24; radius = 20; target.set(0, 0.6, -8.5); }
      if (name === "overhead") { theta = 0; phi = 0.04; radius = 31; target.set(0, 0, 0); }
      if (name === "reception") { theta = -0.75; phi = 0.92; radius = 17; target.set(-5.0, 0.0, -5.0); }
      if (name === "avatar") { theta = -0.8; phi = 1.08; radius = 9; target.set(-8.3, 0.8, 0.8); }
      if (name === "route") { theta = -0.55; phi = 0.75; radius = 25; target.set(-2.2, 0.2, -1.4); }
      setCamera();
    }
    function setLabels(visible) {
      labelSprites.forEach(sprite => { sprite.visible = visible; });
      const button = document.querySelector('button[data-action="toggle-labels"]');
      if (button) button.textContent = visible ? "Hide Labels" : "Show Labels";
    }
    function setAllDoors(open) {
      for (const id of doorGroups.keys()) setDoorState(id, open);
    }
    document.querySelectorAll("button[data-view]").forEach(btn => btn.addEventListener("click", () => preset(btn.dataset.view)));
    document.querySelectorAll("button[data-action]").forEach(btn => btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      if (action === "toggle-labels") {
        const visible = labelSprites.some(sprite => sprite.visible);
        setLabels(!visible);
      }
      if (action === "open-doors") setAllDoors(true);
      if (action === "close-doors") setAllDoors(false);
    }));

    Object.assign(window.spaReview, {
      loadPromise: assetLoadPromise,
      preset,
      setDoorState,
      setAllDoors,
      setLabels,
      snapshot: () => ({
        ready: window.spaReview.ready,
        status: assetLoadState.status,
        expectedInstances: assetLoadState.expectedInstances,
        expectedUniqueSources: assetLoadState.expectedUniqueSources,
        uniqueSourcesRequested: assetLoadState.uniqueSourcesRequested,
        loaded: assetLoadState.loaded.map(row => ({ ...row })),
        failures: assetLoadState.failures.map(row => ({ ...row })),
      }),
    });

    let dragging = false;
    let lastX = 0;
    let lastY = 0;
    renderer.domElement.addEventListener("pointerdown", event => { dragging = true; lastX = event.clientX; lastY = event.clientY; renderer.domElement.setPointerCapture(event.pointerId); });
    renderer.domElement.addEventListener("pointermove", event => {
      if (!dragging) return;
      const dx = event.clientX - lastX;
      const dy = event.clientY - lastY;
      lastX = event.clientX;
      lastY = event.clientY;
      theta -= dx * 0.006;
      phi = Math.max(0.08, Math.min(1.45, phi + dy * 0.004));
      setCamera();
    });
    renderer.domElement.addEventListener("pointerup", () => { dragging = false; });
    renderer.domElement.addEventListener("click", event => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hit = raycaster.intersectObjects(doorHitMeshes, false)[0];
      if (hit && hit.object.userData.doorId) toggleDoor(hit.object.userData.doorId);
    });
    renderer.domElement.addEventListener("wheel", event => {
      event.preventDefault();
      radius = Math.max(5, Math.min(55, radius + event.deltaY * 0.02));
      setCamera();
    }, { passive: false });
    window.addEventListener("resize", () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });
    preset("overview");
    function animate() {
      requestAnimationFrame(animate);
      renderer.render(scene, camera);
    }
    animate();
  </script>
</body>
</html>
"""


def write_floorplan_svg(path: Path, scene: dict[str, Any]) -> None:
    scale = 32
    pad = 30
    width = int(24 * scale + pad * 2)
    height = int(18 * scale + pad * 2)

    def sx(x: float) -> float:
        return pad + (x + 12) * scale

    def sz(z: float) -> float:
        return pad + (z + 9) * scale

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#081723"/>',
        f'<rect x="{pad}" y="{pad}" width="{24*scale}" height="{18*scale}" fill="#c6c0b4" stroke="#8dd9ff" stroke-width="3"/>',
    ]
    for r in scene["rooms"]:
        x = sx(r["x"] - r["w"] / 2)
        z = sz(r["z"] - r["d"] / 2)
        lines.append(f'<rect x="{x:.1f}" y="{z:.1f}" width="{r["w"]*scale:.1f}" height="{r["d"]*scale:.1f}" fill="{r["color"]}" stroke="#12364a" stroke-width="2"/>')
        lines.append(f'<text x="{sx(r["x"]):.1f}" y="{sz(r["z"]):.1f}" fill="#09202e" font-family="Arial" font-size="11" text-anchor="middle">{r["label"]}</text>')
    for d in scene["doors"]:
        lines.append(f'<circle cx="{sx(d["x"]):.1f}" cy="{sz(d["z"]):.1f}" r="7" fill="#2fe0ff" stroke="#05202c" stroke-width="2"/>')
    for t in scene["route_targets"]:
        lines.append(f'<circle cx="{sx(t["x"]):.1f}" cy="{sz(t["z"]):.1f}" r="4" fill="#ffd166"/>')
    lines.append("</svg>")
    write_text(path, "\n".join(lines))


def _box_bounds(item: dict[str, Any], expansion: float = 0.0) -> tuple[float, float, float, float]:
    return (
        item["x"] - item["w"] / 2 - expansion,
        item["x"] + item["w"] / 2 + expansion,
        item["z"] - item["d"] / 2 - expansion,
        item["z"] + item["d"] / 2 + expansion,
    )


def _positive_aabb_overlap(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
    *,
    tolerance: float = 1e-7,
) -> tuple[float, float] | None:
    overlap_x = min(first[1], second[1]) - max(first[0], second[0])
    overlap_z = min(first[3], second[3]) - max(first[2], second[2])
    if overlap_x > tolerance and overlap_z > tolerance:
        return overlap_x, overlap_z
    return None


def _door_aperture_bounds(scene: dict[str, Any], item: dict[str, Any]) -> tuple[float, float, float, float]:
    run = next(run for run in scene["wall_runs"] if run["id"] == item["wall_run_id"])
    half_width = item["width"] / 2
    half_thickness = max(run["thickness"], DOOR_LEAF_THICKNESS_METERS) / 2
    if item["orientation"] == "along_x":
        return item["x"] - half_width, item["x"] + half_width, item["z"] - half_thickness, item["z"] + half_thickness
    return item["x"] - half_thickness, item["x"] + half_thickness, item["z"] - half_width, item["z"] + half_width


def door_wall_overlaps(scene: dict[str, Any]) -> list[dict[str, Any]]:
    """Return positive-area overlaps between every door aperture and solid wall segment."""

    failures: list[dict[str, Any]] = []
    for item in scene["doors"]:
        door_bounds = _door_aperture_bounds(scene, item)
        for wall in scene["walls"]:
            overlap = _positive_aabb_overlap(door_bounds, _box_bounds(wall))
            if overlap is not None:
                failures.append({
                    "door_id": item["id"],
                    "wall_segment": wall["name"],
                    "wall_run_id": wall["wall_run_id"],
                    "overlap_x_m": round(overlap[0], 6),
                    "overlap_z_m": round(overlap[1], 6),
                })
    return failures


def _solid_obstacles(scene: dict[str, Any]) -> list[dict[str, Any]]:
    proxies = scene.get("collision_proxies")
    planned_obstacles = proxies if isinstance(proxies, list) else scene.get("furniture", [])
    return [item for item in [*scene["walls"], *planned_obstacles] if item.get("solid", True)]


def target_clearance_failures(
    scene: dict[str, Any],
    avatar_radius: float = AVATAR_RADIUS_METERS,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for target_item in scene["route_targets"]:
        if not target_item.get("requires_clearance", True):
            continue
        for obstacle in _solid_obstacles(scene):
            xmin, xmax, zmin, zmax = _box_bounds(obstacle, avatar_radius)
            if xmin <= target_item["x"] <= xmax and zmin <= target_item["z"] <= zmax:
                failures.append({
                    "target_id": target_item["id"],
                    "obstacle": obstacle["name"],
                    "avatar_radius_m": avatar_radius,
                })
    return failures


def _door_leaf_segment(item: dict[str, Any], is_open: bool) -> tuple[tuple[float, float], tuple[float, float]]:
    tangent_x, tangent_z = (1.0, 0.0) if item["orientation"] == "along_x" else (0.0, 1.0)
    hinge_x = item["x"] - tangent_x * item["width"] / 2
    hinge_z = item["z"] - tangent_z * item["width"] / 2
    angle = math.radians(item["open_angle_degrees"] if is_open else 0.0)
    # Match THREE.js positive Y rotation: x' = cos*x + sin*z; z' = -sin*x + cos*z.
    dx = tangent_x * item["width"]
    dz = tangent_z * item["width"]
    rotated_x = math.cos(angle) * dx + math.sin(angle) * dz
    rotated_z = -math.sin(angle) * dx + math.cos(angle) * dz
    return (hinge_x, hinge_z), (hinge_x + rotated_x, hinge_z + rotated_z)


def _point_segment_distance(
    x: float,
    z: float,
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    dx = end[0] - start[0]
    dz = end[1] - start[1]
    length_squared = dx * dx + dz * dz
    if length_squared <= 1e-12:
        return math.hypot(x - start[0], z - start[1])
    amount = max(0.0, min(1.0, ((x - start[0]) * dx + (z - start[1]) * dz) / length_squared))
    nearest_x = start[0] + amount * dx
    nearest_z = start[1] + amount * dz
    return math.hypot(x - nearest_x, z - nearest_z)


def point_blocked(
    x: float,
    z: float,
    scene: dict[str, Any],
    *,
    avatar_radius: float = AVATAR_RADIUS_METERS,
    door_states: dict[str, bool] | None = None,
) -> bool:
    for obstacle in _solid_obstacles(scene):
        xmin, xmax, zmin, zmax = _box_bounds(obstacle, avatar_radius)
        if xmin <= x <= xmax and zmin <= z <= zmax:
            return True
    states = door_states or {}
    for item in scene["doors"]:
        start, end = _door_leaf_segment(item, states.get(item["id"], True))
        if _point_segment_distance(x, z, start, end) <= avatar_radius + DOOR_LEAF_THICKNESS_METERS / 2:
            return True
    return False


def _line_clear(
    start: tuple[float, float],
    end: tuple[float, float],
    scene: dict[str, Any],
    avatar_radius: float,
    door_states: dict[str, bool],
    sample_step: float,
) -> bool:
    distance = math.dist(start, end)
    sample_count = max(1, math.ceil(distance / sample_step))
    for index in range(sample_count + 1):
        amount = index / sample_count
        x = start[0] + (end[0] - start[0]) * amount
        z = start[1] + (end[1] - start[1]) * amount
        if point_blocked(x, z, scene, avatar_radius=avatar_radius, door_states=door_states):
            return False
    return True


def astar_path(
    scene: dict[str, Any],
    start: tuple[float, float],
    goal: tuple[float, float],
    *,
    avatar_radius: float = AVATAR_RADIUS_METERS,
    door_states: dict[str, bool] | None = None,
    bounds: tuple[float, float, float, float] = STATIC_PATH_BOUNDS,
    grid_step: float = PATH_GRID_METERS,
) -> list[tuple[float, float]] | None:
    """Run a deterministic 2D capsule-center A* against static AABBs and door leaves."""

    states = {item["id"]: True for item in scene["doors"]}
    if door_states:
        states.update(door_states)
    if point_blocked(*start, scene, avatar_radius=avatar_radius, door_states=states):
        return None
    if point_blocked(*goal, scene, avatar_radius=avatar_radius, door_states=states):
        return None

    xmin, xmax, zmin, zmax = bounds
    if not (xmin <= start[0] <= xmax and zmin <= start[1] <= zmax):
        return None
    if not (xmin <= goal[0] <= xmax and zmin <= goal[1] <= zmax):
        return None
    x_count = int(math.floor((xmax - xmin) / grid_step)) + 1
    z_count = int(math.floor((zmax - zmin) / grid_step)) + 1

    def point_for(node: tuple[int, int]) -> tuple[float, float]:
        return xmin + node[0] * grid_step, zmin + node[1] * grid_step

    blocked_cache: dict[tuple[int, int], bool] = {}

    def node_blocked(node: tuple[int, int]) -> bool:
        if node[0] < 0 or node[0] >= x_count or node[1] < 0 or node[1] >= z_count:
            return True
        if node not in blocked_cache:
            blocked_cache[node] = point_blocked(*point_for(node), scene, avatar_radius=avatar_radius, door_states=states)
        return blocked_cache[node]

    def nearest_open_node(point: tuple[float, float]) -> tuple[int, int] | None:
        base = (round((point[0] - xmin) / grid_step), round((point[1] - zmin) / grid_step))
        candidates: list[tuple[float, tuple[int, int]]] = []
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                node = (base[0] + dx, base[1] + dz)
                if node_blocked(node):
                    continue
                candidate_point = point_for(node)
                if not _line_clear(point, candidate_point, scene, avatar_radius, states, grid_step / 2):
                    continue
                candidates.append((math.dist(point, candidate_point), node))
        return min(candidates, default=(0.0, None), key=lambda row: (row[0], row[1]))[1]

    start_node = nearest_open_node(start)
    goal_node = nearest_open_node(goal)
    if start_node is None or goal_node is None:
        return None

    neighbor_steps = [
        (-1, 0, 1.0),
        (1, 0, 1.0),
        (0, -1, 1.0),
        (0, 1, 1.0),
        (-1, -1, math.sqrt(2)),
        (-1, 1, math.sqrt(2)),
        (1, -1, math.sqrt(2)),
        (1, 1, math.sqrt(2)),
    ]
    frontier: list[tuple[float, float, int, tuple[int, int]]] = []
    serial = 0
    heapq.heappush(frontier, (math.dist(start_node, goal_node), 0.0, serial, start_node))
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    costs = {start_node: 0.0}
    while frontier:
        _, current_cost, _, current = heapq.heappop(frontier)
        if current_cost > costs.get(current, math.inf) + 1e-9:
            continue
        if current == goal_node:
            nodes = [current]
            while nodes[-1] != start_node:
                nodes.append(came_from[nodes[-1]])
            nodes.reverse()
            points = [point_for(node) for node in nodes]
            points[0] = start
            points[-1] = goal
            return points
        for dx, dz, move_cost in neighbor_steps:
            neighbor = (current[0] + dx, current[1] + dz)
            if node_blocked(neighbor):
                continue
            if dx and dz:
                if node_blocked((current[0] + dx, current[1])) or node_blocked((current[0], current[1] + dz)):
                    continue
            next_cost = current_cost + move_cost
            if next_cost + 1e-9 >= costs.get(neighbor, math.inf):
                continue
            costs[neighbor] = next_cost
            came_from[neighbor] = current
            serial += 1
            heuristic = math.dist(neighbor, goal_node)
            heapq.heappush(frontier, (next_cost + heuristic, next_cost, serial, neighbor))
    return None


def _door_local_bounds(item: dict[str, Any]) -> tuple[float, float, float, float]:
    tangent_margin = item["width"] / 2 + 0.70
    normal_margin = DOOR_APPROACH_DISTANCE_METERS + 0.35
    if item["orientation"] == "along_x":
        return item["x"] - tangent_margin, item["x"] + tangent_margin, item["z"] - normal_margin, item["z"] + normal_margin
    return item["x"] - normal_margin, item["x"] + normal_margin, item["z"] - tangent_margin, item["z"] + tangent_margin


def _compress_path(path: list[tuple[float, float]] | None) -> list[dict[str, float]]:
    if not path:
        return []
    if len(path) <= 2:
        return [{"x": round(x, 3), "z": round(z, 3)} for x, z in path]
    kept = [path[0]]
    previous_direction: tuple[int, int] | None = None
    for index in range(1, len(path)):
        dx = round((path[index][0] - path[index - 1][0]) / PATH_GRID_METERS)
        dz = round((path[index][1] - path[index - 1][1]) / PATH_GRID_METERS)
        direction = (dx, dz)
        if previous_direction is not None and direction != previous_direction:
            kept.append(path[index - 1])
        previous_direction = direction
    kept.append(path[-1])
    return [{"x": round(x, 3), "z": round(z, 3)} for x, z in kept]


def _route_through_doors(
    scene: dict[str, Any],
    start_id: str,
    end_id: str,
    door_ids: list[str],
    *,
    reverse: bool = False,
) -> dict[str, Any]:
    targets = {item["id"]: item for item in scene["route_targets"]}
    doors = {item["id"]: item for item in scene["doors"]}
    missing_targets = [item_id for item_id in [start_id, end_id] if item_id not in targets]
    missing_doors = [item_id for item_id in door_ids if item_id not in doors]
    if missing_targets or missing_doors:
        return {
            "status": "failed_missing_route_definition",
            "missing_targets": missing_targets,
            "missing_doors": missing_doors,
            "path": [],
        }

    ordered_doors = list(reversed(door_ids)) if reverse else list(door_ids)
    all_open = {item["id"]: True for item in scene["doors"]}
    start_target = targets[end_id] if reverse else targets[start_id]
    end_target = targets[start_id] if reverse else targets[end_id]
    current = (start_target["x"], start_target["z"])
    full_path: list[tuple[float, float]] = [current]
    segments: list[dict[str, Any]] = []

    def append_path(path: list[tuple[float, float]]) -> None:
        full_path.extend(path[1:] if full_path and path and full_path[-1] == path[0] else path)

    for door_id in ordered_doors:
        item = doors[door_id]
        approach_id = item["to_target"] if reverse else item["from_target"]
        follow_id = item["from_target"] if reverse else item["to_target"]
        approach = (targets[approach_id]["x"], targets[approach_id]["z"])
        follow = (targets[follow_id]["x"], targets[follow_id]["z"])
        approach_path = astar_path(scene, current, approach, door_states=all_open)
        if approach_path is None:
            return {
                "status": "failed_no_path_to_door",
                "failed_door": door_id,
                "path": _compress_path(full_path),
                "segments": segments,
            }
        append_path(approach_path)
        crossing_path = astar_path(scene, approach, follow, door_states=all_open, bounds=_door_local_bounds(item))
        if crossing_path is None:
            return {
                "status": "failed_open_door_crossing",
                "failed_door": door_id,
                "path": _compress_path(full_path),
                "segments": segments,
            }
        append_path(crossing_path)
        segments.append({"door_id": door_id, "status": "passed_open_crossing"})
        current = follow

    final_point = (end_target["x"], end_target["z"])
    final_path = astar_path(scene, current, final_point, door_states=all_open)
    if final_path is None:
        return {
            "status": "failed_no_path_to_target",
            "path": _compress_path(full_path),
            "segments": segments,
        }
    append_path(final_path)
    return {
        "status": "passed_static_capsule_path",
        "distance_m": round(sum(math.dist(full_path[index - 1], full_path[index]) for index in range(1, len(full_path))), 3),
        "path": _compress_path(full_path),
        "segments": segments,
    }


def validate_static_routes(
    scene: dict[str, Any],
    avatar_radius: float = AVATAR_RADIUS_METERS,
) -> dict[str, Any]:
    aperture_failures = door_wall_overlaps(scene)
    clearance_failures = target_clearance_failures(scene, avatar_radius)
    targets = {item["id"]: item for item in scene["route_targets"]}
    all_open = {item["id"]: True for item in scene["doors"]}

    door_state_tests = []
    for item in scene["doors"]:
        from_target = targets[item["from_target"]]
        to_target = targets[item["to_target"]]
        start = (from_target["x"], from_target["z"])
        end = (to_target["x"], to_target["z"])
        open_path = astar_path(scene, start, end, avatar_radius=avatar_radius, door_states=all_open, bounds=_door_local_bounds(item))
        closed_states = dict(all_open)
        closed_states[item["id"]] = False
        closed_path = astar_path(scene, start, end, avatar_radius=avatar_radius, door_states=closed_states, bounds=_door_local_bounds(item))
        center_open_clear = not point_blocked(item["x"], item["z"], scene, avatar_radius=avatar_radius, door_states=all_open)
        center_closed_blocked = point_blocked(item["x"], item["z"], scene, avatar_radius=avatar_radius, door_states=closed_states)
        passed = open_path is not None and closed_path is None and center_open_clear and center_closed_blocked
        door_state_tests.append({
            "door_id": item["id"],
            "orientation": item["orientation"],
            "open_crossing": "passed" if open_path is not None else "failed",
            "closed_crossing": "blocked_as_expected" if closed_path is None else "failed_path_leaked_through_closed_door",
            "open_threshold_center": "clear" if center_open_clear else "blocked",
            "closed_threshold_center": "blocked_as_expected" if center_closed_blocked else "failed_clear_when_closed",
            "status": "passed" if passed else "failed",
        })

    route_rows = []
    for definition in scene["public_route_tests"]:
        forward = _route_through_doors(
            scene,
            "spa_front_door_outside",
            definition["target"],
            definition["via_doors"],
        )
        reverse_result = _route_through_doors(
            scene,
            "spa_front_door_outside",
            definition["target"],
            definition["via_doors"],
            reverse=True,
        )
        route_rows.append({
            "route_id": definition["route_id"],
            "target_id": definition["target"],
            "target_room": targets.get(definition["target"], {}).get("room"),
            "via_doors": definition["via_doors"],
            "forward": forward,
            "reverse": reverse_result,
            "status": "passed_round_trip" if forward["status"].startswith("passed") and reverse_result["status"].startswith("passed") else "failed_round_trip",
            "runtime_kira_test": "not_run",
        })

    public_rooms = {item["id"] for item in scene["rooms"] if item.get("public", True)}
    covered_rooms = {row["target_room"] for row in route_rows if row["target_room"]}
    uncovered_public_rooms = sorted(public_rooms - covered_rooms)
    failures: list[dict[str, Any]] = []
    failures.extend({"kind": "door_wall_overlap", **item} for item in aperture_failures)
    failures.extend({"kind": "target_clearance", **item} for item in clearance_failures)
    failures.extend({"kind": "door_state_semantics", "door_id": item["door_id"]} for item in door_state_tests if item["status"] != "passed")
    failures.extend({"kind": "public_round_trip", "route_id": item["route_id"]} for item in route_rows if item["status"] != "passed_round_trip")
    failures.extend({"kind": "uncovered_public_room", "room_id": room_id} for room_id in uncovered_public_rooms)
    static_passed = not failures
    return {
        "schema_version": 1,
        "created_at": now_iso(),
        "project_id": PROJECT_ID,
        "validation_method": {
            "type": "deterministic_2d_static_capsule_astar",
            "avatar_radius_m": avatar_radius,
            "grid_step_m": PATH_GRID_METERS,
            "solid_geometry": "derived wall segments plus invisible static collision-proxy AABBs",
            "door_geometry": "oriented leaf segment expanded by avatar radius and leaf half-thickness",
        },
        "static_validation_status": "passed" if static_passed else "failed",
        "status": "static_capsule_routes_passed_runtime_kira_test_not_run" if static_passed else "failed_static_capsule_validation",
        "door_wall_overlap_failures": aperture_failures,
        "target_clearance_failures": clearance_failures,
        "door_state_tests": door_state_tests,
        "round_trip_routes": route_rows,
        "public_room_coverage": {
            "required_rooms": sorted(public_rooms),
            "covered_rooms": sorted(covered_rooms),
            "uncovered_rooms": uncovered_public_rooms,
        },
        "failures": failures,
        "runtime_kira_test": "not_run",
        "ready_for_approval": False,
        "important_truth": "Static capsule routes are not a runtime Kira walk test. A not-run or failed runtime test can never make this preview ready for approval.",
    }


def canonical_blueprint(scene: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "project_id": PROJECT_ID,
        "status": "canonical_staged_blueprint_not_approved",
        "units": scene["units"],
        "footprint": scene["footprint"],
        "rooms": scene["rooms"],
        "wall_runs": scene["wall_runs"],
        "derived_wall_segments": scene["walls"],
        "doors": scene["doors"],
        "interaction_targets": scene["route_targets"],
        "public_round_trip_routes": scene["public_route_tests"],
        "real_prefab_instances": scene["asset_instances"],
        "static_collision_proxies": scene["collision_proxies"],
        "code_native_fixtures": scene["code_native_fixtures"],
        "missing_asset_roles": scene["missing_asset_roles"],
        "collision_profile": {
            "avatar_radius_m": AVATAR_RADIUS_METERS,
            "path_grid_m": PATH_GRID_METERS,
            "door_leaf_thickness_m": DOOR_LEAF_THICKNESS_METERS,
        },
        "placement_policy": {
            "home_world_imported": False,
            "requires_robert_approval": True,
            "requires_runtime_kira_route_test": True,
        },
    }


def nav_report(scene: dict[str, Any], ai_report: dict[str, Any] | None = None) -> dict[str, Any]:
    validation = ai_report or validate_static_routes(scene)
    static_passed = validation["static_validation_status"] == "passed"
    return {
        "schema_version": 2,
        "created_at": now_iso(),
        "project_id": PROJECT_ID,
        "status": "static_validation_passed_runtime_kira_test_not_run" if static_passed else "failed_static_validation",
        "static_validation_status": validation["static_validation_status"],
        "avatar_radius_m": AVATAR_RADIUS_METERS,
        "door_count": len(scene["doors"]),
        "door_state_tests_passed": sum(item["status"] == "passed" for item in validation["door_state_tests"]),
        "round_trip_routes_passed": sum(item["status"] == "passed_round_trip" for item in validation["round_trip_routes"]),
        "round_trip_routes_required": len(validation["round_trip_routes"]),
        "failures": validation["failures"],
        "runtime_kira_test": "not_run",
        "ready_for_approval": False,
        "interactive_door_preview": "Door panels have oriented clickable open/close state in the standalone preview. Runtime Home World scripts are not installed.",
        "important_truth": "This report records deterministic static collision results only. Kira has not physically walked these routes, Robert has not approved the build, and Home World was not changed.",
    }


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _prior_failed_review(previous_latest: dict[str, Any]) -> dict[str, Any] | None:
    carried = previous_latest.get("prior_failed_review")
    if isinstance(carried, dict):
        return carried
    previous_status = str(previous_latest.get("status", ""))
    review_path = previous_latest.get("robert_review")
    if "failed" not in previous_status and not review_path:
        return None
    return {
        "build_id": previous_latest.get("build_id"),
        "status": previous_status or "failed_review_recorded",
        "robert_review": review_path,
        "resolution": "unresolved_visual_realism_failure; structural repair does not erase this review",
    }


def _required_artifact_status(
    project_dir: Path,
    out_dir: Path,
    rubric: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = {
        "blueprint.md": project_dir / "blueprint.md",
        "blueprint.json": project_dir / "blueprint.json",
        "source_notes.md": project_dir / "source_notes.md",
        "standalone_preview_url_or_folder": out_dir / "index.html",
        "exterior_contact_sheet.png": out_dir / "exterior_contact_sheet.png",
        "interior_contact_sheet.png": out_dir / "interior_contact_sheet.png",
        "door_threshold_contact_sheet.png": out_dir / "door_threshold_contact_sheet.png",
        "nav_collision_report.json": out_dir / "nav_collision_report.json",
        "ai_route_test_report.json": out_dir / "ai_route_test_report.json",
        "asset_selection_report.json": out_dir / "asset_selection_report.json",
        "asset_credits.json": out_dir / "asset_credits.json",
        "missing_asset_report.json": out_dir / "missing_asset_report.json",
        "approval_gate.json": out_dir / "approval_gate.json",
    }
    required = list(rubric.get("required_artifacts") or candidates)
    for required_asset_report in (
        "asset_selection_report.json",
        "asset_credits.json",
        "missing_asset_report.json",
    ):
        if required_asset_report not in required:
            required.append(required_asset_report)
    rows = []
    for artifact in required:
        candidate = candidates.get(artifact)
        will_exist = artifact == "approval_gate.json"
        present = bool(candidate and (candidate.exists() or will_exist))
        rows.append({
            "artifact": artifact,
            "status": "present" if present else "missing",
            "path": rel(candidate) if candidate else None,
        })
    return rows


def build_preview_artifacts(
    out_dir: Path,
    *,
    project_dir: Path = PROJECT_DIR,
    build_id: str | None = None,
    update_latest: bool = False,
) -> dict[str, Any]:
    """Build staged artifacts and an honest gate without touching Home World."""

    build_id = build_id or out_dir.name
    previous_latest = read_json(project_dir / "latest_preview_build.json") if update_latest else {}
    prior_failed_review = _prior_failed_review(previous_latest)
    selection_report = build_asset_selection_report()
    credits_report = asset_credits(selection_report)
    unresolved_report = missing_asset_report(selection_report)
    scene = build_scene(selection_report)
    ai_report = validate_static_routes(scene)
    review_route = next(
        (item for item in ai_report["round_trip_routes"] if item["route_id"] == "outside_to_relaxation"),
        None,
    )
    scene["validated_review_route_points"] = review_route["forward"]["path"] if review_route else []

    blueprint = canonical_blueprint(scene)
    html = (
        HTML_TEMPLATE
        .replace("__SCENE_JSON__", json.dumps(scene, ensure_ascii=False))
        .replace("__THREE_MODULE_URL__", THREE_MODULE_URL)
        .replace("__THREE_ADDONS_URL__", THREE_ADDONS_URL)
    )
    write_text(out_dir / "index.html", html)
    write_json(out_dir / "scene_data.json", scene)
    write_floorplan_svg(out_dir / "floorplan.svg", scene)
    write_json(out_dir / "blueprint.json", blueprint)
    write_json(project_dir / "blueprint.json", blueprint)
    write_json(out_dir / "ai_route_test_report.json", ai_report)
    navigation = nav_report(scene, ai_report)
    write_json(out_dir / "nav_collision_report.json", navigation)
    write_json(out_dir / "asset_selection_report.json", selection_report)
    write_json(out_dir / "asset_credits.json", credits_report)
    write_json(out_dir / "missing_asset_report.json", unresolved_report)

    rubric = read_json(project_dir / "grade_rubric.json")
    artifact_rows = _required_artifact_status(project_dir, out_dir, rubric)
    missing_artifacts = [item["artifact"] for item in artifact_rows if item["status"] == "missing"]
    gate_failures: list[dict[str, Any]] = []
    if ai_report["static_validation_status"] != "passed":
        gate_failures.append({"kind": "static_collision_or_route_validation_failed", "details": ai_report["failures"]})
    if missing_artifacts:
        gate_failures.append({"kind": "missing_required_artifacts", "artifacts": missing_artifacts})
    if selection_report["missing_asset_roles"]:
        gate_failures.append({
            "kind": "missing_required_real_prefabs",
            "roles": [item["role"] for item in selection_report["missing_asset_roles"]],
            "fallback_visuals_created": False,
        })
    if prior_failed_review:
        gate_failures.append({"kind": "prior_failed_visual_realism_review_unresolved", "review": prior_failed_review})
    gate = {
        "schema_version": 2,
        "project_id": PROJECT_ID,
        "build_id": build_id,
        "created_at": now_iso(),
        "status": "not_approved",
        "world_builder_may_commit_to_home_world": False,
        "not_placed_in_home_world": True,
        "structural_static_validation": ai_report["static_validation_status"],
        "runtime_kira_route_test": "not_run",
        "visual_realism_review": "failed_prior_review_unresolved" if prior_failed_review else "not_run",
        "robert_approval": "not_granted",
        "required_artifacts": artifact_rows,
        "failures": gate_failures,
        "requirements": {
            "requires_robert_approval": True,
            "requires_runtime_kira_route_test": True,
            "requires_visual_contact_sheets": True,
            "requires_all_semantic_real_prefabs": True,
        },
        "important_truth": "A static pass cannot override a not-run runtime Kira route test, missing visual evidence, or Robert's unresolved failed realism review.",
    }
    if prior_failed_review:
        gate["prior_failed_review"] = prior_failed_review
    write_json(out_dir / "approval_gate.json", gate)

    contact_sheets_present = all(
        (out_dir / name).is_file()
        for name in (
            "exterior_contact_sheet.png",
            "interior_contact_sheet.png",
            "door_threshold_contact_sheet.png",
        )
    )
    browser_smoke_present = (out_dir / "browser_smoke_report.json").is_file()
    write_text(out_dir / "README.md", f"""# Legal Day Spa Preview

Build ID: `{build_id}`

This is a staged World Builder preview only. It is not placed in Home World.

Open through the local repo server:

`http://127.0.0.1:8890/{rel(out_dir / "index.html")}`

Structural static validation: `{ai_report["static_validation_status"]}` using a `{AVATAR_RADIUS_METERS:.2f} m` avatar radius.

Real prefab instances selected for browser loading: `{len(scene["asset_instances"])}` from `{len({item["source_url"] for item in scene["asset_instances"]})}` unique GLB sources.

Unresolved required real-asset roles: `{selection_report["missing_asset_count"]}`. They remain visually empty; no colored-block fallback is rendered.

Runtime Kira route test: `not_run`.

Robert approval: `not_granted`.

Visual contact sheets: `{"present" if contact_sheets_present else "not_captured"}`.

Browser loader/nonblank-canvas smoke report: `{"present" if browser_smoke_present else "not_captured"}`.

The preview remains not approved. Evidence files do not override missing real prefabs, the prior failed realism review, the not-run runtime Kira walk, or missing Robert approval.
""")

    latest = {
        "schema_version": 2,
        "project_id": PROJECT_ID,
        "build_id": build_id,
        "status": "staged_preview_not_approved",
        "created_at": now_iso(),
        "preview_folder": rel(out_dir),
        "preview_url": f"http://127.0.0.1:8890/{rel(out_dir / 'index.html')}",
        "scene_data": rel(out_dir / "scene_data.json"),
        "blueprint": rel(out_dir / "blueprint.json"),
        "canonical_blueprint": rel(project_dir / "blueprint.json"),
        "floorplan": rel(out_dir / "floorplan.svg"),
        "nav_collision_report": rel(out_dir / "nav_collision_report.json"),
        "ai_route_test_report": rel(out_dir / "ai_route_test_report.json"),
        "asset_selection_report": rel(out_dir / "asset_selection_report.json"),
        "asset_credits": rel(out_dir / "asset_credits.json"),
        "missing_asset_report": rel(out_dir / "missing_asset_report.json"),
        "approval_gate": rel(out_dir / "approval_gate.json"),
        "structural_static_validation": ai_report["static_validation_status"],
        "runtime_kira_route_test": "not_run",
        "robert_approval": "not_granted",
        "not_placed_in_home_world": True,
    }
    if prior_failed_review:
        latest["prior_failed_review"] = prior_failed_review
    optional_evidence = {
        "browser_smoke_report": out_dir / "browser_smoke_report.json",
        "browser_real_prefab_smoke": out_dir / "browser_real_prefab_smoke.png",
        "exterior_contact_sheet": out_dir / "exterior_contact_sheet.png",
        "interior_contact_sheet": out_dir / "interior_contact_sheet.png",
        "door_threshold_contact_sheet": out_dir / "door_threshold_contact_sheet.png",
    }
    for key, evidence_path in optional_evidence.items():
        if evidence_path.exists():
            latest[key] = rel(evidence_path)
    if update_latest:
        write_json(project_dir / "latest_preview_build.json", latest)
    return {
        "scene": scene,
        "blueprint": blueprint,
        "ai_route_test_report": ai_report,
        "nav_collision_report": navigation,
        "asset_selection_report": selection_report,
        "asset_credits": credits_report,
        "missing_asset_report": unresolved_report,
        "approval_gate": gate,
        "latest": latest,
    }


def main() -> int:
    build_id = f"spa_preview_{stamp()}"
    out_dir = PREVIEW_ROOT / build_id
    result = build_preview_artifacts(out_dir, build_id=build_id, update_latest=True)
    print(json.dumps(result["latest"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
