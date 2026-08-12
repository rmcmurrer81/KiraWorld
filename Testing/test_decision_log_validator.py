import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from validate_decision_log import validate_decision_log  # noqa: E402


class DecisionLogValidatorTests(unittest.TestCase):
    def test_valid_private_decision_log_passes(self) -> None:
        data = {
            "decision_id": "decision_001",
            "timestamp": "2026-04-25T00:00:00Z",
            "actor": {"actor_id": "lisa", "actor_type": "core_ai"},
            "participants": ["lisa"],
            "decision_type": "privacy",
            "summary": "Lisa kept a private feeling sealed.",
            "reason": "Sharing too early could change an important relationship.",
            "privacy_impact": "sealed_details",
            "outcome": "No private content was disclosed.",
            "visibility": "participants_only",
            "status": "draft",
        }
        self.assertEqual(validate_decision_log(data), [])

    def test_sealed_details_cannot_be_public(self) -> None:
        data = {
            "decision_id": "decision_002",
            "timestamp": "2026-04-25T00:00:00Z",
            "actor": {"actor_id": "kira", "actor_type": "core_ai"},
            "decision_type": "privacy",
            "summary": "Private event.",
            "reason": "Private reason.",
            "privacy_impact": "sealed_details",
            "outcome": "Details sealed.",
            "visibility": "public",
            "status": "draft",
        }
        errors = validate_decision_log(data)
        self.assertTrue(any("cannot be public" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
