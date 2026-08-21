import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

import readiness_check  # noqa: E402


class ReadinessCheckFailClosedTests(unittest.TestCase):
    def test_json_loader_accepts_utf8_byte_order_mark(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.json"
            path.write_text('{"ready": true}\n', encoding="utf-8-sig")

            self.assertEqual(readiness_check.load_json_path(path), {"ready": True})

    def test_voice_profile_check_accepts_utf8_byte_order_mark(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            profile = root / "Voice" / "profiles" / "sample.json"
            profile.parent.mkdir(parents=True)
            profile.write_text("{}\n", encoding="utf-8-sig")

            with (
                patch.object(readiness_check, "PROJECT_ROOT", root),
                patch.object(readiness_check, "validate_voice_profile", return_value=[]),
            ):
                ok, detail = readiness_check.voice_profiles_validate()

            self.assertTrue(ok, detail)
            self.assertIn("1 voice profile drafts validate", detail)

    def test_missing_slow_reading_template_is_reported_without_exception(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with patch.object(readiness_check, "PROJECT_ROOT", root):
                ok, detail = readiness_check.slow_reading_sessions_validate()

            self.assertFalse(ok)
            self.assertEqual(
                detail,
                f"{Path('Data') / 'reading' / 'slow_reading_session_template.json'}: missing",
            )

    def test_unexpected_check_error_becomes_failed_result(self) -> None:
        def missing_input() -> tuple[bool, str]:
            raise FileNotFoundError("optional.json")

        ok, detail = readiness_check.run_check_safely(missing_input)

        self.assertFalse(ok)
        self.assertEqual(
            detail,
            "readiness check error (FileNotFoundError): optional.json",
        )


if __name__ == "__main__":
    unittest.main()
