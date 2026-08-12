from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.avatar_asset_library import (  # noqa: E402
    infer_avatar_maturity_policy,
    validate_avatar_body_policy,
)


PRESENCE_DIR = ROOT / "Data" / "presence"
SUBJECT_STOP_PATH = PRESENCE_DIR / "avatar_builder_subject_school_stop.json"
SUBJECT_PRESENCE_PATH = PRESENCE_DIR / "current_avatar_builder_subject_school_run.json"
GENERIC_STOP_PATH = PRESENCE_DIR / "avatar_builder_school_stop.json"
AVATAR_TEMP_DIR = ROOT / "Avatar" / "temp_ai"
SCHOOL_ROOT = ROOT / "Avatar" / "avatar_builder" / "school"
SESSION_ROOT = SCHOOL_ROOT / "subject_runs"
ASSIGNMENT_ROOT = SCHOOL_ROOT / "assignments" / "subject_runs"
ASSET_LIBRARY_ROOT = ROOT / "Avatar" / "avatar_builder" / "asset_library"
REAL_MODEL_PASS_SCRIPT = ROOT / "tools" / "run_avatar_builder_subject_school_real_model_pass_20260713.py"


GWEN_ID = "spider_gwen_spider_gwen_20260606_013325"
GWEN_REQUIRED_BASE = (
    ASSET_LIBRARY_ROOT
    / "base_body_reference"
    / "womenfemale_body_base_rigged_3ec62ba8d7.glb"
)
GWEN_REQUIRED_BASE_SHA256 = "3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e"

BLENDER_METHOD_SOURCES = [
    {
        "topic": "sculpt/block-out for head and face forms",
        "source": "https://docs.blender.org/manual/en/latest/sculpt_paint/sculpting/index.html",
        "use_in_school": "Use sculpting/block-out lessons for head planes, eye sockets, brow, nose, cheek, jaw, lips, ears, and neck.",
    },
    {
        "topic": "lattice deformation for broad body/head fitting",
        "source": "https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/lattice.html",
        "use_in_school": "Use broad lattice/proportional deformation before small sculpt details when matching front and side silhouettes.",
    },
    {
        "topic": "shrinkwrap/projection for fitted clothing and reference overlays",
        "source": "https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/shrinkwrap.html",
        "use_in_school": "Use shrinkwrap-style thinking for clothing layers and surface projection, not for copying a reference body.",
    },
    {
        "topic": "shape keys for expressions and lip sync",
        "source": "https://docs.blender.org/manual/en/latest/animation/shape_keys/index.html",
        "use_in_school": "Use shape-key lessons for blink, visemes, mouth opening, brows, smiles, concern, and speech expressions.",
    },
    {
        "topic": "weight painting and deformation checks",
        "source": "https://docs.blender.org/manual/en/latest/sculpt_paint/weight_paint/index.html",
        "use_in_school": "After sculpting, verify weights around eyes, mouth, jaw, shoulders, elbows, hips, knees, wrists, and hands.",
    },
]

FOLDER_45_REFERENCE_MANIFESTS = {
    "folder_45_index": "Avatar/avatar_builder/reference_models/folder_45_reference_intake_20260713.json",
    "folder_40_index": "Avatar/avatar_builder/reference_models/40_reference_intake_20260713.json",
    "gwen": "Avatar/avatar_builder/reference_models/spider_gwen_spider_gwen_20260606_013325/reference_model_manifest.json",
    "peter": "Avatar/avatar_builder/reference_models/peter_parker_spider_man_no_way_home_final_suit/reference_model_manifest.json",
    "harley_quinn": "Avatar/avatar_builder/reference_models/harley_quinn_reference/reference_model_manifest.json",
    "batgirl": "Avatar/avatar_builder/reference_models/batgirl_reference/reference_model_manifest.json",
    "adult_anatomy": "Avatar/avatar_builder/reference_models/adult_anatomy_reference/reference_model_manifest.json",
    "adult_female_shape": "Avatar/avatar_builder/reference_models/adult_female_shape_reference/reference_model_manifest.json",
    "hand": "Avatar/avatar_builder/reference_models/hand_reference/reference_model_manifest.json",
    "head_expression": "Avatar/avatar_builder/reference_models/head_expression_reference/reference_model_manifest.json",
    "power_rangers": "Avatar/avatar_builder/reference_models/power_rangers_reference/reference_model_manifest.json",
    "tony_stark": "Avatar/avatar_builder/reference_models/tony_stark_reference/reference_model_manifest.json",
}


SUBJECT_LESSONS = [
    {
        "id": "adult_female_rig_baseline",
        "title": "Adult Female Rig Baseline",
        "focus": "Start Gwen from the adult female rig base model.",
        "lesson_goal": (
            "Select the female rig base as the editable source, keep the old Gwen costume and "
            "unmasked models as references only, and create a clean subject work plan before any likeness claim."
        ),
        "builder_tasks": [
            "Use the adult female base body as the only source mesh for the body.",
            "Do not copy the unmasked Gwen model, costume model, or any third-party reference mesh into the candidate body.",
            "Keep Gwen marked adult, with adult anatomy references allowed for neutral anatomical correctness.",
            "Keep the suit, shoes, hood, and gloves as future wardrobe layers rather than base body geometry.",
        ],
        "expected_artifacts": [
            "baseline_source_manifest.json",
            "front_neutral_base_render.png",
            "side_neutral_base_render.png",
            "gwen_reference_board.json",
        ],
        "pass_checks": [
            "Source base path is recorded.",
            "Candidate is not using non-adult doll-safe policy.",
            "No reference model is copied as the candidate body.",
        ],
    },
    {
        "id": "gwen_eye_build",
        "title": "Gwen Eye Build And Placement",
        "focus": "Build Gwen's eyes into the head socket instead of flat plates in front of the face.",
        "lesson_goal": (
            "Use the 4-eyes and human-eye references to build round eyeballs, cornea/sclera/iris/pupil materials, "
            "eyelids, and eye-look controls sized to Gwen's head."
        ),
        "builder_tasks": [
            "Create two round eye assemblies, one left and one right, parented to eye bones or control anchors.",
            "Place eyes inside sockets with the cornea slightly proud but not floating in front of the face.",
            "Use Gwen's blue-gray iris color from Spider-Verse movie references.",
            "Add eyelid control anchors for blink, squint, and look direction.",
        ],
        "expected_artifacts": [
            "gwen_eye_front_closeup.png",
            "gwen_eye_side_socket_closeup.png",
            "gwen_eye_socket_landmarks.json",
            "gwen_eye_control_test.json",
            "gwen_eye_size_measurements.json",
        ],
        "pass_checks": [
            "Eyes are spherical, paired, and mirrored.",
            "Eyes sit in sockets from front and side views.",
            "Pupils/irises are not oversized for the head.",
            "Eye controls can look left, right, up, down, and blink.",
        ],
    },
    {
        "id": "gwen_head_face_shape",
        "title": "Gwen Head, Face, And Neck Shape",
        "focus": "Shape Gwen's head and face from movie references while making her more realistic.",
        "lesson_goal": (
            "Use Spider-Verse Gwen front, side, and three-quarter references to sculpt a realistic adult face: "
            "jaw, cheekbones, nose bridge, lips, brow, ears, neck, and skull volume."
        ),
        "builder_tasks": [
            "Overlay front, side, and three-quarter Gwen references against the editable head.",
            "Sculpt the head, jaw, nose, brow, lips, ears, and neck to match the reference family.",
            "Keep her more realistic than the movie/comic style while preserving recognizable Gwen features.",
            "Leave mouth and eye topology usable for expression and lip sync.",
        ],
        "expected_artifacts": [
            "gwen_head_front_overlay.png",
            "gwen_head_side_overlay.png",
            "gwen_head_three_quarter_overlay.png",
            "gwen_head_landmark_report.json",
            "gwen_head_shape_delta.json",
        ],
        "pass_checks": [
            "Head is not a plain oval or doll head.",
            "Side profile shows a believable nose, lips, chin, and neck transition.",
            "Face reads as Gwen from multiple Spider-Verse references.",
            "Mouth and eye areas are not broken by sculpting.",
        ],
    },
    {
        "id": "gwen_adult_body_shape",
        "title": "Gwen Adult Body Shape",
        "focus": "Shape Gwen's adult body on the female rig using anatomy and suit silhouette references.",
        "lesson_goal": (
            "Build an adult neutral Gwen body with correct anatomy and movement proportions, using the spandex suit "
            "as silhouette guidance only."
        ),
        "builder_tasks": [
            "Use the female base body and adult anatomy references to correct shoulders, torso, hips, arms, legs, hands, and feet.",
            "Use the Spider-Verse suit references only for silhouette, athletic proportions, and garment fit.",
            "Do not use doll-safe smoothing on Gwen; that policy is for non-adult subjects like Marinette.",
            "Keep the neutral body separate from clothing and costume meshes.",
        ],
        "expected_artifacts": [
            "gwen_body_front_overlay.png",
            "gwen_body_side_overlay.png",
            "gwen_body_back_overlay.png",
            "gwen_body_shape_delta.json",
            "gwen_overlay_fit_report.json",
            "gwen_adult_anatomy_gate.json",
        ],
        "pass_checks": [
            "Adult anatomy policy is active.",
            "Body is not a copied costume model.",
            "Proportions match the reference family from front, side, and back.",
            "Hands, feet, shoulders, hips, knees, and elbows remain rig-compatible.",
        ],
    },
    {
        "id": "gwen_hair_build",
        "title": "Gwen Hair Construction",
        "focus": "Build separate blonde asymmetrical Gwen hair instead of helmet blobs or copied hair.",
        "lesson_goal": (
            "Use hair models as construction references and Spider-Verse images as style references to build "
            "Gwen's side-swept blonde hair with shaved/short side and longer textured side."
        ),
        "builder_tasks": [
            "Build hair as separate hair geometry or hair cards, not as part of the face mesh.",
            "Use layered strands/cards with a side part, short undercut side, and longer wavy side.",
            "Add blonde material with subtle darker roots and optional pink tips only when reference-supported.",
            "Prepare alternate hair-state hooks for hood-up, hood-down, and civilian hair later.",
        ],
        "expected_artifacts": [
            "gwen_hair_front.png",
            "gwen_hair_side_left.png",
            "gwen_hair_side_right.png",
            "gwen_hair_without_body_reference.png",
        ],
        "pass_checks": [
            "Hair is not a copied reference mesh.",
            "Hair has recognizable asymmetry.",
            "Hair does not intersect eyes, mouth, or ears badly.",
            "Hair can be hidden or swapped for hood/costume states later.",
        ],
    },
    {
        "id": "gwen_mouth_expression",
        "title": "Mouth, Teeth, Tongue, And Expression Rig",
        "focus": "Prepare Gwen for speech, emotion, and lip sync.",
        "lesson_goal": (
            "Use mouth and tongue references to create an expressive mouth cavity, teeth, tongue, lips, brows, "
            "and phoneme/emotion controls."
        ),
        "builder_tasks": [
            "Add an interior mouth, teeth, and tongue compatible with lip sync.",
            "Create viseme targets for speech and expression targets for smile, concern, anger, surprise, and neutral.",
            "Keep eye, brow, and mouth controls coordinated so she can emote naturally.",
            "Check that mouth opening does not tear the face or expose broken geometry.",
        ],
        "expected_artifacts": [
            "gwen_mouth_open_test.png",
            "gwen_viseme_sheet.png",
            "gwen_expression_sheet.png",
            "gwen_face_rig_controls.json",
        ],
        "pass_checks": [
            "Mouth can open and close.",
            "Teeth and tongue stay inside the mouth.",
            "Basic visemes and emotion poses are present.",
            "Face remains believable from close-up views.",
        ],
    },
    {
        "id": "gwen_motion_rig",
        "title": "Motion Rig And Daily Movement",
        "focus": "Make the shaped Gwen body move correctly.",
        "lesson_goal": (
            "Use walking and hand/rig references to test that the edited adult body can walk, look around, "
            "gesture, sit, and interact without broken deformations."
        ),
        "builder_tasks": [
            "Retarget or validate walk, idle, look-at, hand, and sit poses on the shaped body.",
            "Check shoulder, hip, knee, elbow, wrist, neck, and eye movement after body edits.",
            "Record failures as rig blockers rather than hiding them in the preview.",
            "Keep movement tests separate from combat or notebook-world behavior.",
        ],
        "expected_artifacts": [
            "gwen_walk_cycle_front.gif",
            "gwen_walk_cycle_side.gif",
            "gwen_hand_pose_test.png",
            "gwen_motion_rig_report.json",
        ],
        "pass_checks": [
            "Walk cycle does not fold limbs incorrectly.",
            "Head and eyes can track a target.",
            "Hands can gesture without major distortion.",
            "Body deformation stays plausible in motion.",
        ],
    },
    {
        "id": "gwen_spandex_wardrobe",
        "title": "Gwen Suit As Removable Wardrobe",
        "focus": "Treat the Ghost-Spider suit as clothing, not as her body.",
        "lesson_goal": (
            "Create a wardrobe plan for the spandex suit, hood, gloves, shoes, web-pattern panels, and off/on states "
            "so she can eventually dress and undress like a person."
        ),
        "builder_tasks": [
            "Keep the neutral adult body as the body and the Ghost-Spider suit as a fitted clothing layer.",
            "Define anchors for hood, torso suit, sleeves, gloves, shoes, and wrist devices.",
            "Record closet/hanger/folded storage states for later world interaction.",
            "Do not merge the suit permanently into the body mesh.",
        ],
        "expected_artifacts": [
            "gwen_suit_layer_map.json",
            "gwen_suit_on_preview.png",
            "gwen_suit_off_neutral_preview.png",
            "gwen_suit_storage_states.json",
        ],
        "pass_checks": [
            "Suit can be conceptually removed without deleting the body.",
            "Suit pieces are named as wardrobe layers.",
            "Hands, shoes, hood, and torso layers are separate enough for future clothing logic.",
            "Wardrobe does not override adult body policy.",
        ],
    },
    {
        "id": "gwen_failure_diagnosis_and_builder_communication",
        "title": "Failure Diagnosis And Builder Communication",
        "focus": "Teach the builder to explain what failed before generating another bad body.",
        "lesson_goal": (
            "The builder must compare the last F/F+ contact sheet against Gwen references and write a clear "
            "diagnosis: eyes not in sockets, duplicate proof mouth under the real mouth, doll/barbie body, "
            "wrong hair, wrong skin tone, generic face/head, and placeholder wardrobe."
        ),
        "builder_tasks": [
            "Open the latest contact sheet and mark every visible failure in a blocker report.",
            "Name the exact wrong object classes: floating/protruding eyes, visible lip-sync proof parts, placeholder hair cards, generic body, generic face.",
            "State whether the failure came from measurement, sculpting, material, rigging, or reference selection.",
            "Before any next pass, write what will change and what artifact will prove it changed.",
        ],
        "expected_artifacts": [
            "gwen_failure_diagnosis_report.json",
            "gwen_failed_contact_sheet_markups.png",
            "avatar_builder_question_and_decision_log.md",
        ],
        "pass_checks": [
            "Builder does not call the failed body usable.",
            "Builder identifies the small fake mouth under the real mouth as a visible proof-part failure.",
            "Builder queues concrete next actions instead of vague reassurance.",
        ],
        "fail_hard_if": [
            "The report says the result is close when the eyes, hair, face, or body are visibly wrong.",
            "The builder hides a visible failure instead of recording it.",
        ],
    },
    {
        "id": "gwen_socket_curvature_eye_fit",
        "title": "Eye Socket Curvature Fit",
        "focus": "Fit eyes into the actual eyelid/socket opening, not below or in front of it.",
        "lesson_goal": (
            "Use the head mesh curvature, eyelid rim, and side-view cutaway to locate the real socket opening. "
            "Place each eyeball center behind the eyelid rim, with only the cornea/iris visible through the socket."
        ),
        "builder_tasks": [
            "Find left/right eyelid rim candidates from mesh curvature or the head-reference model, not just fixed height ratios.",
            "Create a socket cutaway proof showing the sphere center behind the eyelid rim and not on the cheek.",
            "Scale the eyeball diameter to the socket width, then separately size iris and pupil.",
            "Remove visible eyelid/mouth debug strips from final review renders; keep controls named in JSON instead.",
        ],
        "expected_artifacts": [
            "gwen_eye_socket_curvature_map.json",
            "gwen_eye_front_socket_fit.png",
            "gwen_eye_side_cutaway_socket_fit.png",
            "gwen_eye_reject_or_pass_report.json",
        ],
        "pass_checks": [
            "Eye center is behind the eyelid rim from side view.",
            "Iris and pupil are visible but not giant.",
            "No cyan/flat placeholder eyes and no debug bars are visible.",
            "Both eyes are symmetrical unless an expression intentionally changes them.",
        ],
        "fail_hard_if": [
            "Eyes sit below the socket, on the cheek, or in front of the face.",
            "The builder only changes color without correcting the socket placement.",
        ],
    },
    {
        "id": "gwen_full_face_sculpt_blockout",
        "title": "Full Face Sculpt Blockout",
        "focus": "Build a complete Gwen-like face before hair or costume approval.",
        "lesson_goal": (
            "Use the Loomis head-plane reference, head-expression model, unmasked Gwen reference, and Spider-Verse "
            "images to sculpt one coherent face: skull volume, brow, eyes, nose, cheeks, lips, jaw, ears, and neck."
        ),
        "builder_tasks": [
            "Place front and side face reference planes and record landmark points: hairline, brow, eyelids, nose bridge/tip, mouth corners, chin, jaw, ears, neck.",
            "Use broad sculpt/lattice moves first, then smaller sculpt edits; do not paste a face plane in front of the head.",
            "Remove the duplicate mini-mouth proof mesh from final visible renders.",
            "Render front, side, three-quarter, and expression-neutral close-ups before the lesson can pass.",
        ],
        "expected_artifacts": [
            "gwen_face_landmark_overlay_front.png",
            "gwen_face_landmark_overlay_side.png",
            "gwen_face_sculpt_delta.json",
            "gwen_face_closeup_front.png",
            "gwen_face_closeup_three_quarter.png",
        ],
        "pass_checks": [
            "Face has a full nose, brow, lips, chin, jaw, ears, and neck transition.",
            "The mouth is on the real face, not a second floating mouth underneath.",
            "Head shape does not read as a plain generic oval.",
            "Face still allows later blink and lip-sync shape keys.",
        ],
        "fail_hard_if": [
            "The face is still generic after the pass.",
            "A reference model face is copied as the body/head instead of measured as reference.",
        ],
    },
    {
        "id": "gwen_adult_anatomy_and_skin_tone_fit",
        "title": "Adult Anatomy And Skin Tone Fit",
        "focus": "Replace the Barbie treatment with a neutral adult body and correct skin-tone material.",
        "lesson_goal": (
            "Use the adult female base, adult anatomy references, Gwen body silhouettes, and skin-tone targets to "
            "make an adult neutral body. Gwen must not receive non-adult doll-safe smoothing."
        ),
        "builder_tasks": [
            "Confirm adult policy before using anatomy references.",
            "Use full-body front/side/back landmarks for shoulder, torso, waist, hips, arms, hands, legs, feet, neck, and head scale.",
            "Create a neutral adult body with proper anatomy policy and no costume baked into the skin.",
            "Create a skin-tone material report with color swatches sampled from Gwen references and applied to the body material.",
        ],
        "expected_artifacts": [
            "gwen_adult_policy_gate.json",
            "gwen_full_body_front_landmarks.png",
            "gwen_full_body_side_landmarks.png",
            "gwen_body_lattice_delta.json",
            "gwen_skin_tone_material_report.json",
            "gwen_neutral_adult_body_review.png",
        ],
        "pass_checks": [
            "Adult policy is active and doll-safe smoothing is not used.",
            "Body is shaped from the female base and not copied from a costume/reference mesh.",
            "Skin tone is recorded and applied as material data.",
            "Hands and feet remain rig-compatible.",
        ],
        "fail_hard_if": [
            "Gwen is treated like a non-adult Barbie body.",
            "The spandex/costume model becomes the base body.",
        ],
    },
    {
        "id": "gwen_hair_reference_rebuild",
        "title": "Gwen Hair Reference Rebuild",
        "focus": "Build the right hair style instead of flat strips or blobs.",
        "lesson_goal": (
            "Use the folder-45 unmasked Gwen model, Gwen images, and hair-reference library to build a generated "
            "side-swept blonde hairstyle with short/undercut side, longer face-framing side, darker roots, and optional pink tips."
        ),
        "builder_tasks": [
            "Measure hairline, part line, short-side boundary, long lock length, back hair volume, and face clearance.",
            "Build hair as separate generated geometry or curves/cards anchored to scalp/head bones.",
            "Render hair-only, head-with-hair front, left side, right side, and back.",
            "Reject wide rectangular strips, helmet blobs, and hair that hides the eyes/mouth incorrectly.",
        ],
        "expected_artifacts": [
            "gwen_hair_reference_measurements.json",
            "gwen_generated_hair_only.png",
            "gwen_hair_front_fit.png",
            "gwen_hair_left_side_fit.png",
            "gwen_hair_right_side_fit.png",
            "gwen_hair_back_fit.png",
        ],
        "pass_checks": [
            "Hair has recognizable Gwen asymmetry.",
            "Hair is separate from the head/body and can be hidden for hood/costume states.",
            "Hair material is blonde with correct darker-root/pink-tip notes when reference-supported.",
            "Hair does not intersect eyes or mouth badly.",
        ],
        "fail_hard_if": [
            "Hair looks like wide cardboard strips.",
            "Hair is copied from the unmasked model instead of generated from references.",
        ],
    },
    {
        "id": "gwen_shape_keys_and_mouth_cleanup",
        "title": "Shape Keys And Mouth Cleanup",
        "focus": "Stop using visible duplicate mouth proof parts and build real expression targets.",
        "lesson_goal": (
            "Move lip-sync and expression data into named controls/shape keys or hidden rig helpers. The final face "
            "render must show one real mouth on the face, with teeth/tongue inside only when the mouth opens."
        ),
        "builder_tasks": [
            "Remove or hide visible debug mouth rings from final proof renders.",
            "Create shape-key/target records for blink, look, smile, concern, anger, surprise, A/E/O/M visemes, and neutral.",
            "Render neutral, smile, mouth-open, blink, and look-left/right proofs.",
            "Use the teeth/tongue/mouth reference models only as construction references.",
        ],
        "expected_artifacts": [
            "gwen_shape_key_plan.json",
            "gwen_neutral_single_mouth.png",
            "gwen_mouth_open_with_teeth_tongue.png",
            "gwen_blink_test.png",
            "gwen_expression_sheet.png",
        ],
        "pass_checks": [
            "Only one mouth appears in neutral renders.",
            "Teeth and tongue stay inside the mouth.",
            "Eyes can blink without the whole eyeball moving out of socket.",
            "Expression targets are named and reviewable.",
        ],
        "fail_hard_if": [
            "A second small mouth appears under the real mouth.",
            "The mouth is a floating object in front of the face.",
        ],
    },
    {
        "id": "adult_anatomy_masterclass_foundation",
        "title": "Adult Anatomy Masterclass Foundation",
        "focus": "Stop treating adult as only metadata; the adult mesh itself must pass anatomy and proportion review.",
        "lesson_goal": (
            "For adult subjects, build a neutral adult body from the approved adult base with measured skeletal, "
            "surface, and proportion landmarks. A smooth generic or doll-safe body is an automatic F even when "
            "the candidate metadata says adult."
        ),
        "builder_tasks": [
            "Confirm the subject is adult before loading adult anatomy references.",
            "Measure head height, shoulder width, ribcage, waist, pelvis, hip, arm, leg, hand, and foot landmarks.",
            "Use a lattice/sculpt pass from front, side, and back overlays instead of simple z-band scaling.",
            "Preserve rig compatibility for walking, sitting, lying, reaching, face tracking, and clothing.",
            "Keep adult body anatomy neutral and nonsexual; this is the base body for movement, clothing, and identity.",
        ],
        "expected_artifacts": [
            "adult_subject_policy_gate.json",
            "adult_body_front_landmark_overlay.png",
            "adult_body_side_landmark_overlay.png",
            "adult_body_back_landmark_overlay.png",
            "adult_body_lattice_sculpt_delta.json",
            "adult_body_anatomy_review_contact_sheet.png",
        ],
        "pass_checks": [
            "The body is not doll-safe, not Barbie-smoothed, and not merely an adult flag on a generic base.",
            "The front, side, and back renders show a coherent adult body fitted to references.",
            "The mesh still supports rig deformation and future clothing layers.",
            "The pass produces a GLB and contact sheet, not JSON-only claims.",
        ],
        "fail_hard_if": [
            "The body still reads as a smooth generic placeholder.",
            "The builder says adult anatomy is approved because metadata is adult.",
            "The result hides missing anatomy or failed proportions behind clothing, labels, or camera angles.",
        ],
    },
    {
        "id": "eye_socket_anatomy_masterclass",
        "title": "Eye Socket Anatomy Masterclass",
        "focus": "Build eyes from the skull/socket landmarks, not from flat guide boxes.",
        "lesson_goal": (
            "Create believable eyes by measuring the head first, then placing spherical eyeballs behind eyelid rims "
            "with iris, pupil, cornea/sclera material, blink controls, and side-view proof."
        ),
        "builder_tasks": [
            "Measure the skull width, brow plane, orbital rim, eyelid opening, eye center, and face-front surface.",
            "Size each eyeball from the eyelid opening and head scale; reject tiny, giant, or flattened eyes.",
            "Place eye centers behind the eyelid rim so the visible front sits inside the socket, not on the face.",
            "Add look targets and blink/upper-lower lid controls without visible debug frames in final renders.",
            "Render close front, side cutaway, three-quarter, look-left/right, and blink proofs.",
        ],
        "expected_artifacts": [
            "eye_socket_landmark_measurements.json",
            "eye_front_realism_closeup.png",
            "eye_side_socket_cutaway.png",
            "eye_blink_test.png",
            "eye_look_direction_sheet.png",
        ],
        "pass_checks": [
            "Eyes are spherical and seated inside the sockets from front and side views.",
            "Iris and pupil read as realistic materials rather than flat cyan/white debug discs.",
            "No eye guide boxes, floating frames, or detached eye objects are visible in review renders.",
        ],
        "fail_hard_if": [
            "The eyes are too small, too flat, outside the socket, below the socket, or visibly floating.",
            "The builder only changes eye color without fixing size, depth, and socket fit.",
        ],
    },
    {
        "id": "body_movement_self_training_lab",
        "title": "Body Movement Self-Training Lab",
        "focus": "Teach bodies to move naturally and improve from recorded attempts.",
        "lesson_goal": (
            "Every avatar body must prove basic daily movement before it is treated as live-ready. Movement learning "
            "should save attempts, failures, scores, and proof clips so future bodies can improve instead of repeating "
            "stiff arms and door failures."
        ),
        "builder_tasks": [
            "Run idle, walk with natural arm swing, turn, sit, stand, lie down, get up, reach, door, stairs, and look-at tests.",
            "Record foot contacts, hand contacts, pelvis/root movement, head/eye tracking, and failed obstacle contacts.",
            "Save failed attempts as draft movement-learning records, not as approved animations.",
            "Promote only reviewed movement clips to the shared movement library.",
            "Keep the mind/body truth check active: if the AI says it is reading, drinking, sitting, or home, the body/world state must support that.",
        ],
        "expected_artifacts": [
            "movement_self_test_contact_sheet.png",
            "walk_arm_swing_front_side.gif",
            "sit_lie_stand_sequence.gif",
            "door_reach_follow_through.gif",
            "movement_learning_attempts.jsonl",
            "mind_body_truth_report.json",
        ],
        "pass_checks": [
            "Arms swing naturally during walking instead of staying stiff.",
            "The body can sit, lie down, get up, reach, and cross door thresholds without teleporting.",
            "Failures are recorded with enough detail for the builder to adjust and retry.",
            "The avatar does not claim unsupported activities when no matching prop or body state exists.",
        ],
        "fail_hard_if": [
            "The avatar walks through walls, gets blocked by doors, or teleports while claiming a normal route.",
            "The test only records coordinates and does not produce visual proof.",
            "The body is visually updated while the avatar is active in a live world session.",
        ],
    },
    {
        "id": "mind_body_grounding_contract",
        "title": "Mind And Body Grounding Contract",
        "focus": "Keep the spoken mind, body location, props, and world state aligned.",
        "lesson_goal": (
            "Synthetic people need their mind and body to share the same truth surface. The chat system, life loop, "
            "navigation state, active prop use, and body animation must agree before a live test is considered valid."
        ),
        "builder_tasks": [
            "Expose current room, route target, prop target, posture, held item, and activity evidence to the mind prompt.",
            "Block unsupported claims such as reading without a book/tablet/phone/computer, drinking without a cup, or being home when coordinates disagree.",
            "When world collision blocks a route, report confusion or blockage instead of pretending the intended destination was reached.",
            "Never hot-swap or edit visible eyes/body parts while the avatar is active in a live world test.",
        ],
        "expected_artifacts": [
            "mind_body_state_contract.json",
            "activity_truth_examples.json",
            "unsupported_claim_blocker_report.json",
            "live_world_hot_swap_safety_rule.json",
        ],
        "pass_checks": [
            "Mind replies reference the actual reachable world state.",
            "The life loop records inner intent separately from spoken text and body outcome.",
            "World/body failures become honest observations instead of generic dialogue.",
        ],
        "fail_hard_if": [
            "The avatar says it is doing an activity with no matching body state or prop evidence.",
            "The body location and spoken location disagree without a recorded confusion/teleport event.",
        ],
    },
    {
        "id": "robe_towel_clothing_state_lab",
        "title": "Robe And Towel Clothing State Lab",
        "focus": "Build first soft-goods clothing that can exist as a world prop and as wearable avatar clothing.",
        "lesson_goal": (
            "Use a bath robe and towels as the first reusable fabric training set. The builder must prove state "
            "changes: hanging, folded, held, worn open, worn tied, carried, removed, and placed back on a hook, "
            "rack, bed, floor, drawer, or laundry basket. A garment stuck in its hanging pose while floating in "
            "front of the avatar is an automatic failure."
        ),
        "builder_tasks": [
            "Build a robe as separate garment geometry with collar, left/right sleeves, belt loops, belt ends, hem, pockets, hook loop, and body collision offsets.",
            "Build towel variants as separate fabric objects: folded stack, rack-hung towel, hand towel, bath towel, body-wrap towel, damp towel, and carried towel.",
            "Define world-prop forms and wearable avatar forms for the same item ID so World Builder and Avatar Builder can hand the object back and forth.",
            "Create dressing animations for grabbing the robe, putting both arms through sleeves, settling it on the body, tying the belt, walking, untying, removing, and hanging or dropping it.",
            "Create towel-use animations for washing hands, drying hands, drying after a bath/shower, wrapping around the body, hanging on a rack, and folding.",
            "Run the same robe/towel fit on at least one adult body and one non-adult doll-safe mannequin without changing the maturity policy of either subject.",
        ],
        "expected_artifacts": [
            "robe_towel_item_state_machine.json",
            "robe_hanging_on_bathroom_hook.png",
            "robe_worn_open_front_side.png",
            "robe_worn_tied_walk_test.gif",
            "robe_remove_and_hang_back_sequence.gif",
            "towel_folded_stack_and_rack.png",
            "towel_hand_use_and_body_wrap_sequence.gif",
            "robe_towel_collision_and_grab_report.json",
            "robe_towel_avatar_world_handoff_report.json",
        ],
        "pass_checks": [
            "The robe and towels are separate fabric/garment objects, not skin textures and not fused body meshes.",
            "The robe can change from hanging or folded to worn and back to a prop state without floating in the old storage pose.",
            "Sleeve openings, collar, belt, towel edges, hooks, rack, hand grab points, and body collision anchors are named and reviewable.",
            "The avatar can walk in the worn robe without the garment clipping badly or staying behind.",
            "Towel use is grounded by a visible towel prop or worn/wrapped towel state.",
            "Adult and non-adult policies remain separate: adult bodies may use neutral adult anatomy, non-adult bodies remain smooth/doll-safe.",
        ],
        "fail_hard_if": [
            "The robe floats in front of the body while still shaped like a hanging robe.",
            "The item has only one static pose and no state machine.",
            "The builder fakes proof by labeling a box or generic body render as robe/towel output.",
            "A non-adult mannequin receives adult anatomy or an adult mannequin receives doll-safe smoothing because of the clothing test.",
        ],
    },
    {
        "id": "subject_review_gate",
        "title": "Robert Review Gate",
        "focus": "Gather proofs and block approval until the subject pass is visually reviewed.",
        "lesson_goal": (
            "Collect front, side, back, close-up, eyes, hair, mouth, motion, and wardrobe proofs before calling "
            "Gwen usable."
        ),
        "builder_tasks": [
            "Summarize all current blockers and missing visual proofs.",
            "Mark failures honestly with F/needs-redo when proofs are missing or broken.",
            "Only recommend approval after actual render proofs exist and Robert accepts the result.",
            "Queue the next weakest lesson as the next subject-school focus.",
        ],
        "expected_artifacts": [
            "gwen_subject_review_summary.json",
            "gwen_review_contact_sheet.png",
            "gwen_blocker_list.json",
        ],
        "pass_checks": [
            "Every previous lesson has a visible artifact or an explicit blocker.",
            "No copied-reference model is marked usable.",
            "No unverified preview is marked final.",
        ],
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compact_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        if isinstance(default, dict):
            return dict(default)
        if isinstance(default, list):
            return list(default)
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def rel(path: Path | str) -> str:
    path = Path(path)
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "subject"


def asset_paths() -> dict:
    return {
        "female_base_model": rel(GWEN_REQUIRED_BASE) if GWEN_REQUIRED_BASE.exists() else "",
        "eye_references": [
            rel(path)
            for path in sorted((ASSET_LIBRARY_ROOT / "eye_reference").glob("*.glb"))
        ],
        "mouth_references": [
            rel(path)
            for path in sorted((ASSET_LIBRARY_ROOT / "face_mouth_reference").glob("*.glb"))
        ],
        "hair_references": [
            rel(path)
            for path in sorted((ASSET_LIBRARY_ROOT / "hair_reference").glob("*.glb"))
        ],
        "motion_references": [
            rel(path)
            for path in sorted((ASSET_LIBRARY_ROOT / "motion_reference").glob("*.glb"))
        ],
        "adult_anatomy_references": [
            rel(path)
            for path in sorted((ASSET_LIBRARY_ROOT / "adult_anatomy_reference").glob("*.glb"))
        ],
    }


def require_gwen_candidate(candidate_id: str) -> str:
    """Reject every candidate except the canonical adult Gwen subject."""
    if candidate_id != GWEN_ID:
        raise ValueError(
            "This is a Gwen-specific subject-school runner and may only modify "
            f"candidate {GWEN_ID!r}; received {candidate_id!r}."
        )
    return candidate_id


def validate_gwen_body_selection(candidate_id: str, source_model: str | Path) -> dict:
    """Fail closed unless canonical adult Gwen is using the required adult-only base."""
    require_gwen_candidate(candidate_id)
    source_path = Path(source_model)
    if not source_path.is_absolute():
        source_path = ROOT / source_path
    if not source_model or not source_path.exists():
        raise ValueError(f"Required Gwen adult base is missing: {GWEN_REQUIRED_BASE}")
    if source_path.resolve() != GWEN_REQUIRED_BASE.resolve():
        raise ValueError(
            "Gwen subject school must use the required adult-only base "
            f"{rel(GWEN_REQUIRED_BASE)!r}; received {rel(source_path)!r}."
        )
    actual_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if actual_sha256 != GWEN_REQUIRED_BASE_SHA256:
        raise ValueError(
            "Gwen subject school body-policy validation failed closed: "
            "required adult base exact identity does not match the reviewed asset."
        )

    maturity_policy = infer_avatar_maturity_policy(
        candidate_id,
        {
            "display_name": "Spider-Gwen / Gwen Stacy",
            "age_review": {
                "maturity_class_override": "adult",
                "reason": "Canonical Gwen subject-school profile is confirmed adult.",
            },
        },
    )
    selected_base = {
        "id": "base_body_reference:womenfemale_body_base_rigged_3ec62ba8d7",
        "filename": GWEN_REQUIRED_BASE.name,
        "local_file": rel(GWEN_REQUIRED_BASE),
        "category": "base_body_reference",
        "adult_only": True,
        "allowed_for_non_adult": False,
        "sha256": actual_sha256,
    }
    validation = validate_avatar_body_policy(
        maturity_policy,
        body_treatment="neutral_adult_anatomy",
        selected_assets=[selected_base],
    )
    if maturity_policy.get("maturity_class") != "adult" or validation.get("status") != "passed":
        raise ValueError(
            "Gwen body-policy validation failed closed: "
            + ", ".join(validation.get("failures") or ["adult maturity was not confirmed"])
        )
    return {
        "maturity_policy": maturity_policy,
        "validation": validation,
        "selected_base": selected_base,
        "selected_base_sha256": actual_sha256,
    }


def gwen_subject_profile(candidate_id: str, source_roots: list[str]) -> dict:
    require_gwen_candidate(candidate_id)
    temp_root = AVATAR_TEMP_DIR / candidate_id
    models_root = ROOT / "Avatar" / "models" / "temp_ai" / candidate_id
    assets = asset_paths()
    body_policy_gate = validate_gwen_body_selection(candidate_id, assets["female_base_model"])
    return {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "display_name": "Spider-Gwen / Gwen Stacy",
        "age_review": {
            "maturity_class_override": "adult",
            "reason": "Canonical Gwen subject-school profile is confirmed adult.",
            "source": "Gwen-specific Avatar Builder subject school",
        },
        "subject_policy": {
            "maturity_class": "adult",
            "base_body": "adult_female_rig",
            "adult_anatomy_allowed": True,
            "non_adult_doll_safe_policy_allowed": False,
            "reference_model_copying_allowed": False,
            "third_party_models_are_reference_only": True,
            "wardrobe_not_body": True,
        },
        "source_roots": source_roots,
        "required_source_model": assets["female_base_model"],
        "required_source_asset_policy": body_policy_gate["selected_base"],
        "body_policy_validation": body_policy_gate["validation"],
        "reference_manifests": [
            rel(temp_root / "gwen_reference_audit_20260712.json"),
            rel(temp_root / "gwen_chat_reference_batch_20260712.json"),
            rel(temp_root / "gwen_chat_reference_batch_20260712_2.json"),
            FOLDER_45_REFERENCE_MANIFESTS["folder_45_index"],
            FOLDER_45_REFERENCE_MANIFESTS["folder_40_index"],
            FOLDER_45_REFERENCE_MANIFESTS["gwen"],
            FOLDER_45_REFERENCE_MANIFESTS["harley_quinn"],
            FOLDER_45_REFERENCE_MANIFESTS["batgirl"],
            FOLDER_45_REFERENCE_MANIFESTS["adult_anatomy"],
            FOLDER_45_REFERENCE_MANIFESTS["adult_female_shape"],
            FOLDER_45_REFERENCE_MANIFESTS["hand"],
            FOLDER_45_REFERENCE_MANIFESTS["head_expression"],
            "Avatar/avatar_builder/reference_routing/spider_gwen_realistic_adult_rebuild_brief_20260712.json",
            "Avatar/avatar_builder/reference_routing/spider_gwen_spiderverse_movie_reference_search_20260712.json",
        ],
        "method_sources": BLENDER_METHOD_SOURCES,
        "reference_models": {
            "saved_unmasked_gwen_reference": "Assets/third_party/intake/3d_models_kira_world/characters/spider_gwen/spider_gwen_low_poly_unmasked_reference.glb",
            "folder_45_unmasked_gwen_and_related_refs": FOLDER_45_REFERENCE_MANIFESTS["gwen"],
            "folder_40_harley_adult_character_stage_reference": FOLDER_45_REFERENCE_MANIFESTS["harley_quinn"],
            "folder_40_batgirl_gotham_dc_reference": FOLDER_45_REFERENCE_MANIFESTS["batgirl"],
            "folder_40_adult_anatomy_structure_reference": FOLDER_45_REFERENCE_MANIFESTS["adult_anatomy"],
            "folder_40_adult_female_shape_reference": FOLDER_45_REFERENCE_MANIFESTS["adult_female_shape"],
            "folder_45_hand_refs": FOLDER_45_REFERENCE_MANIFESTS["hand"],
            "folder_45_head_expression_refs": FOLDER_45_REFERENCE_MANIFESTS["head_expression"],
            "existing_runtime_or_failed_previews": [
                rel(models_root / "avatar.glb"),
                rel(models_root / "avatar_builder_reference_pass_20260712.glb"),
                rel(models_root / "avatar_builder_base_body_pass_20260712.glb"),
                rel(models_root / "avatar_builder_silhouette_overlay_calibration_20260712.glb"),
            ],
            "asset_library": assets,
        },
        "visual_identity_targets": [
            "adult Gwen Stacy from Spider-Verse movie references",
            "more realistic than movie/comic style while staying recognizable",
            "blue-gray expressive eyes seated in sockets",
            "asymmetrical blonde side-swept hair with short side / undercut influence",
            "athletic adult body shaped on the female rig, not doll-safe and not costume-baked",
            "Ghost-Spider suit as removable wardrobe layer",
        ],
    }


def build_assignment(
    *,
    run_id: str,
    candidate_id: str,
    cycle_index: int,
    lesson: dict,
    profile: dict,
    run_dir: Path,
    assignment_dir: Path,
) -> dict:
    require_gwen_candidate(candidate_id)
    stage_id = f"{cycle_index:03d}_{lesson['id']}"
    stage_dir = assignment_dir / stage_id
    artifact_plan = [
        {
            "name": name,
            "expected_path": rel(stage_dir / name),
            "status": "missing_until_builder_generates_visual_proof",
        }
        for name in lesson["expected_artifacts"]
    ]
    assignment = {
        "schema_version": 1,
        "created_at": utc_now(),
        "run_id": run_id,
        "candidate_id": candidate_id,
        "cycle_index": cycle_index,
        "lesson_id": lesson["id"],
        "lesson_title": lesson["title"],
        "focus": lesson["focus"],
        "lesson_goal": lesson["lesson_goal"],
        "method_sources": lesson.get("method_sources", BLENDER_METHOD_SOURCES),
        "local_reference_manifests": FOLDER_45_REFERENCE_MANIFESTS,
        "subject_profile": profile,
        "builder_tasks": lesson["builder_tasks"],
        "expected_artifacts": artifact_plan,
        "pass_checks": lesson["pass_checks"],
        "fail_hard_if": lesson.get(
            "fail_hard_if",
            [
                "The artifact is only vague JSON with no visible proof when a visible result was required.",
                "The builder copies a reference model as the avatar body.",
                "The builder marks a failed likeness/body/hair/eye result as usable.",
            ],
        ),
        "communication_required": [
            "Write what was attempted.",
            "Write what visual proof was produced.",
            "Write what still fails.",
            "If a user correction is needed, ask it directly instead of hiding the failure.",
        ],
        "grade": {
            "current_grade": "queued_subject_stage_needs_constructed_visual_proof",
            "reason": (
                "The subject school has staged the lesson, but the Avatar Builder must produce and save "
                "the expected renders/models before this lesson can pass."
            ),
        },
        "strict_rules": [
            "Reference models can teach proportions, topology, hair, eyes, movement, and clothing, but cannot be copied as the AI body.",
            "Gwen is adult for this run: adult anatomy references are allowed for neutral body correctness.",
            "Doll-safe / Barbie treatment is only for non-adult subjects and must not be applied to Gwen.",
            "Costume, hair, shoes, gloves, hood, and accessories are separate from the base body.",
            "Any visual proof that looks wrong must be marked failed instead of hidden.",
        ],
        "next_builder_action": lesson["builder_tasks"][0],
    }
    write_json(stage_dir / "assignment.json", assignment)
    write_json(run_dir / f"{stage_id}.json", assignment)
    return assignment


def update_index(index_path: Path, assignment: dict) -> None:
    index = read_json(index_path, {"schema_version": 1, "assignments": []})
    entries = index.setdefault("assignments", [])
    entries.append(
        {
            "created_at": assignment["created_at"],
            "cycle_index": assignment["cycle_index"],
            "lesson_id": assignment["lesson_id"],
            "lesson_title": assignment["lesson_title"],
            "grade": assignment["grade"]["current_grade"],
            "assignment_path": rel(
                ASSIGNMENT_ROOT
                / assignment["run_id"]
                / f"{assignment['cycle_index']:03d}_{assignment['lesson_id']}"
                / "assignment.json"
            ),
        }
    )
    index["updated_at"] = utc_now()
    write_json(index_path, index)


def append_progress(progress_path: Path, assignment: dict) -> dict:
    progress = read_json(
        progress_path,
        {
            "schema_version": 1,
            "candidate_id": assignment["candidate_id"],
            "run_id": assignment["run_id"],
            "status": "running",
            "started_at": assignment["created_at"],
            "stages": [],
        },
    )
    if progress.get("run_id") != assignment["run_id"]:
        progress = {
            "schema_version": 1,
            "candidate_id": assignment["candidate_id"],
            "run_id": assignment["run_id"],
            "status": "running",
            "started_at": assignment["created_at"],
            "stages": [],
        }
    stages = progress.setdefault("stages", [])
    stages.append(
        {
            "created_at": assignment["created_at"],
            "cycle_index": assignment["cycle_index"],
            "lesson_id": assignment["lesson_id"],
            "lesson_title": assignment["lesson_title"],
            "focus": assignment["focus"],
            "grade": assignment["grade"]["current_grade"],
            "next_builder_action": assignment["next_builder_action"],
            "assignment_path": rel(
                ASSIGNMENT_ROOT
                / assignment["run_id"]
                / f"{assignment['cycle_index']:03d}_{assignment['lesson_id']}"
                / "assignment.json"
            ),
        }
    )
    progress["updated_at"] = utc_now()
    progress["latest_lesson_id"] = assignment["lesson_id"]
    progress["latest_lesson_title"] = assignment["lesson_title"]
    progress["status"] = "running"
    write_json(progress_path, progress)
    return progress


def add_unique_target(targets: list, lesson: dict, assignment: dict) -> None:
    instruction = f"[Subject School: Gwen] {lesson['lesson_goal']}"
    for target in targets:
        if target.get("source") == "Avatar Builder Subject School" and target.get("area") == lesson["id"]:
            target["updated_at"] = utc_now()
            target["status"] = "queued_subject_stage_needs_visual_proof"
            target["instruction"] = instruction
            return
    targets.append(
        {
            "created_at": assignment["created_at"],
            "updated_at": assignment["created_at"],
            "area": lesson["id"],
            "source": "Avatar Builder Subject School",
            "instruction": instruction,
            "status": "queued_subject_stage_needs_visual_proof",
            "assignment_path": rel(
                ASSIGNMENT_ROOT
                / assignment["run_id"]
                / f"{assignment['cycle_index']:03d}_{assignment['lesson_id']}"
                / "assignment.json"
            ),
        }
    )


def update_candidate_adjustments(candidate_id: str, assignment: dict, progress_path: Path, index_path: Path) -> None:
    body_policy_gate = validate_gwen_body_selection(candidate_id, asset_paths()["female_base_model"])
    path = AVATAR_TEMP_DIR / candidate_id / "avatar_builder_adjustments.json"
    data = read_json(path, {})
    data.setdefault("schema_version", 1)
    data["candidate_id"] = candidate_id
    data["builder"] = "avatar_builder"
    data["updated_at"] = utc_now()
    data["maturity_override"] = "adult"
    data["subject_school_status"] = "running"
    data["subject_school_current_run"] = assignment["run_id"]
    data["subject_school_latest_lesson"] = assignment["lesson_id"]
    data["subject_school_latest_lesson_title"] = assignment["lesson_title"]
    data["subject_school_progress"] = rel(progress_path)
    data["subject_school_assignment_index"] = rel(index_path)
    data["subject_school_last_assignment"] = rel(
        ASSIGNMENT_ROOT
        / assignment["run_id"]
        / f"{assignment['cycle_index']:03d}_{assignment['lesson_id']}"
        / "assignment.json"
    )
    data["approval_status"] = "subject_school_in_progress_not_approved"
    data["adult_anatomy_policy"] = "adult_anatomy_allowed_for_gwen_neutral_body"
    data["non_adult_doll_safe_policy"] = "not_allowed_for_gwen_adult_subject"
    data["body_policy_validation"] = body_policy_gate["validation"]
    data["selected_base_asset_policy"] = body_policy_gate["selected_base"]
    data["reference_copy_policy"] = "disallow_copying_reference_models_as_candidate_body"
    targets = data.setdefault("build_targets", [])
    if not isinstance(targets, list):
        targets = []
        data["build_targets"] = targets
    lesson = next(item for item in SUBJECT_LESSONS if item["id"] == assignment["lesson_id"])
    add_unique_target(targets, lesson, assignment)
    notes = data.setdefault("learning_notes", [])
    if isinstance(notes, list):
        notes.append(
            {
                "created_at": assignment["created_at"],
                "tags": [
                    "avatar_builder_subject_school",
                    "gwen",
                    assignment["lesson_id"],
                    "needs_visual_proof",
                ],
                "text": (
                    f"Subject school staged Gwen lesson '{assignment['lesson_title']}'. "
                    "This is not approved until the expected visual proofs exist and Robert reviews them."
                ),
            }
        )
        del notes[:-80]
    write_json(path, data)


def update_candidate_subject_status(candidate_id: str, run_id: str, status: str, progress_path: Path, index_path: Path) -> None:
    require_gwen_candidate(candidate_id)
    path = AVATAR_TEMP_DIR / candidate_id / "avatar_builder_adjustments.json"
    data = read_json(path, {})
    data["updated_at"] = utc_now()
    data["subject_school_status"] = status
    data["subject_school_current_run"] = run_id
    data["subject_school_progress"] = rel(progress_path)
    data["subject_school_assignment_index"] = rel(index_path)
    if status != "running":
        data["approval_status"] = "subject_school_finished_not_approved"
    write_json(path, data)


def write_presence(
    *,
    run_id: str,
    candidate_id: str,
    cycle_index: int,
    lesson: dict,
    run_dir: Path,
    progress_path: Path,
    index_path: Path,
    status: str = "running",
) -> None:
    require_gwen_candidate(candidate_id)
    write_json(
        SUBJECT_PRESENCE_PATH,
        {
            "schema_version": 1,
            "status": status,
            "updated_at": utc_now(),
            "pid": os.getpid(),
            "run_id": run_id,
            "candidate_id": candidate_id,
            "cycle_index": cycle_index,
            "current_lesson": lesson["id"],
            "current_lesson_title": lesson["title"],
            "run_folder": rel(run_dir),
            "progress_path": rel(progress_path),
            "assignment_index": rel(index_path),
            "stop_file": rel(SUBJECT_STOP_PATH),
        },
    )


def stop_requested() -> bool:
    return SUBJECT_STOP_PATH.exists()


def run_real_artifact_pass(candidate_id: str, run_id: str, run_dir: Path) -> int:
    """Generate the GLB/render proof pass so lessons do not stop at JSON."""
    validate_gwen_body_selection(candidate_id, asset_paths()["female_base_model"])
    if not REAL_MODEL_PASS_SCRIPT.exists():
        write_json(
            run_dir / "real_artifact_pass_result.json",
            {
                "schema_version": 1,
                "created_at": utc_now(),
                "status": "failed_missing_real_model_pass_script",
                "script": rel(REAL_MODEL_PASS_SCRIPT),
            },
        )
        return 2
    command = [
        sys.executable,
        str(REAL_MODEL_PASS_SCRIPT),
        "--candidate-id",
        candidate_id,
        "--run-id",
        run_id,
    ]
    result = subprocess.run(command, cwd=str(ROOT), text=True, capture_output=True)
    write_json(
        run_dir / "real_artifact_pass_result.json",
        {
            "schema_version": 1,
            "created_at": utc_now(),
            "status": "completed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "command": command,
            "stdout_tail": result.stdout[-6000:],
            "stderr_tail": result.stderr[-6000:],
        },
    )
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Avatar Builder School on one live subject.")
    parser.add_argument("--candidate-id", default=GWEN_ID)
    parser.add_argument("--duration-hours", type=float, default=4.0)
    parser.add_argument("--cycle-minutes", type=float, default=15.0)
    parser.add_argument("--max-cycles", type=int, default=0)
    parser.add_argument(
        "--start-lesson-id",
        default="",
        help="Optional lesson id to start from, useful for staging one targeted assignment.",
    )
    parser.add_argument("--source-root", action="append", default=[])
    parser.add_argument(
        "--stop-generic-school",
        action="store_true",
        help="Write the old generic school stop file before starting this subject run.",
    )
    parser.add_argument(
        "--skip-real-artifacts",
        action="store_true",
        help="Emergency/debug only: do not generate the final GLB and proof artifacts after the lesson loop.",
    )
    args = parser.parse_args()

    try:
        candidate_id = require_gwen_candidate(args.candidate_id)
    except ValueError as exc:
        parser.error(str(exc))
    if not (AVATAR_TEMP_DIR / candidate_id).exists():
        raise SystemExit(f"Candidate not found: {candidate_id}")
    profile = gwen_subject_profile(candidate_id, args.source_root)

    PRESENCE_DIR.mkdir(parents=True, exist_ok=True)
    if SUBJECT_STOP_PATH.exists():
        SUBJECT_STOP_PATH.unlink()
    if args.stop_generic_school:
        write_json(
            GENERIC_STOP_PATH,
            {
                "stop_requested_at": utc_now(),
                "reason": "Subject school is replacing the generic Avatar Builder School loop for Gwen.",
            },
        )

    run_id = f"avatar_builder_subject_school_{slug(candidate_id)}_{compact_stamp()}"
    run_dir = SESSION_ROOT / run_id
    assignment_dir = ASSIGNMENT_ROOT / run_id
    index_path = assignment_dir / "assignment_index.json"
    progress_path = AVATAR_TEMP_DIR / candidate_id / "avatar_builder_subject_school_progress.json"
    run_dir.mkdir(parents=True, exist_ok=True)
    assignment_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "subject_profile.json", profile)

    cycle_seconds = max(1.0, args.cycle_minutes * 60.0)
    end_time = time.time() + max(0.01, args.duration_hours) * 3600.0
    cycle_index = 0
    latest_lesson = SUBJECT_LESSONS[0]
    lesson_offset = 0
    if args.start_lesson_id:
        for index, lesson in enumerate(SUBJECT_LESSONS):
            if lesson["id"] == args.start_lesson_id:
                lesson_offset = index
                latest_lesson = lesson
                break
        else:
            known = ", ".join(lesson["id"] for lesson in SUBJECT_LESSONS)
            raise SystemExit(f"Unknown start lesson id: {args.start_lesson_id}. Known lessons: {known}")

    while time.time() < end_time and not stop_requested():
        if args.max_cycles and cycle_index >= args.max_cycles:
            break
        lesson = SUBJECT_LESSONS[(lesson_offset + cycle_index) % len(SUBJECT_LESSONS)]
        latest_lesson = lesson
        assignment = build_assignment(
            run_id=run_id,
            candidate_id=candidate_id,
            cycle_index=cycle_index,
            lesson=lesson,
            profile=profile,
            run_dir=run_dir,
            assignment_dir=assignment_dir,
        )
        update_index(index_path, assignment)
        progress = append_progress(progress_path, assignment)
        update_candidate_adjustments(candidate_id, assignment, progress_path, index_path)
        write_json(
            run_dir / "latest_status.json",
            {
                "schema_version": 1,
                "updated_at": utc_now(),
                "run_id": run_id,
                "candidate_id": candidate_id,
                "cycle_index": cycle_index,
                "lesson": lesson,
                "progress_path": rel(progress_path),
                "assignment_index": rel(index_path),
                "stages_completed_this_run": len(progress.get("stages", [])),
            },
        )
        write_presence(
            run_id=run_id,
            candidate_id=candidate_id,
            cycle_index=cycle_index,
            lesson=lesson,
            run_dir=run_dir,
            progress_path=progress_path,
            index_path=index_path,
        )
        cycle_index += 1
        if args.max_cycles and cycle_index >= args.max_cycles:
            break
        sleep_until = min(end_time, time.time() + cycle_seconds)
        while time.time() < sleep_until:
            if stop_requested():
                break
            time.sleep(min(5.0, sleep_until - time.time()))

    final_status = "stopped" if stop_requested() else "completed"
    progress = read_json(progress_path, {})
    progress["status"] = final_status
    progress["updated_at"] = utc_now()
    progress["finished_at"] = utc_now()
    write_json(progress_path, progress)
    write_json(
        run_dir / "run_summary.json",
        {
            "schema_version": 1,
            "status": final_status,
            "updated_at": utc_now(),
            "run_id": run_id,
            "candidate_id": candidate_id,
            "cycles_completed": cycle_index,
            "progress_path": rel(progress_path),
            "assignment_index": rel(index_path),
            "approval": "not_approved_until_visual_proofs_and_robert_review",
        },
    )
    write_presence(
        run_id=run_id,
        candidate_id=candidate_id,
        cycle_index=max(0, cycle_index - 1),
        lesson=latest_lesson,
        run_dir=run_dir,
        progress_path=progress_path,
        index_path=index_path,
        status=final_status,
    )
    update_candidate_subject_status(candidate_id, run_id, final_status, progress_path, index_path)
    if args.skip_real_artifacts or cycle_index <= 0:
        return 0
    artifact_returncode = run_real_artifact_pass(candidate_id, run_id, run_dir)
    if artifact_returncode != 0:
        progress = read_json(progress_path, {})
        progress["status"] = "completed_but_real_artifact_pass_failed"
        progress["updated_at"] = utc_now()
        write_json(progress_path, progress)
        update_candidate_subject_status(candidate_id, run_id, "completed_but_real_artifact_pass_failed", progress_path, index_path)
    return artifact_returncode


if __name__ == "__main__":
    raise SystemExit(main())
