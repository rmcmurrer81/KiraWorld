"""Fail-closed launch paths for the bounded Hanson ROS 2 bridge demos.

This launcher selects exactly one checked-in conversational person route.  It
can run deterministic ROS-independent validation or the existing ROS 2 policy
admission demo.  It does not attach a running World Shell session and it never
starts a physical-body adapter.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_ROOT = PROJECT_ROOT / "integrations" / "hanson_ros2_bridge"
STANDALONE_ROOT = BRIDGE_ROOT / "standalone"
ROS_WORKSPACE = BRIDGE_ROOT / "ros2_ws"
DEFAULT_POLICY = (
    ROS_WORKSPACE
    / "src"
    / "kira_hanson_bridge"
    / "config"
    / "safety_policy.yaml"
)
DEFAULT_INTAKE = (
    BRIDGE_ROOT
    / "hanson_interface_intake"
    / "official-hanson-interface-intake.template.json"
)
INTAKE_SCHEMA = (
    BRIDGE_ROOT
    / "hanson_interface_intake"
    / "official-hanson-interface-intake.schema.json"
)
INTAKE_VALIDATOR = STANDALONE_ROOT / "validate_hanson_intake.py"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.downloaded_person_chat_catalog import (  # noqa: E402
    PersonChatRoute,
    discover_downloaded_person_routes,
)
from tools.downloaded_person_chat_launcher import choose_route  # noqa: E402


SAFE_PERSON_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SAFE_ROS_DISTRO = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
SAFE_WSL_DISTRIBUTION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
ELIGIBLE_IDENTITY_CLASSES = frozenset(
    {
        "portable_persistent_person",
        "resident_person",
        "temporary_ai_review_candidate",
    }
)
AUTHORITATIVE_INTAKE_STATUSES = frozenset(
    {"hanson_reviewed", "simulator_validated_for_named_versions"}
)


class LauncherRefusal(RuntimeError):
    """A deliberate fail-closed launcher decision."""


def eligible_person_routes(
    project_root: str | Path = PROJECT_ROOT,
) -> tuple[PersonChatRoute, ...]:
    """Return exact catalog routes that are safe for a mock source label.

    A catalog display name never authorizes a route.  Every returned route has
    an exact bounded identifier and a known identity class.  Downloaded
    candidate routes additionally require their shared local review launcher.
    Fixed persistent/resident routes are checked-in catalog identities; their
    separate chat bundle is not required for this deterministic mock label,
    and no chat launcher is started by this bridge launcher.
    """

    root = Path(project_root).resolve()
    routes = discover_downloaded_person_routes(root)
    eligible: list[PersonChatRoute] = []
    seen: dict[str, PersonChatRoute] = {}
    for route in routes:
        person_id = str(route.person_id)
        prior = seen.get(person_id)
        if prior is not None:
            # Fixed routes are discovered first.  A candidate directory may
            # reuse one of those ids, but it must not shadow or duplicate the
            # exact persistent/resident route exposed by this launcher.  Any
            # other duplicate remains an unexpected fail-closed condition.
            if not prior.candidate_id and route.candidate_id == person_id:
                continue
            raise LauncherRefusal("person_catalog_duplicate_id")
        seen[person_id] = route
        if route.identity_class not in ELIGIBLE_IDENTITY_CLASSES:
            continue
        if not SAFE_PERSON_ID.fullmatch(person_id):
            continue
        if route.candidate_id and route.candidate_id != person_id:
            continue
        if route.candidate_id:
            launcher = (root / route.launcher).resolve()
            try:
                launcher.relative_to(root)
            except ValueError:
                continue
            if not launcher.is_file():
                continue
        eligible.append(route)
    return tuple(eligible)


def select_person_route(
    selection: str,
    *,
    project_root: str | Path = PROJECT_ROOT,
    input_fn: Callable[[str], str] = input,
) -> PersonChatRoute:
    """Select one exact eligible person, prompting when no id was supplied."""

    routes = eligible_person_routes(project_root)
    if not routes:
        raise LauncherRefusal("no_eligible_person_routes")
    raw = str(selection or "").strip()
    if not raw:
        print("Eligible deterministic bridge-demo identities:")
        for index, route in enumerate(routes, start=1):
            print(f"{index}. {route.display_name} [{route.person_id}]")
        try:
            raw = input_fn("Pick a number or exact person/candidate id: ").strip()
        except (EOFError, KeyboardInterrupt) as exc:
            raise LauncherRefusal("person_selection_cancelled") from exc
    try:
        selected = choose_route(routes, raw)
    except ValueError as exc:
        raise LauncherRefusal("unknown_or_ineligible_person_selection") from exc
    if sum(route.person_id == selected.person_id for route in routes) != 1:
        raise LauncherRefusal("person_selection_not_unique")
    return selected


def _load_yaml_support() -> tuple[Any, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise LauncherRefusal(
            "standalone_dependencies_missing: install standalone/requirements.txt"
        ) from exc

    package_root = ROS_WORKSPACE / "src" / "kira_hanson_bridge"
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    try:
        from kira_hanson_bridge.policy import SafetyPolicy
    except (ImportError, ModuleNotFoundError) as exc:
        raise LauncherRefusal("bounded_policy_module_unavailable") from exc
    return yaml, SafetyPolicy


def write_single_person_policy(person_id: str, destination: str | Path) -> Path:
    """Copy the default policy and narrow its source allowlist to one id."""

    if not SAFE_PERSON_ID.fullmatch(str(person_id)):
        raise LauncherRefusal("selected_person_id_is_not_policy_safe")
    yaml, safety_policy_type = _load_yaml_support()
    try:
        policy = yaml.safe_load(DEFAULT_POLICY.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise LauncherRefusal("default_safety_policy_unavailable") from exc
    if not isinstance(policy, dict) or not isinstance(policy.get("common"), dict):
        raise LauncherRefusal("default_safety_policy_invalid")
    policy["common"] = dict(policy["common"])
    policy["common"]["allowed_source_identities"] = [str(person_id)]
    safety_policy_type(policy)
    target = Path(destination)
    target.write_text(
        yaml.safe_dump(policy, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    reloaded = safety_policy_type.from_yaml(target)
    if reloaded.common.get("allowed_source_identities") != [str(person_id)]:
        raise LauncherRefusal("single_person_policy_binding_failed")
    return target


def standalone_commands(
    person_id: str,
    policy_path: str | Path,
    *,
    python_executable: str | Path = sys.executable,
) -> tuple[tuple[str, ...], ...]:
    """Build the deterministic validation commands in their review order."""

    python = str(python_executable)
    policy = str(Path(policy_path).resolve())
    evidence = str((STANDALONE_ROOT / "evidence.jsonl").resolve())
    session_evidence = str((STANDALONE_ROOT / "session_evidence.jsonl").resolve())
    event_schema = str(
        (BRIDGE_ROOT / "protocol_v0_2" / "execution-event.schema.json").resolve()
    )
    return (
        (
            python,
            "-B",
            "-W",
            "error",
            "-m",
            "unittest",
            "discover",
            "-s",
            "standalone/tests",
        ),
        (python, "-B", "standalone/validate_hanson_intake.py"),
        (
            python,
            "-B",
            "standalone/demo.py",
            "--source-identity",
            person_id,
            "--policy-file",
            policy,
        ),
        (
            python,
            "-B",
            "standalone/session_demo.py",
            "--source-identity",
            person_id,
            "--policy-file",
            policy,
        ),
        (python, "-B", "standalone/verify_evidence.py", evidence),
        (
            python,
            "-B",
            "standalone/verify_evidence.py",
            session_evidence,
            "--record-schema",
            event_schema,
        ),
    )


def _display_command(command: Sequence[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(list(command))
    return shlex.join(command)


def _run_checked(command: Sequence[str], *, cwd: Path) -> None:
    print(f"> {_display_command(command)}", flush=True)
    try:
        completed = subprocess.run(list(command), cwd=str(cwd), check=False)
    except OSError as exc:
        raise LauncherRefusal("required_process_could_not_start") from exc
    if completed.returncode != 0:
        raise LauncherRefusal(
            f"validation_command_failed_with_exit_{completed.returncode}"
        )


def _require_deterministic_source(session_source: str) -> None:
    if session_source == "deterministic-demo":
        return
    raise LauncherRefusal(
        "running_world_shell_attach_unavailable: the current shell exposes "
        "active-session metadata but no authenticated high-level-intention "
        "stream/session attach API for this bridge"
    )


def run_standalone(
    route: PersonChatRoute,
    *,
    session_source: str = "deterministic-demo",
) -> int:
    """Run the ROS-independent tests and mock lifecycle for one source id."""

    _require_deterministic_source(session_source)
    print(f"Selected exact person id: {route.person_id}")
    print("Source: deterministic fixture only; no running chat or life loop is attached.")
    print("Target: mock simulator lifecycle only; no physical hardware is used.")
    with tempfile.TemporaryDirectory(prefix="kira_hanson_demo_") as directory:
        policy_path = write_single_person_policy(
            route.person_id, Path(directory) / "single_person_safety_policy.yaml"
        )
        for command in standalone_commands(route.person_id, policy_path):
            _run_checked(command, cwd=BRIDGE_ROOT)
    print("Standalone bounded bridge validation passed.")
    return 0


def _load_intake_validator() -> Any:
    if str(STANDALONE_ROOT) not in sys.path:
        sys.path.insert(0, str(STANDALONE_ROOT))
    spec = importlib.util.spec_from_file_location(
        "_kira_hanson_intake_validator", INTAKE_VALIDATOR
    )
    if spec is None or spec.loader is None:
        raise LauncherRefusal("authoritative_intake_validator_unavailable")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except (ImportError, OSError) as exc:
        raise LauncherRefusal(
            "standalone_dependencies_missing: install standalone/requirements.txt"
        ) from exc
    return module


def load_authoritative_intake(path: str | Path) -> Mapping[str, Any]:
    """Validate a completed official intake without printing supplied values."""

    validator = _load_intake_validator()
    try:
        intake = validator.load_and_validate(
            Path(path).resolve(), INTAKE_SCHEMA, require_official=True
        )
    except Exception as exc:
        expected_errors = (
            getattr(validator, "IntakeReferenceError"),
            getattr(validator, "IntakeInputError"),
            OSError,
            TypeError,
            ValueError,
            KeyError,
            IndexError,
            OverflowError,
            RecursionError,
            UnicodeError,
        )
        schema_errors = tuple(
            error
            for error in (
                getattr(validator, "SchemaError", None),
                getattr(validator, "ValidationError", None),
            )
            if isinstance(error, type)
        )
        if isinstance(exc, expected_errors + schema_errors):
            raise LauncherRefusal(
                "authoritative_hanson_intake_required_or_incomplete"
            ) from exc
        raise
    if intake.get("intake_status") not in AUTHORITATIVE_INTAKE_STATUSES:
        raise LauncherRefusal("authoritative_hanson_intake_status_required")
    return intake


def confirmed_ros_distro(
    intake: Mapping[str, Any], requested: str
) -> str:
    """Match the WSL ROS setup directory to the confirmed intake value."""

    distro = str(requested or "").strip().lower()
    if not SAFE_ROS_DISTRO.fullmatch(distro):
        raise LauncherRefusal("safe_ros_distro_argument_required")
    try:
        field = intake["target_environment"]["ros_2_distribution"]
        status = field["status"]
        confirmed = str(field["value"] or "").strip().lower()
    except (KeyError, TypeError) as exc:
        raise LauncherRefusal("confirmed_ros_distribution_missing_from_intake") from exc
    if status != "confirmed_official" or confirmed != distro:
        raise LauncherRefusal("ros_distro_does_not_match_confirmed_intake")
    return distro


def _wsl_prefix(wsl_distribution: str) -> list[str]:
    if wsl_distribution and not SAFE_WSL_DISTRIBUTION.fullmatch(wsl_distribution):
        raise LauncherRefusal("invalid_wsl_distribution_name")
    command = ["wsl.exe"]
    if wsl_distribution:
        command.extend(["-d", wsl_distribution])
    command.append("--")
    return command


def windows_path_to_wsl(path: str | Path, *, wsl_distribution: str = "") -> str:
    """Resolve a Windows path inside the selected WSL distribution."""

    if shutil.which("wsl.exe") is None:
        raise LauncherRefusal("wsl_required_for_supported_linux_ros2_demo")
    command = [
        *_wsl_prefix(wsl_distribution),
        "wslpath",
        "-a",
        "-u",
        str(Path(path).resolve()),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise LauncherRefusal("wsl_path_resolution_failed") from exc
    translated = completed.stdout.strip()
    if completed.returncode != 0 or not translated.startswith("/") or "\n" in translated:
        raise LauncherRefusal("wsl_path_resolution_failed")
    return translated


def _ros_namespace_token(person_id: str) -> str:
    return hashlib.sha256(person_id.encode("ascii")).hexdigest()[:16]


def build_wsl_ros_script(
    *,
    person_id: str,
    ros_distro: str,
    workspace_path: str,
    policy_path: str,
) -> str:
    """Build a quoted simulator-only ROS 2 command script."""

    if not SAFE_PERSON_ID.fullmatch(person_id):
        raise LauncherRefusal("selected_person_id_is_not_policy_safe")
    if not SAFE_ROS_DISTRO.fullmatch(ros_distro):
        raise LauncherRefusal("safe_ros_distro_argument_required")
    if not workspace_path.startswith("/") or not policy_path.startswith("/"):
        raise LauncherRefusal("ros_demo_requires_absolute_wsl_paths")
    token = _ros_namespace_token(person_id)
    setup_path = f"/opt/ros/{ros_distro}/setup.bash"
    namespace = f"little_sophia_sim/person_{token}"
    evidence = f"/tmp/kira_hanson_bridge_{token}.jsonl"
    launch_arguments = (
        f"source_identity:={person_id}",
        f"namespace:={namespace}",
        f"policy_file:={policy_path}",
        f"evidence_file:={evidence}",
    )
    quoted_launch = " ".join(shlex.quote(value) for value in launch_arguments)
    return "\n".join(
        (
            "set -euo pipefail",
            f"test -r {shlex.quote(setup_path)} || {{ echo 'Blocked: ROS 2 setup file is unavailable.' >&2; exit 21; }}",
            f"source {shlex.quote(setup_path)}",
            "command -v colcon >/dev/null || { echo 'Blocked: colcon is unavailable.' >&2; exit 22; }",
            "command -v ros2 >/dev/null || { echo 'Blocked: ros2 is unavailable.' >&2; exit 23; }",
            f"cd {shlex.quote(workspace_path)}",
            "colcon build --symlink-install",
            "test -r install/setup.bash || { echo 'Blocked: ROS workspace setup was not built.' >&2; exit 24; }",
            "source install/setup.bash",
            "echo 'Starting bounded ROS 2 simulator policy-admission demo; no physical adapter is connected.'",
            f"exec ros2 launch kira_hanson_bridge demo.launch.py {quoted_launch}",
        )
    )


def run_ros2_simulator(
    route: PersonChatRoute,
    *,
    intake_path: str | Path,
    ros_distro: str,
    wsl_distribution: str = "",
    session_source: str = "deterministic-demo",
    dry_run: bool = False,
) -> int:
    """Build/start only the existing ROS 2 simulator policy-admission demo."""

    _require_deterministic_source(session_source)
    intake = load_authoritative_intake(intake_path)
    confirmed_distro = confirmed_ros_distro(intake, ros_distro)
    print(f"Selected exact person id: {route.person_id}")
    print("Source: deterministic fixture only; no running chat or life loop is attached.")
    print("Target: ROS 2 simulator policy admission only; no physical adapter is connected.")
    with tempfile.TemporaryDirectory(prefix="kira_hanson_ros2_") as directory:
        windows_policy = write_single_person_policy(
            route.person_id, Path(directory) / "single_person_safety_policy.yaml"
        )
        wsl_workspace = windows_path_to_wsl(
            ROS_WORKSPACE, wsl_distribution=wsl_distribution
        )
        wsl_policy = windows_path_to_wsl(
            windows_policy, wsl_distribution=wsl_distribution
        )
        script = build_wsl_ros_script(
            person_id=route.person_id,
            ros_distro=confirmed_distro,
            workspace_path=wsl_workspace,
            policy_path=wsl_policy,
        )
        command = [*_wsl_prefix(wsl_distribution), "bash", "-lc", script]
        if dry_run:
            print(
                json.dumps(
                    {
                        "mode": "ros2_simulator_policy_admission_only",
                        "person_id": route.person_id,
                        "session_source": session_source,
                        "physical_adapter_connected": False,
                        "command": command,
                    },
                    indent=2,
                )
            )
            return 0
        _run_checked(command, cwd=PROJECT_ROOT)
    return 0


def run_physical_body(*_args: Any, **_kwargs: Any) -> int:
    """Refuse physical execution until an official adapter and return seam exist."""

    raise LauncherRefusal(
        "physical_body_mode_blocked: authoritative intake alone is insufficient; "
        "the repository has no official Hanson execution adapter, hardware "
        "safe-state/rollback binding, or World Shell avatar-or-orb return seam"
    )


def _add_person_source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "person",
        nargs="?",
        default="",
        help="Exact person/candidate id or menu number; display-name guessing is rejected.",
    )
    parser.add_argument(
        "--session-source",
        choices=("deterministic-demo", "running-world-shell"),
        default="deterministic-demo",
        help=(
            "Only deterministic-demo is implemented. running-world-shell is "
            "offered explicitly and fails closed at the missing attach seam."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select one person for the bounded Hanson bridge demos."
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    standalone = subparsers.add_parser(
        "standalone",
        help="Run 88 tests and deterministic mock validation without ROS 2.",
    )
    _add_person_source_arguments(standalone)

    ros2 = subparsers.add_parser(
        "ros2-simulator",
        help="Build/start the ROS 2 policy-admission demo in WSL after strict gates.",
    )
    _add_person_source_arguments(ros2)
    ros2.add_argument("--intake", type=Path, default=DEFAULT_INTAKE)
    ros2.add_argument("--ros-distro", default="")
    ros2.add_argument("--wsl-distribution", default="")
    ros2.add_argument("--dry-run", action="store_true")

    physical = subparsers.add_parser(
        "physical-body",
        help="Documented refusal path; physical execution is not implemented.",
    )
    _add_person_source_arguments(physical)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.mode == "physical-body":
            return run_physical_body()
        route = select_person_route(args.person)
        if args.mode == "standalone":
            return run_standalone(route, session_source=args.session_source)
        if args.mode == "ros2-simulator":
            return run_ros2_simulator(
                route,
                intake_path=args.intake,
                ros_distro=args.ros_distro,
                wsl_distribution=args.wsl_distribution,
                session_source=args.session_source,
                dry_run=args.dry_run,
            )
        raise LauncherRefusal("unsupported_launcher_mode")
    except LauncherRefusal as exc:
        print(f"Blocked: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
