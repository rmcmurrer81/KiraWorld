from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v3r3.json"
)
WRAPPER_PATH = ROOT / "tools/blender_extract_kira_r25_foundation_afes_transition_rings_execution_v3r3.py"
CONTROLLER_PATH = ROOT / "tools/run_kira_r25_foundation_afes_locked_pair_v3r3.py"
BOOTSTRAP_PATH = ROOT / "tools/run_kira_r25_foundation_afes_locked_pair_bootstrap_v3r3.py"
NATIVE_SOURCE_PATH = ROOT / "tools/native/kira_r25_afes_locked_pair_launcher_v3r3.c"
NATIVE_EXE_PATH = ROOT / "tools/native/kira_r25_afes_locked_pair_launcher_v3r3.exe"
CHECKPOINT_PATH = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution_static_preparation/"
    "attempt_03r3/CHECKPOINT.md"
)
MANIFEST_PATH = CHECKPOINT_PATH.with_name("RETAINED_NATIVE_LOCK_MANIFEST.tsv")
AUDIT_PATH = CHECKPOINT_PATH.with_name("INDEPENDENT_AUDIT.json")
OUTCOME_PATH = CHECKPOINT_PATH.with_name("EXECUTION_OUTCOME.receipt.bin")
OUTPUT_ROOT = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution/attempt_03r3"
)
V3R2_AUDIT = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution_static_preparation/"
    "attempt_03r2/INDEPENDENT_AUDIT.json"
)
HEX64 = re.compile(r"[0-9a-f]{64}")


def digest(path: Path) -> tuple[int, str]:
    value = path.read_bytes()
    return len(value), hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"object expected: {path}")
    return value


def iter_rows(contract: dict):
    tables = (
        ("bindings", contract["bindings"], False),
        ("afes_v5_transitive_rows", contract["afes_v5_transitive_rows"], True),
        (
            "child_runtime_read_closure_completion",
            contract["child_runtime_read_closure_completion"], False,
        ),
        ("locked_pair_attempt_01_preservation", contract["locked_pair_attempt_01_preservation"], False),
        ("locked_pair_attempt_02_preservation", contract["locked_pair_attempt_02_preservation"], False),
        ("locked_pair_v3r1_preservation", contract["locked_pair_v3r1_preservation"], False),
        ("locked_pair_v3r2_preservation", contract["locked_pair_v3r2_preservation"], False),
    )
    for table_name, table, nested in tables:
        if nested:
            for nested_name, nested_table in table.items():
                for label, row in nested_table.items():
                    yield f"{table_name}.{nested_name}.{label}", row
        else:
            for label, row in table.items():
                yield f"{table_name}.{label}", row


def parse_manifest(path: Path) -> list[tuple[str, str, int, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if lines[:2] != [
        "KIRA_R25_AFES_RETAINED_MANIFEST_V3R3\t1",
        "label\tpath\tbytes\tsha256",
    ]:
        raise AssertionError("manifest header drift")
    rows = []
    for line in lines[2:]:
        parts = line.split("\t")
        if len(parts) != 4:
            raise AssertionError("manifest row shape drift")
        rows.append((parts[0], parts[1], int(parts[2]), parts[3]))
    return rows


class LockedPairAttempt03R3StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_json(CONFIG_PATH)
        cls.controller_source = CONTROLLER_PATH.read_text(encoding="utf-8")
        cls.bootstrap_source = BOOTSTRAP_PATH.read_text(encoding="utf-8")
        cls.wrapper_source = WRAPPER_PATH.read_text(encoding="utf-8")
        cls.native_source = NATIVE_SOURCE_PATH.read_text(encoding="utf-8")
        cls.manifest_rows = parse_manifest(MANIFEST_PATH)

    def test_01_identity_is_unique_pending_static_gate(self) -> None:
        self.assertEqual(
            self.config["schema"],
            "kira.avatar.r25.foundation_afes_locked_pair_execution.v3r3",
        )
        self.assertEqual(self.config["attempt_id"], "attempt_03r3")
        self.assertEqual(
            self.config["status"],
            "PENDING_FRESH_INDEPENDENT_AUDIT_READ_ONLY_DIAGNOSTIC_PAIR_ONLY",
        )

    def test_02_unique_append_only_roots(self) -> None:
        self.assertTrue(self.config["append_only_output_root"].endswith("attempt_03r3"))
        self.assertIn("attempt_03r3", self.config["execution_outcome_relative_path"])
        self.assertIn("attempt_03r3", self.config["controller_audit_gate"]["path"])
        self.assertEqual(len({
            self.config["append_only_output_root"],
            self.config["execution_outcome_relative_path"],
            self.config["controller_audit_gate"]["path"],
        }), 3)

    def test_03_v3r2_rejection_audit_is_exactly_preserved(self) -> None:
        self.assertEqual(
            digest(V3R2_AUDIT),
            (9474, "4adc80017080b7010fddd1eeeacb2a2dde4084b8c9550785a35ceb2c17f4c9a1"),
        )

    def test_04_all_v3r2_subjects_are_exactly_preserved(self) -> None:
        expected = {
            "locked_pair_v3r2_contract": (31722, "548df35fb87201513585433230df04449d593dc8106351e0fcb4f146faa2cf37"),
            "locked_pair_v3r2_wrapper": (16874, "a9860f53ae86bf70eb42bac0a358ca4edd70a50738140bac3a5d6ca920ea24cb"),
            "locked_pair_v3r2_controller": (57661, "eaaf26db2bf6473378ce208527d39fec43f2ccf2294c31a8c461bca8dc701c4d"),
            "locked_pair_v3r2_bootstrap": (14266, "505293bbd48ba8dae7bce2af3b316d58b4c26510c96f5fcac5efcbe7ef770102"),
            "locked_pair_v3r2_test": (36001, "5edcccc15d543f0900c705dbfc09d090a94bd193074a0ed2d2f5ee8f83cdd630"),
            "locked_pair_v3r2_checkpoint": (8116, "1963cec6191115f4d17846cca79afead02197651ee21f96033184d7757938881"),
            "locked_pair_v3r2_rejection_audit": (9474, "4adc80017080b7010fddd1eeeacb2a2dde4084b8c9550785a35ceb2c17f4c9a1"),
        }
        for label, expected_digest in expected.items():
            row = self.config["bindings"][label]
            self.assertEqual((row["bytes"], row["sha256"]), expected_digest)
            self.assertEqual(digest(ROOT / row["path"]), expected_digest)

    def test_05_v3r2_preservation_table_is_complete(self) -> None:
        table = self.config["locked_pair_v3r2_preservation"]
        self.assertEqual(set(table), {
            "contract", "wrapper", "controller", "bootstrap", "test",
            "checkpoint", "rejection_audit",
        })
        for key, label in {
            "contract": "locked_pair_v3r2_contract",
            "wrapper": "locked_pair_v3r2_wrapper",
            "controller": "locked_pair_v3r2_controller",
            "bootstrap": "locked_pair_v3r2_bootstrap",
            "test": "locked_pair_v3r2_test",
            "checkpoint": "locked_pair_v3r2_checkpoint",
            "rejection_audit": "locked_pair_v3r2_rejection_audit",
        }.items():
            self.assertEqual(table[key], self.config["bindings"][label])

    def test_06_controller_has_no_execution_import_surface(self) -> None:
        tree = ast.parse(self.controller_source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree) if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports |= {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        }
        self.assertTrue({"os", "pathlib", "subprocess", "ctypes", "threading"}.isdisjoint(imports))
        self.assertNotIn("Popen", self.controller_source)
        self.assertNotIn("CreateProcess", self.controller_source)

    def test_07_old_mutable_authority_global_is_gone(self) -> None:
        self.assertNotIn("BOOTSTRAP_RETAINED_CONTROLLER_SHA256", self.controller_source)
        self.assertNotIn("run_pair_from_bootstrap", self.controller_source)
        self.assertNotIn("locks: Any", self.controller_source)
        self.assertNotIn("locked_paths", self.controller_source)

    def test_08_controller_exports_no_public_execution_api(self) -> None:
        tree = ast.parse(self.controller_source)
        names = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
        self.assertFalse(any(name.startswith("run_pair") or name == "run" for name in names))
        self.assertIn("__all__: tuple[str, ...] = ()", self.controller_source)

    def test_09_bootstrap_refuses_project_path_provenance(self) -> None:
        self.assertIn("__KIRA_NATIVE_BROKER_V3R3__", self.bootstrap_source)
        self.assertIn("<native-retained-bootstrap-v3r3>", self.bootstrap_source)
        self.assertIn("native retained-byte launch required", self.bootstrap_source)
        self.assertNotIn("Path(__file__).resolve", self.bootstrap_source)

    def test_10_bootstrap_has_no_python_lock_class_or_lock_argument(self) -> None:
        self.assertNotRegex(self.bootstrap_source, r"class\s+.*Lock")
        self.assertNotIn("CreateFileW", self.bootstrap_source)
        self.assertNotIn("locked_paths=", self.bootstrap_source)
        self.assertNotIn("locks=", self.bootstrap_source)

    def test_11_controller_call_attributes_are_removed(self) -> None:
        self.assertIn("controller.__dict__.pop(name, None)", self.bootstrap_source)
        self.assertIn("pure_controller_call_attribute_survived_capture", self.bootstrap_source)
        self.assertIn("globals().pop(\"_retained_native_main\", None)", self.bootstrap_source)

    def test_12_native_image_is_real_pe_and_exactly_bound(self) -> None:
        self.assertEqual(NATIVE_EXE_PATH.read_bytes()[:2], b"MZ")
        row = self.config["bindings"]["native_launcher_executable"]
        self.assertEqual(digest(NATIVE_EXE_PATH), (row["bytes"], row["sha256"]))

    def test_13_native_source_is_exactly_bound(self) -> None:
        row = self.config["bindings"]["native_launcher_source"]
        self.assertEqual(digest(NATIVE_SOURCE_PATH), (row["bytes"], row["sha256"]))

    def test_14_native_uses_os_module_path_for_self_identity(self) -> None:
        self.assertIn("GetModuleFileNameW", self.native_source)
        self.assertIn("native_launcher", self.native_source)

    def test_15_native_manifest_is_locked_before_project_python(self) -> None:
        lock_index = self.native_source.index("FILE_SHARE_READ")
        python_index = self.native_source.index("Py_Initialize")
        self.assertLess(lock_index, python_index)
        self.assertIn("BCrypt", self.native_source)

    def test_16_native_state_machine_is_single_use(self) -> None:
        for state_field in (
            "claim_attempted", "claimed", "outcome_reserved",
            "outcome_committed", "next_run_number", "finished",
        ):
            self.assertIn(state_field, self.native_source)
        self.assertIn("claim_once", self.native_source)
        self.assertIn("native_broker_claim_already_attempted", self.native_source)
        self.assertIn("g_state.next_run_number != 3", self.native_source)

    def test_17_native_broker_is_embedded_not_installable(self) -> None:
        self.assertIn("PyImport_AppendInittab", self.native_source)
        self.assertIn("_kira_r25_afes_native_broker", self.native_source)
        self.assertNotIn("PyInit__kira_r25_afes_native_broker", self.bootstrap_source)

    def test_18_job_is_kill_on_close(self) -> None:
        self.assertIn("CreateJobObjectW", self.native_source)
        self.assertIn("JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE", self.native_source)
        self.assertIn("SetInformationJobObject", self.native_source)

    def test_19_job_and_handle_lists_are_creation_attributes(self) -> None:
        self.assertIn("PROC_THREAD_ATTRIBUTE_JOB_LIST", self.native_source)
        self.assertIn("PROC_THREAD_ATTRIBUTE_HANDLE_LIST", self.native_source)
        self.assertIn("UpdateProcThreadAttribute", self.native_source)

    def test_20_child_is_suspended_until_job_containment(self) -> None:
        create = self.native_source.index("CREATE_SUSPENDED")
        resume = self.native_source.index("ResumeThread")
        self.assertLess(create, resume)
        self.assertIn("EXTENDED_STARTUPINFO_PRESENT", self.native_source)

    def test_21_native_cleanup_is_composite(self) -> None:
        for token in (
            "TerminateJobObject", "WaitForSingleObject", "CloseHandle",
            "cleanup_errors", "active_process",
        ):
            self.assertIn(token, self.native_source)

    def test_22_drains_are_bounded_and_joined(self) -> None:
        self.assertIn("CreateThread", self.native_source)
        self.assertIn("wait_and_close_drain", self.native_source)
        self.assertIn("DRAIN_JOIN_MILLISECONDS", self.native_source)
        self.assertIn("size_t max_stdout = 4U * 1024U * 1024U", self.native_source)
        self.assertIn("size_t max_stderr = 4U * 1024U * 1024U", self.native_source)
        self.assertIn("Continue draining even when evidence cannot be kept", self.native_source)

    def test_23_outcome_reservation_has_immediate_failure_boundary(self) -> None:
        reserve = self.bootstrap_source.index("broker.reserve_outcome")
        protected_try = self.bootstrap_source.index("try:", reserve)
        output = self.bootstrap_source.index("broker.create_output_root", protected_try)
        self.assertLess(reserve, protected_try)
        self.assertLess(protected_try, output)
        between = self.bootstrap_source[reserve:protected_try]
        self.assertNotIn("resolve(", between)
        self.assertNotIn("relative_to", between)

    def test_24_exactly_one_outcome_commit_guard(self) -> None:
        self.assertIn("committed = False", self.bootstrap_source)
        self.assertIn("if not committed:", self.bootstrap_source)
        self.assertIn("commit_failure_outcome", self.bootstrap_source)
        self.assertIn("commit_failure_outcome_state_refused", self.native_source)
        self.assertIn("Native finish never retries or creates a second outcome", self.bootstrap_source)

    def test_25_audit_subject_requires_checkpoint_and_native_manifest(self) -> None:
        self.assertEqual(self.config["controller_audit_gate"]["must_bind_exact_subjects"], [
            "contract", "native_launcher", "native_launcher_source",
            "retained_manifest", "bootstrap", "controller", "wrapper",
            "static_test", "checkpoint",
        ])

    def test_26_checkpoint_is_exactly_bound_and_in_recursive_graph(self) -> None:
        row = self.config["bindings"]["v3r3_checkpoint"]
        self.assertEqual(row["path"], CHECKPOINT_PATH.relative_to(ROOT).as_posix())
        self.assertEqual(digest(CHECKPOINT_PATH), (row["bytes"], row["sha256"]))
        self.assertIn(row["path"], {item[1] for item in self.manifest_rows})

    def test_27_manifest_is_out_of_band_to_avoid_hash_cycle(self) -> None:
        self.assertEqual(self.config["external_native_manifest_gate"], {
            "path": MANIFEST_PATH.relative_to(ROOT).as_posix(),
            "sha256_supplied_out_of_band": True,
            "manifest_not_self_bound_by_contract_to_avoid_hash_cycle": True,
            "fresh_audit_must_bind_exact_manifest": True,
        })
        self.assertNotIn("retained_manifest", self.config["bindings"])

    def test_28_manifest_rows_are_label_sorted_unique_and_canonical(self) -> None:
        labels = [row[0] for row in self.manifest_rows]
        paths = [row[1] for row in self.manifest_rows]
        self.assertEqual(labels, sorted(labels))
        self.assertEqual(len(labels), len(set(labels)))
        self.assertEqual(len(paths), len(set(paths)))
        for label, path, byte_count, sha256 in self.manifest_rows:
            self.assertTrue(label)
            self.assertGreaterEqual(byte_count, 0)
            self.assertIsNotNone(HEX64.fullmatch(sha256))
            candidate = Path(path) if Path(path).is_absolute() else ROOT / path
            self.assertEqual(digest(candidate), (byte_count, sha256))

    def test_29_manifest_equals_complete_contract_graph_plus_contract(self) -> None:
        expected_paths = {CONFIG_PATH.relative_to(ROOT).as_posix()}
        expected_paths.update(str(row["path"]) for _, row in iter_rows(self.config))
        observed_paths = {row[1] for row in self.manifest_rows}
        self.assertEqual(observed_paths, expected_paths)

    def test_30_five_v2_transitive_rows_remain_present(self) -> None:
        self.assertEqual(set(self.config["child_runtime_read_closure_completion"]), {
            "r23_preflight_config", "r23_preflight_attempt_04",
            "foundation_qualification", "foundation_topology_audit",
            "foundation_relationship_audit",
        })

    def test_31_every_contract_row_matches_exact_bytes(self) -> None:
        for compound, row in iter_rows(self.config):
            candidate = Path(row["path"])
            if not candidate.is_absolute():
                candidate = ROOT / candidate
            self.assertEqual(digest(candidate), (row["bytes"], row["sha256"]), compound)

    def test_32_wrapper_retains_read_only_child_contract(self) -> None:
        for forbidden in ("bpy.ops.wm.save", "render.render", "export_scene", "save_as_mainfile"):
            self.assertNotIn(forbidden, self.wrapper_source)
        self.assertIn("READ_ONLY_EXTRACTION_COMPLETE_PENDING_PAIR_MATCH", self.wrapper_source)
        self.assertIn("V3R2_REJECTED_AND_NOT_EXECUTED", self.wrapper_source)

    def test_33_no_real_execution_evidence_exists(self) -> None:
        self.assertFalse(OUTPUT_ROOT.exists())
        self.assertFalse(OUTCOME_PATH.exists())

    def test_34_fresh_audit_is_not_self_authored_or_bound_as_accepted(self) -> None:
        self.assertNotIn("accepted_controller_audit", self.config["bindings"])
        self.assertEqual(self.config["controller_audit_gate"]["path"], AUDIT_PATH.relative_to(ROOT).as_posix())
        self.assertTrue(self.config["controller_audit_gate"]["sha256_supplied_out_of_band"])

    def test_35_static_sources_parse_without_subject_execution(self) -> None:
        for path in (CONTROLLER_PATH, BOOTSTRAP_PATH, WRAPPER_PATH, Path(__file__)):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


if __name__ == "__main__":
    unittest.main()
