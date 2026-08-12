"""Static-only tests for Attempt 42 shared-obstruction source-star proof."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools/blender_diagnose_kira_r24_blackproject_shared_obstruction_star_attempt42.py"
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT42_CONFIG.json"
)
CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/PREFLIGHT/"
    "ATTEMPT_42_STATIC_CHECKPOINT.md"
)
ATTEMPT41_INTEGRITY = ROOT / (
    "RecoverySprint/continuation_20260808/attempt41_external_pre_post_integrity.json"
)
AUDIT02 = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/PREFLIGHT/"
    "ATTEMPT_41_INDEPENDENT_AUDIT_02_PASS.md"
)
RUNTIME_CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "ATTEMPT41_RUNTIME_OBSTRUCTION_STAR_FAILURE_CHECKPOINT.md"
)
EXISTING_CACHE = ROOT / (
    "tools/__pycache__/"
    "blender_diagnose_kira_r24_blackproject_wider_source_domain_attempt40.cpython-313.pyc"
)
FORBIDDEN_NEW_CACHES = (
    ROOT / "tools/__pycache__/blender_diagnose_kira_r24_blackproject_wider_source_domain_attempt40.cpython-314.pyc",
    ROOT / "tools/__pycache__/blender_diagnose_kira_r24_blackproject_obstruction_star_attempt41.cpython-313.pyc",
    ROOT / "tools/__pycache__/blender_diagnose_kira_r24_blackproject_obstruction_star_attempt41.cpython-314.pyc",
    ROOT / "tools/__pycache__/blender_diagnose_kira_r24_blackproject_shared_obstruction_star_attempt42.cpython-313.pyc",
    ROOT / "tools/__pycache__/blender_diagnose_kira_r24_blackproject_shared_obstruction_star_attempt42.cpython-314.pyc",
)
EXPECTED_WORKER_SHA256 = (
    "5682f9ca85ca54aad71b699ca12c22e206261c0e7967cb4fca87ca36b0ce2595"
)
EXPECTED_CONFIG_SHA256 = (
    "1d3fb520381926d7cf21ff1be1aeaa64cd9f95c7ffd837f69399f2f7320f21d2"
)
EXPECTED_DERIVED_SHA256 = (
    "9d06725f8707fa46d1ce19db69a983a651cea8a5db06c0a566a583bce1188925"
)
EXPECTED_CACHE_SHA256 = (
    "340ddf1fcbb97d8bd309280061f05dd6a914b79c1e36abce69134501902c162f"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_worker():
    spec = importlib.util.spec_from_file_location("attempt42_static_worker", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Attempt 42 worker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Attempt42StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.before_output_exists = (
            ROOT
            / "RecoverySprint/continuation_20260803/"
            "kira_r24_internal_midpoint_fair_surface/attempt_42"
        ).exists()
        cls.module = load_worker()
        cls.config = cls.module.load_config()
        cls.verified = cls.module.verify_package(cls.config)
        cls.derived = cls.verified["derived_source"]
        cls.evidence = cls.verified["attempt41_evidence"]

    def test_01_exact_package_hashes(self) -> None:
        self.assertEqual(sha256(WORKER), EXPECTED_WORKER_SHA256)
        self.assertEqual(sha256(CONFIG), EXPECTED_CONFIG_SHA256)
        self.assertEqual(self.module.EXPECTED_CONFIG_SHA256, EXPECTED_CONFIG_SHA256)
        self.assertEqual(self.verified["derived_source_sha256"], EXPECTED_DERIVED_SHA256)

    def test_02_import_is_blender_free_and_bytecode_is_disabled(self) -> None:
        self.assertNotIn("bpy", sys.modules)
        self.assertTrue(sys.dont_write_bytecode)
        self.assertFalse(self.before_output_exists)
        self.assertFalse((ROOT / self.config["output"]["root"]).exists())
        for name in ("stdout", "stderr", "external_integrity"):
            self.assertFalse((ROOT / self.config["launch_contract"][name]).exists())

    def test_03_attempt41_final_evidence_is_exact(self) -> None:
        expected = {
            "attempt41_audit02": "42c43570ae3bb061f7681a6fba49b0fe69014e1b8d4b77767624736cf2d30224",
            "attempt41_started": "5b4051a8e4ca1ad1f4ca02d0a655e8f306f16e6c07faed1c14b18ef753cef649",
            "attempt41_diagnostic": "7543d7d0141e2e091861ce66ab005030c4c99b147a2887025d84de0996c0fed6",
            "attempt41_failure": "1dd2e310773865da9f7c0b06b8af12906f1795e7621f4462298ced0d45d24218",
            "attempt41_stdout": "3fdac1af5ea617a5b5d8f4caaa454b38d289d498a1b66d86c4009ba6e4d05803",
            "attempt41_stderr": "04ba849ac212c67f9f7cc7e2e56e40ea41d226a83f64c3df79b88f747cc55964",
            "attempt41_external_integrity": "7cf773fbeb3da7ef41cd1e064f311b4159fa1b2be896246fa40e6a884b743bdb",
            "attempt41_runtime_checkpoint": "8c0bb397f4f00083e7542dbcf76fe431b815aab400bb32bd6a46bbeb5b4a7506",
            "attempt40_generated_cache": EXPECTED_CACHE_SHA256,
        }
        for name, digest in expected.items():
            self.assertEqual(self.verified["records"][name]["sha256"], digest)
        self.assertEqual(sha256(AUDIT02), expected["attempt41_audit02"])
        self.assertEqual(
            sha256(RUNTIME_CHECKPOINT), expected["attempt41_runtime_checkpoint"]
        )

    def test_04_all_277_prior_files_and_existing_cache_are_current(self) -> None:
        integrity = self.evidence["integrity"]
        self.assertEqual(integrity["blender_exit_code"], 1)
        self.assertIsNone(integrity["native_invocation_error"])
        self.assertTrue(integrity["pre_post_exact"])
        self.assertEqual(integrity["before"], integrity["after"])
        self.assertEqual(len(integrity["before"]), 277)
        self.assertFalse(integrity["hidden_bytecode_cache_absent"])
        self.assertEqual(len(self.evidence["protected_records"]), 277)
        self.assertTrue(EXISTING_CACHE.is_file())
        self.assertEqual(EXISTING_CACHE.stat().st_size, 36680)
        self.assertEqual(sha256(EXISTING_CACHE), EXPECTED_CACHE_SHA256)

    def test_05_attempt41_stopped_without_mutation_or_save(self) -> None:
        failure = self.evidence["failure"]
        self.assertEqual(failure["status"], "NO_SAVE_ATTEMPT41_DIAGNOSTIC_STOP_PRESERVED")
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

    def test_06_attempt41_shared_obstruction_is_exact(self) -> None:
        candidate = self.evidence["candidate"]
        self.assertEqual(
            candidate["eligibility_failures"],
            [
                "maximum_chart_boundary_deviation_at_most_0.0011_m",
                "forced_prev_current_next_ear_all_angles_at_least_12_degrees",
            ],
        )
        attribution = candidate["chart"]["boundary_deviation_attribution"]
        self.assertEqual(attribution["row_count"], 46)
        self.assertEqual(attribution["exceeding_row_count"], 6)
        self.assertEqual(attribution["maximum_contributor_boundary_indices"], [15])
        self.assertEqual(attribution["maximum_contributor_mesh_vertex_indices"], [458])
        obstruction = candidate["forced_ear_feasibility"]["obstructions"]
        self.assertEqual(len(obstruction), 1)
        self.assertEqual(obstruction[0]["boundary_index"], 15)
        self.assertEqual(candidate["boundary_cycle_mesh_vertex_indices"][15], 458)
        self.assertEqual(obstruction[0]["fixed_ear_minimum_angle_degrees"], 7.288993277879829)

    def test_07_attempt41_complete_base_identity_is_bound(self) -> None:
        base = self.config["attempt41_base_domain"]
        candidate = self.evidence["candidate"]
        self.assertEqual(base["complete_face_count"], 116)
        self.assertEqual(base["complete_face_indices_sha256"], candidate["face_indices_sha256"])
        self.assertEqual(base["complete_vertex_count"], 82)
        self.assertEqual(base["complete_vertex_indices_sha256"], candidate["vertex_indices_sha256"])
        self.assertEqual(base["complete_boundary_edge_count"], 46)
        self.assertEqual(
            base["complete_boundary_cycle_mesh_vertex_indices"],
            candidate["boundary_cycle_mesh_vertex_indices"],
        )
        self.assertEqual(base["complete_boundary_cycle_mesh_vertex_indices"][15], 458)
        self.assertEqual(len(base["added_complete_existing_source_face_indices"]), 28)

    def test_08_exactly_one_shared_source_star_candidate(self) -> None:
        probe = self.config["one_candidate_probe"]
        self.assertEqual(
            probe["candidate"],
            "complete_attempt41_domain_plus_complete_mesh_vertex_star_458",
        )
        self.assertEqual(probe["exact_shared_obstruction_mesh_vertex_index"], 458)
        self.assertTrue(probe["shared_chart_maximum_and_forced_ear_contributor"])
        self.assertTrue(probe["complete_source_mesh_vertex_star_only"])
        self.assertFalse(probe["uniform_face_ring_candidates_allowed"])
        self.assertFalse(probe["alternate_target_sets_allowed"])
        self.assertFalse(probe["coordinate_suppression_allowed"])
        runtime = self.verified["runtime_config"]["source_mesh_diagnostic"]
        self.assertEqual(runtime["targeted_vertex_star_suppression_sets"], [])
        self.assertEqual(runtime["uniform_face_ring_expansions_to_map"], [])

    def test_09_derived_runtime_validator_accepts_exact_config(self) -> None:
        namespace = {
            "__name__": "attempt42_runtime_contract_test",
            "__file__": str(WORKER.resolve()),
            "__builtins__": __builtins__,
        }
        exec(compile(self.derived, str(WORKER) + "::contract", "exec"), namespace, namespace)
        namespace["validate_config"](self.verified["runtime_config"])
        self.assertEqual(
            self.verified["runtime_config"]["status"],
            "STATIC_READ_ONLY_SHARED_OBSTRUCTION_STAR_PROOF_PREPARED_NOT_RUN",
        )

    def test_10_chart_attribution_remains_complete_and_actionable(self) -> None:
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
            '"attempt41_complete_domain_used_only_as_read_only_base"',
        ):
            self.assertIn(token, self.derived)
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
        self.assertIn("complete_attempt41_domain_plus_complete_mesh_vertex_star_458", self.derived)

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
            "attempt42_blender_execution_performed",
            "attempt42_source_domain_mapping_performed",
            "attempt42_candidate_feasibility_proven",
            "attempt42_triangulation_performed",
            "attempt42_reconstruction_performed",
            "attempt42_body_mutation_performed",
            "attempt42_render_reached",
            "attempt42_blend_saved",
            "runtime_changed",
            "executable_body_repair_justified",
            "body_repair_proven",
            "owner_approval_claimed",
        ):
            self.assertFalse(truth[name], name)

    def test_13_checkpoint_wrapper_covers_prior_inventory_and_cache(self) -> None:
        checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        for token in (
            "$priorAttempt41 = Get-Content -LiteralPath $attempt41Integrity -Raw | ConvertFrom-Json",
            "@($priorAttempt41.before).Count -ne 277",
            "foreach ($row in $priorAttempt41.before)",
            "Attempt 42 prior protected file drifted before Blender",
            "$env:PYTHONDONTWRITEBYTECODE = '1'",
            "$expectedRelevantBytecodeCaches",
            "relevant_bytecode_cache_inventory_exact",
            "Attempt 42 relevant bytecode cache inventory drifted",
            "sys.dont_write_bytecode = True",
        ):
            self.assertIn(token, checkpoint)
        prior = json.loads(ATTEMPT41_INTEGRITY.read_text(encoding="utf-8"))
        self.assertTrue(prior["pre_post_exact"])
        self.assertEqual(prior["before"], prior["after"])
        self.assertEqual(len(prior["before"]), 277)

    def test_14_launch_contract_is_one_shot_and_append_only(self) -> None:
        launch = self.config["launch_contract"]
        self.assertTrue(launch["wrapper_unions_attempt41_277_entry_inventory"])
        self.assertTrue(launch["wrapper_verifies_all_attempt41_records_before_blender"])
        self.assertTrue(launch["wrapper_protects_attempt40_generated_cpython313_cache"])
        self.assertTrue(launch["wrapper_refuses_any_new_relevant_worker_cache"])
        self.assertTrue(launch["worker_sets_sys_dont_write_bytecode_before_bound_worker_load"])
        self.assertTrue(launch["create_new_stdout_and_stderr_required"])
        self.assertTrue(launch["create_new_integrity_in_finally_required"])
        self.assertTrue(launch["exactly_one_blender_invocation_required"])
        self.assertTrue(launch["refuse_any_overwrite"])
        self.assertFalse(launch["executed_during_static_preparation"])

    def test_15_static_verification_created_no_output_or_new_cache(self) -> None:
        self.assertFalse((ROOT / self.config["output"]["root"]).exists())
        self.assertFalse(
            (ROOT / self.config["launch_contract"]["external_integrity"]).exists()
        )
        self.assertTrue(EXISTING_CACHE.is_file())
        self.assertEqual(sha256(EXISTING_CACHE), EXPECTED_CACHE_SHA256)
        for cache in FORBIDDEN_NEW_CACHES:
            self.assertFalse(cache.exists(), cache)


if __name__ == "__main__":
    unittest.main()
