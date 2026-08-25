from __future__ import annotations

import json
import tempfile
import time
import unittest
import threading
from dataclasses import replace
from pathlib import Path

from .support import generic_voice
from kira_local_voice.backends import MockBackend
from kira_local_voice.backends.base import BackendCapabilities
from kira_local_voice.errors import BackendUnavailableError, ConflictError, ValidationError
from kira_local_voice.output import MAX_OUTPUT_BYTES
from kira_local_voice.models import JobState, SynthesisRequest
from kira_local_voice.service import LocalVoiceService


class ServiceJobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = LocalVoiceService(Path(self.temp.name))
        self.service.register_voice(generic_voice())

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    def test_health_and_capabilities_are_truthful_about_mock(self):
        self.assertTrue(self.service.health()["local_only"])
        self.assertTrue(self.service.health()["mock_backend"])
        caps = self.service.capabilities()
        self.assertFalse(caps["backend"]["voice_cloning"])
        self.assertTrue(caps["backend"]["mock"])

    def test_synthesis_job_produces_contained_output_and_atomic_receipt(self):
        private_text = "A calm local contract test that should not be persisted verbatim."
        submitted = self.service.submit(
            SynthesisRequest(
                text=private_text,
                voice_id="calm-fallback",
                output_name="sample",
                metadata={"private-note": "also do not persist this value"},
            )
        )
        done = self.service.jobs.wait(submitted.job_id)
        self.assertEqual(done.state, JobState.SUCCEEDED)
        output = self.service.outputs_root / done.output_path
        receipt = self.service.receipts_root / done.receipt_path
        self.assertEqual(output.parent, Path(self.temp.name).resolve() / "outputs")
        self.assertEqual(output.read_bytes()[:4], b"RIFF")
        receipt_text = receipt.read_text(encoding="utf-8")
        data = json.loads(receipt_text)
        self.assertEqual(data["state"], "succeeded")
        self.assertTrue(data["backend"]["mock_audio"])
        self.assertEqual(len(data["output"]["sha256"]), 64)
        self.assertEqual(data["request"]["text_characters"], len(private_text))
        self.assertNotIn(private_text, receipt_text)
        self.assertNotIn("also do not persist this value", receipt_text)
        self.assertEqual(list(receipt.parent.glob("*.tmp")), [])

    def test_output_path_traversal_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.service.submit(
                SynthesisRequest(text="hello", voice_id="calm-fallback", output_name="../outside")
            )
        with self.assertRaises(ValidationError):
            LocalVoiceService(Path(r"\\server\share\voice-data"))

    def test_existing_output_is_not_overwritten(self):
        first = self.service.submit(
            SynthesisRequest(text="first", voice_id="calm-fallback", output_name="same-name")
        )
        self.assertEqual(self.service.jobs.wait(first.job_id).state, JobState.SUCCEEDED)
        with self.assertRaises(ValidationError):
            self.service.submit(
                SynthesisRequest(text="second", voice_id="calm-fallback", output_name="same-name")
            )

    def test_inflight_output_name_is_reserved(self):
        self.service.close()
        self.service = LocalVoiceService(
            Path(self.temp.name) / "reservation-root",
            backend=MockBackend(step_delay_seconds=0.03, steps=20),
        )
        self.service.register_voice(generic_voice())
        first = self.service.submit(
            SynthesisRequest(text="first", voice_id="calm-fallback", output_name="reserved-name")
        )
        with self.assertRaises(ConflictError):
            self.service.submit(
                SynthesisRequest(text="second", voice_id="calm-fallback", output_name="reserved-name")
            )
        self.service.cancel_job(first.job_id)
        self.assertEqual(self.service.jobs.wait(first.job_id).state, JobState.CANCELLED)

    def test_request_limits(self):
        bad_requests = [
            SynthesisRequest(text=" ", voice_id="calm-fallback"),
            SynthesisRequest(text="x" * 4001, voice_id="calm-fallback"),
            SynthesisRequest(text="hello", voice_id="calm-fallback", speed=2.1),
            SynthesisRequest(text="hello", voice_id="calm-fallback", speed=float("nan")),
            SynthesisRequest(text="hello", voice_id="calm-fallback", output_name=""),
            SynthesisRequest(text="hello", voice_id="calm-fallback", language="../../bad"),
            SynthesisRequest(text="hello", voice_id="calm-fallback", style="Not Safe"),
            SynthesisRequest(text="hello", voice_id="calm-fallback", metadata=[]),
        ]
        for request in bad_requests:
            with self.subTest(request=request):
                with self.assertRaises(ValidationError):
                    self.service.submit(request)

    def test_expired_consent_blocks_synthesis(self):
        self.service.register_voice(
            replace(
                generic_voice("expired-fallback"),
                consent=replace(
                    generic_voice().consent,
                    recorded_at="1999-01-01T00:00:00Z",
                    expires_at="2000-01-01T00:00:00Z",
                ),
            )
        )
        with self.assertRaises(ValidationError):
            self.service.submit(SynthesisRequest(text="must not run", voice_id="expired-fallback"))

    def test_running_job_can_be_cancelled_and_has_receipt(self):
        self.service.close()
        self.service = LocalVoiceService(
            Path(self.temp.name) / "cancel-root",
            backend=MockBackend(step_delay_seconds=0.04, steps=30),
        )
        self.service.register_voice(generic_voice())
        submitted = self.service.submit(SynthesisRequest(text="cancel me", voice_id="calm-fallback"))
        deadline = time.monotonic() + 1
        while self.service.get_job(submitted.job_id).state is JobState.QUEUED and time.monotonic() < deadline:
            time.sleep(0.005)
        self.service.cancel_job(submitted.job_id)
        done = self.service.jobs.wait(submitted.job_id)
        self.assertEqual(done.state, JobState.CANCELLED)
        self.assertIsNone(done.output_path)
        receipt = self.service.receipts_root / done.receipt_path
        self.assertEqual(json.loads(receipt.read_text(encoding="utf-8"))["state"], "cancelled")
        with self.assertRaises(ConflictError):
            self.service.cancel_job(submitted.job_id)

    def test_backend_failure_becomes_failed_job_with_atomic_receipt(self):
        class FailingBackend(MockBackend):
            def synthesize(self, request, voice, output_path, cancellation):
                del request, voice, output_path, cancellation
                raise RuntimeError("synthetic backend failure for contract test")

        self.service.close()
        self.service = LocalVoiceService(Path(self.temp.name) / "failure-root", backend=FailingBackend())
        self.service.register_voice(generic_voice())
        submitted = self.service.submit(
            SynthesisRequest(text="failure path", voice_id="calm-fallback", output_name="no-output")
        )
        done = self.service.jobs.wait(submitted.job_id)
        self.assertEqual(done.state, JobState.FAILED)
        self.assertIsNone(done.output_path)
        receipt = json.loads((self.service.receipts_root / done.receipt_path).read_text(encoding="utf-8"))
        self.assertEqual(receipt["state"], "failed")
        self.assertEqual(receipt["error"]["code"], "synthesis_failed")
        self.assertFalse((Path(self.temp.name) / "failure-root" / "outputs" / "no-output.wav").exists())

    def test_two_service_instances_share_atomic_reservation(self):
        shared=Path(self.temp.name)/"shared"; self.service.close()
        first=LocalVoiceService(shared,MockBackend(step_delay_seconds=.03,steps=20))
        first.register_voice(generic_voice()); second=LocalVoiceService(shared,MockBackend(step_delay_seconds=.03,steps=20))
        try:
            job=first.submit(SynthesisRequest("first","calm-fallback",output_name="race"))
            with self.assertRaises(ConflictError):
                second.submit(SynthesisRequest("second","calm-fallback",output_name="race"))
            first.cancel_job(job.job_id); self.assertEqual(first.jobs.wait(job.job_id).state,JobState.CANCELLED)
        finally: first.close(); second.close()
        self.service=LocalVoiceService(Path(self.temp.name)/"replacement"); self.service.register_voice(generic_voice())

    def test_receipt_failure_is_terminal_failure_and_releases_reservation(self):
        self.service.jobs._receipt_writer=lambda path,payload: (_ for _ in ()).throw(OSError("private path"))
        job=self.service.submit(SynthesisRequest("receipt failure","calm-fallback",output_name="receipt-fail"))
        done=self.service.jobs.wait(job.job_id); self.assertEqual(done.state,JobState.FAILED)
        self.assertEqual(done.error["code"],"receipt_io_failure"); self.assertIsNone(done.receipt_path)
        self.assertFalse((self.service.reservations_root/"receipt-fail.lock").exists())
        self.assertFalse((self.service.outputs_root/"receipt-fail.wav").exists())

    def test_timeout_and_deactivation_are_enforced_during_execution(self):
        self.service.close(); self.service=LocalVoiceService(Path(self.temp.name)/"timeout",MockBackend(step_delay_seconds=.1,steps=30))
        self.service.register_voice(generic_voice())
        job=self.service.submit(SynthesisRequest("timeout","calm-fallback"),timeout_seconds=1)
        self.assertEqual(self.service.jobs.wait(job.job_id,3).state,JobState.CANCELLED)
        self.service.registry.deactivate("calm-fallback",authority="owner",reason="stop")
        with self.assertRaises(ValidationError): self.service.submit(SynthesisRequest("blocked","calm-fallback"))

    def test_backend_metadata_mismatch_cannot_succeed(self):
        class LyingBackend(MockBackend):
            def synthesize(self,*args,**kwargs):
                result=super().synthesize(*args,**kwargs)
                return replace(result,sample_rate_hz=16000)
        self.service.close(); self.service=LocalVoiceService(Path(self.temp.name)/"lying",LyingBackend())
        self.service.register_voice(generic_voice()); job=self.service.submit(SynthesisRequest("lie","calm-fallback"))
        self.assertEqual(self.service.jobs.wait(job.job_id).state,JobState.FAILED)

    def test_nonlocal_or_telemetry_backend_is_rejected_before_execution(self):
        class NonLocalBackend(MockBackend):
            called=False
            def capabilities(self):
                return replace(super().capabilities(),offline=False,network_access="internet",telemetry="enabled")
            def synthesize(self,*args,**kwargs):
                self.called=True
                return super().synthesize(*args,**kwargs)
        backend=NonLocalBackend(); self.service.close()
        self.service=LocalVoiceService(Path(self.temp.name)/"nonlocal",backend)
        self.service.register_voice(generic_voice())
        with self.assertRaises(BackendUnavailableError):
            self.service.submit(SynthesisRequest("must not execute","calm-fallback"))
        self.assertFalse(backend.called)

    def test_backend_cannot_omit_exact_voice_provenance(self):
        class MissingVoiceBackend(MockBackend):
            def synthesize(self,*args,**kwargs):
                return replace(super().synthesize(*args,**kwargs),voice_id="none")
        self.service.close(); self.service=LocalVoiceService(Path(self.temp.name)/"no-voice",MissingVoiceBackend())
        self.service.register_voice(generic_voice())
        job=self.service.submit(SynthesisRequest("voice truth","calm-fallback"))
        self.assertEqual(self.service.jobs.wait(job.job_id).state,JobState.FAILED)

    def test_quota_reserves_queued_and_staging_capacity_cross_request(self):
        self.service.close(); self.service=LocalVoiceService(
            Path(self.temp.name)/"quota",MockBackend(step_delay_seconds=.03,steps=30),
            max_storage_bytes=MAX_OUTPUT_BYTES,per_job_reservation_bytes=MAX_OUTPUT_BYTES)
        self.service.register_voice(generic_voice())
        first=self.service.submit(SynthesisRequest("first","calm-fallback",output_name="quota-one"))
        with self.assertRaises(ValidationError):
            self.service.submit(SynthesisRequest("second","calm-fallback",output_name="quota-two"))
        self.service.cancel_job(first.job_id)
        self.assertEqual(self.service.jobs.wait(first.job_id,3).state,JobState.CANCELLED)

    def test_close_terminalizes_queued_jobs_and_releases_every_reservation(self):
        self.service.close(); self.service=LocalVoiceService(
            Path(self.temp.name)/"close-queued",MockBackend(step_delay_seconds=.03,steps=40))
        self.service.register_voice(generic_voice())
        first=self.service.submit(SynthesisRequest("first","calm-fallback",output_name="close-one"))
        second=self.service.submit(SynthesisRequest("second","calm-fallback",output_name="close-two"))
        self.assertTrue(self.service.close())
        self.assertIn(self.service.get_job(first.job_id).state,{JobState.CANCELLED,JobState.FAILED})
        self.assertEqual(self.service.get_job(second.job_id).state,JobState.CANCELLED)
        self.assertEqual(list(self.service.reservations_root.glob("*.lock")),[])

    def test_final_authorization_and_publication_exclude_deactivation(self):
        self.service.close(); self.service=LocalVoiceService(
            Path(self.temp.name)/"publish-guard",MockBackend(step_delay_seconds=.01,steps=2))
        self.service.register_voice(generic_voice())
        entered=threading.Event(); release=threading.Event()
        original=self.service._authorize_and_publish
        def held_publisher(*args):
            with self.service.registry.mutation_guard():
                self.service._authorize_at_execution(args[0]); entered.set(); release.wait(2)
                from kira_local_voice.output import publish_no_replace
                return publish_no_replace(args[1],args[2],args[3])
        self.service.jobs._publisher=held_publisher
        job=self.service.submit(SynthesisRequest("atomic","calm-fallback",output_name="atomic"))
        self.assertTrue(entered.wait(2))
        deactivated=threading.Event()
        thread=threading.Thread(target=lambda:(self.service.registry.deactivate(
            "calm-fallback",authority="owner",reason="after publication"),deactivated.set()))
        thread.start(); time.sleep(.05); self.assertFalse(deactivated.is_set())
        release.set(); thread.join(2); self.assertTrue(deactivated.is_set())
        self.assertEqual(self.service.jobs.wait(job.job_id).state,JobState.SUCCEEDED)


if __name__ == "__main__":
    unittest.main()
