import json
import unittest
from pathlib import Path

from tools.first_week_aliveness import build_packet
from tools.validate_first_week_aliveness_config import validate_first_week_aliveness_config


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "Data" / "launch" / "first_week_aliveness_config.json"


class FirstWeekAlivenessTests(unittest.TestCase):
    def test_config_validates(self):
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertEqual(validate_first_week_aliveness_config(data), [])

    def test_kira_packet_contains_continuity_and_privacy(self):
        packet = build_packet("kira", CONFIG_PATH)
        self.assertEqual(packet["entity_id"], "kira")
        self.assertIn("startup_status", packet)
        self.assertIn("daily_life_carryover", packet)
        self.assertFalse(packet["private_inner_life_prompts"]["visible_to_robert_by_default"])
        self.assertFalse(packet["memory_promotion_review"]["auto_promote"])

    def test_lisa_packet_is_separate(self):
        packet = build_packet("lisa", CONFIG_PATH)
        self.assertEqual(packet["entity_id"], "lisa")
        self.assertEqual(packet["display_name"], "Lisa")
        self.assertIn("separate", packet["first_week_tone"])


if __name__ == "__main__":
    unittest.main()
