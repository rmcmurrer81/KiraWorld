"""Create a privacy-safe recovery checkpoint without copying source photos."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "Core/avatar_likeness_author_backend.py",
    "Core/avatar_multiview_authoring.py",
    "Core/avatar_body_topology.py",
    "Core/wearable_component_contract.py",
    "Core/dual_robert_avatar_authority.py",
    "tools/avatar_likeness_author_backend.py",
    "tools/avatar_multiview_authoring_queue.py",
    "Avatar/outputs/user/BIOLOGICAL_ROBERT_AVATAR_REFERENCE_MANIFEST.json",
    "Avatar/outputs/user/SYNTHETIC_ROBERT_TWIN_BODY_REFERENCE_MANIFEST.json",
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output = ROOT / "Avatar" / "backups" / f"dual_robert_prebuild_{stamp}"
    inventory = []
    for relative in FILES:
        source = ROOT / relative
        if not source.is_file():
            inventory.append({"project_path": relative, "status": "missing"})
            continue
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        inventory.append(
            {
                "project_path": relative,
                "sha256": digest(source),
                "backup_sha256": digest(target),
                "bytes": source.stat().st_size,
                "status": "backed_up",
            }
        )
    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "checkpoint": "dual_robert_avatar_prebuild",
        "private_source_images_copied": False,
        "private_source_paths_or_filenames_recorded": False,
        "targets": ["BIOLOGICAL_ROBERT_AVATAR", "SYNTHETIC_ROBERT_TWIN_BODY"],
        "files": inventory,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "CHECKPOINT.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(output)
    print(f"files={len(inventory)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
