"""Read-only diagnosis of Attempt 01's first dorsal-footprint failure."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.blender_author_kira_r21_nails_attempt01 as a1


OUTPUT = ROOT / "RecoverySprint/continuation_20260802/kira_r21_nail_correction/preflight_02/FOOTPRINT_DIAGNOSIS.json"


def main() -> None:
    bpy.ops.wm.open_mainfile(filepath=str(a1.SOURCE))
    body = bpy.data.objects[a1.BODY_NAME]
    rig = bpy.data.objects[a1.RIG_NAME]
    source = bpy.data.objects["R19_BlackProject_fingernail_2_L_source_native"]
    definition = a1.source_definition(source, rig)
    _points, _triangles, tree = a1.body_geometry(body)
    center = definition["source_center_base"]
    normal = definition["source_normal_candidate_base"].copy()
    nearest, nearest_normal, _face, _distance = tree.find_nearest(center, 4.0)
    if normal.dot(nearest_normal) < 0:
        normal = -normal
    normal.normalize()
    length = definition["source_length_candidate_base"].copy()
    length = (length - normal * length.dot(normal)).normalized()
    bone = rig.data.bones[definition["bone"]]
    bone_direction = (bone.tail_local - bone.head_local).normalized()
    if length.dot(bone_direction) < 0:
        length = -length
    width = normal.cross(length).normalized()
    length = width.cross(normal).normalized()
    if length.dot(bone_direction) < 0:
        length = -length
        width = -width
    source_points = definition["source_points"]
    centered = source_points - tuple(center)
    source_length = float(((centered @ tuple(length)).max() - (centered @ tuple(length)).min()))
    source_width = float(((centered @ tuple(width)).max() - (centered @ tuple(width)).min()))
    rows = []
    for footprint_scale in (1.0, 0.94, 0.88, 0.82, 0.76):
        target_length = source_length * 0.70 * footprint_scale
        target_width = source_width * 0.88 * footprint_scale
        nominal_center = center - length * (source_length * 0.075)
        surface_center, _n, _f, _d = tree.ray_cast(nominal_center + normal * 3.0, -normal, 6.0)
        if surface_center is None:
            raise RuntimeError("center ray missed")
        minimum_alignment = 1.0
        mismatch_samples = []
        for row in range(a1.GRID_ROWS):
            u = -1.0 + 2.0 * row / (a1.GRID_ROWS - 1)
            row_width = target_width * 0.5 * a1.rounded_width_factor(u)
            for column in range(a1.GRID_COLUMNS):
                v = -1.0 + 2.0 * column / (a1.GRID_COLUMNS - 1)
                nominal = surface_center + length * (u * target_length * 0.5) + width * (v * row_width)
                hit, hit_normal, hit_face, hit_distance = tree.ray_cast(nominal + normal * 2.2, -normal, 4.4)
                method = "ray"
                if hit is None or hit_normal is None:
                    hit, hit_normal, hit_face, hit_distance = tree.find_nearest(nominal, 2.5)
                    method = "nearest"
                alignment = float(hit_normal.dot(normal)) if hit_normal is not None else -1.0
                minimum_alignment = min(minimum_alignment, alignment)
                if alignment < 0.15:
                    mismatch_samples.append({"row": row, "column": column, "alignment": alignment, "method": method, "face": int(hit_face), "distance": float(hit_distance)})
        rows.append({"footprint_scale": footprint_scale, "minimum_alignment": minimum_alignment, "mismatch_sample_count": len(mismatch_samples), "first_mismatch_samples": mismatch_samples[:12]})
    record = {
        "schema": "kira_r21_nail_attempt02_footprint_diagnosis_v1",
        "source_sha256": a1.sha256_file(a1.SOURCE),
        "source_object": source.name,
        "bone": definition["bone"],
        "source_length_base_units": source_length,
        "source_width_base_units": source_width,
        "tests": rows,
        "read_only": True,
        "blend_saved": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
