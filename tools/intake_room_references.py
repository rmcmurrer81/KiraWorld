"""Create a traceable room-reconstruction intake from user-provided images."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_size(path: Path) -> tuple[int | None, int | None]:
    try:
        from PIL import Image

        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except Exception:
        return None, None


def intake(source: Path, room_id: str) -> dict:
    room_root = PROJECT_ROOT / "Avatar" / "rooms" / room_id
    references_root = room_root / "references"
    references_root.mkdir(parents=True, exist_ok=True)
    records = []
    seen = set()
    for image in sorted(source.rglob("*")):
        if not image.is_file() or image.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        digest = sha256(image)
        if digest in seen:
            continue
        seen.add(digest)
        target = references_root / f"room_reference_{len(records) + 1:03d}_{digest[:10]}{image.suffix.lower()}"
        if not target.exists():
            shutil.copy2(image, target)
        width, height = image_size(target)
        records.append({
            "source_file": str(image),
            "local_file": str(target.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": digest,
            "width": width,
            "height": height,
            "review": {
                "camera_angle": "unclassified",
                "characters_present": "unknown",
                "use_for_geometry": "pending",
                "use_for_texture": "pending",
            },
        })

    now = datetime.now(timezone.utc).isoformat()
    manifest = {
        "schema_version": 1,
        "room_id": room_id,
        "updated_at": now,
        "status": "reference_intake_ready" if records else "no_images_found",
        "source_folder": str(source),
        "reference_count": len(records),
        "truth_note": "References were copied intact. Characters/backgrounds have not been removed and no panorama or 3D room has been claimed.",
        "references": records,
    }
    plan = {
        "schema_version": 1,
        "room_id": room_id,
        "updated_at": now,
        "status": "reference_review_needed",
        "target": "Marinette's bedroom in the future Paris World",
        "stages": [
            "Review and group images by camera angle and continuity version.",
            "Mask characters only on approved working copies; preserve all source images.",
            "Estimate camera positions and identify stable walls, windows, furniture, and doors.",
            "Build blockout geometry instead of attempting a visually inconsistent flat panorama stitch.",
            "Project or bake reviewed textures onto the room geometry.",
            "Add collision, walkable floor, chair/bed interaction points, and navigation paths.",
            "Add an interactive computer screen surface for later media playback, typing, and web tools.",
            "Place the finished room in the Paris World and connect it to the wider world navigation plan.",
        ],
        "interactive_anchors": {
            "computer_screen": ["future movie/show playback", "future typing", "future reviewed web search"],
            "desk_chair": ["sit", "read", "write", "computer activity"],
            "bed": ["sit", "rest", "sleepwear transition"],
        },
        "next_action": "Review the reference manifest and label camera angles and character-obstructed images before reconstruction.",
    }
    (room_root / "reference_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (room_root / "room_build_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return {"manifest": manifest, "plan": plan, "room_root": str(room_root)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", default=str(Path.home() / "Desktop" / "Marinette's Bedroom"))
    parser.add_argument("--room-id", default="marinette_bedroom")
    args = parser.parse_args()
    result = intake(Path(args.source), args.room_id)
    print(json.dumps({
        "status": result["manifest"]["status"],
        "reference_count": result["manifest"]["reference_count"],
        "room_root": result["room_root"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
