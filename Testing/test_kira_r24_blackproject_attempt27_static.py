from __future__ import annotations

import ast
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import unittest
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "RecoverySprint" / "continuation_20260808" / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT27_CONFIG.json"
WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt27.py"
EVIDENCE_ROOT = ROOT / "RecoverySprint" / "continuation_20260803" / "kira_r24_internal_midpoint_fair_surface"
ATTEMPT26_FAILURE = EVIDENCE_ROOT / "attempt_26" / "FAILURE.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("attempt27_static_subject", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Attempt 27 worker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_functions(
    source: str, names: Sequence[str], namespace: dict[str, Any]
) -> dict[str, Any]:
    wanted = set(names)
    tree = ast.parse(source)
    nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    if {node.name for node in nodes} != wanted:
        raise RuntimeError("requested Attempt 27 functions are absent")
    module = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, "<attempt27-extracted>", "exec"), namespace, namespace)
    return {name: namespace[name] for name in names}


class FakeVector:
    def __init__(self, values: Sequence[float]) -> None:
        self.x = float(values[0])
        self.y = float(values[1])

    def __sub__(self, other: "FakeVector") -> "FakeVector":
        return FakeVector((self.x - other.x, self.y - other.y))

    @property
    def length(self) -> float:
        return math.hypot(self.x, self.y)


def orient2d(first: FakeVector, second: FakeVector, third: FakeVector) -> float:
    return (
        (second.x - first.x) * (third.y - first.y)
        - (second.y - first.y) * (third.x - first.x)
    )


def triangle_angles(points: Sequence[FakeVector]) -> list[float]:
    rows = []
    for index in range(3):
        center = points[index]
        first = points[(index + 1) % 3]
        second = points[(index + 2) % 3]
        ax, ay = first.x - center.x, first.y - center.y
        bx, by = second.x - center.x, second.y - center.y
        la, lb = math.hypot(ax, ay), math.hypot(bx, by)
        cosine = max(-1.0, min(1.0, (ax * bx + ay * by) / (la * lb)))
        rows.append(math.degrees(math.acos(cosine)))
    return rows


class R24BlackProjectAttempt27StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_json(CONFIG)
        cls.module = load_module(WORKER)
        cls.merged = cls.module.load_attempt27_config(CONFIG)
        provider = cls.module.load_attempt26_module()
        cls.source26 = cls.module.materialize_attempt26_source(provider)
        cls.source27 = cls.module.derive_attempt27_source(cls.source26)

    @staticmethod
    def namespace() -> dict[str, Any]:
        return {
            "Any": Any,
            "Mapping": Mapping,
            "Sequence": Sequence,
            "Vector": FakeVector,
            "Path": Path,
            "ROOT": ROOT,
            "datetime": datetime,
            "timezone": timezone,
            "math": math,
            "orient2d": orient2d,
            "triangle_angles": triangle_angles,
        }

    @classmethod
    def functions(cls) -> dict[str, Any]:
        names = (
            "attempt27_xy",
            "attempt27_edge_length",
            "attempt27_point_segment_diagnostic",
            "attempt27_nearest_boundary_segment",
            "attempt27_boundary_angle_diagnostics",
            "attempt27_candidate_child_split",
            "attempt27_seed_rows",
            "attempt27_build_no_candidate_diagnostic",
        )
        return extract_functions(cls.source27, names, cls.namespace())

    def test_attempt26_package_and_live_failure_are_exact(self) -> None:
        records = dict(self.config["bindings"])
        records["proposal"] = self.config["proposal"]
        for name, record in records.items():
            path = ROOT / record["path"]
            with self.subTest(name=name):
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, record["bytes"])
                self.assertEqual(sha256(path), record["sha256"])
        preserved = self.config["preserved_attempt26_package"]
        rows = [records[name] for name in preserved["binding_names"]]
        self.assertEqual(len(rows), preserved["file_count"])
        self.assertEqual(sum(row["bytes"] for row in rows), preserved["total_bytes"])
        self.assertEqual(sha256(ATTEMPT26_FAILURE), self.config["diagnosis"]["attempt26_failure_sha256"])

    def test_attempt26_failure_is_exact_no_candidate_stop(self) -> None:
        failure = load_json(ATTEMPT26_FAILURE)
        self.assertEqual(failure["status"], "NO_SAVE_ATTEMPT26_FAILED_PRESERVED_FOR_DIAGNOSIS")
        self.assertIn("reason=NO_ADMISSIBLE_CANDIDATE", failure["error"])
        self.assertIn("achieved=0.01978234059262607", failure["error"])
        self.assertIn("required=12.0", failure["error"])
        self.assertIn("seeds=36", failure["error"])
        self.assertFalse(failure["blend_saved"])
        self.assertFalse(failure["runtime_changed"])

    def test_derived_source_only_instruments_existing_terminal(self) -> None:
        compile(self.source27, "<attempt27-derived>", "exec")
        self.assertEqual(self.source27.count('("triangle_incenter", triangle_incenter(points))'), 1)
        self.assertEqual(self.source27.count('("triangle_centroid", dimension_safe_vector_mean(points))'), 1)
        self.assertIn('separation["admissible_by_candidate_geometry"]', self.source27)
        self.assertIn('terminal_reason = "NO_ADMISSIBLE_CANDIDATE"', self.source27)
        self.assertIn("attempt27_build_no_candidate_diagnostic", self.source27)
        self.assertIn("diagnostic-only stop before reconstruction", self.source27)
        for forbidden in (
            "bpy.ops.wm.save",
            "save_as_mainfile",
            "export_scene",
            "generic_hole_fill",
        ):
            self.assertNotIn(forbidden, self.source27)
        for stale in ("ATTEMPT26", "attempt_26", "attempt26", "Attempt 26"):
            self.assertNotIn(stale, self.source27)

    def test_fixed_pslg_boundary_corner_test_is_necessary_only(self) -> None:
        function = self.functions()["attempt27_boundary_angle_diagnostics"]
        square = [
            FakeVector((0, 0)),
            FakeVector((1, 0)),
            FakeVector((1, 1)),
            FakeVector((0, 1)),
        ]
        row = function(square, 12.0)
        self.assertAlmostEqual(row["minimum_boundary_interior_angle_degrees"], 90.0)
        self.assertTrue(row["necessary_fixed_boundary_corner_condition_passes"])
        self.assertNotIn("sufficient", json.dumps(row).lower())
        acute = [
            FakeVector((0, 0)),
            FakeVector((1, 0)),
            FakeVector((math.cos(math.radians(5)), math.sin(math.radians(5)))),
        ]
        acute_row = function(acute, 12.0)
        self.assertAlmostEqual(
            acute_row["minimum_boundary_interior_angle_degrees"], 5.0, places=10
        )
        self.assertFalse(
            acute_row["necessary_fixed_boundary_corner_condition_passes"]
        )

    def test_payload_captures_exact_geometry_candidates_seeds_and_bounded_truth(self) -> None:
        functions = self.functions()
        build = functions["attempt27_build_no_candidate_diagnostic"]
        boundary = [
            FakeVector((0, 0)),
            FakeVector((1, 0)),
            FakeVector((1, 1)),
            FakeVector((0, 1)),
        ]
        points = [
            FakeVector((0, 0)),
            FakeVector((1, 0)),
            FakeVector((0.0001, 0.00000001)),
        ]
        angles = triangle_angles(points)
        incenter = FakeVector((0.0001, 0.000000005))
        centroid = FakeVector((sum(v.x for v in points) / 3, sum(v.y for v in points) / 3))
        candidate_rows = [
            {
                "candidate_index": 0,
                "nearest_seed_pair_indices": [0, 1],
                "nearest_seed_pair_length_m": 0.5,
                "actual_pair_altitude_m": 0.0,
                "required_pair_altitude_m": 1e-9,
                "admissible_by_candidate_geometry": False,
                "admissible": False,
                "selected": False,
            },
            {
                "candidate_index": 1,
                "nearest_seed_pair_indices": [0, 1],
                "nearest_seed_pair_length_m": 0.5,
                "actual_pair_altitude_m": 0.0,
                "required_pair_altitude_m": 1e-9,
                "admissible_by_candidate_geometry": False,
                "admissible": False,
                "selected": False,
            },
        ]
        constrained = [
            {"output_indices": [0, 1], "boundary_source_indices": [0, 1]},
            {"output_indices": [1, 2], "boundary_source_indices": [1, 2]},
            {"output_indices": [2, 3], "boundary_source_indices": [2, 3]},
            {"output_indices": [0, 3], "boundary_source_indices": [0, 3]},
        ]
        result = {
            "coordinates": points,
            "faces": [[0, 1, 2]],
            "boundary_diagnostic": {
                "constrained_boundary_edges": constrained,
                "boundary_source_to_output": [
                    {"boundary_source_index": i, "output_index": i}
                    for i in range(4)
                ],
                "missing_boundary_edge_count": 0,
                "extra_open_edge_count": 0,
            },
            "disk_topology": {
                "face_component_count": 1,
                "euler_characteristic": 1,
            },
        }
        payload = build(
            boundary,
            {"minimum_new_triangle_angle_degrees": 12.0},
            7,
            result,
            [FakeVector((0.2, 0.2))],
            1,
            {"accepted_seed_count": 1},
            [{"source_iteration": 7, "selected_candidate_index": None, "candidate_diagnostics": candidate_rows}],
            min(angles),
            0,
            [0, 1, 2],
            points,
            angles,
            [("triangle_incenter", incenter), ("triangle_centroid", centroid)],
            candidate_rows,
            2,
            1,
        )
        self.assertEqual(payload["terminal_reason"], "NO_ADMISSIBLE_CANDIDATE")
        self.assertEqual(payload["worst_face"]["coordinates"], [[0.0, 0.0], [1.0, 0.0], [0.0001, 1e-08]])
        self.assertEqual(len(payload["worst_face"]["edge_rows"]), 3)
        self.assertEqual(len(payload["candidate_diagnostics"]), 2)
        self.assertEqual(payload["accepted_seeds"][0]["origin"], "initial_sanitized_face_centroid")
        self.assertEqual(len(payload["fixed_pslg"]["ordered_boundary_segments"]), 4)
        bounded = payload["bounded_12_degree_feasibility"]
        self.assertFalse(bounded["local_single_point_split"]["can_all_child_angles_reach_target_while_retaining_both_incident_edges"])
        self.assertEqual(bounded["global_fixed_pslg_conclusion"], "UNRESOLVED_BY_BOUNDED_NUMERICAL_DIAGNOSTIC")
        self.assertFalse(bounded["candidate_rejection_alone_used_as_global_proof"])
        self.assertFalse(payload["repair_applied"])
        self.assertFalse(payload["reconstruction_reached"])
        self.assertFalse(payload["blend_saved"])

    def test_seed_origin_mapping_fails_closed(self) -> None:
        function = self.functions()["attempt27_seed_rows"]
        with self.assertRaisesRegex(RuntimeError, "cannot map accepted seeds"):
            function(
                [FakeVector((0, 0)), FakeVector((1, 1))],
                1,
                [],
            )

    def test_scope_paths_labels_and_hard_gates(self) -> None:
        self.assertEqual(self.merged["attempt_id"], "attempt_27")
        self.assertEqual(self.merged["replacement"]["minimum_new_triangle_angle_degrees"], 12.0)
        self.assertEqual(self.merged["replacement"]["minimum_new_triangle_world_area_m2"], 1e-10)
        self.assertEqual(self.module.EXPECTED_CONFIG_SHA256, sha256(CONFIG))
        self.assertFalse((EVIDENCE_ROOT / "attempt_27").exists())
        self.assertFalse(self.config["scope"]["candidate_seed_policy_change_allowed"])
        self.assertFalse(self.config["scope"]["in_memory_local_body_reconstruction_allowed"])
        self.assertFalse(self.config["scope"]["body_geometry_mutation_allowed"])
        self.assertFalse(self.config["scope"]["quality_gate_reduction_allowed"])
        self.assertFalse(self.config["scope"]["blend_save_allowed"])
        self.assertFalse(self.config["truth"]["attempt27_blender_execution_performed"])
        self.assertFalse(self.config["truth"]["attempt27_body_repair_proven"])

    def test_policy_and_global_truth_contract_fail_closed_on_drift(self) -> None:
        for mutation in ("reason", "seeds", "angle", "global", "claim"):
            overlay = copy.deepcopy(self.config)
            if mutation == "reason":
                overlay["diagnosis"]["attempt26_terminal_reason"] = "OTHER"
            elif mutation == "seeds":
                overlay["diagnosis"]["accepted_seed_count"] = 35
            elif mutation == "angle":
                overlay["diagnosis"]["required_minimum_angle_degrees"] = 11.0
            elif mutation == "global":
                overlay["feasibility_contract"]["global_infeasibility_rule"] = "candidate_rejected"
            else:
                overlay["feasibility_contract"]["no_feasibility_claim_from_candidate_rejection_alone"] = False
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                self.module.validate_contract(overlay)


if __name__ == "__main__":
    unittest.main()
