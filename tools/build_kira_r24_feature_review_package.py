"""Build a human-readable, private review package for R24 attempt_04."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ATTEMPT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_feature_aligned_centerline_surface/attempt_04"
)
REVIEW = ATTEMPT / "private_owner_review"
REPORT = ATTEMPT / "SIMULATION_REPORT.json"
ORDINARY_SHEET = REVIEW / "ORDINARY_VIEWS_CONTACT_SHEET.png"
PROTECTED_SHEET = REVIEW / "PROTECTED_CLINICAL_CONTACT_SHEET.png"
INDEX = ATTEMPT / "REVIEW_INDEX.md"
MANIFEST = ATTEMPT / "PACKAGE_MANIFEST.json"
CHECKPOINT = ATTEMPT / "CHECKPOINT.md"

SOURCE = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/"
    "attempt_06/kira_r19_bald_targeted_material_movement_correction.blend"
)
WORKER = ROOT / "tools/blender_simulate_kira_r24_feature_aligned_centerline_surface.py"

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
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    path = Path("C:/Windows/Fonts") / name
    try:
        return ImageFont.truetype(str(path), size=size)
    except OSError:
        return ImageFont.load_default()


def contact_sheet(
    entries: tuple[tuple[str, str], ...],
    output: Path,
    columns: int,
    title: str,
    protected: bool,
) -> None:
    tile_width = 470
    tile_height = 520
    header_height = 92
    rows = (len(entries) + columns - 1) // columns
    background = (7, 13, 21)
    sheet = Image.new("RGB", (columns * tile_width, header_height + rows * tile_height), background)
    draw = ImageDraw.Draw(sheet)
    banner = (132, 30, 36) if protected else (13, 54, 76)
    draw.rectangle((0, 0, sheet.width, header_height), fill=banner)
    draw.text((24, 16), title, font=font(30, bold=True), fill=(255, 255, 255))
    subtitle = (
        "PRIVATE OWNER REVIEW — PROTECTED CLINICAL EVIDENCE — DO NOT PUBLISH"
        if protected
        else "PRIVATE OWNER REVIEW — ordinary whole-body views"
    )
    draw.text((24, 55), subtitle, font=font(18), fill=(242, 242, 242))
    for offset, (filename, label) in enumerate(entries):
        source = REVIEW / filename
        if not source.is_file():
            raise FileNotFoundError(source)
        image = Image.open(source).convert("RGB")
        image.thumbnail((tile_width - 20, tile_height - 62), Image.Resampling.LANCZOS)
        column = offset % columns
        row = offset // columns
        left = column * tile_width
        top = header_height + row * tile_height
        image_left = left + (tile_width - image.width) // 2
        image_top = top + 8
        sheet.paste(image, (image_left, image_top))
        draw.rectangle(
            (left, top + tile_height - 54, left + tile_width, top + tile_height),
            fill=(13, 24, 36),
        )
        draw.text((left + 12, top + tile_height - 49), label, font=font(20, bold=True), fill=(255, 255, 255))
        draw.text((left + 12, top + tile_height - 25), filename, font=font(13), fill=(153, 222, 242))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="PNG", optimize=True)


def main() -> None:
    outputs = (ORDINARY_SHEET, PROTECTED_SHEET, INDEX, MANIFEST, CHECKPOINT)
    existing = [relative(path) for path in outputs if path.exists()]
    if existing:
        raise RuntimeError(f"append-only review outputs already exist: {existing}")
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    failed = [name for name, value in report["gates"]["checks"].items() if not value]
    contact_sheet(
        ORDINARY,
        ORDINARY_SHEET,
        2,
        "Kira R24 Attempt 04 — Ordinary Review Views",
        False,
    )
    contact_sheet(
        PROTECTED,
        PROTECTED_SHEET,
        3,
        "Kira R24 Attempt 04 — Protected Clinical Diagnostics",
        True,
    )

    index_text = f"""# Kira R24 attempt 04 review index

Status: **AUTOMATED GATES FAILED — NOT AN APPROVED BODY — NO BLEND SAVED**

This is the best retained result from the bounded feature-aligned retopology
simulation. It is private, inactive, unassigned, unexported, and unsuitable for
runtime use. The whole body, patch manifold, exact 102-vertex seam, frozen
out-of-mask source state, semantic-set presence, and clinical longitudinal order
passed. The remaining central pelvic geometry is visibly compressed and still
intersects; it must not be described as complete or functional anatomy.

## Ordinary whole-body review

![Ordinary views](private_owner_review/ORDINARY_VIEWS_CONTACT_SHEET.png)

## Protected clinical review

The following evidence is private and clinical. Do not publish it or combine it
with the ordinary owner sheet.

![Protected clinical views](private_owner_review/PROTECTED_CLINICAL_CONTACT_SHEET.png)

## Objective unresolved defects

- Failed gates: `{', '.join(failed)}`.
- Patch-related exact genuine penetration pairs: `{report['gates']['exact_intersections']['patch_related_exact_genuine_pair_count']}`.
- Seam minimum face-normal dot: `{report['gates']['seam_normal_dot']['minimum']:.9f}`.
- Maximum seam dihedral: `{report['gates']['seam_normal_dot']['maximum_dihedral_degrees']:.6f}` degrees.
- Maximum patch edge ratio: `{report['gates']['maximum_patch_edge_ratio']:.6f}`.

## Truth boundary

This package demonstrates only an external, no-save visual/topology simulation.
It does not implement or prove an internal urinary, vaginal, reproductive,
rectal, pelvic-floor, continence, elimination, pregnancy, sensation, privacy,
consent, intimate-behavior, or subjective-experience system. It is not owner
approval, runtime readiness, activation, assignment, export, publication, or a
biological-function claim.

See `SIMULATION_REPORT.json` for machine-readable evidence and `CHECKPOINT.md`
for exact hashes and rollback instructions.
"""
    INDEX.write_text(index_text, encoding="utf-8")

    inventory = []
    excluded = {MANIFEST.resolve(), CHECKPOINT.resolve()}
    for path in sorted(item for item in ATTEMPT.rglob("*") if item.is_file()):
        if path.resolve() in excluded:
            continue
        inventory.append(
            {
                "path": relative(path),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    manifest = {
        "schema": "kira.avatar.r24_feature_aligned_private_review_manifest.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PRIVATE_INACTIVE_NO_SAVE_AUTOMATED_GATES_FAILED",
        "attempt": relative(ATTEMPT),
        "source": {"path": relative(SOURCE), "sha256": sha256(SOURCE)},
        "worker": {"path": relative(WORKER), "sha256": sha256(WORKER)},
        "inventory_excludes": [relative(MANIFEST), relative(CHECKPOINT)],
        "files": inventory,
        "ordinary_and_protected_contact_sheets_separate": True,
        "runtime_or_person_state_changed": False,
        "blend_saved": False,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    checkpoint_text = f"""# Kira R24 feature-aligned attempt 04 checkpoint

Created UTC: {datetime.now(timezone.utc).isoformat()}

## Result

`NO_SAVE_STRUCTURAL_OR_SEMANTIC_GATE_FAILURE_RETAINED_FOR_DIAGNOSIS`

The harmonic exact-source resampling removed attempt 02's catastrophic panel
folding, but attempt 04 remains rejected by the exact intersection, worst seam
normal/dihedral, and maximum edge-ratio gates. It is preserved for Robert's
private visual review and component-level diagnosis only.

## Exact bindings

- Source: `{relative(SOURCE)}`
  - SHA-256: `{sha256(SOURCE)}`
- Worker: `{relative(WORKER)}`
  - SHA-256: `{sha256(WORKER)}`
- Report: `{relative(REPORT)}`
  - SHA-256: `{sha256(REPORT)}`
- Package manifest: `{relative(MANIFEST)}`
  - SHA-256: `{sha256(MANIFEST)}`
- Ordinary contact sheet: `{relative(ORDINARY_SHEET)}`
  - SHA-256: `{sha256(ORDINARY_SHEET)}`
- Protected contact sheet: `{relative(PROTECTED_SHEET)}`
  - SHA-256: `{sha256(PROTECTED_SHEET)}`

## Preserved attempts

- `attempt_01`: Blender 5.1 Eevee enum setup failure, no save.
- `attempt_02`: straight-row baseline structural failure, report SHA-256
  `b10d9833a3257cf7d3c5196747eb003f1a22330cc9a3dd29471832154f8a9400`.
- `attempt_03`: pre-mutation zero-area parameter-triangle diagnostic failure,
  no save.
- `attempt_04`: current best bounded diagnostic, still failed and inactive.

## Rollback

No Blend was saved, no source was overwritten, and no runtime/person/voice state
was changed. The sealed R19 source is already the rollback state. To disregard
this simulation, leave all R24 evidence inactive and continue referencing the
sealed source hash above. Do not delete the append-only failure evidence.

## Truth scope

External private visual/topology simulation only. No internal route,
physiology, elimination, reproduction, pregnancy, sensation, subjective state,
consent, owner approval, runtime readiness, activation, assignment, export, or
publication is implemented or claimed.
"""
    CHECKPOINT.write_text(checkpoint_text, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "review_index": relative(INDEX),
                "checkpoint": relative(CHECKPOINT),
                "manifest": relative(MANIFEST),
            }
        )
    )


if __name__ == "__main__":
    main()
