#!/usr/bin/env python3
"""Inert v2 Blender author worker for one future R24/R5 transaction.

V2 is append-only and does not import or modify the rejected v1 worker.  Its
R5 and author-operation identities are deliberately unsealed and execution
authority is false.  Therefore it fails before importing ``bpy`` or opening a
Blend today.

After a future independent reseal, the worker may run only after its process
was created suspended, assigned to the controller's kill-on-close Job, and
resumed.  It opens the exact R19 source with ``load_ui=False`` and saves only
to a controller-reserved, nonce-named staging path.  It refuses an existing,
symlinked, or reparse output immediately before the one Blender save.  The CPU
controller, not Blender, later publishes that staging file to the final
candidate with an atomic no-replace move after the author tree is quiescent.
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
import stat
import sys
import time
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RELATIVE = PurePosixPath(
    "RecoverySprint/continuation_20260802/"
    "kira_r19_bald_targeted_correction/attempt_06/"
    "kira_r19_bald_targeted_material_movement_correction.blend"
)
SOURCE_BYTES = 90_861_425
SOURCE_SHA256 = "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f"
RUNTIME_ROOT_RELATIVE = PurePosixPath(
    "RecoverySprint/continuation_20260808/kira_r24_one_shot_runtime_attempts_v2"
)
BODY_OBJECT_NAME = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"
PATCH_OBJECT_NAME = "Kira_R24_Intrinsic_EStar_Repaired_Patch"
RIG_OBJECT_NAME = "Kira_R19_BlackProject_Native_188_Rig"

ACCEPTED_R5_CONTRACT_BINDING: dict[str, object] = {
    "path": (
        "RecoverySprint/continuation_20260808/kira_r24_artifact_derived_gate_r5/"
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
EXECUTION_AUTHORITY_GRANTED = False


class R24OneShotAuthorV2Error(RuntimeError):
    """Fail-closed v2 worker error."""


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


def _is_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        return bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except AttributeError:
        return False


def _project_path(raw: object, *, require_file: bool = False) -> Path:
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute():
        raise R24OneShotAuthorV2Error("project path must be nonempty and relative")
    pure = PurePosixPath(raw.replace("\\", "/"))
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise R24OneShotAuthorV2Error("unsafe project path component")
    cursor = ROOT
    for part in pure.parts:
        cursor = cursor / part
        if os.path.lexists(cursor) and _is_reparse(cursor):
            raise R24OneShotAuthorV2Error("project path contains a reparse component")
    try:
        cursor.resolve(strict=require_file).relative_to(ROOT.resolve())
    except (OSError, ValueError) as exc:
        raise R24OneShotAuthorV2Error("project path escaped the repository") from exc
    if require_file and (not cursor.is_file() or _is_reparse(cursor)):
        raise R24OneShotAuthorV2Error("exact regular file is absent or reparsed")
    return cursor


def _verify_binding(binding: Mapping[str, object], label: str) -> Path:
    if set(binding) != {"path", "bytes", "sha256"}:
        raise R24OneShotAuthorV2Error(f"{label} fields are not exact")
    size = binding.get("bytes")
    digest = binding.get("sha256")
    if not isinstance(size, int) or isinstance(size, bool) or size < 1:
        raise R24OneShotAuthorV2Error(f"{label} is not byte-sealed")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise R24OneShotAuthorV2Error(f"{label} is not digest-sealed")
    path = _project_path(binding.get("path"), require_file=True)
    if path.stat().st_size != size or sha256_file(path) != digest:
        raise R24OneShotAuthorV2Error(f"{label} identity changed")
    return path


def _require_inert_authority() -> None:
    if EXECUTION_AUTHORITY_GRANTED is not True:
        raise R24OneShotAuthorV2Error("v2 authoring is inert; execution authority is false")


def _verify_source(path: Path) -> None:
    exact = _project_path(SOURCE_RELATIVE.as_posix(), require_file=True)
    if path.resolve() != exact.resolve():
        raise R24OneShotAuthorV2Error("source is not exact R19 Attempt 06")
    if path.stat().st_size != SOURCE_BYTES or sha256_file(path) != SOURCE_SHA256:
        raise R24OneShotAuthorV2Error("R19 source identity changed")


def _safe_attempt_path(path: Path) -> tuple[Path, Path]:
    runtime = _project_path(RUNTIME_ROOT_RELATIVE.as_posix())
    try:
        relative = path.resolve(strict=False).relative_to(runtime.resolve(strict=False))
    except ValueError as exc:
        raise R24OneShotAuthorV2Error("staging output escaped v2 runtime root") from exc
    if len(relative.parts) != 3 or relative.parts[:2] != ("attempt_01", "author_staging"):
        raise R24OneShotAuthorV2Error("staging output is outside exact reserved attempt/staging root")
    if not re.fullmatch(r"candidate_[0-9a-f]{64}\.blend", relative.name):
        raise R24OneShotAuthorV2Error("staging output leaf is not nonce-bound")
    return runtime, runtime / "attempt_01"


def _assert_regular_nonreparse_parents(path: Path, stop: Path) -> None:
    cursor = path.parent
    while True:
        if not cursor.is_dir() or _is_reparse(cursor):
            raise R24OneShotAuthorV2Error("output parent is absent, linked, or reparsed")
        if cursor == stop:
            return
        if cursor.parent == cursor:
            raise R24OneShotAuthorV2Error("output parent escaped reserved root")
        cursor = cursor.parent


def refuse_existing_or_reparse_output(path: Path, attempt: Path) -> None:
    _assert_regular_nonreparse_parents(path, attempt)
    if os.path.lexists(path) or path.exists() or path.is_symlink():
        raise R24OneShotAuthorV2Error("Blender staging output already exists or is reparsed")


def verify_reservation(path: Path, token: str, attempt: Path) -> dict[str, object]:
    _assert_regular_nonreparse_parents(path, attempt)
    if not path.is_file() or _is_reparse(path):
        raise R24OneShotAuthorV2Error("controller reservation is absent or reparsed")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise R24OneShotAuthorV2Error("controller reservation is invalid") from exc
    expected = {
        "schema": "kira.avatar.r24.one_shot_candidate_reservation.v2",
        "token": token,
        "controller_pid": os.getppid(),
        "held_exclusive": True,
    }
    if not isinstance(payload, dict) or any(payload.get(key) != value for key, value in expected.items()):
        raise R24OneShotAuthorV2Error("controller reservation fields changed")
    return payload


def wait_for_job_gate(path: Path, *, role: str, nonce: str, timeout: float = 30.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while not path.is_file() and time.monotonic() < deadline:
        time.sleep(0.025)
    if not path.is_file() or _is_reparse(path):
        raise R24OneShotAuthorV2Error("suspended-launch Job gate did not arrive")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise R24OneShotAuthorV2Error("suspended-launch Job gate is invalid") from exc
    expected = {
        "schema": "kira.avatar.r24.suspended_child_job_gate.v2",
        "role": role,
        "nonce": nonce,
        "parent_pid": os.getppid(),
        "child_pid": os.getpid(),
        "created_suspended": True,
        "job_configured": True,
        "assigned_before_resume": True,
        "resume_authorized": True,
    }
    if not isinstance(payload, dict) or any(payload.get(key) != value for key, value in expected.items()):
        raise R24OneShotAuthorV2Error("suspended-launch Job gate fields changed")
    return payload


def _load_operation(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("_kira_r24_r5_author_operation_v2", path)
    if spec is None or spec.loader is None:
        raise R24OneShotAuthorV2Error("R5 author operation cannot be imported")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "author_external_surface_r5", None)):
        raise R24OneShotAuthorV2Error("R5 author callable is absent")
    return module


def validate_operation_result(value: object) -> dict[str, object]:
    fields = {
        "schema", "status", "authorized_mutated_objects",
        "protected_scope_before_sha256", "protected_scope_after_sha256",
        "save_performed", "render_performed", "export_performed",
        "activation_performed", "assignment_performed", "publication_performed",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise R24OneShotAuthorV2Error("R5 author operation evidence fields changed")
    if value["schema"] != "kira.avatar.r24.r5_external_surface_author_operation.v1":
        raise R24OneShotAuthorV2Error("R5 author operation schema changed")
    if value["status"] != "AUTHORED_IN_MEMORY_FRESH_REOPEN_REQUIRED":
        raise R24OneShotAuthorV2Error("R5 author operation status changed")
    if value["authorized_mutated_objects"] != [BODY_OBJECT_NAME, PATCH_OBJECT_NAME]:
        raise R24OneShotAuthorV2Error("R5 author mutation scope changed")
    before = value["protected_scope_before_sha256"]
    after = value["protected_scope_after_sha256"]
    if not isinstance(before, str) or not re.fullmatch(r"[0-9a-f]{64}", before) or after != before:
        raise R24OneShotAuthorV2Error("R5 author protected-scope evidence changed")
    for name in (
        "save_performed", "render_performed", "export_performed",
        "activation_performed", "assignment_performed", "publication_performed",
    ):
        if value[name] is not False:
            raise R24OneShotAuthorV2Error(f"forbidden R5 author operation: {name}")
    return value


def restore_neutral(bpy_module: Any) -> dict[str, object]:
    rig = bpy_module.data.objects.get(RIG_OBJECT_NAME)
    if rig is None or str(rig.type) != "ARMATURE":
        raise R24OneShotAuthorV2Error("exact R19 rig is absent")
    animation = rig.animation_data_create()
    animation.action = None
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    for scene in bpy_module.data.scenes:
        scene.frame_set(int(scene.frame_start))
    bpy_module.context.view_layer.update()
    maximum_error = 0.0
    for bone in rig.pose.bones:
        for row in range(4):
            for column in range(4):
                expected = 1.0 if row == column else 0.0
                maximum_error = max(
                    maximum_error,
                    abs(float(bone.matrix_basis[row][column]) - expected),
                )
    if animation.action is not None or not math.isfinite(maximum_error) or maximum_error > 1e-10:
        raise R24OneShotAuthorV2Error("neutral restoration failed")
    return {"action_cleared": True, "pose_bone_count": len(rig.pose.bones), "maximum_error": maximum_error}


def mark_inert_private(bpy_module: Any) -> dict[str, bool]:
    body = bpy_module.data.objects.get(BODY_OBJECT_NAME)
    if body is None or str(body.type) != "MESH":
        raise R24OneShotAuthorV2Error("exact R19 body is absent")
    flags = {
        "private": True,
        "inactive": True,
        "unassigned": True,
        "unpublished": True,
        "runtime_eligible": False,
        "owner_approved": False,
    }
    for target in [body, *list(bpy_module.data.scenes)]:
        for key, value in flags.items():
            target[f"kira_r24_candidate_{key}"] = value
    return flags


def save_staging_once(bpy_module: Any, staging: Path, attempt: Path) -> None:
    refuse_existing_or_reparse_output(staging, attempt)
    result = bpy_module.ops.wm.save_as_mainfile(
        filepath=str(staging),
        check_existing=False,
        relative_remap=False,
    )
    if result != {"FINISHED"}:
        raise R24OneShotAuthorV2Error("the one staging save did not finish")
    if not staging.is_file() or _is_reparse(staging):
        raise R24OneShotAuthorV2Error("the one staging save produced no regular nonreparse file")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--staging-output", required=True)
    parser.add_argument("--reservation", required=True)
    parser.add_argument("--reservation-token", required=True)
    parser.add_argument("--job-gate", required=True)
    parser.add_argument("--role", choices=["author"], required=True)
    parser.add_argument("--child-nonce", required=True)
    parser.add_argument("--execute-authoring", action="store_true")
    return parser.parse_args(argv)


def run_authoring(args: argparse.Namespace, *, bpy_module: Any | None = None) -> dict[str, object]:
    _require_inert_authority()
    if args.execute_authoring is not True:
        raise R24OneShotAuthorV2Error("explicit author flag is absent")
    for label, value in (("child nonce", args.child_nonce), ("reservation token", args.reservation_token)):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise R24OneShotAuthorV2Error(f"{label} is malformed")
    if os.environ.get("KIRA_R24_ONE_SHOT_V2_CHILD_NONCE") != args.child_nonce:
        raise R24OneShotAuthorV2Error("child environment nonce changed")
    source = Path(args.source).resolve()
    staging = Path(args.staging_output).resolve()
    reservation = Path(args.reservation).resolve()
    _verify_source(source)
    _runtime, attempt = _safe_attempt_path(staging)
    _assert_regular_nonreparse_parents(reservation, attempt)
    if reservation.parent != attempt:
        raise R24OneShotAuthorV2Error("reservation is not in exact attempt root")
    verify_reservation(reservation, args.reservation_token, attempt)
    wait_for_job_gate(Path(args.job_gate).resolve(), role=args.role, nonce=args.child_nonce)
    contract = _verify_binding(ACCEPTED_R5_CONTRACT_BINDING, "accepted R5 contract")
    operation_path = _verify_binding(AUTHOR_OPERATION_BINDING, "R5 author operation")
    operation = _load_operation(operation_path)
    source_before = sha256_file(source)
    refuse_existing_or_reparse_output(staging, attempt)
    if bpy_module is None:
        import bpy as bpy_module  # type: ignore[import-not-found]
    bpy_module.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    if Path(bpy_module.data.filepath).resolve() != source:
        raise R24OneShotAuthorV2Error("Blender did not load exact R19 source")
    operation_result = validate_operation_result(
        operation.author_external_surface_r5(
            bpy_module=bpy_module,
            source_path=source,
            accepted_gate_contract_path=contract,
        )
    )
    neutral = restore_neutral(bpy_module)
    flags = mark_inert_private(bpy_module)
    if sha256_file(source) != source_before:
        raise R24OneShotAuthorV2Error("preserved R19 source changed before save")
    save_staging_once(bpy_module, staging, attempt)
    if sha256_file(source) != source_before:
        raise R24OneShotAuthorV2Error("preserved R19 source changed during save")
    return {
        "schema": "kira.avatar.r24.one_shot_author_worker.v2",
        "role": "author",
        "child_nonce": args.child_nonce,
        "status": "STAGING_SAVED_ONCE_CONTROLLER_ATOMIC_PUBLISH_REQUIRED",
        "staging": {"path": str(staging), "bytes": staging.stat().st_size, "sha256": sha256_file(staging)},
        "operation": operation_result,
        "neutral": neutral,
        "flags": flags,
        "save_count": 1,
        "candidate_accepted": False,
    }


def main() -> int:
    result = run_authoring(parse_args())
    print(canonical_bytes(result).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
