from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qwen3_feasibility_worker", ROOT / "feasibility_worker.py"
)
assert SPEC is not None and SPEC.loader is not None
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


def valid_request() -> dict[str, object]:
    return {
        "schema": "kira-qwen3-voice-design-feasibility-v1",
        "candidate_id": "test_candidate_001",
        "language": "English",
        "text": "This is a bounded original voice test.",
        "voice_traits": {
            "presentation": "adult_neutral",
            "pitch": "mid",
            "timbre": "clear",
            "pace": "moderate",
            "warmth": "warm",
            "confidence": "steady",
            "energy": "calm",
            "accent": "neutral_english",
            "breathiness": "low",
        },
        "seed": 42,
        "intent": "generated_original_no_named_person_imitation",
        "named_person_imitation": False,
        "nonproduction_feasibility": True,
    }


class FeasibilityWorkerTests(unittest.TestCase):
    def test_evidence_envelope_binds_every_pilot_artifact(self) -> None:
        envelope = json.loads(
            (ROOT / "evidence" / "pilot-evidence-envelope.json").read_text(
                encoding="utf-8"
            )
        )
        for artifact in envelope["artifacts"]:
            path = ROOT / artifact["path"]
            self.assertEqual(path.stat().st_size, artifact["bytes"])
            self.assertEqual(worker.sha256_file(path), artifact["sha256"])
        self.assertFalse(envelope["assertions"]["voice_assigned"])
        self.assertFalse(envelope["assertions"]["voice_activated"])

    def test_published_request_is_strict_and_valid(self) -> None:
        request = worker.load_request(
            ROOT
            / "auditions"
            / "calm_female_pilot_20260825_01"
            / "qwen3_voice_design_feasibility_request.json"
        )
        self.assertEqual(request["candidate_id"], "calm_female_pilot_20260825_01")

    def test_duplicate_keys_and_imitation_language_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "request.json"
            path.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                worker.load_request(path)

            request = valid_request()
            request["voice_traits"]["timbre"] = "imitate_named_performer"
            path.write_text(json.dumps(request), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsupported voice trait"):
                worker.load_request(path)

    def test_auditor_named_person_bypasses_fail_closed(self) -> None:
        attacks = (
            "modeled after Morgan Freeman",
            "inspired by Barack Obama",
            "Scarlett Johansson's cadence and timbre",
            "sound   like Morgan Freeman",
            "just like Morgan Freeman",
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "request.json"
            for attack in attacks:
                request = valid_request()
                request["voice_traits"]["timbre"] = attack
                path.write_text(json.dumps(request), encoding="utf-8")
                with self.assertRaises(ValueError, msg=attack):
                    worker.load_request(path)

    def test_design_prompt_is_rendered_only_from_allowlisted_traits(self) -> None:
        request = valid_request()
        prompt = worker.render_design_prompt(request["voice_traits"])
        self.assertIn("An original adult gender-neutral person", prompt)
        self.assertIn("no resemblance to any named person", prompt)
        self.assertNotIn("Morgan", prompt)

    def test_model_verification_is_size_and_hash_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = root / "tiny.bin"
            payload.write_bytes(b"exact-test-model")
            expected = {
                "tiny.bin": (payload.stat().st_size, worker.sha256_file(payload))
            }
            with patch.object(worker, "EXPECTED_MODEL_FILES", expected):
                self.assertEqual(worker.verify_model(root)[0]["path"], "tiny.bin")
                extra = root / "unexpected.metadata"
                extra.write_text("not part of the exact snapshot", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "scope"):
                    worker.verify_model(root)
                extra.unlink()
                unexpected_directory = root / "unexpected-directory"
                unexpected_directory.mkdir()
                with self.assertRaisesRegex(ValueError, "scope"):
                    worker.verify_model(root)
                unexpected_directory.rmdir()
                payload.write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "model file mismatch"):
                    worker.verify_model(root)

    def test_wav_gate_accepts_only_canonical_bounded_audio(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sample.wav"
            with wave.open(str(path), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(24_000)
                audio.writeframes(b"\x01\x00" * 24_000)
            result = worker.inspect_wav(path)
            self.assertEqual(result["duration_seconds"], 1.0)

            with wave.open(str(path), "wb") as audio:
                audio.setnchannels(2)
                audio.setsampwidth(2)
                audio.setframerate(24_000)
                audio.writeframes(b"\x01\x00" * 48_000)
            with self.assertRaisesRegex(ValueError, "canonical"):
                worker.inspect_wav(path)


if __name__ == "__main__":
    unittest.main()
