"""Light static acceptance for the R24 nonuniform edge feasibility package.

No test imports Blender, opens a Blend, runs the source-coordinate solver,
creates runtime/cache output, or mutates geometry.
"""

from __future__ import annotations

import ast
import copy
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import unittest


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_nonuniform_source_edge_feasibility_01_static"
)
CONFIG = PACKAGE / "NONUNIFORM_SOURCE_EDGE_FEASIBILITY01_CONFIG.json"
PROPOSAL = PACKAGE / "NONUNIFORM_SOURCE_EDGE_FEASIBILITY01_PROPOSAL.md"
WRAPPER = PACKAGE / "run_nonuniform_source_edge_feasibility01_once.ps1"
WORKER = ROOT / "tools/blender_diagnose_kira_r24_nonuniform_source_edge_feasibility01.py"
AUDIT_REQUEST = PACKAGE / "INDEPENDENT_STATIC_AUDIT_REQUEST.md"
RUNTIME_OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_nonuniform_source_edge_feasibility/nonuniform_feasibility_01"
)
RUNTIME_CACHE = ROOT / (
    "RecoverySprint/runtime_cache/"
    "kira_r24_nonuniform_source_edge_feasibility/nonuniform_feasibility_01"
)
STRICT_TEST = ROOT / "Testing/test_kira_r24_strict_separation_envelope_static.py"
EXPECTED_WORKER_SHA256 = "0a90055b4da95ac46ad1d65447fec2dae91cb365cb0828ebbaeb50c91417a4bd"
EXPECTED_CONFIG_SHA256 = "99ee7871446dce9f924159c434ecbccf890f08adebdaf0b70bbeb171e83fc0e2"
EXPECTED_WRAPPER_SHA256 = "172e8dbffeef3708ad367bcda6754882667830004719312b1cc1cc46472dd768"


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


def dotted_call_name(node: ast.Call) -> str:
    parts = []
    value = node.func
    while isinstance(value, ast.Attribute):
        parts.append(value.attr)
        value = value.value
    if isinstance(value, ast.Name):
        parts.append(value.id)
    return ".".join(reversed(parts))


class NonuniformSourceEdgeFeasibility01StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.worker = load_module("r24_nonuniform_static", WORKER)
        cls.strict = load_module("r24_nonuniform_strict_helpers", STRICT_TEST)
        cls.config = cls.worker.load_config(CONFIG)
        cls.base = cls.worker.validate_config(cls.config)
        cls.runtime_config = json.loads(json.dumps(cls.config))
        cls.runtime_config["chart"] = cls.base["chart"]
        cls.runtime_config["domains"] = cls.base["domains"]
        _, _, cls.faces, cls.vertex_count = cls.strict.parse_genitalia_source_topology(
            ROOT / cls.base["immutable_bindings"]["licensed_source_glb"]["path"]
        )
        domain = json.loads(
            (ROOT / cls.base["immutable_bindings"]["repair_domains"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        by_ring = {row["face_ring_expansion"]: row for row in domain["domains"]}
        d2 = set(by_ring[2]["face_indices"])
        envelope = set(by_ring[4]["face_indices"]) | set(
            cls.base["domains"]["strict_envelope_added_faces"]
        )
        cls.collar = envelope - d2
        diagnostic = json.loads(
            (
                ROOT
                / cls.config["immutable_bindings"]["attempt01_diagnostic"]["path"]
            ).read_text(encoding="utf-8")
        )
        cls.seed = cls.worker.derive_topology_seed(
            cls.faces, cls.collar, diagnostic, cls.config
        )

    def test_01_exact_program_hashes(self) -> None:
        self.assertEqual(sha256_file(WORKER), EXPECTED_WORKER_SHA256)
        self.assertEqual(sha256_file(CONFIG), EXPECTED_CONFIG_SHA256)
        self.assertEqual(sha256_file(WRAPPER), EXPECTED_WRAPPER_SHA256)

    def test_02_distinct_terminal_lane_identity(self) -> None:
        self.assertEqual(self.config["attempt_id"], "nonuniform_feasibility_01")
        self.assertNotEqual(self.config["attempt_id"], "attempt_01")
        self.assertEqual(
            self.config["lane"], "LOCAL_TRANSITION_NONUNIFORM_SOURCE_EDGE_FEASIBILITY"
        )
        self.assertTrue(self.config["uniform_attempt_consumed"])
        self.assertTrue(self.config["uniform_level_family_terminal"])
        self.assertTrue(self.config["source_star_lane_terminal"])

    def test_03_lane_immutable_bindings_are_exact(self) -> None:
        for name, binding in self.config["immutable_bindings"].items():
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), name)
            self.assertEqual(path.stat().st_size, binding["bytes"], name)
            self.assertEqual(sha256_file(path), binding["sha256"], name)

    def test_04_inherited_sections_and_thresholds_are_byte_semantic_exact(self) -> None:
        for section, expected in self.config["inherited_section_sha256"].items():
            self.assertEqual(self.worker.compact_sha256(self.base[section]), expected)
        self.assertEqual(self.config["chart"], self.base["chart"])
        self.assertEqual(self.config["hard_gates"], self.base["hard_gates"])
        self.assertEqual(
            self.config["hard_gates"]["cut_loop_numeric_guard_minimum_angle_degrees"],
            12.000001,
        )
        self.assertEqual(
            self.config["hard_gates"]["cut_loop_numeric_guard_maximum_chart_deviation_m"],
            0.001099999999,
        )

    def test_05_fixed_k1_edge_triangle_seed_reproduces_exactly(self) -> None:
        self.assertEqual(self.vertex_count, 736)
        self.assertEqual(len(self.faces), 1436)
        self.assertEqual(len(self.seed["points"]), 70)
        self.assertEqual(len(self.seed["segments"]), 70)
        self.assertEqual(
            self.worker.compact_sha256(self.seed),
            "fcda32fa49dcabdb60ae0f63c690047ce65ec30665b3b1243da53495ba4007dc",
        )
        self.assertEqual(
            [point["index"] for point in self.seed["points"]], list(range(70))
        )
        self.assertTrue(
            all(
                len(point["incident_collar_faces"]) == 2
                and set(point["incident_collar_faces"]) <= self.collar
                for point in self.seed["points"]
            )
        )

    def test_06_exact_owner_and_actual_other_triangle_reconstruction(self) -> None:
        coordinates = (
            (0.0, 0.0, 0.0),
            (2.0, 0.0, 0.0),
            (0.0, 3.0, 0.0),
            (0.0, 0.0, 5.0),
        )
        t = Fraction(3, 7)
        owner = (0, 1, 2)
        other = (3, 1, 0)
        owner_weights = self.worker.exact_edge_weights(owner, 0, 1, t)
        other_weights = self.worker.exact_edge_weights(other, 0, 1, t)
        direct = (6.0 / 7.0, 0.0, 0.0)
        self.assertEqual(other_weights[0], 0)
        self.assertEqual(sum(other_weights, Fraction(0)), 1)
        self.assertEqual(
            self.worker.reconstruct_triangle(owner, owner_weights, coordinates), direct
        )
        self.assertEqual(
            self.worker.reconstruct_triangle(other, other_weights, coordinates), direct
        )

    def test_07_dyadic_solver_is_open_finite_and_deterministic(self) -> None:
        denominator = self.config["solver"]["edge_parameter_denominator"]
        first = self.worker.nearest_dyadic_parameter(
            Fraction(1, 3), Fraction(0), Fraction(1), Fraction(1, 193), denominator
        )
        second = self.worker.nearest_dyadic_parameter(
            Fraction(1, 3), Fraction(0), Fraction(1), Fraction(1, 193), denominator
        )
        self.assertEqual(first, second)
        self.assertGreater(first, 0)
        self.assertLess(first, 1)
        self.assertEqual(first.denominator & (first.denominator - 1), 0)
        self.assertEqual(self.config["solver"]["plane_sample_intervals"], 190)
        self.assertEqual(self.config["solver"]["maximum_generated_records"], 192)
        self.assertLessEqual(
            self.config["solver"]["maximum_generated_records"],
            self.config["hard_gates"]["maximum_candidate_records"],
        )
        self.assertFalse(self.config["solver"]["randomness_allowed"])
        self.assertFalse(self.config["solver"]["adaptive_retry_allowed"])
        self.assertFalse(self.config["solver"]["global_continuous_minimax_claimed"])
        self.assertFalse(
            self.config["solver"]["global_gate_constrained_optimality_claimed"]
        )

    def _synthetic_direct_case(self):
        coordinates = [(0.0, 0.0, -0.01)]
        for index in range(70):
            angle = 2.0 * math.pi * index / 70.0
            coordinates.append((2.0 * math.cos(angle), 2.0 * math.sin(angle), 0.01))
        faces = [
            (0, index + 1, ((index + 1) % 70) + 1) for index in range(70)
        ]
        points = []
        full_incidence = {}
        for index in range(70):
            first, second = 0, index + 1
            incident = sorted(((index - 1) % 70, index))
            owner_face, other_face = incident
            full_incidence[(first, second)] = incident
            points.append(
                {
                    "index": index,
                    "edge": [first, second],
                    "k1_t": [1, 2],
                    "incident_collar_faces": incident,
                    "owner_face": owner_face,
                    "owner_triangle": list(
                        self.worker._BASE.canonical_triangle(faces[owner_face])
                    ),
                    "other_face": other_face,
                    "other_triangle_stored_order": list(faces[other_face]),
                }
            )
        segments = [
            {
                "source_face_index": index,
                "point_indices": [index, (index + 1) % 70],
            }
            for index in range(70)
        ]
        seed = {"points": points, "segments": segments}
        context = {
            "full_incidence": full_incidence,
            "collar": set(range(70)),
            "exterior_adjacent": set(),
            "d2_vertices": {99998},
            "boundary_vertices": {99999},
            "minimum_seam_rings": 4,
        }
        frame = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), 1.0)
        return seed, faces, coordinates, frame, context

    def test_08_independent_direct_evaluator_passes_and_fails_closed(self) -> None:
        seed, faces, coordinates, frame, context = self._synthetic_direct_case()
        passing = self.worker.independent_direct_evaluate(
            [Fraction(1, 2)] * 70,
            seed,
            faces,
            coordinates,
            frame,
            context,
            self.runtime_config,
        )
        self.assertTrue(passing["passes_all_inherited_premutation_gates"])
        failing_values = [Fraction(1, 2)] * 70
        failing_values[0] = Fraction(3, 4)
        failing = self.worker.independent_direct_evaluate(
            failing_values,
            seed,
            faces,
            coordinates,
            frame,
            context,
            self.runtime_config,
        )
        self.assertFalse(failing["passes_all_inherited_premutation_gates"])
        self.assertIn("chart_deviation_gate", failing["failure_names"])

    def test_08a_bounded_solver_terminates_on_synthetic_geometry(self) -> None:
        seed, faces, coordinates, frame, context = self._synthetic_direct_case()
        summary = self.worker.solve_bounded_nonuniform_family(
            seed,
            faces,
            coordinates,
            frame,
            context,
            self.runtime_config,
        )
        self.assertTrue(summary["finite_termination_reached"])
        self.assertLessEqual(summary["generated_record_count"], 192)
        self.assertGreater(summary["eligible_record_count"], 0)
        self.assertTrue(summary["all_generated_records_directly_evaluated"])
        self.assertEqual(len(summary["selection_domain_sha256"]), 64)
        self.assertTrue(
            summary["proposed_record"]["passes_all_inherited_premutation_gates"]
        )
        self.assertFalse(summary["proposed_record_rejected"])

    def test_08b_direct_evaluator_rejects_each_tampered_gate_class(self) -> None:
        seed, faces, coordinates, frame, context = self._synthetic_direct_case()

        endpoint_values = [Fraction(1, 2)] * 70
        endpoint_values[0] = Fraction(0)
        endpoint = self.worker.independent_direct_evaluate(
            endpoint_values, seed, faces, coordinates, frame, context, self.runtime_config
        )
        self.assertIn("open_edge_parameter", endpoint["failure_names"])

        swapped_seed = copy.deepcopy(seed)
        swapped_seed["points"][0]["owner_face"], swapped_seed["points"][0]["other_face"] = (
            swapped_seed["points"][0]["other_face"],
            swapped_seed["points"][0]["owner_face"],
        )
        swapped = self.worker.independent_direct_evaluate(
            [Fraction(1, 2)] * 70,
            swapped_seed,
            faces,
            coordinates,
            frame,
            context,
            self.runtime_config,
        )
        self.assertIn("fixed_edge_triangle_topology", swapped["failure_names"])
        self.assertFalse(swapped["actual_opposite_triangle_vertex_order_used"])

        broken_seed = copy.deepcopy(seed)
        broken_seed["segments"][0]["point_indices"] = [0, 2]
        broken = self.worker.independent_direct_evaluate(
            [Fraction(1, 2)] * 70,
            broken_seed,
            faces,
            coordinates,
            frame,
            context,
            self.runtime_config,
        )
        self.assertIn("fixed_edge_triangle_topology", broken["failure_names"])

        seam_context = copy.deepcopy(context)
        seam_context["minimum_seam_rings"] = 3
        seam = self.worker.independent_direct_evaluate(
            [Fraction(1, 2)] * 70,
            seed,
            faces,
            coordinates,
            frame,
            seam_context,
            self.runtime_config,
        )
        self.assertIn("global_seam_disjointness", seam["failure_names"])

        exterior_context = copy.deepcopy(context)
        exterior_context["exterior_adjacent"] = {0}
        exterior = self.worker.independent_direct_evaluate(
            [Fraction(1, 2)] * 70,
            seed,
            faces,
            coordinates,
            frame,
            exterior_context,
            self.runtime_config,
        )
        self.assertIn("exterior_adjacent_face_preservation", exterior["failure_names"])

        crossing_coordinates = list(coordinates)
        crossing_coordinates[1], crossing_coordinates[20] = (
            crossing_coordinates[20],
            crossing_coordinates[1],
        )
        crossing = self.worker.independent_direct_evaluate(
            [Fraction(1, 2)] * 70,
            seed,
            faces,
            crossing_coordinates,
            frame,
            context,
            self.runtime_config,
        )
        self.assertIn("projected_simplicity_one_disk", crossing["failure_names"])

        acute_coordinates = list(coordinates)
        acute_coordinates[1] = (20.0, 0.0, 0.01)
        acute = self.worker.independent_direct_evaluate(
            [Fraction(1, 2)] * 70,
            seed,
            faces,
            acute_coordinates,
            frame,
            context,
            self.runtime_config,
        )
        self.assertIn("boundary_angle_gate", acute["failure_names"])

    def test_09_worker_has_only_read_only_blender_operation(self) -> None:
        source = WORKER.read_text(encoding="utf-8")
        tree = ast.parse(source)
        bpy_calls = sorted(
            {
                dotted_call_name(node)
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and dotted_call_name(node).startswith("bpy.ops")
            }
        )
        self.assertEqual(bpy_calls, ["bpy.ops.wm.open_mainfile"])
        for forbidden in (
            "save_as_mainfile",
            "bpy.ops.render",
            "bpy.ops.export",
            "bmesh.ops",
            "from_mesh(",
            "to_mesh(",
            ".co =",
        ):
            self.assertNotIn(forbidden, source.lower())

    def test_10_wrapper_guard_precedes_every_mutating_or_process_action(self) -> None:
        source = WRAPPER.read_text(encoding="utf-8")
        guard_index = source.index("if ($InvocationGuard -cne")
        for token in (
            "Get-Process -Name blender",
            "[System.IO.Directory]::CreateDirectory($cacheRoot)",
            "Write-NewJson $claimPath",
            "& $blender --background",
        ):
            self.assertGreater(source.index(token), guard_index, token)
        invocation_lines = [
            line
            for line in source.splitlines()
            if re.match(r"^\s*& \$blender\b", line)
        ]
        self.assertEqual(len(invocation_lines), 1)
        self.assertIn("1> $temporaryStdout 2> $temporaryStderr", invocation_lines[0])
        self.assertIn("'INVOKE_AUDITED_NONUNIFORM_FEASIBILITY_01_ONCE'", source)
        self.assertIn(EXPECTED_CONFIG_SHA256, source)
        self.assertIn(EXPECTED_WORKER_SHA256, source)
        self.assertIn("function Get-PostProtectionCapture", source)
        self.assertIn("canonical inventory helper was not exact; execution suppressed", source)
        self.assertNotIn("Remove-Item", source)
        self.assertIn("FileMode]::CreateNew", source)
        self.assertTrue(
            self.config["launch_contract"][
                "wrapper_attempts_completion_and_integrity_after_every_invocation"
            ]
        )
        self.assertFalse(
            self.config["launch_contract"][
                "wrapper_always_records_exit_and_pre_post_integrity"
            ]
        )

    def test_11_missing_guard_fails_before_output_or_cache(self) -> None:
        self.assertFalse(RUNTIME_OUTPUT.exists())
        self.assertFalse(RUNTIME_CACHE.exists())
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(WRAPPER),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Invocation guard rejected", completed.stderr)
        self.assertFalse(RUNTIME_OUTPUT.exists())
        self.assertFalse(RUNTIME_CACHE.exists())

    def test_12_output_is_bounded_absent_and_noncolliding(self) -> None:
        self.assertFalse(RUNTIME_OUTPUT.exists())
        self.assertFalse(RUNTIME_CACHE.exists())
        self.assertNotEqual(
            self.config["output_contract"]["root"],
            self.base["output_contract"]["root"],
        )
        self.assertNotEqual(
            self.config["output_contract"]["runtime_cache_root"],
            self.base["output_contract"]["runtime_cache_root"],
        )
        self.assertTrue(self.config["output_contract"]["append_only"])

    def test_13_scope_and_truth_make_no_execution_or_body_claim(self) -> None:
        forbidden_scope = (
            "mesh_mutation_allowed",
            "datablock_mutation_allowed",
            "blend_save_allowed",
            "render_allowed",
            "export_allowed",
            "runtime_activation_allowed",
            "assignment_allowed",
            "publication_allowed",
            "retry_allowed",
        )
        self.assertTrue(all(not self.config["scope"][key] for key in forbidden_scope))
        for key in (
            "independent_static_audit_passed",
            "execution_authorized",
            "wrapper_executed",
            "blender_launched",
            "source_blend_opened",
            "solver_executed_on_source_coordinates",
            "proposed_record_created",
            "eligible_record_found",
            "geometry_mutated",
            "blend_saved",
            "rendered",
            "runtime_changed",
            "body_repair_proven",
            "owner_approval_claimed",
        ):
            self.assertFalse(self.config["truth"][key], key)

    def test_14_static_package_boundary_and_audit_request(self) -> None:
        allowed = {
            CONFIG.name,
            PROPOSAL.name,
            WRAPPER.name,
            "CHECKPOINT.md",
            AUDIT_REQUEST.name,
        }
        self.assertTrue({path.name for path in PACKAGE.iterdir()} <= allowed)
        self.assertTrue(AUDIT_REQUEST.is_file())
        self.assertNotIn("bpy", sys.modules)
        self.assertNotIn("bmesh", sys.modules)


if __name__ == "__main__":
    unittest.main()
