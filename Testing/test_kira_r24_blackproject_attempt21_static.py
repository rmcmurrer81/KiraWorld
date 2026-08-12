from __future__ import annotations

import ast
from collections import deque
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
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT21_CONFIG.json"
)
WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt21.py"
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
    spec = importlib.util.spec_from_file_location("attempt21_static_worker", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Attempt 21 worker specification")
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

    @property
    def length(self) -> float:
        return math.sqrt(sum(value * value for value in self.values))

    def __sub__(self, other: "FakeVector") -> "FakeVector":
        return FakeVector(
            [first - second for first, second in zip(self.values, other.values)]
        )


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
    exec(compile(module, "<attempt21-boundary-recovery>", "exec"), namespace, namespace)
    return {name: namespace[name] for name in names}


class R24BlackProjectAttempt21StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_json(CONFIG)
        cls.module = load_worker_module()
        cls.provider20 = cls.module.load_attempt20_module()
        cls.source20 = cls.module.materialize_attempt20_source(cls.provider20)
        cls.source21 = cls.module.derive_attempt21_source(cls.source20)
        cls.merged = cls.module.load_attempt21_config(CONFIG)
        cls.functions = extract_functions(
            cls.source21,
            (
                "orient2d",
                "cdt_tolerances",
                "cdt_edge_state",
                "exact_boundary_edges",
                "boundary_source_chain",
                "proven_collinear_boundary_chain",
                "restore_exact_boundary_segmentation",
                "validate_cdt_disk",
            ),
            {
                "Sequence": Sequence,
                "Mapping": Mapping,
                "Any": Any,
                "Vector": FakeVector,
                "math": math,
                "deque": deque,
            },
        )

    @staticmethod
    def square() -> tuple[list[FakeVector], list[list[int]], dict[int, int]]:
        boundary = [
            FakeVector((0.0, 0.0)),
            FakeVector((2.0, 0.0)),
            FakeVector((2.0, 2.0)),
            FakeVector((0.0, 2.0)),
        ]
        coordinates = boundary + [FakeVector((1.0, 1.0))]
        faces = [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]]
        return coordinates, faces, {index: index for index in range(4)}

    def recover(
        self,
        coordinates: list[FakeVector],
        faces: list[list[int]],
        boundary_output: dict[int, int],
        boundary: list[FakeVector],
    ) -> tuple[list[list[int]], dict[str, Any]]:
        return self.functions["restore_exact_boundary_segmentation"](
            coordinates,
            faces,
            boundary_output,
            len(boundary),
            boundary,
            1.0e-12,
            self.merged["replacement"],
        )

    def test_complete_attempt20_package_and_logs_are_exact(self) -> None:
        records = dict(self.config["bindings"])
        records["proposal"] = self.config["proposal"]
        for name, record in records.items():
            path = ROOT / record["path"]
            with self.subTest(name=name):
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, record["bytes"])
                self.assertEqual(sha256(path), record["sha256"])
        preserved = self.config["preserved_attempt20_package"]
        self.assertEqual(len(preserved["binding_names"]), preserved["file_count"])
        self.assertEqual(
            sum(
                self.config["bindings"][name]["bytes"]
                for name in preserved["binding_names"]
            ),
            preserved["total_bytes"],
        )

    def test_attempt20_failure_and_diagnosis_are_exact_and_bounded(self) -> None:
        failure = load_json(EVIDENCE_ROOT / "attempt_20" / "FAILURE.json")
        diagnosis = self.config["diagnosis"]
        self.assertEqual(failure["error"], diagnosis["attempt20_error"])
        self.assertEqual(
            failure["status"], "NO_SAVE_ATTEMPT20_FAILED_PRESERVED_FOR_DIAGNOSIS"
        )
        self.assertFalse(failure["blend_saved"])
        self.assertFalse(failure["runtime_changed"])
        self.assertFalse(diagnosis["exact_failed_edge_sets_serialized"])
        self.assertFalse(diagnosis["live_shortcut_collinearity_proven_by_attempt20"])
        self.assertTrue(diagnosis["all_other_holes_or_tears_fail_closed"])
        stderr = (ROOT / self.config["bindings"]["attempt20_stderr"]["path"]).read_text(
            encoding="utf-8"
        )
        self.assertIn(diagnosis["attempt20_error"], stderr)

    def test_already_exact_disk_is_a_coordinate_and_face_noop(self) -> None:
        coordinates, faces, boundary_output = self.square()
        before_coordinates = [value.values[:] for value in coordinates]
        restored, diagnostic = self.recover(
            coordinates, faces, boundary_output, coordinates[:4]
        )
        self.assertEqual(restored, faces)
        self.assertEqual([value.values for value in coordinates], before_coordinates)
        self.assertEqual(diagnostic["recovery_count"], 0)
        self.assertTrue(diagnostic["coordinates_unchanged"])
        topology = self.functions["validate_cdt_disk"](
            restored, boundary_output, 4
        )
        self.assertEqual(topology["euler_characteristic"], 1)

    def test_collinear_shortcut_is_split_through_exact_boundary_vertex(self) -> None:
        boundary = [
            FakeVector((0.0, 0.0)),
            FakeVector((1.0, 0.0)),
            FakeVector((2.0, 0.0)),
            FakeVector((2.0, 2.0)),
            FakeVector((0.0, 2.0)),
        ]
        coordinates = boundary + [FakeVector((1.0, 1.0))]
        faces = [[0, 2, 5], [2, 3, 5], [3, 4, 5], [4, 0, 5]]
        boundary_output = {index: index for index in range(5)}
        before_coordinates = [value.values[:] for value in coordinates]
        restored, diagnostic = self.recover(
            coordinates, faces, boundary_output, boundary
        )
        self.assertEqual(
            restored,
            [[0, 1, 5], [1, 2, 5], [2, 3, 5], [3, 4, 5], [4, 0, 5]],
        )
        self.assertEqual([value.values for value in coordinates], before_coordinates)
        self.assertEqual(diagnostic["recovery_count"], 1)
        self.assertEqual(diagnostic["restored_boundary_segment_count"], 2)
        self.assertTrue(diagnostic["exact_boundary_restored"])
        self.assertLess(
            diagnostic["recoveries"][0]["mismatch_after"],
            diagnostic["recoveries"][0]["mismatch_before"],
        )
        topology = self.functions["validate_cdt_disk"](
            restored, boundary_output, 5
        )
        self.assertEqual(topology["boundary_edge_count"], 5)
        self.assertEqual(topology["euler_characteristic"], 1)
        self.assertTrue(topology["exact_boundary_is_complete_open_edge_set"])

    def test_noncollinear_shortcut_and_interior_open_edge_fail_closed(self) -> None:
        boundary = [
            FakeVector((0.0, 0.0)),
            FakeVector((1.0, 0.25)),
            FakeVector((2.0, 0.0)),
            FakeVector((2.0, 2.0)),
            FakeVector((0.0, 2.0)),
        ]
        coordinates = boundary + [FakeVector((1.0, 1.0))]
        faces = [[0, 2, 5], [2, 3, 5], [3, 4, 5], [4, 0, 5]]
        with self.assertRaisesRegex(RuntimeError, "no unique collinear"):
            self.recover(
                coordinates,
                faces,
                {index: index for index in range(5)},
                boundary,
            )

        square_coordinates, square_faces, square_boundary = self.square()
        with self.assertRaisesRegex(RuntimeError, "no unique collinear"):
            self.recover(
                square_coordinates,
                square_faces[:-1],
                square_boundary,
                square_coordinates[:4],
            )

    def test_boundary_apex_and_ambiguous_or_invalid_recovery_fail_closed(self) -> None:
        boundary = [
            FakeVector((0.0, 0.0)),
            FakeVector((1.0, 0.0)),
            FakeVector((2.0, 0.0)),
            FakeVector((2.0, 2.0)),
            FakeVector((0.0, 2.0)),
        ]
        with self.assertRaisesRegex(RuntimeError, "unchanged interior apex"):
            self.recover(
                boundary,
                [[0, 2, 3], [3, 4, 0]],
                {index: index for index in range(5)},
                boundary,
            )

    def test_hard_gates_and_source_protections_are_unchanged(self) -> None:
        unchanged = self.config["unchanged_hard_gates"]
        self.assertEqual(self.merged["attempt_id"], "attempt_21")
        self.assertEqual(
            self.merged["replacement"]["minimum_new_triangle_angle_degrees"],
            unchanged["minimum_new_triangle_angle_degrees"],
        )
        self.assertEqual(
            self.merged["hard_gates"]["minimum_new_triangle_angle_degrees"], 12.0
        )
        self.assertEqual(
            self.merged["replacement"]["minimum_new_triangle_world_area_m2"],
            1.0e-10,
        )
        self.assertEqual(unchanged["global_seam_vertex_count"], 34)
        self.assertEqual(unchanged["local_boundary_vertex_count"], 32)
        self.assertIn('if minimum >= threshold:', self.source21)
        self.assertIn(
            'if minimum_angle < float(config["minimum_new_triangle_angle_degrees"]):',
            self.source21,
        )
        self.assertLess(
            self.source21.index("faces, boundary_segmentation_recovery ="),
            self.source21.index("disk_topology = validate_cdt_disk"),
        )
        for required in (
            "exact_nonadjacent_intersection_report",
            "nonpatch Kira body or face snapshot changed",
            "protected object or native rig changed",
            "owner visual decision is required after paired review",
            "exact boundary segmentation recovery found no unique collinear boundary shortcut",
            "cdt_boundary_segmentation_recovery",
        ):
            self.assertIn(required, self.source21)
        provider19 = self.provider20.load_attempt19_module()
        self.assertEqual(provider19.unsafe_vector_accumulator_locations(self.source21), [])
        self.assertNotIn("bpy.ops.wm.save", self.source21)
        self.assertNotIn("save_as_mainfile", self.source21)
        self.assertNotIn("export_scene", self.source21)

    def test_attempt21_labels_scope_truth_and_append_only_state(self) -> None:
        labels = self.config["evidence_label_contract"]
        for name in (
            "attempt21_started_schema",
            "attempt21_failure_schema",
            "attempt21_failure_status",
            "attempt21_report_schema",
        ):
            self.assertIn(labels[name], self.source21)
        for stale in ("ATTEMPT20", "attempt_20", "attempt20", "Attempt 20"):
            self.assertNotIn(stale, self.source21)
        self.assertEqual(self.module.EXPECTED_CONFIG_SHA256, sha256(CONFIG))
        self.assertFalse((EVIDENCE_ROOT / "attempt_21").exists())
        for name, value in self.config["scope"].items():
            if name in {"append_only", "private", "inactive", "unassigned", "unpublished", "simulation_only"}:
                self.assertTrue(value, name)
            else:
                self.assertFalse(value, name)
        truth = self.config["truth"]
        self.assertFalse(truth["live_shortcut_collinearity_known"])
        self.assertFalse(truth["internal_tract_or_physiology_implemented"])
        self.assertFalse(truth["bathroom_reproduction_or_pregnancy_function_proven"])
        self.assertFalse(truth["owner_approval_claimed"])


if __name__ == "__main__":
    unittest.main()
