"""Copy Robert-reviewed avatar downloads into candidate reference intake folders.

The desktop folder remains an inbox. This tool never deletes or rewrites those
files; it hashes and copies them so later segmentation, identity review, outfit
grouping, and 3D reconstruction can be repeated safely.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = PROJECT_ROOT / "TemporaryAI" / "candidates"
AVATAR_ROOT = PROJECT_ROOT / "Avatar" / "temp_ai"
INTAKE_ROOT = PROJECT_ROOT / "Avatar" / "reference_intake"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return value or "unknown"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def candidate_index() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for folder in CANDIDATE_ROOT.iterdir() if CANDIDATE_ROOT.exists() else []:
        if not folder.is_dir():
            continue
        profile_path = folder / "temporary_ai_profile.json"
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            profile = {}
        display = str(profile.get("display_name") or folder.name)
        role = str(profile.get("role_title") or "")
        rows.append(
            {
                "candidate_id": folder.name,
                "display_name": display,
                "role": role,
                "search": " ".join((folder.name, display, role)).lower(),
            }
        )
    return rows


def match_candidate(folder_name: str, candidates: list[dict[str, str]]) -> dict[str, str] | None:
    query = slug(folder_name)
    tokens = {item for item in query.split("_") if len(item) > 2}
    aliases = {
        "kara": "kara_zor_el_my_adventures_with_superman",
        "cameron": "cameron_terminator",
        "kathryn_merteuil": "kathryn_merteuil",
        "marinette": "ladybug_marinette",
        "ladybug": "ladybug_marinette",
    }
    alias = aliases.get(query, query)
    ranked: list[tuple[int, dict[str, str]]] = []
    for candidate in candidates:
        searchable = slug(candidate["search"])
        score = 0
        if alias in searchable:
            score += 50
        score += 8 * sum(token in searchable for token in tokens)
        if query == slug(candidate["display_name"]):
            score += 100
        if score:
            ranked.append((score, candidate))
    ranked.sort(key=lambda item: (-item[0], item[1]["candidate_id"]))
    return ranked[0][1] if ranked else None


def infer_form(path: Path) -> str:
    text = slug(path.stem)
    groups = (
        ("sleepwear", ("pajama", "pyjama", "sleep", "nightgown", "robe", "pj")),
        ("hero", ("hero", "ladybug", "supergirl", "armor", "armour", "costume", "suit", "terminator")),
        ("formal", ("formal", "gown", "tux", "evening", "premiere", "red_carpet")),
        ("civilian", ("civilian", "casual", "school", "jeans", "shirt", "dress", "coat", "jacket")),
    )
    for form, terms in groups:
        if any(term in text for term in terms):
            return form
    return "unclassified"


def infer_view(path: Path) -> str:
    text = slug(path.stem)
    groups = (
        ("full_body_front", ("full_body_front", "full_front", "standing_front")),
        ("full_body_side", ("full_body_side", "standing_side")),
        ("head_front", ("head_front", "face_front", "portrait_front")),
        ("head_profile", ("profile", "head_side", "face_side")),
        ("back", ("back", "rear")),
        ("three_quarter", ("three_quarter", "3_4", "threequarter")),
        ("full_body", ("full_body", "standing", "body")),
        ("portrait", ("portrait", "headshot", "face")),
    )
    for view, terms in groups:
        if any(term in text for term in terms):
            return view
    return "unclassified"


def image_metadata(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        return {
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "format": image.format,
        }


def unique_copy(source: Path, destination: Path, digest: str) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"{slug(source.stem)}_{digest[:10]}{source.suffix.lower()}"
    if not target.exists():
        shutil.copy2(source, target)
    return target


def write_outfit_catalog(candidate_id: str, items: list[dict[str, Any]]) -> Path:
    target = AVATAR_ROOT / candidate_id / "outfit_catalog.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    outfits: dict[str, list[str]] = {}
    for item in items:
        outfits.setdefault(item["suggested_form"], []).append(item["copied_file"])
    data = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "updated_at": now_iso(),
        "status": "needs_visual_review",
        "outfits": [
            {
                "id": form,
                "label": form.replace("_", " ").title(),
                "reference_files": sorted(files),
                "review_status": "needs_review",
            }
            for form, files in sorted(outfits.items())
        ],
        "truth_note": "Filename tags are suggestions only. A person must confirm identity, form, and clothing before avatar reconstruction.",
    }
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return target


def ingest(source_root: Path) -> dict[str, Any]:
    candidates = candidate_index()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_items: list[dict[str, Any]] = []
    unmatched: list[str] = []
    grouped: dict[str, list[dict[str, Any]]] = {}

    for source_folder in sorted((path for path in source_root.iterdir() if path.is_dir()), key=lambda p: p.name.lower()):
        candidate = match_candidate(source_folder.name, candidates)
        if not candidate:
            unmatched.append(str(source_folder))
            continue
        candidate_id = candidate["candidate_id"]
        intake_dir = AVATAR_ROOT / candidate_id / "references" / "desktop_intake" / timestamp / "originals"
        for source in sorted(source_folder.rglob("*")):
            if not source.is_file() or source.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            try:
                digest = sha256(source)
                metadata = image_metadata(source)
            except Exception as exc:
                run_items.append({"source_file": str(source), "candidate_id": candidate_id, "status": "read_failed", "error": str(exc)})
                continue
            copied = unique_copy(source, intake_dir, digest)
            item = {
                "candidate_id": candidate_id,
                "display_name": candidate["display_name"],
                "source_file": str(source.resolve()),
                "copied_file": rel(copied),
                "sha256": digest,
                "suggested_form": infer_form(source),
                "suggested_view": infer_view(source),
                "image": metadata,
                "identity_review_status": "needs_review",
                "multi_person_review_status": "needs_review",
                "background_removal_status": "pending_segmentation_tool",
                "status": "copied_for_review",
            }
            run_items.append(item)
            grouped.setdefault(candidate_id, []).append(item)

    catalogs = [rel(write_outfit_catalog(candidate_id, items)) for candidate_id, items in grouped.items()]
    report = {
        "schema_version": 1,
        "created_at": now_iso(),
        "source_root": str(source_root.resolve()),
        "source_files_modified": False,
        "items": run_items,
        "unmatched_folders": unmatched,
        "outfit_catalogs": catalogs,
        "next_steps": [
            "Review identity and exact character version.",
            "Mark images containing other people for subject isolation.",
            "Run a reviewed segmentation tool before reconstruction.",
            "Confirm outfit groups and reference angles.",
        ],
    }
    INTAKE_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = INTAKE_ROOT / f"avatar_reference_intake_{timestamp}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["report"] = rel(report_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=Path.home() / "Desktop" / "Downloads For Avatars",
        help="Folder containing one subfolder per person/character.",
    )
    args = parser.parse_args()
    if not args.source.exists():
        parser.error(f"Source folder does not exist: {args.source}")
    result = ingest(args.source)
    print(json.dumps({
        "report": result["report"],
        "copied": sum(item.get("status") == "copied_for_review" for item in result["items"]),
        "unmatched_folders": result["unmatched_folders"],
        "source_files_modified": result["source_files_modified"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
