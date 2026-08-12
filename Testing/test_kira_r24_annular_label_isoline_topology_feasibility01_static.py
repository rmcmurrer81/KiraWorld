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
WORKER = ROOT / "tools/blender_diagnose_kira_r24_annular_label_isoline_topology_feasibility01.py"
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_annular_label_isoline_topology_feasibility_01_static/"
    "ANNULAR_LABEL_ISOLINE_TOPOLOGY_FEASIBILITY01_CONFIG.json"
)
WRAPPER = CONFIG.with_name("run_annular_label_isoline_topology_feasibility01_once.ps1")
PROPOSAL = CONFIG.with_name("ANNULAR_LABEL_ISOLINE_TOPOLOGY_FEASIBILITY01_PROPOSAL.md")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_worker():
    spec = importlib.util.spec_from_file_location("r24_annular_label_static_test", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not construct worker import")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AnnularLabelIsolineStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.module = load_worker()

    def test_01_safe_import_and_recursive_parent_validation(self) -> None:
        self.assertNotIn("bpy", sys.modules)
        self.assertNotIn("bmesh", sys.modules)
        actual_parent, base, parent = self.module.validate_config(self.config)
        self.assertEqual(base["source_mesh"]["vertex_count"], 736)
        self.assertEqual(base["source_mesh"]["face_count"], 1436)
        self.assertEqual(base["domains"]["d2_face_count"], 88)
        self.assertEqual(base["domains"]["strict_envelope_collar_face_count"], 73)
        self.assertEqual(parent["attempt_id"], "edge_complete_carrier_domain_01")
        self.assertEqual(actual_parent["topology_seed"]["point_count"], 70)

    def test_02_direct_binding_spine_is_exact(self) -> None:
        self.assertEqual(len(self.config["immutable_bindings"]), 11)
        for name, binding in self.config["immutable_bindings"].items():
            with self.subTest(name=name):
                path = ROOT / binding["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, binding["bytes"])
                self.assertEqual(sha256(path), binding["sha256"])

    def test_03_consumed_edge_result_is_terminal_and_exact(self) -> None:
        report = self.module.consumed_edge_result(self.config)
        solver = report["solver_summary"]
        self.assertEqual(
            report["status"], "NO_ELIGIBLE_EDGE_COMPLETE_CARRIER_DOMAIN_FAIL_CLOSED"
        )
        self.assertEqual(solver["candidate_record_count"], 5)
        self.assertEqual(solver["eligible_candidate_count"], 0)
        self.assertEqual(
            [row["component_count"] for row in solver["candidate_records"]],
            [2, 3, 4, 4, 5],
        )
        self.assertTrue(solver["finite_termination_reached"])
        self.assertFalse(solver["mesh_mutation_used"])

    def test_04_exact_annulus_binding_has_two_complete_boundary_cycles(self) -> None:
        contract = self.config["annular_label_contract"]
        self.assertEqual(contract["collar_face_count"], 73)
        self.assertEqual(contract["collar_vertex_count"], 73)
        self.assertEqual(contract["collar_euler_characteristic"], 0)
        self.assertEqual(contract["collar_boundary_cycle_count"], 2)
        self.assertEqual(len(contract["inner_d2_boundary_cycle"]), 32)
        self.assertEqual(len(contract["outer_estar_boundary_cycle"]), 41)
        self.assertFalse(
            set(contract["inner_d2_boundary_cycle"])
            & set(contract["outer_estar_boundary_cycle"])
        )

    def test_05_candidate_family_is_exact_finite_dyadic_and_nonplane(self) -> None:
        contract = self.config["annular_label_contract"]
        self.assertEqual(contract["candidate_levels"], [[value, 32] for value in range(1, 32)])
        self.assertEqual(contract["candidate_count"], 31)
        for key in (
            "plane_equation_used",
            "source_star_search_used",
            "alternate_topology_allowed",
            "randomness_allowed",
            "adaptive_retry_allowed",
            "free_world_space_points_allowed",
            "mutation_package_allowed",
        ):
            self.assertFalse(contract[key], key)
        self.assertLess(contract["candidate_count"], self.config["hard_gates"]["maximum_candidate_records"])

    def _synthetic_annulus(self):
        faces = [
            (0, 1, 5), (0, 5, 4),
            (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6),
            (3, 0, 4), (3, 4, 7),
        ]
        context = {
            "collar": set(range(8)),
            "full_incidence": self.module._BASE.edge_incidence(faces),
            "envelope_vertices": set(range(8)),
        }
        labels = {value: Fraction(0) for value in range(4)}
        labels.update({value: Fraction(1) for value in range(4, 8)})
        return faces, context, labels

    def test_06_binary_annular_label_creates_one_closed_cycle(self) -> None:
        faces, context, labels = self._synthetic_annulus()
        points, segments, failures, equal = self.module._PLANE.build_actual_segments(
            faces, labels, Fraction(1, 2), context
        )
        self.assertEqual(failures, [])
        self.assertEqual(equal, [])
        self.assertEqual(len(points), 8)
        self.assertEqual(len(segments), 8)
        components = self.module._PLANE.extract_components(segments)
        self.assertEqual(len(components), 1)
        self.assertTrue(components[0]["closed_degree_two_cycle"])
        self.assertEqual(components[0]["point_count"], 8)

    def test_07_all_dyadic_levels_keep_the_same_closed_topology(self) -> None:
        faces, context, labels = self._synthetic_annulus()
        signatures = set()
        for numerator in range(1, 32):
            points, segments, failures, equal = self.module._PLANE.build_actual_segments(
                faces, labels, Fraction(numerator, 32), context
            )
            components = self.module._PLANE.extract_components(segments)
            self.assertEqual(failures, [])
            self.assertEqual(equal, [])
            self.assertEqual(len(components), 1)
            self.assertTrue(components[0]["closed_degree_two_cycle"])
            signatures.add((len(points), len(segments), components[0]["point_count"]))
        self.assertEqual(signatures, {(8, 8, 8)})

    def test_08_exact_open_edge_barycentric_provenance_is_rational(self) -> None:
        faces, context, labels = self._synthetic_annulus()
        points, segments, failures, equal = self.module._PLANE.build_actual_segments(
            faces, labels, Fraction(7, 32), context
        )
        self.assertEqual(failures, [])
        for record in points.values():
            record["exact_label_residual"] = record.pop("exact_plane_residual")
            record["exact_label_equation_verified"] = record.pop(
                "exact_plane_equation_verified"
            )
            self.assertEqual(Fraction(*record["t"]), Fraction(7, 32))
            self.assertEqual(record["exact_label_residual"], [0, 1])
            self.assertEqual(len(record["incident_source_faces"]), 2)
            self.assertTrue(record["exact_label_equation_verified"])
        self.assertEqual(len(segments), 8)
        self.assertEqual(equal, [])

    def test_09_unchanged_geometry_gates_are_still_strict(self) -> None:
        gates = self.config["hard_gates"]
        self.assertEqual(gates["cut_loop_numeric_guard_minimum_angle_degrees"], 12.000001)
        self.assertEqual(gates["cut_loop_numeric_guard_maximum_chart_deviation_m"], 0.001099999999)
        self.assertEqual(gates["minimum_future_render_triangle_angle_degrees"], 12.0)
        self.assertEqual(gates["minimum_future_render_triangle_area_m2"], 1e-10)
        self.assertEqual(gates["global_interface_coordinate_delta_m"], 0.0)
        self.assertEqual(gates["global_interface_unique_weld_count"], 34)

    def test_10_worker_ast_is_read_only_with_only_open_mainfile_bpy_operation(self) -> None:
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

    def test_11_wrapper_is_guard_first_one_shot_create_new_no_delete(self) -> None:
        source = WRAPPER.read_text(encoding="utf-8")
        guard = source.index("if ($InvocationGuard -cne")
        self.assertLess(guard, source.index("Get-Process -Name blender"))
        self.assertLess(guard, source.index("CreateDirectory($cacheRoot)"))
        self.assertLess(guard, source.index("Write-NewJson $claimPath"))
        self.assertEqual(source.count("& $blender --background"), 1)
        self.assertIn("[System.IO.FileMode]::CreateNew", source)
        self.assertNotIn("Remove-Item", source)
        self.assertNotIn("Start-Process", source)
        self.assertIn("There is intentionally no retry path", source)

    def test_12_wrapper_parses_and_missing_guard_is_inert(self) -> None:
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

    def test_13_static_truth_claims_no_result_or_body_mutation(self) -> None:
        truth = self.config["truth"]
        self.assertTrue(truth["blender_not_run_by_static_package"])
        self.assertTrue(truth["annular_label_levels_not_yet_measured"])
        self.assertTrue(truth["closed_eligible_cycle_not_claimed"])
        self.assertTrue(truth["body_repair_not_claimed"])
        self.assertTrue(truth["mutation_package_not_prepared"])
        self.assertTrue(truth["candidate_not_saved"])
        self.assertTrue(truth["candidate_not_rendered"])
        self.assertTrue(truth["owner_approval_not_claimed"])
        self.assertTrue(all(value is False for value in self.config["scope"].values()))
        self.assertFalse((ROOT / self.config["output_contract"]["root"]).exists())
        self.assertFalse((ROOT / self.config["output_contract"]["runtime_cache_root"]).exists())

    def test_14_proposal_explicitly_retires_plane_and_source_star_families(self) -> None:
        proposal = PROPOSAL.read_text(encoding="utf-8")
        self.assertIn("No further plane-defined contour family is proposed", proposal)
        self.assertIn("not another existing-source-star search", proposal)
        self.assertIn("31 exact dyadic levels", proposal)
        self.assertIn("not a mutation or render package", proposal)


if __name__ == "__main__":
    unittest.main()
