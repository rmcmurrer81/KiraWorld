"""
Build a persistence manifest for remote phone/app update checks.

The manifest tracks remote contact and private media records that must survive
future app, bridge, or storage migrations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PERSISTENT_ROOTS = [
    Path("Data/remote_contact"),
    Path("Data/private_media"),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json_summary(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    summary: dict[str, Any] = {}
    for key in (
        "event_id",
        "policy_id",
        "initiator",
        "recipient",
        "channel",
        "delivery_state",
        "response_state",
        "status",
    ):
        if key in data:
            summary[key] = data[key]
    if "privacy_context" in data and isinstance(data["privacy_context"], dict):
        summary["exact_private_content_blocked"] = data["privacy_context"].get("exact_private_content_blocked")
    if "access_and_scope" in data and isinstance(data["access_and_scope"], dict):
        summary["access_and_scope"] = data["access_and_scope"]
    return summary


def persistent_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for relative_root in PERSISTENT_ROOTS:
        base = root / relative_root
        if not base.exists():
            continue
        files.extend(path for path in base.rglob("*") if path.is_file())
    return sorted(files)


def build_persistence_manifest(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    root = root.resolve()
    entries = []
    total_bytes = 0
    for path in persistent_files(root):
        relative = str(path.relative_to(root)).replace("\\", "/")
        size = path.stat().st_size
        total_bytes += size
        entries.append(
            {
                "path": relative,
                "size_bytes": size,
                "sha256": sha256_file(path),
                "json_summary": load_json_summary(path) if path.suffix.lower() == ".json" else {},
            }
        )
    return {
        "manifest_type": "remote_phone_app_persistence",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(root),
        "persistent_roots": [str(path).replace("\\", "/") for path in PERSISTENT_ROOTS],
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "files": entries,
    }


def compare_manifests(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    before_files = {item["path"]: item for item in before.get("files", [])}
    after_files = {item["path"]: item for item in after.get("files", [])}
    problems: list[str] = []

    for path, before_item in sorted(before_files.items()):
        after_item = after_files.get(path)
        if after_item is None:
            problems.append(f"Missing persistent file after update: {path}")
            continue
        if before_item.get("sha256") != after_item.get("sha256"):
            problems.append(f"Changed persistent file after update: {path}")

    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or compare remote phone persistence manifests.")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare-before", type=Path)
    parser.add_argument("--compare-after", type=Path)
    args = parser.parse_args()

    if args.compare_before and args.compare_after:
        before = json.loads(args.compare_before.read_text(encoding="utf-8"))
        after = json.loads(args.compare_after.read_text(encoding="utf-8"))
        problems = compare_manifests(before, after)
        if problems:
            print("Persistence check failed:")
            for problem in problems:
                print(f"- {problem}")
            raise SystemExit(1)
        print("Persistence check passed: all tracked remote phone/media records are preserved.")
        return

    manifest = build_persistence_manifest(args.root)
    text = json.dumps(manifest, indent=2) + "\n"
    if args.output:
        output = args.output
        if not output.is_absolute():
            output = args.root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(f"Wrote remote phone persistence manifest: {output}")
        print(f"Persistent files: {manifest['file_count']}")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
