#!/usr/bin/env python3
"""Read-only R26 left-little-finger nail localization and bounded grid probe.

This diagnostic recreates the exact pre-nail body/rig scene in memory, reproduces
the Attempt 08 9x9 projection search, applies the repository's exact triangle-pair
narrow phase, and then probes only 13x13 and 17x17 projection grids. It never
saves a Blend, builds or publishes a candidate, renders, activates, assigns,
exports, or uploads anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import blender_avatar_natural_nail_delivery_v3 as nails  # noqa: E402
from tools import blender_build_biological_robert_r26_bald_owner_review as r26  # noqa: E402
from tools.blender_exact_mesh_intersections import classify_triangle_pair  # noqa: E402
from Core.avatar_natural_nail_delivery_v3 import (  # noqa: E402
    CENTER_FRACTION_CANDIDATES,
    FOOTPRINT_SCALE_CANDIDATES,
    MAXIMUM_NORMAL_LIFT_ITERATIONS,
    MAXIMUM_SURFACE_CLEARANCE_M,
    MINIMUM_OUTWARD_NORMAL_ALIGNMENT,
    MINIMUM_SURFACE_CLEARANCE_M,
    NORMAL_LIFT_STEP_M,
    expected_nail_inventory,
    oval_half_width_scale,
)


EXPECTED_BINDINGS = {
    "config": "c64fa0f833caa86fb59a53d46ab98852ecd8a926666680a1aad11cce54a07c57",
    "worker": "b9926bebe59b4f6720ee690d58da3752c172c1ddb10e517b2f27e4b5581f7f74",
    "nail_adapter": "5d87a610bba4b7a6dd915176545ac882c6b326f6d39527ff1a55eb3052348551",
    "exact_auditor": "75c9f9633686776b72ec7bd83362521daae3d9f9497106b0491b8f85490c3ad1",
    "attempt_08_failure": "8bfa7a6f87672312e211bf8322257dc2dabecda4d9a975d5365af540c088cca5",
}
GRID_CANDIDATES = (9, 13, 17)
TARGET_BONE = "finger5-3.L"
TARGET_NAIL_ID = "fingernail_5_L"


class NailDiagnosticError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def project_path(value: str) -> Path:
    path = (PROJECT_ROOT / value).resolve()
    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise NailDiagnosticError(f"path escapes project root: {path}") from exc
    return path


def verify_bindings(config_path: Path) -> dict[str, Any]:
    paths = {
        "config": config_path,
        "worker": PROJECT_ROOT / "Tools/blender_build_biological_robert_r26_bald_owner_review.py",
        "nail_adapter": PROJECT_ROOT / "Tools/blender_avatar_natural_nail_delivery_v3.py",
        "exact_auditor": PROJECT_ROOT / "Tools/blender_exact_mesh_intersections.py",
        "attempt_08_failure": PROJECT_ROOT
        / "RecoverySprint/runtime_cache/biological_robert_r26/attempt_20260802T181600Z_bff8e49f85/FAILED_BUILD.json",
    }
    rows = {}
    for key, path in paths.items():
        if not path.is_file():
            raise NailDiagnosticError(f"bound input absent: {path}")
        actual = sha256_file(path)
        expected = EXPECTED_BINDINGS[key]
        if actual != expected:
            raise NailDiagnosticError(
                f"bound input changed: {key}; expected={expected}; actual={actual}"
            )
        rows[key] = {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": actual,
        }
    return rows


def world_body_data(body: Any) -> tuple[list[Vector], list[tuple[int, int, int]], BVHTree]:
    body.data.calc_loop_triangles()
    points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    triangles = [
        tuple(int(index) for index in triangle.vertices)
        for triangle in body.data.loop_triangles
    ]
    return (
        points,
        triangles,
        BVHTree.FromPolygons(points, triangles, all_triangles=True, epsilon=0.0),
    )


def clearance_record(body_tree: BVHTree, points: Sequence[Vector]) -> dict[str, Any]:
    distances = []
    for point in points:
        nearest = body_tree.find_nearest(point)
        if nearest[0] is None:
            raise NailDiagnosticError("body clearance query failed")
        distances.append(float(nearest[3]))
    distances.sort()
    percentile_05 = distances[max(0, int(len(distances) * 0.05) - 1)]
    return {
        "sample_count": len(distances),
        "minimum_unsigned_body_surface_clearance_m": distances[0],
        "percentile_05_unsigned_body_surface_clearance_m": percentile_05,
        "median_unsigned_body_surface_clearance_m": distances[len(distances) // 2],
        "maximum_unsigned_body_surface_clearance_m": distances[-1],
    }


def classify_cross_pairs(
    body_points: Sequence[Vector],
    body_triangles: Sequence[tuple[int, int, int]],
    body_tree: BVHTree,
    nail_points: Sequence[Vector],
    nail_triangles: Sequence[tuple[int, int, int]],
    *,
    linear_tolerance: float,
    include_pair_details: bool,
) -> dict[str, Any]:
    nail_tree = BVHTree.FromPolygons(
        nail_points,
        nail_triangles,
        all_triangles=True,
        epsilon=0.0,
    )
    raw_pairs = sorted(body_tree.overlap(nail_tree))
    counts: dict[str, int] = {}
    genuine_pairs: list[list[int]] = []
    details: list[dict[str, Any]] = []
    segment_lengths: list[float] = []
    coplanar_areas: list[float] = []
    for body_index, nail_index in raw_pairs:
        result = classify_triangle_pair(
            tuple(body_points[index] for index in body_triangles[body_index]),
            tuple(nail_points[index] for index in nail_triangles[nail_index]),
            linear_tolerance=linear_tolerance,
        )
        classification = str(result["classification"])
        counts[classification] = counts.get(classification, 0) + 1
        if result.get("genuine_penetration") is True:
            genuine_pairs.append([int(body_index), int(nail_index)])
        if "intersection_segment_length_m" in result:
            segment_lengths.append(float(result["intersection_segment_length_m"]))
        if "coplanar_overlap_area_m2" in result:
            coplanar_areas.append(float(result["coplanar_overlap_area_m2"]))
        if include_pair_details:
            details.append(
                {
                    "body_triangle_index": int(body_index),
                    "nail_triangle_index": int(nail_index),
                    "nail_triangle_vertices": [
                        int(value) for value in nail_triangles[nail_index]
                    ],
                    **result,
                }
            )
    return {
        "raw_bvhtree_pair_count": len(raw_pairs),
        "classification_counts": counts,
        "exact_genuine_penetration_pair_count": len(genuine_pairs),
        "exact_genuine_penetration_pairs": genuine_pairs,
        "maximum_intersection_segment_length_m": max(segment_lengths, default=0.0),
        "maximum_coplanar_overlap_area_m2": max(coplanar_areas, default=0.0),
        "pair_details": details,
        "linear_tolerance_m": linear_tolerance,
    }


def project_grid(
    *,
    body_tree: BVHTree,
    terminal: Vector,
    longitudinal: Vector,
    lateral: Vector,
    outward: Vector,
    length_m: float,
    width_m: float,
    footprint_scale: float,
    center_fraction: float,
    grid: int,
) -> tuple[list[Vector], list[Vector], list[float], float, str]:
    nominal_center = terminal - longitudinal * (length_m * center_fraction)
    hits: list[Vector] = []
    normals: list[Vector] = []
    base_clearances: list[float] = []
    minimum_alignment = 1.0
    for row in range(grid):
        along = ((row / (grid - 1)) - 0.5) * length_m * footprint_scale
        row_width_scale = oval_half_width_scale(row, grid)
        for column in range(grid):
            across_fraction = (column / (grid - 1)) - 0.5
            across = (
                across_fraction
                * width_m
                * footprint_scale
                * row_width_scale
            )
            expected = nominal_center + longitudinal * along + lateral * across
            origin = expected + outward * 0.025
            hit, normal, _face, _distance = body_tree.ray_cast(
                origin, -outward, 0.050
            )
            if hit is None or normal is None:
                return hits, normals, base_clearances, minimum_alignment, (
                    f"surface_projection_miss_{row}_{column}"
                )
            if normal.dot(outward) < 0.0:
                normal = -normal
            normal.normalize()
            alignment = float(normal.dot(outward))
            minimum_alignment = min(minimum_alignment, alignment)
            if alignment < MINIMUM_OUTWARD_NORMAL_ALIGNMENT:
                return hits, normals, base_clearances, minimum_alignment, (
                    f"outward_normal_alignment_{row}_{column}"
                )
            transverse_arch = 1.0 - min(1.0, abs(across_fraction) * 2.0) ** 2
            hits.append(hit.copy())
            normals.append(normal.copy())
            base_clearances.append(0.000055 + 0.000055 * transverse_arch)
    return hits, normals, base_clearances, minimum_alignment, ""


def probe_grid(
    *,
    grid: int,
    stop_on_first_fit: bool,
    body_points: Sequence[Vector],
    body_triangles: Sequence[tuple[int, int, int]],
    body_tree: BVHTree,
    terminal: Vector,
    longitudinal: Vector,
    lateral: Vector,
    outward: Vector,
    length_m: float,
    width_m: float,
    linear_tolerance: float,
) -> dict[str, Any]:
    faces = nails._outward_grid_faces(grid)  # noqa: SLF001
    nail_triangles = [
        (int(face[0]), int(face[1]), int(face[2])) for face in faces
    ] + [
        (int(face[0]), int(face[2]), int(face[3])) for face in faces
    ]
    attempts: list[dict[str, Any]] = []
    accepted: dict[str, Any] | None = None
    for footprint_scale in FOOTPRINT_SCALE_CANDIDATES:
        for center_fraction in CENTER_FRACTION_CANDIDATES:
            hits, normals, base_clearances, alignment, failure = project_grid(
                body_tree=body_tree,
                terminal=terminal,
                longitudinal=longitudinal,
                lateral=lateral,
                outward=outward,
                length_m=length_m,
                width_m=width_m,
                footprint_scale=float(footprint_scale),
                center_fraction=float(center_fraction),
                grid=grid,
            )
            attempt: dict[str, Any] = {
                "grid": grid,
                "footprint_scale": float(footprint_scale),
                "center_fraction_from_terminal": float(center_fraction),
                "projected_sample_count": len(hits),
                "minimum_outward_normal_alignment": alignment,
                "projection_complete": failure == "",
                "failure_reason": failure,
                "lift_iterations": [],
            }
            if failure:
                attempts.append(attempt)
                continue
            for lift_iteration in range(MAXIMUM_NORMAL_LIFT_ITERATIONS + 1):
                additional_lift = lift_iteration * NORMAL_LIFT_STEP_M
                points = [
                    hit + normal * (base + additional_lift)
                    for hit, normal, base in zip(hits, normals, base_clearances)
                ]
                clearance = clearance_record(body_tree, points)
                exact = classify_cross_pairs(
                    body_points,
                    body_triangles,
                    body_tree,
                    points,
                    nail_triangles,
                    linear_tolerance=linear_tolerance,
                    include_pair_details=lift_iteration
                    == MAXIMUM_NORMAL_LIFT_ITERATIONS,
                )
                fit = (
                    exact["exact_genuine_penetration_pair_count"] == 0
                    and float(clearance["minimum_unsigned_body_surface_clearance_m"])
                    >= MINIMUM_SURFACE_CLEARANCE_M
                    and float(clearance["maximum_unsigned_body_surface_clearance_m"])
                    <= MAXIMUM_SURFACE_CLEARANCE_M
                )
                iteration = {
                    "lift_iteration": lift_iteration,
                    "additional_global_normal_lift_m": additional_lift,
                    "clearance": clearance,
                    "exact_intersections": exact,
                    "fit_passed": fit,
                }
                attempt["lift_iterations"].append(iteration)
                if fit:
                    attempt["fit_passed"] = True
                    accepted = {
                        "grid": grid,
                        "footprint_scale": float(footprint_scale),
                        "center_fraction_from_terminal": float(center_fraction),
                        **iteration,
                    }
                    break
                if float(clearance["maximum_unsigned_body_surface_clearance_m"]) > MAXIMUM_SURFACE_CLEARANCE_M:
                    break
            attempt.setdefault("fit_passed", False)
            attempts.append(attempt)
            if accepted is not None and stop_on_first_fit:
                break
        if accepted is not None and stop_on_first_fit:
            break
    return {
        "grid": grid,
        "attempt_count": len(attempts),
        "accepted": accepted,
        "attempts": attempts,
    }


def main() -> None:
    args = parse_args()
    config_path = project_path(args.config)
    output_path = project_path(args.output)
    if output_path.exists():
        raise NailDiagnosticError(f"append-only diagnostic output exists: {output_path}")
    candidate_path = PROJECT_ROOT / (
        "Avatar/private_owner_review/dual_robert_20260729/"
        "biological_robert_r26_bald_owner_review"
    )
    if candidate_path.exists():
        raise NailDiagnosticError("R26 candidate appeared before nail diagnosis")
    bindings_before = verify_bindings(config_path)
    config = r26.json_file(config_path)
    input_records_before = r26.verify_bound_inputs(config)
    source_vertices, source_groups, _targets = r26.target_deformed_source(config)
    source_weights = r26.read_source_weights(
        project_path(str(config["inputs"]["makehuman_weights"]["path"])),
        len(source_vertices),
    )

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    canonical, warped, _append = r26.append_v8_objects(config)
    v8_report = r26.validate_v8(config, canonical, warped)
    height_envelope = r26.validate_expected_warped_height_envelope(
        config, warped, v8_report
    )
    transfer_tree, triangle_sources, tree_points = r26.source_weight_surface(
        source_vertices,
        source_groups,
        float(config["foundation_truth"]["helper_root_inset_native_units"]),
    )
    max_residual_native = (
        float(config["rigging"]["required_transfer_residual_m"])
        / float(config["foundation_truth"]["native_to_blender_scale"])
    )
    normalized_weights, associations, transfer_report = r26.interpolate_weights(
        canonical,
        transfer_tree,
        triangle_sources,
        tree_points,
        source_weights,
        max_residual_native=max_residual_native,
        max_influences=int(config["rigging"]["max_influences_per_vertex"]),
    )
    r26.remove_everything_except([warped])
    warped.name = str(config["candidate_id"]) + "_diagnostic_primary_surface"
    warped.data.name = warped.name + "_mesh"
    floor_native, height = r26.prepare_body_for_meters(warped, config)
    if abs(height - float(height_envelope["expected_warped_height_m"])) > float(
        height_envelope["expected_warped_height_tolerance_m"]
    ):
        raise NailDiagnosticError("recreated body height differs from bound expectation")
    armature, rig_report = r26.build_official_armature(
        warped,
        config,
        source_vertices,
        normalized_weights,
        floor_native=floor_native,
    )

    definition = next(
        row for row in expected_nail_inventory() if row["nail_id"] == TARGET_NAIL_ID
    )
    terminal, longitudinal, lateral, outward = nails._terminal_frame(  # noqa: SLF001
        armature,
        TARGET_BONE,
        definition["outward_hint"],
    )
    length_m = height * float(definition["length_height_fraction"])
    width_m = height * float(definition["width_height_fraction"])
    body_points, body_triangles, body_tree = world_body_data(warped)
    low = Vector(tuple(min(point[axis] for point in body_points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in body_points) for axis in range(3)))
    linear_tolerance = max(1.0e-10, float((high - low).length) * 1.0e-8)

    grids = []
    for grid in GRID_CANDIDATES:
        result = probe_grid(
            grid=grid,
            stop_on_first_fit=grid != 9,
            body_points=body_points,
            body_triangles=body_triangles,
            body_tree=body_tree,
            terminal=terminal,
            longitudinal=longitudinal,
            lateral=lateral,
            outward=outward,
            length_m=length_m,
            width_m=width_m,
            linear_tolerance=linear_tolerance,
        )
        grids.append(result)
        if grid != 9 and result["accepted"] is not None:
            break

    failure = json.loads(
        project_path(
            "RecoverySprint/runtime_cache/biological_robert_r26/"
            "attempt_20260802T181600Z_bff8e49f85/FAILED_BUILD.json"
        ).read_text(encoding="utf-8")
    )
    logged_attempts = json.loads(str(failure["exception"]).split(";attempts=", 1)[1])
    baseline = grids[0]
    reproduced_final_raw = [
        int(attempt["lift_iterations"][-1]["exact_intersections"]["raw_bvhtree_pair_count"])
        for attempt in baseline["attempts"]
    ]
    logged_final_raw = [
        int(attempt["final_body_surface_triangle_overlap_count"])
        for attempt in logged_attempts
    ]
    baseline_final_genuine = [
        int(
            attempt["lift_iterations"][-1]["exact_intersections"][
                "exact_genuine_penetration_pair_count"
            ]
        )
        for attempt in baseline["attempts"]
    ]
    smallest_passing = next(
        (row["accepted"] for row in grids[1:] if row["accepted"] is not None),
        None,
    )
    result = {
        "schema": "kira.avatar.robert_r26_finger5_nail_diagnosis.v1",
        "created_utc": utc_now(),
        "status": "READ_ONLY_DIAGNOSIS_COMPLETE_NO_CANDIDATE_NO_SAVE",
        "bindings_before": bindings_before,
        "config_input_record_count": len(input_records_before),
        "candidate_absent_before": True,
        "candidate_absent_after": not candidate_path.exists(),
        "target": {
            "nail_id": TARGET_NAIL_ID,
            "bone": TARGET_BONE,
            "body_height_m": height,
            "nominal_length_m": length_m,
            "nominal_width_m": width_m,
            "linear_tolerance_m": linear_tolerance,
        },
        "height_envelope": height_envelope,
        "transfer_summary": transfer_report,
        "rig_summary": rig_report,
        "attempt_08_reproduction": {
            "logged_attempt_count": len(logged_attempts),
            "diagnostic_attempt_count": len(baseline["attempts"]),
            "logged_final_raw_pair_counts": logged_final_raw,
            "diagnostic_final_raw_pair_counts": reproduced_final_raw,
            "exact_pair_counts_match": logged_final_raw == reproduced_final_raw,
            "diagnostic_final_genuine_pair_counts": baseline_final_genuine,
            "any_exact_genuine_penetration": any(
                count > 0 for count in baseline_final_genuine
            ),
            "logged_adaptive_iteration_zero_is_failure_sentinel": True,
            "actual_reproduced_maximum_lift_iteration": max(
                int(attempt["lift_iterations"][-1]["lift_iteration"])
                for attempt in baseline["attempts"]
            ),
        },
        "grid_probes": grids,
        "smallest_passing_densified_probe": smallest_passing,
        "interpretation": {
            "raw_bvhtree_pairs_are_not_assumed_genuine": True,
            "exact_triangle_pair_narrow_phase_used": True,
            "touches_are_separate_from_crossing_segments_or_positive_area": True,
            "component_only_grid_refinement_supported": smallest_passing is not None,
            "body_mesh_or_rig_correction_proposed": False,
        },
        "bindings_after": verify_bindings(config_path),
        "blend_saved": False,
        "candidate_created": False,
        "render_performed": False,
        "activation_assignment_export_publication_or_upload": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
