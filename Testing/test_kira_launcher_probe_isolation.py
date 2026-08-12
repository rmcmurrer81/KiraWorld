from __future__ import annotations

import ast
import io
import json
import os
import tempfile
import unittest
import uuid
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]

from tools import kira_launcher_probe as probe
from tools import run_kira_launcher_probes as driver


class LauncherBranchTests(unittest.TestCase):
    def test_exactly_two_existing_launchers_are_in_the_driver(self) -> None:
        self.assertEqual(
            driver.LAUNCHERS,
            (
                ("text_voice_chat", "Start_Kira_Text_Voice_Chat.bat"),
                ("world_shell", "Start_Kira_World_Shell.bat"),
            ),
        )

    def test_normal_launchers_bind_current_models_and_branch_before_side_effects(self) -> None:
        for launcher_id, filename in driver.LAUNCHERS:
            with self.subTest(launcher=filename):
                source = (ROOT / filename).read_text(encoding="utf-8")
                folded = source.casefold()
                branch = folded.index('if /i "%kira_launcher_probe%"=="1" goto kira_launcher_probe')
                server = folded.index("kira_world_shell_server.py")
                install = folded.index("pip', 'install', 'pywebview")
                viewer = folded.index("kira_world_shell_viewer.py")
                self.assertLess(branch, server)
                self.assertLess(branch, install)
                self.assertLess(branch, viewer)
                self.assertIn('set "kira_model_name=qwen3.5:9b"', folded)
                self.assertIn(
                    'set "kira_model_digest=6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"',
                    folded,
                )
                self.assertNotIn('set "kira_model_name=llama3.1:8b"', folded)
                if launcher_id == "text_voice_chat":
                    self.assertIn(
                        'set "kira_enable_persistent_blackwell_voice_candidate_v2=1"',
                        folded,
                    )
                self.assertNotIn("--takeover", folded)

                probe_tail = folded.split(":kira_launcher_probe", 1)[1]
                self.assertIn("tools\\kira_launcher_probe.py serve", probe_tail)
                self.assertIn(f"--launcher-id {launcher_id}", probe_tail)
                for forbidden in (
                    "--takeover",
                    "start-process",
                    "pywebview",
                    " pip ",
                    "pyw",
                    "pause",
                    "kira_world_shell_server.py",
                    "kira_asr",
                    "vite",
                    "npm",
                ):
                    self.assertNotIn(forbidden, probe_tail)


class ProbeSafetyPrimitiveTests(unittest.TestCase):
    def test_probe_root_requires_safe_strict_recovery_descendant(self) -> None:
        valid = ROOT / "RecoverySprint" / "continuation_20260801" / "probe_unit_01"
        self.assertEqual(probe.resolve_probe_root(valid), valid.resolve())
        for invalid in (
            ROOT,
            ROOT / "RecoverySprint",
            ROOT / "Data" / "probe",
            Path("RecoverySprint/probe"),
            ROOT / "RecoverySprint" / "continuation_20260801" / "unsafe root",
            Path(str(ROOT / "RecoverySprint" / "first" / ".." / "second")),
        ):
            with self.subTest(invalid=str(invalid)):
                with self.assertRaises(probe.ProbeSafetyError):
                    probe.resolve_probe_root(invalid)

    def test_probe_ports_are_high_and_bounded(self) -> None:
        self.assertEqual(probe.validate_probe_port("49152"), 49152)
        self.assertEqual(probe.validate_probe_port(65535), 65535)
        for invalid in ("8767", "49151", "65536", "abcde", " 55200 extra", ""):
            with self.subTest(invalid=invalid):
                with self.assertRaises(probe.ProbeSafetyError):
                    probe.validate_probe_port(invalid)

    def test_probe_token_is_exact_256_bit_lowercase_hex(self) -> None:
        token = "ab" * 32
        self.assertEqual(probe.validate_probe_token(token), token)
        for invalid in ("ab" * 31, "AB" * 32, "g0" * 32, "", "ab" * 33):
            with self.subTest(invalid=invalid[:12]):
                with self.assertRaises(probe.ProbeSafetyError):
                    probe.validate_probe_token(invalid)

    def test_json_parser_rejects_duplicates_nonobjects_and_oversize(self) -> None:
        self.assertEqual(probe.parse_strict_json_object(b'{"candidate":"kira"}'), {"candidate": "kira"})
        for raw in (
            b'{"candidate":"kira","candidate":"lisa"}',
            b'[]',
            b'null',
            b'',
            b'{' + (b' ' * probe.MAX_REQUEST_BYTES) + b'}',
        ):
            with self.subTest(size=len(raw)):
                with self.assertRaises(probe.ProbeSafetyError):
                    probe.parse_strict_json_object(raw)

    def test_environment_is_pinned_to_local_typed_kira_contract(self) -> None:
        with patch.dict(
            os.environ,
            {
                "KIRA_MODEL_NAME": "unsafe",
                "KIRA_OLLAMA_ENDPOINT": "https://example.test/api/chat",
                "KIRA_WORLD_SHELL_ACTIVE": "1",
                "KIRA_VOICE_FORCE_SAPI": "1",
                "KIRA_ASR_PORT": "8770",
            },
            clear=True,
        ):
            probe.configure_probe_environment()
            self.assertEqual(os.environ["KIRA_MODEL_NAME"], probe.EXPECTED_MODEL)
            self.assertEqual(os.environ["KIRA_OLLAMA_ENDPOINT"], "http://127.0.0.1:11434/api/chat")
            self.assertEqual(os.environ["KIRA_OLLAMA_NUM_CTX"], "4096")
            self.assertEqual(os.environ["KIRA_WORLD_SHELL_ACTIVE"], "0")
            self.assertEqual(os.environ["KIRA_TEXT_VOICE_CHAT_ACTIVE"], "1")
            self.assertNotIn("KIRA_VOICE_FORCE_SAPI", os.environ)
            self.assertNotIn("KIRA_ASR_PORT", os.environ)

    def test_voice_refuses_while_any_model_is_resident(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            session = probe.ProbeSession(Path(temporary), "text_voice_chat")
            session.active = True
            session.chat_count = 1
            session.last_reply = "This is a public reply."
            with patch.object(probe, "_ollama_models", return_value=[{"name": probe.EXPECTED_MODEL}]):
                with self.assertRaises(probe.ProbeRuntimeError):
                    session.synthesize_voice({"candidate": "kira", "source": "last_public_reply"})

    def test_real_conversation_loop_mutable_managers_are_all_beneath_probe_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            session = probe.ProbeSession(root, "world_shell")
            session._seed_isolated_inputs()
            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                loop = session._build_conversation_loop()
            finally:
                os.chdir(previous_cwd)

            mutable_paths = (
                loop.memory.memory_path,
                loop.logger.log_path,
                loop.relationships.state_path,
                loop.privacy_sessions.session_path,
                loop.decision_log.log_path,
                loop.attention_states.state_path,
                loop.daily_life.state_dir,
                loop.daily_life.log_dir,
                loop.daily_life.reading_session_dir,
                loop.daily_life.reading_recommendation_dir,
                loop.memory_candidate_dir,
            )
            for path in mutable_paths:
                with self.subTest(path=str(path)):
                    Path(path).resolve().relative_to(root)
            session.person_state_path.resolve().relative_to(root)


class ProbeSourceBoundaryTests(unittest.TestCase):
    def test_server_has_no_gui_process_or_normal_shell_imports(self) -> None:
        source = (ROOT / "tools" / "kira_launcher_probe.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        self.assertNotIn("subprocess", imports)
        self.assertNotIn("webbrowser", imports)
        self.assertNotIn("tools.kira_world_shell_server", imports)
        self.assertNotIn("tools.kira_text_voice_asr_sidecar", imports)
        self.assertNotIn("Core.kira_tablet_messages", imports)
        self.assertNotIn("Core.candidate_movement_intents", imports)

    def test_probe_post_route_allowlist_is_minimal(self) -> None:
        source = (ROOT / "tools" / "kira_launcher_probe.py").read_text(encoding="utf-8")
        self.assertIn('"/api/activate": self.probe_server.probe_session.activate', source)
        self.assertIn('"/api/chat": self.probe_server.probe_session.chat', source)
        self.assertIn('"/api/voice": self.probe_server.probe_session.synthesize_voice', source)
        self.assertIn('"/api/close": self.probe_server.probe_session.close', source)
        for forbidden_route in (
            '"/api/open-video-studio"',
            '"/api/tablet/note"',
            '"/api/location"',
            '"/api/action"',
            '"/api/avatar-position"',
            '"/api/messages/prepare"',
        ):
            self.assertNotIn(forbidden_route, source)

    def test_model_voice_and_identity_pins_are_exact(self) -> None:
        self.assertEqual(probe.EXPECTED_MODEL, "qwen3.5:9b")
        self.assertEqual(
            probe.EXPECTED_DIGEST,
            "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
        )
        self.assertEqual(probe.EXPECTED_CONTEXT_LENGTH, 4096)
        self.assertEqual(
            probe.APPROVED_VOICE_PROFILE_SHA256,
            "102d17f5420a1a16b3a920204ebde0d532c0a9bfd2979dca28048378ecddc116",
        )
        self.assertEqual(
            probe.APPROVED_REFERENCE_SHA256,
            "2039a2abd600a63c294d69c2b2e4d450c64c850dc6d1c9a4fbfa1700ba92069c",
        )


class DriverGatingTests(unittest.TestCase):
    def test_sanitized_driver_environment_drops_unrelated_kira_routes(self) -> None:
        root = ROOT / "RecoverySprint" / "unit" / "driver_env"
        with patch.dict(
            os.environ,
            {
                "SystemRoot": r"C:\Windows",
                "PATH": r"C:\Windows\System32",
                "KIRA_ASR_PORT": "8770",
                "KIRA_WORLD_SHELL_ACTIVE": "1",
                "KIRA_STUDIO": "1",
            },
            clear=True,
        ):
            env = driver.sanitized_launcher_environment(root, 55210, "ab" * 32)
        self.assertEqual(env["KIRA_LAUNCHER_PROBE"], "1")
        self.assertEqual(env["KIRA_LAUNCHER_PROBE_ROOT"], str(root))
        self.assertEqual(env["KIRA_LAUNCHER_PROBE_PORT"], "55210")
        self.assertEqual(env["KIRA_LAUNCHER_PROBE_TOKEN"], "ab" * 32)
        self.assertNotIn("KIRA_ASR_PORT", env)
        self.assertNotIn("KIRA_WORLD_SHELL_ACTIVE", env)
        self.assertNotIn("KIRA_STUDIO", env)

    def test_plan_only_driver_does_not_create_root_or_run_live(self) -> None:
        planned = (
            ROOT
            / "RecoverySprint"
            / "continuation_20260801"
            / f"unit_plan_never_created_{uuid.uuid4().hex}"
        )
        self.assertFalse(planned.exists())
        output = io.StringIO()
        with patch.object(driver, "run_live_proofs") as live, redirect_stdout(output):
            code = driver.main(
                [
                    "--probe-root",
                    str(planned),
                    "--text-voice-port",
                    "55211",
                    "--world-shell-port",
                    "55212",
                ]
            )
        self.assertEqual(code, 0)
        live.assert_not_called()
        self.assertFalse(planned.exists())
        plan = json.loads(output.getvalue())
        self.assertEqual(plan["status"], "plan_only")
        self.assertFalse(plan["live_execution"])

    def test_driver_rejects_duplicate_ports_before_live_execution(self) -> None:
        planned = ROOT / "RecoverySprint" / "continuation_20260801" / "duplicate_port_plan"
        with patch.object(driver, "run_live_proofs") as live:
            code = driver.main(
                [
                    "--execute-live-proofs",
                    "--probe-root",
                    str(planned),
                    "--text-voice-port",
                    "55213",
                    "--world-shell-port",
                    "55213",
                ]
            )
        self.assertEqual(code, 2)
        live.assert_not_called()


if __name__ == "__main__":
    unittest.main()
