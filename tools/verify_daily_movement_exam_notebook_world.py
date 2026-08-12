"""Deterministically verify the Daily Movement Exam scene contract."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUILD = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "daily_movement_exam_notebook_world"
    / "builds"
    / "notebook_world_daily_movement_exam_20260717_160706"
)
PROGRAM = BUILD / "procedural_scene_program.json"
REQUIRED_PRIMITIVE_TOKENS = {
    "door",
    "corner",
    "couch",
    "bed",
    "chair",
    "table",
    "tablet",
    "cup",
    "robe",
    "hook",
    "exercise",
}


def read_program(path: Path = PROGRAM) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _collision_at(program: dict[str, Any], x: float, z: float, radius: float) -> str | None:
    for collider in program["colliders"]:
        if (
            collider["min"][0] - radius <= x <= collider["max"][0] + radius
            and collider["min"][2] - radius <= z <= collider["max"][2] + radius
        ):
            return str(collider["id"])
    return None


def _supported_at(program: dict[str, Any], x: float, z: float, radius: float) -> bool:
    return any(
        surface["min_x"] + radius <= x <= surface["max_x"] - radius
        and surface["min_z"] + radius <= z <= surface["max_z"] - radius
        for surface in program["support_surfaces"]
    )


def route_samples(route: dict[str, Any], step: float = 0.05) -> list[tuple[float, float]]:
    points = route["points"]
    samples: list[tuple[float, float]] = []
    for index in range(1, len(points)):
        a, b = points[index - 1], points[index]
        distance = math.hypot(b[0] - a[0], b[2] - a[2])
        count = max(1, math.ceil(distance / step))
        first = 0 if index == 1 else 1
        for sample in range(first, count + 1):
            t = sample / count
            samples.append((a[0] + (b[0] - a[0]) * t, a[2] + (b[2] - a[2]) * t))
    return samples


def verify_program(program: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    if program.get("world_id") != "daily_movement_exam_notebook_world":
        failures.append("wrong_world_id")
    isolation = program.get("isolation", {})
    for key in (
        "home_world_mutation_allowed",
        "strip_mall_mutation_allowed",
        "runtime_registered",
        "person_assets_loaded",
        "resident_minds_loaded",
        "voice_loaded",
        "ollama_loaded",
    ):
        if isolation.get(key) is not False:
            failures.append(f"isolation_not_false:{key}")
    primitive_names = " ".join(str(item.get("id", "")).lower() for item in program.get("primitives", []))
    for token in sorted(REQUIRED_PRIMITIVE_TOKENS):
        if token not in primitive_names:
            failures.append(f"missing_fixture:{token}")
    if len(program.get("filming_marks", [])) != 8:
        failures.append("expected_8_subject_choice_stations")
    route_results: list[dict[str, Any]] = []
    for route in program.get("routes", []):
        radius = float(route.get("avatar_radius", 0.34))
        samples = route_samples(route)
        failure = None
        for x, z in samples:
            collision = _collision_at(program, x, z, radius)
            if collision:
                failure = f"collision:{collision}"
                break
            if not _supported_at(program, x, z, radius):
                failure = "outside_support"
                break
        route_results.append(
            {
                "route_id": route.get("id"),
                "passed": failure is None,
                "failure": failure,
                "sample_count": len(samples),
            }
        )
        if failure:
            failures.append(f"route:{route.get('id')}:{failure}")
    budget = program.get("scene_budget", {})
    if len(program.get("primitives", [])) > int(budget.get("max_meshes", 0)):
        failures.append("mesh_budget_exceeded")
    if len(program.get("materials", [])) > int(budget.get("max_materials", 0)):
        failures.append("material_budget_exceeded")
    if len(program.get("colliders", [])) > int(budget.get("max_colliders", 0)):
        failures.append("collider_budget_exceeded")
    if len(program.get("routes", [])) > int(budget.get("max_routes", 0)):
        failures.append("route_budget_exceeded")
    return {
        "passed": not failures,
        "failures": failures,
        "primitive_count": len(program.get("primitives", [])),
        "material_count": len(program.get("materials", [])),
        "collider_count": len(program.get("colliders", [])),
        "route_count": len(program.get("routes", [])),
        "station_count": len(program.get("filming_marks", [])),
        "route_results": route_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = verify_program(read_program())
    print(json.dumps(result, indent=2) if args.json else f"Daily Movement Exam verification: {'PASS' if result['passed'] else 'FAIL'}")
    if not args.json:
        print(f"Primitives: {result['primitive_count']}; colliders: {result['collider_count']}; routes: {result['route_count']}; stations: {result['station_count']}")
        for route in result["route_results"]:
            print(f"- {route['route_id']}: {'PASS' if route['passed'] else route['failure']} ({route['sample_count']} samples)")
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
