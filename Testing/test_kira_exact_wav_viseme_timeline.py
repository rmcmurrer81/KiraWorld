from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path

from tools.build_kira_exact_wav_viseme_timeline import TimelineError, build_timeline


class ExactWavVisemeTimelineTests(unittest.TestCase):
    TRANSCRIPT = "Map five easy oval actions."

    def fixture(self, root: Path) -> tuple[Path, Path]:
        wav_path = root / "exact.wav"
        with wave.open(str(wav_path), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(24000)
            stream.writeframes(b"\x00\x00" * 48000)
        wav_sha = hashlib.sha256(wav_path.read_bytes()).hexdigest()
        text_sha = hashlib.sha256(self.TRANSCRIPT.encode("utf-8")).hexdigest()
        intervals = [
            ("SIL", 0.00, 0.10, ""),
            ("M", 0.10, 0.25, "map"),
            ("F", 0.35, 0.50, "five"),
            ("IY1", 0.60, 0.78, "easy"),
            ("OW1", 0.88, 1.08, "oval"),
            ("AA1", 1.18, 1.40, "actions"),
            ("SIL", 1.40, 2.00, ""),
        ]
        alignment_path = root / "alignment.json"
        alignment_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "passed",
                    "source": "synthetic_test_for_mfa_compatible_contract",
                    "wav_sha256": wav_sha,
                    "transcript_sha256": text_sha,
                    "word_coverage": 1.0,
                    "oov_words": [],
                    "phones": [
                        {
                            "phone": phone,
                            "start_seconds": start,
                            "end_seconds": end,
                            "word": word,
                        }
                        for phone, start, end, word in intervals
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return wav_path, alignment_path

    def test_all_five_visemes_are_exact_wav_bound_and_return_to_rest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            wav_path, alignment_path = self.fixture(Path(temp))
            timeline = build_timeline(
                wav_path=wav_path,
                transcript=self.TRANSCRIPT,
                alignment_path=alignment_path,
                fps=60,
            )
        self.assertTrue(timeline["gates"]["exact_wav_hash_bound"])
        self.assertTrue(timeline["gates"]["all_five_review_visemes_present"])
        self.assertTrue(timeline["gates"]["first_and_last_samples_exact_rest"])
        for viseme in ("AH", "EE", "O", "FV", "MBP"):
            self.assertEqual(timeline["peak_weights"][viseme], 1.0)
        self.assertTrue(all(value == 0.0 for value in timeline["samples"][0]["weights"].values()))
        self.assertTrue(all(value == 0.0 for value in timeline["samples"][-1]["weights"].values()))

    def test_coarticulation_overlaps_neighboring_visemes_without_exceeding_unit_sum(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wav_path, alignment_path = self.fixture(root)
            payload = json.loads(alignment_path.read_text(encoding="utf-8"))
            payload["phones"][2]["start_seconds"] = 0.27
            payload["phones"][2]["end_seconds"] = 0.42
            alignment_path.write_text(json.dumps(payload), encoding="utf-8")
            timeline = build_timeline(
                wav_path=wav_path,
                transcript=self.TRANSCRIPT,
                alignment_path=alignment_path,
                fps=60,
            )
        overlaps = [
            sample
            for sample in timeline["samples"]
            if sum(1 for name in ("AH", "EE", "O", "FV", "MBP") if sample["weights"][name] > 0.0) > 1
        ]
        self.assertTrue(overlaps)
        for sample in timeline["samples"]:
            total = sum(sample["weights"][name] for name in ("AH", "EE", "O", "FV", "MBP"))
            self.assertLessEqual(total, 1.000001)

    def test_hash_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wav_path, alignment_path = self.fixture(root)
            payload = json.loads(alignment_path.read_text(encoding="utf-8"))
            payload["wav_sha256"] = "0" * 64
            alignment_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(TimelineError, "exact WAV"):
                build_timeline(
                    wav_path=wav_path,
                    transcript=self.TRANSCRIPT,
                    alignment_path=alignment_path,
                    fps=60,
                )

    def test_unknown_phone_fails_instead_of_guessing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wav_path, alignment_path = self.fixture(root)
            payload = json.loads(alignment_path.read_text(encoding="utf-8"))
            payload["phones"][1]["phone"] = "NOT_A_PHONE"
            alignment_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(TimelineError, "unsupported phone"):
                build_timeline(
                    wav_path=wav_path,
                    transcript=self.TRANSCRIPT,
                    alignment_path=alignment_path,
                    fps=60,
                )


if __name__ == "__main__":
    unittest.main()
