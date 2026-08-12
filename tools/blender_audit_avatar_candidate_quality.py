"""Read-only Blender geometry audit for one staged avatar candidate.

Run with Blender, for example::

    blender --background --python tools/blender_audit_avatar_candidate_quality.py -- \
      --input candidate.glb --output geometry_audit.json

The input is imported into an empty in-memory scene and is never saved or
exported.  The JSON deliberately omits raw object, material, and bone names;
names are used transiently only to classify body/eye/control roles.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import bpy  # type: ignore
from mathutils import Vector  # type: ignore


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--reviewed-intentional-boundary-loops",
        type=int,
        default=0,
        help="Exact number independently reviewed as intentional; defaults fail closed.",
    )
    parser.add_argument(
        "--socket-fit-measurement-passed",
        action="store_true",
        help="Set only when a separate measured socket-fit process has passed.",
    )
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (
        bpy.data.meshes,
        bpy.data.armatures,
        bpy.data.actions,
        bpy.data.materials,
        bpy.data.images,
    ):
        for block in list(collection):
            collection.remove(block)


def normalized(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")


def bounds_for_object(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    return low, high


def vector(values: Vector) -> list[float]:
    return [round(float(value), 6) for value in values]


def connected_components(
    vertex_count: int, polygons: list[list[int]]
) -> tuple[int, set[int]]:
    parent = list(range(vertex_count))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    used: set[int] = set()
    for polygon in polygons:
        if not polygon:
            continue
        used.update(polygon)
        for index in polygon[1:]:
            union(polygon[0], index)
    return len({find(index) for index in used}), used


def topology_counts(vertex_count: int, polygons: list[list[int]]) -> dict[str, int]:
    edge_use: dict[tuple[int, int], int] = {}
    collapsed_faces = 0
    for indices in polygons:
        if len(set(indices)) < 3:
            collapsed_faces += 1
            continue
        for position, first in enumerate(indices):
            edge = tuple(sorted((first, indices[(position + 1) % len(indices)])))
            edge_use[edge] = edge_use.get(edge, 0) + 1

    boundary_edges = [edge for edge, count in edge_use.items() if count == 1]
    non_manifold_edges = sum(1 for count in edge_use.values() if count > 2)
    adjacency: dict[int, set[int]] = {}
    for left, right in boundary_edges:
        adjacency.setdefault(left, set()).add(right)
        adjacency.setdefault(right, set()).add(left)
    seen: set[int] = set()
    boundary_loops = 0
    open_chains = 0
    for seed in adjacency:
        if seed in seen:
            continue
        stack = [seed]
        component: set[int] = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(adjacency.get(current, ()))
        seen.update(component)
        if component and all(len(adjacency.get(index, ())) == 2 for index in component):
            boundary_loops += 1
        else:
            open_chains += 1
    islands, used = connected_components(vertex_count, polygons)
    return {
        "surface_island_count": islands,
        "unused_vertex_count": vertex_count - len(used),
        "boundary_edge_count": len(boundary_edges),
        "boundary_loop_count": boundary_loops,
        "open_boundary_chain_count": open_chains,
        "non_manifold_edge_count": non_manifold_edges,
        "collapsed_face_count": collapsed_faces,
    }


def edge_audit(obj: bpy.types.Object) -> dict[str, int | float]:
    polygons = [[int(value) for value in polygon.vertices] for polygon in obj.data.polygons]
    raw = topology_counts(len(obj.data.vertices), polygons)

    low, high = bounds_for_object(obj)
    tolerance = max(float(value) for value in high - low) * 1e-6
    tolerance = max(tolerance, 1e-9)
    representative_for_key: dict[tuple[int, int, int], int] = {}
    welded_index: dict[int, int] = {}
    for vertex in obj.data.vertices:
        point = obj.matrix_world @ vertex.co
        key = tuple(int(round(float(point[axis]) / tolerance)) for axis in range(3))
        representative = representative_for_key.setdefault(key, len(representative_for_key))
        welded_index[vertex.index] = representative
    welded_polygons = [
        [welded_index[index] for index in polygon]
        for polygon in polygons
    ]
    welded = topology_counts(len(representative_for_key), welded_polygons)
    geometric_degenerate_faces = sum(
        1
        for polygon in obj.data.polygons
        if len(set(int(value) for value in polygon.vertices)) < 3
        or float(polygon.area) <= 1e-12
    )
    return {
        "raw_index_surface_island_count": raw["surface_island_count"],
        "raw_index_boundary_edge_count": raw["boundary_edge_count"],
        "positional_weld_tolerance": round(tolerance, 9),
        "positional_weld_vertex_count": len(representative_for_key),
        "surface_island_count": welded["surface_island_count"],
        "unused_vertex_count": welded["unused_vertex_count"],
        "boundary_edge_count": welded["boundary_edge_count"],
        "boundary_loop_count": welded["boundary_loop_count"],
        "open_boundary_chain_count": welded["open_boundary_chain_count"],
        "non_manifold_edge_count": welded["non_manifold_edge_count"],
        "collapsed_face_count_after_positional_weld": welded["collapsed_face_count"],
        "degenerate_face_count": geometric_degenerate_faces,
    }


def weight_audit(obj: bpy.types.Object) -> dict[str, int]:
    unweighted = 0
    bad_sums = 0
    maximum = 0
    too_many = 0
    for vertex in obj.data.vertices:
        weights = [float(item.weight) for item in vertex.groups if float(item.weight) > 1e-7]
        if not weights:
            unweighted += 1
            continue
        maximum = max(maximum, len(weights))
        if len(weights) > 4:
            too_many += 1
        if abs(sum(weights) - 1.0) > 1e-3:
            bad_sums += 1
    return {
        "unweighted_vertex_count": unweighted,
        "weight_sum_out_of_tolerance_count": bad_sums,
        "maximum_positive_influences_per_vertex": maximum,
        "vertices_over_four_influences": too_many,
    }


def has_armature_modifier(obj: bpy.types.Object) -> bool:
    return any(modifier.type == "ARMATURE" and modifier.object for modifier in obj.modifiers)


def role_for_name(name: str) -> str:
    value = normalized(name)
    if "sclera" in value:
        return "sclera"
    if "iris" in value:
        return "iris"
    if "pupil" in value:
        return "pupil"
    if "eyelid" in value or "eye_lid" in value:
        return "eyelid"
    if "catchlight" in value:
        return "catchlight"
    if any(token in value for token in ("hair", "braid", "ponytail", "bangs")):
        return "hair"
    if any(
        token in value
        for token in (
            "shirt",
            "top",
            "tunic",
            "trouser",
            "pants",
            "skirt",
            "dress",
            "robe",
            "shoe",
            "sock",
            "garment",
            "clothing",
        )
    ):
        return "garment"
    if any(token in value for token in ("debug", "guide", "icosphere", "primitive", "helper")):
        return "debug_or_helper"
    return "unclassified"


def side_for_name(name: str) -> str:
    value = normalized(name)
    if "left" in value or value.startswith("l_"):
        return "left"
    if "right" in value or value.startswith("r_"):
        return "right"
    return ""


def parent_chain_reaches_rig_or_head(obj: bpy.types.Object) -> bool:
    current = obj.parent
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if current.type == "ARMATURE":
            if obj.parent_type == "BONE":
                return "head" in normalized(obj.parent_bone) or "eye" in normalized(obj.parent_bone)
            return True
        current = current.parent
    return has_armature_modifier(obj)


def principled_parameters(material: bpy.types.Material | None) -> dict[str, object]:
    if material is None or not material.use_nodes or material.node_tree is None:
        return {"principled": False}
    node = next(
        (item for item in material.node_tree.nodes if item.type == "BSDF_PRINCIPLED"),
        None,
    )
    if node is None:
        return {"principled": False}

    def scalar(name: str, default: float = 0.0) -> float:
        socket = node.inputs.get(name)
        return round(float(socket.default_value), 6) if socket is not None else default

    color_socket = node.inputs.get("Base Color")
    color = (
        [round(float(value), 6) for value in color_socket.default_value[:4]]
        if color_socket is not None
        else []
    )
    return {
        "principled": True,
        "base_color": color,
        "roughness": scalar("Roughness", 1.0),
        "metallic": scalar("Metallic", 0.0),
        "ior": scalar("IOR", 1.45),
        "alpha": scalar("Alpha", 1.0),
    }


def material_audit(
    body: bpy.types.Object | None,
    meshes: list[bpy.types.Object],
) -> dict[str, object]:
    role_components: dict[str, list[bpy.types.Object]] = {
        "sclera": [],
        "iris": [],
        "pupil": [],
    }
    for obj in meshes:
        role = role_for_name(obj.name)
        if role in role_components:
            role_components[role].append(obj)

    def component_material_pass(objects: list[bpy.types.Object]) -> bool:
        return bool(
            objects
            and all(
                len(obj.material_slots) >= 1
                and obj.material_slots[0].material is not None
                and principled_parameters(obj.material_slots[0].material).get("principled") is True
                for obj in objects
            )
        )

    all_materials = {
        slot.material
        for obj in meshes
        for slot in obj.material_slots
        if slot.material is not None
    }
    materialless = [
        obj
        for obj in meshes
        if not any(slot.material is not None for slot in obj.material_slots)
    ]
    pbr_count = sum(
        principled_parameters(material).get("principled") is True
        for material in all_materials
    )
    body_material_count = (
        sum(slot.material is not None for slot in body.material_slots) if body is not None else 0
    )
    eye_component_materials_pass = all(
        component_material_pass(role_components[role])
        for role in ("sclera", "iris", "pupil")
    )
    return {
        "material_count": len(all_materials),
        "principled_material_count": pbr_count,
        "materialless_mesh_count": len(materialless),
        "all_renderable_meshes_have_materials": len(materialless) == 0,
        "body_material_count": body_material_count,
        "body_has_principled_material": bool(
            body is not None
            and any(
                slot.material is not None
                and principled_parameters(slot.material).get("principled") is True
                for slot in body.material_slots
            )
        ),
        "eye_role_component_counts": {
            role: len(objects) for role, objects in role_components.items()
        },
        "all_sclera_iris_pupil_components_have_principled_materials": eye_component_materials_pass,
        "eye_material_visual_realism_proven": False,
        "raw_material_names_or_parameters_disclosed": False,
    }


def control_role_counts(objects: list[bpy.types.Object]) -> dict[str, int]:
    names: list[str] = [obj.name for obj in objects]
    for obj in objects:
        if obj.type == "ARMATURE":
            names.extend(bone.name for bone in obj.data.bones)
    roles = {"eyelid_control": set(), "gaze_control": set(), "blink_control": set()}
    for name in names:
        value = normalized(name)
        if "eyelid" in value or "eye_lid" in value:
            roles["eyelid_control"].add(name)
        if any(token in value for token in ("gaze", "look_target", "eye_target", "lookat")):
            roles["gaze_control"].add(name)
        if "blink" in value:
            roles["blink_control"].add(name)
    return {key: len(value) for key, value in roles.items()}


def eye_audit(meshes: list[bpy.types.Object], objects: list[bpy.types.Object]) -> dict[str, object]:
    roles: dict[str, list[bpy.types.Object]] = {
        "sclera": [],
        "iris": [],
        "pupil": [],
        "eyelid": [],
        "catchlight": [],
    }
    for obj in meshes:
        role = role_for_name(obj.name)
        if role in roles:
            roles[role].append(obj)
    counts: dict[str, int] = {key: len(value) for key, value in roles.items()}
    counts.update(control_role_counts(objects))
    eye_components = [obj for values in roles.values() for obj in values]

    paired_centers: dict[str, list[float]] = {}
    sclera_by_side = {
        side_for_name(obj.name): obj for obj in roles["sclera"] if side_for_name(obj.name)
    }
    if set(sclera_by_side) == {"left", "right"}:
        for side, obj in sclera_by_side.items():
            low, high = bounds_for_object(obj)
            paired_centers[side] = vector((low + high) * 0.5)
    symmetry_passed = False
    if set(paired_centers) == {"left", "right"}:
        left = Vector(paired_centers["left"])
        right = Vector(paired_centers["right"])
        symmetry_passed = bool(
            left.x * right.x < 0
            and abs(abs(left.x) - abs(right.x)) <= 0.004
            and abs(left.y - right.y) <= 0.004
            and abs(left.z - right.z) <= 0.004
        )
    return {
        "role_counts": counts,
        "bilateral_sclera_centers": paired_centers,
        "bilateral_symmetry_sanity_passed": symmetry_passed,
        "all_eye_components_bound_to_head_or_eye_controls": bool(
            eye_components and all(parent_chain_reaches_rig_or_head(obj) for obj in eye_components)
        ),
        # Geometry alone cannot establish eyelid clearance.  The command-line
        # flag is an explicit hand-off from a separate measured fit process.
        "socket_fit_measurement_passed": False,
    }


def main() -> int:
    args = parse_args()
    source = Path(args.input).resolve(strict=True)
    output = Path(args.output).resolve()
    if source.suffix.lower() != ".glb":
        raise SystemExit("input must be GLB")
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(source))
    bpy.context.view_layer.update()
    objects = list(bpy.context.scene.objects)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    skinned = [obj for obj in meshes if has_armature_modifier(obj)]
    body = max(skinned, key=lambda obj: len(obj.data.vertices), default=None)
    if body is None:
        primary_body: dict[str, object] = {
            "present": False,
            "surface_island_count": 0,
            "boundary_loop_count": 0,
            "reviewed_intentional_boundary_loop_count": int(
                args.reviewed_intentional_boundary_loops
            ),
            "open_boundary_chain_count": 0,
            "non_manifold_edge_count": 0,
            "degenerate_face_count": 0,
            "unweighted_vertex_count": 0,
            "weight_sum_out_of_tolerance_count": 0,
            "maximum_positive_influences_per_vertex": 0,
        }
        body_low = body_high = Vector((0.0, 0.0, 0.0))
    else:
        body_low, body_high = bounds_for_object(body)
        primary_body = {
            "present": True,
            "vertex_count": len(body.data.vertices),
            "triangle_count": sum(max(0, len(poly.vertices) - 2) for poly in body.data.polygons),
            **edge_audit(body),
            **weight_audit(body),
            "reviewed_intentional_boundary_loop_count": int(
                args.reviewed_intentional_boundary_loops
            ),
        }

    nonbody = [obj for obj in meshes if obj is not body]
    role_counts: dict[str, int] = {}
    unclassified = []
    oversized = []
    body_height = max(float(body_high.z - body_low.z), 1e-9)
    for obj in nonbody:
        role = role_for_name(obj.name)
        role_counts[role] = role_counts.get(role, 0) + 1
        if role in {"unclassified", "debug_or_helper"}:
            unclassified.append(obj)
            low, high = bounds_for_object(obj)
            if max(float(value) for value in high - low) > body_height * 0.55:
                oversized.append(obj)

    eyes = eye_audit(meshes, objects)
    eyes["socket_fit_measurement_passed"] = bool(args.socket_fit_measurement_passed)
    report = {
        "schema_version": 1,
        "audit_mode": "read_only_blender_geometry_v1",
        "candidate_sha256": sha256_file(source),
        "blender_version": bpy.app.version_string,
        "privacy": {
            "source_path_disclosed": False,
            "raw_object_material_or_bone_names_disclosed": False,
            "input_modified": False,
            "render_created": False,
        },
        "scene": {
            "mesh_count": len(meshes),
            "skinned_mesh_count": len(skinned),
            "armature_count": sum(obj.type == "ARMATURE" for obj in objects),
            "animation_count": len(bpy.data.actions),
        },
        "primary_body": primary_body,
        "neutral_axis_and_grounding": {
            "finite_coordinates": all(
                math.isfinite(float(value)) for value in (*body_low, *body_high)
            ),
            "body_bounds_low": vector(body_low),
            "body_bounds_high": vector(body_high),
            "body_extent": vector(body_high - body_low),
            "lowest_body_z": round(float(body_low.z), 6),
            "ground_reference": "candidate_local_z_zero",
            "ground_contact_dynamically_proven": False,
        },
        "nonbody_geometry": {
            "mesh_count": len(nonbody),
            "role_counts": role_counts,
            "unclassified_mesh_count": len(unclassified),
            "oversized_unclassified_mesh_count": len(oversized),
            "raw_names_disclosed": False,
        },
        "materials": material_audit(body, meshes),
        "eyes": eyes,
        "stable_working_rig_proven": False,
        "anatomical_completeness_proven": False,
        "owner_approved": False,
        "runtime_activation_allowed": False,
        "truth_note": (
            "This read-only audit measures geometry, weights, role counts, and neutral bounds. "
            "It does not prove anatomy, stable motion, eye realism, or owner approval."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output), "candidate_sha256": report["candidate_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
