#!/usr/bin/env python3
"""Append-only R24 Attempt 17 expanded-carrier no-save simulation.

The exact audited R23 695-face mask is reconstructed from sealed evidence.
No donor Blend or donor geometry is loaded.  A replacement carrier is derived
only from the outer seam and exterior collar, then shallow compact-support
semantic relief is added.  The worker writes evidence and renders only; it
never writes a Blend.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import traceback
from typing import Any, Iterable, Mapping, Sequence

import bmesh
import bpy
from mathutils import Vector
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_preflight_kira_r23_cc0_afes_expanded_mask as r23_preflight  # noqa: E402
from tools import blender_simulate_kira_r24_internal_midpoint_fair_surface as r24_intersections  # noqa: E402
from tools.kira_r23_blender51_action_serializer import actions_sha256  # noqa: E402
from tools.kira_r23_cc0_afes_preflight_core import (  # noqa: E402
    boundary_edges_for_region,
    canonical_index_sha256,
    canonical_json_sha256,
    expand_face_rings,
    face_adjacency,
    ordered_boundary_cycles,
    shortest_path_union,
    topology_record,
)


DEFAULT_CONFIG = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r24_expanded_carrier_attempt17_preparation/"
    "KIRA_R24_ATTEMPT17_EXPANDED_CARRIER_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = (
    "dca49a017983125853914d52638eb76abd8ec9a684fd80484136bdfe972820b3"
)
EXPECTED_ATTEMPT_SLOT = "attempt_17"
NO_SAVE = True
ACTIVE_OUTPUT: Path | None = None


class Attempt17Error(RuntimeError):
    pass


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG.as_posix())
    return parser.parse_args(raw)


def project_path(raw: str | Path) -> Path:
    value = Path(str(raw))
    if value.is_absolute() or ".." in value.parts:
        raise Attempt17Error(f"unsafe project-relative path: {raw}")
    resolved = (ROOT / value).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise Attempt17Error(f"path escaped project: {raw}") from exc
    return resolved


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise Attempt17Error(f"JSON root is not an object: {relative(path)}")
    return value


def atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def verify_binding(name: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    path = project_path(str(raw.get("path") or ""))
    if not path.is_file():
        raise Attempt17Error(f"missing bound input {name}: {relative(path)}")
    actual = {
        "path": relative(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    if (
        actual["bytes"] != int(raw.get("bytes", -1))
        or actual["sha256"] != str(raw.get("sha256") or "").lower()
    ):
        raise Attempt17Error(f"bound input drifted: {name}: {actual}")
    return actual


def verify_bindings(config: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(name): verify_binding(str(name), raw)
        for name, raw in config["bindings"].items()
    }


def preserved_attempt_manifest(root: Path) -> dict[str, Any]:
    rows = []
    for number in range(1, 16):
        directory = root / f"attempt_{number:02d}"
        if not directory.is_dir():
            raise Attempt17Error(f"preserved attempt is missing: {relative(directory)}")
        for path in sorted(item for item in directory.rglob("*") if item.is_file()):
            rows.append(
                {
                    "path": relative(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return {
        "file_count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
        "canonical_manifest_sha256": canonical_json_sha256(rows),
    }


def verify_preserved_attempts(config: Mapping[str, Any]) -> dict[str, Any]:
    root = project_path(config["output"]["root"])
    actual = preserved_attempt_manifest(root)
    expected = config["preserved_attempts_01_15"]
    checks = {
        "file_count": actual["file_count"] == int(expected["file_count"]),
        "total_bytes": actual["total_bytes"] == int(expected["total_bytes"]),
        "canonical_manifest_sha256": actual["canonical_manifest_sha256"]
        == expected["canonical_manifest_sha256"],
    }
    if not all(checks.values()):
        raise Attempt17Error(
            f"Attempts 01-15 manifest drifted: checks={checks}, actual={actual}"
        )
    return {**actual, "checks": checks}


def verify_attempt16_runtime(config: Mapping[str, Any]) -> dict[str, Any]:
    contract = config["attempt16_runtime_evidence_contract"]
    directory = project_path(contract["directory"])
    if not directory.is_dir():
        raise Attempt17Error(
            "reserved Attempt 16 must finish before the Attempt 17 fallback may run"
        )
    started_path = directory / contract["started_file"]
    if not started_path.is_file():
        raise Attempt17Error("Attempt 16 runtime start evidence is absent")
    terminal_paths = [
        directory / name for name in contract["terminal_files"] if (directory / name).is_file()
    ]
    if len(terminal_paths) != 1:
        raise Attempt17Error("Attempt 16 must have exactly one terminal evidence file")
    started = read_json(started_path)
    terminal = read_json(terminal_paths[0])
    expected_worker = config["bindings"][
        contract["started_worker_sha256_must_match_binding"]
    ]["sha256"]
    expected_config = config["bindings"][
        contract["started_config_sha256_must_match_binding"]
    ]["sha256"]
    started_checks = {
        "worker_hash": started.get("worker_sha256") == expected_worker,
        "config_hash": started.get("config_sha256") == expected_config,
        "blend_save_not_permitted": started.get("blend_save_permitted") is False,
    }
    if terminal_paths[0].name == "SIMULATION_REPORT.json":
        terminal_no_save = (
            terminal.get("scope", {}).get("blend_saved") is False
            and terminal.get("save_gate", {}).get("save_allowed") is False
            and terminal.get("worker", {}).get("worker_sha256") == expected_worker
            and terminal.get("worker", {}).get("config_sha256") == expected_config
        )
    else:
        terminal_no_save = (
            terminal.get("blend_saved") is False
            and terminal.get("runtime_changed") is False
        )
    files = [
        {
            "path": relative(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(item for item in directory.rglob("*") if item.is_file())
    ]
    checks = {
        **started_checks,
        "exactly_one_terminal_file": len(terminal_paths) == 1,
        "terminal_no_save": terminal_no_save,
    }
    if not all(checks.values()):
        raise Attempt17Error(f"Attempt 16 runtime evidence failed binding: {checks}")
    return {
        "directory": relative(directory),
        "terminal_file": terminal_paths[0].name,
        "terminal_status": terminal.get("status"),
        "file_count": len(files),
        "total_bytes": sum(int(row["bytes"]) for row in files),
        "canonical_manifest_sha256": canonical_json_sha256(files),
        "files": files,
        "checks": checks,
    }


def allocate_output(config: Mapping[str, Any]) -> Path:
    root = project_path(config["output"]["root"])
    expected = project_path(config["output"]["directory"])
    if expected.parent != root or expected.name != EXPECTED_ATTEMPT_SLOT:
        raise Attempt17Error("Attempt 17 output binding is not exact")
    existing = sorted(
        int(path.name.split("_")[-1])
        for path in root.glob("attempt_[0-9][0-9]")
        if path.is_dir() and path.name.split("_")[-1].isdigit()
    )
    next_number = max(existing, default=0) + 1
    if next_number != 17:
        raise Attempt17Error(
            f"append-only attempt slot is attempt_{next_number:02d}, not attempt_17"
        )
    if expected.exists():
        raise FileExistsError(f"append-only output exists: {relative(expected)}")
    expected.mkdir(parents=False, exist_ok=False)
    return expected


def vector_record(value: Vector) -> list[float]:
    return [float(value.x), float(value.y), float(value.z)]


def faces_of(body: bpy.types.Object) -> list[tuple[int, ...]]:
    return [tuple(int(value) for value in face.vertices) for face in body.data.polygons]


def old_patch_record(
    body: bpy.types.Object, contract: Mapping[str, Any]
) -> tuple[set[int], set[int], list[int], dict[str, Any]]:
    faces = faces_of(body)
    selected = {
        int(face.index)
        for face in body.data.polygons
        if int(face.material_index) == int(contract["old_patch_material_slot"])
    }
    vertices = {int(vertex) for index in selected for vertex in faces[index]}
    cycles = ordered_boundary_cycles(boundary_edges_for_region(faces, selected))
    if len(cycles) != 1:
        raise Attempt17Error("old R19 patch is not one disk boundary")
    material = body.data.materials[int(contract["old_patch_material_slot"])]
    checks = {
        "body_vertex_count": len(body.data.vertices)
        == int(contract["expected_body_vertices"]),
        "body_edge_count": len(body.data.edges) == int(contract["expected_body_edges"]),
        "body_face_count": len(body.data.polygons)
        == int(contract["expected_body_faces"]),
        "shape_key_count": (
            len(body.data.shape_keys.key_blocks) if body.data.shape_keys else 0
        )
        == int(contract["expected_shape_keys"]),
        "material_name": material is not None
        and material.name == contract["old_patch_material_name"],
        "face_count": len(selected) == int(contract["old_patch_faces"]),
        "incident_vertex_count": len(vertices)
        == int(contract["old_patch_incident_vertices"]),
        "interface_count": len(cycles[0])
        == int(contract["old_patch_interface_vertices"]),
        "face_hash": canonical_index_sha256(selected)
        == contract["old_patch_face_index_sha256"],
        "vertex_hash": canonical_index_sha256(vertices)
        == contract["old_patch_incident_vertex_sha256"],
        "interface_hash": canonical_json_sha256(cycles[0])
        == contract["old_patch_ordered_interface_sha256"],
    }
    if not all(checks.values()):
        raise Attempt17Error(f"sealed R19 geometry contract failed: {checks}")
    return selected, vertices, cycles[0], {"checks": checks}


def face_chart_coordinates(
    body: bpy.types.Object, projection: Mapping[str, Any]
) -> dict[int, tuple[float, float, float]]:
    origin = Vector(tuple(projection["target_origin_world_m"]))
    axes = projection["target_axes_world"]
    lateral = Vector(tuple(axes["lateral"])).normalized()
    longitudinal = Vector(tuple(axes["longitudinal"])).normalized()
    outward = Vector(tuple(axes["outward"])).normalized()
    scales = projection["target_scales_m"]
    result = {}
    for face in body.data.polygons:
        delta = body.matrix_world @ face.center - origin
        result[int(face.index)] = (
            float(delta.dot(lateral) / float(scales["half_width"])),
            float(delta.dot(longitudinal) / float(scales["half_length"])),
            float(delta.dot(outward) / float(scales["maximum_outward_offset"])),
        )
    return result


def reconstruct_expanded_mask(
    body: bpy.types.Object,
    old_faces: set[int],
    evidence: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> tuple[set[int], list[int], dict[str, Any]]:
    faces = faces_of(body)
    adjacency = face_adjacency(faces)
    projection = evidence["donor_to_r19_projection"]
    hit_faces = {
        int(face)
        for row in projection["groups"].values()
        for face in row["projected_face_indices"]
    }
    hit_hash_check = canonical_index_sha256(hit_faces) == projection[
        "projected_face_index_sha256"
    ]
    chart = face_chart_coordinates(body, projection)
    bounds = projection["donor_chart_bounds"]
    u_min = float(bounds["u"][0]) - float(contract["allowed_chart_margin_u"])
    u_max = float(bounds["u"][1]) + float(contract["allowed_chart_margin_u"])
    v_min = float(bounds["v"][0]) - float(contract["allowed_chart_margin_v"])
    v_max = float(bounds["v"][1]) + float(contract["allowed_chart_margin_v"])
    w_limit = float(contract["allowed_chart_maximum_abs_w"])
    allowed = {
        index
        for index, (u_value, v_value, w_value) in chart.items()
        if u_min <= u_value <= u_max
        and v_min <= v_value <= v_max
        and abs(w_value) <= w_limit
    }
    allowed.update(old_faces)
    allowed.update(hit_faces)
    path_union, distances = shortest_path_union(
        adjacency, old_faces, hit_faces, allowed=allowed
    )
    selected = expand_face_rings(
        path_union,
        adjacency,
        int(contract["selected_exterior_face_rings"]),
        allowed=allowed,
    )
    topology = topology_record(faces, selected)
    cycles = ordered_boundary_cycles(boundary_edges_for_region(faces, selected))
    if len(cycles) != 1:
        raise Attempt17Error("expanded mask does not have one boundary cycle")
    cycle = cycles[0]
    checks = {
        "projection_hit_hash": hit_hash_check,
        "face_count": topology["face_count"] == int(contract["face_count"]),
        "incident_vertex_count": topology["vertex_count"]
        == int(contract["incident_vertex_count"]),
        "edge_count": topology["edge_count"] == int(contract["edge_count"]),
        "triangle_count": topology["triangle_count"]
        == int(contract["triangle_count"]),
        "component_count": topology["component_count"]
        == int(contract["component_count"]),
        "boundary_cycle_count": topology["boundary_cycle_count"]
        == int(contract["boundary_cycle_count"]),
        "outer_boundary_vertices": len(cycle)
        == int(contract["outer_boundary_vertices"]),
        "euler_characteristic": topology["euler_characteristic"]
        == int(contract["euler_characteristic"]),
        "face_hash": topology["face_index_sha256"]
        == contract["face_index_sha256"],
        "vertex_hash": topology["vertex_index_sha256"]
        == contract["incident_vertex_sha256"],
        "edge_hash": topology["edge_sha256"] == contract["edge_sha256"],
        "topology_boundary_hash": topology["boundary_sha256"]
        == contract["topology_boundary_sha256"],
        "ordered_outer_seam_hash": canonical_json_sha256(cycle)
        == contract["ordered_outer_seam_sha256"],
        "old_patch_fully_interior": old_faces.issubset(selected),
        "evidence_face_hash": evidence["expanded_r19_mask"][
            "selected_face_index_sha256"
        ]
        == contract["face_index_sha256"],
        "evidence_seam_hash": evidence["expanded_r19_mask"][
            "ordered_outer_seam_sha256"
        ]
        == contract["ordered_outer_seam_sha256"],
    }
    if not all(checks.values()):
        raise Attempt17Error(f"expanded-mask reconstruction failed: {checks}")
    return selected, cycle, {
        "checks": checks,
        "topology": topology,
        "hit_face_count": len(hit_faces),
        "allowed_face_count": len(allowed),
        "path_union_face_count": len(path_union),
        "maximum_shortest_path_edges": max(distances.values(), default=0),
    }


def vertex_adjacency(
    faces: Sequence[Sequence[int]], selected_faces: Iterable[int]
) -> dict[int, set[int]]:
    result: dict[int, set[int]] = defaultdict(set)
    for face_index in selected_faces:
        values = tuple(int(value) for value in faces[int(face_index)])
        for index, first in enumerate(values):
            second = values[(index + 1) % len(values)]
            result[first].add(second)
            result[second].add(first)
    return dict(result)


def topology_distances(
    adjacency: Mapping[int, set[int]], boundary: Iterable[int]
) -> dict[int, int]:
    result = {int(value): 0 for value in boundary}
    queue = deque(sorted(result))
    while queue:
        current = queue.popleft()
        for neighbor in sorted(adjacency.get(current, set())):
            if neighbor not in result:
                result[neighbor] = result[current] + 1
                queue.append(neighbor)
    if set(result) != set(adjacency):
        raise Attempt17Error("expanded-mask vertex graph is disconnected")
    return result


def exterior_face_collar(
    faces: Sequence[Sequence[int]],
    selected: set[int],
    rings: int,
) -> tuple[set[int], set[int]]:
    adjacency = face_adjacency(faces)
    outside = set(adjacency).difference(selected)
    frontier = {
        neighbor
        for index in selected
        for neighbor in adjacency[index]
        if neighbor in outside
    }
    result = set(frontier)
    for _ in range(1, rings):
        frontier = {
            neighbor
            for index in frontier
            for neighbor in adjacency[index]
            if neighbor in outside and neighbor not in result
        }
        result.update(frontier)
    vertices = {int(value) for index in result for value in faces[index]}
    return result, vertices


def frame_from_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    projection = evidence["donor_to_r19_projection"]
    axes = projection["target_axes_world"]
    return {
        "origin": Vector(tuple(projection["target_origin_world_m"])),
        "lateral": Vector(tuple(axes["lateral"])).normalized(),
        "longitudinal": Vector(tuple(axes["longitudinal"])).normalized(),
        "outward": Vector(tuple(axes["outward"])).normalized(),
        "half_width": float(projection["target_scales_m"]["half_width"]),
        "half_length": float(projection["target_scales_m"]["half_length"]),
    }


def world_coordinates(point: Vector, frame: Mapping[str, Any]) -> tuple[float, float, float]:
    delta = point - frame["origin"]
    return (
        float(delta.dot(frame["lateral"])),
        float(delta.dot(frame["longitudinal"])),
        float(delta.dot(frame["outward"])),
    )


def graph_laplacian(
    vertices: Sequence[int], adjacency: Mapping[int, set[int]]
) -> tuple[np.ndarray, dict[int, int]]:
    lookup = {int(vertex): index for index, vertex in enumerate(vertices)}
    matrix = np.zeros((len(vertices), len(vertices)), dtype=np.float64)
    for vertex in vertices:
        row = lookup[int(vertex)]
        neighbors = sorted(adjacency[int(vertex)])
        matrix[row, row] = float(len(neighbors))
        for neighbor in neighbors:
            matrix[row, lookup[int(neighbor)]] = -1.0
    return matrix, lookup


def solve_dirichlet(
    matrix: np.ndarray,
    vertices: Sequence[int],
    boundary: set[int],
    boundary_values: Mapping[int, float],
) -> tuple[dict[int, float], dict[str, float]]:
    interior_rows = [index for index, vertex in enumerate(vertices) if vertex not in boundary]
    boundary_rows = [index for index, vertex in enumerate(vertices) if vertex in boundary]
    a_ii = matrix[np.ix_(interior_rows, interior_rows)]
    a_ib = matrix[np.ix_(interior_rows, boundary_rows)]
    b_values = np.array([boundary_values[vertices[index]] for index in boundary_rows])
    rhs = -a_ib @ b_values
    condition = float(np.linalg.cond(a_ii))
    solution = np.linalg.solve(a_ii, rhs)
    residual = float(np.linalg.norm(a_ii @ solution - rhs) / math.sqrt(len(solution)))
    result = {int(vertex): float(boundary_values[int(vertex)]) for vertex in boundary}
    result.update(
        {int(vertices[row]): float(value) for row, value in zip(interior_rows, solution)}
    )
    return result, {"condition_number": condition, "rms_residual": residual}


def robust_quadratic_fit(
    samples: Sequence[tuple[float, float, float]], carrier: Mapping[str, Any]
) -> tuple[np.ndarray, dict[str, Any]]:
    design = np.array(
        [[1.0, u, v, u * u, u * v, v * v] for u, v, _ in samples],
        dtype=np.float64,
    )
    target = np.array([w for _, _, w in samples], dtype=np.float64)
    weights = np.ones(len(samples), dtype=np.float64)
    ridge = float(carrier["quadratic_ridge"])
    delta = float(carrier["huber_delta_m"])
    coefficients = np.zeros(6, dtype=np.float64)
    for _ in range(int(carrier["robust_iterations"])):
        weighted = design * np.sqrt(weights)[:, None]
        rhs = target * np.sqrt(weights)
        normal = weighted.T @ weighted + np.eye(6) * ridge
        coefficients = np.linalg.solve(normal, weighted.T @ rhs)
        residual = target - design @ coefficients
        absolute = np.abs(residual)
        weights = np.where(absolute <= delta, 1.0, delta / np.maximum(absolute, 1e-15))
    residual = target - design @ coefficients
    ordered = sorted(float(abs(value)) for value in residual)
    p95 = ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]
    return coefficients, {
        "sample_count": len(samples),
        "coefficient_sha256": canonical_json_sha256([float(v) for v in coefficients]),
        "rms_residual_m": float(math.sqrt(np.mean(residual * residual))),
        "p95_absolute_residual_m": p95,
        "maximum_absolute_residual_m": max(ordered, default=0.0),
    }


def quadratic_value(coefficients: np.ndarray, u: float, v: float) -> float:
    row = np.array([1.0, u, v, u * u, u * v, v * v], dtype=np.float64)
    return float(row @ coefficients)


def solve_screened_biharmonic_depth(
    laplacian: np.ndarray,
    vertices: Sequence[int],
    boundary: set[int],
    boundary_depth: Mapping[int, float],
    seed: Mapping[int, float],
    distances: Mapping[int, int],
    carrier: Mapping[str, Any],
) -> tuple[dict[int, float], dict[str, float]]:
    fairness = float(carrier["biharmonic_fairness_weight"])
    system = fairness * (laplacian.T @ laplacian)
    screen = np.zeros(len(vertices), dtype=np.float64)
    for index, vertex in enumerate(vertices):
        if vertex in boundary:
            continue
        distance = int(distances[vertex])
        if distance == 1:
            screen[index] = float(carrier["screen_weight_ring_1"])
        elif distance == 2:
            screen[index] = float(carrier["screen_weight_ring_2"])
        else:
            screen[index] = float(carrier["screen_weight_deep"])
    system += np.diag(screen)
    rhs = screen * np.array([seed[int(vertex)] for vertex in vertices], dtype=np.float64)
    interior_rows = [index for index, vertex in enumerate(vertices) if vertex not in boundary]
    boundary_rows = [index for index, vertex in enumerate(vertices) if vertex in boundary]
    a_ii = system[np.ix_(interior_rows, interior_rows)]
    a_ib = system[np.ix_(interior_rows, boundary_rows)]
    b_values = np.array([boundary_depth[vertices[index]] for index in boundary_rows])
    rhs_i = rhs[interior_rows] - a_ib @ b_values
    condition = float(np.linalg.cond(a_ii))
    solution = np.linalg.solve(a_ii, rhs_i)
    residual = float(np.linalg.norm(a_ii @ solution - rhs_i) / math.sqrt(len(solution)))
    result = {int(vertex): float(boundary_depth[int(vertex)]) for vertex in boundary}
    result.update(
        {int(vertices[row]): float(value) for row, value in zip(interior_rows, solution)}
    )
    return result, {"condition_number": condition, "rms_residual_m": residual}


def smoothstep(value: float) -> float:
    x = max(0.0, min(1.0, float(value)))
    return x * x * (3.0 - 2.0 * x)


def semantic_relief(
    vertices: Sequence[int],
    u_values: Mapping[int, float],
    v_values: Mapping[int, float],
    distances: Mapping[int, int],
    config: Mapping[str, Any],
) -> tuple[dict[int, float], dict[int, int], dict[str, Any]]:
    u_min, u_max = min(u_values.values()), max(u_values.values())
    v_min, v_max = min(v_values.values()), max(v_values.values())
    u_center, v_center = (u_min + u_max) * 0.5, (v_min + v_max) * 0.5
    u_half = max((u_max - u_min) * 0.5, 1e-9)
    v_half = max((v_max - v_min) * 0.5, 1e-9)
    minimum = int(config["minimum_topology_distance_from_outer_boundary"])
    full = int(config["full_strength_topology_distance"])
    relief: dict[int, float] = {}
    dominant: dict[int, int] = {}
    per_field_max: dict[str, float] = defaultdict(float)
    for vertex in vertices:
        distance = int(distances[vertex])
        if distance < minimum:
            relief[int(vertex)] = 0.0
            dominant[int(vertex)] = 0
            continue
        taper = smoothstep((distance - (minimum - 1)) / max(1, full - (minimum - 1)))
        u_norm = (u_values[vertex] - u_center) / u_half
        v_norm = (v_values[vertex] - v_center) / v_half
        contributions = []
        for field in config["fields"]:
            du = (u_norm - float(field["center_u"])) / float(field["sigma_u"])
            dv = (v_norm - float(field["center_v"])) / float(field["sigma_v"])
            value = float(field["amplitude_m"]) * math.exp(-0.5 * (du * du + dv * dv)) * taper
            contributions.append((field, value))
            per_field_max[str(field["id"])] = max(
                per_field_max[str(field["id"])], abs(value)
            )
        total = sum(value for _, value in contributions)
        total = min(total, float(config["maximum_positive_relief_m"]))
        total = max(total, -float(config["maximum_negative_relief_m"]))
        absolute_cap = float(config["maximum_absolute_combined_relief_m"])
        total = max(-absolute_cap, min(absolute_cap, total))
        winner = max(contributions, key=lambda item: abs(item[1]), default=(None, 0.0))[0]
        relief[int(vertex)] = float(total)
        dominant[int(vertex)] = int(winner["code"]) if winner is not None else 0
    return relief, dominant, {
        "u_bounds_m": [u_min, u_max],
        "v_bounds_m": [v_min, v_max],
        "per_field_maximum_absolute_contribution_m": dict(sorted(per_field_max.items())),
        "maximum_positive_m": max(relief.values(), default=0.0),
        "minimum_negative_m": min(relief.values(), default=0.0),
        "maximum_absolute_m": max((abs(value) for value in relief.values()), default=0.0),
        "zero_ring_maximum_absolute_m": {
            str(ring): max(
                (abs(relief[vertex]) for vertex in vertices if distances[vertex] == ring),
                default=0.0,
            )
            for ring in (0, 1, 2)
        },
    }


def mask_uv_weight_sha256(body: bpy.types.Object, mask_vertices: set[int]) -> str:
    names = {int(group.index): group.name for group in body.vertex_groups}
    weights = [
        [
            int(index),
            sorted(
                [
                    [names[int(item.group)], float(item.weight)]
                    for item in body.data.vertices[index].groups
                    if float(item.weight) > 0.0
                ]
            ),
        ]
        for index in sorted(mask_vertices)
    ]
    uv_layers = []
    for layer in body.data.uv_layers:
        uv_layers.append(
            {
                "name": layer.name,
                "loops": [
                    [
                        int(loop.index),
                        int(loop.vertex_index),
                        float(layer.data[loop.index].uv.x),
                        float(layer.data[loop.index].uv.y),
                    ]
                    for loop in body.data.loops
                    if int(loop.vertex_index) in mask_vertices
                ],
            }
        )
    return canonical_json_sha256({"weights": weights, "uv_layers": uv_layers})


def freeze_ledger(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    mask_faces: set[int],
    seam: Sequence[int],
    objects: Sequence[bpy.types.Object],
) -> dict[str, Any]:
    original = r23_preflight.actions_sha256
    try:
        r23_preflight.actions_sha256 = lambda: actions_sha256(bpy.data.actions)
        return r23_preflight.freeze_ledger(body, rig, mask_faces, seam, objects)
    finally:
        r23_preflight.actions_sha256 = original


def intersection_record(
    body: bpy.types.Object, mask_faces: set[int]
) -> dict[str, Any]:
    bm = bmesh.new()
    try:
        bm.from_mesh(body.data)
        bm.faces.ensure_lookup_table()
        patch = {bm.faces[index] for index in mask_faces}
        summary = r24_intersections.exact_patch_intersection_summary(bm, patch)
        report = r24_intersections.a08.exact_intersections.exact_nonadjacent_intersection_report(
            bm, include_pair_details=True
        )
        genuine = [
            row
            for row in report["pairs"]
            if row.get("overlap_character") == "genuine_penetration"
        ]
        pairs = sorted(
            [sorted(int(value) for value in row["face_indices"]) for row in genuine]
        )
        outside_pairs = [
            row for row in pairs if not any(int(value) in mask_faces for value in row)
        ]
        return {
            **summary,
            "whole_pair_identity_sha256": canonical_json_sha256(pairs),
            "outside_only_pair_count": len(outside_pairs),
            "outside_only_pair_identity_sha256": canonical_json_sha256(outside_pairs),
            "patch_pairs": summary["patch_pairs"],
        }
    finally:
        bm.free()


def face_world_normal(body: bpy.types.Object, face_index: int) -> Vector:
    face = body.data.polygons[int(face_index)]
    points = [body.matrix_world @ body.data.vertices[int(index)].co for index in face.vertices]
    normal = (points[1] - points[0]).cross(points[2] - points[0])
    return normal.normalized() if normal.length > 1e-15 else Vector()


def geometry_quality(
    body: bpy.types.Object,
    mask_faces: set[int],
    seam: Sequence[int],
    original_normals: Mapping[int, Vector],
) -> dict[str, Any]:
    faces = faces_of(body)
    edge_to_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(faces):
        for index, first in enumerate(face):
            edge = tuple(sorted((int(first), int(face[(index + 1) % len(face)]))))
            edge_to_faces[edge].append(face_index)
    areas, ratios, orientation_dots = [], [], []
    for face_index in sorted(mask_faces):
        points = [body.matrix_world @ body.data.vertices[index].co for index in faces[face_index]]
        cross = (points[1] - points[0]).cross(points[2] - points[0])
        areas.append(float(cross.length * 0.5))
        current = cross.normalized() if cross.length > 1e-15 else Vector()
        orientation_dots.append(float(current.dot(original_normals[face_index])))
        lengths = [
            float((points[(index + 1) % 3] - points[index]).length) for index in range(3)
        ]
        ratios.append(max(lengths) / max(min(lengths), 1e-15))
    seam_dots = []
    seam_edges = []
    for index, first in enumerate(seam):
        edge = tuple(sorted((int(first), int(seam[(index + 1) % len(seam)]))))
        incident = edge_to_faces[edge]
        inside = [face for face in incident if face in mask_faces]
        outside = [face for face in incident if face not in mask_faces]
        if len(inside) != 1 or len(outside) != 1:
            raise Attempt17Error(f"outer seam edge incidence is not 1+1: {edge}")
        dot = float(face_world_normal(body, inside[0]).dot(face_world_normal(body, outside[0])))
        seam_dots.append(dot)
        seam_edges.append({"edge": list(edge), "inside_face": inside[0], "outside_face": outside[0], "normal_dot": dot})
    minimum_dot = min(seam_dots, default=-1.0)
    return {
        "minimum_face_area_world_m2": min(areas, default=0.0),
        "maximum_edge_ratio": max(ratios, default=math.inf),
        "minimum_original_normal_dot": min(orientation_dots, default=-1.0),
        "seam_normal_dot": {
            "minimum": minimum_dot,
            "median": statistics.median(seam_dots) if seam_dots else -1.0,
            "maximum": max(seam_dots, default=-1.0),
            "maximum_dihedral_degrees": math.degrees(
                math.acos(max(-1.0, min(1.0, minimum_dot)))
            ),
            "records": seam_edges,
        },
    }


def majority_exterior_material(
    body: bpy.types.Object, mask_faces: set[int], seam: Sequence[int]
) -> tuple[int, dict[str, Any]]:
    faces = faces_of(body)
    edge_to_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(faces):
        for index, first in enumerate(face):
            edge_to_faces[tuple(sorted((first, face[(index + 1) % len(face)])))].append(face_index)
    outside_faces = []
    for index, first in enumerate(seam):
        edge = tuple(sorted((first, seam[(index + 1) % len(seam)])))
        outside_faces.extend(face for face in edge_to_faces[edge] if face not in mask_faces)
    counts = Counter(int(body.data.polygons[index].material_index) for index in outside_faces)
    if not counts:
        raise Attempt17Error("no exterior seam material samples exist")
    selected = min((-count, material) for material, count in counts.items())[1]
    return selected, {"outside_face_count": len(set(outside_faces)), "counts": dict(sorted(counts.items())), "selected_material_index": selected}


def displacement_record(values: Sequence[float]) -> dict[str, Any]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {"maximum_m": 0.0, "p95_m": 0.0, "rms_m": 0.0}
    return {
        "maximum_m": max(ordered),
        "p95_m": ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)],
        "rms_m": math.sqrt(sum(value * value for value in ordered) / len(ordered)),
    }


def apply_carrier(
    body: bpy.types.Object,
    mask_faces: set[int],
    seam: Sequence[int],
    old_vertices: set[int],
    evidence: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    faces = faces_of(body)
    mask_vertices = {int(value) for index in mask_faces for value in faces[index]}
    boundary = {int(value) for value in seam}
    movable = mask_vertices.difference(boundary)
    adjacency = vertex_adjacency(faces, mask_faces)
    distances = topology_distances(adjacency, boundary)
    collar_faces, collar_vertices = exterior_face_collar(
        faces, mask_faces, int(config["carrier"]["exterior_face_collar_rings"])
    )
    training = collar_vertices.difference(mask_vertices).union(boundary)
    old_in_training = training.intersection(old_vertices)
    if old_in_training:
        raise Attempt17Error("old 34-patch interior leaked into carrier training")
    frame = frame_from_evidence(evidence)
    base_world = {
        index: body.matrix_world @ body.data.vertices[index].co.copy()
        for index in mask_vertices
    }
    boundary_coordinates = {
        index: world_coordinates(base_world[index], frame) for index in boundary
    }
    vertices = sorted(mask_vertices)
    laplacian, _ = graph_laplacian(vertices, adjacency)
    u_values, u_solve = solve_dirichlet(
        laplacian,
        vertices,
        boundary,
        {index: boundary_coordinates[index][0] for index in boundary},
    )
    v_values, v_solve = solve_dirichlet(
        laplacian,
        vertices,
        boundary,
        {index: boundary_coordinates[index][1] for index in boundary},
    )
    samples = []
    for index in sorted(training):
        u_value, v_value, w_value = world_coordinates(
            body.matrix_world @ body.data.vertices[index].co, frame
        )
        samples.append(
            (
                u_value / frame["half_width"],
                v_value / frame["half_length"],
                w_value,
            )
        )
    coefficients, fit = robust_quadratic_fit(samples, config["carrier"])
    seed = {
        index: quadratic_value(
            coefficients,
            u_values[index] / frame["half_width"],
            v_values[index] / frame["half_length"],
        )
        for index in vertices
    }
    w_values, w_solve = solve_screened_biharmonic_depth(
        laplacian,
        vertices,
        boundary,
        {index: boundary_coordinates[index][2] for index in boundary},
        seed,
        distances,
        config["carrier"],
    )
    relief, dominant, relief_evidence = semantic_relief(
        vertices, u_values, v_values, distances, config["semantic_relief"]
    )
    carrier_world = {}
    final_world = {}
    for index in vertices:
        if index in boundary:
            carrier_world[index] = base_world[index].copy()
            final_world[index] = base_world[index].copy()
            continue
        carrier_world[index] = (
            frame["origin"]
            + frame["lateral"] * u_values[index]
            + frame["longitudinal"] * v_values[index]
            + frame["outward"] * w_values[index]
        )
        final_world[index] = carrier_world[index] + frame["outward"] * relief[index]
    displacements = [
        float((final_world[index] - base_world[index]).length) for index in movable
    ]
    distribution = displacement_record(displacements)
    world_to_local = body.matrix_world.inverted()
    for index in sorted(movable):
        body.data.vertices[index].co = world_to_local @ final_world[index]
    material, material_evidence = majority_exterior_material(body, mask_faces, seam)
    for face_index in mask_faces:
        body.data.polygons[face_index].material_index = material
    body.data.update()
    feature_faces: dict[int, list[int]] = defaultdict(list)
    for face_index in sorted(mask_faces):
        codes = Counter(dominant[int(vertex)] for vertex in faces[face_index])
        code = min((-count, value) for value, count in codes.items())[1]
        feature_faces[int(code)].append(int(face_index))
    conditions = [u_solve, v_solve, w_solve]
    finite = all(
        math.isfinite(float(value))
        for record in conditions
        for value in record.values()
    ) and all(math.isfinite(value) for value in relief.values())
    return {
        "mask_face_indices": sorted(mask_faces),
        "mask_vertex_indices": sorted(mask_vertices),
        "movable_vertex_indices": sorted(movable),
        "outer_seam": list(seam),
        "topology_distances": {str(index): int(distances[index]) for index in vertices},
        "carrier_training": {
            "exterior_collar_face_count": len(collar_faces),
            "training_vertex_count": len(training),
            "training_vertex_sha256": canonical_index_sha256(training),
            "old_patch_interior_training_sample_count": len(old_in_training),
            "training_source_only_outer_seam_or_exterior": True,
        },
        "frame": {
            key: vector_record(value) if isinstance(value, Vector) else value
            for key, value in frame.items()
        },
        "harmonic_lateral_solve": u_solve,
        "harmonic_longitudinal_solve": v_solve,
        "quadratic_depth_fit": fit,
        "screened_biharmonic_depth_solve": w_solve,
        "relief": relief_evidence,
        "feature_faces": {str(code): values for code, values in sorted(feature_faces.items())},
        "material": material_evidence,
        "displacement": distribution,
        "boundary_maximum_displacement_m": max(
            (float((final_world[index] - base_world[index]).length) for index in boundary),
            default=0.0,
        ),
        "all_solver_and_relief_values_finite": finite,
        "carrier_application_fraction": 1.0,
    }


def clinical_material(name: str, color: Sequence[float]) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    rgba = tuple(float(value) for value in color)
    material.diffuse_color = rgba
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = 0.48
        if bsdf.inputs.get("Specular IOR Level") is not None:
            bsdf.inputs["Specular IOR Level"].default_value = 0.28
    return material


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def make_local_surface(
    body: bpy.types.Object, face_indices: Sequence[int], name: str
) -> tuple[bpy.types.Object, dict[int, int]]:
    source_faces = faces_of(body)
    source_vertices = sorted(
        {int(value) for index in face_indices for value in source_faces[int(index)]}
    )
    vertex_map = {source: new for new, source in enumerate(source_vertices)}
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(
        [tuple(body.data.vertices[index].co) for index in source_vertices],
        [],
        [tuple(vertex_map[value] for value in source_faces[index]) for index in face_indices],
    )
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.matrix_world = body.matrix_world.copy()
    bpy.context.collection.objects.link(obj)
    return obj, {int(source): new for new, source in enumerate(face_indices)}


def render_evidence(
    body: bpy.types.Object,
    mask_faces: set[int],
    applied: Mapping[str, Any],
    directory: Path,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    directory.mkdir(parents=False, exist_ok=False)
    scene = bpy.context.scene
    scene.render.engine = config["render"]["engine"]
    scene.render.resolution_x = int(config["render"]["resolution"][0])
    scene.render.resolution_y = int(config["render"]["resolution"][1])
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.008, 0.012, 0.018)
    scene.view_settings.look = "AgX - Medium High Contrast"
    for obj in list(scene.objects):
        if obj.type in {"LIGHT", "CAMERA"}:
            bpy.data.objects.remove(obj, do_unlink=True)
        elif obj.type == "MESH":
            obj.hide_render = True

    clay = clinical_material("R24_Attempt17_UniformClinicalClay", config["render"]["uniform_clay_rgba"])
    full = body.copy()
    full.data = body.data.copy()
    full.name = "R24_Attempt17_FullClinicalDiagnostic"
    bpy.context.collection.objects.link(full)
    full.hide_render = False
    full.data.materials.clear()
    full.data.materials.append(clay)
    for polygon in full.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True
    full_subdivision = full.modifiers.new("R24_Attempt17_FullSubdivision", "SUBSURF")
    full_subdivision.levels = int(config["render"]["subdivision_level"])
    full_subdivision.render_levels = int(config["render"]["subdivision_level"])

    diagnostic_faces = expand_face_rings(
        mask_faces,
        face_adjacency(faces_of(body)),
        int(config["render"]["diagnostic_exterior_face_rings"]),
    )
    local, local_face_map = make_local_surface(
        body, sorted(diagnostic_faces), "R24_Attempt17_LocalClinicalDiagnostic"
    )
    local.data.materials.append(clay)
    for polygon in local.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True
    local_subdivision = local.modifiers.new("R24_Attempt17_LocalSubdivision", "SUBSURF")
    local_subdivision.levels = int(config["render"]["subdivision_level"])
    local_subdivision.render_levels = int(config["render"]["subdivision_level"])
    local.hide_render = True

    frame = applied["frame"]
    lateral = Vector(tuple(frame["lateral"]))
    longitudinal = Vector(tuple(frame["longitudinal"]))
    outward = Vector(tuple(frame["outward"]))
    mask_vertices = applied["mask_vertex_indices"]
    pelvis = sum(
        (body.matrix_world @ body.data.vertices[index].co for index in mask_vertices),
        Vector(),
    ) / len(mask_vertices)
    all_points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    minimum = Vector(tuple(min(point[axis] for point in all_points) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in all_points) for axis in range(3)))
    center = (minimum + maximum) * 0.5
    height = maximum.z - minimum.z

    lights = []
    for name, location, energy, size in (
        ("R24_A15_Key", pelvis + outward * 2.2 - lateral * 1.6 + longitudinal * 1.6, 980.0, 3.8),
        ("R24_A15_Fill", pelvis + outward * 1.7 + lateral * 1.8 + longitudinal * 0.5, 580.0, 3.0),
        ("R24_A15_Rim", pelvis - outward * 2.0 + lateral * 0.6 + longitudinal * 1.2, 760.0, 2.8),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        light.location = location
        bpy.context.collection.objects.link(light)
        look_at(light, pelvis)
        lights.append(light)

    camera_data = bpy.data.cameras.new("R24_Attempt17_Camera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("R24_Attempt17_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera

    records = []

    def render(name: str, obj: bpy.types.Object, location: Vector, target: Vector, scale: float, *, subdivision: bool, lighting: str = "normal") -> None:
        full.hide_render = obj is not full
        local.hide_render = obj is not local
        if obj is full:
            full_subdivision.show_render = subdivision
        if obj is local:
            local_subdivision.show_render = subdivision
        camera.location = location
        camera.data.ortho_scale = scale
        look_at(camera, target)
        scene.render.filepath = str(directory / name)
        bpy.ops.render.render(write_still=True)
        path = directory / name
        records.append(
            {
                "filename": name,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "surface": "whole_body" if obj is full else "local_unoccluded_surface",
                "diagnostic_subdivision": subdivision,
                "lighting": lighting,
            }
        )

    ordinary = {
        "ordinary_full_front.png": (center + outward * 3.0, center, height * 1.08),
        "ordinary_left_three_quarter.png": (center + outward * 2.6 - lateral * 2.0, center, height * 1.08),
        "ordinary_right_three_quarter.png": (center + outward * 2.6 + lateral * 2.0, center, height * 1.08),
        "ordinary_left_profile.png": (center - lateral * 3.0, center, height * 1.08),
        "ordinary_right_profile.png": (center + lateral * 3.0, center, height * 1.08),
        "ordinary_rear.png": (center - outward * 3.0, center, height * 1.08),
    }
    for name, (location, target, scale) in ordinary.items():
        render(name, full, location, target, scale, subdivision=True)

    protected = {
        "front": (pelvis + outward * 1.6, pelvis, 0.40),
        "left_three_quarter": (pelvis + outward * 1.30 - lateral * 0.88, pelvis, 0.40),
        "right_three_quarter": (pelvis + outward * 1.30 + lateral * 0.88, pelvis, 0.40),
        "left_profile": (pelvis - lateral * 1.6, pelvis, 0.40),
        "right_profile": (pelvis + lateral * 1.6, pelvis, 0.40),
        "inferior": (pelvis + outward * 0.78 - longitudinal * 0.78, pelvis, 0.38),
        "rear": (pelvis - outward * 1.6, pelvis, 0.40),
    }
    for view, (location, target, scale) in protected.items():
        render(f"protected_clinical_{view}.png", local, location, target, scale, subdivision=True)
        render(
            f"protected_clinical_{view}_no_diagnostic_subdivision.png",
            local,
            location,
            target,
            scale,
            subdivision=False,
        )

    normal_energies = [float(light.data.energy) for light in lights]
    lights[0].data.energy, lights[1].data.energy = 340.0, 1180.0
    for view in config["render"]["opposite_light_views"]:
        location, target, scale = protected[str(view)]
        render(
            f"protected_clinical_{view}_opposite_light.png",
            local,
            location,
            target,
            scale,
            subdivision=False,
            lighting="opposite_key_fill",
        )
    for light, energy in zip(lights, normal_energies):
        light.data.energy = energy

    wire = local.copy()
    wire.data = local.data.copy()
    wire.name = "R24_Attempt17_WireDiagnostic"
    bpy.context.collection.objects.link(wire)
    wire.data.materials.clear()
    wire.data.materials.append(clinical_material("R24_Attempt17_WireCyan", (0.0, 0.55, 0.72, 1.0)))
    wireframe = wire.modifiers.new("R24_Attempt17_Wireframe", "WIREFRAME")
    wireframe.thickness = 0.00042
    wireframe.use_replace = True
    wire.hide_render = False
    full.hide_render = True
    local.hide_render = True
    camera.location, target, camera.data.ortho_scale = protected["front"]
    look_at(camera, target)
    scene.render.filepath = str(directory / "protected_clinical_wire.png")
    bpy.ops.render.render(write_still=True)
    wire_path = directory / "protected_clinical_wire.png"
    records.append({"filename": wire_path.name, "sha256": sha256_file(wire_path), "bytes": wire_path.stat().st_size, "surface": "local_unoccluded_surface", "diagnostic_subdivision": False, "lighting": "wire"})
    wire.hide_render = True

    mask = local.copy()
    mask.data = local.data.copy()
    mask.name = "R24_Attempt17_SemanticMaskDiagnostic"
    bpy.context.collection.objects.link(mask)
    palette = {
        0: (0.12, 0.12, 0.12, 1.0), 2: (0.86, 0.58, 0.10, 1.0),
        3: (0.88, 0.12, 0.10, 1.0), 4: (1.0, 0.38, 0.08, 1.0),
        5: (0.05, 0.70, 0.86, 1.0), 6: (0.10, 0.28, 0.95, 1.0),
        7: (0.40, 0.12, 0.60, 1.0), 8: (0.96, 0.92, 0.08, 1.0),
        9: (1.0, 0.05, 0.70, 1.0), 10: (0.08, 0.82, 0.24, 1.0),
        11: (0.94, 0.50, 0.12, 1.0),
    }
    for code in sorted(palette):
        mask.data.materials.append(clinical_material(f"R24_Attempt17_Feature_{code:02d}", palette[code]))
    slot_by_code = {code: index for index, code in enumerate(sorted(palette))}
    source_code = {
        int(face): int(code)
        for code, face_indices in applied["feature_faces"].items()
        for face in face_indices
    }
    for source_face, local_face in local_face_map.items():
        mask.data.polygons[local_face].material_index = slot_by_code.get(source_code.get(source_face, 0), 0)
    mask.hide_render = False
    camera.location, target, camera.data.ortho_scale = protected["front"]
    look_at(camera, target)
    scene.render.filepath = str(directory / "protected_clinical_feature_mask.png")
    bpy.ops.render.render(write_still=True)
    mask_path = directory / "protected_clinical_feature_mask.png"
    records.append({"filename": mask_path.name, "sha256": sha256_file(mask_path), "bytes": mask_path.stat().st_size, "surface": "local_unoccluded_surface", "diagnostic_subdivision": False, "lighting": "semantic_mask"})

    return {
        "directory": relative(directory),
        "render_count": len(records),
        "records": records,
        "paired_protected_view_count": len(protected),
        "protected_profiles_use_local_unoccluded_surface": True,
        "ordinary_whole_body_views": len(ordinary),
        "manual_visual_review_required": True,
        "manual_visual_reject_conditions": config["render"]["manual_visual_reject_conditions"],
    }


def main() -> None:
    global ACTIVE_OUTPUT
    args = arguments()
    config_path = project_path(args.config)
    if config_path != project_path(DEFAULT_CONFIG):
        raise Attempt17Error("only the exact reviewed Attempt 17 config is allowed")
    if sha256_file(config_path) != EXPECTED_CONFIG_SHA256:
        raise Attempt17Error("Attempt 17 config hash drifted")
    config = read_json(config_path)
    if config.get("schema") != "kira.avatar.r24_attempt17_expanded_carrier_no_save.v1":
        raise Attempt17Error("wrong Attempt 17 config schema")
    scope = config["scope"]
    if not (
        scope["append_only"]
        and scope["simulation_only"]
        and not scope["blend_save_allowed"]
        and not scope["donor_geometry_load_allowed"]
        and scope["expected_attempt"] == EXPECTED_ATTEMPT_SLOT
    ):
        raise Attempt17Error("Attempt 17 no-save scope is not exact")

    verified_bindings = verify_bindings(config)
    preserved_before = verify_preserved_attempts(config)
    attempt16_runtime_before = verify_attempt16_runtime(config)
    source_path = project_path(config["bindings"]["sealed_r19_source"]["path"])
    source_hash_before = sha256_file(source_path)
    ACTIVE_OUTPUT = allocate_output(config)
    atomic_write_json(
        ACTIVE_OUTPUT / config["output"]["started"],
        {
            "schema_version": 1,
            "artifact_kind": "KIRA_R24_ATTEMPT17_EXPANDED_CARRIER_STARTED",
            "attempt_id": EXPECTED_ATTEMPT_SLOT,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "STARTED_NO_SAVE",
            "config": {
                "path": relative(config_path),
                "sha256": sha256_file(config_path),
            },
            "worker": {
                "path": relative(Path(__file__)),
                "sha256": sha256_file(Path(__file__)),
            },
            "verified_bindings": verified_bindings,
            "preserved_attempts_01_15": preserved_before,
            "attempt16_runtime_evidence": attempt16_runtime_before,
            "blend_saved": False,
            "runtime_activated": False,
        },
    )

    bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False)
    body = bpy.data.objects.get(config["r19_contract"]["body_object"])
    rig = bpy.data.objects.get(config["r19_contract"]["rig_object"])
    if body is None or body.type != "MESH" or rig is None or rig.type != "ARMATURE":
        raise Attempt17Error("exact R19 body or rig is absent")
    for bone in rig.pose.bones:
        bone.location = (0.0, 0.0, 0.0)
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()

    evidence = read_json(
        project_path(config["bindings"]["audited_expanded_mask_evidence"]["path"])
    )
    old_faces, old_vertices, old_cycle, old_record = old_patch_record(
        body, config["r19_contract"]
    )
    mask_faces, outer_seam, mask_record = reconstruct_expanded_mask(
        body, old_faces, evidence, config["expanded_mask_contract"]
    )
    if set(old_cycle).intersection(set(outer_seam)):
        raise Attempt17Error("old rejected 34-edge interface was not made fully interior")

    source_objects = list(bpy.data.objects)
    ledger_before = freeze_ledger(body, rig, mask_faces, outer_seam, source_objects)
    faces_before = faces_of(body)
    topology_counts_before = {
        "vertices": len(body.data.vertices),
        "edges": len(body.data.edges),
        "faces": len(body.data.polygons),
    }
    mask_vertices = {int(value) for face in mask_faces for value in faces_before[face]}
    attribute_hash_before = mask_uv_weight_sha256(body, mask_vertices)
    original_normals = {index: face_world_normal(body, index) for index in mask_faces}
    intersections_before = intersection_record(body, mask_faces)

    applied = apply_carrier(
        body,
        mask_faces,
        outer_seam,
        old_vertices,
        evidence,
        config,
    )
    ledger_after = freeze_ledger(body, rig, mask_faces, outer_seam, source_objects)
    attribute_hash_after = mask_uv_weight_sha256(body, mask_vertices)
    topology_counts_after = {
        "vertices": len(body.data.vertices),
        "edges": len(body.data.edges),
        "faces": len(body.data.polygons),
    }
    quality = geometry_quality(body, mask_faces, outer_seam, original_normals)
    intersections_after = intersection_record(body, mask_faces)
    source_hash_after_geometry = sha256_file(source_path)

    gates_config = config["gates"]
    carrier_config = config["carrier"]
    relief = applied["relief"]
    seam_quality = quality["seam_normal_dot"]
    checks = {
        "source_hash_unchanged_after_geometry": source_hash_after_geometry
        == source_hash_before,
        "attempts_01_15_manifest_unchanged_before_geometry": preserved_before["checks"]
        == {"file_count": True, "total_bytes": True, "canonical_manifest_sha256": True},
        "old_34_interface_fully_interior": not set(old_cycle).intersection(outer_seam),
        "outer_training_excludes_old_patch_interior": applied["carrier_training"][
            "old_patch_interior_training_sample_count"
        ]
        == int(carrier_config["old_patch_interior_training_samples_required"]),
        "outer_training_source_exact": applied["carrier_training"][
            "training_source_only_outer_seam_or_exterior"
        ],
        "outside_and_outer_seam_freeze_ledger_exact": ledger_after == ledger_before,
        "mask_uv_and_weights_exact": attribute_hash_after == attribute_hash_before,
        "topology_counts_exact": topology_counts_after == topology_counts_before,
        "one_joined_primary_surface": len(
            [obj for obj in source_objects if obj.type == "MESH" and obj == body]
        )
        == 1,
        "no_separate_anatomy_objects_created_before_render": len(bpy.data.objects)
        == len(source_objects),
        "solver_and_relief_finite": applied["all_solver_and_relief_values_finite"],
        "harmonic_lateral_condition_bounded": applied["harmonic_lateral_solve"][
            "condition_number"
        ]
        <= float(carrier_config["maximum_linear_condition_number"]),
        "harmonic_longitudinal_condition_bounded": applied[
            "harmonic_longitudinal_solve"
        ]["condition_number"]
        <= float(carrier_config["maximum_linear_condition_number"]),
        "biharmonic_condition_bounded": applied["screened_biharmonic_depth_solve"][
            "condition_number"
        ]
        <= float(carrier_config["maximum_linear_condition_number"]),
        "all_linear_residuals_bounded": max(
            applied["harmonic_lateral_solve"]["rms_residual"],
            applied["harmonic_longitudinal_solve"]["rms_residual"],
            applied["screened_biharmonic_depth_solve"]["rms_residual_m"],
        )
        <= float(carrier_config["maximum_linear_residual_m"]),
        "carrier_displacement_bounded": applied["displacement"]["maximum_m"]
        <= float(carrier_config["maximum_carrier_displacement_m"]),
        "carrier_rms_displacement_bounded": applied["displacement"]["rms_m"]
        <= float(carrier_config["maximum_carrier_rms_displacement_m"]),
        "outer_boundary_position_exact": applied["boundary_maximum_displacement_m"]
        <= float(carrier_config["boundary_position_tolerance_m"]),
        "carrier_application_fraction_exact": applied["carrier_application_fraction"]
        == float(gates_config["carrier_application_fraction"]),
        "relief_zero_through_ring_2": max(
            relief["zero_ring_maximum_absolute_m"].values()
        )
        == 0.0,
        "relief_absolute_cap": relief["maximum_absolute_m"]
        <= float(config["semantic_relief"]["maximum_absolute_combined_relief_m"]),
        "orientation_preserved": quality["minimum_original_normal_dot"]
        >= float(gates_config["minimum_original_normal_dot"]),
        "nondegenerate": quality["minimum_face_area_world_m2"]
        >= float(gates_config["minimum_face_area_world_m2"]),
        "edge_ratio_bounded": quality["maximum_edge_ratio"]
        <= float(gates_config["maximum_edge_ratio"]),
        "changed_mask_intersections_zero": intersections_after[
            "patch_genuine_pair_count"
        ]
        == int(gates_config["changed_mask_genuine_intersection_pairs"]),
        "whole_intersection_count_exact": intersections_after["whole_genuine_pair_count"]
        == int(gates_config["whole_genuine_intersection_pairs"]),
        "no_new_whole_intersection_pairs": intersections_after[
            "whole_pair_identity_sha256"
        ]
        == intersections_before["whole_pair_identity_sha256"],
        "inherited_outside_pair_identity_exact": intersections_after[
            "outside_only_pair_identity_sha256"
        ]
        == intersections_before["outside_only_pair_identity_sha256"],
        "seam_minimum_dot": seam_quality["minimum"]
        >= float(gates_config["minimum_outer_seam_normal_dot"]),
        "seam_median_dot": seam_quality["median"]
        >= float(gates_config["median_outer_seam_normal_dot"]),
        "seam_dihedral": seam_quality["maximum_dihedral_degrees"]
        <= float(gates_config["maximum_outer_seam_dihedral_degrees"]),
    }
    structural_diagnostic = {
        "schema_version": 1,
        "artifact_kind": "KIRA_R24_ATTEMPT17_EXPANDED_CARRIER_STRUCTURAL_DIAGNOSTIC",
        "attempt_id": EXPECTED_ATTEMPT_SLOT,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "expanded_mask": mask_record,
        "application": applied,
        "geometry_quality": quality,
        "intersections_before": intersections_before,
        "intersections_after": intersections_after,
        "checks": checks,
        "passed": all(checks.values()),
        "false_checks": sorted(name for name, passed in checks.items() if not passed),
        "blend_saved": False,
        "runtime_activated": False,
    }
    atomic_write_json(
        ACTIVE_OUTPUT / config["output"]["structural_diagnostic"],
        structural_diagnostic,
    )
    if not all(checks.values()):
        raise Attempt17Error(
            "Attempt 17 structural gates failed: "
            + ", ".join(name for name, passed in checks.items() if not passed)
        )

    review_directory = ACTIVE_OUTPUT / config["output"]["private_review_directory"]
    renders = render_evidence(body, mask_faces, applied, review_directory, config)
    source_hash_after_render = sha256_file(source_path)
    preserved_after = verify_preserved_attempts(config)
    attempt16_runtime_after = verify_attempt16_runtime(config)
    final_checks = {
        "source_hash_unchanged_after_render": source_hash_after_render
        == source_hash_before,
        "attempts_01_15_manifest_unchanged_after_render": preserved_after[
            "canonical_manifest_sha256"
        ]
        == preserved_before["canonical_manifest_sha256"],
        "attempt16_runtime_manifest_unchanged": attempt16_runtime_after[
            "canonical_manifest_sha256"
        ]
        == attempt16_runtime_before["canonical_manifest_sha256"],
        "blend_not_saved": True,
        "runtime_not_activated": True,
        "owner_visual_approval_pending": True,
    }
    if not all(final_checks.values()):
        raise Attempt17Error(
            "Attempt 17 final preservation gates failed: "
            + ", ".join(
                name for name, passed in final_checks.items() if not passed
            )
        )
    report = {
        "schema_version": 1,
        "artifact_kind": "KIRA_R24_ATTEMPT17_EXPANDED_CARRIER_NO_SAVE_SIMULATION",
        "attempt_id": EXPECTED_ATTEMPT_SLOT,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "STRUCTURAL_SIMULATION_PASS_VISUAL_OWNER_REVIEW_REQUIRED_NO_SAVE",
        "config": {
            "path": relative(config_path),
            "bytes": config_path.stat().st_size,
            "sha256": sha256_file(config_path),
        },
        "worker": {"path": relative(Path(__file__)), "sha256": sha256_file(Path(__file__))},
        "verified_bindings": verified_bindings,
        "preserved_attempts_before": preserved_before,
        "preserved_attempts_after": preserved_after,
        "attempt16_runtime_before": attempt16_runtime_before,
        "attempt16_runtime_after": attempt16_runtime_after,
        "old_patch": old_record,
        "expanded_mask": mask_record,
        "freeze_ledger_before": ledger_before,
        "freeze_ledger_after": ledger_after,
        "mask_uv_weight_sha256_before": attribute_hash_before,
        "mask_uv_weight_sha256_after": attribute_hash_after,
        "application": applied,
        "geometry_quality": quality,
        "intersections_before": intersections_before,
        "intersections_after": intersections_after,
        "checks": checks,
        "renders": renders,
        "final_checks": final_checks,
        "truth_boundary": config["truth_boundary"],
        "operations": {
            "donor_loaded": False,
            "literal_donor_geometry_used": False,
            "mesh_mutated_in_memory": True,
            "blend_saved": False,
            "exported": False,
            "runtime_activated": False,
        },
    }
    atomic_write_json(ACTIVE_OUTPUT / config["output"]["report"], report)
    print(json.dumps({"status": report["status"], "output": relative(ACTIVE_OUTPUT)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        if ACTIVE_OUTPUT is not None:
            failure = {
                "schema_version": 1,
                "artifact_kind": "KIRA_R24_ATTEMPT17_EXPANDED_CARRIER_FAILURE",
                "attempt_id": EXPECTED_ATTEMPT_SLOT,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "status": "FAILED_CLOSED_NO_SAVE",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "worker": {
                    "path": relative(Path(__file__)),
                    "sha256": sha256_file(Path(__file__)),
                },
                "source": {
                    "path": "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/attempt_06/kira_r19_bald_targeted_material_movement_correction.blend",
                    "sha256": sha256_file(
                        ROOT
                        / "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/attempt_06/kira_r19_bald_targeted_material_movement_correction.blend"
                    ),
                },
                "structural_diagnostic": (
                    {
                        "path": relative(ACTIVE_OUTPUT / "STRUCTURAL_DIAGNOSTIC.json"),
                        "sha256": sha256_file(ACTIVE_OUTPUT / "STRUCTURAL_DIAGNOSTIC.json"),
                    }
                    if (ACTIVE_OUTPUT / "STRUCTURAL_DIAGNOSTIC.json").is_file()
                    else None
                ),
                "blend_saved": False,
                "runtime_activated": False,
            }
            atomic_write_json(ACTIVE_OUTPUT / "FAILURE.json", failure)
        raise
