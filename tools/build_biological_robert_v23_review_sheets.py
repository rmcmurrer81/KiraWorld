"""Build the private V23 static-likeness review contact sheets.

The script deliberately consumes only the named Blender review renders below.
It never discovers, opens, or embeds Robert's protected source photographs.

Examples:

    py tools/build_biological_robert_v23_review_sheets.py ^
        --candidate-folder Avatar/private_owner_review/.../candidate

    py tools/build_biological_robert_v23_review_sheets.py ^
        --render-folder Avatar/private_owner_review/.../candidate/private_review
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw, ImageFont


OVERVIEW_RENDERS: tuple[tuple[str, str], ...] = (
    ("FRONT", "front.png"),
    ("REAR", "rear.png"),
    ("LEFT PROFILE", "left_profile.png"),
    ("RIGHT PROFILE", "right_profile.png"),
    ("LEFT THREE-QUARTER", "left_three_quarter.png"),
    ("RIGHT THREE-QUARTER", "right_three_quarter.png"),
    ("NEUTRAL CLOSE FACE", "close_face.png"),
)

PROTECTED_DETAIL_RENDERS: tuple[tuple[str, str], ...] = (
    ("LOCAL FRONT", "close_pelvis_front.png"),
    ("LOCAL LEFT THREE-QUARTER", "close_pelvis_left_three_quarter.png"),
    ("LOCAL RIGHT THREE-QUARTER", "close_pelvis_right_three_quarter.png"),
    ("LOCAL SIDE", "close_pelvis_side.png"),
    ("LEFT HAND AND NAILS", "close_hand_left.png"),
    ("RIGHT HAND AND NAILS", "close_hand_right.png"),
    ("RIGHT HAND SIDE", "close_hand_right_side.png"),
    ("UPPER-LEG FORM", "close_upper_legs.png"),
)

SHEET_FILENAMES = {
    "overview": "BIOLOGICAL_ROBERT_V23_PROTECTED_OVERVIEW_CONTACT_SHEET.jpg",
    "details": "BIOLOGICAL_ROBERT_V23_PROTECTED_DETAIL_CONTACT_SHEET.jpg",
    "manifest": "BIOLOGICAL_ROBERT_V23_CONTACT_SHEET_MANIFEST.json",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build private V23 overview and protected-detail contact sheets from "
            "an explicit candidate folder or private_review render folder."
        )
    )
    parser.add_argument(
        "folder",
        nargs="?",
        type=Path,
        help=(
            "Candidate folder containing private_review, or the private_review "
            "folder itself. Use instead of the named folder options."
        ),
    )
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--candidate-folder",
        type=Path,
        help="Candidate folder whose private_review child contains the renders.",
    )
    source_group.add_argument(
        "--render-folder",
        type=Path,
        help="Folder containing the named Blender review renders.",
    )
    parser.add_argument(
        "--output-folder",
        type=Path,
        help="Destination for the two sheets and manifest (default: render folder).",
    )
    parser.add_argument(
        "--status",
        default="AWAITING ROBERT STATIC LIKENESS REVIEW",
        help="Truthful candidate status printed on both sheets.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help=(
            "Build an explicitly INCOMPLETE engineering sheet from available "
            "renders. The normal owner-review build is strict."
        ),
    )
    return parser


def _resolve_folders(args: argparse.Namespace) -> tuple[Path, Path]:
    supplied = [
        value
        for value in (args.folder, args.candidate_folder, args.render_folder)
        if value is not None
    ]
    if len(supplied) != 1:
        raise SystemExit(
            "Provide exactly one positional folder, --candidate-folder, or "
            "--render-folder."
        )

    if args.candidate_folder is not None:
        candidate = args.candidate_folder.resolve()
        render_folder = candidate / "private_review"
    elif args.render_folder is not None:
        render_folder = args.render_folder.resolve()
        candidate = (
            render_folder.parent
            if render_folder.name.casefold() == "private_review"
            else render_folder
        )
    else:
        selected = args.folder.resolve()
        if (selected / "private_review").is_dir():
            candidate = selected
            render_folder = selected / "private_review"
        else:
            render_folder = selected
            candidate = (
                selected.parent
                if selected.name.casefold() == "private_review"
                else selected
            )

    if not render_folder.is_dir():
        raise SystemExit(f"Review render folder does not exist: {render_folder}")
    return candidate, render_folder


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        Path("C:/Windows/Fonts/arialbd.ttf") if bold else Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf") if bold else Path("C:/Windows/Fonts/segoeui.ttf"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _available_entries(
    render_folder: Path,
    specifications: Sequence[tuple[str, str]],
    *,
    allow_missing: bool,
) -> tuple[list[tuple[str, Path]], list[str]]:
    entries: list[tuple[str, Path]] = []
    missing: list[str] = []
    render_root = render_folder.resolve()

    for label, filename in specifications:
        # The filename comes from the fixed allowlist above. The containment
        # check prevents an accidental future traversal from including a
        # protected source photograph outside private_review.
        source = (render_folder / filename).resolve()
        if source.parent != render_root:
            raise SystemExit(f"Render path escaped the selected folder: {source}")
        if not source.is_file():
            missing.append(filename)
            continue
        entries.append((label, source))

    if missing and not allow_missing:
        missing_list = "\n  - ".join(missing)
        raise SystemExit(
            "Owner-review contact sheets require every requested render. Missing:\n"
            f"  - {missing_list}\n"
            "Render the missing views, or use --allow-missing only for an "
            "explicitly incomplete engineering sheet."
        )
    if not entries:
        raise SystemExit("No allowlisted V23 review renders were found.")
    return entries, missing


def _draw_centered(
    draw: ImageDraw.ImageDraw,
    bounds: tuple[int, int, int, int],
    text: str,
    *,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> None:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    width, height = right - left, bottom - top
    x = bounds[0] + (bounds[2] - bounds[0] - width) // 2
    y = bounds[1] + (bounds[3] - bounds[1] - height) // 2
    draw.text((x, y), text, font=font, fill=fill)


def _build_sheet(
    destination: Path,
    *,
    heading: str,
    entries: Sequence[tuple[str, Path]],
    status: str,
    missing: Iterable[str],
    columns: int,
) -> dict[str, object]:
    cell_width = 620
    cell_height = 835
    header_height = 156
    footer_height = 84
    rows = (len(entries) + columns - 1) // columns
    canvas = Image.new(
        "RGB",
        (columns * cell_width, header_height + rows * cell_height + footer_height),
        (20, 23, 30),
    )
    draw = ImageDraw.Draw(canvas)
    title_font = _font(29, bold=True)
    label_font = _font(20, bold=True)
    status_font = _font(17, bold=True)
    footer_font = _font(16)

    _draw_centered(
        draw,
        (30, 18, canvas.width - 30, 70),
        heading,
        font=title_font,
        fill=(245, 246, 250),
    )
    incomplete = bool(tuple(missing))
    displayed_status = (
        f"INCOMPLETE ENGINEERING SHEET — {status}" if incomplete else status
    )
    _draw_centered(
        draw,
        (30, 76, canvas.width - 30, 125),
        displayed_status,
        font=status_font,
        fill=(255, 160, 92) if incomplete else (95, 210, 232),
    )
    draw.line(
        (45, header_height - 14, canvas.width - 45, header_height - 14),
        fill=(65, 123, 149),
        width=2,
    )

    source_records: list[dict[str, object]] = []
    for index, (label, source) in enumerate(entries):
        row, column = divmod(index, columns)
        x = column * cell_width
        y = header_height + row * cell_height
        _draw_centered(
            draw,
            (x + 15, y + 8, x + cell_width - 15, y + 48),
            label,
            font=label_font,
            fill=(240, 202, 112),
        )
        with Image.open(source) as opened:
            image = opened.convert("RGB")
            original_size = image.size
            image.thumbnail(
                (cell_width - 44, cell_height - 82), Image.Resampling.LANCZOS
            )
        image_x = x + (cell_width - image.width) // 2
        image_y = y + 58 + (cell_height - 72 - image.height) // 2
        canvas.paste(image, (image_x, image_y))
        draw.rectangle(
            (
                image_x - 1,
                image_y - 1,
                image_x + image.width,
                image_y + image.height,
            ),
            outline=(69, 74, 86),
            width=1,
        )
        source_records.append(
            {
                "label": label,
                "filename": source.name,
                "dimensions": list(original_size),
                "sha256": _sha256(source),
            }
        )

    footer_top = canvas.height - footer_height
    draw.line(
        (45, footer_top, canvas.width - 45, footer_top),
        fill=(65, 123, 149),
        width=2,
    )
    _draw_centered(
        draw,
        (30, footer_top + 8, canvas.width - 30, canvas.height - 9),
        "PRIVATE LOCAL REVIEW • STATIC ONLY • NOT APPROVED • NO RUNTIME OR ACTIVATION",
        font=footer_font,
        fill=(205, 209, 219),
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, quality=95, subsampling=0, optimize=True)
    return {
        "output_filename": destination.name,
        "output_sha256": _sha256(destination),
        "output_dimensions": list(canvas.size),
        "source_renders": source_records,
    }


def main() -> None:
    args = _parser().parse_args()
    candidate, render_folder = _resolve_folders(args)
    output_folder = (
        args.output_folder.resolve() if args.output_folder else render_folder
    )
    output_folder.mkdir(parents=True, exist_ok=True)

    overview_entries, overview_missing = _available_entries(
        render_folder, OVERVIEW_RENDERS, allow_missing=args.allow_missing
    )
    detail_entries, detail_missing = _available_entries(
        render_folder, PROTECTED_DETAIL_RENDERS, allow_missing=args.allow_missing
    )

    overview_record = _build_sheet(
        output_folder / SHEET_FILENAMES["overview"],
        heading="BIOLOGICAL ROBERT — V23 PROTECTED STATIC OVERVIEW",
        entries=overview_entries,
        status=args.status,
        missing=overview_missing,
        columns=3,
    )
    detail_record = _build_sheet(
        output_folder / SHEET_FILENAMES["details"],
        heading="BIOLOGICAL ROBERT — V23 PROTECTED STATIC DETAILS",
        entries=detail_entries,
        status=args.status,
        missing=detail_missing,
        columns=3,
    )

    manifest = {
        "schema": "kira.avatar.protected_static_contact_sheets.v1",
        "version": "V23",
        "candidate_folder": str(candidate),
        "render_folder": str(render_folder),
        "output_folder": str(output_folder),
        "status": args.status,
        "private_local_only": True,
        "static_only": True,
        "approved": False,
        "source_reference_photos_embedded": False,
        "input_policy": (
            "Only the fixed allowlist of Blender-produced review-render filenames "
            "is consumed; protected source photographs are neither discovered nor "
            "embedded."
        ),
        "complete": not (overview_missing or detail_missing),
        "missing_renders": overview_missing + detail_missing,
        "sheets": {
            "overview": overview_record,
            "protected_details": detail_record,
        },
    }
    manifest_path = output_folder / SHEET_FILENAMES["manifest"]
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(overview_record["output_filename"])
    print(detail_record["output_filename"])
    print(manifest_path.name)


if __name__ == "__main__":
    main()
