#!/usr/bin/env python3
"""Read-only R26 probe for the approved nail-only local-surface fallback.

The probe recreates the exact bound R26 body and official rig in memory, runs
only the left little-finger nail component through the unchanged primary path
and the new fallback, audits raw and evaluated geometry, removes all temporary
data, and writes append-only JSON evidence.  It never saves or opens a Blend as
the main file, renders, builds a candidate, activates, assigns, exports,
publishes, or uploads anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import bpy


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import blender_avatar_natural_nail_delivery_v3 as nails  # noqa: E402
from tools import blender_build_biological_robert_r26_bald_owner_review as r26  # noqa: E402
from tools import (  # noqa: E402
    blender_diagnose_robert_r26_finger5_nail_exact_looptris as diagnosis02,
)
from Core.avatar_natural_nail_delivery_v3 import (  # noqa: E402
    FREE_EDGE_MATERIAL,
    NAIL_BED_MATERIAL,
    expected_nail_inventory,
)


EXPECTED_CONFIG_SHA256 = (
    "c64fa0f833caa86fb59a53d46ab98852ecd8a926666680a1aad11cce54a07c57"
)
EXPECTED_CONFIG_ADAPTER_SHA256 = (
    "5d87a610bba4b7a6dd915176545ac882c6b326f6d39527ff1a55eb3052348551"
)
EXPECTED_PATCHED_ADAPTER_SHA256 = (
    "65edf49c0f72523a7728f30ee5243a522d9866f825e9b940ad44f23f41b669c8"
)
TARGET_NAIL_ID = "fingernail_5_L"
TARGET_BONE = "finger5-3.L"

EXPECTED_BINDINGS = {
    "worker": {
        "path": "Tools/blender_build_biological_robert_r26_bald_owner_review.py",
        "sha256": "b9926bebe59b4f6720ee690d58da3752c172c1ddb10e517b2f27e4b5581f7f74",
    },
    "patched_adapter": {
        "path": "Tools/blender_avatar_natural_nail_delivery_v3.py",
        "sha256": EXPECTED_PATCHED_ADAPTER_SHA256,
    },
    "unchanged_contract": {
        "path": "Core/avatar_natural_nail_delivery_v3.py",
        "sha256": "8ce6cad33e519382043509f81fc1d465d354dac12ff427f33234cd12d52ce9ab",
    },
    "exact_auditor": {
        "path": "Tools/blender_exact_mesh_intersections.py",
        "sha256": "75c9f9633686776b72ec7bd83362521daae3d9f9497106b0491b8f85490c3ad1",
    },
    "focused_static_test": {
        "path": "Tools/test_blender_avatar_natural_nail_delivery_v3_static.py",
        "sha256": "56d3aed81ea5686bca6935658d6ce7f3803e567b4f34c1ae614d8bb6c04041ab",
    },
    "unchanged_pure_test": {
        "path": "Tools/test_avatar_natural_nail_delivery_v3.py",
        "sha256": "d8e55b52f156f113ebea0e63b7f306d163f6a3fd355fb99be24eb1c529de0bec",
    },
    "diagnosis02_script": {
        "path": "Tools/blender_diagnose_robert_r26_finger5_nail_exact_looptris.py",
        "sha256": "60aab7f364fda37f68ad1412ae7dfe85a080d616ce8213045038dff71d2dcc5a",
    },
    "diagnosis02_result": {
        "path": (
            "RecoverySprint/continuation_20260802/"
            "biological_robert_r26_bounded_run/attempt_08/nail_diagnosis/"
            "DIAGNOSTIC_RESULT_02.json"
        ),
        "sha256": "05eb1e43ab6365428d693a9b3565bfedbfd3a85e8c637a92129224c125acb397",
    },
    "diagnosis02_manifest": {
        "path": (
            "RecoverySprint/continuation_20260802/"
            "biological_robert_r26_bounded_run/attempt_08/nail_diagnosis/"
            "PACKAGE_MANIFEST_02.json"
        ),
        "sha256": "61009a9e5b28ee25a8782251fc9baaabdb4484862dbf951de240f67c97d17782",
    },
    "approved_proposal": {
        "path": (
            "RecoverySprint/continuation_20260802/"
            "biological_robert_r26_bounded_run/attempt_08/nail_diagnosis/"
            "NAIL_COMPONENT_CORRECTION_PROPOSAL_01.md"
        ),
        "sha256": "4def40575485522c25dfae9b47f09c1bd0ab9c2a20e315f3f2d1c8a4b1ffd35f",
    },
}


class RobertR26NailFallbackProbeError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def project_path(value: str) -> Path:
    path = (PROJECT_ROOT / value).resolve()
    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise RobertR26NailFallbackProbeError(
            f"path escapes project root: {path}"
        ) from exc
    return path


def verify_bindings() -> dict[str, Any]:
    records: dict[str, Any] = {}
    for binding, expected in EXPECTED_BINDINGS.items():
        path = project_path(str(expected["path"]))
        if not path.is_file():
            raise RobertR26NailFallbackProbeError(
                f"bound probe input absent: {path}"
            )
        actual = sha256_file(path)
        if actual != str(expected["sha256"]):
            raise RobertR26NailFallbackProbeError(
                f"bound probe input changed: {binding};"
                f"expected={expected['sha256']};actual={actual}"
            )
        records[binding] = {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": actual,
        }
    return records


def verify_config_inputs_except_adapter(config: dict[str, Any]) -> dict[str, Any]:
    records: dict[str, Any] = {}
    for binding, expected in config["inputs"].items():
        path = project_path(str(expected["path"]))
        if not path.is_file():
            raise RobertR26NailFallbackProbeError(
                f"config input absent: {binding}: {path}"
            )
        actual = sha256_file(path)
        if binding == "natural_nail_component_worker":
            if str(expected["sha256"]) != EXPECTED_CONFIG_ADAPTER_SHA256:
                raise RobertR26NailFallbackProbeError(
                    "config no longer records the sealed Attempt 08 adapter"
                )
            if actual != EXPECTED_PATCHED_ADAPTER_SHA256:
                raise RobertR26NailFallbackProbeError(
                    "component probe adapter differs from reviewed patch"
                )
            disposition = "EXPECTED_REVIEWED_COMPONENT_PATCH_NOT_REBOUND"
        else:
            if actual != str(expected["sha256"]):
                raise RobertR26NailFallbackProbeError(
                    f"config input changed: {binding};"
                    f"expected={expected['sha256']};actual={actual}"
                )
            disposition = "EXACT_CONFIG_BINDING_MATCH"
        if "bytes" in expected and path.stat().st_size != int(expected["bytes"]):
            raise RobertR26NailFallbackProbeError(
                f"config input byte count changed: {binding}"
            )
        records[binding] = {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": actual,
            "disposition": disposition,
        }
    return records


def cleanup_probe_data(nail: Any | None, materials: list[Any]) -> None:
    if nail is not None and nail.name in bpy.data.objects:
        nails._remove_object_and_mesh(nail)  # noqa: SLF001
    for material in materials:
        if material is not None and material.name in bpy.data.materials:
            if material.users == 0:
                bpy.data.materials.remove(material)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def main() -> None:
    args = parse_args()
    config_path = project_path(args.config)
    output_path = project_path(args.output)
    if output_path.exists():
        raise RobertR26NailFallbackProbeError(
            f"append-only component probe output exists: {output_path}"
        )
    candidate_path = project_path(
        "Avatar/private_owner_review/dual_robert_20260729/"
        "biological_robert_r26_bald_owner_review"
    )
    if candidate_path.exists():
        raise RobertR26NailFallbackProbeError(
            "R26 candidate appeared before component probe"
        )
    if sha256_file(config_path) != EXPECTED_CONFIG_SHA256:
        raise RobertR26NailFallbackProbeError("R26 config changed before probe")

    evidence: dict[str, Any] = {
        "schema": "kira.avatar.robert_r26_finger5_local_surface_fallback_probe.v1",
        "created_utc": utc_now(),
        "status": "RUNNING_READ_ONLY_COMPONENT_PROBE",
        "config": {
            "path": config_path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": config_path.stat().st_size,
            "sha256": sha256_file(config_path),
            "rebound_for_patch": False,
        },
        "candidate_absent_before": True,
        "candidate_absent_after": None,
        "bindings_before": None,
        "bindings_after": None,
        "config_inputs_before": None,
        "config_inputs_after": None,
        "target": {"nail_id": TARGET_NAIL_ID, "bone": TARGET_BONE},
        "blend_opened_as_main_file": False,
        "blend_saved": False,
        "render_performed": False,
        "candidate_created": False,
        "activation_assignment_export_publication_or_upload": False,
    }
    nail = None
    materials: list[Any] = []
    failed = False
    try:
        evidence["bindings_before"] = verify_bindings()
        config = r26.json_file(config_path)
        evidence["config_inputs_before"] = verify_config_inputs_except_adapter(
            config
        )
        (
            body,
            armature,
            height,
            height_envelope,
            transfer_report,
            rig_report,
        ) = diagnosis02.recreate_bound_body_and_rig(config)
        body_signature_before = nails._mesh_signature(body)  # noqa: SLF001
        rig_signature_before = nails._rig_signature(armature)  # noqa: SLF001
        body_modifier_count_before = len(body.modifiers)
        body_tree = nails.v1._world_surface_bvh(body)  # noqa: SLF001
        body_points, body_triangles = nails._world_surface_geometry(  # noqa: SLF001
            body
        )
        bed_material = nails._natural_nail_material(  # noqa: SLF001
            "R26_Finger5_Fallback_Probe_Nail_Bed",
            NAIL_BED_MATERIAL,
        )
        free_edge_material = nails._natural_nail_material(  # noqa: SLF001
            "R26_Finger5_Fallback_Probe_Free_Edge",
            FREE_EDGE_MATERIAL,
        )
        materials.extend([bed_material, free_edge_material])
        definition = next(
            row
            for row in expected_nail_inventory()
            if row["nail_id"] == TARGET_NAIL_ID
        )
        nail, record = nails._projected_oval_nail_plate(  # noqa: SLF001
            name="R26_Finger5_Local_Surface_Fallback_Probe",
            nail_id=TARGET_NAIL_ID,
            body_points=body_points,
            body_triangles=body_triangles,
            body_tree=body_tree,
            armature=armature,
            bone_name=TARGET_BONE,
            outward_hint=definition["outward_hint"],
            length_m=height * float(definition["length_height_fraction"]),
            width_m=height * float(definition["width_height_fraction"]),
            target_height_m=height,
            bed_material=bed_material,
            free_edge_material=free_edge_material,
        )
        body_signature_after = nails._mesh_signature(body)  # noqa: SLF001
        rig_signature_after = nails._rig_signature(armature)  # noqa: SLF001
        evaluated_exact = r26.exact_cross_intersections(body, [nail])
        evaluated_clearance = r26.component_surface_clearance_report(body, [nail])
        gates = {
            "unchanged_primary_exhausted_all_24_variants": int(
                record["primary_projection_attempt_count"]
            )
            == 24,
            "fallback_path_used": record["projection_query_mode"]
            == "nearest_coherent_local_surface_fallback",
            "fallback_attempted": int(record["fallback_projection_attempt_count"])
            >= 1,
            "fallback_grid_is_17x17": list(record["projection_grid_dimensions"])
            == [17, 17],
            "nearest_query_bound_respected": float(
                record["maximum_nearest_query_distance_m"]
            )
            <= nails.LOCAL_SURFACE_MAXIMUM_QUERY_DISTANCE_M,
            "locality_gate_passed": record["grid_locality"][
                "locality_gate_passed"
            ]
            is True,
            "winding_gate_passed": record["top_surface_winding"][
                "all_top_surface_faces_outward"
            ]
            is True,
            "raw_exact_genuine_intersections_zero": int(
                record["body_surface_triangle_overlap_count"]
            )
            == 0,
            "evaluated_exact_genuine_intersections_zero": int(
                evaluated_exact["total_exact_genuine_triangle_pair_count"]
            )
            == 0,
            "evaluated_clearance_positive": float(
                evaluated_clearance["minimum_unsigned_surface_clearance_m"]
            )
            > 0.0,
            "evaluated_clearance_below_bound": float(
                evaluated_clearance["maximum_unsigned_surface_clearance_m"]
            )
            <= float(config["component_follow"]["nail_maximum_surface_clearance_m"]),
            "body_mesh_unchanged": body_signature_after == body_signature_before,
            "official_rig_unchanged": rig_signature_after == rig_signature_before,
            "body_modifier_stack_unchanged": len(body.modifiers)
            == body_modifier_count_before,
            "only_one_nail_component_instantiated": sum(
                obj.type == "MESH" and "Fallback_Probe" in obj.name
                for obj in bpy.data.objects
            )
            == 1,
        }
        evidence.update(
            {
                "height_envelope": height_envelope,
                "transfer_summary": transfer_report,
                "rig_summary": rig_report,
                "body_mesh_sha256_before": body_signature_before,
                "body_mesh_sha256_after": body_signature_after,
                "official_rig_sha256_before": rig_signature_before,
                "official_rig_sha256_after": rig_signature_after,
                "component_record": record,
                "evaluated_exact_intersections": evaluated_exact,
                "evaluated_clearance": evaluated_clearance,
                "gates": gates,
            }
        )
        if not all(gates.values()):
            failed_names = [name for name, passed in gates.items() if not passed]
            raise RobertR26NailFallbackProbeError(
                "component probe gates failed: " + ",".join(failed_names)
            )
        evidence["status"] = "PASS_READ_ONLY_COMPONENT_PROBE_NO_CANDIDATE_NO_SAVE"
    except Exception as exc:
        failed = True
        evidence["status"] = "FAILED_READ_ONLY_COMPONENT_PROBE_PRESERVED"
        evidence["exception_type"] = type(exc).__name__
        evidence["exception"] = str(exc)
        evidence["traceback"] = traceback.format_exc()
    finally:
        cleanup_probe_data(nail, materials)
        evidence["temporary_probe_objects_remaining"] = sum(
            "Fallback_Probe" in obj.name for obj in bpy.data.objects
        )
        evidence["temporary_probe_meshes_remaining"] = sum(
            "Fallback_Probe" in mesh.name for mesh in bpy.data.meshes
        )
        evidence["candidate_absent_after"] = not candidate_path.exists()
        try:
            evidence["bindings_after"] = verify_bindings()
            config_after = r26.json_file(config_path)
            evidence["config_inputs_after"] = verify_config_inputs_except_adapter(
                config_after
            )
        except Exception as binding_exc:
            failed = True
            evidence["status"] = "FAILED_READ_ONLY_COMPONENT_PROBE_PRESERVED"
            evidence["post_cleanup_binding_exception"] = str(binding_exc)
            evidence["post_cleanup_binding_traceback"] = traceback.format_exc()
        if (
            int(evidence["temporary_probe_objects_remaining"]) != 0
            or int(evidence["temporary_probe_meshes_remaining"]) != 0
            or evidence["candidate_absent_after"] is not True
        ):
            failed = True
            evidence["status"] = "FAILED_READ_ONLY_COMPONENT_PROBE_PRESERVED"
            evidence["cleanup_gate_failed"] = True
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
