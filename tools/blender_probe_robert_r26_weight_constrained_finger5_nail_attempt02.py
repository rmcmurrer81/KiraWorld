#!/usr/bin/env python3
"""Attempt 02 cleanup-only wrapper for the passing R26 one-nail probe.

Attempt 01 passed every geometry, mapping, attachment, preservation, and exact
evaluated-shell gate.  It failed only because object deletion left four
zero-user mesh datablocks in the isolated ``--factory-startup`` process.  This
wrapper preserves Attempt 01 byte-for-byte, changes no construction threshold,
and replaces only its final cleanup callback with ownership-scoped mesh-data
cleanup.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

import bpy


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import (  # noqa: E402
    blender_probe_robert_r26_weight_constrained_finger5_nail as attempt01,
)


ATTEMPT_LABEL = "attempt_02"
EXPECTED_OUTPUT = (
    "RecoverySprint/continuation_20260802/"
    "biological_robert_r26_bounded_run/attempt_09_preparation/"
    "nail_weight_constrained_finger5_probe/attempt_02/PROBE_RESULT.json"
)
ATTEMPT01_SCRIPT = (
    "Tools/blender_probe_robert_r26_weight_constrained_finger5_nail.py"
)
ATTEMPT01_SCRIPT_SHA256 = (
    "9c61e417fb63564cda488d3d89a400e29bd4e4b0de362843e2ed0bd3764a93b4"
)
ATTEMPT01_RESULT = (
    "RecoverySprint/continuation_20260802/"
    "biological_robert_r26_bounded_run/attempt_09_preparation/"
    "nail_weight_constrained_finger5_probe/PROBE_RESULT.json"
)
ATTEMPT01_RESULT_SHA256 = (
    "a9387c8b1616af32cd6dc87d62e2c7eaf577c67650d23243427f9bf5a109c53a"
)
ATTEMPT01_RESULT_BYTES = 207404


class Attempt02CleanupError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = (PROJECT_ROOT / value).resolve()
    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise Attempt02CleanupError(f"path escapes project root: {path}") from exc
    return path


def requested_output() -> Path:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    try:
        index = argv.index("--output")
        value = argv[index + 1]
    except (ValueError, IndexError) as exc:
        raise Attempt02CleanupError("Attempt 02 requires --output") from exc
    path = project_path(value)
    if path != project_path(EXPECTED_OUTPUT):
        raise Attempt02CleanupError(
            "Attempt 02 output must use the exact append-only attempt_02 path"
        )
    if path.exists():
        raise Attempt02CleanupError(f"Attempt 02 output already exists: {path}")
    return path


def fixed_attempt01_evidence() -> dict[str, Any]:
    rows = {
        "attempt_01_probe_script": (
            project_path(ATTEMPT01_SCRIPT),
            ATTEMPT01_SCRIPT_SHA256,
            None,
        ),
        "attempt_01_preserved_result": (
            project_path(ATTEMPT01_RESULT),
            ATTEMPT01_RESULT_SHA256,
            ATTEMPT01_RESULT_BYTES,
        ),
    }
    records = {}
    for name, (path, expected_hash, expected_bytes) in rows.items():
        actual_hash = sha256_file(path)
        actual_bytes = path.stat().st_size
        if actual_hash != expected_hash:
            raise Attempt02CleanupError(
                f"fixed Attempt 01 evidence changed: {name}"
            )
        if expected_bytes is not None and actual_bytes != expected_bytes:
            raise Attempt02CleanupError(
                f"fixed Attempt 01 evidence size changed: {name}"
            )
        records[name] = {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": actual_bytes,
            "sha256": actual_hash,
        }
    return records


def isolated_factory_startup_preflight() -> dict[str, Any]:
    objects = list(bpy.data.objects)
    meshes = list(bpy.data.meshes)
    type_counts = {
        object_type: sum(obj.type == object_type for obj in objects)
        for object_type in sorted({obj.type for obj in objects})
    }
    gates = {
        "no_blend_is_loaded": bpy.data.filepath == "",
        "exact_three_factory_objects": len(objects) == 3,
        "factory_object_types_are_camera_light_mesh": type_counts
        == {"CAMERA": 1, "LIGHT": 1, "MESH": 1},
        "exact_one_initial_mesh_datablock": len(meshes) == 1,
        "initial_mesh_has_exactly_one_user": len(meshes) == 1
        and int(meshes[0].users) == 1,
        "initial_mesh_is_used_by_the_only_mesh_object": len(meshes) == 1
        and sum(obj.type == "MESH" and obj.data == meshes[0] for obj in objects)
        == 1,
    }
    if not all(gates.values()):
        raise Attempt02CleanupError(
            "Attempt 02 refuses non-isolated or non-factory-startup Blender state: "
            + ",".join(name for name, passed in gates.items() if not passed)
        )
    mesh = meshes[0]
    return {
        "attempt_label": ATTEMPT_LABEL,
        "scope": "isolated_factory_startup_process_only",
        "gates": gates,
        "initial_object_names": sorted(obj.name for obj in objects),
        "initial_mesh": {
            "name": mesh.name,
            "users": int(mesh.users),
            "pointer": int(mesh.as_pointer()),
        },
        "passed": True,
    }


ATTEMPT01_FIXED = fixed_attempt01_evidence()
FACTORY_PREFLIGHT = isolated_factory_startup_preflight()
CLEANUP_EVIDENCE: dict[str, Any] = {
    "attempt_label": ATTEMPT_LABEL,
    "phase": "preflight_not_yet_run",
    "factory_startup": FACTORY_PREFLIGHT,
    "attempt_01_preserved": ATTEMPT01_FIXED,
    "geometry_projection_threshold_or_bone_change": False,
}
ORIGINAL_CLEANUP = attempt01.cleanup_all
ORIGINAL_VERIFY = attempt01.verify_fixed_inputs


def cleanup_objects_and_owned_mesh_datablocks() -> None:
    """Remove only mesh data owned by this isolated probe process."""

    meshes_before = list(bpy.data.meshes)
    mesh_objects_before = {
        int(obj.data.as_pointer()): obj.name
        for obj in bpy.data.objects
        if obj.type == "MESH" and obj.data is not None
    }
    baseline_pointer = int(FACTORY_PREFLIGHT["initial_mesh"]["pointer"])
    rows = []
    for mesh in meshes_before:
        pointer = int(mesh.as_pointer())
        if pointer == baseline_pointer:
            classification = "factory_startup_mesh_deleted_by_probe_initialization"
        elif pointer in mesh_objects_before:
            object_name = mesh_objects_before[pointer]
            classification = (
                "weight_constrained_nail_mesh"
                if "Weight_Constrained_Finger5_L_Probe" in object_name
                else "recreated_R26_body_mesh"
            )
        else:
            classification = "appended_canonical_source_mesh_orphan"
        rows.append(
            {
                "name": mesh.name,
                "pointer": pointer,
                "users_before_object_cleanup": int(mesh.users),
                "owning_object_before_cleanup": mesh_objects_before.get(pointer),
                "classification": classification,
                "removed": False,
            }
        )

    # Attempt 01 proved that exactly these four datablocks remain after object
    # deletion.  Any count change fails closed rather than broadening cleanup.
    exact_four_before = len(meshes_before) == 4
    ORIGINAL_CLEANUP()
    for row, mesh in zip(rows, meshes_before):
        row["users_after_object_cleanup"] = int(mesh.users)
        if int(mesh.users) == 0 and mesh.name in bpy.data.meshes:
            bpy.data.meshes.remove(mesh)
            row["removed"] = True
        else:
            row["removal_blocked_nonzero_users"] = int(mesh.users)

    classifications = sorted(row["classification"] for row in rows)
    expected_classifications = sorted(
        [
            "factory_startup_mesh_deleted_by_probe_initialization",
            "appended_canonical_source_mesh_orphan",
            "recreated_R26_body_mesh",
            "weight_constrained_nail_mesh",
        ]
    )
    gates = {
        "exact_four_attempt01_mesh_datablocks_observed": exact_four_before,
        "exact_expected_four_classifications": classifications
        == expected_classifications,
        "every_owned_mesh_had_zero_users_after_object_cleanup": all(
            row.get("users_after_object_cleanup") == 0 for row in rows
        ),
        "every_owned_mesh_removed": all(row["removed"] is True for row in rows),
        "zero_objects_after_cleanup": len(bpy.data.objects) == 0,
        "zero_mesh_datablocks_after_cleanup": len(bpy.data.meshes) == 0,
    }
    CLEANUP_EVIDENCE.clear()
    CLEANUP_EVIDENCE.update(
        {
            "attempt_label": ATTEMPT_LABEL,
            "phase": "cleanup_complete",
            "factory_startup": FACTORY_PREFLIGHT,
            "attempt_01_preserved": ATTEMPT01_FIXED,
            "ownership_rule": (
                "only the exact four mesh datablocks present in the isolated "
                "probe immediately before final object cleanup; remove only "
                "after each reaches users==0"
            ),
            "mesh_datablocks": rows,
            "mesh_datablock_count_before": len(meshes_before),
            "mesh_datablock_count_after": len(bpy.data.meshes),
            "object_count_after": len(bpy.data.objects),
            "gates": gates,
            "geometry_projection_threshold_or_bone_change": False,
            "passed": all(gates.values()),
        }
    )


def verify_with_attempt02_cleanup(config_path: Path) -> dict[str, Any]:
    records = ORIGINAL_VERIFY(config_path)
    # Re-hash Attempt 01 on both the before and after verification boundaries.
    preserved = fixed_attempt01_evidence()
    if (
        CLEANUP_EVIDENCE.get("phase") == "cleanup_complete"
        and CLEANUP_EVIDENCE.get("passed") is not True
    ):
        raise Attempt02CleanupError(
            "Attempt 02 ownership-scoped mesh cleanup failed closed"
        )
    records["attempt_02_cleanup_only_contract"] = {
        "attempt_label": ATTEMPT_LABEL,
        "expected_append_only_output": EXPECTED_OUTPUT,
        "attempt_01": preserved,
        "cleanup": dict(CLEANUP_EVIDENCE),
        "geometry_projection_threshold_or_bone_change": False,
        "config_rebind": False,
    }
    return records


def main() -> None:
    requested_output()
    attempt01.cleanup_all = cleanup_objects_and_owned_mesh_datablocks
    attempt01.verify_fixed_inputs = verify_with_attempt02_cleanup
    attempt01.main()


if __name__ == "__main__":
    main()
