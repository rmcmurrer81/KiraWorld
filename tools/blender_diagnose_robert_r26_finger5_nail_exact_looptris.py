#!/usr/bin/env python3
"""Exact-loop-triangle R26 left-little-finger nail diagnosis.

This append-only second diagnostic corrects one limitation in the preserved
first diagnostic: every temporary nail is constructed exactly as the current
adapter constructs it, and every BVH uses Blender's ``mesh.calc_loop_triangles``
result rather than a hand-selected quad diagonal.  The 9x9 baseline must
reproduce all 24 Attempt 08 final raw overlap counts before any 13x13 or 17x17
probe is permitted.

The script never saves or opens a Blend, renders, creates an owner candidate,
activates or assigns a body, exports, publishes, or uploads anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import blender_avatar_natural_nail_delivery_v3 as nails  # noqa: E402
from tools import blender_build_biological_robert_r26_bald_owner_review as r26  # noqa: E402
from tools import blender_diagnose_robert_r26_finger5_nail as first  # noqa: E402
from Core.avatar_natural_nail_delivery_v3 import (  # noqa: E402
    CENTER_FRACTION_CANDIDATES,
    FOOTPRINT_SCALE_CANDIDATES,
    MAXIMUM_NORMAL_LIFT_ITERATIONS,
    MAXIMUM_SURFACE_CLEARANCE_M,
    MINIMUM_SURFACE_CLEARANCE_M,
    NORMAL_LIFT_STEP_M,
    expected_nail_inventory,
)


EXPECTED_ADDITIONAL_BINDINGS = {
    "first_diagnostic_script": {
        "path": "Tools/blender_diagnose_robert_r26_finger5_nail.py",
        "sha256": "87be0ba846d66e38a9f7b36fb5c5423a166a6c7a728d81bf05bc327cc31e1379",
    },
    "first_diagnostic_result": {
        "path": (
            "RecoverySprint/continuation_20260802/"
            "biological_robert_r26_bounded_run/attempt_08/nail_diagnosis/"
            "DIAGNOSTIC_RESULT.json"
        ),
        "sha256": "8e733c03ac0036ecd5e716efc10a5da16a074f3e00242760d848cd7892b13d3d",
    },
    "first_diagnostic_report": {
        "path": (
            "RecoverySprint/continuation_20260802/"
            "biological_robert_r26_bounded_run/attempt_08/nail_diagnosis/"
            "DIAGNOSTIC_REPORT.md"
        ),
        "sha256": "0ae3cd26a82b41929c761629dda502a97d0d972a67b16854d9a4dac2250b5dc4",
    },
    "first_diagnostic_manifest": {
        "path": (
            "RecoverySprint/continuation_20260802/"
            "biological_robert_r26_bounded_run/attempt_08/nail_diagnosis/"
            "PACKAGE_MANIFEST.json"
        ),
        "sha256": "2f384f0c34164ae460d72cc99a64660fa7460a8e77903662614a1bc824ba3920",
    },
}

TARGET_BONE = "finger5-3.L"
TARGET_NAIL_ID = "fingernail_5_L"
GRID_CANDIDATES = (9, 13, 17)


class ExactLoopTriangleDiagnosticError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        raise ExactLoopTriangleDiagnosticError(
            f"path escapes project root: {path}"
        ) from exc
    return path


def verify_additional_bindings() -> dict[str, Any]:
    records: dict[str, Any] = {}
    for binding, expected in EXPECTED_ADDITIONAL_BINDINGS.items():
        path = project_path(str(expected["path"]))
        if not path.is_file():
            raise ExactLoopTriangleDiagnosticError(
                f"additional bound input absent: {path}"
            )
        actual = sha256_file(path)
        if actual != str(expected["sha256"]):
            raise ExactLoopTriangleDiagnosticError(
                f"additional bound input changed: {binding};"
                f"expected={expected['sha256']};actual={actual}"
            )
        records[binding] = {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": actual,
        }
    return records


def loop_triangle_data(nail: Any) -> tuple[list[Vector], list[tuple[int, int, int]]]:
    """Return the exact raw-object triangles used by the current adapter BVH."""

    nail.data.calc_loop_triangles()
    points = [nail.matrix_world @ vertex.co for vertex in nail.data.vertices]
    triangles = [
        tuple(int(index) for index in triangle.vertices)
        for triangle in nail.data.loop_triangles
    ]
    if not points or not triangles:
        raise ExactLoopTriangleDiagnosticError("temporary nail tessellation is empty")
    return points, triangles


def remove_temporary_nail(nail: Any | None, mesh: Any | None) -> None:
    if nail is not None and nail.name in bpy.data.objects:
        bpy.data.objects.remove(nail, do_unlink=True)
    if mesh is not None and mesh.name in bpy.data.meshes and mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def exact_fit(
    *,
    clearance: dict[str, Any],
    intersections: dict[str, Any],
) -> bool:
    return (
        int(intersections["exact_genuine_penetration_pair_count"]) == 0
        and float(clearance["minimum_unsigned_body_surface_clearance_m"])
        >= MINIMUM_SURFACE_CLEARANCE_M
        and float(clearance["maximum_unsigned_body_surface_clearance_m"])
        <= MAXIMUM_SURFACE_CLEARANCE_M
    )


def probe_grid_exact_loop_triangles(
    *,
    grid: int,
    force_all_variants_and_lifts: bool,
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
    attempts: list[dict[str, Any]] = []
    accepted: dict[str, Any] | None = None
    for footprint_scale in FOOTPRINT_SCALE_CANDIDATES:
        for center_fraction in CENTER_FRACTION_CANDIDATES:
            hits, normals, base_clearances, alignment, failure = first.project_grid(
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
                "first_exact_fit": None,
            }
            if failure:
                attempts.append(attempt)
                continue

            mesh = None
            nail = None
            try:
                mesh = bpy.data.meshes.new(
                    f"R26_exact_looptri_grid{grid}_temporary_mesh"
                )
                mesh.from_pydata(
                    [
                        tuple(hit + normal * clearance)
                        for hit, normal, clearance in zip(
                            hits, normals, base_clearances
                        )
                    ],
                    [],
                    faces,
                )
                mesh.update(calc_edges=True)
                nail = bpy.data.objects.new(
                    f"R26_exact_looptri_grid{grid}_temporary_nail", mesh
                )
                bpy.context.collection.objects.link(nail)

                for lift_iteration in range(MAXIMUM_NORMAL_LIFT_ITERATIONS + 1):
                    additional_lift = lift_iteration * NORMAL_LIFT_STEP_M
                    for vertex, hit, normal, base_clearance in zip(
                        nail.data.vertices,
                        hits,
                        normals,
                        base_clearances,
                    ):
                        vertex.co = hit + normal * (
                            base_clearance + additional_lift
                        )
                    nail.data.update()
                    nail_points, nail_triangles = loop_triangle_data(nail)
                    clearance = first.clearance_record(body_tree, nail_points)
                    intersections = first.classify_cross_pairs(
                        body_points,
                        body_triangles,
                        body_tree,
                        nail_points,
                        nail_triangles,
                        linear_tolerance=linear_tolerance,
                        include_pair_details=(
                            lift_iteration == MAXIMUM_NORMAL_LIFT_ITERATIONS
                        ),
                    )
                    fit = exact_fit(
                        clearance=clearance,
                        intersections=intersections,
                    )
                    iteration = {
                        "lift_iteration": lift_iteration,
                        "additional_global_normal_lift_m": additional_lift,
                        "loop_triangle_count": len(nail_triangles),
                        "clearance": clearance,
                        "exact_intersections": intersections,
                        "fit_passed": fit,
                    }
                    attempt["lift_iterations"].append(iteration)
                    if fit and attempt["first_exact_fit"] is None:
                        attempt["first_exact_fit"] = {
                            "grid": grid,
                            "footprint_scale": float(footprint_scale),
                            "center_fraction_from_terminal": float(
                                center_fraction
                            ),
                            **iteration,
                        }
                        if accepted is None:
                            accepted = dict(attempt["first_exact_fit"])
                    if fit and not force_all_variants_and_lifts:
                        break
                    if (
                        float(
                            clearance[
                                "maximum_unsigned_body_surface_clearance_m"
                            ]
                        )
                        > MAXIMUM_SURFACE_CLEARANCE_M
                        and not force_all_variants_and_lifts
                    ):
                        break
            finally:
                remove_temporary_nail(nail, mesh)

            attempt["fit_passed"] = attempt["first_exact_fit"] is not None
            attempts.append(attempt)
            if (
                accepted is not None
                and stop_on_first_fit
                and not force_all_variants_and_lifts
            ):
                break
        if (
            accepted is not None
            and stop_on_first_fit
            and not force_all_variants_and_lifts
        ):
            break
    return {
        "grid": grid,
        "attempt_count": len(attempts),
        "accepted": accepted,
        "attempts": attempts,
        "temporary_objects_remaining": sum(
            obj.name.startswith("R26_exact_looptri_grid")
            for obj in bpy.data.objects
        ),
        "temporary_meshes_remaining": sum(
            mesh.name.startswith("R26_exact_looptri_grid")
            for mesh in bpy.data.meshes
        ),
    }


def recreate_bound_body_and_rig(
    config: dict[str, Any],
) -> tuple[
    Any,
    Any,
    float,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
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
    normalized_weights, _associations, transfer_report = r26.interpolate_weights(
        canonical,
        transfer_tree,
        triangle_sources,
        tree_points,
        source_weights,
        max_residual_native=max_residual_native,
        max_influences=int(config["rigging"]["max_influences_per_vertex"]),
    )
    r26.remove_everything_except([warped])
    warped.name = str(config["candidate_id"]) + "_exact_looptri_diagnostic_body"
    warped.data.name = warped.name + "_mesh"
    floor_native, height = r26.prepare_body_for_meters(warped, config)
    if abs(height - float(height_envelope["expected_warped_height_m"])) > float(
        height_envelope["expected_warped_height_tolerance_m"]
    ):
        raise ExactLoopTriangleDiagnosticError(
            "recreated body height differs from bound expectation"
        )
    armature, rig_report = r26.build_official_armature(
        warped,
        config,
        source_vertices,
        normalized_weights,
        floor_native=floor_native,
    )
    return (
        warped,
        armature,
        height,
        height_envelope,
        transfer_report,
        rig_report,
    )


def main() -> None:
    args = parse_args()
    config_path = project_path(args.config)
    output_path = project_path(args.output)
    if output_path.exists():
        raise ExactLoopTriangleDiagnosticError(
            f"append-only diagnostic output exists: {output_path}"
        )
    candidate_path = project_path(
        "Avatar/private_owner_review/dual_robert_20260729/"
        "biological_robert_r26_bald_owner_review"
    )
    if candidate_path.exists():
        raise ExactLoopTriangleDiagnosticError(
            "R26 candidate appeared before exact-loop-triangle diagnosis"
        )

    first_bindings_before = first.verify_bindings(config_path)
    additional_bindings_before = verify_additional_bindings()
    config = r26.json_file(config_path)
    input_records_before = r26.verify_bound_inputs(config)
    (
        body,
        armature,
        height,
        height_envelope,
        transfer_report,
        rig_report,
    ) = recreate_bound_body_and_rig(config)

    definition = next(
        row
        for row in expected_nail_inventory()
        if row["nail_id"] == TARGET_NAIL_ID
    )
    terminal, longitudinal, lateral, outward = nails._terminal_frame(  # noqa: SLF001
        armature,
        TARGET_BONE,
        definition["outward_hint"],
    )
    length_m = height * float(definition["length_height_fraction"])
    width_m = height * float(definition["width_height_fraction"])
    body_points, body_triangles, body_tree = first.world_body_data(body)
    low = Vector(
        tuple(min(point[axis] for point in body_points) for axis in range(3))
    )
    high = Vector(
        tuple(max(point[axis] for point in body_points) for axis in range(3))
    )
    linear_tolerance = max(1.0e-10, float((high - low).length) * 1.0e-8)

    failure = json.loads(
        project_path(
            "RecoverySprint/runtime_cache/biological_robert_r26/"
            "attempt_20260802T181600Z_bff8e49f85/FAILED_BUILD.json"
        ).read_text(encoding="utf-8")
    )
    logged_attempts = json.loads(
        str(failure["exception"]).split(";attempts=", 1)[1]
    )
    logged_final_raw = [
        int(attempt["final_body_surface_triangle_overlap_count"])
        for attempt in logged_attempts
    ]

    baseline = probe_grid_exact_loop_triangles(
        grid=GRID_CANDIDATES[0],
        force_all_variants_and_lifts=True,
        stop_on_first_fit=False,
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
    reproduced_final_raw = [
        int(
            attempt["lift_iterations"][-1]["exact_intersections"]
            ["raw_bvhtree_pair_count"]
        )
        for attempt in baseline["attempts"]
    ]
    reproduction_passed = (
        len(baseline["attempts"]) == len(logged_attempts) == 24
        and reproduced_final_raw == logged_final_raw
    )

    grids = [baseline]
    if reproduction_passed and baseline["accepted"] is None:
        for grid in GRID_CANDIDATES[1:]:
            probe = probe_grid_exact_loop_triangles(
                grid=grid,
                force_all_variants_and_lifts=False,
                stop_on_first_fit=True,
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
            grids.append(probe)
            if probe["accepted"] is not None:
                break

    smallest_passing = next(
        (probe["accepted"] for probe in grids if probe["accepted"] is not None),
        None,
    )
    temporary_object_count = sum(
        obj.name.startswith("R26_exact_looptri_grid") for obj in bpy.data.objects
    )
    temporary_mesh_count = sum(
        mesh.name.startswith("R26_exact_looptri_grid") for mesh in bpy.data.meshes
    )
    if temporary_object_count != 0 or temporary_mesh_count != 0:
        raise ExactLoopTriangleDiagnosticError(
            "temporary nail data remained after diagnostic"
        )

    status = (
        "READ_ONLY_EXACT_LOOPTRI_DIAGNOSIS_COMPLETE_NO_CANDIDATE_NO_SAVE"
        if reproduction_passed
        else "FAILED_EXACT_LOOPTRI_REPRODUCTION_NO_DENSIFIED_CONCLUSION"
    )
    result = {
        "schema": "kira.avatar.robert_r26_finger5_nail_exact_looptri_diagnosis.v1",
        "created_utc": first.utc_now(),
        "status": status,
        "first_bindings_before": first_bindings_before,
        "additional_bindings_before": additional_bindings_before,
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
            "required_exact_match_before_densified_probe": True,
            "logged_attempt_count": len(logged_attempts),
            "diagnostic_attempt_count": len(baseline["attempts"]),
            "logged_final_raw_pair_counts": logged_final_raw,
            "diagnostic_final_raw_pair_counts": reproduced_final_raw,
            "exact_pair_counts_match": reproduction_passed,
            "matched_variant_count": sum(
                int(first_count == second_count)
                for first_count, second_count in zip(
                    logged_final_raw, reproduced_final_raw
                )
            ),
            "actual_blender_loop_triangles_used": True,
            "all_variants_and_all_lifts_forced": True,
        },
        "densified_probe_permitted": reproduction_passed,
        "grid_probes": grids,
        "smallest_passing_exact_looptri_probe": smallest_passing,
        "interpretation": {
            "raw_bvhtree_pairs_are_not_assumed_genuine": True,
            "exact_triangle_pair_narrow_phase_used": True,
            "touches_are_separate_from_crossing_segments_or_positive_area": True,
            "component_change_supported_only_if_reproduction_passed": True,
            "component_change_applied": False,
            "body_mesh_or_rig_correction_proposed": False,
        },
        "temporary_objects_remaining": temporary_object_count,
        "temporary_meshes_remaining": temporary_mesh_count,
        "first_bindings_after": first.verify_bindings(config_path),
        "additional_bindings_after": verify_additional_bindings(),
        "blend_opened": False,
        "blend_saved": False,
        "candidate_created": False,
        "render_performed": False,
        "activation_assignment_export_publication_or_upload": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
