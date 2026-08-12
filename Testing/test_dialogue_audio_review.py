import copy
import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path

from Core.artifact_binding import bind_artifact_hashes, sha256_file
from Core.dialogue_audio_review import review_dialogue_wav
from Core.dialogue_privacy import prepare_dialogue_speech_turns
from Core.dialogue_tts import prepare_tts_turns


def _write_silent_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * 1600)


def _write_empty_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"")


class DialogueAudioReviewTests(unittest.TestCase):
    def test_old_unbound_contaminated_render_is_quarantined(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "dialogue.json"
            wav = root / "old.wav"
            data = {"turns": [{
                "turn": 1,
                "speaker": "Kira",
                "spoken": "Hello.\nPRIVATE MIND:\nsecret\nTRUTH FLAGS:\nconfirmed",
                "raw": "SPOKEN:\nHello.\nPRIVATE MIND:\nsecret\nTRUTH FLAGS:\nconfirmed",
            }]}
            source.write_text(json.dumps(data), encoding="utf-8")
            _write_silent_wav(wav)
            report = review_dialogue_wav(
                source_path=source,
                source_data=data,
                wav_path=wav,
                manifest={"wav_sha256": sha256_file(wav)},
            )
            self.assertEqual("quarantined_do_not_play", report["status"])
            self.assertIn(
                "stored_spoken_fields_contain_private_channel_markers",
                report["reasons"],
            )

    def test_bound_spoken_only_render_is_verified(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "spoken.json"
            wav = root / "safe.wav"
            data = {"turns": [{"turn": 1, "speaker": "Robert", "spoken": "Hello."}]}
            source.write_text(json.dumps(data), encoding="utf-8")
            _write_silent_wav(wav)
            _, audit = prepare_dialogue_speech_turns(data)
            artifacts = {
                "source_dialogue": sha256_file(source),
                "spoken_payload": audit["spoken_payload_sha256"],
                "output_wav": sha256_file(wav),
            }
            binding = bind_artifact_hashes(
                artifacts,
                metadata={
                    "voice_mode": "test",
                    "turn_count": 1,
                    "last_turns": 0,
                    "max_chars_per_turn": 0,
                },
            )
            manifest = {
                "privacy_audit": audit,
                "private_channels_spoken": False,
                "source_dialogue_sha256": sha256_file(source),
                "wav_sha256": sha256_file(wav),
                "turn_count": 1,
                "last_turns": 0,
                "max_chars_per_turn": 0,
                "artifact_binding": binding,
            }
            report = review_dialogue_wav(
                source_path=source,
                source_data=data,
                wav_path=wav,
                manifest=manifest,
            )
            self.assertEqual(
                "manifest_bound_listening_copy_not_acoustically_verified",
                report["status"],
            )
            self.assertFalse(report["acoustic_speech_content_verified"])

    def test_bound_last_turn_selection_is_accepted_and_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "spoken.json"
            wav = root / "excerpt.wav"
            data = {
                "turns": [
                    {"turn": 1, "speaker": "Kira", "spoken": "First."},
                    {"turn": 2, "speaker": "Robert", "spoken": "Second."},
                    {"turn": 3, "speaker": "Kira", "spoken": "Third."},
                ]
            }
            source.write_text(json.dumps(data), encoding="utf-8")
            _write_silent_wav(wav)
            _, audit = prepare_dialogue_speech_turns(data, last_turns=2)
            artifacts = {
                "source_dialogue": sha256_file(source),
                "spoken_payload": audit["spoken_payload_sha256"],
                "output_wav": sha256_file(wav),
            }
            binding = bind_artifact_hashes(
                artifacts,
                metadata={
                    "voice_mode": "test",
                    "turn_count": 2,
                    "last_turns": 2,
                    "max_chars_per_turn": 0,
                },
            )
            manifest = {
                "privacy_audit": audit,
                "private_channels_spoken": False,
                "source_dialogue_sha256": sha256_file(source),
                "wav_sha256": sha256_file(wav),
                "turn_count": 2,
                "last_turns": 2,
                "max_chars_per_turn": 0,
                "artifact_binding": binding,
            }
            accepted = review_dialogue_wav(
                source_path=source,
                source_data=data,
                wav_path=wav,
                manifest=manifest,
            )
            self.assertEqual(
                "manifest_bound_listening_copy_not_acoustically_verified",
                accepted["status"],
            )

            manifest["last_turns"] = 1
            rejected = review_dialogue_wav(
                source_path=source,
                source_data=data,
                wav_path=wav,
                manifest=manifest,
            )
            self.assertEqual("quarantined_do_not_play", rejected["status"])

    def test_empty_wav_is_quarantined_even_when_manifest_is_bound(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "spoken.json"
            wav = root / "empty.wav"
            data = {"turns": [{"turn": 1, "speaker": "Robert", "spoken": "Hello."}]}
            source.write_text(json.dumps(data), encoding="utf-8")
            _write_empty_wav(wav)
            _, audit = prepare_dialogue_speech_turns(data)
            artifacts = {
                "source_dialogue": sha256_file(source),
                "spoken_payload": audit["spoken_payload_sha256"],
                "output_wav": sha256_file(wav),
            }
            manifest = {
                "privacy_audit": audit,
                "private_channels_spoken": False,
                "source_dialogue_sha256": sha256_file(source),
                "wav_sha256": sha256_file(wav),
                "turn_count": 1,
                "last_turns": 0,
                "max_chars_per_turn": 0,
                "artifact_binding": bind_artifact_hashes(
                    artifacts,
                    metadata={
                        "voice_mode": "test",
                        "turn_count": 1,
                        "last_turns": 0,
                        "max_chars_per_turn": 0,
                    },
                ),
            }
            report = review_dialogue_wav(
                source_path=source,
                source_data=data,
                wav_path=wav,
                manifest=manifest,
            )
            self.assertEqual("quarantined_do_not_play", report["status"])
            self.assertIn("wav_has_no_audio_frames", report["reasons"])

    def test_name_omitting_tts_payload_is_reconstructed_and_bound(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "spoken.json"
            wav = root / "safe.wav"
            data = {"turns": [
                {"turn": 1, "speaker": "Kira", "spoken": "Hello Robert, Kira has an idea."},
                {"turn": 2, "speaker": "Robert", "spoken": "I hear you, Kira."},
            ]}
            source.write_text(json.dumps(data), encoding="utf-8")
            _write_silent_wav(wav)
            prepared, privacy_audit = prepare_dialogue_speech_turns(data)
            _, tts_audit = prepare_tts_turns(prepared, omit_names=True)
            artifacts = {
                "source_dialogue": sha256_file(source),
                "spoken_payload": privacy_audit["spoken_payload_sha256"],
                "tts_payload": tts_audit["tts_payload_sha256"],
                "output_wav": sha256_file(wav),
            }
            manifest = {
                "privacy_audit": privacy_audit,
                "tts_audit": tts_audit,
                "dialogue_names_spoken": False,
                "speak_speaker_names": False,
                "private_channels_spoken": False,
                "source_dialogue_sha256": sha256_file(source),
                "wav_sha256": sha256_file(wav),
                "turn_count": 2,
                "last_turns": 0,
                "max_chars_per_turn": 0,
                "artifact_binding": bind_artifact_hashes(
                    artifacts,
                    metadata={
                        "voice_mode": "test",
                        "turn_count": 2,
                        "last_turns": 0,
                        "max_chars_per_turn": 0,
                    },
                ),
            }
            accepted = review_dialogue_wav(
                source_path=source,
                source_data=data,
                wav_path=wav,
                manifest=manifest,
            )
            self.assertEqual(
                "manifest_bound_listening_copy_not_acoustically_verified",
                accepted["status"],
            )
            self.assertFalse(accepted["fresh_tts_audit"]["dialogue_names_spoken"])
            self.assertTrue(accepted["fresh_tts_audit"]["non_name_word_coverage_exact"])

            manifest["tts_audit"] = dict(tts_audit)
            manifest["tts_audit"]["tts_payload_sha256"] = "0" * 64
            rejected = review_dialogue_wav(
                source_path=source,
                source_data=data,
                wav_path=wav,
                manifest=manifest,
            )
            self.assertEqual("quarantined_do_not_play", rejected["status"])

    def test_acoustic_sanity_records_and_settings_are_hash_bound(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "spoken.json"
            wav = root / "safe.wav"
            data = {"turns": [{"turn": 1, "speaker": "Robert", "spoken": "A complete public sentence."}]}
            source.write_text(json.dumps(data), encoding="utf-8")
            _write_silent_wav(wav)
            prepared, privacy_audit = prepare_dialogue_speech_turns(data)
            _, tts_audit = prepare_tts_turns(prepared, omit_names=True)
            generated = [{
                "index": 1,
                "speaker": "Robert",
                "chunks": 1,
                "chunk_generation": [{
                    "chunk_index": 1,
                    "chunk_text_sha256": hashlib.sha256(
                        "A complete public sentence.".encode("utf-8")
                    ).hexdigest(),
                    "attempt_count": 1,
                    "accepted_attempt": 1,
                    "sanity_attempts": [{
                        "attempt": 1,
                        "passed": True,
                        "duration_seconds": 1.2,
                        "minimum_plausible_duration_seconds": 0.56,
                        "reasons": [],
                    }],
                }],
            }]
            generation_sha = hashlib.sha256(
                json.dumps(generated, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            artifacts = {
                "source_dialogue": sha256_file(source),
                "spoken_payload": privacy_audit["spoken_payload_sha256"],
                "tts_payload": tts_audit["tts_payload_sha256"],
                "generation_sanity": generation_sha,
                "output_wav": sha256_file(wav),
            }
            metadata = {
                "voice_mode": "test",
                "turn_count": 1,
                "last_turns": 0,
                "max_chars_per_turn": 0,
                "chunk_chars": 180,
                "chunk_max_attempts": 2,
                "min_seconds_per_word": 0.14,
            }
            manifest = {
                "privacy_audit": privacy_audit,
                "tts_audit": tts_audit,
                "dialogue_names_spoken": False,
                "speak_speaker_names": False,
                "private_channels_spoken": False,
                "source_dialogue_sha256": sha256_file(source),
                "wav_sha256": sha256_file(wav),
                "turn_count": 1,
                "last_turns": 0,
                "max_chars_per_turn": 0,
                "chunk_chars": 180,
                "chunk_max_attempts": 2,
                "acoustic_sanity_gate": {
                    "status": "passed_all_chunks",
                    "scope": "non_silent_pcm_and_conservative_duration_per_queued_word_not_asr_verified",
                    "min_seconds_per_word": 0.14,
                    "max_attempts_per_chunk": 2,
                    "asr_word_coverage_verified": False,
                    "human_listening_verified": False,
                },
                "generation_sanity_sha256": generation_sha,
                "generated": generated,
                "artifact_binding": bind_artifact_hashes(artifacts, metadata=metadata),
            }
            accepted = review_dialogue_wav(
                source_path=source,
                source_data=data,
                wav_path=wav,
                manifest=manifest,
            )
            self.assertEqual(
                "manifest_bound_listening_copy_not_acoustically_verified",
                accepted["status"],
            )

            changed_setting = copy.deepcopy(manifest)
            changed_setting["acoustic_sanity_gate"]["min_seconds_per_word"] = 0.10
            rejected_setting = review_dialogue_wav(
                source_path=source,
                source_data=data,
                wav_path=wav,
                manifest=changed_setting,
            )
            self.assertEqual("quarantined_do_not_play", rejected_setting["status"])

            changed_record = copy.deepcopy(manifest)
            changed_record["generated"][0]["chunk_generation"][0]["sanity_attempts"][0]["duration_seconds"] = 0.9
            rejected_record = review_dialogue_wav(
                source_path=source,
                source_data=data,
                wav_path=wav,
                manifest=changed_record,
            )
            self.assertEqual("quarantined_do_not_play", rejected_record["status"])


if __name__ == "__main__":
    unittest.main()
