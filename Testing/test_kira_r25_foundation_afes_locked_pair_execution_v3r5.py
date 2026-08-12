"""Hostile static gates for append-only AFES locked-pair v3r5.

The suite never imports or executes the v3r5 controller, bootstrap, wrapper,
native PE, Blender, or any AFES extraction.  Python source is parsed/compiled
without evaluation, C is inspected as text, and the PE is inspected as bytes.
"""

from __future__ import annotations

import ast
import dis
import hashlib
import json
from pathlib import Path
import re
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_locked_pair_execution_v3r5.json"
CONTROLLER = ROOT / "tools/run_kira_r25_foundation_afes_locked_pair_v3r5.py"
BOOTSTRAP = ROOT / "tools/run_kira_r25_foundation_afes_locked_pair_bootstrap_v3r5.py"
WRAPPER = ROOT / "tools/blender_extract_kira_r25_foundation_afes_transition_rings_execution_v3r5.py"
NATIVE = ROOT / "tools/native/kira_r25_afes_locked_pair_launcher_v3r5.c"
PE = ROOT / "tools/native/kira_r25_afes_locked_pair_launcher_v3r5.exe"
CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution_static_preparation/"
    "attempt_03r5/CHECKPOINT.md"
)
MANIFEST = CHECKPOINT.with_name("RETAINED_NATIVE_LOCK_MANIFEST.tsv")
AUDIT = CHECKPOINT.with_name("INDEPENDENT_AUDIT.json")
OUTCOME = CHECKPOINT.with_name("EXECUTION_OUTCOME.receipt.bin")
OUTPUT_ROOT = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_foundation_afes_locked_pair_execution/attempt_03r5"
)

V3R4 = {
    "Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_locked_pair_execution_v3r4.json": (40892, "ddc25acaa90036d85ec0982051666fcc887af1d9d0063fac8b37c71547119737"),
    "tools/blender_extract_kira_r25_foundation_afes_transition_rings_execution_v3r4.py": (18750, "21a7c4e6649f48c8a259270dc258cc7980d1dd3d6c339173b9e2d3ca4a68bae7"),
    "tools/run_kira_r25_foundation_afes_locked_pair_v3r4.py": (31627, "2066d832a6988ffb1cbc70abf3a41eb002158959f000d842d6ec179ae9e2f30b"),
    "tools/run_kira_r25_foundation_afes_locked_pair_bootstrap_v3r4.py": (14929, "14b8a5432a64fb8af60025d3f54bcb8608f3e90aaf79c1bb8bb2ebeb62400a14"),
    "Testing/test_kira_r25_foundation_afes_locked_pair_execution_v3r4.py": (48317, "5433525b191135c5b69376f3bec620f5ebf4ea598e17da24e43179717a598e13"),
    "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_03r4/CHECKPOINT.md": (5020, "f5ce645cce83f5a4b58b6c597ba2a171c1d39dacc04b45c12471f394bedc5328"),
    "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_03r4/RETAINED_NATIVE_LOCK_MANIFEST.tsv": (15037, "0f2936fbd76c9a7eb75ff763991e47ff091fe413b91859ee873dda251ad2e10f"),
    "tools/native/kira_r25_afes_locked_pair_launcher_v3r4.exe": (244224, "6c1b79045758a0c58e0cd1dbb5889aa2f73cd7e0f96c2d54cde8313e84b4b387"),
    "tools/native/kira_r25_afes_locked_pair_launcher_v3r4.c": (185845, "40c9fb92fe5ac63cedc549fc288a1ddf1aeaaa1f469cf19c3f74253dc8f57beb"),
    "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_03r4/INDEPENDENT_AUDIT.md": (12008, "97a34c059b2ef17477d9042a06ef929574ced2e0ba3df72b27f1c00418d226a7"),
}
REQUIRED = (CONFIG, CONTROLLER, BOOTSTRAP, WRAPPER, NATIVE, PE, CHECKPOINT, MANIFEST)
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
EXPORTS = {
    "_build_execution_plan", "_validate_child_payload", "_compare_pair",
    "_success_payload", "_failure_payload",
}
EXPECTED_REACHABLE_TOP = {
    "LockedPairV3R5PlanError", "_audit_gate", "_bootstrap_contract",
    "_build_execution_plan", "_compare_pair", "_decode_blob",
    "_decode_edge_reference", "_decode_index_reference", "_exact_row",
    "_failure_payload", "_iter_contract_rows", "_native_launcher_contract",
    "_normalize_indices", "_outer_truth", "_pair_contract", "_process_contract",
    "_scope", "_sha256_bytes", "_signed64", "_strict_object",
    "_success_payload", "_truth_boundary", "_u32", "_validate_audit",
    "_validate_child_payload", "_validate_compact_afes_analysis",
    "_verify_retained_rows",
}
EXPECTED_GLOBALS = {
    "AUDIT_RELATIVE_PATH", "BLENDER_COMMAND_TEMPLATE", "CONSTANT_ENVIRONMENT",
    "CONTRACT_RELATIVE_PATH", "EDGE_SEMANTIC", "ENVIRONMENT_INHERITED_EXACT_KEYS",
    "INDEX_SEMANTIC", "LockedPairV3R5PlanError", "MANIFEST_RELATIVE_PATH",
    "MAX_FRAME_BYTES", "MAX_STDERR_BYTES", "MAX_STDOUT_BYTES",
    "MUTABLE_ENVIRONMENT_UNDER_UNIQUE_RUN_ROOT", "NANOMETERS_PER_METER",
    "OUTCOME_RELATIVE_PATH", "OUTPUT_RELATIVE_PATH", "ROUNDING_RULE",
    "SIGNED64_MAX", "SIGNED64_MIN", "UINT32_MAX", "_audit_gate",
    "_bootstrap_contract", "_decode_blob", "_decode_edge_reference",
    "_decode_index_reference", "_exact_row", "_iter_contract_rows",
    "_native_canonical_json_sha256", "_native_decode_u32_blob",
    "_native_is_lower_hex64", "_native_launcher_contract",
    "_native_parse_strict_json_object", "_native_sha256_hex",
    "_normalize_indices", "_outer_truth", "_pair_contract", "_process_contract",
    "_scope", "_sha256_bytes", "_signed64", "_strict_object",
    "_truth_boundary", "_u32", "_validate_audit",
    "_validate_compact_afes_analysis", "_verify_retained_rows", "any", "bytes",
    "dict", "int", "isinstance", "len", "list", "set", "sorted", "str",
    "tuple", "type",
}
SENSITIVE_ATTRS = {
    "__globals__", "__builtins__", "__dict__", "__class__", "__mro__",
    "__subclasses__", "__code__", "__closure__", "__self__", "f_globals",
    "gi_frame", "cr_frame", "tb_frame", "__loader__", "__spec__",
    "__getattribute__", "__annotate__", "__annotations__",
}
EXPECTED_CONTROLLER_ATTRS = {
    "__name__", "add", "append", "get", "intersection", "issubset",
    "items", "values",
}
EXPECTED_BOOTSTRAP_NAMES = {
    "BaseException", "BootstrapError", "NameError", "RuntimeError",
    "SystemExit", "__KIRA_NATIVE_BROKER_OBJECT_V3R5__",
    "__KIRA_NATIVE_CONTROLLER_CALLS_V3R5__",
    "__KIRA_NATIVE_SEED_IDENTITY_V3R5__",
    "__KIRA_RETAINED_BOOTSTRAP_LABEL__", "__KIRA_RETAINED_BOOTSTRAP_SHA256__",
    "__name__", "_broker", "_controller", "_retained_exit_code",
    "_retained_label", "_retained_native_main", "_retained_sha256", "_seed",
    "all", "any", "bytes", "callable", "dict", "int", "isinstance", "len",
    "set", "str", "tuple", "type",
}
EXPECTED_BOOTSTRAP_ATTRS = {
    "__name__", "after_snapshot", "append", "audit_bytes", "audit_identity",
    "broker_process_id", "canonical_json_sha256", "claim_nonce_bundle",
    "claim_once", "commit_failure_outcome", "commit_outcome",
    "create_output_root", "decode_receipt_frame", "encode_receipt_frame",
    "extend", "finish", "get", "is_lower_hex64", "locked_read", "locked_rows",
    "manifest_identity", "quiesce_owned_resources", "reserve_outcome",
    "run_child", "sha256_hex", "values", "write_evidence",
}


def digest(path: Path) -> tuple[int, str]:
    value = path.read_bytes()
    return len(value), hashlib.sha256(value).hexdigest()


def load_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise AssertionError("exact JSON object required")
    return value


def iter_rows(value: object):
    if type(value) is dict:
        if set(value) == {"path", "bytes", "sha256"}:
            yield value
        for child in value.values():
            yield from iter_rows(child)
    elif type(value) is list:
        for child in value:
            yield from iter_rows(child)


def parse_manifest(path: Path) -> list[tuple[str, str, int, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if lines[:2] != [
        "KIRA_R25_AFES_RETAINED_MANIFEST_V3R5\t1",
        "label\tpath\tbytes\tsha256",
    ]:
        raise AssertionError("manifest header drift")
    result = []
    for line in lines[2:]:
        fields = line.split("\t")
        if len(fields) != 4:
            raise AssertionError("manifest row shape")
        result.append((fields[0], fields[1], int(fields[2]), fields[3]))
    return result


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


def nested_codes(code: types.CodeType):
    yield code
    for constant in code.co_consts:
        if isinstance(constant, types.CodeType):
            yield from nested_codes(constant)


def controller_closure(source: str):
    module = compile(source, "<v3r5-controller-static>", "exec", flags=0x1000000, dont_inherit=True)
    top = {
        constant.co_name: constant for constant in module.co_consts
        if isinstance(constant, types.CodeType)
    }
    pending = list(EXPORTS)
    reachable = set()
    global_names = set()
    codes = []
    while pending:
        name = pending.pop()
        if name in reachable:
            continue
        code = top.get(name)
        if code is None:
            raise AssertionError(f"missing closure object {name}")
        reachable.add(name)
        for nested in nested_codes(code):
            codes.append(nested)
            for instruction in dis.get_instructions(nested):
                if instruction.opname == "LOAD_GLOBAL":
                    global_names.add(str(instruction.argval))
                    if instruction.argval in top and instruction.argval not in reachable:
                        pending.append(str(instruction.argval))
    return module, top, reachable, global_names, codes


class FrozenV3R4Tests(unittest.TestCase):
    def test_001_v3r4_rejection_graph_is_byte_frozen(self):
        for relative, expected in V3R4.items():
            self.assertEqual(digest(ROOT / relative), expected, relative)

    def test_002_controlling_rejection_hash_is_exact(self):
        self.assertEqual(V3R4[next(key for key in V3R4 if key.endswith("INDEPENDENT_AUDIT.md"))][1],
                         "97a34c059b2ef17477d9042a06ef929574ced2e0ba3df72b27f1c00418d226a7")

    def test_003_v3r4_has_no_execution_artifact(self):
        prior = CHECKPOINT.parent.parent / "attempt_03r4"
        self.assertFalse((prior / "EXECUTION_OUTCOME.receipt.bin").exists())


class SourcePresenceTests(unittest.TestCase):
    def test_010_all_v3r5_subjects_exist(self):
        self.assertEqual([path for path in REQUIRED if not path.is_file()], [])

    def test_011_no_execution_or_acceptance_exists(self):
        self.assertFalse(AUDIT.exists())
        self.assertFalse(OUTCOME.exists())
        self.assertFalse(OUTPUT_ROOT.exists())

    def test_012_names_are_append_only_v3r5(self):
        for path in REQUIRED:
            combined = path.name.lower() + path.parent.name.lower()
            self.assertTrue(
                "v3r5" in combined or "03r5" in combined, path
            )


class ControllerClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = CONTROLLER.read_text(encoding="utf-8")
        cls.module, cls.top, cls.reachable, cls.globals, cls.codes = controller_closure(cls.source)

    def test_020_controller_ast_has_zero_imports(self):
        tree = ast.parse(self.source)
        self.assertFalse(any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree)))

    def test_021_fixed_point_top_level_closure_is_exact(self):
        self.assertEqual(self.reachable, EXPECTED_REACHABLE_TOP)

    def test_022_fixed_point_global_dependency_set_is_exact(self):
        self.assertEqual(self.globals, EXPECTED_GLOBALS)

    def test_023_every_reachable_code_object_has_no_import_or_global_mutation(self):
        forbidden = {"IMPORT_NAME", "IMPORT_FROM", "IMPORT_STAR", "STORE_GLOBAL", "DELETE_GLOBAL"}
        for code in self.codes:
            self.assertFalse(forbidden.intersection(i.opname for i in dis.get_instructions(code)), code.co_name)

    def test_024_no_sensitive_attribute_traversal_is_reachable(self):
        observed = {
            str(i.argval) for code in self.codes for i in dis.get_instructions(code)
            if i.opname in {"LOAD_ATTR", "LOAD_METHOD"}
        }
        self.assertEqual(observed, EXPECTED_CONTROLLER_ATTRS)
        self.assertFalse(observed.intersection(SENSITIVE_ATTRS), observed)
        self.assertFalse({name for name in observed if name.startswith("__")}
                         - {"__name__"})

    def test_025_pep649_annotation_thunks_are_not_in_export_fixed_point(self):
        dormant = {c.co_name for c in nested_codes(self.module) if c.co_name == "__annotate__"}
        self.assertTrue(dormant)
        self.assertFalse(any(c.co_name == "__annotate__" for c in self.codes))

    def test_026_exact_five_exports_are_declared(self):
        self.assertIn("CONTROLLER_EXPORTED_CALLS", self.source)
        for export in EXPORTS:
            self.assertIn(f'"{export}"', self.source)

    def test_027_only_null_self_native_services_are_global_inputs(self):
        services = {
            name for name in self.globals
            if name.startswith("_native_") and name != "_native_launcher_contract"
        }
        self.assertEqual(services, {
            "_native_sha256_hex", "_native_is_lower_hex64",
            "_native_parse_strict_json_object", "_native_decode_u32_blob",
            "_native_canonical_json_sha256",
        })

    def test_028_complete_compact_validator_gate_family_exists(self):
        for marker in (
            "compact_blob_native_decode_type", "compact_duplicate_raw_blob",
            "compact_group_union_mismatch", "compact_union_vertex_bound",
            "compact_incident_face_bound", "compact_internal_face_bound",
            "compact_edge_vertex_bound", "compact_ring_order", "compact_rings_overlap",
            "compact_combined_ring_mismatch", "compact_ring_union_overlap",
            "compact_unreferenced_blob", "compact_structure_acceptance",
            "compact_bounds_codec", "compact_bounds_shape",
        ):
            self.assertIn(marker, self.source)

    def test_029_hostile_compact_corruption_matrix_is_closed(self):
        corruptions = {
            "base64": "compact_blob_native_decode_type",
            "raw_sha_or_ref": "_native_decode_u32_blob",
            "u32_order": "compact_index_order_invalid",
            "semantic_digest": "compact_index_digest",
            "group_union": "compact_group_union_mismatch",
            "vertex_bound": "compact_union_vertex_bound",
            "face_bound": "compact_incident_face_bound",
            "edge_bound": "compact_edge_vertex_bound",
            "ring_order": "compact_ring_order",
            "ring_overlap": "compact_rings_overlap",
            "ring_union_overlap": "compact_ring_union_overlap",
            "unreferenced_blob": "compact_unreferenced_blob",
            "structural_metrics": "compact_structure_acceptance",
            "bounds_signed64": "compact_signed64_invalid",
        }
        for marker in corruptions.values():
            self.assertIn(marker, self.source)

    def test_02a_v3r4_rejection_and_truth_are_controller_bound(self):
        self.assertIn('"locked_pair_v3r4_preservation"', self.source)
        self.assertIn("v3r4_preservation_drift", self.source)
        self.assertGreaterEqual(self.source.count("V3R4_REJECTED_AND_NOT_EXECUTED"), 2)


class BootstrapCapabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = BOOTSTRAP.read_text(encoding="utf-8")

    def test_030_bootstrap_has_zero_imports(self):
        tree = ast.parse(self.source)
        self.assertFalse(any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree)))

    def test_031_bootstrap_exact_seed_and_controller_shapes(self):
        for marker in ("type(_seed) is not dict", "type(_controller) is not dict", "all(", "callable("):
            self.assertIn(marker, self.source)

    def test_032_no_argparse_secrets_sys_or_path_loader(self):
        for forbidden in ("argparse", "secrets", "sys.modules", "pathlib", "load_private_dependency_graph"):
            self.assertNotIn(forbidden, self.source)

    def test_033_controller_never_receives_broker(self):
        controller_calls = self.source[self.source.index("_controller["):]
        self.assertNotIn("_controller[_broker", controller_calls)
        self.assertIn("_broker.run_child(plan, run_number)", self.source)

    def test_034_decoded_receipt_exact_shape_is_required(self):
        self.assertIn('set(decoded) != {', self.source)
        for key in ("payload", "payload_sha256", "frame_sha256"):
            self.assertIn(f'"{key}"', self.source)

    def test_035_failure_commit_is_native_measured_envelope_input(self):
        self.assertIn("_broker.commit_failure_outcome(failure)", self.source)
        self.assertNotIn("encode_receipt_frame(failure)", self.source)

    def test_036_bootstrap_complete_bytecode_closure_is_exact(self):
        module = compile(
            self.source, "<v3r5-bootstrap-static>", "exec",
            flags=0x1000000, dont_inherit=True,
        )
        codes = list(nested_codes(module))
        names = {
            str(instruction.argval)
            for code in codes for instruction in dis.get_instructions(code)
            if instruction.opname in {"LOAD_NAME", "LOAD_GLOBAL"}
        }
        attrs = {
            str(instruction.argval)
            for code in codes for instruction in dis.get_instructions(code)
            if instruction.opname in {"LOAD_ATTR", "LOAD_METHOD"}
        }
        forbidden = {
            instruction.opname
            for code in codes for instruction in dis.get_instructions(code)
            if instruction.opname.startswith("IMPORT") or
            instruction.opname in {"STORE_GLOBAL", "DELETE_GLOBAL"}
        }
        self.assertEqual(names, EXPECTED_BOOTSTRAP_NAMES)
        self.assertEqual(attrs, EXPECTED_BOOTSTRAP_ATTRS)
        self.assertEqual(forbidden, set())
        self.assertFalse(attrs.intersection(SENSITIVE_ATTRS))

    def test_037_parent_does_not_execute_path_based_v5_loader(self):
        controller = CONTROLLER.read_text(encoding="utf-8")
        loader = (ROOT / "tools/kira_r25_afes_topology_core_v5.py").read_text(encoding="utf-8")
        wrapper = WRAPPER.read_text(encoding="utf-8")
        self.assertNotIn("load_private_dependency_graph", self.source + controller)
        self.assertIn("tuple[Path, bytes]", wrapper)
        self.assertIn("Mapping[str, tuple[Path, bytes]]", wrapper)
        self.assertIn("isinstance(path, Path)", loader)
        self.assertIn("resolve(strict=True)", loader)


class NativeAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = NATIVE.read_text(encoding="utf-8")

    def test_040_exact_builtins_start_from_empty_dict(self):
        body = c_body(self.source, "build_exact_builtins")
        self.assertIn("PyDict_New()", body)
        self.assertNotIn("PyDict_Copy", body)
        loader = c_body(self.source, "load_pure_controller_calls")
        bootstrap = c_body(self.source, "execute_retained_bootstrap")
        self.assertIn("build_exact_builtins", loader)
        self.assertIn("build_exact_builtins", bootstrap)
        self.assertNotIn("PyEval_GetBuiltins", loader + bootstrap)

    def test_041_no_broker_import_or_sys_modules_registration(self):
        self.assertNotIn("PyImport_AppendInittab", self.source)
        self.assertNotIn("PyImport_ImportModule", c_body(self.source, "execute_retained_bootstrap"))
        self.assertNotIn("PyImport_AddModule", self.source)

    def test_042_all_controller_services_are_null_self(self):
        body = c_body(self.source, "new_null_self_callable")
        self.assertIn("PyCFunction_NewEx(definition, NULL, NULL)", body)
        self.assertIn("PyCFunction_GetSelf(callable) != NULL", body)
        loader = c_body(self.source, "load_pure_controller_calls")
        for name in ("pure_sha256_method", "pure_hex_method", "pure_json_method", "pure_blob_method", "pure_canonical_sha_method"):
            self.assertIn(f"new_null_self_callable(&{name})", loader)

    def test_042a_parent_import_delta_is_exact_closed_allowlist(self):
        allowed = c_body(self.source, "parent_module_delta_is_allowed")
        verifier = c_body(self.source, "verify_exact_parent_module_delta")
        execute = c_body(self.source, "execute_retained_bootstrap")
        exact = {
            "_abc", "_blake2", "_collections", "_collections_abc", "_functools",
            "_hashlib", "_json", "_operator", "_sre", "_types", "abc",
            "collections", "collections.abc", "copyreg", "enum", "functools",
            "hashlib", "itertools", "json", "json.decoder", "json.encoder",
            "json.scanner", "keyword", "operator", "re", "re._casefix",
            "re._compiler", "re._constants", "re._parser", "reprlib", "types",
        }
        observed = set(re.findall(r'"([A-Za-z0-9_.]+)"', allowed))
        self.assertEqual(observed, exact)
        for forbidden in ("os", "shutil", "subprocess", "pathlib", "ctypes"):
            self.assertNotIn(f'"{forbidden}"', allowed)
        self.assertIn("PySet_Contains", verifier)
        self.assertIn("parent_module_delta_is_allowed", verifier)
        self.assertIn("capture_parent_module_baseline", execute)
        self.assertIn("verify_exact_parent_module_delta", execute)

    def test_043_native_nonce_bundle_uses_bcrypt_and_exact_distinctness(self):
        nonce = c_body(self.source, "generate_nonce_hex")
        self.assertIn("BCryptGenRandom", nonce)
        claim = c_body(self.source, "py_claim_nonce_bundle")
        self.assertIn("run_nonce_1", claim)
        self.assertIn("run_nonce_2", claim)
        self.assertIn("strcmp", claim)

    def test_044_timeout_is_structural_exact_int_180(self):
        body = c_body(self.source, "parse_structural_contract_timeout")
        for marker in ("parse_strict_json_object_bytes", "process_contract", "process_timeout_seconds", "PyLong_CheckExact", "180L", "180000U"):
            self.assertIn(marker, body)
        self.assertNotIn("strstr", body)

    def test_045_hostile_timeout_decoys_are_rejected_by_parser_design(self):
        body = c_body(self.source, "parse_strict_json_object_bytes") + c_body(self.source, "parse_structural_contract_timeout")
        for marker in ("object_pairs_hook", "parse_float", "parse_constant"):
            self.assertIn(marker, body)
        # bool is not an exact PyLong; duplicate/trailing/embedded strings cannot
        # satisfy the structural nested-member lookup.
        self.assertIn("PyLong_CheckExact", body)
        self.assertIn("PyObject_Call(loads", body)

    def test_046_one_absolute_deadline_starts_after_resume(self):
        body = c_body(self.source, "py_run_child")
        resume = body.index("ResumeThread")
        deadline = body.index("absolute_deadline = GetTickCount64()")
        auth = body.rindex("authenticate_result_pipe_root_pid")
        wait = body.index("WaitForSingleObject(process.hProcess")
        self.assertLess(resume, deadline)
        self.assertLess(deadline, auth)
        self.assertLess(auth, wait)
        self.assertGreaterEqual(body.count("remaining_deadline_milliseconds"), 2)

    def test_047_overlapped_result_pipe_has_overlapped_read(self):
        auth = c_body(self.source, "authenticate_result_pipe_root_pid")
        drain = c_body(self.source, "drain_thread_main")
        self.assertIn("FILE_FLAG_OVERLAPPED", auth)
        self.assertIn("&operation", drain)
        self.assertIn("GetOverlappedResult", drain)
        self.assertIn("WaitForSingleObject(overlapped_event, INFINITE)", drain)
        self.assertIn("CancelIoEx", c_body(self.source, "cancel_join_and_destroy_drain"))
        self.assertIn("drains[0]->overlapped_read = 1", c_body(self.source, "py_run_child"))

    def test_048_no_null_overlapped_read_consumes_result_pipe(self):
        drain = c_body(self.source, "drain_thread_main")
        self.assertIsNotNone(re.search(
            r"if \(context->overlapped_read\).*?ReadFile\(.*?&operation\)",
            drain, re.S,
        ))
        self.assertIsNotNone(re.search(
            r"else \{\s*read_ok = ReadFile\(.*?NULL\)", drain, re.S,
        ))

    def test_049_drain_transfer_invalidates_caller_aliases(self):
        body = c_body(self.source, "py_run_child")
        for marker in (
            "drains[1]->read_handle = stdout_read;\n    stdout_read = INVALID_HANDLE_VALUE",
            "drains[2]->read_handle = stderr_read;\n    stderr_read = INVALID_HANDLE_VALUE",
            "drains[0]->read_handle = frame_read;\n    frame_read = INVALID_HANDLE_VALUE",
        ):
            self.assertIn(marker, body)
        cleanup = c_body(self.source, "cancel_join_and_destroy_drain")
        self.assertIn("snapshot->read_handle = INVALID_HANDLE_VALUE", cleanup)
        self.assertNotIn("context->read_handle = snapshot", cleanup)

    def test_04a_evidence_exact_set_and_package_completeness(self):
        writer = c_body(self.source, "py_write_evidence")
        commit = c_body(self.source, "py_commit_outcome")
        terminal = c_body(self.source, "build_native_terminal_failure_frame")
        for name in (
            "run_01_raw_frame.bin", "run_01_stdout.log", "run_01_stderr.log",
            "run_01_receipt.bin", "run_02_raw_frame.bin", "run_02_stdout.log",
            "run_02_stderr.log", "run_02_receipt.bin",
        ):
            self.assertIn(name, self.source)
        self.assertIn("evidence_exact_order_or_identity_refused", writer)
        self.assertIn("evidence_verified_write_count", commit)
        self.assertIn("evidence_verified_mask", commit)
        self.assertIn("evidence_package_complete", terminal)
        self.assertIn("all_attempted_evidence_writes_verified", terminal)
        self.assertIn("sha256_memory", writer)
        self.assertIn("constant_time_equal32(expected_hash, hash)", writer)
        self.assertIn("EVIDENCE_READBACK_DIGEST_MISMATCH", writer)

    def test_04aa_evidence_ledger_precedes_python_result_allocation(self):
        writer = c_body(self.source, "py_write_evidence")
        self.assertLess(
            writer.index("InterlockedIncrement"),
            writer.index("PyUnicode_FromStringAndSize"),
        )

    def test_04b_early_and_mid_package_failures_cannot_claim_complete(self):
        terminal = c_body(self.source, "build_native_terminal_failure_frame")
        self.assertIn("verified_evidence_count == 8L", terminal)
        self.assertIn("verified_evidence_mask == 0xffL", terminal)
        self.assertIn("evidence_verified_write_count", terminal)

    def test_04c_partial_measurement_uses_file_size_not_cursor(self):
        for name in ("record_partial_evidence", "record_partial_outcome"):
            body = c_body(self.source, name)
            self.assertIn("GetFileSizeEx", body)
            self.assertNotIn("FILE_CURRENT", body)
        self.assertIn("SIZE_MEASUREMENT_FAILED", self.source)
        self.assertIn("FULL_BYTES_UNVERIFIED", self.source)

    def test_04d_first_outcome_failure_is_never_overwritten(self):
        body = c_body(self.source, "record_partial_outcome")
        self.assertIn("InterlockedIncrement", body)
        self.assertIn("if (failure_count != 1L)", body)
        self.assertIn("multiple_outcome_write_failures", body)

    def test_04e_failure_core_hash_is_exact_native_binding(self):
        body = c_body(self.source, "py_commit_failure_outcome")
        self.assertIn("parse_hex64", body)
        self.assertIn("constant_time_equal32", body)
        self.assertIn("g_state.expected_contract_sha256", body)

    def test_04f_terminal_frames_are_canonical_k25_frames(self):
        native = c_body(self.source, "build_native_terminal_failure_frame")
        rewrite = c_body(self.source, "rewrite_terminal_outcome")
        self.assertIn('memcpy(frame, "K25RCPT!", 8U)', native)
        self.assertIn("write_be32", native)
        self.assertIn("write_be64", native)
        self.assertIn("sha256_memory", native)
        self.assertIn("sha256_handle", rewrite)
        self.assertIn("observed_bytes != (uint64_t)size", rewrite)
        keys = re.findall(r'\\\"([a-z0-9_]+)\\\":', native)
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(len(keys), len(set(keys)))

    def test_04g_late_success_is_provisional_and_superseded_on_failure(self):
        commit = c_body(self.source, "py_commit_outcome")
        emergency = c_body(self.source, "commit_native_failure_if_reserved")
        execute = c_body(self.source, "execute_retained_bootstrap")
        terminal = c_body(self.source, "build_native_terminal_failure_frame")
        self.assertIn("outcome_success_provisional = 1", commit)
        self.assertIn("stage_terminal_outcome", commit)
        self.assertNotIn("rewrite_terminal_outcome", commit)
        self.assertIn("g_state.staged_outcome_frame == NULL", emergency)
        self.assertIn("Py_FinalizeEx", execute)
        self.assertLess(execute.index("Py_FinalizeEx"),
                        execute.index("rewrite_terminal_outcome"))
        self.assertIn("staged_outcome_superseded", terminal)
        self.assertIn("staged_outcome_sha256", terminal)

    def test_04ga_success_write_fallback_cannot_be_reported_as_success(self):
        rewrite = c_body(self.source, "rewrite_terminal_outcome")
        execute = c_body(self.source, "execute_retained_bootstrap")
        self.assertIn("TERMINAL_REWRITE_PRIMARY_VERIFIED", rewrite)
        self.assertIn("TERMINAL_REWRITE_FALLBACK_FAILURE_VERIFIED", rewrite)
        self.assertIn(
            "terminal_result == TERMINAL_REWRITE_PRIMARY_VERIFIED", execute
        )
        self.assertIn(
            "TERMINAL_REWRITE_FALLBACK_FAILURE_VERIFIED", execute,
        )
        self.assertIn("outcome_success_provisional = 0", execute)

    def test_04gb_first_attempt_identity_survives_terminal_fallback(self):
        rewrite = c_body(self.source, "rewrite_terminal_outcome")
        terminal = c_body(self.source, "build_native_terminal_failure_frame")
        self.assertIn("outcome_first_attempt_sha256", rewrite)
        self.assertIn("outcome_first_attempt_bytes", rewrite)
        for kind in ("SUCCESS", "CALLER_FAILURE", "NATIVE_FAILURE"):
            self.assertIn(f'"{kind}"', self.source)
        for field in (
            "outcome_attempt_count", "outcome_current_attempt_bytes",
            "outcome_current_attempt_kind", "outcome_current_attempt_seen",
            "outcome_current_attempt_sha256",
            "outcome_current_attempt_sha256_known",
            "outcome_first_attempt_bytes", "outcome_first_attempt_kind",
            "outcome_first_attempt_seen",
            "outcome_first_attempt_sha256",
            "outcome_first_attempt_sha256_known",
        ):
            self.assertIn(field, terminal)

    def test_04gc_all_python_terminal_frames_are_staged_until_finalize(self):
        success = c_body(self.source, "py_commit_outcome")
        failure = c_body(self.source, "py_commit_failure_outcome")
        execute = c_body(self.source, "execute_retained_bootstrap")
        for body, kind in ((success, "SUCCESS"), (failure, "CALLER_FAILURE")):
            self.assertIn("stage_terminal_outcome", body)
            self.assertIn(f'"{kind}"', body)
            self.assertNotIn("rewrite_terminal_outcome", body)
        self.assertIn('strcmp(g_state.staged_outcome_kind, "SUCCESS")', execute)
        self.assertIn(
            'strcmp(g_state.staged_outcome_kind, "CALLER_FAILURE")', execute)
        self.assertLess(execute.index("Py_FinalizeEx"),
                        execute.index("rewrite_terminal_outcome"))

    def test_04gca_late_gates_dominate_success_and_caller_failure_flush(self):
        execute = c_body(self.source, "execute_retained_bootstrap")
        failed_start = execute.index("if (evaluation == NULL)")
        failed_eval = execute[
            failed_start:execute.index("goto cleanup;", failed_start)
        ]
        self.assertIn("g_state.finished", failed_eval)
        self.assertIn("verify_exact_parent_module_delta", failed_eval)
        flush_gate = (
            "if (!finalize_failed && terminal_gate_checked && terminal_gate_ok &&"
        )
        self.assertIn(flush_gate, execute)
        gated = execute[execute.index(flush_gate):]
        self.assertIn('strcmp(g_state.staged_outcome_kind, "SUCCESS")', gated)
        self.assertIn(
            'strcmp(g_state.staged_outcome_kind, "CALLER_FAILURE")', gated)

    def test_04gd_finalize_failure_is_preserved_with_primary_truth(self):
        execute = c_body(self.source, "execute_retained_bootstrap")
        recorder = c_body(self.source, "record_native_cleanup_failure")
        terminal = c_body(self.source, "build_native_terminal_failure_frame")
        self.assertIn("if (initialized && Py_FinalizeEx() < 0)", execute)
        self.assertIn("record_native_cleanup_failure", execute)
        self.assertIn("used == 0U", recorder)
        self.assertIn("native_cleanup_failure_count", terminal)
        self.assertIn("native_cleanup_failure", terminal)

    def test_04ge_cleanup_error_recording_failure_is_fail_closed(self):
        cleanup = c_body(self.source, "cleanup_add")
        drop = c_body(self.source, "cleanup_record_drop")
        run = c_body(self.source, "py_run_child")
        composite = c_body(self.source, "set_composite_child_error")
        self.assertGreaterEqual(cleanup.count("cleanup_record_drop"), 3)
        self.assertIn("recording_failed = 1", drop)
        self.assertIn("dropped_count", drop)
        self.assertIn("cleanup.recording_failed", run)
        self.assertIn("cleanup_error_recording_failed", composite)

    def test_04h_canonical_receipt_subset_is_ascii_and_bounded(self):
        canonical = c_body(self.source, "validate_canonical_value")
        self.assertIn("character > 0x7fU", canonical)
        self.assertIn("depth > 32U", canonical)
        self.assertIn("*nodes) > 8192U", canonical)
        strict = c_body(self.source, "parse_strict_json_object_bytes")
        for marker in ("json_reject_method", "parse_constant", "object_pairs_hook"):
            self.assertIn(marker, strict)

    def test_04i_unicode_and_numeric_hostile_cases_are_explicitly_closed(self):
        canonical = c_body(self.source, "validate_canonical_value")
        self.assertIn("PyLong_CheckExact", canonical)
        self.assertIn("PyLong_AsLongLongAndOverflow", canonical)
        self.assertIn("overflow != 0", canonical)
        self.assertIn("PyFloat_Check", canonical)
        self.assertIn("canonical_json_float_refused", canonical)
        # ASCII-only rejects decomposed e+0301, precomposed e-acute, and surrogates.
        self.assertIn("0x7fU", canonical)

    def test_04j_result_writer_is_one_win32_owner(self):
        wrapper = WRAPPER.read_text(encoding="utf-8")
        writer = wrapper[wrapper.index("def _write_result_frame_win32"):wrapper.index("def _parse_object")]
        self.assertIn("kernel32.WriteFile", writer)
        self.assertNotIn("open_osfhandle", wrapper)
        self.assertNotIn("import msvcrt", wrapper)
        self.assertNotIn("msvcrt.", wrapper)
        self.assertNotIn("write_result_frame(", writer)
        main = wrapper[wrapper.index("def main("):]
        self.assertIn("result_pipe = 0", main)
        self.assertEqual(main.count("_close_result_pipe(owned_handle)"), 1)

    def test_04k_restricted_environment_omits_path_and_parent_temp(self):
        body = c_body(self.source, "native_restricted_environment")
        for key in ("SYSTEMROOT", "WINDIR", "USERNAME", "TEMP", "TMP", "PYTHONNOUSERSITE", "PYTHONDONTWRITEBYTECODE", "PYTHONHASHSEED"):
            self.assertIn(key, body)
        self.assertNotIn('L"PATH"', body)

    def test_04l_build_contract_is_warning_as_error_and_cfg(self):
        checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        for marker in ("/W4", "/WX", "/guard:cf", "/std:c17"):
            self.assertIn(marker, checkpoint)


@unittest.skipUnless(all(path.is_file() for path in REQUIRED), "v3r5 package incomplete")
class ContractManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_object(CONFIG)
        cls.rows = parse_manifest(MANIFEST)

    def test_050_contract_identity_and_static_status(self):
        self.assertEqual(self.contract["schema"], "kira.avatar.r25.foundation_afes_locked_pair_execution.v3r5")
        self.assertEqual(self.contract["attempt_id"], "attempt_03r5")
        self.assertEqual(self.contract["status"], "PENDING_FRESH_INDEPENDENT_AUDIT_READ_ONLY_DIAGNOSTIC_PAIR_ONLY")

    def test_051_all_six_findings_and_hidden_r7_are_named(self):
        self.assertEqual(set(self.contract["repair_boundaries"]), {
            "r1_controller_dependency_closure", "r2_restricted_exec_and_import_graph",
            "r3_single_result_pipe_owner", "r4_native_exact_timeout",
            "r5_drain_alias_invalidation", "r6_native_terminal_truth",
            "r7_no_parent_path_loader_authority",
        })

    def test_052_v3r4_preservation_is_complete_and_exact(self):
        rows = self.contract["locked_pair_v3r4_preservation"]
        self.assertEqual({row["path"] for row in rows.values()}, set(V3R4))
        for row in rows.values():
            self.assertEqual((row["bytes"], row["sha256"]), V3R4[row["path"]])

    def test_053_controlling_rejection_is_bound_not_accepted(self):
        preservation = self.contract["locked_pair_v3r4_preservation"]
        self.assertEqual(preservation["rejection_audit"]["sha256"],
                         "97a34c059b2ef17477d9042a06ef929574ced2e0ba3df72b27f1c00418d226a7")
        self.assertIn("REJECTED", self.contract["authorization_basis"])

    def test_054_manifest_is_unique_canonical_and_exact(self):
        labels = [row[0] for row in self.rows]
        paths = [row[1] for row in self.rows]
        self.assertEqual(labels, sorted(labels))
        self.assertEqual(len(labels), len(set(labels)))
        self.assertEqual(len(paths), len(set(paths)))
        for _, relative, size, sha in self.rows:
            self.assertTrue(HEX64.fullmatch(sha))
            self.assertEqual(digest(ROOT / relative), (size, sha), relative)

    def test_055_manifest_equals_recursive_contract_graph_plus_contract(self):
        expected = {row["path"] for row in iter_rows(self.contract)} | {CONFIG.relative_to(ROOT).as_posix()}
        self.assertEqual({row[1] for row in self.rows}, expected)

    def test_056_every_new_subject_is_contract_bound(self):
        paths = {row["path"] for row in iter_rows(self.contract)}
        for path in (CONTROLLER, BOOTSTRAP, WRAPPER, NATIVE, PE, CHECKPOINT, Path(__file__)):
            self.assertIn(path.relative_to(ROOT).as_posix(), paths)

    def test_057_native_pe_is_static_bound_image(self):
        value = PE.read_bytes()
        self.assertEqual(value[:2], b"MZ")
        self.assertIn(b"python314.dll", value.lower())
        self.assertIn(b"bcrypt.dll", value.lower())

    def test_058_checkpoint_freezes_no_execution_claim(self):
        text = CHECKPOINT.read_text(encoding="utf-8")
        self.assertIn("NOT EXECUTED", text)
        self.assertIn("external independent audit", text)
        self.assertIn("97a34c059b2ef17477d9042a06ef929574ced2e0ba3df72b27f1c00418d226a7", text)

    def test_059_no_accepted_audit_outcome_or_output_root(self):
        self.assertFalse(AUDIT.exists())
        self.assertFalse(OUTCOME.exists())
        self.assertFalse(OUTPUT_ROOT.exists())


if __name__ == "__main__":
    unittest.main()
