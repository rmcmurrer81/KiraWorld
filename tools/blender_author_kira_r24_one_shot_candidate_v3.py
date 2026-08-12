#!/usr/bin/env python3
"""Inert append-only v3 Blender worker for one future R24/R7 transaction.

The worker never asks Blender to save to the public sealed-staging or final
candidate path.  Blender writes once to a nonce-private author path with normal
existing-file checking enabled.  The worker then publishes that private file
to the controller-reserved sealed-staging name with Win32 no-replace rename.
The controller may later perform a second no-replace publication to the final
candidate only after the author Job tree is independently quiescent.

All raw path components are inspected for links/reparse points before any
``resolve`` call and are rechecked at every open/save/publish boundary.  R7 and
author-operation identities are deliberately symbolic and execution authority
is false, so this module cannot open Blender or mutate a body today.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
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
    "RecoverySprint/continuation_20260808/kira_r24_one_shot_runtime_attempts_v3"
)
ATTEMPT_NAME = "attempt_01"
BODY_OBJECT_NAME = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"
PATCH_OBJECT_NAME = "Kira_R24_Intrinsic_EStar_Repaired_Patch"
RIG_OBJECT_NAME = "Kira_R19_BlackProject_Native_188_Rig"

ACCEPTED_R7_CONTRACT_BINDING: dict[str, object] = {
    "path": (
        "RecoverySprint/continuation_20260808/kira_r24_artifact_derived_gate_r7/"
        "KIRA_R24_ARTIFACT_DERIVED_GATE_R7_CONTRACT.json"
    ),
    "bytes": None,
    "sha256": None,
}
AUTHOR_OPERATION_R7_BINDING: dict[str, object] = {
    "path": "tools/blender_author_kira_r24_r7_external_surface_operation.py",
    "bytes": None,
    "sha256": None,
}
EXECUTION_AUTHORITY_GRANTED = False


class R24OneShotAuthorV3Error(RuntimeError):
    """Fail-closed v3 author error."""


def sha256_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _is_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        return bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except (AttributeError, FileNotFoundError):
        return False


def inspect_raw_nonreparse(raw: str | os.PathLike[str]) -> Path:
    """Inspect the lexical/raw path before any symlink-resolving operation."""
    if not isinstance(raw, (str, os.PathLike)) or not os.fspath(raw):
        raise R24OneShotAuthorV3Error("raw path is empty")
    raw_text = os.fspath(raw)
    path = Path(os.path.abspath(raw_text))
    cursor = Path(path.anchor)
    for part in path.parts[1:]:
        cursor = cursor / part
        if os.path.lexists(cursor) and _is_reparse(cursor):
            raise R24OneShotAuthorV3Error(f"raw path contains reparse component:{cursor}")
    return path


def checked_path(
    raw: str | os.PathLike[str],
    *,
    root: Path,
    require_file: bool = False,
    require_directory: bool = False,
) -> Path:
    lexical = inspect_raw_nonreparse(raw)
    lexical_root = inspect_raw_nonreparse(root)
    try:
        resolved_root = lexical_root.resolve(strict=True)
        resolved = lexical.resolve(strict=require_file or require_directory)
        resolved.relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise R24OneShotAuthorV3Error("path escaped its exact non-reparse root") from exc
    inspect_raw_nonreparse(lexical)
    if require_file and (not lexical.is_file() or _is_reparse(lexical)):
        raise R24OneShotAuthorV3Error("required regular non-reparse file is absent")
    if require_directory and (not lexical.is_dir() or _is_reparse(lexical)):
        raise R24OneShotAuthorV3Error("required regular non-reparse directory is absent")
    return lexical


def _verify_binding(binding: Mapping[str, object], label: str) -> Path:
    if set(binding) != {"path", "bytes", "sha256"}:
        raise R24OneShotAuthorV3Error(f"{label} binding fields changed")
    size = binding.get("bytes")
    digest = binding.get("sha256")
    if not isinstance(size, int) or isinstance(size, bool) or size < 1:
        raise R24OneShotAuthorV3Error(f"{label} byte identity is unsealed")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise R24OneShotAuthorV3Error(f"{label} digest identity is unsealed")
    raw = binding.get("path")
    if not isinstance(raw, str) or Path(raw).is_absolute():
        raise R24OneShotAuthorV3Error(f"{label} path is not project-relative")
    path = checked_path(ROOT / raw, root=ROOT, require_file=True)
    if path.stat().st_size != size or sha256_file(path) != digest:
        raise R24OneShotAuthorV3Error(f"{label} exact identity changed")
    return path


def _require_inert_authority() -> None:
    if EXECUTION_AUTHORITY_GRANTED is not True:
        raise R24OneShotAuthorV3Error("v3 authoring is inert; execution authority is false")


def verify_source(raw: str | os.PathLike[str]) -> Path:
    exact = checked_path(ROOT / SOURCE_RELATIVE, root=ROOT, require_file=True)
    supplied = checked_path(raw, root=ROOT, require_file=True)
    if supplied != exact:
        raise R24OneShotAuthorV3Error("source is not exact R19 Attempt 06")
    if supplied.stat().st_size != SOURCE_BYTES or sha256_file(supplied) != SOURCE_SHA256:
        raise R24OneShotAuthorV3Error("R19 source identity changed")
    return supplied


def validate_output_paths(
    private_raw: str | os.PathLike[str],
    staging_raw: str | os.PathLike[str],
    *,
    reservation_token: str,
    child_nonce: str,
) -> tuple[Path, Path, Path]:
    runtime = checked_path(ROOT / RUNTIME_ROOT_RELATIVE, root=ROOT, require_directory=True)
    attempt = checked_path(runtime / ATTEMPT_NAME, root=runtime, require_directory=True)
    private = checked_path(private_raw, root=attempt)
    staging = checked_path(staging_raw, root=attempt)
    expected_private_parent = attempt / f"private_author_{reservation_token}"
    expected_staging_parent = attempt / "sealed_staging"
    if private.parent != expected_private_parent or private.name != f"blender_write_{child_nonce}.blend":
        raise R24OneShotAuthorV3Error("private Blender target is not exact nonce-owned path")
    if staging.parent != expected_staging_parent or staging.name != f"candidate_{reservation_token}.blend":
        raise R24OneShotAuthorV3Error("sealed staging target is not exact reservation path")
    checked_path(private.parent, root=attempt, require_directory=True)
    checked_path(staging.parent, root=attempt, require_directory=True)
    return attempt, private, staging


def require_absent_raw(path: Path, *, root: Path) -> None:
    checked = checked_path(path, root=root)
    if os.path.lexists(checked) or checked.exists() or checked.is_symlink():
        raise R24OneShotAuthorV3Error("output target already exists or is reparsed")


def require_regular_raw(path: Path, *, root: Path) -> None:
    checked = checked_path(path, root=root, require_file=True)
    if checked != path or _is_reparse(checked):
        raise R24OneShotAuthorV3Error("output artifact is linked or reparsed")


def verify_reservation(path_raw: str | os.PathLike[str], token: str, attempt: Path) -> dict[str, object]:
    path = checked_path(path_raw, root=attempt, require_file=True)
    if path.parent != attempt or path.name != "CANDIDATE_RESERVATION_V3.json":
        raise R24OneShotAuthorV3Error("reservation path changed")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise R24OneShotAuthorV3Error("reservation payload is invalid") from exc
    expected = {
        "schema": "kira.avatar.r24.one_shot_candidate_reservation.v3",
        "token": token,
        "controller_pid": os.getppid(),
        "held_no_write_or_delete_share": True,
    }
    if not isinstance(payload, dict) or set(payload) != set(expected) or payload != expected:
        raise R24OneShotAuthorV3Error("reservation payload changed")
    return payload


def wait_for_job_gate(path_raw: str | os.PathLike[str], *, role: str, nonce: str, attempt: Path) -> dict[str, object]:
    path = checked_path(path_raw, root=attempt)
    deadline = time.monotonic() + 30.0
    while not path.is_file() and time.monotonic() < deadline:
        inspect_raw_nonreparse(path)
        time.sleep(0.025)
    path = checked_path(path, root=attempt, require_file=True)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise R24OneShotAuthorV3Error("Job gate payload is invalid") from exc
    expected = {
        "schema": "kira.avatar.r24.suspended_child_job_gate.v3",
        "role": role,
        "nonce": nonce,
        "parent_pid": os.getppid(),
        "child_pid": os.getpid(),
        "created_suspended": True,
        "job_configured": True,
        "assigned_before_resume": True,
        "resume_authorized": True,
    }
    if not isinstance(payload, dict) or payload != expected:
        raise R24OneShotAuthorV3Error("Job gate fields changed")
    return payload


def _load_operation(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("_kira_r24_r7_author_operation_v3", path)
    if spec is None or spec.loader is None:
        raise R24OneShotAuthorV3Error("R7 author operation cannot be imported")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "author_external_surface_r7", None)):
        raise R24OneShotAuthorV3Error("R7 author callable is absent")
    return module


def validate_operation_result(value: object) -> dict[str, object]:
    fields = {
        "schema", "status", "authorized_mutated_objects",
        "protected_scope_before_sha256", "protected_scope_after_sha256",
        "save_performed", "render_performed", "export_performed",
        "activation_performed", "assignment_performed", "publication_performed",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise R24OneShotAuthorV3Error("R7 author evidence fields changed")
    if value["schema"] != "kira.avatar.r24.r7_external_surface_author_operation.v1":
        raise R24OneShotAuthorV3Error("R7 author evidence schema changed")
    if value["status"] != "AUTHORED_IN_MEMORY_FRESH_REOPEN_REQUIRED":
        raise R24OneShotAuthorV3Error("R7 author status changed")
    if value["authorized_mutated_objects"] != [BODY_OBJECT_NAME, PATCH_OBJECT_NAME]:
        raise R24OneShotAuthorV3Error("R7 mutation scope changed")
    before = value["protected_scope_before_sha256"]
    if not isinstance(before, str) or not re.fullmatch(r"[0-9a-f]{64}", before):
        raise R24OneShotAuthorV3Error("R7 protected scope digest is invalid")
    if value["protected_scope_after_sha256"] != before:
        raise R24OneShotAuthorV3Error("R7 protected scope changed")
    for key in (
        "save_performed", "render_performed", "export_performed",
        "activation_performed", "assignment_performed", "publication_performed",
    ):
        if value[key] is not False:
            raise R24OneShotAuthorV3Error(f"forbidden R7 author action:{key}")
    return value


def restore_neutral(bpy_module: Any) -> dict[str, object]:
    rig = bpy_module.data.objects.get(RIG_OBJECT_NAME)
    if rig is None or str(rig.type) != "ARMATURE":
        raise R24OneShotAuthorV3Error("exact R19 rig is absent")
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
                maximum_error = max(maximum_error, abs(float(bone.matrix_basis[row][column]) - expected))
    if animation.action is not None or not math.isfinite(maximum_error) or maximum_error > 1e-10:
        raise R24OneShotAuthorV3Error("neutral restoration failed")
    return {"action_cleared": True, "pose_bone_count": len(rig.pose.bones), "maximum_error": maximum_error}


def mark_inert_private(bpy_module: Any) -> dict[str, bool]:
    body = bpy_module.data.objects.get(BODY_OBJECT_NAME)
    if body is None or str(body.type) != "MESH":
        raise R24OneShotAuthorV3Error("exact R19 body is absent")
    flags = {
        "private": True, "inactive": True, "unassigned": True,
        "unpublished": True, "runtime_eligible": False, "owner_approved": False,
    }
    for target in [body, *list(bpy_module.data.scenes)]:
        for key, value in flags.items():
            target[f"kira_r24_candidate_{key}"] = value
    return flags


def no_replace_move(source: Path, destination: Path, *, root: Path) -> None:
    if os.name != "nt":
        raise R24OneShotAuthorV3Error("Win32 no-replace publication is mandatory")
    require_regular_raw(source, root=root)
    require_absent_raw(destination, root=root)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.MoveFileExW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
    kernel32.MoveFileExW.restype = wintypes.BOOL
    if not kernel32.MoveFileExW(str(source), str(destination), 0):
        raise R24OneShotAuthorV3Error("private-to-sealed no-replace publication failed")
    if os.path.lexists(source):
        raise R24OneShotAuthorV3Error("private Blender file remained after publication")
    require_regular_raw(destination, root=root)


def save_private_once_then_seal(
    bpy_module: Any,
    private: Path,
    staging: Path,
    *,
    attempt: Path,
) -> dict[str, object]:
    require_absent_raw(private, root=attempt)
    require_absent_raw(staging, root=attempt)
    result = bpy_module.ops.wm.save_as_mainfile(
        filepath=str(private),
        check_existing=True,
        relative_remap=False,
    )
    if result != {"FINISHED"}:
        raise R24OneShotAuthorV3Error("the one private Blender save did not finish")
    require_regular_raw(private, root=attempt)
    private_digest = sha256_file(private)
    require_absent_raw(staging, root=attempt)
    no_replace_move(private, staging, root=attempt)
    if sha256_file(staging) != private_digest:
        raise R24OneShotAuthorV3Error("sealed staging bytes changed during no-replace publication")
    return {
        "private_write_removed": True,
        "sealed_staging_path": str(staging),
        "sealed_staging_bytes": staging.stat().st_size,
        "sealed_staging_sha256": private_digest,
        "blender_save_count": 1,
        "private_to_staging_no_replace_count": 1,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--private-write-output", required=True)
    parser.add_argument("--sealed-staging-output", required=True)
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
        raise R24OneShotAuthorV3Error("explicit author flag is absent")
    for label, value in (("child nonce", args.child_nonce), ("reservation token", args.reservation_token)):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise R24OneShotAuthorV3Error(f"{label} is malformed")
    if os.environ.get("KIRA_R24_ONE_SHOT_V3_CHILD_NONCE") != args.child_nonce:
        raise R24OneShotAuthorV3Error("child environment nonce changed")
    source = verify_source(args.source)
    attempt, private, staging = validate_output_paths(
        args.private_write_output,
        args.sealed_staging_output,
        reservation_token=args.reservation_token,
        child_nonce=args.child_nonce,
    )
    verify_reservation(args.reservation, args.reservation_token, attempt)
    wait_for_job_gate(args.job_gate, role=args.role, nonce=args.child_nonce, attempt=attempt)
    contract = _verify_binding(ACCEPTED_R7_CONTRACT_BINDING, "accepted R7 contract")
    operation_path = _verify_binding(AUTHOR_OPERATION_R7_BINDING, "R7 author operation")
    operation = _load_operation(operation_path)
    source_before = sha256_file(source)
    require_absent_raw(private, root=attempt)
    require_absent_raw(staging, root=attempt)
    if bpy_module is None:
        import bpy as bpy_module  # type: ignore[import-not-found]
    inspect_raw_nonreparse(source)
    bpy_module.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    if inspect_raw_nonreparse(bpy_module.data.filepath) != source:
        raise R24OneShotAuthorV3Error("Blender did not load exact raw R19 source")
    operation_result = validate_operation_result(
        operation.author_external_surface_r7(
            bpy_module=bpy_module,
            source_path=source,
            accepted_gate_contract_path=contract,
        )
    )
    neutral = restore_neutral(bpy_module)
    flags = mark_inert_private(bpy_module)
    if sha256_file(source) != source_before:
        raise R24OneShotAuthorV3Error("preserved R19 source changed before save")
    sealed = save_private_once_then_seal(bpy_module, private, staging, attempt=attempt)
    if sha256_file(source) != source_before:
        raise R24OneShotAuthorV3Error("preserved R19 source changed during save")
    return {
        "schema": "kira.avatar.r24.one_shot_author_worker.v3",
        "role": "author",
        "child_nonce": args.child_nonce,
        "status": "SEALED_STAGING_PUBLISHED_CONTROLLER_EXIT_PROOF_REQUIRED",
        "sealed": sealed,
        "operation": operation_result,
        "neutral": neutral,
        "flags": flags,
        "candidate_accepted": False,
    }


def main() -> int:
    result = run_authoring(parse_args())
    print(canonical_bytes(result).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
