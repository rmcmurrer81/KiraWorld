from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from Core.dialogue_tts import split_for_tts, spoken_words
from tools import kira_world_shell_server as shell


def append_jsonl(path: Path, item: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")


class PublicConversationContinuityTests(unittest.TestCase):
    def test_completed_pairs_ignore_current_unanswered_user_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            chat = Path(tmpdir) / "chat.jsonl"
            append_jsonl(chat, {"speaker": "Robert", "to": "kira", "text": "How are you?"})
            append_jsonl(
                chat,
                {
                    "speaker": "Kira",
                    "speaker_id": "kira",
                    "to": "Robert",
                    "text": "I'm thoughtful today.",
                },
            )
            append_jsonl(chat, {"speaker": "Robert", "to": "kira", "text": "How are you now?"})
            with patch.object(shell, "CHAT_LOG", chat):
                pairs = shell._completed_public_chat_pairs("kira", active_label="Kira", limit=8)

        self.assertEqual(pairs, [("How are you?", "I'm thoughtful today.")])

    def test_new_loop_is_seeded_from_durable_public_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            chat = Path(tmpdir) / "chat.jsonl"
            append_jsonl(chat, {"speaker": "Robert", "to": "kira", "text": "Earlier question."})
            append_jsonl(
                chat,
                {"speaker": "Kira", "speaker_id": "kira", "to": "Robert", "text": "Earlier answer."},
            )
            loop = SimpleNamespace(conversation_history=[])
            with patch.object(shell, "CHAT_LOG", chat):
                count = shell._seed_kira_public_history(loop)

        self.assertEqual(count, 1)
        self.assertEqual(
            loop.conversation_history,
            [
                {"role": "user", "content": "Earlier question."},
                {"role": "assistant", "content": "Earlier answer."},
            ],
        )

    def test_exact_repeated_opening_is_detected_and_privately_regenerated(self) -> None:
        repeated = (
            "I'm here, a little quiet, but more myself than I was. I don't want to perform a checklist at you; "
            "I just want to answer honestly."
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            chat = Path(tmpdir) / "chat.jsonl"
            life = Path(tmpdir) / "life.jsonl"
            append_jsonl(chat, {"speaker": "Robert", "to": "kira", "text": "How are you?"})
            append_jsonl(
                chat,
                {"speaker": "Kira", "speaker_id": "kira", "to": "Robert", "text": repeated},
            )

            class FakeLoop:
                def __init__(self) -> None:
                    self.conversation_history = [
                        {"role": "user", "content": "How are you"},
                        {"role": "assistant", "content": repeated},
                    ]

                def build_context(self, prompt: str) -> dict:
                    return {"user_message": prompt}

                def call_model(self, _context: dict) -> str:
                    return "I'm glad you checked in. I feel curious and a little unsettled about where our last talk left us."

            loop = FakeLoop()
            with patch.object(shell, "CHAT_LOG", chat), patch.object(shell, "LIFE_LOOP_LOG", life):
                detected, similarity = shell._kira_reply_repeats_prior_opening("How are you", repeated)
                repaired = shell._repair_kira_cross_session_repeat(loop, "How are you", repeated)

            events = [json.loads(line) for line in life.read_text(encoding="utf-8").splitlines()]

        self.assertTrue(detected)
        self.assertEqual(similarity, 1.0)
        self.assertNotEqual(repaired, repeated)
        self.assertIn("where our last talk left us", repaired)
        self.assertEqual(loop.conversation_history[-1]["content"], repaired)
        self.assertEqual(events[-1]["event"], "conversation_continuity_repair")

    def test_social_checkin_repairs_unasked_old_episode_thread(self) -> None:
        stale = (
            "I've been thinking about the episode and its character development. "
            "The storyline still feels unfinished to me."
        )

        class FakeLoop:
            def process(self, prompt: str) -> str:
                self.prompt = prompt
                return "I'm a little tired, but I'm glad you checked in. How are you doing?"

        loop = FakeLoop()
        repaired = shell._repair_kira_social_tangent(loop, "How are you?", stale, "home", {})

        self.assertNotIn("episode", repaired.lower())
        self.assertNotIn("character development", repaired.lower())
        self.assertIn("glad you checked in", repaired.lower())
        self.assertIn("did not ask about", loop.prompt)

    def test_explicit_episode_question_is_not_treated_as_social_checkin_drift(self) -> None:
        answer = "I think that episode gave the character a more honest turning point."
        repaired = shell._repair_kira_social_tangent(object(), "What did you think of that episode?", answer, "home", {})
        self.assertEqual(repaired, answer)

    def test_social_checkin_about_episode_preserves_requested_topic(self) -> None:
        answer = "I feel unsettled by that episode because the character finally faced what she had avoided."

        class FailIfRegenerated:
            def process(self, _prompt: str) -> str:
                raise AssertionError("an explicitly requested episode topic must not be regenerated")

        repaired = shell._repair_kira_social_tangent(
            FailIfRegenerated(),
            "How are you feeling about that episode?",
            answer,
            "home",
            {},
        )

        self.assertEqual(repaired, answer)

    def test_episode_statement_after_generic_checkin_does_not_disable_repair(self) -> None:
        stale = "I've been thinking about the episode and its character development again."

        class FakeLoop:
            def process(self, _prompt: str) -> str:
                return "I'm tired, but being outside for a moment is helping me settle."

        repaired = shell._repair_kira_social_tangent(
            FakeLoop(),
            "How are you? I watched an episode last night.",
            stale,
            "home",
            {},
        )

        self.assertNotIn("episode", repaired.lower())
        self.assertIn("helping me settle", repaired.lower())

    def test_honest_feeling_script_metaphor_is_not_silenced(self) -> None:
        answer = "I feel off today, almost like I'm following a script instead of finding my own words."
        repaired = shell._repair_kira_social_tangent(object(), "How are you?", answer, "home", {})
        self.assertEqual(repaired, answer)


class LiveSpokenOnlyPayloadTests(unittest.TestCase):
    def test_browser_records_submit_marker_before_snapshot_wait_and_chat_request(self) -> None:
        html = shell.html_shell().decode("utf-8")

        marker = html.index('/api/voice-benchmark/submit')
        snapshot = html.index('persistAvatarSnapshotBeforeChat()', marker)
        chat = html.index('/api/chat', snapshot)
        self.assertLess(marker, snapshot)
        self.assertLess(snapshot, chat)
        self.assertIn('benchmark_request_id: benchmarkCaptureId', html)

    def test_structured_reply_speaks_only_spoken_section_and_keeps_addressed_names(self) -> None:
        raw = (
            "SPOKEN:\nHi Robert, I'm Kira and I remember our last talk.\n\n"
            "PRIVATE_MIND:\nI do not want this private sentence spoken.\n\n"
            "TRUTH_FLAGS:\nThe public statement is subjective."
        )

        payload, audit = shell._live_spoken_only_payload(raw)

        self.assertEqual(spoken_words(payload), ["hi", "robert", "i'm", "kira", "and", "i", "remember", "our", "last", "talk"])
        self.assertNotIn("private sentence", payload.lower())
        self.assertEqual(audit["source_mode"], "explicit_spoken_section_only")
        self.assertEqual(audit["removed_dialogue_name_occurrences"], 0)
        self.assertTrue(audit["non_name_word_coverage_exact"])
        self.assertTrue(audit["public_word_coverage_exact"])
        self.assertTrue(audit["dialogue_names_spoken"])
        self.assertTrue(audit["in_content_names_preserved"])
        self.assertFalse(audit["speaker_labels_spoken"])

    def test_unstructured_public_reply_preserves_every_public_word(self) -> None:
        payload, audit = shell._live_spoken_only_payload("Robert, Kira's complete answer stays intact.")

        self.assertEqual(spoken_words(payload), ["robert", "kira's", "complete", "answer", "stays", "intact"])
        self.assertEqual(audit["removed_dialogue_name_occurrences"], 0)
        self.assertTrue(audit["privacy_safe_for_speech"])

    def test_leading_speaker_label_is_removed_but_addressed_name_is_retained(self) -> None:
        payload, audit = shell._live_spoken_only_payload("Kira: Hi Robert, I remember our last talk.")

        self.assertEqual(payload, "Hi Robert, I remember our last talk.")
        self.assertTrue(audit["speaker_label_removed"])
        self.assertFalse(audit["speaker_labels_spoken"])
        self.assertIn("robert", spoken_words(payload))

    def test_short_opening_is_rebalanced_to_give_prefetch_playback_runway(self) -> None:
        public = (
            "I'm flattered by the invitation, Robert. Before we talk about going on a date, "
            "I'd love to understand what you have in mind and how you see the evening going."
        )
        chunks, audit = split_for_tts(public, max_chars=120)

        self.assertGreaterEqual(len(chunks[0]), 56)
        self.assertEqual(spoken_words(" ".join(chunks)), spoken_words(public))
        self.assertTrue(audit["word_coverage_exact"])

    def test_live_chatterbox_split_uses_a_short_natural_first_phrase_without_losing_words(self) -> None:
        public = (
            "How am I? I'm feeling pretty calm and relaxed right now, enjoying the quiet evening. "
            "You asked how I was doing, so I guess I'll just take a seat on the couch and unwind a bit. "
            "After that, we can decide together what feels right for the rest of the evening."
        )

        chunks = shell._split_for_voice(public, 180, first_chunk_max_chars=72)

        self.assertGreaterEqual(len(chunks), 2)
        self.assertLessEqual(len(chunks[0]), 72)
        self.assertGreaterEqual(len(chunks[0]), 44)
        self.assertTrue(all(len(chunk) <= 180 for chunk in chunks))
        self.assertEqual(spoken_words(" ".join(chunks)), spoken_words(public))

    def test_attempt_02_sized_reply_that_fits_full_limit_stays_one_gpu_chunk(self) -> None:
        public = (
            "I'm seeing the screen of my device in front of me, and I can hear some "
            "background ambient noise from the room."
        )

        chunks = shell._split_for_voice(public, 180, first_chunk_max_chars=72)

        self.assertEqual(len(public), 110)
        self.assertEqual(chunks, [public])
        self.assertEqual(spoken_words(" ".join(chunks)), spoken_words(public))

    def test_persistent_v2_refines_oversized_single_waveform_without_losing_words(self) -> None:
        public = (
            "I'm feeling calm and grounded right now, just taking a moment to settle into this "
            "quiet space. I don't have any questions at the moment. How is your day going?"
        )

        baseline = shell._split_for_voice(public, 180, first_chunk_max_chars=72)
        refined = shell._split_for_voice(
            public,
            180,
            first_chunk_max_chars=72,
            refine_single_chunk=True,
        )

        self.assertEqual(baseline, [public])
        self.assertGreaterEqual(len(refined), 2)
        self.assertGreaterEqual(len(refined[0]), 44)
        self.assertLessEqual(len(refined[0]), 72)
        self.assertTrue(all(len(chunk) <= 180 for chunk in refined))
        self.assertEqual(spoken_words(" ".join(refined)), spoken_words(public))

    def test_single_waveform_refinement_is_selected_only_for_persistent_v2(self) -> None:
        cfg = SimpleNamespace(engine="chatterbox_tts")

        with patch.object(
            shell,
            "persistent_blackwell_voice_status",
            return_value={"selected_candidate_version": "v2"},
        ):
            self.assertTrue(shell._live_refine_single_voice_chunk(cfg))
        with patch.object(
            shell,
            "persistent_blackwell_voice_status",
            return_value={"selected_candidate_version": "v1"},
        ):
            self.assertFalse(shell._live_refine_single_voice_chunk(cfg))
        self.assertFalse(
            shell._live_refine_single_voice_chunk(SimpleNamespace(engine="sapi"))
        )

    def test_short_complete_reply_remains_one_chunk_instead_of_becoming_choppy(self) -> None:
        public = "I'm excited for our walk, Robert! Let's get comfortable before heading out."

        chunks = shell._split_for_voice(public, 220, first_chunk_max_chars=72)

        self.assertEqual(chunks, [public])
        self.assertEqual(spoken_words(" ".join(chunks)), spoken_words(public))

    def test_long_public_reply_is_not_replaced_by_a_voice_summary(self) -> None:
        public = " ".join(["Every public spoken word must remain audible."] * 12)
        cfg = SimpleNamespace(engine="chatterbox_tts")

        with patch.object(shell, "SPEAK_FULL_REPLY", True):
            payload, mode, full_text_chars, audit = shell._voice_text_for_reply_with_audit(public, cfg)

        self.assertEqual(spoken_words(payload), spoken_words(public))
        self.assertEqual(mode, "full_reply_chunked")
        self.assertEqual(full_text_chars, len(public))
        self.assertTrue(audit["non_name_word_coverage_exact"])
        self.assertNotIn("full details are in the chat text", payload.lower())

    def test_private_marker_without_explicit_spoken_section_fails_closed(self) -> None:
        payload, audit = shell._live_spoken_only_payload("Hello.\nPRIVATE_MIND: do not speak this.")

        self.assertEqual(payload, "")
        self.assertFalse(audit["privacy_safe_for_speech"])

    def test_shell_uses_bounded_stream_pipeline_and_exposes_incomplete_status(self) -> None:
        cfg = SimpleNamespace(engine="chatterbox_tts", max_chars=120, play_audio=True)
        pipeline = {
            "spoken": True,
            "complete": False,
            "reason": "voice_incomplete",
            "pipeline": "bounded_chunk_prefetch_v1",
            "first_audio_elapsed_seconds": 1.25,
            "max_continuation_gap_seconds": 0.1,
            "chunk_results": [
                {
                    "chunk_index": 0,
                    "text": "First complete sentence.",
                    "generated": True,
                    "played": True,
                    "playback_reason": "ok",
                    "audio_path": "Voice/generated/first.wav",
                    "continuation_gap_seconds": 0.0,
                },
                {
                    "chunk_index": 1,
                    "text": "Second complete sentence.",
                    "generated": False,
                    "played": False,
                    "playback_reason": "not_played",
                    "audio_path": "",
                    "continuation_gap_seconds": None,
                },
            ],
        }
        with (
            patch.object(shell, "load_candidate_voice_config", return_value=cfg),
            patch.object(shell, "_split_for_voice", return_value=["First complete sentence.", "Second complete sentence."]),
            patch.object(shell, "speak_text_chunks_streaming", return_value=pipeline),
            patch.object(shell, "append_jsonl"),
        ):
            result = shell.speak_active_reply("kira", "Kira", "First complete sentence. Second complete sentence.")

        self.assertTrue(result["spoken"])
        self.assertFalse(result["complete"])
        self.assertEqual(result["reason"], "voice_incomplete")
        self.assertEqual(result["pipeline"], "bounded_chunk_prefetch_v1")
        self.assertEqual(result["first_chunk_elapsed_seconds"], 1.25)

    def test_persisted_active_kira_is_prewarmed_without_reactivation(self) -> None:
        with (
            patch.object(shell, "candidate_activation_block", return_value=None),
            patch.object(shell, "candidate_info", return_value={"label": "Kira"}),
            patch.object(shell, "begin_voice_session", return_value=42) as begin,
            patch.object(shell, "append_jsonl") as log,
        ):
            restored = shell.restore_voice_session_for_active_state({"active_ai": "kira"})

        self.assertTrue(restored)
        begin.assert_called_once_with("kira", "Kira")
        self.assertEqual(log.call_args.args[1]["event"], "voice_session_restored_on_shell_start")
        self.assertFalse(log.call_args.args[1]["activation_changed"])


if __name__ == "__main__":
    unittest.main()
