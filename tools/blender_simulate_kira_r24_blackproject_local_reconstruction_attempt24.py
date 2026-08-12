"""Hash-bound Attempt 24 first refinement-terminal diagnostic.

The wrapper derives sealed Attempt 23, passes exact CDT boundaries through
quality refinement, captures only the first actual boundary mismatch or another
exact refinement terminal, and stops before body reconstruction. Blender is not
imported during static inspection.
"""

from __future__ import annotations

import ast
import copy
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
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT24_CONFIG.json"
)
ATTEMPT23_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt23.py"
ATTEMPT22_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt22.py"
ATTEMPT21_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt21.py"
ATTEMPT20_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt20.py"
ATTEMPT19_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt19.py"
ATTEMPT18_WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt18.py"
EXPECTED_CONFIG_SHA256 = "2b3092446ecda7c916759ec5ef0508801a4b04ac6ecc7b09c81638e642d7adf3"
EXPECTED_ATTEMPT23_WORKER_SHA256 = "834b865ff1641963d1183e9e211a78d987c53e81eb69ff1d9784a04e5b5a7f6a"


def load_attempt23_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "attempt24_sealed_attempt23_provider", ATTEMPT23_WORKER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Attempt 24 could not load the sealed Attempt 23 provider")
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
        raise RuntimeError(f"Attempt 24 binding escapes project: {value}")
    return path


def verify_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    path = project_path(str(record["path"]))
    actual_bytes = path.stat().st_size
    actual_sha256 = sha256_file(path)
    if actual_bytes != int(record["bytes"]):
        raise RuntimeError(f"Attempt 24 bound byte count drifted: {name}")
    if actual_sha256 != str(record["sha256"]).lower():
        raise RuntimeError(f"Attempt 24 bound hash drifted: {name}: {actual_sha256}")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": actual_bytes,
        "sha256": actual_sha256,
    }


def load_overlay(config_path: Path) -> dict[str, Any]:
    config_path = config_path.resolve(strict=True)
    if config_path != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 24 requires the exact sealed overlay config path")
    actual = sha256_file(config_path)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 24 overlay config hash drifted: {actual}")
    overlay = json.loads(config_path.read_text(encoding="utf-8"))
    if (
        overlay.get("attempt_id") != "attempt_24"
        or overlay.get("status") != "STATIC_DIAGNOSTIC_PREPARED_NOT_RUN"
        or overlay.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 24 overlay identity drifted")
    forbidden = (
        "blend_save_allowed",
        "export_allowed",
        "runtime_activation_allowed",
        "boundary_or_seam_movement_allowed",
        "quality_gate_reduction_allowed",
        "body_geometry_mutation_allowed",
        "render_allowed",
        "boundary_repair_allowed",
        "generic_hole_fill_allowed",
        "whole_polygon_retriangulation_allowed",
    )
    if any(bool(overlay["scope"][name]) for name in forbidden):
        raise RuntimeError("Attempt 24 scope is not diagnostic-only and no-save")
    return overlay


def verify_overlay_bindings(overlay: Mapping[str, Any]) -> dict[str, Any]:
    verified = {
        name: verify_record(name, record)
        for name, record in overlay["bindings"].items()
    }
    verified["proposal"] = verify_record("proposal", overlay["proposal"])
    if verified["attempt23_worker"]["sha256"] != EXPECTED_ATTEMPT23_WORKER_SHA256:
        raise RuntimeError("Attempt 24 provider constant and binding disagree")
    preserved = overlay["preserved_attempt23_package"]
    rows = [verified[name] for name in preserved["binding_names"]]
    if len(rows) != int(preserved["file_count"]):
        raise RuntimeError("Attempt 23 preserved package file count drifted")
    if sum(int(row["bytes"]) for row in rows) != int(preserved["total_bytes"]):
        raise RuntimeError("Attempt 23 preserved package byte total drifted")
    return verified


def load_attempt24_config(config_path: Path) -> dict[str, Any]:
    overlay = load_overlay(config_path)
    verified = verify_overlay_bindings(overlay)
    provider = load_attempt23_module()
    base_config_path = project_path(overlay["bindings"]["attempt23_config"]["path"])
    merged = provider.load_attempt23_config(base_config_path)
    if merged.get("attempt_id") != overlay["base"]["expected_config_attempt_id"]:
        raise RuntimeError("Attempt 23 materialized base identity drifted")
    merged = copy.deepcopy(merged)
    merged["schema"] = "kira.avatar.r24.blackproject_local_reconstruction_attempt24.config.v1"
    merged["attempt_id"] = "attempt_24"
    merged["output"] = copy.deepcopy(overlay["output"])
    path_contract = overlay["diagnostic_path_contract"]
    expected_relative = (
        f'{overlay["output"]["root"]}/'
        f'{overlay["output"]["cdt_refinement_terminal"]}'
    )
    if path_contract["project_relative_path"] != expected_relative:
        raise RuntimeError("Attempt 24 terminal path contract disagrees with output")
    merged["replacement"][path_contract["replacement_key"]] = expected_relative
    merged["attempt24_diagnosis"] = copy.deepcopy(overlay["diagnosis"])
    merged["attempt24_refinement_capture_contract"] = copy.deepcopy(
        overlay["refinement_capture_contract"]
    )
    merged["attempt24_unchanged_hard_gates"] = copy.deepcopy(
        overlay["unchanged_hard_gates"]
    )
    merged["attempt24_evidence_label_contract"] = copy.deepcopy(
        overlay["evidence_label_contract"]
    )
    merged["attempt24_truth"] = copy.deepcopy(overlay["truth"])
    merged["inputs"].update(
        {
            f"attempt24_bound_{name}": {
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
            raise RuntimeError(f"Attempt 24 {location} minimum-angle gate drifted")
    if float(merged["replacement"]["minimum_new_triangle_world_area_m2"]) != float(
        unchanged["minimum_new_triangle_world_area_m2"]
    ):
        raise RuntimeError("Attempt 24 minimum-area gate drifted")
    return merged


REFINEMENT_TERMINAL_HELPERS = r'''
def resolve_attempt24_refinement_terminal_path(config: Mapping[str, Any]) -> Path:
    relative = Path(str(config["attempt24_cdt_refinement_terminal_project_path"]))
    if relative.is_absolute():
        raise RuntimeError("Attempt 24 terminal path must be project-relative")
    root = ROOT.resolve()
    resolved = (root / relative).resolve()
    if root != resolved and root not in resolved.parents:
        raise RuntimeError("Attempt 24 terminal path escapes project")
    return resolved


def atomic_write_attempt24_once(path: Path, payload: Mapping[str, Any]) -> None:
    if path.exists():
        raise RuntimeError("Attempt 24 terminal capture already exists; refusing overwrite")
    atomic_write_json(path, payload)


def attempt24_current_minimum_angle(
    coordinates: Sequence[Vector], faces: Sequence[Sequence[int]]
) -> float:
    return min(
        min(triangle_angles([coordinates[int(index)] for index in face]))
        for face in faces
    )


def build_attempt24_terminal_payload(
    terminal_reason: str,
    boundary_state: Mapping[str, Any],
    run_context: Mapping[str, Any],
    quality_diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "kira.avatar.r24.blackproject_attempt24.cdt_refinement_terminal.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "CAPTURED_FIRST_CDT_REFINEMENT_TERMINAL_NO_REPAIR",
        "attempt_id": "attempt_24",
        "terminal_reason": str(terminal_reason),
        "boundary_mismatch_detected": bool(boundary_state["mismatch_detected"]),
        "run_context": dict(run_context),
        "quality_diagnostics": dict(quality_diagnostics),
        "boundary_state": dict(boundary_state),
        "repair_applied": False,
        "body_geometry_mutation_reached": False,
        "reconstruction_reached": False,
        "render_reached": False,
        "blend_saved": False,
        "runtime_changed": False,
    }


def capture_attempt24_terminal_and_stop(
    terminal_reason: str,
    boundary_state: Mapping[str, Any],
    run_context: Mapping[str, Any],
    quality_diagnostics: Mapping[str, Any],
    config: Mapping[str, Any],
) -> None:
    payload = build_attempt24_terminal_payload(
        terminal_reason, boundary_state, run_context, quality_diagnostics
    )
    path = resolve_attempt24_refinement_terminal_path(config)
    atomic_write_attempt24_once(path, payload)
    if boundary_state["mismatch_detected"]:
        raise RuntimeError(
            "Attempt 24 captured first actual CDT boundary mismatch; "
            "diagnostic-only stop before reconstruction"
        )
    raise RuntimeError(
        "Attempt 24 captured exact CDT refinement terminal; "
        "diagnostic-only stop before reconstruction"
    )
'''


DIAGNOSTIC_QUALITY_REFINEMENT = r'''def quality_refined_cdt(
    boundary: Sequence[Vector], config: Mapping[str, Any]
) -> dict[str, Any]:
    epsilon = float(config["cdt_epsilon_m"])
    threshold = float(config["minimum_new_triangle_angle_degrees"])
    maximum_vertices = int(config["maximum_new_interior_vertex_count"])
    maximum_iterations = int(config["maximum_quality_refinement_iterations"])
    base_context = {
        "phase": "initial_zero_seed",
        "refinement_iteration": None,
        "requested_seed_count": 0,
        "previous_candidate_record": None,
    }
    base = run_cdt(boundary, [], epsilon, config, base_context)
    seeds = [
        dimension_safe_vector_mean([base["coordinates"][index] for index in face])
        for face in base["faces"]
    ]
    seeds, initial_seed_sanitation = sanitize_cdt_seed_points(
        boundary, seeds, epsilon, config
    )
    seen = {
        (round(float(value.x), 14), round(float(value.y), 14)) for value in seeds
    }
    previous_candidate_record: dict[str, Any] = {
        "source": "initial_exact_face_centroids",
        "seed_sanitation": initial_seed_sanitation,
        "resulting_seed_count": len(seeds),
    }
    result = None
    last_context: dict[str, Any] = base_context
    last_quality: dict[str, Any] = {}

    for iteration in range(maximum_iterations + 1):
        run_context = {
            "phase": "quality_refinement",
            "refinement_iteration": int(iteration),
            "requested_seed_count": len(seeds),
            "previous_candidate_record": previous_candidate_record,
        }
        result = run_cdt(boundary, seeds, epsilon, config, run_context)
        quality = []
        for face_index, face in enumerate(result["faces"]):
            points = [result["coordinates"][index] for index in face]
            angles = triangle_angles(points)
            quality.append((min(angles), face_index, face, points, angles))
        worst = min(quality, key=lambda value: value[0])
        minimum, worst_face_index, worst_face, points, worst_angles = worst
        last_context = run_context
        last_quality = {
            "minimum_2d_triangle_angle_degrees": float(minimum),
            "required_minimum_2d_triangle_angle_degrees": float(threshold),
            "refinement_iteration": int(iteration),
            "seed_count": len(seeds),
            "seed_cap": int(maximum_vertices),
            "iteration_cap": int(maximum_iterations),
            "worst_face_index": int(worst_face_index),
            "worst_face_output_indices": [int(value) for value in worst_face],
            "worst_face_coordinates": [
                [float(value.x), float(value.y)] for value in points
            ],
            "worst_face_angles_degrees": [float(value) for value in worst_angles],
            "candidate_diagnostics": [],
        }
        if minimum >= threshold:
            capture_attempt24_terminal_and_stop(
                "QUALITY_TARGET_MET_WITH_EXACT_BOUNDARY",
                result["boundary_diagnostic"],
                run_context,
                last_quality,
                config,
            )
        if len(seeds) >= maximum_vertices:
            capture_attempt24_terminal_and_stop(
                "SEED_CAP_REACHED_WITH_EXACT_BOUNDARY",
                result["boundary_diagnostic"],
                run_context,
                last_quality,
                config,
            )

        candidate_values = [
            ("triangle_incenter", triangle_incenter(points)),
            ("triangle_centroid", dimension_safe_vector_mean(points)),
        ]
        candidate_rows = []
        selected_index = None
        for candidate_index, (method, candidate) in enumerate(candidate_values):
            key = (round(float(candidate.x), 14), round(float(candidate.y), 14))
            duplicate = key in seen
            separated = (
                False
                if duplicate
                else cdt_seed_is_separated(
                    candidate, boundary, seeds, epsilon, config
                )
            )
            eligible = bool(not duplicate and separated)
            if selected_index is None and eligible:
                selected_index = candidate_index
            candidate_rows.append(
                {
                    "candidate_index": int(candidate_index),
                    "method": method,
                    "xy": [float(candidate.x), float(candidate.y)],
                    "rounded_key": [float(key[0]), float(key[1])],
                    "already_seen": duplicate,
                    "separated_from_boundary_and_seeds": separated,
                    "admissible": eligible,
                    "selected": False,
                }
            )
        if selected_index is not None:
            candidate_rows[selected_index]["selected"] = True
        last_quality["candidate_diagnostics"] = candidate_rows
        previous_candidate_record = {
            "source_iteration": int(iteration),
            "minimum_2d_triangle_angle_degrees": float(minimum),
            "worst_face_index": int(worst_face_index),
            "worst_face_output_indices": [int(value) for value in worst_face],
            "candidate_diagnostics": candidate_rows,
            "selected_candidate_index": selected_index,
        }
        if selected_index is None:
            capture_attempt24_terminal_and_stop(
                "NO_ADMISSIBLE_CANDIDATE_WITH_EXACT_BOUNDARY",
                result["boundary_diagnostic"],
                run_context,
                last_quality,
                config,
            )
        selected = candidate_values[selected_index][1]
        selected_key = (
            round(float(selected.x), 14),
            round(float(selected.y), 14),
        )
        seeds.append(selected)
        seen.add(selected_key)

    if result is None:
        raise RuntimeError("Attempt 24 refinement produced no exact result")
    capture_attempt24_terminal_and_stop(
        "ITERATION_CAP_EXHAUSTED_WITH_EXACT_BOUNDARY",
        result["boundary_diagnostic"],
        last_context,
        last_quality,
        config,
    )
    raise RuntimeError("Attempt 24 terminal capture unexpectedly returned")
'''


def exact_replace(source: str, old: str, new: str, name: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Attempt 24 replacement drifted: {name}: {count}")
    return source.replace(old, new, 1)


def replace_top_level_function(source: str, name: str, replacement: str) -> str:
    tree = ast.parse(source)
    matches = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Attempt 24 function replacement drifted: {name}: {len(matches)}")
    node = matches[0]
    lines = source.splitlines(keepends=True)
    return "".join(lines[: node.lineno - 1]) + replacement.rstrip() + "\n\n" + "".join(lines[node.end_lineno :])


def derive_attempt24_source(source23: str) -> str:
    source = source23
    source = exact_replace(
        source,
        "def run_cdt(\n",
        REFINEMENT_TERMINAL_HELPERS + "\n\ndef run_cdt(\n",
        "insert refinement terminal helpers",
    )
    source = exact_replace(
        source,
        "    epsilon: float,\n"
        "    config: Mapping[str, Any],\n"
        ") -> dict[str, Any]:\n"
        "    clean_seeds, seed_sanitation = sanitize_cdt_seed_points(\n",
        "    epsilon: float,\n"
        "    config: Mapping[str, Any],\n"
        "    diagnostic_context: Mapping[str, Any] | None = None,\n"
        ") -> dict[str, Any]:\n"
        "    clean_seeds, seed_sanitation = sanitize_cdt_seed_points(\n",
        "run_cdt diagnostic context",
    )
    source = exact_replace(
        source,
        "    boundary_mismatch = capture_exact_cdt_boundary_mismatch(\n"
        "        coordinates,\n"
        "        faces,\n"
        "        original_vertices,\n"
        "        boundary_output,\n"
        "        boundary_count,\n"
        "        boundary,\n"
        "        epsilon,\n"
        "        config,\n"
        "        seed_sanitation,\n"
        "        cdt_sanitation,\n"
        "    )\n"
        "    mismatch_path = resolve_attempt23_diagnostic_path(config)\n"
        "    atomic_write_json(mismatch_path, boundary_mismatch)\n"
        "    raise RuntimeError(\n"
        "        \"Attempt 23 captured exact sanitized CDT boundary state; \"\n"
        "        \"diagnostic-only stop before reconstruction\"\n"
        "    )\n",
        "    boundary_mismatch = capture_exact_cdt_boundary_mismatch(\n"
        "        coordinates,\n"
        "        faces,\n"
        "        original_vertices,\n"
        "        boundary_output,\n"
        "        boundary_count,\n"
        "        boundary,\n"
        "        epsilon,\n"
        "        config,\n"
        "        seed_sanitation,\n"
        "        cdt_sanitation,\n"
        "    )\n"
        "    run_context = dict(diagnostic_context or {})\n"
        "    boundary_mismatch[\"run_context\"] = run_context\n"
        "    boundary_mismatch[\"current_minimum_2d_triangle_angle_degrees\"] = (\n"
        "        attempt24_current_minimum_angle(coordinates, faces)\n"
        "    )\n"
        "    if boundary_mismatch[\"mismatch_detected\"]:\n"
        "        capture_attempt24_terminal_and_stop(\n"
        "            \"FIRST_ACTUAL_BOUNDARY_MISMATCH\",\n"
        "            boundary_mismatch,\n"
        "            run_context,\n"
        "            {\n"
        "                \"current_minimum_2d_triangle_angle_degrees\": boundary_mismatch[\n"
        "                    \"current_minimum_2d_triangle_angle_degrees\"\n"
        "                ],\n"
        "                \"required_minimum_2d_triangle_angle_degrees\": float(\n"
        "                    config[\"minimum_new_triangle_angle_degrees\"]\n"
        "                ),\n"
        "                \"previous_candidate_record\": run_context.get(\n"
        "                    \"previous_candidate_record\"\n"
        "                ),\n"
        "            },\n"
        "            config,\n"
        "        )\n",
        "pass exact state and stop on first mismatch",
    )
    source = exact_replace(
        source,
        '        "boundary_segmentation_recovery": boundary_segmentation_recovery,\n'
        '        "disk_topology": disk_topology,\n',
        '        "boundary_segmentation_recovery": boundary_segmentation_recovery,\n'
        '        "boundary_diagnostic": boundary_mismatch,\n'
        '        "disk_topology": disk_topology,\n',
        "return exact boundary diagnostic in-memory",
    )
    source = replace_top_level_function(
        source, "quality_refined_cdt", DIAGNOSTIC_QUALITY_REFINEMENT
    )
    source = exact_replace(
        source,
        "    config = load_attempt23_config(config_path)\n",
        "    config = load_attempt24_config(config_path)\n",
        "Attempt 24 config loader",
    )
    for old, new in (
        ("attempt_23", "attempt_24"),
        ("attempt23", "attempt24"),
        ("Attempt 23", "Attempt 24"),
        ("ATTEMPT23", "ATTEMPT24"),
    ):
        if old not in source:
            raise RuntimeError(f"Attempt 23 identity token disappeared: {old}")
        source = source.replace(old, new)
    if any(
        token in source
        for token in ("ATTEMPT23", "attempt_23", "attempt23", "Attempt 23")
    ):
        raise RuntimeError("Attempt 24 derived source retained stale evidence identity")
    tree = ast.parse(source)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    required = {
        "atomic_write_attempt24_once",
        "capture_attempt24_terminal_and_stop",
        "quality_refined_cdt",
    }
    if not required.issubset(names):
        raise RuntimeError("Attempt 24 refinement diagnostic helpers are absent")
    return source


def materialize_attempt23_source(provider: Any) -> str:
    provider22 = provider.load_attempt22_module()
    source22 = provider.materialize_attempt22_source(provider22)
    return provider.derive_attempt23_source(source22)


def main() -> None:
    if sha256_file(ATTEMPT23_WORKER) != EXPECTED_ATTEMPT23_WORKER_SHA256:
        raise RuntimeError("Attempt 23 worker changed before Attempt 24 derivation")
    provider = load_attempt23_module()
    preserved_paths = (
        ATTEMPT23_WORKER,
        ATTEMPT22_WORKER,
        ATTEMPT21_WORKER,
        ATTEMPT20_WORKER,
        ATTEMPT19_WORKER,
        ATTEMPT18_WORKER,
    )
    before = {path: path.read_bytes() for path in preserved_paths}
    source23 = materialize_attempt23_source(provider)
    source24 = derive_attempt24_source(source23)
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
        "load_attempt24_config": load_attempt24_config,
    }
    try:
        exec(
            compile(source24, str(Path(__file__).resolve()) + "::derived", "exec"),
            namespace,
            namespace,
        )
    finally:
        for path in preserved_paths:
            if path.read_bytes() != before[path]:
                raise RuntimeError(f"{path.name} changed during Attempt 24 execution")


if __name__ == "__main__":
    main()
