from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = PROJECT_ROOT / "Avatar" / "user" / "references"
OUTPUT_JSON = PROJECT_ROOT / "Avatar" / "outputs" / "user" / "robert_avatar_reference_inventory.json"
OUTPUT_MD = PROJECT_ROOT / "Avatar" / "outputs" / "user" / "robert_avatar_reference_inventory.md"

TARGETS = {
    "images/face": {"minimum": 7, "purpose": "front, side/profile, relaxed, and smiling face references"},
    "images/body_clothed": {"minimum": 2, "purpose": "clothed full-body proportion references"},
    "images/body_private": {"minimum": 0, "purpose": "optional owner-only private body references"},
    "video": {"minimum": 1, "purpose": "short movement/standing/walking reference"},
    "voice": {"minimum": 2, "purpose": "normal conversation and reading voice samples"},
    "style": {"minimum": 5, "purpose": "clothing/style examples Robert likes"},
    "items": {"minimum": 0, "purpose": "optional personal objects/world motifs"},
    "autobiography": {"minimum": 0, "purpose": "reviewed autobiography-derived notes, not raw bio ingestion"},
}

IGNORED_SUFFIXES = {".note.md", ".tmp"}


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def list_files(folder: Path) -> list[dict]:
    if not folder.exists():
        return []
    files = []
    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if any(path.name.endswith(suffix) for suffix in IGNORED_SUFFIXES):
            continue
        note = path.with_name(path.name + ".note.md")
        files.append(
            {
                "path": rel(path),
                "size_bytes": path.stat().st_size,
                "has_sidecar_note": note.exists(),
                "sidecar_note": rel(note) if note.exists() else "",
            }
        )
    return files


def build_inventory() -> dict:
    categories = {}
    for relative, target in TARGETS.items():
        folder = REFERENCE_ROOT / relative
        files = list_files(folder)
        minimum = int(target["minimum"])
        categories[relative] = {
            "folder": rel(folder),
            "purpose": target["purpose"],
            "minimum_recommended": minimum,
            "count": len(files),
            "complete_for_first_pass": len(files) >= minimum,
            "files": files,
        }
    missing = [
        {
            "category": name,
            "folder": data["folder"],
            "needed": max(0, int(data["minimum_recommended"]) - int(data["count"])),
            "purpose": data["purpose"],
        }
        for name, data in categories.items()
        if not data["complete_for_first_pass"]
    ]
    return {
        "inventory_id": "robert_avatar_reference_inventory",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reference_root": rel(REFERENCE_ROOT),
        "privacy_policy": {
            "owner_controlled": True,
            "not_loaded_into_kira_lisa": True,
            "private_body_reference_reuse_allowed": False,
            "approval_required_before_generation": True,
        },
        "categories": categories,
        "missing_for_first_pass": missing,
    }


def write_markdown(inventory: dict) -> None:
    lines = [
        "# Robert Avatar Reference Inventory",
        "",
        f"- created_at: {inventory['created_at']}",
        f"- reference_root: `{inventory['reference_root']}`",
        "",
        "## Missing For First Pass",
    ]
    missing = inventory.get("missing_for_first_pass", [])
    if not missing:
        lines.append("- First-pass reference minimums are met.")
    else:
        for item in missing:
            lines.append(f"- `{item['category']}`: needs {item['needed']} more; {item['purpose']}")
    lines.extend(["", "## Categories"])
    for name, data in inventory["categories"].items():
        status = "ok" if data["complete_for_first_pass"] else "needs more"
        lines.extend(
            [
                f"### {name}",
                f"- status: {status}",
                f"- folder: `{data['folder']}`",
                f"- count: {data['count']} / {data['minimum_recommended']}",
                f"- purpose: {data['purpose']}",
            ]
        )
        if data["files"]:
            for file_info in data["files"]:
                note = " note" if file_info["has_sidecar_note"] else ""
                lines.append(f"- `{file_info['path']}`{note}")
        else:
            lines.append("- No files yet.")
        lines.append("")
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    inventory = build_inventory()
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(inventory)
    print(json.dumps({"json": rel(OUTPUT_JSON), "markdown": rel(OUTPUT_MD), "missing": inventory["missing_for_first_pass"]}, indent=2))


if __name__ == "__main__":
    main()

