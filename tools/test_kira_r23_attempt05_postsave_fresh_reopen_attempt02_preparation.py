#!/usr/bin/env python3
"""Warning-fatal, no-Blender tests for fresh-reopen Attempt 02."""

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
    "kira_r23_cc0_afes_author_attempt05_postsave_fresh_reopen_attempt02_preparation"
)
CONFIG_PATH = PACKAGE / (
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT05_POSTSAVE_FRESH_REOPEN_ATTEMPT02_CONFIG.json"
)
PREVIOUS_CONFIG_PATH = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt05_postsave_fresh_reopen_preparation/"
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT05_POSTSAVE_FRESH_REOPEN_CONFIG.json"
)
BOOTSTRAP_PATH = ROOT / "tools/blender_bootstrap_kira_r23_attempt05_fresh_reopen.py"
PREFLIGHT_PATH = ROOT / (
    "tools/kira_r23_attempt05_postsave_fresh_reopen_attempt02_preflight.py"
)
WORKER_PATH = ROOT / "tools/blender_verify_kira_r23_postsave_fresh_reopen.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Attempt02PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.previous = json.loads(PREVIOUS_CONFIG_PATH.read_text(encoding="utf-8"))
        cls.bootstrap = load(BOOTSTRAP_PATH, "_attempt02_bootstrap_test")
        cls.preflight = load(PREFLIGHT_PATH, "_attempt02_preflight_test")
        cls.worker = load(WORKER_PATH, "_attempt02_worker_test")

    def test_01_attempt02_identity_and_new_output_paths(self) -> None:
        self.assertTrue(self.config["attempt_id"].endswith("ATTEMPT02"))
        output = self.config["bound_output"]
        self.assertTrue(output["evidence_directory"].endswith("/attempt_02"))
        self.assertTrue(output["owner_render_directory"].endswith("/attempt_02/owner_renders"))
        self.assertFalse((ROOT / output["evidence_directory"]).exists())
        self.assertFalse((ROOT / output["owner_render_directory"]).exists())

    def test_02_attempt01_closure_and_failure_are_exact(self) -> None:
        result = self.preflight.verify_attempt01_failure(self.config)
        self.assertEqual(result["exact_entries"], ["FAILURE_EVIDENCE.json", "owner_renders"])
        self.assertTrue(result["owner_renders_empty"])
        self.assertEqual(
            result["binding"]["sha256"],
            "b7b135b8fb12cdfead6365fd41a8a703aefe6fa39069c00dda5a6389f1586031",
        )

    def test_03_attempt01_failed_before_open_and_changed_nothing(self) -> None:
        failure = json.loads(
            (ROOT / self.config["fixed_inputs"]["attempt01_failure_evidence"]["path"])
            .read_text(encoding="utf-8")
        )
        self.assertEqual(failure["exception"], "No module named 'tools'")
        self.assertIn("line 1018", failure["traceback"])
        self.assertEqual(failure["source_before"], failure["source_current"])
        self.assertEqual(failure["candidate_before"], failure["candidate_current"])

    def test_04_bootstrap_exact_project_root(self) -> None:
        self.assertEqual(self.bootstrap.exact_project_root(), ROOT.resolve())
        self.assertEqual(self.bootstrap.EXPECTED_PROJECT_ROOT.resolve(), ROOT.resolve())

    def test_05_bootstrap_adds_only_exact_root(self) -> None:
        original = sys.path[:]
        initial = ["SENTINEL_A", str(ROOT.parent), "SENTINEL_B"]
        try:
            sys.path[:] = initial
            self.bootstrap.install_exact_project_root(ROOT.resolve())
            observed = sys.path[:]
        finally:
            sys.path[:] = original
        self.assertEqual(observed, [str(ROOT.resolve()), *initial])
        self.assertNotIn(str(ROOT.parent.resolve()), observed[:1])

    def test_06_bootstrap_deduplicates_only_exact_root(self) -> None:
        original = sys.path[:]
        exact = str(ROOT.resolve())
        try:
            sys.path[:] = ["A", exact, "B", exact, "C"]
            self.bootstrap.install_exact_project_root(ROOT.resolve())
            observed = sys.path[:]
        finally:
            sys.path[:] = original
        self.assertEqual(observed, [exact, "A", "B", "C"])

    def test_07_bootstrap_does_not_read_ambient_pythonpath(self) -> None:
        tree = ast.parse(BOOTSTRAP_PATH.read_text(encoding="utf-8"))
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertNotIn("os", imported)
        source = BOOTSTRAP_PATH.read_text(encoding="utf-8")
        self.assertNotIn("os.environ", source)
        self.assertNotIn("getenv(", source)

    def test_08_bootstrap_binds_unchanged_worker(self) -> None:
        worker = self.bootstrap.verified_worker(ROOT.resolve())
        self.assertEqual(worker, WORKER_PATH.resolve())
        self.assertEqual(self.bootstrap.WORKER_BYTES, 55260)
        self.assertEqual(
            self.bootstrap.WORKER_SHA256,
            "5dbf4faaef09a82717989f5e7bc17312d5182b0042e39475aa5b47f131f3a1b5",
        )

    def test_09_bootstrap_has_no_blender_or_output_operations(self) -> None:
        source = BOOTSTRAP_PATH.read_text(encoding="utf-8")
        forbidden = (
            "bpy", "open_mainfile", "save_as_mainfile", "render.render",
            "mkdir", "write_text", "write_bytes", "subprocess",
        )
        for token in forbidden:
            self.assertNotIn(token, source, token)

    def test_10_explicit_execution_flag_still_required(self) -> None:
        with self.assertRaises(self.worker.VerificationError):
            self.worker.validate_bound_contract(self.config, explicit_execution=False)

    def test_11_bound_contract_accepts_only_absent_nested_outputs(self) -> None:
        paths = self.worker.validate_bound_contract(self.config, explicit_execution=True)
        self.assertFalse(paths["evidence_dir"].exists())
        self.assertFalse(paths["render_dir"].exists())
        paths["render_dir"].relative_to(paths["evidence_dir"])

    def test_12_candidate_and_evidence_bindings_unchanged(self) -> None:
        self.assertEqual(self.config["candidate_binding"], self.previous["candidate_binding"])
        self.assertEqual(
            self.config["build_evidence_binding"], self.previous["build_evidence_binding"]
        )

    def test_13_all_original_verification_gates_are_exact(self) -> None:
        result = self.preflight.verify_same_gates(self.config)
        self.assertTrue(all(result.values()))

    def test_14_seam_and_intersection_thresholds_are_not_weakened(self) -> None:
        thresholds = self.config["continuity_thresholds"]
        self.assertEqual(thresholds, self.previous["continuity_thresholds"])
        self.assertEqual(thresholds["maximum_seam_position_error_m"], 1e-8)
        self.assertEqual(thresholds["maximum_seam_weight_error"], 1e-8)
        self.assertEqual(thresholds["maximum_new_exact_intersection_pairs_per_pose"], 0)
        self.assertEqual(thresholds["maximum_patch_involving_exact_intersection_pairs"], 0)

    def test_15_boundary_semantics_are_unchanged(self) -> None:
        semantics = self.config["boundary_semantics_contract"]
        self.assertEqual(semantics, self.previous["boundary_semantics_contract"])
        self.assertEqual(semantics["whole_body_source_inherited_boundary_edge_count"], 330)
        self.assertEqual(semantics["whole_body_source_inherited_boundary_cycle_count"], 23)
        self.assertEqual(semantics["replacement_patch_subset_interface_vertex_count"], 91)
        self.assertFalse(semantics["rejected_pelvic_patch_seam_as_new_whole_body_boundary_allowed"])

    def test_16_future_command_uses_bootstrap_then_same_config_gate(self) -> None:
        command = self.preflight.future_command(self.config)
        self.assertEqual(command[1:4], ["--background", "--factory-startup", "--disable-autoexec"])
        self.assertEqual(Path(command[5]), BOOTSTRAP_PATH.resolve())
        self.assertIn("--execute-fresh-reopen", command)
        self.assertNotIn(str(WORKER_PATH.resolve()), command)

    def test_17_preflight_is_nonexecuting(self) -> None:
        source = PREFLIGHT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("Popen(", source)
        self.assertNotIn("subprocess.run", source)

    def test_18_zstd_remains_preliminary_only(self) -> None:
        candidate = ROOT / self.config["candidate_binding"]["path"]
        with candidate.open("rb") as stream:
            self.assertEqual(stream.read(4), bytes.fromhex("28b52ffd"))
        self.assertTrue(self.config["container_preflight"]["does_not_establish_blend_validity"])
        self.assertTrue(self.config["container_preflight"]["does_not_replace_fresh_blender_reopen"])

    def test_19_no_preparation_execution_or_render_truth(self) -> None:
        execution = self.config["execution"]
        self.assertFalse(execution["executed_during_preparation"])
        self.assertFalse(execution["rendered_during_preparation"])
        self.assertTrue(execution["source_save_forbidden"])
        self.assertTrue(execution["candidate_save_forbidden"])
        self.assertTrue(execution["runtime_activation_forbidden"])
        self.assertTrue(execution["publication_forbidden"])
        self.assertTrue(execution["export_forbidden"])

    def test_20_manifest_closes_required_artifacts_without_self_reference(self) -> None:
        manifest = json.loads((PACKAGE / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
        paths = [row["path"] for row in manifest["artifacts"]]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertNotIn(
            "RecoverySprint/continuation_20260803/"
            "kira_r23_cc0_afes_author_attempt05_postsave_fresh_reopen_attempt02_preparation/"
            "PACKAGE_MANIFEST.json",
            paths,
        )
        for row in manifest["artifacts"]:
            path = ROOT / row["path"]
            self.assertEqual(path.stat().st_size, row["bytes"])
            self.assertEqual(self.preflight.sha256_file(path), row["sha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
