from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTIC = PROJECT_ROOT / "tools/blender_diagnose_kira_r20_preflight_contract.py"
PROBE = PROJECT_ROOT / "tools/blender_probe_blackproject_adult_patch_interface.py"
INTERFACE = PROJECT_ROOT / (
    "Avatar/private_owner_review/kira_temporary_functional_body_20260730/"
    "source_inspection/blackproject_adult_patch_interface.json"
)
ATTEMPT03 = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring/"
    "preflight_attempt_03/PREFLIGHT_FAILURE.json"
)
CONFIG = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/AUTHORING_CONFIG.json"
)
WORKER = PROJECT_ROOT / "tools/blender_author_kira_r20_pelvis_only.py"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def call_chain(node: ast.AST) -> str:
    parts = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


class R20WholePreflightDiagnosticStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = DIAGNOSTIC.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.calls = [node for node in ast.walk(cls.tree) if isinstance(node, ast.Call)]

    def test_exact_failed_attempt_and_inputs_are_bound(self) -> None:
        self.assertEqual(
            sha256_file(ATTEMPT03),
            "3afa5894348d862974e3829c3c4dad5fa0d1aed92bf7c7c503d058d75c0f50ab",
        )
        failure = json.loads(ATTEMPT03.read_text(encoding="utf-8"))
        self.assertEqual(failure["status"], "FAILED_CLOSED")
        self.assertEqual(
            failure["error"],
            "R19 seam no longer matches exact licensed interface: 0.12830215951281168 m",
        )
        for path in (ATTEMPT03, CONFIG, WORKER, INTERFACE, PROBE):
            self.assertIn(sha256_file(path), self.source)

    def test_probe_field_is_bfs_component_order_not_cycle_walk(self) -> None:
        source = PROBE.read_text(encoding="utf-8")
        self.assertIn("queue = deque([start])", source)
        self.assertIn("component.append(current)", source)
        self.assertIn("for neighbor in adjacency[current]:", source)
        self.assertIn('"ordered_boundary_cycles_world_m"', source)
        boundary_function = next(
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef) and node.name == "boundary_loops"
        )
        calls = [call_chain(node.func) for node in ast.walk(boundary_function) if isinstance(node, ast.Call)]
        self.assertIn("queue.popleft", calls)
        self.assertNotIn("walk_cycle", calls)

    def test_interface_evidence_retains_exact_coordinate_set_authority(self) -> None:
        evidence = json.loads(INTERFACE.read_text(encoding="utf-8"))
        bfs_rows = evidence["adult_patch"]["ordered_boundary_cycles_world_m"][0]
        records = evidence["adult_boundary_to_base_vertices"]["records"]
        self.assertEqual(len(bfs_rows), 34)
        self.assertEqual(len(records), 34)
        self.assertEqual(evidence["adult_boundary_to_base_vertices"]["minimum_m"], 0.0)
        self.assertEqual(evidence["adult_boundary_to_base_vertices"]["maximum_m"], 0.0)
        self.assertTrue(
            all(math.dist(record["adult_world"], record["base_world"]) == 0.0 for record in records)
        )
        nearest = [
            min(math.dist(point, record["base_world"]) for record in records)
            for point in bfs_rows
        ]
        self.assertLessEqual(max(nearest), 1.0e-8)

    def test_diagnostic_has_no_blend_save_or_body_mutation_operator(self) -> None:
        calls = {call_chain(node.func) for node in self.calls}
        prohibited = {
            "bpy.ops.wm.save_as_mainfile",
            "bpy.ops.wm.save_mainfile",
            "bpy.ops.object.delete",
            "bpy.ops.object.join",
            "bpy.ops.mesh.delete",
            "bpy.ops.object.modifier_apply",
        }
        self.assertTrue(prohibited.isdisjoint(calls), prohibited.intersection(calls))
        self.assertNotIn("keyframe_insert", calls)
        self.assertNotIn("bmesh", self.source)
        prohibited_worker_calls = {
            "worker._author_candidate",
            "worker._save_candidate_once",
            "worker.run_author_mode",
            "worker.run_pose_suite",
            "worker.run_verify_render_mode",
            "worker._render_review_package",
        }
        self.assertTrue(
            prohibited_worker_calls.isdisjoint(calls),
            prohibited_worker_calls.intersection(calls),
        )

    def test_one_append_only_output_and_all_remaining_gates_are_collected(self) -> None:
        self.assertIn(
            "kira_r20_preflight_contract_reconciliation/diagnostic_attempt_01",
            self.source,
        )
        for marker in (
            "historical_attempt03_sequential_interface_gate",
            "corrected_interface_set_and_mask_contract",
            "preserved_primary_snapshot",
            "preserved_primary_counts",
            "all_exterior_ring_and_normal_vertices",
            "production_exterior_ring_function",
            "all_seam_uv_vertices",
            "production_seam_uv_function",
            "all_seam_weight_vertices",
            "production_seam_weight_function",
            "pure_patch_contract",
            "global_frozen_state_digests",
            "unexpected_failed_gates",
        ):
            self.assertIn(marker, self.source)

    def test_coordinate_frame_and_pairing_are_explicit(self) -> None:
        for marker in (
            "body.matrix_world",
            "scene_unit_settings",
            "unique_bijective_nearest_assignment",
            "full-precision base_world coordinates",
            "actual sealed R19 selected/unselected edge cycle",
            "BFS component visitation",
            "local_coordinate_set_vs_world_source",
            "world_coordinate_set_vs_full_precision_base_records",
        ):
            self.assertIn(marker, self.source)


if __name__ == "__main__":
    unittest.main()
