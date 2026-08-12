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
import struct
import sys
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "Avatar/avatar_builder/body_systems/kira_r25_semantic_control_cage_diagnostic_v4r2.json"
ADAPTER = ROOT / "tools/kira_r25_semantic_control_cage_afes_v3r3_adapter_v4r1.py"
WRAPPER = ROOT / "tools/blender_diagnose_kira_r25_semantic_control_cage_v4r2.py"
CONTROLLER = ROOT / "tools/run_kira_r25_semantic_control_cage_v4r2.py"
CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_static_preparation/attempt_04r2/CHECKPOINT.md"
)
R1_AUDIT = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_static_preparation/attempt_04r1/INDEPENDENT_AUDIT.md"
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


class _Lease:
    def __init__(self, observed):
        self.observed = observed
        self.closed = False

    def close(self):
        self.closed = True


class SemanticControlCageAttempt04R2StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.controller = load_module("_test_semantic_controller_v4r2", CONTROLLER)
        fake_bpy = types.ModuleType("bpy")
        prior = sys.modules.get("bpy")
        sys.modules["bpy"] = fake_bpy
        try:
            cls.wrapper = load_module("_test_semantic_wrapper_v4r2", WRAPPER)
        finally:
            if prior is None:
                sys.modules.pop("bpy", None)
            else:
                sys.modules["bpy"] = prior
        cls.wrapper_source = WRAPPER.read_text(encoding="utf-8")
        cls.controller_source = CONTROLLER.read_text(encoding="utf-8")

    def setUp(self) -> None:
        self.wrapper._CONSUMED_NONCE_SHA256S.clear()

    def native_binding(self, nonce: str = "ab" * 32) -> dict:
        return {
            "state": self.wrapper.NATIVE_BINDING_STATE,
            "final_image_path": r"\\?\C:\Trusted\semantic-controller.exe",
            "bytes": 1048576,
            "sha256": "1" * 64,
            "volume_serial_number": 987654321,
            "file_id_128_hex": "2" * 32,
            "image_file_creation_time_100ns": 133800000000000001,
            "parent_process_creation_time_100ns": 133800000000000002,
            "windows_session_id": 7,
            "authorized_one_shot_run_nonce_sha256": hashlib.sha256(
                bytes.fromhex(nonce)
            ).hexdigest(),
        }

    def sealed_config(self, nonce: str = "ab" * 32) -> dict:
        config = copy.deepcopy(self.config)
        config["status"] = self.wrapper.SEALED_STATUS
        config["native_semantic_controller_binding"] = self.native_binding(nonce)
        pair = config["afes_v3r3_pair_binding"]
        pair["seal_status"] = "SEALED_FINAL_INDEPENDENTLY_ACCEPTED_V3R3_PAIR"
        pair["required_final_placeholders"] = []
        pair["expected_pair_and_analysis"] = {
            "pair_acceptance_frame_sha256": "3" * 64,
            "run_01_frame_sha256": "4" * 64,
            "run_02_frame_sha256": "5" * 64,
        }
        config["future_independent_audit_gate"]["accepted_audit_sha256"] = "6" * 64
        return config

    def observed_identity(self, binding: dict, parent_pid: int = 701) -> dict:
        result = {
            key: binding[key] for key in self.wrapper.NATIVE_IDENTITY_KEYS
        }
        result["process_id"] = parent_pid
        return result

    def capability_payload(
        self, config: dict, *, nonce: str = "ab" * 32, parent_pid: int = 701,
        child_pid: int = 702, child_time: int = 133800000000000003,
        cap: int = 801, lock: int = 802, result: int = 803,
    ) -> dict:
        binding = config["native_semantic_controller_binding"]
        return {
            "schema": self.wrapper.CAPABILITY_SCHEMA,
            "status": self.wrapper.CAPABILITY_STATUS,
            "config_sha256": "7" * 64,
            "wrapper_sha256": config["bindings"]["execution_wrapper"]["sha256"],
            "accepted_audit_sha256": config["future_independent_audit_gate"]["accepted_audit_sha256"],
            "native_controller_sha256": binding["sha256"],
            "native_controller_identity_sha256": self.wrapper._native_identity_sha256(binding),
            "native_controller_process_id": parent_pid,
            "native_controller_process_creation_time_100ns": binding["parent_process_creation_time_100ns"],
            "native_controller_session_id": binding["windows_session_id"],
            "intended_child_process_id": child_pid,
            "intended_child_process_creation_time_100ns": child_time,
            "one_shot_run_nonce": nonce,
            "handles": {"capability": cap, "lock_input": lock, "result_output": result},
            "input_frames": self.wrapper._expected_capability_inputs(
                config["afes_v3r3_pair_binding"]["expected_pair_and_analysis"]
            ),
            "single_read_nonreusable": True,
            "truth_boundary": copy.deepcopy(self.wrapper.CAPABILITY_TRUTH),
        }

    def validate_capability(self, payload: dict, config: dict):
        return self.wrapper._validate_capability(
            payload, capability_handle=801, lock_handle=802, result_handle=803,
            config_sha256="7" * 64, config=config, parent_pid=701,
            child_pid=702, child_creation_time_100ns=133800000000000003,
        )

    def accepted_audit_fixture(self, config: dict) -> dict:
        return {
            "schema": self.controller.AUDIT_SCHEMA,
            "authoritative_decision": copy.deepcopy(self.controller.AUDIT_DECISION),
            "auditor": copy.deepcopy(self.controller.AUDITOR_IDENTITY),
            "subject_manifest": {
                label: self.controller._row_for(relative)
                for label, relative in self.controller.SUBJECT_PATHS.items()
            },
            "native_controller_binding": copy.deepcopy(
                config["native_semantic_controller_binding"]
            ),
            "findings": {"blocking": []},
            "truth_boundary": copy.deepcopy(self.controller.AUDIT_TRUTH),
        }

    def test_01_identity_is_static_unsealed_and_native_controller_absent(self) -> None:
        self.assertEqual(self.config["schema"], "kira.avatar.r25.semantic_control_cage_diagnostic.v4r2")
        self.assertEqual(self.config["attempt_id"], "attempt_04r2_static_unsealed")
        self.assertEqual(self.config["status"], self.wrapper.PREPARATION_STATUS)
        self.assertFalse(self.config["scope"]["blender_execution_authorized"])
        self.assertFalse(self.config["scope"]["controller_execution_authorized"])
        self.assertFalse(self.config["scope"]["native_controller_exists"])

    def test_02_exact_sixteen_placeholders_and_seven_null_slots(self) -> None:
        pair = self.config["afes_v3r3_pair_binding"]
        r1 = json.loads((ROOT / self.config["bindings"]["attempt04r1_config"]["path"]).read_text(encoding="utf-8"))
        self.assertEqual(
            pair["required_final_placeholders"],
            r1["afes_v3r3_pair_binding"]["required_final_placeholders"],
        )
        self.assertEqual(len(pair["required_final_placeholders"]), 16)
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

    def test_03_every_04r1_subject_and_rejection_audit_is_byte_preserved(self) -> None:
        expected = {
            "config": (17956, "ac527161220bfe7eaad29828052567799ce54e106e11096950a0cc78fb8c38dc"),
            "adapter": (19457, "b954a47a7103a9bb4a119cf11c26ce997e16c04ef23069796db627a31b2df766"),
            "wrapper": (18492, "4bfee203edde730e00c23e0a713c317dfea0eb70f742ce4bfe799fc65c283a4c"),
            "controller": (13208, "4fd1faf532dcbc3a43d53b7a552a3d0a388e9568d6652ff669eced5450e70d3b"),
            "test": (20290, "08f1eccb95fa716ffc8a99451e1024652322227d6886b471767021213afb07c3"),
            "checkpoint": (4594, "fd2b2827db3fad70a49dd18f672a78546b42fc80b296d99107e322dd179de748"),
            "independent_rejection_audit": (10403, "a0c7c18b6150e26069ef0c2100b46d9398019c26b0650677d43a332079120967"),
        }
        for label, row in self.config["preserved_attempt04r1_rejection_lineage"].items():
            self.assertEqual(digest(ROOT / row["path"]), expected[label], label)
        self.assertEqual(digest(R1_AUDIT), expected["independent_rejection_audit"])
        self.assertEqual(
            self.config["preserved_attempt04r1_rejection_lineage"]["independent_rejection_audit"]["decision"],
            "REJECTED",
        )

    def test_04_all_current_code_and_dependency_bindings_rehash(self) -> None:
        for label, row in self.config["bindings"].items():
            self.assertEqual(digest(ROOT / row["path"]), (row["bytes"], row["sha256"]), label)

    def test_05_native_binding_has_only_explicit_non_null_sentinels(self) -> None:
        binding = self.config["native_semantic_controller_binding"]
        self.assertEqual(set(binding), self.wrapper.NATIVE_BINDING_KEYS)
        self.assertTrue(all(value is not None for value in binding.values()))
        self.assertTrue(all(type(value) is str and value.startswith("UNRESOLVED_") for value in binding.values()))
        with self.assertRaisesRegex(
            self.wrapper.R25SemanticControlCageV4R2Error,
            "native_controller_binding_not_sealed",
        ):
            self.wrapper._require_sealed_native_binding(binding)

    def test_06_exact_native_identity_fixture_passes(self) -> None:
        binding = self.native_binding()
        observed = self.observed_identity(binding)
        self.assertIs(
            self.wrapper._validate_parent_identity(binding, observed, 701), observed
        )

    def test_07_wrong_path_hash_file_id_volume_bytes_times_session_or_pid_fails(self) -> None:
        binding = self.native_binding()
        mutations = {
            "final_image_path": r"\\?\C:\Attacker\semantic-controller.exe",
            "bytes": binding["bytes"] + 1,
            "sha256": "f" * 64,
            "volume_serial_number": binding["volume_serial_number"] + 1,
            "file_id_128_hex": "e" * 32,
            "image_file_creation_time_100ns": binding["image_file_creation_time_100ns"] + 1,
            "parent_process_creation_time_100ns": binding["parent_process_creation_time_100ns"] + 1,
            "windows_session_id": binding["windows_session_id"] + 1,
            "process_id": 999,
        }
        for key, value in mutations.items():
            with self.subTest(key=key):
                observed = self.observed_identity(binding)
                observed[key] = value
                with self.assertRaisesRegex(
                    self.wrapper.R25SemanticControlCageV4R2Error,
                    "native_controller_(identity|parent_pid)_mismatch",
                ):
                    self.wrapper._validate_parent_identity(binding, observed, 701)

    def test_08_same_filename_at_different_path_and_file_identity_fails(self) -> None:
        binding = self.native_binding()
        observed = self.observed_identity(binding)
        observed["final_image_path"] = r"\\?\D:\Copy\semantic-controller.exe"
        observed["file_id_128_hex"] = "9" * 32
        with self.assertRaisesRegex(
            self.wrapper.R25SemanticControlCageV4R2Error,
            "native_controller_identity_mismatch",
        ):
            self.wrapper._validate_parent_identity(binding, observed, 701)

    def test_09_arbitrary_pipe_server_fails_before_identity_query_or_runtime(self) -> None:
        config = self.sealed_config()
        with mock.patch.object(self.wrapper.os, "getppid", return_value=701), mock.patch.object(
            self.wrapper, "_pipe_server_pid", return_value=999
        ), mock.patch.object(
            self.wrapper, "_query_and_hold_parent_identity",
            side_effect=AssertionError("identity query must not follow wrong server PID"),
        ):
            with self.assertRaisesRegex(
                self.wrapper.R25SemanticControlCageV4R2Error,
                "pipe_server_is_not_os_parent",
            ):
                self.wrapper._authorize_native_parent_and_capability(801, 802, 803, "7" * 64, config)

    def test_10_wrong_parent_image_fails_before_capability_read_runtime_or_input(self) -> None:
        config = self.sealed_config()
        observed = self.observed_identity(config["native_semantic_controller_binding"])
        observed["sha256"] = "f" * 64
        lease = _Lease(observed)
        with mock.patch.object(self.wrapper.os, "getppid", return_value=701), mock.patch.object(
            self.wrapper, "_pipe_server_pid", return_value=701
        ), mock.patch.object(
            self.wrapper, "_query_and_hold_parent_identity", return_value=lease
        ), mock.patch.object(
            self.wrapper, "_adopt_pipe",
            side_effect=AssertionError("capability must not be read for wrong image"),
        ), mock.patch.object(
            self.wrapper, "_query_process_creation_time",
            side_effect=AssertionError("child query must not follow wrong parent image"),
        ):
            with self.assertRaisesRegex(
                self.wrapper.R25SemanticControlCageV4R2Error,
                "identity_mismatch:sha256",
            ):
                self.wrapper._authorize_native_parent_and_capability(801, 802, 803, "7" * 64, config)
        self.assertTrue(lease.closed)

    def test_11_exact_capability_binds_all_hash_process_handle_and_frame_fields(self) -> None:
        config = self.sealed_config()
        payload = self.capability_payload(config)
        self.assertIs(self.validate_capability(payload, config), payload)

    def test_12_self_minted_wrong_nonce_fails_against_config_commitment(self) -> None:
        config = self.sealed_config()
        hostile = self.capability_payload(config, nonce="cd" * 32)
        with self.assertRaisesRegex(
            self.wrapper.R25SemanticControlCageV4R2Error,
            "nonce_not_authorized_by_sealed_config",
        ):
            self.validate_capability(hostile, config)

    def test_13_capability_replay_fails_after_one_success(self) -> None:
        config = self.sealed_config()
        payload = self.capability_payload(config)
        self.validate_capability(payload, config)
        with self.assertRaisesRegex(
            self.wrapper.R25SemanticControlCageV4R2Error, "nonce_replay"
        ):
            self.validate_capability(copy.deepcopy(payload), config)

    def test_14_wrong_child_creation_config_wrapper_audit_native_or_frame_fails(self) -> None:
        cases = {
            "intended_child_process_creation_time_100ns": 1,
            "config_sha256": "8" * 64,
            "wrapper_sha256": "8" * 64,
            "accepted_audit_sha256": "8" * 64,
            "native_controller_sha256": "8" * 64,
            "native_controller_identity_sha256": "8" * 64,
            "input_frames": [],
        }
        for key, value in cases.items():
            with self.subTest(key=key):
                config = self.sealed_config()
                hostile = self.capability_payload(config)
                hostile[key] = value
                with self.assertRaisesRegex(
                    self.wrapper.R25SemanticControlCageV4R2Error,
                    "capability_binding_mismatch:" + key,
                ):
                    self.validate_capability(hostile, config)

    def test_15_capability_reader_accepts_one_canonical_frame_then_eof_only(self) -> None:
        receipt = importlib.import_module("tools.kira_r25_canonical_receipt")
        config = self.sealed_config()
        payload = self.capability_payload(config)
        frame = receipt.encode_receipt_frame(payload)
        self.assertEqual(self.wrapper._read_capability_payload(io.BytesIO(frame)), payload)
        with self.assertRaisesRegex(
            self.wrapper.R25SemanticControlCageV4R2Error,
            "more_than_one_frame",
        ):
            self.wrapper._read_capability_payload(io.BytesIO(frame + b"x"))
        pretty = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
        hostile = struct.pack(">8sIQ32s", b"K25RCPT!", 1, len(pretty), hashlib.sha256(pretty).digest()) + pretty
        with self.assertRaisesRegex(
            self.wrapper.R25SemanticControlCageV4R2Error,
            "not_canonical_object",
        ):
            self.wrapper._read_capability_payload(io.BytesIO(hostile))

    def test_16_current_config_refuses_direct_python_or_blender_invocation(self) -> None:
        with self.assertRaisesRegex(
            self.wrapper.R25SemanticControlCageV4R2Error,
            "v4r2_static_preparation_is_not_execution_authority",
        ):
            self.wrapper._read_config(digest(CONFIG)[1])
        with self.assertRaisesRegex(
            self.controller.SemanticCageV4R2PlanError,
            "static_v4r2_preparation_is_not_execution_authority",
        ):
            self.controller.build_sealed_execution_plan(digest(CONFIG)[1], "0" * 64)

    def test_17_main_orders_native_authorization_before_runtime_and_afes_input(self) -> None:
        start = self.wrapper_source.index("def main()")
        authorize = self.wrapper_source.index("_authorize_native_parent_and_capability(", start)
        runtime = self.wrapper_source.index("_verified_runtime(config)", start)
        bundle = self.wrapper_source.index("_read_bundle(", start)
        extract = self.wrapper_source.index("extract_diagnostic(", start)
        self.assertLess(authorize, runtime)
        self.assertLess(runtime, bundle)
        self.assertLess(bundle, extract)

    def test_18_windows_identity_query_opens_and_holds_process_and_image(self) -> None:
        for token in (
            "OpenProcess", "GetProcessId", "GetProcessTimes",
            "QueryFullProcessImageNameW", "CreateFileW",
            "GetFinalPathNameByHandleW", "GetFileInformationByHandleEx",
            "GetFileTime", "ProcessIdToSessionId", "DuplicateHandle", "ReadFile",
        ):
            self.assertIn(token, self.wrapper_source)
        self.assertIn("PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE", self.wrapper_source)
        self.assertIn("if lease is not None:\n            lease.close()", self.wrapper_source)

    def test_19_inert_controller_has_no_launch_secret_pipe_blender_or_write_ability(self) -> None:
        tree = ast.parse(self.controller_source)
        imported = {
            alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        for forbidden in ("subprocess", "ctypes", "bpy", "secrets", "socket"):
            self.assertNotIn(forbidden, imported)
        for token in (
            "Popen(", "CreatePipe", "CreateNamedPipe", "open_osfhandle",
            "write_bytes(", "write_text(", "mkdir(", "WindowsExclusiveReceiptReservation",
            "save_as_mainfile", "token_hex(", "randbytes(",
        ):
            self.assertNotIn(token, self.controller_source)

    def test_20_canonical_audit_parser_binds_all_subjects_and_native_identity(self) -> None:
        config = self.sealed_config()
        audit = self.accepted_audit_fixture(config)
        raw = self.controller._canonical_json_bytes(audit)
        observed = self.controller._parse_independent_audit(
            raw, hashlib.sha256(raw).hexdigest(), digest(CONFIG)[1], config
        )
        self.assertEqual(observed, audit)
        hostile = copy.deepcopy(audit)
        hostile["native_controller_binding"]["file_id_128_hex"] = "f" * 32
        hostile_raw = self.controller._canonical_json_bytes(hostile)
        with self.assertRaisesRegex(
            self.controller.SemanticCageV4R2PlanError,
            "native_controller_binding_drift",
        ):
            self.controller._parse_independent_audit(
                hostile_raw, hashlib.sha256(hostile_raw).hexdigest(),
                digest(CONFIG)[1], config,
            )

    def test_21_audit_rejects_hash_valid_rejection_extra_or_missing_subject(self) -> None:
        config = self.sealed_config()
        for mutation in ("decision", "extra", "missing"):
            audit = self.accepted_audit_fixture(config)
            if mutation == "decision":
                audit["authoritative_decision"]["status"] = "REJECTED"
                pattern = "decision_not_accepted"
            elif mutation == "extra":
                audit["attacker_alias"] = True
                pattern = "schema_or_shape_drift"
            else:
                audit["subject_manifest"].pop("attempt04r2_wrapper")
                pattern = "subject_manifest_shape"
            raw = self.controller._canonical_json_bytes(audit)
            with self.assertRaisesRegex(self.controller.SemanticCageV4R2PlanError, pattern):
                self.controller._parse_independent_audit(
                    raw, hashlib.sha256(raw).hexdigest(), digest(CONFIG)[1], config
                )

    def test_22_reserved_audit_outcome_and_evidence_paths_are_unique_and_absent(self) -> None:
        paths = self.config["append_only_execution_paths"]
        values = [paths["independent_audit"], paths["outcome_receipt"], paths["evidence_root"]]
        self.assertEqual(len(values), len(set(values)))
        self.assertTrue(all("attempt_04r2" in value for value in values))
        for value in values:
            self.assertFalse((ROOT / value).exists(), value)


if __name__ == "__main__":
    unittest.main()
