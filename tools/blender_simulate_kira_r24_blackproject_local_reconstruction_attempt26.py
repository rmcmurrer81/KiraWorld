"""Hash-bound Attempt 26 nearest-seed-pair altitude repair.

The wrapper derives sealed Attempt 25 and extends candidate admissibility with
the exact existing CDT face-sanitation tolerance applied to the two nearest
accepted seeds. Blender is not imported during static inspection.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260808"
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT26_CONFIG.json"
)
ATTEMPT25_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt25.py"
ATTEMPT24_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt24.py"
ATTEMPT23_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt23.py"
ATTEMPT22_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt22.py"
ATTEMPT21_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt21.py"
ATTEMPT20_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt20.py"
ATTEMPT19_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt19.py"
ATTEMPT18_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt18.py"
EXPECTED_CONFIG_SHA256 = "67fe732f4857cf265fa2f36be24194d1f97762dcfb01637afbe13a3206a0cbec"
EXPECTED_ATTEMPT25_WORKER_SHA256 = "613298da0d93d24184d049ffb17f20e2bbc5d5bc387f05ae2719e017d7baa30a"


def load_attempt25_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "attempt26_sealed_attempt25_provider", ATTEMPT25_WORKER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Attempt 26 could not load the sealed Attempt 25 provider")
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
        raise RuntimeError(f"Attempt 26 binding escapes project: {value}")
    return path


def verify_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    path = project_path(str(record["path"]))
    actual_bytes = path.stat().st_size
    actual_sha256 = sha256_file(path)
    if actual_bytes != int(record["bytes"]):
        raise RuntimeError(f"Attempt 26 bound byte count drifted: {name}")
    if actual_sha256 != str(record["sha256"]).lower():
        raise RuntimeError(f"Attempt 26 bound hash drifted: {name}: {actual_sha256}")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": actual_bytes,
        "sha256": actual_sha256,
    }


def load_overlay(config_path: Path) -> dict[str, Any]:
    config_path = config_path.resolve(strict=True)
    if config_path != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 26 requires the exact sealed overlay config path")
    actual = sha256_file(config_path)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 26 overlay config hash drifted: {actual}")
    overlay = json.loads(config_path.read_text(encoding="utf-8"))
    if (
        overlay.get("attempt_id") != "attempt_26"
        or overlay.get("status") != "STATIC_BOUNDED_REPAIR_PREPARED_NOT_RUN"
        or overlay.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 26 overlay identity drifted")
    required_true = (
        "append_only",
        "private",
        "inactive",
        "unassigned",
        "unpublished",
        "repair_simulation_only",
        "candidate_seed_policy_change_allowed",
        "in_memory_local_body_reconstruction_allowed_during_later_reviewed_run",
    )
    if not all(bool(overlay["scope"][name]) for name in required_true):
        raise RuntimeError("Attempt 26 repair scope lost a required private gate")
    forbidden = (
        "blend_save_allowed",
        "export_allowed",
        "runtime_activation_allowed",
        "boundary_or_seam_movement_allowed",
        "quality_gate_reduction_allowed",
        "render_allowed",
        "boundary_repair_allowed",
        "generic_hole_fill_allowed",
        "sanitation_weakening_allowed",
        "whole_polygon_retriangulation_allowed",
    )
    if any(bool(overlay["scope"][name]) for name in forbidden):
        raise RuntimeError("Attempt 26 scope permits a forbidden operation")
    return overlay


def verify_overlay_bindings(overlay: Mapping[str, Any]) -> dict[str, Any]:
    verified = {
        name: verify_record(name, record)
        for name, record in overlay["bindings"].items()
    }
    verified["proposal"] = verify_record("proposal", overlay["proposal"])
    if verified["attempt25_worker"]["sha256"] != EXPECTED_ATTEMPT25_WORKER_SHA256:
        raise RuntimeError("Attempt 26 provider constant and binding disagree")
    preserved = overlay["preserved_attempt25_package"]
    rows = [verified[name] for name in preserved["binding_names"]]
    if len(rows) != int(preserved["file_count"]):
        raise RuntimeError("Attempt 25 preserved package file count drifted")
    if sum(int(row["bytes"]) for row in rows) != int(preserved["total_bytes"]):
        raise RuntimeError("Attempt 25 preserved package byte total drifted")
    return verified


def validate_policy_contract(overlay: Mapping[str, Any]) -> None:
    policy = overlay["candidate_admissibility_policy"]
    captured = policy["captured_case"]
    pair_length = float(captured["nearest_seed_pair_length_m"])
    twice_area = float(captured["pair_twice_area_m2"])
    actual_altitude = twice_area / pair_length
    sanitation_floor = (
        float(captured["sanitation_twice_area_tolerance_m2"]) / pair_length
    )
    required = max(float(captured["point_floor_m"]), sanitation_floor)
    checks = {
        "actual_pair_altitude_m": actual_altitude,
        "sanitation_pair_altitude_floor_m": sanitation_floor,
        "required_pair_altitude_m": required,
    }
    for name, actual in checks.items():
        expected = float(captured[name])
        if not math.isclose(actual, expected, rel_tol=1.0e-12, abs_tol=1.0e-20):
            raise RuntimeError(f"Attempt 26 captured policy derivation drifted: {name}")
    if policy["candidate_order"] != ["triangle_incenter", "triangle_centroid"]:
        raise RuntimeError("Attempt 26 candidate order drifted")
    if bool(policy["new_arbitrary_length_constant"]) or bool(
        policy["new_arbitrary_multiplier"]
    ):
        raise RuntimeError("Attempt 26 introduced an arbitrary candidate scale")


def load_attempt26_config(config_path: Path) -> dict[str, Any]:
    overlay = load_overlay(config_path)
    validate_policy_contract(overlay)
    verified = verify_overlay_bindings(overlay)
    provider = load_attempt25_module()
    base_config_path = project_path(overlay["bindings"]["attempt25_config"]["path"])
    merged = provider.load_attempt25_config(base_config_path)
    if merged.get("attempt_id") != overlay["base"]["expected_config_attempt_id"]:
        raise RuntimeError("Attempt 25 materialized base identity drifted")
    merged = copy.deepcopy(merged)
    merged["schema"] = "kira.avatar.r24.blackproject_local_reconstruction_attempt26.config.v1"
    merged["attempt_id"] = "attempt_26"
    merged["output"] = copy.deepcopy(overlay["output"])
    path_contract = overlay["failure_capture_path_contract"]
    expected_relative = (
        f'{overlay["output"]["root"]}/'
        f'{overlay["output"]["cdt_candidate_repair_failure"]}'
    )
    if path_contract["project_relative_path"] != expected_relative:
        raise RuntimeError("Attempt 26 failure path contract disagrees with output")
    merged["replacement"][path_contract["replacement_key"]] = expected_relative
    merged["attempt26_diagnosis"] = copy.deepcopy(overlay["diagnosis"])
    merged["attempt26_candidate_admissibility_policy"] = copy.deepcopy(
        overlay["candidate_admissibility_policy"]
    )
    merged["attempt26_repair_contract"] = copy.deepcopy(overlay["repair_contract"])
    merged["attempt26_unchanged_hard_gates"] = copy.deepcopy(
        overlay["unchanged_hard_gates"]
    )
    merged["attempt26_evidence_label_contract"] = copy.deepcopy(
        overlay["evidence_label_contract"]
    )
    merged["attempt26_truth"] = copy.deepcopy(overlay["truth"])
    merged["inputs"].update(
        {
            f"attempt26_bound_{name}": {
                "path": record["path"],
                "bytes": record["bytes"],
                "sha256": record["sha256"],
            }
            for name, record in verified.items()
        }
    )
    unchanged = overlay["unchanged_hard_gates"]
    for location in ("replacement", "hard_gates"):
        if float(merged[location]["minimum_new_triangle_angle_degrees"]) != float(
            unchanged["minimum_new_triangle_angle_degrees"]
        ):
            raise RuntimeError(f"Attempt 26 {location} minimum-angle gate drifted")
    if float(merged["replacement"]["minimum_new_triangle_world_area_m2"]) != float(
        unchanged["minimum_new_triangle_world_area_m2"]
    ):
        raise RuntimeError("Attempt 26 minimum-area gate drifted")
    return merged


PAIR_ALTITUDE_DIAGNOSTICS = r'''def attempt26_candidate_separation_diagnostics(
    candidate: Vector,
    method: str,
    local_points: Sequence[Vector],
    boundary: Sequence[Vector],
    seeds: Sequence[Vector],
    epsilon: float,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    if len(local_points) != 3:
        raise RuntimeError("Attempt 26 candidate policy requires one triangle")
    tolerances = cdt_tolerances(boundary, epsilon, config)
    edge_lengths = [
        float((local_points[first] - local_points[second]).length)
        for first, second in ((0, 1), (1, 2), (2, 0))
    ]
    if any(not math.isfinite(value) or value <= 0.0 for value in edge_lengths):
        raise RuntimeError("Attempt 26 candidate policy received a degenerate local edge")
    local_shortest = min(edge_lengths)
    local_longest = max(edge_lengths)
    minimum_area = float(config["minimum_new_triangle_world_area_m2"])
    target_angle = float(config["minimum_new_triangle_angle_degrees"])
    if not math.isfinite(minimum_area) or minimum_area <= 0.0:
        raise RuntimeError("Attempt 26 minimum-area gate is not positive and finite")
    if not math.isfinite(target_angle) or not 0.0 < target_angle < 180.0:
        raise RuntimeError("Attempt 26 minimum-angle gate is outside (0,180)")
    area_altitude_floor = 2.0 * minimum_area / local_longest
    angle_altitude_floor = local_shortest * math.sin(math.radians(target_angle))
    point_floor = float(tolerances["point_tolerance_m"])
    required = max(point_floor, min(area_altitude_floor, angle_altitude_floor))
    references = [
        ("boundary", int(index), value)
        for index, value in enumerate(boundary)
    ] + [
        ("seed", int(index), value)
        for index, value in enumerate(seeds)
    ]
    if not references:
        raise RuntimeError("Attempt 26 candidate policy has no reference coordinates")
    distances = [
        (float((candidate - value).length), source, index)
        for source, index, value in references
    ]
    nearest_distance, nearest_source, nearest_index = min(
        distances, key=lambda value: (value[0], value[1], value[2])
    )
    point_separated = bool(nearest_distance > required)

    pair_diagnostics = {
        "nearest_seed_pair_available": False,
        "nearest_seed_pair_indices": [],
        "nearest_seed_pair_distances_m": [],
        "nearest_seed_pair_length_m": None,
        "nearest_seed_pair_twice_area_m2": None,
        "actual_pair_altitude_m": None,
        "sanitation_pair_altitude_floor_m": None,
        "required_pair_altitude_m": None,
        "nearest_seed_pair_non_degenerate": True,
    }
    if len(seeds) >= 2:
        nearest_seeds = sorted(
            (
                (float((candidate - value).length), int(index), value)
                for index, value in enumerate(seeds)
            ),
            key=lambda value: (value[0], value[1]),
        )[:2]
        first_distance, first_index, first_seed = nearest_seeds[0]
        second_distance, second_index, second_seed = nearest_seeds[1]
        pair_length = float((first_seed - second_seed).length)
        if not math.isfinite(pair_length) or pair_length <= point_floor:
            pair_non_degenerate = False
            twice_area = 0.0
            actual_pair_altitude = 0.0
            sanitation_pair_floor = math.inf
            required_pair_altitude = math.inf
        else:
            twice_area = abs(float(orient2d(first_seed, second_seed, candidate)))
            actual_pair_altitude = twice_area / pair_length
            sanitation_pair_floor = (
                float(tolerances["twice_area_tolerance_m2"]) / pair_length
            )
            required_pair_altitude = max(point_floor, sanitation_pair_floor)
            pair_non_degenerate = bool(
                actual_pair_altitude > required_pair_altitude
            )
        pair_diagnostics = {
            "nearest_seed_pair_available": True,
            "nearest_seed_pair_indices": [first_index, second_index],
            "nearest_seed_pair_distances_m": [first_distance, second_distance],
            "nearest_seed_pair_length_m": pair_length,
            "nearest_seed_pair_twice_area_m2": float(twice_area),
            "actual_pair_altitude_m": float(actual_pair_altitude),
            "sanitation_pair_altitude_floor_m": float(sanitation_pair_floor),
            "required_pair_altitude_m": float(required_pair_altitude),
            "nearest_seed_pair_non_degenerate": pair_non_degenerate,
        }
    pair_passes = bool(pair_diagnostics["nearest_seed_pair_non_degenerate"])
    admissible_geometry = bool(point_separated and pair_passes)
    if not point_separated:
        rejection_reason = "BELOW_AREA_ANGLE_LOCAL_EDGE_SEPARATION_FLOOR"
    elif not pair_passes:
        rejection_reason = "NEAREST_SEED_PAIR_ALTITUDE_AT_OR_BELOW_SANITATION_FLOOR"
    else:
        rejection_reason = None
    return {
        "policy_id": "minimum_area_angle_local_edge_and_nearest_seed_pair_altitude_v2",
        "method": str(method),
        "local_edge_lengths_m": edge_lengths,
        "local_shortest_edge_m": float(local_shortest),
        "local_longest_edge_m": float(local_longest),
        "point_floor_m": point_floor,
        "area_altitude_floor_m": float(area_altitude_floor),
        "angle_altitude_floor_m": float(angle_altitude_floor),
        "required_separation_m": float(required),
        "boundary_diagonal_m": float(tolerances["boundary_diagonal_m"]),
        "required_separation_relative_to_boundary_diagonal": float(
            required / tolerances["boundary_diagonal_m"]
        ),
        "nearest_reference_distance_m": float(nearest_distance),
        "nearest_reference_type": nearest_source,
        "nearest_reference_index": int(nearest_index),
        "separated_from_boundary_and_seeds": point_separated,
        **pair_diagnostics,
        "admissible_by_candidate_geometry": admissible_geometry,
        "rejection_reason": rejection_reason,
    }
'''


def exact_replace(source: str, old: str, new: str, name: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Attempt 26 replacement drifted: {name}: {count}")
    return source.replace(old, new, 1)


def replace_top_level_function(source: str, name: str, replacement: str) -> str:
    tree = ast.parse(source)
    matches = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Attempt 26 function replacement drifted: {name}: {len(matches)}")
    node = matches[0]
    lines = source.splitlines(keepends=True)
    return "".join(lines[: node.lineno - 1]) + replacement.rstrip() + "\n\n" + "".join(lines[node.end_lineno :])


def derive_attempt26_source(source25: str) -> str:
    source = replace_top_level_function(
        source25,
        "attempt25_candidate_separation_diagnostics",
        PAIR_ALTITUDE_DIAGNOSTICS,
    )
    source = exact_replace(
        source,
        '            eligible = bool(not duplicate and separation["separated_from_boundary_and_seeds"])',
        '            eligible = bool(not duplicate and separation["admissible_by_candidate_geometry"])',
        "pair-altitude eligibility",
    )
    old_policy = "minimum_area_angle_local_edge_separation_v1"
    new_policy = "minimum_area_angle_local_edge_and_nearest_seed_pair_altitude_v2"
    if old_policy not in source:
        raise RuntimeError("Attempt 25 policy identity disappeared")
    source = source.replace(old_policy, new_policy)
    source = exact_replace(
        source,
        '            "Attempt 25 candidate-admissibility repair still produced a CDT "\n'
        '            "mismatch; no-save stop before reconstruction"',
        '            "Attempt 25 nearest-seed-pair altitude repair still produced a "\n'
        '            "CDT mismatch; no-save stop before reconstruction"',
        "pair-altitude mismatch error",
    )
    for old, new in (
        ("attempt_25", "attempt_26"),
        ("attempt25", "attempt26"),
        ("Attempt 25", "Attempt 26"),
        ("ATTEMPT25", "ATTEMPT26"),
    ):
        if old not in source:
            raise RuntimeError(f"Attempt 25 identity token disappeared: {old}")
        source = source.replace(old, new)
    if any(
        token in source
        for token in ("ATTEMPT25", "attempt_25", "attempt25", "Attempt 25")
    ):
        raise RuntimeError("Attempt 26 derived source retained stale evidence identity")
    tree = ast.parse(source)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    required = {
        "attempt26_candidate_separation_diagnostics",
        "attempt26_assert_exact_boundary_and_disk",
        "quality_refined_cdt",
        "capture_attempt26_terminal_and_stop",
    }
    if not required.issubset(names):
        raise RuntimeError("Attempt 26 pair-altitude repair functions are absent")
    return source


def materialize_attempt25_source(provider: Any) -> str:
    provider24 = provider.load_attempt24_module()
    source24 = provider.materialize_attempt24_source(provider24)
    return provider.derive_attempt25_source(source24)


def main() -> None:
    if sha256_file(ATTEMPT25_WORKER) != EXPECTED_ATTEMPT25_WORKER_SHA256:
        raise RuntimeError("Attempt 25 worker changed before Attempt 26 derivation")
    provider = load_attempt25_module()
    preserved_paths = (
        ATTEMPT25_WORKER,
        ATTEMPT24_WORKER,
        ATTEMPT23_WORKER,
        ATTEMPT22_WORKER,
        ATTEMPT21_WORKER,
        ATTEMPT20_WORKER,
        ATTEMPT19_WORKER,
        ATTEMPT18_WORKER,
    )
    before = {path: path.read_bytes() for path in preserved_paths}
    source25 = materialize_attempt25_source(provider)
    source26 = derive_attempt26_source(source25)
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
        "load_attempt26_config": load_attempt26_config,
    }
    try:
        exec(
            compile(source26, str(Path(__file__).resolve()) + "::derived", "exec"),
            namespace,
            namespace,
        )
    finally:
        for path in preserved_paths:
            if path.read_bytes() != before[path]:
                raise RuntimeError(f"{path.name} changed during Attempt 26 execution")


if __name__ == "__main__":
    main()
