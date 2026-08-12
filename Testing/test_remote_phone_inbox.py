import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from daily_life_manager import DailyLifeManager  # noqa: E402

from remote_phone_inbox import (  # noqa: E402
    export_inbox_snapshot,
    render_event,
    render_inbox,
    send_text,
    set_response,
)
from validate_remote_contact_event import validate_remote_contact_event  # noqa: E402


class RemotePhoneInboxTests(unittest.TestCase):
    def test_send_and_render_inbox(self) -> None:
        with TemporaryDirectory() as tmpdir:
            events_dir = Path(tmpdir)
            event = send_text(
                to="kira",
                message="Phone inbox smoke test.",
                reason="test",
                events_dir=events_dir,
            )

            self.assertEqual(validate_remote_contact_event(event), [])
            inbox = render_inbox(events_dir)
            self.assertIn("Kira/Lisa Phone", inbox)
            self.assertIn("Robert -> Kira", inbox)
            self.assertIn("Phone inbox smoke test.", inbox)

    def test_read_by_inbox_number(self) -> None:
        with TemporaryDirectory() as tmpdir:
            events_dir = Path(tmpdir)
            send_text(to="lisa", message="Read this by number.", events_dir=events_dir)

            rendered = render_event("1", events_dir)

            self.assertIn("From: Robert", rendered)
            self.assertIn("To: Lisa", rendered)
            self.assertIn("Read this by number.", rendered)

    def test_reply_updates_event(self) -> None:
        with TemporaryDirectory() as tmpdir:
            events_dir = Path(tmpdir)
            send_text(to="kira_lisa", message="Group reply test.", events_dir=events_dir)

            updated = set_response(
                selector="1",
                response_state="replied",
                reply_message="Group reply received.",
                events_dir=events_dir,
            )

            self.assertEqual(validate_remote_contact_event(updated), [])
            self.assertEqual(updated["response_state"], "replied")
            self.assertIn("Group reply received.", render_event("1", events_dir))

    def test_snapshot_marks_phone_and_video_future(self) -> None:
        with TemporaryDirectory() as tmpdir:
            events_dir = Path(tmpdir)
            send_text(to="kira", message="Snapshot test.", events_dir=events_dir)

            snapshot = export_inbox_snapshot(events_dir)

            self.assertEqual(snapshot["mode"], "pre_gpu_text_only")
            self.assertEqual(snapshot["available_buttons"], ["Text"])
            self.assertIn("Phone", snapshot["future_buttons"])
            self.assertIn("Video Chat", snapshot["future_buttons"])
            self.assertIn("daily_life_availability", snapshot)
            self.assertIn("kira", snapshot["daily_life_availability"])

    def test_send_text_marks_delayed_when_recipient_is_locked_private(self) -> None:
        with TemporaryDirectory() as tmpdir:
            events_dir = Path(tmpdir) / "events"
            manager = DailyLifeManager(state_dir=Path(tmpdir) / "states", log_dir=Path(tmpdir) / "logs")
            manager.set_state(
                "kira",
                cycle_state="private",
                mood="angry",
                intensity=0.8,
                activity_type="private_time",
                public_summary="Kira is taking private time.",
                privacy_level="locked_private",
                robert_visibility="status_only",
                interruptibility="low",
            )

            event = send_text(
                to="kira",
                message="Are you there?",
                events_dir=events_dir,
                daily_life_manager=manager,
            )

            self.assertEqual(validate_remote_contact_event(event), [])
            self.assertEqual(event["response_state"], "delayed")
            self.assertIn("recipient_daily_life_availability", event)
            self.assertEqual(
                event["recipient_daily_life_availability"]["kira"]["recommendation"],
                "delay_or_ignore",
            )


if __name__ == "__main__":
    unittest.main()
