"""Plan, queue, or process immutable Avatar Builder component production."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_component_production import (
    AvatarProductionError,
    canonical_json_bytes,
    plan_orchestration_request,
    process_queue,
    queue_production_request,
    sha256_file,
)
from Core.avatar_profile_preflight import (
    evaluate_orchestration_identity_preflight,
    identity_registry_available,
)
from Core.avatar_multiview_authoring import evaluate_multiview_manifest


def _json_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise AvatarProductionError("request must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Immutable, inactive separated-component production queue."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--orchestration-request", type=Path, required=True)
    plan_parser.add_argument(
        "--multiview-manifest",
        type=Path,
        help=(
            "Optional private evidence manifest. When omitted, the planner uses "
            "the request's multiview_authoring binding if present."
        ),
    )
    plan_parser.add_argument("--write", type=Path)
    queue_parser = subparsers.add_parser("queue")
    queue_parser.add_argument("--production-request", type=Path, required=True)
    process_parser = subparsers.add_parser("process")
    process_parser.add_argument("--max-jobs", type=int, default=4)
    args = parser.parse_args()

    try:
        if args.command == "plan":
            request_path = args.orchestration_request.resolve(strict=True)
            request = _json_object(request_path)
            identity_preflight = (
                evaluate_orchestration_identity_preflight(PROJECT_ROOT, request)
                if identity_registry_available(PROJECT_ROOT)
                else None
            )
            preliminary = plan_orchestration_request(
                request, identity_preflight=identity_preflight
            )
            binding = request.get("multiview_authoring")
            binding = binding if isinstance(binding, dict) else {}
            manifest_value = args.multiview_manifest or binding.get("manifest_path")
            multiview_evidence = None
            if manifest_value:
                multiview_evidence = evaluate_multiview_manifest(
                    PROJECT_ROOT,
                    Path(manifest_value),
                    expected_candidate_id=str(preliminary.get("candidate_id") or ""),
                    expected_subject_id=str(preliminary.get("subject_id") or ""),
                    expected_topology_lane=str(preliminary.get("topology_lane") or ""),
                    expected_manifest_sha256=str(
                        binding.get("manifest_sha256") or ""
                    ),
                )
            result = plan_orchestration_request(
                request,
                identity_preflight=identity_preflight,
                multiview_evidence=multiview_evidence,
            )
            if manifest_value and isinstance(result.get("multiview_authoring"), dict):
                manifest_path = Path(manifest_value)
                if not manifest_path.is_absolute():
                    manifest_path = PROJECT_ROOT / manifest_path
                manifest_path = manifest_path.resolve(strict=True)
                result["multiview_authoring"]["manifest_path"] = (
                    manifest_path.relative_to(PROJECT_ROOT.resolve()).as_posix()
                )
            result["orchestration_request_sha256"] = sha256_file(request_path)
            if args.write:
                output = args.write.resolve()
                output.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with output.open("xb") as handle:
                        handle.write(canonical_json_bytes(result) + b"\n")
                except FileExistsError:
                    if output.read_bytes() != canonical_json_bytes(result) + b"\n":
                        raise AvatarProductionError("plan output already exists with different content")
            print(json.dumps(result, indent=2))
            return 0 if result["authored_component_set_present"] else 6
        if args.command == "queue":
            result = queue_production_request(
                PROJECT_ROOT, args.production_request.resolve(strict=True)
            )
            print(json.dumps(result, indent=2))
            return 0
        results = process_queue(PROJECT_ROOT, max_jobs=args.max_jobs)
        print(json.dumps({"processed_count": len(results), "results": results}, indent=2))
        return 0
    except (AvatarProductionError, FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}), file=sys.stderr)
        return 6


if __name__ == "__main__":
    raise SystemExit(main())
