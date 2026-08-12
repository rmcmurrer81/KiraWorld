"""Refresh the Avatar Builder asset library from Robert's local model folders."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_asset_library import (  # noqa: E402
    build_avatar_asset_library,
    hair_trial_report_path,
    run_hair_style_trials,
    write_avatar_builder_learning_plans,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Update Avatar Builder reusable model assets.")
    parser.add_argument(
        "--source-root",
        action="append",
        type=Path,
        help="Optional source root. Can be passed more than once. Defaults to known Desktop folders.",
    )
    parser.add_argument(
        "--library-root",
        type=Path,
        default=None,
        help="Optional destination root. Defaults to Avatar/avatar_builder/asset_library.",
    )
    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="Scan and write metadata without copying models.",
    )
    args = parser.parse_args()

    manifest = build_avatar_asset_library(
        source_roots=args.source_root,
        library_root=args.library_root,
        copy_assets=not args.no_copy,
    )
    report = run_hair_style_trials(manifest)
    learning_plans = write_avatar_builder_learning_plans(manifest)
    print(json.dumps({
        "asset_count": manifest["asset_count"],
        "categories": manifest["categories"],
        "manifest": "Avatar/avatar_builder/asset_library/manifest.json",
        "hair_trials": str(hair_trial_report_path().relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "learning_plans": learning_plans,
        "hair_grades": {
            key: value["grade"]
            for key, value in report["trials"].items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()
