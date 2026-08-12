from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REJECTED_PROBE_PATH = ROOT / "tools" / "run_blackwell_import_component_isolation_probe.py"
REJECTED_FINALIZER_PATH = (
    ROOT
    / "tools"
    / "run_persistent_blackwell_protocol_import_only_control_pending_defender_state_v2.py"
)
PROBE_PATH = ROOT / "tools" / "run_blackwell_import_component_isolation_probe_v2.py"
FINALIZER_PATH = (
    ROOT
    / "tools"
    / "run_persistent_blackwell_protocol_import_only_control_pending_defender_state_v3.py"
)
REJECTED_PROBE_SHA256 = "a275123607567db7e9663036829808c51c24e792e3c44445d625a45697ee5153"
REJECTED_FINALIZER_SHA256 = "424869e7a3d90d30dd20381a3adbcf00cd91521ec5cd57c40d0e6f0d8e5eb7c0"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


probe = load_module("blackwell_component_isolation_v2_hardened_test", PROBE_PATH)
finalizer = load_module("blackwell_pending_defender_v3_hardened_test", FINALIZER_PATH)


class BlackwellImportComponentIsolationHardenedRevisionTests(unittest.TestCase):
    def test_rejected_static_evidence_remains_exact(self) -> None:
        self.assertEqual(probe.sha256_file(REJECTED_PROBE_PATH), REJECTED_PROBE_SHA256)
        self.assertEqual(
            probe.sha256_file(REJECTED_FINALIZER_PATH),
            REJECTED_FINALIZER_SHA256,
        )

    def test_both_static_self_checks_pass_without_runtime(self) -> None:
        for result in (probe.static_self_check(), finalizer.static_self_check()):
            self.assertTrue(result["passed"], result)
            for key in (
                "blackwell_runtime_started",
                "torch_imported",
                "cuda_api_invoked",
                "model_loaded",
                "audio_generated",
                "playback_performed",
                "ollama_invoked",
                "defender_queried",
                "defender_changed",
                "candidate_promoted",
                "production_routing_changed",
            ):
                self.assertIs(result[key], False, key)

    def test_timeout_is_clamped_inside_run_function_and_cleanup_fits_bound(self) -> None:
        total, measurement = probe.bounded_timeouts(9999.0)
        self.assertEqual(total, 180.0)
        self.assertEqual(measurement, 120.0)
        maximum_waits = (
            measurement
            + probe.OWNED_PROCESS_TERMINATE_GRACE_SECONDS
            + probe.OWNED_PROCESS_KILL_GRACE_SECONDS
            + (2 * probe.DRAIN_JOIN_SECONDS)
            + 2.0
        )
        self.assertLess(maximum_waits, total)
        source = PROBE_PATH.read_text(encoding="utf-8")
        run_source = source[source.index("\ndef run_one_arm_v2") : source.index("\ndef describe")]
        self.assertIn("bounded_timeouts(", run_source)
        self.assertIn("requested_total_timeout_seconds", run_source)
        self.assertIn("wall_bound_exceeded", run_source)

    def test_direct_child_cli_is_gated_and_self_bounded(self) -> None:
        source = PROBE_PATH.read_text(encoding="utf-8")
        child = source[source.index("\ndef child_arm_v2") : source.index("\ndef _drain_stdout")]
        for marker in (
            "DIAGNOSTIC_OPT_IN",
            "_validate_child_authorization(",
            "expected_authorization_sha256",
        ):
            self.assertIn(marker, child)
        for marker in ("PARENT_NONCE_ENV", "no_active_blender", "os._exit(124)"):
            self.assertIn(marker, source)
        self.assertLess(
            child.index("_validate_child_authorization("),
            child.index("_load_rejected_dependency()"),
        )
        self.assertLess(
            child.index("hard_exit_thread.start()"),
            child.index("_load_rejected_dependency()"),
        )
        self.assertLess(
            child.index("child no-active-Blender gate failed"),
            child.index('importlib.import_module("torch")'),
        )
        authorization = source[
            source.index("\ndef _validate_child_authorization") : source.index(
                "\ndef _emit_pipe_bundle_event"
            )
        ]
        for marker in (
            "os.getppid() == parent_pid",
            "same_attempt_directory",
            "bound_result_path",
            "fresh_record",
        ):
            self.assertIn(marker, authorization)

    def test_child_contains_only_the_declared_torch_import_boundary(self) -> None:
        source = PROBE_PATH.read_text(encoding="utf-8")
        child = source[source.index("\ndef child_arm_v2") : source.index("\ndef _drain_stdout")]
        self.assertIn('importlib.import_module("torch")', child)
        for marker in (
            "torch.cuda",
            'import_module("torchaudio")',
            'import_module("chatterbox")',
            "from_pretrained(",
            "winsound.PlaySound(",
            "sounddevice.play(",
            "sd.play(",
        ):
            self.assertNotIn(marker, child)

    def test_partial_or_uncommitted_child_result_is_never_trusted(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            directory = Path(temporary)
            result_path = directory / "CHILD_RESULT.json"
            ready_path = directory / "CHILD_RESULT_READY.json"
            result_path.write_text('{"torch_imported":', encoding="utf-8")
            result, evidence = probe._safe_child_result(
                result_path,
                ready_path,
                expected_arm="minimal_direct",
                expected_component_spec=probe.ARM_SPECS["minimal_direct"],
                expected_candidate_hashes=probe._load_rejected_dependency().EXPECTED_CANDIDATE_HASHES,
                expected_authorization_sha256="a" * 64,
            )
            self.assertIsNone(result)
            self.assertFalse(evidence["trusted_complete"])
            self.assertFalse(evidence["ready_marker_present"])

    def test_ready_marker_must_bind_exact_result_hash_and_size(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            directory = Path(temporary)
            result_path = directory / "CHILD_RESULT.json"
            ready_path = directory / "CHILD_RESULT_READY.json"
            dependency = probe._load_rejected_dependency()
            payload = {
                "schema_version": 2,
                "artifact_kind": "blackwell_import_component_isolation_v2_child",
                "arm": "minimal_direct",
                "component_spec": probe.ARM_SPECS["minimal_direct"],
                "candidate_hashes": dependency.EXPECTED_CANDIDATE_HASHES,
                "authorization_record_sha256": "a" * 64,
                "child_no_active_blender": {
                    "query_succeeded": True,
                    "active": False,
                },
                "torch_imported": True,
                "cuda_api_invoked": False,
            }
            encoded = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
            result_path.write_bytes(encoded)
            ready_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "artifact_kind": "blackwell_import_component_isolation_v2_child_ready",
                        "arm": "minimal_direct",
                        "authorization_record_sha256": "a" * 64,
                        "child_result_sha256": hashlib.sha256(encoded).hexdigest(),
                        "child_result_bytes": len(encoded),
                    }
                ),
                encoding="utf-8",
            )
            result, evidence = probe._safe_child_result(
                result_path,
                ready_path,
                expected_arm="minimal_direct",
                expected_component_spec=probe.ARM_SPECS["minimal_direct"],
                expected_candidate_hashes=dependency.EXPECTED_CANDIDATE_HASHES,
                expected_authorization_sha256="a" * 64,
            )
            self.assertEqual(result, payload)
            self.assertTrue(evidence["trusted_complete"])
            ready_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "artifact_kind": "blackwell_import_component_isolation_v2_child_ready",
                        "arm": "minimal_direct",
                        "authorization_record_sha256": "a" * 64,
                        "child_result_sha256": "0" * 64,
                        "child_result_bytes": len(encoded),
                    }
                ),
                encoding="utf-8",
            )
            result, evidence = probe._safe_child_result(
                result_path,
                ready_path,
                expected_arm="minimal_direct",
                expected_component_spec=probe.ARM_SPECS["minimal_direct"],
                expected_candidate_hashes=dependency.EXPECTED_CANDIDATE_HASHES,
                expected_authorization_sha256="a" * 64,
            )
            self.assertIsNone(result)
            self.assertFalse(evidence["trusted_complete"])
            self.assertIn("hash", evidence["parse_error"])

    def test_semantic_result_binding_rejects_wrong_arm(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            directory = Path(temporary)
            result_path = directory / "CHILD_RESULT.json"
            ready_path = directory / "CHILD_RESULT_READY.json"
            dependency = probe._load_rejected_dependency()
            payload = {
                "schema_version": 2,
                "artifact_kind": "blackwell_import_component_isolation_v2_child",
                "arm": "worker_context_only",
                "component_spec": probe.ARM_SPECS["worker_context_only"],
                "candidate_hashes": dependency.EXPECTED_CANDIDATE_HASHES,
                "authorization_record_sha256": "b" * 64,
                "child_no_active_blender": {
                    "query_succeeded": True,
                    "active": False,
                },
            }
            encoded = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
            result_path.write_bytes(encoded)
            ready_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "artifact_kind": "blackwell_import_component_isolation_v2_child_ready",
                        "arm": "minimal_direct",
                        "authorization_record_sha256": "b" * 64,
                        "child_result_sha256": hashlib.sha256(encoded).hexdigest(),
                        "child_result_bytes": len(encoded),
                    }
                ),
                encoding="utf-8",
            )
            result, evidence = probe._safe_child_result(
                result_path,
                ready_path,
                expected_arm="minimal_direct",
                expected_component_spec=probe.ARM_SPECS["minimal_direct"],
                expected_candidate_hashes=dependency.EXPECTED_CANDIDATE_HASHES,
                expected_authorization_sha256="b" * 64,
            )
            self.assertIsNone(result)
            self.assertFalse(evidence["trusted_complete"])
            self.assertIn("semantic", evidence["parse_error"])

    def test_timeout_or_missing_result_keeps_child_outcomes_unknown(self) -> None:
        outcomes = probe._child_outcomes(None)
        self.assertFalse(outcomes["evidence_complete"])
        self.assertIsNone(outcomes["torch_import_only"])
        for key, value in outcomes.items():
            if key not in ("evidence_complete", "torch_import_only"):
                self.assertIsNone(value, key)

    def test_child_outcome_contract_rejects_non_boolean_values(self) -> None:
        payload = {
            "torch_imported": True,
            "cuda_api_invoked": False,
            "torchaudio_imported": False,
            "chatterbox_imported": False,
            "model_loaded": False,
            "audio_generated": False,
            "playback_performed": False,
            "ollama_invoked": False,
            "candidate_promoted": False,
            "production_routing_changed": False,
        }
        self.assertIs(probe._child_outcomes(payload)["torch_import_only"], True)
        payload["cuda_api_invoked"] = 0
        malformed = probe._child_outcomes(payload)
        self.assertFalse(malformed["evidence_complete"])
        self.assertIsNone(malformed["torch_import_only"])

    def test_pipe_arm_is_explicitly_a_bundle_not_individual_isolation(self) -> None:
        spec = probe.ARM_SPECS["pipe_drains_phase_fsync_bundle"]
        self.assertTrue(spec["pipe_transport_bundle"])
        self.assertIn("bundle", spec["comparison"])
        self.assertIn("not individually isolated", spec["comparison"])

    def test_drain_errors_prevent_finalized_evidence_and_artifact_hashing(self) -> None:
        source = PROBE_PATH.read_text(encoding="utf-8")
        run_source = source[source.index("\ndef run_one_arm_v2") : source.index("\ndef describe")]
        self.assertIn("drain_errors", run_source)
        self.assertIn("not drains_alive and not drain_errors", run_source)
        self.assertIn("or not drains_finalized", run_source)
        self.assertIn("or not owned_child_exited", run_source)
        for gate in (
            '"exact_torch_import_only"',
            '"outcome_evidence_complete"',
            '"candidate_unchanged"',
            '"wall_bound_not_exceeded"',
            '"drains_finalized_without_error"',
            '"expected_transport_artifacts_present"',
        ):
            self.assertIn(gate, run_source)

    def test_unstarted_drain_thread_is_recorded_without_join_exception(self) -> None:
        metrics: dict[str, object] = {}
        never_started = threading.Thread(target=lambda: None, name="never-started-drain")
        probe._safe_join_drain(
            never_started,
            timeout_seconds=0.0,
            metrics=metrics,
            label="stdout",
        )
        self.assertEqual(metrics["stdout_drain_error"], "thread_was_not_started")

    def test_v3_complete_exact_false_contract_proves_absence(self) -> None:
        self.assertIn("model_loaded", finalizer.REQUIRED_EXACT_FALSE["hello"])
        result = finalizer.classify_prohibited_outcomes_strict(
            finalizer.complete_safe_fixture()
        )
        self.assertTrue(result["prohibited_outcomes_evidence_complete"])
        self.assertIs(result["prohibited_outcomes_absent"], True)

    def test_v3_missing_and_falsey_nonboolean_values_remain_unknown(self) -> None:
        self.assertIs(
            finalizer.classify_prohibited_outcomes_strict({})[
                "prohibited_outcomes_absent"
            ],
            None,
        )
        for source_name, keys in finalizer.REQUIRED_EXACT_FALSE.items():
            for key in keys:
                for invalid in (None, 0, ""):
                    fixture = finalizer.complete_safe_fixture()
                    payload = fixture if source_name == "report" else fixture[source_name]
                    payload[key] = invalid
                    result = finalizer.classify_prohibited_outcomes_strict(fixture)
                    self.assertIs(
                        result["prohibited_outcomes_absent"],
                        None,
                        f"{source_name}.{key}={invalid!r}",
                    )

    def test_v3_truthy_nonboolean_or_true_values_fail_closed(self) -> None:
        for source_name, keys in finalizer.REQUIRED_EXACT_FALSE.items():
            for key in keys:
                for prohibited in (True, 1, "false"):
                    fixture = finalizer.complete_safe_fixture()
                    payload = fixture if source_name == "report" else fixture[source_name]
                    payload[key] = prohibited
                    result = finalizer.classify_prohibited_outcomes_strict(fixture)
                    self.assertIs(
                        result["prohibited_outcomes_absent"],
                        False,
                        f"{source_name}.{key}={prohibited!r}",
                    )

    def test_v3_late_event_cannot_hide_a_prohibited_outcome(self) -> None:
        fixture = finalizer.complete_safe_fixture()
        fixture["phase_events_after_cleanup"].append({"cuda_api_invoked": True})
        result = finalizer.classify_prohibited_outcomes_strict(fixture)
        self.assertTrue(result["prohibited_outcomes_observed"])
        self.assertIs(result["prohibited_outcomes_absent"], False)

    def test_v3_unexpected_payload_location_cannot_hide_prohibited_outcome(self) -> None:
        placements = (
            ("hello", "cuda_api_invoked"),
            ("load_import_only", "candidate_promoted"),
            ("report", "audio_generated"),
        )
        for source_name, key in placements:
            fixture = finalizer.complete_safe_fixture()
            payload = fixture if source_name == "report" else fixture[source_name]
            payload[key] = True
            result = finalizer.classify_prohibited_outcomes_strict(fixture)
            self.assertIs(
                result["prohibited_outcomes_absent"],
                False,
                f"{source_name}.{key}",
            )

    def test_v3_malformed_event_container_is_unknown(self) -> None:
        for malformed in ({}, 0, "", None):
            fixture = finalizer.complete_safe_fixture()
            fixture["phase_events_after_cleanup"] = malformed
            result = finalizer.classify_prohibited_outcomes_strict(fixture)
            self.assertIs(result["prohibited_outcomes_absent"], None, repr(malformed))

    def test_v3_pass_remains_gated_on_cleanup_integrity_and_exact_absence(self) -> None:
        source = FINALIZER_PATH.read_text(encoding="utf-8")
        gate = source[source.index('report["passed"] = (') : source.index(
            'report["status"] ='
        )]
        self.assertIn('report["candidate_unchanged"] is True', gate)
        self.assertIn('report["cleanup_clean"] is True', gate)
        self.assertIn('report["prohibited_outcomes_absent"] is True', gate)


if __name__ == "__main__":
    unittest.main()
