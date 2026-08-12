"""Static-only acceptance for R24 Attempt 45.

This suite must never launch Blender. It verifies the exact preserved
Attempt 44 evidence, the one compound candidate contract, and the derived
read-only source before a separate independent audit may authorize execution.
"""

from __future__ import annotations

import ast
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
    "compound_local_blocker_stars_attempt45.py"
)
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT45_CONFIG.json"
)
OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/attempt_45"
)
EXTERNAL_OUTPUTS = (
    ROOT / "RecoverySprint/continuation_20260808/attempt45_blender_stdout.log",
    ROOT / "RecoverySprint/continuation_20260808/attempt45_blender_stderr.log",
    ROOT
    / "RecoverySprint/continuation_20260808/attempt45_external_pre_post_integrity.json",
)
EXPECTED_WORKER_SHA256 = (
    "98801efef8fd8c7118b25e9475b827193869098b4156456f645004cc14212784"
)
EXPECTED_CONFIG_SHA256 = (
    "41144f0b470c078312cc35aae6368dd75c0a1b1079b0a56b6808f81a1fd4117b"
)
EXPECTED_DERIVED_SHA256 = (
    "481dd0105147edef6f39b2f682f2def99388355c325429b02e5d11e214c11ccf"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_worker():
    spec = importlib.util.spec_from_file_location("attempt45_static_test", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("Attempt 45 static worker could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Attempt45StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.before_caches = sorted(
            str(path.resolve())
            for path in (ROOT / "tools/__pycache__").glob("*attempt45*.pyc")
        ) if (ROOT / "tools/__pycache__").exists() else []
        cls.module = load_worker()
        cls.config = cls.module.load_config()
        cls.verified = cls.module.verify_package(cls.config)

    @classmethod
    def tearDownClass(cls) -> None:
        after = sorted(
            str(path.resolve())
            for path in (ROOT / "tools/__pycache__").glob("*attempt45*.pyc")
        ) if (ROOT / "tools/__pycache__").exists() else []
        if after != cls.before_caches:
            raise AssertionError("Attempt 45 static suite created worker bytecode")

    def test_01_exact_outer_hashes(self) -> None:
        self.assertEqual(sha256_file(WORKER), EXPECTED_WORKER_SHA256)
        self.assertEqual(sha256_file(CONFIG), EXPECTED_CONFIG_SHA256)

    def test_02_identity_and_output_absence(self) -> None:
        self.assertEqual(self.config["attempt_id"], "attempt_45")
        self.assertEqual(
            self.config["status"],
            "STATIC_READ_ONLY_COMPOUND_LOCAL_BLOCKER_STARS_PROOF_PREPARED_NOT_RUN",
        )
        self.assertFalse(OUTPUT.exists())
        self.assertTrue(all(not path.exists() for path in EXTERNAL_OUTPUTS))

    def test_03_scope_is_read_only_and_one_candidate(self) -> None:
        scope = self.config["scope"]
        self.assertTrue(scope["exact_one_compound_blocker_vertex_star_mapping_allowed"])
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

    def test_04_exact_blocker_probe(self) -> None:
        probe = self.config["one_candidate_probe"]
        self.assertEqual(
            probe["candidate"],
            "complete_attempt44_domain_plus_complete_mesh_vertex_stars_218_508",
        )
        self.assertEqual(probe["required_complete_source_mesh_vertex_stars"], [241, 218, 508])
        self.assertEqual(probe["new_compound_blocker_source_mesh_vertex_stars"], [218, 508])
        self.assertEqual(probe["attempt44_chart_maximum_mesh_vertex_index"], 218)
        self.assertEqual(probe["attempt44_forced_ear_obstruction_mesh_vertex_index"], 508)

    def test_05_attempt44_evidence_is_exact(self) -> None:
        evidence = self.verified["attempt44_evidence"]
        self.assertEqual(len(evidence["protected_records"]), 317)
        self.assertEqual(evidence["integrity"]["before"], evidence["integrity"]["after"])
        self.assertTrue(evidence["integrity"]["pre_post_exact"])
        self.assertTrue(evidence["integrity"]["relevant_bytecode_cache_inventory_exact"])
        self.assertEqual(evidence["integrity"]["blender_exit_code"], 1)
        self.assertIsNone(evidence["integrity"]["native_invocation_error"])

    def test_06_attempt44_failure_metrics_are_exact(self) -> None:
        result = self.config["attempt44_runtime_result"]
        self.assertEqual((result["face_count"], result["vertex_count"]), (127, 90))
        self.assertEqual((result["edge_count"], result["boundary_edge_count"]), (216, 51))
        self.assertEqual(result["chart_exceeding_row_count"], 11)
        self.assertEqual(result["chart_maximum_contributor_mesh_vertex_indices"], [218])
        self.assertEqual(result["forced_ear_obstruction_mesh_vertex_indices"], [508])
        self.assertAlmostEqual(
            result["maximum_chart_boundary_deviation_m"],
            0.0020634647516999394,
            places=15,
        )
        self.assertAlmostEqual(
            result["forced_ear_obstruction_minimum_angle_degrees"][0],
            11.646591879879606,
            places=12,
        )

    def test_07_derived_source_hash_is_bound(self) -> None:
        self.assertEqual(
            self.verified["derived_source_sha256"], EXPECTED_DERIVED_SHA256
        )
        self.assertEqual(
            hashlib.sha256(self.verified["derived_source"].encode("utf-8")).hexdigest(),
            EXPECTED_DERIVED_SHA256,
        )

    def test_08_derived_source_has_one_compound_mapping(self) -> None:
        source = self.verified["derived_source"]
        self.assertEqual(
            source.count(
                '"complete_attempt44_domain_plus_complete_mesh_vertex_stars_218_508"'
            ),
            1,
        )
        self.assertEqual(source.count('"compound_source_star_rows"'), 1)
        self.assertEqual(source.count('"one_indivisible_compound_candidate"'), 1)
        self.assertIn(
            'probe["new_compound_blocker_source_mesh_vertex_stars"]', source
        )
        self.assertNotIn("uniform_face_ring_expansions_to_map =", source)

    def test_09_derived_source_reverifies_attempt44(self) -> None:
        source = self.verified["derived_source"]
        self.assertIn('"attempt44_runtime_result"', source)
        self.assertIn('"attempt44_complete_candidate_reverified"', source)
        self.assertIn('"attempt44_complete_candidate_used_only_as_read_only_base"', source)
        self.assertIn("previous_checks", source)
        self.assertIn("Attempt 45 exact candidate or blockers drifted", source)

    def test_10_derived_ast_has_no_forbidden_mutation_calls(self) -> None:
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

    def test_11_runtime_config_retains_hard_gates(self) -> None:
        runtime = self.verified["runtime_config"]
        self.assertEqual(runtime["attempt_id"], "attempt_45")
        self.assertEqual(runtime["diagnosis"]["required_minimum_angle_degrees"], 12.0)
        self.assertEqual(
            runtime["source_identity_contract"]["maximum_local_chart_boundary_deviation_m"],
            0.0011,
        )
        self.assertEqual(runtime["unchanged_hard_gates"]["global_seam_vertex_count"], 34)
        self.assertEqual(runtime["unchanged_hard_gates"]["global_seam_coordinate_delta_m"], 0.0)

    def test_12_prior_files_and_cache_are_still_exact(self) -> None:
        records = self.verified["records"]
        self.assertEqual(records["attempt44_diagnostic"]["sha256"],
                         "429b6f70e65af5aaf976f49e558c87cc06fbd791c9e994fda1a8a241a9adf89d")
        cache = self.verified["attempt44_evidence"]["cache_record"]
        self.assertEqual(cache["bytes"], 36680)
        self.assertEqual(cache["sha256"],
                         "340ddf1fcbb97d8bd309280061f05dd6a914b79c1e36abce69134501902c162f")

    def test_13_no_blender_module_was_imported(self) -> None:
        self.assertNotIn("bpy", sys.modules)
        self.assertNotIn("bmesh", sys.modules)

    def test_14_truth_does_not_overclaim(self) -> None:
        truth = self.config["truth"]
        for name in (
            "attempt45_blender_execution_performed",
            "attempt45_source_domain_mapping_performed",
            "attempt45_candidate_feasibility_proven",
            "attempt45_triangulation_performed",
            "attempt45_reconstruction_performed",
            "attempt45_body_mutation_performed",
            "attempt45_render_reached",
            "attempt45_blend_saved",
            "runtime_changed",
            "executable_body_repair_justified",
            "body_repair_proven",
            "owner_approval_claimed",
        ):
            self.assertFalse(truth[name], name)

    def test_15_config_is_json_and_worker_is_python(self) -> None:
        self.assertEqual(json.loads(CONFIG.read_text(encoding="utf-8")), self.config)
        ast.parse(WORKER.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
