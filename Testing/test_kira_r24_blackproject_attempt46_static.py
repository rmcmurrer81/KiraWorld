"""Static-only acceptance for R24 Attempt 46.

This suite must never launch Blender. It binds the exact Attempt 45 pre-
diagnostic KeyError evidence and verifies the smallest derived probe-key
repair before a separate independent audit may authorize one execution.
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
    "compound_local_blocker_stars_attempt46.py"
)
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT46_CONFIG.json"
)
OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/attempt_46"
)
EXTERNAL_OUTPUTS = (
    ROOT / "RecoverySprint/continuation_20260808/attempt46_blender_stdout.log",
    ROOT / "RecoverySprint/continuation_20260808/attempt46_blender_stderr.log",
    ROOT
    / "RecoverySprint/continuation_20260808/attempt46_external_pre_post_integrity.json",
)
EXPECTED_WORKER_SHA256 = (
    "1da1962a11233f5c6247d90ebd085f3b61e04d5048828e0cbebf2fc03c6502c3"
)
EXPECTED_CONFIG_SHA256 = (
    "c9b2db89e58726b82a22146c1af2eacb7a3c121156f0f1336951792131881780"
)
EXPECTED_DERIVED_SHA256 = (
    "82d2332c4a39fea67a968c3d1ed31abd3e06a209e903161741db54121741c066"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_worker():
    spec = importlib.util.spec_from_file_location("attempt46_static_test", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("Attempt 46 static worker could not be loaded")
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


class Attempt46StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cache_dir = ROOT / "tools/__pycache__"
        cls.before_caches = (
            sorted(str(path.resolve()) for path in cache_dir.glob("*attempt46*.pyc"))
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
            sorted(str(path.resolve()) for path in cache_dir.glob("*attempt46*.pyc"))
            if cache_dir.exists()
            else []
        )
        if after != cls.before_caches:
            raise AssertionError("Attempt 46 static suite created worker bytecode")

    def test_01_exact_outer_hashes(self) -> None:
        self.assertEqual(sha256_file(WORKER), EXPECTED_WORKER_SHA256)
        self.assertEqual(sha256_file(CONFIG), EXPECTED_CONFIG_SHA256)

    def test_02_identity_and_output_absence(self) -> None:
        self.assertEqual(self.config["attempt_id"], "attempt_46")
        self.assertEqual(
            self.config["status"],
            "STATIC_READ_ONLY_PROBE_KEY_CONTRACT_REPAIR_PREPARED_NOT_RUN",
        )
        self.assertFalse(OUTPUT.exists())
        self.assertTrue(all(not path.exists() for path in EXTERNAL_OUTPUTS))

    def test_03_scope_is_read_only_and_one_candidate(self) -> None:
        scope = self.config["scope"]
        self.assertTrue(scope["exact_one_compound_blocker_vertex_star_mapping_allowed"])
        self.assertTrue(scope["exact_runtime_probe_key_contract_required_before_blender"])
        self.assertFalse(scope["separate_blocker_star_candidates_allowed"])
        self.assertFalse(scope["automatic_alternate_candidate_allowed"])
        self.assertFalse(scope["automatic_retry_allowed"])
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
            "boundary_or_seam_movement_allowed",
            "arbitrary_new_coordinate_allowed",
            "quality_gate_reduction_allowed",
        ):
            self.assertFalse(scope[name], name)

    def test_04_exact_candidate_was_not_changed(self) -> None:
        candidate = self.config["one_candidate_contract"]
        self.assertEqual(
            candidate["candidate"],
            "complete_attempt44_domain_plus_complete_mesh_vertex_stars_218_508",
        )
        self.assertEqual(candidate["required_complete_source_mesh_vertex_stars"], [241, 218, 508])
        self.assertEqual(candidate["new_compound_blocker_source_mesh_vertex_stars"], [218, 508])
        self.assertTrue(candidate["one_indivisible_compound_candidate"])
        self.assertFalse(candidate["separate_star_candidates_allowed"])

    def test_05_attempt45_failure_is_exact(self) -> None:
        evidence = self.verified["attempt45_evidence"]
        self.assertEqual(
            evidence["failure"]["error"],
            "'attempt45_chart_maximum_boundary_index'",
        )
        self.assertEqual(evidence["failure"]["error_type"], "KeyError")
        self.assertFalse(evidence["failure"]["diagnostic_exists"])
        self.assertFalse(evidence["failure"]["mesh_mutated"])
        self.assertFalse(evidence["failure"]["body_mutated"])

    def test_06_attempt45_inventory_is_exact(self) -> None:
        evidence = self.verified["attempt45_evidence"]
        integrity = evidence["integrity"]
        self.assertEqual(len(evidence["protected_records"]), 331)
        self.assertEqual(integrity["before"], integrity["after"])
        self.assertTrue(integrity["pre_post_exact"])
        self.assertTrue(integrity["relevant_bytecode_cache_inventory_exact"])
        self.assertEqual(integrity["blender_exit_code"], 1)
        self.assertIsNone(integrity["native_invocation_error"])

    def test_07_attempt45_files_are_byte_exact(self) -> None:
        records = self.verified["records"]
        self.assertEqual(
            records["attempt45_started"]["sha256"],
            "0e5a28acf04f582ddb5a06c4ad5328fa813a195587608c2cfcb09af692160ea9",
        )
        self.assertEqual(
            records["attempt45_failure"]["sha256"],
            "5da757d6999e36783a0c32c9a9e0c3c8c6ec95b50d4614b174298264644dca1d",
        )
        self.assertEqual(
            records["attempt45_external_integrity"]["sha256"],
            "3b03a517522069aacca4cfae2eee13d3d09ba36be6a8195145ad4bf10278c248",
        )

    def test_08_derived_source_hash_is_bound(self) -> None:
        source = self.verified["derived_source"]
        self.assertEqual(self.verified["derived_source_sha256"], EXPECTED_DERIVED_SHA256)
        self.assertEqual(hashlib.sha256(source.encode("utf-8")).hexdigest(), EXPECTED_DERIVED_SHA256)

    def test_09_every_literal_probe_reference_exists_in_manifest(self) -> None:
        # This is the structural regression gate Attempt 45 lacked. It extracts
        # every probe["..."] from the final derived AST, not from templates.
        source = self.verified["derived_source"]
        references = literal_probe_subscripts(source)
        manifest = self.verified["runtime_config"]["one_candidate_probe"]
        self.assertGreater(len(references), 0)
        self.assertEqual(sorted(set(references).difference(manifest)), [])
        counts = collections.Counter(references)
        self.assertEqual(counts["attempt44_chart_maximum_boundary_index"], 1)
        self.assertEqual(counts["attempt44_chart_maximum_mesh_vertex_index"], 1)
        self.assertEqual(counts["attempt44_forced_ear_obstruction_boundary_index"], 2)
        self.assertEqual(counts["attempt44_forced_ear_obstruction_mesh_vertex_index"], 1)

    def test_10_attempt45_missing_key_regression_is_rejected(self) -> None:
        source = self.verified["derived_source"]
        regressed = source.replace(
            'probe["attempt44_chart_maximum_boundary_index"]',
            'probe["attempt45_chart_maximum_boundary_index"]',
            1,
        )
        with self.assertRaisesRegex(RuntimeError, "probe keys are absent"):
            self.module.validate_probe_key_contract(
                regressed, self.verified["runtime_config"]["one_candidate_probe"]
            )

    def test_11_only_semantic_probe_names_are_restored(self) -> None:
        source = self.verified["derived_source"]
        self.assertNotIn('probe["attempt45_', source)
        self.assertNotIn('probe["attempt46_', source)
        for key in self.config["probe_key_repair"]["exact_semantic_keys"]:
            self.assertIn(f'probe["{key}"]', source)
        self.assertEqual(
            hashlib.sha256(self.verified["source45"].encode("utf-8")).hexdigest(),
            "481dd0105147edef6f39b2f682f2def99388355c325429b02e5d11e214c11ccf",
        )

    def test_12_derived_source_has_one_compound_mapping(self) -> None:
        source = self.verified["derived_source"]
        self.assertEqual(
            source.count(
                '"complete_attempt44_domain_plus_complete_mesh_vertex_stars_218_508"'
            ),
            1,
        )
        self.assertEqual(source.count('"compound_source_star_rows"'), 1)
        self.assertEqual(source.count('"one_indivisible_compound_candidate"'), 1)
        self.assertNotIn("uniform_face_ring_expansions_to_map =", source)

    def test_13_derived_ast_has_no_forbidden_mutation_calls(self) -> None:
        source = self.verified["derived_source"]
        ast.parse(source)
        for token in (
            "bpy.ops.wm.save",
            "bpy.ops.render",
            "bpy.ops.export",
            "bpy.ops.object.join",
            "bmesh.ops.delete",
            "to_mesh(",
        ):
            self.assertNotIn(token, source)

    def test_14_runtime_config_retains_hard_gates(self) -> None:
        runtime = self.verified["runtime_config"]
        self.assertEqual(runtime["attempt_id"], "attempt_46")
        self.assertEqual(runtime["diagnosis"]["required_minimum_angle_degrees"], 12.0)
        self.assertEqual(
            runtime["source_identity_contract"]["maximum_local_chart_boundary_deviation_m"],
            0.0011,
        )
        self.assertEqual(runtime["unchanged_hard_gates"]["global_seam_vertex_count"], 34)
        self.assertEqual(runtime["unchanged_hard_gates"]["global_seam_coordinate_delta_m"], 0.0)

    def test_15_no_blender_module_was_imported(self) -> None:
        self.assertNotIn("bpy", sys.modules)
        self.assertNotIn("bmesh", sys.modules)

    def test_16_truth_does_not_overclaim(self) -> None:
        truth = self.config["truth"]
        for name in (
            "attempt46_blender_execution_performed",
            "attempt46_source_domain_mapping_performed",
            "attempt46_candidate_feasibility_proven",
            "attempt46_triangulation_performed",
            "attempt46_reconstruction_performed",
            "attempt46_body_mutation_performed",
            "attempt46_render_reached",
            "attempt46_blend_saved",
            "runtime_changed",
            "executable_body_repair_justified",
            "body_repair_proven",
            "owner_approval_claimed",
        ):
            self.assertFalse(truth[name], name)

    def test_17_config_is_json_and_worker_is_python(self) -> None:
        self.assertEqual(json.loads(CONFIG.read_text(encoding="utf-8")), self.config)
        ast.parse(WORKER.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
