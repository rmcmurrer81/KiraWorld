"""Build append-only private review evidence for an R24 direct-subdivision attempt."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / (
    "RecoverySprint/continuation_20260803/kira_r24_direct_subdivision_surface"
)
SOURCE = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/"
    "attempt_06/kira_r19_bald_targeted_material_movement_correction.blend"
)
WORKER = ROOT / "tools/blender_simulate_kira_r24_direct_subdivision_surface.py"

ORDINARY = (
    ("ordinary_full_front.png", "Full front"),
    ("ordinary_left_three_quarter.png", "Left three-quarter"),
    ("ordinary_side_profile.png", "Side profile"),
    ("ordinary_rear.png", "Rear"),
)
PROTECTED = (
    ("protected_clinical_front.png", "Clinical front"),
    ("protected_clinical_left_three_quarter.png", "Clinical left three-quarter"),
    ("protected_clinical_profile.png", "Clinical profile"),
    ("protected_clinical_inferior.png", "Clinical inferior"),
    ("protected_clinical_rear.png", "Clinical rear"),
    ("protected_clinical_wire.png", "Topology wire"),
    ("protected_clinical_feature_mask.png", "Semantic feature mask"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = Path("C:/Windows/Fonts") / ("segoeuib.ttf" if bold else "segoeui.ttf")
    try:
        return ImageFont.truetype(str(path), size=size)
    except OSError:
        return ImageFont.load_default()


def contact_sheet(
    review: Path,
    entries: tuple[tuple[str, str], ...],
    output: Path,
    *,
    columns: int,
    title: str,
    protected: bool,
) -> None:
    tile_width, tile_height, header_height = 470, 520, 92
    rows = (len(entries) + columns - 1) // columns
    sheet = Image.new(
        "RGB", (columns * tile_width, header_height + rows * tile_height), (7, 13, 21)
    )
    draw = ImageDraw.Draw(sheet)
    draw.rectangle(
        (0, 0, sheet.width, header_height),
        fill=(132, 30, 36) if protected else (13, 54, 76),
    )
    draw.text((24, 16), title, font=font(30, True), fill=(255, 255, 255))
    subtitle = (
        "PRIVATE OWNER REVIEW — PROTECTED CLINICAL EVIDENCE — DO NOT PUBLISH"
        if protected
        else "PRIVATE OWNER REVIEW — ordinary whole-body views"
    )
    draw.text((24, 55), subtitle, font=font(18), fill=(242, 242, 242))
    for offset, (filename, label) in enumerate(entries):
        source = review / filename
        if not source.is_file():
            raise FileNotFoundError(source)
        image = Image.open(source).convert("RGB")
        image.thumbnail((tile_width - 20, tile_height - 62), Image.Resampling.LANCZOS)
        column, row = offset % columns, offset // columns
        left, top = column * tile_width, header_height + row * tile_height
        sheet.paste(image, (left + (tile_width - image.width) // 2, top + 8))
        draw.rectangle(
            (left, top + tile_height - 54, left + tile_width, top + tile_height),
            fill=(13, 24, 36),
        )
        draw.text((left + 12, top + tile_height - 49), label, font=font(20, True), fill="white")
        draw.text(
            (left + 12, top + tile_height - 25),
            filename,
            font=font(13),
            fill=(153, 222, 242),
        )
    sheet.save(output, format="PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", type=int, required=True)
    args = parser.parse_args()
    attempt = BASE / f"attempt_{args.attempt:02d}"
    review = attempt / "private_owner_review"
    report_path = attempt / "SIMULATION_REPORT.json"
    if not report_path.is_file():
        raise FileNotFoundError(report_path)
    ordinary_sheet = review / "ORDINARY_VIEWS_CONTACT_SHEET.png"
    protected_sheet = review / "PROTECTED_CLINICAL_CONTACT_SHEET.png"
    index = attempt / "REVIEW_INDEX.md"
    checkpoint = attempt / "CHECKPOINT.md"
    manifest = attempt / "PACKAGE_MANIFEST.json"
    outputs = (ordinary_sheet, protected_sheet, index, checkpoint, manifest)
    if any(path.exists() for path in outputs):
        raise RuntimeError("append-only review output already exists")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    passed = bool(report["gates"]["passed"])
    failed = [name for name, value in report["gates"]["checks"].items() if not value]
    contact_sheet(
        review,
        ORDINARY,
        ordinary_sheet,
        columns=2,
        title=f"Kira R24 Direct Subdivision Attempt {args.attempt:02d} — Ordinary Views",
        protected=False,
    )
    contact_sheet(
        review,
        PROTECTED,
        protected_sheet,
        columns=3,
        title=f"Kira R24 Direct Subdivision Attempt {args.attempt:02d} — Clinical Diagnostics",
        protected=True,
    )
    status_text = (
        "STRUCTURAL GATES PASS — VISUAL OWNER REVIEW REQUIRED — NO BLEND SAVED"
        if passed
        else "AUTOMATED GATES FAILED — DIAGNOSTIC ONLY — NO BLEND SAVED"
    )
    visual_note = (
        "No owner visual decision has been inferred from the automated pass."
        if passed
        else (
            "The result remains visually rejected: a horizontal superior seam is visible and "
            "the central external landmarks remain too recessed and subtle."
        )
    )
    index.write_text(
        f"""# Kira R24 direct-subdivision attempt {args.attempt:02d} review index

Status: **{status_text}**

The exact embedded R19 patch was refined in place with its original 34-edge
seam fixed. The package is private, inactive, unassigned, unexported, and does
not contain a saved candidate Blend. {visual_note}

## Ordinary whole-body review

![Ordinary views](private_owner_review/ORDINARY_VIEWS_CONTACT_SHEET.png)

## Protected clinical review

![Protected clinical views](private_owner_review/PROTECTED_CLINICAL_CONTACT_SHEET.png)

## Objective result

- Failed gates: `{', '.join(failed) if failed else 'none'}`.
- Patch-related exact penetrations: `{report['gates']['exact_intersections']['patch_related_exact_genuine_pair_count']}`.
- Seam minimum/median dot: `{report['gates']['seam_normal_dot']['minimum']:.9f}` / `{report['gates']['seam_normal_dot']['median']:.9f}`.
- Maximum seam dihedral: `{report['gates']['seam_normal_dot']['maximum_dihedral_degrees']:.6f}` degrees.
- Maximum patch edge ratio: `{report['gates']['maximum_patch_edge_ratio']:.6f}`.

## Truth boundary

External visual/topology simulation only. No internal route, physiology,
elimination, reproduction, pregnancy, sensation, privacy, consent, subjective
state, owner approval, runtime readiness, activation, assignment, export, or
publication is implemented or claimed.
""",
        encoding="utf-8",
    )

    inventory = []
    for path in sorted(item for item in attempt.rglob("*") if item.is_file()):
        if path.resolve() in {manifest.resolve(), checkpoint.resolve()}:
            continue
        inventory.append(
            {"path": relative(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
        )
    manifest.write_text(
        json.dumps(
            {
                "schema": "kira.avatar.r24_direct_subdivision_private_review_manifest.v1",
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "status": (
                    "PRIVATE_INACTIVE_NO_SAVE_STRUCTURAL_PASS_VISUAL_REVIEW_REQUIRED"
                    if passed
                    else "PRIVATE_INACTIVE_NO_SAVE_AUTOMATED_GATES_FAILED"
                ),
                "attempt": relative(attempt),
                "source": {"path": relative(SOURCE), "sha256": sha256(SOURCE)},
                "worker": {"path": relative(WORKER), "sha256": sha256(WORKER)},
                "files": inventory,
                "ordinary_and_protected_contact_sheets_separate": True,
                "blend_saved": False,
                "runtime_or_person_state_changed": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    checkpoint.write_text(
        f"""# Kira R24 direct-subdivision attempt {args.attempt:02d} checkpoint

Created UTC: {datetime.now(timezone.utc).isoformat()}

## Result

`{report['status']}`

The exact sealed R19 source and all earlier R24 evidence remain unchanged. The
worker saved no Blend and changed no runtime/person/voice state.

## Exact bindings

- Source: `{relative(SOURCE)}` — SHA-256 `{sha256(SOURCE)}`
- Worker: `{relative(WORKER)}` — SHA-256 `{sha256(WORKER)}`
- Report: `{relative(report_path)}` — SHA-256 `{sha256(report_path)}`
- Manifest: `{relative(manifest)}` — SHA-256 `{sha256(manifest)}`
- Ordinary sheet: `{relative(ordinary_sheet)}` — SHA-256 `{sha256(ordinary_sheet)}`
- Protected sheet: `{relative(protected_sheet)}` — SHA-256 `{sha256(protected_sheet)}`

## Failed gates

`{', '.join(failed) if failed else 'none'}`

## Rollback

No authored candidate exists. The sealed R19 source is already the rollback
state. Preserve this append-only evidence and do not delete it.

## Truth scope

External private visual/topology evidence only; no functional, physiological,
person, runtime, or owner-approval claim.
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
