#!/usr/bin/env python3
"""Inventory one exact private candidate GLB in a second clean process.

This stage imports only into an unsaved in-memory factory scene.  It reports
body, rig, animation, material, hair curve-to-mesh, custom-property, and morph
survival without claiming visual acceptance or runtime qualification.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import traceback
from typing import Any, Mapping

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_profiled_kira_candidate_audit_contract import (  # noqa: E402
    GLB_EVIDENCE_NAME,
    evaluate_glb_append_preflight,
    inventory_glb_container,
    sha256_file,
    verify_inputs_unchanged,
)


AUDITOR_ID = "profiled_kira_private_glb_fresh_import_inventory_v1"
HAIR_RESPONSE_KEYS = (
    "hair_wind_left_dry",
    "hair_wind_right_dry",
    "hair_wet_neutral",
    "hair_wet_wind_left",
    "hair_wet_wind_right",
)
HAIR_TOKENS = ("hair", "groom", "responsive")


class ProfiledKiraPrivateGlbAuditError(RuntimeError):
    """Raised when the isolated GLB inventory cannot safely continue."""


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="Fresh-process private GLB inventory")
    parser.add_argument("--glb", required=True)
    parser.add_argument("--glb-sha256", required=True)
    parser.add_argument("--audit-output-dir", required=True)
    parser.add_argument("--main-evidence-sha256", required=True)
    return parser.parse_args(argv)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ProfiledKiraPrivateGlbAuditError(f"JSON root must be an object: {path}")
    return value


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _relative(path: Path) -> str:
    return path.resolve(strict=True).relative_to(PROJECT_ROOT.resolve(strict=True)).as_posix()


def _factory_startup_fingerprint() -> dict[str, Any]:
    objects = sorted((obj.name, obj.type) for obj in bpy.data.objects)
    result = {
        "background": bool(bpy.app.background),
        "blend_filepath_empty": bpy.data.filepath == "",
        "scene_names": sorted(scene.name for scene in bpy.data.scenes),
        "objects": [{"name": name, "type": kind} for name, kind in objects],
        "library_count": len(bpy.data.libraries),
        "expected_command_flags": [
            "--background", "--factory-startup", "--disable-autoexec"
        ],
    }
    result["passed"] = bool(
        result["background"]
        and result["blend_filepath_empty"]
        and result["scene_names"] == ["Scene"]
        and objects == [("Camera", "CAMERA"), ("Cube", "MESH"), ("Light", "LIGHT")]
        and result["library_count"] == 0
    )
    return result


def _clear_factory_objects_in_memory() -> None:
    """Remove only the disposable factory objects from the unsaved scene."""

    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def _shape_keys(obj: bpy.types.Object) -> list[str]:
    data = getattr(obj, "data", None)
    keys = getattr(data, "shape_keys", None)
    return [block.name for block in keys.key_blocks] if keys is not None else []


def _materials(obj: bpy.types.Object) -> list[str]:
    return [slot.material.name for slot in obj.material_slots if slot.material is not None]


def _mesh_record(obj: bpy.types.Object) -> dict[str, Any]:
    mesh = obj.data
    return {
        "name": obj.name,
        "candidate_id_extra": obj.get("candidate_id"),
        "primary_surface_extra": obj.get("primary_surface"),
        "vertex_count": len(mesh.vertices),
        "edge_count": len(mesh.edges),
        "polygon_count": len(mesh.polygons),
        "material_names": _materials(obj),
        "shape_key_names": _shape_keys(obj),
        "armature_modifiers": [
            {
                "name": modifier.name,
                "target": modifier.object.name if modifier.object is not None else None,
                "use_vertex_groups": bool(modifier.use_vertex_groups),
            }
            for modifier in obj.modifiers
            if modifier.type == "ARMATURE"
        ],
    }


def _object_record(obj: bpy.types.Object) -> dict[str, Any]:
    return {
        "name": obj.name,
        "type": obj.type,
        "data_name": getattr(getattr(obj, "data", None), "name", None),
        "candidate_id_extra": obj.get("candidate_id"),
        "private_owner_review_only_extra": obj.get("private_owner_review_only"),
        "inactive_candidate_extra": obj.get("inactive_candidate"),
        "runtime_activation_allowed_extra": obj.get("runtime_activation_allowed"),
        "material_names": _materials(obj),
        "shape_key_names": _shape_keys(obj),
        "hair_wind_direction_extra": obj.get("hair_wind_direction_minus1_1"),
        "hair_wetness_extra": obj.get("hair_wetness_0_1"),
    }


def _action_records() -> list[dict[str, Any]]:
    return [
        {
            "name": action.name,
            "frame_range": [float(action.frame_range[0]), float(action.frame_range[1])],
            "fake_user": bool(action.use_fake_user),
        }
        for action in sorted(bpy.data.actions, key=lambda item: item.name)
    ]


def _expected_source_inventory(main: Mapping[str, Any]) -> dict[str, Any]:
    audit = main.get("audit_result") if isinstance(main.get("audit_result"), Mapping) else {}
    safety = audit.get("safety_metadata") if isinstance(audit.get("safety_metadata"), Mapping) else {}
    raw_objects = safety.get("candidate_objects")
    source_objects = raw_objects if isinstance(raw_objects, Mapping) else {}
    expected_actions = audit.get("action_inventory")
    if not isinstance(expected_actions, list):
        expected_actions = []
    return {
        "candidate_id": audit.get("candidate_id") or main.get("preflight", {}).get("resolved", {}).get("candidate_id"),
        "objects": source_objects,
        "action_names": sorted(
            str(record.get("name"))
            for record in expected_actions
            if isinstance(record, Mapping) and record.get("name")
        ),
    }


def _inventory_import(main: Mapping[str, Any], candidate_id: str) -> dict[str, Any]:
    objects = list(bpy.data.objects)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    armatures = [obj for obj in objects if obj.type == "ARMATURE"]
    marked_primary = [obj for obj in meshes if obj.get("primary_surface") is True]
    expected = _expected_source_inventory(main)
    source_objects = expected["objects"]
    expected_primary_names = sorted(
        str(name)
        for name, record in source_objects.items()
        if isinstance(record, Mapping) and record.get("primary_surface") is True
    )
    imported_by_name = {obj.name: obj for obj in objects}
    exact_name_body = (
        imported_by_name.get(expected_primary_names[0])
        if len(expected_primary_names) == 1
        else None
    )
    largest_fallback = max(meshes, key=lambda obj: len(obj.data.vertices)) if meshes else None
    body = (
        marked_primary[0]
        if len(marked_primary) == 1
        else exact_name_body
        if exact_name_body is not None and exact_name_body.type == "MESH"
        else largest_fallback
    )
    expected_hair = {
        str(name): record
        for name, record in source_objects.items()
        if any(token in str(name).lower() for token in HAIR_TOKENS)
    }
    object_survival: dict[str, Any] = {}
    for name, raw_source in source_objects.items():
        source = raw_source if isinstance(raw_source, Mapping) else {}
        imported = imported_by_name.get(str(name))
        expected_shapes = sorted(str(value) for value in source.get("shape_key_names", []))
        actual_shapes = sorted(_shape_keys(imported)) if imported is not None else []
        expected_object_materials = sorted(
            str(value) for value in source.get("material_names", [])
        )
        actual_object_materials = sorted(_materials(imported)) if imported is not None else []
        object_survival[str(name)] = {
            "source_type": source.get("type"),
            "imported_type": imported.type if imported is not None else None,
            "object_name_survived": imported is not None,
            "candidate_id_extra_survived": bool(
                imported is not None and imported.get("candidate_id") == candidate_id
            ),
            "expected_shape_keys": expected_shapes,
            "imported_shape_keys": actual_shapes,
            "missing_shape_keys": sorted(set(expected_shapes).difference(actual_shapes)),
            "expected_material_names": expected_object_materials,
            "imported_material_names": actual_object_materials,
            "missing_material_names": sorted(
                set(expected_object_materials).difference(actual_object_materials)
            ),
        }
    hair_survival: dict[str, Any] = {}
    for name, raw_source in expected_hair.items():
        source = raw_source if isinstance(raw_source, Mapping) else {}
        imported = imported_by_name.get(name)
        expected_type = str(source.get("type") or "")
        expected_shapes = sorted(str(value) for value in source.get("shape_key_names", []))
        actual_shapes = sorted(_shape_keys(imported)) if imported is not None else []
        if imported is None:
            type_survival = "MISSING_AFTER_IMPORT"
        elif imported.type == expected_type:
            type_survival = "NATIVE_TYPE_SURVIVED"
        elif expected_type == "CURVE" and imported.type == "MESH":
            type_survival = "CURVE_CONVERTED_TO_MESH"
        else:
            type_survival = f"TYPE_CHANGED_{expected_type}_TO_{imported.type}"
        hair_survival[name] = {
            "source_type": expected_type,
            "imported_type": imported.type if imported is not None else None,
            "type_survival": type_survival,
            "expected_shape_keys": expected_shapes,
            "imported_shape_keys": actual_shapes,
            "missing_shape_keys": sorted(set(expected_shapes).difference(actual_shapes)),
            "response_shape_keys_expected": sorted(
                key for key in expected_shapes if key in HAIR_RESPONSE_KEYS
            ),
            "response_shape_keys_survived": sorted(
                key for key in actual_shapes if key in HAIR_RESPONSE_KEYS
            ),
            "wind_property_survived": bool(
                imported is not None and "hair_wind_direction_minus1_1" in imported
            ),
            "wet_property_survived": bool(
                imported is not None and "hair_wetness_0_1" in imported
            ),
        }
    expected_materials = sorted(
        {
            str(material)
            for record in source_objects.values()
            if isinstance(record, Mapping)
            for material in record.get("material_names", [])
        }
    )
    actual_materials = sorted(material.name for material in bpy.data.materials)
    expected_actions = expected["action_names"]
    actions = _action_records()
    action_names = sorted(record["name"] for record in actions)
    body_record = _mesh_record(body) if body is not None else None
    candidate_armatures = [obj for obj in armatures if obj.get("candidate_id") == candidate_id]
    intended_armature = candidate_armatures[0] if len(candidate_armatures) == 1 else None
    body_skin_binding = bool(
        body is not None
        and intended_armature is not None
        and any(
            modifier.type == "ARMATURE" and modifier.object == intended_armature
            for modifier in body.modifiers
        )
    )
    survival = {
        "readable_nonempty_import": bool(objects and meshes),
        "exactly_one_primary_surface_extra_survived": len(marked_primary) == 1,
        "primary_body_selection_used_fallback": len(marked_primary) != 1 and body is not None,
        "exactly_one_candidate_armature_extra_survived": len(candidate_armatures) == 1,
        "body_skin_binding_survived": body_skin_binding,
        "all_expected_actions_survived_by_exact_name": set(expected_actions).issubset(action_names),
        "all_expected_materials_survived_by_exact_name": set(expected_materials).issubset(actual_materials),
    }
    return {
        "candidate_id": candidate_id,
        "object_count": len(objects),
        "objects": [_object_record(obj) for obj in sorted(objects, key=lambda item: item.name)],
        "source_to_fresh_import_object_and_morph_survival": object_survival,
        "mesh_count": len(meshes),
        "meshes": [_mesh_record(obj) for obj in sorted(meshes, key=lambda item: item.name)],
        "armature_count": len(armatures),
        "armatures": [
            {
                "name": obj.name,
                "candidate_id_extra": obj.get("candidate_id"),
                "bone_count": len(obj.data.bones),
            }
            for obj in sorted(armatures, key=lambda item: item.name)
        ],
        "selected_primary_body": body_record,
        "expected_primary_body_names_from_blend_audit": expected_primary_names,
        "primary_body_fallback_order": [
            "surviving_primary_surface_extra",
            "exact_source_primary_object_name",
            "largest_mesh_inventory_fallback",
        ],
        "actions": actions,
        "expected_action_names_from_blend_audit": expected_actions,
        "missing_expected_action_names": sorted(set(expected_actions).difference(action_names)),
        "materials": actual_materials,
        "expected_material_names_from_blend_audit": expected_materials,
        "missing_expected_material_names": sorted(set(expected_materials).difference(actual_materials)),
        "hair_curve_to_mesh_and_morph_survival": hair_survival,
        "survival_checks": survival,
        "fresh_import_engineering_readable": bool(
            survival["readable_nonempty_import"]
            and body is not None
            and len(armatures) >= 1
        ),
        "runtime_qualified": False,
    }


def run(args: argparse.Namespace) -> tuple[dict[str, Any], Path | None]:
    preflight = evaluate_glb_append_preflight(
        PROJECT_ROOT,
        glb_path=args.glb,
        glb_sha256=args.glb_sha256,
        audit_output_dir=args.audit_output_dir,
        main_evidence_sha256=args.main_evidence_sha256,
    )
    if preflight["ready"] is not True:
        return {
            "schema_version": 1,
            "audit": AUDITOR_ID,
            "status": "BLOCKED_BEFORE_PRIVATE_GLB_IMPORT_NO_EVIDENCE_WRITTEN",
            "preflight": preflight,
        }, None
    resolved = preflight["resolved"]
    glb_path = PROJECT_ROOT / resolved["glb"]["path"]
    main_path = PROJECT_ROOT / resolved["main_evidence"]["path"]
    evidence_path = PROJECT_ROOT / resolved["fresh_evidence_path"]
    bindings = {"glb": resolved["glb"], "main_evidence": resolved["main_evidence"]}
    before = {
        label: {
            "path": record["path"],
            "sha256": sha256_file(PROJECT_ROOT / record["path"]),
            "size_bytes": (PROJECT_ROOT / record["path"]).stat().st_size,
        }
        for label, record in bindings.items()
    }
    before_matches_preflight = all(
        before[label]["sha256"] == bindings[label]["sha256"]
        for label in bindings
    )
    factory = _factory_startup_fingerprint()
    inventory: dict[str, Any] | None = None
    partial_scene_after_import_error: dict[str, Any] | None = None
    container_inventory: dict[str, Any] | None = None
    fatal: dict[str, Any] | None = None
    try:
        container_inventory = inventory_glb_container(glb_path)
    except Exception as exc:
        fatal = {
            "error_type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
            "stage": "GLB_CONTAINER_INVENTORY_BEFORE_BLENDER_IMPORT",
        }
    if factory["passed"] and before_matches_preflight and fatal is None:
        try:
            main = _read_json(main_path)
            candidate_id = str(resolved["candidate_id"])
            main_candidate_id = str(
                main.get("preflight", {}).get("resolved", {}).get("candidate_id") or ""
            )
            if main_candidate_id != candidate_id:
                raise ProfiledKiraPrivateGlbAuditError("main evidence candidate ID mismatch")
            _clear_factory_objects_in_memory()
            bpy.ops.import_scene.gltf(filepath=str(glb_path))
            bpy.context.view_layer.update()
            inventory = _inventory_import(main, candidate_id)
        except Exception as exc:
            partial_objects = list(bpy.data.objects)
            partial_scene_after_import_error = {
                "object_count": len(partial_objects),
                "objects": [
                    _object_record(obj)
                    for obj in sorted(partial_objects, key=lambda item: item.name)
                ],
                "action_inventory": _action_records(),
                "complete_fresh_import_survival_proven": False,
                "partial_scene_is_diagnostic_only": True,
            }
            fatal = {
                "error_type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
                "stage": "BLENDER_5_1_GLTF_IMPORT",
            }
    elif fatal is not None:
        pass
    elif not factory["passed"]:
        fatal = {
            "error_type": "UnsafeStartupFingerprint",
            "message": "fresh background factory-startup fingerprint did not pass",
        }
    else:
        fatal = {
            "error_type": "InputChangedAfterPreflight",
            "message": "an exact input changed between preflight and private GLB import",
        }
    unchanged = verify_inputs_unchanged(PROJECT_ROOT, bindings)
    completed = bool(inventory and fatal is None and unchanged["passed"])
    no_observed_losses = bool(
        completed
        and inventory["survival_checks"]["exactly_one_primary_surface_extra_survived"]
        and inventory["survival_checks"]["exactly_one_candidate_armature_extra_survived"]
        and inventory["survival_checks"]["body_skin_binding_survived"]
        and inventory["survival_checks"]["all_expected_actions_survived_by_exact_name"]
        and inventory["survival_checks"]["all_expected_materials_survived_by_exact_name"]
        and all(
            record["object_name_survived"]
            and not record["missing_shape_keys"]
            and not record["missing_material_names"]
            for record in inventory[
                "source_to_fresh_import_object_and_morph_survival"
            ].values()
        )
        and all(
            not record["missing_shape_keys"] and record["type_survival"] == "NATIVE_TYPE_SURVIVED"
            for record in inventory["hair_curve_to_mesh_and_morph_survival"].values()
        )
    )
    evidence = {
        "schema_version": 1,
        "audit": AUDITOR_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "FRESH_IMPORT_INVENTORY_COMPLETED_NO_OBSERVED_SURVIVAL_LOSS"
            if no_observed_losses
            else "FRESH_IMPORT_INVENTORY_COMPLETED_WITH_RECORDED_SURVIVAL_FINDINGS"
            if completed
            else "FRESH_IMPORT_INVENTORY_BLOCKED"
        ),
        "inventory_completed": completed,
        "no_observed_survival_loss": no_observed_losses,
        "preflight": preflight,
        "factory_startup_fingerprint": factory,
        "input_files_before": before,
        "input_files_still_matched_preflight_before_import": before_matches_preflight,
        "input_integrity_after": unchanged,
        "inventory": inventory,
        "glb_container_inventory_before_import": container_inventory,
        "partial_scene_after_import_error": partial_scene_after_import_error,
        "fatal_error": fatal,
        "implementation_hashes": {
            "tools/blender_fresh_import_profiled_kira_private_glb.py": sha256_file(
                PROJECT_ROOT / "tools/blender_fresh_import_profiled_kira_private_glb.py"
            ),
            "Core/avatar_profiled_kira_candidate_audit_contract.py": sha256_file(
                PROJECT_ROOT / "Core/avatar_profiled_kira_candidate_audit_contract.py"
            ),
        },
        "truth_boundaries": {
            "candidate_blend_opened": False,
            "candidate_or_glb_modified": False,
            "factory_scene_objects_removed_in_memory_only": bool(factory["passed"]),
            "render_performed": False,
            "blend_saved": False,
            "export_performed": False,
            "activation_performed": False,
            "visual_acceptance_performed": False,
            "runtime_loaded_or_exercised": False,
            "runtime_qualified": False,
            "activation_allowed": False,
        },
    }
    if evidence_path.exists():
        raise ProfiledKiraPrivateGlbAuditError("refusing to overwrite GLB audit evidence")
    with evidence_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(_json_safe(evidence), stream, indent=2, sort_keys=True)
        stream.write("\n")
    return evidence, evidence_path


def main() -> int:
    evidence, path = run(_arguments())
    print(
        json.dumps(
            {
                "status": evidence["status"],
                "inventory_completed": evidence.get("inventory_completed", False),
                "evidence_path": _relative(path) if path is not None else None,
                "evidence_sha256": sha256_file(path) if path is not None else None,
                "runtime_qualified": False,
                "activation_allowed": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if evidence.get("inventory_completed") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
