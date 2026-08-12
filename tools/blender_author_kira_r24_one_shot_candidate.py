#!/usr/bin/env python3
"""Inert Blender-side worker for one bounded Kira R24 author transaction.

This module deliberately carries no current execution authority.  After a
separate post-R4/R5 author-operation module is independently sealed, a later static
reseal may replace the ``None`` dependency fields and the authority state.
Until then even a direct invocation with ``--execute-authoring`` fails before
Blender opens a Blend or mutates data.

When eventually sealed, the worker opens the exact R19 Attempt 06 source with
``load_ui=False``, calls exactly one hash-bound external-surface author
operation, rejects out-of-scope drift, restores an explicit neutral pose,
marks the candidate private/inactive/unassigned/unpublished/not-runtime-
eligible, and performs one candidate save.  It never renders, exports,
activates, assigns, publishes, or writes the preserved source.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import sys
import time
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RELATIVE = PurePosixPath(
    "RecoverySprint/continuation_20260802/"
    "kira_r19_bald_targeted_correction/attempt_06/"
    "kira_r19_bald_targeted_material_movement_correction.blend"
)
SOURCE_BYTES = 90_861_425
SOURCE_SHA256 = "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f"
RUNTIME_ROOT_RELATIVE = PurePosixPath(
    "RecoverySprint/continuation_20260808/"
    "kira_r24_one_shot_runtime_attempts"
)
CANDIDATE_BASENAME = "kira_r24_one_shot_private_candidate.blend"
BODY_OBJECT_NAME = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"
PATCH_OBJECT_NAME = "Kira_R24_Intrinsic_EStar_Repaired_Patch"
RIG_OBJECT_NAME = "Kira_R19_BlackProject_Native_188_Rig"

# These are intentionally symbolic.  A later independent reseal must fill the
# byte count and digest from a future accepted post-R4/R5 audit and the
# separate author operation.  This file must not infer authoring from the
# rejected R4 evaluator.
ACCEPTED_GATE_CONTRACT_BINDING: dict[str, object] = {
    "path": (
        "RecoverySprint/continuation_20260808/"
        "kira_r24_artifact_derived_gate_r5/"
        "KIRA_R24_ARTIFACT_DERIVED_GATE_R5_CONTRACT.json"
    ),
    "bytes": None,
    "sha256": None,
}
AUTHOR_OPERATION_BINDING: dict[str, object] = {
    "path": "tools/blender_author_kira_r24_r5_external_surface_operation.py",
    "bytes": None,
    "sha256": None,
}
EXECUTION_AUTHORITY_STATE = (
    "NOT_GRANTED_R4_REJECTED_R5_GATE_AND_AUTHOR_OPERATION_RESEAL_REQUIRED"
)
REQUIRED_EXECUTION_AUTHORITY_STATE = "GRANTED_FOR_ONE_APPEND_ONLY_TRANSACTION"


class R24OneShotAuthorError(RuntimeError):
    """Fail-closed author-worker error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _project_path(raw: object, *, require_file: bool = False) -> Path:
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute():
        raise R24OneShotAuthorError("project path must be nonempty and relative")
    pure = PurePosixPath(raw.replace("\\", "/"))
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise R24OneShotAuthorError("unsafe project path component")
    path = ROOT.joinpath(*pure.parts)
    try:
        path.resolve(strict=require_file).relative_to(ROOT.resolve())
    except (OSError, ValueError) as exc:
        raise R24OneShotAuthorError("project path escaped the repository") from exc
    if require_file and (not path.is_file() or path.is_symlink()):
        raise R24OneShotAuthorError(f"exact regular file is absent: {raw}")
    return path


def _verify_binding(binding: Mapping[str, object], label: str) -> Path:
    if set(binding) != {"path", "bytes", "sha256"}:
        raise R24OneShotAuthorError(f"{label} binding fields are not exact")
    if not isinstance(binding.get("bytes"), int) or isinstance(binding.get("bytes"), bool):
        raise R24OneShotAuthorError(f"{label} byte binding is not sealed")
    digest = binding.get("sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise R24OneShotAuthorError(f"{label} digest binding is not sealed")
    path = _project_path(binding.get("path"), require_file=True)
    if path.stat().st_size != int(binding["bytes"]) or sha256_file(path) != digest:
        raise R24OneShotAuthorError(f"{label} binding changed")
    return path


def _verify_execution_authority() -> None:
    if EXECUTION_AUTHORITY_STATE != REQUIRED_EXECUTION_AUTHORITY_STATE:
        raise R24OneShotAuthorError(
            "R24 one-shot authoring is inert; execution authority is not granted"
        )


def _verify_source(path: Path) -> None:
    expected = _project_path(SOURCE_RELATIVE.as_posix(), require_file=True)
    if path.resolve() != expected.resolve():
        raise R24OneShotAuthorError("worker source is not exact R19 Attempt 06")
    if path.stat().st_size != SOURCE_BYTES or sha256_file(path) != SOURCE_SHA256:
        raise R24OneShotAuthorError("exact R19 Attempt 06 source identity changed")


def _verify_output(path: Path) -> None:
    runtime = _project_path(RUNTIME_ROOT_RELATIVE.as_posix())
    try:
        relative = path.resolve(strict=False).relative_to(runtime.resolve(strict=False))
    except ValueError as exc:
        raise R24OneShotAuthorError("candidate output escaped the R24 runtime root") from exc
    if len(relative.parts) != 2 or not re.fullmatch(r"attempt_[0-9]{2}", relative.parts[0]):
        raise R24OneShotAuthorError("candidate output does not use one append-only attempt root")
    if relative.parts[1] != CANDIDATE_BASENAME:
        raise R24OneShotAuthorError("candidate basename changed")
    if not path.parent.is_dir() or path.exists():
        raise R24OneShotAuthorError("candidate output is not a fresh reserved path")


def _load_exact_module(path: Path) -> Any:
    name = "_kira_r24_r5_sealed_external_surface_author_operation"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise R24OneShotAuthorError("sealed author operation cannot be imported")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    function = getattr(module, "author_external_surface_r5", None)
    if not callable(function):
        raise R24OneShotAuthorError("sealed author operation callable is absent")
    return module


def _float_rows(value: Any) -> list[list[float]]:
    return [[float(item) for item in row] for row in value]


def _action_fingerprint(action: Any) -> dict[str, object]:
    curves: list[dict[str, object]] = []
    for curve in sorted(
        getattr(action, "fcurves", ()),
        key=lambda item: (str(item.data_path), int(item.array_index)),
    ):
        curves.append(
            {
                "path": str(curve.data_path),
                "index": int(curve.array_index),
                "keys": [
                    [float(point.co.x), float(point.co.y), str(point.interpolation)]
                    for point in curve.keyframe_points
                ],
            }
        )
    return {
        "name": str(action.name),
        "frame_range": [float(item) for item in action.frame_range],
        "curves": curves,
    }


def _material_fingerprint(material: Any) -> dict[str, object]:
    nodes: list[list[object]] = []
    links: list[list[str]] = []
    if bool(material.use_nodes) and material.node_tree is not None:
        nodes = sorted(
            [
                [
                    str(node.name),
                    str(node.bl_idname),
                    str(getattr(getattr(node, "image", None), "name", "")),
                ]
                for node in material.node_tree.nodes
            ]
        )
        links = sorted(
            [
                [
                    str(link.from_node.name),
                    str(link.from_socket.name),
                    str(link.to_node.name),
                    str(link.to_socket.name),
                ]
                for link in material.node_tree.links
            ]
        )
    return {"name": str(material.name), "use_nodes": bool(material.use_nodes), "nodes": nodes, "links": links}


def protected_scope_snapshot(bpy_module: Any) -> dict[str, object]:
    """Capture the author worker's fast out-of-scope non-regression ledger.

    A future accepted fresh-reopen R5 extractor remains the acceptance
    authority.  This
    author-side ledger is an additional early rejection, not a substitute for
    artifact-derived verification.
    """

    allowed_objects = {BODY_OBJECT_NAME, PATCH_OBJECT_NAME}
    allowed_meshes = {
        "Kira_R19_BlackProject_Radial_Patch_Primary_Surface_Mesh",
        "Kira_R24_Intrinsic_EStar_Repaired_Patch_Mesh",
    }
    objects = []
    for obj in sorted(bpy_module.data.objects, key=lambda item: str(item.name)):
        if str(obj.name) in allowed_objects:
            continue
        objects.append(
            {
                "name": str(obj.name),
                "type": str(obj.type),
                "data": str(obj.data.name) if obj.data is not None else None,
                "parent": str(obj.parent.name) if obj.parent else None,
                "matrix_world": _float_rows(obj.matrix_world),
                "collections": sorted(str(item.name) for item in obj.users_collection),
                "modifiers": sorted([str(item.name), str(item.type)] for item in obj.modifiers),
            }
        )
    armatures = []
    for armature in sorted(bpy_module.data.armatures, key=lambda item: str(item.name)):
        armatures.append(
            {
                "name": str(armature.name),
                "bones": [
                    {
                        "name": str(bone.name),
                        "parent": str(bone.parent.name) if bone.parent else None,
                        "head": [float(item) for item in bone.head_local],
                        "tail": [float(item) for item in bone.tail_local],
                        "matrix": _float_rows(bone.matrix_local),
                        "deform": bool(bone.use_deform),
                    }
                    for bone in sorted(armature.bones, key=lambda item: str(item.name))
                ],
            }
        )
    return {
        "objects": objects,
        "non_authorized_mesh_names": sorted(
            str(mesh.name) for mesh in bpy_module.data.meshes if str(mesh.name) not in allowed_meshes
        ),
        "armatures": armatures,
        "actions": [_action_fingerprint(item) for item in sorted(bpy_module.data.actions, key=lambda x: str(x.name))],
        "materials": [_material_fingerprint(item) for item in sorted(bpy_module.data.materials, key=lambda x: str(x.name))],
        "images": sorted(str(item.name) for item in bpy_module.data.images),
        "collections": sorted(str(item.name) for item in bpy_module.data.collections),
    }


def restore_neutral(bpy_module: Any) -> dict[str, object]:
    rig = bpy_module.data.objects.get(RIG_OBJECT_NAME)
    if rig is None or str(rig.type) != "ARMATURE":
        raise R24OneShotAuthorError("exact R19 rig is absent")
    animation = rig.animation_data_create()
    animation.action = None
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    for scene in bpy_module.data.scenes:
        scene.frame_set(int(scene.frame_start))
    bpy_module.context.view_layer.update()
    max_basis_error = 0.0
    for bone in rig.pose.bones:
        matrix = bone.matrix_basis
        for row in range(4):
            for column in range(4):
                expected = 1.0 if row == column else 0.0
                max_basis_error = max(max_basis_error, abs(float(matrix[row][column]) - expected))
    if getattr(animation, "action", None) is not None or not math.isfinite(max_basis_error) or max_basis_error > 1e-10:
        raise R24OneShotAuthorError("neutral pose restoration failed")
    return {
        "rig": RIG_OBJECT_NAME,
        "action_cleared": True,
        "pose_bone_count": len(rig.pose.bones),
        "maximum_matrix_basis_identity_error": max_basis_error,
        "scene_frames": {str(scene.name): int(scene.frame_current) for scene in bpy_module.data.scenes},
    }


def mark_private_candidate(bpy_module: Any) -> dict[str, bool]:
    flags = {
        "private": True,
        "inactive": True,
        "unassigned": True,
        "unpublished": True,
        "runtime_eligible": False,
        "owner_approved": False,
    }
    body = bpy_module.data.objects.get(BODY_OBJECT_NAME)
    if body is None or str(body.type) != "MESH":
        raise R24OneShotAuthorError("exact R19 body is absent")
    for target in [body, *list(bpy_module.data.scenes)]:
        for key, value in flags.items():
            target[f"kira_r24_candidate_{key}"] = value
    return flags


def validate_operation_result(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise R24OneShotAuthorError("author operation did not return an exact record")
    required = {
        "schema",
        "status",
        "authorized_mutated_objects",
        "save_performed",
        "render_performed",
        "export_performed",
        "activation_performed",
        "assignment_performed",
        "publication_performed",
    }
    if set(value) != required:
        raise R24OneShotAuthorError("author operation result fields drifted")
    if value["schema"] != "kira.avatar.r24.r5_external_surface_author_operation.v1":
        raise R24OneShotAuthorError("author operation schema drifted")
    if value["status"] != "AUTHORED_IN_MEMORY_POSTSAVE_EVALUATION_REQUIRED":
        raise R24OneShotAuthorError("author operation status drifted")
    if value["authorized_mutated_objects"] != [BODY_OBJECT_NAME, PATCH_OBJECT_NAME]:
        raise R24OneShotAuthorError("author operation mutation scope drifted")
    for key in (
        "save_performed",
        "render_performed",
        "export_performed",
        "activation_performed",
        "assignment_performed",
        "publication_performed",
    ):
        if value[key] is not False:
            raise R24OneShotAuthorError(f"forbidden author-operation claim: {key}")
    return value


def _save_once(bpy_module: Any, output: Path) -> None:
    if output.exists():
        raise R24OneShotAuthorError("candidate output appeared before the one save")
    result = bpy_module.ops.wm.save_as_mainfile(
        filepath=str(output),
        check_existing=False,
        relative_remap=False,
    )
    if result != {"FINISHED"} or not output.is_file():
        raise R24OneShotAuthorError("the one candidate save did not complete")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--controller-nonce", required=True)
    parser.add_argument("--job-gate", required=True)
    parser.add_argument("--execute-authoring", action="store_true")
    return parser.parse_args(argv)


def wait_for_parent_job_gate(args: argparse.Namespace, timeout_seconds: float = 30.0) -> dict[str, object]:
    gate = Path(args.job_gate).resolve()
    try:
        gate.relative_to(Path(args.output).resolve().parent)
    except ValueError as exc:
        raise R24OneShotAuthorError("job gate is outside the reserved attempt root") from exc
    deadline = time.monotonic() + timeout_seconds
    while not gate.is_file() and time.monotonic() < deadline:
        time.sleep(0.025)
    if not gate.is_file() or gate.is_symlink():
        raise R24OneShotAuthorError("parent job-assignment gate did not arrive")
    try:
        payload = json.loads(gate.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise R24OneShotAuthorError("parent job-assignment gate is invalid") from exc
    expected = {
        "schema": "kira.avatar.r24.author_parent_job_gate.v1",
        "nonce": args.controller_nonce,
        "parent_pid": os.getppid(),
        "child_pid": os.getpid(),
        "assigned": True,
        "kill_on_job_close": True,
    }
    if not isinstance(payload, dict) or any(payload.get(key) != value for key, value in expected.items()):
        raise R24OneShotAuthorError("parent job-assignment gate fields changed")
    return payload


def run_authoring(args: argparse.Namespace, *, bpy_module: Any | None = None) -> dict[str, object]:
    _verify_execution_authority()
    if not args.execute_authoring:
        raise R24OneShotAuthorError("explicit one-shot author flag is absent")
    if not re.fullmatch(r"[0-9a-f]{64}", str(args.controller_nonce)):
        raise R24OneShotAuthorError("controller nonce is malformed")
    if os.environ.get("KIRA_R24_ONE_SHOT_CONTROLLER_NONCE") != args.controller_nonce:
        raise R24OneShotAuthorError("controller nonce environment binding changed")
    wait_for_parent_job_gate(args)
    source = Path(args.source).resolve()
    output = Path(args.output).resolve()
    _verify_source(source)
    _verify_output(output)
    contract_path = _verify_binding(ACCEPTED_GATE_CONTRACT_BINDING, "accepted gate contract")
    operation_path = _verify_binding(AUTHOR_OPERATION_BINDING, "R5 author operation")
    source_hash_before = sha256_file(source)
    operation_module = _load_exact_module(operation_path)
    if bpy_module is None:
        import bpy as bpy_module  # type: ignore[import-not-found]
    bpy_module.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    if Path(bpy_module.data.filepath).resolve() != source:
        raise R24OneShotAuthorError("Blender did not load exact R19 Attempt 06")
    before = protected_scope_snapshot(bpy_module)
    operation_result = validate_operation_result(
        operation_module.author_external_surface_r5(
            bpy_module=bpy_module,
            source_path=source,
            accepted_gate_contract_path=contract_path,
        )
    )
    after = protected_scope_snapshot(bpy_module)
    if canonical_sha256(before) != canonical_sha256(after):
        raise R24OneShotAuthorError("author operation changed out-of-scope data")
    neutral = restore_neutral(bpy_module)
    flags = mark_private_candidate(bpy_module)
    if sha256_file(source) != source_hash_before:
        raise R24OneShotAuthorError("preserved R19 source changed before save")
    _save_once(bpy_module, output)
    if sha256_file(source) != source_hash_before:
        raise R24OneShotAuthorError("preserved R19 source changed during candidate save")
    return {
        "schema": "kira.avatar.r24.one_shot_author_worker_result.v1",
        "status": "CANDIDATE_SAVED_ONCE_FRESH_REOPEN_REQUIRED_NOT_ACCEPTED",
        "source_sha256_before_after": source_hash_before,
        "candidate": {
            "path": str(output),
            "bytes": output.stat().st_size,
            "sha256": sha256_file(output),
            **flags,
        },
        "operation": operation_result,
        "protected_scope_sha256": canonical_sha256(after),
        "neutral": neutral,
        "save_count": 1,
        "render_performed": False,
        "export_performed": False,
        "runtime_mutation_performed": False,
        "candidate_accepted": False,
    }


def main() -> int:
    result = run_authoring(parse_args())
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
