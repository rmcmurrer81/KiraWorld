#!/usr/bin/env python3
"""Bounded one-nail probe for the R26 weight-constrained projection repair.

The probe is deliberately limited to the already-failing left little-finger
nail.  It recreates the exact body and rig in memory, permits at most one nail
object, and gates the complete evaluated Armature-plus-Solidify shell.  It
never saves a Blend, renders, creates a candidate package, changes a config,
exports, activates, assigns, publishes, or uploads anything.
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

from Core.avatar_natural_nail_delivery_v3 import (  # noqa: E402
    FREE_EDGE_MATERIAL,
    NAIL_BED_MATERIAL,
    expected_nail_inventory,
)
from tools import blender_avatar_natural_nail_delivery_v3 as nails  # noqa: E402
from tools import blender_avatar_weight_constrained_nail_projection_v1 as repair  # noqa: E402
from tools import blender_build_biological_robert_r26_bald_owner_review as r26  # noqa: E402
from tools import (  # noqa: E402
    blender_diagnose_robert_r26_finger5_nail_exact_looptris as diagnosis02,
)
from tools import (  # noqa: E402
    blender_probe_robert_r26_all20_evaluated_nail_footprints as all20,
)


EXPECTED_CONFIG_SHA256 = (
    "c64fa0f833caa86fb59a53d46ab98852ecd8a926666680a1aad11cce54a07c57"
)
TARGET_NAIL_ID = "fingernail_5_L"
TARGET_BONE = "finger5-3.L"
FIXED_BINDINGS = {
    "all20_probe_script": {
        "path": "Tools/blender_probe_robert_r26_all20_evaluated_nail_footprints.py",
        "sha256": "61d0322f5091e46c4ab8cc117e443a03c4009f2146b9b974100b3bd6dc52924d",
    },
    "all20_probe_result": {
        "path": (
            "RecoverySprint/continuation_20260802/"
            "biological_robert_r26_bounded_run/attempt_09_preparation/"
            "nail_all20_evaluated_footprint_probe/PROBE_RESULT.json"
        ),
        "sha256": "6a9626d14481f2b90c42fc25a0c268031fbd8a5616ad54625e9a87af30d1a11a",
    },
    "modifier_stage_script": {
        "path": "Tools/blender_diagnose_robert_r26_finger5_nail_modifier_stages.py",
        "sha256": "caba970f4f0a5c53ee39b804e0718695245b122c6b68c502838a8b78a39b6860",
    },
    "modifier_stage_result": {
        "path": (
            "RecoverySprint/continuation_20260802/"
            "biological_robert_r26_bounded_run/attempt_09_preparation/"
            "nail_modifier_stage_diagnosis/DIAGNOSTIC_RESULT.json"
        ),
        "sha256": "c5df50067511dbaffcad5f735416e5b1f5777c06670e5784d2f21d409093b4fc",
    },
    "strict_footprint_contract": {
        "path": "Core/avatar_nail_footprint_binding_v1.py",
        "sha256": "94c5df362b83fccbe64cc0d076339dd35237cd83b80d81bc63332113509f0bf6",
    },
    "source_mapping_revalidation": {
        "path": (
            "RecoverySprint/continuation_20260802/"
            "biological_robert_r26_bounded_run/attempt_09_preparation/"
            "nail_inventory_mapping_audit/"
            "OFFICIAL_SOURCE_MAPPING_AUDIT_STRICT_POLICY_REVALIDATION.json"
        ),
        "sha256": "620ebe22602b760c56aa7ca57986e467a7c34836d84fab6d9d4ec065ea7e4b5d",
    },
    "weight_constrained_contract": {
        "path": "Core/avatar_nail_weight_constrained_projection_v1.py",
        "sha256": "3f0823f78cdb6e0e7c3880a89dee3ae1c35f50b6ac0f5ce61e52a169a77de2b2",
    },
    "weight_constrained_contract_tests": {
        "path": "Tools/test_avatar_nail_weight_constrained_projection_v1.py",
        "sha256": "cfe08c1badd72a0093a62a86550b4918962a35ac5b709bc7e64ad54f754d5921",
    },
    "weight_constrained_blender_adapter": {
        "path": "Tools/blender_avatar_weight_constrained_nail_projection_v1.py",
        "sha256": "d769962a1b3f7be2e99c3ce0d2b808124f6ee6045e904c38f49079c1d658c251",
    },
    "weight_constrained_blender_adapter_static_tests": {
        "path": "Tools/test_blender_avatar_weight_constrained_nail_projection_v1_static.py",
        "sha256": "8a95acd040bc08d56b42dc364ff69e92d1092ca51ceddf4f4234511acbd793f3",
    },
    "existing_unbound_v3_adapter": {
        "path": "Tools/blender_avatar_natural_nail_delivery_v3.py",
        "sha256": "65edf49c0f72523a7728f30ee5243a522d9866f825e9b940ad44f23f41b669c8",
    },
    "natural_nail_contract": {
        "path": "Core/avatar_natural_nail_delivery_v3.py",
        "sha256": "8ce6cad33e519382043509f81fc1d465d354dac12ff427f33234cd12d52ce9ab",
    },
}


class RobertR26WeightConstrainedFinger5ProbeError(RuntimeError):
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
    path = (PROJECT_ROOT / value).resolve()
    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise RobertR26WeightConstrainedFinger5ProbeError(
            f"path escapes project root: {path}"
        ) from exc
    return path


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def verify_fixed_inputs(config_path: Path) -> dict[str, Any]:
    if sha256_file(config_path) != EXPECTED_CONFIG_SHA256:
        raise RobertR26WeightConstrainedFinger5ProbeError(
            "R26 config changed before bounded repair probe"
        )
    records = {
        "all20_nested_fixed_inputs": all20.verify_fixed_inputs(config_path),
    }
    for name, expected in FIXED_BINDINGS.items():
        path = project_path(str(expected["path"]))
        actual = sha256_file(path)
        if actual != str(expected["sha256"]):
            raise RobertR26WeightConstrainedFinger5ProbeError(
                f"fixed repair input changed: {name};"
                f"expected={expected['sha256']};actual={actual}"
            )
        records[name] = {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": actual,
        }
    all20_result = json.loads(
        project_path(str(FIXED_BINDINGS["all20_probe_result"]["path"]))
        .read_text(encoding="utf-8")
    )
    if all20_result.get("status") != (
        "COMPLETE_READ_ONLY_ALL20_EVALUATED_FOOTPRINT_DIAGNOSIS_NO_CANDIDATE"
    ):
        raise RobertR26WeightConstrainedFinger5ProbeError(
            "all-20 diagnostic status changed"
        )
    summary = all20_result.get("binding_summary", {})
    if summary.get("passed_count") != 18 or summary.get("failed_nail_ids") != [
        "fingernail_5_L",
        "fingernail_5_R",
    ]:
        raise RobertR26WeightConstrainedFinger5ProbeError(
            "all-20 bilateral failure boundary changed"
        )
    return records


def cleanup_all() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def main() -> None:
    args = parse_args()
    config_path = project_path(args.config)
    output_path = project_path(args.output)
    if output_path.exists():
        raise RobertR26WeightConstrainedFinger5ProbeError(
            f"append-only output exists: {output_path}"
        )
    candidate_path = project_path(
        "Avatar/private_owner_review/dual_robert_20260729/"
        "biological_robert_r26_bald_owner_review"
    )
    if candidate_path.exists():
        raise RobertR26WeightConstrainedFinger5ProbeError(
            "R26 candidate appeared before bounded one-nail repair probe"
        )

    evidence: dict[str, Any] = {
        "schema": "kira.avatar.robert_r26_weight_constrained_finger5_probe.v1",
        "created_utc": utc_now(),
        "status": "RUNNING_BOUNDED_ONE_NAIL_WEIGHT_CONSTRAINED_PROBE",
        "target": {"nail_id": TARGET_NAIL_ID, "bone": TARGET_BONE},
        "maximum_nail_objects": 1,
        "config_rebound": False,
        "blend_opened_as_main_file": False,
        "blend_saved": False,
        "render_performed": False,
        "candidate_created": False,
        "activation_assignment_export_publication_or_upload": False,
        "candidate_absent_before": True,
        "candidate_absent_after": None,
    }
    failed = False
    nail = None
    materials = []
    try:
        evidence["fixed_inputs_before"] = verify_fixed_inputs(config_path)
        config = r26.json_file(config_path)
        body, armature, height, height_envelope, transfer, rig = (
            diagnosis02.recreate_bound_body_and_rig(config)
        )
        body_signature_before = nails._mesh_signature(body)  # noqa: SLF001
        rig_signature_before = nails._rig_signature(armature)  # noqa: SLF001
        body_modifier_count_before = len(body.modifiers)
        definition = next(
            row
            for row in expected_nail_inventory()
            if row["nail_id"] == TARGET_NAIL_ID
        )
        if str(definition["bone"]) != TARGET_BONE:
            raise RobertR26WeightConstrainedFinger5ProbeError(
                "target inventory bone changed"
            )
        bed = nails._natural_nail_material(  # noqa: SLF001
            "R26_Weight_Constrained_Finger5_Probe_Bed", NAIL_BED_MATERIAL
        )
        edge = nails._natural_nail_material(  # noqa: SLF001
            "R26_Weight_Constrained_Finger5_Probe_Edge", FREE_EDGE_MATERIAL
        )
        materials.extend([bed, edge])
        nail, record = repair.build_weight_constrained_nail_v1(
            body=body,
            armature=armature,
            definition=definition,
            target_height_m=height,
            name="R26_Weight_Constrained_Finger5_L_Probe",
            bed_material=bed,
            free_edge_material=edge,
        )
        nail["private_owner_review_only"] = True
        nail["inactive_candidate"] = True
        nail["runtime_activation_allowed"] = False
        nail["nail_component"] = True
        body_signature_after = nails._mesh_signature(body)  # noqa: SLF001
        rig_signature_after = nails._rig_signature(armature)  # noqa: SLF001
        nail_meshes = [
            obj
            for obj in bpy.data.objects
            if obj.type == "MESH" and bool(obj.get("nail_component", False))
        ]
        final_shell = record["final_evaluated_complete_shell_gate"]
        selection = record["selection"]
        gates = {
            "exact_one_nail_component_instantiated": len(nail_meshes) == 1
            and nail_meshes[0] == nail,
            "declared_terminal_bone_unchanged": record[
                "declared_terminal_bone"
            ]
            == TARGET_BONE,
            "strict_declared_digit_footprint_passed": record[
                "footprint_binding"
            ]["passed"]
            is True,
            "one_connected_declared_digit_region_selected": selection[
                "every_sample_uses_one_connected_region"
            ]
            is True,
            "occluding_first_hit_was_demonstrably_rejected": int(
                selection["neighboring_or_occluding_first_hit_rejected_count"]
            )
            > 0,
            "complete_evaluated_shell_passed": final_shell["passed"] is True,
            "zero_exact_final_shell_penetrations": int(
                final_shell["exact_genuine_triangle_pair_count"]
            )
            == 0,
            "no_automatic_bone_remap": record[
                "automatic_bone_remap_performed"
            ]
            is False,
            "body_mesh_unchanged": body_signature_after
            == body_signature_before,
            "official_rig_unchanged": rig_signature_after
            == rig_signature_before,
            "body_modifier_stack_unchanged": len(body.modifiers)
            == body_modifier_count_before,
        }
        if not all(gates.values()):
            raise RobertR26WeightConstrainedFinger5ProbeError(
                "one-nail repair gates failed: "
                + ",".join(name for name, passed in gates.items() if not passed)
            )
        evidence.update(
            {
                "height_envelope": height_envelope,
                "transfer_summary": transfer,
                "rig_summary": rig,
                "record": record,
                "body_mesh_sha256_before": body_signature_before,
                "body_mesh_sha256_after": body_signature_after,
                "official_rig_sha256_before": rig_signature_before,
                "official_rig_sha256_after": rig_signature_after,
                "gates": gates,
                "status": (
                    "PASS_BOUNDED_ONE_NAIL_WEIGHT_CONSTRAINED_EVALUATED_SHELL_"
                    "NO_CANDIDATE_NO_SAVE"
                ),
            }
        )
    except Exception as exc:
        failed = True
        evidence["status"] = (
            "FAILED_BOUNDED_ONE_NAIL_WEIGHT_CONSTRAINED_PROBE_PRESERVED"
        )
        evidence["exception_type"] = type(exc).__name__
        evidence["exception"] = str(exc)
        evidence["traceback"] = traceback.format_exc()
    finally:
        cleanup_all()
        for material in materials:
            if material.name in bpy.data.materials and material.users == 0:
                bpy.data.materials.remove(material)
        evidence["temporary_objects_remaining"] = len(bpy.data.objects)
        evidence["temporary_meshes_remaining"] = len(bpy.data.meshes)
        evidence["candidate_absent_after"] = not candidate_path.exists()
        try:
            evidence["fixed_inputs_after"] = verify_fixed_inputs(config_path)
        except Exception as binding_exc:
            failed = True
            evidence["status"] = (
                "FAILED_BOUNDED_ONE_NAIL_WEIGHT_CONSTRAINED_PROBE_PRESERVED"
            )
            evidence["post_cleanup_binding_exception"] = str(binding_exc)
            evidence["post_cleanup_binding_traceback"] = traceback.format_exc()
        if (
            evidence["temporary_objects_remaining"] != 0
            or evidence["temporary_meshes_remaining"] != 0
            or evidence["candidate_absent_after"] is not True
        ):
            failed = True
            evidence["status"] = (
                "FAILED_BOUNDED_ONE_NAIL_WEIGHT_CONSTRAINED_PROBE_PRESERVED"
            )
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
