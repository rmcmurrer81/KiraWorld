"""Append-only no-save R24 Attempt 16 BlackProject patch simulation.

The worker keeps the sealed R24 face/body/rig, appends only the licensed
BlackProject Attempt 02 adult patch, replaces the measured 88-face collision
domain with an injective quality-refined constrained-Delaunay height graph,
and welds the unchanged 34-point interface.  Structural gates run before
private paired renders.  No Blend is saved and nothing is activated.
"""

from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import traceback
from typing import Any, Iterable, Mapping, Sequence

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
from mathutils.kdtree import KDTree
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_author_kira_r21_pelvis_attempt01 as r21  # noqa: E402
from tools import blender_simulate_kira_r24_internal_midpoint_fair_surface as a09  # noqa: E402
from tools.blender_exact_mesh_intersections import (  # noqa: E402
    exact_nonadjacent_intersection_report,
)


LATERAL = Vector((0.9999999403953552, 0.0, 0.0)).normalized()
LONGITUDINAL = Vector((0.0, -0.3000001609325409, 0.9539390802383423)).normalized()
OUTWARD = Vector((0.0, -0.9539390802383423, -0.3000001609325409)).normalized()


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def atomic_write_json(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def resolve_bound(path: str) -> Path:
    resolved = (ROOT / path).resolve(strict=True)
    if ROOT.resolve() not in resolved.parents:
        raise RuntimeError(f"bound path escapes project: {path}")
    return resolved


def verify_inputs(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    verified = {}
    for name, record in config["inputs"].items():
        path = resolve_bound(str(record["path"]))
        actual = sha256_file(path)
        expected = str(record["sha256"]).lower()
        if actual != expected:
            raise RuntimeError(f"bound input hash drifted: {name}: {actual}")
        verified[name] = {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": actual,
            "bytes": path.stat().st_size,
        }
    authority = json.loads(
        resolve_bound(config["inputs"]["licensed_authority"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    if (
        authority.get("authority_id") != config["license"]["authority_id"]
        or authority.get("source", {}).get("author") != "BlackProject"
        or authority.get("source", {}).get("license") != "CC BY 4.0"
        or authority.get("allowed_use", {}).get("may_transform_geometry") is not True
    ):
        raise RuntimeError("licensed authority no longer permits this derivative")
    return verified


def exact_report(obj: bpy.types.Object) -> dict[str, Any]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    result = exact_nonadjacent_intersection_report(bm, include_pair_details=True)
    bm.free()
    return result


def append_patch(
    path: Path,
    object_name: str,
    body: bpy.types.Object,
    contract: Mapping[str, Any],
    output: Path,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    before_objects = set(bpy.data.objects)
    before_collections = set(bpy.data.collections)
    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        if object_name not in source.objects:
            raise RuntimeError("preserved Attempt 02 patch object is absent")
        target.objects = [object_name]
    appended = sorted(
        (value for value in bpy.data.objects if value not in before_objects),
        key=lambda value: value.name,
    )
    new_collections = sorted(
        (value.name for value in bpy.data.collections if value not in before_collections)
    )
    actual_names = [value.name for value in appended]
    expected_names = list(contract["expected_appended_object_names"])
    expected_collections = list(contract["expected_new_collection_names"])
    if canonical_sha256(expected_names) != contract["expected_appended_object_names_sha256"]:
        raise RuntimeError("Attempt 16 configured append-object inventory hash drifted")
    if canonical_sha256(expected_collections) != contract["expected_new_collection_names_sha256"]:
        raise RuntimeError("Attempt 16 configured append-collection inventory hash drifted")
    dependencies = list(contract["dependency_object_names_removed_in_memory_only"])
    if canonical_sha256(dependencies) != contract["dependency_object_names_sha256"]:
        raise RuntimeError("Attempt 16 configured append-dependency inventory hash drifted")
    signatures = [
        {
            "name": value.name,
            "type": value.type,
            "data_name": value.data.name if value.data is not None else None,
            "parent_name": value.parent.name if value.parent is not None else None,
            "collection_names": sorted(collection.name for collection in value.users_collection),
            "modifiers": [
                {
                    "name": modifier.name,
                    "type": modifier.type,
                    "object": (
                        modifier.object.name
                        if hasattr(modifier, "object") and modifier.object is not None
                        else None
                    ),
                }
                for modifier in value.modifiers
            ],
        }
        for value in appended
    ]
    exact_inventory = (
        actual_names == expected_names and new_collections == expected_collections
    )
    evidence = {
        "schema": "kira.avatar.r24.blackproject_attempt16.append_inventory.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "PASS_EXACT_SEVEN_OBJECT_HIERARCHY_NO_NEW_COLLECTIONS"
            if exact_inventory
            else "FAIL_APPEND_INVENTORY_DRIFT_BEFORE_GEOMETRY_MUTATION"
        ),
        "requested_object": object_name,
        "expected_appended_object_names": expected_names,
        "expected_appended_object_names_sha256": canonical_sha256(expected_names),
        "actual_appended_object_names": actual_names,
        "actual_appended_object_names_sha256": canonical_sha256(actual_names),
        "missing_object_names": sorted(set(expected_names) - set(actual_names)),
        "extra_object_names": sorted(set(actual_names) - set(expected_names)),
        "expected_new_collection_names": expected_collections,
        "actual_new_collection_names": new_collections,
        "missing_collection_names": sorted(set(expected_collections) - set(new_collections)),
        "extra_collection_names": sorted(set(new_collections) - set(expected_collections)),
        "object_signatures": signatures,
        "geometry_mutation_reached": False,
        "render_reached": False,
        "blend_saved": False,
    }
    atomic_write_json(output / contract["inventory_evidence_filename"], evidence)
    if not exact_inventory:
        raise RuntimeError(
            "Attempt 16 append inventory drifted before geometry mutation: "
            f"objects={actual_names!r}; collections={new_collections!r}"
        )
    patch_contract = contract["requested_patch"]
    adult = next(
        (
            value
            for value in appended
            if value.name == patch_contract["object_name"]
            and value.type == patch_contract["object_type"]
            and value.data is not None
            and value.data.name.startswith(patch_contract["mesh_name_prefix"])
        ),
        None,
    )
    if adult is None:
        raise RuntimeError("Attempt 16 exact requested patch signature is absent")
    if sorted(value for value in actual_names if value != adult.name) != dependencies:
        raise RuntimeError("Attempt 16 dependency cleanup set does not match exact append set")
    adult.parent = None
    adult.matrix_parent_inverse.identity()
    adult.matrix_world = body.matrix_world.copy()
    for modifier in list(adult.modifiers):
        adult.modifiers.remove(modifier)
    for value in appended:
        if value is not adult:
            bpy.data.objects.remove(value, do_unlink=True)
    if not adult.users_collection:
        bpy.context.scene.collection.objects.link(adult)
    bpy.context.view_layer.update()
    return adult, evidence


def ordered_cycle(edges: Iterable[bmesh.types.BMEdge]) -> list[bmesh.types.BMVert]:
    adjacency: dict[bmesh.types.BMVert, set[bmesh.types.BMVert]] = {}
    for edge in edges:
        first, second = edge.verts
        adjacency.setdefault(first, set()).add(second)
        adjacency.setdefault(second, set()).add(first)
    if not adjacency or any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise RuntimeError("local repair boundary is not one simple cycle")
    start = min(adjacency, key=lambda vertex: int(vertex.index))
    cycle = [start]
    previous = None
    current = start
    while True:
        candidates = sorted(
            (value for value in adjacency[current] if value != previous),
            key=lambda vertex: int(vertex.index),
        )
        next_value = candidates[0]
        if next_value == start:
            break
        if next_value in cycle:
            raise RuntimeError("local repair boundary traversal crossed itself")
        cycle.append(next_value)
        previous, current = current, next_value
    if len(cycle) != len(adjacency):
        raise RuntimeError("local repair boundary has multiple cycles")
    return cycle


def polygon_area(points: Sequence[Vector]) -> float:
    return 0.5 * sum(
        float(first.x * second.y - second.x * first.y)
        for first, second in zip(points, points[1:] + points[:1])
    )


def orient2d(first: Vector, second: Vector, third: Vector) -> float:
    return float(
        (second.x - first.x) * (third.y - first.y)
        - (second.y - first.y) * (third.x - first.x)
    )


def proper_segment_crossing(
    first: Vector, second: Vector, third: Vector, fourth: Vector, epsilon: float
) -> bool:
    values = (
        orient2d(first, second, third),
        orient2d(first, second, fourth),
        orient2d(third, fourth, first),
        orient2d(third, fourth, second),
    )
    return (
        values[0] * values[1] < -(epsilon * epsilon)
        and values[2] * values[3] < -(epsilon * epsilon)
    )


def polygon_is_simple(points: Sequence[Vector], epsilon: float) -> bool:
    count = len(points)
    for first_index in range(count):
        first_next = (first_index + 1) % count
        for second_index in range(first_index + 1, count):
            second_next = (second_index + 1) % count
            if len({first_index, first_next, second_index, second_next}) < 4:
                continue
            if proper_segment_crossing(
                points[first_index],
                points[first_next],
                points[second_index],
                points[second_next],
                epsilon,
            ):
                return False
    return True


def triangle_angles(points: Sequence[Vector]) -> list[float]:
    result = []
    for index in range(3):
        center = points[index]
        first = points[(index + 1) % 3] - center
        second = points[(index + 2) % 3] - center
        if first.length == 0.0 or second.length == 0.0:
            return [0.0, 0.0, 0.0]
        result.append(math.degrees(first.angle(second)))
    return result


def triangle_incenter(points: Sequence[Vector]) -> Vector:
    first, second, third = points
    weights = ((second - third).length, (first - third).length, (first - second).length)
    total = sum(weights)
    return (first * weights[0] + second * weights[1] + third * weights[2]) / total


def run_cdt(
    boundary: Sequence[Vector], seeds: Sequence[Vector], epsilon: float
) -> dict[str, Any]:
    inputs = [Vector((float(value.x), float(value.y))) for value in boundary + list(seeds)]
    boundary_count = len(boundary)
    edges = [(index, (index + 1) % boundary_count) for index in range(boundary_count)]
    output = delaunay_2d_cdt(
        inputs,
        edges,
        [list(range(boundary_count))],
        1,
        float(epsilon),
        True,
    )
    coordinates, _edges, faces, original_vertices, _oe, _of = output
    if any(len(face) != 3 for face in faces):
        raise RuntimeError("constrained Delaunay output was not all triangles")
    boundary_output: dict[int, int] = {}
    for output_index, sources in enumerate(original_vertices):
        for source_index in sources:
            if int(source_index) < boundary_count:
                if int(source_index) in boundary_output:
                    raise RuntimeError("constrained Delaunay duplicated a boundary vertex")
                boundary_output[int(source_index)] = output_index
    if len(boundary_output) != boundary_count:
        raise RuntimeError("constrained Delaunay omitted a boundary vertex")
    maximum_boundary_delta = max(
        (
            coordinates[output_index] - boundary[source_index]
        ).length
        for source_index, output_index in boundary_output.items()
    )
    if maximum_boundary_delta > epsilon * 4.0:
        raise RuntimeError("constrained Delaunay moved the local boundary")
    return {
        "coordinates": list(coordinates),
        "faces": [list(map(int, face)) for face in faces],
        "boundary_output": boundary_output,
        "maximum_boundary_delta_2d_m": float(maximum_boundary_delta),
    }


def quality_refined_cdt(
    boundary: Sequence[Vector], config: Mapping[str, Any]
) -> dict[str, Any]:
    epsilon = float(config["cdt_epsilon_m"])
    threshold = float(config["minimum_new_triangle_angle_degrees"])
    maximum_vertices = int(config["maximum_new_interior_vertex_count"])
    maximum_iterations = int(config["maximum_quality_refinement_iterations"])
    base = run_cdt(boundary, [], epsilon)
    seeds = [
        sum((base["coordinates"][index] for index in face), Vector()) / 3.0
        for face in base["faces"]
    ]
    seen = {
        (round(float(value.x), 14), round(float(value.y), 14)) for value in seeds
    }
    result = None
    for iteration in range(maximum_iterations + 1):
        result = run_cdt(boundary, seeds, epsilon)
        quality = []
        for face in result["faces"]:
            points = [result["coordinates"][index] for index in face]
            quality.append((min(triangle_angles(points)), face, points))
        minimum = min(value[0] for value in quality)
        if minimum >= threshold:
            result["quality_refinement_iterations"] = iteration
            result["seed_count"] = len(seeds)
            result["minimum_2d_triangle_angle_degrees"] = minimum
            return result
        if len(seeds) >= maximum_vertices:
            break
        _angle, _face, points = min(quality, key=lambda value: value[0])
        candidates = [
            triangle_incenter(points),
            sum(points, Vector()) / 3.0,
        ]
        added = False
        for candidate in candidates:
            key = (round(float(candidate.x), 14), round(float(candidate.y), 14))
            if key not in seen and all(
                (candidate - value).length > epsilon * 16.0
                for value in boundary + list(seeds)
            ):
                seeds.append(candidate)
                seen.add(key)
                added = True
                break
        if not added:
            break
    minimum = (
        min(
            min(
                triangle_angles(
                    [result["coordinates"][index] for index in face]
                )
            )
            for face in result["faces"]
        )
        if result
        else 0.0
    )
    raise RuntimeError(
        "quality_refined_cdt_failed_minimum_angle:"
        f"achieved={minimum}:required={threshold}:seeds={len(seeds)}"
    )


def solve_dirichlet(
    faces: Sequence[Sequence[int]],
    boundary_values: Mapping[int, Sequence[float]],
    component_count: int,
) -> dict[int, np.ndarray]:
    adjacency: dict[int, set[int]] = {}
    for face in faces:
        for index, first in enumerate(face):
            second = face[(index + 1) % len(face)]
            adjacency.setdefault(first, set()).add(second)
            adjacency.setdefault(second, set()).add(first)
    interior = sorted(set(adjacency) - set(boundary_values))
    interior_index = {value: index for index, value in enumerate(interior)}
    matrix = np.zeros((len(interior), len(interior)), dtype=np.float64)
    rhs = np.zeros((len(interior), component_count), dtype=np.float64)
    for vertex in interior:
        row = interior_index[vertex]
        matrix[row, row] = float(len(adjacency[vertex]))
        for neighbor in adjacency[vertex]:
            if neighbor in interior_index:
                matrix[row, interior_index[neighbor]] -= 1.0
            else:
                rhs[row] += np.asarray(boundary_values[neighbor], dtype=np.float64)
    solved = np.linalg.solve(matrix, rhs) if interior else np.zeros((0, component_count))
    residual = matrix @ solved - rhs if interior else np.zeros((0, component_count))
    if residual.size and float(np.max(np.abs(residual))) > 1.0e-10:
        raise RuntimeError("Dirichlet reconstruction residual exceeded tolerance")
    result = {
        int(index): np.asarray(value, dtype=np.float64)
        for index, value in boundary_values.items()
    }
    result.update(
        {vertex: solved[index] for vertex, index in interior_index.items()}
    )
    return result


def capture_local_domain(
    bm: bmesh.types.BMesh,
    exact: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.faces.index_update()
    genuine_pairs = sorted(
        list(map(int, record["face_indices"]))
        for record in exact["pairs"]
        if record["genuine_positive_area_or_segment_penetration"]
    )
    if (
        len(genuine_pairs) != int(config["initial_exact_pair_count"])
        or canonical_sha256(genuine_pairs) != config["exact_pair_sha256"]
    ):
        raise RuntimeError("Attempt 02 exact-pair identity drifted")
    involved_faces = sorted({value for pair in genuine_pairs for value in pair})
    involved_vertices = sorted(
        {
            int(vertex.index)
            for face_index in involved_faces
            for vertex in bm.faces[face_index].verts
        }
    )
    if (
        canonical_sha256(involved_faces) != config["involved_face_sha256"]
        or canonical_sha256(involved_vertices) != config["involved_vertex_sha256"]
    ):
        raise RuntimeError("Attempt 02 collision locality drifted")
    selected = set(involved_faces)
    for _ in range(int(config["face_ring_expansion"])):
        selected.update(
            int(other.index)
            for face_index in list(selected)
            for edge in bm.faces[face_index].edges
            for other in edge.link_faces
        )
    selected_faces = {bm.faces[index] for index in selected}
    selected_vertices = {
        vertex for face in selected_faces for vertex in face.verts
    }
    selected_edges = {edge for face in selected_faces for edge in face.edges}
    edge_counts = {
        edge: sum(face in selected_faces for face in edge.link_faces)
        for edge in selected_edges
    }
    local_boundary_edges = {edge for edge, count in edge_counts.items() if count == 1}
    local_boundary = set(ordered_cycle(local_boundary_edges))
    interior = selected_vertices - local_boundary
    face_ids = sorted(int(face.index) for face in selected_faces)
    vertex_ids = sorted(int(vertex.index) for vertex in selected_vertices)
    boundary_edge_ids = sorted(
        sorted((int(edge.verts[0].index), int(edge.verts[1].index)))
        for edge in local_boundary_edges
    )
    if (
        len(selected_faces) != int(config["face_count"])
        or len(selected_vertices) != int(config["vertex_count"])
        or len(selected_edges) != int(config["edge_count"])
        or len(interior) != int(config["interior_vertex_count"])
        or len(local_boundary) != int(config["local_boundary_vertex_count"])
        or canonical_sha256(face_ids) != config["domain_face_sha256"]
        or canonical_sha256(vertex_ids) != config["domain_vertex_sha256"]
        or canonical_sha256(boundary_edge_ids)
        != config["local_boundary_edge_sha256"]
    ):
        raise RuntimeError("measured 88-face Attempt 16 domain drifted")
    cycle = ordered_cycle(local_boundary_edges)
    cycle_ids = [int(vertex.index) for vertex in cycle]
    if canonical_sha256(cycle_ids) != config["local_boundary_cycle_sha256"]:
        reversed_cycle = list(reversed(cycle_ids))
        rotations = [
            reversed_cycle[index:] + reversed_cycle[:index]
            for index in range(len(reversed_cycle))
        ] + [
            cycle_ids[index:] + cycle_ids[:index]
            for index in range(len(cycle_ids))
        ]
        matching = next(
            (row for row in rotations if canonical_sha256(row) == config["local_boundary_cycle_sha256"]),
            None,
        )
        if matching is None:
            raise RuntimeError("measured local boundary cycle identity drifted")
        by_id = {int(vertex.index): vertex for vertex in cycle}
        cycle = [by_id[value] for value in matching]
    return {
        "selected_faces": selected_faces,
        "selected_vertices": selected_vertices,
        "selected_edges": selected_edges,
        "local_boundary_edges": local_boundary_edges,
        "local_boundary": local_boundary,
        "interior": interior,
        "cycle": cycle,
        "face_ids": face_ids,
        "vertex_ids": vertex_ids,
        "boundary_edge_ids": boundary_edge_ids,
    }


def reconstruct_local_domain(
    obj: bpy.types.Object,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.index_update()
    bm.faces.index_update()
    global_boundary = {
        vertex: vertex.co.copy()
        for edge in bm.edges
        if len(edge.link_faces) == 1
        for vertex in edge.verts
    }
    if len(global_boundary) != int(config["global_seam_vertex_count"]):
        bm.free()
        raise RuntimeError("global 34-point patch seam drifted")
    before_exact = exact_nonadjacent_intersection_report(bm, include_pair_details=True)
    domain = capture_local_domain(bm, before_exact, config)
    cycle = list(domain["cycle"])
    cycle_world = [obj.matrix_world @ vertex.co for vertex in cycle]
    centroid_array = np.mean(np.asarray([tuple(value) for value in cycle_world]), axis=0)
    centroid = Vector(tuple(float(value) for value in centroid_array))
    centered = np.asarray([tuple(value - centroid) for value in cycle_world])
    _u, _s, vh = np.linalg.svd(centered, full_matrices=False)
    normal = Vector(tuple(float(value) for value in vh[-1])).normalized()
    surrounding_normals = []
    for vertex in domain["local_boundary"]:
        for face in vertex.link_faces:
            if face not in domain["selected_faces"]:
                transformed = obj.matrix_world.to_3x3() @ face.normal
                if transformed.length:
                    surrounding_normals.append(transformed.normalized())
    average_normal = sum(surrounding_normals, Vector()).normalized()
    if normal.dot(average_normal) < 0.0:
        normal.negate()
    u_axis = LATERAL - normal * LATERAL.dot(normal)
    if u_axis.length < 1.0e-8:
        u_axis = Vector(tuple(float(value) for value in vh[0]))
    u_axis.normalize()
    v_axis = normal.cross(u_axis).normalized()
    if v_axis.dot(LONGITUDINAL) < 0.0:
        u_axis.negate()
        v_axis.negate()
    boundary_2d = [
        Vector(((value - centroid).dot(u_axis), (value - centroid).dot(v_axis)))
        for value in cycle_world
    ]
    heights = [(value - centroid).dot(normal) for value in cycle_world]
    if polygon_area(boundary_2d) < 0.0:
        cycle.reverse()
        cycle_world.reverse()
        boundary_2d.reverse()
        heights.reverse()
    epsilon = float(config["cdt_epsilon_m"])
    if not polygon_is_simple(boundary_2d, epsilon):
        bm.free()
        raise RuntimeError("local boundary projection is not a simple polygon")
    maximum_deviation = max(abs(value) for value in heights)
    if maximum_deviation > float(config["maximum_local_chart_boundary_deviation_m"]):
        bm.free()
        raise RuntimeError("local boundary best-fit deviation exceeded bound")

    uv_layer = bm.loops.layers.uv.active
    if uv_layer is None:
        bm.free()
        raise RuntimeError("licensed patch UV layer is absent")
    boundary_uv: list[list[float]] = []
    for vertex in cycle:
        samples = [
            loop[uv_layer].uv.copy()
            for loop in vertex.link_loops
            if loop.face not in domain["selected_faces"]
        ]
        if not samples:
            bm.free()
            raise RuntimeError("local boundary lacks preserved outside UV samples")
        value = sum(samples, Vector()) / len(samples)
        boundary_uv.append([float(value.x), float(value.y)])
    deform = bm.verts.layers.deform.verify()
    group_indices = sorted(
        {
            int(group)
            for vertex in cycle
            for group, weight in vertex[deform].items()
            if float(weight) > 1.0e-10
        }
    )
    boundary_weights = [
        [float(vertex[deform].get(group, 0.0)) for group in group_indices]
        for vertex in cycle
    ]

    cdt = quality_refined_cdt(boundary_2d, config)
    output_boundary = {
        int(output_index): int(source_index)
        for source_index, output_index in cdt["boundary_output"].items()
    }
    boundary_height_values = {
        output_index: [float(heights[source_index])]
        for output_index, source_index in output_boundary.items()
    }
    boundary_uv_values = {
        output_index: boundary_uv[source_index]
        for output_index, source_index in output_boundary.items()
    }
    boundary_weight_values = {
        output_index: boundary_weights[source_index]
        for output_index, source_index in output_boundary.items()
    }
    reconstructed_heights = solve_dirichlet(cdt["faces"], boundary_height_values, 1)
    reconstructed_uv = solve_dirichlet(cdt["faces"], boundary_uv_values, 2)
    reconstructed_weights = solve_dirichlet(
        cdt["faces"], boundary_weight_values, len(group_indices)
    )

    bmesh.ops.delete(
        bm, geom=list(domain["selected_faces"]), context="FACES_KEEP_BOUNDARY"
    )
    isolated = [
        vertex for vertex in domain["interior"] if vertex.is_valid and not vertex.link_faces
    ]
    if isolated:
        bmesh.ops.delete(bm, geom=isolated, context="VERTS")
    output_vertices: dict[int, bmesh.types.BMVert] = {}
    for output_index, coordinate in enumerate(cdt["coordinates"]):
        if output_index in output_boundary:
            output_vertices[output_index] = cycle[output_boundary[output_index]]
            continue
        height = float(reconstructed_heights[output_index][0])
        world = centroid + u_axis * float(coordinate.x) + v_axis * float(coordinate.y) + normal * height
        vertex = bm.verts.new(obj.matrix_world.inverted() @ world)
        weights = np.maximum(reconstructed_weights[output_index], 0.0)
        total = float(np.sum(weights))
        if total > 1.0e-12:
            weights /= total
        for group, weight in zip(group_indices, weights):
            if float(weight) > 1.0e-10:
                vertex[deform][group] = float(weight)
        output_vertices[output_index] = vertex
    bm.verts.index_update()
    new_faces = []
    for triangle in cdt["faces"]:
        face = bm.faces.new([output_vertices[index] for index in triangle])
        face.material_index = 0
        face.smooth = True
        for loop, output_index in zip(face.loops, triangle):
            value = reconstructed_uv[output_index]
            loop[uv_layer].uv = (float(value[0]), float(value[1]))
        new_faces.append(face)
    bmesh.ops.recalc_face_normals(bm, faces=new_faces)
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.index_update()
    bm.faces.index_update()
    after_exact = exact_nonadjacent_intersection_report(bm, include_pair_details=True)
    global_boundary_delta = max(
        (
            (vertex.co - coordinate).length
            for vertex, coordinate in global_boundary.items()
            if vertex.is_valid
        ),
        default=0.0,
    )
    qualities = []
    for face in new_faces:
        points = [obj.matrix_world @ vertex.co for vertex in face.verts]
        area = (points[1] - points[0]).cross(points[2] - points[0]).length * 0.5
        qualities.append((float(area), min(triangle_angles(points))))
    minimum_area = min(value[0] for value in qualities)
    minimum_angle = min(value[1] for value in qualities)
    if int(after_exact["exact_genuine_penetration_pair_count"]) != 0:
        bm.free()
        raise RuntimeError("quality replacement did not reach zero exact patch pairs")
    if global_boundary_delta != 0.0:
        bm.free()
        raise RuntimeError("global 34-point patch seam moved")
    if minimum_angle < float(config["minimum_new_triangle_angle_degrees"]):
        bm.free()
        raise RuntimeError("quality replacement minimum triangle angle failed")
    if minimum_area < float(config["minimum_new_triangle_world_area_m2"]):
        bm.free()
        raise RuntimeError("quality replacement minimum triangle area failed")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update(calc_edges=True)
    return {
        "method": config["method"],
        "initial_exact_pair_count": before_exact[
            "exact_genuine_penetration_pair_count"
        ],
        "final_exact_pair_count": after_exact[
            "exact_genuine_penetration_pair_count"
        ],
        "removed_face_count": len(domain["face_ids"]),
        "removed_vertex_count": len(domain["interior"]),
        "local_boundary_vertex_count": len(cycle),
        "global_boundary_vertex_count": len(global_boundary),
        "global_boundary_coordinate_delta_local_units": global_boundary_delta,
        "maximum_local_chart_boundary_deviation_m": maximum_deviation,
        "new_interior_vertex_count": len(cdt["coordinates"]) - len(cycle),
        "new_face_count": len(cdt["faces"]),
        "quality_refinement_iterations": cdt["quality_refinement_iterations"],
        "minimum_new_triangle_angle_degrees": minimum_angle,
        "minimum_new_triangle_world_area_m2": minimum_area,
        "maximum_cdt_boundary_delta_2d_m": cdt["maximum_boundary_delta_2d_m"],
        "uv_reconstructed_from_exact_local_boundary": True,
        "native_weights_reconstructed_from_exact_local_boundary": True,
        "standalone_patch_exact_intersections_zero": True,
    }


def interface_world_points(body: bpy.types.Object, mask: Mapping[str, Any]) -> list[Vector]:
    return [
        body.matrix_world @ body.data.vertices[int(index)].co
        for index in mask["interface_vertices"]
    ]


def exact_interface_delta(points: Sequence[Vector], body: bpy.types.Object) -> dict[str, Any]:
    tree = KDTree(len(body.data.vertices))
    for index, vertex in enumerate(body.data.vertices):
        tree.insert(body.matrix_world @ vertex.co, index)
    tree.balance()
    distances = []
    matches = set()
    for point in points:
        _found, index, distance = tree.find(point)
        distances.append(float(distance))
        matches.add(int(index))
    return {
        "unique_matches": len(matches),
        "maximum_distance_m": max(distances, default=float("inf")),
        "exact_34_at_zero_distance": len(matches) == 34
        and max(distances, default=float("inf")) == 0.0,
    }


def inherited_pair_signature(
    body: bpy.types.Object, report: Mapping[str, Any], patch_faces: set[int]
) -> str:
    records = []
    for record in report["pairs"]:
        if not record["genuine_positive_area_or_segment_penetration"]:
            continue
        first, second = map(int, record["face_indices"])
        if first in patch_faces or second in patch_faces:
            continue
        face_rows = []
        for face_index in (first, second):
            face = body.data.polygons[face_index]
            face_rows.append(
                sorted(
                    [
                        round(float(component), 9)
                        for component in body.data.vertices[int(vertex)].co
                    ]
                    for vertex in face.vertices
                )
            )
        records.append(sorted(face_rows))
    return canonical_sha256(sorted(records))


def render_paired_evidence(
    body: bpy.types.Object,
    patch_faces: set[int],
    output: Path,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    applied = {
        "patch_face_indices": sorted(patch_faces),
        "feature_faces": {},
    }
    renders = a09.a08.r24_render.render_evidence(body, applied, output)
    paired = a09.render_uniform_clay_pairs_without_subdivision(output, applied)
    renders["rendered"].extend(record["filename"] for record in paired)
    renders["paired_subdivision_diagnostics"] = paired
    baseline_root = resolve_bound(config["baseline_root"])
    required = list(config["required_candidate_views"])
    pair_records = []
    for filename in required:
        candidate = output / filename
        baseline = baseline_root / filename
        if not candidate.is_file() or candidate.stat().st_size == 0:
            raise RuntimeError(f"required Attempt 16 render absent: {filename}")
        if not baseline.is_file() or baseline.stat().st_size == 0:
            raise RuntimeError(f"required Attempt 14 baseline absent: {filename}")
        pair_records.append(
            {
                "filename": filename,
                "attempt14_baseline_path": str(baseline.relative_to(ROOT)).replace("\\", "/"),
                "attempt14_baseline_sha256": sha256_file(baseline),
                "attempt16_candidate_path": str(candidate.relative_to(ROOT)).replace("\\", "/"),
                "attempt16_candidate_sha256": sha256_file(candidate),
                "same_camera_light_clay_contract": True,
            }
        )
    renders["attempt14_attempt16_same_camera_pairs"] = pair_records
    renders["required_pair_count"] = len(required)
    renders["all_required_pairs_present"] = len(pair_records) == len(required)
    return renders


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("attempt_id") != "attempt_16" or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION":
        raise RuntimeError("Attempt 16 config identity drifted")
    output = (ROOT / config["output"]["root"]).resolve()
    if output.exists():
        raise RuntimeError("append-only Attempt 16 output already exists")
    output.mkdir(parents=True)
    started = {
        "schema": "kira.avatar.r24.blackproject_attempt16.started.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "worker": str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"),
        "worker_sha256": sha256_file(Path(__file__).resolve()),
        "config": str(config_path.relative_to(ROOT)).replace("\\", "/"),
        "config_sha256": sha256_file(config_path),
        "blend_save_permitted": False,
    }
    atomic_write_json(output / "ATTEMPT_STARTED.json", started)
    try:
        verified = verify_inputs(config)
        source = resolve_bound(config["inputs"]["sealed_r24_source_blend"]["path"])
        patch_blend = resolve_bound(
            config["inputs"]["preserved_patch_attempt02_blend"]["path"]
        )
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
        body = bpy.data.objects.get(config["objects"]["body"])
        rig = bpy.data.objects.get(config["objects"]["rig"])
        if body is None or body.type != "MESH" or rig is None or rig.type != "ARMATURE":
            raise RuntimeError("sealed R24 body or native rig absent")
        r21.clear_pose(rig)
        mask = r21.patch_mask(body)
        seam_before = interface_world_points(body, mask)
        nonpatch_before = r21.nonpatch_snapshot(body)
        normals = r21.r20._capture_preserved_loop_normals(body)
        protected_objects = [value for value in bpy.data.objects if value != body]
        protected_before = {
            value.name: r21.object_digest(value) for value in protected_objects
        }
        rig_before = r21.object_digest(rig)
        material_names_before = [
            material.name if material else None for material in body.data.materials
        ]
        body_before_exact = r21.exact_audit(body)
        body_before_patch_faces = {
            int(face.index)
            for face in body.data.polygons
            if int(face.material_index) == int(config["objects"]["patch_material_index"])
        }
        inherited_before_signature = inherited_pair_signature(
            body, body_before_exact, body_before_patch_faces
        )

        adult, append_inventory = append_patch(
            patch_blend,
            config["objects"]["patch_object"],
            body,
            config["append_contract"],
            output,
        )
        repair = reconstruct_local_domain(adult, config["replacement"] | config["measured_repair_domain"])
        standalone_after = exact_report(adult)
        if standalone_after["exact_genuine_penetration_pair_count"] != 0:
            raise RuntimeError("standalone repaired licensed patch has exact intersections")
        comparison = r21.interface_comparison(body, mask, adult)
        if comparison["maximum_distance_m"] != 0.0 or comparison["unique_matches"] != 34:
            raise RuntimeError("licensed patch is not an exact zero-distance 34-point seam match")
        r21.remove_old_patch(body, mask)
        join = r21.join_and_weld(body, adult, rig)
        if join["actual_vertex_reduction"] != 34:
            raise RuntimeError("Attempt 16 did not weld exactly 34 seam vertices")
        normal_restore = r21.r20._restore_exact_preserved_loop_normals(body, normals)
        nonpatch_after = r21.nonpatch_snapshot(body)
        protected_after = {
            value.name: r21.object_digest(value) for value in protected_objects
        }
        if nonpatch_after != nonpatch_before:
            raise RuntimeError("nonpatch Kira body or face snapshot changed")
        if protected_after != protected_before or r21.object_digest(rig) != rig_before:
            raise RuntimeError("protected object or native rig changed")
        if [material.name if material else None for material in body.data.materials] != material_names_before:
            raise RuntimeError("body material slots changed")
        seam_after = exact_interface_delta(seam_before, body)
        if not seam_after["exact_34_at_zero_distance"]:
            raise RuntimeError("global 34-point seam changed during graft")
        final_exact = r21.exact_audit(body)
        classification = final_exact["classification"]
        if classification["patch_related_exact_genuine_pairs"] != 0:
            raise RuntimeError("post-graft patch-related exact intersections remain")
        if classification["nonpatch_exact_genuine_pairs"] != int(
            config["hard_gates"]["preserved_inherited_nonpatch_exact_genuine_intersections"]
        ):
            raise RuntimeError("inherited nonpatch intersection count changed")
        final_patch_faces = {
            int(face.index)
            for face in body.data.polygons
            if int(face.material_index) == int(config["objects"]["patch_material_index"])
        }
        inherited_after_signature = inherited_pair_signature(body, final_exact, final_patch_faces)
        if inherited_after_signature != inherited_before_signature:
            raise RuntimeError("inherited nonpatch exact-pair identity changed")

        structural_gates = {
            "standalone_patch_exact_genuine_intersections_zero": True,
            "post_graft_patch_related_exact_genuine_intersections_zero": True,
            "post_graft_new_noninherited_exact_genuine_intersections_zero": True,
            "preserved_inherited_nonpatch_exact_genuine_intersections_exactly_29": True,
            "global_34_seam_coordinate_delta_m_exact_zero": seam_after[
                "maximum_distance_m"
            ]
            == 0.0,
            "global_34_seam_unique_weld_count_exactly_34": join[
                "actual_vertex_reduction"
            ]
            == 34,
            "nonpatch_body_and_face_snapshot_exact": nonpatch_after == nonpatch_before,
            "protected_face_and_nonbody_objects_exact": protected_after
            == protected_before,
            "native_rig_exact": r21.object_digest(rig) == rig_before,
            "minimum_new_triangle_angle_at_least_12_degrees": repair[
                "minimum_new_triangle_angle_degrees"
            ]
            >= float(config["hard_gates"]["minimum_new_triangle_angle_degrees"]),
            "minimum_new_triangle_world_area_at_least_bound": repair[
                "minimum_new_triangle_world_area_m2"
            ]
            >= float(config["hard_gates"]["minimum_new_triangle_world_area_m2"]),
        }
        if not all(structural_gates.values()):
            raise RuntimeError("Attempt 16 structural hard gate failed")

        review = output / config["output"]["review_directory"]
        renders = render_paired_evidence(
            body, final_patch_faces, review, config["paired_visual_evidence"]
        )
        verified_after = verify_inputs(config)
        if verified_after != verified:
            raise RuntimeError("bound input changed during Attempt 16")
        report = {
            "schema": "kira.avatar.r24.blackproject_local_reconstruction_attempt16.simulation.v1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "NO_SAVE_STRUCTURAL_GATES_PASS_VISUAL_OWNER_REVIEW_REQUIRED",
            "license_and_attribution": config["license"],
            "inputs": verified,
            "worker": started,
            "append_inventory": append_inventory,
            "scope": {
                "private": True,
                "inactive": True,
                "unassigned": True,
                "unpublished": True,
                "runtime_changed": False,
                "blend_saved": False,
                "face_and_body_outside_exact_patch_preserved": True,
            },
            "repair": repair,
            "interface_before_graft": comparison,
            "join": join,
            "global_seam_after_graft": seam_after,
            "nonpatch_before": nonpatch_before,
            "nonpatch_after": nonpatch_after,
            "normal_restore": normal_restore,
            "exact_intersections": final_exact,
            "inherited_pair_signature_before": inherited_before_signature,
            "inherited_pair_signature_after": inherited_after_signature,
            "structural_hard_gates": structural_gates,
            "renders": renders,
            "save_gate": {
                "structural_hard_gates_pass": True,
                "paired_visual_evidence_complete": renders[
                    "all_required_pairs_present"
                ],
                "owner_visual_acceptance": False,
                "save_allowed": False,
                "reason": "owner visual decision is required after paired review",
            },
            "truth": {
                "patch_related_intersections_zero": True,
                "whole_body_intersections_zero": False,
                "whole_body_intersection_count": final_exact[
                    "exact_genuine_penetration_pair_count"
                ],
                "whole_body_nonzero_reason": "29 exact inherited nonpatch pairs are preserved because unrelated body mutation is forbidden",
                "internal_tract_or_physiology_implemented": False,
                "bathroom_reproduction_pregnancy_function_proven": False,
                "owner_approval_claimed": False,
            },
        }
        atomic_write_json(output / config["output"]["report"], report)
    except Exception as error:
        failure = {
            "schema": "kira.avatar.r24.blackproject_local_reconstruction_attempt16.failure.v1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "NO_SAVE_ATTEMPT16_FAILED_PRESERVED_FOR_DIAGNOSIS",
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "blend_saved": False,
            "runtime_changed": False,
        }
        atomic_write_json(output / config["output"]["failure"], failure)
        raise


if __name__ == "__main__":
    main()
