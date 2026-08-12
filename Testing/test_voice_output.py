import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

import voice_output  # noqa: E402
from voice_output import (  # noqa: E402
    VoiceOutputConfig,
    apply_speech_emotion,
    clean_text_for_speech,
    infer_speech_emotion,
    load_voice_config,
    load_kira_production_voice_config,
    postprocess_chatterbox_samples,
    release_voice_output,
    speak_text_chunks_streaming,
    speak_text,
    synthesize_text_to_wav,
    warm_voice_output,
)


class VoiceOutputTests(unittest.TestCase):
    def test_kira_production_loader_is_gpu_first_and_cannot_be_forced_to_sapi(self) -> None:
        with patch.dict(
            os.environ,
            {
                "KIRA_VOICE_FORCE_SAPI": "1",
                "KIRA_CHATTERBOX_DEVICE": "auto",
            },
        ):
            config = load_kira_production_voice_config()

        self.assertEqual(config.engine, "chatterbox_tts")
        self.assertEqual(
            config.chatterbox_reference_audio,
            voice_output.KIRA_APPROVED_REFERENCE_RELATIVE,
        )
        self.assertEqual(config.chatterbox_device, "auto")
        routing = voice_output._kira_chatterbox_sidecar_binding(config)
        self.assertIsNotNone(routing)
        self.assertEqual(
            [route["route_id"] for route in routing["routes"] if route["valid"]],
            ["blackwell_gpu", "sealed_cpu"],
        )
        self.assertFalse(routing["policy"]["sapi_fallback_allowed"])
        self.assertFalse(routing["policy"]["generic_voice_fallback_allowed"])

    def test_exact_kira_chatterbox_reference_routes_to_sealed_sidecar(self) -> None:
        text = "This is public spoken text for Kira."
        config = VoiceOutputConfig(
            engine="chatterbox_tts",
            chatterbox_reference_audio=(
                "Voice/reference_packs/kira/kira_online_source_20260706_221447/"
                "model_input/approved_reference.wav"
            ),
            play_audio=False,
        )
        expected = {"generated": True, "reason": "mocked_sidecar", "sidecar": True, "text": text}
        with (
            patch.object(voice_output, "_synthesize_with_kira_chatterbox_sidecar", return_value=expected) as sidecar,
            patch.object(voice_output, "_synthesize_with_chatterbox_to_wav") as in_process,
        ):
            result = synthesize_text_to_wav(text, "unused.wav", config)

        self.assertEqual(result, expected)
        sidecar.assert_called_once()
        in_process.assert_not_called()

    def test_invalid_exact_kira_router_fails_closed_without_in_process_or_sapi(self) -> None:
        config = VoiceOutputConfig(
            engine="chatterbox_tts",
            chatterbox_reference_audio=voice_output.KIRA_APPROVED_REFERENCE_RELATIVE,
            play_audio=False,
        )
        with (
            patch.object(
                voice_output,
                "_load_approved_voice_routing_config",
                return_value={
                    "valid": False,
                    "reason": "approved_voice_routing_contract_failed",
                    "issues": ["fixture"],
                },
            ),
            patch.object(voice_output, "_synthesize_with_chatterbox_to_wav") as in_process,
            patch.object(voice_output, "_build_windows_sapi_command") as sapi,
        ):
            result = synthesize_text_to_wav("Public words.", "unused.wav", config)

        self.assertFalse(result["generated"])
        self.assertEqual(result["reason"], "approved_voice_routing_contract_failed")
        self.assertFalse(result["generic_voice_used"])
        in_process.assert_not_called()
        sapi.assert_not_called()

    def test_exact_kira_reference_cannot_be_forced_to_sapi(self) -> None:
        config = VoiceOutputConfig(
            engine="windows_sapi_powershell",
            chatterbox_reference_audio=voice_output.KIRA_APPROVED_REFERENCE_RELATIVE,
            play_audio=False,
        )
        with (
            patch.object(voice_output.subprocess, "run") as process,
            patch.object(voice_output, "_build_windows_sapi_command") as sapi,
        ):
            result = synthesize_text_to_wav("Public words.", "unused.wav", config)
        self.assertFalse(result["generated"])
        self.assertEqual(
            result["reason"],
            "exact_kira_reference_requires_approved_chatterbox_routes",
        )
        self.assertFalse(result["sapi_fallback_used"])
        process.assert_not_called()
        sapi.assert_not_called()

    def test_non_kira_chatterbox_reference_keeps_existing_in_process_route(self) -> None:
        config = VoiceOutputConfig(
            engine="chatterbox_tts",
            chatterbox_reference_audio="Voice/reference_packs/other/approved_reference.wav",
            play_audio=False,
        )
        expected = {"generated": True, "reason": "mocked_existing_route"}
        with (
            patch.object(voice_output, "_synthesize_with_kira_chatterbox_sidecar") as sidecar,
            patch.object(voice_output, "_synthesize_with_chatterbox_to_wav", return_value=expected) as in_process,
        ):
            result = synthesize_text_to_wav("Public words.", "unused.wav", config)

        self.assertEqual(result, expected)
        sidecar.assert_not_called()
        in_process.assert_called_once()

    def test_cpu_sidecar_request_is_hash_bound_offline_cuda_hidden_and_credential_free(self) -> None:
        config = VoiceOutputConfig(
            engine="chatterbox_tts",
            chatterbox_reference_audio=(
                "Voice/reference_packs/kira/kira_online_source_20260706_221447/"
                "model_input/approved_reference.wav"
            ),
            play_audio=False,
        )
        text = "Only this public spoken sentence may reach Kira's approved voice."
        scratch_root = voice_output.PROJECT_ROOT / "RecoverySprint" / "verification_scratch"
        scratch_root.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(dir=str(scratch_root)) as temp_value:
            target = Path(temp_value) / "sidecar_contract.wav"

            route = next(
                item
                for item in voice_output._load_approved_voice_routing_config()["routes"]
                if item["route_id"] == "sealed_cpu"
            )

            def fake_run(*_args, **kwargs):
                request = json.loads(kwargs["input"])
                target.write_bytes(b"RIFF-sidecar-contract")
                response = {
                    "generated": True,
                    "reason": "ok",
                    "engine": "chatterbox_tts",
                    "device": "cpu",
                    "request_id": request["request_id"],
                    "text_sha256": request["text_sha256"],
                    "requested_text_bound": True,
                    "reference_sha256": request["reference_sha256"],
                    "playback": False,
                    "generic_voice_used": False,
                    "voice_identity_status": "reviewed_reference_chatterbox",
                    "audio_path": str(target.resolve()),
                }
                self.assertEqual(request["channel"], "public_spoken_only")
                self.assertEqual(request["text"], text)
                self.assertEqual(request["text_sha256"], hashlib.sha256(text.encode()).hexdigest())
                self.assertEqual(kwargs["env"]["HF_HUB_OFFLINE"], "1")
                self.assertEqual(kwargs["env"]["TRANSFORMERS_OFFLINE"], "1")
                self.assertEqual(kwargs["env"]["CUDA_VISIBLE_DEVICES"], "")
                self.assertNotIn("HF_TOKEN", kwargs["env"])
                return subprocess.CompletedProcess(_args, 0, json.dumps(response), "")

            with (
                patch.dict(os.environ, {"HF_TOKEN": "must-not-reach-sidecar"}),
                patch.object(voice_output.subprocess, "run", side_effect=fake_run),
            ):
                result = voice_output._synthesize_with_approved_sidecar(
                    text, target, config, route
                )

            self.assertTrue(result["generated"], result)
            self.assertTrue(result["sidecar"])
            self.assertFalse(result["playback"])

    def test_hash_bound_router_manifest_has_exact_gpu_then_cpu_routes(self) -> None:
        routing = voice_output._load_approved_voice_routing_config()
        self.assertTrue(routing["valid"], routing)
        self.assertEqual(
            [item["route_id"] for item in routing["routes"]],
            ["blackwell_gpu", "sealed_cpu"],
        )
        self.assertTrue(all(item["valid"] for item in routing["routes"]), routing)
        self.assertEqual(
            routing["approved_reference_sha256"],
            voice_output.KIRA_APPROVED_REFERENCE_SHA256,
        )
        self.assertFalse(routing["policy"]["generic_voice_fallback_allowed"])
        self.assertFalse(routing["policy"]["sapi_fallback_allowed"])
        self.assertFalse(routing["policy"]["unsealed_in_process_fallback_allowed"])

    def test_gpu_environment_is_restricted_controlled_and_cpu_stays_cuda_hidden(self) -> None:
        with patch.dict(
            os.environ,
            {
                "USERNAME": "Robert",
                "USERPROFILE": r"C:\\Users\\Robert",
                "SystemRoot": r"C:\\Windows",
                "PATH": r"C:\\Windows\\System32",
                "HF_TOKEN": "must-not-cross",
            },
            clear=True,
        ):
            gpu = voice_output._chatterbox_sidecar_environment(
                {"route_id": "blackwell_gpu"}
            )
            cpu = voice_output._chatterbox_sidecar_environment(
                {"route_id": "sealed_cpu"}
            )
        self.assertEqual(gpu["USERNAME"], "Robert")
        self.assertEqual(gpu["CUDA_VISIBLE_DEVICES"], "0")
        self.assertEqual(gpu["HF_HUB_OFFLINE"], "1")
        self.assertEqual(gpu["TRANSFORMERS_OFFLINE"], "1")
        controlled = voice_output.BLACKWELL_RUNTIME_CACHE_ROOT.resolve()
        for key in ("TORCHINDUCTOR_CACHE_DIR", "TRITON_CACHE_DIR", "TEMP", "TMP"):
            Path(gpu[key]).resolve().relative_to(controlled)
        self.assertNotIn("HF_TOKEN", gpu)
        self.assertEqual(cpu["CUDA_VISIBLE_DEVICES"], "")
        self.assertEqual(cpu["HF_HUB_OFFLINE"], "1")
        self.assertNotIn("TORCHINDUCTOR_CACHE_DIR", cpu)
        self.assertNotIn("HF_TOKEN", cpu)

    def test_qwen_residency_probe_is_read_only_loopback_and_fails_closed(self) -> None:
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return json.dumps(
                    {
                        "models": [
                            {
                                "name": "qwen3.5:9b",
                                "model": "qwen3.5:9b",
                                "digest": voice_output.KIRA_QWEN_DIGEST,
                            }
                        ]
                    }
                ).encode()

        opener = SimpleNamespace(open=lambda request, timeout: Response())
        with patch.object(
            voice_output.urllib_request, "build_opener", return_value=opener
        ) as build:
            resident = voice_output._qwen_residency_evidence()
        self.assertTrue(resident["query_succeeded"])
        self.assertFalse(resident["qwen_absent_proven"])
        self.assertFalse(resident["model_state_changed"])
        build.assert_called_once()

        failing = SimpleNamespace(open=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("offline")))
        with patch.object(
            voice_output.urllib_request, "build_opener", return_value=failing
        ):
            unknown = voice_output._qwen_residency_evidence()
        self.assertFalse(unknown["query_succeeded"])
        self.assertFalse(unknown["qwen_absent_proven"])
        self.assertFalse(unknown["model_state_changed"])

    def test_gpu_first_then_cpu_fallback_reports_actual_approved_path(self) -> None:
        routes = [
            {"route_id": "blackwell_gpu", "role": "preferred", "valid": True},
            {"route_id": "sealed_cpu", "role": "automatic_fallback_only", "valid": True},
        ]
        routing = {
            "valid": True,
            "routing_id": "fixture",
            "routing_config_sha256": "a" * 64,
            "routes": routes,
        }
        config = VoiceOutputConfig(
            engine="chatterbox_tts",
            chatterbox_reference_audio=voice_output.KIRA_APPROVED_REFERENCE_RELATIVE,
            play_audio=False,
        )
        synthesis_order: list[str] = []

        def synth(_text, _target, _cfg, route):
            synthesis_order.append(route["route_id"])
            if route["route_id"] == "blackwell_gpu":
                return {"generated": False, "reason": "approved_sidecar_process_error"}
            return {"generated": True, "reason": "ok", "route_id": "sealed_cpu"}

        with (
            patch.object(voice_output, "_load_approved_voice_routing_config", return_value=routing),
            patch.object(
                voice_output,
                "_qwen_residency_evidence",
                return_value={"query_succeeded": True, "qwen_absent_proven": True},
            ),
            patch.object(
                voice_output,
                "_run_approved_sidecar_self_check",
                return_value={"ready": True, "reason": "approved_sidecar_ready"},
            ),
            patch.object(voice_output, "_synthesize_with_approved_sidecar", side_effect=synth),
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Public words.", Path("unused.wav"), config
            )

        self.assertTrue(result["generated"])
        self.assertEqual(synthesis_order, ["blackwell_gpu", "sealed_cpu"])
        self.assertEqual(result["approved_voice_path_used"], "sealed_cpu")
        self.assertTrue(result["approved_voice_routing"]["automatic_cpu_fallback_used"])
        self.assertEqual(
            result["approved_voice_routing"]["preferred_failure_reason"],
            "gpu_synthesis_or_contract_failed",
        )
        self.assertEqual(
            [item["status"] for item in result["approved_voice_attempts"]],
            ["synthesis_failed", "used"],
        )

    def test_qwen_resident_blocks_gpu_and_independently_uses_cpu(self) -> None:
        routes = [
            {"route_id": "blackwell_gpu", "role": "preferred", "valid": True},
            {"route_id": "sealed_cpu", "role": "automatic_fallback_only", "valid": True},
        ]
        routing = {
            "valid": True,
            "routing_id": "fixture",
            "routing_config_sha256": "b" * 64,
            "routes": routes,
        }
        config = VoiceOutputConfig(
            engine="chatterbox_tts",
            chatterbox_reference_audio=voice_output.KIRA_APPROVED_REFERENCE_RELATIVE,
            play_audio=False,
        )
        checked: list[str] = []

        def self_check(route):
            checked.append(route["route_id"])
            return {"ready": True, "reason": "approved_sidecar_ready"}

        def synth(_text, _target, _cfg, route):
            return {"generated": True, "reason": "ok", "route_id": route["route_id"]}

        residency = {
            "query_succeeded": True,
            "qwen_absent_proven": False,
            "qwen_records": [{"name": "qwen3.5:9b", "digest": voice_output.KIRA_QWEN_DIGEST}],
            "model_state_changed": False,
        }
        with (
            patch.object(voice_output, "_load_approved_voice_routing_config", return_value=routing),
            patch.object(voice_output, "_qwen_residency_evidence", return_value=residency),
            patch.object(voice_output, "_run_approved_sidecar_self_check", side_effect=self_check),
            patch.object(voice_output, "_synthesize_with_approved_sidecar", side_effect=synth),
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Public words.", Path("unused.wav"), config
            )

        self.assertTrue(result["generated"])
        self.assertEqual(checked, ["sealed_cpu"])
        self.assertEqual(result["approved_voice_path_used"], "sealed_cpu")
        self.assertEqual(result["approved_voice_attempts"][0]["reason"], "qwen_absence_not_proven")
        self.assertFalse(result["approved_voice_routing"]["arbitrary_model_unload_performed"])

    def test_qwen_still_resident_after_gpu_self_check_fails_over_before_synthesis(self) -> None:
        routes = [
            {"route_id": "blackwell_gpu", "role": "preferred", "valid": True},
            {"route_id": "sealed_cpu", "role": "automatic_fallback_only", "valid": True},
        ]
        routing = {
            "valid": True,
            "routing_id": "fixture",
            "routing_config_sha256": "d" * 64,
            "routes": routes,
        }
        config = VoiceOutputConfig(
            engine="chatterbox_tts",
            chatterbox_reference_audio=voice_output.KIRA_APPROVED_REFERENCE_RELATIVE,
            play_audio=False,
        )
        residency = [
            {"query_succeeded": True, "qwen_absent_proven": True},
            {
                "query_succeeded": True,
                "qwen_absent_proven": False,
                "qwen_records": [{"name": "qwen3.5:9b"}],
            },
        ]
        synthesized: list[str] = []

        def synth(_text, _target, _cfg, route):
            synthesized.append(route["route_id"])
            return {"generated": True, "reason": "ok", "route_id": route["route_id"]}

        with (
            patch.object(voice_output, "_load_approved_voice_routing_config", return_value=routing),
            patch.object(voice_output, "_qwen_residency_evidence", side_effect=residency),
            patch.object(
                voice_output,
                "_run_approved_sidecar_self_check",
                return_value={"ready": True, "reason": "approved_sidecar_ready"},
            ),
            patch.object(voice_output, "_synthesize_with_approved_sidecar", side_effect=synth),
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Public words.", Path("unused.wav"), config
            )

        self.assertEqual(synthesized, ["sealed_cpu"])
        self.assertEqual(result["approved_voice_path_used"], "sealed_cpu")
        self.assertEqual(
            result["approved_voice_routing"]["preferred_failure_reason"],
            "qwen_remained_resident_after_gpu_self_check",
        )

    def test_gpu_self_check_failure_uses_only_sealed_cpu_fallback(self) -> None:
        routes = [
            {"route_id": "blackwell_gpu", "role": "preferred", "valid": True},
            {"route_id": "sealed_cpu", "role": "automatic_fallback_only", "valid": True},
        ]
        routing = {
            "valid": True,
            "routing_id": "fixture",
            "routing_config_sha256": "e" * 64,
            "routes": routes,
        }
        config = VoiceOutputConfig(
            engine="chatterbox_tts",
            chatterbox_reference_audio=voice_output.KIRA_APPROVED_REFERENCE_RELATIVE,
            play_audio=False,
        )

        def self_check(route):
            if route["route_id"] == "blackwell_gpu":
                return {"ready": False, "reason": "approved_sidecar_self_check_process_error"}
            return {"ready": True, "reason": "approved_sidecar_ready"}

        with (
            patch.object(voice_output, "_load_approved_voice_routing_config", return_value=routing),
            patch.object(
                voice_output,
                "_qwen_residency_evidence",
                return_value={"query_succeeded": True, "qwen_absent_proven": True},
            ),
            patch.object(voice_output, "_run_approved_sidecar_self_check", side_effect=self_check),
            patch.object(
                voice_output,
                "_synthesize_with_approved_sidecar",
                return_value={"generated": True, "reason": "ok", "route_id": "sealed_cpu"},
            ) as synth,
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Public words.", Path("unused.wav"), config
            )

        self.assertEqual(result["approved_voice_path_used"], "sealed_cpu")
        self.assertEqual(synth.call_count, 1)
        self.assertEqual(synth.call_args.args[3]["route_id"], "sealed_cpu")
        self.assertEqual(
            result["approved_voice_routing"]["preferred_failure_reason"],
            "gpu_self_check_failed",
        )

    def test_qwen_absent_uses_gpu_without_touching_cpu(self) -> None:
        routes = [
            {"route_id": "blackwell_gpu", "role": "preferred", "valid": True},
            {"route_id": "sealed_cpu", "role": "automatic_fallback_only", "valid": True},
        ]
        routing = {
            "valid": True,
            "routing_id": "fixture",
            "routing_config_sha256": "c" * 64,
            "routes": routes,
        }
        config = VoiceOutputConfig(
            engine="chatterbox_tts",
            chatterbox_reference_audio=voice_output.KIRA_APPROVED_REFERENCE_RELATIVE,
            play_audio=False,
        )
        with (
            patch.object(voice_output, "_load_approved_voice_routing_config", return_value=routing),
            patch.object(
                voice_output,
                "_qwen_residency_evidence",
                return_value={"query_succeeded": True, "qwen_absent_proven": True},
            ),
            patch.object(
                voice_output,
                "_run_approved_sidecar_self_check",
                return_value={"ready": True, "reason": "approved_sidecar_ready"},
            ) as self_check,
            patch.object(
                voice_output,
                "_synthesize_with_approved_sidecar",
                return_value={"generated": True, "reason": "ok", "route_id": "blackwell_gpu"},
            ) as synth,
        ):
            result = voice_output._synthesize_with_kira_chatterbox_sidecar(
                "Public words.", Path("unused.wav"), config
            )

        self.assertEqual(result["approved_voice_path_used"], "blackwell_gpu")
        self.assertTrue(result["approved_voice_routing"]["preferred_path_used"])
        self.assertEqual(self_check.call_count, 1)
        self.assertEqual(synth.call_count, 1)

    def test_blackwell_successful_self_check_is_cached_for_exact_session_contract(self) -> None:
        routing = voice_output._load_approved_voice_routing_config()
        route = next(item for item in routing["routes"] if item["route_id"] == "blackwell_gpu")
        config = route["sidecar_config"]
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "ready": True,
                    "reason": "sealed_blackwell_sidecar_ready",
                    "sidecar_id": config["sidecar_id"],
                    "reference_sha256": voice_output.KIRA_APPROVED_REFERENCE_SHA256,
                    "runtime_cuda_checks": {
                        "cuda_available": True,
                        "device": True,
                        "capability": True,
                        "sm_120": True,
                    },
                    "playback": False,
                    "model_loaded": False,
                    "production_preferred": False,
                }
            ),
            stderr="",
        )
        voice_output._clear_approved_sidecar_self_check_cache()
        try:
            with patch.object(voice_output.subprocess, "run", return_value=completed) as process:
                first = voice_output._run_approved_sidecar_self_check(route)
                second = voice_output._run_approved_sidecar_self_check(route)
        finally:
            voice_output._clear_approved_sidecar_self_check_cache()

        self.assertTrue(first["ready"])
        self.assertTrue(second["ready"])
        self.assertEqual(first["self_check_cache"]["status"], "miss_stored")
        self.assertEqual(second["self_check_cache"]["status"], "hit")
        self.assertEqual(
            first["self_check_cache"]["key_sha256"],
            second["self_check_cache"]["key_sha256"],
        )
        self.assertEqual(len(first["self_check_cache"]["key_sha256"]), 64)
        self.assertFalse(second["self_check_cache"]["synthesis_cached"])
        self.assertFalse(second["self_check_cache"]["qwen_absence_cached"])
        self.assertEqual(process.call_count, 1)

    def test_blackwell_self_check_cache_key_changes_with_restricted_environment(self) -> None:
        routing = voice_output._load_approved_voice_routing_config()
        route = next(item for item in routing["routes"] if item["route_id"] == "blackwell_gpu")
        config = route["sidecar_config"]
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "ready": True,
                    "sidecar_id": config["sidecar_id"],
                    "reference_sha256": voice_output.KIRA_APPROVED_REFERENCE_SHA256,
                    "runtime_cuda_checks": {"all_required_cuda_gates": True},
                    "playback": False,
                    "model_loaded": False,
                }
            ),
            stderr="",
        )
        voice_output._clear_approved_sidecar_self_check_cache()
        try:
            with patch.object(voice_output.subprocess, "run", return_value=completed) as process:
                with patch.dict(os.environ, {"PATH": "self-check-cache-environment-a"}):
                    first = voice_output._run_approved_sidecar_self_check(route)
                with patch.dict(os.environ, {"PATH": "self-check-cache-environment-b"}):
                    second = voice_output._run_approved_sidecar_self_check(route)
        finally:
            voice_output._clear_approved_sidecar_self_check_cache()

        self.assertEqual(first["self_check_cache"]["status"], "miss_stored")
        self.assertEqual(second["self_check_cache"]["status"], "miss_stored")
        self.assertNotEqual(
            first["self_check_cache"]["key_sha256"],
            second["self_check_cache"]["key_sha256"],
        )
        self.assertEqual(process.call_count, 2)

    def test_blackwell_failed_self_check_is_never_cached(self) -> None:
        routing = voice_output._load_approved_voice_routing_config()
        route = next(item for item in routing["routes"] if item["route_id"] == "blackwell_gpu")
        config = route["sidecar_config"]
        failed = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout=json.dumps(
                {
                    "ready": False,
                    "reason": "fixture_failure",
                    "sidecar_id": config["sidecar_id"],
                    "reference_sha256": voice_output.KIRA_APPROVED_REFERENCE_SHA256,
                    "runtime_cuda_checks": {"cuda_available": False},
                    "playback": False,
                    "model_loaded": False,
                }
            ),
            stderr="fixture failure",
        )
        passed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "ready": True,
                    "sidecar_id": config["sidecar_id"],
                    "reference_sha256": voice_output.KIRA_APPROVED_REFERENCE_SHA256,
                    "runtime_cuda_checks": {"all_required_cuda_gates": True},
                    "playback": False,
                    "model_loaded": False,
                }
            ),
            stderr="",
        )
        voice_output._clear_approved_sidecar_self_check_cache()
        try:
            with patch.object(voice_output.subprocess, "run", side_effect=[failed, passed]) as process:
                first = voice_output._run_approved_sidecar_self_check(route)
                second = voice_output._run_approved_sidecar_self_check(route)
                third = voice_output._run_approved_sidecar_self_check(route)
        finally:
            voice_output._clear_approved_sidecar_self_check_cache()

        self.assertFalse(first["ready"])
        self.assertEqual(first["self_check_cache"]["status"], "miss_not_stored")
        self.assertTrue(second["ready"])
        self.assertEqual(second["self_check_cache"]["status"], "miss_stored")
        self.assertEqual(third["self_check_cache"]["status"], "hit")
        self.assertEqual(process.call_count, 2)

    def test_session_cache_never_reuses_the_cpu_fallback_self_check(self) -> None:
        routing = voice_output._load_approved_voice_routing_config()
        route = next(item for item in routing["routes"] if item["route_id"] == "sealed_cpu")
        config = route["sidecar_config"]
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "ready": True,
                    "sidecar_id": config["sidecar_id"],
                    "reference_sha256": voice_output.KIRA_APPROVED_REFERENCE_SHA256,
                    "playback": False,
                    "model_loaded": False,
                }
            ),
            stderr="",
        )
        voice_output._clear_approved_sidecar_self_check_cache()
        try:
            with patch.object(voice_output.subprocess, "run", return_value=completed) as process:
                first = voice_output._run_approved_sidecar_self_check(route)
                second = voice_output._run_approved_sidecar_self_check(route)
        finally:
            voice_output._clear_approved_sidecar_self_check_cache()

        self.assertTrue(first["ready"])
        self.assertTrue(second["ready"])
        self.assertNotIn("self_check_cache", first)
        self.assertNotIn("self_check_cache", second)
        self.assertEqual(process.call_count, 2)

    def test_cached_blackwell_self_check_still_rechecks_qwen_before_each_synthesis(self) -> None:
        routing = voice_output._load_approved_voice_routing_config()
        route = next(item for item in routing["routes"] if item["route_id"] == "blackwell_gpu")
        config_data = route["sidecar_config"]
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "ready": True,
                    "sidecar_id": config_data["sidecar_id"],
                    "reference_sha256": voice_output.KIRA_APPROVED_REFERENCE_SHA256,
                    "runtime_cuda_checks": {"all_required_cuda_gates": True},
                    "playback": False,
                    "model_loaded": False,
                }
            ),
            stderr="",
        )
        config = VoiceOutputConfig(
            engine="chatterbox_tts",
            chatterbox_reference_audio=voice_output.KIRA_APPROVED_REFERENCE_RELATIVE,
            play_audio=False,
        )
        voice_output._clear_approved_sidecar_self_check_cache()
        try:
            with (
                patch.object(voice_output.subprocess, "run", return_value=completed) as process,
                patch.object(
                    voice_output,
                    "_qwen_residency_evidence",
                    side_effect=lambda: {
                        "query_succeeded": True,
                        "qwen_absent_proven": True,
                        "qwen_records": [],
                    },
                ) as qwen_probe,
                patch.object(
                    voice_output,
                    "_synthesize_with_approved_sidecar",
                    return_value={
                        "generated": True,
                        "reason": "ok",
                        "route_id": "blackwell_gpu",
                    },
                ) as synthesis,
            ):
                first = voice_output._synthesize_with_kira_chatterbox_sidecar(
                    "First public sentence.", Path("unused-first.wav"), config
                )
                second = voice_output._synthesize_with_kira_chatterbox_sidecar(
                    "Second public sentence.", Path("unused-second.wav"), config
                )
        finally:
            voice_output._clear_approved_sidecar_self_check_cache()

        self.assertTrue(first["generated"])
        self.assertTrue(second["generated"])
        self.assertEqual(
            second["approved_voice_attempts"][0]["self_check"]["self_check_cache"]["status"],
            "hit",
        )
        self.assertEqual(qwen_probe.call_count, 4)
        self.assertEqual(process.call_count, 1)
        self.assertEqual(synthesis.call_count, 2)
        self.assertTrue(
            all(call.args[3]["route_id"] == "blackwell_gpu" for call in synthesis.call_args_list)
        )
        safe_audit = voice_output._safe_approved_voice_route_evidence(second)
        self.assertEqual(safe_audit["blackwell_self_check_cache_status"], "hit")
        self.assertEqual(safe_audit["blackwell_self_check_cache_scope"], "current_python_process")
        self.assertRegex(
            safe_audit["blackwell_self_check_cache_key_sha256"],
            r"^[0-9a-f]{64}$",
        )

    def test_real_wav_router_projects_cache_miss_and_hit_through_stream_telemetry(self) -> None:
        routing = voice_output._load_approved_voice_routing_config()
        route = next(item for item in routing["routes"] if item["route_id"] == "blackwell_gpu")
        config_data = route["sidecar_config"]
        self_check_process = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "ready": True,
                    "sidecar_id": config_data["sidecar_id"],
                    "reference_sha256": voice_output.KIRA_APPROVED_REFERENCE_SHA256,
                    "runtime_cuda_checks": {"all_required_cuda_gates": True},
                    "playback": False,
                    "model_loaded": False,
                }
            ),
            stderr="",
        )

        def fake_synthesis(text, target, _cfg, used_route):
            return {
                "generated": True,
                "reason": "ok",
                "engine": "chatterbox_tts",
                "route_id": used_route["route_id"],
                "device": "cuda",
                "text": text,
                "audio_path": str(target),
                "gpu_proof": {"actual_gpu_allocation": True},
                "gpu_utilization_observed": True,
                "playback": False,
                "generic_voice_used": False,
            }

        cache_root = voice_output.PROJECT_ROOT / "RecoverySprint" / "runtime_cache"
        cache_root.mkdir(parents=True, exist_ok=True)
        voice_output._clear_approved_sidecar_self_check_cache()
        first_events: list[tuple[str, dict]] = []
        second_events: list[tuple[str, dict]] = []
        try:
            with tempfile.TemporaryDirectory(dir=cache_root) as output_dir:
                config = VoiceOutputConfig(
                    engine="chatterbox_tts",
                    chatterbox_reference_audio=voice_output.KIRA_APPROVED_REFERENCE_RELATIVE,
                    output_dir=output_dir,
                    play_audio=True,
                )
                with (
                    patch.object(
                        voice_output.subprocess,
                        "run",
                        return_value=self_check_process,
                    ) as process,
                    patch.object(
                        voice_output,
                        "_qwen_residency_evidence",
                        side_effect=lambda: {
                            "query_succeeded": True,
                            "qwen_absent_proven": True,
                            "qwen_records": [],
                        },
                    ) as qwen_probe,
                    patch.object(
                        voice_output,
                        "_synthesize_with_approved_sidecar",
                        side_effect=fake_synthesis,
                    ) as synthesis,
                    patch.object(
                        voice_output,
                        "play_wav_file",
                        return_value={"played": True, "reason": "ok"},
                    ),
                ):
                    first = speak_text_chunks_streaming(
                        ["First public sentence."],
                        config,
                        event_callback=lambda event, payload: first_events.append((event, payload)),
                    )
                    second = speak_text_chunks_streaming(
                        ["Second public sentence."],
                        config,
                        event_callback=lambda event, payload: second_events.append((event, payload)),
                    )
        finally:
            voice_output._clear_approved_sidecar_self_check_cache()

        first_end = next(payload for event, payload in first_events if event == "chunk_synthesis_end")
        second_end = next(payload for event, payload in second_events if event == "chunk_synthesis_end")
        first_chunk = first["chunk_results"][0]
        second_chunk = second["chunk_results"][0]
        self.assertEqual(first_end["blackwell_self_check_cache_status"], "miss_stored")
        self.assertEqual(first_chunk["blackwell_self_check_cache_status"], "miss_stored")
        self.assertEqual(second_end["blackwell_self_check_cache_status"], "hit")
        self.assertEqual(second_chunk["blackwell_self_check_cache_status"], "hit")
        self.assertEqual(second_chunk["blackwell_self_check_cache_scope"], "current_python_process")
        self.assertRegex(
            second_chunk["blackwell_self_check_cache_key_sha256"],
            r"^[0-9a-f]{64}$",
        )
        self.assertEqual(
            first_chunk["blackwell_self_check_cache_key_sha256"],
            second_chunk["blackwell_self_check_cache_key_sha256"],
        )
        # The shell's life-log projection invokes this sanitizer again.  The
        # flat evidence must survive that second projection unchanged.
        reprojected = voice_output._safe_approved_voice_route_evidence(second_chunk)
        self.assertEqual(reprojected["blackwell_self_check_cache_status"], "hit")
        self.assertEqual(
            reprojected["blackwell_self_check_cache_key_sha256"],
            second_chunk["blackwell_self_check_cache_key_sha256"],
        )
        self.assertEqual(process.call_count, 1)
        self.assertEqual(qwen_probe.call_count, 4)
        self.assertEqual(synthesis.call_count, 2)

    def test_auto_chatterbox_device_requires_proven_vram_headroom(self) -> None:
        enough = SimpleNamespace(
            cuda=SimpleNamespace(
                is_available=lambda: True,
                mem_get_info=lambda: (8 * 1024**3, 16 * 1024**3),
            )
        )
        low = SimpleNamespace(
            cuda=SimpleNamespace(
                is_available=lambda: True,
                mem_get_info=lambda: (4 * 1024**3, 16 * 1024**3),
            )
        )
        unknown = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: True))
        cfg = VoiceOutputConfig(chatterbox_device="auto")
        with patch.dict("os.environ", {"KIRA_CHATTERBOX_MIN_FREE_VRAM_MIB": "6144"}):
            self.assertEqual(voice_output._resolve_chatterbox_device(cfg, enough), "cuda")
            self.assertEqual(voice_output._resolve_chatterbox_device(cfg, low), "cpu")
            self.assertEqual(voice_output._resolve_chatterbox_device(cfg, unknown), "cpu")

    def test_auto_prewarm_falls_back_to_cpu_without_generating_audio(self) -> None:
        class FakeModel:
            sr = 24000

        loaded_devices: list[str] = []

        def load(device: str):
            loaded_devices.append(device)
            if device == "cuda":
                raise RuntimeError("synthetic CUDA out of memory")
            return FakeModel()

        fake_tts_module = ModuleType("chatterbox.tts")
        fake_tts_module.ChatterboxTTS = SimpleNamespace(from_pretrained=load)
        fake_chatterbox = ModuleType("chatterbox")
        fake_chatterbox.__path__ = []
        fake_torch = ModuleType("torch")
        fake_torch.cuda = SimpleNamespace(
            is_available=lambda: True,
            mem_get_info=lambda: (8 * 1024**3, 16 * 1024**3),
            empty_cache=lambda: None,
        )
        cfg = VoiceOutputConfig(engine="chatterbox_tts", chatterbox_device="auto", play_audio=True)
        with (
            patch.dict(
                sys.modules,
                {"torch": fake_torch, "chatterbox": fake_chatterbox, "chatterbox.tts": fake_tts_module},
            ),
            patch.object(voice_output, "_CHATTERBOX_MODEL", None),
            patch.object(voice_output, "_CHATTERBOX_DEVICE", None),
            patch.object(voice_output, "_schedule_chatterbox_idle_unload_locked", return_value=False),
            patch.object(voice_output, "_play_wav") as play,
        ):
            result = warm_voice_output(cfg)
            release_voice_output()

        self.assertTrue(result["warmed"])
        self.assertEqual(result["device"], "cpu")
        self.assertEqual(result["auto_device_fallback"], "cpu_after_cuda_prewarm_error")
        self.assertEqual(loaded_devices, ["cuda", "cpu"])
        play.assert_not_called()

    def test_chatterbox_prewarm_loads_model_without_generation_or_playback(self) -> None:
        class FakeModel:
            sr = 24000

            def generate(self, *args, **kwargs):
                raise AssertionError("prewarm must not generate audio")

        model = FakeModel()
        fake_tts_module = ModuleType("chatterbox.tts")
        fake_tts_module.ChatterboxTTS = SimpleNamespace(from_pretrained=lambda device: model)
        fake_chatterbox = ModuleType("chatterbox")
        fake_chatterbox.__path__ = []
        fake_torch = ModuleType("torch")
        fake_torch.cuda = SimpleNamespace(is_available=lambda: False, empty_cache=lambda: None)
        config = VoiceOutputConfig(engine="chatterbox_tts", chatterbox_device="cpu", play_audio=True)

        with (
            patch.dict(
                sys.modules,
                {"torch": fake_torch, "chatterbox": fake_chatterbox, "chatterbox.tts": fake_tts_module},
            ),
            patch.object(voice_output, "_CHATTERBOX_MODEL", None),
            patch.object(voice_output, "_CHATTERBOX_DEVICE", None),
            patch.object(voice_output, "_schedule_chatterbox_idle_unload_locked", return_value=False),
            patch.object(voice_output, "_play_wav") as play,
        ):
            warmed = warm_voice_output(config)
            released = release_voice_output()

        self.assertTrue(warmed["warmed"])
        self.assertEqual(warmed["reason"], "model_loaded")
        self.assertFalse(warmed["generated_audio"])
        self.assertFalse(warmed["playback"])
        self.assertTrue(released["released"])
        play.assert_not_called()

    def test_expression_hint_changes_sapi_approximation_without_mutating_base(self) -> None:
        base = VoiceOutputConfig(rate=-1, volume=90)
        adjusted, emotion = apply_speech_emotion(base, "I'm excited to see you!")
        self.assertEqual(emotion, "excited")
        self.assertGreater(adjusted.rate, base.rate)
        self.assertGreater(adjusted.volume, base.volume)
        self.assertEqual(base.rate, -1)
        self.assertEqual(infer_speech_emotion("I'm sorry you're feeling lonely."), "gentle")

    def test_single_exclamation_does_not_force_fast_excited_delivery(self) -> None:
        base = VoiceOutputConfig(rate=-1, volume=92)
        adjusted, emotion = apply_speech_emotion(base, "I'm glad to see you again!")

        self.assertEqual(emotion, "warm")
        self.assertEqual(adjusted.rate, base.rate)

    def test_clean_text_removes_markdown_and_limits_length(self) -> None:
        text = "**Kira** says [hello](http://example.com) `Robert`.\n```py\nprint('x')\n```"

        cleaned = clean_text_for_speech(text, max_chars=30)

        self.assertNotIn("**", cleaned)
        self.assertNotIn("http://", cleaned)
        self.assertNotIn("```", cleaned)
        self.assertLessEqual(len(cleaned), 30)

    def test_dry_run_does_not_speak(self) -> None:
        result = speak_text("Hello Robert.", VoiceOutputConfig(dry_run=True))

        self.assertFalse(result["spoken"])
        self.assertEqual(result["reason"], "dry_run")
        self.assertEqual(result["text"], "Hello Robert.")

    def test_disabled_config_does_not_speak(self) -> None:
        result = speak_text("Hello Robert.", VoiceOutputConfig(enabled=False))

        self.assertFalse(result["spoken"])
        self.assertEqual(result["reason"], "voice_output_disabled")

    def test_dry_run_does_not_create_wav(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "message.wav"
            result = synthesize_text_to_wav("Hello Robert.", output, VoiceOutputConfig(dry_run=True))

            self.assertFalse(result["generated"])
            self.assertEqual(result["reason"], "dry_run")
            self.assertFalse(output.exists())

    def test_load_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "voice.json"
            path.write_text(
                json.dumps(
                    {
                        "enabled": True,
                        "engine": "windows_sapi_powershell",
                        "voice_name": "Example",
                        "rate": 2,
                        "volume": 80,
                        "max_chars": 100,
                        "dry_run": True,
                    }
                ),
                encoding="utf-8",
            )

            config = load_voice_config(path)

        self.assertEqual(config.voice_name, "Example")
        self.assertEqual(config.rate, 2)
        self.assertEqual(config.volume, 80)
        self.assertEqual(config.max_chars, 100)
        self.assertTrue(config.dry_run)

    def test_default_chatterbox_pcm_postprocess_is_identity(self) -> None:
        import numpy as np

        samples = np.asarray([-0.25, 0.0, 0.25], dtype=np.float32)
        processed, audit = postprocess_chatterbox_samples(
            samples,
            sample_rate=24000,
            config=VoiceOutputConfig(),
        )

        np.testing.assert_allclose(processed, samples, rtol=0.0, atol=0.0)
        self.assertFalse(audit["applied"])
        self.assertEqual(audit["application_count"], 1)
        self.assertEqual(audit["clipped_sample_count"], 0)
        self.assertFalse(audit["pitch_changed"])

    def test_profile_pcm_gain_is_applied_once_without_clipping(self) -> None:
        import numpy as np

        sample_rate = 24000
        seconds = 0.25
        timeline = np.arange(int(sample_rate * seconds), dtype=np.float32) / sample_rate
        samples = (0.50 * np.sin(2.0 * np.pi * 1000.0 * timeline)).astype(np.float32)
        config = VoiceOutputConfig(
            pcm_output_gain_db=-9.5,
            proximity_cut_hz=95.0,
            proximity_cut_mix=0.3,
        )

        processed, audit = postprocess_chatterbox_samples(
            samples,
            sample_rate=sample_rate,
            config=config,
        )

        expected_gain = 10.0 ** (-9.5 / 20.0)
        measured_gain = float(np.sqrt(np.mean(processed.astype(np.float64) ** 2))) / float(
            np.sqrt(np.mean(samples.astype(np.float64) ** 2))
        )
        self.assertAlmostEqual(measured_gain, expected_gain, delta=0.003)
        self.assertTrue(audit["applied"])
        self.assertEqual(audit["application_count"], 1)
        self.assertEqual(audit["gain_db"], -9.5)
        self.assertEqual(audit["clipped_sample_count"], 0)
        self.assertLess(audit["post_peak"], audit["pre_peak"])
        self.assertFalse(audit["pitch_changed"])

    def test_chatterbox_wav_route_preserves_full_text_for_internal_chunking(self) -> None:
        text = "This complete message is deliberately longer than the configured live chunk limit."
        config = VoiceOutputConfig(
            engine="chatterbox_tts",
            chatterbox_reference_audio="Voice/reference.wav",
            max_chars=20,
            play_audio=False,
        )
        expected = {"generated": True, "reason": "mocked", "text": text}
        with patch.object(
            voice_output,
            "_synthesize_with_chatterbox_to_wav",
            return_value=expected,
        ) as render:
            result = synthesize_text_to_wav(text, "unused.wav", config)

        self.assertEqual(result, expected)
        self.assertEqual(render.call_args.args[0], text)
        self.assertGreater(len(render.call_args.args[0]), config.max_chars)

    def test_chatterbox_message_writer_retries_signal_gate_and_never_plays(self) -> None:
        import numpy as np

        class FakeModel:
            sr = 8000

            def __init__(self) -> None:
                self.calls = 0

            def generate(self, text, audio_prompt_path):
                self.calls += 1
                words = max(1, len(text.split()))
                sample_count = max(2000, int(words * 0.20 * self.sr))
                if self.calls == 1:
                    return np.zeros(sample_count, dtype=np.float32)
                return np.full(sample_count, 0.08, dtype=np.float32)

        model = FakeModel()
        fake_tts_module = ModuleType("chatterbox.tts")
        fake_tts_module.ChatterboxTTS = SimpleNamespace(from_pretrained=lambda device: model)
        fake_chatterbox = ModuleType("chatterbox")
        fake_chatterbox.__path__ = []
        fake_torch = ModuleType("torch")
        fake_torch.cuda = SimpleNamespace(is_available=lambda: False, empty_cache=lambda: None)

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "reference.wav").write_bytes(b"reviewed-reference-placeholder")
            output = root / "message.wav"
            config = VoiceOutputConfig(
                engine="chatterbox_tts",
                chatterbox_reference_audio="reference.wav",
                chatterbox_device="cpu",
                play_audio=True,
                pcm_output_gain_db=-9.5,
                proximity_cut_hz=95.0,
                proximity_cut_mix=0.3,
            )
            with (
                patch.dict(
                    sys.modules,
                    {
                        "torch": fake_torch,
                        "chatterbox": fake_chatterbox,
                        "chatterbox.tts": fake_tts_module,
                    },
                ),
                patch.object(voice_output, "PROJECT_ROOT", root),
                patch.object(voice_output, "_CHATTERBOX_MODEL", None),
                patch.object(voice_output, "_CHATTERBOX_DEVICE", None),
                patch.object(voice_output, "_schedule_chatterbox_idle_unload_locked", return_value=False),
                patch.object(voice_output, "_play_wav") as play,
            ):
                result = synthesize_text_to_wav(
                    "A complete saved message should pass the non-silent signal gate.",
                    output,
                    config,
                )

            self.assertTrue(result["generated"])
            self.assertFalse(result["playback"])
            self.assertEqual(result["voice_identity_status"], "reviewed_reference_chatterbox")
            self.assertEqual(result["chunk_checks"][0]["attempt"], 2)
            self.assertEqual(result["audio_postprocess"]["application_count_per_chunk"], 1)
            self.assertTrue(result["audio_postprocess"]["chunks"][0]["applied"])
            self.assertEqual(result["audio_postprocess"]["chunks"][0]["gain_db"], -9.5)
            self.assertEqual(result["audio_postprocess"]["chunks"][0]["clipped_sample_count"], 0)
            self.assertTrue(output.is_file())
            play.assert_not_called()

    def test_idle_unload_timer_ignores_a_cancelled_stale_callback(self) -> None:
        created = []

        class FakeTimer:
            def __init__(self, interval, callback, args=()):
                self.interval = interval
                self.callback = callback
                self.args = args
                self.cancelled = False
                self.daemon = False
                created.append(self)

            def start(self):
                return None

            def cancel(self):
                self.cancelled = True

        with (
            patch.dict("os.environ", {"KIRA_VOICE_IDLE_UNLOAD_SECONDS": "10"}),
            patch.object(voice_output.threading, "Timer", FakeTimer),
            patch.object(voice_output, "_CHATTERBOX_MODEL", object()),
            patch.object(voice_output, "_release_chatterbox_model_locked") as release,
        ):
            with voice_output._CHATTERBOX_LOCK:
                voice_output._schedule_chatterbox_idle_unload_locked()
                voice_output._schedule_chatterbox_idle_unload_locked()
            self.assertTrue(created[0].cancelled)
            created[0].callback(*created[0].args)
            release.assert_not_called()
            created[1].callback(*created[1].args)
            release.assert_called_once_with()

    def test_live_chatterbox_retries_implausible_chunk_before_playback(self) -> None:
        import numpy as np

        class FakeModel:
            sr = 8000

            def __init__(self) -> None:
                self.calls = 0

            def generate(self, text, audio_prompt_path):
                self.calls += 1
                samples = max(2000, int(max(1, len(text.split())) * 0.20 * self.sr))
                return np.full(samples, 0.07 if self.calls > 1 else 0.0, dtype=np.float32)

        model = FakeModel()
        fake_tts_module = ModuleType("chatterbox.tts")
        fake_tts_module.ChatterboxTTS = SimpleNamespace(from_pretrained=lambda device: model)
        fake_chatterbox = ModuleType("chatterbox")
        fake_chatterbox.__path__ = []
        fake_torch = ModuleType("torch")
        fake_torch.cuda = SimpleNamespace(is_available=lambda: False, empty_cache=lambda: None)

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "reference.wav").write_bytes(b"reviewed-reference-placeholder")
            config = VoiceOutputConfig(
                engine="chatterbox_tts",
                chatterbox_reference_audio="reference.wav",
                chatterbox_device="cpu",
                output_dir="generated",
                play_audio=True,
                pcm_output_gain_db=-9.5,
                proximity_cut_hz=95.0,
                proximity_cut_mix=0.3,
            )
            with (
                patch.dict(
                    sys.modules,
                    {"torch": fake_torch, "chatterbox": fake_chatterbox, "chatterbox.tts": fake_tts_module},
                ),
                patch.object(voice_output, "PROJECT_ROOT", root),
                patch.object(voice_output, "_CHATTERBOX_MODEL", None),
                patch.object(voice_output, "_CHATTERBOX_DEVICE", None),
                patch.object(voice_output, "_schedule_chatterbox_idle_unload_locked", return_value=False),
                patch.object(voice_output, "_play_wav", return_value={"played": True, "reason": "ok"}) as play,
            ):
                result = speak_text("Every word in this live chunk should have plausible audio duration.", config)

        self.assertTrue(result["spoken"])
        self.assertEqual(result["signal_check"]["attempt"], 2)
        self.assertTrue(result["signal_check"]["passed"])
        self.assertTrue(result["audio_postprocess"]["applied"])
        self.assertEqual(result["audio_postprocess"]["application_count"], 1)
        self.assertEqual(result["audio_postprocess"]["gain_db"], -9.5)
        self.assertEqual(result["audio_postprocess"]["clipped_sample_count"], 0)
        play.assert_called_once()

    def test_bounded_chunk_pipeline_overlaps_generation_and_ordered_playback(self) -> None:
        played: list[str] = []
        benchmark_events: list[tuple[str, dict]] = []

        def fake_synthesize(text, output_path, _config):
            time.sleep(0.04)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(b"RIFF-test")
            return {"generated": True, "reason": "ok", "audio_path": str(output_path), "text": text}

        def fake_play(path):
            played.append(Path(path).name)
            time.sleep(0.08)
            return {"played": True, "reason": "ok", "audio_path": str(path)}

        cfg = VoiceOutputConfig(engine="chatterbox_tts", output_dir="generated", play_audio=True)
        started = time.perf_counter()
        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch.object(voice_output, "PROJECT_ROOT", Path(tmpdir)),
                patch.object(voice_output, "synthesize_text_to_wav", side_effect=fake_synthesize),
                patch.object(voice_output, "play_wav_file", side_effect=fake_play),
            ):
                result = speak_text_chunks_streaming(
                    ["First complete thought.", "Second complete thought.", "Third complete thought."],
                    cfg,
                    event_callback=lambda event, payload: benchmark_events.append((event, payload)),
                )
        elapsed = time.perf_counter() - started

        self.assertTrue(result["spoken"])
        self.assertTrue(result["complete"])
        self.assertEqual(result["reason"], "ok")
        self.assertEqual(result["pipeline"], "bounded_chunk_prefetch_v1")
        self.assertEqual(3, result["played_chunk_count"])
        self.assertEqual(played, sorted(played))
        self.assertLess(elapsed, 0.34)  # serial generation + playback would be about 0.36 s
        self.assertLess(result["max_continuation_gap_seconds"], 0.03)
        event_names = [event for event, _payload in benchmark_events]
        self.assertEqual(event_names.count("chunk_synthesis_start"), 3)
        self.assertEqual(event_names.count("chunk_synthesis_end"), 3)
        self.assertEqual(event_names.count("chunk_playback_start"), 3)
        self.assertEqual(event_names.count("chunk_playback_end"), 3)
        self.assertEqual(event_names.count("first_playback_proxy"), 1)
        first_proxy = next(payload for event, payload in benchmark_events if event == "first_playback_proxy")
        self.assertEqual(first_proxy["first_audible_proxy_kind"], "playback_api_call_start_not_owner_observed_audible")
        self.assertIsNone(first_proxy["owner_true_first_audible_monotonic_ms"])
        self.assertTrue(all(isinstance(payload.get("monotonic_ns"), int) for _event, payload in benchmark_events))

    def test_bounded_chunk_pipeline_never_labels_partial_audio_complete(self) -> None:
        calls = 0

        def fake_synthesize(text, output_path, _config):
            nonlocal calls
            calls += 1
            if calls == 2:
                return {"generated": False, "reason": "synthetic_failure", "text": text}
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(b"RIFF-test")
            return {"generated": True, "reason": "ok", "audio_path": str(output_path), "text": text}

        cfg = VoiceOutputConfig(engine="chatterbox_tts", output_dir="generated", play_audio=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch.object(voice_output, "PROJECT_ROOT", Path(tmpdir)),
                patch.object(voice_output, "synthesize_text_to_wav", side_effect=fake_synthesize),
                patch.object(voice_output, "play_wav_file", return_value={"played": True, "reason": "ok"}),
            ):
                result = speak_text_chunks_streaming(["First.", "Second.", "Third."], cfg)

        self.assertTrue(result["spoken"])
        self.assertFalse(result["complete"])
        self.assertEqual(result["reason"], "voice_incomplete")
        self.assertEqual(result["played_chunk_count"], 1)

    def test_bounded_chunk_pipeline_preserves_only_safe_approved_route_proof(self) -> None:
        benchmark_events: list[tuple[str, dict]] = []

        def fake_synthesize(text, output_path, _config):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(b"RIFF-test")
            return {
                "generated": True,
                "reason": "ok",
                "audio_path": str(output_path),
                "text": text,
                "route_id": "sealed_cpu",
                "approved_voice_path_used": "sealed_cpu",
                "device": "cpu",
                "approved_voice_attempts": [
                    {
                        "route_id": "blackwell_gpu",
                        "role": "preferred",
                        "status": "synthesis_failed",
                        "reason": "gpu_synthesis_or_contract_failed",
                        "self_check": {"traceback": "PRIVATE TRACEBACK MUST NOT PERSIST"},
                    },
                    {
                        "route_id": "sealed_cpu",
                        "role": "automatic_fallback_only",
                        "status": "used",
                        "reason": "ok",
                    },
                ],
                "approved_voice_routing": {
                    "preferred_failure_reason": "gpu_synthesis_or_contract_failed",
                    "qwen_residency": {"raw_response": "PRIVATE ROUTE PAYLOAD"},
                },
                "resources": {
                    "peak_process_rss_mib": 1234.5,
                    "peak_system_ram_used_mib": 8192.0,
                    "baseline_gpu_vram_used_mib": 900.0,
                    "peak_gpu_vram_used_mib": 900.0,
                    "peak_sidecar_gpu_delta_mib": 0.0,
                },
                "process_seconds": 4.25,
                "traceback": "PRIVATE TOP LEVEL TRACEBACK",
                "captured_warnings": ["PRIVATE WARNING TEXT"],
            }

        cfg = VoiceOutputConfig(engine="chatterbox_tts", output_dir="generated", play_audio=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch.object(voice_output, "PROJECT_ROOT", Path(tmpdir)),
                patch.object(voice_output, "synthesize_text_to_wav", side_effect=fake_synthesize),
                patch.object(voice_output, "play_wav_file", return_value={"played": True, "reason": "ok"}),
            ):
                result = speak_text_chunks_streaming(
                    ["One safe public sentence."],
                    cfg,
                    event_callback=lambda event, payload: benchmark_events.append((event, payload)),
                )

        chunk = result["chunk_results"][0]
        self.assertEqual(chunk["approved_voice_path_used"], "sealed_cpu")
        self.assertEqual(chunk["device"], "cpu")
        self.assertTrue(chunk["gpu_synthesis_attempted"])
        self.assertTrue(chunk["cpu_synthesis_attempted"])
        self.assertTrue(chunk["automatic_cpu_fallback_used"])
        self.assertEqual(chunk["preferred_failure_reason"], "gpu_synthesis_or_contract_failed")
        self.assertEqual(chunk["peak_process_rss_mib"], 1234.5)
        self.assertEqual(
            chunk["route_attempt_summary"],
            "blackwell_gpu:synthesis_failed:gpu_synthesis_or_contract_failed,sealed_cpu:used:ok",
        )
        self.assertEqual(
            chunk["approved_voice_attempts"],
            [
                {
                    "route_id": "blackwell_gpu",
                    "role": "preferred",
                    "status": "synthesis_failed",
                    "reason": "gpu_synthesis_or_contract_failed",
                },
                {
                    "route_id": "sealed_cpu",
                    "role": "automatic_fallback_only",
                    "status": "used",
                    "reason": "ok",
                },
            ],
        )
        synthesis_event = next(
            payload for event, payload in benchmark_events if event == "chunk_synthesis_end"
        )
        self.assertEqual(synthesis_event["approved_voice_path_used"], "sealed_cpu")
        self.assertNotIn("approved_voice_attempts", synthesis_event)
        serialized = json.dumps({"result": result, "events": benchmark_events}).casefold()
        self.assertNotIn("private traceback", serialized)
        self.assertNotIn("private route payload", serialized)
        self.assertNotIn("private warning", serialized)


if __name__ == "__main__":
    unittest.main()
