"""Select a checked-in person and open that person's exact chat route."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.downloaded_person_chat_catalog import (  # noqa: E402
    PersonChatRoute,
    discover_downloaded_person_routes,
)


def choose_route(
    routes: Sequence[PersonChatRoute],
    selection: str,
) -> PersonChatRoute:
    raw = str(selection or "").strip()
    if raw.isdigit():
        index = int(raw)
        if 1 <= index <= len(routes):
            return routes[index - 1]
    for route in routes:
        if raw in {route.person_id, route.candidate_id}:
            return route
    raise ValueError("unknown_person_selection")


def build_launch_spec(
    route: PersonChatRoute,
    *,
    project_root: Path = PROJECT_ROOT,
    environment: dict[str, str] | None = None,
) -> tuple[list[str], Path, dict[str, str]]:
    root = Path(project_root).resolve()
    launcher = (root / route.launcher).resolve()
    try:
        launcher.relative_to(root)
    except ValueError as exc:
        raise ValueError("launcher_outside_project") from exc
    if not launcher.is_file():
        raise FileNotFoundError(f"launcher_missing:{route.launcher}")
    env = dict(environment if environment is not None else os.environ)
    if route.identity_class == "temporary_ai_review_candidate":
        env["TEMP_AI_INITIAL_CANDIDATE_ID"] = route.candidate_id
    command = [
        env.get("COMSPEC") or "cmd.exe",
        "/d",
        "/c",
        "call",
        str(launcher),
    ]
    return command, root, env


def launch_route(route: PersonChatRoute) -> int:
    command, cwd, env = build_launch_spec(route)
    completed = subprocess.run(command, cwd=str(cwd), env=env, check=False)
    return int(completed.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Open Kira, Synthetic Robert, Lisa, or a downloaded TemporaryAI review chat."
    )
    parser.add_argument("person", nargs="?", default="")
    parser.add_argument("--list-json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    routes = discover_downloaded_person_routes(PROJECT_ROOT)
    if args.list_json:
        print(json.dumps([route.to_dict() for route in routes], indent=2, ensure_ascii=False))
        return
    selection = args.person
    if not selection:
        print("Downloaded conversational people:")
        for index, route in enumerate(routes, start=1):
            print(
                f"{index}. {route.display_name} "
                f"[{route.identity_class}; {route.chat_mode}; {route.voice_mode}]"
            )
        selection = input("Pick a number or exact person/candidate id: ").strip()
    route = choose_route(routes, selection)
    command, cwd, env = build_launch_spec(route)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "route": route.to_dict(),
                    "command": command,
                    "cwd": str(cwd),
                    "initial_candidate_id": env.get("TEMP_AI_INITIAL_CANDIDATE_ID", ""),
                    "launched": False,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return
    raise SystemExit(launch_route(route))


if __name__ == "__main__":
    main()
