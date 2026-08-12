"""Hostile static-only tests for the append-only AFES v3r10 diagnostic.

This suite reads source/configuration/PE bytes.  It never imports or executes
the diagnostic PE, v3r9 launcher, controller, bootstrap, wrapper, AFES code, or
Blender.
"""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_locked_pair_preoutcome_diagnostic_v3r10.json"
NATIVE = ROOT / "tools/native/kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r10.c"
PE = ROOT / "tools/native/kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r10.exe"
CHECKPOINT = ROOT / "RecoverySprint/continuation_20260810/kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r10_static_preparation/attempt_01/CHECKPOINT.md"
EVIDENCE = ROOT / "RecoverySprint/continuation_20260810/kira_r25_afes_locked_pair_preoutcome_diagnostic_v3r10_static_preparation/attempt_01/RUN_EVIDENCE.jsonl"
FUTURE_AUDIT = ROOT / "RecoverySprint/continuation_20260810/kira_r25_afes_v3r10_fresh_static_audit/attempt_01/INDEPENDENT_AUDIT.tsv"
MANIFEST = ROOT / "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_03r9/RETAINED_NATIVE_LOCK_MANIFEST.tsv"
POSTMORTEM = ROOT / "RecoverySprint/continuation_20260810/kira_r25_afes_v3r9_consumed_run_static_postmortem/attempt_01/CHECKPOINT.md"

V3R9_FROZEN = {
    "Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_locked_pair_execution_v3r9.json": (146969, "f50df32a70093cf968e2d6be7c7de228d84f003605f854b97bfa542b9ea396d5"),
    "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_03r9/CHECKPOINT.md": (6155, "0bab2d9615797cef7255fcbe54bff09f37f3b519e43bb2072f248f3c3c6863fe"),
    "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_03r9/INDEPENDENT_AUDIT.json": (923, "2e21632eb1d394e43af6da8dbdfcdfbd2db4c86b7460fc3def319273e4e4c414"),
    "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_03r9/RETAINED_NATIVE_LOCK_MANIFEST.tsv": (24975, "6df14df08a3f4c5a68c22b3eb3ccd8d8ce46209a156784a7582357071fc78d96"),
    "RecoverySprint/continuation_20260810/kira_r25_afes_v3r9_consumed_run_static_postmortem/attempt_01/CHECKPOINT.md": (8451, "275fd7501a5d35ec6c5648a3935cafa56eb7854dfb80c173a2adc364738afed3"),
    "RecoverySprint/continuation_20260810/kira_r25_afes_v3r9_consumed_run_static_postmortem/attempt_01/CONSUMED_COMMAND.txt": (883, "76e7de2dd99dd7c4a1aaba3f76f371f6fae8d3d1ffd91ef14d90786ffa0fbb10"),
    "RecoverySprint/continuation_20260810/kira_r25_afes_v3r9_consumed_run_static_postmortem/attempt_01/RAW_TOOL_RESULT_TRANSCRIPT.txt": (249, "012f65b23b5f604b559b16533c11e7869758a77bc3e9348593c3c167027d56c6"),
    "RecoverySprint/continuation_20260810/kira_r25_afes_v3r9_fresh_static_audit/attempt_01/CHECKPOINT.md": (8602, "8fe9287f1bcee93912881efe794f24ea427fa32f2e9a56e9c26462a8b07926dd"),
    "RecoverySprint/runtime_cache/kira_r25_afes_v3r9_fresh_static_audit/launcher.exe": (282112, "36f355e5c71a3be5cbdbf7f79f78b161f170c07cd3140a301df5c8f4f552e716"),
    "RecoverySprint/runtime_cache/kira_r25_afes_v3r9_fresh_static_audit/launcher.exp": (835, "2f3c51358dba0bdb94304656a8ff31b5d9c281919998f6ca5809dffbbd60c1db"),
    "RecoverySprint/runtime_cache/kira_r25_afes_v3r9_fresh_static_audit/launcher.lib": (1850, "fc4f48c6a673b627b5fd459eb98804c05cd701caac65668b7a15a6bdbb68b66f"),
    "RecoverySprint/runtime_cache/kira_r25_afes_v3r9_fresh_static_audit/launcher.obj": (427785, "47cec94e616724a4acc527936238bb5ab4bae69e521fbbf34a19e9410b56e40e"),
    "Testing/test_kira_r25_foundation_afes_locked_pair_execution_v3r9.py": (67410, "ff6f1c75f773fa29e9c6815705e8ca8b9f4f1e80e8dea64c508489eb929eae6d"),
    "tools/blender_extract_kira_r25_foundation_afes_transition_rings_execution_v3r9.py": (25343, "a9c3da1146f2b8057338eb8ce679f96cc3f1d14582ecbb7212249c6a69e2383b"),
    "tools/native/kira_r25_afes_locked_pair_launcher_v3r9.c": (263949, "703f9683c44f8506558b85dbf3480425f0da0a05c115c1da2ef5bdd092e7addd"),
    "tools/native/kira_r25_afes_locked_pair_launcher_v3r9.exe": (282112, "2aec90c36e3150c258f6089fd1ba3f9e5c336ca0b69d8d1a4d826bc6a8764760"),
    "tools/native/kira_r25_afes_locked_pair_launcher_v3r9.exp": (822, "246a044e38befd28e2292bddd754c2dd75c1d833b13dffcafe526fb9edd23482"),
    "tools/native/kira_r25_afes_locked_pair_launcher_v3r9.lib": (2324, "b86d186082a6777e50f2b8da9ba85c459a6b01c51df575679e938af391fe2e61"),
    "tools/native/kira_r25_afes_locked_pair_launcher_v3r9.obj": (427765, "6b7c47090a0437861e5de54661ca99fe0c0c1e32b77c783b475d29b2f1cee5c6"),
    "tools/run_kira_r25_foundation_afes_locked_pair_bootstrap_v3r9.py": (9381, "57ecda2ce2aecc75a259c3b6e9296eeec1512a296ebe7309f803e5ada3ea8378"),
    "tools/run_kira_r25_foundation_afes_locked_pair_v3r9.py": (50907, "60674e104d69ac9166aca7ea9001ff32e8494d07677748fbb633955ee1d9ebaf"),
}

AUDIT_KEYS = (
    "decision", "auditor_boundary", "auditor_id", "contract_sha256",
    "native_executable_sha256", "native_source_sha256", "static_test_sha256",
    "static_checkpoint_sha256", "retained_manifest_sha256",
    "v3r9_postmortem_sha256",
)


def digest(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), hashlib.sha256(data).hexdigest()


def c_body(source: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^;{{}}]*\)\s*\{{", source, re.S)
    if match is None:
        raise AssertionError(f"missing C function {name}")
    opening = source.find("{", match.start())
    depth = 0
    string = character = escaped = False
    for index in range(opening, len(source)):
        token = source[index]
        if escaped:
            escaped = False
        elif token == "\\" and (string or character):
            escaped = True
        elif token == '"' and not character:
            string = not string
        elif token == "'" and not string:
            character = not character
        elif not string and not character:
            if token == "{":
                depth += 1
            elif token == "}":
                depth -= 1
                if depth == 0:
                    return source[opening + 1:index]
    raise AssertionError(f"unbalanced C function {name}")


def pe_shape(value: bytes) -> tuple[int, int, int, set[str], set[str]]:
    if value[:2] != b"MZ":
        raise AssertionError("not MZ")
    pe = int.from_bytes(value[0x3C:0x40], "little")
    if value[pe:pe + 4] != b"PE\0\0":
        raise AssertionError("not PE")
    machine = int.from_bytes(value[pe + 4:pe + 6], "little")
    section_count = int.from_bytes(value[pe + 6:pe + 8], "little")
    optional_size = int.from_bytes(value[pe + 20:pe + 22], "little")
    optional = pe + 24
    magic = int.from_bytes(value[optional:optional + 2], "little")
    dll_characteristics = int.from_bytes(value[optional + 70:optional + 72], "little")
    image_base = int.from_bytes(value[optional + 24:optional + 32], "little")
    directories = optional + 112
    import_rva = int.from_bytes(value[directories + 8:directories + 12], "little")
    delay_rva = int.from_bytes(value[directories + 13 * 8:directories + 13 * 8 + 4], "little")
    sections = []
    table = optional + optional_size
    for index in range(section_count):
        row = table + index * 40
        virtual_size = int.from_bytes(value[row + 8:row + 12], "little")
        virtual_address = int.from_bytes(value[row + 12:row + 16], "little")
        raw_size = int.from_bytes(value[row + 16:row + 20], "little")
        raw_offset = int.from_bytes(value[row + 20:row + 24], "little")
        sections.append((virtual_address, max(virtual_size, raw_size), raw_offset))

    def offset(rva: int) -> int:
        for address, span, raw in sections:
            if address <= rva < address + span:
                return raw + rva - address
        raise AssertionError(f"unmapped RVA {rva:#x}")

    def ascii_z(rva: int) -> str:
        start = offset(rva)
        return value[start:value.index(0, start)].decode("ascii").lower()

    normal: set[str] = set()
    if import_rva:
        cursor = offset(import_rva)
        while any(value[cursor:cursor + 20]):
            normal.add(ascii_z(int.from_bytes(value[cursor + 12:cursor + 16], "little")))
            cursor += 20
    delayed: set[str] = set()
    if delay_rva:
        cursor = offset(delay_rva)
        while any(value[cursor:cursor + 32]):
            attributes = int.from_bytes(value[cursor:cursor + 4], "little")
            name = int.from_bytes(value[cursor + 4:cursor + 8], "little")
            if not attributes & 1:
                name -= image_base
            delayed.add(ascii_z(name))
            cursor += 32
    return machine, magic, dll_characteristics, normal, delayed


def parse_manifest() -> list[tuple[str, str, int, str]]:
    lines = MANIFEST.read_text(encoding="utf-8").splitlines()
    if lines[:2] != [
        "KIRA_R25_AFES_RETAINED_MANIFEST_V3R9\t1",
        "label\tpath\tbytes\tsha256",
    ]:
        raise AssertionError("manifest header drift")
    rows = []
    for line in lines[2:]:
        fields = line.split("\t")
        if len(fields) != 4:
            raise AssertionError("manifest row shape")
        rows.append((fields[0], fields[1], int(fields[2]), fields[3]))
    return rows


def canonical_audit(values: dict[str, str]) -> bytes:
    lines = ["KIRA_R25_AFES_PREOUTCOME_DIAGNOSTIC_AUDIT_V3R10\t1"]
    lines.extend(f"{key}\t{values[key]}" for key in AUDIT_KEYS)
    return ("\n".join(lines) + "\n").encode("ascii")


def simulated_audit_accepts(raw: bytes, contract_hash: str, pe_hash: str) -> bool:
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        return False
    if not text.endswith("\n") or "\r" in text or "\0" in text:
        return False
    lines = text[:-1].split("\n")
    if len(lines) != 11 or lines[0] != "KIRA_R25_AFES_PREOUTCOME_DIAGNOSTIC_AUDIT_V3R10\t1":
        return False
    parsed = {}
    for key, line in zip(AUDIT_KEYS, lines[1:], strict=True):
        fields = line.split("\t")
        if len(fields) != 2 or fields[0] != key or not fields[1]:
            return False
        parsed[key] = fields[1]
    lower_id = re.fullmatch(r"[a-z0-9_]{3,64}", parsed["auditor_id"])
    hex64 = re.compile(r"[0-9a-f]{64}\Z")
    return bool(
        parsed["decision"] == "ACCEPTED_FOR_ONE_BOUNDED_NATIVE_DIAGNOSTIC_ONLY"
        and parsed["auditor_boundary"] == "different_fresh_exact_byte_static_auditor"
        and lower_id
        and parsed["auditor_id"] != "codex_r25_afes_v3r10_recovery_author"
        and parsed["contract_sha256"] == contract_hash
        and parsed["native_executable_sha256"] == pe_hash
        and all(hex64.fullmatch(parsed[key]) for key in (
            "native_source_sha256", "static_test_sha256", "static_checkpoint_sha256"
        ))
        and parsed["retained_manifest_sha256"] == "6df14df08a3f4c5a68c22b3eb3ccd8d8ce46209a156784a7582357071fc78d96"
        and parsed["v3r9_postmortem_sha256"] == "275fd7501a5d35ec6c5648a3935cafa56eb7854dfb80c173a2adc364738afed3"
    )


class FrozenPredecessorTests(unittest.TestCase):
    def test_001_every_named_v3r9_byte_is_preserved(self):
        self.assertEqual(
            {path: digest(ROOT / path) for path in V3R9_FROZEN}, V3R9_FROZEN
        )

    def test_002_consumed_authority_is_not_reinterpreted(self):
        text = POSTMORTEM.read_text(encoding="utf-8")
        for marker in (
            "V3R9_ONE_SHOT_AUTHORITY_CONSUMED", "NO_RETRY",
            "NO_READ_ONLY_PAIR_RESULT_WAS_PRODUCED", "NO_RETRY_V3R9",
        ):
            self.assertIn(marker, text)


class StaticBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = NATIVE.read_text(encoding="utf-8")
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_010_append_only_subjects_exist_and_runtime_evidence_does_not(self):
        for path in (CONTRACT, NATIVE, PE, CHECKPOINT):
            self.assertTrue(path.is_file(), path)
        self.assertFalse(EVIDENCE.exists())
        self.assertFalse(FUTURE_AUDIT.exists())

    def test_011_contract_has_no_execution_authority(self):
        self.assertEqual(
            self.contract["status"],
            "SEALED_STATIC_CANDIDATE_AWAITING_DIFFERENT_FRESH_AUDIT",
        )
        self.assertEqual(self.contract["execution_authority"], "NONE")
        self.assertEqual(
            self.contract["authoring_boundary"]["v3r9_one_shot_authority"],
            "CONSUMED_NO_RETRY",
        )
        self.assertFalse(
            self.contract["authoring_boundary"]["launcher_controller_bootstrap_wrapper_blender_execution"]
        )
        self.assertFalse(
            self.contract["authoring_boundary"]["body_mutation_save_render_export"]
        )

    def test_012_contract_binds_exact_consumed_inputs(self):
        sealed = self.contract["sealed_v3r9_inputs"]
        self.assertEqual(
            sealed["retained_manifest"],
            {
                "path": MANIFEST.relative_to(ROOT).as_posix(),
                "bytes": 24975,
                "sha256": "6df14df08a3f4c5a68c22b3eb3ccd8d8ce46209a156784a7582357071fc78d96",
            },
        )
        self.assertEqual(
            sealed["consumed_run_postmortem"]["sha256"],
            "275fd7501a5d35ec6c5648a3935cafa56eb7854dfb80c173a2adc364738afed3",
        )

    def test_013_no_body_runtime_surface_is_linked_or_called(self):
        forbidden = (
            "Py_", "PyInitialize", "python314.lib", "bpy", "execute_retained_bootstrap",
            "reserve_outcome(", "run_child(", "CreateDirectoryW", "DeleteFileW",
            "RemoveDirectoryW", "MoveFile", "ReplaceFile", "ShellExecute",
        )
        for token in forbidden:
            self.assertNotIn(token, self.source)
        self.assertEqual(self.source.count("CreateProcessW("), 1)
        create = c_body(self.source, "observer_main")
        self.assertIn("CreateProcessW(\n            self_path", create)

    def test_014_observer_records_creation_before_resuming_child(self):
        body = c_body(self.source, "observer_main")
        create = body.index("CreateProcessW(")
        record = body.index('write_record("observer", "create_process", "passed"')
        resume = body.index("ResumeThread(process.hThread)")
        self.assertLess(create, record)
        self.assertLess(record, resume)
        resumed = body.index("child_resumed = 1", resume)
        wait = body.index("wait_result = WaitForSingleObject", resumed)
        self.assertNotIn("write_record", body[resumed:wait])
        for marker in (
            "CREATE_SUSPENDED", "CREATE_NO_WINDOW", "EXTENDED_STARTUPINFO_PRESENT",
            "PROC_THREAD_ATTRIBUTE_HANDLE_LIST",
        ):
            self.assertIn(marker, body)
        self.assertIn("startup.StartupInfo.hStdInput = g_evidence", body)

    def test_015_raw_exit_and_both_streams_are_native_captured(self):
        body = c_body(self.source, "observer_main")
        for marker in (
            "GetExitCodeProcess", "read_pipe_bounded(stdout_read",
            "read_pipe_bounded(stderr_read", "raw_exit_and_captured_streams",
            "stdout_hex", "stderr_hex", "CHILD_PRE_OUTCOME_STOP_EXIT",
        ):
            self.assertIn(marker, body)

    def test_016_evidence_is_create_new_write_through_and_never_replaced(self):
        body = c_body(self.source, "reserve_evidence")
        self.assertIn("CREATE_NEW", body)
        self.assertIn("FILE_FLAG_WRITE_THROUGH", body)
        self.assertIn("FILE_SHARE_READ", body)
        for token in ("OPEN_ALWAYS", "CREATE_ALWAYS", "TRUNCATE_EXISTING"):
            self.assertNotIn(token, body)

    def test_017_child_stops_before_outcome_and_returns_distinct_raw_exit(self):
        body = c_body(self.source, "child_main")
        successful_records = (
            'write_record("child", "wmain_entry", "entered"',
            'write_record("child", "argument_gate", "passed"',
            'write_record("child", "self_image_identity", "passed"',
            'write_record("child", "fresh_audit_and_subject_gate", "passed"',
            'write_record("child", "retained_graph_gate", "passed"',
            'write_record("child", "pre_outcome_parent_access_gate", "passed"',
            'write_record("child", "python_dll_delayed_load_identity", "passed"',
            'write_record("child", "pre_outcome_stop", "reached"',
        )
        positions = [body.index(record) for record in successful_records]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("return (int)CHILD_PRE_OUTCOME_STOP_EXIT", body)
        self.assertIn("no_python_initialization_no_controller_no_reservation", body)

    def test_018_original_receipt_is_only_absence_checked(self):
        body = c_body(self.source, "probe_outcome_parent")
        self.assertIn("GetFileAttributesW(receipt)", body)
        self.assertIn("CreateFileW(\n        parent", body)
        self.assertNotIn("CreateFileW(\n        receipt", body)
        self.assertIn("FILE_ADD_FILE", body)

    def test_019_python_boundary_is_load_identity_only(self):
        body = c_body(self.source, "verify_python_dll_load")
        self.assertIn("LoadLibraryExW", body)
        self.assertIn("open_locked_subject", body)
        self.assertIn("FreeLibrary", body)
        for token in ("GetProcAddress", "Py_", "CreateProcess"):
            self.assertNotIn(token, body)

    def test_01a_complete_retained_graph_is_locked_and_exact(self):
        body = c_body(self.source, "verify_manifest_graph")
        for marker in (
            "count != 137U", "native_launcher", "python_runtime_dll",
            "blender_executable", "open_locked_subject",
            "manifest_path_duplicate", "manifest_required_graph_drift",
        ):
            self.assertIn(marker, body)
        rows = parse_manifest()
        self.assertEqual(len(rows), 137)
        self.assertEqual([row[0] for row in rows], sorted(row[0] for row in rows))
        self.assertEqual(len({row[1].casefold() for row in rows}), 137)

    def test_01b_fresh_audit_is_a_runtime_gate_not_a_note(self):
        body = c_body(self.source, "parse_exact_audit")
        for marker in (
            "ACCEPTED_FOR_ONE_BOUNDED_NATIVE_DIAGNOSTIC_ONLY",
            "different_fresh_exact_byte_static_auditor", "AUTHOR_ID",
            "MANIFEST_SHA256", "POSTMORTEM_SHA256", "self_sha256",
        ):
            self.assertIn(marker, body)
        self.assertIn("strcmp(values[2], AUTHOR_ID) == 0", body)

    def test_01c_main_distinguishes_observer_and_child_entry(self):
        body = c_body(self.source, "wmain")
        self.assertLess(body.index("find_child_surface"), body.index("reserve_evidence"))
        self.assertIn("child_main(argc, argv", body)
        self.assertIn("observer_main(argc, argv", body)

    def test_01d_compile_contract_is_hardened_static_native(self):
        checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        for marker in ("/W4", "/WX", "/O2", "/MT", "/guard:cf", "/std:c17"):
            self.assertIn(marker, checkpoint)


class HostileAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract_hash = digest(CONTRACT)[1]
        cls.pe_hash = digest(PE)[1]
        cls.good = {
            "decision": "ACCEPTED_FOR_ONE_BOUNDED_NATIVE_DIAGNOSTIC_ONLY",
            "auditor_boundary": "different_fresh_exact_byte_static_auditor",
            "auditor_id": "fresh_auditor_example",
            "contract_sha256": cls.contract_hash,
            "native_executable_sha256": cls.pe_hash,
            "native_source_sha256": "1" * 64,
            "static_test_sha256": "2" * 64,
            "static_checkpoint_sha256": "3" * 64,
            "retained_manifest_sha256": "6df14df08a3f4c5a68c22b3eb3ccd8d8ce46209a156784a7582357071fc78d96",
            "v3r9_postmortem_sha256": "275fd7501a5d35ec6c5648a3935cafa56eb7854dfb80c173a2adc364738afed3",
        }

    def test_020_exact_fresh_auditor_fixture_accepts(self):
        self.assertTrue(simulated_audit_accepts(
            canonical_audit(self.good), self.contract_hash, self.pe_hash
        ))

    def test_021_author_identity_decision_and_boundary_substitution_fail(self):
        for key, value in (
            ("auditor_id", "codex_r25_afes_v3r10_recovery_author"),
            ("decision", "ACCEPTED"),
            ("auditor_boundary", "same_author"),
        ):
            hostile = dict(self.good, **{key: value})
            self.assertFalse(simulated_audit_accepts(
                canonical_audit(hostile), self.contract_hash, self.pe_hash
            ), key)

    def test_022_every_runtime_subject_substitution_fails(self):
        for key in (
            "contract_sha256", "native_executable_sha256",
            "retained_manifest_sha256", "v3r9_postmortem_sha256",
        ):
            hostile = dict(self.good, **{key: "0" * 64})
            self.assertFalse(simulated_audit_accepts(
                canonical_audit(hostile), self.contract_hash, self.pe_hash
            ), key)

    def test_023_noncanonical_rows_extra_rows_crlf_and_nul_fail(self):
        good = canonical_audit(self.good)
        variants = (
            good.replace(b"decision\t", b"decision \t", 1),
            good + b"extra\trow\n",
            good.replace(b"\n", b"\r\n"),
            good[:-1],
            good + b"\0",
        )
        for hostile in variants:
            self.assertFalse(simulated_audit_accepts(
                hostile, self.contract_hash, self.pe_hash
            ))


class PEStaticTests(unittest.TestCase):
    def test_030_pe_is_x64_pe32plus_cfg_nx_aslr(self):
        machine, magic, characteristics, _, _ = pe_shape(PE.read_bytes())
        self.assertEqual(machine, 0x8664)
        self.assertEqual(magic, 0x20B)
        for flag in (0x0040, 0x0100, 0x4000):
            self.assertTrue(characteristics & flag, hex(flag))

    def test_031_pe_has_no_python_or_blender_import(self):
        _, _, _, normal, delayed = pe_shape(PE.read_bytes())
        names = normal | delayed
        self.assertEqual(normal, {"kernel32.dll", "bcrypt.dll"})
        self.assertFalse(any("python" in name or "blender" in name for name in names))
        self.assertEqual(delayed, set())


if __name__ == "__main__":
    unittest.main()
