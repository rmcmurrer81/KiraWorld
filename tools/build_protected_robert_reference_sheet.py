"""Build an owner-only opaque-ID sheet for authorized local fitting review."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\Users\robmc\Desktop\robert avatar base")
MANIFEST = ROOT / "Avatar/outputs/user/BIOLOGICAL_ROBERT_AVATAR_REFERENCE_MANIFEST.json"
OUTPUT = ROOT / "Avatar/private_owner_review/dual_robert_20260729"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    by_hash = {
        digest(path): path
        for path in SOURCE.iterdir()
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    }
    entries = []
    for record in manifest["references"]:
        path = by_hash.get(record["sha256"])
        if path is None:
            raise RuntimeError(f"missing protected source for {record['opaque_reference_id']}")
        entries.append((record["opaque_reference_id"], path))

    OUTPUT.mkdir(parents=True, exist_ok=True)
    tile = (420, 420)
    columns = 4
    rows = (len(entries) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * tile[0], rows * tile[1]), "#181818")
    draw = ImageDraw.Draw(sheet)
    for index, (opaque_id, path) in enumerate(entries):
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((tile[0] - 24, tile[1] - 52), Image.Resampling.LANCZOS)
            x = (index % columns) * tile[0] + (tile[0] - image.width) // 2
            y = (index // columns) * tile[1] + 34
            sheet.paste(image, (x, y))
        draw.text(((index % columns) * tile[0] + 12, (index // columns) * tile[1] + 10), opaque_id, fill="white")
    path = OUTPUT / "PROTECTED_REFERENCE_SHEET.jpg"
    sheet.save(path, quality=88)
    access = {
        "classification": "PROTECTED REFERENCE AND LANDMARK REVIEW",
        "authorized_targets": ["BIOLOGICAL_ROBERT_AVATAR", "SYNTHETIC_ROBERT_TWIN_BODY"],
        "ordinary_handoff_allowed": False,
        "public_export_allowed": False,
        "source_filenames_recorded": False,
        "source_paths_recorded": False,
        "sheet_path": path.name,
        "sheet_sha256": digest(path),
    }
    (OUTPUT / "ACCESS_RECORD.json").write_text(
        json.dumps(access, indent=2) + "\n", encoding="utf-8"
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
