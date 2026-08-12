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
CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260807"
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT25_CONFIG.json"
)
WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt25.py"
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_r24_internal_midpoint_fair_surface"
)
CAPTURE = EVIDENCE_ROOT / "attempt_24" / "CDT_REFINEMENT_TERMINAL.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("attempt25_static_subject", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Attempt 25 worker")
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
        raise RuntimeError("requested derived functions are absent")
    module = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, "<attempt25-extracted>", "exec"), namespace, namespace)
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


class R24BlackProjectAttempt25StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_json(CONFIG)
        cls.capture = load_json(CAPTURE)
        cls.module = load_module(WORKER)
        cls.merged = cls.module.load_attempt25_config(CONFIG)
        provider = cls.module.load_attempt24_module()
        source24 = cls.module.materialize_attempt24_source(provider)
        cls.source25 = cls.module.derive_attempt25_source(source24)
        cls.boundary_state = cls.capture["boundary_state"]
        cls.coordinate_rows = {
            int(row["output_index"]): row for row in cls.boundary_state["coordinates"]
        }
        cls.source_coordinates = {}
        for row in cls.boundary_state["coordinates"]:
            for source_index in row["original_input_source_indices"]:
                cls.source_coordinates[int(source_index)] = FakeVector(row["xy"])

    @staticmethod
    def base_namespace() -> dict[str, Any]:
        return {
            "Any": Any,
            "Mapping": Mapping,
            "Sequence": Sequence,
            "Vector": FakeVector,
            "math": math,
        }

    @classmethod
    def materialize_candidate_functions(
        cls, additions: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        namespace = cls.base_namespace()
        if additions:
            namespace.update(additions)
        return extract_functions(
            cls.source25,
            (
                "cdt_tolerances",
                "attempt25_candidate_separation_diagnostics",
                "attempt25_assert_exact_boundary_and_disk",
            ),
            namespace,
        )

    @classmethod
    def captured_vectors(cls) -> tuple[list[FakeVector], list[FakeVector], list[FakeVector]]:
        boundary = [cls.source_coordinates[index] for index in range(32)]
        pre_incenter_seeds = [cls.source_coordinates[index] for index in range(32, 73)]
        worst_points = [
            FakeVector(cls.coordinate_rows[index]["xy"]) for index in (19, 20, 72)
        ]
        return boundary, pre_incenter_seeds, worst_points

    @staticmethod
    def exact_result(coordinates: list[FakeVector]) -> dict[str, Any]:
        return {
            "coordinates": coordinates,
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

    def test_complete_attempt24_package_and_logs_are_exact(self) -> None:
        records = dict(self.config["bindings"])
        records["proposal"] = self.config["proposal"]
        for name, record in records.items():
            path = ROOT / record["path"]
            with self.subTest(name=name):
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, record["bytes"])
                self.assertEqual(sha256(path), record["sha256"])
        preserved = self.config["preserved_attempt24_package"]
        rows = [records[name] for name in preserved["binding_names"]]
        self.assertEqual(len(rows), preserved["file_count"])
        self.assertEqual(sum(row["bytes"] for row in rows), preserved["total_bytes"])
        self.assertEqual(sha256(CAPTURE), self.config["diagnosis"]["attempt24_capture_sha256"])

    def test_capture_reproduces_five_edge_near_collinear_interior_loop(self) -> None:
        terminal = self.capture
        state = self.boundary_state
        self.assertEqual(terminal["terminal_reason"], "FIRST_ACTUAL_BOUNDARY_MISMATCH")
        self.assertEqual(terminal["run_context"]["refinement_iteration"], 12)
        self.assertEqual(terminal["run_context"]["requested_seed_count"], 42)
        self.assertEqual(state["mismatch_summary_class"], "INTERIOR_OPEN_EDGE_TEAR_OR_REMOVED_FACE_HOLE")
        self.assertEqual(state["missing_boundary_edge_count"], 0)
        self.assertEqual(state["extra_open_edge_count"], 5)
        self.assertEqual(state["cdt_sanitation"]["input_face_count"], 114)
        self.assertEqual(state["cdt_sanitation"]["output_face_count"], 111)
        self.assertEqual(
            state["cdt_sanitation"]["removed_faces"]["collinear_or_near_zero_area"],
            3,
        )
        edges = {
            tuple(sorted(int(value) for value in row["output_indices"]))
            for row in state["extra_open_edges"]
        }
        expected = {(68, 69), (69, 70), (70, 72), (72, 73), (68, 73)}
        self.assertEqual(edges, expected)
        self.assertTrue(
            all(
                row["boundary_source_indices"] == [None, None]
                for row in state["extra_open_edges"]
            )
        )
        degrees = {index: 0 for index in (68, 69, 70, 72, 73)}
        for first, second in edges:
            degrees[first] += 1
            degrees[second] += 1
        self.assertEqual(set(degrees.values()), {2})
        order = (68, 69, 70, 72, 73, 68)
        distances = [
            math.dist(
                self.coordinate_rows[first]["xy"],
                self.coordinate_rows[second]["xy"],
            )
            for first, second in zip(order, order[1:])
        ]
        expected_distances = [
            8.372174047766007e-8,
            4.187511842088382e-8,
            2.0953403748536017e-8,
            1.04735786084373e-8,
            1.5702377552311375e-7,
        ]
        for actual, expected_distance in zip(distances, expected_distances):
            self.assertAlmostEqual(actual, expected_distance, delta=2.0e-15)
        self.assertLess(
            max(distances) / state["tolerances"]["boundary_diagonal_m"], 1.5e-5
        )

    def test_captured_formula_rejects_incenter_and_accepts_centroid(self) -> None:
        functions = self.materialize_candidate_functions()
        candidate = functions["attempt25_candidate_separation_diagnostics"]
        boundary, seeds, points = self.captured_vectors()
        previous = self.capture["run_context"]["previous_candidate_record"]
        incenter = FakeVector(previous["candidate_diagnostics"][0]["xy"])
        centroid = FakeVector(previous["candidate_diagnostics"][1]["xy"])
        config = self.merged["replacement"]
        rejected = candidate(
            incenter, "triangle_incenter", points, boundary, seeds, 1.0e-12, config
        )
        accepted = candidate(
            centroid, "triangle_centroid", points, boundary, seeds, 1.0e-12, config
        )
        captured = self.config["candidate_admissibility_policy"]["captured_case"]
        self.assertAlmostEqual(
            rejected["required_separation_m"],
            captured["required_separation_m"],
            delta=1.0e-18,
        )
        self.assertAlmostEqual(
            rejected["area_altitude_floor_m"],
            captured["area_altitude_floor_m"],
            delta=1.0e-18,
        )
        self.assertAlmostEqual(
            rejected["angle_altitude_floor_m"],
            captured["angle_altitude_floor_m"],
            delta=1.0e-18,
        )
        self.assertFalse(rejected["separated_from_boundary_and_seeds"])
        self.assertEqual(rejected["nearest_reference_type"], "seed")
        self.assertAlmostEqual(
            rejected["nearest_reference_distance_m"], 1.04735786084373e-8, delta=1.0e-18
        )
        self.assertTrue(accepted["separated_from_boundary_and_seeds"])
        self.assertEqual(accepted["nearest_reference_type"], "boundary")
        self.assertAlmostEqual(
            accepted["nearest_reference_distance_m"], 5.672949077494197e-5, delta=1.0e-16
        )

    def test_capture_binds_exact_bad_candidate_sequence(self) -> None:
        previous = self.capture["run_context"]["previous_candidate_record"]
        self.assertEqual(previous["source_iteration"], 11)
        self.assertEqual(previous["worst_face_output_indices"], [19, 20, 72])
        self.assertEqual(previous["selected_candidate_index"], 0)
        incenter, centroid = previous["candidate_diagnostics"]
        self.assertEqual(incenter["method"], "triangle_incenter")
        self.assertTrue(incenter["admissible"])
        self.assertTrue(incenter["selected"])
        self.assertEqual(centroid["method"], "triangle_centroid")
        self.assertTrue(centroid["admissible"])
        self.assertFalse(centroid["selected"])
        self.assertEqual(
            self.coordinate_rows[73]["xy"], incenter["xy"]
        )
        self.assertEqual(
            self.coordinate_rows[73]["original_input_source_indices"], [73]
        )

    def test_policy_contract_fails_closed_on_numeric_or_order_drift(self) -> None:
        for mutation in ("required", "order", "arbitrary"):
            overlay = copy.deepcopy(self.config)
            if mutation == "required":
                overlay["candidate_admissibility_policy"]["captured_case"][
                    "required_separation_m"
                ] *= 2.0
            elif mutation == "order":
                overlay["candidate_admissibility_policy"]["candidate_order"].reverse()
            else:
                overlay["candidate_admissibility_policy"][
                    "new_arbitrary_length_constant"
                ] = True
            with self.subTest(mutation=mutation):
                with self.assertRaises(RuntimeError):
                    self.module.validate_policy_contract(overlay)

    def test_quality_flow_selects_centroid_then_passes_exact_disk_gate(self) -> None:
        boundary, captured_seeds, worst_points = self.captured_vectors()
        previous = self.capture["run_context"]["previous_candidate_record"]
        captured_incenter = FakeVector(previous["candidate_diagnostics"][0]["xy"])
        captured_centroid = FakeVector(previous["candidate_diagnostics"][1]["xy"])
        calls = {"run": 0, "angles": 0}

        def mean(values: Sequence[FakeVector]) -> FakeVector:
            return FakeVector(
                (
                    sum(value.x for value in values) / len(values),
                    sum(value.y for value in values) / len(values),
                )
            )

        replay_centroid = mean(worst_points)
        self.assertAlmostEqual(replay_centroid.x, captured_centroid.x, delta=1.0e-11)
        self.assertAlmostEqual(replay_centroid.y, captured_centroid.y, delta=1.0e-11)

        def run_cdt(
            _boundary: Any, seeds: Any, _epsilon: Any, _config: Any, _context: Any
        ) -> dict[str, Any]:
            calls["run"] += 1
            if calls["run"] == 1:
                return self.exact_result(worst_points)
            if calls["run"] == 2:
                self.assertEqual(len(seeds), len(captured_seeds))
                return self.exact_result(worst_points)
            self.assertEqual(len(seeds), len(captured_seeds) + 1)
            self.assertAlmostEqual(seeds[-1].x, replay_centroid.x, delta=1.0e-18)
            self.assertAlmostEqual(seeds[-1].y, replay_centroid.y, delta=1.0e-18)
            return self.exact_result(worst_points)

        def sanitize(_boundary: Any, _seeds: Any, _epsilon: Any, _config: Any) -> Any:
            return list(captured_seeds), {
                "input_seed_count": len(captured_seeds),
                "accepted_seed_count": len(captured_seeds),
            }

        def angles(_points: Any) -> list[float]:
            calls["angles"] += 1
            return [0.0, 90.0, 90.0] if calls["angles"] == 1 else [12.0, 84.0, 84.0]

        namespace = self.base_namespace()
        namespace.update(
            {
                "run_cdt": run_cdt,
                "dimension_safe_vector_mean": mean,
                "sanitize_cdt_seed_points": sanitize,
                "triangle_angles": angles,
                "triangle_incenter": lambda _points: captured_incenter,
            }
        )
        functions = extract_functions(
            self.source25,
            (
                "cdt_tolerances",
                "attempt25_candidate_separation_diagnostics",
                "attempt25_assert_exact_boundary_and_disk",
                "quality_refined_cdt",
            ),
            namespace,
        )
        config = copy.deepcopy(self.merged["replacement"])
        config["maximum_quality_refinement_iterations"] = 2
        result = functions["quality_refined_cdt"](boundary, config)
        first = result["attempt25_candidate_history"][0]["candidate_diagnostics"]
        self.assertFalse(first[0]["admissible"])
        self.assertFalse(first[0]["selected"])
        self.assertTrue(first[1]["admissible"])
        self.assertTrue(first[1]["selected"])
        self.assertEqual(result["attempt25_rejected_incenter_count"], 1)
        self.assertEqual(result["attempt25_centroid_fallback_selection_count"], 1)
        self.assertEqual(result["attempt25_exact_boundary_and_disk_gate"]["euler_characteristic"], 1)
        self.assertEqual(result["boundary_diagnostic"]["missing_boundary_edge_count"], 0)
        self.assertEqual(result["boundary_diagnostic"]["extra_open_edge_count"], 0)

    def test_exact_boundary_and_disk_gate_fails_closed(self) -> None:
        gate = self.materialize_candidate_functions()[
            "attempt25_assert_exact_boundary_and_disk"
        ]
        valid = self.exact_result([FakeVector((0, 0)), FakeVector((1, 0)), FakeVector((0, 1))])
        self.assertEqual(gate(valid)["euler_characteristic"], 1)
        mutations = (
            ("boundary_diagnostic", "missing_boundary_edge_count", 1),
            ("boundary_diagnostic", "extra_open_edge_count", 1),
            ("boundary_diagnostic", "mismatch_detected", True),
            ("disk_topology", "exact_boundary_is_complete_open_edge_set", False),
            ("disk_topology", "face_component_count", 2),
            ("disk_topology", "euler_characteristic", 0),
        )
        for section, key, value in mutations:
            broken = copy.deepcopy(valid)
            broken[section][key] = value
            with self.subTest(section=section, key=key):
                with self.assertRaises(RuntimeError):
                    gate(broken)

    def test_labels_scope_gates_and_source_are_actual_repair_no_save(self) -> None:
        compile(self.source25, "<attempt25-derived-worker>", "exec")
        self.assertEqual(self.merged["attempt_id"], "attempt_25")
        self.assertEqual(self.merged["replacement"]["minimum_new_triangle_angle_degrees"], 12.0)
        self.assertEqual(self.merged["hard_gates"]["minimum_new_triangle_angle_degrees"], 12.0)
        self.assertEqual(self.merged["replacement"]["minimum_new_triangle_world_area_m2"], 1.0e-10)
        self.assertIn("minimum_area_angle_local_edge_separation_v1", self.source25)
        self.assertIn("candidate-admissibility repair still produced a CDT", self.source25)
        self.assertIn("mismatch; no-save stop before reconstruction", self.source25)
        labels = self.config["evidence_label_contract"]
        for name in (
            "attempt25_started_schema",
            "attempt25_failure_capture_schema",
            "attempt25_boundary_state_schema",
            "attempt25_failure_schema",
            "attempt25_failure_status",
            "attempt25_report_schema",
            "attempt25_candidate_policy_id",
        ):
            self.assertIn(labels[name], self.source25)
        self.assertIn("attempt25_assert_exact_boundary_and_disk(result)", self.source25)
        self.assertIn('if minimum >= threshold:', self.source25)
        self.assertIn('return result', self.source25)
        for stale in ("ATTEMPT24", "attempt_24", "attempt24", "Attempt 24"):
            self.assertNotIn(stale, self.source25)
        for forbidden in (
            "bpy.ops.wm.save",
            "save_as_mainfile",
            "export_scene",
            "generic_hole_fill",
        ):
            self.assertNotIn(forbidden, self.source25)
        self.assertEqual(self.module.EXPECTED_CONFIG_SHA256, sha256(CONFIG))
        self.assertFalse((EVIDENCE_ROOT / "attempt_25").exists())
        self.assertTrue(self.config["scope"]["candidate_seed_policy_change_allowed"])
        self.assertFalse(self.config["scope"]["quality_gate_reduction_allowed"])
        self.assertFalse(self.config["scope"]["boundary_or_seam_movement_allowed"])
        self.assertFalse(self.config["scope"]["blend_save_allowed"])
        self.assertTrue(self.config["truth"]["attempt25_candidate_admissibility_repair_implemented"])
        self.assertFalse(self.config["truth"]["attempt25_blender_execution_performed"])
        self.assertFalse(self.config["truth"]["attempt25_body_repair_proven"])


if __name__ == "__main__":
    unittest.main()
