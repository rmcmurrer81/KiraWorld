from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tools import kira_text_voice_asr_sidecar as asr
from tools import kira_world_shell_server as shell
from Core.shared_person_workbench import standalone_video_studio_access


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "kira_text_voice_device_capture.json"
DEVICE_SCRIPT_PATH = ROOT / "tools" / "kira_text_voice_devices.js"
LAUNCHER_PATH = ROOT / "Start_Kira_Text_Voice_Chat.bat"


class FakeWhisperModel:
    def __init__(self) -> None:
        self.received = b""
        self.options = {}

    def transcribe(self, source, **options):
        self.received = source.read()
        self.options = dict(options)
        segments = [
            SimpleNamespace(start=0.0, end=0.8, text=" camera test "),
            SimpleNamespace(start=0.8, end=1.3, text=" passed "),
        ]
        info = SimpleNamespace(language="en", language_probability=0.998)
        return iter(segments), info


class TextVoiceDeviceCaptureTests(unittest.TestCase):
    def test_device_config_is_fail_closed_and_keeps_devices_independent(self) -> None:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertEqual(config["surface"], "existing_kira_text_voice_chat")
        self.assertFalse(config["duplicate_person_selector_allowed"])
        self.assertFalse(config["startup_defaults"]["camera_on"])
        self.assertFalse(config["startup_defaults"]["microphone_on"])
        self.assertFalse(config["startup_defaults"]["raw_media_persistence"])
        self.assertTrue(config["device_policy"]["camera_and_microphone_are_independent"])
        self.assertTrue(config["device_policy"]["c920_video_with_separate_microphone_supported"])
        self.assertEqual(
            config["camera"]["vision_understanding_approved"],
            "sampled_coarse_cues_plus_owner_requested_transient_qwen_one_still",
        )
        self.assertTrue(config["camera"]["ongoing_semantic_observation_enabled"])
        self.assertFalse(config["camera"]["qwen3_5_9b_default_visual_backend"])
        self.assertTrue(config["camera"]["qwen3_5_9b_explicit_look_now_authorized"])
        self.assertFalse(config["camera"]["qwen3_5_9b_continuous_capture_authorized"])
        self.assertFalse(config["camera"]["identity_recognition_enabled"])
        self.assertFalse(config["microphone"]["automatic_send"])
        self.assertTrue(config["microphone"]["continuous_local_hearing_available"])
        self.assertTrue(config["microphone"]["voice_activity_segmentation"])
        self.assertTrue(config["microphone"]["synthesized_voice_playback_suppression"])
        self.assertTrue(config["microphone"]["hearing_does_not_force_attention_or_response"])
        self.assertFalse(config["asr_sidecar"]["package_or_chatterbox_mutation"])
        self.assertFalse(config["asr_sidecar"]["raw_audio_persisted"])
        self.assertTrue(config["asr_sidecar"]["exact_person_activation_lease_required"])
        self.assertTrue(config["visual_sidecar"]["loopback_only"])
        self.assertTrue(config["visual_sidecar"]["one_transient_jpeg_at_a_time"])
        self.assertFalse(config["visual_sidecar"]["raw_frame_persisted"])
        self.assertFalse(config["visual_sidecar"]["identity_inference_enabled"])
        self.assertFalse(config["visual_sidecar"]["qwen_used"])
        self.assertTrue(config["qwen_one_still"]["owner_authorized"])
        self.assertEqual(config["qwen_one_still"]["opt_in_action"], "Look Now (one still)")
        self.assertFalse(config["qwen_one_still"]["continuous_capture"])
        self.assertFalse(config["qwen_one_still"]["low_rate_sample_use"])
        self.assertTrue(config["qwen_one_still"]["qwen3_5_9b_remains_normal_text_default"])
        self.assertNotIn("llama_remains_normal_text_default", config["qwen_one_still"])
        self.assertEqual(config["qwen_one_still"]["model"], "qwen3.5:9b")
        self.assertEqual(
            config["qwen_one_still"]["exact_digest"],
            "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
        )
        self.assertTrue(config["qwen_one_still"]["serial_gpu_arbitration"])
        self.assertTrue(config["qwen_one_still"]["unload_qwen_after_each_still"])
        self.assertFalse(config["qwen_one_still"]["identity_inference_enabled"])
        self.assertFalse(config["qwen_one_still"]["appearance_memory_enabled"])
        self.assertFalse(config["qwen_one_still"]["raw_frame_persisted"])
        self.assertFalse(config["qwen_one_still"]["raw_frame_hashed"])
        self.assertTrue(
            config["person_binding"]["accepted_observation_requires_active_selected_person_match"]
        )
        self.assertTrue(config["person_binding"]["person_change_clears_temporary_visual_context"])
        self.assertTrue(config["person_binding"]["person_change_cancels_active_recording"])
        self.assertTrue(config["person_binding"]["person_change_clears_temporary_transcript"])

    def test_existing_text_voice_page_contains_one_person_selector_and_all_controls(self) -> None:
        with (
            mock.patch.object(shell, "TEXT_ONLY_CHAT_MODE", True),
            mock.patch.dict(
                os.environ,
                {
                    "KIRA_ASR_SESSION_TOKEN": "unit-test-token",
                    "KIRA_VISUAL_SESSION_TOKEN": "unit-test-visual-token",
                },
            ),
        ):
            page = shell.html_shell().decode("utf-8")
        self.assertEqual(page.count('id="candidate"'), 1)
        for control_id in (
            "cameraDevice",
            "microphoneDevice",
            "speakerDevice",
            "cameraPreview",
            "stillPreview",
            "lookNow",
            "cameraToggle",
            "cameraOff",
            "microphoneTest",
            "continuousHearingToggle",
            "microphoneMute",
            "speakerTest",
            "holdToTalk",
            "pushToTalkTranscript",
            "useTranscript",
            "mediaSearchText",
            "mediaSearchButton",
            "mediaResults",
            "mediaCoviewButton",
            "mediaOpenButton",
            "mediaStopButton",
        ):
            self.assertIn(f'id="{control_id}"', page)
        self.assertIn("Camera and microphone start OFF", page)
        self.assertIn("Visual cues: OFF", page)
        self.assertIn('data-asr-token="unit-test-token"', page)
        self.assertIn('data-visual-token="unit-test-visual-token"', page)
        self.assertIn("X-Kira-Shell-Token", page)
        self.assertIn('<script src="/kira-text-voice-devices.js"></script>', page)

    def test_world_surface_does_not_load_text_voice_device_script(self) -> None:
        with mock.patch.object(shell, "TEXT_ONLY_CHAT_MODE", False):
            page = shell.html_shell().decode("utf-8")
        self.assertIn('id="devicePanel" hidden', page)
        self.assertNotIn('<script src="/kira-text-voice-devices.js"></script>', page)

    def test_browser_contract_is_ephemeral_person_bound_and_not_auto_send(self) -> None:
        script = DEVICE_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("selected === active", script)
        self.assertIn('candidateEl.addEventListener("change"', script)
        self.assertIn("clearTemporaryVisualContext", script)
        self.assertIn("audio: false", script)
        self.assertIn("video: false", script)
        self.assertIn("audioBitsPerSecond: 96000", script)
        self.assertIn("raw audio discarded", script)
        self.assertIn("Press Send manually", script)
        self.assertIn("purgePersonBoundSensoryState", script)
        self.assertIn("continuousHearingLoop", script)
        self.assertIn("synthesizedVoicePlaying", script)
        self.assertIn('window.addEventListener("kira-chat-busy"', script)
        self.assertIn('window.addEventListener("kira-voice-pipeline-busy"', script)
        self.assertIn("conversationPipelineBusy", script)
        self.assertIn("voicePipelineBusy", script)
        self.assertIn("AbortController", script)
        self.assertIn("kiraNotifyLocalOutputStarted", script)
        self.assertIn('fetch("/api/sensory/cue"', script)
        self.assertIn('/api/derive-cues', script)
        self.assertIn('canvas.toBlob', script)
        self.assertIn('identity_inference_performed: false', script)
        self.assertIn("automatic_memory_write: false", script)
        self.assertIn('fetch("/api/sensory/qwen-look"', script)
        self.assertIn('if (reason === "look_now")', script)
        self.assertIn("deriveQwenOneStillCue(binding, blob, capturedAt)", script)
        self.assertIn('captureFrame("low_rate_sample")', script)
        qwen_call_gate = script.split('if (reason === "look_now")', 1)[1].split("await Promise.all", 1)[0]
        self.assertIn("deriveQwenOneStillCue", qwen_call_gate)
        low_rate_timer = next(
            line for line in script.splitlines() if 'captureFrame("low_rate_sample")' in line
        )
        self.assertNotIn("Qwen", low_rate_timer)
        self.assertIn("values.fill(0)", script)
        self.assertIn('transientJpegBase64 = ""', script)
        self.assertNotIn("localStorage", script)
        self.assertNotIn("indexedDB", script)
        self.assertNotIn("toDataURL", script)

    def test_low_rate_camera_sample_skips_draw_and_jpeg_while_chat_voice_or_visual_work_is_active(self) -> None:
        script = DEVICE_SCRIPT_PATH.read_text(encoding="utf-8")
        capture = script.split("async function captureFrame(reason)", 1)[1].split(
            "function stopCamera", 1
        )[0]
        early_skip = (
            'if (reason === "low_rate_sample" && '
            "(conversationPipelineBusy || voicePipelineBusy || visualFrameInFlight || qwenLookInFlight))"
        )
        self.assertEqual(capture.count(early_skip), 1)
        self.assertLess(capture.index(early_skip), capture.index("drawImage(cameraPreview"))
        self.assertLess(capture.index(early_skip), capture.index("canvasJpegBlob(stillPreview)"))

        server_source = (ROOT / "tools" / "kira_world_shell_server.py").read_text(
            encoding="utf-8"
        )
        busy = server_source.split("function setChatBusy(enabled)", 1)[1].split(
            "function renderTabletSummary", 1
        )[0]
        event = 'new CustomEvent("kira-chat-busy"'
        self.assertEqual(busy.count(event), 1)
        self.assertIn("detail: {{ busy: chatInFlight }}", busy)
        self.assertLess(busy.index(event), busy.index('document.querySelector("#chatText")'))

        voice_poll = server_source.split("async function refreshVoicePlayback()", 1)[1].split(
            "function setObserveFollowButton", 1
        )[0]
        voice_event = 'new CustomEvent("kira-voice-pipeline-busy"'
        self.assertEqual(voice_poll.count(voice_event), 1)
        self.assertIn("busy: playback.active === true", voice_poll)
        self.assertIn('phase: String(playback.phase || "idle")', voice_poll)
        self.assertLess(voice_poll.index(voice_event), voice_poll.index("kiraSetPersonVoicePlaybackState"))

    def test_launcher_pins_model_and_creates_per_session_asr_token(self) -> None:
        launcher = LAUNCHER_PATH.read_text(encoding="utf-8")
        self.assertIn('set "KIRA_MODEL_NAME=qwen3.5:9b"', launcher)
        self.assertIn(
            'set "KIRA_MODEL_DIGEST=6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"',
            launcher,
        )
        self.assertIn('set "KIRA_ASR_PORT=8770"', launcher)
        self.assertIn('secrets.token_urlsafe(32)', launcher)
        self.assertIn('do set "KIRA_ASR_SESSION_TOKEN=%%T"', launcher)
        self.assertIn('set "KIRA_VISUAL_PORT=8771"', launcher)
        self.assertIn('do set "KIRA_VISUAL_SESSION_TOKEN=%%T"', launcher)
        self.assertNotIn("%RANDOM%", launcher)
        self.assertNotIn("KIRA_MODEL_NAME=llama3.1:8b", launcher)

    def test_text_voice_server_starts_both_loopback_sensory_sidecars(self) -> None:
        with (
            mock.patch.object(shell, "TEXT_ONLY_CHAT_MODE", True),
            mock.patch.dict(
                os.environ,
                {
                    "KIRA_ASR_SESSION_TOKEN": "asr-token",
                    "KIRA_VISUAL_SESSION_TOKEN": "visual-token",
                    "KIRA_ASR_PORT": "8770",
                    "KIRA_VISUAL_PORT": "8771",
                },
            ),
            mock.patch.object(shell.subprocess, "Popen") as popen,
        ):
            processes = shell.start_processes()
        self.assertEqual(len(processes), 2)
        commands = [call.args[0] for call in popen.call_args_list]
        self.assertTrue(any("kira_text_voice_asr_sidecar.py" in " ".join(command) for command in commands))
        self.assertTrue(any("kira_text_voice_visual_perception_sidecar.py" in " ".join(command) for command in commands))
        visual_call = next(
            call for call in popen.call_args_list
            if "kira_text_voice_visual_perception_sidecar.py" in " ".join(call.args[0])
        )
        self.assertEqual(visual_call.kwargs["env"]["KIRA_VISUAL_SESSION_TOKEN"], "visual-token")
        self.assertNotIn("KIRA_ASR_SESSION_TOKEN", visual_call.kwargs["env"])
        asr_call = next(
            call for call in popen.call_args_list
            if "kira_text_voice_asr_sidecar.py" in " ".join(call.args[0])
        )
        self.assertNotIn("KIRA_VISUAL_SESSION_TOKEN", asr_call.kwargs["env"])
        self.assertEqual(
            visual_call.kwargs["env"]["KIRA_SENSORY_LEASE_SECRET"],
            shell.SENSORY_LEASE_SECRET,
        )

    def test_video_studio_access_is_person_state_independent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            launcher = (
                root
                / "VideoStudioDevelopment"
                / "chat_first_production"
                / "START_CHAT_FIRST_STUDIO.bat"
            )
            launcher.parent.mkdir(parents=True)
            launcher.write_text("@echo off\n", encoding="utf-8")
            allowed = standalone_video_studio_access(root)
            self.assertTrue(allowed["allowed"])
            self.assertEqual(allowed["mode"], "standalone_owner_decision")
            self.assertIsNone(allowed["person_id"])
            self.assertFalse(allowed["person_state_inspected"])
            self.assertFalse(allowed["person_state_mutated"])
            self.assertFalse(allowed["automatic_person_studio_switching"])
            self.assertFalse(allowed["active_person_count_condition"])
            self.assertFalse(allowed["automatic_publication"])

    def test_shell_studio_button_is_always_enabled_and_never_auto_switches(self) -> None:
        source = (ROOT / "tools" / "kira_world_shell_server.py").read_text(encoding="utf-8")
        self.assertIn('videoStudioButton.disabled = false', source)
        self.assertIn('videoStudioButton.textContent = "Open Video Studio"', source)
        self.assertNotIn("Stop Person Before Video Studio", source)
        self.assertNotIn("must manually stop", source)
        self.assertIn('api("/api/open-video-studio", {{ standalone: true }})', source)
        self.assertIn('"event": "video_studio_opened_owner_decision"', source)
        self.assertIn('"person_state_inspected": False', source)
        self.assertIn('"person_state_mutated": False', source)
        self.assertIn('"automatic_person_studio_switching": False', source)
        click_route = source.split(
            'document.querySelector("#openVideoStudio").onclick', 1
        )[1].split('messageModalEl.onclick', 1)[0]
        self.assertNotIn("state.active_candidate", click_route)
        self.assertNotIn("confirm(", click_route)
        route = source.split('if path == "/api/open-video-studio":', 1)[1].split(
            'state = load_state()', 1
        )[0]
        self.assertNotIn("active_candidate", route)
        self.assertNotIn("active_people", route)
        self.assertNotIn("safe_stop_active_ai", route)
        self.assertNotIn("save_state", route)
        self.assertNotIn("/api/activate", route)
        self.assertNotIn("/api/deactivate", route)
        for forbidden in (
            "begin_voice_session",
            "end_voice_session",
            "update_voice_output_state",
            "personal_workbench",
            "LIFE_LOOP_LOG",
        ):
            self.assertNotIn(forbidden, route)

    def test_studio_endpoint_launches_without_reading_or_writing_person_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            launcher = Path(temporary) / "START_CHAT_FIRST_STUDIO.bat"
            launcher.write_text("@echo off\n", encoding="utf-8")
            responses: list[tuple[int, dict]] = []
            handler = object.__new__(shell.Handler)
            handler.path = "/api/open-video-studio"
            handler._body = lambda: {"standalone": False, "active_people": ["kira", "lisa"]}
            handler._json = lambda status, payload: responses.append((status, payload))
            access = {
                "allowed": True,
                "mode": "standalone_owner_decision",
                "launcher": str(launcher),
                "person_state_inspected": False,
                "person_state_mutated": False,
                "lifecycle_action": "none",
                "automatic_person_studio_switching": False,
                "automatic_publication": False,
            }
            with (
                mock.patch.object(shell, "load_state") as load_state,
                mock.patch.object(shell, "standalone_video_studio_access", return_value=access),
                mock.patch.object(shell.subprocess, "Popen") as popen,
                mock.patch.object(shell, "append_jsonl") as append_log,
                mock.patch.object(shell, "save_state") as save_state,
                mock.patch.object(shell, "safe_stop_active_ai") as safe_stop,
            ):
                handler.do_POST()
            self.assertEqual(responses[0][0], 200)
            self.assertTrue(responses[0][1]["ok"])
            self.assertFalse(responses[0][1]["person_state_inspected"])
            self.assertFalse(responses[0][1]["person_state_mutated"])
            popen.assert_called_once()
            load_state.assert_not_called()
            save_state.assert_not_called()
            safe_stop.assert_not_called()
            self.assertNotEqual(shell.STUDIO_ACCESS_LOG, shell.LIFE_LOOP_LOG)
            self.assertEqual(append_log.call_args.args[0], shell.STUDIO_ACCESS_LOG)
            event = append_log.call_args.args[1]
            self.assertEqual(event["event"], "video_studio_opened_owner_decision")
            self.assertFalse(event["person_state_inspected"])
            self.assertFalse(event["person_state_mutated"])
            self.assertFalse(event["automatic_publication"])

    def test_asr_health_is_cache_only_and_never_claims_vision(self) -> None:
        health = asr.health_payload()
        self.assertEqual(health["service"], "kira_text_voice_asr_sidecar")
        self.assertTrue(health["process_isolated"])
        self.assertTrue(health["cache_only"])
        self.assertFalse(health["raw_audio_persisted"])
        self.assertFalse(health["automatic_send"])
        self.assertFalse(health["visual_understanding_enabled"])
        self.assertTrue(health["person_activation_lease_required"])
        self.assertEqual(health["model_id"], "Systran/faster-whisper-small.en")

    def test_asr_transcribes_from_memory_and_returns_editable_unsent_text(self) -> None:
        fake = FakeWhisperModel()
        payload = b"not-a-real-container-but-model-is-stubbed"
        result = asr.transcribe_audio_bytes(payload, model=fake)
        self.assertEqual(fake.received, payload)
        self.assertIsInstance(io.BytesIO(payload), io.BytesIO)
        self.assertEqual(result["text"], "camera test passed")
        self.assertEqual(result["audio_bytes_received"], len(payload))
        self.assertFalse(result["raw_audio_persisted"])
        self.assertTrue(result["editable_before_send"])
        self.assertFalse(result["automatic_send"])
        self.assertEqual(fake.options["language"], "en")
        self.assertTrue(fake.options["vad_filter"])
        self.assertFalse(fake.options["condition_on_previous_text"])

    def test_asr_rejects_empty_and_oversized_audio(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty audio"):
            asr.transcribe_audio_bytes(b"", model=FakeWhisperModel())
        with self.assertRaisesRegex(ValueError, "exceeds"):
            asr.transcribe_audio_bytes(b"x" * (asr.MAX_AUDIO_BYTES + 1), model=FakeWhisperModel())


if __name__ == "__main__":
    unittest.main()
