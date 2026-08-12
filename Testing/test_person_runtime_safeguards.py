import tempfile
import unittest
from pathlib import Path

from Core.person_runtime_safeguards import (
    apply_activity_choice,
    ground_claim,
    interpret_interpersonal_request,
    verify_artifact_claim,
)


class PersonRuntimeSafeguardTests(unittest.TestCase):
    def test_artifact_claim_fails_closed_and_verifies_hash(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "actual.md"
            self.assertFalse(verify_artifact_claim(path)["claim_allowed"])
            path.write_text("real content", encoding="utf-8")
            wrong = verify_artifact_claim(path, expected_name="claimed.csv")
            self.assertFalse(wrong["verified"])
            good = verify_artifact_claim(path, expected_name="actual.md")
            self.assertTrue(good["verified"])
            self.assertEqual(len(good["sha256"]), 64)

    def test_claim_requires_source_and_keeps_runtime_truth_separate(self):
        row = ground_claim("I remember it clearly.", selected_timeline="1894")
        self.assertEqual(row["status"], "unverified")
        self.assertFalse(row["first_person_memory_allowed"])
        self.assertFalse(row["runtime_truth_changed"])
        supported = ground_claim(
            "Known fact",
            sources=[{"supports": True, "citation": "reviewed local source"}],
        )
        self.assertTrue(supported["certainty_allowed"])

    def test_activity_can_stop_and_change_without_forced_loop(self):
        state = {"current_activity": "robotics work", "active": True}
        stopped = apply_activity_choice(state, "stop_activity", chosen_by_person=True)
        self.assertEqual(stopped["execution_status"], "stopped")
        self.assertIsNone(stopped["current_activity"])
        changed = apply_activity_choice(
            state, "change_activity", chosen_by_person=True, replacement_activity="listen to music"
        )
        self.assertEqual(changed["current_activity"], "listen to music")

    def test_interpersonal_request_never_directly_controls_other_body(self):
        row = interpret_interpersonal_request(
            "Kira, can you shut the door?",
            requested_by="Peter Parker",
            context_targets=["entry door"],
        )
        self.assertEqual(row["addressed_to"], "Kira")
        self.assertEqual(row["requested_by"], "Peter Parker")
        self.assertIsNone(row["performed_by"])
        self.assertEqual(row["consent_or_choice"], "pending_addressed_person_choice")
        self.assertFalse(row["requester_directly_controls_actor"])


if __name__ == "__main__":
    unittest.main()
