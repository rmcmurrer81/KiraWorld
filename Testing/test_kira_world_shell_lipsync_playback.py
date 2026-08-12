from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from tools import kira_world_shell_server as shell


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOME_MAIN = (
    PROJECT_ROOT
    / "Data/world_builds/notebook_worlds/home_world/builds"
    / "home_world_main_house_20260630_223000/preview/src/main.js"
)


class KiraWorldShellLipSyncPlaybackTests(unittest.TestCase):
    def setUp(self) -> None:
        with shell.VOICE_OUTPUT_STATE_LOCK:
            self.original = dict(shell.VOICE_OUTPUT_STATE)
            shell.VOICE_OUTPUT_STATE.clear()
            shell.VOICE_OUTPUT_STATE.update(
                {
                    "revision": 0,
                    "active": False,
                    "playing": False,
                    "phase": "idle",
                    "candidate": "kira",
                    "label": "Kira",
                }
            )

    def tearDown(self) -> None:
        with shell.VOICE_OUTPUT_STATE_LOCK:
            shell.VOICE_OUTPUT_STATE.clear()
            shell.VOICE_OUTPUT_STATE.update(self.original)

    def test_real_playback_boundaries_drive_text_free_state(self) -> None:
        callback = shell._voice_benchmark_callback("")
        self.assertIsNotNone(callback)
        callback("chunk_synthesis_start", {"chunk_index": 0, "public_words": ["private"]})
        synthesizing = shell.voice_playback_state()
        self.assertFalse(synthesizing["playing"])
        self.assertEqual(synthesizing["phase"], "synthesizing")

        callback("chunk_playback_start", {"chunk_index": 0, "public_words": ["private"]})
        playing = shell.voice_playback_state()
        self.assertTrue(playing["playing"])
        self.assertEqual(playing["phase"], "playing")
        self.assertNotIn("public_words", playing)
        self.assertNotIn("text", playing)

        callback("chunk_playback_end", {"chunk_index": 0, "public_words": ["private"], "played": True})
        ended = shell.voice_playback_state()
        self.assertFalse(ended["playing"])
        self.assertEqual(ended["phase"], "waiting_continuation")
        self.assertGreater(ended["revision"], playing["revision"])

    def test_shell_polls_and_posts_playback_without_reply_text(self) -> None:
        with (
            patch.object(shell, "load_state", return_value={**shell.DEFAULT_STATE, "location": "home"}),
            patch.object(shell, "voice_message_inbox", return_value={"messages": [], "unread": 0}),
            patch.object(shell, "tablet_workspace_summary", return_value={"notes": 0, "pending_requests": 0}),
        ):
            html = shell.html_shell().decode("utf-8")
        self.assertIn('/api/voice-playback', html)
        self.assertIn('type: "kira-voice-playback"', html)
        self.assertIn('setInterval(refreshVoicePlayback, 100)', html)

    def test_runtime_mouth_snapshot_is_bounded_and_text_free(self) -> None:
        sanitized = shell._valid_kira_mouth_lipsync_snapshot(
            {
                "active": True,
                "version": "existing-lip-island-audio-playback-v2",
                "method": "existing_connected_lip_island_vertex_deformation",
                "meshName": "Object_85",
                "amount": 0.82,
                "peakAmount": 0.91,
                "openingDistance": 0.0064,
                "restored": False,
                "createdSceneNodes": 0,
                "secondMouthCreated": False,
                "deformationOnly": True,
                "sourceHasPhonemeMorphTargets": False,
                "sourceHasFacialBones": False,
                "visemeReady": False,
                "visualMotionProven": False,
                "playingMatchedActiveAvatar": True,
                "matchedPlaybackSegments": 3,
                "matchedPlaybackFrames": 180,
                "currentPlaybackFrames": 42,
                "lastMatchedRevision": 19,
                "lastCompletedPlaybackFrames": 61,
                "lastPlaybackPeakAmount": 0.84,
                "lastPlaybackPeakOpeningDistance": 0.0068,
                "sourceMeshes": ["private-scene-name"],
                "text": "private spoken words",
                "playback": {
                    "revision": 7,
                    "active": True,
                    "playing": True,
                    "phase": "playing",
                    "candidate": "kira",
                    "chunkIndex": 2,
                    "text": "private spoken words",
                },
            }
        )

        self.assertTrue(sanitized["active"])
        self.assertTrue(sanitized["playingMatchedActiveAvatar"])
        self.assertEqual(sanitized["matchedPlaybackSegments"], 3)
        self.assertEqual(sanitized["matchedPlaybackFrames"], 180)
        self.assertEqual(sanitized["lastCompletedPlaybackFrames"], 61)
        self.assertEqual(sanitized["lastPlaybackPeakOpeningDistance"], 0.0068)
        self.assertTrue(sanitized["playback"]["playing"])
        self.assertEqual(sanitized["openingDistance"], 0.0064)
        self.assertEqual(sanitized["createdSceneNodes"], 0)
        self.assertFalse(sanitized["secondMouthCreated"])
        self.assertTrue(sanitized["deformationOnly"])
        self.assertFalse(sanitized["sourceHasPhonemeMorphTargets"])
        self.assertFalse(sanitized["sourceHasFacialBones"])
        self.assertFalse(sanitized["visemeReady"])
        self.assertFalse(sanitized["visualMotionProven"])
        self.assertNotIn("text", sanitized)
        self.assertNotIn("sourceMeshes", sanitized)
        self.assertNotIn("text", sanitized["playback"])

    def test_live_snapshot_posts_existing_mouth_and_eye_diagnostics(self) -> None:
        source = HOME_MAIN.read_text(encoding="utf-8")
        self.assertIn(
            "kiraExistingMouthLipSync: activeAvatarIsKiraLike() ? kiraExistingMouthLipSyncProbe() : null",
            source,
        )
        self.assertIn(
            "kiraEyeRig: activeKiraEyeRig ? kiraEyeBindingProbe()",
            source,
        )
        self.assertIn('event.data?.type === "kira-voice-playback"', source)
        self.assertIn("voicePlaybackMatchesActiveAvatar()", source)
        self.assertIn("matchedPlaybackSegments: activeKiraMouthPlaybackEvidence.matchedPlaybackSegments", source)
        self.assertIn("lastPlaybackPeakOpeningDistance", source)

    def test_existing_mouth_fallback_does_not_claim_proven_viseme_lipsync(self) -> None:
        source = (
            PROJECT_ROOT
            / "Data/world_builds/notebook_worlds/home_world/builds"
            / "home_world_main_house_20260630_223000/preview/src/existing_mouth_lipsync.js"
        ).read_text(encoding="utf-8")
        self.assertIn("deformationOnly: true", source)
        self.assertIn("sourceHasPhonemeMorphTargets: false", source)
        self.assertIn("sourceHasFacialBones: false", source)
        self.assertIn("visemeReady: false", source)
        self.assertIn("visualMotionProven: false", source)

    def test_r6_body_review_status_reports_reversible_live_trial_truthfully(self) -> None:
        status = shell.kira_body_review_status()
        self.assertEqual(
            status["status"], "reversible_live_owner_review_trial_selected"
        )
        self.assertTrue(status["runtime_active"])
        self.assertTrue(status["activation_authorized"])
        self.assertTrue(status["current_runtime_unchanged"])
        self.assertTrue(status["original_live_asset_unchanged"])
        self.assertFalse(status["permanent_promotion_authorized"])
        self.assertIn("preserved", status["summary"])
        self.assertIn("clothing remains separate", status["summary"])
        self.assertIn("permanent promotion remain unapproved", status["summary"])


if __name__ == "__main__":
    unittest.main()
