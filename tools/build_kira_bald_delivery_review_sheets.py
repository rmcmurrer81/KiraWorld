"""Build append-only private contact sheets from an exact Kira bald-body build."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROOT = (PROJECT_ROOT / "Avatar" / "private_owner_review").resolve()
OVERVIEW_NAME = "OWNER_REVIEW_OVERVIEW.png"
PROTECTED_NAME = "OWNER_REVIEW_PROTECTED.png"
ACTIVITY_NAME = "OWNER_REVIEW_ACTIVITY_FOUNDATIONS.png"
MANIFEST_NAME = "OWNER_REVIEW_SHEETS.json"


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", required=True)
    parser.add_argument("--acknowledge-private-owner-review", action="store_true")
    return parser.parse_args()


def resolve_candidate(raw: str) -> Path:
    candidate = (PROJECT_ROOT / Path(raw)).resolve(strict=True)
    if candidate.parent != ALLOWED_ROOT:
        raise ValueError("candidate must be a direct private_owner_review child")
    if not candidate.name.startswith("kira_profiled_adult_candidate_"):
        raise ValueError("unexpected candidate directory name")
    return candidate


def load_font(size: int) -> ImageFont.ImageFont:
    for path in (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
    ):
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def verified_rows(candidate: Path, evidence: dict[str, Any]) -> list[dict[str, Any]]:
    rows = list(evidence["owner_review"]["views"])
    if len(rows) != 23 or len({str(row["label"]) for row in rows}) != 23:
        raise ValueError("exact 23-view evidence is required")
    for row in rows:
        path = (candidate / str(row["path"])).resolve(strict=True)
        if path.parent != candidate or file_sha256(path) != str(row["sha256"]):
            raise ValueError(f"review render hash mismatch: {row['label']}")
    return rows


def verified_activity_rows(
    candidate: Path, evidence: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = list(evidence.get("supplemental_activity_review", {}).get("views") or [])
    if not rows:
        return []
    labels = {str(row.get("label") or "") for row in rows}
    required = {
        "lying_supine_side_contact",
        "lying_supine_top_contact",
        "eating_ready_seated_contact",
    }
    if labels != required or len(rows) != len(required):
        raise ValueError("exact three-view supplemental activity evidence is required")
    for row in rows:
        path = (candidate / str(row["path"])).resolve(strict=True)
        if path.parent != candidate or file_sha256(path) != str(row["sha256"]):
            raise ValueError(f"activity review render hash mismatch: {row['label']}")
    return rows


def build_sheet(
    *,
    candidate: Path,
    rows: Iterable[dict[str, Any]],
    output: Path,
    title: str,
    columns: int,
) -> dict[str, Any]:
    rows = list(rows)
    panel_width, panel_height = 390, 485
    header_height = 96
    row_count = (len(rows) + columns - 1) // columns
    canvas = Image.new(
        "RGB",
        (panel_width * columns, header_height + panel_height * row_count),
        (7, 12, 19),
    )
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(30)
    label_font = load_font(21)
    draw.text((24, 20), title, fill=(240, 220, 205), font=title_font)
    draw.text(
        (24, 58),
        "PRIVATE OWNER REVIEW ONLY - INACTIVE - NOT FOR PUBLICATION",
        fill=(235, 135, 105),
        font=load_font(17),
    )
    panels: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        column = index % columns
        row_index = index // columns
        left = column * panel_width
        top = header_height + row_index * panel_height
        source_path = candidate / str(row["path"])
        with Image.open(source_path) as source:
            source = ImageOps.exif_transpose(source).convert("RGB")
            fitted = ImageOps.contain(source, (360, 420), Image.Resampling.LANCZOS)
        image_left = left + (panel_width - fitted.width) // 2
        image_top = top + 38 + (420 - fitted.height) // 2
        canvas.paste(fitted, (image_left, image_top))
        label = str(row["label"]).replace("_", " ")
        draw.text((left + 14, top + 7), label, fill=(235, 235, 240), font=label_font)
        draw.rectangle(
            (left + 6, top + 2, left + panel_width - 7, top + panel_height - 7),
            outline=(58, 76, 96),
            width=2,
        )
        panels.append(
            {
                "label": str(row["label"]),
                "source_path": str(row["path"]),
                "source_sha256": str(row["sha256"]),
            }
        )
    canvas.save(output, format="PNG", optimize=True)
    return {
        "path": output.name,
        "sha256": file_sha256(output),
        "size_bytes": output.stat().st_size,
        "resolution_px": list(canvas.size),
        "panel_count": len(panels),
        "panels": panels,
    }


def main() -> int:
    args = arguments()
    if not args.acknowledge_private_owner_review:
        raise ValueError("--acknowledge-private-owner-review is required")
    candidate = resolve_candidate(args.candidate_dir)
    evidence_path = candidate / "BUILD_EVIDENCE.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
    if (
        evidence.get("candidate_asset_id") != "KIRA_BALD_LOW_RESOURCE_BODY"
        or evidence.get("status")
        != "INACTIVE_PRIVATE_COMPLETE_BODY_AWAITING_OWNER_VISUAL_DECISION"
    ):
        raise ValueError("candidate evidence is not the completed bald review body")
    activity_rows = verified_activity_rows(candidate, evidence)
    outputs = [candidate / OVERVIEW_NAME, candidate / PROTECTED_NAME, candidate / MANIFEST_NAME]
    if activity_rows:
        outputs.append(candidate / ACTIVITY_NAME)
    if any(path.exists() for path in outputs):
        raise FileExistsError("append-only review-sheet output already exists")
    rows = verified_rows(candidate, evidence)
    overview = build_sheet(
        candidate=candidate,
        rows=(row for row in rows if not bool(row["protected_view"])),
        output=candidate / OVERVIEW_NAME,
        title="KIRA BALD LOW-RESOURCE BODY - OWNER REVIEW OVERVIEW",
        columns=4,
    )
    protected = build_sheet(
        candidate=candidate,
        rows=(row for row in rows if bool(row["protected_view"])),
        output=candidate / PROTECTED_NAME,
        title="KIRA ADULT-SURFACE DETAIL - PROTECTED OWNER REVIEW",
        columns=3,
    )
    activity = None
    if activity_rows:
        activity = build_sheet(
            candidate=candidate,
            rows=activity_rows,
            output=candidate / ACTIVITY_NAME,
            title="KIRA STATIC HUMAN-ACTIVITY FOUNDATIONS - OWNER REVIEW",
            columns=3,
        )
    manifest = {
        "schema_version": 1,
        "artifact_type": "kira_bald_delivery_private_owner_review_sheets",
        "candidate_id": str(evidence["candidate_id"]),
        "candidate_asset_id": "KIRA_BALD_LOW_RESOURCE_BODY",
        "build_evidence": {
            "path": evidence_path.name,
            "sha256": file_sha256(evidence_path),
        },
        "overview": overview,
        "protected": protected,
        "activity_foundations": activity,
        "all_23_source_renders_hash_verified": True,
        "all_3_activity_source_renders_hash_verified": bool(activity_rows),
        "activity_foundations_are_static_not_full_animation_proof": bool(activity_rows),
        "private_owner_review_only": True,
        "runtime_activation_allowed": False,
        "publication_allowed": False,
    }
    manifest_path = candidate / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"manifest": str(manifest_path), **manifest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
