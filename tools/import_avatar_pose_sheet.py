"""Split a reviewed 3x2 full-body pose sheet into TemporaryAI motion frames."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_living_portrait import (  # noqa: E402
    POSE_ORDER,
    avatar_body_root,
    ensure_avatar_body_manifest,
)
from tools.temporary_ai_live_chat import load_candidate  # noqa: E402


def remove_green_screen(image: Image.Image) -> Image.Image:
    """Remove a bright green generation background while preserving edge softness."""
    rgba = image.convert("RGBA")
    cleaned = []
    pixels = (
        rgba.get_flattened_data()
        if hasattr(rgba, "get_flattened_data")
        else rgba.getdata()
    )
    for red, green, blue, alpha in pixels:
        dominance = green - max(red, blue)
        if green >= 170 and dominance >= 55:
            key_alpha = max(0, 255 - min(255, (dominance - 40) * 4))
            cleaned.append((red, green, blue, min(alpha, key_alpha)))
        else:
            cleaned.append((red, green, blue, alpha))
    rgba.putdata(cleaned)
    return rgba


def import_pose_sheet(candidate_id: str, form: str, source: Path) -> list[Path]:
    candidate = load_candidate(candidate_id)
    profile = candidate.get("profile", {}) or {}
    allowed_forms = {
        str(item.get("id") or item.get("label", "")).lower()
        for item in (profile.get("visual_identity", {}) or {}).get("forms", [])
        if isinstance(item, dict)
    }
    normalized_form = form.strip().lower()
    if allowed_forms and normalized_form not in allowed_forms:
        raise ValueError(
            f"Form {normalized_form!r} is not declared for {candidate_id}. "
            f"Choose one of: {', '.join(sorted(allowed_forms))}"
        )
    if not source.exists():
        raise FileNotFoundError(source)

    sheet = Image.open(source).convert("RGBA")
    cell_width = sheet.width // 3
    cell_height = sheet.height // 2
    if cell_width < 120 or cell_height < 180:
        raise ValueError("Pose sheet must be a 3-column by 2-row full-body image.")

    form_dir = avatar_body_root(candidate_id) / normalized_form
    form_dir.mkdir(parents=True, exist_ok=True)
    copied_sheet = form_dir / "pose_sheet_source.png"
    sheet.save(copied_sheet)
    created: list[Path] = []
    for index, pose in enumerate(POSE_ORDER):
        row, column = divmod(index, 3)
        left = column * cell_width
        top = row * cell_height
        right = sheet.width if column == 2 else left + cell_width
        bottom = sheet.height if row == 1 else top + cell_height
        output = form_dir / f"{pose}.png"
        frame = remove_green_screen(sheet.crop((left, top, right, bottom)))
        frame.save(output)
        created.append(output)

    ensure_avatar_body_manifest(candidate_id, profile)
    return created


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_id")
    parser.add_argument("form", choices=("civilian", "hero", "default"))
    parser.add_argument("pose_sheet", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    created = import_pose_sheet(args.candidate_id, args.form, args.pose_sheet.resolve())
    print(f"Imported {len(created)} pose frames into {created[0].parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
