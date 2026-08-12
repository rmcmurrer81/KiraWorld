#!/usr/bin/env python3
"""Static fail-closed checks for the R23 Attempt05 read-only root-cause probe."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools/blender_probe_kira_r23_attempt05_patch_root_cause.py"
CONFIG = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt05_patch_root_cause_probe_attempt03_preparation/"
    "KIRA_R23_ATTEMPT05_PATCH_ROOT_CAUSE_PROBE_ATTEMPT03_CONFIG.json"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RootCauseProbePreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = WORKER.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_config_is_bound_but_requires_explicit_flag(self) -> None:
        self.assertEqual(
            self.config["status"],
            "BOUND_NOT_RUN_EXPLICIT_READONLY_ROOT_CAUSE_AUTHORIZATION_REQUIRED",
        )
        self.assertIn("--execute-readonly-root-cause-probe", self.source)

    def test_all_mutating_operations_are_forbidden(self) -> None:
        execution = self.config["execution"]
        for key in (
            "read_only_source_and_candidate",
            "render_forbidden",
            "blend_save_forbidden",
            "export_forbidden",
            "runtime_mutation_forbidden",
            "activation_assignment_publication_forbidden",
        ):
            self.assertIs(execution[key], True)

    def test_worker_has_no_render_save_or_export_call(self) -> None:
        forbidden = (
            "bpy.ops.render.render",
            "bpy.ops.wm.save_as_mainfile",
            "bpy.ops.wm.save_mainfile",
            "bpy.ops.export_scene",
        )
        for value in forbidden:
            self.assertNotIn(value, self.source)

    def test_exact_bound_files_match(self) -> None:
        for label in (
            "verification_config",
            "accepted_diagnostic",
            "r19_source",
            "r23_candidate",
        ):
            binding = self.config[label]
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), label)
            self.assertEqual(path.stat().st_size, binding["bytes"], label)
            self.assertEqual(digest(path), binding["sha256"], label)

    def test_output_is_new_append_only_attempt(self) -> None:
        output = self.config["output"]
        self.assertIs(output["append_only"], True)
        self.assertEqual(output["filename"], "ROOT_CAUSE_METRICS.json")
        self.assertFalse((ROOT / output["directory"]).exists())

    def test_attempt01_failure_is_preserved_and_exactly_bound(self) -> None:
        repair = self.config["repair_scope"]
        self.assertIs(repair["attempt_01_preserved"], True)
        binding = repair["attempt_01_failure"]
        path = ROOT / binding["path"]
        self.assertTrue(path.is_file())
        self.assertEqual(path.stat().st_size, binding["bytes"])
        self.assertEqual(digest(path), binding["sha256"])
        failure = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(failure["exception_type"], "ModuleNotFoundError")
        self.assertIn("No module named 'tools'", failure["exception"])

    def test_attempt02_metrics_are_preserved_and_exactly_bound(self) -> None:
        repair = self.config["repair_scope"]
        self.assertIs(repair["attempt_02_preserved"], True)
        binding = repair["attempt_02_metrics"]
        path = ROOT / binding["path"]
        self.assertTrue(path.is_file())
        self.assertEqual(path.stat().st_size, binding["bytes"])
        self.assertEqual(digest(path), binding["sha256"])
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            record["status"],
            "READ_ONLY_ROOT_CAUSE_METRICS_NOT_ACCEPTANCE_NOT_OWNER_APPROVAL",
        )

    def test_executing_worker_is_exactly_bound(self) -> None:
        binding = self.config["worker"]
        path = ROOT / binding["path"]
        self.assertEqual(path.resolve(), WORKER.resolve())
        self.assertEqual(path.stat().st_size, binding["bytes"])
        self.assertEqual(digest(path), binding["sha256"])
        self.assertIn('require_binding(config["worker"]', self.source)

    def test_exact_root_bootstrap_precedes_project_import(self) -> None:
        bootstrap = 'sys.path.insert(0, str(ROOT))'
        project_import = 'from tools import blender_verify_kira_r23_postsave_fresh_reopen'
        self.assertIn(bootstrap, self.source)
        self.assertLess(self.source.index(bootstrap), self.source.index(project_import))

    def test_probe_reuses_accepted_diagnostic_instead_of_repeating_exact_sweep(self) -> None:
        self.assertIn('diagnostic["intersections"]', self.source)
        self.assertNotIn("exact_nonadjacent_intersection_report", self.source)

    def test_patch_section_counts_are_exact(self) -> None:
        self.assertIn('(\"outer_91_to_154_zipper\", 245)', self.source)
        self.assertIn('(\"first_154_ring_bridge\", 308)', self.source)
        self.assertIn('(\"second_154_ring_bridge\", 308)', self.source)
        self.assertIn('(\"mapped_cc0_donor_disk\", 2488)', self.source)

    def test_truth_boundary_is_explicit(self) -> None:
        boundary = self.config["truth_boundary"]
        self.assertIs(boundary["diagnostic_only"], True)
        self.assertIs(boundary["owner_visual_approval"], False)
        self.assertIs(boundary["internal_physiology_or_subjective_experience_evidence"], False)


if __name__ == "__main__":
    unittest.main()
