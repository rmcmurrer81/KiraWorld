import unittest

import numpy as np

from Core.dialogue_audio_signal import (
    assess_generated_speech_chunk,
    gentle_proximity_correction,
)
from Core.dialogue_tts import prepare_tts_turns, split_for_tts, spoken_words


class DialogueTtsTests(unittest.TestCase):
    def test_default_omits_dialogue_names_and_keeps_every_other_word(self):
        turns, audit = prepare_tts_turns(
            [
                {"speaker": "Kira", "text": "Hi Robert, I'm Kira and Kira's idea still matters."},
                {"speaker": "Robert", "text": "I agree with Robert McMurrer's careful point, Kira."},
            ],
            omit_names=True,
        )
        combined = " ".join(turn["text"] for turn in turns).casefold()
        self.assertNotIn("kira", combined)
        self.assertNotIn("robert", combined)
        self.assertNotIn("mcmurrer", combined)
        self.assertEqual(
            ["hi", "i'm", "and", "idea", "still", "matters"],
            spoken_words(turns[0]["text"]),
        )
        self.assertEqual(5, audit["removed_dialogue_name_occurrences"])
        self.assertTrue(audit["non_name_word_coverage_exact"])
        self.assertFalse(audit["dialogue_names_spoken"])

    def test_chunking_retains_all_words_in_order_and_bounds_chunks(self):
        text = (
            "This deliberately long sentence has no early stopping point and it keeps adding "
            "ordinary public spoken words so the renderer must divide it safely without ever "
            "dropping a word or clipping a word in half before the sentence finally ends. "
            "Then a second sentence remains intact."
        )
        chunks, audit = split_for_tts(text, max_chars=100)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 100 for chunk in chunks))
        self.assertEqual(spoken_words(text), spoken_words(" ".join(chunks)))
        self.assertTrue(audit["word_coverage_exact"])

    def test_chunking_rebalances_tiny_clause_fragments(self):
        text = (
            "In my mind, I've been thinking about our conversations as more of a mentor-student "
            "relationship rather than something personal or, romantic. But I want to be honest "
            "with you about how that uncertainty feels."
        )

        chunks, audit = split_for_tts(text, max_chars=120)

        self.assertEqual(spoken_words(text), spoken_words(" ".join(chunks)))
        self.assertTrue(all(len(chunk) <= 120 for chunk in chunks))
        self.assertTrue(all(len(chunk) >= 32 for chunk in chunks[:-1]))
        self.assertNotIn("In my mind,", chunks)
        self.assertNotIn("romantic.", chunks)
        self.assertTrue(audit["word_coverage_exact"])

    def test_fenced_public_words_are_kept_while_fence_markup_is_removed(self):
        turns, audit = prepare_tts_turns(
            [{
                "speaker": "Kira",
                "text": "Before. ```text\nEvery public fenced word stays here.\n``` After Robert.",
            }],
            omit_names=True,
        )
        self.assertEqual(
            ["before", "every", "public", "fenced", "word", "stays", "here", "after"],
            spoken_words(turns[0]["text"]),
        )
        self.assertTrue(audit["non_name_word_coverage_exact"])

    def test_optional_speaker_prefix_is_in_the_bound_tts_payload(self):
        turns, audit = prepare_tts_turns(
            [{"speaker": "Kira", "text": "A public sentence."}],
            omit_names=False,
            prefix_speaker_names=True,
        )
        self.assertEqual("Kira. A public sentence.", turns[0]["text"])
        self.assertTrue(audit["speaker_labels_spoken"])

    def test_robert_proximity_filter_is_conservative_and_frequency_selective(self):
        sample_rate = 24000
        seconds = 1.0
        time = np.arange(int(sample_rate * seconds), dtype=np.float32) / sample_rate
        low = np.sin(2 * np.pi * 40.0 * time).astype(np.float32)
        high = np.sin(2 * np.pi * 1000.0 * time).astype(np.float32)
        low_corrected = gentle_proximity_correction(
            low,
            sample_rate=sample_rate,
            cutoff_hz=95.0,
            mix=0.30,
        )
        high_corrected = gentle_proximity_correction(
            high,
            sample_rate=sample_rate,
            cutoff_hz=95.0,
            mix=0.30,
        )
        low_ratio = float(np.sqrt(np.mean(low_corrected**2)) / np.sqrt(np.mean(low**2)))
        high_ratio = float(np.sqrt(np.mean(high_corrected**2)) / np.sqrt(np.mean(high**2)))
        self.assertLess(low_ratio, high_ratio)
        self.assertGreater(low_ratio, 0.60)
        self.assertGreater(high_ratio, 0.95)
        self.assertEqual(low.shape, low_corrected.shape)
        self.assertTrue(np.isfinite(low_corrected).all())

    def test_zero_mix_leaves_signal_unchanged(self):
        signal = np.asarray([0.1, -0.2, 0.3], dtype=np.float32)
        corrected = gentle_proximity_correction(
            signal,
            sample_rate=24000,
            cutoff_hz=95.0,
            mix=0.0,
        )
        np.testing.assert_array_equal(signal, corrected)

    def test_acoustic_chunk_sanity_passes_plausible_non_silent_pcm(self):
        sample_rate = 24000
        time = np.arange(sample_rate * 2, dtype=np.float32) / sample_rate
        signal = (0.08 * np.sin(2 * np.pi * 220.0 * time)).astype(np.float32)
        result = assess_generated_speech_chunk(
            signal,
            sample_rate=sample_rate,
            queued_word_count=10,
            min_seconds_per_word=0.14,
        )
        self.assertTrue(result["passed"])
        self.assertEqual([], result["reasons"])

    def test_acoustic_chunk_sanity_rejects_silence(self):
        result = assess_generated_speech_chunk(
            np.zeros(24000, dtype=np.float32),
            sample_rate=24000,
            queued_word_count=4,
        )
        self.assertFalse(result["passed"])
        self.assertIn("rms_below_speech_floor", result["reasons"])
        self.assertIn("peak_below_speech_floor", result["reasons"])

    def test_acoustic_chunk_sanity_rejects_implausibly_short_output(self):
        sample_rate = 24000
        time = np.arange(2400, dtype=np.float32) / sample_rate
        signal = (0.08 * np.sin(2 * np.pi * 220.0 * time)).astype(np.float32)
        result = assess_generated_speech_chunk(
            signal,
            sample_rate=sample_rate,
            queued_word_count=20,
            min_seconds_per_word=0.14,
        )
        self.assertFalse(result["passed"])
        self.assertIn("duration_too_short_for_queued_words", result["reasons"])


if __name__ == "__main__":
    unittest.main()
