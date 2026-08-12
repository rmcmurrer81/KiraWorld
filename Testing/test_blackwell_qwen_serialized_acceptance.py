from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_blackwell_qwen_serialized_acceptance as acceptance  # noqa: E402


class PublicSpokenClient:
    def __init__(self, nonce: str) -> None:
        self.nonce = nonce
        self.payloads: list[dict] = []

    def chat(self, payload: dict) -> dict:
        self.payloads.append(payload)
        return {
            "model": acceptance.PINNED_MODEL,
            "message": {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "SPOKEN": acceptance.PUBLIC_SPOKEN_TEXT,
                        "nonce": self.nonce,
                    }
                ),
            },
            "done": True,
            "done_reason": "stop",
            "total_duration": 1_000_000,
            "load_duration": 100_000,
            "prompt_eval_count": 20,
            "eval_count": 20,
            "eval_duration": 500_000,
        }


class BlackwellQwenSerializedAcceptanceTests(unittest.TestCase):
    def test_static_contract_and_attempt_05_prerequisite_are_exact(self) -> None:
        contract = acceptance.validate_static_contract()
        proof = acceptance.validate_standalone_attempt_05()
        self.assertEqual(contract["qwen_digest"], acceptance.PINNED_DIGEST)
        self.assertEqual(contract["approved_profile_sha256"], acceptance.APPROVED_PROFILE_SHA256)
        self.assertEqual(proof["status"], "PASS")
        self.assertEqual(
            proof["report_sha256"],
            "dd0d609dc5405a04dcb0c4e689bbc674c553058bcad9cd93bfaf67a595c841de",
        )

    def test_strict_spoken_parser_rejects_extra_or_duplicate_fields(self) -> None:
        nonce = "a" * 48
        valid = acceptance._parse_strict_spoken_reply(
            json.dumps({"SPOKEN": acceptance.PUBLIC_SPOKEN_TEXT, "nonce": nonce}),
            nonce,
        )
        self.assertTrue(valid["passed"])
        extra = acceptance._parse_strict_spoken_reply(
            json.dumps(
                {
                    "SPOKEN": acceptance.PUBLIC_SPOKEN_TEXT,
                    "nonce": nonce,
                    "PRIVATE MIND": "must not cross the boundary",
                }
            ),
            nonce,
        )
        self.assertFalse(extra["passed"])
        duplicate = acceptance._parse_strict_spoken_reply(
            '{"SPOKEN":"one","SPOKEN":"two","nonce":"' + nonce + '"}',
            nonce,
        )
        self.assertFalse(duplicate["passed"])

    def test_qwen_probe_releases_only_exact_spoken_field(self) -> None:
        nonce = "b" * 48
        client = PublicSpokenClient(nonce)
        residency = {
            "passed": True,
            "loaded_record": {
                "name": acceptance.PINNED_MODEL,
                "model": acceptance.PINNED_MODEL,
                "digest": acceptance.PINNED_DIGEST,
                "context_length": acceptance.qwen.LIFECYCLE_CONTEXT_LENGTH,
            },
            "issues": [],
        }
        with patch.object(acceptance.qwen, "wait_for_model_state", return_value=residency):
            result = acceptance.qwen_public_spoken_probe(
                client, "unit", nonce=nonce
            )
        self.assertTrue(result["passed"])
        self.assertEqual(result["released_spoken_text"], acceptance.PUBLIC_SPOKEN_TEXT)
        self.assertEqual(result["release_boundary"]["released_fields"], ["SPOKEN"])
        payload = client.payloads[0]
        self.assertNotIn("images", json.dumps(payload).casefold())
        self.assertIs(payload["think"], False)
        self.assertEqual(payload["keep_alive"], "10m")

    def test_voice_payload_contains_spoken_text_but_not_qwen_nonce_or_response(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "RecoverySprint") as value:
            run_dir = Path(value)
            payload, output = acceptance.build_voice_payload(
                run_dir, acceptance.PUBLIC_SPOKEN_TEXT
            )
        self.assertEqual(payload["channel"], "public_spoken_only")
        self.assertEqual(payload["text"], acceptance.PUBLIC_SPOKEN_TEXT)
        self.assertNotIn("nonce", payload)
        self.assertNotIn("response", payload)
        self.assertTrue(output.name.endswith("serialized_probe.wav"))

    def test_run_directory_is_append_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "RecoverySprint") as value:
            evidence_root = Path(value)
            with patch.object(acceptance, "EVIDENCE_ROOT", evidence_root):
                created = acceptance._new_run_directory(1)
                self.assertTrue(created.is_dir())
                with self.assertRaises(acceptance.qwen.AcceptanceSafetyError):
                    acceptance._new_run_directory(1)


if __name__ == "__main__":
    unittest.main()
