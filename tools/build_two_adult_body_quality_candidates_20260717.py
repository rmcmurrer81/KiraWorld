"""Run the bounded Kira/Gwen inactive adult-body quality build."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
WORKER = ROOT / "tools" / "blender_build_two_adult_body_quality_candidates.py"
SOURCE = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "asset_library"
    / "base_body_reference"
    / "base_female_game_ready_rigged_low_poly_1_471903a311.glb"
)
SOURCE_SHA256 = "471903a31194e6cd364b2980580ddc976c48ac755a2bfacfe3115615501eceb2"
OUTPUT_ROOT = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "candidate_sources"
    / "two_body_quality_r4"
    / "private_review"
)
LIVE_MODELS = {
    "kira": ROOT / "Avatar" / "models" / "temp_ai" / "kira" / "avatar.glb",
    "gwen": (
        ROOT
        / "Avatar"
        / "models"
        / "temp_ai"
        / "spider_gwen_spider_gwen_20260606_013325"
        / "avatar.glb"
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def axis_preflight_sanity(metrics: dict[str, object]) -> dict[str, object]:
    """Fail closed unless the neutral evaluated assembly is plainly Z-up."""

    extent = metrics.get("extent")
    finite = metrics.get("finite_coordinates") is True
    if not (
        isinstance(extent, list)
        and len(extent) == 3
        and all(isinstance(value, (int, float)) for value in extent)
    ):
        return {"passed": False, "reason": "missing_or_invalid_extent"}
    width, depth, height = (float(value) for value in extent)
    passed = (
        finite
        and height > 1.25
        and height > width * 1.35
        and height > depth * 2.0
    )
    return {
        "passed": passed,
        "finite_coordinates": finite,
        "extent": [round(width, 6), round(depth, 6), round(height, 6)],
        "z_up_height_over_width": round(height / max(width, 1e-9), 6),
        "z_up_height_over_depth": round(height / max(depth, 1e-9), 6),
        "reason": "bounded_z_up" if passed else "rejected_orientation_or_unbounded_assembly",
    }


def validate_render_bindings(
    manifest: dict[str, object],
    *,
    run_dir: Path,
    project_root: Path = ROOT,
) -> dict[str, object]:
    """Bind every declared render to one hashed file inside this exact run."""

    renders = manifest.get("renders")
    if not isinstance(renders, dict) or not renders:
        raise RuntimeError("manifest has no bound renders")
    resolved_run = run_dir.resolve()
    seen: set[Path] = set()
    records: dict[str, object] = {}
    for name, record in renders.items():
        if not isinstance(record, dict):
            raise RuntimeError(f"invalid render record: {name}")
        project_path = record.get("path")
        expected_hash = record.get("sha256")
        if not isinstance(project_path, str) or not isinstance(expected_hash, str):
            raise RuntimeError(f"incomplete render binding: {name}")
        path = (project_root / project_path).resolve()
        try:
            path.relative_to(resolved_run)
        except ValueError as error:
            raise RuntimeError(f"render escapes exact run directory: {name}") from error
        if path in seen:
            raise RuntimeError(f"duplicate render output binding: {name}")
        if not path.is_file():
            raise RuntimeError(f"manifest render is missing: {project_path}")
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise RuntimeError(f"render hash binding failed: {project_path}")
        seen.add(path)
        records[name] = {
            "path": project_path,
            "sha256": actual_hash,
            "inside_exact_run": True,
        }
    return {"passed": True, "count": len(records), "records": records}


def generated_evidence_gate_truth(subject_count: int) -> dict[str, object]:
    """Generated files cannot self-authorize owner approval or autobuild."""

    return {
        "generated_subject_evidence_count": int(subject_count),
        "owner_approval_may_be_inferred_from_generated_evidence": False,
        "owner_approved": False,
        "positive_proof_gate_released": False,
        "two_subject_autobuild_released": False,
        "required_external_event": "Robert reviews and explicitly approves each exact candidate",
    }


def create_contact_sheet(subject: str, manifest: dict, run_dir: Path) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    keys = [
        "neutral_front",
        "neutral_front_three_quarter",
        "neutral_left_profile",
        "neutral_back",
        "head_front",
        "head_three_quarter",
        "head_profile",
        "stride_front_three_quarter",
        "reach_front_three_quarter",
    ]
    tile_w, tile_h = 320, 420
    header_h = 72
    sheet = Image.new("RGB", (tile_w * 3, tile_h * 3 + header_h), (8, 14, 22))
    draw = ImageDraw.Draw(sheet)
    try:
        title_font = ImageFont.truetype("arial.ttf", 21)
        label_font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
    draw.text(
        (18, 20),
        f"{subject.title()} adult quality R4 - clothed private review; approval pending",
        fill=(230, 240, 246),
        font=title_font,
    )
    for index, key in enumerate(keys):
        record = manifest["renders"][key]
        source = ROOT / record["path"]
        if not source.is_file():
            raise RuntimeError(f"manifest render is missing: {record['path']}")
        column, row = index % 3, index // 3
        x, y = column * tile_w, header_h + row * tile_h
        draw.rectangle((x + 7, y + 7, x + tile_w - 7, y + tile_h - 7), outline=(42, 105, 126), width=2)
        with Image.open(source) as image:
            image = image.convert("RGB")
            image.thumbnail((tile_w - 28, tile_h - 58))
            sheet.paste(image, (x + (tile_w - image.width) // 2, y + 14))
        draw.text((x + 14, y + tile_h - 34), key, fill=(205, 222, 232), font=label_font)
    output = run_dir / subject / f"{subject}_quality_r4_contact_sheet.png"
    sheet.save(output)
    return output


def render_occupancy_sanity(path: Path, *, head_view: bool) -> dict[str, object]:
    """Fail closed on blank, edge-filled, or badly cropped review renders."""

    from PIL import Image

    with Image.open(path) as source:
        image = source.convert("RGB")
        width, height = image.size
        pixels = image.load()
        # Review subjects are deliberately lit above the dark neutral backdrop.
        # Ignore the lowest 7% where the light ground plane can span the frame.
        points: list[tuple[int, int]] = []
        y_limit = max(1, round(height * 0.93))
        for y in range(y_limit):
            for x in range(width):
                red, green, blue = pixels[x, y]
                if max(red, green, blue) >= 92 and (red + green + blue) >= 260:
                    points.append((x, y))
        if not points:
            return {"passed": False, "reason": "no_lit_subject_pixels"}
        left = min(point[0] for point in points)
        right = max(point[0] for point in points)
        top = min(point[1] for point in points)
        bottom = max(point[1] for point in points)
        box_width = (right - left + 1) / width
        box_height = (bottom - top + 1) / height
        coverage = len(points) / (width * y_limit)
        if head_view:
            passed = (
                0.18 <= box_width <= 0.88
                and 0.35 <= box_height <= 0.93
                and 0.01 <= top / height <= 0.32
                and coverage >= 0.025
            )
        else:
            passed = (
                0.08 <= box_width <= 0.78
                and 0.62 <= box_height <= 0.93
                and 0.01 <= top / height <= 0.20
                and coverage >= 0.02
            )
        return {
            "passed": passed,
            "lit_subject_bbox_px": [left, top, right, bottom],
            "bbox_width_fraction": round(box_width, 6),
            "bbox_height_fraction": round(box_height, 6),
            "top_margin_fraction": round(top / height, 6),
            "lit_pixel_coverage": round(coverage, 6),
            "head_view": head_view,
        }


def main() -> int:
    if not BLENDER.is_file():
        raise SystemExit(f"Missing Blender: {BLENDER}")
    if not SOURCE.is_file() or sha256_file(SOURCE) != SOURCE_SHA256:
        raise SystemExit("The exact authorized 471903 source is missing or changed.")
    live_before = {
        subject: sha256_file(path) for subject, path in LIVE_MODELS.items() if path.is_file()
    }
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUTPUT_ROOT / f"two_body_quality_r4_{stamp}"
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
        "runtime_activation_requested": False,
        "public_export_requested": False,
    }
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    subprocess.run(
        [
            str(BLENDER),
            "--background",
            "--python",
            str(WORKER),
            "--",
            "--config",
            str(config_path),
        ],
        cwd=str(ROOT),
        check=True,
    )
    live_after = {
        subject: sha256_file(path) for subject, path in LIVE_MODELS.items() if path.is_file()
    }
    if live_after != live_before:
        raise RuntimeError("A live Kira or Gwen model changed during the inactive build.")
    subjects: dict[str, object] = {}
    for subject in ("kira", "gwen"):
        manifest_path = run_dir / subject / f"{subject}_quality_r4_manifest.json"
        if not manifest_path.is_file():
            raise RuntimeError(f"missing {subject} manifest")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        axis_sanity = axis_preflight_sanity(
            manifest.get("rig", {}).get("neutral_z_up_axis_preflight", {})
        )
        if axis_sanity["passed"] is not True:
            raise RuntimeError(f"axis preflight failed for {subject}: {axis_sanity}")
        render_bindings = validate_render_bindings(manifest, run_dir=run_dir)
        render_sanity: dict[str, object] = {}
        for name, record in manifest["renders"].items():
            path = ROOT / record["path"]
            sanity = render_occupancy_sanity(path, head_view=name.startswith("head_"))
            render_sanity[name] = sanity
            if sanity["passed"] is not True:
                raise RuntimeError(f"render framing sanity failed for {subject}/{name}: {sanity}")
        manifest["render_framing_sanity"] = {
            "all_passed": True,
            "method": "lit_subject_bbox_v1",
            "views": render_sanity,
        }
        manifest["evaluated_axis_sanity"] = axis_sanity
        manifest["render_output_binding"] = render_bindings
        contact_sheet = create_contact_sheet(subject, manifest, run_dir)
        manifest["contact_sheet"] = {
            "path": relative(contact_sheet),
            "sha256": sha256_file(contact_sheet),
        }
        manifest["live_model_unchanged_evidence"] = {
            "path": relative(LIVE_MODELS[subject]),
            "sha256_before": live_before.get(subject, ""),
            "sha256_after": live_after.get(subject, ""),
            "unchanged": live_before.get(subject) == live_after.get(subject),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        subjects[subject] = {
            "manifest": relative(manifest_path),
            "contact_sheet": relative(contact_sheet),
            "model": manifest["model"]["path"],
            "owner_approved": False,
        }
    generated_gate_truth = generated_evidence_gate_truth(len(subjects))
    run_manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run": relative(run_dir),
        "subjects": subjects,
        "ordinary_review_is_clothed": True,
        "anatomical_completeness_proven": False,
        "live_models_unchanged": True,
        "runtime_activation_allowed": False,
        "generated_evidence_gate_truth": generated_gate_truth,
        "positive_proof_gate_released": generated_gate_truth["positive_proof_gate_released"],
        "two_subject_autobuild_released": generated_gate_truth["two_subject_autobuild_released"],
        "autobuild_blockers": [
            "Robert has not approved either exact clothed candidate",
            "identity likeness remains unproven",
            "stable motion/deformation remains unproven",
            "face controls, blink, gaze, and dressing behavior remain unproven",
            "anatomical completeness remains unproven",
        ],
    }
    run_manifest_path = run_dir / "two_body_quality_r4_run_manifest.json"
    run_manifest_path.write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "run_manifest": relative(run_manifest_path), "subjects": subjects}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
