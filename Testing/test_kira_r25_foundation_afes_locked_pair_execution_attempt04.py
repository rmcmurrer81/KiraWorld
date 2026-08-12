from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v4.json"
)
BOOTSTRAP_PATH = ROOT / "tools/launch_kira_r25_foundation_afes_locked_pair_v4.py"
CONTROLLER_PATH = ROOT / "tools/run_kira_r25_foundation_afes_locked_pair_v4.py"
WRAPPER_PATH = ROOT / (
    "tools/blender_extract_kira_r25_foundation_afes_"
    "transition_rings_execution_v4.py"
)
AUDIT_PATH = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution_static_preparation/"
    "attempt_04/INDEPENDENT_AUDIT.json"
)
OUTPUT_ROOT = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution/attempt_04"
)


def load_private(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bootstrap = load_private(BOOTSTRAP_PATH, "_test_afes_pair_v4_bootstrap")
controller = load_private(CONTROLLER_PATH, "_test_afes_pair_v4_controller")
wrapper = load_private(WRAPPER_PATH, "_test_afes_pair_v4_wrapper")
CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def digest(path: Path) -> tuple[int, str]:
    value = path.read_bytes()
    return len(value), hashlib.sha256(value).hexdigest()


class ReadOnlyLedger:
    def read_path(self, path: Path) -> bytes:
        return Path(path).read_bytes()

    def read_exact(self, row: object, *, label: str = "row"):
        assert isinstance(row, dict), label
        path = Path(str(row["path"]))
        if not path.is_absolute():
            path = ROOT / path
        value = path.read_bytes()
        assert len(value) == row["bytes"], label
        assert hashlib.sha256(value).hexdigest() == row["sha256"], label
        return path.resolve(strict=True), value


class Attempt04StaticHostileTests(unittest.TestCase):
    def test_01_identity_and_no_execution_authority(self) -> None:
        self.assertEqual(
            CONTRACT["schema"],
            "kira.avatar.r25.foundation_afes_locked_pair_execution.v4",
        )
        self.assertEqual(CONTRACT["attempt_id"], "attempt_04")
        self.assertEqual(
            CONTRACT["status"],
            "PENDING_FRESH_INDEPENDENT_AUDIT_READ_ONLY_DIAGNOSTIC_PAIR_ONLY",
        )
        self.assertFalse(CONTRACT["scope"]["blend_mutation_allowed"])
        self.assertFalse(CONTRACT["scope"]["blend_save_allowed"])
        self.assertFalse(CONTRACT["scope"]["body_authoring_allowed"])
        self.assertFalse(AUDIT_PATH.exists())
        self.assertFalse(OUTPUT_ROOT.exists())

    def test_02_execution_sources_are_exact(self) -> None:
        for label, row in CONTRACT["execution_sources"].items():
            path = Path(str(row["path"]))
            if not path.is_absolute():
                path = ROOT / path
            self.assertEqual(digest(path), (row["bytes"], row["sha256"]), label)

    def test_03_all_35_recursive_rows_match_and_are_unique(self) -> None:
        closure = CONTRACT["child_project_read_closure"]
        self.assertEqual(len(closure), 35)
        self.assertEqual(len({row["path"] for row in closure.values()}), 35)
        for label, row in closure.items():
            self.assertEqual(
                digest(ROOT / row["path"]), (row["bytes"], row["sha256"]), label
            )

    def test_04_recursive_walk_equals_declared_closure(self) -> None:
        v5 = json.loads((ROOT / CONTRACT["child_project_read_closure"]["afes_v5_config"]["path"]).read_text())
        derived = bootstrap._derive_recursive_child_rows(v5, ReadOnlyLedger())
        declared = {
            row["path"]: row for row in CONTRACT["child_project_read_closure"].values()
        }
        self.assertEqual(derived, declared)
        canonical = bootstrap._canonical_json_bytes(declared)
        self.assertEqual(
            hashlib.sha256(canonical).hexdigest(),
            CONTRACT["recursive_closure_contract"]["canonical_closure_sha256"],
        )

    def test_05_all_five_previously_missing_rows_are_now_present(self) -> None:
        paths = {row["path"] for row in CONTRACT["child_project_read_closure"].values()}
        self.assertTrue(bootstrap.REQUIRED_MISSING_V2_PATHS.issubset(paths))

    def test_06_prior_v3_and_v3r1_bytes_are_preserved(self) -> None:
        for label, row in CONTRACT["preserved_rejected_attempt03"].items():
            self.assertEqual(
                digest(ROOT / row["path"]), (row["bytes"], row["sha256"]), label
            )

    def _accepted_audit(self) -> dict[str, object]:
        contract_bytes = CONTRACT_PATH.read_bytes()
        return {
            "schema": "kira.avatar.r25.foundation_afes_locked_pair_independent_audit.v4",
            "attempt_id": "attempt_04",
            "decision": {
                "accepted": True,
                "code": "ACCEPTED_FOR_ONE_BOUNDED_READ_ONLY_PAIR_ONLY",
                "scope": "ONE_FRESH_LOCKED_AFES_DIAGNOSTIC_PAIR",
            },
            "reviewed_execution_artifacts": {
                "contract": {
                    "path": bootstrap.CONTRACT_RELATIVE_PATH,
                    "bytes": len(contract_bytes),
                    "sha256": hashlib.sha256(contract_bytes).hexdigest(),
                },
                "external_bootstrap": CONTRACT["execution_sources"]["external_bootstrap"],
                "private_controller": CONTRACT["execution_sources"]["private_controller"],
                "child_wrapper": CONTRACT["execution_sources"]["child_wrapper"],
                "static_hostile_test": CONTRACT["execution_sources"]["static_hostile_test"],
                "blender_executable": CONTRACT["execution_sources"]["blender_executable"],
            },
            "recursive_closure_sha256": CONTRACT[
                "recursive_closure_contract"
            ]["canonical_closure_sha256"],
            "truth_boundary": {
                "body_authoring_authorized": False,
                "one_bounded_pair_authorized": True,
                "owner_body_approval": False,
                "static_review_did_not_run_blender": True,
            },
        }

    def test_07_structured_authoritative_audit_accepts_only_exact_object(self) -> None:
        document = self._accepted_audit()
        contract_bytes = CONTRACT_PATH.read_bytes()
        observed = bootstrap._validate_structured_audit(
            audit_bytes=bootstrap._canonical_json_bytes(document),
            contract=CONTRACT,
            expected_contract_sha256=hashlib.sha256(contract_bytes).hexdigest(),
            retained_contract_bytes=contract_bytes,
        )
        self.assertEqual(observed, document)

    def test_08_quoted_acceptance_inside_rejection_cannot_pass(self) -> None:
        document = self._accepted_audit()
        document["decision"] = {
            "accepted": False,
            "code": "REJECTED",
            "scope": "quoted text says ACCEPTED_FOR_ONE_BOUNDED_READ_ONLY_PAIR_ONLY",
        }
        contract_bytes = CONTRACT_PATH.read_bytes()
        with self.assertRaisesRegex(
            bootstrap.LockedPairBootstrapV4Error,
            "authoritative_decision_not_acceptance",
        ):
            bootstrap._validate_structured_audit(
                audit_bytes=bootstrap._canonical_json_bytes(document),
                contract=CONTRACT,
                expected_contract_sha256=hashlib.sha256(contract_bytes).hexdigest(),
                retained_contract_bytes=contract_bytes,
            )

    def test_09_contradictory_or_extra_audit_field_is_rejected(self) -> None:
        document = self._accepted_audit()
        document["contradictory_decision"] = "REJECTED"
        contract_bytes = CONTRACT_PATH.read_bytes()
        with self.assertRaisesRegex(
            bootstrap.LockedPairBootstrapV4Error, "top_level_schema_mismatch"
        ):
            bootstrap._validate_structured_audit(
                audit_bytes=bootstrap._canonical_json_bytes(document),
                contract=CONTRACT,
                expected_contract_sha256=hashlib.sha256(contract_bytes).hexdigest(),
                retained_contract_bytes=contract_bytes,
            )

        numeric = self._accepted_audit()
        numeric["decision"]["accepted"] = 1
        with self.assertRaisesRegex(
            bootstrap.LockedPairBootstrapV4Error,
            "authoritative_decision_not_acceptance",
        ):
            bootstrap._validate_structured_audit(
                audit_bytes=bootstrap._canonical_json_bytes(numeric),
                contract=CONTRACT,
                expected_contract_sha256=hashlib.sha256(contract_bytes).hexdigest(),
                retained_contract_bytes=contract_bytes,
            )

        accepted_bytes = bootstrap._canonical_json_bytes(self._accepted_audit())
        duplicate = accepted_bytes.replace(
            b'"attempt_id":"attempt_04"',
            b'"attempt_id":"attempt_03","attempt_id":"attempt_04"',
        )
        with self.assertRaisesRegex(
            bootstrap.LockedPairBootstrapV4Error, "duplicate_json_key"
        ):
            bootstrap._validate_structured_audit(
                audit_bytes=duplicate,
                contract=CONTRACT,
                expected_contract_sha256=hashlib.sha256(contract_bytes).hexdigest(),
                retained_contract_bytes=contract_bytes,
            )

    def test_10_external_bootstrap_truth_and_private_controller_boundary(self) -> None:
        truth = CONTRACT["runtime_dependency_truth"]
        self.assertTrue(truth["external_bootstrap_already_executing_bytes_cannot_self_prove"])
        self.assertTrue(truth["external_bootstrap_is_explicit_independent_audit_trust_root"])
        self.assertTrue(truth["controller_compiled_from_retained_locked_bytes"])
        self.assertTrue(
            truth["structured_audit_parsed_before_private_controller_compile"]
        )
        self.assertEqual(controller.main(), 2)

    def test_11_partial_lock_failure_invokes_no_body(self) -> None:
        invoked = False

        class Locks:
            active = False
            locked_paths: list[Path] = []
            def __enter__(self):
                self.active = True
                return self
            def add(self, path: Path):
                if self.locked_paths:
                    raise bootstrap.LockedPairBootstrapV4Error("synthetic_lock_failure")
                self.locked_paths.append(path)
            def __exit__(self, *_args):
                self.active = False

        def body(_locks):
            nonlocal invoked
            invoked = True

        with self.assertRaisesRegex(
            bootstrap.LockedPairBootstrapV4Error, "synthetic_lock_failure"
        ):
            bootstrap._with_complete_locks(
                [BOOTSTRAP_PATH, CONTROLLER_PATH], body, lock_factory=Locks
            )
        self.assertFalse(invoked)

    def test_12_ledger_rejects_missing_lock_and_same_length_replacement(self) -> None:
        fake = SimpleNamespace(active=True, locked_paths=[BOOTSTRAP_PATH])
        ledger = bootstrap.LockedByteLedger(fake, [BOOTSTRAP_PATH])
        bad = {
            "path": BOOTSTRAP_PATH.relative_to(ROOT).as_posix(),
            "bytes": BOOTSTRAP_PATH.stat().st_size,
            "sha256": "0" * 64,
        }
        with self.assertRaisesRegex(bootstrap.LockedPairBootstrapV4Error, "binding_drift"):
            ledger.read_exact(bad, label="same_length_attack")
        with self.assertRaisesRegex(
            bootstrap.LockedPairBootstrapV4Error, "ledger_requires_complete"
        ):
            bootstrap.LockedByteLedger(fake, [BOOTSTRAP_PATH, CONTROLLER_PATH])

    def test_13_exception_cleanup_targets_exact_job_tree(self) -> None:
        process = mock.Mock()
        process.pid = 123
        process.poll.return_value = None
        process.wait.return_value = 0
        job = mock.Mock()
        job.assigned_pid = 123
        job.closed = False
        controller._terminate_exact_job_process(process, job)
        job.terminate_tree.assert_called_once_with()
        process.terminate.assert_not_called()
        controller._close_job_exception_safe(job)
        job.close.assert_called_once_with()

    def test_14_child_runner_has_structural_finally_cleanup(self) -> None:
        tree = ast.parse(CONTROLLER_PATH.read_text(encoding="utf-8"))
        function = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_run_child"
        )
        finally_nodes = [node for node in ast.walk(function) if isinstance(node, ast.Try) and node.finalbody]
        self.assertTrue(finally_nodes)
        source = ast.get_source_segment(CONTROLLER_PATH.read_text(encoding="utf-8"), function)
        self.assertIn("_terminate_exact_job_process(process, job)", source)
        self.assertIn("_close_job_exception_safe(job)", source)

    def _valid_payload(self):
        closure = CONTRACT["child_project_read_closure"]
        v5 = json.loads((ROOT / closure["afes_v5_config"]["path"]).read_text())
        v4 = json.loads((ROOT / v5["attempt_04_baseline_config"]["path"]).read_text())
        v3 = json.loads((ROOT / v4["attempt_03_baseline_config"]["path"]).read_text())
        v2 = json.loads((ROOT / v3["attempt_02_baseline_config"]["path"]).read_text())
        topology = "a" * 64
        graph_keys = (
            "attempt_01_topology_core_execution_dependency",
            "attempt_02_hardening_core_execution_dependency",
            "attempt_03_hardening_core_execution_dependency",
            "canonical_receipt_helper",
        )
        source_keys = ("attempt_05_private_loader_core", *graph_keys, "attempt_05_extractor")
        source_reads = [
            {"path": v5["bindings"][key]["path"], "physical_read_count": 1,
             "bytes": v5["bindings"][key]["bytes"], "sha256": v5["bindings"][key]["sha256"]}
            for key in source_keys
        ]
        source_reads.sort(key=lambda row: row["path"])
        inner = {
            "schema": "kira.avatar.r25.foundation_afes_transition_diagnostic.v5",
            "artifact_kind": "READ_ONLY_PRIVATE_EXACT_BYTE_AFES_DIAGNOSTIC",
            "status": "EXTRACTED_UNSEALED_REQUIRES_MATCHING_FRESH_LOCKED_RUN",
            "config_observed_unsealed_by_parent": closure["afes_v5_config"],
            "private_execution_dependencies": {key: v5["bindings"][key] for key in graph_keys},
            "private_source_physical_reads": source_reads,
            "ambient_project_modules_consumed": 0,
            "ambient_dataclasses_decorator_consumed": 0,
            "private_modules_inserted_into_sys_modules": 0,
            "private_receipt_runtime": {
                "receipt_module_name": "_kira_private_canonical_receipt_attempt05",
                "decoded_receipt_class_module": "_kira_private_canonical_receipt_attempt05",
                "dataclass_shim_module_name": "_kira_private_dataclass_shim_attempt05",
                "receipt_or_shim_aliases_ambient_sys_modules": False,
            },
            "foundation_object": v2["foundation_contract"]["object_name"],
            "foundation_mesh": v2["foundation_contract"]["mesh_name"],
            "analysis": {"topology_structure": {"full_normalized_topology_sha256": topology}},
            "topology_sealing": {
                "prior_sealed_expected_full_normalized_topology_digest_available": False,
                "required_matching_fresh_locked_extractions": 2,
                "this_receipt_alone_is_acceptance": False,
                "measured_full_normalized_topology_sha256": topology,
            },
            "read_only_guards": {
                "blend_loaded_exactly": True, "blend_clean_before": True,
                "blend_clean_after": True, "data_block_inventory_unchanged": True,
                "operator_calls_by_this_extractor": 0,
                "edit_calls_by_this_extractor": 0,
                "persistence_calls_by_this_extractor": 0,
                "path_result_writes_by_this_extractor": 0,
            },
            "truth_boundary": v5["truth_boundary"],
        }
        contract_bytes = CONTRACT_PATH.read_bytes()
        environment = {"names": ["A"], "sha256": "b" * 64}
        outer = {
            "schema": "kira.avatar.r25.foundation_afes_locked_extraction_run.v4",
            "status": "READ_ONLY_EXTRACTION_COMPLETE_PENDING_PAIR_MATCH",
            "execution_contract": {
                "path": controller.CONTRACT_RELATIVE_PATH,
                "bytes": len(contract_bytes),
                "sha256": hashlib.sha256(contract_bytes).hexdigest(),
            },
            "accepted_afes_v5_config": closure["afes_v5_config"],
            "accepted_afes_v5_extractor": closure["afes_v5_extractor"],
            "pair_session_nonce": "3" * 64,
            "run_nonce": "4" * 64,
            "run_number": 1,
            "result_pipe_handle": 123,
            "child_pid": 456,
            "parent_pid": 789,
            "environment_observation": environment,
            "inner_attempt05_payload": inner,
            "truth_boundary": list(controller.OUTER_TRUTH_BOUNDARY),
        }
        return outer, v5, v2, environment, contract_bytes

    def test_15_exact_outer_and_inner_payload_schema(self) -> None:
        payload, v5, v2, environment, contract_bytes = self._valid_payload()
        validator = SimpleNamespace(validate_compact_afes_analysis=lambda _value: None)
        inner, topology = controller._validate_exact_child_payload(
            payload=payload, contract=CONTRACT, v5=v5, v2=v2,
            attempt03=validator,
            contract_sha256=hashlib.sha256(contract_bytes).hexdigest(),
            contract_bytes=len(contract_bytes), run_number=1,
            pair_session_nonce="3" * 64, run_nonce="4" * 64,
            result_handle=123, child_pid=456, parent_pid=789,
            environment_observation=environment,
        )
        self.assertIs(inner, payload["inner_attempt05_payload"])
        self.assertEqual(topology, "a" * 64)

    def test_16_payload_extra_key_bytes_or_truth_drift_fails_closed(self) -> None:
        validator = SimpleNamespace(validate_compact_afes_analysis=lambda _value: None)
        for mutation in ("extra", "bytes", "truth", "inner_extra", "boolean_for_zero"):
            payload, v5, v2, environment, contract_bytes = self._valid_payload()
            if mutation == "extra": payload["unexpected"] = True
            elif mutation == "bytes": payload["execution_contract"]["bytes"] += 1
            elif mutation == "truth": payload["truth_boundary"] = ["quoted valid values"]
            elif mutation == "inner_extra":
                payload["inner_attempt05_payload"]["unexpected"] = True
            else:
                payload["inner_attempt05_payload"]["read_only_guards"][
                    "operator_calls_by_this_extractor"
                ] = False
            with self.assertRaises(controller.LockedPairV4Error):
                controller._validate_exact_child_payload(
                    payload=payload, contract=CONTRACT, v5=v5, v2=v2,
                    attempt03=validator,
                    contract_sha256=hashlib.sha256(contract_bytes).hexdigest(),
                    contract_bytes=len(contract_bytes), run_number=1,
                    pair_session_nonce="3" * 64, run_nonce="4" * 64,
                    result_handle=123, child_pid=456, parent_pid=789,
                    environment_observation=environment,
                )

    def test_17_environment_and_platform_dependency_truth_are_exact(self) -> None:
        self.assertEqual(CONTRACT["process_contract"], bootstrap._expected_process_contract())
        truth = CONTRACT["runtime_dependency_truth"]
        self.assertFalse(truth[
            "windows_system_dlls_and_blender_bundled_dynamic_runtime_files_individually_sealed"
        ])
        self.assertTrue(truth[
            "windows_system_dlls_and_blender_bundled_dynamic_runtime_files_are_platform_dependencies"
        ])
        self.assertFalse(truth["network_dependency_expected"])
        self.assertFalse(truth["model_dependency_expected"])

    def test_18_no_ambient_project_import_and_wrapper_delays_bpy(self) -> None:
        for path in (BOOTSTRAP_PATH, CONTROLLER_PATH, WRAPPER_PATH):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertFalse(any(alias.name == "tools" or alias.name.startswith("tools.") for alias in node.names))
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse((node.module or "") == "tools" or (node.module or "").startswith("tools."))
        prefix = WRAPPER_PATH.read_text(encoding="utf-8").split("def _real_blender_bpy", 1)[0]
        self.assertNotIn("import bpy", prefix)

    def test_19_append_only_and_receipt_truth_does_not_overclaim(self) -> None:
        acceptance = CONTRACT["pair_acceptance"]
        self.assertTrue(acceptance["fixed_root_second_use_is_rejected"])
        self.assertTrue(acceptance["pre_reservation_failure_has_no_receipt"])
        self.assertTrue(acceptance[
            "abrupt_process_or_storage_failure_can_prevent_failure_receipt"
        ])
        source = CONTROLLER_PATH.read_text(encoding="utf-8")
        self.assertIn("os.O_EXCL", source)
        self.assertIn("exist_ok=False", source)

    def test_20_static_checks_created_no_blender_or_pair_evidence(self) -> None:
        self.assertFalse(AUDIT_PATH.exists())
        self.assertFalse(OUTPUT_ROOT.exists())


if __name__ == "__main__":
    unittest.main()
