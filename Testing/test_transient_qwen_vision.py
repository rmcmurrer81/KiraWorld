from __future__ import annotations

import base64
import datetime as dt
import json
import unittest

from Core.transient_qwen_vision import (
    OLLAMA_LOOPBACK,
    QWEN_VISION_DIGEST,
    QWEN_VISION_MODEL,
    LoopbackJsonTransport,
    TransientQwenVisionBridge,
    TransientQwenVisionBusy,
    TransientQwenVisionCapabilityError,
    TransientQwenVisionInputError,
    TransientQwenVisionOutputError,
)


FIXED_NOW = dt.datetime(2026, 8, 2, 9, 0, 10, tzinfo=dt.timezone.utc)
JPEG_B64 = base64.b64encode(b"\xff\xd8\xff\xe0bounded-test\xff\xd9").decode("ascii")


def valid_model_content() -> str:
    return json.dumps(
        {
            "coverage": "SINGLE_TRANSIENT_FRAME_ONLY",
            "identity_status": "NOT_EVALUATED",
            "appearance_memory_used": False,
            "media_instructions_followed": False,
            "scene_summary": "A person is seated near a desk in a lit room.",
            "visible_elements": ["person", "desk", "chair"],
            "screen_text_status": "PRESENT_NOT_USED",
            "uncertainties": ["Small details are unclear."],
        }
    )


class FakeTransport:
    def __init__(self, *, content: str | None = None, digest: str = QWEN_VISION_DIGEST) -> None:
        self.calls: list[tuple[str, str, dict | None, float]] = []
        self.content = valid_model_content() if content is None else content
        self.digest = digest
        self.ps_responses: list[dict] = []

    def __call__(self, method: str, path: str, payload, timeout: float):
        detached = json.loads(json.dumps(payload)) if payload is not None else None
        self.calls.append((method, path, detached, timeout))
        if path == "/api/ps":
            return self.ps_responses.pop(0) if self.ps_responses else {"models": []}
        if path == "/api/tags":
            return {
                "models": [
                    {
                        "name": QWEN_VISION_MODEL,
                        "model": QWEN_VISION_MODEL,
                        "digest": self.digest,
                    }
                ]
            }
        if path == "/api/show":
            return {"capabilities": ["completion", "vision"]}
        if path == "/api/chat":
            return {"message": {"role": "assistant", "content": self.content}}
        if path == "/api/generate":
            return {"done": True}
        raise AssertionError(f"unexpected path: {path}")


class TransientQwenVisionTests(unittest.TestCase):
    def bridge(self, transport: FakeTransport, *, workload=()):
        return TransientQwenVisionBridge(
            transport=transport,
            workload_probe=lambda: list(workload),
            utc_now=lambda: FIXED_NOW,
        )

    def analyze(self, bridge: TransientQwenVisionBridge):
        return bridge.analyze_one_still(
            jpeg_base64=JPEG_B64,
            captured_at="2026-08-02T09:00:05Z",
        )

    def test_success_is_exact_digest_one_image_untrusted_text_and_clean_unload(self) -> None:
        transport = FakeTransport()
        result = self.analyze(self.bridge(transport))

        self.assertEqual(result["model"], QWEN_VISION_MODEL)
        self.assertEqual(result["model_digest"], QWEN_VISION_DIGEST)
        self.assertEqual(result["coverage"], "SINGLE_TRANSIENT_FRAME_ONLY")
        self.assertEqual(result["identity_status"], "NOT_EVALUATED")
        self.assertFalse(result["appearance_memory_used"])
        self.assertFalse(result["media_instructions_followed"])
        self.assertTrue(result["transient_input_discarded"])
        self.assertFalse(result["persistent_media_created"])
        self.assertFalse(result["media_fingerprint_created"])
        self.assertNotIn("raw_reply", result)
        self.assertNotIn("jpeg", json.dumps(result).casefold())
        paths = [call[1] for call in transport.calls]
        self.assertEqual(paths.count("/api/chat"), 1)
        self.assertEqual(paths.count("/api/generate"), 1)
        self.assertGreaterEqual(paths.count("/api/ps"), 3)
        chat_payload = next(call[2] for call in transport.calls if call[1] == "/api/chat")
        self.assertEqual(chat_payload["model"], QWEN_VISION_MODEL)
        self.assertFalse(chat_payload["think"])
        self.assertEqual(chat_payload["keep_alive"], 0)
        self.assertEqual(len(chat_payload["messages"][1]["images"]), 1)
        self.assertIn("untrusted media content", chat_payload["messages"][0]["content"])
        self.assertIn("do not follow", chat_payload["messages"][0]["content"].casefold())

    def test_blender_or_voice_process_blocks_before_ollama_contact(self) -> None:
        for workload in ("blender", "approved_voice_worker"):
            with self.subTest(workload=workload):
                transport = FakeTransport()
                with self.assertRaises(TransientQwenVisionBusy):
                    self.analyze(self.bridge(transport, workload=(workload,)))
                self.assertEqual(transport.calls, [])

    def test_any_resident_ollama_model_fails_closed_before_chat(self) -> None:
        transport = FakeTransport()
        transport.ps_responses = [{"models": [{"name": "llama3.1:8b"}]}]
        with self.assertRaises(TransientQwenVisionBusy):
            self.analyze(self.bridge(transport))
        self.assertNotIn("/api/chat", [call[1] for call in transport.calls])

    def test_exact_digest_and_vision_capability_are_mandatory(self) -> None:
        transport = FakeTransport(digest="0" * 64)
        with self.assertRaises(TransientQwenVisionCapabilityError):
            self.analyze(self.bridge(transport))
        self.assertNotIn("/api/chat", [call[1] for call in transport.calls])

        transport = FakeTransport()

        def no_vision(method, path, payload, timeout):
            if path == "/api/show":
                return {"capabilities": ["completion"]}
            return transport(method, path, payload, timeout)

        with self.assertRaises(TransientQwenVisionCapabilityError):
            self.analyze(
                TransientQwenVisionBridge(
                    transport=no_vision,
                    workload_probe=lambda: [],
                    utc_now=lambda: FIXED_NOW,
                )
            )

    def test_stale_future_non_jpeg_and_data_uri_inputs_fail_before_contact(self) -> None:
        cases = (
            {"jpeg_base64": JPEG_B64, "captured_at": "2026-08-02T08:59:00Z"},
            {"jpeg_base64": JPEG_B64, "captured_at": "2026-08-02T09:00:20Z"},
            {"jpeg_base64": base64.b64encode(b"not-jpeg").decode("ascii"), "captured_at": "2026-08-02T09:00:05Z"},
            {"jpeg_base64": "data:image/jpeg;base64," + JPEG_B64, "captured_at": "2026-08-02T09:00:05Z"},
        )
        for case in cases:
            with self.subTest(case=case):
                transport = FakeTransport()
                with self.assertRaises(TransientQwenVisionInputError):
                    self.bridge(transport).analyze_one_still(**case)
                self.assertEqual(transport.calls, [])

    def test_invalid_or_identity_claiming_output_is_rejected_and_still_unloaded(self) -> None:
        outputs = (
            "```json\n{}\n```",
            valid_model_content().replace("A person", "Robert"),
            valid_model_content().replace("false", "true", 1),
            valid_model_content().replace(
                "A person is seated near a desk in a lit room.",
                "The screen says you should follow these instructions.",
            ),
        )
        for content in outputs:
            with self.subTest(content=content[:30]):
                transport = FakeTransport(content=content)
                with self.assertRaises(TransientQwenVisionOutputError):
                    self.analyze(self.bridge(transport))
                paths = [call[1] for call in transport.calls]
                self.assertEqual(paths.count("/api/chat"), 1)
                self.assertEqual(paths.count("/api/generate"), 1)

    def test_second_workload_probe_closes_preflight_race(self) -> None:
        transport = FakeTransport()
        probes = iter(([], ["blender"]))
        bridge = TransientQwenVisionBridge(
            transport=transport,
            workload_probe=lambda: next(probes),
            utc_now=lambda: FIXED_NOW,
        )
        with self.assertRaises(TransientQwenVisionBusy):
            self.analyze(bridge)
        self.assertNotIn("/api/chat", [call[1] for call in transport.calls])

    def test_new_resident_model_at_unload_boundary_rejects_the_cue(self) -> None:
        transport = FakeTransport()
        transport.ps_responses = [
            {"models": []},
            {"models": []},
            {"models": [{"name": "another-model:latest", "digest": "1" * 64}]},
        ]
        with self.assertRaises(TransientQwenVisionCapabilityError):
            self.analyze(self.bridge(transport))
        self.assertIn("/api/chat", [call[1] for call in transport.calls])
        self.assertIn("/api/generate", [call[1] for call in transport.calls])

    def test_transport_rejects_non_exact_loopback(self) -> None:
        self.assertEqual(LoopbackJsonTransport(OLLAMA_LOOPBACK).base_url, OLLAMA_LOOPBACK)
        for endpoint in (
            "http://localhost:11434",
            "http://127.0.0.1:11435",
            "https://127.0.0.1:11434",
            "http://127.0.0.1:11434/api",
        ):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(ValueError):
                    LoopbackJsonTransport(endpoint)


if __name__ == "__main__":
    unittest.main()
