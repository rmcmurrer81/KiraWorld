#!/usr/bin/env python3
"""Author an isolated, inactive visible-lip shape-key trial for Kira R7.

Only vertices already belonging to the visible face shell are deformed.  The
known 207-vertex hidden backing patch is identified and held byte-for-byte at
its Basis coordinates in every key.  No mesh object, mouth overlay, cavity, or
runtime export is added to the saved candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from collections import defaultdict, deque
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


HIDDEN_VERTEX_COUNT = 207
HIDDEN_INDEX_SHA256 = (
    "dee38f86b4bfbb732a3cbcc4ae2927f8ff50626d463dcdcfe4bca1f0b84edc3b"
)

# Manually reviewed on the isolated R7 authoring copy after hiding the exact
# 207-vertex backing patch.  Every consecutive pair must remain a mesh boundary
# edge and every vertex must belong to the front-occluding face shell.
VISIBLE_RIM_PATHS = {
    "upper_right": [
        7066, 7069, 7070, 7063, 7064, 7045, 7046, 7036,
        7037, 7038, 7049, 7050, 7057, 7058, 7088, 7079,
    ],
    "upper_left": [
        7523, 7525, 7524, 7519, 7518, 7501, 7500, 7495,
        7494, 7493, 7507, 7506, 7513, 7512, 7543, 7530,
    ],
    "lower_right": [
        7140, 7139, 7138, 7231, 7229, 7228, 7125,
        7128, 7133, 7150, 7154, 7162, 7161,
    ],
    "lower_left": [
        7595, 7596, 7597, 7685, 7683, 7684, 7580,
        7581, 7584, 7604, 7606, 7619, 7616,
    ],
}

TRIAL_KEY_NAMES = {
    "KW_VISIBLE_LIP_OPEN_REVIEW",
    "KW_VISEME_O_REVIEW",
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--candidate-blend", required=True)
    return parser.parse_args(argv)


def index_sha256(indices: list[int]) -> str:
    digest = hashlib.sha256()
    for index in sorted(indices):
        digest.update(struct.pack("<I", index))
    return digest.hexdigest()


def edge_sha256(edges: list[tuple[int, int]]) -> str:
    digest = hashlib.sha256()
    for first, second in sorted(tuple(sorted(edge)) for edge in edges):
        digest.update(struct.pack("<II", first, second))
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


def mesh_adjacency(mesh: bpy.types.Mesh) -> dict[int, set[int]]:
    adjacency: dict[int, set[int]] = defaultdict(set)
    for edge in mesh.edges:
        first, second = (int(value) for value in edge.vertices)
        adjacency[first].add(second)
        adjacency[second].add(first)
    return adjacency


def neighborhood_weights(
    seeds: set[int],
    adjacency: dict[int, set[int]],
    excluded: set[int],
    maximum_ring: int = 3,
) -> dict[int, float]:
    """Return compact topological falloff around a pinned visible rim."""
    ring_weight = {0: 1.0, 1: 0.68, 2: 0.38, 3: 0.16}
    distances = {index: 0 for index in seeds}
    queue = deque(sorted(seeds))
    while queue:
        current = queue.popleft()
        distance = distances[current]
        if distance >= maximum_ring:
            continue
        for neighbor in adjacency[current]:
            if neighbor in excluded or neighbor in distances:
                continue
            distances[neighbor] = distance + 1
            queue.append(neighbor)
    return {index: ring_weight[distance] for index, distance in distances.items()}


def point_record(mesh: bpy.types.Mesh, index: int) -> dict[str, object]:
    vertex = mesh.vertices[index]
    return {
        "index": index,
        "co": [round(float(value), 9) for value in vertex.co],
        "normal": [round(float(value), 9) for value in vertex.normal],
    }


def validate_visible_rims(
    mesh: bpy.types.Mesh,
    hidden: set[int],
) -> dict[str, object]:
    edge_use: dict[tuple[int, int], int] = defaultdict(int)
    for polygon in mesh.polygons:
        vertices = [int(value) for value in polygon.vertices]
        for ordinal, first in enumerate(vertices):
            second = vertices[(ordinal + 1) % len(vertices)]
            edge_use[tuple(sorted((first, second)))] += 1

    path_edges: dict[str, list[tuple[int, int]]] = {}
    all_vertices: set[int] = set()
    for role, path in VISIBLE_RIM_PATHS.items():
        if len(path) != len(set(path)):
            raise ValueError(f"{role} contains a duplicate vertex")
        if set(path) & hidden:
            raise ValueError(f"{role} overlaps the hidden backing patch")
        edges = [tuple(sorted((first, second))) for first, second in zip(path, path[1:])]
        missing = [edge for edge in edges if edge_use.get(edge) != 1]
        if missing:
            raise ValueError(f"{role} contains non-boundary edges: {missing}")
        path_edges[role] = edges
        all_vertices.update(path)

    upper = set(VISIBLE_RIM_PATHS["upper_right"] + VISIBLE_RIM_PATHS["upper_left"])
    lower = set(VISIBLE_RIM_PATHS["lower_right"] + VISIBLE_RIM_PATHS["lower_left"])
    if upper & lower:
        raise ValueError("upper and lower visible lip rims overlap")
    upper_normal_min = min(-float(mesh.vertices[index].normal.z) for index in upper)
    lower_normal_min = min(float(mesh.vertices[index].normal.z) for index in lower)
    if upper_normal_min < 0.70:
        raise ValueError(f"upper visible rim normal proof failed: {upper_normal_min}")
    if lower_normal_min < 0.90:
        raise ValueError(f"lower visible rim normal proof failed: {lower_normal_min}")

    nonhidden_polygons = [
        [int(value) for value in polygon.vertices]
        for polygon in mesh.polygons
        if not all(int(value) in hidden for value in polygon.vertices)
    ]
    hidden_polygons = [
        [int(value) for value in polygon.vertices]
        for polygon in mesh.polygons
        if all(int(value) in hidden for value in polygon.vertices)
    ]
    hidden_bvh = BVHTree.FromPolygons(
        [vertex.co.copy() for vertex in mesh.vertices],
        hidden_polygons,
        all_triangles=False,
        epsilon=0.0,
    )
    backing_distances: dict[str, float | None] = {}
    for index in sorted(all_vertices):
        origin = mesh.vertices[index].co + Vector((0.0, 0.000001, 0.0))
        _location, _normal, _polygon, distance = hidden_bvh.ray_cast(
            origin, Vector((0.0, 1.0, 0.0)), 0.08
        )
        backing_distances[str(index)] = round(float(distance), 9) if distance is not None else None

    return {
        "paths": {role: list(path) for role, path in VISIBLE_RIM_PATHS.items()},
        "path_edges": {
            role: [list(edge) for edge in edges] for role, edges in path_edges.items()
        },
        "path_edge_sha256": {
            role: edge_sha256(edges) for role, edges in path_edges.items()
        },
        "visible_rim_vertex_count": len(all_vertices),
        "visible_rim_vertex_index_sha256": index_sha256(sorted(all_vertices)),
        "overlaps_hidden_backing": False,
        "all_consecutive_path_edges_are_single_use_mesh_boundaries": True,
        "upper_min_negative_normal_z": round(upper_normal_min, 9),
        "lower_min_positive_normal_z": round(lower_normal_min, 9),
        "existing_hidden_backing_distance_by_visible_rim_vertex_m": backing_distances,
        "nonhidden_polygon_count": len(nonhidden_polygons),
        "hidden_backing_polygon_count": len(hidden_polygons),
        "path_vertex_records": {
            role: [point_record(mesh, index) for index in path]
            for role, path in VISIBLE_RIM_PATHS.items()
        },
    }


def center_taper(mesh: bpy.types.Mesh, index: int) -> float:
    normalized = min(abs(float(mesh.vertices[index].co.x)) / 0.092, 1.0)
    return max(0.14, (1.0 - normalized) ** 0.42)


def create_shape_key(
    body: bpy.types.Object,
    name: str,
    upper_weights: dict[int, float],
    lower_weights: dict[int, float],
    hidden: set[int],
    mode: str,
) -> dict[str, object]:
    mesh = body.data
    key = body.shape_key_add(name=name, from_mix=False)
    basis = body.data.shape_keys.key_blocks["Basis"]
    moved: dict[int, Vector] = {}

    def add_delta(index: int, delta: Vector) -> None:
        if index in hidden:
            raise ValueError(f"shape-key deformation reached hidden backing vertex {index}")
        moved[index] = moved.get(index, Vector()) + delta

    for index, ring_weight in upper_weights.items():
        taper = center_taper(mesh, index)
        if mode == "open":
            delta = Vector((0.0, -0.0020, 0.0120)) * (ring_weight * taper)
        elif mode == "round":
            point = mesh.vertices[index].co
            delta = Vector((-float(point.x) * 0.28, -0.0060, 0.0090)) * (
                ring_weight * taper
            )
        else:
            raise ValueError(mode)
        add_delta(index, delta)

    for index, ring_weight in lower_weights.items():
        taper = center_taper(mesh, index)
        if mode == "open":
            delta = Vector((0.0, -0.0040, -0.0450)) * (ring_weight * taper)
        elif mode == "round":
            point = mesh.vertices[index].co
            delta = Vector((-float(point.x) * 0.32, -0.0080, -0.0280)) * (
                ring_weight * taper
            )
        else:
            raise ValueError(mode)
        add_delta(index, delta)

    for index, delta in moved.items():
        key.data[index].co = basis.data[index].co + delta
    key.value = 0.0

    hidden_max = max(
        (key.data[index].co - basis.data[index].co).length for index in hidden
    )
    displacement = {
        index: (key.data[index].co - basis.data[index].co).length for index in moved
    }
    return {
        "name": name,
        "mode": mode,
        "moved_vertex_count": len(moved),
        "moved_vertex_index_sha256": index_sha256(sorted(moved)),
        "maximum_displacement_m": round(max(displacement.values()), 9),
        "minimum_nonzero_displacement_m": round(min(displacement.values()), 9),
        "hidden_backing_maximum_displacement_m": round(float(hidden_max), 12),
    }


def key_center_gap(body: bpy.types.Object, key_name: str | None) -> dict[str, float]:
    if key_name is None:
        points = body.data.shape_keys.key_blocks["Basis"].data
    else:
        points = body.data.shape_keys.key_blocks[key_name].data
    upper_z = sum(float(points[index].co.z) for index in (7066, 7523)) / 2.0
    lower_z = sum(float(points[index].co.z) for index in (7140, 7595)) / 2.0
    return {
        "upper_center_z_m": round(upper_z, 9),
        "lower_center_z_m": round(lower_z, 9),
        "vertical_separation_m": round(upper_z - lower_z, 9),
    }


def make_material(
    name: str,
    color: tuple[float, float, float, float],
    roughness: float,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Roughness"].default_value = roughness
    return material


def look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def set_key(body: bpy.types.Object, key_name: str | None) -> None:
    for key in body.data.shape_keys.key_blocks:
        if key.name in TRIAL_KEY_NAMES:
            key.value = 1.0 if key.name == key_name else 0.0
    bpy.context.view_layer.update()


def render_view(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    body: bpy.types.Object,
    output: Path,
    key_name: str | None,
    location: Vector,
    target: Vector,
    ortho_scale: float,
) -> dict[str, object]:
    set_key(body, key_name)
    camera.location = location
    camera.data.ortho_scale = ortho_scale
    look_at(camera, target)
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    return {
        "path": str(output),
        "shape_key": key_name or "Basis",
        "camera_location": [round(float(value), 9) for value in location],
        "target": [round(float(value), 9) for value in target],
        "orthographic_scale": ortho_scale,
    }


def configure_transient_render(
    body: bpy.types.Object,
    hidden: set[int],
) -> tuple[bpy.types.Scene, bpy.types.Object]:
    scene = bpy.context.scene
    for obj in list(scene.objects):
        if obj != body:
            obj.hide_render = True
    body.hide_render = False

    skin = make_material("KW_Review_Skin_Transient", (0.55, 0.33, 0.24, 1.0), 0.62)
    cavity = make_material("KW_Existing_Backing_Transient", (0.055, 0.012, 0.009, 1.0), 0.83)
    body.data.materials.clear()
    body.data.materials.append(skin)
    body.data.materials.append(cavity)
    for polygon in body.data.polygons:
        polygon.material_index = (
            1 if all(int(value) in hidden for value in polygon.vertices) else 0
        )

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.012, 0.016, 0.025)
    scene.view_settings.look = "AgX - Medium High Contrast"

    camera_data = bpy.data.cameras.new("KW_Transient_Visible_Lip_Camera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("KW_Transient_Visible_Lip_Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    bpy.ops.object.light_add(type="AREA", location=(-0.55, -1.1, 7.05))
    key = bpy.context.object
    key.name = "KW_Transient_Key"
    key.data.energy = 1050
    key.data.size = 0.75
    look_at(key, Vector((0.0, -0.37, 6.60)))
    bpy.ops.object.light_add(type="AREA", location=(0.65, -0.65, 6.55))
    fill = bpy.context.object
    fill.name = "KW_Transient_Fill"
    fill.data.energy = 620
    fill.data.size = 0.65
    look_at(fill, Vector((0.0, -0.37, 6.59)))
    bpy.ops.object.light_add(type="AREA", location=(0.0, 0.15, 6.72))
    rim = bpy.context.object
    rim.name = "KW_Transient_Rim"
    rim.data.energy = 500
    rim.data.size = 0.55
    look_at(rim, Vector((0.0, -0.37, 6.63)))
    return scene, camera


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    render_dir = output_dir / "fixed_renders"
    candidate_blend = Path(args.candidate_blend).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    render_dir.mkdir(parents=True, exist_ok=True)
    candidate_blend.parent.mkdir(parents=True, exist_ok=True)

    source_workspace = Path(bpy.data.filepath).resolve()
    bodies = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.get("r7_role") == "working_body_unauthored"
    ]
    if len(bodies) != 1:
        raise ValueError(f"expected one R7 working body, found {len(bodies)}")
    body = bodies[0]
    mesh = body.data
    mesh.update()
    topology_before = {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "objects": len(bpy.data.objects),
        "mesh_objects": sum(1 for obj in bpy.data.objects if obj.type == "MESH"),
    }

    hidden_matches = [
        component
        for component in connected_components(mesh)
        if len(component) == HIDDEN_VERTEX_COUNT
        and index_sha256(component) == HIDDEN_INDEX_SHA256
    ]
    if len(hidden_matches) != 1:
        raise ValueError(f"expected one exact hidden backing component, got {len(hidden_matches)}")
    hidden = set(hidden_matches[0])
    rim_evidence = validate_visible_rims(mesh, hidden)

    existing_shape_keys = (
        [key.name for key in body.data.shape_keys.key_blocks]
        if body.data.shape_keys is not None
        else []
    )
    if any(name in existing_shape_keys for name in TRIAL_KEY_NAMES):
        raise ValueError(f"trial shape keys already exist in source: {existing_shape_keys}")
    if body.data.shape_keys is None:
        basis = body.shape_key_add(name="Basis", from_mix=False)
    else:
        basis = body.data.shape_keys.key_blocks.get("Basis")
        if basis is None:
            raise ValueError(f"existing shape-key stack has no Basis: {existing_shape_keys}")
    if len(basis.data) != len(mesh.vertices):
        raise ValueError("Basis shape-key point count does not match mesh")

    adjacency = mesh_adjacency(mesh)
    upper_core = set(VISIBLE_RIM_PATHS["upper_right"] + VISIBLE_RIM_PATHS["upper_left"])
    lower_core = set(VISIBLE_RIM_PATHS["lower_right"] + VISIBLE_RIM_PATHS["lower_left"])
    upper_weights = neighborhood_weights(upper_core, adjacency, hidden | lower_core)
    lower_weights = neighborhood_weights(lower_core, adjacency, hidden | upper_core)
    overlap = set(upper_weights) & set(lower_weights)
    # Where compact support touches at the commissures, retain the stronger role
    # only. This avoids summing opposed vertical deltas onto the same vertex.
    for index in sorted(overlap):
        if upper_weights[index] >= lower_weights[index]:
            del lower_weights[index]
        else:
            del upper_weights[index]

    shape_keys = [
        create_shape_key(
            body,
            "KW_VISIBLE_LIP_OPEN_REVIEW",
            upper_weights,
            lower_weights,
            hidden,
            "open",
        ),
        create_shape_key(
            body,
            "KW_VISEME_O_REVIEW",
            upper_weights,
            lower_weights,
            hidden,
            "round",
        ),
    ]
    for record in shape_keys:
        if record["name"] == "KW_VISIBLE_LIP_OPEN_REVIEW":
            record["review_disposition"] = (
                "visible_same_mesh_open_shape_engineering_proof_owner_review_pending"
            )
        elif record["name"] == "KW_VISEME_O_REVIEW":
            record["review_disposition"] = (
                "provisional_shape_not_visually_distinct_enough_for_final_o"
            )
    gaps = {
        "Basis": key_center_gap(body, None),
        "KW_VISIBLE_LIP_OPEN_REVIEW": key_center_gap(
            body, "KW_VISIBLE_LIP_OPEN_REVIEW"
        ),
        "KW_VISEME_O_REVIEW": key_center_gap(body, "KW_VISEME_O_REVIEW"),
    }
    if gaps["KW_VISIBLE_LIP_OPEN_REVIEW"]["vertical_separation_m"] < 0.045:
        raise ValueError(f"open key did not create measurable separation: {gaps}")
    if any(item["hidden_backing_maximum_displacement_m"] != 0.0 for item in shape_keys):
        raise ValueError("hidden backing moved in a visible-lip shape key")

    topology_after_keys = {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "objects": len(bpy.data.objects),
        "mesh_objects": sum(1 for obj in bpy.data.objects if obj.type == "MESH"),
    }
    if topology_after_keys != topology_before:
        raise ValueError(
            f"shape-key authoring changed topology/object counts: {topology_before} -> {topology_after_keys}"
        )
    body["kw_trial_status"] = "inactive_owner_review_only"
    body["kw_trial_source_workspace"] = str(source_workspace)
    body["kw_second_mouth_created"] = False
    body["kw_runtime_export_allowed"] = False
    set_key(body, None)
    bpy.ops.wm.save_as_mainfile(filepath=str(candidate_blend), check_existing=False)

    # Rendering additions and the cavity-color diagnostic are made only after
    # the isolated candidate has been saved, so they are not authored assets.
    scene, camera = configure_transient_render(body, hidden)
    mouth_center = body.matrix_world @ Vector((0.0, -0.37, 6.582))
    face_center = body.matrix_world @ Vector((0.0, -0.36, 6.72))
    front_mouth_camera = mouth_center + Vector((0.0, -1.0, 0.015))
    front_face_camera = face_center + Vector((0.0, -1.35, 0.02))
    oblique_camera = mouth_center + Vector((0.36, -0.8, 0.035))
    renders = {
        "basis_face": render_view(
            scene,
            camera,
            body,
            render_dir / "basis_front_face.png",
            None,
            front_face_camera,
            face_center,
            0.50,
        ),
        "open_face": render_view(
            scene,
            camera,
            body,
            render_dir / "open_front_face.png",
            "KW_VISIBLE_LIP_OPEN_REVIEW",
            front_face_camera,
            face_center,
            0.50,
        ),
        "basis_mouth": render_view(
            scene,
            camera,
            body,
            render_dir / "basis_mouth_closeup.png",
            None,
            front_mouth_camera,
            mouth_center,
            0.23,
        ),
        "open_mouth": render_view(
            scene,
            camera,
            body,
            render_dir / "open_mouth_closeup.png",
            "KW_VISIBLE_LIP_OPEN_REVIEW",
            front_mouth_camera,
            mouth_center,
            0.23,
        ),
        "round_mouth": render_view(
            scene,
            camera,
            body,
            render_dir / "viseme_o_mouth_closeup.png",
            "KW_VISEME_O_REVIEW",
            front_mouth_camera,
            mouth_center,
            0.23,
        ),
        "open_oblique": render_view(
            scene,
            camera,
            body,
            render_dir / "open_oblique.png",
            "KW_VISIBLE_LIP_OPEN_REVIEW",
            oblique_camera,
            mouth_center,
            0.24,
        ),
    }

    evidence = {
        "schema_version": 1,
        "mode": "inactive_isolated_same_mesh_visible_lip_shape_key_trial",
        "source_workspace": str(source_workspace),
        "candidate_blend": str(candidate_blend),
        "body_object": body.name,
        "body_mesh": mesh.name,
        "topology": {
            "before": topology_before,
            "after_shape_keys_before_save": topology_after_keys,
            "unchanged": topology_before == topology_after_keys,
        },
        "hidden_backing": {
            "vertex_count": len(hidden),
            "vertex_index_sha256": index_sha256(sorted(hidden)),
            "deformed_by_any_shape_key": False,
            "render_only_dark_material_used_after_candidate_save": True,
        },
        "visible_lip_rim_proof": rim_evidence,
        "shape_keys": shape_keys,
        "preexisting_shape_keys_preserved": existing_shape_keys,
        "center_separation": gaps,
        "fixed_renders": renders,
        "engineering_verdict": {
            "same_existing_face_mesh_deformed": True,
            "visible_rim_motion_geometrically_proven": True,
            "visible_open_shape_proven_in_fixed_renders": True,
            "o_viseme_final_quality_proven": False,
            "o_viseme_disposition": (
                "provisional_only; fixed render is subtly different but not "
                "distinctly round enough to call a finished O viseme"
            ),
            "rendered_review_required": True,
            "owner_approval_recorded": False,
            "runtime_ready": False,
            "promotion_allowed": False,
        },
        "safety": {
            "source_workspace_saved_or_overwritten": False,
            "isolated_candidate_saved": True,
            "second_mouth_created": False,
            "mesh_object_added_to_saved_candidate": False,
            "vertex_or_face_topology_changed": False,
            "runtime_model_exported": False,
            "runtime_binding_touched": False,
            "person_state_touched": False,
            "activation_attempted": False,
        },
    }
    evidence_path = output_dir / "topology_and_shape_key_evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "candidate": str(candidate_blend),
        "evidence": str(evidence_path),
        "center_separation": gaps,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
