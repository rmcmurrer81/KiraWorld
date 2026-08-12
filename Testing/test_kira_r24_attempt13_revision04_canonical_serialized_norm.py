from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_r24_internal_midpoint_fair_surface"
)
ATTEMPT12 = EVIDENCE_ROOT / "attempt_12"
ATTEMPT12_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_internal_midpoint_measured_postsolve_attempt12_revision03.py"
)
ATTEMPT13_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_internal_midpoint_measured_postsolve_attempt13_revision04.py"
)
PROPOSAL = (
    EVIDENCE_ROOT
    / "PREFLIGHT"
    / "ATTEMPT_13_REVISION04_CANONICAL_SERIALIZED_NORM_PROPOSAL.md"
)

BOUND_SHA256 = {
    ATTEMPT12_WORKER: "a03597d16623450d72608fdfffe9bd4c4db252b226f52a3090f4d17ff29370f2",
    ATTEMPT12 / "PRE_MASK_DIAGNOSTIC.json": "8614dd1c7a7cb83c05e49a6e55c3590408690f28b3c7ece83897b6d4f1069d93",
    ATTEMPT12 / "PRE_CAP_DIAGNOSTIC.json": "73ccdbb0051ee1ba983a95c149d53dfc90b1547e82c4f8abf37e6eb2079ea88a",
    ATTEMPT12 / "SOLVER_DIAGNOSTIC.json": "cfda494e79549feee2b3e35c4b293be53cd265a969940f979b4d1a3dd4ffc896",
    ATTEMPT12 / "FAILURE.json": "3bb9012990727a7c049ac0dae3ab747f395a8bd039a88187c2b936d6bd394598",
    PROPOSAL: "9c83c411816d6f71832effbc8919c523ee68f57550b4e27a3f3228c5a816764a",
}

VECTOR_NORM_FIELDS = (
    ("coefficient_world", "coefficient_norm"),
    ("closest_minimum_vector_m", "closest_minimum_norm_m"),
    ("parallel_from_row_vector_m", "parallel_from_row_norm_m"),
    ("applied_kkt_vector_m", "applied_kkt_norm_m"),
    ("nullspace_vector_m", "nullspace_norm_m"),
    ("soft_target_vector_m", "soft_target_norm_m"),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_norm(values) -> float:
    return math.sqrt(sum(float(value) ** 2 for value in values))


def function_source(source: str, function_name: str) -> str:
    tree = ast.parse(source)
    node = next(
        item
        for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == function_name
    )
    lines = source.splitlines(keepends=True)
    return "".join(lines[node.lineno - 1 : node.end_lineno])


class R24Attempt13CanonicalSerializedNormTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.solver = load_json(ATTEMPT12 / "SOLVER_DIAGNOSTIC.json")
        cls.old_source = ATTEMPT12_WORKER.read_text(encoding="utf-8")
        cls.new_source = ATTEMPT13_WORKER.read_text(encoding="utf-8")

    def test_attempt12_is_exactly_bound(self) -> None:
        for path, expected in BOUND_SHA256.items():
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
                self.assertEqual(sha256(path), expected)

    def test_attempt12_only_false_solver_check_is_norm_self_consistency(self) -> None:
        checks = self.solver["checks"]
        false_checks = sorted(name for name, passed in checks.items() if not passed)
        self.assertEqual(
            false_checks,
            ["all_support_serialized_vector_norms_recompute_within_1pm"],
        )
        self.assertTrue(checks["all_hard_support_records_within_postsolve_ceiling"])
        self.assertTrue(checks["boundary_displacement_exact_zero"])
        self.assertTrue(checks["ring2_cap_0_90mm"])
        self.assertTrue(checks["deep_cap_0_60mm"])
        self.assertTrue(checks["overall_postsolve_ceiling_2_525mm"])
        self.assertTrue(checks["p95_cap_0_90mm"])
        self.assertTrue(checks["rms_postsolve_ceiling_0_460mm"])
        self.assertTrue(
            checks[
                "attempt12_revision03_solver_semantic_runtime_effect_fingerprint_before_geometry"
            ]
        )
        self.assertLessEqual(self.solver["maximum_constraint_residual_m"], 2.0e-8)

    def test_native_norm_discrepancy_is_reproduced_without_relaxing_caps(self) -> None:
        records = self.solver["attempt10_support_movement_records"]
        self.assertEqual(len(records), 27)
        maxima = {}
        for vector_key, norm_key in VECTOR_NORM_FIELDS:
            differences = [
                abs(canonical_norm(record[vector_key]) - float(record[norm_key]))
                for record in records
            ]
            maxima[vector_key] = max(differences)
        self.assertEqual(maxima["coefficient_world"], 1.4759708566458585e-08)
        self.assertEqual(maxima["soft_target_vector_m"], 3.592508972596886e-11)
        self.assertGreater(max(maxima.values()), 1.0e-12)
        self.assertTrue(all(record["within_postsolve_ceiling"] for record in records))

    def test_python_double_diagnostic_is_self_recomputing_for_every_support_vector(self) -> None:
        records = self.solver["attempt10_support_movement_records"]
        for record in records:
            for vector_key, _old_norm_key in VECTOR_NORM_FIELDS:
                with self.subTest(edge=record["edge"], vector=vector_key):
                    first = canonical_norm(record[vector_key])
                    second = canonical_norm([float(value) for value in record[vector_key]])
                    self.assertLessEqual(abs(first - second), 1.0e-12)

    def test_solver_and_geometry_operations_outside_evidence_block_are_unchanged(self) -> None:
        old_function = function_source(self.old_source, "attempt08_coupled_fit")
        new_function = function_source(self.new_source, "attempt08_coupled_fit")
        old_solver_prefix = old_function[: old_function.index("    movements =")]
        new_solver_prefix = new_function[: new_function.index("    movements =")]
        self.assertEqual(new_solver_prefix, old_solver_prefix)
        old_geometry_suffix = old_function[old_function.index("    world_to_local =") :]
        new_geometry_suffix = new_function[new_function.index("    world_to_local =") :]
        self.assertEqual(new_geometry_suffix, old_geometry_suffix)

        invariant_assignments = (
            "SEVERE_RING_1_CAP_M = a14.SEVERE_RING_1_CAP_M",
            "OTHER_RING_1_CAP_M = a14.OTHER_RING_1_CAP_M",
            "RING_2_CAP_M = a14.RING_2_CAP_M",
            "DEEP_CAP_M = a14.DEEP_CAP_M",
            "POSTSOLVE_DEFAULT_SEVERE_CEILING_M = 0.002330",
            "POSTSOLVE_OVERALL_CEILING_M = 0.002525",
            "POSTSOLVE_RMS_CEILING_M = 0.000460",
            "INHERITED_RING_1_CAP_M = 0.00240",
            "INHERITED_TOTAL_BASE_FIT_CAP_M = 0.00240",
            "CONSTRAINT_RESIDUAL_TOLERANCE_M = a14.CONSTRAINT_RESIDUAL_TOLERANCE_M",
        )
        for assignment in invariant_assignments:
            with self.subTest(assignment=assignment):
                self.assertIn(assignment, self.new_source)

    def test_worker_is_append_only_bound_canonical_and_no_save(self) -> None:
        ast.parse(self.new_source, filename=str(ATTEMPT13_WORKER))
        self.assertIn('EXPECTED_ATTEMPT_SLOT = "attempt_13"', self.new_source)
        self.assertIn(
            'ATTEMPT_13_PROPOSAL_SHA256 = "9c83c411816d6f71832effbc8919c523ee68f57550b4e27a3f3228c5a816764a"',
            self.new_source,
        )
        self.assertGreaterEqual(self.new_source.count("serialized_mathutils_norm("), 4)
        self.assertGreaterEqual(
            self.new_source.count("serialized_python_double_norm("), 7
        )
        for field in (
            "coefficient_python_double_norm",
            "closest_minimum_python_double_norm_m",
            "parallel_from_row_python_double_norm_m",
            "applied_kkt_python_double_norm_m",
            "nullspace_python_double_norm_m",
            "soft_target_python_double_norm_m",
        ):
            self.assertIn(field, self.new_source)
        self.assertIn("coefficient_norm = float(coefficient.length)", self.new_source)
        self.assertIn("movement_norm = float(movement.length)", self.new_source)
        self.assertIn(
            '"all_support_serialized_coefficient_norms_recompute_within_1e_12"',
            self.new_source,
        )
        self.assertIn(
            '"all_support_serialized_metric_vector_norms_recompute_within_1pm"',
            self.new_source,
        )
        self.assertNotIn("serialized_component_norm(", self.new_source)
        self.assertNotIn(
            'raise RuntimeError("Attempt 06 KKT solution violates an exact movement cap")',
            self.new_source,
        )
        self.assertIn("failed_check_names = sorted(", self.new_source)

        allocation = self.new_source.index("planned_output = next_append_only_output()")
        source_load = self.new_source.index("bpy.ops.wm.open_mainfile")
        for binding in (
            '"attempt_12 revision-03 worker"',
            '"attempt_12 pre-mask"',
            '"attempt_12 pre-cap"',
            '"attempt_12 solver"',
            '"attempt_12 failure"',
            '"attempt_13 revision-04 proposal"',
        ):
            location = self.new_source.index(binding)
            self.assertLess(location, allocation)
            self.assertLess(location, source_load)
        self.assertNotIn("bpy.ops.wm.save", self.new_source)
        self.assertNotIn("save_as_mainfile", self.new_source)
        self.assertFalse((EVIDENCE_ROOT / "attempt_13").exists())


if __name__ == "__main__":
    unittest.main()
