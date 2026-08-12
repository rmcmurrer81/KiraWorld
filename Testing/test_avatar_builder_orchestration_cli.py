from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.evaluate_avatar_builder_orchestration import resolve_regular_request_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL = PROJECT_ROOT / "tools" / "evaluate_avatar_builder_orchestration.py"
BETH_REQUEST = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "orchestration_requests"
    / "beth_smith_ordinary_temp_20260716.json"
)


class AvatarBuilderOrchestrationCliTests(unittest.TestCase):
    def test_cli_rejects_request_symlink_before_resolving_it(self) -> None:
        with (
            patch.object(Path, "is_symlink", return_value=True),
            patch.object(
                Path,
                "resolve",
                side_effect=AssertionError("resolve must not run before symlink rejection"),
            ),
        ):
            with self.assertRaisesRegex(FileNotFoundError, "Request is symlinked"):
                resolve_regular_request_path(BETH_REQUEST)

    def test_direct_cli_runs_outside_project_and_returns_blocked_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--request",
                    str(BETH_REQUEST),
                    "--compact",
                ],
                cwd=temp_dir,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(completed.returncode, 6, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["candidate_id"], "beth_smith_ordinary_temp_20260716")
        self.assertEqual(
            result["route"]["reconstruction_source_lane"],
            "licensed_shape_preserving_derivative",
        )
        self.assertFalse(result["review_stage_allowed"])
        self.assertFalse(result["runtime_activation_allowed"])


if __name__ == "__main__":
    unittest.main()
