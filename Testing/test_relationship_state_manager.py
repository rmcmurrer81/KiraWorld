import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from relationship_state_manager import (  # noqa: E402
    RelationshipStateManager,
    validate_relationship_event,
    validate_relationship_state,
)


def sample_state() -> dict:
    return {
        "relationship_id": "rel_kira_lisa_test",
        "participants": [
            {"participant_id": "kira", "presence_role": "core_ai"},
            {"participant_id": "lisa", "presence_role": "core_ai"},
        ],
        "relationship_type": "friendship",
        "metrics": {
            "trust": 0.7,
            "familiarity": 0.8,
            "emotional_closeness": 0.7,
            "comfort": 0.6,
            "conflict_level": 0.2,
            "privacy_sensitivity": 0.8,
        },
        "boundaries": [],
        "consent_context": {},
        "milestones": [],
        "unresolved_issues": [],
        "recent_emotional_tone": "mixed",
        "long_term_trend": "stable",
        "linked_records": [],
        "privacy_rules": {},
        "status": "draft",
    }


class RelationshipStateManagerTests(unittest.TestCase):
    def test_valid_state_passes(self) -> None:
        self.assertEqual(validate_relationship_state(sample_state()), [])

    def test_metric_updates_are_clamped(self) -> None:
        with TemporaryDirectory() as tmpdir:
            manager = RelationshipStateManager(Path(tmpdir) / "relationships.json")
            manager.add_state(sample_state())
            updated = manager.update_metrics("rel_kira_lisa_test", {"trust": 0.5, "conflict_level": -1.0})
            self.assertEqual(updated["metrics"]["trust"], 1.0)
            self.assertEqual(updated["metrics"]["conflict_level"], 0.0)

    def test_add_unresolved_issue(self) -> None:
        with TemporaryDirectory() as tmpdir:
            manager = RelationshipStateManager(Path(tmpdir) / "relationships.json")
            manager.add_state(sample_state())
            updated = manager.add_unresolved_issue(
                "rel_kira_lisa_test",
                {"issue_id": "issue_001", "summary": "Kira needs time before talking.", "status": "open"},
            )
            self.assertEqual(len(updated["unresolved_issues"]), 1)

    def test_relationship_event_delta_is_bounded(self) -> None:
        event = {
            "event_id": "event_too_big",
            "relationship_id": "rel_kira_lisa_test",
            "event_type": "repair",
            "participants": ["kira", "lisa"],
            "privacy": {"level": "private"},
            "emotional_effect": {"primary_effect": "relief"},
            "suggested_metric_changes": {"trust": 0.5},
            "relationship_update_policy": {
                "creates_romance": False,
                "creates_intimacy": False,
                "requires_review_before_apply": False,
            },
            "status": "reviewed",
        }
        errors = validate_relationship_event(event)
        self.assertTrue(any("exceeds max event delta" in error for error in errors))

    def test_apply_relationship_event(self) -> None:
        with TemporaryDirectory() as tmpdir:
            manager = RelationshipStateManager(Path(tmpdir) / "relationships.json")
            manager.add_state(sample_state())
            event = {
                "event_id": "event_repair",
                "relationship_id": "rel_kira_lisa_test",
                "event_type": "repair",
                "participants": ["kira", "lisa"],
                "privacy": {"level": "private"},
                "emotional_effect": {"primary_effect": "relief"},
                "suggested_metric_changes": {"trust": 0.03, "conflict_level": -0.1},
                "relationship_update_policy": {
                    "creates_romance": False,
                    "creates_intimacy": False,
                    "requires_review_before_apply": False,
                },
                "resulting_tone": "repairing",
                "status": "reviewed",
            }
            updated = manager.apply_event(event)
            self.assertAlmostEqual(updated["metrics"]["trust"], 0.73)
            self.assertAlmostEqual(updated["metrics"]["conflict_level"], 0.1)
            self.assertIn("event_repair", updated["linked_records"])
            self.assertEqual(updated["recent_emotional_tone"], "repairing")


if __name__ == "__main__":
    unittest.main()
