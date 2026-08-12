import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core import kira_tablet_messages as tablet_messages  # noqa: E402
from Core.kira_tablet_messages import (  # noqa: E402
    create_voice_message,
    ensure_voice_message_audio,
    queue_tablet_request,
    save_tablet_note,
    set_voice_message_status,
    tablet_workspace_summary,
    voice_message_audio_path,
    voice_message_inbox,
)
from Core.voice_output import VoiceOutputConfig  # noqa: E402


def fake_wav_synthesizer(text, output_path, config=None):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(8000)
        target.writeframes((2000).to_bytes(2, "little", signed=True) * 800)
    return {
        "generated": True,
        "reason": "ok",
        "engine": "test_synthesizer",
        "text": text,
    }


class KiraTabletMessagesTests(unittest.TestCase):
    def test_world_shell_opt_in_preserves_reviewed_target_voice_without_playback(self) -> None:
        candidate = VoiceOutputConfig(
            engine="chatterbox_tts",
            chatterbox_reference_audio="Voice/profiles/kira.wav",
            chatterbox_device="cpu",
            max_chars=450,
            play_audio=True,
        )
        with (
            patch.dict("os.environ", {"KIRA_MESSAGE_TARGET_VOICE": "1"}),
            patch.object(tablet_messages, "load_candidate_voice_config", return_value=candidate),
        ):
            selected = tablet_messages._lightweight_voice_config("kira")

        self.assertEqual(selected.engine, "chatterbox_tts")
        self.assertEqual(selected.chatterbox_reference_audio, candidate.chatterbox_reference_audio)
        self.assertFalse(selected.play_audio)
        self.assertGreaterEqual(selected.max_chars, 4000)

    def test_message_voice_without_shell_opt_in_remains_lightweight_nonplaying_sapi(self) -> None:
        candidate = VoiceOutputConfig(
            engine="chatterbox_tts",
            chatterbox_reference_audio="Voice/profiles/kira.wav",
            play_audio=True,
        )
        with (
            patch.dict("os.environ", {}, clear=False),
            patch.object(tablet_messages, "load_candidate_voice_config", return_value=candidate),
        ):
            import os

            os.environ.pop("KIRA_MESSAGE_TARGET_VOICE", None)
            selected = tablet_messages._lightweight_voice_config("kira")

        self.assertEqual(selected.engine, "windows_sapi_powershell")
        self.assertEqual(selected.chatterbox_reference_audio, "")
        self.assertFalse(selected.play_audio)

    def test_text_backed_message_gets_real_wav_and_stays_unread_until_play_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            messages_dir = Path(tmpdir) / "messages"
            created = create_voice_message(
                "I left you a thought about my story.",
                messages_dir=messages_dir,
                synthesize=False,
            )
            message_id = created["record"]["message_id"]

            result = ensure_voice_message_audio(
                message_id,
                messages_dir=messages_dir,
                synthesizer=fake_wav_synthesizer,
                config=VoiceOutputConfig(engine="windows_sapi_powershell"),
            )
            inbox = voice_message_inbox(messages_dir)

            self.assertTrue(result["audio_ready"])
            self.assertEqual(inbox["unread"], 1)
            self.assertEqual(inbox["messages"][0]["text"], "I left you a thought about my story.")
            self.assertTrue(inbox["messages"][0]["audio_ready"])
            self.assertIsNotNone(voice_message_audio_path(message_id, messages_dir))

            marked = set_voice_message_status(message_id, "read", messages_dir=messages_dir)
            self.assertTrue(marked["ok"])
            self.assertEqual(voice_message_inbox(messages_dir)["unread"], 0)
            saved = json.loads(created["path"].read_text(encoding="utf-8"))
            self.assertIn("played_or_read_at", saved)

    def test_ready_target_voice_message_records_reviewed_reference_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            messages_dir = Path(tmpdir) / "messages"
            created = create_voice_message("This should use the reviewed voice.", messages_dir=messages_dir, synthesize=False)

            def target_voice_synthesizer(text, output_path, config=None):
                result = fake_wav_synthesizer(text, output_path, config=config)
                result.update(
                    {
                        "engine": "chatterbox_tts",
                        "voice_identity_status": "reviewed_reference_chatterbox",
                    }
                )
                return result

            result = ensure_voice_message_audio(
                created["record"]["message_id"],
                messages_dir=messages_dir,
                synthesizer=target_voice_synthesizer,
                config=VoiceOutputConfig(engine="chatterbox_tts"),
            )
            saved = json.loads(created["path"].read_text(encoding="utf-8"))

            self.assertTrue(result["audio_ready"])
            self.assertEqual(saved["audio"]["engine"], "chatterbox_tts")
            self.assertEqual(saved["audio"]["voice_identity_status"], "reviewed_reference_chatterbox")

    def test_failed_synthesis_is_truthfully_blocked_and_preserves_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            messages_dir = Path(tmpdir) / "messages"
            created = create_voice_message("Please read this even if speech is unavailable.", messages_dir=messages_dir, synthesize=False)

            def blocked_synthesizer(text, output_path, config=None):
                return {"generated": False, "reason": "tts_unavailable", "engine": "test"}

            result = ensure_voice_message_audio(
                created["record"]["message_id"],
                messages_dir=messages_dir,
                synthesizer=blocked_synthesizer,
                config=VoiceOutputConfig(),
            )
            saved = json.loads(created["path"].read_text(encoding="utf-8"))

            self.assertFalse(result["audio_ready"])
            self.assertEqual(saved["audio"]["status"], "blocked")
            self.assertEqual(saved["audio"]["reason"], "tts_unavailable")
            self.assertEqual(saved["message"]["message"], "Please read this even if speech is unavailable.")
            self.assertEqual(saved["status"], "unread")

    def test_backend_failure_cannot_promote_riff_shaped_garbage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            messages_dir = Path(tmpdir) / "messages"
            created = create_voice_message("Private-safe text.", messages_dir=messages_dir, synthesize=False)

            def deceptive_backend(text, output_path, config=None):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"RIFF" + (44).to_bytes(4, "little") + b"WAVE" + b"x" * 40)
                return {"generated": False, "reason": "backend_failed"}

            result = ensure_voice_message_audio(
                created["record"]["message_id"],
                messages_dir=messages_dir,
                synthesizer=deceptive_backend,
                config=VoiceOutputConfig(),
            )
            self.assertFalse(result["audio_ready"])
            self.assertIsNone(voice_message_audio_path(created["record"]["message_id"], messages_dir))
            saved = json.loads(created["path"].read_text(encoding="utf-8"))
            self.assertEqual("blocked", saved["audio"]["status"])

    def test_valid_wav_with_truncated_rendered_payload_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            messages_dir = Path(tmpdir) / "messages"
            created = create_voice_message(
                "This full sentence must be represented by the render payload.",
                messages_dir=messages_dir,
                synthesize=False,
            )

            def truncated_backend(text, output_path, config=None):
                fake_wav_synthesizer(text, output_path, config=config)
                return {"generated": True, "reason": "ok", "text": "This full sentence."}

            result = ensure_voice_message_audio(
                created["record"]["message_id"],
                messages_dir=messages_dir,
                synthesizer=truncated_backend,
                config=VoiceOutputConfig(),
            )
            self.assertFalse(result["audio_ready"])
            self.assertEqual("rendered_text_is_missing_or_truncated", result["reason"])

    def test_silent_pcm_cannot_be_promoted_to_ready_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            messages_dir = Path(tmpdir) / "messages"
            created = create_voice_message(
                "This text must not be represented by silence.",
                messages_dir=messages_dir,
                synthesize=False,
            )

            def silent_backend(text, output_path, config=None):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with wave.open(str(output_path), "wb") as target:
                    target.setnchannels(1)
                    target.setsampwidth(2)
                    target.setframerate(8000)
                    target.writeframes(b"\x00\x00" * 800)
                return {"generated": True, "reason": "ok", "text": text}

            result = ensure_voice_message_audio(
                created["record"]["message_id"],
                messages_dir=messages_dir,
                synthesizer=silent_backend,
                config=VoiceOutputConfig(),
            )
            self.assertFalse(result["audio_ready"])
            self.assertEqual("silent_or_near_silent_pcm", result["wav_validation"]["reason"])
            self.assertIsNone(
                voice_message_audio_path(created["record"]["message_id"], messages_dir)
            )

    def test_text_edit_invalidates_old_wav_and_forces_regeneration(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            messages_dir = Path(tmpdir) / "messages"
            created = create_voice_message("First canonical text.", messages_dir=messages_dir, synthesize=False)
            message_id = created["record"]["message_id"]
            ensure_voice_message_audio(
                message_id,
                messages_dir=messages_dir,
                synthesizer=fake_wav_synthesizer,
                config=VoiceOutputConfig(),
            )
            first = json.loads(created["path"].read_text(encoding="utf-8"))
            first_hash = first["audio"]["source_text_sha256"]

            first["message"]["message"] = "Revised canonical text."
            created["path"].write_text(json.dumps(first), encoding="utf-8")
            self.assertIsNone(voice_message_audio_path(message_id, messages_dir))
            self.assertEqual(
                voice_message_inbox(messages_dir)["messages"][0]["audio_status"],
                "stale_or_unverified",
            )

            regenerated = ensure_voice_message_audio(
                message_id,
                messages_dir=messages_dir,
                synthesizer=fake_wav_synthesizer,
                config=VoiceOutputConfig(),
            )
            saved = json.loads(created["path"].read_text(encoding="utf-8"))
            self.assertTrue(regenerated["audio_ready"])
            self.assertNotEqual(saved["audio"]["source_text_sha256"], first_hash)
            self.assertIsNotNone(voice_message_audio_path(message_id, messages_dir))

    def test_message_identifier_cannot_escape_mailbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            messages_dir = Path(tmpdir) / "messages"
            self.assertIsNone(voice_message_audio_path("../../outside", messages_dir))
            self.assertFalse(set_voice_message_status("../../outside", "read", messages_dir=messages_dir)["ok"])

    def test_identity_fields_cannot_escape_configured_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            messages = root / "messages"
            tablet = root / "tablet"
            message = create_voice_message("Hello", subject="../escape", messages_dir=messages, synthesize=False)
            note = save_tablet_note("Note", author="../../escape", tablet_root=tablet)
            request = queue_tablet_request(
                "Question", request_type="online_lookup", requested_by="../../escape", tablet_root=tablet
            )
            self.assertTrue(message["path"].resolve().is_relative_to(messages.resolve()))
            self.assertTrue(note["path"].resolve().is_relative_to(tablet.resolve()))
            self.assertTrue(request["path"].resolve().is_relative_to(tablet.resolve()))
            self.assertFalse((root / "escape").exists())

    def test_tablet_notes_and_requests_are_local_review_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tablet_root = Path(tmpdir) / "tablet"
            note = save_tablet_note(
                "A scene about choosing whether to open a mysterious door.",
                note_kind="creative_writing",
                author="kira",
                requested_by="kira",
                generated_by="kira",
                approved_by_subject=True,
                body_grounding={"physical_tablet_use_proven": True, "held_prop_kind": "tablet"},
                tablet_root=tablet_root,
            )
            lookup = queue_tablet_request(
                "Find a reliable source about door symbolism.",
                request_type="online_lookup",
                requested_by="kira",
                tablet_root=tablet_root,
            )
            reading = queue_tablet_request(
                "Continue the selected local book.",
                request_type="read_local_source",
                requested_by="kira",
                source_hint="local library",
                tablet_root=tablet_root,
            )
            summary = tablet_workspace_summary(tablet_root)

            self.assertTrue(note["record"]["tablet_state"]["physical_tablet_use_proven"])
            self.assertTrue(note["record"]["memory_policy"]["creative_work_not_lived_memory"])
            self.assertTrue(note["record"]["authorship_provenance"]["authorship_claim_allowed"])
            self.assertEqual(lookup["record"]["status"], "pending_robert_review")
            self.assertFalse(lookup["record"]["execution"]["network_access_performed"])
            self.assertEqual(reading["record"]["status"], "pending_local_source_selection")
            self.assertFalse(reading["record"]["execution"]["completion_claim_allowed"])
            self.assertEqual(summary["notes"], 1)
            self.assertEqual(summary["pending_requests"], 2)
            self.assertFalse(summary["online_access_performed_by_queue"])

    def test_unapproved_model_outputs_are_drafts_not_kira_authorship_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            messages = root / "messages"
            tablet = root / "tablet"
            voice = create_voice_message(
                "A generated draft for later review.",
                subject="kira",
                requested_by="supervised_life_loop",
                generated_by="local_model_for_kira",
                approved_by_subject=False,
                messages_dir=messages,
                synthesize=False,
            )
            note = save_tablet_note(
                "Generated story draft.",
                author="kira",
                requested_by="supervised_life_loop",
                generated_by="local_model_for_kira",
                approved_by_subject=False,
                tablet_root=tablet,
            )

            self.assertEqual("local_model_for_kira", voice["record"]["sender"])
            self.assertTrue(voice["record"]["kind"].startswith("unapproved_voice_message_draft"))
            self.assertFalse(
                voice["record"]["authorship_provenance"]["authorship_claim_allowed"]
            )
            inbox_record = voice_message_inbox(messages)["messages"][0]
            self.assertEqual("local_model_for_kira", inbox_record["sender"])
            self.assertFalse(inbox_record["authorship_claim_allowed"])
            self.assertEqual("local_model_for_kira", note["record"]["author"])
            self.assertEqual(
                "kira",
                note["record"]["authorship_provenance"]["claimed_author"],
            )
            self.assertFalse(
                note["record"]["authorship_provenance"]["authorship_claim_allowed"]
            )


if __name__ == "__main__":
    unittest.main()
