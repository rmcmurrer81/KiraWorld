"""Hash-bound Attempt 20 derivation with deterministic CDT sanitation.

The wrapper preserves Attempt 19 and its evidence. It materializes the exact
Attempt 19 derived Blender source, adds only seed/face sanitation and disk
validation, corrects current-attempt evidence labels, and executes no-save
Attempt 20 source. Blender is not imported when this wrapper is inspected by
the static regression suite.
"""

from __future__ import annotations

import ast
import copy
from collections import deque
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260807"
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT20_CONFIG.json"
)
ATTEMPT19_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt19.py"
)
ATTEMPT18_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt18.py"
)
EXPECTED_CONFIG_SHA256 = (
    "95fb35b83469ba259a1379b640a7972bc763813a38a74e01816f29cf3603ddee"
)
EXPECTED_ATTEMPT19_WORKER_SHA256 = (
    "92163ce2ae8459617f7bee206523c836c946ba7b825e5493a64ed5f47a2630ff"
)


def load_attempt19_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "attempt20_sealed_attempt19_provider", ATTEMPT19_WORKER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Attempt 20 could not load the sealed Attempt 19 provider")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = (ROOT / value).resolve(strict=True)
    root = ROOT.resolve()
    if root != path and root not in path.parents:
        raise RuntimeError(f"Attempt 20 binding escapes project: {value}")
    return path


def verify_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    path = project_path(str(record["path"]))
    actual_bytes = path.stat().st_size
    actual_sha256 = sha256_file(path)
    if actual_bytes != int(record["bytes"]):
        raise RuntimeError(f"Attempt 20 bound byte count drifted: {name}")
    if actual_sha256 != str(record["sha256"]).lower():
        raise RuntimeError(f"Attempt 20 bound hash drifted: {name}: {actual_sha256}")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": actual_bytes,
        "sha256": actual_sha256,
    }


def load_overlay(config_path: Path) -> dict[str, Any]:
    config_path = config_path.resolve(strict=True)
    if config_path != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 20 requires the exact sealed overlay config path")
    actual = sha256_file(config_path)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 20 overlay config hash drifted: {actual}")
    overlay = json.loads(config_path.read_text(encoding="utf-8"))
    if (
        overlay.get("attempt_id") != "attempt_20"
        or overlay.get("status") != "STATIC_PREPARED_NOT_RUN"
        or overlay.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 20 overlay identity drifted")
    forbidden = (
        "blend_save_allowed",
        "export_allowed",
        "runtime_activation_allowed",
        "boundary_or_seam_movement_allowed",
        "quality_gate_reduction_allowed",
        "geometry_changes_beyond_cdt_sanitation_allowed",
    )
    if any(bool(overlay["scope"][name]) for name in forbidden):
        raise RuntimeError("Attempt 20 scope is not bounded and no-save")
    return overlay


def verify_overlay_bindings(overlay: Mapping[str, Any]) -> dict[str, Any]:
    verified = {
        name: verify_record(name, record)
        for name, record in overlay["bindings"].items()
    }
    verified["proposal"] = verify_record("proposal", overlay["proposal"])
    if verified["attempt19_worker"]["sha256"] != EXPECTED_ATTEMPT19_WORKER_SHA256:
        raise RuntimeError("Attempt 20 provider constant and binding disagree")
    preserved = overlay["preserved_attempts_15_19"]
    rows = [verified[name] for name in preserved["binding_names"]]
    if len(rows) != int(preserved["file_count"]):
        raise RuntimeError("Attempt 15-19 preserved file count drifted")
    if sum(int(row["bytes"]) for row in rows) != int(preserved["total_bytes"]):
        raise RuntimeError("Attempt 15-19 preserved byte total drifted")
    return verified


def load_attempt20_config(config_path: Path) -> dict[str, Any]:
    overlay = load_overlay(config_path)
    verified = verify_overlay_bindings(overlay)
    provider = load_attempt19_module()
    base_config_path = project_path(overlay["bindings"]["attempt19_config"]["path"])
    merged = provider.load_attempt19_config(base_config_path)
    if merged.get("attempt_id") != overlay["base"]["expected_config_attempt_id"]:
        raise RuntimeError("Attempt 19 materialized base identity drifted")
    merged = copy.deepcopy(merged)
    merged["schema"] = (
        "kira.avatar.r24.blackproject_local_reconstruction_attempt20.config.v1"
    )
    merged["attempt_id"] = "attempt_20"
    merged["output"] = copy.deepcopy(overlay["output"])
    merged["replacement"].update(copy.deepcopy(overlay["sanitation_parameters"]))
    merged["attempt20_diagnosis"] = copy.deepcopy(overlay["diagnosis"])
    merged["attempt20_unchanged_hard_gates"] = copy.deepcopy(
        overlay["unchanged_hard_gates"]
    )
    merged["attempt20_evidence_label_contract"] = copy.deepcopy(
        overlay["evidence_label_contract"]
    )
    merged["attempt20_truth"] = copy.deepcopy(overlay["truth"])
    merged["inputs"].update(
        {
            f"attempt20_bound_{name}": {
                "path": record["path"],
                "bytes": record["bytes"],
                "sha256": record["sha256"],
            }
            for name, record in verified.items()
        }
    )
    unchanged = overlay["unchanged_hard_gates"]
    if float(merged["replacement"]["minimum_new_triangle_angle_degrees"]) != float(
        unchanged["minimum_new_triangle_angle_degrees"]
    ):
        raise RuntimeError("Attempt 20 minimum-angle gate drifted")
    if float(merged["hard_gates"]["minimum_new_triangle_angle_degrees"]) != float(
        unchanged["minimum_new_triangle_angle_degrees"]
    ):
        raise RuntimeError("Attempt 20 structural minimum-angle gate drifted")
    if float(merged["replacement"]["minimum_new_triangle_world_area_m2"]) != float(
        unchanged["minimum_new_triangle_world_area_m2"]
    ):
        raise RuntimeError("Attempt 20 minimum-area gate drifted")
    return merged


SANITATION_HELPERS = r'''
def cdt_tolerances(
    boundary: Sequence[Vector], epsilon: float, config: Mapping[str, Any]
) -> dict[str, float]:
    if len(boundary) < 3:
        raise RuntimeError("CDT boundary requires at least three vertices")
    minimum_x = min(float(value.x) for value in boundary)
    maximum_x = max(float(value.x) for value in boundary)
    minimum_y = min(float(value.y) for value in boundary)
    maximum_y = max(float(value.y) for value in boundary)
    diagonal = math.hypot(maximum_x - minimum_x, maximum_y - minimum_y)
    if not math.isfinite(diagonal) or diagonal <= 0.0:
        raise RuntimeError("CDT boundary diagonal is not positive and finite")
    point = max(
        float(config["cdt_point_tolerance_absolute_m"]),
        float(epsilon) * float(config["cdt_point_tolerance_epsilon_multiplier"]),
        diagonal
        * float(config["cdt_point_tolerance_relative_to_boundary_diagonal"]),
    )
    twice_area = max(
        point * point,
        diagonal
        * diagonal
        * float(
            config[
                "cdt_twice_area_tolerance_relative_to_boundary_diagonal_squared"
            ]
        ),
    )
    return {
        "boundary_diagonal_m": float(diagonal),
        "point_tolerance_m": float(point),
        "twice_area_tolerance_m2": float(twice_area),
    }


def sanitize_cdt_seed_points(
    boundary: Sequence[Vector],
    seeds: Sequence[Vector],
    epsilon: float,
    config: Mapping[str, Any],
) -> tuple[list[Vector], dict[str, Any]]:
    tolerances = cdt_tolerances(boundary, epsilon, config)
    point_tolerance = tolerances["point_tolerance_m"]
    accepted: list[Vector] = []
    rejected_near_boundary = 0
    rejected_near_seed = 0
    for candidate in seeds:
        if any((candidate - value).length <= point_tolerance for value in boundary):
            rejected_near_boundary += 1
            continue
        if any((candidate - value).length <= point_tolerance for value in accepted):
            rejected_near_seed += 1
            continue
        accepted.append(candidate.copy())
    return accepted, {
        "input_seed_count": len(seeds),
        "accepted_seed_count": len(accepted),
        "rejected_near_boundary_count": rejected_near_boundary,
        "rejected_near_seed_count": rejected_near_seed,
        **tolerances,
    }


def cdt_seed_is_separated(
    candidate: Vector,
    boundary: Sequence[Vector],
    seeds: Sequence[Vector],
    epsilon: float,
    config: Mapping[str, Any],
) -> bool:
    tolerance = cdt_tolerances(boundary, epsilon, config)["point_tolerance_m"]
    return all(
        (candidate - value).length > tolerance
        for value in list(boundary) + list(seeds)
    )


def sanitize_cdt_output(
    coordinates: Sequence[Vector],
    faces: Sequence[Sequence[int]],
    original_vertices: Sequence[Sequence[int]],
    boundary_count: int,
    boundary: Sequence[Vector],
    epsilon: float,
    config: Mapping[str, Any],
) -> tuple[list[Vector], list[list[int]], list[Sequence[int]], dict[str, Any]]:
    tolerances = cdt_tolerances(boundary, epsilon, config)
    point_tolerance = tolerances["point_tolerance_m"]
    area_tolerance = tolerances["twice_area_tolerance_m2"]
    removed = {
        "repeated_index": 0,
        "coincident_coordinate": 0,
        "collinear_or_near_zero_area": 0,
        "duplicate_face": 0,
    }
    kept: list[list[int]] = []
    seen_faces: set[tuple[int, int, int]] = set()
    for raw_face in faces:
        if len(raw_face) != 3:
            raise RuntimeError("constrained Delaunay output was not all triangles")
        face = [int(value) for value in raw_face]
        if any(value < 0 or value >= len(coordinates) for value in face):
            raise RuntimeError("constrained Delaunay face index escaped coordinates")
        if len(set(face)) != 3:
            removed["repeated_index"] += 1
            continue
        points = [coordinates[index] for index in face]
        if any(
            (points[first] - points[second]).length <= point_tolerance
            for first, second in ((0, 1), (1, 2), (2, 0))
        ):
            removed["coincident_coordinate"] += 1
            continue
        if abs(orient2d(points[0], points[1], points[2])) <= area_tolerance:
            removed["collinear_or_near_zero_area"] += 1
            continue
        key = tuple(sorted(face))
        if key in seen_faces:
            removed["duplicate_face"] += 1
            continue
        seen_faces.add(key)
        kept.append(face)
    if not kept:
        raise RuntimeError("CDT sanitation removed every face")

    boundary_output_old: dict[int, int] = {}
    for output_index, sources in enumerate(original_vertices):
        for source_index in sources:
            source_index = int(source_index)
            if source_index < boundary_count:
                if source_index in boundary_output_old:
                    raise RuntimeError("constrained Delaunay duplicated a boundary vertex")
                boundary_output_old[source_index] = output_index
    if len(boundary_output_old) != boundary_count:
        raise RuntimeError("constrained Delaunay omitted a boundary vertex")

    used = {index for face in kept for index in face}
    used.update(boundary_output_old.values())
    order = sorted(used)
    remap = {old: new for new, old in enumerate(order)}
    compact_coordinates = [coordinates[index] for index in order]
    compact_original = [original_vertices[index] for index in order]
    compact_faces = [[remap[index] for index in face] for face in kept]
    diagnostics = {
        "input_coordinate_count": len(coordinates),
        "output_coordinate_count": len(compact_coordinates),
        "compacted_unused_nonboundary_point_count": len(coordinates) - len(order),
        "input_face_count": len(faces),
        "output_face_count": len(compact_faces),
        "removed_faces": removed,
        **tolerances,
    }
    return compact_coordinates, compact_faces, compact_original, diagnostics


def validate_cdt_disk(
    faces: Sequence[Sequence[int]],
    boundary_output: Mapping[int, int],
    boundary_count: int,
) -> dict[str, Any]:
    if set(int(value) for value in boundary_output) != set(range(boundary_count)):
        raise RuntimeError("sanitized CDT boundary source mapping is incomplete")
    edge_counts: dict[tuple[int, int], int] = {}
    edge_faces: dict[tuple[int, int], list[int]] = {}
    used: set[int] = set()
    for face_index, face in enumerate(faces):
        if len(face) != 3 or len(set(int(value) for value in face)) != 3:
            raise RuntimeError("sanitized CDT retained a repeated-index face")
        triangle = [int(value) for value in face]
        used.update(triangle)
        for first, second in zip(triangle, triangle[1:] + triangle[:1]):
            edge = tuple(sorted((first, second)))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
            edge_faces.setdefault(edge, []).append(face_index)
    if any(count not in (1, 2) for count in edge_counts.values()):
        raise RuntimeError("sanitized CDT has nonmanifold edge incidence")
    constrained = {
        tuple(
            sorted(
                (
                    int(boundary_output[index]),
                    int(boundary_output[(index + 1) % boundary_count]),
                )
            )
        )
        for index in range(boundary_count)
    }
    open_edges = {edge for edge, count in edge_counts.items() if count == 1}
    if open_edges != constrained:
        raise RuntimeError("sanitized CDT open edges do not equal exact boundary")
    if not set(int(value) for value in boundary_output.values()).issubset(used):
        raise RuntimeError("sanitized CDT left an exact boundary vertex unused")
    euler = len(used) - len(edge_counts) + len(faces)
    if euler != 1:
        raise RuntimeError(f"sanitized CDT is not a disk: euler={euler}")
    adjacency = [set() for _ in faces]
    for linked in edge_faces.values():
        if len(linked) == 2:
            first, second = linked
            adjacency[first].add(second)
            adjacency[second].add(first)
    visited = {0}
    queue = deque([0])
    while queue:
        current = queue.popleft()
        for other in adjacency[current]:
            if other not in visited:
                visited.add(other)
                queue.append(other)
    if len(visited) != len(faces):
        raise RuntimeError("sanitized CDT has multiple face components")
    return {
        "used_vertex_count": len(used),
        "edge_count": len(edge_counts),
        "face_count": len(faces),
        "boundary_edge_count": len(open_edges),
        "face_component_count": 1,
        "euler_characteristic": euler,
        "exact_boundary_is_complete_open_edge_set": True,
    }
'''


def exact_replace(source: str, old: str, new: str, name: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Attempt 20 replacement drifted: {name}: {count}")
    return source.replace(old, new, 1)


def derive_attempt20_source(source19: str) -> str:
    source = source19
    source = exact_replace(
        source,
        "def run_cdt(\n",
        SANITATION_HELPERS + "\n\ndef run_cdt(\n",
        "insert sanitation helpers",
    )
    source = exact_replace(
        source,
        "def run_cdt(\n"
        "    boundary: Sequence[Vector], seeds: Sequence[Vector], epsilon: float\n"
        ") -> dict[str, Any]:\n"
        "    inputs = [Vector((float(value.x), float(value.y))) for value in boundary + list(seeds)]\n",
        "def run_cdt(\n"
        "    boundary: Sequence[Vector],\n"
        "    seeds: Sequence[Vector],\n"
        "    epsilon: float,\n"
        "    config: Mapping[str, Any],\n"
        ") -> dict[str, Any]:\n"
        "    clean_seeds, seed_sanitation = sanitize_cdt_seed_points(\n"
        "        boundary, seeds, epsilon, config\n"
        "    )\n"
        "    inputs = [\n"
        "        Vector((float(value.x), float(value.y)))\n"
        "        for value in list(boundary) + clean_seeds\n"
        "    ]\n",
        "run_cdt signature and seed sanitation",
    )
    source = exact_replace(
        source,
        "    coordinates, _edges, faces, original_vertices, _oe, _of = output\n"
        "    if any(len(face) != 3 for face in faces):\n"
        "        raise RuntimeError(\"constrained Delaunay output was not all triangles\")\n",
        "    coordinates, _edges, faces, original_vertices, _oe, _of = output\n"
        "    if any(len(face) != 3 for face in faces):\n"
        "        raise RuntimeError(\"constrained Delaunay output was not all triangles\")\n"
        "    coordinates, faces, original_vertices, cdt_sanitation = sanitize_cdt_output(\n"
        "        list(coordinates),\n"
        "        faces,\n"
        "        original_vertices,\n"
        "        boundary_count,\n"
        "        boundary,\n"
        "        epsilon,\n"
        "        config,\n"
        "    )\n",
        "sanitize every CDT output",
    )
    source = exact_replace(
        source,
        "    if maximum_boundary_delta > epsilon * 4.0:\n"
        "        raise RuntimeError(\"constrained Delaunay moved the local boundary\")\n"
        "    return {\n",
        "    if maximum_boundary_delta > epsilon * 4.0:\n"
        "        raise RuntimeError(\"constrained Delaunay moved the local boundary\")\n"
        "    disk_topology = validate_cdt_disk(faces, boundary_output, boundary_count)\n"
        "    return {\n",
        "validate sanitized disk",
    )
    source = exact_replace(
        source,
        '        "maximum_boundary_delta_2d_m": float(maximum_boundary_delta),\n'
        "    }\n\n\n"
        "def quality_refined_cdt(\n",
        '        "maximum_boundary_delta_2d_m": float(maximum_boundary_delta),\n'
        '        "seed_sanitation": seed_sanitation,\n'
        '        "cdt_sanitation": cdt_sanitation,\n'
        '        "disk_topology": disk_topology,\n'
        "    }\n\n\n"
        "def quality_refined_cdt(\n",
        "return sanitation diagnostics",
    )
    source = exact_replace(
        source,
        "    base = run_cdt(boundary, [], epsilon)\n",
        "    base = run_cdt(boundary, [], epsilon, config)\n",
        "base CDT config",
    )
    source = exact_replace(
        source,
        "    ]\n"
        "    seen = {\n"
        "        (round(float(value.x), 14), round(float(value.y), 14)) for value in seeds\n"
        "    }\n",
        "    ]\n"
        "    seeds, initial_seed_sanitation = sanitize_cdt_seed_points(\n"
        "        boundary, seeds, epsilon, config\n"
        "    )\n"
        "    seen = {\n"
        "        (round(float(value.x), 14), round(float(value.y), 14)) for value in seeds\n"
        "    }\n",
        "initial seed deduplication",
    )
    source = exact_replace(
        source,
        "        result = run_cdt(boundary, seeds, epsilon)\n",
        "        result = run_cdt(boundary, seeds, epsilon, config)\n",
        "refinement CDT config",
    )
    source = exact_replace(
        source,
        '            result["minimum_2d_triangle_angle_degrees"] = minimum\n'
        "            return result\n",
        '            result["minimum_2d_triangle_angle_degrees"] = minimum\n'
        '            result["initial_seed_sanitation"] = initial_seed_sanitation\n'
        "            return result\n",
        "record initial seed sanitation",
    )
    source = exact_replace(
        source,
        "            if key not in seen and all(\n"
        "                (candidate - value).length > epsilon * 16.0\n"
        "                for value in boundary + list(seeds)\n"
        "            ):\n",
        "            if key not in seen and cdt_seed_is_separated(\n"
        "                candidate, boundary, seeds, epsilon, config\n"
        "            ):\n",
        "scale-aware candidate separation",
    )
    source = exact_replace(
        source,
        '        "maximum_cdt_boundary_delta_2d_m": cdt["maximum_boundary_delta_2d_m"],\n',
        '        "maximum_cdt_boundary_delta_2d_m": cdt["maximum_boundary_delta_2d_m"],\n'
        '        "cdt_seed_sanitation": cdt["seed_sanitation"],\n'
        '        "cdt_face_sanitation": cdt["cdt_sanitation"],\n'
        '        "cdt_disk_topology": cdt["disk_topology"],\n'
        '        "initial_seed_sanitation": cdt["initial_seed_sanitation"],\n',
        "surface sanitation evidence",
    )
    source = exact_replace(
        source,
        "    config = load_attempt19_config(config_path)\n",
        "    config = load_attempt20_config(config_path)\n",
        "Attempt 20 config loader",
    )
    source = exact_replace(
        source,
        '            "status": "NO_SAVE_ATTEMPT18_FAILED_PRESERVED_FOR_DIAGNOSIS",\n',
        '            "status": "NO_SAVE_ATTEMPT20_FAILED_PRESERVED_FOR_DIAGNOSIS",\n',
        "correct current-attempt failure status",
    )
    for old, new in (
        ("attempt_19", "attempt_20"),
        ("attempt19", "attempt20"),
        ("Attempt 19", "Attempt 20"),
    ):
        if old not in source:
            raise RuntimeError(f"Attempt 19 identity token disappeared: {old}")
        source = source.replace(old, new)
    if any(token in source for token in ("ATTEMPT18", "attempt_19", "attempt19", "Attempt 19")):
        raise RuntimeError("Attempt 20 derived source retained a stale evidence identity")
    tree = ast.parse(source)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    if not any(
        isinstance(node, ast.FunctionDef) and node.name == "sanitize_cdt_output"
        for node in tree.body
    ):
        raise RuntimeError("Attempt 20 sanitation helper was not inserted")
    return source


def main() -> None:
    if sha256_file(ATTEMPT19_WORKER) != EXPECTED_ATTEMPT19_WORKER_SHA256:
        raise RuntimeError("Attempt 19 worker changed before Attempt 20 derivation")
    provider = load_attempt19_module()
    attempt19_before = ATTEMPT19_WORKER.read_bytes()
    attempt18_before = ATTEMPT18_WORKER.read_bytes()
    source19 = provider.derive_attempt19_source(attempt18_before.decode("utf-8"))
    source20 = derive_attempt20_source(source19)
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
        "load_attempt20_config": load_attempt20_config,
    }
    try:
        exec(
            compile(
                source20,
                str(Path(__file__).resolve()) + "::derived",
                "exec",
            ),
            namespace,
            namespace,
        )
    finally:
        if ATTEMPT19_WORKER.read_bytes() != attempt19_before:
            raise RuntimeError("Attempt 19 worker changed during Attempt 20 execution")
        if ATTEMPT18_WORKER.read_bytes() != attempt18_before:
            raise RuntimeError("Attempt 18 worker changed during Attempt 20 execution")


if __name__ == "__main__":
    main()
