from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "ros2_ws" / "src" / "kira_hanson_bridge"
sys.path.insert(0, str(PACKAGE_ROOT))

from kira_hanson_bridge.evidence import EvidenceChain, sanitize_payload  # noqa: E402


class EvidenceTests(unittest.TestCase):
    def test_default_sanitization_omits_raw_speech_and_provenance(self) -> None:
        payload = {
            "intent_id": "speech-1",
            "source_identity": "kira",
            "confidence": 0.9,
            "ttl_ms": 5000,
            "age_ms": 10,
            "evidence_ref": "private:conversation:42",
            "text": "private sentence",
            "voice": "default",
            "max_duration_ms": 1000,
        }
        sanitized = sanitize_payload("speech", payload)
        encoded = json.dumps(sanitized)
        self.assertNotIn("private sentence", encoded)
        self.assertNotIn("private:conversation:42", encoded)
        self.assertIn("text_digest", sanitized)
        self.assertIn("evidence_ref_digest", sanitized)

    def test_gaze_coordinates_are_hashed_by_default(self) -> None:
        payload = {
            "intent_id": "gaze-1",
            "source_identity": "kira",
            "confidence": 0.9,
            "ttl_ms": 5000,
            "age_ms": 10,
            "evidence_ref": "opaque",
            "target_frame": "world",
            "target": {"x": 1.0, "y": 2.0, "z": 3.0},
            "duration_ms": 1000,
        }
        sanitized = sanitize_payload("gaze", payload)
        self.assertNotIn("target", sanitized)
        self.assertIn("target_digest", sanitized)

    def test_rejected_nonfinite_gaze_value_is_sanitized_without_raising(self) -> None:
        payload = {
            "intent_id": "gaze-invalid",
            "source_identity": "kira",
            "confidence": 0.9,
            "ttl_ms": 5000,
            "age_ms": 10,
            "evidence_ref": "opaque",
            "target_frame": "world",
            "target": {"x": math.nan, "y": 0.0, "z": 1.0},
            "duration_ms": 1000,
        }
        sanitized = sanitize_payload("gaze", payload)
        self.assertEqual(
            sanitized["target_digest"]["encoding"], "UNENCODABLE_REJECTED_VALUE"
        )

    def test_chain_verifies_and_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.jsonl"
            chain = EvidenceChain(path)
            first = chain.append({"state": "REQUESTED"})
            second = chain.append({"state": "REJECTED"})
            valid, count, final_hash = EvidenceChain.verify(path)
            self.assertTrue(valid)
            self.assertEqual(count, 2)
            self.assertEqual(final_hash, second)
            self.assertNotEqual(first, second)

            lines = path.read_text(encoding="utf-8").splitlines()
            record = json.loads(lines[0])
            record["record"]["state"] = "COMPLETED"
            lines[0] = json.dumps(record, separators=(",", ":"), sort_keys=True)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.assertFalse(EvidenceChain.verify(path)[0])

    def test_invalid_existing_chain_refuses_append(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.jsonl"
            path.write_text('{"broken":true}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                EvidenceChain(path)


if __name__ == "__main__":
    unittest.main()
