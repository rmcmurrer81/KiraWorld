"""Create source-labeled notebook world build requests.

This is a pre-GPU/request-mode tool. It prepares the files that Kira, Lisa,
Robert, or a later world builder can use without claiming a 3D world exists yet.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from validate_notebook_world_request import validate_notebook_world_request
except ModuleNotFoundError:  # Imported as tools.create_world_notebook_request.
    from tools.validate_notebook_world_request import validate_notebook_world_request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORLD_ROOT = PROJECT_ROOT / "Data" / "world_builds" / "notebook_worlds"
DEFAULT_INDEX_PATH = PROJECT_ROOT / "Data" / "world_builds" / "notebook_world_index.json"

ALLOWED_SOURCE_TYPES = [
    "official_site",
    "local_library",
    "web_search",
    "map_or_satellite_view",
    "street_level_photos",
    "public_photos",
    "public_video",
    "floor_plans",
    "blueprints",
    "measurements",
    "manual_notes",
    "style_or_era_references",
]

CONFIDENCE_LABELS = [
    "blueprint_confirmed",
    "photo_confirmed",
    "video_confirmed",
    "map_confirmed",
    "manual_note_confirmed",
    "inferred_from_sources",
    "style_fill",
    "unknown",
    "blocked_private",
]

ALLOWED_V2_CATEGORIES = {
    "real_place",
    "real_historic_place",
    "fictional_or_original_place",
    "fictional_place",
    "memory_place",
    "original_idea",
    "hybrid",
}
ALLOWED_REQUESTED_BY = {"robert", "kira", "lisa", "kira_lisa"}
ALLOWED_VISIBILITY = {"private_only", "share_with_robert", "public_export_candidate"}
ALLOWED_AUTONOMY = {"manual_only", "request_mode", "approved_autonomy", "mature_autonomy"}


@dataclass
class PlaceSeed:
    name: str
    category: str = "real_place"
    city: str = ""
    region: str = ""
    country: str = ""
    era: str = "current_or_best_sourced"
    notebook_world_id: str = ""
    notebook_title: str = ""
    latitude: float | None = None
    longitude: float | None = None
    starting_area: str = "main exterior approach"
    initial_scope: str = "small_prototype"
    collection_id: str = ""


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "notebook_world"


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
        if temporary is None:  # Defensive; NamedTemporaryFile should always supply a path.
            raise RuntimeError("Atomic write did not create a temporary file.")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        try:
            return str(path.resolve().relative_to(DEFAULT_WORLD_ROOT.parent.resolve())).replace("\\", "/")
        except ValueError:
            return str(path)


def normalized_project_relative(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or value.startswith("/"):
        return False
    parts = value.split("/")
    return all(part not in {"", ".", ".."} and ":" not in part for part in parts)


def validate_index_for_mutation(index: dict[str, Any]) -> None:
    if index.get("schema_version") != 1 or not isinstance(index.get("notebook_worlds"), dict):
        raise ValueError("Notebook-world index is malformed; refusing to mutate it.")
    request_ids: set[str] = set()
    for world_id, world in index["notebook_worlds"].items():
        if slugify(str(world_id)) != world_id or not str(world_id).endswith("_notebook_world"):
            raise ValueError(f"Notebook-world index contains an invalid world id: {world_id!r}")
        if not isinstance(world, dict) or not isinstance(world.get("anchors"), list):
            raise ValueError(f"Notebook-world index has an invalid anchor list: {world_id}")
        for anchor in world["anchors"]:
            if not isinstance(anchor, dict):
                raise ValueError(f"Notebook-world index contains a non-object anchor: {world_id}")
            request_id = str(anchor.get("request_id") or "")
            if not request_id or request_id in request_ids:
                raise ValueError(f"Notebook-world index contains a missing or duplicate request id: {request_id!r}")
            request_ids.add(request_id)
            if not normalized_project_relative(anchor.get("scene_folder")):
                raise ValueError(f"Notebook-world index contains an unsafe scene folder: {request_id}")


def validate_generator_inputs(
    seed: PlaceSeed,
    requested_by: str,
    trigger: str,
    visibility: str,
    autonomy: str,
    status: str,
) -> None:
    if not seed.name.strip():
        raise ValueError("A non-empty place or world subject name is required.")
    if slugify(seed.notebook_world_id) != seed.notebook_world_id or not seed.notebook_world_id.endswith("_notebook_world"):
        raise ValueError("notebook_world_id must be a normalized *_notebook_world identifier.")
    if not seed.notebook_title.strip():
        raise ValueError("A notebook-world title is required.")
    if seed.category not in ALLOWED_V2_CATEGORIES:
        raise ValueError(f"Unsupported notebook-world category: {seed.category!r}")
    if bool(seed.latitude is None) != bool(seed.longitude is None):
        raise ValueError("Latitude and longitude must be supplied together.")
    if seed.latitude is not None and not -90 <= seed.latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90.")
    if seed.longitude is not None and not -180 <= seed.longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180.")
    if seed.collection_id and slugify(seed.collection_id) != seed.collection_id:
        raise ValueError("collection_id must be a normalized identifier.")
    if requested_by not in ALLOWED_REQUESTED_BY:
        raise ValueError(f"Unsupported requester: {requested_by!r}")
    if not trigger.strip():
        raise ValueError("A non-empty request trigger summary is required.")
    if visibility not in ALLOWED_VISIBILITY:
        raise ValueError("Generated drafts cannot self-declare public approval.")
    if autonomy not in ALLOWED_AUTONOMY:
        raise ValueError(f"Unsupported autonomy level: {autonomy!r}")
    if status != "draft":
        raise ValueError("The request generator is draft-only; promotion requires a separate approval artifact.")


def infer_seed(name: str, city: str = "", era: str = "", category: str = "real_place") -> PlaceSeed:
    value = f"{name} {city} {era}".lower()
    seed = PlaceSeed(name=name.strip(), category=category, city=city.strip(), era=era.strip() or "current_or_best_sourced")
    if category != "memory_place" and ("college campus" in value or "learning campus" in value):
        seed.city = seed.city or "Standalone Learning Campus"
        seed.region = "Education Notebook Collection"
        seed.country = "Virtual"
        seed.notebook_world_id = "college_campus_core_notebook_world"
        seed.notebook_title = "College Campus Core Notebook World"
        seed.category = "original_idea"
        seed.starting_area = "campus arrival court, student union lobby, and library approach"
        seed.initial_scope = "campus_core_prototype"
        seed.collection_id = "education_notebook_collection"
    elif "louvre" in value:
        seed.city = seed.city or "Paris"
        seed.region = "Ile-de-France"
        seed.country = "France"
        seed.notebook_world_id = "paris_notebook_world"
        seed.notebook_title = "Paris Notebook World"
        seed.latitude = 48.8606
        seed.longitude = 2.3376
        seed.starting_area = "Cour Napoleon and Louvre Pyramid exterior prototype"
        seed.initial_scope = "courtyard_prototype"
    elif "paris" in value:
        seed.city = seed.city or "Paris"
        seed.region = "Île-de-France"
        seed.country = "France"
        seed.notebook_world_id = "paris_notebook_world"
        seed.notebook_title = "Paris Notebook World"
    elif "brown derby" in value:
        seed.city = seed.city or "Los Angeles"
        seed.region = "California"
        seed.country = "United States"
        seed.era = seed.era if seed.era != "current_or_best_sourced" else "1930s"
        seed.notebook_world_id = "los_angeles_1930s_notebook_world"
        seed.notebook_title = "1930s Los Angeles Notebook World"
        seed.category = "real_historic_place"
        seed.starting_area = "street exterior and restaurant entrance prototype"
        seed.initial_scope = "facade_and_entry_prototype"
    elif "los angeles" in value or "hollywood" in value:
        seed.city = seed.city or "Los Angeles"
        seed.region = "California"
        seed.country = "United States"
        seed.notebook_world_id = f"los_angeles_{slugify(seed.era)}_notebook_world"
        seed.notebook_title = f"{seed.era.title()} Los Angeles Notebook World"
    else:
        world_base = slugify(seed.city or seed.name)
        seed.notebook_world_id = f"{world_base}_notebook_world"
        seed.notebook_title = f"{(seed.city or seed.name).strip()} Notebook World"
    return seed


def apply_seed_overrides(
    seed: PlaceSeed,
    *,
    notebook_world_id: str = "",
    notebook_title: str = "",
    region: str = "",
    country: str = "",
    starting_area: str = "",
    initial_scope: str = "",
) -> PlaceSeed:
    """Apply explicit generic request fields without adding place-specific code.

    Inference remains useful for known test locations, while original notebook
    worlds can now declare their own isolated identity and small starting slice.
    Normal strict-v2 validation still runs before any file or index mutation.
    """

    if notebook_world_id:
        seed.notebook_world_id = notebook_world_id.strip()
    if notebook_title:
        seed.notebook_title = notebook_title.strip()
    if region:
        seed.region = region.strip()
    if country:
        seed.country = country.strip()
    if starting_area:
        seed.starting_area = starting_area.strip()
    if initial_scope:
        seed.initial_scope = initial_scope.strip()
    return seed


def haversine_meters(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    radius = 6_371_000.0
    phi1 = math.radians(a_lat)
    phi2 = math.radians(b_lat)
    d_phi = math.radians(b_lat - a_lat)
    d_lambda = math.radians(b_lon - a_lon)
    value = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def placement_for(seed: PlaceSeed, index: dict[str, Any]) -> dict[str, Any]:
    world = index.get("notebook_worlds", {}).get(seed.notebook_world_id, {})
    anchors = world.get("anchors", []) if isinstance(world.get("anchors"), list) else []
    approved_anchors = [
        anchor
        for anchor in anchors
        if isinstance(anchor, dict)
        and anchor.get("status") in {"approved", "active"}
        and anchor.get("placement_approved") is True
    ]
    candidate_anchor_count = len(anchors) - len(approved_anchors)
    if seed.latitude is None or seed.longitude is None or not approved_anchors:
        return {
            "placement_status": (
                "coordinates_known_no_approved_anchor"
                if seed.latitude is not None and seed.longitude is not None and anchors
                else "first_anchor_or_coordinates_needed"
            ),
            "notebook_world_id": seed.notebook_world_id,
            "real_world_coordinates": {"latitude": seed.latitude, "longitude": seed.longitude},
            "local_scene_offset_meters": {"x": 0, "z": 0},
            "nearest_existing_anchor": None,
            "distance_from_nearest_anchor_meters": None,
            "truth_label": "map_confirmed" if seed.latitude is not None and seed.longitude is not None else "unknown",
            "unapproved_candidate_anchors_ignored": candidate_anchor_count,
            "commit_rule": "Draft/catalog anchors cannot become coordinate origins until a separate placement approval marks placement_approved=true.",
        }
    nearest: dict[str, Any] | None = None
    nearest_distance = float("inf")
    for anchor in approved_anchors:
        coords = anchor.get("real_world_coordinates", {})
        lat = coords.get("latitude")
        lon = coords.get("longitude")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            distance = haversine_meters(seed.latitude, seed.longitude, float(lat), float(lon))
            if distance < nearest_distance:
                nearest = anchor
                nearest_distance = distance
    if not nearest:
        return {
            "placement_status": "coordinates_known_no_comparable_anchor",
            "notebook_world_id": seed.notebook_world_id,
            "real_world_coordinates": {"latitude": seed.latitude, "longitude": seed.longitude},
            "local_scene_offset_meters": {"x": 0, "z": 0},
            "nearest_existing_anchor": None,
            "distance_from_nearest_anchor_meters": None,
            "truth_label": "map_confirmed",
            "unapproved_candidate_anchors_ignored": candidate_anchor_count,
        }
    coords = nearest["real_world_coordinates"]
    meters_per_degree_lat = 111_320.0
    meters_per_degree_lon = 111_320.0 * math.cos(math.radians(seed.latitude))
    return {
        "placement_status": "placed_relative_to_existing_anchor",
        "notebook_world_id": seed.notebook_world_id,
        "real_world_coordinates": {"latitude": seed.latitude, "longitude": seed.longitude},
        "local_scene_offset_meters": {
            "x": round((seed.longitude - coords["longitude"]) * meters_per_degree_lon, 2),
            "z": round((seed.latitude - coords["latitude"]) * meters_per_degree_lat, 2),
        },
        "nearest_existing_anchor": {
            "request_id": nearest.get("request_id"),
            "name": nearest.get("name"),
            "scene_folder": nearest.get("scene_folder"),
        },
        "distance_from_nearest_anchor_meters": round(nearest_distance, 2),
        "truth_label": "map_confirmed",
        "unapproved_candidate_anchors_ignored": candidate_anchor_count,
    }


def source_tasks_for(seed: PlaceSeed) -> list[dict[str, Any]]:
    tasks = [
        {
            "task_id": "official_overview",
            "goal": "Find official or high-trust overview pages for names, dates, access points, and landmark descriptions.",
            "preferred_sources": ["official_site", "institutional_archive"],
            "output": "source_notes.md",
            "truth_labels_created": ["manual_note_confirmed"],
        },
        {
            "task_id": "measurements_and_scale",
            "goal": "Collect dimensions for courtyards, facades, rooms, major structures, or known footprints.",
            "preferred_sources": ["official_site", "architecture_archive", "blueprints", "maps"],
            "output": "measurements.json",
            "truth_labels_created": ["blueprint_confirmed", "map_confirmed", "inferred_from_sources"],
        },
        {
            "task_id": "exterior_reference_board",
            "goal": "Collect exterior reference images from multiple angles without treating a single photo as complete truth.",
            "preferred_sources": ["official_site", "public_photos", "street_level_photos"],
            "output": "asset_manifest.json",
            "truth_labels_created": ["photo_confirmed"],
        },
        {
            "task_id": "community_photo_intake",
            "goal": "Find crowd-posted and third-party location photos from galleries, travel sites, blogs, archives, and map/street-level sources; review license, date, angle, and reliability before local download or texture use.",
            "preferred_sources": ["public_photo_gallery", "travel_blog", "architecture_site", "map_or_satellite_view", "street_level_photos", "public_video"],
            "output": "public_photo_reference_board.json",
            "truth_labels_created": ["photo_confirmed", "video_confirmed", "inferred_from_sources"],
        },
        {
            "task_id": "interior_or_hidden_area_boundaries",
            "goal": "Mark interiors, service corridors, restricted areas, or missing views as unknown unless sourced.",
            "preferred_sources": ["floor_plans", "public_video", "manual_notes"],
            "output": "scene_plan.json",
            "truth_labels_created": ["unknown", "blocked_private"],
        },
        {
            "task_id": "era_and_style_context",
            "goal": "Capture material, signage, lighting, clothing, vehicles, street furniture, and atmosphere appropriate to the requested era.",
            "preferred_sources": ["style_or_era_references", "local_library", "public_photos"],
            "output": "builder_notes.md",
            "truth_labels_created": ["style_fill", "inferred_from_sources"],
        },
    ]
    if seed.category == "real_historic_place" or re.search(r"\b(19|18|17)\d0s\b", seed.era):
        tasks.append(
            {
                "task_id": "historic_variant_check",
                "goal": "Separate current location evidence from era-specific evidence so the notebook world does not mix time periods accidentally.",
                "preferred_sources": ["historic_photos", "newspaper_archive", "city_archive", "manual_notes"],
                "output": "historic_evidence_matrix.json",
                "truth_labels_created": ["photo_confirmed", "style_fill", "unknown"],
            }
        )
    return tasks


def blueprint_preview_for(seed: PlaceSeed, request_id: str, placement: dict[str, Any], index: dict[str, Any], world_root: Path) -> dict[str, Any]:
    world = index.get("notebook_worlds", {}).get(seed.notebook_world_id, {})
    anchors = world.get("anchors", []) if isinstance(world.get("anchors"), list) else []
    return {
        "schema_version": 1,
        "request_id": request_id,
        "notebook_world_id": seed.notebook_world_id,
        "subject": {
            "name": seed.name,
            "category": seed.category,
            "city": seed.city,
            "era": seed.era,
        },
        "approval_policy": {
            "status": "draft_not_placed",
            "auto_place_in_existing_world": False,
            "robert_approval_required_before_commit": True,
            "approval_required_for": [
                "world/notebook selection",
                "map/blueprint placement",
                "scale and footprint",
                "first exterior/room preview",
                "final commit into the selected separate notebook world",
            ],
        },
        "review_flow": [
            "collect/source-label references",
            "produce blueprint/map placement preview",
            "produce isolated exterior or small-scene preview",
            "stage walkable review version in the TARDIS builder bay",
            "wait for Robert approval",
            "commit to the selected separate notebook world only after approval",
        ],
        "preview_requirements": {
            "building": "show exterior massing/facade preview before any import",
            "new_notebook_world": "show one small walkable prototype area before any full map work",
            "existing_world_addition": "show blueprint placement against current world anchors before import",
        },
        "placement_preview": placement,
        "known_world_anchors": [
            {
                "name": anchor.get("name"),
                "request_id": anchor.get("request_id"),
                "scene_folder": anchor.get("scene_folder"),
                "coordinates": anchor.get("real_world_coordinates"),
            }
            for anchor in anchors[-12:]
            if isinstance(anchor, dict)
        ],
        "files": {
            "blueprint_map": relative(world_root / "blueprint_map.md"),
            "tardis_review_stage": relative(world_root / "tardis_review_stage.json"),
            "approval_gate": relative(world_root / "approval_gate.json"),
        },
    }


def blueprint_map_text(seed: PlaceSeed, preview: dict[str, Any]) -> str:
    anchors = preview.get("known_world_anchors", [])
    placement = preview.get("placement_preview", {})
    lines = [
        f"# {seed.name} Blueprint / Placement Preview",
        "",
        "Status: draft only. Do not place in the target world until Robert approves.",
        "",
        f"- Target notebook world: `{seed.notebook_world_id}`",
        f"- Starting area: `{seed.starting_area}`",
        f"- Placement status: `{placement.get('placement_status', 'unknown')}`",
        f"- Local offset meters: `{placement.get('local_scene_offset_meters', {})}`",
        "",
        "## Approval Flow",
        "",
        "1. Review sources and blueprint/map placement.",
        "2. Review an isolated exterior or small-scene preview.",
        "3. Walk the staged preview inside the TARDIS builder bay.",
        "4. Approve or request changes.",
        "5. Only then commit it into the selected separate notebook world.",
        "",
        "## Nearby / Existing Anchors",
        "",
    ]
    if anchors:
        for anchor in anchors:
            lines.append(f"- {anchor.get('name') or 'unnamed'}: `{anchor.get('scene_folder') or 'no folder'}`")
    else:
        lines.append("- No existing anchors are known for this notebook world yet.")
    lines.extend([
        "",
        "## Preview Sketch",
        "",
        "```text",
        "          north / +z",
        "              ^",
        "              |",
        "   existing anchors / map references",
        "              |",
        "      [ proposed draft footprint ]",
        "              |",
        " Robert approval gate before import",
        "```",
        "",
    ])
    return "\n".join(lines)


def create_files(seed: PlaceSeed, requested_by: str, trigger: str, visibility: str, autonomy: str, status: str) -> dict[str, Path]:
    validate_generator_inputs(seed, requested_by, trigger, visibility, autonomy, status)
    stamp = now_stamp()
    place_slug = slugify(seed.name)
    request_id = f"notebook_world_{place_slug}_{stamp}"
    world_root = DEFAULT_WORLD_ROOT / seed.notebook_world_id / "builds" / request_id
    index = read_json(DEFAULT_INDEX_PATH, {"schema_version": 1, "notebook_worlds": {}})
    if not isinstance(index, dict):
        raise ValueError("Notebook-world index must be a JSON object.")
    validate_index_for_mutation(index)
    if world_root.exists():
        raise FileExistsError(f"Refusing to overwrite an existing request folder: {world_root}")
    known_request_ids = {
        str(anchor.get("request_id"))
        for world in index["notebook_worlds"].values()
        for anchor in world.get("anchors", [])
        if isinstance(anchor, dict)
    }
    if request_id in known_request_ids:
        raise ValueError(f"Request id already exists in the notebook-world index: {request_id}")
    placement = placement_for(seed, index)

    original_categories = {"original_idea", "fictional_or_original_place", "fictional_place"}
    if seed.category in original_categories:
        creation_mode = "original_creation"
    elif seed.category == "memory_place":
        creation_mode = "memory_reconstruction"
    else:
        creation_mode = "source_reconstruction"

    quality_gates = {
        "source_evidence": "not_run",
        "scale_and_placement": "not_run",
        "doors_routes_and_collision": "not_run",
        "visual_realism": "not_run",
        "runtime_route": "blocked",
        "pinned_deployment": "blocked",
        "explicit_robert_approval": "blocked",
    }

    request = {
        "schema_version": 2,
        "request_id": request_id,
        "request_type": "notebook_world",
        "title": f"{seed.name} - {seed.notebook_title}",
        "requested_by": requested_by,
        "trigger": {
            "source": "world_generator_request",
            "summary": trigger,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "subject": {
            "name": seed.name,
            "category": seed.category,
            "city": seed.city,
            "region": seed.region,
            "country": seed.country,
            "era": seed.era,
            "private_use_allowed": True,
            "public_export_requires_review": True,
        },
        "source_collection_plan": {
            "allowed_source_types": ALLOWED_SOURCE_TYPES,
            "requires_robert_approval_now": True,
            "auto_collection_allowed_later": False,
            "download_policy": "record_source_leads_first_download_only_after_review",
            "source_tasks_path": relative(world_root / "source_tasks.json"),
        },
        "creation_mode": {
            "mode": creation_mode,
            "starts_from_blank": creation_mode == "original_creation",
            "description": (
                "Build an original environment from a blank notebook-world scene."
                if creation_mode == "original_creation"
                else "Reconstruct only what approved sources or consented memories support."
            ),
        },
        "access_gateway": {
            "gateway_id": "tardis_notebook_world_gateway",
            "entry_location": "outside_protected_home_world",
            "selection_method": "interior_console",
        },
        "world_plan": {
            "notebook_world_id": seed.notebook_world_id,
            "notebook_world_title": seed.notebook_title,
            "starting_area": seed.starting_area,
            "initial_scope": seed.initial_scope,
            "confirmed_zones": [],
            "inferred_zones": ["approach paths and surrounding scene massing after maps/photos are reviewed"],
            "unknown_zones": ["interiors, service spaces, rear elevations, and any area not visible in approved references"],
            "npc_policy": "generic",
            "ride_or_attraction_policy": "none",
            "truth_labels": CONFIDENCE_LABELS,
            "placement_path": relative(world_root / "placement.json"),
            "scene_plan_path": relative(world_root / "scene_plan.json"),
            "blueprint_preview_path": relative(world_root / "blueprint_preview.json"),
            "tardis_review_stage_path": relative(world_root / "tardis_review_stage.json"),
            "quality_gate_path": relative(world_root / "quality_gate.json"),
            "resource_isolation_gate_path": relative(world_root / "resource_isolation_gate.json"),
            "collection_id": seed.collection_id or None,
        },
        "approval_workflow": {
            "auto_place_in_existing_world": False,
            "robert_approval_required_before_commit": True,
            "current_stage": "draft_request_only",
            "review_location": "TARDIS builder review bay",
            "required_previews_before_approval": [
                "blueprint/map placement",
                "isolated exterior or representative room preview",
                "walkable TARDIS review stage",
            ],
        },
        "isolation_policy": {
            "world_class": "separate_notebook_world",
            "home_world_import_requested": False,
            "home_world_mutation_allowed": False,
            "strip_mall_mutation_allowed": False,
            "co_load_with_home_world": False,
            "co_load_with_other_notebook_worlds": False,
            "runtime_load_policy": "one_notebook_world_at_a_time",
            "collection_id": seed.collection_id or None,
            "collection_members_are_logical_not_co_loaded": True,
        },
        "resource_policy": {
            "hardware_profile": "Data/launch/hardware_capability_profile.json",
            "current_decision": "request_paperwork_only_no_runtime",
            "loads_kira_mind": False,
            "loads_kira_body": False,
            "loads_voice": False,
            "loads_ollama": False,
            "loads_second_person": False,
            "future_preview_policy": "isolated_preview_only_one_heavy_workload_at_a_time",
        },
        "quality_gates": quality_gates,
        "visibility_scope": visibility,
        "autonomy_level_required": autonomy,
        "status": status,
    }

    scene_plan = {
        "schema_version": 1,
        "request_id": request_id,
        "scene_id": f"scene_{place_slug}",
        "renderer_target": "threejs_notebook_world",
        "units": "meters",
        "coordinate_policy": "local_scene_offsets_are_derived_from_real_world_coordinates_when_available",
        "placement": placement,
        "build_layers": [
            {"layer": "terrain_or_ground_plane", "status": "placeholder", "truth_label": "style_fill"},
            {"layer": "primary_exterior_mass", "status": "waiting_for_sources", "truth_label": "unknown"},
            {"layer": "major_landmarks", "status": "waiting_for_sources", "truth_label": "unknown"},
            {"layer": "walkable_paths", "status": "waiting_for_maps", "truth_label": "unknown"},
            {"layer": "lighting_and_atmosphere", "status": "draft_after_reference_review", "truth_label": "style_fill"},
        ],
        "do_not_claim": [
            "Do not claim exact dimensions unless the measurement source is recorded.",
            "Do not fill hidden interiors as source-confirmed.",
            "Do not import into the protected home world without review.",
            "Do not treat a draft index anchor as an approved coordinate origin.",
        ],
        "approval_gate": {
            "auto_place_in_existing_world": False,
            "robert_approval_required_before_commit": True,
            "preview_before_commit": True,
        },
    }

    blueprint_preview = blueprint_preview_for(seed, request_id, placement, index, world_root)
    approval_gate = {
        "schema_version": 1,
        "request_id": request_id,
        "status": "draft_not_approved",
        "world_builder_may_build_preview": False,
        "preview_build_requires_separate_resource_gate": True,
        "world_builder_may_commit_to_world": False,
        "world_builder_may_import_to_home_world": False,
        "world_builder_may_mutate_strip_mall": False,
        "requires_robert_approval": True,
        "approval_notes": "",
    }
    quality_gate = {
        "schema_version": 1,
        "request_id": request_id,
        "status": "draft_all_gates_unmet",
        "world_builder_may_commit_to_world": False,
        "gates": quality_gates,
        "promotion_rule": "Each gate needs its own evidence artifact; request creation cannot pass a gate.",
    }
    resource_isolation_gate = {
        "schema_version": 1,
        "request_id": request_id,
        "status": "paperwork_only_no_runtime",
        "hardware_profile": "Data/launch/hardware_capability_profile.json",
        "observed_ram_gb": 32,
        "hardware_stage": "stage_16gb_gpu_bridge",
        "max_concurrent_notebook_worlds": 1,
        "notebook_world_runtime_started": False,
        "loads_home_world": False,
        "loads_kira_mind": False,
        "loads_kira_body": False,
        "loads_voice": False,
        "loads_ollama": False,
        "loads_second_person": False,
        "co_load_collection_members": False,
        "home_world_merge_allowed": False,
        "strip_mall_mutation_allowed": False,
        "next_runtime_gate": "Run a separate resource check immediately before an isolated preview; never infer runtime approval from this draft.",
    }
    tardis_review_stage = {
        "schema_version": 1,
        "request_id": request_id,
        "stage_name": f"TARDIS review bay - {seed.name}",
        "status": "preview_required_not_built",
        "purpose": "When a 3D preview is ready, stage it here for Robert to walk around before committing it to a world.",
        "allowed_preview_types": ["exterior_massing", "single_room_slice", "small_walkable_world_slice"],
        "commit_rule": "Never import into Home World; commit only to this separate notebook world after all gates and Robert approval pass.",
    }

    source_tasks = {
        "schema_version": 1,
        "request_id": request_id,
        "place": seed.__dict__,
        "tasks": source_tasks_for(seed),
        "source_leads": [],
    }

    source_notes = f"""# {seed.name} Source Notes

Status: source leads created, source download/reconstruction pending review.

Notebook world: {seed.notebook_title}
Era: {seed.era}
Visibility: {visibility}

## Truth Rules

- Confirm measurements only when a cited source gives dimensions or a map/blueprint supports scale.
- Treat photos as angle-specific evidence, not complete layouts.
- Mark unseen areas as `unknown`.
- Mark decorative era fill as `style_fill`.
- Keep this as a private notebook world unless Robert approves wider export.

## Initial Source Leads

Add official pages, map references, public photo sets, videos, floor plans, blueprints, and manual notes here before asset intake.
"""

    builder_notes = f"""# {seed.name} Builder Notes

This folder is a request-mode notebook world draft. It prepares a future Three.js world; it does not claim the world already exists.

## First Build Goal

Create a small, walkable prototype of `{seed.starting_area}` with source labels visible in metadata.

## Placement Idea

`{seed.name}` is proposed for `{seed.notebook_title}`. This draft anchor cannot be used as a coordinate origin until a separate placement approval marks it approved.
"""

    request_errors = validate_notebook_world_request(request)
    if request_errors:
        formatted = "\n- ".join(request_errors)
        raise ValueError(f"Generated notebook-world request failed schema validation:\n- {formatted}")

    write_json(world_root / "notebook_world_request.json", request)
    write_json(world_root / "scene_plan.json", scene_plan)
    write_json(world_root / "placement.json", placement)
    write_json(world_root / "source_tasks.json", source_tasks)
    write_json(world_root / "blueprint_preview.json", blueprint_preview)
    write_json(world_root / "approval_gate.json", approval_gate)
    write_json(world_root / "quality_gate.json", quality_gate)
    write_json(world_root / "resource_isolation_gate.json", resource_isolation_gate)
    write_json(world_root / "tardis_review_stage.json", tardis_review_stage)
    write_text(world_root / "blueprint_map.md", blueprint_map_text(seed, blueprint_preview))
    write_text(world_root / "source_notes.md", source_notes)
    write_text(world_root / "builder_notes.md", builder_notes)

    worlds = index.setdefault("notebook_worlds", {})
    world = worlds.setdefault(
        seed.notebook_world_id,
        {
            "title": seed.notebook_title,
            "city": seed.city,
            "region": seed.region,
            "country": seed.country,
            "era": seed.era,
            "anchors": [],
        },
    )
    anchors = world.setdefault("anchors", [])
    anchors.append(
        {
            "request_id": request_id,
            "name": seed.name,
            "category": seed.category,
            "era": seed.era,
            "scene_folder": relative(world_root),
            "real_world_coordinates": {"latitude": seed.latitude, "longitude": seed.longitude},
            "created_at": request["trigger"]["created_at"],
            "status": "draft_request_only",
            "requested_status": status,
            "placement_approved": False,
            "runtime_registered": False,
            "collection_id": seed.collection_id or None,
        }
    )
    write_json(DEFAULT_INDEX_PATH, index)

    return {
        "world_root": world_root,
        "request": world_root / "notebook_world_request.json",
        "scene_plan": world_root / "scene_plan.json",
        "placement": world_root / "placement.json",
        "blueprint_preview": world_root / "blueprint_preview.json",
        "blueprint_map": world_root / "blueprint_map.md",
        "approval_gate": world_root / "approval_gate.json",
        "quality_gate": world_root / "quality_gate.json",
        "resource_isolation_gate": world_root / "resource_isolation_gate.json",
        "tardis_review_stage": world_root / "tardis_review_stage.json",
        "source_tasks": world_root / "source_tasks.json",
        "index": DEFAULT_INDEX_PATH,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a source-labeled notebook world request.")
    parser.add_argument("name", help="Place or world subject name.")
    parser.add_argument("--city", default="")
    parser.add_argument("--era", default="")
    parser.add_argument("--category", default="real_place")
    parser.add_argument("--requested-by", default="robert", choices=["robert", "kira", "lisa", "kira_lisa"])
    parser.add_argument("--trigger", default="Robert requested a place-based notebook world generator draft.")
    parser.add_argument("--visibility", default="private_only", choices=["private_only", "share_with_robert", "public_export_candidate"])
    parser.add_argument("--autonomy", default="request_mode", choices=["manual_only", "request_mode", "approved_autonomy", "mature_autonomy"])
    parser.add_argument("--status", default="draft", choices=["draft"])
    parser.add_argument("--collection-id", default="", help="Optional logical collection id; collection members must still load sequentially.")
    parser.add_argument("--notebook-world-id", default="", help="Explicit normalized *_notebook_world id for an original/generic request.")
    parser.add_argument("--notebook-title", default="", help="Explicit notebook-world title.")
    parser.add_argument("--region", default="")
    parser.add_argument("--country", default="")
    parser.add_argument("--starting-area", default="", help="Small first review area; still draft-only.")
    parser.add_argument("--initial-scope", default="", help="Normalized description of the first bounded prototype slice.")
    parser.add_argument("--lat", type=float, default=None)
    parser.add_argument("--lon", type=float, default=None)
    args = parser.parse_args()

    seed = infer_seed(args.name, city=args.city, era=args.era, category=args.category)
    apply_seed_overrides(
        seed,
        notebook_world_id=args.notebook_world_id,
        notebook_title=args.notebook_title,
        region=args.region,
        country=args.country,
        starting_area=args.starting_area,
        initial_scope=args.initial_scope,
    )
    if args.lat is not None:
        seed.latitude = args.lat
    if args.lon is not None:
        seed.longitude = args.lon
    if args.collection_id:
        seed.collection_id = args.collection_id
    paths = create_files(seed, args.requested_by, args.trigger, args.visibility, args.autonomy, args.status)
    print(json.dumps({key: relative(path) for key, path in paths.items()}, indent=2))


if __name__ == "__main__":
    main()
