"""Static-only hostile tests for the append-only Qwen3-TTS Voice Forge R6.

These tests do not create audio, import model packages, use a GPU, or launch a
person/runtime.  They exercise only stdlib trust and evidence validators.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r6 = load("voice_forge_r6_guards_test", "tools/qwen3_tts_voice_forge_r6_guards.py")
worker = load(
    "voice_forge_r6_worker_test", "tools/qwen3_tts_original_voice_forge_worker_v6.py"
)
runner = load(
    "voice_forge_r6_runner_test",
    "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v6.py",
)

H = hashlib.sha256(b"voice-forge-r6-static-hostile-fixture").hexdigest()


def semantic() -> dict:
    value = {key: H for key in r6.SEMANTIC_BINDING_KEYS}
    value.update(
        {
            "bundle_id": "bundle.r6.test",
            "candidate_id": "candidate.r6.test",
            "ai_type": "expert_temp_ai",
            "opaque_voice_id": "voice.r6.test",
            "run_id": "run.r6.test",
            "attempt": "Voice/voice_forge/private_review_v6/run.r6.test/attempt_001",
            "generation_seed": 8675309,
            "voice_design_model_revision": "sealed-design-revision",
            "base_model_revision": "sealed-base-revision",
        }
    )
    return value


def core(value: dict | None = None) -> dict:
    source = value or semantic()
    return {key: source[key] for key in r6.CORE_BINDING_KEYS}


def r4_and_r5_profiles() -> tuple[dict, dict]:
    r4 = {
        "schema": "qwen3_tts_original_voice_profile_candidate_v4",
        **core(),
        **r6.FINAL_DISABLED_PERMISSIONS,
        "historical_marker": "preserved-r4",
    }
    r5 = {
        **r4,
        "schema": "qwen3_tts_original_voice_profile_candidate_v5",
        "r5_status": "PRIVATE_UNREVIEWED_PARENT_FINALIZATION_PENDING",
        "payload_manifest_sha256": H,
        "execution_authorization": {"sha256": H},
        "authorization_ledger_sha256": H,
        "exact_provenance_sha256": H,
        "parent_finalization_required": True,
        "later_use_acceptance_reopen_required": True,
        "independent_execution_audit": "REQUIRED_AFTER_BOUNDED_RUN",
    }
    return r4, r5


def evaluator(value: dict | None = None) -> dict:
    s = value or semantic()

    def asr(role: str, wav_key: str, text_key: str, transcript_key: str) -> dict:
        return {
            "role": role,
            "source_wav_sha256": s[wav_key],
            "expected_text_sha256": s[text_key],
            "transcript_sha256": s[transcript_key],
            "asr_mode": "REAL_LOCAL_ASR",
            "asr_engine": "sealed-asr",
            "asr_version": "1",
            "asr_model_manifest_sha256": H,
            "speech_mode": "REAL_LOCAL_SPEECH_CLASSIFIER",
            "speech_classifier_engine": "sealed-speech",
            "speech_classifier_version": "1",
            "speech_classifier_model_manifest_sha256": H,
            "speech_classifier_adapter_sha256": H,
            "word_error_rate": 0.0,
            "maximum_word_error_rate": 0.1,
            "speech_probability": 0.99,
            "minimum_speech_probability": 0.8,
            "accepted": True,
        }

    def tone(role: str, wav_key: str) -> dict:
        return {
            "role": role,
            "source_wav_sha256": s[wav_key],
            "detector": "MULTIWINDOW_SPECTRAL_CONCENTRATION_V2",
            "pure_tone_probability": 0.01,
            "maximum_pure_tone_probability": 0.2,
            "pure_tone_rejected": True,
        }

    return {
        "schema": "qwen3_tts_voice_forge_evaluator_evidence_v6",
        "status": "WORKER_EVIDENCE_PARENT_REVALIDATION_REQUIRED",
        "semantic_binding_sha256": r6.evidence_subject_sha256(s),
        "reference_wav_sha256": s["reference_wav_sha256"],
        "clone_test_wav_sha256": s["clone_test_wav_sha256"],
        "runtime_clone_prompt_sha256": s["runtime_clone_prompt_sha256"],
        "reference_transcript_sha256": s["reference_transcript_sha256"],
        "clone_transcript_sha256": s["clone_transcript_sha256"],
        "asr_and_speech": {
            "reference": asr(
                "reference", "reference_wav_sha256", "reference_text_sha256",
                "reference_transcript_sha256"
            ),
            "clone": asr(
                "clone", "clone_test_wav_sha256", "test_text_sha256",
                "clone_transcript_sha256"
            ),
        },
        "pure_tone": {
            "reference": tone("reference", "reference_wav_sha256"),
            "clone": tone("clone", "clone_test_wav_sha256"),
        },
        "speaker_identity": {
            "reference_wav_sha256": s["reference_wav_sha256"],
            "clone_test_wav_sha256": s["clone_test_wav_sha256"],
            "embedding_mode": "REAL_LOCAL_SPEAKER_EMBEDDING",
            "embedding_engine": "sealed-embedding",
            "embedding_version": "1",
            "embedding_model_manifest_sha256": H,
            "reference_to_clone_similarity": 0.9,
            "minimum_similarity": 0.8,
            "accepted": True,
        },
        "collision_corpus": {
            "clone_test_wav_sha256": s["clone_test_wav_sha256"],
            "corpus_manifest_sha256": H,
            "corpus_snapshot_sha256": H,
            "all_embeddings_recomputed_from_exact_wavs": True,
            "collision_results_sha256": H,
            "maximum_allowed_similarity": 0.75,
            "no_resident_or_generic_collision": True,
        },
        "named_person_clearance": {
            "identity_basis": "original_trait_description",
            "voice_origin": "ORIGINAL_SYNTHETIC_TEXT_DESIGN_NOT_PERSON_CLONE",
            "static_manifest_path": "sealed/static.json",
            "static_manifest_sha256": H,
            "live_report_path": "sealed/live.json",
            "live_report_sha256": H,
            "named_person_or_imitation_language_found": False,
            "cleared": True,
        },
        "watermark": {
            "preflight_manifest_path": "sealed/watermark_preflight.json",
            "preflight_manifest_sha256": H,
            "live_report_path": "sealed/watermark_live.json",
            "live_report_sha256": H,
            "status_ceiling": "NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK",
            "intentional_audio_watermark_proven": False,
            "watermark_removal_or_circumvention_attempted": False,
        },
        "predecessor_audio_acceptance_sha256": H,
        "predecessor_evaluator_import_bindings_sha256": H,
        "predecessor_r2_manifest_sha256": H,
    }


def worker_resource(value: dict | None = None) -> dict:
    s = value or semantic()
    telemetry = {key: 100 for key in r6.WORKER_TELEMETRY_KEYS}
    telemetry.update(
        {
            "rss_sampler": {"kind": "sealed-parent-independent-sampler"},
            "os_reported_peak_process_rss_is_high_water_mark": True,
            "point_samples_labeled_as_peaks": False,
        }
    )
    timings = {key: 1.0 for key in r6.TIMING_KEYS}
    timings["total_worker"] = 6.0
    events = ["bootstrap", "complete"]
    return {
        "schema": "qwen3_tts_voice_forge_worker_resource_evidence_v6",
        "status": "WORKER_REPORTED_PARENT_RECONCILIATION_REQUIRED",
        "semantic_binding_sha256": r6.evidence_subject_sha256(s),
        "worker_reported_telemetry": telemetry,
        "worker_reported_telemetry_sha256": r6.canonical_sha256(telemetry),
        "worker_reported_timings_seconds": timings,
        "worker_reported_timings_sha256": r6.canonical_sha256(timings),
        "worker_reported_events": events,
        "worker_reported_events_sha256": r6.canonical_sha256(events),
    }


def parent_resource(value: dict | None = None, wr: dict | None = None) -> dict:
    s = value or semantic()
    worker_value = wr or worker_resource(s)
    observation = {
        "schema": "qwen3_tts_voice_forge_parent_job_observation_v6",
        "observed_by_parent_not_child": True,
        "windows_job_assigned_before_resume": True,
        "primary_worker_exit_code": 0,
        "job_termination_requested_after_primary_exit": True,
        "active_processes_after_termination": 0,
        "process_tree_quiescent_before_finalization": True,
        "quiescence_observed_utc": "2026-08-10T12:00:00Z",
        "finalization_started_utc": "2026-08-10T12:00:01Z",
        "parent_wall_seconds": 7.0,
        "peak_process_memory_used_bytes": 100,
        "peak_job_memory_used_bytes": 100,
        "io_read_operation_count": 0,
        "io_write_operation_count": 0,
        "io_read_bytes": 0,
        "io_write_bytes": 0,
        "worker_stdout_bytes": 0,
        "worker_stdout_sha256": H,
        "worker_stderr_bytes": 0,
        "worker_stderr_sha256": H,
    }
    return {
        "schema": "qwen3_tts_voice_forge_resource_reconciliation_v6",
        "status": "PARENT_RECONCILED_AFTER_PROCESS_TREE_QUIESCENCE",
        "semantic_binding_sha256": r6.evidence_subject_sha256(s),
        "worker_resource_evidence_sha256": s["resource_evidence_sha256"],
        "parent_job_observation": observation,
        "parent_job_observation_sha256": r6.canonical_sha256(observation),
        "worker_only_telemetry_accepted_as_parent_truth": False,
        "reconciliation_passed": True,
    }


class SemanticBindingTests(unittest.TestCase):
    def test_valid_semantic_binding(self):
        self.assertEqual(r6.validate_semantic_binding(semantic()), semantic())

    def test_ineligible_person_clone_ai_type_rejected(self):
        value = semantic()
        value["ai_type"] = "person_clone"
        with self.assertRaises(r6.R6GuardError):
            r6.validate_semantic_binding(value)

    def test_boolean_seed_rejected(self):
        value = semantic()
        value["generation_seed"] = True
        with self.assertRaises(r6.R6GuardError):
            r6.validate_semantic_binding(value)

    def test_hash_exact_unsafe_r5_profile_rejected(self):
        r4, r5 = r4_and_r5_profiles()
        unsafe = copy.deepcopy(r5)
        unsafe["candidate_id"] = "attacker.candidate"
        unsafe["ai_type"] = "person_clone"
        unsafe["assignment_allowed"] = True
        hashlib.sha256(r6.canonical_bytes(unsafe)).hexdigest()  # exact hostile bytes exist
        with self.assertRaises(r6.R6GuardError):
            r6.validate_r5_safe_extension(
                r4_profile=r4,
                r5_profile=unsafe,
                expected_core=core(),
                expected_r4_profile_sha256=H,
                expected_payload_sha256=H,
                expected_authorization_sha256=H,
                expected_parent_ledger_sha256=H,
            )

    def test_profile_extra_field_rejected(self):
        r4, r5 = r4_and_r5_profiles()
        r5["unreviewed_attacker_field"] = True
        with self.assertRaises(r6.R6GuardError):
            r6.validate_r5_safe_extension(
                r4_profile=r4, r5_profile=r5, expected_core=core(),
                expected_r4_profile_sha256=H, expected_payload_sha256=H,
                expected_authorization_sha256=H, expected_parent_ledger_sha256=H,
            )


class WorkerClaimTests(unittest.TestCase):
    def test_second_worker_claim_collides(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            kwargs = dict(
                project_root=root,
                authorization_sha256=H,
                authorization_nonce_sha256=H,
                worker_instance_nonce_sha256=H,
                payload_manifest_sha256=H,
                bundle_id="bundle.r6.test",
                run_id="run.r6.test",
                attempt="attempt_001",
                parent_reservation_path="stable/reservation.json",
                parent_reservation_sha256=H,
                parent_ledger_path="stable/ledger.json",
                parent_ledger_sha256=H,
                worker_path="tools/worker_v6.py",
                worker_sha256=H,
                worker_pid=1234,
                created_utc="2026-08-10T12:00:00Z",
            )
            r6.create_worker_launch_claim(**kwargs)
            with self.assertRaises(r6.R6CollisionError):
                r6.create_worker_launch_claim(**kwargs)

    def test_early_failure_claim_still_blocks_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            kwargs = dict(
                project_root=Path(folder), authorization_sha256=H,
                authorization_nonce_sha256=H, worker_instance_nonce_sha256=H,
                payload_manifest_sha256=H, bundle_id="bundle.r6.test",
                run_id="run.r6.test", attempt="attempt_001",
                parent_reservation_path="stable/reservation.json",
                parent_reservation_sha256=H, parent_ledger_path="stable/ledger.json",
                parent_ledger_sha256=H, worker_path="tools/worker_v6.py",
                worker_sha256=H, worker_pid=1234,
                created_utc="2026-08-10T12:00:00Z",
            )
            r6.create_worker_launch_claim(**kwargs)
            # No successor output is created: this represents an early crash.
            with self.assertRaises(r6.R6CollisionError):
                r6.create_worker_launch_claim(**kwargs)

    def test_claim_collision_prevents_loader_call(self):
        called = []
        with mock.patch.object(
            worker,
            "bootstrap_claim_before_predecessor_import",
            side_effect=worker.R6ForgeError("claimed"),
        ):
            with self.assertRaises(worker.R6ForgeError):
                worker.claim_then_load_predecessors(
                    args=mock.Mock(), authorization={}, loader=lambda: called.append(True)
                )
        self.assertEqual(called, [])

    def test_worker_source_claim_precedes_predecessor_load(self):
        source = (ROOT / "tools/qwen3_tts_original_voice_forge_worker_v6.py").read_text(
            encoding="utf-8"
        )
        main_body = source[source.index("def main(") :]
        self.assertLess(
            main_body.index("bootstrap_claim_before_predecessor_import"),
            main_body.index("execute_after_claim"),
        )


class EvaluatorAndResourceTests(unittest.TestCase):
    def test_complete_evaluator_schema_passes(self):
        self.assertEqual(r6.validate_evaluator_evidence(evaluator(), semantic_binding=semantic()), evaluator())

    def test_missing_evaluator_section_rejected(self):
        evidence = evaluator()
        del evidence["watermark"]
        with self.assertRaises(r6.R6GuardError):
            r6.validate_evaluator_evidence(evidence, semantic_binding=semantic())

    def test_wav_unbound_asr_rejected(self):
        evidence = evaluator()
        evidence["asr_and_speech"]["clone"]["source_wav_sha256"] = "a" * 64
        with self.assertRaises(r6.R6GuardError):
            r6.validate_evaluator_evidence(evidence, semantic_binding=semantic())

    def test_forged_evidence_subject_rejected(self):
        evidence = evaluator()
        evidence["semantic_binding_sha256"] = "b" * 64
        with self.assertRaises(r6.R6GuardError):
            r6.validate_evaluator_evidence(evidence, semantic_binding=semantic())

    def test_parent_reconciled_resources_pass(self):
        wr = worker_resource()
        evidence = parent_resource(wr=wr)
        self.assertEqual(
            r6.validate_resource_evidence(
                evidence, worker_evidence=wr, semantic_binding=semantic()
            ),
            evidence,
        )

    def test_child_only_resource_evidence_rejected(self):
        wr = worker_resource()
        with self.assertRaises(r6.R6GuardError):
            r6.validate_resource_evidence(
                wr, worker_evidence=wr, semantic_binding=semantic()
            )

    def test_live_descendant_blocks_quiescence(self):
        wr = worker_resource()
        evidence = parent_resource(wr=wr)
        evidence["parent_job_observation"]["active_processes_after_termination"] = 1
        evidence["parent_job_observation_sha256"] = r6.canonical_sha256(
            evidence["parent_job_observation"]
        )
        with self.assertRaises(r6.R6GuardError):
            r6.validate_resource_evidence(
                evidence, worker_evidence=wr, semantic_binding=semantic()
            )

    def test_finalization_before_quiescence_rejected(self):
        wr = worker_resource()
        evidence = parent_resource(wr=wr)
        evidence["parent_job_observation"]["finalization_started_utc"] = (
            "2026-08-10T11:59:59Z"
        )
        evidence["parent_job_observation_sha256"] = r6.canonical_sha256(
            evidence["parent_job_observation"]
        )
        with self.assertRaises(r6.R6GuardError):
            r6.validate_resource_evidence(
                evidence, worker_evidence=wr, semantic_binding=semantic()
            )

    def test_parent_peak_below_worker_peak_rejected(self):
        wr = worker_resource()
        evidence = parent_resource(wr=wr)
        evidence["parent_job_observation"]["peak_process_memory_used_bytes"] = 99
        evidence["parent_job_observation_sha256"] = r6.canonical_sha256(
            evidence["parent_job_observation"]
        )
        with self.assertRaises(r6.R6GuardError):
            r6.validate_resource_evidence(
                evidence, worker_evidence=wr, semantic_binding=semantic()
            )


class StaticTrustBoundaryTests(unittest.TestCase):
    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(r6.R6GuardError):
            r6.strict_json_bytes(b'{"a":1,"a":2}', "duplicate fixture")

    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(r6.R6GuardError):
                r6.inside(Path(folder), "../escape.json", "escape fixture")

    def test_output_collision_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "append_only.json"
            r6.write_new(path, b"first")
            with self.assertRaises(r6.R6CollisionError):
                r6.write_new(path, b"second")

    def test_stale_authorization_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rejected = root / r6.R5_REJECTED_AUDIT_REL
            rejected.parent.mkdir(parents=True)
            rejected.write_bytes((ROOT / r6.R5_REJECTED_AUDIT_REL).read_bytes())
            audit = root / "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R6_INDEPENDENT_AUDIT_TEST.md"
            audit.write_text("static audit fixture\n", encoding="utf-8")
            auth_path = root / r6.R6_AUTHORIZATION_ROOT_REL / "stale.json"
            auth_path.parent.mkdir(parents=True)
            auth = {
                "schema": "qwen3_tts_voice_forge_execution_authorization_v6",
                "status": "FRESH_R6_AUDIT_ACCEPTED_ONE_BOUNDED_RUN",
                "execution_allowed": True,
                "one_use": True,
                "payload_manifest_path": r6.R6_PAYLOAD_MANIFEST_REL.as_posix(),
                "payload_manifest_sha256": H,
                "independent_audit_path": audit.relative_to(root).as_posix(),
                "independent_audit_sha256": r6.sha256_file(audit),
                "rejected_r5_audit_path": r6.R5_REJECTED_AUDIT_REL.as_posix(),
                "rejected_r5_audit_sha256": r6.R5_REJECTED_AUDIT_SHA256,
                "bundle_id": "bundle.r6.test",
                "run_id": "run.r6.test",
                "authorization_nonce_sha256": H,
                "worker_instance_nonce_sha256": H,
                "generation_seed": 1,
                "issued_utc": "2026-08-01T00:00:00Z",
                "expires_utc": "2026-08-02T00:00:00Z",
            }
            auth_path.write_text(json.dumps(auth, sort_keys=True), encoding="utf-8")
            with self.assertRaises(r6.R6GuardError):
                r6.verify_execution_authorization(
                    project_root=root,
                    authorization_path=auth_path,
                    expected_authorization_sha256=r6.sha256_file(auth_path),
                    expected_manifest_sha256=H,
                    bundle_id="bundle.r6.test",
                    run_id="run.r6.test",
                    verified_at=datetime(2026, 8, 10, tzinfo=timezone.utc),
                )

    def test_r5_principal_files_preserved(self):
        expected = {
            "tools/qwen3_tts_voice_forge_r5_guards.py": "c2792fd8009d78055c5e0d750713e4d104f468db20d258776d468953f6c09885",
            "tools/qwen3_tts_original_voice_forge_worker_v5.py": "2714e29525a64e59ffa38cee6cbcd5f07538492c9c3e768f762e13d7de24c842",
            "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v5.py": "253ca43a809ce29dd02036b36ced63cdc1222109bc6369499eed238d946f1453",
            "Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v5.py": "49539c8735274928c9882390bb424e0f623265acd10020630dcd6c12a6e4c1e7",
            "TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v5.json": "92de1f2f770892e0bb09a6a0b2fb44ac1acf4206282bda6124dc84c54d10901b",
            "TemporaryAI/config/qwen3_tts_voice_forge_external_acceptance_binding_v5.disabled.json": "4222979540b97757a2b8dd9c684c3f9736428abedacf0d775a5abd485d995917",
        }
        for rel, digest in expected.items():
            self.assertEqual(r6.sha256_file(ROOT / rel), digest, rel)

    def test_payload_sets_are_exact_and_match(self):
        self.assertEqual(runner.R6_REQUIRED_PAYLOADS, worker.R6_REQUIRED_PAYLOADS)
        r5_manifest = json.loads(
            (ROOT / "TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v5.json").read_text(
                encoding="utf-8"
            )
        )
        expected = {row["path"] for row in r5_manifest["files"]} | {
            "TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v5.json",
            "tools/qwen3_tts_voice_forge_r6_guards.py",
            "tools/qwen3_tts_original_voice_forge_worker_v6.py",
            "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v6.py",
            r6.R5_REJECTED_AUDIT_REL.as_posix(),
            "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R6_REPAIR_BOUNDARY_20260810.md",
        }
        self.assertEqual(runner.R6_REQUIRED_PAYLOADS, expected)
        self.assertEqual(len(expected), 24)

    def test_disabled_binding_is_non_authorizing(self):
        path = ROOT / "TemporaryAI/config/qwen3_tts_voice_forge_external_acceptance_binding_v6.disabled.json"
        self.assertTrue(path.is_file())
        value = r6.strict_read_json(path, label="R6 disabled binding")
        self.assertFalse(value["execution_allowed"])
        self.assertNotEqual(value["status"], "FRESH_R6_AUDIT_ACCEPTED_ONE_BOUNDED_RUN")
        self.assertNotIn(
            r6.R6_AUTHORIZATION_ROOT_REL.as_posix(), path.relative_to(ROOT).as_posix()
        )

    def test_static_sources_compile_from_exact_bytes(self):
        for rel in (
            "tools/qwen3_tts_voice_forge_r6_guards.py",
            "tools/qwen3_tts_original_voice_forge_worker_v6.py",
            "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v6.py",
        ):
            compile((ROOT / rel).read_bytes(), rel, "exec")


if __name__ == "__main__":
    unittest.main()
