"""Hash-bound Attempt 22 exact sanitized-CDT boundary diagnostic.

This derives the sealed Attempt 21 source and inserts one append-only diagnostic
capture before boundary recovery. The derived worker always stops immediately
after capture, before reconstruction or geometry mutation. Blender is not
imported when the wrapper is inspected by static tests.
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
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT22_CONFIG.json"
)
ATTEMPT21_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt21.py"
)
ATTEMPT20_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt20.py"
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
    "3123ee4f193170926d40bee4bfc300d00bd8a529d719c7d14d791bdef8cf86e0"
)
EXPECTED_ATTEMPT21_WORKER_SHA256 = (
    "6f3027cbc241d6a04529c5c36c0c79ac2fd14b5e83b6ad3b963d76ce68e28af5"
)


def load_attempt21_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "attempt22_sealed_attempt21_provider", ATTEMPT21_WORKER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Attempt 22 could not load the sealed Attempt 21 provider")
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
        raise RuntimeError(f"Attempt 22 binding escapes project: {value}")
    return path


def verify_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    path = project_path(str(record["path"]))
    actual_bytes = path.stat().st_size
    actual_sha256 = sha256_file(path)
    if actual_bytes != int(record["bytes"]):
        raise RuntimeError(f"Attempt 22 bound byte count drifted: {name}")
    if actual_sha256 != str(record["sha256"]).lower():
        raise RuntimeError(f"Attempt 22 bound hash drifted: {name}: {actual_sha256}")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": actual_bytes,
        "sha256": actual_sha256,
    }


def load_overlay(config_path: Path) -> dict[str, Any]:
    config_path = config_path.resolve(strict=True)
    if config_path != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 22 requires the exact sealed overlay config path")
    actual = sha256_file(config_path)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 22 overlay config hash drifted: {actual}")
    overlay = json.loads(config_path.read_text(encoding="utf-8"))
    if (
        overlay.get("attempt_id") != "attempt_22"
        or overlay.get("status") != "STATIC_DIAGNOSTIC_PREPARED_NOT_RUN"
        or overlay.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 22 overlay identity drifted")
    forbidden = (
        "blend_save_allowed",
        "export_allowed",
        "runtime_activation_allowed",
        "boundary_or_seam_movement_allowed",
        "quality_gate_reduction_allowed",
        "geometry_mutation_allowed",
        "render_allowed",
        "boundary_repair_allowed_before_exact_capture",
        "generic_hole_fill_allowed",
        "whole_polygon_retriangulation_allowed",
    )
    if any(bool(overlay["scope"][name]) for name in forbidden):
        raise RuntimeError("Attempt 22 scope is not diagnostic-only and no-save")
    return overlay


def verify_overlay_bindings(overlay: Mapping[str, Any]) -> dict[str, Any]:
    verified = {
        name: verify_record(name, record)
        for name, record in overlay["bindings"].items()
    }
    verified["proposal"] = verify_record("proposal", overlay["proposal"])
    if verified["attempt21_worker"]["sha256"] != EXPECTED_ATTEMPT21_WORKER_SHA256:
        raise RuntimeError("Attempt 22 provider constant and binding disagree")
    preserved = overlay["preserved_attempt21_package"]
    rows = [verified[name] for name in preserved["binding_names"]]
    if len(rows) != int(preserved["file_count"]):
        raise RuntimeError("Attempt 21 preserved package file count drifted")
    if sum(int(row["bytes"]) for row in rows) != int(preserved["total_bytes"]):
        raise RuntimeError("Attempt 21 preserved package byte total drifted")
    return verified


def load_attempt22_config(config_path: Path) -> dict[str, Any]:
    overlay = load_overlay(config_path)
    verified = verify_overlay_bindings(overlay)
    provider = load_attempt21_module()
    base_config_path = project_path(overlay["bindings"]["attempt21_config"]["path"])
    merged = provider.load_attempt21_config(base_config_path)
    if merged.get("attempt_id") != overlay["base"]["expected_config_attempt_id"]:
        raise RuntimeError("Attempt 21 materialized base identity drifted")
    merged = copy.deepcopy(merged)
    merged["schema"] = (
        "kira.avatar.r24.blackproject_local_reconstruction_attempt22.config.v1"
    )
    merged["attempt_id"] = "attempt_22"
    merged["output"] = copy.deepcopy(overlay["output"])
    merged["attempt22_diagnosis"] = copy.deepcopy(overlay["diagnosis"])
    merged["attempt22_capture_contract"] = copy.deepcopy(overlay["capture_contract"])
    merged["attempt22_unchanged_hard_gates"] = copy.deepcopy(
        overlay["unchanged_hard_gates"]
    )
    merged["attempt22_evidence_label_contract"] = copy.deepcopy(
        overlay["evidence_label_contract"]
    )
    merged["attempt22_truth"] = copy.deepcopy(overlay["truth"])
    merged["inputs"].update(
        {
            f"attempt22_bound_{name}": {
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
            raise RuntimeError(f"Attempt 22 {location} minimum-angle gate drifted")
    if float(merged["replacement"]["minimum_new_triangle_world_area_m2"]) != float(
        unchanged["minimum_new_triangle_world_area_m2"]
    ):
        raise RuntimeError("Attempt 22 minimum-area gate drifted")
    return merged


MISMATCH_CAPTURE_HELPERS = r'''
def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def diagnostic_edge_row(
    edge: tuple[int, int],
    coordinates: Sequence[Vector],
    output_to_source: Mapping[int, int],
    edge_counts: Mapping[tuple[int, int], int],
    edge_faces: Mapping[tuple[int, int], Sequence[int]],
) -> dict[str, Any]:
    return {
        "output_indices": [int(edge[0]), int(edge[1])],
        "endpoint_coordinates": [
            [float(coordinates[index].x), float(coordinates[index].y)]
            for index in edge
        ],
        "boundary_source_indices": [
            output_to_source.get(int(index)) for index in edge
        ],
        "incidence_count": int(edge_counts.get(edge, 0)),
        "incident_face_indices": [
            int(value) for value in edge_faces.get(edge, [])
        ],
    }


def diagnostic_boundary_chain(
    start_source: int,
    end_source: int,
    step: int,
    boundary_count: int,
    boundary_output: Mapping[int, int],
    coordinates: Sequence[Vector],
    open_edges: set[tuple[int, int]],
    missing_edges: set[tuple[int, int]],
    point_tolerance: float,
    area_tolerance: float,
) -> dict[str, Any]:
    sources = boundary_source_chain(start_source, end_source, step, boundary_count)
    outputs = [int(boundary_output[source]) for source in sources]
    points = [coordinates[index] for index in outputs]
    start = points[0]
    end = points[-1]
    delta_x = float(end.x - start.x)
    delta_y = float(end.y - start.y)
    chord_squared = delta_x * delta_x + delta_y * delta_y
    chord_length = math.sqrt(chord_squared)
    projections: list[float | None] = []
    residuals: list[float] = []
    if chord_squared > 0.0:
        for point in points:
            projections.append(
                (
                    float(point.x - start.x) * delta_x
                    + float(point.y - start.y) * delta_y
                )
                / chord_squared
            )
            residuals.append(abs(orient2d(start, end, point)))
    else:
        projections = [None for _value in points]
        residuals = [0.0 for _value in points]
    chain_edges = [
        tuple(sorted((first, second)))
        for first, second in zip(outputs, outputs[1:])
    ]
    minimum_step = point_tolerance / chord_length if chord_length > 0.0 else math.inf
    interior_projections = projections[1:-1]
    strictly_ordered = bool(chord_length > point_tolerance)
    previous = 0.0
    for projection in interior_projections:
        if projection is None or not (
            projection > previous + minimum_step
            and projection < 1.0 - minimum_step
        ):
            strictly_ordered = False
            break
        previous = projection
    all_collinear = max(residuals, default=0.0) <= area_tolerance
    all_missing = all(edge in missing_edges for edge in chain_edges)
    qualifies = (
        len(outputs) > 2
        and all_collinear
        and strictly_ordered
        and all_missing
    )
    return {
        "step": int(step),
        "boundary_source_indices": [int(value) for value in sources],
        "boundary_output_indices": outputs,
        "coordinates": [[float(value.x), float(value.y)] for value in points],
        "projections_on_chord": projections,
        "absolute_twice_area_residuals": residuals,
        "maximum_absolute_twice_area_residual": max(residuals, default=0.0),
        "point_tolerance_m": float(point_tolerance),
        "twice_area_tolerance_m2": float(area_tolerance),
        "chain_edges": [[int(edge[0]), int(edge[1])] for edge in chain_edges],
        "chain_edge_is_open": [edge in open_edges for edge in chain_edges],
        "chain_edge_is_missing": [edge in missing_edges for edge in chain_edges],
        "intermediate_vertices_strictly_ordered": strictly_ordered,
        "all_vertices_collinear_with_chord": all_collinear,
        "all_chain_edges_missing": all_missing,
        "qualifies_unique_collinear_boundary_shortcut": qualifies,
    }


def capture_exact_cdt_boundary_mismatch(
    coordinates: Sequence[Vector],
    faces: Sequence[Sequence[int]],
    original_vertices: Sequence[Sequence[int]],
    boundary_output: Mapping[int, int],
    boundary_count: int,
    boundary: Sequence[Vector],
    epsilon: float,
    config: Mapping[str, Any],
    seed_sanitation: Mapping[str, Any],
    cdt_sanitation: Mapping[str, Any],
) -> dict[str, Any]:
    tolerances = cdt_tolerances(boundary, epsilon, config)
    point_tolerance = tolerances["point_tolerance_m"]
    area_tolerance = tolerances["twice_area_tolerance_m2"]
    edge_counts, edge_faces = cdt_edge_state(faces)
    constrained = exact_boundary_edges(boundary_output, boundary_count)
    open_edges = {edge for edge, count in edge_counts.items() if count == 1}
    missing = constrained - open_edges
    extra = open_edges - constrained
    output_to_source = {
        int(output): int(source) for source, output in boundary_output.items()
    }

    coordinate_rows = []
    for index, coordinate in enumerate(coordinates):
        sources = (
            sorted(int(value) for value in original_vertices[index])
            if index < len(original_vertices)
            else []
        )
        coordinate_rows.append(
            {
                "output_index": int(index),
                "xy": [float(coordinate.x), float(coordinate.y)],
                "original_input_source_indices": sources,
                "boundary_source_index": output_to_source.get(int(index)),
            }
        )
    face_rows = [
        {
            "face_index": int(face_index),
            "output_indices": [int(value) for value in face],
            "coordinates": [
                [float(coordinates[int(value)].x), float(coordinates[int(value)].y)]
                for value in face
            ],
        }
        for face_index, face in enumerate(faces)
    ]
    edge_rows = [
        diagnostic_edge_row(
            edge, coordinates, output_to_source, edge_counts, edge_faces
        )
        for edge in sorted(edge_counts)
    ]

    extra_rows = []
    classes: list[str] = []
    for edge in sorted(extra):
        row = diagnostic_edge_row(
            edge, coordinates, output_to_source, edge_counts, edge_faces
        )
        sources = row["boundary_source_indices"]
        chains: list[dict[str, Any]] = []
        if sources[0] is not None and sources[1] is not None:
            chains = [
                diagnostic_boundary_chain(
                    int(sources[0]),
                    int(sources[1]),
                    step,
                    boundary_count,
                    boundary_output,
                    coordinates,
                    open_edges,
                    missing,
                    point_tolerance,
                    area_tolerance,
                )
                for step in (1, -1)
            ]
            qualifying = sum(
                bool(value["qualifies_unique_collinear_boundary_shortcut"])
                for value in chains
            )
            if qualifying == 1:
                classification = "UNIQUE_COLLINEAR_BOUNDARY_SHORTCUT"
            elif qualifying > 1:
                classification = "AMBIGUOUS_COLLINEAR_BOUNDARY_SHORTCUT"
            else:
                classification = "NONCOLLINEAR_OR_INCOMPLETE_BOUNDARY_SHORTCUT"
        else:
            classification = "INTERIOR_ENDPOINT_OPEN_EDGE"
        row["classification"] = classification
        row["ordered_boundary_chain_diagnostics"] = chains
        extra_rows.append(row)
        classes.append(classification)

    if not missing and not extra:
        summary_class = "EXACT_BOUNDARY_ALREADY_MATCHED"
    elif any(value == "INTERIOR_ENDPOINT_OPEN_EDGE" for value in classes):
        summary_class = "INTERIOR_OPEN_EDGE_TEAR_OR_REMOVED_FACE_HOLE"
    elif classes and all(
        value == "NONCOLLINEAR_OR_INCOMPLETE_BOUNDARY_SHORTCUT"
        for value in classes
    ):
        summary_class = "NONCOLLINEAR_BOUNDARY_SHORTCUT_OR_DOMAIN_FACE_MISMATCH"
    elif not extra:
        summary_class = "MISSING_BOUNDARY_EDGE_WITHOUT_EXTRA_OPEN_EDGE"
    else:
        summary_class = "COMPOUND_BOUNDARY_MISMATCH"

    constrained_rows = [
        diagnostic_edge_row(
            edge, coordinates, output_to_source, edge_counts, edge_faces
        )
        for edge in sorted(constrained)
    ]
    open_rows = [
        diagnostic_edge_row(
            edge, coordinates, output_to_source, edge_counts, edge_faces
        )
        for edge in sorted(open_edges)
    ]
    missing_rows = [
        diagnostic_edge_row(
            edge, coordinates, output_to_source, edge_counts, edge_faces
        )
        for edge in sorted(missing)
    ]
    boundary_mapping = [
        {
            "boundary_source_index": int(source),
            "output_index": int(boundary_output[source]),
            "input_xy": [float(boundary[source].x), float(boundary[source].y)],
            "output_xy": [
                float(coordinates[int(boundary_output[source])].x),
                float(coordinates[int(boundary_output[source])].y),
            ],
        }
        for source in range(boundary_count)
    ]
    result = {
        "schema": "kira.avatar.r24.blackproject_attempt22.cdt_boundary_mismatch.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "CAPTURED_EXACT_SANITIZED_CDT_BOUNDARY_STATE_NO_REPAIR",
        "attempt_id": "attempt_22",
        "stage": "first_run_cdt_after_sanitation_before_boundary_recovery",
        "predecessor_terminal_subtype": "NO_UNIQUE_COLLINEAR_BOUNDARY_SHORTCUT",
        "mismatch_detected": bool(missing or extra),
        "mismatch_summary_class": summary_class,
        "repair_applied": False,
        "repair_decision": "DEFER_UNTIL_EXACT_CAPTURE_REVIEWED",
        "geometry_mutation_reached": False,
        "render_reached": False,
        "blend_saved": False,
        "runtime_changed": False,
        "boundary_count": int(boundary_count),
        "coordinate_count": len(coordinate_rows),
        "face_count": len(face_rows),
        "edge_count": len(edge_rows),
        "constrained_boundary_edge_count": len(constrained_rows),
        "open_edge_count": len(open_rows),
        "missing_boundary_edge_count": len(missing_rows),
        "extra_open_edge_count": len(extra_rows),
        "tolerances": tolerances,
        "seed_sanitation": dict(seed_sanitation),
        "cdt_sanitation": dict(cdt_sanitation),
        "boundary_source_to_output": boundary_mapping,
        "coordinates": coordinate_rows,
        "faces": face_rows,
        "edges": edge_rows,
        "constrained_boundary_edges": constrained_rows,
        "open_edges": open_rows,
        "missing_boundary_edges": missing_rows,
        "extra_open_edges": extra_rows,
    }
    result["canonical_sha256"] = {
        "coordinates": canonical_json_sha256(coordinate_rows),
        "faces": canonical_json_sha256(face_rows),
        "edges": canonical_json_sha256(edge_rows),
        "constrained_boundary_edges": canonical_json_sha256(constrained_rows),
        "open_edges": canonical_json_sha256(open_rows),
        "missing_boundary_edges": canonical_json_sha256(missing_rows),
        "extra_open_edges": canonical_json_sha256(extra_rows),
    }
    return result
'''


def exact_replace(source: str, old: str, new: str, name: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Attempt 22 replacement drifted: {name}: {count}")
    return source.replace(old, new, 1)


def derive_attempt22_source(source21: str) -> str:
    source = source21
    source = exact_replace(
        source,
        "def run_cdt(\n",
        MISMATCH_CAPTURE_HELPERS + "\n\ndef run_cdt(\n",
        "insert exact mismatch capture helpers",
    )
    source = exact_replace(
        source,
        "    faces, boundary_segmentation_recovery = restore_exact_boundary_segmentation(\n",
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
        "    mismatch_path = (\n"
        "        ROOT\n"
        "        / config[\"output\"][\"root\"]\n"
        "        / config[\"output\"][\"cdt_boundary_mismatch\"]\n"
        "    ).resolve()\n"
        "    atomic_write_json(mismatch_path, boundary_mismatch)\n"
        "    raise RuntimeError(\n"
        "        \"Attempt 22 captured exact sanitized CDT boundary state; \"\n"
        "        \"diagnostic-only stop before reconstruction\"\n"
        "    )\n"
        "    faces, boundary_segmentation_recovery = restore_exact_boundary_segmentation(\n",
        "capture and stop before boundary recovery",
    )
    source = exact_replace(
        source,
        "    config = load_attempt21_config(config_path)\n",
        "    config = load_attempt22_config(config_path)\n",
        "Attempt 22 config loader",
    )
    for old, new in (
        ("attempt_21", "attempt_22"),
        ("attempt21", "attempt22"),
        ("Attempt 21", "Attempt 22"),
        ("ATTEMPT21", "ATTEMPT22"),
    ):
        if old not in source:
            raise RuntimeError(f"Attempt 21 identity token disappeared: {old}")
        source = source.replace(old, new)
    if any(
        token in source
        for token in ("ATTEMPT21", "attempt_21", "attempt21", "Attempt 21")
    ):
        raise RuntimeError("Attempt 22 derived source retained a stale evidence identity")
    tree = ast.parse(source)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    names = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    if "capture_exact_cdt_boundary_mismatch" not in names:
        raise RuntimeError("Attempt 22 exact mismatch capture was not inserted")
    capture_index = source.index("boundary_mismatch = capture_exact_cdt_boundary_mismatch(")
    old_recovery_index = source.index(
        "faces, boundary_segmentation_recovery = restore_exact_boundary_segmentation("
    )
    terminal_index = source.index(
        "Attempt 22 captured exact sanitized CDT boundary state"
    )
    if not (capture_index < terminal_index < old_recovery_index):
        raise RuntimeError("Attempt 22 capture is not terminal before boundary recovery")
    return source


def materialize_attempt21_source(provider: Any) -> str:
    provider20 = provider.load_attempt20_module()
    source20 = provider.materialize_attempt20_source(provider20)
    return provider.derive_attempt21_source(source20)


def main() -> None:
    if sha256_file(ATTEMPT21_WORKER) != EXPECTED_ATTEMPT21_WORKER_SHA256:
        raise RuntimeError("Attempt 21 worker changed before Attempt 22 derivation")
    provider = load_attempt21_module()
    preserved_paths = (
        ATTEMPT21_WORKER,
        ATTEMPT20_WORKER,
        ATTEMPT19_WORKER,
        ATTEMPT18_WORKER,
    )
    before = {path: path.read_bytes() for path in preserved_paths}
    source21 = materialize_attempt21_source(provider)
    source22 = derive_attempt22_source(source21)
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
        "load_attempt22_config": load_attempt22_config,
    }
    try:
        exec(
            compile(
                source22,
                str(Path(__file__).resolve()) + "::derived",
                "exec",
            ),
            namespace,
            namespace,
        )
    finally:
        for path in preserved_paths:
            if path.read_bytes() != before[path]:
                raise RuntimeError(
                    f"{path.name} changed during Attempt 22 execution"
                )


if __name__ == "__main__":
    main()
