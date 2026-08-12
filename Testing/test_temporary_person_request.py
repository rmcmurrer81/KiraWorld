import tempfile
import unittest
from pathlib import Path

from Core.temporary_person_request import REQUIRED_RECORDS, build_request, save_request


class TemporaryPersonRequestTests(unittest.TestCase):
    def test_ambiguous_character_request_asks_instead_of_guessing(self):
        result = build_request(
            requested_by={"person_id": "kira", "person_kind": "permanent_resident", "authorized": True},
            request_type="fictional_character",
            request_text="I would like Ladybug.",
        )
        self.assertEqual("needs_clarification", result["status"])
        self.assertFalse(result["activation_allowed"])
        self.assertTrue(result["clarifications_needed"])
        self.assertEqual(set(REQUIRED_RECORDS), set(result["records"]))

    def test_complete_expert_request_starts_evidence_pipeline_only(self):
        result = build_request(
            requested_by={"person_id": "robert", "person_kind": "biological_person", "authorized": True},
            request_type="expert",
            request_text="I need someone who knows robotics.",
            details={"expert_domain": "humanoid robotics hardware", "purpose": "research and design review"},
        )
        self.assertEqual("ready_for_evidence_pipeline", result["status"])
        self.assertFalse(result["fabricated_finished_person"])
        self.assertEqual("inactive", result["records"]["activation_state"]["value"])
        self.assertFalse(result["records"]["voice"]["generic_fallback_allowed"])

    def test_unauthorized_requester_is_blocked(self):
        result = build_request(
            requested_by={"person_id": "unknown", "authorized": False},
            request_type="expert",
            request_text="robotics expert",
            details={"expert_domain": "robotics"},
        )
        self.assertEqual("blocked", result["status"])

    def test_save_is_idempotent_for_same_request(self):
        request = build_request(
            requested_by={"person_id": "kira", "authorized": True},
            request_type="expert",
            request_text="robotics expert",
            details={"expert_domain": "robotics"},
        )
        with tempfile.TemporaryDirectory() as folder:
            first = save_request(request, Path(folder))
            second = save_request(request, Path(folder))
            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
