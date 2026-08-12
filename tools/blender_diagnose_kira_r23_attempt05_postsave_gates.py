#!/usr/bin/env python3
"""Read-only R23 Attempt05 post-save gate diagnostic.

This Blender worker reuses the unchanged fresh-reopen verifier's measurement
helpers but never calls its renderer or acceptance ``run`` function.  It opens
the exact source and candidate read-only, captures complete intersection,
continuity-localization, and per-pose deformation evidence, verifies both files
remain immutable, and writes only a new append-only diagnostic record.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import traceback
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
EXECUTION_FLAG = "--execute-readonly-gate-diagnostic"
BOUND_STATUS = "BOUND_NOT_RUN_EXPLICIT_READONLY_DIAGNOSTIC_AUTHORIZATION_REQUIRED"


class DiagnosticError(RuntimeError):
    """Fail-closed diagnostic binding or collection error."""


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument(EXECUTION_FLAG, action="store_true")
    return parser.parse_args(raw)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DiagnosticError(f"JSON root is not an object: {path}")
    return value


def verify_attempt02_failure(config: Mapping[str, Any], verifier: Any) -> dict[str, Any]:
    binding = config["attempt02_failure_binding"]
    path = verifier.require_binding(binding, "Attempt 02 failure evidence")
    record = verifier.read_json(path)
    expected_groups = (
        "{'candidate_flags': True, 'structure': True, 'intersections': False, "
        "'continuity': False, 'weights': True, 'frozen_ledgers': True, "
        "'retained_surface': True, 'deformation': False}"
    )
    if (
        record.get("exception_type") != "VerificationError"
        or expected_groups not in str(record.get("exception"))
        or record.get("source_before") != record.get("source_current")
        or record.get("candidate_before") != record.get("candidate_current")
        or record.get("candidate_remains_inactive_private_and_unapproved") is not True
    ):
        raise DiagnosticError("Attempt 02 failure evidence semantics drifted")
    directory = path.parent
    if sorted(entry.name for entry in directory.iterdir()) != [
        "FAILURE_EVIDENCE.json", "owner_renders"
    ]:
        raise DiagnosticError("Attempt 02 failure directory closure drifted")
    owner_renders = directory / "owner_renders"
    if not owner_renders.is_dir() or list(owner_renders.iterdir()):
        raise DiagnosticError("Attempt 02 owner_renders is absent or nonempty")
    return record


def validate_contract(
    diagnostic_config: Mapping[str, Any], explicit_execution: bool, verifier: Any
) -> dict[str, Any]:
    if not explicit_execution:
        raise DiagnosticError(f"explicit {EXECUTION_FLAG} flag is required")
    if diagnostic_config.get("status") != BOUND_STATUS:
        raise DiagnosticError("diagnostic configuration is unbound or wrong status")
    execution = diagnostic_config.get("execution", {})
    if execution.get("enabled") is not True:
        raise DiagnosticError("diagnostic execution remains disabled")
    required_true = (
        "fresh_factory_empty_blender_required", "read_only_source_and_candidate",
        "full_metrics_written_before_any_render", "render_forbidden",
        "source_save_forbidden", "candidate_save_forbidden", "export_forbidden",
        "runtime_activation_forbidden", "publication_forbidden",
    )
    if any(execution.get(key) is not True for key in required_true):
        raise DiagnosticError("read-only diagnostic contract was weakened")
    verification_config_path = verifier.require_binding(
        diagnostic_config["verification_config_binding"], "exact Attempt 02 config"
    )
    failure = verify_attempt02_failure(diagnostic_config, verifier)
    output = diagnostic_config["diagnostic_output"]
    output_directory = verifier.project_path(output["directory"])
    if output_directory.exists():
        raise DiagnosticError("append-only diagnostic output already exists")
    return {
        "verification_config_path": verification_config_path,
        "attempt02_failure": failure,
        "output_directory": output_directory,
    }


def uv_error_rows(
    verifier: Any,
    body: Any,
    candidate_index: int,
    original_index: int,
    source: Mapping[str, Any],
    patch_faces: set[int],
    retained_faces: set[int],
) -> tuple[list[dict[str, Any]], list[float], list[float]]:
    layers = []
    patch_errors: list[float] = []
    retained_errors: list[float] = []
    expected_layers = source["seam"][original_index]["uv"]
    current_patch = verifier.uv_values_at_vertex(body, candidate_index, patch_faces)
    current_retained = verifier.uv_values_at_vertex(body, candidate_index, retained_faces)
    for layer, expected_values in expected_layers.items():
        if not expected_values:
            continue
        patch_values = current_patch.get(layer, [])
        retained_values = current_retained.get(layer, [])
        current_patch_errors = [
            min(verifier.euclidean(value, expected) for expected in expected_values)
            for value in patch_values
        ]
        current_retained_errors = [
            min(verifier.euclidean(value, expected) for expected in expected_values)
            for value in retained_values
        ]
        patch_errors.extend(current_patch_errors)
        retained_errors.extend(current_retained_errors)
        layers.append(
            {
                "layer": layer,
                "expected_values": expected_values,
                "candidate_patch_values": patch_values,
                "candidate_retained_values": retained_values,
                "patch_errors": current_patch_errors,
                "retained_errors": current_retained_errors,
            }
        )
    return layers, patch_errors, retained_errors


def continuity_localization(
    verifier: Any,
    body: Any,
    source: Mapping[str, Any],
    patch_faces: set[int],
    topology: Any,
    continuity: Mapping[str, Any],
    thresholds: Mapping[str, float],
) -> dict[str, Any]:
    from mathutils import Vector

    candidate_cycle = [int(value) for value in continuity["candidate_cycle"]]
    mapped_cycle = [int(value) for value in continuity["mapped_source_cycle"]]
    source_order = [int(value) for value in source["seam_order"]]
    matched = dict(zip(candidate_cycle, mapped_cycle))
    faces = [tuple(map(int, polygon.vertices)) for polygon in body.data.polygons]
    retained_faces = set(range(len(faces))).difference(patch_faces)
    vertex_rows = []
    all_patch_uv_errors: list[float] = []
    all_retained_uv_errors: list[float] = []
    for offset, candidate_index in enumerate(candidate_cycle):
        original_index = matched[candidate_index]
        coordinate = verifier.vector_record(body.data.vertices[candidate_index].co)
        source_record = source["seam"][original_index]
        previous_index = candidate_cycle[(offset - 1) % len(candidate_cycle)]
        following_index = candidate_cycle[(offset + 1) % len(candidate_cycle)]
        current_tangent = (
            body.data.vertices[following_index].co
            - body.data.vertices[previous_index].co
        )
        source_offset = source_order.index(original_index)
        source_previous = source_order[(source_offset - 1) % len(source_order)]
        source_following = source_order[(source_offset + 1) % len(source_order)]
        source_tangent = (
            Vector(source["seam"][source_following]["coordinate"])
            - Vector(source["seam"][source_previous]["coordinate"])
        )
        tangent_dot = 0.0
        if current_tangent.length != 0.0 and source_tangent.length != 0.0:
            tangent_dot = abs(
                float(current_tangent.normalized().dot(source_tangent.normalized()))
            )
        uv_rows, patch_uv_errors, retained_uv_errors = uv_error_rows(
            verifier,
            body,
            candidate_index,
            original_index,
            source,
            patch_faces,
            retained_faces,
        )
        all_patch_uv_errors.extend(patch_uv_errors)
        all_retained_uv_errors.extend(retained_uv_errors)
        position_error = verifier.euclidean(coordinate, source_record["coordinate"])
        weight_error = verifier.weight_error(
            verifier.weight_map(body, candidate_index), source_record["weights"]
        )
        vertex_rows.append(
            {
                "candidate_vertex": candidate_index,
                "mapped_source_vertex": original_index,
                "candidate_coordinate": coordinate,
                "source_coordinate": source_record["coordinate"],
                "position_error_m": position_error,
                "weight_error": weight_error,
                "tangent_dot": tangent_dot,
                "uv_layers": uv_rows,
                "checks": {
                    "position": position_error
                    <= thresholds["maximum_seam_position_error_m"],
                    "weight": weight_error
                    <= thresholds["maximum_seam_weight_error"],
                    "tangent": tangent_dot >= thresholds["minimum_seam_tangent_dot"],
                    "patch_uv": max(patch_uv_errors, default=0.0)
                    <= thresholds["maximum_patch_retained_uv_distance"],
                    "retained_uv": max(retained_uv_errors, default=0.0)
                    <= thresholds["maximum_patch_retained_uv_distance"],
                },
            }
        )
    edge_faces = topology.edge_face_map(faces)
    edge_rows = []
    for edge in sorted(topology.boundary_edges_for_region(faces, patch_faces)):
        incident = edge_faces[edge]
        patch_incident = [index for index in incident if index in patch_faces]
        retained_incident = [index for index in incident if index not in patch_faces]
        if len(patch_incident) != 1 or len(retained_incident) != 1:
            raise DiagnosticError("seam edge incidence drifted during localization")
        normal_dot = float(
            body.data.polygons[patch_incident[0]].normal.dot(
                body.data.polygons[retained_incident[0]].normal
            )
        )
        edge_rows.append(
            {
                "edge": list(edge),
                "patch_face": patch_incident[0],
                "retained_face": retained_incident[0],
                "normal_dot": normal_dot,
                "passed": normal_dot >= thresholds["minimum_patch_retained_normal_dot"],
            }
        )
    aggregates = {
        "maximum_position_error_m": max(
            (row["position_error_m"] for row in vertex_rows), default=float("inf")
        ),
        "maximum_weight_error": max(
            (row["weight_error"] for row in vertex_rows), default=float("inf")
        ),
        "minimum_tangent_dot": min(
            (row["tangent_dot"] for row in vertex_rows), default=-1.0
        ),
        "minimum_patch_retained_normal_dot": min(
            (row["normal_dot"] for row in edge_rows), default=-1.0
        ),
        "maximum_patch_uv_distance": max(all_patch_uv_errors, default=0.0),
        "maximum_retained_uv_distance": max(all_retained_uv_errors, default=0.0),
    }
    aggregate_matches_helper = {
        key: abs(float(value) - float(continuity[key])) <= 1e-12
        for key, value in aggregates.items()
    }
    if not all(aggregate_matches_helper.values()):
        raise DiagnosticError(
            f"continuity localization differs from unchanged helper: {aggregate_matches_helper}"
        )
    return {
        "candidate_cycle": candidate_cycle,
        "mapped_source_cycle": mapped_cycle,
        "thresholds": dict(thresholds),
        "per_vertex": vertex_rows,
        "per_edge": edge_rows,
        "aggregates": aggregates,
        "aggregate_matches_unchanged_helper": aggregate_matches_helper,
    }


def evaluated_index_compatibility(body: Any, bpy: Any) -> dict[str, Any]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    try:
        record = {
            "base_vertex_count": len(body.data.vertices),
            "evaluated_vertex_count": len(mesh.vertices),
            "base_polygon_count": len(body.data.polygons),
            "evaluated_polygon_count": len(mesh.polygons),
        }
    finally:
        evaluated.to_mesh_clear()
    record["vertex_indices_compatible"] = (
        record["base_vertex_count"] == record["evaluated_vertex_count"]
    )
    record["face_indices_compatible"] = (
        record["base_polygon_count"] == record["evaluated_polygon_count"]
    )
    record["passed"] = (
        record["vertex_indices_compatible"] and record["face_indices_compatible"]
    )
    return record


def captured_deformation_series(
    verifier: Any,
    config: Mapping[str, Any],
    body: Any,
    rig: Any,
    patch_faces: set[int],
    seam_cycle: Sequence[int],
    candidate_exact: Mapping[str, Any],
    bpy: Any,
    bmesh: Any,
    exact_module: Any,
    topology: Any,
) -> dict[str, Any]:
    captured: list[dict[str, Any]] = []
    unchanged_exact_intersections = verifier.exact_intersections

    def capture(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result = unchanged_exact_intersections(*args, **kwargs)
        captured.append(result)
        return result

    verifier.exact_intersections = capture
    try:
        records, _points = verifier.deformation_series(
            config,
            body,
            rig,
            patch_faces,
            seam_cycle,
            candidate_exact,
            bpy,
            bmesh,
            exact_module,
            topology,
        )
    finally:
        verifier.exact_intersections = unchanged_exact_intersections
    pose_ids = [pose["id"] for pose in config["poses"]]
    if len(captured) != len(pose_ids) or set(records) != set(pose_ids):
        raise DiagnosticError("per-pose full-intersection capture is incomplete")
    return {
        pose_id: {
            **records[pose_id],
            "full_exact_intersections": captured[index],
        }
        for index, pose_id in enumerate(pose_ids)
    }


def run(config_path: Path, explicit_execution: bool) -> int:
    from tools import blender_verify_kira_r23_postsave_fresh_reopen as verifier

    diagnostic_config = read_json(config_path)
    contract = validate_contract(diagnostic_config, explicit_execution, verifier)
    verification_config = verifier.read_json(contract["verification_config_path"])
    fixed_inputs = verifier.verify_fixed_inputs(verification_config)
    candidate_path = verifier.require_binding(
        verification_config["candidate_binding"], "candidate"
    )
    build_evidence_path = verifier.require_binding(
        verification_config["build_evidence_binding"], "build evidence"
    )
    verifier.verify_build_evidence_binding(
        verification_config, {"build_evidence": build_evidence_path}
    )
    source_path = verifier.project_path(
        verification_config["fixed_inputs"]["r19_source_blend"]["path"]
    )
    source_before = {
        "bytes": source_path.stat().st_size,
        "sha256": verifier.sha256_file(source_path),
    }
    candidate_before = {
        "bytes": candidate_path.stat().st_size,
        "sha256": verifier.sha256_file(candidate_path),
    }
    output_directory = contract["output_directory"]
    output_directory.mkdir(parents=True, exist_ok=False)
    try:
        import bmesh
        import bpy
        from tools import blender_exact_mesh_intersections as exact_module
        from tools import blender_preflight_kira_r23_cc0_afes_expanded_mask as preflight
        from tools import kira_r23_cc0_afes_preflight_core as topology
        from tools import kira_r23_blender51_action_serializer as actions

        if bpy.data.filepath:
            raise DiagnosticError("diagnostic was not launched factory-empty")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False)
        source = verifier.source_snapshot(
            verification_config,
            bpy,
            bmesh,
            preflight,
            actions,
            exact_module,
            topology,
        )
        source_baseline_count = source["exact_intersections"]["exact_report"][
            "exact_genuine_penetration_pair_count"
        ]
        expected_source_baseline = verification_config["inherited_r19_baseline"][
            "neutral_exact_genuine_nonadjacent_intersection_pair_count"
        ]
        if source_baseline_count != expected_source_baseline:
            raise DiagnosticError("exact R19 intersection baseline drifted")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.wm.open_mainfile(filepath=str(candidate_path), load_ui=False)
        names = verification_config["objects"]
        body = bpy.data.objects.get(names["r23_body"])
        rig = bpy.data.objects.get(names["rig"])
        if body is None or rig is None:
            raise DiagnosticError("exact candidate body or native rig is absent")
        verifier.suspend_rig_action(rig)
        verifier.apply_pose(rig, {})
        bpy.context.scene.frame_set(0)
        bpy.context.view_layer.update()
        index_compatibility = evaluated_index_compatibility(body, bpy)
        if not index_compatibility["passed"]:
            raise DiagnosticError(
                "evaluated topology changes face/vertex index interpretation"
            )
        patch_faces, patch_material_index = verifier.patch_face_indices(
            body, names["r23_patch_material"]
        )
        candidate_exact = verifier.exact_intersections(
            body, bpy, bmesh, exact_module
        )
        candidate_pairs = {
            tuple(pair) for pair in candidate_exact["genuine_index_pairs"]
        }
        patch_pairs = sorted(
            [
                list(pair)
                for pair in candidate_pairs
                if any(index in patch_faces for index in pair)
            ]
        )
        source_geometry_pairs = Counter(
            tuple(pair)
            for pair in source["exact_intersections"]["genuine_geometry_pairs"]
        )
        candidate_geometry_pairs = Counter(
            tuple(pair) for pair in candidate_exact["genuine_geometry_pairs"]
        )
        new_geometry_pairs = candidate_geometry_pairs - source_geometry_pairs
        expected_baseline = verification_config["inherited_r19_baseline"][
            "neutral_exact_genuine_nonadjacent_intersection_pair_count"
        ]
        intersections = {
            "r19_neutral_full": source["exact_intersections"],
            "r23_neutral_full": candidate_exact,
            "new_geometry_pair_count_vs_r19": sum(new_geometry_pairs.values()),
            "new_geometry_pairs_vs_r19": [
                list(pair) for pair in sorted(new_geometry_pairs.elements())
            ],
            "patch_involving_pairs": patch_pairs,
            "checks": {
                "candidate_not_above_inherited_count": len(candidate_pairs)
                <= expected_baseline,
                "no_new_geometry_bound_pair": not new_geometry_pairs,
                "zero_patch_involving_pair": not patch_pairs,
            },
        }
        continuity = verifier.seam_continuity(
            body,
            source,
            patch_faces,
            topology,
            verification_config["continuity_thresholds"],
        )
        localized_continuity = continuity_localization(
            verifier,
            body,
            source,
            patch_faces,
            topology,
            continuity,
            verification_config["continuity_thresholds"],
        )
        deformation = captured_deformation_series(
            verifier,
            verification_config,
            body,
            rig,
            patch_faces,
            continuity["candidate_cycle"],
            candidate_exact,
            bpy,
            bmesh,
            exact_module,
            topology,
        )
        source_after = {
            "bytes": source_path.stat().st_size,
            "sha256": verifier.sha256_file(source_path),
        }
        candidate_after = {
            "bytes": candidate_path.stat().st_size,
            "sha256": verifier.sha256_file(candidate_path),
        }
        immutability = {
            "source_before": source_before,
            "source_after": source_after,
            "candidate_before": candidate_before,
            "candidate_after": candidate_after,
            "source_unchanged": source_before == source_after,
            "candidate_unchanged": candidate_before == candidate_after,
        }
        if not immutability["source_unchanged"] or not immutability[
            "candidate_unchanged"
        ]:
            raise DiagnosticError("source or candidate changed during diagnostic")
        gate_reproduction = {
            "intersections": all(intersections["checks"].values()),
            "continuity": continuity["passed"],
            "deformation": all(record["passed"] for record in deformation.values()),
        }
        diagnostic = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_ATTEMPT05_POSTSAVE_GATE_DIAGNOSTIC",
            "created_utc": utc_now(),
            "status": "DIAGNOSTIC_METRICS_CAPTURED_NOT_ACCEPTANCE_NOT_OWNER_APPROVAL",
            "diagnostic_config": {
                "path": verifier.relative(config_path),
                "sha256": verifier.sha256_file(config_path),
            },
            "exact_verification_config_binding": diagnostic_config[
                "verification_config_binding"
            ],
            "attempt02_failure_binding": diagnostic_config[
                "attempt02_failure_binding"
            ],
            "fixed_inputs": fixed_inputs,
            "candidate_binding": verification_config["candidate_binding"],
            "build_evidence_binding": verification_config[
                "build_evidence_binding"
            ],
            "factory_empty_source_then_candidate_reopen": True,
            "evaluated_index_compatibility": index_compatibility,
            "patch_material_index": patch_material_index,
            "patch_face_count": len(patch_faces),
            "intersections": intersections,
            "continuity_helper_result": continuity,
            "continuity_full_localization": localized_continuity,
            "deformation_poses_full": deformation,
            "gate_reproduction_without_gate_changes": gate_reproduction,
            "immutability": immutability,
            "operations": {
                "render_performed": False,
                "source_or_candidate_written": False,
                "export_performed": False,
                "runtime_mutation_performed": False,
                "candidate_activated_or_assigned": False,
                "published": False,
                "append_only_private_diagnostic_written": True,
            },
            "truth_boundary": diagnostic_config["truth_boundary"],
        }
        output = diagnostic_config["diagnostic_output"]
        diagnostic_path = output_directory / output["metrics_filename"]
        verifier.write_new_json(diagnostic_path, diagnostic)
        manifest_path = output_directory / output["manifest_filename"]
        verifier.write_new_json(
            manifest_path,
            verifier.output_manifest(output_directory, manifest_path.name),
        )
        print(
            json.dumps(
                {
                    "status": diagnostic["status"],
                    "gate_reproduction": gate_reproduction,
                    "diagnostic": verifier.relative(diagnostic_path),
                    "manifest": verifier.relative(manifest_path),
                },
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        failure = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_ATTEMPT05_POSTSAVE_GATE_DIAGNOSTIC_FAILURE",
            "created_utc": utc_now(),
            "status": "DIAGNOSTIC_COLLECTION_FAILED_NO_ACCEPTANCE_DECISION",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
            "source_before": source_before,
            "source_current": {
                "bytes": source_path.stat().st_size,
                "sha256": verifier.sha256_file(source_path),
            },
            "candidate_before": candidate_before,
            "candidate_current": {
                "bytes": candidate_path.stat().st_size,
                "sha256": verifier.sha256_file(candidate_path),
            },
            "render_performed": False,
            "source_or_candidate_written": False,
            "candidate_remains_inactive_private_and_unapproved": True,
        }
        failure_path = output_directory / diagnostic_config["diagnostic_output"][
            "failure_filename"
        ]
        if not failure_path.exists():
            verifier.write_new_json(failure_path, failure)
        raise


def main() -> int:
    args = arguments()
    config_path = (ROOT / Path(args.config)).resolve()
    try:
        config_path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise DiagnosticError("diagnostic config path escaped project root") from exc
    return run(config_path, bool(getattr(args, "execute_readonly_gate_diagnostic")))


if __name__ == "__main__":
    raise SystemExit(main())
