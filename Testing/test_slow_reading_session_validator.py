import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from validate_slow_reading_session import validate_slow_reading_session  # noqa: E402


class SlowReadingSessionValidatorTests(unittest.TestCase):
    def _template(self) -> dict:
        path = PROJECT_ROOT / "Data" / "reading" / "slow_reading_session_template.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_template_validates(self) -> None:
        self.assertEqual(validate_slow_reading_session(self._template()), [])

    def test_instant_full_ingestion_is_rejected(self) -> None:
        data = self._template()
        data["pacing"]["allow_instant_full_ingestion"] = True
        errors = validate_slow_reading_session(data)
        self.assertTrue(any("allow_instant_full_ingestion" in error for error in errors))

    def test_large_reading_burst_is_rejected(self) -> None:
        data = self._template()
        data["pacing"]["target_units_per_session"] = 20
        errors = validate_slow_reading_session(data)
        self.assertTrue(any("target_units_per_session" in error for error in errors))

    def test_source_material_cannot_become_lived_memory(self) -> None:
        data = self._template()
        data["memory_policy"]["does_not_become_lived_memory"] = False
        errors = validate_slow_reading_session(data)
        self.assertTrue(any("does_not_become_lived_memory" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
