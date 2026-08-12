import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from relationship_state_manager import validate_relationship_event  # noqa: E402


class RelationshipEventValidatorTests(unittest.TestCase):
    def test_example_events_validate(self) -> None:
        for path in (PROJECT_ROOT / "Data" / "relationships" / "events").glob("*.example.json"):
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(validate_relationship_event(data), [])

    def test_event_cannot_create_romance_directly(self) -> None:
        data = {
            "event_id": "event_bad_romance",
            "relationship_id": "rel_test",
            "event_type": "vulnerable_share",
            "participants": ["kira", "real_robert"],
            "privacy": {"level": "private"},
            "emotional_effect": {"primary_effect": "warmth"},
            "suggested_metric_changes": {"trust": 0.02},
            "relationship_update_policy": {
                "creates_romance": True,
                "creates_intimacy": False,
                "requires_review_before_apply": False,
            },
            "status": "reviewed",
        }
        errors = validate_relationship_event(data)
        self.assertTrue(any("cannot directly create romance" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
