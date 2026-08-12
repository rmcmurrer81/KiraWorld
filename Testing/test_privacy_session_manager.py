import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
sys.path.insert(0, str(CORE_ROOT))

from privacy_session_manager import PrivacySessionManager, validate_privacy_session  # noqa: E402


class PrivacySessionManagerTests(unittest.TestCase):
    def test_privacy_session_state_validates(self) -> None:
        path = PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json"
        sessions = json.loads(path.read_text(encoding="utf-8"))
        for session in sessions:
            with self.subTest(session=session["session_id"]):
                self.assertEqual(validate_privacy_session(session), [])

    def test_locked_room_denies_unlisted_participant(self) -> None:
        with TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "privacy.json"
            state_file.write_text(json.dumps([
                {
                    "session_id": "locked_kira_room",
                    "session_type": "locked_door_private",
                    "status": "active",
                    "owner": "kira",
                    "participants": ["kira"],
                    "door_state": "locked",
                    "allowed_participants": ["kira"],
                    "denied_participants": ["real_robert"],
                    "observers_allowed": False,
                    "entry_requests": [],
                    "door_messages": [],
                    "sharing_scope": "none",
                    "content_logging": {
                        "metadata_allowed": True,
                        "content_allowed": False,
                        "safe_summary_allowed": False,
                    },
                    "related_records": [],
                }
            ]), encoding="utf-8")
            manager = PrivacySessionManager(state_file)
            self.assertTrue(manager.can_access("locked_kira_room", "kira"))
            self.assertFalse(manager.can_access("locked_kira_room", "real_robert"))

    def test_doorbell_request_does_not_grant_access(self) -> None:
        with TemporaryDirectory() as tmpdir:
            source = PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json"
            state_file = Path(tmpdir) / "privacy.json"
            state_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            manager = PrivacySessionManager(state_file)
            updated = manager.add_entry_request(
                "privacy_session_kira_locked_room_template",
                "real_robert",
                "Robert wants to talk.",
            )
            self.assertEqual(updated["door_state"], "doorbell_pending")
            self.assertFalse(manager.can_access("privacy_session_kira_locked_room_template", "real_robert"))

    def test_owner_can_approve_entry_after_doorbell(self) -> None:
        with TemporaryDirectory() as tmpdir:
            source = PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json"
            state_file = Path(tmpdir) / "privacy.json"
            state_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            manager = PrivacySessionManager(state_file)
            manager.request_entry("privacy_session_kira_locked_room_template", "real_robert", "Robert wants to talk.")
            updated = manager.approve_entry(
                "privacy_session_kira_locked_room_template",
                "real_robert",
                approved_by="kira",
            )
            self.assertIn("real_robert", updated["participants"])
            self.assertIn("real_robert", updated["allowed_participants"])
            self.assertNotIn("real_robert", updated["denied_participants"])
            self.assertTrue(manager.can_access("privacy_session_kira_locked_room_template", "real_robert"))

    def test_non_owner_cannot_approve_entry(self) -> None:
        with TemporaryDirectory() as tmpdir:
            source = PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json"
            state_file = Path(tmpdir) / "privacy.json"
            state_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            manager = PrivacySessionManager(state_file)
            manager.request_entry("privacy_session_lisa_doctor_ai_template", "real_robert", "Robert asks.")
            with self.assertRaises(PermissionError):
                manager.approve_entry(
                    "privacy_session_lisa_doctor_ai_template",
                    "real_robert",
                    approved_by="real_robert",
                )

    def test_owner_can_deny_entry_without_revealing_content(self) -> None:
        with TemporaryDirectory() as tmpdir:
            source = PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json"
            state_file = Path(tmpdir) / "privacy.json"
            state_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            manager = PrivacySessionManager(state_file)
            manager.request_entry("privacy_session_lisa_doctor_ai_template", "real_robert", "Robert asks.")
            updated = manager.deny_entry(
                "privacy_session_lisa_doctor_ai_template",
                "real_robert",
                denied_by="lisa",
                reason="not ready to share",
            )
            self.assertIn("real_robert", updated["denied_participants"])
            self.assertFalse(manager.can_access("privacy_session_lisa_doctor_ai_template", "real_robert"))
            self.assertFalse(updated["content_logging"]["content_allowed"])

    def test_doctor_ai_session_does_not_share_details_with_robert(self) -> None:
        manager = PrivacySessionManager(PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json")
        session_id = "privacy_session_lisa_doctor_ai_template"
        self.assertFalse(manager.can_access(session_id, "real_robert"))
        self.assertFalse(manager.safe_summary_allowed(session_id, "real_robert"))

    def test_memory_reconstruction_safe_summary_without_full_replay(self) -> None:
        manager = PrivacySessionManager(PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json")
        session_id = "privacy_session_college_memory_non_intimate_lead_in_template"
        self.assertFalse(manager.can_access(session_id, "real_robert"))
        self.assertTrue(manager.safe_summary_allowed(session_id, "real_robert"))

    def test_lock_unlock_and_end_session(self) -> None:
        with TemporaryDirectory() as tmpdir:
            source = PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json"
            state_file = Path(tmpdir) / "privacy.json"
            state_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            manager = PrivacySessionManager(state_file)
            session_id = "privacy_session_robert_kira_default_chat"
            locked = manager.lock_session(session_id, "kira")
            self.assertEqual(locked["door_state"], "locked")
            unlocked = manager.unlock_session(session_id, "kira")
            self.assertEqual(unlocked["door_state"], "open")
            ended = manager.end_session(session_id, "kira", safe_summary="Robert and Kira talked.")
            self.assertEqual(ended["status"], "ended")
            self.assertFalse(ended["content_logging"]["content_allowed"])
            self.assertEqual(ended["safe_summary"], "Robert and Kira talked.")

    def test_ending_private_session_withholds_summary_when_not_allowed(self) -> None:
        with TemporaryDirectory() as tmpdir:
            source = PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json"
            state_file = Path(tmpdir) / "privacy.json"
            state_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            manager = PrivacySessionManager(state_file)
            ended = manager.end_session(
                "privacy_session_lisa_doctor_ai_template",
                "lisa",
                safe_summary="Private clinical content.",
            )
            self.assertEqual(ended["status"], "ended")
            self.assertEqual(ended["safe_summary"], "withheld")
            self.assertFalse(ended["content_logging"]["content_allowed"])

    def test_leave_door_message_does_not_grant_access(self) -> None:
        with TemporaryDirectory() as tmpdir:
            source = PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json"
            state_file = Path(tmpdir) / "privacy.json"
            state_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            manager = PrivacySessionManager(state_file)
            updated = manager.leave_door_message(
                "privacy_session_kira_locked_room_template",
                "real_robert",
                "I'm sorry. I pushed too hard. I'll give you space.",
            )
            self.assertEqual(updated["door_state"], "locked")
            self.assertFalse(manager.can_access("privacy_session_kira_locked_room_template", "real_robert"))
            self.assertEqual(updated["door_messages"][0]["status"], "unread")
            self.assertFalse(updated["door_messages"][0]["trusted_memory"])
            self.assertFalse(updated["door_messages"][0]["grants_access"])

    def test_owner_can_read_door_message_without_unlocking(self) -> None:
        with TemporaryDirectory() as tmpdir:
            source = PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json"
            state_file = Path(tmpdir) / "privacy.json"
            state_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            manager = PrivacySessionManager(state_file)
            manager.leave_door_message("privacy_session_kira_locked_room_template", "real_robert", "I want to talk.")
            messages = manager.read_door_messages("privacy_session_kira_locked_room_template", "kira")
            session = manager.get_session("privacy_session_kira_locked_room_template")
            self.assertEqual(messages[0]["status"], "read")
            self.assertEqual(session["door_state"], "locked")
            self.assertFalse(manager.can_access("privacy_session_kira_locked_room_template", "real_robert"))

    def test_non_owner_cannot_read_door_messages(self) -> None:
        with TemporaryDirectory() as tmpdir:
            source = PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json"
            state_file = Path(tmpdir) / "privacy.json"
            state_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            manager = PrivacySessionManager(state_file)
            manager.leave_door_message("privacy_session_lisa_doctor_ai_template", "real_robert", "I hope you're okay.")
            with self.assertRaises(PermissionError):
                manager.read_door_messages("privacy_session_lisa_doctor_ai_template", "real_robert")

    def test_kira_can_ring_roberts_locked_door_without_access(self) -> None:
        with TemporaryDirectory() as tmpdir:
            source = PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json"
            state_file = Path(tmpdir) / "privacy.json"
            state_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            manager = PrivacySessionManager(state_file)
            updated = manager.request_entry(
                "privacy_session_robert_locked_room_template",
                "kira",
                "Kira wants to check whether Robert is okay.",
            )
            self.assertEqual(updated["door_state"], "doorbell_pending")
            self.assertFalse(manager.can_access("privacy_session_robert_locked_room_template", "kira"))
            self.assertEqual(updated["entry_requests"][0]["requester"], "kira")

    def test_lisa_can_leave_robert_a_door_message_without_unlocking(self) -> None:
        with TemporaryDirectory() as tmpdir:
            source = PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json"
            state_file = Path(tmpdir) / "privacy.json"
            state_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            manager = PrivacySessionManager(state_file)
            updated = manager.leave_door_message(
                "privacy_session_robert_locked_room_template",
                "lisa",
                "I will give you privacy. I am here if you want to talk later.",
            )
            self.assertEqual(updated["door_state"], "locked")
            self.assertFalse(manager.can_access("privacy_session_robert_locked_room_template", "lisa"))
            self.assertEqual(updated["door_messages"][0]["status"], "unread")
            self.assertFalse(updated["door_messages"][0]["trusted_memory"])
            self.assertFalse(updated["door_messages"][0]["grants_access"])

    def test_robert_can_read_and_answer_door_message_without_unlocking(self) -> None:
        with TemporaryDirectory() as tmpdir:
            source = PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json"
            state_file = Path(tmpdir) / "privacy.json"
            state_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            manager = PrivacySessionManager(state_file)
            updated = manager.leave_door_message("privacy_session_robert_locked_room_template", "kira", "I hope you are okay.")
            message_id = updated["door_messages"][0]["message_id"]
            messages = manager.read_door_messages("privacy_session_robert_locked_room_template", "real_robert")
            self.assertEqual(messages[0]["status"], "read")
            responded = manager.respond_to_door_message(
                "privacy_session_robert_locked_room_template",
                "real_robert",
                message_id,
                "I read it. I still want privacy, but thank you.",
            )
            self.assertEqual(responded["door_state"], "locked")
            self.assertFalse(manager.can_access("privacy_session_robert_locked_room_template", "kira"))
            self.assertEqual(responded["door_messages"][0]["status"], "responded")

    def test_robert_temp_ai_owner_locked_session_denies_kira_and_lisa(self) -> None:
        manager = PrivacySessionManager(PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json")
        session_id = "privacy_session_robert_temp_ai_owner_locked_template"
        self.assertTrue(manager.can_access(session_id, "real_robert"))
        self.assertTrue(manager.can_access(session_id, "temporary_ai_private_instance"))
        self.assertFalse(manager.can_access(session_id, "kira"))
        self.assertFalse(manager.can_access(session_id, "lisa"))

    def test_owner_can_respond_to_door_message_without_unlocking(self) -> None:
        with TemporaryDirectory() as tmpdir:
            source = PROJECT_ROOT / "Data" / "privacy" / "privacy_session_state.json"
            state_file = Path(tmpdir) / "privacy.json"
            state_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            manager = PrivacySessionManager(state_file)
            updated = manager.leave_door_message("privacy_session_kira_locked_room_template", "real_robert", "I'm sorry.")
            message_id = updated["door_messages"][0]["message_id"]
            responded = manager.respond_to_door_message(
                "privacy_session_kira_locked_room_template",
                "kira",
                message_id,
                "I read it. I'm still upset, but I appreciate the message.",
            )
            message = responded["door_messages"][0]
            self.assertEqual(message["status"], "responded")
            self.assertIn("still upset", message["response"])
            self.assertEqual(responded["door_state"], "locked")

    def test_private_content_logging_is_rejected(self) -> None:
        session = {
            "session_id": "bad_private_logging",
            "session_type": "doctor_ai_private",
            "status": "active",
            "owner": "lisa",
            "participants": ["lisa", "doctor_ai"],
            "door_state": "locked",
            "allowed_participants": ["lisa", "doctor_ai"],
            "denied_participants": [],
            "observers_allowed": False,
            "entry_requests": [],
            "door_messages": [],
            "sharing_scope": "none",
            "content_logging": {
                "metadata_allowed": True,
                "content_allowed": True,
                "safe_summary_allowed": False,
            },
            "related_records": [],
        }
        errors = validate_privacy_session(session)
        self.assertTrue(any("must not log private content" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
