from __future__ import annotations
import math, struct, sys, tempfile, unittest, wave
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from Core.voice_reference_pipeline import segment_wav

class VoiceReferencePipelineTests(unittest.TestCase):
    def test_segment_wav_finds_two_regions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "source.wav"; rate = 24000; samples = []
            for seconds, amplitude in [(0.6, 0), (1.4, 8000), (0.8, 0), (1.3, 6500), (0.6, 0)]:
                for index in range(int(rate * seconds)):
                    samples.append(int(amplitude * math.sin(2 * math.pi * 220 * index / rate)) if amplitude else 0)
            with wave.open(str(source), "wb") as writer:
                writer.setnchannels(1); writer.setsampwidth(2); writer.setframerate(rate); writer.writeframes(struct.pack(f"<{len(samples)}h", *samples))
            clips = segment_wav(source, root / "clips")
            self.assertEqual(len(clips), 2); self.assertTrue(all((root / "clips" / f"{clip.clip_id}.wav").exists() for clip in clips))
            self.assertTrue(all(clip.review_status == "unreviewed" for clip in clips))
if __name__ == "__main__": unittest.main()
