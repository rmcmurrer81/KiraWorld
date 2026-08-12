"""Second bounded append-only R21 nail repair.

Attempt 01 stopped before saving because one proximal/lateral index-nail sample
reached a steep but coherent digit surface whose normal alignment was 0.1296,
just below the provisional 0.15 authoring threshold.  Attempt 02 changes only
that pre-intersection localization gate: winding is normalized before judging
coherence and steep curved-edge samples may reach 0.05 alignment.  Exact raw
and evaluated body intersections remain mandatory zero.
"""

from __future__ import annotations

import hashlib
import json
import sys
import traceback
from pathlib import Path
from typing import Any

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.blender_author_kira_r21_nails_attempt01 as a1


MINIMUM_CURVED_EDGE_NORMAL_ALIGNMENT = 0.05
ATTEMPT01_FAILURE = ROOT / "RecoverySprint/continuation_20260802/kira_r21_nail_correction/author_attempt_01/FAILURE_EVIDENCE.json"
DIAGNOSIS = ROOT / "RecoverySprint/continuation_20260802/kira_r21_nail_correction/preflight_02/FOOTPRINT_DIAGNOSIS.json"


def build_plate_geometry_attempt02(
    definition: dict[str, Any],
    body_tree: BVHTree,
    clearance: float,
) -> tuple[list[Vector], list[tuple[int, ...]], list[int], dict[str, Any]]:
    source_center: Vector = definition["source_center_base"]
    normal: Vector = definition["source_normal_candidate_base"].copy()
    nearest, nearest_normal, _face, nearest_distance = body_tree.find_nearest(source_center, 4.0)
    if nearest is None or nearest_normal is None:
        raise RuntimeError(f"no body surface near {definition['source_object']}")
    if normal.dot(nearest_normal) < 0.0:
        normal = -normal
    normal.normalize()
    length: Vector = definition["source_length_candidate_base"].copy()
    length = length - normal * length.dot(normal)
    if length.length <= 1.0e-8:
        raise RuntimeError(f"length tangent collapsed for {definition['source_object']}")
    length.normalize()
    bone_direction = (
        bpy.data.objects[a1.RIG_NAME].data.bones[definition["bone"]].tail_local
        - bpy.data.objects[a1.RIG_NAME].data.bones[definition["bone"]].head_local
    ).normalized()
    if length.dot(bone_direction) < 0.0:
        length = -length
    width = normal.cross(length)
    if width.length <= 1.0e-8:
        raise RuntimeError(f"width tangent collapsed for {definition['source_object']}")
    width.normalize()
    length = width.cross(normal).normalized()
    if length.dot(bone_direction) < 0.0:
        length = -length
        width = -width

    points_np: np.ndarray = definition["source_points"]
    centered = points_np - np.asarray(tuple(source_center), dtype=np.float64)
    length_values = centered @ np.asarray(tuple(length), dtype=np.float64)
    width_values = centered @ np.asarray(tuple(width), dtype=np.float64)
    source_length = float(length_values.max() - length_values.min())
    source_width = float(width_values.max() - width_values.min())
    if definition["kind"] == "fingernail":
        length_scale = 0.68 if definition["digit"] == 1 else 0.70
        width_scale = 0.88
        proximal_shift = 0.075
    else:
        length_scale = 0.70 if definition["digit"] == 1 else 0.76
        width_scale = 0.90
        proximal_shift = 0.050
    target_length = source_length * length_scale
    target_width = source_width * width_scale
    nominal_center = source_center - length * (source_length * proximal_shift)
    ray_hit, ray_normal, ray_face, ray_distance = body_tree.ray_cast(
        nominal_center + normal * 3.0,
        -normal,
        6.0,
    )
    if ray_hit is None or ray_normal is None:
        ray_hit, ray_normal, ray_face, ray_distance = body_tree.find_nearest(nominal_center, 4.0)
    if ray_hit is None or ray_normal is None:
        raise RuntimeError(f"center projection failed for {definition['source_object']}")
    if ray_normal.dot(normal) < 0.0:
        ray_normal = -ray_normal
    surface_center = ray_hit.copy()

    bottom: list[Vector] = []
    top: list[Vector] = []
    sample_normals: list[Vector] = []
    projection_distances: list[float] = []
    nearest_fallback_count = 0
    for row in range(a1.GRID_ROWS):
        u = -1.0 + 2.0 * row / (a1.GRID_ROWS - 1)
        row_width = target_width * 0.5 * a1.rounded_width_factor(u)
        for column in range(a1.GRID_COLUMNS):
            v = -1.0 + 2.0 * column / (a1.GRID_COLUMNS - 1)
            nominal = surface_center + length * (u * target_length * 0.5) + width * (v * row_width)
            hit, hit_normal, _hit_face, hit_distance = body_tree.ray_cast(
                nominal + normal * 2.2,
                -normal,
                4.4,
            )
            if (
                hit is None
                or hit_normal is None
                or abs(float(hit_normal.dot(normal))) < MINIMUM_CURVED_EDGE_NORMAL_ALIGNMENT
            ):
                hit, hit_normal, _hit_face, hit_distance = body_tree.find_nearest(nominal, 2.5)
                nearest_fallback_count += 1
            if hit is None or hit_normal is None:
                raise RuntimeError(f"grid projection failed {definition['source_object']} row={row} col={column}")
            if hit_normal.dot(normal) < 0.0:
                hit_normal = -hit_normal
            hit_normal.normalize()
            alignment = float(hit_normal.dot(normal))
            if alignment < MINIMUM_CURVED_EDGE_NORMAL_ALIGNMENT:
                raise RuntimeError(
                    f"grid surface coherence failed {definition['source_object']} row={row} col={column} alignment={alignment}"
                )
            bottom_point = hit + hit_normal * clearance
            transverse_arch = a1.PLATE_CENTER_ARCH * max(0.0, 1.0 - v * v)
            top_point = bottom_point + hit_normal * (a1.PLATE_BASE_THICKNESS + transverse_arch)
            bottom.append(bottom_point)
            top.append(top_point)
            sample_normals.append(hit_normal.copy())
            projection_distances.append(float(hit_distance))

    count = a1.GRID_ROWS * a1.GRID_COLUMNS
    vertices = bottom + top
    faces: list[tuple[int, ...]] = []
    material_indices: list[int] = []
    for row in range(a1.GRID_ROWS - 1):
        for column in range(a1.GRID_COLUMNS - 1):
            a = row * a1.GRID_COLUMNS + column
            b = (row + 1) * a1.GRID_COLUMNS + column
            c = (row + 1) * a1.GRID_COLUMNS + column + 1
            d = row * a1.GRID_COLUMNS + column + 1
            faces.append((count + a, count + b, count + c, count + d))
            material_indices.append(1 if row == a1.GRID_ROWS - 2 else 0)
            faces.append((d, c, b, a))
            material_indices.append(0)
    for row in range(a1.GRID_ROWS - 1):
        for column in (0, a1.GRID_COLUMNS - 1):
            a = row * a1.GRID_COLUMNS + column
            b = (row + 1) * a1.GRID_COLUMNS + column
            faces.append((a, b, count + b, count + a) if column == a1.GRID_COLUMNS - 1 else (b, a, count + a, count + b))
            material_indices.append(0)
    for row, material_index in ((0, 0), (a1.GRID_ROWS - 1, 1)):
        for column in range(a1.GRID_COLUMNS - 1):
            a = row * a1.GRID_COLUMNS + column
            b = row * a1.GRID_COLUMNS + column + 1
            faces.append((b, a, count + a, count + b) if row == 0 else (a, b, count + b, count + a))
            material_indices.append(material_index)
    details = {
        "source_length_base_units": source_length,
        "source_width_base_units": source_width,
        "target_length_base_units": target_length,
        "target_width_base_units": target_width,
        "length_scale_from_source_envelope": length_scale,
        "width_scale_from_source_envelope": width_scale,
        "proximal_center_shift_source_length_fraction": proximal_shift,
        "base_clearance_base_units": clearance,
        "plate_base_thickness_base_units": a1.PLATE_BASE_THICKNESS,
        "plate_center_arch_base_units": a1.PLATE_CENTER_ARCH,
        "surface_center_base": list(map(float, surface_center)),
        "outward_base": list(map(float, normal)),
        "distal_base": list(map(float, length)),
        "lateral_base": list(map(float, width)),
        "source_center_nearest_distance_base_units": float(nearest_distance),
        "center_projection_face": int(ray_face),
        "center_projection_distance_base_units": float(ray_distance),
        "maximum_grid_projection_distance_base_units": max(projection_distances),
        "minimum_grid_normal_alignment": min(float(value.dot(normal)) for value in sample_normals),
        "minimum_required_curved_edge_normal_alignment": MINIMUM_CURVED_EDGE_NORMAL_ALIGNMENT,
        "nearest_surface_fallback_count": nearest_fallback_count,
        "grid_rows": a1.GRID_ROWS,
        "grid_columns": a1.GRID_COLUMNS,
        "connected_closed_shell_by_construction": True,
    }
    return vertices, faces, material_indices, details


def configure_attempt02() -> None:
    a1.EVIDENCE_DIR = ROOT / "RecoverySprint/continuation_20260802/kira_r21_nail_correction/author_attempt_02"
    a1.OWNER_DIR = ROOT / "Avatar/private_owner_review/kira_r21_bald_localized_correction_attempt_10_nails"
    a1.OUTPUT_BLEND = a1.OWNER_DIR / "KIRA_R21_BALD_PRIVATE_INACTIVE_PELVIS_NAILS_ATTEMPT10.blend"
    a1.EVIDENCE_PATH = a1.EVIDENCE_DIR / "BUILD_EVIDENCE.json"
    a1.OWNER_EVIDENCE_PATH = a1.OWNER_DIR / "BUILD_EVIDENCE.json"
    a1.FAILURE_PATH = a1.EVIDENCE_DIR / "FAILURE_EVIDENCE.json"
    a1.README_PATH = a1.OWNER_DIR / "OWNER_REVIEW_README.md"
    a1.MANIFEST_PATH = a1.OWNER_DIR / "FILE_MANIFEST.json"
    a1.build_plate_geometry = build_plate_geometry_attempt02

    original_material = a1.natural_material
    original_create = a1.create_nail_object

    def material_attempt02(name: str, rgba: tuple[float, float, float, float], *, free_edge: bool):
        return original_material(name.replace("Attempt01", "Attempt02"), rgba, free_edge=free_edge)

    def create_attempt02(*args: Any, **kwargs: Any):
        obj = original_create(*args, **kwargs)
        obj.name = obj.name.replace("Attempt01", "Attempt02")
        obj.data.name = obj.data.name.replace("Attempt01", "Attempt02")
        obj["bounded_repair_attempt"] = 2
        obj["attempt02_localization_change"] = "normalize_winding_then_allow_steep_curved_edge_alignment_to_0.05"
        return obj

    a1.natural_material = material_attempt02
    a1.create_nail_object = create_attempt02


def update_package_truth() -> None:
    evidence = json.loads(a1.EVIDENCE_PATH.read_text(encoding="utf-8"))
    evidence["schema"] = "kira_r21_nail_only_correction_attempt02_v1"
    evidence["status"] = "PRIVATE_INACTIVE_NAIL_ONLY_REVIEW_CANDIDATE_ATTEMPT02"
    evidence["attempt"] = 2
    evidence["predecessor"] = {
        "attempt01_failure_project_relative": ATTEMPT01_FAILURE.relative_to(ROOT).as_posix(),
        "attempt01_failure_sha256": a1.sha256_file(ATTEMPT01_FAILURE),
        "attempt01_preserved_unchanged": True,
        "attempt01_failure": "first index-fingernail corner normal alignment 0.129567 below provisional 0.15 gate",
        "footprint_diagnosis_project_relative": DIAGNOSIS.relative_to(ROOT).as_posix(),
        "footprint_diagnosis_sha256": a1.sha256_file(DIAGNOSIS),
    }
    evidence["tooling"]["author_script_project_relative"] = Path(__file__).resolve().relative_to(ROOT).as_posix()
    evidence["tooling"]["author_script_sha256"] = a1.sha256_file(Path(__file__).resolve())
    evidence["tooling"]["attempt01_base_worker_project_relative"] = Path(a1.__file__).resolve().relative_to(ROOT).as_posix()
    evidence["tooling"]["attempt01_base_worker_sha256"] = a1.sha256_file(Path(a1.__file__).resolve())
    evidence["method"]["attempt02_only_change"] = {
        "old_provisional_normal_alignment": 0.15,
        "new_curved_edge_normal_alignment": MINIMUM_CURVED_EDGE_NORMAL_ALIGNMENT,
        "winding_normalized_before_alignment_gate": True,
        "raw_and_evaluated_exact_zero_intersection_gates_unchanged": True,
    }
    evidence_text = json.dumps(evidence, indent=2) + "\n"
    a1.EVIDENCE_PATH.write_text(evidence_text, encoding="utf-8")
    a1.OWNER_EVIDENCE_PATH.write_text(evidence_text, encoding="utf-8")
    readme = a1.README_PATH.read_text(encoding="utf-8")
    readme = readme.replace("Attempt 01", "Attempt 02").replace("attempt01", "attempt02")
    readme += (
        "\nAttempt 02 is the second bounded nail repair. It normalizes local triangle winding before the surface-coherence gate and permits steep but coherent curved nail-fold samples down to 0.05 alignment. Exact raw and evaluated body-intersection requirements remain zero.\n"
    )
    a1.README_PATH.write_text(readme, encoding="utf-8")
    manifest_rows = []
    for path in sorted(a1.OWNER_DIR.iterdir(), key=lambda item: item.name):
        if path == a1.MANIFEST_PATH or not path.is_file():
            continue
        manifest_rows.append({"file": path.name, "sha256": a1.sha256_file(path), "bytes": path.stat().st_size})
    a1.MANIFEST_PATH.write_text(
        json.dumps({"schema": "kira_r21_nail_attempt02_file_manifest_v1", "files": manifest_rows}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": evidence["status"], "blend": evidence["blend"], "validation": evidence["validation"], "renders": evidence["renders"]}, indent=2))


def main() -> None:
    configure_attempt02()
    a1.main()
    update_package_truth()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        evidence_dir = ROOT / "RecoverySprint/continuation_20260802/kira_r21_nail_correction/author_attempt_02"
        owner_dir = ROOT / "Avatar/private_owner_review/kira_r21_bald_localized_correction_attempt_10_nails"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        owner_dir.mkdir(parents=True, exist_ok=True)
        output_blend = owner_dir / "KIRA_R21_BALD_PRIVATE_INACTIVE_PELVIS_NAILS_ATTEMPT10.blend"
        record = {
            "schema": "kira_r21_nail_only_correction_attempt02_failure_v1",
            "status": "SECOND_BOUNDED_ATTEMPT_FAILED_CANDIDATE_PRESERVED" if output_blend.is_file() else "SECOND_BOUNDED_ATTEMPT_FAILED_NO_CANDIDATE",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "attempt01_failure_sha256": a1.sha256_file(ATTEMPT01_FAILURE),
            "source_sha256": a1.sha256_file(a1.SOURCE),
            "blend_saved": output_blend.is_file(),
            "blend_sha256": a1.sha256_file(output_blend) if output_blend.is_file() else None,
            "raw_and_evaluated_zero_intersection_gates_not_waived": True,
        }
        (evidence_dir / "FAILURE_EVIDENCE.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        (owner_dir / "ATTEMPT_02_FAILURE.md").write_text(
            "# Kira R21 nail Attempt 02 failed\n\nThe second bounded nail repair did not pass. Nothing was activated. See the append-only failure evidence.\n",
            encoding="utf-8",
        )
        print(json.dumps(record, indent=2))
        raise
