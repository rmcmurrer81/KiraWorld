import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from remote_contact_simulator import build_remote_text_event, update_response, write_event  # noqa: E402
from validate_remote_contact_event import validate_remote_contact_event  # noqa: E402


class RemoteContactSimulatorTests(unittest.TestCase):
    def test_robert_to_kira_text_event_validates(self) -> None:
        event = build_remote_text_event(
            initiator="real_robert",
            recipient="kira",
            message="I made it to Los Angeles. Text me when you want to talk.",
            reason="travel_check_in",
        )

        self.assertEqual(validate_remote_contact_event(event), [])
        self.assertEqual(event["direction"], "robert_to_ai")
        self.assertEqual(event["channel"], "pre_gpu_text_message")
        self.assertEqual(event["response_state"], "waiting")
        self.assertIn("message_text", event)

    def test_group_text_uses_group_channel(self) -> None:
        event = build_remote_text_event(
            initiator="real_robert",
            recipient="kira_lisa",
            message="Group text test for Kira and Lisa.",
        )

        self.assertEqual(validate_remote_contact_event(event), [])
        self.assertEqual(event["channel"], "pre_gpu_group_text")

    def test_private_text_does_not_store_exact_message(self) -> None:
        event = build_remote_text_event(
            initiator="kira",
            recipient="real_robert",
            message="This exact text should stay sealed in the simulator event.",
            private=True,
        )

        self.assertEqual(validate_remote_contact_event(event), [])
        self.assertNotIn("message_text", event)
        self.assertTrue(event["message_text_sealed"])
        self.assertIn("sealed", event["message_summary"])

    def test_update_response_writes_valid_event(self) -> None:
        with TemporaryDirectory() as tmpdir:
            events_dir = Path(tmpdir)
            event = build_remote_text_event(
                initiator="lisa",
                recipient="real_robert",
                message="I am checking in.",
            )
            write_event(event, events_dir)

            updated = update_response(
                event_id=event["event_id"],
                response_state="replied",
                reply_message="I got your text.",
                events_dir=events_dir,
            )

            self.assertEqual(validate_remote_contact_event(updated), [])
            self.assertEqual(updated["delivery_state"], "read")
            self.assertEqual(updated["response_state"], "replied")
            self.assertIn("reply_text", updated)


if __name__ == "__main__":
    unittest.main()
