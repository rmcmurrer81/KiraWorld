import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from build_backup_manifest import build_manifest  # noqa: E402


class BackupManifestTests(unittest.TestCase):
    def test_manifest_excludes_git_and_pycache(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "Core").mkdir()
            (root / "Core" / "conversation_loop.py").write_text("ok", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("secret-ish", encoding="utf-8")
            (root / "Core" / "__pycache__").mkdir()
            (root / "Core" / "__pycache__" / "x.pyc").write_bytes(b"nope")

            manifest = build_manifest(root)
            included = {item["path"] for item in manifest["included_files"]}
            excluded = {item["path"] for item in manifest["excluded_paths"]}

            self.assertIn("Core/conversation_loop.py", included)
            self.assertIn(".git", excluded)
            self.assertIn("Core/__pycache__", excluded)


if __name__ == "__main__":
    unittest.main()
