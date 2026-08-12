from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "Data" / "vision" / "image_reference_queue.json"
DEFAULT_SCAN_ROOTS = [
    PROJECT_ROOT / "Avatar",
    PROJECT_ROOT / "Data" / "library",
    PROJECT_ROOT / "Data" / "media",
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif", ".bmp", ".tif", ".tiff"}
SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "site-packages",
}
PRIVATE_HINTS = {
    "private",
    "adult",
    "erotic",
    "nude",
    "nudes",
    "naked",
    "breast",
    "breasts",
    "body",
}


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def classify_owner(path: Path) -> str:
    try:
        rel_parts = [part.lower() for part in path.relative_to(PROJECT_ROOT).parts]
    except ValueError:
        rel_parts = [part.lower() for part in path.parts]
    if rel_parts and rel_parts[0] == "avatar":
        if len(rel_parts) > 1 and rel_parts[1] == "kira":
            return "kira"
        if len(rel_parts) > 1 and rel_parts[1] == "lisa":
            return "lisa"
        if len(rel_parts) > 1 and rel_parts[1] in {"user", "robert"}:
            return "robert"
        return "avatar_reference_library"
    if rel_parts and rel_parts[0:2] == ["data", "media"]:
        return "media_library"
    if rel_parts and rel_parts[0:2] == ["data", "library"]:
        return "source_library"
    return "unknown"


def classify_purpose(path: Path) -> str:
    lower_path = rel(path).lower()
    if "face_structure" in lower_path or "/face/" in lower_path:
        return "face_reference"
    if "/hair/" in lower_path or "hair" in lower_path:
        return "hair_reference"
    if "/eyes/" in lower_path or "eye" in lower_path:
        return "eye_reference"
    if "/outfit" in lower_path or "fashion" in lower_path or "clothing" in lower_path:
        return "style_or_outfit_reference"
    if "body" in lower_path or "proportion" in lower_path:
        return "body_or_proportion_reference"
    if "/covers/" in lower_path or "cover" in lower_path:
        return "media_cover_or_source_image"
    return "general_image_reference"


def sensitivity(path: Path) -> str:
    lower = rel(path).lower()
    if any(hint in lower for hint in PRIVATE_HINTS):
        return "review_private"
    return "standard_review"


def iter_images(roots: list[Path]) -> list[Path]:
    images: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            if any(part in SKIP_DIR_NAMES for part in path.parts):
                continue
            images.append(path)
    return images


def build_queue(roots: list[Path]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for path in iter_images(roots):
        stat = path.stat()
        owner = classify_owner(path)
        purpose = classify_purpose(path)
        entry_sensitivity = sensitivity(path)
        entries.append(
            {
                "path": rel(path),
                "name": path.name,
                "extension": path.suffix.lower(),
                "owner_scope": owner,
                "reference_purpose": purpose,
                "sensitivity": entry_sensitivity,
                "status": "queued_for_optional_visual_review",
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "policy": {
                    "content_not_analyzed_by_this_tool": True,
                    "does_not_create_memory": True,
                    "does_not_create_avatar_choice": True,
                    "private_or_body_reference_requires_owner_review": entry_sensitivity == "review_private",
                    "kira_or_lisa_may_react_but_not_claim_lived_experience": True,
                },
            }
        )
    return {
        "queue_id": "image_reference_queue_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scan_roots": [rel(root) for root in roots],
        "entry_count": len(entries),
        "policy": {
            "purpose": "List image references that Kira/Lisa may eventually view or discuss after explicit review.",
            "not_memory": True,
            "not_avatar_selection": True,
            "content_not_opened_or_analyzed": True,
        },
        "entries": entries,
    }


def resolve_paths(paths: list[str]) -> list[Path]:
    roots: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        roots.append(path)
    return roots


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a lightweight image/reference review queue without opening image contents.")
    parser.add_argument("--roots", nargs="*", default=[], help="Optional roots to scan. Defaults to Avatar, Data/library, and Data/media.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    roots = resolve_paths(args.roots) if args.roots else DEFAULT_SCAN_ROOTS
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    queue = build_queue(roots)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": rel(output), "entries": queue["entry_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
