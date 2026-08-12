#!/usr/bin/env python3
"""Hostile static tests for Kira R25 AFES locked-pair Attempt 05.

No test launches Blender, creates the execution output root, opens a body,
mutates a Blend, or grants execution/body authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from tools import launch_kira_r25_foundation_afes_locked_pair_v5 as bootstrap
from tools import run_kira_r25_foundation_afes_locked_pair_v5 as controller


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v5.json"
)
V4_CONTRACT = ROOT / (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_foundation_afes_locked_pair_execution_v4.json"
)
AUDIT = ROOT / bootstrap.AUDIT_RELATIVE_PATH
OUTPUT = ROOT / controller.OUTPUT_RELATIVE_PATH
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
EMPTY_REF = f"sha256:{EMPTY_SHA256}"


def file_row(path: Path) -> tuple[int, str]:
    value = path.read_bytes()
    return len(value), hashlib.sha256(value).hexdigest()


def index_ref(count: int, digest: str) -> dict[str, object]:
    return {
        "blob_ref": EMPTY_REF,
        "semantic": controller.INDEX_SEMANTIC,
        "item_count": count,
        "semantic_sha256": digest,
    }


def edge_ref(count: int, digest: str) -> dict[str, object]:
    return {
        "blob_ref": EMPTY_REF,
        "semantic": controller.EDGE_SEMANTIC,
        "item_count": count,
        "semantic_sha256": digest,
    }


class FakeExactCompactValidator:
    """Stand-in only for isolating the new parent binding checks."""

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
            "connection_edges": tuple((index, index + 1) for index in range(
                union["primary_connection_edge_count"]
            )),
            "transition_rings": ((0,), (1,)),
            "combined_transition_vertices": (0, 1),
        }


class DummySeal:
    def __init__(self, paths: object) -> None:
        self.paths = tuple(Path(path) for path in paths)
        self.closed = False

    def verify_empty(self) -> None:
        if any(any(path.iterdir()) for path in self.paths):
            raise controller.LockedPairV5Error("dummy_sealed_directory_changed")

    def close(self) -> None:
        self.closed = True


class Attempt05Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_bytes = CONTRACT.read_bytes()
        cls.contract = json.loads(cls.contract_bytes.decode("utf-8"))
        cls.v4_contract = json.loads(V4_CONTRACT.read_text(encoding="utf-8"))
        v5_config_path = ROOT / cls.v4_contract[
            "child_project_read_closure"
        ]["afes_v5_config"]["path"]
        v5 = json.loads(v5_config_path.read_text(encoding="utf-8"))
        v4 = json.loads((ROOT / v5["attempt_04_baseline_config"]["path"]).read_text(
            encoding="utf-8"
        ))
        v3 = json.loads((ROOT / v4["attempt_03_baseline_config"]["path"]).read_text(
            encoding="utf-8"
        ))
        cls.v2 = json.loads((ROOT / v3["attempt_02_baseline_config"]["path"]).read_text(
            encoding="utf-8"
        ))
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
                "rounding": controller.ROUNDING_RULE,
                **copy.deepcopy(foundation["expected_bounds_object_nanometers"]),
            },
            "binary_arrays": {
                EMPTY_REF: {
                    "codec": controller.BLOB_CODEC,
                    "endianness": "big",
                    "u32_count": 0,
                    "raw_bytes": 0,
                    "raw_sha256": EMPTY_SHA256,
                    "base64": "",
                }
            },
        }

    def assert_analysis_rejected(self, analysis: object) -> None:
        with self.assertRaises(controller.LockedPairV5Error):
            controller._validate_foundation_bound_analysis(
                analysis, v2=self.v2, attempt03=self.validator,
            )

    def test_01_attempt04_package_and_rejection_are_byte_preserved(self) -> None:
        expected = {
            "contract": (
                "Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_locked_pair_execution_v4.json",
                18707, "0b676c632dc907643fb33d25a15f55dd6bd3c83468021ebf8f7ed47563b473a1",
            ),
            "external_bootstrap": (
                "tools/launch_kira_r25_foundation_afes_locked_pair_v4.py",
                33199, "7a734b715eef1cb8d1fdee949fb3b25bb28a23d1f2d53e600cdf0d29da2fba6d",
            ),
            "private_controller": (
                "tools/run_kira_r25_foundation_afes_locked_pair_v4.py",
                39032, "c5863757a121b892b38a11a0ffcafac8c08ea59b4434c3b4b24dc670628cc390",
            ),
            "child_wrapper": (
                "tools/blender_extract_kira_r25_foundation_afes_transition_rings_execution_v4.py",
                12823, "526217e23b7445c70804211b9299ba420d5c5b62052014e0f2af67c84626093c",
            ),
            "static_hostile_test": (
                "Testing/test_kira_r25_foundation_afes_locked_pair_execution_attempt04.py",
                21975, "124477213121ba1177c416cd964d9c332e630433fc69ced24eec0b3409454359",
            ),
            "checkpoint": (
                "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_04/CHECKPOINT.md",
                8918, "e81dc8bf3d49c95de4f6d4efe369fb7bd103710a0533ac33f326827ff68c1649",
            ),
            "rejection_audit": (
                "RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_04/INDEPENDENT_AUDIT.md",
                12003, "6da1ad25c9aab51fd1803fda8bb2c692184ee92737081d931fb23144435e0234",
            ),
        }
        self.assertEqual(self.contract["preserved_rejected_attempt04"], {
            key: {"path": path, "bytes": size, "sha256": digest}
            for key, (path, size, digest) in expected.items()
        })
        for path, size, digest in expected.values():
            self.assertEqual(file_row(ROOT / path), (size, digest))

    def test_02_exact_inherited_35_file_closure_is_bound(self) -> None:
        closure = self.v4_contract["child_project_read_closure"]
        self.assertEqual(len(closure), 35)
        by_path = {row["path"]: row for row in closure.values()}
        self.assertEqual(len(by_path), 35)
        digest = hashlib.sha256(bootstrap._canonical_json_bytes(by_path)).hexdigest()
        self.assertEqual(
            digest,
            self.contract["recursive_closure_contract"]["canonical_closure_sha256"],
        )
        for row in closure.values():
            self.assertEqual(file_row(ROOT / row["path"]), (row["bytes"], row["sha256"]))

    def test_03_new_execution_sources_are_exact_and_direct_controller_refuses(self) -> None:
        for label, row in self.contract["execution_sources"].items():
            path = Path(row["path"]) if label == "blender_executable" else ROOT / row["path"]
            self.assertEqual(file_row(path), (row["bytes"], row["sha256"]), label)
        self.assertEqual(controller.main(), 2)

    def test_04_valid_foundation_bound_shape_passes_new_parent_layer(self) -> None:
        topology = controller._validate_foundation_bound_analysis(
            self.valid_analysis(), v2=self.v2, attempt03=self.validator,
        )
        self.assertEqual(topology, "1" * 64)

    def test_05_toy_mesh_for_real_foundation_is_rejected(self) -> None:
        bad = self.valid_analysis()
        bad["whole_mesh"]["vertex_count"] = 7
        bad["whole_mesh"]["edge_count"] = 6
        bad["whole_mesh"]["face_count"] = 3
        self.assert_analysis_rejected(bad)

    def test_06_group_extra_and_wrong_exact_group_set_are_rejected(self) -> None:
        bad = self.valid_analysis()
        first = next(iter(bad["groups"]))
        bad["groups"][first]["unexpected"] = True
        self.assert_analysis_rejected(bad)
        bad = self.valid_analysis()
        bad["groups"]["AFES_TOY"] = copy.deepcopy(next(iter(bad["groups"].values())))
        self.assert_analysis_rejected(bad)

    def test_07_group_count_and_semantic_digest_substitution_are_rejected(self) -> None:
        first = next(iter(self.foundation["required_groups"]))
        bad = self.valid_analysis()
        bad["groups"][first]["vertex_indices"]["item_count"] += 1
        self.assert_analysis_rejected(bad)
        bad = self.valid_analysis()
        bad["groups"][first]["vertex_indices"]["semantic_sha256"] = "0" * 64
        self.assert_analysis_rejected(bad)

    def test_08_union_extra_count_and_digest_substitution_are_rejected(self) -> None:
        bad = self.valid_analysis()
        bad["afes_union"]["unexpected"] = 1
        self.assert_analysis_rejected(bad)
        bad = self.valid_analysis()
        bad["afes_union"]["vertex_indices"]["item_count"] = 7
        self.assert_analysis_rejected(bad)
        bad = self.valid_analysis()
        bad["afes_union"]["primary_connection_edges"]["semantic_sha256"] = "0" * 64
        self.assert_analysis_rejected(bad)

    def test_09_transition_container_and_ring_extras_are_rejected(self) -> None:
        bad = self.valid_analysis()
        bad["transition_rings"]["unexpected"] = True
        self.assert_analysis_rejected(bad)
        bad = self.valid_analysis()
        bad["transition_rings"]["rings"][0]["unexpected"] = True
        self.assert_analysis_rejected(bad)

    def test_10_boolean_integer_alias_and_ring_shape_are_rejected(self) -> None:
        bad = self.valid_analysis()
        bad["transition_rings"]["disjoint_from_afes_union"] = 1
        self.assert_analysis_rejected(bad)
        bad = self.valid_analysis()
        bad["transition_rings"]["ring_count"] = True
        self.assert_analysis_rejected(bad)
        bad = self.valid_analysis()
        bad["transition_rings"]["rings"][1]["ring_number"] = 1
        self.assert_analysis_rejected(bad)

    def test_11_structural_metric_and_topology_drift_are_rejected(self) -> None:
        bad = self.valid_analysis()
        bad["topology_structure"]["connected_component_count"] = 2
        self.assert_analysis_rejected(bad)
        bad = self.valid_analysis()
        bad["topology_structure"]["full_normalized_topology_sha256"] = "2" * 64
        self.assert_analysis_rejected(bad)

    def test_12_bounds_extra_type_and_expected_tolerance_drift_are_rejected(self) -> None:
        bad = self.valid_analysis()
        bad["bounds_object_nm"]["unexpected"] = 1
        self.assert_analysis_rejected(bad)
        bad = self.valid_analysis()
        bad["bounds_object_nm"]["minimum"][0] = True
        self.assert_analysis_rejected(bad)
        bad = self.valid_analysis()
        bad["bounds_object_nm"]["minimum"][0] -= 101
        self.assert_analysis_rejected(bad)

    def test_13_binary_record_extra_and_unreferenced_blob_are_rejected(self) -> None:
        bad = self.valid_analysis()
        bad["binary_arrays"][EMPTY_REF]["unexpected"] = 1
        self.assert_analysis_rejected(bad)
        bad = self.valid_analysis()
        other = "sha256:" + "0" * 64
        bad["binary_arrays"][other] = copy.deepcopy(bad["binary_arrays"][EMPTY_REF])
        self.assert_analysis_rejected(bad)

    def test_14_nonce_scoped_runtime_tree_is_exclusive_and_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            pair = "a" * 64
            run = "b" * 64
            pair_root = controller._prepare_pair_runtime_root(
                pair_session_nonce=pair, project_root=project,
            )
            lease = controller._prepare_runtime_lease(
                pair_session_nonce=pair, run_nonce=run, run_number=1,
                seal_factory=DummySeal, project_root=project, pair_root=pair_root,
            )
            try:
                lease.verify_before_child()
                self.assertEqual(
                    set(lease.directories),
                    {"temp", "user_config", "user_scripts", "user_datafiles"},
                )
                self.assertTrue(all(not any(path.iterdir()) for path in lease.directories.values()))
            finally:
                lease.close()
            second = controller._prepare_runtime_lease(
                pair_session_nonce=pair, run_nonce="9" * 64, run_number=2,
                seal_factory=DummySeal, project_root=project, pair_root=pair_root,
            )
            try:
                second.verify_before_child()
                self.assertNotEqual(lease.root, second.root)
            finally:
                second.close()

    def test_15_preoccupied_runtime_scope_and_foreign_startup_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            pair = "c" * 64
            run = "d" * 64
            pair_token = hashlib.sha256(pair.encode("ascii")).hexdigest()[:32]
            run_token = hashlib.sha256(f"{pair}:1:{run}".encode("ascii")).hexdigest()[:32]
            pair_root = project / controller.RUNTIME_BASE_RELATIVE_PATH / f"pair_{pair_token}"
            startup = pair_root / f"run_01_{run_token}" / "user_scripts" / "startup"
            startup.mkdir(parents=True)
            (startup / "foreign.py").write_text("foreign", encoding="utf-8")
            with self.assertRaises((FileExistsError, controller.LockedPairV5Error)):
                controller._prepare_runtime_lease(
                    pair_session_nonce=pair, run_nonce=run, run_number=1,
                    seal_factory=DummySeal, project_root=project,
                )

    def test_16_reparse_ancestor_is_rejected_before_runtime_use(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            original = controller._has_reparse_attribute

            def classify(path: Path) -> bool:
                return path.name == "runtime_cache" or original(path)

            with mock.patch.object(controller, "_has_reparse_attribute", side_effect=classify):
                with self.assertRaises(controller.LockedPairV5Error):
                    controller._prepare_runtime_lease(
                        pair_session_nonce="e" * 64, run_nonce="f" * 64,
                        run_number=1, seal_factory=DummySeal, project_root=project,
                    )

    def test_17_sealed_user_script_change_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lease = controller._prepare_runtime_lease(
                pair_session_nonce="1" * 64, run_nonce="2" * 64,
                run_number=1, seal_factory=DummySeal,
                project_root=Path(temporary),
            )
            try:
                (lease.directories["user_scripts"] / "foreign.py").write_text(
                    "foreign", encoding="utf-8"
                )
                with self.assertRaises(controller.LockedPairV5Error):
                    lease.verify_after_child()
            finally:
                lease.close()

    def synthetic_accepted_audit(self) -> dict[str, object]:
        contract_sha = hashlib.sha256(self.contract_bytes).hexdigest()
        return {
            "schema": "kira.avatar.r25.foundation_afes_locked_pair_independent_audit.v5",
            "attempt_id": "attempt_05",
            "decision": {
                "accepted": True,
                "code": "ACCEPTED_FOR_ONE_BOUNDED_READ_ONLY_PAIR_ONLY",
                "scope": "ONE_FRESH_LOCKED_AFES_DIAGNOSTIC_PAIR",
            },
            "reviewed_execution_artifacts": bootstrap._expected_audit_artifacts(
                self.contract, self.contract_bytes, contract_sha,
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

    def test_18_pre_audit_and_post_audit_states_are_both_explicitly_verifiable(self) -> None:
        contract_sha = hashlib.sha256(self.contract_bytes).hexdigest()
        if AUDIT.exists():
            bootstrap._validate_structured_audit(
                audit_bytes=AUDIT.read_bytes(), contract=self.contract,
                expected_contract_sha256=contract_sha,
                retained_contract_bytes=self.contract_bytes,
            )
        else:
            self.assertEqual(
                self.contract["audit_gate"]["path"], bootstrap.AUDIT_RELATIVE_PATH,
            )
        synthetic = bootstrap._canonical_json_bytes(self.synthetic_accepted_audit())
        bootstrap._validate_structured_audit(
            audit_bytes=synthetic, contract=self.contract,
            expected_contract_sha256=contract_sha,
            retained_contract_bytes=self.contract_bytes,
        )

    def test_19_post_audit_hash_binding_and_exact_schema_fail_closed(self) -> None:
        contract_sha = hashlib.sha256(self.contract_bytes).hexdigest()
        accepted = self.synthetic_accepted_audit()
        bad = copy.deepcopy(accepted)
        bad["decision"]["accepted"] = 1
        with self.assertRaises(bootstrap.LockedPairBootstrapV5Error):
            bootstrap._validate_structured_audit(
                audit_bytes=bootstrap._canonical_json_bytes(bad),
                contract=self.contract, expected_contract_sha256=contract_sha,
                retained_contract_bytes=self.contract_bytes,
            )
        bad = copy.deepcopy(accepted)
        bad["unexpected"] = "ACCEPTED_FOR_ONE_BOUNDED_READ_ONLY_PAIR_ONLY"
        with self.assertRaises(bootstrap.LockedPairBootstrapV5Error):
            bootstrap._validate_structured_audit(
                audit_bytes=bootstrap._canonical_json_bytes(bad),
                contract=self.contract, expected_contract_sha256=contract_sha,
                retained_contract_bytes=self.contract_bytes,
            )

    def test_20_static_suite_never_invokes_blender_or_body_authoring(self) -> None:
        sources = "\n".join((
            (ROOT / "tools/run_kira_r25_foundation_afes_locked_pair_v5.py").read_text(
                encoding="utf-8"
            ),
            (ROOT / "tools/launch_kira_r25_foundation_afes_locked_pair_v5.py").read_text(
                encoding="utf-8"
            ),
        ))
        self.assertNotIn("bpy.ops", sources)
        self.assertNotIn("subprocess.run(", sources)


if __name__ == "__main__":
    unittest.main()
