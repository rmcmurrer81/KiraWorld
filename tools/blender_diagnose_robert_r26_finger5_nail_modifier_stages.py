#!/usr/bin/env python3
"""Read-only modifier-stage diagnosis for the R26 left little-finger nail.

This diagnosis exists only because the sealed Attempt 09 component probe
proved zero raw top-plate crossings but 216 genuine crossings after Blender
evaluated the component.  It recreates the exact bound body and rig in memory,
instantiates only that one nail, and separates the evaluated effects of the
armature and Solidify modifiers.  It never saves or opens a Blend as the main
file, renders, builds a candidate, rebinds a config, exports, activates,
publishes, or uploads anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_natural_nail_delivery_v3 import (  # noqa: E402
    FREE_EDGE_MATERIAL,
    NAIL_BED_MATERIAL,
    expected_nail_inventory,
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
EXPECTED_ADAPTER_SHA256 = (
    "65edf49c0f72523a7728f30ee5243a522d9866f825e9b940ad44f23f41b669c8"
)
EXPECTED_PROBE09_SCRIPT_SHA256 = (
    "34b01c8323bc48f82e922c321044fbb2aca7247c20c3fafeddf8992d73a50327"
)
EXPECTED_PROBE09_RESULT_SHA256 = (
    "64e2e8ab4cd8bdcd7bdb0133725b43f20211446d072a92869eb22c16f00fca03"
)
PROBE09_RESULT = (
    "RecoverySprint/continuation_20260802/"
    "biological_robert_r26_bounded_run/attempt_09_preparation/"
    "nail_component_probe/PROBE_RESULT.json"
)
TARGET_NAIL_ID = "fingernail_5_L"
TARGET_BONE = "finger5-3.L"
ARMATURE_MODIFIER_NAME = "Official_Rigid_Bone_Attachment"
SOLIDIFY_MODIFIER_NAME = "Natural_Nail_Plate_Thickness_V3"
STAGE_SPECS = (
    ("no_nail_modifiers", False, False),
    ("armature_only", True, False),
    ("solidify_only", False, True),
    ("current_armature_then_solidify", True, True),
)


class RobertR26NailModifierStageDiagnosisError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
        raise RobertR26NailModifierStageDiagnosisError(
            f"path escapes project root: {path}"
        ) from exc
    return path


def _quantile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    position = max(0.0, min(1.0, float(fraction))) * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    alpha = position - low
    return ordered[low] * (1.0 - alpha) + ordered[high] * alpha


def displacement_record(first: Sequence[Vector], second: Sequence[Vector]) -> dict[str, Any]:
    if len(first) != len(second):
        return {
            "first_vertex_count": len(first),
            "second_vertex_count": len(second),
            "index_stable": False,
        }
    distances = [float((right - left).length) for left, right in zip(first, second)]
    return {
        "first_vertex_count": len(first),
        "second_vertex_count": len(second),
        "index_stable": True,
        "minimum_displacement_m": min(distances),
        "median_displacement_m": _quantile(distances, 0.5),
        "percentile_95_displacement_m": _quantile(distances, 0.95),
        "maximum_displacement_m": max(distances),
    }


def solidify_triangle_region(indices: Iterable[int], source_vertex_count: int) -> str:
    values = tuple(int(value) for value in indices)
    if values and all(0 <= value < source_vertex_count for value in values):
        return "index_block_0"
    if values and all(
        source_vertex_count <= value < source_vertex_count * 2 for value in values
    ):
        return "index_block_1"
    return "mixed_index_rim_or_unexpected"


def world_geometry(obj: Any, *, evaluated: bool) -> tuple[list[Vector], list[tuple[int, int, int]]]:
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


def exact_pair_record(
    body_points: Sequence[Vector],
    body_triangles: Sequence[tuple[int, int, int]],
    nail_points: Sequence[Vector],
    nail_triangles: Sequence[tuple[int, int, int]],
    *,
    source_nail_vertex_count: int,
) -> dict[str, Any]:
    body_tree = BVHTree.FromPolygons(
        list(body_points), list(body_triangles), all_triangles=True
    )
    nail_tree = BVHTree.FromPolygons(
        list(nail_points), list(nail_triangles), all_triangles=True
    )
    broad_pairs = sorted(body_tree.overlap(nail_tree))
    all_points = list(body_points) + list(nail_points)
    low = Vector(
        tuple(min(float(point[axis]) for point in all_points) for axis in range(3))
    )
    high = Vector(
        tuple(max(float(point[axis]) for point in all_points) for axis in range(3))
    )
    tolerance = max(1.0e-10, float((high - low).length) * 1.0e-8)
    classification_counts: dict[str, int] = {}
    genuine_by_region: dict[str, int] = {}
    genuine_pairs: list[list[int]] = []
    for body_index, nail_index in broad_pairs:
        result = nails.exact_auditor.classify_triangle_pair(
            tuple(body_points[index] for index in body_triangles[body_index]),
            tuple(nail_points[index] for index in nail_triangles[nail_index]),
            linear_tolerance=tolerance,
        )
        classification = str(result["classification"])
        classification_counts[classification] = (
            classification_counts.get(classification, 0) + 1
        )
        if result.get("genuine_penetration") is True:
            region = solidify_triangle_region(
                nail_triangles[nail_index], source_nail_vertex_count
            )
            genuine_by_region[region] = genuine_by_region.get(region, 0) + 1
            genuine_pairs.append([int(body_index), int(nail_index)])
    distances = []
    for point in nail_points:
        nearest = body_tree.find_nearest(point)
        if nearest[0] is None:
            raise RobertR26NailModifierStageDiagnosisError(
                "body clearance query failed"
            )
        distances.append(float(nearest[3]))
    return {
        "body_vertex_count": len(body_points),
        "body_loop_triangle_count": len(body_triangles),
        "nail_vertex_count": len(nail_points),
        "nail_loop_triangle_count": len(nail_triangles),
        "bvh_triangle_pair_count": len(broad_pairs),
        "classification_counts": classification_counts,
        "exact_genuine_triangle_pair_count": len(genuine_pairs),
        "exact_genuine_triangle_pairs": genuine_pairs,
        "exact_genuine_pairs_by_solidify_index_region": genuine_by_region,
        "linear_tolerance_m": tolerance,
        "minimum_unsigned_surface_clearance_m": min(distances),
        "median_unsigned_surface_clearance_m": _quantile(distances, 0.5),
        "maximum_unsigned_surface_clearance_m": max(distances),
        "broad_phase_is_not_the_pass_gate": True,
    }


def matrix_record(matrix: Matrix) -> list[list[float]]:
    return [[float(matrix[row][column]) for column in range(4)] for row in range(4)]


def identity_delta(matrix: Matrix) -> float:
    identity = Matrix.Identity(4)
    return max(
        abs(float(matrix[row][column]) - float(identity[row][column]))
        for row in range(4)
        for column in range(4)
    )


def modifier_record(modifier: Any) -> dict[str, Any]:
    row = {
        "name": modifier.name,
        "type": modifier.type,
        "show_viewport": bool(modifier.show_viewport),
        "show_render": bool(modifier.show_render),
    }
    if modifier.type == "ARMATURE":
        row.update(
            {
                "target": modifier.object.name if modifier.object else None,
                "use_vertex_groups": bool(modifier.use_vertex_groups),
                "use_deform_preserve_volume": bool(
                    modifier.use_deform_preserve_volume
                ),
            }
        )
    elif modifier.type == "SOLIDIFY":
        row.update(
            {
                "thickness_m": float(modifier.thickness),
                "offset": float(modifier.offset),
                "use_even_offset": bool(modifier.use_even_offset),
                "use_rim": bool(modifier.use_rim),
            }
        )
    return row


def set_modifier_state(
    armature_modifier: Any,
    solidify_modifier: Any,
    *,
    armature_enabled: bool,
    solidify_enabled: bool,
) -> None:
    armature_modifier.show_viewport = bool(armature_enabled)
    armature_modifier.show_render = bool(armature_enabled)
    solidify_modifier.show_viewport = bool(solidify_enabled)
    solidify_modifier.show_render = bool(solidify_enabled)
    bpy.context.view_layer.update()


def footprint_weight_record(
    body: Any,
    body_tree: BVHTree,
    body_triangles: Sequence[tuple[int, int, int]],
    nail_points: Sequence[Vector],
    terminal_bone: str,
) -> dict[str, Any]:
    triangle_indices = []
    for point in nail_points:
        nearest = body_tree.find_nearest(point)
        if nearest[0] is None or nearest[2] is None:
            raise RobertR26NailModifierStageDiagnosisError(
                "footprint nearest-body query failed"
            )
        triangle_indices.append(int(nearest[2]))
    body_vertex_indices = sorted(
        {
            int(vertex_index)
            for triangle_index in triangle_indices
            for vertex_index in body_triangles[triangle_index]
        }
    )
    names = {int(group.index): str(group.name) for group in body.vertex_groups}
    terminal_weights = []
    influence_names: set[str] = set()
    per_vertex = []
    for vertex_index in body_vertex_indices:
        influences = sorted(
            (
                names.get(int(element.group), f"unknown_group_{element.group}"),
                float(element.weight),
            )
            for element in body.data.vertices[vertex_index].groups
            if float(element.weight) > 0.0
        )
        terminal_weight = sum(
            weight for name, weight in influences if name == terminal_bone
        )
        terminal_weights.append(terminal_weight)
        influence_names.update(name for name, _weight in influences)
        per_vertex.append(
            {
                "body_vertex_index": vertex_index,
                "terminal_bone_weight": terminal_weight,
                "influences": [
                    {"bone": name, "weight": weight}
                    for name, weight in influences
                ],
            }
        )
    return {
        "nearest_body_loop_triangle_count": len(set(triangle_indices)),
        "nearest_body_loop_triangle_indices": sorted(set(triangle_indices)),
        "footprint_body_vertex_count": len(body_vertex_indices),
        "terminal_bone": terminal_bone,
        "minimum_terminal_bone_weight": min(terminal_weights),
        "median_terminal_bone_weight": _quantile(terminal_weights, 0.5),
        "maximum_terminal_bone_weight": max(terminal_weights),
        "all_body_influence_names": sorted(influence_names),
        "body_vertices": per_vertex,
    }


def verify_fixed_inputs(config_path: Path) -> dict[str, Any]:
    bindings = probe09.verify_bindings()
    config = r26.json_file(config_path)
    config_bindings = probe09.verify_config_inputs_except_adapter(config)
    extra = {
        "attempt09_probe_script": {
            "path": "Tools/blender_probe_robert_r26_finger5_nail_local_surface_fallback.py",
            "expected_sha256": EXPECTED_PROBE09_SCRIPT_SHA256,
        },
        "attempt09_probe_result": {
            "path": PROBE09_RESULT,
            "expected_sha256": EXPECTED_PROBE09_RESULT_SHA256,
        },
    }
    extra_records = {}
    for name, row in extra.items():
        path = project_path(str(row["path"]))
        actual = sha256_file(path)
        if actual != str(row["expected_sha256"]):
            raise RobertR26NailModifierStageDiagnosisError(
                f"fixed input changed: {name}; expected={row['expected_sha256']};"
                f"actual={actual}"
            )
        extra_records[name] = {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": actual,
        }
    if sha256_file(config_path) != EXPECTED_CONFIG_SHA256:
        raise RobertR26NailModifierStageDiagnosisError(
            "R26 config changed before modifier-stage diagnosis"
        )
    if sha256_file(project_path("Tools/blender_avatar_natural_nail_delivery_v3.py")) != EXPECTED_ADAPTER_SHA256:
        raise RobertR26NailModifierStageDiagnosisError(
            "R26 nail adapter changed before modifier-stage diagnosis"
        )
    return {
        "probe09_bindings": bindings,
        "config_inputs_except_unrebound_adapter": config_bindings,
        **extra_records,
    }


def main() -> None:
    args = parse_args()
    config_path = project_path(args.config)
    output_path = project_path(args.output)
    if output_path.exists():
        raise RobertR26NailModifierStageDiagnosisError(
            f"append-only diagnosis output exists: {output_path}"
        )
    candidate_path = project_path(
        "Avatar/private_owner_review/dual_robert_20260729/"
        "biological_robert_r26_bald_owner_review"
    )
    if candidate_path.exists():
        raise RobertR26NailModifierStageDiagnosisError(
            "R26 candidate appeared before modifier-stage diagnosis"
        )

    evidence: dict[str, Any] = {
        "schema": "kira.avatar.robert_r26_finger5_nail_modifier_stage_diagnosis.v1",
        "created_utc": utc_now(),
        "status": "RUNNING_READ_ONLY_MODIFIER_STAGE_DIAGNOSIS",
        "target": {"nail_id": TARGET_NAIL_ID, "bone": TARGET_BONE},
        "config_rebound": False,
        "blend_opened_as_main_file": False,
        "blend_saved": False,
        "render_performed": False,
        "candidate_created": False,
        "activation_assignment_export_publication_or_upload": False,
        "candidate_absent_before": True,
        "candidate_absent_after": None,
    }
    failed = False
    nail = None
    materials: list[Any] = []
    try:
        evidence["fixed_inputs_before"] = verify_fixed_inputs(config_path)
        config = r26.json_file(config_path)
        body, armature, height, height_envelope, transfer, rig = (
            diagnosis02.recreate_bound_body_and_rig(config)
        )
        body_signature_before = nails._mesh_signature(body)  # noqa: SLF001
        rig_signature_before = nails._rig_signature(armature)  # noqa: SLF001
        body_modifier_count_before = len(body.modifiers)
        body_raw_points, body_raw_triangles = world_geometry(body, evaluated=False)
        body_evaluated_points, body_evaluated_triangles = world_geometry(
            body, evaluated=True
        )
        body_tree = BVHTree.FromPolygons(
            body_raw_points, body_raw_triangles, all_triangles=True
        )
        bed_material = nails._natural_nail_material(  # noqa: SLF001
            "R26_Finger5_Modifier_Diagnosis_Nail_Bed", NAIL_BED_MATERIAL
        )
        free_edge_material = nails._natural_nail_material(  # noqa: SLF001
            "R26_Finger5_Modifier_Diagnosis_Free_Edge", FREE_EDGE_MATERIAL
        )
        materials.extend([bed_material, free_edge_material])
        definition = next(
            row
            for row in expected_nail_inventory()
            if row["nail_id"] == TARGET_NAIL_ID
        )
        nail, component_record = nails._projected_oval_nail_plate(  # noqa: SLF001
            name="R26_Finger5_Modifier_Stage_Diagnosis",
            nail_id=TARGET_NAIL_ID,
            body_points=body_raw_points,
            body_triangles=body_raw_triangles,
            body_tree=body_tree,
            armature=armature,
            bone_name=TARGET_BONE,
            outward_hint=definition["outward_hint"],
            length_m=height * float(definition["length_height_fraction"]),
            width_m=height * float(definition["width_height_fraction"]),
            target_height_m=height,
            bed_material=bed_material,
            free_edge_material=free_edge_material,
        )
        source_nail_points, source_nail_triangles = world_geometry(
            nail, evaluated=False
        )
        source_vertex_count = len(source_nail_points)
        armature_modifier = nail.modifiers.get(ARMATURE_MODIFIER_NAME)
        solidify_modifier = nail.modifiers.get(SOLIDIFY_MODIFIER_NAME)
        if armature_modifier is None or armature_modifier.type != "ARMATURE":
            raise RobertR26NailModifierStageDiagnosisError(
                "exact armature modifier unavailable"
            )
        if solidify_modifier is None or solidify_modifier.type != "SOLIDIFY":
            raise RobertR26NailModifierStageDiagnosisError(
                "exact Solidify modifier unavailable"
            )
        if [modifier.name for modifier in nail.modifiers] != [
            ARMATURE_MODIFIER_NAME,
            SOLIDIFY_MODIFIER_NAME,
        ]:
            raise RobertR26NailModifierStageDiagnosisError(
                "nail modifier order changed"
            )

        footprint_weights = footprint_weight_record(
            body,
            body_tree,
            body_raw_triangles,
            source_nail_points,
            TARGET_BONE,
        )
        raw_exact = exact_pair_record(
            body_raw_points,
            body_raw_triangles,
            source_nail_points,
            source_nail_triangles,
            source_nail_vertex_count=source_vertex_count,
        )
        stages = {}
        stage_points: dict[str, list[Vector]] = {}
        for stage_name, armature_enabled, solidify_enabled in STAGE_SPECS:
            set_modifier_state(
                armature_modifier,
                solidify_modifier,
                armature_enabled=armature_enabled,
                solidify_enabled=solidify_enabled,
            )
            points, triangles = world_geometry(nail, evaluated=True)
            stage_points[stage_name] = points
            stages[stage_name] = {
                "armature_modifier_enabled": armature_enabled,
                "solidify_modifier_enabled": solidify_enabled,
                "exact_against_evaluated_body": exact_pair_record(
                    body_evaluated_points,
                    body_evaluated_triangles,
                    points,
                    triangles,
                    source_nail_vertex_count=source_vertex_count,
                ),
            }
        set_modifier_state(
            armature_modifier,
            solidify_modifier,
            armature_enabled=True,
            solidify_enabled=True,
        )

        current_points = stage_points["current_armature_then_solidify"]
        armature_only_points = stage_points["armature_only"]
        shell_blocks: dict[str, Any] = {
            "source_top_vertex_count": source_vertex_count,
            "current_evaluated_vertex_count": len(current_points),
            "exact_two_index_blocks": len(current_points) == source_vertex_count * 2,
        }
        if len(current_points) == source_vertex_count * 2:
            shell_blocks["index_block_0_to_armature_only"] = displacement_record(
                armature_only_points,
                current_points[:source_vertex_count],
            )
            shell_blocks["index_block_1_to_armature_only"] = displacement_record(
                armature_only_points,
                current_points[source_vertex_count:],
            )

        pose_bone = armature.pose.bones.get(TARGET_BONE)
        rest_bone = armature.data.bones.get(TARGET_BONE)
        if pose_bone is None or rest_bone is None:
            raise RobertR26NailModifierStageDiagnosisError(
                "target pose/rest bone unavailable"
            )
        pose_from_rest = pose_bone.matrix @ rest_bone.matrix_local.inverted()
        body_signature_after = nails._mesh_signature(body)  # noqa: SLF001
        rig_signature_after = nails._rig_signature(armature)  # noqa: SLF001
        gates = {
            "attempt09_failure_reproduced_by_current_stage": int(
                stages["current_armature_then_solidify"]
                ["exact_against_evaluated_body"]
                ["exact_genuine_triangle_pair_count"]
            )
            == 216,
            "raw_top_plate_remains_intersection_free": int(
                raw_exact["exact_genuine_triangle_pair_count"]
            )
            == 0,
            "all_four_modifier_stages_recorded": set(stages)
            == {name for name, _armature, _solidify in STAGE_SPECS},
            "body_mesh_unchanged": body_signature_after == body_signature_before,
            "official_rig_unchanged": rig_signature_after == rig_signature_before,
            "body_modifier_stack_unchanged": len(body.modifiers)
            == body_modifier_count_before,
            "only_one_nail_component_instantiated": sum(
                obj.type == "MESH" and "Modifier_Stage_Diagnosis" in obj.name
                for obj in bpy.data.objects
            )
            == 1,
        }
        evidence.update(
            {
                "height_envelope": height_envelope,
                "transfer_summary": transfer,
                "rig_summary": rig,
                "component_record": component_record,
                "body_raw_to_evaluated_rest_displacement": displacement_record(
                    body_raw_points, body_evaluated_points
                ),
                "raw_body_against_raw_top_plate": raw_exact,
                "modifier_stack": [modifier_record(value) for value in nail.modifiers],
                "modifier_stage_records": stages,
                "armature_only_top_plate_from_raw_displacement": displacement_record(
                    source_nail_points, armature_only_points
                ),
                "solidify_index_block_comparison": shell_blocks,
                "underlying_body_weight_inventory": footprint_weights,
                "attachment_transform": {
                    "armature_pose_position": str(armature.data.pose_position),
                    "armature_matrix_world": matrix_record(armature.matrix_world),
                    "nail_matrix_world": matrix_record(nail.matrix_world),
                    "nail_matrix_parent_inverse": matrix_record(
                        nail.matrix_parent_inverse
                    ),
                    "target_pose_from_rest_matrix": matrix_record(pose_from_rest),
                    "target_pose_from_rest_identity_maximum_absolute_delta": (
                        identity_delta(pose_from_rest)
                    ),
                },
                "body_mesh_sha256_before": body_signature_before,
                "body_mesh_sha256_after": body_signature_after,
                "official_rig_sha256_before": rig_signature_before,
                "official_rig_sha256_after": rig_signature_after,
                "gates": gates,
            }
        )
        if not all(gates.values()):
            raise RobertR26NailModifierStageDiagnosisError(
                "modifier-stage diagnosis gates failed: "
                + ",".join(name for name, passed in gates.items() if not passed)
            )
        evidence["status"] = (
            "COMPLETE_READ_ONLY_MODIFIER_STAGE_DIAGNOSIS_NO_CANDIDATE_NO_SAVE"
        )
    except Exception as exc:
        failed = True
        evidence["status"] = "FAILED_READ_ONLY_MODIFIER_STAGE_DIAGNOSIS_PRESERVED"
        evidence["exception_type"] = type(exc).__name__
        evidence["exception"] = str(exc)
        evidence["traceback"] = traceback.format_exc()
    finally:
        probe09.cleanup_probe_data(nail, materials)
        evidence["temporary_diagnosis_objects_remaining"] = sum(
            "Modifier_Stage_Diagnosis" in obj.name for obj in bpy.data.objects
        )
        evidence["temporary_diagnosis_meshes_remaining"] = sum(
            "Modifier_Stage_Diagnosis" in mesh.name for mesh in bpy.data.meshes
        )
        evidence["candidate_absent_after"] = not candidate_path.exists()
        try:
            evidence["fixed_inputs_after"] = verify_fixed_inputs(config_path)
        except Exception as binding_exc:
            failed = True
            evidence["status"] = (
                "FAILED_READ_ONLY_MODIFIER_STAGE_DIAGNOSIS_PRESERVED"
            )
            evidence["post_cleanup_binding_exception"] = str(binding_exc)
            evidence["post_cleanup_binding_traceback"] = traceback.format_exc()
        if (
            int(evidence["temporary_diagnosis_objects_remaining"]) != 0
            or int(evidence["temporary_diagnosis_meshes_remaining"]) != 0
            or evidence["candidate_absent_after"] is not True
        ):
            failed = True
            evidence["status"] = (
                "FAILED_READ_ONLY_MODIFIER_STAGE_DIAGNOSIS_PRESERVED"
            )
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
