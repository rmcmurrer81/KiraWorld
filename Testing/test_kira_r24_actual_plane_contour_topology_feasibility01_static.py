from __future__ import annotations

import ast
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools/blender_diagnose_kira_r24_actual_plane_contour_topology_feasibility01.py"
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_actual_plane_contour_topology_feasibility_01_static/"
    "ACTUAL_PLANE_CONTOUR_TOPOLOGY_FEASIBILITY01_CONFIG.json"
)
WRAPPER = CONFIG.with_name("run_actual_plane_contour_topology_feasibility01_once.ps1")
PROPOSAL = CONFIG.with_name("ACTUAL_PLANE_CONTOUR_TOPOLOGY_FEASIBILITY01_PROPOSAL.md")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_worker():
    spec = importlib.util.spec_from_file_location("r24_actual_plane_static_test", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not construct worker import")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ActualPlaneContourStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.module = load_worker()

    def test_01_safe_import_and_config_validation(self) -> None:
        self.assertNotIn("bpy", sys.modules)
        self.assertNotIn("bmesh", sys.modules)
        parent, base = self.module.validate_config(self.config)
        self.assertEqual(base["source_mesh"]["face_count"], 1436)
        self.assertEqual(base["domains"]["d2_face_count"], 88)
        self.assertEqual(base["domains"]["strict_envelope_face_count"], 161)
        self.assertEqual(base["domains"]["strict_envelope_collar_face_count"], 73)
        self.assertEqual(base["domains"]["strict_envelope_exterior_adjacent_face_count"], 41)
        self.assertEqual(base["domains"]["global_interface_vertex_count"], 34)
        self.assertEqual(base["domains"]["minimum_source_graph_rings_from_global_interface"], 4)
        self.assertEqual(parent["topology_seed"]["point_count"], 70)
        self.assertEqual(parent["topology_seed"]["segment_count"], 70)

    def test_02_direct_binding_spine_is_exact(self) -> None:
        self.assertEqual(len(self.config["immutable_bindings"]), 16)
        for name, binding in self.config["immutable_bindings"].items():
            with self.subTest(name=name):
                path = ROOT / binding["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, binding["bytes"])
                self.assertEqual(sha256(path), binding["sha256"])

    def test_03_parent_canonical_and_consumed_result_are_exact(self) -> None:
        parent = self.module.parent_config(self.config)
        self.assertEqual(
            self.module.compact_sha256(parent),
            "fffac614dc0682829b484aae9f028004263c3a4c2beb052a7578088c3615e382",
        )
        result = self.module.consumed_nonuniform_result(self.config)
        self.assertEqual(result["status"], "NO_ELIGIBLE_NONUNIFORM_RECORD_FAIL_CLOSED")
        self.assertEqual(result["solver_summary"]["generated_record_count"], 192)
        self.assertEqual(result["solver_summary"]["eligible_record_count"], 0)
        self.assertEqual(result["proposed_record"]["failure_names"], ["boundary_angle_gate"])
        self.assertEqual(
            result["proposed_record"]["record_sha256"],
            "6cc074964f95b230564790ebdd72ed7e06fef60f380b5dfa33b551eb0883a65c",
        )

    def test_04_consumed_external_integrity_manifest_is_semantically_complete(self) -> None:
        binding = self.config["immutable_bindings"]["parent_nonuniform_external_integrity"]
        path = ROOT / binding["path"]
        manifest = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["before"], manifest["after"])
        self.assertTrue(manifest["pre_post_exact"])
        self.assertEqual(manifest["blender_invocation_count"], 1)
        self.assertEqual(manifest["blender_exit_code"], 0)
        self.assertIsNone(manifest["native_invocation_error"])
        self.assertEqual(manifest["post_capture_errors"], [])
        self.assertEqual(manifest["finalization_errors"], [])
        self.assertFalse(manifest["retry_permitted"])
        self.assertEqual(len(manifest["before"]["lane_bindings"]), 24)
        self.assertEqual(len(manifest["before"]["inherited_bindings"]), 24)
        self.assertEqual(len(manifest["before"]["protected_inventories"]), 4)
        self.assertEqual(len(manifest["output_files"]), 5)
        for row in manifest["output_files"]:
            artifact = path.parent / row["name"]
            self.assertEqual(artifact.stat().st_size, row["bytes"])
            self.assertEqual(sha256(artifact), row["sha256"])

    def test_05_contract_is_one_plane_all_collar_no_clamp_no_retry(self) -> None:
        contour = self.config["contour_contract"]
        self.assertEqual(contour["sample_numerator"], 112)
        self.assertEqual(contour["sample_denominator"], 190)
        self.assertEqual(contour["collar_face_count"], 73)
        self.assertEqual(contour["maximum_segment_count"], 73)
        for key in (
            "endpoint_clamping_allowed",
            "reuse_fixed_70_edge_carrier_allowed",
            "alternate_plane_allowed",
            "randomness_allowed",
            "adaptive_retry_allowed",
            "free_world_space_points_allowed",
        ):
            self.assertFalse(contour[key], key)
        self.assertTrue(contour["evaluate_every_actual_component"])
        self.assertTrue(contour["single_proposed_output_record"])
        self.assertEqual(
            self.config["hard_gates"]["cut_loop_numeric_guard_minimum_angle_degrees"],
            12.000001,
        )
        self.assertEqual(
            self.config["hard_gates"]["cut_loop_numeric_guard_maximum_chart_deviation_m"],
            0.001099999999,
        )

    def test_06_qstar_is_exactly_rederived_from_seed_endpoint_range(self) -> None:
        seed = {
            "points": [
                {"edge": [0, 1]},
                {"edge": [1, 2]},
            ]
        }
        coordinates = [(0.0, 0.0, 0.0), (0.0, 0.0, 10.0), (0.0, 0.0, 20.0)]
        frame = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), 1.0)
        target, evidence, normal_by_vertex = self.module.derive_target_plane(
            seed, coordinates, frame, self.config
        )
        self.assertEqual(target, Fraction(224, 19))
        self.assertEqual(evidence["sample"], [56, 95])
        self.assertEqual(evidence["lower_seed_endpoint_normal"], [0, 1])
        self.assertEqual(evidence["upper_seed_endpoint_normal"], [20, 1])
        self.assertEqual(normal_by_vertex[1], Fraction(10, 1))
        with self.assertRaisesRegex(RuntimeError, "no span"):
            self.module.derive_target_plane(
                {"points": [{"edge": [0, 1]}]},
                [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)],
                frame,
                self.config,
            )

    def test_07_strict_unclamped_crossings_and_exact_two_owner_provenance(self) -> None:
        self.assertTrue(self.module.strict_crossing(Fraction(0), Fraction(2), Fraction(1)))
        self.assertFalse(self.module.strict_crossing(Fraction(1), Fraction(2), Fraction(1)))
        self.assertFalse(self.module.strict_crossing(Fraction(0), Fraction(1), Fraction(2)))
        faces = [(0, 1, 2), (1, 0, 3)]
        key, record = self.module.exact_point_record(
            (0, 1),
            Fraction(1),
            {0: Fraction(0), 1: Fraction(2), 2: Fraction(0), 3: Fraction(0)},
            faces,
            [0, 1],
        )
        self.assertEqual(key, (0, 1, 1, 2))
        self.assertEqual(record["t"], [1, 2])
        owner = [Fraction(*value) for value in record["owner_barycentric"]]
        other = [Fraction(*value) for value in record["other_barycentric"]]
        self.assertEqual(sum(owner), Fraction(1))
        self.assertEqual(sum(other), Fraction(1))
        self.assertEqual(owner.count(Fraction(0)), 1)
        self.assertEqual(other.count(Fraction(0)), 1)
        self.assertEqual(record["other_triangle_stored_order"], [1, 0, 3])
        self.assertTrue(record["exact_plane_equation_verified"])
        self.assertEqual(record["exact_plane_residual"], [0, 1])
        with self.assertRaises(ValueError):
            self.module.exact_point_record(
                (0, 1), Fraction(0), {0: Fraction(0), 1: Fraction(2)}, faces, [0, 1]
            )

    def test_08_march_fail_closed_on_vertex_plane_and_incomplete_edge_ownership(self) -> None:
        faces = [(0, 1, 2), (1, 0, 3)]
        incidence = self.module._BASE.edge_incidence(faces)
        context = {
            "envelope_vertices": {0, 1, 2, 3},
            "collar": {0, 1},
            "full_incidence": incidence,
        }
        _, _, failures, equal = self.module.build_actual_segments(
            faces,
            {0: Fraction(0), 1: Fraction(2), 2: Fraction(1), 3: Fraction(0)},
            Fraction(1),
            context,
        )
        self.assertIn("target_plane_vertex_or_edge_degeneracy", failures)
        self.assertEqual(equal, [2])
        _, _, failures, _ = self.module.build_actual_segments(
            faces,
            {0: Fraction(0), 1: Fraction(2), 2: Fraction(0), 3: Fraction(0)},
            Fraction(1),
            context,
        )
        self.assertIn("complete_two_collar_face_edge_ownership", failures)

    def test_09_component_extraction_rejects_open_branch_and_multiple_cycles(self) -> None:
        a, b, c, d = (0, 1, 1, 2), (1, 2, 1, 2), (2, 3, 1, 2), (3, 4, 1, 2)

        def segment(first, second, face=0):
            return {"source_face_index": face, "point_keys": [list(first), list(second)]}

        cycle = self.module.extract_components([segment(a, b), segment(b, c), segment(c, a)])
        self.assertEqual(len(cycle), 1)
        self.assertTrue(cycle[0]["closed_degree_two_cycle"])
        self.assertEqual(cycle[0]["point_count"], 3)
        open_chain = self.module.extract_components([segment(a, b), segment(b, c)])
        self.assertFalse(open_chain[0]["closed_degree_two_cycle"])
        branch = self.module.extract_components(
            [segment(a, b), segment(b, c), segment(b, d)]
        )
        self.assertFalse(branch[0]["closed_degree_two_cycle"])
        second = (10, 11, 1, 2), (11, 12, 1, 2), (12, 13, 1, 2)
        two = self.module.extract_components(
            [
                segment(a, b), segment(b, c), segment(c, a),
                segment(second[0], second[1], 1),
                segment(second[1], second[2], 1),
                segment(second[2], second[0], 1),
            ]
        )
        self.assertEqual(len(two), 2)

    def test_10_polygon_boundary_and_uncertainty_are_fail_closed(self) -> None:
        square = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
        self.assertTrue(self.module.strict_point_in_polygon((1.0, 1.0), square, 1e-12))
        self.assertFalse(self.module.strict_point_in_polygon((3.0, 1.0), square, 1e-12))
        self.assertFalse(self.module.strict_point_in_polygon((0.0, 1.0), square, 1e-12))

    def test_11_worker_ast_is_read_only_and_has_one_permitted_bpy_operation(self) -> None:
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

    def test_12_wrapper_is_guard_first_create_new_one_shot_no_delete(self) -> None:
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

    def test_13_wrapper_parses_and_missing_guard_is_inert(self) -> None:
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        self.assertIsNotNone(powershell)
        parse_script = (
            "$t=$null;$e=$null;"
            "[System.Management.Automation.Language.Parser]::ParseFile(" 
            f"'{str(WRAPPER).replace("'", "''")}',[ref]$t,[ref]$e)|Out-Null;"
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
            [
                powershell,
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
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("Invocation guard rejected", rejected.stdout + rejected.stderr)
        self.assertFalse(output.exists())
        self.assertFalse(cache.exists())

    def test_14_static_truth_does_not_claim_a_runtime_result(self) -> None:
        truth = self.config["truth"]
        self.assertTrue(truth["blender_not_run_by_static_package"])
        self.assertTrue(truth["actual_plane_contour_not_yet_measured"])
        self.assertTrue(truth["eligible_contour_not_claimed"])
        self.assertTrue(truth["body_repair_not_claimed"])
        self.assertTrue(truth["candidate_not_saved"])
        self.assertTrue(truth["candidate_not_rendered"])
        self.assertTrue(truth["owner_approval_not_claimed"])
        self.assertTrue(all(value is False for value in self.config["scope"].values()))
        self.assertFalse((ROOT / self.config["output_contract"]["root"]).exists())
        self.assertFalse((ROOT / self.config["output_contract"]["runtime_cache_root"]).exists())

    def test_15_seed_use_is_range_derivation_or_postmarch_diagnostic_only(self) -> None:
        source = WORKER.read_text(encoding="utf-8")
        marcher = source[
            source.index("def build_actual_segments("):
            source.index("def extract_components(")
        ]
        self.assertNotIn("seed", marcher)
        self.assertNotIn("k1", marcher)

        evaluator = source[
            source.index("def evaluate_actual_plane_contour("):
            source.index("def runtime_output_paths(")
        ]
        self.assertLess(
            evaluator.index("build_actual_segments("),
            evaluator.index("k1_graph_distances("),
        )
        self.assertIn("if len(components) != 1:", evaluator)
        self.assertIn("eligible = [row for row in records", evaluator)
        self.assertIn("selected = min(eligible, key=component_score) if eligible else None", evaluator)

        proposal = PROPOSAL.read_text(encoding="utf-8")
        self.assertIn("post-march diagnostic comparisons", proposal)
        self.assertIn("multiple-component condition fails every component closed", proposal)


if __name__ == "__main__":
    unittest.main()
