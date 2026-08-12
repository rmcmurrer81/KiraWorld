"""Static-only tests for Attempt 43 shared-obstruction source-star proof."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools/blender_diagnose_kira_r24_blackproject_shared_obstruction_star_attempt43.py"
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT43_CONFIG.json"
)
CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/PREFLIGHT/"
    "ATTEMPT_43_STATIC_CHECKPOINT.md"
)
ATTEMPT42_INTEGRITY = ROOT / (
    "RecoverySprint/continuation_20260808/attempt42_external_pre_post_integrity.json"
)
ATTEMPT42_AUDIT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/PREFLIGHT/"
    "ATTEMPT_42_INDEPENDENT_AUDIT_01_PASS.md"
)
ATTEMPT42_RUNTIME_CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "ATTEMPT42_RUNTIME_SHARED_OBSTRUCTION_STAR_FAILURE_CHECKPOINT.md"
)
EXISTING_CACHE = ROOT / (
    "tools/__pycache__/"
    "blender_diagnose_kira_r24_blackproject_wider_source_domain_attempt40.cpython-313.pyc"
)
EXPECTED_WORKER_SHA256 = (
    "91d95ba542aac127a6815cf404aa8767414872cb715f03278956ad3f6f4b83ba"
)
EXPECTED_CONFIG_SHA256 = (
    "b5ffb534fd5e302341673a69f7ba707a579a2a7347c6596862802e9e6904a6f1"
)
EXPECTED_DERIVED_SHA256 = (
    "99fce13f2d6501c6abee894c0031766ce15eed7e8e69f190ed15f6535eddc854"
)
EXPECTED_CACHE_SHA256 = (
    "340ddf1fcbb97d8bd309280061f05dd6a914b79c1e36abce69134501902c162f"
)
RELEVANT_STEMS = (
    "blender_diagnose_kira_r24_blackproject_wider_source_domain_attempt40",
    "blender_diagnose_kira_r24_blackproject_obstruction_star_attempt41",
    "blender_diagnose_kira_r24_blackproject_shared_obstruction_star_attempt42",
    "blender_diagnose_kira_r24_blackproject_shared_obstruction_star_attempt43",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relevant_caches() -> list[Path]:
    cache_dir = ROOT / "tools/__pycache__"
    if not cache_dir.is_dir():
        return []
    return sorted(
        path
        for path in cache_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() == ".pyc"
        and any(path.name.startswith(stem + ".") for stem in RELEVANT_STEMS)
    )


def load_worker():
    spec = importlib.util.spec_from_file_location("attempt43_static_worker", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Attempt 43 worker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Attempt43StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.before_output_exists = (
            ROOT
            / "RecoverySprint/continuation_20260803/"
            "kira_r24_internal_midpoint_fair_surface/attempt_43"
        ).exists()
        cls.cache_before = [
            (str(path.resolve()), path.stat().st_size, sha256(path))
            for path in relevant_caches()
        ]
        cls.module = load_worker()
        cls.config = cls.module.load_config()
        cls.verified = cls.module.verify_package(cls.config)
        cls.derived = cls.verified["derived_source"]
        cls.evidence = cls.verified["attempt42_evidence"]

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

    def test_03_attempt42_complete_package_is_bound_exactly(self) -> None:
        expected = {
            "attempt42_proposal": "f9b3762c6a7445e876b865545bc44eb29b628fe191df46d767fd78651e559e3a",
            "attempt42_config": "1d3fb520381926d7cf21ff1be1aeaa64cd9f95c7ffd837f69399f2f7320f21d2",
            "attempt42_worker": "5682f9ca85ca54aad71b699ca12c22e206261c0e7967cb4fca87ca36b0ce2595",
            "attempt42_test": "14b0084e38457da4954fd2627b62abdc569b31e4717474a802c4afef90df1264",
            "attempt42_checkpoint": "399e2f8d72cf1db80181203f2cb8217b6fe12741a683d1e3e6d1a35d25b7cb9a",
            "attempt42_audit01": "c573ad874acfdb66100d6a48e576353fae80abfbaff3b5a4f0eef9e327e0add3",
            "attempt42_started": "7dc0b826c30fa73128bd556c44261555dda4922a2f0749da9ddded18c430fd6c",
            "attempt42_diagnostic": "99df9d5828f2926ec6baac09613ef044b45929f95e65978b0fd4070ac4664369",
            "attempt42_failure": "03848114cfc0b008a0c0df7d8f578627d451bbb2ddbbd6d7c682e152f6c1b6ce",
            "attempt42_stdout": "40c3acb93c4e7874a11d34b10f3e427a11929e575d99f278329049cfcda34d73",
            "attempt42_stderr": "142d83dd35d1c89080d2ca5f70894eb2eb135275a93ba0f0c4d18fae69d70ad2",
            "attempt42_external_integrity": "9323dff62e5dc68836df3b7099c325f745ca72762c3e9cc413cc161d327abf69",
            "attempt42_runtime_checkpoint": "45e0c1978a648bea569304cfe57af15cfd254780e34a8639c7b25a86c82a2ee5",
            "attempt40_generated_cache": EXPECTED_CACHE_SHA256,
        }
        for name, digest in expected.items():
            self.assertEqual(self.verified["records"][name]["sha256"], digest)
        self.assertEqual(sha256(ATTEMPT42_AUDIT), expected["attempt42_audit01"])
        self.assertEqual(
            sha256(ATTEMPT42_RUNTIME_CHECKPOINT),
            expected["attempt42_runtime_checkpoint"],
        )

    def test_04_all_291_prior_files_and_cache_are_current(self) -> None:
        integrity = self.evidence["integrity"]
        self.assertEqual(integrity["blender_exit_code"], 1)
        self.assertIsNone(integrity["native_invocation_error"])
        self.assertTrue(integrity["pre_post_exact"])
        self.assertEqual(integrity["before"], integrity["after"])
        self.assertEqual(len(integrity["before"]), 291)
        self.assertTrue(integrity["relevant_bytecode_cache_inventory_exact"])
        self.assertEqual(len(self.evidence["protected_records"]), 291)
        self.assertTrue(EXISTING_CACHE.is_file())
        self.assertEqual(EXISTING_CACHE.stat().st_size, 36680)
        self.assertEqual(sha256(EXISTING_CACHE), EXPECTED_CACHE_SHA256)

    def test_05_attempt42_stopped_without_mutation_or_save(self) -> None:
        failure = self.evidence["failure"]
        self.assertEqual(failure["status"], "NO_SAVE_ATTEMPT42_DIAGNOSTIC_STOP_PRESERVED")
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

    def test_06_attempt42_shared_obstruction_is_exact(self) -> None:
        candidate = self.evidence["candidate"]
        self.assertEqual(
            candidate["eligibility_failures"],
            [
                "maximum_chart_boundary_deviation_at_most_0.0011_m",
                "forced_prev_current_next_ear_all_angles_at_least_12_degrees",
            ],
        )
        attribution = candidate["chart"]["boundary_deviation_attribution"]
        self.assertEqual(attribution["row_count"], 48)
        self.assertEqual(attribution["exceeding_row_count"], 6)
        self.assertEqual(attribution["maximum_contributor_boundary_indices"], [16])
        self.assertEqual(attribution["maximum_contributor_mesh_vertex_indices"], [463])
        obstruction = candidate["forced_ear_feasibility"]["obstructions"]
        self.assertEqual(len(obstruction), 1)
        self.assertEqual(obstruction[0]["boundary_index"], 16)
        self.assertEqual(candidate["boundary_cycle_mesh_vertex_indices"][16], 463)
        self.assertEqual(
            obstruction[0]["fixed_ear_minimum_angle_degrees"],
            10.704972662246028,
        )

    def test_07_attempt42_complete_base_identity_is_bound(self) -> None:
        base = self.config["attempt42_base_domain"]
        candidate = self.evidence["candidate"]
        self.assertEqual(base["complete_face_count"], 120)
        self.assertEqual(base["complete_face_indices_sha256"], candidate["face_indices_sha256"])
        self.assertEqual(base["complete_vertex_count"], 85)
        self.assertEqual(base["complete_vertex_indices_sha256"], candidate["vertex_indices_sha256"])
        self.assertEqual(base["complete_boundary_edge_count"], 48)
        self.assertEqual(
            base["complete_boundary_cycle_mesh_vertex_indices"],
            candidate["boundary_cycle_mesh_vertex_indices"],
        )
        self.assertEqual(base["complete_boundary_cycle_mesh_vertex_indices"][16], 463)
        self.assertEqual(len(base["added_complete_existing_source_face_indices"]), 32)

    def test_08_exactly_one_shared_source_star_candidate(self) -> None:
        probe = self.config["one_candidate_probe"]
        self.assertEqual(
            probe["candidate"],
            "complete_attempt42_domain_plus_complete_mesh_vertex_star_463",
        )
        self.assertEqual(probe["exact_shared_obstruction_mesh_vertex_index"], 463)
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
            "__name__": "attempt43_runtime_contract_test",
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
            '"attempt42_complete_domain_used_only_as_read_only_base"',
        ):
            self.assertIn(token, self.derived)
        attribution = self.config["chart_attribution_contract"]
        self.assertEqual(attribution["maximum_allowed_boundary_deviation_m"], 0.0011)
        self.assertFalse(attribution["attribution_authorizes_vertex_movement"])
        self.assertFalse(attribution["attribution_authorizes_gate_change"])

    def test_11_derived_mapper_contains_no_mutation_or_output_operation(self) -> None:
        ast.parse(self.derived)
        for token in (
            "bpy.ops.wm.save",
            "bpy.ops.render",
            "bpy.ops.export",
            "bpy.ops.object.join",
            "bmesh.ops.delete",
            "to_mesh(",
        ):
            self.assertNotIn(token, self.derived)
        self.assertIn("bm.verts[obstruction_vertex_index].link_faces", self.derived)
        self.assertIn("ring_rows = []", self.derived)
        self.assertIn("complete_attempt42_domain_plus_complete_mesh_vertex_star_463", self.derived)

    def test_12_scope_and_truth_forbid_execution_and_repair_claims(self) -> None:
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
            self.assertFalse(self.config["scope"][name], name)
        for name in (
            "attempt43_blender_execution_performed",
            "attempt43_source_domain_mapping_performed",
            "attempt43_candidate_feasibility_proven",
            "attempt43_triangulation_performed",
            "attempt43_reconstruction_performed",
            "attempt43_body_mutation_performed",
            "attempt43_render_reached",
            "attempt43_blend_saved",
            "runtime_changed",
            "executable_body_repair_justified",
            "body_repair_proven",
            "owner_approval_claimed",
        ):
            self.assertFalse(self.config["truth"][name], name)

    def test_13_checkpoint_wrapper_covers_prior_inventory_and_cache(self) -> None:
        checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        for token in (
            "$priorAttempt42 = Get-Content -LiteralPath $attempt42Integrity -Raw | ConvertFrom-Json",
            "@($priorAttempt42.before).Count -ne 291",
            "foreach ($row in $priorAttempt42.before)",
            "Attempt 43 prior protected file drifted before Blender",
            "$env:PYTHONDONTWRITEBYTECODE = '1'",
            "$expectedRelevantBytecodeCaches",
            "relevant_bytecode_cache_inventory_exact",
            "Attempt 43 relevant bytecode cache inventory drifted",
            "sys.dont_write_bytecode = True",
        ):
            self.assertIn(token, checkpoint)
        prior = json.loads(ATTEMPT42_INTEGRITY.read_text(encoding="utf-8"))
        self.assertTrue(prior["pre_post_exact"])
        self.assertEqual(prior["before"], prior["after"])
        self.assertEqual(len(prior["before"]), 291)

    def test_14_launch_contract_is_one_shot_and_append_only(self) -> None:
        launch = self.config["launch_contract"]
        self.assertTrue(launch["wrapper_unions_attempt42_291_entry_inventory"])
        self.assertTrue(launch["wrapper_verifies_all_attempt42_records_before_blender"])
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
        self.assertFalse((ROOT / self.config["launch_contract"]["external_integrity"]).exists())
        self.assertTrue(EXISTING_CACHE.is_file())
        self.assertEqual(sha256(EXISTING_CACHE), EXPECTED_CACHE_SHA256)
        cache_after = [
            (str(path.resolve()), path.stat().st_size, sha256(path))
            for path in relevant_caches()
        ]
        self.assertEqual(cache_after, self.cache_before)
        self.assertEqual(cache_after, [(str(EXISTING_CACHE.resolve()), 36680, EXPECTED_CACHE_SHA256)])


if __name__ == "__main__":
    unittest.main()
