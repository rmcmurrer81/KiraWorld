#!/usr/bin/env python3
"""Package the licensed BlackProject source-native nails as 20 audited parts.

This is the bounded fallback after two procedural open-recess attempts. It does
not reshape nails or regenerate the body. Blender's loose-part separation keeps
the enrolled source geometry, materials, UVs, vertex weights, and modifiers,
while exact terminal-digit classification makes each component independently
auditable and importable by the private R19 assembly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import blender_probe_blackproject_r19_natural_nails as probe  # noqa: E402
from tools import blender_avatar_natural_nail_delivery_v3 as nail_v3  # noqa: E402
from tools import blender_profiled_adult_candidate_components as component_v1  # noqa: E402


SOURCE_SHA256 = probe.SOURCE_SHA256
ALIGNMENT_SHA256 = probe.ALIGNMENT_SHA256
SOURCE_NAIL_MESHES = probe.SOURCE_NAIL_MESHES
HAND_SURFACE_MESH = probe.HAND_SURFACE_MESH
FOOT_SURFACE_MESH = probe.FOOT_SURFACE_MESH
METHOD_ID = "blackproject_cc_by_4_source_native_nail_fallback_v1"


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.users == 0:
            bpy.data.collections.remove(collection)


def _mesh_map(objects: Iterable[Any]) -> dict[str, Any]:
    return {obj.data.name: obj for obj in objects if obj.type == "MESH"}


def _world_point_token(obj: Any, vertex_index: int) -> bytes:
    point = obj.matrix_world @ obj.data.vertices[vertex_index].co
    return struct.pack("<3d", *(float(value) for value in point))


def _canonical_cycle(tokens: list[bytes]) -> bytes:
    candidates = []
    for sequence in (tokens, list(reversed(tokens))):
        for offset in range(len(sequence)):
            candidates.append(b"".join(sequence[offset:] + sequence[:offset]))
    return min(candidates)


def _source_data_fingerprint(objects: Iterable[Any]) -> dict[str, Any]:
    objects = list(objects)
    vertex_tokens: list[bytes] = []
    face_tokens: list[bytes] = []
    uv_tokens: list[bytes] = []
    weight_tokens: list[bytes] = []
    for obj in objects:
        mesh = obj.data
        points = [_world_point_token(obj, index) for index in range(len(mesh.vertices))]
        vertex_tokens.extend(points)
        material_names = [material.name if material else "" for material in mesh.materials]
        for polygon in mesh.polygons:
            polygon_points = [points[int(index)] for index in polygon.vertices]
            material_name = (
                material_names[int(polygon.material_index)]
                if int(polygon.material_index) < len(material_names)
                else ""
            )
            face_tokens.append(
                material_name.encode("utf-8")
                + b"\0"
                + _canonical_cycle(polygon_points)
            )
        for uv_layer in mesh.uv_layers:
            for loop_index, loop in enumerate(mesh.loops):
                uv = uv_layer.data[loop_index].uv
                uv_tokens.append(
                    uv_layer.name.encode("utf-8")
                    + b"\0"
                    + points[int(loop.vertex_index)]
                    + struct.pack("<2d", float(uv[0]), float(uv[1]))
                )
        group_names = {group.index: group.name for group in obj.vertex_groups}
        for vertex in mesh.vertices:
            assignments = sorted(
                (
                    group_names[int(item.group)],
                    float(item.weight),
                )
                for item in vertex.groups
                if float(item.weight) > 0.0
            )
            payload = points[int(vertex.index)] + b"\0"
            for group_name, weight in assignments:
                payload += group_name.encode("utf-8") + b"\0" + struct.pack(
                    "<d", weight
                )
            weight_tokens.append(payload)

    def digest_rows(rows: list[bytes]) -> str:
        digest = hashlib.sha256()
        for row in sorted(rows):
            digest.update(struct.pack("<Q", len(row)))
            digest.update(row)
        return digest.hexdigest()

    return {
        "object_count": len(objects),
        "vertex_count": sum(len(obj.data.vertices) for obj in objects),
        "polygon_count": sum(len(obj.data.polygons) for obj in objects),
        "loop_count": sum(len(obj.data.loops) for obj in objects),
        "world_vertex_multiset_sha256": digest_rows(vertex_tokens),
        "face_geometry_and_material_assignment_sha256": digest_rows(face_tokens),
        "uv_assignment_sha256": digest_rows(uv_tokens),
        "vertex_group_weight_assignment_sha256": digest_rows(weight_tokens),
    }


def _split_loose_parts(source_obj: Any) -> list[Any]:
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="DESELECT")
    source_obj.select_set(True)
    bpy.context.view_layer.objects.active = source_obj
    before = set(bpy.data.objects)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    created = [obj for obj in bpy.data.objects if obj not in before]
    parts = [source_obj, *created]
    parts = [obj for obj in parts if obj.type == "MESH"]
    if len(parts) != 10:
        raise ValueError(
            f"source-native nail object did not split into ten parts: "
            f"{source_obj.name}={len(parts)}"
        )
    return parts


def _dominant_group(obj: Any) -> tuple[str, dict[str, float]]:
    names = {group.index: group.name for group in obj.vertex_groups}
    totals: dict[str, float] = {}
    for vertex in obj.data.vertices:
        for assignment in vertex.groups:
            name = names[int(assignment.group)]
            totals[name] = totals.get(name, 0.0) + float(assignment.weight)
    if not totals:
        raise ValueError(f"source-native nail component has no weights: {obj.name}")
    return max(totals.items(), key=lambda item: item[1])[0], totals


def _component_frame(obj: Any, kind: str, digit_center: Vector) -> dict[str, Any]:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    array = np.asarray(
        [[float(value) for value in point] for point in points], dtype=np.float64
    )
    centroid_array = array.mean(axis=0)
    centered = array - centroid_array
    covariance = centered.T @ centered / max(1, len(array) - 1)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    outward = Vector(tuple(float(value) for value in eigenvectors[:, 0]))
    preferred = Vector((0.0, -1.0, 0.0)) if kind == "fingernail" else Vector((0.0, 0.0, 1.0))
    if outward.dot(preferred) < 0.0:
        outward = -outward
    outward.normalize()
    centroid = Vector(tuple(float(value) for value in centroid_array))
    longitudinal = centroid - digit_center
    longitudinal = longitudinal - outward * longitudinal.dot(outward)
    if longitudinal.length <= 1.0e-7:
        longitudinal = Vector(tuple(float(value) for value in eigenvectors[:, -1]))
        longitudinal = longitudinal - outward * longitudinal.dot(outward)
    longitudinal.normalize()
    lateral = outward.cross(longitudinal).normalized()
    longitudinal = lateral.cross(outward).normalized()
    return {
        "centroid_world_m": [float(value) for value in centroid],
        "outward_world": [float(value) for value in outward],
        "longitudinal_world": [float(value) for value in longitudinal],
        "lateral_world": [float(value) for value in lateral],
        "pca_eigenvalues_m2": [float(value) for value in eigenvalues],
    }


def _attachment_record(obj: Any, armature: Any, bone_name: str) -> dict[str, Any]:
    group = obj.vertex_groups.get(bone_name)
    group_index = int(group.index) if group is not None else -1
    terminal_weights: list[float] = []
    all_have_terminal = group is not None
    all_unit_terminal_only = group is not None
    other_positive_assignment_count = 0
    for vertex in obj.data.vertices:
        assignments = [item for item in vertex.groups if float(item.weight) > 0.0]
        matches = [item for item in assignments if int(item.group) == group_index]
        if len(matches) != 1:
            all_have_terminal = False
            all_unit_terminal_only = False
            continue
        terminal_weight = float(matches[0].weight)
        terminal_weights.append(terminal_weight)
        other = [item for item in assignments if int(item.group) != group_index]
        other_positive_assignment_count += len(other)
        if abs(terminal_weight - 1.0) > 1.0e-7 or other:
            all_unit_terminal_only = False
    armature_modifiers = [modifier for modifier in obj.modifiers if modifier.type == "ARMATURE"]
    exact_modifier = len(armature_modifiers) == 1 and armature_modifiers[0].object == armature
    return {
        "parent_is_exact_armature": obj.parent == armature,
        "armature_modifier_count": len(armature_modifiers),
        "armature_modifier_targets_exact_rig": exact_modifier,
        "all_vertices_have_expected_terminal_group": all_have_terminal,
        "terminal_weight_minimum": min(terminal_weights) if terminal_weights else None,
        "terminal_weight_maximum": max(terminal_weights) if terminal_weights else None,
        "other_positive_group_assignment_count": other_positive_assignment_count,
        "every_vertex_has_unit_terminal_bone_weight": all_unit_terminal_only,
        "source_weights_preserved_without_rigid_reweighting": True,
        "source_native_following_gate_passed": exact_modifier and all_have_terminal,
    }


def _raw_clearance(body_tree: BVHTree, obj: Any) -> dict[str, Any]:
    distances = []
    for vertex in obj.data.vertices:
        point = obj.matrix_world @ vertex.co
        nearest = body_tree.find_nearest(point, 0.020)
        if nearest[0] is None:
            raise ValueError(f"body clearance query failed: {obj.name}")
        distances.append(float(nearest[3]))
    return {
        "sample_count": len(distances),
        "minimum_unsigned_body_surface_clearance_m": min(distances),
        "maximum_unsigned_body_surface_clearance_m": max(distances),
        "mean_unsigned_body_surface_clearance_m": sum(distances) / len(distances),
    }


def _render(
    scene: Any,
    camera: Any,
    path: Path,
    location: Vector,
    target: Vector,
    scale: float,
) -> None:
    camera.location = location
    camera.data.ortho_scale = scale
    camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def _render_review_set(
    *,
    scene: Any,
    output_dir: Path,
    records: list[dict[str, Any]],
) -> dict[str, str]:
    camera_data = bpy.data.cameras.new("R19_SOURCE_NATIVE_NAIL_CAMERA")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("R19_SOURCE_NATIVE_NAIL_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    depsgraph = bpy.context.evaluated_depsgraph_get()
    views: dict[str, tuple[Vector, Vector, float]] = {}
    for kind, label, full_scale, macro_scale in (
        ("fingernail", "hand", 0.19, 0.155),
        ("toenail", "foot", 0.27, 0.150),
    ):
        for side, side_label in (("L", "left"), ("R", "right")):
            selected = [
                record
                for record in records
                if record["kind"] == kind and record["side"] == side
            ]
            points: list[Vector] = []
            for record in selected:
                obj = bpy.data.objects[str(record["object"])]
                evaluated = obj.evaluated_get(depsgraph)
                mesh = evaluated.to_mesh()
                try:
                    points.extend(
                        evaluated.matrix_world @ vertex.co for vertex in mesh.vertices
                    )
                finally:
                    evaluated.to_mesh_clear()
            low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
            high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
            nail_target = (low + high) * 0.5
            outward = sum(
                (Vector(record["source_component_frame"]["outward_world"]) for record in selected),
                Vector(),
            ).normalized()
            if kind == "fingernail":
                full_target = nail_target + Vector(
                    (0.018 if side == "L" else -0.018, 0.0, 0.003)
                )
                oblique_bias = Vector(
                    (0.20 if side == "L" else -0.20, -0.05, 0.55)
                )
            else:
                full_target = nail_target + Vector((0.0, 0.072, 0.010))
                oblique_bias = Vector(
                    (0.15 if side == "L" else -0.15, -0.55, 0.18)
                )
            oblique = (outward + oblique_bias).normalized()
            views[f"{side_label}_{label}_dorsal_all_five_full"] = (
                full_target + outward * 0.55,
                full_target,
                full_scale,
            )
            views[f"{side_label}_{label}_oblique_all_five_full"] = (
                full_target + oblique * 0.55,
                full_target,
                full_scale,
            )
            views[f"{side_label}_{label}_dorsal_all_five_macro"] = (
                nail_target + outward * 0.45,
                nail_target,
                macro_scale,
            )
            views[f"{side_label}_{label}_oblique_all_five_macro"] = (
                nail_target + oblique * 0.45,
                nail_target,
                macro_scale,
            )
    renders: dict[str, str] = {}
    for name, (location, target, scale) in views.items():
        path = output_dir / f"{name}.png"
        _render(scene, camera, path, location, target, scale)
        renders[name] = path.name
    return renders


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = Path(config["project_root"]).resolve(strict=True)
    source = (root / config["source_path"]).resolve(strict=True)
    alignment_path = (root / config["alignment_path"]).resolve(strict=True)
    output_dir = (root / config["output_dir"]).resolve()
    if sha256_file(source) != SOURCE_SHA256:
        raise ValueError("BlackProject source hash mismatch")
    if sha256_file(alignment_path) != ALIGNMENT_SHA256:
        raise ValueError("BlackProject alignment hash mismatch")
    if output_dir.exists():
        raise FileExistsError(f"append-only attempt already exists: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)

    definitions = probe._inventory()  # noqa: SLF001
    by_bone = {str(row["bone"]): dict(row) for row in definitions}
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    alignment_rows = probe._alignment_rows_by_bone(alignment)  # noqa: SLF001
    if set(by_bone) != set(alignment_rows) or len(by_bone) != 20:
        raise ValueError("exact source-native 20-bone inventory mismatch")

    _clear_scene()
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(source))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    meshes = _mesh_map(imported)
    required = {HAND_SURFACE_MESH, FOOT_SURFACE_MESH, *SOURCE_NAIL_MESHES}
    missing = sorted(required - set(meshes))
    if missing:
        raise ValueError(f"required BlackProject meshes missing: {missing}")
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]
    if len(armatures) != 1 or len(armatures[0].data.bones) != 188:
        raise ValueError("source must expose one exact native 188-joint rig")
    armature = armatures[0]
    pose_position = str(armature.data.pose_position)
    expected_bones = set(by_bone)
    if not expected_bones.issubset({bone.name for bone in armature.data.bones}):
        raise ValueError("one or more exact source-native nail bones is missing")

    body_parts = [meshes[HAND_SURFACE_MESH], meshes[FOOT_SURFACE_MESH]]
    body_before = {
        obj.data.name: nail_v3._mesh_signature(obj) for obj in body_parts  # noqa: SLF001
    }
    rig_before = nail_v3._rig_signature(armature)  # noqa: SLF001
    source_nail_objects = [meshes[name] for name in SOURCE_NAIL_MESHES]
    source_before = _source_data_fingerprint(source_nail_objects)
    source_object_evidence = {
        name: {
            "object": meshes[name].name,
            "mesh_signature_sha256": nail_v3._mesh_signature(meshes[name]),  # noqa: SLF001
            "vertex_count": len(meshes[name].data.vertices),
            "polygon_count": len(meshes[name].data.polygons),
            "material_names": [
                material.name if material else "" for material in meshes[name].data.materials
            ],
            "uv_layer_names": [layer.name for layer in meshes[name].data.uv_layers],
        }
        for name in SOURCE_NAIL_MESHES
    }

    parts: list[Any] = []
    for source_obj in source_nail_objects:
        parts.extend(_split_loose_parts(source_obj))
    if len(parts) != 20:
        raise ValueError(f"exact source-native part count failed: {len(parts)}")

    records: list[dict[str, Any]] = []
    used_bones: set[str] = set()
    object_by_bone: dict[str, Any] = {}
    for obj in parts:
        dominant_bone, group_totals = _dominant_group(obj)
        if dominant_bone not in by_bone or dominant_bone in used_bones:
            raise ValueError(f"invalid or duplicate source-native component: {dominant_bone}")
        used_bones.add(dominant_bone)
        definition = by_bone[dominant_bone]
        alignment_row = alignment_rows[dominant_bone]
        if len(obj.data.vertices) != int(alignment_row["component_vertex_count"]):
            raise ValueError(f"source-native component vertex mismatch: {dominant_bone}")
        desired_name = f"R19_BlackProject_{definition['nail_id']}_source_native"
        obj.name = desired_name
        obj.data.name = f"{desired_name}_Mesh"
        obj["private_owner_review_only"] = True
        obj["inactive_source_native_fallback"] = True
        obj["runtime_activation_allowed"] = False
        obj["source_license"] = "CC BY 4.0"
        obj["source_geometry_reshaped"] = False
        attachment = _attachment_record(obj, armature, dominant_bone)
        frame = _component_frame(
            obj,
            str(definition["kind"]),
            Vector(alignment_row["digit_bounds_m"]["center"]),
        )
        records.append(
            {
                "nail_id": str(definition["nail_id"]),
                "object": obj.name,
                "mesh": obj.data.name,
                "bone": dominant_bone,
                "kind": str(definition["kind"]),
                "side": str(definition["side"]),
                "digit": int(definition["digit"]),
                "nail_component": True,
                "component_provenance": (
                    "licensed_blackproject_cc_by_4_source_native_split"
                ),
                "source_component_vertex_count": len(obj.data.vertices),
                "source_component_polygon_count": len(obj.data.polygons),
                "material_names": [
                    material.name if material else "" for material in obj.data.materials
                ],
                "uv_layer_names": [layer.name for layer in obj.data.uv_layers],
                "dominant_group_weight_totals": group_totals,
                "source_component_frame": frame,
                **attachment,
            }
        )
        object_by_bone[dominant_bone] = obj

    if used_bones != expected_bones:
        raise ValueError("source-native split did not cover exact 20-bone set")
    records.sort(key=lambda row: (row["side"], row["kind"], row["digit"]))
    source_after = _source_data_fingerprint(parts)
    preserved_data_keys = sorted(set(source_before) - {"object_count"})
    source_preserved = all(
        source_after.get(key) == source_before.get(key) for key in preserved_data_keys
    )
    source_object_count_transition_expected = (
        int(source_before["object_count"]) == 2
        and int(source_after["object_count"]) == 20
    )
    source_preserved = source_preserved and source_object_count_transition_expected
    if not source_preserved:
        differences = {
            key: {"before": source_before.get(key), "after": source_after.get(key)}
            for key in sorted(set(source_before) | set(source_after))
            if source_before.get(key) != source_after.get(key)
        }
        raise ValueError(
            "loose-part separation fingerprint mismatch: "
            + json.dumps(differences, sort_keys=True)
        )

    surface_trees = {
        HAND_SURFACE_MESH: component_v1._world_surface_bvh(  # noqa: SLF001
            meshes[HAND_SURFACE_MESH]
        ),
        FOOT_SURFACE_MESH: component_v1._world_surface_bvh(  # noqa: SLF001
            meshes[FOOT_SURFACE_MESH]
        ),
    }
    for record in records:
        obj = bpy.data.objects[str(record["object"])]
        surface_name = (
            HAND_SURFACE_MESH if record["kind"] == "fingernail" else FOOT_SURFACE_MESH
        )
        body = meshes[surface_name]
        record["surface_mesh"] = surface_name
        record["raw_clearance"] = _raw_clearance(surface_trees[surface_name], obj)
        record["raw_exact_intersections"] = probe._exact_mesh_pair_intersections(  # noqa: SLF001
            body, obj, evaluated=False
        )
        record["evaluated_exact_intersections"] = probe._exact_mesh_pair_intersections(  # noqa: SLF001
            body, obj, evaluated=True
        )
        record["raw_exact_no_genuine_penetration"] = (
            int(
                record["raw_exact_intersections"][
                    "exact_genuine_penetration_pair_count"
                ]
            )
            == 0
        )
        record["evaluated_exact_no_genuine_penetration"] = (
            int(
                record["evaluated_exact_intersections"][
                    "exact_genuine_penetration_pair_count"
                ]
            )
            == 0
        )

    body_after = {
        obj.data.name: nail_v3._mesh_signature(obj) for obj in body_parts  # noqa: SLF001
    }
    rig_after = nail_v3._rig_signature(armature)  # noqa: SLF001
    if body_after != body_before or rig_after != rig_before:
        raise ValueError("body or native rig changed during source-native packaging")

    removed_hair = []
    for obj in list(bpy.data.objects):
        if obj.type == "MESH" and obj.data.name.startswith("Hair_"):
            removed_hair.append(obj.data.name)
            bpy.data.objects.remove(obj, do_unlink=True)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.010, 0.016, 0.024)
    if hasattr(scene.view_settings, "look"):
        try:
            scene.view_settings.look = "AgX - Medium High Contrast"
        except TypeError:
            pass
    if hasattr(scene.view_settings, "exposure"):
        scene.view_settings.exposure = -0.55
    probe._add_lights(scene)  # noqa: SLF001
    renders = _render_review_set(scene=scene, output_dir=output_dir, records=records)

    blend_path = output_dir / "r19_blackproject_source_native_nails.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    all_raw_clear = all(row["raw_exact_no_genuine_penetration"] for row in records)
    all_evaluated_clear = all(
        row["evaluated_exact_no_genuine_penetration"] for row in records
    )
    all_follow = all(row["source_native_following_gate_passed"] for row in records)
    all_unit = all(
        row["every_vertex_has_unit_terminal_bone_weight"] for row in records
    )
    validation = {
        "component_count": len(records),
        "fingernail_count": sum(row["kind"] == "fingernail" for row in records),
        "toenail_count": sum(row["kind"] == "toenail" for row in records),
        "all_twenty_present": len(records) == 20,
        "all_object_names_unique": len({row["object"] for row in records}) == 20,
        "all_exact_blackproject_distal_bones_used": {
            row["bone"] for row in records
        }
        == expected_bones,
        "source_geometry_material_uv_and_weights_preserved": source_preserved,
        "all_source_native_following_gates_passed": all_follow,
        "all_vertices_have_unit_terminal_bone_weight": all_unit,
        "all_raw_exact_no_genuine_penetration": all_raw_clear,
        "all_evaluated_exact_no_genuine_penetration": all_evaluated_clear,
        "visual_acceptance_requires_post_render_self_review": True,
    }
    report = {
        "schema_version": 1,
        "mode": "R19_BLACKPROJECT_SOURCE_NATIVE_NAILS_PRIVATE_INACTIVE_FALLBACK",
        "source": {
            "path": str(source.relative_to(root)).replace("\\", "/"),
            "sha256": SOURCE_SHA256,
            "source_unchanged": sha256_file(source) == SOURCE_SHA256,
            "license": "CC BY 4.0",
            "attribution": "BlackProject base female character, CC BY 4.0",
        },
        "alignment_evidence": {
            "path": str(alignment_path.relative_to(root)).replace("\\", "/"),
            "sha256": ALIGNMENT_SHA256,
            "exact_20_bone_set_matched": True,
        },
        "adapter": {
            "method": METHOD_ID,
            "bounded_fallback_reason": (
                "two procedural open-recess repair attempts exhausted; preserve "
                "the licensed source-native natural nails"
            ),
            "generated_short_conformal_curved_shell_count": 20,
            "generated_count_field_semantics": (
                "assembly compatibility count only: these 20 objects are source-native "
                "loose-part splits, not procedurally regenerated shells"
            ),
            "source_native_split_component_count": 20,
            "source_geometry_reshaped_or_regenerated": False,
            "records": records,
            "validation": validation,
        },
        "source_native_preservation": {
            "original_objects": source_object_evidence,
            "before_split": source_before,
            "after_split": source_after,
            "exact_fingerprint_match": source_preserved,
            "fingerprinted_data_keys_required_equal": preserved_data_keys,
            "expected_object_count_transition": {
                "before": 2,
                "after": 20,
                "passed": source_object_count_transition_expected,
            },
            "operation": "Blender separate by loose parts only; object/data rename only",
        },
        "preservation": {
            "hand_and_foot_mesh_signatures_before": body_before,
            "hand_and_foot_mesh_signatures_after": body_after,
            "hand_and_foot_meshes_unchanged": body_after == body_before,
            "native_rig_signature_before": rig_before,
            "native_rig_signature_after": rig_after,
            "native_rig_unchanged": rig_after == rig_before,
            "native_joint_count": len(armature.data.bones),
            "armature_pose_position": pose_position,
            "unrelated_hair_removed_from_probe_only": sorted(removed_hair),
        },
        "renders": renders,
        "blend": {"path": blend_path.name, "sha256": sha256_file(blend_path)},
        "private_inactive_append_only_probe": True,
        "complete_body_candidate_built": False,
        "body_identity_anatomy_or_movement_changed": False,
        "runtime_roster_assignment_or_activation_changed": False,
        "owner_visual_approval_claimed": False,
    }
    report_path = output_dir / "BLACKPROJECT_SOURCE_NATIVE_NAIL_FALLBACK.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    manifest_path = probe._write_manifest(  # noqa: SLF001
        output_dir,
        root,
        [Path(__file__).resolve(), config_path, source, alignment_path],
    )
    print(
        json.dumps(
            {
                "status": "BUILT_PENDING_POST_RENDER_VISUAL_REVIEW",
                "component_count": len(records),
                "source_preserved": source_preserved,
                "all_source_native_following_gates_passed": all_follow,
                "all_unit_terminal_weights": all_unit,
                "all_raw_exact_no_genuine_penetration": all_raw_clear,
                "all_evaluated_exact_no_genuine_penetration": all_evaluated_clear,
                "report": str(report_path),
                "report_sha256": sha256_file(report_path),
                "manifest": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
