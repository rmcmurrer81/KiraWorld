"""Static acceptance for R24 local-transition geometric diagnostic attempt_01.

This suite never imports Blender, launches a process, opens a Blend, creates
runtime evidence, or mutates geometry.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from fractions import Fraction
from pathlib import Path
import re
import sys
import unittest


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_geometric_diagnostic_attempt_01_static"
)
CONFIG = PACKAGE / "LOCAL_TRANSITION_GEOMETRIC_DIAGNOSTIC_ATTEMPT01_CONFIG.json"
PROPOSAL = PACKAGE / "LOCAL_TRANSITION_GEOMETRIC_DIAGNOSTIC_ATTEMPT01_PROPOSAL.md"
WRAPPER = PACKAGE / "run_local_transition_geometric_diagnostic_attempt01_once.ps1"
WORKER = ROOT / "tools/blender_diagnose_kira_r24_local_transition_geometric_attempt01.py"
RUNTIME_OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_geometric_diagnostic/attempt_01"
)
DOMAIN = ROOT / (
    "RecoverySprint/continuation_20260807/"
    "r24_blackproject_patch_reconstruction_diagnostic/attempt_02/"
    "BLACKPROJECT_ATTEMPT02_REPAIR_DOMAIN.json"
)
STRICT_TEST = ROOT / "Testing/test_kira_r24_strict_separation_envelope_static.py"
EXPECTED_WORKER_SHA256 = "3790de7faa67b7f3605a3278a5baa756b0584219b2dd022c69e05af3ac10a6e2"
EXPECTED_CONFIG_SHA256 = "87f9fa8b72e6f1abc6c6cf83c1289913252ca015b424cedfb5061b306b113ae9"
EXPECTED_WRAPPER_SHA256 = "376ed6efc967b4d6cd0b41cf7ba802244823295e67314423f17506029ba3601a"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inventory(root: Path) -> tuple[int, int, str]:
    rows = []
    for path in sorted((value for value in root.rglob("*") if value.is_file()), key=lambda value: value.as_posix()):
        rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return len(rows), sum(row["bytes"] for row in rows), hashlib.sha256(encoded).hexdigest()


def dotted_call_name(node: ast.Call) -> str:
    parts = []
    value = node.func
    while isinstance(value, ast.Attribute):
        parts.append(value.attr)
        value = value.value
    if isinstance(value, ast.Name):
        parts.append(value.id)
    return ".".join(reversed(parts))


class LocalTransitionGeometricAttempt01StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.worker = load_module("local_transition_attempt01_static", WORKER)
        cls.strict = load_module("strict_envelope_helpers", STRICT_TEST)
        cls.config = cls.worker.load_config(CONFIG)
        cls.worker.validate_config(cls.config)
        cls.domain = json.loads(DOMAIN.read_text(encoding="utf-8"))
        _, _, cls.faces, cls.vertex_count = cls.strict.parse_genitalia_source_topology(
            ROOT / cls.config["immutable_bindings"]["licensed_source_glb"]["path"]
        )
        cls.by_ring = {row["face_ring_expansion"]: row for row in cls.domain["domains"]}
        cls.d2 = set(cls.by_ring[2]["face_indices"])
        cls.d4 = set(cls.by_ring[4]["face_indices"])
        cls.envelope = cls.d4 | set(cls.config["domains"]["strict_envelope_added_faces"])
        cls.collar = cls.envelope - cls.d2
        cls.summary = cls.worker.selected_topology(cls.faces, cls.envelope)

    def test_01_exact_static_program_hashes(self) -> None:
        self.assertEqual(sha256_file(WORKER), EXPECTED_WORKER_SHA256)
        self.assertEqual(sha256_file(CONFIG), EXPECTED_CONFIG_SHA256)
        self.assertEqual(sha256_file(WRAPPER), EXPECTED_WRAPPER_SHA256)

    def test_02_every_explicit_input_is_exact(self) -> None:
        verified = self.worker.verify_immutable_bindings(self.config)
        self.assertEqual(len(verified), 24)

    def test_03_targeted_protected_inventories_are_exact(self) -> None:
        for expected in self.config["protected_inventories"]:
            actual = inventory(ROOT / expected["root"])
            self.assertEqual(
                actual,
                (
                    expected["file_count"],
                    expected["total_bytes"],
                    expected["compact_inventory_sha256"],
                ),
                expected["root"],
            )

    def test_04_exact_source_topology_and_strict_envelope_reproduce(self) -> None:
        domains = self.config["domains"]
        self.assertEqual(self.vertex_count, 736)
        self.assertEqual(len(self.faces), 1436)
        self.assertEqual(
            self.worker.compact_sha256([list(face) for face in self.faces]),
            self.config["source_mesh"]["stored_winding_face_loops_sha256"],
        )
        self.assertEqual(len(self.envelope), 161)
        self.assertEqual(self.worker.compact_sha256(sorted(self.envelope)), domains["strict_envelope_faces_sha256"])
        self.assertEqual(len(self.collar), 73)
        self.assertEqual(self.worker.compact_sha256(sorted(self.collar)), domains["strict_envelope_collar_faces_sha256"])
        self.assertEqual(len(self.summary["vertices"]), 102)
        self.assertEqual(len(self.summary["edges"]), 262)
        self.assertEqual(len(self.summary["boundary"]), 41)
        self.assertEqual(self.summary["face_components"], 1)
        self.assertEqual(self.summary["euler"], 1)

    def test_05_nine_faces_are_exactly_the_accepted_one_shot_addition(self) -> None:
        additions = self.config["domains"]["strict_envelope_added_faces"]
        self.assertEqual(additions, [3, 368, 369, 372, 373, 826, 864, 1329, 1330])
        self.assertEqual(
            self.worker.compact_sha256(additions),
            "de93c898c67d4c7ef74adfbd9068b04af6746e3f8be33cc403bad0c8a58dd420",
        )
        self.assertEqual(
            [list(self.faces[index]) for index in additions],
            [[3, 5, 0], [246, 247, 90], [246, 90, 241], [248, 240, 91], [248, 91, 249], [507, 508, 516], [528, 527, 534], [91, 713, 249], [90, 247, 714]],
        )

    def test_06_d2_is_strictly_inside_exact_e_star(self) -> None:
        d2_vertices = {vertex for face in self.d2 for vertex in self.faces[face]}
        self.assertFalse(d2_vertices & set(self.summary["cycle"]))
        self.assertEqual(
            self.worker.compact_sha256(self.summary["cycle"]),
            self.config["domains"]["strict_envelope_ordered_boundary_cycle_sha256"],
        )

    def test_07_exterior_ownership_ledger_is_exact(self) -> None:
        full = self.worker.edge_incidence(self.faces)
        outside = sorted(set(range(len(self.faces))) - self.envelope)
        exterior = sorted(
            {
                face
                for edge in self.summary["boundary"]
                for face in full[edge]
                if face not in self.envelope
            }
        )
        domains = self.config["domains"]
        self.assertEqual(len(outside), 1275)
        self.assertEqual(self.worker.compact_sha256(outside), domains["strict_envelope_outside_faces_sha256"])
        self.assertEqual(len(exterior), 41)
        self.assertEqual(self.worker.compact_sha256(exterior), domains["strict_envelope_exterior_adjacent_faces_sha256"])
        self.assertTrue(all(len(full[edge]) == 2 for edge in self.summary["boundary"]))

    def test_08_scalar_field_and_all_192_rational_levels_are_fixed(self) -> None:
        adjacency = {vertex: set() for vertex in self.summary["vertices"]}
        for first, second in self.summary["edges"]:
            adjacency[first].add(second)
            adjacency[second].add(first)
        d2_vertices = {vertex for face in self.d2 for vertex in self.faces[face]}
        boundary = set(self.summary["cycle"])
        din = self.worker.graph_distances(adjacency, d2_vertices)
        dout = self.worker.graph_distances(adjacency, boundary)
        phi = {vertex: Fraction(din[vertex], din[vertex] + dout[vertex]) for vertex in adjacency}
        self.assertTrue(all(phi[vertex] == 0 for vertex in d2_vertices))
        self.assertTrue(all(phi[vertex] == 1 for vertex in boundary))
        levels = [Fraction(k, 193) for k in range(1, 193)]
        self.assertEqual(len(levels), 192)
        self.assertEqual(levels[0], Fraction(1, 193))
        self.assertEqual(levels[-1], Fraction(192, 193))

    def test_09_worker_binds_rational_barycentric_and_chart_computations(self) -> None:
        source = WORKER.read_text(encoding="utf-8")
        for token in (
            "Fraction(k, config[\"candidate_generator\"][\"tau_denominator\"])",
            "canonical_triangle",
            "owner_triangle_vertices",
            "barycentric_reconstruction_maximum_delta_m",
            "binary64_barycentric_sum_maximum_residual",
            "chart_frame(matrix, config)",
            "segment_distance_2d",
            "cut_loop_numeric_guard_minimum_angle_degrees",
            "selection_metrics",
            "for k in range(1, 193)",
        ):
            self.assertIn(token, source)

    def test_10_worker_has_only_read_only_blender_operation(self) -> None:
        tree = ast.parse(WORKER.read_text(encoding="utf-8"))
        bpy_calls = sorted(
            {dotted_call_name(node) for node in ast.walk(tree) if isinstance(node, ast.Call) and dotted_call_name(node).startswith("bpy.ops")}
        )
        self.assertEqual(bpy_calls, ["bpy.ops.wm.open_mainfile"])
        source = WORKER.read_text(encoding="utf-8").lower()
        for forbidden in (
            "save_as_mainfile",
            "bpy.ops.render",
            "bpy.ops.export",
            "bmesh.ops",
            "from_mesh(",
            "to_mesh(",
            ".co =",
        ):
            self.assertNotIn(forbidden, source)

    def test_11_worker_fails_before_any_mutation_and_never_retries(self) -> None:
        scope = self.config["scope"]
        self.assertTrue(scope["open_sealed_source_blend_during_later_audited_run"])
        self.assertTrue(scope["read_mesh_coordinates_during_later_audited_run"])
        self.assertTrue(scope["write_append_only_json_and_logs_during_later_audited_run"])
        self.assertTrue(all(not scope[key] for key in (
            "mesh_mutation_allowed", "datablock_mutation_allowed", "blend_save_allowed",
            "render_allowed", "export_allowed", "runtime_activation_allowed",
            "assignment_allowed", "publication_allowed", "retry_allowed",
        )))
        self.assertFalse(self.config["launch_contract"]["automatic_retry_allowed"])

    def test_12_wrapper_has_one_invocation_and_fixed_log_ownership(self) -> None:
        source = WRAPPER.read_text(encoding="utf-8")
        invocation_lines = [line for line in source.splitlines() if re.match(r"^\s*& \$blender\b", line)]
        self.assertEqual(len(invocation_lines), 1)
        self.assertIn("1> $temporaryStdout 2> $temporaryStderr", invocation_lines[0])
        self.assertIn("[System.IO.File]::Move($temporaryStdout, $stdoutPath)", source)
        self.assertIn("[System.IO.File]::Move($temporaryStderr, $stderrPath)", source)
        self.assertIn("FileMode]::CreateNew", source)
        self.assertNotIn("Remove-Item", source)
        self.assertNotIn("1> $stdoutPath", source)
        self.assertNotIn("2> $stderrPath", source)

    def test_13_final_logs_do_not_conflict_with_worker_preflight(self) -> None:
        launch = self.config["launch_contract"]
        self.assertTrue(launch["wrapper_redirects_only_to_controlled_temporary_logs"])
        self.assertTrue(launch["worker_never_treats_wrapper_temporary_logs_as_static_outputs"])
        self.assertTrue(launch["final_stdout_stderr_created_only_by_atomic_move_after_worker_exit"])
        self.assertTrue(launch["worker_requires_exact_claim_but_not_final_logs"])
        self.assertFalse(launch["temporary_logs_deleted_automatically"])

    def test_14_hard_gates_are_not_weakened(self) -> None:
        hard = self.config["hard_gates"]
        self.assertEqual(hard["cut_loop_numeric_guard_minimum_angle_degrees"], 12.000001)
        self.assertEqual(hard["cut_loop_numeric_guard_maximum_chart_deviation_m"], 0.001099999999)
        self.assertEqual(hard["minimum_future_render_triangle_angle_degrees"], 12.0)
        self.assertEqual(hard["minimum_future_render_triangle_area_m2"], 1e-10)
        self.assertEqual(hard["maximum_future_new_interior_vertices"], 160)
        self.assertEqual(hard["maximum_candidate_records"], 192)
        self.assertEqual(hard["inherited_nonpatch_exact_pairs"], 29)
        self.assertEqual(hard["global_interface_coordinate_delta_m"], 0.0)
        self.assertEqual(hard["global_interface_unique_weld_count"], 34)

    def test_15_truth_is_static_and_does_not_claim_a_body(self) -> None:
        truth = self.config["truth"]
        self.assertTrue(truth["static_package_prepared"])
        for key in (
            "independent_static_audit_passed", "execution_authorized", "wrapper_executed",
            "blender_launched", "source_blend_opened", "candidate_records_created",
            "eligible_candidate_found", "geometry_mutated", "blend_saved", "rendered",
            "runtime_changed", "body_repair_proven", "owner_approval_claimed",
        ):
            self.assertFalse(truth[key], key)

    def test_16_proposal_preserves_scope_and_attempt_identity(self) -> None:
        text = PROPOSAL.read_text(encoding="utf-8").lower()
        for required in (
            "not attempt 48",
            "never another\nexisting-source-star",
            "exactly one record for every",
            "temporary logs",
            "no blender process was launched",
            "execution is not authorized",
            "one read-only\ndiagnostic invocation",
        ):
            self.assertIn(required, text)

    def test_17_runtime_output_is_absent_and_static_package_has_no_runtime_artifact(self) -> None:
        self.assertFalse(RUNTIME_OUTPUT.exists())
        allowed = {
            "LOCAL_TRANSITION_GEOMETRIC_DIAGNOSTIC_ATTEMPT01_CONFIG.json",
            "LOCAL_TRANSITION_GEOMETRIC_DIAGNOSTIC_ATTEMPT01_PROPOSAL.md",
            "run_local_transition_geometric_diagnostic_attempt01_once.ps1",
            "CHECKPOINT.md",
            "INDEPENDENT_STATIC_AUDIT.md",
        }
        self.assertTrue({path.name for path in PACKAGE.iterdir()} <= allowed)
        self.assertNotIn("bpy", sys.modules)
        self.assertNotIn("bmesh", sys.modules)

    def test_18_config_worker_wrapper_and_test_are_parseable(self) -> None:
        self.assertEqual(json.loads(CONFIG.read_text(encoding="utf-8")), self.config)
        ast.parse(WORKER.read_text(encoding="utf-8"))
        self.assertIn("Set-StrictMode -Version Latest", WRAPPER.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
