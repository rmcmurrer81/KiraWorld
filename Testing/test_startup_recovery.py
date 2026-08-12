import json
import unittest
from pathlib import Path

from tools.startup_recovery_check import build_startup_report, load_state, mark_clean_shutdown, mark_start
from tools.validate_startup_recovery_config import validate_startup_recovery_config


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "Data" / "launch" / "startup_recovery_config.json"
TMP_STATE = PROJECT_ROOT / "Data" / "launch" / "_startup_recovery_state_test.json"


class StartupRecoveryTests(unittest.TestCase):
    def tearDown(self):
        if TMP_STATE.exists():
            TMP_STATE.unlink()

    def test_config_validates(self):
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertEqual(validate_startup_recovery_config(data), [])

    def test_quick_report_is_not_blocked(self):
        report = build_startup_report(CONFIG_PATH, run_command_checks=False)
        self.assertFalse(report["blocked"], report)
        self.assertFalse(report["missing_files"])
        self.assertFalse(report["missing_watched_roots"])

    def test_unclean_session_marker_round_trip(self):
        mark_start(TMP_STATE, "kira_text_only")
        dirty = load_state(TMP_STATE)
        self.assertTrue(dirty["active_session"])
        mark_clean_shutdown(TMP_STATE)
        clean = load_state(TMP_STATE)
        self.assertFalse(clean["active_session"])
        self.assertIsNotNone(clean["last_clean_shutdown_at"])


if __name__ == "__main__":
    unittest.main()
