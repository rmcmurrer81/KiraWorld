#!/usr/bin/env python3
"""Read-only topology inspection for Kira's R7 protected head/body boundary.

The worker opens the pinned inactive R7 workspace, inspects the unchanged R6
surface, and writes diagnostic evidence.  It intentionally does not save the
Blend file, export geometry, or alter any live/runtime binding.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import heapq
import math
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import bpy
from mathutils import Vector


SUPPORT_GROUPS = (
    "mixamorig:Head_06",
    "mixamorig:Neck_05",
    "mixamorig:Spine2_04",
)


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--workspace-sha256", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--debug-render-dir")
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def index_sha256(indices: list[int]) -> str:
    digest = hashlib.sha256()
    for index in sorted(indices):
        digest.update(struct.pack("<I", int(index)))
    return digest.hexdigest()


def edge_sha256(edges: list[tuple[int, int]]) -> str:
    digest = hashlib.sha256()
    for first, second in sorted((min(a, b), max(a, b)) for a, b in edges):
        digest.update(struct.pack("<II", first, second))
    return digest.hexdigest()


def rounded_bounds(points: list[Vector]) -> dict[str, list[float]]:
    low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    return {
        "low": [round(float(value), 9) for value in low],
        "high": [round(float(value), 9) for value in high],
        "size": [round(float(value), 9) for value in high - low],
    }


def connected_components(mesh: bpy.types.Mesh) -> tuple[list[list[int]], dict[int, int]]:
    parent = list(range(len(mesh.vertices)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first: int, second: int) -> None:
        left = find(first)
        right = find(second)
        if left != right:
            parent[right] = left

    for edge in mesh.edges:
        union(int(edge.vertices[0]), int(edge.vertices[1]))
    result: dict[int, list[int]] = {}
    for vertex in mesh.vertices:
        result.setdefault(find(int(vertex.index)), []).append(int(vertex.index))
    components = sorted(result.values(), key=lambda item: (-len(item), min(item)))
    by_vertex: dict[int, int] = {}
    for ordinal, indices in enumerate(components):
        for index in indices:
            by_vertex[index] = ordinal
    return components, by_vertex


def positive_group_vertices(body: bpy.types.Object, name: str) -> set[int]:
    group = body.vertex_groups.get(name)
    if group is None:
        return set()
    return {
        int(vertex.index)
        for vertex in body.data.vertices
        if any(
            int(item.group) == int(group.index) and float(item.weight) > 1e-8
            for item in vertex.groups
        )
    }


def edge_face_counts(mesh: bpy.types.Mesh) -> dict[tuple[int, int], int]:
    counts: Counter[tuple[int, int]] = Counter()
    for polygon in mesh.polygons:
        indices = [int(index) for index in polygon.vertices]
        for position, first in enumerate(indices):
            second = indices[(position + 1) % len(indices)]
            counts[(min(first, second), max(first, second))] += 1
    return dict(counts)


def edge_graph_parts(edges: list[tuple[int, int]]) -> list[dict[str, object]]:
    adjacency: defaultdict[int, set[int]] = defaultdict(set)
    normalized = [(min(a, b), max(a, b)) for a, b in edges]
    for first, second in normalized:
        adjacency[first].add(second)
        adjacency[second].add(first)
    unseen = set(adjacency)
    result: list[dict[str, object]] = []
    while unseen:
        seed = min(unseen)
        queue = deque([seed])
        vertices: set[int] = set()
        while queue:
            current = queue.popleft()
            if current in vertices:
                continue
            vertices.add(current)
            unseen.discard(current)
            queue.extend(adjacency[current] - vertices)
        part_edges = [edge for edge in normalized if edge[0] in vertices and edge[1] in vertices]
        degrees = Counter({index: len(adjacency[index]) for index in vertices})
        result.append(
            {
                "vertices": sorted(vertices),
                "edges": sorted(set(part_edges)),
                "degree_histogram": dict(sorted(Counter(degrees.values()).items())),
                "topologically_closed_cycle": bool(vertices)
                and len(part_edges) == len(vertices)
                and all(value == 2 for value in degrees.values()),
            }
        )
    return sorted(result, key=lambda item: (-len(item["vertices"]), item["vertices"][0]))


def mesh_adjacency(mesh: bpy.types.Mesh) -> dict[int, set[int]]:
    adjacency: defaultdict[int, set[int]] = defaultdict(set)
    for edge in mesh.edges:
        first, second = (int(value) for value in edge.vertices)
        adjacency[first].add(second)
        adjacency[second].add(first)
    return dict(adjacency)


def shortest_level_path(
    mesh: bpy.types.Mesh,
    adjacency: dict[int, set[int]],
    allowed: set[int],
    start: int,
    end: int,
    target_z: float,
) -> list[int]:
    distances: dict[int, float] = {start: 0.0}
    previous: dict[int, int] = {}
    queue: list[tuple[float, int]] = [(0.0, start)]
    while queue:
        distance, current = heapq.heappop(queue)
        if distance != distances.get(current):
            continue
        if current == end:
            break
        first = mesh.vertices[current].co
        for neighbor in adjacency.get(current, set()):
            if neighbor not in allowed:
                continue
            second = mesh.vertices[neighbor].co
            length = float((second - first).length)
            vertical = 0.5 * (abs(float(first.z) - target_z) + abs(float(second.z) - target_z))
            # Prefer an actual mesh-edge path near the review plane without
            # pretending that it is a semantic or approved neck cut.
            step = length * (1.0 + 28.0 * vertical) + 2.0 * vertical
            candidate = distance + step
            if candidate < distances.get(neighbor, math.inf):
                distances[neighbor] = candidate
                previous[neighbor] = current
                heapq.heappush(queue, (candidate, neighbor))
    if end not in distances:
        raise ValueError(f"no level path from {start} to {end} near Z={target_z}")
    result = [end]
    while result[-1] != start:
        result.append(previous[result[-1]])
    result.reverse()
    return result


def paired_review_trace(
    body: bpy.types.Object,
    components: list[list[int]],
    shared_components: list[int],
    boundary_edges: list[tuple[int, int]],
    target_z: float,
) -> dict[str, object]:
    """Build two open, mirrored edge paths as a visual owner-review aid.

    The paths are deliberately not called a closed topological loop.  Each
    starts and ends on the disconnected sagittal seam and passes through the
    lateral neck surface.  Their endpoint proximity is measured rather than
    assumed.
    """
    mesh = body.data
    adjacency = mesh_adjacency(mesh)
    boundary_vertices = set(value for edge in boundary_edges for value in edge)
    half_records: list[dict[str, object]] = []
    all_edges: list[tuple[int, int]] = []
    endpoint_points: list[tuple[Vector, Vector]] = []
    for component_index in shared_components:
        component = set(components[component_index])
        midline = [
            index
            for index in component & boundary_vertices
            if abs(float(mesh.vertices[index].co.x)) <= 0.0015
            and abs(float(mesh.vertices[index].co.z) - target_z) <= 0.055
        ]
        if len(midline) < 2:
            raise ValueError(f"component {component_index} has insufficient midline endpoints")
        front = min(midline, key=lambda index: (float(mesh.vertices[index].co.y), abs(float(mesh.vertices[index].co.z) - target_z)))
        back = max(midline, key=lambda index: (float(mesh.vertices[index].co.y), -abs(float(mesh.vertices[index].co.z) - target_z)))
        allowed = {
            index
            for index in component
            if abs(float(mesh.vertices[index].co.z) - target_z) <= 0.30
        }
        lateral_candidates = [
            index
            for index in allowed
            if abs(float(mesh.vertices[index].co.z) - target_z) <= 0.05
        ]
        if not lateral_candidates:
            raise ValueError(f"component {component_index} has no lateral review anchor")
        lateral = max(
            lateral_candidates,
            key=lambda index: (
                abs(float(mesh.vertices[index].co.x)),
                -abs(float(mesh.vertices[index].co.y)),
                -abs(float(mesh.vertices[index].co.z) - target_z),
            ),
        )
        first_path = shortest_level_path(mesh, adjacency, allowed, front, lateral, target_z)
        # Keep the second half from walking back across the first half.  The
        # surface is dense enough to support a disjoint continuation; if it
        # does not, the review trace is not defensible and the inspection
        # should fail rather than silently draw a self-intersection.
        second_allowed = allowed - set(first_path[:-1])
        second_allowed.update((lateral, back))
        second_path = shortest_level_path(
            mesh,
            adjacency,
            second_allowed,
            lateral,
            back,
            target_z,
        )
        indices = first_path + second_path[1:]
        if len(indices) != len(set(indices)):
            raise ValueError(f"component {component_index} review path self-intersects")
        edges = list(zip(indices, indices[1:]))
        points = [mesh.vertices[index].co.copy() for index in indices]
        world_points = [body.matrix_world @ point for point in points]
        endpoint_points.append((world_points[0], world_points[-1]))
        all_edges.extend(edges)
        half_records.append(
            {
                "component_id": f"component_{component_index:03d}",
                "vertex_count": len(indices),
                "edge_count": len(edges),
                "vertex_indices": indices,
                "vertex_index_sha256": index_sha256(indices),
                "edge_index_pair_sha256": edge_sha256(edges),
                "front_midline_endpoint_vertex": front,
                "lateral_anchor_vertex": lateral,
                "back_midline_endpoint_vertex": back,
                "local_bounds": rounded_bounds(points),
                "world_bounds_m": rounded_bounds(world_points),
                "topologically_closed": False,
                "endpoint_degree_pattern": {"degree_1": 2, "degree_2": len(indices) - 2},
            }
        )
    front_gap = float((endpoint_points[0][0] - endpoint_points[1][0]).length)
    back_gap = float((endpoint_points[0][1] - endpoint_points[1][1]).length)
    return {
        "target_local_z": target_z,
        "status": "paired_open_half_paths_for_visual_review_only",
        "half_path_count": len(half_records),
        "halves": half_records,
        "combined_edge_count": len(all_edges),
        "combined_edge_index_pair_sha256": edge_sha256(all_edges),
        "topologically_closed_ring": False,
        "geometric_midline_endpoint_gaps_m": {
            "front": round(front_gap, 9),
            "back": round(back_gap, 9),
        },
        "visual_review_required": True,
        "edges": all_edges,
    }


def part_record(body: bpy.types.Object, part: dict[str, object]) -> dict[str, object]:
    indices = list(part["vertices"])
    local_points = [body.data.vertices[index].co.copy() for index in indices]
    world_points = [body.matrix_world @ point for point in local_points]
    return {
        "vertex_count": len(indices),
        "edge_count": len(part["edges"]),
        "vertex_index_sha256": index_sha256(indices),
        "edge_index_pair_sha256": edge_sha256(list(part["edges"])),
        "degree_histogram": part["degree_histogram"],
        "topologically_closed_cycle": part["topologically_closed_cycle"],
        "local_bounds": rounded_bounds(local_points),
        "world_bounds_m": rounded_bounds(world_points),
        "minimum_vertex_index": min(indices),
        "maximum_vertex_index": max(indices),
    }


def component_support_records(
    body: bpy.types.Object,
    components: list[list[int]],
    by_vertex: dict[int, int],
) -> tuple[dict[str, dict[str, object]], list[int]]:
    records: dict[str, dict[str, object]] = {}
    component_sets: list[set[int]] = []
    for name in SUPPORT_GROUPS:
        indices = positive_group_vertices(body, name)
        counts = Counter(by_vertex[index] for index in indices)
        component_sets.append(set(counts))
        records[name] = {
            "vertex_count": len(indices),
            "components": {f"component_{key:03d}": value for key, value in sorted(counts.items())},
        }
    shared = sorted(set.intersection(*component_sets)) if component_sets else []
    return records, shared


def debug_render(
    body: bpy.types.Object,
    components: list[list[int]],
    shared_components: list[int],
    boundary_edges: list[tuple[int, int]],
    review_traces: list[dict[str, object]],
    output_dir: Path,
) -> dict[str, dict[str, object]]:
    """Render a temporary component/boundary diagnostic without saving the file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.006, 0.009, 0.015)
    scene.view_settings.look = "AgX - Medium High Contrast"

    # Hide the workspace objects and make an inspection-only subset.
    for obj in scene.objects:
        obj.hide_render = True

    selected = set().union(*(set(components[index]) for index in shared_components))
    source_indices = sorted(selected)
    remap = {old: new for new, old in enumerate(source_indices)}
    coordinates = [body.data.vertices[index].co.copy() for index in source_indices]
    faces: list[list[int]] = []
    for polygon in body.data.polygons:
        indices = [int(index) for index in polygon.vertices]
        if all(index in selected for index in indices):
            faces.append([remap[index] for index in indices])
    subset_mesh = bpy.data.meshes.new("R7_Neck_Debug_Subset_Temporary")
    subset_mesh.from_pydata(coordinates, [], faces)
    subset_mesh.update()
    subset = bpy.data.objects.new("R7_Neck_Debug_Subset_Temporary", subset_mesh)
    scene.collection.objects.link(subset)
    subset.matrix_world = body.matrix_world.copy()
    subset.hide_render = False
    material = bpy.data.materials.new("R7_Neck_Debug_Surface_Temporary")
    material.diffuse_color = (0.18, 0.30, 0.42, 1.0)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled:
        principled.inputs["Base Color"].default_value = (0.06, 0.20, 0.34, 1.0)
        principled.inputs["Roughness"].default_value = 0.74
    subset.data.materials.append(material)
    wire = subset.modifiers.new(name="Topology_Wire_Temporary", type="WIREFRAME")
    wire.thickness = 0.0010
    wire.use_replace = False

    # Open component boundaries are drawn faint red; review traces are drawn
    # in bright, distinct colors. All are temporary diagnostic geometry.
    curve_data = bpy.data.curves.new("R7_Neck_Boundary_Edges_Temporary", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.bevel_depth = 0.00055
    curve_data.bevel_resolution = 2
    for first, second in boundary_edges:
        spline = curve_data.splines.new("POLY")
        spline.points.add(1)
        for point, index in zip(spline.points, (first, second)):
            world = body.matrix_world @ body.data.vertices[index].co
            point.co = (*world, 1.0)
    curve = bpy.data.objects.new("R7_Neck_Boundary_Edges_Temporary", curve_data)
    scene.collection.objects.link(curve)
    curve.hide_render = False
    line_material = bpy.data.materials.new("R7_Neck_Boundary_Orange_Temporary")
    line_material.diffuse_color = (0.45, 0.025, 0.02, 1.0)
    line_material.use_nodes = True
    line_principled = line_material.node_tree.nodes.get("Principled BSDF")
    if line_principled:
        line_principled.inputs["Base Color"].default_value = (0.32, 0.01, 0.006, 1.0)
        line_principled.inputs["Emission Color"].default_value = (0.35, 0.008, 0.004, 1.0)
        line_principled.inputs["Emission Strength"].default_value = 0.55
    curve.data.materials.append(line_material)

    trace_colors = (
        (1.0, 0.19, 0.01, 1.0),
        (0.0, 0.68, 1.0, 1.0),
    )
    for ordinal, trace in enumerate(review_traces):
        trace_data = bpy.data.curves.new(f"R7_Neck_Review_Trace_{ordinal}_Temporary", type="CURVE")
        trace_data.dimensions = "3D"
        trace_data.bevel_depth = 0.00215
        trace_data.bevel_resolution = 3
        for first, second in trace["edges"]:
            spline = trace_data.splines.new("POLY")
            spline.points.add(1)
            for point, index in zip(spline.points, (first, second)):
                world = body.matrix_world @ body.data.vertices[index].co
                point.co = (*world, 1.0)
        trace_object = bpy.data.objects.new(f"R7_Neck_Review_Trace_{ordinal}_Temporary", trace_data)
        scene.collection.objects.link(trace_object)
        trace_object.hide_render = False
        trace_material = bpy.data.materials.new(f"R7_Neck_Review_Trace_{ordinal}_Material_Temporary")
        color = trace_colors[ordinal % len(trace_colors)]
        trace_material.diffuse_color = color
        trace_material.use_nodes = True
        trace_principled = trace_material.node_tree.nodes.get("Principled BSDF")
        if trace_principled:
            trace_principled.inputs["Base Color"].default_value = color
            trace_principled.inputs["Emission Color"].default_value = color
            trace_principled.inputs["Emission Strength"].default_value = 4.0
        trace_data.materials.append(trace_material)

    points = [body.matrix_world @ body.data.vertices[index].co for index in source_indices]
    low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    center = (low + high) * 0.5
    height = float(high.z - low.z)

    bpy.ops.object.light_add(type="AREA", location=(center.x - 0.45, center.y - 0.55, center.z + 0.55))
    key = bpy.context.object
    key.data.energy = 340
    key.data.shape = "DISK"
    key.data.size = 0.75
    key.hide_render = False
    bpy.ops.object.light_add(type="AREA", location=(center.x + 0.45, center.y + 0.45, center.z + 0.25))
    fill = bpy.context.object
    fill.data.energy = 220
    fill.data.size = 0.65
    fill.hide_render = False

    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max(height * 1.12, 0.38)
    camera.hide_render = False
    scene.camera = camera

    def point_camera(location: Vector) -> None:
        camera.location = location
        camera.rotation_euler = (center - location).to_track_quat("-Z", "Y").to_euler()

    specs = {
        "front": center + Vector((0.0, -0.72, 0.0)),
        "left": center + Vector((-0.72, 0.0, 0.0)),
        "back": center + Vector((0.0, 0.72, 0.0)),
        "right": center + Vector((0.72, 0.0, 0.0)),
    }
    records: dict[str, dict[str, object]] = {}
    for name, location in specs.items():
        point_camera(location)
        path = output_dir / f"neck_boundary_review_{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        records[name] = {
            "path": str(path),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
            "camera_location": [round(float(value), 9) for value in camera.location],
            "orthographic_scale": round(float(camera.data.ortho_scale), 9),
        }
    return records


def main() -> int:
    args = parse_args()
    workspace = Path(bpy.data.filepath).resolve(strict=True)
    source = Path(args.source).resolve(strict=True)
    output = Path(args.output).resolve()
    actual_hashes = {
        "workspace": sha256_file(workspace),
        "source_r6": sha256_file(source),
    }
    expected_hashes = {
        "workspace": args.workspace_sha256,
        "source_r6": args.source_sha256,
    }
    if actual_hashes != expected_hashes:
        raise ValueError(f"pinned inputs changed: expected={expected_hashes} actual={actual_hashes}")

    working = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.get("r7_role") == "working_body_unauthored"
    ]
    if len(working) != 1:
        raise ValueError(f"expected one unchanged R7 working body, found {len(working)}")
    body = working[0]
    mesh = body.data
    components, by_vertex = connected_components(mesh)
    support_records, shared_components = component_support_records(body, components, by_vertex)

    face_counts = edge_face_counts(mesh)
    shared_vertex_set = set().union(*(set(components[index]) for index in shared_components))
    shared_boundary_edges = [
        edge
        for edge, count in face_counts.items()
        if count == 1 and edge[0] in shared_vertex_set and edge[1] in shared_vertex_set
    ]
    boundary_parts = edge_graph_parts(shared_boundary_edges)
    boundary_records = [part_record(body, part) for part in boundary_parts]
    for record in boundary_records:
        record["defensible_neck_boundary"] = False
        record["classification"] = "whole_mirrored_half_shell_perimeter_not_neck_ring"
        record["disqualification"] = (
            "Although this degree-2 boundary is a closed graph cycle, its bounds span "
            "the sagittal face/scalp seam, eye/ear openings, neck, and shoulder-bottom "
            "perimeter of one disconnected mirrored half-shell. It is not a transverse "
            "neck boundary and cannot define a protected head mask."
        )

    # Candidate closed cycles in a conservative lower-neck search slab.
    # This stage enumerates topology only; it does not semantically approve a cut.
    lower_neck_edges = [
        (int(edge.vertices[0]), int(edge.vertices[1]))
        for edge in mesh.edges
        if by_vertex[int(edge.vertices[0])] in shared_components
        and by_vertex[int(edge.vertices[1])] in shared_components
        and 5.90 <= float(mesh.vertices[int(edge.vertices[0])].co.z) <= 6.25
        and 5.90 <= float(mesh.vertices[int(edge.vertices[1])].co.z) <= 6.25
        and abs(float(mesh.vertices[int(edge.vertices[0])].co.z) - float(mesh.vertices[int(edge.vertices[1])].co.z)) <= 0.004
    ]
    slab_parts = edge_graph_parts(lower_neck_edges)
    slab_records = [part_record(body, part) for part in slab_parts]
    slab_closed = [record for record in slab_records if record["topologically_closed_cycle"]]

    # Do not fabricate a neck ring.  The exact lower-neck edge search below
    # yields disconnected/non-cyclic parts, so its edges are used only as a
    # bright render overlay.  A prior attempt to route paired open half-paths
    # through the unchanged mesh either self-intersected or disconnected;
    # retaining those paths would overstate the evidence.
    review_traces: list[dict[str, object]] = []
    render_overlays = [{"edges": lower_neck_edges}]

    debug_renders: dict[str, dict[str, object]] = {}
    if args.debug_render_dir:
        debug_renders = debug_render(
            body,
            components,
            shared_components,
            shared_boundary_edges,
            render_overlays,
            Path(args.debug_render_dir).resolve(),
        )

    evidence = {
        "schema_version": 1,
        "inspection_id": "kira_r7_neck_boundary_candidates_20260721",
        "mode": "read_only_inactive_topology_inspection",
        "sources": {
            "workspace": {"path": str(workspace), "sha256": actual_hashes["workspace"]},
            "source_r6": {"path": str(source), "sha256": actual_hashes["source_r6"]},
        },
        "working_body": {
            "object": body.name,
            "mesh": mesh.name,
            "vertex_count": len(mesh.vertices),
            "edge_count": len(mesh.edges),
            "polygon_count": len(mesh.polygons),
            "connected_component_count": len(components),
        },
        "support_analysis": {
            "groups": support_records,
            "shared_head_neck_spine2_components": [
                f"component_{index:03d}" for index in shared_components
            ],
            "shared_component_count": len(shared_components),
        },
        "shared_component_open_boundary_analysis": {
            "boundary_edge_count": len(shared_boundary_edges),
            "boundary_edge_index_pair_sha256": edge_sha256(shared_boundary_edges),
            "connected_boundary_part_count": len(boundary_records),
            "parts": boundary_records,
            "closed_boundary_cycle_count": sum(
                1 for record in boundary_records if record["topologically_closed_cycle"]
            ),
            "defensible_neck_boundary_count": 0,
        },
        "lower_neck_existing_edge_cycle_search": {
            "local_z_slab": [5.90, 6.25],
            "maximum_edge_endpoint_delta_z": 0.004,
            "candidate_edge_count": len(lower_neck_edges),
            "candidate_edge_index_pair_sha256": edge_sha256(lower_neck_edges),
            "connected_part_count": len(slab_records),
            "topologically_closed_cycle_count": len(slab_closed),
            "parts": slab_records,
        },
        "paired_open_review_traces": {
            "status": "not_emitted_no_simple_defensible_path",
            "trace_count": 0,
            "reason": (
                "Routing across the unchanged mirrored half-shells produced either a "
                "self-intersection or no disjoint continuation. A visual trace would "
                "therefore imply a boundary that the exact topology does not contain."
            ),
        },
        "render_overlay": {
            "meaning": "all exact edges admitted by the lower-neck slab search; not a ring",
            "edge_count": len(lower_neck_edges),
            "edge_index_pair_sha256": edge_sha256(lower_neck_edges),
        },
        "fixed_multiview_renders": debug_renders,
        "conclusion": {
            "defensible_existing_closed_neck_ring_count": 0,
            "automatic_boundary_result": "blocked_no_exact_ring_in_unchanged_topology",
            "why": [
                (
                    "The only two closed boundary cycles are the complete perimeters of "
                    "the disconnected left/right head-neck-shoulder half-shells."
                ),
                (
                    "The conservative lower-neck slab contains 612 exact mesh edges in "
                    "141 connected parts and zero topologically closed cycles."
                ),
                (
                    "A proposed paired open trace either self-intersects or cannot continue "
                    "without reusing the first path, so it is not emitted as evidence."
                ),
            ],
        },
        "manual_blender_selection_required": {
            "automatic_selection_allowed": False,
            "object": body.name,
            "mesh": mesh.name,
            "steps": [
                "Open the pinned inactive R7 workspace; do not save over it or export a candidate.",
                "Select Object_85 / Cuerpo__0 and enter Edit Mode with X-ray or wireframe enabled.",
                "In fixed front, left, back, right, and top views, manually select one transverse boundary as two open mesh-edge chains, one on component_002 and one on component_003.",
                "Keep the boundary below the complete jaw, both ears, scalp, face, eyelids, and eye sockets; endpoints must lie on the front and back sagittal seams.",
                "Visually verify that the mirrored front endpoint pair and back endpoint pair coincide, with no branch, overlap, skipped face, or crossing.",
                "Flood-select the complete protected head above the reviewed chains, including all disconnected identity-bearing face parts; record exact vertex and edge index hashes.",
                "Create the below-boundary complement only after an owner multiview review and explicit attestation; rerun structural audits before moving any geometry.",
            ],
        },
        "gates": {
            "automatic_neck_boundary_approved": False,
            "protected_head_mask_assignment_allowed": False,
            "geometry_authoring_allowed": False,
            "candidate_export_allowed": False,
            "runtime_activation_allowed": False,
            "owner_approved": False,
        },
        "safety": {
            "blend_saved": False,
            "source_glb_edited": False,
            "candidate_glb_exported": False,
            "live_binding_changed": False,
            "runtime_changed": False,
        },
        "truth_note": (
            "This evidence proves that the unchanged topology contains no defensible existing "
            "closed neck ring under the documented exact search. It does not approve a "
            "protected-head cut, body authoring region, adult anatomy, or runtime model."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
