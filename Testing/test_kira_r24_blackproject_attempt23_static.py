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
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT23_CONFIG.json"
)
WORKER = ROOT / "tools" / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt23.py"
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
    spec = importlib.util.spec_from_file_location("attempt23_static_worker", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Attempt 23 worker specification")
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
    exec(compile(module, "<attempt23-schema-mapping>", "exec"), namespace, namespace)
    return {name: namespace[name] for name in names}


class R24BlackProjectAttempt23StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_json(CONFIG)
        cls.module = load_worker_module()
        cls.provider22 = cls.module.load_attempt22_module()
        cls.source22 = cls.module.materialize_attempt22_source(cls.provider22)
        cls.source23 = cls.module.derive_attempt23_source(cls.source22)
        cls.merged = cls.module.load_attempt23_config(CONFIG)
        cls.functions = extract_functions(
            cls.source23,
            (
                "orient2d",
                "cdt_tolerances",
                "cdt_edge_state",
                "exact_boundary_edges",
                "boundary_source_chain",
                "canonical_json_sha256",
                "diagnostic_edge_row",
                "diagnostic_boundary_chain",
                "normalize_boundary_source_to_output_mapping",
                "resolve_attempt23_diagnostic_path",
                "capture_exact_cdt_boundary_mismatch",
            ),
            {
                "Sequence": Sequence,
                "Mapping": Mapping,
                "Any": Any,
                "Vector": FakeVector,
                "Path": Path,
                "ROOT": ROOT,
                "math": math,
                "json": json,
                "hashlib": hashlib,
                "datetime": datetime,
                "timezone": timezone,
                "deque": deque,
            },
        )

    @staticmethod
    def nonidentity_mismatch() -> tuple[
        list[FakeVector],
        list[list[int]],
        list[list[int]],
        dict[int, int],
        list[FakeVector],
    ]:
        boundary = [
            FakeVector((0.0, 0.0)),
            FakeVector((1.0, 0.25)),
            FakeVector((2.0, 0.0)),
            FakeVector((2.0, 2.0)),
            FakeVector((0.0, 2.0)),
        ]
        coordinates = [
            boundary[3],
            boundary[1],
            FakeVector((1.0, 1.0)),
            boundary[4],
            boundary[0],
            boundary[2],
        ]
        source_to_output = {0: 4, 1: 1, 2: 5, 3: 0, 4: 3}
        originals = [[3], [1], [], [4], [0], [2]]
        faces = [[4, 5, 2], [5, 0, 2], [0, 3, 2], [3, 4, 2]]
        return coordinates, faces, originals, source_to_output, boundary

    def capture_nonidentity(self) -> dict[str, Any]:
        coordinates, faces, originals, source_to_output, boundary = (
            self.nonidentity_mismatch()
        )
        return self.functions["capture_exact_cdt_boundary_mismatch"](
            coordinates,
            faces,
            originals,
            source_to_output,
            len(boundary),
            boundary,
            1.0e-12,
            self.merged["replacement"],
            {"accepted_seed_count": 0},
            {"output_face_count": len(faces)},
        )

    def test_complete_attempt22_package_and_logs_are_exact(self) -> None:
        records = dict(self.config["bindings"])
        records["proposal"] = self.config["proposal"]
        for name, record in records.items():
            path = ROOT / record["path"]
            with self.subTest(name=name):
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, record["bytes"])
                self.assertEqual(sha256(path), record["sha256"])
        preserved = self.config["preserved_attempt22_package"]
        self.assertEqual(len(preserved["binding_names"]), preserved["file_count"])
        self.assertEqual(
            sum(
                self.config["bindings"][name]["bytes"]
                for name in preserved["binding_names"]
            ),
            preserved["total_bytes"],
        )

    def test_attempt22_keyerror_is_exact_and_no_capture_was_written(self) -> None:
        failure = load_json(EVIDENCE_ROOT / "attempt_22" / "FAILURE.json")
        inventory = load_json(EVIDENCE_ROOT / "attempt_22" / "APPEND_INVENTORY.json")
        diagnosis = self.config["diagnosis"]
        self.assertEqual(failure["error_type"], diagnosis["attempt22_error_type"])
        self.assertEqual(failure["error"], diagnosis["attempt22_error"])
        self.assertIn("KeyError: 'output'", failure["traceback"])
        self.assertFalse(inventory["geometry_mutation_reached"])
        self.assertFalse(
            (EVIDENCE_ROOT / "attempt_22" / "CDT_BOUNDARY_MISMATCH.json").exists()
        )
        self.assertFalse(diagnosis["geometry_cause_learned_from_attempt22"])

    def test_real_nonidentity_source_to_output_mapping_is_used_exactly(self) -> None:
        result = self.capture_nonidentity()
        mapping = result["boundary_source_to_output"]
        self.assertEqual(
            [(row["boundary_source_index"], row["output_index"]) for row in mapping],
            [(0, 4), (1, 1), (2, 5), (3, 0), (4, 3)],
        )
        self.assertEqual(mapping[0]["input_xy"], [0.0, 0.0])
        self.assertEqual(mapping[0]["output_xy"], [0.0, 0.0])
        self.assertEqual(mapping[3]["output_xy"], [2.0, 2.0])
        self.assertEqual(result["missing_boundary_edge_count"], 2)
        self.assertEqual(result["extra_open_edge_count"], 1)
        self.assertEqual(
            {tuple(row["output_indices"]) for row in result["missing_boundary_edges"]},
            {(1, 4), (1, 5)},
        )
        extra = result["extra_open_edges"][0]
        self.assertEqual(extra["output_indices"], [4, 5])
        self.assertEqual(extra["boundary_source_indices"], [0, 2])
        self.assertEqual(
            extra["ordered_boundary_chain_diagnostics"][0]["boundary_source_indices"],
            [0, 1, 2],
        )
        self.assertEqual(
            extra["ordered_boundary_chain_diagnostics"][0]["boundary_output_indices"],
            [4, 1, 5],
        )
        self.assertEqual(result["coordinates"][4]["original_input_source_indices"], [0])
        self.assertFalse(result["repair_applied"])

    def test_mapping_validator_rejects_direction_and_cardinality_drift(self) -> None:
        validate = self.functions["normalize_boundary_source_to_output_mapping"]
        expected = {0: 4, 1: 1, 2: 5, 3: 0, 4: 3}
        self.assertEqual(validate(expected, 5, 6), expected)
        inverted = {output: source for source, output in expected.items()}
        with self.assertRaisesRegex(RuntimeError, "exact source keys"):
            validate(inverted, 5, 6)
        with self.assertRaisesRegex(RuntimeError, "exact source keys"):
            validate({0: 4, 1: 1, 2: 5, 3: 0}, 5, 6)
        with self.assertRaisesRegex(RuntimeError, "duplicate outputs"):
            validate({0: 4, 1: 1, 2: 5, 3: 0, 4: 4}, 5, 6)
        with self.assertRaisesRegex(RuntimeError, "escaped coordinates"):
            validate({0: 4, 1: 1, 2: 6, 3: 0, 4: 3}, 5, 6)

    def test_real_replacement_domain_contains_scalar_path_not_output_object(self) -> None:
        replacement = self.merged["replacement"]
        contract = self.config["diagnostic_path_contract"]
        self.assertNotIn("output", replacement)
        self.assertEqual(
            replacement[contract["replacement_key"]],
            contract["project_relative_path"],
        )
        resolved = self.functions["resolve_attempt23_diagnostic_path"](replacement)
        self.assertEqual(resolved, (ROOT / contract["project_relative_path"]).resolve())
        self.assertEqual(resolved.name, "CDT_BOUNDARY_MISMATCH.json")
        self.assertEqual(resolved.parent.name, "attempt_23")

    def test_diagnostic_path_resolver_fails_closed(self) -> None:
        resolve = self.functions["resolve_attempt23_diagnostic_path"]
        key = self.config["diagnostic_path_contract"]["replacement_key"]
        with self.assertRaises(KeyError):
            resolve({})
        with self.assertRaisesRegex(RuntimeError, "project-relative"):
            resolve({key: str((ROOT / "outside.json").resolve())})
        with self.assertRaisesRegex(RuntimeError, "escapes project"):
            resolve({key: "../outside.json"})

    def test_derived_source_repairs_only_schema_and_mapping_before_terminal(self) -> None:
        compile(self.source23, "<attempt23-derived-worker>", "exec")
        normalize = self.source23.index(
            "boundary_output = normalize_boundary_source_to_output_mapping("
        )
        capture = self.source23.index(
            "boundary_mismatch = capture_exact_cdt_boundary_mismatch("
        )
        resolve = self.source23.index(
            "mismatch_path = resolve_attempt23_diagnostic_path(config)"
        )
        write = self.source23.index("atomic_write_json(mismatch_path, boundary_mismatch)")
        terminal = self.source23.index(
            "Attempt 23 captured exact sanitized CDT boundary state"
        )
        recovery = self.source23.index(
            "faces, boundary_segmentation_recovery = restore_exact_boundary_segmentation("
        )
        self.assertLess(normalize, capture)
        self.assertLess(capture, resolve)
        self.assertLess(resolve, write)
        self.assertLess(write, terminal)
        self.assertLess(terminal, recovery)
        broken = (
            'config["output"]["root"]',
            'config["output"]["cdt_boundary_mismatch"]',
        )
        run_cdt_start = self.source23.index("def run_cdt(")
        quality_start = self.source23.index("def quality_refined_cdt(")
        run_cdt_source = self.source23[run_cdt_start:quality_start]
        for value in broken:
            self.assertNotIn(value, run_cdt_source)
        for forbidden in ("bpy.ops.wm.save", "save_as_mainfile", "export_scene"):
            self.assertNotIn(forbidden, self.source23)

    def test_hard_gates_evidence_labels_and_append_only_scope(self) -> None:
        self.assertEqual(self.merged["attempt_id"], "attempt_23")
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
        unchanged = self.config["unchanged_hard_gates"]
        self.assertEqual(unchanged["global_seam_vertex_count"], 34)
        self.assertEqual(unchanged["local_boundary_vertex_count"], 32)
        labels = self.config["evidence_label_contract"]
        for name in (
            "attempt23_started_schema",
            "attempt23_capture_schema",
            "attempt23_failure_schema",
            "attempt23_failure_status",
            "attempt23_report_schema",
        ):
            self.assertIn(labels[name], self.source23)
        for stale in ("ATTEMPT22", "attempt_22", "attempt22", "Attempt 22"):
            self.assertNotIn(stale, self.source23)
        self.assertEqual(self.module.EXPECTED_CONFIG_SHA256, sha256(CONFIG))
        self.assertFalse((EVIDENCE_ROOT / "attempt_23").exists())
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
        self.assertFalse(self.config["truth"]["attempt23_geometry_repair_implemented"])
        self.assertFalse(self.config["truth"]["owner_approval_claimed"])


if __name__ == "__main__":
    unittest.main()
