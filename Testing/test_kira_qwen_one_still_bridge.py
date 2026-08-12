from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from Core.ephemeral_sensory_buffer import EphemeralSensoryBuffer
from Core.sensory_lease import issue_sensory_lease
from Core.transient_qwen_vision import (
    QWEN_VISION_DIGEST,
    QWEN_VISION_MODEL,
    TransientQwenVisionBusy,
    TransientQwenVisionInputError,
)
from tools import kira_world_shell_server as shell


class FakeBridge:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def analyze_one_still(self, *, jpeg_base64: str, captured_at: str):
        self.calls.append({"jpeg_base64": jpeg_base64, "captured_at": captured_at})
        return {
            "scene_summary": "A person is seated near a desk in a lit room.",
            "visible_elements": ["person", "desk", "chair"],
            "screen_text_status": "PRESENT_NOT_USED",
            "uncertainties": ["Small details are unclear."],
            "captured_at_utc": "2026-08-02T09:00:05Z",
            "inference_started_at_utc": "2026-08-02T09:00:06Z",
            "inference_completed_at_utc": "2026-08-02T09:00:08Z",
            "inference_elapsed_seconds": 2.0,
        }


class KiraQwenOneStillShellBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_buffer = shell.SENSORY_BUFFER
        self.original_voice_state = dict(shell.VOICE_OUTPUT_STATE)
        shell.SENSORY_BUFFER = EphemeralSensoryBuffer(
            ttl_seconds=45.0,
            max_count=16,
            max_derived_bytes=8192,
        )
        shell.VOICE_OUTPUT_STATE.update(
            {
                "active": False,
                "playing": False,
                "phase": "idle",
            }
        )
        while not shell.VOICE_REPLY_QUEUE.empty():
            shell.VOICE_REPLY_QUEUE.get_nowait()
            shell.VOICE_REPLY_QUEUE.task_done()
        self.state = {
            "active_candidate": "kira",
            "last_activation_at": "qwen-one-still-r1",
        }
        self.lease = shell.SENSORY_BUFFER.activate("kira", self.state["last_activation_at"])
        self.token = issue_sensory_lease(
            shell.SENSORY_LEASE_SECRET,
            person_id="kira",
            activation_revision=self.state["last_activation_at"],
            ttl_seconds=90,
            nonce=self.lease.session_nonce,
        )

    def tearDown(self) -> None:
        current = shell.SENSORY_BUFFER.current_lease
        if current is not None:
            shell.SENSORY_BUFFER.deactivate(current)
        shell.SENSORY_BUFFER = self.original_buffer
        shell.VOICE_OUTPUT_STATE.clear()
        shell.VOICE_OUTPUT_STATE.update(self.original_voice_state)

    def invoke(self, bridge: FakeBridge | None = None):
        with patch.object(shell, "load_state", return_value=dict(self.state)):
            return shell.accept_transient_qwen_visual_look(
                self.state,
                sensory_token=self.token,
                person_id="kira",
                activation_revision=self.state["last_activation_at"],
                captured_at="2026-08-02T09:00:05Z",
                jpeg_base64="transient-test-only",
                bridge=bridge or FakeBridge(),
            )

    def test_success_creates_only_person_bound_short_lived_derived_cue(self) -> None:
        bridge = FakeBridge()
        result = self.invoke(bridge)

        self.assertEqual(len(bridge.calls), 1)
        self.assertEqual(result["person_id"], "kira")
        self.assertEqual(result["model"], QWEN_VISION_MODEL)
        self.assertEqual(result["model_digest"], QWEN_VISION_DIGEST)
        self.assertEqual(result["identity_status"], "NOT_EVALUATED")
        self.assertFalse(result["automatic_spoken_response"])
        self.assertFalse(result["automatic_memory_write"])
        snapshot = shell.SENSORY_BUFFER.snapshot(self.lease)
        cue = snapshot["factual_cues"][0]
        self.assertEqual(cue["fact"]["event"], "qwen_transient_one_still")
        self.assertEqual(cue["source"]["kind"], "local_qwen_vision_one_still")
        self.assertTrue(cue["source"]["person_session_bound"])
        self.assertLessEqual(cue["ttl_remaining_seconds"], 45.0)
        self.assertGreater(cue["ttl_remaining_seconds"], 0.0)
        self.assertIn("cue_created_at_utc", cue["attributes"])
        self.assertIn("cue_expires_at_utc", cue["attributes"])
        serialized = json.dumps(snapshot).casefold()
        self.assertNotIn("transient-test-only", serialized)
        self.assertNotIn("jpeg_base64", serialized)
        self.assertNotIn("scene_description_logged", serialized)
        self.assertFalse(cue["attributes"]["identity_inference_performed"])
        self.assertFalse(cue["attributes"]["appearance_memory_used"])
        self.assertFalse(cue["attributes"]["automatic_memory_write"])

    def test_wrong_person_or_revision_never_reaches_bridge(self) -> None:
        for person, revision in (("robert", "qwen-one-still-r1"), ("kira", "old-r0")):
            with self.subTest(person=person, revision=revision):
                bridge = FakeBridge()
                with self.assertRaises(TransientQwenVisionInputError):
                    with patch.object(shell, "load_state", return_value=dict(self.state)):
                        shell.accept_transient_qwen_visual_look(
                            self.state,
                            sensory_token=self.token,
                            person_id=person,
                            activation_revision=revision,
                            captured_at="2026-08-02T09:00:05Z",
                            jpeg_base64="transient-test-only",
                            bridge=bridge,
                        )
                self.assertEqual(bridge.calls, [])

    def test_rollback_environment_switch_disables_only_qwen_one_still(self) -> None:
        bridge = FakeBridge()
        with (
            patch.dict(os.environ, {"KIRA_ENABLE_QWEN_ONE_STILL": "0"}),
            self.assertRaises(shell.TransientQwenVisionCapabilityError),
        ):
            self.invoke(bridge)
        self.assertEqual(bridge.calls, [])

    def test_chat_or_voice_activity_fails_closed_before_bridge(self) -> None:
        bridge = FakeBridge()
        shell.CHAT_REPLY_LOCK.acquire()
        try:
            with self.assertRaises(TransientQwenVisionBusy):
                self.invoke(bridge)
        finally:
            shell.CHAT_REPLY_LOCK.release()
        self.assertEqual(bridge.calls, [])

        shell.VOICE_OUTPUT_STATE["active"] = True
        with self.assertRaises(TransientQwenVisionBusy):
            self.invoke(bridge)
        self.assertEqual(bridge.calls, [])

    def test_activation_change_during_inference_discards_result(self) -> None:
        changed = {
            "active_candidate": "robert",
            "last_activation_at": "qwen-one-still-r2",
        }
        bridge = FakeBridge()
        with patch.object(shell, "load_state", side_effect=[dict(self.state), changed]):
            with self.assertRaises(TransientQwenVisionInputError):
                shell.accept_transient_qwen_visual_look(
                    self.state,
                    sensory_token=self.token,
                    person_id="kira",
                    activation_revision=self.state["last_activation_at"],
                    captured_at="2026-08-02T09:00:05Z",
                    jpeg_base64="transient-test-only",
                    bridge=bridge,
                )
        self.assertEqual(len(bridge.calls), 1)
        self.assertEqual(shell.SENSORY_BUFFER.stats(self.lease)["factual_cue_count"], 0)


if __name__ == "__main__":
    unittest.main()
