#!/usr/bin/env python3
"""R23 read-only preflight Attempt 04 with Blender 5.1 action hashing."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import traceback
from typing import Any, Mapping

import bpy


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_preflight_kira_r23_cc0_afes_expanded_mask as base  # noqa: E402
from tools import blender_preflight_kira_r23_cc0_afes_expanded_mask_attempt03 as attempt03  # noqa: E402
from tools.kira_r23_blender51_action_serializer import (  # noqa: E402
    action_inventory,
    actions_sha256,
    serialize_actions,
)


DEFAULT_ADDENDUM = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_expanded_mask_attempt04_preparation/"
    "KIRA_R23_ATTEMPT04_BLENDER51_ACTION_HASH_ADDENDUM.json"
)
ALLOWED_OUTPUT = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_expanded_mask/preflight_attempt_04"
)


class Attempt04Error(RuntimeError):
    pass


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--addendum", default=DEFAULT_ADDENDUM.as_posix())
    return parser.parse_args(raw)


def project_path(raw: str | Path) -> Path:
    value = Path(str(raw))
    if value.is_absolute() or ".." in value.parts:
        raise Attempt04Error(f"unsafe project-relative path: {raw}")
    resolved = (ROOT / value).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise Attempt04Error(f"path escaped project: {raw}") from exc
    return resolved


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_binding(name: str, binding: Mapping[str, Any]) -> dict[str, Any]:
    path = project_path(str(binding["path"]))
    if not path.is_file():
        raise Attempt04Error(f"missing {name}: {relative(path)}")
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != int(binding["bytes"]) or digest != str(binding["sha256"]):
        raise Attempt04Error(
            f"{name} binding mismatch: size={size}, sha256={digest}"
        )
    return {"path": relative(path), "bytes": size, "sha256": digest}


def output_directory(addendum: Mapping[str, Any]) -> Path:
    directory = project_path(str(addendum["output"]["directory"]))
    if directory != project_path(ALLOWED_OUTPUT):
        raise Attempt04Error("Attempt 04 output path is not exact")
    if directory.exists():
        raise FileExistsError(
            f"append-only Attempt 04 output already exists: {relative(directory)}"
        )
    return directory


def main() -> int:
    args = arguments()
    addendum_path = project_path(args.addendum)
    addendum = read_json(addendum_path)
    if addendum.get("schema") != (
        "kira.avatar.r23_cc0_afes_preflight_attempt04_"
        "blender51_action_hash_addendum.v1"
    ):
        raise Attempt04Error("wrong Attempt 04 addendum schema")

    verified_bindings = {
        name: verify_binding(name, addendum[name])
        for name in (
            "base_worker",
            "base_config",
            "attempt03_contract_addendum",
            "source_blend",
            "qualified_cc0_foundation",
        )
    }
    verified_bindings["proven_serializer_sources"] = [
        verify_binding(f"serializer_source_{index}", row)
        for index, row in enumerate(addendum["proven_serializer_sources"], 1)
    ]
    verified_bindings["preserved_attempts"] = [
        verify_binding(row["attempt_id"], row)
        for row in addendum["preserved_attempts"]
    ]
    if Path(base.__file__).resolve() != project_path(addendum["base_worker"]["path"]):
        raise Attempt04Error("imported base worker path is not exact")

    base_config_path = project_path(addendum["base_config"]["path"])
    sealed_config = read_json(base_config_path)
    config = deepcopy(sealed_config)
    config["alignment_and_mask"]["maximum_expanded_mask_world_extent_m"] = (
        addendum["contract"]["world_extent_addendum_retained_m"]
    )
    differences = attempt03.leaf_differences(sealed_config, config)
    expected_differences = [
        {
            "path": "alignment_and_mask.maximum_expanded_mask_world_extent_m",
            "before": addendum["contract"]["base_world_extent_m"],
            "after": addendum["contract"]["world_extent_addendum_retained_m"],
        }
    ]
    if differences != expected_differences:
        raise Attempt04Error(f"Attempt 04 config diff is not exact: {differences}")

    attempt03_addendum = read_json(
        project_path(addendum["attempt03_contract_addendum"]["path"])
    )
    directory = output_directory(addendum)
    directory.mkdir(parents=True, exist_ok=False)
    original_action_hasher = base.actions_sha256

    def blender51_action_hasher() -> str:
        return actions_sha256(bpy.data.actions)

    try:
        base.actions_sha256 = blender51_action_hasher
        try:
            report, captured = attempt03.run_base_with_selected_mask_capture(
                config, base_config_path
            )
        finally:
            base.actions_sha256 = original_action_hasher

        selected_faces = {int(value) for value in captured.get("chosen", set())}
        allowed_faces = {int(value) for value in captured.get("allowed", set())}
        if not selected_faces or not allowed_faces:
            raise Attempt04Error("selected mask trace capture was incomplete")
        selected = report["expanded_r19_mask"]
        expected = addendum["expected_selection"]
        selected_attempt = selected["attempts"][-1]
        selection_checks = {
            "smallest_passing_ring_exact": (
                selected["selected_exterior_rings"]
                == expected["smallest_passing_exterior_rings"]
            ),
            "face_count_exact": selected["selected_topology"]["face_count"]
            == expected["face_count"],
            "face_hash_exact": selected["selected_face_index_sha256"]
            == expected["face_index_sha256"],
            "outer_seam_count_exact": selected["selected_topology"][
                "boundary_cycle_lengths"
            ]
            == [expected["ordered_outer_seam_vertices"]],
            "world_extent_exact": abs(
                selected_attempt["world_extent_m"] - expected["world_extent_m"]
            )
            <= 1.0e-12,
            "world_extent_within_040m": selected_attempt["world_extent_m"]
            <= expected["maximum_allowed_world_extent_m"],
            "all_selection_gates_pass": all(selected_attempt["gates"].values()),
        }
        if not all(selection_checks.values()):
            raise Attempt04Error(
                f"deterministic selected mask contract failed: {selection_checks}"
            )

        body = bpy.data.objects[config["r19_contract"]["body_object"]]
        locality = attempt03.dominant_group_locality_proof(
            body, selected_faces, allowed_faces, report, attempt03_addendum
        )
        if not locality["passed"]:
            raise Attempt04Error(
                f"selected mask locality proof failed: {locality['checks']}"
            )

        action_rows = serialize_actions(bpy.data.actions)
        action_record = action_inventory(action_rows)
        action_record.update(
            {
                "serializer": (
                    "legacy_fcurves_or_blender51_slots_layers_strips_"
                    "channelbags_slot_handles_fcurves_v1"
                ),
                "legacy_path_used_when_fcurves_attribute_present": True,
                "layered_path_used_otherwise": True,
                "complete_keyframe_handles_and_types_hashed": True,
                "freeze_ledger_actions_sha256_matches": (
                    report["fresh_freeze_ledger"]["actions_sha256"]
                    == action_record["serialized_rows_sha256"]
                ),
            }
        )
        if not action_record["freeze_ledger_actions_sha256_matches"]:
            raise Attempt04Error("freeze-ledger action hash mismatch")

        report["artifact_kind"] = (
            "KIRA_R23_CC0_AFES_EXPANDED_MASK_READ_ONLY_PREFLIGHT_ATTEMPT04"
        )
        report["attempt_id"] = "attempt_04"
        report["status"] = "PREFLIGHT_PASS_AUTHORING_NOT_STARTED"
        report["attempt04_addendum"] = {
            "path": relative(addendum_path),
            "sha256": sha256_file(addendum_path),
            "exact_config_leaf_differences": differences,
            "all_other_config_leaves_unchanged": True,
            "only_runtime_function_replaced": "actions_sha256",
            "base_action_hasher_restored_after_preflight": (
                base.actions_sha256 is original_action_hasher
            ),
            "wrapper": {
                "path": relative(Path(__file__)),
                "sha256": sha256_file(Path(__file__)),
            },
            "verified_bindings": verified_bindings,
        }
        report["blender51_action_freeze_ledger"] = action_record
        report["deterministic_selection_checks"] = selection_checks
        report["explicit_locality_escape_proof"] = locality
        filename = str(addendum["output"]["pass_file"])
        result = 0
    except Exception as exc:
        base.actions_sha256 = original_action_hasher
        source_path = project_path(addendum["source_blend"]["path"])
        report = {
            "schema_version": 1,
            "artifact_kind": (
                "KIRA_R23_CC0_AFES_EXPANDED_MASK_READ_ONLY_PREFLIGHT_"
                "ATTEMPT04_FAILURE"
            ),
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PREFLIGHT_NO_GO_NO_CANDIDATE",
            "attempt_id": "attempt_04",
            "attempt04_addendum": {
                "path": relative(addendum_path),
                "sha256": sha256_file(addendum_path),
                "exact_config_leaf_differences": differences,
                "all_other_config_leaves_unchanged": differences
                == expected_differences,
                "only_runtime_function_replaced": "actions_sha256",
                "base_action_hasher_restored_after_preflight": (
                    base.actions_sha256 is original_action_hasher
                ),
            },
            "verified_bindings": verified_bindings,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "source_blend": {
                "path": relative(source_path),
                "sha256_after": sha256_file(source_path),
                "expected_sha256": addendum["source_blend"]["sha256"],
            },
            "operations": {
                "mesh_mutation_performed": False,
                "candidate_created": False,
                "blend_written": False,
                "render_performed": False,
                "export_performed": False,
                "runtime_mutation_performed": False,
                "reference_only_asset_loaded": False,
            },
        }
        filename = str(addendum["output"]["failure_file"])
        result = 2

    evidence_path = directory / filename
    if evidence_path.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {relative(evidence_path)}")
    evidence_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "evidence": relative(evidence_path),
                "sha256": sha256_file(evidence_path),
                "candidate_created": False,
            },
            indent=2,
        )
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())

