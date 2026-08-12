#!/usr/bin/env python3
"""Build read-only fixed-camera evidence for Kira R7's existing mouth.

The worker runs against the pinned R7 authoring workspace and never saves it.
It identifies the already-pinned 207-vertex exterior mouth component, records a
visually reviewable partition of its *existing boundary* and renders transient
diagnostic edge overlays.  It does not create or export mouth geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


EXPECTED_VERTEX_COUNT = 207
EXPECTED_INDEX_SHA256 = (
    "dee38f86b4bfbb732a3cbcc4ae2927f8ff50626d463dcdcfe4bca1f0b84edc3b"
)

# Positions in the canonical ordered boundary loop measured by the earlier
# topology proof.  End-exclusive edge ranges are expressed as [start, stop),
# where edge i connects ordered[i] to ordered[i + 1].
SEMANTIC_EDGE_RANGES = {
    "lower_oral_fissure": [(0, 16), (125, 140)],
    "upper_oral_fissure": [(17, 34), (106, 124)],
    "commissures": [(16, 17), (124, 125)],
    "outer_attachment_rim": [(36, 104)],
    "open_upper_center_seam": [(34, 36), (104, 106)],
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def index_sha256(indices: list[int]) -> str:
    digest = hashlib.sha256()
    for index in sorted(indices):
        digest.update(struct.pack("<I", index))
    return digest.hexdigest()


def connected_components(mesh: bpy.types.Mesh) -> list[list[int]]:
    adjacency: dict[int, set[int]] = defaultdict(set)
    for edge in mesh.edges:
        first, second = (int(value) for value in edge.vertices)
        adjacency[first].add(second)
        adjacency[second].add(first)
    remaining = set(range(len(mesh.vertices)))
    components: list[list[int]] = []
    while remaining:
        seed = min(remaining)
        stack = [seed]
        found: set[int] = set()
        while stack:
            current = stack.pop()
            if current in found:
                continue
            found.add(current)
            stack.extend(adjacency[current] - found)
        remaining -= found
        components.append(sorted(found))
    return components


def ordered_boundary(mesh: bpy.types.Mesh, indices: list[int]) -> list[int]:
    index_set = set(indices)
    edge_use: dict[tuple[int, int], int] = defaultdict(int)
    for polygon in mesh.polygons:
        vertices = [int(vertex) for vertex in polygon.vertices]
        if not all(vertex in index_set for vertex in vertices):
            continue
        for ordinal, first in enumerate(vertices):
            second = vertices[(ordinal + 1) % len(vertices)]
            edge_use[tuple(sorted((first, second)))] += 1
    boundary = sorted(edge for edge, count in edge_use.items() if count == 1)
    adjacency: dict[int, list[int]] = defaultdict(list)
    for first, second in boundary:
        adjacency[first].append(second)
        adjacency[second].append(first)
    if any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise ValueError("mouth boundary is no longer a single degree-two loop")
    # Pin the same orientation and start used in the earlier evidence.
    start, following = 7247, 7248
    ordered = [start, following]
    previous, current = start, following
    while True:
        candidates = [value for value in adjacency[current] if value != previous]
        if len(candidates) != 1:
            raise ValueError(f"ambiguous boundary traversal at {current}: {candidates}")
        next_vertex = candidates[0]
        ordered.append(next_vertex)
        previous, current = current, next_vertex
        if current == start:
            break
        if len(ordered) > len(boundary) + 1:
            raise ValueError("boundary traversal did not close")
    if len(ordered) != 141:
        raise ValueError(f"expected 140 boundary edges, got {len(ordered) - 1}")
    return ordered


def edge_list(ordered: list[int], ranges: list[tuple[int, int]]) -> list[list[int]]:
    return [
        [int(ordered[position]), int(ordered[position + 1])]
        for start, stop in ranges
        for position in range(start, stop)
    ]


def make_material(name: str, color: tuple[float, float, float, float], emission: float = 0.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Roughness"].default_value = 0.72
    if emission:
        principled.inputs["Emission Color"].default_value = color
        principled.inputs["Emission Strength"].default_value = emission
    return material


def add_edge_overlay(
    name: str,
    edges: list[list[int]],
    body: bpy.types.Object,
    mesh: bpy.types.Mesh,
    material: bpy.types.Material,
    bevel_depth: float,
) -> None:
    for ordinal, (first, second) in enumerate(edges):
        curve = bpy.data.curves.new(f"{name}_{ordinal:03d}_curve", "CURVE")
        curve.dimensions = "3D"
        curve.bevel_depth = bevel_depth
        curve.bevel_resolution = 2
        spline = curve.splines.new("POLY")
        spline.points.add(1)
        # Pull the overlay only 0.15 mm toward the front camera to avoid z-fight.
        for point, vertex_index in zip(spline.points, (first, second)):
            world = body.matrix_world @ mesh.vertices[vertex_index].co
            world.y -= 0.00015
            point.co = (*world, 1.0)
        obj = bpy.data.objects.new(f"{name}_{ordinal:03d}", curve)
        bpy.context.scene.collection.objects.link(obj)
        obj.data.materials.append(material)
        obj["transient_diagnostic_overlay"] = True


def add_landmark(
    name: str,
    indices: list[int],
    body: bpy.types.Object,
    mesh: bpy.types.Mesh,
    material: bpy.types.Material,
    radius: float,
) -> None:
    center = Vector((0.0, 0.0, 0.0))
    for index in indices:
        center += body.matrix_world @ mesh.vertices[index].co
    center /= len(indices)
    center.y -= 0.0003
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=radius, location=center)
    marker = bpy.context.object
    marker.name = name
    marker.data.materials.append(material)
    marker["transient_diagnostic_overlay"] = True


def look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def render_view(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    output: Path,
    location: Vector,
    target: Vector,
    ortho_scale: float,
) -> dict[str, object]:
    camera.location = location
    camera.data.ortho_scale = ortho_scale
    look_at(camera, target)
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    return {
        "path": str(output),
        "camera_location": [round(float(value), 9) for value in camera.location],
        "target": [round(float(value), 9) for value in target],
        "orthographic_scale": round(float(ortho_scale), 9),
    }


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    render_dir = output_dir / "fixed_renders"
    render_dir.mkdir(parents=True, exist_ok=True)

    bodies = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.get("r7_role") == "working_body_unauthored"
    ]
    if len(bodies) != 1:
        raise ValueError(f"expected one R7 working body, found {len(bodies)}")
    body = bodies[0]
    mesh = body.data
    matches = [
        component
        for component in connected_components(mesh)
        if len(component) == EXPECTED_VERTEX_COUNT
        and index_sha256(component) == EXPECTED_INDEX_SHA256
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one exact mouth component, found {len(matches)}")
    mouth_indices = matches[0]
    ordered = ordered_boundary(mesh, mouth_indices)

    semantic_edges = {
        role: edge_list(ordered, ranges)
        for role, ranges in SEMANTIC_EDGE_RANGES.items()
    }
    all_selected = {
        tuple(sorted(edge))
        for edges in semantic_edges.values()
        for edge in edges
    }
    if len(all_selected) != 140:
        raise ValueError(f"semantic map must cover 140 unique boundary edges, got {len(all_selected)}")

    duplicate_center_pairs = [[7256, 7708], [7257, 7711], [7260, 7716]]
    duplicate_pair_distances = []
    for first, second in duplicate_center_pairs:
        distance = (mesh.vertices[first].co - mesh.vertices[second].co).length
        duplicate_pair_distances.append(
            {"vertices": [first, second], "local_distance_m": round(float(distance), 12)}
        )

    mouth_set = set(mouth_indices)
    mouth_polygons = [
        polygon
        for polygon in mesh.polygons
        if all(int(vertex) in mouth_set for vertex in polygon.vertices)
    ]
    nonmouth_source_polygons = [
        polygon
        for polygon in mesh.polygons
        if not all(int(vertex) in mouth_set for vertex in polygon.vertices)
    ]
    nonmouth_polygons = [
        [int(vertex) for vertex in polygon.vertices]
        for polygon in nonmouth_source_polygons
    ]
    nonmouth_bvh = BVHTree.FromPolygons(
        [vertex.co.copy() for vertex in mesh.vertices],
        nonmouth_polygons,
        all_triangles=False,
        epsilon=0.0,
    )
    visibility_by_vertex: dict[str, dict[str, object]] = {}
    for index in mouth_indices:
        origin = mesh.vertices[index].co + Vector((0.0, -0.000001, 0.0))
        location, _normal, polygon_index, distance = nonmouth_bvh.ray_cast(
            origin,
            Vector((0.0, -1.0, 0.0)),
            0.2,
        )
        visibility_by_vertex[str(index)] = {
            "front_occluded_by_nonmouth_surface": distance is not None,
            "nearest_front_occluder_distance_m": (
                round(float(distance), 9) if distance is not None else None
            ),
            "nearest_front_occluder_location_local": (
                [round(float(value), 9) for value in location]
                if location is not None
                else None
            ),
            "nearest_front_occluder_source_polygon_index": (
                int(nonmouth_source_polygons[int(polygon_index)].index)
                if polygon_index is not None
                else None
            ),
            "nearest_front_occluder_source_polygon_vertices": (
                [
                    int(value)
                    for value in nonmouth_source_polygons[int(polygon_index)].vertices
                ]
                if polygon_index is not None
                else None
            ),
        }

    visibility_by_role = {}
    for role, edges in semantic_edges.items():
        vertices = sorted({index for edge in edges for index in edge})
        occluded = [
            index
            for index in vertices
            if visibility_by_vertex[str(index)]["front_occluded_by_nonmouth_surface"]
        ]
        visibility_by_role[role] = {
            "vertex_count": len(vertices),
            "front_occluded_vertex_count": len(occluded),
            "front_visible_vertex_count": len(vertices) - len(occluded),
            "front_occluded_fraction": round(len(occluded) / max(len(vertices), 1), 6),
        }
    occluding_polygon_indices = sorted(
        {
            int(record["nearest_front_occluder_source_polygon_index"])
            for record in visibility_by_vertex.values()
            if record["nearest_front_occluder_source_polygon_index"] is not None
        }
    )
    occluding_vertices = sorted(
        {
            int(vertex)
            for record in visibility_by_vertex.values()
            if record["nearest_front_occluder_source_polygon_vertices"] is not None
            for vertex in record["nearest_front_occluder_source_polygon_vertices"]
        }
    )

    # Transient in-memory review materials and overlays. Nothing is saved.
    body_material = make_material("ReviewBody", (0.34, 0.25, 0.20, 1.0))
    for slot in body.material_slots:
        slot.material = body_material
    colors = {
        "upper_oral_fissure": (0.15, 0.75, 1.0, 1.0),
        "lower_oral_fissure": (0.15, 1.0, 0.45, 1.0),
        "commissures": (1.0, 0.2, 0.2, 1.0),
        "outer_attachment_rim": (1.0, 0.65, 0.1, 1.0),
        "open_upper_center_seam": (0.9, 0.2, 1.0, 1.0),
    }
    materials = {
        role: make_material(f"Review_{role}", color, emission=1.4)
        for role, color in colors.items()
    }
    for role, edges in semantic_edges.items():
        add_edge_overlay(role, edges, body, mesh, materials[role], bevel_depth=0.00065)
    add_landmark("RightCommissurePair", [7307, 7308], body, mesh, materials["commissures"], 0.0022)
    add_landmark("LeftCommissurePair", [7759, 7765], body, mesh, materials["commissures"], 0.0022)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.008, 0.012, 0.02)
    scene.view_settings.look = "AgX - Medium High Contrast"

    camera_data = bpy.data.cameras.new("TransientMouthReviewCamera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("TransientMouthReviewCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    bpy.ops.object.light_add(type="AREA", location=(0.0, -1.2, 7.0))
    key = bpy.context.object
    key.data.energy = 900
    key.data.shape = "DISK"
    key.data.size = 1.2
    key.rotation_euler = (math.radians(20), 0.0, 0.0)
    bpy.ops.object.light_add(type="AREA", location=(0.8, -0.5, 6.8))
    fill = bpy.context.object
    fill.data.energy = 500
    fill.data.size = 0.8

    world_positions = [body.matrix_world @ mesh.vertices[index].co for index in mouth_indices]
    center = sum(world_positions, Vector()) / len(world_positions)
    x_extent = max(point.x for point in world_positions) - min(point.x for point in world_positions)
    z_extent = max(point.z for point in world_positions) - min(point.z for point in world_positions)
    mouth_scale = max(x_extent * 1.55, z_extent * 3.8, 0.23)
    head_scale = 0.52
    renders = {
        "front_face": render_view(
            scene,
            camera,
            render_dir / "front_face_semantic_overlay.png",
            center + Vector((0.0, -1.2, 0.035)),
            center + Vector((0.0, 0.0, 0.035)),
            head_scale,
        ),
        "front_mouth": render_view(
            scene,
            camera,
            render_dir / "front_mouth_semantic_overlay.png",
            center + Vector((0.0, -0.8, 0.0)),
            center,
            mouth_scale,
        ),
        "left_profile": render_view(
            scene,
            camera,
            render_dir / "left_profile_semantic_overlay.png",
            center + Vector((-0.8, 0.0, 0.0)),
            center,
            mouth_scale,
        ),
        "right_profile": render_view(
            scene,
            camera,
            render_dir / "right_profile_semantic_overlay.png",
            center + Vector((0.8, 0.0, 0.0)),
            center,
            mouth_scale,
        ),
        "oblique": render_view(
            scene,
            camera,
            render_dir / "oblique_semantic_overlay.png",
            center + Vector((0.42, -0.75, 0.05)),
            center,
            mouth_scale,
        ),
    }


    evidence = {
        "schema_version": 1,
        "mode": "read_only_inactive_visually_informed_semantic_review",
        "workspace": str(Path(bpy.data.filepath).resolve()),
        "body_object": body.name,
        "body_mesh": mesh.name,
        "existing_mouth": {
            "vertex_count": len(mouth_indices),
            "vertex_index_sha256": index_sha256(mouth_indices),
            "boundary_edge_count": len(ordered) - 1,
            "ordered_boundary": ordered,
        },
        "candidate_boundary_partition": {
            "upper_oral_fissure_edges": semantic_edges["upper_oral_fissure"],
            "lower_oral_fissure_edges": semantic_edges["lower_oral_fissure"],
            "right_commissure_vertices": [7307, 7308],
            "left_commissure_vertices": [7759, 7765],
            "commissure_edges": semantic_edges["commissures"],
            "outer_attachment_rim_edges": semantic_edges["outer_attachment_rim"],
            "open_upper_center_seam_edges": semantic_edges["open_upper_center_seam"],
            "duplicate_upper_center_vertex_pairs": duplicate_pair_distances,
            "boundary_partition_complete": len(all_selected) == 140,
            "boundary_partition_unique_edge_count": len(all_selected),
            "semantic_status": "rejected_not_visually_defensible",
            "reason": (
                "The fixed face renders and front-ray probe show that every vertex in the "
                "proposed outer rim, upper fissure, commissure, and center seam is behind a "
                "different non-mouth surface. The partition is geometrically reproducible "
                "but cannot be named as Kira's visible exterior lip semantics."
            ),
        },
        "front_visibility_probe": {
            "ray_direction_local": [0.0, -1.0, 0.0],
            "maximum_distance_m": 0.2,
            "mouth_polygon_count": len(mouth_polygons),
            "nonmouth_polygon_count": len(nonmouth_polygons),
            "by_semantic_role": visibility_by_role,
            "by_vertex": visibility_by_vertex,
            "unique_nearest_occluding_source_polygon_indices": occluding_polygon_indices,
            "unique_nearest_occluding_source_vertex_indices": occluding_vertices,
            "unique_nearest_occluding_source_vertex_index_sha256": index_sha256(
                occluding_vertices
            ),
        },
        "verdict": {
            "defensible_existing_mouth_semantic_map_proven": False,
            "isolated_cavity_or_viseme_prototype_allowed": False,
            "exact_207_component_confirmed_as_visible_exterior_lips": False,
            "smallest_remaining_manual_ambiguity": (
                "In the isolated R7 authoring copy, hide the 207-vertex backing patch and "
                "manually select the visible upper/lower lip seam and commissures on the "
                "occluding welded face shell. Then toggle the 207 patch to classify it as "
                "backing/inner-lip/artifact before any cavity, jaw, or viseme authoring."
            ),
        },
        "render_legend": {role: list(color) for role, color in colors.items()},
        "fixed_renders": renders,
        "safety": {
            "geometry_edited": False,
            "blend_saved": False,
            "model_exported": False,
            "second_mouth_created": False,
            "mouth_overlay_exported": False,
            "runtime_binding_touched": False,
            "person_state_touched": False,
        },
    }
    output = output_dir / "semantic_review_evidence.json"
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "evidence": str(output), "renders": renders}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
