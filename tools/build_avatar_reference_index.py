"""
Build a privacy-aware index of Avatar reference files.

This does not open or analyze image contents. It only records paths, names,
extensions, rough reference categories, and privacy/use policy.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AVATAR_ROOT = PROJECT_ROOT / "Avatar"
DEFAULT_OUTPUT = PROJECT_ROOT / "Data" / "indexes" / "avatar_reference_index.json"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
DOCUMENT_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".json"}
PRIVATE_BODY_TERMS = {
    "nude",
    "nudes",
    "naked",
    "breast",
    "breasts",
    "body",
    "bare",
    "chest",
    "tits",
    "erotic",
}
NOISY_NAME_TERMS = {
    "erotic",
    "perfect",
    "mainthumb",
    "bannerpic",
    "small-tits",
    "ai-models",
}
MULTISPACE_RE = re.compile(r"\s{2,}")


def _relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _file_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in DOCUMENT_EXTENSIONS:
        return "document"
    return "other"


def _category(path: Path, avatar_root: Path) -> str:
    parts = [part.lower() for part in path.relative_to(avatar_root).parts]
    joined = "/".join(parts)
    if "outfits" in parts:
        return "outfit_reference"
    if "face_structure" in parts:
        return "face_structure"
    if "eyes" in parts:
        return "eyes"
    if "hair" in parts:
        return "hair"
    if "nose" in parts:
        return "nose"
    if "breast_shape" in parts:
        return "body_shape_private"
    if "body" in parts or "proportions" in parts:
        return "body_or_proportion_private"
    if "voice" in parts:
        return "voice_reference"
    if "autobiography" in parts:
        return "autobiography_reference"
    if "items" in parts:
        return "life_item_reference"
    if "user/references" in joined:
        return "user_private_reference"
    return "general_avatar_reference"


def _owner_scope(path: Path, avatar_root: Path) -> str:
    parts = [part.lower() for part in path.relative_to(avatar_root).parts]
    if parts and parts[0] in {"kira", "lisa", "user"}:
        return parts[0]
    if "library" in parts:
        return "shared_reference_library"
    return "avatar_system"


def _sensitivity(path: Path, category: str, owner_scope: str) -> str:
    lower = path.name.lower()
    parts = {part.lower() for part in path.parts}
    has_private_term = any(term in lower for term in PRIVATE_BODY_TERMS)
    if owner_scope == "user":
        return "user_private"
    if "private" in category or "body" in category or "proportion" in category:
        return "private_body_reference"
    if has_private_term or {"body", "breast_shape"} & parts:
        return "private_body_reference"
    if category == "outfit_reference":
        return "style_reference"
    return "feature_reference"


def _issues(path: Path, sensitivity: str) -> list[str]:
    lower = path.name.lower()
    issues: list[str] = []
    if MULTISPACE_RE.search(path.name):
        issues.append("multiple_spaces")
    for term in sorted(NOISY_NAME_TERMS):
        if term in lower:
            issues.append(f"noisy_or_sexualized_filename:{term}")
    if sensitivity in {"private_body_reference", "user_private"}:
        issues.append("requires_private_reference_handling")
    return issues


def build_index(avatar_root: Path = DEFAULT_AVATAR_ROOT) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    counts_by_category: dict[str, int] = {}
    counts_by_sensitivity: dict[str, int] = {}

    for path in sorted(avatar_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | DOCUMENT_EXTENSIONS:
            continue
        category = _category(path, avatar_root)
        owner_scope = _owner_scope(path, avatar_root)
        sensitivity = _sensitivity(path, category, owner_scope)
        counts_by_category[category] = counts_by_category.get(category, 0) + 1
        counts_by_sensitivity[sensitivity] = counts_by_sensitivity.get(sensitivity, 0) + 1
        entries.append(
            {
                "path": _relative(path),
                "name": path.name,
                "extension": path.suffix.lower(),
                "file_type": _file_type(path),
                "category": category,
                "owner_scope": owner_scope,
                "sensitivity": sensitivity,
                "size_bytes": path.stat().st_size,
                "issues": _issues(path, sensitivity),
                "usage_policy": {
                    "owner_controls_visibility": True,
                    "may_be_used_for_public_exports": False,
                    "may_be_used_for_other_avatars": False,
                    "does_not_create_memory": True,
                    "does_not_create_avatar_automatically": True,
                    "requires_review_before_temp_ai_use": True,
                },
            }
        )

    return {
        "index_id": "avatar_reference_index_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "avatar_root": _relative(avatar_root),
        "entry_count": len(entries),
        "counts_by_category": dict(sorted(counts_by_category.items())),
        "counts_by_sensitivity": dict(sorted(counts_by_sensitivity.items())),
        "rules": {
            "content_not_analyzed": True,
            "private_body_references_are_owner_controlled": True,
            "references_do_not_create_avatar_automatically": True,
            "references_do_not_become_memory": True,
            "kira_lisa_final_choices_remain_theirs": True,
        },
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the avatar reference index.")
    parser.add_argument("--avatar-root", default=str(DEFAULT_AVATAR_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    avatar_root = Path(args.avatar_root)
    if not avatar_root.is_absolute():
        avatar_root = PROJECT_ROOT / avatar_root
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output

    index = build_index(avatar_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {index['entry_count']} avatar reference entries to {_relative(output)}")


if __name__ == "__main__":
    main()
