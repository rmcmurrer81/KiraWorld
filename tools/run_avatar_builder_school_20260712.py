"""Avatar Builder School curriculum and failure-gate runner.

Robert's latest review graded the Marinette/Gwen calibration previews F again:
eyes are too large/protruding, Gwen still reads doll-safe, head/body/hair are
not close, and the builder is not learning enough from the real eye, body,
anatomy, and hair assets. This runner creates a Kira-school-style curriculum
for the Avatar Builder AI and records assignments that must pass before the
next body preview can claim improvement.

Run:
  py tools/run_avatar_builder_school_20260712.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILDER_ROOT = PROJECT_ROOT / "Avatar" / "avatar_builder"
ASSET_LIBRARY = BUILDER_ROOT / "asset_library" / "manifest.json"
SCHOOL_ROOT = BUILDER_ROOT / "school"
AVATAR_TEMP = PROJECT_ROOT / "Avatar" / "temp_ai"

MARINETTE_ID = "ladybug_marinette_expanded_smoke"
GWEN_ID = "spider_gwen_spider_gwen_20260606_013325"
PASS_ID = "avatar_builder_school_20260712"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default.copy() if isinstance(default, dict) else default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def records(manifest: dict[str, Any], category: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for record in manifest.get("records", []) or []:
        if record.get("category") == category:
            out.append({
                "id": record.get("id"),
                "filename": record.get("filename"),
                "local_file": record.get("local_file"),
                "tags": record.get("tags", []),
                "adult_only": bool(record.get("adult_only", False)),
            })
    return out


def build_curriculum(manifest: dict[str, Any]) -> dict[str, Any]:
    eye_assets = records(manifest, "eye_reference")
    body_assets = records(manifest, "base_body_reference")
    anatomy_assets = records(manifest, "adult_anatomy_reference")
    hair_assets = records(manifest, "hair_reference")
    motion_assets = records(manifest, "motion_reference")
    shoe_assets = records(manifest, "shoe_reference")
    return {
        "schema_version": 1,
        "pass_id": PASS_ID,
        "created_at": now_iso(),
        "status": "active_required_before_next_preview",
        "purpose": (
            "Teach Avatar Builder through long lessons plus assignments before it is allowed "
            "to generate another Marinette/Gwen preview. The current drafts remain failed."
        ),
        "activation_policy": (
            "Avatar Builder School runs only when Robert/Codex triggers it or when Robert "
            "opens Avatar Builder/SPA builder work. It is not autonomous background generation."
        ),
        "global_failures_from_robert": [
            "Eye models exist but the builder keeps making oversized or protruding eyes.",
            "Gwen is adult but still reads as doll-safe/Barbie-bodied.",
            "Body and head shapes do not match the references.",
            "Hair construction is extremely poor and blob-like.",
            "Overlay calibration is not enough; the builder must learn anatomy, measurement, and garment construction.",
        ],
        "source_assets": {
            "eye_reference": eye_assets,
            "base_body_reference": body_assets,
            "adult_anatomy_reference": anatomy_assets,
            "hair_reference": hair_assets,
            "motion_reference": motion_assets,
            "shoe_reference": shoe_assets,
        },
        "classes": [
            {
                "class_id": "eye_model_lab_001",
                "title": "Real Eye Model Scale, Socket Placement, And Expressions",
                "lesson_length": "long",
                "required_reading_or_assets": [asset.get("local_file") for asset in eye_assets],
                "lesson": [
                    "Use the real eye-reference GLBs as geometry teachers before generating any new eye.",
                    "An eye is a round eyeball seated behind eyelids inside a socket. It is not a flat rectangle, sticker, or plate.",
                    "Visible sclera/iris/pupil/catchlight must be scaled to the fitted head. If it reads as goggles, it fails.",
                    "For a realistic adult head, each visible eye opening is roughly one fifth of face width, with one eye-width between the eyes. Stylized heads may vary, but the eye must still sit inside an eyelid/socket volume.",
                    "The iris/pupil live on the front of the eyeball/cornea surface. The eyeball center must sit behind the face surface, not in front of it.",
                    "Blinks move eyelids or eyelid blendshapes. Do not blink by moving the eyeball or hiding the whole face.",
                ],
                "assignments": [
                    {
                        "id": "eye_asset_inspection",
                        "task": "Inspect every eye_reference GLB and save a ledger of meshes, materials, bounds, and useful eye parts.",
                        "required_output": "Avatar/avatar_builder/school/assignments/eye_asset_measurement_ledger_20260712.json",
                    },
                    {
                        "id": "candidate_eye_scale_formula",
                        "task": "For Marinette and Gwen, compute head width, candidate eye diameter, visible iris diameter, protrusion depth, and reject if the eye protrudes past the face plane or dominates the head.",
                        "required_output": "Avatar/avatar_builder/school/assignments/candidate_eye_scale_checks_20260712.json",
                    },
                    {
                        "id": "eye_socket_closeups",
                        "task": "Produce front and profile closeups with guides showing eyeball centers, eyelids, iris, pupil, and face surface.",
                        "required_output": "front/profile screenshots before approval",
                    },
                ],
                "pass_gate": [
                    "No flat eye plates.",
                    "No cyan placeholder boxes as final eyes.",
                    "Eye parts are named: sclera, iris, pupil, cornea/catchlight, eyelid, eye_socket_anchor.",
                    "Eye diameter and depth are measured against the candidate head.",
                    "Human review agrees the eyes are in the head, not stuck onto the face.",
                ],
            },
            {
                "class_id": "body_anatomy_and_maturity_001",
                "title": "Body Alteration, Anatomy, And Adult/Non-Adult Policy",
                "lesson_length": "long",
                "required_reading_or_assets": [asset.get("local_file") for asset in body_assets + anatomy_assets + motion_assets],
                "lesson": [
                    "Start with a valid base body, then alter one rigged body mesh. Do not assemble a body from abstract spheres or copied reference character bodies.",
                    "Before sculpting, create a measurement ledger: total height, head height, shoulder width, chest/rib width, waist, hip width, arm length, hand size, leg length, foot size, and head/body ratio.",
                    "Adult and non-adult are separate policies. Normal Marinette/Ladybug is non-adult doll-safe. Gwen is adult and must not receive the non-adult doll-safe simplification.",
                    "Adult anatomy references can teach proportion, landmarks, and deformation only for adult avatars. They are blocked for normal Marinette.",
                    "Silhouette overlays are guides, not final proof. The body must be shaped to match front and side references, then tested in movement.",
                    "A good body pass needs relaxed shoulders, believable joint bends, correct hand/foot scale, and a head that belongs on the body.",
                ],
                "assignments": [
                    {
                        "id": "maturity_gate_reaudit",
                        "task": "Re-check Marinette and Gwen policy fields and fail any body where Gwen gets doll-safe simplification or Marinette uses adult anatomy.",
                        "required_output": "candidate adjustment fields and school progress grade",
                    },
                    {
                        "id": "body_measurement_ledger",
                        "task": "Create body measurement ledger for Marinette and Gwen before new sculpting.",
                        "required_output": "Avatar/avatar_builder/school/assignments/body_measurement_ledger_20260712.json",
                    },
                    {
                        "id": "body_morph_plan",
                        "task": "Write concrete morph targets from overlay deltas: head width/depth, shoulder width, torso/waist/hip, limbs, hands, feet.",
                        "required_output": "Avatar/avatar_builder/school/assignments/body_morph_targets_20260712.json",
                    },
                ],
                "pass_gate": [
                    "Gwen remains adult in all fields and visual policy.",
                    "Marinette remains non-adult doll-safe in all fields.",
                    "No abstract placeholder body is presented as an avatar.",
                    "Measurements are saved before another preview.",
                    "Movement checks are queued before runtime promotion.",
                ],
            },
            {
                "class_id": "head_face_topology_001",
                "title": "Head Shape, Face Planes, Mouth, And Expression Topology",
                "lesson_length": "long",
                "required_reading_or_assets": [
                    "https://www.3dart.it/head-sculpt-in-blender-tutorial/",
                    "https://yelzkizi.org/2d-image-to-3d-model-in-blender-guide/",
                    "system/docs/AVATAR_BUILDER_IMPLEMENTATION_SPEC_v2.md",
                ],
                "lesson": [
                    "Block the cranium, jaw, cheekbones, brow, nose, mouth, and ears as large forms before adding detail.",
                    "Do not paste face planes onto a smooth egg head. Eye sockets, nose, mouth, and jaw must be part of one fitted head mesh or connected facial rig.",
                    "Expression topology needs loops around eyes and mouth so blinking and lip sync can work.",
                    "Mouth movement requires jaw, lips, and viseme controls. A floating line under the eyes is not a mouth rig.",
                    "Stylized heads still need believable anatomy: skull volume, face plane, jaw/chin, nose bridge, lips, ears, and eyelids.",
                ],
                "assignments": [
                    {
                        "id": "head_landmark_map",
                        "task": "Create candidate head landmarks for brow, eye centers, nose bridge/tip, mouth corners, chin, jaw angle, ears, and skull depth.",
                        "required_output": "Avatar/avatar_builder/school/assignments/head_landmark_maps_20260712.json",
                    },
                    {
                        "id": "expression_readiness_check",
                        "task": "Confirm shape-key or rig targets exist for blink, look, jaw open, M closed, O round, E wide, smile/frown.",
                        "required_output": "Avatar/avatar_builder/school/assignments/expression_readiness_20260712.json",
                    },
                ],
                "pass_gate": [
                    "No blank egg head as final preview.",
                    "No pasted face card.",
                    "Mouth and eyes are measured to head landmarks.",
                    "Expression hooks are present before voice/lip-sync approval.",
                ],
            },
            {
                "class_id": "hair_construction_001",
                "title": "Hair From References Without Blob Copies",
                "lesson_length": "long",
                "required_reading_or_assets": [asset.get("local_file") for asset in hair_assets],
                "lesson": [
                    "Hair references teach construction, silhouette, strand direction, scalp coverage, and rigging. Do not copy a full character head/hair mesh as the candidate.",
                    "Good hair is separate from the body/head mesh and anchored to scalp/head bones.",
                    "Hair should be built in named sections: scalp cap, bangs, side locks, back mass, pigtails/ponytail/bob layers, ties, collision bounds.",
                    "Marinette needs multiple variants: low twin pigtails, hair down, hair up without pigtails.",
                    "Gwen needs asymmetric blonde side-part/undercut variants plus hood-compatible compression.",
                    "A hair pass fails if it reads as spheres, helmet blobs, wrong color, wrong silhouette, or clips through eyes/face.",
                ],
                "assignments": [
                    {
                        "id": "hair_asset_lessons",
                        "task": "Inspect hair_reference GLBs and label usable construction ideas: cap, locks, cards, curves, bones, colors, collisions.",
                        "required_output": "Avatar/avatar_builder/school/assignments/hair_asset_lessons_20260712.json",
                    },
                    {
                        "id": "candidate_hair_variant_plan",
                        "task": "Create separate Marinette and Gwen hair variant plans before any new generated hair mesh.",
                        "required_output": "Avatar/avatar_builder/school/assignments/candidate_hair_variant_plan_20260712.json",
                    },
                ],
                "pass_gate": [
                    "Hair is separate and named.",
                    "Hair follows scalp/head movement.",
                    "Hair color/material is recorded.",
                    "Front/side/back screenshots pass Robert review.",
                ],
            },
            {
                "class_id": "real_clothes_and_fabric_001",
                "title": "Real Clothes, Fabric, And Human Dressing Interactions",
                "lesson_length": "long",
                "required_reading_or_assets": [
                    "C:/Users/robmc/Documents/avatar clothing help.txt",
                    *[asset.get("local_file") for asset in shoe_assets],
                ],
                "lesson": [
                    "Clothes are separate garment meshes, not skin textures and not a hanging prop state floating in front of the body.",
                    "A garment has states: stored/hanging, grasped, dressing_transition, worn, adjusted/fastened, removed.",
                    "For normal walking, use a skinned/worn garment with collision offsets and wrinkle bones. For dressing-room actions, use a higher-cost cloth-simulation or baked morph sequence.",
                    "Photo-to-clothing should extract garment mask, infer pattern pieces, create or edit 2D sewing pieces, simulate to 3D, extract fabric material, fit to the avatar, then add grab points and dressing animations.",
                    "Shirts need real openings: neck hole, sleeves, cuffs, front placket/button area. Pants need waist opening, legs, waistband, fly/closure. Dresses/skirts need hems and collision.",
                    "The avatar dressing action should animate hands, garment grab points, arm/leg insertion paths, and a final state swap from simulated dressing garment to stable worn garment.",
                ],
                "assignments": [
                    {
                        "id": "garment_state_machine",
                        "task": "Define garment states, transitions, required hand grab points, collision groups, and failure recovery for shirt/pants/dress/jacket/shoes.",
                        "required_output": "Avatar/avatar_builder/wardrobe_training/garment_state_machine_20260712.json",
                    },
                    {
                        "id": "white_dress_shirt_redo",
                        "task": "Turn Robert's white dress shirt test into a proper garment: hanging prop, dressing simulation/morph, worn skinned garment, button states.",
                        "required_output": "Avatar/avatar_builder/wardrobe_training/white_dress_shirt_dressing_assignment_20260712.json",
                    },
                    {
                        "id": "photo_to_garment_pipeline",
                        "task": "Save the five-stage photo-to-garment pipeline as builder instructions: segment, pattern, simulate, texture, fit/dress.",
                        "required_output": "Avatar/avatar_builder/wardrobe_training/photo_to_garment_pipeline_20260712.json",
                    },
                ],
                "pass_gate": [
                    "A garment never floats in hanging state after worn transition.",
                    "Worn garment is physically separate from body but follows the rig.",
                    "Dressing transition uses grab points or baked morphs.",
                    "Cloth sim budget is separate from low-RAM world mode.",
                ],
            },
        ],
        "graduation_rule": (
            "Avatar Builder cannot claim a new Marinette or Gwen body is improved until every class "
            "has complete assignments and the relevant candidate passes the listed gates."
        ),
    }


def build_initial_progress(curriculum: dict[str, Any]) -> dict[str, Any]:
    now = now_iso()
    return {
        "schema_version": 1,
        "pass_id": PASS_ID,
        "created_at": now,
        "updated_at": now,
        "status": "school_assigned_not_graduated",
        "student": "avatar_builder_ai",
        "current_unit_index": 0,
        "classes": {
            item["class_id"]: {
                "title": item["title"],
                "status": "assigned",
                "times_seen": 1,
                "grade": "incomplete",
                "assignments": [
                    {
                        "id": assignment["id"],
                        "status": "assigned",
                        "required_output": assignment["required_output"],
                    }
                    for assignment in item.get("assignments", [])
                ],
                "pass_gate": item.get("pass_gate", []),
            }
            for item in curriculum.get("classes", [])
        },
        "blocked_preview_claims": [
            "Marinette likeness not approved.",
            "Gwen likeness not approved.",
            "No new preview may be called successful until eye/body/head/hair/fabric assignments pass.",
        ],
    }


def build_assignment_scaffolds(curriculum: dict[str, Any]) -> dict[str, str]:
    assignment_root = SCHOOL_ROOT / "assignments"
    outputs: dict[Path, dict[str, Any]] = {}
    outputs[assignment_root / "eye_asset_measurement_ledger_20260712.json"] = {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "assigned",
        "task": "Inspect real eye GLBs with Blender and record mesh/material/bounds before next eye build.",
        "eye_assets": curriculum["source_assets"]["eye_reference"],
        "required_measurements": [
            "eyeball mesh names",
            "iris/pupil/cornea material names",
            "bounds and approximate sphere diameter",
            "usable orientation/front axis",
            "notes on whether the asset is a full eye pair or a single eye",
        ],
    }
    outputs[assignment_root / "candidate_eye_scale_checks_20260712.json"] = {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "assigned_failed_current_previews",
        "current_failure": "Robert says the eyes are closer but too big for those heads and protrude a little.",
        "candidates": {
            MARINETTE_ID: {
                "required_policy": "non_adult_doll_safe",
                "current_grade": "F",
                "next_check": "measure head width and fit smaller real-eye-derived eyeballs inside sockets",
            },
            GWEN_ID: {
                "required_policy": "adult",
                "current_grade": "F",
                "next_check": "measure adult head width and fit smaller real-eye-derived eyeballs inside sockets",
            },
        },
        "reject_if": [
            "eye appears as glasses/goggles",
            "sclera/iris/pupil are outside the face surface",
            "eye diameter dominates the head",
            "eye parts are flat planes used as final geometry",
        ],
    }
    outputs[assignment_root / "body_measurement_ledger_20260712.json"] = {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "assigned",
        "required_measurements": [
            "height",
            "head height and width",
            "shoulder width",
            "chest/rib width",
            "waist",
            "hip width",
            "arm length",
            "hand size",
            "leg length",
            "foot size",
            "head/body ratio",
            "front/side silhouette deltas",
        ],
        "candidate_notes": {
            MARINETTE_ID: "Only non-adult doll-safe body. Do not use adult anatomy.",
            GWEN_ID: "Adult female base/anatomy-guided body. Do not use Barbie/doll-safe treatment.",
        },
    }
    outputs[assignment_root / "body_morph_targets_20260712.json"] = {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "assigned",
        "rule": "Morph one base body/head to measured deltas; do not assemble abstract placeholder shapes.",
        "targets_required": ["head", "neck", "shoulders", "torso", "waist", "hips", "arms", "hands", "legs", "feet"],
    }
    outputs[assignment_root / "head_landmark_maps_20260712.json"] = {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "assigned",
        "landmarks": ["brow", "eye_center_L", "eye_center_R", "nose_bridge", "nose_tip", "mouth_corners", "chin", "jaw_angles", "ears", "skull_depth"],
    }
    outputs[assignment_root / "expression_readiness_20260712.json"] = {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "assigned",
        "required_controls": ["blink_L", "blink_R", "look_targets", "jaw_open", "viseme_M", "viseme_O", "viseme_E", "smile", "frown"],
    }
    outputs[assignment_root / "hair_asset_lessons_20260712.json"] = {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "assigned",
        "hair_assets": curriculum["source_assets"]["hair_reference"],
        "required_labels": ["cap", "bangs", "side_locks", "back_mass", "cards_or_curves", "bones", "collision_bounds", "material_color"],
    }
    outputs[assignment_root / "candidate_hair_variant_plan_20260712.json"] = {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "assigned",
        "candidates": {
            MARINETTE_ID: ["default low twin pigtails", "hair down", "hair up without pigtails"],
            GWEN_ID: ["asymmetric blonde side part", "hood-compatible compressed hair", "civilian hair-down/side-swept variant"],
        },
    }
    written: dict[str, str] = {}
    for path, payload in outputs.items():
        write_json(path, payload)
        written[path.stem] = rel(path)
    return written


def build_wardrobe_plans() -> dict[str, str]:
    root = BUILDER_ROOT / "wardrobe_training"
    plans: dict[Path, dict[str, Any]] = {}
    plans[root / "garment_state_machine_20260712.json"] = {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "active_training_assignment",
        "states": ["stored_hanging", "folded_or_carried", "grasped", "dressing_transition", "worn", "adjusting_fasteners", "removed"],
        "transitions": [
            {"from": "stored_hanging", "to": "grasped", "requires": ["reachable hanger/closet hook", "left/right hand grab target"]},
            {"from": "grasped", "to": "dressing_transition", "requires": ["garment openings mapped", "hand grab vertex groups", "avatar pose path"]},
            {"from": "dressing_transition", "to": "worn", "requires": ["arms/legs/head through openings", "collision clear", "state swap or cloth settle"]},
            {"from": "worn", "to": "adjusting_fasteners", "requires": ["buttons/zippers/ties/snaps named and reachable"]},
            {"from": "worn", "to": "removed", "requires": ["reverse dressing path", "prop state restored"]},
        ],
        "implementation_strategy": {
            "low_ram_world_mode": "use stable skinned garments with wrinkle bones and collision offsets during daily life",
            "dressing_room_mode": "use higher-cost cloth simulation or pre-baked morph/animation only during dressing actions",
            "final_swap": "after dressing, switch from simulated dressing garment to stable worn garment with same material and shape",
        },
    }
    plans[root / "white_dress_shirt_dressing_assignment_20260712.json"] = {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "assigned",
        "source_problem": "Kira shirt test left the shirt floating in hanging state in front of her body.",
        "garment": "white dress shirt",
        "required_parts": ["collar", "front_left_panel", "front_right_panel", "back_panel", "left_sleeve", "right_sleeve", "cuffs", "buttons", "buttonholes"],
        "required_openings": ["neck", "left_sleeve", "right_sleeve", "front_placket"],
        "required_grab_points": ["collar_back", "left_cuff", "right_cuff", "front_left_panel", "front_right_panel", "bottom_hem"],
        "state_test": [
            "shirt hangs in closet",
            "avatar grabs shirt",
            "right arm enters right sleeve",
            "left arm enters left sleeve",
            "shirt settles on torso",
            "buttons close",
            "shirt follows walking/sitting without floating",
        ],
    }
    plans[root / "photo_to_garment_pipeline_20260712.json"] = {
        "schema_version": 1,
        "created_at": now_iso(),
        "status": "active_training_note",
        "pipeline": [
            {"step": 1, "name": "segment garment", "output": "clean mask for shirt/pants/dress/etc."},
            {"step": 2, "name": "infer pattern pieces", "output": "front/back/sleeves/collar/waistband panels with seams"},
            {"step": 3, "name": "simulate into 3D garment", "output": "sewn cloth mesh on avatar mannequin"},
            {"step": 4, "name": "extract fabric material", "output": "albedo/roughness/normal/bump/seam/stitch maps"},
            {"step": 5, "name": "fit and dress", "output": "skinned worn garment plus dressing transition with grab points"},
        ],
        "tooling_options": [
            "Blender cloth simulation for local/open workflow",
            "Marvelous Designer/CLO-style pattern workflow if Robert later chooses external tools",
            "Segment Anything or clothing segmentation later when online/model tooling is available",
        ],
        "important_design": (
            "Use two representations when needed: a high-cost simulated dressing garment for putting on/taking off, "
            "and a stable skinned garment for daily-world walking after it is worn."
        ),
    }
    written: dict[str, str] = {}
    for path, payload in plans.items():
        write_json(path, payload)
        written[path.stem] = rel(path)
    return written


def mark_candidate_failed(candidate_id: str, curriculum_path: Path, progress_path: Path, wardrobe_paths: dict[str, str]) -> None:
    if candidate_id not in {MARINETTE_ID, GWEN_ID}:
        raise ValueError(
            "Avatar Builder School failure marking is restricted to the exact "
            f"canonical IDs {MARINETTE_ID!r} and {GWEN_ID!r}; received {candidate_id!r}."
        )
    path = AVATAR_TEMP / candidate_id / "avatar_builder_adjustments.json"
    data = read_json(path, {"schema_version": 1, "candidate_id": candidate_id, "builder": "avatar_builder"})
    if candidate_id == MARINETTE_ID:
        reason = (
            "Robert graded the latest preview F: eyes too big/protruding, body/head/hair not close, "
            "and the builder must attend Avatar Builder School before another likeness attempt. "
            "Marinette remains non-adult doll-safe only."
        )
        data["maturity_override"] = "non_adult_doll_safe"
        data["non_adult_barbie_treatment_allowed"] = True
        data["adult_anatomy_references_allowed"] = False
    elif candidate_id == GWEN_ID:
        reason = (
            "Robert graded the latest Gwen preview F: eyes too big/protruding, body/head/hair not close, "
            "and Gwen still reads like Barbie/doll-safe despite being adult. Gwen must use adult base/anatomy-guided training."
        )
        data["maturity_override"] = "adult"
        data["non_adult_barbie_treatment_allowed"] = False
        data["adult_anatomy_references_allowed"] = True
    data["updated_at"] = now_iso()
    data["approval_status"] = "avatar_builder_school_required_failed_preview"
    data["current_likeness_claim"] = "failed_not_approved"
    data["last_failed_preview_reason"] = reason
    data["avatar_builder_school_curriculum"] = rel(curriculum_path)
    data["avatar_builder_school_progress"] = rel(progress_path)
    data["wardrobe_training_state_machine"] = wardrobe_paths.get("garment_state_machine_20260712", "")
    data["photo_to_garment_pipeline"] = wardrobe_paths.get("photo_to_garment_pipeline_20260712", "")
    data.setdefault("failed_preview_models", []).append({
        "created_at": now_iso(),
        "model": str(data.get("builder_overlay_calibration_model_url") or data.get("builder_preview_model_url") or ""),
        "reason": reason,
        "status": "failed_avatar_builder_school_required",
    })
    data.setdefault("learning_notes", []).append({
        "created_at": now_iso(),
        "tags": ["avatar_builder", "school_required", "robert_f_grade", "eyes", "body", "hair", "fabric"],
        "text": reason,
    })
    write_json(path, data)


def main() -> int:
    manifest = read_json(ASSET_LIBRARY, {"records": []})
    curriculum = build_curriculum(manifest)
    curriculum_path = SCHOOL_ROOT / "avatar_builder_school_curriculum_20260712.json"
    progress = build_initial_progress(curriculum)
    progress_path = SCHOOL_ROOT / "progress" / "avatar_builder_school_progress_20260712.json"
    write_json(curriculum_path, curriculum)
    write_json(progress_path, progress)
    assignment_paths = build_assignment_scaffolds(curriculum)
    wardrobe_paths = build_wardrobe_plans()
    for candidate_id in (MARINETTE_ID, GWEN_ID):
        mark_candidate_failed(candidate_id, curriculum_path, progress_path, wardrobe_paths)
    result = {
        "ok": True,
        "curriculum": rel(curriculum_path),
        "progress": rel(progress_path),
        "assignment_paths": assignment_paths,
        "wardrobe_paths": wardrobe_paths,
        "marked_failed": [MARINETTE_ID, GWEN_ID],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
