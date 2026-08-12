#!/usr/bin/env python3
"""Blender worker for an exact, inactive Kira R7 authoring workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import bpy


MASK_SPECS = (
    (
        "r7_mask_protected_head_existing_mouth",
        "Human-reviewed vertices for the entire protected Kira head, including every existing mouth/lip vertex.",
        "required_before_any_geometry_authoring",
    ),
    (
        "r7_mask_authorable_body_below_protected_boundary",
        "Human-reviewed exact complement of the protected head/existing-mouth mask.",
        "required_before_any_geometry_authoring",
    ),
    (
        "r7_mask_mammary_areola_left",
        "Human-reviewed left adult areolar surface selection; no automated coordinate or UV inference.",
        "required_before_localized_coloration",
    ),
    (
        "r7_mask_mammary_areola_right",
        "Human-reviewed right adult areolar surface selection; no automated coordinate or UV inference.",
        "required_before_localized_coloration",
    ),
    (
        "r7_mask_external_genital_surface",
        "Human-reviewed adult external-genital surface selection; no automated coordinate or UV inference.",
        "required_before_localized_coloration",
    ),
)


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


def update_text(digest: "hashlib._Hash", value: str) -> None:
    encoded = value.encode("utf-8")
    digest.update(struct.pack("<I", len(encoded)))
    digest.update(encoded)


def matrix_values(matrix: object) -> list[float]:
    return [float(matrix[row][column]) for row in range(4) for column in range(4)]


def hash_float_rows(rows: list[tuple[float, ...]]) -> str:
    digest = hashlib.sha256()
    for index, row in enumerate(rows):
        digest.update(struct.pack("<II", index, len(row)))
        digest.update(struct.pack(f"<{len(row)}d", *row))
    return digest.hexdigest()


def topology_hash(mesh: bpy.types.Mesh) -> str:
    digest = hashlib.sha256()
    for polygon in mesh.polygons:
        indices = tuple(int(value) for value in polygon.vertices)
        digest.update(struct.pack("<II", int(polygon.index), len(indices)))
        digest.update(struct.pack(f"<{len(indices)}I", *indices))
    return digest.hexdigest()


def shape_key_snapshot(mesh: bpy.types.Mesh) -> dict[str, object]:
    if mesh.shape_keys is None:
        rows = [tuple(float(v.co[axis]) for axis in range(3)) for v in mesh.vertices]
        return {
            "count": 0,
            "names": [],
            "values": [],
            "coordinate_sha256": hash_float_rows(rows),
            "per_key_coordinate_sha256": {},
        }
    names: list[str] = []
    values: list[float] = []
    per_key: dict[str, str] = {}
    combined = hashlib.sha256()
    for key in mesh.shape_keys.key_blocks:
        names.append(key.name)
        values.append(float(key.value))
        rows = [tuple(float(point.co[axis]) for axis in range(3)) for point in key.data]
        coordinate_hash = hash_float_rows(rows)
        per_key[key.name] = coordinate_hash
        update_text(combined, key.name)
        combined.update(struct.pack("<d", float(key.value)))
        combined.update(bytes.fromhex(coordinate_hash))
    return {
        "count": len(names),
        "names": names,
        "values": values,
        "coordinate_sha256": combined.hexdigest(),
        "per_key_coordinate_sha256": per_key,
    }


def mixed_position_rows(mesh: bpy.types.Mesh) -> list[tuple[float, float, float]]:
    if mesh.shape_keys is None:
        return [tuple(float(v.co[axis]) for axis in range(3)) for v in mesh.vertices]
    keys = mesh.shape_keys.key_blocks
    basis = keys[0]
    rows: list[tuple[float, float, float]] = []
    for index in range(len(mesh.vertices)):
        point = basis.data[index].co.copy()
        for key in keys[1:]:
            point += (key.data[index].co - basis.data[index].co) * float(key.value)
        rows.append(tuple(float(point[axis]) for axis in range(3)))
    return rows


def uv_snapshot(mesh: bpy.types.Mesh) -> dict[str, object]:
    digest = hashlib.sha256()
    names: list[str] = []
    for layer in mesh.uv_layers:
        names.append(layer.name)
        update_text(digest, layer.name)
        for index, loop in enumerate(layer.data):
            digest.update(struct.pack("<Idd", index, float(loop.uv.x), float(loop.uv.y)))
    return {"layer_count": len(names), "names": names, "sha256": digest.hexdigest()}


def weight_snapshot(body: bpy.types.Object) -> dict[str, object]:
    digest = hashlib.sha256()
    group_names = [group.name for group in body.vertex_groups]
    for name in group_names:
        update_text(digest, name)
    unweighted = 0
    over_four = 0
    maximum = 0
    for vertex in body.data.vertices:
        assignments = sorted(
            (int(item.group), float(item.weight))
            for item in vertex.groups
            if float(item.weight) > 1e-8
        )
        maximum = max(maximum, len(assignments))
        if not assignments:
            unweighted += 1
        if len(assignments) > 4:
            over_four += 1
        digest.update(struct.pack("<II", int(vertex.index), len(assignments)))
        for group_index, weight in assignments:
            digest.update(struct.pack("<Id", group_index, weight))
    return {
        "vertex_group_count": len(group_names),
        "vertex_group_names": group_names,
        "unweighted_vertex_count": unweighted,
        "maximum_positive_influences": maximum,
        "vertices_over_four_influences": over_four,
        "sha256": digest.hexdigest(),
    }


def rig_snapshot(armature: bpy.types.Object) -> dict[str, object]:
    digest = hashlib.sha256()
    names: list[str] = []
    parents: list[str | None] = []
    for bone in armature.data.bones:
        names.append(bone.name)
        parent = bone.parent.name if bone.parent else None
        parents.append(parent)
        update_text(digest, bone.name)
        update_text(digest, parent or "")
        digest.update(struct.pack("<16d", *matrix_values(bone.matrix_local)))
    return {
        "bone_count": len(names),
        "bone_names_in_order": names,
        "parents_in_order": parents,
        "rest_hierarchy_sha256": digest.hexdigest(),
    }


def object_snapshot(body: bpy.types.Object, armature: bpy.types.Object) -> dict[str, object]:
    mesh = body.data
    return {
        "body_object_name": body.name,
        "body_mesh_name": mesh.name,
        "armature_object_name": armature.name,
        "armature_data_name": armature.data.name,
        "vertex_count": len(mesh.vertices),
        "edge_count": len(mesh.edges),
        "polygon_count": len(mesh.polygons),
        "loop_count": len(mesh.loops),
        "topology_face_index_sha256": topology_hash(mesh),
        "mixed_surface_position_sha256": hash_float_rows(mixed_position_rows(mesh)),
        "shape_keys": shape_key_snapshot(mesh),
        "uv": uv_snapshot(mesh),
        "weights": weight_snapshot(body),
        "rig": rig_snapshot(armature),
        "body_matrix_world": matrix_values(body.matrix_world),
        "armature_matrix_world": matrix_values(armature.matrix_world),
        "material_slot_count": len(body.material_slots),
        "material_slot_names": [slot.name for slot in body.material_slots],
    }


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)


def create_instruction_text() -> None:
    instructions = """KIRA R7 AUTHORING WORKSPACE — READ FIRST

This file is isolated and inactive. It contains no approved R7 candidate.
The protected baseline is an exact duplicate of the pinned R6 import.

DO NOT sculpt, retopologize, paint, export, activate, or bind the working body yet.

First required manual operation:
1. Inspect the exact unchanged working mesh in Blender.
2. Select the complete Kira head, including every vertex of the existing single
   mouth/lip surface and the full neck transition that must remain unchanged.
3. Assign that reviewed selection to the point attribute
   r7_mask_protected_head_existing_mouth.
4. Assign its exact complement to
   r7_mask_authorable_body_below_protected_boundary.
5. Save, run the workspace audit, and bind the selection-index hashes to a
   signed/reviewed attestation before any geometry editing.

Localized coloration remains blocked. The adult-region mask attributes are
empty on purpose and must be independently selected/reviewed. Never infer them
from coordinate boxes or guessed UV positions.
"""
    text = bpy.data.texts.new("R7_READ_ME_FIRST.txt")
    text.write(instructions)

    helper = bpy.data.texts.new("R7_MANUAL_MASK_ASSIGNMENT_HELPER.py")
    helper.write(
        "# Run only after a human modeler has visually/topologically reviewed\n"
        "# the selected vertices. This helper NEVER chooses a body region.\n"
        "import bpy\n"
        "import bmesh\n\n"
        "MASK_ATTRIBUTE = 'r7_mask_protected_head_existing_mouth'\n"
        "ALLOWED = {\n"
        "    'r7_mask_protected_head_existing_mouth',\n"
        "    'r7_mask_authorable_body_below_protected_boundary',\n"
        "    'r7_mask_mammary_areola_left',\n"
        "    'r7_mask_mammary_areola_right',\n"
        "    'r7_mask_external_genital_surface',\n"
        "}\n"
        "obj = bpy.context.edit_object\n"
        "if obj is None or obj.type != 'MESH':\n"
        "    raise RuntimeError('Select the R7 working body and enter Edit Mode')\n"
        "if MASK_ATTRIBUTE not in ALLOWED:\n"
        "    raise RuntimeError('Choose one registered R7 mask attribute')\n"
        "bm = bmesh.from_edit_mesh(obj.data)\n"
        "selected = {v.index for v in bm.verts if v.select}\n"
        "if not selected:\n"
        "    raise RuntimeError('No human-reviewed vertices are selected')\n"
        "bpy.ops.object.mode_set(mode='OBJECT')\n"
        "attribute = obj.data.attributes[MASK_ATTRIBUTE]\n"
        "for index, value in enumerate(attribute.data):\n"
        "    value.value = 1.0 if index in selected else 0.0\n"
        "obj['r7_masks_changed_requires_external_audit'] = True\n"
        "print(f'Assigned {len(selected)} reviewed vertices to {MASK_ATTRIBUTE}; run the external audit next.')\n"
    )


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("runtime_activation_requested") or config.get("candidate_export_requested"):
        raise ValueError("R7 workspace worker refuses activation and candidate export requests")
    project_root = Path(config["project_root"]).resolve(strict=True)
    source = Path(config["source_model"]).resolve(strict=True)
    output_dir = Path(config["output_dir"]).resolve(strict=True)
    allowed_root = (
        project_root
        / "Avatar"
        / "avatar_builder"
        / "candidate_sources"
        / "kira_adult_body_r7"
    ).resolve()
    output_dir.relative_to(allowed_root)
    if sha256_file(source) != config["source_sha256"]:
        raise ValueError("exact pinned R6 SHA-256 mismatch")

    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise ValueError(f"expected exactly one R6 armature, found {len(armatures)}")
    if not meshes:
        raise ValueError("R6 import contains no mesh")
    body = max(meshes, key=lambda obj: len(obj.data.vertices))
    armature = armatures[0]
    substantive = [obj for obj in meshes if len(obj.data.vertices) >= 1000]
    if substantive != [body]:
        raise ValueError("R6 import no longer has exactly one substantive body mesh")
    if len(armature.data.bones) != 79:
        raise ValueError("R6 import no longer has the exact 79-bone rig")

    baseline_before = object_snapshot(body, armature)
    if baseline_before["weights"]["vertices_over_four_influences"] != 0:
        raise ValueError("R6 source has more than four effective weights on a vertex")
    if baseline_before["weights"]["unweighted_vertex_count"] != 0:
        raise ValueError("R6 source has unweighted body vertices")

    scene_root = bpy.context.scene.collection
    protected_collection = bpy.data.collections.new("R7_PROTECTED_EXACT_BASELINE_DO_NOT_EDIT")
    working_collection = bpy.data.collections.new("R7_WORKING_UNAUTHORED_NO_EXPORT")
    rig_collection = bpy.data.collections.new("R7_PROTECTED_79_BONE_RIG_DO_NOT_EDIT")
    scene_root.children.link(protected_collection)
    scene_root.children.link(working_collection)
    scene_root.children.link(rig_collection)

    baseline_body = body.copy()
    baseline_body.data = body.data.copy()
    baseline_body.name = "R7_PROTECTED_FULL_SURFACE_BASELINE_DO_NOT_EDIT"
    baseline_body.data.name = "R7_PROTECTED_FULL_SURFACE_BASELINE_MESH_DO_NOT_EDIT"
    protected_collection.objects.link(baseline_body)
    baseline_body.hide_select = True
    baseline_body.hide_render = True
    baseline_body.hide_viewport = True
    baseline_body["r7_role"] = "exact_full_surface_baseline"
    baseline_body["source_sha256"] = config["source_sha256"]
    baseline_body["do_not_edit"] = True

    move_to_collection(body, working_collection)
    move_to_collection(armature, rig_collection)
    armature.hide_select = True
    armature["r7_role"] = "protected_exact_79_bone_rig"
    armature["do_not_edit"] = True
    body["r7_role"] = "working_body_unauthored"
    body["workspace_id"] = config["workspace_id"]
    body["source_sha256"] = config["source_sha256"]
    body["geometry_authoring_allowed"] = False
    body["localized_coloration_allowed"] = False
    body["runtime_activation_allowed"] = False
    body["candidate_export_allowed"] = False
    body["anatomical_completeness_proven"] = False
    body["owner_approved"] = False
    body["existing_single_mouth_surface_must_be_preserved"] = True
    body["second_mouth_allowed"] = False

    for name, _meaning, _gate in MASK_SPECS:
        if body.data.attributes.get(name) is not None:
            raise ValueError(f"source unexpectedly already contains reserved R7 mask: {name}")
        attribute = body.data.attributes.new(name=name, type="FLOAT", domain="POINT")
        for value in attribute.data:
            value.value = 0.0

    create_instruction_text()
    bpy.context.scene["workspace_id"] = config["workspace_id"]
    bpy.context.scene["source_sha256"] = config["source_sha256"]
    bpy.context.scene["runtime_activation_allowed"] = False
    bpy.context.scene["candidate_export_allowed"] = False
    bpy.context.scene["geometry_authoring_allowed"] = False
    bpy.context.scene["localized_coloration_allowed"] = False
    bpy.context.scene["truth_status"] = "inactive_unmodified_workspace_waiting_for_reviewed_semantic_selections"

    baseline_after = object_snapshot(body, armature)
    immutable_keys = (
        "body_object_name",
        "body_mesh_name",
        "armature_object_name",
        "armature_data_name",
        "vertex_count",
        "edge_count",
        "polygon_count",
        "loop_count",
        "topology_face_index_sha256",
        "mixed_surface_position_sha256",
        "shape_keys",
        "uv",
        "weights",
        "rig",
        "body_matrix_world",
        "armature_matrix_world",
        "material_slot_count",
        "material_slot_names",
    )
    if any(baseline_before[key] != baseline_after[key] for key in immutable_keys):
        raise RuntimeError("workspace preparation changed R6 geometry, rig, weights, UVs, or materials")

    baseline_record = {
        "schema_version": 1,
        "workspace_id": config["workspace_id"],
        "source": {
            "project_path": str(source.relative_to(project_root)).replace("\\", "/"),
            "sha256": config["source_sha256"],
        },
        "exact_import_snapshot": baseline_before,
        "protection_strategy": {
            "full_surface_baseline_duplicate_created": True,
            "entire_working_surface_exact_at_preparation": True,
            "therefore_existing_head_and_single_mouth_exact_at_preparation": True,
            "separate_mouth_mesh_created": False,
            "future_partial_protection_requires_reviewed_mask": True,
        },
        "truth_limits": {
            "complete_adult_anatomy_proven": False,
            "stable_working_rig_proven": False,
            "semantic_body_regions_selected": False,
            "localized_coloration_possible": False,
            "candidate_model_exists": False,
            "runtime_activation_allowed": False,
        },
    }
    Path(config["baseline_path"]).write_text(
        json.dumps(baseline_record, indent=2) + "\n", encoding="utf-8"
    )

    registry = {
        "schema_version": 1,
        "workspace_id": config["workspace_id"],
        "source_sha256": config["source_sha256"],
        "storage": {
            "type": "Blender mesh point-domain FLOAT attributes",
            "body_object": body.name,
            "vertex_domain_count": len(body.data.vertices),
            "skin_vertex_groups_changed": False,
            "skin_weights_changed": False,
        },
        "masks": [
            {
                "attribute": name,
                "meaning": meaning,
                "gate": gate,
                "initial_nonzero_vertex_count": 0,
                "selection_state": "empty_unreviewed_no_automated_region_guess",
                "human_review_required": True,
            }
            for name, meaning, gate in MASK_SPECS
        ],
        "uv_rasterization": {
            "allowed": False,
            "reason": "No semantic vertex selection has been reviewed; no UV pixels may be guessed.",
            "future_requirement": "Rasterize only reviewed selection indices, then run non-overlap and seam/bleed audits.",
        },
    }
    Path(config["registry_path"]).write_text(
        json.dumps(registry, indent=2) + "\n", encoding="utf-8"
    )

    selection_template = {
        "schema_version": 1,
        "workspace_id": config["workspace_id"],
        "source_sha256": config["source_sha256"],
        "reviewed": False,
        "reviewer": "",
        "review_scope": "manual topological selection on exact unchanged Kira R7 working mesh",
        "masks": {
            name: {
                "meaning_confirmed": False,
                "vertex_count": None,
                "vertex_index_sha256": "",
            }
            for name, _meaning, _gate in MASK_SPECS
        },
        "warning": "Do not set reviewed=true until the exact selections have been visually/topologically inspected. The audit validates hashes but cannot identify anatomy by itself.",
    }
    Path(config["selection_template_path"]).write_text(
        json.dumps(selection_template, indent=2) + "\n", encoding="utf-8"
    )

    protected_collection.hide_render = True
    protected_collection.hide_viewport = True
    rig_collection.hide_select = True
    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    body.hide_select = False
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.context.scene.tool_settings.mesh_select_mode = (True, False, False)

    workspace_path = Path(config["workspace_path"]).resolve()
    bpy.ops.wm.save_as_mainfile(filepath=str(workspace_path), check_existing=False, compress=True)
    if not workspace_path.is_file():
        raise RuntimeError("Blender did not save the R7 workspace")

    manifest = {
        "schema_version": 1,
        "workspace_id": config["workspace_id"],
        "status": "inactive_unmodified_workspace_waiting_for_manual_semantic_selection",
        "source_sha256": config["source_sha256"],
        "workspace": {
            "path": str(workspace_path.relative_to(project_root)).replace("\\", "/"),
            "sha256": sha256_file(workspace_path),
        },
        "exact_preservation": {
            "whole_surface_position_hash_preserved": True,
            "shape_key_coordinates_and_values_preserved": True,
            "face_index_topology_preserved": True,
            "uv_preserved": True,
            "skin_vertex_group_names_and_order_preserved": True,
            "skin_weight_assignments_preserved": True,
            "bone_count": 79,
            "bone_names_order_parents_and_rest_matrices_preserved": True,
            "maximum_positive_influences": baseline_after["weights"]["maximum_positive_influences"],
            "existing_single_mouth_preserved_as_part_of_exact_whole_surface": True,
            "second_mouth_created": False,
        },
        "semantic_mask_scaffold": {
            "attribute_count": len(MASK_SPECS),
            "all_attributes_empty": True,
            "automated_body_region_selection_used": False,
            "skin_vertex_groups_changed": False,
            "localized_color_applied": False,
        },
        "outputs": {
            "candidate_glb_created": False,
            "runtime_binding_changed": False,
            "avatar_builder_binding_changed": False,
            "home_world_changed": False,
        },
        "gates": {
            "geometry_authoring_allowed": False,
            "localized_coloration_allowed": False,
            "anatomical_completeness_proven": False,
            "stable_working_rig_proven": False,
            "owner_approved": False,
            "runtime_activation_allowed": False,
            "autobuild_allowed": False,
        },
    }
    Path(config["manifest_path"]).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"ok": True, **manifest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
