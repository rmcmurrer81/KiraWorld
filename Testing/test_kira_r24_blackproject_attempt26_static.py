from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import unittest
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "RecoverySprint" / "continuation_20260808" / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT26_CONFIG.json"
WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt26.py"
EVIDENCE_ROOT = ROOT / "RecoverySprint" / "continuation_20260803" / "kira_r24_internal_midpoint_fair_surface"
CAPTURE = EVIDENCE_ROOT / "attempt_25" / "CDT_CANDIDATE_REPAIR_FAILURE.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("attempt26_static_subject", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Attempt 26 worker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_functions(source: str, names: Sequence[str], namespace: dict[str, Any]) -> dict[str, Any]:
    wanted = set(names)
    tree = ast.parse(source)
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    if {node.name for node in nodes} != wanted:
        raise RuntimeError("requested Attempt 26 functions are absent")
    module = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, "<attempt26-extracted>", "exec"), namespace, namespace)
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

    def copy(self) -> "FakeVector":
        return FakeVector((self.x, self.y))


class R24BlackProjectAttempt26StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_json(CONFIG)
        cls.capture = load_json(CAPTURE)
        cls.state = cls.capture["boundary_state"]
        cls.module = load_module(WORKER)
        cls.merged = cls.module.load_attempt26_config(CONFIG)
        provider = cls.module.load_attempt25_module()
        cls.source26 = cls.module.derive_attempt26_source(
            cls.module.materialize_attempt25_source(provider)
        )
        cls.rows = {int(row["output_index"]): row for row in cls.state["coordinates"]}
        cls.by_source = {}
        for row in cls.state["coordinates"]:
            for source in row["original_input_source_indices"]:
                cls.by_source[int(source)] = FakeVector(row["xy"])

    @staticmethod
    def namespace() -> dict[str, Any]:
        return {"Any": Any, "Mapping": Mapping, "Sequence": Sequence, "Vector": FakeVector, "math": math}

    @classmethod
    def functions(cls, additions: Mapping[str, Any] | None = None) -> dict[str, Any]:
        namespace = cls.namespace()
        if additions:
            namespace.update(additions)
        return extract_functions(
            cls.source26,
            (
                "orient2d",
                "cdt_tolerances",
                "attempt26_candidate_separation_diagnostics",
                "attempt26_assert_exact_boundary_and_disk",
            ),
            namespace,
        )

    @classmethod
    def captured_inputs(cls) -> tuple[list[FakeVector], list[FakeVector], list[FakeVector]]:
        boundary = [cls.by_source[index] for index in range(32)]
        seeds = [cls.by_source[index] for index in range(32, 74)]
        points = [FakeVector(cls.rows[index]["xy"]) for index in (19, 20, 73)]
        return boundary, seeds, points

    @staticmethod
    def exact_result(points: list[FakeVector]) -> dict[str, Any]:
        return {
            "coordinates": points,
            "faces": [[0, 1, 2]],
            "boundary_diagnostic": {
                "mismatch_detected": False,
                "missing_boundary_edge_count": 0,
                "extra_open_edge_count": 0,
                "open_edge_count": 32,
                "constrained_boundary_edge_count": 32,
            },
            "disk_topology": {
                "exact_boundary_is_complete_open_edge_set": True,
                "face_component_count": 1,
                "euler_characteristic": 1,
            },
        }

    def test_complete_attempt25_package_and_logs_are_exact(self) -> None:
        records = dict(self.config["bindings"])
        records["proposal"] = self.config["proposal"]
        for name, record in records.items():
            path = ROOT / record["path"]
            with self.subTest(name=name):
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, record["bytes"])
                self.assertEqual(sha256(path), record["sha256"])
        preserved = self.config["preserved_attempt25_package"]
        rows = [records[name] for name in preserved["binding_names"]]
        self.assertEqual(len(rows), preserved["file_count"])
        self.assertEqual(sum(row["bytes"] for row in rows), preserved["total_bytes"])
        self.assertEqual(sha256(CAPTURE), self.config["diagnosis"]["attempt25_capture_sha256"])

    def test_capture_is_exact_three_edge_interior_triangle_hole(self) -> None:
        self.assertEqual(self.capture["run_context"]["refinement_iteration"], 13)
        self.assertEqual(self.capture["run_context"]["requested_seed_count"], 43)
        self.assertEqual(self.state["missing_boundary_edge_count"], 0)
        self.assertEqual(self.state["extra_open_edge_count"], 3)
        self.assertEqual(self.state["cdt_sanitation"]["removed_faces"]["collinear_or_near_zero_area"], 1)
        edges = {tuple(sorted(row["output_indices"])) for row in self.state["extra_open_edges"]}
        self.assertEqual(edges, {(72, 73), (73, 74), (72, 74)})
        self.assertTrue(all(row["boundary_source_indices"] == [None, None] for row in self.state["extra_open_edges"]))
        previous = self.capture["run_context"]["previous_candidate_record"]
        self.assertEqual(previous["worst_face_output_indices"], [19, 20, 73])
        self.assertFalse(previous["candidate_diagnostics"][0]["admissible"])
        self.assertTrue(previous["candidate_diagnostics"][1]["selected"])
        self.assertEqual(self.rows[74]["xy"], previous["candidate_diagnostics"][1]["xy"])

    def test_captured_centroid_passes_point_but_fails_pair_altitude(self) -> None:
        function = self.functions()["attempt26_candidate_separation_diagnostics"]
        boundary, seeds, points = self.captured_inputs()
        centroid = FakeVector(self.rows[74]["xy"])
        row = function(centroid, "triangle_centroid", points, boundary, seeds, 1.0e-12, self.merged["replacement"])
        captured = self.config["candidate_admissibility_policy"]["captured_case"]
        self.assertTrue(row["separated_from_boundary_and_seeds"])
        self.assertEqual(row["nearest_seed_pair_indices"], [41, 40])
        self.assertAlmostEqual(row["nearest_seed_pair_length_m"], captured["nearest_seed_pair_length_m"], delta=1.0e-18)
        self.assertAlmostEqual(row["nearest_seed_pair_twice_area_m2"], captured["pair_twice_area_m2"], delta=1.0e-25)
        self.assertAlmostEqual(row["actual_pair_altitude_m"], captured["actual_pair_altitude_m"], delta=1.0e-18)
        self.assertAlmostEqual(row["required_pair_altitude_m"], captured["required_pair_altitude_m"], delta=1.0e-18)
        self.assertFalse(row["nearest_seed_pair_non_degenerate"])
        self.assertFalse(row["admissible_by_candidate_geometry"])
        self.assertEqual(row["rejection_reason"], "NEAREST_SEED_PAIR_ALTITUDE_AT_OR_BELOW_SANITATION_FLOOR")

    def test_noncollinear_candidate_passes_both_predicates(self) -> None:
        function = self.functions()["attempt26_candidate_separation_diagnostics"]
        boundary, seeds, points = self.captured_inputs()
        candidate = FakeVector((-0.0001, 0.0004))
        row = function(candidate, "bounded_noncollinear_probe", points, boundary, seeds, 1.0e-12, self.merged["replacement"])
        self.assertTrue(row["separated_from_boundary_and_seeds"])
        self.assertTrue(row["nearest_seed_pair_non_degenerate"])
        self.assertTrue(row["admissible_by_candidate_geometry"])
        self.assertIsNone(row["rejection_reason"])

    def test_quality_flow_stops_before_known_bad_43rd_seed(self) -> None:
        boundary, seeds, points = self.captured_inputs()
        previous = self.capture["run_context"]["previous_candidate_record"]
        incenter = FakeVector(previous["candidate_diagnostics"][0]["xy"])
        calls = {"run": 0}

        def mean(values: Sequence[FakeVector]) -> FakeVector:
            return FakeVector((sum(v.x for v in values) / len(values), sum(v.y for v in values) / len(values)))

        def run_cdt(_boundary: Any, current_seeds: Any, _epsilon: Any, _config: Any, _context: Any) -> dict[str, Any]:
            calls["run"] += 1
            if calls["run"] == 2:
                self.assertEqual(len(current_seeds), 42)
            if calls["run"] > 2:
                self.fail("Attempt 26 sent the rejected 43rd seed to CDT")
            return self.exact_result(points)

        def sanitize(_boundary: Any, _seeds: Any, _epsilon: Any, _config: Any) -> Any:
            return list(seeds), {"input_seed_count": 42, "accepted_seed_count": 42}

        namespace = self.namespace()
        namespace.update(
            {
                "run_cdt": run_cdt,
                "dimension_safe_vector_mean": mean,
                "sanitize_cdt_seed_points": sanitize,
                "triangle_angles": lambda _points: [0.0, 0.0, 180.0],
                "triangle_incenter": lambda _points: incenter,
            }
        )
        functions = extract_functions(
            self.source26,
            (
                "orient2d",
                "cdt_tolerances",
                "attempt26_candidate_separation_diagnostics",
                "attempt26_assert_exact_boundary_and_disk",
                "quality_refined_cdt",
            ),
            namespace,
        )
        config = copy.deepcopy(self.merged["replacement"])
        config["maximum_quality_refinement_iterations"] = 2
        with self.assertRaisesRegex(RuntimeError, "reason=NO_ADMISSIBLE_CANDIDATE"):
            functions["quality_refined_cdt"](boundary, config)
        self.assertEqual(calls["run"], 2)

    def test_exact_boundary_and_disk_gate_remains_fail_closed(self) -> None:
        gate = self.functions()["attempt26_assert_exact_boundary_and_disk"]
        valid = self.exact_result([FakeVector((0, 0)), FakeVector((1, 0)), FakeVector((0, 1))])
        self.assertEqual(gate(valid)["euler_characteristic"], 1)
        for section, key, value in (
            ("boundary_diagnostic", "missing_boundary_edge_count", 1),
            ("boundary_diagnostic", "extra_open_edge_count", 1),
            ("boundary_diagnostic", "mismatch_detected", True),
            ("disk_topology", "face_component_count", 2),
            ("disk_topology", "euler_characteristic", 0),
        ):
            broken = copy.deepcopy(valid)
            broken[section][key] = value
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                gate(broken)

    def test_policy_contract_fails_closed_on_drift(self) -> None:
        for mutation in ("required", "order", "arbitrary"):
            overlay = copy.deepcopy(self.config)
            if mutation == "required":
                overlay["candidate_admissibility_policy"]["captured_case"]["required_pair_altitude_m"] *= 2
            elif mutation == "order":
                overlay["candidate_admissibility_policy"]["candidate_order"].reverse()
            else:
                overlay["candidate_admissibility_policy"]["new_arbitrary_multiplier"] = True
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                self.module.validate_policy_contract(overlay)

    def test_labels_gates_scope_and_no_save(self) -> None:
        compile(self.source26, "<attempt26-derived>", "exec")
        self.assertEqual(self.merged["attempt_id"], "attempt_26")
        self.assertEqual(self.merged["replacement"]["minimum_new_triangle_angle_degrees"], 12.0)
        self.assertEqual(self.merged["replacement"]["minimum_new_triangle_world_area_m2"], 1e-10)
        self.assertIn("minimum_area_angle_local_edge_and_nearest_seed_pair_altitude_v2", self.source26)
        self.assertIn('separation["admissible_by_candidate_geometry"]', self.source26)
        labels = self.config["evidence_label_contract"]
        for key in (
            "attempt26_started_schema", "attempt26_failure_capture_schema",
            "attempt26_boundary_state_schema", "attempt26_failure_schema",
            "attempt26_failure_status", "attempt26_report_schema", "attempt26_candidate_policy_id",
        ):
            self.assertIn(labels[key], self.source26)
        for stale in ("ATTEMPT25", "attempt_25", "attempt25", "Attempt 25"):
            self.assertNotIn(stale, self.source26)
        for forbidden in ("bpy.ops.wm.save", "save_as_mainfile", "export_scene", "generic_hole_fill"):
            self.assertNotIn(forbidden, self.source26)
        self.assertEqual(self.module.EXPECTED_CONFIG_SHA256, sha256(CONFIG))
        self.assertFalse((EVIDENCE_ROOT / "attempt_26").exists())
        self.assertFalse(self.config["scope"]["quality_gate_reduction_allowed"])
        self.assertFalse(self.config["scope"]["boundary_or_seam_movement_allowed"])
        self.assertFalse(self.config["scope"]["blend_save_allowed"])
        self.assertTrue(self.config["truth"]["attempt26_pair_altitude_repair_implemented"])
        self.assertFalse(self.config["truth"]["attempt26_blender_execution_performed"])
        self.assertFalse(self.config["truth"]["attempt26_body_repair_proven"])


if __name__ == "__main__":
    unittest.main()
