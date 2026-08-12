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
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT20_CONFIG.json"
)
WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt20.py"
)
ATTEMPT19_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt19.py"
)
ATTEMPT18_WORKER = (
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
    spec = importlib.util.spec_from_file_location("attempt20_static_worker", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Attempt 20 worker specification")
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
    def length(self) -> float:
        return math.sqrt(sum(value * value for value in self.values))

    def copy(self) -> "FakeVector":
        return FakeVector(self.values)

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
    if {node.name for node in nodes} != wanted:
        raise AssertionError(
            f"missing functions: {sorted(wanted - {node.name for node in nodes})}"
        )
    module = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, "<attempt20-sanitizers>", "exec"), namespace, namespace)
    return {name: namespace[name] for name in names}


class R24BlackProjectAttempt20StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_json(CONFIG)
        cls.module = load_worker_module()
        cls.provider = cls.module.load_attempt19_module()
        cls.source19 = cls.provider.derive_attempt19_source(
            ATTEMPT18_WORKER.read_text(encoding="utf-8")
        )
        cls.source20 = cls.module.derive_attempt20_source(cls.source19)
        cls.sanitizers = extract_functions(
            cls.source20,
            (
                "orient2d",
                "cdt_tolerances",
                "sanitize_cdt_seed_points",
                "cdt_seed_is_separated",
                "sanitize_cdt_output",
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

    def sanitation_config(self) -> dict[str, Any]:
        return dict(self.config["sanitation_parameters"])

    def test_all_bindings_and_attempt15_19_evidence_are_exact(self) -> None:
        records = dict(self.config["bindings"])
        records["proposal"] = self.config["proposal"]
        for name, record in records.items():
            path = ROOT / record["path"]
            with self.subTest(name=name):
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, record["bytes"])
                self.assertEqual(sha256(path), record["sha256"])
        preserved = self.config["preserved_attempts_15_19"]
        expected_paths = {
            self.config["bindings"][name]["path"]
            for name in preserved["binding_names"]
        }
        actual_paths = {
            path.relative_to(ROOT).as_posix()
            for number in range(15, 20)
            for path in (EVIDENCE_ROOT / f"attempt_{number:02d}").rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual_paths, expected_paths)
        self.assertEqual(len(actual_paths), preserved["file_count"])
        self.assertEqual(
            sum((ROOT / path).stat().st_size for path in actual_paths),
            preserved["total_bytes"],
        )

    def test_attempt19_failure_diagnosis_is_exact_and_not_overclaimed(self) -> None:
        failure = load_json(EVIDENCE_ROOT / "attempt_19" / "FAILURE.json")
        inventory = load_json(EVIDENCE_ROOT / "attempt_19" / "APPEND_INVENTORY.json")
        diagnosis = self.config["diagnosis"]
        self.assertEqual(failure["error"], diagnosis["attempt19_error"])
        self.assertEqual(failure["status"], "NO_SAVE_ATTEMPT18_FAILED_PRESERVED_FOR_DIAGNOSIS")
        self.assertFalse(failure["blend_saved"])
        self.assertFalse(failure["runtime_changed"])
        self.assertEqual(
            inventory["status"],
            "PASS_EXACT_SEVEN_OBJECT_HIERARCHY_NO_NEW_COLLECTIONS",
        )
        self.assertFalse(inventory["geometry_mutation_reached"])
        self.assertFalse(diagnosis["failure_was_seed_cap_exhaustion"])
        self.assertFalse(diagnosis["failure_was_proven_iteration_cap_exhaustion"])
        self.assertFalse(diagnosis["primitive_subtype_recorded_by_attempt19"])
        self.assertEqual(diagnosis["configured_seed_cap"], 160)
        self.assertEqual(diagnosis["configured_iteration_cap"], 192)

    def test_representative_degenerate_output_is_sanitized_to_exact_disk(self) -> None:
        boundary = [
            FakeVector((0.0, 0.0)),
            FakeVector((2.0, 0.0)),
            FakeVector((2.0, 2.0)),
            FakeVector((0.0, 2.0)),
        ]
        coordinates = boundary + [
            FakeVector((1.0, 1.0)),
            FakeVector((0.0, 0.0)),
            FakeVector((1.0, 0.0)),
        ]
        faces = [
            [0, 1, 4],
            [1, 2, 4],
            [2, 3, 4],
            [3, 0, 4],
            [0, 0, 1],
            [0, 5, 4],
            [0, 6, 1],
            [4, 1, 0],
        ]
        originals: list[Sequence[int]] = [
            {0},
            {1},
            {2},
            {3},
            set(),
            set(),
            set(),
        ]
        coordinates_after, faces_after, original_after, diagnostic = self.sanitizers[
            "sanitize_cdt_output"
        ](
            coordinates,
            faces,
            originals,
            4,
            boundary,
            1.0e-12,
            self.sanitation_config(),
        )
        self.assertEqual([value.values for value in coordinates_after[:4]], [value.values for value in boundary])
        self.assertEqual(faces_after, [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]])
        self.assertEqual(len(coordinates_after), 5)
        self.assertEqual(len(original_after), 5)
        self.assertEqual(diagnostic["compacted_unused_nonboundary_point_count"], 2)
        self.assertEqual(
            diagnostic["removed_faces"],
            {
                "repeated_index": 1,
                "coincident_coordinate": 1,
                "collinear_or_near_zero_area": 1,
                "duplicate_face": 1,
            },
        )
        boundary_output = {index: index for index in range(4)}
        topology = self.sanitizers["validate_cdt_disk"](
            faces_after, boundary_output, 4
        )
        self.assertEqual(topology["euler_characteristic"], 1)
        self.assertEqual(topology["face_component_count"], 1)
        self.assertEqual(topology["boundary_edge_count"], 4)
        self.assertTrue(topology["exact_boundary_is_complete_open_edge_set"])

    def test_hole_or_boundary_loss_fails_closed(self) -> None:
        faces_with_hole = [[0, 1, 4], [1, 2, 4], [2, 3, 4]]
        with self.assertRaisesRegex(RuntimeError, "open edges do not equal exact boundary"):
            self.sanitizers["validate_cdt_disk"](
                faces_with_hole, {index: index for index in range(4)}, 4
            )
        with self.assertRaisesRegex(RuntimeError, "boundary source mapping is incomplete"):
            self.sanitizers["validate_cdt_disk"](
                [[0, 1, 2]], {0: 0, 1: 1, 2: 2}, 4
            )

    def test_seed_deduplication_is_ordered_scale_aware_and_boundary_safe(self) -> None:
        boundary = [
            FakeVector((0.0, 0.0)),
            FakeVector((2.0, 0.0)),
            FakeVector((2.0, 2.0)),
            FakeVector((0.0, 2.0)),
        ]
        center = FakeVector((1.0, 1.0))
        seeds = [
            center,
            center.copy(),
            FakeVector((1.0e-10, 1.0e-10)),
            FakeVector((1.5, 1.0)),
        ]
        accepted, diagnostic = self.sanitizers["sanitize_cdt_seed_points"](
            boundary, seeds, 1.0e-12, self.sanitation_config()
        )
        self.assertEqual([value.values for value in accepted], [[1.0, 1.0], [1.5, 1.0]])
        self.assertEqual(diagnostic["rejected_near_boundary_count"], 1)
        self.assertEqual(diagnostic["rejected_near_seed_count"], 1)
        self.assertFalse(
            self.sanitizers["cdt_seed_is_separated"](
                center.copy(), boundary, accepted, 1.0e-12, self.sanitation_config()
            )
        )

    def test_gate_is_not_weakened_in_materialized_config_or_source(self) -> None:
        merged = self.module.load_attempt20_config(CONFIG)
        expected = self.config["unchanged_hard_gates"]
        self.assertEqual(merged["attempt_id"], "attempt_20")
        self.assertEqual(merged["replacement"]["minimum_new_triangle_angle_degrees"], 12.0)
        self.assertEqual(merged["hard_gates"]["minimum_new_triangle_angle_degrees"], 12.0)
        self.assertEqual(merged["replacement"]["minimum_new_triangle_world_area_m2"], 1.0e-10)
        self.assertEqual(merged["replacement"]["maximum_new_interior_vertex_count"], 160)
        self.assertEqual(merged["replacement"]["maximum_quality_refinement_iterations"], 192)
        self.assertEqual(expected["minimum_new_triangle_angle_degrees"], 12.0)
        self.assertIn('minimum = min(value[0] for value in quality)', self.source20)
        self.assertIn('if minimum >= threshold:', self.source20)
        self.assertIn('if minimum_angle < float(config["minimum_new_triangle_angle_degrees"]):', self.source20)

    def test_attempt20_evidence_labels_are_current_and_attempt19_typo_is_only_historical(self) -> None:
        labels = self.config["evidence_label_contract"]
        self.assertIn(labels["attempt20_started_schema"], self.source20)
        self.assertIn(labels["attempt20_failure_schema"], self.source20)
        self.assertIn(labels["attempt20_failure_status"], self.source20)
        self.assertIn(labels["attempt20_report_schema"], self.source20)
        self.assertNotIn("ATTEMPT18", self.source20)
        self.assertNotIn("attempt_19", self.source20)
        self.assertNotIn("attempt19", self.source20)
        self.assertNotIn("Attempt 19", self.source20)

    def test_derived_source_compiles_and_retains_all_protection_gates(self) -> None:
        compile(self.source20, "<attempt20-derived-worker>", "exec")
        for required in (
            "def sanitize_cdt_output(",
            "def validate_cdt_disk(",
            "exact_nonadjacent_intersection_report",
            "nonpatch Kira body or face snapshot changed",
            "protected object or native rig changed",
            "quality replacement minimum triangle angle failed",
            "owner visual decision is required after paired review",
        ):
            self.assertIn(required, self.source20)
        self.assertEqual(
            self.provider.unsafe_vector_accumulator_locations(self.source20), []
        )
        self.assertNotIn("bpy.ops.wm.save", self.source20)
        self.assertNotIn("save_as_mainfile", self.source20)
        self.assertNotIn("export_scene", self.source20)

    def test_append_only_scope_truth_and_self_binding(self) -> None:
        self.assertFalse((EVIDENCE_ROOT / "attempt_20").exists())
        self.assertEqual(self.module.EXPECTED_CONFIG_SHA256, sha256(CONFIG))
        scope = self.config["scope"]
        for name in (
            "blend_save_allowed",
            "export_allowed",
            "runtime_activation_allowed",
            "boundary_or_seam_movement_allowed",
            "quality_gate_reduction_allowed",
            "geometry_changes_beyond_cdt_sanitation_allowed",
        ):
            self.assertFalse(scope[name], name)
        truth = self.config["truth"]
        self.assertFalse(truth["primitive_degeneracy_subtype_known"])
        self.assertFalse(truth["internal_tract_or_physiology_implemented"])
        self.assertFalse(truth["bathroom_reproduction_or_pregnancy_function_proven"])
        self.assertFalse(truth["owner_approval_claimed"])


if __name__ == "__main__":
    unittest.main()
