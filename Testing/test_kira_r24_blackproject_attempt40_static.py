"""Static-only tests for the Attempt 40 wider source-domain proof."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools/blender_diagnose_kira_r24_blackproject_wider_source_domain_attempt40.py"
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT40_CONFIG.json"
)
CHECKPOINT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_internal_midpoint_fair_surface/PREFLIGHT/"
    "ATTEMPT_40_STATIC_CHECKPOINT.md"
)
ATTEMPT39_INTEGRITY = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "attempt39_external_pre_post_integrity.json"
)
EXPECTED_WORKER_SHA256 = (
    "faaf1259e408f7d547743940c0be11e0cd3c3e256ff7f221c5a2c7f570d38eb1"
)
EXPECTED_CONFIG_SHA256 = (
    "26bdb0f8a7eb6651260eb84f37d7714453e2620f3add3f864f89051732a17493"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_worker():
    spec = importlib.util.spec_from_file_location("attempt40_static_test_worker", WORKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Attempt 40 worker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Attempt40StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.before_output_exists = (
            ROOT
            / "RecoverySprint/continuation_20260803/"
            "kira_r24_internal_midpoint_fair_surface/attempt_40"
        ).exists()
        cls.module = load_worker()
        cls.config = cls.module.load_config()
        cls.verified = cls.module.verify_package(cls.config)
        cls.source = WORKER.read_text(encoding="utf-8")
        cls.derived = cls.verified["derived_source"]

    def test_01_exact_static_package_hashes(self) -> None:
        self.assertEqual(sha256(WORKER), EXPECTED_WORKER_SHA256)
        self.assertEqual(sha256(CONFIG), EXPECTED_CONFIG_SHA256)
        self.assertEqual(self.module.EXPECTED_CONFIG_SHA256, EXPECTED_CONFIG_SHA256)

    def test_02_import_is_blender_free_and_output_absent(self) -> None:
        self.assertNotIn("bpy", sys.modules)
        self.assertFalse(self.before_output_exists)
        output = ROOT / self.config["output"]["root"]
        self.assertFalse(output.exists())
        for name in ("stdout", "stderr", "external_integrity"):
            self.assertFalse((ROOT / self.config["launch_contract"][name]).exists())

    def test_03_attempt39_terminal_failure_is_exact(self) -> None:
        blocker = self.config["attempt39_terminal_blocker"]
        trials = self.verified["attempt39_trials"]
        terminal = trials["iterations"][-1]
        self.assertEqual(trials["error"], blocker["error"])
        self.assertEqual(terminal["iteration"], 5)
        self.assertEqual(terminal["worst_face"], [24, 22, 23])
        self.assertEqual(
            [row["output_indices"] for row in terminal["constrained_face_edges"]],
            [[22, 23], [23, 24]],
        )
        self.assertEqual(terminal["nonboundary_face_outputs"], [])
        self.assertEqual(terminal["matched_seed_rows"], [])
        self.assertEqual(terminal["trials"], [])
        self.assertFalse(blocker["another_seed_can_repair_exact_boundary"])

    def test_04_attempt39_external_integrity_is_exact(self) -> None:
        evidence = self.verified["attempt39_integrity"]
        self.assertEqual(evidence["blender_exit_code"], 1)
        self.assertIsNone(evidence["native_invocation_error"])
        self.assertTrue(evidence["pre_post_exact"])
        self.assertEqual(evidence["before"], evidence["after"])
        self.assertEqual(len(evidence["before"]), 252)

    def test_05_forced_ear_helper_accepts_and_rejects_known_triangles(self) -> None:
        failing = {
            "projected_boundary_xy_m": [[0.0, 0.0], [1.0, 0.0], [0.05, 0.01]],
            "boundary_angle_analysis": {
                "corner_rows": [
                    {"boundary_index": index, "interior_angle_degrees": angle}
                    for index, angle in enumerate([11.888658, 0.603091, 167.508251])
                ]
            },
        }
        # Corners below T are handled by the ordinary boundary-angle gate, so
        # this helper correctly has no [T,2T) forced-ear row for this triangle.
        self.assertTrue(self.module.forced_ear_feasibility(failing)["passes"])
        selected = self.verified["attempt30_diagnostic"][
            "smallest_necessary_eligible_existing_source_candidate"
        ]
        result = self.module.forced_ear_feasibility(selected)
        self.assertFalse(result["passes"])
        self.assertEqual(
            [row["boundary_index"] for row in result["obstructions"]], [13, 23]
        )

    def test_06_all_seven_prior_candidates_are_proven_infeasible(self) -> None:
        rows = self.verified["forced_rows"]
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(not row["result"]["passes"] for row in rows))
        self.assertEqual(
            {row["candidate"] for row in rows},
            {
                row["candidate"]
                for row in self.config["forced_ear_contract"][
                    "previous_candidate_obstructions"
                ]
            },
        )

    def test_07_one_probe_is_source_aligned_and_has_no_alternate(self) -> None:
        probe = self.config["one_wider_source_domain_probe"]
        self.assertEqual(probe["capture_source_indices"], [2, 6, 9, 19, 20, 28])
        self.assertEqual(probe["source_mesh_vertex_indices"], [90, 418, 504, 534, 407, 91])
        self.assertEqual(probe["added_exact_obstructing_mesh_vertex_indices"], [504, 534])
        self.assertFalse(probe["uniform_face_ring_candidates_allowed"])
        self.assertFalse(probe["alternate_target_sets_allowed"])
        runtime = self.verified["runtime_config"]
        self.assertEqual(
            runtime["source_mesh_diagnostic"]["targeted_vertex_star_suppression_sets"],
            [[2, 6, 9, 19, 20, 28]],
        )
        self.assertEqual(
            runtime["source_mesh_diagnostic"]["uniform_face_ring_expansions_to_map"],
            [0],
        )

    def test_08_derived_read_only_mapper_compiles(self) -> None:
        ast.parse(self.derived)
        compile(self.derived, str(WORKER) + "::derived-test", "exec")
        self.assertEqual(
            self.verified["derived_source_sha256"],
            "0361b8551d078a9039927bd6676b68c42029f089b964fd30c46d560d8bf96603",
        )
        self.assertIn("def attempt40_forced_ear_feasibility", self.derived)
        self.assertIn(
            'row["forced_ear_feasibility"] = forced_ear', self.derived
        )
        self.assertIn(
            '"executable_body_repair_justified": False', self.derived
        )

    def test_08b_derived_validator_accepts_exact_runtime_config(self) -> None:
        namespace = {
            "__name__": "attempt40_static_runtime_contract_test",
            "__file__": str(WORKER.resolve()),
            "__builtins__": __builtins__,
        }
        exec(
            compile(self.derived, str(WORKER) + "::derived-contract-test", "exec"),
            namespace,
            namespace,
        )
        namespace["validate_config"](self.verified["runtime_config"])
        self.assertEqual(
            self.verified["runtime_config"]["status"],
            "STATIC_READ_ONLY_DOMAIN_PROOF_PREPARED_NOT_RUN",
        )

    def test_09_derived_mapper_contains_no_geometry_or_output_operation(self) -> None:
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
        self.assertNotIn("attempt_30", self.derived)
        self.assertNotIn("attempt30", self.derived)

    def test_10_scope_forbids_reconstruction_mutation_save_render_and_retry(self) -> None:
        scope = self.config["scope"]
        for name in (
            "source_file_mutation_allowed",
            "prior_evidence_mutation_allowed",
            "body_geometry_mutation_allowed",
            "patch_geometry_mutation_allowed",
            "blender_datablock_transform_assignment_allowed",
            "triangulation_allowed",
            "reconstruction_allowed",
            "render_allowed",
            "blend_save_allowed",
            "export_allowed",
            "runtime_activation_allowed",
            "assignment_allowed",
            "publication_allowed",
            "boundary_or_seam_movement_allowed",
            "quality_gate_reduction_allowed",
            "automatic_alternate_candidate_allowed",
            "automatic_retry_allowed",
        ):
            self.assertFalse(scope[name], name)

    def test_11_truth_does_not_claim_executable_repair(self) -> None:
        truth = self.config["truth"]
        self.assertTrue(truth["attempt39_fixed_boundary_infeasibility_proven"])
        self.assertTrue(truth["all_seven_attempt30_eligible_candidates_forced_ear_infeasible"])
        for name in (
            "attempt40_blender_execution_performed",
            "attempt40_source_domain_mapping_performed",
            "attempt40_candidate_feasibility_proven",
            "attempt40_triangulation_performed",
            "attempt40_reconstruction_performed",
            "attempt40_body_mutation_performed",
            "attempt40_render_reached",
            "attempt40_blend_saved",
            "runtime_changed",
            "executable_body_repair_justified",
            "body_repair_proven",
            "owner_approval_claimed",
        ):
            self.assertFalse(truth[name], name)

    def test_12_launch_contract_is_one_shot_and_append_only(self) -> None:
        launch = self.config["launch_contract"]
        self.assertTrue(launch["wrapper_checks_output_and_all_external_targets_absent_before_open"])
        self.assertTrue(launch["create_new_stdout_and_stderr_required"])
        self.assertTrue(launch["create_new_integrity_in_finally_required"])
        self.assertTrue(launch["exactly_one_blender_invocation_required"])
        self.assertTrue(launch["refuse_any_overwrite"])
        self.assertFalse(launch["executed_during_static_preparation"])

    def test_12b_wrapper_covers_and_verifies_prior_protected_inventory(self) -> None:
        checkpoint = CHECKPOINT.read_text(encoding="utf-8")
        for token in (
            "$prior = Get-Content -LiteralPath $attempt39Integrity -Raw | ConvertFrom-Json",
            "@($prior.before).Count -ne 252",
            "foreach ($row in $prior.before)",
            "Attempt 40 prior protected file drifted before Blender",
        ):
            self.assertIn(token, checkpoint)

        prior = json.loads(ATTEMPT39_INTEGRITY.read_text(encoding="utf-8"))
        self.assertTrue(prior["pre_post_exact"])
        self.assertEqual(prior["before"], prior["after"])
        self.assertEqual(len(prior["before"]), 252)
        prior_paths = set()
        for row in prior["before"]:
            path = Path(row["path"]).resolve(strict=True)
            self.assertTrue(path == ROOT.resolve() or ROOT.resolve() in path.parents)
            self.assertEqual(path.stat().st_size, int(row["bytes"]))
            self.assertEqual(sha256(path), row["sha256"])
            prior_paths.add(path)
        self.assertEqual(len(prior_paths), 252)
        for required in (
            ROOT / "RecoverySprint/continuation_20260803/kira_r24_internal_midpoint_fair_surface/PREFLIGHT/ATTEMPT_39_STATIC_CHECKPOINT.md",
            ROOT / "Testing/test_kira_r24_blackproject_attempt38_runtime_analysis_static.py",
            ROOT / "Testing/test_kira_r24_blackproject_attempt39_static.py",
        ):
            self.assertIn(required.resolve(strict=True), prior_paths)

    def test_13_static_verification_created_no_attempt40_output(self) -> None:
        output = ROOT / self.config["output"]["root"]
        self.assertFalse(output.exists())
        self.assertFalse(
            (ROOT / self.config["launch_contract"]["external_integrity"]).exists()
        )


if __name__ == "__main__":
    unittest.main()
