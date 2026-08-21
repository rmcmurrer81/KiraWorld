from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]

from tools import hanson_ros2_bridge_launcher as launcher


class HansonRos2BridgeLauncherTests(unittest.TestCase):
    def test_selector_includes_kira_robert_and_checked_in_catalog_routes(self) -> None:
        routes = launcher.eligible_person_routes(ROOT)
        ids = [route.person_id for route in routes]

        self.assertIn("kira", ids)
        self.assertIn("synthetic_robert", ids)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(
            any(route.identity_class == "temporary_ai_review_candidate" for route in routes)
        )

    def test_selector_requires_exact_id_or_menu_number(self) -> None:
        self.assertEqual(
            launcher.select_person_route("synthetic_robert", project_root=ROOT).person_id,
            "synthetic_robert",
        )
        self.assertEqual(
            launcher.select_person_route("1", project_root=ROOT).person_id,
            launcher.eligible_person_routes(ROOT)[0].person_id,
        )
        for unknown in ("Synthetic Robert", "not_a_checked_in_person", "99999"):
            with self.subTest(unknown=unknown), self.assertRaises(
                launcher.LauncherRefusal
            ):
                launcher.select_person_route(unknown, project_root=ROOT)

    def test_generated_policy_binds_exactly_one_person_without_changing_default(self) -> None:
        original = launcher.DEFAULT_POLICY.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            bound_path = launcher.write_single_person_policy(
                "synthetic_robert", Path(directory) / "policy.yaml"
            )
            import yaml

            default = yaml.safe_load(original)
            bound = yaml.safe_load(bound_path.read_text(encoding="utf-8"))

        self.assertEqual(
            bound["common"]["allowed_source_identities"], ["synthetic_robert"]
        )
        default["common"]["allowed_source_identities"] = ["synthetic_robert"]
        self.assertEqual(bound, default)
        self.assertEqual(launcher.DEFAULT_POLICY.read_bytes(), original)

    def test_standalone_commands_pass_one_selected_identity_to_both_demos(self) -> None:
        commands = launcher.standalone_commands(
            "synthetic_robert", ROOT / "single-person-policy.yaml", python_executable="py"
        )
        demo_commands = [command for command in commands if "demo.py" in " ".join(command)]

        self.assertEqual(len(demo_commands), 2)
        for command in demo_commands:
            self.assertEqual(command.count("--source-identity"), 1)
            self.assertEqual(command.count("synthetic_robert"), 1)
            self.assertEqual(command.count("--policy-file"), 1)

    def test_running_world_shell_attach_is_explicitly_unavailable(self) -> None:
        with self.assertRaisesRegex(
            launcher.LauncherRefusal, "no authenticated high-level-intention"
        ):
            launcher._require_deterministic_source("running-world-shell")

    def test_default_unresolved_intake_cannot_start_ros_demo(self) -> None:
        with self.assertRaisesRegex(
            launcher.LauncherRefusal, "authoritative_hanson_intake"
        ):
            launcher.load_authoritative_intake(launcher.DEFAULT_INTAKE)

    def test_ros_gate_checks_intake_before_wsl_or_build(self) -> None:
        route = launcher.select_person_route("kira", project_root=ROOT)
        with mock.patch.object(
            launcher,
            "load_authoritative_intake",
            side_effect=launcher.LauncherRefusal("intake_blocked"),
        ), mock.patch.object(
            launcher,
            "windows_path_to_wsl",
            side_effect=AssertionError("WSL must not run before intake passes"),
        ):
            with self.assertRaisesRegex(launcher.LauncherRefusal, "intake_blocked"):
                launcher.run_ros2_simulator(
                    route, intake_path=launcher.DEFAULT_INTAKE, ros_distro="jazzy"
                )

    def test_ros_script_is_simulator_only_and_identity_scoped(self) -> None:
        script = launcher.build_wsl_ros_script(
            person_id="synthetic_robert",
            ros_distro="jazzy",
            workspace_path="/mnt/c/repo/ros2_ws",
            policy_path="/tmp/single_person_policy.yaml",
        )

        self.assertIn("source_identity:=synthetic_robert", script)
        self.assertIn("demo.launch.py", script)
        self.assertIn("simulator policy-admission demo", script)
        self.assertIn("no physical adapter is connected", script)
        for forbidden in ("joint_trajectory", "cmd_vel", "motor_command", "ros2 topic pub"):
            self.assertNotIn(forbidden, script)

    def test_physical_body_mode_always_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            launcher.LauncherRefusal, "physical_body_mode_blocked"
        ):
            launcher.run_physical_body()
        self.assertEqual(launcher.main(["physical-body", "kira"]), 3)

    def test_root_windows_launchers_are_checkout_relative(self) -> None:
        expected = {
            "Run_Hanson_ROS2_Bridge_Standalone_Validation.bat": "standalone",
            "Start_Hanson_ROS2_Bridge_Simulator_Demo.bat": "ros2-simulator",
        }
        for filename, mode in expected.items():
            with self.subTest(filename=filename):
                text = (ROOT / filename).read_text(encoding="utf-8")
                self.assertIn('cd /d "%~dp0"', text)
                self.assertIn("tools\\hanson_ros2_bridge_launcher.py", text)
                self.assertIn(mode, text)
                self.assertNotIn(str(Path.home()), text)

    def test_ros_launch_exposes_and_passes_source_identity(self) -> None:
        launch_path = (
            launcher.ROS_WORKSPACE
            / "src"
            / "kira_hanson_bridge"
            / "launch"
            / "demo.launch.py"
        )
        text = launch_path.read_text(encoding="utf-8")

        self.assertIn('DeclareLaunchArgument("source_identity", default_value="kira")', text)
        self.assertIn('"source_identity": source_identity', text)


if __name__ == "__main__":
    unittest.main()
