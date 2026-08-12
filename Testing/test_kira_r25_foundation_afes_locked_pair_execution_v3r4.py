from __future__ import annotations

"""Hostile static/source gates for the append-only R25 AFES v3r4 repair.

This module deliberately does not import or execute any v3r4 launcher,
controller, bootstrap, Blender wrapper, or Blender process.  It treats those
subjects as bytes/text only.  The first class freezes the rejected v3r3
evidence.  The second class fails red until every v3r4 subject is staged.  The
remaining classes are skipped while the append-only v3r4 package is absent and
become mandatory as soon as it is complete.

The tests are intentionally hostile.  A comment containing a security word is
not normally enough: sensitive requirements are checked in the C function
body that owns the transition, and important checks must occur before the
operation they guard.
"""

import ast
import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]

CONFIG_PATH = ROOT / (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v3r4.json"
)
WRAPPER_PATH = ROOT / (
    "tools/blender_extract_kira_r25_foundation_afes_transition_rings_execution_v3r4.py"
)
CONTROLLER_PATH = ROOT / "tools/run_kira_r25_foundation_afes_locked_pair_v3r4.py"
BOOTSTRAP_PATH = ROOT / (
    "tools/run_kira_r25_foundation_afes_locked_pair_bootstrap_v3r4.py"
)
NATIVE_SOURCE_PATH = ROOT / "tools/native/kira_r25_afes_locked_pair_launcher_v3r4.c"
NATIVE_EXE_PATH = ROOT / "tools/native/kira_r25_afes_locked_pair_launcher_v3r4.exe"
CHECKPOINT_PATH = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution_static_preparation/"
    "attempt_03r4/CHECKPOINT.md"
)
MANIFEST_PATH = CHECKPOINT_PATH.with_name("RETAINED_NATIVE_LOCK_MANIFEST.tsv")
AUDIT_PATH = CHECKPOINT_PATH.with_name("INDEPENDENT_AUDIT.json")
OUTCOME_PATH = CHECKPOINT_PATH.with_name("EXECUTION_OUTCOME.receipt.bin")
OUTPUT_ROOT = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution/attempt_03r4"
)

V3R3_CONFIG = ROOT / (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v3r3.json"
)
V3R3_WRAPPER = ROOT / (
    "tools/blender_extract_kira_r25_foundation_afes_transition_rings_execution_v3r3.py"
)
V3R3_CONTROLLER = ROOT / "tools/run_kira_r25_foundation_afes_locked_pair_v3r3.py"
V3R3_BOOTSTRAP = ROOT / (
    "tools/run_kira_r25_foundation_afes_locked_pair_bootstrap_v3r3.py"
)
V3R3_NATIVE_SOURCE = ROOT / "tools/native/kira_r25_afes_locked_pair_launcher_v3r3.c"
V3R3_NATIVE_EXE = ROOT / "tools/native/kira_r25_afes_locked_pair_launcher_v3r3.exe"
V3R3_TEST = ROOT / "Testing/test_kira_r25_foundation_afes_locked_pair_execution_v3r3.py"
V3R3_CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution_static_preparation/"
    "attempt_03r3/CHECKPOINT.md"
)
V3R3_MANIFEST = V3R3_CHECKPOINT.with_name("RETAINED_NATIVE_LOCK_MANIFEST.tsv")
V3R3_AUDIT = V3R3_CHECKPOINT.with_name("INDEPENDENT_AUDIT.json")
V3R3_OUTCOME = V3R3_CHECKPOINT.with_name("EXECUTION_OUTCOME.receipt.bin")
V3R3_OUTPUT_ROOT = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution/attempt_03r3"
)

V3R4_REQUIRED_SUBJECTS = (
    CONFIG_PATH,
    WRAPPER_PATH,
    CONTROLLER_PATH,
    BOOTSTRAP_PATH,
    NATIVE_SOURCE_PATH,
    NATIVE_EXE_PATH,
    CHECKPOINT_PATH,
    MANIFEST_PATH,
)
V3R4_SOURCE_SUBJECTS = (
    CONFIG_PATH,
    WRAPPER_PATH,
    CONTROLLER_PATH,
    BOOTSTRAP_PATH,
    NATIVE_SOURCE_PATH,
)
V3R4_SOURCE_STAGED = all(path.is_file() for path in V3R4_SOURCE_SUBJECTS)
V3R4_STAGED = all(path.is_file() for path in V3R4_REQUIRED_SUBJECTS)
HEX64 = re.compile(r"[0-9a-f]{64}")


def digest(path: Path) -> tuple[int, str]:
    value = path.read_bytes()
    return len(value), hashlib.sha256(value).hexdigest()


def load_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"JSON object required: {path}")
    return value


def parse_manifest(path: Path) -> list[tuple[str, str, int, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if lines[:2] != [
        "KIRA_R25_AFES_RETAINED_MANIFEST_V3R4\t1",
        "label\tpath\tbytes\tsha256",
    ]:
        raise AssertionError("v3r4 manifest header drift")
    rows: list[tuple[str, str, int, str]] = []
    for line in lines[2:]:
        fields = line.split("\t")
        if len(fields) != 4:
            raise AssertionError("v3r4 manifest row shape drift")
        rows.append((fields[0], fields[1], int(fields[2]), fields[3]))
    return rows


def iter_exact_rows(value: object):
    """Yield every recursively declared exact-byte row in a JSON contract."""

    if isinstance(value, dict):
        if (
            set(("path", "bytes", "sha256")).issubset(value)
            and isinstance(value["path"], str)
            and isinstance(value["bytes"], int)
            and isinstance(value["sha256"], str)
        ):
            yield value
        for child in value.values():
            yield from iter_exact_rows(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_exact_rows(child)


def c_function_body(source: str, name: str) -> str:
    """Return a balanced C function definition body, not a prototype."""

    pattern = re.compile(rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{", re.S)
    match = pattern.search(source)
    if match is None:
        raise AssertionError(f"C function definition missing: {name}")
    opening = source.find("{", match.start())
    depth = 0
    in_string = False
    in_character = False
    escaped = False
    index = opening
    while index < len(source):
        character = source[index]
        if escaped:
            escaped = False
        elif character == "\\" and (in_string or in_character):
            escaped = True
        elif character == '"' and not in_character:
            in_string = not in_string
        elif character == "'" and not in_string:
            in_character = not in_character
        elif not in_string and not in_character:
            if character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 0:
                    return source[opening + 1 : index]
        index += 1
    raise AssertionError(f"unbalanced C function definition: {name}")


def first_c_function_body(source: str, names: tuple[str, ...]) -> tuple[str, str]:
    for name in names:
        try:
            return name, c_function_body(source, name)
        except AssertionError:
            pass
    raise AssertionError(f"none of the required C function definitions exists: {names!r}")


def one_of(text: str, alternatives: tuple[str, ...], message: str) -> None:
    if not any(alternative in text for alternative in alternatives):
        raise AssertionError(f"{message}; expected one of {alternatives!r}")


def before(text: str, guard: str, operation: str, message: str) -> None:
    guard_index = text.find(guard)
    operation_index = text.find(operation)
    if guard_index < 0 or operation_index < 0 or guard_index >= operation_index:
        raise AssertionError(
            f"{message}; guard={guard!r}@{guard_index}, "
            f"operation={operation!r}@{operation_index}"
        )


class FrozenV3R3EvidenceTests(unittest.TestCase):
    """The rejected baseline is evidence and must remain byte-for-byte frozen."""

    def test_001_v3r3_subjects_are_exactly_frozen(self) -> None:
        expected = {
            V3R3_CONFIG: (37419, "421d284d49096be5860b7953e298429ebc43039840f0b1ed3ae98ac34288190e"),
            V3R3_NATIVE_SOURCE: (131644, "be926d46208dec359fe8f66f8f15affff8b576dd75c3ff1c7a5dd247225f7245"),
            V3R3_NATIVE_EXE: (220672, "43997b035c56d29291ce4f1b370476c24fca607ef2fa3fbfa92474092a2f2fce"),
            V3R3_WRAPPER: (17377, "e9f4ab58a0f6734f6ab08c9905a0b620ef2b137079fe05d332201b40b7d529ec"),
            V3R3_CONTROLLER: (31694, "e9e23072d73df77a6c10eabfb7e959e02a0160e458a5aa2b45731c32120658be"),
            V3R3_BOOTSTRAP: (14800, "1453ee497ea88743434be611578bfedb904e0457c719ee345acabd61b6c514b8"),
            V3R3_TEST: (18393, "652cb6da861ae851f210e7e23a1b840f409293b7f7bf0149ffd36590b051a80d"),
            V3R3_CHECKPOINT: (7802, "e39c51a7be2006f3d6fe2269bedf4d2bee3eef5addc96de6ffa2e071d4ae8ed6"),
            V3R3_MANIFEST: (14099, "21d14bb2b40972f8a99d830b307466767b21e2814bcc1418e17dd360fdc37c36"),
        }
        for path, expected_digest in expected.items():
            self.assertEqual(digest(path), expected_digest, str(path))

    def test_002_v3r3_never_acquired_execution_evidence(self) -> None:
        self.assertFalse(V3R3_AUDIT.exists())
        self.assertFalse(V3R3_OUTCOME.exists())
        self.assertFalse(V3R3_OUTPUT_ROOT.exists())

    def test_003_v3r3_still_exhibits_the_detected_job_quiescence_gap(self) -> None:
        source = V3R3_NATIVE_SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("JobObjectBasicAccountingInformation", source)
        self.assertNotIn("ActiveProcesses", source)

    def test_004_v3r3_still_exhibits_the_detected_writer_provenance_gap(self) -> None:
        source = V3R3_NATIVE_SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("CreateNamedPipeW", source)
        self.assertNotIn("GetNamedPipeClientProcessId", source)
        self.assertIn("--result-handle", source)

    def test_005_v3r3_still_exhibits_the_detected_environment_gap(self) -> None:
        body = c_function_body(
            V3R3_NATIVE_SOURCE.read_text(encoding="utf-8"),
            "native_restricted_environment",
        )
        self.assertIn('L"Path"', body)
        self.assertIn('L"TEMP"', body)
        self.assertIn('L"LOCALAPPDATA"', body)


class V3R4PackagePresenceTests(unittest.TestCase):
    def test_010_every_append_only_v3r4_subject_is_staged(self) -> None:
        missing = [path.relative_to(ROOT).as_posix() for path in V3R4_REQUIRED_SUBJECTS if not path.is_file()]
        self.assertEqual(missing, [], "v3r4 hostile suite remains red; missing subjects")


@unittest.skipUnless(V3R4_STAGED, "append-only v3r4 package is not fully staged")
class V3R4ContractAndGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_object(CONFIG_PATH)
        cls.native = NATIVE_SOURCE_PATH.read_text(encoding="utf-8")
        cls.controller = CONTROLLER_PATH.read_text(encoding="utf-8")
        cls.bootstrap = BOOTSTRAP_PATH.read_text(encoding="utf-8")
        cls.wrapper = WRAPPER_PATH.read_text(encoding="utf-8")
        cls.checkpoint = CHECKPOINT_PATH.read_text(encoding="utf-8")
        cls.manifest = parse_manifest(MANIFEST_PATH)

    def test_020_identity_is_unique_and_not_execution_accepted(self) -> None:
        self.assertEqual(
            self.config["schema"],
            "kira.avatar.r25.foundation_afes_locked_pair_execution.v3r4",
        )
        self.assertEqual(self.config["attempt_id"], "attempt_03r4")
        status = str(self.config["status"])
        self.assertIn("PENDING", status)
        self.assertNotIn("EXECUTED", status)
        self.assertNotIn("OWNER_APPROVED", status)

    def test_021_append_only_paths_are_v3r4_only(self) -> None:
        serialized = json.dumps(self.config, sort_keys=True)
        self.assertIn("attempt_03r4", self.config["append_only_output_root"])
        self.assertIn("attempt_03r4", self.config["execution_outcome_relative_path"])
        self.assertIn("attempt_03r4", self.config["controller_audit_gate"]["path"])
        self.assertIn("v3r4", serialized)
        self.assertNotEqual(CONFIG_PATH, V3R3_CONFIG)

    def test_022_contract_names_all_eleven_repair_boundaries(self) -> None:
        text = json.dumps(self.config, sort_keys=True).lower()
        groups = {
            "main-thread/lifecycle": ("main_os_thread", "active_child_count", "run_consumed"),
            "held identity": ("ancestor", "file_id", "python_runtime"),
            "output identity": ("output_root_handle", "reserved_device", "final_handle"),
            "Python authority": ("ambient_import", "capability", "module_search"),
            "writer provenance": ("named_pipe", "root_pid"),
            "Job quiescence": ("activeprocess", "job_quiescence"),
            "drain lifetime": ("drain", "use_after_free"),
            "terminal outcome": ("transaction", "partial_evidence"),
            "environment": ("unique_cache", "minimal_path"),
            "audit parse": ("exact_audit", "checkpoint"),
            "build discipline": ("/w4", "/wx"),
        }
        for label, tokens in groups.items():
            for token in tokens:
                self.assertIn(token, text, f"contract omits {label}: {token}")

    def test_023_manifest_is_canonical_unique_and_exact(self) -> None:
        labels = [row[0] for row in self.manifest]
        paths = [row[1] for row in self.manifest]
        self.assertEqual(labels, sorted(labels))
        self.assertEqual(len(labels), len(set(labels)))
        self.assertEqual(len(paths), len(set(paths)))
        for label, path, byte_count, sha256 in self.manifest:
            self.assertTrue(label)
            self.assertGreaterEqual(byte_count, 0)
            self.assertIsNotNone(HEX64.fullmatch(sha256))
            candidate = Path(path) if Path(path).is_absolute() else ROOT / path
            self.assertEqual(digest(candidate), (byte_count, sha256), label)

    def test_024_manifest_equals_recursive_contract_graph_plus_contract(self) -> None:
        declared = {str(row["path"]) for row in iter_exact_rows(self.config)}
        declared.add(CONFIG_PATH.relative_to(ROOT).as_posix())
        observed = {row[1] for row in self.manifest}
        self.assertEqual(observed, declared)

    def test_025_current_test_checkpoint_and_all_execution_subjects_are_bound(self) -> None:
        observed = {row[1] for row in self.manifest}
        required = {
            CONFIG_PATH.relative_to(ROOT).as_posix(),
            WRAPPER_PATH.relative_to(ROOT).as_posix(),
            CONTROLLER_PATH.relative_to(ROOT).as_posix(),
            BOOTSTRAP_PATH.relative_to(ROOT).as_posix(),
            NATIVE_SOURCE_PATH.relative_to(ROOT).as_posix(),
            NATIVE_EXE_PATH.relative_to(ROOT).as_posix(),
            Path(__file__).resolve().relative_to(ROOT).as_posix(),
            CHECKPOINT_PATH.relative_to(ROOT).as_posix(),
        }
        self.assertTrue(required.issubset(observed), sorted(required - observed))

    def test_026_audit_gate_requires_exact_external_hash_and_subject_graph(self) -> None:
        gate = self.config["controller_audit_gate"]
        self.assertTrue(gate["sha256_supplied_out_of_band"])
        self.assertEqual(gate["authoritative_decision_field"], "authoritative_decision.decision")
        self.assertEqual(
            gate["required_decision"],
            "ACCEPTED_FOR_ONE_BOUNDED_READ_ONLY_PAIR_ONLY",
        )
        required = set(gate["must_bind_exact_subjects"])
        self.assertTrue(
            {
                "contract", "native_launcher", "native_launcher_source",
                "retained_manifest", "bootstrap", "controller", "wrapper",
                "static_test", "checkpoint",
            }.issubset(required)
        )

    def test_027_external_audit_and_manifest_are_not_fake_in_graph_acceptance(self) -> None:
        labels = {row[0] for row in self.manifest}
        self.assertNotIn("accepted_controller_audit", labels)
        self.assertNotIn("retained_manifest", labels)
        self.assertNotIn("accepted_controller_audit", self.config.get("bindings", {}))
        gate = self.config["external_native_manifest_gate"]
        self.assertTrue(gate["sha256_supplied_out_of_band"])
        self.assertTrue(gate["fresh_audit_must_bind_exact_manifest"])

    def test_028_v3r3_is_bound_as_rejected_preservation_not_reinterpreted(self) -> None:
        preservation = self.config["locked_pair_v3r3_preservation"]
        paths = {str(row["path"]) for row in iter_exact_rows(preservation)}
        expected = {
            V3R3_CONFIG.relative_to(ROOT).as_posix(),
            V3R3_NATIVE_SOURCE.relative_to(ROOT).as_posix(),
            V3R3_NATIVE_EXE.relative_to(ROOT).as_posix(),
            V3R3_WRAPPER.relative_to(ROOT).as_posix(),
            V3R3_CONTROLLER.relative_to(ROOT).as_posix(),
            V3R3_BOOTSTRAP.relative_to(ROOT).as_posix(),
            V3R3_TEST.relative_to(ROOT).as_posix(),
            V3R3_CHECKPOINT.relative_to(ROOT).as_posix(),
            V3R3_MANIFEST.relative_to(ROOT).as_posix(),
        }
        self.assertTrue(expected.issubset(paths), sorted(expected - paths))
        self.assertIn("REJECT", json.dumps(preservation, sort_keys=True).upper())

    def test_029_no_execution_or_audit_artifact_exists(self) -> None:
        self.assertFalse(AUDIT_PATH.exists())
        self.assertFalse(OUTCOME_PATH.exists())
        self.assertFalse(OUTPUT_ROOT.exists())


@unittest.skipUnless(V3R4_SOURCE_STAGED, "append-only v3r4 source package is not staged")
class V3R4NativeLifecycleAndConcurrencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = NATIVE_SOURCE_PATH.read_text(encoding="utf-8")

    def test_030_state_records_main_thread_active_count_and_consumed_runs(self) -> None:
        one_of(self.source, ("main_thread_id", "main_os_thread_id"), "main OS thread ID is absent")
        one_of(self.source, ("active_child_count", "active_count"), "active child count is absent")
        one_of(self.source, ("run_attempt_consumed[2]", "run_1_consumed"), "per-run consumed state is absent")
        for token in ("next_run_number", "BrokerLifecycle", "CRITICAL_SECTION"):
            self.assertIn(token, self.source)
        self.assertNotRegex(self.source, r"\bint\s+active_process\s*;")

    def test_031_main_os_thread_is_captured_before_python_or_claim_authority(self) -> None:
        initialize = c_function_body(self.source, "initialize_locked_state")
        self.assertIn("GetCurrentThreadId", initialize)
        before(initialize, "GetCurrentThreadId", "lifecycle", "main OS thread must be captured first")

    def test_032_every_python_mutator_requires_the_main_os_thread(self) -> None:
        mutators = (
            "py_claim_once", "py_reserve_outcome", "py_create_output_root",
            "py_write_evidence", "py_run_child", "py_after_snapshot",
            "py_commit_failure_outcome", "py_finish",
        )
        for name in mutators:
            body = c_function_body(self.source, name)
            self.assertIn("require_main_os_thread", body, name)
        _, success = first_c_function_body(
            self.source, ("py_commit_success_outcome", "py_commit_outcome")
        )
        self.assertIn("require_main_os_thread", success)

    def test_033_run_slot_is_guarded_and_consumed_before_gil_release(self) -> None:
        body = c_function_body(self.source, "py_run_child")
        before(body, "EnterCriticalSection", "Py_BEGIN_ALLOW_THREADS", "run mutex must precede GIL release")
        active_token = "active_child_count" if "active_child_count" in body else "active_count"
        consumed_token = "run_attempt_consumed" if "run_attempt_consumed" in body else "run_1_consumed"
        before(body, active_token, "Py_BEGIN_ALLOW_THREADS", "active count guard must precede GIL release")
        before(body, consumed_token, "Py_BEGIN_ALLOW_THREADS", "run slot must be consumed before GIL release")
        self.assertIn("LeaveCriticalSection", body)
        one_of(
            body,
            ("concurrent_child_run_refused", "active_child_count_not_zero", "child_already_active"),
            "parallel run authority is not refused",
        )

    def test_034_run_number_is_never_advanced_outside_the_mutex(self) -> None:
        body = c_function_body(self.source, "py_run_child")
        enter = body.find("EnterCriticalSection")
        advance = body.find("++g_state.next_run_number")
        if advance < 0:
            advance = body.find("g_state.next_run_number =")
        leave = body.find("LeaveCriticalSection", advance)
        self.assertGreaterEqual(enter, 0)
        self.assertGreater(advance, enter)
        self.assertGreater(leave, advance)

    def test_035_snapshot_and_terminal_commits_require_global_quiescence(self) -> None:
        named_bodies = [
            ("py_after_snapshot", c_function_body(self.source, "py_after_snapshot")),
            first_c_function_body(self.source, ("py_commit_success_outcome", "py_commit_outcome")),
            ("py_commit_failure_outcome", c_function_body(self.source, "py_commit_failure_outcome")),
            ("py_finish", c_function_body(self.source, "py_finish")),
        ]
        for name, body in named_bodies:
            one_of(body, ("active_child_count", "active_count"), f"{name} lacks active count gate")
            one_of(body, ("run_attempt_consumed", "run_1_consumed"), f"{name} lacks consumed-run gate")
            one_of(body, ("require_all_jobs_quiescent", "all_jobs_quiescent"), f"{name} lacks Job-zero gate")

    def test_036_finish_is_one_way_consumed_even_on_failure(self) -> None:
        body = c_function_body(self.source, "py_finish")
        self.assertIn("CONSUMED", body)
        self.assertIn("finished", body)
        self.assertNotIn("next_run_number = 1", body)
        self.assertNotIn("run_1_consumed = 0", body)
        self.assertNotIn("run_2_consumed = 0", body)
        self.assertNotIn("run_attempt_consumed[0] = 0", body)
        self.assertNotIn("run_attempt_consumed[1] = 0", body)


@unittest.skipUnless(V3R4_SOURCE_STAGED, "append-only v3r4 source package is not staged")
class V3R4NativePathAndRuntimeIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_object(CONFIG_PATH)
        cls.source = NATIVE_SOURCE_PATH.read_text(encoding="utf-8")

    def test_040_file_identity_and_final_handle_apis_are_mandatory(self) -> None:
        for token in (
            "FILE_ID_INFO", "FileIdInfo", "GetFileInformationByHandleEx",
            "GetFinalPathNameByHandleW", "FILE_FLAG_OPEN_REPARSE_POINT",
            "FILE_FLAG_BACKUP_SEMANTICS",
        ):
            self.assertIn(token, self.source)

    def test_041_ancestor_directories_are_held_without_delete_sharing(self) -> None:
        _, body = first_c_function_body(
            self.source, ("open_locked_directory", "hold_directory_ancestor")
        )
        self.assertIn("FILE_FLAG_BACKUP_SEMANTICS", body)
        self.assertIn("FILE_FLAG_OPEN_REPARSE_POINT", body)
        self.assertNotIn("FILE_SHARE_DELETE", body)
        one_of(
            body,
            ("GetFileInformationByHandleEx", "final_handle_matches_path", "capture_handle_identity"),
            "directory handle identity is not captured",
        )

    def test_042_every_retained_row_holds_and_rechecks_ancestor_identity(self) -> None:
        body = c_function_body(self.source, "lock_and_verify_manifest_rows")
        one_of(body, ("hold_verified_ancestor_chain", "lock_verified_ancestor_chain", "hold_every_path_ancestor"), "retained row ancestry is not held")
        _, verify = first_c_function_body(
            self.source, ("verify_held_ancestor_chain", "recheck_ancestor_chain")
        )
        one_of(verify, ("same_file_identity", "FileIdInfo"), "ancestor recheck does not compare file identity")
        run = c_function_body(self.source, "py_run_child")
        one_of(run, ("verify_held_ancestor_chain", "recheck_ancestor_chain"), "ancestor identity is not rechecked at consumption")

    def test_042a_startup_manifest_audit_project_and_self_ancestors_are_held(self) -> None:
        body = c_function_body(self.source, "initialize_locked_state")
        for value in ("project_root", "manifest_path", "audit_path", "self_path"):
            pattern = re.compile(
                rf"(?:hold_verified_ancestor_chain|hold_every_path_ancestor|lock_verified_ancestor_chain)\s*\([^;]*{value}"
            )
            self.assertRegex(body, pattern, value)
        hold_manifest = min(
            index for index in (
                body.find("hold_verified_ancestor_chain", body.find("manifest_path")),
                body.find("hold_every_path_ancestor", body.find("manifest_path")),
                body.find("lock_verified_ancestor_chain", body.find("manifest_path")),
            ) if index >= 0
        )
        self.assertLess(hold_manifest, body.find("open_locked_read_file(g_state.manifest_path"))

    def test_043_child_launch_uses_reverified_handle_identity_not_manifest_text_alone(self) -> None:
        body = c_function_body(self.source, "py_run_child")
        before(body, "verify_retained_row_identity", "CreateProcessW", "child executable identity must be rechecked")
        path_token = "GetFinalPathNameByHandleW"
        if path_token not in body:
            path_token = "launch_path_from_retained_handle"
            _, helper = first_c_function_body(
                self.source,
                ("launch_path_from_retained_handle", "retained_handle_launch_path"),
            )
            self.assertIn("GetFinalPathNameByHandleW", helper)
        before(body, path_token, "CreateProcessW", "child launch path must derive from a held handle")
        self.assertNotIn("CreateProcessW(\n            executable_row->path", body)
        self.assertIn("wrapper", body)
        self.assertIn("foundation", body)

    def test_044_self_image_must_match_the_manifest_executable_row(self) -> None:
        lock = c_function_body(self.source, "lock_and_verify_manifest_rows")
        one_of(lock, ("verify_self_image_matches_manifest", "verify_native_image_identity"), "self image is not matched after graph lock")
        _, body = first_c_function_body(
            self.source,
            ("verify_self_image_matches_manifest", "verify_native_image_identity"),
        )
        for token in ("native_launcher", "GetModuleFileNameW", "verify_retained_row_identity"):
            self.assertIn(token, body)
        one_of(body, ("self_file_id_mismatch", "native_image_identity_mismatch"), "self image mismatch is not fatal")

    def test_045_embedded_python_is_absent_or_exact_runtime_identity_is_verified(self) -> None:
        embedded = "Python.h" in self.source or "Py_Initialize" in self.source
        if not embedded:
            self.assertNotRegex(self.source, r"\bPy[A-Z_a-z0-9]*\s*\(")
            return
        runtime_rows = [row for row in iter_exact_rows(self.config) if "python" in str(row["path"]).lower()]
        self.assertTrue(runtime_rows, "embedded Python runtime is not in exact-byte graph")
        if MANIFEST_PATH.is_file():
            manifest_paths = {row[1] for row in parse_manifest(MANIFEST_PATH)}
            self.assertTrue({str(row["path"]) for row in runtime_rows}.issubset(manifest_paths))
        body = c_function_body(self.source, "verify_loaded_python_runtime")
        for token in ("GetModuleHandleW", "GetModuleFileNameW", "verify_retained_row_identity"):
            self.assertIn(token, body)
        one_of(body, ("python_runtime_dll", "embedded_python_runtime"), "Python DLL row is not named")

    def test_045a_embedded_python_cannot_execute_before_its_identity_gate(self) -> None:
        embedded = "Python.h" in self.source or "Py_Initialize" in self.source
        if not embedded:
            return
        for token in (
            "SetDefaultDllDirectories", "LoadLibraryExW",
            "LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR",
        ):
            self.assertIn(token, self.source)
        self.assertIn("/DELAYLOAD:python314.dll", self.source)
        self.assertIn("delayimp.lib", self.source)
        initialize = c_function_body(self.source, "initialize_locked_state")
        self.assertIn("verify_retained_row_identity", initialize)
        one_of(initialize, ("python_runtime_dll", "embedded_python_runtime"), "Python runtime row is not verified at graph lock")
        loader_name, loader = first_c_function_body(
            self.source,
            ("secure_load_embedded_python", "load_verified_python_runtime"),
        )
        self.assertIn("LoadLibraryExW", loader)
        execute = c_function_body(self.source, "execute_retained_bootstrap")
        before(
            execute,
            loader_name,
            "Py_Initialize",
            "Python API cannot run before secure explicit load",
        )
        main = c_function_body(self.source, "wmain")
        before(main, "initialize_locked_state", "execute_retained_bootstrap", "graph/runtime verification must precede Python execution")

    def test_046_output_root_and_files_are_handle_verified(self) -> None:
        create = c_function_body(self.source, "py_create_output_root")
        write = c_function_body(self.source, "py_write_evidence")
        reserve = c_function_body(self.source, "py_reserve_outcome")
        for body, label in ((create, "root"), (write, "evidence"), (reserve, "outcome")):
            one_of(body, ("GetFinalPathNameByHandleW", "verify_new_output_handle", "final_handle_matches_path"), f"{label} final handle path is not verified")
            one_of(body, ("GetFileInformationByHandleEx", "verify_new_output_handle", "final_handle_matches_path"), f"{label} file ID is not verified")
            one_of(body, ("verify_output_ancestor_chain", "recheck_output_ancestor_chain"), f"{label} ancestry is not rechecked")

    def test_047_reserved_dos_device_ads_and_nt_device_names_are_rejected(self) -> None:
        _, body = first_c_function_body(
            self.source, ("safe_output_leaf_name", "safe_relative_path")
        )
        for reserved in ("CON", "PRN", "AUX", "NUL", "COM1", "COM9", "LPT1", "LPT9"):
            self.assertIn(reserved, body)
        for dangerous in ("GLOBALROOT", "\\\\.\\"):
            self.assertIn(dangerous, self.source)
        one_of(self.source, ("::$DATA", "alternate_data_stream", "ads_name_refused"), "NTFS ADS syntax is not explicitly refused")
        self.assertIn("L':'", body)
        one_of(body, ("trailing_dot_or_space", "output_leaf_trailing"), "trailing dot/space is not rejected")

    def test_048_path_prefix_string_check_is_not_the_output_authority(self) -> None:
        if "path_is_under_output_root" in self.source:
            body = c_function_body(self.source, "path_is_under_output_root")
            one_of(body, ("same_file_identity", "verify_output_ancestor_chain"), "path prefix remains output authority")


@unittest.skipUnless(V3R4_SOURCE_STAGED, "append-only v3r4 source package is not staged")
class V3R4PythonAuditAndProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_object(CONFIG_PATH)
        cls.source = NATIVE_SOURCE_PATH.read_text(encoding="utf-8")
        cls.controller = CONTROLLER_PATH.read_text(encoding="utf-8")
        cls.bootstrap = BOOTSTRAP_PATH.read_text(encoding="utf-8")
        cls.wrapper = WRAPPER_PATH.read_text(encoding="utf-8")

    def test_050_embedded_python_is_absent_or_has_no_ambient_search_authority(self) -> None:
        embedded = "Python.h" in self.source or "Py_Initialize" in self.source
        if not embedded:
            self.assertNotIn("python314.lib", self.source)
            return
        for token in (
            "PyConfig_InitIsolatedConfig", "use_environment = 0",
            "user_site_directory = 0", "site_import = 0", "safe_path = 1",
            "module_search_paths_set = 1",
        ):
            self.assertIn(token, self.source)
        one_of(
            self.source,
            ("retained_stdlib_zip", "embedded_python_runtime_closure"),
            "embedded Python search path is not pinned to a retained closure",
        )
        self.assertNotIn("Py_GetPath()", self.source)
        execute = c_function_body(self.source, "execute_retained_bootstrap")
        self.assertNotIn("python_home_from_runtime", execute)
        self.assertNotIn("config.home", execute)
        self.assertIn("config.module_search_paths", execute)
        one_of(
            execute,
            ("retained_stdlib_zip", "embedded_python_runtime_closure"),
            "module search paths do not come from a retained runtime row",
        )

    def test_051_embedded_python_sources_cannot_import_process_or_filesystem_capabilities(self) -> None:
        embedded = "Python.h" in self.source or "Py_Initialize" in self.source
        if not embedded:
            return
        forbidden_roots = {"os", "pathlib", "subprocess", "ctypes", "importlib", "site", "socket", "shutil", "tempfile"}
        for label, text in (("controller", self.controller), ("bootstrap", self.bootstrap)):
            tree = ast.parse(text)
            imports = {
                alias.name.split(".")[0]
                for node in ast.walk(tree) if isinstance(node, ast.Import)
                for alias in node.names
            }
            imports |= {
                (node.module or "").split(".")[0]
                for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
            }
            self.assertTrue(forbidden_roots.isdisjoint(imports), (label, sorted(imports & forbidden_roots)))
        execute = c_function_body(self.source, "execute_retained_bootstrap")
        one_of(
            execute,
            ("restricted_builtins", "capability_free_builtins", "install_denied_import"),
            "retained Python receives ambient builtins/import capabilities",
        )

    def test_052_external_manifest_contract_and_audit_hashes_are_mandatory(self) -> None:
        parse = c_function_body(self.source, "parse_main_arguments")
        initialize = c_function_body(self.source, "initialize_locked_state")
        for token in ("--manifest-sha256", "--contract-sha256", "--audit-sha256"):
            self.assertIn(token, parse)
        for token in (
            "expected_manifest_sha256", "expected_contract_sha256",
            "expected_audit_sha256", "constant_time_equal32",
        ):
            self.assertIn(token, initialize)

    def test_053_audit_bytes_are_strictly_parsed_before_audit_accepted(self) -> None:
        initialize = c_function_body(self.source, "initialize_locked_state")
        before(initialize, "parse_and_verify_exact_audit", "AUDIT_ACCEPTED", "audit content must be parsed before acceptance")
        parser = c_function_body(self.source, "parse_and_verify_exact_audit")
        for token in (
            "kira.avatar.r25.foundation_afes_locked_pair_independent_audit.v3r4",
            "authoritative_decision", "decision",
            "ACCEPTED_FOR_ONE_BOUNDED_READ_ONLY_PAIR_ONLY",
            "exact_subjects", "checkpoint", "retained_manifest",
            "native_launcher", "native_launcher_source", "static_test",
        ):
            self.assertIn(token, parser)
        one_of(parser, ("duplicate_json_key", "reject_duplicate_key"), "duplicate JSON keys are not rejected")
        one_of(parser, ("unknown_json_key", "reject_unknown_key"), "unknown audit keys are not rejected")
        self.assertIn("constant_time_equal32", parser)

    def test_054_result_channel_is_named_pipe_root_pid_authenticated(self) -> None:
        run = c_function_body(self.source, "py_run_child")
        auth_name, auth = first_c_function_body(
            self.source,
            ("authenticate_result_pipe_root_pid", "accept_authenticated_result_pipe"),
        )
        self.assertIn(auth_name, run)
        for token in (
            "CreateNamedPipeW", "PIPE_REJECT_REMOTE_CLIENTS",
            "ConnectNamedPipe", "GetNamedPipeClientProcessId",
        ):
            self.assertIn(token, auth)
        if "ReadFile" in auth:
            before(auth, "GetNamedPipeClientProcessId", "ReadFile", "writer PID must be authenticated before result read")
        self.assertRegex(auth, r"client[_a-z]*pid\s*!=\s*(?:expected_root_pid|process\.(?:dwProcessId|process_id))")
        one_of(auth, ("named_pipe_client_pid_mismatch", "result_writer_pid_mismatch"), "wrong writer PID is not fatal")
        before(run, auth_name, "make_child_result", "result cannot be accepted before writer authentication")

    def test_055_inherited_result_handle_protocol_is_removed(self) -> None:
        self.assertNotIn("--result-handle", self.source)
        self.assertNotIn("--result-handle", self.controller)
        self.assertNotIn("--result-handle", self.wrapper)
        self.assertIn("--result-pipe-name", self.source)
        self.assertIn("--result-pipe-name", self.wrapper)


@unittest.skipUnless(V3R4_SOURCE_STAGED, "append-only v3r4 source package is not staged")
class V3R4QuiescenceDrainOutcomeAndEnvironmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_object(CONFIG_PATH)
        cls.source = NATIVE_SOURCE_PATH.read_text(encoding="utf-8")
        cls.controller = CONTROLLER_PATH.read_text(encoding="utf-8")
        cls.bootstrap = BOOTSTRAP_PATH.read_text(encoding="utf-8")

    def test_060_job_quiescence_uses_active_processes_zero(self) -> None:
        body = c_function_body(self.source, "wait_for_job_active_processes_zero")
        for token in (
            "QueryInformationJobObject", "JobObjectBasicAccountingInformation",
            "JOBOBJECT_BASIC_ACCOUNTING_INFORMATION", "ActiveProcesses",
        ):
            self.assertIn(token, body)
        self.assertRegex(body, r"ActiveProcesses\s*==\s*0")
        one_of(body, ("WaitForSingleObject", "Sleep", "WaitForMultipleObjects"), "Job-zero polling has no bounded wait")

    def test_061_root_process_exit_never_clears_active_count_by_itself(self) -> None:
        body = c_function_body(self.source, "py_run_child")
        process_wait = body.find("WaitForSingleObject(process.hProcess")
        job_zero = body.find("wait_for_job_active_processes_zero", process_wait)
        decrement = body.find("--g_state.active_child_count", process_wait)
        if decrement < 0:
            decrement = body.find("g_state.active_child_count -=", process_wait)
        self.assertGreaterEqual(process_wait, 0)
        self.assertGreater(job_zero, process_wait)
        self.assertGreater(decrement, job_zero)

    def test_062_every_cleanup_path_proves_job_zero_before_return(self) -> None:
        body = c_function_body(self.source, "py_run_child")
        self.assertGreaterEqual(body.count("wait_for_job_active_processes_zero"), 2)
        one_of(body, ("job_descendants_not_quiescent", "job_active_processes_nonzero"), "nonzero Job cannot be reported clean")

    def test_063_drain_contexts_are_heap_owned_not_stack_borrowed(self) -> None:
        body = c_function_body(self.source, "py_run_child")
        self.assertNotRegex(body, r"DrainContext\s+drains\s*\[")
        self.assertNotRegex(body, r"CreateThread\s*\([^;]*&drains\[")
        self.assertRegex(body, r"(?:calloc|HeapAlloc)\s*\([^;]*DrainContext")

    def test_064_drain_cancellation_joins_before_context_or_handle_release(self) -> None:
        body = c_function_body(self.source, "cancel_join_and_destroy_drain")
        one_of(body, ("CancelSynchronousIo", "CancelIoEx"), "blocked drain read cannot be cancelled")
        self.assertIn("WaitForSingleObject", body)
        self.assertIn("WAIT_OBJECT_0", body)
        wait = body.find("WaitForSingleObject")
        free = body.find("free(")
        if free < 0:
            free = body.find("HeapFree")
        self.assertGreater(free, wait)
        self.assertNotIn("CloseHandle(*thread)", body[:wait])

    def test_065_no_second_bounded_join_can_return_with_live_stack_references(self) -> None:
        self.assertNotIn("wait_and_close_drain", self.source)
        cleanup = c_function_body(self.source, "cancel_join_and_destroy_drain")
        one_of(cleanup, ("INFINITE", "drain_join_must_complete"), "drain cleanup may return while thread remains live")

    def test_066_terminal_outcome_success_and_failure_use_one_rewrite_transaction(self) -> None:
        rewrite = c_function_body(self.source, "rewrite_terminal_outcome")
        for token in ("SetFilePointerEx", "SetEndOfFile", "write_all_handle", "FlushFileBuffers"):
            self.assertIn(token, rewrite)
        self.assertLess(rewrite.find("SetFilePointerEx"), rewrite.find("SetEndOfFile"))
        self.assertLess(rewrite.find("SetEndOfFile"), rewrite.find("write_all_handle"))
        named_bodies = [
            first_c_function_body(self.source, ("py_commit_success_outcome", "py_commit_outcome")),
            ("py_commit_failure_outcome", c_function_body(self.source, "py_commit_failure_outcome")),
            ("commit_native_failure_if_reserved", c_function_body(self.source, "commit_native_failure_if_reserved")),
        ]
        for name, body in named_bodies:
            self.assertIn("rewrite_terminal_outcome", body, name)

    def test_067_partial_write_is_rewound_truncated_and_terminally_recorded(self) -> None:
        rewrite = c_function_body(self.source, "rewrite_terminal_outcome")
        one_of(rewrite, ("partial_write", "terminal_write_partial"), "partial write is not detected")
        self.assertGreaterEqual(rewrite.count("SetFilePointerEx"), 2)
        self.assertGreaterEqual(rewrite.count("SetEndOfFile"), 2)
        self.assertIn("PARTIAL_EVIDENCE", self.source)
        self.assertIn("evidence_complete", self.source)
        self.assertIn("evidence_write_failures", self.source)

    def test_067a_partial_evidence_is_measured_and_carried_into_terminal_failure(self) -> None:
        write = c_function_body(self.source, "py_write_evidence")
        one_of(
            write,
            ("record_partial_evidence", "partial_evidence_write"),
            "partial evidence state is not captured at the writer",
        )
        failure = c_function_body(self.source, "py_commit_failure_outcome")
        for token in ("partial_evidence", "evidence_complete", "evidence_write_failures"):
            self.assertIn(token, failure)
        one_of(failure, ("measured_partial_bytes", "partial_evidence_bytes"), "partial evidence byte truth is omitted")

    def test_068_outcome_is_never_considered_committed_before_flush(self) -> None:
        rewrite = c_function_body(self.source, "rewrite_terminal_outcome")
        self.assertIn("FlushFileBuffers", rewrite)
        named_bodies = [
            first_c_function_body(self.source, ("py_commit_success_outcome", "py_commit_outcome")),
            ("py_commit_failure_outcome", c_function_body(self.source, "py_commit_failure_outcome")),
            ("commit_native_failure_if_reserved", c_function_body(self.source, "commit_native_failure_if_reserved")),
        ]
        for name, body in named_bodies:
            rewrite_call = body.find("rewrite_terminal_outcome")
            committed = body.find("outcome_committed", rewrite_call)
            self.assertGreater(committed, rewrite_call, name)

    def test_069_parent_path_temp_profile_and_cache_values_are_not_inherited(self) -> None:
        body = c_function_body(self.source, "native_restricted_environment")
        for forbidden in ('L"Path"', 'L"TEMP"', 'L"TMP"', 'L"LOCALAPPDATA"', 'L"APPDATA"'):
            self.assertNotIn(forbidden, body)
        self.assertNotIn("GetEnvironmentVariableW(L\"Path\"", body)
        one_of(body, ("build_minimal_path", "PATH_OMITTED_BY_DESIGN"), "PATH is neither minimal nor omitted")

    def test_070_each_run_gets_a_new_nonce_bound_cache_root(self) -> None:
        run = c_function_body(self.source, "py_run_child")
        for token in ("pair_nonce", "run_nonce", "create_unique_cache_root"):
            self.assertIn(token, run)
        cache = c_function_body(self.source, "create_unique_cache_root")
        self.assertIn("CreateDirectoryW", cache)
        self.assertIn("ERROR_ALREADY_EXISTS", cache)
        one_of(cache, ("hold_cache_ancestor_chain", "verify_cache_root_handle"), "cache root is not handle sealed")

    def test_071_all_mutable_child_locations_point_inside_the_unique_run_root(self) -> None:
        body = c_function_body(self.source, "native_restricted_environment")
        for name in (
            "TEMP", "TMP", "BLENDER_USER_CONFIG", "BLENDER_USER_SCRIPTS",
            "BLENDER_USER_DATAFILES", "PYTHONPYCACHEPREFIX",
        ):
            self.assertIn(name, body)
        self.assertIn("unique_run_cache_root", body)
        self.assertNotIn("RecoverySprint/runtime_cache/r25_blender/user_config", body)

    def test_072_environment_block_has_exact_unique_case_insensitive_keys(self) -> None:
        body = c_function_body(self.source, "build_environment_block")
        self.assertIn("case_insensitive_environment_duplicate", body)
        self.assertIn("qsort", body)
        one_of(body, ("environment_exact_key_count", "exact_environment_keys"), "extra environment keys are not refused")


@unittest.skipUnless(V3R4_STAGED, "append-only v3r4 package is not fully staged")
class V3R4BuildAndStaticPurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = NATIVE_SOURCE_PATH.read_text(encoding="utf-8")
        cls.controller = CONTROLLER_PATH.read_text(encoding="utf-8")
        cls.bootstrap = BOOTSTRAP_PATH.read_text(encoding="utf-8")
        cls.wrapper = WRAPPER_PATH.read_text(encoding="utf-8")
        cls.checkpoint = CHECKPOINT_PATH.read_text(encoding="utf-8")

    def test_080_native_build_contract_requires_w4_wx_and_control_flow_guard(self) -> None:
        for token in ("/W4", "/WX", "/guard:cf", "/std:c17"):
            self.assertIn(token, self.source)
            self.assertIn(token, self.checkpoint)
        one_of(self.checkpoint.lower(), ("warnings: 0", "warning_count: 0", "zero warnings"), "checkpoint lacks zero-warning result")

    def test_081_no_unused_static_function_is_hidden_from_the_build_gate(self) -> None:
        definitions = re.findall(
            r"(?m)^static\s+(?!const\b)(?:[A-Za-z_][\w\s*]+?)\s+([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{",
            self.source,
        )
        self.assertTrue(definitions)
        unreferenced = [
            name for name in definitions
            if len(re.findall(rf"\b{re.escape(name)}\b", self.source)) < 2
        ]
        self.assertEqual(unreferenced, [], "unused static definitions")
        self.assertIn("/WX", self.source)

    def test_082_python_sources_parse_without_import_or_execution(self) -> None:
        for path, text in (
            (CONTROLLER_PATH, self.controller),
            (BOOTSTRAP_PATH, self.bootstrap),
            (WRAPPER_PATH, self.wrapper),
            (Path(__file__).resolve(), Path(__file__).read_text(encoding="utf-8")),
        ):
            ast.parse(text, filename=str(path))

    def test_083_controller_exports_no_standalone_process_or_filesystem_authority(self) -> None:
        tree = ast.parse(self.controller)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree) if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports |= {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        }
        self.assertTrue({"os", "pathlib", "subprocess", "ctypes", "threading", "multiprocessing"}.isdisjoint(imports))
        for token in ("Popen", "CreateProcess", "open(", "Path("):
            self.assertNotIn(token, self.controller)

    def test_084_wrapper_remains_read_only_and_has_no_body_mutation(self) -> None:
        for forbidden in (
            "bpy.ops.wm.save", "save_as_mainfile", "render.render",
            "export_scene", "mesh.from_pydata", "vertices.add", "foreach_set",
        ):
            self.assertNotIn(forbidden, self.wrapper)
        self.assertIn("READ_ONLY_EXTRACTION_COMPLETE_PENDING_PAIR_MATCH", self.wrapper)

    def test_085_native_executable_is_a_bound_pe_image(self) -> None:
        self.assertEqual(NATIVE_EXE_PATH.read_bytes()[:2], b"MZ")
        rows = {row[1]: (row[2], row[3]) for row in parse_manifest(MANIFEST_PATH)}
        path = NATIVE_EXE_PATH.relative_to(ROOT).as_posix()
        self.assertIn(path, rows)
        self.assertEqual(digest(NATIVE_EXE_PATH), rows[path])


if __name__ == "__main__":
    unittest.main()
