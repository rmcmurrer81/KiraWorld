#!/usr/bin/env python3
"""Build one new bald, inactive MakeHuman rigged carrier.

This worker only runs inside background Blender with factory startup and
automatic script execution disabled.  It requires a separately supplied exact
one-run authorization, refuses every existing output, never saves over the
qualified source, and does not add hair, clothes, internal anatomy, identity
styling, actions, runtime selection, or public export data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
import tempfile
from typing import Any, Mapping

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_makehuman_rigged_carrier import (  # noqa: E402
    REQUIRED_BLENDER_FLAGS,
    RiggedCarrierError,
    canonical_sha256,
    load_transformed_makehuman_vertices,
    native_filesystem_path,
    prepare_preflight,
    promote_file_no_replace,
    project_path,
    read_json,
    resolve_makehuman_skeleton_geometry,
    same_filesystem_path,
    sha256_file,
    validate_one_run_authorization,
)


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--authorization", required=True)
    return parser.parse_args(values)


def _project_argument(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def require_safe_blender_invocation() -> Path:
    if not bpy.app.background:
        raise RiggedCarrierError("carrier build requires Blender background mode")
    separator = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    blender_arguments = sys.argv[:separator]
    for flag in REQUIRED_BLENDER_FLAGS:
        if blender_arguments.count(flag) != 1:
            raise RiggedCarrierError(f"carrier build requires Blender flag {flag}")
    autoexec = getattr(bpy.context.preferences.filepaths, "use_scripts_auto_execute", None)
    if autoexec is not False:
        raise RiggedCarrierError("automatic script execution must be disabled")
    executable = Path(sys.executable).resolve(strict=True)
    if executable.name.lower() not in {"blender", "blender.exe"}:
        raise RiggedCarrierError("worker executable is not Blender")
    return executable


def _mesh_geometry_digest(body: bpy.types.Object) -> str:
    mesh = body.data
    digest = hashlib.sha256()
    digest.update(struct.pack("<QQ", len(mesh.vertices), len(mesh.polygons)))
    for vertex in mesh.vertices:
        digest.update(struct.pack("<I3d", int(vertex.index), *(float(v) for v in vertex.co)))
    for polygon in mesh.polygons:
        indices = tuple(int(value) for value in polygon.vertices)
        digest.update(struct.pack("<II", int(polygon.index), len(indices)))
        digest.update(struct.pack(f"<{len(indices)}I", *indices))
    return digest.hexdigest()


def _weight_digest(body: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    groups = list(body.vertex_groups)
    digest.update(struct.pack("<I", len(groups)))
    for group in groups:
        encoded = group.name.encode("utf-8")
        digest.update(struct.pack("<II", int(group.index), len(encoded)))
        digest.update(encoded)
    assignment_count = 0
    for vertex in body.data.vertices:
        assignments = sorted(
            (int(item.group), float(item.weight))
            for item in vertex.groups
            if float(item.weight) > 0.0
        )
        digest.update(struct.pack("<II", int(vertex.index), len(assignments)))
        for group_index, weight in assignments:
            digest.update(struct.pack("<Id", group_index, weight))
            assignment_count += 1
    digest.update(struct.pack("<Q", assignment_count))
    return digest.hexdigest()


def _matrix_values(matrix: Any) -> list[float]:
    values = [float(matrix[row][column]) for row in range(4) for column in range(4)]
    if not all(math.isfinite(value) for value in values):
        raise RiggedCarrierError("matrix contains non-finite value")
    return values


def _armature_digest(armature: bpy.types.Object) -> str:
    records = []
    for bone in armature.data.bones:
        records.append(
            {
                "name": bone.name,
                "parent": bone.parent.name if bone.parent else None,
                "use_deform": bool(bone.use_deform),
                "matrix_local": _matrix_values(bone.matrix_local),
            }
        )
    return canonical_sha256(records)


def _source_body(config: Mapping[str, Any]) -> bpy.types.Object:
    source = config["source"]
    expected_name = str(source["primary_object_id"])
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    if len(bpy.data.objects) != 1 or len(meshes) != 1 or armatures:
        raise RiggedCarrierError("qualified source must contain exactly one mesh and no armature")
    body = meshes[0]
    if body.name != expected_name or body.get("primary_surface") is not True:
        raise RiggedCarrierError("qualified source primary object differs")
    if len(body.data.vertices) != int(source["expected_vertex_count"]):
        raise RiggedCarrierError("qualified source vertex count differs")
    if len(body.data.polygons) != int(source["expected_face_count"]):
        raise RiggedCarrierError("qualified source face count differs")
    if body.data.shape_keys is not None:
        raise RiggedCarrierError("qualified source unexpectedly contains shape keys")
    if body.data.uv_layers or body.data.materials or body.material_slots:
        raise RiggedCarrierError("qualified source unexpectedly contains appearance layers")
    if bpy.data.actions:
        raise RiggedCarrierError("qualified source unexpectedly contains actions")
    return body


def _create_armature(
    body: bpy.types.Object,
    config: Mapping[str, Any],
    skeleton_geometry: Mapping[str, Any],
    weight_group_names: set[str],
) -> bpy.types.Object:
    armature_name = str(config["candidate"]["armature_id"])
    data = bpy.data.armatures.new(f"{armature_name}__data")
    armature = bpy.data.objects.new(armature_name, data)
    bpy.context.scene.collection.objects.link(armature)
    armature.matrix_world.identity()
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    body.select_set(False)
    bpy.ops.object.mode_set(mode="EDIT")
    created: dict[str, Any] = {}
    try:
        for name in skeleton_geometry["bone_order"]:
            record = skeleton_geometry["bones"][name]
            bone = data.edit_bones.new(name)
            bone.head = Vector(record["head"])
            bone.tail = Vector(record["tail"])
            if (bone.tail - bone.head).length <= 1.0e-7:
                raise RiggedCarrierError(f"bone {name} is degenerate")
            parent_name = record["parent"]
            if parent_name is not None:
                if parent_name not in created:
                    raise RiggedCarrierError(f"bone {name} parent was not created")
                bone.parent = created[parent_name]
                bone.use_connect = False
            normal = Vector(record["roll_normal"])
            if normal.length <= 1.0e-10:
                raise RiggedCarrierError(f"bone {name} roll normal is degenerate")
            bone.align_roll(normal)
            bone.use_deform = name in weight_group_names
            created[name] = bone
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
    if len(data.bones) != int(config["skeleton"]["expected_bone_count"]):
        raise RiggedCarrierError("created armature bone count differs")
    modifier = body.modifiers.new("Inactive_Rigged_Carrier_Armature", "ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    modifier.use_bone_envelopes = False
    body.parent = armature
    body.matrix_parent_inverse = armature.matrix_world.inverted()
    return armature


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    try:
        with native_filesystem_path(path).open(
            "x", encoding="utf-8", newline="\n"
        ) as stream:
            stream.write(text)
    except FileExistsError as exc:
        raise RiggedCarrierError(f"refusing to overwrite report: {path}") from exc


def _path_exists(path: Path) -> bool:
    native = native_filesystem_path(path)
    return native.exists() or native.is_symlink()


def _save_and_promote_without_replace(
    candidate_path: Path,
    source_path: Path,
    source_sha_before: str,
) -> dict[str, Any]:
    """Save privately, then atomically create the final name without replacement."""

    parent = candidate_path.parent
    native_parent = native_filesystem_path(parent)
    if not native_parent.is_dir():
        raise RiggedCarrierError("authorized output directory does not exist")
    if _path_exists(candidate_path):
        raise RiggedCarrierError("candidate output appeared before private save")
    temporary_directory = Path(
        tempfile.mkdtemp(prefix=".carrier-build-", dir=str(native_parent))
    )
    staging_path = temporary_directory / "carrier.staging.blend"
    try:
        if _path_exists(staging_path):
            raise RiggedCarrierError("private staging path unexpectedly exists")
        bpy.ops.wm.save_as_mainfile(
            filepath=str(native_filesystem_path(staging_path)),
            check_existing=False,
        )
        if not same_filesystem_path(Path(bpy.data.filepath), staging_path):
            raise RiggedCarrierError("Blender did not save the exact private staging path")
        if sha256_file(source_path) != source_sha_before:
            raise RiggedCarrierError("qualified source changed during private save")
        receipt = promote_file_no_replace(staging_path, candidate_path)
        native_filesystem_path(temporary_directory).rmdir()
        final_path = project_path(
            PROJECT_ROOT,
            candidate_path.relative_to(PROJECT_ROOT).as_posix(),
            "promoted candidate",
            must_exist=True,
        )
        if sha256_file(final_path) != receipt["sha256"]:
            raise RiggedCarrierError("promoted candidate hash differs from private save")
        if native_filesystem_path(final_path).stat().st_size != receipt["bytes"]:
            raise RiggedCarrierError("promoted candidate byte count differs from private save")
        if sha256_file(source_path) != source_sha_before:
            raise RiggedCarrierError("qualified source changed during no-replace promotion")
        return receipt
    finally:
        if _path_exists(staging_path):
            try:
                os.unlink(native_filesystem_path(staging_path))
            except OSError:
                pass
        if native_filesystem_path(temporary_directory).is_dir():
            try:
                native_filesystem_path(temporary_directory).rmdir()
            except OSError:
                pass


def main() -> int:
    args = parse_args()
    blender_executable = require_safe_blender_invocation()
    config_path = _project_argument(args.config).resolve(strict=True)
    authorization_path = _project_argument(args.authorization).resolve(strict=True)
    preflight = prepare_preflight(
        PROJECT_ROOT,
        config_path,
        blender_executable=blender_executable,
        authorization_path=authorization_path,
        verify_decompressed_container=False,
    )
    if preflight["status"] != "PREFLIGHT_AUTHORIZED_EXACT_INACTIVE_RUN_READY":
        raise RiggedCarrierError("exact authorized preflight is not ready")
    authorization = validate_one_run_authorization(
        PROJECT_ROOT,
        config_path,
        authorization_path,
        blender_executable,
        operation="build",
    )
    config = read_json(config_path, "rigged-carrier config")
    source = config["source"]
    build_inputs = config["source_build_inputs"]
    skeleton_config = config["skeleton"]
    output = config["output"]

    source_path = project_path(PROJECT_ROOT, source["path"], "source", must_exist=True)
    candidate_path = project_path(
        PROJECT_ROOT, output["candidate_blend"], "candidate output", must_exist=False
    )
    build_report_path = project_path(
        PROJECT_ROOT, output["build_report"], "build report", must_exist=False
    )
    audit_report_path = project_path(
        PROJECT_ROOT, output["audit_report"], "audit report", must_exist=False
    )
    if _path_exists(candidate_path) or _path_exists(build_report_path) or _path_exists(audit_report_path):
        raise RiggedCarrierError("append-only carrier output is no longer empty")
    if not native_filesystem_path(candidate_path.parent).is_dir():
        raise RiggedCarrierError("authorized output directory does not exist")
    source_sha_before = sha256_file(source_path)
    if source_sha_before != source["sha256"]:
        raise RiggedCarrierError("qualified source hash changed before Blender open")

    base_path = project_path(
        PROJECT_ROOT, build_inputs["base_obj"]["path"], "base OBJ", must_exist=True
    )
    targets = [
        (
            project_path(
                PROJECT_ROOT,
                record["path"],
                f"macro target {index}",
                must_exist=True,
            ),
            float(record["weight"]),
        )
        for index, record in enumerate(build_inputs["female_macro_targets"])
    ]
    skeleton_path = project_path(
        PROJECT_ROOT,
        skeleton_config["definition"]["path"],
        "skeleton definition",
        must_exist=True,
    )
    weights_path = project_path(
        PROJECT_ROOT,
        skeleton_config["weights"]["path"],
        "skeleton weights",
        must_exist=True,
    )
    skeleton_payload = read_json(skeleton_path, "MakeHuman skeleton")
    weights_payload = read_json(weights_path, "MakeHuman weights")
    expected_weight_names = set(weights_payload["weights"])
    transformed, transform = load_transformed_makehuman_vertices(
        base_path,
        targets,
        float(build_inputs["target_height_m"]),
    )
    skeleton_geometry = resolve_makehuman_skeleton_geometry(skeleton_payload, transformed)

    bpy.ops.wm.open_mainfile(
        filepath=str(native_filesystem_path(source_path)),
        load_ui=False,
        use_scripts=False,
    )
    if not same_filesystem_path(Path(bpy.data.filepath), source_path):
        raise RiggedCarrierError("Blender did not open the exact qualified source")
    body = _source_body(config)
    source_geometry_digest = _mesh_geometry_digest(body)
    source_weight_digest = _weight_digest(body)
    source_group_names = [group.name for group in body.vertex_groups]
    missing_weight_groups = sorted(expected_weight_names - set(source_group_names))
    if missing_weight_groups:
        raise RiggedCarrierError(
            f"qualified source lacks MakeHuman weight groups: {missing_weight_groups!r}"
        )
    source_object_matrix = _matrix_values(body.matrix_world)

    armature = _create_armature(body, config, skeleton_geometry, expected_weight_names)
    if _mesh_geometry_digest(body) != source_geometry_digest:
        raise RiggedCarrierError("armature attachment changed source geometry")
    if _weight_digest(body) != source_weight_digest:
        raise RiggedCarrierError("armature attachment changed source weights")
    if [group.name for group in body.vertex_groups] != source_group_names:
        raise RiggedCarrierError("armature attachment changed source vertex groups")
    if _matrix_values(body.matrix_world) != source_object_matrix:
        raise RiggedCarrierError("armature attachment changed body transform")

    candidate = config["candidate"]
    body["inactive_rigged_carrier_candidate"] = True
    body["carrier_candidate_id"] = candidate["candidate_id"]
    body["source_foundation_id"] = candidate["foundation_id"]
    body["source_foundation_sha256"] = source_sha_before
    body["generic_identity_neutral"] = True
    body["bald"] = True
    body["contains_hair"] = False
    body["contains_clothing"] = False
    body["contains_internal_anatomy"] = False
    body["runtime_activation_allowed"] = False
    body["public_export_allowed"] = False
    armature["inactive_rigged_carrier_candidate"] = True
    armature["carrier_candidate_id"] = candidate["candidate_id"]
    armature["source_foundation_sha256"] = source_sha_before
    armature["runtime_activation_allowed"] = False
    armature["public_export_allowed"] = False
    bpy.context.scene["inactive_rigged_carrier_candidate"] = True
    bpy.context.scene["runtime_activation_allowed"] = False
    bpy.context.scene["public_export_allowed"] = False
    bpy.context.scene["contains_hair"] = False
    bpy.context.scene["contains_clothing"] = False
    bpy.context.scene["contains_internal_anatomy"] = False

    if bpy.data.actions:
        raise RiggedCarrierError("carrier build created or retained actions")
    if len(bpy.data.objects) != 2:
        raise RiggedCarrierError("carrier build must contain only body and armature")
    if any(obj.type not in {"MESH", "ARMATURE"} for obj in bpy.data.objects):
        raise RiggedCarrierError("carrier build contains an unexpected object type")

    candidate_receipt = _save_and_promote_without_replace(
        candidate_path,
        source_path,
        source_sha_before,
    )
    source_sha_after = sha256_file(source_path)
    if source_sha_after != source_sha_before:
        raise RiggedCarrierError("qualified source changed during carrier build")

    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_type": "makehuman_adult_female_rigged_carrier_build_report",
        "status": "BUILT_PRIVATE_INACTIVE_PENDING_INDEPENDENT_POSE_AUDIT_AND_OWNER_REVIEW",
        "candidate_id": candidate["candidate_id"],
        "config_sha256": sha256_file(config_path),
        "authorization": {
            "path": authorization_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256_file(authorization_path),
            "one_run_id": authorization["one_run_id"],
            "preflight_receipt_sha256": authorization["preflight_receipt_sha256"],
            "controller_sha256": authorization["controller_sha256"],
            "builder_sha256": authorization["builder_sha256"],
            "auditor_sha256": authorization["auditor_sha256"],
            "intersection_auditor_sha256": authorization[
                "intersection_auditor_sha256"
            ],
        },
        "source": {
            "path": source["path"],
            "bytes": native_filesystem_path(source_path).stat().st_size,
            "sha256_before": source_sha_before,
            "sha256_after": source_sha_after,
            "unchanged": source_sha_before == source_sha_after,
        },
        "candidate": {
            "path": output["candidate_blend"],
            "bytes": candidate_receipt["bytes"],
            "sha256": candidate_receipt["sha256"],
            "creation_transaction": candidate_receipt["promotion"],
        },
        "body": {
            "object_id": body.name,
            "vertex_count": len(body.data.vertices),
            "face_count": len(body.data.polygons),
            "geometry_sha256_before": source_geometry_digest,
            "geometry_sha256_after": _mesh_geometry_digest(body),
            "weight_sha256_before": source_weight_digest,
            "weight_sha256_after": _weight_digest(body),
            "vertex_group_names": source_group_names,
            "object_matrix": source_object_matrix,
        },
        "armature": {
            "object_id": armature.name,
            "bone_count": len(armature.data.bones),
            "deforming_bone_count": sum(bool(bone.use_deform) for bone in armature.data.bones),
            "rest_sha256": _armature_digest(armature),
            "object_matrix": _matrix_values(armature.matrix_world),
            "definition_sha256": sha256_file(skeleton_path),
            "weights_source_sha256": sha256_file(weights_path),
            "resolved_geometry_sha256": canonical_sha256(skeleton_geometry["bones"]),
            "transform": transform,
        },
        "recorded_actions": {
            "source_overwritten": False,
            "hair_added": False,
            "clothing_added": False,
            "internal_anatomy_added": False,
            "identity_styling_added": False,
            "actions_added": False,
            "render_performed": False,
            "glb_export_performed": False,
            "runtime_activation_performed": False,
            "public_export_performed": False,
        },
        "authority": {
            "owner_approved": False,
            "anatomy_authoring_authorized": False,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        },
        "blender": {
            "version": list(bpy.app.version),
            "background": bool(bpy.app.background),
            "factory_startup_flag_present_before_separator": (
                "--factory-startup" in sys.argv[: sys.argv.index("--")]
            ),
            "autoexec_disabled_flag_present_before_separator": (
                "--disable-autoexec" in sys.argv[: sys.argv.index("--")]
            ),
            "executable_sha256": sha256_file(blender_executable),
            "compressed_source_decompression_deferred_to_safe_blender_open": True,
        },
    }
    report["build_receipt_sha256"] = canonical_sha256(report)
    _write_new_json(build_report_path, report)
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "BUILD_REJECTED",
                    "error": str(exc),
                    "runtime_activation_performed": False,
                    "public_export_performed": False,
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)
