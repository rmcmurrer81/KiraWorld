"""
Plan or apply clean deterministic names for avatar reference files.

The default mode only writes a plan. Use --apply to perform the renames.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AVATAR_ROOT = PROJECT_ROOT / "Avatar"
DEFAULT_OUTPUT = PROJECT_ROOT / "Data" / "indexes" / "avatar_reference_rename_plan.json"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}

RENAME_TARGETS = {
    "Avatar/library/female/body": "female_body_reference",
    "Avatar/library/female/face_structure": "female_face_structure_reference",
    "Avatar/library/shared_features/eyes": "shared_eye_reference",
    "Avatar/library/shared_features/hair": "shared_hair_reference",
    "Avatar/library/shared_features/nose": "shared_nose_reference",
}


def _relative(path: Path, base: Path | None = None) -> str:
    if base is None:
        base = PROJECT_ROOT
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _next_available(path: Path, reserved: set[Path]) -> Path:
    if path not in reserved and not path.exists():
        reserved.add(path)
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem}_dup{counter}{suffix}")
        if candidate not in reserved and not candidate.exists():
            reserved.add(candidate)
            return candidate
        counter += 1


def build_plan(avatar_root: Path = DEFAULT_AVATAR_ROOT) -> dict[str, Any]:
    renames: list[dict[str, Any]] = []
    reserved: set[Path] = set()

    for relative_folder, prefix in RENAME_TARGETS.items():
        folder = PROJECT_ROOT / relative_folder
        if not folder.exists():
            continue
        files = [path for path in sorted(folder.iterdir()) if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS]
        for index, path in enumerate(files, start=1):
            target_name = f"{prefix}_{index:03d}{path.suffix.lower()}"
            target = _next_available(path.with_name(target_name), reserved)
            if path.name == target.name:
                action = "keep"
            else:
                action = "rename"
            renames.append(
                {
                    "action": action,
                    "old_path": _relative(path),
                    "new_path": _relative(target),
                    "reason": "Clean deterministic avatar reference name for feature selection.",
                }
            )

    return {
        "plan_id": "avatar_reference_rename_plan_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "avatar_root": _relative(avatar_root),
        "rename_count": sum(1 for item in renames if item["action"] == "rename"),
        "keep_count": sum(1 for item in renames if item["action"] == "keep"),
        "rules": {
            "content_not_analyzed": True,
            "uses_folder_category_not_person_identity": True,
            "does_not_clone_a_single_person": True,
            "does_not_change_privacy_rules": True,
        },
        "renames": renames,
    }


def apply_plan(plan: dict[str, Any]) -> None:
    allowed_roots = [
        (PROJECT_ROOT / "Avatar" / "library" / "female").resolve(),
        (PROJECT_ROOT / "Avatar" / "library" / "shared_features").resolve(),
    ]
    for item in plan["renames"]:
        if item["action"] != "rename":
            continue
        source = (PROJECT_ROOT / item["old_path"]).resolve()
        target = (PROJECT_ROOT / item["new_path"]).resolve()
        if not any(_within(source, root) and _within(target, root) for root in allowed_roots):
            raise RuntimeError(f"Refusing rename outside avatar reference roots: {source} -> {target}")
        if not source.exists():
            raise RuntimeError(f"Source missing: {source}")
        if target.exists():
            raise RuntimeError(f"Target already exists: {target}")
        source.rename(target)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan or apply clean avatar reference filenames.")
    parser.add_argument("--avatar-root", default=str(DEFAULT_AVATAR_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--apply", action="store_true", help="Apply the planned renames after writing the plan.")
    args = parser.parse_args()

    avatar_root = Path(args.avatar_root)
    if not avatar_root.is_absolute():
        avatar_root = PROJECT_ROOT / avatar_root
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output

    plan = build_plan(avatar_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.apply:
        apply_plan(plan)
        print(f"Applied {plan['rename_count']} avatar reference renames.")
    else:
        print(f"Planned {plan['rename_count']} avatar reference renames.")
    print(f"Wrote {_relative(output)}")


if __name__ == "__main__":
    main()
