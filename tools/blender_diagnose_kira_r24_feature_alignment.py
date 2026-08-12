"""Read-only alignment diagnostic for the failed R24 attempt_02.

The worker opens the sealed R19 source, enumerates every cyclic/reversed mapping
of the exact 102-vertex broad boundary onto the 28x25 rectangular perimeter,
and records centerline/fold metrics.  It does not mutate or save the mesh.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_simulate_kira_r24_feature_aligned_centerline_surface as r24


OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_feature_aligned_centerline_surface/attempt_02/"
    "BOUNDARY_ALIGNMENT_DIAGNOSTIC.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record(value: Vector) -> list[float]:
    return [round(float(component), 12) for component in value]


def evaluate_alignment(cycle: list[int], body: bpy.types.Object) -> dict[str, object]:
    boundary = {
        key: body.matrix_world @ body.data.vertices[index].co
        for key, index in zip(r24.PERIMETER_KEYS, cycle)
    }
    left = [boundary[(0, row)] for row in range(r24.GRID_HEIGHT)]
    right = [boundary[(r24.GRID_WIDTH - 1, row)] for row in range(r24.GRID_HEIGHT)]
    centers = [(first + second) * 0.5 for first, second in zip(left, right)]
    widths = [(second - first).length for first, second in zip(left, right)]
    normals: list[Vector] = []
    zero_frames = 0
    for row in range(r24.GRID_HEIGHT):
        tangent = (
            centers[min(r24.GRID_HEIGHT - 1, row + 1)]
            - centers[max(0, row - 1)]
        )
        across = right[row] - left[row]
        normal = across.cross(tangent)
        if normal.length < 1.0e-10:
            zero_frames += 1
            normal = Vector((0.0, 0.0, 1.0))
        else:
            normal.normalize()
        if normals and normal.dot(normals[-1]) < 0.0:
            normal.negate()
        normals.append(normal)
    adjacent_normal_dots = [
        normals[index].dot(normals[index + 1])
        for index in range(len(normals) - 1)
    ]
    center_steps = [
        (centers[index + 1] - centers[index]).length
        for index in range(len(centers) - 1)
    ]
    # A good centerline should advance consistently along the source's local
    # longitudinal chart rather than reversing repeatedly.
    center_v = [r24.r24_base.local_chart(value)[1] for value in centers]
    v_deltas = [center_v[index + 1] - center_v[index] for index in range(len(center_v) - 1)]
    nonzero_v = [value for value in v_deltas if abs(value) > 1.0e-8]
    dominant_sign = 1.0 if statistics.median(nonzero_v or [1.0]) >= 0.0 else -1.0
    v_reversals = sum(value * dominant_sign < -1.0e-5 for value in nonzero_v)
    # Penalize pairs whose connecting chord passes far from the two adjacent
    # row centers; this captures abrupt cross-pairing on concave boundaries.
    second_differences = [
        (centers[index + 1] - centers[index] * 2.0 + centers[index - 1]).length
        for index in range(1, len(centers) - 1)
    ]
    return {
        "zero_frame_count": zero_frames,
        "minimum_adjacent_normal_dot": min(adjacent_normal_dots, default=-1.0),
        "median_adjacent_normal_dot": statistics.median(adjacent_normal_dots),
        "maximum_centerline_step_m": max(center_steps, default=math.inf),
        "centerline_total_length_m": sum(center_steps),
        "maximum_centerline_second_difference_m": max(second_differences, default=math.inf),
        "longitudinal_reversal_count": v_reversals,
        "minimum_row_width_m": min(widths, default=0.0),
        "maximum_row_width_m": max(widths, default=math.inf),
        "maximum_to_median_row_width_ratio": max(widths, default=math.inf)
        / max(statistics.median(widths), 1.0e-12),
        "centerline_world": [record(value) for value in centers],
    }


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("append-only boundary diagnostic already exists")
    if sha256(r24.SOURCE) != r24.SOURCE_SHA256:
        raise RuntimeError("sealed R19 source drifted")
    bpy.ops.wm.open_mainfile(filepath=str(r24.SOURCE), load_ui=False)
    body = bpy.data.objects.get(r24.BODY_NAME)
    if body is None:
        raise RuntimeError("sealed R19 body absent")
    faces = r24.faces_of(body)
    patch = {
        int(polygon.index)
        for polygon in body.data.polygons
        if int(polygon.material_index) == r24.PATCH_MATERIAL_INDEX
    }
    adjacency = r24.topology_core.face_adjacency(faces)
    region = r24.topology_core.expand_face_rings(patch, adjacency, r24.EXTERIOR_FACE_RINGS)
    edges = r24.topology_core.boundary_edges_for_region(faces, region)
    cycles = r24.topology_core.ordered_boundary_cycles(edges)
    if len(cycles) != 1 or len(cycles[0]) != 102:
        raise RuntimeError("qualified 102-loop drifted")
    base = list(map(int, cycles[0]))
    candidates = []
    for reversed_order in (False, True):
        oriented = list(reversed(base)) if reversed_order else list(base)
        for shift in range(len(oriented)):
            aligned = oriented[shift:] + oriented[:shift]
            metrics = evaluate_alignment(aligned, body)
            score = (
                1000.0 * int(metrics["zero_frame_count"])
                + 25.0 * int(metrics["longitudinal_reversal_count"])
                + 120.0 * max(0.0, -float(metrics["minimum_adjacent_normal_dot"]))
                + 40.0 * float(metrics["maximum_centerline_second_difference_m"])
                + 20.0 * float(metrics["maximum_centerline_step_m"])
                + float(metrics["maximum_to_median_row_width_ratio"])
            )
            candidates.append(
                {
                    "reversed": reversed_order,
                    "shift": shift,
                    "score": score,
                    "corner_original_vertex_indices": [aligned[offset] for offset in (0, 27, 51, 78)],
                    "metrics": metrics,
                }
            )
    candidates.sort(key=lambda item: float(item["score"]))
    current, current_alignment = r24.choose_boundary_alignment(base, body)
    current_metrics = evaluate_alignment(current, body)
    report = {
        "schema": "kira.avatar.r24_feature_boundary_alignment_diagnostic.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "READ_ONLY_NO_MESH_MUTATION_NO_BLEND_SAVE",
        "source": r24.relative(r24.SOURCE),
        "source_sha256": sha256(r24.SOURCE),
        "current_mse_alignment": {
            **current_alignment,
            "metrics": current_metrics,
        },
        "best_centerline_candidates": candidates[:12],
        "candidate_count": len(candidates),
        "operations": {
            "mesh_mutated": False,
            "blend_saved": False,
            "runtime_or_person_state_changed": False,
        },
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(OUTPUT)}))


if __name__ == "__main__":
    main()
