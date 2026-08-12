"""Static-only tests for the inert Voice Forge R8 guard successor."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import inspect
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load inert source: {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


r8 = load("voice_forge_r8_test_guards", "tools/qwen3_tts_voice_forge_r8_guards.py")
fixtures = load(
    "voice_forge_r8_preserved_r7_fixtures",
    "Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v7.py",
)

H = hashlib.sha256(b"voice-forge-r8-test-one").hexdigest()
H2 = hashlib.sha256(b"voice-forge-r8-test-two").hexdigest()


class FakeClock:
    CLOCK_ID_SHA256 = r8.SystemClockAuthority.CLOCK_ID_SHA256
    sample_value = r8.ClockSample(
        datetime(2026, 8, 10, 12, 5, tzinfo=timezone.utc),
        1_240_000_000_000,
        CLOCK_ID_SHA256,
    )

    def sample(self):
        return self.sample_value


def write_audit_and_authorization(
    root: Path,
    *,
    ttl: int = 600,
    issued: datetime = datetime(2026, 8, 10, 12, 1, tzinfo=timezone.utc),
    issued_mono: int = 1_000_000_000_000,
    completed: datetime = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc),
    clock_id: str | None = None,
):
    manifest_hash = "a" * 64
    inventory_hash = "b" * 64
    report = root / "System/Docs/r8-independent-audit.md"
    report.parent.mkdir(parents=True)
    report.write_bytes(b"fresh independent static R8 audit\n")
    subject = r8.audit_subject(
        manifest_sha256=manifest_hash, inventory_sha256=inventory_hash
    )
    audit = {
        "schema": "qwen3_tts_voice_forge_independent_static_audit_v8",
        "status": "FINAL",
        "authoritative_decision": "ACCEPT_STATIC_ONLY",
        "static_only": True,
        "runtime_execution_performed": False,
        "audit_authorizes_execution": False,
        "unresolved_blockers": [],
        **subject,
        "subject_sha256": r8.canonical_sha256(subject),
        "auditor_identity_sha256": H,
        "auditor_separation": {
            "fresh_independent_process": True,
            "subject_sources_authored_by_auditor": False,
        },
        "audit_report_path": report.relative_to(root).as_posix(),
        "audit_report_sha256": r8.sha256_file(report),
        "completed_utc": completed.isoformat().replace("+00:00", "Z"),
    }
    decision = root / "RecoverySprint/r8-audit/decision.json"
    decision.parent.mkdir(parents=True)
    decision.write_bytes(r8.canonical_bytes(audit) + b"\n")
    expires = issued + timedelta(seconds=ttl)
    authorization = {
        "schema": "qwen3_tts_voice_forge_execution_authorization_v8",
        "status": "FRESH_R8_STATIC_AUDIT_ACCEPTED_ONE_BOUNDED_RUN_DOCUMENT_ONLY",
        "execution_allowed": True,
        "one_use": True,
        "payload_manifest_path": r8.R8_PAYLOAD_MANIFEST_REL.as_posix(),
        "payload_manifest_sha256": manifest_hash,
        "independent_audit_decision_path": decision.relative_to(root).as_posix(),
        "independent_audit_decision_sha256": r8.sha256_file(decision),
        "independent_audit_subject_sha256": audit["subject_sha256"],
        "independent_auditor_identity_sha256": audit["auditor_identity_sha256"],
        "independent_audit_path": report.relative_to(root).as_posix(),
        "independent_audit_sha256": r8.sha256_file(report),
        "rejected_r7_audit_path": r8.R7_REJECTED_AUDIT_REL.as_posix(),
        "rejected_r7_audit_sha256": r8.R7_REJECTED_AUDIT_SHA256,
        "bundle_id": "bundle.r8.static",
        "run_id": "run.r8.static",
        "authorization_nonce_sha256": H,
        "worker_instance_nonce_sha256": H2,
        "generation_seed": 1,
        "clock_id_sha256": clock_id or FakeClock.CLOCK_ID_SHA256,
        "ttl_seconds": ttl,
        "issued_utc": issued.isoformat().replace("+00:00", "Z"),
        "expires_utc": expires.isoformat().replace("+00:00", "Z"),
        "issued_monotonic_ns": issued_mono,
        "expires_monotonic_ns": issued_mono + ttl * 1_000_000_000,
    }
    path = root / r8.R8_AUTHORIZATION_ROOT_REL / "authorization.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(r8.canonical_bytes(authorization) + b"\n")
    kwargs = {
        "project_root": root,
        "authorization_path": path,
        "expected_authorization_sha256": r8.sha256_file(path),
        "expected_manifest_sha256": manifest_hash,
        "expected_inventory_sha256": inventory_hash,
        "bundle_id": authorization["bundle_id"],
        "run_id": authorization["run_id"],
    }
    return authorization, path, kwargs


def worker_resource() -> dict:
    value = fixtures.worker_resource()
    value["schema"] = "qwen3_tts_voice_forge_worker_resource_evidence_v8"
    telemetry = value["worker_reported_telemetry"]
    telemetry["rss_sampler"]["started_monotonic_ns"] = 1_000_000_000_000
    telemetry["rss_sampler"]["ended_monotonic_ns"] = 1_001_000_000_000
    telemetry["design_generation_observed_cuda_reserved_bytes"] = 240
    telemetry["after_design_unload_cuda_reserved_bytes"] = 0
    telemetry["clone_generation_observed_cuda_reserved_bytes"] = 250
    value["worker_reported_telemetry_sha256"] = r8.canonical_sha256(telemetry)
    return value


def parent_resource():
    child = worker_resource()
    evidence, _old_child, claim, stdout_row, stderr_row = fixtures.parent_resource(
        child=child
    )
    evidence["schema"] = "qwen3_tts_voice_forge_resource_reconciliation_v8"
    parent = evidence["parent_job_observation"]
    parent["schema"] = "qwen3_tts_voice_forge_parent_job_observation_v8"
    parent["parent_started_monotonic_ns"] = 2_000_000_000_000
    parent["parent_ended_monotonic_ns"] = 2_008_000_000_000
    evidence["parent_job_observation_sha256"] = r8.canonical_sha256(parent)
    return evidence, child, claim, stdout_row, stderr_row


def validate_parent(bundle):
    evidence, child, claim, stdout_row, stderr_row = bundle
    return r8.validate_resource_evidence(
        evidence,
        worker_evidence=child,
        semantic_binding=fixtures.semantic(),
        worker_claim=claim,
        stdout_row=stdout_row,
        stderr_row=stderr_row,
    )


class PreservationAndInertnessTests(unittest.TestCase):
    def test_r8_payload_is_exact_inert_predecessor_closure(self):
        path = ROOT / r8.R8_PAYLOAD_MANIFEST_REL
        manifest, indexed = r8.verify_payload_manifest(
            project_root=ROOT,
            expected_manifest_sha256=r8.sha256_file(path),
        )
        self.assertFalse(manifest["execution_allowed"])
        self.assertFalse(manifest["self_authorization_allowed"])
        self.assertFalse(manifest["parent_worker_integration_present"])
        self.assertEqual(34, len(indexed))

    def test_distributed_binding_is_disabled_and_outside_authority_root(self):
        relative = Path(
            "TemporaryAI/config/qwen3_tts_voice_forge_external_acceptance_binding_v8.disabled.json"
        )
        binding = r8.strict_read_json(ROOT / relative, label="R8 disabled binding")
        self.assertFalse(binding["execution_allowed"])
        self.assertIn("NO_R8_PARENT_OR_WORKER_INTEGRATION", binding["status"])
        self.assertFalse(
            relative.as_posix().startswith(r8.R8_AUTHORIZATION_ROOT_REL.as_posix() + "/")
        )

    def test_rejected_r7_exact_bytes_are_preserved(self):
        expected = {
            "TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v7.json": (
                6646,
                "509d2b802310b1c0e075039da28e18744dad59bccd816f7623a8b0963169e6eb",
            ),
            "tools/qwen3_tts_voice_forge_r7_guards.py": (
                79259,
                "a92c9cf4fd7d6058a1a0f901725480a13380004478577b543b69475d56b5fc60",
            ),
            "tools/qwen3_tts_original_voice_forge_worker_v7.py": (
                26850,
                "8e7497dd6101040003ab17e8b79c4f57deedffb31df21de3cbd001ce6b391ca9",
            ),
            "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v7.py": (
                71846,
                "e4f99a0d315c41e9b23de0bee70cff3c460f1dd13f32f49b888f3af3007dd79b",
            ),
            "Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v7.py": (
                26326,
                "ac2514d7778a76e0a26f3561006faeb6cc0681781a4c4db7c3e057babef82b10",
            ),
            "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R7_INDEPENDENT_AUDIT_20260810.md": (
                11496,
                "577fd3cf047fbaa0abddeea7dfb7f86602b6b94f97b9f43a724d77affc7ab966",
            ),
        }
        for relative, (size, digest) in expected.items():
            path = ROOT / relative
            self.assertEqual(size, path.stat().st_size, relative)
            self.assertEqual(digest, r8.sha256_file(path), relative)

    def test_all_six_predecessor_manifests_and_r7_rejection_evidence_are_exact(self):
        expected = {
            "TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v2.json": "682d95880d93fffa68a7c9bbf6005ca52e59f1ab241be827c3f0c1d2938844a4",
            "TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v3.json": "3116650bf4937c77af9937fede8ee187f16165ab3a3d21ee3c2e08e6579bcada",
            "TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v4.json": "576d1a64db85d3b783ed6186fa3332daf54ed94381c5cf5a44600b875494f038",
            "TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v5.json": "92de1f2f770892e0bb09a6a0b2fb44ac1acf4206282bda6124dc84c54d10901b",
            "TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v6.json": "e32eb5dadfe80cc94cf1b57a98bf9220c8f7a5809d251b056d72fc02d2408a0e",
            "TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v7.json": "509d2b802310b1c0e075039da28e18744dad59bccd816f7623a8b0963169e6eb",
            "RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7_independent_audit/attempt_01/INDEPENDENT_REHASH.py": "b8e21af5fd5e8e64b13077ef92c7cb4d08ed5be2a909c9cc9c4eed8c645724ef",
            "RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7_independent_audit/attempt_01/INDEPENDENT_HOSTILE_PROBES.py": "f7fcea592b45e6a1cf351e5909a3e6bb156e5d88555205ab2f4c87ad7b37ea19",
            "RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7_independent_audit/attempt_01/EXACT_BYTE_REHASH_RESULT.json": "76593b84a5632b336d5098f03eb90bd764d9aa749e96faa37a53501a647b0125",
            "RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7_independent_audit/attempt_01/INDEPENDENT_HOSTILE_PROBE_RESULT.json": "96aeb6b3ea87cb4c4a03c9c7e6eb15f5432a33eb6c8fa01e5b0a7c5582060f56",
            "RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7_independent_audit/attempt_01/CHECKPOINT.md": "e4c58754f3623d02e30c557831caacf55ffae4269c64bc35235c3a273f9f035c",
        }
        for relative, digest in expected.items():
            self.assertEqual(digest, r8.sha256_file(ROOT / relative), relative)

    def test_r8_has_no_parent_or_worker_entry_point(self):
        self.assertFalse((ROOT / "tools/qwen3_tts_original_voice_forge_worker_v8.py").exists())
        self.assertFalse(
            (ROOT / "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v8.py").exists()
        )


class AuthorizationTimeTests(unittest.TestCase):
    def test_valid_short_lived_dual_clock_document_validates_but_cannot_authorize(self):
        with tempfile.TemporaryDirectory() as folder:
            _authorization, _path, kwargs = write_audit_and_authorization(Path(folder))
            with mock.patch.object(r8, "SystemClockAuthority", FakeClock):
                observed, evidence = r8.validate_execution_authorization_document(**kwargs)
                self.assertEqual(600, observed["ttl_seconds"])
                self.assertEqual(FakeClock.CLOCK_ID_SHA256, evidence["verified_clock_id_sha256"])
                with self.assertRaisesRegex(r8.R8GuardError, "integration is absent"):
                    r8.verify_execution_authorization(**kwargs)

    def test_no_caller_supplied_verified_time_parameter_exists(self):
        signature = inspect.signature(r8.validate_execution_authorization_document)
        self.assertNotIn("verified_at", signature.parameters)
        self.assertNotIn("trusted_time", signature.parameters)

    def test_r7_year_9999_style_lifetime_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            _authorization, path, kwargs = write_audit_and_authorization(
                Path(folder), ttl=901
            )
            with mock.patch.object(r8, "SystemClockAuthority", FakeClock):
                with self.assertRaisesRegex(r8.R8GuardError, "TTL"):
                    r8.validate_execution_authorization_document(**kwargs)
            self.assertTrue(path.exists())

    def test_utc_and_monotonic_lifetimes_must_encode_same_ttl(self):
        with tempfile.TemporaryDirectory() as folder:
            authorization, path, kwargs = write_audit_and_authorization(Path(folder))
            authorization["expires_monotonic_ns"] += 1
            path.write_bytes(r8.canonical_bytes(authorization) + b"\n")
            kwargs["expected_authorization_sha256"] = r8.sha256_file(path)
            with mock.patch.object(r8, "SystemClockAuthority", FakeClock):
                with self.assertRaisesRegex(r8.R8GuardError, "monotonic.*TTL"):
                    r8.validate_execution_authorization_document(**kwargs)

    def test_stale_audit_and_clock_identity_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            _authorization, _path, kwargs = write_audit_and_authorization(
                Path(folder), completed=datetime(2026, 8, 8, 0, 0, tzinfo=timezone.utc)
            )
            with mock.patch.object(r8, "SystemClockAuthority", FakeClock):
                with self.assertRaisesRegex(r8.R8GuardError, "fresh completed audit"):
                    r8.validate_execution_authorization_document(**kwargs)
        with tempfile.TemporaryDirectory() as folder:
            _authorization, _path, kwargs = write_audit_and_authorization(
                Path(folder), clock_id="c" * 64
            )
            with mock.patch.object(r8, "SystemClockAuthority", FakeClock):
                with self.assertRaisesRegex(r8.R8GuardError, "clock identity"):
                    r8.validate_execution_authorization_document(**kwargs)


class WorkerResourceTests(unittest.TestCase):
    def test_valid_extended_worker_evidence_passes(self):
        value = worker_resource()
        self.assertIs(
            value,
            r8.validate_worker_resource_evidence(
                value, semantic_binding=fixtures.semantic()
            ),
        )

    def test_every_required_cuda_pair_rejects_allocated_above_reserved(self):
        for allocated_key, reserved_key in r8.CUDA_PAIRS:
            with self.subTest(sample=allocated_key):
                value = worker_resource()
                telemetry = value["worker_reported_telemetry"]
                telemetry[reserved_key] = telemetry[allocated_key]
                telemetry[allocated_key] += 1
                value["worker_reported_telemetry_sha256"] = r8.canonical_sha256(telemetry)
                with self.assertRaises(r8.R8GuardError):
                    r8.validate_worker_resource_evidence(
                        value, semantic_binding=fixtures.semantic()
                    )

    def test_exact_r7_baseline_and_final_impossibility_is_rejected(self):
        value = worker_resource()
        telemetry = value["worker_reported_telemetry"]
        telemetry["baseline_cuda_allocated_bytes"] = 50
        telemetry["baseline_cuda_reserved_bytes"] = 0
        telemetry["after_design_unload_cuda_allocated_bytes"] = 50
        telemetry["after_design_unload_cuda_reserved_bytes"] = 0
        telemetry["final_cuda_allocated_bytes"] = 50
        telemetry["final_cuda_reserved_bytes"] = 0
        value["worker_reported_telemetry_sha256"] = r8.canonical_sha256(telemetry)
        with self.assertRaisesRegex(r8.R8GuardError, "reserved bytes"):
            r8.validate_worker_resource_evidence(value, semantic_binding=fixtures.semantic())

    def test_elapsed_must_equal_monotonic_and_remain_finite_positive(self):
        for hostile in (999.0, -1.0):
            with self.subTest(elapsed=hostile):
                value = worker_resource()
                value["worker_reported_telemetry"]["rss_sampler"][
                    "elapsed_seconds"
                ] = hostile
                value["worker_reported_telemetry_sha256"] = r8.canonical_sha256(
                    value["worker_reported_telemetry"]
                )
                with self.assertRaises(r8.R8GuardError):
                    r8.validate_worker_resource_evidence(
                        value, semantic_binding=fixtures.semantic()
                    )
        for hostile in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(nonfinite=repr(hostile)):
                with self.assertRaisesRegex(r8.R8GuardError, "not finite"):
                    r8._validate_elapsed(
                        started_ns=1,
                        ended_ns=1_000_000_001,
                        elapsed=hostile,
                        label="hostile R8 elapsed",
                    )

    def test_equal_utc_clock_and_impossible_sample_count_are_rejected(self):
        value = worker_resource()
        rss = value["worker_reported_telemetry"]["rss_sampler"]
        rss["ended_utc"] = rss["started_utc"]
        value["worker_reported_telemetry_sha256"] = r8.canonical_sha256(
            value["worker_reported_telemetry"]
        )
        with self.assertRaisesRegex(r8.R8GuardError, "UTC interval"):
            r8.validate_worker_resource_evidence(value, semantic_binding=fixtures.semantic())
        value = worker_resource()
        value["worker_reported_telemetry"]["rss_sampler"]["sample_count"] = 10000
        value["worker_reported_telemetry_sha256"] = r8.canonical_sha256(
            value["worker_reported_telemetry"]
        )
        with self.assertRaisesRegex(r8.R8GuardError, "sample count"):
            r8.validate_worker_resource_evidence(value, semantic_binding=fixtures.semantic())


class ParentResourceTests(unittest.TestCase):
    def test_valid_parent_evidence_passes(self):
        bundle = parent_resource()
        self.assertIs(bundle[0], validate_parent(bundle))

    def test_every_job_counter_rejects_negative_boolean_and_fractional_values(self):
        for key in r8.JOB_COUNTER_BOUNDS:
            for hostile in (-1, True, 1.5):
                with self.subTest(counter=key, value=hostile):
                    bundle = parent_resource()
                    bundle[0]["parent_job_observation"][key] = hostile
                    bundle[0]["parent_job_observation_sha256"] = r8.canonical_sha256(
                        bundle[0]["parent_job_observation"]
                    )
                    with self.assertRaises(r8.R8GuardError):
                        validate_parent(bundle)

    def test_exact_r7_negative_terminated_counter_is_rejected(self):
        bundle = parent_resource()
        bundle[0]["parent_job_observation"]["total_terminated_processes"] = -1
        bundle[0]["parent_job_observation_sha256"] = r8.canonical_sha256(
            bundle[0]["parent_job_observation"]
        )
        with self.assertRaisesRegex(r8.R8GuardError, "bounded integer"):
            validate_parent(bundle)

    def test_physically_impossible_job_relationships_are_rejected(self):
        mutations = (
            ("terminated", lambda p: p.update(total_processes=1, total_terminated_processes=2)),
            ("active", lambda p: p.update(total_processes=1, active_processes_after_termination=2)),
            ("memory", lambda p: p.update(peak_process_memory_used_bytes=6000, peak_job_memory_used_bytes=5000)),
            ("read_io", lambda p: p.update(io_read_operation_count=0, io_read_bytes=1)),
            ("write_io", lambda p: p.update(io_write_operation_count=0, io_write_bytes=1)),
            ("pid", lambda p: p.update(parent_pid=p["primary_worker_pid"])),
        )
        for label, mutate in mutations:
            with self.subTest(relationship=label):
                bundle = parent_resource()
                mutate(bundle[0]["parent_job_observation"])
                bundle[0]["parent_job_observation_sha256"] = r8.canonical_sha256(
                    bundle[0]["parent_job_observation"]
                )
                with self.assertRaises(r8.R8GuardError):
                    validate_parent(bundle)

    def test_parent_wall_elapsed_must_match_monotonic_timestamps(self):
        bundle = parent_resource()
        bundle[0]["parent_job_observation"]["parent_wall_seconds"] = 999.0
        bundle[0]["parent_job_observation_sha256"] = r8.canonical_sha256(
            bundle[0]["parent_job_observation"]
        )
        with self.assertRaisesRegex(r8.R8GuardError, "monotonic timestamps"):
            validate_parent(bundle)


if __name__ == "__main__":
    unittest.main()
