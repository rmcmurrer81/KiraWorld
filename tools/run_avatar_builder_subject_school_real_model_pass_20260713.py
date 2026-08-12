"""Generate real model artifacts for an Avatar Builder subject-school run.

The 2026-07-12 subject school produced assignment JSON but no model/renders.
This wrapper fixes that failure mode:

1. Normal Python resolves the latest subject-school run and launches Blender.
2. Blender builds a rough real Gwen model from the adult female base body, not
   from copied Gwen/reference meshes.
3. Blender exports a GLB and proof renders.
4. Normal Python creates GIF/contact-sheet proofs and audits the assignments.

This is still not an approval/likeness pass. It is a real-artifact pass so
Robert has something concrete to review instead of JSON-only homework.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.avatar_asset_library import (  # noqa: E402
    infer_avatar_maturity_policy,
    validate_avatar_body_policy,
)

PRESENCE_PATH = ROOT / "Data" / "presence" / "current_avatar_builder_subject_school_run.json"
AVATAR_MODELS = ROOT / "Avatar" / "models" / "temp_ai"
AVATAR_TEMP = ROOT / "Avatar" / "temp_ai"
BUILDER_ROOT = ROOT / "Avatar" / "avatar_builder"
SCHOOL_ROOT = BUILDER_ROOT / "school"
SUBJECT_RUN_ROOT = SCHOOL_ROOT / "subject_runs"
ASSIGNMENT_ROOT = SCHOOL_ROOT / "assignments" / "subject_runs"
GWEN_ID = "spider_gwen_spider_gwen_20260606_013325"
BLENDER_EXE = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
BASE_FEMALE = BUILDER_ROOT / "asset_library" / "base_body_reference" / "womenfemale_body_base_rigged_3ec62ba8d7.glb"
BASE_FEMALE_SHA256 = "3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e"
GWEN_OVERLAY_PASS = (
    BUILDER_ROOT
    / "body_training"
    / "overlay_passes"
    / "20260712_robert_f_grade"
    / GWEN_ID
    / f"{GWEN_ID}_silhouette_overlay_pass_20260712.json"
)


def now_iso() -> str:
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


def require_gwen_candidate(candidate_id: str) -> str:
    """Reject every candidate except the canonical adult Gwen subject."""
    if candidate_id != GWEN_ID:
        raise ValueError(
            "This real-model pass is Gwen-specific and may only modify "
            f"candidate {GWEN_ID!r}; received {candidate_id!r}."
        )
    return candidate_id


def validate_gwen_body_selection(candidate_id: str, source_model: str | Path = BASE_FEMALE) -> dict[str, Any]:
    """Fail closed unless confirmed-adult Gwen uses the required adult-only base."""
    require_gwen_candidate(candidate_id)
    source_path = Path(source_model)
    if not source_path.is_absolute():
        source_path = ROOT / source_path
    if not source_model or not source_path.exists():
        raise ValueError(f"Required Gwen adult base is missing: {BASE_FEMALE}")
    if source_path.resolve() != BASE_FEMALE.resolve():
        raise ValueError(
            f"Gwen real-model pass requires adult-only base {rel(BASE_FEMALE)!r}; "
            f"received {rel(source_path)!r}."
        )
    actual_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if actual_sha256 != BASE_FEMALE_SHA256:
        raise ValueError(
            "Gwen body-policy validation failed closed: required adult base exact "
            "identity does not match the reviewed asset."
        )

    maturity_policy = infer_avatar_maturity_policy(
        candidate_id,
        {
            "display_name": "Spider-Gwen / Gwen Stacy",
            "age_review": {
                "maturity_class_override": "adult",
                "reason": "Canonical Gwen real-model subject is confirmed adult.",
            },
        },
    )
    selected_base = {
        "id": "base_body_reference:womenfemale_body_base_rigged_3ec62ba8d7",
        "filename": BASE_FEMALE.name,
        "local_file": rel(BASE_FEMALE),
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


def require_gwen_run(run_id: str, candidate_id: str) -> dict[str, Any]:
    """Verify that a subject-school run itself belongs to canonical Gwen."""
    require_gwen_candidate(candidate_id)
    profile_path = SUBJECT_RUN_ROOT / run_id / "subject_profile.json"
    profile = read_json(profile_path, {})
    recorded_candidate = str(profile.get("candidate_id") or "")
    if recorded_candidate != GWEN_ID:
        raise ValueError(
            f"Run {run_id!r} is not a verified Gwen subject-school run; "
            f"subject profile recorded {recorded_candidate or 'no candidate'!r}."
        )
    return profile


def candidate_adjustments(candidate_id: str) -> dict[str, Any]:
    return read_json(AVATAR_TEMP / candidate_id / "avatar_builder_adjustments.json", {})


def target_height_for_candidate(candidate_id: str, default_m: float = 1.68) -> dict[str, Any]:
    adjustments = candidate_adjustments(candidate_id)
    raw = adjustments.get("target_height_m")
    try:
        height_m = float(raw)
    except (TypeError, ValueError):
        height_m = default_m
    if not 1.2 <= height_m <= 2.2:
        height_m = default_m
    return {
        "height_m": round(height_m, 3),
        "source": adjustments.get("target_height_source") or ("Robert chat" if raw else "builder default"),
        "from_adjustments": bool(raw),
        "adult_body_fit_plan": adjustments.get("adult_body_fit_plan") or "",
        "adult_body_fit_status": adjustments.get("adult_body_fit_status") or "",
    }


def resolve_run_id(explicit: str | None) -> str:
    if explicit:
        return explicit
    presence = read_json(PRESENCE_PATH, {})
    run_id = presence.get("run_id")
    if run_id:
        return str(run_id)
    runs = sorted(SUBJECT_RUN_ROOT.glob("avatar_builder_subject_school_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if runs:
        return runs[0].name
    raise SystemExit("No subject-school run was found.")


def find_blender() -> Path:
    if BLENDER_EXE.exists():
        return BLENDER_EXE
    candidates = sorted(Path(r"C:\Program Files\Blender Foundation").glob("Blender *\\blender.exe"), reverse=True)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit("Blender executable was not found.")


def stage_dirs(run_id: str) -> list[Path]:
    root = ASSIGNMENT_ROOT / run_id
    return sorted(path for path in root.iterdir() if path.is_dir() and (path / "assignment.json").exists())


def view_for_artifact(name: str) -> str:
    lowered = name.lower()
    if "robe" in lowered or "towel" in lowered:
        return "soft_goods_not_generated"
    if "eye_side" in lowered or "side_socket" in lowered:
        return "eye_side"
    if "eye" in lowered:
        return "eye_front"
    if "hair_side_right" in lowered:
        return "hair_side_right"
    if "hair_side" in lowered:
        return "hair_side_left"
    if "hair" in lowered:
        return "hair_front"
    if "mouth" in lowered or "viseme" in lowered or "expression" in lowered:
        return "mouth_close"
    if "back" in lowered:
        return "back_body"
    if "side" in lowered:
        return "side_body"
    if "suit_on" in lowered:
        return "suit_on"
    if "suit_off" in lowered or "neutral" in lowered:
        return "front_body"
    if "contact" in lowered or "review" in lowered:
        return "contact_sheet"
    return "front_body"


def artifact_manifest_path(run_id: str) -> Path:
    return SUBJECT_RUN_ROOT / run_id / "real_model_artifacts" / "artifact_manifest.json"


def create_gif_from_png(source_png: Path, output_gif: Path) -> None:
    from PIL import Image

    output_gif.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_png) as image:
        frame = image.convert("P", palette=Image.Palette.ADAPTIVE)
        frame.save(output_gif, save_all=True, append_images=[frame], duration=600, loop=0)


def make_contact_sheet(run_id: str, views: dict[str, str], out_path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    keys = [
        "front_body",
        "side_body",
        "back_body",
        "head_front",
        "eye_front",
        "eye_side",
        "hair_front",
        "mouth_close",
        "suit_on",
    ]
    tile_w, tile_h = 360, 430
    header = 62
    sheet = Image.new("RGB", (tile_w * 3, tile_h * 3 + header), (12, 22, 32))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 18)
        small = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font = ImageFont.load_default()
        small = ImageFont.load_default()
    draw.text((18, 18), f"Gwen real-model subject-school proof: {run_id}", fill=(236, 245, 250), font=font)
    for index, key in enumerate(keys):
        source = views.get(key)
        x = (index % 3) * tile_w
        y = header + (index // 3) * tile_h
        draw.rectangle((x + 8, y + 8, x + tile_w - 8, y + tile_h - 8), outline=(48, 90, 125), width=2)
        if source and (ROOT / source).exists():
            with Image.open(ROOT / source) as img:
                img = img.convert("RGB")
                img.thumbnail((tile_w - 28, tile_h - 58))
                sheet.paste(img, (x + (tile_w - img.width) // 2, y + 20))
        draw.text((x + 16, y + tile_h - 30), key, fill=(210, 230, 240), font=small)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def finalize_assignments(run_id: str) -> dict:
    manifest = read_json(artifact_manifest_path(run_id), {})
    if not manifest:
        raise SystemExit(f"Real model artifact manifest missing for run {run_id}.")
    candidate_id = require_gwen_candidate(str(manifest.get("candidate_id") or ""))
    require_gwen_run(run_id, candidate_id)
    body_policy_gate = validate_gwen_body_selection(candidate_id, str(manifest.get("source_base") or ""))
    manifest["selected_base_asset_policy"] = body_policy_gate["selected_base"]
    manifest["body_policy_validation"] = body_policy_gate["validation"]
    quality_gate = manifest.get("visual_quality_gate_data") or {}
    quality_failed = (
        str(quality_gate.get("status") or "").lower() == "failed"
        or str(quality_gate.get("grade") or "").upper() == "F"
    )

    views: dict[str, str] = manifest.get("views", {})
    model_path = ROOT / manifest["model"]
    contact_sheet = SUBJECT_RUN_ROOT / run_id / "real_model_artifacts" / "gwen_review_contact_sheet.png"
    make_contact_sheet(run_id, views, contact_sheet)
    views["contact_sheet"] = rel(contact_sheet)
    manifest["views"] = views

    generated: list[str] = []
    missing: list[str] = []
    for stage_dir in stage_dirs(run_id):
        stage_missing_start = len(missing)
        assignment_path = stage_dir / "assignment.json"
        assignment = read_json(assignment_path, {})
        stage_model = stage_dir / "gwen_subject_real_model.glb"
        shutil.copy2(model_path, stage_model)
        generated.append(rel(stage_model))

        actual_artifacts = assignment.setdefault("actual_artifacts", [])
        actual_artifacts.append(
            {
                "name": stage_model.name,
                "path": rel(stage_model),
                "status": "generated_real_model_for_assignment_review",
            }
        )

        for artifact in assignment.get("expected_artifacts", []):
            expected = ROOT / artifact.get("expected_path", "")
            expected.parent.mkdir(parents=True, exist_ok=True)
            name = expected.name
            suffix = expected.suffix.lower()
            if suffix == ".png":
                view_key = view_for_artifact(name)
                if view_key == "soft_goods_not_generated":
                    artifact["status"] = "missing_soft_goods_visual_proof_robe_towel_not_generated_by_gwen_body_pass"
                    missing.append(rel(expected))
                    continue
                source_rel = views.get(view_key, views.get("front_body"))
                if source_rel and (ROOT / source_rel).exists():
                    shutil.copy2(ROOT / source_rel, expected)
                    artifact["status"] = "generated_real_model_visual_proof_needs_robert_review"
                    generated.append(rel(expected))
                else:
                    artifact["status"] = "missing_render_source"
                    missing.append(rel(expected))
            elif suffix == ".gif":
                if "robe" in name.lower() or "towel" in name.lower():
                    artifact["status"] = "missing_soft_goods_motion_proof_robe_towel_not_generated_by_gwen_body_pass"
                    missing.append(rel(expected))
                    continue
                view_key = "front_body" if "front" in name.lower() else "side_body"
                source_rel = views.get(view_key, views.get("front_body"))
                if source_rel and (ROOT / source_rel).exists():
                    create_gif_from_png(ROOT / source_rel, expected)
                    artifact["status"] = "generated_single_frame_motion_gif_placeholder_needs_real_animation_later"
                    generated.append(rel(expected))
                else:
                    artifact["status"] = "missing_render_source"
                    missing.append(rel(expected))
            elif suffix == ".json":
                landmark_report = manifest.get("landmark_report_data") or {}
                body_shape_report = manifest.get("body_shape_delta_data") or {}
                overlay_report = manifest.get("overlay_fit_report_data") or {}
                report = {
                    "schema_version": 1,
                    "created_at": now_iso(),
                    "run_id": run_id,
                    "stage": stage_dir.name,
                    "candidate_id": manifest["candidate_id"],
                    "artifact_name": name,
                    "status": "generated_real_model_assignment_result_needs_robert_review",
                    "model": manifest["model"],
                    "model_copy_in_stage": rel(stage_model),
                    "source_base": manifest.get("source_base"),
                    "strict_result": "real artifact produced; likeness and rig quality are not approved yet",
                    "known_limits": manifest.get("known_limits", []),
                    "no_reference_model_copying": True,
                    "adult_policy": "Gwen is adult; adult neutral anatomy references allowed; non-adult doll-safe policy not applied.",
                }
                lowered_name = name.lower()
                if any(term in lowered_name for term in ("eye", "socket", "landmark", "measurement")):
                    report["landmark_method"] = landmark_report.get("method", "")
                    report["head_landmarks"] = landmark_report.get("head", {})
                    report["eye_socket_landmarks"] = landmark_report.get("eyes", {})
                    report["eye_measurements"] = landmark_report.get("eye_measurements", {})
                    report["reject_if"] = [
                        "eyes are not spherical",
                        "eyes are not seated from measured head/socket landmarks",
                        "eye surface protrudes in front of the measured face surface",
                        "eye centers are below the measured eye band",
                        "iris or pupil is oversized for the measured eye radius",
                    ]
                if any(term in lowered_name for term in ("mouth", "viseme", "expression")):
                    report["mouth_landmarks"] = landmark_report.get("mouth", {})
                    report["mouth_parts"] = manifest.get("generated_mouth_parts", [])
                    report["reject_if"] = [
                        "a second/debug mouth is visible below the real mouth",
                        "mouth seam is detached from the lips",
                        "teeth or tongue are visible in a closed-mouth proof",
                        "viseme controls are visible as face geometry instead of hidden rig targets",
                    ]
                if any(term in lowered_name for term in ("body", "shape", "anatomy", "overlay")):
                    report["body_shape_delta"] = body_shape_report
                    report["overlay_fit"] = overlay_report
                    report["adult_body_fit_diagnosis"] = manifest.get("adult_body_fit_diagnosis_data", {})
                    report["adult_anatomy_policy"] = {
                        "maturity_class": "adult",
                        "neutral_anatomy_reference_allowed": True,
                        "non_adult_doll_safe_applied": False,
                    }
                if "hair" in lowered_name:
                    report["hair_method"] = manifest.get("hair_method", "")
                    report["hair_parts"] = manifest.get("generated_hair_parts", [])
                    report["reject_if"] = [
                        "hair is copied from a reference model",
                        "hair is a helmet blob instead of separate cards/strands",
                        "hair intersects eyes or mouth badly",
                        "hair cannot be hidden or swapped for hood states",
                    ]
                write_json(expected, report)
                artifact["status"] = "generated_real_model_report_needs_robert_review"
                generated.append(rel(expected))
            elif suffix == ".md":
                expected.write_text(
                    "\n".join(
                        [
                            f"# Avatar Builder Communication Log - {stage_dir.name}",
                            "",
                            f"Run: `{run_id}`",
                            f"Candidate: `{manifest['candidate_id']}`",
                            "",
                            "## Attempted",
                            "- Generated a real GLB and proof renders for this assignment stage.",
                            "- Used reference models as guidance only; no character reference mesh was copied as the body.",
                            "- Used measured landmarks for eyes and recorded body/overlay reports when available.",
                            "",
                            "## Still Failing",
                            "- This proof is not approved as a Gwen likeness.",
                            "- Hair, face, body shape, eye realism, and wardrobe remain review blockers unless Robert accepts them.",
                            "",
                            "## Required Next Builder Action",
                            "- Produce visible proof for the specific lesson goal, then mark any remaining failure honestly.",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )
                artifact["status"] = "generated_builder_communication_log_needs_robert_review"
                generated.append(rel(expected))
            else:
                artifact["status"] = f"missing_unsupported_expected_artifact_type_{suffix.lstrip('.') or 'none'}"
                missing.append(rel(expected))

        stage_has_missing = len(missing) > stage_missing_start
        grade = assignment.setdefault("grade", {})
        if quality_failed:
            grade["current_grade"] = "failed_visual_quality_gate"
            grade["reason"] = (
                "The global visual quality gate failed. Generated files remain review evidence only and cannot "
                "be graded review-ready or approved."
            )
        elif stage_has_missing:
            grade["current_grade"] = "failed_missing_expected_artifacts"
            grade["reason"] = "One or more expected assignment artifacts were not generated."
        else:
            grade["current_grade"] = "real_model_artifacts_generated_needs_robert_review"
            grade["reason"] = (
                "This run produced a real GLB and proof images, but remains unapproved until Robert reviews them."
            )
        assignment["real_model_artifact_manifest"] = rel(artifact_manifest_path(run_id))
        assignment["updated_at"] = now_iso()
        write_json(assignment_path, assignment)

    manifest["contact_sheet"] = rel(contact_sheet)
    review_note_path = contact_sheet.parent / f"review_notes_{datetime.now().strftime('%Y%m%d')}.md"
    review_note_path.write_text(
        "\n".join(
            [
                "# Gwen Avatar Builder Review Notes",
                "",
                f"Run: `{run_id}`",
                f"Candidate: `{manifest['candidate_id']}`",
                f"Contact sheet: `{rel(contact_sheet)}`",
                f"Model: `{manifest['model']}`",
                "",
                "## What Is Real",
                "- This run produced a GLB, proof renders, assignment artifacts, and measurement reports.",
                "- The model was generated from the adult female base body, not copied from a reference model.",
                "- No visible mouth proxy/debug mouth is generated; the only neutral mouth is the base face mouth.",
                "- Lip-sync proof controls are exported as shape keys on the existing face mesh.",
                "- Hair is deliberately not generated in this proof because the previous rough hair made review worse; clothing is disabled because the old proxy geometry was misleading.",
                "- Adult body-fit diagnosis is written separately so adult policy cannot be mistaken for an approved body shape.",
                "",
                "## Still Not Approved",
                "- This is not an approved Gwen likeness.",
                "- The face is still generic and needs true front/side/three-quarter sculpt fitting.",
                "- Eye placement must be judged from the contact sheet; protruding or low eyes are a blocker.",
                "- Hair is still missing from this proof and needs a real hair-card/sculpt pass before likeness review can pass.",
                "- Body shape is only a coarse adult-base proportional pass and needs real landmark/lattice fitting before it can stop reading as a generic smooth base.",
                "- The suit/clothing system is disabled in this proof; production clothing still needs a separate wearable-layer pipeline.",
                "",
                "## Next Required Fix",
                "- Build a true fitting pipeline: measure reference landmarks, fit the base mesh with lattice/sculpt deltas, fit eyes into socket rims, animate the one mouth with face morphs, then build hair and clothing as separate swappable systems.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest["review_notes"] = rel(review_note_path)
    manifest["generated_assignment_artifact_count"] = len(generated)
    manifest["missing_assignment_artifact_count"] = len(missing)
    manifest["missing_assignment_artifacts"] = missing
    if quality_failed and missing:
        manifest["status"] = "real_model_artifacts_failed_visual_quality_gate_with_missing_expected_files"
    elif quality_failed:
        manifest["status"] = "real_model_artifacts_generated_failed_visual_quality_gate"
    elif missing:
        manifest["status"] = "real_model_artifacts_generated_with_missing_expected_files"
    else:
        manifest["status"] = "real_model_artifacts_generated_needs_robert_review"
    manifest["updated_at"] = now_iso()
    write_json(artifact_manifest_path(run_id), manifest)

    progress_path = AVATAR_TEMP / manifest["candidate_id"] / "avatar_builder_subject_school_progress.json"
    progress = read_json(progress_path, {})
    if progress.get("run_id") == run_id:
        for stage in progress.get("stages", []):
            if quality_failed:
                stage["grade"] = "failed_visual_quality_gate"
            elif missing:
                stage["grade"] = "failed_missing_expected_artifacts"
            else:
                stage["grade"] = "real_model_artifacts_generated_needs_robert_review"
        progress["status"] = manifest["status"]
        progress["updated_at"] = now_iso()
        progress["real_model_artifact_manifest"] = rel(artifact_manifest_path(run_id))
        progress["review_contact_sheet"] = rel(contact_sheet)
        write_json(progress_path, progress)

    adjustments_path = AVATAR_TEMP / manifest["candidate_id"] / "avatar_builder_adjustments.json"
    adjustments = read_json(adjustments_path, {})
    adjustments["updated_at"] = now_iso()
    adjustments["subject_school_status"] = manifest["status"]
    adjustments["subject_school_real_model_artifact_manifest"] = rel(artifact_manifest_path(run_id))
    adjustments["builder_preview_model_url"] = "/" + manifest["model"]
    if quality_failed:
        adjustments["builder_status"] = "real_model_generated_failed_visual_quality_gate"
        adjustments["approval_status"] = "failed_visual_quality_gate_real_artifacts_available"
    elif missing:
        adjustments["builder_status"] = "real_model_generated_missing_expected_artifacts"
        adjustments["approval_status"] = "failed_missing_expected_artifacts"
    else:
        adjustments["builder_status"] = "real_model_generated_needs_robert_review"
        adjustments["approval_status"] = "not_approved_real_model_artifacts_need_robert_review"
    adjustments.setdefault("learning_notes", []).append(
        {
            "created_at": now_iso(),
            "tags": ["avatar_builder_subject_school", "real_model_artifacts", "json_only_failure_fixed"],
            "text": (
                "Subject school now has a real GLB plus proof renders. This fixes the JSON-only failure, "
                "but the model is still not approved for likeness/body quality until Robert reviews it."
            ),
        }
    )
    write_json(adjustments_path, adjustments)

    summary_path = SUBJECT_RUN_ROOT / run_id / "run_summary.json"
    summary = read_json(summary_path, {})
    summary["status"] = manifest["status"]
    summary["real_model_artifact_manifest"] = rel(artifact_manifest_path(run_id))
    summary["review_contact_sheet"] = rel(contact_sheet)
    summary["generated_assignment_artifact_count"] = len(generated)
    summary["missing_assignment_artifact_count"] = len(missing)
    summary["updated_at"] = now_iso()
    write_json(summary_path, summary)

    return {
        "ok": not missing and not quality_failed,
        "run_id": run_id,
        "manifest": rel(artifact_manifest_path(run_id)),
        "model": manifest["model"],
        "contact_sheet": rel(contact_sheet),
        "generated_count": len(generated),
        "missing_count": len(missing),
    }


def run_normal(args: argparse.Namespace) -> int:
    candidate_id = require_gwen_candidate(args.candidate_id or GWEN_ID)
    validate_gwen_body_selection(candidate_id)
    run_id = resolve_run_id(args.run_id)
    require_gwen_run(run_id, candidate_id)
    blender = find_blender()
    command = [
        str(blender),
        "--background",
        "--python",
        str(Path(__file__).resolve()),
        "--",
        "--blender-worker",
        "--run-id",
        run_id,
    ]
    command.extend(["--candidate-id", candidate_id])
    result = subprocess.run(command, cwd=str(ROOT))
    if result.returncode != 0:
        return result.returncode
    final = finalize_assignments(run_id)
    print(json.dumps(final, indent=2))
    return 0 if final["ok"] else 2


def run_blender_worker(args: argparse.Namespace) -> int:
    import bpy  # type: ignore
    import mathutils  # type: ignore

    candidate_id = require_gwen_candidate(args.candidate_id or GWEN_ID)
    run_id = resolve_run_id(args.run_id)
    require_gwen_run(run_id, candidate_id)
    validate_gwen_body_selection(candidate_id)
    artifact_root = SUBJECT_RUN_ROOT / run_id / "real_model_artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    model_output = AVATAR_MODELS / candidate_id / f"avatar_builder_subject_school_real_model_{compact_stamp()}.glb"
    height_contract = target_height_for_candidate(candidate_id)

    def clear_scene() -> None:
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in list(bpy.data.meshes):
            bpy.data.meshes.remove(mesh)
        for mat in list(bpy.data.materials):
            bpy.data.materials.remove(mat)

    def make_material(name: str, color: tuple[float, float, float, float], roughness: float = 0.55):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = color
            bsdf.inputs["Roughness"].default_value = roughness
        return mat

    def object_bounds(obj):
        points = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
        return (
            mathutils.Vector(min(point[index] for point in points) for index in range(3)),
            mathutils.Vector(max(point[index] for point in points) for index in range(3)),
        )

    def scene_bounds():
        points = []
        for obj in bpy.context.scene.objects:
            if obj.type == "MESH":
                for corner in obj.bound_box:
                    points.append(obj.matrix_world @ mathutils.Vector(corner))
        if not points:
            return mathutils.Vector((0, 0, 0)), mathutils.Vector((0, 0, 0))
        return (
            mathutils.Vector(min(point[index] for point in points) for index in range(3)),
            mathutils.Vector(max(point[index] for point in points) for index in range(3)),
        )

    def normalize_scene(target_height: float) -> None:
        low, high = scene_bounds()
        height = max(high.z - low.z, 0.001)
        center = mathutils.Vector(((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, low.z))
        scale = target_height / height
        for obj in list(bpy.context.scene.objects):
            if obj.parent is None:
                obj.location = (obj.location - center) * scale
                obj.scale *= scale
        bpy.context.view_layer.update()

    def remove_unmaterialized_helpers() -> list[str]:
        removed: list[str] = []
        for obj in list(bpy.context.scene.objects):
            lowered = obj.name.lower()
            if obj.type == "MESH" and lowered.startswith(("icosphere", "sphere")) and not obj.data.materials:
                removed.append(obj.name)
                bpy.data.objects.remove(obj, do_unlink=True)
        return removed

    def rename_body() -> list[str]:
        renamed: list[str] = []
        for obj in bpy.context.scene.objects:
            if obj.type != "MESH":
                continue
            original = obj.name
            if obj.name.startswith("Object_85") or "body" in obj.name.lower():
                obj.name = "gwen_subject_adult_female_base_body_not_reference_copy"
                obj.data.name = f"{obj.name}_mesh"
            if obj.name != original:
                renamed.append(f"{original}->{obj.name}")
        return renamed

    def add_anchor(name: str, location: tuple[float, float, float], size: float = 0.02) -> None:
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = "SPHERE"
        empty.empty_display_size = size
        empty.location = location
        bpy.context.collection.objects.link(empty)

    def add_uv_ellipsoid(name: str, location, scale, material, segments: int = 32):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=max(8, segments // 2), radius=1.0, location=location)
        obj = bpy.context.object
        obj.name = name
        obj.data.name = f"{name}_mesh"
        obj.scale = scale
        obj.data.materials.append(material)
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        return obj

    def add_capsule_proxy(name: str, location, scale, material, rotation=(0, 0, 0)):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1.0, location=location)
        obj = bpy.context.object
        obj.name = name
        obj.data.name = f"{name}_mesh"
        obj.scale = scale
        obj.rotation_euler = rotation
        obj.data.materials.append(material)
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        return obj

    def primary_body_object():
        meshes = [
            obj
            for obj in bpy.context.scene.objects
            if obj.type == "MESH"
        ]
        named = [obj for obj in meshes if "body" in obj.name.lower()]
        candidates = named or meshes
        if not candidates:
            raise RuntimeError("No base body mesh was imported.")
        return max(
            candidates,
            key=lambda obj: max((object_bounds(obj)[1] - object_bounds(obj)[0]).length, 0.0),
        )

    def points_bounds(points):
        if not points:
            zero = mathutils.Vector((0, 0, 0))
            return zero, zero
        return (
            mathutils.Vector(min(point[index] for point in points) for index in range(3)),
            mathutils.Vector(max(point[index] for point in points) for index in range(3)),
        )

    def percentile(values: list[float], ratio: float, fallback: float) -> float:
        if not values:
            return fallback
        values = sorted(values)
        index = min(len(values) - 1, max(0, int(round((len(values) - 1) * ratio))))
        return float(values[index])

    def clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def vector_list(value) -> list[float]:
        return [round(float(value[0]), 6), round(float(value[1]), 6), round(float(value[2]), 6)]

    def mesh_world_vertices(obj) -> list:
        return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]

    def measure_subject_landmarks(body_obj) -> dict:
        verts = mesh_world_vertices(body_obj)
        low, high = points_bounds(verts)
        height = max(high.z - low.z, 0.001)
        head_floor = high.z - height * 0.18
        head_points = [point for point in verts if point.z >= head_floor]
        if len(head_points) < 24:
            head_floor = high.z - height * 0.22
            head_points = [point for point in verts if point.z >= head_floor]
        head_low, head_high = points_bounds(head_points)
        head_height = max(head_high.z - head_low.z, height * 0.12)
        head_width = max(head_high.x - head_low.x, 0.12)
        head_depth = max(head_high.y - head_low.y, 0.10)
        center_x = (head_low.x + head_high.x) * 0.5
        center_y = (head_low.y + head_high.y) * 0.5
        face_front_y = percentile([point.y for point in head_points], 0.03, head_low.y)

        face_width_estimate = clamp(head_width * 0.58, 0.13, 0.18)
        eye_z = head_low.z + head_height * 0.695
        eye_x_offset = clamp(face_width_estimate * 0.205, 0.028, 0.039)
        eye_radius = clamp(min(face_width_estimate * 0.068, head_height * 0.038), 0.0084, 0.0118)
        x_window = max(face_width_estimate * 0.12, eye_radius * 2.5)
        z_window = max(head_height * 0.08, eye_radius * 2.2)

        eyes: dict[str, dict] = {}
        warnings: list[str] = []
        for side, x_sign in (("left", -1.0), ("right", 1.0)):
            target_x = center_x + eye_x_offset * x_sign
            samples = [
                point
                for point in head_points
                if abs(point.x - target_x) <= x_window and abs(point.z - eye_z) <= z_window
            ]
            if samples:
                surface_y = percentile([point.y for point in samples], 0.08, face_front_y)
                sampled_eye_z = sum(point.z for point in samples) / len(samples)
                center_z = eye_z * 0.75 + sampled_eye_z * 0.25
            else:
                surface_y = face_front_y
                center_z = eye_z
                warnings.append(f"{side} eye used head-ratio fallback because socket samples were sparse")
            # Negative Y is the face/front direction. Keep the eye front just inside
            # the sampled face surface; the visible eyelids then read as socket rims
            # instead of the eyeball floating in front of the face.
            center = mathutils.Vector((target_x, surface_y + eye_radius * 1.45, center_z))
            eyes[side] = {
                "center": vector_list(center),
                "socket_surface_y": round(float(surface_y), 6),
                "radius": round(float(eye_radius), 6),
                "sample_count": len(samples),
                "look_target": vector_list((center.x, center.y - eye_radius * 14.0, center.z)),
                "front_surface_clearance": round(float((center.y - eye_radius) - surface_y), 6),
                "iris_radius": round(float(eye_radius * 0.43), 6),
                "pupil_radius": round(float(eye_radius * 0.20), 6),
            }

        mouth_z = head_low.z + head_height * 0.405
        mouth_samples = [
            point
            for point in head_points
            if abs(point.x - center_x) <= head_width * 0.18 and abs(point.z - mouth_z) <= head_height * 0.09
        ]
        mouth_surface_y = percentile([point.y for point in mouth_samples], 0.06, face_front_y)
        mouth_center = mathutils.Vector((center_x, mouth_surface_y + eye_radius * 0.30, mouth_z))
        return {
            "schema_version": 1,
            "created_at": now_iso(),
            "candidate_id": candidate_id,
            "method": (
                "Measured body/head bounds from the imported base mesh, isolated the head region, "
                "sampled the front eye band, and placed eyes from those landmarks instead of fixed coordinates."
            ),
            "front_axis": "negative_y",
            "body": {
                "bounds_low": vector_list(low),
                "bounds_high": vector_list(high),
                "height": round(float(height), 6),
            },
            "head": {
                "bounds_low": vector_list(head_low),
                "bounds_high": vector_list(head_high),
                "center": vector_list((center_x, center_y, (head_low.z + head_high.z) * 0.5)),
                "width": round(float(head_width), 6),
                "face_width_estimate": round(float(face_width_estimate), 6),
                "depth": round(float(head_depth), 6),
                "height": round(float(head_height), 6),
                "face_front_y": round(float(face_front_y), 6),
                "head_floor_z": round(float(head_floor), 6),
                "sample_count": len(head_points),
            },
            "eyes": eyes,
            "eye_measurements": {
                "center_spacing": round(float(abs(eyes["right"]["center"][0] - eyes["left"]["center"][0])), 6),
                "diameter": round(float(eye_radius * 2.0), 6),
                "diameter_to_head_width": round(float((eye_radius * 2.0) / head_width), 6),
                "placement_rule": "round eye sphere center is placed behind the sampled socket surface; the eye front should sit inside the eyelid opening instead of floating on the face",
            },
            "mouth": {
                "center": vector_list(mouth_center),
                "surface_y": round(float(mouth_surface_y), 6),
                "sample_count": len(mouth_samples),
            },
            "warnings": warnings,
        }

    def band_weight(value: float, low: float, high: float, fade: float = 0.025) -> float:
        if value < low or value > high:
            return 0.0
        left = 1.0 if value >= low + fade else (value - low) / max(fade, 0.001)
        right = 1.0 if value <= high - fade else (high - value) / max(fade, 0.001)
        return clamp(min(left, right), 0.0, 1.0)

    def apply_gwen_body_shape_adjustments(body_obj, landmarks: dict) -> dict:
        low = mathutils.Vector(landmarks["body"]["bounds_low"])
        high = mathutils.Vector(landmarks["body"]["bounds_high"])
        height = max(high.z - low.z, 0.001)
        center_x = (low.x + high.x) * 0.5
        center_y = (low.y + high.y) * 0.5
        head_low = mathutils.Vector(landmarks["head"]["bounds_low"])
        head_high = mathutils.Vector(landmarks["head"]["bounds_high"])
        head_height = max(head_high.z - head_low.z, height * 0.12)
        head_mid_z = (head_low.z + head_high.z) * 0.5
        inverse = body_obj.matrix_world.inverted()
        changed = 0
        max_x_delta = 0.0
        max_y_delta = 0.0
        max_z_delta = 0.0
        for vertex in body_obj.data.vertices:
            world = body_obj.matrix_world @ vertex.co
            z_norm = (world.z - low.z) / height
            head_norm = clamp((world.z - head_low.z) / head_height, 0.0, 1.0) if world.z >= head_low.z else 0.0
            shoulder = band_weight(z_norm, 0.68, 0.84)
            chest = band_weight(z_norm, 0.57, 0.70)
            waist = band_weight(z_norm, 0.46, 0.58)
            hip = band_weight(z_norm, 0.34, 0.49)
            thigh = band_weight(z_norm, 0.20, 0.36)
            calf = band_weight(z_norm, 0.09, 0.23)
            neck = band_weight(z_norm, 0.78, 0.88)
            jaw = band_weight(head_norm, 0.06, 0.26, 0.04) if world.z >= head_low.z else 0.0
            cheek = band_weight(head_norm, 0.34, 0.58, 0.05) if world.z >= head_low.z else 0.0
            cranium = band_weight(head_norm, 0.62, 1.0, 0.08) if world.z >= head_low.z else 0.0
            full_head = band_weight(head_norm, 0.03, 1.0, 0.08) if world.z >= head_low.z else 0.0
            x_factor = (
                1.0
                + shoulder * 0.025
                - chest * 0.004
                - waist * 0.035
                + hip * 0.030
                + thigh * 0.025
                + calf * 0.010
                - neck * 0.030
                - jaw * 0.040
                + cheek * 0.012
                - cranium * 0.006
                - full_head * 0.016
            )
            y_factor = (
                1.0
                + shoulder * 0.006
                - waist * 0.010
                + hip * 0.008
                + thigh * 0.006
                + jaw * 0.006
                - cranium * 0.004
                - full_head * 0.008
            )
            z_delta = 0.0
            if world.z >= head_low.z:
                z_delta -= cranium * 0.0025 * clamp((head_norm - 0.62) / 0.38, 0.0, 1.0)
            if abs(x_factor - 1.0) > 0.0001 or abs(y_factor - 1.0) > 0.0001:
                original = world.copy()
                world.x = center_x + (world.x - center_x) * x_factor
                world.y = center_y + (world.y - center_y) * y_factor
                if full_head > 0.0:
                    world.z = head_mid_z + (world.z - head_mid_z) * (1.0 - full_head * 0.014)
                world.z += z_delta
                vertex.co = inverse @ world
                changed += 1
                max_x_delta = max(max_x_delta, abs(world.x - original.x))
                max_y_delta = max(max_y_delta, abs(world.y - original.y))
                max_z_delta = max(max_z_delta, abs(world.z - original.z))
        body_obj.data.update()
        overlay = read_json(GWEN_OVERLAY_PASS, {})
        return {
            "schema_version": 1,
            "created_at": now_iso(),
            "candidate_id": candidate_id,
            "method": "Conservative adult Gwen proportion/head-shape repair pass using mild z-band mesh deltas on the female base body; no reference mesh copied.",
            "changed_vertices": changed,
            "max_x_delta_m": round(float(max_x_delta), 6),
            "max_y_delta_m": round(float(max_y_delta), 6),
            "max_z_delta_m": round(float(max_z_delta), 6),
            "bands": [
                {"name": "shoulders", "z_norm": [0.68, 0.84], "x_delta": "+2.5%"},
                {"name": "chest", "z_norm": [0.57, 0.70], "x_delta": "-0.4%"},
                {"name": "waist", "z_norm": [0.46, 0.58], "x_delta": "-3.5%", "y_delta": "-1.0%"},
                {"name": "hips", "z_norm": [0.34, 0.49], "x_delta": "+3.0%", "y_delta": "+0.8%"},
                {"name": "thighs", "z_norm": [0.20, 0.36], "x_delta": "+2.5%", "y_delta": "+0.6%"},
                {"name": "calves", "z_norm": [0.09, 0.23], "x_delta": "+1.0%"},
                {"name": "jaw_chin", "head_norm": [0.06, 0.26], "x_delta": "-4.0%", "y_delta": "+0.6%"},
                {"name": "cheekbones", "head_norm": [0.34, 0.58], "x_delta": "+1.2%"},
                {"name": "whole_head", "head_norm": [0.03, 1.0], "x_delta": "-1.6%", "y_delta": "-0.8%", "z_scale": "-1.4% toward head center"},
                {"name": "cranium_forehead", "head_norm": [0.62, 1.0], "x_delta": "-0.6%", "y_delta": "-0.4%", "z_delta": "-0.0025m"},
                {"name": "neck", "z_norm": [0.78, 0.88], "x_delta": "-3.0%"},
            ],
            "adult_policy": {
                "maturity_class": "adult",
                "neutral_anatomy_reference_allowed": True,
                "non_adult_doll_safe_applied": False,
                "adult_neutral_anatomy_preserved_from_base": True,
            },
            "overlay_source": rel(GWEN_OVERLAY_PASS),
            "overlay_source_quality": overlay.get("source_set_quality", "unknown"),
            "overlay_reference_image_count": overlay.get("reference_image_count", 0),
            "warning": (
                "This is still a coarse proportional mesh pass. It records real deltas but does not replace "
                "a true sculpt/lattice pass from high-quality front and side overlays."
            ),
        }

    def build_overlay_fit_report(body_shape_report: dict) -> dict:
        overlay = read_json(GWEN_OVERLAY_PASS, {})
        front = overlay.get("front_silhouette_stack", {}) if isinstance(overlay, dict) else {}
        side = overlay.get("side_silhouette_stack", {}) if isinstance(overlay, dict) else {}
        return {
            "schema_version": 1,
            "created_at": now_iso(),
            "candidate_id": candidate_id,
            "overlay_pass": rel(GWEN_OVERLAY_PASS),
            "status": "used_as_weak_guidance_not_as_final_likeness",
            "front_silhouette_stack": front.get("output", ""),
            "side_silhouette_stack": side.get("output", ""),
            "front_aggregate_width_height_ratio": front.get("aggregate_width_height_ratio"),
            "side_aggregate_width_height_ratio": side.get("aggregate_width_height_ratio"),
            "source_quality": overlay.get("source_set_quality", "unknown") if isinstance(overlay, dict) else "missing",
            "applied_body_shape_delta": {
                "changed_vertices": body_shape_report.get("changed_vertices", 0),
                "max_x_delta_m": body_shape_report.get("max_x_delta_m", 0),
                "max_y_delta_m": body_shape_report.get("max_y_delta_m", 0),
            },
            "next_required_builder_step": (
                "Replace this coarse band fit with a real Blender lattice/sculpt pass that pins measured head, "
                "shoulder, waist, hip, knee, and ankle landmarks to front and side image planes."
            ),
        }

    def add_eye_system(landmarks: dict) -> list[str]:
        sclera = make_material("gwen_real_pass_round_sclera_warm_white", (0.93, 0.925, 0.89, 1), 0.34)
        iris = make_material("gwen_real_pass_blue_gray_iris", (0.18, 0.34, 0.54, 1), 0.28)
        pupil = make_material("gwen_real_pass_pupil_black", (0.002, 0.002, 0.002, 1), 0.2)
        names: list[str] = []
        for side in ("left", "right"):
            eye = landmarks["eyes"][side]
            loc = tuple(eye["center"])
            radius = float(eye["radius"])
            look = tuple(eye["look_target"])
            add_anchor(f"gwen_{side}_eye_socket_anchor_landmark_real_pass", loc, 0.012)
            add_anchor(f"gwen_{side}_eye_look_target_landmark_real_pass", look, 0.010)
            add_uv_ellipsoid(f"gwen_{side}_round_eye_sclera_landmark_real_pass", loc, (radius, radius, radius), sclera, 48)
            add_uv_ellipsoid(
                f"gwen_{side}_iris_blue_gray_landmark_real_pass",
                (loc[0], loc[1] - radius * 1.015, loc[2]),
                (radius * 0.38, radius * 0.012, radius * 0.38),
                iris,
                24,
            )
            add_uv_ellipsoid(
                f"gwen_{side}_pupil_round_landmark_real_pass",
                (loc[0], loc[1] - radius * 1.030, loc[2]),
                (radius * 0.17, radius * 0.009, radius * 0.17),
                pupil,
                16,
            )
            names.extend(
                [
                    f"gwen_{side}_eye_socket_anchor_landmark_real_pass",
                    f"gwen_{side}_eye_look_target_landmark_real_pass",
                    f"gwen_{side}_round_eye_sclera_landmark_real_pass",
                    f"gwen_{side}_iris_blue_gray_landmark_real_pass",
                    f"gwen_{side}_pupil_round_landmark_real_pass",
                ]
            )
        return names

    def add_mouth_system(body_obj, landmarks: dict) -> list[str]:
        loc = mathutils.Vector(landmarks["mouth"]["center"])
        eye_radius = float(landmarks["eyes"]["left"]["radius"])
        inverse = body_obj.matrix_world.inverted()
        names: list[str] = []

        if body_obj.data.shape_keys is None:
            body_obj.shape_key_add(name="Basis")

        def mouth_weight(world) -> float:
            dx = abs(world.x - loc.x) / max(eye_radius * 3.1, 0.001)
            dz = abs(world.z - loc.z) / max(eye_radius * 2.0, 0.001)
            front_gate = 1.0 if world.y <= loc.y + eye_radius * 5.0 else 0.0
            return front_gate * clamp(1.0 - math.sqrt(dx * dx + dz * dz), 0.0, 1.0)

        def apply_shape_key(name: str, transform) -> int:
            existing = body_obj.data.shape_keys.key_blocks.get(name)
            if existing:
                key = existing
            else:
                key = body_obj.shape_key_add(name=name)
            key.value = 0.0
            changed = 0
            for index, vertex in enumerate(body_obj.data.vertices):
                world = body_obj.matrix_world @ vertex.co
                weight = mouth_weight(world)
                if weight <= 0.0:
                    continue
                lower = clamp((loc.z - world.z) / max(eye_radius * 1.25, 0.001), 0.0, 1.0)
                upper = clamp((world.z - loc.z) / max(eye_radius * 1.25, 0.001), 0.0, 1.0)
                corner = clamp((abs(world.x - loc.x) / max(eye_radius * 2.2, 0.001) - 0.42) / 0.58, 0.0, 1.0)
                delta = transform(world, weight, lower, upper, corner)
                if delta.length <= 0.000001:
                    continue
                key.data[index].co = inverse @ (world + delta)
                changed += 1
            body_obj[f"{name}_changed_vertices"] = changed
            return changed

        def jaw_open(world, weight, lower, upper, corner):
            return mathutils.Vector((0.0, eye_radius * 0.02 * weight * lower, -eye_radius * 0.72 * weight * lower))

        def wide_e(world, weight, lower, upper, corner):
            x_dir = -1.0 if world.x < loc.x else 1.0
            return mathutils.Vector((x_dir * eye_radius * 0.32 * weight * corner, 0.0, eye_radius * 0.05 * weight * corner))

        def round_o(world, weight, lower, upper, corner):
            target_x = loc.x + (world.x - loc.x) * (1.0 - 0.24 * weight)
            return mathutils.Vector((target_x - world.x, -eye_radius * 0.06 * weight, eye_radius * 0.06 * weight * (upper - lower)))

        def smile(world, weight, lower, upper, corner):
            x_dir = -1.0 if world.x < loc.x else 1.0
            return mathutils.Vector((x_dir * eye_radius * 0.24 * weight * corner, 0.0, eye_radius * 0.34 * weight * corner))

        shape_keys = [
            "gwen_mouth_viseme_A_jaw_open_shape_key",
            "gwen_mouth_viseme_E_wide_shape_key",
            "gwen_mouth_viseme_O_round_shape_key",
            "gwen_mouth_smile_shape_key",
        ]
        changed_counts = {
            shape_keys[0]: apply_shape_key(shape_keys[0], jaw_open),
            shape_keys[1]: apply_shape_key(shape_keys[1], wide_e),
            shape_keys[2]: apply_shape_key(shape_keys[2], round_o),
            shape_keys[3]: apply_shape_key(shape_keys[3], smile),
        }
        names.extend(shape_keys)

        control_offsets = {
            "lip_sync_mouth_opening_control_hidden_real_pass": (0, -eye_radius * 0.18, -eye_radius * 1.20),
            "viseme_E_wide_target_hidden_real_pass": (eye_radius * 1.50, -eye_radius * 0.18, 0),
            "viseme_O_round_target_hidden_real_pass": (0, -eye_radius * 0.18, eye_radius * 0.95),
            "smile_target_hidden_real_pass": (eye_radius * 1.70, -eye_radius * 0.18, eye_radius * 0.55),
        }
        for name, offset in control_offsets.items():
            control_name = f"gwen_{name}"
            add_anchor(control_name, (loc.x + offset[0], loc.y + offset[1], loc.z + offset[2]), 0.006)
            names.append(control_name)

        body_obj["mouth_system_rule"] = "single neutral mouth only; no visible proxy/debug mouth generated"
        body_obj["mouth_animation_method"] = "exported shape keys on existing face mesh"
        body_obj["mouth_shape_key_changed_vertices"] = json.dumps(changed_counts)
        return names

    def add_face_features(landmarks: dict) -> list[str]:
        brow = make_material("gwen_real_pass_soft_brown_brows", (0.23, 0.13, 0.07, 1), 0.50)
        lid_skin = make_material("gwen_real_pass_warm_skin_eyelid_socket_rims", (0.82, 0.60, 0.51, 1), 0.58)
        freckle = make_material("gwen_real_pass_subtle_freckle_marks", (0.33, 0.16, 0.10, 1), 0.60)
        blush = make_material("gwen_real_pass_warm_cheek_tone", (0.78, 0.42, 0.38, 1), 0.62)
        names: list[str] = []
        left = landmarks["eyes"]["left"]
        right = landmarks["eyes"]["right"]
        radius = float(left["radius"])
        for side, eye in (("left", left), ("right", right)):
            loc = tuple(eye["center"])
            x_dir = -1.0 if side == "left" else 1.0
            brow_obj = add_capsule_proxy(
                f"gwen_{side}_arched_brow_landmark_real_pass",
                (loc[0] + x_dir * radius * 0.08, loc[1] - radius * 0.76, loc[2] + radius * 1.56),
                (radius * 1.18, radius * 0.018, radius * 0.060),
                brow,
                (0, math.radians(0), math.radians(-9 * x_dir)),
            )
            cheek_obj = add_capsule_proxy(
                f"gwen_{side}_soft_cheek_tone_landmark_real_pass",
                (loc[0] + x_dir * radius * 0.85, loc[1] - radius * 0.62, loc[2] - radius * 2.20),
                (radius * 0.36, radius * 0.010, radius * 0.22),
                blush,
            )
            upper_lid = add_capsule_proxy(
                f"gwen_{side}_upper_eyelid_socket_rim_real_pass",
                (loc[0], loc[1] - radius * 1.10, loc[2] + radius * 0.54),
                (radius * 0.86, radius * 0.018, radius * 0.060),
                lid_skin,
                (0, math.radians(0), math.radians(-3 * x_dir)),
            )
            lower_lid = add_capsule_proxy(
                f"gwen_{side}_lower_eyelid_socket_rim_real_pass",
                (loc[0], loc[1] - radius * 1.105, loc[2] - radius * 0.52),
                (radius * 0.72, radius * 0.014, radius * 0.042),
                lid_skin,
                (0, math.radians(0), math.radians(2 * x_dir)),
            )
            inner_corner = add_capsule_proxy(
                f"gwen_{side}_inner_eye_corner_socket_rim_real_pass",
                (loc[0] - x_dir * radius * 0.82, loc[1] - radius * 1.105, loc[2] + radius * 0.02),
                (radius * 0.060, radius * 0.014, radius * 0.24),
                lid_skin,
            )
            outer_corner = add_capsule_proxy(
                f"gwen_{side}_outer_eye_corner_socket_rim_real_pass",
                (loc[0] + x_dir * radius * 0.82, loc[1] - radius * 1.105, loc[2] + radius * 0.02),
                (radius * 0.060, radius * 0.014, radius * 0.23),
                lid_skin,
            )
            names.extend([brow_obj.name, cheek_obj.name, upper_lid.name, lower_lid.name, inner_corner.name, outer_corner.name])
        eye_mid_x = (float(left["center"][0]) + float(right["center"][0])) * 0.5
        eye_mid_y = (float(left["center"][1]) + float(right["center"][1])) * 0.5
        eye_mid_z = (float(left["center"][2]) + float(right["center"][2])) * 0.5
        for index, x_mul in enumerate((-0.42, -0.18, 0.20, 0.48)):
            freckle_obj = add_uv_ellipsoid(
                f"gwen_subtle_freckle_{index + 1:02d}_landmark_real_pass",
                (eye_mid_x + x_mul * radius, eye_mid_y - radius * 0.72, eye_mid_z - radius * 2.05),
                (radius * 0.055, radius * 0.006, radius * 0.055),
                freckle,
                12,
            )
            names.append(freckle_obj.name)
        return names

    def add_hair_card(name: str, points: list[tuple[float, float, float]], widths: list[float], material) -> object:
        verts: list[tuple[float, float, float]] = []
        faces: list[tuple[int, int, int, int]] = []
        for point, width in zip(points, widths):
            verts.append((point[0] - width * 0.5, point[1], point[2]))
            verts.append((point[0] + width * 0.5, point[1], point[2]))
        for index in range(len(points) - 1):
            faces.append((index * 2, index * 2 + 1, index * 2 + 3, index * 2 + 2))
        mesh = bpy.data.meshes.new(f"{name}_mesh")
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        obj.data.materials.append(material)
        bpy.context.collection.objects.link(obj)
        return obj

    def add_hair(landmarks: dict) -> list[str]:
        blonde = make_material("gwen_real_pass_blonde_layered_hair", (0.82, 0.67, 0.48, 1), 0.46)
        light_blonde = make_material("gwen_real_pass_light_blonde_hair_highlights", (0.94, 0.82, 0.60, 1), 0.42)
        root = make_material("gwen_real_pass_shadow_roots", (0.38, 0.27, 0.18, 1), 0.52)
        pink = make_material("gwen_real_pass_subtle_pink_tips", (0.78, 0.32, 0.50, 1), 0.48)
        head = landmarks["head"]
        left_eye = landmarks["eyes"]["left"]
        right_eye = landmarks["eyes"]["right"]
        head_center = mathutils.Vector(head["center"])
        head_width = float(head.get("face_width_estimate") or min(float(head["width"]) * 0.58, 0.18))
        head_depth = float(head["depth"])
        head_height = float(head["height"])
        head_top = float(head["bounds_high"][2])
        front_y = float(head["face_front_y"]) - 0.006
        back_y = float(head["bounds_high"][1]) + 0.005
        eye_z = (float(left_eye["center"][2]) + float(right_eye["center"][2])) * 0.5
        mouth_z = float(landmarks["mouth"]["center"][2])
        side_x = head_center.x + head_width * 0.34
        parts = [
            add_capsule_proxy(
                "gwen_generated_scalp_cap_not_reference_copy_real_pass",
                (head_center.x + head_width * 0.04, head_center.y + head_depth * 0.02, head_top - head_height * 0.19),
                (head_width * 0.43, head_depth * 0.31, head_height * 0.105),
                blonde,
            ),
            add_capsule_proxy(
                "gwen_back_layered_hair_mass_not_reference_copy_real_pass",
                (head_center.x + head_width * 0.04, back_y - head_depth * 0.05, eye_z + head_height * 0.04),
                (head_width * 0.34, head_depth * 0.12, head_height * 0.23),
                blonde,
            ),
            add_capsule_proxy(
                "gwen_short_undercut_shadow_patch_not_reference_copy_real_pass",
                (head_center.x - head_width * 0.32, head_center.y + head_depth * 0.03, eye_z + head_height * 0.08),
                (head_width * 0.050, head_depth * 0.050, head_height * 0.12),
                root,
            ),
            add_capsule_proxy(
                "gwen_dark_side_part_ridge_not_reference_copy_real_pass",
                (head_center.x + head_width * 0.02, front_y - 0.006, head_top - head_height * 0.10),
                (head_width * 0.19, head_depth * 0.012, head_height * 0.018),
                root,
                (0, math.radians(0), math.radians(-10)),
            ),
            add_capsule_proxy(
                "gwen_long_swept_front_lock_main_real_pass",
                (side_x, front_y - 0.003, eye_z - head_height * 0.02),
                (head_width * 0.045, head_depth * 0.030, head_height * 0.33),
                light_blonde,
                (math.radians(0), math.radians(6), math.radians(-8)),
            ),
            add_capsule_proxy(
                "gwen_long_swept_front_lock_inner_real_pass",
                (head_center.x + head_width * 0.18, front_y - 0.004, eye_z + head_height * 0.07),
                (head_width * 0.035, head_depth * 0.024, head_height * 0.22),
                blonde,
                (math.radians(0), math.radians(5), math.radians(-14)),
            ),
            add_capsule_proxy(
                "gwen_short_left_side_lock_real_pass",
                (head_center.x - head_width * 0.30, front_y + head_depth * 0.20, eye_z + head_height * 0.03),
                (head_width * 0.030, head_depth * 0.026, head_height * 0.17),
                blonde,
                (math.radians(0), math.radians(-4), math.radians(8)),
            ),
            add_capsule_proxy(
                "gwen_right_back_short_layer_real_pass",
                (head_center.x + head_width * 0.27, back_y - head_depth * 0.02, eye_z + head_height * 0.02),
                (head_width * 0.042, head_depth * 0.034, head_height * 0.20),
                light_blonde,
                (math.radians(0), math.radians(2), math.radians(-4)),
            ),
            add_capsule_proxy(
                "gwen_subtle_pink_tip_on_long_lock_real_pass",
                (side_x + head_width * 0.02, front_y - 0.005, mouth_z - head_height * 0.10),
                (head_width * 0.024, head_depth * 0.020, head_height * 0.070),
                pink,
                (math.radians(0), math.radians(5), math.radians(-8)),
            ),
        ]
        return [obj.name for obj in parts]

    def add_suit_layer(hidden: bool = True) -> list[str]:
        black = make_material("gwen_removable_suit_black_spandex_layer", (0.005, 0.005, 0.006, 1), 0.28)
        white = make_material("gwen_removable_suit_white_panel_layer", (0.92, 0.92, 0.88, 1), 0.32)
        pink = make_material("gwen_removable_suit_pink_web_layer", (0.82, 0.04, 0.34, 1), 0.38)
        parts = [
            add_capsule_proxy("gwen_removable_suit_torso_black_layer", (0, -0.118, 1.00), (0.145, 0.010, 0.245), black),
            add_capsule_proxy("gwen_removable_suit_chest_white_panel_layer", (0, -0.126, 1.245), (0.125, 0.008, 0.052), white),
            add_capsule_proxy("gwen_removable_suit_left_forearm_pink_web_layer", (-0.185, -0.118, 1.040), (0.030, 0.008, 0.115), pink, (0, 0, math.radians(-15))),
            add_capsule_proxy("gwen_removable_suit_right_forearm_pink_web_layer", (0.185, -0.118, 1.040), (0.030, 0.008, 0.115), pink, (0, 0, math.radians(15))),
        ]
        for obj in parts:
            obj.hide_render = hidden
            obj.hide_viewport = hidden
            obj["wardrobe_layer_not_body"] = True
        return [obj.name for obj in parts]

    def add_lights_and_camera():
        bpy.ops.object.light_add(type="AREA", location=(0, -3.0, 3.0))
        key = bpy.context.object
        key.name = "real_model_proof_key_light"
        key.data.energy = 600
        key.data.size = 4
        bpy.ops.object.camera_add()
        bpy.context.scene.camera = bpy.context.object
        return bpy.context.object

    def look_at(obj, target):
        direction = mathutils.Vector(target) - obj.location
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    def set_camera(camera, location, target, ortho_scale):
        camera.location = location
        look_at(camera, target)
        camera.data.type = "ORTHO"
        camera.data.ortho_scale = ortho_scale

    def render_view(name: str, camera, location, target, ortho_scale, suit_visible: bool = False) -> str:
        for obj in bpy.context.scene.objects:
            if obj.name.startswith("gwen_removable_suit_"):
                obj.hide_render = not suit_visible
                obj.hide_viewport = not suit_visible
        set_camera(camera, location, target, ortho_scale)
        path = artifact_root / f"{name}.png"
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        return rel(path)

    # Re-check immediately before Blender imports any body geometry. The
    # selected base is explicitly adult-only; policy failure aborts the pass.
    body_policy_gate = validate_gwen_body_selection(candidate_id, BASE_FEMALE)
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(BASE_FEMALE))
    removed = remove_unmaterialized_helpers()
    renamed = rename_body()
    skin = make_material("gwen_real_pass_adult_warm_skin", (0.82, 0.60, 0.51, 1), 0.56)
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and "body" in obj.name.lower():
            obj.data.materials.clear()
            obj.data.materials.append(skin)
    normalize_scene(float(height_contract["height_m"]))
    body_obj = primary_body_object()
    initial_landmarks = measure_subject_landmarks(body_obj)
    body_shape_report = apply_gwen_body_shape_adjustments(body_obj, initial_landmarks)
    body_shape_report["target_height_contract"] = height_contract
    body_shape_report["body_fit_gate_status"] = "failed_requires_landmark_lattice_sculpt_fit"
    bpy.context.view_layer.update()
    landmarks = measure_subject_landmarks(body_obj)
    overlay_fit_report = build_overlay_fit_report(body_shape_report)
    landmark_report_path = artifact_root / "gwen_landmark_report.json"
    body_shape_report_path = artifact_root / "gwen_body_shape_delta.json"
    overlay_fit_report_path = artifact_root / "gwen_overlay_fit_report.json"
    adult_body_fit_diagnosis_path = artifact_root / "gwen_adult_body_fit_diagnosis.json"
    movement_training_plan_path = artifact_root / "gwen_movement_self_training_plan.json"
    adult_body_fit_diagnosis = {
        "schema_version": 1,
        "created_at": now_iso(),
        "candidate_id": candidate_id,
        "status": "failed_requires_landmark_lattice_sculpt_fit",
        "grade": "F",
        "target_height_contract": height_contract,
        "why_barbie_body_happened": [
            "The candidate is marked adult, but adult metadata only changes policy; it does not reshape the mesh.",
            "This script still starts from a smooth generic adult female base and applies conservative band deltas.",
            "That is useful as a proof that the GLB path works, but it is not enough for an approved adult likeness/body.",
        ],
        "current_method": body_shape_report.get("method", ""),
        "required_method_before_approval": [
            "front/side/back reference landmark extraction",
            "height-scaled adult base fitting",
            "lattice or sculpt deformation from measured shoulder, chest, waist, hip, limb, head, and jaw landmarks",
            "neutral adult anatomy/proportion preservation for adult candidates only",
            "adult anatomy masterclass proof that the mesh no longer reads as doll-safe, Barbie-smoothed, or generic",
            "movement self-test proof for walk arm swing, sit, lie, reach, and door threshold crossing",
            "before/after silhouette proof and rendered GLB, not JSON-only claims",
        ],
        "automatic_fail_until": [
            "body_shape_delta_report is produced by a true landmark/lattice/sculpt fitting stage",
            "visual proof no longer reads as the untouched smooth generic base",
            "movement_self_training_curriculum_v1 produces reviewed visual proof on this body",
            "Robert approves the adult body proportions from front, side, and back renders",
        ],
    }
    write_json(landmark_report_path, landmarks)
    write_json(body_shape_report_path, body_shape_report)
    write_json(overlay_fit_report_path, overlay_fit_report)
    write_json(adult_body_fit_diagnosis_path, adult_body_fit_diagnosis)
    movement_training_plan = {
        "schema_version": 1,
        "created_at": now_iso(),
        "candidate_id": candidate_id,
        "status": "required_before_live_ready",
        "movement_library_skill": "movement_self_training_curriculum_v1",
        "required_visual_assignments": [
            "idle_breathing_weight_shift",
            "walk_with_natural_arm_swing_front_side",
            "turn_in_place",
            "sit_down_and_stand_up",
            "lie_down_and_get_up",
            "reach_door_handle_and_cross_threshold",
            "pick_up_small_object",
            "hold_book_or_tablet",
            "drink_from_cup",
            "look_at_speaker_and_scan_room",
        ],
        "automatic_fail_until": [
            "each movement assignment has a short clip or contact sheet",
            "hand and foot contacts are recorded",
            "the body keeps believable deformation during movement",
            "mind/body truth report confirms spoken activity matches prop and posture evidence",
        ],
    }
    write_json(movement_training_plan_path, movement_training_plan)

    eye_parts = add_eye_system(landmarks)
    mouth_parts = add_mouth_system(body_obj, landmarks)
    face_parts = add_face_features(landmarks)
    # The previous procedural hair pass made review worse by creating blocky
    # pieces that looked copied or misplaced. Keep hair out of this repair proof
    # until the dedicated hair-card/sculpt lesson can produce a usable result.
    hair_parts: list[str] = []
    # Clothing is deliberately disabled in this proof pass. The previous oval
    # placeholders made the adult body review look like a doll/clothing mockup
    # and should not be treated as a real wardrobe result.
    suit_parts: list[str] = []
    quality_failures = [
        "Head and face still come from a generic base mesh; no true Gwen likeness sculpt has passed.",
        "Eyes use generated sclera/iris/pupil parts, but the base face still lacks fitted eyelid topology around the sockets.",
        "Hair is intentionally disabled in this repair proof because the prior procedural hair was making the model worse.",
        "Body/head shape is now a conservative stabilization pass, not a true reference-fitted lattice/sculpt result.",
        "Adult anatomy policy is allowed for Gwen, but the current base still needs a real approved adult anatomy fitting pass.",
        "Adult body-fit gate failed: this pass did not run the required landmark-driven lattice/sculpt fit.",
    ]
    if overlay_fit_report.get("source_quality") == "insufficient_local_images_for_gwen_use_chat_refs_or_save_new_images":
        quality_failures.append("Overlay source set is still marked insufficient for Gwen likeness fitting.")
    visual_quality_gate = {
        "schema_version": 1,
        "created_at": now_iso(),
        "candidate_id": candidate_id,
        "status": "failed" if quality_failures else "passed",
        "grade": "F" if quality_failures else "pending_robert_review",
        "failures": quality_failures,
        "automatic_fail_rules": [
            "visible second/debug mouth",
            "floating/protruding eyes",
            "eyes too small for the measured head/socket or not recessed behind the eyelid rim",
            "flat eye decals instead of round eyes seated in sockets",
            "non-adult doll-safe treatment on adult Gwen",
            "adult body reads as Barbie-smoothed or generic after the pass",
            "adult Gwen only has maturity metadata plus a smooth generic base instead of measured body fitting",
            "copied reference model used as candidate body",
            "missing Gwen hair on a likeness pass",
            "no movement proof for arm swing, sitting, lying, reaching, and threshold crossing",
        ],
        "fixes_applied_this_pass": [
            "Removed fake eyelid proxy strips that made the eyes read as flat bars.",
            "Smoothed generated eye spheres and moved eye fronts farther behind the sampled face surface.",
            "Replaced the stronger head/body z-band deltas with a conservative repair pass to avoid strange bumps.",
            "Disabled the rough generated hair pieces instead of shipping a misleading bad hair result.",
            "Kept mouth animation as shape keys on the one base-mouth mesh; no second visible mouth proxy was generated.",
            "Preserved adult policy and blocked non-adult doll-safe treatment for Gwen.",
        ],
        "required_next_work": [
            "Build a true head/face fitting pass from front/side/three-quarter reference landmarks.",
            "Create real eyelid/socket topology or deform the base face around the inserted eyes.",
            "Fit separate asymmetric Gwen hair from the saved unmasked reference measurements.",
            "Replace coarse z-band body deltas with a lattice/sculpt fit checked against front and side silhouettes.",
            "Run movement_self_training_curriculum_v1 on the generated body and save visual proof clips/contact sheets.",
            "Use the adult body-fit plan and target height contract as blocking requirements before the next approval attempt.",
        ],
    }
    visual_quality_gate_path = artifact_root / "gwen_visual_quality_gate.json"
    write_json(visual_quality_gate_path, visual_quality_gate)
    body_center = (
        (landmarks["body"]["bounds_low"][0] + landmarks["body"]["bounds_high"][0]) * 0.5,
        (landmarks["body"]["bounds_low"][1] + landmarks["body"]["bounds_high"][1]) * 0.5,
        (landmarks["body"]["bounds_low"][2] + landmarks["body"]["bounds_high"][2]) * 0.54,
    )
    head_center = tuple(landmarks["head"]["center"])
    eye_mid = (
        (landmarks["eyes"]["left"]["center"][0] + landmarks["eyes"]["right"]["center"][0]) * 0.5,
        (landmarks["eyes"]["left"]["center"][1] + landmarks["eyes"]["right"]["center"][1]) * 0.5,
        (landmarks["eyes"]["left"]["center"][2] + landmarks["eyes"]["right"]["center"][2]) * 0.5,
    )
    mouth_center = tuple(landmarks["mouth"]["center"])
    add_anchor("gwen_subject_school_body_control_root_real_pass", body_center, 0.04)
    add_anchor("gwen_subject_school_head_look_control_landmark_real_pass", (head_center[0], head_center[1] - 0.16, eye_mid[2]), 0.025)
    camera = add_lights_and_camera()

    try:
        bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        bpy.context.scene.render.engine = "BLENDER_EEVEE"
    bpy.context.scene.render.resolution_x = 1200
    bpy.context.scene.render.resolution_y = 1600
    if hasattr(bpy.context.scene, "eevee"):
        bpy.context.scene.eevee.taa_render_samples = 32
    bpy.context.scene.world.color = (0.02, 0.03, 0.04)

    views = {
        "front_body": render_view("front_body", camera, (body_center[0], -4.0, body_center[2]), body_center, 1.90),
        "side_body": render_view("side_body", camera, (4.0, body_center[1], body_center[2]), body_center, 1.90),
        "back_body": render_view("back_body", camera, (body_center[0], 4.0, body_center[2]), body_center, 1.90),
        "head_front": render_view("head_front", camera, (head_center[0], -2.0, eye_mid[2]), (head_center[0], head_center[1], eye_mid[2]), 0.48),
        "eye_front": render_view("eye_front", camera, (eye_mid[0], -1.3, eye_mid[2]), eye_mid, 0.21),
        "eye_side": render_view("eye_side", camera, (0.70, -1.0, eye_mid[2]), eye_mid, 0.23),
        "hair_front": render_view("hair_front", camera, (head_center[0], -2.0, eye_mid[2]), (head_center[0], head_center[1], eye_mid[2]), 0.58),
        "hair_side_left": render_view("hair_side_left", camera, (-2.0, head_center[1], eye_mid[2]), (head_center[0], head_center[1], eye_mid[2]), 0.58),
        "hair_side_right": render_view("hair_side_right", camera, (2.0, head_center[1], eye_mid[2]), (head_center[0], head_center[1], eye_mid[2]), 0.58),
        "mouth_close": render_view("mouth_close", camera, (mouth_center[0], -1.25, mouth_center[2]), mouth_center, 0.20),
        "suit_on": render_view("suit_on", camera, (body_center[0], -4.0, body_center[2]), body_center, 1.90, suit_visible=False),
    }

    model_output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(model_output),
        export_format="GLB",
        export_apply=True,
        export_yup=True,
        export_animations=False,
        export_morph=True,
    )
    run_model = artifact_root / "gwen_subject_school_real_model.glb"
    shutil.copy2(model_output, run_model)

    low, high = scene_bounds()
    manifest = {
        "schema_version": 1,
        "created_at": now_iso(),
        "run_id": run_id,
        "candidate_id": candidate_id,
        "status": "blender_real_model_and_renders_generated_pending_assignment_finalization",
        "model": rel(run_model),
        "model_library_copy": rel(model_output),
        "source_base": rel(BASE_FEMALE),
        "selected_base_asset_policy": body_policy_gate["selected_base"],
        "body_policy_validation": body_policy_gate["validation"],
        "target_height_contract": height_contract,
        "reference_model_copying": False,
        "runtime_body_replaced": False,
        "maturity_policy": "adult",
        "adult_anatomy_allowed": True,
        "non_adult_doll_safe_applied": False,
        "views": views,
        "landmark_report": rel(landmark_report_path),
        "body_shape_delta_report": rel(body_shape_report_path),
        "overlay_fit_report": rel(overlay_fit_report_path),
        "adult_body_fit_diagnosis": rel(adult_body_fit_diagnosis_path),
        "movement_training_plan": rel(movement_training_plan_path),
        "visual_quality_gate": rel(visual_quality_gate_path),
        "landmark_report_data": landmarks,
        "body_shape_delta_data": body_shape_report,
        "overlay_fit_report_data": overlay_fit_report,
        "adult_body_fit_diagnosis_data": adult_body_fit_diagnosis,
        "movement_training_plan_data": movement_training_plan,
        "visual_quality_gate_data": visual_quality_gate,
        "removed_unmaterialized_helpers": removed,
        "renamed_body_meshes": renamed,
        "generated_eye_parts": eye_parts,
        "generated_mouth_parts": mouth_parts,
        "generated_face_parts": face_parts,
        "generated_hair_parts": hair_parts,
        "hair_method": "Hair intentionally disabled in this repair proof because the previous procedural hair failed review; next pass must use a dedicated hair-card/sculpt lesson without copying reference meshes.",
        "generated_wardrobe_parts": suit_parts,
        "scene_bounds": {"low": list(low), "high": list(high)},
        "known_limits": [
            "This is a rough constructed proof model, not an approved Gwen likeness.",
            "Eyes are placed from measured head/eye-band landmarks and kept smaller/recessed; fake eyelid proxy strips were removed because they made the eyes look flat.",
            "Any visible second/debug mouth, detached lip seam, or eye protrusion is an automatic visual failure.",
            "Body proportions now receive only mild conservative z-band mesh deltas from the female base body to avoid new bumps; a true sculpt/lattice fit is still required.",
            "Hair is disabled in this proof because the rough procedural hair was worse than no hair; this remains a visual blocker until a real hair lesson can fit the style.",
            "Mouth animation is exported as shape keys on the existing face mesh; no visible mouth proxy/debug mesh is generated.",
            "Motion GIFs are proof placeholders until a real animation retarget pass is built.",
            "The Ghost-Spider suit placeholder is disabled in this proof because the old oval layer looked like a false clothing pass.",
        ],
    }
    write_json(artifact_manifest_path(run_id), manifest)
    print(json.dumps({"ok": True, "manifest": rel(artifact_manifest_path(run_id)), "model": rel(run_model)}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate real model artifacts for Avatar Builder subject school.")
    parser.add_argument("--candidate-id", default=GWEN_ID)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--blender-worker", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    try:
        if args.blender_worker:
            return run_blender_worker(args)
        return run_normal(args)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
