"""Evaluate or queue exact-hash multiview Avatar Builder evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_multiview_authoring import (  # noqa: E402
    AvatarMultiviewError,
    canonical_json_bytes,
    evaluate_multiview_manifest,
    queue_multiview_authoring_manifest,
)


def _common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--candidate-id", default="")
    parser.add_argument("--subject-id", default="")
    parser.add_argument("--topology-lane", default="")
    parser.add_argument("--expected-manifest-sha256", default="")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify reviewed multiview images, calibration, landmarks, scale, "
            "and base-body bindings without generating or activating a body."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    evaluate_parser = subparsers.add_parser("evaluate")
    _common_arguments(evaluate_parser)
    evaluate_parser.add_argument("--write", type=Path)
    queue_parser = subparsers.add_parser("queue")
    _common_arguments(queue_parser)
    args = parser.parse_args()

    kwargs = {
        "expected_candidate_id": args.candidate_id,
        "expected_subject_id": args.subject_id,
        "expected_topology_lane": args.topology_lane,
        "expected_manifest_sha256": args.expected_manifest_sha256,
    }
    try:
        if args.command == "evaluate":
            result = evaluate_multiview_manifest(
                PROJECT_ROOT, args.manifest, **kwargs
            )
            if args.write:
                output = args.write
                if not output.is_absolute():
                    output = PROJECT_ROOT / output
                output = output.resolve()
                try:
                    output.relative_to(PROJECT_ROOT.resolve())
                except ValueError as exc:
                    raise AvatarMultiviewError(
                        "evaluation output must stay inside the project"
                    ) from exc
                output.parent.mkdir(parents=True, exist_ok=True)
                encoded = canonical_json_bytes(result) + b"\n"
                try:
                    with output.open("xb") as handle:
                        handle.write(encoded)
                except FileExistsError:
                    if output.is_symlink() or output.read_bytes() != encoded:
                        raise AvatarMultiviewError(
                            "evaluation output already contains different content"
                        )
            print(json.dumps(result, indent=2))
            return 0 if result["authoring_queue_ready"] else 6
        result = queue_multiview_authoring_manifest(
            PROJECT_ROOT, args.manifest, **kwargs
        )
        print(json.dumps(result, indent=2))
        return 0
    except (AvatarMultiviewError, FileNotFoundError, OSError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}), file=sys.stderr)
        return 6


if __name__ == "__main__":
    raise SystemExit(main())
