"""Static-only acceptance for R24 Attempt 47.

The suite derives and inspects the final Blender program but never imports
Blender, creates an Attempt 47 output, or launches a process.
"""

from __future__ import annotations

import ast
import collections
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / (
    "tools/blender_diagnose_kira_r24_blackproject_"
    "last_attributable_source_stars_attempt47.py"
)
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT47_CONFIG.json"
)
OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/attempt_47"
)
EXTERNAL_OUTPUTS = (
    ROOT / "RecoverySprint/continuation_20260808/attempt47_blender_stdout.log",
    ROOT / "RecoverySprint/continuation_20260808/attempt47_blender_stderr.log",
    ROOT
    / "RecoverySprint/continuation_20260808/attempt47_external_pre_post_integrity.json",
)
EXPECTED_WORKER_SHA256 = (
    "a08ee6cd2a7ae03daac2944dc31e130d25ef3a5ae96c326acc41f408c29fa770"
)
EXPECTED_CONFIG_SHA256 = (
    "f0d116cdb64b4c813e25214de87dcf0a660938f4393f5b2ab12421bc6b53a3b4"
)
EXPECTED_ATTEMPT46_SOURCE_SHA256 = (
    "82d2332c4a39fea67a968c3d1ed31abd3e06a209e903161741db54121741c066"
)
EXPECTED_DERIVED_SHA256 = (
    "2f6fbea317c01a8bbe5c9e9d1a9aea39d896b17c178b084942343d2a6a48115a"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_worker():
    spec = importlib.util.spec_from_file_location("attempt47_static_test", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("Attempt 47 static worker could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def literal_probe_subscripts(source: str) -> list[str]:
    references: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Subscript):
            continue
        if not isinstance(node.value, ast.Name) or node.value.id != "probe":
            continue
        if not isinstance(node.slice, ast.Constant) or not isinstance(
            node.slice.value, str
        ):
            raise AssertionError("derived source contains a dynamic probe subscript")
        references.append(node.slice.value)
    return references


def dotted_call_name(node: ast.Call) -> str:
    parts: list[str] = []
    value: ast.AST = node.func
    while isinstance(value, ast.Attribute):
        parts.append(value.attr)
        value = value.value
    if isinstance(value, ast.Name):
        parts.append(value.id)
    return ".".join(reversed(parts))


class Attempt47StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cache_dir = ROOT / "tools/__pycache__"
        cls.before_caches = (
            sorted(str(path.resolve()) for path in cache_dir.glob("*attempt47*.pyc"))
            if cache_dir.exists()
            else []
        )
        cls.module = load_worker()
        cls.config = cls.module.load_config()
        cls.verified = cls.module.verify_package(cls.config)

    @classmethod
    def tearDownClass(cls) -> None:
        cache_dir = ROOT / "tools/__pycache__"
        after = (
            sorted(str(path.resolve()) for path in cache_dir.glob("*attempt47*.pyc"))
            if cache_dir.exists()
            else []
        )
        if after != cls.before_caches:
            raise AssertionError("Attempt 47 static suite created worker bytecode")

    def test_01_exact_outer_hashes(self) -> None:
        self.assertEqual(sha256_file(WORKER), EXPECTED_WORKER_SHA256)
        self.assertEqual(sha256_file(CONFIG), EXPECTED_CONFIG_SHA256)

    def test_02_identity_and_all_output_absence(self) -> None:
        self.assertEqual(self.config["attempt_id"], "attempt_47")
        self.assertEqual(
            self.config["status"],
            "STATIC_READ_ONLY_LAST_ATTRIBUTABLE_SOURCE_STARS_PREPARED_NOT_RUN",
        )
        self.assertFalse(OUTPUT.exists())
        self.assertTrue(all(not path.exists() for path in EXTERNAL_OUTPUTS))
        self.assertFalse(self.config["launch_contract"]["wrapper_prepared_in_this_package"])

    def test_03_exact_one_indivisible_candidate(self) -> None:
        candidate = self.config["one_candidate_contract"]
        self.assertEqual(
            candidate["candidate"],
            "complete_attempt46_domain_plus_complete_mesh_vertex_stars_351_248_676",
        )
        self.assertEqual(candidate["attempt46_base_source_mesh_vertex_stars"], [218, 508])
        self.assertEqual(
            candidate["new_compound_blocker_source_mesh_vertex_stars"],
            [351, 248, 676],
        )
        self.assertEqual(
            candidate["all_source_mesh_vertex_stars_after_attempt44"],
            [218, 508, 351, 248, 676],
        )
        self.assertTrue(candidate["one_indivisible_compound_candidate"])
        self.assertFalse(candidate["separate_star_candidates_allowed"])
        self.assertFalse(candidate["uniform_face_ring_candidates_allowed"])
        self.assertFalse(candidate["alternate_target_sets_allowed"])

    def test_04_attempt46_runtime_files_are_byte_exact(self) -> None:
        records = self.verified["records"]
        self.assertEqual(
            records["attempt46_diagnostic"]["sha256"],
            "5b6b0e7f4596dbb674a8bc36d59a9cc31f122eadaa4a39125727d6ea0c38ea0a",
        )
        self.assertEqual(
            records["attempt46_external_integrity"]["sha256"],
            "20871d49e9afa6b8ba9a1f4bb05d2b258c5ac70561dbe94d4e23bb5554522232",
        )
        self.assertEqual(
            records["attempt46_runtime_checkpoint"]["sha256"],
            "fcf8b369f96dc8f436776febdc90ddb877acbafb522dd38b83ba2ef2a3efaa4f",
        )

    def test_05_attempt46_exact_rejected_candidate_is_bound(self) -> None:
        evidence = self.verified["attempt46_evidence"]
        row = evidence["candidate"]
        self.assertEqual(row["face_count"], 135)
        self.assertEqual(row["vertex_count"], 95)
        self.assertEqual(row["edge_count"], 229)
        self.assertEqual(row["boundary_edge_count"], 53)
        self.assertFalse(row["simple_projected_boundary"])
        self.assertEqual(
            row["boundary_angle_analysis"]["minimum_boundary_interior_angle_degrees"],
            10.810841145214567,
        )
        self.assertEqual(row["chart"]["maximum_absolute_boundary_deviation_m"], 0.0022750297794118524)
        self.assertEqual(
            row["chart"]["boundary_deviation_attribution"]["maximum_contributor_mesh_vertex_indices"],
            [351],
        )
        self.assertEqual(
            row["forced_ear_feasibility"]["obstructions"][0]["fixed_ear_minimum_angle_degrees"],
            0.7490738376972431,
        )

    def test_06_only_crossing_and_shared_676_attribution_are_exact(self) -> None:
        crossing = self.verified["attempt46_evidence"]["crossings"]
        self.assertEqual(len(crossing), 1)
        self.assertEqual(crossing[0]["first_edge_mesh_vertices"], [531, 676])
        self.assertEqual(crossing[0]["second_edge_mesh_vertices"], [689, 690])
        self.assertEqual(self.config["one_candidate_contract"]["role_by_new_source_mesh_vertex"]["676"], "forced_ear_obstruction_and_endpoint_of_only_boundary_crossing_edge")

    def test_07_wrapper_bookkeeping_is_diagnosed_not_hidden(self) -> None:
        evidence = self.verified["attempt46_evidence"]
        self.assertEqual(evidence["stable_inventory_count"], 343)
        self.assertEqual(
            set(evidence["changed_inventory_paths"]),
            {
                "RecoverySprint/continuation_20260808/attempt46_blender_stdout.log",
                "RecoverySprint/continuation_20260808/attempt46_blender_stderr.log",
            },
        )
        launch = self.config["launch_contract"]
        self.assertTrue(launch["wrapper_builds_fresh_protected_inventory"])
        self.assertTrue(
            launch[
                "wrapper_excludes_its_own_stdout_stderr_and_integrity_from_immutable_before_after"
            ]
        )
        self.assertTrue(launch["wrapper_protects_final_attempt46_logs_and_integrity_as_inputs"])

    def test_08_all_343_stable_attempt46_inventory_records_are_current(self) -> None:
        # verify_package hashes each stable record and fails before this test if
        # any protected Attempts 1-46 input differs.
        self.assertEqual(self.verified["attempt46_evidence"]["stable_inventory_count"], 343)
        self.assertTrue(
            self.verified["attempt46_evidence"]["integrity"][
                "relevant_bytecode_cache_inventory_exact"
            ]
        )

    def test_09_attempt46_source_and_attempt47_derived_hashes_are_bound(self) -> None:
        source46 = self.verified["reconstructed"]["source46"]
        source47 = self.verified["derived_source"]
        self.assertEqual(hashlib.sha256(source46.encode()).hexdigest(), EXPECTED_ATTEMPT46_SOURCE_SHA256)
        self.assertEqual(hashlib.sha256(source47.encode()).hexdigest(), EXPECTED_DERIVED_SHA256)
        self.assertEqual(self.verified["derived_source_sha256"], EXPECTED_DERIVED_SHA256)

    def test_10_every_literal_probe_reference_exists(self) -> None:
        references = literal_probe_subscripts(self.verified["derived_source"])
        manifest = self.verified["runtime_config"]["one_candidate_probe"]
        self.assertGreater(len(references), 0)
        self.assertEqual(sorted(set(references).difference(manifest)), [])
        counts = collections.Counter(references)
        self.assertEqual(counts["attempt46_base_source_mesh_vertex_stars"], 1)
        self.assertEqual(counts["new_compound_blocker_source_mesh_vertex_stars"], 2)
        self.assertEqual(counts["attempt44_chart_maximum_boundary_index"], 1)
        self.assertEqual(counts["attempt44_forced_ear_obstruction_boundary_index"], 2)

    def test_11_missing_probe_key_regression_fails_closed(self) -> None:
        regressed = self.verified["derived_source"].replace(
            'probe["attempt46_base_source_mesh_vertex_stars"]',
            'probe["attempt47_missing_base_source_mesh_vertex_stars"]',
            1,
        )
        with self.assertRaisesRegex(RuntimeError, "probe keys are absent"):
            self.module.validate_probe_key_contract(
                regressed, self.verified["runtime_config"]["one_candidate_probe"]
            )

    def test_12_derived_program_maps_one_final_candidate_only(self) -> None:
        source = self.verified["derived_source"]
        self.assertEqual(
            source.count(
                '"complete_attempt46_domain_plus_complete_mesh_vertex_stars_351_248_676"'
            ),
            1,
        )
        self.assertEqual(source.count("        targeted.append(row)"), 1)
        self.assertEqual(source.count('probe["new_compound_blocker_source_mesh_vertex_stars"]'), 2)
        self.assertNotIn("uniform_face_ring_expansions_to_map =", source)

    def test_13_exact_attempt46_base_is_reverified_in_derived_program(self) -> None:
        source = self.verified["derived_source"]
        for token in (
            'config["attempt46_base_contract"]',
            '"reverified_complete_attempt46_candidate"',
            '"attempt46_complete_candidate_reverified"',
            '"attempt46_base_source_star_rows"',
            '"Attempt 47 exact Attempt 46 base domain drifted"',
        ):
            self.assertIn(token, source)

    def test_14_derived_ast_has_no_mutation_save_render_or_export(self) -> None:
        source = self.verified["derived_source"]
        tree = ast.parse(source)
        names = {dotted_call_name(node) for node in ast.walk(tree) if isinstance(node, ast.Call)}
        forbidden_prefixes = (
            "bpy.ops.wm.save",
            "bpy.ops.render",
            "bpy.ops.export",
            "bpy.ops.object.join",
            "bmesh.ops.delete",
        )
        self.assertFalse(any(name.startswith(forbidden_prefixes) for name in names))
        for token in ("to_mesh(", "save_as_mainfile", "render.render", "export_scene"):
            self.assertNotIn(token, source)

    def test_15_all_hard_gates_are_unchanged(self) -> None:
        hard = self.config["unchanged_hard_gates"]
        self.assertEqual(hard["required_minimum_angle_degrees"], 12.0)
        self.assertEqual(hard["maximum_local_chart_boundary_deviation_m"], 0.0011)
        self.assertEqual(hard["minimum_new_triangle_area_m2"], 1e-10)
        self.assertTrue(hard["simple_projected_boundary_required"])
        self.assertEqual(hard["global_seam_vertex_count"], 34)
        self.assertEqual(hard["global_seam_coordinate_delta_m"], 0.0)
        runtime = self.verified["runtime_config"]
        self.assertEqual(runtime["diagnosis"]["required_minimum_angle_degrees"], 12.0)
        self.assertEqual(
            runtime["source_identity_contract"]["maximum_local_chart_boundary_deviation_m"],
            0.0011,
        )

    def test_16_failure_is_terminal_for_source_star_chasing(self) -> None:
        terminal = self.config["terminal_source_star_rule"]
        self.assertTrue(terminal["this_is_last_attributable_source_star_candidate"])
        self.assertTrue(terminal["if_any_necessary_gate_fails_stop_source_star_expansion"])
        self.assertFalse(terminal["attempt48_source_star_followup_allowed"])
        self.assertFalse(terminal["shifted_blocker_chasing_allowed"])
        self.assertIn(
            '"source_star_expansion_terminal_if_candidate_fails": True',
            self.verified["derived_source"],
        )

    def test_17_scope_and_truth_prohibit_execution_claims(self) -> None:
        scope = self.config["scope"]
        for name in (
            "body_geometry_mutation_allowed",
            "patch_geometry_mutation_allowed",
            "triangulation_allowed",
            "reconstruction_allowed",
            "render_allowed",
            "blend_save_allowed",
            "export_allowed",
            "runtime_activation_allowed",
            "assignment_allowed",
            "publication_allowed",
            "automatic_retry_allowed",
        ):
            self.assertFalse(scope[name], name)
        for name in (
            "attempt47_wrapper_prepared",
            "attempt47_blender_execution_performed",
            "attempt47_source_domain_mapping_performed",
            "attempt47_candidate_feasibility_proven",
            "attempt47_body_mutation_performed",
            "runtime_changed",
            "body_repair_proven",
            "owner_approval_claimed",
        ):
            self.assertFalse(self.config["truth"][name], name)

    def test_18_no_blender_module_or_process_was_used(self) -> None:
        self.assertNotIn("bpy", sys.modules)
        self.assertNotIn("bmesh", sys.modules)
        self.assertFalse(OUTPUT.exists())
        self.assertTrue(all(not path.exists() for path in EXTERNAL_OUTPUTS))

    def test_19_config_and_worker_are_parseable(self) -> None:
        self.assertEqual(json.loads(CONFIG.read_text(encoding="utf-8")), self.config)
        ast.parse(WORKER.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
