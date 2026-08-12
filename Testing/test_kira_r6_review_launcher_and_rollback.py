import subprocess
import unittest
from pathlib import Path

from tools.open_kira_r6_private_owner_review import REVIEW, review_uri
from tools.restore_kira_pre_r6_live_body import EXPECTED, verify


ROOT = Path(__file__).resolve().parents[1]


class KiraR6ReviewLauncherAndRollbackTests(unittest.TestCase):
    def test_review_launcher_uses_absolute_file_uri(self):
        uri = review_uri()
        self.assertTrue(REVIEW.is_file())
        self.assertTrue(uri.startswith("file:///C:/"), uri)
        self.assertNotIn("\\", uri)
        self.assertTrue(uri.endswith("/index.html"))

    def test_batch_launcher_passes_safe_test_arguments(self):
        completed = subprocess.run(
            [
                "cmd",
                "/c",
                str(ROOT / "Open_Kira_R6_Private_Clothed_Owner_Review.bat"),
                "--print-uri",
                "--no-open",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertIn("file:///", completed.stdout)

    def test_exact_rollback_payload_is_intact(self):
        verify()
        self.assertGreaterEqual(len(EXPECTED), 5)


if __name__ == "__main__":
    unittest.main()
