"""Static-only tests for Attempt 41 obstruction-star chart attribution."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools/blender_diagnose_kira_r24_blackproject_obstruction_star_attempt41.py"
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT41_CONFIG.json"
)
CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/PREFLIGHT/"
    "ATTEMPT_41_STATIC_CHECKPOINT.md"
)
ATTEMPT40_INTEGRITY = ROOT / (
    "RecoverySprint/continuation_20260808/attempt40_external_pre_post_integrity.json"
)
AUDIT01 = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/PREFLIGHT/"
    "ATTEMPT_41_INDEPENDENT_AUDIT_01_FAILURE.md"
)
BYTECODE_CACHES = (
    ROOT / "tools/__pycache__/blender_diagnose_kira_r24_blackproject_obstruction_star_attempt41.cpython-314.pyc",
    ROOT / "tools/__pycache__/blender_diagnose_kira_r24_blackproject_obstruction_star_attempt41.cpython-313.pyc",
    ROOT / "tools/__pycache__/blender_diagnose_kira_r24_blackproject_wider_source_domain_attempt40.cpython-313.pyc",
)
EXPECTED_WORKER_SHA256 = (
    "e74d73a723aa2dd0dff5fd4f329e57878ac7a2a0f686d8140060d63116e72d81"
)
EXPECTED_CONFIG_SHA256 = (
    "eb9f92a2e7bc4d97494394b5e90e49dfb527b192b290e4cd96d0b3716152535d"
)
EXPECTED_DERIVED_SHA256 = (
    "066392ee3d5066f7c12a8fa93b75eb8a211b32b1c9f3fd9221920b7313f98da9"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_worker():
    spec = importlib.util.spec_from_file_location("attempt41_static_worker", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Attempt 41 worker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Attempt41StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.before_output_exists = (
            ROOT
            / "RecoverySprint/continuation_20260803/"
            "kira_r24_internal_midpoint_fair_surface/attempt_41"
        ).exists()
        cls.module = load_worker()
        cls.config = cls.module.load_config()
        cls.verified = cls.module.verify_package(cls.config)
        cls.derived = cls.verified["derived_source"]
        cls.evidence = cls.verified["attempt40_evidence"]

    def test_01_exact_package_hashes(self) -> None:
        self.assertEqual(sha256(WORKER), EXPECTED_WORKER_SHA256)
        self.assertEqual(sha256(CONFIG), EXPECTED_CONFIG_SHA256)
        self.assertEqual(self.module.EXPECTED_CONFIG_SHA256, EXPECTED_CONFIG_SHA256)
        self.assertEqual(self.verified["derived_source_sha256"], EXPECTED_DERIVED_SHA256)

    def test_02_import_is_blender_free_and_outputs_are_absent(self) -> None:
        self.assertNotIn("bpy", sys.modules)
        self.assertFalse(self.before_output_exists)
        self.assertFalse((ROOT / self.config["output"]["root"]).exists())
        for name in ("stdout", "stderr", "external_integrity"):
            self.assertFalse((ROOT / self.config["launch_contract"][name]).exists())
        for cache in BYTECODE_CACHES:
            self.assertFalse(cache.exists(), cache)

    def test_03_attempt40_runtime_files_are_exact(self) -> None:
        expected = {
            "attempt40_started": "a8ebef69fae17d401a6711c31b65e36cbfe0237bcb631cbe67006191417ac13c",
            "attempt40_diagnostic": "004b0c31616dc54e0e9583a8bb6f5150eac78a8828e76269912428f4287dadd0",
            "attempt40_failure": "0f892d6ebd263abeb0ce5db3c921e386929d9edb41da9eabc60ee8043567ffe0",
            "attempt40_stdout": "c50b252c95a6c33cd35a4d18dd1e8c304b97c96b6d85cf622f7016d00a09fc1a",
            "attempt40_stderr": "16e03eca559f40ba3f5489f7716ac04987e660f18ad6a8fcd245765e5061dfe9",
            "attempt40_external_integrity": "b44fe9a98f7f1316adb7aab1f25939a060ca80983a76755e6c9d1c980d10a337",
        }
        for name, digest in expected.items():
            self.assertEqual(self.verified["records"][name]["sha256"], digest)

    def test_04_all_265_attempt40_protected_files_are_current(self) -> None:
        integrity = self.evidence["integrity"]
        self.assertEqual(integrity["blender_exit_code"], 1)
        self.assertIsNone(integrity["native_invocation_error"])
        self.assertTrue(integrity["pre_post_exact"])
        self.assertEqual(integrity["before"], integrity["after"])
        self.assertEqual(len(integrity["before"]), 265)
        records = self.evidence["protected_records"]
        self.assertEqual(len(records), 265)
        self.assertEqual(len({row["path"] for row in records}), 265)

    def test_05_attempt40_stopped_without_mutation_or_save(self) -> None:
        failure = self.evidence["failure"]
        self.assertEqual(failure["status"], "NO_SAVE_ATTEMPT40_DIAGNOSTIC_STOP_PRESERVED")
        self.assertTrue(failure["diagnostic_exists"])
        for name in (
            "mesh_mutated",
            "body_mutated",
            "render_reached",
            "blend_saved",
            "runtime_changed",
        ):
            self.assertFalse(failure[name], name)
        truth = self.evidence["diagnostic"]["truth"]
        for name in (
            "replacement_boundary_repair_applied",
            "triangulation_performed",
            "mesh_mutated",
            "body_mutated",
            "render_reached",
            "blend_saved",
            "runtime_changed",
            "necessary_candidate_is_sufficient_repair_proof",
            "executable_body_repair_justified",
        ):
            self.assertFalse(truth[name], name)

    def test_06_attempt40_exact_two_failures_and_obstruction(self) -> None:
        candidate = self.evidence["candidate"]
        self.assertEqual(
            candidate["eligibility_failures"],
            [
                "maximum_chart_boundary_deviation_at_most_0.0011_m",
                "forced_prev_current_next_ear_all_angles_at_least_12_degrees",
            ],
        )
        self.assertEqual(
            candidate["chart"]["maximum_absolute_boundary_deviation_m"],
            0.001111660800233949,
        )
        obstruction = candidate["forced_ear_feasibility"]["obstructions"]
        self.assertEqual(len(obstruction), 1)
        self.assertEqual(obstruction[0]["boundary_index"], 14)
        self.assertEqual(candidate["boundary_cycle_mesh_vertex_indices"][14], 459)
        self.assertEqual(
            obstruction[0]["fixed_ear_minimum_angle_degrees"],
            7.335720737992295,
        )

    def test_07_attempt40_complete_base_identity_is_bound(self) -> None:
        base = self.config["attempt40_base_domain"]
        candidate = self.evidence["candidate"]
        self.assertEqual(base["complete_face_count"], 112)
        self.assertEqual(base["complete_face_indices_sha256"], candidate["face_indices_sha256"])
        self.assertEqual(base["complete_vertex_count"], 79)
        self.assertEqual(base["complete_vertex_indices_sha256"], candidate["vertex_indices_sha256"])
        self.assertEqual(base["complete_boundary_edge_count"], 44)
        self.assertEqual(
            base["complete_boundary_cycle_mesh_vertex_indices"],
            candidate["boundary_cycle_mesh_vertex_indices"],
        )
        self.assertEqual(base["complete_boundary_cycle_mesh_vertex_indices"][14], 459)

    def test_08_exactly_one_source_star_candidate_and_no_alternate(self) -> None:
        probe = self.config["one_candidate_probe"]
        self.assertEqual(
            probe["candidate"],
            "complete_attempt40_domain_plus_complete_mesh_vertex_star_459",
        )
        self.assertEqual(probe["exact_obstruction_mesh_vertex_index"], 459)
        self.assertTrue(probe["complete_source_mesh_vertex_star_only"])
        self.assertFalse(probe["uniform_face_ring_candidates_allowed"])
        self.assertFalse(probe["alternate_target_sets_allowed"])
        self.assertFalse(probe["coordinate_suppression_allowed"])
        runtime = self.verified["runtime_config"]["source_mesh_diagnostic"]
        self.assertEqual(runtime["targeted_vertex_star_suppression_sets"], [])
        self.assertEqual(runtime["uniform_face_ring_expansions_to_map"], [])

    def test_09_derived_runtime_validator_accepts_exact_config(self) -> None:
        namespace = {
            "__name__": "attempt41_runtime_contract_test",
            "__file__": str(WORKER.resolve()),
            "__builtins__": __builtins__,
        }
        exec(compile(self.derived, str(WORKER) + "::contract", "exec"), namespace, namespace)
        namespace["validate_config"](self.verified["runtime_config"])
        self.assertEqual(
            self.verified["runtime_config"]["status"],
            "STATIC_READ_ONLY_DOMAIN_ATTRIBUTION_PROOF_PREPARED_NOT_RUN",
        )

    def test_10_chart_attribution_is_per_boundary_and_actionable(self) -> None:
        for token in (
            '"boundary_deviation_attribution"',
            '"boundary_index"',
            '"mesh_vertex_index"',
            '"signed_deviation_m"',
            '"absolute_deviation_m"',
            '"absolute_deviation_rank"',
            '"is_maximum_contributor"',
            '"maximum_allowed_deviation_m"',
            '"exceeds_maximum_allowed_deviation"',
            '"exceeding_rows"',
            '"attempt40_complete_domain_used_only_as_read_only_base"',
        ):
            self.assertIn(token, self.derived)
        self.assertNotIn(
            '"attempt41_complete_domain_used_only_as_read_only_base"', self.derived
        )
        attribution = self.config["chart_attribution_contract"]
        self.assertEqual(attribution["maximum_allowed_boundary_deviation_m"], 0.0011)
        self.assertFalse(attribution["attribution_authorizes_vertex_movement"])
        self.assertFalse(attribution["attribution_authorizes_gate_change"])

    def test_11_derived_mapper_contains_no_mutation_or_output_operation(self) -> None:
        ast.parse(self.derived)
        forbidden = (
            "bpy.ops.wm.save",
            "bpy.ops.render",
            "bpy.ops.export",
            "bpy.ops.object.join",
            "bmesh.ops.delete",
            "to_mesh(",
        )
        for token in forbidden:
            self.assertNotIn(token, self.derived)
        self.assertIn("bm.verts[obstruction_vertex_index].link_faces", self.derived)
        self.assertIn("ring_rows = []", self.derived)

    def test_12_scope_and_truth_forbid_execution_and_repair_claims(self) -> None:
        scope = self.config["scope"]
        for name in (
            "source_file_mutation_allowed",
            "prior_evidence_mutation_allowed",
            "body_geometry_mutation_allowed",
            "patch_geometry_mutation_allowed",
            "triangulation_allowed",
            "reconstruction_allowed",
            "render_allowed",
            "blend_save_allowed",
            "export_allowed",
            "runtime_activation_allowed",
            "uniform_face_ring_allowed",
            "automatic_alternate_candidate_allowed",
            "automatic_retry_allowed",
        ):
            self.assertFalse(scope[name], name)
        truth = self.config["truth"]
        for name in (
            "attempt41_blender_execution_performed",
            "attempt41_source_domain_mapping_performed",
            "attempt41_candidate_feasibility_proven",
            "attempt41_triangulation_performed",
            "attempt41_reconstruction_performed",
            "attempt41_body_mutation_performed",
            "attempt41_render_reached",
            "attempt41_blend_saved",
            "runtime_changed",
            "executable_body_repair_justified",
            "body_repair_proven",
            "owner_approval_claimed",
        ):
            self.assertFalse(truth[name], name)

    def test_13_checkpoint_wrapper_covers_attempt40_inventory(self) -> None:
        checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        for token in (
            "$priorAttempt40 = Get-Content -LiteralPath $attempt40Integrity -Raw | ConvertFrom-Json",
            "@($priorAttempt40.before).Count -ne 265",
            "foreach ($row in $priorAttempt40.before)",
            "Attempt 41 prior protected file drifted before Blender",
            "Attempt 41 prior protected path is absent from target set",
            "$env:PYTHONDONTWRITEBYTECODE = '1'",
            "$hiddenBytecodeCaches",
            "hidden_bytecode_cache_absent",
            "Attempt 41 hidden bytecode cache appeared",
        ):
            self.assertIn(token, checkpoint)
        self.assertEqual(sha256(AUDIT01), "52496286512038f90bdb035aff2d984ae72774e5fad02c8d529f236505c307d1")
        prior = json.loads(ATTEMPT40_INTEGRITY.read_text(encoding="utf-8"))
        self.assertTrue(prior["pre_post_exact"])
        self.assertEqual(prior["before"], prior["after"])
        self.assertEqual(len(prior["before"]), 265)

    def test_14_launch_contract_is_one_shot_and_append_only(self) -> None:
        launch = self.config["launch_contract"]
        self.assertTrue(launch["wrapper_unions_attempt40_265_entry_inventory"])
        self.assertTrue(launch["wrapper_verifies_all_attempt40_records_before_blender"])
        self.assertTrue(launch["create_new_stdout_and_stderr_required"])
        self.assertTrue(launch["create_new_integrity_in_finally_required"])
        self.assertTrue(launch["exactly_one_blender_invocation_required"])
        self.assertTrue(launch["refuse_any_overwrite"])
        self.assertTrue(launch["wrapper_keeps_python_bytecode_disabled_through_blender_and_integrity"])
        self.assertTrue(launch["wrapper_refuses_attempt41_cpython314_cache"])
        self.assertTrue(launch["wrapper_refuses_attempt41_cpython313_cache"])
        self.assertTrue(launch["wrapper_refuses_attempt40_cpython313_cache"])
        self.assertTrue(launch["external_integrity_records_hidden_bytecode_cache_absence"])
        self.assertFalse(launch["executed_during_static_preparation"])

    def test_15_static_verification_created_no_attempt41_output(self) -> None:
        self.assertFalse((ROOT / self.config["output"]["root"]).exists())
        self.assertFalse(
            (ROOT / self.config["launch_contract"]["external_integrity"]).exists()
        )
        for cache in BYTECODE_CACHES:
            self.assertFalse(cache.exists(), cache)


if __name__ == "__main__":
    unittest.main()
