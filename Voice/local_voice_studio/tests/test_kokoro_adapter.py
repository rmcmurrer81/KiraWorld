from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import threading
import unittest
import wave
import base64
from pathlib import Path
from unittest.mock import patch

from .support import ROOT
from kira_local_voice.backends import (CancellationToken,KokoroConfig,KokoroSubprocessBackend,
                                       MxcIsolationConfig,MxcIsolationProvider,
                                       builtin_kokoro_profiles)
from kira_local_voice.backends import kokoro_subprocess as kokoro_module
from kira_local_voice.backends.kokoro_subprocess import (
    AUDITION_EVIDENCE_REVISION,
    EXPECTED_RUNTIME_LOCK_SHA256,
    EXPECTED_RUNTIME_BRIDGE_SHA256,
    EXPECTED_BASE_RUNTIME_TREE,
    EXPECTED_RUNTIME_TREE,
    EXPECTED_WORKER_SHA256,
    IMPLEMENTED_ISOLATION_PROVIDER_IDS,
    MXC_PROVIDER_ID,
    MODEL_FILES,
    MODEL_REPO,
    MODEL_REVISION,
    REVIEWED_ISOLATION_PROVIDER_IDS,
    REVIEWED_PYTHON_EXECUTABLE_SHA256,
    PROVENANCE_SCOPE,
    ProcessResult,
    _bounded_process,
    _parse_success_response,
    _release_provider_matches,
    _runtime_tree_attestation,
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
        self.assertEqual(caps.provenance_scope,PROVENANCE_SCOPE)
        self.assertEqual(caps.audition_evidence_revision,AUDITION_EVIDENCE_REVISION)
        self.assertTrue(caps.audition_evidence_grants_runtime_access)

    def test_readme_files_and_self_asserted_marker_cannot_forge_readiness(self):
        readme = ROOT / "README.md"
        marker = self.cache / "kira_kokoro_ready.json"
        marker.write_text(
            json.dumps(
                {
                    "schema": "kira.kokoro.ready.v3",
                    "model_repo": MODEL_REPO,
                    "model_revision": MODEL_REVISION,
                    "provenance_scope":PROVENANCE_SCOPE,
                    "audition_evidence_revision":AUDITION_EVIDENCE_REVISION,
                    "audition_evidence_grants_runtime_access":True,
                    "route": "KModel+misaki.espeak.EspeakG2P",
                    "voices": ["af_heart", "am_fenrir"],
                    "python_sha256": hashlib.sha256(readme.read_bytes()).hexdigest(),
                    "worker_sha256": hashlib.sha256(readme.read_bytes()).hexdigest(),
                    "runtime_lock_sha256": hashlib.sha256(readme.read_bytes()).hexdigest(),
                    "runtime_bridge_sha256": hashlib.sha256(readme.read_bytes()).hexdigest(),
                    "runtime_packages": {},
                    "runtime_tree": EXPECTED_RUNTIME_TREE,
                    "base_runtime_tree": EXPECTED_BASE_RUNTIME_TREE,
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
        bridge=ROOT/"evidence"/"kokoro_starter_runtime_bridge_v1.json"
        self.assertEqual(hashlib.sha256(bridge.read_bytes()).hexdigest(),EXPECTED_RUNTIME_BRIDGE_SHA256)
        lock = json.loads(self.lock.read_text(encoding="utf-8"))
        self.assertEqual(lock["runtime_tree"], EXPECTED_RUNTIME_TREE)
        self.assertEqual(lock["base_runtime_tree"], EXPECTED_BASE_RUNTIME_TREE)
        self.assertEqual(
            lock["reviewed_python_executable_sha256"],
            sorted(REVIEWED_PYTHON_EXECUTABLE_SHA256),
        )

    def test_tampered_runtime_bridge_fails_closed_before_runtime_use(self):
        bridge = ROOT / "evidence" / "kokoro_starter_runtime_bridge_v1.json"
        tampered = self.root / "tampered-runtime-bridge.json"
        document = json.loads(bridge.read_text(encoding="utf-8"))
        document["activation_performed"] = True
        tampered.write_text(json.dumps(document), encoding="utf-8")
        config = KokoroConfig(
            python_executable=self.config.python_executable,
            cache_root=self.cache,
            staging_root=self.staging,
            worker_script=self.worker,
            runtime_lock=self.lock,
            python_sha256=self.config.python_sha256,
            runtime_bridge=tampered,
        )
        with patch.object(
            kokoro_module,
            "REVIEWED_PYTHON_EXECUTABLE_SHA256",
            frozenset({self.config.python_sha256}),
        ):
            caps = KokoroSubprocessBackend(config).capabilities()
        self.assertFalse(caps.ready)
        self.assertIn("bridge", caps.unavailable_reason.lower())

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
            "provenance_scope":PROVENANCE_SCOPE,
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

        with wave.open(str(output), "wb") as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(24_000)
            wav.writeframes(b"\0\0\0\0" * 2_400)
        with self.assertRaises(BackendUnavailableError):
            _parse_success_response(
                json.dumps(dict(base, output_bytes=output.stat().st_size)).encode(),
                request=request,
                output_path=output,
            )

        with wave.open(str(output), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24_000)
            wav.writeframes(b"\0\0" * 2_400)
        with self.assertRaises(BackendUnavailableError):
            _parse_success_response(
                json.dumps(
                    dict(base, duration_seconds=0.2, output_bytes=output.stat().st_size)
                ).encode(),
                request=request,
                output_path=output,
            )

    def test_profiles_are_owner_audition_approved_without_identity_claim(self):
        profiles = builtin_kokoro_profiles()
        self.assertEqual({profile.voice_id for profile in profiles}, {"af_heart", "am_fenrir"})
        self.assertTrue(all(profile.audition_status is AuditionStatus.OWNER_APPROVED for profile in profiles))
        self.assertTrue(all(not profile.reference_hashes for profile in profiles))
        self.assertTrue(all("audition approved" in profile.description for profile in profiles))
        self.assertTrue(all("requires user audition" not in profile.description for profile in profiles))

    def test_unc_configuration_is_rejected_and_no_provider_is_release_reviewed(self):
        unc = KokoroConfig(Path(r"\\server\share\python.exe"), self.cache, self.staging)
        caps = KokoroSubprocessBackend(unc).capabilities()
        self.assertFalse(caps.ready)
        self.assertIn("UNC", caps.unavailable_reason)
        self.assertEqual(IMPLEMENTED_ISOLATION_PROVIDER_IDS, frozenset({MXC_PROVIDER_ID}))
        self.assertEqual(REVIEWED_ISOLATION_PROVIDER_IDS, frozenset())

    def test_mxc_provider_requires_pinned_executor_and_builds_deny_network_policy(self):
        readonly=self.root/"readonly"; readonly.mkdir()
        executor=readonly/"wxc-exec.exe"; executor.write_bytes(b"MZ"+b"x"*128)
        python=readonly/"python.exe"; python.write_bytes(b"MZ"+b"p"*64)
        worker=readonly/"worker.py"; worker.write_text("# worker",encoding="utf-8")
        bundle=readonly/"sealed_bundle"; bundle.mkdir()
        executor_hash=hashlib.sha256(executor.read_bytes()).hexdigest()
        calls=[]

        def fake_runner(command,request,env,token,timeout,stdout_limit,stderr_limit,
                        output_path,output_limit):
            calls.append((list(command),request,dict(env),output_path))
            if command[-1]=="--probe":
                return ProcessResult(0,json.dumps({
                    "tier":"base-container","needsDaclAugmentation":False,"warnings":[],
                    "probes":{"baseContainerApiPresent":True,"bfscfgPresent":False,
                              "bfsCompiledIn":False},
                },separators=(",",":")).encode(),b"")
            return ProcessResult(0,b"worker-result" if request else b"",b"")

        config=MxcIsolationConfig(executor,executor_hash,self.staging,(readonly,))
        hostile_environment = {
            "LOCALAPPDATA": "attacker-local-app-data",
            "PATH": "attacker-path",
            "SYSTEMROOT": "attacker-system-root",
            "WINDIR": "attacker-windir",
            "TEMP": "attacker-temp",
            "TMP": "attacker-tmp",
        }
        with (
            patch.dict(os.environ, hostile_environment, clear=False),
            patch.object(
                kokoro_module,
                "REVIEWED_MXC_EXECUTABLE_SHA256",
                frozenset({executor_hash}),
            ),
        ):
            provider=MxcIsolationProvider(config,runner=fake_runner)
            attestation=provider.attest()
            self.assertFalse(attestation.process_tree_contained)
            self.assertFalse(attestation.network_denied_by_os)
            self.assertIn("hostile isolation canaries", attestation.reason)
            self.assertFalse(_release_provider_matches(provider, self.config, bundle))
        for _, _, environment, _ in calls:
            self.assertEqual(
                set(environment),
                {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"},
            )
            self.assertEqual(environment["SYSTEMROOT"], environment["WINDIR"])
            self.assertEqual(
                Path(environment["PATH"]),
                Path(environment["SYSTEMROOT"]) / "System32",
            )
            self.assertEqual(Path(environment["TEMP"]), self.staging.resolve())
            self.assertEqual(environment["TEMP"], environment["TMP"])
            self.assertNotIn("LOCALAPPDATA", environment)
            self.assertNotIn("attacker", "\n".join(environment.values()))
        command=next(item[0] for item in reversed(calls) if "--config-base64" in item[0])
        self.assertEqual(command[1],"--config-base64")
        policy=json.loads(base64.b64decode(command[2]))
        self.assertEqual(policy["containment"],"processcontainer")
        self.assertEqual(policy["network"],{
            "defaultPolicy":"block","enforcementMode":"capabilities",
            "allowedHosts":[],"blockedHosts":[],"allowLocalNetwork":False,
        })
        self.assertEqual(policy["processContainer"]["capabilities"],[])
        self.assertFalse(policy["fallback"]["allowDaclMutation"])
        self.assertEqual(policy["filesystem"]["readwritePaths"],[str(self.staging.resolve())])
        self.assertNotIn(str(self.staging.resolve()),policy["filesystem"]["readonlyPaths"])

    def test_worker_environment_does_not_inherit_user_controlled_paths(self):
        captured = {}

        class CaptureProvider:
            provider_id = "test-only-capture-provider"

            def run(
                self,
                command,
                request,
                env,
                token,
                timeout,
                stdout_limit,
                stderr_limit,
                output_path,
                output_limit,
            ):
                del command, request, token, timeout, stdout_limit, stderr_limit
                del output_path, output_limit
                captured.update(env)
                return ProcessResult(1, b"", b"")

        config = KokoroConfig(
            self.config.python_executable,
            self.cache,
            self.staging,
            self.worker,
            self.lock,
            self.config.python_sha256,
            base_runtime_root=Path(sys.base_prefix),
        )
        backend = KokoroSubprocessBackend(config, CaptureProvider())
        request = SynthesisRequest("Environment isolation test.", "af_heart")
        hostile_environment = {
            "HOME": "attacker-home",
            "LOCALAPPDATA": "attacker-local-app-data",
            "PATH": "attacker-path",
            "SYSTEMROOT": "attacker-system-root",
            "WINDIR": "attacker-windir",
            "TEMP": "attacker-temp",
            "TMP": "attacker-tmp",
        }
        with (
            patch.dict(os.environ, hostile_environment, clear=False),
            patch.object(backend, "_readiness", return_value=(True, None)),
            self.assertRaises(BackendUnavailableError),
        ):
            backend.synthesize(
                request,
                builtin_kokoro_profiles()[0],
                self.staging / "environment.partial",
                CancellationToken(threading.Event()),
            )
        self.assertEqual(
            set(captured),
            {
                "SYSTEMROOT",
                "WINDIR",
                "TEMP",
                "TMP",
                "PATH",
                "HF_HUB_OFFLINE",
                "TRANSFORMERS_OFFLINE",
                "HF_HUB_DISABLE_TELEMETRY",
                "DO_NOT_TRACK",
                "PYTHONNOUSERSITE",
                "PYTHONDONTWRITEBYTECODE",
                "CUDA_CACHE_DISABLE",
            },
        )
        self.assertEqual(captured["SYSTEMROOT"], captured["WINDIR"])
        self.assertEqual(Path(captured["TEMP"]), self.staging.resolve())
        self.assertEqual(captured["TEMP"], captured["TMP"])
        path_entries = captured["PATH"].split(os.pathsep)
        self.assertEqual(
            Path(path_entries[0]), self.config.python_executable.resolve().parent
        )
        self.assertEqual(
            Path(path_entries[1]), Path(captured["SYSTEMROOT"]) / "System32"
        )
        self.assertNotIn("HOME", captured)
        self.assertNotIn("LOCALAPPDATA", captured)
        self.assertNotIn("attacker", "\n".join(captured.values()))

    def test_runtime_tree_attestation_detects_added_or_modified_code(self):
        runtime = self.root / "runtime-tree"
        package = runtime / "Lib" / "site-packages" / "example"
        package.mkdir(parents=True)
        module = package / "module.py"
        module.write_text("VALUE = 1\n", encoding="utf-8")
        first = _runtime_tree_attestation(runtime)
        self.assertEqual(first["file_count"], 1)
        self.assertEqual(first["total_bytes"], module.stat().st_size)
        module.write_text("VALUE = 2\n", encoding="utf-8")
        changed = _runtime_tree_attestation(runtime)
        self.assertNotEqual(changed["tree_sha256"], first["tree_sha256"])
        (package / "sitecustomize.py").write_text("raise SystemExit\n", encoding="utf-8")
        added = _runtime_tree_attestation(runtime)
        self.assertEqual(added["file_count"], 2)
        self.assertNotEqual(added["tree_sha256"], changed["tree_sha256"])

    def test_self_asserted_provider_id_and_injected_runner_are_not_release_trust(self):
        bundle = self.cache / "sealed_bundle"
        bundle.mkdir()

        class SelfAssertedProvider:
            provider_id = MXC_PROVIDER_ID

            def attest(self):
                return kokoro_module.IsolationAttestation(
                    MXC_PROVIDER_ID, True, True, True, "self asserted"
                )

        self.assertFalse(
            _release_provider_matches(SelfAssertedProvider(), self.config, bundle)
        )

        executor = self.root / "wxc-exec.exe"
        executor.write_bytes(b"MZ" + b"x" * 128)
        executor_hash = hashlib.sha256(executor.read_bytes()).hexdigest()
        injected = MxcIsolationProvider(
            MxcIsolationConfig(executor, executor_hash, self.staging, (self.root,)),
            runner=lambda *_args, **_kwargs: ProcessResult(0, b"", b""),
        )
        with (
            patch.object(kokoro_module, "REVIEWED_ISOLATION_PROVIDER_IDS", frozenset({MXC_PROVIDER_ID})),
            patch.object(kokoro_module, "REVIEWED_MXC_EXECUTABLE_SHA256", frozenset({executor_hash})),
        ):
            self.assertFalse(_release_provider_matches(injected, self.config, bundle))

    def test_direct_mxc_run_cannot_bypass_release_review(self):
        readonly = self.root / "readonly-direct-run"
        readonly.mkdir()
        executor = readonly / "wxc-exec.exe"
        executor.write_bytes(b"MZ" + b"x" * 128)
        executor_hash = hashlib.sha256(executor.read_bytes()).hexdigest()
        output = self.staging / "direct-run.partial"
        runner_called = False

        def injected_runner(*_args, **_kwargs):
            nonlocal runner_called
            runner_called = True
            return ProcessResult(0, b"", b"")

        provider = MxcIsolationProvider(
            MxcIsolationConfig(executor, executor_hash, self.staging, (readonly,)),
            runner=injected_runner,
        )
        with (
            patch.object(
                provider,
                "attest",
                return_value=kokoro_module.IsolationAttestation(
                    MXC_PROVIDER_ID, True, True, True, "future canaries passed"
                ),
            ),
            patch.object(
                kokoro_module,
                "REVIEWED_ISOLATION_PROVIDER_IDS",
                frozenset({MXC_PROVIDER_ID}),
            ),
            self.assertRaisesRegex(BackendUnavailableError, "not release reviewed"),
        ):
            provider.run(
                [str(executor)],
                b"",
                {},
                CancellationToken(threading.Event()),
                1.0,
                32,
                32,
                output,
                1024,
            )
        self.assertFalse(runner_called)
        self.assertFalse(output.exists())

    def test_mxc_provider_fails_closed_when_launch_canary_fails(self):
        readonly=self.root/"readonly"; readonly.mkdir()
        executor=readonly/"wxc-exec.exe"; executor.write_bytes(b"MZ"+b"x"*128)
        executor_hash=hashlib.sha256(executor.read_bytes()).hexdigest()

        def failing_canary(command,request,env,token,timeout,stdout_limit,stderr_limit,
                           output_path,output_limit):
            if command[-1]=="--probe":
                return ProcessResult(0,json.dumps({
                    "tier":"base-container","needsDaclAugmentation":False,"warnings":[],
                    "probes":{"baseContainerApiPresent":True,"bfscfgPresent":False,
                              "bfsCompiledIn":False},
                }).encode(),b"")
            return ProcessResult(1,b'{"error":"not_implemented"}',b"")

        with patch.object(kokoro_module,"REVIEWED_MXC_EXECUTABLE_SHA256",
                          frozenset({executor_hash})):
            provider=MxcIsolationProvider(
                MxcIsolationConfig(executor,executor_hash,self.staging,(readonly,)),
                runner=failing_canary,
            )
            attestation=provider.attest()
        self.assertFalse(attestation.process_tree_contained)
        self.assertFalse(attestation.network_denied_by_os)
        self.assertIn("did not pass",attestation.reason)

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
