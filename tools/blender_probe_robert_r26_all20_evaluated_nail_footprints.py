#!/usr/bin/env python3
"""Read-only all-20 evaluated-body footprint audit for Robert R26 nails.

The probe recreates the exact bound R26 body and official rig in memory, but it
does not instantiate even a temporary nail.  For every declared fingernail and
toenail it samples bounded projection candidates on the evaluated body, maps
those evaluated hits back to the weighted raw cage, and verifies that the
declared digit family wins.  It never remaps a nail to a neighboring digit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_nail_footprint_binding_v1 import (  # noqa: E402
    summarize_footprint_binding,
)
from Core.avatar_natural_nail_delivery_v3 import (  # noqa: E402
    CENTER_FRACTION_CANDIDATES,
    FOOTPRINT_SCALE_CANDIDATES,
    MINIMUM_OUTWARD_NORMAL_ALIGNMENT,
    PROJECTION_GRID_SIZE,
    expected_nail_inventory,
    oval_half_width_scale,
)
from tools import blender_avatar_natural_nail_delivery_v3 as nails  # noqa: E402
from tools import blender_build_biological_robert_r26_bald_owner_review as r26  # noqa: E402
from tools import (  # noqa: E402
    blender_diagnose_robert_r26_finger5_nail_exact_looptris as diagnosis02,
)
from tools import (  # noqa: E402
    blender_probe_robert_r26_finger5_nail_local_surface_fallback as probe09,
)


EXPECTED_CONFIG_SHA256 = (
    "c64fa0f833caa86fb59a53d46ab98852ecd8a926666680a1aad11cce54a07c57"
)
FIXED_BINDINGS = {
    "staged_modifier_result": {
        "path": (
            "RecoverySprint/continuation_20260802/"
            "biological_robert_r26_bounded_run/attempt_09_preparation/"
            "nail_modifier_stage_diagnosis/DIAGNOSTIC_RESULT.json"
        ),
        "sha256": "c5df50067511dbaffcad5f735416e5b1f5777c06670e5784d2f21d409093b4fc",
    },
    "official_source_mapping_audit": {
        "path": (
            "RecoverySprint/continuation_20260802/"
            "biological_robert_r26_bounded_run/attempt_09_preparation/"
            "nail_inventory_mapping_audit/"
            "OFFICIAL_SOURCE_MAPPING_AUDIT_STRICT_POLICY_REVALIDATION.json"
        ),
        "sha256": "620ebe22602b760c56aa7ca57986e467a7c34836d84fab6d9d4ec065ea7e4b5d",
    },
    "footprint_binding_contract": {
        "path": "Core/avatar_nail_footprint_binding_v1.py",
        "sha256": "94c5df362b83fccbe64cc0d076339dd35237cd83b80d81bc63332113509f0bf6",
    },
    "footprint_binding_tests": {
        "path": "Tools/test_avatar_nail_footprint_binding_v1.py",
        "sha256": "b5e52a8493d47e19aca65fa98a989481c26447985298bf7e1dfccc8069e6fcbc",
    },
    "source_mapping_audit_script": {
        "path": "Tools/audit_robert_r26_official_nail_inventory_mapping.py",
        "sha256": "0b9f5f583230aa0e8c09ba95e3e64b0bd386d5be560ca75b25f8d91f282b0307",
    },
}
PRIMARY_GRID = PROJECTION_GRID_SIZE
FALLBACK_GRID = 17
MAXIMUM_RAW_CAGE_MAPPING_DISTANCE_M = 0.004
EVALUATED_RAY_OFFSET_M = 0.025
EVALUATED_RAY_LENGTH_M = 0.050


class RobertR26All20FootprintProbeError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = (PROJECT_ROOT / value).resolve()
    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise RobertR26All20FootprintProbeError(
            f"path escapes project root: {path}"
        ) from exc
    return path


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def verify_fixed_inputs(config_path: Path) -> dict[str, Any]:
    if sha256_file(config_path) != EXPECTED_CONFIG_SHA256:
        raise RobertR26All20FootprintProbeError("R26 config changed")
    config = r26.json_file(config_path)
    records = {
        "probe09_bindings": probe09.verify_bindings(),
        "config_inputs_except_unrebound_adapter": (
            probe09.verify_config_inputs_except_adapter(config)
        ),
    }
    for name, expected in FIXED_BINDINGS.items():
        path = project_path(str(expected["path"]))
        actual = sha256_file(path)
        if actual != str(expected["sha256"]):
            raise RobertR26All20FootprintProbeError(
                f"fixed footprint input changed: {name};"
                f"expected={expected['sha256']};actual={actual}"
            )
        records[name] = {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": actual,
        }
    return records


def world_geometry(
    obj: Any, *, evaluated: bool
) -> tuple[list[Vector], list[tuple[int, int, int]]]:
    evaluated_obj = None
    if evaluated:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated_obj = obj.evaluated_get(depsgraph)
        mesh = evaluated_obj.to_mesh()
        matrix = evaluated_obj.matrix_world
    else:
        mesh = obj.data
        matrix = obj.matrix_world
    try:
        mesh.calc_loop_triangles()
        return (
            [matrix @ vertex.co for vertex in mesh.vertices],
            [
                tuple(int(index) for index in triangle.vertices)
                for triangle in mesh.loop_triangles
            ],
        )
    finally:
        if evaluated_obj is not None:
            evaluated_obj.to_mesh_clear()


def body_group_names(body: Any) -> dict[int, str]:
    return {int(group.index): str(group.name) for group in body.vertex_groups}


def interpolate_raw_cage_influences(
    *,
    point: Vector,
    body: Any,
    raw_tree: BVHTree,
    raw_points: Sequence[Vector],
    raw_triangles: Sequence[tuple[int, int, int]],
    group_names: Mapping[int, str],
) -> tuple[dict[str, float], dict[str, Any]]:
    nearest, _normal, raw_triangle_index, raw_distance = raw_tree.find_nearest(
        point, MAXIMUM_RAW_CAGE_MAPPING_DISTANCE_M
    )
    if nearest is None or raw_triangle_index is None:
        raise RobertR26All20FootprintProbeError(
            "evaluated footprint could not map to weighted raw cage"
        )
    triangle = raw_triangles[int(raw_triangle_index)]
    barycentric = r26.barycentric(
        nearest,
        raw_points[triangle[0]],
        raw_points[triangle[1]],
        raw_points[triangle[2]],
    )
    influences: dict[str, float] = defaultdict(float)
    for vertex_index, factor in zip(triangle, barycentric):
        for assignment in body.data.vertices[int(vertex_index)].groups:
            name = group_names.get(int(assignment.group))
            if name is not None and float(assignment.weight) > 0.0:
                influences[name] += float(factor) * float(assignment.weight)
    total = sum(influences.values())
    if total <= 0.0 or not math.isfinite(total):
        raise RobertR26All20FootprintProbeError(
            "raw cage footprint interpolation has no finite weight"
        )
    normalized = {name: value / total for name, value in influences.items()}
    return normalized, {
        "raw_loop_triangle_index": int(raw_triangle_index),
        "raw_triangle_vertex_indices": [int(value) for value in triangle],
        "raw_cage_distance_m": float(raw_distance),
        "raw_barycentric": [float(value) for value in barycentric],
    }


def compact_binding(binding: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in binding.items()
        if key not in {"per_sample"}
    }


def footprint_binding_for_hits(
    *,
    definition: Mapping[str, Any],
    hits: Sequence[Vector],
    body: Any,
    raw_tree: BVHTree,
    raw_points: Sequence[Vector],
    raw_triangles: Sequence[tuple[int, int, int]],
    group_names: Mapping[int, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    samples = []
    mappings = []
    for point in hits:
        influences, mapping = interpolate_raw_cage_influences(
            point=point,
            body=body,
            raw_tree=raw_tree,
            raw_points=raw_points,
            raw_triangles=raw_triangles,
            group_names=group_names,
        )
        samples.append({"influences": influences})
        mappings.append(mapping)
    binding = summarize_footprint_binding(
        nail_id=str(definition["nail_id"]),
        kind=str(definition["kind"]),
        digit=int(definition["digit"]),
        side=str(definition["side"]),
        expected_bone=str(definition["bone"]),
        samples=samples,
    )
    distances = [float(row["raw_cage_distance_m"]) for row in mappings]
    raw_faces = sorted({int(row["raw_loop_triangle_index"]) for row in mappings})
    return compact_binding(binding), {
        "sample_count": len(mappings),
        "raw_cage_distance_m_minimum": min(distances),
        "raw_cage_distance_m_maximum": max(distances),
        "raw_cage_mapping_distance_bound_m": (
            MAXIMUM_RAW_CAGE_MAPPING_DISTANCE_M
        ),
        "raw_loop_triangle_count": len(raw_faces),
        "raw_loop_triangle_indices": raw_faces,
    }


def primary_candidates(
    *,
    definition: Mapping[str, Any],
    evaluated_tree: BVHTree,
    terminal: Vector,
    longitudinal: Vector,
    lateral: Vector,
    outward: Vector,
    length_m: float,
    width_m: float,
) -> Iterable[dict[str, Any]]:
    grid = PRIMARY_GRID
    for footprint_scale in FOOTPRINT_SCALE_CANDIDATES:
        for center_fraction in CENTER_FRACTION_CANDIDATES:
            nominal_center = terminal - longitudinal * (
                length_m * float(center_fraction)
            )
            hits = []
            normals = []
            failure_reason = ""
            for row in range(grid):
                along = (
                    ((row / (grid - 1)) - 0.5)
                    * length_m
                    * float(footprint_scale)
                )
                row_width = oval_half_width_scale(row, grid)
                for column in range(grid):
                    across = (
                        ((column / (grid - 1)) - 0.5)
                        * width_m
                        * float(footprint_scale)
                        * row_width
                    )
                    expected = nominal_center + longitudinal * along + lateral * across
                    hit, normal, _face, _distance = evaluated_tree.ray_cast(
                        expected + outward * EVALUATED_RAY_OFFSET_M,
                        -outward,
                        EVALUATED_RAY_LENGTH_M,
                    )
                    if hit is None or normal is None:
                        failure_reason = f"evaluated_surface_ray_miss_{row}_{column}"
                        break
                    if normal.dot(outward) < 0.0:
                        normal = -normal
                    normal.normalize()
                    if float(normal.dot(outward)) < MINIMUM_OUTWARD_NORMAL_ALIGNMENT:
                        failure_reason = (
                            f"evaluated_surface_normal_mismatch_{row}_{column}"
                        )
                        break
                    hits.append(hit.copy())
                    normals.append(normal.copy())
                if failure_reason:
                    break
            yield {
                "projection_method": "evaluated_first_hit_raycast",
                "grid": grid,
                "footprint_scale": float(footprint_scale),
                "center_fraction": float(center_fraction),
                "complete": not failure_reason and len(hits) == grid * grid,
                "failure_reason": failure_reason,
                "hits": hits,
                "normals": normals,
            }


def fallback_candidates(
    *,
    evaluated_tree: BVHTree,
    terminal: Vector,
    longitudinal_hint: Vector,
    outward_hint: Vector,
    length_m: float,
    width_m: float,
) -> Iterable[dict[str, Any]]:
    grid = FALLBACK_GRID
    for footprint_scale in FOOTPRINT_SCALE_CANDIDATES:
        for center_fraction in CENTER_FRACTION_CANDIDATES:
            nominal_center = terminal - longitudinal_hint * (
                length_m * float(center_fraction)
            )
            center_hit, center_normal, center_face, center_distance = (
                evaluated_tree.ray_cast(
                    nominal_center + outward_hint * EVALUATED_RAY_OFFSET_M,
                    -outward_hint,
                    EVALUATED_RAY_LENGTH_M,
                )
            )
            if center_hit is None or center_normal is None:
                yield {
                    "projection_method": "evaluated_nearest_coherent_fallback",
                    "grid": grid,
                    "footprint_scale": float(footprint_scale),
                    "center_fraction": float(center_fraction),
                    "complete": False,
                    "failure_reason": "evaluated_center_ray_miss",
                    "hits": [],
                    "normals": [],
                }
                continue
            if center_normal.dot(outward_hint) < 0.0:
                center_normal = -center_normal
            center_normal.normalize()
            longitudinal = longitudinal_hint - center_normal * (
                longitudinal_hint.dot(center_normal)
            )
            if longitudinal.length <= 1.0e-8:
                yield {
                    "projection_method": "evaluated_nearest_coherent_fallback",
                    "grid": grid,
                    "footprint_scale": float(footprint_scale),
                    "center_fraction": float(center_fraction),
                    "complete": False,
                    "failure_reason": "evaluated_local_tangent_degenerate",
                    "hits": [],
                    "normals": [],
                }
                continue
            longitudinal.normalize()
            if longitudinal.dot(longitudinal_hint) < 0.0:
                longitudinal = -longitudinal
            lateral = center_normal.cross(longitudinal)
            if lateral.length <= 1.0e-8:
                raise RobertR26All20FootprintProbeError(
                    "evaluated fallback lateral tangent degenerate"
                )
            lateral.normalize()
            hits = []
            normals = []
            maximum_query_distance = 0.0
            failure_reason = ""
            for row in range(grid):
                along = (
                    ((row / (grid - 1)) - 0.5)
                    * length_m
                    * float(footprint_scale)
                )
                row_width = oval_half_width_scale(row, grid)
                for column in range(grid):
                    across = (
                        ((column / (grid - 1)) - 0.5)
                        * width_m
                        * float(footprint_scale)
                        * row_width
                    )
                    expected = center_hit + longitudinal * along + lateral * across
                    hit, normal, _face, query_distance = evaluated_tree.find_nearest(
                        expected,
                        nails.LOCAL_SURFACE_MAXIMUM_QUERY_DISTANCE_M,
                    )
                    if hit is None or normal is None:
                        failure_reason = f"evaluated_nearest_miss_{row}_{column}"
                        break
                    maximum_query_distance = max(
                        maximum_query_distance, float(query_distance)
                    )
                    if normal.dot(center_normal) < 0.0:
                        normal = -normal
                    normal.normalize()
                    if (
                        float(normal.dot(center_normal))
                        < MINIMUM_OUTWARD_NORMAL_ALIGNMENT
                    ):
                        failure_reason = (
                            f"evaluated_local_surface_discontinuity_{row}_{column}"
                        )
                        break
                    hits.append(hit.copy())
                    normals.append(normal.copy())
                if failure_reason:
                    break
            yield {
                "projection_method": "evaluated_nearest_coherent_fallback",
                "grid": grid,
                "footprint_scale": float(footprint_scale),
                "center_fraction": float(center_fraction),
                "complete": not failure_reason and len(hits) == grid * grid,
                "failure_reason": failure_reason,
                "center_surface_face_index": int(center_face),
                "center_ray_distance_m": float(center_distance),
                "maximum_nearest_query_distance_m": maximum_query_distance,
                "hits": hits,
                "normals": normals,
            }


def audit_definition(
    *,
    definition: Mapping[str, Any],
    body: Any,
    armature: Any,
    target_height_m: float,
    evaluated_tree: BVHTree,
    raw_tree: BVHTree,
    raw_points: Sequence[Vector],
    raw_triangles: Sequence[tuple[int, int, int]],
    group_names: Mapping[int, str],
) -> dict[str, Any]:
    terminal, longitudinal, lateral, outward = nails._terminal_frame(  # noqa: SLF001
        armature, str(definition["bone"]), definition["outward_hint"]
    )
    length_m = target_height_m * float(definition["length_height_fraction"])
    width_m = target_height_m * float(definition["width_height_fraction"])
    candidates = []
    passing_indices = []
    streams = (
        primary_candidates(
            definition=definition,
            evaluated_tree=evaluated_tree,
            terminal=terminal,
            longitudinal=longitudinal,
            lateral=lateral,
            outward=outward,
            length_m=length_m,
            width_m=width_m,
        ),
        fallback_candidates(
            evaluated_tree=evaluated_tree,
            terminal=terminal,
            longitudinal_hint=longitudinal,
            outward_hint=outward,
            length_m=length_m,
            width_m=width_m,
        ),
    )
    for stream in streams:
        for candidate in stream:
            hits = candidate.pop("hits")
            candidate.pop("normals")
            record = dict(candidate)
            if candidate["complete"] is True:
                try:
                    binding, cage = footprint_binding_for_hits(
                        definition=definition,
                        hits=hits,
                        body=body,
                        raw_tree=raw_tree,
                        raw_points=raw_points,
                        raw_triangles=raw_triangles,
                        group_names=group_names,
                    )
                    record["footprint_binding"] = binding
                    record["raw_cage_mapping"] = cage
                    if binding["passed"] is True:
                        passing_indices.append(len(candidates))
                except Exception as exc:
                    record["complete"] = False
                    record["failure_reason"] = (
                        "evaluated_hit_to_raw_weight_mapping_failed: " + str(exc)
                    )
            candidates.append(record)
    selected_index = passing_indices[0] if passing_indices else None
    selected = candidates[selected_index] if selected_index is not None else None
    return {
        "nail_id": str(definition["nail_id"]),
        "kind": str(definition["kind"]),
        "side": str(definition["side"]),
        "digit": int(definition["digit"]),
        "expected_terminal_bone": str(definition["bone"]),
        "target_height_m": float(target_height_m),
        "nominal_length_m": length_m,
        "nominal_width_m": width_m,
        "candidate_count": len(candidates),
        "expected_candidate_count": 48,
        "complete_candidate_count": sum(row["complete"] is True for row in candidates),
        "passing_expected_digit_candidate_count": len(passing_indices),
        "selected_candidate_index": selected_index,
        "selected_candidate": selected,
        "passed": selected_index is not None,
        "automatic_bone_remap_performed": False,
        "candidates": candidates,
    }


def modifier_stack(obj: Any) -> list[dict[str, Any]]:
    rows = []
    for index, modifier in enumerate(obj.modifiers):
        row = {
            "index": index,
            "name": str(modifier.name),
            "type": str(modifier.type),
            "show_viewport": bool(modifier.show_viewport),
            "show_render": bool(modifier.show_render),
        }
        if modifier.type == "ARMATURE":
            row["target"] = modifier.object.name if modifier.object else None
            row["use_vertex_groups"] = bool(modifier.use_vertex_groups)
            row["use_deform_preserve_volume"] = bool(
                modifier.use_deform_preserve_volume
            )
        elif modifier.type == "SUBSURF":
            row["levels"] = int(modifier.levels)
            row["render_levels"] = int(modifier.render_levels)
            row["subdivision_type"] = str(modifier.subdivision_type)
        rows.append(row)
    return rows


def cleanup_all() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def main() -> None:
    args = parse_args()
    config_path = project_path(args.config)
    output_path = project_path(args.output)
    if output_path.exists():
        raise RobertR26All20FootprintProbeError(
            f"append-only output exists: {output_path}"
        )
    candidate_path = project_path(
        "Avatar/private_owner_review/dual_robert_20260729/"
        "biological_robert_r26_bald_owner_review"
    )
    if candidate_path.exists():
        raise RobertR26All20FootprintProbeError(
            "R26 candidate appeared before all-20 footprint probe"
        )
    evidence: dict[str, Any] = {
        "schema": "kira.avatar.robert_r26_all20_evaluated_nail_footprint_probe.v1",
        "created_utc": utc_now(),
        "status": "RUNNING_READ_ONLY_ALL20_FOOTPRINT_PROBE",
        "config_rebound": False,
        "candidate_absent_before": True,
        "candidate_absent_after": None,
        "nail_objects_instantiated": 0,
        "blend_opened_as_main_file": False,
        "blend_saved": False,
        "render_performed": False,
        "candidate_created": False,
        "activation_assignment_export_publication_or_upload": False,
    }
    failed = False
    try:
        evidence["fixed_inputs_before"] = verify_fixed_inputs(config_path)
        config = r26.json_file(config_path)
        body, armature, height, height_envelope, transfer, rig = (
            diagnosis02.recreate_bound_body_and_rig(config)
        )
        body_signature_before = nails._mesh_signature(body)  # noqa: SLF001
        rig_signature_before = nails._rig_signature(armature)  # noqa: SLF001
        body_modifier_count_before = len(body.modifiers)
        raw_points, raw_triangles = world_geometry(body, evaluated=False)
        evaluated_points, evaluated_triangles = world_geometry(body, evaluated=True)
        raw_tree = BVHTree.FromPolygons(
            raw_points, raw_triangles, all_triangles=True
        )
        evaluated_tree = BVHTree.FromPolygons(
            evaluated_points, evaluated_triangles, all_triangles=True
        )
        names = body_group_names(body)
        records = [
            audit_definition(
                definition=definition,
                body=body,
                armature=armature,
                target_height_m=height,
                evaluated_tree=evaluated_tree,
                raw_tree=raw_tree,
                raw_points=raw_points,
                raw_triangles=raw_triangles,
                group_names=names,
            )
            for definition in expected_nail_inventory()
        ]
        body_signature_after = nails._mesh_signature(body)  # noqa: SLF001
        rig_signature_after = nails._rig_signature(armature)  # noqa: SLF001
        expected_ids = {
            str(row["nail_id"]) for row in expected_nail_inventory()
        }
        actual_ids = [str(row["nail_id"]) for row in records]
        gates = {
            "all_20_inventory_entries_recorded": len(records) == 20
            and len(set(actual_ids)) == 20
            and set(actual_ids) == expected_ids,
            "all_20_exhausted_exact_48_bounded_candidates": all(
                int(row["candidate_count"]) == 48 for row in records
            ),
            "no_nail_geometry_instantiated": sum(
                "nail" in obj.name.lower() and obj.type == "MESH"
                for obj in bpy.data.objects
            )
            == 0,
            "body_mesh_unchanged": body_signature_after == body_signature_before,
            "official_rig_unchanged": rig_signature_after == rig_signature_before,
            "body_modifier_stack_unchanged": len(body.modifiers)
            == body_modifier_count_before,
        }
        evidence.update(
            {
                "height_envelope": height_envelope,
                "transfer_summary": transfer,
                "rig_summary": rig,
                "body_modifier_stack": modifier_stack(body),
                "raw_body_geometry": {
                    "vertex_count": len(raw_points),
                    "loop_triangle_count": len(raw_triangles),
                },
                "evaluated_body_geometry": {
                    "vertex_count": len(evaluated_points),
                    "loop_triangle_count": len(evaluated_triangles),
                },
                "records": records,
                "binding_summary": {
                    "passed_count": sum(row["passed"] is True for row in records),
                    "failed_count": sum(row["passed"] is not True for row in records),
                    "failed_nail_ids": [
                        row["nail_id"] for row in records if row["passed"] is not True
                    ],
                    "all_twenty_passed": all(row["passed"] is True for row in records),
                    "acceptance_claimed": False,
                },
                "body_mesh_sha256_before": body_signature_before,
                "body_mesh_sha256_after": body_signature_after,
                "official_rig_sha256_before": rig_signature_before,
                "official_rig_sha256_after": rig_signature_after,
                "gates": gates,
            }
        )
        if not all(gates.values()):
            raise RobertR26All20FootprintProbeError(
                "all-20 footprint diagnostic execution gates failed: "
                + ",".join(name for name, passed in gates.items() if not passed)
            )
        evidence["status"] = (
            "COMPLETE_READ_ONLY_ALL20_EVALUATED_FOOTPRINT_DIAGNOSIS_NO_CANDIDATE"
        )
    except Exception as exc:
        failed = True
        evidence["status"] = "FAILED_READ_ONLY_ALL20_FOOTPRINT_PROBE_PRESERVED"
        evidence["exception_type"] = type(exc).__name__
        evidence["exception"] = str(exc)
        evidence["traceback"] = traceback.format_exc()
    finally:
        cleanup_all()
        evidence["temporary_objects_remaining"] = len(bpy.data.objects)
        evidence["candidate_absent_after"] = not candidate_path.exists()
        try:
            evidence["fixed_inputs_after"] = verify_fixed_inputs(config_path)
        except Exception as binding_exc:
            failed = True
            evidence["status"] = "FAILED_READ_ONLY_ALL20_FOOTPRINT_PROBE_PRESERVED"
            evidence["post_cleanup_binding_exception"] = str(binding_exc)
            evidence["post_cleanup_binding_traceback"] = traceback.format_exc()
        if (
            int(evidence["temporary_objects_remaining"]) != 0
            or evidence["candidate_absent_after"] is not True
        ):
            failed = True
            evidence["status"] = "FAILED_READ_ONLY_ALL20_FOOTPRINT_PROBE_PRESERVED"
            evidence["cleanup_gate_failed"] = True
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
