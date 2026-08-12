from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / (
    "RecoverySprint/continuation_20260807/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT18_CONFIG.json"
)
WORKER_PATH = ROOT / (
    "tools/blender_simulate_kira_r24_blackproject_local_reconstruction_attempt18.py"
)
ATTEMPT16_CONFIG_PATH = ROOT / (
    "RecoverySprint/continuation_20260807/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT16_CONFIG.json"
)
ATTEMPT16_ROOT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/attempt_16"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class FakeVector:
    def __init__(self, values: Sequence[float]) -> None:
        self.values = [float(value) for value in values]

    def __len__(self) -> int:
        return len(self.values)

    def copy(self) -> "FakeVector":
        return FakeVector(self.values)

    def __iadd__(self, other: "FakeVector") -> "FakeVector":
        if len(self) != len(other):
            raise AttributeError("vectors must have the same dimensions")
        self.values = [first + second for first, second in zip(self.values, other.values)]
        return self

    def __truediv__(self, divisor: float) -> "FakeVector":
        return FakeVector([value / float(divisor) for value in self.values])


class Attempt18StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.attempt16_config = json.loads(
            ATTEMPT16_CONFIG_PATH.read_text(encoding="utf-8")
        )
        cls.worker = WORKER_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.worker)
        helper = next(
            node
            for node in cls.tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "dimension_safe_vector_mean"
        )
        namespace: dict[str, Any] = {"Sequence": Sequence, "Any": Any}
        module = ast.fix_missing_locations(ast.Module(body=[helper], type_ignores=[]))
        exec(compile(module, str(WORKER_PATH), "exec"), namespace)
        cls.vector_mean = staticmethod(namespace["dimension_safe_vector_mean"])
        cls.failure = json.loads(
            (ATTEMPT16_ROOT / "FAILURE.json").read_text(encoding="utf-8")
        )
        cls.append_inventory = json.loads(
            (ATTEMPT16_ROOT / "APPEND_INVENTORY.json").read_text(encoding="utf-8")
        )

    def test_01_all_bound_inputs_are_present_and_hash_exact(self) -> None:
        for name, record in self.config["inputs"].items():
            path = ROOT / record["path"]
            self.assertTrue(path.is_file(), name)
            self.assertEqual(sha256_file(path), record["sha256"], name)

    def test_02_attempt16_evidence_is_preserved_byte_exact(self) -> None:
        expected = {
            "APPEND_INVENTORY.json": "638fc5c4bf3bbaa0f79cc870550e2a853b316659f10517ada219cf7c0e3ad142",
            "ATTEMPT_STARTED.json": "cfc44c31fe1daf3c57c5b6ff01330508b23a4d3f2efda7ac37d730e3b84bddfd",
            "FAILURE.json": "ce8a43d8e5ea87d3d04cb4e7a0b7ceb8fa6b2be8e9a298a204f96b6328d39e7d",
        }
        self.assertEqual(
            sorted(path.name for path in ATTEMPT16_ROOT.iterdir() if path.is_file()),
            sorted(expected),
        )
        for name, digest in expected.items():
            self.assertEqual(sha256_file(ATTEMPT16_ROOT / name), digest, name)

    def test_03_real_traceback_and_expression_are_exact(self) -> None:
        self.assertEqual(self.failure["error_type"], "AttributeError")
        self.assertEqual(
            self.failure["error"],
            "Vector addition: vectors must have the same dimensions for this operation",
        )
        self.assertIn("line 659, in reconstruct_local_domain", self.failure["traceback"])
        self.assertIn(
            "value = sum(samples, Vector()) / len(samples)",
            self.failure["traceback"],
        )
        self.assertFalse(self.failure["blend_saved"])
        self.assertFalse(self.failure["runtime_changed"])

    def test_04_attempt16_append_inventory_passed_exactly(self) -> None:
        inventory = self.append_inventory
        self.assertEqual(
            inventory["status"],
            "PASS_EXACT_SEVEN_OBJECT_HIERARCHY_NO_NEW_COLLECTIONS",
        )
        self.assertEqual(
            inventory["actual_appended_object_names"],
            inventory["expected_appended_object_names"],
        )
        self.assertEqual(inventory["actual_new_collection_names"], [])
        self.assertEqual(inventory["missing_object_names"], [])
        self.assertEqual(inventory["extra_object_names"], [])

    def test_05_dimension_safe_mean_handles_real_2d_shape(self) -> None:
        result = self.vector_mean(
            [FakeVector((0.0, 2.0)), FakeVector((2.0, 4.0)), FakeVector((4.0, 6.0))]
        )
        self.assertEqual(result.values, [2.0, 4.0])
        self.assertEqual(len(result), 2)

    def test_06_dimension_safe_mean_handles_3d_shape(self) -> None:
        result = self.vector_mean(
            [FakeVector((1.0, 2.0, 3.0)), FakeVector((3.0, 4.0, 5.0))]
        )
        self.assertEqual(result.values, [2.0, 3.0, 4.0])
        self.assertEqual(len(result), 3)

    def test_07_dimension_safe_mean_fails_closed_for_empty_or_mixed_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one sample"):
            self.vector_mean([])
        with self.assertRaisesRegex(ValueError, "mixed dimensions"):
            self.vector_mean([FakeVector((1.0, 2.0)), FakeVector((1.0, 2.0, 3.0))])

    def test_08_worker_replaces_only_the_unsafe_mean_expression(self) -> None:
        self.assertNotIn("sum(samples, Vector())", self.worker)
        self.assertEqual(
            self.worker.count("value = dimension_safe_vector_mean(samples)"), 1
        )
        contract = self.config["dimension_safe_mean_contract"]
        self.assertEqual(contract["supported_dimensions_under_static_regression"], [2, 3])
        self.assertEqual(contract["exact_failure_worker_line"], 659)

    def test_09_structural_contracts_remain_exactly_attempt16(self) -> None:
        for key in (
            "license",
            "objects",
            "measured_repair_domain",
            "replacement",
            "hard_gates",
            "paired_visual_evidence",
        ):
            self.assertEqual(self.config[key], self.attempt16_config[key], key)
        current_append = dict(self.config["append_contract"])
        prior_append = dict(self.attempt16_config["append_contract"])
        current_append.pop("source_truth")
        prior_append.pop("source_truth")
        self.assertEqual(current_append, prior_append)

    def test_10_worker_retains_append_intersection_preservation_and_render_gates(self) -> None:
        required = (
            "PASS_EXACT_SEVEN_OBJECT_HIERARCHY_NO_NEW_COLLECTIONS",
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

    def test_11_worker_has_no_blend_save_or_activation_path(self) -> None:
        for forbidden in (
            "save_as_mainfile",
            "save_mainfile",
            "write_homefile",
            "runtime_activation_allowed = True",
            "owner_approved = True",
        ):
            self.assertNotIn(forbidden, self.worker)
        self.assertFalse(self.config["output"]["blend_save_permitted"])

    def test_12_attempt18_uses_unallocated_slot_and_does_not_reuse_attempt17(self) -> None:
        self.assertEqual(self.config["attempt_id"], "attempt_18")
        self.assertTrue(
            self.config["output"]["root"].endswith("/attempt_18")
        )
        self.assertFalse((ROOT / self.config["output"]["root"]).exists())
        self.assertNotIn("attempt_17", self.config["output"]["root"])


if __name__ == "__main__":
    unittest.main()
