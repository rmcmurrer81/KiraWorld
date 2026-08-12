"""
CLI for the pre-GPU Kira/Lisa daily life loop.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from daily_life_manager import DEFAULT_LOG_DIR, DEFAULT_STATE_DIR, DailyLifeManager, validate_daily_life_state  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage lightweight pre-GPU daily life state.")
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show Kira and Lisa daily life states.")

    set_parser = subparsers.add_parser("set", help="Set one daily life state.")
    set_parser.add_argument("--entity", required=True, choices=["kira", "lisa"])
    set_parser.add_argument("--cycle", required=True)
    set_parser.add_argument("--mood", required=True)
    set_parser.add_argument("--intensity", type=float, default=0.4)
    set_parser.add_argument("--activity", required=True)
    set_parser.add_argument("--summary", required=True)
    set_parser.add_argument("--private-summary", default="")
    set_parser.add_argument("--privacy", default="personal")
    set_parser.add_argument("--robert-visibility", default="status_only")
    set_parser.add_argument("--interruptibility", default="medium")
    set_parser.add_argument("--toward", default="")

    step_parser = subparsers.add_parser("away-step", help="Advance one lightweight away-mode step.")
    step_parser.add_argument("--entity", choices=["kira", "lisa", "both"], default="both")

    choose_parser = subparsers.add_parser("choose-activity", help="Suggest one advisory daily-life activity.")
    choose_parser.add_argument("--entity", choices=["kira", "lisa", "both"], default="both")
    choose_parser.add_argument("--apply", action="store_true", help="Apply the suggested activity to daily-life state.")

    availability_parser = subparsers.add_parser("phone-availability", help="Show whether Kira/Lisa may answer a text.")
    availability_parser.add_argument("--entity", choices=["kira", "lisa", "both"], default="both")

    log_parser = subparsers.add_parser("log", help="Write a daily life log from current state.")
    log_parser.add_argument("--entity", required=True, choices=["kira", "lisa"])
    log_parser.add_argument("--notes", default="")

    validate_parser = subparsers.add_parser("validate", help="Validate a daily life state JSON file.")
    validate_parser.add_argument("path", type=Path)

    args = parser.parse_args()
    manager = DailyLifeManager(state_dir=args.state_dir, log_dir=args.log_dir)

    if args.command == "status":
        print(json.dumps(manager.list_states(), indent=2))
    elif args.command == "set":
        state = manager.set_state(
            args.entity,
            cycle_state=args.cycle,
            mood=args.mood,
            intensity=args.intensity,
            activity_type=args.activity,
            public_summary=args.summary,
            private_summary=args.private_summary,
            privacy_level=args.privacy,
            robert_visibility=args.robert_visibility,
            interruptibility=args.interruptibility,
            toward=args.toward,
        )
        print(json.dumps(state, indent=2))
    elif args.command == "away-step":
        entities = ["kira", "lisa"] if args.entity == "both" else [args.entity]
        print(json.dumps([manager.advance_away_step(entity) for entity in entities], indent=2))
    elif args.command == "choose-activity":
        entities = ["kira", "lisa"] if args.entity == "both" else [args.entity]
        if args.apply:
            print(json.dumps([manager.choose_and_apply_activity(entity) for entity in entities], indent=2))
        else:
            print(json.dumps([manager.choose_activity(entity) for entity in entities], indent=2))
    elif args.command == "phone-availability":
        entities = ["kira", "lisa"] if args.entity == "both" else [args.entity]
        print(json.dumps([manager.phone_availability(entity) for entity in entities], indent=2))
    elif args.command == "log":
        print(json.dumps(manager.write_log(args.entity, notes=args.notes), indent=2))
    elif args.command == "validate":
        data = json.loads(args.path.read_text(encoding="utf-8"))
        errors = validate_daily_life_state(data)
        if errors:
            print(f"{args.path} is not valid:")
            for error in errors:
                print(f"- {error}")
            raise SystemExit(1)
        print(f"{args.path} is structurally valid.")


if __name__ == "__main__":
    main()
