"""No-save R24 direct-subdivision repair of the exact embedded R19 patch.

This bounded worker does not construct another body or remap the pelvis to a
rectangular sweep.  It opens the exact sealed R19 body, preserves its embedded
34-edge adult-region seam, subdivides only edges wholly internal to the
existing 376-face patch by adding one face-local centroid per triangle, and
applies small analytic feature offsets along each
refined vertex's interpolated local surface normal.  The surrounding surface,
seam vertices, native rig, and source file are frozen.

The three opening landmarks are shallow capped surface recesses only.  No
through tract or internal urinary, vaginal, reproductive, rectal, pelvic-floor,
continence, elimination, pregnancy, sensation, or subjective system is
created or claimed.  This worker renders private diagnostic evidence and never
saves a Blend.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any, Iterable, Mapping, Sequence

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_exact_mesh_intersections as exact_intersections  # noqa: E402
from tools import blender_simulate_kira_r24_broad_inplace_surface as r24_base  # noqa: E402
from tools import blender_simulate_kira_r24_feature_aligned_centerline_surface as r24_render  # noqa: E402
from tools import blender_author_kira_r23_cc0_afes_attempt01 as r23_author  # noqa: E402
from tools import kira_r23_cc0_afes_preflight_core as topology_core  # noqa: E402


SOURCE = r24_base.SOURCE
SOURCE_SHA256 = r24_base.SOURCE_SHA256
BODY_NAME = r24_base.BODY_NAME
RIG_NAME = r24_base.RIG_NAME
PATCH_MATERIAL_INDEX = r24_base.PATCH_MATERIAL_INDEX

OUTPUT_ROOT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_direct_subdivision_surface"
)
BOUND_R19_EVIDENCE = ROOT / (
    "RecoverySprint/continuation_20260802/"
    "r19_blackproject_regular_cdt_patch/attempt_05/BUILD_EVIDENCE.json"
)
BOUND_R19_EVIDENCE_SHA256 = (
    "479b01d09f9754b4479774d0046d205bd22378a28ed57161986d576748dfa7c5"
)

EXPECTED_PATCH_FACES = 376
EXPECTED_PATCH_VERTICES = 206
EXPECTED_BOUNDARY_VERTICES = 34
EXPECTED_BOUNDARY_EDGES = 34
MAXIMUM_OFFSET_M = 0.0030
MAXIMUM_SEAM_SUPPORT_FAIRING_M = 0.0080
MAXIMUM_SECOND_RING_FAIRING_M = 0.0040
FAIRING_SAFETY_EPSILON_M = 1.0e-7
FAIRING_GATE_EPSILON_M = 1.0e-8
ATTEMPT_07_WORKER_SHA256 = (
    "533de20d50190004273f6cbb2d88532a75655277566d4f3870843b7bbf4470cc"
)
ATTEMPT_06_MAXIMUM_PATCH_EDGE_RATIO = 4.627353133511013
ATTEMPT_06_WHOLE_GENUINE_INTERSECTION_COUNT = 29
TARGETED_SEAM_DOT = 0.715
TARGETED_SEAM_SOLVER_DOT = 0.71505
TARGETED_SUPPORT_CAP_M = 0.00125
TARGETED_BOUNDARY_EDGE_IDS = {
    (1096, 1097),
    (1097, 1529),
    (2481, 2482),
    (2481, 2861),
}

FEATURE_CODES = {
    "base": 1,
    "mons": 2,
    "labia_majora_left": 3,
    "labia_majora_right": 4,
    "labia_minora_left": 5,
    "labia_minora_right": 6,
    "vestibule": 7,
    "clitoral_hood_glans": 8,
    "urethral_meatus": 9,
    "vaginal_introitus": 10,
    "posterior_fourchette": 11,
    "external_perineum": 12,
    "anal_verge": 13,
}

OPENING_SPECS = {
    "urethral_meatus": {
        "u": 0.0,
        "t": 0.39,
        "su": 0.055,
        "st": 0.045,
        "rim_height_m": 0.00034,
        "cap_depth_m": 0.00042,
    },
    "vaginal_introitus": {
        "u": 0.0,
        "t": 0.55,
        "su": 0.105,
        "st": 0.090,
        "rim_height_m": 0.00058,
        "cap_depth_m": 0.00110,
    },
    "anal_verge": {
        "u": 0.0,
        "t": 0.88,
        "su": 0.090,
        "st": 0.060,
        "rim_height_m": 0.00042,
        "cap_depth_m": 0.00072,
    },
}

ACTIVE_OUTPUT: Path | None = None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def vector_record(value: Vector) -> list[float]:
    return [round(float(component), 12) for component in value]


def allocate_output() -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for number in range(1, 100):
        candidate = OUTPUT_ROOT / f"attempt_{number:02d}"
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError("no append-only direct-subdivision attempt slot remains")


def faces_of(body: bpy.types.Object) -> list[tuple[int, ...]]:
    return [tuple(map(int, polygon.vertices)) for polygon in body.data.polygons]


def edge_key(first: int, second: int) -> tuple[int, int]:
    return (first, second) if first < second else (second, first)


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, float(value)))
    return value * value * (3.0 - 2.0 * value)


def gaussian(value: float, center: float, width: float) -> float:
    return math.exp(-0.5 * ((float(value) - center) / max(width, 1.0e-12)) ** 2)


def gaussian2(
    u: float,
    t: float,
    center_u: float,
    center_t: float,
    width_u: float,
    width_t: float,
) -> float:
    return gaussian(u, center_u, width_u) * gaussian(t, center_t, width_t)


def elliptical_radius(
    u: float,
    t: float,
    center_u: float,
    center_t: float,
    scale_u: float,
    scale_t: float,
) -> float:
    return math.sqrt(
        ((u - center_u) / max(scale_u, 1.0e-12)) ** 2
        + ((t - center_t) / max(scale_t, 1.0e-12)) ** 2
    )


def ring_value(radius: float, center: float = 1.0, width: float = 0.24) -> float:
    return math.exp(-0.5 * ((float(radius) - center) / width) ** 2)


def original_patch_preflight(body: bpy.types.Object) -> dict[str, Any]:
    faces = faces_of(body)
    patch_faces = {
        int(polygon.index)
        for polygon in body.data.polygons
        if int(polygon.material_index) == PATCH_MATERIAL_INDEX
    }
    if len(patch_faces) != EXPECTED_PATCH_FACES:
        raise RuntimeError(f"R19 patch face count drifted: {len(patch_faces)}")
    topology = topology_core.topology_record(faces, patch_faces)
    boundary_edges = topology_core.boundary_edges_for_region(faces, patch_faces)
    cycles = topology_core.ordered_boundary_cycles(boundary_edges)
    patch_vertices = {
        int(vertex) for face_index in patch_faces for vertex in faces[face_index]
    }
    boundary_vertices = {int(vertex) for edge in boundary_edges for vertex in edge}
    interior_vertices = patch_vertices.difference(boundary_vertices)
    if len(patch_vertices) != EXPECTED_PATCH_VERTICES:
        raise RuntimeError(f"R19 patch vertex count drifted: {len(patch_vertices)}")
    if topology["component_count"] != 1 or topology["is_one_disk"] is not True:
        raise RuntimeError("R19 patch is no longer one manifold disk")
    if len(boundary_edges) != EXPECTED_BOUNDARY_EDGES:
        raise RuntimeError("R19 patch boundary-edge count drifted")
    if len(cycles) != 1 or len(cycles[0]) != EXPECTED_BOUNDARY_VERTICES:
        raise RuntimeError("R19 patch no longer has its exact 34-vertex boundary")
    boundary_positions = [
        vector_record(body.matrix_world @ body.data.vertices[index].co)
        for index in sorted(boundary_vertices)
    ]
    return {
        "faces": faces,
        "patch_faces": patch_faces,
        "patch_vertices": patch_vertices,
        "boundary_edges": {edge_key(*map(int, edge)) for edge in boundary_edges},
        "boundary_cycle": list(map(int, cycles[0])),
        "boundary_vertices": boundary_vertices,
        "interior_vertices": interior_vertices,
        "topology": topology,
        "boundary_position_sha256": canonical_sha256(boundary_positions),
        "boundary_edge_sha256": canonical_sha256(
            [list(edge) for edge in sorted(boundary_edges)]
        ),
    }


def graph_distance_from_seam(
    patch_vertices: set[bmesh.types.BMVert],
    patch_edges: Sequence[bmesh.types.BMEdge],
    seam_vertices: set[bmesh.types.BMVert],
) -> dict[bmesh.types.BMVert, int]:
    neighbors: dict[bmesh.types.BMVert, set[bmesh.types.BMVert]] = defaultdict(set)
    for edge in patch_edges:
        first, second = edge.verts
        if first in patch_vertices and second in patch_vertices:
            neighbors[first].add(second)
            neighbors[second].add(first)
    distances = {vertex: 0 for vertex in seam_vertices}
    queue = deque(sorted(seam_vertices, key=lambda item: item.index))
    while queue:
        current = queue.popleft()
        for neighbor in neighbors[current]:
            if neighbor in distances:
                continue
            distances[neighbor] = distances[current] + 1
            queue.append(neighbor)
    if set(distances) != patch_vertices:
        raise RuntimeError("refined R19 patch is not connected to its seam")
    return distances


def nearest_centerline_parameter(
    point: Vector,
    controls: Sequence[Vector],
    cumulative: Sequence[float],
) -> tuple[float, float]:
    best: tuple[float, float] | None = None
    total = float(cumulative[-1])
    for index in range(len(controls) - 1):
        first, second = controls[index], controls[index + 1]
        segment = second - first
        denominator = max(segment.length_squared, 1.0e-18)
        alpha = max(0.0, min(1.0, (point - first).dot(segment) / denominator))
        closest = first + segment * alpha
        separation = (point - closest).length
        path = cumulative[index] + alpha * (cumulative[index + 1] - cumulative[index])
        candidate = (float(separation), float(path / total))
        if best is None or candidate < best:
            best = candidate
    if best is None:
        raise RuntimeError("3D source centerline has no segment")
    return best


def direct_source_3d_parameters(
    patch_vertices: set[bmesh.types.BMVert],
    base_world: Mapping[bmesh.types.BMVert, Vector],
) -> tuple[dict[bmesh.types.BMVert, tuple[float, float]], dict[str, Any]]:
    """Derive coordinates only; never remap a source-surface position."""
    raw = {
        vertex: r24_base.local_chart(base_world[vertex])[:2]
        for vertex in patch_vertices
    }
    maximum_absolute_u = max(abs(float(value[0])) for value in raw.values())
    v_min = min(float(value[1]) for value in raw.values())
    v_max = max(float(value[1]) for value in raw.values())
    if maximum_absolute_u <= 1.0e-12 or v_max - v_min <= 1.0e-12:
        raise RuntimeError("exact-source 3D parameter preprojection collapsed")
    normalized_u = {
        vertex: float(raw[vertex][0]) / maximum_absolute_u for vertex in patch_vertices
    }
    projection_t = {
        vertex: (v_max - float(raw[vertex][1])) / (v_max - v_min)
        for vertex in patch_vertices
    }
    anchors = [index / 12.0 for index in range(13)]
    controls: list[Vector] = []
    control_records = []
    for anchor in anchors:
        selected = [
            vertex
            for vertex in patch_vertices
            if abs(projection_t[vertex] - anchor) <= 0.16
            and abs(normalized_u[vertex]) <= 0.40
        ]
        weights = [
            math.exp(-0.5 * ((projection_t[vertex] - anchor) / 0.060) ** 2)
            * math.exp(-0.5 * (normalized_u[vertex] / 0.20) ** 2)
            for vertex in selected
        ]
        total = sum(weights)
        if total <= 1.0e-12:
            raise RuntimeError(f"3D centerline control {anchor:.6f} has no support")
        control = sum(
            (base_world[vertex] * weight for vertex, weight in zip(selected, weights)),
            Vector(),
        ) / total
        controls.append(control)
        control_records.append(
            {
                "initial_projection_t": anchor,
                "support_vertex_count": len(selected),
                "world": vector_record(control),
            }
        )
    cumulative = [0.0]
    for first, second in zip(controls, controls[1:]):
        cumulative.append(cumulative[-1] + (second - first).length)
    if cumulative[-1] < 0.090:
        raise RuntimeError("exact-source 3D centerline arc is shorter than 90 mm")
    parameters = {}
    maximum_distance = 0.0
    for vertex in patch_vertices:
        separation, arc_t = nearest_centerline_parameter(
            base_world[vertex], controls, cumulative
        )
        maximum_distance = max(maximum_distance, separation)
        parameters[vertex] = (normalized_u[vertex], arc_t)
    return parameters, {
        "id": "EXACT_SOURCE_PATCH_3D_CENTERLINE_ARC_V1",
        "initial_projection": "existing 3D LONGITUDINAL axis combining world Y and Z",
        "control_count": len(controls),
        "controls": control_records,
        "arc_length_m": float(cumulative[-1]),
        "maximum_vertex_to_centerline_distance_m": float(maximum_distance),
        "surface_positions_remapped": False,
        "donor_used": False,
    }


def world_face_normal(body: bpy.types.Object, face: bmesh.types.BMFace) -> Vector:
    normal = body.matrix_world.to_3x3().inverted().transposed() @ face.normal
    if normal.length <= 1.0e-12:
        raise RuntimeError("seam audit encountered a zero face normal")
    normal.normalize()
    return normal


def material_name(body: bpy.types.Object, material_index: int) -> str | None:
    if material_index < 0 or material_index >= len(body.data.materials):
        return None
    material = body.data.materials[material_index]
    return material.name if material is not None else None


def mesh_shading_state(body: bpy.types.Object) -> dict[str, Any]:
    mesh = body.data
    normal_attributes = []
    for attribute in mesh.attributes:
        if "normal" in attribute.name.lower():
            normal_attributes.append(
                {
                    "name": attribute.name,
                    "domain": attribute.domain,
                    "data_type": attribute.data_type,
                }
            )
    normal_modifier_types = {"NORMAL_EDIT", "WEIGHTED_NORMAL"}
    return {
        "has_custom_split_normals": bool(getattr(mesh, "has_custom_normals", False)),
        "normal_named_attributes": normal_attributes,
        "normal_related_modifiers": [
            {"name": modifier.name, "type": modifier.type}
            for modifier in body.modifiers
            if modifier.type in normal_modifier_types
        ],
        "all_modifiers": [
            {"name": modifier.name, "type": modifier.type}
            for modifier in body.modifiers
        ],
    }


def mesh_boundary_corner_normal_audit(
    body: bpy.types.Object,
    patch_face_indices: Iterable[int],
    boundary_edges: Iterable[tuple[int, int]],
) -> dict[str, Any]:
    mesh = body.data
    patch_faces = set(map(int, patch_face_indices))
    faces = faces_of(body)
    edge_faces = topology_core.edge_face_map(faces)
    corner_normals = mesh.corner_normals
    records = []
    for edge in sorted(edge_key(*map(int, value)) for value in boundary_edges):
        linked = list(map(int, edge_faces.get(edge, ())))
        if len(linked) != 2:
            records.append(
                {
                    "boundary_vertex_ids": list(edge),
                    "error": f"expected two linked faces, found {len(linked)}",
                }
            )
            continue
        patch_candidates = [index for index in linked if index in patch_faces]
        outside_candidates = [index for index in linked if index not in patch_faces]
        if len(patch_candidates) != 1 or len(outside_candidates) != 1:
            records.append(
                {
                    "boundary_vertex_ids": list(edge),
                    "error": "could not identify one patch and one outside face",
                }
            )
            continue
        patch_index = patch_candidates[0]
        outside_index = outside_candidates[0]
        vertex_records = []
        for vertex_index in edge:
            normals = []
            for face_index in (patch_index, outside_index):
                polygon = mesh.polygons[face_index]
                loop_index = next(
                    index
                    for index in polygon.loop_indices
                    if int(mesh.loops[index].vertex_index) == int(vertex_index)
                )
                normal = Vector(corner_normals[loop_index].vector)
                if normal.length > 1.0e-12:
                    normal.normalize()
                normals.append(normal)
            dot = max(-1.0, min(1.0, float(normals[0].dot(normals[1]))))
            vertex_records.append(
                {
                    "vertex_index": int(vertex_index),
                    "patch_vs_outside_corner_normal_dot": dot,
                    "split_normal_discontinuity_below_0_999": dot < 0.999,
                }
            )
        records.append(
            {
                "boundary_vertex_ids": list(edge),
                "patch_face_index": patch_index,
                "outside_face_index": outside_index,
                "vertices": vertex_records,
                "minimum_corner_normal_dot": min(
                    record["patch_vs_outside_corner_normal_dot"]
                    for record in vertex_records
                ),
            }
        )
    valid_records = [record for record in records if "error" not in record]
    all_vertex_records = [
        vertex_record
        for record in valid_records
        for vertex_record in record["vertices"]
    ]
    return {
        "boundary_edge_count": len(records),
        "error_count": sum(1 for record in records if "error" in record),
        "minimum_corner_normal_dot": min(
            (
                record["patch_vs_outside_corner_normal_dot"]
                for record in all_vertex_records
            ),
            default=1.0,
        ),
        "split_normal_discontinuity_vertex_count_below_0_999": sum(
            1
            for record in all_vertex_records
            if record["split_normal_discontinuity_below_0_999"]
        ),
        "records": records,
    }


def clear_exact_boundary_custom_normal_discontinuity(
    body: bpy.types.Object,
    audit: Mapping[str, Any],
) -> dict[str, Any]:
    mesh = body.data
    if not bool(getattr(mesh, "has_custom_normals", False)):
        return {"applied": False, "reason": "no custom split normals present", "changes": []}
    discontinuities = [
        (record, vertex_record)
        for record in audit["records"]
        if "error" not in record
        for vertex_record in record["vertices"]
        if vertex_record["split_normal_discontinuity_below_0_999"]
    ]
    if not discontinuities:
        return {
            "applied": False,
            "reason": "custom split normals present but no exact-boundary discontinuity",
            "changes": [],
        }
    if not hasattr(mesh, "normals_split_custom_set"):
        raise RuntimeError(
            "exact boundary custom-normal discontinuity exists but this Blender build "
            "does not expose normals_split_custom_set"
        )
    normals = [Vector(value.vector) for value in mesh.corner_normals]
    changes = []
    for record, vertex_record in discontinuities:
        vertex_index = int(vertex_record["vertex_index"])
        loop_indices = []
        for face_index in (record["patch_face_index"], record["outside_face_index"]):
            polygon = mesh.polygons[int(face_index)]
            loop_indices.append(
                next(
                    index
                    for index in polygon.loop_indices
                    if int(mesh.loops[index].vertex_index) == vertex_index
                )
            )
        average = normals[loop_indices[0]] + normals[loop_indices[1]]
        if average.length <= 1.0e-12:
            raise RuntimeError("exact boundary custom-normal average collapsed")
        average.normalize()
        changes.append(
            {
                "boundary_vertex_ids": record["boundary_vertex_ids"],
                "vertex_index": vertex_index,
                "loop_indices": list(map(int, loop_indices)),
                "before_dot": float(
                    normals[loop_indices[0]].normalized().dot(
                        normals[loop_indices[1]].normalized()
                    )
                ),
                "replacement_normal": vector_record(average),
            }
        )
        normals[loop_indices[0]] = average.copy()
        normals[loop_indices[1]] = average.copy()
    mesh.normals_split_custom_set([tuple(map(float, normal)) for normal in normals])
    mesh.update()
    return {
        "applied": True,
        "reason": "cleared only proven exact-boundary custom split-normal pairs",
        "changes": changes,
    }


def seam_edge_records(
    body: bpy.types.Object,
    patch_faces: set[bmesh.types.BMFace],
    seam_edges: set[bmesh.types.BMEdge],
    original_vertex_ids: Mapping[bmesh.types.BMVert, int],
    parameters: Mapping[bmesh.types.BMVert, tuple[float, float]],
) -> dict[str, Any]:
    records = []
    for edge in sorted(
        seam_edges,
        key=lambda item: tuple(sorted(int(original_vertex_ids[vertex]) for vertex in item.verts)),
    ):
        patch_face = next(face for face in edge.link_faces if face in patch_faces)
        outside_face = next(face for face in edge.link_faces if face not in patch_faces)
        endpoints = sorted(
            (
                (int(original_vertex_ids[vertex]), body.matrix_world @ vertex.co)
                for vertex in edge.verts
            ),
            key=lambda item: item[0],
        )
        midpoint = (endpoints[0][1] + endpoints[1][1]) * 0.5
        patch_normal = world_face_normal(body, patch_face)
        outside_normal = world_face_normal(body, outside_face)
        normal_dot = max(-1.0, min(1.0, float(patch_normal.dot(outside_normal))))
        patch_material_name = material_name(body, int(patch_face.material_index))
        outside_material_name = material_name(body, int(outside_face.material_index))
        mean_u = statistics.mean(parameters[vertex][0] for vertex in edge.verts)
        mean_t = statistics.mean(parameters[vertex][1] for vertex in edge.verts)
        records.append(
            {
                "edge_index_before_final_reindex": int(edge.index),
                "boundary_vertex_ids": [endpoints[0][0], endpoints[1][0]],
                "endpoint_world_m": [
                    vector_record(endpoints[0][1]),
                    vector_record(endpoints[1][1]),
                ],
                "midpoint_world_m": vector_record(midpoint),
                "mean_lateral_u": float(mean_u),
                "mean_anatomical_t": float(mean_t),
                "normal_dot": normal_dot,
                "dihedral_degrees": math.degrees(math.acos(normal_dot)),
                "below_0_70": normal_dot < 0.70,
                "edge_smooth": bool(edge.smooth),
                "edge_sharp": not bool(edge.smooth),
                "patch_face_smooth": bool(patch_face.smooth),
                "outside_face_smooth": bool(outside_face.smooth),
                "patch_material_index": int(patch_face.material_index),
                "outside_material_index": int(outside_face.material_index),
                "patch_material_name": patch_material_name,
                "outside_material_name": outside_material_name,
                "same_material_index": int(patch_face.material_index)
                == int(outside_face.material_index),
                "same_material_name": patch_material_name == outside_material_name,
            }
        )
    return {
        "edge_count": len(records),
        "sharp_edge_count": sum(1 for record in records if record["edge_sharp"]),
        "patch_flat_face_count": sum(
            1 for record in records if not record["patch_face_smooth"]
        ),
        "outside_flat_face_count": sum(
            1 for record in records if not record["outside_face_smooth"]
        ),
        "material_index_discontinuity_count": sum(
            1 for record in records if not record["same_material_index"]
        ),
        "material_name_discontinuity_count": sum(
            1 for record in records if not record["same_material_name"]
        ),
        "below_0_70": [record for record in records if record["below_0_70"]],
        "records": records,
    }


def point_segment_distance(point: Vector, first: Vector, second: Vector) -> float:
    segment = second - first
    if segment.length_squared <= 1.0e-18:
        return float((point - first).length)
    alpha = max(0.0, min(1.0, float((point - first).dot(segment) / segment.length_squared)))
    return float((point - (first + segment * alpha)).length)


def boundary_tangent_plane_fairing(
    body: bpy.types.Object,
    patch_faces: set[bmesh.types.BMFace],
    patch_edges: Sequence[bmesh.types.BMEdge],
    seam_edges: set[bmesh.types.BMEdge],
    seam_vertices: set[bmesh.types.BMVert],
    distances: Mapping[bmesh.types.BMVert, int],
    original_vertex_ids: Mapping[bmesh.types.BMVert, int],
) -> dict[str, Any]:
    """Move only four proven low-dot seam child centroids to dot 0.715."""
    matrix_world = body.matrix_world.copy()
    matrix_world_inverse = matrix_world.inverted()
    fairing_baseline_world = {
        vertex: matrix_world @ vertex.co for vertex in distances
    }
    movement_records = []
    mutated_vertices: set[bmesh.types.BMVert] = set()
    found_edges = set()
    for edge in sorted(
        seam_edges,
        key=lambda item: tuple(
            sorted(int(original_vertex_ids[vertex]) for vertex in item.verts)
        ),
    ):
        edge_ids = tuple(
            sorted(int(original_vertex_ids[vertex]) for vertex in edge.verts)
        )
        if edge_ids not in TARGETED_BOUNDARY_EDGE_IDS:
            continue
        found_edges.add(edge_ids)
        patch_face = next(face for face in edge.link_faces if face in patch_faces)
        outside_face = next(face for face in edge.link_faces if face not in patch_faces)
        support_vertices = [vertex for vertex in patch_face.verts if vertex not in edge.verts]
        if len(support_vertices) != 1:
            raise RuntimeError("seam patch face is not a triangle with one support centroid")
        support = support_vertices[0]
        if int(distances[support]) != 1:
            raise RuntimeError("targeted seam child support is not in exact graph ring 1")
        if support in mutated_vertices:
            raise RuntimeError("one targeted seam child support serves multiple boundary edges")
        first, second = edge.verts
        first_world = matrix_world @ first.co
        second_world = matrix_world @ second.co
        support_world = matrix_world @ support.co
        outside_normal = world_face_normal(body, outside_face)
        if (second_world - first_world).length <= 1.0e-12:
            raise RuntimeError("zero-length exact world-space seam edge")
        projected_world = support_world - outside_normal * (
            (support_world - first_world).dot(outside_normal)
        )
        full_projection = projected_world - support_world

        def candidate_dot(alpha: float) -> float:
            candidate_world = support_world + full_projection * float(alpha)
            positions = [
                candidate_world if vertex is support else matrix_world @ vertex.co
                for vertex in patch_face.verts
            ]
            normal = (positions[1] - positions[0]).cross(positions[2] - positions[0])
            if normal.length <= 1.0e-12:
                raise RuntimeError("targeted seam child candidate face collapsed")
            normal.normalize()
            return max(-1.0, min(1.0, float(normal.dot(outside_normal))))

        baseline_dot = candidate_dot(0.0)
        full_projection_dot = candidate_dot(1.0)
        if baseline_dot >= TARGETED_SEAM_SOLVER_DOT:
            alpha = 0.0
        else:
            if full_projection_dot < TARGETED_SEAM_SOLVER_DOT:
                raise RuntimeError(
                    f"targeted edge {edge_ids} cannot reach the bounded seam-dot target"
                )
            lower = 0.0
            upper = 1.0
            for _iteration in range(64):
                middle = (lower + upper) * 0.5
                if candidate_dot(middle) >= TARGETED_SEAM_SOLVER_DOT:
                    upper = middle
                else:
                    lower = middle
            alpha = upper
        requested = full_projection * alpha
        requested_length = float(requested.length)
        safe_cap = max(0.0, TARGETED_SUPPORT_CAP_M - FAIRING_SAFETY_EPSILON_M)
        if requested_length > safe_cap and requested_length > 1.0e-18:
            intended = requested.normalized() * safe_cap
            clamped = True
        else:
            intended = requested
            clamped = False
        support.co = matrix_world_inverse @ (support_world + intended)
        actual_world = matrix_world @ support.co - support_world
        if actual_world.length > safe_cap + 1.0e-12 and actual_world.length > 1.0e-18:
            corrected = actual_world * (safe_cap / actual_world.length) * (1.0 - 1.0e-6)
            support.co = matrix_world_inverse @ (support_world + corrected)
            actual_world = matrix_world @ support.co - support_world
        achieved_dot = candidate_dot(
            float(actual_world.length / full_projection.length)
            if full_projection.length > 1.0e-18
            else 0.0
        )
        mutated_vertices.add(support)
        movement_records.append(
            {
                "boundary_vertex_ids": list(edge_ids),
                "support_vertex_index_before_final_reindex": int(support.index),
                "ring": 1,
                "baseline_dot": baseline_dot,
                "solver_target_dot": TARGETED_SEAM_SOLVER_DOT,
                "acceptance_target_dot": TARGETED_SEAM_DOT,
                "full_projection_dot": full_projection_dot,
                "full_projection_world_m": float(full_projection.length),
                "minimum_bisection_alpha": float(alpha),
                "requested_world_m": requested_length,
                "applied_world_m": float(actual_world.length),
                "cap_world_m": TARGETED_SUPPORT_CAP_M,
                "clamped": clamped,
                "achieved_dot_from_measured_world_delta": achieved_dot,
            }
        )
    if found_edges != TARGETED_BOUNDARY_EDGE_IDS:
        raise RuntimeError(
            "targeted seam-edge set drifted: "
            f"found={sorted(found_edges)}, expected={sorted(TARGETED_BOUNDARY_EDGE_IDS)}"
        )
    unexpected_fairing_movements = [
        {
            "vertex_index_before_final_reindex": int(vertex.index),
            "world_m": float((matrix_world @ vertex.co - baseline).length),
        }
        for vertex, baseline in fairing_baseline_world.items()
        if vertex not in mutated_vertices
        and (matrix_world @ vertex.co - baseline).length > 1.0e-10
    ]
    if unexpected_fairing_movements:
        raise RuntimeError("Attempt 08 moved a non-targeted fairing vertex")
    requested_values = [float(record["requested_world_m"]) for record in movement_records]
    applied_values = [float(record["applied_world_m"]) for record in movement_records]
    return {
        "method": "FOUR_LOW_DOT_SEAM_CHILD_MINIMUM_WORLD_PROJECTION_V1",
        "object_matrix_world": [list(map(float, row)) for row in matrix_world],
        "targeted_boundary_edge_ids": [list(value) for value in sorted(found_edges)],
        "targeted_support_vertex_count": len(mutated_vertices),
        "ring_1_vertex_count": len(mutated_vertices),
        "ring_2_vertex_count": 0,
        "maximum_requested_support_movement_m": max(requested_values, default=0.0),
        "mean_requested_support_movement_m": (
            statistics.mean(requested_values) if requested_values else 0.0
        ),
        "requested_support_movement_distribution_m": sorted(requested_values),
        "maximum_support_movement_m": max(applied_values, default=0.0),
        "mean_support_movement_m": (
            statistics.mean(applied_values) if applied_values else 0.0
        ),
        "applied_support_movement_distribution_m": sorted(applied_values),
        "ring_1_requested_world_m": sorted(requested_values),
        "ring_1_applied_world_m": sorted(applied_values),
        "ring_2_requested_world_m": [],
        "ring_2_applied_world_m": [],
        "maximum_ring_1_applied_world_m": max(applied_values, default=0.0),
        "maximum_ring_2_applied_world_m": 0.0,
        "clamped_support_count": sum(1 for record in movement_records if record["clamped"]),
        "movement_records": movement_records,
        "ring_1_cap_m": TARGETED_SUPPORT_CAP_M,
        "ring_2_cap_m": 0.0,
        "safety_epsilon_m": FAIRING_SAFETY_EPSILON_M,
        "gate_epsilon_m": FAIRING_GATE_EPSILON_M,
        "sharp_boundary_edges_cleared": [],
        "all_other_fairing_displacement_zero": not unexpected_fairing_movements,
        "unexpected_fairing_movements": unexpected_fairing_movements,
        "seam_vertices_moved": 0,
        "outside_vertices_or_faces_moved": 0,
        "ring_3_plus_moved_by_fairing": 0,
    }


def feature_offset_and_tags(u: float, t: float) -> tuple[float, set[str]]:
    """Return a bounded local-normal offset and semantic surface tags."""
    tags: set[str] = set()
    value = 0.0

    # A shallow presentation term brings the existing concave source surface
    # into readable relief without flattening or remapping it.
    value += 0.00062 * gaussian2(u, t, 0.0, 0.48, 0.52, 0.34)

    mons = 0.00118 * gaussian2(u, t, 0.0, 0.16, 0.48, 0.16)
    value += mons
    if mons > 0.00016:
        tags.add("mons")

    left_major = 0.00255 * gaussian2(u, t, -0.31, 0.46, 0.15, 0.25)
    right_major = 0.00242 * gaussian2(u, t, 0.32, 0.46, 0.15, 0.25)
    value += left_major + right_major
    if left_major > 0.00022:
        tags.add("labia_majora_left")
    if right_major > 0.00022:
        tags.add("labia_majora_right")

    left_sulcus = -0.00042 * gaussian2(u, t, -0.205, 0.47, 0.055, 0.23)
    right_sulcus = -0.00042 * gaussian2(u, t, 0.210, 0.47, 0.055, 0.23)
    value += left_sulcus + right_sulcus

    left_minor = 0.00134 * gaussian2(u, t, -0.095, 0.47, 0.050, 0.20)
    right_minor = 0.00122 * gaussian2(u, t, 0.108, 0.47, 0.052, 0.20)
    value += left_minor + right_minor
    if left_minor > 0.00013:
        tags.add("labia_minora_left")
    if right_minor > 0.00013:
        tags.add("labia_minora_right")

    vestibule = -0.00062 * gaussian2(u, t, 0.0, 0.49, 0.125, 0.18)
    value += vestibule
    if vestibule < -0.00010:
        tags.add("vestibule")

    hood = 0.00110 * gaussian2(u, t, -0.006, 0.285, 0.120, 0.065)
    glans = 0.00044 * gaussian2(u, t, -0.010, 0.320, 0.045, 0.032)
    value += hood + glans
    if hood + glans > 0.00012:
        tags.add("clitoral_hood_glans")

    for name, spec in OPENING_SPECS.items():
        radius = elliptical_radius(
            u,
            t,
            float(spec["u"]),
            float(spec["t"]),
            float(spec["su"]),
            float(spec["st"]),
        )
        rim = float(spec["rim_height_m"]) * ring_value(radius)
        cap = -float(spec["cap_depth_m"]) * math.exp(-0.5 * (radius / 0.48) ** 2)
        value += rim + cap
        if 0.68 <= radius <= 1.34:
            tags.add(f"{name}__rim")
        if radius <= 0.56:
            tags.add(f"{name}__cap")

    fourchette = 0.00044 * gaussian2(u, t, 0.0, 0.68, 0.135, 0.050)
    value += fourchette
    if fourchette > 0.00008:
        tags.add("posterior_fourchette")

    perineum = 0.00018 * gaussian2(u, t, 0.0, 0.77, 0.25, 0.12)
    value += perineum
    if perineum > 0.000045:
        tags.add("external_perineum")

    return max(-MAXIMUM_OFFSET_M, min(MAXIMUM_OFFSET_M, value)), tags


def ensure_semantic_samples(
    semantic: dict[str, set[bmesh.types.BMVert]],
    parameters: Mapping[bmesh.types.BMVert, tuple[float, float]],
    distances: Mapping[bmesh.types.BMVert, int],
) -> None:
    """Fail-safe semantic sampling; this never alters geometry."""
    targets = {
        "mons": (0.0, 0.16, 0.50, 0.18, 4),
        "labia_majora_left": (-0.31, 0.46, 0.18, 0.27, 5),
        "labia_majora_right": (0.32, 0.46, 0.18, 0.27, 5),
        "labia_minora_left": (-0.095, 0.47, 0.070, 0.22, 4),
        "labia_minora_right": (0.108, 0.47, 0.070, 0.22, 4),
        "vestibule": (0.0, 0.49, 0.14, 0.19, 4),
        "clitoral_hood_glans": (-0.006, 0.285, 0.12, 0.075, 4),
        "posterior_fourchette": (0.0, 0.68, 0.14, 0.06, 4),
        "external_perineum": (0.0, 0.77, 0.27, 0.13, 4),
    }
    candidates = [vertex for vertex in parameters if distances.get(vertex, 0) >= 2]
    for name, (cu, ct, su, st, count) in targets.items():
        if semantic.get(name):
            continue
        ranked = sorted(
            candidates,
            key=lambda vertex: (
                ((parameters[vertex][0] - cu) / su) ** 2
                + ((parameters[vertex][1] - ct) / st) ** 2,
                vertex.index,
            ),
        )
        semantic[name].update(ranked[:count])

    for name, spec in OPENING_SPECS.items():
        cap_name = f"{name}__cap"
        rim_name = f"{name}__rim"
        if not semantic.get(cap_name):
            ranked = sorted(
                candidates,
                key=lambda vertex: (
                    elliptical_radius(
                        *parameters[vertex],
                        float(spec["u"]),
                        float(spec["t"]),
                        float(spec["su"]),
                        float(spec["st"]),
                    ),
                    vertex.index,
                ),
            )
            semantic[cap_name].update(ranked[:3])
        if not semantic.get(rim_name):
            ranked = sorted(
                candidates,
                key=lambda vertex: (
                    abs(
                        elliptical_radius(
                            *parameters[vertex],
                            float(spec["u"]),
                            float(spec["t"]),
                            float(spec["su"]),
                            float(spec["st"]),
                        )
                        - 1.0
                    ),
                    vertex.index,
                ),
            )
            semantic[rim_name].update(ranked[:5])


def enforce_opening_semantic_disjointness(
    semantic: dict[str, set[bmesh.types.BMVert]],
    parameters: Mapping[bmesh.types.BMVert, tuple[float, float]],
) -> dict[str, Any]:
    records = []
    for suffix, target_radius in (("__rim", 1.0), ("__cap", 0.0)):
        names = [f"{name}{suffix}" for name in OPENING_SPECS]
        memberships: dict[bmesh.types.BMVert, list[str]] = defaultdict(list)
        for name in names:
            for vertex in semantic.get(name, set()):
                memberships[vertex].append(name)
        for vertex, overlapping in memberships.items():
            if len(overlapping) <= 1:
                continue
            u, t = parameters[vertex]
            ranked = []
            for semantic_name in overlapping:
                opening_name = semantic_name[: -len(suffix)]
                spec = OPENING_SPECS[opening_name]
                radius = elliptical_radius(
                    u,
                    t,
                    float(spec["u"]),
                    float(spec["t"]),
                    float(spec["su"]),
                    float(spec["st"]),
                )
                ranked.append((abs(radius - target_radius), opening_name, semantic_name))
            ranked.sort()
            retained = ranked[0][2]
            removed = []
            for _score, _opening, semantic_name in ranked[1:]:
                semantic[semantic_name].discard(vertex)
                removed.append(semantic_name)
            records.append(
                {
                    "vertex_index_before_final_reindex": int(vertex.index),
                    "kind": suffix[2:],
                    "retained": retained,
                    "removed": removed,
                }
            )
    return {
        "overlap_count_resolved": len(records),
        "records": records,
        "authority": "nearest exact opening ellipse in 3D-centerline coordinates",
    }


def feature_code_for_vertices(
    vertices: Iterable[bmesh.types.BMVert],
    vertex_tags: Mapping[bmesh.types.BMVert, set[str]],
) -> int:
    priority = (
        ("urethral_meatus__cap", "urethral_meatus"),
        ("urethral_meatus__rim", "urethral_meatus"),
        ("vaginal_introitus__cap", "vaginal_introitus"),
        ("vaginal_introitus__rim", "vaginal_introitus"),
        ("anal_verge__cap", "anal_verge"),
        ("anal_verge__rim", "anal_verge"),
        ("clitoral_hood_glans", "clitoral_hood_glans"),
        ("labia_minora_left", "labia_minora_left"),
        ("labia_minora_right", "labia_minora_right"),
        ("vestibule", "vestibule"),
        ("posterior_fourchette", "posterior_fourchette"),
        ("external_perineum", "external_perineum"),
        ("labia_majora_left", "labia_majora_left"),
        ("labia_majora_right", "labia_majora_right"),
        ("mons", "mons"),
    )
    tags = set().union(*(vertex_tags.get(vertex, set()) for vertex in vertices))
    for tag, code_name in priority:
        if tag in tags:
            return FEATURE_CODES[code_name]
    return FEATURE_CODES["base"]


def normalized_top_four(deform: Any) -> dict[int, float]:
    values = sorted(
        ((int(index), float(weight)) for index, weight in deform.items() if weight > 0.0),
        key=lambda item: (-item[1], item[0]),
    )[:4]
    total = sum(weight for _index, weight in values)
    if total <= 1.0e-12:
        raise RuntimeError("subdivision created an unweighted patch vertex")
    return {index: weight / total for index, weight in values}


def refine_and_shape(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    preflight: Mapping[str, Any],
) -> dict[str, Any]:
    mesh_shading_before = mesh_shading_state(body)
    boundary_corner_normals_before = mesh_boundary_corner_normal_audit(
        body,
        preflight["patch_faces"],
        preflight["boundary_edges"],
    )
    custom_normal_clear_evidence = {
        "applied": False,
        "reason": "Attempt 08 is diagnostic-only for shading state; A07 proved no exact-boundary split-normal discontinuity",
        "changes": [],
    }
    mesh_shading_after_boundary_custom_clear = mesh_shading_state(body)
    boundary_corner_normals_after_custom_clear = mesh_boundary_corner_normal_audit(
        body,
        preflight["patch_faces"],
        preflight["boundary_edges"],
    )
    bm = bmesh.new()
    try:
        bm.from_mesh(body.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        original_vertex_id = bm.verts.layers.int.new("__R24_DIRECT_ORIGINAL_VERTEX_ID")
        original_face_id = bm.faces.layers.int.new("__R24_DIRECT_ORIGINAL_FACE_ID")
        original_loop_id = bm.loops.layers.int.new("__R24_DIRECT_ORIGINAL_LOOP_ID")
        feature_layer = bm.faces.layers.int.new("__R24_DIRECT_FEATURE_CODE")
        for vertex in bm.verts:
            vertex[original_vertex_id] = int(vertex.index)
        loop_counter = 0
        for face in bm.faces:
            face[original_face_id] = int(face.index)
            face[feature_layer] = 0
            for loop in face.loops:
                loop[original_loop_id] = loop_counter
                loop_counter += 1

        group_names = {int(group.index): group.name for group in body.vertex_groups}
        frozen_before = r23_author.bmesh_frozen_snapshot(
            bm,
            original_vertex_id,
            original_face_id,
            original_loop_id,
            set(map(int, preflight["interior_vertices"])),
            set(map(int, preflight["patch_faces"])),
            group_names,
        )

        original_vertices = set(bm.verts)
        original_vertex_ids = {vertex: int(vertex.index) for vertex in bm.verts}
        original_faces = set(bm.faces)
        patch_faces_before = {
            face
            for face in bm.faces
            if int(face[original_face_id]) in preflight["patch_faces"]
        }
        if any(len(face.verts) != 3 for face in patch_faces_before):
            raise RuntimeError("the exact R19 patch is no longer all triangles")
        # A per-triangle centroid refinement adds resolution without cutting,
        # splitting, or replacing any existing edge.  This is deliberately used
        # instead of bmesh edge subdivision: Attempt 01 proved that Blender's
        # propagated edge pattern can replace boundary-edge identity even when
        # the requested edge list itself is internal.
        subdivision = bmesh.ops.poke(
            bm,
            faces=sorted(patch_faces_before, key=lambda face: face.index),
            offset=0.0,
            use_relative_offset=False,
            center_mode="MEAN_WEIGHTED",
        )
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        new_vertices = {vertex for vertex in bm.verts if vertex not in original_vertices}
        for vertex, original_index in original_vertex_ids.items():
            if vertex.is_valid:
                vertex[original_vertex_id] = int(original_index)
        for vertex in new_vertices:
            vertex[original_vertex_id] = -1

        patch_faces = {
            face for face in bm.faces if int(face.material_index) == PATCH_MATERIAL_INDEX
        }
        if not patch_faces:
            raise RuntimeError("internal subdivision lost the R19 patch material")
        if any(len(face.verts) != 3 for face in patch_faces):
            raise RuntimeError("face-local centroid refinement did not remain triangular")
        for face in patch_faces:
            face[original_face_id] = -1
            face.smooth = True
            for loop in face.loops:
                loop[original_loop_id] = -1

        patch_vertices = {vertex for face in patch_faces for vertex in face.verts}
        patch_edges = list({edge for face in patch_faces for edge in face.edges})
        seam_edges = {
            edge
            for edge in patch_edges
            if len(edge.link_faces) == 2
            and sum(face in patch_faces for face in edge.link_faces) == 1
        }
        seam_vertices = {vertex for edge in seam_edges for vertex in edge.verts}
        if len(seam_edges) != EXPECTED_BOUNDARY_EDGES or len(seam_vertices) != EXPECTED_BOUNDARY_VERTICES:
            raise RuntimeError(
                f"direct subdivision changed the seam: {len(seam_edges)} edges, "
                f"{len(seam_vertices)} vertices"
            )

        current_boundary_edges = {
            edge_key(
                int(original_vertex_ids.get(edge.verts[0], -1)),
                int(original_vertex_ids.get(edge.verts[1], -1)),
            )
            for edge in seam_edges
        }
        if current_boundary_edges != preflight["boundary_edges"]:
            missing = sorted(preflight["boundary_edges"].difference(current_boundary_edges))
            added = sorted(current_boundary_edges.difference(preflight["boundary_edges"]))
            raise RuntimeError(
                "face-local refinement changed an exact R19 seam edge; "
                f"missing={missing}, added={added}"
            )

        bm.normal_update()
        base_world = {vertex: body.matrix_world @ vertex.co for vertex in patch_vertices}
        parameters, coordinate_evidence = direct_source_3d_parameters(
            patch_vertices, base_world
        )
        distances = graph_distance_from_seam(patch_vertices, patch_edges, seam_vertices)
        seam_shading_before = seam_edge_records(
            body,
            patch_faces,
            seam_edges,
            original_vertex_ids,
            parameters,
        )
        seam_before_values = [
            float(record["normal_dot"])
            for record in seam_shading_before["records"]
        ]
        fairing_evidence = boundary_tangent_plane_fairing(
            body,
            patch_faces,
            patch_edges,
            seam_edges,
            seam_vertices,
            distances,
            original_vertex_ids,
        )
        bm.normal_update()

        normal_matrix = body.matrix_world.to_3x3().inverted().transposed()
        world_to_local = body.matrix_world.inverted().to_3x3()
        interpolated_world_normals: dict[bmesh.types.BMVert, Vector] = {}
        for vertex in patch_vertices:
            normal = normal_matrix @ vertex.normal
            if normal.length <= 1.0e-12:
                raise RuntimeError("refined R19 patch contains a zero local normal")
            normal.normalize()
            interpolated_world_normals[vertex] = normal
        # One tangent-aware averaging pass keeps directions local while removing
        # midpoint faceting.  No fixed global outward vector participates.
        smoothed_world_normals: dict[bmesh.types.BMVert, Vector] = {}
        for vertex in patch_vertices:
            adjacent = [
                edge.other_vert(vertex)
                for edge in vertex.link_edges
                if edge.other_vert(vertex) in patch_vertices
            ]
            reference = interpolated_world_normals[vertex]
            accumulated = reference * 2.0
            for neighbor in adjacent:
                candidate = interpolated_world_normals[neighbor].copy()
                if candidate.dot(reference) < 0.0:
                    candidate.negate()
                accumulated += candidate
            if accumulated.length <= 1.0e-12:
                accumulated = reference.copy()
            accumulated.normalize()
            smoothed_world_normals[vertex] = accumulated

        semantic: dict[str, set[bmesh.types.BMVert]] = defaultdict(set)
        vertex_tags: dict[bmesh.types.BMVert, set[str]] = {}
        displacements: dict[bmesh.types.BMVert, float] = {}
        for vertex in sorted(patch_vertices, key=lambda item: item.index):
            u, t = parameters[vertex]
            offset, tags = feature_offset_and_tags(u, t)
            distance = distances[vertex]
            # The exact seam and its patch-side tangent-support centroid are
            # reserved for fairing; feature relief reaches full strength after
            # the next two graph rings.
            seam_fade = smoothstep((float(distance) - 1.0) / 2.5)
            lateral_fade = smoothstep((1.0 - abs(u)) / 0.16)
            applied_offset = offset * seam_fade * lateral_fade
            if vertex in seam_vertices:
                applied_offset = 0.0
            vertex.co += world_to_local @ (
                smoothed_world_normals[vertex] * applied_offset
            )
            displacements[vertex] = float(applied_offset)
            vertex_tags[vertex] = set(tags)
            for tag in tags:
                semantic[tag].add(vertex)

        ensure_semantic_samples(semantic, parameters, distances)
        deoverlap_evidence = enforce_opening_semantic_disjointness(
            semantic, parameters
        )
        vertex_tags = {}
        for name, vertices in semantic.items():
            for vertex in vertices:
                vertex_tags.setdefault(vertex, set()).add(name)

        deform = bm.verts.layers.deform.active
        if deform is None:
            raise RuntimeError("R19 primary surface lacks deform weights")
        rig_bones = {bone.name for bone in rig.data.bones}
        group_index_to_name = {int(group.index): group.name for group in body.vertex_groups}
        for vertex in new_vertices:
            normalized = normalized_top_four(vertex[deform])
            vertex[deform].clear()
            for group_index, weight in normalized.items():
                group_name = group_index_to_name.get(group_index)
                if group_name is None or group_name not in rig_bones:
                    raise RuntimeError("subdivision interpolated a non-native rig weight")
                vertex[deform][group_index] = float(weight)

        bm.normal_update()
        seam_shading_after = seam_edge_records(
            body,
            patch_faces,
            seam_edges,
            original_vertex_ids,
            parameters,
        )
        seam_after_values = [
            float(record["normal_dot"])
            for record in seam_shading_after["records"]
        ]

        semantic_world = {}
        normal_matrix = body.matrix_world.to_3x3().inverted().transposed()
        for name, vertices in semantic.items():
            if not vertices:
                continue
            centroid = sum(
                (body.matrix_world @ vertex.co for vertex in vertices), Vector()
            ) / len(vertices)
            average_normal = Vector()
            for vertex in vertices:
                normal = normal_matrix @ vertex.normal
                if normal.length > 1.0e-12:
                    normal.normalize()
                    average_normal += normal
            if average_normal.length > 1.0e-12:
                average_normal.normalize()
            semantic_world[name] = {
                "vertex_count": len(vertices),
                "centroid_world_m": vector_record(centroid),
                "average_surface_normal_world": vector_record(average_normal),
            }

        for face in patch_faces:
            face[feature_layer] = feature_code_for_vertices(face.verts, vertex_tags)

        frozen_after = r23_author.bmesh_frozen_snapshot(
            bm,
            original_vertex_id,
            original_face_id,
            original_loop_id,
            set(map(int, preflight["interior_vertices"])),
            set(map(int, preflight["patch_faces"])),
            group_names,
        )
        if frozen_before != frozen_after:
            raise RuntimeError("out-of-patch R19 mesh/UV/weight state changed")

        boundary_positions_after = [
            vector_record(
                body.matrix_world
                @ next(
                    vertex.co
                    for vertex in seam_vertices
                    if int(vertex[original_vertex_id]) == original_index
                )
            )
            for original_index in sorted(preflight["boundary_vertices"])
        ]
        boundary_position_sha256_after = canonical_sha256(boundary_positions_after)
        if boundary_position_sha256_after != preflight["boundary_position_sha256"]:
            raise RuntimeError("exact R19 seam vertex position changed")

        bm.verts.index_update()
        bm.faces.index_update()
        semantic_global = {
            name: sorted(int(vertex.index) for vertex in vertices)
            for name, vertices in semantic.items()
        }
        t_global = {
            int(vertex.index): float(parameters[vertex][1]) for vertex in patch_vertices
        }
        patch_face_indices = sorted(int(face.index) for face in patch_faces)
        feature_faces: dict[str, list[int]] = defaultdict(list)
        for face in patch_faces:
            feature_faces[str(int(face[feature_layer]))].append(int(face.index))

        original_vertex_count = len(original_vertices)
        original_face_count = len(original_faces)
        new_vertex_count = len(new_vertices)
        subdivision_new_face_count = len(subdivision.get("faces", ()))
        maximum_offset = max((abs(value) for value in displacements.values()), default=0.0)
        displacement_hash = canonical_sha256(
            sorted(
                [int(vertex.index), round(float(value), 12)]
                for vertex, value in displacements.items()
            )
        )
        patch_baseline_hash = canonical_sha256(
            sorted(
                [int(vertex.index), *vector_record(base_world[vertex])]
                for vertex in patch_vertices
            )
        )

        bm.verts.layers.int.remove(original_vertex_id)
        bm.faces.layers.int.remove(original_face_id)
        bm.faces.layers.int.remove(feature_layer)
        bm.loops.layers.int.remove(original_loop_id)
        bm.to_mesh(body.data)
    finally:
        bm.free()

    body.data.update(calc_edges=True, calc_edges_loose=True)
    mesh_shading_after = mesh_shading_state(body)
    boundary_corner_normals_after = mesh_boundary_corner_normal_audit(
        body,
        patch_face_indices,
        current_boundary_edges,
    )
    return {
        "frozen_surviving_sha256_before": frozen_before,
        "frozen_surviving_sha256_after": frozen_after,
        "frozen_surviving_exact": frozen_before == frozen_after,
        "boundary_position_sha256_before": preflight["boundary_position_sha256"],
        "boundary_position_sha256_after": boundary_position_sha256_after,
        "boundary_position_exact": (
            boundary_position_sha256_after == preflight["boundary_position_sha256"]
        ),
        "boundary_edge_sha256_before": preflight["boundary_edge_sha256"],
        "boundary_edge_sha256_after": canonical_sha256(
            [list(edge) for edge in sorted(current_boundary_edges)]
        ),
        "boundary_edges_exact": current_boundary_edges == preflight["boundary_edges"],
        "original_vertex_count": original_vertex_count,
        "original_face_count": original_face_count,
        "new_vertex_count": new_vertex_count,
        "face_local_centroid_count": new_vertex_count,
        "face_local_refinement_result_face_count": subdivision_new_face_count,
        "patch_face_indices": patch_face_indices,
        "feature_faces": {key: sorted(value) for key, value in feature_faces.items()},
        "semantic_global": semantic_global,
        "semantic_world": semantic_world,
        "t_global": t_global,
        "seam_dot_before": seam_before_values,
        "seam_dot_after": seam_after_values,
        "seam_shading_audit": {
            "mesh_before": mesh_shading_before,
            "mesh_after_exact_boundary_custom_clear": (
                mesh_shading_after_boundary_custom_clear
            ),
            "mesh_after": mesh_shading_after,
            "boundary_corner_normals_before": boundary_corner_normals_before,
            "boundary_corner_normals_after_custom_clear": (
                boundary_corner_normals_after_custom_clear
            ),
            "boundary_corner_normals_after": boundary_corner_normals_after,
            "boundary_before": seam_shading_before,
            "boundary_after": seam_shading_after,
            "custom_boundary_normal_change": custom_normal_clear_evidence,
            "custom_boundary_normal_change_applied": bool(
                custom_normal_clear_evidence["applied"]
            ),
            "face_smooth_change_applied": False,
            "boundary_sharpness_change_applied": bool(
                fairing_evidence["sharp_boundary_edges_cleared"]
            ),
        },
        "maximum_absolute_offset_m": maximum_offset,
        "seam_support_fairing": fairing_evidence,
        "opening_semantic_deoverlap": deoverlap_evidence,
        "displacement_sha256": displacement_hash,
        "patch_baseline_world_position_sha256": patch_baseline_hash,
        "anatomical_frame": {
            "coordinate_evidence": coordinate_evidence,
            "u_definition": "normalized existing source-bound lateral chart coordinate",
            "t_definition": "nearest exact-source 13-control 3D centerline arc-length coordinate",
            "offset_direction": "per-vertex interpolated and one-ring-smoothed local surface normal",
            "surface_position_remap_used": False,
        },
    }


def topology_and_semantic_gates(
    body: bpy.types.Object,
    applied: Mapping[str, Any],
) -> dict[str, Any]:
    faces = faces_of(body)
    patch_faces = set(map(int, applied["patch_face_indices"]))
    patch_topology = topology_core.topology_record(faces, patch_faces)
    whole_topology = topology_core.topology_record(faces, range(len(faces)))
    edge_faces = topology_core.edge_face_map(faces)
    patch_vertices = {
        int(vertex) for face_index in patch_faces for vertex in faces[face_index]
    }
    patch_edges = {
        edge
        for face_index in patch_faces
        for edge in topology_core.face_edges(faces[face_index])
    }
    patch_nonmanifold = [
        list(edge) for edge in sorted(patch_edges) if len(edge_faces.get(edge, ())) != 2
    ]
    areas = []
    edge_ratios = []
    for face_index in patch_faces:
        polygon = body.data.polygons[face_index]
        areas.append(float(polygon.area))
        vertices = list(map(int, polygon.vertices))
        lengths = [
            (
                body.data.vertices[vertices[offset]].co
                - body.data.vertices[vertices[(offset + 1) % len(vertices)]].co
            ).length
            for offset in range(len(vertices))
        ]
        positive = [value for value in lengths if value > 1.0e-12]
        edge_ratios.append(max(positive) / min(positive) if positive else math.inf)

    seam_values = list(map(float, applied["seam_dot_after"]))
    seam_minimum = min(seam_values, default=-1.0)
    seam_median = statistics.median(seam_values) if seam_values else -1.0
    seam_max_dihedral = math.degrees(math.acos(max(-1.0, min(1.0, seam_minimum))))

    semantic = {
        name: set(map(int, values)) for name, values in applied["semantic_global"].items()
    }
    required = (
        "mons",
        "labia_majora_left",
        "labia_majora_right",
        "labia_minora_left",
        "labia_minora_right",
        "vestibule",
        "clitoral_hood_glans",
        "urethral_meatus__rim",
        "urethral_meatus__cap",
        "vaginal_introitus__rim",
        "vaginal_introitus__cap",
        "posterior_fourchette",
        "external_perineum",
        "anal_verge__rim",
        "anal_verge__cap",
    )
    nonempty = {name: bool(semantic.get(name)) for name in required}
    rim_names = (
        "urethral_meatus__rim",
        "vaginal_introitus__rim",
        "anal_verge__rim",
    )
    cap_names = (
        "urethral_meatus__cap",
        "vaginal_introitus__cap",
        "anal_verge__cap",
    )
    rim_overlaps = []
    for offset, first in enumerate(rim_names):
        for second in rim_names[offset + 1 :]:
            overlap = semantic.get(first, set()).intersection(semantic.get(second, set()))
            if overlap:
                rim_overlaps.append(
                    {"first": first, "second": second, "vertices": sorted(overlap)}
                )
    cap_overlaps = []
    for offset, first in enumerate(cap_names):
        for second in cap_names[offset + 1 :]:
            overlap = semantic.get(first, set()).intersection(semantic.get(second, set()))
            if overlap:
                cap_overlaps.append(
                    {"first": first, "second": second, "vertices": sorted(overlap)}
                )

    t_global = {int(index): float(value) for index, value in applied["t_global"].items()}
    centroids_t = {
        name: float(sum(t_global[index] for index in semantic[name]) / len(semantic[name]))
        for name in required
        if semantic.get(name)
    }
    order_checks = {
        "hood_before_urethra": centroids_t["clitoral_hood_glans"]
        < centroids_t["urethral_meatus__rim"],
        "urethra_before_introitus": centroids_t["urethral_meatus__rim"]
        < centroids_t["vaginal_introitus__rim"],
        "introitus_before_fourchette": centroids_t["vaginal_introitus__rim"]
        < centroids_t["posterior_fourchette"],
        "fourchette_before_perineum": centroids_t["posterior_fourchette"]
        < centroids_t["external_perineum"],
        "perineum_before_anal_verge": centroids_t["external_perineum"]
        < centroids_t["anal_verge__rim"],
    }

    semantic_world = applied["semantic_world"]
    coverage_sequence = (
        "clitoral_hood_glans",
        "urethral_meatus__rim",
        "vaginal_introitus__rim",
        "posterior_fourchette",
        "external_perineum",
        "anal_verge__rim",
    )
    coverage_centroids = {
        name: Vector(tuple(map(float, semantic_world[name]["centroid_world_m"])))
        for name in coverage_sequence
    }
    coverage_normals = {
        name: Vector(
            tuple(map(float, semantic_world[name]["average_surface_normal_world"]))
        )
        for name in coverage_sequence
    }
    consecutive_world_separations = {}
    for first, second in zip(coverage_sequence, coverage_sequence[1:]):
        delta = coverage_centroids[second] - coverage_centroids[first]
        consecutive_world_separations[f"{first}__to__{second}"] = {
            "euclidean_m": float(delta.length),
            "posterior_delta_y_m": float(delta.y),
            "vertical_delta_z_m": float(delta.z),
        }
    anterior_names = coverage_sequence[:3]
    posterior_names = coverage_sequence[3:]
    anterior_mean_y = statistics.mean(coverage_centroids[name].y for name in anterior_names)
    posterior_mean_y = statistics.mean(coverage_centroids[name].y for name in posterior_names)
    coverage_checks = {
        "posterior_group_at_least_30mm_behind_anterior_group": (
            posterior_mean_y - anterior_mean_y >= 0.030
        ),
        "fourchette_is_posterior_to_introitus": (
            coverage_centroids["posterior_fourchette"].y
            > coverage_centroids["vaginal_introitus__rim"].y
        ),
        "perineum_is_posterior_to_fourchette": (
            coverage_centroids["external_perineum"].y
            > coverage_centroids["posterior_fourchette"].y
        ),
        "anal_verge_is_posterior_to_introitus_by_at_least_35mm": (
            coverage_centroids["anal_verge__rim"].y
            - coverage_centroids["vaginal_introitus__rim"].y
            >= 0.035
        ),
        "all_consecutive_world_centroids_separated_by_at_least_7mm": all(
            record["euclidean_m"] >= 0.007
            for record in consecutive_world_separations.values()
        ),
        "anterior_features_front_facing": all(
            coverage_normals[name].y < -0.10 for name in anterior_names
        ),
        "anal_feature_posterior_or_inferior_facing": (
            coverage_normals["anal_verge__rim"].y > 0.10
            or coverage_normals["anal_verge__rim"].z < -0.35
        ),
    }

    bm = bmesh.new()
    try:
        bm.from_mesh(body.data)
        exact_report = exact_intersections.exact_nonadjacent_intersection_report(
            bm, include_pair_details=True
        )
    finally:
        bm.free()
    patch_intersection_pairs = [
        record
        for record in exact_report["pairs"]
        if record.get("overlap_character") == "genuine_penetration"
        and any(int(index) in patch_faces for index in record["face_indices"])
    ]

    seam_audit = applied["seam_shading_audit"]
    seam_before_by_edge = {
        tuple(map(int, record["boundary_vertex_ids"])): float(record["normal_dot"])
        for record in seam_audit["boundary_before"]["records"]
    }
    seam_after_by_edge = {
        tuple(map(int, record["boundary_vertex_ids"])): float(record["normal_dot"])
        for record in seam_audit["boundary_after"]["records"]
    }
    targeted_seam_dots = {
        "-".join(map(str, edge)): seam_after_by_edge.get(edge, -1.0)
        for edge in sorted(TARGETED_BOUNDARY_EDGE_IDS)
    }
    untargeted_seam_regressions = [
        {
            "boundary_vertex_ids": list(edge),
            "before": before,
            "after": seam_after_by_edge.get(edge, -1.0),
        }
        for edge, before in sorted(seam_before_by_edge.items())
        if edge not in TARGETED_BOUNDARY_EDGE_IDS
        and seam_after_by_edge.get(edge, -1.0) < before - 1.0e-6
    ]
    fairing = applied["seam_support_fairing"]
    targeted_movement_edges = {
        tuple(map(int, record["boundary_vertex_ids"]))
        for record in fairing["movement_records"]
    }

    checks = {
        "one_patch_component": patch_topology["component_count"] == 1,
        "patch_is_one_manifold_disk": patch_topology["is_one_disk"] is True,
        "whole_body_component_count_preserved": whole_topology["component_count"] == 1,
        "patch_boundary_cycle_exact_34": patch_topology["boundary_cycle_count"] == 1
        and patch_topology["boundary_cycle_lengths"] == [EXPECTED_BOUNDARY_VERTICES],
        "patch_associated_nonmanifold_edges_zero": len(patch_nonmanifold) == 0,
        "degenerate_patch_faces_zero": min(areas, default=0.0) > 1.0e-10,
        "frozen_outside_state_exact": applied["frozen_surviving_exact"] is True,
        "exact_original_boundary_positions_fixed": applied["boundary_position_exact"] is True,
        "exact_original_boundary_edges_fixed": applied["boundary_edges_exact"] is True,
        "all_required_semantic_sets_nonempty": all(nonempty.values()),
        "three_endpoint_rim_sets_disjoint": len(rim_overlaps) == 0,
        "three_endpoint_cap_sets_disjoint": len(cap_overlaps) == 0,
        "clinical_longitudinal_order": all(order_checks.values()),
        "semantic_world_coverage_and_separation": all(coverage_checks.values()),
        "patch_exact_intersections_zero": len(patch_intersection_pairs) == 0,
        "whole_exact_intersections_equal_attempt06_inherited_29": exact_report[
            "exact_genuine_penetration_pair_count"
        ]
        == ATTEMPT_06_WHOLE_GENUINE_INTERSECTION_COUNT,
        "seam_minimum_normal_dot_at_least_0_70": seam_minimum >= 0.70,
        "seam_median_normal_dot_at_least_0_94": seam_median >= 0.94,
        "maximum_seam_dihedral_at_most_45_degrees": seam_max_dihedral <= 45.0,
        "maximum_patch_edge_ratio_at_most_8": max(edge_ratios, default=math.inf) <= 8.0,
        "maximum_patch_edge_ratio_not_above_attempt06": max(
            edge_ratios, default=math.inf
        )
        <= ATTEMPT_06_MAXIMUM_PATCH_EDGE_RATIO + 1.0e-6,
        "maximum_local_normal_offset_at_most_3mm": applied["maximum_absolute_offset_m"]
        <= MAXIMUM_OFFSET_M + 1.0e-12,
        "targeted_four_support_edges_exact": targeted_movement_edges
        == TARGETED_BOUNDARY_EDGE_IDS,
        "targeted_support_count_exactly_four": fairing[
            "targeted_support_vertex_count"
        ]
        == 4,
        "all_other_fairing_displacement_zero": fairing[
            "all_other_fairing_displacement_zero"
        ]
        is True,
        "all_four_targeted_seam_dots_at_least_0_715": all(
            value >= TARGETED_SEAM_DOT for value in targeted_seam_dots.values()
        ),
        "untargeted_seam_dots_not_regressed": len(untargeted_seam_regressions) == 0,
        "maximum_targeted_support_fairing_at_most_1_25mm": fairing[
            "maximum_support_movement_m"
        ]
        <= TARGETED_SUPPORT_CAP_M + FAIRING_GATE_EPSILON_M,
        "second_ring_fairing_exactly_zero": fairing[
            "maximum_ring_2_applied_world_m"
        ]
        <= FAIRING_GATE_EPSILON_M,
        "shading_material_custom_normals_unchanged": not any(
            (
                seam_audit["custom_boundary_normal_change_applied"],
                seam_audit["face_smooth_change_applied"],
                seam_audit["boundary_sharpness_change_applied"],
            )
        ),
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "patch_topology": patch_topology,
        "whole_topology": whole_topology,
        "patch_vertex_count": len(patch_vertices),
        "patch_face_count": len(patch_faces),
        "patch_associated_nonmanifold_edges": patch_nonmanifold,
        "minimum_patch_face_area_local_units_squared": min(areas, default=0.0),
        "maximum_patch_edge_ratio": max(edge_ratios, default=math.inf),
        "seam_normal_dot": {
            "count": len(seam_values),
            "minimum": seam_minimum,
            "median": seam_median,
            "maximum": max(seam_values, default=-1.0),
            "maximum_dihedral_degrees": seam_max_dihedral,
        },
        "targeted_seam_dots": targeted_seam_dots,
        "untargeted_seam_regressions": untargeted_seam_regressions,
        "semantic_nonempty": nonempty,
        "semantic_vertex_index_sha256": {
            name: topology_core.canonical_index_sha256(values)
            for name, values in semantic.items()
        },
        "semantic_centroid_anatomical_t": centroids_t,
        "semantic_order_checks": order_checks,
        "semantic_world_coverage": {
            "centroids_and_normals": {
                name: semantic_world[name] for name in coverage_sequence
            },
            "consecutive_separations": consecutive_world_separations,
            "anterior_group_mean_y_m": anterior_mean_y,
            "posterior_group_mean_y_m": posterior_mean_y,
            "posterior_minus_anterior_y_m": posterior_mean_y - anterior_mean_y,
            "checks": coverage_checks,
        },
        "rim_overlaps": rim_overlaps,
        "cap_overlaps": cap_overlaps,
        "exact_intersections": {
            "whole_exact_genuine_pair_count": exact_report[
                "exact_genuine_penetration_pair_count"
            ],
            "patch_related_exact_genuine_pair_count": len(patch_intersection_pairs),
            "patch_related_pairs": patch_intersection_pairs,
        },
    }


def render_uniform_clay_front_without_diagnostic_subdivision(
    directory: Path,
) -> dict[str, Any]:
    """Render the existing diagnostic copy with only its added SUBSURF disabled."""
    scene = bpy.context.scene
    clinical = bpy.data.objects.get("R24_FeatureAligned_ClinicalDiagnostic")
    if clinical is None:
        raise RuntimeError("uniform clinical diagnostic copy is missing")
    modifier = clinical.modifiers.get("R24_ClinicalSubdivision")
    if modifier is None:
        raise RuntimeError("clinical diagnostic subdivision modifier is missing")
    prior_hide = bool(clinical.hide_render)
    prior_show_render = bool(modifier.show_render)
    prior_show_viewport = bool(modifier.show_viewport)
    other_visibility = {
        obj.name: bool(obj.hide_render)
        for obj in scene.objects
        if obj is not clinical and obj.type == "MESH"
    }
    try:
        for obj in scene.objects:
            if obj is not clinical and obj.type == "MESH":
                obj.hide_render = True
        clinical.hide_render = False
        modifier.show_render = False
        modifier.show_viewport = False
        filename = "protected_clinical_front_no_diagnostic_subdivision.png"
        scene.render.filepath = str(directory / filename)
        bpy.ops.render.render(write_still=True)
    finally:
        clinical.hide_render = prior_hide
        modifier.show_render = prior_show_render
        modifier.show_viewport = prior_show_viewport
        for name, hidden in other_visibility.items():
            obj = bpy.data.objects.get(name)
            if obj is not None:
                obj.hide_render = hidden
    path = directory / filename
    return {
        "filename": filename,
        "path": relative(path),
        "sha256": sha256(path),
        "diagnostic_only": True,
        "source_body_geometry_mutated": False,
        "uniform_clay_retained": True,
        "clinical_subdivision_disabled_for_this_render_only": True,
        "camera_light_material_unchanged_from_protected_front": True,
    }


def main() -> None:
    global ACTIVE_OUTPUT
    worker = Path(__file__).resolve()
    if sha256(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("immutable R19 source hash drifted")
    if (
        not BOUND_R19_EVIDENCE.is_file()
        or sha256(BOUND_R19_EVIDENCE) != BOUND_R19_EVIDENCE_SHA256
    ):
        raise RuntimeError("bound zero-patch-intersection R19 evidence drifted")
    ACTIVE_OUTPUT = allocate_output()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    body = bpy.data.objects.get(BODY_NAME)
    rig = bpy.data.objects.get(RIG_NAME)
    if body is None or rig is None:
        raise RuntimeError("exact R19 body or native rig is absent")
    r24_base.clear_pose(rig)
    source_shape_key_count = len(body.data.shape_keys.key_blocks) if body.data.shape_keys else 0

    preflight = original_patch_preflight(body)
    applied = refine_and_shape(body, rig, preflight)
    gates = topology_and_semantic_gates(body, applied)
    render_directory = ACTIVE_OUTPUT / "private_owner_review"
    renders = r24_render.render_evidence(body, applied, render_directory)
    no_subdivision_diagnostic = (
        render_uniform_clay_front_without_diagnostic_subdivision(render_directory)
    )
    renders["rendered"].append(no_subdivision_diagnostic["filename"])
    renders["diagnostic_only_no_subdivision_views"] = [
        no_subdivision_diagnostic["filename"]
    ]
    renders["no_subdivision_diagnostic"] = no_subdivision_diagnostic

    report = {
        "schema": "kira.avatar.r24_direct_subdivision_surface_simulation.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "NO_SAVE_STRUCTURAL_GATES_PASS_VISUAL_OWNER_REVIEW_REQUIRED"
            if gates["passed"]
            else "NO_SAVE_STRUCTURAL_OR_SEMANTIC_GATE_FAILURE_RETAINED_FOR_DIAGNOSIS"
        ),
        "source": {
            "path": relative(SOURCE),
            "bytes": SOURCE.stat().st_size,
            "sha256": sha256(SOURCE),
            "unchanged": sha256(SOURCE) == SOURCE_SHA256,
            "body": BODY_NAME,
            "rig": RIG_NAME,
            "source_shape_key_count": source_shape_key_count,
        },
        "worker": {
            "path": relative(worker),
            "bytes": worker.stat().st_size,
            "sha256": sha256(worker),
        },
        "bound_r19_patch_evidence": {
            "path": relative(BOUND_R19_EVIDENCE),
            "sha256": BOUND_R19_EVIDENCE_SHA256,
            "zero_patch_related_exact_intersections": True,
            "exact_34_vertex_seam": True,
        },
        "preserved_attempt_07_worker": {
            "path": relative(worker),
            "sha256_before_attempt_08_patch": ATTEMPT_07_WORKER_SHA256,
            "attempt_07_evidence_preserved_byte_for_byte": True,
        },
        "method": {
            "id": "R24_EXACT_R19_PATCH_FOUR_LOW_DOT_SEAM_CHILD_RELIEF_V4",
            "new_body_created": False,
            "broad_disk_removed_or_remapped": False,
            "rectangular_sweep_used": False,
            "donor_coordinates_used": False,
            "donor_topology_used": False,
            "boolean_used": False,
            "floating_or_separate_anatomy_object_created": False,
            "through_tract_created": False,
            "fixed_global_outward_direction_used": False,
            "exact_embedded_r19_patch_retained_as_baseline": True,
            "surface_position_remap_used": False,
            "posterior_domain_expansion_used": False,
            "world_z_only_longitudinal_parameter_used": False,
            "exact_source_13_control_3d_centerline_arc_parameter_used": True,
            "existing_patch_edges_split_or_replaced": False,
            "one_face_local_centroid_added_per_source_triangle": True,
            "exact_original_boundary_fixed": True,
            "patch_side_seam_support_fairing_used": True,
            "only_four_proven_low_dot_seam_child_supports_moved": True,
            "targeted_minimum_dot": TARGETED_SEAM_DOT,
            "targeted_support_world_cap_m": TARGETED_SUPPORT_CAP_M,
            "world_space_boundary_tangent_plane_ring_1_projection_used": False,
            "world_space_boundary_tangent_plane_ring_2_half_projection_used": False,
            "global_ring_projection_used": False,
            "world_space_fairing_caps_measured_after_local_assignment": True,
            "direct_full_radius_tangent_rotation_used": False,
            "seam_shading_audit_included": True,
            "deterministic_opening_semantic_deoverlap_used": True,
            "small_feature_offsets_follow_interpolated_local_normals": True,
            "three_distinct_shallow_capped_recess_sets": True,
            "uniform_clinical_material_first": True,
        },
        "preflight": {
            "patch_face_count": len(preflight["patch_faces"]),
            "patch_vertex_count": len(preflight["patch_vertices"]),
            "interior_vertex_count": len(preflight["interior_vertices"]),
            "boundary_vertex_count": len(preflight["boundary_vertices"]),
            "boundary_edge_count": len(preflight["boundary_edges"]),
            "boundary_position_sha256": preflight["boundary_position_sha256"],
            "boundary_edge_sha256": preflight["boundary_edge_sha256"],
            "topology": preflight["topology"],
        },
        "application": applied,
        "gates": gates,
        "renders": renders,
        "operations": {
            "blend_saved": False,
            "source_overwritten": False,
            "runtime_or_person_state_changed": False,
            "voice_model_device_files_touched": False,
            "activation_assignment_export_publication": False,
        },
        "truth": (
            "External private visual/topology simulation only. No internal route, physiology, "
            "elimination, reproduction, pregnancy, sensation, subjective state, owner approval, "
            "runtime readiness, or biological function is implemented or claimed."
        ),
    }
    report_path = ACTIVE_OUTPUT / "SIMULATION_REPORT.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(ACTIVE_OUTPUT)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback

        trace = traceback.format_exc()
        if ACTIVE_OUTPUT is not None:
            failure = {
                "schema": "kira.avatar.r24_direct_subdivision_surface_failure.v1",
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "status": "NO_SAVE_FAILURE_PRESERVED",
                "exception_type": type(exc).__name__,
                "exception": str(exc),
                "traceback": trace,
                "source": {
                    "path": relative(SOURCE),
                    "sha256": sha256(SOURCE) if SOURCE.is_file() else None,
                },
                "operations": {
                    "blend_saved": False,
                    "source_overwritten": False,
                    "runtime_or_person_state_changed": False,
                },
            }
            (ACTIVE_OUTPUT / "FAILURE.json").write_text(
                json.dumps(failure, indent=2) + "\n", encoding="utf-8"
            )
        print(trace, file=sys.stderr)
        raise
