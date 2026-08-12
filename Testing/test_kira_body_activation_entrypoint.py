import hashlib
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/build_kira_adult_body_with_eyes_20260713.py"
LIVE = ROOT / "Avatar/models/temp_ai/kira/avatar.glb"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class KiraBodyActivationEntrypointTests(unittest.TestCase):
    def test_legacy_one_command_activation_fails_before_live_copy(self):
        before = sha256(LIVE)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--activate"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("legacy --activate path is disabled", result.stdout + result.stderr)
        self.assertEqual(sha256(LIVE), before)

    def test_entrypoint_requires_exact_hash_activation_helper(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("activate_staged_model_if_approved", source)
        self.assertIn("--activate-staged", source)
        self.assertIn("activation_requested=True", source)
        self.assertNotIn("shutil.copy2(model_out, ACTIVE_MODEL)", source)


if __name__ == "__main__":
    unittest.main()
