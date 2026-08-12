#!/usr/bin/env python3
"""Hostile static and real-Windows tests for locked-pair Attempt 06.

The real Windows tests create only temporary nonce-private directory trees and
ordinary Python attack processes.  They do not invoke the controller entry,
Blender, the AFES extractor, a body, or the configured execution/runtime root.
"""

from __future__ import annotations

import base64
import builtins
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock

from tools import launch_kira_r25_foundation_afes_locked_pair_v6 as bootstrap
from tools import run_kira_r25_foundation_afes_locked_pair_v6 as controller
from tools import run_kira_r25_foundation_afes_locked_pair_v5 as controller_v5


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / bootstrap.CONTRACT_RELATIVE_PATH
V5_CONTRACT = ROOT / bootstrap.PRESERVED_ATTEMPT05["contract"]["path"]
AUDIT = ROOT / bootstrap.AUDIT_RELATIVE_PATH
OUTPUT = ROOT / controller.OUTPUT_RELATIVE_PATH
RUNTIME = ROOT / controller.RUNTIME_BASE_RELATIVE_PATH
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
EMPTY_REF = f"sha256:{EMPTY_SHA256}"


def file_row(path: Path) -> tuple[int, str]:
    value = path.read_bytes()
    return len(value), hashlib.sha256(value).hexdigest()


def index_ref(count: int, digest: str) -> dict[str, object]:
    return {
        "blob_ref": EMPTY_REF,
        "semantic": controller_v5.INDEX_SEMANTIC,
        "item_count": count,
        "semantic_sha256": digest,
    }


def edge_ref(count: int, digest: str) -> dict[str, object]:
    return {
        "blob_ref": EMPTY_REF,
        "semantic": controller_v5.EDGE_SEMANTIC,
        "item_count": count,
        "semantic_sha256": digest,
    }


class FakeExactCompactValidator:
    def __init__(self, foundation: dict[str, object]) -> None:
        self.foundation = foundation

    def validate_compact_afes_analysis(self, _compact: object) -> dict[str, object]:
        groups = {
            name: tuple(range(row["vertex_count"]))
            for name, row in self.foundation["required_groups"].items()
        }
        union = self.foundation["afes_union"]
        return {
            "groups": groups,
            "afes_union": tuple(range(union["vertex_count"])),
            "incident_faces": tuple(range(union["incident_face_count"])),
            "internal_faces": tuple(range(union["internal_face_count"])),
            "connection_edges": tuple(
                (index, index + 1)
                for index in range(union["primary_connection_edge_count"])
            ),
            "transition_rings": ((0,), (1,)),
            "combined_transition_vertices": (0, 1),
        }


class Attempt06Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_bytes = CONTRACT.read_bytes()
        cls.contract = bootstrap._parse_json(cls.contract_bytes, "test_contract")
        cls.contract_sha256 = hashlib.sha256(cls.contract_bytes).hexdigest()
        cls.v5_contract = json.loads(V5_CONTRACT.read_text(encoding="utf-8"))
        v4_path = ROOT / cls.v5_contract["inherited_attempt04_contract"]["path"]
        cls.v4_contract = json.loads(v4_path.read_text(encoding="utf-8"))
        afes_v5_path = ROOT / cls.v4_contract[
            "child_project_read_closure"
        ]["afes_v5_config"]["path"]
        afes_v5 = json.loads(afes_v5_path.read_text(encoding="utf-8"))
        afes_v4 = json.loads((ROOT / afes_v5[
            "attempt_04_baseline_config"
        ]["path"]).read_text(encoding="utf-8"))
        afes_v3 = json.loads((ROOT / afes_v4[
            "attempt_03_baseline_config"
        ]["path"]).read_text(encoding="utf-8"))
        cls.v2 = json.loads((ROOT / afes_v3[
            "attempt_02_baseline_config"
        ]["path"]).read_text(encoding="utf-8"))
        cls.foundation = cls.v2["foundation_contract"]
        cls.validator = FakeExactCompactValidator(cls.foundation)

    def valid_analysis(self) -> dict[str, object]:
        foundation = self.foundation
        topology = "1" * 64
        groups = {
            name: {
                "vertex_indices": index_ref(
                    expected["vertex_count"], expected["vertex_index_sha256"],
                )
            }
            for name, expected in foundation["required_groups"].items()
        }
        union = foundation["afes_union"]
        return {
            "whole_mesh": {
                "vertex_count": foundation["vertices"],
                "edge_count": foundation["edges"],
                "face_count": foundation["faces"],
                "topology_sha256": topology,
            },
            "topology_structure": {
                **foundation["required_topology_structure"],
                "full_normalized_topology_sha256": topology,
            },
            "groups": groups,
            "afes_union": {
                "vertex_indices": index_ref(
                    union["vertex_count"], union["vertex_index_sha256"],
                ),
                "incident_face_indices": index_ref(
                    union["incident_face_count"], union["incident_face_index_sha256"],
                ),
                "internal_face_indices": index_ref(
                    union["internal_face_count"], union["internal_face_index_sha256"],
                ),
                "primary_connection_edges": edge_ref(
                    union["primary_connection_edge_count"],
                    union["connection_edge_sha256"],
                ),
            },
            "transition_rings": {
                "ring_count": 2,
                "rings": [
                    {"ring_number": 1, "vertex_indices": index_ref(1, "2" * 64)},
                    {"ring_number": 2, "vertex_indices": index_ref(1, "3" * 64)},
                ],
                "combined_vertex_indices": index_ref(2, "4" * 64),
                "disjoint_from_afes_union": True,
            },
            "bounds_object_nm": {
                "unit": "nanometer",
                "integer_units_per_meter": 1_000_000_000,
                "rounding": controller_v5.ROUNDING_RULE,
                **copy.deepcopy(foundation["expected_bounds_object_nanometers"]),
            },
            "binary_arrays": {
                EMPTY_REF: {
                    "codec": controller_v5.BLOB_CODEC,
                    "endianness": "big",
                    "u32_count": 0,
                    "raw_bytes": 0,
                    "raw_sha256": EMPTY_SHA256,
                    "base64": "",
                }
            },
        }

    def exact_audit(self) -> dict[str, object]:
        return {
            "schema": "kira.avatar.r25.foundation_afes_locked_pair_independent_audit.v6",
            "attempt_id": "attempt_06",
            "decision": {
                "accepted": True,
                "code": "ACCEPTED_FOR_ONE_BOUNDED_READ_ONLY_PAIR_ONLY",
                "scope": "ONE_FRESH_LOCKED_AFES_DIAGNOSTIC_PAIR",
            },
            "reviewed_execution_artifacts": bootstrap._expected_audit_artifacts(
                self.contract, self.contract_bytes, self.contract_sha256,
            ),
            "recursive_closure_sha256": self.contract[
                "recursive_closure_contract"
            ]["canonical_closure_sha256"],
            "truth_boundary": {
                "body_authoring_authorized": False,
                "one_bounded_pair_authorized": True,
                "owner_body_approval": False,
                "static_review_did_not_run_blender": True,
            },
        }

    def temporary_tree(self, nonce: str = "a" * 64):
        holder = tempfile.TemporaryDirectory(
            dir=(ROOT / "RecoverySprint/runtime_cache").resolve()
        )
        tree = controller.SecureRuntimeTree.create(
            pair_session_nonce=nonce, project_root=Path(holder.name),
            base_relative_path="runtime", run_nonces={1: "1" * 64, 2: "2" * 64},
        )
        return holder, tree

    def test_01_attempt05_and_exact_rejection_audit_are_byte_preserved(self) -> None:
        self.assertEqual(
            self.contract["preserved_rejected_attempt05"],
            bootstrap.PRESERVED_ATTEMPT05,
        )
        for row in bootstrap.PRESERVED_ATTEMPT05.values():
            path = ROOT / row["path"]
            self.assertEqual(file_row(path), (row["bytes"], row["sha256"]))
        self.assertEqual(
            bootstrap.PRESERVED_ATTEMPT05["rejection_audit"]["sha256"],
            "da85fab5053272e2f53589825014d05ce4a0381f6ddf5b447934bf791ca926aa",
        )

    def test_02_exact_inherited_35_file_closure_is_reproduced(self) -> None:
        closure = self.v4_contract["child_project_read_closure"]
        by_path = {str(row["path"]): dict(row) for row in closure.values()}
        self.assertEqual(len(closure), 35)
        self.assertEqual(len(by_path), 35)
        self.assertEqual(
            hashlib.sha256(bootstrap._canonical_json_bytes(by_path)).hexdigest(),
            "cde7ed10ab51b5ed57405b47aba0d986aff96e529fa637cc75dd3f4a7ad7b591",
        )
        self.assertTrue(bootstrap.REQUIRED_MISSING_V2_PATHS.issubset(by_path))

    def test_03_new_contract_sections_and_sources_are_exact(self) -> None:
        bootstrap._validate_exact_contract_sections(self.contract)
        for row in self.contract["execution_sources"].values():
            path = ROOT / row["path"]
            self.assertEqual(file_row(path), (row["bytes"], row["sha256"]))

    def test_04_ambient_import_and_duck_context_fail_before_side_effects(self) -> None:
        self.assertFalse(hasattr(controller, "_authorized_pair"))
        with self.assertRaisesRegex(
            controller.LockedPairV6Error,
            "ambient_import_has_no_bootstrap_capability",
        ):
            controller.run_locked_pair(
                bootstrap_context=SimpleNamespace(
                    locks_active=True, controller_private_execution=True,
                ),
                bootstrap_capability=object(),
                expected_contract_sha256="0" * 64,
                accepted_audit_sha256="1" * 64,
            )

    def test_05_private_capability_is_exact_context_bound_and_one_use(self) -> None:
        source_path = ROOT / self.contract["execution_sources"][
            "private_controller"
        ]["path"]
        source = source_path.read_bytes()
        capability = object()
        context = object()
        private = ModuleType("_attempt06_capability_test")
        private.__file__ = str(source_path)
        private.__package__ = ""
        private.__spec__ = None
        private.__loader__ = None
        private.__dict__["__builtins__"] = dict(vars(builtins))
        private.__dict__["_KIRA_BOOTSTRAP_INJECTION"] = (capability, context)
        exec(compile(source, str(source_path), "exec"), private.__dict__, private.__dict__)
        calls: list[dict[str, object]] = []
        self.assertFalse(hasattr(private, "_authorized_pair"))
        closure = dict(zip(
            private.run_locked_pair.__code__.co_freevars,
            private.run_locked_pair.__closure__ or (),
        ))
        closure["authorized_pair"].cell_contents = (
            lambda **kwargs: calls.append(kwargs) or Path("accepted")
        )
        with self.assertRaisesRegex(
            private.LockedPairV6Error, "bootstrap_capability_identity_mismatch",
        ):
            private.run_locked_pair(
                bootstrap_context=context, bootstrap_capability=object(),
                expected_contract_sha256="0" * 64,
                accepted_audit_sha256="1" * 64,
            )
        with self.assertRaisesRegex(
            private.LockedPairV6Error, "bootstrap_context_identity_mismatch",
        ):
            private.run_locked_pair(
                bootstrap_context=object(), bootstrap_capability=capability,
                expected_contract_sha256="0" * 64,
                accepted_audit_sha256="1" * 64,
            )
        self.assertEqual(
            private.run_locked_pair(
                bootstrap_context=context, bootstrap_capability=capability,
                expected_contract_sha256="0" * 64,
                accepted_audit_sha256="1" * 64,
            ),
            Path("accepted"),
        )
        with self.assertRaisesRegex(
            private.LockedPairV6Error, "bootstrap_capability_already_consumed",
        ):
            private.run_locked_pair(
                bootstrap_context=context, bootstrap_capability=capability,
                expected_contract_sha256="0" * 64,
                accepted_audit_sha256="1" * 64,
            )
        self.assertEqual(len(calls), 1)

    def test_06_recursive_foundation_bound_valid_result_is_preserved(self) -> None:
        topology = controller_v5._validate_foundation_bound_analysis(
            self.valid_analysis(), v2=self.v2, attempt03=self.validator,
        )
        self.assertEqual(topology, "1" * 64)

    def test_07_toy_foundation_and_nested_extra_remain_rejected(self) -> None:
        toy = self.valid_analysis()
        toy["whole_mesh"]["vertex_count"] = 7
        with self.assertRaises(controller_v5.LockedPairV5Error):
            controller_v5._validate_foundation_bound_analysis(
                toy, v2=self.v2, attempt03=self.validator,
            )
        extra = self.valid_analysis()
        name = next(iter(extra["groups"]))
        extra["groups"][name]["unexpected"] = True
        with self.assertRaises(controller_v5.LockedPairV5Error):
            controller_v5._validate_foundation_bound_analysis(
                extra, v2=self.v2, attempt03=self.validator,
            )

    @unittest.skipUnless(os.name == "nt", "real Windows DACL test")
    def test_08_real_windows_dacl_denies_protected_child_creation(self) -> None:
        holder, tree = self.temporary_tree("8" * 64)
        try:
            target = tree.runs[1]["user_scripts"].path / "foreign.py"
            with self.assertRaises(OSError):
                target.write_text("foreign", encoding="utf-8")
            with self.assertRaises(OSError):
                target.parent.joinpath("foreign_dir").mkdir()
            self.assertFalse(target.exists())
            tree.verify_before_any_child()
        finally:
            tree.close(suppress_errors=True)
            holder.cleanup()

    @unittest.skipUnless(os.name == "nt", "real Windows separate-process DACL test")
    def test_09_real_separate_process_cannot_create_then_delete_transient(self) -> None:
        holder, tree = self.temporary_tree("9" * 64)
        try:
            target = tree.runs[1]["user_scripts"].path / "transient.py"
            script = (
                "from pathlib import Path\nimport sys\n"
                "p=Path(sys.argv[1])\n"
                "try:\n p.write_text('x',encoding='utf-8'); p.unlink(); print('SUCCEEDED')\n"
                "except OSError as e:\n print('DENIED',type(e).__name__); raise SystemExit(17)\n"
            )
            result = subprocess.run(
                [sys.executable, "-B", "-c", script, str(target)],
                cwd=str(ROOT), capture_output=True, text=True, timeout=20,
                check=False,
            )
            self.assertEqual(result.returncode, 17, result.stdout + result.stderr)
            self.assertIn("DENIED", result.stdout)
            self.assertFalse(target.exists())
            tree.verify_before_any_child()
        finally:
            tree.close(suppress_errors=True)
            holder.cleanup()

    @unittest.skipUnless(os.name == "nt", "real Windows handle rename test")
    def test_10_real_handles_block_pair_run_leaf_and_temp_replacement(self) -> None:
        holder, tree = self.temporary_tree("a" * 64)
        try:
            paths = [
                tree.pair.path,
                tree.runs[1]["root"].path,
                tree.runs[1]["user_config"].path,
                tree.runs[1]["temp"].path,
            ]
            for index, source in enumerate(paths):
                with self.subTest(path=source):
                    with self.assertRaises(OSError):
                        os.rename(source, source.with_name(f"replacement_{index}"))
            tree.verify_before_any_child()
        finally:
            tree.close(suppress_errors=True)
            holder.cleanup()

    @unittest.skipUnless(os.name == "nt", "real Windows sticky notification test")
    def test_11_real_change_sentinel_detects_transient_create_delete(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=(ROOT / "RecoverySprint/runtime_cache").resolve()
        ) as directory:
            sentinel = controller.WindowsChangeSentinel(Path(directory))
            try:
                transient = Path(directory) / "transient.tmp"
                transient.write_bytes(b"x")
                transient.unlink()
                for _ in range(50):
                    if sentinel.changed():
                        break
                    time.sleep(0.01)
                self.assertTrue(sentinel.changed())
                with self.assertRaises(controller.LockedPairV6Error):
                    sentinel.verify_unchanged("transient_probe")
            finally:
                sentinel.close()

    @unittest.skipUnless(os.name == "nt", "real Windows DACL mutation test")
    def test_12_real_security_change_is_sticky_and_fails_verification(self) -> None:
        holder, tree = self.temporary_tree("b" * 64)
        try:
            boundary = next(
                item for item in tree.boundaries
                if item.label == "run_01_user_scripts"
            )
            boundary._install_world_deny_mask(boundary.FILE_WRITE_ATTRIBUTES)
            for _ in range(50):
                if boundary.sentinel.changed():
                    break
                time.sleep(0.01)
            with self.assertRaises(controller.LockedPairV6Error):
                boundary.verify()
        finally:
            tree.close(suppress_errors=True)
            holder.cleanup()

    @unittest.skipUnless(os.name == "nt", "real Windows identity test")
    def test_13_handle_manifest_binds_unique_file_ids_and_exact_ancestry(self) -> None:
        holder, tree = self.temporary_tree("c" * 64)
        try:
            manifest = tree.identity_manifest()
            identities = {
                (row["volume_serial"], row["file_index"]) for row in manifest
            }
            self.assertEqual(len(identities), len(manifest))
            self.assertTrue(all(not row["reparse_point"] for row in manifest))
            self.assertTrue(all(row["delete_sharing"] is False for row in manifest))
            tree.verify_all_identities()
        finally:
            tree.close(suppress_errors=True)
            holder.cleanup()

    @unittest.skipUnless(os.name == "nt", "real Windows preoccupation test")
    def test_14_preoccupied_nonce_pair_scope_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=(ROOT / "RecoverySprint/runtime_cache").resolve()
        ) as directory:
            project = Path(directory)
            base = project / "runtime"
            base.mkdir()
            token = hashlib.sha256(("d" * 64).encode("ascii")).hexdigest()[:32]
            (base / f"pair_{token}").mkdir()
            with self.assertRaisesRegex(
                controller.LockedPairV6Error, "runtime_pair_scope_preoccupied",
            ):
                controller.SecureRuntimeTree.create(
                    pair_session_nonce="d" * 64, project_root=project,
                    base_relative_path="runtime",
                    run_nonces={1: "1" * 64, 2: "2" * 64},
                )

    @unittest.skipUnless(os.name == "nt", "real Windows environment test")
    def test_15_two_runs_are_precreated_distinct_and_environment_is_exact(self) -> None:
        holder, tree = self.temporary_tree("e" * 64)
        try:
            self.assertNotEqual(tree.runs[1]["root"].file_id, tree.runs[2]["root"].file_id)
            env = tree.prepare_environment(
                blender=Path(sys.executable), run_number=1, run_nonce="1" * 64,
                pair_session_nonce="e" * 64,
            )
            self.assertEqual(Path(env["TEMP"]), tree.runs[1]["temp"].path)
            self.assertEqual(Path(env["BLENDER_USER_CONFIG"]), tree.runs[1]["user_config"].path)
            self.assertEqual(Path(env["BLENDER_USER_SCRIPTS"]), tree.runs[1]["user_scripts"].path)
            self.assertEqual(Path(env["BLENDER_USER_DATAFILES"]), tree.runs[1]["user_datafiles"].path)
            tree.runs[1]["temp"].path.joinpath("allowed.tmp").write_bytes(b"runtime")
            tree.verify_after_child(1)
            with self.assertRaises(controller.LockedPairV6Error):
                tree.prepare_environment(
                    blender=Path(sys.executable), run_number=1,
                    run_nonce="1" * 64, pair_session_nonce="e" * 64,
                )
        finally:
            tree.close(suppress_errors=True)
            holder.cleanup()

    def test_16_pre_audit_and_post_audit_lifecycle_are_both_valid(self) -> None:
        exact = self.exact_audit()
        bootstrap._validate_structured_audit(
            audit_bytes=bootstrap._canonical_json_bytes(exact),
            contract=self.contract,
            expected_contract_sha256=self.contract_sha256,
            retained_contract_bytes=self.contract_bytes,
        )
        if AUDIT.exists():
            audit_bytes = AUDIT.read_bytes()
            bootstrap._validate_structured_audit(
                audit_bytes=audit_bytes, contract=self.contract,
                expected_contract_sha256=self.contract_sha256,
                retained_contract_bytes=self.contract_bytes,
            )

    def test_17_audit_extra_boolean_alias_and_hash_drift_fail_closed(self) -> None:
        exact = self.exact_audit()
        hostile = []
        extra = copy.deepcopy(exact)
        extra["decision"]["quoted_acceptance"] = "accepted"
        hostile.append(extra)
        boolean_alias = copy.deepcopy(exact)
        boolean_alias["decision"]["accepted"] = 1
        hostile.append(boolean_alias)
        drift = copy.deepcopy(exact)
        drift["reviewed_execution_artifacts"]["contract"]["sha256"] = "0" * 64
        hostile.append(drift)
        for value in hostile:
            with self.assertRaises(bootstrap.LockedPairBootstrapV6Error):
                bootstrap._validate_structured_audit(
                    audit_bytes=bootstrap._canonical_json_bytes(value),
                    contract=self.contract,
                    expected_contract_sha256=self.contract_sha256,
                    retained_contract_bytes=self.contract_bytes,
                )

    def test_18_duplicate_key_and_nonfinite_audit_json_are_rejected(self) -> None:
        with self.assertRaises(bootstrap.LockedPairBootstrapV6Error):
            bootstrap._parse_json(b'{"schema":"a","schema":"b"}', "duplicate")
        with self.assertRaises(bootstrap.LockedPairBootstrapV6Error):
            bootstrap._parse_json(b'{"value":NaN}', "nonfinite")

    def test_19_all_python_artifacts_compile_from_exact_bytes(self) -> None:
        labels = (
            "external_bootstrap", "private_controller", "child_wrapper",
            "static_hostile_test",
        )
        for label in labels:
            path = ROOT / self.contract["execution_sources"][label]["path"]
            compile(path.read_bytes(), str(path), "exec", dont_inherit=True)

    def test_20_static_sources_do_not_author_or_invoke_blender(self) -> None:
        source_paths = [
            ROOT / self.contract["execution_sources"][label]["path"]
            for label in ("external_bootstrap", "private_controller", "child_wrapper")
        ]
        sources = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)
        self.assertNotIn("bpy.ops", sources)
        self.assertNotIn("bpy.data.objects.new", sources)
        self.assertNotIn("mesh.from_pydata", sources)
        self.assertIn("CREATE_SUSPENDED", (ROOT / self.v5_contract[
            "execution_sources"
        ]["attempt04_controller_core"]["path"]).read_text(encoding="utf-8"))

    def test_21_direct_script_entry_refuses(self) -> None:
        self.assertEqual(controller.main(), 2)

    def test_22_discovery_supports_absent_or_exact_future_audit(self) -> None:
        _contract_path, paths = bootstrap._untrusted_discovery(require_audit=False)
        self.assertEqual(len(paths), len(set(paths)))
        self.assertGreaterEqual(len(paths), 45)

    def test_23_runtime_descendants_use_native_parent_handle_creation_only(self) -> None:
        source = (ROOT / self.contract["execution_sources"][
            "private_controller"
        ]["path"]).read_text(encoding="utf-8")
        tree_source = source.split("class SecureRuntimeTree", 1)[1].split(
            "_ACTIVE_RUNTIME_TREE", 1
        )[0]
        self.assertIn("NtCreateFile", source)
        self.assertIn("WindowsDirectoryIdentity.open_child", tree_source)
        self.assertNotIn(".mkdir(", tree_source)


if __name__ == "__main__":
    unittest.main()
