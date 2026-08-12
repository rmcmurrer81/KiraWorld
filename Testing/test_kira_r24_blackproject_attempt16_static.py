from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / (
    "RecoverySprint/continuation_20260807/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT16_CONFIG.json"
)
WORKER_PATH = ROOT / (
    "tools/blender_simulate_kira_r24_blackproject_local_reconstruction_attempt16.py"
)
ATTEMPT15_ROOT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/attempt_15"
)
PRIOR_APPEND_FAILURE_PATH = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r21_localized_repair/"
    "author_attempt_01/FAILURE_EVIDENCE.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class Attempt16StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.worker = WORKER_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.worker)
        cls.prior_append_failure = json.loads(
            PRIOR_APPEND_FAILURE_PATH.read_text(encoding="utf-8")
        )
        cls.recorded_append_result = ast.literal_eval(
            cls.prior_append_failure["error"].split(": ", 1)[1]
        )

    def test_01_all_bound_inputs_are_present_and_hash_exact(self) -> None:
        for name, record in self.config["inputs"].items():
            path = ROOT / record["path"]
            self.assertTrue(path.is_file(), name)
            self.assertEqual(sha256_file(path), record["sha256"], name)

    def test_02_attempt15_failure_is_preserved_and_hash_bound(self) -> None:
        self.assertEqual(
            sha256_file(ATTEMPT15_ROOT / "ATTEMPT_STARTED.json"),
            "8f7d7ee829d0d9bda54e0c2b111fe086625938e66368c51efd98cf9db62c42fa",
        )
        self.assertEqual(
            sha256_file(ATTEMPT15_ROOT / "FAILURE.json"),
            "346014f9ea62184116c3462045bd2cccdf39dbc580cdb3206494c5dd4637af9d",
        )
        failure = json.loads((ATTEMPT15_ROOT / "FAILURE.json").read_text())
        self.assertEqual(failure["error"], "unexpected Attempt 02 patch append inventory")
        self.assertFalse(failure["blend_saved"])
        self.assertFalse(failure["runtime_changed"])

    def test_03_exact_seven_object_append_inventory_is_bound(self) -> None:
        contract = self.config["append_contract"]
        expected = [
            "216c8bc711374b3fbf0155edac218dc1.fbx.001",
            "Icosphere",
            "Object_2.001",
            "Object_23",
            "Object_4",
            "RootNode.001",
            "Sketchfab_model.001",
        ]
        self.assertEqual(contract["expected_appended_object_names"], expected)
        self.assertEqual(
            canonical_sha256(expected),
            contract["expected_appended_object_names_sha256"],
        )
        self.assertEqual(self.recorded_append_result, expected)

    def test_04_regression_fixture_catches_attempt15_singleton_error(self) -> None:
        actual_append_result = self.recorded_append_result
        old_attempt15_gate_passes = (
            len(actual_append_result) == 1 and actual_append_result[0] == "Object_23"
        )
        new_attempt16_gate_passes = (
            actual_append_result
            == self.config["append_contract"]["expected_appended_object_names"]
        )
        self.assertFalse(old_attempt15_gate_passes)
        self.assertTrue(new_attempt16_gate_passes)
        self.assertEqual(len(actual_append_result), 7)

    def test_05_exact_cleanup_set_is_six_dependencies_only(self) -> None:
        contract = self.config["append_contract"]
        dependencies = contract["dependency_object_names_removed_in_memory_only"]
        self.assertEqual(len(dependencies), 6)
        self.assertNotIn("Object_23", dependencies)
        self.assertEqual(
            sorted(dependencies + ["Object_23"]),
            contract["expected_appended_object_names"],
        )
        self.assertEqual(
            canonical_sha256(dependencies),
            contract["dependency_object_names_sha256"],
        )

    def test_06_no_collection_append_is_expected_and_hash_bound(self) -> None:
        contract = self.config["append_contract"]
        self.assertEqual(contract["expected_new_collection_names"], [])
        self.assertEqual(
            canonical_sha256([]),
            contract["expected_new_collection_names_sha256"],
        )
        self.assertIn("before_collections = set(bpy.data.collections)", self.worker)
        self.assertIn("actual_new_collection_names", self.worker)
        self.assertIn("extra_collection_names", self.worker)

    def test_07_requested_patch_signature_and_source_armature_are_exact(self) -> None:
        patch = self.config["append_contract"]["requested_patch"]
        self.assertEqual(patch["object_name"], "Object_23")
        self.assertEqual(patch["object_type"], "MESH")
        self.assertEqual(patch["mesh_name_prefix"], "Ariel_Mesh_Genitalia_0")
        self.assertEqual(patch["source_armature_modifier_object"], "Object_4")
        self.assertIn("value.data.name.startswith", self.worker)

    def test_08_worker_records_inventory_before_geometry_reconstruction(self) -> None:
        inventory_write = self.worker.index(
            'atomic_write_json(output / contract["inventory_evidence_filename"], evidence)'
        )
        reconstruction_call = self.worker.index("reconstruct_local_domain(adult")
        self.assertLess(inventory_write, reconstruction_call)
        self.assertIn("FAIL_APPEND_INVENTORY_DRIFT_BEFORE_GEOMETRY_MUTATION", self.worker)
        self.assertIn('"geometry_mutation_reached": False', self.worker)

    def test_09_worker_uses_exact_transform_and_bounded_cleanup(self) -> None:
        append_function = next(
            node
            for node in self.tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "append_patch"
        )
        source = ast.get_source_segment(self.worker, append_function)
        self.assertIsNotNone(source)
        self.assertIn("adult.parent = None", source)
        self.assertIn("adult.matrix_world = body.matrix_world.copy()", source)
        self.assertIn("for modifier in list(adult.modifiers)", source)
        self.assertIn("if value is not adult", source)
        self.assertIn("bpy.data.objects.remove(value, do_unlink=True)", source)
        self.assertNotIn("for value in list(bpy.data.objects)", source)

    def test_10_attempt16_retains_structural_and_no_save_gates(self) -> None:
        required = (
            "quality_refined_cdt",
            "standalone_patch_exact_genuine_intersections_zero",
            "post_graft_patch_related_exact_genuine_intersections_zero",
            "global_34_seam_coordinate_delta_m_exact_zero",
            "nonpatch_body_and_face_snapshot_exact",
            "native_rig_exact",
            "render_uniform_clay_pairs_without_subdivision",
        )
        for value in required:
            self.assertIn(value, self.worker)
        for forbidden in ("save_as_mainfile", "save_mainfile", "write_homefile"):
            self.assertNotIn(forbidden, self.worker)
        self.assertFalse(self.config["output"]["blend_save_permitted"])

    def test_11_attempt16_is_a_new_unallocated_append_only_slot(self) -> None:
        self.assertEqual(self.config["attempt_id"], "attempt_16")
        self.assertEqual(
            self.config["output"]["root"],
            "RecoverySprint/continuation_20260803/"
            "kira_r24_internal_midpoint_fair_surface/attempt_16",
        )
        self.assertFalse((ROOT / self.config["output"]["root"]).exists())


if __name__ == "__main__":
    unittest.main()
