"""Fail-closed backend for lightweight strict-v2 notebook-world previews.

The request generator remains draft-only.  This module consumes a separately
authorized, exact-hash-bound procedural scene program and emits one immutable
preview build.  It never promotes a request, registers a runtime, or mutates
Home World.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

try:
    from notebook_world_integrity import canonical_json_sha256, sha256_file
    from validate_notebook_world_request import VALID_TRUTH_LABELS, validate_notebook_world_request
except ModuleNotFoundError:  # Imported as tools.notebook_world_preview_backend.
    from tools.notebook_world_integrity import canonical_json_sha256, sha256_file
    from tools.validate_notebook_world_request import VALID_TRUTH_LABELS, validate_notebook_world_request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORLD_ROOT = PROJECT_ROOT / "Data" / "world_builds" / "notebook_worlds"
INDEX_PATH = PROJECT_ROOT / "Data" / "world_builds" / "notebook_world_index.json"
TEMPLATE_ROOT = (
    PROJECT_ROOT
    / "Data"
    / "world_builder"
    / "preview_runtime"
    / "procedural_notebook_preview_v1"
)
THREE_MODULE = (
    PROJECT_ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "home_world"
    / "builds"
    / "home_world_main_house_20260630_223000"
    / "preview"
    / "node_modules"
    / "three"
    / "build"
    / "three.module.js"
)
THREE_CORE = THREE_MODULE.with_name("three.core.js")

BACKEND_ID = "strict_v2_procedural_preview_lane_v1"
PROGRAM_KIND = "strict_v2_procedural_notebook_world_preview"
AUTHORIZATION_KIND = "notebook_world_preview_scope_authorization"
AUTHORIZATION_STATUS = "authorized_for_isolated_prototype_preview_only"
BUILD_STATUS = "prototype_draft_not_final_not_approved"
_ID_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

HARD_BUDGET = {
    "max_meshes": 160,
    "max_materials": 32,
    "max_lights": 5,
    "max_triangles": 50_000,
    "max_colliders": 128,
    "max_routes": 24,
    "max_route_points": 320,
    "max_rooms": 12,
    "max_spawns": 16,
    "max_cameras": 20,
    "max_filming_marks": 32,
    "max_overlays": 12,
    "max_generated_payload_bytes": 2_500_000,
}

PROGRAM_KEYS = {
    "schema_version",
    "program_kind",
    "world_id",
    "request_id",
    "status",
    "title",
    "subtitle",
    "units",
    "world_bounds",
    "scene_budget",
    "environment",
    "materials",
    "lights",
    "primitives",
    "rooms",
    "colliders",
    "support_surfaces",
    "spawns",
    "cameras",
    "filming_marks",
    "routes",
    "overlays",
    "isolation",
    "source_notes",
}

AUTHORIZATION_KEYS = {
    "schema_version",
    "authorization_kind",
    "status",
    "authorized_by",
    "authorized_at",
    "scope_statement",
    "world_id",
    "request_id",
    "request_binding",
    "program_binding",
    "builder_backend",
    "allowed_build_id",
    "authorized_actions",
    "limits",
}

REQUIRED_BUILD_ROLES = {
    "registration",
    "notebook_request",
    "preview_scope_authorization",
    "procedural_scene_program",
    "notebook_approval_gate",
    "notebook_quality_gate",
    "notebook_resource_gate",
    "tardis_review_metadata",
    "entry_html",
    "entry_javascript",
    "entry_stylesheet",
    "scene_metadata",
    "collision_nav_metadata",
    "source_truth_metadata",
    "resource_budget_metadata",
    "build_status_metadata",
    "three_runtime",
    "three_core_runtime",
}


class PreviewBuildError(ValueError):
    """Raised before a preview is committed when any contract diverges."""


@dataclass(frozen=True)
class PreviewBuildResult:
    world_id: str
    request_id: str
    build_id: str
    request_root: Path
    build_root: Path
    registration_path: Path
    manifest_path: Path
    manifest_sha256: str
    entrypoint_path: Path
    actual_budget: dict[str, int]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreviewBuildError(f"Cannot read required JSON object: {path}") from exc
    if not isinstance(data, dict):
        raise PreviewBuildError(f"Expected a JSON object: {path}")
    return data


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _project_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise PreviewBuildError(f"Path is outside the trusted project root: {path}") from exc


def _normalized_relative(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    posix = PurePosixPath(value)
    return (
        not posix.is_absolute()
        and bool(posix.parts)
        and ":" not in posix.parts[0]
        and all(part not in {"", ".", ".."} for part in posix.parts)
        and posix.as_posix() == value
    )


def _exact_project_path(root: Path, declared: object, *, label: str) -> Path:
    if not _normalized_relative(declared):
        raise PreviewBuildError(f"{label} must be a normalized project-relative path.")
    relative = str(declared)
    target = root.joinpath(*PurePosixPath(relative).parts).resolve()
    if _project_relative(root, target) != relative:
        raise PreviewBuildError(f"{label} diverges after path resolution: {relative}")
    return target


def _require_exact_keys(value: dict[str, Any], allowed: set[str], *, label: str) -> None:
    unknown = sorted(set(value).difference(allowed))
    if unknown:
        raise PreviewBuildError(f"{label} contains unsupported keys: {', '.join(unknown)}")


def _number(value: object, *, label: str, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise PreviewBuildError(f"{label} must be a finite number.")
    result = float(value)
    if minimum is not None and result < minimum:
        raise PreviewBuildError(f"{label} must be >= {minimum}.")
    if maximum is not None and result > maximum:
        raise PreviewBuildError(f"{label} must be <= {maximum}.")
    return result


def _integer(value: object, *, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise PreviewBuildError(f"{label} must be an integer >= {minimum}.")
    return value


def _vec(value: object, length: int, *, label: str) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != length:
        raise PreviewBuildError(f"{label} must contain exactly {length} numbers.")
    return tuple(_number(item, label=f"{label}[{index}]") for index, item in enumerate(value))


def _truth(value: object, *, label: str) -> str:
    if not isinstance(value, str) or value not in VALID_TRUTH_LABELS:
        raise PreviewBuildError(f"{label} has an unsupported truth label.")
    return value


def _text(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PreviewBuildError(f"{label} must be a non-empty string.")
    return value.strip()


def _normalized_id(value: object, *, label: str) -> str:
    text = _text(value, label=label)
    if not _ID_RE.fullmatch(text):
        raise PreviewBuildError(f"{label} must be a normalized lowercase identifier.")
    return text


def _inside(point: Iterable[float], minimum: tuple[float, ...], maximum: tuple[float, ...]) -> bool:
    return all(low <= coordinate <= high for coordinate, low, high in zip(point, minimum, maximum))


def _validate_bounds(value: object, *, label: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    if not isinstance(value, dict) or set(value) != {"min", "max"}:
        raise PreviewBuildError(f"{label} must contain only min and max vectors.")
    minimum = _vec(value["min"], 3, label=f"{label}.min")
    maximum = _vec(value["max"], 3, label=f"{label}.max")
    if any(high <= low for low, high in zip(minimum, maximum)):
        raise PreviewBuildError(f"{label} must have positive extents.")
    return minimum, maximum


def _point_hits_collider(x: float, z: float, radius: float, collider: dict[str, Any]) -> bool:
    minimum = collider["min"]
    maximum = collider["max"]
    return (
        x >= minimum[0] - radius
        and x <= maximum[0] + radius
        and z >= minimum[2] - radius
        and z <= maximum[2] + radius
    )


def _segment_hits_collider(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    radius: float,
    collider: dict[str, Any],
) -> bool:
    """Liang-Barsky 2D segment/AABB test with avatar-radius expansion."""

    minimum_x = float(collider["min"][0]) - radius
    maximum_x = float(collider["max"][0]) + radius
    minimum_z = float(collider["min"][2]) - radius
    maximum_z = float(collider["max"][2]) + radius
    dx = end[0] - start[0]
    dz = end[2] - start[2]
    lower = 0.0
    upper = 1.0
    for origin, delta, low, high in (
        (start[0], dx, minimum_x, maximum_x),
        (start[2], dz, minimum_z, maximum_z),
    ):
        if abs(delta) < 1e-9:
            if origin < low or origin > high:
                return False
            continue
        first = (low - origin) / delta
        second = (high - origin) / delta
        if first > second:
            first, second = second, first
        lower = max(lower, first)
        upper = min(upper, second)
        if lower > upper:
            return False
    return True


def _primitive_triangles(item: dict[str, Any]) -> int:
    primitive = item["primitive"]
    if primitive == "box":
        return 12
    if primitive == "plane":
        return 2
    if primitive == "cylinder":
        return 4 * int(item["segments"])
    raise PreviewBuildError(f"Unsupported primitive type: {primitive}")


def _validate_source_labeled_item(item: dict[str, Any], *, label: str) -> None:
    _truth(item.get("truth_label"), label=f"{label}.truth_label")
    _text(item.get("source_note"), label=f"{label}.source_note")


def validate_scene_program(program: dict[str, Any]) -> dict[str, Any]:
    """Validate and measure a procedural scene without writing any files."""

    _require_exact_keys(program, PROGRAM_KEYS, label="scene program")
    if program.get("schema_version") != 1 or program.get("program_kind") != PROGRAM_KIND:
        raise PreviewBuildError("Unsupported procedural scene program schema or kind.")
    world_id = _normalized_id(program.get("world_id"), label="program.world_id")
    request_id = _normalized_id(program.get("request_id"), label="program.request_id")
    if not world_id.endswith("_notebook_world") or not request_id.startswith("notebook_world_"):
        raise PreviewBuildError("Program world/request identity is not a notebook-world identity.")
    if program.get("status") != "prototype_draft":
        raise PreviewBuildError("Procedural scene programs must remain prototype_draft.")
    _text(program.get("title"), label="program.title")
    _text(program.get("subtitle"), label="program.subtitle")
    if program.get("units") != "meters":
        raise PreviewBuildError("Procedural preview units must be meters.")
    world_min, world_max = _validate_bounds(program.get("world_bounds"), label="program.world_bounds")

    budget = program.get("scene_budget")
    if not isinstance(budget, dict) or set(budget) != set(HARD_BUDGET):
        raise PreviewBuildError("scene_budget must declare every supported hard-budget field exactly once.")
    for key, hard_limit in HARD_BUDGET.items():
        declared = _integer(budget.get(key), label=f"scene_budget.{key}", minimum=1)
        if declared > hard_limit:
            raise PreviewBuildError(f"scene_budget.{key} exceeds the backend hard limit {hard_limit}.")

    environment = program.get("environment")
    if not isinstance(environment, dict):
        raise PreviewBuildError("program.environment must be an object.")
    _require_exact_keys(environment, {"background_color", "fog_color", "fog_near", "fog_far"}, label="environment")
    for key in ("background_color", "fog_color"):
        if not isinstance(environment.get(key), str) or not _COLOR_RE.fullmatch(environment[key]):
            raise PreviewBuildError(f"environment.{key} must be a #RRGGBB color.")
    fog_near = _number(environment.get("fog_near"), label="environment.fog_near", minimum=0.1)
    fog_far = _number(environment.get("fog_far"), label="environment.fog_far", minimum=fog_near + 0.1)
    if fog_far > 500:
        raise PreviewBuildError("environment.fog_far exceeds the lightweight preview range.")

    materials = program.get("materials")
    if not isinstance(materials, list) or not materials:
        raise PreviewBuildError("program.materials must be a non-empty list.")
    material_ids: set[str] = set()
    for index, item in enumerate(materials):
        label = f"materials[{index}]"
        if not isinstance(item, dict):
            raise PreviewBuildError(f"{label} must be an object.")
        _require_exact_keys(
            item,
            {"id", "color", "roughness", "metalness", "opacity", "truth_label", "source_note"},
            label=label,
        )
        item_id = _normalized_id(item.get("id"), label=f"{label}.id")
        if item_id in material_ids:
            raise PreviewBuildError(f"Duplicate material id: {item_id}")
        material_ids.add(item_id)
        if not isinstance(item.get("color"), str) or not _COLOR_RE.fullmatch(item["color"]):
            raise PreviewBuildError(f"{label}.color must be a #RRGGBB color.")
        _number(item.get("roughness"), label=f"{label}.roughness", minimum=0, maximum=1)
        _number(item.get("metalness"), label=f"{label}.metalness", minimum=0, maximum=1)
        _number(item.get("opacity"), label=f"{label}.opacity", minimum=0.05, maximum=1)
        _validate_source_labeled_item(item, label=label)

    lights = program.get("lights")
    if not isinstance(lights, list) or not lights:
        raise PreviewBuildError("program.lights must be a non-empty list.")
    light_ids: set[str] = set()
    for index, item in enumerate(lights):
        label = f"lights[{index}]"
        if not isinstance(item, dict):
            raise PreviewBuildError(f"{label} must be an object.")
        light_type = item.get("type")
        allowed = {"id", "type", "intensity", "truth_label", "source_note"}
        allowed |= {"sky_color", "ground_color"} if light_type == "hemisphere" else {"color", "position"}
        _require_exact_keys(item, allowed, label=label)
        light_id = _normalized_id(item.get("id"), label=f"{label}.id")
        if light_id in light_ids:
            raise PreviewBuildError(f"Duplicate light id: {light_id}")
        light_ids.add(light_id)
        if light_type not in {"hemisphere", "directional"}:
            raise PreviewBuildError(f"{label}.type must be hemisphere or directional.")
        color_keys = ("sky_color", "ground_color") if light_type == "hemisphere" else ("color",)
        for key in color_keys:
            if not isinstance(item.get(key), str) or not _COLOR_RE.fullmatch(item[key]):
                raise PreviewBuildError(f"{label}.{key} must be a #RRGGBB color.")
        if light_type == "directional":
            _vec(item.get("position"), 3, label=f"{label}.position")
        _number(item.get("intensity"), label=f"{label}.intensity", minimum=0, maximum=10)
        _validate_source_labeled_item(item, label=label)

    primitives = program.get("primitives")
    if not isinstance(primitives, list) or not primitives:
        raise PreviewBuildError("program.primitives must be a non-empty list.")
    primitive_ids: set[str] = set()
    triangle_count = 0
    valid_categories = {"architecture", "furniture", "floor_mark", "camera_mark", "facade", "safety", "landscape"}
    for index, item in enumerate(primitives):
        label = f"primitives[{index}]"
        if not isinstance(item, dict):
            raise PreviewBuildError(f"{label} must be an object.")
        primitive_type = item.get("primitive")
        common = {
            "id",
            "primitive",
            "material_id",
            "position",
            "rotation",
            "category",
            "truth_label",
            "source_note",
        }
        shape = {"size"} if primitive_type in {"box", "plane"} else {"radius", "height", "segments"}
        _require_exact_keys(item, common | shape, label=label)
        primitive_id = _normalized_id(item.get("id"), label=f"{label}.id")
        if primitive_id in primitive_ids:
            raise PreviewBuildError(f"Duplicate primitive id: {primitive_id}")
        primitive_ids.add(primitive_id)
        if item.get("material_id") not in material_ids:
            raise PreviewBuildError(f"{label}.material_id does not reference a declared material.")
        position = _vec(item.get("position"), 3, label=f"{label}.position")
        if not _inside(position, world_min, world_max):
            raise PreviewBuildError(f"{label}.position is outside world_bounds.")
        _vec(item.get("rotation"), 3, label=f"{label}.rotation")
        if item.get("category") not in valid_categories:
            raise PreviewBuildError(f"{label}.category is unsupported.")
        if primitive_type == "box":
            size = _vec(item.get("size"), 3, label=f"{label}.size")
            if any(dimension <= 0 or dimension > 100 for dimension in size):
                raise PreviewBuildError(f"{label}.size must contain positive bounded dimensions.")
        elif primitive_type == "plane":
            size = _vec(item.get("size"), 2, label=f"{label}.size")
            if any(dimension <= 0 or dimension > 100 for dimension in size):
                raise PreviewBuildError(f"{label}.size must contain positive bounded dimensions.")
        elif primitive_type == "cylinder":
            _number(item.get("radius"), label=f"{label}.radius", minimum=0.01, maximum=20)
            _number(item.get("height"), label=f"{label}.height", minimum=0.005, maximum=50)
            _integer(item.get("segments"), label=f"{label}.segments", minimum=6)
            if int(item["segments"]) > 64:
                raise PreviewBuildError(f"{label}.segments exceeds the lightweight cap.")
        else:
            raise PreviewBuildError(f"{label}.primitive is unsupported.")
        _validate_source_labeled_item(item, label=label)
        triangle_count += _primitive_triangles(item)

    rooms = program.get("rooms")
    if not isinstance(rooms, list) or not rooms:
        raise PreviewBuildError("program.rooms must be a non-empty list.")
    room_ids: set[str] = set()
    for index, item in enumerate(rooms):
        label = f"rooms[{index}]"
        if not isinstance(item, dict):
            raise PreviewBuildError(f"{label} must be an object.")
        _require_exact_keys(item, {"id", "name", "purpose", "bounds", "truth_label", "source_note"}, label=label)
        room_id = _normalized_id(item.get("id"), label=f"{label}.id")
        if room_id in room_ids:
            raise PreviewBuildError(f"Duplicate room id: {room_id}")
        room_ids.add(room_id)
        _text(item.get("name"), label=f"{label}.name")
        _text(item.get("purpose"), label=f"{label}.purpose")
        minimum, maximum = _validate_bounds(item.get("bounds"), label=f"{label}.bounds")
        if not _inside(minimum, world_min, world_max) or not _inside(maximum, world_min, world_max):
            raise PreviewBuildError(f"{label}.bounds escapes world_bounds.")
        _validate_source_labeled_item(item, label=label)

    colliders = program.get("colliders")
    if not isinstance(colliders, list):
        raise PreviewBuildError("program.colliders must be a list.")
    collider_ids: set[str] = set()
    normalized_colliders: list[dict[str, Any]] = []
    for index, item in enumerate(colliders):
        label = f"colliders[{index}]"
        if not isinstance(item, dict):
            raise PreviewBuildError(f"{label} must be an object.")
        _require_exact_keys(item, {"id", "kind", "min", "max", "truth_label", "source_note"}, label=label)
        collider_id = _normalized_id(item.get("id"), label=f"{label}.id")
        if collider_id in collider_ids:
            raise PreviewBuildError(f"Duplicate collider id: {collider_id}")
        collider_ids.add(collider_id)
        if item.get("kind") != "solid_aabb":
            raise PreviewBuildError(f"{label}.kind must be solid_aabb.")
        minimum = _vec(item.get("min"), 3, label=f"{label}.min")
        maximum = _vec(item.get("max"), 3, label=f"{label}.max")
        if any(high <= low for low, high in zip(minimum, maximum)):
            raise PreviewBuildError(f"{label} must have positive extents.")
        if not _inside(minimum, world_min, world_max) or not _inside(maximum, world_min, world_max):
            raise PreviewBuildError(f"{label} escapes world_bounds.")
        _validate_source_labeled_item(item, label=label)
        normalized_colliders.append({"id": collider_id, "min": minimum, "max": maximum})

    supports = program.get("support_surfaces")
    if not isinstance(supports, list) or not supports:
        raise PreviewBuildError("program.support_surfaces must be a non-empty list.")
    support_ids: set[str] = set()
    for index, item in enumerate(supports):
        label = f"support_surfaces[{index}]"
        if not isinstance(item, dict):
            raise PreviewBuildError(f"{label} must be an object.")
        _require_exact_keys(item, {"id", "min_x", "max_x", "min_z", "max_z", "y", "truth_label", "source_note"}, label=label)
        support_id = _normalized_id(item.get("id"), label=f"{label}.id")
        if support_id in support_ids:
            raise PreviewBuildError(f"Duplicate support surface id: {support_id}")
        support_ids.add(support_id)
        min_x = _number(item.get("min_x"), label=f"{label}.min_x")
        max_x = _number(item.get("max_x"), label=f"{label}.max_x")
        min_z = _number(item.get("min_z"), label=f"{label}.min_z")
        max_z = _number(item.get("max_z"), label=f"{label}.max_z")
        y = _number(item.get("y"), label=f"{label}.y")
        if min_x >= max_x or min_z >= max_z or not _inside((min_x, y, min_z), world_min, world_max) or not _inside((max_x, y, max_z), world_min, world_max):
            raise PreviewBuildError(f"{label} has invalid or out-of-bounds extents.")
        _validate_source_labeled_item(item, label=label)

    def validate_marks(key: str, required_extra: set[str]) -> tuple[set[str], list[dict[str, Any]]]:
        values = program.get(key)
        if not isinstance(values, list) or not values:
            raise PreviewBuildError(f"program.{key} must be a non-empty list.")
        ids: set[str] = set()
        result: list[dict[str, Any]] = []
        for index, item in enumerate(values):
            label = f"{key}[{index}]"
            if not isinstance(item, dict):
                raise PreviewBuildError(f"{label} must be an object.")
            _require_exact_keys(
                item,
                {"id", "label", "position", "primitive_id", "truth_label", "source_note"} | required_extra,
                label=label,
            )
            item_id = _normalized_id(item.get("id"), label=f"{label}.id")
            if item_id in ids:
                raise PreviewBuildError(f"Duplicate {key} id: {item_id}")
            ids.add(item_id)
            _text(item.get("label"), label=f"{label}.label")
            position = _vec(item.get("position"), 3, label=f"{label}.position")
            if not _inside(position, world_min, world_max):
                raise PreviewBuildError(f"{label}.position is outside world_bounds.")
            if item.get("primitive_id") not in primitive_ids:
                raise PreviewBuildError(f"{label}.primitive_id is not a declared primitive.")
            _validate_source_labeled_item(item, label=label)
            result.append({"id": item_id, "position": position, "raw": item})
        return ids, result

    spawn_ids, spawns = validate_marks("spawns", {"intended_role", "occupant_policy", "yaw"})
    for index, spawn in enumerate(spawns):
        raw = spawn["raw"]
        if raw.get("occupant_policy") != "mark_only_no_person_loaded":
            raise PreviewBuildError(f"spawns[{index}].occupant_policy must keep the mark unoccupied.")
        _text(raw.get("intended_role"), label=f"spawns[{index}].intended_role")
        _number(raw.get("yaw"), label=f"spawns[{index}].yaw", minimum=-math.tau, maximum=math.tau)
        for collider in normalized_colliders:
            if _point_hits_collider(spawn["position"][0], spawn["position"][2], 0.34, collider):
                raise PreviewBuildError(f"Spawn {spawn['id']} intersects collider {collider['id']}.")

    camera_ids, cameras = validate_marks("cameras", {"target", "fov"})
    for index, camera in enumerate(cameras):
        raw = camera["raw"]
        _vec(raw.get("target"), 3, label=f"cameras[{index}].target")
        _number(raw.get("fov"), label=f"cameras[{index}].fov", minimum=20, maximum=100)

    mark_ids, marks = validate_marks("filming_marks", {"mark_type"})
    for index, mark in enumerate(marks):
        _normalized_id(mark["raw"].get("mark_type"), label=f"filming_marks[{index}].mark_type")

    routes = program.get("routes")
    if not isinstance(routes, list) or not routes:
        raise PreviewBuildError("program.routes must be a non-empty list.")
    route_ids: set[str] = set()
    route_point_count = 0
    route_checks: list[dict[str, Any]] = []
    for index, item in enumerate(routes):
        label = f"routes[{index}]"
        if not isinstance(item, dict):
            raise PreviewBuildError(f"{label} must be an object.")
        _require_exact_keys(item, {"id", "label", "avatar_radius", "points", "truth_label", "source_note"}, label=label)
        route_id = _normalized_id(item.get("id"), label=f"{label}.id")
        if route_id in route_ids:
            raise PreviewBuildError(f"Duplicate route id: {route_id}")
        route_ids.add(route_id)
        _text(item.get("label"), label=f"{label}.label")
        radius = _number(item.get("avatar_radius"), label=f"{label}.avatar_radius", minimum=0.2, maximum=0.6)
        raw_points = item.get("points")
        if not isinstance(raw_points, list) or len(raw_points) < 2:
            raise PreviewBuildError(f"{label}.points must contain at least two points.")
        points = [_vec(point, 3, label=f"{label}.points[{point_index}]") for point_index, point in enumerate(raw_points)]
        route_point_count += len(points)
        for point in points:
            if not _inside(point, world_min, world_max):
                raise PreviewBuildError(f"{label} contains a point outside world_bounds.")
        collisions: list[dict[str, Any]] = []
        for segment_index, (start, end) in enumerate(zip(points, points[1:])):
            for collider in normalized_colliders:
                if _segment_hits_collider(start, end, radius, collider):
                    collisions.append({"segment_index": segment_index, "collider_id": collider["id"]})
        if collisions:
            raise PreviewBuildError(f"Route {route_id} is obstructed: {collisions}")
        _validate_source_labeled_item(item, label=label)
        route_checks.append(
            {
                "route_id": route_id,
                "avatar_radius": radius,
                "point_count": len(points),
                "segment_count": len(points) - 1,
                "status": "clear",
                "obstructions": [],
            }
        )

    overlays = program.get("overlays")
    if not isinstance(overlays, list) or not overlays:
        raise PreviewBuildError("program.overlays must be a non-empty list.")
    overlay_ids: set[str] = set()
    for index, item in enumerate(overlays):
        label = f"overlays[{index}]"
        if not isinstance(item, dict):
            raise PreviewBuildError(f"{label} must be an object.")
        _require_exact_keys(item, {"id", "title", "body", "mode", "truth_label", "source_note"}, label=label)
        overlay_id = _normalized_id(item.get("id"), label=f"{label}.id")
        if overlay_id in overlay_ids:
            raise PreviewBuildError(f"Duplicate overlay id: {overlay_id}")
        overlay_ids.add(overlay_id)
        _text(item.get("title"), label=f"{label}.title")
        _text(item.get("body"), label=f"{label}.body")
        if item.get("mode") != "informational_future_hook_only":
            raise PreviewBuildError(f"{label}.mode must remain informational_future_hook_only.")
        _validate_source_labeled_item(item, label=label)

    isolation = program.get("isolation")
    if not isinstance(isolation, dict):
        raise PreviewBuildError("program.isolation must be an object.")
    exact_isolation = {
        "world_class": "separate_notebook_world",
        "home_world_mutation_allowed": False,
        "strip_mall_mutation_allowed": False,
        "runtime_registered": False,
        "person_assets_loaded": False,
        "resident_minds_loaded": False,
        "voice_loaded": False,
        "ollama_loaded": False,
    }
    if isolation != exact_isolation:
        raise PreviewBuildError("program.isolation must match the fail-closed notebook preview policy exactly.")
    source_notes = program.get("source_notes")
    if not isinstance(source_notes, list) or not source_notes or any(not isinstance(note, str) or not note.strip() for note in source_notes):
        raise PreviewBuildError("program.source_notes must contain non-empty source/truth notes.")

    all_ids = [
        material_ids,
        light_ids,
        primitive_ids,
        room_ids,
        collider_ids,
        support_ids,
        spawn_ids,
        camera_ids,
        mark_ids,
        route_ids,
        overlay_ids,
    ]
    flattened = [item for group in all_ids for item in group]
    if len(flattened) != len(set(flattened)):
        raise PreviewBuildError("Scene identifiers must be globally unique across all declaration types.")

    actual = {
        "max_meshes": len(primitives),
        "max_materials": len(materials),
        "max_lights": len(lights),
        "max_triangles": triangle_count,
        "max_colliders": len(colliders),
        "max_routes": len(routes),
        "max_route_points": route_point_count,
        "max_rooms": len(rooms),
        "max_spawns": len(spawns),
        "max_cameras": len(cameras),
        "max_filming_marks": len(marks),
        "max_overlays": len(overlays),
    }
    for key, value in actual.items():
        if value > int(budget[key]):
            raise PreviewBuildError(f"Scene uses {value} for {key}, above its authorized budget {budget[key]}.")

    return {
        "world_id": world_id,
        "request_id": request_id,
        "actual_budget": actual,
        "route_checks": route_checks,
        "truth_label_counts": _truth_label_counts(program),
    }


def _truth_label_counts(program: dict[str, Any]) -> dict[str, int]:
    counts = {label: 0 for label in sorted(VALID_TRUTH_LABELS)}
    for key in (
        "materials",
        "lights",
        "primitives",
        "rooms",
        "colliders",
        "support_surfaces",
        "spawns",
        "cameras",
        "filming_marks",
        "routes",
        "overlays",
    ):
        for item in program.get(key, []):
            if isinstance(item, dict) and item.get("truth_label") in counts:
                counts[str(item["truth_label"])] += 1
    return counts


def _find_index_anchor(index: dict[str, Any], world_id: str, request_id: str) -> dict[str, Any]:
    worlds = index.get("notebook_worlds")
    if index.get("schema_version") != 1 or not isinstance(worlds, dict):
        raise PreviewBuildError("Notebook-world index is malformed.")
    matches: list[tuple[str, dict[str, Any]]] = []
    for candidate_world_id, world in worlds.items():
        if not isinstance(world, dict) or not isinstance(world.get("anchors"), list):
            continue
        for anchor in world["anchors"]:
            if isinstance(anchor, dict) and anchor.get("request_id") == request_id:
                matches.append((str(candidate_world_id), anchor))
    if len(matches) != 1 or matches[0][0] != world_id:
        raise PreviewBuildError("Request is missing, duplicated, or registered in another notebook world.")
    return matches[0][1]


def _validate_request_and_gates(
    *,
    root: Path,
    request_path: Path,
    request: dict[str, Any],
) -> tuple[str, str, Path, dict[str, Any], dict[str, Path]]:
    errors = validate_notebook_world_request(request)
    if errors:
        raise PreviewBuildError("Strict-v2 request validation failed: " + "; ".join(errors))
    if request.get("schema_version") != 2 or request.get("status") != "draft":
        raise PreviewBuildError("Preview backend accepts only strict-v2 draft requests.")
    world_plan = request.get("world_plan")
    if not isinstance(world_plan, dict):
        raise PreviewBuildError("Request world_plan is missing.")
    world_id = _normalized_id(world_plan.get("notebook_world_id"), label="request world id")
    request_id = _normalized_id(request.get("request_id"), label="request id")
    expected_request_root = root / "Data" / "world_builds" / "notebook_worlds" / world_id / "builds" / request_id
    expected_request_path = expected_request_root / "notebook_world_request.json"
    if request_path.resolve() != expected_request_path.resolve():
        raise PreviewBuildError("Request path does not match its strict world/request identity.")
    if not request_path.is_file() or request_path.is_symlink():
        raise PreviewBuildError("Request must be a regular non-symlinked file.")
    isolation = request.get("isolation_policy")
    resource = request.get("resource_policy")
    if not isinstance(isolation, dict) or not isinstance(resource, dict):
        raise PreviewBuildError("Request isolation/resource policy is missing.")
    false_isolation = (
        "home_world_import_requested",
        "home_world_mutation_allowed",
        "strip_mall_mutation_allowed",
        "co_load_with_home_world",
        "co_load_with_other_notebook_worlds",
    )
    false_resource = ("loads_kira_mind", "loads_kira_body", "loads_voice", "loads_ollama", "loads_second_person")
    if any(isolation.get(key) is not False for key in false_isolation) or any(resource.get(key) is not False for key in false_resource):
        raise PreviewBuildError("Request attempts to broaden protected-world or resident runtime scope.")

    gate_paths = {
        "notebook_approval_gate": expected_request_root / "approval_gate.json",
        "notebook_quality_gate": expected_request_root / "quality_gate.json",
        "notebook_resource_gate": expected_request_root / "resource_isolation_gate.json",
        "tardis_review_metadata": expected_request_root / "tardis_review_stage.json",
    }
    gates = {role: _read_json(path) for role, path in gate_paths.items()}
    if any(gate.get("request_id") != request_id for gate in gates.values()):
        raise PreviewBuildError("A notebook gate is bound to another request.")
    approval = gates["notebook_approval_gate"]
    quality = gates["notebook_quality_gate"]
    runtime = gates["notebook_resource_gate"]
    tardis = gates["tardis_review_metadata"]
    if (
        approval.get("world_builder_may_commit_to_world") is not False
        or approval.get("world_builder_may_import_to_home_world") is not False
        or approval.get("world_builder_may_mutate_strip_mall") is not False
        or quality.get("world_builder_may_commit_to_world") is not False
        or runtime.get("notebook_world_runtime_started") is not False
        or runtime.get("loads_home_world") is not False
        or runtime.get("home_world_merge_allowed") is not False
        or runtime.get("strip_mall_mutation_allowed") is not False
        or tardis.get("status") != "preview_required_not_built"
    ):
        raise PreviewBuildError("Notebook gates do not remain draft/isolation fail-closed.")
    index_path = root / "Data" / "world_builds" / "notebook_world_index.json"
    index = _read_json(index_path)
    anchor = _find_index_anchor(index, world_id, request_id)
    expected_scene_folder = _project_relative(root, expected_request_root)
    if (
        anchor.get("scene_folder") != expected_scene_folder
        or anchor.get("placement_approved") is not False
        or anchor.get("runtime_registered") is not False
        or anchor.get("status") != "draft_request_only"
    ):
        raise PreviewBuildError("Notebook index anchor is not an unplaced, unregistered strict-v2 draft.")
    return world_id, request_id, expected_request_root, anchor, gate_paths


def _validate_authorization(
    *,
    root: Path,
    authorization_path: Path,
    authorization: dict[str, Any],
    request_path: Path,
    program_path: Path,
    world_id: str,
    request_id: str,
    build_id: str,
    actual_budget: dict[str, int],
) -> None:
    _require_exact_keys(authorization, AUTHORIZATION_KEYS, label="preview scope authorization")
    if (
        authorization.get("schema_version") != 1
        or authorization.get("authorization_kind") != AUTHORIZATION_KIND
        or authorization.get("status") != AUTHORIZATION_STATUS
        or authorization.get("builder_backend") != BACKEND_ID
    ):
        raise PreviewBuildError("Preview scope authorization has an unsupported schema, status, or backend.")
    _text(authorization.get("authorized_by"), label="authorization.authorized_by")
    _text(authorization.get("authorized_at"), label="authorization.authorized_at")
    _text(authorization.get("scope_statement"), label="authorization.scope_statement")
    if authorization.get("world_id") != world_id or authorization.get("request_id") != request_id:
        raise PreviewBuildError("Preview authorization identity does not match the request.")
    if authorization.get("allowed_build_id") != build_id:
        raise PreviewBuildError("Preview authorization does not permit this build id.")
    expected_authorization_path = request_path.parent / "preview_scope_authorization.json"
    if authorization_path.resolve() != expected_authorization_path.resolve() or authorization_path.is_symlink():
        raise PreviewBuildError("Preview authorization must be the request-local non-symlinked authorization file.")

    for key, path in (("request_binding", request_path), ("program_binding", program_path)):
        binding = authorization.get(key)
        if not isinstance(binding, dict) or set(binding) != {"path", "sha256", "bytes"}:
            raise PreviewBuildError(f"authorization.{key} must bind path, sha256, and bytes exactly.")
        if binding.get("path") != _project_relative(root, path):
            raise PreviewBuildError(f"authorization.{key}.path diverges from the supplied input.")
        if binding.get("sha256") != sha256_file(path) or binding.get("bytes") != path.stat().st_size:
            raise PreviewBuildError(f"authorization.{key} does not match the current input bytes.")

    actions = authorization.get("authorized_actions")
    exact_actions = {
        "build_isolated_procedural_preview": True,
        "serve_scoped_preview": True,
        "approve_world": False,
        "register_runtime": False,
        "place_in_home_world": False,
        "mutate_home_world": False,
        "mutate_strip_mall": False,
        "load_people": False,
        "load_minds": False,
        "load_voice": False,
    }
    if actions != exact_actions:
        raise PreviewBuildError("Preview authorization actions must match the narrow fail-closed action set exactly.")
    limits = authorization.get("limits")
    if not isinstance(limits, dict) or set(limits) != set(HARD_BUDGET):
        raise PreviewBuildError("Preview authorization must declare every backend limit exactly.")
    for key, hard_limit in HARD_BUDGET.items():
        value = _integer(limits.get(key), label=f"authorization.limits.{key}", minimum=1)
        if value > hard_limit:
            raise PreviewBuildError(f"authorization.limits.{key} exceeds the backend hard limit.")
        if key in actual_budget and actual_budget[key] > value:
            raise PreviewBuildError(f"Scene exceeds authorization.limits.{key}.")


def _binding(path: Path, *, root: Path, role: str, url: str | None = None, declared_path: Path | None = None) -> dict[str, Any]:
    actual_path = path
    declaration = declared_path or path
    item: dict[str, Any] = {
        "role": role,
        "path": _project_relative(root, declaration),
        "sha256": sha256_file(actual_path),
        "bytes": actual_path.stat().st_size,
    }
    if url is not None:
        item["url"] = url
    return item


def build_authorized_preview(
    *,
    request_path: Path,
    program_path: Path,
    authorization_path: Path,
    build_id: str,
    root: Path = PROJECT_ROOT,
    template_root: Path | None = None,
    three_module: Path | None = None,
    three_core: Path | None = None,
    created_at: str | None = None,
) -> PreviewBuildResult:
    """Build one immutable preview after all request and authorization checks pass."""

    root = root.resolve()
    request_path = request_path.resolve()
    program_path = program_path.resolve()
    authorization_path = authorization_path.resolve()
    template_root = (template_root or (root / TEMPLATE_ROOT.relative_to(PROJECT_ROOT))).resolve()
    three_module = (three_module or (root / THREE_MODULE.relative_to(PROJECT_ROOT))).resolve()
    three_core = (three_core or (root / THREE_CORE.relative_to(PROJECT_ROOT))).resolve()
    build_id = _normalized_id(build_id, label="build_id")
    request = _read_json(request_path)
    world_id, request_id, request_root, anchor, gate_paths = _validate_request_and_gates(
        root=root,
        request_path=request_path,
        request=request,
    )
    if program_path != request_root / "procedural_scene_program.json" or program_path.is_symlink():
        raise PreviewBuildError("Scene program must be the request-local non-symlinked procedural_scene_program.json.")
    program = _read_json(program_path)
    measured = validate_scene_program(program)
    if measured["world_id"] != world_id or measured["request_id"] != request_id:
        raise PreviewBuildError("Scene program identity does not match the strict-v2 request.")
    authorization = _read_json(authorization_path)
    _validate_authorization(
        root=root,
        authorization_path=authorization_path,
        authorization=authorization,
        request_path=request_path,
        program_path=program_path,
        world_id=world_id,
        request_id=request_id,
        build_id=build_id,
        actual_budget=measured["actual_budget"],
    )

    template_files = {
        "entry_html": template_root / "index.html",
        "entry_javascript": template_root / "main.js",
        "entry_stylesheet": template_root / "styles.css",
    }
    for role, path in {
        **template_files,
        "three_runtime": three_module,
        "three_core_runtime": three_core,
    }.items():
        if not path.is_file() or path.is_symlink():
            raise PreviewBuildError(f"Required {role} source is missing or symlinked: {path}")
        _project_relative(root, path)

    preview_builds_root = request_root / "preview_builds"
    final_build_root = preview_builds_root / build_id
    if final_build_root.exists():
        raise PreviewBuildError(f"Refusing to overwrite existing preview build: {final_build_root}")
    preview_builds_root.mkdir(parents=True, exist_ok=True)
    # Stage under a short trusted project path for Windows MAX_PATH
    # compatibility, then atomically move the complete directory into the
    # request-local immutable build folder.
    stage_token = hashlib.sha256(f"{world_id}:{request_id}:{build_id}".encode("utf-8")).hexdigest()[:12]
    staging_root = root / "Data" / ".notebook_preview_staging" / f"{stage_token}.{os.getpid()}"
    if staging_root.exists():
        raise PreviewBuildError(f"Staging path already exists: {staging_root}")
    staging_root.mkdir(parents=True)

    created = created_at or utc_now()
    final_preview = final_build_root / "preview"
    staging_preview = staging_root / "preview"
    try:
        staging_preview.mkdir()
        for role, source in template_files.items():
            target_name = {"entry_html": "index.html", "entry_javascript": "main.js", "entry_stylesheet": "styles.css"}[role]
            _atomic_write(staging_preview / target_name, source.read_bytes())

        scene_metadata = {
            "schema_version": 1,
            "metadata_kind": "generated_procedural_notebook_world_scene",
            "backend": BACKEND_ID,
            "world_id": world_id,
            "request_id": request_id,
            "build_id": build_id,
            "status": BUILD_STATUS,
            "title": program["title"],
            "subtitle": program["subtitle"],
            "units": "meters",
            "world_bounds": program["world_bounds"],
            "environment": program["environment"],
            "materials": program["materials"],
            "lights": program["lights"],
            "primitives": program["primitives"],
            "rooms": program["rooms"],
            "spawns": program["spawns"],
            "cameras": program["cameras"],
            "filming_marks": program["filming_marks"],
            "overlays": program["overlays"],
            "isolation": program["isolation"],
        }
        collision_nav = {
            "schema_version": 1,
            "metadata_kind": "procedural_collision_navigation_contract",
            "world_id": world_id,
            "request_id": request_id,
            "build_id": build_id,
            "status": "static_validation_passed_runtime_walk_not_claimed",
            "collision_model": "axis_aligned_boxes_with_0_34m_default_walker_radius",
            "colliders": program["colliders"],
            "support_surfaces": program["support_surfaces"],
            "routes": program["routes"],
            "route_checks": measured["route_checks"],
            "spawn_marks": program["spawns"],
            "camera_marks": program["cameras"],
            "filming_marks": program["filming_marks"],
            "runtime_route_claim_allowed": False,
        }
        source_truth = {
            "schema_version": 1,
            "metadata_kind": "procedural_preview_source_truth_labels",
            "world_id": world_id,
            "request_id": request_id,
            "build_id": build_id,
            "status": "truth_labels_present_prototype_not_source_reconstruction",
            "allowed_labels": sorted(VALID_TRUTH_LABELS),
            "label_counts": measured["truth_label_counts"],
            "source_notes": program["source_notes"],
            "truth_rule": "Original procedural choices remain style_fill or inferred; manual_note_confirmed identifies the requested program, not real-world factual reconstruction.",
        }
        build_status = {
            "schema_version": 1,
            "metadata_kind": "procedural_notebook_world_preview_status",
            "world_id": world_id,
            "request_id": request_id,
            "build_id": build_id,
            "created_at": created,
            "backend": BACKEND_ID,
            "status": BUILD_STATUS,
            "prototype": True,
            "draft": True,
            "final": False,
            "approved": False,
            "runtime_registered": False,
            "home_world_mutation": False,
            "strip_mall_mutation": False,
            "people_loaded": False,
            "minds_loaded": False,
            "voice_loaded": False,
            "ollama_loaded": False,
            "request_sha256": sha256_file(request_path),
            "program_sha256": sha256_file(program_path),
            "authorization_sha256": sha256_file(authorization_path),
            "template_sha256": {role: sha256_file(path) for role, path in template_files.items()},
            "limitations": [
                "Procedural geometry and static metadata only.",
                "No person, avatar, mind, voice, or autonomy runtime is present.",
                "Static route clearance is not a live embodied route test.",
                "Exterior/facade may be intentionally incomplete when the program labels it so.",
                "No Home World placement or import is authorized.",
            ],
        }

        generated_json = {
            "scene_manifest.json": scene_metadata,
            "collision_nav.json": collision_nav,
            "source_truth.json": source_truth,
            "build_status.json": build_status,
        }
        for name, value in generated_json.items():
            _atomic_write(staging_root / name, canonical_json_bytes(value))

        payload_paths = [*staging_preview.iterdir(), *(staging_root / name for name in generated_json)]
        payload_bytes = sum(path.stat().st_size for path in payload_paths)
        authorized_payload_limit = int(authorization["limits"]["max_generated_payload_bytes"])
        declared_payload_limit = int(program["scene_budget"]["max_generated_payload_bytes"])
        if payload_bytes > min(authorized_payload_limit, declared_payload_limit, HARD_BUDGET["max_generated_payload_bytes"]):
            raise PreviewBuildError("Generated preview payload exceeds its authorized byte budget.")
        actual_budget = dict(measured["actual_budget"])
        actual_budget["max_generated_payload_bytes"] = payload_bytes
        resource_budget = {
            "schema_version": 1,
            "metadata_kind": "lightweight_procedural_scene_budget",
            "world_id": world_id,
            "request_id": request_id,
            "build_id": build_id,
            "status": "within_declared_and_backend_caps",
            "declared_budget": program["scene_budget"],
            "authorization_limits": authorization["limits"],
            "backend_hard_limits": HARD_BUDGET,
            "actual": actual_budget,
            "payload_measurement_scope": "entry files plus scene/collision/source/status JSON; excludes registration, manifest, and this report to avoid circular byte accounting",
            "loads_home_world": False,
            "loads_people": False,
            "loads_minds": False,
            "loads_voice": False,
            "loads_ollama": False,
        }
        _atomic_write(staging_root / "resource_budget.json", canonical_json_bytes(resource_budget))

        final_rel = _project_relative(root, final_build_root)
        registration = {
            "schema_version": 1,
            "registration_kind": "generated_procedural_notebook_world_preview_registration",
            "world_id": world_id,
            "request_id": request_id,
            "build_id": build_id,
            "created_at": created,
            "status": BUILD_STATUS,
            "scene_folder": _project_relative(root, request_root),
            "preview": f"{final_rel}/preview/index.html",
            "pinned_build_manifest": f"{final_rel}/pinned_build_manifest.json",
            "request": _project_relative(root, request_path),
            "program": _project_relative(root, program_path),
            "authorization": _project_relative(root, authorization_path),
            "request_sha256": sha256_file(request_path),
            "program_sha256": sha256_file(program_path),
            "authorization_sha256": sha256_file(authorization_path),
            "launcher_requires_code_pinned_manifest": True,
            "launcher_verifies_all_manifest_bytes_before_bind": True,
            "server_scope": {
                "entire_workspace_served": False,
                "directory_listing": False,
                "exact_manifest_bound_files_only": True,
                "hash_rechecked_on_every_request": True,
            },
            "prototype": True,
            "draft": True,
            "final": False,
            "approved": False,
            "runtime_registered": False,
            "home_world_mutation_allowed": False,
            "strip_mall_mutation_allowed": False,
            "loads_people": False,
            "loads_minds": False,
            "loads_voice": False,
            "loads_ollama": False,
        }
        _atomic_write(staging_root / "registration.json", canonical_json_bytes(registration))

        final_paths = {
            "registration": final_build_root / "registration.json",
            "entry_html": final_preview / "index.html",
            "entry_javascript": final_preview / "main.js",
            "entry_stylesheet": final_preview / "styles.css",
            "scene_metadata": final_build_root / "scene_manifest.json",
            "collision_nav_metadata": final_build_root / "collision_nav.json",
            "source_truth_metadata": final_build_root / "source_truth.json",
            "resource_budget_metadata": final_build_root / "resource_budget.json",
            "build_status_metadata": final_build_root / "build_status.json",
        }
        staging_paths = {
            "registration": staging_root / "registration.json",
            "entry_html": staging_preview / "index.html",
            "entry_javascript": staging_preview / "main.js",
            "entry_stylesheet": staging_preview / "styles.css",
            "scene_metadata": staging_root / "scene_manifest.json",
            "collision_nav_metadata": staging_root / "collision_nav.json",
            "source_truth_metadata": staging_root / "source_truth.json",
            "resource_budget_metadata": staging_root / "resource_budget.json",
            "build_status_metadata": staging_root / "build_status.json",
        }
        served_urls = {
            "entry_html": "/index.html",
            "entry_javascript": "/main.js",
            "entry_stylesheet": "/styles.css",
            "scene_metadata": "/data/scene_manifest.json",
            "collision_nav_metadata": "/data/collision_nav.json",
            "source_truth_metadata": "/data/source_truth.json",
            "resource_budget_metadata": "/data/resource_budget.json",
            "build_status_metadata": "/data/build_status.json",
        }
        files: list[dict[str, Any]] = []
        for role, staging_path in staging_paths.items():
            files.append(
                _binding(
                    staging_path,
                    root=root,
                    role=role,
                    url=served_urls.get(role),
                    declared_path=final_paths[role],
                )
            )
        for role, path in (
            ("notebook_request", request_path),
            ("preview_scope_authorization", authorization_path),
            ("procedural_scene_program", program_path),
            *tuple((role, path) for role, path in gate_paths.items()),
        ):
            files.append(_binding(path, root=root, role=role))
        files.append(_binding(three_module, root=root, role="three_runtime", url="/vendor/three/three.module.js"))
        files.append(_binding(three_core, root=root, role="three_core_runtime", url="/vendor/three/three.core.js"))

        registration_binding = next(item for item in files if item["role"] == "registration")
        entry_binding = next(item for item in files if item["role"] == "entry_html")
        manifest = {
            "schema_version": 1,
            "manifest_kind": "code_pinned_notebook_world_build",
            "world_id": world_id,
            "request_id": request_id,
            "build_id": build_id,
            "build_status": BUILD_STATUS,
            "backend": BACKEND_ID,
            "registration": {key: registration_binding[key] for key in ("path", "sha256", "bytes")},
            "entrypoint": {key: entry_binding[key] for key in ("url", "path", "sha256", "bytes")},
            "index_registration": {
                "path": "Data/world_builds/notebook_world_index.json",
                "scene_folder": _project_relative(root, request_root),
                "anchor_sha256": canonical_json_sha256(anchor),
            },
            "input_bindings": {
                "request_sha256": sha256_file(request_path),
                "program_sha256": sha256_file(program_path),
                "authorization_sha256": sha256_file(authorization_path),
            },
            "protected_world_policy": {
                "home_world_mutation_allowed": False,
                "strip_mall_mutation_allowed": False,
                "runtime_registered": False,
                "people_loaded": False,
                "minds_loaded": False,
                "voice_loaded": False,
            },
            "files": files,
        }
        _atomic_write(staging_root / "pinned_build_manifest.json", canonical_json_bytes(manifest))

        # Re-check all mutable inputs immediately before the atomic directory move.
        if (
            sha256_file(request_path) != registration["request_sha256"]
            or sha256_file(program_path) != registration["program_sha256"]
            or sha256_file(authorization_path) != registration["authorization_sha256"]
        ):
            raise PreviewBuildError("An input changed while the preview was being staged.")
        current_anchor = _find_index_anchor(_read_json(root / "Data" / "world_builds" / "notebook_world_index.json"), world_id, request_id)
        if canonical_json_sha256(current_anchor) != manifest["index_registration"]["anchor_sha256"]:
            raise PreviewBuildError("Notebook index anchor changed while the preview was being staged.")
        os.replace(staging_root, final_build_root)
    except Exception:
        if staging_root.exists():
            shutil.rmtree(staging_root)
        raise

    manifest_path = final_build_root / "pinned_build_manifest.json"
    return PreviewBuildResult(
        world_id=world_id,
        request_id=request_id,
        build_id=build_id,
        request_root=request_root,
        build_root=final_build_root,
        registration_path=final_build_root / "registration.json",
        manifest_path=manifest_path,
        manifest_sha256=sha256_file(manifest_path),
        entrypoint_path=final_build_root / "preview" / "index.html",
        actual_budget=actual_budget,
    )


def authorization_binding(path: Path, *, root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Return the exact binding shape expected in a reviewed authorization file."""

    path = path.resolve()
    if not path.is_file() or path.is_symlink():
        raise PreviewBuildError(f"Cannot bind missing or symlinked file: {path}")
    return {
        "path": _project_relative(root.resolve(), path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }
