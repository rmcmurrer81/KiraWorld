"""Validate and emit the append-only Kira R18 BALD authoring plan.

This is deliberately a standard-library preparation tool, not a Blender
mutation tool.  It binds the next Blender authoring pass to the exact frozen
R17 owner-review package and the completed R18 preflight evidence.  It writes
only one new append-only JSON plan under RecoverySprint.  It cannot open or
save a Blend, render, export, activate, assign, publish, or modify live state.

The later Blender author must consume the emitted plan and prove every body
coordinate/topology change is inside the named masks before it can save a new
private R18 staging Blend.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]

R17_CANDIDATE_ID = (
    "kira_profiled_adult_candidate_r17_bald_corrected_20260801_165816"
)
R17_PACKAGE_RELATIVE = Path("Avatar/private_owner_review") / R17_CANDIDATE_ID
R17_BLEND_RELATIVE = R17_PACKAGE_RELATIVE / f"{R17_CANDIDATE_ID}.blend"
R17_BLEND_SHA256 = "7f7a6519ee5902fb01b247add864a4f41f4be6e600ab917cc5195ca9ea21e493"
R17_BUILD_EVIDENCE_SHA256 = (
    "5a2965bb77b50aa5217e5eedda66d58bfaa5b54f4faa74a1808bbab6a94b8188"
)
R17_PACKAGE_FILE_COUNT = 34
R17_PACKAGE_INVENTORY_SHA256 = (
    "38e0eb282bc86307f9abc7edd0bfd7f2f5fcf72c5a09077a232303e64f733091"
)

PREFLIGHT_BINDINGS = {
    "System/Docs/KIRA_R18_MEDICAL_EXTERNAL_ANATOMY_AND_BATHROOM_READINESS_BOUNDARY_20260801.md":
        "21b71a8ecd869d0ac26ec40cc0a63371c4c99490d115676b50a2b3bda811fb41",
    "RecoverySprint/continuation_20260801/kira_r18_owner_boundary_checkpoint/"
    "R17_INHERITED_INTERSECTION_LOCALIZATION_20260801.md":
        "a3776c43732c1954e719da3cc0ec8d096f733c969869f98f4d875eea61b02f9f",
    "RecoverySprint/continuation_20260801/kira_r18_owner_boundary_checkpoint/"
    "KIRA_R18_EXACT_CORRECTION_MASKS_20260801.md":
        "563ec2cf6cbed0eaff34e4d59c3c494639c168c945aa2bfdf2c5cd1a084fd527",
    "RecoverySprint/continuation_20260801/kira_r18_owner_boundary_checkpoint/"
    "KIRA_R17_FULL_PACKAGE_REVERIFICATION_20260801.md":
        "f087d3c3512598754b3ae57a6c13c2a38419befeb6374be0b8f8022da8d615e1",
    "RecoverySprint/continuation_20260801/kira_r18_owner_boundary_checkpoint/"
    "CHECKPOINT.md":
        "3bdb1de25bbaa953e87d8f3d6e2eb8d9fba129d8ba4fb2cc3fe7bdb7db91802e",
}

R17_IMPLEMENTATION_BINDINGS = {
    "tools/blender_build_kira_r17_corrected_bald_candidate.py":
        "2f05121038400b37568b60ae7e05ec542bb5b466d1e8b06c0c9c6d76dfc2f17c",
    "tools/blender_probe_kira_r17_integrated_corrections.py":
        "91ed9cb1dc7bc677001111611f0f2c11f9f5daa20ae16a7b30790e7d9015919d",
    "tools/blender_commit_kira_r17_best_safe_bald_candidate.py":
        "d37932085016170ea136a9039263f9df46e01090304c75d94f2ce8bf2f95bc3f",
    "tools/blender_report_kira_r18_preflight_masks.py":
        "a664d1d50b473d6334a21c713f24fb242c210542be27cad96c2acee69121103b",
}

OUTPUT_PARENT_RELATIVE = Path(
    "RecoverySprint/continuation_20260802/kira_r18_bounded_bald_authoring_preparation"
)

P1_BOUNDARY = (
    4315, 4316, 4356, 4352, 4344, 4346, 4340, 4338, 4332, 4331,
    4325, 4358, 4357, 4317, 10981, 10982, 10953, 10958, 10959, 10964,
    10966, 10971, 10969, 10976, 10980, 10946, 10945, 11052, 11060,
    11079, 11082, 11101, 11102, 12995, 11103, 11084, 11085, 11066,
    11044, 11040, 11039, 11031, 11032, 11004, 10999, 11000, 10995,
    10996, 4374, 4377, 4375, 4381, 4380, 4385, 4414, 4413, 4421,
    4422, 4426, 4448, 4467, 4466, 4485, 6398, 4484, 4483, 4464,
    4461, 4442, 4434,
)
P2_BOUNDARY = (
    4220, 4221, 4222, 4231, 4232, 10866, 10858, 10857, 10856, 10864,
    10863, 10871, 10879, 10887, 10888, 10895, 10896, 11000, 10996,
    4374, 4377, 4381, 4265, 4264, 4256, 4255, 4246, 4237, 4228, 4229,
)
P3_BOUNDARY = (
    4220, 4221, 4222, 4231, 4232, 10866, 10858, 10857, 10856, 10864,
    10863, 10871, 10879, 10887, 10888, 10895, 10896, 11000, 10999,
    11004, 11032, 11031, 11039, 11040, 11044, 11066, 11085, 11084,
    11103, 12995, 11102, 11101, 11082, 11079, 11060, 11052, 10945,
    10946, 10980, 10976, 10969, 10971, 10966, 10964, 10959, 10958,
    10953, 10982, 10981, 4317, 4357, 4358, 4325, 4331, 4332, 4338,
    4340, 4346, 4344, 4352, 4356, 4316, 4315, 4434, 4442, 4461,
    4464, 4483, 4484, 6398, 4485, 4466, 4467, 4448, 4426, 4422,
    4421, 4413, 4414, 4385, 4380, 4381, 4265, 4264, 4256, 4255,
    4246, 4237, 4228, 4229,
)


class R18AuthoringPreparationError(RuntimeError):
    """Raised before an R18 authoring plan may be called source-bound."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def index_set_sha256(indices: Iterable[int]) -> str:
    rows = sorted({int(value) for value in indices})
    digest = hashlib.sha256(struct.pack("<Q", len(rows)))
    for value in rows:
        digest.update(struct.pack("<I", value))
    return digest.hexdigest()


def package_inventory(root: Path) -> tuple[list[dict[str, Any]], str]:
    rows: list[dict[str, Any]] = []
    ledger = bytearray()
    # Reproduce the sealed Windows package-audit digest exactly.  The audit's
    # established ordering is case-folded relative path (with the original
    # spelling retained in the ledger), which places the uppercase manifest
    # names alongside their lowercase equivalents consistently.
    for path in sorted((item for item in root.rglob("*") if item.is_file()),
                       key=lambda item: (
                           item.relative_to(root).as_posix().casefold(),
                           item.relative_to(root).as_posix(),
                       )):
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        digest = sha256_file(path)
        rows.append({"path": relative, "bytes": size, "sha256": digest})
        ledger.extend(f"{relative}\0{size}\0{digest}\n".encode("utf-8"))
    return rows, hashlib.sha256(ledger).hexdigest()


def validate_sources(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    package = project_root / R17_PACKAGE_RELATIVE
    blend = project_root / R17_BLEND_RELATIVE
    evidence = package / "BUILD_EVIDENCE.json"
    if not package.is_dir() or not blend.is_file() or not evidence.is_file():
        raise R18AuthoringPreparationError("exact preserved R17 package is missing")
    if sha256_file(blend) != R17_BLEND_SHA256:
        raise R18AuthoringPreparationError("frozen R17 Blend hash drifted")
    if sha256_file(evidence) != R17_BUILD_EVIDENCE_SHA256:
        raise R18AuthoringPreparationError("frozen R17 BUILD_EVIDENCE hash drifted")
    rows, inventory_digest = package_inventory(package)
    if len(rows) != R17_PACKAGE_FILE_COUNT:
        raise R18AuthoringPreparationError(
            f"R17 package file count drifted: {len(rows)}"
        )
    if inventory_digest != R17_PACKAGE_INVENTORY_SHA256:
        raise R18AuthoringPreparationError("R17 whole-package digest drifted")

    checked: dict[str, str] = {}
    for relative, expected in {**PREFLIGHT_BINDINGS, **R17_IMPLEMENTATION_BINDINGS}.items():
        path = project_root / relative
        if not path.is_file():
            raise R18AuthoringPreparationError(f"bound input missing: {relative}")
        actual = sha256_file(path)
        if actual != expected:
            raise R18AuthoringPreparationError(
                f"bound input hash drifted: {relative}: {actual}"
            )
        checked[relative] = actual
    return {
        "r17_blend_sha256": R17_BLEND_SHA256,
        "r17_build_evidence_sha256": R17_BUILD_EVIDENCE_SHA256,
        "r17_package_file_count": len(rows),
        "r17_package_inventory_sha256": inventory_digest,
        "bound_input_hashes": checked,
    }


def _mask_contract() -> dict[str, Any]:
    return {
        "P1_front_connected_surface_first": {
            "selection": "unique >=13380 component with 5478 vertices and exact bounds",
            "component_vertex_count": 5478,
            "touching_face_count": 11070,
            "touching_vertex_count": 5630,
            "topology": "one disk",
            "boundary_vertex_count": len(P1_BOUNDARY),
            "ordered_boundary": list(P1_BOUNDARY),
            "boundary_index_set_sha256": index_set_sha256(P1_BOUNDARY),
            "boundary_coordinates": "pin exactly to R17",
            "attempt_order": 1,
        },
        "P2_rear_connected_surface_conditional": {
            "selection": "unique >=13380 component with 339 vertices and exact bounds",
            "component_vertex_count": 339,
            "touching_face_count": 716,
            "touching_vertex_count": 394,
            "topology": "one disk",
            "boundary_vertex_count": len(P2_BOUNDARY),
            "ordered_boundary": list(P2_BOUNDARY),
            "boundary_index_set_sha256": index_set_sha256(P2_BOUNDARY),
            "boundary_coordinates": "pin exactly to R17",
            "condition": "only if P1 leaves a visible posterior/perineal defect",
            "attempt_order": 2,
        },
        "P3_combined_exact_fallback": {
            "selection": "P1 faces UNION P2 faces UNION {14634,14723}",
            "face_count": 11788,
            "vertex_count": 6019,
            "topology": "Euler characteristic 1; one boundary",
            "boundary_vertex_count": len(P3_BOUNDARY),
            "ordered_boundary": list(P3_BOUNDARY),
            "boundary_index_set_sha256": index_set_sha256(P3_BOUNDARY),
            "boundary_coordinates": "pin exactly to R17",
            "condition": "fallback only; never stack P3 over a retained P1/P2 edit",
        },
        "N_nails": {
            "replaceable_object_count": 20,
            "name_ledger_sha256": "40a0460b4f750a89386117b9e625c13fb5fa1406c7aadc33204b7b6a1b27ed73",
            "body_or_digit_mutation_authorized_by_N": False,
        },
        "S_rear_scalp": {
            "vertex_count": 286,
            "index_set_sha256": "6d26abaea72462d046ceb66958e3cede7fbc84163b3215ff6fd0e19997b45601",
            "boundary": "pin; no cap, dome, painted hair, or hair dependency",
        },
        "K_knees": {
            "L": {"vertex_count": 230, "index_set_sha256": "f304e16f178574aed15b95b545fad44e1916370e8822a342c1bcf8f05255f44f"},
            "R": {"vertex_count": 230, "index_set_sha256": "77ca8bfbbe07ac56cd61e1b20296a5d1775273353dca8b629f5cf1f70a1fdfc5"},
            "outside_mask_rest_coordinates_may_move": False,
        },
        "F_face_and_brows": {
            "F1_vertex_count": 1385,
            "F1_index_set_sha256": "0f3889475e7fd928a916032e069def76b71b843e0bb7588d1535bb6363d275d9",
            "F2_lower_lip_vertex_count": 187,
            "F2_index_set_sha256": "2603edd3d96c8ab505402cffec03653dcf1040b03b8fa5b2cb09685c64eeb1d3",
            "F2_only_weight_change": {"from": 0.20, "to": 0.12},
            "F3_replaceable_objects": ["continuous_brow_v3_L", "continuous_brow_v3_R"],
            "excluded": ["head_oval_soft", "cranium", "eyes", "lids", "lashes", "ears"],
        },
        "H_hands": {
            "L": {"vertex_count": 1671, "index_set_sha256": "b07c12953d3c8cbc4fb2667aa19455d4e6150fdbd7d406ad1177b24ece84b803"},
            "R": {"vertex_count": 1671, "index_set_sha256": "b63861cefe99dbde33505c1972344399a6f443a60cf3730d229d4863ef329074"},
        },
        "T_feet": {
            "L": {"vertex_count": 1150, "index_set_sha256": "ac9d8f5293fae8a7ef3031e76c148e89903d07cd63f33fc1dab98f96cc0f7b85"},
            "R": {"vertex_count": 1150, "index_set_sha256": "f5e4e4cc059120e2f3a4839d59b151f3a6e62d3165e5cc688136088f29988a5d"},
        },
    }


def build_plan(validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "artifact_type": "kira_r18_bounded_bald_authoring_plan",
        "status": "SOURCE_BOUND_READY_FOR_NEW_PRIVATE_BLENDER_AUTHORING_ATTEMPT",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "preparation_only": {
            "blender_started": False,
            "blend_opened_or_saved": False,
            "mesh_mutated": False,
            "rendered": False,
            "candidate_created": False,
            "runtime_changed": False,
        },
        "source": {
            "candidate_id": R17_CANDIDATE_ID,
            "package": R17_PACKAGE_RELATIVE.as_posix(),
            "blend": R17_BLEND_RELATIVE.as_posix(),
            **validation,
            "read_only": True,
            "reuse_policy": "reuse every accepted R17 component; never mutate R17",
        },
        "future_output_contract": {
            "parent": "Avatar/private_owner_review",
            "required_prefix": "kira_profiled_adult_candidate_r18_bald_targeted_",
            "append_only_new_directory": True,
            "candidate_asset_id": "KIRA_BALD_LOW_RESOURCE_BODY",
            "inactive": True,
            "private_owner_review_only": True,
            "assigned": False,
            "activated": False,
            "runtime_export_allowed": False,
            "hair_or_clothing_allowed": False,
            "publication_or_upload_allowed": False,
        },
        "authorized_masks": _mask_contract(),
        "ordered_authoring_passes": [
            {
                "pass": 0,
                "name": "clone_exact_R17_in_memory_and_snapshot",
                "requirements": [
                    "reset to neutral",
                    "capture all-body coordinates/topology/weights/attributes/object ledgers",
                    "capture live Kira state hashes",
                    "retag only in the new in-memory/output copy",
                ],
            },
            {
                "pass": 1,
                "name": "F2_lip_intersection_repair",
                "requirements": [
                    "change only lower_lip_natural_volume contribution 0.20 to 0.12",
                    "run exact base-mesh and evaluated-stack intersection gates",
                    "classify inherited, repaired, numerical near-contact, artifact, new, and final counts",
                ],
            },
            {
                "pass": 2,
                "name": "P1_front_connected_surface_attempt_01",
                "requirements": [
                    "repair connected natural external appearance only inside P1",
                    "pin the exact R17 boundary",
                    "preserve FACE/CORNER/EDGE attributes outside the changed patch",
                    "do not reuse rejected v4 plate or v5 harmonic starburst as a completed result",
                    "do not graft qualified-foundation indices or use global nearest-neighbor transfer",
                    "preserve neutral natural state and add only a reversible diagnostic review control",
                ],
            },
            {
                "pass": 3,
                "name": "P2_or_P3_bounded_surface_attempt_02_if_needed",
                "requirements": [
                    "use P2 only for a remaining posterior/perineal defect",
                    "use P3 only instead of, not on top of, an incompatible P1/P2 topology result",
                    "after the second bounded surface attempt, preserve the best safe complete result for owner review",
                ],
            },
            {
                "pass": 4,
                "name": "independent_component_refinement",
                "requirements": [
                    "F1 face only; F3 brows only",
                    "N replaces only 20 detachable nail plates",
                    "S scalp fairing only with boundary pinned and no hair dependency",
                    "K knees, H hands, and T feet only inside their side-specific masks",
                    "a failed component cannot regenerate another accepted component",
                ],
            },
            {
                "pass": 5,
                "name": "immutable_diff_and_candidate_gate",
                "requirements": [
                    "prove every changed coordinate is inside an authorized mask",
                    "prove topology changes are confined to the selected P mask",
                    "prove eyes/lids/lashes/rig/actions/skin/outside attributes remain exact",
                    "prove no scalp-hair object, material, texture, guide, simulation, or dependency exists",
                    "prove source R17 package and live Kira state remain unchanged",
                ],
            },
        ],
        "movement_and_deformation_review": {
            "required_states": [
                "neutral_standing",
                "left_knee_bend_30_55_80_degrees",
                "right_knee_bend_30_55_80_degrees",
                "bilateral_knee_bend",
                "seated_front_three_quarter",
                "seated_side_contact",
                "toilet_seated_diagnostic_contact",
                "neutral_restored_after_every_pose",
            ],
            "gates": [
                "same exact 163-bone rig and deform-weight ledger",
                "no new nonadjacent leg/pelvis/body intersection or leg collapse",
                "smooth bilateral knee silhouette without dark fold or inside-out surface",
                "measured buttock/seat residual within 2 mm",
                "believable thigh and supported-foot contact",
                "pelvic/perineal surface remains continuous under hip flexion and natural thigh separation",
                "pose reset restores the exact neutral coordinate state",
            ],
            "claim_limit": (
                "Static and evaluated-pose evidence proves only visible external modeling, "
                "clearance, and deformation at the tested states. It does not prove full "
                "animation, eating, elimination, continence, internal anatomy, intimate "
                "behavior, reproduction, pregnancy, or autonomous human capability."
            ),
        },
        "private_review_evidence": [
            "front", "left_three_quarter", "right_three_quarter", "left_profile",
            "right_profile", "rear", "crown_top_scalp", "rear_scalp_hairline",
            "face_and_eyes_close", "brows_close", "both_hands_and_fingernails",
            "both_feet_and_toenails", "neutral_standing", "left_knee_bend",
            "right_knee_bend", "bilateral_knee_bend", "seated_front_three_quarter",
            "seated_side_contact", "protected_adult_front", "protected_adult_side",
            "protected_adult_three_quarter", "diagnostic_medical_external_view",
        ],
        "medical_truth_boundary": {
            "visible_external_relationships_required": True,
            "natural_variation_and_slight_asymmetry_required": True,
            "regional_skin_color_and_roughness_variation_allowed": True,
            "internal_organs_or_canals_implemented": False,
            "bathroom_function_implemented_or_claimed": False,
            "pregnancy_or_reproductive_function_implemented_or_claimed": False,
            "medical_note_controls": next(iter(PREFLIGHT_BINDINGS)),
        },
        "stop_boundary": (
            "Render and package one complete inactive private R18 candidate for Robert. "
            "Do not begin Robert, activation, assignment, clothing, runtime export, hair "
            "loading, publication, or upload. Stop for owner visual decisions."
        ),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default=(OUTPUT_PARENT_RELATIVE / "AUTHORING_PLAN.json").as_posix(),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    output_relative = Path(args.output)
    if output_relative.is_absolute():
        raise R18AuthoringPreparationError("output must be project-relative")
    output = (PROJECT_ROOT / output_relative).resolve()
    allowed_parent = (PROJECT_ROOT / OUTPUT_PARENT_RELATIVE).resolve()
    if output.parent != allowed_parent or output.name != "AUTHORING_PLAN.json":
        raise R18AuthoringPreparationError(
            "output must be the exact append-only R18 preparation plan path"
        )
    if output.exists():
        raise R18AuthoringPreparationError("append-only plan already exists")
    validation = validate_sources(PROJECT_ROOT)
    plan = build_plan(validation)
    allowed_parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": plan["status"],
                "output": output_relative.as_posix(),
                "sha256": sha256_file(output),
                "blender_started": False,
                "mesh_mutated": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
