#!/usr/bin/env python3
"""Append-only Kira R21 nail Attempt 03 worker.

The worker opens the exact hash-pinned R21 source, derives corrected nail
landmarks through the body's transform, constructs all twenty nails with the
weight-constrained connected-region adapter, and saves a candidate only when
every strict gate passes.  Partial successes are serialized as reusable top
surface components; no partial Blend is ever saved.

This file is prepared for an explicitly scheduled Blender run.  Importing or
syntax-checking it does not launch Blender or mutate a candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.kira_blackproject_nail_topology_v1 import (
    CACHE_SCHEMA,
    METHOD_ID,
    canonical_json_sha256,
    component_payload_sha256,
    expected_nail_inventory,
    validate_component_cache,
)
from tools import blender_avatar_blackproject_weight_constrained_nail_projection_v1 as projector
from tools import blender_avatar_natural_nail_delivery_v3 as nails
from tools import blender_author_kira_r21_nails_attempt01 as legacy


CONFIG_SCHEMA = "kira.r21.nail_attempt03.run_config.v1"
EVIDENCE_SCHEMA = "kira.r21.nail_attempt03.weight_constrained_evidence.v1"
FAILURE_SCHEMA = "kira.r21.nail_attempt03.weight_constrained_failure.v1"
BODY_NAME = "Kira_R21_Bald_Private_Inactive_Pelvis_Attempt01"
RIG_NAME = "Kira_R19_BlackProject_Native_188_Rig"


class KiraNailAttempt03Error(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = (ROOT / str(value)).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise KiraNailAttempt03Error(f"path escapes project root: {value}") from exc
    return path


def json_file(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise KiraNailAttempt03Error(f"JSON root is not an object: {path}")
    return value


def jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, Vector):
        return [float(item) for item in value]
    if isinstance(value, Path):
        return value.relative_to(ROOT).as_posix()
    if isinstance(value, float):
        if not math.isfinite(value):
            raise KiraNailAttempt03Error("evidence contains a non-finite float")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return str(value)


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def verify_config(config_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    config = json_file(config_path)
    if config.get("schema") != CONFIG_SCHEMA or int(config.get("attempt", 0)) != 3:
        raise KiraNailAttempt03Error("wrong Attempt03 config schema or attempt")
    if config.get("status") != "PREPARED_NOT_RUN":
        raise KiraNailAttempt03Error("config is not the prepared, unrun contract")
    source_contract = dict(config.get("source", {}))
    if source_contract.get("body_object") != BODY_NAME:
        raise KiraNailAttempt03Error("configured R21 body object changed")
    if source_contract.get("rig_object") != RIG_NAME:
        raise KiraNailAttempt03Error("configured R21 rig object changed")
    if config.get("reuse_components_from") is not None:
        reuse = dict(config["reuse_components_from"])
        if not all(
            reuse.get(field)
            for field in (
                "path",
                "sha256",
                "origin_run_config_sha256",
                "origin_source_blend_sha256",
                "origin_source_non_nail_manifest_sha256",
                "origin_rig_rest_sha256",
            )
        ):
            raise KiraNailAttempt03Error("reuse cache binding is incomplete")
    inventory = expected_nail_inventory()
    expected_ids = [row["nail_id"] for row in inventory]
    if list(config.get("exact_nail_inventory", [])) != expected_ids:
        raise KiraNailAttempt03Error("exact 20-nail inventory drifted")
    if len(config.get("corrected_reference_anchors_world_m", {})) != 20:
        raise KiraNailAttempt03Error("config does not bind all 20 corrected anchors")
    bindings = {}
    for label, row in dict(config.get("fixed_inputs", {})).items():
        path = project_path(str(row["path"]))
        if not path.is_file():
            raise KiraNailAttempt03Error(f"fixed input is missing: {label}")
        actual = sha256_file(path)
        if actual != str(row["sha256"]):
            raise KiraNailAttempt03Error(
                f"fixed input changed: {label}; expected={row['sha256']}; actual={actual}"
            )
        bindings[label] = {
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": actual,
        }
    required_true_gates = (
        "all_20_unique_nails_required",
        "one_connected_declared_digit_region_per_nail",
        "complete_9x9_grid_required",
        "minimum_expected_digit_family_weight_0_99",
        "maximum_foreign_digit_family_weight_0_01",
        "maximum_wrong_side_digit_weight_0_01",
        "median_exact_terminal_bone_weight_0_90",
        "minimum_outward_normal_alignment_0_12",
        "complete_evaluated_armature_then_solidify_shell",
        "zero_exact_genuine_body_penetrations",
        "minimum_clearance_m_0_000040",
        "maximum_clearance_m_0_000450",
        "body_mesh_unchanged",
        "body_modifier_stack_unchanged",
        "rig_rest_and_pose_unchanged",
        "all_non_nail_objects_unchanged",
        "no_automatic_bone_remap",
        "no_nail_to_nail_overlap",
        "candidate_blend_saved_only_after_every_gate_passes",
        "partial_successes_cacheable_but_not_saved_as_candidate_blend",
        "private_inactive_unassigned_unpublished",
    )
    gates = dict(config.get("strict_gates", {}))
    if any(gates.get(name) is not True for name in required_true_gates):
        raise KiraNailAttempt03Error("one or more mandatory Attempt03 gates is absent")
    constants = dict(config.get("method_constants", {}))
    actual_constants = {
        "projection_grid": [projector.PROJECTION_GRID_SIZE, projector.PROJECTION_GRID_SIZE],
        "maximum_ray_hits": projector.MAXIMUM_RAY_HITS,
        "ray_start_offset_m": projector.RAY_START_OFFSET_M,
        "ray_length_m": projector.RAY_LENGTH_M,
        "ray_advance_epsilon_m": projector.RAY_ADVANCE_EPSILON_M,
        "maximum_raw_cage_mapping_distance_m": projector.MAXIMUM_RAW_CAGE_MAPPING_DISTANCE_M,
        "minimum_expected_family_weight": projector.MINIMUM_EXPECTED_FAMILY_WEIGHT,
        "footprint_scale_candidates": list(projector.FOOTPRINT_SCALE_CANDIDATES),
        "center_fraction_candidates": list(projector.CENTER_FRACTION_CANDIDATES),
        "maximum_surface_clearance_m": projector.MAXIMUM_FINAL_CLEARANCE_M,
        "nail_plate_thickness_m": projector.NAIL_PLATE_THICKNESS_M,
        "normal_lift_step_m": projector.NORMAL_LIFT_STEP_M,
        "maximum_normal_lift_iterations": projector.MAXIMUM_NORMAL_LIFT_ITERATIONS,
    }
    drifted = {
        name: {"configured": constants.get(name), "actual": actual}
        for name, actual in actual_constants.items()
        if constants.get(name) != actual
    }
    if drifted:
        raise KiraNailAttempt03Error(f"Attempt03 method constants drifted: {drifted}")
    return config, bindings


def verify_r21_evidence_truth(config: Mapping[str, Any]) -> dict[str, Any]:
    evidence_binding = config["fixed_inputs"]["r21_build_evidence"]
    evidence = json_file(project_path(str(evidence_binding["path"])))
    expected = config["protected_r21_truth"]
    checks = {
        "nonpatch_vertex_coordinate_weight_sha256": (
            evidence["nonpatch_after"]["vertex_coordinate_weight_sha256"]
            == expected["nonpatch_vertex_coordinate_weight_sha256"]
        ),
        "nonpatch_face_coordinate_material_uv_sha256": (
            evidence["nonpatch_after"]["face_coordinate_material_uv_sha256"]
            == expected["nonpatch_face_coordinate_material_uv_sha256"]
        ),
        "nonpatch_exactly_preserved": evidence.get("nonpatch_exactly_preserved") is True,
        "rig_exactly_preserved": evidence.get("rig_exactly_preserved") is True,
        "protected_nonbody_objects_exactly_preserved": (
            evidence.get("protected_nonbody_objects_exactly_preserved") is True
        ),
        "nails_not_repaired_by_r21": (
            evidence["visual_truth"].get("nails_repaired_in_this_attempt") is False
        ),
    }
    if not all(checks.values()):
        raise KiraNailAttempt03Error(
            f"R21 protected evidence truth drifted: {checks}"
        )
    return checks


def load_reuse_components(
    config: Mapping[str, Any], current_manifest_sha256: str
) -> dict[str, dict[str, Any]]:
    binding = config.get("reuse_components_from")
    if binding is None:
        return {}
    row = dict(binding)
    path = project_path(str(row["path"]))
    if sha256_file(path) != str(row["sha256"]):
        raise KiraNailAttempt03Error("append-only passing-component cache changed")
    cache = validate_component_cache(
        json_file(path),
        source_blend_sha256=str(row["origin_source_blend_sha256"]),
        source_non_nail_manifest_sha256=str(
            row["origin_source_non_nail_manifest_sha256"]
        ),
        rig_rest_sha256=str(row["origin_rig_rest_sha256"]),
        run_config_sha256=str(row["origin_run_config_sha256"]),
    )
    if str(row["origin_source_blend_sha256"]) != str(config["source"]["sha256"]):
        raise KiraNailAttempt03Error("reuse cache belongs to a different source Blend")
    if str(row["origin_source_non_nail_manifest_sha256"]) != current_manifest_sha256:
        raise KiraNailAttempt03Error("reuse cache belongs to changed non-nail content")
    return {str(component["nail_id"]): component for component in cache["components"]}


def make_materials() -> tuple[Any, Any]:
    bed = legacy.natural_material(
        "Kira_R21_Attempt03_Natural_Nail_Bed",
        (0.72, 0.40, 0.39, 0.78),
        free_edge=False,
    )
    edge = legacy.natural_material(
        "Kira_R21_Attempt03_Subtle_Free_Edge",
        (0.93, 0.78, 0.75, 0.70),
        free_edge=True,
    )
    return bed, edge


def remove_source_nails(source_objects: list[Any]) -> None:
    for obj in source_objects:
        nails._remove_object_and_mesh(obj)  # noqa: SLF001


def reusable_component_row(
    *,
    definition: Mapping[str, Any],
    result: Mapping[str, Any],
    source_sha256: str,
    non_nail_manifest_sha256: str,
    rig_rest_sha256: str,
    config_sha256: str,
) -> dict[str, Any]:
    row = {
        "nail_id": str(definition["nail_id"]),
        "kind": str(definition["kind"]),
        "side": str(definition["side"]),
        "digit": int(definition["digit"]),
        "bone": str(definition["bone"]),
        "family": str(definition["family"]),
        "source_blend_sha256": source_sha256,
        "source_non_nail_manifest_sha256": non_nail_manifest_sha256,
        "rig_rest_sha256": rig_rest_sha256,
        "run_config_sha256": config_sha256,
        "projection_method": METHOD_ID,
        "top_surface_vertices_world_m": result["top_surface_vertices_world_m"],
        "top_surface_normals_world": result["top_surface_normals_world"],
        "base_clearances_m": result["base_clearances_m"],
        "accepted_result_sha256": canonical_json_sha256(jsonable(result)),
        "all_strict_gates_passed": True,
        "candidate_blend_saved_by_this_component_record": False,
    }
    row["component_payload_sha256"] = component_payload_sha256(row)
    return row


def set_component_properties(obj: Any, definition: Mapping[str, Any]) -> None:
    obj["nail_component"] = True
    obj["nail_kind"] = str(definition["kind"])
    obj["nail_side"] = str(definition["side"])
    obj["nail_digit"] = int(definition["digit"])
    obj["nail_id"] = str(definition["nail_id"])
    obj["declared_terminal_bone"] = str(definition["bone"])
    obj["projection_method"] = METHOD_ID
    obj["private_owner_review_only"] = True
    obj["inactive_candidate"] = True
    obj["runtime_activation_allowed"] = False
    obj["automatic_bone_remap_performed"] = False


def render_close_reviews(
    owner_dir: Path,
    built: list[Any],
    definitions: Mapping[str, Mapping[str, Any]],
) -> dict[str, str]:
    """Render four bilateral close groups only after all authoring gates pass."""

    scene = bpy.context.scene
    old = {
        "camera": scene.camera,
        "engine": scene.render.engine,
        "resolution_x": scene.render.resolution_x,
        "resolution_y": scene.render.resolution_y,
        "resolution_percentage": scene.render.resolution_percentage,
        "filepath": scene.render.filepath,
        "format": scene.render.image_settings.file_format,
    }
    camera_data = bpy.data.cameras.new("KIRA_NAIL_ATTEMPT03_CAMERA_TMP")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("KIRA_NAIL_ATTEMPT03_CAMERA_TMP", camera_data)
    scene.collection.objects.link(camera)
    lights = legacy.add_lights(scene)
    scene.camera = camera
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 800
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    outputs: dict[str, str] = {}
    try:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for kind, label in (("fingernail", "hand"), ("toenail", "foot")):
            for side, side_label in (("L", "left"), ("R", "right")):
                selected = [
                    obj
                    for obj in built
                    if obj.get("nail_kind") == kind and obj.get("nail_side") == side
                ]
                points = []
                normal = Vector((0.0, 0.0, 0.0))
                for obj in selected:
                    evaluated = obj.evaluated_get(depsgraph)
                    mesh = evaluated.to_mesh()
                    try:
                        points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
                    finally:
                        evaluated.to_mesh_clear()
                    definition = definitions[str(obj["nail_id"])]
                    normal += definition["reference_outward_world"]
                if len(selected) != 5 or not points or normal.length <= 1.0e-8:
                    raise KiraNailAttempt03Error("close-review nail group is incomplete")
                normal.normalize()
                low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
                high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
                target = (low + high) * 0.5
                span = max(float(value) for value in (high - low))
                for view_name, direction in (
                    ("dorsal", normal),
                    ("oblique", (normal + Vector((0.18 if side == "L" else -0.18, -0.06, 0.16))).normalized()),
                ):
                    camera.location = target + direction * 0.52
                    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
                    camera.data.ortho_scale = max(0.145, span * 1.60)
                    path = owner_dir / f"{side_label}_{label}_{view_name}_all_five_close.png"
                    scene.render.filepath = str(path)
                    bpy.ops.render.render(write_still=True)
                    outputs[f"{side_label}_{label}_{view_name}"] = path.name
    finally:
        for obj in [camera, *lights]:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data and data.users == 0:
                if isinstance(data, bpy.types.Camera):
                    bpy.data.cameras.remove(data)
                elif isinstance(data, bpy.types.Light):
                    bpy.data.lights.remove(data)
        scene.camera = old["camera"]
        scene.render.engine = old["engine"]
        scene.render.resolution_x = old["resolution_x"]
        scene.render.resolution_y = old["resolution_y"]
        scene.render.resolution_percentage = old["resolution_percentage"]
        scene.render.filepath = old["filepath"]
        scene.render.image_settings.file_format = old["format"]
    return outputs


def write_owner_package(
    *,
    owner_dir: Path,
    output_blend: Path,
    evidence: Mapping[str, Any],
    render_paths: Mapping[str, str],
) -> None:
    evidence_path = owner_dir / "BUILD_EVIDENCE.json"
    readme_path = owner_dir / "OWNER_REVIEW_README.md"
    manifest_path = owner_dir / "FILE_MANIFEST.json"
    evidence_path.write_text(json.dumps(jsonable(evidence), indent=2) + "\n", encoding="utf-8")
    readme_path.write_text(
        "# Kira R21 nail Attempt 03 — private inactive review\n\n"
        "This append-only candidate exists only because all twenty Kira nails passed the "
        "strict connected-region, binding, evaluated-shell, clearance, and protected-content gates. "
        "It does not approve the inherited R21 pelvis or activate/assign/export Kira.\n\n"
        "Review the bilateral dorsal and oblique hand/foot close images. The source R21 Blend and "
        "Attempts 01 and 02 remain unchanged.\n",
        encoding="utf-8",
    )
    rows = []
    for path in sorted(owner_dir.iterdir(), key=lambda item: item.name):
        if not path.is_file() or path == manifest_path:
            continue
        rows.append({"file": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest_path.write_text(
        json.dumps(
            {
                "schema": "kira.r21.nail_attempt03.owner_manifest.v1",
                "blend": output_blend.name,
                "render_count": len(render_paths),
                "files": rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    config_path = project_path(args.config)
    config_sha256 = sha256_file(config_path)
    config, fixed_inputs = verify_config(config_path)
    verify_r21_evidence_truth(config)
    source = project_path(str(config["source"]["path"]))
    if sha256_file(source) != str(config["source"]["sha256"]):
        raise KiraNailAttempt03Error("R21 source Blend hash changed")
    run_dir = project_path(str(config["outputs"]["run_evidence_dir"]))
    owner_dir = project_path(str(config["outputs"]["owner_review_dir"]))
    output_blend = project_path(str(config["outputs"]["candidate_blend"]))
    if run_dir.exists() or owner_dir.exists() or output_blend.exists():
        raise KiraNailAttempt03Error("append-only Attempt03 output already exists")
    run_dir.mkdir(parents=True, exist_ok=False)

    source_hash_before_open = sha256_file(source)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    if sha256_file(source) != source_hash_before_open:
        raise KiraNailAttempt03Error("source Blend changed while opening")
    body = bpy.data.objects.get(BODY_NAME)
    armature = bpy.data.objects.get(RIG_NAME)
    if body is None or body.type != "MESH":
        raise KiraNailAttempt03Error("exact R21 body object missing")
    if armature is None or armature.type != "ARMATURE":
        raise KiraNailAttempt03Error("exact R21 rig object missing")
    non_nail_before = legacy.non_nail_manifest()
    non_nail_manifest_sha256 = canonical_json_sha256(jsonable(non_nail_before))
    rig_rest_sha256 = nails._rig_signature(armature)  # noqa: SLF001
    expected_rig_rest = str(
        config["protected_r21_truth"]["expected_rig_rest_sha256"]
    )
    if rig_rest_sha256 != expected_rig_rest:
        raise KiraNailAttempt03Error(
            "exact R21 rig rest signature changed before nail authoring"
        )
    body_mesh_sha256 = nails._mesh_signature(body)  # noqa: SLF001
    body_modifier_count = len(body.modifiers)
    scene_before = legacy.scene_state_record()

    inventory = expected_nail_inventory()
    sources = []
    definitions: dict[str, dict[str, Any]] = {}
    anchors = dict(config["corrected_reference_anchors_world_m"])
    for base_definition in inventory:
        source_obj = bpy.data.objects.get(str(base_definition["source_object"]))
        if source_obj is None:
            raise KiraNailAttempt03Error(
                f"exact source landmark missing: {base_definition['source_object']}"
            )
        sources.append(source_obj)
        definitions[str(base_definition["nail_id"])] = projector.corrected_reference_definition(
            source_nail=source_obj,
            body=body,
            armature=armature,
            definition=base_definition,
            expected_anchor_world_m=anchors[str(base_definition["nail_id"])],
        )
    if len({obj.name for obj in sources}) != 20:
        raise KiraNailAttempt03Error("source landmark inventory is not 20 unique objects")
    reused = load_reuse_components(config, non_nail_manifest_sha256)
    remove_source_nails(sources)
    bed_material, edge_material = make_materials()
    built = []
    results = []
    failures = []
    reusable_rows = []
    for base_definition in inventory:
        nail_id = str(base_definition["nail_id"])
        definition = definitions[nail_id]
        name = f"Kira_R21_Attempt03_{nail_id}"
        try:
            if nail_id in reused:
                obj, result = projector.reconstruct_cached_nail_v1(
                    body=body,
                    armature=armature,
                    definition=definition,
                    cached_component=reused[nail_id],
                    name=name,
                    bed_material=bed_material,
                    free_edge_material=edge_material,
                )
                result = {
                    **result,
                    "top_surface_vertices_world_m": reused[nail_id]["top_surface_vertices_world_m"],
                    "top_surface_normals_world": reused[nail_id]["top_surface_normals_world"],
                    "base_clearances_m": reused[nail_id]["base_clearances_m"],
                }
            else:
                obj, result = projector.build_weight_constrained_nail_v1(
                    body=body,
                    armature=armature,
                    definition=definition,
                    name=name,
                    bed_material=bed_material,
                    free_edge_material=edge_material,
                )
            set_component_properties(obj, definition)
            built.append(obj)
            result = jsonable(result)
            results.append(result)
            reusable_rows.append(
                reusable_component_row(
                    definition=definition,
                    result=result,
                    source_sha256=source_hash_before_open,
                    non_nail_manifest_sha256=non_nail_manifest_sha256,
                    rig_rest_sha256=rig_rest_sha256,
                    config_sha256=config_sha256,
                )
            )
        except Exception as exc:
            failures.append(
                {
                    "nail_id": nail_id,
                    "bone": str(definition["bone"]),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )

    cache = {
        "schema": CACHE_SCHEMA,
        "attempt": 3,
        "created_utc": utc_now(),
        "source_blend_sha256": source_hash_before_open,
        "source_non_nail_manifest_sha256": non_nail_manifest_sha256,
        "rig_rest_sha256": rig_rest_sha256,
        "run_config_sha256": config_sha256,
        "component_count": len(reusable_rows),
        "components": reusable_rows,
        "candidate_blend_saved": False,
        "purpose": "exact passing top surfaces for one later bounded component-only repair",
    }
    cache_path = run_dir / "PASSING_NAIL_COMPONENTS.json"
    cache_path.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")

    non_nail_after = legacy.non_nail_manifest()
    full_gates = {
        "all_20_unique_nails": len(built) == 20 and len({obj["nail_id"] for obj in built}) == 20,
        "no_per_nail_failures": not failures,
        "every_result_strict_pass": len(results) == 20 and all(row.get("all_strict_gates_passed") is True for row in results),
        "body_mesh_unchanged": nails._mesh_signature(body) == body_mesh_sha256,  # noqa: SLF001
        "body_modifier_stack_unchanged": len(body.modifiers) == body_modifier_count,
        "rig_rest_unchanged": nails._rig_signature(armature) == rig_rest_sha256,  # noqa: SLF001
        "all_non_nail_objects_unchanged": non_nail_after == non_nail_before,
        "source_blend_unchanged": sha256_file(source) == source_hash_before_open,
        "no_automatic_bone_remap": all(row.get("automatic_bone_remap_performed") is False for row in results),
    }
    pair_audit = legacy.nail_pair_audit(built) if len(built) == 20 else None
    full_gates["no_nail_to_nail_overlap"] = bool(
        pair_audit and pair_audit["no_nail_to_nail_broad_phase_overlap"] is True
    )
    evidence = {
        "schema": EVIDENCE_SCHEMA,
        "status": "ALL_STRICT_GATES_PASSED_PRIVATE_INACTIVE" if all(full_gates.values()) else "FAILED_NO_CANDIDATE_BLEND_SAVED",
        "attempt": 3,
        "created_utc": utc_now(),
        "config": config_path.relative_to(ROOT).as_posix(),
        "config_sha256": config_sha256,
        "fixed_inputs": fixed_inputs,
        "source_blend": source.relative_to(ROOT).as_posix(),
        "source_blend_sha256": source_hash_before_open,
        "body_object": BODY_NAME,
        "rig_object": RIG_NAME,
        "body_mesh_sha256_before": body_mesh_sha256,
        "rig_rest_sha256_before": rig_rest_sha256,
        "source_reference_rule": "body.matrix_world_at_source_open @ source_nail.data.vertex.co",
        "source_nail_matrix_world_used_for_placement": False,
        "definitions": jsonable(definitions),
        "results": results,
        "failures": failures,
        "passing_component_cache": cache_path.relative_to(ROOT).as_posix(),
        "passing_component_cache_sha256": sha256_file(cache_path),
        "nail_pair_audit": pair_audit,
        "full_gates": full_gates,
        "scene_before": scene_before,
        "private": True,
        "inactive": True,
        "unassigned": True,
        "unpublished": True,
        "runtime_activation_allowed": False,
        "inherited_r21_pelvis_approved_by_this_work": False,
        "candidate_blend_saved": False,
    }
    if not all(full_gates.values()):
        for obj in list(built):
            if obj.name in bpy.data.objects:
                nails._remove_object_and_mesh(obj)  # noqa: SLF001
        failure_path = run_dir / "FAILURE_EVIDENCE.json"
        failure_path.write_text(json.dumps(jsonable({**evidence, "schema": FAILURE_SCHEMA}), indent=2) + "\n", encoding="utf-8")
        raise KiraNailAttempt03Error(
            "Attempt03 failed closed; no candidate Blend saved; see FAILURE_EVIDENCE.json"
        )

    owner_dir.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))
    evidence["candidate_blend_saved"] = True
    evidence["candidate_blend"] = output_blend.relative_to(ROOT).as_posix()
    evidence["candidate_blend_sha256"] = sha256_file(output_blend)
    render_paths = render_close_reviews(owner_dir, built, definitions)
    evidence["renders"] = render_paths
    write_owner_package(
        owner_dir=owner_dir,
        output_blend=output_blend,
        evidence=evidence,
        render_paths=render_paths,
    )
    run_evidence_path = run_dir / "BUILD_EVIDENCE.json"
    run_evidence_path.write_text(json.dumps(jsonable(evidence), indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": evidence["status"], "blend": evidence["candidate_blend"], "renders": render_paths}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema": FAILURE_SCHEMA,
                    "status": "ATTEMPT03_FAILED_CLOSED",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                    "candidate_blend_save_authorized_on_failure": False,
                },
                indent=2,
            )
        )
        raise
