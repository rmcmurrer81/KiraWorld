from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools/blender_diagnose_kira_r24_edge_complete_carrier_domain_topology_feasibility01.py"
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_edge_complete_carrier_domain_topology_feasibility_01_static/"
    "EDGE_COMPLETE_CARRIER_DOMAIN_TOPOLOGY_FEASIBILITY01_CONFIG.json"
)
WRAPPER = CONFIG.with_name("run_edge_complete_carrier_domain_topology_feasibility01_once.ps1")
PROPOSAL = CONFIG.with_name("EDGE_COMPLETE_CARRIER_DOMAIN_TOPOLOGY_FEASIBILITY01_PROPOSAL.md")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_worker():
    spec = importlib.util.spec_from_file_location("r24_edge_complete_static_test", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not construct worker import")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EdgeCompleteCarrierDomainStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.module = load_worker()

    def test_01_safe_import_and_parent_config_validation(self) -> None:
        self.assertNotIn("bpy", sys.modules)
        self.assertNotIn("bmesh", sys.modules)
        parent, base = self.module.validate_config(self.config)
        self.assertEqual(base["source_mesh"]["vertex_count"], 736)
        self.assertEqual(base["source_mesh"]["face_count"], 1436)
        self.assertEqual(base["domains"]["d2_face_count"], 88)
        self.assertEqual(base["domains"]["strict_envelope_face_count"], 161)
        self.assertEqual(base["domains"]["strict_envelope_collar_face_count"], 73)
        self.assertEqual(base["domains"]["strict_envelope_exterior_adjacent_face_count"], 41)
        self.assertEqual(parent["topology_seed"]["point_count"], 70)

    def test_02_direct_binding_spine_is_exact(self) -> None:
        self.assertEqual(len(self.config["immutable_bindings"]), 11)
        for name, binding in self.config["immutable_bindings"].items():
            with self.subTest(name=name):
                path = ROOT / binding["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, binding["bytes"])
                self.assertEqual(sha256(path), binding["sha256"])

    def test_03_consumed_actual_plane_result_is_terminal_and_exact(self) -> None:
        report = self.module.consumed_actual_plane_result(self.config)
        solver = report["solver_summary"]
        self.assertEqual(report["status"], "NO_ELIGIBLE_ACTUAL_PLANE_CONTOUR_FAIL_CLOSED")
        self.assertEqual(solver["collar_face_count"], 73)
        self.assertEqual(len(solver["collar_face_visit_ledger"]), 73)
        self.assertEqual(solver["actual_segment_count"], 3)
        self.assertEqual(solver["actual_point_count"], 6)
        self.assertEqual(solver["component_count"], 2)
        self.assertEqual(solver["eligible_component_count"], 0)
        self.assertEqual(
            solver["global_failure_names"],
            [
                "complete_two_collar_face_edge_ownership",
                "single_component_d2_envelope_separation",
            ],
        )
        self.assertIsNone(solver["selected_eligible_component"])

    def test_04_recursive_parent_and_runtime_integrity_reverify(self) -> None:
        state = self.module.verify_immutable_inputs(self.config)
        self.assertEqual(len(state["lane_bindings"]), 11)
        self.assertEqual(len(state["parent_lane_bindings"]), 16)
        self.assertEqual(len(state["inherited_bindings"]), 24)
        self.assertEqual(len(state["protected_inventories"]), 4)
        runtime = state["consumed_parent_runtime_integrity"]
        self.assertEqual(len(runtime["recursive_files"]), 16)
        self.assertEqual(len(runtime["protected_inventories"]), 4)
        self.assertEqual(len(runtime["output_files"]), 5)

    def test_05_contract_is_exactly_five_nested_bounded_domains(self) -> None:
        contract = self.config["carrier_domain_contract"]
        self.assertEqual(contract["candidate_dual_ring_expansions"], [0, 1, 2, 3, 4])
        self.assertEqual(contract["candidate_count"], 5)
        self.assertEqual(contract["maximum_dual_ring_expansion"], 4)
        self.assertEqual(contract["base_collar_face_count"], 73)
        self.assertEqual(contract["minimum_vertex_source_graph_rings_from_global_interface"], 4)
        for key in (
            "endpoint_clamping_allowed",
            "alternate_plane_allowed",
            "randomness_allowed",
            "adaptive_retry_allowed",
            "free_world_space_points_allowed",
            "mutation_package_allowed",
        ):
            self.assertFalse(contract[key], key)
        self.assertEqual(
            self.config["hard_gates"]["cut_loop_numeric_guard_minimum_angle_degrees"],
            12.000001,
        )
        self.assertEqual(
            self.config["hard_gates"]["cut_loop_numeric_guard_maximum_chart_deviation_m"],
            0.001099999999,
        )

    def test_06_boundary_cycle_extraction_recognizes_one_annulus(self) -> None:
        faces = [
            (0, 1, 5), (0, 5, 4),
            (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6),
            (3, 0, 4), (3, 4, 7),
        ]
        cycles, boundary, valid = self.module.boundary_cycles(faces, set(range(8)))
        self.assertTrue(valid)
        self.assertEqual(len(cycles), 2)
        self.assertEqual(sorted(len(cycle) for cycle in cycles), [4, 4])
        self.assertEqual(len(boundary), 8)
        topology = self.module._BASE.selected_topology(faces, set(range(8)))
        self.assertEqual(topology["face_components"], 1)
        self.assertEqual(topology["euler"], 0)

    def test_07_dual_ring_expansion_is_deterministic_nested_and_excludes_d2(self) -> None:
        faces = [(0, 1, 2), (1, 3, 2), (3, 4, 2), (3, 5, 4)]
        context = {
            "d2": {0},
            "collar": {1},
            "full_incidence": self.module._BASE.edge_incidence(faces),
            "domain": {"global_interface": {"boundary_vertex_indices": [0]}},
        }
        config = copy.deepcopy(self.config)
        contract = config["carrier_domain_contract"]
        contract["candidate_dual_ring_expansions"] = [0, 1, 2]
        contract["maximum_dual_ring_expansion"] = 2
        contract["minimum_vertex_source_graph_rings_from_global_interface"] = 0
        rows = self.module.bounded_candidate_domains(faces, context, config)
        ledgers = [row["faces"] for row in rows]
        self.assertEqual(ledgers, [{1}, {1, 2}, {1, 2, 3}])
        self.assertTrue(ledgers[0] <= ledgers[1] <= ledgers[2])
        self.assertTrue(all(0 not in row for row in ledgers))

    def test_08_crossing_edges_require_exact_two_candidate_owners(self) -> None:
        faces = [(0, 1, 2), (1, 0, 3)]
        incidence = self.module._BASE.edge_incidence(faces)
        context = {
            "envelope_vertices": {0, 1, 2, 3},
            "collar": {0},
            "full_incidence": incidence,
        }
        _, _, failures, _ = self.module._PARENT.build_actual_segments(
            faces,
            {0: self.module.Fraction(0), 1: self.module.Fraction(2), 2: self.module.Fraction(0), 3: self.module.Fraction(0)},
            self.module.Fraction(1),
            context,
        )
        self.assertIn("complete_two_collar_face_edge_ownership", failures)
        context["collar"] = {0, 1}
        points, segments, failures, _ = self.module._PARENT.build_actual_segments(
            faces,
            {0: self.module.Fraction(0), 1: self.module.Fraction(2), 2: self.module.Fraction(0), 3: self.module.Fraction(0)},
            self.module.Fraction(1),
            context,
        )
        self.assertEqual(len(points), 1)
        self.assertEqual(len(segments), 0)
        shared = next(iter(points.values()))
        self.assertEqual(shared["edge"], [0, 1])
        self.assertEqual(shared["incident_source_faces"], [0, 1])
        self.assertIn("complete_two_collar_face_edge_ownership", failures)

    def test_09_component_extraction_accepts_only_a_closed_degree_two_cycle(self) -> None:
        a, b, c, d = (0, 1, 1, 2), (1, 2, 1, 2), (2, 3, 1, 2), (3, 4, 1, 2)

        def segment(first, second):
            return {"source_face_index": 0, "point_keys": [list(first), list(second)]}

        cycle = self.module._PARENT.extract_components(
            [segment(a, b), segment(b, c), segment(c, a)]
        )
        self.assertEqual(len(cycle), 1)
        self.assertTrue(cycle[0]["closed_degree_two_cycle"])
        open_chain = self.module._PARENT.extract_components([segment(a, b), segment(b, c)])
        self.assertFalse(open_chain[0]["closed_degree_two_cycle"])
        branch = self.module._PARENT.extract_components(
            [segment(a, b), segment(b, c), segment(b, d)]
        )
        self.assertFalse(branch[0]["closed_degree_two_cycle"])

    def _outer_boundary_case(self, outer_coordinates) -> bool:
        contour = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
        coordinates = []
        points = {}
        ordered = []
        for index, (x_value, y_value) in enumerate(contour):
            first = len(coordinates)
            coordinates.extend(
                [
                    (x_value - 0.5, y_value, 0.0),
                    (x_value + 0.5, y_value, 0.0),
                ]
            )
            key = (first, first + 1, 1, 2)
            ordered.append(key)
            points[key] = {"edge": [first, first + 1], "t": [1, 2]}
        outer = []
        for point in outer_coordinates:
            outer.append(len(coordinates))
            coordinates.append((float(point[0]), float(point[1]), 0.0))
        return self.module.outer_boundary_outside_component(
            {"ordered_loop": [list(key) for key in ordered]},
            points,
            coordinates,
            (
                (1.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
                (0.0, 0.0, 1.0),
                1.0,
            ),
            outer,
            1e-12,
        )

    def test_10_outer_boundary_vertex_on_contour_edge_fails_closed(self) -> None:
        self.assertFalse(
            self._outer_boundary_case(
                [(1.0, 0.0), (3.0, -1.0), (3.0, 3.0), (-1.0, 3.0), (-1.0, -1.0)]
            )
        )

    def test_11_outer_boundary_edge_crossing_with_outside_endpoints_fails_closed(self) -> None:
        self.assertFalse(
            self._outer_boundary_case(
                [(-1.0, 1.0), (3.0, 1.0), (3.0, 3.0), (-1.0, 3.0)]
            )
        )

    def test_12_strictly_separated_outer_boundary_passes_geometric_predicate(self) -> None:
        self.assertTrue(
            self._outer_boundary_case(
                [(-1.0, -1.0), (3.0, -1.0), (3.0, 3.0), (-1.0, 3.0)]
            )
        )

    def test_13_failure_order_keeps_domain_and_every_inherited_gate_fail_closed(self) -> None:
        self.assertEqual(tuple(self.module.FAILURE_ORDER[:5]), self.module.DOMAIN_FAILURE_ORDER)
        self.assertEqual(
            tuple(self.module.FAILURE_ORDER[5:]),
            tuple(self.module._PARENT.FAILURE_ORDER),
        )
        self.assertIn("exterior_adjacent_face_preservation", self.module.FAILURE_ORDER)
        self.assertIn("global_seam_disjointness", self.module.FAILURE_ORDER)
        self.assertIn("boundary_angle_gate", self.module.FAILURE_ORDER)
        self.assertIn("chart_deviation_gate", self.module.FAILURE_ORDER)

    def test_14_worker_ast_is_read_only_and_has_one_permitted_bpy_operation(self) -> None:
        source = WORKER.read_text(encoding="utf-8")
        tree = ast.parse(source)
        bpy_ops = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                parts = []
                current = node.func
                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.append(current.id)
                name = ".".join(reversed(parts))
                if name.startswith("bpy.ops."):
                    bpy_ops.append(name)
        self.assertEqual(bpy_ops, ["bpy.ops.wm.open_mainfile"])
        for forbidden in (
            "bmesh",
            "save_as_mainfile",
            "save_mainfile",
            "bpy.ops.render",
            "bpy.ops.export",
            ".vertices.add(",
            ".polygons.add(",
            "from_pydata(",
        ):
            self.assertNotIn(forbidden, source)

    def test_15_wrapper_is_guard_first_create_new_one_shot_no_delete(self) -> None:
        source = WRAPPER.read_text(encoding="utf-8")
        guard = source.index("if ($InvocationGuard -cne")
        self.assertLess(guard, source.index("Get-Process -Name blender"))
        self.assertLess(guard, source.index("CreateDirectory($cacheRoot)"))
        self.assertLess(guard, source.index("Write-NewJson $claimPath"))
        self.assertEqual(source.count("& $blender --background"), 1)
        self.assertIn("[System.IO.FileMode]::CreateNew", source)
        self.assertNotIn("Remove-Item", source)
        self.assertNotIn("Start-Process", source)
        self.assertNotIn("automatic_retry_allowed = $true", source)
        self.assertIn("There is intentionally no retry path", source)

    def test_16_wrapper_parses_and_missing_guard_is_inert(self) -> None:
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        self.assertIsNotNone(powershell)
        parse_script = (
            "$t=$null;$e=$null;"
            "[System.Management.Automation.Language.Parser]::ParseFile("
            f"'{str(WRAPPER).replace(chr(39), chr(39) * 2)}',[ref]$t,[ref]$e)|Out-Null;"
            "if($e.Count){$e|ForEach-Object{$_.Message};exit 1}"
        )
        parsed = subprocess.run(
            [powershell, "-NoProfile", "-Command", parse_script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(parsed.returncode, 0, parsed.stdout + parsed.stderr)
        output = ROOT / self.config["output_contract"]["root"]
        cache = ROOT / self.config["output_contract"]["runtime_cache_root"]
        self.assertFalse(output.exists())
        self.assertFalse(cache.exists())
        rejected = subprocess.run(
            [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(WRAPPER)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("Invocation guard rejected", rejected.stdout + rejected.stderr)
        self.assertFalse(output.exists())
        self.assertFalse(cache.exists())

    def test_17_static_truth_claims_no_result_mutation_or_runtime_root(self) -> None:
        truth = self.config["truth"]
        self.assertTrue(truth["blender_not_run_by_static_package"])
        self.assertTrue(truth["carrier_domain_expansion_not_yet_measured"])
        self.assertTrue(truth["edge_complete_cycle_not_claimed"])
        self.assertTrue(truth["body_repair_not_claimed"])
        self.assertTrue(truth["mutation_package_not_prepared"])
        self.assertTrue(truth["candidate_not_saved"])
        self.assertTrue(truth["candidate_not_rendered"])
        self.assertTrue(truth["owner_approval_not_claimed"])
        self.assertTrue(all(value is False for value in self.config["scope"].values()))
        self.assertFalse((ROOT / self.config["output_contract"]["root"]).exists())
        self.assertFalse((ROOT / self.config["output_contract"]["runtime_cache_root"]).exists())

    def test_18_proposal_keeps_exterior_and_mutation_boundaries_explicit(self) -> None:
        proposal = PROPOSAL.read_text(encoding="utf-8")
        self.assertIn("exact 41-face exterior-adjacent protected ledger", proposal)
        self.assertIn("The exterior-adjacent rule remains a hard gate", proposal)
        self.assertIn("not a body-edit or mutation package", proposal)
        self.assertIn("Only no-Blender tests and recursive verification", proposal)


if __name__ == "__main__":
    unittest.main()
