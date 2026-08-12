"""No-save/no-render scan of a topology-preserving local harmonic repair.

The measured 88-face two-ring collision domain is solved with an exact
Dirichlet uniform-Laplacian field while its 32-vertex local boundary stays
fixed.  Several bounded blend factors are audited for exact intersections and
triangle quality.  No source or Blend is written.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.blender_exact_mesh_intersections import (  # noqa: E402
    exact_nonadjacent_intersection_report,
)


SOURCE = ROOT / (
    "RecoverySprint/continuation_20260802/r19_blackproject_patch_reconstruction/"
    "attempt_02/r19_patch_reconstruction_probe.blend"
)
SOURCE_SHA256 = (
    "47cbf26279bc3b75076caf43f96c1c3441dd86e48ad0c404f7a45504985add4d"
)
OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260807/"
    "r24_blackproject_patch_reconstruction_diagnostic/attempt_04"
)
ADULT_MESH_NAME = "Ariel_Mesh_Genitalia_0"
BLEND_FACTORS = (0.25, 0.50, 0.75, 1.00)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def face_quality(obj: bpy.types.Object, face: bmesh.types.BMFace) -> tuple[float, float]:
    points = [obj.matrix_world @ vertex.co for vertex in face.verts]
    if len(points) != 3:
        return 0.0, 0.0
    area = float((points[1] - points[0]).cross(points[2] - points[0]).length * 0.5)
    angles = []
    for index in range(3):
        first = points[(index + 1) % 3] - points[index]
        second = points[(index + 2) % 3] - points[index]
        if first.length == 0.0 or second.length == 0.0:
            return area, 0.0
        angles.append(math.degrees(first.angle(second)))
    return area, min(angles)


def prepare() -> tuple[bpy.types.Object, bmesh.types.BMesh, dict]:
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    obj = next(
        (
            value
            for value in bpy.data.objects
            if value.type == "MESH" and value.data.name == ADULT_MESH_NAME
        ),
        None,
    )
    if obj is None:
        raise RuntimeError("Attempt 02 adult patch absent")
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.faces.index_update()
    before = exact_nonadjacent_intersection_report(bm, include_pair_details=True)
    seed = {
        int(value)
        for record in before["pairs"]
        if record["genuine_positive_area_or_segment_penetration"]
        for value in record["face_indices"]
    }
    selected = set(seed)
    for _ in range(2):
        selected.update(
            int(other.index)
            for face_index in list(selected)
            for edge in bm.faces[face_index].edges
            for other in edge.link_faces
        )
    selected_faces = [bm.faces[index] for index in sorted(selected)]
    edge_counts: dict[bmesh.types.BMEdge, int] = {}
    for face in selected_faces:
        for edge in face.edges:
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
    local_boundary = {
        vertex
        for edge, count in edge_counts.items()
        if count == 1
        for vertex in edge.verts
    }
    selected_vertices = {vertex for face in selected_faces for vertex in face.verts}
    interior = selected_vertices - local_boundary
    if len(selected_faces) != 88 or len(local_boundary) != 32 or len(interior) != 29:
        raise RuntimeError("measured Attempt 15 local domain drifted")
    return obj, bm, {
        "before": before,
        "selected_faces": selected_faces,
        "selected_vertices": selected_vertices,
        "boundary": local_boundary,
        "interior": interior,
    }


def solve_uniform_harmonic(domain: dict) -> dict[bmesh.types.BMVert, Vector]:
    interior = sorted(domain["interior"], key=lambda vertex: int(vertex.index))
    interior_index = {vertex: index for index, vertex in enumerate(interior)}
    matrix = np.zeros((len(interior), len(interior)), dtype=np.float64)
    rhs = np.zeros((len(interior), 3), dtype=np.float64)
    for vertex in interior:
        row = interior_index[vertex]
        neighbors = {
            edge.other_vert(vertex)
            for edge in vertex.link_edges
            if edge.other_vert(vertex) in domain["selected_vertices"]
        }
        matrix[row, row] = float(len(neighbors))
        for neighbor in neighbors:
            if neighbor in interior_index:
                matrix[row, interior_index[neighbor]] -= 1.0
            else:
                rhs[row] += np.array(tuple(neighbor.co), dtype=np.float64)
    coordinates = np.linalg.solve(matrix, rhs)
    residual = matrix @ coordinates - rhs
    return {
        "coordinates": {
            vertex: Vector(tuple(float(value) for value in coordinates[index]))
            for index, vertex in enumerate(interior)
        },
        "maximum_linear_residual_local_units": float(np.max(np.abs(residual))),
        "matrix_condition_number": float(np.linalg.cond(matrix)),
    }


def run_variant(factor: float) -> dict:
    obj, bm, domain = prepare()
    solved = solve_uniform_harmonic(domain)
    original = {vertex: vertex.co.copy() for vertex in domain["selected_vertices"]}
    for vertex, target in solved["coordinates"].items():
        vertex.co = original[vertex].lerp(target, float(factor))
    bm.normal_update()
    after = exact_nonadjacent_intersection_report(bm, include_pair_details=True)
    movement_world = [
        (obj.matrix_world.to_3x3() @ (vertex.co - original[vertex])).length
        for vertex in domain["interior"]
    ]
    qualities = [face_quality(obj, face) for face in domain["selected_faces"]]
    boundary_delta = max(
        ((vertex.co - original[vertex]).length for vertex in domain["boundary"]),
        default=0.0,
    )
    result = {
        "blend_factor": factor,
        "solver": {
            "method": "uniform_graph_laplacian_dirichlet_exact_local_boundary",
            "interior_vertex_count": len(domain["interior"]),
            "boundary_vertex_count": len(domain["boundary"]),
            "maximum_linear_residual_local_units": solved[
                "maximum_linear_residual_local_units"
            ],
            "matrix_condition_number": solved["matrix_condition_number"],
        },
        "maximum_interior_vertex_movement_world_m": max(movement_world),
        "rms_interior_vertex_movement_world_m": float(
            np.sqrt(np.mean(np.square(movement_world)))
        ),
        "minimum_domain_triangle_world_area_m2": min(value[0] for value in qualities),
        "minimum_domain_triangle_angle_degrees": min(value[1] for value in qualities),
        "global_34_seam_coordinate_delta_local_units": float(boundary_delta),
        "exact_genuine_pair_count": after["exact_genuine_penetration_pair_count"],
        "touch_pair_count": after["touch_or_coplanar_false_positive_pair_count"],
        "aabb_false_positive_pair_count": after["bvh_aabb_false_positive_pair_count"],
        "exact_pairs": after["pairs"],
    }
    bm.free()
    return result


def main() -> None:
    if not SOURCE.is_file() or sha256_file(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("preserved Attempt 02 hash mismatch")
    if OUTPUT.exists():
        raise RuntimeError("append-only harmonic scan output already exists")
    variants = [run_variant(value) for value in BLEND_FACTORS]
    zero = [row for row in variants if row["exact_genuine_pair_count"] == 0]
    selected = min(
        zero,
        key=lambda row: (
            row["maximum_interior_vertex_movement_world_m"],
            -row["minimum_domain_triangle_angle_degrees"],
        ),
        default=None,
    )
    report = {
        "schema": "kira.avatar.r24.blackproject_attempt02_local_harmonic_scan.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "IN_MEMORY_ONLY_NO_RENDER_NO_SAVE",
        "input": {
            "path": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
            "sha256": SOURCE_SHA256,
        },
        "variants": variants,
        "minimum_movement_zero_intersection_variant": selected,
        "truth": {
            "source_overwritten": False,
            "blend_saved": False,
            "rendered": False,
            "runtime_changed": False,
            "visual_acceptance_claimed": False,
        },
    }
    OUTPUT.mkdir(parents=True)
    report_path = OUTPUT / "BLACKPROJECT_ATTEMPT02_LOCAL_HARMONIC_SCAN.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if sha256_file(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("source changed during no-save scan")
    print(json.dumps({"report": str(report_path), "sha256": sha256_file(report_path)}))


if __name__ == "__main__":
    main()
