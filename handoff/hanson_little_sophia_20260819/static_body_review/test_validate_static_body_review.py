from __future__ import annotations

import shutil
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from validate_static_body_review import EXPECTED, validate


class StaticBodyReviewValidatorTests(unittest.TestCase):
    def _fixture(self, destination: Path) -> None:
        destination.mkdir()
        for name in EXPECTED:
            shutil.copyfile(ROOT / name, destination / name)

    def test_exact_curated_artifacts_pass(self) -> None:
        self.assertEqual([], validate(ROOT))

    def test_one_byte_tamper_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "fixture"
            self._fixture(fixture)
            target = fixture / "INTENDED_BODY_V5_AUDIT_DECISION.json"
            target.write_bytes(target.read_bytes() + b" ")
            issues = validate(fixture)
            self.assertTrue(any("byte mismatch" in issue for issue in issues))
            self.assertTrue(any("sha256 mismatch" in issue for issue in issues))

    def test_duplicate_key_fails_even_with_valid_json_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "fixture"
            self._fixture(fixture)
            target = fixture / "FACIAL_V4_AUDIT_DECISION.json"
            target.write_text('{"a":1,"a":2}', encoding="utf-8")
            issues = validate(fixture)
            self.assertTrue(any("strict JSON failure" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
