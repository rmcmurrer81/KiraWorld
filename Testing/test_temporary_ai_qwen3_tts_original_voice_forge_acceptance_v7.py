"""Static-only hostile tests for append-only Voice Forge R7.

No parent, worker, predecessor graph, model, audio, GPU, person, body, Blender,
network, or launcher is executed.  The suite imports inert source modules and
calls only pure/stdlib trust, evidence, and identity-comparison helpers.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r7 = load("voice_forge_r7_guards_test", "tools/qwen3_tts_voice_forge_r7_guards.py")
worker = load(
    "voice_forge_r7_worker_test", "tools/qwen3_tts_original_voice_forge_worker_v7.py"
)

H = hashlib.sha256(b"voice-forge-r7-hostile-fixture").hexdigest()
H2 = hashlib.sha256(b"voice-forge-r7-hostile-fixture-two").hexdigest()


def semantic() -> dict:
    value = {key: H for key in r7.SEMANTIC_BINDING_KEYS}
    value.update(
        {
            "bundle_id": "bundle.r7.test",
            "candidate_id": "candidate.r7.test",
            "ai_type": "expert_temp_ai",
            "opaque_voice_id": "voice.r7.test",
            "run_id": "run.r7.test",
            "attempt": "Voice/voice_forge/private_review_v7/run.r7.test/attempt_001",
            "generation_seed": 8675309,
            "voice_design_model_revision": "sealed-design-revision",
            "base_model_revision": "sealed-base-revision",
            "execution_authorization_path": "Data/voice/authorizations/qwen3_tts_voice_forge_v7/auth.json",
            "independent_audit_decision_path": "RecoverySprint/audit/decision.json",
            "independent_audit_report_path": "System/Docs/audit.md",
            "entry_worker_path": "tools/qwen3_tts_original_voice_forge_worker_v7.py",
        }
    )
    return value


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
            "word_error_rate": 0.01,
            "maximum_word_error_rate": 0.05,
            "speech_probability": 0.99,
            "minimum_speech_probability": 0.9,
            "accepted": True,
        }

    def tone(role: str, wav_key: str) -> dict:
        return {
            "role": role,
            "source_wav_sha256": s[wav_key],
            "detector": "MULTIWINDOW_SPECTRAL_CONCENTRATION_V2",
            "pure_tone_probability": 0.01,
            "maximum_pure_tone_probability": 0.1,
            "pure_tone_rejected": True,
        }

    collision_results = [
        {"voice_id": "resident.voice", "kind": "resident", "similarity": 0.5}
    ]
    return {
        "schema": "qwen3_tts_voice_forge_evaluator_evidence_v7",
        "status": "WORKER_EVIDENCE_PARENT_REVALIDATION_REQUIRED",
        "semantic_binding_sha256": r7.evidence_subject_sha256(s),
        "reference_wav_sha256": s["reference_wav_sha256"],
        "clone_test_wav_sha256": s["clone_test_wav_sha256"],
        "runtime_clone_prompt_sha256": s["runtime_clone_prompt_sha256"],
        "reference_transcript_sha256": s["reference_transcript_sha256"],
        "clone_transcript_sha256": s["clone_transcript_sha256"],
        "threshold_contract_path": r7.R2_CONTRACT_REL.as_posix(),
        "threshold_contract_sha256": r7.R2_CONTRACT_SHA256,
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
            "corpus_manifest_sha256": s["evaluation_corpus_sha256"],
            "corpus_snapshot_sha256": H,
            "all_embeddings_recomputed_from_exact_wavs": True,
            "collision_results": collision_results,
            "collision_results_sha256": r7.canonical_sha256(collision_results),
            "maximum_observed_similarity": 0.5,
            "maximum_allowed_similarity": 0.72,
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
    rss = {
        "maximum_observed_process_rss_bytes": 2_500,
        "sample_count": 20,
        "sampling_interval_seconds": 0.01,
        "started_utc": "2026-08-10T12:00:00Z",
        "ended_utc": "2026-08-10T12:00:01Z",
        "elapsed_seconds": 1.0,
        "generation_and_evaluation_phases_included": True,
        "is_os_high_water_mark": False,
    }
    telemetry = {
        "rss_sampler": rss,
        "os_reported_peak_process_rss_bytes": 3_000,
        "os_reported_peak_process_rss_is_high_water_mark": True,
        "baseline_process_rss_bytes": 1_000,
        "baseline_cuda_allocated_bytes": 0,
        "baseline_cuda_reserved_bytes": 0,
        "torch_peak_cuda_allocated_bytes": 180,
        "torch_peak_cuda_reserved_bytes": 280,
        "after_design_load_observed_cuda_allocated_bytes": 100,
        "after_design_load_observed_cuda_reserved_bytes": 200,
        "after_base_load_observed_cuda_allocated_bytes": 120,
        "after_base_load_observed_cuda_reserved_bytes": 220,
        "after_design_unload_cuda_allocated_bytes": 0,
        "final_cuda_allocated_bytes": 0,
        "final_cuda_reserved_bytes": 0,
        "design_generation_observed_cuda_allocated_bytes": 140,
        "clone_generation_observed_cuda_allocated_bytes": 150,
        "point_samples_labeled_as_peaks": False,
    }
    timings = {
        "voice_design_load": 1.0,
        "voice_design_generation": 1.0,
        "base_load": 1.0,
        "clone_prompt": 1.0,
        "clone_generation": 1.0,
        "total_worker": 6.0,
    }
    predecessor_events = list(r7.EXPECTED_PREDECESSOR_EVENTS)
    runtime_events = list(r7.EXPECTED_RUNTIME_PHASE_EVENTS)
    return {
        "schema": "qwen3_tts_voice_forge_worker_resource_evidence_v7",
        "status": "WORKER_REPORTED_PARENT_RECONCILIATION_REQUIRED",
        "semantic_binding_sha256": r7.evidence_subject_sha256(s),
        "worker_reported_telemetry": telemetry,
        "worker_reported_telemetry_sha256": r7.canonical_sha256(telemetry),
        "worker_reported_timings_seconds": timings,
        "worker_reported_timings_sha256": r7.canonical_sha256(timings),
        "predecessor_events": predecessor_events,
        "predecessor_events_sha256": r7.canonical_sha256(predecessor_events),
        "runtime_phase_events": runtime_events,
        "runtime_phase_events_sha256": r7.canonical_sha256(runtime_events),
    }


def fake_identity(seed: str = "a") -> dict:
    return {
        "volume_serial_hex": seed * 16,
        "file_id_hex": seed * 32,
        "normalized_final_path_sha256": H,
    }


def parent_resource(value: dict | None = None, child: dict | None = None):
    s = value or semantic()
    worker_value = child or worker_resource(s)
    stdout_row = {
        "role": "worker_stdout",
        "path": "private/worker.stdout",
        "bytes": 17,
        "sha256": H,
        "windows_file_identity": fake_identity("a"),
    }
    stderr_row = {
        "role": "worker_stderr",
        "path": "private/worker.stderr",
        "bytes": 0,
        "sha256": H2,
        "windows_file_identity": fake_identity("b"),
    }
    observation = {
        "schema": "qwen3_tts_voice_forge_parent_job_observation_v7",
        "observed_by_parent_not_child": True,
        "windows_job_assigned_before_resume": True,
        "primary_worker_exit_code": 0,
        "job_termination_requested_after_primary_exit": True,
        "active_processes_after_termination": 0,
        "process_tree_quiescent_before_finalization": True,
        "quiescence_observed_utc": "2026-08-10T12:00:10Z",
        "finalization_started_utc": "2026-08-10T12:00:11Z",
        "parent_wall_seconds": 8.0,
        "peak_process_memory_used_bytes": 4_000,
        "peak_job_memory_used_bytes": 5_000,
        "io_read_operation_count": 1,
        "io_write_operation_count": 1,
        "io_read_bytes": 1,
        "io_write_bytes": 1,
        "worker_stdout_bytes": stdout_row["bytes"],
        "worker_stdout_sha256": stdout_row["sha256"],
        "worker_stderr_bytes": stderr_row["bytes"],
        "worker_stderr_sha256": stderr_row["sha256"],
        "primary_worker_pid": 1234,
        "parent_pid": 1233,
        "worker_path": s["entry_worker_path"],
        "worker_sha256": s["entry_worker_sha256"],
        "worker_command_sha256": s["worker_command_sha256"],
        "authorization_sha256": s["execution_authorization_sha256"],
        "worker_instance_nonce_sha256": s["worker_instance_nonce_sha256"],
        "job_kill_on_close_limit_active": True,
        "job_accounting_query_succeeded": True,
        "job_extended_limits_query_succeeded": True,
        "total_processes": 1,
        # A clean primary exit with no surviving descendants can legitimately
        # leave the Job's limit-termination counter at zero.
        "total_terminated_processes": 0,
    }
    evidence = {
        "schema": "qwen3_tts_voice_forge_resource_reconciliation_v7",
        "status": "PARENT_RECONCILED_AFTER_PROCESS_TREE_QUIESCENCE",
        "semantic_binding_sha256": r7.evidence_subject_sha256(s),
        "worker_resource_evidence_sha256": s["resource_evidence_sha256"],
        "parent_job_observation": observation,
        "parent_job_observation_sha256": r7.canonical_sha256(observation),
        "worker_only_telemetry_accepted_as_parent_truth": False,
        "reconciliation_passed": True,
    }
    claim = {"worker_pid": 1234}
    return evidence, worker_value, claim, stdout_row, stderr_row


class AuditDecisionTests(unittest.TestCase):
    def _write_audit(self, root: Path, *, decision: str = "ACCEPT_STATIC_ONLY", authored: bool = False):
        report = root / "System/Docs/r7-independent-audit.md"
        report.parent.mkdir(parents=True)
        report.write_bytes(b"independent static report\n")
        manifest_hash = "a" * 64
        inventory_hash = "b" * 64
        subject = r7.audit_subject(
            manifest_path=r7.R7_PAYLOAD_MANIFEST_REL.as_posix(),
            manifest_sha256=manifest_hash,
            inventory_sha256=inventory_hash,
        )
        value = {
            "schema": "qwen3_tts_voice_forge_independent_static_audit_v7",
            "status": "FINAL",
            "authoritative_decision": decision,
            "static_only": True,
            "runtime_execution_performed": False,
            "audit_authorizes_execution": False,
            "unresolved_blockers": [],
            **subject,
            "audit_report_path": "System/Docs/r7-independent-audit.md",
            "audit_report_sha256": r7.sha256_file(report),
            "subject_sha256": r7.canonical_sha256(subject),
            "auditor_identity_sha256": H,
            "auditor_separation": {
                "fresh_independent_process": True,
                "subject_sources_authored_by_auditor": authored,
            },
            "completed_utc": "2026-08-10T12:00:00Z",
        }
        path = root / "RecoverySprint/r7-audit/decision.json"
        path.parent.mkdir(parents=True)
        path.write_bytes(r7.canonical_bytes(value) + b"\n")
        return path, r7.sha256_file(path), manifest_hash, inventory_hash

    def test_exact_independent_static_acceptance_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, digest, manifest_hash, inventory_hash = self._write_audit(root)
            audit, _evidence = r7.validate_independent_audit_v7(
                project_root=root,
                audit_decision_path=path,
                expected_audit_decision_sha256=digest,
                expected_manifest_sha256=manifest_hash,
                expected_inventory_sha256=inventory_hash,
            )
            self.assertEqual(audit["authoritative_decision"], "ACCEPT_STATIC_ONLY")

    def test_rejected_audit_cannot_be_laundered(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, digest, manifest_hash, inventory_hash = self._write_audit(
                root, decision="REJECT"
            )
            with self.assertRaises(r7.R7GuardError):
                r7.validate_independent_audit_v7(
                    project_root=root,
                    audit_decision_path=path,
                    expected_audit_decision_sha256=digest,
                    expected_manifest_sha256=manifest_hash,
                    expected_inventory_sha256=inventory_hash,
                )

    def test_subject_author_auditor_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, digest, manifest_hash, inventory_hash = self._write_audit(
                root, authored=True
            )
            with self.assertRaises(r7.R7GuardError):
                r7.validate_independent_audit_v7(
                    project_root=root,
                    audit_decision_path=path,
                    expected_audit_decision_sha256=digest,
                    expected_manifest_sha256=manifest_hash,
                    expected_inventory_sha256=inventory_hash,
                )


class EvaluatorTests(unittest.TestCase):
    def test_sealed_limits_and_complete_collision_rows_pass(self):
        value = evaluator()
        self.assertEqual(
            r7.validate_evaluator_evidence(
                value,
                semantic_binding=semantic(),
                project_root=ROOT,
                expected_collision_subjects={("resident.voice", "resident")},
            ),
            value,
        )

    def test_nonfinite_and_out_of_range_values_rejected(self):
        for hostile in (float("nan"), float("inf"), 2.0):
            value = evaluator()
            value["asr_and_speech"]["clone"]["speech_probability"] = hostile
            with self.assertRaises(r7.R7GuardError):
                r7.validate_evaluator_evidence(
                    value,
                    semantic_binding=semantic(),
                    project_root=ROOT,
                    expected_collision_subjects={("resident.voice", "resident")},
                )

    def test_worker_selected_threshold_rejected(self):
        value = evaluator()
        value["asr_and_speech"]["clone"]["maximum_word_error_rate"] = 0.99
        with self.assertRaises(r7.R7GuardError):
            r7.validate_evaluator_evidence(
                value,
                semantic_binding=semantic(),
                project_root=ROOT,
                expected_collision_subjects={("resident.voice", "resident")},
            )

    def test_missing_collision_subject_and_forged_maximum_rejected(self):
        for mutation in ("missing", "maximum"):
            value = evaluator()
            if mutation == "missing":
                value["collision_corpus"]["collision_results"] = []
                value["collision_corpus"]["collision_results_sha256"] = r7.canonical_sha256([])
            else:
                value["collision_corpus"]["maximum_observed_similarity"] = 0.1
            with self.assertRaises(r7.R7GuardError):
                r7.validate_evaluator_evidence(
                    value,
                    semantic_binding=semantic(),
                    project_root=ROOT,
                    expected_collision_subjects={("resident.voice", "resident")},
                )


class ResourceTests(unittest.TestCase):
    def test_finite_real_worker_telemetry_passes(self):
        value = worker_resource()
        self.assertEqual(
            r7.validate_worker_resource_evidence(value, semantic_binding=semantic()), value
        )

    def test_zero_gpu_and_zero_timing_rejected(self):
        for mode in ("gpu", "timing"):
            value = worker_resource()
            if mode == "gpu":
                value["worker_reported_telemetry"][
                    "clone_generation_observed_cuda_allocated_bytes"
                ] = 0
                value["worker_reported_telemetry_sha256"] = r7.canonical_sha256(
                    value["worker_reported_telemetry"]
                )
            else:
                value["worker_reported_timings_seconds"]["clone_generation"] = 0.0
                value["worker_reported_timings_sha256"] = r7.canonical_sha256(
                    value["worker_reported_timings_seconds"]
                )
            with self.assertRaises(r7.R7GuardError):
                r7.validate_worker_resource_evidence(value, semantic_binding=semantic())

    def test_unclosed_or_reordered_event_sequence_rejected(self):
        value = worker_resource()
        value["runtime_phase_events"] = list(reversed(value["runtime_phase_events"]))
        value["runtime_phase_events_sha256"] = r7.canonical_sha256(
            value["runtime_phase_events"]
        )
        with self.assertRaises(r7.R7GuardError):
            r7.validate_worker_resource_evidence(value, semantic_binding=semantic())

    def test_parent_process_claim_and_log_linkage_passes(self):
        evidence, child, claim, stdout_row, stderr_row = parent_resource()
        self.assertEqual(
            r7.validate_resource_evidence(
                evidence,
                worker_evidence=child,
                semantic_binding=semantic(),
                worker_claim=claim,
                stdout_row=stdout_row,
                stderr_row=stderr_row,
            ),
            evidence,
        )

    def test_wrong_pid_or_stdout_hash_rejected(self):
        for mode in ("pid", "stdout"):
            evidence, child, claim, stdout_row, stderr_row = parent_resource()
            if mode == "pid":
                evidence["parent_job_observation"]["primary_worker_pid"] = 9876
            else:
                evidence["parent_job_observation"]["worker_stdout_sha256"] = H2
            evidence["parent_job_observation_sha256"] = r7.canonical_sha256(
                evidence["parent_job_observation"]
            )
            with self.assertRaises(r7.R7GuardError):
                r7.validate_resource_evidence(
                    evidence,
                    worker_evidence=child,
                    semantic_binding=semantic(),
                    worker_claim=claim,
                    stdout_row=stdout_row,
                    stderr_row=stderr_row,
                )


class AuthorityAndIdentityTests(unittest.TestCase):
    def test_exact_30_row_payload_closure_passes(self):
        predecessor = r7.strict_read_json(
            ROOT / r7.R6_PAYLOAD_MANIFEST_REL,
            expected_sha256=r7.R6_PAYLOAD_MANIFEST_SHA256,
            label="sealed R6 payload",
        )
        additions = {
            r7.R6_PAYLOAD_MANIFEST_REL.as_posix(),
            r7.R6_REJECTED_AUDIT_REL.as_posix(),
            "System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R7_REPAIR_BOUNDARY_20260810.md",
            "tools/qwen3_tts_voice_forge_r7_guards.py",
            "tools/qwen3_tts_original_voice_forge_worker_v7.py",
            "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v7.py",
        }
        required = {row["path"] for row in predecessor["files"]} | additions
        manifest_path = ROOT / r7.R7_PAYLOAD_MANIFEST_REL
        manifest, indexed = r7.verify_payload_manifest(
            project_root=ROOT,
            expected_manifest_sha256=r7.sha256_file(manifest_path),
            required_payloads=required,
        )
        self.assertEqual(len(manifest["files"]), 30)
        self.assertEqual(set(indexed), required)

    def test_ledger_nonce_is_bound_to_expected_authority(self):
        expected = {
            "authorization_sha256": H,
            "authorization_nonce_sha256": H,
            "worker_instance_nonce_sha256": H,
            "independent_audit_decision_sha256": H,
            "independent_audit_subject_sha256": H,
            "independent_auditor_identity_sha256": H,
            "independent_audit_report_sha256": H,
            "payload_manifest_sha256": H,
            "bundle_id": "bundle.r7.test",
            "run_id": "run.r7.test",
            "attempt": "attempt.r7.test",
            "parent_reservation_path": "stable/reservation.json",
            "parent_reservation_sha256": H,
            "verified_worker_path": "tools/worker_v7.py",
            "verified_worker_sha256": H,
            "worker_command_sha256": H,
        }
        ledger = {
            "schema": "qwen3_tts_voice_forge_authorization_ledger_v7",
            "status": "CONSUMED_FOR_ONE_EXACT_PENDING_ATTEMPT",
            "utc": "2026-08-10T12:00:00Z",
            **expected,
        }
        self.assertEqual(r7.validate_parent_ledger(ledger, expected=expected), ledger)
        ledger["worker_instance_nonce_sha256"] = H2
        with self.assertRaises(r7.R7GuardError):
            r7.validate_parent_ledger(ledger, expected=expected)

    def test_file_id_substitution_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "held.bin"
            path.write_bytes(b"held exact bytes")
            row = {
                "role": "held",
                "path": "held.bin",
                "bytes": path.stat().st_size,
                "sha256": r7.sha256_file(path),
                "windows_file_identity": fake_identity("a"),
            }
            indexed = r7.verify_accepted_files(
                project_root=root,
                rows=[row],
                identity_provider=lambda _path: fake_identity("a"),
            )
            self.assertEqual(indexed["held"], row)
            with self.assertRaises(r7.R7GuardError):
                r7.verify_accepted_files(
                    project_root=root,
                    rows=[row],
                    identity_provider=lambda _path: fake_identity("b"),
                )

    def test_strict_json_rejects_duplicate_and_nan(self):
        for payload in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.assertRaises(r7.R7GuardError):
                r7.strict_json_bytes(payload, "hostile")

    def test_worker_claim_precedes_predecessor_module_load(self):
        source = (
            ROOT / "tools/qwen3_tts_original_voice_forge_worker_v7.py"
        ).read_text(encoding="utf-8")
        main_body = source[source.index("def main(") :]
        self.assertLess(
            main_body.index("bootstrap_claim_before_predecessor_import"),
            main_body.index("execute_after_claim"),
        )
        execute_body = source[source.index("def execute_after_claim(") :]
        self.assertLess(
            main_body.index("bootstrap_claim_before_predecessor_import"),
            main_body.index("execute_after_claim"),
        )
        self.assertIn("_load_sealed_module(R6_WORKER_REL", execute_body)

    def test_parent_blocks_empty_corpus_before_worker_and_commits_under_leases(self):
        source = (
            ROOT / "tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v7.py"
        ).read_text(encoding="utf-8")
        run_body = source[source.index("def run(") :]
        self.assertLess(
            run_body.index("if not collision_subjects"),
            run_body.index("run_contained_worker_v7("),
        )
        self.assertLess(
            run_body.index("with r7.hold_windows_file_leases("),
            run_body.index("r7.commit_acceptance_with_held_identities("),
        )
        self.assertLess(
            run_body.index("r7.commit_acceptance_with_held_identities("),
            run_body.index("reopen_acceptance_for_later_use("),
        )


if __name__ == "__main__":
    unittest.main()
