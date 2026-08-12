#!/usr/bin/env python3
"""Fail-closed, no-save R24 eyebrow/nail component preparation worker.

The caller must launch Blender with the exact future candidate already loaded
and supply a hash-bound run contract after ``--``.  This worker never opens or
saves a Blend.  It transplants only the two fixed R21 Attempt-02 brow objects,
builds twenty connected-digit nails in memory, validates every bound pose,
renders eight close staging images, writes append-only evidence, and exits.

No output from this worker is a body candidate.  A later separately authorized
integration step would have to consume the evidence and repeat the gates before
any candidate could be saved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.kira_blackproject_nail_topology_v1 import (  # noqa: E402
    expected_nail_inventory,
)
from Core.kira_r24_brow_nail_component_contract_v1 import (  # noqa: E402
    BROW_BINDINGS,
    BROW_SOURCE_PATH,
    EXPECTED_RENDER_KEYS,
    MAXIMUM_CLEARANCE_M,
    MINIMUM_CLEARANCE_M,
    NAIL_BINDINGS,
    OLD_BROW_NAME,
    canonical_json_sha256,
    sha256_file,
    validate_config,
    validate_no_save_transaction,
    validate_pose_gate_matrix,
    validate_render_inventory,
)
from tools import (  # noqa: E402
    blender_avatar_blackproject_weight_constrained_nail_projection_v2 as projector,
)
from tools import blender_avatar_natural_nail_delivery_v3 as nails  # noqa: E402
from tools import blender_author_kira_r21_brow_only_attempt01 as brow_hashes  # noqa: E402
from tools import blender_author_kira_r21_nails_attempt01 as nail_legacy  # noqa: E402
from tools import (  # noqa: E402
    blender_author_kira_r21_nails_attempt03_weight_constrained as nail_review,
)
from tools import (  # noqa: E402
    blender_diagnose_robert_r26_finger5_nail_modifier_stages as exact_audit,
)


EVIDENCE_SCHEMA = "kira.r24.brow_nail_component_no_save_evidence.v1"
FAILURE_SCHEMA = "kira.r24.brow_nail_component_no_save_failure.v1"
NEW_NAIL_PREFIX = "Kira_R24_Natural_Nail"
NATURAL_BED_MATERIAL = "Kira_R24_Natural_Nail_Bed"
NATURAL_EDGE_MATERIAL = "Kira_R24_Subtle_Free_Edge"


class KiraR24PreparationError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def _json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise KiraR24PreparationError(f"JSON root must be an object: {path}")
    return value


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, (Vector, Matrix)):
        return [_plain(item) for item in value]
    if isinstance(value, Path):
        return value.relative_to(ROOT).as_posix()
    if isinstance(value, float):
        if not math.isfinite(value):
            raise KiraR24PreparationError("non-finite evidence value")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return str(value)


def _update_text(digest: "hashlib._Hash", value: str) -> None:
    encoded = str(value).encode("utf-8")
    digest.update(struct.pack("<I", len(encoded)))
    digest.update(encoded)


def _matrix_sha256(matrix: Matrix) -> str:
    digest = hashlib.sha256()
    for row in matrix:
        digest.update(struct.pack("<4d", *map(float, row)))
    return digest.hexdigest()


def _rig_rest_sha256(rig: Any) -> str:
    digest = hashlib.sha256()
    _update_text(digest, rig.name)
    _update_text(digest, rig.data.name)
    for bone in sorted(rig.data.bones, key=lambda item: item.name):
        _update_text(digest, bone.name)
        _update_text(digest, bone.parent.name if bone.parent else "")
        digest.update(struct.pack("<3d", *map(float, bone.head_local)))
        digest.update(struct.pack("<3d", *map(float, bone.tail_local)))
        digest.update(struct.pack("<d", float(bone.roll)))
        digest.update(
            struct.pack(
                "<???",
                bool(bone.use_deform),
                bool(bone.use_connect),
                bool(bone.use_relative_parent),
            )
        )
        for row in bone.matrix_local:
            digest.update(struct.pack("<4d", *map(float, row)))
    return digest.hexdigest()


def _rig_pose_sha256(rig: Any) -> str:
    digest = hashlib.sha256()
    action = rig.animation_data.action if rig.animation_data else None
    _update_text(digest, action.name if action else "")
    for bone in sorted(rig.pose.bones, key=lambda item: item.name):
        _update_text(digest, bone.name)
        _update_text(digest, bone.rotation_mode)
        digest.update(struct.pack("<3d", *map(float, bone.location)))
        digest.update(struct.pack("<4d", *map(float, bone.rotation_quaternion)))
        digest.update(struct.pack("<3d", *map(float, bone.rotation_euler)))
        digest.update(struct.pack("<4d", *map(float, bone.rotation_axis_angle)))
        digest.update(struct.pack("<3d", *map(float, bone.scale)))
        for row in bone.matrix_basis:
            digest.update(struct.pack("<4d", *map(float, row)))
    return digest.hexdigest()


def _custom_properties(owner: Any) -> dict[str, Any]:
    result = {}
    for key in sorted(owner.keys()):
        if key == "_RNA_UI":
            continue
        try:
            result[str(key)] = _plain(owner[key])
        except (AttributeError, ReferenceError, TypeError, ValueError):
            result[str(key)] = {"unreadable": True}
    return result


def _object_scene_record(obj: Any) -> dict[str, Any]:
    action = obj.animation_data.action if obj.animation_data else None
    row: dict[str, Any] = {
        "name": obj.name,
        "type": obj.type,
        "data": obj.data.name if obj.data else None,
        "parent": obj.parent.name if obj.parent else None,
        "parent_type": obj.parent_type,
        "parent_bone": obj.parent_bone,
        "matrix_world_sha256": _matrix_sha256(obj.matrix_world),
        "matrix_basis_sha256": _matrix_sha256(obj.matrix_basis),
        "matrix_parent_inverse_sha256": _matrix_sha256(obj.matrix_parent_inverse),
        "hide_viewport": bool(obj.hide_viewport),
        "hide_render": bool(obj.hide_render),
        "hide_select": bool(obj.hide_select),
        "action": action.name if action else None,
        "collections": sorted(collection.name for collection in obj.users_collection),
        "modifiers": projector.modifier_stack_record(obj),
        "custom_properties": _custom_properties(obj),
    }
    if obj.type == "MESH":
        row.update(
            {
                "geometry_uv_sha256": brow_hashes.mesh_geometry_digest(obj),
                "positive_weight_sha256": brow_hashes.weight_digest(obj),
                "material_slots": [
                    slot.material.name if slot.material else None
                    for slot in obj.material_slots
                ],
            }
        )
    elif obj.type == "ARMATURE":
        row.update(
            {
                "rest_pose_sha256": _rig_rest_sha256(obj),
                "pose_sha256": _rig_pose_sha256(obj),
            }
        )
    return row


def full_scene_state_record(*, excluded_objects: Iterable[str] = ()) -> dict[str, Any]:
    excluded = set(excluded_objects)
    scene = bpy.context.scene
    objects = {
        obj.name: _object_scene_record(obj)
        for obj in sorted(scene.objects, key=lambda item: item.name)
        if obj.name not in excluded
    }
    return {
        "scene": scene.name,
        "frame": int(scene.frame_current),
        "frame_subframe": float(scene.frame_subframe),
        "camera": scene.camera.name if scene.camera and scene.camera.name not in excluded else None,
        "render": {
            "engine": scene.render.engine,
            "resolution_x": int(scene.render.resolution_x),
            "resolution_y": int(scene.render.resolution_y),
            "resolution_percentage": int(scene.render.resolution_percentage),
            "filepath": scene.render.filepath,
            "image_file_format": scene.render.image_settings.file_format,
            "film_transparent": bool(scene.render.film_transparent),
        },
        "world": scene.world.name if scene.world else None,
        "world_color": list(map(float, scene.world.color)) if scene.world else None,
        "custom_properties": _custom_properties(scene),
        "objects": objects,
    }


def full_scene_state_sha256(*, excluded_objects: Iterable[str] = ()) -> str:
    return canonical_json_sha256(
        full_scene_state_record(excluded_objects=excluded_objects)
    )


def _action_record(action: Any) -> dict[str, Any]:
    fcurves = []
    for curve in sorted(
        action.fcurves,
        key=lambda item: (str(item.data_path), int(item.array_index)),
    ):
        keyframes = []
        for point in curve.keyframe_points:
            keyframes.append(
                {
                    "co": list(map(float, point.co)),
                    "handle_left": list(map(float, point.handle_left)),
                    "handle_right": list(map(float, point.handle_right)),
                    "handle_left_type": str(point.handle_left_type),
                    "handle_right_type": str(point.handle_right_type),
                    "interpolation": str(point.interpolation),
                    "easing": str(point.easing),
                }
            )
        fcurves.append(
            {
                "data_path": str(curve.data_path),
                "array_index": int(curve.array_index),
                "extrapolation": str(curve.extrapolation),
                "keyframes": keyframes,
            }
        )
    return {
        "name": action.name,
        "frame_range": list(map(float, action.frame_range)),
        "fcurves": fcurves,
    }


def action_sha256(action: Any) -> str:
    return canonical_json_sha256(_action_record(action))


def _assert_sha(actual: str, expected: Any, label: str) -> None:
    if actual != str(expected).lower():
        raise KiraR24PreparationError(
            f"{label} hash mismatch: expected={expected}; actual={actual}"
        )


def _mesh_binding(obj: Any) -> dict[str, str]:
    return {
        "complete_mesh_sha256": nails._mesh_signature(obj),  # noqa: SLF001
        "geometry_uv_sha256": brow_hashes.mesh_geometry_digest(obj),
        "positive_weight_sha256": brow_hashes.weight_digest(obj),
        "world_matrix_sha256": _matrix_sha256(obj.matrix_world),
        "modifier_stack_sha256": projector.modifier_stack_sha256(obj),
    }


def _verify_mesh_binding(
    obj: Any,
    expected: Mapping[str, Any],
    *,
    label: str,
    fields: Sequence[str],
) -> dict[str, str]:
    if obj is None or obj.type != "MESH":
        raise KiraR24PreparationError(f"{label} mesh object is absent")
    actual = _mesh_binding(obj)
    for field in fields:
        _assert_sha(actual[field], expected[field], f"{label}.{field}")
    return actual


def verify_loaded_candidate(bound: Mapping[str, Any]) -> dict[str, Any]:
    candidate_path = Path(bound["candidate_path"]).resolve()
    loaded_text = str(bpy.data.filepath).strip()
    if not loaded_text or Path(loaded_text).resolve() != candidate_path:
        raise KiraR24PreparationError(
            "Blender does not have the exact caller-bound candidate loaded"
        )
    if bool(bpy.data.is_dirty):
        raise KiraR24PreparationError(
            "loaded candidate has unsaved changes before preparation"
        )
    _assert_sha(
        sha256_file(candidate_path), bound["candidate_sha256"], "candidate Blend"
    )
    candidate = bound["raw"]["candidate"]
    body = bpy.data.objects.get(str(candidate["body"]["object"]))
    rig = bpy.data.objects.get(str(candidate["rig"]["object"]))
    old_brow = bpy.data.objects.get(OLD_BROW_NAME)
    body_binding = _verify_mesh_binding(
        body,
        candidate["body"],
        label="body",
        fields=(
            "complete_mesh_sha256",
            "geometry_uv_sha256",
            "positive_weight_sha256",
            "world_matrix_sha256",
            "modifier_stack_sha256",
        ),
    )
    if rig is None or rig.type != "ARMATURE":
        raise KiraR24PreparationError("exact bound armature is absent")
    rig_binding = {
        "rest_pose_sha256": _rig_rest_sha256(rig),
        "pose_sha256": _rig_pose_sha256(rig),
        "world_matrix_sha256": _matrix_sha256(rig.matrix_world),
    }
    for field, value in rig_binding.items():
        _assert_sha(value, candidate["rig"][field], f"rig.{field}")
    old_brow_binding = _verify_mesh_binding(
        old_brow,
        candidate["replaceable_old_brow"],
        label="replaceable old brow",
        fields=(
            "complete_mesh_sha256",
            "geometry_uv_sha256",
            "positive_weight_sha256",
            "world_matrix_sha256",
            "modifier_stack_sha256",
        ),
    )
    source_bindings = {}
    for nail_id, source_object, _bone in NAIL_BINDINGS:
        row = bound["source_nails"][nail_id]
        obj = bpy.data.objects.get(source_object)
        source_bindings[nail_id] = _verify_mesh_binding(
            obj,
            row,
            label=f"source nail {nail_id}",
            fields=(
                "complete_mesh_sha256",
                "geometry_uv_sha256",
                "positive_weight_sha256",
                "world_matrix_sha256",
                "modifier_stack_sha256",
            ),
        )
    scene_sha = full_scene_state_sha256()
    _assert_sha(
        scene_sha,
        candidate["full_scene_state_sha256"],
        "candidate full scene state",
    )
    return {
        "body": body,
        "rig": rig,
        "old_brow": old_brow,
        "body_binding": body_binding,
        "rig_binding": rig_binding,
        "old_brow_binding": old_brow_binding,
        "source_nail_bindings": source_bindings,
        "full_scene_state_sha256": scene_sha,
    }


def transplant_exact_attempt02_brows(*, rig: Any, source_path: Path) -> tuple[list[Any], list[dict[str, Any]]]:
    expected_names = [str(row["object"]) for row in BROW_BINDINGS]
    if any(bpy.data.objects.get(name) is not None for name in expected_names):
        raise KiraR24PreparationError(
            "an Attempt-02 brow name already exists; exact append would be ambiguous"
        )
    with bpy.data.libraries.load(str(source_path), link=False) as (data_from, data_to):
        missing = sorted(set(expected_names).difference(data_from.objects))
        if missing:
            raise KiraR24PreparationError(
                f"Attempt-02 source is missing exact brows: {missing}"
            )
        data_to.objects = expected_names
    imported = list(data_to.objects)
    if len(imported) != 2 or any(obj is None for obj in imported):
        raise KiraR24PreparationError("Attempt-02 append did not return exactly two brows")
    by_name = {obj.name: obj for obj in imported}
    if set(by_name) != set(expected_names):
        raise KiraR24PreparationError("Blender renamed an exact Attempt-02 brow")
    records = []
    for binding in BROW_BINDINGS:
        obj = by_name[str(binding["object"])]
        if obj.type != "MESH":
            raise KiraR24PreparationError("Attempt-02 brow is not a mesh")
        if not obj.users_collection:
            bpy.context.scene.collection.objects.link(obj)
        _assert_sha(
            brow_hashes.mesh_geometry_digest(obj),
            binding["geometry_uv_sha256"],
            f"transplanted {obj.name} geometry",
        )
        _assert_sha(
            brow_hashes.weight_digest(obj),
            binding["positive_weight_sha256"],
            f"transplanted {obj.name} weights",
        )
        for bone_name in binding["bones"]:
            if rig.data.bones.get(str(bone_name)) is None:
                raise KiraR24PreparationError(
                    f"target rig lacks native brow bone {bone_name}"
                )
        positive_groups = {
            group.name
            for group in obj.vertex_groups
            if any(
                _group_weight(group, vertex.index) > 0.0
                for vertex in obj.data.vertices
            )
        }
        if positive_groups != set(binding["bones"]):
            raise KiraR24PreparationError(
                f"transplanted brow positive groups drifted: {obj.name}"
            )
        world = obj.matrix_world.copy()
        obj.parent = rig
        obj.parent_type = "OBJECT"
        obj.matrix_parent_inverse = rig.matrix_world.inverted()
        obj.matrix_world = world
        for modifier in list(obj.modifiers):
            if modifier.type == "ARMATURE":
                obj.modifiers.remove(modifier)
        modifier = obj.modifiers.new("R24_Exact_Attempt02_Brow_Attachment", "ARMATURE")
        modifier.object = rig
        obj["private_owner_review_only"] = True
        obj["inactive_candidate"] = True
        obj["runtime_activation_allowed"] = False
        obj["source_component_sha256"] = str(binding["geometry_uv_sha256"])
        # Geometry and vertex weights must stay byte-for-byte fingerprint exact
        # through target-rig rebinding; no third brow is authored here.
        _assert_sha(
            brow_hashes.mesh_geometry_digest(obj),
            binding["geometry_uv_sha256"],
            f"rebound {obj.name} geometry",
        )
        _assert_sha(
            brow_hashes.weight_digest(obj),
            binding["positive_weight_sha256"],
            f"rebound {obj.name} weights",
        )
        records.append(
            {
                "object": obj.name,
                "geometry_uv_sha256": brow_hashes.mesh_geometry_digest(obj),
                "positive_weight_sha256": brow_hashes.weight_digest(obj),
                "native_expression_bones": list(binding["bones"]),
                "target_rig": rig.name,
                "third_brow_authored": False,
                "exact_attempt02_component_unchanged": True,
            }
        )
    return [by_name[name] for name in expected_names], records


def _group_weight(group: Any, vertex_index: int) -> float:
    try:
        return float(group.weight(vertex_index))
    except RuntimeError:
        return 0.0


def _remove_mesh_object(obj: Any) -> None:
    mesh = obj.data if obj and obj.type == "MESH" else None
    if obj is not None and obj.name in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    if mesh is not None and mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def _make_nail_materials() -> tuple[Any, Any]:
    if bpy.data.materials.get(NATURAL_BED_MATERIAL) is not None:
        raise KiraR24PreparationError("R24 nail bed material name already exists")
    if bpy.data.materials.get(NATURAL_EDGE_MATERIAL) is not None:
        raise KiraR24PreparationError("R24 free-edge material name already exists")
    bed = nail_legacy.natural_material(
        NATURAL_BED_MATERIAL, (0.72, 0.40, 0.39, 0.78), free_edge=False
    )
    edge = nail_legacy.natural_material(
        NATURAL_EDGE_MATERIAL, (0.93, 0.78, 0.75, 0.70), free_edge=True
    )
    return bed, edge


def _set_nail_properties(obj: Any, definition: Mapping[str, Any]) -> None:
    obj["nail_component"] = True
    obj["nail_kind"] = str(definition["kind"])
    obj["nail_side"] = str(definition["side"])
    obj["nail_digit"] = int(definition["digit"])
    obj["nail_id"] = str(definition["nail_id"])
    obj["declared_terminal_bone"] = str(definition["bone"])
    obj["projection_method"] = projector.METHOD_ID
    obj["private_owner_review_only"] = True
    obj["inactive_candidate"] = True
    obj["runtime_activation_allowed"] = False
    obj["automatic_bone_remap_performed"] = False


def build_all_twenty_nails(
    *,
    body: Any,
    rig: Any,
    source_rows: Mapping[str, Mapping[str, Any]],
) -> tuple[list[Any], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    definitions: dict[str, dict[str, Any]] = {}
    inventory = expected_nail_inventory()
    live_bindings = {
        (str(row["nail_id"]), str(row["source_object"]), str(row["bone"]))
        for row in inventory
    }
    if live_bindings != set(NAIL_BINDINGS) or len(inventory) != 20:
        raise KiraR24PreparationError("live 20-nail inventory drifted")
    for base in inventory:
        nail_id = str(base["nail_id"])
        source_obj = bpy.data.objects.get(str(base["source_object"]))
        row = source_rows[nail_id]
        definitions[nail_id] = projector.corrected_reference_definition(
            source_nail=source_obj,
            body=body,
            armature=rig,
            definition=base,
            expected_anchor_world_m=row["corrected_anchor_world_m"],
        )
    bed, edge = _make_nail_materials()
    built = []
    results = []
    try:
        for base in inventory:
            nail_id = str(base["nail_id"])
            name = f"{NEW_NAIL_PREFIX}_{nail_id}"
            if bpy.data.objects.get(name) is not None:
                raise KiraR24PreparationError(f"new nail name already exists: {name}")
            obj, result = projector.build_weight_constrained_nail_v2(
                body=body,
                armature=rig,
                definition=definitions[nail_id],
                name=name,
                bed_material=bed,
                free_edge_material=edge,
            )
            _set_nail_properties(obj, definitions[nail_id])
            if result.get("all_strict_gates_passed") is not True:
                raise KiraR24PreparationError(f"nail did not pass: {nail_id}")
            if result.get("component_id_zero_rejected") is not True:
                raise KiraR24PreparationError(
                    f"reserved component zero was not rejected: {nail_id}"
                )
            if int(result["selection"]["selected_raw_component_id"]) <= 0:
                raise KiraR24PreparationError(
                    f"nonpositive component reached final nail: {nail_id}"
                )
            built.append(obj)
            results.append(_plain(result))
    except Exception:
        for obj in list(built):
            _remove_mesh_object(obj)
        raise
    if len(built) != 20 or len({str(obj["nail_id"]) for obj in built}) != 20:
        raise KiraR24PreparationError("complete unique 20-nail result is absent")
    return built, definitions, results


def _all_nails_attached(nail_objects: Sequence[Any], rig: Any) -> bool:
    if len(nail_objects) != 20:
        return False
    for obj in nail_objects:
        bone = str(obj["declared_terminal_bone"])
        groups = {group.name for group in obj.vertex_groups}
        modifiers = [modifier for modifier in obj.modifiers if modifier.type == "ARMATURE"]
        if bone not in groups or len(modifiers) != 1 or modifiers[0].object != rig:
            return False
    return True


def _posed_nail_gate_row(
    *,
    source_row: Mapping[str, Any],
    body: Any,
    rig: Any,
    nail_objects: Sequence[Any],
) -> dict[str, Any]:
    action_name = str(source_row["action"])
    action = bpy.data.actions.get(action_name)
    if action is None:
        raise KiraR24PreparationError(f"pose action is absent: {action_name}")
    _assert_sha(action_sha256(action), source_row["action_sha256"], f"action {action_name}")
    if rig.animation_data is None:
        rig.animation_data_create()
    rig.animation_data.action = action
    bpy.context.scene.frame_set(int(source_row["frame"]))
    bpy.context.view_layer.update()
    body_points, body_triangles = exact_audit.world_geometry(body, evaluated=True)
    per_nail = []
    for nail in nail_objects:
        nail_points, nail_triangles = exact_audit.world_geometry(nail, evaluated=True)
        record = exact_audit.exact_pair_record(
            body_points,
            body_triangles,
            nail_points,
            nail_triangles,
            source_nail_vertex_count=len(nail.data.vertices),
        )
        per_nail.append(
            {
                "nail_id": str(nail["nail_id"]),
                "exact_genuine_triangle_pair_count": int(
                    record["exact_genuine_triangle_pair_count"]
                ),
                "minimum_clearance_m": float(
                    record["minimum_unsigned_surface_clearance_m"]
                ),
                "maximum_clearance_m": float(
                    record["maximum_unsigned_surface_clearance_m"]
                ),
                "exact_pair_record": record,
            }
        )
    pair_audit = nail_legacy.nail_pair_audit(list(nail_objects))
    crossings = sum(
        int(row["exact_genuine_triangle_pair_count"]) for row in per_nail
    )
    minimum = min(float(row["minimum_clearance_m"]) for row in per_nail)
    maximum = max(float(row["maximum_clearance_m"]) for row in per_nail)
    row = {
        "pose": str(source_row["pose"]),
        "action": action_name,
        "action_sha256": action_sha256(action),
        "frame": int(source_row["frame"]),
        "contact_gate_passed": source_row.get("contact_gate_passed") is True,
        "contact_gate_source": "exact_candidate_bound_pose_evidence",
        "all_20_nails_attached": _all_nails_attached(nail_objects, rig),
        "all_clearance_gates_passed": (
            minimum >= MINIMUM_CLEARANCE_M and maximum <= MAXIMUM_CLEARANCE_M
        ),
        "no_body_nail_intersections": crossings == 0,
        "no_nail_pair_overlap": pair_audit.get(
            "no_nail_to_nail_broad_phase_overlap"
        )
        is True,
        "nail_count": len(nail_objects),
        "exact_body_nail_crossing_pair_count": crossings,
        "tested_nail_pair_count": int(pair_audit["tested_object_pair_count"]),
        "minimum_clearance_m": minimum,
        "maximum_clearance_m": maximum,
        "per_nail": per_nail,
        "nail_pair_audit": pair_audit,
    }
    return _plain(row)


def run_all_bound_pose_gates(
    *,
    pose_evidence: Mapping[str, Any],
    candidate_sha256: str,
    body: Any,
    rig: Any,
    nail_objects: Sequence[Any],
) -> dict[str, Any]:
    source_validation = validate_pose_gate_matrix(pose_evidence, candidate_sha256)
    source_rows = {
        str(row["pose"]): row for row in pose_evidence["poses"]
    }
    scene = bpy.context.scene
    original_frame = int(scene.frame_current)
    original_subframe = float(scene.frame_subframe)
    original_action = rig.animation_data.action if rig.animation_data else None
    output_rows = []
    try:
        for pose in source_validation["required_pose_keys"]:
            output_rows.append(
                _posed_nail_gate_row(
                    source_row=source_rows[pose],
                    body=body,
                    rig=rig,
                    nail_objects=nail_objects,
                )
            )
        result = {"candidate_sha256": candidate_sha256, "poses": output_rows}
        output_validation = validate_pose_gate_matrix(result, candidate_sha256)
        return {
            "source_pose_matrix_validation": source_validation,
            "in_memory_pose_matrix_validation": output_validation,
            **result,
        }
    finally:
        if rig.animation_data is None:
            rig.animation_data_create()
        rig.animation_data.action = original_action
        scene.frame_set(original_frame, subframe=original_subframe)
        bpy.context.view_layer.update()


def render_after_pose_gates(
    *,
    render_dir: Path,
    nail_objects: Sequence[Any],
    definitions: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, str], dict[str, Any]]:
    render_dir.mkdir(parents=False, exist_ok=False)
    paths = nail_review.render_close_reviews(
        render_dir, list(nail_objects), definitions
    )
    if set(paths) != set(EXPECTED_RENDER_KEYS):
        raise KiraR24PreparationError("review renderer did not produce the exact 8-view set")
    validation = validate_render_inventory(render_dir, paths)
    return dict(paths), validation


def _exclusive_json(path: Path, value: Mapping[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(_plain(value), stream, indent=2, sort_keys=True)
        stream.write("\n")


def _post_component_exactness(
    *,
    body: Any,
    rig: Any,
    expected_body: Mapping[str, Any],
    expected_rig: Mapping[str, Any],
    brows: Sequence[Any],
) -> dict[str, Any]:
    body_actual = _verify_mesh_binding(
        body,
        expected_body,
        label="post body",
        fields=(
            "complete_mesh_sha256",
            "geometry_uv_sha256",
            "positive_weight_sha256",
            "world_matrix_sha256",
            "modifier_stack_sha256",
        ),
    )
    rig_actual = {
        "rest_pose_sha256": _rig_rest_sha256(rig),
        "pose_sha256": _rig_pose_sha256(rig),
        "world_matrix_sha256": _matrix_sha256(rig.matrix_world),
    }
    for field, value in rig_actual.items():
        _assert_sha(value, expected_rig[field], f"post rig.{field}")
    brow_records = []
    expected_brows = {str(row["object"]): row for row in BROW_BINDINGS}
    for obj in brows:
        binding = expected_brows[obj.name]
        _assert_sha(
            brow_hashes.mesh_geometry_digest(obj),
            binding["geometry_uv_sha256"],
            f"post brow {obj.name} geometry",
        )
        _assert_sha(
            brow_hashes.weight_digest(obj),
            binding["positive_weight_sha256"],
            f"post brow {obj.name} weights",
        )
        brow_records.append(
            {
                "object": obj.name,
                "geometry_uv_sha256": brow_hashes.mesh_geometry_digest(obj),
                "positive_weight_sha256": brow_hashes.weight_digest(obj),
            }
        )
    return {
        "body": body_actual,
        "rig": rig_actual,
        "brows": brow_records,
        "all_exact_post_component_bindings_passed": True,
    }


def main() -> None:
    args = parse_args()
    config_path = (ROOT / args.config).resolve()
    try:
        config_path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise KiraR24PreparationError("config path escapes project root") from exc
    config = _json_object(config_path)
    bound = validate_config(config, project_root=ROOT, verify_files=True)
    config_sha = sha256_file(config_path)
    verified = verify_loaded_candidate(bound)
    body = verified["body"]
    rig = verified["rig"]
    old_brow = verified["old_brow"]
    source_objects = [
        bpy.data.objects[str(source_object)]
        for _nail_id, source_object, _bone in NAIL_BINDINGS
    ]
    excluded_before = {OLD_BROW_NAME, *(obj.name for obj in source_objects)}
    protected_before = full_scene_state_record(excluded_objects=excluded_before)
    protected_before_sha = canonical_json_sha256(protected_before)
    evidence_dir = Path(bound["evidence_dir"])
    render_dir = Path(bound["render_dir"])
    evidence_dir.mkdir(parents=True, exist_ok=False)
    events = ["exact_bindings_verified"]
    try:
        brow_source = (ROOT / BROW_SOURCE_PATH).resolve()
        brows, brow_records = transplant_exact_attempt02_brows(
            rig=rig, source_path=brow_source
        )
        built, definitions, nail_results = build_all_twenty_nails(
            body=body,
            rig=rig,
            source_rows=bound["source_nails"],
        )
        # Input landmarks and the replaceable brow disappear only after all
        # replacement components pass their individual in-memory gates.
        _remove_mesh_object(old_brow)
        for source in source_objects:
            _remove_mesh_object(source)
        events.append("components_built_in_memory")

        pose_evidence = _json_object(Path(bound["pose_evidence_path"]))
        pose_results = run_all_bound_pose_gates(
            pose_evidence=pose_evidence,
            candidate_sha256=str(bound["candidate_sha256"]),
            body=body,
            rig=rig,
            nail_objects=built,
        )
        events.append("pose_gates_validated")

        render_paths, render_validation = render_after_pose_gates(
            render_dir=render_dir,
            nail_objects=built,
            definitions=definitions,
        )
        events.append("renders_validated")

        post_exact = _post_component_exactness(
            body=body,
            rig=rig,
            expected_body=bound["body"],
            expected_rig=bound["rig"],
            brows=brows,
        )
        excluded_after = {
            *(obj.name for obj in brows),
            *(obj.name for obj in built),
        }
        protected_after = full_scene_state_record(excluded_objects=excluded_after)
        protected_after_sha = canonical_json_sha256(protected_after)
        if protected_after != protected_before:
            raise KiraR24PreparationError(
                "protected full scene state changed outside brow/nail replacement"
            )
        events.append("protected_state_reverified")
        transaction_events = [*events, "evidence_written", "no_save_exit"]
        transaction = validate_no_save_transaction(transaction_events)
        evidence = {
            "schema": EVIDENCE_SCHEMA,
            "status": "ALL_GATES_PASSED_NO_BLEND_SAVED",
            "created_utc": utc_now(),
            "config": config_path.relative_to(ROOT).as_posix(),
            "config_sha256": config_sha,
            "candidate": {
                "path": Path(bound["candidate_path"]).relative_to(ROOT).as_posix(),
                "sha256": bound["candidate_sha256"],
                "loaded_exactly": True,
                "unsaved_at_entry": True,
                "blend_saved_by_worker": False,
            },
            "input_bindings": {
                key: value
                for key, value in verified.items()
                if key not in {"body", "rig", "old_brow"}
            },
            "brow_transplant": {
                "source": BROW_SOURCE_PATH,
                "source_sha256": sha256_file(brow_source),
                "objects": brow_records,
                "object_count": 2,
                "third_brow_authored": False,
            },
            "nail_method": projector.METHOD_ID,
            "nail_results": nail_results,
            "nail_count": len(built),
            "pose_contact_intersection_gates": pose_results,
            "renders": render_paths,
            "render_validation": render_validation,
            "post_component_exactness": post_exact,
            "protected_full_scene": {
                "before_sha256": protected_before_sha,
                "after_sha256": protected_after_sha,
                "exactly_unchanged": True,
                "excluded_before": sorted(excluded_before),
                "excluded_after": sorted(excluded_after),
            },
            "transaction": transaction,
            "private": True,
            "inactive": True,
            "unassigned": True,
            "unpublished": True,
            "runtime_activation_allowed": False,
            "candidate_blend_saved": False,
            "body_authored_or_mutated": False,
        }
        _exclusive_json(evidence_dir / "BUILD_EVIDENCE.json", evidence)
        print(
            json.dumps(
                {
                    "status": evidence["status"],
                    "evidence": (
                        evidence_dir / "BUILD_EVIDENCE.json"
                    ).relative_to(ROOT).as_posix(),
                    "render_count": render_validation["render_count"],
                    "candidate_blend_saved": False,
                },
                indent=2,
            )
        )
    except Exception as exc:
        failure = {
            "schema": FAILURE_SCHEMA,
            "status": "FAILED_CLOSED_NO_BLEND_SAVED",
            "created_utc": utc_now(),
            "config": config_path.relative_to(ROOT).as_posix(),
            "config_sha256": config_sha,
            "candidate_sha256": bound["candidate_sha256"],
            "events_completed": events,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "candidate_blend_saved": False,
            "runtime_activation_allowed": False,
        }
        failure_path = evidence_dir / "FAILURE_EVIDENCE.json"
        if not failure_path.exists():
            _exclusive_json(failure_path, failure)
        raise


if __name__ == "__main__":
    main()
