#!/usr/bin/env python3
"""Run one hash-guarded private Kira provisional body R5 build and audit."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
WORKER = ROOT / "tools" / "blender_build_kira_provisional_body_r5.py"
STRUCTURAL_AUDIT = ROOT / "tools" / "audit_avatar_body_topology.py"
GEOMETRY_AUDIT = ROOT / "tools" / "blender_audit_avatar_candidate_quality.py"
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
ARTIFACT_ROOT = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "candidate_sources"
    / "kira_provisional_body_r5"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(ROOT),
        check=check,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def create_contact_sheet(run_dir: Path, manifest: dict[str, object]) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    keys = [
        "neutral_front",
        "neutral_side",
        "neutral_back",
        "reach_front_three_quarter",
        "stride_front_three_quarter",
        "stride_side",
        "seated_front_three_quarter",
        "seated_side",
    ]
    tile_width, tile_height = 300, 400
    header_height = 76
    columns = 4
    rows = 2
    sheet = Image.new(
        "RGB",
        (columns * tile_width, header_height + rows * tile_height),
        (7, 12, 19),
    )
    draw = ImageDraw.Draw(sheet)
    try:
        title_font = ImageFont.truetype("arial.ttf", 21)
        label_font = ImageFont.truetype("arial.ttf", 14)
        note_font = ImageFont.truetype("arial.ttf", 12)
    except OSError:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        note_font = ImageFont.load_default()
    draw.text(
        (16, 12),
        "Kira provisional body R5 — PRIVATE / INACTIVE / NOT APPROVED",
        fill=(232, 240, 246),
        font=title_font,
    )
    draw.text(
        (16, 45),
        "Body-only deformation evidence; no eyes, hair, clothes, shoes, likeness, anatomy, or autobuild pass.",
        fill=(234, 182, 103),
        font=note_font,
    )
    renders = manifest["renders"]
    assert isinstance(renders, dict)
    for index, key in enumerate(keys):
        record = renders[key]
        assert isinstance(record, dict)
        source = Path(str(record["path"]))
        column, row = index % columns, index // columns
        x_value = column * tile_width
        y_value = header_height + row * tile_height
        draw.rectangle(
            (
                x_value + 7,
                y_value + 7,
                x_value + tile_width - 7,
                y_value + tile_height - 7,
            ),
            outline=(39, 105, 130),
            width=2,
        )
        with Image.open(source) as image:
            image = image.convert("RGB")
            image.thumbnail((tile_width - 28, tile_height - 60))
            sheet.paste(
                image,
                (
                    x_value + (tile_width - image.width) // 2,
                    y_value + 14,
                ),
            )
        draw.text(
            (x_value + 14, y_value + tile_height - 35),
            key,
            fill=(204, 222, 232),
            font=label_font,
        )
    output = run_dir / "kira_provisional_body_r5_contact_sheet.png"
    sheet.save(output)
    return output


def main() -> int:
    if not BLENDER.is_file():
        raise SystemExit(f"Missing Blender executable: {BLENDER}")
    for required in (WORKER, STRUCTURAL_AUDIT, GEOMETRY_AUDIT):
        if not required.is_file():
            raise SystemExit(f"Missing required R5 tool: {required}")
    if not SOURCE.is_file() or sha256_file(SOURCE) != SOURCE_SHA256:
        raise SystemExit("The exact enrolled 3ec62 Kira cage is missing or changed.")
    if not LIVE_MODEL.is_file():
        raise SystemExit(f"Missing live Kira avatar hash-guard target: {LIVE_MODEL}")
    source_before = sha256_file(SOURCE)
    live_before = sha256_file(LIVE_MODEL)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = ARTIFACT_ROOT / f"r5_{timestamp}"
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
        raise RuntimeError("Source cage changed during the R5 build; stop and investigate.")
    if live_after != live_before:
        raise RuntimeError("Live Kira avatar changed during the private R5 build; stop and investigate.")
    manifest_path = run_dir / "kira_provisional_body_r5_manifest.json"
    candidate_path = run_dir / "kira_provisional_body_r5.glb"
    if not manifest_path.is_file() or not candidate_path.is_file():
        raise RuntimeError("R5 worker did not create its candidate and manifest.")
    candidate_sha256 = sha256_file(candidate_path)
    if candidate_sha256 == SOURCE_SHA256:
        raise RuntimeError("R5 candidate is a byte copy of the source, not a transformed derivative.")

    structural_output = run_dir / "structural_rig_topology_audit.json"
    run(
        [
            "python",
            str(STRUCTURAL_AUDIT),
            str(candidate_path),
            "--artifact-id",
            f"kira_provisional_body_r5_{candidate_sha256[:12]}",
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
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contact_sheet = create_contact_sheet(run_dir, manifest)
    structural = json.loads(structural_output.read_text(encoding="utf-8"))
    geometry = json.loads(geometry_output.read_text(encoding="utf-8"))
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
        "candidate_sha256": candidate_sha256,
        "candidate_differs_from_source": candidate_sha256 != source_before,
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
    }
    manifest["contact_sheet"] = {
        "path": str(contact_sheet),
        "sha256": sha256_file(contact_sheet),
        "size_bytes": contact_sheet.stat().st_size,
        "visual_qa_status": "pending_independent_human_or_agent_inspection",
    }
    manifest["autobuild_gate"] = {
        "passed_subjects": 0,
        "required_subjects": 2,
        "passed": False,
        "reason": "R5 is one provisional, unapproved Kira body candidate and cannot self-pass.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    summary = {
        "ok": True,
        "run_dir": relative(run_dir),
        "candidate": relative(candidate_path),
        "candidate_sha256": candidate_sha256,
        "manifest": relative(manifest_path),
        "contact_sheet": relative(contact_sheet),
        "renders": {
            key: relative(Path(value["path"])) for key, value in manifest["renders"].items()
        },
        "source_unchanged": True,
        "live_model_unchanged": True,
        "humanoid_rig_structurally_ready": structural.get("humanoid_rig_structurally_ready"),
        "owner_approved": False,
        "autobuild_gate": "0/2",
    }
    summary_path = run_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
