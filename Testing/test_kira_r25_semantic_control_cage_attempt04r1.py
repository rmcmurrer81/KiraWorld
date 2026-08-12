from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "Avatar/avatar_builder/body_systems/kira_r25_semantic_control_cage_diagnostic_v4r1.json"
ADAPTER = ROOT / "tools/kira_r25_semantic_control_cage_afes_v3r3_adapter_v4r1.py"
WRAPPER = ROOT / "tools/blender_diagnose_kira_r25_semantic_control_cage_v4r1.py"
CONTROLLER = ROOT / "tools/run_kira_r25_semantic_control_cage_v4r1.py"
CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_static_preparation/attempt_04r1/CHECKPOINT.md"
)


def digest(path: Path) -> tuple[int, str]:
    raw = path.read_bytes()
    return len(raw), hashlib.sha256(raw).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


class SemanticControlCageAttempt04R1StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.adapter = load_module("_test_semantic_adapter_v4r1", ADAPTER)
        cls.controller = load_module("_test_semantic_controller_v4r1", CONTROLLER)
        fake_bpy = types.ModuleType("bpy")
        prior = sys.modules.get("bpy")
        sys.modules["bpy"] = fake_bpy
        try:
            cls.wrapper = load_module("_test_semantic_wrapper_v4r1", WRAPPER)
        finally:
            if prior is None:
                sys.modules.pop("bpy", None)
            else:
                sys.modules["bpy"] = prior
        cls.adapter_source = ADAPTER.read_text(encoding="utf-8")
        cls.wrapper_source = WRAPPER.read_text(encoding="utf-8")
        cls.controller_source = CONTROLLER.read_text(encoding="utf-8")

    @classmethod
    def expected_fixture(cls) -> dict:
        a = cls.adapter
        zero = "0" * 64
        one = "1" * 64
        two = "2" * 64
        three = "3" * 64
        metadata = []
        for number, nonce in ((1, two), (2, three)):
            metadata.append({
                "run_number": number, "pair_session_nonce": one, "run_nonce": nonce,
                "pid": 100 + number, "exit_code": 0, "frame_bytes": 1000 + number,
                "frame_sha256": zero, "payload_sha256": zero,
                "inner_payload_sha256": zero, "topology_sha256": zero,
                "stdout_bytes": 0, "stdout_sha256": zero,
                "stderr_bytes": 0, "stderr_sha256": zero,
            })
        return {
            "pair_schema": a.PAIR_SCHEMA, "pair_status": a.PAIR_STATUS,
            "pair_truth_boundary": copy.deepcopy(a.PAIR_TRUTH_BOUNDARY),
            "pair_acceptance_frame_sha256": zero,
            "execution_contract_binding": {"path": "future/contract.json", "bytes": 1, "sha256": zero},
            "input_snapshot_sha256": zero, "matching_inner_payload_sha256": zero,
            "run_schema": a.RUN_SCHEMA, "run_status": a.RUN_STATUS,
            "run_truth_boundary": copy.deepcopy(a.RUN_TRUTH_BOUNDARY),
            "run_01_frame_sha256": zero, "run_02_frame_sha256": zero,
            "run_01_payload_sha256": zero, "run_02_payload_sha256": zero,
            "pair_session_nonce": one, "run_01_nonce": two, "run_02_nonce": three,
            "exact_run_metadata": metadata,
            "accepted_afes_v5_config": copy.deepcopy(a.AFES_V5_CONFIG_BINDING),
            "accepted_afes_v5_extractor": copy.deepcopy(a.AFES_V5_EXTRACTOR_BINDING),
            "inner_schema": a.INNER_SCHEMA, "inner_artifact_kind": a.INNER_ARTIFACT_KIND,
            "inner_status": a.INNER_STATUS,
            "inner_truth_boundary": copy.deepcopy(a.INNER_TRUTH_BOUNDARY),
            "exact_extraction_verified_inputs": {
                "private_execution_dependencies": {}, "private_source_physical_reads": [],
            },
            "private_receipt_runtime": copy.deepcopy(a.PRIVATE_RECEIPT_RUNTIME),
            "exact_read_only_guards": copy.deepcopy(a.READ_ONLY_GUARDS),
            "foundation_object": "foundation", "foundation_mesh": "mesh",
            "foundation_vertex_count": 1, "foundation_edge_count": 1,
            "foundation_face_count": 1, "foundation_topology_sha256": zero,
            "required_afes_group_names": [], "afes_union_count": 1,
            "afes_union_sha256": zero, "ring_1_count": 1, "ring_1_sha256": zero,
            "ring_2_count": 1, "ring_2_sha256": zero,
            "combined_ring_count": 2, "combined_ring_sha256": zero,
            "locked_vertex_count": 3, "locked_vertex_sha256": zero,
            "exact_topology_structure": {}, "exact_afes_bounds_object_nm": {},
        }

    def accepted_audit_fixture(self) -> dict:
        return {
            "schema": self.controller.AUDIT_SCHEMA,
            "authoritative_decision": copy.deepcopy(self.controller.AUDIT_DECISION),
            "auditor": copy.deepcopy(self.controller.AUDITOR_IDENTITY),
            "subject_manifest": {
                label: self.controller._row_for(relative)
                for label, relative in self.controller.SUBJECT_PATHS.items()
            },
            "findings": {"blocking": []},
            "truth_boundary": copy.deepcopy(self.controller.AUDIT_TRUTH),
        }

    def test_01_identity_is_static_unsealed_and_controller_forbidden(self) -> None:
        self.assertEqual(self.config["schema"], "kira.avatar.r25.semantic_control_cage_diagnostic.v4r1")
        self.assertEqual(self.config["attempt_id"], "attempt_04r1_static_unsealed")
        self.assertEqual(self.config["status"], self.controller.PREPARATION_STATUS)
        self.assertFalse(self.config["scope"]["blender_execution_authorized"])
        self.assertFalse(self.config["scope"]["controller_execution_authorized"])

    def test_02_exact_sixteen_placeholders_and_seven_null_slots(self) -> None:
        pair = self.config["afes_v3r3_pair_binding"]
        self.assertEqual(len(pair["required_final_placeholders"]), 16)
        self.assertEqual(len(set(pair["required_final_placeholders"])), 16)
        self.assertTrue(all(value.startswith("FINAL_") for value in pair["required_final_placeholders"]))
        null_keys = [
            "final_locked_pair_execution_contract_binding",
            "final_locked_pair_independent_audit_binding",
            "final_locked_pair_native_manifest_binding",
            "final_locked_pair_execution_outcome_binding",
            "final_run_01_receipt_binding", "final_run_02_receipt_binding",
            "expected_pair_and_analysis",
        ]
        self.assertTrue(all(pair[key] is None for key in null_keys))
        self.assertEqual(CONFIG.read_text(encoding="utf-8").count(": null"), 7)

    def test_03_attempt04_subjects_and_rejection_are_byte_preserved(self) -> None:
        for label, row in self.config["preserved_attempt04_rejection_lineage"].items():
            path = ROOT / row["path"]
            self.assertEqual(digest(path), (row["bytes"], row["sha256"]), label)
        audit = self.config["preserved_attempt04_rejection_lineage"]["independent_rejection_audit"]
        self.assertEqual(audit["decision"], "REJECTED")

    def test_04_every_current_binding_rehashes_exactly(self) -> None:
        for label, row in self.config["bindings"].items():
            self.assertEqual(
                digest(ROOT / row["path"]), (row["bytes"], row["sha256"]), label
            )

    def test_05_adapter_exact_validation_has_no_runtime_import(self) -> None:
        tree = ast.parse(self.adapter_source)
        imports = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            and not (isinstance(node, ast.ImportFrom) and node.module == "__future__")
        ]
        self.assertEqual(imports, [])
        self.assertNotIn("sys.modules", self.adapter_source)
        self.assertNotIn(".fullmatch(", self.adapter_source)

    def test_06_hostile_sys_modules_re_cannot_change_hex_validation(self) -> None:
        hostile = types.ModuleType("re")
        hostile.fullmatch = lambda *_args, **_kwargs: object()
        prior = sys.modules.get("re")
        sys.modules["re"] = hostile
        marker = mock.Mock(side_effect=AssertionError("adapter attempted an import"))
        try:
            with mock.patch.object(self.wrapper, "_deny_adapter_import", marker):
                module = self.wrapper._dependency_free_adapter(ADAPTER, ADAPTER.read_bytes())
            with self.assertRaises(module.SemanticCageAfesV3R3R1Error):
                module._hex64("NOT-A-SHA256", "hostile")
            self.assertEqual(marker.call_count, 0)
        finally:
            if prior is None:
                sys.modules.pop("re", None)
            else:
                sys.modules["re"] = prior

    def test_07_expected_protocol_literals_pass_only_when_frozen(self) -> None:
        expected = self.expected_fixture()
        result = self.adapter.require_sealed_expected(
            expected, copy.deepcopy(self.adapter.AFES_V5_CONFIG_BINDING),
            copy.deepcopy(self.adapter.AFES_V5_EXTRACTOR_BINDING),
        )
        self.assertIs(result, expected)
        mutations = {
            "pair_schema": "attacker.pair",
            "pair_status": "ATTACKER_PAIR_OK",
            "run_schema": "attacker.run",
            "run_status": "ATTACKER_RUN_OK",
            "inner_schema": "attacker.inner",
            "inner_status": "ATTACKER_INNER_OK",
            "pair_truth_boundary": ["ATTACKER"],
            "run_truth_boundary": ["ATTACKER"],
            "inner_truth_boundary": {"attacker": True},
        }
        for key, value in mutations.items():
            hostile = copy.deepcopy(expected)
            hostile[key] = value
            with self.assertRaisesRegex(
                self.adapter.SemanticCageAfesV3R3R1Error, "not_frozen_literal"
            ):
                self.adapter.require_sealed_expected(
                    hostile, copy.deepcopy(self.adapter.AFES_V5_CONFIG_BINDING),
                    copy.deepcopy(self.adapter.AFES_V5_EXTRACTOR_BINDING),
                )

    def test_08_afes_rows_must_equal_frozen_top_level_verified_bindings(self) -> None:
        expected = self.expected_fixture()
        hostile = copy.deepcopy(self.adapter.AFES_V5_CONFIG_BINDING)
        hostile["sha256"] = "f" * 64
        with self.assertRaisesRegex(
            self.adapter.SemanticCageAfesV3R3R1Error,
            "trusted_afes_v5_config_not_frozen_binding",
        ):
            self.adapter.require_sealed_expected(
                expected, hostile, copy.deepcopy(self.adapter.AFES_V5_EXTRACTOR_BINDING)
            )
        bindings = self.config["bindings"]
        self.assertEqual(
            {key: bindings["accepted_afes_v5_config"][key] for key in ("path", "bytes", "sha256")},
            self.adapter.AFES_V5_CONFIG_BINDING,
        )
        self.assertEqual(
            {key: bindings["accepted_afes_v5_extractor"][key] for key in ("path", "bytes", "sha256")},
            self.adapter.AFES_V5_EXTRACTOR_BINDING,
        )

    def test_09_extra_or_aliased_expected_field_fails_closed(self) -> None:
        expected = self.expected_fixture()
        expected["pair_frame_sha256"] = expected.pop("pair_acceptance_frame_sha256")
        with self.assertRaisesRegex(
            self.adapter.SemanticCageAfesV3R3R1Error, "shape_drift"
        ):
            self.adapter.require_sealed_expected(
                expected, copy.deepcopy(self.adapter.AFES_V5_CONFIG_BINDING),
                copy.deepcopy(self.adapter.AFES_V5_EXTRACTOR_BINDING),
            )

    def _capability_config(self) -> dict:
        config = copy.deepcopy(self.config)
        config["afes_v3r3_pair_binding"]["expected_pair_and_analysis"] = self.expected_fixture()
        config["future_independent_audit_gate"]["accepted_audit_sha256"] = "a" * 64
        return config

    def _capability_payload(self, config: dict, cap: int, lock: int, result: int) -> dict:
        return {
            "schema": self.wrapper.CAPABILITY_SCHEMA,
            "status": self.wrapper.CAPABILITY_STATUS,
            "config_sha256": "b" * 64,
            "accepted_audit_sha256": "a" * 64,
            "controller_binding": copy.deepcopy(config["bindings"]["static_controller"]),
            "wrapper_binding": copy.deepcopy(config["bindings"]["execution_wrapper"]),
            "controller_process_id": os.getppid(),
            "intended_child_process_id": os.getpid(),
            "one_run_nonce": "c" * 64,
            "handles": {"capability": cap, "lock_input": lock, "result_output": result},
            "input_frames": self.wrapper._expected_capability_inputs(
                config["afes_v3r3_pair_binding"]["expected_pair_and_analysis"]
            ),
            "single_read_nonreusable": True,
            "truth_boundary": copy.deepcopy(self.wrapper.CAPABILITY_TRUTH),
        }

    def _capability_runtime(self, frame: bytes):
        class Runtime:
            @staticmethod
            def _require_pipe(_handle, _label):
                return None

            @staticmethod
            def _adopt_pipe(_handle, _flags, _label):
                return io.BytesIO(frame)

        return Runtime()

    def test_10_one_read_parent_owned_capability_is_mandatory_and_exact(self) -> None:
        receipt = importlib.import_module("tools.kira_r25_canonical_receipt")
        config = self._capability_config()
        cap, lock, result = 101, 102, 103
        payload = self._capability_payload(config, cap, lock, result)
        frame = receipt.encode_receipt_frame(payload)
        with mock.patch.object(self.wrapper, "_pipe_server_pid", return_value=os.getppid()):
            observed = self.wrapper._read_controller_capability(
                cap, lock, result, "b" * 64, config,
                self._capability_runtime(frame), receipt,
            )
        self.assertEqual(observed, payload)
        with mock.patch.object(self.wrapper, "_pipe_server_pid", return_value=os.getppid() + 1):
            with self.assertRaisesRegex(
                self.wrapper.R25SemanticControlCageV4R1Error,
                "not_owned_by_parent_controller",
            ):
                self.wrapper._read_controller_capability(
                    cap, lock, result, "b" * 64, config,
                    self._capability_runtime(frame), receipt,
                )
        with mock.patch.object(self.wrapper, "_pipe_server_pid", return_value=os.getppid()):
            with self.assertRaisesRegex(
                self.wrapper.R25SemanticControlCageV4R1Error, "header_truncated"
            ):
                self.wrapper._read_controller_capability(
                    cap, lock, result, "b" * 64, config,
                    self._capability_runtime(b""), receipt,
                )

    def test_11_wrapper_requires_three_distinct_handles_and_capability_first(self) -> None:
        self.assertIn('parser.add_argument("--capability-handle"', self.wrapper_source)
        self.assertLess(
            self.wrapper_source.index("_read_controller_capability(", self.wrapper_source.index("def main")),
            self.wrapper_source.index("_read_bundle(", self.wrapper_source.index("def main")),
        )
        self.assertIn("len(set(handles)) != 3", self.wrapper_source)
        self.assertNotIn("--capability-token", self.wrapper_source)
        self.assertNotIn("--capability-path", self.wrapper_source)

    def test_12_current_wrapper_config_refuses_before_private_runtime(self) -> None:
        with self.assertRaisesRegex(
            self.wrapper.R25SemanticControlCageV4R1Error,
            "v4r1_static_preparation_is_not_execution_authority",
        ):
            self.wrapper._read_config(digest(CONFIG)[1])

    def test_13_exact_canonical_independent_audit_parser_accepts_only_full_subject(self) -> None:
        audit = self.accepted_audit_fixture()
        raw = self.controller._canonical_json_bytes(audit)
        observed = self.controller._parse_independent_audit(
            raw, hashlib.sha256(raw).hexdigest(), digest(CONFIG)[1], self.config
        )
        self.assertEqual(observed, audit)

    def test_14_audit_hash_alone_cannot_authorize_rejection_or_extra_fields(self) -> None:
        for mutation in ("decision", "extra", "subject"):
            audit = self.accepted_audit_fixture()
            if mutation == "decision":
                audit["authoritative_decision"]["status"] = "REJECTED"
                pattern = "decision_not_accepted"
            elif mutation == "extra":
                audit["alias_decision"] = audit["authoritative_decision"]
                pattern = "schema_or_shape_drift"
            else:
                audit["subject_manifest"]["attempt04r1_config"]["sha256"] = "f" * 64
                pattern = "subject_hash_drift"
            raw = self.controller._canonical_json_bytes(audit)
            with self.assertRaisesRegex(self.controller.SemanticCageV4R1PlanError, pattern):
                self.controller._parse_independent_audit(
                    raw, hashlib.sha256(raw).hexdigest(), digest(CONFIG)[1], self.config
                )

    def test_15_noncanonical_duplicate_or_missing_audit_subject_fails(self) -> None:
        audit = self.accepted_audit_fixture()
        pretty = json.dumps(audit, sort_keys=True, indent=2).encode("utf-8")
        with self.assertRaisesRegex(
            self.controller.SemanticCageV4R1PlanError, "not_canonical"
        ):
            self.controller._parse_independent_audit(
                pretty, hashlib.sha256(pretty).hexdigest(), digest(CONFIG)[1], self.config
            )
        missing = self.accepted_audit_fixture()
        missing["subject_manifest"].pop("attempt04r1_wrapper")
        raw = self.controller._canonical_json_bytes(missing)
        with self.assertRaisesRegex(
            self.controller.SemanticCageV4R1PlanError, "subject_manifest_shape"
        ):
            self.controller._parse_independent_audit(
                raw, hashlib.sha256(raw).hexdigest(), digest(CONFIG)[1], self.config
            )
        duplicate = b'{"schema":"x","schema":"y"}'
        with self.assertRaisesRegex(
            self.controller.SemanticCageV4R1PlanError, "duplicate_key"
        ):
            self.controller._parse_independent_audit(
                duplicate, hashlib.sha256(duplicate).hexdigest(), digest(CONFIG)[1], self.config
            )

    def test_16_current_plan_fails_on_static_status_before_audit_path(self) -> None:
        with self.assertRaisesRegex(
            self.controller.SemanticCageV4R1PlanError,
            "static_v4r1_preparation_is_not_execution_authority",
        ):
            self.controller.build_sealed_execution_plan(digest(CONFIG)[1], "0" * 64)

    def test_17_controller_is_static_only_and_was_not_invoked(self) -> None:
        tree = ast.parse(self.controller_source)
        imported = {
            alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        for forbidden in ("subprocess", "ctypes", "bpy", "secrets"):
            self.assertNotIn(forbidden, imported)
        for token in (
            "Popen(", "CreatePipe", "write_bytes(", "write_text(", "mkdir(",
            "WindowsExclusiveReceiptReservation", "save_as_mainfile",
        ):
            self.assertNotIn(token, self.controller_source)

    def test_18_reserved_audit_outcome_and_evidence_paths_are_unique_and_absent(self) -> None:
        paths = self.config["append_only_execution_paths"]
        values = [paths["independent_audit"], paths["outcome_receipt"], paths["evidence_root"]]
        self.assertEqual(len(values), len(set(values)))
        self.assertTrue(all("attempt_04r1" in value for value in values))
        for value in values:
            self.assertFalse((ROOT / value).exists(), value)


if __name__ == "__main__":
    unittest.main()
