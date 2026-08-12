from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.evaluate_realtime_audio_readiness import (  # noqa: E402
    EVALUATION_ROOT,
    _resolve_output_path,
    _write_json_exclusive,
)


class RealtimeAudioReadinessCliTests(unittest.TestCase):
    def test_blocked_baseline_returns_nonzero_by_default(self) -> None:
        command = [
            sys.executable,
            str(PROJECT_ROOT / "tools" / "evaluate_realtime_audio_readiness.py"),
            "Data/voice/realtime_audio_readiness/kira_cpu_chatterbox_baseline_20260716.json",
            "--profile",
            "desktop_live",
        ]
        completed = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 2)
        self.assertIn('"status": "blocked_evidence_contract_invalid"', completed.stdout)
        self.assertIn('"source_evidence_sha256"', completed.stdout)
        self.assertIn('"evaluator_core_sha256"', completed.stdout)

    def test_interactive_override_is_explicit(self) -> None:
        command = [
            sys.executable,
            str(PROJECT_ROOT / "tools" / "evaluate_realtime_audio_readiness.py"),
            "Data/voice/realtime_audio_readiness/kira_cpu_chatterbox_baseline_20260716.json",
            "--allow-not-ready-exit-zero",
        ]
        completed = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 0)

    def test_output_is_limited_to_immutable_evaluation_folder(self) -> None:
        evidence = PROJECT_ROOT / "Data" / "voice" / "realtime_audio_readiness" / "kira_cpu_chatterbox_baseline_20260716.json"
        with self.assertRaisesRegex(ValueError, "escape|limited"):
            _resolve_output_path(str(PROJECT_ROOT / "Data" / "codex_reports" / "important.json"), evidence_path=evidence)
        with self.assertRaisesRegex(ValueError, "parent"):
            _resolve_output_path("../../overwrite.json", evidence_path=evidence)

    def test_exclusive_writer_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory(dir=EVALUATION_ROOT.parent) as temp:
            path = Path(temp) / "evaluation.json"
            _write_json_exclusive(path, {"status": "first"})
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                _write_json_exclusive(path, {"status": "second"})
            self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
