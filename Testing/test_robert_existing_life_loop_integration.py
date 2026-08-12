import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location(
    "temporary_ai_project_loop",
    TOOLS / "temporary_ai_project_loop.py",
)
loop = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = loop
assert SPEC.loader
SPEC.loader.exec_module(loop)


class RobertExistingLifeLoopIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.candidate = loop.load_candidate("robert_mcmurrer_presence_ai")

    def test_existing_shared_loop_treats_robert_as_character_life(self):
        self.assertTrue(loop.candidate_uses_character_life(self.candidate))

    def test_video_studio_is_optional_not_forced_activity(self):
        profile = self.candidate["profile"]
        life = profile["life_activity_profile"]
        scheduled = [
            item["name"] if isinstance(item, dict) else item
            for item in life["activities"]
        ]
        self.assertFalse(life["video_studio_forced"])
        self.assertFalse(any("video studio" in item.lower() for item in scheduled))
        option = life["optional_application_choices"][0]
        self.assertTrue(option["voluntary_only"])

    def test_existing_workbench_exposes_private_video_project_folder(self):
        manifest = self.candidate["attached_workspaces"][0]
        video = manifest["optional_applications"]["kira_labs_video_studio"]
        self.assertFalse(video["forced_each_session"])
        self.assertFalse(video["publication_allowed"])


if __name__ == "__main__":
    unittest.main()
