from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Core.portable_os_voice import (
    OSVoiceRoute,
    candidate_os_voice_preferences,
    detect_candidate_os_voice_route,
    detect_os_voice_route,
    speak_with_os_voice,
)


def completed(stdout: str = "", stderr: str = "", returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


class PortableOSVoiceTests(unittest.TestCase):
    def test_holmes_requests_generic_male_windows_voice(self) -> None:
        candidate = {
            "candidate_id": "h_h_holmes_h_h_holmes_20260605_221432",
            "profile": {
                "display_name": "H. H. Holmes",
                "gender_preference": "Male",
            },
        }
        profile = {
            "sapi_approximation": {"voice_name": "Microsoft David Desktop"}
        }

        self.assertEqual(
            candidate_os_voice_preferences(candidate, profile),
            ("male", "Microsoft David Desktop"),
        )

    def test_synthetic_robert_requires_separate_persistent_runtime_voice_route(self) -> None:
        candidate = {
            "candidate_id": "robert_mcmurrer_presence_ai",
            "profile": {"display_name": "Synthetic Robert", "gender_preference": "Male"},
        }
        run = Mock()

        route = detect_candidate_os_voice_route(
            candidate,
            platform_name="win32",
            which=lambda name: "powershell" if name == "powershell.exe" else None,
            run=run,
        )

        self.assertFalse(route.available)
        self.assertEqual(
            route.reason,
            "synthetic_robert_persistent_runtime_voice_route_required",
        )
        run.assert_not_called()

    def test_canonical_synthetic_robert_id_blocks_discovery_with_blank_or_renamed_display(self) -> None:
        for display_name in ("", "Renamed Downloaded Person"):
            with self.subTest(display_name=display_name):
                candidate = {
                    "candidate_id": "synthetic_robert",
                    "profile": {
                        "candidate_id": "synthetic_robert",
                        "display_name": display_name,
                        "gender_preference": "Male",
                    },
                }
                run = Mock()
                route = detect_candidate_os_voice_route(
                    candidate,
                    platform_name="win32",
                    which=lambda name: "powershell" if name == "powershell.exe" else None,
                    run=run,
                )

                self.assertFalse(route.available)
                self.assertEqual(
                    route.reason,
                    "synthetic_robert_persistent_runtime_voice_route_required",
                )
                run.assert_not_called()

    def test_windows_probe_selects_exact_installed_holmes_preference(self) -> None:
        voices = json.dumps(
            [
                {"name": "Microsoft Zira Desktop", "gender": "Female", "culture": "en-US"},
                {"name": "Microsoft David Desktop", "gender": "Male", "culture": "en-US"},
            ]
        )
        run = Mock(return_value=completed(voices))
        which = lambda name: "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe" if name == "powershell.exe" else None
        candidate = {
            "candidate_id": "h_h_holmes_h_h_holmes_20260605_221432",
            "profile": {"display_name": "H. H. Holmes", "gender_preference": "Male"},
        }

        route = detect_candidate_os_voice_route(
            candidate,
            {"sapi_approximation": {"voice_name": "Microsoft David Desktop"}},
            platform_name="win32",
            which=which,
            run=run,
        )

        self.assertTrue(route.available)
        self.assertEqual(route.backend, "windows_system_speech")
        self.assertEqual(route.voice_name, "Microsoft David Desktop")
        self.assertEqual(route.selection_basis, "exact_preference")
        self.assertEqual(route.installed_voice_count, 2)
        self.assertNotIn("Speak(", run.call_args.args[0][-1])

    def test_windows_fails_closed_when_system_speech_has_no_voices(self) -> None:
        route = detect_os_voice_route(
            gender_preference="female",
            platform_name="win32",
            which=lambda name: "powershell" if name == "powershell.exe" else None,
            run=Mock(return_value=completed("")),
        )

        self.assertFalse(route.available)
        self.assertEqual(route.reason, "windows_sapi_reported_no_installed_voices")

    def test_windows_uses_builtin_sapi_com_when_system_speech_probe_fails(self) -> None:
        voices = json.dumps(
            [
                {
                    "name": "Microsoft David Desktop - English (United States)",
                    "gender": "Male",
                    "culture": "409",
                }
            ]
        )
        run = Mock(
            side_effect=[
                completed(stderr="System.Speech null reference", returncode=1),
                completed(voices),
            ]
        )
        route = detect_os_voice_route(
            gender_preference="male",
            preferred_windows_voice="Microsoft David Desktop",
            platform_name="win32",
            which=lambda name: "powershell" if name == "powershell.exe" else None,
            run=run,
        )

        self.assertTrue(route.available)
        self.assertEqual(route.backend, "windows_sapi_com")
        self.assertEqual(
            route.voice_name,
            "Microsoft David Desktop - English (United States)",
        )
        self.assertEqual(route.selection_basis, "exact_preference")

    def test_macos_say_selects_installed_gender_preference(self) -> None:
        listing = (
            "Alex                 en_US    # Hello! My name is Alex.\n"
            "Samantha             en_US    # Hello! My name is Samantha.\n"
        )
        route = detect_os_voice_route(
            gender_preference="female",
            platform_name="darwin",
            which=lambda name: "/usr/bin/say" if name == "say" else None,
            run=Mock(return_value=completed(listing)),
        )

        self.assertTrue(route.available)
        self.assertEqual(route.backend, "macos_say")
        self.assertEqual(route.voice_name, "Samantha")
        self.assertEqual(route.selection_basis, "gender_preference")

    def test_linux_uses_only_installed_espeak_and_matches_gender(self) -> None:
        listing = (
            "Pty Language Age/Gender VoiceName          File          Other Languages\n"
            " 5  en-gb             M  english-mb-en1   mb/mb-en1\n"
            " 5  en-gb             F  english-mb-en1-f1 mb/mb-en1-f1\n"
        )
        route = detect_os_voice_route(
            gender_preference="female",
            platform_name="linux",
            which=lambda name: "/usr/bin/espeak-ng" if name == "espeak-ng" else None,
            run=Mock(return_value=completed(listing)),
        )

        self.assertTrue(route.available)
        self.assertEqual(route.backend, "linux_espeak")
        self.assertEqual(route.voice_name, "english-mb-en1-f1")
        self.assertEqual(route.selection_basis, "installed_gender_match")

    def test_linux_without_installed_tts_is_truthfully_unavailable(self) -> None:
        route = detect_os_voice_route(
            platform_name="linux",
            which=lambda _name: None,
            run=Mock(),
        )

        self.assertFalse(route.available)
        self.assertEqual(route.reason, "no_supported_installed_linux_tts_command")

    def test_windows_speech_passes_text_via_stdin_not_command_source(self) -> None:
        route = OSVoiceRoute(
            True,
            "windows",
            backend="windows_system_speech",
            executable="powershell",
            voice_name="Microsoft David Desktop",
            gender_preference="male",
        )
        run = Mock(return_value=completed())
        malicious_text = "Hello'; Remove-Item C:/never; 'Robert"

        result = speak_with_os_voice(malicious_text, route, run=run)

        self.assertTrue(result["spoken"])
        self.assertTrue(result["os_voice_fallback_used"])
        self.assertFalse(result["custom_voice_pack_used"])
        args = run.call_args.args[0]
        self.assertNotIn(malicious_text, args[-1])
        payload = json.loads(run.call_args.kwargs["input"])
        self.assertEqual(payload["text"], malicious_text)
        self.assertEqual(payload["voice_name"], "Microsoft David Desktop")

    def test_macos_and_linux_execution_are_argument_lists(self) -> None:
        routes = (
            OSVoiceRoute(True, "macos", "macos_say", "/usr/bin/say", "Samantha"),
            OSVoiceRoute(True, "linux", "linux_espeak", "/usr/bin/espeak", "english"),
            OSVoiceRoute(True, "linux", "linux_spd_say", "/usr/bin/spd-say", "male1"),
        )
        for route in routes:
            with self.subTest(backend=route.backend):
                run = Mock(return_value=completed())
                result = speak_with_os_voice("Hello Robert.", route, run=run)
                self.assertTrue(result["spoken"])
                self.assertIsInstance(run.call_args.args[0], list)
                self.assertIn("Hello Robert.", run.call_args.args[0])

    def test_probe_errors_and_speech_errors_do_not_claim_success(self) -> None:
        probe_route = detect_os_voice_route(
            platform_name="win32",
            which=lambda name: "powershell" if name == "powershell.exe" else None,
            run=Mock(side_effect=subprocess.TimeoutExpired("powershell", 8)),
        )
        self.assertFalse(probe_route.available)
        self.assertIn("probe_error:TimeoutExpired", probe_route.reason)

        route = OSVoiceRoute(True, "macos", "macos_say", "/usr/bin/say", "Alex")
        result = speak_with_os_voice(
            "Hello.", route, run=Mock(return_value=completed(stderr="failed", returncode=1))
        )
        self.assertFalse(result["spoken"])
        self.assertFalse(result["os_voice_fallback_used"])
        self.assertEqual(result["reason"], "os_voice_command_failed")

    def test_dry_run_never_invokes_speech(self) -> None:
        route = OSVoiceRoute(True, "macos", "macos_say", "/usr/bin/say", "Alex")
        run = Mock()

        result = speak_with_os_voice("Hello.", route, run=run, dry_run=True)

        self.assertFalse(result["spoken"])
        self.assertEqual(result["reason"], "dry_run")
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
