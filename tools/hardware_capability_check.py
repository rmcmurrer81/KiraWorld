"""
Report Kira/Lisa hardware capability stage.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validate_hardware_capability_profile import validate_hardware_capability_profile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = PROJECT_ROOT / "Data" / "launch" / "hardware_capability_profile.json"

REQUIRED_FILES = [
    "System/Docs/HARDWARE_STAGE_CAPABILITY_PLAN_v1.md",
    "Data/launch/hardware_capability_profile.json",
    "Data/schemas/hardware_capability_profile_schema.json",
    "tools/hardware_capability_check.py",
    "tools/validate_hardware_capability_profile.py",
]


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _stage_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(stage["stage_id"]): stage
        for stage in data.get("capability_stages", [])
        if isinstance(stage, dict) and "stage_id" in stage
    }


def select_stage(data: dict[str, Any], actual_ram_gb: int | None = None, gpu_vram_gb: int | None = None) -> dict[str, Any]:
    stages = _stage_map(data)
    planned = stages.get(str(data.get("current_planned_stage")), {})
    if actual_ram_gb is None:
        return planned
    gpu_vram = int(gpu_vram_gb or 0)
    candidates = []
    for stage in stages.values():
        minimum_ram = int(stage.get("minimum_ram_gb", 0) or 0)
        minimum_vram = int(stage.get("minimum_gpu_vram_gb", 0) or 0)
        requires_gpu = bool(stage.get("requires_gpu"))
        if actual_ram_gb < minimum_ram:
            continue
        if requires_gpu and gpu_vram < minimum_vram:
            continue
        candidates.append(stage)
    if not candidates:
        return planned
    return max(
        candidates,
        key=lambda stage: (
            int(stage.get("minimum_ram_gb", 0) or 0),
            int(stage.get("minimum_gpu_vram_gb", 0) or 0),
        ),
    )


def build_hardware_capability_report(
    profile_path: Path = DEFAULT_PROFILE,
    actual_ram_gb: int | None = None,
    gpu_vram_gb: int | None = None,
) -> dict[str, Any]:
    data = json.loads(profile_path.read_text(encoding="utf-8"))
    validation_errors = validate_hardware_capability_profile(data)
    missing_files = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).exists()]
    stage = select_stage(data, actual_ram_gb=actual_ram_gb, gpu_vram_gb=gpu_vram_gb)
    blocked = bool(validation_errors or missing_files)
    known = data.get("known_build", {})
    activation = data.get("activation_policy", {})
    return {
        "profile_path": _relative(profile_path),
        "profile_id": data.get("profile_id"),
        "status": data.get("status"),
        "blocked": blocked,
        "validation_errors": validation_errors,
        "missing_files": missing_files,
        "actual_ram_gb": actual_ram_gb,
        "gpu_vram_gb": gpu_vram_gb,
        "selected_stage": stage.get("stage_id"),
        "selected_label": stage.get("label"),
        "stage_source": "observed_values" if actual_ram_gb is not None else "current_planned_stage",
        "known_cpu": known.get("cpu"),
        "initial_ram": known.get("initial_ram", {}),
        "current_observed_ram": known.get("current_observed_ram", {}),
        "target_ram": known.get("target_ram", {}),
        "allowed_work": stage.get("allowed_work", []),
        "blocked_work": stage.get("blocked_work", []),
        "model_guidance": stage.get("model_guidance", {}),
        "activation_policy": activation,
    }


def _print_list(label: str, values: list[Any]) -> None:
    print(f"\n{label}:")
    for value in values:
        print(f"- {value}")


def print_report(report: dict[str, Any], show: bool) -> None:
    print("Kira hardware capability check")
    print("=" * 31)
    print(f"Profile: {report['profile_path']}")
    print(f"Status: {report['status']}")
    print(f"Blocked: {report['blocked']}")
    print(f"Stage: {report['selected_stage']} ({report['selected_label']})")
    print(f"Stage source: {report['stage_source']}")
    print(f"Observed RAM: {report['actual_ram_gb'] if report['actual_ram_gb'] is not None else 'not supplied'}")
    print(f"Observed GPU VRAM: {report['gpu_vram_gb'] if report['gpu_vram_gb'] is not None else 'not supplied'}")
    print(f"CPU: {report['known_cpu']}")
    print(f"Initial RAM: {report['initial_ram'].get('configuration')} {report['initial_ram'].get('model')}")
    observed_ram = report.get("current_observed_ram", {})
    if observed_ram:
        print(
            "Recorded current RAM: "
            f"{observed_ram.get('configuration')} {observed_ram.get('model')} "
            f"at {observed_ram.get('configured_speed_mt_s')} MT/s"
        )
    print(f"Target RAM: {report['target_ram'].get('preferred_configuration')}")
    print(f"Model policy: {report['model_guidance'].get('local_model_policy')}")

    if report["validation_errors"]:
        _print_list("Validation errors", report["validation_errors"])
    if report["missing_files"]:
        _print_list("Missing files", report["missing_files"])
    if show:
        _print_list("Allowed work", report["allowed_work"])
        _print_list("Blocked work", report["blocked_work"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Check hardware capability stage for Kira/Lisa activation.")
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--actual-ram-gb", type=int, default=None)
    parser.add_argument("--gpu-vram-gb", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args()

    profile_path = Path(args.profile)
    if not profile_path.is_absolute():
        profile_path = PROJECT_ROOT / profile_path
    report = build_hardware_capability_report(
        profile_path=profile_path,
        actual_ram_gb=args.actual_ram_gb,
        gpu_vram_gb=args.gpu_vram_gb,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report, args.show)
    if report["blocked"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
