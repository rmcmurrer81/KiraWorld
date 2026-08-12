import json
import tempfile
import unittest
from pathlib import Path

from Core.person_mind_runtime import finalize_person_turn


class PersonMindRuntimeTests(unittest.TestCase):
    def test_only_spoken_is_displayed_and_action_is_not_claimed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = finalize_person_turn(
                person_id="peter_parker",
                person_label="Peter Parker",
                raw_reply='*pauses and smiles* "Give me a second."',
                source_turn_id="turn-1",
                turn_root=root / "turns",
                movement_state_dir=root / "movement",
                movement_audit_path=root / "audit.jsonl",
            )
            self.assertNotIn("pause", result["channels"]["spoken"].lower())
            self.assertNotIn("smile", result["channels"]["spoken"].lower())
            self.assertTrue(result["channels"]["runtime_truth"]["action_requests"])
            self.assertTrue(all(not item["completed"] for item in result["channels"]["runtime_truth"]["action_results"]))
            self.assertIsNone(result["channels"]["private_mind"]["content"])
            saved = json.loads(Path(result["evidence_path"]).read_text(encoding="utf-8"))
            self.assertEqual("spoken", saved["display_contract"]["tts_channel"])

    def test_architecture_is_person_agnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for person in ("ladybug", "emily", "jessica", "holmes", "unrelated_temp_ai", "kira"):
                result = finalize_person_turn(
                    person_id=person,
                    person_label=person,
                    raw_reply="I would rather talk for a while.",
                    source_turn_id=f"{person}-1",
                    turn_root=root,
                    movement_state_dir=root / "movement",
                    movement_audit_path=root / "audit.jsonl",
                )
                self.assertEqual("I would rather talk for a while.", result["channels"]["spoken"])
                self.assertEqual("person_mind_turn_v1", result["schema_version"])

    def test_first_person_stop_intention_is_routed_but_remains_spoken(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = finalize_person_turn(
                person_id="emily",
                person_label="Emily",
                raw_reply="I want to stop working and talk with you for a while.",
                source_turn_id="emily-stop-1",
                turn_root=root,
                movement_state_dir=root / "movement",
                movement_audit_path=root / "audit.jsonl",
            )
            self.assertEqual(
                "I want to stop working and talk with you for a while.",
                result["channels"]["spoken"],
            )
            requests = result["channels"]["runtime_truth"]["action_requests"]
            self.assertEqual(["stop_activity"], [item["action"] for item in requests])
            self.assertEqual(
                "blocked_no_active_controller",
                result["channels"]["runtime_truth"]["action_results"][0]["status"],
            )


if __name__ == "__main__":
    unittest.main()
