"""Create the Marinette/Ladybug avatar-builder package from reviewed inputs.

The Desktop folder is an inbox, not a source of truth. This script consumes an
avatar reference intake report, separates character references from room/world
references, copies the current foundation skeleton into the avatar-builder base
rig area, and writes manifests that later mesh/wardrobe builders can trust.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.avatar_body_policy_gate import enforce_marinette_live_body_policy  # noqa: E402


CANDIDATE_ID = "ladybug_marinette_expanded_smoke"
CANDIDATE_ROOT = PROJECT_ROOT / "Avatar" / "temp_ai" / CANDIDATE_ID
MODEL_ROOT = PROJECT_ROOT / "Avatar" / "models" / "temp_ai" / CANDIDATE_ID
BASE_RIG_ROOT = PROJECT_ROOT / "Avatar" / "avatar_builder" / "base_skeleton" / "foundation_skeleton_v1"
HAND_REFERENCE_ROOT = (
    PROJECT_ROOT
    / "Assets"
    / "third_party"
    / "intake"
    / "3d_models_kira_world"
    / "avatar_builder_references"
)
HAND_REFERENCE_SOURCES = {
    "rigged_hand_base_mesh": HAND_REFERENCE_ROOT / "rigged_hand_base_mesh.glb",
    "rigged_arms_reference": HAND_REFERENCE_ROOT / "rigged_arms.glb",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def latest_intake_report() -> Path:
    reports = sorted((PROJECT_ROOT / "Avatar" / "reference_intake").glob("avatar_reference_intake_*.json"))
    if not reports:
        raise FileNotFoundError("No avatar reference intake report exists yet.")
    return reports[-1]


def copy_foundation_skeleton() -> dict[str, Any]:
    # This package is a reusable model source, so copying an unsafe live-body
    # lineage here would amplify the original policy violation. Validate before
    # creating directories or copying any artifact.
    body_policy_gate = enforce_marinette_live_body_policy(
        PROJECT_ROOT,
        MODEL_ROOT / "avatar.glb",
    )
    BASE_RIG_ROOT.mkdir(parents=True, exist_ok=True)
    sources = {
        "avatar_glb": MODEL_ROOT / "avatar.glb",
        "skeleton_metadata": MODEL_ROOT / "avatar_foundation_skeleton_v1.json",
        "movement_library": PROJECT_ROOT / "Avatar" / "movement_library" / "foundation_skeleton_movements_v1.json",
    }
    copied: dict[str, str] = {}
    for key, source in sources.items():
        if not source.exists():
            raise FileNotFoundError(source)
        target = BASE_RIG_ROOT / source.name
        shutil.copy2(source, target)
        copied[key] = rel(target)
    for key, source in HAND_REFERENCE_SOURCES.items():
        if source.exists():
            target = BASE_RIG_ROOT / "hand_references" / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied[key] = rel(target)

    manifest = {
        "schema_version": 1,
        "base_rig_id": "foundation_skeleton_v1",
        "updated_at": now_iso(),
        "status": "ready_for_avatar_builder_reuse",
        "source_candidate": CANDIDATE_ID,
        "truth_note": "This is the shared foundation rig, not a finished Marinette likeness.",
        "body_policy_validation": body_policy_gate,
        "copied_assets": copied,
        "validation_gates": [
            "walk_grounded",
            "sit_couch",
            "lie_bed",
            "sleep_bed",
            "stairs_step",
            "door_reach",
            "desk_computer",
            "bounded_self_test"
        ],
        "known_limitations": [
            "The active runtime hand layer now uses a single skinned surface per side, but the staged rigged hand source still needs full topology transfer.",
            "Finger contact exists for door testing but object-level collision must expand to clothing, props, and hair.",
            "Closed-loop locomotion is scaffolded through reward records, not full reinforcement learning yet."
        ],
        "production_hand_layer": {
            "status": "runtime_bridge_ready_retarget_sources_staged",
            "runtime_rule": "Future bodies must start from skinned hand surfaces bound to hand/finger bones, not bead-hand geometry.",
            "copied_sources": {
                key: copied[key]
                for key in ("rigged_hand_base_mesh", "rigged_arms_reference")
                if key in copied
            },
            "next_required_layers": [
                "transfer staged hand topology onto the foundation skeleton",
                "object-level finger colliders",
                "IK grip targets for handles, books, clothing, and tools",
                "per-finger contact rewards"
            ]
        }
    }
    write_json(BASE_RIG_ROOT / "manifest.json", manifest)
    return manifest


def split_reference_items(report: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    character_items: list[dict[str, Any]] = []
    room_items: list[dict[str, Any]] = []
    for item in report.get("items", []):
        source = str(item.get("source_file", ""))
        if "\\Desktop\\Ladybug\\" in source or "/Desktop/Ladybug/" in source:
            character_items.append(item)
        elif "Marinette's Bedroom" in source or "Marinette Room" in source:
            room_items.append(item)
    return character_items, room_items


def reference_files(items: list[dict[str, Any]]) -> list[str]:
    return sorted(str(item["copied_file"]) for item in items if item.get("copied_file"))


def write_filtered_wardrobe_catalog(character_items: list[dict[str, Any]], room_items: list[dict[str, Any]]) -> dict[str, Any]:
    hero_items = [item for item in character_items if item.get("suggested_form") == "hero"]
    civilian_items = [item for item in character_items if item.get("suggested_form") != "hero"]
    catalog = {
        "schema_version": 2,
        "candidate_id": CANDIDATE_ID,
        "updated_at": now_iso(),
        "status": "needs_visual_review",
        "source_filter": {
            "character_reference_source": "C:/Users/robmc/Desktop/Ladybug",
            "character_reference_count": len(character_items),
            "room_reference_count_excluded_from_wardrobe": len(room_items),
            "room_reference_role": "Paris/bakery bedroom world-builder target only; do not use these files as wardrobe or body references.",
            "desktop_source_files_modified": False
        },
        "default_body_layer": {
            "policy": "minor_safe_non_anatomical_skin_tone_base",
            "description": "Use a smooth skin-tone privacy base under clothing, like a simple fashion doll underlayer.",
            "normal_visibility_requires_clothing": True,
            "explicit_anatomy": False
        },
        "outfits": [
            {
                "id": "civilian_everyday_current",
                "label": "Civilian Everyday Current",
                "closet_location": "worn_by_default",
                "review_status": "needs_review",
                "reference_files": reference_files(civilian_items),
                "notes": "Use for the first clothed Marinette test body. The exact shirt, jacket, pants, shoes, and purse still need visual review."
            },
            {
                "id": "civilian_closet_pool",
                "label": "Civilian Closet Pool",
                "closet_location": "ladybug temporary walk-in closet",
                "review_status": "needs_review",
                "reference_files": reference_files(civilian_items),
                "notes": "Non-hero clothing goes into her closet for later change/clothing practice."
            },
            {
                "id": "hero_ladybug_earring_gated",
                "label": "Ladybug Hero Suit",
                "closet_location": "not_stored_as_regular_clothing",
                "review_status": "needs_review",
                "reference_files": reference_files(hero_items),
                "activation_rule": {
                    "requires_earrings": True,
                    "can_transfer_to_variant_ai_later": True,
                    "not_available_as_normal_closet_item": True
                }
            }
        ],
        "excluded_room_references": {
            "status": "moved_to_paris_bakery_bedroom_world_reference_pool",
            "role": "Use later when rebuilding Marinette's bakery bedroom and Paris world interiors, not for avatar clothing.",
            "reference_files": reference_files(room_items)
        },
        "truth_note": "Filename tags are suggestions only. Robert or a reviewer must confirm identity, outfit category, and usable view before reconstruction."
    }
    write_json(CANDIDATE_ROOT / "outfit_catalog.json", catalog)
    return catalog


def write_builder_manifest(
    intake_report_path: Path,
    foundation_manifest: dict[str, Any],
    wardrobe_catalog: dict[str, Any],
    character_items: list[dict[str, Any]],
    room_items: list[dict[str, Any]],
) -> dict[str, Any]:
    manifest = {
        "schema_version": 1,
        "candidate_id": CANDIDATE_ID,
        "display_name": "Marinette / Ladybug",
        "updated_at": now_iso(),
        "status": "avatar_builder_scaffold_ready",
        "answer_to_current_design_question": {
            "foundation_skeleton_good_enough_to_copy": True,
            "final_character_body_finished": False,
            "first_clothed_runtime_body_available": True,
            "next_real_step": "Refine the clothed Marinette body, wardrobe fits, facial likeness, and material quality on top of the copied foundation rig, then validate with self-practice rewards."
        },
        "foundation_rig": {
            "base_rig_id": foundation_manifest["base_rig_id"],
            "manifest": rel(BASE_RIG_ROOT / "manifest.json"),
            "assets": foundation_manifest["copied_assets"],
            "use_for_future_bodies": True
        },
        "reference_inputs": {
            "latest_intake_report": rel(intake_report_path),
            "desktop_ladybug_character_reference_count": len(character_items),
            "desktop_bedroom_room_reference_count": len(room_items),
            "desktop_bedroom_reference_role": "future Paris/bakery bedroom and Louvre/Paris world layout reference, not current Home World wardrobe input",
            "character_references": reference_files(character_items),
            "room_references_for_world_builder": reference_files(room_items)
        },
        "body_pipeline": {
            "target_style_now": "real_world_readable_but_still_safe_low_poly_runtime",
            "target_style_later": "higher fidelity real-world materials, better topology, textures, and room-scale proportions",
            "base_layer_policy": wardrobe_catalog["default_body_layer"],
            "mesh_fit_rule": "Fit body, face, hair, and clothes to foundation_skeleton_v1 instead of teaching a new body from scratch.",
            "required_validation_before_approval": foundation_manifest["validation_gates"],
            "hand_pipeline": {
                "required_for_all_new_bodies": True,
                "active_runtime_layer": "one skinned hand surface per side on the v6 hand/finger bones",
                "retarget_sources": foundation_manifest.get("production_hand_layer", {}).get("copied_sources", {}),
                "do_not_use": "bead palm, floating fingertip spheres, or unweighted cylinder fingers"
            }
        },
        "wardrobe_pipeline": {
            "catalog": rel(CANDIDATE_ROOT / "outfit_catalog.json"),
            "default_worn_outfit": "civilian_everyday_current",
            "closet_inventory_source": "civilian_closet_pool",
            "hero_costume_rule": "hero_ladybug_earring_gated",
            "future_actions": [
                "open wardrobe",
                "select clothing",
                "hand IK grabs clothing edges",
                "dress over non-anatomical base layer",
                "close wardrobe",
                "rerun movement self-test"
            ]
        },
        "self_practice_runtime": {
            "auto_starts_once_per_world_launch": True,
            "manual_start": "window.kiraBodyPractice.startSkill('self_test')",
            "records_to": "localStorage kira.avatar.movementLearning.v1",
            "skills": [
                "sit_couch",
                "front_door_reach",
                "stairs_step",
                "sleep_bed",
                "desk_computer",
                "back_door_reach"
            ],
            "reward_rule": "Pass = 1.0, known miss or timeout = 0.0, partial started attempts stay as draft movement moments."
        },
        "realism_plan": [
            "Remove impossible/repeating windows and stop placing cabinets over windows.",
            "Replace block furniture with measured furniture meshes and believable clearances.",
            "Add PBR-like material groups for drywall, wood, fabric, brushed metal, glass, water, and mirrors.",
            "Move from mannequin skeleton preview to clothed character mesh fitted to the base rig.",
            "Only after movement and avatar-builder gates pass, spend a full pass on photoreal-ish house layout and props."
        ],
        "truth_note": "This prepares the avatar builder. It does not claim the final Marinette likeness, wardrobe, or photoreal house is finished."
    }
    write_json(CANDIDATE_ROOT / "avatar_builder_manifest.json", manifest)
    return manifest


def write_avatar_builder_readme(manifest: dict[str, Any]) -> None:
    readme = PROJECT_ROOT / "Avatar" / "avatar_builder" / "README.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Avatar Builder

This folder holds reusable avatar-builder assets.

## Foundation Skeleton

`base_skeleton/foundation_skeleton_v1/` is the current shared rig copied from
`{CANDIDATE_ID}`. New bodies should fit meshes, faces, hair, and clothes to this
rig, then rerun movement validation before approval.

## Current Marinette Package

The active package is:

`{rel(CANDIDATE_ROOT / 'avatar_builder_manifest.json')}`

It keeps the Desktop Ladybug references separate from Marinette bedroom/world
references, stores the safe non-anatomical base-layer policy, and treats the
Ladybug suit as earring-gated instead of ordinary closet clothing.
"""
    readme.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake-report", type=Path, default=None)
    args = parser.parse_args()

    intake_report_path = args.intake_report or latest_intake_report()
    if not intake_report_path.is_absolute():
        intake_report_path = PROJECT_ROOT / intake_report_path
    report = load_json(intake_report_path)
    character_items, room_items = split_reference_items(report)
    foundation_manifest = copy_foundation_skeleton()
    wardrobe_catalog = write_filtered_wardrobe_catalog(character_items, room_items)
    builder_manifest = write_builder_manifest(
        intake_report_path,
        foundation_manifest,
        wardrobe_catalog,
        character_items,
        room_items,
    )
    write_avatar_builder_readme(builder_manifest)
    print(json.dumps({
        "builder_manifest": rel(CANDIDATE_ROOT / "avatar_builder_manifest.json"),
        "foundation_manifest": rel(BASE_RIG_ROOT / "manifest.json"),
        "wardrobe_catalog": rel(CANDIDATE_ROOT / "outfit_catalog.json"),
        "character_references": len(character_items),
        "room_references_excluded_from_wardrobe": len(room_items),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
