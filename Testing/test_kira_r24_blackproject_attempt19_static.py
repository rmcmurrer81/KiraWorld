from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260807"
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT19_CONFIG.json"
)
WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt19.py"
)
BASE_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt18.py"
)
EVIDENCE_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260803"
    / "kira_r24_internal_midpoint_fair_surface"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_worker_module() -> Any:
    spec = importlib.util.spec_from_file_location("attempt19_static_worker", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Attempt 19 worker specification")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeVector:
    def __init__(self, values: Sequence[float]):
        self.values = [float(value) for value in values]

    def __len__(self) -> int:
        return len(self.values)

    @property
    def x(self) -> float:
        return self.values[0]

    @property
    def y(self) -> float:
        return self.values[1]

    @property
    def z(self) -> float:
        return self.values[2]

    @property
    def length(self) -> float:
        return math.sqrt(sum(value * value for value in self.values))

    def copy(self) -> "FakeVector":
        return FakeVector(self.values)

    def __iadd__(self, other: "FakeVector") -> "FakeVector":
        if len(self) != len(other):
            raise ValueError("fake vector dimension mismatch")
        self.values = [first + second for first, second in zip(self.values, other.values)]
        return self

    def __add__(self, other: "FakeVector") -> "FakeVector":
        result = self.copy()
        result += other
        return result

    def __sub__(self, other: "FakeVector") -> "FakeVector":
        if len(self) != len(other):
            raise ValueError("fake vector dimension mismatch")
        return FakeVector(
            [first - second for first, second in zip(self.values, other.values)]
        )

    def __truediv__(self, divisor: float) -> "FakeVector":
        return FakeVector([value / float(divisor) for value in self.values])

    def normalized(self) -> "FakeVector":
        length = self.length
        if length == 0.0:
            raise ValueError("cannot normalize a zero vector")
        return self / length


def extract_function(source: str, name: str, namespace: dict[str, Any]) -> Any:
    tree = ast.parse(source)
    matches = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected one function {name}, got {len(matches)}")
    module = ast.Module(body=[matches[0]], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, f"<attempt19:{name}>", "exec"), namespace, namespace)
    return namespace[name]


class R24BlackProjectAttempt19StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_json(CONFIG)
        cls.module = load_worker_module()
        cls.base_source = BASE_WORKER.read_text(encoding="utf-8")
        cls.derived_source = cls.module.derive_attempt19_source(cls.base_source)

    def test_all_bindings_and_attempt15_18_evidence_are_exact(self) -> None:
        records = dict(self.config["bindings"])
        records["proposal"] = self.config["proposal"]
        for name, record in records.items():
            path = ROOT / record["path"]
            with self.subTest(name=name):
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, record["bytes"])
                self.assertEqual(sha256(path), record["sha256"])

        preserved = self.config["preserved_attempts_15_18"]
        expected_paths = {
            self.config["bindings"][name]["path"]
            for name in preserved["binding_names"]
        }
        actual_paths = {
            path.relative_to(ROOT).as_posix()
            for number in range(15, 19)
            for path in (EVIDENCE_ROOT / f"attempt_{number:02d}").rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual_paths, expected_paths)
        self.assertEqual(len(actual_paths), preserved["file_count"])
        self.assertEqual(
            sum((ROOT / path).stat().st_size for path in actual_paths),
            preserved["total_bytes"],
        )

    def test_attempt18_failure_and_logs_are_exactly_diagnosed(self) -> None:
        failure = load_json(EVIDENCE_ROOT / "attempt_18" / "FAILURE.json")
        inventory = load_json(EVIDENCE_ROOT / "attempt_18" / "APPEND_INVENTORY.json")
        self.assertEqual(
            failure["error"],
            "Vector addition: vectors must have the same dimensions for this operation",
        )
        self.assertIn("line 396, in quality_refined_cdt", failure["traceback"])
        self.assertIn(
            'sum((base["coordinates"][index] for index in face), Vector()) / 3.0',
            failure["traceback"],
        )
        self.assertFalse(failure["blend_saved"])
        self.assertFalse(failure["runtime_changed"])
        self.assertEqual(
            inventory["status"],
            "PASS_EXACT_SEVEN_OBJECT_HIERARCHY_NO_NEW_COLLECTIONS",
        )
        self.assertFalse(inventory["geometry_mutation_reached"])
        self.assertFalse(inventory["render_reached"])
        stderr = (
            ROOT / self.config["bindings"]["attempt18_stderr"]["path"]
        ).read_text(encoding="utf-8")
        self.assertIn("line 396, in quality_refined_cdt", stderr)

    def test_derived_source_has_exact_complete_vector_accumulator_audit(self) -> None:
        self.assertEqual(
            self.module.unsafe_vector_accumulator_locations(self.base_source),
            [(396, 8), (420, 12), (630, 21)],
        )
        self.assertEqual(
            self.module.unsafe_vector_accumulator_locations(self.derived_source), []
        )
        self.assertNotIn("Vector()", self.derived_source)
        self.assertNotIn("attempt_18", self.derived_source)
        self.assertNotIn("attempt18", self.derived_source)
        self.assertNotIn("Attempt 18", self.derived_source)
        compile(self.derived_source, "<attempt19-derived-worker>", "exec")
        for _name, old, new in self.module.MEAN_REPLACEMENTS:
            self.assertNotIn(old, self.derived_source)
            self.assertEqual(self.derived_source.count(new), 1)

    def test_scalar_sum_paths_remain_unchanged(self) -> None:
        for expression in (
            "return 0.5 * sum(",
            "total = sum(weights)",
            "edge: sum(face in selected_faces for face in edge.link_faces)",
            "total = float(np.sum(weights))",
        ):
            with self.subTest(expression=expression):
                self.assertIn(expression, self.base_source)
                self.assertIn(expression, self.derived_source)
        named_sum_calls = [
            node
            for node in ast.walk(ast.parse(self.derived_source))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "sum"
        ]
        self.assertEqual(len(named_sum_calls), 3)

    def test_dimension_safe_helper_executes_2d_3d_and_fail_closed_paths(self) -> None:
        namespace = {"Sequence": Sequence, "Any": Any}
        mean = extract_function(
            self.derived_source, "dimension_safe_vector_mean", namespace
        )
        mean2 = mean([FakeVector((0.0, 2.0)), FakeVector((2.0, 4.0))])
        mean3 = mean(
            [
                FakeVector((1.0, 2.0, 3.0)),
                FakeVector((3.0, 4.0, 5.0)),
                FakeVector((5.0, 6.0, 7.0)),
            ]
        )
        self.assertEqual(mean2.values, [1.0, 3.0])
        self.assertEqual(mean3.values, [3.0, 4.0, 5.0])
        with self.assertRaisesRegex(ValueError, "at least one sample"):
            mean([])
        with self.assertRaisesRegex(ValueError, "mixed dimensions"):
            mean([FakeVector((1.0, 2.0)), FakeVector((1.0, 2.0, 3.0))])

    def test_both_quality_refinement_centroid_paths_execute(self) -> None:
        helper_namespace = {"Sequence": Sequence, "Any": Any}
        real_mean = extract_function(
            self.derived_source,
            "dimension_safe_vector_mean",
            helper_namespace,
        )
        mean_calls: list[list[int]] = []

        def recording_mean(samples: Sequence[FakeVector]) -> FakeVector:
            values = list(samples)
            mean_calls.append([len(value) for value in values])
            return real_mean(values)

        run_count = 0

        def run_cdt(
            _boundary: Sequence[FakeVector],
            _seeds: Sequence[FakeVector],
            _epsilon: float,
        ) -> dict[str, Any]:
            nonlocal run_count
            run_count += 1
            offset = 0.0 if run_count == 1 else 20.0
            return {
                "coordinates": [
                    FakeVector((offset, offset)),
                    FakeVector((offset + 3.0, offset)),
                    FakeVector((offset, offset + 3.0)),
                ],
                "faces": [[0, 1, 2]],
                "boundary_output": {},
                "maximum_boundary_delta_2d_m": 0.0,
            }

        angle_count = 0

        def triangle_angles(_points: Sequence[FakeVector]) -> list[float]:
            nonlocal angle_count
            angle_count += 1
            return [1.0, 1.0, 1.0] if angle_count == 1 else [30.0, 30.0, 30.0]

        quality_namespace = {
            "Sequence": Sequence,
            "Mapping": Mapping,
            "Any": Any,
            "Vector": FakeVector,
            "run_cdt": run_cdt,
            "triangle_angles": triangle_angles,
            "triangle_incenter": lambda _points: FakeVector((1.0, 1.0)),
            "dimension_safe_vector_mean": recording_mean,
        }
        quality = extract_function(
            self.derived_source, "quality_refined_cdt", quality_namespace
        )
        result = quality(
            [
                FakeVector((-100.0, -100.0)),
                FakeVector((100.0, -100.0)),
                FakeVector((0.0, 100.0)),
            ],
            {
                "cdt_epsilon_m": 1.0e-6,
                "minimum_new_triangle_angle_degrees": 10.0,
                "maximum_new_interior_vertex_count": 8,
                "maximum_quality_refinement_iterations": 2,
            },
        )
        self.assertEqual(mean_calls, [[2, 2, 2], [2, 2, 2]])
        self.assertEqual(result["quality_refinement_iterations"], 1)
        self.assertEqual(result["seed_count"], 2)

    def test_surrounding_normal_mean_expression_executes(self) -> None:
        tree = ast.parse(self.derived_source)
        reconstruct = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "reconstruct_local_domain"
        )
        assignments = [
            node
            for node in ast.walk(reconstruct)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "average_normal"
                for target in node.targets
            )
        ]
        self.assertEqual(len(assignments), 1)
        expression = ast.Expression(body=assignments[0].value)
        ast.fix_missing_locations(expression)
        calls: list[list[int]] = []

        def recording_mean(samples: Sequence[FakeVector]) -> FakeVector:
            values = list(samples)
            calls.append([len(value) for value in values])
            total = values[0].copy()
            for value in values[1:]:
                total += value
            return total / len(values)

        result = eval(
            compile(expression, "<attempt19-surrounding-normal>", "eval"),
            {"dimension_safe_vector_mean": recording_mean},
            {
                "surrounding_normals": [
                    FakeVector((1.0, 0.0, 0.0)),
                    FakeVector((0.0, 1.0, 0.0)),
                    FakeVector((0.0, 0.0, 1.0)),
                ]
            },
        )
        self.assertEqual(calls, [[3, 3, 3]])
        self.assertAlmostEqual(result.length, 1.0, places=12)

    def test_complete_config_materializes_without_mutating_attempt18(self) -> None:
        base_before = BASE_WORKER.read_bytes()
        merged = self.module.load_attempt19_config(CONFIG)
        self.assertEqual(merged["attempt_id"], "attempt_19")
        self.assertEqual(
            merged["output"]["root"],
            "RecoverySprint/continuation_20260803/kira_r24_internal_midpoint_fair_surface/attempt_19",
        )
        self.assertEqual(merged["output"]["review_directory"], "private_owner_review")
        self.assertFalse(merged["output"]["blend_save_permitted"])
        self.assertFalse(self.config["scope"]["blend_save_allowed"])
        self.assertFalse(self.config["scope"]["runtime_activation_allowed"])
        self.assertEqual(
            len(merged["attempt19_vector_accumulator_audit"]["corrected_paths"]),
            3,
        )
        self.assertEqual(BASE_WORKER.read_bytes(), base_before)
        self.assertEqual(
            self.module.EXPECTED_CONFIG_SHA256,
            sha256(CONFIG),
        )

    def test_append_only_no_save_scope_and_truth_boundary(self) -> None:
        self.assertFalse((EVIDENCE_ROOT / "attempt_19").exists())
        self.assertNotIn("bpy.ops.wm.save", self.derived_source)
        self.assertNotIn("save_as_mainfile", self.derived_source)
        self.assertNotIn("export_scene", self.derived_source)
        truth = self.config["truth"]
        self.assertFalse(truth["internal_tract_or_physiology_implemented"])
        self.assertFalse(truth["bathroom_reproduction_or_pregnancy_function_proven"])
        self.assertFalse(truth["owner_approval_claimed"])
        self.assertFalse(truth["attempt18_geometry_mutation_reached"])
        self.assertFalse(truth["attempt18_render_reached"])


if __name__ == "__main__":
    unittest.main()
