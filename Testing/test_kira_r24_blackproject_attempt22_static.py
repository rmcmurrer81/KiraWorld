from __future__ import annotations

import ast
from collections import deque
from datetime import datetime, timezone
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
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT22_CONFIG.json"
)
WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt22.py"
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
    spec = importlib.util.spec_from_file_location("attempt22_static_worker", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Attempt 22 worker specification")
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
    exec(compile(module, "<attempt22-capture>", "exec"), namespace, namespace)
    return {name: namespace[name] for name in names}


class R24BlackProjectAttempt22StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_json(CONFIG)
        cls.module = load_worker_module()
        cls.provider21 = cls.module.load_attempt21_module()
        cls.source21 = cls.module.materialize_attempt21_source(cls.provider21)
        cls.source22 = cls.module.derive_attempt22_source(cls.source21)
        cls.merged = cls.module.load_attempt22_config(CONFIG)
        cls.functions = extract_functions(
            cls.source22,
            (
                "orient2d",
                "cdt_tolerances",
                "cdt_edge_state",
                "exact_boundary_edges",
                "boundary_source_chain",
                "canonical_json_sha256",
                "diagnostic_edge_row",
                "diagnostic_boundary_chain",
                "capture_exact_cdt_boundary_mismatch",
            ),
            {
                "Sequence": Sequence,
                "Mapping": Mapping,
                "Any": Any,
                "Vector": FakeVector,
                "math": math,
                "json": json,
                "hashlib": hashlib,
                "datetime": datetime,
                "timezone": timezone,
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

    def capture(
        self,
        coordinates: list[FakeVector],
        faces: list[list[int]],
        boundary_output: dict[int, int],
        boundary: list[FakeVector],
    ) -> dict[str, Any]:
        originals = [
            [index] if index < len(boundary) else []
            for index in range(len(coordinates))
        ]
        return self.functions["capture_exact_cdt_boundary_mismatch"](
            coordinates,
            faces,
            originals,
            boundary_output,
            len(boundary),
            boundary,
            1.0e-12,
            self.merged["replacement"],
            {"accepted_seed_count": 0},
            {"output_face_count": len(faces)},
        )

    def test_complete_attempt21_package_and_logs_are_exact(self) -> None:
        records = dict(self.config["bindings"])
        records["proposal"] = self.config["proposal"]
        for name, record in records.items():
            path = ROOT / record["path"]
            with self.subTest(name=name):
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, record["bytes"])
                self.assertEqual(sha256(path), record["sha256"])
        preserved = self.config["preserved_attempt21_package"]
        self.assertEqual(len(preserved["binding_names"]), preserved["file_count"])
        self.assertEqual(
            sum(
                self.config["bindings"][name]["bytes"]
                for name in preserved["binding_names"]
            ),
            preserved["total_bytes"],
        )

    def test_attempt21_terminal_result_is_exact_and_not_overclaimed(self) -> None:
        failure = load_json(EVIDENCE_ROOT / "attempt_21" / "FAILURE.json")
        inventory = load_json(EVIDENCE_ROOT / "attempt_21" / "APPEND_INVENTORY.json")
        diagnosis = self.config["diagnosis"]
        self.assertEqual(failure["error"], diagnosis["attempt21_error"])
        self.assertEqual(
            failure["status"], "NO_SAVE_ATTEMPT21_FAILED_PRESERVED_FOR_DIAGNOSIS"
        )
        self.assertFalse(failure["blend_saved"])
        self.assertFalse(failure["runtime_changed"])
        self.assertFalse(inventory["geometry_mutation_reached"])
        self.assertEqual(
            inventory["status"], "PASS_EXACT_SEVEN_OBJECT_HIERARCHY_NO_NEW_COLLECTIONS"
        )
        self.assertFalse(diagnosis["exact_open_expected_missing_extra_edge_sets_serialized"])
        self.assertFalse(diagnosis["exact_offending_coordinates_serialized"])
        self.assertFalse(diagnosis["mathematically_sound_repair_supported_by_current_evidence"])

    def test_real_terminal_subtype_noncollinear_shortcut_is_fully_serialized(self) -> None:
        boundary = [
            FakeVector((0.0, 0.0)),
            FakeVector((1.0, 0.25)),
            FakeVector((2.0, 0.0)),
            FakeVector((2.0, 2.0)),
            FakeVector((0.0, 2.0)),
        ]
        coordinates = boundary + [FakeVector((1.0, 1.0))]
        faces = [[0, 2, 5], [2, 3, 5], [3, 4, 5], [4, 0, 5]]
        result = self.capture(
            coordinates, faces, {index: index for index in range(5)}, boundary
        )
        self.assertTrue(result["mismatch_detected"])
        self.assertEqual(result["missing_boundary_edge_count"], 2)
        self.assertEqual(result["extra_open_edge_count"], 1)
        self.assertEqual(
            result["mismatch_summary_class"],
            "NONCOLLINEAR_BOUNDARY_SHORTCUT_OR_DOMAIN_FACE_MISMATCH",
        )
        extra = result["extra_open_edges"][0]
        self.assertEqual(extra["output_indices"], [0, 2])
        self.assertEqual(
            extra["classification"],
            "NONCOLLINEAR_OR_INCOMPLETE_BOUNDARY_SHORTCUT",
        )
        self.assertEqual(len(extra["ordered_boundary_chain_diagnostics"]), 2)
        direct = extra["ordered_boundary_chain_diagnostics"][0]
        self.assertEqual(direct["boundary_source_indices"], [0, 1, 2])
        self.assertGreater(direct["maximum_absolute_twice_area_residual"], 0.0)
        self.assertFalse(direct["all_vertices_collinear_with_chord"])
        self.assertFalse(direct["qualifies_unique_collinear_boundary_shortcut"])
        self.assertFalse(result["repair_applied"])
        self.assertEqual(
            result["coordinates"][1]["original_input_source_indices"], [1]
        )
        self.assertEqual(result["faces"][0]["coordinates"][1], [2.0, 0.0])
        for name, value in result["canonical_sha256"].items():
            with self.subTest(name=name):
                self.assertRegex(value, r"^[0-9a-f]{64}$")

    def test_interior_open_edge_tear_is_distinguished(self) -> None:
        coordinates, faces, boundary_output = self.square()
        result = self.capture(
            coordinates, faces[:-1], boundary_output, coordinates[:4]
        )
        self.assertEqual(
            result["mismatch_summary_class"],
            "INTERIOR_OPEN_EDGE_TEAR_OR_REMOVED_FACE_HOLE",
        )
        self.assertEqual(result["missing_boundary_edge_count"], 1)
        self.assertEqual(result["extra_open_edge_count"], 2)
        self.assertTrue(
            all(
                value["classification"] == "INTERIOR_ENDPOINT_OPEN_EDGE"
                for value in result["extra_open_edges"]
            )
        )
        incident = {
            tuple(value["output_indices"]): value["incident_face_indices"]
            for value in result["edges"]
        }
        self.assertEqual(incident[(0, 4)], [0])
        self.assertEqual(incident[(3, 4)], [2])

    def test_exact_disk_is_recorded_without_manufacturing_a_mismatch(self) -> None:
        coordinates, faces, boundary_output = self.square()
        result = self.capture(coordinates, faces, boundary_output, coordinates[:4])
        self.assertFalse(result["mismatch_detected"])
        self.assertEqual(result["mismatch_summary_class"], "EXACT_BOUNDARY_ALREADY_MATCHED")
        self.assertEqual(result["missing_boundary_edges"], [])
        self.assertEqual(result["extra_open_edges"], [])
        self.assertFalse(result["repair_applied"])

    def test_capture_is_deterministic_except_timestamp(self) -> None:
        coordinates, faces, boundary_output = self.square()
        first = self.capture(coordinates, faces[:-1], boundary_output, coordinates[:4])
        second = self.capture(coordinates, faces[:-1], boundary_output, coordinates[:4])
        first.pop("created_utc")
        second.pop("created_utc")
        self.assertEqual(first, second)

    def test_derived_worker_captures_atomically_and_stops_before_recovery(self) -> None:
        compile(self.source22, "<attempt22-derived-worker>", "exec")
        capture = self.source22.index(
            "boundary_mismatch = capture_exact_cdt_boundary_mismatch("
        )
        write = self.source22.index("atomic_write_json(mismatch_path, boundary_mismatch)")
        terminal = self.source22.index(
            "Attempt 22 captured exact sanitized CDT boundary state"
        )
        recovery = self.source22.index(
            "faces, boundary_segmentation_recovery = restore_exact_boundary_segmentation("
        )
        self.assertLess(capture, write)
        self.assertLess(write, terminal)
        self.assertLess(terminal, recovery)
        for required in (
            "CDT_BOUNDARY_MISMATCH.json",
            "exact_nonadjacent_intersection_report",
            "nonpatch Kira body or face snapshot changed",
            "protected object or native rig changed",
            "owner visual decision is required after paired review",
        ):
            self.assertIn(required, self.source22 if required != "CDT_BOUNDARY_MISMATCH.json" else json.dumps(self.config))
        provider20 = self.provider21.load_attempt20_module()
        provider19 = provider20.load_attempt19_module()
        self.assertEqual(provider19.unsafe_vector_accumulator_locations(self.source22), [])
        self.assertNotIn("bpy.ops.wm.save", self.source22)
        self.assertNotIn("save_as_mainfile", self.source22)
        self.assertNotIn("export_scene", self.source22)

    def test_hard_gates_labels_scope_truth_and_append_only_state(self) -> None:
        unchanged = self.config["unchanged_hard_gates"]
        self.assertEqual(self.merged["attempt_id"], "attempt_22")
        self.assertEqual(
            self.merged["replacement"]["minimum_new_triangle_angle_degrees"], 12.0
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
        labels = self.config["evidence_label_contract"]
        for name in (
            "attempt22_started_schema",
            "attempt22_capture_schema",
            "attempt22_failure_schema",
            "attempt22_failure_status",
            "attempt22_report_schema",
        ):
            self.assertIn(labels[name], self.source22)
        for stale in ("ATTEMPT21", "attempt_21", "attempt21", "Attempt 21"):
            self.assertNotIn(stale, self.source22)
        self.assertEqual(self.module.EXPECTED_CONFIG_SHA256, sha256(CONFIG))
        self.assertFalse((EVIDENCE_ROOT / "attempt_22").exists())
        for name, value in self.config["scope"].items():
            if name in {
                "append_only",
                "private",
                "inactive",
                "unassigned",
                "unpublished",
                "diagnostic_simulation_only",
            }:
                self.assertTrue(value, name)
            else:
                self.assertFalse(value, name)
        truth = self.config["truth"]
        self.assertFalse(truth["exact_live_mismatch_primitive_known"])
        self.assertFalse(truth["attempt22_repair_implemented"])
        self.assertFalse(truth["owner_approval_claimed"])


if __name__ == "__main__":
    unittest.main()
