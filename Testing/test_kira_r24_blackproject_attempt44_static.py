"""Static-only tests for Attempt 44 chart-maximum source-star proof."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools/blender_diagnose_kira_r24_blackproject_chart_maximum_star_attempt44.py"
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT44_CONFIG.json"
)
CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/PREFLIGHT/"
    "ATTEMPT_44_STATIC_CHECKPOINT.md"
)
ATTEMPT43_INTEGRITY = ROOT / (
    "RecoverySprint/continuation_20260808/attempt43_external_pre_post_integrity.json"
)
ATTEMPT43_AUDIT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/PREFLIGHT/"
    "ATTEMPT_43_INDEPENDENT_AUDIT_01_PASS.md"
)
ATTEMPT43_RUNTIME_CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "ATTEMPT43_RUNTIME_SHARED_OBSTRUCTION_STAR_FAILURE_CHECKPOINT.md"
)
EXISTING_CACHE = ROOT / (
    "tools/__pycache__/"
    "blender_diagnose_kira_r24_blackproject_wider_source_domain_attempt40.cpython-313.pyc"
)
EXPECTED_WORKER_SHA256 = (
    "2e7fe7f3fd841e8a0d5330dcb5481ebaabfd3a8a59cfc957dd3e780e016f0245"
)
EXPECTED_CONFIG_SHA256 = (
    "78bf8b2f44460b0091f72eb6115971da6bb592acb205e036259f5fece0c193b3"
)
EXPECTED_DERIVED_SHA256 = (
    "216eb9b56dbb8ee768167756e2590d42b33f692d5a275013fed32a970c24613b"
)
EXPECTED_CACHE_SHA256 = (
    "340ddf1fcbb97d8bd309280061f05dd6a914b79c1e36abce69134501902c162f"
)
RELEVANT_STEMS = (
    "blender_diagnose_kira_r24_blackproject_wider_source_domain_attempt40",
    "blender_diagnose_kira_r24_blackproject_obstruction_star_attempt41",
    "blender_diagnose_kira_r24_blackproject_shared_obstruction_star_attempt42",
    "blender_diagnose_kira_r24_blackproject_shared_obstruction_star_attempt43",
    "blender_diagnose_kira_r24_blackproject_chart_maximum_star_attempt44",
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
    spec = importlib.util.spec_from_file_location("attempt44_static_worker", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Attempt 44 worker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Attempt44StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.output = ROOT / (
            "RecoverySprint/continuation_20260803/"
            "kira_r24_internal_midpoint_fair_surface/attempt_44"
        )
        cls.before_output_exists = cls.output.exists()
        cls.cache_before = [
            (str(path.resolve()), path.stat().st_size, sha256(path))
            for path in relevant_caches()
        ]
        cls.module = load_worker()
        cls.config = cls.module.load_config()
        cls.verified = cls.module.verify_package(cls.config)
        cls.derived = cls.verified["derived_source"]
        cls.evidence = cls.verified["attempt43_evidence"]

    def test_01_exact_package_hashes(self) -> None:
        self.assertEqual(sha256(WORKER), EXPECTED_WORKER_SHA256)
        self.assertEqual(sha256(CONFIG), EXPECTED_CONFIG_SHA256)
        self.assertEqual(self.module.EXPECTED_CONFIG_SHA256, EXPECTED_CONFIG_SHA256)
        self.assertEqual(self.verified["derived_source_sha256"], EXPECTED_DERIVED_SHA256)

    def test_02_import_is_blender_free_and_bytecode_is_disabled(self) -> None:
        self.assertNotIn("bpy", sys.modules)
        self.assertTrue(sys.dont_write_bytecode)
        self.assertFalse(self.before_output_exists)
        self.assertFalse(self.output.exists())
        for name in ("stdout", "stderr", "external_integrity"):
            self.assertFalse((ROOT / self.config["launch_contract"][name]).exists())

    def test_03_attempt43_complete_package_is_bound_exactly(self) -> None:
        expected = {
            "attempt43_proposal": "7d79aaf72242783d8faebdc923652742ae9886cc9360e87c7f92121924ddc815",
            "attempt43_config": "b5ffb534fd5e302341673a69f7ba707a579a2a7347c6596862802e9e6904a6f1",
            "attempt43_worker": "91d95ba542aac127a6815cf404aa8767414872cb715f03278956ad3f6f4b83ba",
            "attempt43_test": "f343e65f3d48353f9648d0f4a82cbead472ed676dc2b81625ebb64e8a24089de",
            "attempt43_checkpoint": "fe5af9f3cfb5d79b7c1ccc5f72f6f71ce6bdd3ce285b004e5a5d68ff5b8c98cd",
            "attempt43_audit01": "6a65ade4c884b54ef5c42fe2f5a1732d06c784576c37a9ec66c7a465f39492ac",
            "attempt43_started": "89683c7df4f36710eca950485e0ca6d5fc780305b6a427f263a3584095f55d96",
            "attempt43_diagnostic": "fd887f73e20809ca311c3c9893959a01747f347213a052a76e63e86f9ff12329",
            "attempt43_failure": "39d2f270f3ec2d816a08caef3fe65459dae69e5e28b9b4f3bed39d447381dd55",
            "attempt43_stdout": "88be65156b7e7588ba20877d62c39287c24da17cf7f11c8aa75797bf4c808fc4",
            "attempt43_stderr": "db7c8025021cd3877c1db23012bb8d337b84025bc64f129f32b0006bdab87c41",
            "attempt43_external_integrity": "1f08ce1c0a28cd93b880b0a6fa0bbe782a540588fdab2f2caf60944fd262f481",
            "attempt43_runtime_checkpoint": "bfb1f72a7afe1c8723e20076ef4953d2f004222db0aa6650263b8a7b76168e08",
            "attempt40_generated_cache": EXPECTED_CACHE_SHA256,
        }
        for name, digest in expected.items():
            self.assertEqual(self.verified["records"][name]["sha256"], digest)
        self.assertEqual(sha256(ATTEMPT43_AUDIT), expected["attempt43_audit01"])
        self.assertEqual(
            sha256(ATTEMPT43_RUNTIME_CHECKPOINT),
            expected["attempt43_runtime_checkpoint"],
        )

    def test_04_all_304_prior_files_and_cache_are_current(self) -> None:
        integrity = self.evidence["integrity"]
        self.assertEqual(integrity["blender_exit_code"], 1)
        self.assertIsNone(integrity["native_invocation_error"])
        self.assertTrue(integrity["pre_post_exact"])
        self.assertEqual(integrity["before"], integrity["after"])
        self.assertEqual(len(integrity["before"]), 304)
        self.assertTrue(integrity["relevant_bytecode_cache_inventory_exact"])
        self.assertEqual(len(self.evidence["protected_records"]), 304)
        self.assertTrue(EXISTING_CACHE.is_file())
        self.assertEqual(EXISTING_CACHE.stat().st_size, 36680)
        self.assertEqual(sha256(EXISTING_CACHE), EXPECTED_CACHE_SHA256)

    def test_05_attempt43_stopped_without_mutation_or_save(self) -> None:
        failure = self.evidence["failure"]
        self.assertEqual(failure["status"], "NO_SAVE_ATTEMPT43_DIAGNOSTIC_STOP_PRESERVED")
        self.assertTrue(failure["diagnostic_exists"])
        for name in ("mesh_mutated", "body_mutated", "render_reached", "blend_saved", "runtime_changed"):
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

    def test_06_attempt43_chart_maximum_is_exact(self) -> None:
        candidate = self.evidence["candidate"]
        self.assertEqual(candidate["eligibility_failures"], ["maximum_chart_boundary_deviation_at_most_0.0011_m"])
        attribution = candidate["chart"]["boundary_deviation_attribution"]
        self.assertEqual(attribution["row_count"], 50)
        self.assertEqual(attribution["exceeding_row_count"], 9)
        self.assertEqual(attribution["maximum_contributor_boundary_indices"], [3])
        self.assertEqual(attribution["maximum_contributor_mesh_vertex_indices"], [241])
        self.assertEqual(candidate["boundary_cycle_mesh_vertex_indices"][3], 241)
        self.assertTrue(candidate["forced_ear_feasibility"]["passes"])
        self.assertEqual(candidate["forced_ear_feasibility"]["obstruction_count"], 0)

    def test_07_attempt43_complete_base_identity_is_bound(self) -> None:
        base = self.config["attempt43_base_domain"]
        candidate = self.evidence["candidate"]
        self.assertEqual(base["complete_face_count"], 124)
        self.assertEqual(base["complete_face_indices_sha256"], candidate["face_indices_sha256"])
        self.assertEqual(base["complete_vertex_count"], 88)
        self.assertEqual(base["complete_vertex_indices_sha256"], candidate["vertex_indices_sha256"])
        self.assertEqual(base["complete_boundary_edge_count"], 50)
        self.assertEqual(base["complete_boundary_cycle_mesh_vertex_indices"], candidate["boundary_cycle_mesh_vertex_indices"])
        self.assertEqual(base["complete_boundary_cycle_mesh_vertex_indices"][3], 241)
        self.assertEqual(len(base["added_complete_existing_source_face_indices"]), 36)
        attempt43_config = json.loads(
            (ROOT / self.config["bindings"]["attempt43_config"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        expected_added = set(
            attempt43_config["attempt42_base_domain"][
                "added_complete_existing_source_face_indices"
            ]
        ) | set(candidate["added_complete_source_mesh_vertex_star_face_indices"])
        self.assertEqual(
            set(base["added_complete_existing_source_face_indices"]), expected_added
        )

    def test_08_exactly_one_chart_maximum_source_star_candidate(self) -> None:
        probe = self.config["one_candidate_probe"]
        self.assertEqual(probe["candidate"], "complete_attempt43_domain_plus_complete_mesh_vertex_star_241")
        self.assertEqual(probe["exact_chart_maximum_mesh_vertex_index"], 241)
        self.assertTrue(probe["sole_chart_maximum_contributor"])
        self.assertTrue(probe["complete_source_mesh_vertex_star_only"])
        self.assertFalse(probe["uniform_face_ring_candidates_allowed"])
        self.assertFalse(probe["alternate_target_sets_allowed"])
        self.assertFalse(probe["coordinate_suppression_allowed"])
        runtime = self.verified["runtime_config"]["source_mesh_diagnostic"]
        self.assertEqual(runtime["targeted_vertex_star_suppression_sets"], [])
        self.assertEqual(runtime["uniform_face_ring_expansions_to_map"], [])

    def test_09_derived_runtime_validator_accepts_exact_config(self) -> None:
        namespace = {"__name__": "attempt44_runtime_contract_test", "__file__": str(WORKER.resolve()), "__builtins__": __builtins__}
        exec(compile(self.derived, str(WORKER) + "::contract", "exec"), namespace, namespace)
        namespace["validate_config"](self.verified["runtime_config"])
        self.assertEqual(self.verified["runtime_config"]["status"], "STATIC_READ_ONLY_CHART_MAXIMUM_STAR_PROOF_PREPARED_NOT_RUN")

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
            '"attempt43_complete_domain_used_only_as_read_only_base"',
        ):
            self.assertIn(token, self.derived)
        attribution = self.config["chart_attribution_contract"]
        self.assertEqual(attribution["maximum_allowed_boundary_deviation_m"], 0.0011)
        self.assertFalse(attribution["attribution_authorizes_vertex_movement"])
        self.assertFalse(attribution["attribution_authorizes_gate_change"])
        runtime = self.verified["runtime_config"]
        self.assertEqual(runtime["diagnosis"]["required_minimum_angle_degrees"], 12.0)
        self.assertEqual(
            runtime["unchanged_hard_gates"]["minimum_new_triangle_angle_degrees"],
            12.0,
        )
        self.assertEqual(
            runtime["unchanged_hard_gates"]["minimum_new_triangle_world_area_m2"],
            1.0e-10,
        )
        self.assertEqual(runtime["unchanged_hard_gates"]["global_seam_vertex_count"], 34)
        self.assertEqual(runtime["unchanged_hard_gates"]["global_seam_coordinate_delta_m"], 0.0)

    def test_11_derived_mapper_contains_no_mutation_or_output_operation(self) -> None:
        tree = ast.parse(self.derived)
        self.assertIsNotNone(tree)
        for token in (
            "bpy.ops.wm.save",
            "bpy.ops.render",
            "bpy.ops.export",
            "bpy.ops.object.join",
            "bmesh.ops.delete",
            "to_mesh(",
        ):
            self.assertNotIn(token, self.derived)
        self.assertIn("bm.verts[maximum_vertex_index].link_faces", self.derived)
        self.assertEqual(self.derived.count("targeted.append(row)"), 1)
        self.assertIn("ring_rows = []", self.derived)
        self.assertIn("complete_attempt43_domain_plus_complete_mesh_vertex_star_241", self.derived)

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
            "attempt44_blender_execution_performed",
            "attempt44_source_domain_mapping_performed",
            "attempt44_candidate_feasibility_proven",
            "attempt44_triangulation_performed",
            "attempt44_reconstruction_performed",
            "attempt44_body_mutation_performed",
            "attempt44_render_reached",
            "attempt44_blend_saved",
            "runtime_changed",
            "executable_body_repair_justified",
            "body_repair_proven",
            "owner_approval_claimed",
        ):
            self.assertFalse(self.config["truth"][name], name)

    def test_13_checkpoint_wrapper_covers_prior_inventory_and_cache(self) -> None:
        checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        for token in (
            "$priorAttempt43 = Get-Content -LiteralPath $attempt43Integrity -Raw | ConvertFrom-Json",
            "@($priorAttempt43.before).Count -ne 304",
            "foreach ($row in $priorAttempt43.before)",
            "Attempt 44 prior protected file drifted before Blender",
            "$env:PYTHONDONTWRITEBYTECODE = '1'",
            "$expectedRelevantBytecodeCaches",
            "relevant_bytecode_cache_inventory_exact",
            "Attempt 44 relevant bytecode cache inventory drifted",
            "sys.dont_write_bytecode = True",
        ):
            self.assertIn(token, checkpoint)
        prior = json.loads(ATTEMPT43_INTEGRITY.read_text(encoding="utf-8"))
        self.assertTrue(prior["pre_post_exact"])
        self.assertEqual(prior["before"], prior["after"])
        self.assertEqual(len(prior["before"]), 304)

    def test_14_launch_contract_is_one_shot_and_append_only(self) -> None:
        launch = self.config["launch_contract"]
        self.assertTrue(launch["wrapper_unions_attempt43_304_entry_inventory"])
        self.assertTrue(launch["wrapper_verifies_all_attempt43_records_before_blender"])
        self.assertTrue(launch["wrapper_protects_attempt40_generated_cpython313_cache"])
        self.assertTrue(launch["wrapper_refuses_any_new_relevant_worker_cache"])
        self.assertTrue(launch["worker_sets_sys_dont_write_bytecode_before_bound_worker_load"])
        self.assertTrue(launch["create_new_stdout_and_stderr_required"])
        self.assertTrue(launch["create_new_integrity_in_finally_required"])
        self.assertTrue(launch["exactly_one_blender_invocation_required"])
        self.assertTrue(launch["refuse_any_overwrite"])
        self.assertFalse(launch["executed_during_static_preparation"])

    def test_15_static_verification_created_no_output_or_new_cache(self) -> None:
        self.assertFalse(self.output.exists())
        self.assertFalse((ROOT / self.config["launch_contract"]["external_integrity"]).exists())
        self.assertTrue(EXISTING_CACHE.is_file())
        self.assertEqual(sha256(EXISTING_CACHE), EXPECTED_CACHE_SHA256)
        cache_after = [(str(path.resolve()), path.stat().st_size, sha256(path)) for path in relevant_caches()]
        self.assertEqual(cache_after, self.cache_before)
        self.assertEqual(cache_after, [(str(EXISTING_CACHE.resolve()), 36680, EXPECTED_CACHE_SHA256)])


if __name__ == "__main__":
    unittest.main()
