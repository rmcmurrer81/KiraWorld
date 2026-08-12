"""Run one bounded, private Kira avatar quality pass in Blender."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
WORKER = ROOT / "tools" / "blender_build_kira_inactive_quality_candidate.py"
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
    / "kira_inactive_quality_r3"
    / "private_review"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def create_contact_sheet(run_dir: Path, manifest: dict) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    keys = [
        "relaxed_front",
        "relaxed_front_three_quarter",
        "relaxed_left_profile",
        "relaxed_back",
        "relaxed_head_closeup",
        "relaxed_head_left_profile",
        "walk_front_three_quarter",
        "walk_left_profile",
        "walk_head_three_quarter",
        "reach_front_three_quarter",
        "reach_left_profile",
        "reach_head_three_quarter",
    ]
    tile_w, tile_h = 300, 390
    header_h = 62
    sheet = Image.new("RGB", (tile_w * 4, tile_h * 3 + header_h), (8, 14, 22))
    draw = ImageDraw.Draw(sheet)
    try:
        title_font = ImageFont.truetype("arial.ttf", 22)
        label_font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
    draw.text(
        (18, 17),
        "Kira inactive quality R3 — clothed private review; owner approval pending",
        fill=(230, 240, 246),
        font=title_font,
    )
    for index, key in enumerate(keys):
        record = manifest["renders"][key]
        source = Path(record["path"])
        column, row = index % 4, index // 4
        x, y = column * tile_w, header_h + row * tile_h
        draw.rectangle(
            (x + 7, y + 7, x + tile_w - 7, y + tile_h - 7),
            outline=(42, 105, 126),
            width=2,
        )
        with Image.open(source) as image:
            image = image.convert("RGB")
            image.thumbnail((tile_w - 28, tile_h - 56))
            sheet.paste(image, (x + (tile_w - image.width) // 2, y + 15))
        draw.text((x + 14, y + tile_h - 34), key, fill=(205, 222, 232), font=label_font)
    output = run_dir / "kira_inactive_quality_r3_contact_sheet.png"
    sheet.save(output)
    return output


def main() -> int:
    if not BLENDER.is_file():
        raise SystemExit(f"Missing Blender: {BLENDER}")
    if not SOURCE.is_file() or sha256_file(SOURCE) != SOURCE_SHA256:
        raise SystemExit("Kira adult base is missing or its exact hash changed.")
    if not LIVE_MODEL.is_file():
        raise SystemExit(f"Missing live Kira model: {LIVE_MODEL}")
    live_before = sha256_file(LIVE_MODEL)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = ARTIFACT_ROOT / f"kira_inactive_quality_r3_{stamp}"
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
        "live_model_project_path_for_unchanged_hash_check_only": relative(LIVE_MODEL),
        "live_model_sha256_before": live_before,
        "runtime_activation_requested": False,
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
    live_after = sha256_file(LIVE_MODEL)
    if live_after != live_before:
        raise RuntimeError("Live Kira model changed during an inactive build; stop and investigate.")
    manifest_path = run_dir / "kira_inactive_quality_r3_manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(
            "Blender did not produce the candidate manifest; inspect the Blender traceback above."
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contact_sheet = create_contact_sheet(run_dir, manifest)
    manifest["live_model_unchanged_evidence"] = {
        "project_path": relative(LIVE_MODEL),
        "sha256_before": live_before,
        "sha256_after": live_after,
        "unchanged": live_before == live_after,
    }
    manifest["contact_sheet"] = {
        "path": str(contact_sheet),
        "sha256": sha256_file(contact_sheet),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "run_dir": relative(run_dir),
                "manifest": relative(manifest_path),
                "contact_sheet": relative(contact_sheet),
                "live_model_unchanged": True,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
