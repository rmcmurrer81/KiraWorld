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
ATTEMPT13 = EVIDENCE_ROOT / "attempt_13"
ATTEMPT13_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_internal_midpoint_measured_postsolve_attempt13_revision04.py"
)
ATTEMPT14_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_internal_midpoint_measured_postsolve_attempt14_revision05.py"
)
PROPOSAL = (
    EVIDENCE_ROOT
    / "PREFLIGHT"
    / "ATTEMPT_14_REVISION05_BOUND_SEAM_NUMERICAL_TOLERANCE_PROPOSAL.md"
)

BOUND_SHA256 = {
    ATTEMPT13_WORKER: "fab7359e002ed2a2a87977844442fc33a1283622a6f40a9fa68b7de1af9f6036",
    ATTEMPT13 / "PRE_MASK_DIAGNOSTIC.json": "e554c9b73fcae18e9fdafde69f0356f45753cb1e585579fb7c2939e4c1e82687",
    ATTEMPT13 / "PRE_CAP_DIAGNOSTIC.json": "4abfe6ab9f49c51ae0b9fbbdb2061f11db3b350ec8543a44b921e3183fde1231",
    ATTEMPT13 / "SOLVER_DIAGNOSTIC.json": "6eac8aaf619a145572f6508e8ed3576eca21f707fbc6ce8153225b9eb1a49c90",
    ATTEMPT13 / "FAILURE.json": "a3b9aa1bf107c91cecd60d6be7e3732925b03c886686e64adcefedf3a1f72e64",
    PROPOSAL: "ac974d033fac40f0187972aa44921db6864f44e62691cc7ad9b4a4deb3d46f60",
}

TOLERANCE = 4.0e-6
TARGETS = {
    "SUPERIOR_JOIN_EDGES": 0.985,
    "SEVERE_FLANK_EDGES": 0.900,
    "REGULAR_FLANK_EDGES": 0.965,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def bounded_dot_pass(achieved: float, target: float, tolerance: float) -> bool:
    return (
        math.isfinite(achieved)
        and -1.0 <= achieved <= 1.0
        and achieved >= target - tolerance
    )


def function_source(source: str, function_name: str) -> str:
    tree = ast.parse(source)
    node = next(
        item
        for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == function_name
    )
    lines = source.splitlines(keepends=True)
    return "".join(lines[node.lineno - 1 : node.end_lineno])


class R24Attempt14BoundSeamToleranceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.solver = load_json(ATTEMPT13 / "SOLVER_DIAGNOSTIC.json")
        cls.old_source = ATTEMPT13_WORKER.read_text(encoding="utf-8")
        cls.new_source = ATTEMPT14_WORKER.read_text(encoding="utf-8")

    def test_attempt13_and_proposal_are_exactly_bound(self) -> None:
        for path, expected in BOUND_SHA256.items():
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
                self.assertEqual(sha256(path), expected)

    def test_attempt13_only_failed_zero_tolerance_seam_checks(self) -> None:
        checks = self.solver["checks"]
        self.assertEqual(
            sorted(name for name, passed in checks.items() if not passed),
            [
                "regular_all_at_least_0_965",
                "severe_all_at_least_0_900",
                "superior_all_at_least_0_985",
                "whole_seam_dihedral_at_most_25_841933",
                "whole_seam_minimum_at_least_0_900",
            ],
        )
        for required in (
            "orientation_preserved",
            "nondegenerate",
            "edge_ratio_at_most_8",
            "patch_exact_intersections_zero",
            "whole_exact_intersections_29",
            "all_hard_support_records_within_postsolve_ceiling",
            "overall_postsolve_ceiling_2_525mm",
            "rms_postsolve_ceiling_0_460mm",
        ):
            self.assertTrue(checks[required], required)

    def test_bound_measurements_and_raw_strict_truth_are_exact(self) -> None:
        records = self.solver["seam_class_records"]
        self.assertEqual(len(records), 34)
        minima = {
            name: min(
                float(record["achieved_dot"])
                for record in records
                if record["class"] == name
            )
            for name in TARGETS
        }
        self.assertEqual(minima["SUPERIOR_JOIN_EDGES"], 0.984996821731329)
        self.assertEqual(minima["REGULAR_FLANK_EDGES"], 0.964996937662363)
        self.assertEqual(minima["SEVERE_FLANK_EDGES"], 0.8999973759055138)
        deficits = [
            max(0.0, float(record["target_dot"]) - float(record["achieved_dot"]))
            for record in records
        ]
        self.assertEqual(max(deficits), 3.178268671022444e-06)
        strict_misses = [record for record in records if not record["passed"]]
        self.assertEqual(len(strict_misses), 17)
        counts = {}
        for record in strict_misses:
            counts[record["class"]] = counts.get(record["class"], 0) + 1
        self.assertEqual(
            counts,
            {
                "REGULAR_FLANK_EDGES": 13,
                "SUPERIOR_JOIN_EDGES": 3,
                "SEVERE_FLANK_EDGES": 1,
            },
        )
        self.assertTrue(
            all(
                bounded_dot_pass(
                    float(record["achieved_dot"]),
                    float(record["target_dot"]),
                    TOLERANCE,
                )
                for record in records
            )
        )

    def test_tolerance_boundary_and_invalid_values_fail_closed(self) -> None:
        target = 0.900
        self.assertTrue(bounded_dot_pass(target - TOLERANCE, target, TOLERANCE))
        self.assertFalse(
            bounded_dot_pass(target - TOLERANCE - 1.0e-12, target, TOLERANCE)
        )
        for invalid in (math.nan, math.inf, -math.inf, -1.000001, 1.000001):
            with self.subTest(value=invalid):
                self.assertFalse(bounded_dot_pass(invalid, target, TOLERANCE))

    def test_dihedral_limit_is_derived_from_same_dot_floor(self) -> None:
        expected = math.degrees(math.acos(0.900 - TOLERANCE))
        self.assertEqual(expected, 25.842458540318322)
        self.assertLess(float(self.solver["maximum_seam_dihedral_degrees"]), expected)
        self.assertGreater(
            float(self.solver["maximum_seam_dihedral_degrees"]), 25.841933
        )

    def test_solver_geometry_and_caps_are_unchanged(self) -> None:
        old_function = function_source(self.old_source, "attempt08_coupled_fit")
        new_function = function_source(self.new_source, "attempt08_coupled_fit")
        old_prefix = old_function[: old_function.index("    world_to_local =")].replace(
            "Attempt 13", "Attempt XX"
        )
        new_prefix = new_function[: new_function.index("    world_to_local =")].replace(
            "Attempt 14", "Attempt XX"
        )
        self.assertEqual(new_prefix, old_prefix)
        application_end = "    bm.normal_update()\n"
        old_application = old_function[
            old_function.index("    world_to_local =") : old_function.index(
                application_end, old_function.index("    world_to_local =")
            )
            + len(application_end)
        ]
        new_application = new_function[
            new_function.index("    world_to_local =") : new_function.index(
                application_end, new_function.index("    world_to_local =")
            )
            + len(application_end)
        ]
        self.assertEqual(new_application, old_application)
        for assignment in (
            "TARGET_BY_CLASS = a14.TARGET_BY_CLASS",
            "POSTSOLVE_DEFAULT_SEVERE_CEILING_M = 0.002330",
            "POSTSOLVE_OVERALL_CEILING_M = 0.002525",
            "POSTSOLVE_RMS_CEILING_M = 0.000460",
            "INHERITED_RING_1_CAP_M = 0.00240",
            "INHERITED_TOTAL_BASE_FIT_CAP_M = 0.00240",
        ):
            self.assertIn(assignment, self.new_source)

    def test_worker_preserves_strict_truth_and_replaces_only_exact_downstream_gates(self) -> None:
        ast.parse(self.new_source, filename=str(ATTEMPT14_WORKER))
        self.assertIn("FINAL_SEAM_DOT_NUMERICAL_TOLERANCE = 4.0e-06", self.new_source)
        self.assertIn(
            "math.acos(0.900 - FINAL_SEAM_DOT_NUMERICAL_TOLERANCE)",
            self.new_source,
        )
        for field in (
            '"strict_pass"',
            '"dot_deficit"',
            '"tolerance_used"',
            '"passed_with_bound_numerical_tolerance"',
            '"strict_target_checks"',
            '"strict_target_all_pass"',
        ):
            self.assertIn(field, self.new_source)
        self.assertIn("math.isfinite(value) and -1.0 <= value <= 1.0", self.new_source)
        for exact_gate in (
            '"attempt06_superior_minimum_0_985"',
            '"attempt06_severe_minimum_0_900"',
            '"attempt06_regular_minimum_0_965"',
        ):
            self.assertIn(exact_gate, self.new_source)
        self.assertIn("inherited_strict_seam_results", self.new_source)
        self.assertIn('"whole_seam_median_at_least_0_965"', self.new_source)

    def test_worker_is_append_only_bound_and_no_save(self) -> None:
        self.assertIn('EXPECTED_ATTEMPT_SLOT = "attempt_14"', self.new_source)
        self.assertIn(
            'ATTEMPT_14_PROPOSAL_SHA256 = "ac974d033fac40f0187972aa44921db6864f44e62691cc7ad9b4a4deb3d46f60"',
            self.new_source,
        )
        allocation = self.new_source.index("planned_output = next_append_only_output()")
        source_load = self.new_source.index("bpy.ops.wm.open_mainfile")
        for binding in (
            '"attempt_13 revision-04 worker"',
            '"attempt_13 pre-mask"',
            '"attempt_13 pre-cap"',
            '"attempt_13 solver"',
            '"attempt_13 failure"',
            '"attempt_14 revision-05 proposal"',
        ):
            location = self.new_source.index(binding)
            self.assertLess(location, allocation)
            self.assertLess(location, source_load)
        self.assertNotIn("bpy.ops.wm.save", self.new_source)
        self.assertNotIn("save_as_mainfile", self.new_source)
        self.assertFalse((EVIDENCE_ROOT / "attempt_14").exists())


if __name__ == "__main__":
    unittest.main()
