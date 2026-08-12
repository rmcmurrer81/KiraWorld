from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import math
import os
import struct
import tempfile
import time
import unittest
import wave
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in os.sys.path:
    os.sys.path.insert(0, str(TOOLS))

import qwen3_tts_original_voice_forge_worker_v2 as worker
import run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2 as launcher


CONTRACT_SOURCE = ROOT / worker.CONTRACT_REL
ENVIRONMENT_SOURCE = ROOT / worker.ENVIRONMENT_REL
WORKER_SOURCE = ROOT / worker.WORKER_REL if hasattr(worker, "WORKER_REL") else ROOT / "tools/qwen3_tts_original_voice_forge_worker_v2.py"
RUNNER_SOURCE = ROOT / "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py"
V1_CHECKPOINT = ROOT / "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_ACCEPTANCE_HARNESS_CHECKPOINT_20260809.md"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_test_wav(path: Path, frequency: float = 223.0, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = [
        round(5000 * math.sin(2 * math.pi * frequency * index / sample_rate))
        for index in range(sample_rate // 2)
    ]
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        writer.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def record_hash(data: bytes) -> str:
    return base64.urlsafe_b64encode(bytes.fromhex(worker.sha256_bytes(data))).decode("ascii").rstrip("=")


def write_test_wheel(root: Path, package: str, version: str) -> Path:
    normalized = package.replace("-", "_")
    dist_info = f"{normalized}-{version}.dist-info"
    metadata = f"Metadata-Version: 2.1\nName: {package}\nVersion: {version}\n".encode()
    wheel = b"Wheel-Version: 1.0\nGenerator: bounded-test\nRoot-Is-Purelib: false\nTag: py3-none-win_amd64\n"
    payloads = {f"{dist_info}/METADATA": metadata, f"{dist_info}/WHEEL": wheel}
    record_name = f"{dist_info}/RECORD"
    lines = [f"{name},sha256={record_hash(payload)},{len(payload)}" for name, payload in payloads.items()]
    lines.append(f"{record_name},,")
    payloads[record_name] = ("\n".join(lines) + "\n").encode()
    path = root / f"{normalized}-{version}-py3-none-win_amd64.whl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as archive:
        for name, payload in payloads.items():
            archive.writestr(name, payload)
    return path


def exact_eval(
    text: str, vector: list[float], *, evaluator: dict | None = None,
    wav_sha256: str = "e" * 64, tone: float = 0.0, speech: float = 0.99,
) -> dict:
    evaluator = evaluator or {
        "asr_engine": "test-real-asr", "asr_version": "1.0", "asr_model_manifest_sha256": "a" * 64,
        "speech_classifier_engine": "test-real-speech", "speech_classifier_version": "1.0",
        "speech_classifier_model_manifest_sha256": "c" * 64, "speech_classifier_adapter_sha256": "d" * 64,
        "speaker_embedding_engine": "test-real-embedding", "speaker_embedding_version": "1.0",
        "speaker_model_manifest_sha256": "b" * 64,
    }
    return {
        "asr_mode": "REAL_LOCAL_ASR",
        "asr_engine": evaluator["asr_engine"],
        "asr_version": evaluator["asr_version"],
        "asr_model_manifest_sha256": evaluator["asr_model_manifest_sha256"],
        "asr_source_wav_sha256": wav_sha256,
        "transcript": text,
        "speech_mode": "REAL_LOCAL_SPEECH_CLASSIFIER",
        "speech_classifier_engine": evaluator["speech_classifier_engine"],
        "speech_classifier_version": evaluator["speech_classifier_version"],
        "speech_classifier_model_manifest_sha256": evaluator["speech_classifier_model_manifest_sha256"],
        "speech_classifier_adapter_sha256": evaluator["speech_classifier_adapter_sha256"],
        "speech_classifier_source_wav_sha256": wav_sha256,
        "speech_probability": speech,
        "pure_tone_probability": tone,
        "pure_tone_detector": "MULTIWINDOW_SPECTRAL_CONCENTRATION_V2",
        "embedding_mode": "REAL_LOCAL_SPEAKER_EMBEDDING",
        "embedding_engine": evaluator["speaker_embedding_engine"],
        "embedding_version": evaluator["speaker_embedding_version"],
        "embedding_model_manifest_sha256": evaluator["speaker_model_manifest_sha256"],
        "source_wav_sha256": wav_sha256,
        "source_sample_rate_hz": 16000,
        "speaker_input_sample_rate_hz": 16000,
        "speaker_resampling_method": "TORCHAUDIO_FUNCTIONAL_RESAMPLE_FLOAT32_V1",
        "resampled_for_embedding": False,
        "embedding_input_wav_path": "REQUIRED_TEST_ARTIFACT",
        "embedding_input_wav_sha256": "f" * 64,
        "embedding_input_wav_bytes": 1,
        "embedding_computed_from_reloaded_exact_pcm16_artifact": True,
        "speaker_embedding": vector,
    }


class FakeRuntime:
    def __init__(self, environment: dict) -> None:
        self.environment = environment
        self.active = None
        self.allocated = 10
        self.reserved = 20
        self.peak_allocated = self.allocated
        self.peak_reserved = self.reserved
        self.events: list[str] = []

    def environment_evidence(self, spec: dict, project_root: Path) -> dict:
        return self.environment

    def post_execution_provenance(self, spec: dict, project_root: Path) -> dict:
        return {
            "site_packages_manifest_path": self.environment["site_packages_inventory"]["manifest_path"],
            "site_packages_manifest_sha256": self.environment["site_packages_inventory"]["manifest_sha256"],
            "complete_site_packages_inventory_reverified_after_execution": True,
            "every_loaded_site_packages_module_bound_to_verified_record": True,
            "required_engine_distributions_observed": sorted((
                "torch", "torchaudio", "qwen-tts", "transformers", "accelerate",
                "faster-whisper", "speechbrain",
            )),
            "loaded_module_count": 7,
            "loaded_modules": list(self.environment["imported_module_bindings"].values()),
        }

    def rss_bytes(self) -> int:
        return 4096 if self.active else 1024

    def peak_rss_bytes(self) -> int:
        return 8192

    def cuda_allocated_bytes(self) -> int:
        return self.allocated

    def cuda_reserved_bytes(self) -> int:
        return self.reserved

    def load(self, role: str, snapshot: Path) -> None:
        if self.active is not None:
            raise AssertionError("two heavy models resident")
        self.active = role
        self.events.append(f"load:{role}")
        self.allocated = 1_000_000_000
        self.reserved = 1_200_000_000
        self.peak_allocated = max(self.peak_allocated, self.allocated)
        self.peak_reserved = max(self.peak_reserved, self.reserved)

    def generate_design(self, *, text: str, language: str, traits: str):
        self.events.append("generate_voice_design")
        self.peak_allocated = max(self.peak_allocated, 1_450_000_000)
        self.peak_reserved = max(self.peak_reserved, 1_600_000_000)
        return [0.13 * math.sin(2 * math.pi * 241 * i / 16000) + 0.03 * math.sin(2 * math.pi * 397 * i / 16000) for i in range(8000)], 16000

    def create_prompt(self, *, reference, reference_text: str):
        self.events.append("create_voice_clone_prompt")
        return {"reference_text": reference_text}

    def generate_clone(self, *, text: str, language: str, prompt):
        self.events.append("generate_voice_clone")
        self.peak_allocated = max(self.peak_allocated, 1_700_000_000)
        self.peak_reserved = max(self.peak_reserved, 1_900_000_000)
        return [0.11 * math.sin(2 * math.pi * 263 * i / 16000) + 0.04 * math.sin(2 * math.pi * 421 * i / 16000) for i in range(8000)], 16000

    def serialize_prompt(self, prompt) -> bytes:
        return json.dumps(prompt, sort_keys=True).encode("utf-8")

    def unload(self) -> None:
        if self.active:
            self.events.append(f"unload:{self.active}")
        self.active = None
        self.allocated = 10
        self.reserved = 20

    def reset_peak_cuda_memory_stats(self) -> None:
        self.peak_allocated = self.allocated
        self.peak_reserved = self.reserved

    def peak_cuda_allocated_bytes(self) -> int:
        return self.peak_allocated

    def peak_cuda_reserved_bytes(self) -> int:
        return self.peak_reserved


class FakeEvaluator:
    def __init__(self, spec: dict, project_root: Path) -> None:
        self.evaluator = spec["speech_evaluators"]
        self.project_root = project_root
        self.calls = 0

    def speaker_embedding(self, wav_path: Path) -> dict:
        voice_hint = wav_path.parent.name if wav_path.stem == "source" else wav_path.stem
        if voice_hint == "resident":
            vector = [0.0, 1.0]
        elif voice_hint == "generic":
            vector = [-1.0, 0.0]
        else:
            vector = [1.0, 0.01]
        normalized = worker.speaker_embedding_artifact_path(
            source_wav_path=wav_path,
            project_root=self.project_root,
            target_sample_rate_hz=16000,
        )
        normalized.parent.mkdir(parents=True, exist_ok=True)
        normalized.write_bytes(wav_path.read_bytes())
        evidence = exact_eval("", vector, evaluator=self.evaluator, wav_sha256=worker.sha256_file(wav_path))
        evidence.update({
            "embedding_input_wav_path": worker.relative(normalized, self.project_root),
            "embedding_input_wav_sha256": worker.sha256_file(normalized),
            "embedding_input_wav_bytes": normalized.stat().st_size,
            "embedding_computed_from_reloaded_exact_pcm16_artifact": True,
        })
        return {key: evidence[key] for key in (
            "embedding_mode", "embedding_engine", "embedding_version",
            "embedding_model_manifest_sha256", "source_wav_sha256",
            "source_sample_rate_hz", "speaker_input_sample_rate_hz",
            "speaker_resampling_method", "resampled_for_embedding",
            "embedding_input_wav_path", "embedding_input_wav_sha256",
            "embedding_input_wav_bytes",
            "embedding_computed_from_reloaded_exact_pcm16_artifact",
            "speaker_embedding",
        )}

    def evaluate(self, wav_path: Path, *, expected_text: str, language: str) -> dict:
        self.calls += 1
        evidence = exact_eval(
            expected_text,
            [1.0, 0.01] if self.calls == 1 else [0.99, 0.02],
            evaluator=self.evaluator,
            wav_sha256=worker.sha256_file(wav_path),
        )
        embedding = self.speaker_embedding(wav_path)
        evidence.update(embedding)
        return evidence

    def import_provenance_evidence(self) -> dict:
        bindings = {}
        for package in ("faster-whisper", "speechbrain", "torchaudio", "torch"):
            path = self.project_root / worker.ISOLATED_VENV_REL / "Lib/site-packages" / f"{package.replace('-', '_')}_bounded_test.py"
            bindings[package] = {
                "package": package, "module_name": package.replace("-", "_"),
                "origin_path": worker.relative(path, self.project_root),
                "origin_sha256": worker.sha256_file(path), "origin_bytes": path.stat().st_size,
                "package_paths": [], "record_membership_verified_after_import": True,
            }
        return bindings


class FakeIdentityAnalyzer:
    def __init__(self, spec: dict, project_root: Path) -> None:
        self.identity = spec["identity_analyzer"]

    def analyze(self, *, design_text: str, design_sha256: str, attempt_dir: Path) -> dict:
        return {
            "schema": "qwen3_tts_live_identity_analyzer_result_v2",
            "mode": "REAL_LOCAL_NER_AND_IMITATION_CLASSIFIER",
            "engine": self.identity["engine"],
            "version": self.identity["version"],
            "input_sha256": design_sha256,
            "adapter_sha256": self.identity["adapter_sha256"],
            "model_manifest_sha256": self.identity["model_manifest_sha256"],
            "detected_named_person_entities": [],
            "named_person_imitation_requested": False,
            "named_person_probability": 0.0,
            "imitation_request_probability": 0.0,
            "input_artifact_sha256": "1" * 64,
            "output_artifact_sha256": "2" * 64,
            "stdout_sha256": "3" * 64,
            "stderr_sha256": "4" * 64,
            "command_sha256": "5" * 64,
            "process_returncode": 0,
        }


class ExecutionFixture:
    def __init__(self, test: unittest.TestCase) -> None:
        temp = tempfile.TemporaryDirectory()
        test.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.bundle_id = "bundle_test_001"
        self.candidate_id = "expert_test_001"
        self.opaque_voice_id = "voice_test_001"
        self.job = {
            "schema": "qwen3_tts_original_voice_forge_job_v2",
            "voice_origin": worker.VOICE_ORIGIN,
            "identity_basis": worker.IDENTITY_BASIS,
            "design_traits_text": "An original warm adult expert voice with clear diction and a measured pace.",
            "reference_text": "This exact sentence establishes the original expert voice.",
            "test_text": "This exact sentence verifies the reusable private clone.",
            "language": "English",
        }
        for prefix in ("design_traits", "reference", "test"):
            self.job[f"{prefix}_text_sha256"] = worker.sha256_text(self.job[f"{prefix}_text"])
        self.contract = json.loads(CONTRACT_SOURCE.read_text(encoding="utf-8"))
        self.environment = self.accepted_environment()
        write_json(self.root / worker.CONTRACT_REL, self.contract)
        write_json(self.root / worker.ENVIRONMENT_REL, self.environment)
        write_json(self.root / worker.REGISTRY_REL, {"schema": "temporaryai_qwen3_tts_voice_forge_bundle_registry_v2", "append_only_entries": []})
        write_json(self.root / worker.HARNESS_MANIFEST_REL, {"schema": "qwen3_tts_voice_forge_harness_manifest_v2", "status": "TEST_INTERNAL_ONLY"})
        (self.root / worker.WORKER_REL).parent.mkdir(parents=True, exist_ok=True)
        (self.root / worker.WORKER_REL).write_bytes(WORKER_SOURCE.read_bytes())
        (self.root / worker.RUNNER_REL).write_bytes(RUNNER_SOURCE.read_bytes())
        self.bundle_dir = self.root / "TemporaryAI/voice_forge_acceptance_bundles_v2" / self.bundle_id
        self.bundle_dir.mkdir(parents=True)
        write_json(self.bundle_dir / "BUNDLE_SEAL.json", {"schema": "qwen3_tts_original_voice_forge_bundle_seal_v2", "bundle_id": self.bundle_id, "files": []})
        corpus_root = self.root / worker.EVALUATION_CORPUS_ROOT_REL
        voices = []
        for voice_id, kind, vector, frequency in (
            ("resident", "approved_resident", [0.0, 1.0], 211.0),
            ("generic", "known_generic", [-1.0, 0.0], 307.0),
        ):
            wav = corpus_root / "audio" / f"{voice_id}.wav"
            write_test_wav(wav, frequency)
            evidence = corpus_root / "embeddings" / f"{voice_id}.json"
            write_json(evidence, {
                "schema": "qwen3_tts_voice_forge_corpus_embedding_evidence_v2",
                "voice_id": voice_id,
                "source_wav_sha256": worker.sha256_file(wav),
                "embedding_engine": self.environment["speech_evaluators"]["speaker_embedding_engine"],
                "embedding_engine_version": self.environment["speech_evaluators"]["speaker_embedding_version"],
                "embedding_model_manifest_sha256": self.environment["speech_evaluators"]["speaker_model_manifest_sha256"],
                "source_sample_rate_hz": 16000,
                "speaker_input_sample_rate_hz": 16000,
                "speaker_resampling_method": "TORCHAUDIO_FUNCTIONAL_RESAMPLE_FLOAT32_V1",
                "embedding_computed_from_reloaded_exact_pcm16_artifact": True,
                "embedding": vector,
            })
            voices.append({
                "voice_id": voice_id,
                "kind": kind,
                "source_wav_path": worker.relative(wav, self.root),
                "source_wav_sha256": worker.sha256_file(wav),
                "embedding_evidence_path": worker.relative(evidence, self.root),
                "embedding_evidence_sha256": worker.sha256_file(evidence),
                "verified_embedding": vector,
            })
        self.corpus = {
            "schema": "qwen3_tts_voice_forge_evaluation_corpus_v2",
            "status": "ACCEPTED_REAL_LOCAL_SPEAKER_EMBEDDING_CORPUS",
            "embedding_engine": self.environment["speech_evaluators"]["speaker_embedding_engine"],
            "embedding_engine_version": self.environment["speech_evaluators"]["speaker_embedding_version"],
            "embedding_model_path": self.environment["speech_evaluators"]["speaker_model_path"],
            "embedding_model_manifest_path": self.environment["speech_evaluators"]["speaker_model_manifest_path"],
            "embedding_model_manifest_sha256": self.environment["speech_evaluators"]["speaker_model_manifest_sha256"],
            "speaker_input_sample_rate_hz": 16000,
            "speaker_resampling_method": "TORCHAUDIO_FUNCTIONAL_RESAMPLE_FLOAT32_V1",
            "voices": voices,
            "verified_against_exact_files": True,
        }
        design_manifest = self.model("Qwen3-TTS-12Hz-1.7B-VoiceDesign", "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", b"design-model")
        base_manifest = self.model("Qwen3-TTS-12Hz-0.6B-Base", "Qwen/Qwen3-TTS-12Hz-0.6B-Base", b"base-model")
        nonce_hash = worker.sha256_text("test-nonce")
        self.bundle = {
            "bundle_id": self.bundle_id,
            "candidate_id": self.candidate_id,
            "ai_type": "expert_temp_ai",
            "opaque_voice_id": self.opaque_voice_id,
            "single_use_nonce_sha256": nonce_hash,
            "job_sha256": worker.sha256_bytes(worker.canonical_bytes(self.job)),
            "canonical_profile_sha256": "1" * 64,
            "canonical_creation_request_sha256": "2" * 64,
            "owner_authorization_sha256": "3" * 64,
            "watermark_evidence_manifest_sha256": "4" * 64,
            "identity_clearance_manifest_sha256": "5" * 64,
            "evaluation_corpus_sha256": "6" * 64,
            "environment_spec_sha256": worker.sha256_file(self.root / worker.ENVIRONMENT_REL),
            "voice_design_model_directory": "Voice/models/qwen3_tts/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            "voice_design_model_manifest_path": "Voice/models/qwen3_tts/Qwen3-TTS-12Hz-1.7B-VoiceDesign/MODEL_FILE_MANIFEST.json",
            "voice_design_model_manifest_sha256": worker.sha256_file(design_manifest),
            "base_model_directory": "Voice/models/qwen3_tts/Qwen3-TTS-12Hz-0.6B-Base",
            "base_model_manifest_path": "Voice/models/qwen3_tts/Qwen3-TTS-12Hz-0.6B-Base/MODEL_FILE_MANIFEST.json",
            "base_model_manifest_sha256": worker.sha256_file(base_manifest),
        }
        self.bundle["queue_binding_sha256"] = worker.compute_queue_binding(self.bundle)
        self.attempt = self.root / worker.OUTPUT_ROOT_REL / self.bundle_id / "attempt_01"
        self.attempt.mkdir(parents=True)
        ledger = self.root / worker.NONCE_LEDGER_REL / f"{nonce_hash}.json"
        ledger_payload = {
            "schema": "qwen3_tts_voice_forge_single_use_nonce_ledger_v2",
            "status": "CONSUMED_FOR_EXACT_QUEUE_ATTEMPT",
            "bundle_id": self.bundle_id,
            "candidate_id": self.candidate_id,
            "opaque_voice_id": self.opaque_voice_id,
            "ai_type": "expert_temp_ai",
            "single_use_nonce_sha256": nonce_hash,
            "queue_binding_sha256": self.bundle["queue_binding_sha256"],
            "job_sha256": self.bundle["job_sha256"],
            "attempt": worker.relative(self.attempt, self.root),
        }
        ledger_payload.update(worker.queue_binding_payload(self.bundle))
        write_json(ledger, ledger_payload)
        write_json(self.attempt / "parent_reservation.json", {
            "schema": "qwen3_tts_voice_forge_parent_reservation_v2",
            "status": "RESERVED_AND_NONCE_CONSUMED_FOR_EXACT_QUEUE",
            "bundle_id": self.bundle_id,
            **worker.queue_binding_payload(self.bundle),
            "nonce_ledger_path": worker.relative(ledger, self.root),
            "nonce_ledger_sha256": worker.sha256_file(ledger),
            "contract_sha256": worker.sha256_file(self.root / worker.CONTRACT_REL),
            "environment_spec_sha256": worker.sha256_file(self.root / worker.ENVIRONMENT_REL),
            "trusted_registry_sha256": worker.sha256_file(self.root / worker.REGISTRY_REL),
            "bundle_seal_sha256": worker.sha256_file(self.bundle_dir / "BUNDLE_SEAL.json"),
            "verified_worker_sha256": worker.sha256_file(Path(worker.__file__).resolve()),
            "harness_manifest_sha256": worker.sha256_file(self.root / worker.HARNESS_MANIFEST_REL),
        })
        self.trusted = worker.TrustedBundle(
            self.root, self.bundle_dir, self.bundle, self.job, {}, {}, {}, {}, {},
            self.corpus, self.contract, self.environment, {},
        )

    def model(self, name: str, repository: str, content: bytes) -> Path:
        directory = self.root / "Voice/models/qwen3_tts" / name
        directory.mkdir(parents=True)
        model_file = directory / "config.json"
        model_file.write_bytes(content)
        manifest = directory / "MODEL_FILE_MANIFEST.json"
        write_json(manifest, {
            "schema": "qwen3_tts_local_model_file_manifest_v1",
            "repository": repository,
            "revision": "exact-test-revision",
            "complete_file_inventory": True,
            "files": [{"path": "config.json", "bytes": len(content), "sha256": worker.sha256_file(model_file)}],
        })
        return manifest

    def accepted_environment(self) -> dict:
        spec = json.loads(ENVIRONMENT_SOURCE.read_text(encoding="utf-8"))
        spec["status"] = "ACCEPTED_READY_FOR_ONE_BOUNDED_RUN"
        python_path = self.root / worker.ISOLATED_VENV_REL / "Scripts/python.exe"
        python_path.parent.mkdir(parents=True, exist_ok=True)
        python_path.write_bytes(b"exact-isolated-test-python")
        spec["python"] = {
            "version": "3.11.9",
            "executable_path": worker.relative(python_path, self.root),
            "executable_sha256": worker.sha256_file(python_path),
        }
        site_packages = self.root / worker.ISOLATED_VENV_REL / "Lib/site-packages"
        versions = {
            "qwen-tts": "0.1.1", "transformers": "4.57.3", "accelerate": "1.12.0",
            "torch": "2.11.0+cu130", "torchaudio": "2.11.0+cu130",
            "faster-whisper": "1.2.1", "speechbrain": "1.0.3",
        }
        for package, version in versions.items():
            row = spec["distributions"][package]
            row["version"] = version
            normalized = package.replace("-", "_")
            installed = site_packages / f"{normalized}_bounded_test.py"
            installed.parent.mkdir(parents=True, exist_ok=True)
            installed.write_text(f"PACKAGE = {package!r}\n", encoding="utf-8")
            record = site_packages / f"{normalized}-{version}.dist-info/RECORD"
            record.parent.mkdir(parents=True, exist_ok=True)
            installed_rel = worker.relative(installed, site_packages)
            installed_bytes = installed.read_bytes()
            record_rel = worker.relative(record, site_packages)
            record.write_text(
                f"{installed_rel},sha256={record_hash(installed_bytes)},{len(installed_bytes)}\n{record_rel},,\n",
                encoding="utf-8",
            )
            row["record_path"] = worker.relative(record, self.root)
            row["record_sha256"] = worker.sha256_file(record)
        wheel_root = self.root / worker.WHEEL_EVIDENCE_ROOT_REL
        for package in ("torch", "torchaudio"):
            row = spec["distributions"][package]
            wheel = write_test_wheel(wheel_root, package, row["version"])
            row["wheel_filename"] = wheel.name
            row["wheel_sha256"] = worker.sha256_file(wheel)
            row["wheel_evidence_path"] = worker.relative(wheel, self.root)
        spec["cuda"]["torch_cuda_build"] = "13.0"
        evaluator_root = self.root / worker.EVALUATOR_ROOT_REL

        def model(role: str, engine: str, version: str) -> tuple[Path, Path]:
            directory = evaluator_root / role / "model"
            directory.mkdir(parents=True)
            model_file = directory / "model.bin"
            model_file.write_bytes(f"{role}-exact-model".encode())
            manifest = directory / "MODEL_MANIFEST.json"
            write_json(manifest, {
                "schema": "qwen3_tts_local_evaluator_model_manifest_v2",
                "engine": engine,
                "version": version,
                "complete_file_inventory": True,
                "files": [{"path": "model.bin", "bytes": model_file.stat().st_size, "sha256": worker.sha256_file(model_file)}],
            })
            return directory, manifest

        asr_dir, asr_manifest = model("asr", "test-real-asr", "1.0")
        speaker_dir, speaker_manifest = model("speaker", "test-real-embedding", "1.0")
        speech_dir, speech_manifest = model("speech_classifier", "test-real-speech", "1.0")
        speech_adapter = evaluator_root / "speech_classifier/adapter.py"
        speech_adapter.write_text("# exact bounded speech classifier adapter\n", encoding="utf-8")
        spec["speech_evaluators"] = {
            "status": "ACCEPTED_EXACT_LOCAL_ASR_SPEECH_AND_SPEAKER_EMBEDDING",
            "asr_engine": "test-real-asr", "asr_version": "1.0", "asr_model_path": worker.relative(asr_dir, self.root), "asr_model_manifest_path": worker.relative(asr_manifest, self.root), "asr_model_manifest_sha256": worker.sha256_file(asr_manifest),
            "speaker_embedding_engine": "test-real-embedding", "speaker_embedding_version": "1.0", "speaker_model_path": worker.relative(speaker_dir, self.root), "speaker_model_manifest_path": worker.relative(speaker_manifest, self.root), "speaker_model_manifest_sha256": worker.sha256_file(speaker_manifest),
            "speaker_input_sample_rate_hz": 16000, "speaker_resampling_method": "TORCHAUDIO_FUNCTIONAL_RESAMPLE_FLOAT32_V1",
            "speech_classifier_engine": "test-real-speech", "speech_classifier_version": "1.0", "speech_classifier_adapter_path": worker.relative(speech_adapter, self.root), "speech_classifier_adapter_sha256": worker.sha256_file(speech_adapter), "speech_classifier_model_path": worker.relative(speech_dir, self.root), "speech_classifier_model_manifest_path": worker.relative(speech_manifest, self.root), "speech_classifier_model_manifest_sha256": worker.sha256_file(speech_manifest),
        }
        identity_dir, identity_manifest = model("identity", "test-identity", "1")
        identity_adapter = evaluator_root / "identity/adapter.py"
        identity_adapter.write_text("# exact bounded identity analyzer adapter\n", encoding="utf-8")
        spec["identity_analyzer"] = {
            "status": "ACCEPTED_EXACT_LOCAL_NER_AND_IMITATION_ANALYZER",
            "engine": "test-identity", "version": "1", "adapter_path": worker.relative(identity_adapter, self.root), "adapter_sha256": worker.sha256_file(identity_adapter),
            "model_path": worker.relative(identity_dir, self.root), "model_manifest_path": worker.relative(identity_manifest, self.root), "model_manifest_sha256": worker.sha256_file(identity_manifest),
        }
        ownership: dict[str, list[str]] = {}
        distributions = []
        for package, row in spec["distributions"].items():
            record = self.root / row["record_path"]
            distributions.append({
                "name": package, "version": row["version"],
                "record_path": row["record_path"], "record_sha256": row["record_sha256"],
            })
            with record.open("r", encoding="utf-8", newline="") as handle:
                for record_row in csv.reader(handle):
                    ownership.setdefault(record_row[0].replace("\\", "/"), []).append(package)
        inventory_files = []
        for path in sorted(site_packages.rglob("*")):
            if path.is_file():
                rel = worker.relative(path, site_packages)
                owners = sorted(ownership.get(rel, []))
                inventory_files.append({
                    "path": rel, "bytes": path.stat().st_size,
                    "sha256": worker.sha256_file(path),
                    "owner_distributions": owners,
                    "loose_unowned_file": not owners,
                })
        inventory_manifest = self.root / worker.ISOLATED_ROOT_REL / "site_packages_inventory_v2.json"
        write_json(inventory_manifest, {
            "schema": "qwen3_tts_complete_site_packages_inventory_v2",
            "status": "ACCEPTED_COMPLETE_EXACT_TRANSITIVE_AND_LOOSE_FILE_INVENTORY",
            "site_packages_root": worker.relative(site_packages, self.root),
            "complete_file_inventory": True,
            "distributions": sorted(distributions, key=lambda row: row["name"]),
            "files": inventory_files,
        })
        spec["site_packages_inventory"] = {
            "status": "ACCEPTED_COMPLETE_EXACT_TRANSITIVE_AND_LOOSE_FILE_INVENTORY",
            "root": worker.relative(site_packages, self.root),
            "manifest_path": worker.relative(inventory_manifest, self.root),
            "manifest_sha256": worker.sha256_file(inventory_manifest),
            "complete_file_inventory": True,
            "all_distributions_and_loose_files_declared": True,
        }
        return spec

    def environment_evidence(self) -> dict:
        distributions = {}
        site_packages = self.root / worker.ISOLATED_VENV_REL / "Lib/site-packages"
        for name, row in self.environment["distributions"].items():
            record = self.root / row["record_path"]
            installed_rows = []
            with record.open("r", encoding="utf-8", newline="") as handle:
                for record_row in csv.reader(handle):
                    path = site_packages / record_row[0]
                    installed_rows.append({"path": worker.relative(path, self.root), "bytes": path.stat().st_size, "sha256": worker.sha256_file(path)})
            distributions[name] = {
                "version": row["version"], "record_path": row["record_path"],
                "record_sha256": row["record_sha256"], "record_rows_verified": len(installed_rows),
                "installed_files": installed_rows,
            }
        return {
            "python_version": self.environment["python"]["version"],
            "python_executable_path": self.environment["python"]["executable_path"],
            "python_executable_sha256": self.environment["python"]["executable_sha256"],
            "distributions": distributions,
            "site_packages_inventory": {
                "manifest_path": self.environment["site_packages_inventory"]["manifest_path"],
                "manifest_sha256": self.environment["site_packages_inventory"]["manifest_sha256"],
                "complete_file_inventory": True,
                "all_transitive_distributions_declared": True,
                "all_loose_files_declared": True,
                "files": [
                    {
                        "path": worker.relative(site_packages / row["path"], self.root),
                        "bytes": row["bytes"], "sha256": row["sha256"],
                        "owner_distributions": row["owner_distributions"],
                        "loose_unowned_file": row["loose_unowned_file"],
                    }
                    for row in json.loads(
                        (self.root / self.environment["site_packages_inventory"]["manifest_path"]).read_text()
                    )["files"]
                ],
            },
            "imported_module_bindings": {
                package: {
                    "package": package,
                    "module_name": package.replace("-", "_"),
                    "origin_path": next(
                        row["path"] for row in distributions[package]["installed_files"]
                        if row["path"].endswith("_bounded_test.py")
                    ),
                    "origin_sha256": next(
                        row["sha256"] for row in distributions[package]["installed_files"]
                        if row["path"].endswith("_bounded_test.py")
                    ),
                    "origin_bytes": next(
                        row["bytes"] for row in distributions[package]["installed_files"]
                        if row["path"].endswith("_bounded_test.py")
                    ),
                    "package_paths": [],
                    "record_membership_verified_after_import": True,
                }
                for package in (
                    "torch", "torchaudio", "qwen-tts", "transformers", "accelerate",
                    "faster-whisper", "speechbrain",
                )
            },
            "wheel_archives": {
                name: {
                    "path": row["wheel_evidence_path"], "filename": row["wheel_filename"],
                    "sha256": row["wheel_sha256"], "archive_members_verified": 2,
                    "metadata_name": name, "metadata_version": row["version"],
                }
                for name, row in self.environment["distributions"].items() if name in {"torch", "torchaudio"}
            },
            "torch_wheel_sha256": self.environment["distributions"]["torch"]["wheel_sha256"],
            "torchaudio_wheel_sha256": self.environment["distributions"]["torchaudio"]["wheel_sha256"],
            "torch_cuda_build": "13.0", "device_name": "NVIDIA GeForce RTX 5060 Ti",
            "compute_capability": [12, 0], "arch_list": ["sm_120"], "sm_120_present": True,
            "ordinary_eager_cuda_matrix_result": [[19.0, 22.0], [43.0, 50.0]],
            "cuda_synchronization_passed": True, "unsupported_architecture_warning": False,
            "attention_implementation": "sdpa", "torch_compile_invoked": False,
            "network_boundary": worker.NETWORK_BOUNDARY, "network_use_proven": False,
        }


class TemporaryAiQwen3TtsForgeV2Tests(unittest.TestCase):
    def test_v1_checkpoint_is_byte_preserved(self) -> None:
        self.assertEqual(worker.sha256_file(V1_CHECKPOINT), "a4f10dd5206f0a74aa2058fa48b886ca5f1a7c2b2f2f9a2e0b8415d2b36ae06c")

    def test_contract_truthfully_says_offline_flags_only(self) -> None:
        contract = json.loads(CONTRACT_SOURCE.read_text(encoding="utf-8"))
        self.assertEqual(contract["execution"]["network_boundary"], worker.NETWORK_BOUNDARY)
        self.assertFalse(contract["execution"]["network_nonuse_may_be_claimed"])

    def test_no_network_used_false_assertion_exists(self) -> None:
        source = WORKER_SOURCE.read_text(encoding="utf-8") + RUNNER_SOURCE.read_text(encoding="utf-8")
        self.assertNotIn('"network_used"', source)
        self.assertNotIn("network_used=False", source)

    def test_worker_import_is_inert(self) -> None:
        prefix = WORKER_SOURCE.read_text(encoding="utf-8").split("class OfficialRuntimeV2", 1)[0]
        self.assertNotIn("import torch", prefix)
        self.assertNotIn("import qwen_tts", prefix)

    def test_runtime_imports_torch_and_qwen_only_after_provenance_and_cuda_gates(self) -> None:
        source = WORKER_SOURCE.read_text(encoding="utf-8")
        runtime_source = source.split("class OfficialRuntimeV2", 1)[1].split("class OfficialSpeechEvaluatorV2", 1)[0]
        record_gate = runtime_source.index("verify_installed_distribution")
        torch_import = runtime_source.index('self.torch = importlib.import_module("torch")')
        eager_gate = runtime_source.index("a @ b")
        qwen_import = runtime_source.index('importlib.import_module("qwen_tts")')
        self.assertLess(record_gate, torch_import)
        self.assertLess(torch_import, eager_gate)
        self.assertLess(eager_gate, qwen_import)

    def test_parent_never_imports_worker(self) -> None:
        source = RUNNER_SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("import qwen3_tts_original_voice_forge_worker_v2", source)

    def test_official_qwen_api_and_eager_sdpa_are_exact(self) -> None:
        source = WORKER_SOURCE.read_text(encoding="utf-8")
        for token in ("Qwen3TTSModel.from_pretrained", ".generate_voice_design(", ".create_voice_clone_prompt(", ".generate_voice_clone(", 'attn_implementation="sdpa"', "local_files_only=True"):
            self.assertIn(token, source)
        self.assertNotIn("torch.compile(", source)
        self.assertNotIn("flash_attention_2", source)

    def test_caller_can_supply_only_bundle_id_and_acknowledgements(self) -> None:
        args = launcher.parse_args(["--bundle-id", "bundle_001"])
        self.assertFalse(hasattr(args, "contract_sha256"))
        self.assertFalse(hasattr(args, "worker_sha256"))
        self.assertFalse(hasattr(args, "authorization_path"))

    def test_pending_environment_fails_closed(self) -> None:
        spec = json.loads(ENVIRONMENT_SOURCE.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(worker.R2ForgeError, "not accepted ready"):
            worker.validate_environment_spec_static(spec, require_ready=True)

    def test_restricted_environment_does_not_copy_secret(self) -> None:
        with mock.patch.dict(os.environ, {"FORGE_R2_SECRET": "never-copy"}, clear=False):
            env = launcher.restricted_child_environment(isolated_python=Path(r"C:\isolated\.venv\Scripts\python.exe"))
        self.assertNotIn("FORGE_R2_SECRET", env)
        self.assertEqual(env["HF_HUB_OFFLINE"], "1")

    def test_parent_reserves_and_preserves_preflight_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(launcher, "PROJECT_ROOT", Path(temp)):
            args = launcher.parse_args(["--execute", "--bundle-id", "bundle_fail_001", "--acknowledge-private-unreviewed", "--acknowledge-no-download"])
            with self.assertRaises(launcher.R2LauncherError):
                launcher.run(args)
            failure = Path(temp) / launcher.OUTPUT_ROOT_REL / "bundle_fail_001/attempt_01/parent_preflight_failure_v2.json"
            self.assertTrue(failure.is_file())
            self.assertFalse(json.loads(failure.read_text())["worker_started"])

    def test_preflight_failures_are_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(launcher, "PROJECT_ROOT", Path(temp)):
            args = launcher.parse_args(["--execute", "--bundle-id", "bundle_fail_002", "--acknowledge-private-unreviewed", "--acknowledge-no-download"])
            for _ in range(2):
                with self.assertRaises(launcher.R2LauncherError):
                    launcher.run(args)
            root = Path(temp) / launcher.OUTPUT_ROOT_REL / "bundle_fail_002"
            self.assertTrue((root / "attempt_01/parent_preflight_failure_v2.json").is_file())
            self.assertTrue((root / "attempt_02/parent_preflight_failure_v2.json").is_file())

    def test_nonce_is_single_use_and_queue_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(launcher, "PROJECT_ROOT", Path(temp)):
            bundle = {
                "bundle_id": "b", "candidate_id": "c", "opaque_voice_id": "v", "ai_type": "expert_temp_ai",
                "single_use_nonce_sha256": "1" * 64, "queue_binding_sha256": "2" * 64, "job_sha256": "3" * 64,
                "canonical_profile_sha256": "4" * 64, "canonical_creation_request_sha256": "5" * 64,
                "identity_clearance_manifest_sha256": "6" * 64, "watermark_evidence_manifest_sha256": "7" * 64,
                "evaluation_corpus_sha256": "8" * 64, "voice_design_model_manifest_sha256": "9" * 64,
                "base_model_manifest_sha256": "a" * 64, "environment_spec_sha256": "b" * 64,
            }
            attempt = Path(temp) / launcher.OUTPUT_ROOT_REL / "b/attempt_01"
            attempt.mkdir(parents=True)
            launcher.consume_nonce(bundle, attempt)
            with self.assertRaisesRegex(launcher.R2LauncherError, "append-only"):
                launcher.consume_nonce(bundle, attempt)

    def test_queue_binding_changes_with_candidate_job_or_nonce(self) -> None:
        bundle = {"bundle_id": "bundle", "candidate_id": "candidate", "opaque_voice_id": "voice", "ai_type": "expert_temp_ai", "job_sha256": "1" * 64, "single_use_nonce_sha256": "2" * 64, "canonical_profile_sha256": "3" * 64, "canonical_creation_request_sha256": "4" * 64, "identity_clearance_manifest_sha256": "5" * 64, "watermark_evidence_manifest_sha256": "6" * 64, "evaluation_corpus_sha256": "7" * 64, "voice_design_model_manifest_sha256": "8" * 64, "base_model_manifest_sha256": "9" * 64, "environment_spec_sha256": "a" * 64}
        original = worker.compute_queue_binding(bundle)
        mutations = {
            "candidate_id": "other", "job_sha256": "b" * 64, "single_use_nonce_sha256": "c" * 64,
            "canonical_profile_sha256": "d" * 64, "canonical_creation_request_sha256": "e" * 64,
            "identity_clearance_manifest_sha256": "f" * 64, "watermark_evidence_manifest_sha256": "0" * 64,
            "evaluation_corpus_sha256": "1" * 64, "voice_design_model_manifest_sha256": "2" * 64,
            "base_model_manifest_sha256": "3" * 64, "environment_spec_sha256": "4" * 64,
        }
        for key, value in mutations.items():
            changed = dict(bundle)
            changed[key] = value
            with self.subTest(key=key):
                self.assertNotEqual(original, worker.compute_queue_binding(changed))

    def test_canonical_candidate_requires_exact_profile_and_creation_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate = "expert_original_001"
            directory = root / "TemporaryAI/candidates" / candidate
            profile = {"profile_id": f"{candidate}_temporary_ai_profile_v1", "candidate_id": candidate, "ai_type": "expert_temp_ai", "status": "draft"}
            creation = {"template_id": "temporary_ai_creation_request_template_v2", "request_id": f"temp_ai_request_{candidate}", "ai_type": "expert_temp_ai", "requested_by": "real_robert", "lifecycle": {"status": "draft"}}
            profile_path = directory / "temporary_ai_profile.json"
            creation_path = directory / "creation_request.json"
            write_json(profile_path, profile); write_json(creation_path, creation)
            bundle = {"candidate_id": candidate, "ai_type": "expert_temp_ai", "canonical_profile_path": worker.relative(profile_path, root), "canonical_profile_sha256": worker.sha256_file(profile_path), "canonical_creation_request_path": worker.relative(creation_path, root), "canonical_creation_request_sha256": worker.sha256_file(creation_path)}
            loaded_profile, loaded_creation = worker.validate_canonical_candidate(root, bundle)
            self.assertEqual(loaded_profile["profile_id"], f"{candidate}_temporary_ai_profile_v1")
            self.assertEqual(loaded_creation["requested_by"], "real_robert")
            bundle["canonical_profile_path"] = "TemporaryAI/candidates/fake/temporary_ai_profile.json"
            with self.assertRaisesRegex(worker.R2ForgeError, "canonical"):
                worker.validate_canonical_candidate(root, bundle)

    def test_ineligible_ai_type_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(worker.R2ForgeError, "not eligible"):
                worker.validate_canonical_candidate(Path(temp), {"candidate_id": "candidate_001", "ai_type": "canon_reconstruction_temp_ai"})

    def identity_fixture(self, traits: str) -> tuple[Path, dict, dict, dict, dict]:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        bundle_dir = Path(temp.name)
        traits_hash = worker.sha256_text(traits)
        analyzer_manifest = bundle_dir / "evidence/identity/model.json"
        analyzer_model = bundle_dir / "evidence/identity/model.bin"
        report_path = bundle_dir / "evidence/identity/report.json"
        review_path = bundle_dir / "evidence/identity/review.json"
        command_path = bundle_dir / "evidence/identity/command.json"
        stdout_path = bundle_dir / "evidence/identity/stdout.log"
        stderr_path = bundle_dir / "evidence/identity/stderr.log"
        analyzer_model.parent.mkdir(parents=True, exist_ok=True); analyzer_model.write_bytes(b"exact-test-analyzer-model")
        write_json(analyzer_manifest, {"schema": "qwen3_tts_identity_analyzer_model_manifest_v2", "status": "ACCEPTED_EXACT_LOCAL_ANALYZER", "engine": "exact-local", "version": "1", "complete_file_inventory": True, "files": [{"path": "evidence/identity/model.bin", "bytes": analyzer_model.stat().st_size, "sha256": worker.sha256_file(analyzer_model)}]})
        write_json(command_path, {"schema": "qwen3_tts_identity_analyzer_command_v2", "engine": "exact-local", "version": "1", "input_sha256": traits_hash, "argv": ["exact-local-analyzer"]})
        stdout_path.write_text("exact analyzer completed\n", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        write_json(report_path, {"schema": "qwen3_tts_identity_analyzer_report_v2", "mode": "REAL_LOCAL_NER_AND_IMITATION_CLASSIFIER", "analyzer_name": "exact-local", "analyzer_version": "1", "analyzer_model_manifest_path": "evidence/identity/model.json", "analyzer_model_manifest_sha256": worker.sha256_file(analyzer_manifest), "input_sha256": traits_hash, "detected_named_person_entities": [], "named_person_imitation_requested": False, "execution_mode": "HASH_BOUND_LOCAL_ANALYZER_EXECUTION", "process_returncode": 0, "command_path": "evidence/identity/command.json", "command_sha256": worker.sha256_file(command_path), "stdout_path": "evidence/identity/stdout.log", "stdout_sha256": worker.sha256_file(stdout_path), "stderr_path": "evidence/identity/stderr.log", "stderr_sha256": worker.sha256_file(stderr_path)})
        write_json(review_path, {"schema": "qwen3_tts_owner_identity_clearance_v2", "decision": "CLEARED_ORIGINAL_TRAIT_ONLY", "owner_id": "robert", "design_traits_sha256": traits_hash})
        sealed = {}
        for path in (analyzer_manifest, analyzer_model, command_path, stdout_path, stderr_path, report_path, review_path):
            sealed[worker.relative(path, bundle_dir)] = {"sha256": worker.sha256_file(path), "bytes": path.stat().st_size}
        manifest = {"schema": "qwen3_tts_original_voice_identity_clearance_manifest_v2", "status": "CLEARED_ORIGINAL_TRAIT_ONLY", "candidate_id": "candidate", "opaque_voice_id": "voice", "design_traits_sha256": traits_hash, "analyzer_report_path": "evidence/identity/report.json", "analyzer_report_sha256": worker.sha256_file(report_path), "owner_review_path": "evidence/identity/review.json", "owner_review_sha256": worker.sha256_file(review_path)}
        return bundle_dir, manifest, sealed, {"design_traits_text": traits, "design_traits_text_sha256": traits_hash}, {"candidate_id": "candidate", "opaque_voice_id": "voice"}

    def test_identity_clearance_requires_hashed_real_analyzer_evidence(self) -> None:
        bundle_dir, manifest, sealed, job, bundle = self.identity_fixture("An original calm adult expert voice.")
        worker.validate_identity_clearance(bundle_dir=bundle_dir, manifest=manifest, sealed=sealed, job=job, bundle=bundle)
        report = bundle_dir / "evidence/identity/report.json"
        payload = json.loads(report.read_text())
        payload["mode"] = "REGEX_ONLY"
        write_json(report, payload)
        manifest["analyzer_report_sha256"] = worker.sha256_file(report)
        sealed["evidence/identity/report.json"]["sha256"] = worker.sha256_file(report)
        sealed["evidence/identity/report.json"]["bytes"] = report.stat().st_size
        with self.assertRaisesRegex(worker.R2ForgeError, "self-asserted|provenance"):
            worker.validate_identity_clearance(bundle_dir=bundle_dir, manifest=manifest, sealed=sealed, job=job, bundle=bundle)

    def test_taylor_swift_imitation_fails_despite_forged_clear_report(self) -> None:
        traits = "Give this expert a voice that sounds exactly like Taylor Swift."
        bundle_dir, manifest, sealed, job, bundle = self.identity_fixture(traits)
        with self.assertRaisesRegex(worker.R2ForgeError, "named-person|imitation"):
            worker.validate_identity_clearance(bundle_dir=bundle_dir, manifest=manifest, sealed=sealed, job=job, bundle=bundle)

    def watermark_fixture(self) -> tuple[Path, dict, dict, dict]:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        tool = root / "evidence/watermark/scan.py"; tool.parent.mkdir(parents=True); tool.write_text("# accepted test scanner\n")
        scanned = root / "revision/qwen_tts_source.py"; scanned.parent.mkdir(parents=True); scanned.write_text("def synthesize():\n    return 'audio'\n", encoding="utf-8")
        inventory = root / "evidence/watermark/files.json"
        write_json(inventory, {"schema": "qwen3_tts_watermark_scanned_file_manifest_v2", "complete_inventory": True, "files": [{"path": worker.relative(scanned, root), "bytes": scanned.stat().st_size, "sha256": worker.sha256_file(scanned)}]})
        bundle = {"voice_design_model_manifest_sha256": "1" * 64, "base_model_manifest_sha256": "2" * 64}
        evidence_rows = []
        paths = [tool, inventory]
        for kind, name in (("EXACT_REVISION_SOURCE_SCAN", "source.json"), ("EXACT_DEPENDENCY_SCAN", "deps.json")):
            path = root / "evidence/watermark" / name
            write_json(path, {"schema": "qwen3_tts_watermark_preflight_evidence_v2", "kind": kind, "status": "PASS_NO_DOCUMENTED_INTENTIONAL_WATERMARK_STAGE_FOUND", "scan_tool": "evidence/watermark/scan.py", "scan_tool_version": "1", "scan_tool_sha256": worker.sha256_file(tool), "scanned_file_manifest_path": "evidence/watermark/files.json", "scanned_file_manifest_sha256": worker.sha256_file(inventory), "findings": [], "watermark_removal_or_circumvention_attempted": False, **bundle})
            evidence_rows.append({"kind": kind, "path": worker.relative(path, root), "sha256": worker.sha256_file(path)})
            paths.append(path)
        sealed = {worker.relative(path, root): {"sha256": worker.sha256_file(path), "bytes": path.stat().st_size} for path in paths}
        manifest = {"schema": "qwen3_tts_original_voice_watermark_preflight_manifest_v2", "status": "PREFLIGHT_EVIDENCE_COMPLETE_INITIAL_STATUS_ONLY", "permitted_runtime_status": worker.INITIAL_WATERMARK_STATUS, "stronger_status_requested": False, "evidence": evidence_rows}
        return root, manifest, sealed, bundle

    def test_watermark_evidence_files_are_resolved_and_hashed(self) -> None:
        root, manifest, sealed, bundle = self.watermark_fixture()
        self.assertEqual(
            worker.validate_watermark_preflight(project_root=root, bundle_dir=root, manifest=manifest, sealed=sealed, bundle=bundle),
            worker.HISTORICAL_WATERMARK_PREFLIGHT_STATUS,
        )
        (root / "evidence/watermark/scan.py").write_text("tampered\n")
        with self.assertRaisesRegex(worker.R2ForgeError, "hash mismatch"):
            worker.validate_watermark_preflight(project_root=root, bundle_dir=root, manifest=manifest, sealed=sealed, bundle=bundle)

    def test_stronger_watermark_status_is_never_self_asserted(self) -> None:
        root, manifest, sealed, bundle = self.watermark_fixture()
        manifest["stronger_status_requested"] = True
        with self.assertRaisesRegex(worker.R2ForgeError, "stronger"):
            worker.validate_watermark_preflight(project_root=root, bundle_dir=root, manifest=manifest, sealed=sealed, bundle=bundle)

    def test_watermark_removal_or_circumvention_fails(self) -> None:
        root, manifest, sealed, bundle = self.watermark_fixture()
        path = root / manifest["evidence"][0]["path"]
        payload = json.loads(path.read_text()); payload["watermark_removal_or_circumvention_attempted"] = True
        write_json(path, payload)
        digest = worker.sha256_file(path); manifest["evidence"][0]["sha256"] = digest
        sealed[worker.relative(path, root)] = {"sha256": digest, "bytes": path.stat().st_size}
        with self.assertRaisesRegex(worker.R2ForgeError, "removal|circumvention"):
            worker.validate_watermark_preflight(project_root=root, bundle_dir=root, manifest=manifest, sealed=sealed, bundle=bundle)

    def test_empty_historical_watermark_inventory_fails_closed(self) -> None:
        root, manifest, sealed, bundle = self.watermark_fixture()
        inventory = root / "evidence/watermark/files.json"
        write_json(inventory, {"schema": "qwen3_tts_watermark_scanned_file_manifest_v2", "complete_inventory": True, "files": []})
        for evidence_row in manifest["evidence"]:
            path = root / evidence_row["path"]
            payload = json.loads(path.read_text())
            payload["scanned_file_manifest_sha256"] = worker.sha256_file(inventory)
            write_json(path, payload)
            evidence_row["sha256"] = worker.sha256_file(path)
            sealed[evidence_row["path"]] = {"sha256": worker.sha256_file(path), "bytes": path.stat().st_size}
        sealed["evidence/watermark/files.json"] = {"sha256": worker.sha256_file(inventory), "bytes": inventory.stat().st_size}
        with self.assertRaisesRegex(worker.R2ForgeError, "empty"):
            worker.validate_watermark_preflight(project_root=root, bundle_dir=root, manifest=manifest, sealed=sealed, bundle=bundle)

    def test_live_watermark_scan_executes_on_real_files_and_rejects_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            attempt = root / "attempt_01"; attempt.mkdir()
            snapshot = root / "snapshot"; snapshot.mkdir()
            source = snapshot / "dependency.py"
            source.write_text("def build_audio():\n    return embed_audio_watermark()\n", encoding="utf-8")
            for rel in (
                worker.WORKER_REL, worker.RUNNER_REL, worker.CONTRACT_REL,
                worker.ENVIRONMENT_REL, worker.HARNESS_MANIFEST_REL,
            ):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# exact bounded test source\n", encoding="utf-8")
            python = root / worker.ISOLATED_VENV_REL / "Scripts/python.exe"
            python.parent.mkdir(parents=True, exist_ok=True)
            python.write_bytes(b"exact-python")
            site_file = root / worker.ISOLATED_VENV_REL / "Lib/site-packages/exact_dependency.py"
            site_file.parent.mkdir(parents=True, exist_ok=True)
            site_file.write_text("VALUE = 1\n", encoding="utf-8")
            site_manifest = root / worker.ISOLATED_ROOT_REL / "site_packages_inventory_v2.json"
            write_json(site_manifest, {"schema": "bounded-test-site-inventory"})
            wheel_archives = {}
            for package in ("torch", "torchaudio"):
                wheel = root / worker.WHEEL_EVIDENCE_ROOT_REL / f"{package}-exact.whl"
                wheel.parent.mkdir(parents=True, exist_ok=True)
                wheel.write_bytes(f"{package}-wheel".encode())
                wheel_archives[package] = {
                    "path": worker.relative(wheel, root),
                    "sha256": worker.sha256_file(wheel),
                }
            environment = {
                "python_executable_path": worker.relative(python, root),
                "site_packages_inventory": {
                    "manifest_path": worker.relative(site_manifest, root),
                    "manifest_sha256": worker.sha256_file(site_manifest),
                    "complete_file_inventory": True,
                    "all_transitive_distributions_declared": True,
                    "all_loose_files_declared": True,
                    "files": [{
                        "path": worker.relative(site_file, root),
                        "bytes": site_file.stat().st_size,
                        "sha256": worker.sha256_file(site_file),
                    }],
                },
                "wheel_archives": wheel_archives,
            }
            with self.assertRaisesRegex(worker.R2ForgeError, "watermark"):
                worker.run_live_watermark_documentation_scan(
                    project_root=root, attempt_dir=attempt, model_snapshots=[snapshot],
                    evaluator_snapshots={}, environment_evidence=environment,
                )
            report = json.loads((attempt / "live_watermark_documentation_scan_v2.json").read_text())
            self.assertEqual(report["status"], "FAIL_INTENTIONAL_AUDIO_WATERMARK_IMPLEMENTATION_MARKER_FOUND")
            self.assertFalse(report["stronger_detector_status_granted"])
            self.assertFalse(report["complete_exact_file_inventory"])
            self.assertTrue(report["scan_scope_exhaustively_declared"])
            self.assertFalse(report["bounded_execution_dependency_inventory_complete"])

    def audio_inputs(self) -> tuple[dict, dict, dict, dict, dict]:
        job = {"reference_text": "Exact reference speech here", "test_text": "Exact clone speech here"}
        reference = exact_eval(job["reference_text"], [1.0, 0.0])
        clone = exact_eval(job["test_text"], [0.99, 0.01])
        corpus = {"voices": [
            {"voice_id": "resident", "kind": "approved_resident", "embedding": [0.0, 1.0], "recomputed_from_exact_wav": True},
            {"voice_id": "generic", "kind": "known_generic", "embedding": [-1.0, 0.0], "recomputed_from_exact_wav": True},
        ]}
        contract = {"audio_acceptance": {"maximum_word_error_rate": 0.05, "minimum_speech_probability": 0.9, "maximum_pure_tone_probability": 0.1, "minimum_reference_to_clone_similarity": 0.8, "maximum_similarity_to_resident_or_generic_voice": 0.72}}
        return job, reference, clone, corpus, contract

    def validate_audio(self, job: dict, reference: dict, clone: dict, corpus: dict, contract: dict) -> dict:
        environment = {"speech_evaluators": {
            "asr_engine": "test-real-asr", "asr_version": "1.0", "asr_model_manifest_sha256": "a" * 64,
            "speech_classifier_engine": "test-real-speech", "speech_classifier_version": "1.0",
            "speech_classifier_model_manifest_sha256": "c" * 64, "speech_classifier_adapter_sha256": "d" * 64,
            "speaker_embedding_engine": "test-real-embedding", "speaker_embedding_version": "1.0",
            "speaker_model_manifest_sha256": "b" * 64,
            "speaker_input_sample_rate_hz": 16000,
            "speaker_resampling_method": "TORCHAUDIO_FUNCTIONAL_RESAMPLE_FLOAT32_V1",
        }}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for label, evidence in (("reference", reference), ("clone", clone)):
                artifact = root / f"{label}_speaker_input.wav"
                write_test_wav(artifact, 231.0 if label == "reference" else 289.0)
                evidence.update({
                    "source_sample_rate_hz": 16000,
                    "speaker_input_sample_rate_hz": 16000,
                    "speaker_resampling_method": "TORCHAUDIO_FUNCTIONAL_RESAMPLE_FLOAT32_V1",
                    "resampled_for_embedding": False,
                    "embedding_input_wav_path": worker.relative(artifact, root),
                    "embedding_input_wav_sha256": worker.sha256_file(artifact),
                    "embedding_input_wav_bytes": artifact.stat().st_size,
                    "embedding_computed_from_reloaded_exact_pcm16_artifact": True,
                })
            return worker.validate_audio_acceptance(
                job=job, reference_eval=reference, clone_eval=clone, corpus=corpus, contract=contract,
                environment_spec=environment, reference_wav_sha256="e" * 64,
                clone_wav_sha256="e" * 64, project_root=root,
            )

    def test_real_asr_text_fidelity_is_mandatory(self) -> None:
        job, reference, clone, corpus, contract = self.audio_inputs()
        clone["transcript"] = "completely unrelated words"
        with self.assertRaisesRegex(worker.R2ForgeError, "ASR text fidelity"):
            self.validate_audio(job, reference, clone, corpus, contract)

    def test_sine_or_pure_tone_evidence_fails(self) -> None:
        job, reference, clone, corpus, contract = self.audio_inputs()
        clone["pure_tone_probability"] = 0.99
        with self.assertRaisesRegex(worker.R2ForgeError, "sine|pure-tone"):
            self.validate_audio(job, reference, clone, corpus, contract)

    def test_actual_pcm16_sine_is_measured_as_persistent_pure_tone(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            wav = Path(temp) / "sine.wav"
            write_test_wav(wav, 400.0)
            self.assertGreater(worker.pcm16_multiwindow_pure_tone_probability(wav), 0.80)

    def test_official_evaluator_path_measures_actual_sine_not_an_injected_tone_field(self) -> None:
        class Segment:
            text = "Exact clone speech here"

        class Asr:
            @staticmethod
            def transcribe(_path: str, **_kwargs):
                return [Segment()], {}

        with tempfile.TemporaryDirectory() as temp:
            wav = Path(temp) / "sine.wav"
            write_test_wav(wav, 400.0)
            evaluator = object.__new__(worker.OfficialSpeechEvaluatorV2)
            evaluator.asr = Asr()
            evaluator.asr_engine = "test-real-asr"
            evaluator.asr_version = "1.0"
            evaluator.asr_manifest_hash = "a" * 64
            evaluator.speaker_embedding = lambda path: {
                "embedding_mode": "REAL_LOCAL_SPEAKER_EMBEDDING",
                "embedding_engine": "test-real-embedding",
                "embedding_version": "1.0",
                "embedding_model_manifest_sha256": "b" * 64,
                "source_wav_sha256": worker.sha256_file(path),
                "speaker_embedding": [0.99, 0.01],
            }
            evaluator._speech_classifier = lambda path: {
                "speech_mode": "REAL_LOCAL_SPEECH_CLASSIFIER",
                "speech_classifier_engine": "test-real-speech",
                "speech_classifier_version": "1.0",
                "speech_classifier_model_manifest_sha256": "c" * 64,
                "speech_classifier_adapter_sha256": "d" * 64,
                "speech_classifier_source_wav_sha256": worker.sha256_file(path),
                "speech_probability": 0.99,
            }
            evidence = worker.OfficialSpeechEvaluatorV2.evaluate(
                evaluator,
                wav,
                expected_text="Exact clone speech here",
                language="English",
            )
            self.assertEqual(evidence["pure_tone_detector"], "MULTIWINDOW_SPECTRAL_CONCENTRATION_V2")
            self.assertGreater(evidence["pure_tone_probability"], 0.80)

    def test_non_speech_evidence_fails(self) -> None:
        job, reference, clone, corpus, contract = self.audio_inputs()
        clone["speech_probability"] = 0.1
        with self.assertRaisesRegex(worker.R2ForgeError, "real speech"):
            self.validate_audio(job, reference, clone, corpus, contract)

    def test_non_finite_audio_or_embedding_evidence_fails(self) -> None:
        job, reference, clone, corpus, contract = self.audio_inputs()
        clone["speech_probability"] = float("nan")
        with self.assertRaisesRegex(worker.R2ForgeError, "non-finite"):
            self.validate_audio(job, reference, clone, corpus, contract)
        job, reference, clone, corpus, contract = self.audio_inputs()
        clone["speaker_embedding"] = [float("nan"), 0.0]
        with self.assertRaisesRegex(worker.R2ForgeError, "non-finite"):
            self.validate_audio(job, reference, clone, corpus, contract)

    def test_generic_substitute_voice_collision_fails(self) -> None:
        job, reference, clone, corpus, contract = self.audio_inputs()
        clone["speaker_embedding"] = [-1.0, 0.0]
        reference["speaker_embedding"] = [-1.0, 0.0]
        with self.assertRaisesRegex(worker.R2ForgeError, "known_generic"):
            self.validate_audio(job, reference, clone, corpus, contract)

    def test_real_audio_evidence_happy_path_passes(self) -> None:
        job, reference, clone, corpus, contract = self.audio_inputs()
        result = self.validate_audio(job, reference, clone, corpus, contract)
        self.assertTrue(result["real_speech_and_asr"])
        self.assertTrue(result["generic_or_resident_substitute_rejected"])

    def test_runtime_environment_requires_every_distribution_record(self) -> None:
        fixture = ExecutionFixture(self)
        evidence = fixture.environment_evidence()
        worker.validate_runtime_environment_evidence(evidence, fixture.environment)
        evidence["distributions"]["transformers"]["record_sha256"] = "f" * 64
        with self.assertRaisesRegex(worker.R2ForgeError, "transformers.*RECORD"):
            worker.validate_runtime_environment_evidence(evidence, fixture.environment)

    def test_post_import_binding_rejects_loose_shadow_module_for_every_runtime_package(self) -> None:
        fixture = ExecutionFixture(self)
        environment = fixture.environment_evidence()
        for package in (
            "torch", "torchaudio", "qwen-tts", "transformers", "accelerate",
            "faster-whisper", "speechbrain",
        ):
            shadow = fixture.root / "unattested_shadow" / f"{package.replace('-', '_')}.py"
            shadow.parent.mkdir(parents=True, exist_ok=True)
            shadow.write_text("SHADOW = True\n", encoding="utf-8")
            module = type("ShadowModule", (), {
                "__file__": str(shadow),
                "__name__": package.replace("-", "_"),
                "__path__": [],
            })()
            with self.subTest(package=package), self.assertRaisesRegex(
                worker.R2ForgeError, "not a member of its verified RECORD"
            ):
                worker.bind_imported_module_to_attested_record(
                    package=package,
                    module=module,
                    distribution_evidence=environment["distributions"][package],
                    project_root=fixture.root,
                )

    def test_complete_site_packages_inventory_rejects_new_loose_file(self) -> None:
        fixture = ExecutionFixture(self)
        site_packages = fixture.root / worker.ISOLATED_VENV_REL / "Lib/site-packages"
        (site_packages / "undeclared_shadow.py").write_text("SHADOW = True\n", encoding="utf-8")
        with self.assertRaisesRegex(worker.R2ForgeError, "inventory drift"):
            worker.verify_complete_site_packages_inventory(
                project_root=fixture.root,
                spec=fixture.environment,
                distribution_evidence=fixture.environment_evidence()["distributions"],
            )

    def test_post_execution_provenance_rejects_a_loaded_loose_site_module(self) -> None:
        fixture = ExecutionFixture(self)
        modules = {}
        site_packages = fixture.root / worker.ISOLATED_VENV_REL / "Lib/site-packages"
        for package in (
            "torch", "torchaudio", "qwen-tts", "transformers", "accelerate",
            "faster-whisper", "speechbrain",
        ):
            path = site_packages / f"{package.replace('-', '_')}_bounded_test.py"
            modules[f"bounded_{package.replace('-', '_')}"] = type("BoundModule", (), {
                "__file__": str(path), "__path__": [],
            })()
        runtime = worker.OfficialRuntimeV2()
        distribution_evidence = fixture.environment_evidence()["distributions"]
        site_evidence = fixture.environment_evidence()["site_packages_inventory"]
        distribution_patch = mock.patch.object(
            worker,
            "verify_installed_distribution",
            side_effect=lambda *, project_root, package, row: distribution_evidence[package],
        )
        site_patch = mock.patch.object(
            worker,
            "verify_complete_site_packages_inventory",
            return_value=site_evidence,
        )
        with distribution_patch, site_patch, mock.patch.dict(os.sys.modules, modules, clear=False):
            accepted = runtime.post_execution_provenance(fixture.environment, fixture.root)
        self.assertTrue(accepted["every_loaded_site_packages_module_bound_to_verified_record"])

        loose = site_packages / "aaa_loaded_loose.py"
        loose.write_text("LOOSE = True\n", encoding="utf-8")
        inventory_path = fixture.root / fixture.environment["site_packages_inventory"]["manifest_path"]
        inventory = json.loads(inventory_path.read_text())
        inventory["files"].append({
            "path": worker.relative(loose, site_packages),
            "bytes": loose.stat().st_size,
            "sha256": worker.sha256_file(loose),
            "owner_distributions": [],
            "loose_unowned_file": True,
        })
        inventory["files"] = sorted(inventory["files"], key=lambda row: row["path"])
        write_json(inventory_path, inventory)
        fixture.environment["site_packages_inventory"]["manifest_sha256"] = worker.sha256_file(inventory_path)
        loose_module = type("LooseModule", (), {"__file__": str(loose), "__path__": []})()
        with distribution_patch, site_patch, mock.patch.dict(
            os.sys.modules, {**modules, "aaa_loaded_loose": loose_module}, clear=False
        ):
            with self.assertRaisesRegex(worker.R2ForgeError, "loose|outside every verified RECORD"):
                runtime.post_execution_provenance(fixture.environment, fixture.root)

    def test_runtime_environment_rejects_wrong_python_and_wheel(self) -> None:
        fixture = ExecutionFixture(self)
        evidence = fixture.environment_evidence(); evidence["python_version"] = "3.12.0"
        with self.assertRaisesRegex(worker.R2ForgeError, "Python"):
            worker.validate_runtime_environment_evidence(evidence, fixture.environment)
        evidence = fixture.environment_evidence(); evidence["torch_wheel_sha256"] = "0" * 64
        with self.assertRaisesRegex(worker.R2ForgeError, "wheel"):
            worker.validate_runtime_environment_evidence(evidence, fixture.environment)

    def test_runtime_environment_rejects_device_capability_sm120_and_eager_drift(self) -> None:
        fixture = ExecutionFixture(self)
        for key, value, pattern in (
            ("device_name", "Other GPU", "device"),
            ("compute_capability", [8, 9], "capability"),
            ("sm_120_present", False, "sm_120"),
            ("ordinary_eager_cuda_matrix_result", [[0]], "eager"),
        ):
            evidence = fixture.environment_evidence(); evidence[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(worker.R2ForgeError, pattern):
                worker.validate_runtime_environment_evidence(evidence, fixture.environment)

    def test_embedding_input_is_bound_to_exact_cross_rate_resampling_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            attempt = root / worker.OUTPUT_ROOT_REL / "bundle" / "attempt_01"
            attempt.mkdir(parents=True)
            source = attempt / "source_24000.wav"
            normalized = attempt / "speaker_embedding_inputs" / "normalized_16000.wav"
            write_test_wav(source, 233.0, sample_rate=24000)
            write_test_wav(normalized, 233.0, sample_rate=16000)
            evidence = {
                "source_wav_sha256": worker.sha256_file(source),
                "source_sample_rate_hz": 24000,
                "speaker_input_sample_rate_hz": 16000,
                "speaker_resampling_method": "TORCHAUDIO_FUNCTIONAL_RESAMPLE_FLOAT32_V1",
                "resampled_for_embedding": True,
                "embedding_input_wav_path": worker.relative(normalized, root),
                "embedding_input_wav_sha256": worker.sha256_file(normalized),
                "embedding_input_wav_bytes": normalized.stat().st_size,
                "embedding_computed_from_reloaded_exact_pcm16_artifact": True,
            }
            result = worker.validate_embedding_input_artifact(
                evidence=evidence,
                source_wav_path=source,
                source_wav_sha256=worker.sha256_file(source),
                project_root=root,
                speaker_input_sample_rate_hz=16000,
                speaker_resampling_method="TORCHAUDIO_FUNCTIONAL_RESAMPLE_FLOAT32_V1",
            )
            self.assertTrue(result["resampled_for_embedding"])
            broken = dict(evidence, resampled_for_embedding=False)
            with self.assertRaisesRegex(worker.R2ForgeError, "resampling decision"):
                worker.validate_embedding_input_artifact(
                    evidence=broken,
                    source_wav_path=source,
                    source_wav_sha256=worker.sha256_file(source),
                    project_root=root,
                    speaker_input_sample_rate_hz=16000,
                    speaker_resampling_method="TORCHAUDIO_FUNCTIONAL_RESAMPLE_FLOAT32_V1",
                )

    def test_official_speaker_embedding_resamples_cross_rate_audio_before_encoding(self) -> None:
        class FakeSignal:
            def to(self, **_kwargs):
                return self

        class FakeEmbedding:
            def detach(self): return self
            def cpu(self): return self
            def reshape(self, *_shape): return self
            def tolist(self): return [1.0, 0.0]

        class FakeSpeaker:
            def encode_batch(self, signal):
                self.received = signal
                return FakeEmbedding()

        calls: list[tuple[int, int]] = []

        class Functional:
            @staticmethod
            def resample(signal, source_rate, target_rate):
                calls.append((source_rate, target_rate))
                return signal

        class FakeTorchaudio:
            functional = Functional()

            @staticmethod
            def load(path):
                with wave.open(str(path), "rb") as reader:
                    return FakeSignal(), reader.getframerate()

            @staticmethod
            def save(path, _signal, sample_rate, **_kwargs):
                write_test_wav(Path(path), 271.0, sample_rate=sample_rate)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            attempt = root / worker.OUTPUT_ROOT_REL / "bundle" / "attempt_01"
            attempt.mkdir(parents=True)
            source = attempt / "source_24000.wav"
            write_test_wav(source, 271.0, sample_rate=24000)
            evaluator = object.__new__(worker.OfficialSpeechEvaluatorV2)
            evaluator.project_root = root
            evaluator.torchaudio = FakeTorchaudio()
            evaluator.torch = type("FakeTorch", (), {"float32": object()})()
            evaluator.speaker = FakeSpeaker()
            evaluator.speaker_input_sample_rate_hz = 16000
            evaluator.speaker_resampling_method = "TORCHAUDIO_FUNCTIONAL_RESAMPLE_FLOAT32_V1"
            evaluator.embedding_engine = "test-real-embedding"
            evaluator.embedding_version = "1.0"
            evaluator.embedding_manifest_hash = "b" * 64
            evidence = worker.OfficialSpeechEvaluatorV2.speaker_embedding(evaluator, source)
            self.assertEqual(calls, [(24000, 16000)])
            self.assertTrue(evidence["resampled_for_embedding"])
            self.assertTrue(evidence["embedding_computed_from_reloaded_exact_pcm16_artifact"])
            normalized = root / evidence["embedding_input_wav_path"]
            _samples, rate = worker._wav_samples(normalized)
            self.assertEqual(rate, 16000)
            write_test_wav(normalized, 233.0, sample_rate=24000)
            evidence["embedding_input_wav_sha256"] = worker.sha256_file(normalized)
            evidence["embedding_input_wav_bytes"] = normalized.stat().st_size
            with self.assertRaisesRegex(worker.R2ForgeError, "wrong rate"):
                worker.validate_embedding_input_artifact(
                    evidence=evidence,
                    source_wav_path=source,
                    source_wav_sha256=worker.sha256_file(source),
                    project_root=root,
                    speaker_input_sample_rate_hz=16000,
                    speaker_resampling_method="TORCHAUDIO_FUNCTIONAL_RESAMPLE_FLOAT32_V1",
                )

    def test_collision_corpus_is_bound_to_exact_wavs_evidence_and_evaluator(self) -> None:
        fixture = ExecutionFixture(self)
        verified = worker.validate_evaluation_corpus(
            project_root=fixture.root,
            corpus=fixture.corpus,
            environment_spec=fixture.environment,
        )
        self.assertTrue(verified["verified_against_exact_files"])
        wav = fixture.root / verified["voices"][0]["source_wav_path"]
        wav.write_bytes(b"tampered")
        with self.assertRaisesRegex(worker.R2ForgeError, "hash mismatch"):
            worker.validate_evaluation_corpus(
                project_root=fixture.root,
                corpus=fixture.corpus,
                environment_spec=fixture.environment,
            )

    def test_collision_corpus_embeddings_are_recomputed_not_trusted_inline(self) -> None:
        fixture = ExecutionFixture(self)
        snapshot_corpus, _manifest = worker.create_private_corpus_snapshot(
            project_root=fixture.root,
            corpus=fixture.corpus,
            attempt_dir=fixture.attempt,
        )
        broken = json.loads(json.dumps(snapshot_corpus))
        broken["voices"][0]["verified_embedding"] = [1.0, 0.0]
        evaluator = FakeEvaluator(fixture.environment, fixture.root)
        with self.assertRaisesRegex(worker.R2ForgeError, "does not reproduce"):
            worker.recompute_collision_corpus(
                evaluator=evaluator,
                corpus=broken,
                project_root=fixture.root,
            )

    def test_collision_corpus_is_snapshotted_before_evaluation(self) -> None:
        fixture = ExecutionFixture(self)
        _snapshot, manifest = worker.create_private_corpus_snapshot(
            project_root=fixture.root, corpus=fixture.corpus, attempt_dir=fixture.attempt,
        )
        worker.verify_private_corpus_snapshot(attempt_dir=fixture.attempt, manifest=manifest)
        copied = fixture.attempt / manifest["files"][0]["path"]
        os.chmod(copied, 0o666)
        copied.write_bytes(b"tampered")
        with self.assertRaisesRegex(worker.R2ForgeError, "hash mismatch|size drift"):
            worker.verify_private_corpus_snapshot(attempt_dir=fixture.attempt, manifest=manifest)

    def test_model_private_snapshot_closes_source_toctou(self) -> None:
        fixture = ExecutionFixture(self)
        snapshot, manifest = worker.create_private_model_snapshot(project_root=fixture.root, bundle=fixture.bundle, attempt_dir=fixture.attempt, role="voice_design")
        worker.verify_private_snapshot(snapshot, manifest)
        os.chmod(snapshot / "config.json", 0o666)
        (snapshot / "config.json").write_bytes(b"changed-after-copy")
        with self.assertRaisesRegex(worker.R2ForgeError, "hash mismatch|size drift"):
            worker.verify_private_snapshot(snapshot, manifest)

    def test_evaluator_and_identity_snapshots_close_source_toctou(self) -> None:
        fixture = ExecutionFixture(self)
        snapshot_spec, manifests = worker.create_private_evaluator_snapshots(
            project_root=fixture.root, spec=fixture.environment, attempt_dir=fixture.attempt,
        )
        worker.verify_private_evaluator_snapshots(attempt_dir=fixture.attempt, snapshots=manifests)
        adapter = fixture.root / snapshot_spec["identity_analyzer"]["adapter_path"]
        os.chmod(adapter, 0o666)
        adapter.write_text("tampered\n", encoding="utf-8")
        with self.assertRaisesRegex(worker.R2ForgeError, "hash mismatch"):
            worker.verify_private_evaluator_snapshots(attempt_dir=fixture.attempt, snapshots=manifests)

    def test_live_identity_result_rejects_arbitrary_named_person_not_only_taylor(self) -> None:
        fixture = ExecutionFixture(self)
        analyzer = FakeIdentityAnalyzer(fixture.environment, fixture.root)
        result = analyzer.analyze(
            design_text=fixture.job["design_traits_text"],
            design_sha256=fixture.job["design_traits_text_sha256"],
            attempt_dir=fixture.attempt,
        )
        result["detected_named_person_entities"] = ["Beyonce Knowles"]
        result["named_person_probability"] = 0.99
        with self.assertRaisesRegex(worker.R2ForgeError, "named-person"):
            worker.validate_live_identity_result(
                result=result,
                identity_spec=fixture.environment["identity_analyzer"],
                design_text="Make this sound like Beyonce Knowles.",
                design_sha256=fixture.job["design_traits_text_sha256"],
            )

    def test_model_manifest_rejects_unlisted_source_file(self) -> None:
        fixture = ExecutionFixture(self)
        source = fixture.root / fixture.bundle["voice_design_model_directory"]
        (source / "unlisted.bin").write_bytes(b"drift")
        with self.assertRaisesRegex(worker.R2ForgeError, "complete source directory"):
            worker.create_private_model_snapshot(project_root=fixture.root, bundle=fixture.bundle, attempt_dir=fixture.attempt, role="voice_design")

    def test_worker_rejects_mismatched_nonce_ledger_binding(self) -> None:
        fixture = ExecutionFixture(self)
        reservation = json.loads((fixture.attempt / "parent_reservation.json").read_text())
        ledger = fixture.root / reservation["nonce_ledger_path"]
        payload = json.loads(ledger.read_text()); payload["candidate_id"] = "other_candidate"
        write_json(ledger, payload)
        reservation["nonce_ledger_sha256"] = worker.sha256_file(ledger)
        write_json(fixture.attempt / "parent_reservation.json", reservation)
        with self.assertRaisesRegex(worker.R2ForgeError, "candidate_id"):
            worker.execute_verified_bundle(trusted=fixture.trusted, attempt_dir=fixture.attempt, runtime_factory=lambda: FakeRuntime(fixture.environment_evidence()), evaluator_factory=FakeEvaluator, identity_analyzer_factory=FakeIdentityAnalyzer)

    def test_mocked_success_runs_serial_design_unload_base_clone(self) -> None:
        fixture = ExecutionFixture(self)
        runtime = FakeRuntime(fixture.environment_evidence())
        result = worker.execute_verified_bundle(trusted=fixture.trusted, attempt_dir=fixture.attempt, runtime_factory=lambda: runtime, evaluator_factory=FakeEvaluator, identity_analyzer_factory=FakeIdentityAnalyzer)
        self.assertEqual(runtime.events, ["load:voice_design", "generate_voice_design", "unload:voice_design", "load:runtime_clone", "create_voice_clone_prompt", "generate_voice_clone", "unload:runtime_clone"])
        self.assertEqual(result["status"], "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_INDEPENDENT_AUDIT")
        profile = json.loads((fixture.attempt / "voice_profile_candidate_v2.json").read_text())
        manifest = json.loads((fixture.attempt / "worker_manifest_v2.json").read_text())
        self.assertEqual(profile["owner_hearing_acceptance"], "PENDING")
        self.assertFalse(profile["assignment_allowed"])
        self.assertEqual(manifest["watermark_status"], worker.INITIAL_WATERMARK_STATUS)
        self.assertTrue((fixture.attempt / "live_watermark_documentation_scan_v2.json").is_file())
        live_scan = json.loads((fixture.attempt / "live_watermark_documentation_scan_v2.json").read_text())
        scanned_paths = {row["path"] for row in live_scan["files"]}
        self.assertIn(worker.relative(fixture.root / worker.WORKER_REL, fixture.root), scanned_paths)
        self.assertIn(fixture.environment["site_packages_inventory"]["manifest_path"], scanned_paths)
        self.assertIn(fixture.environment["distributions"]["torch"]["wheel_evidence_path"], scanned_paths)
        self.assertTrue(manifest["evaluator_snapshots"]["verified_after_evaluation"])
        self.assertTrue(
            manifest["post_execution_environment_provenance"]
            ["every_loaded_site_packages_module_bound_to_verified_record"]
        )
        telemetry = manifest["telemetry"]
        self.assertGreater(telemetry["torch_peak_cuda_allocated_bytes"], telemetry["baseline_cuda_allocated_bytes"])
        self.assertGreaterEqual(
            telemetry["os_reported_peak_process_rss_bytes"],
            telemetry["rss_sampler"]["maximum_observed_process_rss_bytes"],
        )
        self.assertTrue(telemetry["os_reported_peak_process_rss_is_high_water_mark"])
        self.assertFalse(telemetry["point_samples_labeled_as_peaks"])

    def test_mocked_success_writes_readable_non_silent_wavs(self) -> None:
        fixture = ExecutionFixture(self)
        worker.execute_verified_bundle(trusted=fixture.trusted, attempt_dir=fixture.attempt, runtime_factory=lambda: FakeRuntime(fixture.environment_evidence()), evaluator_factory=FakeEvaluator, identity_analyzer_factory=FakeIdentityAnalyzer)
        for name in ("original_design_reference.wav", "runtime_clone_test.wav"):
            samples, rate = worker._wav_samples(fixture.attempt / name)
            self.assertEqual(rate, 16000)
            self.assertGreater(max(abs(value) for value in samples), 0.01)

    def test_rss_sampler_observes_a_transient_without_calling_it_os_peak(self) -> None:
        state = {"rss": 1024}
        sampler = worker.PeakRssSampler(lambda: state["rss"], interval_seconds=0.005)
        sampler.start()
        state["rss"] = 65536
        time.sleep(0.025)
        state["rss"] = 2048
        evidence = sampler.stop()
        self.assertEqual(evidence["maximum_observed_process_rss_bytes"], 65536)
        self.assertGreaterEqual(evidence["sample_count"], 3)
        self.assertFalse(evidence["is_os_high_water_mark"])

    def test_os_process_peak_rss_is_available_without_loading_a_model(self) -> None:
        self.assertGreater(worker.OfficialRuntimeV2().peak_rss_bytes(), 0)

    def test_failure_is_text_plus_silence_without_substitute(self) -> None:
        fixture = ExecutionFixture(self)

        class RejectingEvaluator(FakeEvaluator):
            def evaluate(self, wav_path: Path, *, expected_text: str, language: str) -> dict:
                return exact_eval("wrong transcript", [1.0, 0.0])

        with self.assertRaises(worker.R2ForgeError):
            worker.execute_verified_bundle(trusted=fixture.trusted, attempt_dir=fixture.attempt, runtime_factory=lambda: FakeRuntime(fixture.environment_evidence()), evaluator_factory=RejectingEvaluator, identity_analyzer_factory=FakeIdentityAnalyzer)
        failure = json.loads((fixture.attempt / "worker_failure_v2.json").read_text())
        self.assertEqual(failure["fallback"]["voice_audio"], "SILENCE_NO_AUDIO")
        self.assertFalse(failure["fallback"]["generic_voice_used"])
        self.assertFalse(failure["fallback"]["sapi_used"])
        self.assertFalse(failure["fallback"]["other_person_voice_used"])

    def test_environment_spec_keeps_chatterbox_sealed_and_pending(self) -> None:
        spec = json.loads(ENVIRONMENT_SOURCE.read_text(encoding="utf-8"))
        self.assertEqual(spec["status"], "SPECIFIED_NOT_CREATED_OR_ACCEPTED")
        self.assertIn("Voice/sidecars/chatterbox_blackwell_gpu/.venv", spec["must_not_reuse_or_modify"])
        self.assertIsNone(spec["distributions"]["torch"]["version"])
        self.assertIsNone(spec["distributions"]["torchaudio"]["version"])

    def test_exact_text_hashes_are_all_mandatory(self) -> None:
        job = {"schema": "qwen3_tts_original_voice_forge_job_v2", "voice_origin": worker.VOICE_ORIGIN, "identity_basis": worker.IDENTITY_BASIS, "language": "English"}
        for prefix, text in (("design_traits", "Original traits"), ("reference", "Reference words"), ("test", "Test words")):
            job[f"{prefix}_text"] = text
            job[f"{prefix}_text_sha256"] = worker.sha256_text(text)
        worker.validate_job(job)
        for prefix in ("design_traits", "reference", "test"):
            broken = dict(job); broken[f"{prefix}_text_sha256"] = "0" * 64
            with self.subTest(prefix=prefix), self.assertRaisesRegex(worker.R2ForgeError, "hash"):
                worker.validate_job(broken)

    def test_owner_authorization_is_exact_single_use_queue_bound(self) -> None:
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        bundle = {key: value for key, value in {
            "bundle_id": "bundle", "candidate_id": "candidate", "opaque_voice_id": "voice",
            "ai_type": "expert_temp_ai", "single_use_nonce_sha256": "1" * 64,
            "queue_binding_sha256": "2" * 64, "job_sha256": "3" * 64,
            "canonical_profile_sha256": "4" * 64, "canonical_creation_request_sha256": "5" * 64,
            "identity_clearance_manifest_sha256": "6" * 64, "watermark_evidence_manifest_sha256": "7" * 64,
            "evaluation_corpus_sha256": "8" * 64, "voice_design_model_manifest_sha256": "9" * 64,
            "base_model_manifest_sha256": "a" * 64, "environment_spec_sha256": "b" * 64,
        }.items()}
        owner = {"schema": "qwen3_tts_original_voice_forge_owner_authorization_v2", "status": "OWNER_AUTHORIZED_SINGLE_USE", "owner_id": "robert", "single_use": True, "revoked": False, "authorized_scope": "ONE_PRIVATE_QWEN3_TTS_ORIGINAL_VOICE_FORGE_ACCEPTANCE_V2", "authorized_utc": (now - timedelta(minutes=1)).isoformat(), "expires_utc": (now + timedelta(hours=1)).isoformat(), **bundle}
        worker.validate_owner_authorization(owner, bundle)
        owner["queue_binding_sha256"] = "4" * 64
        with self.assertRaisesRegex(worker.R2ForgeError, "queue_binding"):
            worker.validate_owner_authorization(owner, bundle)

    def test_parent_validates_exact_owner_authorization_before_nonce_consumption(self) -> None:
        from datetime import datetime, timedelta, timezone

        with tempfile.TemporaryDirectory() as temp:
            bundle_dir = Path(temp) / "bundle"
            bundle_dir.mkdir()
            bundle = {
                "bundle_id": "bundle_test", "candidate_id": "candidate_test",
                "opaque_voice_id": "voice_test", "ai_type": "expert_temp_ai",
                "single_use_nonce_sha256": "1" * 64,
                "queue_binding_sha256": "2" * 64, "job_sha256": "3" * 64,
                "canonical_profile_sha256": "4" * 64,
                "canonical_creation_request_sha256": "5" * 64,
                "identity_clearance_manifest_sha256": "6" * 64,
                "watermark_evidence_manifest_sha256": "7" * 64,
                "evaluation_corpus_sha256": "8" * 64,
                "voice_design_model_manifest_sha256": "9" * 64,
                "base_model_manifest_sha256": "a" * 64,
                "environment_spec_sha256": "b" * 64,
                "owner_authorization_path": "owner_authorization.json",
            }
            now = datetime.now(timezone.utc)
            owner = {
                "schema": "qwen3_tts_original_voice_forge_owner_authorization_v2",
                "status": "OWNER_AUTHORIZED_SINGLE_USE", "owner_id": "robert",
                "single_use": True, "revoked": False,
                "authorized_scope": "ONE_PRIVATE_QWEN3_TTS_ORIGINAL_VOICE_FORGE_ACCEPTANCE_V2",
                "authorized_utc": (now - timedelta(minutes=1)).isoformat(),
                "expires_utc": (now + timedelta(hours=1)).isoformat(),
                **{key: bundle[key] for key in (
                    "bundle_id", "candidate_id", "opaque_voice_id", "ai_type",
                    "single_use_nonce_sha256", "queue_binding_sha256", "job_sha256",
                    "canonical_profile_sha256", "canonical_creation_request_sha256",
                    "identity_clearance_manifest_sha256", "watermark_evidence_manifest_sha256",
                    "evaluation_corpus_sha256", "voice_design_model_manifest_sha256",
                    "base_model_manifest_sha256", "environment_spec_sha256",
                )},
            }
            owner_path = bundle_dir / "owner_authorization.json"
            write_json(owner_path, owner)
            bundle["owner_authorization_sha256"] = launcher.sha256_file(owner_path)
            declared = {"owner_authorization.json"}
            self.assertEqual(
                launcher.validate_owner_authorization_before_nonce(
                    bundle_dir=bundle_dir, declared=declared, bundle=bundle,
                ),
                owner,
            )
            owner["expires_utc"] = (now - timedelta(seconds=1)).isoformat()
            write_json(owner_path, owner)
            bundle["owner_authorization_sha256"] = launcher.sha256_file(owner_path)
            with self.assertRaisesRegex(launcher.R2LauncherError, "expired"):
                launcher.validate_owner_authorization_before_nonce(
                    bundle_dir=bundle_dir, declared=declared, bundle=bundle,
                )
            source = RUNNER_SOURCE.read_text(encoding="utf-8")
            verification_call = source.index(
                "validate_owner_authorization_before_nonce(",
                source.index("def verify_bundle_envelope"),
            )
            nonce_call = source.index("consume_nonce(bundle, attempt)", source.index("def run"))
            self.assertLess(verification_call, nonce_call)

    def test_bundle_seal_requires_complete_exact_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "a.json").write_text("{}\n"); (root / "extra.bin").write_bytes(b"x")
            seal = {"schema": "qwen3_tts_original_voice_forge_bundle_seal_v2", "files": [{"path": "a.json", "bytes": (root / "a.json").stat().st_size, "sha256": worker.sha256_file(root / "a.json")}]}
            with self.assertRaisesRegex(worker.R2ForgeError, "complete exact inventory"):
                worker._sealed_bundle_files(root, seal)

    def test_runner_exact_python_record_wheel_and_blackwell_static_gates(self) -> None:
        fixture = ExecutionFixture(self)
        with mock.patch.object(launcher, "PROJECT_ROOT", fixture.root):
            worker_path = fixture.root / launcher.WORKER_REL
            worker_path.parent.mkdir(parents=True, exist_ok=True)
            worker_path.write_text("# verified worker\n", encoding="utf-8")
            python = fixture.root / worker.ISOLATED_VENV_REL / "Scripts/python.exe"
            self.assertEqual(
                launcher.validate_ready_environment(fixture.contract, fixture.environment, worker_path),
                python.resolve(),
            )
            arbitrary_record = fixture.root / "evidence/torch.RECORD"
            arbitrary_record.parent.mkdir(parents=True, exist_ok=True)
            arbitrary_record.write_text("fake\n", encoding="utf-8")
            broken = json.loads(json.dumps(fixture.environment))
            broken["distributions"]["torch"]["record_path"] = launcher.relative(arbitrary_record, fixture.root)
            broken["distributions"]["torch"]["record_sha256"] = launcher.sha256_file(arbitrary_record)
            with self.assertRaisesRegex(launcher.R2LauncherError, "outside the isolated environment"):
                launcher.validate_ready_environment(fixture.contract, broken, worker_path)
            broken = json.loads(json.dumps(fixture.environment))
            bad_wheel = fixture.root / worker.WHEEL_EVIDENCE_ROOT_REL / broken["distributions"]["torch"]["wheel_filename"]
            original_wheel = bad_wheel.read_bytes()
            bad_wheel.write_bytes(b"not a wheel archive")
            broken["distributions"]["torch"]["wheel_sha256"] = launcher.sha256_file(bad_wheel)
            with self.assertRaisesRegex(launcher.R2LauncherError, "valid exact archive"):
                launcher.validate_ready_environment(fixture.contract, broken, worker_path)
            bad_wheel.write_bytes(original_wheel)
            broken = json.loads(json.dumps(fixture.environment))
            broken["cuda"]["compute_capability"] = [8, 9]
            with self.assertRaisesRegex(launcher.R2LauncherError, "capability"):
                launcher.validate_ready_environment(fixture.contract, broken, worker_path)

    def test_current_harness_manifest_requires_independent_audit_before_run(self) -> None:
        manifest_path = ROOT / launcher.HARNESS_MANIFEST_REL
        if not manifest_path.exists():
            self.skipTest("manifest is generated after final source hashes")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "IMPLEMENTED_REQUIRES_INDEPENDENT_AUDIT")

    def test_started_or_post_worker_failure_is_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(launcher, "PROJECT_ROOT", Path(temp)):
            attempt = Path(temp) / launcher.OUTPUT_ROOT_REL / "bundle/attempt_01"; attempt.mkdir(parents=True)
            error = RuntimeError("subprocess could not start")
            try:
                raise error
            except RuntimeError as caught:
                launcher.preserve_started_or_post_failure(attempt, caught, "WORKER_PROCESS")
            evidence = json.loads((attempt / "parent_started_or_post_failure_v2.json").read_text())
            self.assertTrue(evidence["worker_start_attempted"])
            self.assertFalse(evidence["clean_worker_exit_and_acceptance_confirmed"])


if __name__ == "__main__":
    unittest.main()
