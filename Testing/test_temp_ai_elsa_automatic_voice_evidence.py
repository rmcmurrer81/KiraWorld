from __future__ import annotations

import json
import math
import tempfile
import unittest
import wave
from array import array
from pathlib import Path

from Core.temp_ai_elsa_automatic_voice_evidence import (
    ANCHOR_FILENAME,
    MANIFEST_FILENAME,
    OFFICIAL_SOURCE_URL,
    SELECTED_RANGES,
    build_elsa_automatic_voice_evidence,
    concatenate_pcm_deterministically,
)
from Core.temp_ai_online_media_analysis import SAMPLE_RATE, file_sha256


def write_pcm(path: Path, *, frequency: float, duration: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    values = array(
        "h",
        (
            round(4000 * math.sin(2 * math.pi * frequency * index / SAMPLE_RATE))
            for index in range(round(duration * SAMPLE_RATE))
        ),
    )
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(SAMPLE_RATE)
        target.writeframes(values.tobytes())


class ElsaAutomaticVoiceEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        self.candidate_root = self.project / "TemporaryAI" / "candidates"
        self.candidate_id = "elsa_test_candidate"
        self.candidate = self.candidate_root / self.candidate_id
        self.candidate.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_cached_range(
        self,
        start: float,
        end: float,
        *,
        contaminated: bool = False,
        suffix: str = "cached",
    ) -> Path:
        run = self.candidate / "workbench" / "inputs" / "online_voice_analysis" / f"{suffix}_{start}"
        pcm = run / "prepared" / "voice_mono_16khz_pcm.wav"
        write_pcm(pcm, frequency=180 + start, duration=end - start)
        manifest = {
            "analysis_id": f"analysis_{suffix}_{start}",
            "source": {
                "url": OFFICIAL_SOURCE_URL,
                "requested_range": {"start_seconds": start, "end_seconds": end},
            },
            "artifacts": {
                "mono_16khz_pcm": {
                    "path": str(pcm.resolve()),
                    "sha256": file_sha256(pcm),
                }
            },
            "objective_review": {
                "basic_signal_quality_passed": True,
                "possible_contamination_flagged": contaminated,
            },
        }
        run.mkdir(parents=True, exist_ok=True)
        (run / "analysis_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return pcm

    def test_deterministic_concat_preserves_exact_order_and_shape(self):
        first = self.project / "first.wav"
        second = self.project / "second.wav"
        output = self.project / "combined.wav"
        write_pcm(first, frequency=180, duration=0.25)
        write_pcm(second, frequency=260, duration=0.30)
        details1 = concatenate_pcm_deterministically([first, second], output)
        content1 = output.read_bytes()
        details2 = concatenate_pcm_deterministically([first, second], output)
        self.assertEqual(content1, output.read_bytes())
        self.assertEqual(details1["sha256"], details2["sha256"])
        self.assertEqual(0.55, details2["duration_seconds"])
        with wave.open(str(output), "rb") as source:
            self.assertEqual((1, 2, SAMPLE_RATE), (source.getnchannels(), source.getsampwidth(), source.getframerate()))

    def test_one_click_build_reuses_both_clean_hash_bound_runs(self):
        expected_inputs = [self.add_cached_range(start, end) for start, end in SELECTED_RANGES]

        def network_must_not_run(_request, **_kwargs):
            raise AssertionError("clean cached bounded runs should be reused")

        result = build_elsa_automatic_voice_evidence(
            candidate_id=self.candidate_id,
            candidate_root=self.candidate_root,
            project_root=self.project,
            analysis_runner=network_must_not_run,
        )
        self.assertEqual({"bounded_runs_reused": 2, "bounded_runs_acquired": 0}, result["cache"])
        self.assertEqual(OFFICIAL_SOURCE_URL, result["source"]["url"])
        self.assertEqual([[40.12, 43.72], [54.86, 58.16]], result["combined_evidence_wav"]["concatenation_order"])
        self.assertFalse(result["authority_boundary"]["speaker_identity_claimed"])
        self.assertFalse(result["authority_boundary"]["voice_assigned"])
        self.assertFalse(result["authority_boundary"]["candidate_activated"])
        anchor = self.candidate / "workbench" / "inputs" / "identity_reviews" / ANCHOR_FILENAME
        manifest = self.candidate / "workbench" / "inputs" / "identity_reviews" / MANIFEST_FILENAME
        self.assertTrue(anchor.is_file())
        self.assertTrue(manifest.is_file())
        self.assertEqual(result["combined_evidence_wav"]["sha256"], file_sha256(anchor))
        self.assertEqual(
            round(sum((end - start) for start, end in SELECTED_RANGES), 3),
            result["combined_evidence_wav"]["duration_seconds"],
        )
        # A second run is byte-for-byte deterministic and still does no network work.
        first_bytes = anchor.read_bytes()
        again = build_elsa_automatic_voice_evidence(
            candidate_id=self.candidate_id,
            candidate_root=self.candidate_root,
            project_root=self.project,
            analysis_runner=network_must_not_run,
        )
        self.assertEqual(first_bytes, anchor.read_bytes())
        self.assertEqual(result["combined_evidence_wav"]["sha256"], again["combined_evidence_wav"]["sha256"])
        self.assertEqual([file_sha256(path) for path in expected_inputs], [item["pcm"]["sha256"] for item in result["source"]["ranges"]])

    def test_contaminated_cache_is_not_reused_and_fails_closed(self):
        start, end = SELECTED_RANGES[0]
        self.add_cached_range(start, end, contaminated=True)

        def blocked_network(_request, **_kwargs):
            raise RuntimeError("offline")

        with self.assertRaisesRegex(RuntimeError, "offline"):
            build_elsa_automatic_voice_evidence(
                candidate_id=self.candidate_id,
                candidate_root=self.candidate_root,
                project_root=self.project,
                analysis_runner=blocked_network,
            )

    def test_missing_ranges_are_acquired_but_never_gain_identity_or_runtime_authority(self):
        calls: list[tuple[float, float]] = []

        def runner(request, **_kwargs):
            bounds = request["range"]
            start = float(bounds["start_seconds"])
            end = float(bounds["end_seconds"])
            calls.append((start, end))
            run = self.candidate / "mock_acquired" / str(len(calls))
            pcm = run / "voice.wav"
            write_pcm(pcm, frequency=210 + len(calls), duration=end - start)
            return {
                "analysis_id": f"mock_{len(calls)}",
                "artifacts": {"mono_16khz_pcm": {"path": str(pcm), "sha256": file_sha256(pcm)}},
                "objective_review": {
                    "basic_signal_quality_passed": True,
                    "possible_contamination_flagged": False,
                },
            }

        result = build_elsa_automatic_voice_evidence(
            candidate_id=self.candidate_id,
            candidate_root=self.candidate_root,
            project_root=self.project,
            analysis_runner=runner,
        )
        self.assertEqual(list(SELECTED_RANGES), calls)
        self.assertEqual({"bounded_runs_reused": 0, "bounded_runs_acquired": 2}, result["cache"])
        self.assertTrue(all(not value for key, value in result["authority_boundary"].items() if isinstance(value, bool)))


if __name__ == "__main__":
    unittest.main()
