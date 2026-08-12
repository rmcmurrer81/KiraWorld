import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
CORE_ROOT = PROJECT_ROOT / "Core"
sys.path.insert(0, str(TOOLS_ROOT))
sys.path.insert(0, str(CORE_ROOT))

from daily_life_manager import DailyLifeManager  # noqa: E402
from daily_life_moment import create_moment  # noqa: E402


class DailyLifeMomentTests(unittest.TestCase):
    def test_create_moment_is_pre_gpu_safe(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manager = DailyLifeManager(state_dir=root / "states", log_dir=root / "logs")
            moment = create_moment("kira", output_dir=root / "moments", manager=manager)

            self.assertEqual(moment["entity_id"], "kira")
            self.assertTrue(moment["resource_use"]["pre_gpu_safe"])
            self.assertFalse(moment["resource_use"]["used_heavy_model"])
            self.assertTrue((root / "moments" / Path(moment["path"]).name).exists())
            self.assertTrue(moment["memory_policy"]["does_not_promote_memory_automatically"])


if __name__ == "__main__":
    unittest.main()
