from __future__ import annotations

import json
import tempfile
import unittest
import wave
from dataclasses import replace
from pathlib import Path

from .support import generic_voice
from .test_voice_design import brief
from kira_local_voice.backends.base import BackendCapabilities
from kira_local_voice.candidate_audio_queue import CandidateAudioQueue
from kira_local_voice.errors import ValidationError
from kira_local_voice.models import BackendResult
from kira_local_voice.registry import VoiceRegistry
from kira_local_voice.runtime_resolver import ExactRuntimeVoiceResolver
from kira_local_voice.service import LocalVoiceService
from kira_local_voice.voice_design import VoiceDesignEngine, VoiceDesignStore


F3FF = "f3ff3571791e39611d31c381e3a41a3af07b4987"
FBBA = "fbba31e67ad83eb66394c926627e99d35abeb087"


class ExactAuditionBackend:
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            name="exact-audition-test",
            version="1",
            ready=True,
            formats=("wav",),
            languages=("en-US",),
            voice_cloning=False,
            voice_design=False,
            mock=False,
            offline=True,
            network_access="none",
            telemetry="none",
            model_source="hexgrad/Kokoro-82M",
            model_revision=F3FF,
            license_id="Apache-2.0",
            voice_ids=("af_heart",),
            provenance_scope="two_voice_generic_bootstrap_only",
            audition_evidence_revision=F3FF,
            audition_evidence_grants_runtime_access=True,
        )

    def synthesize(self, request, voice, output_path, cancellation) -> BackendResult:
        del voice
        cancellation.raise_if_cancelled()
        frames = 2400
        with wave.open(str(output_path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(24000)
            audio.writeframes(b"\x00\x00" * frames)
        caps = self.capabilities()
        return BackendResult(
            format="wav",
            sample_rate_hz=24000,
            duration_seconds=frames / 24000,
            backend_name=caps.name,
            backend_version=caps.version,
            mock_audio=False,
            model_source=caps.model_source,
            model_revision=caps.model_revision,
            voice_id=request.voice_id,
            license_id=caps.license_id,
            offline=True,
            provenance_scope=caps.provenance_scope,
        )


class NoSubmitRuntime:
    def __init__(self, registry: VoiceRegistry):
        self.registry = registry
        self.submit_calls = 0

    def capabilities(self) -> dict:
        return {
            "schema": "kira.local-voice.capabilities.v1",
            "local_only": False,
            "backend": {
                "name": "blocked-current-runtime",
                "version": "1",
                "ready": False,
                "formats": ["wav"],
                "languages": ["en-US"],
                "voice_cloning": False,
                "voice_design": False,
                "mock": False,
                "offline": False,
                "network_access": "not_os_enforced",
                "telemetry": "disabled_by_environment_only",
                "model_source": "hexgrad/Kokoro-82M",
                "model_revision": FBBA,
                "license_id": "Apache-2.0",
                "voice_ids": ["af_heart", "am_fenrir"],
                "provenance_scope": "two_voice_runtime_bundle_only",
                "audition_evidence_revision": F3FF,
                "audition_evidence_grants_runtime_access": False,
                "unavailable_reason": "test blocked",
            },
        }

    def submit(self, *args, **kwargs):
        self.submit_calls += 1
        raise AssertionError("blocked candidate must never be submitted")


class CandidateAudioQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.design_registry = VoiceRegistry(self.root / "design-voices")
        self.engine = VoiceDesignEngine(VoiceDesignStore(self.root / "design"), self.design_registry)
        self.bundle = self.engine.create_bundle(brief(
            role="Counselor",
            traits=("calm", "reassuring", "patient"),
            candidate_count=2,
        ))

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_ready_candidate_writes_sample_and_service_receipt_digests_without_activation(self):
        service = LocalVoiceService(self.root / "service", ExactAuditionBackend())
        try:
            service.register_voice(replace(generic_voice("af_heart"), language="en-US"))
            resolver = ExactRuntimeVoiceResolver(self.engine, service)
            queue = CandidateAudioQueue(self.root / "queue", self.engine, resolver, service)
            record = queue.run_bundle(self.bundle["bundle_id"])
            by_candidate = {item["candidate_id"]: item for item in record["results"]}
            heart = next(item for item in self.bundle["candidates"] if item["backend_voice_id"] == "af_heart")
            heart_result = by_candidate[heart["candidate_id"]]
            self.assertEqual(heart_result["status"], "succeeded")
            self.assertEqual(len(heart_result["sample_sha256"]), 64)
            self.assertEqual(len(heart_result["service_receipt_sha256"]), 64)
            self.assertTrue((service.outputs_root / heart_result["sample_path"]).is_file())
            queue_receipt = self.root / "queue/receipts" / f"{record['queue_id']}.json"
            saved = json.loads(queue_receipt.read_text(encoding="utf-8"))
            self.assertEqual(saved, record)
            self.assertEqual(queue.get_receipt(record["queue_id"]), record)
            self.assertFalse(record["approval_performed"])
            self.assertFalse(record["selection_performed"])
            self.assertFalse(record["binding_performed"])
            self.assertFalse(record["activation_performed"])
            self.assertIsNone(self.engine.current_binding(self.bundle["brief"]["subject_id"]))
        finally:
            service.close()

    def test_current_runtime_mismatch_records_blockers_and_never_submits(self):
        self.design_registry.register(replace(generic_voice("af_heart"), language="en-US"))
        service = NoSubmitRuntime(self.design_registry)
        resolver = ExactRuntimeVoiceResolver(self.engine, service)
        queue = CandidateAudioQueue(self.root / "blocked-queue", self.engine, resolver, service)
        record = queue.run_bundle(self.bundle["bundle_id"])
        self.assertEqual(service.submit_calls, 0)
        self.assertTrue(all(item["status"] == "blocked_before_submission" for item in record["results"]))
        self.assertTrue(all(item["sample_sha256"] is None for item in record["results"]))
        self.assertFalse(record["all_samples_ready"])
        self.assertFalse(record["activation_performed"])

    def test_unc_and_reparse_ancestor_queue_roots_are_rejected(self):
        service = NoSubmitRuntime(self.design_registry)
        resolver = ExactRuntimeVoiceResolver(self.engine, service)
        with self.assertRaisesRegex(ValidationError, "non-UNC"):
            CandidateAudioQueue(Path(r"\\server\share\voice-queue"), self.engine, resolver, service)

        target = self.root / "real-parent"
        target.mkdir()
        linked = self.root / "linked-parent"
        try:
            linked.symlink_to(target, target_is_directory=True)
        except OSError:
            return
        with self.assertRaisesRegex(ValidationError, "link, junction, or reparse"):
            CandidateAudioQueue(linked / "queue", self.engine, resolver, service)

    def test_receipt_reader_rejects_tampering_and_duplicate_keys(self):
        self.design_registry.register(replace(generic_voice("af_heart"), language="en-US"))
        service = NoSubmitRuntime(self.design_registry)
        resolver = ExactRuntimeVoiceResolver(self.engine, service)
        queue = CandidateAudioQueue(self.root / "verified-queue", self.engine, resolver, service)
        record = queue.run_bundle(self.bundle["bundle_id"])
        receipt = queue.receipt_root / f"{record['queue_id']}.json"
        value = json.loads(receipt.read_text(encoding="utf-8"))
        value["activation_performed"] = True
        receipt.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "digest"):
            queue.get_receipt(record["queue_id"])

        duplicate_id = "cq-duplicate-test"
        duplicate = queue.receipt_root / f"{duplicate_id}.json"
        duplicate.write_text(
            '{"schema":"kira.local-voice.candidate-audio-queue.v1",'
            f'"queue_id":"{duplicate_id}","queue_id":"{duplicate_id}"}}',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValidationError, "duplicate queue receipt key"):
            queue.get_receipt(duplicate_id)


if __name__ == "__main__":
    unittest.main()
