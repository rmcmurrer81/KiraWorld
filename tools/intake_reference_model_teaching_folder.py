"""Inventory and route a local 3D-model folder as teaching evidence only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.reference_model_teaching_intake import (  # noqa: E402
    build_intake_manifest,
    write_consumer_route_links,
    write_intake_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create a hash-bound, reference-only inventory for 3D models. "
            "This never copies or activates a model."
        )
    )
    parser.add_argument(
        "source_root",
        nargs="?",
        type=Path,
        default=Path.home() / "Desktop" / "91",
    )
    args = parser.parse_args()
    manifest = build_intake_manifest(args.source_root, project_root=PROJECT_ROOT)
    outputs = write_intake_outputs(manifest, project_root=PROJECT_ROOT)
    links = write_consumer_route_links(outputs, manifest, project_root=PROJECT_ROOT)
    print(
        json.dumps(
            {
                "status": "reference_only_intake_complete",
                "source_root": str(args.source_root.resolve()),
                "inventory_sha256": manifest["inventory_sha256"],
                "file_count": manifest["file_count"],
                "total_bytes": manifest["total_bytes"],
                "family_count": manifest["family_count"],
                "lane_counts": manifest["lane_counts"],
                "manifest": str(outputs.manifest),
                "avatar_route": str(outputs.avatar_route),
                "movement_route": str(outputs.movement_route),
                "world_route": str(outputs.world_route),
                "blocked_route": str(outputs.blocked_route),
                "avatar_consumer_link": str(links.avatar),
                "movement_consumer_link": str(links.movement),
                "world_consumer_link": str(links.world),
                "files_copied": False,
                "runtime_activation_allowed": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
