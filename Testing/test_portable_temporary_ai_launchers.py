from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]

LIVE_CHAT_LAUNCHERS = (
    "Start_TemporaryAI_Live_Chat.bat",
    "Start_TemporaryAI_Live_Chat_GUI.bat",
    "Start_TemporaryAI_Candidate_Probe.bat",
)


class PortableTemporaryAILaunchersTest(unittest.TestCase):
    def test_live_chat_launchers_start_from_their_checkout(self) -> None:
        for name in LIVE_CHAT_LAUNCHERS:
            with self.subTest(launcher=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                normalized = text.replace("\\", "/").lower()
                self.assertIn('cd /d "%~dp0"', normalized)
                self.assertNotIn("c:/users/robmc/kira", normalized)

    def test_live_chat_launchers_keep_their_expected_entry_points(self) -> None:
        expected = {
            "Start_TemporaryAI_Live_Chat.bat": "tools\\temporary_ai_live_chat.py",
            "Start_TemporaryAI_Live_Chat_GUI.bat": "tools\\temporary_ai_live_chat_gui.py",
            "Start_TemporaryAI_Candidate_Probe.bat": (
                "tools\\run_temporary_ai_candidate_probe.py"
            ),
        }
        for name, entry_point in expected.items():
            with self.subTest(launcher=name):
                text = (ROOT / name).read_text(encoding="utf-8").lower()
                self.assertIn(entry_point, text)


if __name__ == "__main__":
    unittest.main()
