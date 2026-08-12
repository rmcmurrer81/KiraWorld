#!/usr/bin/env python3
"""Preflight and optionally execute the adult licensed-reference backend."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.adult_reference_avatar_backend import (  # noqa: E402
    finalize_adult_reference_candidate,
    run_blender_worker,
    validate_adult_reference_request,
    validate_adult_reference_request_file,
)


DEFAULT_BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Stage a licensed adult reference derivative. No render, public export, "
            "live-avatar write, or runtime activation is performed."
        )
    )
    parser.add_argument("request", help="Exact-hash build request JSON")
    parser.add_argument("--execute", action="store_true", help="Run the bounded Blender worker")
    parser.add_argument(
        "--confirm-life-loop-stopped",
        action="store_true",
        help="Required with --execute after separately checking Kira/life-loop processes",
    )
    parser.add_argument("--blender", default=str(DEFAULT_BLENDER))
    parser.add_argument("--timeout-seconds", type=int, default=300)
    args = parser.parse_args()

    request_path = Path(args.request).resolve()
    request = json.loads(request_path.read_text(encoding="utf-8"))
    gate = validate_adult_reference_request(request, project_root=PROJECT_ROOT)
    location_failures = validate_adult_reference_request_file(
        request_path, request, project_root=PROJECT_ROOT
    )
    if location_failures:
        gate["failures"] = list(dict.fromkeys([*gate["failures"], *location_failures]))
        gate["preflight_passed"] = False
        gate["status"] = "blocked"
    if not args.execute:
        print(json.dumps(gate, indent=2))
        return 0 if gate["preflight_passed"] else 2
    if not args.confirm_life_loop_stopped:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "failures": ["life_loop_stop_confirmation_required_before_blender"],
                    "runtime_activation_allowed": False,
                },
                indent=2,
            )
        )
        return 3
    if not gate["preflight_passed"]:
        print(json.dumps(gate, indent=2))
        return 2
    blender = Path(args.blender)
    if not blender.is_file():
        print(json.dumps({"status": "blocked", "failures": ["blender_executable_missing"]}, indent=2))
        return 4
    try:
        completed = run_blender_worker(
            request_path,
            blender_executable=blender,
            project_root=PROJECT_ROOT,
            timeout_seconds=args.timeout_seconds,
        )
        if completed.stdout.strip():
            print(completed.stdout.strip())
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
        status = finalize_adult_reference_candidate(request_path, project_root=PROJECT_ROOT)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "failures": [f"backend_execution_failed:{type(exc).__name__}"],
                    "detail": str(exc),
                    "runtime_activation_allowed": False,
                },
                indent=2,
            )
        )
        return 5
    print(json.dumps(status, indent=2))
    successful_inactive_generation = (
        status.get("status") == "artifact_generated_review_blocked"
        and status.get("artifact_generation_succeeded") is True
        and status.get("runtime_activation_allowed") is False
    )
    return 0 if successful_inactive_generation else 6


if __name__ == "__main__":
    raise SystemExit(main())
