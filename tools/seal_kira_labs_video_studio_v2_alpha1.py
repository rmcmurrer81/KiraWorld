"""Create a read-only outer seal for the staged Video Studio alpha checkpoint.

This utility inventories the complete staging tree and the complete private
proof project without modifying either source.  It writes its manifests to a
separate evidence directory.  Python bytecode caches are excluded because they
are interpreter-generated and are not part of the authored checkpoint.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_STAGE = Path(
    r"C:\KiraVideos\KiraLabsVideoStudio_v2_staging\2.0.0-alpha.1"
)
DEFAULT_PROOF = Path(
    r"C:\Users\robmc\KiraVideos\StudioOutputs\V2_PrivateTests"
    r"\20260723_111612_kira_world_july_23_2026_engineering_checkpoint"
    r"_v2_kira_world_july_2"
)
DEFAULT_CONCEPT_PROOF = Path(
    r"C:\Users\robmc\KiraVideos\StudioOutputs\V2_PrivateTests"
    r"\20260725_193114_kira_labs_concept_motion_private_proof"
    r"_v2_concept_motion_pr"
)
DEFAULT_ACTIVE_V1 = Path(r"C:\KiraVideos\VideoStudio")
DEFAULT_R6 = Path(
    r"C:\Users\robmc\Kira\Avatar\avatar_builder\candidate_sources"
    r"\kira_provisional_body_r6\r6_20260718_163658"
    r"\kira_provisional_body_r6.glb"
)
DEFAULT_RUNTIME_STATE = Path(
    r"C:\Users\robmc\Kira\Data\runtime\kira_world_shell_state.json"
)
EXPECTED_ACTIVE_V1_TREE_SHA256 = (
    "7e36756a953a266d0adf52343b7271c0306bcdd3908508c1567615ffc58a5460"
)
EXPECTED_R6_SHA256 = (
    "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_authored_file(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    return "__pycache__" not in relative.parts and path.suffix.casefold() != ".pyc"


def inventory(root: Path, *, authored_only: bool) -> dict[str, Any]:
    if not root.is_dir():
        raise FileNotFoundError(root)
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (candidate for candidate in root.rglob("*") if candidate.is_file()),
        key=lambda item: item.relative_to(root).as_posix().casefold(),
    ):
        if authored_only and not is_authored_file(path, root):
            continue
        stat = path.stat()
        rows.append(
            {
                "relative_path": path.relative_to(root).as_posix(),
                "bytes": stat.st_size,
                "sha256": sha256_file(path),
                "modified_utc": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
            }
        )
    digest_input = "\n".join(
        f"{row['relative_path']}|{row['bytes']}|{row['sha256']}" for row in rows
    ).encode("utf-8")
    windows_digest_input = "\n".join(
        f"{str(row['relative_path']).replace('/', chr(92))}|{row['bytes']}|{row['sha256']}"
        for row in rows
    ).encode("utf-8")
    return {
        "root": str(root.resolve()),
        "authored_only": authored_only,
        "excluded": ["**/__pycache__/**", "*.pyc"] if authored_only else [],
        "file_count": len(rows),
        "byte_count": sum(int(row["bytes"]) for row in rows),
        "tree_sha256": hashlib.sha256(digest_input).hexdigest(),
        "windows_tree_sha256": hashlib.sha256(windows_digest_input).hexdigest(),
        "files": rows,
    }


def find_row(manifest: dict[str, Any], suffix: str) -> dict[str, Any]:
    normalized = suffix.replace("\\", "/").casefold()
    matches = [
        row
        for row in manifest["files"]
        if str(row["relative_path"]).casefold().endswith(normalized)
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one manifest row ending with {suffix!r}, got {len(matches)}")
    return matches[0]


def verify_private_only(proof_root: Path, proof_manifest: dict[str, Any]) -> dict[str, Any]:
    project_path = proof_root / "project.v2.json"
    project = json.loads(project_path.read_text(encoding="utf-8"))
    publication = project.get("publication", {})
    if publication.get("automatic_upload_enabled") is not False:
        raise RuntimeError("Proof project does not fail closed on automatic upload.")
    if publication.get("posting_performed") is not False:
        raise RuntimeError("Proof project claims publication occurred.")
    if publication.get("public_release_approved") is not False:
        raise RuntimeError("Proof project is unexpectedly approved for public release.")

    clean_files = [
        row["relative_path"]
        for row in proof_manifest["files"]
        if "/clean/" in f"/{str(row['relative_path']).casefold()}/"
        and not str(row["relative_path"]).casefold().endswith("clean_final_blocked.json")
    ]
    public_mp4s = [
        row["relative_path"]
        for row in proof_manifest["files"]
        if str(row["relative_path"]).casefold().endswith(".mp4")
        and "private_review" not in str(row["relative_path"]).casefold()
    ]
    if clean_files:
        raise RuntimeError(f"Unexpected clean artifacts: {clean_files}")
    if public_mp4s:
        raise RuntimeError(f"Unexpected non-private MP4 artifacts: {public_mp4s}")
    return {
        "automatic_upload_enabled": False,
        "posting_performed": False,
        "public_release_approved": False,
        "unexpected_clean_artifacts": [],
        "unexpected_non_private_mp4s": [],
        "robert_review_state": project.get("review", {}).get(
            "robert_review_state", "unknown"
        ),
    }


def verify_concept_proof(
    proof_root: Path, proof_manifest: dict[str, Any]
) -> dict[str, Any]:
    proof_path = proof_root / "manifests" / "concept_motion_private_proof.json"
    project_path = proof_root / "project.v2.json"
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    project = json.loads(project_path.read_text(encoding="utf-8"))
    expected_values = {
        "status": "PASSED_PRIVATE_REVIEW_PROOF",
        "truth_label": "CONCEPT VISUALIZATION",
        "persistent_on_screen_disclosure": True,
        "documentary_evidence": False,
        "external_or_ai_generation_used": False,
        "narration_regenerated": False,
        "narration_unchanged": True,
        "permission_status": "private_review_only",
        "rights_review_status": "unknown",
        "robert_visual_review_approved": False,
        "clean_final_allowed": False,
        "publication_performed": False,
        "runtime_capture_used": False,
        "resident_activation_performed": False,
    }
    for key, expected in expected_values.items():
        if proof.get(key) != expected:
            raise RuntimeError(
                f"Concept proof field {key!r} was {proof.get(key)!r}, "
                f"expected {expected!r}."
            )

    publication = project.get("publication", {})
    if publication.get("automatic_upload_enabled") is not False:
        raise RuntimeError("Concept proof does not fail closed on automatic upload.")
    if publication.get("posting_performed") is not False:
        raise RuntimeError("Concept proof claims publication occurred.")
    if publication.get("public_release_approved") is not False:
        raise RuntimeError("Concept proof is unexpectedly approved for public release.")

    expected_png_sizes = {
        "landscape_16_9": [1920, 1080],
        "vertical_9_16": [1080, 1920],
        "square_1_1": [1080, 1080],
    }
    png_rows: dict[str, dict[str, Any]] = {}
    for profile, expected_size in expected_png_sizes.items():
        check = proof.get("png_checks", {}).get(profile, {})
        if check.get("decoded") is not True or check.get("size") != expected_size:
            raise RuntimeError(
                f"Concept PNG check for {profile} is not a decoded native render."
            )
        relative_path = str(check.get("path") or "")
        if not relative_path.casefold().endswith(".png"):
            raise RuntimeError(f"Concept PNG path is invalid for {profile}.")
        png_rows[profile] = find_row(proof_manifest, relative_path)

    motion = proof.get("motion_check", {})
    if motion.get("decoded") is not True:
        raise RuntimeError("Concept motion preview was not decoded.")
    if motion.get("silent_no_audio_stream") is not True:
        raise RuntimeError("Concept motion preview is not proven silent.")
    if motion.get("size") != [1920, 1080]:
        raise RuntimeError("Concept motion preview is not native 1920x1080.")
    motion_path = str(motion.get("path") or "")
    if "build/private_review/" not in motion_path.replace("\\", "/").casefold():
        raise RuntimeError("Concept motion preview is not in a private-review path.")
    motion_row = find_row(proof_manifest, motion_path)

    unexpected_mp4s = [
        row["relative_path"]
        for row in proof_manifest["files"]
        if str(row["relative_path"]).casefold().endswith(".mp4")
        and "private_review" not in str(row["relative_path"]).casefold()
    ]
    unexpected_clean = [
        row["relative_path"]
        for row in proof_manifest["files"]
        if "/clean/" in f"/{str(row['relative_path']).casefold()}/"
    ]
    if unexpected_mp4s:
        raise RuntimeError(
            f"Concept proof contains non-private MP4s: {unexpected_mp4s}"
        )
    if unexpected_clean:
        raise RuntimeError(
            f"Concept proof contains clean artifacts: {unexpected_clean}"
        )

    return {
        "status": proof["status"],
        "truth_label": proof["truth_label"],
        "persistent_on_screen_disclosure": True,
        "documentary_evidence": False,
        "external_or_ai_generation_used": False,
        "permission_status": "private_review_only",
        "rights_review_status": "unknown",
        "robert_visual_review_approved": False,
        "clean_final_allowed": False,
        "publication_performed": False,
        "runtime_capture_used": False,
        "resident_activation_performed": False,
        "narration_regenerated": False,
        "narration_unchanged": True,
        "pngs": png_rows,
        "motion_preview": motion_row,
        "motion_preview_decoded": True,
        "motion_preview_silent": True,
        "unexpected_non_private_mp4s": [],
        "unexpected_clean_artifacts": [],
    }


def verify_backup_proof(
    path: Path, stage: Path, backup: Path
) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("passed") is not True:
        raise RuntimeError("Staging backup verification did not pass.")
    if Path(payload.get("source", {}).get("root", "")).resolve() != stage:
        raise RuntimeError("Backup verification source does not match staging.")
    if Path(payload.get("backup", {}).get("root", "")).resolve() != backup:
        raise RuntimeError("Backup verification destination does not match backup.")
    source = payload.get("source", {})
    destination = payload.get("backup", {})
    if (
        source.get("tree_sha256") != destination.get("tree_sha256")
        or source.get("file_count") != destination.get("file_count")
        or source.get("total_bytes") != destination.get("total_bytes")
    ):
        raise RuntimeError("Backup verification summaries are not identical.")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "passed": True,
        "source_tree_sha256": source.get("tree_sha256"),
        "backup_tree_sha256": destination.get("tree_sha256"),
        "file_count": source.get("file_count"),
        "byte_count": source.get("total_bytes"),
        "alternate_data_streams_passed": payload.get(
            "alternate_data_stream_audit", {}
        )
        .get("comparison", {})
        .get("passed"),
    }


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    parser.add_argument("--proof", type=Path, default=DEFAULT_PROOF)
    parser.add_argument(
        "--concept-proof", type=Path, default=DEFAULT_CONCEPT_PROOF
    )
    parser.add_argument("--staging-backup", type=Path, required=True)
    parser.add_argument("--backup-verification", type=Path, required=True)
    parser.add_argument("--active-v1", type=Path, default=DEFAULT_ACTIVE_V1)
    parser.add_argument("--r6", type=Path, default=DEFAULT_R6)
    parser.add_argument("--runtime-state", type=Path, default=DEFAULT_RUNTIME_STATE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    stage = args.stage.resolve()
    proof = args.proof.resolve()
    concept_proof = args.concept_proof.resolve()
    staging_backup = args.staging_backup.resolve()
    backup_verification = args.backup_verification.resolve()
    active_v1 = args.active_v1.resolve()
    r6 = args.r6.resolve()
    runtime_state_path = args.runtime_state.resolve()
    output = args.output.resolve()
    if output == stage or output in stage.parents or stage in output.parents:
        raise ValueError("Evidence output must remain outside the staging tree.")
    if output == proof or output in proof.parents or proof in output.parents:
        raise ValueError("Evidence output must remain outside the proof tree.")
    if (
        output == concept_proof
        or output in concept_proof.parents
        or concept_proof in output.parents
    ):
        raise ValueError("Evidence output must remain outside the concept proof tree.")
    if (
        output == staging_backup
        or output in staging_backup.parents
        or staging_backup in output.parents
    ):
        raise ValueError("Evidence output must remain outside the staging backup tree.")
    output.mkdir(parents=True, exist_ok=False)

    stage_manifest = inventory(stage, authored_only=True)
    proof_manifest = inventory(proof, authored_only=False)
    concept_proof_manifest = inventory(concept_proof, authored_only=False)
    staging_backup_manifest = inventory(staging_backup, authored_only=True)
    active_manifest = inventory(active_v1, authored_only=False)
    private_state = verify_private_only(proof, proof_manifest)
    concept_state = verify_concept_proof(concept_proof, concept_proof_manifest)
    backup_state = verify_backup_proof(
        backup_verification, stage, staging_backup
    )
    if (
        stage_manifest["tree_sha256"] != staging_backup_manifest["tree_sha256"]
        or stage_manifest["file_count"] != staging_backup_manifest["file_count"]
        or stage_manifest["byte_count"] != staging_backup_manifest["byte_count"]
    ):
        raise RuntimeError("Independent seal inventory found a staging backup mismatch.")
    r6_sha256 = sha256_file(r6)
    runtime_state_sha256 = sha256_file(runtime_state_path)
    runtime_state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
    active_candidate = str(runtime_state.get("active_candidate") or "")
    active_conversation_mode = str(
        runtime_state.get("active_conversation_mode") or ""
    )
    if active_candidate or active_conversation_mode:
        raise RuntimeError(
            "Runtime is active; checkpoint sealing must remain read-only and inactive."
        )
    if active_manifest["windows_tree_sha256"] != EXPECTED_ACTIVE_V1_TREE_SHA256:
        raise RuntimeError("Active v1.9 tree no longer matches its preserved seal.")
    if r6_sha256 != EXPECTED_R6_SHA256:
        raise RuntimeError("Current R6 body no longer matches its recovery hash.")

    narration_row = find_row(proof_manifest, "review/narration_reuse_proof.json")
    rebuild_row = find_row(proof_manifest, "review/project_service_rebuild_proof.json")
    approved_voice_row = find_row(stage_manifest, "voice/approved_reference.wav")
    summary = {
        "created_utc": datetime.now(tz=timezone.utc).isoformat(),
        "version": "2.0.0-alpha.1",
        "status": "private_staging_checkpoint_awaiting_robert_review",
        "stage": {
            key: stage_manifest[key]
            for key in ("root", "authored_only", "excluded", "file_count", "byte_count", "tree_sha256")
        },
        "private_proof": {
            key: proof_manifest[key]
            for key in ("root", "file_count", "byte_count", "tree_sha256")
        },
        "concept_motion_private_proof": {
            **{
                key: concept_proof_manifest[key]
                for key in ("root", "file_count", "byte_count", "tree_sha256")
            },
            "verified_state": concept_state,
        },
        "staging_backup": {
            **{
                key: staging_backup_manifest[key]
                for key in ("root", "authored_only", "excluded", "file_count", "byte_count", "tree_sha256")
            },
            "matches_staging": True,
            "verification": backup_state,
        },
        "active_v1": {
            "root": str(active_v1),
            "file_count": active_manifest["file_count"],
            "byte_count": active_manifest["byte_count"],
            "tree_sha256": active_manifest["windows_tree_sha256"],
            "canonical_posix_tree_sha256": active_manifest["tree_sha256"],
            "matches_preserved_seal": True,
        },
        "r6": {
            "path": str(r6),
            "sha256": r6_sha256,
            "matches_recovery_hash": True,
        },
        "runtime_state": {
            "path": str(runtime_state_path),
            "sha256": runtime_state_sha256,
            "active_candidate": "",
            "active_conversation_mode": "",
            "last_activation_at": runtime_state.get("last_activation_at"),
            "last_deactivation_at": runtime_state.get("last_deactivation_at"),
            "updated_at": runtime_state.get("updated_at"),
            "note": (
                "This proves only that the runtime was inactive when sealed. "
                "It does not claim that Robert or the runtime activated nobody "
                "earlier in the day."
            ),
        },
        "approved_voice": {
            "path": str(stage / approved_voice_row["relative_path"]),
            "sha256": approved_voice_row["sha256"],
        },
        "narration_reuse_proof": narration_row,
        "project_service_rebuild_proof": rebuild_row,
        "private_only_state": private_state,
        "safety": {
            "kira_activated_by_seal": False,
            "active_v1_modified_by_seal": False,
            "automatic_publication_available": False,
            "clean_final_built": False,
            "concept_visuals_labeled": True,
            "concept_motion_is_silent_still_motion_only": True,
            "external_or_ai_image_generator_connected": False,
        },
    }

    write_json(output / "staging_authored_file_manifest.json", stage_manifest)
    write_json(output / "private_proof_complete_file_manifest.json", proof_manifest)
    write_json(
        output / "concept_motion_private_proof_complete_file_manifest.json",
        concept_proof_manifest,
    )
    write_json(
        output / "staging_backup_authored_file_manifest.json",
        staging_backup_manifest,
    )
    write_json(output / "active_v1_file_manifest.json", active_manifest)
    write_json(output / "checkpoint_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
