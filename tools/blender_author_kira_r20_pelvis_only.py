#!/usr/bin/env python3
"""Author and independently verify Kira R20's bounded pelvic-surface patch.

This is deliberately a thin, self-contained Blender worker around the pure
``Core.kira_r20_curvilinear_pelvic_patch`` contract.  It is not a generic body
builder.  It may replace only the exact rejected 376-face R19 pelvic insert,
reuses the exact 34 seam vertices, creates no separate anatomy object, and
never activates, assigns, exports, clothes, publishes, or uploads a candidate.

Modes are intentionally separate so the saved Blend can be verified and
rendered by a fresh process.  The worker refuses an existing append-only output
directory and writes evidence with exclusive creation.  A failed preflight
never saves a Blend.  Author mode contains exactly one guarded save call.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct
import sys
import traceback
from typing import Any, Iterable, Iterator, Mapping, Sequence

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from Core import kira_r20_curvilinear_pelvic_patch as patch_contract  # noqa: E402
import blender_exact_mesh_intersections as exact_intersections  # noqa: E402


WORKER_ID = "KIRA_R20_PELVIS_ONLY_AUTHORING_WORKER_V1"
DEFAULT_CONFIG = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/AUTHORING_CONFIG.json"
)
CONFIG_SHA256 = "5ab9d60a948d7cac4e08e71a0f9c3927af9f33004ef23f888cc60f21b2e9e7cc"
PURE_CONTRACT_REL = "Core/kira_r20_curvilinear_pelvic_patch.py"
PURE_CONTRACT_SHA256 = "fe5b9f8b68dd7acd9b6eaaaf26d12d65fe0e3e263548e8979bcb26c0e58f640d"
PLAN_SHA256 = "d9907f9ac7db74999ce2853b8865f614ccacabfabacef82b3111374dd89d0035"
FREEZE_SHA256 = "b63bdff693d8efe239f982d72591e4523c860abe89107a79d7b4607e43243873"
SOURCE_LEDGER_SHA256 = "3076b54d86a705d599a142816ace5688bf34b89ce230d0ba11bfddcd55964ee4"
SOURCE_BLEND_SHA256 = "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f"
SOURCE_MANIFEST_SHA256 = "9c7038b60e2c712e49e810c0b7f7932bf36a18042dd00a6951834be59bb40f0c"
INTERFACE_SHA256 = "01beed05140bb22bff2de23922d280fb312952078b496f16fb4fd80d9d742c86"
BODY_NAME = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"
RIG_NAME = "Kira_R19_BlackProject_Native_188_Rig"
PATCH_MATERIAL_SLOT = 5
PATCH_MATERIAL_NAME = "R19_WarmTexture_Genitalia_Attempt06_BoundedSurfaceResponse"
EXPECTED_R19_MATERIAL_SLOT_NAMES = (
    "R19_WarmTexture_Torso_Attempt06_BoundedSurfaceResponse",
    "R19_WarmTexture_Arms_Attempt06_BoundedSurfaceResponse",
    "R19_WarmTexture_Legs_Attempt06_BoundedSurfaceResponse",
    "R19_WarmTexture_Face_Attempt06_BoundedSurfaceResponse",
    "R19_WarmTexture_Ears_Attempt06_BoundedSurfaceResponse",
    PATCH_MATERIAL_NAME,
)
PRIOR_FAILED_PREFLIGHT_SHA256 = (
    "c7b537780d4871679a298ccc47e0acab9b0e9d190afd7d48d3ccae999e35e03a"
)
PRIOR_FAILED_PREFLIGHT_ATTEMPT_02_SHA256 = (
    "ccbfe304673c5527f5be3897b54fc39ba1be23895de32f40dd1e5034303370e2"
)
PRIOR_FAILED_PREFLIGHT_ATTEMPT_03_SHA256 = (
    "3afa5894348d862974e3829c3c4dad5fa0d1aed92bf7c7c503d058d75c0f50ab"
)
FREEZE_IDENTITY_CORRECTION_SHA256 = (
    "b4fa8d912761239df62b8d6a3e252bd5ccc07c98cd123d7087b0b89512acdafb"
)
INTERFACE_ATTRIBUTE_CORRECTION_SHA256 = (
    "2d0475a38152521eba2e3ac664c8160abbe4cdbcb606897ffc64015ce219ae5e"
)
PREFLIGHT_RECONCILIATION_EVIDENCE_SHA256 = (
    "d4c61ba39d69664a862f8c4d8b052209ac72c1e2c6a02837f8afd0837e20c34c"
)
PREFLIGHT_RECONCILIATION_CHECKPOINT_SHA256 = (
    "69552b56adb644aecfa54bf2d9cd22495ca20eaa70c62520257e3151a4ec8260"
)
PREFLIGHT_RECONCILIATION_MANIFEST_SHA256 = (
    "06b68ef1a51fc7d6f9cf6c0a3424a0aef45e6c92088074cf2f3a45a7da67dc63"
)
PASSED_PREFLIGHT_ATTEMPT_04_MANIFEST_SHA256 = (
    "f59922da78291131808ee691c1ec502c1b5f634f690ce8017978b01ff2037c99"
)
PASSED_PREFLIGHT_ATTEMPT_04_EVIDENCE_SHA256 = (
    "ff0645d564f935c5e4bd93a621fcbf3653ba91fc0c1830d84196ec818acea105"
)
PASSED_PREFLIGHT_ATTEMPT_04_CHECKPOINT_SHA256 = (
    "9daf0f4e3b981dbcc5a63a11ca7919a8ca4f3f98288117dc3395fbb7b6281296"
)
AUTHOR_ATTEMPT_01_SUMMARY_SHA256 = (
    "728524ce8bb6f167f8e2eb7339423cf7a3af1e4c639f724d14fe5215bbc41062"
)
AUTHOR_ATTEMPT_01_FAILURE_SHA256 = (
    "abad8f5922f643b00c0491797fbd209f444711b2b0072bc45821433dc2a18ba5"
)
AUTHOR_ATTEMPT_01_CANDIDATE_A_FAILURE_SHA256 = (
    "93ce0d0e4bd5c4f0b7b3167ecc48397f7ec3df26d9b7c00fe0e6d966060bb597"
)
AUTHOR_ATTEMPT_01_CANDIDATE_B_FAILURE_SHA256 = (
    "208015ce9d56e1c1a4667ab6868d9f9f741d7e57b12a96e634054ba7e151ce8a"
)
AUTHOR_ATTEMPT_01_DIAGNOSIS_SHA256 = (
    "effcc7e2e9ff4c67c7caf63baa0aa06a67eb373d6de29f8e63a471efb450d3c3"
)
AUTHOR_ATTEMPT_02_SUMMARY_SHA256 = (
    "fb9689c481574839f2b3922f021167dd3decbd755e4ec66ea22c993c19bf6ffd"
)
AUTHOR_ATTEMPT_02_FAILURE_SHA256 = (
    "ed26cb56e861a3e00d97d98ae22f22580833b6fdc22f427088aead3d3a407527"
)
AUTHOR_ATTEMPT_02_CANDIDATE_A_FAILURE_SHA256 = (
    "b12f503486c0f89e41e2b230f6bc919379bfc410b3d530fe53bb2945e41c3762"
)
AUTHOR_ATTEMPT_02_CANDIDATE_B_FAILURE_SHA256 = (
    "1efdd7ef5b3bf6cd7d6d1aea7edcfe54e8175727d84dcbecb0e13daf30e978a6"
)
AUTHOR_ATTEMPT_02_DIAGNOSIS_SHA256 = (
    "b41d069db3b33aac1768330bf2c1d8dbd0ad0f2535032565bd67259baa26e9e6"
)
AUTHOR_ATTEMPT_03_SUMMARY_SHA256 = (
    "abaa9367fc71c44fb8d3923cb04abbf9e9f397084758e5894506c1cb4fb4126b"
)
AUTHOR_ATTEMPT_03_FAILURE_SHA256 = (
    "d1b14bb9cd1f31a33e23fd644a494ac5fa63d0e6bd1a192d980f566450abfdaa"
)
AUTHOR_ATTEMPT_03_CANDIDATE_A_FAILURE_SHA256 = (
    "01d43bc741de5c6ce8758fb18507b9c1d8d669b9b0968cb0754c8307a11fbc7b"
)
AUTHOR_ATTEMPT_03_CANDIDATE_B_FAILURE_SHA256 = (
    "c9b0491010918853bceadb4f17432444b85142313c60a354a9f6fb268cac698e"
)
AUTHOR_ATTEMPT_03_COORDINATE_DIAGNOSIS_SHA256 = (
    "180af87d31765236340c515729baea62e4d95bf77b8b71bdf696b7f75928ab55"
)
EXPECTED_PREFLIGHT_OUTPUT_REL = (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/preflight_attempt_04"
)
EXPECTED_AUTHOR_OUTPUT_REL = (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_04"
)
EXPECTED_SOURCE_COUNTS = (12612, 37569, 24936)
EXPECTED_RESULT_COUNTS = (13180, 38517, 25316)
EXPECTED_BOUNDARY_EDGES = 330
EXPECTED_BOUNDARY_LOOPS = 23
EXPECTED_SOURCE_MANIFEST_ENTRIES = 49
EXPECTED_SOURCE_SELF_INTERSECTIONS = 29
MAXIMUM_CANDIDATES = 2
POSE_FRAME = 30
SELECTED_SEATED_ACTION = "KIRA_R19_ATTEMPT05_SEATED_OPEN_HIP_A"
SELECTED_SUPINE_ACTION = "KIRA_R19_ATTEMPT05_SUPINE_FACE_UP_A"
KNEE_BONES = {"left": "lShin_07", "right": "rShin_023"}
KNEE_ROTATION_AXIS = "X"
LANDMARK_ATTRIBUTE_PREFIX = "R20_EXT_"
TRANSIENT_PREFIX = "R20_TRANSIENT_REVIEW_"
PLANNED_SURVIVING_ATTRIBUTE_RULES = {
    "custom_normal": {
        "domain": "CORNER",
        "data_type": "INT16_2D",
        "surviving_rule": "preserve every nonpatch encoded short2 value exactly",
        "new_patch_rule": "explicit (0, 0) auto-normal sentinel on every smooth new-patch corner plus localized continuity gate",
    },
    ".uv_select_vert": {
        "domain": "CORNER",
        "data_type": "BOOLEAN",
        "surviving_rule": "preserve every nonpatch editor selection value exactly",
        "new_patch_rule": "false",
    },
    ".uv_select_edge": {
        "domain": "CORNER",
        "data_type": "BOOLEAN",
        "surviving_rule": "preserve every nonpatch editor selection value exactly",
        "new_patch_rule": "false",
    },
    ".uv_select_face": {
        "domain": "FACE",
        "data_type": "BOOLEAN",
        "surviving_rule": "preserve every nonpatch editor selection value exactly",
        "new_patch_rule": "false",
    },
}
CUSTOM_NORMAL_NAME = "custom_normal"
UV_SELECTION_CORNER_NAMES = (".uv_select_vert", ".uv_select_edge")
UV_SELECTION_FACE_NAME = ".uv_select_face"
R19_SELECTED_SEAT = {
    "top_z_m": 0.7603846011161804,
    "x_min_m": -0.24802017092704776,
    "x_max_m": 0.24811551809310917,
    "y_min_m": -0.07903144511580466,
    "y_max_m": 0.24104623079299925,
    "contact_tolerance_m": 0.006,
}


class R20Error(RuntimeError):
    """Fail-closed R20 contract error."""


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument(
        "--mode", choices=("preflight", "author", "verify-render"), required=True
    )
    parser.add_argument("--candidate-id")
    parser.add_argument("--acknowledge-private-inactive", action="store_true")
    return parser.parse_args(argv)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise R20Error(f"path escapes project root: {path}") from exc


def resolve_project_path(value: str, *, must_exist: bool = True) -> Path:
    candidate = (PROJECT_ROOT / Path(value)).resolve()
    try:
        candidate.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise R20Error(f"path escapes project root: {value}") from exc
    if must_exist and not candidate.exists():
        raise FileNotFoundError(candidate)
    return candidate


def write_json_exclusive(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write("\n")


def write_text_exclusive(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)


def canonical_blender_name(name: str) -> str:
    stem, dot, suffix = str(name).rpartition(".")
    return stem if dot and len(suffix) == 3 and suffix.isdigit() else str(name)


def float_rows(matrix: Any) -> list[list[float]]:
    return [[float(value) for value in row] for row in matrix]


def vector_record(value: Sequence[float]) -> list[float]:
    return [round(float(component), 12) for component in value]


def _assert_hash(path: Path, expected: str, label: str) -> dict[str, Any]:
    actual = sha256_file(path)
    if actual != expected.lower():
        raise R20Error(f"{label} hash mismatch: {actual} != {expected}")
    return {
        "path": project_relative(path),
        "sha256": actual,
        "size_bytes": path.stat().st_size,
    }


def _manifest_member_paths(manifest_path: Path, manifest: Mapping[str, Any]) -> set[Path]:
    entries = manifest.get("files_excluding_this_manifest")
    if not isinstance(entries, list) or len(entries) != EXPECTED_SOURCE_MANIFEST_ENTRIES:
        raise R20Error("sealed R19 manifest must contain exactly 49 member records")
    source_directory = manifest_path.parent.resolve()
    seen_relative: set[str] = set()
    resolved: set[Path] = set()
    failures: list[dict[str, Any]] = []
    for record in entries:
        relative = str(record.get("path", ""))
        if not relative or relative in seen_relative:
            raise R20Error(f"duplicate or empty manifest path: {relative!r}")
        seen_relative.add(relative)
        path = resolve_project_path(relative)
        try:
            path.relative_to(source_directory)
        except ValueError as exc:
            raise R20Error(f"manifest member escapes sealed source package: {relative}") from exc
        resolved.add(path)
        actual_size = path.stat().st_size
        actual_hash = sha256_file(path)
        if actual_size != int(record.get("size_bytes", -1)) or actual_hash != str(
            record.get("sha256", "")
        ).lower():
            failures.append(
                {
                    "path": relative,
                    "expected_size": record.get("size_bytes"),
                    "actual_size": actual_size,
                    "expected_sha256": record.get("sha256"),
                    "actual_sha256": actual_hash,
                }
            )
    actual_members = {
        path.resolve()
        for path in source_directory.rglob("*")
        if path.is_file() and path.resolve() != manifest_path.resolve()
    }
    missing_from_manifest = sorted(project_relative(path) for path in actual_members - resolved)
    absent_on_disk = sorted(project_relative(path) for path in resolved - actual_members)
    if failures or missing_from_manifest or absent_on_disk:
        raise R20Error(
            "sealed R19 package failed whole-package verification: "
            + json.dumps(
                {
                    "member_mismatches": failures,
                    "unlisted_files": missing_from_manifest,
                    "missing_files": absent_on_disk,
                },
                sort_keys=True,
            )
        )
    return resolved


def validate_config(config_path: Path, args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Path]]:
    if not args.acknowledge_private_inactive:
        raise R20Error("--acknowledge-private-inactive is required")
    config_path = config_path.resolve(strict=True)
    if config_path != DEFAULT_CONFIG.resolve(strict=True):
        raise R20Error("only the exact prepared R20 authoring config is permitted")
    if CONFIG_SHA256.startswith("PENDING_"):
        raise R20Error("worker CONFIG_SHA256 binding was not finalized")
    _assert_hash(config_path, CONFIG_SHA256, "R20 authoring config")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if Path(str(config.get("project_root", ""))).resolve() != PROJECT_ROOT.resolve():
        raise R20Error("configured project root drifted")
    required_true = ("private", "inactive", "unassigned", "unpublished")
    required_false = (
        "runtime_eligible",
        "owner_approved",
        "scalp_hair_loaded",
        "body_activation_allowed",
        "clothing_allowed",
        "export_allowed",
        "publication_allowed",
    )
    if any(config.get(name) is not True for name in required_true):
        raise R20Error("private/inactive/unassigned/unpublished contract drifted")
    if any(config.get(name) is not False for name in required_false):
        raise R20Error("R20 config attempts to authorize a forbidden state")
    if int(config.get("maximum_candidate_count", -1)) != MAXIMUM_CANDIDATES:
        raise R20Error("R20 is bounded to exactly two candidates")
    expected_candidate_ids = [candidate.candidate_id for candidate in patch_contract.CANDIDATES]
    actual_candidate_ids = [str(record.get("candidate_id")) for record in config.get("candidates", [])]
    if actual_candidate_ids != expected_candidate_ids or len(set(actual_candidate_ids)) != 2:
        raise R20Error("candidate IDs/order drifted from the pure contract")

    path_keys = {
        "source_blend": SOURCE_BLEND_SHA256,
        "source_build_evidence": str(config["source_build_evidence_sha256"]),
        "source_package_manifest": SOURCE_MANIFEST_SHA256,
        "source_post_render_review": str(config["source_post_render_review_sha256"]),
        "r20_plan": PLAN_SHA256,
        "r20_freeze_ledger": FREEZE_SHA256,
        "r20_source_ledger": SOURCE_LEDGER_SHA256,
        "interface_evidence": INTERFACE_SHA256,
        "prior_failed_preflight": PRIOR_FAILED_PREFLIGHT_SHA256,
        "prior_failed_preflight_attempt_02": PRIOR_FAILED_PREFLIGHT_ATTEMPT_02_SHA256,
        "prior_failed_preflight_attempt_03": PRIOR_FAILED_PREFLIGHT_ATTEMPT_03_SHA256,
        "freeze_identity_correction": FREEZE_IDENTITY_CORRECTION_SHA256,
        "interface_attribute_correction": INTERFACE_ATTRIBUTE_CORRECTION_SHA256,
        "preflight_reconciliation_evidence": PREFLIGHT_RECONCILIATION_EVIDENCE_SHA256,
        "preflight_reconciliation_checkpoint": PREFLIGHT_RECONCILIATION_CHECKPOINT_SHA256,
        "preflight_reconciliation_manifest": PREFLIGHT_RECONCILIATION_MANIFEST_SHA256,
        "passed_preflight_attempt_04_manifest": PASSED_PREFLIGHT_ATTEMPT_04_MANIFEST_SHA256,
        "passed_preflight_attempt_04_evidence": PASSED_PREFLIGHT_ATTEMPT_04_EVIDENCE_SHA256,
        "passed_preflight_attempt_04_checkpoint": PASSED_PREFLIGHT_ATTEMPT_04_CHECKPOINT_SHA256,
        "author_attempt_01_summary": AUTHOR_ATTEMPT_01_SUMMARY_SHA256,
        "author_attempt_01_failure": AUTHOR_ATTEMPT_01_FAILURE_SHA256,
        "author_attempt_01_candidate_a_failure": AUTHOR_ATTEMPT_01_CANDIDATE_A_FAILURE_SHA256,
        "author_attempt_01_candidate_b_failure": AUTHOR_ATTEMPT_01_CANDIDATE_B_FAILURE_SHA256,
        "author_attempt_01_diagnosis": AUTHOR_ATTEMPT_01_DIAGNOSIS_SHA256,
        "author_attempt_02_summary": AUTHOR_ATTEMPT_02_SUMMARY_SHA256,
        "author_attempt_02_failure": AUTHOR_ATTEMPT_02_FAILURE_SHA256,
        "author_attempt_02_candidate_a_failure": AUTHOR_ATTEMPT_02_CANDIDATE_A_FAILURE_SHA256,
        "author_attempt_02_candidate_b_failure": AUTHOR_ATTEMPT_02_CANDIDATE_B_FAILURE_SHA256,
        "author_attempt_02_diagnosis": AUTHOR_ATTEMPT_02_DIAGNOSIS_SHA256,
        "author_attempt_03_summary": AUTHOR_ATTEMPT_03_SUMMARY_SHA256,
        "author_attempt_03_failure": AUTHOR_ATTEMPT_03_FAILURE_SHA256,
        "author_attempt_03_candidate_a_failure": AUTHOR_ATTEMPT_03_CANDIDATE_A_FAILURE_SHA256,
        "author_attempt_03_candidate_b_failure": AUTHOR_ATTEMPT_03_CANDIDATE_B_FAILURE_SHA256,
        "author_attempt_03_coordinate_diagnosis": AUTHOR_ATTEMPT_03_COORDINATE_DIAGNOSIS_SHA256,
    }
    paths: dict[str, Path] = {}
    for key, expected in path_keys.items():
        path = resolve_project_path(str(config[key]))
        _assert_hash(path, expected, key)
        paths[key] = path
    _assert_hash(PROJECT_ROOT / PURE_CONTRACT_REL, PURE_CONTRACT_SHA256, "pure R20 geometry contract")
    if config["body_object"] != BODY_NAME or config["rig_object"] != RIG_NAME:
        raise R20Error("body or rig binding drifted")
    if int(config["patch_material_slot"]) != PATCH_MATERIAL_SLOT:
        raise R20Error("patch material slot drifted")
    if str(config["patch_material"]) != PATCH_MATERIAL_NAME:
        raise R20Error("patch material name drifted")
    if tuple(config.get("expected_r19_material_slots", ())) != EXPECTED_R19_MATERIAL_SLOT_NAMES:
        raise R20Error("expected R19 regional material-slot order drifted")
    correction = config.get("material_slot_correction", {})
    if (
        int(correction.get("previous_incorrect_zero_based_slot", -1)) != 1
        or int(correction.get("corrected_zero_based_slot", -1)) != PATCH_MATERIAL_SLOT
        or correction.get("material_name_changed") is not False
        or correction.get("original_r20_plan_preserved_as_historical_incorrect_slot_record")
        is not True
    ):
        raise R20Error("Attempt-02 material-slot correction record drifted")
    freeze_contract = config.get("freeze_identity_contract", {})
    if freeze_contract != {
        "historical_ledger_record_count": 32,
        "historical_nonpersisted_exact_object": "Icosphere",
        "persisted_separate_protected_component_count": 31,
        "primary_surface_component_count": 1,
        "total_protected_component_count": 32,
        "review_context_component_count": 15,
        "whole_exact_inventory_required": True,
        "loose_object_matching_allowed": False,
    }:
        raise R20Error("Attempt-03 exact freeze-identity contract drifted")
    if int(config.get("schema_version", -1)) != 7:
        raise R20Error("Author Attempt-04 config schema drifted")
    if config.get("status") != (
        "AUTHOR_ATTEMPT_03_FAILED_CLOSED_ATTEMPT_04_COORDINATE_SPACE_REPAIR_"
        "PREPARED_NOT_EXECUTED"
    ):
        raise R20Error("Author Attempt-04 config status drifted")
    attempt04_contract = config.get("attempt_04_interface_attribute_contract", {})
    if attempt04_contract != {
        "sealed_r19_topology_is_cycle_order_authority": True,
        "historical_probe_bfs_order_used_as_adjacency": False,
        "licensed_full_precision_coordinate_set_bijective_tolerance_m": 1.0e-8,
        "surviving_nonpatch_attribute_elements_exact": True,
        "new_patch_uv_selection_values": False,
        "new_patch_custom_normal_short2": [0, 0],
        "whole_mesh_normal_setter_allowed": False,
        "global_normal_recalculation_allowed": False,
        "fresh_save_reopen_attribute_verification_required": True,
        "ordinary_and_opposite_light_normal_heatmaps_required": True,
    }:
        raise R20Error("Attempt-04 interface/attribute contract drifted")
    attempt02_contract = config.get("attempt_02_baseline_gate_contract", {})
    if attempt02_contract != {
        "r19_baseline_has_generated_r20_patch": False,
        "r19_baseline_candidate_only_patch_quality_evaluated": False,
        "r19_baseline_candidate_only_landmarks_evaluated": False,
        "r19_baseline_candidate_only_external_patch_gate_evaluated": False,
        "candidate_patch_gates_run_only_after_apply_local_patch": True,
        "generated_patch_face_count": 756,
        "generated_patch_all_quad_gate_required": True,
        "topology_candidate_parameters_and_thresholds_unchanged": True,
    }:
        raise R20Error("Author Attempt-02 baseline/candidate gate contract drifted")
    attempt03_contract = config.get("attempt_03_native_knee_contract", {})
    if attempt03_contract != {
        "evidence_path": str(config["source_build_evidence"]),
        "evidence_sha256": str(config["source_build_evidence_sha256"]),
        "left_shin_bone": KNEE_BONES["left"],
        "right_shin_bone": KNEE_BONES["right"],
        "manual_rotation_axis": KNEE_ROTATION_AXIS,
        "manual_knee_angles_degrees": [30, 55, 80],
        "manual_knee_state_scope": (
            "isolated bilateral shin-flexion stress diagnostics; not exact "
            "reproductions of the full frozen R19 actions"
        ),
        "manual_knee_states_reproduce_full_r19_actions": False,
        "selected_seated_action": SELECTED_SEATED_ACTION,
        "selected_supine_action": SELECTED_SUPINE_ACTION,
        "frozen_action_evaluation_frame": POSE_FRAME,
        "natural_owner_views_use_frozen_r19_actions": True,
        "seated_candidate_a_shin_rotations_degrees_xyz": [72.0, 0.0, 0.0],
        "seated_candidate_b_shin_rotations_degrees_xyz": [78.0, 0.0, 0.0],
        "pose_inventory_geometry_topology_thresholds_candidates_unchanged": True,
    }:
        raise R20Error("Author Attempt-03 native knee mapping/axis contract drifted")
    attempt04_coordinate_contract = config.get("attempt_04_coordinate_space_contract", {})
    if attempt04_coordinate_contract != {
        "failure_local_median_edge_scale": 1.8541125424006801,
        "preflight_serialized_local_median_edge_scale": 1.8541125424012472,
        "preflight_serialized_world_median_edge_scale_m": 0.017658196540973933,
        "expected_world_median_absolute_tolerance_m": 2.0e-8,
        "serialized_world_seam_crosscheck_tolerance_m": 1.0e-8,
        "body_matrix_world_sha256": "d17219fa4a62a17715a7c4dd587baaac643590f14cc6439e734ec43edd1b060a",
        "body_matrix_world": [
            [0.009523809887468815, 0.0, 0.0, 0.0],
            [0.0, 0.00952381081879139, -1.6055943241610748e-09, 0.0],
            [0.0, 1.6055943241610748e-09, 0.00952381081879139, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        "construction_and_quality_space": "project_world_meters",
        "live_full_precision_seam_from_canonical_ids": True,
        "serialized_world_seam_is_crosscheck_not_construction_input": True,
        "serialized_crosscheck_authority": (
            "passed_preflight_attempt_04_hash_bound_canonical_arrays"
        ),
        "full_affine_exterior_ring_point_transform": True,
        "inverse_transpose_normal_transform_and_renormalization": True,
        "normal_averaging_order": (
            "transform_and_normalize_each_incident_face_then_equal_weight_average"
        ),
        "winding_normals_share_project_world_space": True,
        "inverse_transform_generated_vertex_count": 740,
        "original_seam_local_coordinates_reused_exactly": True,
        "maximum_seam_local_roundtrip_delta_local_units": 1.0e-9,
        "maximum_generated_project_roundtrip_delta_m": 1.0e-9,
        "source_transform_must_match_exact_r19_matrix": True,
        "arbitrary_nonuniform_scale_or_shear_supported": False,
        "unsupported_transform_variation_fails_closed": True,
        "singular_reflected_projective_or_nonfinite_transform_fails_closed": True,
        "saved_candidate_geometry_quality_uses_world_meters": True,
        "pose_inventory_geometry_topology_thresholds_candidates_unchanged": True,
    }:
        raise R20Error("Author Attempt-04 coordinate-space contract drifted")
    source_build = json.loads(paths["source_build_evidence"].read_text(encoding="utf-8"))
    source_matrix = source_build["immutable_component_verification"]["immutable_mesh_states"][
        BODY_NAME
    ]["matrix_world"]
    if source_matrix != attempt04_coordinate_contract["body_matrix_world"]:
        raise R20Error("R19 source matrix evidence drifted from Attempt-04 contract")
    passed_preflight = json.loads(
        paths["passed_preflight_attempt_04_evidence"].read_text(encoding="utf-8")
    )
    serialized_local = passed_preflight["mask"]["canonical_seam_local_coordinates"]
    serialized_world = passed_preflight["mask"]["canonical_seam_world_coordinates"]
    if not math.isclose(
        patch_contract.closed_cycle_median_edge_scale(serialized_local),
        float(attempt04_coordinate_contract["preflight_serialized_local_median_edge_scale"]),
        rel_tol=0.0,
        abs_tol=1.0e-15,
    ):
        raise R20Error("serialized preflight local seam scale drifted")
    if not math.isclose(
        patch_contract.closed_cycle_median_edge_scale(serialized_world),
        float(attempt04_coordinate_contract["preflight_serialized_world_median_edge_scale_m"]),
        rel_tol=0.0,
        abs_tol=1.0e-15,
    ):
        raise R20Error("serialized preflight world seam scale drifted")
    source_manifest = json.loads(paths["source_package_manifest"].read_text(encoding="utf-8"))
    _manifest_member_paths(paths["source_package_manifest"], source_manifest)
    paths["preflight_output"] = resolve_project_path(str(config["preflight_output"]), must_exist=False)
    if project_relative(paths["preflight_output"]) != EXPECTED_PREFLIGHT_OUTPUT_REL:
        raise R20Error("Attempt-04 append-only preflight output drifted")
    paths["author_output"] = resolve_project_path(str(config["author_output"]), must_exist=False)
    if project_relative(paths["author_output"]) != EXPECTED_AUTHOR_OUTPUT_REL:
        raise R20Error("Author Attempt-04 append-only output drifted")
    return config, paths


def _matrix_digest(value: Any) -> str:
    return sha256_json(float_rows(value))


def mesh_geometry_uv_signature(obj: bpy.types.Object) -> str:
    """Exact historical R19 signature used by the sealed freeze ledger."""
    digest = hashlib.sha256()
    digest.update(canonical_blender_name(obj.data.name).encode("utf-8"))
    for vertex in obj.data.vertices:
        digest.update(
            (
                f"v:{vertex.index}:{float(vertex.co.x):.12g}:"
                f"{float(vertex.co.y):.12g}:{float(vertex.co.z):.12g};"
            ).encode("ascii")
        )
    for polygon in obj.data.polygons:
        digest.update(
            ("p:" + ",".join(str(int(index)) for index in polygon.vertices) + ";").encode("ascii")
        )
    for layer in obj.data.uv_layers:
        digest.update(f"uv:{layer.name};".encode("utf-8"))
        for entry in layer.data:
            digest.update(
                (f"{float(entry.uv.x):.12g},{float(entry.uv.y):.12g};").encode("ascii")
            )
    return digest.hexdigest()


def positive_weight_signature(obj: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    group_names = {int(group.index): group.name for group in obj.vertex_groups}
    for vertex in obj.data.vertices:
        digest.update(f"v:{int(vertex.index)};".encode("ascii"))
        assignments = sorted(
            (group_names[int(item.group)], float(item.weight))
            for item in vertex.groups
            if float(item.weight) > 0.0
        )
        for name, weight in assignments:
            digest.update(f"{name}:{weight:.12g};".encode("utf-8"))
    return digest.hexdigest()


def modifier_record(obj: bpy.types.Object) -> list[dict[str, Any]]:
    result = []
    for modifier in obj.modifiers:
        record: dict[str, Any] = {"name": modifier.name, "type": modifier.type}
        if modifier.type == "ARMATURE":
            record["object"] = modifier.object.name if modifier.object else None
            record["use_vertex_groups"] = bool(modifier.use_vertex_groups)
        result.append(record)
    return result


def rig_rest_signature(rig: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    for bone in sorted(rig.data.bones, key=lambda item: item.name):
        matrix_local = ",".join(
            f"{float(value):.12g}" for row in bone.matrix_local for value in row
        )
        digest.update(
            (
                f"{bone.name}|{bone.parent.name if bone.parent else ''}|"
                f"{float(bone.head_local.x):.12g},{float(bone.head_local.y):.12g},"
                f"{float(bone.head_local.z):.12g}|{float(bone.tail_local.x):.12g},"
                f"{float(bone.tail_local.y):.12g},{float(bone.tail_local.z):.12g}|"
                f"{matrix_local}|{int(bool(bone.use_deform))};"
            ).encode("utf-8")
        )
    return digest.hexdigest()


def action_digest() -> str:
    """Hash all action data without authoring or inserting a keyframe."""
    rows: list[dict[str, Any]] = []
    for action in sorted(bpy.data.actions, key=lambda item: item.name):
        row: dict[str, Any] = {
            "name": action.name,
            "frame_range": [float(value) for value in action.frame_range],
            "use_fake_user": bool(action.use_fake_user),
            "legacy_fcurves": [],
            "slots": [],
            "layers": [],
        }
        curves = getattr(action, "fcurves", ())
        for curve in sorted(curves, key=lambda item: (item.data_path, int(item.array_index))):
            row["legacy_fcurves"].append(
                {
                    "data_path": curve.data_path,
                    "array_index": int(curve.array_index),
                    "keys": [
                        {
                            "co": [float(point.co.x), float(point.co.y)],
                            "left": [float(point.handle_left.x), float(point.handle_left.y)],
                            "right": [float(point.handle_right.x), float(point.handle_right.y)],
                            "interpolation": point.interpolation,
                        }
                        for point in curve.keyframe_points
                    ],
                }
            )
        for slot in getattr(action, "slots", ()):
            row["slots"].append(
                {
                    "identifier": str(getattr(slot, "identifier", "")),
                    "target_id_type": str(getattr(slot, "target_id_type", "")),
                }
            )
        for layer in getattr(action, "layers", ()):
            layer_row = {"name": layer.name, "strips": []}
            for strip in getattr(layer, "strips", ()):
                strip_row = {"type": type(strip).__name__, "channelbags": []}
                channelbags = getattr(strip, "channelbags", ())
                for channelbag in channelbags:
                    curve_rows = []
                    for curve in sorted(
                        getattr(channelbag, "fcurves", ()),
                        key=lambda item: (item.data_path, int(item.array_index)),
                    ):
                        curve_rows.append(
                            {
                                "data_path": curve.data_path,
                                "array_index": int(curve.array_index),
                                "keys": [
                                    [float(point.co.x), float(point.co.y), point.interpolation]
                                    for point in curve.keyframe_points
                                ],
                            }
                        )
                    strip_row["channelbags"].append(curve_rows)
                layer_row["strips"].append(strip_row)
            row["layers"].append(layer_row)
        rows.append(row)
    return sha256_json(rows)


def material_graph_digest() -> str:
    rows: list[dict[str, Any]] = []
    for material in sorted(bpy.data.materials, key=lambda item: item.name):
        row: dict[str, Any] = {
            "name": material.name,
            "diffuse_color": [float(value) for value in material.diffuse_color],
            "use_nodes": bool(material.use_nodes),
            "nodes": [],
            "links": [],
        }
        tree = material.node_tree
        if tree is not None:
            for node in sorted(tree.nodes, key=lambda item: item.name):
                inputs = []
                for socket in node.inputs:
                    default = getattr(socket, "default_value", None)
                    try:
                        default_value = [float(value) for value in default]
                    except (TypeError, ValueError):
                        default_value = float(default) if isinstance(default, (int, float)) else None
                    inputs.append({"name": socket.name, "default": default_value})
                row["nodes"].append(
                    {
                        "name": node.name,
                        "type": node.bl_idname,
                        "label": node.label,
                        "image": getattr(getattr(node, "image", None), "name", None),
                        "inputs": inputs,
                    }
                )
            row["links"] = sorted(
                (
                    link.from_node.name,
                    link.from_socket.name,
                    link.to_node.name,
                    link.to_socket.name,
                )
                for link in tree.links
            )
        rows.append(row)
    return sha256_json(rows)


def _find_scene_components(config: Mapping[str, Any]) -> tuple[bpy.types.Object, bpy.types.Object]:
    body = bpy.data.objects.get(str(config["body_object"]))
    rig = bpy.data.objects.get(str(config["rig_object"]))
    if body is None or body.type != "MESH":
        raise R20Error("exact R19 primary-surface object is missing")
    if rig is None or rig.type != "ARMATURE" or len(rig.data.bones) != 188:
        raise R20Error("exact R19 native 188-joint armature is missing")
    if tuple((len(body.data.vertices), len(body.data.edges), len(body.data.polygons))) != EXPECTED_SOURCE_COUNTS:
        raise R20Error("R19 source primary-surface counts drifted")
    actual_material_slots = tuple(
        slot.material.name if slot.material is not None else None
        for slot in body.material_slots
    )
    if actual_material_slots != EXPECTED_R19_MATERIAL_SLOT_NAMES:
        raise R20Error(
            "R19 exact regional material-slot order drifted: "
            + json.dumps(
                {
                    "actual_material_slots": actual_material_slots,
                    "expected_material_slots": EXPECTED_R19_MATERIAL_SLOT_NAMES,
                    "corrected_patch_slot_zero_based": PATCH_MATERIAL_SLOT,
                },
                sort_keys=True,
            )
        )
    material = body.material_slots[PATCH_MATERIAL_SLOT].material
    if material is None or material.name != PATCH_MATERIAL_NAME:
        raise R20Error(
            "R19 exact regional material binding drifted after ordered-slot gate: "
            + json.dumps(
                {
                    "actual_material": material.name if material is not None else None,
                    "expected_material": PATCH_MATERIAL_NAME,
                    "slot_zero_based": PATCH_MATERIAL_SLOT,
                },
                sort_keys=True,
            )
        )
    if body.data.shape_keys is not None and len(body.data.shape_keys.key_blocks) > 1:
        raise R20Error("unplanned primary-surface shape keys make localized replacement ambiguous")
    return body, rig


def validate_freeze_ledger(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    freeze_path: Path,
    identity_correction_path: Path,
    *,
    require_source_primary_hashes: bool,
) -> dict[str, Any]:
    ledger = json.loads(freeze_path.read_text(encoding="utf-8"))
    correction = json.loads(identity_correction_path.read_text(encoding="utf-8"))
    if correction.get("diagnosis_id") != (
        "KIRA_R20_ATTEMPT02_FREEZE_IDENTITY_CORRECTION_FOR_ATTEMPT03"
    ):
        raise R20Error("Attempt-03 freeze-identity diagnosis ID drifted")
    if correction.get("sealed_source", {}).get("freeze_ledger_sha256") != FREEZE_SHA256:
        raise R20Error("Attempt-03 freeze correction no longer binds the sealed ledger")
    if correction.get("sealed_source", {}).get("blend_sha256") != SOURCE_BLEND_SHA256:
        raise R20Error("Attempt-03 freeze correction no longer binds the sealed Blend")
    if ledger.get("native_rig", {}).get("object") != rig.name:
        raise R20Error("freeze-ledger rig name drifted")
    actual_rig = rig_rest_signature(rig)
    if actual_rig != ledger["native_rig"]["rest_structure_sha256"]:
        raise R20Error("native rig rest structure changed")

    expected_records = ledger.get("separate_mesh_objects_required_exact", [])
    if len(expected_records) != 32:
        raise R20Error("historical freeze ledger no longer contains exactly 32 records")
    historical = correction.get("root_cause", {}).get(
        "sole_historical_nonpersisted_record"
    )
    historical_matches = [record for record in expected_records if record == historical]
    if len(historical_matches) != 1 or str(historical.get("object", "")) != "Icosphere":
        raise R20Error("exact historical nonpersisted Icosphere record drifted")
    persisted_records = [record for record in expected_records if record != historical]
    if len(persisted_records) != 31 or any(
        str(record.get("object", "")) == "Icosphere" for record in persisted_records
    ):
        raise R20Error("corrected persisted freeze-record set is not exact 31")

    def exact_bindings(key: str, expected_count: int) -> list[list[str]]:
        raw = correction.get(key)
        if not isinstance(raw, list) or len(raw) != expected_count:
            raise R20Error(f"Attempt-03 {key} count drifted")
        bindings: list[list[str]] = []
        for value in raw:
            if (
                not isinstance(value, list)
                or len(value) != 2
                or not all(isinstance(part, str) and part for part in value)
            ):
                raise R20Error(f"Attempt-03 {key} contains an invalid exact binding")
            bindings.append([value[0], value[1]])
        if len({value[0] for value in bindings}) != expected_count:
            raise R20Error(f"Attempt-03 {key} contains duplicate object IDs")
        if bindings != sorted(bindings):
            raise R20Error(f"Attempt-03 {key} is not in sealed exact-object order")
        return bindings

    expected_protected = exact_bindings(
        "expected_protected_object_to_mesh_bindings", 32
    )
    expected_review_context = exact_bindings(
        "expected_review_context_object_to_mesh_bindings", 15
    )
    expected_primary = [body.name, body.data.name]
    if expected_primary not in expected_protected:
        raise R20Error("corrected protected inventory does not bind the exact primary surface")
    persisted_ledger_bindings = sorted(
        [[str(record["object"]), str(record["mesh"])] for record in persisted_records]
    )
    corrected_separate_bindings = sorted(
        binding for binding in expected_protected if binding[0] != body.name
    )
    if persisted_ledger_bindings != corrected_separate_bindings:
        raise R20Error("corrected persisted binding set differs from the historical ledger")

    actual_protected = sorted(
        [obj.name, obj.data.name]
        for obj in bpy.data.objects
        if obj.type == "MESH" and not bool(obj.get("review_context_prop_only"))
    )
    actual_review_context = sorted(
        [obj.name, obj.data.name]
        for obj in bpy.data.objects
        if obj.type == "MESH" and bool(obj.get("review_context_prop_only"))
    )

    def inventory_differences(
        expected: Sequence[Sequence[str]], actual: Sequence[Sequence[str]]
    ) -> dict[str, Any]:
        expected_by_object = {value[0]: value[1] for value in expected}
        actual_by_object = {value[0]: value[1] for value in actual}
        common = sorted(set(expected_by_object) & set(actual_by_object))
        return {
            "expected_count": len(expected),
            "actual_count": len(actual),
            "missing_objects": sorted(set(expected_by_object) - set(actual_by_object)),
            "extra_objects": sorted(set(actual_by_object) - set(expected_by_object)),
            "mesh_binding_mismatches": [
                {
                    "object": name,
                    "expected_mesh": expected_by_object[name],
                    "actual_mesh": actual_by_object[name],
                }
                for name in common
                if expected_by_object[name] != actual_by_object[name]
            ],
        }

    protected_differences = inventory_differences(expected_protected, actual_protected)
    review_differences = inventory_differences(
        expected_review_context, actual_review_context
    )
    if actual_protected != expected_protected or actual_review_context != expected_review_context:
        raise R20Error(
            "whole exact source mesh inventory changed: "
            + json.dumps(
                {
                    "protected": protected_differences,
                    "review_context": review_differences,
                    "actual_protected_bindings": actual_protected,
                    "actual_review_context_bindings": actual_review_context,
                },
                sort_keys=True,
            )
        )

    separate: list[dict[str, Any]] = []
    for expected in persisted_records:
        obj = bpy.data.objects.get(str(expected["object"]))
        if obj is None or obj.type != "MESH":
            raise R20Error(
                f"persisted frozen separate mesh object missing: {expected['object']}"
            )
        actual = {
            "object": obj.name,
            "mesh": canonical_blender_name(obj.data.name),
            "vertices": len(obj.data.vertices),
            "faces": len(obj.data.polygons),
            "geometry_uv_sha256": mesh_geometry_uv_signature(obj),
            "positive_weight_assignment_sha256": positive_weight_signature(obj),
            "matrix_world_sha256": _matrix_digest(obj.matrix_world),
            "modifiers": modifier_record(obj),
        }
        for key in (
            "mesh",
            "vertices",
            "faces",
            "geometry_uv_sha256",
            "positive_weight_assignment_sha256",
        ):
            if actual[key] != expected[key]:
                raise R20Error(f"frozen object {obj.name} changed at {key}")
        separate.append(actual)
    primary = ledger["primary_surface"]
    if require_source_primary_hashes:
        if mesh_geometry_uv_signature(body) != primary["current_geometry_uv_sha256"]:
            raise R20Error("R19 source primary geometry/UV hash drifted")
        if positive_weight_signature(body) != primary["current_positive_weight_assignment_sha256"]:
            raise R20Error("R19 source primary weight hash drifted")
    return {
        "native_rig_rest_structure_sha256": actual_rig,
        "historical_freeze_ledger_record_count": len(expected_records),
        "historical_nonpersisted_record": historical,
        "historical_nonpersisted_record_count": 1,
        "protected_component_count_including_primary": len(actual_protected),
        "separate_mesh_count": len(separate),
        "separate_mesh_records_sha256": sha256_json(separate),
        "all_separate_meshes_exact": True,
        "review_context_mesh_count": len(actual_review_context),
        "protected_object_to_mesh_bindings": actual_protected,
        "protected_object_to_mesh_bindings_sha256": sha256_json(actual_protected),
        "review_context_object_to_mesh_bindings": actual_review_context,
        "review_context_object_to_mesh_bindings_sha256": sha256_json(
            actual_review_context
        ),
        "whole_exact_source_mesh_inventory_passed": True,
        "missing_protected_objects": [],
        "extra_protected_objects": [],
        "protected_mesh_binding_mismatches": [],
        "missing_review_context_objects": [],
        "extra_review_context_objects": [],
        "review_context_mesh_binding_mismatches": [],
        "loose_object_matching_used": False,
        "source_primary_hashes_required": require_source_primary_hashes,
    }


def _face_connected_components(mesh: bpy.types.Mesh, selected: set[int]) -> int:
    by_edge: defaultdict[tuple[int, int], list[int]] = defaultdict(list)
    for polygon in mesh.polygons:
        if int(polygon.index) not in selected:
            continue
        vertices = [int(value) for value in polygon.vertices]
        for first, second in zip(vertices, vertices[1:] + vertices[:1]):
            by_edge[tuple(sorted((first, second)))].append(int(polygon.index))
    adjacency: defaultdict[int, set[int]] = defaultdict(set)
    for faces in by_edge.values():
        for first in faces:
            adjacency[first].update(second for second in faces if second != first)
    components = 0
    unseen = set(selected)
    while unseen:
        components += 1
        queue = [unseen.pop()]
        while queue:
            current = queue.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
    return components


def _walk_cycle(graph: Mapping[int, set[int]]) -> list[int]:
    if len(graph) != patch_contract.SEAM_COUNT or any(len(values) != 2 for values in graph.values()):
        raise R20Error("interface graph is not one 34-vertex degree-two cycle")
    start = next(iter(graph))
    order = [start]
    previous = None
    current = start
    while True:
        choices = sorted(value for value in graph[current] if value != previous)
        if not choices:
            raise R20Error("interface cycle terminated early")
        following = choices[0]
        if following == start:
            break
        if following in order:
            raise R20Error("interface graph contains a short subcycle")
        order.append(following)
        previous, current = current, following
    if len(order) != patch_contract.SEAM_COUNT:
        raise R20Error("interface graph did not form one complete cycle")
    return order


def _bijective_coordinate_set_match(
    actual_points: Sequence[Sequence[float]],
    licensed_records: Sequence[Mapping[str, Any]],
    *,
    tolerance_m: float,
) -> dict[str, Any]:
    """Match an actual world-space interface to licensed points as a set.

    The historical probe serialized a breadth-first component visitation under
    a misleading ordered-cycle field.  Its row order therefore has no
    topological meaning.  The sealed R19 mesh is the sole cycle-order
    authority; the full-precision adult-to-base records are only the licensed
    coordinate-set authority.
    """

    if len(actual_points) != patch_contract.SEAM_COUNT or len(licensed_records) != patch_contract.SEAM_COUNT:
        raise R20Error("licensed interface match requires exactly 34 actual and 34 source points")
    source_points: list[tuple[float, float, float]] = []
    for source_index, record in enumerate(licensed_records):
        adult = tuple(float(value) for value in record.get("adult_world", ()))
        base = tuple(float(value) for value in record.get("base_world", ()))
        if len(adult) != 3 or len(base) != 3:
            raise R20Error(f"licensed interface record {source_index} lacks full-precision world coordinates")
        if float(record.get("distance_m", math.inf)) != 0.0 or adult != base:
            raise R20Error(f"licensed adult/base zero-distance record drifted at index {source_index}")
        source_points.append(base)

    possible_by_actual: dict[int, list[tuple[float, int]]] = {}
    possible_by_source: defaultdict[int, list[tuple[float, int]]] = defaultdict(list)
    for actual_index, actual in enumerate(actual_points):
        candidates = []
        for source_index, source in enumerate(source_points):
            distance = math.dist(actual, source)
            if distance <= tolerance_m:
                candidates.append((distance, source_index))
                possible_by_source[source_index].append((distance, actual_index))
        possible_by_actual[actual_index] = sorted(candidates)
    ambiguous_actual = {
        index: values for index, values in possible_by_actual.items() if len(values) != 1
    }
    ambiguous_source = {
        index: values
        for index, values in possible_by_source.items()
        if len(values) != 1
    }
    missing_source = sorted(set(range(len(source_points))) - set(possible_by_source))
    if ambiguous_actual or ambiguous_source or missing_source:
        raise R20Error(
            "R19 seam does not have one unique licensed coordinate per actual/source point: "
            + json.dumps(
                {
                    "ambiguous_actual": ambiguous_actual,
                    "ambiguous_source": ambiguous_source,
                    "missing_source": missing_source,
                    "tolerance_m": tolerance_m,
                },
                sort_keys=True,
            )
        )
    matches = []
    for actual_index in range(len(actual_points)):
        distance, source_index = possible_by_actual[actual_index][0]
        record = licensed_records[source_index]
        matches.append(
            {
                "actual_cycle_index": actual_index,
                "licensed_record_index": source_index,
                "licensed_adult_vertex": int(record["adult_vertex"]),
                "licensed_base_vertex": int(record["base_vertex"]),
                "distance_m": distance,
            }
        )
    maximum = max(float(record["distance_m"]) for record in matches)
    return {
        "status": "PASS",
        "actual_count": len(actual_points),
        "licensed_count": len(source_points),
        "tolerance_m": tolerance_m,
        "maximum_distance_m": maximum,
        "unique_bijective_assignment": True,
        "actual_cycle_order_authority": "sealed R19 topology edge walk",
        "licensed_coordinate_authority": "full-precision adult_boundary_to_base_vertices.base_world set",
        "licensed_record_order_used_as_adjacency": False,
        "matches": matches,
        "matches_sha256": sha256_json(matches),
    }


def derive_exact_mask(body: bpy.types.Object, interface_path: Path) -> dict[str, Any]:
    mesh = body.data
    selected = {
        int(polygon.index)
        for polygon in mesh.polygons
        if int(polygon.material_index) == PATCH_MATERIAL_SLOT
    }
    if len(selected) != 376 or _face_connected_components(mesh, selected) != 1:
        raise R20Error("exact old patch selector is not 376 faces in one component")
    pure_mask = patch_contract.mask_topology_contract(
        [tuple(int(vertex) for vertex in polygon.vertices) for polygon in mesh.polygons],
        selected,
    )
    incident = {
        int(vertex)
        for face_index in selected
        for vertex in mesh.polygons[face_index].vertices
    }
    if len(incident) != 206:
        raise R20Error("exact old patch must have 206 incident vertices")
    edge_faces: defaultdict[tuple[int, int], list[int]] = defaultdict(list)
    for polygon in mesh.polygons:
        values = [int(vertex) for vertex in polygon.vertices]
        for first, second in zip(values, values[1:] + values[:1]):
            edge_faces[tuple(sorted((first, second)))].append(int(polygon.index))
    interface_edges = []
    for edge, face_indices in edge_faces.items():
        selected_count = sum(index in selected for index in face_indices)
        if selected_count and selected_count != len(face_indices):
            if len(face_indices) != 2 or selected_count != 1:
                raise R20Error("patch interface edge does not have exactly one face per side")
            interface_edges.append(edge)
    if len(interface_edges) != 34:
        raise R20Error(f"exact patch must have 34 interface edges, found {len(interface_edges)}")
    graph: defaultdict[int, set[int]] = defaultdict(set)
    for first, second in interface_edges:
        graph[first].add(second)
        graph[second].add(first)
    raw_cycle = _walk_cycle(graph)
    world_points = [body.matrix_world @ mesh.vertices[index].co for index in raw_cycle]
    canonical_points, order = patch_contract.canonicalize_cycle(
        [tuple(float(value) for value in point) for point in world_points]
    )
    seam_indices = [raw_cycle[index] for index in order]
    local_points = [tuple(float(value) for value in mesh.vertices[index].co) for index in seam_indices]
    evidence = json.loads(interface_path.read_text(encoding="utf-8"))
    licensed = evidence.get("adult_boundary_to_base_vertices", {})
    licensed_records = licensed.get("records", [])
    if (
        int(licensed.get("count_under_1e_8_m", -1)) != patch_contract.SEAM_COUNT
        or float(licensed.get("minimum_m", math.inf)) != 0.0
        or float(licensed.get("maximum_m", math.inf)) != 0.0
    ):
        raise R20Error("licensed adult-to-base interface summary drifted")
    licensed_set_match = _bijective_coordinate_set_match(
        canonical_points,
        licensed_records,
        tolerance_m=1.0e-8,
    )
    interface_vertices = set(seam_indices)
    interior = incident - interface_vertices
    if len(interior) != 172:
        raise R20Error("exact patch must expose 172 removable interior vertices")
    expected_pure_mask = {
        "selected_face_count": 376,
        "selected_face_connected_components": 1,
        "incident_vertex_count": 206,
        "interface_edge_count": 34,
        "interface_vertex_count": 34,
        "interface_degree_two": True,
        "interface_connected_components": 1,
        "removable_interior_vertex_count": 172,
    }
    if any(pure_mask.get(key) != value for key, value in expected_pure_mask.items()):
        raise R20Error(f"pure mask topology contract failed: {pure_mask}")
    unselected_references = {
        int(vertex)
        for polygon in mesh.polygons
        if int(polygon.index) not in selected
        for vertex in polygon.vertices
    }
    if interior.intersection(unselected_references):
        raise R20Error("a supposedly removable interior vertex is referenced by a preserved face")
    bounds_low = Vector((math.inf, math.inf, math.inf))
    bounds_high = Vector((-math.inf, -math.inf, -math.inf))
    for index in incident:
        point = body.matrix_world @ mesh.vertices[index].co
        for axis in range(3):
            bounds_low[axis] = min(bounds_low[axis], point[axis])
            bounds_high[axis] = max(bounds_high[axis], point[axis])
    allowed_low = Vector((-0.054620426, -0.09303198, 0.823473752))
    allowed_high = Vector((0.05467169, 0.060616653, 0.918649852))
    tolerance = 1.0e-8
    if any(bounds_low[axis] < allowed_low[axis] - tolerance for axis in range(3)) or any(
        bounds_high[axis] > allowed_high[axis] + tolerance for axis in range(3)
    ):
        raise R20Error("selected old patch bounds escape the sealed interface envelope")
    return {
        "selected_face_ids": sorted(selected),
        "pure_mask_topology_contract": pure_mask,
        "incident_vertex_ids": sorted(incident),
        "removable_interior_vertex_ids": sorted(interior),
        "interface_edge_ids": [list(edge) for edge in sorted(interface_edges)],
        "canonical_seam_vertex_ids": seam_indices,
        "canonical_seam_local_coordinates": [vector_record(value) for value in local_points],
        "canonical_seam_world_coordinates": [vector_record(value) for value in canonical_points],
        "licensed_coordinate_set_match": licensed_set_match,
        "maximum_interface_delta_m": licensed_set_match["maximum_distance_m"],
        "historical_ordered_boundary_field_used_as_adjacency": False,
        "selected_bounds_world_m": {
            "minimum": vector_record(bounds_low),
            "maximum": vector_record(bounds_high),
        },
        "selected_face_ids_sha256": sha256_json(sorted(selected)),
        "incident_vertex_ids_sha256": sha256_json(sorted(incident)),
        "removable_vertex_ids_sha256": sha256_json(sorted(interior)),
        "canonical_seam_sha256": sha256_json(
            {"ids": seam_indices, "world": [vector_record(value) for value in canonical_points]}
        ),
    }


def _coordinate_key(value: Sequence[float]) -> str:
    return struct.pack("<3d", *(float(component) for component in value)).hex()


def _cycle_rotation(values: Sequence[Any]) -> tuple[Any, ...]:
    rows = tuple(values)
    if not rows:
        return ()
    rotations = [rows[index:] + rows[:index] for index in range(len(rows))]
    return min(
        rotations,
        key=lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")),
    )


def _corner_normal(mesh: bpy.types.Mesh, loop_index: int) -> tuple[float, float, float]:
    corner_normals = getattr(mesh, "corner_normals", None)
    if corner_normals is not None and len(corner_normals) == len(mesh.loops):
        value = corner_normals[loop_index].vector
    else:
        value = mesh.loops[loop_index].normal
    return tuple(float(component) for component in value)


def _supported_attribute_inventory(mesh: bpy.types.Mesh) -> list[dict[str, Any]]:
    """Inventory attributes and fail closed on unplanned author data.

    BMesh preserves built-in topology, selection, sharpness and every UV layer.
    R20 adds only named POINT/BOOLEAN landmark hooks after the edit.  The four
    source attributes listed in ``PLANNED_SURVIVING_ATTRIBUTE_RULES`` have
    explicit, localized rules.  Any other source attribute fails closed.
    """

    uv_names = {layer.name for layer in mesh.uv_layers}
    builtins = {
        "position",
        ".edge_verts",
        ".corner_vert",
        ".corner_edge",
        ".select_vert",
        ".select_edge",
        ".select_poly",
        "sharp_edge",
        "sharp_face",
        "material_index",
    }
    inventory = []
    unsupported = []
    planned_seen: set[str] = set()
    for attribute in mesh.attributes:
        record = {
            "name": attribute.name,
            "domain": str(attribute.domain),
            "data_type": str(attribute.data_type),
            "length": len(attribute.data),
        }
        inventory.append(record)
        if attribute.name in PLANNED_SURVIVING_ATTRIBUTE_RULES:
            planned_seen.add(attribute.name)
            rule = PLANNED_SURVIVING_ATTRIBUTE_RULES[attribute.name]
            if record["domain"] != rule["domain"] or record["data_type"] != rule["data_type"]:
                unsupported.append({**record, "reason": "planned descriptor mismatch", "rule": rule})
        elif (
            attribute.name not in builtins
            and attribute.name not in uv_names
            and not attribute.name.startswith(LANDMARK_ATTRIBUTE_PREFIX)
        ):
            unsupported.append(record)
    missing_planned = sorted(set(PLANNED_SURVIVING_ATTRIBUTE_RULES) - planned_seen)
    if unsupported or missing_planned:
        raise R20Error(
            "source primary surface has attributes without an authorized localized rule: "
            + json.dumps(
                {"unsupported_or_mismatched": unsupported, "missing_planned": missing_planned},
                sort_keys=True,
            )
        )
    return inventory


def _planned_attribute(mesh: bpy.types.Mesh, name: str) -> Any:
    attribute = mesh.attributes.get(name)
    rule = PLANNED_SURVIVING_ATTRIBUTE_RULES[name]
    if attribute is None:
        raise R20Error(f"planned source attribute disappeared: {name}")
    if str(attribute.domain) != rule["domain"] or str(attribute.data_type) != rule["data_type"]:
        raise R20Error(
            f"planned source attribute descriptor drifted for {name}: "
            f"{attribute.domain}/{attribute.data_type}"
        )
    return attribute


def _read_planned_attribute_value(attribute: Any, index: int) -> Any:
    entry = attribute.data[int(index)]
    value = getattr(entry, "value", None)
    if value is None:
        raise R20Error(
            f"Blender RNA does not expose a writable value for {attribute.name}/{attribute.data_type}"
        )
    if str(attribute.data_type) == "INT16_2D":
        values = tuple(int(component) for component in value)
        if len(values) != 2 or any(component < -32768 or component > 32767 for component in values):
            raise R20Error(f"invalid INT16_2D value on {attribute.name}: {values}")
        return list(values)
    if str(attribute.data_type) == "BOOLEAN":
        return bool(value)
    raise R20Error(f"unimplemented planned attribute value type: {attribute.data_type}")


def _write_planned_attribute_value(attribute: Any, index: int, value: Any) -> None:
    if str(attribute.data_type) == "INT16_2D":
        encoded = tuple(int(component) for component in value)
        if len(encoded) != 2 or any(component < -32768 or component > 32767 for component in encoded):
            raise R20Error(f"invalid INT16_2D restore value on {attribute.name}: {encoded}")
        attribute.data[int(index)].value = encoded
        return
    if str(attribute.data_type) == "BOOLEAN":
        attribute.data[int(index)].value = bool(value)
        return
    raise R20Error(f"unimplemented planned attribute write type: {attribute.data_type}")


def _canonical_face_record(
    mesh: bpy.types.Mesh,
    polygon: bpy.types.MeshPolygon,
    *,
    include_corner_data: bool,
    include_decoded_normals: bool = False,
) -> dict[str, Any]:
    coords = [_coordinate_key(mesh.vertices[int(index)].co) for index in polygon.vertices]
    loop_indices = list(range(int(polygon.loop_start), int(polygon.loop_start + polygon.loop_total)))
    corners: list[dict[str, Any]] = []
    for local_index, loop_index in enumerate(loop_indices):
        corner: dict[str, Any] = {"coordinate": coords[local_index]}
        if include_corner_data:
            corner["uv"] = {
                layer.name: [float(value) for value in layer.data[loop_index].uv]
                for layer in mesh.uv_layers
            }
            corner["planned_attributes"] = {
                name: _read_planned_attribute_value(_planned_attribute(mesh, name), loop_index)
                for name in (CUSTOM_NORMAL_NAME, *UV_SELECTION_CORNER_NAMES)
            }
            if include_decoded_normals:
                corner["decoded_normal"] = list(_corner_normal(mesh, loop_index))
        corners.append(corner)
    rotated = _cycle_rotation(corners)
    record = {
        "corners": rotated,
        "material_index": int(polygon.material_index),
        "use_smooth": bool(polygon.use_smooth),
        "select": bool(polygon.select),
    }
    if include_corner_data:
        record["planned_face_attributes"] = {
            UV_SELECTION_FACE_NAME: _read_planned_attribute_value(
                _planned_attribute(mesh, UV_SELECTION_FACE_NAME), int(polygon.index)
            )
        }
    return record


def _patch_interface_vertex_ids(mesh: bpy.types.Mesh) -> set[int]:
    patch_vertices = {
        int(index)
        for polygon in mesh.polygons
        if int(polygon.material_index) == PATCH_MATERIAL_SLOT
        for index in polygon.vertices
    }
    preserved_vertices = {
        int(index)
        for polygon in mesh.polygons
        if int(polygon.material_index) != PATCH_MATERIAL_SLOT
        for index in polygon.vertices
    }
    interface = patch_vertices.intersection(preserved_vertices)
    if len(interface) != patch_contract.SEAM_COUNT:
        raise R20Error(f"primary-surface patch interface vertex count drifted: {len(interface)}")
    return interface


def _preserved_attribute_hashes(
    mesh: bpy.types.Mesh,
    preserved_faces: Sequence[bpy.types.MeshPolygon],
) -> dict[str, Any]:
    records: dict[str, list[dict[str, Any]]] = {
        name: [] for name in PLANNED_SURVIVING_ATTRIBUTE_RULES
    }
    for polygon in preserved_faces:
        face_identity = sha256_json(
            _canonical_face_record(mesh, polygon, include_corner_data=False)
        )
        face_attribute = _planned_attribute(mesh, UV_SELECTION_FACE_NAME)
        records[UV_SELECTION_FACE_NAME].append(
            {
                "face_identity": face_identity,
                "value": _read_planned_attribute_value(face_attribute, int(polygon.index)),
            }
        )
        for loop_index in range(int(polygon.loop_start), int(polygon.loop_start + polygon.loop_total)):
            vertex_index = int(mesh.loops[loop_index].vertex_index)
            coordinate = _coordinate_key(mesh.vertices[vertex_index].co)
            for name in (CUSTOM_NORMAL_NAME, *UV_SELECTION_CORNER_NAMES):
                records[name].append(
                    {
                        "face_identity": face_identity,
                        "coordinate": coordinate,
                        "value": _read_planned_attribute_value(
                            _planned_attribute(mesh, name), loop_index
                        ),
                    }
                )
    return {
        name: {
            "domain": PLANNED_SURVIVING_ATTRIBUTE_RULES[name]["domain"],
            "data_type": PLANNED_SURVIVING_ATTRIBUTE_RULES[name]["data_type"],
            "surviving_element_count": len(values),
            "surviving_elements_sha256": sha256_json(
                sorted(values, key=lambda value: json.dumps(value, sort_keys=True))
            ),
            "surviving_rule": PLANNED_SURVIVING_ATTRIBUTE_RULES[name]["surviving_rule"],
            "new_patch_rule": PLANNED_SURVIVING_ATTRIBUTE_RULES[name]["new_patch_rule"],
        }
        for name, values in records.items()
    }


def preserved_primary_snapshot(body: bpy.types.Object) -> dict[str, Any]:
    """Canonical exact snapshot of every surface element outside slot 1.

    Numeric indices are intentionally absent.  A local BMesh edit may reindex
    elements, while exact coordinates, winding, weights, UVs and every raw
    surviving planned attribute value remain the preservation authority.
    Decoded custom normals are topology-dependent in Blender's short2 normal
    space, so the complete hash includes decoded values only outside the local
    seam fan.  The seam fan is checked separately by the localized normal gate.
    """

    mesh = body.data
    _supported_attribute_inventory(mesh)
    preserved_faces = [
        polygon for polygon in mesh.polygons if int(polygon.material_index) != PATCH_MATERIAL_SLOT
    ]
    interface_vertices = _patch_interface_vertex_ids(mesh)
    preserved_vertex_ids = {
        int(index) for polygon in preserved_faces for index in polygon.vertices
    }
    group_names = {int(group.index): group.name for group in body.vertex_groups}
    vertex_records = []
    for index in preserved_vertex_ids:
        vertex = mesh.vertices[index]
        vertex_records.append(
            {
                "coordinate": _coordinate_key(vertex.co),
                "select": bool(vertex.select),
                "weights": sorted(
                    (group_names[int(item.group)], float(item.weight))
                    for item in vertex.groups
                    if float(item.weight) > 0.0
                ),
            }
        )
    face_records = [
        _canonical_face_record(
            mesh,
            polygon,
            include_corner_data=True,
            include_decoded_normals=False,
        )
        for polygon in preserved_faces
    ]
    noninterface_decoded_normals = []
    interface_decoded_loop_count = 0
    for polygon in preserved_faces:
        face_identity = sha256_json(
            _canonical_face_record(mesh, polygon, include_corner_data=False)
        )
        for loop_index in range(int(polygon.loop_start), int(polygon.loop_start + polygon.loop_total)):
            vertex_index = int(mesh.loops[loop_index].vertex_index)
            if vertex_index in interface_vertices:
                interface_decoded_loop_count += 1
                continue
            noninterface_decoded_normals.append(
                {
                    "face_identity": face_identity,
                    "coordinate": _coordinate_key(mesh.vertices[vertex_index].co),
                    "decoded_normal": list(_corner_normal(mesh, loop_index)),
                }
            )
    preserved_edges: dict[tuple[str, str], dict[str, Any]] = {}
    for polygon in preserved_faces:
        for loop_index in range(int(polygon.loop_start), int(polygon.loop_start + polygon.loop_total)):
            edge_index = int(mesh.loops[loop_index].edge_index)
            edge = mesh.edges[edge_index]
            first, second = (int(value) for value in edge.vertices)
            key = tuple(
                sorted(
                    (
                        _coordinate_key(mesh.vertices[first].co),
                        _coordinate_key(mesh.vertices[second].co),
                    )
                )
            )
            record = {
                "coordinates": key,
                "select": bool(edge.select),
                "use_edge_sharp": bool(edge.use_edge_sharp),
            }
            if key in preserved_edges and preserved_edges[key] != record:
                raise R20Error("preserved edge attribute record is ambiguous")
            preserved_edges[key] = record
    result = {
        "preserved_vertex_count": len(preserved_vertex_ids),
        "preserved_face_count": len(preserved_faces),
        "preserved_edge_count": len(preserved_edges),
        "vertices_sha256": sha256_json(sorted(vertex_records, key=lambda value: json.dumps(value, sort_keys=True))),
        "faces_sha256": sha256_json(sorted(face_records, key=lambda value: json.dumps(value, sort_keys=True))),
        "edges_sha256": sha256_json(
            sorted(preserved_edges.values(), key=lambda value: json.dumps(value, sort_keys=True))
        ),
        "matrix_world_sha256": _matrix_digest(body.matrix_world),
        "modifiers_sha256": sha256_json(modifier_record(body)),
        "material_slots": [slot.material.name if slot.material else "" for slot in body.material_slots],
        "attribute_descriptors": sorted(
            {
                (str(record["name"]), str(record["domain"]), str(record["data_type"]))
                for record in _supported_attribute_inventory(mesh)
                if not str(record["name"]).startswith(LANDMARK_ATTRIBUTE_PREFIX)
            }
        ),
        "planned_surviving_attribute_hashes": _preserved_attribute_hashes(
            mesh, preserved_faces
        ),
        "decoded_normal_zones": {
            "noninterface_loop_count": len(noninterface_decoded_normals),
            "noninterface_values_sha256": sha256_json(
                sorted(
                    noninterface_decoded_normals,
                    key=lambda value: json.dumps(value, sort_keys=True),
                )
            ),
            "interface_loop_count": interface_decoded_loop_count,
            "noninterface_rule": "exact decoded corner-normal values; no global normal drift",
            "interface_rule": "raw short2 exact plus bounded localized decoded continuity gate",
        },
        "normal_capture": "raw short2 exact everywhere; decoded exact outside the 34-vertex seam fan",
    }
    result["complete_snapshot_sha256"] = sha256_json(result)
    return result


def _vertex_neighbors(mesh: bpy.types.Mesh) -> dict[int, set[int]]:
    result: defaultdict[int, set[int]] = defaultdict(set)
    for edge in mesh.edges:
        first, second = (int(value) for value in edge.vertices)
        result[first].add(second)
        result[second].add(first)
    return result


def derive_exterior_rings_and_normals(
    body: bpy.types.Object,
    mask: Mapping[str, Any],
) -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]], list[tuple[float, float, float]], dict[str, Any]]:
    mesh = body.data
    selected = set(int(value) for value in mask["selected_face_ids"])
    seam = [int(value) for value in mask["canonical_seam_vertex_ids"]]
    seam_set = set(seam)
    incident_unselected: defaultdict[int, list[bpy.types.MeshPolygon]] = defaultdict(list)
    unselected_neighbors: defaultdict[int, set[int]] = defaultdict(set)
    for polygon in mesh.polygons:
        if int(polygon.index) in selected:
            continue
        for vertex in polygon.vertices:
            incident_unselected[int(vertex)].append(polygon)
        values = [int(vertex) for vertex in polygon.vertices]
        for first_vertex, second_vertex in zip(values, values[1:] + values[:1]):
            unselected_neighbors[first_vertex].add(second_vertex)
            unselected_neighbors[second_vertex].add(first_vertex)
    first_records: list[tuple[float, float, float]] = []
    second_records: list[tuple[float, float, float]] = []
    normal_records: list[tuple[float, float, float]] = []
    evidence = []
    for seam_index in seam:
        first_ids = sorted(unselected_neighbors[seam_index] - seam_set)
        if not first_ids:
            raise R20Error(f"seam vertex {seam_index} lacks a first preserved exterior ring")
        second_ids = sorted(
            {
                neighbor
                for first in first_ids
                for neighbor in unselected_neighbors[first]
                if neighbor not in seam_set and neighbor not in first_ids and neighbor != seam_index
            }
        )
        if not second_ids:
            raise R20Error(f"seam vertex {seam_index} lacks a second preserved exterior ring")
        first = sum((mesh.vertices[index].co for index in first_ids), Vector()) / len(first_ids)
        second = sum((mesh.vertices[index].co for index in second_ids), Vector()) / len(second_ids)
        faces = incident_unselected[seam_index]
        if not faces:
            raise R20Error(f"seam vertex {seam_index} lacks an unselected exterior face")
        normal = sum((polygon.normal for polygon in faces), Vector()).normalized()
        first_records.append(tuple(float(value) for value in first))
        second_records.append(tuple(float(value) for value in second))
        normal_records.append(tuple(float(value) for value in normal))
        evidence.append(
            {
                "seam_vertex": seam_index,
                "first_ring_source_vertices": first_ids,
                "second_ring_source_vertices": second_ids,
                "exterior_face_ids": sorted(int(face.index) for face in faces),
            }
        )
    return first_records, second_records, normal_records, {
        "method": "deterministic means of first two unselected edge rings plus area-independent exterior face normals",
        "records": evidence,
        "records_sha256": sha256_json(evidence),
    }


def _project_meter_coordinate_inputs(
    body: bpy.types.Object,
    mask: Mapping[str, Any],
    sealed_preflight_mask: Mapping[str, Any],
    first_exterior_ring_local: Sequence[Sequence[float]],
    second_exterior_ring_local: Sequence[Sequence[float]],
    exterior_ring_evidence: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind the exact source affine transform and produce meter-space inputs."""

    matrix_rows = float_rows(body.matrix_world)
    if _matrix_digest(body.matrix_world) != contract["body_matrix_world_sha256"]:
        raise R20Error("live body matrix digest drifted from the sealed R19 transform")
    if matrix_rows != contract["body_matrix_world"]:
        raise R20Error("live body matrix rows drifted from the exact R19 transform")
    try:
        inverse_rows, normal_rows, affine_evidence = (
            patch_contract.positive_affine_transform_matrices(matrix_rows)
        )
    except ValueError as exc:
        raise R20Error(f"unsupported body affine transform: {exc}") from exc

    seam_ids = [int(value) for value in mask["canonical_seam_vertex_ids"]]
    sealed_seam_ids = [
        int(value) for value in sealed_preflight_mask["canonical_seam_vertex_ids"]
    ]
    if seam_ids != sealed_seam_ids:
        raise R20Error("live canonical seam IDs drifted from immutable passed preflight")
    seam_local = tuple(
        tuple(float(value) for value in body.data.vertices[index].co) for index in seam_ids
    )
    if len(seam_local) != patch_contract.SEAM_COUNT:
        raise R20Error("live canonical seam count drifted")
    serialized_local = sealed_preflight_mask["canonical_seam_local_coordinates"]
    local_crosscheck_delta = max(
        math.dist(actual, recorded) for actual, recorded in zip(seam_local, serialized_local)
    )
    if local_crosscheck_delta > 1.0e-8:
        raise R20Error(f"live local seam drifted from sealed preflight: {local_crosscheck_delta}")

    # Blender's live Matrix @ Vector path is authoritative for construction;
    # the 12-decimal serialized world coordinates are a cross-check only.
    seam_project_m = tuple(
        tuple(float(value) for value in (body.matrix_world @ Vector(point)))
        for point in seam_local
    )
    serialized_world = sealed_preflight_mask["canonical_seam_world_coordinates"]
    world_crosscheck_delta = max(
        math.dist(actual, recorded) for actual, recorded in zip(seam_project_m, serialized_world)
    )
    if world_crosscheck_delta > float(contract["serialized_world_seam_crosscheck_tolerance_m"]):
        raise R20Error(
            f"live world seam drifted from sealed preflight: {world_crosscheck_delta}"
        )
    world_edge_scale = patch_contract.closed_cycle_median_edge_scale(seam_project_m)
    expected_world_edge_scale = float(
        contract["preflight_serialized_world_median_edge_scale_m"]
    )
    if not math.isclose(
        world_edge_scale,
        expected_world_edge_scale,
        rel_tol=0.0,
        abs_tol=float(contract["expected_world_median_absolute_tolerance_m"]),
    ):
        raise R20Error(
            "live project-meter seam scale drifted: "
            f"{world_edge_scale} != {expected_world_edge_scale}"
        )

    pure_roundtrip_delta = patch_contract.affine_roundtrip_maximum_delta(
        seam_local, matrix_rows, inverse_rows
    )
    if pure_roundtrip_delta > float(
        contract["maximum_seam_local_roundtrip_delta_local_units"]
    ):
        raise R20Error(f"affine seam roundtrip exceeded bound: {pure_roundtrip_delta}")
    first_project_m = tuple(
        tuple(float(value) for value in (body.matrix_world @ Vector(point)))
        for point in first_exterior_ring_local
    )
    second_project_m = tuple(
        tuple(float(value) for value in (body.matrix_world @ Vector(point)))
        for point in second_exterior_ring_local
    )
    normals_project = []
    try:
        for record in exterior_ring_evidence["records"]:
            transformed_face_normals = patch_contract.transform_normals(
                normal_rows,
                [
                    body.data.polygons[int(face_id)].normal
                    for face_id in record["exterior_face_ids"]
                ],
            )
            average = sum((Vector(value) for value in transformed_face_normals), Vector())
            if average.length <= 1.0e-12:
                raise R20Error("project exterior seam-normal average collapsed")
            normals_project.append(tuple(float(value) for value in average.normalized()))
    except ValueError as exc:
        raise R20Error(f"project normal transformation failed: {exc}") from exc
    if len(normals_project) != patch_contract.SEAM_COUNT:
        raise R20Error("project seam-normal record count drifted")
    return {
        "seam_local": seam_local,
        "seam_project_m": seam_project_m,
        "first_exterior_ring_project_m": first_project_m,
        "second_exterior_ring_project_m": second_project_m,
        "seam_normals_project": tuple(normals_project),
        "matrix_world_rows": tuple(tuple(row) for row in matrix_rows),
        "matrix_world_inverse_rows": inverse_rows,
        "normal_matrix_rows": normal_rows,
        "maximum_seam_local_roundtrip_delta_local_units": float(
            contract["maximum_seam_local_roundtrip_delta_local_units"]
        ),
        "maximum_generated_project_roundtrip_delta_m": float(
            contract["maximum_generated_project_roundtrip_delta_m"]
        ),
        "evidence": {
            "coordinate_space": "project_world_meters",
            "live_full_precision_seam_from_canonical_ids": True,
            "serialized_world_seam_used_as_crosscheck_only": True,
            "serialized_crosscheck_authority": (
                "immutable hash-bound preflight_attempt_04/PREFLIGHT_EVIDENCE.json"
            ),
            "local_seam_serialized_crosscheck_maximum_delta": local_crosscheck_delta,
            "world_seam_serialized_crosscheck_maximum_delta_m": world_crosscheck_delta,
            "local_seam_median_edge_scale": patch_contract.closed_cycle_median_edge_scale(
                seam_local
            ),
            "world_seam_median_edge_scale_m": world_edge_scale,
            "expected_world_seam_median_edge_scale_m": expected_world_edge_scale,
            "seam_affine_roundtrip_maximum_local_delta": pure_roundtrip_delta,
            "seam_affine_roundtrip_delta_unit": "body_local_units",
            "exact_source_matrix_required": True,
            "arbitrary_transform_variation_allowed": False,
            "affine_validation": affine_evidence,
            "full_matrix_exterior_ring_transform": True,
            "inverse_transpose_normal_transform": True,
            "normal_averaging_order": (
                "transform and normalize each incident exterior face normal, then equal-weight average"
            ),
        },
    }


def seam_uv_records(body: bpy.types.Object, mask: Mapping[str, Any]) -> tuple[dict[str, list[tuple[float, float]]], dict[str, Any]]:
    mesh = body.data
    selected = set(int(value) for value in mask["selected_face_ids"])
    seam = [int(value) for value in mask["canonical_seam_vertex_ids"]]
    result: dict[str, list[tuple[float, float]]] = {}
    evidence: dict[str, Any] = {}
    for layer in mesh.uv_layers:
        values: list[tuple[float, float]] = []
        records = []
        for vertex_index in seam:
            samples = []
            for face_index in selected:
                polygon = mesh.polygons[face_index]
                for loop_index in range(int(polygon.loop_start), int(polygon.loop_start + polygon.loop_total)):
                    if int(mesh.loops[loop_index].vertex_index) == vertex_index:
                        uv = layer.data[loop_index].uv
                        samples.append((float(uv.x), float(uv.y)))
            unique = []
            for sample in samples:
                if all(math.dist(sample, prior) > 1.0e-10 for prior in unique):
                    unique.append(sample)
            if len(unique) != 1:
                raise R20Error(
                    f"patch-side seam UV is ambiguous at vertex {vertex_index} on {layer.name}: {unique}"
                )
            values.append(unique[0])
            records.append({"vertex": vertex_index, "uv": list(unique[0]), "sample_count": len(samples)})
        crossings = patch_contract.uv_cycle_crossings(values)
        if crossings:
            raise R20Error(f"seam UV cycle self-crosses on {layer.name}: {crossings}")
        result[layer.name] = values
        evidence[layer.name] = {
            "records": records,
            "sha256": sha256_json(records),
            "self_crossing_pairs": [],
        }
    if not result:
        raise R20Error("primary surface has no UV layer")
    return result, evidence


def seam_weight_records(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    mask: Mapping[str, Any],
) -> tuple[list[dict[str, float]], dict[str, Any]]:
    group_names = {int(group.index): group.name for group in body.vertex_groups}
    bone_names = {bone.name for bone in rig.data.bones}
    result = []
    for vertex_index in mask["canonical_seam_vertex_ids"]:
        vertex = body.data.vertices[int(vertex_index)]
        weights = {
            group_names[int(item.group)]: float(item.weight)
            for item in vertex.groups
            if float(item.weight) > 0.0
        }
        if not weights or set(weights) - bone_names:
            raise R20Error(f"seam vertex {vertex_index} has missing or non-armature weights")
        if not math.isclose(sum(weights.values()), 1.0, rel_tol=0.0, abs_tol=1.0e-5):
            raise R20Error(f"seam vertex {vertex_index} weights do not sum to one")
        result.append(weights)
    return result, {
        "record_count": len(result),
        "records_sha256": sha256_json(result),
        "all_groups_exist_on_native_rig": True,
        "all_seam_sums_within_1e_5": True,
    }


def preflight_scene(
    config: Mapping[str, Any],
    paths: Mapping[str, Path],
) -> tuple[bpy.types.Object, bpy.types.Object, dict[str, Any], dict[str, Any]]:
    body, rig = _find_scene_components(config)
    freeze = validate_freeze_ledger(
        body,
        rig,
        paths["r20_freeze_ledger"],
        paths["freeze_identity_correction"],
        require_source_primary_hashes=True,
    )
    mask = derive_exact_mask(body, paths["interface_evidence"])
    preserved = preserved_primary_snapshot(body)
    if preserved["preserved_face_count"] != 24560 or preserved["preserved_vertex_count"] != 12440:
        raise R20Error("canonical preserved-primary subset counts drifted")
    first, second, _local_normals, ring_evidence = derive_exterior_rings_and_normals(body, mask)
    sealed_preflight_mask = json.loads(
        paths["passed_preflight_attempt_04_evidence"].read_text(encoding="utf-8")
    )["mask"]
    coordinate_inputs = _project_meter_coordinate_inputs(
        body,
        mask,
        sealed_preflight_mask,
        first,
        second,
        ring_evidence,
        config["attempt_04_coordinate_space_contract"],
    )
    uv, uv_evidence = seam_uv_records(body, mask)
    weights, weight_evidence = seam_weight_records(body, rig, mask)
    global_state = {
        "rig_rest_structure_sha256": rig_rest_signature(rig),
        "actions_sha256": action_digest(),
        "materials_sha256": material_graph_digest(),
        "body_matrix_world_sha256": _matrix_digest(body.matrix_world),
        "body_modifiers_sha256": sha256_json(modifier_record(body)),
    }
    record = {
        "worker_id": WORKER_ID,
        "timestamp_utc": utc_now(),
        "source_blend": _assert_hash(paths["source_blend"], SOURCE_BLEND_SHA256, "source Blend"),
        "whole_source_package": {
            "manifest_sha256": SOURCE_MANIFEST_SHA256,
            "entry_count": EXPECTED_SOURCE_MANIFEST_ENTRIES,
            "all_entries_size_and_sha256_match": True,
            "exact_file_set_matches": True,
        },
        "attempt_04_correction_authorities": {
            "attempt_03_failure": _assert_hash(
                paths["prior_failed_preflight_attempt_03"],
                PRIOR_FAILED_PREFLIGHT_ATTEMPT_03_SHA256,
                "Attempt03 failure evidence",
            ),
            "interface_attribute_correction": _assert_hash(
                paths["interface_attribute_correction"],
                INTERFACE_ATTRIBUTE_CORRECTION_SHA256,
                "Attempt04 interface/attribute correction",
            ),
            "whole_preflight_reconciliation": {
                "evidence": _assert_hash(
                    paths["preflight_reconciliation_evidence"],
                    PREFLIGHT_RECONCILIATION_EVIDENCE_SHA256,
                    "whole preflight reconciliation evidence",
                ),
                "checkpoint": _assert_hash(
                    paths["preflight_reconciliation_checkpoint"],
                    PREFLIGHT_RECONCILIATION_CHECKPOINT_SHA256,
                    "whole preflight reconciliation checkpoint",
                ),
                "manifest": _assert_hash(
                    paths["preflight_reconciliation_manifest"],
                    PREFLIGHT_RECONCILIATION_MANIFEST_SHA256,
                    "whole preflight reconciliation manifest",
                ),
            },
        },
        "author_attempt_04_coordinate_space_authorities": {
            "attempt_03_summary": _assert_hash(
                paths["author_attempt_03_summary"],
                AUTHOR_ATTEMPT_03_SUMMARY_SHA256,
                "Author Attempt03 summary",
            ),
            "attempt_03_failure": _assert_hash(
                paths["author_attempt_03_failure"],
                AUTHOR_ATTEMPT_03_FAILURE_SHA256,
                "Author Attempt03 top failure",
            ),
            "attempt_03_candidate_a_failure": _assert_hash(
                paths["author_attempt_03_candidate_a_failure"],
                AUTHOR_ATTEMPT_03_CANDIDATE_A_FAILURE_SHA256,
                "Author Attempt03 candidate A failure",
            ),
            "attempt_03_candidate_b_failure": _assert_hash(
                paths["author_attempt_03_candidate_b_failure"],
                AUTHOR_ATTEMPT_03_CANDIDATE_B_FAILURE_SHA256,
                "Author Attempt03 candidate B failure",
            ),
            "coordinate_space_diagnosis": _assert_hash(
                paths["author_attempt_03_coordinate_diagnosis"],
                AUTHOR_ATTEMPT_03_COORDINATE_DIAGNOSIS_SHA256,
                "Author Attempt03 coordinate-space diagnosis",
            ),
        },
        "freeze": freeze,
        "mask": mask,
        "preserved_primary_snapshot": preserved,
        "exterior_ring_evidence": ring_evidence,
        "coordinate_space_evidence": coordinate_inputs["evidence"],
        "seam_uv_evidence": uv_evidence,
        "seam_weight_evidence": weight_evidence,
        "global_state": global_state,
        "pure_contract": patch_contract.contract_record(),
        "regional_material_response": {
            "existing_material": PATCH_MATERIAL_NAME,
            "material_graph_unchanged": True,
            "patch_faces_use_existing_slot": PATCH_MATERIAL_SLOT,
            "texture_response_uses_harmonic_uv_interpolation": True,
            "painted_geometry_substitute_used": False,
            "bounded_natural_surface_response_requires_owner_render_review": True,
        },
        "visual_rejection_to_correct": [
            "broad inverted trapezoid or triangular pasted panel",
            "straight superior edge and sharp diagonal borders",
            "central dark cavity or crease",
            "unreadable external landmark order",
        ],
        "face_head_eyes_brows_upper_body_frozen": True,
        "body_asset_mutated": False,
        "blender_file_saved": False,
    }
    inputs = {
        "seam_local": coordinate_inputs["seam_local"],
        "seam_project_m": coordinate_inputs["seam_project_m"],
        "first_exterior_ring": coordinate_inputs["first_exterior_ring_project_m"],
        "second_exterior_ring": coordinate_inputs["second_exterior_ring_project_m"],
        "seam_normals": coordinate_inputs["seam_normals_project"],
        "matrix_world_rows": coordinate_inputs["matrix_world_rows"],
        "matrix_world_inverse_rows": coordinate_inputs["matrix_world_inverse_rows"],
        "normal_matrix_rows": coordinate_inputs["normal_matrix_rows"],
        "maximum_seam_local_roundtrip_delta_local_units": coordinate_inputs[
            "maximum_seam_local_roundtrip_delta_local_units"
        ],
        "maximum_generated_project_roundtrip_delta_m": coordinate_inputs[
            "maximum_generated_project_roundtrip_delta_m"
        ],
        "seam_uv": uv,
        "seam_weights": weights,
        "preserved_snapshot": preserved,
        "global_state": global_state,
    }
    return body, rig, record, inputs


def _average_patch_normal_project_m(
    body: bpy.types.Object,
    selected_face_ids: Sequence[int],
    normal_matrix_rows: Sequence[Sequence[float]],
) -> Vector:
    try:
        transformed = patch_contract.transform_normals(
            normal_matrix_rows,
            [body.data.polygons[int(index)].normal for index in selected_face_ids],
        )
    except ValueError as exc:
        raise R20Error(f"old patch project-normal transformation failed: {exc}") from exc
    normal = sum((Vector(value) for value in transformed), Vector())
    if normal.length <= 1.0e-12:
        raise R20Error("old patch average normal collapsed")
    return normal.normalized()


def _face_normal_from_positions(face: Sequence[int], positions: Sequence[Sequence[float]]) -> Vector:
    first, second, third = (Vector(positions[index]) for index in face[:3])
    normal = (second - first).cross(third - first)
    if normal.length <= 1.0e-12:
        raise R20Error("generated patch face normal collapsed")
    return normal.normalized()


def _capture_preserved_loop_normals(body: bpy.types.Object) -> dict[str, Any]:
    """Capture decoded normals and every raw planned nonpatch attribute.

    The historical function name is retained because this is still the input
    to localized split-normal restoration.  Attempt04 expands the capture so
    no surviving ``custom_normal`` or UV-editor selection element is implicit.
    """

    mesh = body.data
    _supported_attribute_inventory(mesh)
    interface_coordinates = {
        _coordinate_key(mesh.vertices[index].co) for index in _patch_interface_vertex_ids(mesh)
    }
    result: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for polygon in mesh.polygons:
        if int(polygon.material_index) == PATCH_MATERIAL_SLOT:
            continue
        face_key = json.dumps(
            _canonical_face_record(mesh, polygon, include_corner_data=False),
            sort_keys=True,
            separators=(",", ":"),
        )
        corners: list[dict[str, Any]] = []
        for loop_index in range(int(polygon.loop_start), int(polygon.loop_start + polygon.loop_total)):
            vertex_index = int(mesh.loops[loop_index].vertex_index)
            corners.append(
                {
                    "coordinate": _coordinate_key(mesh.vertices[vertex_index].co),
                    "decoded_normal": list(_corner_normal(mesh, loop_index)),
                    "custom_normal": _read_planned_attribute_value(
                        _planned_attribute(mesh, CUSTOM_NORMAL_NAME), loop_index
                    ),
                    ".uv_select_vert": _read_planned_attribute_value(
                        _planned_attribute(mesh, ".uv_select_vert"), loop_index
                    ),
                    ".uv_select_edge": _read_planned_attribute_value(
                        _planned_attribute(mesh, ".uv_select_edge"), loop_index
                    ),
                }
            )
        result[face_key].append(
            {
                "corners": corners,
                ".uv_select_face": _read_planned_attribute_value(
                    _planned_attribute(mesh, UV_SELECTION_FACE_NAME), int(polygon.index)
                ),
            }
        )
    return {
        "faces": dict(result),
        "interface_coordinate_keys": sorted(interface_coordinates),
        "capture_sha256": sha256_json(result),
    }


def _restore_exact_preserved_loop_normals(
    body: bpy.types.Object,
    captured: Mapping[str, Any],
) -> dict[str, Any]:
    mesh = body.data
    working = {key: deque(values) for key, values in captured["faces"].items()}
    interface_coordinates = set(str(value) for value in captured["interface_coordinate_keys"])
    exterior_by_vertex: defaultdict[int, list[Vector]] = defaultdict(list)
    preserved_targets: dict[int, dict[str, Any]] = {}
    preserved_face_targets: dict[int, bool] = {}
    matched_faces = 0
    for polygon in mesh.polygons:
        if int(polygon.material_index) == PATCH_MATERIAL_SLOT:
            continue
        face_key = json.dumps(
            _canonical_face_record(mesh, polygon, include_corner_data=False),
            sort_keys=True,
            separators=(",", ":"),
        )
        if face_key not in working or not working[face_key]:
            raise R20Error("a preserved face could not be matched for split-normal restoration")
        face_record = working[face_key].popleft()
        normals = face_record["corners"]
        loop_indices = range(int(polygon.loop_start), int(polygon.loop_start + polygon.loop_total))
        if len(normals) != int(polygon.loop_total):
            raise R20Error("preserved split-normal corner count drifted")
        by_coordinate = {str(record["coordinate"]): record for record in normals}
        if len(by_coordinate) != len(normals):
            raise R20Error("preserved face has duplicate coordinates and ambiguous loop normals")
        for loop_index in loop_indices:
            vertex_index = int(mesh.loops[loop_index].vertex_index)
            coordinate = _coordinate_key(mesh.vertices[vertex_index].co)
            if coordinate not in by_coordinate:
                raise R20Error("preserved face corner coordinate changed")
            target = by_coordinate[coordinate]
            exterior_by_vertex[int(mesh.loops[loop_index].vertex_index)].append(
                Vector(target["decoded_normal"])
            )
            preserved_targets[int(loop_index)] = target
        preserved_face_targets[int(polygon.index)] = bool(face_record[UV_SELECTION_FACE_NAME])
        matched_faces += 1
    if any(queue for queue in working.values()):
        raise R20Error("one or more captured preserved faces disappeared")

    # Do not call Mesh.normals_split_custom_set here.  Blender 5.1 implements
    # that API as a whole-mesh smooth-fan recalculation that can also add sharp
    # edges.  Preserve every surviving raw short2 instead, and explicitly use
    # the (0, 0) auto-normal sentinel for each smooth new-patch corner.  The
    # local decoded seam-fan gate below detects any unacceptable basis change.
    custom_normal = _planned_attribute(mesh, CUSTOM_NORMAL_NAME)
    uv_select_vert = _planned_attribute(mesh, ".uv_select_vert")
    uv_select_edge = _planned_attribute(mesh, ".uv_select_edge")
    uv_select_face = _planned_attribute(mesh, UV_SELECTION_FACE_NAME)
    for loop_index, target in preserved_targets.items():
        _write_planned_attribute_value(custom_normal, loop_index, target[CUSTOM_NORMAL_NAME])
        _write_planned_attribute_value(uv_select_vert, loop_index, target[".uv_select_vert"])
        _write_planned_attribute_value(uv_select_edge, loop_index, target[".uv_select_edge"])
    for face_index, value in preserved_face_targets.items():
        _write_planned_attribute_value(uv_select_face, face_index, value)
    patch_loop_indices = []
    patch_face_indices = []
    for polygon in mesh.polygons:
        if int(polygon.material_index) != PATCH_MATERIAL_SLOT:
            continue
        patch_face_indices.append(int(polygon.index))
        _write_planned_attribute_value(uv_select_face, int(polygon.index), False)
        for loop_index in range(int(polygon.loop_start), int(polygon.loop_start + polygon.loop_total)):
            patch_loop_indices.append(loop_index)
            _write_planned_attribute_value(custom_normal, loop_index, (0, 0))
            _write_planned_attribute_value(uv_select_vert, loop_index, False)
            _write_planned_attribute_value(uv_select_edge, loop_index, False)
    mesh.update()

    raw_mismatches = []
    noninterface_decoded_delta = 0.0
    interface_decoded_dots = []
    for loop_index, target in preserved_targets.items():
        actual_raw = _read_planned_attribute_value(custom_normal, loop_index)
        actual_vert = _read_planned_attribute_value(uv_select_vert, loop_index)
        actual_edge = _read_planned_attribute_value(uv_select_edge, loop_index)
        if (
            actual_raw != target[CUSTOM_NORMAL_NAME]
            or actual_vert != target[".uv_select_vert"]
            or actual_edge != target[".uv_select_edge"]
        ):
            raw_mismatches.append(loop_index)
        actual_normal = Vector(_corner_normal(mesh, loop_index)).normalized()
        target_normal = Vector(target["decoded_normal"]).normalized()
        coordinate = str(target["coordinate"])
        if coordinate in interface_coordinates:
            interface_decoded_dots.append(max(-1.0, min(1.0, actual_normal.dot(target_normal))))
        else:
            noninterface_decoded_delta = max(
                noninterface_decoded_delta,
                (actual_normal - target_normal).length,
            )
    face_selection_mismatches = [
        face_index
        for face_index, value in preserved_face_targets.items()
        if _read_planned_attribute_value(uv_select_face, face_index) is not value
    ]
    if raw_mismatches or face_selection_mismatches:
        raise R20Error(
            "surviving planned attribute values changed: "
            + json.dumps(
                {
                    "corner_mismatch_count": len(raw_mismatches),
                    "face_mismatch_count": len(face_selection_mismatches),
                },
                sort_keys=True,
            )
        )
    if noninterface_decoded_delta > 1.0e-7:
        raise R20Error(
            f"decoded custom normals drifted outside the seam fan: {noninterface_decoded_delta}"
        )
    if not interface_decoded_dots:
        raise R20Error("localized seam-normal comparison produced no records")
    interface_minimum_dot = min(interface_decoded_dots)
    interface_median_dot = statistics.median(interface_decoded_dots)
    if interface_minimum_dot < 0.94 or interface_median_dot < 0.98:
        raise R20Error(
            "localized preserved seam-fan normal continuity failed: "
            f"min={interface_minimum_dot}, median={interface_median_dot}"
        )

    patch_normal_lengths = []
    seam_patch_dots = []
    patch_normals_by_vertex: defaultdict[int, list[Vector]] = defaultdict(list)
    for loop_index in patch_loop_indices:
        vertex_index = int(mesh.loops[loop_index].vertex_index)
        actual = Vector(_corner_normal(mesh, loop_index))
        patch_normal_lengths.append(actual.length)
        if actual.length > 1.0e-12:
            actual.normalize()
        patch_normals_by_vertex[vertex_index].append(actual)
        if exterior_by_vertex[vertex_index]:
            exterior = sum(exterior_by_vertex[vertex_index], Vector()).normalized()
            seam_patch_dots.append(max(-1.0, min(1.0, actual.dot(exterior))))
    same_vertex_dots = []
    for values in patch_normals_by_vertex.values():
        for first in range(len(values)):
            for second in range(first + 1, len(values)):
                same_vertex_dots.append(max(-1.0, min(1.0, values[first].dot(values[second]))))
    patch_selection_false = all(
        not _read_planned_attribute_value(uv_select_vert, loop_index)
        and not _read_planned_attribute_value(uv_select_edge, loop_index)
        for loop_index in patch_loop_indices
    ) and all(
        not _read_planned_attribute_value(uv_select_face, face_index)
        for face_index in patch_face_indices
    )
    if not patch_selection_false:
        raise R20Error("new patch UV editor selection attributes are not deterministically false")
    maximum_patch_normal_length_error = max(
        abs(value - 1.0) for value in patch_normal_lengths
    )
    minimum_patch_same_vertex_dot = min(same_vertex_dots) if same_vertex_dots else 1.0
    minimum_seam_patch_dot = min(seam_patch_dots) if seam_patch_dots else -1.0
    median_seam_patch_dot = statistics.median(seam_patch_dots) if seam_patch_dots else -1.0
    if (
        maximum_patch_normal_length_error > 1.0e-4
        or minimum_patch_same_vertex_dot < 0.995
        or minimum_seam_patch_dot < 0.94
        or median_seam_patch_dot < 0.98
    ):
        raise R20Error(
            "new patch smooth-normal numeric gate failed: "
            + json.dumps(
                {
                    "maximum_unit_length_error": maximum_patch_normal_length_error,
                    "minimum_same_vertex_dot": minimum_patch_same_vertex_dot,
                    "minimum_seam_dot": minimum_seam_patch_dot,
                    "median_seam_dot": median_seam_patch_dot,
                },
                sort_keys=True,
            )
        )
    return {
        "preserved_face_count": matched_faces,
        "preserved_corner_count": len(preserved_targets),
        "all_surviving_custom_normal_short2_values_exact": True,
        "all_surviving_uv_selection_values_exact": True,
        "new_patch_uv_selection_values_all_false": True,
        "decoded_noninterface_maximum_vector_delta": noninterface_decoded_delta,
        "decoded_interface_minimum_dot": interface_minimum_dot,
        "decoded_interface_median_dot": interface_median_dot,
        "new_patch_custom_normal_storage": "explicit (0, 0) Blender auto-normal sentinel",
        "new_patch_faces_smooth": True,
        "patch_normal_numeric_gate": {
            "patch_loop_count": len(patch_loop_indices),
            "maximum_unit_length_error": maximum_patch_normal_length_error,
            "minimum_same_vertex_dot": minimum_patch_same_vertex_dot,
            "minimum_seam_to_preserved_exterior_dot": minimum_seam_patch_dot,
            "median_seam_to_preserved_exterior_dot": median_seam_patch_dot,
            "thresholds": {
                "maximum_unit_length_error": 1.0e-4,
                "minimum_same_vertex_dot": 0.995,
                "minimum_seam_dot": 0.94,
                "median_seam_dot": 0.98,
            },
            "heatmap_review_required": True,
            "status": "PASS",
        },
        "surviving_raw_custom_normal_storage_used_without_reencoding": True,
        "normals_split_custom_set_used": False,
        "sharp_edge_attribute_modified_by_normal_work": False,
        "global_normal_recalculation_used": False,
    }


def _current_patch_attribute_normal_gate(body: bpy.types.Object) -> dict[str, Any]:
    """Re-run the local attribute/normal gate, including after save/reopen."""

    mesh = body.data
    _supported_attribute_inventory(mesh)
    custom_normal = _planned_attribute(mesh, CUSTOM_NORMAL_NAME)
    uv_select_vert = _planned_attribute(mesh, ".uv_select_vert")
    uv_select_edge = _planned_attribute(mesh, ".uv_select_edge")
    uv_select_face = _planned_attribute(mesh, UV_SELECTION_FACE_NAME)
    expected_lengths = {
        CUSTOM_NORMAL_NAME: len(mesh.loops),
        ".uv_select_vert": len(mesh.loops),
        ".uv_select_edge": len(mesh.loops),
        UV_SELECTION_FACE_NAME: len(mesh.polygons),
    }
    for name, expected in expected_lengths.items():
        actual = len(_planned_attribute(mesh, name).data)
        if actual != expected:
            raise R20Error(f"planned attribute domain length drifted for {name}: {actual} != {expected}")

    interface_vertices = _patch_interface_vertex_ids(mesh)
    exterior_by_vertex: defaultdict[int, list[Vector]] = defaultdict(list)
    preserved_edge_indices: set[int] = set()
    for polygon in mesh.polygons:
        if int(polygon.material_index) == PATCH_MATERIAL_SLOT:
            continue
        for loop_index in range(int(polygon.loop_start), int(polygon.loop_start + polygon.loop_total)):
            preserved_edge_indices.add(int(mesh.loops[loop_index].edge_index))
            vertex_index = int(mesh.loops[loop_index].vertex_index)
            if vertex_index in interface_vertices:
                exterior_by_vertex[vertex_index].append(Vector(_corner_normal(mesh, loop_index)))

    patch_loop_indices: list[int] = []
    patch_face_indices: list[int] = []
    patch_vertex_indices: set[int] = set()
    patch_edge_indices: set[int] = set()
    patch_normals_by_vertex: defaultdict[int, list[Vector]] = defaultdict(list)
    seam_dots: list[float] = []
    normal_lengths: list[float] = []
    nonzero_patch_custom_normal = []
    nonsmooth_patch_faces = []
    for polygon in mesh.polygons:
        if int(polygon.material_index) != PATCH_MATERIAL_SLOT:
            continue
        patch_face_indices.append(int(polygon.index))
        if not bool(polygon.use_smooth):
            nonsmooth_patch_faces.append(int(polygon.index))
        for loop_index in range(int(polygon.loop_start), int(polygon.loop_start + polygon.loop_total)):
            patch_loop_indices.append(loop_index)
            patch_vertex_indices.add(int(mesh.loops[loop_index].vertex_index))
            patch_edge_indices.add(int(mesh.loops[loop_index].edge_index))
            if _read_planned_attribute_value(custom_normal, loop_index) != [0, 0]:
                nonzero_patch_custom_normal.append(loop_index)
            vertex_index = int(mesh.loops[loop_index].vertex_index)
            normal = Vector(_corner_normal(mesh, loop_index))
            normal_lengths.append(normal.length)
            if normal.length > 1.0e-12:
                normal.normalize()
            patch_normals_by_vertex[vertex_index].append(normal)
            if exterior_by_vertex[vertex_index]:
                exterior = sum(exterior_by_vertex[vertex_index], Vector()).normalized()
                seam_dots.append(max(-1.0, min(1.0, normal.dot(exterior))))

    if len(patch_face_indices) != patch_contract.REPLACEMENT_FACE_COUNT or not patch_loop_indices:
        raise R20Error("saved patch attribute/normal gate found incomplete replacement topology")
    uv_selections_false = all(
        not _read_planned_attribute_value(uv_select_vert, index)
        and not _read_planned_attribute_value(uv_select_edge, index)
        for index in patch_loop_indices
    ) and all(
        not _read_planned_attribute_value(uv_select_face, index)
        for index in patch_face_indices
    )
    new_vertex_indices = patch_vertex_indices - interface_vertices
    new_edge_indices = patch_edge_indices - preserved_edge_indices
    mesh_selection_and_sharp_defaults = (
        all(not bool(mesh.vertices[index].select) for index in new_vertex_indices)
        and all(
            not bool(mesh.edges[index].select) and not bool(mesh.edges[index].use_edge_sharp)
            for index in new_edge_indices
        )
        and all(not bool(mesh.polygons[index].select) for index in patch_face_indices)
    )
    same_vertex_dots = []
    for normals in patch_normals_by_vertex.values():
        for first in range(len(normals)):
            for second in range(first + 1, len(normals)):
                same_vertex_dots.append(
                    max(-1.0, min(1.0, normals[first].dot(normals[second])))
                )
    maximum_unit_error = max(abs(value - 1.0) for value in normal_lengths)
    minimum_same_vertex_dot = min(same_vertex_dots) if same_vertex_dots else 1.0
    minimum_seam_dot = min(seam_dots) if seam_dots else -1.0
    median_seam_dot = statistics.median(seam_dots) if seam_dots else -1.0
    if (
        nonzero_patch_custom_normal
        or nonsmooth_patch_faces
        or not uv_selections_false
        or not mesh_selection_and_sharp_defaults
        or maximum_unit_error > 1.0e-4
        or minimum_same_vertex_dot < 0.995
        or minimum_seam_dot < 0.94
        or median_seam_dot < 0.98
    ):
        raise R20Error(
            "current patch attribute/normal gate failed: "
            + json.dumps(
                {
                    "nonzero_patch_custom_normal_count": len(nonzero_patch_custom_normal),
                    "nonsmooth_patch_face_count": len(nonsmooth_patch_faces),
                    "new_patch_uv_selections_false": uv_selections_false,
                    "new_mesh_selection_and_sharp_defaults": mesh_selection_and_sharp_defaults,
                    "maximum_unit_length_error": maximum_unit_error,
                    "minimum_same_vertex_dot": minimum_same_vertex_dot,
                    "minimum_seam_dot": minimum_seam_dot,
                    "median_seam_dot": median_seam_dot,
                },
                sort_keys=True,
            )
        )
    return {
        "planned_attribute_lengths": expected_lengths,
        "patch_face_count": len(patch_face_indices),
        "patch_corner_count": len(patch_loop_indices),
        "patch_custom_normal_all_zero_auto_sentinel": True,
        "patch_faces_all_smooth": True,
        "patch_uv_selection_values_all_false": True,
        "new_vertex_selection_values_all_false": True,
        "new_edge_selection_values_all_false": True,
        "new_edge_sharp_values_all_false": True,
        "new_face_selection_values_all_false": True,
        "maximum_unit_length_error": maximum_unit_error,
        "minimum_same_vertex_dot": minimum_same_vertex_dot,
        "minimum_seam_to_preserved_exterior_dot": minimum_seam_dot,
        "median_seam_to_preserved_exterior_dot": median_seam_dot,
        "ordinary_and_opposite_light_normal_heatmaps_required": True,
        "status": "PASS",
    }


def _candidate_parameters(candidate_id: str) -> patch_contract.CandidateParameters:
    for candidate in patch_contract.CANDIDATES:
        if candidate.candidate_id == candidate_id:
            return candidate
    raise R20Error(f"candidate is outside the sealed two-candidate set: {candidate_id}")


def _boundary_loop_counts(mesh: bpy.types.Mesh) -> tuple[int, int, int]:
    edge_incidence: Counter[tuple[int, int]] = Counter()
    adjacency: defaultdict[int, set[int]] = defaultdict(set)
    for polygon in mesh.polygons:
        values = [int(value) for value in polygon.vertices]
        for first, second in zip(values, values[1:] + values[:1]):
            edge_incidence[tuple(sorted((first, second)))] += 1
    boundaries = [edge for edge, count in edge_incidence.items() if count == 1]
    nonmanifold = sum(count > 2 for count in edge_incidence.values())
    for first, second in boundaries:
        adjacency[first].add(second)
        adjacency[second].add(first)
    loops = 0
    unseen = set(adjacency)
    while unseen:
        loops += 1
        queue = [unseen.pop()]
        while queue:
            current = queue.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
    return len(boundaries), loops, nonmanifold


def _mesh_component_count(mesh: bpy.types.Mesh) -> int:
    adjacency = _vertex_neighbors(mesh)
    referenced = {int(index) for polygon in mesh.polygons for index in polygon.vertices}
    components = 0
    unseen = set(referenced)
    while unseen:
        components += 1
        queue = [unseen.pop()]
        while queue:
            current = queue.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
    return components


def _semantic_attribute_name(name: str) -> str:
    cleaned = "".join(character if character.isalnum() else "_" for character in name).strip("_")
    return (LANDMARK_ATTRIBUTE_PREFIX + cleaned.upper())[:63]


def _add_landmark_attributes(
    body: bpy.types.Object,
    local_to_global: Mapping[int, int],
) -> dict[str, Any]:
    mesh = body.data
    result: dict[str, Any] = {}
    for name, local_indices in patch_contract.landmark_vertex_sets().items():
        attribute_name = _semantic_attribute_name(name)
        if mesh.attributes.get(attribute_name) is not None:
            raise R20Error(f"semantic landmark attribute already exists: {attribute_name}")
        attribute = mesh.attributes.new(name=attribute_name, type="BOOLEAN", domain="POINT")
        global_indices = sorted(int(local_to_global[index]) for index in local_indices)
        for index in global_indices:
            attribute.data[index].value = True
        points = [body.matrix_world @ mesh.vertices[index].co for index in global_indices]
        centroid = sum(points, Vector()) / len(points)
        low = [min(float(point[axis]) for point in points) for axis in range(3)]
        high = [max(float(point[axis]) for point in points) for axis in range(3)]
        result[name] = {
            "attribute": attribute_name,
            "vertex_count": len(global_indices),
            "global_vertex_indices": global_indices,
            "project_space_centroid_m": vector_record(centroid),
            "project_space_bounds_m": {"minimum": vector_record(low), "maximum": vector_record(high)},
            "external_surface_semantic_hook_only": True,
            "internal_function_claimed": False,
        }
    body["r20_external_landmark_order_json"] = json.dumps(
        list(patch_contract.EXTERNAL_LANDMARK_ORDER), separators=(",", ":")
    )
    body["r20_external_landmark_record_sha256"] = sha256_json(result)
    body["r20_internal_function_claimed"] = False
    return result


def _prepare_candidate_fields(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    mask: Mapping[str, Any],
    inputs: Mapping[str, Any],
    candidate_id: str,
) -> dict[str, Any]:
    candidate = _candidate_parameters(candidate_id)
    seam_local = tuple(inputs["seam_local"])
    seam_project_m = tuple(inputs["seam_project_m"])
    positions_project_m, geometry_evidence = patch_contract.build_positions(
        seam_project_m,
        inputs["first_exterior_ring"],
        inputs["second_exterior_ring"],
        inputs["seam_normals"],
        candidate,
    )
    faces = patch_contract.build_quad_topology()
    old_normal = _average_patch_normal_project_m(
        body, mask["selected_face_ids"], inputs["normal_matrix_rows"]
    )
    generated_normal = _face_normal_from_positions(faces[0], positions_project_m)
    reverse_winding = float(old_normal.dot(generated_normal)) < 0.0
    if reverse_winding:
        faces = patch_contract.build_quad_topology(reverse_winding=True)
    topology = patch_contract.topology_contract(faces)
    quality = patch_contract.geometry_quality(positions_project_m, faces)
    if int(quality["degenerate_face_count_at_1e_10_m2"]) != 0:
        raise R20Error(f"{candidate_id} contains a degenerate patch face")
    if float(quality["minimum_face_area_m2"]) <= 1.0e-10:
        raise R20Error(f"{candidate_id} violates minimum face area")
    if float(quality["maximum_quad_edge_ratio"]) > 3.0:
        raise R20Error(f"{candidate_id} violates maximum quad edge ratio: {quality}")
    uv_fields = {}
    uv_evidence = {}
    for name, seam_values in inputs["seam_uv"].items():
        solved, evidence = patch_contract.harmonic_uv(seam_values)
        uv_fields[name] = solved
        uv_evidence[name] = evidence
    weight_solution = patch_contract.harmonic_weights(inputs["seam_weights"])
    if weight_solution.maximum_positive_influences_after_projection > 4:
        raise R20Error("harmonic top-four projection exceeded four influences")
    if any(
        not math.isclose(sum(record.values()), 1.0, rel_tol=0.0, abs_tol=1.0e-8)
        for record in weight_solution.records[patch_contract.SEAM_COUNT :]
    ):
        raise R20Error("one or more new harmonic weights do not sum to one")
    generated_project_m = positions_project_m[patch_contract.SEAM_COUNT :]
    generated_body_local = patch_contract.transform_affine_points(
        inputs["matrix_world_inverse_rows"], generated_project_m
    )
    if len(generated_body_local) != patch_contract.NEW_VERTEX_COUNT:
        raise R20Error("Attempt-04 inverse transform did not produce exactly 740 new vertices")
    positions_body_local = seam_local + generated_body_local
    if positions_body_local[: patch_contract.SEAM_COUNT] != seam_local:
        raise R20Error("Attempt-04 changed an exact original seam-local coordinate")
    generated_project_roundtrip = patch_contract.transform_affine_points(
        inputs["matrix_world_rows"], generated_body_local
    )
    generated_world_roundtrip_delta = max(
        math.dist(first, second)
        for first, second in zip(generated_project_m, generated_project_roundtrip)
    )
    if generated_world_roundtrip_delta > float(
        inputs["maximum_generated_project_roundtrip_delta_m"]
    ):
        raise R20Error(
            "generated project/local/project roundtrip exceeded bound: "
            f"{generated_world_roundtrip_delta}"
        )
    return {
        "candidate": candidate,
        "positions_body_local": positions_body_local,
        "faces": faces,
        "uv_fields": uv_fields,
        "weight_solution": weight_solution,
        "evidence": {
            "geometry_construction": geometry_evidence,
            "topology": topology,
            "geometry_quality": quality,
            "geometry_quality_coordinate_space": "project_world_meters",
            "reverse_winding": reverse_winding,
            "winding_comparison_coordinate_space": "project_world_meters",
            "old_patch_average_normal_project": vector_record(old_normal),
            "first_generated_face_normal_project": vector_record(generated_normal),
            "coordinate_conversion": {
                "project_meter_position_count": len(positions_project_m),
                "exact_original_seam_local_position_count": len(seam_local),
                "inverse_transformed_generated_position_count": len(generated_body_local),
                "generated_project_local_project_maximum_delta_m": generated_world_roundtrip_delta,
                "generated_project_roundtrip_delta_unit": "project_world_meters",
                "original_seam_vertices_reused_not_recreated": True,
            },
            "harmonic_uv": uv_evidence,
            "harmonic_weights": {
                "method": "discrete harmonic pre-projection weights followed by deterministic top-four normalization on new vertices only",
                "iterations": weight_solution.iterations,
                "final_maximum_delta": weight_solution.final_maximum_delta,
                "group_count_before_projection": weight_solution.group_count_before_projection,
                "maximum_positive_influences_after_projection": weight_solution.maximum_positive_influences_after_projection,
            },
        },
    }


def _apply_local_patch(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    mask: Mapping[str, Any],
    prepared: Mapping[str, Any],
) -> tuple[dict[int, int], dict[str, Any]]:
    """Perform the only authorized mesh mutation, directly against seam verts."""

    mesh = body.data
    captured_normals = _capture_preserved_loop_normals(body)
    old_mesh_name = mesh.name
    old_material_slots = [slot.material.name if slot.material else "" for slot in body.material_slots]
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        original_vertex_layer = bm.verts.layers.int.new("__R20_ORIGINAL_VERTEX_ID_TRANSIENT")
        local_patch_layer = bm.verts.layers.int.new("__R20_LOCAL_PATCH_ID_TRANSIENT")
        original_face_layer = bm.faces.layers.int.new("__R20_ORIGINAL_FACE_ID_TRANSIENT")
        for vertex in bm.verts:
            vertex[original_vertex_layer] = int(vertex.index)
            vertex[local_patch_layer] = -1
        for face in bm.faces:
            face[original_face_layer] = int(face.index)

        by_original_vertex = {int(vertex[original_vertex_layer]): vertex for vertex in bm.verts}
        by_original_face = {int(face[original_face_layer]): face for face in bm.faces}
        seam_vertices = [by_original_vertex[int(index)] for index in mask["canonical_seam_vertex_ids"]]
        for local_index, vertex in enumerate(seam_vertices):
            vertex[local_patch_layer] = local_index
        selected_faces = [by_original_face[int(index)] for index in mask["selected_face_ids"]]
        interior_vertices = [
            by_original_vertex[int(index)] for index in mask["removable_interior_vertex_ids"]
        ]
        bmesh.ops.delete(bm, geom=selected_faces, context="FACES_ONLY")
        bmesh.ops.delete(bm, geom=interior_vertices, context="VERTS")

        local_vertices = list(seam_vertices)
        for local_index, coordinate in enumerate(
            prepared["positions_body_local"][patch_contract.SEAM_COUNT :],
            start=patch_contract.SEAM_COUNT,
        ):
            vertex = bm.verts.new(Vector(coordinate))
            vertex[original_vertex_layer] = -1
            vertex[local_patch_layer] = local_index
            vertex.select = False
            local_vertices.append(vertex)
        bm.verts.index_update()
        bm.verts.ensure_lookup_table()
        if len(local_vertices) != patch_contract.TOTAL_PATCH_INCIDENT_VERTICES:
            raise R20Error("localized BMesh vertex mapping drifted")

        new_faces = []
        for face_indices in prepared["faces"]:
            face = bm.faces.new([local_vertices[index] for index in face_indices])
            face.material_index = PATCH_MATERIAL_SLOT
            face.smooth = True
            face.select = False
            face[original_face_layer] = -1
            new_faces.append(face)
        bm.faces.index_update()
        bm.faces.ensure_lookup_table()
        if len(new_faces) != patch_contract.REPLACEMENT_FACE_COUNT:
            raise R20Error("localized BMesh face count drifted")

        for edge in {edge for face in new_faces for edge in face.edges}:
            if any(int(vertex[original_vertex_layer]) == -1 for vertex in edge.verts):
                edge.select = False
                edge.smooth = True

        for layer_name, values in prepared["uv_fields"].items():
            uv_layer = bm.loops.layers.uv.get(layer_name)
            if uv_layer is None:
                raise R20Error(f"BMesh lost required UV layer {layer_name}")
            for face in new_faces:
                for loop in face.loops:
                    local_index = int(loop.vert[local_patch_layer])
                    loop[uv_layer].uv = values[local_index]

        deform_layer = bm.verts.layers.deform.active
        if deform_layer is None:
            raise R20Error("primary surface lacks its deform-weight layer")
        groups_by_name = {group.name: int(group.index) for group in body.vertex_groups}
        bone_names = {bone.name for bone in rig.data.bones}
        for local_index in range(patch_contract.SEAM_COUNT, len(local_vertices)):
            vertex = local_vertices[local_index]
            record = prepared["weight_solution"].records[local_index]
            deform = vertex[deform_layer]
            for group_name, weight in record.items():
                if group_name not in bone_names or group_name not in groups_by_name:
                    raise R20Error(f"harmonic result references an unknown native bone group: {group_name}")
                deform[groups_by_name[group_name]] = float(weight)

        bm.normal_update()
        local_to_global = {
            local_index: int(vertex.index) for local_index, vertex in enumerate(local_vertices)
        }
        bm.verts.layers.int.remove(original_vertex_layer)
        bm.verts.layers.int.remove(local_patch_layer)
        bm.faces.layers.int.remove(original_face_layer)
        bm.to_mesh(mesh)
    finally:
        bm.free()
    mesh.update(calc_edges=True, calc_edges_loose=True)
    if mesh.name != old_mesh_name:
        raise R20Error("primary mesh datablock name changed")
    if [slot.material.name if slot.material else "" for slot in body.material_slots] != old_material_slots:
        raise R20Error("primary material-slot bindings changed")
    normal_evidence = _restore_exact_preserved_loop_normals(body, captured_normals)
    landmark_evidence = _add_landmark_attributes(body, local_to_global)
    body["r20_candidate_id"] = prepared["candidate"].candidate_id
    body["r20_private_owner_review_only"] = True
    body["r20_inactive"] = True
    body["r20_unassigned"] = True
    body["r20_unpublished"] = True
    body["r20_runtime_eligible"] = False
    body["r20_owner_approved"] = False
    body["r20_scalp_hair_dependency"] = False
    body["r20_external_surface_only"] = True
    return local_to_global, {
        "localized_edit": True,
        "object_join_used": False,
        "global_weld_used": False,
        "global_normal_recalculation_used": False,
        "boolean_used": False,
        "shrinkwrap_used": False,
        "donor_interior_geometry_used": False,
        "separate_anatomy_objects_created": 0,
        "normal_preservation": normal_evidence,
        "external_landmark_sets": landmark_evidence,
    }


def _weights_for_vertex(body: bpy.types.Object, vertex_index: int) -> dict[str, float]:
    names = {int(group.index): group.name for group in body.vertex_groups}
    return {
        names[int(item.group)]: float(item.weight)
        for item in body.data.vertices[vertex_index].groups
        if float(item.weight) > 0.0
    }


def structural_gate(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    paths: Mapping[str, Path],
    inputs: Mapping[str, Any],
    mask: Mapping[str, Any],
    prepared: Mapping[str, Any],
    local_to_global: Mapping[int, int],
) -> dict[str, Any]:
    mesh = body.data
    counts = (len(mesh.vertices), len(mesh.edges), len(mesh.polygons))
    if counts != EXPECTED_RESULT_COUNTS:
        raise R20Error(f"joined result counts drifted: {counts} != {EXPECTED_RESULT_COUNTS}")
    boundaries, boundary_loops, nonmanifold = _boundary_loop_counts(mesh)
    components = _mesh_component_count(mesh)
    patch_faces = [
        polygon for polygon in mesh.polygons if int(polygon.material_index) == PATCH_MATERIAL_SLOT
    ]
    patch_incident = {int(index) for polygon in patch_faces for index in polygon.vertices}
    if len(patch_faces) != 756 or len(patch_incident) != 774:
        raise R20Error("new joined patch does not expose exact 756-face/774-incident counts")
    if boundaries != EXPECTED_BOUNDARY_EDGES or boundary_loops != EXPECTED_BOUNDARY_LOOPS:
        raise R20Error("whole-body boundary topology changed")
    if nonmanifold != 0 or components != 1:
        raise R20Error("new primary surface is disconnected or nonmanifold")

    seam_position_delta = 0.0
    seam_world_position_delta_m = 0.0
    seam_weight_delta = 0.0
    seam_uv_delta = 0.0
    for local_index in range(patch_contract.SEAM_COUNT):
        global_index = int(local_to_global[local_index])
        expected_position = prepared["positions_body_local"][local_index]
        seam_position_delta = max(
            seam_position_delta,
            math.dist(tuple(float(value) for value in mesh.vertices[global_index].co), expected_position),
        )
        actual_world = body.matrix_world @ mesh.vertices[global_index].co
        seam_world_position_delta_m = max(
            seam_world_position_delta_m,
            math.dist(actual_world, inputs["seam_project_m"][local_index]),
        )
        actual_weights = _weights_for_vertex(body, global_index)
        expected_weights = inputs["seam_weights"][local_index]
        for group in set(actual_weights) | set(expected_weights):
            seam_weight_delta = max(
                seam_weight_delta,
                abs(actual_weights.get(group, 0.0) - expected_weights.get(group, 0.0)),
            )
    for layer in mesh.uv_layers:
        expected = inputs["seam_uv"][layer.name]
        samples: defaultdict[int, list[tuple[float, float]]] = defaultdict(list)
        for polygon in patch_faces:
            for loop_index in range(int(polygon.loop_start), int(polygon.loop_start + polygon.loop_total)):
                vertex_index = int(mesh.loops[loop_index].vertex_index)
                for local_index in range(patch_contract.SEAM_COUNT):
                    if vertex_index == int(local_to_global[local_index]):
                        uv = layer.data[loop_index].uv
                        samples[local_index].append((float(uv.x), float(uv.y)))
        for local_index in range(patch_contract.SEAM_COUNT):
            if not samples[local_index]:
                raise R20Error("new patch lacks a seam UV loop")
            seam_uv_delta = max(
                seam_uv_delta,
                max(math.dist(sample, expected[local_index]) for sample in samples[local_index]),
            )
    if seam_position_delta != 0.0:
        raise R20Error(f"seam positions changed: {seam_position_delta}")
    if seam_world_position_delta_m > 1.0e-8:
        raise R20Error(
            f"seam world-meter positions changed: {seam_world_position_delta_m}"
        )
    if seam_uv_delta > 1.0e-12:
        raise R20Error(f"seam UVs changed: {seam_uv_delta}")
    if seam_weight_delta > 1.0e-12:
        raise R20Error(f"seam weights changed: {seam_weight_delta}")

    new_weight_records = []
    for local_index in range(patch_contract.SEAM_COUNT, patch_contract.TOTAL_PATCH_INCIDENT_VERTICES):
        global_index = int(local_to_global[local_index])
        record = _weights_for_vertex(body, global_index)
        if not record or len(record) > 4 or not math.isclose(
            sum(record.values()), 1.0, rel_tol=0.0, abs_tol=1.0e-6
        ):
            raise R20Error(f"invalid new-vertex weight record at local {local_index}: {record}")
        if set(record) - {bone.name for bone in rig.data.bones}:
            raise R20Error("new patch weight references a non-native bone")
        new_weight_records.append(record)

    preserved_after = preserved_primary_snapshot(body)
    before = inputs["preserved_snapshot"]
    if preserved_after["complete_snapshot_sha256"] != before["complete_snapshot_sha256"]:
        raise R20Error(
            "preserved primary-surface subset changed: "
            + json.dumps(
                {
                    "before": before,
                    "after": preserved_after,
                },
                sort_keys=True,
            )
        )
    attribute_normal_gate = _current_patch_attribute_normal_gate(body)
    global_before = inputs["global_state"]
    global_after = {
        "rig_rest_structure_sha256": rig_rest_signature(rig),
        "actions_sha256": action_digest(),
        "materials_sha256": material_graph_digest(),
        "body_matrix_world_sha256": _matrix_digest(body.matrix_world),
        "body_modifiers_sha256": sha256_json(modifier_record(body)),
    }
    if global_after != global_before:
        raise R20Error(f"rig/action/material/object state changed: {global_after} != {global_before}")
    freeze_after = validate_freeze_ledger(
        body,
        rig,
        paths["r20_freeze_ledger"],
        paths["freeze_identity_correction"],
        require_source_primary_hashes=False,
    )
    semantic_names = {
        _semantic_attribute_name(name) for name in patch_contract.landmark_vertex_sets()
    }
    actual_semantic = {
        attribute.name
        for attribute in mesh.attributes
        if attribute.name.startswith(LANDMARK_ATTRIBUTE_PREFIX)
    }
    if actual_semantic != semantic_names:
        raise R20Error("external landmark semantic attribute set drifted")
    return {
        "primary_surface_counts": {
            "vertices": counts[0],
            "edges": counts[1],
            "faces": counts[2],
            "connected_components": components,
            "boundary_edges": boundaries,
            "boundary_loops": boundary_loops,
            "nonmanifold_edges": nonmanifold,
        },
        "new_patch": {
            "faces": len(patch_faces),
            "incident_vertices": len(patch_incident),
            "all_faces_are_quads": all(len(polygon.vertices) == 4 for polygon in patch_faces),
            "maximum_quad_edge_ratio": prepared["evidence"]["geometry_quality"]["maximum_quad_edge_ratio"],
            "minimum_face_area_m2": prepared["evidence"]["geometry_quality"]["minimum_face_area_m2"],
            "maximum_vertex_valence": prepared["evidence"]["topology"]["maximum_vertex_valence"],
        },
        "seam": {
            "maximum_body_local_position_delta": seam_position_delta,
            "maximum_world_position_delta_m": seam_world_position_delta_m,
            "maximum_uv_delta": seam_uv_delta,
            "maximum_weight_delta": seam_weight_delta,
        },
        "new_weights": {
            "vertex_count": len(new_weight_records),
            "unweighted_vertices": 0,
            "maximum_positive_influences": max(len(record) for record in new_weight_records),
            "all_sums_one_within_1e_6": True,
            "records_sha256": sha256_json(new_weight_records),
        },
        "preserved_primary_subset": preserved_after,
        "localized_attribute_and_normal_gate": attribute_normal_gate,
        "global_state": global_after,
        "freeze_after": freeze_after,
        "landmark_attribute_names": sorted(actual_semantic),
        "all_hard_structural_gates_passed": True,
    }


def _canonical_bm_face_key(face: bmesh.types.BMFace) -> str:
    coordinates = [_coordinate_key(vertex.co) for vertex in face.verts]
    return sha256_json(
        {
            "coordinates": _cycle_rotation(coordinates),
            "material_index": int(face.material_index),
        }
    )


def _evaluated_world_bmesh(obj: bpy.types.Object) -> tuple[bmesh.types.BMesh, Any]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bmesh.ops.transform(bm, matrix=evaluated.matrix_world, verts=list(bm.verts))
        bm.faces.ensure_lookup_table()
        bm.faces.index_update()
        bm.normal_update()
    except Exception:
        bm.free()
        evaluated.to_mesh_clear()
        raise
    return bm, evaluated


def exact_self_intersection_classification(body: bpy.types.Object) -> dict[str, Any]:
    bm, evaluated = _evaluated_world_bmesh(body)
    try:
        report = exact_intersections.exact_nonadjacent_intersection_report(
            bm, include_pair_details=True
        )
        patch_related = []
        nonpatch_keys = []
        all_genuine = []
        for record in report["pairs"]:
            if not record.get("genuine_positive_area_or_segment_penetration"):
                continue
            first_index, second_index = (int(value) for value in record["face_indices"])
            first = bm.faces[first_index]
            second = bm.faces[second_index]
            row = {
                "face_indices": [first_index, second_index],
                "first_material_index": int(first.material_index),
                "second_material_index": int(second.material_index),
                "first_face_key": _canonical_bm_face_key(first),
                "second_face_key": _canonical_bm_face_key(second),
                "body_region": record.get("body_region"),
                "combined_bounds": record.get("combined_bounds"),
            }
            all_genuine.append(row)
            if PATCH_MATERIAL_SLOT in (int(first.material_index), int(second.material_index)):
                patch_related.append(row)
            else:
                nonpatch_keys.append(tuple(sorted((row["first_face_key"], row["second_face_key"]))))
        return {
            "exact_genuine_pair_count": len(all_genuine),
            "patch_related_exact_pair_count": len(patch_related),
            "nonpatch_exact_pair_count": len(nonpatch_keys),
            "nonpatch_pair_keys": sorted(set(nonpatch_keys)),
            "patch_related_pairs": patch_related,
            "raw_summary": {
                key: value for key, value in report.items() if key != "pairs"
            },
        }
    finally:
        bm.free()
        evaluated.to_mesh_clear()


def _evaluated_world_triangles(
    obj: bpy.types.Object,
    *,
    patch_only: bool,
) -> tuple[list[Vector], list[tuple[int, int, int]], Any]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    triangles = [
        tuple(int(index) for index in triangle.vertices)
        for triangle in mesh.loop_triangles
        if not patch_only
        or int(mesh.polygons[int(triangle.polygon_index)].material_index) == PATCH_MATERIAL_SLOT
    ]
    return points, triangles, evaluated


def exact_cross_intersections(
    body: bpy.types.Object,
    objects: Sequence[bpy.types.Object],
    *,
    patch_only: bool,
) -> dict[str, Any]:
    body_points, body_triangles, body_evaluated = _evaluated_world_triangles(
        body, patch_only=patch_only
    )
    body_tree = BVHTree.FromPolygons(body_points, body_triangles, all_triangles=True)
    diagonal = (
        Vector(tuple(max(float(point[axis]) for point in body_points) for axis in range(3)))
        - Vector(tuple(min(float(point[axis]) for point in body_points) for axis in range(3)))
    ).length
    tolerance = max(1.0e-10, float(diagonal) * 1.0e-8)
    records = []
    total = 0
    try:
        for obj in objects:
            points, triangles, evaluated = _evaluated_world_triangles(obj, patch_only=False)
            try:
                tree = BVHTree.FromPolygons(points, triangles, all_triangles=True)
                overlaps = body_tree.overlap(tree)
                genuine = 0
                for body_index, object_index in overlaps:
                    result = exact_intersections.classify_triangle_pair(
                        tuple(body_points[index] for index in body_triangles[body_index]),
                        tuple(points[index] for index in triangles[object_index]),
                        linear_tolerance=tolerance,
                    )
                    if result.get("genuine_penetration") is True:
                        genuine += 1
                total += genuine
                records.append(
                    {
                        "object": obj.name,
                        "bvh_triangle_pair_count": len(overlaps),
                        "exact_genuine_triangle_pair_count": genuine,
                    }
                )
            finally:
                evaluated.to_mesh_clear()
    finally:
        body_evaluated.to_mesh_clear()
    return {
        "patch_only": patch_only,
        "object_count": len(objects),
        "exact_genuine_triangle_pair_count": total,
        "records": records,
        "method": "evaluated-mesh BVH broad phase plus exact triangle narrow phase",
    }


def _freeze_objects_by_role(paths: Mapping[str, Path]) -> tuple[list[bpy.types.Object], list[bpy.types.Object]]:
    ledger = json.loads(paths["r20_freeze_ledger"].read_text(encoding="utf-8"))
    correction = json.loads(
        paths["freeze_identity_correction"].read_text(encoding="utf-8")
    )
    historical = correction["root_cause"]["sole_historical_nonpersisted_record"]
    persisted_records = [
        record
        for record in ledger["separate_mesh_objects_required_exact"]
        if record != historical
    ]
    if len(persisted_records) != 31:
        raise R20Error("corrected freeze role lookup does not contain exact 31 records")
    objects = [
        bpy.data.objects.get(str(record["object"]))
        for record in persisted_records
    ]
    if any(obj is None for obj in objects):
        raise R20Error("freeze-ledger object lookup failed")
    nails = [
        obj
        for obj in objects
        if "fingernail" in obj.name.lower() or "toenail" in obj.name.lower()
    ]
    eyes = [
        obj
        for obj in objects
        if any(token in canonical_blender_name(obj.data.name).lower() for token in ("pupil", "cornea", "irise", "sclera"))
    ]
    if len(nails) != 20 or not eyes:
        raise R20Error(f"expected 20 nails and named eye components, found {len(nails)}/{len(eyes)}")
    return nails, eyes


def _evaluated_coordinate_digest(body: bpy.types.Object) -> str:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        digest = hashlib.sha256()
        for vertex in mesh.vertices:
            point = evaluated.matrix_world @ vertex.co
            digest.update(struct.pack("<3d", *(float(value) for value in point)))
        return digest.hexdigest()
    finally:
        evaluated.to_mesh_clear()


def _pose_snapshot(rig: bpy.types.Object) -> dict[str, Any]:
    animation = rig.animation_data
    return {
        "frame": int(bpy.context.scene.frame_current),
        "subframe": float(bpy.context.scene.frame_subframe),
        "action": animation.action if animation else None,
        "action_slot": getattr(animation, "action_slot", None) if animation else None,
        "nla_mute": [bool(track.mute) for track in animation.nla_tracks] if animation else [],
        "bones": {
            bone.name: {
                "matrix_basis": bone.matrix_basis.copy(),
                "rotation_mode": bone.rotation_mode,
            }
            for bone in rig.pose.bones
        },
    }


def _reset_pose(rig: bpy.types.Object) -> None:
    rig.animation_data_create()
    rig.animation_data.action = None
    for track in rig.animation_data.nla_tracks:
        track.mute = True
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


def _restore_pose(rig: bpy.types.Object, snapshot: Mapping[str, Any]) -> None:
    animation = rig.animation_data
    if animation is None:
        raise R20Error("rig animation data disappeared during pose evaluation")
    animation.action = snapshot["action"]
    if snapshot.get("action_slot") is not None and hasattr(animation, "action_slot"):
        try:
            animation.action_slot = snapshot["action_slot"]
        except (TypeError, RuntimeError):
            pass
    for track, mute in zip(animation.nla_tracks, snapshot["nla_mute"]):
        track.mute = bool(mute)
    for name, record in snapshot["bones"].items():
        bone = rig.pose.bones.get(name)
        if bone is None:
            raise R20Error(f"pose bone disappeared: {name}")
        bone.rotation_mode = record["rotation_mode"]
        bone.matrix_basis = record["matrix_basis"]
    bpy.context.scene.frame_set(int(snapshot["frame"]), subframe=float(snapshot["subframe"]))
    bpy.context.view_layer.update()


@contextmanager
def evaluated_pose(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    pose: Mapping[str, Any],
) -> Iterator[dict[str, Any]]:
    snapshot = _pose_snapshot(rig)
    before_digest = _evaluated_coordinate_digest(body)
    restoration = {"before_neutral_evaluated_sha256": before_digest}
    try:
        _reset_pose(rig)
        action_name = pose.get("action")
        if action_name:
            action = bpy.data.actions.get(str(action_name))
            if action is None:
                raise R20Error(f"required frozen action is missing: {action_name}")
            rig.animation_data.action = action
            bpy.context.scene.frame_set(POSE_FRAME)
        for side, degrees in pose.get("knees", {}).items():
            bone_name = KNEE_BONES[str(side)]
            bone = rig.pose.bones.get(bone_name)
            if bone is None:
                raise R20Error(f"required knee bone is missing: {bone_name}")
            bone.rotation_mode = "XYZ"
            bone.rotation_euler.x = math.radians(float(degrees))
        bpy.context.view_layer.update()
        yield restoration
    finally:
        _restore_pose(rig, snapshot)
        after_digest = _evaluated_coordinate_digest(body)
        restoration["after_neutral_evaluated_sha256"] = after_digest
        restoration["exact"] = after_digest == before_digest
        if after_digest != before_digest:
            raise R20Error(
                f"pose restoration failed: {after_digest} != {before_digest}"
            )


def required_pose_states() -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = [{"id": "neutral_standing"}]
    for degrees in (30, 55, 80):
        states.extend(
            (
                {"id": f"left_knee_{degrees}", "knees": {"left": degrees}},
                {"id": f"right_knee_{degrees}", "knees": {"right": degrees}},
                {
                    "id": f"bilateral_knee_{degrees}",
                    "knees": {"left": degrees, "right": degrees},
                },
            )
        )
    states.extend(
        (
            {"id": "bounded_hip_open_diagnostic", "action": SELECTED_SEATED_ACTION},
            {"id": "selected_seated_open_hip", "action": SELECTED_SEATED_ACTION},
            {"id": "toilet_seated_diagnostic_contact", "action": SELECTED_SEATED_ACTION},
            {"id": "selected_supine", "action": SELECTED_SUPINE_ACTION},
        )
    )
    return states


def _patch_world_points(body: bpy.types.Object) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        patch_ids = {
            int(index)
            for polygon in mesh.polygons
            if int(polygon.material_index) == PATCH_MATERIAL_SLOT
            for index in polygon.vertices
        }
        return [evaluated.matrix_world @ mesh.vertices[index].co for index in sorted(patch_ids)]
    finally:
        evaluated.to_mesh_clear()


def evaluated_patch_quality(body: bpy.types.Object) -> dict[str, Any]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        areas = []
        folded = 0
        patch_faces = [
            polygon for polygon in mesh.polygons if int(polygon.material_index) == PATCH_MATERIAL_SLOT
        ]
        for polygon in patch_faces:
            if len(polygon.vertices) != 4:
                raise R20Error("evaluated R20 patch contains a non-quad")
            points = [evaluated.matrix_world @ mesh.vertices[int(index)].co for index in polygon.vertices]
            first_normal = (points[1] - points[0]).cross(points[2] - points[0])
            second_normal = (points[2] - points[0]).cross(points[3] - points[0])
            first_area = 0.5 * first_normal.length
            second_area = 0.5 * second_normal.length
            areas.append(first_area + second_area)
            if first_normal.length <= 2.0e-10 or second_normal.length <= 2.0e-10:
                folded += 1
            elif first_normal.normalized().dot(second_normal.normalized()) <= 0.0:
                folded += 1
        return {
            "patch_face_count": len(patch_faces),
            "minimum_face_area_m2": min(areas, default=0.0),
            "collapsed_or_inverted_quad_count": folded,
            "passes": len(patch_faces) == 756 and min(areas, default=0.0) > 1.0e-10 and folded == 0,
        }
    finally:
        evaluated.to_mesh_clear()


def evaluated_external_landmarks(body: bpy.types.Object) -> dict[str, Any]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        records = {}
        for name in patch_contract.landmark_vertex_sets():
            attribute_name = _semantic_attribute_name(name)
            attribute = mesh.attributes.get(attribute_name)
            if attribute is None or str(attribute.domain) != "POINT":
                raise R20Error(f"evaluated landmark hook missing: {attribute_name}")
            indices = [index for index, item in enumerate(attribute.data) if bool(item.value)]
            if not indices:
                raise R20Error(f"evaluated landmark set is empty: {attribute_name}")
            points = [evaluated.matrix_world @ mesh.vertices[index].co for index in indices]
            centroid = sum(points, Vector()) / len(points)
            records[name] = {
                "attribute": attribute_name,
                "vertex_count": len(indices),
                "project_space_centroid_m": vector_record(centroid),
            }
        return {
            "records": records,
            "required_longitudinal_order": list(patch_contract.EXTERNAL_LANDMARK_ORDER),
            "all_named_sets_present": True,
            "external_surface_semantics_only": True,
            "visibility_requires_review_render": True,
        }
    finally:
        evaluated.to_mesh_clear()


def toilet_seat_clearance_metrics(
    body: bpy.types.Object,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    points = _patch_world_points(body)
    seat = config["toilet_seat"]
    center_x = 0.5 * (R19_SELECTED_SEAT["x_min_m"] + R19_SELECTED_SEAT["x_max_m"])
    center_y = 0.5 * (R19_SELECTED_SEAT["y_min_m"] + R19_SELECTED_SEAT["y_max_m"])
    outer_half_x = float(seat["outer_width_m"]) * 0.5
    outer_half_y = float(seat["outer_depth_m"]) * 0.5
    opening_half_x = float(seat["opening_width_m"]) * 0.5
    opening_half_y = float(seat["opening_depth_m"]) * 0.5
    top_z = float(R19_SELECTED_SEAT["top_z_m"])
    tolerance = float(seat["penetration_tolerance_m"])
    rim_points = []
    inside_opening = []
    for point in points:
        dx = float(point.x) - center_x
        dy = float(point.y) - center_y
        in_outer = abs(dx) <= outer_half_x and abs(dy) <= outer_half_y
        in_opening = (dx / opening_half_x) ** 2 + (dy / opening_half_y) ** 2 <= 1.0
        if in_opening:
            inside_opening.append(point)
        elif in_outer:
            rim_points.append(point)
    signed_rim_gaps = [float(point.z) - top_z for point in rim_points]
    penetrations = [gap for gap in signed_rim_gaps if gap < -tolerance]
    minimum_gap = min(signed_rim_gaps, default=math.inf)
    required_clearance = float(seat["clearance_minimum_m"])
    return {
        "reference": "exact selected R19 seated-open-hip seat bounds plus configured bounded toilet opening",
        "seat_top_z_m": top_z,
        "seat_center_xy_m": [center_x, center_y],
        "outer_size_m": [float(seat["outer_width_m"]), float(seat["outer_depth_m"])],
        "opening_size_m": [float(seat["opening_width_m"]), float(seat["opening_depth_m"])],
        "patch_vertex_count": len(points),
        "patch_vertices_inside_opening": len(inside_opening),
        "patch_vertices_over_solid_rim": len(rim_points),
        "minimum_signed_patch_to_rim_gap_m": None if math.isinf(minimum_gap) else minimum_gap,
        "maximum_penetration_depth_m": max((-gap for gap in penetrations), default=0.0),
        "penetrating_patch_vertex_count": len(penetrations),
        "minimum_configured_clearance_m": required_clearance,
        "no_patch_to_seat_penetration": not penetrations,
        "clearance_at_least_minimum_or_patch_inside_opening": (
            not rim_points or minimum_gap >= required_clearance
        ),
        "contact_and_clearance_measurement_only": True,
    }


def run_pose_suite(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    paths: Mapping[str, Path],
    config: Mapping[str, Any],
    *,
    baseline_by_pose: Mapping[str, Any] | None,
) -> dict[str, Any]:
    nails, eyes = _freeze_objects_by_role(paths)
    results = {}
    action_before = action_digest()
    rig_before = rig_rest_signature(rig)
    candidate_patch_present = baseline_by_pose is not None
    for pose in required_pose_states():
        with evaluated_pose(body, rig, pose) as restoration:
            self_report = exact_self_intersection_classification(body)
            body_nails = exact_cross_intersections(body, nails, patch_only=False)
            if candidate_patch_present:
                patch_external = exact_cross_intersections(
                    body, nails + eyes, patch_only=True
                )
                patch_quality = evaluated_patch_quality(body)
                landmarks = evaluated_external_landmarks(body)
            else:
                # The sealed R19 source still contains the rejected 376-face
                # panel in the shared regional material slot.  It is not the
                # generated 756-quad R20 patch and has no R20 landmark attrs.
                # Baseline collection therefore records only comparable R19
                # intersection/contact truth.  Every candidate-only gate runs
                # below after _apply_local_patch, when baseline_by_pose is set.
                patch_external = {
                    "status": "NOT_EVALUATED_SOURCE_R19_BASELINE_NO_R20_PATCH",
                    "patch_only": True,
                    "evaluated": False,
                }
                patch_quality = {
                    "status": "NOT_EVALUATED_SOURCE_R19_BASELINE_NO_R20_PATCH",
                    "evaluated": False,
                    "all_quad_gate_deferred_until_candidate_patch_exists": True,
                }
                landmarks = {
                    "status": "NOT_EVALUATED_SOURCE_R19_BASELINE_NO_R20_PATCH",
                    "evaluated": False,
                    "candidate_landmark_gate_deferred_until_candidate_patch_exists": True,
                }
            record = {
                "pose": pose,
                "self_intersections": self_report,
                "patch_to_nails_and_eyes": patch_external,
                "body_to_nails": body_nails,
                "evaluated_patch_quality": patch_quality,
                "external_landmarks": landmarks,
                "neutral_restoration": restoration,
            }
            if pose["id"] == "toilet_seated_diagnostic_contact":
                record["toilet_seat_contact_and_clearance"] = toilet_seat_clearance_metrics(
                    body, config
                )
            if baseline_by_pose is not None:
                baseline = baseline_by_pose[pose["id"]]
                additions = sorted(
                    set(tuple(value) for value in self_report["nonpatch_pair_keys"])
                    - set(tuple(value) for value in baseline["self_intersections"]["nonpatch_pair_keys"])
                )
                gates = {
                    "new_patch_related_exact_pairs_zero": self_report["patch_related_exact_pair_count"] == 0,
                    "new_nonpatch_pair_additions_zero": not additions,
                    "patch_to_nails_and_eyes_zero": patch_external["exact_genuine_triangle_pair_count"] == 0,
                    "body_to_nails_zero": body_nails["exact_genuine_triangle_pair_count"] == 0,
                    "no_collapsed_or_inverted_patch_quad": patch_quality["passes"],
                    "all_external_landmark_sets_present": landmarks["all_named_sets_present"],
                    "nonpatch_pair_additions": additions,
                }
                if "toilet_seat_contact_and_clearance" in record:
                    toilet = record["toilet_seat_contact_and_clearance"]
                    gates["toilet_patch_penetration_zero"] = toilet["no_patch_to_seat_penetration"]
                    gates["toilet_clearance_gate"] = toilet[
                        "clearance_at_least_minimum_or_patch_inside_opening"
                    ]
                if not all(
                    value is True
                    for key, value in gates.items()
                    if key != "nonpatch_pair_additions"
                ):
                    raise R20Error(f"pose gate failed for {pose['id']}: {gates}")
                record["gates"] = gates
            results[pose["id"]] = record
    if action_digest() != action_before or rig_rest_signature(rig) != rig_before:
        raise R20Error("pose suite altered a frozen action or rig rest structure")
    if baseline_by_pose is None:
        neutral = results["neutral_standing"]["self_intersections"]
        if neutral["exact_genuine_pair_count"] != EXPECTED_SOURCE_SELF_INTERSECTIONS:
            raise R20Error(
                f"R19 neutral intersection baseline drifted: {neutral['exact_genuine_pair_count']}"
            )
    return {
        "state_count": len(results),
        "states": results,
        "candidate_patch_present": candidate_patch_present,
        "candidate_only_patch_gates_evaluated": candidate_patch_present,
        "actions_sha256_before_after": action_before,
        "rig_rest_sha256_before_after": rig_before,
        "all_required_states_evaluated": len(results) == len(required_pose_states()),
    }


def _open_exact_blend(path: Path) -> None:
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)


def _object_inventory() -> list[dict[str, Any]]:
    return [
        {
            "name": obj.name,
            "type": obj.type,
            "data": canonical_blender_name(obj.data.name) if obj.data is not None else None,
        }
        for obj in sorted(bpy.data.objects, key=lambda value: value.name)
    ]


def _candidate_config(config: Mapping[str, Any], candidate_id: str) -> Mapping[str, Any]:
    for record in config["candidates"]:
        if record["candidate_id"] == candidate_id:
            return record
    raise R20Error(f"candidate config is missing: {candidate_id}")


def _author_candidate(
    config: Mapping[str, Any],
    paths: Mapping[str, Path],
    candidate_id: str,
    candidate_dir: Path,
) -> dict[str, Any]:
    _open_exact_blend(paths["source_blend"])
    body, rig, preflight, inputs = preflight_scene(config, paths)
    source_inventory = _object_inventory()
    baseline_pose_suite = run_pose_suite(
        body,
        rig,
        paths,
        config,
        baseline_by_pose=None,
    )
    prepared = _prepare_candidate_fields(body, rig, preflight["mask"], inputs, candidate_id)
    local_to_global, edit = _apply_local_patch(
        body,
        rig,
        preflight["mask"],
        prepared,
    )
    structural = structural_gate(
        body,
        rig,
        paths,
        inputs,
        preflight["mask"],
        prepared,
        local_to_global,
    )
    pose_suite = run_pose_suite(
        body,
        rig,
        paths,
        config,
        baseline_by_pose=baseline_pose_suite["states"],
    )
    if _object_inventory() != source_inventory:
        raise R20Error("object inventory changed; R20 may not create a separate anatomy object")
    if action_digest() != preflight["global_state"]["actions_sha256"]:
        raise R20Error("actions changed before candidate save")
    if rig_rest_signature(rig) != preflight["global_state"]["rig_rest_structure_sha256"]:
        raise R20Error("rig rest structure changed before candidate save")

    candidate_record = _candidate_config(config, candidate_id)
    blend_path = candidate_dir / str(candidate_record["blend_filename"])
    if blend_path.exists():
        raise R20Error(f"refusing to overwrite candidate Blend: {blend_path}")
    body["r20_structural_acceptance_passed"] = True
    body["r20_pose_acceptance_passed"] = True
    body["r20_visual_owner_approval_pending"] = True
    scene = bpy.context.scene
    scene["r20_candidate_id"] = candidate_id
    scene["r20_private_owner_review_only"] = True
    scene["r20_inactive_unassigned_unpublished"] = True
    scene["r20_owner_approved"] = False
    scene["r20_runtime_activation_allowed"] = False
    _save_candidate_once(blend_path)
    blend_hash = sha256_file(blend_path)
    evidence = {
        "schema_version": 1,
        "worker_id": WORKER_ID,
        "timestamp_utc": utc_now(),
        "status": "STRUCTURAL_AND_POSE_GATES_PASSED_PENDING_FRESH_PROCESS_RENDER_AND_OWNER_VISUAL_REVIEW",
        "candidate_id": candidate_id,
        "private": True,
        "inactive": True,
        "unassigned": True,
        "unpublished": True,
        "runtime_eligible": False,
        "owner_approved": False,
        "blend": {
            "path": project_relative(blend_path),
            "sha256": blend_hash,
            "size_bytes": blend_path.stat().st_size,
        },
        "source_preflight": preflight,
        "exact_seam_weights": inputs["seam_weights"],
        "exact_seam_uv": inputs["seam_uv"],
        "prepared_patch": prepared["evidence"],
        "local_to_saved_global_vertex_index": {
            str(key): int(value) for key, value in sorted(local_to_global.items())
        },
        "localized_edit": edit,
        "structural_acceptance": structural,
        "source_pose_baselines": baseline_pose_suite,
        "candidate_pose_acceptance": pose_suite,
        "visual_rejection_conditions_to_compare": [
            "broad inverted trapezoid or triangular panel",
            "straight superior edge",
            "sharp diagonal borders",
            "central dark cavity or crease",
            "missing readable hood/glans, urethral meatus, introitus, fourchette/perineum, and separate anal relationship",
        ],
        "visual_gate_passed": False,
        "owner_visual_approval_required": True,
        "face_head_eyes_brows_upper_body_changed": False,
        "separate_anatomy_objects": 0,
        "internal_function_claimed": False,
        "toilet_metrics_are_contact_and_clearance_only": True,
        "body_activated_or_assigned": False,
        "exported_or_published": False,
    }
    evidence_path = candidate_dir / "AUTHORING_EVIDENCE.json"
    write_json_exclusive(evidence_path, evidence)
    return {
        "candidate_id": candidate_id,
        "status": evidence["status"],
        "blend": evidence["blend"],
        "authoring_evidence": {
            "path": project_relative(evidence_path),
            "sha256": sha256_file(evidence_path),
            "size_bytes": evidence_path.stat().st_size,
        },
    }


def _save_candidate_once(path: Path) -> None:
    """The sole save call site; reached only after every in-memory hard gate."""
    bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False)


def run_preflight_mode(
    config: Mapping[str, Any],
    paths: Mapping[str, Path],
) -> dict[str, Any]:
    output = paths["preflight_output"]
    if output.exists():
        raise R20Error(f"append-only preflight output already exists: {output}")
    output.mkdir(parents=True, exist_ok=False)
    _open_exact_blend(paths["source_blend"])
    _body, _rig, preflight, _inputs = preflight_scene(config, paths)
    path = output / "PREFLIGHT_EVIDENCE.json"
    write_json_exclusive(path, preflight)
    checkpoint = output / "CHECKPOINT.md"
    write_text_exclusive(
        checkpoint,
        "# Kira R20 authoring preflight\n\n"
        "Status: PASS — no mesh mutation and no Blend save.\n\n"
        f"- Evidence: `{project_relative(path)}`\n"
        f"- Evidence SHA-256: `{sha256_file(path)}`\n"
        f"- Source R19 SHA-256: `{SOURCE_BLEND_SHA256}`\n"
        "- Candidate state: not created; private/inactive policy retained.\n",
    )
    manifest_path = output / "PACKAGE_MANIFEST.json"
    members = []
    for member in sorted(path for path in output.rglob("*") if path.is_file()):
        if member == manifest_path:
            continue
        members.append(
            {
                "path": project_relative(member),
                "sha256": sha256_file(member),
                "size_bytes": member.stat().st_size,
            }
        )
    write_json_exclusive(
        manifest_path,
        {
            "schema_version": 1,
            "status": "PREFLIGHT_ONLY_NO_BODY_MUTATION",
            "files_excluding_this_manifest": members,
        },
    )
    return {
        "status": "PASS_PREFLIGHT_ONLY_NO_BODY_MUTATION",
        "output": project_relative(output),
        "manifest_sha256": sha256_file(manifest_path),
    }


def run_author_mode(
    config: Mapping[str, Any],
    paths: Mapping[str, Path],
) -> dict[str, Any]:
    output = paths["author_output"]
    if output.exists():
        raise R20Error(f"append-only authoring output already exists: {output}")
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for candidate in patch_contract.CANDIDATES:
        candidate_dir = output / candidate.candidate_id
        candidate_dir.mkdir(parents=False, exist_ok=False)
        try:
            results.append(
                _author_candidate(config, paths, candidate.candidate_id, candidate_dir)
            )
        except Exception as exc:
            failure = {
                "schema_version": 1,
                "worker_id": WORKER_ID,
                "timestamp_utc": utc_now(),
                "candidate_id": candidate.candidate_id,
                "status": "BOUNDED_CANDIDATE_REJECTED_NO_BLEND_SAVED",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "source_r19_unchanged": sha256_file(paths["source_blend"]) == SOURCE_BLEND_SHA256,
            }
            write_json_exclusive(candidate_dir / "FAILURE_EVIDENCE.json", failure)
            results.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "status": failure["status"],
                    "failure_evidence": {
                        "path": project_relative(candidate_dir / "FAILURE_EVIDENCE.json"),
                        "sha256": sha256_file(candidate_dir / "FAILURE_EVIDENCE.json"),
                    },
                }
            )
    summary = {
        "schema_version": 1,
        "worker_id": WORKER_ID,
        "timestamp_utc": utc_now(),
        "status": "AUTHORING_COMPLETE_PENDING_FRESH_PROCESS_VERIFICATION_AND_OWNER_REVIEW",
        "bounded_candidate_count": 2,
        "results": results,
        "successful_candidate_count": sum("blend" in record for record in results),
        "source_r19_sha256_after": sha256_file(paths["source_blend"]),
        "source_r19_unchanged": sha256_file(paths["source_blend"]) == SOURCE_BLEND_SHA256,
        "no_runtime_activation_assignment_export_publication": True,
    }
    write_json_exclusive(output / "AUTHORING_SUMMARY.json", summary)
    if not summary["successful_candidate_count"]:
        raise R20Error("both bounded candidates failed; evidence preserved and no Blend saved")
    return summary


def _cyclic_face(values: Sequence[int]) -> tuple[int, ...]:
    rows = tuple(int(value) for value in values)
    return min(rows[index:] + rows[:index] for index in range(len(rows)))


def verify_saved_structure(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    paths: Mapping[str, Path],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    mesh = body.data
    counts = (len(mesh.vertices), len(mesh.edges), len(mesh.polygons))
    if counts != EXPECTED_RESULT_COUNTS:
        raise R20Error("saved candidate whole-body counts drifted")
    boundaries, loops, nonmanifold = _boundary_loop_counts(mesh)
    if (boundaries, loops, nonmanifold, _mesh_component_count(mesh)) != (
        EXPECTED_BOUNDARY_EDGES,
        EXPECTED_BOUNDARY_LOOPS,
        0,
        1,
    ):
        raise R20Error("saved candidate topology is not the sealed joined result")
    candidate_id = str(evidence["candidate_id"])
    reverse = bool(evidence["prepared_patch"]["reverse_winding"])
    expected_faces = {
        _cyclic_face(face)
        for face in patch_contract.build_quad_topology(reverse_winding=reverse)
    }
    local_to_global = {
        int(key): int(value)
        for key, value in evidence["local_to_saved_global_vertex_index"].items()
    }
    global_to_local = {value: key for key, value in local_to_global.items()}
    if len(local_to_global) != 774 or len(global_to_local) != 774:
        raise R20Error("saved local/global patch mapping is incomplete or duplicated")
    patch_faces = [
        polygon for polygon in mesh.polygons if int(polygon.material_index) == PATCH_MATERIAL_SLOT
    ]
    actual_faces = set()
    for polygon in patch_faces:
        try:
            local = [global_to_local[int(index)] for index in polygon.vertices]
        except KeyError as exc:
            raise R20Error("saved patch references a vertex outside its sealed mapping") from exc
        actual_faces.add(_cyclic_face(local))
    if actual_faces != expected_faces or len(patch_faces) != 756:
        raise R20Error("saved patch connectivity differs from the golden all-quad topology")
    positions_body_local = [
        tuple(float(value) for value in mesh.vertices[local_to_global[index]].co)
        for index in range(patch_contract.TOTAL_PATCH_INCIDENT_VERTICES)
    ]
    positions_project_m = [
        tuple(float(value) for value in (body.matrix_world @ Vector(position)))
        for position in positions_body_local
    ]
    quality = patch_contract.geometry_quality(
        positions_project_m, patch_contract.build_quad_topology(reverse_winding=reverse)
    )
    if (
        int(quality["degenerate_face_count_at_1e_10_m2"]) != 0
        or float(quality["maximum_quad_edge_ratio"]) > 3.0
    ):
        raise R20Error(f"saved patch project-meter geometry quality failed: {quality}")
    quality["coordinate_space"] = "project_world_meters"
    preserved = preserved_primary_snapshot(body)
    expected_preserved = evidence["source_preflight"]["preserved_primary_snapshot"]
    if preserved["complete_snapshot_sha256"] != expected_preserved["complete_snapshot_sha256"]:
        raise R20Error("saved nonpelvic primary-surface subset changed")
    attribute_normal_gate = _current_patch_attribute_normal_gate(body)
    freeze = validate_freeze_ledger(
        body,
        rig,
        paths["r20_freeze_ledger"],
        paths["freeze_identity_correction"],
        require_source_primary_hashes=False,
    )
    global_expected = evidence["source_preflight"]["global_state"]
    global_actual = {
        "rig_rest_structure_sha256": rig_rest_signature(rig),
        "actions_sha256": action_digest(),
        "materials_sha256": material_graph_digest(),
        "body_matrix_world_sha256": _matrix_digest(body.matrix_world),
        "body_modifiers_sha256": sha256_json(modifier_record(body)),
    }
    if global_actual != global_expected:
        raise R20Error("saved rig/actions/materials/object transform or modifiers changed")
    seam_position_delta = 0.0
    seam_weight_delta = 0.0
    seam_uv_delta = 0.0
    expected_world = evidence["source_preflight"]["mask"]["canonical_seam_world_coordinates"]
    for local_index in range(patch_contract.SEAM_COUNT):
        global_index = local_to_global[local_index]
        world = body.matrix_world @ mesh.vertices[global_index].co
        seam_position_delta = max(seam_position_delta, math.dist(world, expected_world[local_index]))
        actual_weights = _weights_for_vertex(body, global_index)
        expected_weights = evidence["exact_seam_weights"][local_index]
        seam_weight_delta = max(
            seam_weight_delta,
            max(
                abs(actual_weights.get(group, 0.0) - expected_weights.get(group, 0.0))
                for group in set(actual_weights) | set(expected_weights)
            ),
        )
    for layer in mesh.uv_layers:
        expected_layer = evidence["exact_seam_uv"][layer.name]
        for polygon in patch_faces:
            for loop_index in range(int(polygon.loop_start), int(polygon.loop_start + polygon.loop_total)):
                vertex_index = int(mesh.loops[loop_index].vertex_index)
                local_index = global_to_local[vertex_index]
                if local_index < patch_contract.SEAM_COUNT:
                    uv = layer.data[loop_index].uv
                    seam_uv_delta = max(
                        seam_uv_delta,
                        math.dist((float(uv.x), float(uv.y)), expected_layer[local_index]),
                    )
    if seam_position_delta > 1.0e-8 or seam_weight_delta > 1.0e-12 or seam_uv_delta > 1.0e-12:
        raise R20Error("saved seam position, weight, or UV contract failed")
    expected_properties = {
        "r20_candidate_id": candidate_id,
        "r20_private_owner_review_only": True,
        "r20_inactive": True,
        "r20_unassigned": True,
        "r20_unpublished": True,
        "r20_runtime_eligible": False,
        "r20_owner_approved": False,
        "r20_scalp_hair_dependency": False,
        "r20_external_surface_only": True,
    }
    for key, value in expected_properties.items():
        if body.get(key) != value:
            raise R20Error(f"saved private/inactive property drifted: {key}")
    return {
        "candidate_id": candidate_id,
        "counts": {
            "vertices": counts[0],
            "edges": counts[1],
            "faces": counts[2],
            "boundary_edges": boundaries,
            "boundary_loops": loops,
            "nonmanifold_edges": nonmanifold,
            "connected_components": 1,
        },
        "topology_connectivity_sha256": patch_contract.topology_contract()["connectivity_sha256"],
        "geometry_quality": quality,
        "preserved_primary_snapshot": preserved,
        "localized_attribute_and_normal_gate": attribute_normal_gate,
        "freeze": freeze,
        "global_state": global_actual,
        "seam": {
            "maximum_world_position_delta_m": seam_position_delta,
            "maximum_weight_delta": seam_weight_delta,
            "maximum_uv_delta": seam_uv_delta,
        },
        "private_inactive_properties_exact": True,
        "all_saved_structural_gates_passed": True,
    }


def _body_bounds(body: bpy.types.Object) -> tuple[Vector, Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        low = Vector(tuple(min(float(point[axis]) for point in points) for axis in range(3)))
        high = Vector(tuple(max(float(point[axis]) for point in points) for axis in range(3)))
        return low, high
    finally:
        evaluated.to_mesh_clear()


def _patch_center(body: bpy.types.Object) -> Vector:
    points = _patch_world_points(body)
    return sum(points, Vector()) / len(points)


def _look_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    if direction.length <= 1.0e-8:
        raise R20Error("review camera collapsed onto its target")
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _create_review_camera_and_lights() -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    camera_data = bpy.data.cameras.new(TRANSIENT_PREFIX + "CameraData")
    camera = bpy.data.objects.new(TRANSIENT_PREFIX + "Camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera_data.lens = 58.0
    camera_data.clip_start = 0.01
    camera_data.clip_end = 100.0
    bpy.context.scene.camera = camera
    lights = []
    for index, energy in enumerate((900.0, 520.0, 360.0)):
        data = bpy.data.lights.new(TRANSIENT_PREFIX + f"AreaData_{index}", type="AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = 2.2 if index == 0 else 1.4
        obj = bpy.data.objects.new(TRANSIENT_PREFIX + f"Area_{index}", data)
        bpy.context.scene.collection.objects.link(obj)
        lights.append(obj)
    return camera, lights


def _create_flat_material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    material = bpy.data.materials.new(TRANSIENT_PREFIX + name)
    material.use_nodes = True
    tree = material.node_tree
    principled = next(node for node in tree.nodes if node.bl_idname == "ShaderNodeBsdfPrincipled")
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Roughness"].default_value = 0.72
    return material


def _create_normal_heatmap_material() -> bpy.types.Material:
    material = bpy.data.materials.new(TRANSIENT_PREFIX + "NormalHeatmap")
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    principled = tree.nodes.new("ShaderNodeBsdfPrincipled")
    geometry = tree.nodes.new("ShaderNodeNewGeometry")
    vector_math = tree.nodes.new("ShaderNodeVectorMath")
    vector_math.operation = "MULTIPLY_ADD"
    vector_math.inputs[1].default_value = (0.5, 0.5, 0.5)
    vector_math.inputs[2].default_value = (0.5, 0.5, 0.5)
    tree.links.new(geometry.outputs["Normal"], vector_math.inputs[0])
    tree.links.new(vector_math.outputs["Vector"], principled.inputs["Base Color"])
    tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    principled.inputs["Roughness"].default_value = 0.82
    return material


def _create_toilet_seat_prop(config: Mapping[str, Any]) -> bpy.types.Object:
    seat = config["toilet_seat"]
    outer_x = float(seat["outer_width_m"]) * 0.5
    outer_y = float(seat["outer_depth_m"]) * 0.5
    inner_x = float(seat["opening_width_m"]) * 0.5
    inner_y = float(seat["opening_depth_m"]) * 0.5
    center_x = 0.5 * (R19_SELECTED_SEAT["x_min_m"] + R19_SELECTED_SEAT["x_max_m"])
    center_y = 0.5 * (R19_SELECTED_SEAT["y_min_m"] + R19_SELECTED_SEAT["y_max_m"])
    top_z = float(R19_SELECTED_SEAT["top_z_m"])
    thickness = float(seat["rim_thickness_m"])
    segments = 64
    vertices = []
    for z in (top_z, top_z - thickness):
        for radius_x, radius_y in ((outer_x, outer_y), (inner_x, inner_y)):
            for index in range(segments):
                angle = 2.0 * math.pi * index / segments
                vertices.append(
                    (
                        center_x + radius_x * math.cos(angle),
                        center_y + radius_y * math.sin(angle),
                        z,
                    )
                )
    outer_top = 0
    inner_top = segments
    outer_bottom = segments * 2
    inner_bottom = segments * 3
    faces = []
    for index in range(segments):
        following = (index + 1) % segments
        faces.extend(
            (
                (outer_top + index, outer_top + following, inner_top + following, inner_top + index),
                (outer_bottom + following, outer_bottom + index, inner_bottom + index, inner_bottom + following),
                (outer_top + index, outer_bottom + index, outer_bottom + following, outer_top + following),
                (inner_top + following, inner_bottom + following, inner_bottom + index, inner_top + index),
            )
        )
    mesh = bpy.data.meshes.new(TRANSIENT_PREFIX + "ToiletSeatMesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(TRANSIENT_PREFIX + "ToiletSeat", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj["review_context_prop_only"] = True
    obj.data.materials.append(_create_flat_material("SeatMaterial", (0.16, 0.18, 0.20, 1.0)))
    return obj


def _configure_render_scene() -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new(TRANSIENT_PREFIX + "World")
        scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background is not None:
        background.inputs["Color"].default_value = (0.006, 0.012, 0.020, 1.0)
        background.inputs["Strength"].default_value = 0.28


def _review_specs() -> list[dict[str, Any]]:
    specs = [
        {"name": "full_body_neutral_front", "pose": "neutral_standing", "target": "body", "view": "front"},
        {"name": "full_body_neutral_left_three_quarter", "pose": "neutral_standing", "target": "body", "view": "left_three_quarter"},
        {"name": "full_body_neutral_right_three_quarter", "pose": "neutral_standing", "target": "body", "view": "right_three_quarter"},
        {"name": "protected_neutral_front", "pose": "neutral_standing", "target": "patch", "view": "front"},
        {"name": "protected_neutral_left_three_quarter", "pose": "neutral_standing", "target": "patch", "view": "left_three_quarter"},
        {"name": "protected_neutral_right_three_quarter", "pose": "neutral_standing", "target": "patch", "view": "right_three_quarter"},
        {"name": "protected_left_profile", "pose": "neutral_standing", "target": "patch", "view": "left_profile"},
        {"name": "protected_right_profile", "pose": "neutral_standing", "target": "patch", "view": "right_profile"},
        {"name": "inferior_underbody_transition", "pose": "neutral_standing", "target": "patch", "view": "inferior"},
        {"name": "posterior_perineum_anal_relationship", "pose": "neutral_standing", "target": "patch", "view": "posterior"},
        {"name": "diagnostic_hip_open_front", "pose": "bounded_hip_open_diagnostic", "target": "patch", "view": "front"},
        {"name": "diagnostic_hip_open_inferior", "pose": "bounded_hip_open_diagnostic", "target": "patch", "view": "inferior"},
        {"name": "seated_front_three_quarter", "pose": "selected_seated_open_hip", "target": "body", "view": "right_three_quarter"},
        {"name": "seated_side_contact", "pose": "selected_seated_open_hip", "target": "body", "view": "right_profile"},
        {"name": "toilet_seated_diagnostic_contact", "pose": "toilet_seated_diagnostic_contact", "target": "patch", "view": "right_three_quarter", "toilet": True},
        {"name": "supine_side", "pose": "selected_supine", "target": "body", "view": "right_profile"},
        {"name": "supine_inferior_relationship", "pose": "selected_supine", "target": "patch", "view": "inferior"},
    ]
    for degrees in (30, 55, 80):
        for side in ("left", "right", "bilateral"):
            specs.append(
                {
                    "name": f"{side}_knee_bend_{degrees}",
                    "pose": f"{side}_knee_{degrees}",
                    "target": "body",
                    "view": "front",
                }
            )
    for view in ("front", "right_three_quarter", "right_profile", "inferior"):
        specs.append(
            {
                "name": f"wire_overlay_{view}",
                "pose": "neutral_standing",
                "target": "patch",
                "view": view,
                "wire": True,
            }
        )
    specs.extend(
        (
            {"name": "seam_normal_heatmap_light_a", "pose": "neutral_standing", "target": "patch", "view": "right_three_quarter", "style": "normal", "light_sign": 1.0},
            {"name": "seam_normal_heatmap_light_b", "pose": "neutral_standing", "target": "patch", "view": "left_three_quarter", "style": "normal", "light_sign": -1.0},
            {"name": "flat_neutral_material_comparison", "pose": "neutral_standing", "target": "patch", "view": "front", "style": "flat"},
        )
    )
    return specs


def _camera_location(target: Vector, low: Vector, high: Vector, view: str, tight: bool) -> Vector:
    size = high - low
    distance = 0.42 if tight else max(float(size.z), float(size.x), 0.25) * 2.2
    offsets = {
        "front": Vector((0.0, -distance, 0.05 * distance)),
        "posterior": Vector((0.0, distance, 0.02 * distance)),
        "left_three_quarter": Vector((-0.62 * distance, -distance, 0.08 * distance)),
        "right_three_quarter": Vector((0.62 * distance, -distance, 0.08 * distance)),
        "left_profile": Vector((-distance, 0.0, 0.02 * distance)),
        "right_profile": Vector((distance, 0.0, 0.02 * distance)),
        "inferior": Vector((0.0, -0.48 * distance, -0.86 * distance)),
    }
    return target + offsets[view]


def _render_review_package(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    config: Mapping[str, Any],
    output: Path,
) -> dict[str, Any]:
    _configure_render_scene()
    camera, lights = _create_review_camera_and_lights()
    pose_map = {record["id"]: record for record in required_pose_states()}
    flat_material = _create_flat_material("FlatNeutral", (0.48, 0.31, 0.24, 1.0))
    normal_material = _create_normal_heatmap_material()
    renders = {}
    original_wire = (bool(body.show_wire), bool(body.show_all_edges))
    original_override = bpy.context.view_layer.material_override
    try:
        for spec in _review_specs():
            pose = pose_map[spec["pose"]]
            with evaluated_pose(body, rig, pose):
                low, high = _body_bounds(body)
                target = (low + high) * 0.5 if spec["target"] == "body" else _patch_center(body)
                tight = spec["target"] == "patch"
                camera.location = _camera_location(target, low, high, spec["view"], tight)
                _look_at(camera, target)
                light_sign = float(spec.get("light_sign", 1.0))
                light_offsets = (
                    Vector((1.6 * light_sign, -1.4, 2.0)),
                    Vector((-1.3 * light_sign, -0.4, 0.8)),
                    Vector((0.3, 1.2, 1.4)),
                )
                for light, offset in zip(lights, light_offsets):
                    light.location = target + offset
                    _look_at(light, target)
                body.show_wire = bool(spec.get("wire", False))
                body.show_all_edges = bool(spec.get("wire", False))
                style = spec.get("style")
                bpy.context.view_layer.material_override = (
                    normal_material if style == "normal" else flat_material if style == "flat" else None
                )
                toilet = _create_toilet_seat_prop(config) if spec.get("toilet") else None
                path = output / f"{spec['name']}.png"
                if path.exists():
                    raise R20Error(f"refusing to overwrite review render: {path}")
                bpy.context.scene.render.filepath = str(path)
                bpy.ops.render.render(write_still=True)
                if not path.is_file() or path.stat().st_size <= 1024:
                    raise R20Error(f"review render missing or implausibly small: {path}")
                renders[spec["name"]] = {
                    "path": project_relative(path),
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                    "pose": spec["pose"],
                    "view": spec["view"],
                    "style": style or "ordinary_studio_material",
                }
                if toilet is not None:
                    mesh = toilet.data
                    bpy.data.objects.remove(toilet, do_unlink=True)
                    bpy.data.meshes.remove(mesh)
    finally:
        body.show_wire, body.show_all_edges = original_wire
        bpy.context.view_layer.material_override = original_override
    required_names = {spec["name"] for spec in _review_specs()}
    if set(renders) != required_names:
        raise R20Error("private review render inventory is incomplete")
    return {
        "render_count": len(renders),
        "renders": renders,
        "all_required_private_review_angles_present": True,
        "ordinary_material_review_retained": True,
        "wire_and_normal_diagnostics_do_not_replace_ordinary_review": True,
        "opposite_light_normal_heatmaps": [
            "seam_normal_heatmap_light_a",
            "seam_normal_heatmap_light_b",
        ],
        "numeric_normal_gate_required_before_heatmap_render": True,
        "visual_rejection_conditions_require_owner_decision": True,
    }


def _candidate_package_manifest(candidate_dir: Path) -> Path:
    manifest_path = candidate_dir / "PACKAGE_MANIFEST.json"
    if manifest_path.exists():
        raise R20Error("candidate package manifest already exists")
    members = []
    for path in sorted(value for value in candidate_dir.rglob("*") if value.is_file()):
        if path == manifest_path:
            continue
        try:
            path.resolve().relative_to(candidate_dir.resolve())
        except ValueError as exc:
            raise R20Error("candidate package member escapes candidate directory") from exc
        members.append(
            {
                "path": project_relative(path),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    if len({record["path"] for record in members}) != len(members):
        raise R20Error("candidate package contains a duplicate member path")
    write_json_exclusive(
        manifest_path,
        {
            "schema_version": 1,
            "worker_id": WORKER_ID,
            "created_utc": utc_now(),
            "status": "PRIVATE_INACTIVE_OWNER_REVIEW_PACKAGE_NOT_APPROVED",
            "files_excluding_this_manifest": members,
            "private": True,
            "inactive": True,
            "unassigned": True,
            "unpublished": True,
            "runtime_eligible": False,
            "owner_approved": False,
        },
    )
    return manifest_path


def run_verify_render_mode(
    config: Mapping[str, Any],
    paths: Mapping[str, Path],
    candidate_id: str | None,
) -> dict[str, Any]:
    if candidate_id is None:
        raise R20Error("verify-render requires --candidate-id")
    _candidate_parameters(candidate_id)
    author_output = paths["author_output"]
    if not author_output.is_dir():
        raise R20Error("author output does not exist; run serialized author mode first")
    candidate_dir = author_output / candidate_id
    if not candidate_dir.is_dir():
        raise R20Error(f"candidate output does not exist: {candidate_dir}")
    if (candidate_dir / "VERIFY_RENDER_EVIDENCE.json").exists() or (
        candidate_dir / "PACKAGE_MANIFEST.json"
    ).exists():
        raise R20Error("verify-render output already exists; append-only rerun refused")
    evidence_path = candidate_dir / "AUTHORING_EVIDENCE.json"
    if not evidence_path.is_file():
        raise R20Error("candidate lacks AUTHORING_EVIDENCE.json")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence.get("candidate_id") != candidate_id:
        raise R20Error("candidate evidence ID mismatch")
    candidate_record = _candidate_config(config, candidate_id)
    blend_path = candidate_dir / str(candidate_record["blend_filename"])
    expected_blend = evidence.get("blend", {})
    _assert_hash(blend_path, str(expected_blend.get("sha256", "")), "candidate Blend")
    if blend_path.stat().st_size != int(expected_blend.get("size_bytes", -1)):
        raise R20Error("candidate Blend size changed")
    _open_exact_blend(blend_path)
    body = bpy.data.objects.get(BODY_NAME)
    rig = bpy.data.objects.get(RIG_NAME)
    if body is None or body.type != "MESH" or rig is None or rig.type != "ARMATURE":
        raise R20Error("saved candidate body or rig is missing")
    saved_structure = verify_saved_structure(body, rig, paths, evidence)
    pose_suite = run_pose_suite(
        body,
        rig,
        paths,
        config,
        baseline_by_pose=evidence["source_pose_baselines"]["states"],
    )
    render_package = _render_review_package(body, rig, config, candidate_dir)
    if sha256_file(blend_path) != expected_blend["sha256"]:
        raise R20Error("render process altered the saved candidate Blend")
    if sha256_file(paths["source_blend"]) != SOURCE_BLEND_SHA256:
        raise R20Error("sealed R19 source changed during candidate verification")
    result = {
        "schema_version": 1,
        "worker_id": WORKER_ID,
        "timestamp_utc": utc_now(),
        "status": "FRESH_PROCESS_STRUCTURAL_POSE_RENDER_PASS_PENDING_OWNER_VISUAL_DECISION",
        "candidate_id": candidate_id,
        "candidate_blend": _assert_hash(blend_path, expected_blend["sha256"], "candidate Blend"),
        "authoring_evidence": _assert_hash(
            evidence_path, sha256_file(evidence_path), "authoring evidence"
        ),
        "saved_structure": saved_structure,
        "fresh_process_pose_acceptance": pose_suite,
        "private_review_package": render_package,
        "explicit_visual_review_questions": [
            "Does the surface read as continuous anatomy rather than a trapezoid, triangular plate, shelf, or apron?",
            "Are the straight superior edge and sharp diagonal borders absent under ordinary and opposite lighting?",
            "Is there no central black cavity, starburst, accordion fold, or collision crease?",
            "Are hood/restrained glans, urethral meatus, introitus, fourchette, continuous perineum, and separate anal region readable in correct order?",
            "Does neutral presentation remain natural and non-exaggerated?",
            "Does the toilet-seated diagnostic show opening clearance without seat-rim penetration?",
        ],
        "visual_acceptance_claimed": False,
        "owner_approval_claimed": False,
        "private": True,
        "inactive": True,
        "unassigned": True,
        "unpublished": True,
        "runtime_eligible": False,
        "source_r19_unchanged": True,
        "candidate_blend_unchanged_by_render_process": True,
    }
    result_path = candidate_dir / "VERIFY_RENDER_EVIDENCE.json"
    write_json_exclusive(result_path, result)
    readme_path = candidate_dir / "README_OWNER_REVIEW.md"
    write_text_exclusive(
        readme_path,
        "# Kira R20 private owner review\n\n"
        "This candidate is inactive, unassigned, unpublished, and not runtime eligible. "
        "Structural and movement gates do not constitute visual approval.\n\n"
        "Compare the ordinary, wire, opposite-light normal, seated, toilet-clearance, "
        "and supine views against the explicit rejection questions in "
        "`VERIFY_RENDER_EVIDENCE.json`. The approved face, head, eyes, brows, upper body, "
        "hands, feet, nails, rig, actions, and materials are frozen.\n\n"
        "The named external landmarks are shallow connected surface geometry and semantic "
        "review hooks only. No internal urinary, reproductive, bowel, continence, pregnancy, "
        "or intimate-behavior function is implemented or claimed.\n",
    )
    manifest_path = _candidate_package_manifest(candidate_dir)
    return {
        "status": result["status"],
        "candidate_id": candidate_id,
        "verify_evidence_sha256": sha256_file(result_path),
        "package_manifest_sha256": sha256_file(manifest_path),
        "owner_visual_approval_pending": True,
    }


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    config: dict[str, Any] | None = None
    paths: dict[str, Path] | None = None
    output_existed_before = True
    try:
        config, paths = validate_config(config_path, args)
        requested = (
            paths["preflight_output"] if args.mode == "preflight" else paths["author_output"]
        )
        output_existed_before = requested.exists()
        if args.mode == "preflight":
            result = run_preflight_mode(config, paths)
        elif args.mode == "author":
            if args.candidate_id is not None:
                raise R20Error("author mode always evaluates the exact two bounded candidates")
            result = run_author_mode(config, paths)
        else:
            result = run_verify_render_mode(config, paths, args.candidate_id)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        failure = {
            "schema_version": 1,
            "worker_id": WORKER_ID,
            "timestamp_utc": utc_now(),
            "mode": args.mode,
            "candidate_id": args.candidate_id,
            "status": "FAILED_CLOSED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "no_runtime_activation_assignment_export_publication": True,
            "no_source_blend_save_attempted_by_failure_handler": True,
        }
        if paths is not None:
            requested = (
                paths["preflight_output"] if args.mode == "preflight" else paths["author_output"]
            )
            # Preserve evidence only when this invocation created or is already
            # operating inside its exact append-only output. Never append to an
            # arbitrary pre-existing target rejected by the path guard.
            if requested.is_dir() and not output_existed_before:
                failure_path = requested / f"{args.mode.upper().replace('-', '_')}_FAILURE.json"
                if not failure_path.exists():
                    write_json_exclusive(failure_path, failure)
        print(json.dumps(failure, indent=2, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
