"""Regrade Avatar Builder School assignments after Robert review.

This script is intentionally stricter than the first school loop grader:
reference coverage is not a passing assignment. A lesson needs a constructed,
inspectable artifact such as rendered images or a GLB proof.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENT_RUNS = PROJECT_ROOT / "Avatar" / "avatar_builder" / "school" / "assignments" / "lesson_runs"
SESSION_RUNS = PROJECT_ROOT / "Avatar" / "avatar_builder" / "school" / "session_runs"
PROGRESS_PATH = PROJECT_ROOT / "Avatar" / "avatar_builder" / "school" / "progress" / "avatar_builder_school_progress_20260712.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return fallback


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_assignment(run_root: Path, cycle: int, lesson_id: str, status: str, review: str) -> None:
    path = run_root / f"{cycle:03d}_{lesson_id}_assignment.json"
    data = read_json(path, {})
    if not data:
        return
    data["assignment_status"] = status
    data["robert_review"] = review
    data["updated_by_regrade_at"] = now_iso()
    write_json(path, data)


def update_grade_card(run_root: Path, cycle: int, lesson_id: str, grade: str, review: str, extra: dict[str, Any] | None = None) -> None:
    path = run_root / f"{cycle:03d}_{lesson_id}_grade_card.json"
    data = read_json(path, {})
    if not data:
        return
    data["grade"] = grade
    data["robert_review"] = review
    data["updated_by_regrade_at"] = now_iso()
    data["reference_coverage_is_not_a_pass"] = True
    data["learning_proof"] = (
        "Regraded after Robert review: a reference list or copied/reference render is not proof of learning. "
        "A passing assignment needs constructed, inspectable evidence that matches the pass gate."
    )
    if extra:
        data.update(extra)
    write_json(path, data)


def update_session_artifact(run_id: str, cycle: int, lesson_id: str, grade: str, status: str, review: str, extra: dict[str, Any] | None = None) -> None:
    path = SESSION_RUNS / run_id / f"{cycle:03d}_{lesson_id}.json"
    data = read_json(path, {})
    if not data:
        return
    data["assignment_grade"] = grade
    data["status"] = status
    data["robert_review"] = review
    data["updated_by_regrade_at"] = now_iso()
    if extra:
        data.update(extra)
    write_json(path, data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    args = parser.parse_args()

    run_root = ASSIGNMENT_RUNS / args.run_id
    proof_root = run_root / "001_eye_socket_placement_constructed_proof"
    proof_manifest_path = proof_root / "constructed_eye_socket_training_head_manifest.json"
    proof_manifest = read_json(proof_manifest_path, {})
    proof_renders = proof_manifest.get("renders", {}) if isinstance(proof_manifest, dict) else {}

    eye_asset_review = (
        "Robert rejected this as reference-only: it rendered/listed eye models and reference patches, "
        "but did not construct a head with two eyes seated in sockets."
    )
    update_assignment(run_root, 0, "eye_asset_lab", "failed_robert_review_reference_only", eye_asset_review)
    update_grade_card(
        run_root,
        0,
        "eye_asset_lab",
        "F_reference_patch_only_not_constructed",
        eye_asset_review,
        {
            "failed_reason": "Reference eye assets were useful sources, but the assignment did not build two eyes in one head.",
            "next_required_pass": "Construct a head with two round left/right eyes inside sockets and render front plus side views.",
            "angle_review_folder": rel(run_root / "000_eye_asset_lab_angle_review"),
        },
    )
    update_session_artifact(
        args.run_id,
        0,
        "eye_asset_lab",
        "F_reference_patch_only_not_constructed",
        "failed_robert_review_reference_only",
        eye_asset_review,
    )

    if proof_manifest:
        eye_socket_review = (
            "Regraded as a constructed training proof only: there is now a simple head with two separate round eyes "
            "seated behind the face plane. This does not approve Marinette, Gwen, or any runtime avatar."
        )
        eye_socket_grade = "B_constructed_training_head_ready_not_character_likeness"
        eye_socket_status = "completed_training_proof_ready_for_robert_review"
        eye_socket_extra = {
            "constructed_proof_folder": rel(proof_root),
            "constructed_proof_manifest": rel(proof_manifest_path),
            "proof_renders": proof_renders,
            "proof_limits": proof_manifest.get("limits", []),
            "proof_measurements": proof_manifest.get("measurements", {}),
        }
    else:
        eye_socket_review = "No constructed eye-socket proof images were found, so this remains reference-only."
        eye_socket_grade = "F_no_constructed_visual_proof"
        eye_socket_status = "failed_no_constructed_visual_proof"
        eye_socket_extra = {}
    update_assignment(run_root, 1, "eye_socket_placement", eye_socket_status, eye_socket_review)
    update_grade_card(run_root, 1, "eye_socket_placement", eye_socket_grade, eye_socket_review, eye_socket_extra)
    update_session_artifact(args.run_id, 1, "eye_socket_placement", eye_socket_grade, eye_socket_status, eye_socket_review, eye_socket_extra)

    body_review = (
        "Robert could not review this lesson because it produced no overlay images, no constructed body, "
        "and no front/side/back visual proof. Listing body references is not a passing assignment."
    )
    update_assignment(run_root, 2, "body_shape_overlay", "failed_no_inspectable_visual_assignment", body_review)
    update_grade_card(
        run_root,
        2,
        "body_shape_overlay",
        "F_no_overlay_images_or_constructed_body",
        body_review,
        {
            "failed_reason": "No visual overlay assignment exists for review.",
            "next_required_pass": "Generate front and side overlay images against a base body, then save measurements and a non-copied constructed candidate.",
        },
    )
    update_session_artifact(
        args.run_id,
        2,
        "body_shape_overlay",
        "F_no_overlay_images_or_constructed_body",
        "failed_no_inspectable_visual_assignment",
        body_review,
    )

    index_path = run_root / "assignment_index.json"
    index = read_json(index_path, {"schema_version": 1, "run_id": args.run_id, "assignments": []})
    grade_by_cycle = {
        0: "F_reference_patch_only_not_constructed",
        1: eye_socket_grade,
        2: "F_no_overlay_images_or_constructed_body",
    }
    review_by_cycle = {
        0: eye_asset_review,
        1: eye_socket_review,
        2: body_review,
    }
    for item in index.get("assignments", []) or []:
        cycle = item.get("cycle_index")
        if cycle in grade_by_cycle:
            item["assignment_grade"] = grade_by_cycle[cycle]
            item["robert_review"] = review_by_cycle[cycle]
            if cycle == 1 and proof_manifest:
                item["constructed_proof_folder"] = rel(proof_root)
                item["constructed_proof_manifest"] = rel(proof_manifest_path)
    index["updated_at"] = now_iso()
    index["regraded_after_robert_review"] = True
    index["regrade_rule"] = "Reference coverage alone is not a pass; constructed visual proof is required."
    write_json(index_path, index)

    progress = read_json(PROGRESS_PATH, {})
    progress["updated_at"] = now_iso()
    progress["latest_avatar_builder_regrade"] = {
        "run_id": args.run_id,
        "assignment_index": rel(index_path),
        "rule": "Reference-only assignments now fail unless paired with constructed inspectable evidence.",
        "eye_socket_proof": rel(proof_manifest_path) if proof_manifest else None,
    }
    write_json(PROGRESS_PATH, progress)

    print(json.dumps(progress["latest_avatar_builder_regrade"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
