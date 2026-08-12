"""Create a photo-head reconstruction pack for one avatar candidate.

The pack is an assignment aid, not an approval. It gathers local reference
photos, preserves existing audit labels, makes a contact sheet, and records
which view slots are still missing before a head sculpt should claim likeness.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMP_AI_ROOT = PROJECT_ROOT / "Avatar" / "temp_ai"
PACK_ROOT = PROJECT_ROOT / "Avatar" / "avatar_builder" / "school" / "assignments" / "photo_head_reconstruction_packs"
ROUTING_ROOT = PROJECT_ROOT / "Avatar" / "avatar_builder" / "reference_routing"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return fallback


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def candidate_dir(candidate_id: str) -> Path:
    path = TEMP_AI_ROOT / candidate_id
    if not path.exists():
        raise SystemExit(f"Candidate not found: {path}")
    return path


def load_audit_map(root: Path) -> dict[str, dict[str, Any]]:
    audit_map: dict[str, dict[str, Any]] = {}
    for audit_path in root.glob("*reference_audit*.json"):
        audit = read_json(audit_path, {})
        for item in audit.get("items", []) or []:
            raw = item.get("path")
            if not raw:
                continue
            key = Path(raw).as_posix().lower()
            audit_map[key] = item
            audit_map[(PROJECT_ROOT / raw).as_posix().lower()] = item
    return audit_map


def load_route_overrides(candidate_id: str) -> list[dict[str, Any]]:
    overrides: list[dict[str, Any]] = []
    if not ROUTING_ROOT.exists():
        return overrides
    for path in sorted(ROUTING_ROOT.glob(f"{candidate_id}_photo_route_overrides*.json")):
        data = read_json(path, {})
        for item in data.get("records", []) or []:
            if isinstance(item, dict):
                item = {**item, "override_file": rel(path)}
                overrides.append(item)
    return overrides


def gather_images(root: Path) -> list[Path]:
    refs = root / "references"
    if not refs.exists():
        return []
    images = [path for path in refs.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTS]
    images.sort(key=lambda path: path.as_posix().lower())
    return images


def classify_slot(path: Path, audit: dict[str, Any] | None) -> str:
    if audit:
        label = str(audit.get("classification", "")).lower()
        reason = str(audit.get("reason", "")).lower()
        text = f"{label} {reason}"
        if "reject" in text:
            return "rejected"
        if "wardrobe" in text or "pose" in text:
            return "wardrobe_or_pose_only"
        if "cosplay" in text or "real person" in text or "voice actress" in text:
            return "wardrobe_or_style_only"
        if "profile" in text:
            return "profile_candidate"
        if "head" in text or "hair" in text or "face" in text:
            return "head_or_hair_candidate"
    name = path.stem.lower()
    if "profile" in name or "side" in name:
        return "profile_candidate"
    if "front" in name or "face" in name or "head" in name:
        return "head_or_hair_candidate"
    return "unclassified_needs_robert_slotting"


def match_override(path: Path, index: int, overrides: list[dict[str, Any]]) -> dict[str, Any] | None:
    name = path.name.lower()
    stem = path.stem.lower()
    rel_path = rel(path).lower()
    for item in overrides:
        try:
            match_index = int(item.get("match_index", -1))
        except (TypeError, ValueError):
            match_index = -1
        if match_index == index:
            return item
        basename = str(item.get("match_basename", "")).lower()
        if basename and basename in {name, stem}:
            return item
        contains = str(item.get("match_contains", "")).lower()
        if contains and contains in rel_path:
            return item
    return None


def classify_route(path: Path, audit: dict[str, Any] | None, slot_guess: str, override: dict[str, Any] | None) -> tuple[str, str]:
    if override:
        return str(override.get("route", "unclassified_needs_robert_slotting")), str(override.get("reason", "Robert/Codex route override."))
    text = f"{path.name} {slot_guess}".lower()
    if audit:
        text += " " + str(audit.get("classification", "")).lower()
        text += " " + str(audit.get("reason", "")).lower()
    if any(term in text for term in ["voice actress", "hailee", "steinfeld", "actor", "actress", "real person", "comic shop", "unrelated"]):
        return "reject_non_character_likeness", "Reject for likeness: not the animated target character."
    if any(term in text for term in ["cosplay", "cosplayer"]):
        return "wardrobe_or_style_only_not_likeness", "Cosplay may help wardrobe/style only; it cannot drive Gwen/character head or body likeness."
    if any(term in text for term in ["comic-cover", "comic cover", "cover art", "toy", "figure", "sponsored", "product"]):
        return "wardrobe_or_style_only_not_likeness", "Non-movie or product art may help wardrobe/style only after review."
    if any(term in text for term in ["bedroom", "background", "room", "house", "interior", "desk", "bed", "school hallway"]):
        return "world_builder_environment_reference", "Environment/background reference belongs to World Builder, not avatar head/body likeness."
    if slot_guess in {"head_or_hair_candidate", "profile_candidate"}:
        return "avatar_head_reconstruction_candidate", "Candidate head/photo reference; still requires Robert review and view-slot labeling."
    if slot_guess == "wardrobe_or_pose_only":
        return "wardrobe_reference_only", "Wardrobe/pose reference, not neutral head/body likeness."
    if slot_guess == "rejected":
        return "reject_non_character_likeness", "Rejected by audit or routing."
    return "unclassified_needs_robert_slotting", "Needs Robert/Codex routing before use."


def make_contact_sheet(records: list[dict[str, Any]], output_path: Path) -> str | None:
    thumbs = []
    for index, record in enumerate(records, start=1):
        src = PROJECT_ROOT / record["copied_file"]
        try:
            image = Image.open(src)
            image = ImageOps.exif_transpose(image).convert("RGB")
        except Exception:
            continue
        image.thumbnail((300, 220))
        canvas = Image.new("RGB", (320, 280), "white")
        x = (320 - image.width) // 2
        canvas.paste(image, (x, 10))
        draw = ImageDraw.Draw(canvas)
        draw.text((10, 235), f"{index}. {Path(record['source_file']).name}", fill=(0, 0, 0))
        draw.text((10, 252), record["slot_guess"][:42], fill=(80, 80, 80))
        thumbs.append(canvas)
    if not thumbs:
        return None
    cols = min(3, len(thumbs))
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 320, rows * 280), (235, 238, 240))
    for i, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((i % cols) * 320, (i // cols) * 280))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)
    return rel(output_path)


def build_pack(candidate_id: str) -> dict[str, Any]:
    root = candidate_dir(candidate_id)
    audit_map = load_audit_map(root)
    overrides = load_route_overrides(candidate_id)
    images = gather_images(root)
    pack_dir = PACK_ROOT / f"{candidate_id}_{now_id()}"
    image_dir = pack_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for index, image in enumerate(images, start=1):
        suffix = image.suffix.lower()
        copied = image_dir / f"{index:02d}_{image.stem}{suffix}"
        shutil.copy2(image, copied)
        key_options = [
            image.as_posix().lower(),
            rel(image).lower(),
            str(image).lower().replace("\\", "/"),
        ]
        audit = next((audit_map.get(key) for key in key_options if audit_map.get(key)), None)
        slot_guess = classify_slot(image, audit)
        override = match_override(image, index, overrides)
        route, route_reason = classify_route(image, audit, slot_guess, override)
        records.append(
            {
                "index": index,
                "source_file": rel(image),
                "copied_file": rel(copied),
                "slot_guess": slot_guess,
                "route": route,
                "route_reason": route_reason,
                "route_override_file": override.get("override_file") if override else None,
                "audit_classification": audit.get("classification") if audit else None,
                "audit_reason": audit.get("reason") if audit else None,
                "approved_for_head_reconstruction": route == "avatar_head_reconstruction_candidate",
                "approved_for_world_builder": route == "world_builder_environment_reference",
                "approved_for_wardrobe_builder": route in {"wardrobe_reference_only", "wardrobe_or_style_only_not_likeness"},
            }
        )

    slots = {
        "front_neutral_face": [],
        "left_profile": [],
        "right_profile": [],
        "three_quarter_front": [],
        "back_or_hair_silhouette": [],
        "mouth_open_or_smile": [],
    }
    for record in records:
        if not record["approved_for_head_reconstruction"]:
            continue
        if record["slot_guess"] == "head_or_hair_candidate":
            slots["front_neutral_face"].append(record["copied_file"])
            slots["three_quarter_front"].append(record["copied_file"])
            slots["back_or_hair_silhouette"].append(record["copied_file"])
        elif record["slot_guess"] == "profile_candidate":
            slots["left_profile"].append(record["copied_file"])
            slots["right_profile"].append(record["copied_file"])

    missing_slots = [slot for slot, values in slots.items() if not values]
    contact_sheet = make_contact_sheet(records, pack_dir / "reference_contact_sheet.jpg")
    pack = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "created_at": now_iso(),
        "status": "photo_head_reconstruction_pack_ready_for_slot_review",
        "pack_folder": rel(pack_dir),
        "contact_sheet": contact_sheet,
        "source_image_count": len(records),
        "usable_head_or_profile_count": sum(1 for record in records if record["approved_for_head_reconstruction"]),
        "world_builder_reference_count": sum(1 for record in records if record["approved_for_world_builder"]),
        "wardrobe_builder_reference_count": sum(1 for record in records if record["approved_for_wardrobe_builder"]),
        "route_overrides_loaded": sorted({record.get("override_file") for record in overrides if record.get("override_file")}),
        "records": records,
        "view_slots": slots,
        "missing_slots": missing_slots,
        "rule": "Photos drive head likeness only after route review; model assets teach topology, rigging, and motion only.",
        "routing_rule": "Environment/background photos go to World Builder; clothing/costume photos go to Wardrobe Builder; only clean character stills go to avatar head reconstruction.",
        "must_not_claim_pass_until_outputs_exist": [
            "candidate_head_mesh.glb",
            "candidate_head_on_generic_body.glb",
            "front_head_overlay.png",
            "left_profile_overlay.png",
            "right_profile_overlay.png",
            "three_quarter_overlay.png",
            "eyes_inside_socket_side_proof.png",
            "mouth_open_lip_sync_proof.png",
            "head_neck_rig_controls.json",
            "likeness_measurement_report.json",
        ],
    }
    write_json(pack_dir / "photo_head_reconstruction_pack.json", pack)
    return pack


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate_id")
    args = parser.parse_args()
    pack = build_pack(args.candidate_id)
    print(json.dumps(pack, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
