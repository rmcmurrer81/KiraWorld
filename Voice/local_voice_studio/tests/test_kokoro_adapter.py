from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import threading
import unittest
import wave
from pathlib import Path

from .support import ROOT
from kira_local_voice.backends import (CancellationToken,KokoroConfig,KokoroSubprocessBackend,
                                       builtin_kokoro_profiles)
from kira_local_voice.backends.kokoro_subprocess import (
    AUDITION_EVIDENCE_REVISION,
    EXPECTED_RUNTIME_LOCK_SHA256,
    EXPECTED_WORKER_SHA256,
    MODEL_FILES,
    MODEL_REPO,
    MODEL_REVISION,
    REVIEWED_ISOLATION_PROVIDER_IDS,
    _bounded_process,
    _parse_success_response,
)
from kira_local_voice.errors import BackendUnavailableError,CancelledError
from kira_local_voice.models import AuditionStatus, SynthesisRequest


class KokoroAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cache = self.root / "cache"
        self.cache.mkdir()
        self.staging = self.root / "staging"
        self.staging.mkdir()
        self.worker = ROOT / "src" / "kira_local_voice" / "backends" / "kokoro_worker.py"
        self.lock = ROOT / "requirements-kokoro.lock.json"
        self.config = KokoroConfig(
            Path(sys.executable),
            self.cache,
            self.staging,
            self.worker,
            self.lock,
            hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_bundle_and_marker_are_truthfully_unavailable(self):
        caps = KokoroSubprocessBackend(self.config).capabilities()
        self.assertFalse(caps.ready)
        self.assertFalse(caps.offline)
        self.assertFalse(caps.mock)
        self.assertEqual(caps.network_access, "not_os_enforced")
        self.assertNotEqual(caps.telemetry, "none")
        self.assertEqual(caps.voice_ids,("af_heart","am_fenrir"))
        self.assertEqual(caps.provenance_scope,"two_voice_runtime_bundle_only")
        self.assertEqual(caps.audition_evidence_revision,AUDITION_EVIDENCE_REVISION)
        self.assertFalse(caps.audition_evidence_grants_runtime_access)

    def test_readme_files_and_self_asserted_marker_cannot_forge_readiness(self):
        readme = ROOT / "README.md"
        marker = self.cache / "kira_kokoro_ready.json"
        marker.write_text(
            json.dumps(
                {
                    "schema": "kira.kokoro.ready.v2",
                    "model_repo": MODEL_REPO,
                    "model_revision": MODEL_REVISION,
                    "provenance_scope":"two_voice_runtime_bundle_only",
                    "audition_evidence_revision":AUDITION_EVIDENCE_REVISION,
                    "audition_evidence_grants_runtime_access":False,
                    "route": "KModel+misaki.espeak.EspeakG2P",
                    "voices": ["af_heart", "am_fenrir"],
                    "python_sha256": hashlib.sha256(readme.read_bytes()).hexdigest(),
                    "worker_sha256": hashlib.sha256(readme.read_bytes()).hexdigest(),
                    "runtime_lock_sha256": hashlib.sha256(readme.read_bytes()).hexdigest(),
                    "runtime_packages": {},
                    "bundle_files": MODEL_FILES,
                }
            ),
            encoding="utf-8",
        )
        forged = KokoroConfig(
            readme,
            self.cache,
            self.staging,
            readme,
            readme,
            hashlib.sha256(readme.read_bytes()).hexdigest(),
            ready_marker=marker,
        )
        caps = KokoroSubprocessBackend(forged).capabilities()
        self.assertFalse(caps.ready)
        self.assertIn("executable", caps.unavailable_reason.lower())

    def test_release_worker_and_runtime_lock_have_exact_pinned_hashes(self):
        self.assertEqual(hashlib.sha256(self.worker.read_bytes()).hexdigest(), EXPECTED_WORKER_SHA256)
        self.assertEqual(hashlib.sha256(self.lock.read_bytes()).hexdigest(), EXPECTED_RUNTIME_LOCK_SHA256)

    def test_strict_response_requires_finite_complete_exact_provenance(self):
        output = self.staging / "strict.wav.partial"
        with wave.open(str(output), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24_000)
            wav.writeframes(b"\0\0" * 2_400)
        request = SynthesisRequest("hello", "af_heart")
        base = {
            "schema": "kira.kokoro.result.v2",
            "ok": True,
            "format": "wav",
            "sample_rate_hz": 24_000,
            "duration_seconds": 0.1,
            "output_bytes": output.stat().st_size,
            "backend_name": "kokoro-direct-subprocess",
            "backend_version": "2.0",
            "model_source": MODEL_REPO,
            "model_revision": MODEL_REVISION,
            "voice_id": "af_heart",
            "license_id": "Apache-2.0",
            "offline": True,
            "provenance_scope":"two_voice_runtime_bundle_only",
        }
        result = _parse_success_response(json.dumps(base).encode(), request=request, output_path=output)
        self.assertEqual(result.voice_id, "af_heart")
        self.assertEqual(result.model_revision, MODEL_REVISION)
        for mutation in (
            {key: value for key, value in base.items() if key != "model_revision"},
            dict(base, model_revision="wrong"),
            dict(base, voice_id="none"),
        ):
            with self.subTest(mutation=mutation):
                with self.assertRaises(BackendUnavailableError):
                    _parse_success_response(json.dumps(mutation).encode(), request=request, output_path=output)
        with self.assertRaises(BackendUnavailableError):
            _parse_success_response(
                json.dumps(dict(base, duration_seconds=float("nan"))).encode(),
                request=request,
                output_path=output,
            )
        duplicate=json.dumps(base).replace('"voice_id": "af_heart"',
            '"voice_id": "af_heart", "voice_id": "af_heart"')
        with self.assertRaises(BackendUnavailableError):
            _parse_success_response(duplicate.encode(),request=request,output_path=output)

    def test_profiles_are_owner_audition_approved_without_identity_claim(self):
        profiles = builtin_kokoro_profiles()
        self.assertEqual({profile.voice_id for profile in profiles}, {"af_heart", "am_fenrir"})
        self.assertTrue(all(profile.audition_status is AuditionStatus.OWNER_APPROVED for profile in profiles))
        self.assertTrue(all(not profile.reference_hashes for profile in profiles))
        self.assertTrue(all("audition approved" in profile.description for profile in profiles))
        self.assertTrue(all("requires user audition" not in profile.description for profile in profiles))

    def test_unc_configuration_is_rejected_and_no_provider_is_reviewed(self):
        unc = KokoroConfig(Path(r"\\server\share\python.exe"), self.cache, self.staging)
        caps = KokoroSubprocessBackend(unc).capabilities()
        self.assertFalse(caps.ready)
        self.assertIn("UNC", caps.unavailable_reason)
        self.assertEqual(REVIEWED_ISOLATION_PROVIDER_IDS, frozenset())

    def test_process_seam_enforces_stream_bounds_and_cancellation(self):
        output=self.staging/"unused.partial"
        with self.assertRaises(BackendUnavailableError):
            _bounded_process([sys.executable,"-I","-c","print('x'*1000)"],b"",dict(os.environ),
                CancellationToken(threading.Event()),3,32,32,output,1024)
        cancelled=threading.Event(); cancelled.set()
        with self.assertRaises(CancelledError):
            _bounded_process([sys.executable,"-I","-c","import time; time.sleep(5)"],b"",dict(os.environ),
                CancellationToken(cancelled),3,32,32,output,1024)


if __name__ == "__main__":
    unittest.main()
