#!/usr/bin/env python3
"""Warning-fatal, no-Blender tests for the R23 gate diagnostic package."""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt05_postsave_gate_diagnostic_preparation"
)
CONFIG_PATH = PACKAGE / "KIRA_R23_ATTEMPT05_POSTSAVE_GATE_DIAGNOSTIC_CONFIG.json"
WORKER_PATH = ROOT / "tools/blender_diagnose_kira_r23_attempt05_postsave_gates.py"
BOOTSTRAP_PATH = ROOT / (
    "tools/blender_bootstrap_kira_r23_attempt05_postsave_gate_diagnostic.py"
)
PREFLIGHT_PATH = ROOT / "tools/kira_r23_attempt05_postsave_gate_diagnostic_preflight.py"
VERIFIER_PATH = ROOT / "tools/blender_verify_kira_r23_postsave_fresh_reopen.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def qualified_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = qualified_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


class GateDiagnosticPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        verification_path = ROOT / cls.config["verification_config_binding"]["path"]
        cls.verification = json.loads(verification_path.read_text(encoding="utf-8"))
        cls.worker = load(WORKER_PATH, "_r23_gate_diagnostic_worker_test")
        cls.bootstrap = load(BOOTSTRAP_PATH, "_r23_gate_diagnostic_bootstrap_test")
        cls.preflight = load(PREFLIGHT_PATH, "_r23_gate_diagnostic_preflight_test")
        cls.verifier = load(VERIFIER_PATH, "_r23_gate_diagnostic_verifier_test")
        cls.worker_source = WORKER_PATH.read_text(encoding="utf-8")
        cls.worker_tree = ast.parse(cls.worker_source)
        cls.worker_calls = {
            qualified_name(node.func)
            for node in ast.walk(cls.worker_tree)
            if isinstance(node, ast.Call)
        }

    def test_01_bound_identity_and_output_absent(self) -> None:
        self.assertEqual(
            self.config["status"],
            "BOUND_NOT_RUN_EXPLICIT_READONLY_DIAGNOSTIC_AUTHORIZATION_REQUIRED",
        )
        output = ROOT / self.config["diagnostic_output"]["directory"]
        self.assertFalse(output.exists())

    def test_02_attempt02_failure_binding_exact(self) -> None:
        binding = self.config["attempt02_failure_binding"]
        self.assertEqual(binding["bytes"], 2073)
        self.assertEqual(
            binding["sha256"],
            "a496028f1e7fad0c624e18f05c76927fe2c4a410ed10d65d7ebb7f84ad1c4ec0",
        )
        result = self.preflight.verify_binding(binding, "Attempt02 failure")
        self.assertEqual(result["sha256"], binding["sha256"])

    def test_03_attempt02_failure_closure_preserved(self) -> None:
        result = self.preflight.verify_attempt02_preservation(
            self.config, self.worker, self.verifier
        )
        self.assertEqual(result["exact_entries"], ["FAILURE_EVIDENCE.json", "owner_renders"])
        self.assertTrue(result["owner_renders_empty"])
        self.assertTrue(result["source_and_candidate_unchanged"])

    def test_04_exact_failed_gate_groups_preserved(self) -> None:
        groups = self.config["attempt02_failure_preservation"]["pre_render_gate_groups"]
        self.assertFalse(groups["intersections"])
        self.assertFalse(groups["continuity"])
        self.assertFalse(groups["deformation"])
        for key in (
            "candidate_flags", "structure", "weights", "frozen_ledgers",
            "retained_surface",
        ):
            self.assertTrue(groups[key], key)

    def test_05_exact_attempt02_config_binding(self) -> None:
        binding = self.config["verification_config_binding"]
        self.assertEqual(binding["bytes"], 29054)
        self.assertEqual(
            binding["sha256"],
            "ca97037ae8a2cd0465c09b32533687e30f862f2b87bb8ce626ce57b52330afbd",
        )
        self.preflight.verify_binding(binding, "Attempt02 config")

    def test_06_unchanged_verifier_binding(self) -> None:
        binding = self.config["tool_bindings"]["unchanged_fresh_reopen_verifier"]
        self.assertEqual(binding["bytes"], 55260)
        self.assertEqual(
            binding["sha256"],
            "5dbf4faaef09a82717989f5e7bc17312d5182b0042e39475aa5b47f131f3a1b5",
        )
        self.preflight.verify_binding(binding, "unchanged verifier")

    def test_07_explicit_diagnostic_flag_required(self) -> None:
        with self.assertRaises(self.worker.DiagnosticError):
            self.worker.validate_contract(self.config, False, self.verifier)

    def test_08_bound_contract_accepts_only_new_absent_output(self) -> None:
        result = self.worker.validate_contract(self.config, True, self.verifier)
        self.assertFalse(result["output_directory"].exists())

    def test_09_bootstrap_adds_only_exact_root(self) -> None:
        root = self.bootstrap.exact_project_root()
        original = sys.path[:]
        initial = ["DIAGNOSTIC_A", str(ROOT.parent), "DIAGNOSTIC_B"]
        try:
            sys.path[:] = initial
            self.bootstrap.install_exact_project_root(root)
            observed = sys.path[:]
        finally:
            sys.path[:] = original
        self.assertEqual(observed, [str(ROOT.resolve()), *initial])

    def test_10_bootstrap_binds_exact_diagnostic_worker(self) -> None:
        self.assertEqual(self.bootstrap.verified_worker(ROOT.resolve()), WORKER_PATH.resolve())
        binding = self.config["tool_bindings"]["diagnostic_worker"]
        self.assertEqual(self.bootstrap.WORKER_BYTES, binding["bytes"])
        self.assertEqual(self.bootstrap.WORKER_SHA256, binding["sha256"])

    def test_11_worker_never_calls_acceptance_run_or_renderer(self) -> None:
        forbidden = {
            "verifier.run", "verifier.render_owner_package",
            "verifier.configure_render_scene", "bpy.ops.render.render",
            "bpy.ops.wm.save_as_mainfile", "bpy.ops.wm.save_mainfile",
        }
        self.assertFalse(forbidden.intersection(self.worker_calls))

    def test_12_worker_never_launches_another_process(self) -> None:
        self.assertNotIn("subprocess", self.worker_source)
        self.assertNotIn("Popen(", self.worker_source)

    def test_13_worker_reuses_unchanged_measurement_helpers(self) -> None:
        required = {
            "verifier.source_snapshot", "verifier.exact_intersections",
            "verifier.seam_continuity", "verifier.deformation_series",
            "verifier.uv_values_at_vertex", "verifier.weight_map",
            "verifier.weight_error", "verifier.write_new_json",
        }
        self.assertTrue(required.issubset(self.worker_calls))

    def test_14_single_deformation_pass_captures_full_intersections(self) -> None:
        self.assertIn("verifier.exact_intersections = capture", self.worker_source)
        self.assertIn("verifier.exact_intersections = unchanged_exact_intersections", self.worker_source)
        self.assertIn('"full_exact_intersections": captured[index]', self.worker_source)
        self.assertEqual(self.worker_source.count("verifier.deformation_series("), 1)

    def test_15_full_continuity_localization_is_required(self) -> None:
        contract = self.config["metric_capture_contract"]
        self.assertTrue(contract["continuity_helper_result_required"])
        self.assertTrue(contract["continuity_per_vertex_position_weight_tangent_uv_required"])
        self.assertTrue(contract["continuity_per_edge_normal_required"])
        self.assertTrue(contract["continuity_localization_must_reproduce_helper_aggregates"])

    def test_16_evaluated_index_compatibility_is_fail_closed(self) -> None:
        self.assertIn("def evaluated_index_compatibility", self.worker_source)
        self.assertIn('if not index_compatibility["passed"]', self.worker_source)
        self.assertIn('"evaluated_index_compatibility": index_compatibility', self.worker_source)

    def test_17_exact_thresholds_are_reused_unchanged(self) -> None:
        result = self.preflight.verify_metric_contract(self.config, self.verification)
        self.assertTrue(result["all_contract_requirements_true"])
        thresholds = result["unchanged_thresholds"]
        self.assertEqual(thresholds["maximum_seam_position_error_m"], 1e-8)
        self.assertEqual(thresholds["minimum_seam_tangent_dot"], 0.999999)
        self.assertEqual(thresholds["maximum_new_exact_intersection_pairs_per_pose"], 0)
        self.assertEqual(thresholds["maximum_patch_involving_exact_intersection_pairs"], 0)

    def test_18_boundary_semantics_and_pelvic_seam_gate_unchanged(self) -> None:
        semantics = self.verification["boundary_semantics_contract"]
        self.assertEqual(semantics["whole_body_source_inherited_boundary_edge_count"], 330)
        self.assertEqual(semantics["whole_body_source_inherited_boundary_cycle_count"], 23)
        self.assertEqual(semantics["replacement_patch_subset_interface_vertex_count"], 91)
        self.assertFalse(semantics["rejected_pelvic_patch_seam_as_new_whole_body_boundary_allowed"])
        self.assertTrue(semantics["fresh_reopen_must_recheck_seam_position_normal_tangent_uv_weight_and_intersection_gates"])

    def test_19_all_exact_config_poses_are_preserved(self) -> None:
        pose_ids = [pose["id"] for pose in self.verification["poses"]]
        self.assertEqual(len(pose_ids), 11)
        self.assertEqual(
            pose_ids,
            [
                "neutral", "left_knee_bend", "right_knee_bend",
                "bilateral_knee_bend", "hip_flexion", "hip_abduction",
                "seated_contact", "toilet_seated", "supine",
                "eating_reach", "hand_presentation",
            ],
        )

    def test_20_metrics_are_written_only_after_all_measurements(self) -> None:
        self.assertLess(
            self.worker_source.index("deformation = captured_deformation_series("),
            self.worker_source.index("verifier.write_new_json(diagnostic_path, diagnostic)"),
        )
        self.assertLess(
            self.worker_source.index("localized_continuity = continuity_localization("),
            self.worker_source.index("verifier.write_new_json(diagnostic_path, diagnostic)"),
        )

    def test_21_gate_failures_are_recorded_not_waived(self) -> None:
        contract = self.config["metric_capture_contract"]
        self.assertTrue(contract["gate_failures_are_recorded_not_reclassified_as_passes"])
        self.assertTrue(contract["acceptance_threshold_changes_forbidden"])
        self.assertTrue(contract["diagnostic_is_not_acceptance_or_owner_approval"])

    def test_22_source_candidate_operations_are_read_only(self) -> None:
        execution = self.config["execution"]
        for key in (
            "read_only_source_and_candidate", "render_forbidden",
            "source_save_forbidden", "candidate_save_forbidden",
            "export_forbidden", "runtime_activation_forbidden",
            "publication_forbidden",
        ):
            self.assertTrue(execution[key], key)
        self.assertFalse(execution["executed_during_preparation"])
        self.assertFalse(execution["rendered_during_preparation"])

    def test_23_future_command_is_factory_empty_and_bootstrapped(self) -> None:
        command = self.preflight.future_command(self.config)
        self.assertEqual(command[1:4], ["--background", "--factory-startup", "--disable-autoexec"])
        self.assertEqual(Path(command[5]), BOOTSTRAP_PATH.resolve())
        self.assertIn("--execute-readonly-gate-diagnostic", command)
        self.assertNotIn(self.verification["candidate_binding"]["path"], command)

    def test_24_preflight_cannot_start_blender(self) -> None:
        source = PREFLIGHT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("Popen(", source)
        self.assertNotIn("subprocess.run", source)

    def test_25_manifest_closes_required_artifacts_without_self_reference(self) -> None:
        manifest = json.loads((PACKAGE / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
        paths = [row["path"] for row in manifest["artifacts"]]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertNotIn(
            "RecoverySprint/continuation_20260803/"
            "kira_r23_cc0_afes_author_attempt05_postsave_gate_diagnostic_preparation/"
            "PACKAGE_MANIFEST.json",
            paths,
        )
        for row in manifest["artifacts"]:
            path = ROOT / row["path"]
            self.assertEqual(path.stat().st_size, row["bytes"])
            self.assertEqual(self.preflight.sha256_file(path), row["sha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
