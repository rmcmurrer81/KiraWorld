from __future__ import annotations

import json
import math
import os
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.voice_speaker_separation import (  # noqa: E402
    _read_json,
    _io_path,
    _write_text,
    build_speaker_audition_reels,
    separate_reference_pack,
)


def write_tone(path: Path, frequency: float) -> None:
    rate = 16000
    samples = [int(9000 * math.sin(2 * math.pi * frequency * index / rate)) for index in range(rate)]
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(struct.pack(f"<{len(samples)}h", *samples))


class VoiceSpeakerSeparationTests(unittest.TestCase):
    def test_metadata_io_supports_long_descriptive_windows_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / (("voice_review_" * 18) + ".json")
            payload = {"status": "unreviewed", "identity_claim": False}
            _write_text(path, json.dumps(payload))
            self.assertEqual(_read_json(path, {}), payload)
            os.remove(_io_path(path))

    def test_groups_clips_and_honors_reviewed_identity_hint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = Path(temp_dir)
            clips_dir = pack / "candidate_clips"
            clips_dir.mkdir()
            clips = []
            for index, frequency in enumerate((110, 115, 220, 225), start=1):
                path = clips_dir / f"clip_{index:04d}.wav"
                write_tone(path, frequency)
                clips.append({"clip_id": path.stem, "path": str(path), "start_seconds": index, "end_seconds": index + 1})
            (pack / "voice_reference_manifest.json").write_text(json.dumps({"pack_id": "smoke", "audio": {"clips": clips}}), encoding="utf-8")
            (pack / "speaker_identity_hints.json").write_text(json.dumps({"clip_ids": {"clip_0001": "Clark Kent"}, "time_ranges": []}), encoding="utf-8")
            result = separate_reference_pack(pack, cluster_count=2)
            self.assertEqual(len(result["clips"]), 4)
            self.assertIn("clark_kent", result["speaker_labels"])
            self.assertTrue((pack / "speaker_separation" / "speakers" / "clark_kent" / "clip_0001.wav").exists())
            self.assertTrue((pack / "speaker_separation" / "speaker_separation_manifest.json").exists())

            reels = build_speaker_audition_reels(pack, clips_per_group=2)
            self.assertGreaterEqual(len(reels["reels"]), 2)
            self.assertTrue((pack / "speaker_separation" / "review_reels" / "audition_reels_manifest.json").exists())
            for reel in reels["reels"]:
                self.assertTrue(Path(reel["path"]).exists())
                self.assertGreater(reel["clip_count"], 0)


if __name__ == "__main__":
    unittest.main()
