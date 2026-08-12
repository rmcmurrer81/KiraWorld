"""No-save/no-render local-fill feasibility probe for R24 Attempt 15.

The probe starts from preserved BlackProject reconstruction Attempt 02,
removes only the smallest measured two-ring collision domain, fills that
domain against its exact 32-vertex local boundary, and runs the exact global
intersection audit.  It never writes a Blend or source asset.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector


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
    "r24_blackproject_patch_reconstruction_diagnostic/attempt_03"
)
ADULT_MESH_NAME = "Ariel_Mesh_Genitalia_0"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def vector_record(value: Vector) -> list[float]:
    return [round(float(component), 12) for component in value]


def world_area(obj: bpy.types.Object, face: bmesh.types.BMFace) -> float:
    points = [obj.matrix_world @ vertex.co for vertex in face.verts]
    if len(points) != 3:
        return 0.0
    return float((points[1] - points[0]).cross(points[2] - points[0]).length * 0.5)


def minimum_angle(obj: bpy.types.Object, face: bmesh.types.BMFace) -> float:
    points = [obj.matrix_world @ vertex.co for vertex in face.verts]
    if len(points) != 3:
        return 0.0
    values = []
    for index in range(3):
        first = points[(index + 1) % 3] - points[index]
        second = points[(index + 2) % 3] - points[index]
        if first.length == 0.0 or second.length == 0.0:
            return 0.0
        values.append(math.degrees(first.angle(second)))
    return min(values)


def main() -> None:
    if not SOURCE.is_file() or sha256_file(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("preserved Attempt 02 hash mismatch")
    if OUTPUT.exists():
        raise RuntimeError("append-only local-fill output already exists")
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
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.index_update()
    bm.faces.index_update()
    original_id = bm.verts.layers.int.new("attempt02_original_vertex_id")
    for vertex in bm.verts:
        vertex[original_id] = int(vertex.index)
    source_boundary_coordinates = {
        vertex: vertex.co.copy()
        for edge in bm.edges
        if len(edge.link_faces) == 1
        for vertex in edge.verts
    }
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
    local_boundary_edges = {edge for edge, count in edge_counts.items() if count == 1}
    local_boundary_vertices = {
        vertex for edge in local_boundary_edges for vertex in edge.verts
    }
    selected_vertices = {vertex for face in selected_faces for vertex in face.verts}
    removed_interior_vertices = selected_vertices - local_boundary_vertices
    local_boundary_keys = {
        tuple(sorted((int(edge.verts[0][original_id]), int(edge.verts[1][original_id]))))
        for edge in local_boundary_edges
    }
    topology_before = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
    }
    bmesh.ops.delete(bm, geom=selected_faces, context="FACES_KEEP_BOUNDARY")
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    isolated = [
        vertex
        for vertex in removed_interior_vertices
        if vertex.is_valid and not vertex.link_faces
    ]
    if isolated:
        bmesh.ops.delete(bm, geom=isolated, context="VERTS")
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    boundary_edges = [edge for edge in local_boundary_edges if edge.is_valid]
    if len(boundary_edges) != 32:
        raise RuntimeError(f"local boundary drifted before fill: {len(boundary_edges)}")
    fill = bmesh.ops.triangle_fill(bm, edges=boundary_edges, use_beauty=True)
    fill_faces = [value for value in fill.get("geom", []) if isinstance(value, bmesh.types.BMFace)]
    if not fill_faces:
        raise RuntimeError("triangle fill produced no faces")
    for face in fill_faces:
        face.material_index = 0
    bmesh.ops.recalc_face_normals(bm, faces=fill_faces)
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.index_update()
    bm.faces.index_update()
    after = exact_nonadjacent_intersection_report(bm, include_pair_details=True)
    boundary_delta = max(
        (
            (vertex.co - point).length
            for vertex, point in source_boundary_coordinates.items()
            if vertex.is_valid
        ),
        default=0.0,
    )
    new_areas = [world_area(obj, face) for face in fill_faces]
    new_angles = [minimum_angle(obj, face) for face in fill_faces]
    report = {
        "schema": "kira.avatar.r24.blackproject_attempt02_local_fill_probe.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "IN_MEMORY_ONLY_NO_RENDER_NO_SAVE",
        "input": {
            "path": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
            "sha256": SOURCE_SHA256,
        },
        "measured_domain": {
            "expansion_rings": 2,
            "removed_face_count": len(selected),
            "selected_vertex_count": len(selected_vertices),
            "removed_interior_vertex_count": len(removed_interior_vertices),
            "local_boundary_vertex_count": len(local_boundary_vertices),
            "local_boundary_edge_count": len(local_boundary_keys),
            "local_boundary_vertex_indices": sorted(
                int(vertex[original_id]) for vertex in local_boundary_vertices
            ),
            "local_boundary_edges": [list(value) for value in sorted(local_boundary_keys)],
        },
        "fill": {
            "method": "bmesh_triangle_fill_exact_local_boundary_use_beauty",
            "new_face_count": len(fill_faces),
            "topology_before": topology_before,
            "topology_after": {
                "vertices": len(bm.verts),
                "edges": len(bm.edges),
                "faces": len(bm.faces),
            },
            "minimum_new_triangle_world_area_m2": min(new_areas),
            "minimum_new_triangle_angle_degrees": min(new_angles),
            "maximum_global_34_seam_coordinate_delta_local_units": float(boundary_delta),
        },
        "exact_intersections": {
            "before_genuine_pair_count": before["exact_genuine_penetration_pair_count"],
            "after_genuine_pair_count": after["exact_genuine_penetration_pair_count"],
            "after_touch_count": after["touch_or_coplanar_false_positive_pair_count"],
            "after_aabb_false_positive_count": after["bvh_aabb_false_positive_pair_count"],
            "after_pairs": after["pairs"],
        },
        "truth": {
            "source_overwritten": False,
            "blend_saved": False,
            "rendered": False,
            "runtime_changed": False,
            "visually_natural_proven": False,
            "qualified_for_body_use": False,
        },
    }
    bm.free()
    OUTPUT.mkdir(parents=True)
    report_path = OUTPUT / "BLACKPROJECT_ATTEMPT02_LOCAL_FILL_PROBE.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if sha256_file(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("source changed during no-save probe")
    print(json.dumps({"report": str(report_path), "sha256": sha256_file(report_path)}))


if __name__ == "__main__":
    main()
