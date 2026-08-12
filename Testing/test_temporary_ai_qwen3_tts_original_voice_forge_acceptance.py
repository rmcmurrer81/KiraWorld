from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import qwen3_tts_original_voice_forge_worker as worker
import run_temporary_ai_qwen3_tts_voice_forge_acceptance as launcher
import create_temporary_ai_candidate as creator


CONTRACT_SOURCE = (
    ROOT
    / "TemporaryAI"
    / "config"
    / "temporary_ai_qwen3_tts_original_voice_forge_acceptance_v1.json"
)
ENVIRONMENT_SOURCE = (
    ROOT / "Voice" / "sidecars" / "qwen3_tts_voice_forge" / "environment_spec_v1.json"
)
WORKER_SOURCE = ROOT / "tools" / "qwen3_tts_original_voice_forge_worker.py"
RUNNER_SOURCE = ROOT / "tools" / "run_temporary_ai_qwen3_tts_voice_forge_acceptance.py"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sine_wave(sample_rate: int = 16000, seconds: float = 0.2) -> list[float]:
    return [0.2 * math.sin(2 * math.pi * 220 * index / sample_rate) for index in range(int(sample_rate * seconds))]


class FakeRuntime:
    def __init__(self, *, fail_at: str | None = None, allocate: bool = True, return_vram: bool = True) -> None:
        self.fail_at = fail_at
        self.allocate = allocate
        self.return_vram = return_vram
        self.active: str | None = None
        self.events: list[str] = []
        self.allocated = 10
        self.reserved = 20
        self.rss = 1000

    def environment_evidence(self) -> dict:
        return {
            "device": "cuda:0",
            "device_name": "Fake RTX",
            "compute_capability": [12, 0],
            "attention_implementation": "sdpa",
            "ordinary_eager_cuda": True,
            "torch_compile_invoked": False,
        }

    def rss_bytes(self) -> int:
        return self.rss

    def cuda_allocated_bytes(self) -> int:
        return self.allocated

    def cuda_reserved_bytes(self) -> int:
        return self.reserved

    def load(self, role: str, model_path: Path) -> None:
        if self.active is not None:
            raise AssertionError("two models resident")
        if self.fail_at == f"load_{role}":
            raise RuntimeError("injected load failure")
        self.active = role
        self.events.append(f"load:{role}")
        if self.allocate:
            self.allocated = 400_000_000
            self.reserved = 500_000_000
        self.rss = 5000
        time.sleep(0.025)

    def generate_voice_design(self, *, text: str, language: str, instruct: str):
        self.events.append("generate_voice_design")
        if self.fail_at == "voice_design":
            raise RuntimeError("injected design failure")
        time.sleep(0.025)
        return sine_wave(), 16000

    def create_voice_clone_prompt(self, *, ref_audio, ref_text: str):
        self.events.append("create_voice_clone_prompt")
        if self.fail_at == "prompt":
            raise RuntimeError("injected prompt failure")
        return {"fake": "prompt", "ref_text": ref_text}

    def generate_voice_clone(self, *, text: str, language: str, prompt):
        self.events.append("generate_voice_clone")
        if self.fail_at == "clone":
            raise RuntimeError("injected clone failure")
        time.sleep(0.025)
        return sine_wave(seconds=0.25), 16000

    def serialize_prompt(self, prompt) -> bytes:
        return json.dumps(prompt, sort_keys=True).encode("utf-8")

    def unload(self) -> None:
        if self.active is not None:
            self.events.append(f"unload:{self.active}")
        self.active = None
        if self.return_vram:
            self.allocated = 10
            self.reserved = 20
        self.rss = 1200
        time.sleep(0.025)


class ForgeFixture:
    def __init__(self, test: unittest.TestCase) -> None:
        temporary = tempfile.TemporaryDirectory()
        test.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.contract_path = self.root / "TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v1.json"
        self.environment_path = self.root / "Voice/sidecars/qwen3_tts_voice_forge/environment_spec_v1.json"
        contract = json.loads(CONTRACT_SOURCE.read_text(encoding="utf-8"))
        environment = json.loads(ENVIRONMENT_SOURCE.read_text(encoding="utf-8"))
        environment["status"] = "ACCEPTED_READY_FOR_BOUNDED_OFFLINE_RUN"
        environment["torch_installation"] = {
            "status": "PINNED_OFFICIAL_BLACKWELL_WINDOWS_WHEELS_ACCEPTED",
            "torch": "fake-test-pin",
            "torchaudio": "fake-test-pin",
        }
        write_json(self.contract_path, contract)
        write_json(self.environment_path, environment)
        self.design_dir = self.root / contract["paths"]["voice_design_model_directory"]
        self.base_dir = self.root / contract["paths"]["base_model_directory"]
        self.design_manifest = self._model(
            self.design_dir, "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", b"design"
        )
        self.base_manifest = self._model(
            self.base_dir, "Qwen/Qwen3-TTS-12Hz-0.6B-Base", b"base"
        )
        traits = "An adult expert voice with a warm midrange, calm authority, clear diction, and moderate pace."
        reference = "This exact reference sentence establishes an original synthetic expert voice."
        test_text = "This exact test sentence checks the reusable offline voice profile."
        self.job = {
            "schema": worker.JOB_SCHEMA,
            "candidate_id": "test_expert",
            "opaque_voice_id": "voice_test_expert_01",
            "voice_origin": worker.VOICE_ORIGIN,
            "identity_basis": worker.IDENTITY_BASIS,
            "named_real_person_imitation_requested": False,
            "named_real_person_names": [],
            "design_traits_text": traits,
            "design_traits_text_sha256": worker.sha256_text(traits),
            "reference_text": reference,
            "reference_text_sha256": worker.sha256_text(reference),
            "test_text": test_text,
            "test_text_sha256": worker.sha256_text(test_text),
            "language": "English",
            "voice_design_model_directory": contract["paths"]["voice_design_model_directory"],
            "voice_design_model_manifest": self.design_manifest.relative_to(self.root).as_posix(),
            "voice_design_model_manifest_sha256": worker.sha256_file(self.design_manifest),
            "base_model_directory": contract["paths"]["base_model_directory"],
            "base_model_manifest": self.base_manifest.relative_to(self.root).as_posix(),
            "base_model_manifest_sha256": worker.sha256_file(self.base_manifest),
            "watermark_evidence": {"requested_status": worker.INITIAL_WATERMARK_STATUS},
        }
        self.job_path = self.root / "TemporaryAI/queues/test_expert/job.json"
        write_json(self.job_path, self.job)

    def _model(self, directory: Path, repository: str, payload: bytes) -> Path:
        directory.mkdir(parents=True)
        model_file = directory / "config.json"
        model_file.write_bytes(payload)
        manifest = {
            "schema": "qwen3_tts_local_model_file_manifest_v1",
            "repository": repository,
            "revision": "fake-exact-revision-for-static-tests",
            "complete_file_inventory": True,
            "files": [
                {
                    "path": "config.json",
                    "bytes": len(payload),
                    "sha256": worker.sha256_file(model_file),
                }
            ],
        }
        path = directory / "MODEL_FILE_MANIFEST.json"
        write_json(path, manifest)
        return path

    def rewrite_job(self) -> None:
        write_json(self.job_path, self.job)

    def execute(self, runtime: FakeRuntime, attempt: str = "attempt_01") -> dict:
        output = self.root / "Voice/voice_forge/private_review/test_expert" / attempt
        return worker.execute_job(
            project_root=self.root,
            contract_path=self.contract_path,
            contract_sha256=worker.sha256_file(self.contract_path),
            environment_spec_path=self.environment_path,
            environment_spec_sha256=worker.sha256_file(self.environment_path),
            job_path=self.job_path,
            job_sha256=worker.sha256_file(self.job_path),
            output_dir=output,
            runtime_factory=lambda: runtime,
            require_ready_environment=True,
            verify_installed_versions=False,
        )


class TemporaryAiQwen3TtsOriginalVoiceForgeAcceptanceTests(unittest.TestCase):
    def fixture(self) -> ForgeFixture:
        return ForgeFixture(self)

    def test_contract_is_inert_offline_and_fail_closed(self) -> None:
        contract = json.loads(CONTRACT_SOURCE.read_text(encoding="utf-8"))
        self.assertTrue(contract["execution"]["default_is_inert"])
        self.assertFalse(contract["execution"]["network_allowed"])
        self.assertFalse(contract["execution"]["playback_allowed"])
        self.assertEqual(contract["execution"]["attention_implementation"], "sdpa")
        self.assertEqual(contract["failure_behavior"]["status"], worker.FAILURE_STATUS)
        self.assertFalse(contract["failure_behavior"]["sapi_fallback_allowed"])

    def test_creator_queue_contains_only_inert_hash_bound_worker_metadata(self) -> None:
        lane = creator.build_original_voice_fast_lane("test_expert")
        metadata = lane["acceptance_worker_metadata"]
        self.assertEqual(
            metadata["queue_kind"],
            "TEMPORARYAI_ORIGINAL_VOICE_FORGE_PRIVATE_ACCEPTANCE_V1",
        )
        self.assertEqual(metadata["execution_status"], "QUEUED_INERT_NOT_RUN")
        self.assertTrue(metadata["explicit_hash_bound_execution_required"])
        self.assertEqual(metadata["fallback_on_failure"], "TEXT_PLUS_SILENCE_ONLY")
        self.assertEqual(
            metadata["acceptance_contract"],
            "TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v1.json",
        )

    def test_environment_spec_has_exact_pins_and_pending_torch_truth(self) -> None:
        spec = json.loads(ENVIRONMENT_SOURCE.read_text(encoding="utf-8"))
        self.assertEqual(
            spec["pinned_core_packages"],
            {"qwen-tts": "0.1.1", "transformers": "4.57.3", "accelerate": "1.12.0"},
        )
        self.assertIn("PENDING", spec["torch_installation"]["status"])
        self.assertIsNone(spec["torch_installation"]["torch"])
        self.assertFalse(spec["runtime"]["torch_compile"])

    def test_real_adapter_source_uses_exact_official_api_and_sdpa(self) -> None:
        source = WORKER_SOURCE.read_text(encoding="utf-8")
        for token in (
            "Qwen3TTSModel.from_pretrained",
            ".generate_voice_design(",
            ".create_voice_clone_prompt(",
            ".generate_voice_clone(",
            'attn_implementation="sdpa"',
            "local_files_only=True",
        ):
            self.assertIn(token, source)
        self.assertNotIn("torch.compile(", source)
        self.assertNotIn('attn_implementation="flash_attention_2"', source)

    def test_import_is_inert_and_has_no_top_level_torch_or_qwen_import(self) -> None:
        first_import = WORKER_SOURCE.read_text(encoding="utf-8").split("class OfficialQwenRuntime", 1)[0]
        self.assertNotIn("import torch", first_import)
        self.assertNotIn("import qwen_tts", first_import)

    def test_launcher_without_execute_is_inert(self) -> None:
        args = launcher.parse_args([])
        with self.assertRaisesRegex(launcher.LauncherError, "inert"):
            launcher.run(args)

    def test_pending_environment_blocks_real_launcher_preflight(self) -> None:
        spec = json.loads(ENVIRONMENT_SOURCE.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(worker.ForgeError, "not accepted ready"):
            worker.validate_environment_spec(spec, require_ready=True)

    def test_restricted_environment_does_not_copy_arbitrary_parent_values(self) -> None:
        old = os.environ.get("FORGE_TEST_SECRET")
        os.environ["FORGE_TEST_SECRET"] = "must-not-cross"
        self.addCleanup(lambda: os.environ.__setitem__("FORGE_TEST_SECRET", old) if old is not None else os.environ.pop("FORGE_TEST_SECRET", None))
        with tempfile.TemporaryDirectory() as temp_cache:
            env = launcher.restricted_child_environment(
                isolated_python=Path(r"C:\isolated\.venv\Scripts\python.exe"),
                cache_root=Path(temp_cache) / "cache",
            )
        self.assertNotIn("FORGE_TEST_SECRET", env)
        self.assertEqual(env["HF_HUB_OFFLINE"], "1")
        self.assertEqual(env["TRANSFORMERS_OFFLINE"], "1")

    def test_named_real_person_imitation_flag_is_rejected(self) -> None:
        fixture = self.fixture()
        fixture.job["named_real_person_imitation_requested"] = True
        with self.assertRaisesRegex(worker.ForgeError, "imitation"):
            worker.validate_job_identity(fixture.job)

    def test_named_real_person_imitation_language_is_rejected(self) -> None:
        fixture = self.fixture()
        text = "Create an adult voice that sounds exactly like a named celebrity voice for this expert."
        fixture.job["design_traits_text"] = text
        fixture.job["design_traits_text_sha256"] = worker.sha256_text(text)
        with self.assertRaisesRegex(worker.ForgeError, "imitation"):
            worker.validate_job_identity(fixture.job)

    def test_all_three_exact_text_hashes_are_enforced_before_runtime(self) -> None:
        fixture = self.fixture()
        for field in ("design_traits", "reference", "test"):
            broken = dict(fixture.job)
            broken[f"{field}_text_sha256"] = "0" * 64
            with self.subTest(field=field), self.assertRaisesRegex(worker.ForgeError, "hash mismatch"):
                worker.validate_job_identity(broken)

    def test_stronger_watermark_claim_requires_explicit_detector_evidence(self) -> None:
        evidence = {"requested_status": worker.STRONG_WATERMARK_STATUS}
        with self.assertRaisesRegex(worker.ForgeError, "evidence gate"):
            worker.resolve_watermark_status(evidence)

    def test_stronger_watermark_claim_accepts_complete_explicit_evidence_only(self) -> None:
        evidence = {
            "requested_status": worker.STRONG_WATERMARK_STATUS,
            "exact_revision_source_scan_passed": True,
            "dependency_scan_passed": True,
            "wav_inventory_passed": True,
            "detector_positive_controls_passed": True,
            "repeated_generated_samples_no_known_mark_detected": True,
            "owner_hearing_acceptance_passed": True,
            "detectors": [{"name": "bounded-test-detector", "version": "1", "evidence_sha256": "a" * 64}],
        }
        self.assertEqual(worker.resolve_watermark_status(evidence), worker.STRONG_WATERMARK_STATUS)

    def test_model_manifest_verifies_every_bound_file(self) -> None:
        fixture = self.fixture()
        manifest = worker.verify_model_file_manifest(
            project_root=fixture.root,
            model_dir=fixture.design_dir,
            manifest_path=fixture.design_manifest,
            expected_manifest_hash=worker.sha256_file(fixture.design_manifest),
            expected_repository="Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        )
        self.assertTrue(manifest["complete_file_inventory"])

    def test_model_manifest_file_drift_is_rejected(self) -> None:
        fixture = self.fixture()
        (fixture.design_dir / "config.json").write_bytes(b"drift")
        with self.assertRaisesRegex(worker.ForgeError, "size mismatch|hash mismatch"):
            worker.verify_model_file_manifest(
                project_root=fixture.root,
                model_dir=fixture.design_dir,
                manifest_path=fixture.design_manifest,
                expected_manifest_hash=worker.sha256_file(fixture.design_manifest),
                expected_repository="Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            )

    def test_mocked_happy_path_runs_exact_serial_sequence_and_writes_evidence(self) -> None:
        fixture = self.fixture()
        runtime = FakeRuntime()
        result = fixture.execute(runtime)
        self.assertEqual(
            runtime.events,
            [
                "load:voice_design",
                "generate_voice_design",
                "unload:voice_design",
                "load:runtime_clone",
                "create_voice_clone_prompt",
                "generate_voice_clone",
                "unload:runtime_clone",
            ],
        )
        self.assertEqual(result["status"], "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING")
        manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
        profile = json.loads(Path(result["profile_path"]).read_text(encoding="utf-8"))
        self.assertGreater(
            manifest["telemetry"]["peak_cuda_allocated_bytes"],
            manifest["telemetry"]["baseline_cuda_allocated_bytes"],
        )
        self.assertEqual(profile["owner_hearing_acceptance"], "PENDING")
        self.assertFalse(profile["assignment_allowed"])
        self.assertEqual(manifest["watermark"]["status"], worker.INITIAL_WATERMARK_STATUS)

    def test_generated_wavs_are_pcm16_readable_and_non_silent(self) -> None:
        fixture = self.fixture()
        result = fixture.execute(FakeRuntime())
        output = Path(result["output_dir"])
        for name in ("original_design_reference.wav", "runtime_clone_test.wav"):
            with self.subTest(name=name):
                evidence = worker.validate_readable_non_silent_wav(output / name)
                self.assertEqual(evidence["sample_width_bytes"], 2)
                self.assertTrue(evidence["non_silent"])

    def test_profile_and_manifest_hashes_match_written_files(self) -> None:
        fixture = self.fixture()
        result = fixture.execute(FakeRuntime())
        self.assertEqual(result["profile_sha256"], worker.sha256_file(Path(result["profile_path"])))
        self.assertEqual(result["manifest_sha256"], worker.sha256_file(Path(result["manifest_path"])))

    def test_append_only_existing_attempt_is_refused_before_runtime_creation(self) -> None:
        fixture = self.fixture()
        fixture.execute(FakeRuntime())
        second = FakeRuntime()
        with self.assertRaisesRegex(worker.ForgeError, "append-only output already exists"):
            fixture.execute(second)
        self.assertEqual(second.events, [])

    def test_clone_failure_preserves_traceback_and_text_plus_silence(self) -> None:
        fixture = self.fixture()
        with self.assertRaises(worker.ForgeError):
            fixture.execute(FakeRuntime(fail_at="clone"))
        failure_path = fixture.root / "Voice/voice_forge/private_review/test_expert/attempt_01/failure.json"
        failure = json.loads(failure_path.read_text(encoding="utf-8"))
        self.assertEqual(failure["status"], worker.FAILURE_STATUS)
        self.assertEqual(failure["fallback"]["voice_audio_result"], "SILENCE_NO_AUDIO")
        self.assertFalse(failure["fallback"]["generic_voice_used"])
        self.assertFalse(failure["fallback"]["sapi_used"])
        self.assertIn("injected clone failure", failure["traceback"])

    def test_no_gpu_allocation_fails_engineering_acceptance(self) -> None:
        fixture = self.fixture()
        with self.assertRaisesRegex(worker.ForgeError, "no actual CUDA allocation"):
            fixture.execute(FakeRuntime(allocate=False))
        failure = json.loads(
            (fixture.root / "Voice/voice_forge/private_review/test_expert/attempt_01/failure.json").read_text(encoding="utf-8")
        )
        self.assertEqual(failure["status"], worker.FAILURE_STATUS)

    def test_vram_nonreturn_blocks_base_or_final_acceptance(self) -> None:
        fixture = self.fixture()
        with self.assertRaisesRegex(worker.ForgeError, "VRAM"):
            fixture.execute(FakeRuntime(return_vram=False))

    def test_job_hash_mismatch_fails_before_output_or_runtime(self) -> None:
        fixture = self.fixture()
        runtime = FakeRuntime()
        output = fixture.root / "Voice/voice_forge/private_review/test_expert/attempt_01"
        with self.assertRaisesRegex(worker.ForgeError, "job hash mismatch"):
            worker.execute_job(
                project_root=fixture.root,
                contract_path=fixture.contract_path,
                contract_sha256=worker.sha256_file(fixture.contract_path),
                environment_spec_path=fixture.environment_path,
                environment_spec_sha256=worker.sha256_file(fixture.environment_path),
                job_path=fixture.job_path,
                job_sha256="0" * 64,
                output_dir=output,
                runtime_factory=lambda: runtime,
                require_ready_environment=True,
                verify_installed_versions=False,
            )
        self.assertFalse(output.exists())
        self.assertEqual(runtime.events, [])

    def test_contract_records_no_chatterbox_environment_reuse(self) -> None:
        contract = json.loads(CONTRACT_SOURCE.read_text(encoding="utf-8"))
        forbidden = "\n".join(contract["forbidden_environment_roots"])
        self.assertIn("chatterbox_blackwell_gpu", forbidden)
        self.assertEqual(
            contract["paths"]["isolated_sidecar_root"],
            "Voice/sidecars/qwen3_tts_voice_forge",
        )

    def test_runner_source_never_installs_or_downloads_dependencies(self) -> None:
        source = RUNNER_SOURCE.read_text(encoding="utf-8").lower()
        self.assertNotIn("pip install", source)
        self.assertNotIn("huggingface-cli download", source)
        self.assertNotIn("modelscope download", source)
        self.assertIn('"hf_hub_offline": "1"', source)


if __name__ == "__main__":
    unittest.main()
