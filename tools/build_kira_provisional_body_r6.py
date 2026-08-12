#!/usr/bin/env python3
"""Run one hash-guarded, private, inactive Kira provisional body R6 pass."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
WORKER = ROOT / "tools" / "blender_build_kira_provisional_body_r6.py"
STRUCTURAL_AUDIT = ROOT / "tools" / "audit_avatar_body_topology.py"
GEOMETRY_AUDIT = ROOT / "tools" / "blender_audit_avatar_candidate_quality.py"
COMPATIBILITY_AUDIT = ROOT / "tools" / "blender_audit_kira_r6_compatibility.py"
SOURCE = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "asset_library"
    / "base_body_reference"
    / "womenfemale_body_base_rigged_3ec62ba8d7.glb"
)
SOURCE_SHA256 = "3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e"
LIVE_MODEL = ROOT / "Avatar" / "models" / "temp_ai" / "kira" / "avatar.glb"
EYE_MANIFEST = (
    ROOT
    / "Avatar"
    / "models"
    / "staged"
    / "kira"
    / "eyes"
    / "kira_brown_eye_rig_v3_2"
    / "manifest.json"
)
ASSET_MANIFEST = ROOT / "Avatar" / "avatar_builder" / "asset_library" / "manifest.json"
REFERENCE_POLICY_MANIFEST = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "reference_models"
    / "adult_anatomy_reference"
    / "reference_model_manifest.json"
)
ARTIFACT_ROOT = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "candidate_sources"
    / "kira_provisional_body_r6"
)
STUDY_REFERENCE_NAMES = (
    "female_body_skeleton_muscles_base_mesh_9929c94607.glb",
    "female_anatomy_study_progress_2_b0577836d8.glb",
    "female_reproductive_and_urinary_systems_7016cf9b6f.glb",
    "ligaments_of_the_female_pelvis_e90ef9781e.glb",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(ROOT),
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def selected_reference_evidence() -> list[dict[str, object]]:
    asset_manifest = json.loads(ASSET_MANIFEST.read_text(encoding="utf-8"))
    records = {
        Path(record["local_file"]).name: record
        for record in asset_manifest.get("records", [])
        if record.get("category") == "adult_anatomy_reference"
    }
    evidence: list[dict[str, object]] = []
    for name in STUDY_REFERENCE_NAMES:
        if name not in records:
            raise RuntimeError(f"selected study reference missing from enrolled manifest: {name}")
        record = records[name]
        path = ROOT / str(record["local_file"])
        if not path.is_file():
            raise RuntimeError(f"selected study reference file is missing: {path}")
        exact_hash = sha256_file(path)
        if exact_hash != record.get("sha256"):
            raise RuntimeError(f"selected study reference hash changed: {path}")
        evidence.append(
            {
                "project_path": relative(path),
                "sha256": exact_hash,
                "adult_only": bool(record.get("adult_only", True)),
                "usage_policy": record.get("usage_policy"),
                "use_in_r6": "nonvisual adult proportion/topology study only",
                "geometry_imported_or_copied": False,
            }
        )
    return evidence


def create_contact_sheet(run_dir: Path, manifest: dict[str, object]) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    renders = manifest["privacy_safe_renders"]
    assert isinstance(renders, dict)
    keys = list(renders)
    tile_width, tile_height = 320, 430
    header_height = 88
    columns = 3
    rows = 2
    sheet = Image.new("RGB", (columns * tile_width, header_height + rows * tile_height), (7, 12, 19))
    draw = ImageDraw.Draw(sheet)
    try:
        title_font = ImageFont.truetype("arial.ttf", 20)
        label_font = ImageFont.truetype("arial.ttf", 14)
        note_font = ImageFont.truetype("arial.ttf", 12)
    except OSError:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        note_font = ImageFont.load_default()
    draw.text(
        (16, 12),
        "Kira provisional body R6 - PRIVATE / COVERED / INACTIVE",
        fill=(232, 240, 246),
        font=title_font,
    )
    draw.text(
        (16, 46),
        "Opaque review coverage hides private adult details; coverage is not exported clothing.",
        fill=(234, 182, 103),
        font=note_font,
    )
    draw.text(
        (16, 64),
        "No activation, anatomy-completeness, eye-fit, lip-sync playback, or owner-approval claim.",
        fill=(234, 182, 103),
        font=note_font,
    )
    for index, key in enumerate(keys):
        record = renders[key]
        assert isinstance(record, dict)
        source = Path(str(record["path"]))
        column, row = index % columns, index // columns
        x_value = column * tile_width
        y_value = header_height + row * tile_height
        draw.rectangle(
            (x_value + 7, y_value + 7, x_value + tile_width - 7, y_value + tile_height - 7),
            outline=(39, 105, 130),
            width=2,
        )
        with Image.open(source) as image:
            image = image.convert("RGB")
            image.thumbnail((tile_width - 28, tile_height - 58))
            sheet.paste(image, (x_value + (tile_width - image.width) // 2, y_value + 12))
        draw.text(
            (x_value + 14, y_value + tile_height - 34),
            key,
            fill=(204, 222, 232),
            font=label_font,
        )
    output = run_dir / "kira_provisional_body_r6_covered_contact_sheet.png"
    sheet.save(output)
    return output


def main() -> int:
    for required in (
        BLENDER,
        WORKER,
        STRUCTURAL_AUDIT,
        GEOMETRY_AUDIT,
        COMPATIBILITY_AUDIT,
        SOURCE,
        LIVE_MODEL,
        EYE_MANIFEST,
        ASSET_MANIFEST,
        REFERENCE_POLICY_MANIFEST,
    ):
        if not required.is_file():
            raise SystemExit(f"Missing required R6 input/tool: {required}")
    if sha256_file(SOURCE) != SOURCE_SHA256:
        raise SystemExit("The exact enrolled adult base is missing or changed.")
    if sha256_file(LIVE_MODEL) != SOURCE_SHA256:
        raise SystemExit("Live Kira body no longer matches the guarded enrolled source; stop.")

    references = selected_reference_evidence()
    reference_policy = json.loads(REFERENCE_POLICY_MANIFEST.read_text(encoding="utf-8"))
    source_before = sha256_file(SOURCE)
    live_before = sha256_file(LIVE_MODEL)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = ARTIFACT_ROOT / f"r6_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    config_path = run_dir / "build_config.json"
    config = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(ROOT),
        "source_model": str(SOURCE),
        "source_project_path": relative(SOURCE),
        "source_sha256": SOURCE_SHA256,
        "output_dir": str(run_dir),
        "live_model_project_path_for_hash_guard_only": relative(LIVE_MODEL),
        "live_model_sha256_before": live_before,
        "runtime_activation_requested": False,
        "owner_approval_requested": False,
        "autobuild_requested": False,
        "adult_reference_geometry_import_or_copy_requested": False,
    }
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    run(
        [
            str(BLENDER),
            "--background",
            "--python",
            str(WORKER),
            "--",
            "--config",
            str(config_path),
        ]
    )
    source_after = sha256_file(SOURCE)
    live_after = sha256_file(LIVE_MODEL)
    if source_after != source_before:
        raise RuntimeError("Source adult base changed during R6 build; stop and investigate.")
    if live_after != live_before:
        raise RuntimeError("Live Kira body changed during private R6 build; stop and investigate.")

    manifest_path = run_dir / "kira_provisional_body_r6_manifest.json"
    candidate_path = run_dir / "kira_provisional_body_r6.glb"
    if not manifest_path.is_file() or not candidate_path.is_file():
        raise RuntimeError("R6 worker did not create its candidate and manifest.")
    candidate_sha = sha256_file(candidate_path)
    if candidate_sha == source_before:
        raise RuntimeError("R6 candidate is a byte copy rather than a transformed derivative.")

    structural_output = run_dir / "structural_rig_topology_audit.json"
    run(
        [
            "python",
            str(STRUCTURAL_AUDIT),
            str(candidate_path),
            "--artifact-id",
            f"kira_provisional_body_r6_{candidate_sha[:12]}",
            "--require-structural-rig",
            "--output",
            str(structural_output),
        ]
    )
    geometry_output = run_dir / "blender_geometry_deformation_audit.json"
    run(
        [
            str(BLENDER),
            "--background",
            "--python",
            str(GEOMETRY_AUDIT),
            "--",
            "--input",
            str(candidate_path),
            "--output",
            str(geometry_output),
        ]
    )
    compatibility_output = run_dir / "exact_candidate_compatibility_audit.json"
    run(
        [
            str(BLENDER),
            "--background",
            "--python",
            str(COMPATIBILITY_AUDIT),
            "--",
            "--source",
            str(SOURCE),
            "--candidate",
            str(candidate_path),
            "--eye-manifest",
            str(EYE_MANIFEST),
            "--output",
            str(compatibility_output),
        ]
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    structural = json.loads(structural_output.read_text(encoding="utf-8"))
    geometry = json.loads(geometry_output.read_text(encoding="utf-8"))
    compatibility = json.loads(compatibility_output.read_text(encoding="utf-8"))
    contact_sheet = create_contact_sheet(run_dir, manifest)
    body_geometry = geometry.get("primary_body", {})
    manifest["exact_hash_guards"] = {
        "source_project_path": relative(SOURCE),
        "source_sha256_before": source_before,
        "source_sha256_after": source_after,
        "source_unchanged": source_before == source_after,
        "live_model_project_path": relative(LIVE_MODEL),
        "live_model_sha256_before": live_before,
        "live_model_sha256_after": live_after,
        "live_model_unchanged": live_before == live_after,
        "candidate_sha256": candidate_sha,
        "candidate_differs_from_source": candidate_sha != source_before,
    }
    manifest["adult_anatomy_study_evidence"] = {
        "policy_manifest": relative(REFERENCE_POLICY_MANIFEST),
        "policy_manifest_sha256": sha256_file(REFERENCE_POLICY_MANIFEST),
        "reference_only_rule": reference_policy.get("reference_only_rule"),
        "selected_references": references,
        "reference_geometry_imported_or_copied": False,
    }
    manifest["independent_audits"] = {
        "structural": {
            "path": str(structural_output),
            "sha256": sha256_file(structural_output),
            "valid_glb": structural.get("valid_glb"),
            "humanoid_rig_structurally_ready": structural.get("humanoid_rig_structurally_ready"),
            "stable_working_rig_proven": structural.get("stable_working_rig_proven"),
        },
        "geometry": {
            "path": str(geometry_output),
            "sha256": sha256_file(geometry_output),
            "body_topology": body_geometry.get("topology", {}),
            "body_weights": body_geometry.get("weights", {}),
            "overall_stable_working_rig_proven": geometry.get("stable_working_rig_proven"),
        },
        "exact_candidate_compatibility": {
            "path": str(compatibility_output),
            "sha256": sha256_file(compatibility_output),
            "structural_preservation": compatibility.get("structural_preservation"),
            "deformation_regions": compatibility.get("deformation_regions"),
            "staged_eye_rig_compatibility": compatibility.get("staged_eye_rig_compatibility"),
            "existing_mouth_lip_sync_compatibility": compatibility.get("existing_mouth_lip_sync_compatibility"),
            "gates": compatibility.get("gates"),
        },
    }
    manifest["covered_contact_sheet"] = {
        "path": str(contact_sheet),
        "sha256": sha256_file(contact_sheet),
        "size_bytes": contact_sheet.stat().st_size,
        "contains_uncovered_or_intimate_view": False,
        "visual_qa_status": "pending_independent_review",
    }
    manifest["autobuild_gate"] = {
        "passed_subjects": 0,
        "required_subjects": 2,
        "passed": False,
        "reason": "R6 is one private, unapproved Kira candidate and cannot self-pass or start autobuild.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    summary = {
        "ok": True,
        "run_dir": relative(run_dir),
        "candidate": relative(candidate_path),
        "candidate_sha256": candidate_sha,
        "manifest": relative(manifest_path),
        "covered_contact_sheet": relative(contact_sheet),
        "source_unchanged": source_before == source_after,
        "live_model_unchanged": live_before == live_after,
        "adult_external_form_materially_advanced": compatibility["gates"]["adult_external_form_materially_advanced"],
        "head_and_existing_mouth_preserved": (
            compatibility["deformation_regions"]["protected_head"]["exact_within_tolerance"]
            and compatibility["deformation_regions"]["protected_existing_mouth_surface"]["exact_within_tolerance"]
        ),
        "eye_structural_reuse_supported": compatibility["staged_eye_rig_compatibility"]["structural_reuse_supported"],
        "mouth_lip_sync_structural_compatibility_supported": compatibility["existing_mouth_lip_sync_compatibility"]["structural_compatibility_supported"],
        "anatomical_completeness_proven": False,
        "stable_working_rig_proven": False,
        "runtime_activation_allowed": False,
        "owner_approved": False,
        "autobuild_gate": "0/2",
    }
    summary_path = run_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
