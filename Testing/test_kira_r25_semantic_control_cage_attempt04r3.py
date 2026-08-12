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
CONFIG = ROOT / "Avatar/avatar_builder/body_systems/kira_r25_semantic_control_cage_diagnostic_v4r3.json"
WRAPPER = ROOT / "tools/blender_diagnose_kira_r25_semantic_control_cage_v4r3.py"
CONTROLLER = ROOT / "tools/run_kira_r25_semantic_control_cage_v4r3.py"
CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_static_preparation/attempt_04r3/CHECKPOINT.md"
)
R2_AUDIT = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_static_preparation/attempt_04r2/INDEPENDENT_AUDIT.md"
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


class SemanticControlCageAttempt04R3StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.controller = load_module("_test_semantic_controller_v4r3", CONTROLLER)
        fake_bpy = types.ModuleType("bpy")
        prior = sys.modules.get("bpy")
        sys.modules["bpy"] = fake_bpy
        try:
            cls.wrapper = load_module("_test_semantic_wrapper_v4r3", WRAPPER)
        finally:
            if prior is None:
                sys.modules.pop("bpy", None)
            else:
                sys.modules["bpy"] = prior
        cls.wrapper_source = WRAPPER.read_text(encoding="utf-8")
        cls.controller_source = CONTROLLER.read_text(encoding="utf-8")
        cls.config_source = CONFIG.read_text(encoding="utf-8")

    def static_binding(self) -> dict:
        return {
            "state": self.wrapper.STATIC_NATIVE_STATE,
            "final_image_path": r"\\?\C:\Trusted\semantic-controller.exe",
            "bytes": 1048576,
            "sha256": "1" * 64,
            "volume_serial_number": 987654321,
            "file_id_128_hex": "2" * 32,
            "image_file_creation_time_100ns": 133800000000000001,
        }

    def sealed_config_and_row(self) -> tuple[dict, dict]:
        config = copy.deepcopy(self.config)
        config["status"] = self.wrapper.SEALED_STATUS
        config["native_semantic_controller_executable_binding"] = self.static_binding()
        pair = config["afes_v3r3_pair_binding"]
        pair["seal_status"] = "SEALED_FINAL_INDEPENDENTLY_ACCEPTED_V3R3_PAIR"
        pair["required_final_placeholders"] = []
        pair["expected_pair_and_analysis"] = {
            "pair_acceptance_frame_sha256": "3" * 64,
            "run_01_frame_sha256": "4" * 64,
            "run_02_frame_sha256": "5" * 64,
        }
        raw = json.dumps(
            config, ensure_ascii=False, allow_nan=False, sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        row = {
            "path": self.wrapper.CONFIG_RELATIVE_PATH,
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
        }
        return config, row

    def observed_parent(self, binding: dict, parent_pid: int = 701) -> dict:
        device = r"\Device\HarddiskVolume7\Trusted\semantic-controller.exe"
        return {
            "process_id": parent_pid,
            "process_creation_time_100ns": 133800000000000002,
            "windows_session_id": 7,
            "process_image_device_path": device,
            "mapped_image_device_path": device,
            "held_image_device_path": device,
            "final_image_path": binding["final_image_path"],
            "bytes": binding["bytes"], "sha256": binding["sha256"],
            "volume_serial_number": binding["volume_serial_number"],
            "file_id_128_hex": binding["file_id_128_hex"],
            "image_file_creation_time_100ns": binding["image_file_creation_time_100ns"],
        }

    def audit_fixture(self, config: dict, config_row: dict, module) -> dict:
        rows = {
            label: module._row_for(relative)
            for label, relative in module.SUBJECT_PATHS.items()
        }
        rows["attempt04r3_config"] = copy.deepcopy(config_row)
        return {
            "schema": module.AUDIT_SCHEMA,
            "authoritative_decision": copy.deepcopy(module.AUDIT_DECISION),
            "auditor": copy.deepcopy(module.AUDITOR_IDENTITY),
            "subject_manifest": rows,
            "native_controller_executable_binding": copy.deepcopy(
                config["native_semantic_controller_executable_binding"]
            ),
            "native_runtime_lease_review": copy.deepcopy(module.AUDIT_LEASE_REVIEW),
            "findings": {"blocking": []},
            "truth_boundary": copy.deepcopy(module.AUDIT_TRUTH),
        }

    def runtime_lease(self) -> dict:
        return {
            "schema": self.wrapper.RUNTIME_LEASE_SCHEMA,
            "status": self.wrapper.RUNTIME_LEASE_STATUS,
            "authority_owner": self.wrapper.AUDIT_LEASE_REVIEW["authority_owner"],
            "lease_id": "a" * 64,
            "one_shot_nonce": "b" * 64,
            "capability_pipe_instance_id": "c" * 64,
            "persistent_exclusive_reservation_acquired": True,
            "reservation_persisted_before_child_resume": True,
            "lease_and_nonce_consumed_before_capability_write": True,
            "second_issue_or_replay_refused": True,
            "cross_child_reissue_refused": True,
            "child_wrapper_replay_ledger_authority": False,
        }

    def capability_fixture(self):
        config, config_row = self.sealed_config_and_row()
        observed = self.observed_parent(
            config["native_semantic_controller_executable_binding"]
        )
        audit = self.audit_fixture(config, config_row, self.wrapper)
        audit_sha = hashlib.sha256(self.wrapper._canonical_json_bytes(audit)).hexdigest()
        payload = {
            "schema": self.wrapper.CAPABILITY_SCHEMA,
            "status": self.wrapper.CAPABILITY_STATUS,
            "config_sha256": config_row["sha256"],
            "wrapper_sha256": config["bindings"]["execution_wrapper"]["sha256"],
            "native_controller_sha256": config["native_semantic_controller_executable_binding"]["sha256"],
            "accepted_audit_path": self.wrapper.AUDIT_RELATIVE_PATH,
            "accepted_audit_sha256": audit_sha,
            "accepted_audit_subject": audit,
            "native_controller_process_id": observed["process_id"],
            "native_controller_process_creation_time_100ns": observed["process_creation_time_100ns"],
            "native_controller_session_id": observed["windows_session_id"],
            "native_controller_process_image_device_path": observed["process_image_device_path"],
            "native_controller_mapped_image_device_path": observed["mapped_image_device_path"],
            "intended_child_process_id": 702,
            "intended_child_process_creation_time_100ns": 133800000000000003,
            "runtime_lease": self.runtime_lease(),
            "handles": {"capability": 801, "lock_input": 802, "result_output": 803},
            "input_frames": self.wrapper._expected_capability_inputs(
                config["afes_v3r3_pair_binding"]["expected_pair_and_analysis"]
            ),
            "one_frame_then_eof": True,
            "truth_boundary": copy.deepcopy(self.wrapper.CAPABILITY_TRUTH),
        }
        return config, config_row, observed, payload

    def validate_capability(self, config, config_row, observed, payload, **overrides):
        real_row_for = self.wrapper._row_for

        def row_for(relative):
            if relative == self.wrapper.CONFIG_RELATIVE_PATH:
                return copy.deepcopy(config_row)
            return real_row_for(relative)

        values = {
            "capability_handle": 801, "lock_handle": 802, "result_handle": 803,
            "config_sha256": config_row["sha256"], "config": config,
            "observed_parent": observed, "child_pid": 702,
            "child_creation_time_100ns": 133800000000000003,
        }
        values.update(overrides)
        with mock.patch.object(self.wrapper, "_row_for", side_effect=row_for):
            return self.wrapper._validate_capability(payload, **values)

    def test_01_identity_is_static_unsealed_and_execution_forbidden(self) -> None:
        self.assertEqual(self.config["schema"], "kira.avatar.r25.semantic_control_cage_diagnostic.v4r3")
        self.assertEqual(self.config["status"], self.wrapper.PREPARATION_STATUS)
        self.assertFalse(self.config["scope"]["blender_execution_authorized"])
        self.assertFalse(self.config["scope"]["controller_execution_authorized"])
        self.assertFalse(self.config["scope"]["native_controller_exists"])

    def test_02_exact_sixteen_placeholders_and_seven_null_slots(self) -> None:
        pair = self.config["afes_v3r3_pair_binding"]
        r2 = json.loads((ROOT / self.config["preserved_attempt04r2_rejection_lineage"]["config"]["path"]).read_text(encoding="utf-8"))
        self.assertEqual(
            pair["required_final_placeholders"],
            r2["afes_v3r3_pair_binding"]["required_final_placeholders"],
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
        self.assertEqual(self.config_source.count(": null"), 7)

    def test_03_all_04r2_subjects_and_rejection_audit_are_byte_preserved(self) -> None:
        expected = {
            "config": (13213, "9921e1448a66075fa45b8c6fd5646a64fa66a38ba461f79b3c805289e59bdbca"),
            "adapter": (19457, "b954a47a7103a9bb4a119cf11c26ce997e16c04ef23069796db627a31b2df766"),
            "wrapper": (32293, "10161701eeccd0476edb1af35b9a635dbffbcc4582d3099da585404c095e5e1b"),
            "controller": (15227, "be8b2dc84fdef89bc65e0b62d2ac637a613c4545f22a4e892a69ac12d7db3567"),
            "test": (22567, "4511ee3c45b83bd2f07edd431ef02cb25e24d4f8f6f78f91e336d528dba7f371"),
            "checkpoint": (4688, "63795762018055adee56483691d3a369c47dae0e02bc52c5ca3169ecb9b0c3e6"),
            "independent_rejection_audit": (12746, "1529eb2cf2e6484f7ce4062f11475a1ced26612c92d144ff1bed322651d2af92"),
        }
        for label, row in self.config["preserved_attempt04r2_rejection_lineage"].items():
            self.assertEqual(digest(ROOT / row["path"]), expected[label], label)
        self.assertEqual(digest(R2_AUDIT), expected["independent_rejection_audit"])

    def test_04_current_bindings_rehash_exactly(self) -> None:
        for label, row in self.config["bindings"].items():
            self.assertEqual(digest(ROOT / row["path"]), (row["bytes"], row["sha256"]), label)

    def test_05_config_native_binding_has_only_immutable_non_null_sentinels(self) -> None:
        binding = self.config["native_semantic_controller_executable_binding"]
        self.assertEqual(set(binding), self.wrapper.STATIC_NATIVE_KEYS)
        self.assertTrue(all(type(value) is str and value.startswith("UNRESOLVED_") for value in binding.values()))
        with self.assertRaisesRegex(
            self.wrapper.R25SemanticControlCageV4R3Error,
            "static_native_executable_binding_not_sealed",
        ):
            self.wrapper._require_static_native_binding(binding)

    def test_06_config_has_no_future_audit_digest_path_or_native_runtime_state(self) -> None:
        forbidden_keys = {
            "accepted_audit_sha256", "accepted_audit_path", "parent_process_id",
            "parent_process_creation_time_100ns", "windows_session_id",
            "intended_child_process_id", "intended_child_process_creation_time_100ns",
            "one_shot_nonce", "lease_id", "capability_pipe_instance_id",
        }
        keys = set()
        stack = [self.config]
        while stack:
            value = stack.pop()
            if type(value) is dict:
                keys.update(value)
                stack.extend(value.values())
            elif type(value) is list:
                stack.extend(value)
        self.assertTrue(forbidden_keys.isdisjoint(keys), forbidden_keys & keys)
        self.assertNotIn(self.wrapper.AUDIT_RELATIVE_PATH, self.config_source)

    def test_07_out_of_band_audit_has_finite_acyclic_serialization(self) -> None:
        config_raw_before = CONFIG.read_bytes()
        config_sha = hashlib.sha256(config_raw_before).hexdigest()
        config_row = {
            "path": self.controller.CONFIG_RELATIVE_PATH,
            "bytes": len(config_raw_before), "sha256": config_sha,
        }
        audit = self.audit_fixture(self.config, config_row, self.controller)
        audit_raw = self.controller._canonical_json_bytes(audit)
        audit_sha = hashlib.sha256(audit_raw).hexdigest()
        parsed = self.controller._parse_out_of_band_audit(
            audit_raw, audit_sha, config_sha, self.config
        )
        self.assertEqual(parsed, audit)
        self.assertEqual(CONFIG.read_bytes(), config_raw_before)
        self.assertNotIn(audit_sha.encode("ascii"), config_raw_before)

    def test_08_audit_hash_decision_native_or_subject_drift_fails(self) -> None:
        raw_config = CONFIG.read_bytes()
        config_row = {
            "path": self.controller.CONFIG_RELATIVE_PATH,
            "bytes": len(raw_config), "sha256": hashlib.sha256(raw_config).hexdigest(),
        }
        for mutation in ("hash", "decision", "native", "subject"):
            audit = self.audit_fixture(self.config, config_row, self.controller)
            if mutation == "decision":
                audit["authoritative_decision"]["status"] = "REJECTED"
                pattern = "decision_not_accepted"
            elif mutation == "native":
                audit["native_controller_executable_binding"]["sha256"] = "f" * 64
                pattern = "native_binding_drift"
            elif mutation == "subject":
                audit["subject_manifest"]["attempt04r3_wrapper"]["sha256"] = "f" * 64
                pattern = "subject_hash_drift"
            else:
                pattern = "sha256_mismatch"
            audit_raw = self.controller._canonical_json_bytes(audit)
            audit_sha = hashlib.sha256(audit_raw).hexdigest()
            if mutation == "hash":
                audit_sha = "f" * 64
            with self.assertRaisesRegex(self.controller.SemanticCageV4R3PlanError, pattern):
                self.controller._parse_out_of_band_audit(
                    audit_raw, audit_sha, config_row["sha256"], self.config
                )

    def test_09_exact_static_and_mapped_parent_identity_fixture_passes(self) -> None:
        binding = self.static_binding()
        observed = self.observed_parent(binding)
        self.assertIs(
            self.wrapper._validate_mapped_parent_identity(binding, observed, 701),
            observed,
        )

    def test_10_static_image_field_drift_fails(self) -> None:
        binding = self.static_binding()
        mutations = {
            "final_image_path": r"\\?\D:\Copy\semantic-controller.exe",
            "bytes": binding["bytes"] + 1, "sha256": "f" * 64,
            "volume_serial_number": binding["volume_serial_number"] + 1,
            "file_id_128_hex": "f" * 32,
            "image_file_creation_time_100ns": binding["image_file_creation_time_100ns"] + 1,
        }
        for key, value in mutations.items():
            with self.subTest(key=key):
                observed = self.observed_parent(binding)
                observed[key] = value
                with self.assertRaisesRegex(
                    self.wrapper.R25SemanticControlCageV4R3Error,
                    "static_identity_mismatch",
                ):
                    self.wrapper._validate_mapped_parent_identity(binding, observed, 701)

    def test_11_reopened_trusted_path_cannot_replace_malicious_mapped_image(self) -> None:
        config, _ = self.sealed_config_and_row()
        binding = config["native_semantic_controller_executable_binding"]
        observed = self.observed_parent(binding)
        observed["process_image_device_path"] = r"\Device\HarddiskVolume9\Evil\semantic-controller.exe"
        observed["mapped_image_device_path"] = r"\Device\HarddiskVolume9\Evil\semantic-controller.exe"
        lease = _Lease(observed)
        with mock.patch.object(self.wrapper.os, "getppid", return_value=701), mock.patch.object(
            self.wrapper, "_pipe_server_pid", return_value=701
        ), mock.patch.object(
            self.wrapper, "_query_and_hold_mapped_parent_identity", return_value=lease
        ), mock.patch.object(
            self.wrapper, "_adopt_pipe",
            side_effect=AssertionError("capability read must remain untouched"),
        ), mock.patch.object(
            self.wrapper, "_query_process_creation_time",
            side_effect=AssertionError("child query must remain untouched"),
        ):
            with self.assertRaisesRegex(
                self.wrapper.R25SemanticControlCageV4R3Error,
                "mapped_image_does_not_equal_held_file",
            ):
                self.wrapper._authorize_mapped_parent_and_runtime_lease(
                    801, 802, 803, "7" * 64, config
                )
        self.assertTrue(lease.closed)

    def test_12_wrong_pipe_server_fails_before_mapped_image_query(self) -> None:
        config, _ = self.sealed_config_and_row()
        with mock.patch.object(self.wrapper.os, "getppid", return_value=701), mock.patch.object(
            self.wrapper, "_pipe_server_pid", return_value=999
        ), mock.patch.object(
            self.wrapper, "_query_and_hold_mapped_parent_identity",
            side_effect=AssertionError("mapped query must not follow wrong server"),
        ):
            with self.assertRaisesRegex(
                self.wrapper.R25SemanticControlCageV4R3Error,
                "pipe_server_is_not_os_parent",
            ):
                self.wrapper._authorize_mapped_parent_and_runtime_lease(
                    801, 802, 803, "7" * 64, config
                )

    def test_13_native_owned_persistent_runtime_lease_is_exact(self) -> None:
        lease = self.runtime_lease()
        self.assertIs(self.wrapper._require_native_runtime_lease(lease), lease)
        for key in (
            "authority_owner", "persistent_exclusive_reservation_acquired",
            "reservation_persisted_before_child_resume",
            "lease_and_nonce_consumed_before_capability_write",
            "second_issue_or_replay_refused", "cross_child_reissue_refused",
            "child_wrapper_replay_ledger_authority",
        ):
            with self.subTest(key=key):
                hostile = copy.deepcopy(lease)
                hostile[key] = "ATTACKER" if key == "authority_owner" else not hostile[key]
                with self.assertRaisesRegex(
                    self.wrapper.R25SemanticControlCageV4R3Error,
                    "native_runtime_lease_binding_mismatch",
                ):
                    self.wrapper._require_native_runtime_lease(hostile)

    def test_14_valid_runtime_capability_binds_exact_audit_and_live_instances(self) -> None:
        config, row, observed, payload = self.capability_fixture()
        self.assertIs(self.validate_capability(config, row, observed, payload), payload)

    def test_15_runtime_lease_field_drift_fails(self) -> None:
        payload_mutations = {
            "config_sha256": "e" * 64,
            "wrapper_sha256": "e" * 64,
            "native_controller_sha256": "e" * 64,
            "accepted_audit_path": "attacker/audit.json",
            "native_controller_process_id": 999,
            "native_controller_process_creation_time_100ns": 1,
            "native_controller_session_id": 99,
            "native_controller_process_image_device_path": r"\Device\Evil",
            "native_controller_mapped_image_device_path": r"\Device\Evil",
            "intended_child_process_id": 999,
            "intended_child_process_creation_time_100ns": 1,
            "handles": {}, "input_frames": [],
        }
        for key, value in payload_mutations.items():
            with self.subTest(key=key):
                config, row, observed, payload = self.capability_fixture()
                payload[key] = value
                with self.assertRaisesRegex(
                    self.wrapper.R25SemanticControlCageV4R3Error,
                    "capability_runtime_binding_mismatch:" + key,
                ):
                    self.validate_capability(config, row, observed, payload)

    def test_16_cross_child_replay_fails_on_exact_pid_and_creation_binding(self) -> None:
        config, row, observed, payload = self.capability_fixture()
        with self.assertRaisesRegex(
            self.wrapper.R25SemanticControlCageV4R3Error,
            "capability_runtime_binding_mismatch:intended_child_process_id",
        ):
            self.validate_capability(
                config, row, observed, payload, child_pid=1702,
                child_creation_time_100ns=233800000000000003,
            )

    def test_17_same_child_second_frame_or_read_fails_then_eof_passes(self) -> None:
        receipt = importlib.import_module("tools.kira_r25_canonical_receipt")
        _, _, _, payload = self.capability_fixture()
        frame = receipt.encode_receipt_frame(payload)
        self.assertEqual(self.wrapper._read_capability_payload(io.BytesIO(frame)), payload)
        for trailing in (b"x", frame):
            with self.subTest(length=len(trailing)):
                with self.assertRaisesRegex(
                    self.wrapper.R25SemanticControlCageV4R3Error,
                    "second_read_or_trailing_frame",
                ):
                    self.wrapper._read_capability_payload(io.BytesIO(frame + trailing))

    def test_18_no_child_local_ledger_claim_and_same_payload_validation_is_pure(self) -> None:
        self.assertNotIn("_CONSUMED_NONCE", self.wrapper_source)
        self.assertNotIn("nonce_replay", self.wrapper_source)
        config, row, observed, payload = self.capability_fixture()
        self.assertIs(self.validate_capability(config, row, observed, payload), payload)
        self.assertIs(self.validate_capability(config, row, observed, payload), payload)
        self.assertFalse(payload["runtime_lease"]["child_wrapper_replay_ledger_authority"])

    def test_19_mapped_main_module_and_process_image_apis_are_mandatory(self) -> None:
        for token in (
            "EnumProcessModulesEx", "GetModuleFileNameExW", "GetMappedFileNameW",
            "GetProcessImageFileNameW", "GetFinalPathNameByHandleW",
            "VOLUME_NAME_NT", "GetFileInformationByHandleEx", "ReadFile",
        ):
            self.assertIn(token, self.wrapper_source)
        self.assertNotIn("QueryFullProcessImageNameW", self.wrapper_source)
        self.assertIn("process_image_before != process_image_after", self.wrapper_source)
        self.assertIn("mapped_before != mapped_after", self.wrapper_source)

    def test_20_native_authorization_precedes_runtime_afes_and_blend(self) -> None:
        start = self.wrapper_source.index("def main()")
        authorize = self.wrapper_source.index("_authorize_mapped_parent_and_runtime_lease(", start)
        runtime = self.wrapper_source.index("_verified_runtime(config)", start)
        bundle = self.wrapper_source.index("_read_bundle(", start)
        extract = self.wrapper_source.index("extract_diagnostic(", start)
        self.assertLess(authorize, runtime)
        self.assertLess(runtime, bundle)
        self.assertLess(bundle, extract)

    def test_21_current_wrapper_and_plan_refuse_before_audit_or_runtime(self) -> None:
        config_sha = digest(CONFIG)[1]
        with self.assertRaisesRegex(
            self.wrapper.R25SemanticControlCageV4R3Error,
            "v4r3_static_preparation_is_not_execution_authority",
        ):
            self.wrapper._read_config(config_sha)
        with self.assertRaisesRegex(
            self.controller.SemanticCageV4R3PlanError,
            "static_v4r3_preparation_is_not_execution_authority",
        ):
            self.controller.build_sealed_execution_plan(
                config_sha, self.controller.AUDIT_RELATIVE_PATH, "0" * 64
            )

    def test_22_python_controller_is_inert_and_cannot_mint_native_lease(self) -> None:
        tree = ast.parse(self.controller_source)
        imported = {
            alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        for forbidden in ("subprocess", "ctypes", "bpy", "secrets", "socket", "msvcrt"):
            self.assertNotIn(forbidden, imported)
        for token in (
            "Popen(", "CreateProcess", "CreatePipe", "CreateNamedPipe",
            "open_osfhandle", "write_bytes(", "write_text(", "mkdir(",
            "WindowsExclusiveReceiptReservation", "save_as_mainfile", "token_hex(",
        ):
            self.assertNotIn(token, self.controller_source)

    def test_23_canonical_audit_rejects_noncanonical_and_duplicate_json(self) -> None:
        config_raw = CONFIG.read_bytes()
        config_row = {
            "path": self.controller.CONFIG_RELATIVE_PATH,
            "bytes": len(config_raw), "sha256": hashlib.sha256(config_raw).hexdigest(),
        }
        audit = self.audit_fixture(self.config, config_row, self.controller)
        pretty = json.dumps(audit, sort_keys=True, indent=2).encode("utf-8")
        with self.assertRaisesRegex(
            self.controller.SemanticCageV4R3PlanError, "not_canonical_object"
        ):
            self.controller._parse_out_of_band_audit(
                pretty, hashlib.sha256(pretty).hexdigest(), config_row["sha256"], self.config
            )
        duplicate = b'{"schema":"x","schema":"y"}'
        with self.assertRaisesRegex(
            self.controller.SemanticCageV4R3PlanError, "duplicate_key"
        ):
            self.controller._parse_out_of_band_audit(
                duplicate, hashlib.sha256(duplicate).hexdigest(), config_row["sha256"], self.config
            )

    def test_24_unique_reserved_paths_are_out_of_config_and_absent(self) -> None:
        values = [
            self.controller.AUDIT_RELATIVE_PATH,
            self.controller.OUTCOME_RELATIVE_PATH,
            self.controller.OUTPUT_RELATIVE_ROOT,
        ]
        self.assertEqual(len(values), len(set(values)))
        self.assertTrue(all("attempt_04r3" in value for value in values))
        self.assertNotIn(self.controller.AUDIT_RELATIVE_PATH, self.config_source)
        for value in values:
            self.assertFalse((ROOT / value).exists(), value)


if __name__ == "__main__":
    unittest.main()
