from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import chat_lisa
from Core.portable_os_voice import OSVoiceRoute


class LisaOSVoiceFallbackTests(unittest.TestCase):
    def test_disabled_route_never_discovers_or_speaks(self) -> None:
        with (
            patch.object(chat_lisa, "lisa_os_voice_route") as route,
            patch.object(chat_lisa, "speak_with_os_voice") as speak,
        ):
            result = chat_lisa.speak_lisa_reply("Hello.", enabled=False)

        self.assertFalse(result["spoken"])
        self.assertEqual(result["reason"], "lisa_os_voice_disabled")
        route.assert_not_called()
        speak.assert_not_called()

    def test_available_route_is_generic_os_voice_not_custom_identity(self) -> None:
        route = OSVoiceRoute(
            True,
            "windows",
            "windows_system_speech",
            "powershell",
            "Microsoft Zira Desktop",
            "female",
            "gender_preference",
        )
        with (
            patch.object(chat_lisa, "lisa_os_voice_route", return_value=route),
            patch.object(
                chat_lisa,
                "speak_with_os_voice",
                return_value={
                    "spoken": True,
                    "os_voice_fallback_used": True,
                    "custom_voice_pack_used": False,
                    "authentic_voice_claim": False,
                },
            ) as speak,
        ):
            result = chat_lisa.speak_lisa_reply("Hello, Robert.", enabled=True)

        self.assertTrue(result["spoken"])
        self.assertTrue(result["os_voice_fallback_used"])
        self.assertFalse(result["custom_voice_pack_used"])
        self.assertFalse(result["authentic_voice_claim"])
        speak.assert_called_once_with("Hello, Robert.", route)

    def test_missing_os_voice_falls_back_to_text_only(self) -> None:
        route = OSVoiceRoute(False, "linux", reason="no_supported_installed_linux_tts_command")
        with (
            patch.object(chat_lisa, "lisa_os_voice_route", return_value=route),
            patch.object(chat_lisa, "speak_with_os_voice") as speak,
        ):
            result = chat_lisa.speak_lisa_reply("Hello.", enabled=True)

        self.assertFalse(result["spoken"])
        self.assertEqual(result["reason"], "no_supported_installed_linux_tts_command")
        speak.assert_not_called()

    def test_model_error_text_never_reaches_os_voice(self) -> None:
        for reply, audit, reason in (
            ("[Lisa - model offline] Ollama is unavailable.", {}, "model_offline_diagnostic"),
            ("[Lisa - error] response parse failed", {}, "model_error_diagnostic"),
            (
                "This value must not be spoken.",
                {"model_calls": [{"voice_generation_allowed": False}]},
                "model_call_disallows_voice",
            ),
        ):
            with self.subTest(reason=reason), patch.object(
                chat_lisa, "speak_with_os_voice"
            ) as speak:
                result = chat_lisa.speak_lisa_reply(
                    reply,
                    enabled=True,
                    turn_audit=audit,
                )
            self.assertFalse(result["spoken"])
            self.assertEqual(result["reason"], reason)
            speak.assert_not_called()

    def test_launcher_enables_generic_os_voice(self) -> None:
        launcher = (chat_lisa.PROJECT_ROOT / "Start_Lisa_Chat.bat").read_text(
            encoding="utf-8"
        )
        self.assertIn('set "KIRA_LISA_OS_VOICE=1"', launcher)
        self.assertIn("py chat_lisa.py", launcher)


if __name__ == "__main__":
    unittest.main()
