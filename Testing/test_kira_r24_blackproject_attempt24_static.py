from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping, Sequence
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "RecoverySprint" / "continuation_20260807" / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT24_CONFIG.json"
WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt24.py"
EVIDENCE_ROOT = ROOT / "RecoverySprint" / "continuation_20260803" / "kira_r24_internal_midpoint_fair_surface"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_worker_module() -> Any:
    spec = importlib.util.spec_from_file_location("attempt24_static_worker", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Attempt 24 worker specification")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeVector:
    def __init__(self, values: Sequence[float]):
        self.values = [float(value) for value in values]

    @property
    def x(self) -> float:
        return self.values[0]

    @property
    def y(self) -> float:
        return self.values[1]


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
    actual = {node.name for node in nodes}
    if actual != wanted:
        raise AssertionError(f"missing functions: {sorted(wanted - actual)}")
    module = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, "<attempt24-refinement>", "exec"), namespace, namespace)
    return {name: namespace[name] for name in names}


class TerminalCapture(RuntimeError):
    pass


class R24BlackProjectAttempt24StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_json(CONFIG)
        cls.module = load_worker_module()
        cls.provider23 = cls.module.load_attempt23_module()
        cls.source23 = cls.module.materialize_attempt23_source(cls.provider23)
        cls.source24 = cls.module.derive_attempt24_source(cls.source23)
        cls.merged = cls.module.load_attempt24_config(CONFIG)

    @staticmethod
    def exact_result() -> dict[str, Any]:
        coordinates = [
            FakeVector((0.0, 0.0)),
            FakeVector((1.0, 0.0)),
            FakeVector((0.5, 0.866025403784)),
        ]
        return {
            "coordinates": coordinates,
            "faces": [[0, 1, 2]],
            "boundary_diagnostic": {
                "mismatch_detected": False,
                "mismatch_summary_class": "EXACT_BOUNDARY_ALREADY_MATCHED",
            },
        }

    @staticmethod
    def quality_namespace(
        run_cdt: Any,
        terminal: Any,
        triangle_angle: float,
        separated: bool = True,
    ) -> dict[str, Any]:
        incenter_calls = 0

        def mean(values: Sequence[FakeVector]) -> FakeVector:
            return FakeVector(
                (
                    sum(value.x for value in values) / len(values),
                    sum(value.y for value in values) / len(values),
                )
            )

        def distinct_incenter(values: Sequence[FakeVector]) -> FakeVector:
            nonlocal incenter_calls
            incenter_calls += 1
            center = mean(values)
            return FakeVector((center.x + 0.01 * incenter_calls, center.y))

        return {
            "Sequence": Sequence,
            "Mapping": Mapping,
            "Any": Any,
            "Vector": FakeVector,
            "run_cdt": run_cdt,
            "dimension_safe_vector_mean": mean,
            "sanitize_cdt_seed_points": lambda boundary, seeds, epsilon, config: (
                list(seeds),
                {"input_seed_count": len(seeds), "accepted_seed_count": len(seeds)},
            ),
            "triangle_angles": lambda points: [triangle_angle, 60.0, 60.0],
            "triangle_incenter": distinct_incenter,
            "cdt_seed_is_separated": lambda candidate, boundary, seeds, epsilon, config: separated,
            "capture_attempt24_terminal_and_stop": terminal,
        }

    def materialize_quality_function(self, namespace: dict[str, Any]) -> Any:
        return extract_functions(
            self.source24, ("quality_refined_cdt",), namespace
        )["quality_refined_cdt"]

    def base_config(self) -> dict[str, Any]:
        return {
            "cdt_epsilon_m": 1.0e-12,
            "minimum_new_triangle_angle_degrees": 12.0,
            "maximum_new_interior_vertex_count": 160,
            "maximum_quality_refinement_iterations": 192,
        }

    def test_complete_attempt23_package_and_logs_are_exact(self) -> None:
        records = dict(self.config["bindings"])
        records["proposal"] = self.config["proposal"]
        for name, record in records.items():
            path = ROOT / record["path"]
            with self.subTest(name=name):
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, record["bytes"])
                self.assertEqual(sha256(path), record["sha256"])
        preserved = self.config["preserved_attempt23_package"]
        self.assertEqual(len(preserved["binding_names"]), preserved["file_count"])
        self.assertEqual(
            sum(self.config["bindings"][name]["bytes"] for name in preserved["binding_names"]),
            preserved["total_bytes"],
        )

    def test_attempt23_capture_proves_initial_zero_seed_boundary_is_exact(self) -> None:
        capture = load_json(EVIDENCE_ROOT / "attempt_23" / "CDT_BOUNDARY_MISMATCH.json")
        diagnosis = self.config["diagnosis"]
        self.assertEqual(sha256(EVIDENCE_ROOT / "attempt_23" / "CDT_BOUNDARY_MISMATCH.json"), self.config["bindings"]["attempt23_capture"]["sha256"])
        self.assertFalse(capture["mismatch_detected"])
        self.assertEqual(capture["mismatch_summary_class"], "EXACT_BOUNDARY_ALREADY_MATCHED")
        for name in (
            "boundary_count",
            "coordinate_count",
            "face_count",
            "edge_count",
            "constrained_boundary_edge_count",
            "open_edge_count",
            "missing_boundary_edge_count",
            "extra_open_edge_count",
        ):
            self.assertEqual(capture[name], diagnosis[f"attempt23_{name}"])
        self.assertEqual(capture["constrained_boundary_edges"], capture["open_edges"])
        self.assertFalse(capture["geometry_mutation_reached"])

    def test_exact_initial_passes_then_later_mismatch_receives_context(self) -> None:
        calls: list[dict[str, Any]] = []
        result = self.exact_result()

        def terminal(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("quality loop terminal should not run before mismatch")

        def run(boundary: Any, seeds: Any, epsilon: Any, config: Any, context: Any) -> dict[str, Any]:
            calls.append({"seed_count": len(seeds), "context": context})
            if len(calls) == 1:
                return result
            self.assertEqual(context["phase"], "quality_refinement")
            self.assertEqual(context["refinement_iteration"], 0)
            self.assertEqual(context["requested_seed_count"], 1)
            self.assertEqual(context["previous_candidate_record"]["source"], "initial_exact_face_centroids")
            raise TerminalCapture("FIRST_ACTUAL_BOUNDARY_MISMATCH")

        function = self.materialize_quality_function(
            self.quality_namespace(run, terminal, 5.0)
        )
        with self.assertRaisesRegex(TerminalCapture, "FIRST_ACTUAL"):
            function([FakeVector((0.0, 0.0))], self.base_config())
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["context"]["phase"], "initial_zero_seed")
        self.assertEqual(calls[0]["seed_count"], 0)

    def test_exact_quality_target_terminal_captures_iteration_angle_and_seed(self) -> None:
        calls = []
        terminals = []
        result = self.exact_result()

        def run(boundary: Any, seeds: Any, epsilon: Any, config: Any, context: Any) -> dict[str, Any]:
            calls.append(context)
            return result

        def terminal(reason: str, boundary_state: Any, context: Any, quality: Any, config: Any) -> None:
            terminals.append((reason, boundary_state, context, quality))
            raise TerminalCapture(reason)

        function = self.materialize_quality_function(
            self.quality_namespace(run, terminal, 60.0)
        )
        with self.assertRaisesRegex(TerminalCapture, "QUALITY_TARGET_MET"):
            function([FakeVector((0.0, 0.0))], self.base_config())
        reason, boundary_state, context, quality = terminals[0]
        self.assertEqual(reason, "QUALITY_TARGET_MET_WITH_EXACT_BOUNDARY")
        self.assertFalse(boundary_state["mismatch_detected"])
        self.assertEqual(context["refinement_iteration"], 0)
        self.assertEqual(context["requested_seed_count"], 1)
        self.assertEqual(quality["minimum_2d_triangle_angle_degrees"], 60.0)
        self.assertEqual(quality["required_minimum_2d_triangle_angle_degrees"], 12.0)
        self.assertEqual(quality["candidate_diagnostics"], [])

    def test_other_exact_terminal_reasons_and_candidate_diagnostics(self) -> None:
        result = self.exact_result()

        def exercise(config_update: dict[str, Any], separated: bool) -> tuple[str, dict[str, Any]]:
            captured = []

            def run(boundary: Any, seeds: Any, epsilon: Any, config: Any, context: Any) -> dict[str, Any]:
                return result

            def terminal(reason: str, boundary_state: Any, context: Any, quality: Any, config: Any) -> None:
                captured.append((reason, quality))
                raise TerminalCapture(reason)

            function = self.materialize_quality_function(
                self.quality_namespace(run, terminal, 5.0, separated=separated)
            )
            config = self.base_config()
            config.update(config_update)
            with self.assertRaises(TerminalCapture):
                function([FakeVector((0.0, 0.0))], config)
            return captured[0]

        reason, quality = exercise({"maximum_new_interior_vertex_count": 1}, True)
        self.assertEqual(reason, "SEED_CAP_REACHED_WITH_EXACT_BOUNDARY")
        self.assertEqual(quality["seed_count"], 1)

        reason, quality = exercise({}, False)
        self.assertEqual(reason, "NO_ADMISSIBLE_CANDIDATE_WITH_EXACT_BOUNDARY")
        self.assertEqual(len(quality["candidate_diagnostics"]), 2)
        self.assertTrue(all(not row["admissible"] for row in quality["candidate_diagnostics"]))

        reason, quality = exercise({"maximum_quality_refinement_iterations": 0}, True)
        self.assertEqual(reason, "ITERATION_CAP_EXHAUSTED_WITH_EXACT_BOUNDARY")
        self.assertEqual(quality["refinement_iteration"], 0)
        self.assertEqual(sum(bool(row["selected"]) for row in quality["candidate_diagnostics"]), 1)

    def test_append_only_atomic_writer_refuses_overwrite(self) -> None:
        namespace = {
            "Path": Path,
            "Mapping": Mapping,
            "Any": Any,
            "atomic_write_json": lambda path, payload: path.write_text(
                json.dumps(payload, sort_keys=True), encoding="utf-8"
            ),
        }
        writer = extract_functions(
            self.source24, ("atomic_write_attempt24_once",), namespace
        )["atomic_write_attempt24_once"]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "terminal.json"
            writer(path, {"first": True})
            before = path.read_bytes()
            with self.assertRaisesRegex(RuntimeError, "refusing overwrite"):
                writer(path, {"second": True})
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"first": True})

    def test_run_cdt_writes_only_on_mismatch_and_returns_exact_state(self) -> None:
        run_start = self.source24.index("def run_cdt(")
        quality_start = self.source24.index("def quality_refined_cdt(")
        source = self.source24[run_start:quality_start]
        mismatch_if = source.index('if boundary_mismatch["mismatch_detected"]:')
        capture = source.index("capture_attempt24_terminal_and_stop(", mismatch_if)
        recovery = source.index("faces, boundary_segmentation_recovery = restore_exact_boundary_segmentation(")
        returned = source.index('"boundary_diagnostic": boundary_mismatch')
        self.assertLess(mismatch_if, capture)
        self.assertLess(capture, recovery)
        self.assertLess(recovery, returned)
        self.assertNotIn("atomic_write_json(mismatch_path, boundary_mismatch)", source)
        self.assertIn("diagnostic_context: Mapping[str, Any] | None = None", source)

    def test_labels_gates_scope_and_no_reconstruction_result(self) -> None:
        compile(self.source24, "<attempt24-derived-worker>", "exec")
        self.assertEqual(self.merged["attempt_id"], "attempt_24")
        self.assertEqual(self.merged["replacement"]["minimum_new_triangle_angle_degrees"], 12.0)
        self.assertEqual(self.merged["hard_gates"]["minimum_new_triangle_angle_degrees"], 12.0)
        self.assertEqual(self.merged["replacement"]["minimum_new_triangle_world_area_m2"], 1.0e-10)
        labels = self.config["evidence_label_contract"]
        for name in (
            "attempt24_started_schema",
            "attempt24_terminal_schema",
            "attempt24_failure_schema",
            "attempt24_failure_status",
            "attempt24_report_schema",
        ):
            self.assertIn(labels[name], self.source24)
        for name in (
            "attempt24_boundary_terminal_error",
            "attempt24_exact_terminal_error",
        ):
            first, second = labels[name].split("; ", 1)
            self.assertIn(first, self.source24)
            self.assertIn(second, self.source24)
        for stale in ("ATTEMPT23", "attempt_23", "attempt23", "Attempt 23"):
            self.assertNotIn(stale, self.source24)
        self.assertNotIn("return result\n\n\ndef reconstruct_local_domain", self.source24)
        for forbidden in ("bpy.ops.wm.save", "save_as_mainfile", "export_scene"):
            self.assertNotIn(forbidden, self.source24)
        self.assertEqual(self.module.EXPECTED_CONFIG_SHA256, sha256(CONFIG))
        self.assertFalse((EVIDENCE_ROOT / "attempt_24").exists())
        for name, value in self.config["scope"].items():
            if name in {"append_only", "private", "inactive", "unassigned", "unpublished", "diagnostic_simulation_only"}:
                self.assertTrue(value, name)
            else:
                self.assertFalse(value, name)
        self.assertFalse(self.config["truth"]["attempt24_geometry_repair_implemented"])


if __name__ == "__main__":
    unittest.main()
