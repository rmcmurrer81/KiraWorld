"""
Check Robert's hardware intake and rested-build gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validate_hardware_intake_rest_gate import validate_hardware_intake_rest_gate


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE = PROJECT_ROOT / "Data" / "launch" / "hardware_intake_rest_gate.json"

REQUIRED_FILES = [
    "System/Docs/HARDWARE_INTAKE_AND_RESTED_BUILD_GATE_v1.md",
    "Data/launch/hardware_intake_rest_gate.json",
    "Data/schemas/hardware_intake_rest_gate_schema.json",
    "tools/hardware_intake_check.py",
    "tools/validate_hardware_intake_rest_gate.py",
]


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def build_hardware_intake_report(gate_path: Path = DEFAULT_GATE) -> dict[str, Any]:
    data = json.loads(gate_path.read_text(encoding="utf-8"))
    validation_errors = validate_hardware_intake_rest_gate(data)
    missing_files = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).exists()]
    gate = data.get("rest_before_build_gate", {})
    compatibility = data.get("post_purchase_compatibility_check", {})
    blocked = bool(validation_errors or missing_files)
    return {
        "gate_path": _relative(gate_path),
        "gate_id": data.get("gate_id"),
        "status": data.get("status"),
        "blocked": blocked,
        "validation_errors": validation_errors,
        "missing_files": missing_files,
        "known_reserved_item": data.get("expected_return_plan", {}).get("known_reserved_item"),
        "assembly_blocked_until_rest_gate_passes": gate.get("assembly_blocked_until_rest_gate_passes"),
        "minimum_recovery": gate.get("minimum_recovery"),
        "recommended_recovery": gate.get("recommended_recovery"),
        "must_confirm_before_build": gate.get("must_confirm_before_build", []),
        "blocked_before_rest_gate": gate.get("blocked_before_rest_gate", []),
        "cpu_socket_required": compatibility.get("cpu", {}).get("must_match_motherboard_socket"),
        "ram_required_type": compatibility.get("ram", {}).get("required_type"),
        "ram_can_wait": compatibility.get("ram", {}).get("build_can_wait_if_ram_not_obtained"),
        "immediate_return_home_actions": data.get("expected_return_plan", {}).get("immediate_actions", []),
        "do_not_do_tired": data.get("do_not_do_tired", []),
    }


def print_report(report: dict[str, Any], show: bool) -> None:
    print("Kira hardware intake and rested-build gate")
    print("=" * 43)
    print(f"Gate: {report['gate_path']}")
    print(f"Status: {report['status']}")
    print(f"Blocked: {report['blocked']}")
    print(f"Known reserved item: {report['known_reserved_item']}")
    print(f"Assembly blocked until rest gate passes: {report['assembly_blocked_until_rest_gate_passes']}")
    print(f"Minimum recovery: {report['minimum_recovery']}")
    print(f"CPU socket required: {report['cpu_socket_required']}")
    print(f"RAM required type: {report['ram_required_type']}")
    print(f"RAM can wait: {report['ram_can_wait']}")

    if report["validation_errors"]:
        print("\nValidation errors:")
        for error in report["validation_errors"]:
            print(f"- {error}")
    if report["missing_files"]:
        print("\nMissing files:")
        for path in report["missing_files"]:
            print(f"- {path}")

    if show:
        print("\nImmediate return-home actions:")
        for action in report["immediate_return_home_actions"]:
            print(f"- {action}")
        print("\nMust confirm before build:")
        for item in report["must_confirm_before_build"]:
            print(f"- {item}")
        print("\nBlocked before rest gate:")
        for item in report["blocked_before_rest_gate"]:
            print(f"- {item}")
        print("\nDo not do tired:")
        for item in report["do_not_do_tired"]:
            print(f"- {item}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check hardware intake and rested-build gate.")
    parser.add_argument("--gate", default=str(DEFAULT_GATE))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args()

    gate_path = Path(args.gate)
    if not gate_path.is_absolute():
        gate_path = PROJECT_ROOT / gate_path
    report = build_hardware_intake_report(gate_path)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report, args.show)
    if report["blocked"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
