"""Static-first Attempt 33 orchestration for the bounded R24 reconstruction.

This module keeps Attempt 31's exact candidate and reconstruction engine
byte-bound, replacing only its obsolete singleton patch loader with the exact
Attempt 16 seven-object/signature/six-dependency cleanup contract.  Blender is
not imported during static validation.  A later separately reviewed run is
in-memory and no-save only.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT33_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = "715163fe202baccb219d385e162d944e67f2b06b0ce656ce17d41e5a00a0840a"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def project_path(relative: str, *, must_exist: bool = True) -> Path:
    candidate = (ROOT / relative).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError as error:
        raise RuntimeError(f"Attempt 33 path escapes project: {relative}") from error
    if must_exist and not candidate.is_file():
        raise RuntimeError(f"Attempt 33 bound file is absent: {relative}")
    return candidate


def file_record(path: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def require_record(label: str, record: Mapping[str, object]) -> dict[str, object]:
    path = project_path(str(record["path"]))
    actual = file_record(path)
    if actual["bytes"] != int(record["bytes"]):
        raise RuntimeError(f"Attempt 33 bound byte count drifted: {label}")
    if actual["sha256"] != str(record["sha256"]):
        raise RuntimeError(f"Attempt 33 bound SHA-256 drifted: {label}")
    return actual


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Attempt 33 cannot load provider: {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 33 requires the exact configured manifest path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 33 config SHA-256 drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_33"
        or config.get("status") != "STATIC_DIAGNOSTIC_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 33 identity drifted")
    scope = config["scope"]
    for key in (
        "append_only",
        "private",
        "inactive",
        "unassigned",
        "unpublished",
        "diagnostic_only",
        "later_reviewed_blender_launch_required",
        "in_memory_patch_append_cleanup_allowed_only_after_exact_gates",
        "in_memory_reconstruction_and_graft_allowed_only_after_exact_gates",
        "append_only_json_evidence_allowed_during_later_run",
    ):
        if scope.get(key) is not True:
            raise RuntimeError(f"Attempt 33 required scope drifted: {key}")
    for key in (
        "source_file_mutation_allowed",
        "prior_evidence_mutation_allowed",
        "render_allowed",
        "blend_save_allowed",
        "export_allowed",
        "runtime_activation_allowed",
        "assignment_allowed",
        "publication_allowed",
        "quality_gate_reduction_allowed",
        "automatic_retry_allowed",
    ):
        if scope.get(key) is not False:
            raise RuntimeError(f"Attempt 33 forbidden scope drifted: {key}")
    output = config["runtime_overlay"]["output"]
    if output != {
        "root": "RecoverySprint/continuation_20260803/kira_r24_internal_midpoint_fair_surface/attempt_33",
        "started": "ATTEMPT_STARTED.json",
        "diagnostic": "TRIANGULATION_RECONSTRUCTION_DIAGNOSTIC.json",
        "failure": "FAILURE.json",
        "blend_save_permitted": False,
        "render_permitted": False,
    }:
        raise RuntimeError("Attempt 33 output overlay drifted")
    contract = config["attempt16_append_contract"]
    names = list(contract["expected_appended_object_names"])
    dependencies = list(contract["dependency_object_names_removed_in_memory_only"])
    if (
        len(names) != 7
        or canonical_sha256(names)
        != contract["expected_appended_object_names_sha256"]
        or dependencies != sorted(name for name in names if name != "Object_23")
        or canonical_sha256(dependencies) != contract["dependency_object_names_sha256"]
        or list(contract["expected_new_collection_names"]) != []
        or canonical_sha256([]) != contract["expected_new_collection_names_sha256"]
    ):
        raise RuntimeError("Attempt 33 exact Attempt 16 append contract drifted")
    requested = contract["requested_patch"]
    if requested != {
        "object_name": "Object_23",
        "object_type": "MESH",
        "mesh_name_prefix": "Ariel_Mesh_Genitalia_0",
        "source_armature_modifier_object": "Object_4",
    }:
        raise RuntimeError("Attempt 33 requested patch signature drifted")
    launch = config["launch_contract"]
    if (
        launch["worker"]
        != "tools/blender_diagnose_kira_r24_blackproject_candidate_attempt33.py"
        or launch["config"]
        != "RecoverySprint/continuation_20260808/R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT33_CONFIG.json"
        or launch["executed_during_static_preparation"] is not False
    ):
        raise RuntimeError("Attempt 33 launch contract drifted")
    if project_path(str(output["root"]), must_exist=False).exists():
        raise RuntimeError("Attempt 33 output already exists")


def verify_overlay(config: Mapping[str, Any]) -> dict[str, object]:
    records = {
        str(label): require_record(str(label), record)
        for label, record in config["bindings"].items()
    }
    records["proposal"] = require_record("proposal", config["proposal"])
    attempt32 = json.loads(
        project_path(str(records["attempt32_inventory"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    if (
        attempt32["status"]
        != "PASS_EXACT_SEVEN_OBJECT_HIERARCHY_NO_NEW_COLLECTIONS_NO_SAVE"
        or attempt32["append_observation"]["actual_appended_object_names_sha256"]
        != config["attempt16_append_contract"]["expected_appended_object_names_sha256"]
        or attempt32["append_observation"]["actual_new_collection_names"] != []
        or not attempt32["sealed_body_pre_post_exact"]
        or not attempt32["bound_files_pre_post_exact"]
        or any(
            attempt32[key]
            for key in (
                "scene_link_reached",
                "dependency_cleanup_reached",
                "geometry_mutation_reached",
                "triangulation_reached",
                "reconstruction_reached",
                "graft_reached",
                "render_reached",
                "blend_saved",
                "runtime_changed",
            )
        )
    ):
        raise RuntimeError("Attempt 33 bound Attempt 32 pass truth drifted")
    external = json.loads(
        project_path(str(records["attempt32_external_integrity"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    if (
        external["blender_exit_code"] != 0
        or external["native_invocation_error"] is not None
        or external["pre_post_exact"] is not True
        or external["before"] != external["after"]
    ):
        raise RuntimeError("Attempt 33 bound Attempt 32 external integrity drifted")
    attempt16 = json.loads(
        project_path(str(records["attempt16_config"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    if attempt16["append_contract"] != config["attempt16_append_contract"]:
        raise RuntimeError("Attempt 33 does not reuse the exact Attempt 16 contract")
    return {"records": records, "attempt32_status": attempt32["status"]}


def object_signature(value: Any) -> dict[str, object]:
    return {
        "name": value.name,
        "type": value.type,
        "data_name": value.data.name if value.data is not None else None,
        "parent_name": value.parent.name if value.parent is not None else None,
        "collection_names": sorted(collection.name for collection in value.users_collection),
        "modifiers": [
            {
                "name": modifier.name,
                "type": modifier.type,
                "object": getattr(getattr(modifier, "object", None), "name", None),
            }
            for modifier in value.modifiers
        ],
    }


def relabel_base_evidence(
    value: Mapping[str, Any], orchestration: Mapping[str, Any]
) -> dict[str, Any]:
    result = deepcopy(dict(value))
    if isinstance(result.get("schema"), str):
        result["schema"] = result["schema"].replace("attempt31", "attempt33")
    if result.get("attempt_id") == "attempt_31":
        result["attempt_id"] = "attempt_33"
    if isinstance(result.get("status"), str):
        result["status"] = result["status"].replace("ATTEMPT31", "ATTEMPT33")
    if isinstance(result.get("reason"), str):
        result["reason"] = result["reason"].replace("Attempt 31", "Attempt 33")
    result["attempt33_orchestration"] = deepcopy(dict(orchestration))
    return result


def run_blender(config_path: Path, config: Mapping[str, Any]) -> None:
    # These imports remain unreachable during static validation.
    import bpy  # type: ignore

    overlay_verified = verify_overlay(config)
    base_worker = project_path(str(config["bindings"]["attempt31_worker"]["path"]))
    base_config_path = project_path(
        str(config["bindings"]["attempt31_config"]["path"])
    )
    base = load_module("attempt33_bound_attempt31", base_worker)
    if sha256_file(Path(base.__file__).resolve()) != config["bindings"]["attempt31_worker"]["sha256"]:
        raise RuntimeError("Attempt 33 imported Attempt 31 engine drifted")
    base_config = base.load_config(base_config_path)
    base_verified = base.verify_bindings(base_config)
    runtime_config = deepcopy(base_config)
    runtime_config["output"] = deepcopy(config["runtime_overlay"]["output"])

    output = project_path(str(runtime_config["output"]["root"]), must_exist=False)
    contract = config["attempt16_append_contract"]
    expected_names = list(contract["expected_appended_object_names"])
    dependencies = list(contract["dependency_object_names_removed_in_memory_only"])
    requested_contract = contract["requested_patch"]
    orchestration = {
        "worker": file_record(Path(__file__).resolve()),
        "config": file_record(config_path),
        "base_attempt31_worker": overlay_verified["records"]["attempt31_worker"],
        "base_attempt31_config": overlay_verified["records"]["attempt31_config"],
        "append_provider_contract": "EXACT_ATTEMPT16_SEVEN_OBJECT_SIGNATURE_SIX_DEPENDENCY_CLEANUP",
        "attempt32_runtime_authority": overlay_verified["records"]["attempt32_inventory"],
        "render_permitted": False,
        "blend_save_permitted": False,
    }

    original_loader = base._load_module
    original_writer = base._exclusive_write_once
    original_default_config = base.DEFAULT_CONFIG

    def write_base_evidence(path: Path, value: Mapping[str, Any]) -> None:
        original_writer(path, relabel_base_evidence(value, orchestration))

    def corrected_append_patch(path: Path, object_name: str) -> Any:
        body = bpy.data.objects.get(runtime_config["objects"]["body"])
        if body is None or body.type != "MESH":
            raise RuntimeError("Attempt 33 sealed body is absent before append")
        before_objects = set(bpy.data.objects)
        before_collections = set(bpy.data.collections)
        with bpy.data.libraries.load(str(path), link=False) as (source, target):
            if object_name not in source.objects:
                raise RuntimeError("Attempt 33 preserved patch lacks Object_23")
            target.objects = [object_name]
        returned = list(target.objects)
        appended = sorted(
            (value for value in bpy.data.objects if value not in before_objects),
            key=lambda value: value.name,
        )
        actual_names = [value.name for value in appended]
        new_collections = sorted(
            value.name for value in bpy.data.collections if value not in before_collections
        )
        signatures = [object_signature(value) for value in appended]
        inventory = {
            "schema": "kira.avatar.r24.blackproject_attempt33.append_inventory.v1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PASS_EXACT_SEVEN_OBJECT_HIERARCHY_NO_NEW_COLLECTIONS_BEFORE_CLEANUP",
            "requested_object": object_name,
            "returned_target_slots": [
                {
                    "index": index,
                    "is_none": value is None,
                    "name": getattr(value, "name", None),
                    "type": getattr(value, "type", None),
                    "data_name": getattr(getattr(value, "data", None), "name", None),
                }
                for index, value in enumerate(returned)
            ],
            "expected_appended_object_names": expected_names,
            "expected_appended_object_names_sha256": canonical_sha256(expected_names),
            "actual_appended_object_names": actual_names,
            "actual_appended_object_names_sha256": canonical_sha256(actual_names),
            "expected_new_collection_names": [],
            "actual_new_collection_names": new_collections,
            "object_signatures": signatures,
            "dependency_cleanup_reached": False,
            "geometry_mutation_reached": False,
            "render_reached": False,
            "blend_saved": False,
        }
        inventory_path = output / str(contract["inventory_evidence_filename"])
        if len(returned) != 1 or returned[0] is None or returned[0].name != object_name:
            inventory["status"] = "FAIL_RETURNED_TARGET_SLOT_DRIFT_BEFORE_CLEANUP"
            original_writer(inventory_path, inventory)
            raise RuntimeError("Attempt 33 returned target slot drifted")
        if actual_names != expected_names or new_collections != []:
            inventory["status"] = "FAIL_APPEND_INVENTORY_DRIFT_BEFORE_CLEANUP"
            original_writer(inventory_path, inventory)
            raise RuntimeError("Attempt 33 exact append inventory drifted")
        if any(signature["collection_names"] for signature in signatures):
            inventory["status"] = "FAIL_COLLECTION_LINK_DRIFT_BEFORE_CLEANUP"
            original_writer(inventory_path, inventory)
            raise RuntimeError("Attempt 33 appended object is already collection-linked")
        by_name = {signature["name"]: signature for signature in signatures}
        patch_signature = by_name.get(object_name)
        expected_modifier = {
            "name": "Armature",
            "type": "ARMATURE",
            "object": requested_contract["source_armature_modifier_object"],
        }
        if (
            patch_signature is None
            or patch_signature["type"] != requested_contract["object_type"]
            or patch_signature["data_name"] != requested_contract["mesh_name_prefix"]
            or patch_signature["parent_name"]
            != requested_contract["source_armature_modifier_object"]
            or patch_signature["modifiers"] != [expected_modifier]
        ):
            inventory["status"] = "FAIL_REQUESTED_PATCH_SIGNATURE_DRIFT_BEFORE_CLEANUP"
            original_writer(inventory_path, inventory)
            raise RuntimeError("Attempt 33 requested patch signature drifted")
        if sorted(name for name in actual_names if name != object_name) != dependencies:
            inventory["status"] = "FAIL_DEPENDENCY_SET_DRIFT_BEFORE_CLEANUP"
            original_writer(inventory_path, inventory)
            raise RuntimeError("Attempt 33 six-object dependency set drifted")
        original_writer(inventory_path, inventory)

        adult = next(value for value in appended if value.name == object_name)
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
        return adult

    def patched_loader(name: str, path: Path) -> Any:
        module = original_loader(name, path)
        if path.resolve() == project_path(
            str(config["bindings"]["attempt15_worker"]["path"])
        ):
            module.append_patch = corrected_append_patch
        return module

    base._load_module = patched_loader
    base._exclusive_write_once = write_base_evidence
    base.DEFAULT_CONFIG = config_path
    try:
        base.run_blender_diagnostic(runtime_config, base_verified)
    finally:
        base._load_module = original_loader
        base._exclusive_write_once = original_writer
        base.DEFAULT_CONFIG = original_default_config


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    verify_overlay(config)
    run_blender(config_path, config)


if __name__ == "__main__":
    main()
